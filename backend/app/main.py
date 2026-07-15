"""SundayOS 3.0 backend — FastAPI entry.

Wires the cognitive engine router, memory, dual-process dispatch, guardrails,
and persona into a chat endpoint. Runs offline in mock mode (no keys needed).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Path as FastAPIPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from .webchat import CHAT_HTML
from .pwa import MANIFEST_JSON, get_icon_svg
from .persona.preferences import PreferenceStore
from .persona.feedback_parser import parse_feedback
from .auth import UserStore

from .cognition.belief import BeliefState
from .cognition.burst_split import burst_split
from .cognition.dispatch import needs_reasoner, risk_level
from .engines.base import Complexity, EngineMessage
from .engines.registry import build_engines
from .engines.router import CognitiveRequest, CognitiveRouter
from .guardrails.pipeline import GuardrailTripwire, check_input, redact_pii
from .conversation.store import ConversationStore
from .memory.schema import MemoryNode, MemoryType
from .memory.store import MemoryStore
from .memory.sqlite_store import SQLiteMemoryStore
from .memory.embedding import auto_upgrade_embedder, set_embedder
from .memory.importance import score_importance
from .memory.reflection import run_reflection, schedule_reflection
from .memory.experience import run_experience_layer
from .cognition.tools import TOOLS, SKILLS, _memory_search_handler
from .cognition.react_loop import ReActLoop, ReActResult
from .cognition.context_builder import build_context, AssembledContext
from .persona import build_system_prompt, build_prompt_with_prefs, get_user_preferences
from .persona import load as load_persona, reload as reload_persona, version as persona_version
from .persona.empathy import run_empathy_pipeline, analyze_user as empathy_analyze

load_dotenv(override=True)

# Read version from the project VERSION file (single source of truth).
# Falls back to "0.0.0-dev" if the file is missing.
_version_path = Path(__file__).resolve().parent.parent.parent / "VERSION"
try:
    _version_str = _version_path.read_text(encoding="utf-8").strip()
except Exception:
    _version_str = "0.0.0-dev"
app = FastAPI(title="Sunday OS", version=_version_str)

# CORS — the API is auth-protected via X-API-Key, so we allow any origin to
# call it (iPhone Shortcuts, the web console on another domain, curl, etc.).
# Tighten `allow_origins` to your own domains if you prefer.
_origins = os.getenv("SUNDAY_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Runtime — the single skeletal container for all subsystems ---------------
# All subsystems are held in one typed object. See app/runtime.py for:
#   - Field documentation (what each subsystem is)
#   - LINKAGE graph (who calls whom, in what order)
# When you add a subsystem: add 1 field to Runtime + 1 entry to its linkage.
from .runtime import Runtime
from .log_engine import log

ENGINES = build_engines()
ROUTER = CognitiveRouter(ENGINES)

# ── Startup: log the engine fleet ──────────────────────────────────────
log.engine_startup(ENGINES)
# Use SQLite-backed memory (persists across restarts). Falls back to in-memory
# if db_path is not set or the SQLite store can't be opened.
_db_path = os.getenv("SUNDAY_DB_PATH", "./sunday.db")
try:
    MEMORY = SQLiteMemoryStore(db_path=_db_path)
except Exception:
    log.warn("startup", event="memory_sqlite_fallback",
             detail="SQLite store init failed, falling back to in-memory MemoryStore")
    MEMORY = MemoryStore()
CONV = ConversationStore()
API_KEY = os.getenv("SUNDAY_API_KEY", "change-me-in-production")

# ── Preference store (ADR-012) ──
# Own connection (not shared with MEMORY) to avoid SQLITE_BUSY / lock
# conflicts when both stores are written concurrently.
import sqlite3 as _sqlite3
_DB_PATH = os.getenv("SUNDAY_DB_PATH", "./sunday.db")
PREF_STORE = PreferenceStore(_sqlite3.connect(_DB_PATH, check_same_thread=False))
PREF_STORE._conn.execute("PRAGMA journal_mode=WAL")
PREF_STORE._conn.execute("PRAGMA busy_timeout=5000")

# ── User account store ──
USER_STORE = UserStore(_DB_PATH)

# Auto-upgrade embedder to semantic if API keys are configured AND the provider
# actually supports embeddings (DeepSeek currently does not). Falls back to the
# hash embedder for offline / no-key scenarios.
_has_semantic = False
try:
    _has_semantic = auto_upgrade_embedder()
except Exception:
    pass  # hash embedder is always available

# ---- Runtime: the canonical container for all subsystems -----------------
runtime = Runtime(
    engines=ENGINES,
    router=ROUTER,
    memory=MEMORY,
    conversations=CONV,
    tools=TOOLS,
    skills=SKILLS,
)
RT = runtime  # shorter alias
runtime.semantic_embedder_available = _has_semantic

# --- usage stats (in-memory, resets on restart) ------------------------------
# Deprecated: use runtime.messages_today etc. and runtime.record_call() directly.
from collections import defaultdict
from datetime import datetime as _dt
# _USAGE is deprecated — use runtime.messages_today etc. directly.
# _record_stats() is deprecated — use runtime.record_call().

def _record_stats(engine_id: str | None, latency_ms: float,
                  prompt_tokens: int, completion_tokens: int, cost_usd: float,
                  event: str = "") -> None:
    runtime.record_call(engine_id, latency_ms, prompt_tokens, completion_tokens, cost_usd, event)

# Persona is loaded from persona.yaml (Git-versioned, per ADR-009).
# Call reload_persona() to pick up changes without restarting.


def _auth(x_api_key: str | None = None,
          x_sunday_token: str | None = None) -> str:
    """Authenticate request. Returns user_id on success, raises 401 on failure.

    Dual auth: User token first (for logged-in users), then API key
    (for admin / Shortcuts / scripts). Token is the primary path.

    If the token value is actually an old-format API key (migration path),
    it is checked as an API key before being rejected.
    """
    # Path 1: User token (webchat/console login)
    if x_sunday_token:
        user = USER_STORE.get_user_by_token(x_sunday_token)
        if user is not None:
            return user.id
        # Token not found — could be an old-format API key (migration)
        # Try it as an API key before rejecting
        if x_sunday_token == API_KEY:
            import hashlib
            return "user_" + hashlib.sha256(x_sunday_token.encode("utf-8")).hexdigest()[:16]
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")

    # Path 2: Legacy API key (admin / Shortcuts / curl)
    if x_api_key:
        if x_api_key == API_KEY:
            import hashlib
            return "user_" + hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()[:16]
        raise HTTPException(status_code=401, detail="invalid or missing API Key")

    # No credentials at all
    raise HTTPException(status_code=401, detail="请先登录或提供 API Key")





# --- iPhone Shortcuts endpoints ----------------------------------------------

class ShortcutChatRequest(BaseModel):
    message: str
    voice_input: bool = True


@app.post("/api/shortcuts/chat")
async def shortcuts_chat(req: ShortcutChatRequest,
                         x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")):
    """iPhone Shortcuts / Siri endpoint.

    Accepts a message, runs the full Sunday pipeline, returns a compact
    voice-friendly response. Designed to be used with the "Get Contents of URL"
    action in Apple Shortcuts.
    """
    user_id = _auth(x_api_key, x_sunday_token)

    # Run the same pipeline as /api/chat but with a compact response
    try:
        check_input(req.message)
    except GuardrailTripwire as t:
        raise HTTPException(status_code=400, detail=f"guardrail:{t.layer}:{t.reason}")

    user = user_id

    # Topic-aware cross-session context
    assembled = await build_context(req.message, user, MEMORY, ROUTER)
    context_block = assembled.to_prompt_section() if assembled else ""

    use_reasoner = needs_reasoner("chat", req.message,
                                  BeliefState(user_id=user))
    system_prompt = build_prompt_with_prefs(user, PREF_STORE)
    if context_block:
        system_prompt += f"\n\n{context_block}"

    if use_reasoner:
        react = ReActLoop(router=ROUTER, tools=TOOLS, memory_store=MEMORY, skills=SKILLS,
                          max_steps=5, timeout_s=60.0)
        react_result = await react.run(
            system_prompt=system_prompt,
            user_message=req.message,
            user_id=user,
        )
        reply = react_result.answer
    else:
        messages = [
            EngineMessage(role="system", content=system_prompt),
            EngineMessage(role="user", content=req.message),
        ]
        result = await ROUTER.route(CognitiveRequest(
            messages=messages,
            complexity=Complexity.L2_DAILY,
            prefer_chinese=True,
        ))
        reply = (result.response.text if result.response
                 else "抱歉，引擎当前不可用。")

    reply, _ = redact_pii(reply)

    # Store memory
    importance = 6 if use_reasoner else 4
    MEMORY.add(MemoryNode(
        content=f"用户说：{req.message}",
        user_id=user,
        type=MemoryType.EPISODIC,
        importance=importance,
        source="voice_capsule" if req.voice_input else "shortcuts",
    ))

    return {
        "reply": reply,
        "mode": "reasoner" if use_reasoner else "talker",
    }


class ChatRequest(BaseModel):
    message: str
    role_hint: str | None = None
    voice_input: bool = False
    conversation_id: str | None = None


# --- PWA manifest + icons ------------------------------------------------

@app.get("/manifest.json")
async def manifest() -> dict:
    """PWA manifest — enables 'Add to Home Screen' on mobile."""
    import json as _json
    return _json.loads(MANIFEST_JSON)


@app.get("/api/pwa/icon-{size}", response_class=Response)
async def pwa_icon(size: int = FastAPIPath(..., ge=1)) -> Response:
    """SVG icon at requested size — vector, scales to anything."""
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(
        content=get_icon_svg(size),
        media_type="image/svg+xml",
    )


# --- static console files (built from Next.js with output:export) ----------
_CONSOLE_DIR = Path(__file__).parent.parent / "console_static"
if _CONSOLE_DIR.exists():
    from starlette.responses import RedirectResponse

    @app.get("/console")
    async def console_redirect() -> RedirectResponse:
        """Redirect /console → /console/ so StaticFiles handles SPA routes."""
        return RedirectResponse(url="/console/", status_code=301)

    # StaticFiles with html=True serves:
    #   /console/ → index.html
    #   /console/_next/static/... → JS/CSS/chunks
    #   /console/dashboard, /console/brain etc → index.html (SPA fallback)
    app.mount("/console", StaticFiles(
        directory=str(_CONSOLE_DIR),
        html=True,
    ), name="console")


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """Serve the self-contained chat web page at the root URL."""
    return CHAT_HTML


# ── Auth: register / login ─────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
async def auth_register(req: AuthRequest) -> dict:
    """Register a new user account. Returns a token for immediate login."""
    try:
        user = USER_STORE.create_user(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
    }


@app.post("/api/auth/login")
async def auth_login(req: AuthRequest) -> dict:
    """Login with username + password. Returns a fresh token."""
    user = USER_STORE.verify_user(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
    }


@app.get("/api/auth/me")
async def auth_me(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Get current user info from token."""
    user_id = _auth(x_api_key, x_sunday_token)
    user = USER_STORE.get_user_by_id(user_id)
    if user is not None:
        return {"user_id": user.id, "username": user.username, "created_at": user.created_at}
    # Legacy API key user
    return {"user_id": user_id, "username": "admin"}


@app.get("/api/version")
async def version_info() -> dict:
    """Return the current Sunday OS version + changelog pointer."""
    parts = _version_str.replace("-dev", "").replace("-alpha", "").replace("-beta", "").split(".")
    return {
        "version": _version_str,
        "phase": "Phase 1 · ~90%",
        "changelog": "CHANGELOG.md",
        "major": int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0,
        "minor": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
        "patch": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
    }


@app.get("/health")
async def health() -> dict:
    from .memory.embedding import embedding_dim as edim
    return {
        "status": "ok",
        "version": _version_str,
        "engines": [e.id for e in ENGINES],
        "memory_nodes": len(MEMORY.all()),
        "conversation_count": CONV.count(),
        "embedder": "semantic" if _has_semantic else "hash",
        "embedding_dim": edim(),
    }


@app.get("/api/stats/dashboard")
async def dashboard_stats(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Real-time dashboard data — replaces frontend mock values."""
    user_id = _auth(x_api_key, x_sunday_token)
    avg_lat = (runtime.total_latency_ms / runtime.call_count
               if runtime.call_count > 0 else 0)
    return {
        "messages_today": runtime.messages_today,
        "model_calls": runtime.calls_today,
        "tokens_used": runtime.tokens_today,
        "cost_today": round(runtime.cost_today, 4),
        "memory_nodes": len(MEMORY.all()),
        "avg_latency_ms": round(avg_lat, 1),
        "active_tools": len(SKILLS.list()),
        "engines": [
            {"id": e.id, "calls": runtime.engine_calls.get(e.id, 0),
             "strong": e.caps.strong_reasoning, "local": e.caps.local}
            for e in ENGINES
        ],
        "conv_count": CONV.count(),
        "reflect_count": sum(
            1 for n in MEMORY.all() if n.type.value == "reflection"
        ),
        "experience_count": sum(
            1 for n in MEMORY.all() if n.type.value == "experience"
        ),
        "recent_events": runtime.recent_events[:8],
    }


@app.get("/api/debug/overview")
async def debug_overview(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Unified debug overview — all module states in one call.

    Intended as the first thing to check when something breaks.
    Returns a snapshot of every subsystem's runtime state.
    """
    user_id = _auth(x_api_key, x_sunday_token)
    from .memory.embedding import embedding_dim as edim
    return {
        "server": {
            "status": "ok",
            "python": __import__("sys").version,
        },
        "engines": {
            "count": len(ENGINES),
            "list": [e.id for e in ENGINES],
            "has_semantic_embedder": _has_semantic,
            "embedding_dim": edim(),
        },
        "memory": {
            "db_type": "sqlite" if isinstance(MEMORY, SQLiteMemoryStore) else "memory",
            "total_nodes": len(MEMORY.all()),
            "by_type": {str(k.value): sum(1 for n in MEMORY.all() if n.type == k)
                        for k in MemoryType},
            "embedder": "semantic" if _has_semantic else "hash",
        },
        "conversations": {
            "count": CONV.count(),
        },
        "skills": {
            "count": len(SKILLS.list()),
            "categories": SKILLS.categories(),
            "list": [{"name": s.name, "category": s.category, "risk": s.risk, "usage": s.usage_count}
                     for s in SKILLS.list()],
        },
        "usage": {
            "messages_today": runtime.messages_today,
            "calls_today": runtime.calls_today,
            "tokens_today": runtime.tokens_today,
            "cost_today": round(runtime.cost_today, 6),
            "avg_latency_ms": round(
                runtime.total_latency_ms / runtime.call_count, 1
            ) if runtime.call_count > 0 else 0,
        },
        "reflection": {
            "count": sum(
                1 for n in MEMORY.all() if n.type == MemoryType.REFLECTION
            ),
            "session_importance": dict(runtime.session_importance),
        },
        "checks": {
            "db_accessible": isinstance(MEMORY, SQLiteMemoryStore) and
                MEMORY.get("__nonexistent__") is None,
            "engines_available": len(ENGINES) > 0,
            "memory_working": len(MEMORY.all()) >= 0,
        },
    }


@app.get("/api/debug/env")
async def debug_env(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Diagnostic: report WHICH engine-related env vars the running process can
    see — names + presence + value length only. NEVER returns the secret value.
    Auth-gated. Remove or ignore once diagnosis is done."""
    user_id = _auth(x_api_key, x_sunday_token)
    watched = [
        "SUNDAY_API_KEY", "SUNDAY_ALLOW_MOCK", "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL", "QWEN_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "CUSTOM_API_KEY", "CUSTOM_BASE_URL",
        "CUSTOM_MODEL", "CUSTOM_MODEL_REASONER",
    ]
    seen = {}
    for name in watched:
        v = os.getenv(name)
        seen[name] = {"present": v is not None, "length": len(v) if v else 0}
    # also list any env var NAME that looks key-ish, to catch typos (names only)
    keyish = sorted(
        n for n in os.environ
        if any(tok in n.upper() for tok in ("KEY", "DEEPSEEK", "SUNDAY", "QWEN", "MOCK", "ANTHROPIC"))
    )
    return {"watched": seen, "keyish_names_present": keyish, "engines_built": [e.id for e in ENGINES]}


@app.get("/api/debug/routing")
async def debug_routing(msg: str = "你好",
                         x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Test router: which engine would answer this message RIGHT NOW?

    Shows the full decision tree — eligible engines, scores, which one
    gets picked first, and which fallback chain. Also makes a single test
    call to verify the chosen engine actually works.

    Query params:
      msg  — test message to route (default: "你好")
    """
    user_id = _auth(x_api_key, x_sunday_token)

    messages = [
        EngineMessage(role="system", content="你是一个AI助手，用中文回答。"),
        EngineMessage(role="user", content=msg),
    ]
    from .cognition.dispatch import needs_reasoner
    complexity = Complexity.L3_DEEP if needs_reasoner("debug", msg) else Complexity.L2_DAILY
    ranked, trace = ROUTER.plan(CognitiveRequest(
        messages=messages, complexity=complexity, prefer_chinese=True))

    # Try the first engine to verify it actually works
    test_result = None
    if ranked:
        import time as _time
        t0 = _time.monotonic()
        try:
            resp = await ranked[0].complete(messages, temperature=0.7)
            test_result = {
                "engine": ranked[0].id,
                "model": getattr(ranked[0], "_model", "?"),
                "base_url": getattr(ranked[0], "_base_url", "?"),
                "reply": resp.text[:200],
                "latency_ms": round((_time.monotonic() - t0) * 1000, 1),
                "tokens": resp.prompt_tokens + resp.completion_tokens,
            }
            log.engine_call(ranked[0].id, test_result["latency_ms"],
                          resp.prompt_tokens, resp.completion_tokens, 0,
                          model=test_result["model"])
        except Exception as exc:
            test_result = {
                "engine": ranked[0].id,
                "model": getattr(ranked[0], "_model", "?"),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                "latency_ms": round((_time.monotonic() - t0) * 1000, 1),
            }
            log.engine_error(ranked[0].id, type(exc).__name__,
                           f"{type(exc).__name__}: {str(exc)[:300]}")

    return {
        "test_message": msg,
        "complexity": int(complexity),
        "all_engines": [{
            "id": e.id,
            "model": getattr(e, "_model", "?"),
            "base_url": getattr(e, "_base_url", "?"),
            "quality": e.caps.quality,
            "primary": e.caps.primary,
            "caps": {
                "function_calling": e.caps.function_calling,
                "strong_reasoning": e.caps.strong_reasoning,
                "max_context": e.caps.max_context,
                "languages": list(e.caps.languages),
            },
            "price_in": e.price_in,
            "price_out": e.price_out,
        } for e in ENGINES],
        "eligible": trace.candidates,
        "scores": trace.scores,
        "chosen": trace.chosen,
        "reason": trace.reason,
        "fallback_chain": [e.id for e in ranked[1:]] if len(ranked) > 1 else [],
        "test_call": test_result,
    }


@app.get("/api/skills")
async def skills(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """List all registered skills with categories and usage stats."""
    user_id = _auth(x_api_key, x_sunday_token)
    return SKILLS.summary()


@app.get("/api/persona")
async def persona_view(reload: bool = False,
                       x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """View Sunday's current persona (from persona.yaml).

    Set ?reload=true to hot-reload from disk without restarting.
    """
    user_id = _auth(x_api_key, x_sunday_token)
    data = reload_persona() if reload else load_persona()
    return {
        "version": persona_version(),
        "persona": data,
        "reloaded": reload,
    }


# ── Feedback & Preferences (ADR-012) ──────────────────────────────────

@app.get("/api/preferences")
async def get_prefs(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Return the current user's preference profile."""
    user_id = _auth(x_api_key, x_sunday_token)
    user_id = user_id
    prefs = get_user_preferences(user_id, PREF_STORE)
    return {
        "user_id": user_id,
        "style": prefs.style if prefs else "",
        "topics": prefs.topics if prefs else {},
        "history": prefs.history[-10:] if prefs else [],
    }


class FeedbackRequest(BaseModel):
    rating: int  # 1 = 👍, -1 = 👎
    feedback_text: str = ""
    engine_id: str = ""
    msg_preview: str = ""  # first 60 chars of the AI reply


@app.post("/api/feedback")
async def post_feedback(req: FeedbackRequest,
                         x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Submit feedback on a reply. Adjusts quality score and parses NL feedback."""
    user_id = _auth(x_api_key, x_sunday_token)

    # 1. Adjust engine quality (immediate, lightweight)
    if req.engine_id:
        for e in ENGINES:
            if e.id == req.engine_id:
                delta = 0.01 if req.rating > 0 else -0.02
                e.caps.quality = max(0.1, min(1.0, e.caps.quality + delta))
                break

    # 2. Parse natural-language feedback (async, optional)
    parsed = {}
    if req.feedback_text.strip():
        try:
            parsed = await parse_feedback(req.feedback_text, ROUTER)
            # Apply parsed preferences
            if parsed.get("action") in ("prompt_inject", "both"):
                prefs = PREF_STORE.get(user_id)
                if parsed.get("dimension") == "style" and parsed.get("style_value"):
                    prefs.style = parsed["summary"]
                if parsed.get("dimension") == "topic" and parsed.get("topic_preference"):
                    prefs.topics[parsed["topic"]] = parsed["topic_preference"]
                prefs.add_feedback(req.feedback_text, req.rating,
                                  req.engine_id, parsed.get("summary", ""))
                PREF_STORE.save(prefs)
        except Exception:
            pass  # NL parsing is best-effort; never block feedback

    # 3. Log to feedback_log (best-effort, don't crash on DB errors)
    try:
        PREF_STORE.log_feedback(
            user_id, req.msg_preview, req.engine_id,
            req.rating, req.feedback_text, parsed)
    except Exception:
        pass

    return {
        "rating": req.rating,
        "engine_adjusted": req.engine_id,
        "parsed_feedback": parsed,
    }


@app.post("/api/preferences/update")
async def update_prefs(body: dict,
                        x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Directly set a preference value via API (for settings UI)."""
    user_id = _auth(x_api_key, x_sunday_token)
    user_id = user_id
    prefs = PREF_STORE.get(user_id)

    if "style" in body:
        prefs.style = body["style"]
    if "topic_prefs" in body:
        for topic, pref in body["topic_prefs"].items():
            prefs.topics[topic] = pref
    if "engine_prefs" in body:
        prefs.engine_prefs.update(body["engine_prefs"])

    PREF_STORE.save(prefs)
    return {"user_id": user_id, "style": prefs.style, "topics": prefs.topics}


class EmpathyRequest(BaseModel):
    message: str


@app.post("/api/debug/context")
async def debug_context(req: EmpathyRequest,
                        x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Debug endpoint — see what context the ContextBuilder assembles."""
    user_id = _auth(x_api_key, x_sunday_token)
    user = user_id
    assembled = await build_context(req.message, user, MEMORY, ROUTER)
    return {
        "message": req.message,
        "context": assembled.to_prompt_section(),
        "profile_chars": len(assembled.profile),
        "history_chars": len(assembled.topic_history),
        "reflections_chars": len(assembled.reflections),
        "total_chars": assembled.total_chars,
        "close_to_cap": assembled.total_chars > 2400,
    }


@app.post("/api/empathy/analyze")
async def empathy_analyze_endpoint(req: EmpathyRequest,
                                   x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Debug endpoint — analyze a single message for emotion and intent.

    Returns the UU emotional snapshot + IRG empathy guidance that would be
    injected into the system prompt.
    """
    user_id = _auth(x_api_key, x_sunday_token)
    snapshot, guidance = await run_empathy_pipeline(req.message, ROUTER)
    return {
        "message": req.message,
        "emotion": snapshot.primary_emotion,
        "intensity": snapshot.intensity,
        "secondary_emotion": snapshot.secondary_emotion,
        "dialogue_act": snapshot.dialogue_act,
        "topic": snapshot.topic,
        "confidence": snapshot.confidence,
        "empathy_guidance": guidance,
        "summary_zh": snapshot.to_zh(),
    }


@app.get("/api/engines")
async def engines() -> dict:
    return {
        "engines": [
            {
                "id": e.id,
                "strong_reasoning": e.caps.strong_reasoning,
                "function_calling": e.caps.function_calling,
                "local": e.caps.local,
                "quality": e.caps.quality,
                "primary": e.caps.primary,
                "price_in": e.price_in,
                "price_out": e.price_out,
            }
            for e in ENGINES
        ]
    }


@app.post("/api/chat")
async def chat(req: ChatRequest, x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)

    # L6 input guardrails
    try:
        check_input(req.message)
    except GuardrailTripwire as t:
        raise HTTPException(status_code=400, detail=f"guardrail:{t.layer}:{t.reason}")

    # Build topic-aware cross-session context (Engram/GAM/APEX-MEM)
    assembled = await build_context(req.message, user_id, MEMORY, ROUTER)
    context_block = assembled.to_prompt_section() if assembled else ""

    # Empathy: UU analysis → IRG guidance
    empathy_snapshot, empathy_guidance = await run_empathy_pipeline(
        req.message, ROUTER,
    )

    # Resolve user early: needed for preference injection + logging
    user_id = user_id

    # Dispatch: System 1 vs System 2
    belief = BeliefState(user_id=user_id)
    use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)
    complexity = Complexity.L3_DEEP if use_reasoner else Complexity.L2_DAILY

    system_prompt = build_prompt_with_prefs(user_id, PREF_STORE)
    if empathy_guidance:
        system_prompt += f"\n\n[当前互动]\n{empathy_guidance}"
    if context_block:
        system_prompt += f"\n\n{context_block}"

    react_steps = []
    log.chat_request(user_id, len(req.message),
                     "reasoner" if use_reasoner else "talker",
                     int(complexity))

    if use_reasoner:
        # System 2: ReAct loop — Thought → Action → Observation
        react = ReActLoop(router=ROUTER, tools=TOOLS, memory_store=MEMORY, skills=SKILLS,
                          max_steps=7, timeout_s=120.0)
        react_result = await react.run(
            system_prompt=system_prompt,
            user_message=req.message,
            user_id=user_id,
        )
        reply = react_result.answer
        react_steps = [
            {
                "type": s.type, "content": s.content,
                "tool_name": s.tool_name, "tool_input": s.tool_input,
                "tool_output": s.tool_output, "latency_ms": s.latency_ms,
            }
            for s in react_result.steps
        ]
        # Use a synthetic trace for the ReAct run
        trace = {
            "candidates": [], "scores": {}, "reason": "react_loop",
            "fallbacks_used": [], "usage": {}, "latency_ms": react_result.total_latency_ms,
            "errors": {},
        }
        chosen_engine = "react-loop"
    else:
        # System 1: single completion
        messages = [
            EngineMessage(role="system", content=system_prompt),
            EngineMessage(role="user", content=req.message),
        ]
        # Pre-route log: what the router sees
        ranked, plan_trace = ROUTER.plan(CognitiveRequest(
            messages=messages, complexity=complexity, prefer_chinese=True))
        log.route_decision(int(complexity), plan_trace.candidates,
                          plan_trace.scores, plan_trace.chosen,
                          plan_trace.reason, req.message)

        result = await ROUTER.route(CognitiveRequest(
            messages=messages,
            complexity=complexity,
            prefer_chinese=True,
        ))

        if result.response is None:
            errors = result.trace.errors
            log.chat_all_engines_failed(user_id, errors)
            if errors:
                first_err = next(iter(errors.values()))
                reply = "引擎暂时不可用，请稍后重试。"
            else:
                reply = "引擎暂时不可用，请稍后重试。"
        else:
            reply, _ = redact_pii(result.response.text)

        trace = {
            "candidates": result.trace.candidates,
            "scores": result.trace.scores,
            "reason": result.trace.reason,
            "fallbacks_used": result.trace.fallbacks_used,
            "usage": result.trace.usage,
            "latency_ms": result.trace.latency_ms,
            "errors": result.trace.errors,
        }
        chosen_engine = result.trace.chosen or "none"

        # Post-route log: what actually happened
        log.chat_response(user_id, chosen_engine,
                         trace.get("latency_ms", 0), len(reply or ""),
                         trace.get("usage", {}).get("prompt_tokens", 0) +
                         trace.get("usage", {}).get("completion_tokens", 0),
                         trace.get("usage", {}).get("cost_usd", 0))

    # Record usage stats
    if use_reasoner:
        _record_stats("react-loop", react_result.total_latency_ms, 0, 0, 0,
                      event=f"ReAct: {len(react_steps)} steps → {reply[:50]}...")
    else:
        latency = trace.get("latency_ms", 0)
        usage = trace.get("usage", {})
        _record_stats(chosen_engine, latency,
                      usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                      usage.get("cost_usd", 0))

    # --- conversation session: auto-create or append ---
    conv_id = req.conversation_id
    if not conv_id or not CONV.get(conv_id):
        conv = CONV.create(user_id)
        conv_id = conv.id
    CONV.add_message(conv_id, "user", req.message)
    CONV.add_message(conv_id, "assistant", reply,
                     engine=chosen_engine,
                     system="reasoner" if use_reasoner else "talker",
                     trace={
                         "engine": chosen_engine,
                         "system": "reasoner" if use_reasoner else "talker",
                         "complexity": int(complexity),
                         "errors": trace.get("errors", {}),
                         "latency_ms": trace.get("latency_ms", 0),
                         "react_steps": react_steps,
                     })

    # Memory write with LLM importance scoring (async, non-blocking)
    # Uses the cheapest engine for scoring; falls back to 6/4 heuristic
    try:
        _score_engine = next(
            (e for e in ENGINES if not e.caps.strong_reasoning), ENGINES[0]
        ) if ENGINES else None
        if _score_engine and _has_semantic:
            importance = await score_importance(req.message, _score_engine)
            if importance == 5:  # fallback — use heuristic instead
                importance = 6 if use_reasoner else 4
        else:
            importance = 6 if use_reasoner else 4
    except Exception:
        importance = 6 if use_reasoner else 4

    MEMORY.add(MemoryNode(
        content=f"用户说：{req.message}",
        user_id=user_id,
        type=MemoryType.EPISODIC,
        importance=importance,
        source="voice_capsule" if req.voice_input else "chat",
    ))

    # -- auto-trigger reflection if importance threshold crossed ---
    runtime.session_importance[user_id] = runtime.session_importance.get(user_id, 0) + importance
    schedule_reflection(MEMORY, user_id, ROUTER,
                        session_importance=runtime.session_importance[user_id])

    return {
        "reply": reply,
        "bursts": burst_split(reply),
        "conversation_id": conv_id,
        "engine": chosen_engine,
        "system": "reasoner" if use_reasoner else "talker",
        "complexity": int(complexity),
        "risk": risk_level(req.message),
        "memory_hits": len(assembled.topic_history) if assembled else 0,
        "react_steps": react_steps,
        "trace": trace,
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest,
                      x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")):
    """SSE streaming chat — each ReAct step is pushed as an event.

    For System 1 (talker): streams the text chunk by chunk.
    For System 2 (reasoner): pushes each Thought/Action/Observation as SSE.
    """
    import json as _json

    user_id = _auth(x_api_key, x_sunday_token)

    async def _event_stream():
        # Input guardrails
        try:
            check_input(req.message)
        except GuardrailTripwire as t:
            yield f"data: {_json.dumps({'type': 'error', 'content': str(t.detail)})}\n\n"
            return

        # Memory retrieval
        assembled = await build_context(req.message, user_id, MEMORY, ROUTER)
        context_block = assembled.to_prompt_section() if assembled else ""

        # Empathy: UU analysis → IRG guidance
        empathy_snapshot, empathy_guidance = await run_empathy_pipeline(
            req.message, ROUTER,
        )

        # Dispatch
        stream_user_id = user_id
        belief = BeliefState(user_id=stream_user_id)
        use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)

        system_prompt = build_prompt_with_prefs(stream_user_id, PREF_STORE)
        if empathy_guidance:
            system_prompt += f"\n\n[当前互动]\n{empathy_guidance}"
        if context_block:
            system_prompt += f"\n\n{context_block}"

        conv_id = req.conversation_id
        if not conv_id or not CONV.get(conv_id):
            conv = CONV.create(user_id)
            conv_id = conv.id

        if use_reasoner:
            # System 2: ReAct loop → stream each step
            react = ReActLoop(router=ROUTER, tools=TOOLS, memory_store=MEMORY, skills=SKILLS,
                              max_steps=7, timeout_s=120.0)
            react_result = await react.run(
                system_prompt=system_prompt,
                user_message=req.message,
                user_id=user_id,
            )
            for s in react_result.steps:
                yield f"data: {_json.dumps({'type': s.type, 'content': s.content, 'tool_name': s.tool_name, 'tool_input': s.tool_input, 'tool_output': s.tool_output, 'latency_ms': s.latency_ms})}\n\n"
            reply = react_result.answer
            engine = "react-loop"
            system_label = "reasoner"
        else:
            # System 1: stream word by word
            messages = [
                EngineMessage(role="system", content=system_prompt),
                EngineMessage(role="user", content=req.message),
            ]
            result = await ROUTER.route(CognitiveRequest(
                messages=messages, complexity=Complexity.L2_DAILY,
                prefer_chinese=True,
            ))
            reply = result.response.text if result.response else "抱歉，引擎暂时不可用。"
            engine = result.trace.chosen or "none"
            system_label = "talker"
            # Stream chunks
            words = reply.split()
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3])
                yield f"data: {_json.dumps({'type': 'text', 'content': chunk + ' '})}\n\n"

        # Done event — include bursts for multi-bubble rendering
        done_payload = {
            "type": "done",
            "conversation_id": conv_id,
            "engine": engine,
            "system": system_label,
            "reply": reply,
            "bursts": burst_split(reply),
        }
        yield f"data: {_json.dumps(done_payload)}\n\n"

        # Persist conversation
        CONV.add_message(conv_id, "user", req.message)
        CONV.add_message(conv_id, "assistant", reply,
                         engine=engine, system=system_label)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# --- conversation endpoints ---------------------------------------------------

class ConversationCreateRequest(BaseModel):
    title: str = "新对话"


@app.post("/api/conversations")
async def conversation_create(req: ConversationCreateRequest,
                              x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    conv = CONV.create(user_id, req.title)
    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "message_count": len(conv.messages),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@app.get("/api/conversations")
async def conversation_list(
        x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    convs = CONV.list(user_id)
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "message_count": len(c.messages),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]
    }


@app.get("/api/conversations/{conv_id}")
async def conversation_get(conv_id: str,
                           x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    conv = CONV.get(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    if conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "messages": conv.messages,
        "message_count": len(conv.messages),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@app.delete("/api/conversations/{conv_id}")
async def conversation_delete(conv_id: str,
                              x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    conv = CONV.get(conv_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"deleted": CONV.delete(conv_id)}


class ConversationRenameRequest(BaseModel):
    title: str


@app.put("/api/conversations/{conv_id}/title")
async def conversation_rename(conv_id: str, req: ConversationRenameRequest,
                              x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    conv = CONV.get(conv_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    ok = CONV.rename(conv_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"id": conv_id, "title": req.title}


class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "episodic"
    importance: int = 5


@app.post("/api/memory/store")
async def memory_store(req: MemoryStoreRequest, x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    node = MEMORY.add(MemoryNode(
        content=req.content, user_id=user_id,
        type=MemoryType(req.memory_type), importance=req.importance,
    ))
    return {"id": node.id, "stored": True}


class MemorySearchRequest(BaseModel):
    query: str
    k: int = 12


@app.post("/api/memory/search")
async def memory_search(req: MemorySearchRequest, x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    hits = MEMORY.retrieve(req.query, user_id=user_id, k=req.k)
    return {
        "results": [
            {
                "id": h.node.id, "content": h.node.content, "type": h.node.type,
                "score": round(h.score, 4),
                "components": {
                    "recency": round(h.recency, 3),
                    "importance": round(h.importance, 3),
                    "relevance": round(h.relevance, 3),
                },
            }
            for h in hits
        ]
    }


# --- reflection endpoints ---------------------------------------------------

class ReflectionRequest(BaseModel):
    force: bool = False  # skip threshold check if True


@app.post("/api/memory/reflect")
async def memory_reflect(req: ReflectionRequest,
                         x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Trigger reflection (L1→L2). Generative Agents two-step pipeline.

    Unless force=True, respects the importance threshold.
    Returns the generated insights with their evidence IDs.
    """
    user_id = _auth(x_api_key, x_sunday_token)
    from .memory.reflection import _should_reflect
    if not req.force and not _should_reflect(MEMORY, user_id):
        return {"triggered": False, "insights": [],
                "message": "Importance threshold not reached. Use force=true to override."}
    insights = await run_reflection(MEMORY, user_id, ROUTER)
    return {
        "triggered": True,
        "insights": insights,
        "message": f"Generated {len(insights)} reflections.",
    }


@app.get("/api/memory/reflections")
async def memory_reflections(limit: int = 20,
                             x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """List generated REFLECTION nodes for the current user, newest first."""
    user_id = _auth(x_api_key, x_sunday_token)
    from .memory.schema import MemoryType
    all_nodes = MEMORY.all(user_id)
    reflections = [
        n for n in all_nodes if n.type == MemoryType.REFLECTION
    ]
    reflections.sort(key=lambda n: n.created_at, reverse=True)
    return {
        "reflections": [
            {
                "id": r.id,
                "content": r.content,
                "evidence_ids": r.evidence_ids,
                "importance": r.importance,
                "created_at": r.created_at.isoformat(),
            }
            for r in reflections[:limit]
        ]
    }


@app.post("/api/memory/consolidate")
async def memory_consolidate(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Run L1 consolidation — archive expired low-importance memories.

    For the full L3 experience layer (merge + archive + extract + patterns),
    use POST /api/experience/run.
    """
    user_id = _auth(x_api_key, x_sunday_token)
    dropped = MEMORY.archive_expired(threshold=0.4)
    total = len(MEMORY.all())
    return {
        "dropped": dropped,
        "remaining": total,
        "message": f"Archived {dropped} expired memories. {total} remaining.",
    }


# --- experience layer endpoints (L2→L3) -------------------------------------

@app.post("/api/experience/run")
async def experience_run(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Run the full L3 Experience layer.

    Performs three operations from From Storage to Experience (2026):
    1. CONSOLIDATION — merge similar memories, archive expired, extract semantics
    2. PATTERN DETECTION — find repeating behavioral patterns → EXPERIENCE nodes
    3. PROCEDURAL PRIMITIVE — detect recurring tool sequences → skill proposals

    This is the nightly batch job for Sunday's cognitive evolution.
    Uses the current user's identity (derived from API key).
    """
    user_id = _auth(x_api_key, x_sunday_token)
    user = user_id
    result = await run_experience_layer(MEMORY, ROUTER, user)
    return {
        "user": user,
        "consolidation": result["consolidation"],
        "patterns_found": len(result["patterns"]),
        "patterns": result["patterns"],
        "primitives_found": len(result["primitives"]),
        "primitives": result["primitives"],
    }


@app.get("/api/experience/nodes")
async def experience_nodes(limit: int = 20,
                           x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """List EXPERIENCE nodes for the current user."""
    user_id = _auth(x_api_key, x_sunday_token)
    from .memory.schema import MemoryType
    all_nodes = MEMORY.all(user_id)
    exp_nodes = [n for n in all_nodes if n.type == MemoryType.EXPERIENCE]
    exp_nodes.sort(key=lambda n: n.created_at, reverse=True)
    return {
        "experiences": [
            {
                "id": n.id,
                "content": n.content,
                "source": n.source,
                "importance": n.importance,
                "evidence_ids": n.evidence_ids,
                "created_at": n.created_at.isoformat(),
            }
            for n in exp_nodes[:limit]
        ]
    }


@app.get("/api/memory/stats")
async def memory_stats(x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    """Return memory statistics — count by type, embedder info."""
    user_id = _auth(x_api_key, x_sunday_token)
    from .memory.embedding import embedding_dim as edim, embed as emb_fn
    all_nodes = MEMORY.all(user_id)
    by_type: dict[str, int] = {}
    for n in all_nodes:
        by_type[str(n.type.value)] = by_type.get(str(n.type.value), 0) + 1
    is_semantic = _has_semantic
    return {
        "total_nodes": len(all_nodes),
        "by_type": by_type,
        "embedder": "semantic" if is_semantic else "hash",
        "embedding_dim": edim(),
        "db_type": "sqlite" if isinstance(MEMORY, SQLiteMemoryStore) else "memory",
    }


@app.delete("/api/memory/{mem_id}")
async def memory_delete(mem_id: str, x_api_key: str | None = Header(default=None), x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token")) -> dict:
    user_id = _auth(x_api_key, x_sunday_token)
    node = MEMORY.get(mem_id)
    if node is None or node.user_id != user_id:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": MEMORY.delete(mem_id)}

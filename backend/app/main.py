"""SundayOS 3.0 backend — FastAPI entry.

Wires the cognitive engine router, memory, dual-process dispatch, guardrails,
and persona into a chat endpoint. Runs offline in mock mode (no keys needed).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from .webchat import CHAT_HTML

from .cognition.belief import BeliefState
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
from .cognition.tools import TOOLS, SKILLS, _memory_search_handler
from .cognition.react_loop import ReActLoop, ReActResult

load_dotenv(override=True)

app = FastAPI(title="SundayOS 3.0", version="3.0.0-alpha")

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

# --- singletons (start-simple: in-process; swap for DI/DB in production) ----
ENGINES = build_engines()
ROUTER = CognitiveRouter(ENGINES)
# Use SQLite-backed memory (persists across restarts). Falls back to in-memory
# if db_path is not set or the SQLite store can't be opened.
_db_path = os.getenv("SUNDAY_DB_PATH", "./sunday.db")
try:
    MEMORY = SQLiteMemoryStore(db_path=_db_path)
except Exception:
    MEMORY = MemoryStore()
CONV = ConversationStore()
API_KEY = os.getenv("SUNDAY_API_KEY", "change-me-in-production")
# Track per-user session importance for reflection auto-trigger.
# Reset on server restart (acceptable — reflection will catch up then).
_SESSION_IMPORTANCE: dict[str, int] = {}

# Auto-upgrade embedder to semantic if API keys are configured AND the provider
# actually supports embeddings (DeepSeek currently does not). Falls back to the
# hash embedder for offline / no-key scenarios.
_has_semantic = False
try:
    _has_semantic = auto_upgrade_embedder()
except Exception:
    pass  # hash embedder is always available

# --- usage stats (in-memory, resets on restart) ------------------------------
from collections import defaultdict
from datetime import datetime as _dt
_USAGE = {
    "messages_today": 0,
    "calls_today": 0,
    "tokens_today": 0,
    "cost_today": 0.0,
    "total_latency_ms": 0.0,
    "call_count": 0,
    "engine_calls": defaultdict(int),
    "recent_events": [],  # list of {time, event}
}

def _record_stats(engine_id: str | None, latency_ms: float,
                  prompt_tokens: int, completion_tokens: int, cost_usd: float,
                  event: str = "") -> None:
    _USAGE["messages_today"] += 1
    _USAGE["calls_today"] += 1
    _USAGE["tokens_today"] += prompt_tokens + completion_tokens
    _USAGE["cost_today"] += cost_usd
    _USAGE["total_latency_ms"] += latency_ms
    _USAGE["call_count"] += 1
    if engine_id:
        _USAGE["engine_calls"][engine_id] += 1
    if event:
        _USAGE["recent_events"].insert(0, {"time": _dt.now().isoformat(), "event": event})
        _USAGE["recent_events"] = _USAGE["recent_events"][:20]

PERSONA = (
    "你是 Sunday，一个温暖、克制、聪明的个人 AI 伙伴。理性但不冷漠，"
    "幽默但不轻浮。面对情绪优先共情，面对问题优先解决。称呼用户为『你』。"
)


def _auth(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


def _resolve_user(x_api_key: str | None) -> str:
    """Derive a stable user_id from the API Key.

    Same Key → same user_id across all devices (iPhone/PC/tablet).
    Different Key → completely isolated identity.

    Uses a truncated hash — stable, consistent, no personal info.
    """
    import hashlib
    raw = (x_api_key or "anonymous").encode("utf-8")
    return "user_" + hashlib.sha256(raw).hexdigest()[:16]


# --- iPhone Shortcuts endpoints ----------------------------------------------

class ShortcutChatRequest(BaseModel):
    message: str
    voice_input: bool = True


@app.post("/api/shortcuts/chat")
async def shortcuts_chat(req: ShortcutChatRequest,
                         x_api_key: str | None = Header(default=None)):
    """iPhone Shortcuts / Siri endpoint.

    Accepts a message, runs the full Sunday pipeline, returns a compact
    voice-friendly response. Designed to be used with the "Get Contents of URL"
    action in Apple Shortcuts.
    """
    _auth(x_api_key)

    # Run the same pipeline as /api/chat but with a compact response
    try:
        check_input(req.message)
    except GuardrailTripwire as t:
        raise HTTPException(status_code=400, detail=f"guardrail:{t.layer}:{t.reason}")

    user = _resolve_user(x_api_key)

    hits = MEMORY.retrieve(req.message, user_id=user, k=4)
    context = "\n".join(f"- {h.node.content}" for h in hits)

    use_reasoner = needs_reasoner("chat", req.message,
                                  BeliefState(user_id=user))
    system_prompt = PERSONA
    if context:
        system_prompt += f"\n\n[相关记忆]\n{context}"

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


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """Serve the self-contained chat web page at the root URL."""
    return CHAT_HTML


@app.get("/health")
async def health() -> dict:
    from .memory.embedding import embedding_dim as edim
    return {
        "status": "ok",
        "engines": [e.id for e in ENGINES],
        "memory_nodes": len(MEMORY.all()),
        "conversation_count": CONV.count(),
        "embedder": "semantic" if _has_semantic else "hash",
        "embedding_dim": edim(),
    }


@app.get("/api/stats/dashboard")
async def dashboard_stats(x_api_key: str | None = Header(default=None)) -> dict:
    """Real-time dashboard data — replaces frontend mock values."""
    _auth(x_api_key)
    avg_lat = (_USAGE["total_latency_ms"] / _USAGE["call_count"]
               if _USAGE["call_count"] > 0 else 0)
    return {
        "messages_today": _USAGE["messages_today"],
        "model_calls": _USAGE["calls_today"],
        "tokens_used": _USAGE["tokens_today"],
        "cost_today": round(_USAGE["cost_today"], 4),
        "memory_nodes": len(MEMORY.all()),
        "avg_latency_ms": round(avg_lat, 1),
        "active_tools": len(SKILLS.list()),
        "engines": [
            {"id": e.id, "calls": _USAGE["engine_calls"].get(e.id, 0),
             "strong": e.caps.strong_reasoning, "local": e.caps.local}
            for e in ENGINES
        ],
        "conv_count": CONV.count(),
        "reflect_count": sum(
            1 for n in MEMORY.all() if n.type.value == "reflection"
        ),
        "recent_events": _USAGE["recent_events"][:8],
    }


@app.get("/api/debug/overview")
async def debug_overview(x_api_key: str | None = Header(default=None)) -> dict:
    """Unified debug overview — all module states in one call.

    Intended as the first thing to check when something breaks.
    Returns a snapshot of every subsystem's runtime state.
    """
    _auth(x_api_key)
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
            "messages_today": _USAGE["messages_today"],
            "calls_today": _USAGE["calls_today"],
            "tokens_today": _USAGE["tokens_today"],
            "cost_today": round(_USAGE["cost_today"], 6),
            "avg_latency_ms": round(
                _USAGE["total_latency_ms"] / _USAGE["call_count"], 1
            ) if _USAGE["call_count"] > 0 else 0,
        },
        "reflection": {
            "count": sum(
                1 for n in MEMORY.all() if n.type == MemoryType.REFLECTION
            ),
            "session_importance": dict(_SESSION_IMPORTANCE),
        },
        "checks": {
            "db_accessible": isinstance(MEMORY, SQLiteMemoryStore) and
                MEMORY.get("__nonexistent__") is None,
            "engines_available": len(ENGINES) > 0,
            "memory_working": len(MEMORY.all()) >= 0,
        },
    }


@app.get("/api/debug/env")
async def debug_env(x_api_key: str | None = Header(default=None)) -> dict:
    """Diagnostic: report WHICH engine-related env vars the running process can
    see — names + presence + value length only. NEVER returns the secret value.
    Auth-gated. Remove or ignore once diagnosis is done."""
    _auth(x_api_key)
    watched = [
        "SUNDAY_API_KEY", "SUNDAY_ALLOW_MOCK", "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL", "QWEN_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
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


@app.get("/api/skills")
async def skills(x_api_key: str | None = Header(default=None)) -> dict:
    """List all registered skills with categories and usage stats."""
    _auth(x_api_key)
    return SKILLS.summary()


@app.get("/api/engines")
async def engines() -> dict:
    return {
        "engines": [
            {
                "id": e.id,
                "strong_reasoning": e.caps.strong_reasoning,
                "function_calling": e.caps.function_calling,
                "local": e.caps.local,
                "price_in": e.price_in,
                "price_out": e.price_out,
            }
            for e in ENGINES
        ]
    }


@app.post("/api/chat")
async def chat(req: ChatRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)

    # L6 input guardrails
    try:
        check_input(req.message)
    except GuardrailTripwire as t:
        raise HTTPException(status_code=400, detail=f"guardrail:{t.layer}:{t.reason}")

    # Retrieve memory context (System 1 view)
    hits = MEMORY.retrieve(req.message, user_id=_resolve_user(x_api_key), k=6)
    context = "\n".join(f"- {h.node.content}" for h in hits)

    # Dispatch: System 1 vs System 2
    belief = BeliefState(user_id=_resolve_user(x_api_key))
    use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)
    complexity = Complexity.L3_DEEP if use_reasoner else Complexity.L2_DAILY

    system_prompt = PERSONA
    if context:
        system_prompt += f"\n\n[相关记忆]\n{context}"

    react_steps = []
    if use_reasoner:
        # System 2: ReAct loop — Thought → Action → Observation
        react = ReActLoop(router=ROUTER, tools=TOOLS, memory_store=MEMORY, skills=SKILLS,
                          max_steps=7, timeout_s=120.0)
        react_result = await react.run(
            system_prompt=system_prompt,
            user_message=req.message,
            user_id=_resolve_user(x_api_key),
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
        # System 1: single completion (unchanged)
        messages = [
            EngineMessage(role="system", content=system_prompt),
            EngineMessage(role="user", content=req.message),
        ]
        result = await ROUTER.route(CognitiveRequest(
            messages=messages,
            complexity=complexity,
            prefer_chinese=True,
        ))

        if result.response is None:
            errors = result.trace.errors
            if errors:
                first_err = next(iter(errors.values()))
                reply = f"[引擎调用失败] {first_err}"
            else:
                reply = "所有引擎当前不可用，请稍后重试。"
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
        chosen_engine = result.trace.chosen or "none"  # L3 output PII filter

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
        conv = CONV.create(_resolve_user(x_api_key))
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
        user_id=_resolve_user(x_api_key),
        type=MemoryType.EPISODIC,
        importance=importance,
        source="voice_capsule" if req.voice_input else "chat",
    ))

    # -- auto-trigger reflection if importance threshold crossed ---
    _SESSION_IMPORTANCE[_resolve_user(x_api_key)] = _SESSION_IMPORTANCE.get(_resolve_user(x_api_key), 0) + importance
    schedule_reflection(MEMORY, _resolve_user(x_api_key), ROUTER,
                        session_importance=_SESSION_IMPORTANCE[_resolve_user(x_api_key)])

    return {
        "reply": reply,
        "conversation_id": conv_id,
        "engine": chosen_engine,
        "system": "reasoner" if use_reasoner else "talker",
        "complexity": int(complexity),
        "risk": risk_level(req.message),
        "memory_hits": len(hits),
        "react_steps": react_steps,
        "trace": trace,
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest,
                      x_api_key: str | None = Header(default=None)):
    """SSE streaming chat — each ReAct step is pushed as an event.

    For System 1 (talker): streams the text chunk by chunk.
    For System 2 (reasoner): pushes each Thought/Action/Observation as SSE.
    """
    import json as _json

    _auth(x_api_key)

    async def _event_stream():
        # Input guardrails
        try:
            check_input(req.message)
        except GuardrailTripwire as t:
            yield f"data: {_json.dumps({'type': 'error', 'content': str(t.detail)})}\n\n"
            return

        # Memory retrieval
        hits = MEMORY.retrieve(req.message, user_id=_resolve_user(x_api_key), k=6)
        context = "\n".join(f"- {h.node.content}" for h in hits)

        # Dispatch
        belief = BeliefState(user_id=_resolve_user(x_api_key))
        use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)

        system_prompt = PERSONA
        if context:
            system_prompt += f"\n\n[相关记忆]\n{context}"

        conv_id = req.conversation_id
        if not conv_id or not CONV.get(conv_id):
            conv = CONV.create(_resolve_user(x_api_key))
            conv_id = conv.id

        if use_reasoner:
            # System 2: ReAct loop → stream each step
            react = ReActLoop(router=ROUTER, tools=TOOLS, memory_store=MEMORY, skills=SKILLS,
                              max_steps=7, timeout_s=120.0)
            react_result = await react.run(
                system_prompt=system_prompt,
                user_message=req.message,
                user_id=_resolve_user(x_api_key),
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

        # Done event
        yield f"data: {_json.dumps({'type': 'done', 'conversation_id': conv_id, 'engine': engine, 'system': system_label})}\n\n"

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
                              x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    conv = CONV.create(_resolve_user(x_api_key), req.title)
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
        x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    convs = CONV.list(_resolve_user(x_api_key))
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
                           x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    conv = CONV.get(conv_id)
    if conv is None:
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
                              x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    return {"deleted": CONV.delete(conv_id)}


class ConversationRenameRequest(BaseModel):
    title: str


@app.put("/api/conversations/{conv_id}/title")
async def conversation_rename(conv_id: str, req: ConversationRenameRequest,
                              x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    ok = CONV.rename(conv_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"id": conv_id, "title": req.title}


class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "episodic"
    importance: int = 5


@app.post("/api/memory/store")
async def memory_store(req: MemoryStoreRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    node = MEMORY.add(MemoryNode(
        content=req.content, user_id=_resolve_user(x_api_key),
        type=MemoryType(req.memory_type), importance=req.importance,
    ))
    return {"id": node.id, "stored": True}


class MemorySearchRequest(BaseModel):
    query: str
    k: int = 12


@app.post("/api/memory/search")
async def memory_search(req: MemorySearchRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    hits = MEMORY.retrieve(req.query, user_id=_resolve_user(x_api_key), k=req.k)
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
                         x_api_key: str | None = Header(default=None)) -> dict:
    """Trigger reflection (L1→L2). Generative Agents two-step pipeline.

    Unless force=True, respects the importance threshold.
    Returns the generated insights with their evidence IDs.
    """
    _auth(x_api_key)
    from .memory.reflection import _should_reflect
    if not req.force and not _should_reflect(MEMORY, _resolve_user(x_api_key)):
        return {"triggered": False, "insights": [],
                "message": "Importance threshold not reached. Use force=true to override."}
    insights = await run_reflection(MEMORY, _resolve_user(x_api_key), ROUTER)
    return {
        "triggered": True,
        "insights": insights,
        "message": f"Generated {len(insights)} reflections.",
    }


@app.get("/api/memory/reflections")
async def memory_reflections(limit: int = 20,
                             x_api_key: str | None = Header(default=None)) -> dict:
    """List generated REFLECTION nodes for the current user, newest first."""
    _auth(x_api_key)
    from .memory.schema import MemoryType
    all_nodes = MEMORY.all(_resolve_user(x_api_key))
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
async def memory_consolidate(x_api_key: str | None = Header(default=None)) -> dict:
    """Trigger memory consolidation — archive expired low-importance nodes.

    Runs archive_expired() which removes memories whose effective importance
    has decayed below the threshold. CRITICAL (10) and frozen nodes are
    never touched.
    """
    _auth(x_api_key)
    dropped = MEMORY.archive_expired(threshold=0.4)
    total = len(MEMORY.all())
    return {
        "dropped": dropped,
        "remaining": total,
        "message": f"Archived {dropped} expired memories. {total} remaining.",
    }


@app.get("/api/memory/stats")
async def memory_stats(x_api_key: str | None = Header(default=None)) -> dict:
    """Return memory statistics — count by type, embedder info."""
    _auth(x_api_key)
    from .memory.embedding import embedding_dim as edim, embed as emb_fn
    all_nodes = MEMORY.all()
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
async def memory_delete(mem_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    return {"deleted": MEMORY.delete(mem_id)}

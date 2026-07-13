"""SundayOS 3.0 backend — FastAPI entry.

Wires the cognitive engine router, memory, dual-process dispatch, guardrails,
and persona into a chat endpoint. Runs offline in mock mode (no keys needed).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .cognition.belief import BeliefState
from .cognition.dispatch import needs_reasoner, risk_level
from .engines.base import Complexity, EngineMessage
from .engines.registry import build_engines
from .engines.router import CognitiveRequest, CognitiveRouter
from .guardrails.pipeline import GuardrailTripwire, check_input, redact_pii
from .memory.schema import MemoryNode, MemoryType
from .memory.store import MemoryStore

load_dotenv()

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
MEMORY = MemoryStore()
API_KEY = os.getenv("SUNDAY_API_KEY", "change-me-in-production")

PERSONA = (
    "你是 Sunday，一个温暖、克制、聪明的个人 AI 伙伴。理性但不冷漠，"
    "幽默但不轻浮。面对情绪优先共情，面对问题优先解决。称呼用户为『你』。"
)


def _auth(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


class ChatRequest(BaseModel):
    message: str
    user_id: str
    role_hint: str | None = None
    voice_input: bool = False


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "engines": [e.id for e in ENGINES],
        "memory_nodes": len(MEMORY.all()),
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
    hits = MEMORY.retrieve(req.message, user_id=req.user_id, k=6)
    context = "\n".join(f"- {h.node.content}" for h in hits)

    # Dispatch: System 1 vs System 2
    belief = BeliefState(user_id=req.user_id)
    use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)
    complexity = Complexity.L3_DEEP if use_reasoner else Complexity.L2_DAILY

    system_prompt = PERSONA
    if context:
        system_prompt += f"\n\n[相关记忆]\n{context}"

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
        # graceful degradation — never "crash the mind"
        reply = "我现在思考有点慢，稍等一下再问我好吗？"
    else:
        reply, _ = redact_pii(result.response.text)  # L3 output PII filter

    # async-ish memory write (inline here for simplicity)
    MEMORY.add(MemoryNode(
        content=f"用户说：{req.message}",
        user_id=req.user_id,
        type=MemoryType.EPISODIC,
        importance=6 if use_reasoner else 4,
        source="voice_capsule" if req.voice_input else "chat",
    ))

    return {
        "reply": reply,
        "engine": result.trace.chosen,
        "system": "reasoner" if use_reasoner else "talker",
        "complexity": result.trace.complexity,
        "risk": risk_level(req.message),
        "memory_hits": len(hits),
        "trace": {
            "candidates": result.trace.candidates,
            "scores": result.trace.scores,
            "reason": result.trace.reason,
            "fallbacks_used": result.trace.fallbacks_used,
            "usage": result.trace.usage,
            "latency_ms": result.trace.latency_ms,
            "errors": result.trace.errors,
        },
    }


class MemoryStoreRequest(BaseModel):
    user_id: str
    content: str
    memory_type: str = "episodic"
    importance: int = 5


@app.post("/api/memory/store")
async def memory_store(req: MemoryStoreRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    node = MEMORY.add(MemoryNode(
        content=req.content, user_id=req.user_id,
        type=MemoryType(req.memory_type), importance=req.importance,
    ))
    return {"id": node.id, "stored": True}


class MemorySearchRequest(BaseModel):
    user_id: str
    query: str
    k: int = 12


@app.post("/api/memory/search")
async def memory_search(req: MemorySearchRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    hits = MEMORY.retrieve(req.query, user_id=req.user_id, k=req.k)
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


@app.delete("/api/memory/{mem_id}")
async def memory_delete(mem_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(x_api_key)
    return {"deleted": MEMORY.delete(mem_id)}

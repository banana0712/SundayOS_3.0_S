"""Debug router — diagnostic endpoints for troubleshooting."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from typing import TYPE_CHECKING

from ..deps import get_current_user, ctx
from ..engines.base import EngineMessage, Complexity
from ..engines.router import CognitiveRequest
from ..memory.sqlite_store import SQLiteMemoryStore
from ..memory.schema import MemoryType
from ..cognition.context_builder import build_context
from ..persona.empathy import run_empathy_pipeline
from ..log_engine import log
from .. import runtime

if TYPE_CHECKING:
    from ..deps import _Context

import os

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/overview")
async def debug_overview(user_id: str = Depends(get_current_user)) -> dict:
    """Unified debug overview — all module states in one call.

    Intended as the first thing to check when something breaks.
    Returns a snapshot of every subsystem's runtime state.
    """
    from ..memory.embedding import embedding_dim as edim

    return {
        "server": {
            "status": "ok",
            "python": __import__("sys").version,
        },
        "engines": {
            "count": len(ctx.engines),
            "list": [e.id for e in ctx.engines],
            "has_semantic_embedder": ctx.has_semantic,
            "embedding_dim": edim(),
        },
        "memory": {
            "db_type": "sqlite" if isinstance(ctx.memory, SQLiteMemoryStore) else "memory",
            "total_nodes": len(ctx.memory.all()),
            "by_type": {str(k.value): sum(1 for n in ctx.memory.all() if n.type == k)
                        for k in MemoryType},
            "embedder": "semantic" if ctx.has_semantic else "hash",
        },
        "conversations": {
            "count": ctx.conversations.count(),
        },
        "skills": {
            "count": len(ctx.skills.list()),
            "categories": ctx.skills.categories(),
            "list": [{"name": s.name, "category": s.category, "risk": s.risk, "usage": s.usage_count}
                     for s in ctx.skills.list()],
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
                1 for n in ctx.memory.all() if n.type == MemoryType.REFLECTION
            ),
            "session_importance": dict(runtime.session_importance),
        },
        "checks": {
            "db_accessible": isinstance(ctx.memory, SQLiteMemoryStore) and
                ctx.memory.get("__nonexistent__") is None,
            "engines_available": len(ctx.engines) > 0,
            "memory_working": len(ctx.memory.all()) >= 0,
        },
    }


@router.get("/env")
async def debug_env(user_id: str = Depends(get_current_user)) -> dict:
    """Diagnostic: report WHICH engine-related env vars the running process can
    see — names + presence + value length only. NEVER returns the secret value.
    Auth-gated. Remove or ignore once diagnosis is done."""
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
    return {"watched": seen, "keyish_names_present": keyish, "engines_built": [e.id for e in ctx.engines]}


@router.get("/routing")
async def debug_routing(msg: str = "你好", user_id: str = Depends(get_current_user)) -> dict:
    """Test router: which engine would answer this message RIGHT NOW?

    Shows the full decision tree — eligible engines, scores, which one
    gets picked first, and which fallback chain. Also makes a single test
    call to verify the chosen engine actually works.

    Query params:
      msg  — test message to route (default: "你好")
    """
    messages = [
        EngineMessage(role="system", content="你是一个AI助手，用中文回答。"),
        EngineMessage(role="user", content=msg),
    ]
    from ..cognition.dispatch import needs_reasoner
    complexity = Complexity.L3_DEEP if needs_reasoner("debug", msg) else Complexity.L2_DAILY
    ranked, trace = ctx.router.plan(CognitiveRequest(
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
        } for e in ctx.engines],
        "eligible": trace.candidates,
        "scores": trace.scores,
        "chosen": trace.chosen,
        "reason": trace.reason,
        "fallback_chain": [e.id for e in ranked[1:]] if len(ranked) > 1 else [],
        "test_call": test_result,
    }


@router.post("/context")
async def debug_context(req: EmpathyRequest, user_id: str = Depends(get_current_user)) -> dict:
    """Debug endpoint — see what context the ContextBuilder assembles."""
    from ..main import _get_recent_topics

    user = user_id
    recent_topics = _get_recent_topics(req.conversation_id) if hasattr(req, 'conversation_id') else []
    assembled = await build_context(req.message, user, ctx.memory, ctx.router, recent_topics=recent_topics)
    return {
        "message": req.message,
        "context": assembled.to_prompt_section(),
        "profile_chars": len(assembled.profile),
        "history_chars": len(assembled.topic_history),
        "reflections_chars": len(assembled.reflections),
        "total_chars": assembled.total_chars,
        "close_to_cap": assembled.total_chars > 2400,
    }


@router.get("/compression-stats")
async def get_compression_stats(user_id: str = Depends(get_current_user)) -> dict:
    """Get aggregate compression statistics across all conversations."""
    from ..cognition.context_window import get_all_compression_stats

    return {
        "status": "ok",
        "stats": get_all_compression_stats(),
    }


@router.get("/compression-history/{conversation_id}")
async def get_conversation_compression_history(
    conversation_id: str,
    user_id: str = Depends(get_current_user)
) -> dict:
    """Get compression history for a specific conversation.

    Returns detailed metrics for each compression operation including:
    - Compression ratio and time
    - Token savings
    - Facts extracted
    - Quality scores (when available)
    """
    from ..cognition.context_window import get_compression_history

    history = get_compression_history(conversation_id)
    return {
        "status": "ok",
        "data": history.to_dict(),
    }

"""Misc router — version, health, stats, skills, persona, engines, empathy, pwa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, Path as FastAPIPath
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel

from ..deps import get_current_user, ctx
from ..log_engine import log
from .. import runtime
from ..persona.empathy import run_empathy_pipeline

router = APIRouter(tags=["misc"])


@router.get("/api/version")
async def version_info() -> dict:
    """Return the current Sunday OS version + changelog pointer."""
    from ..main import _version_str

    parts = _version_str.replace("-dev", "").replace("-alpha", "").replace("-beta", "").split(".")
    return {
        "version": _version_str,
        "phase": "Phase 1 · ~90%",
        "changelog": "CHANGELOG.md",
        "major": int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0,
        "minor": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
        "patch": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
    }


@router.get("/health")
async def health() -> dict:
    """Health check endpoint with system status."""
    from ..main import _version_str
    from ..memory.embedding import embedding_dim as edim, embedder_provider as eprov

    provider = eprov()
    return {
        "status": "ok",
        "version": _version_str,
        "engines": [e.id for e in ctx.engines],
        "memory_nodes": len(ctx.memory.all()),
        "conversation_count": ctx.conversations.count(),
        "embedder": "semantic" if provider != "hash" else "hash",
        "embedder_provider": provider,
        # degraded = running on the hash fallback (no semantic relevance).
        # Surfaces silently-broken CJK retrieval when a key is missing/failing.
        "embedder_degraded": provider == "hash",
        "embedding_dim": edim(),
    }


@router.get("/api/stats/dashboard")
async def dashboard_stats(user_id: str = Depends(get_current_user)) -> dict:
    """Real-time dashboard data — replaces frontend mock values."""
    avg_lat = (runtime.total_latency_ms / runtime.call_count
               if runtime.call_count > 0 else 0)
    return {
        "messages_today": runtime.messages_today,
        "model_calls": runtime.calls_today,
        "tokens_used": runtime.tokens_today,
        "cost_today": round(runtime.cost_today, 4),
        "memory_nodes": len(ctx.memory.all()),
        "avg_latency_ms": round(avg_lat, 1),
        "active_tools": len(ctx.skills.list()),
        "engines": [
            {"id": e.id, "calls": runtime.engine_calls.get(e.id, 0),
             "strong": e.caps.strong_reasoning, "local": e.caps.local}
            for e in ctx.engines
        ],
        "recent_errors": runtime.recent_errors[-10:],
    }


@router.get("/api/skills")
async def skills(user_id: str = Depends(get_current_user)) -> dict:
    """List all registered skills with categories and usage stats."""
    return ctx.skills.summary()


@router.get("/api/persona")
async def persona_view(reload: bool = False, user_id: str = Depends(get_current_user)) -> dict:
    """View Sunday's current persona (from persona.yaml).

    Set ?reload=true to hot-reload from disk without restarting.
    """
    from ..persona import load_persona, reload_persona, persona_version

    data = reload_persona() if reload else load_persona()
    return {
        "version": persona_version(),
        "persona": data,
        "reloaded": reload,
    }


class EmpathyRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/api/empathy/analyze")
async def empathy_analyze_endpoint(req: EmpathyRequest, user_id: str = Depends(get_current_user)) -> dict:
    """Debug endpoint — analyze a single message for emotion and intent.

    Returns the UU emotional snapshot + IRG empathy guidance that would be
    injected into the system prompt.
    """
    snapshot, guidance = await run_empathy_pipeline(req.message, ctx.router)
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


@router.get("/api/engines")
async def engines() -> dict:
    """List available engines with capabilities."""
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
            for e in ctx.engines
        ]
    }


@router.get("/api/pwa/icon-{size}", response_class=Response)
async def pwa_icon(size: int = FastAPIPath(..., ge=1)) -> Response:
    """SVG icon at requested size — vector, scales to anything."""
    from ..pwa import get_icon_svg

    return FastAPIResponse(
        content=get_icon_svg(size),
        media_type="image/svg+xml",
    )

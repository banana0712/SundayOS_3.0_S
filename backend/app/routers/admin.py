"""Admin domain — owner-gated management endpoints (ADR-013).

First domain extracted from main.py in the routers/ split. Reads shared
singletons from app.deps; admin gate via Depends(get_admin). Behavior is
identical to the original main.py routes (verified against the same curl flow).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import ctx, get_admin
from ..memory.sqlite_store import SQLiteMemoryStore
from ..memory.embedding import embedding_dim, embedder_provider

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def admin_users(_: str = Depends(get_admin)) -> dict:
    """List all registered users with per-user memory/conversation counts."""
    users = ctx.user_store.list_all()
    enriched = []
    for u in users:
        mem_count = len(ctx.memory.all(u["id"]))
        conv_count = len(ctx.conversations.list(u["id"]))
        enriched.append({**u, "memory_count": mem_count, "conv_count": conv_count})
    return {"users": enriched, "total": len(enriched)}


@router.get("/usage")
async def admin_usage(_: str = Depends(get_admin)) -> dict:
    """Global usage metrics."""
    rt = ctx.runtime
    return {
        "users": ctx.user_store.count(),
        "total_memories": len(ctx.memory.all()),
        "total_conversations": ctx.conversations.count(),
        "engines": [
            {"id": e.id, "quality": e.caps.quality,
             "calls": rt.engine_calls.get(e.id, 0),
             "primary": e.caps.primary}
            for e in ctx.engines
        ],
        "runtime": {
            "messages_today": rt.messages_today,
            "calls_today": rt.calls_today,
            "tokens_today": rt.tokens_today,
            "cost_today": round(rt.cost_today, 6),
            "avg_latency_ms": round(rt.avg_latency, 1),
        },
    }


@router.get("/health")
async def admin_health(_: str = Depends(get_admin)) -> dict:
    """Full system health snapshot."""
    rt = ctx.runtime
    prov = embedder_provider()
    return {
        "server": {
            "version": ctx.version,
            "python": __import__("sys").version,
        },
        "db": {
            "type": "sqlite" if isinstance(ctx.memory, SQLiteMemoryStore) else "memory",
            "users": ctx.user_store.count(),
            "memories": len(ctx.memory.all()),
            "conversations": ctx.conversations.count(),
        },
        "engines": [
            {"id": e.id, "quality": e.caps.quality, "healthy": True,
             "calls": rt.engine_calls.get(e.id, 0)}
            for e in ctx.engines
        ],
        "embedder": "semantic" if prov != "hash" else "hash",
        "embedder_provider": prov,
        "embedder_degraded": prov == "hash",
        "embedding_dim": embedding_dim(),
    }

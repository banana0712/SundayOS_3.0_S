"""Memory & Experience Layer API endpoints.

Seven memory routes (store/search/reflect/reflections/consolidate/stats/delete)
+ two experience routes (run/nodes).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import ctx, get_current_user
from ..memory.schema import MemoryNode, MemoryType
from ..memory.sqlite_store import SQLiteMemoryStore
from ..memory.reflection import run_reflection
from ..memory.experience import run_experience_layer

router = APIRouter(tags=["memory"])


# --- Request models ---------------------------------------------------------

class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "episodic"
    importance: int = 5


class MemorySearchRequest(BaseModel):
    query: str
    k: int = 12


class ReflectionRequest(BaseModel):
    force: bool = False


# --- Memory endpoints -------------------------------------------------------

@router.post("/api/memory/store")
async def memory_store(req: MemoryStoreRequest,
                      user_id: str = Depends(get_current_user)) -> dict:
    node = ctx.memory.add(MemoryNode(
        content=req.content, user_id=user_id,
        type=MemoryType(req.memory_type), importance=req.importance,
    ))
    return {"id": node.id, "stored": True}


@router.post("/api/memory/search")
async def memory_search(req: MemorySearchRequest,
                       user_id: str = Depends(get_current_user)) -> dict:
    hits = ctx.memory.retrieve(req.query, user_id=user_id, k=req.k)
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


@router.post("/api/memory/reflect")
async def memory_reflect(req: ReflectionRequest,
                        user_id: str = Depends(get_current_user)) -> dict:
    """Trigger reflection (L1→L2). Generative Agents two-step pipeline.

    Unless force=True, respects the importance threshold.
    Returns the generated insights with their evidence IDs.
    """
    from ..memory.reflection import _should_reflect
    if not req.force and not _should_reflect(ctx.memory, user_id):
        return {"triggered": False, "insights": [],
                "message": "Importance threshold not reached. Use force=true to override."}
    insights = await run_reflection(ctx.memory, user_id, ctx.router)
    return {
        "triggered": True,
        "insights": insights,
        "message": f"Generated {len(insights)} reflections.",
    }


@router.get("/api/memory/reflections")
async def memory_reflections(limit: int = 20,
                             user_id: str = Depends(get_current_user)) -> dict:
    """List generated REFLECTION nodes for the current user, newest first."""
    all_nodes = ctx.memory.all(user_id)
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


@router.post("/api/memory/consolidate")
async def memory_consolidate(user_id: str = Depends(get_current_user)) -> dict:
    """Run L1 consolidation — archive expired low-importance memories.

    For the full L3 experience layer (merge + archive + extract + patterns),
    use POST /api/experience/run.
    """
    dropped = ctx.memory.archive_expired(threshold=0.4)
    total = len(ctx.memory.all())
    return {
        "dropped": dropped,
        "remaining": total,
        "message": f"Archived {dropped} expired memories. {total} remaining.",
    }


@router.get("/api/memory/stats")
async def memory_stats(user_id: str = Depends(get_current_user)) -> dict:
    """Return memory statistics — count by type, embedder info."""
    from ..memory.embedding import embedding_dim as edim
    from ..main import _has_semantic
    all_nodes = ctx.memory.all(user_id)
    by_type: dict[str, int] = {}
    for n in all_nodes:
        by_type[str(n.type.value)] = by_type.get(str(n.type.value), 0) + 1
    return {
        "total_nodes": len(all_nodes),
        "by_type": by_type,
        "embedder": "semantic" if _has_semantic else "hash",
        "embedding_dim": edim(),
        "db_type": "sqlite" if isinstance(ctx.memory, SQLiteMemoryStore) else "memory",
    }


@router.delete("/api/memory/{mem_id}")
async def memory_delete(mem_id: str,
                       user_id: str = Depends(get_current_user)) -> dict:
    node = ctx.memory.get(mem_id)
    if node is None or node.user_id != user_id:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": ctx.memory.delete(mem_id)}


# --- Experience layer endpoints ---------------------------------------------

@router.post("/api/experience/run")
async def experience_run(user_id: str = Depends(get_current_user)) -> dict:
    """Run the full L3 Experience layer.

    Performs three operations from From Storage to Experience (2026):
    1. CONSOLIDATION — merge similar memories, archive expired, extract semantics
    2. PATTERN DETECTION — find repeating behavioral patterns → EXPERIENCE nodes
    3. PROCEDURAL PRIMITIVE — detect recurring tool sequences → skill proposals

    This is the nightly batch job for Sunday's cognitive evolution.
    Uses the current user's identity (derived from API key).
    """
    user = user_id
    result = await run_experience_layer(ctx.memory, ctx.router, user)
    return {
        "user": user,
        "consolidation": result["consolidation"],
        "patterns_found": len(result["patterns"]),
        "patterns": result["patterns"],
        "primitives_found": len(result["primitives"]),
        "primitives": result["primitives"],
    }


@router.get("/api/experience/nodes")
async def experience_nodes(limit: int = 20,
                          user_id: str = Depends(get_current_user)) -> dict:
    """List EXPERIENCE nodes for the current user."""
    all_nodes = ctx.memory.all(user_id)
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

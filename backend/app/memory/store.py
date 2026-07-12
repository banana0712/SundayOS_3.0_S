"""Memory store with the composite retrieval score.

docs/3.0/04-memory-system.md §4.4:
    score = α·recency + β·importance + γ·relevance
Each component min-max normalized over candidates before weighting.

In-memory store (used directly in tests). A SQLite-backed subclass persists it;
both share the pure scoring logic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .embedding import cosine, embed
from .schema import MemoryNode, MemoryType

RECENCY_DECAY = 0.995  # per hour (docs §4.4)


@dataclass
class ScoredMemory:
    node: MemoryNode
    score: float
    recency: float
    importance: float
    relevance: float


def _recency(node: MemoryNode, now: datetime) -> float:
    hours = max(0.0, (now - node.last_access).total_seconds() / 3600.0)
    return RECENCY_DECAY ** hours


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if math.isclose(hi, lo):
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


class MemoryStore:
    def __init__(self, alpha: float = 1.0, beta: float = 1.0, gamma: float = 1.0):
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self._nodes: dict[str, MemoryNode] = {}

    # -- writes --------------------------------------------------------------
    def add(self, node: MemoryNode) -> MemoryNode:
        if node.embedding is None:
            node.embedding = embed(node.content)
        self._nodes[node.id] = node
        return node

    def get(self, mem_id: str) -> MemoryNode | None:
        return self._nodes.get(mem_id)

    def delete(self, mem_id: str) -> bool:
        return self._nodes.pop(mem_id, None) is not None

    def all(self, user_id: str | None = None) -> list[MemoryNode]:
        return [n for n in self._nodes.values() if user_id is None or n.user_id == user_id]

    # -- retrieval (docs §4.4) ----------------------------------------------
    def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = 12,
        now: datetime | None = None,
        types: list[MemoryType] | None = None,
    ) -> list[ScoredMemory]:
        now = now or datetime.now(timezone.utc)
        candidates = [
            n for n in self._nodes.values()
            if n.user_id == user_id and (types is None or n.type in types)
        ]
        if not candidates:
            return []

        q_emb = embed(query)
        rec = [_recency(n, now) for n in candidates]
        imp = [n.importance / 10.0 for n in candidates]
        rel = [cosine(q_emb, n.embedding or []) for n in candidates]

        rec_n, imp_n, rel_n = _minmax(rec), _minmax(imp), _minmax(rel)

        scored = [
            ScoredMemory(
                node=n,
                score=self.alpha * rec_n[i] + self.beta * imp_n[i] + self.gamma * rel_n[i],
                recency=rec_n[i], importance=imp_n[i], relevance=rel_n[i],
            )
            for i, n in enumerate(candidates)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        top = scored[:k]

        # touch retrieved memories (reinforcement)
        for s in top:
            s.node.last_access = now
            s.node.access_count += 1
        return top

    # -- consolidation helper (docs §4.7) -----------------------------------
    def archive_expired(self, threshold: float = 0.4, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        to_drop = [
            n.id for n in self._nodes.values()
            if not n.frozen and n.importance < 10
            and n.effective_importance(now) < threshold
        ]
        for mid in to_drop:
            del self._nodes[mid]
        return len(to_drop)

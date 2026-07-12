"""Memory node schema — docs/3.0/04-memory-system.md §4.3."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return "mem_" + uuid.uuid4().hex[:16]


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    REFLECTION = "reflection"    # L2 product
    EXPERIENCE = "experience"    # L3 product


@dataclass
class MemoryNode:
    content: str
    user_id: str
    type: MemoryType = MemoryType.EPISODIC
    id: str = field(default_factory=_uid)
    importance: int = 5                       # 1..10 (Generative Agents scale)
    embedding: list[float] | None = None
    created_at: datetime = field(default_factory=_now)
    last_access: datetime = field(default_factory=_now)
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    source: str = "chat"
    frozen: bool = False

    def effective_importance(self, now: datetime | None = None) -> float:
        """docs §4.7: base × decay^(days/30) × (1 + 0.1·access_count)."""
        now = now or _now()
        days = max(0.0, (now - self.created_at).total_seconds() / 86400.0)
        decay = 0.5 ** (days / 30.0)          # 30-day half-life
        return self.importance * decay * (1 + 0.1 * self.access_count)

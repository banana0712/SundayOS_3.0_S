"""Belief state — structured user model shared across the two systems.
docs/3.0/05-dual-process-cognition.md §5.4."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Task:
    id: str
    desc: str
    status: str = "pending"   # pending | in_progress | done


@dataclass
class EmotionalState:
    mood: float = 0.6         # 0..1
    energy: float = 0.6
    stress: float = 0.3


@dataclass
class BeliefState:
    user_id: str
    current_goal: dict | None = None
    active_tasks: list[Task] = field(default_factory=list)
    obstacles: list[str] = field(default_factory=list)
    motivations: list[str] = field(default_factory=list)
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    preferences_touched: list[str] = field(default_factory=list)
    updated_by: str = "talker"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def has_unresolved_obstacles(self) -> bool:
        return len(self.obstacles) > 0

    def to_json(self) -> dict:
        return {
            "user_id": self.user_id,
            "current_goal": self.current_goal,
            "active_tasks": [t.__dict__ for t in self.active_tasks],
            "obstacles": self.obstacles,
            "motivations": self.motivations,
            "emotional_state": self.emotional_state.__dict__,
            "preferences_touched": self.preferences_touched,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }

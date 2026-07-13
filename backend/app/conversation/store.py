"""ConversationStore — multi-turn dialogue session management.

Same pattern as MemoryStore: in-memory dict for Phase 1, swappable to
SQLite later without changing the interface.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return "conv_" + uuid.uuid4().hex[:12]


@dataclass
class Conversation:
    id: str = field(default_factory=_uid)
    user_id: str = ""
    title: str = "新对话"
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


class ConversationStore:
    """In-memory conversation manager. Interface designed for later SQLite swap."""

    def __init__(self):
        self._convs: dict[str, Conversation] = {}

    # -- CRUD ----------------------------------------------------------------

    def create(self, user_id: str, title: str = "新对话") -> Conversation:
        conv = Conversation(user_id=user_id, title=title)
        self._convs[conv.id] = conv
        return conv

    def list(self, user_id: str) -> list[Conversation]:
        """Return all conversations for a user, newest first."""
        convs = [c for c in self._convs.values() if c.user_id == user_id]
        convs.sort(key=lambda c: c.updated_at, reverse=True)
        return convs

    def get(self, conv_id: str) -> Conversation | None:
        return self._convs.get(conv_id)

    def delete(self, conv_id: str) -> bool:
        return self._convs.pop(conv_id, None) is not None

    def rename(self, conv_id: str, title: str) -> bool:
        conv = self._convs.get(conv_id)
        if conv is None:
            return False
        conv.title = title
        conv.updated_at = _now()
        return True

    # -- messages ------------------------------------------------------------

    def add_message(self, conv_id: str, role: str, content: str,
                    engine: str | None = None, system: str | None = None,
                    trace: dict | None = None) -> bool:
        """Append a message to the conversation. Auto-creates if missing."""
        conv = self._convs.get(conv_id)
        if conv is None:
            return False
        msg = {
            "role": role,
            "content": content,
            "timestamp": _now().isoformat(),
        }
        if engine:
            msg["engine"] = engine
        if system:
            msg["system"] = system
        if trace:
            msg["trace"] = trace
        conv.messages.append(msg)

        # Auto-title: use first user message (truncate to 30 chars)
        if role == "user" and conv.title == "新对话":
            conv.title = content[:30] + ("…" if len(content) > 30 else "")

        conv.updated_at = _now()
        return True

    def count(self) -> int:
        return len(self._convs)

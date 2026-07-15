"""SQLite-backed ConversationStore — persists dialogue sessions across restarts.

Implements the same interface as ConversationStore (store.py) so main.py only
needs a one-line swap. Mirrors the sqlite_store.py (memory) pattern: subclass
the in-memory store, override the CRUD ops with SQLite ops, keep the return
type (Conversation dataclass) identical.

Messages are stored as a JSON array in a TEXT column (same approach as memory
embeddings). For personal scale (~thousands of turns per conversation) this is
fast enough; the retrieval pipeline never scans message bodies, it only reads a
whole conversation by id.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .store import Conversation, ConversationStore, _now


def _ensure_utc(dt: datetime) -> datetime:
    """Attach UTC timezone to naive datetimes read from SQLite."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SQLiteConversationStore(ConversationStore):
    """SQLite-persisted conversation store with the same CRUD interface."""

    def __init__(self, db_path: str = "sunday.db"):
        super().__init__()
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    # -- schema ---------------------------------------------------------------

    def _migrate(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                title       TEXT NOT NULL DEFAULT '新对话',
                messages    TEXT NOT NULL DEFAULT '[]',  -- JSON array of msg dicts
                created_at  TEXT NOT NULL,               -- ISO 8601
                updated_at  TEXT NOT NULL                -- ISO 8601
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_user
                ON conversations(user_id, updated_at DESC)
        """)
        self._conn.commit()

    # -- row <-> dataclass ----------------------------------------------------

    @staticmethod
    def _row_to_conv(row: tuple) -> Conversation:
        id_, user_id, title, messages_json, created_at, updated_at = row
        return Conversation(
            id=id_,
            user_id=user_id,
            title=title,
            messages=json.loads(messages_json) if messages_json else [],
            created_at=_ensure_utc(datetime.fromisoformat(created_at)),
            updated_at=_ensure_utc(datetime.fromisoformat(updated_at)),
        )

    def _persist(self, conv: Conversation) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO conversations
               (id, user_id, title, messages, created_at, updated_at)
               VALUES (?,?,?,?,?,?)""",
            (conv.id, conv.user_id, conv.title,
             json.dumps(conv.messages, ensure_ascii=False),
             conv.created_at.isoformat(), conv.updated_at.isoformat()),
        )
        self._conn.commit()

    # -- CRUD -----------------------------------------------------------------

    def create(self, user_id: str, title: str = "新对话") -> Conversation:
        conv = Conversation(user_id=user_id, title=title)
        self._persist(conv)
        return conv

    def list(self, user_id: str) -> list[Conversation]:
        """Return all conversations for a user, newest first."""
        rows = self._conn.execute(
            """SELECT id, user_id, title, messages, created_at, updated_at
               FROM conversations WHERE user_id = ?
               ORDER BY updated_at DESC""",
            (user_id,),
        ).fetchall()
        return [self._row_to_conv(r) for r in rows]

    def get(self, conv_id: str) -> Conversation | None:
        row = self._conn.execute(
            """SELECT id, user_id, title, messages, created_at, updated_at
               FROM conversations WHERE id = ?""",
            (conv_id,),
        ).fetchone()
        return self._row_to_conv(row) if row else None

    def delete(self, conv_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conv_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def rename(self, conv_id: str, title: str) -> bool:
        conv = self.get(conv_id)
        if conv is None:
            return False
        conv.title = title
        conv.updated_at = _now()
        self._persist(conv)
        return True

    # -- messages -------------------------------------------------------------

    def add_message(self, conv_id: str, role: str, content: str,
                    engine: str | None = None, system: str | None = None,
                    trace: dict | None = None) -> bool:
        """Append a message. Read-modify-write against SQLite."""
        conv = self.get(conv_id)
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
        self._persist(conv)
        return True

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM conversations"
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()

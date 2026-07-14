"""User preference profile — per-user, text-driven, SQLite-persisted.

Philosophy (ADR-012, aligned with PLUS/VAC/DeepMind 2025-2026):
  Preferences are NOT scalar ratings. They are STRUCTURED TEXT summaries
  that grow from user feedback and are injected into the system prompt.

  "用户说" → LLM 解析 → 偏好档案 → system prompt 注入 → 更好的回复

Storage: reuses the existing sunday.db SQLite connection.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserPreferences:
    """Per-user preference profile."""

    user_id: str = ""
    # ── Style (injected into system prompt directly) ──
    style: str = ""  # e.g. "用户喜欢简洁直接的回复"
    # ── Topic-specific preferences ──
    topics: dict[str, str] = field(default_factory=dict)
    # ── Engine quality (learned, per-engine) ──
    engine_prefs: dict[str, dict] = field(default_factory=dict)
    # ── Feedback history (last 50) ──
    history: list[dict] = field(default_factory=list)
    # ── Metadata ──
    updated_at: str = ""

    def to_prompt_block(self) -> str:
        """Generate a compact natural-language preference block for the system prompt.
        Returns empty string if no preferences are recorded."""
        lines: list[str] = []
        if self.style:
            lines.append(f"- {self.style}")
        for topic, pref in self.topics.items():
            lines.append(f"- [{topic}] {pref}")
        if not lines:
            return ""
        return "[用户偏好]\n" + "\n".join(lines)

    def add_feedback(self, feedback_text: str, rating: int,
                     engine_id: str = "", resolved_to: str = "") -> None:
        """Record a feedback event in history (bounded to 50)."""
        self.history.append({
            "text": feedback_text,
            "rating": rating,
            "engine": engine_id,
            "resolved_to": resolved_to,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if len(self.history) > 50:
            self.history = self.history[-50:]
        self.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")


# ── SQLite-backed preference store ──────────────────────────────────────

class PreferenceStore:
    """Persists per-user preferences in SQLite alongside memory nodes."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._migrate()

    def _migrate(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id     TEXT PRIMARY KEY,
                style       TEXT NOT NULL DEFAULT '',
                topics      TEXT NOT NULL DEFAULT '{}',     -- JSON
                engine_prefs TEXT NOT NULL DEFAULT '{}',    -- JSON
                history     TEXT NOT NULL DEFAULT '[]',     -- JSON array
                updated_at  TEXT NOT NULL DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                message_id  TEXT    NOT NULL DEFAULT '',
                engine_id   TEXT    NOT NULL DEFAULT '',
                rating      INTEGER NOT NULL DEFAULT 0,  -- 1 = 👍, -1 = 👎
                text        TEXT    NOT NULL DEFAULT '',
                parsed      TEXT    NOT NULL DEFAULT '{}', -- JSON parse result
                created_at  TEXT    NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_user
                ON feedback_log(user_id)
        """)
        self._conn.commit()

    def get(self, user_id: str) -> UserPreferences:
        row = self._conn.execute(
            "SELECT user_id, style, topics, engine_prefs, history, updated_at "
            "FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if row is None:
            return UserPreferences(user_id=user_id)

        return UserPreferences(
            user_id=row[0],
            style=row[1],
            topics=json.loads(row[2]) if row[2] else {},
            engine_prefs=json.loads(row[3]) if row[3] else {},
            history=json.loads(row[4]) if row[4] else [],
            updated_at=row[5],
        )

    def save(self, prefs: UserPreferences) -> None:
        prefs.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            "INSERT OR REPLACE INTO user_preferences "
            "(user_id, style, topics, engine_prefs, history, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                prefs.user_id,
                prefs.style,
                json.dumps(prefs.topics, ensure_ascii=False),
                json.dumps(prefs.engine_prefs, ensure_ascii=False),
                json.dumps(prefs.history, ensure_ascii=False, default=str),
                prefs.updated_at,
            ),
        )
        self._conn.commit()

    def log_feedback(self, user_id: str, message_id: str, engine_id: str,
                     rating: int, text: str = "",
                     parsed: dict[str, Any] | None = None) -> None:
        self._conn.execute(
            "INSERT INTO feedback_log (user_id, message_id, engine_id, rating, text, parsed, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, message_id, engine_id, rating, text,
             json.dumps(parsed or {}, ensure_ascii=False, default=str),
             time.strftime("%Y-%m-%d %H:%M:%S")),
        )
        self._conn.commit()

    def recent_feedback(self, user_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT message_id, engine_id, rating, text, parsed, created_at "
            "FROM feedback_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "message_id": r[0], "engine_id": r[1], "rating": r[2],
                "text": r[3], "parsed": json.loads(r[4]) if r[4] else {},
                "created_at": r[5],
            }
            for r in rows
        ]

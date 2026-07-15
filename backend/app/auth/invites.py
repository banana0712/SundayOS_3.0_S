"""Invite code management — gate registration to invited friends only.

SCAFFOLD (2026-07-15): This is a self-contained data layer for the invite
system. It is intentionally NOT wired into main.py yet — nothing imports it,
so it cannot break the running app. A follow-up task completes the wiring;
see docs/guides/INVITE_SYSTEM_PLAN.md for the exact steps.

Design (matches UserStore style):
  - Codes: human-readable "SUN-XXXX" (Crockford-ish, no ambiguous chars)
  - One-time use: redeeming stamps used_by/used_at; re-redeem is rejected
  - Owner-only creation (enforced at the endpoint layer, not here)
  - Storage: SQLite, own table in the shared sunday.db
"""

from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass

# Crockford base32 minus ambiguous chars (no I/L/O/U/0/1) → readable codes.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"


def _make_code() -> str:
    """SUN-XXXX, 4 unambiguous chars. ~800K space — fine for personal scale;
    collisions are caught by the PRIMARY KEY and retried by the caller."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"SUN-{body}"


@dataclass
class Invite:
    code: str
    created_by: str          # owner user_id
    note: str                # free-text "who is this for"
    created_at: str
    used_by: str | None      # redeemer user_id; None = still valid
    used_at: str | None

    @property
    def is_used(self) -> bool:
        return self.used_by is not None


class InviteStore:
    """SQLite-backed invite code manager. Interface mirrors UserStore."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                code       TEXT PRIMARY KEY,
                created_by TEXT NOT NULL,
                note       TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                used_by    TEXT,            -- NULL = unredeemed
                used_at    TEXT
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_invites_used ON invites(used_by)"
        )
        self._conn.commit()

    # ── row <-> dataclass ────────────────────────────────────────────────

    @staticmethod
    def _row_to_invite(row: tuple) -> Invite:
        return Invite(
            code=row[0], created_by=row[1], note=row[2],
            created_at=row[3], used_by=row[4], used_at=row[5],
        )

    # ── create (owner) ───────────────────────────────────────────────────

    def create(self, created_by: str, note: str = "") -> Invite:
        """Generate a fresh one-time code. Retries on the (rare) collision."""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for _ in range(5):
            code = _make_code()
            try:
                self._conn.execute(
                    "INSERT INTO invites (code, created_by, note, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (code, created_by, note.strip(), now),
                )
                self._conn.commit()
                return Invite(code=code, created_by=created_by,
                              note=note.strip(), created_at=now,
                              used_by=None, used_at=None)
            except sqlite3.IntegrityError:
                continue  # code collision, try another
        raise RuntimeError("邀请码生成失败，请重试")

    # ── redeem (registration) ────────────────────────────────────────────

    def is_valid(self, code: str) -> bool:
        """True if the code exists and is unredeemed. Read-only check."""
        row = self._conn.execute(
            "SELECT used_by FROM invites WHERE code = ?", (code.strip(),)
        ).fetchone()
        return row is not None and row[0] is None

    def redeem(self, code: str, used_by: str) -> bool:
        """Atomically mark a code used. Returns False if missing/already used.

        The `used_by IS NULL` guard in the UPDATE makes this race-safe: two
        concurrent redemptions of the same code — only one gets rowcount 1.
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cur = self._conn.execute(
            "UPDATE invites SET used_by = ?, used_at = ? "
            "WHERE code = ? AND used_by IS NULL",
            (used_by, now, code.strip()),
        )
        self._conn.commit()
        return cur.rowcount == 1

    # ── list / revoke (owner) ────────────────────────────────────────────

    def list_all(self) -> list[Invite]:
        rows = self._conn.execute(
            "SELECT code, created_by, note, created_at, used_by, used_at "
            "FROM invites ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_invite(r) for r in rows]

    def revoke(self, code: str) -> bool:
        """Delete an UNUSED code. Used codes are kept as an audit trail."""
        cur = self._conn.execute(
            "DELETE FROM invites WHERE code = ? AND used_by IS NULL",
            (code.strip(),),
        )
        self._conn.commit()
        return cur.rowcount == 1

    def close(self) -> None:
        self._conn.close()

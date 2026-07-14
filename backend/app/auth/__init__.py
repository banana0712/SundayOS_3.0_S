"""User account management — registration, login, token-based auth.

Design:
  - Passwords: pbkdf2_sha256 (stdlib, zero new deps)
  - Tokens: 32-char hex, stored in users table
  - Storage: SQLite (reuses sunday.db connection)
  - Backward-compat: SUNDAY_API_KEY still works as admin key
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass


# ── Password hashing (pbkdf2_sha256, stdlib only) ────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                              salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            salt.encode("utf-8"), 100_000,
        )
        return secrets.compare_digest(expected.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


# ── Token generation ─────────────────────────────────────────────────

def _make_token(username: str) -> str:
    raw = f"{username}:{time.time()}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ── User model ───────────────────────────────────────────────────────

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    token: str
    created_at: str

    @staticmethod
    def make_id(username: str) -> str:
        return "user_" + hashlib.sha256(username.encode("utf-8")).hexdigest()[:16]


# ── UserStore ────────────────────────────────────────────────────────

class UserStore:
    """SQLite-backed user account manager."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                token         TEXT NOT NULL DEFAULT '',
                created_at    TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
                ON users(username)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_token
                ON users(token)
        """)
        self._conn.commit()

    # ── Create / Register ────────────────────────────────────────────

    def create_user(self, username: str, password: str) -> User:
        username = username.strip()
        if len(username) < 2 or len(username) > 30:
            raise ValueError("用户名长度需在 2-30 个字符之间")
        if len(password) < 4:
            raise ValueError("密码至少 4 个字符")

        user_id = User.make_id(username)
        pw_hash = _hash_password(password)
        token = _make_token(username)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self._conn.execute(
                "INSERT INTO users (id, username, password_hash, token, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username, pw_hash, token, now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("用户名已存在")

        return User(
            id=user_id, username=username, password_hash=pw_hash,
            token=token, created_at=now,
        )

    # ── Verify / Login ──────────────────────────────────────────────

    def verify_user(self, username: str, password: str) -> User | None:
        username = username.strip()
        row = self._conn.execute(
            "SELECT id, username, password_hash, token, created_at "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        if not _verify_password(password, row[2]):
            return None
        # Refresh token on each login (invalidates old sessions)
        new_token = _make_token(username)
        self._conn.execute(
            "UPDATE users SET token = ? WHERE id = ?",
            (new_token, row[0]),
        )
        self._conn.commit()
        return User(
            id=row[0], username=row[1], password_hash=row[2],
            token=new_token, created_at=row[4],
        )

    # ── Token lookup ─────────────────────────────────────────────────

    def get_user_by_token(self, token: str) -> User | None:
        if not token:
            return None
        row = self._conn.execute(
            "SELECT id, username, password_hash, token, created_at "
            "FROM users WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row[0], username=row[1], password_hash=row[2],
            token=row[3], created_at=row[4],
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        if not user_id:
            return None
        row = self._conn.execute(
            "SELECT id, username, password_hash, token, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row[0], username=row[1], password_hash=row[2],
            token=row[3], created_at=row[4],
        )

    # ── Token management ─────────────────────────────────────────────

    def invalidate_token(self, token: str) -> None:
        self._conn.execute(
            "UPDATE users SET token = '' WHERE token = ?",
            (token,),
        )
        self._conn.commit()

    def refresh_token(self, user_id: str) -> str | None:
        user = self.get_user_by_id(user_id)
        if user is None:
            return None
        new_token = _make_token(user.username)
        self._conn.execute(
            "UPDATE users SET token = ? WHERE id = ?",
            (new_token, user_id),
        )
        self._conn.commit()
        return new_token

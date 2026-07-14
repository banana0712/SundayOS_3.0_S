"""Structured runtime logger — answers "what happened and why".

Writes to: stdout (console) + /var/log/sundayos.log (file, append-only).
Rotate: keeps last 5MB, writes to sundayos.log.1, sundayos.log.2.

Usage:
    from app.log_engine import log
    log.engine_startup(engines)
    log.route_decision(complexity, candidates, scores, chosen, reason)
    log.engine_call(engine_id, model, latency, tokens, cost)
    log.engine_error(engine_id, error)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

_LOG_PATH = os.environ.get("SUNDAY_LOG_PATH", "/var/log/sundayos.log")
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _rotate() -> None:
    try:
        p = Path(_LOG_PATH)
        if p.exists() and p.stat().st_size > _MAX_SIZE:
            for i in range(2, 0, -1):
                old = Path(f"{_LOG_PATH}.{i}")
                new = Path(f"{_LOG_PATH}.{i + 1}")
                if old.exists():
                    if new.exists():
                        new.unlink()
                    old.rename(new)
            backup = Path(f"{_LOG_PATH}.1")
            if backup.exists():
                backup.unlink()
            p.rename(backup)
    except OSError:
        pass  # best-effort rotation


def _write_file(line: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _emit(level: str, category: str, **fields) -> None:
    record = {
        "ts": _now(),
        "level": level,
        "cat": category,
        **fields,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    print(f"[{record['ts']}] [{level}] [{category}]", json.dumps(fields, ensure_ascii=False, default=str))
    # write to file (non-blocking best-effort)
    _rotate()
    _write_file(line)


class Logger:
    """Structured logger with semantic methods."""

    # ── startup ──────────────────────────────────────────────────────

    def engine_startup(self, engines: list) -> None:
        _emit("INFO", "startup", engines=[
            {"id": e.id, "model": getattr(e, "_model", "?"),
             "base_url": getattr(e, "_base_url", "?"),
             "caps": {
                 "fc": e.caps.function_calling,
                 "reasoning": e.caps.strong_reasoning,
                 "max_ctx": e.caps.max_context,
             }}
            for e in engines
        ])

    # ── routing ──────────────────────────────────────────────────────

    def route_decision(
        self,
        complexity: int,
        eligible: list[str],
        scores: dict[str, float],
        chosen: str | None,
        reason: str,
        user_msg_preview: str = "",
    ) -> None:
        _emit("INFO", "router", complexity=complexity,
              eligible=eligible, scores=scores, chosen=chosen,
              reason=reason, user_preview=user_msg_preview[:80])

    def route_no_candidates(self, complexity: int, all_engines: list[str],
                            breaker_state: dict) -> None:
        _emit("WARN", "router", event="no_candidates",
              complexity=complexity, all_engines=all_engines,
              breaker_state=breaker_state)

    # ── engine calls ─────────────────────────────────────────────────

    def engine_call(self, engine_id: str, latency_ms: float,
                    prompt_tokens: int, completion_tokens: int,
                    cost_usd: float, model: str = "",
                    success: bool = True) -> None:
        _emit("INFO" if success else "ERROR", "engine_call",
              engine_id=engine_id, model=model, latency_ms=latency_ms,
              prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
              cost_usd=cost_usd, success=success)

    def engine_error(self, engine_id: str, error_type: str,
                     error_detail: str, attempt: int = 1) -> None:
        _emit("ERROR", "engine_error", engine_id=engine_id,
              error_type=error_type, error_detail=error_detail[:300],
              attempt=attempt)

    def engine_fallback(self, from_engine: str, to_engine: str,
                        reason: str) -> None:
        _emit("WARN", "engine_fallback", from_engine=from_engine,
              to_engine=to_engine, reason=reason[:200])

    # ── chat pipeline ────────────────────────────────────────────────

    def chat_request(self, user_id: str, msg_len: int,
                     system: str, complexity: int) -> None:
        _emit("INFO", "chat", user_id=user_id, msg_len=msg_len,
              system=system, complexity=complexity)

    def chat_response(self, user_id: str, chosen_engine: str,
                      latency_ms: float, reply_len: int,
                      tokens: int, cost_usd: float) -> None:
        _emit("INFO", "chat_done", user_id=user_id, chosen_engine=chosen_engine,
              latency_ms=latency_ms, reply_len=reply_len,
              tokens=tokens, cost_usd=cost_usd)

    # ── errors ───────────────────────────────────────────────────────

    def chat_all_engines_failed(self, user_id: str, errors: dict) -> None:
        _emit("CRITICAL", "chat_fail", user_id=user_id, errors=errors)

    def health(self, engines: list[str], memory_nodes: int,
               conv_count: int, embedder: str) -> None:
        _emit("INFO", "health", engines=engines, memory_nodes=memory_nodes,
              conv_count=conv_count, embedder=embedder)

    # ── generic ──────────────────────────────────────────────────────

    def info(self, category: str, **fields) -> None:
        _emit("INFO", category, **fields)

    def warn(self, category: str, **fields) -> None:
        _emit("WARN", category, **fields)

    def error(self, category: str, **fields) -> None:
        _emit("ERROR", category, **fields)


# Singleton
log = Logger()

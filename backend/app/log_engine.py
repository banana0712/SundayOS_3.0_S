"""Structured runtime logger — answers "what happened and why".

Writes to:
  - stdout (console)
  - /var/log/sundayos.log (engine layer, 5MB rotate)
  - /var/log/sundayos-interaction.log (user interaction layer, 20MB rotate)

Usage:
    from app.log_engine import log

    # Engine layer
    log.engine_startup(engines)
    log.route_decision(complexity, candidates, scores, chosen, reason)
    log.engine_call(engine_id, model, latency, tokens, cost)
    log.engine_error(engine_id, error)

    # User interaction layer (NEW)
    log.interaction_start(session_id, user_id, request_id, user_message)
    log.context_retrieved(request_id, memory_nodes, conversation_history)
    log.guardrail_check(request_id, stage, passed, reason)
    log.tool_call(request_id, tool_name, tool_args, tool_result, success)
    log.memory_write(request_id, node_id, node_type, content_preview)
    log.interaction_complete(request_id, user_id, system_response, success)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

_LOG_PATH = os.environ.get("SUNDAY_LOG_PATH", "/var/log/sundayos.log")
_INTERACTION_LOG_PATH = os.environ.get("SUNDAY_INTERACTION_LOG_PATH", "/var/log/sundayos-interaction.log")
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB (engine log)
_INTERACTION_MAX_SIZE = 20 * 1024 * 1024  # 20 MB (interaction log)

# 配置选项
_LOG_INTERACTION = os.environ.get("SUNDAY_LOG_INTERACTION", "true").lower() == "true"
_LOG_FULL_CONTENT = os.environ.get("SUNDAY_LOG_FULL_CONTENT", "true").lower() == "true"
_LOG_MAX_MESSAGE_LEN = int(os.environ.get("SUNDAY_LOG_MAX_MESSAGE_LEN", "10000"))
_LOG_REDACT_PII = os.environ.get("SUNDAY_LOG_REDACT_PII", "true").lower() == "true"


def _rotate(log_path: str, max_size: int) -> None:
    """通用日志轮转函数"""
    try:
        p = Path(log_path)
        if p.exists() and p.stat().st_size > max_size:
            for i in range(2, 0, -1):
                old = Path(f"{log_path}.{i}")
                new = Path(f"{log_path}.{i + 1}")
                if old.exists():
                    if new.exists():
                        new.unlink()
                    old.rename(new)
            backup = Path(f"{log_path}.1")
            if backup.exists():
                backup.unlink()
            p.rename(backup)
    except OSError:
        pass  # best-effort rotation


def _write_file(log_path: str, line: str, max_size: int) -> None:
    """通用文件写入函数"""
    try:
        _rotate(log_path, max_size)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass  # best-effort write


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _emit(level: str, category: str, log_type: str = "engine", **fields) -> None:
    """
    发送日志记录

    Args:
        level: 日志级别 (INFO/WARN/ERROR/CRITICAL)
        category: 日志类别
        log_type: 日志类型 ("engine" 或 "interaction")
        **fields: 其他字段
    """
    record = {
        "ts": _now(),
        "level": level,
        "cat": category,
        **fields,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    print(f"[{record['ts']}] [{level}] [{category}]", json.dumps(fields, ensure_ascii=False, default=str))

    # 写入对应的日志文件
    if log_type == "interaction":
        _write_file(_INTERACTION_LOG_PATH, line, _INTERACTION_MAX_SIZE)
    else:
        _write_file(_LOG_PATH, line, _MAX_SIZE)


class Logger:
    """Structured logger with semantic methods."""

    # ── startup ──────────────────────────────────────────────────────

    def engine_startup(self, engines: list) -> None:
        _emit("INFO", "startup", engines=[
            {"id": e.id, "model": getattr(e, "_model", "?"),
             "base_url": getattr(e, "_base_url", "?"),
             "quality": e.caps.quality,
             "primary": e.caps.primary,
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

    # ── 用户交互完整记录 ────────────────────────────────────────

    def interaction_start(
        self,
        session_id: str,
        user_id: str,
        request_id: str,
        user_message: str,
        conversation_id: str = None,
        metadata: dict = None,
    ) -> None:
        """记录用户请求开始"""
        if not _LOG_INTERACTION:
            return

        # 截断过长消息
        if _LOG_FULL_CONTENT and len(user_message) > _LOG_MAX_MESSAGE_LEN:
            user_message = user_message[:_LOG_MAX_MESSAGE_LEN] + "...[截断]"

        # PII 脱敏（简单版本，可扩展）
        if _LOG_REDACT_PII:
            user_message = _redact_pii(user_message)

        _emit(
            "INFO",
            "interaction_start",
            "interaction",
            session_id=session_id,
            user_id=user_id,
            request_id=request_id,
            user_message=user_message if _LOG_FULL_CONTENT else f"[{len(user_message)} chars]",
            conversation_id=conversation_id,
            metadata=metadata or {},
        )

    def context_retrieved(
        self,
        request_id: str,
        memory_nodes: list,
        conversation_history: list,
        retrieved_count: int,
    ) -> None:
        """记录检索到的上下文"""
        if not _LOG_INTERACTION:
            return

        # 简化记忆节点（只保留关键信息）
        simplified_nodes = [
            {
                "id": node.get("id", "?"),
                "content": node.get("content", "")[:100] + "..." if len(node.get("content", "")) > 100 else node.get("content", ""),
                "importance": node.get("importance"),
            }
            for node in memory_nodes[:5]  # 最多记录 5 个
        ]

        # 简化对话历史
        simplified_history = [
            {
                "role": msg.get("role"),
                "content": msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", ""),
            }
            for msg in conversation_history[-3:]  # 最多记录最近 3 条
        ]

        _emit(
            "INFO",
            "context_retrieved",
            "interaction",
            request_id=request_id,
            memory_nodes=simplified_nodes,
            conversation_history=simplified_history,
            retrieved_count=retrieved_count,
        )

    def guardrail_check(
        self,
        request_id: str,
        stage: str,
        passed: bool,
        reason: str = "",
        redacted_fields: list = None,
    ) -> None:
        """记录护栏检查结果"""
        if not _LOG_INTERACTION:
            return

        _emit(
            "INFO" if passed else "WARN",
            "guardrail",
            "interaction",
            request_id=request_id,
            stage=stage,
            passed=passed,
            reason=reason,
            redacted_fields=redacted_fields or [],
        )

    def tool_call(
        self,
        request_id: str,
        tool_name: str,
        tool_args: dict,
        tool_result: any,
        success: bool,
        latency_ms: float,
        error: str = None,
    ) -> None:
        """记录工具调用"""
        if not _LOG_INTERACTION:
            return

        # 截断过长的结果
        result_str = str(tool_result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "...[截断]"

        _emit(
            "INFO" if success else "ERROR",
            "tool_call",
            "interaction",
            request_id=request_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=result_str,
            success=success,
            latency_ms=latency_ms,
            error=error,
        )

    def memory_write(
        self,
        request_id: str,
        node_id: str,
        node_type: str,
        content_preview: str,
        importance: float = None,
    ) -> None:
        """记录记忆写入"""
        if not _LOG_INTERACTION:
            return

        # 截断内容预览
        if len(content_preview) > 200:
            content_preview = content_preview[:200] + "..."

        _emit(
            "INFO",
            "memory_write",
            "interaction",
            request_id=request_id,
            node_id=node_id,
            node_type=node_type,
            content_preview=content_preview,
            importance=importance,
        )

    def interaction_complete(
        self,
        request_id: str,
        user_id: str,
        system_response: str,
        total_latency_ms: float,
        tokens_used: int,
        cost_usd: float,
        engine_used: str,
        success: bool,
        error: str = None,
    ) -> None:
        """记录完整交互结束"""
        if not _LOG_INTERACTION:
            return

        # 截断过长响应
        if _LOG_FULL_CONTENT and len(system_response) > _LOG_MAX_MESSAGE_LEN:
            system_response = system_response[:_LOG_MAX_MESSAGE_LEN] + "...[截断]"

        # PII 脱敏
        if _LOG_REDACT_PII:
            system_response = _redact_pii(system_response)

        _emit(
            "INFO" if success else "ERROR",
            "interaction_complete",
            "interaction",
            request_id=request_id,
            user_id=user_id,
            system_response=system_response if _LOG_FULL_CONTENT else f"[{len(system_response)} chars]",
            total_latency_ms=total_latency_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            engine_used=engine_used,
            success=success,
            error=error,
        )


# ── PII 脱敏辅助函数 ────────────────────────────────────────────────

import re

def _redact_pii(text: str) -> str:
    """简单的 PII 脱敏（可扩展）"""
    # 手机号：13812345678 -> 138****5678
    text = re.sub(r'(\d{3})\d{4}(\d{4})', r'\1****\2', text)

    # 邮箱：user@example.com -> u***@example.com
    text = re.sub(r'(\w)[^@\s]*(@[\w.]+)', r'\1***\2', text)

    # 身份证号：简单遮蔽中间部分
    text = re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', text)

    return text


# Singleton
log = Logger()

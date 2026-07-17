"""交互日志查询 API

提供查询和分析用户交互日志的接口。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/logs", tags=["logs"])


class InteractionLogEntry(BaseModel):
    """单条交互日志记录"""
    ts: str
    level: str
    cat: str
    request_id: str | None = None
    user_id: str | None = None
    data: dict


class InteractionLogResponse(BaseModel):
    """交互日志查询响应"""
    total: int
    entries: list[InteractionLogEntry]
    next_offset: int | None = None


class InteractionStatsResponse(BaseModel):
    """交互统计响应"""
    total_interactions: int
    successful: int
    failed: int
    avg_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    engines: dict[str, int]


def _read_interaction_log(
    log_path: str = "/var/log/sundayos-interaction.log",
    limit: int = 100,
    offset: int = 0,
    request_id: str | None = None,
    user_id: str | None = None,
    category: str | None = None,
    since: str | None = None,
) -> tuple[list[InteractionLogEntry], int]:
    """读取并过滤交互日志

    Returns:
        (entries, total_count) - 分页后的条目列表和总条目数
    """

    try:
        log_file = Path(log_path)
        if not log_file.exists():
            return [], 0

        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    # 过滤条件
                    if request_id and entry.get("request_id") != request_id:
                        continue
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    if category and entry.get("cat") != category:
                        continue
                    if since:
                        entry_time = datetime.fromisoformat(entry.get("ts", ""))
                        since_time = datetime.fromisoformat(since)
                        if entry_time < since_time:
                            continue

                    # 提取通用字段
                    log_entry = InteractionLogEntry(
                        ts=entry.get("ts", ""),
                        level=entry.get("level", "INFO"),
                        cat=entry.get("cat", "unknown"),
                        request_id=entry.get("request_id"),
                        user_id=entry.get("user_id"),
                        data=entry
                    )
                    entries.append(log_entry)

                except json.JSONDecodeError:
                    continue

        total_count = len(entries)

        # 分页
        start = offset
        end = offset + limit
        return entries[start:end], total_count

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


@router.get("/interaction", response_model=InteractionLogResponse)
async def get_interaction_logs(
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    request_id: str | None = Query(None, description="请求ID"),
    user_id: str | None = Query(None, description="用户ID"),
    category: str | None = Query(None, description="日志类别 (interaction_start, guardrail, etc.)"),
    since: str | None = Query(None, description="起始时间 (ISO 8601)"),
) -> InteractionLogResponse:
    """查询交互日志

    Examples:
        # 查看最近 20 条日志
        GET /api/logs/interaction?limit=20

        # 查看特定请求的完整交互
        GET /api/logs/interaction?request_id=req_abc123

        # 查看某个用户的所有交互
        GET /api/logs/interaction?user_id=user_001&limit=50

        # 查看最近 1 小时的交互
        GET /api/logs/interaction?since=2026-07-17T10:00:00
    """

    entries, total = _read_interaction_log(
        limit=limit,
        offset=offset,
        request_id=request_id,
        user_id=user_id,
        category=category,
        since=since,
    )

    next_offset = offset + limit if offset + limit < total else None

    return InteractionLogResponse(
        total=total,
        entries=entries,
        next_offset=next_offset
    )


@router.get("/interaction/{request_id}", response_model=InteractionLogResponse)
async def get_interaction_by_id(request_id: str) -> InteractionLogResponse:
    """根据 request_id 获取完整交互流程

    返回该请求的所有日志记录（开始、护栏、上下文、记忆、完成）
    """

    entries, total = _read_interaction_log(request_id=request_id, limit=1000)

    if not entries:
        raise HTTPException(status_code=404, detail=f"未找到 request_id: {request_id}")

    return InteractionLogResponse(
        total=total,
        entries=entries,
        next_offset=None
    )


@router.get("/interaction/stats/summary", response_model=InteractionStatsResponse)
async def get_interaction_stats(
    since: str | None = Query(None, description="统计起始时间"),
    until: str | None = Query(None, description="统计结束时间"),
) -> InteractionStatsResponse:
    """获取交互统计

    Examples:
        # 今天的统计
        GET /api/logs/interaction/stats/summary?since=2026-07-17T00:00:00

        # 最近 24 小时
        GET /api/logs/interaction/stats/summary?since=2026-07-16T12:00:00
    """

    entries, _ = _read_interaction_log(
        limit=100000,  # 读取所有
        category="interaction_complete",
        since=since,
    )

    total_interactions = len(entries)
    successful = sum(1 for e in entries if e.data.get("success", False))
    failed = total_interactions - successful

    latencies = [e.data.get("total_latency_ms", 0) for e in entries if e.data.get("total_latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    total_tokens = sum(e.data.get("tokens_used", 0) for e in entries)
    total_cost = sum(e.data.get("cost_usd", 0) for e in entries)

    # 统计引擎使用
    engines: dict[str, int] = {}
    for e in entries:
        engine = e.data.get("engine_used", "unknown")
        engines[engine] = engines.get(engine, 0) + 1

    return InteractionStatsResponse(
        total_interactions=total_interactions,
        successful=successful,
        failed=failed,
        avg_latency_ms=avg_latency,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        engines=engines
    )

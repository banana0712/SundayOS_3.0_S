"""Cognitive Router — dynamic engine selection + budgeted autonomy + fallback.

Implements docs/3.0/03-cognitive-engine-layer.md §3.4–§3.7. The scoring and
fallback logic here are pure and unit-tested offline (tests/test_router.py).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .base import Complexity, EngineMessage, EngineProvider, EngineResponse


# --- Complexity weight table (docs §3.5) ------------------------------------
#                         w_cap  w_cost  w_lat  w_avail
WEIGHTS: dict[Complexity, tuple[float, float, float, float]] = {
    Complexity.L1_INSTANT: (0.2, 0.5, 0.3, 0.3),
    Complexity.L2_DAILY:   (0.3, 0.4, 0.3, 0.3),
    Complexity.L3_DEEP:    (0.6, 0.2, 0.1, 0.3),
    Complexity.L4_CRITICAL:(0.8, 0.05, 0.05, 0.4),
}

_CODE_RE = re.compile(r"```|def |class |import |SELECT |function ")
_TOOL_RE = re.compile(r"(搜索|查一下|查询|发邮件|提交|运行|计算|日程|提醒|search|run|commit|schedule)")
_RISK_RE = re.compile(r"(删除|删掉|支付|付款|转账|权限|delete|drop|pay|purchase|rm -rf)")


@dataclass
class CognitiveRequest:
    messages: list[EngineMessage]
    complexity: Complexity | None = None
    require_tools: bool = False
    privacy_sensitive: bool = False
    prefer_chinese: bool = False
    latency_budget_ms: int = 3000
    max_cost_usd: float | None = None
    temperature: float = 0.7


@dataclass
class RouteTrace:
    complexity: int
    candidates: list[str]
    chosen: str | None
    scores: dict[str, float]
    reason: str
    fallbacks_used: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    errors: dict[str, str] = field(default_factory=dict)  # engine_id → why it failed


@dataclass
class CognitiveResult:
    response: EngineResponse | None
    trace: RouteTrace


def estimate_tokens(messages: list[EngineMessage]) -> int:
    return max(1, sum(len(m.content) for m in messages) // 4)


def _minmax(values: list[float]) -> list[float]:
    """Normalize to [0,1] across the set; all-equal → all 0 (no penalty)."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def heuristic_complexity(text: str) -> Complexity:
    """Cheap classifier fallback when no complexity given (docs §3.4)."""
    if _RISK_RE.search(text):
        return Complexity.L4_CRITICAL
    if _CODE_RE.search(text) or len(text) > 400:
        return Complexity.L3_DEEP
    if _TOOL_RE.search(text):
        return Complexity.L2_DAILY
    return Complexity.L1_INSTANT


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_s: float = 60.0):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._fails: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def record_failure(self, engine_id: str) -> None:
        self._fails[engine_id] = self._fails.get(engine_id, 0) + 1
        if self._fails[engine_id] >= self.threshold:
            self._opened_at[engine_id] = time.monotonic()

    def record_success(self, engine_id: str) -> None:
        self._fails.pop(engine_id, None)
        self._opened_at.pop(engine_id, None)

    def is_open(self, engine_id: str) -> bool:
        opened = self._opened_at.get(engine_id)
        if opened is None:
            return False
        if time.monotonic() - opened > self.cooldown_s:
            # cooldown elapsed → half-open, allow a retry
            self._opened_at.pop(engine_id, None)
            self._fails.pop(engine_id, None)
            return False
        return True


class CognitiveRouter:
    def __init__(self, engines: list[EngineProvider], breaker: CircuitBreaker | None = None):
        self.engines = engines
        self.breaker = breaker or CircuitBreaker()

    # -- candidate filtering (hard constraints, docs §3.5) -------------------
    def _eligible(self, req: CognitiveRequest, complexity: Complexity) -> list[EngineProvider]:
        est = estimate_tokens(req.messages)
        out: list[EngineProvider] = []
        for e in self.engines:
            if self.breaker.is_open(e.id):
                continue
            if req.require_tools and not e.caps.function_calling:
                continue
            if req.privacy_sensitive and not e.caps.local:
                continue
            if complexity >= Complexity.L3_DEEP and not e.caps.strong_reasoning:
                continue
            if e.caps.max_context < est:
                continue
            out.append(e)
        return out

    # -- scoring (docs §3.5) -------------------------------------------------
    @staticmethod
    def _capability(e: EngineProvider, req: CognitiveRequest) -> float:
        cap = 0.0
        if e.caps.strong_reasoning:
            cap += 0.6
        if e.caps.function_calling:
            cap += 0.2
        if req.prefer_chinese and "zh" in e.caps.languages:
            cap += 0.2
        return min(cap, 1.0)

    def _score_all(
        self, engines: list[EngineProvider], req: CognitiveRequest, complexity: Complexity
    ) -> dict[str, float]:
        """Batch scoring. Cost & latency are min-max normalized ACROSS the
        candidate set so they discriminate regardless of absolute token size
        (a tiny prompt still makes the pricey engine score ~1 on cost)."""
        if not engines:
            return {}
        w_cap, w_cost, w_lat, w_avail = WEIGHTS[complexity]
        est_in = estimate_tokens(req.messages)
        est_out = min(1024, est_in)

        raw_cost = [(e.price_in * est_in + e.price_out * est_out) for e in engines]
        raw_lat = [e.avg_latency_ms for e in engines]
        cost_n = _minmax(raw_cost)
        lat_n = _minmax(raw_lat)

        scores: dict[str, float] = {}
        for i, e in enumerate(engines):
            cap = self._capability(e, req)
            s = (w_cap * cap) - (w_cost * cost_n[i]) - (w_lat * lat_n[i]) + (w_avail * 1.0)
            scores[e.id] = round(s, 4)
        return scores

    def plan(self, req: CognitiveRequest) -> tuple[list[EngineProvider], RouteTrace]:
        """Pure decision step: returns ranked engines + a trace (no I/O)."""
        text = req.messages[-1].content if req.messages else ""
        complexity = req.complexity or heuristic_complexity(text)
        eligible = self._eligible(req, complexity)
        scores = self._score_all(eligible, req, complexity)
        ranked = sorted(eligible, key=lambda e: scores[e.id], reverse=True)
        reason = _explain(complexity, req)
        trace = RouteTrace(
            complexity=int(complexity),
            candidates=[e.id for e in ranked],
            chosen=ranked[0].id if ranked else None,
            scores=scores,
            reason=reason,
        )
        return ranked, trace

    async def route(self, req: CognitiveRequest) -> CognitiveResult:
        """Plan, then execute down the fallback chain until one succeeds."""
        ranked, trace = self.plan(req)
        t0 = time.monotonic()
        for i, engine in enumerate(ranked):
            try:
                resp = await engine.complete(req.messages, temperature=req.temperature)
                self.breaker.record_success(engine.id)
                trace.chosen = engine.id
                if i > 0:
                    trace.fallbacks_used = [e.id for e in ranked[:i]]
                trace.usage = {
                    "prompt_tokens": resp.prompt_tokens,
                    "completion_tokens": resp.completion_tokens,
                    "cost_usd": round(
                        (engine.price_in * resp.prompt_tokens
                         + engine.price_out * resp.completion_tokens) / 1_000_000, 6
                    ),
                }
                trace.latency_ms = round((time.monotonic() - t0) * 1000, 1)
                return CognitiveResult(response=resp, trace=trace)
            except Exception as exc:  # noqa: BLE001 — degrade gracefully, try next
                self.breaker.record_failure(engine.id)
                trace.fallbacks_used.append(engine.id)
                # capture the real reason so failures aren't silently swallowed
                trace.errors[engine.id] = f"{type(exc).__name__}: {str(exc)[:300]}"
        trace.latency_ms = round((time.monotonic() - t0) * 1000, 1)
        trace.chosen = None
        return CognitiveResult(response=None, trace=trace)


def _explain(complexity: Complexity, req: CognitiveRequest) -> str:
    bits = [f"complexity={complexity.name}"]
    if req.privacy_sensitive:
        bits.append("privacy→local only")
    if req.require_tools:
        bits.append("tools required")
    if complexity >= Complexity.L3_DEEP:
        bits.append("capability-weighted")
    else:
        bits.append("cost-weighted")
    return ", ".join(bits)

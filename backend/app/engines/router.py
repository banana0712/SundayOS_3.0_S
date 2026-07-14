"""Cognitive Router — dynamic engine selection + budgeted autonomy + fallback.

Implements docs/3.0/03-cognitive-engine-layer.md §3.4–§3.7. The scoring and
fallback logic here are pure and unit-tested offline (tests/test_router.py).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .base import Complexity, EngineMessage, EngineProvider, EngineResponse


# --- Quality-first weight table (ADR-011) -----------------------------------
# Each tuple = (w_quality, w_cap, w_cost, w_lat, w_avail)
# Quality is the PRIMARY axis for chat. Cost only gates extreme outliers.
#
# Philosophy: "Pick the best model for the task, not the cheapest one."
# Research base: Cascade Routing + Quality-Aware selection (FutureAGI 2026,
# Microsoft Foundry Model Router, Multi-LLM Prototype arXiv 2026).
WEIGHTS: dict[Complexity, tuple[float, float, float, float, float]] = {
    # L1 trivial tasks: still OK to optimize cost, but quality matters
    Complexity.L1_INSTANT: (0.25, 0.15, 0.30, 0.20, 0.30),
    # L2 daily chat: quality FIRST — this is the companion experience
    Complexity.L2_DAILY:   (0.40, 0.20, 0.10, 0.15, 0.30),
    # L3 deep reasoning: capability + quality dominate
    Complexity.L3_DEEP:    (0.35, 0.35, 0.05, 0.10, 0.30),
    # L4 critical: maximum quality, zero cost consideration
    Complexity.L4_CRITICAL:(0.50, 0.30, 0.00, 0.05, 0.35),
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

    # -- scoring (docs §3.5, ADR-011 quality-first) ----------------------------
    @staticmethod
    def _capability(e: EngineProvider, req: CognitiveRequest) -> float:
        """Capability score: reasoning + tools + language + quality."""
        cap = 0.0
        # Base quality (user-assigned or inferred, 0.0-1.0)
        cap += e.caps.quality * 0.5
        if e.caps.strong_reasoning:
            cap += 0.3
        if e.caps.function_calling:
            cap += 0.1
        if req.prefer_chinese and "zh" in e.caps.languages:
            cap += 0.1
        # Primary engine bonus: user's designated favorite gets a boost
        if e.caps.primary:
            cap += 0.15
        return min(cap, 1.0)

    def _score_all(
        self, engines: list[EngineProvider], req: CognitiveRequest, complexity: Complexity
    ) -> dict[str, float]:
        """Batch scoring. Quality + Capability weighted high, cost/latency
        act as soft constraints (ADR-011: quality-first)."""
        if not engines:
            return {}
        w_qual, w_cap, w_cost, w_lat, w_avail = WEIGHTS[complexity]
        est_in = estimate_tokens(req.messages)
        est_out = min(1024, est_in)

        raw_cost = [(e.price_in * est_in + e.price_out * est_out) for e in engines]
        raw_lat = [e.avg_latency_ms for e in engines]
        cost_n = _minmax(raw_cost)
        lat_n = _minmax(raw_lat)

        scores: dict[str, float] = {}
        for i, e in enumerate(engines):
            cap = self._capability(e, req)
            # Quality score: both explicit (caps.quality) and implicit (capability)
            qual = e.caps.quality  # 0.0-1.0
            s = (w_qual * qual) + (w_cap * cap) - (w_cost * cost_n[i]) - (w_lat * lat_n[i]) + (w_avail * 1.0)
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
                err_str = f"{type(exc).__name__}: {str(exc)[:300]}"
                trace.errors[engine.id] = err_str
                # Log the failure so it's visible in the console immediately
                from app.log_engine import log as _log
                _log.engine_error(engine.id, type(exc).__name__,
                                  err_str, attempt=i + 1)
                if i + 1 < len(ranked):
                    _log.engine_fallback(engine.id, ranked[i + 1].id, err_str)
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
        bits.append("capability-weighted (ADR-011 quality-first)")
    elif complexity == Complexity.L2_DAILY:
        bits.append("quality-first (ADR-011)")
    else:
        bits.append("balanced (ADR-011)")
    return ", ".join(bits)

"""Cognitive router tests (docs §3.4–§3.6)."""
import pytest

from app.engines.base import Complexity, EngineCapabilities, EngineMessage
from app.engines.providers import MockProvider
from app.engines.router import (
    CircuitBreaker,
    CognitiveRequest,
    CognitiveRouter,
    heuristic_complexity,
)


def _msg(text):
    return [EngineMessage(role="user", content=text)]


def _cheap_weak():
    return MockProvider(id="cheap", strong_reasoning=False, price_in=0.1, price_out=0.1)


def _expensive_strong():
    return MockProvider(id="strong", strong_reasoning=True, price_in=15.0, price_out=75.0)


def test_heuristic_complexity_levels():
    assert heuristic_complexity("你好") == Complexity.L1_INSTANT
    assert heuristic_complexity("帮我查一下天气") == Complexity.L2_DAILY
    assert heuristic_complexity("```python\ndef f(): pass\n```") == Complexity.L3_DEEP
    assert heuristic_complexity("帮我删除这个账户") == Complexity.L4_CRITICAL


def test_l1_prefers_cheap_engine():
    r = CognitiveRouter([_cheap_weak(), _expensive_strong()])
    ranked, trace = r.plan(CognitiveRequest(messages=_msg("你好"), complexity=Complexity.L1_INSTANT))
    assert ranked[0].id == "cheap"
    assert "balanced" in trace.reason


def test_l3_prefers_strong_engine():
    r = CognitiveRouter([_cheap_weak(), _expensive_strong()])
    ranked, trace = r.plan(CognitiveRequest(
        messages=_msg("设计一个多步算法并写代码"), complexity=Complexity.L3_DEEP))
    assert ranked[0].id == "strong"
    assert "capability-weighted" in trace.reason


def test_l3_filters_out_weak_engines():
    # weak engine lacks strong_reasoning → ineligible for L3
    r = CognitiveRouter([_cheap_weak()])
    ranked, trace = r.plan(CognitiveRequest(
        messages=_msg("复杂推理"), complexity=Complexity.L3_DEEP))
    assert ranked == []
    assert trace.chosen is None


def test_privacy_requires_local():
    remote = MockProvider(id="remote", strong_reasoning=True)
    remote.caps = EngineCapabilities(strong_reasoning=True, local=False)
    local = MockProvider(id="local", strong_reasoning=True)
    local.caps = EngineCapabilities(strong_reasoning=True, local=True)
    r = CognitiveRouter([remote, local])
    ranked, _ = r.plan(CognitiveRequest(
        messages=_msg("私密"), complexity=Complexity.L2_DAILY, privacy_sensitive=True))
    assert [e.id for e in ranked] == ["local"]


def test_require_tools_filters_non_tool_engines():
    no_tools = MockProvider(id="notool", function_calling=False)
    with_tools = MockProvider(id="tools", function_calling=True)
    r = CognitiveRouter([no_tools, with_tools])
    ranked, _ = r.plan(CognitiveRequest(
        messages=_msg("用工具"), complexity=Complexity.L2_DAILY, require_tools=True))
    assert all(e.caps.function_calling for e in ranked)


@pytest.mark.asyncio
async def test_route_returns_response():
    r = CognitiveRouter([_cheap_weak()])
    res = await r.route(CognitiveRequest(messages=_msg("你好"), complexity=Complexity.L1_INSTANT))
    assert res.response is not None
    assert res.trace.chosen == "cheap"
    assert res.trace.latency_ms >= 0


class _FailingProvider(MockProvider):
    async def complete(self, messages, temperature=0.7, tools=None, max_tokens=None):
        raise RuntimeError("simulated engine failure")


@pytest.mark.asyncio
async def test_fallback_chain_degrades_to_next_engine():
    failing = _FailingProvider(id="failing", strong_reasoning=True, price_in=0.1, price_out=0.1)
    backup = MockProvider(id="backup", strong_reasoning=True, price_in=20, price_out=60)
    r = CognitiveRouter([failing, backup])
    res = await r.route(CognitiveRequest(messages=_msg("hi"), complexity=Complexity.L3_DEEP))
    assert res.response is not None
    assert res.trace.chosen == "backup"
    assert "failing" in res.trace.fallbacks_used


def test_circuit_breaker_opens_after_threshold():
    b = CircuitBreaker(threshold=2, cooldown_s=60)
    assert not b.is_open("e1")
    b.record_failure("e1")
    assert not b.is_open("e1")
    b.record_failure("e1")
    assert b.is_open("e1")
    b.record_success("e1")
    assert not b.is_open("e1")

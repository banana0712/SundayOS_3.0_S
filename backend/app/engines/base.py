"""Engine abstraction — see docs/3.0/03-cognitive-engine-layer.md §3.3.

An EngineProvider is a swappable "cognitive engine". Sunday's identity does NOT
live here — it lives in memory, personality, goals. Engines are just the motor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import AsyncIterator, Literal


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------
@dataclass
class EngineMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    def to_openai(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class EngineCapabilities:
    function_calling: bool = False
    streaming: bool = True
    max_context: int = 32_000
    strong_reasoning: bool = False
    local: bool = False
    languages: tuple[str, ...] = ("en", "zh")


@dataclass
class EngineResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = "stop"


class Complexity(IntEnum):
    """Task cognitive complexity (docs §3.4)."""
    L1_INSTANT = 1     # intent/emotion classify, trivial Q&A
    L2_DAILY = 2       # chat, retrieval, summarization
    L3_DEEP = 3        # multi-step planning, decisions, code
    L4_CRITICAL = 4    # high-risk ops, compliance, safety


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------
class EngineProvider(ABC):
    """A single replaceable cognitive engine."""

    id: str
    caps: EngineCapabilities
    price_in: float = 0.0    # USD / 1M prompt tokens
    price_out: float = 0.0   # USD / 1M completion tokens
    avg_latency_ms: float = 800.0

    @abstractmethod
    async def complete(
        self,
        messages: list[EngineMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> EngineResponse:
        ...

    async def stream(
        self, messages: list[EngineMessage], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        # Default: fall back to a single complete() chunk.
        resp = await self.complete(messages, temperature=temperature)
        yield resp.text

    async def health(self) -> bool:
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Engine {self.id}>"

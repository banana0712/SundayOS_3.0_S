"""Concrete engine providers. One OpenAI-compatible class covers DeepSeek /
Qwen / Ling / OpenAI / Ollama; Anthropic is adapted separately.

SDKs are imported lazily so the backend runs (in mock mode) without them.
See docs/3.0/03-cognitive-engine-layer.md §3.8.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import AsyncIterator

from .base import (
    EngineCapabilities,
    EngineMessage,
    EngineProvider,
    EngineResponse,
)


class OpenAICompatibleProvider(EngineProvider):
    """DeepSeek / Qwen / Ling / OpenAI / local vLLM / Ollama."""

    def __init__(
        self,
        id: str,
        api_key: str,
        base_url: str,
        model: str,
        caps: EngineCapabilities,
        price_in: float = 0.0,
        price_out: float = 0.0,
    ):
        self.id = id
        self._model = model
        self.caps = caps
        self.price_in = price_in
        self.price_out = price_out
        self._api_key = api_key
        self._base_url = base_url
        self._client = None  # lazy

    def _ensure(self):
        if self._client is None:
            from openai import AsyncOpenAI  # lazy import

            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    async def complete(
        self,
        messages: list[EngineMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> EngineResponse:
        client = self._ensure()
        kwargs: dict = {
            "model": self._model,
            "messages": [m.to_openai() for m in messages],
            "temperature": temperature,
        }
        if tools and self.caps.function_calling:
            kwargs["tools"] = tools
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage
        return EngineResponse(
            text=choice.message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            tool_calls=[tc.model_dump() for tc in (choice.message.tool_calls or [])],
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self, messages: list[EngineMessage], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        client = self._ensure()
        stream = await client.chat.completions.create(
            model=self._model,
            messages=[m.to_openai() for m in messages],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class AnthropicProvider(EngineProvider):
    """Claude via the Anthropic SDK (different message shape)."""

    def __init__(
        self,
        id: str,
        api_key: str,
        model: str,
        caps: EngineCapabilities,
        base_url: str | None = None,
        price_in: float = 15.0,
        price_out: float = 75.0,
    ):
        self.id = id
        self._model = model
        self.caps = caps
        self.price_in = price_in
        self.price_out = price_out
        self._api_key = api_key
        self._base_url = base_url
        self._client = None

    def _ensure(self):
        if self._client is None:
            from anthropic import AsyncAnthropic  # lazy

            kw = {"api_key": self._api_key}
            if self._base_url:
                kw["base_url"] = self._base_url
            self._client = AsyncAnthropic(**kw)
        return self._client

    @staticmethod
    def _split(messages: list[EngineMessage]) -> tuple[str, list[dict]]:
        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        return system, turns

    async def complete(
        self,
        messages: list[EngineMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> EngineResponse:
        client = self._ensure()
        system, turns = self._split(messages)
        resp = await client.messages.create(
            model=self._model,
            system=system or None,
            messages=turns,
            temperature=temperature,
            max_tokens=max_tokens or 2048,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return EngineResponse(
            text=text,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            finish_reason=resp.stop_reason or "stop",
        )


class MockProvider(EngineProvider):
    """Deterministic offline engine. Lets memory/routing/dispatch run and be
    tested with zero external services (see .env SUNDAY_ALLOW_MOCK)."""

    def __init__(
        self,
        id: str = "mock",
        caps: EngineCapabilities | None = None,
        price_in: float = 0.0,
        price_out: float = 0.0,
        strong_reasoning: bool = True,
        function_calling: bool = True,
    ):
        self.id = id
        self.caps = caps or EngineCapabilities(
            function_calling=function_calling,
            strong_reasoning=strong_reasoning,
            local=True,
            max_context=128_000,
        )
        self.price_in = price_in
        self.price_out = price_out
        self.avg_latency_ms = 5.0

    async def complete(
        self,
        messages: list[EngineMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> EngineResponse:
        await asyncio.sleep(0)  # keep it truly async
        last = messages[-1].content if messages else ""
        digest = hashlib.sha256(last.encode("utf-8")).hexdigest()[:6]
        text = f"[mock:{self.id}] echo({digest}): {last[:120]}"
        return EngineResponse(
            text=text,
            prompt_tokens=sum(len(m.content) for m in messages) // 4,
            completion_tokens=len(text) // 4,
        )

    async def stream(
        self, messages: list[EngineMessage], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        resp = await self.complete(messages, temperature)
        for tok in resp.text.split(" "):
            yield tok + " "

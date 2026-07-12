"""Engine registry — builds the live engine set from environment config.

Adding a new engine = register its capabilities/price here. Zero upstream code
changes (docs/3.0/03-cognitive-engine-layer.md §3.8).
"""
from __future__ import annotations

import os

from .base import EngineCapabilities
from .providers import AnthropicProvider, MockProvider, OpenAICompatibleProvider


def build_engines() -> list:
    """Instantiate every engine that has credentials configured."""
    engines: list = []

    ds_key = os.getenv("DEEPSEEK_API_KEY")
    if ds_key:
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        engines.append(OpenAICompatibleProvider(
            id="deepseek-chat", api_key=ds_key, base_url=base, model="deepseek-chat",
            caps=EngineCapabilities(function_calling=True, max_context=64_000,
                                    languages=("zh", "en")),
            price_in=0.27, price_out=1.10,
        ))
        engines.append(OpenAICompatibleProvider(
            id="deepseek-reasoner", api_key=ds_key, base_url=base, model="deepseek-reasoner",
            caps=EngineCapabilities(strong_reasoning=True, max_context=64_000,
                                    languages=("zh", "en")),
            price_in=0.55, price_out=2.19,
        ))

    qwen_key = os.getenv("QWEN_API_KEY")
    if qwen_key:
        engines.append(OpenAICompatibleProvider(
            id="qwen-plus", api_key=qwen_key,
            base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            model="qwen-plus",
            caps=EngineCapabilities(function_calling=True, languages=("zh", "en")),
            price_in=0.4, price_out=1.2,
        ))

    oai_key = os.getenv("OPENAI_API_KEY")
    if oai_key:
        engines.append(OpenAICompatibleProvider(
            id="gpt-4o", api_key=oai_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model="gpt-4o",
            caps=EngineCapabilities(function_calling=True, strong_reasoning=True,
                                    max_context=128_000),
            price_in=2.5, price_out=10.0,
        ))

    ant_key = os.getenv("ANTHROPIC_API_KEY")
    if ant_key:
        engines.append(AnthropicProvider(
            id="claude-opus", api_key=ant_key, model="claude-opus-4-20250514",
            base_url=os.getenv("ANTHROPIC_BASE_URL") or None,
            caps=EngineCapabilities(function_calling=True, strong_reasoning=True,
                                    max_context=200_000),
            price_in=15.0, price_out=75.0,
        ))

    ollama = os.getenv("OLLAMA_API_KEY", "ollama")
    if os.getenv("OLLAMA_ENABLED", "").lower() in ("1", "true", "yes"):
        engines.append(OpenAICompatibleProvider(
            id="ollama-local", api_key=ollama,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            caps=EngineCapabilities(function_calling=False, local=True,
                                    languages=("zh", "en")),
        ))

    # Fallback: if nothing configured (and allowed), provide deterministic mocks
    # so memory/routing/dispatch still run offline.
    if not engines and os.getenv("SUNDAY_ALLOW_MOCK", "true").lower() != "false":
        engines = [
            MockProvider(id="mock-fast", strong_reasoning=False, price_in=0.1, price_out=0.1),
            MockProvider(id="mock-strong", strong_reasoning=True, price_in=5.0, price_out=15.0),
        ]

    return engines

"""LLM-based importance scoring — Generative Agents §Importance.

Scores each memory on a 1-10 scale using a lightweight engine call.
The prompt is adapted from "Generative Agents: Interactive Simulacra" (UIST 2023):
    "On the scale of 1 to 10, where 1 is purely mundane
     and 10 is extremely important, rate the likely importance
     of the following memory. Answer with a single digit."
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.base import EngineProvider

logger = logging.getLogger(__name__)

# There is no built-in fallback — if the engine call fails, we return the
# midpoint (5) rather than blocking the chat response.
_IMPORTANCE_PROMPT = (
    "在 1（纯日常琐事，例如 '今天天气不错'、'吃了个苹果'）到 10"
    "（极重要的核心记忆，例如 '被公司解雇'、'妻子怀孕了'、'决定换城市生活'）之间，"
    "为下面这条记忆的重要性打分，只输出一个 1-10 的整数：\n\n"
    "{content}"
)

_FALLBACK_SCORE = 5
_NUMBER_RE = re.compile(r"\d+")
_MAX_RETRIES = 2


async def score_importance(
    content: str,
    engine,  # EngineProvider that has .complete()
    temperature: float = 0.3,
) -> int:
    """Rate memory importance 1-10 using a lightweight LLM call.

    Returns 5 (midpoint) on any failure so chat isn't blocked.
    """
    from ..engines.base import EngineMessage

    prompt = _IMPORTANCE_PROMPT.format(content=content)
    messages = [EngineMessage(role="user", content=prompt)]

    for attempt in range(_MAX_RETRIES):
        try:
            resp = await engine.complete(messages, temperature=temperature)
            text = resp.text.strip()
            # Extract first number
            match = _NUMBER_RE.search(text)
            if match:
                score = int(match.group())
                return max(1, min(10, score))  # clamp to 1-10
        except Exception as e:
            logger.debug("importance scoring attempt %d failed: %s", attempt + 1, e)

    logger.debug("importance scoring failed after %d attempts, using %d",
                 _MAX_RETRIES, _FALLBACK_SCORE)
    return _FALLBACK_SCORE


# Synchronous wrapper for use in non-async contexts (auto-runs async).
def score_importance_sync(content: str, engine) -> int:
    """Same as score_importance but blocks until done. Use only in scripts."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(score_importance(content, engine))

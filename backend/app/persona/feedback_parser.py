"""Natural-language feedback parser — LLM-driven, structured output.

Philosophy (ADR-012, aligned with VAC 2026):
  "太啰嗦了" is richer than a 👎. Parsing natural language into
  structured preferences beats scalar ratings by 6-13%.

Design:
  - Uses the existing engine fleet (~100 tokens per parse)
  - Output constrained by JSON schema → no parsing ambiguity
  - Falls back gracefully: if the engine is down, return a neutral result
  - Non-blocking: never delays the feedback API response
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.router import CognitiveRouter

_PARSE_PROMPT = """分析这段用户反馈，提取偏好信息。只返回 JSON，不要其他文字。

反馈文本: "{text}"

JSON schema:
{{
  "dimension": "style" | "topic" | "engine" | "other",
  "style_value": "concise" | "detailed" | "casual" | "professional" | "",
  "topic": "tech" | "chat" | "creative" | "daily" | "",
  "topic_preference": "简短回答" | "详细解释" | "例子优先" | "直接结论" | "",
  "direction": "prefer" | "avoid",
  "summary": "一行中文，总结这条偏好（将注入系统提示）",
  "action": "prompt_inject" | "engine_adjust" | "both",
  "confidence": 0.0-1.0
}}

规则：
- 如果用户批评回复太长、啰嗦 → style_value=concise, direction=avoid, summary="用户喜欢简短的回复"
- 如果用户表扬分析深入 → topic_preference="详细解释", direction=prefer
- 如果用户说某个模型不好 → dimension=engine, action=engine_adjust
- 如果看不出明确偏好 → confidence=0.3, summary="通用反馈"
- summary 必须是一行可自然注入中文提示的句子，不超过 40 字"""


async def parse_feedback(
    feedback_text: str,
    router: CognitiveRouter,
) -> dict:
    """Parse user feedback text into structured preferences.

    Returns a dict with dimension/style_value/topic/direction/summary/etc.
    On any error, returns a neutral fallback.
    """
    from ..engines.base import Complexity, CognitiveRequest, EngineMessage

    prompt = _PARSE_PROMPT.replace("{text}", feedback_text.replace('"', "'"))

    try:
        ranked, _ = router.plan(CognitiveRequest(
            messages=[EngineMessage(role="user", content=prompt)],
            complexity=Complexity.L1_INSTANT,
        ))
        if not ranked:
            return _fallback(feedback_text)

        resp = await ranked[0].complete(
            [EngineMessage(role="user", content=prompt)],
            temperature=0.1,  # low temp for structured parsing
        )

        import json
        text = resp.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        result = json.loads(text)
        return _validate(result, feedback_text)

    except Exception:
        return _fallback(feedback_text)


def _validate(parsed: dict, original_text: str) -> dict:
    """Validate and normalize the parsed result."""
    valid_dimensions = {"style", "topic", "engine", "other"}
    valid_styles = {"concise", "detailed", "casual", "professional"}
    valid_directions = {"prefer", "avoid"}
    valid_actions = {"prompt_inject", "engine_adjust", "both"}

    return {
        "dimension": parsed.get("dimension", "other")
        if parsed.get("dimension") in valid_dimensions else "other",
        "style_value": parsed.get("style_value", "")
        if parsed.get("style_value") in valid_styles else "",
        "topic": parsed.get("topic", ""),
        "topic_preference": parsed.get("topic_preference", ""),
        "direction": parsed.get("direction", "prefer")
        if parsed.get("direction") in valid_directions else "prefer",
        "summary": parsed.get("summary", original_text[:40]),
        "action": parsed.get("action", "prompt_inject")
        if parsed.get("action") in valid_actions else "prompt_inject",
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
        "raw_text": original_text,
    }


def _fallback(text: str) -> dict:
    return {
        "dimension": "other",
        "style_value": "",
        "topic": "",
        "topic_preference": "",
        "direction": "prefer",
        "summary": text[:40] if text else "通用反馈",
        "action": "prompt_inject",
        "confidence": 0.3,
        "raw_text": text,
    }

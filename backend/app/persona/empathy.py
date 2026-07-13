"""XiaoIce Empathy Module — CQU→UU→IRG three-stage pipeline.

Implements the core EQ system from:
  Zhou et al., "The Design and Implementation of XiaoIce" (2019, §Empathy)

Phase 2 scope: UU (User Understanding) + IRG (Interpersonal Response Generation).
CQU (Contextual Query Understanding — entity resolution, anaphora) deferred.

UU produces an EmotionalSnapshot that feeds into both IRG (current-turn empathy
guidance) and BeliefState (persistent emotional model).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.router import CognitiveRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

# XiaoIce UU emotion taxonomy: 5 primary emotions
EMOTIONS = ["joy", "anger", "sadness", "fear", "calm"]
EMOTION_LABELS_ZH = {
    "joy": "喜悦", "anger": "愤怒", "sadness": "悲伤",
    "fear": "恐惧", "calm": "平静",
}

# XiaoIce UU dialogue acts: ~11 classes
DIALOGUE_ACTS = [
    "statement", "question", "request", "complaint",
    "greeting", "farewell", "thanks", "apology",
    "self_disclosure", "vent", "other",
]
DA_LABELS_ZH = {
    "statement": "陈述", "question": "提问", "request": "请求",
    "complaint": "抱怨", "greeting": "寒暄", "farewell": "告别",
    "thanks": "感谢", "apology": "道歉", "self_disclosure": "自我暴露",
    "vent": "宣泄", "other": "其他",
}


@dataclass
class EmotionalSnapshot:
    """One-turn UU output. Feeds into IRG and BeliefState."""
    primary_emotion: str         # "joy" | "anger" | "sadness" | "fear" | "calm"
    intensity: float             # 0.0 - 1.0
    secondary_emotion: str | None = None
    dialogue_act: str = "other"  # one of DIALOGUE_ACTS
    topic: str = ""              # brief topic label
    confidence: float = 0.7      # model confidence, used to weight persistence

    def to_zh(self) -> str:
        return (
            f"情绪: {EMOTION_LABELS_ZH.get(self.primary_emotion, self.primary_emotion)} "
            f"(强度 {self.intensity:.0%}), "
            f"行为: {DA_LABELS_ZH.get(self.dialogue_act, self.dialogue_act)}"
        )


# ---------------------------------------------------------------------------
# UU — User Understanding (emotion + intent via lightweight LLM)
# ---------------------------------------------------------------------------

_UU_PROMPT = (
    "分析以下用户消息的情绪和对话行为。\n\n"
    "用户消息：\"{message}\"\n\n"
    "请返回一个 JSON 对象，包含以下字段：\n"
    "- primary_emotion: 主要情绪，从 [\"joy\", \"anger\", \"sadness\", \"fear\", \"calm\"] 中选择\n"
    "- intensity: 情绪强度，0.0(极微弱) 到 1.0(极强烈)\n"
    "- secondary_emotion: 次要情绪，同上列表，无则填 null\n"
    "- dialogue_act: 对话行为，从 [\"statement\", \"question\", \"request\", \"complaint\", "
    "\"greeting\", \"farewell\", \"thanks\", \"apology\", \"self_disclosure\", \"vent\", \"other\"] 中选择\n"
    "- topic: 一句话概括话题核心（中文，5字以内）\n"
    "- confidence: 你对上述判断的整体置信度，0.0 到 1.0\n\n"
    "只输出 JSON，不要任何其他文字。"
)

# Cache: skip UU analysis for trivial greetings (save token)
_SKIP_UU_PATTERNS = {"hi", "你好", "你好呀", "hello", "hi there", "早", "晚安", "谢谢", "再见"}


def should_analyze(message: str) -> bool:
    """Skip UU for trivial one-word messages where emotion is obvious."""
    stripped = message.strip().lower()
    if len(stripped) <= 2:
        return False
    if stripped in _SKIP_UU_PATTERNS:
        return False
    return True


async def analyze_user(
    message: str,
    router: "CognitiveRouter",
) -> EmotionalSnapshot:
    """Run UU analysis via lightweight LLM call.

    Uses a cheap engine (L1_INSTANT) to classify emotion + dialogue act.
    Falls back to a rule-based default on failure.
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    if not should_analyze(message):
        return EmotionalSnapshot(
            primary_emotion="calm", intensity=0.3,
            dialogue_act="greeting", topic="问候", confidence=0.9,
        )

    import json as _json
    prompt = _UU_PROMPT.format(message=message)

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L1_INSTANT,  # cheapest engine for classification
        prefer_chinese=True,
        temperature=0.1,                  # low temp = deterministic
    )
    result = await router.route(req)

    if result.response is None:
        return _rule_based_fallback(message)

    # Parse JSON from response
    try:
        text = result.response.text.strip()
        # Some LLMs wrap JSON in markdown code blocks
        for marker in ("```json", "```"):
            if text.startswith(marker):
                text = text[len(marker):]
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()
        data = _json.loads(text)

        return EmotionalSnapshot(
            primary_emotion=data.get("primary_emotion", "calm"),
            intensity=float(data.get("intensity", 0.5)),
            secondary_emotion=data.get("secondary_emotion"),
            dialogue_act=data.get("dialogue_act", "other"),
            topic=data.get("topic", ""),
            confidence=float(data.get("confidence", 0.5)),
        )
    except Exception as e:
        logger.debug("UU LLM parse failed: %s, falling back to rules", e)
        return _rule_based_fallback(message)


# ---------------------------------------------------------------------------
# Rule-based fallback (offline, no LLM call)
# ---------------------------------------------------------------------------

def _rule_based_fallback(message: str) -> EmotionalSnapshot:
    """Quick regex-based emotion detection when LLM is unavailable."""
    m = message.strip()

    # Joy indicators
    if any(w in m for w in ("哈哈", "开心", "太好了", "喜欢", "嘿嘿", "😊", "😄", "棒", "赞")):
        return EmotionalSnapshot("joy", 0.7, dialogue_act="self_disclosure", topic="喜悦")

    # Sadness
    if any(w in m for w in ("难过", "伤心", "哭", "失落", "遗憾", "😢", "😭", "沮丧")):
        return EmotionalSnapshot("sadness", 0.7, dialogue_act="self_disclosure", topic="悲伤")

    # Anger
    if any(w in m for w in ("气死", "混蛋", "滚", "烦死了", "受不了", "😡", "🤬", "凭什么")):
        return EmotionalSnapshot("anger", 0.8, dialogue_act="complaint", topic="愤怒")

    # Fear / anxiety
    if any(w in m for w in ("害怕", "担心", "焦虑", "紧张", "万一", "怎么办", "😨", "😰")):
        return EmotionalSnapshot("fear", 0.6, dialogue_act="self_disclosure", topic="恐惧")

    # Questions
    if "?" in m or "？" in m or any(w in m for w in ("什么", "怎么", "为什么", "吗", "呢")):
        return EmotionalSnapshot("calm", 0.3, dialogue_act="question", topic="疑问")

    # Default
    return EmotionalSnapshot("calm", 0.3, dialogue_act="statement", topic="话题")


# ---------------------------------------------------------------------------
# IRG — Interpersonal Response Generation (empathy guidance)
# ---------------------------------------------------------------------------

def build_empathy_guidance(snapshot: EmotionalSnapshot) -> str:
    """Generate the empathy injection for the system prompt.

    Based on XiaoIce's IRG: the empathy vector eR conditions the response
    on both content (eQ) and emotion (eR), while respecting persona.

    Returns an empty string if the emotion is mild calm (no guidance needed).
    """
    if snapshot.primary_emotion == "calm" and snapshot.intensity < 0.5:
        return ""

    parts: list[str] = []
    emo = snapshot.primary_emotion
    intensity = snapshot.intensity
    act = snapshot.dialogue_act

    # Core empathy rule per emotion (XiaoIce §IRG)
    guidance = {
        "joy": "用户正在表达喜悦。你的任务是**共鸣并放大这份快乐**——不要扫兴，不要转移话题。和他一起开心。",
        "sadness": (
            "用户可能感到悲伤。**先倾听，再共情，最后才给建议**。"
            "不要说'别难过了'或'振作起来'——这会让对方觉得情绪不被允许。"
            "用'听起来…'、'我能感觉到…'开头，让对方知道你在陪他。"
        ),
        "anger": (
            "用户正在生气或不满。**先认可情绪的合理性**——不要急着讲道理或劝解。"
            "说'这确实让人生气'比说'冷静一下'有效得多。"
            "等情绪稍微平复后，再温和地提出建设性的视角。"
        ),
        "fear": (
            "用户可能在担心或焦虑。**提供安全感，而不是解决方案**。"
            "说'我在这里'比说'你应该…'更有用。"
            "承认不确定性的存在，但提醒他——他不需要一个人面对。"
        ),
        "calm": "用户情绪平稳。自然地推进对话，不需要特殊的情感处理。",
    }

    base = guidance.get(emo, guidance["calm"])

    # Intensity modifier
    if intensity > 0.7:
        base += f"\n情绪强度较高（{intensity:.0%}），需要更多共情空间，少说教。"
    elif intensity < 0.3:
        base += f"\n情绪较轻微（{intensity:.0%}），点到为止即可。"

    # Dialogue act modifier
    if act == "vent":
        base += "\n用户正在宣泄情绪——不需要解决方案，只需要倾听。"
    elif act == "self_disclosure":
        base += "\n用户正在敞开心扉——这是建立信任的时刻。真诚回应。"
    elif act == "complaint":
        base += "\n用户在抱怨——先认可感受，再提供建设性视角。"

    parts.append(base)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Combined pipeline: UU → IRG → BeliefState update
# ---------------------------------------------------------------------------

async def run_empathy_pipeline(
    message: str,
    router: "CognitiveRouter",
    belief: "BeliefState | None" = None,
) -> tuple[EmotionalSnapshot, str]:
    """Run the full UU→IRG pipeline for one turn.

    Returns (emotional_snapshot, empathy_guidance_string).
    The guidance string is empty if no emotional adjustment is needed.

    Also updates the BeliefState if provided.
    """
    snapshot = await analyze_user(message, router)

    # Update BeliefState
    if belief is not None and snapshot.confidence > 0.5:
        # Exponential moving average: smooth emotional transitions
        alpha = 0.3  # weight for new observation
        if snapshot.primary_emotion == "joy":
            belief.emotional_state.mood = round(
                belief.emotional_state.mood * (1 - alpha) + snapshot.intensity * alpha, 2
            )
        elif snapshot.primary_emotion == "sadness":
            belief.emotional_state.mood = round(
                belief.emotional_state.mood * (1 - alpha) + (1 - snapshot.intensity) * alpha, 2
            )
            belief.emotional_state.stress = min(1.0, round(
                belief.emotional_state.stress + snapshot.intensity * 0.2, 2
            ))
        elif snapshot.primary_emotion == "anger":
            belief.emotional_state.stress = min(1.0, round(
                belief.emotional_state.stress + snapshot.intensity * 0.3, 2
            ))
        elif snapshot.primary_emotion == "fear":
            belief.emotional_state.stress = min(1.0, round(
                belief.emotional_state.stress + snapshot.intensity * 0.2, 2
            ))
            belief.emotional_state.energy = round(
                belief.emotional_state.energy * 0.8 + 0.2 * (1 - snapshot.intensity), 2
            )
        elif snapshot.primary_emotion == "calm":
            # Decay stress during calm moments
            belief.emotional_state.stress = max(0.0, round(
                belief.emotional_state.stress * 0.95, 2
            ))

        belief.emotional_state.mood = max(0.0, min(1.0, belief.emotional_state.mood))
        belief.emotional_state.stress = max(0.0, min(1.0, belief.emotional_state.stress))

    # Build guidance
    guidance = build_empathy_guidance(snapshot)

    return snapshot, guidance

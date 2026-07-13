"""Context Builder — topic-aware cross-session context assembly.

Based on:
  Engram (2026): "A lean retrieved context (~9.6k tokens) beats full history (~79k)"
  GAM (2026): Topic associative networks across sessions
  APEX-MEM (2026): Temporal grounding of conversational events

Replaces simple top-K semantic retrieval with a structured pipeline:
  1. Topic extraction — cheap LLM call to identify current topic
  2. Topic-network retrieval — find all memories touching the topic (cross-session)
  3. Temporal sorting — recency × importance × topical_relevance
  4. Context assembly — profile summary + topic history + reflections + beliefs
  5. Capped at ~3000 tokens (~2400 Chinese chars)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..memory.store import MemoryStore
    from ..engines.router import CognitiveRouter

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 3000     # Engram: 9.6k beats 79k, but we'll be conservative
TOPIC_K = 20                  # memories per topic (cross-session)
TOPIC_WEIGHT = 1.5            # multiplier for topic-matched memories in scoring


@dataclass
class AssembledContext:
    """Structured context ready for injection into the system prompt."""
    profile: str = ""           # user profile summary (from semantic memories)
    topic_history: str = ""     # memories relevant to current topic
    reflections: str = ""       # related reflection insights
    belief_snapshot: str = ""   # current belief state summary
    total_chars: int = 0

    def to_prompt_section(self) -> str:
        """Build the compact prompt injection."""
        parts = []
        if self.profile:
            parts.append(f"[用户画像]\n{self.profile}")
        if self.belief_snapshot and len(self.belief_snapshot) > 5:
            parts.append(f"[当前状态]\n{self.belief_snapshot}")
        if self.reflections:
            parts.append(f"[相关洞察]\n{self.reflections}")
        if self.topic_history:
            parts.append(f"[相关记忆]\n{self.topic_history}")
        return "\n\n".join(parts)

    def __bool__(self) -> bool:
        return self.total_chars > 0


# ---------------------------------------------------------------------------
# Topic Extraction (cheap LLM call)
# ---------------------------------------------------------------------------

_TOPIC_PROMPT = (
    "从下面这条用户消息中，提取 1-3 个话题关键词（用逗号分隔），"
    "同时判断这个消息是否延续了之前的某个话题（是/否）。"
    "每个话题关键词不超过 5 个字。只输出关键词和是/否，不要其他文字。\n\n"
    "消息：{message}\n\n"
    "关键词："
)


async def _extract_topics(message: str, router: "CognitiveRouter") -> list[str]:
    """Extract 1-3 topic tags from the user message via cheap LLM call."""
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    prompt = _TOPIC_PROMPT.format(message=message)
    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L1_INSTANT,
        prefer_chinese=True,
        temperature=0.1,
    )
    result = await router.route(req)
    if result.response is None:
        return _rule_topics(message)

    text = result.response.text.strip()
    # Parse "跑步, 健康, 运动\n是" or "旅行\n否"
    # Take the first line, strip the 是/否 suffix
    first_line = text.split("\n")[0].strip()
    # Remove trailing continuation indicator
    for suffix in ("是", "否", "yes", "no", "Yes", "No"):
        if first_line.endswith(suffix):
            first_line = first_line[:-len(suffix)].strip()
    tags = [t.strip() for t in first_line.replace("，", ",").split(",") if t.strip()]
    return tags[:3] if tags else _rule_topics(message)


def _rule_topics(message: str) -> list[str]:
    """Fallback keyword extraction when LLM is unavailable."""
    m = message.strip()
    topic_map = {
        "运动": ["跑步", "健身", "运动", "游泳", "骑车", "锻炼", "训练"],
        "健康": ["生病", "医院", "药", "体检", "健康", "累", "睡眠", "失眠"],
        "工作": ["工作", "上班", "项目", "会议", "老板", "同事", "代码", "编程"],
        "学习": ["学", "课程", "考试", "书", "教材", "日语", "英语", "翻译"],
        "感情": ["喜欢", "爱", "分手", "约会", "恋爱", "结婚"],
        "生活": ["吃饭", "天气", "购物", "买东西", "做饭", "打扫"],
        "旅行": ["旅行", "旅游", "机票", "酒店", "出国", "东京", "日本"],
    }
    for tag, keywords in topic_map.items():
        if any(kw in m for kw in keywords):
            return [tag]
    return ["日常"]


# ---------------------------------------------------------------------------
# Context Assembly
# ---------------------------------------------------------------------------

async def build_context(
    message: str,
    user_id: str,
    store: "MemoryStore",
    router: "CognitiveRouter",
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> AssembledContext:
    """Build topic-aware, cross-session context for the current message.

    This replaces the simple `MEMORY.retrieve(k=6)` call with a structured
    pipeline that retrieves memories across sessions connected by topic,
    sorted by temporal relevance, and capped at ~3000 tokens.
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    ctx = AssembledContext()
    all_nodes = store.all(user_id)
    if not all_nodes:
        return ctx

    from ..memory.schema import MemoryType

    # 1. Extract topics from the message
    topics = await _extract_topics(message, router)

    # 2. Retrieve topic-relevant memories (cross-session)
    topic_memories: list = []
    for topic in topics:
        # Use broader search — search for the topic tag itself and a
        # combined semantic query
        hits = store.retrieve(topic, user_id=user_id, k=TOPIC_K)
        for h in hits:
            # Boost score for topic-matched memories
            h.score *= TOPIC_WEIGHT
            topic_memories.append(h)

    # Also do a direct semantic search with the raw message
    raw_hits = store.retrieve(message, user_id=user_id, k=10)

    # Deduplicate and merge
    seen_ids: set[str] = set()
    merged: list = []
    for h in topic_memories + raw_hits:
        if h.node.id not in seen_ids:
            seen_ids.add(h.node.id)
            merged.append(h)
    merged.sort(key=lambda h: h.score, reverse=True)

    # 3. Separate memories by type for structured assembly
    episodic_memories = [h for h in merged if h.node.type == MemoryType.EPISODIC]
    semantic_memories = [h for h in merged if h.node.type == MemoryType.SEMANTIC]
    reflection_memories = [h for h in merged if h.node.type == MemoryType.REFLECTION]
    experience_memories = [h for h in merged if h.node.type == MemoryType.EXPERIENCE]

    # 4. Build profile (from semantic memories + experiences)
    profile_parts = []
    for h in semantic_memories[:5]:
        profile_parts.append(h.node.content)
    for h in experience_memories[:3]:
        profile_parts.append(h.node.content)
    ctx.profile = "\n".join(f"- {p}" for p in profile_parts[:8])

    # 5. Build topic history (from episodic memories, with time anchors)
    history_parts = []
    for i, h in enumerate(episodic_memories[:15]):
        # Add relative time anchor — "3天前", "上周", "1个月前"
        time_anchor = _time_anchor(h.node.created_at)
        history_parts.append(f"[{time_anchor}] {h.node.content}")
    ctx.topic_history = "\n".join(history_parts[:15])
    # Ensure we don't blow the context cap: ~2400 Chinese chars
    if len(ctx.topic_history) > 2400:
        ctx.topic_history = ctx.topic_history[:2400] + "\n…(更多历史记忆已省略)"

    # 6. Build reflections (relevant insights)
    ref_parts = []
    for h in reflection_memories[:5]:
        ref_parts.append(h.node.content)
    ctx.reflections = "\n".join(f"- {r}" for r in ref_parts[:5])

    # 7. Calculate total
    ctx.total_chars = (
        len(ctx.profile) + len(ctx.topic_history) +
        len(ctx.reflections) + len(ctx.belief_snapshot)
    )
    logger.debug(
        "context built: topics=%s profile=%d chars history=%d chars "
        "reflections=%d total=%d",
        topics, len(ctx.profile), len(ctx.topic_history),
        len(ctx.reflections), ctx.total_chars,
    )
    return ctx


# ---------------------------------------------------------------------------
# Time anchor helper
# ---------------------------------------------------------------------------

def _time_anchor(dt: datetime) -> str:
    """Convert a datetime to a human-readable time anchor in Chinese."""
    now = datetime.now(timezone.utc)
    delta = now - dt.replace(tzinfo=dt.tzinfo or timezone.utc)
    seconds = delta.total_seconds()
    if seconds < 3600:
        return f"{int(seconds // 60)}分钟前"
    if seconds < 86400:
        return f"{int(seconds // 3600)}小时前"
    if seconds < 604800:
        return f"{int(seconds // 86400)}天前"
    if seconds < 2592000:
        return f"{int(seconds // 604800)}周前"
    if seconds < 31536000:
        return f"{int(seconds // 2592000)}个月前"
    return f"{int(seconds // 31536000)}年前"

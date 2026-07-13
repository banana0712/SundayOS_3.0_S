"""Reflection Engine (L1→L2) — Generative Agents two-step pipeline.

Implements the exact algorithm from:
  Park et al., "Generative Agents: Interactive Simulacra of Human Behavior"
  (UIST 2023, §Reflection)

Pipeline:
  1. Take the most recent 100 memories.
  2. Ask the LLM: "What are the 3 most salient high-level questions we can
     answer about this user based on this information?"
  3. For each question, retrieve relevant memories as evidence.
  4. Ask the LLM to synthesize an insight, citing source memory IDs.
  5. Write the insight back as a REFLECTION node (with evidence_ids).

Trigger conditions (any one):
  - Cumulative importance of the last 100 memories > θ (default 100).
  - End of a conversation where cumulative importance > 30.
  - Manual trigger via API.

Reflections can recursively trigger further reflections (abstraction tree).
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import MemoryStore
    from ..engines.router import CognitiveRouter, CognitiveRequest

logger = logging.getLogger(__name__)

_REFLECTION_IMPORTANCE = 8  # reflections are always high-importance
_RECENT_COUNT = 100          # look at the 100 most recent memories
_TRIGGER_THRESHOLD = 100     # cumulative importance to auto-trigger
_SESSION_TRIGGER = 30        # session-end cumulative importance threshold
_QUESTION_COUNT = 3           # number of high-level questions to generate
_EVIDENCE_K = 8              # how many memories to retrieve per question


# ── prompt templates (from Generative Agents paper, adapted to Chinese) ─────

_QUESTIONS_PROMPT = (
    "你是一个反思助手。你需要根据用户近期的记忆，提炼出关于该用户的最值得追问的高层问题。\n\n"
    "以下是用户最近的记忆，每条以 [id] 内容 的格式呈现：\n\n"
    "{memories}\n\n"
    "仅根据以上信息，关于该用户我们可以问哪 3 个最显著的高层问题？\n"
    "每个问题应该能揭示用户深层的偏好、行为模式、或重要趋势。\n"
    "只输出 3 个问题，每行一个，不要编号，不要任何其他文字。"
)

_INSIGHT_PROMPT = (
    "你是一个反思助手。请基于以下记忆片段，回答这个关于用户的问题。\n\n"
    "**问题**：{question}\n\n"
    "**相关记忆**：\n"
    "{evidence}\n\n"
    "请给出一个简洁、有洞察力的回答（2-4 句话），并在回答末尾附上你引用的记忆 ID 列表。\n"
    "格式：\n"
    "回答：<你的洞察>\n"
    "引用：[mem_xxx, mem_yyy, ...]"
)


# ── trigger logic ───────────────────────────────────────────────────────────

def _should_reflect(store: "MemoryStore", user_id: str,
                    recent_count: int = _RECENT_COUNT,
                    threshold: int = _TRIGGER_THRESHOLD) -> bool:
    """Check if the cumulative importance of recent memories exceeds threshold.

    Only considers L1 (EPISODIC / SEMANTIC / PROCEDURAL) memories — not
    existing REFLECTION or EXPERIENCE nodes (to avoid infinite loops).

    Returns True if reflection should trigger.
    """
    from .schema import MemoryType

    all_nodes = store.all(user_id)
    # filter to only primary memories
    primary = [
        n for n in all_nodes
        if n.type in (MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.PROCEDURAL)
    ]
    recent = sorted(primary, key=lambda n: n.created_at, reverse=True)[:recent_count]
    total_importance = sum(n.importance for n in recent)
    logger.debug(
        "reflection check: user=%s recent_count=%d total_importance=%d threshold=%d",
        user_id, len(recent), total_importance, threshold,
    )
    return total_importance >= threshold


def _should_reflect_session(store: "MemoryStore", user_id: str,
                            session_importance: int = 0,
                            threshold: int = _SESSION_TRIGGER) -> bool:
    """Check if session-end reflection should trigger."""
    return session_importance >= threshold


# ── two-step pipeline ───────────────────────────────────────────────────────

async def _generate_questions(
    store: "MemoryStore", user_id: str, router: "CognitiveRouter",
    recent_count: int = _RECENT_COUNT,
) -> list[str]:
    """Step 1: Generate 3 high-level questions from recent memories."""
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    all_nodes = store.all(user_id)
    recent = sorted(all_nodes, key=lambda n: n.created_at, reverse=True)[:recent_count]

    if not recent:
        return []

    # Build memory list for the prompt
    memory_lines = [
        f"[{n.id}] {n.content}" for n in recent
    ]
    prompt = _QUESTIONS_PROMPT.format(memories="\n".join(memory_lines))

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L3_DEEP,
        prefer_chinese=True,
        temperature=0.4,
    )
    result = await router.route(req)
    if result.response is None:
        logger.warning("reflection: question generation failed (all engines down)")
        return []

    # Parse questions — each line is one question
    lines = [line.strip() for line in result.response.text.strip().split("\n") if line.strip()]
    questions = lines[:_QUESTION_COUNT]
    logger.debug("reflection: generated %d questions", len(questions))
    return questions


async def _synthesize_insight(
    question: str, store: "MemoryStore", user_id: str, router: "CognitiveRouter",
    k: int = _EVIDENCE_K,
) -> tuple[str, list[str]] | None:
    """Step 2: Retrieve evidence + synthesize one insight.

    Returns (insight_text, evidence_ids) or None on failure.
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    # Retrieve relevant memories for this question
    hits = store.retrieve(question, user_id=user_id, k=k)
    if not hits:
        return None

    evidence_lines = [f"[{h.node.id}] {h.node.content}" for h in hits]
    prompt = _INSIGHT_PROMPT.format(
        question=question,
        evidence="\n".join(evidence_lines),
    )

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L3_DEEP,
        prefer_chinese=True,
        temperature=0.5,
    )
    result = await router.route(req)
    if result.response is None:
        logger.warning("reflection: insight synthesis failed for question: %s", question[:60])
        return None

    text = result.response.text.strip()

    # Parse: "回答：<insight>\n引用：[id1, id2, ...]"
    insight = text
    evidence_ids: list[str] = []
    citation_match = re.search(r"引用[：:]\s*\[([^\]]+)\]", text)
    if citation_match:
        refs = citation_match.group(1)
        evidence_ids = [rid.strip() for rid in refs.split(",") if rid.strip()]
        # Remove citation line from insight
        insight = text[: citation_match.start()].strip()
    insight = re.sub(r"^回答[：:]\s*", "", insight).strip()

    return insight, evidence_ids


# ── main public API ─────────────────────────────────────────────────────────

async def run_reflection(
    store: "MemoryStore", user_id: str, router: "CognitiveRouter",
    recent_count: int = _RECENT_COUNT,
    question_count: int = _QUESTION_COUNT,
) -> list[dict]:
    """Run the full reflection pipeline and write insights to the store.

    Returns a list of dicts: [{id, content, evidence_ids, question}].

    Safe to call in a background task (asyncio.create_task).
    """
    from .schema import MemoryNode, MemoryType

    # Step 1: Generate questions
    questions = await _generate_questions(store, user_id, router, recent_count)
    if not questions:
        return []

    # Step 2: Synthesize insights for each question
    insights = []
    for question in questions[:question_count]:
        result = await _synthesize_insight(question, store, user_id, router)
        if result is None:
            continue
        insight_text, evidence_ids = result

        # Step 3: Write REFLECTION node
        node = MemoryNode(
            content=insight_text,
            user_id=user_id,
            type=MemoryType.REFLECTION,
            importance=_REFLECTION_IMPORTANCE,
            evidence_ids=evidence_ids,
            source="reflection",
        )
        store.add(node)
        insights.append({
            "id": node.id,
            "content": insight_text,
            "evidence_ids": evidence_ids,
            "question": question,
        })

    logger.info("reflection: generated %d insights for user %s", len(insights), user_id)
    return insights


def schedule_reflection(store: "MemoryStore", user_id: str, router: "CognitiveRouter",
                        session_importance: int = 0) -> None:
    """Schedule a reflection in the background if conditions are met.

    Call this after writing memories to the store. It checks trigger
    conditions and, if satisfied, launches reflection as a background task.

    Args:
        store: MemoryStore instance
        user_id: user identifier
        router: CognitiveRouter instance
        session_importance: cumulative importance of the current session
    """
    should_run = _should_reflect(store, user_id)

    if not should_run and session_importance > 0:
        should_run = _should_reflect_session(store, user_id, session_importance)

    if should_run:
        logger.info("reflection triggered for user %s (session_imp=%d)", user_id, session_importance)
        try:
            asyncio.create_task(run_reflection(store, user_id, router))
        except RuntimeError:
            # No event loop running (e.g. in tests) — skip
            logger.debug("reflection: no event loop, skipping auto-trigger")


# ── sync wrapper (for testing) ──────────────────────────────────────────────

def run_reflection_sync(store: "MemoryStore", user_id: str, router: "CognitiveRouter") -> list[dict]:
    """Synchronous wrapper for test contexts."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_reflection(store, user_id, router))
    finally:
        loop.close()

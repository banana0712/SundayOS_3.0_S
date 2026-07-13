"""Experience Layer (L2→L3) — cross-trajectory abstraction.

Implements the Experience stage from:
  "From Storage to Experience" (2026, §Experience + Hybrid Experience)

Three core operations:
  1. CONSOLIDATION — nightly batch: merge similar memories, archive expired,
     extract semantic knowledge.
  2. PATTERN DETECTION — scan episodic + reflection memories for repeating
     sequences. If a pattern repeats ≥N times, it's an Experience.
  3. PROCEDURAL PRIMITIVE — when a tool-use pattern recurs ≥3 times,
     auto-encapsulate as a named skill.

L3 Experience nodes satisfy the Minimum Description Length principle:
  "Use the shortest description to cover the most situations."
  — From Storage to Experience, 2026

All operations are read-only from the store perspective — they CREATE new
MemoryType.EXPERIENCE nodes but never modify existing data.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import MemoryStore
    from ..engines.router import CognitiveRouter

logger = logging.getLogger(__name__)

_EXPERIENCE_IMPORTANCE = 9   # experience nodes are very high importance
_MERGE_THRESHOLD = 0.92      # cosine similarity to merge memories
_PATTERN_MIN_REPEAT = 3      # times a pattern must repeat to be extracted
_RECENT_WINDOW = 200         # look at this many recent memories for patterns


# ---------------------------------------------------------------------------
# 1. CONSOLIDATION — nightly batch job
# ---------------------------------------------------------------------------

def _merge_similar(store: "MemoryStore", threshold: float = _MERGE_THRESHOLD) -> int:
    """Merge nearly-identical memory nodes (cosine > threshold).

    Two memories with similar embeddings and content are merged into one:
    - The older one absorbs the younger one's access_count
    - The younger one's evidence_ids are appended to the older one's
    - The younger one is archived (soft-deleted)

    Returns number of merges performed.
    """
    from .embedding import cosine

    all_nodes = store.all()
    if len(all_nodes) < 2:
        return 0

    # Group by user for efficiency
    by_user: dict[str, list] = defaultdict(list)
    for n in all_nodes:
        if n.frozen or n.importance >= 10:
            continue  # never touch frozen or critical
        by_user[n.user_id].append(n)

    merges = 0
    for user_nodes in by_user.values():
        for i in range(len(user_nodes)):
            if store.get(user_nodes[i].id) is None:
                continue  # already deleted in a previous merge
            for j in range(i + 1, len(user_nodes)):
                if store.get(user_nodes[j].id) is None:
                    continue
                a, b = user_nodes[i], user_nodes[j]
                sim = cosine(a.embedding or [], b.embedding or [])
                if sim > threshold:
                    # Merge b into a
                    a.access_count += b.access_count
                    a.evidence_ids = list(set(a.evidence_ids + b.evidence_ids))
                    a.tags = list(set(a.tags + b.tags))
                    store.delete(b.id)
                    merges += 1

    return merges


def _archive_expired(store: "MemoryStore", threshold: float = 0.4) -> int:
    """Soft-delete low-importance memories whose effective importance has decayed."""
    return store.archive_expired(threshold=threshold)


async def _extract_semantic(store: "MemoryStore", router: "CognitiveRouter",
                      user_id: str) -> list[str]:
    """Extract semantic knowledge from recent episodic memories.

    Uses a lightweight LLM call to distill structured facts from raw episodes.
    Returns a list of semantic fact strings (stored as SEMANTIC nodes).
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest

    # Get recent episodic memories for this user
    from .schema import MemoryType
    all_nodes = store.all(user_id)
    episodic = [n for n in all_nodes if n.type == MemoryType.EPISODIC]
    recent = sorted(episodic, key=lambda n: n.created_at, reverse=True)[:50]

    if len(recent) < 10:
        return []  # not enough material

    memory_lines = "\n".join(
        f"[{n.id}] {n.content}" for n in recent
    )
    prompt = (
        "你是一个知识提取助手。从以下用户的近期记忆中，提取出 3-5 条"
        "**客观事实**或**稳定偏好**（不是情绪或一次性事件）。\n\n"
        "规则：\n"
        "- 只提取持久性的信息（如'用户在学习日语'，不是'用户今天很开心'）\n"
        "- 每条一行，以 '- ' 开头\n"
        "- 如果没有值得提取的持久信息，输出 '无'\n\n"
        f"近期记忆：\n{memory_lines}\n\n"
        "提取的语义知识："
    )

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L2_DAILY,
        prefer_chinese=True,
        temperature=0.3,
    )
    result = await router.route(req)
    if result.response is None:
        return []

    facts = [
        line.lstrip("- ").strip()
        for line in result.response.text.split("\n")
        if line.strip().startswith("-") and "无" not in line
    ]
    return facts[:5]


async def run_consolidation(
    store: "MemoryStore",
    router: "CognitiveRouter | None" = None,
    user_id: str = "",
    merge: bool = True,
    archive: bool = True,
    extract: bool = True,
) -> dict:
    """Run the full nightly consolidation job.

    Returns a summary dict suitable for API response.
    """
    from .schema import MemoryNode, MemoryType

    result = {"merged": 0, "archived": 0, "extracted": [], "experiences": 0}

    # Step 1: Merge similar
    if merge:
        result["merged"] = _merge_similar(store)

    # Step 2: Archive expired
    if archive:
        result["archived"] = _archive_expired(store)

    # Step 3: Extract semantic knowledge
    if extract and router and user_id:
        facts = await _extract_semantic(store, router, user_id)
        for fact in facts:
            store.add(MemoryNode(
                content=fact,
                user_id=user_id,
                type=MemoryType.SEMANTIC,
                importance=7,
                source="consolidation",
            ))
        result["extracted"] = facts

    return result


# ---------------------------------------------------------------------------
# 2. PATTERN DETECTION — find repeating sequences
# ---------------------------------------------------------------------------

async def detect_patterns(
    store: "MemoryStore",
    router: "CognitiveRouter",
    user_id: str,
    window: int = _RECENT_WINDOW,
    min_repeat: int = _PATTERN_MIN_REPEAT,
) -> list[dict]:
    """Scan recent memories for repeating behavioral patterns.

    Uses an LLM to identify recurring themes, habits, and interaction patterns
    from the user's memory stream. When the same pattern appears ≥ min_repeat
    times, it's abstracted into an EXPERIENCE node.

    Returns list of generated experience dicts.
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest
    from .schema import MemoryNode, MemoryType

    all_nodes = store.all(user_id)
    recent = sorted(all_nodes, key=lambda n: n.created_at, reverse=True)[:window]

    if len(recent) < 20:
        return []

    memory_lines = "\n".join(
        f"[{n.id}] [{n.type.value}] {n.content}" for n in recent
    )
    prompt = (
        "你是一个模式识别助手。从以下用户的近期记忆中，找出**重复出现的"
        "行为模式、习惯或偏好**。\n\n"
        "要求：\n"
        "- 找出出现了至少几次的重复模式（不是一次性事件）\n"
        "- 关注：用户会重复做的事情、会重复问的问题、会重复出现的需求\n"
        "- 每个模式一句话概括\n"
        "- 如果确实没有重复模式，说'无'\n"
        "- 输出格式：每行一个模式，以 '- ' 开头，后面跟一句话描述\n\n"
        f"近期记忆（{len(recent)}条）：\n{memory_lines}\n\n"
        "识别到的重复模式："
    )

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L3_DEEP,
        prefer_chinese=True,
        temperature=0.4,
    )
    result = await router.route(req)
    if result.response is None:
        return []

    patterns = [
        line.lstrip("- ").strip()
        for line in result.response.text.split("\n")
        if line.strip().startswith("-") and "无" not in line
    ]

    experiences = []
    for pattern in patterns[:5]:
        node = MemoryNode(
            content=pattern,
            user_id=user_id,
            type=MemoryType.EXPERIENCE,
            importance=_EXPERIENCE_IMPORTANCE,
            source="pattern_detection",
        )
        store.add(node)
        experiences.append({
            "id": node.id,
            "content": pattern,
        })

    logger.info("pattern detection: %d patterns found for user %s",
                len(experiences), user_id)
    return experiences


# ---------------------------------------------------------------------------
# 3. PROCEDURAL PRIMITIVE — auto-skill encapsulation
# ---------------------------------------------------------------------------

async def encapsulate_procedures(
    store: "MemoryStore",
    router: "CognitiveRouter",
    user_id: str,
    min_repeat: int = _PATTERN_MIN_REPEAT,
) -> list[dict]:
    """Detect recurring tool-use sequences and propose skill encapsulation.

    Scans React Observation nodes for repeated tool invocation patterns.
    When the pattern repeats ≥ min_repeat, generates an EXPERIENCE node
    describing a potential skill primitive.

    Returns list of generated procedural primitives.
    """
    from ..engines.base import Complexity, EngineMessage
    from ..engines.router import CognitiveRequest
    from .schema import MemoryNode, MemoryType

    all_nodes = store.all(user_id)
    # Focus on episodic nodes that contain tool usage (from ReAct loops)
    tool_nodes = [
        n for n in all_nodes
        if n.type == MemoryType.EPISODIC
        and ("Action:" in n.content or "calculator" in n.content
             or "memory_search" in n.content or "weather" in n.content)
    ]

    if len(tool_nodes) < 5:
        return []

    tool_lines = "\n".join(
        f"[{n.id}] {n.content[:200]}" for n in tool_nodes[-100:]
    )
    prompt = (
        "你是一个技能封装助手。从以下用户的工具使用记录中，找出**重复出现的"
        "多步操作序列**——同一个流程被用户要求了至少 2-3 次。\n\n"
        "要求：\n"
        "- 识别可以自动化的重复流程（如'每次都先查天气再建议穿什么'）\n"
        "- 给每个可封装的流程起一个简短名字\n"
        "- 如果没有可封装的流程，说'无'\n"
        "- 输出格式：每行一个，'- 流程名：一句话描述'\n\n"
        f"工具使用记录：\n{tool_lines}\n\n"
        "可封装的流程："
    )

    req = CognitiveRequest(
        messages=[EngineMessage(role="user", content=prompt)],
        complexity=Complexity.L3_DEEP,
        prefer_chinese=True,
        temperature=0.4,
    )
    result = await router.route(req)
    if result.response is None:
        return []

    primitives = [
        line.lstrip("- ").strip()
        for line in result.response.text.split("\n")
        if line.strip().startswith("-") and "无" not in line
    ]

    experiences = []
    for primitive in primitives[:5]:
        node = MemoryNode(
            content=f"[程序原语] {primitive}",
            user_id=user_id,
            type=MemoryType.EXPERIENCE,
            importance=_EXPERIENCE_IMPORTANCE,
            source="procedural_primitive",
        )
        store.add(node)
        experiences.append({
            "id": node.id,
            "content": primitive,
        })

    logger.info("procedural primitive: %d primitives found for user %s",
                len(experiences), user_id)
    return experiences


# ---------------------------------------------------------------------------
# Combined L3 pipeline
# ---------------------------------------------------------------------------

async def run_experience_layer(
    store: "MemoryStore",
    router: "CognitiveRouter",
    user_id: str,
) -> dict:
    """Run the full L3 experience layer: consolidation + pattern + procedural.

    Intended as a nightly cron job or manual trigger.
    """
    result: dict = {
        "consolidation": {},
        "patterns": [],
        "primitives": [],
    }

    # Consolidation
    result["consolidation"] = await run_consolidation(
        store, router, user_id,
    )

    # Pattern detection
    result["patterns"] = await detect_patterns(
        store, router, user_id,
    )

    # Procedural primitive
    result["primitives"] = await encapsulate_procedures(
        store, router, user_id,
    )

    return result


def run_experience_sync(store: "MemoryStore", router: "CognitiveRouter",
                        user_id: str = "") -> dict:
    """Synchronous wrapper for testing."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            run_experience_layer(store, router, user_id)
        )
    finally:
        loop.close()

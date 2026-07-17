"""Context Window Manager — intelligent conversation history compression.

Manages token budget and conversation history for long multi-turn dialogues:
  - Keeps recent messages intact (sliding window)
  - Compresses older messages into summaries
  - Extracts key facts to memory system
  - Maintains conversation coherence across compressions

Based on:
  - Anthropic's "prompt caching" best practices
  - OpenAI's "conversation summarization" pattern
  - Google's "Memorizing Transformers" sliding window approach
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.router import CognitiveRouter
    from ..memory.store import MemoryStore

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

MAX_CONTEXT_MESSAGES = 20      # Maximum messages to keep in full context
RECENT_WINDOW_SIZE = 6         # Always keep this many recent messages intact
COMPRESSION_THRESHOLD = 12     # Trigger compression when messages exceed this
TARGET_SUMMARY_TOKENS = 300    # Target token count for compressed history


# ── Data Structures ────────────────────────────────────────────────────────────

@dataclass
class CompressionResult:
    """Result of compressing conversation history."""
    summary: str                           # Compressed summary of older messages
    kept_messages: list[dict]              # Recent messages kept intact
    compressed_count: int                  # Number of messages compressed
    extracted_facts: list[str]             # Key facts extracted for memory
    compression_ratio: float               # Original tokens / compressed tokens


@dataclass
class ContextWindow:
    """Managed context window for a conversation."""
    messages: list[dict]                   # Current messages in window
    summary: str | None = None             # Compressed history summary
    total_messages_seen: int = 0           # Total messages in conversation
    last_compression_at: int = 0           # Message count at last compression

    def needs_compression(self) -> bool:
        """Check if window needs compression."""
        return len(self.messages) > COMPRESSION_THRESHOLD

    def token_estimate(self) -> int:
        """Estimate total tokens in current window (rough heuristic)."""
        # Chinese: ~1.5 chars per token, English: ~4 chars per token
        # Simplified: count all chars and assume mixed content
        total_chars = sum(len(str(m.get("content", ""))) for m in self.messages)
        if self.summary:
            total_chars += len(self.summary)
        return int(total_chars / 2)  # Conservative estimate


# ── Compression Engine ─────────────────────────────────────────────────────────

_SUMMARIZATION_PROMPT = """分析以下对话历史，生成简洁摘要。

对话历史：
{history}

要求：
1. 提取关键信息：主题、决策、重要事实
2. 保持时间顺序和因果关系
3. 省略寒暄和重复内容
4. 控制在 200 字以内

输出 JSON 格式：
{{
  "summary": "对话摘要...",
  "key_facts": ["事实1", "事实2", ...],
  "topics": ["话题1", "话题2"]
}}

只输出 JSON，不要其他内容。"""


async def compress_history(
    messages: list[dict],
    router: "CognitiveRouter",
    keep_recent: int = RECENT_WINDOW_SIZE,
) -> CompressionResult:
    """Compress older messages while keeping recent ones intact.

    Args:
        messages: Full message history
        router: Cognitive router for LLM calls
        keep_recent: Number of recent messages to keep intact

    Returns:
        CompressionResult with summary and kept messages
    """
    if len(messages) <= keep_recent:
        # Nothing to compress
        return CompressionResult(
            summary="",
            kept_messages=messages,
            compressed_count=0,
            extracted_facts=[],
            compression_ratio=1.0,
        )

    # Split: older messages to compress, recent messages to keep
    to_compress = messages[:-keep_recent]
    to_keep = messages[-keep_recent:]

    # Format history for LLM
    history_text = _format_messages_for_summary(to_compress)
    prompt = _SUMMARIZATION_PROMPT.format(history=history_text)

    # Call LLM to generate summary
    try:
        from ..engines.base import EngineMessage
        response = await router.route_simple(
            messages=[EngineMessage(role="user", content=prompt)],
            allow_reasoner=False,  # Fast model is fine for summarization
        )

        # Parse JSON response
        result_text = response.text.strip()
        # Extract JSON from markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        summary = result.get("summary", "")
        key_facts = result.get("key_facts", [])

        # Calculate compression ratio
        original_chars = sum(len(str(m.get("content", ""))) for m in to_compress)
        compressed_chars = len(summary)
        ratio = original_chars / max(compressed_chars, 1)

        logger.info(f"Compressed {len(to_compress)} messages into {compressed_chars} chars (ratio: {ratio:.1f}x)")

        return CompressionResult(
            summary=summary,
            kept_messages=to_keep,
            compressed_count=len(to_compress),
            extracted_facts=key_facts,
            compression_ratio=ratio,
        )

    except Exception as e:
        logger.error(f"Failed to compress history: {e}")
        # Fallback: simple truncation
        fallback_summary = _simple_truncation_summary(to_compress)
        return CompressionResult(
            summary=fallback_summary,
            kept_messages=to_keep,
            compressed_count=len(to_compress),
            extracted_facts=[],
            compression_ratio=1.0,
        )


def _format_messages_for_summary(messages: list[dict]) -> str:
    """Format messages for summarization prompt."""
    lines = []
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        role_label = "用户" if role == "user" else "Sunday"
        lines.append(f"{i}. [{role_label}] {content[:200]}")

    return "\n".join(lines)


def _simple_truncation_summary(messages: list[dict]) -> str:
    """Fallback: simple truncation when LLM summarization fails."""
    if not messages:
        return ""

    topics = []
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")[:50]
            if content and content not in topics:
                topics.append(content)

    if not topics:
        return f"早期对话（{len(messages)} 条消息）"

    return f"早期对话涉及：{', '.join(topics[:3])}等话题"


# ── Window Management ──────────────────────────────────────────────────────────

async def manage_context_window(
    conversation_id: str,
    messages: list[dict],
    router: "CognitiveRouter",
    memory_store: "MemoryStore | None" = None,
    user_id: str = "",
) -> ContextWindow:
    """Manage context window for a conversation.

    Args:
        conversation_id: Conversation ID
        messages: Full message history
        router: Cognitive router for LLM calls
        memory_store: Optional memory store for extracted facts
        user_id: User ID for memory attribution

    Returns:
        ContextWindow with managed messages and summary
    """
    window = ContextWindow(messages=messages, total_messages_seen=len(messages))

    # Check if compression is needed
    if not window.needs_compression():
        return window

    # Perform compression
    logger.info(f"Compressing conversation {conversation_id}: {len(messages)} messages")
    result = await compress_history(messages, router, keep_recent=RECENT_WINDOW_SIZE)

    # Update window
    window.messages = result.kept_messages
    window.summary = result.summary
    window.last_compression_at = window.total_messages_seen - len(result.kept_messages)

    # Extract facts to memory if available
    if memory_store and result.extracted_facts and user_id:
        await _store_extracted_facts(
            facts=result.extracted_facts,
            conversation_id=conversation_id,
            memory_store=memory_store,
            user_id=user_id,
        )

    logger.info(
        f"Compression complete: {result.compressed_count} → summary, "
        f"{len(result.kept_messages)} kept, {len(result.extracted_facts)} facts extracted"
    )

    return window


async def _store_extracted_facts(
    facts: list[str],
    conversation_id: str,
    memory_store: "MemoryStore",
    user_id: str,
) -> None:
    """Store extracted facts as semantic memories."""
    from ..memory.schema import MemoryNode, MemoryType
    from datetime import datetime, timezone
    import uuid

    for fact in facts:
        if not fact or len(fact) < 5:
            continue

        node = MemoryNode(
            id=f"fact_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            content=fact,
            type=MemoryType.SEMANTIC,
            importance=0.6,  # Facts are moderately important
            created_at=datetime.now(timezone.utc),
            tags=["对话提取", conversation_id],
        )
        memory_store.add(node)

    logger.info(f"Stored {len(facts)} facts to memory from conversation {conversation_id}")


# ── Context Assembly ───────────────────────────────────────────────────────────

def build_context_with_window(window: ContextWindow) -> list[dict]:
    """Build final context messages with compression summary prepended.

    Returns messages ready for engine consumption:
    - If compressed: [system message with summary] + recent messages
    - If not compressed: original messages
    """
    if not window.summary:
        # No compression, return messages as-is
        return window.messages

    # Prepend summary as system message
    summary_message = {
        "role": "system",
        "content": f"[对话历史摘要]\n{window.summary}\n\n以下是最近的对话：",
        "timestamp": "",
    }

    return [summary_message] + window.messages


# ── Utility Functions ──────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimation (conservative)."""
    # Mixed Chinese/English: ~2 chars per token average
    return len(text) // 2


def should_trigger_compression(messages: list[dict]) -> bool:
    """Check if conversation should trigger compression."""
    return len(messages) > COMPRESSION_THRESHOLD

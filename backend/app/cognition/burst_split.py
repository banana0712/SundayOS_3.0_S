"""Natural message segmentation for human-like multi-bubble delivery.

Research basis:
  - Stephanie (NAACL 2025): step-by-step dialogue paradigm — split at natural
    conversation breakpoints for higher engagement
  - ChatLab / OpenHuman (2025-2026): sentence-level chunking with typing
    indicators between bubbles
  - Parlant: message splitting as perceived performance optimization

Strategy (no LLM needed — pure heuristic, ~0.1ms):
  1. Primary split: double newlines (natural paragraph breaks)
  2. Secondary split: sentences within paragraphs > 500 chars
  3. Minimum segment size: 20 chars (don't fragment single words)
  4. Merge very short segments (< 20 chars) into adjacent ones

The result reads like a human texting in bursts — not a robot dumping a wall
of text into a single bubble.
"""

from __future__ import annotations

import re

# ── Split points (Chinese + English) ──────────────────────────────────
# Split AFTER these characters (they end a natural thought unit)
_SENTENCE_END = re.compile(r"[。！？\n.!?\n]")

# Minimum characters per bubble — smaller sentence fragments get merged
_MIN_SEGMENT = 20

# Maximum characters before we try to split by sentences
# (if a paragraph is shorter than this, keep it whole)
_MAX_PARAGRAPH_FOR_SENTENCE_SPLIT = 400

# If after all splitting there's only 1 segment shorter than this,
# return it as-is — don't force artificial splits on short replies
_SINGLE_BUBBLE_MAX = 200


def burst_split(text: str) -> list[str]:
    """Split a reply into natural segments for multi-bubble delivery.

    Args:
        text: the complete AI reply

    Returns:
        list of text segments, each a complete thought unit ready to be
        rendered as a separate chat bubble
    """
    if not text or not text.strip():
        return [text] if text else []

    text = text.strip()

    # Step 1: split on double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text]

    # Step 2: split paragraphs at sentence boundaries
    segments: list[str] = []
    for para in paragraphs:
        if len(para) <= _MAX_PARAGRAPH_FOR_SENTENCE_SPLIT:
            # Still try sentence splitting if it naturally contains multiple sentences
            sentences = _split_sentences(para)
            if len(sentences) > 1:
                for s in sentences:
                    segments.append(("s", s))
            else:
                segments.append(("p", para))
        else:
            sentences = _split_sentences(para)
            for s in sentences:
                segments.append(("s", s))

    # Step 3: merge very short SENTENCE-LEVEL segments into previous ones.
    # Paragraph-level splits are sacred — never merge across them.
    merged: list[str] = []
    for boundary, seg in segments:
        if boundary == "p":
            merged.append(seg)
        elif len(seg) < _MIN_SEGMENT and merged:
            merged[-1] = merged[-1] + " " + seg
        else:
            merged.append(seg)

    # Step 4: if everything merged into one short bubble, keep it whole
    if len(merged) == 1 and len(merged[0]) <= _SINGLE_BUBBLE_MAX:
        return merged

    # Step 5: single-bubble guard for very long single segments
    # (> 800 chars with no natural breaks) — force-split at sentence boundaries
    if len(merged) == 1 and len(merged[0]) > _SINGLE_BUBBLE_MAX:
        long_text = merged[0]
        sentences = _split_sentences(long_text)
        if len(sentences) > 1:
            # Group sentences into chunks of ~200-400 chars
            result: list[str] = []
            acc = ""
            for s in sentences:
                if len(acc) + len(s) > 450 and acc:
                    result.append(acc.strip())
                    acc = s
                else:
                    acc += s
            if acc.strip():
                result.append(acc.strip())
            return result

    return merged if merged else [text]


def _split_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries (。！？.!? followed by space or start)."""
    result: list[str] = []
    current = ""
    for i, ch in enumerate(text):
        current += ch
        if ch in "。！？.!?":
            # Check if this is a real sentence end (followed by space, newline, or end)
            if i + 1 >= len(text) or text[i + 1] in " \n\r\t":
                result.append(current.strip())
                current = ""
            # Chinese punctuation followed by Chinese char = sentence end
            elif ch in "。！？" and i + 1 < len(text) and '一' <= text[i + 1] <= '鿿':
                result.append(current.strip())
                current = ""
    if current.strip():
        result.append(current.strip())
    return [r for r in result if r]

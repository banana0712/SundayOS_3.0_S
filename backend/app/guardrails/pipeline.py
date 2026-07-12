"""Guardrail pipeline — docs/3.0/08-security-and-autonomy.md §8.1.

Order (input): length → rules/regex/blocklist → moderation → relevance+safety.
A trip raises GuardrailTripwire immediately. The LLM-based layers (moderation,
relevance, safety) are pluggable; deterministic rule layers run offline and are
unit-tested. Tool risk rating (L5) is provided for the action loop.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


class GuardrailTripwire(Exception):
    def __init__(self, layer: str, reason: str):
        self.layer = layer
        self.reason = reason
        super().__init__(f"[{layer}] {reason}")


# L4 rules
_MAX_LEN = 8000
_BLOCKLIST = re.compile(r"(?i)(ignore (all )?previous instructions|你现在是|"
                        r"disregard (the )?system prompt|jailbreak|DAN mode)")
_INJECTION = re.compile(r"(?i)(system prompt|reveal your instructions|"
                        r"print your (system )?prompt)")
# L3 PII (basic patterns; production adds NER)
_PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone_cn": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
    "id_cn": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
}

# L5 tool risk
_TOOL_RISK = {
    "search": "low", "web": "low", "read_file": "low", "calendar": "medium",
    "run_python": "medium", "github": "medium", "write_file": "medium",
    "send_email": "medium", "delete_file": "high", "pay": "high",
    "change_permission": "high", "delete_account": "high",
}


@dataclass
class GuardrailResult:
    ok: bool
    layer: str = ""
    reason: str = ""
    redactions: dict[str, int] = field(default_factory=dict)


def check_input(text: str) -> GuardrailResult:
    """Run the deterministic input layers in order. Raises on trip."""
    # L4 length
    if len(text) > _MAX_LEN:
        raise GuardrailTripwire("L4-rules", f"input exceeds {_MAX_LEN} chars")
    # L4 blocklist / injection
    if _BLOCKLIST.search(text) or _INJECTION.search(text):
        raise GuardrailTripwire("L4-rules", "prompt-injection / jailbreak pattern")
    return GuardrailResult(ok=True)


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """L3 PII filter for outputs. Returns (redacted_text, counts)."""
    counts: dict[str, int] = {}
    out = text
    for name, pat in _PII_PATTERNS.items():
        found = pat.findall(out)
        if found:
            counts[name] = len(found)
            out = pat.sub(f"[REDACTED_{name.upper()}]", out)
    return out, counts


def tool_risk(tool_name: str) -> str:
    """L5: rate a tool call low|medium|high (docs §8.1)."""
    return _TOOL_RISK.get(tool_name, "medium")


def requires_confirmation(tool_name: str) -> bool:
    """High-risk tools need human confirmation before execution (HITL, L6)."""
    return tool_risk(tool_name) == "high"

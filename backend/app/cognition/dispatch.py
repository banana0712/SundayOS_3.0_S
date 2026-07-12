"""Dual-process dispatch — decide whether System 2 (Reasoner) is needed.
docs/3.0/05-dual-process-cognition.md §5.6. Pure logic, unit-tested offline."""
from __future__ import annotations

import re

from .belief import BeliefState

_INTENT_REASONER = {"plan", "code", "analyze", "research", "multi_step"}
_TOOL_RE = re.compile(r"(搜索|查一下|查询|发邮件|提交|运行|计算|规划|安排|日程|提醒|"
                      r"search|run|commit|schedule|plan|calculate|book)")
_RISK_RE = re.compile(r"(删除|删掉|支付|付款|转账|权限|delete|drop|pay|purchase|rm -rf)")
_STEP_RE = re.compile(r"(然后|接着|之后|first|then|after that|step \d|步骤|再|最后)")


class Risk:
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def risk_level(text: str) -> int:
    if _RISK_RE.search(text):
        return Risk.HIGH
    if _TOOL_RE.search(text):
        return Risk.MEDIUM
    return Risk.LOW


def estimated_steps(text: str) -> int:
    return 1 + len(_STEP_RE.findall(text))


def contains_tool_intent(text: str) -> bool:
    return bool(_TOOL_RE.search(text))


def needs_reasoner(intent: str, text: str, belief: BeliefState | None = None) -> bool:
    """Return True if System 2 should be activated."""
    checks = [
        intent in _INTENT_REASONER,
        contains_tool_intent(text),
        estimated_steps(text) > 1,
        risk_level(text) >= Risk.MEDIUM,
        bool(belief and belief.has_unresolved_obstacles()),
        len(text) > 280 and "?" in text or "？" in text,
    ]
    return any(checks)

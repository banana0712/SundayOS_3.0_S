"""Skill Registry — extensible skill system for the ReAct loop.

Upgraded from ToolRegistry to align with docs/3.0/07-skills-and-tools.md.

Skills are categorized, discoverable capability packages. Each Skill wraps a Tool
with category metadata, dependencies, and usage tracking.

To add a new skill: create an async handler, call SKILLS.register().
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

# ---------------------------------------------------------------------------
# Tool definition (backward-compatible base)
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    params: dict            # {"param_name": "type"}
    risk: str = "low"       # low | medium | high
    handler: Callable[..., Awaitable[str]] | None = None

    def to_openai(self) -> dict:
        props = {}
        for pname, ptype in self.params.items():
            props[pname] = {"type": ptype, "description": pname}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": list(self.params.keys()),
                } if self.params else None,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai(self) -> list[dict]:
        return [t.to_openai() for t in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)


# ---------------------------------------------------------------------------
# Skill layer (extends Tool with category, deps, usage)
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    name: str
    description: str          # for LLM
    params: dict              # {"param": "string"}
    category: str             # data | action | orchestration | support
    risk: str = "low"
    handler: Callable[..., Awaitable[str]] | None = None
    requires: list[str] = field(default_factory=list)   # dependency tool names
    examples: list[str] = field(default_factory=list)    # user-facing examples
    usage_count: int = 0

    def to_tool(self) -> Tool:
        return Tool(
            name=self.name, description=self.description,
            params=self.params, risk=self.risk, handler=self.handler,
        )


class SkillRegistry:
    """Skill management layer on top of ToolRegistry."""

    def __init__(self, tools: ToolRegistry):
        self._tools = tools
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        self._tools.register(skill.to_tool())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list(self) -> list[Skill]:
        return list(self._skills.values())

    def by_category(self, category: str) -> list[Skill]:
        return [s for s in self._skills.values() if s.category == category]

    def categories(self) -> list[str]:
        return sorted(set(s.category for s in self._skills.values()))

    def record_usage(self, name: str) -> None:
        s = self._skills.get(name)
        if s:
            s.usage_count += 1

    def summary(self) -> dict:
        """Return a summary for API/console display."""
        by_cat: dict[str, list[str]] = {}
        for s in self._skills.values():
            by_cat.setdefault(s.category, []).append(s.name)
        return {
            "total": len(self._skills),
            "by_category": {k: len(v) for k, v in by_cat.items()},
            "skills": {s.name: {"category": s.category, "risk": s.risk,
                                 "usage": s.usage_count, "examples": s.examples}
                       for s in self._skills.values()},
        }

    def __len__(self) -> int:
        return len(self._skills)


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------

TOOLS = ToolRegistry()
SKILLS = SkillRegistry(TOOLS)


# ---------------------------------------------------------------------------
# Built-in skill handlers
# ---------------------------------------------------------------------------

# -- data skills -------------------------------------------------------------

async def _memory_search_handler(query: str, *, store=None, user_id: str = "") -> str:
    if store is None:
        return "[memory_search] No memory store available."
    hits = store.retrieve(query, user_id=user_id or "", k=5)
    if not hits:
        return "[memory_search] No relevant memories found."
    return "\n".join(
        f"- [{h.node.type.value}] {h.node.content} (score: {h.score:.2f})" for h in hits
    )


async def _get_time_handler() -> str:
    now = datetime.now(timezone.utc)
    return (
        f"Current UTC time: {now.isoformat()}\n"
        f"Day of week: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%Y-%m-%d')}"
    )


async def _translate_handler(text: str, target_lang: str = "zh") -> str:
    """Simple translate — returns a template for the LLM to fill in."""
    return (
        f"[translate] Request to translate the following text to {target_lang}:\n"
        f"---\n{text}\n---\n"
        f"(Translation will be provided by the reasoning engine.)"
    )


async def _web_search_handler(query: str) -> str:
    """Placeholder. Real implementation needs a search API key."""
    return (
        f"[web_search] Web search is not yet configured. "
        f"Query: '{query}'. Try memory_search for local knowledge."
    )


# -- action skills -----------------------------------------------------------

async def _calculator_handler(expression: str) -> str:
    safe_globals = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "len": len, "int": int, "float": float,
        "sqrt": math.sqrt, "pow": pow, "sin": math.sin,
        "cos": math.cos, "pi": math.pi, "e": math.e,
    }
    try:
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in safe_globals and name not in ("__builtins__",):
                return f"[calculator] Error: '{name}' is not allowed."
        result = eval(code, {"__builtins__": {}}, safe_globals)
        return f"[calculator] {expression} = {result}"
    except Exception as e:
        return f"[calculator] Error: {e}"


async def _read_file_handler(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()[:8000]
        line_count = content.count("\n") + 1
        return f"[read_file] {path} ({line_count} lines, {len(content)} chars):\n---\n{content}\n---"
    except FileNotFoundError:
        return f"[read_file] File not found: {path}"
    except PermissionError:
        return f"[read_file] Permission denied: {path}"
    except Exception as e:
        return f"[read_file] Error: {e}"


async def _write_file_handler(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[write_file] Written {len(content)} chars to {path}"
    except Exception as e:
        return f"[write_file] Error: {e}"


# -- support skills ----------------------------------------------------------

async def _weather_handler(city: str) -> str:
    """Placeholder — real implementation needs a weather API key."""
    return (
        f"[weather] Weather API is not yet configured. "
        f"Query for city: '{city}'. Try web_search for weather information."
    )


async def _echo_handler(text: str) -> str:
    return f"[echo] {text}"


# ---------------------------------------------------------------------------
# Register all skills
# ---------------------------------------------------------------------------

SKILLS.register(Skill(
    name="memory_search", description="检索 Sunday 的记忆库，查找过去的对话、事实和偏好。",
    params={"query": "string"}, category="data", risk="low",
    handler=_memory_search_handler,
    examples=["搜索我关于跑步的记忆", "我之前说过喜欢什么颜色"],
))
SKILLS.register(Skill(
    name="calculator", description="安全地执行数学表达式计算。支持 + - * / sqrt sin cos pow abs round pi e。",
    params={"expression": "string"}, category="action", risk="low",
    handler=_calculator_handler,
    examples=["计算 156 * 23", "sqrt(144)"],
))
SKILLS.register(Skill(
    name="get_time", description="获取当前 UTC 日期、时间和星期几。",
    params={}, category="data", risk="low",
    handler=_get_time_handler,
    examples=["现在几点", "今天是星期几"],
))
SKILLS.register(Skill(
    name="web_search", description="搜索互联网获取实时信息（新闻、天气、百科）。当前为占位实现。",
    params={"query": "string"}, category="data", risk="medium",
    handler=_web_search_handler,
    examples=["搜索 Python 3.14 新特性", "查一下上海今天天气"],
))
SKILLS.register(Skill(
    name="read_file", description="读取服务器上的文本文件，返回内容摘要。",
    params={"path": "string"}, category="data", risk="low",
    handler=_read_file_handler,
    examples=["读取 /opt/sundayos/README.md"],
))
SKILLS.register(Skill(
    name="write_file", description="将文本内容写入服务器文件（覆盖写入）。需要确认。",
    params={"path": "string", "content": "string"}, category="action", risk="medium",
    handler=_write_file_handler,
    examples=["保存笔记到 notes.txt"],
))
SKILLS.register(Skill(
    name="translate", description="翻译文本到指定语言（由推理引擎提供翻译）。",
    params={"text": "string", "target_lang": "string"}, category="support", risk="low",
    handler=_translate_handler,
    examples=["把这段英文翻译成中文", "翻译成日语"],
))
SKILLS.register(Skill(
    name="weather", description="查询指定城市的天气信息（当前为占位实现，待接入天气 API）。",
    params={"city": "string"}, category="data", risk="low",
    handler=_weather_handler,
    examples=["北京今天天气", "东京天气怎么样"],
))

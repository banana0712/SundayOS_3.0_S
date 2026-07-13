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
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from urllib.parse import quote

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
    """Real web search via DuckDuckGo HTML endpoint. No API key needed."""
    import httpx
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        resp = httpx.get(url, headers={"User-Agent": "SundayOS/1.0"}, timeout=10.0,
                         follow_redirects=True)
        resp.raise_for_status()

        # Extract snippets from DuckDuckGo's HTML results
        snippets = re.findall(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            resp.text, re.DOTALL
        )
        if not snippets:
            # Fallback: try to extract any snippet-like content
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</',
                resp.text, re.DOTALL
            )

        if not snippets:
            return f"[web_search] No results found for '{query}'."

        # Clean HTML tags and entities, trim each snippet
        clean = []
        for s in snippets[:8]:
            s = re.sub(r'<[^>]+>', '', s)          # strip HTML tags
            s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            s = s.replace('&quot;', '"').replace('&#x27;', "'")
            s = s.replace('&nbsp;', ' ').strip()
            if s:
                clean.append(s)

        if not clean:
            return f"[web_search] No clear results for '{query}'."

        return f"[web_search] Results for '{query}':\n" + "\n".join(
            f"{i+1}. {snippet}" for i, snippet in enumerate(clean)
        )
    except Exception as e:
        return f"[web_search] Search failed: {e}. Try a different query."


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
    """Real weather via wttr.in + Open-Meteo fallback. No API key needed."""
    import httpx
    city_clean = city.strip().replace(" ", "+")

    # Try wttr.in first (plain text, super simple)
    try:
        url = f"https://wttr.in/{quote(city_clean)}?format=%C+%t+%w+%h&m"
        resp = httpx.get(url, headers={"User-Agent": "curl/7.0"}, timeout=8.0)
        if resp.status_code == 200 and resp.text.strip():
            text = resp.text.strip()
            # Parse wttr output: "Sunny +22°C 15km/h 65%"
            return f"[weather] {city}: {text}"
    except Exception:
        pass  # fall through to Open-Meteo

    # Fallback: Open-Meteo geocoding + forecast (free, no key)
    try:
        # Step 1: geocode city name to coordinates
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city_clean)}&count=1&language=zh"
        geo_resp = httpx.get(geo_url, timeout=8.0)
        if geo_resp.status_code == 200:
            geo_data = geo_resp.json()
            results = geo_data.get("results", [])
            if results:
                r = results[0]
                lat, lon = r["latitude"], r["longitude"]
                name = r.get("name", city)
                country = r.get("country", "")

                # Step 2: get current weather
                wx_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}"
                    f"&current=temperature_2m,relative_humidity_2m,"
                    f"wind_speed_10m,weather_code&timezone=auto"
                )
                wx_resp = httpx.get(wx_url, timeout=8.0)
                if wx_resp.status_code == 200:
                    wx = wx_resp.json()
                    cur = wx.get("current", {})
                    temp = cur.get("temperature_2m", "?")
                    hum = cur.get("relative_humidity_2m", "?")
                    wind = cur.get("wind_speed_10m", "?")
                    code = cur.get("weather_code", 0)

                    # WMO weather code → description
                    wx_desc = _weather_code_desc(code)

                    return (
                        f"[weather] {name}, {country}: {wx_desc}, "
                        f"温度 {temp}°C, 湿度 {hum}%, 风速 {wind} km/h"
                    )

        return f"[weather] Could not find weather data for '{city}'. Check the city name."
    except Exception as e:
        return f"[weather] Weather lookup failed for '{city}': {e}"


def _weather_code_desc(code: int) -> str:
    """WMO weather code to Chinese description."""
    if code == 0:
        return "晴"
    if code <= 3:
        return "多云"
    if code <= 49:
        return "雾/霾"
    if code <= 59:
        return "小雨"
    if code <= 69:
        return "中雨"
    if code <= 79:
        return "雪"
    if code <= 84:
        return "大雨"
    if code <= 99:
        return "雷暴"
    return "未知"


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
    name="web_search", description="通过 DuckDuckGo 搜索互联网获取实时信息（新闻、百科、事实）。免费，无需 API Key。",
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
    name="weather", description="通过 wttr.in / Open-Meteo 查询指定城市的实时天气（温度、湿度、风速）。免费，无需 API Key。",
    params={"city": "string"}, category="data", risk="low",
    handler=_weather_handler,
    examples=["北京今天天气", "东京天气怎么样"],
))

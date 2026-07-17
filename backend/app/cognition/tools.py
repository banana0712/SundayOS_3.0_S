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
    """Optimized web search with proxy support and fallback strategies.

    Priority:
    1. duckduckgo-search library (if available)
    2. DuckDuckGo HTML (with proxy support)
    3. Bing search (fallback)

    Reads proxy from environment: HTTP_PROXY, HTTPS_PROXY, or SEARCH_PROXY
    """
    # Try using duckduckgo-search library (preferred)
    try:
        from duckduckgo_search import DDGS

        # Get proxy from environment
        proxy = os.environ.get('SEARCH_PROXY') or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')

        with DDGS(proxy=proxy, timeout=20) as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return f"[web_search] No results found for '{query}'."

        # Format results with title, URL, and snippet
        formatted = [f"[web_search] Results for '{query}':\n"]
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('href', result.get('link', ''))
            snippet = result.get('body', result.get('snippet', ''))

            # Truncate long snippets
            if len(snippet) > 200:
                snippet = snippet[:197] + '...'

            formatted.append(f"{i}. {title}\n   {url}\n   {snippet}\n")

        return "\n".join(formatted)

    except ImportError:
        pass  # Library not installed, try HTML fallback
    except Exception as e:
        # Log but continue to fallback
        print(f"[DEBUG] duckduckgo-search failed: {type(e).__name__}: {str(e)[:100]}")

    # Fallback: DuckDuckGo HTML with proxy support
    import httpx
    try:
        # Get proxy configuration
        proxy = os.environ.get('SEARCH_PROXY') or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')

        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        async with httpx.AsyncClient(proxy=proxy, verify=False) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=20.0,
                follow_redirects=True
            )
            resp.raise_for_status()

        # Extract titles, snippets, and URLs
        titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        urls = re.findall(r'<a[^>]*class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

        if not snippets and not titles:
            return f"[web_search] No results found for '{query}'."

        # Clean and format results
        results = []
        max_results = min(5, len(snippets))
        for i in range(max_results):
            title = re.sub(r'<[^>]+>', '', titles[i] if i < len(titles) else 'Result')
            snippet = re.sub(r'<[^>]+>', '', snippets[i] if i < len(snippets) else '')
            url = re.sub(r'<[^>]+>', '', urls[i] if i < len(urls) else '')

            # Clean HTML entities
            for entity, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                                 ('&quot;', '"'), ('&#x27;', "'"), ('&nbsp;', ' ')]:
                title = title.replace(entity, char)
                snippet = snippet.replace(entity, char)
                url = url.replace(entity, char)

            title = title.strip()
            snippet = snippet.strip()
            url = url.strip()

            if snippet:
                results.append(f"{i+1}. {title}\n   {url}\n   {snippet}")

        if not results:
            return f"[web_search] No clear results for '{query}'."

        return f"[web_search] Results for '{query}':\n" + "\n\n".join(results)

    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
        # Network error - suggest proxy configuration
        return (f"[web_search] Network error: {type(e).__name__}. "
                f"DuckDuckGo may be blocked. Configure SEARCH_PROXY or HTTPS_PROXY environment variable. "
                f"Example: export HTTPS_PROXY=http://127.0.0.1:7890")

    except Exception as e:
        print(f"[DEBUG] web_search failed: {type(e).__name__}: {str(e)[:200]}")
        return f"[web_search] Search failed: {type(e).__name__}. Try a different query or check network connection."


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


# -- orchestration skills ----------------------------------------------------

async def _create_reminder_handler(content: str, when: str, *, store=None, user_id: str = "") -> str:
    """创建提醒事项（保存到记忆系统作为 EXPERIENCE）"""
    if not store or not user_id:
        return "[create_reminder] Error: store or user_id missing."

    from ..memory.schema import MemoryNode, MemoryType
    from datetime import datetime, timezone
    import uuid

    # 解析时间（简单实现：支持相对时间和绝对时间）
    when_parsed = _parse_reminder_time(when)
    reminder_text = f"提醒：{content}（时间：{when_parsed}）"

    # 保存为经验记忆
    node = MemoryNode(
        id=f"reminder_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        content=reminder_text,
        type=MemoryType.EXPERIENCE,
        importance=0.8,  # 提醒较重要
        created_at=datetime.now(timezone.utc),
        tags=["提醒", "待办"],
    )
    store.add(node)
    return f"[create_reminder] 已创建提醒：{reminder_text}"


def _parse_reminder_time(when: str) -> str:
    """解析时间描述（简单版）"""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    when_lower = when.lower().strip()

    # 相对时间
    if "明天" in when_lower:
        target = now + timedelta(days=1)
        return target.strftime("%Y-%m-%d %H:%M")
    if "今天" in when_lower or "一会" in when_lower:
        return now.strftime("%Y-%m-%d %H:%M")
    if "小时" in when_lower:
        # 提取数字
        import re
        match = re.search(r'(\d+)', when_lower)
        if match:
            hours = int(match.group(1))
            target = now + timedelta(hours=hours)
            return target.strftime("%Y-%m-%d %H:%M")

    # 默认返回原始描述
    return when


async def _save_note_handler(title: str, content: str, *, store=None, user_id: str = "") -> str:
    """保存笔记到记忆系统"""
    if not store or not user_id:
        return "[save_note] Error: store or user_id missing."

    from ..memory.schema import MemoryNode, MemoryType
    from datetime import datetime, timezone
    import uuid

    note_text = f"笔记「{title}」：{content}"
    node = MemoryNode(
        id=f"note_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        content=note_text,
        type=MemoryType.SEMANTIC,  # 笔记作为语义记忆
        importance=0.7,
        created_at=datetime.now(timezone.utc),
        tags=["笔记", title],
    )
    store.add(node)
    return f"[save_note] 已保存笔记「{title}」（{len(content)} 字）"


async def _list_notes_handler(tag: str = "", *, store=None, user_id: str = "") -> str:
    """列出用户的笔记"""
    if not store or not user_id:
        return "[list_notes] Error: store or user_id missing."

    # 搜索笔记类型的记忆
    query = f"笔记 {tag}" if tag else "笔记"
    hits = store.retrieve(query, user_id=user_id, k=10)

    notes = [h for h in hits if "笔记" in h.node.content]
    if not notes:
        return "[list_notes] 未找到笔记。"

    result = f"[list_notes] 找到 {len(notes)} 条笔记：\n"
    for i, h in enumerate(notes[:10], 1):
        # 提取标题
        content = h.node.content
        if "笔记「" in content:
            title = content.split("笔记「")[1].split("」")[0]
            result += f"{i}. {title}\n"
        else:
            result += f"{i}. {content[:50]}...\n"

    return result


async def _fetch_url_handler(url: str) -> str:
    """获取 URL 内容（HTTP GET）"""
    import httpx
    try:
        resp = httpx.get(url, timeout=10.0, follow_redirects=True,
                        headers={"User-Agent": "SundayOS/1.0"})
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()

        # JSON 响应
        if "application/json" in content_type:
            try:
                data = resp.json()
                return f"[fetch_url] JSON 响应（{len(str(data))} 字符）：\n{json.dumps(data, ensure_ascii=False, indent=2)[:2000]}"
            except Exception:
                pass

        # HTML/文本响应
        text = resp.text[:5000]  # 限制长度
        return f"[fetch_url] 响应（{len(text)} 字符）：\n{text}"

    except httpx.HTTPStatusError as e:
        return f"[fetch_url] HTTP 错误 {e.response.status_code}: {url}"
    except Exception as e:
        return f"[fetch_url] 请求失败: {e}"


# Register new skills
SKILLS.register(Skill(
    name="create_reminder",
    description="创建提醒事项，指定内容和时间（相对时间如「明天」「3小时后」或绝对时间）。",
    params={"content": "string", "when": "string"},
    category="orchestration",
    risk="low",
    handler=_create_reminder_handler,
    examples=["提醒我明天9点开会", "3小时后提醒我吃药"],
))

SKILLS.register(Skill(
    name="save_note",
    description="保存笔记到记忆系统，指定标题和内容。后续可通过 memory_search 或 list_notes 检索。",
    params={"title": "string", "content": "string"},
    category="action",
    risk="low",
    handler=_save_note_handler,
    examples=["保存笔记：今天学到的Python技巧", "记录想法"],
))

SKILLS.register(Skill(
    name="list_notes",
    description="列出用户保存的笔记，可选标签过滤。",
    params={"tag": "string"},
    category="data",
    risk="low",
    handler=_list_notes_handler,
    examples=["列出我的笔记", "查看关于Python的笔记"],
))

SKILLS.register(Skill(
    name="fetch_url",
    description="通过 HTTP GET 获取指定 URL 的内容（支持 JSON/HTML/文本）。用于访问 API 或网页内容。",
    params={"url": "string"},
    category="data",
    risk="medium",
    handler=_fetch_url_handler,
    examples=["获取 https://api.github.com/users/octocat", "访问这个链接"],
))


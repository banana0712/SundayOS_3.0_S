"""ReAct execution loop — Thought → Action → Observation.

Implements the ReAct pattern from:
  Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models"
  (ICLR 2023)

The loop:
  1. Builds a system prompt with few-shot examples and available tools.
  2. Loops (up to max_steps):
    a. Calls the engine with tool definitions.
    b. Parses the response for Thought/Action/Observation patterns.
    c. If Action: runs the tool via ToolRegistry, feeds Observation back.
    d. If finish: returns the final answer.
    e. If ask: pauses for user input (reformulated as HITL).
  3. On timeout / max steps exceeded: forces a best-effort finish.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.base import EngineProvider
    from ..engines.router import CognitiveRouter, CognitiveRequest
    from ..memory.store import MemoryStore
    from .tools import SkillRegistry, ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ReActStep:
    type: str  # "thought" | "action" | "observation" | "finish" | "ask"
    content: str
    tool_name: str | None = None
    tool_input: str | None = None
    tool_output: str | None = None
    latency_ms: float = 0.0


@dataclass
class ReActResult:
    answer: str
    steps: list[ReActStep] = field(default_factory=list)
    belief_updates: dict = field(default_factory=dict)
    total_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Skill prompt engineering (Anthropic-style)
# ---------------------------------------------------------------------------
# Each skill has a docstring-like description including:
#   - What it does, When to use, When NOT to use, Example, Common mistakes
# This follows "Building Effective Agents" §Prompt Engineering Your Tools:
#   "Write tool descriptions like docstrings for a junior developer."
# ---------------------------------------------------------------------------

_SKILL_DOCS: dict[str, str] = {
    "memory_search": (
        "`memory_search[query]` — 搜索 Sunday 的记忆库。\n"
        "  **何时使用**：用户提到过去的事、偏好、习惯，或问「你还记得…」「我之前…」「我说过喜欢什么…」\n"
        "  **不要使用**：问的是实时信息（天气、新闻）→ 用 web_search；问的是时间 → 用 get_time\n"
        "  **示例**：`memory_search[用户喜欢什么颜色]`\n"
        "  **注意**：query 用关键词，不要写完整句子。中文用户推荐用中文 query。"
    ),
    "calculator": (
        "`calculator[expression]` — 安全地计算数学表达式。\n"
        "  **何时使用**：需要精确的数学结果、单位换算、统计。用户说「算一下」「等于多少」「帮我算」\n"
        "  **不要使用**：简单的心理计算（如 2+2）可以直接回答；文本推理或逻辑题不需要\n"
        "  **示例**：`calculator[156 * 23]`、`calculator[sqrt(144)]`\n"
        "  **注意**：expression 只含数学运算符和数字。不能用变量名或函数调用。支持 + - * / ** sqrt sin cos abs round pi e。"
    ),
    "get_time": (
        "`get_time[]` — 获取当前 UTC 时间和日期。\n"
        "  **何时使用**：用户问「现在几点」「今天是星期几」「今天几号」\n"
        "  **不要使用**：问的是某个事件的时间或历史日期 → 用 memory_search 或 web_search\n"
        "  **注意**：无参数，直接调用 `get_time[]`。"
    ),
    "web_search": (
        "`web_search[query]` — 通过 DuckDuckGo 搜索互联网获取实时信息。\n"
        "  **何时使用**：用户问的是实时信息（天气、新闻、股价）、最新文档、当前事件\n"
        "  **不要使用**：用户问的是个人历史或偏好 → 用 memory_search；纯计算 → 用 calculator\n"
        "  **示例**：`web_search[上海今天天气预报]`\n"
        "  **注意**：免费，无需 API Key。返回搜索结果摘要（1-8 条）。失败时尝试从记忆推断。"
    ),
    "read_file": (
        "`read_file[path]` — 读取服务器上的文本文件。\n"
        "  **何时使用**：用户让你「读一下」「看一下」「打开」某个文件\n"
        "  **不要使用**：用户想写入或保存内容 → 用 write_file；搜索内容 → 用 memory_search\n"
        "  **示例**：`read_file[/opt/sundayos/notes.txt]`\n"
        "  **注意**：path 必须是绝对路径。只能读文本文件。文件不存在时返回错误。"
    ),
    "write_file": (
        "`write_file[path, content]` — 将文本写入文件。\n"
        "  **何时使用**：用户说「保存」「记下来」「写下来」「创建文件」\n"
        "  **不要使用**：用户只是聊天或提问 → 不需要写文件。未明确要求时不要主动写入\n"
        "  **示例**：`write_file[notes.txt, 明天要记得买牛奶和面包]`\n"
        "  **注意**：这个操作会覆盖已有文件。需要用户明确确认。风险等级：中等。"
    ),
    "translate": (
        "`translate[text, target_lang]` — 翻译文本到目标语言。\n"
        "  **何时使用**：用户说「翻译成…」「帮我翻译」「这句话用…怎么说」\n"
        "  **不要使用**：用户在用外语聊天但没有要求翻译 → 直接用外语回复即可\n"
        "  **示例**：`translate[Hello World, zh]`\n"
        "  **注意**：翻译由推理引擎提供，translate 工具返回原文供引擎翻译。target_lang 用简写：zh(中文) en(英语) ja(日语) ko(韩语)。"
    ),
    "weather": (
        "`weather[city]` — 通过 wttr.in / Open-Meteo 查询城市实时天气。\n"
        "  **何时使用**：用户问「天气」「多少度」「会下雨吗」\n"
        "  **不要使用**：用户问的是气候或历史天气 → 用 web_search\n"
        "  **示例**：`weather[北京]`、`weather[Tokyo]`\n"
        "  **注意**：免费，无需 API Key。返回温度/湿度/风速/天气描述。支持中英文城市名。"
    ),
    "create_reminder": (
        "`create_reminder[content, when]` — 创建提醒事项。\n"
        "  **何时使用**：用户说「提醒我」「记得」「别忘了」\n"
        "  **不要使用**：用户只是说要做某事但没要求提醒 → 用 memory_search 记录即可\n"
        "  **示例**：`create_reminder[开会, 明天9点]`、`create_reminder[吃药, 3小时后]`\n"
        "  **注意**：when 支持相对时间（明天/今天/X小时后）或绝对时间。提醒保存到记忆系统。\n"
        "  **⚠️ 强制执行**：必须调用此工具完成持久化，禁止直接回答「已创建」。"
    ),
    "save_note": (
        "`save_note[title, content]` — 保存笔记到记忆系统。\n"
        "  **何时使用**：用户说「记下来」「做个笔记」「保存这个想法」\n"
        "  **不要使用**：用户只是聊天 → 不需要笔记；要保存到文件 → 用 write_file\n"
        "  **示例**：`save_note[Python技巧, 用enumerate遍历索引和值]`\n"
        "  **注意**：笔记保存为语义记忆，可通过 memory_search 或 list_notes 检索。\n"
        "  **⚠️ 强制执行**：必须调用此工具完成持久化，禁止直接回答「已保存」。"
    ),
    "list_notes": (
        "`list_notes[tag]` — 列出用户保存的笔记。\n"
        "  **何时使用**：用户说「看看我的笔记」「我记了什么」「查笔记」\n"
        "  **不要使用**：用户要搜索特定内容 → 用 memory_search 更精确\n"
        "  **示例**：`list_notes[]`、`list_notes[Python]`\n"
        "  **注意**：tag 可选，用于过滤特定标签的笔记。"
    ),
    "fetch_url": (
        "`fetch_url[url]` — 获取 URL 内容（HTTP GET）。\n"
        "  **何时使用**：用户给了一个链接让你「看看」「访问」「打开」，或需要调用 API\n"
        "  **不要使用**：用户只是分享链接聊天 → 不需要实际访问；搜索信息 → 用 web_search\n"
        "  **示例**：`fetch_url[https://api.github.com/users/octocat]`\n"
        "  **注意**：支持 JSON/HTML/文本响应。风险等级：中等（可能访问外部服务）。"
    ),

}

# ---------------------------------------------------------------------------
# Few-shot examples — one per skill category (ReAct paper: 3-6 shots)
# ---------------------------------------------------------------------------

_REACT_FEWSHOT = (
    "═══════════════════════════════════════════\n"
    "示例 1 — 使用记忆检索 + 计算（data + action 技能）：\n"
    "用户：我上周跑步的记录有哪些？顺便帮我算一下如果每天跑5公里，一个月跑多少。\n"
    "Thought: 用户首先需要查记忆里的跑步记录，这是 data 类技能。我先检索记忆。\n"
    "Action: memory_search[跑步 运动 记录]\n"
    "Observation: - [episodic] 用户周一跑步5公里，周三跑步3公里，周五跑步5公里\n"
    "Thought: 找到了跑步记录。现在用户还想算每天5公里一个月的总量——这是计算，用 calculator。\n"
    "Action: calculator[5 * 30]\n"
    "Observation: [calculator] 5 * 30 = 150\n"
    "Thought: 我有了完整的答案：用户上周跑了三次共13公里；如果每天5公里，一个月30天能跑150公里。\n"
    "Action: finish[你上周跑步三次：周一5公里、周三3公里、周五5公里，共13公里。如果每天跑5公里，一个月（30天）能跑150公里！]\n"
    "\n"
    "示例 2 — 使用时间 + 文件（data + action 技能）：\n"
    "用户：现在几点了？帮我把今天的待办事项写到 notes.txt 里。\n"
    "Thought: 用户问了两个独立任务：查时间和写文件。先查时间。\n"
    "Action: get_time[]\n"
    "Observation: Current UTC time: 2026-07-13T14:30:00. Day: Monday. Date: 2026-07-13.\n"
    "Thought: 现在是 UTC 14:30（北京时间约22:30）。接下来用户要写待办事项到 notes.txt。但用户没有说具体内容，我应该先问他或给一个模板。不过既然用户说「今天的待办事项」，我可以创建一个合理的模板。\n"
    "Action: write_file[notes.txt, 今日待办 (2026-07-13)\n1. \n2. \n3. ]\n"
    "Observation: [write_file] Written 45 chars to notes.txt\n"
    "Thought: 时间告诉用户了，文件也创建了。\n"
    "Action: finish[现在是 UTC 14:30（北京时间 22:30）。我在 notes.txt 里创建了待办事项模板，你可以直接编辑它！]\n"
    "\n"
    "示例 3 — 不需要工具（直接回答）：\n"
    "用户：你好呀，今天心情不错！\n"
    "Thought: 这是一个普通的问候，不需要任何工具。直接回复就好。\n"
    "Action: finish[你好！看到你心情好我也很开心～今天有什么想聊的或需要帮忙的吗？]\n"
    "\n"
    "示例 4 — 使用翻译（support 技能）：\n"
    "用户：帮我把 'Good morning, how are you today?' 翻译成中文。\n"
    "Thought: 用户要求翻译英文到中文，这是翻译任务。\n"
    "Action: translate[Good morning, how are you today?, zh]\n"
    "Observation: [translate] Request to translate the following text to zh:\n---\nGood morning, how are you today?\n---\n(Translation will be provided by the reasoning engine.)\n"
    "Thought: translate 工具返回了原文，现在我来完成翻译。\n"
    "Action: finish[早上好，你今天怎么样？]\n"
)

# ---------------------------------------------------------------------------
# Skill catalog builder (category-grouped, with progressive disclosure hints)
# ---------------------------------------------------------------------------

def _build_skill_catalog(tools: "ToolRegistry") -> str:
    """Build a category-grouped skill catalog for the system prompt.

    Groups skills by category so the model can quickly scan available
    capabilities without being overwhelmed by a flat list.
    """
    from .tools import SKILLS as _skills

    categories: dict[str, list[str]] = {}
    for s in _skills.list():
        categories.setdefault(s.category, []).append(s.name)

    lines = []
    cat_names = {
        "data": "【信息获取 Data】查询已有信息，不改变任何东西",
        "action": "【动作执行 Action】改变/创建内容，需要谨慎",
        "support": "【辅助 Support】增强推理，不直接修改外部状态",
    }

    for cat, skill_names in categories.items():
        label = cat_names.get(cat, f"【{cat}】")
        lines.append(f"\n{label}")
        for name in skill_names:
            doc = _SKILL_DOCS.get(name, f"  {name} — 无详细文档。")
            lines.append(doc)

    return "\n".join(lines)

# Regex patterns for parsing
_THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\n(?:Thought|Action|Observation):|$)", re.DOTALL)
_ACTION_RE = re.compile(r"Action:\s*(\w+)\[([^\]]*)\]")
_OBS_RE = re.compile(r"Observation:\s*(.+?)(?=\n(?:Thought|Action):|$)", re.DOTALL)


def _parse_tool_args(tool_input: str, param_schema: dict) -> dict:
    """Parse tool input string into kwargs based on parameter schema.

    Examples:
        "title, content" → {"title": "title", "content": "content"}
        "Python技巧, 用enumerate遍历" → {"title": "Python技巧", "content": "用enumerate遍历"}
    """
    if not tool_input or not param_schema:
        return {}

    param_names = list(param_schema.keys())

    # 按逗号分割（简单实现）
    parts = [p.strip() for p in tool_input.split(",")]

    # 匹配参数名和值
    kwargs = {}
    for i, name in enumerate(param_names):
        if i < len(parts):
            kwargs[name] = parts[i]
        else:
            kwargs[name] = ""  # 缺失参数用空字符串

    return kwargs



# ---------------------------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------------------------

class ReActLoop:
    def __init__(
        self,
        router: "CognitiveRouter",
        tools: "ToolRegistry",
        memory_store: "MemoryStore | None" = None,
        max_steps: int = 7,
        timeout_s: float = 120.0,
        skills: "SkillRegistry | None" = None,
    ):
        self.router = router
        self.tools = tools
        self.memory = memory_store
        self.max_steps = max_steps
        self.timeout_s = timeout_s
        self._skills = skills  # for usage tracking

    async def run(
        self,
        system_prompt: str,
        user_message: str,
        user_id: str = "",
        temperature: float = 0.7,
    ) -> ReActResult:
        """Run the full ReAct loop. Returns a ReActResult."""
        from ..engines.base import Complexity, EngineMessage
        from ..engines.router import CognitiveRequest

        t0 = time.monotonic()
        steps: list[ReActStep] = []

        # Build Anthropic-style skill catalog (category-grouped with usage docs)
        skill_catalog = _build_skill_catalog(self.tools)

        _REACT_SYSTEM_PROMPT = (
            "你是 Sunday，一个能使用工具的 AI 助手。\n\n"
            "## 核心规则\n"
            "1. 每条回复必须以 `Thought:` 或 `Action:` 开头。\n"
            "2. `Thought:` 写你的推理——分析用户意图、决定下一步。\n"
            "3. `Action:` 格式：`Action: 工具名[参数]` 或 `Action: finish[最终回答]`。\n"
            "4. 不要编造 Observation——只有系统才能返回 Observation。\n"
            "5. 每次一个 Thought + 一个 Action，不要一次性输出多步。\n"
            "6. **强制工具调用场景**（必须调用工具，禁止直接回答）：\n"
            "   - 持久化操作：保存笔记(save_note)、创建提醒(create_reminder)、列出笔记(list_notes)\n"
            "   - 文件操作：读文件(read_file)、写文件(write_file)\n"
            "   - 外部数据：查天气(get_weather)、查时间(get_time)、网页获取(fetch_url)、搜索(web_search)\n"
            "   - 计算任务：复杂计算(calculator)\n"
            "7. **可直接回答**：普通聊天、问候、情感交流、基于已知知识的解释说明。\n\n"
            "## ⚠️ 重要：不要模拟工具执行结果\n"
            "当用户要求「记笔记」「创建提醒」「查天气」「读文件」时：\n"
            "- ❌ 错误：直接回答「已保存笔记」「已创建提醒」（数据未持久化）\n"
            "- ✅ 正确：`Action: save_note[标题, 内容]` 等待 Observation，再基于实际结果回复\n\n"
            "## 技能目录\n{skills}\n\n"
            "## 示例\n{fewshot}"
        )

        system_prompt_full = _REACT_SYSTEM_PROMPT.format(
            skills=skill_catalog,
            fewshot=_REACT_FEWSHOT,
        )

        # Build messages list — start with system + user
        messages: list[EngineMessage] = [
            EngineMessage(role="system", content=system_prompt_full),
        ]
        if system_prompt:
            messages.insert(0, EngineMessage(role="system", content=system_prompt))
        messages.append(EngineMessage(role="user", content=user_message))

        final_answer = ""
        for step_idx in range(self.max_steps):
            # Check timeout
            if time.monotonic() - t0 > self.timeout_s:
                final_answer = self._force_finish(messages, steps)
                break

            # Call engine
            t_step = time.monotonic()
            req = CognitiveRequest(
                messages=messages,
                complexity=Complexity.L2_DAILY,  # text-driven ReAct, prompt provides structure
                prefer_chinese=True,
                temperature=temperature,
            )
            result = await self.router.route(req)

            if result.response is None:
                # All engines failed — log errors and force finish
                err_detail = "; ".join(
                    f"{eid}:{msg[:80]}" for eid, msg in result.trace.errors.items()
                ) if result.trace.errors else "unknown"
                logger.warning("ReAct step %d: all engines failed: %s", step_idx, err_detail)
                steps.append(ReActStep(
                    type="observation",
                    content=f"Engine error: {err_detail}",
                    latency_ms=round((time.monotonic() - t_step) * 1000, 1),
                ))
                # Try to synthesize from existing observations
                final_answer = self._synthesize_from_steps(steps, user_message)
                break

            response_text = result.response.text
            latency_ms = round((time.monotonic() - t_step) * 1000, 1)

            # Parse the response
            parsed = self._parse_response(response_text, latency_ms)
            steps.extend(parsed)

            # Add assistant response to message context
            messages.append(EngineMessage(role="assistant", content=response_text))

            # Process each parsed step
            for p in parsed:
                if p.type == "action":
                    # Execute tool
                    tool = self.tools.get(p.tool_name or "")
                    if tool is None:
                        obs_text = f"[error] Unknown tool: {p.tool_name}"
                        steps.append(ReActStep(type="observation", content=obs_text))
                        messages.append(EngineMessage(
                            role="user", content=f"Observation: {obs_text}",
                        ))
                        continue

                    # Guardrail: risk check
                    from ..guardrails.pipeline import requires_confirmation
                    if requires_confirmation(tool.name):
                        # High-risk tool → refuse in automatic mode
                        obs_text = (
                            f"[blocked] Tool '{tool.name}' requires human confirmation. "
                            f"Use a different approach."
                        )
                        steps.append(ReActStep(type="observation", content=obs_text))
                        messages.append(EngineMessage(role="tool", content=obs_text,
                                                       name=tool.name))
                        continue

                    # Execute
                    t_tool = time.monotonic()
                    try:
                        if tool.handler is None:
                            obs_text = f"[error] Tool '{tool.name}' has no handler."
                        elif tool.name == "memory_search":
                            obs_text = await tool.handler(
                                query=p.tool_input or "",
                                store=self.memory,
                                user_id=user_id,
                            )
                        elif tool.name in ("create_reminder", "save_note", "list_notes"):
                            # 这些工具需要 store 和 user_id 注入
                            kwargs = _parse_tool_args(p.tool_input or "", tool.params)
                            kwargs["store"] = self.memory
                            kwargs["user_id"] = user_id
                            obs_text = await tool.handler(**kwargs)
                        elif len(tool.params) > 1:
                            # 多参数工具：解析参数
                            kwargs = _parse_tool_args(p.tool_input or "", tool.params)
                            obs_text = await tool.handler(**kwargs)
                        elif tool.params:
                            # 单参数工具：直接传递
                            obs_text = await tool.handler(
                                **{list(tool.params.keys())[0]: p.tool_input or ""}
                            )
                        else:
                            obs_text = await tool.handler()
                    except Exception as e:
                        obs_text = f"[error] Tool '{tool.name}' failed: {e}"

                    tool_latency = round((time.monotonic() - t_tool) * 1000, 1)
                    # Record skill usage
                    if hasattr(self, '_skills') and self._skills:
                        self._skills.record_usage(tool.name)
                    obs_step = ReActStep(
                        type="observation",
                        content=obs_text,
                        tool_name=p.tool_name,
                        tool_output=obs_text,
                        latency_ms=tool_latency,
                    )
                    steps.append(obs_step)
                    # Append as user message for better model compatibility
                    messages.append(EngineMessage(
                        role="user",
                        content=f"Observation: {obs_text}",
                    ))

                elif p.type == "finish":
                    final_answer = p.content
                    break

                elif p.type == "ask":
                    # Pause for user — reformulate as HITL answer
                    final_answer = (
                        f"我需要更多信息：{p.content}\n\n"
                        f"请回复我，我会继续处理。"
                    )
                    break

            if final_answer:
                break

        # If we exhausted max_steps without finishing
        if not final_answer:
            final_answer = self._force_finish(messages, steps)

        return ReActResult(
            answer=final_answer,
            steps=steps,
            total_latency_ms=round((time.monotonic() - t0) * 1000, 1),
        )

    # -- response parsing -----------------------------------------------------

    def _parse_response(self, text: str, latency_ms: float) -> list[ReActStep]:
        """Parse a single engine response into ReAct steps.

        The LLM is instructed to output one Thought + one Action per turn,
        but some models may output multiple. Parse all of them.
        """
        steps: list[ReActStep] = []

        # Try to parse structured Thought/Action pairs first
        thoughts = _THOUGHT_RE.findall(text)
        actions = _ACTION_RE.findall(text)

        for thought_text in thoughts:
            clean = thought_text.strip()
            if clean:
                steps.append(ReActStep(
                    type="thought", content=clean, latency_ms=latency_ms,
                ))

        for tool_name, tool_input in actions:
            tn = tool_name.strip()
            ti = tool_input.strip()
            if tn in ("finish", "answer"):
                steps.append(ReActStep(
                    type="finish", content=ti,
                    tool_name=tn, tool_input=ti, latency_ms=latency_ms,
                ))
            elif tn == "ask":
                steps.append(ReActStep(
                    type="ask", content=ti,
                    tool_name=tn, tool_input=ti, latency_ms=latency_ms,
                ))
            else:
                steps.append(ReActStep(
                    type="action", content=f"{tn}[{ti}]",
                    tool_name=tn, tool_input=ti, latency_ms=latency_ms,
                ))

        # If no structured output found, treat entire response as a
        # direct answer (engine ignored the ReAct format)
        if not thoughts and not actions:
            # Check for finish pattern anywhere in the text
            finish_match = re.search(r"(?:Action:\s*)?finish\[([^\]]+)\]", text)
            if finish_match:
                steps.append(ReActStep(
                    type="finish", content=finish_match.group(1),
                    latency_ms=latency_ms,
                ))
            else:
                # Treat as final answer
                steps.append(ReActStep(
                    type="finish", content=text.strip(),
                    latency_ms=latency_ms,
                ))

        return steps

    # -- force finish ---------------------------------------------------------

    def _force_finish(
        self, messages: list, steps: list[ReActStep],
    ) -> str:
        """Force a best-effort answer from the last Observation."""
        return self._synthesize_from_steps(steps, "")

    def _synthesize_from_steps(self, steps: list[ReActStep], user_message: str) -> str:
        """Build a best-effort answer from ReAct observations."""
        observations = [s for s in steps if s.type == "observation" and s.tool_output]
        if observations:
            last_obs = observations[-1].tool_output or observations[-1].content
            return f"根据工具返回的结果：\n{last_obs}\n\n你可以继续问我其他问题。"
        return (
            "我花了一点时间来处理这个请求。"
            "根据目前的信息，建议分步骤处理这个任务。"
            "你可以换个方式问我，或者给我更具体的指令。"
        )

"""ReAct loop tests — parsing, tool execution, step counting."""
import pytest
from app.cognition.react_loop import ReActLoop, ReActStep, ReActResult
from app.cognition.tools import TOOLS, ToolRegistry, Tool
from app.engines.providers import MockProvider
from app.engines.router import CognitiveRouter


def _router():
    return CognitiveRouter([MockProvider(id="mock")])


def _tools():
    """Return a fresh registry with memory + calculator for tests."""
    from app.cognition.tools import (
        _memory_search_handler, _calculator_handler, _get_time_handler,
    )
    r = ToolRegistry()
    r.register(Tool("memory_search", "Search memory", {"query": "string"},
                    "low", _memory_search_handler))
    r.register(Tool("calculator", "Math", {"expression": "string"},
                    "low", _calculator_handler))
    r.register(Tool("get_time", "Get time", {}, "low", _get_time_handler))
    return r


# -- parsing ----------------------------------------------------------------

def test_parse_thought_action():
    loop = ReActLoop(_router(), _tools())
    text = "Thought: I need to search\nAction: memory_search[user preferences]\nObservation: result"
    steps = loop._parse_response(text, 100.0)
    types = [s.type for s in steps]
    assert "thought" in types
    assert "action" in types


def test_parse_finish():
    loop = ReActLoop(_router(), _tools())
    text = "Thought: I have the answer\nAction: finish[The answer is 42]"
    steps = loop._parse_response(text, 100.0)
    finish_steps = [s for s in steps if s.type == "finish"]
    assert len(finish_steps) == 1
    assert "42" in finish_steps[0].content


def test_parse_direct_answer():
    """When engine returns plain text without ReAct format, treat as finish."""
    loop = ReActLoop(_router(), _tools())
    text = "Hello, how can I help you today?"
    steps = loop._parse_response(text, 100.0)
    assert any(s.type == "finish" for s in steps)


# -- full loop --------------------------------------------------------------

@pytest.mark.asyncio
async def test_simple_query_uses_talker_path():
    """Simple message should complete quickly (single or few steps)."""
    loop = ReActLoop(_router(), _tools(), max_steps=3)
    result = await loop.run(
        system_prompt="You are helpful.",
        user_message="What is 2+2?",
    )
    assert isinstance(result, ReActResult)
    assert len(result.answer) > 0
    assert result.total_latency_ms >= 0


@pytest.mark.asyncio
async def test_max_steps_doesnt_crash():
    """Even at max_steps=0, the loop should return a result."""
    loop = ReActLoop(_router(), _tools(), max_steps=0)
    result = await loop.run(
        system_prompt="You are helpful.",
        user_message="Complex multi-step task",
    )
    assert isinstance(result.answer, str)
    assert len(result.answer) > 0


def test_tool_registry_list():
    assert len(TOOLS.list()) >= 8
    assert TOOLS.get("calculator") is not None
    assert TOOLS.get("nonexistent") is None


def test_tool_to_openai_format():
    fmt = TOOLS.to_openai()
    assert len(fmt) >= 8
    assert fmt[0]["type"] == "function"
    assert "name" in fmt[0]["function"]


@pytest.mark.asyncio
async def test_calculator_tool():
    handler = TOOLS.get("calculator").handler
    assert handler is not None
    result = await handler(expression="2+2")
    assert "4" in result


@pytest.mark.asyncio
async def test_get_time_tool():
    handler = TOOLS.get("get_time").handler
    assert handler is not None
    result = await handler()
    assert "UTC" in result

def test_skill_registry_categories():
    from app.cognition.tools import SKILLS
    cats = SKILLS.categories()
    assert "data" in cats
    assert "action" in cats
    assert "support" in cats
    assert SKILLS.get("memory_search") is not None
    assert SKILLS.get("memory_search").category == "data"
    s = SKILLS.summary()
    assert s["total"] >= 8
    assert "by_category" in s

def test_skill_usage_tracking():
    from app.cognition.tools import SKILLS
    SKILLS.record_usage("calculator")
    calc = SKILLS.get("calculator")
    assert calc.usage_count > 0


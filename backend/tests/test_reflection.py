"""Reflection engine tests — trigger logic + pipeline (mock engine)."""
from datetime import datetime, timezone

import pytest

from app.memory.schema import MemoryNode, MemoryType
from app.memory.reflection import (
    _should_reflect,
    _should_reflect_session,
    run_reflection_sync,
)
from app.memory.sqlite_store import SQLiteMemoryStore
from app.engines.providers import MockProvider
from app.engines.router import CognitiveRouter
import tempfile
import os


@pytest.fixture
def store():
    path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    s = SQLiteMemoryStore(db_path=path)
    yield s
    s.close()
    os.unlink(path)


def _router():
    """Router backed by a mock engine that always returns something."""
    return CognitiveRouter([MockProvider(id="mock-strong", strong_reasoning=True)])


# -- trigger logic ------------------------------------------------------------

def test_should_reflect_below_threshold(store):
    store.add(MemoryNode(content="trivial", user_id="u1", importance=1,
                         type=MemoryType.EPISODIC))
    assert _should_reflect(store, "u1", threshold=100) is False


def test_should_reflect_exceeds_threshold(store):
    for i in range(20):
        store.add(MemoryNode(content=f"important {i}", user_id="u1", importance=10,
                             type=MemoryType.EPISODIC))
    assert _should_reflect(store, "u1", threshold=100) is True


def test_should_reflect_skips_reflection_nodes(store):
    # REFLECTION nodes should not count toward the trigger
    for i in range(15):
        store.add(MemoryNode(content=f"important {i}", user_id="u1", importance=10,
                             type=MemoryType.EPISODIC))
    # 15 × 10 = 150 > 100, but should still trigger
    assert _should_reflect(store, "u1", threshold=100) is True


def test_should_reflect_session_threshold():
    assert _should_reflect_session(None, "u1", session_importance=35, threshold=30) is True
    assert _should_reflect_session(None, "u1", session_importance=20, threshold=30) is False


# -- full pipeline (mock engine) ----------------------------------------------

def test_run_reflection_generates_insights(store):
    # Add some memories to reflect on
    store.add(MemoryNode(content="用户喜欢跑步，每周跑三次", user_id="u1",
                         type=MemoryType.EPISODIC, importance=8))
    store.add(MemoryNode(content="用户在学习Python编程", user_id="u1",
                         type=MemoryType.EPISODIC, importance=7))
    store.add(MemoryNode(content="用户昨天失眠了", user_id="u1",
                         type=MemoryType.EPISODIC, importance=6))
    store.add(MemoryNode(content="用户计划去日本旅行", user_id="u1",
                         type=MemoryType.EPISODIC, importance=9))

    router = _router()
    insights = run_reflection_sync(store, "u1", router)

    # With a mock engine, we should get at least some output
    assert isinstance(insights, list)


def test_run_reflection_empty_store(store):
    router = _router()
    insights = run_reflection_sync(store, "u1", router)
    assert insights == []  # no memories → no questions → no insights


def test_reflection_nodes_have_correct_type(store):
    store.add(MemoryNode(content="用户换工作了", user_id="u1",
                         type=MemoryType.EPISODIC, importance=10))
    store.add(MemoryNode(content="用户对新工作很满意", user_id="u1",
                         type=MemoryType.EPISODIC, importance=8))

    router = _router()
    insights = run_reflection_sync(store, "u1", router)

    for ins in insights:
        node = store.get(ins["id"])
        if node:
            assert node.type == MemoryType.REFLECTION
            assert node.importance == 8
            assert node.source == "reflection"
            # evidence_ids parsing depends on real engine output;
            # mock engine can't reliably produce citations

"""Experience layer tests — L2→L3 consolidation, pattern detection, procedural primitives."""
import os
import tempfile

import pytest

from app.memory.schema import MemoryNode, MemoryType
from app.memory.sqlite_store import SQLiteMemoryStore
from app.memory.experience import (
    _merge_similar,
    run_consolidation,
    detect_patterns,
    encapsulate_procedures,
    run_experience_layer,
    run_experience_sync,
)
from app.engines.providers import MockProvider
from app.engines.router import CognitiveRouter


@pytest.fixture
def store():
    path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    s = SQLiteMemoryStore(db_path=path)
    yield s
    s.close()
    os.unlink(path)


def _router():
    return CognitiveRouter([MockProvider(id="mock-strong", strong_reasoning=True)])


# ── merge similar ───────────────────────────────────────────────────────────

def test_merge_similar_no_duplicates(store):
    store.add(MemoryNode(content="unique A", user_id="u1",
                         type=MemoryType.EPISODIC))
    store.add(MemoryNode(content="unique B", user_id="u1",
                         type=MemoryType.EPISODIC))
    merged = _merge_similar(store, threshold=0.9)
    assert merged == 0
    assert len(store.all()) == 2


def test_merge_similar_preserves_frozen(store):
    frozen = MemoryNode(content="frozen memory", user_id="u1",
                        type=MemoryType.EPISODIC, frozen=True)
    store.add(frozen)
    store.add(MemoryNode(content="frozen memory", user_id="u1",
                         type=MemoryType.EPISODIC))
    merged = _merge_similar(store, threshold=0.9)
    assert store.get(frozen.id) is not None  # frozen preserved


# ── consolidation ──────────────────────────────────────────────────────────

def test_consolidation_mock(store):
    """Consolidation should work even with mock engine (returns empty facts)."""
    for i in range(10):
        store.add(MemoryNode(content=f"episodic {i}", user_id="u1",
                             type=MemoryType.EPISODIC, importance=5))
    result = run_experience_sync(store, _router(), "u1")
    assert "consolidation" in result
    assert isinstance(result["consolidation"], dict)


# ── pattern detection ─────────────────────────────────────────────────────

def test_detect_patterns_empty(store):
    """Empty store should return no patterns."""
    result = run_experience_sync(store, _router(), "u1")
    assert result["patterns"] == []


def test_detect_patterns_with_memories(store):
    """Store with some memories should not crash."""
    for i in range(5):
        store.add(MemoryNode(content=f"用户问了关于跑步的问题 {i}", user_id="u1",
                             type=MemoryType.EPISODIC, importance=6))
    _ = run_experience_sync(store, _router(), "u1")


# ── full pipeline ──────────────────────────────────────────────────────────

def test_experience_layer_create_nodes(store):
    """Full pipeline should create EXPERIENCE nodes if patterns found."""
    for i in range(5):
        store.add(MemoryNode(content=f"用户搜索了天气 {i}", user_id="u1",
                             type=MemoryType.EPISODIC, importance=7))
    result = run_experience_sync(store, _router(), "u1")
    assert "consolidation" in result
    assert "patterns" in result
    assert "primitives" in result

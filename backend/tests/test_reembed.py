"""Embedder-upgrade migration tests — reembed_stale + provider detection.

Covers the silent dim-mismatch bug: when the embedder is swapped to a higher
dimension, old vectors become uncomparable (cosine returns 0.0), so retrieval
silently loses all history until re-embedded.
"""
import os
import tempfile

import pytest

from app.memory import embedding as emb
from app.memory.schema import MemoryNode
from app.memory.store import MemoryStore
from app.memory.sqlite_store import SQLiteMemoryStore


@pytest.fixture(autouse=True)
def _restore_embedder():
    """Every test starts and ends on the hash embedder."""
    emb.set_embedder(emb._hash_embed, dim=emb._DIM, provider="hash")
    yield
    emb.set_embedder(emb._hash_embed, dim=emb._DIM, provider="hash")


def _fake_1024(text: str):
    """Deterministic fake 'semantic' embedder at a different dim than hash."""
    v = [0.0] * 1024
    for i, ch in enumerate(text):
        v[(ord(ch) + i) % 1024] += 1.0
    return v


# -- reembed_stale (in-memory) -----------------------------------------------

def test_reembed_stale_fixes_dim_mismatch():
    s = MemoryStore()
    n = s.add(MemoryNode(content="我喜欢跑步", user_id="u1"))
    assert len(n.embedding) == emb._DIM  # hash dim

    # Upgrade embedder to a different dim — old vector is now stale
    emb.set_embedder(_fake_1024, dim=1024, provider="fake")
    assert len(n.embedding) != emb.embedding_dim()

    fixed = s.reembed_stale()
    assert fixed == 1
    assert len(s.get(n.id).embedding) == 1024


def test_reembed_stale_is_idempotent():
    s = MemoryStore()
    s.add(MemoryNode(content="a", user_id="u1"))
    emb.set_embedder(_fake_1024, dim=1024, provider="fake")
    assert s.reembed_stale() == 1
    assert s.reembed_stale() == 0  # nothing stale on second pass


def test_reembed_stale_noop_when_dims_match():
    s = MemoryStore()
    s.add(MemoryNode(content="a", user_id="u1"))
    # Same embedder, same dim → nothing to do
    assert s.reembed_stale() == 0


# -- reembed_stale (SQLite, persists) ----------------------------------------

def test_reembed_stale_persists_to_sqlite():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        s = SQLiteMemoryStore(db_path=path)
        n = s.add(MemoryNode(content="语义检索测试", user_id="u1"))
        assert len(n.embedding) == emb._DIM

        emb.set_embedder(_fake_1024, dim=1024, provider="fake")
        assert s.reembed_stale() == 1
        s.close()

        # Re-open: the persisted vector must be the new dim, not the hash one
        s2 = SQLiteMemoryStore(db_path=path)
        assert len(s2.get(n.id).embedding) == 1024
        s2.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# -- provider detection ------------------------------------------------------

def test_qwen_key_selects_qwen_provider(monkeypatch):
    for k in ("QWEN_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("QWEN_API_KEY", "sk-fake-qwen")
    got = emb.try_semantic_embedder()
    assert got is not None
    embedder, provider = got
    assert provider == "qwen"
    assert embedder._dim == 1024
    assert "dashscope" in embedder._base_url


def test_openai_key_selects_openai_when_no_qwen(monkeypatch):
    for k in ("QWEN_API_KEY", "DASHSCOPE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-openai")
    got = emb.try_semantic_embedder()
    assert got is not None
    _, provider = got
    assert provider == "openai"


def test_no_key_returns_none(monkeypatch):
    for k in ("QWEN_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert emb.try_semantic_embedder() is None

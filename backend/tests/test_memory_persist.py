"""SQLiteMemoryStore tests — persistence + same search interface."""
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from app.memory.schema import MemoryNode, MemoryType
from app.memory.sqlite_store import SQLiteMemoryStore


@pytest.fixture
def store():
    """Each test gets a fresh temp DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = SQLiteMemoryStore(db_path=path)
    yield s
    s.close()
    import os
    try:
        os.unlink(path)
    except OSError:
        pass


def _mk(content, uid="u1", importance=5, created=None):
    n = MemoryNode(content=content, user_id=uid, importance=importance)
    if created:
        n.created_at = created
        n.last_access = created
    return n


# -- basic CRUD ---------------------------------------------------------------

def test_add_and_get_same_instance(store):
    n = store.add(_mk("hello world"))
    fetched = store.get(n.id)
    assert fetched is not None
    assert fetched.content == "hello world"


def test_add_persists_across_connections(store):
    n = store.add(_mk("persistent memory"))
    store.close()
    # open a new connection to the same file
    s2 = SQLiteMemoryStore(db_path=store._db_path)
    fetched = s2.get(n.id)
    assert fetched is not None
    assert fetched.content == "persistent memory"
    s2.close()


def test_delete_removes_from_db(store):
    n = store.add(_mk("to be deleted"))
    assert store.delete(n.id) is True
    assert store.get(n.id) is None
    assert store.delete("nonexistent") is False


# -- retrieval ----------------------------------------------------------------

# NOTE: semantic relevance ranking with the hash embedder is unreliable for
# Chinese (no whitespace tokenization). This test is deferred until a real
# embedding model is plugged in (see 1c in the plan).

def test_retrieve_user_isolation(store):
    store.add(_mk("A 的记忆", uid="A"))
    store.add(_mk("B 的记忆", uid="B"))
    hits = store.retrieve("记忆", user_id="A", k=5)
    assert all(h.node.user_id == "A" for h in hits)


def test_retrieve_touches_access(store):
    n = store.add(_mk("access test"))
    assert n.access_count == 0
    store.retrieve("access test", user_id="u1", k=1)
    fetched = store.get(n.id)
    assert fetched is not None
    assert fetched.access_count >= 1


def test_importance_boosts_score(store):
    now = datetime.now(timezone.utc)
    store.add(_mk("same A", importance=10, created=now))
    store.add(_mk("same B", importance=1, created=now))
    hits = store.retrieve("same", user_id="u1", k=2)
    assert hits[0].node.importance == 10


def test_recency_decays_old(store):
    now = datetime.now(timezone.utc)
    store.add(_mk("old memory", importance=5, created=now - timedelta(days=10)))
    store.add(_mk("new memory", importance=5, created=now))
    hits = store.retrieve("memory", user_id="u1", k=2)
    assert hits[0].node.content == "new memory"


def test_archive_expired(store):
    old = datetime.now(timezone.utc) - timedelta(days=400)
    store.add(_mk("普通旧记忆", importance=2, created=old))
    store.add(_mk("关键记忆", importance=10, created=old))
    dropped = store.archive_expired(threshold=0.4)
    assert dropped == 1
    assert any(n.importance == 10 for n in store.all())


def test_all_filters_user(store):
    store.add(_mk("alice's", uid="alice"))
    store.add(_mk("bob's", uid="bob"))
    assert len(store.all("alice")) == 1
    assert len(store.all()) == 2


def test_type_filtering_on_retrieve(store):
    store.add(MemoryNode(content="episodic mem", user_id="u1",
                         type=MemoryType.EPISODIC))
    store.add(MemoryNode(content="reflection mem", user_id="u1",
                         type=MemoryType.REFLECTION))
    hits = store.retrieve("mem", user_id="u1", k=5,
                          types=[MemoryType.REFLECTION])
    assert len(hits) == 1
    assert hits[0].node.type == MemoryType.REFLECTION

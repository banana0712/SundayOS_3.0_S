"""Memory retrieval scoring tests (docs §4.4, §4.7)."""
from datetime import datetime, timedelta, timezone

from app.memory.schema import MemoryNode, MemoryType
from app.memory.store import MemoryStore


def _mk(content, uid="u1", importance=5, created=None):
    n = MemoryNode(content=content, user_id=uid, importance=importance)
    if created:
        n.created_at = created
        n.last_access = created
    return n


def test_relevance_ranks_semantically_closer_first():
    s = MemoryStore()
    s.add(_mk("用户喜欢跑步和马拉松训练"))
    s.add(_mk("用户在学习软件工程"))
    s.add(_mk("今天天气不错"))
    hits = s.retrieve("跑步 训练", user_id="u1", k=3)
    assert hits[0].node.content.startswith("用户喜欢跑步")


def test_importance_boosts_score():
    s = MemoryStore()
    now = datetime.now(timezone.utc)
    s.add(_mk("同一句话 A", importance=10, created=now))
    s.add(_mk("同一句话 B", importance=1, created=now))
    hits = s.retrieve("同一句话", user_id="u1", k=2)
    # higher importance should win when recency+relevance are equal
    assert hits[0].node.importance == 10


def test_recency_decays_older_memories():
    s = MemoryStore()
    now = datetime.now(timezone.utc)
    s.add(_mk("旧记忆", importance=5, created=now - timedelta(days=10)))
    s.add(_mk("新记忆", importance=5, created=now))
    hits = s.retrieve("记忆", user_id="u1", k=2)
    assert hits[0].node.content == "新记忆"


def test_retrieve_touches_access_count():
    s = MemoryStore()
    n = s.add(_mk("可访问记忆"))
    assert n.access_count == 0
    s.retrieve("可访问记忆", user_id="u1", k=1)
    assert n.access_count == 1


def test_user_isolation():
    s = MemoryStore()
    s.add(_mk("A 的记忆", uid="A"))
    s.add(_mk("B 的记忆", uid="B"))
    hits = s.retrieve("记忆", user_id="A", k=5)
    assert all(h.node.user_id == "A" for h in hits)


def test_archive_expired_keeps_critical():
    s = MemoryStore()
    old = datetime.now(timezone.utc) - timedelta(days=400)
    s.add(_mk("普通旧记忆", importance=2, created=old))
    s.add(_mk("关键记忆", importance=10, created=old))
    dropped = s.archive_expired(threshold=0.4)
    assert dropped == 1
    assert any(n.importance == 10 for n in s.all())


def test_effective_importance_decays():
    now = datetime.now(timezone.utc)
    fresh = MemoryNode(content="x", user_id="u", importance=8)
    fresh.created_at = now
    old = MemoryNode(content="x", user_id="u", importance=8)
    old.created_at = now - timedelta(days=60)
    assert fresh.effective_importance(now) > old.effective_importance(now)

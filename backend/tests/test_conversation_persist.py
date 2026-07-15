"""SQLiteConversationStore tests — persistence + same CRUD interface."""
import os
import tempfile

import pytest

from app.conversation.sqlite_store import SQLiteConversationStore


@pytest.fixture
def store():
    """Each test gets a fresh temp DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = SQLiteConversationStore(db_path=path)
    yield s
    s.close()
    try:
        os.unlink(path)
    except OSError:
        pass


# -- interface parity with in-memory store -----------------------------------

def test_create_and_get(store):
    conv = store.create("u1")
    assert conv.id.startswith("conv_")
    assert conv.title == "新对话"
    fetched = store.get(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id


def test_list_newest_first_scoped_to_user(store):
    store.create("alice")
    b = store.create("alice")
    store.create("bob")
    convs = store.list("alice")
    assert len(convs) == 2
    assert convs[0].id == b.id  # newest first
    assert len(store.list("bob")) == 1


def test_delete(store):
    c = store.create("u1")
    assert store.delete(c.id) is True
    assert store.get(c.id) is None
    assert store.delete("nonexistent") is False


def test_rename(store):
    c = store.create("u1")
    assert store.rename(c.id, "日本旅行计划")
    assert store.get(c.id).title == "日本旅行计划"
    assert store.rename("nonexistent", "x") is False


def test_add_message_appends_and_auto_titles(store):
    c = store.create("u1")
    assert store.add_message(c.id, "user", "帮我规划日本旅行，七天的行程")
    assert store.add_message(c.id, "assistant", "好的", engine="deepseek-chat")
    conv = store.get(c.id)
    assert len(conv.messages) == 2
    assert conv.title == "帮我规划日本旅行，七天的行程"  # auto-titled
    assert conv.messages[1]["engine"] == "deepseek-chat"


def test_add_message_ignores_nonexistent(store):
    assert store.add_message("nonexistent", "user", "hello") is False


def test_count(store):
    assert store.count() == 0
    store.create("u1")
    store.create("u2")
    assert store.count() == 2


# -- the whole point: persistence across connections --------------------------

def test_conversation_persists_across_connections(store):
    conv = store.create("u1", "持久化测试")
    store.add_message(conv.id, "user", "第一条消息")
    store.add_message(conv.id, "assistant", "回复", engine="deepseek-chat")
    store.close()

    # reopen the same file with a fresh connection — simulates a restart
    s2 = SQLiteConversationStore(db_path=store._db_path)
    fetched = s2.get(conv.id)
    assert fetched is not None
    assert fetched.title == "持久化测试"
    assert len(fetched.messages) == 2
    assert fetched.messages[0]["content"] == "第一条消息"
    assert fetched.messages[1]["engine"] == "deepseek-chat"
    assert s2.count() == 1
    s2.close()

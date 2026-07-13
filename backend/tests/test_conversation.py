"""ConversationStore tests — session CRUD + message management."""
from app.conversation.store import ConversationStore


def test_create_and_get():
    s = ConversationStore()
    conv = s.create("u1")
    assert conv.id.startswith("conv_")
    assert conv.title == "新对话"
    assert s.get(conv.id) is conv


def test_list_returns_newest_first():
    s = ConversationStore()
    a = s.create("u1")
    b = s.create("u1")
    convs = s.list("u1")
    assert len(convs) == 2
    assert convs[0].id == b.id  # newest first


def test_list_scoped_to_user():
    s = ConversationStore()
    s.create("alice")
    s.create("bob")
    assert len(s.list("alice")) == 1


def test_delete_removes_conversation():
    s = ConversationStore()
    c = s.create("u1")
    assert s.delete(c.id) is True
    assert s.get(c.id) is None
    assert s.delete("nonexistent") is False


def test_rename_updates_title():
    s = ConversationStore()
    c = s.create("u1")
    assert s.rename(c.id, "日本旅行计划")
    assert s.get(c.id).title == "日本旅行计划"
    assert s.rename("nonexistent", "x") is False


def test_add_message_appends_and_auto_titles():
    s = ConversationStore()
    c = s.create("u1")
    assert s.add_message(c.id, "user", "帮我规划日本旅行，七天的行程")
    assert s.add_message(c.id, "assistant", "好的，我来帮你规划", engine="deepseek-chat")
    conv = s.get(c.id)
    assert len(conv.messages) == 2
    assert conv.title == "帮我规划日本旅行，七天的行程"  # auto-titled
    assert conv.messages[0]["role"] == "user"
    assert conv.messages[1]["engine"] == "deepseek-chat"


def test_auto_title_truncates_long_messages():
    s = ConversationStore()
    c = s.create("u1")
    s.add_message(c.id, "user", "这是一条非常非常非常非常非常非常长的消息用来测试截断功能是否正常工作")
    conv = s.get(c.id)
    assert conv.title.endswith("…")
    assert len(conv.title) <= 33  # 30 chars + "…"


def test_add_message_ignores_nonexistent_conversation():
    s = ConversationStore()
    assert s.add_message("nonexistent", "user", "hello") is False


def test_count_reflects_all_conversations():
    s = ConversationStore()
    assert s.count() == 0
    s.create("u1")
    s.create("u2")
    assert s.count() == 2

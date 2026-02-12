"""Tests for conversation history module (R-02)."""

from voice_agent.history import ConversationHistory


def test_add_and_retrieve():
    """Messages are stored and retrievable."""
    history = ConversationHistory(max_turns=20)
    history.add("user", "Hello")
    history.add("assistant", "Hi there!")
    msgs = history.get_messages_for_llm()
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "Hello"}
    assert msgs[1] == {"role": "assistant", "content": "Hi there!"}


def test_clear():
    """clear() removes all messages."""
    history = ConversationHistory()
    history.add("user", "test")
    history.clear()
    assert len(history) == 0
    assert history.messages == []


def test_len():
    """__len__ returns message count."""
    history = ConversationHistory()
    assert len(history) == 0
    history.add("user", "a")
    assert len(history) == 1


def test_max_turns_enforced():
    """Oldest non-system messages are trimmed when max_turns is exceeded."""
    history = ConversationHistory(max_turns=2)
    # Add 3 full turns (6 messages)
    for i in range(3):
        history.add("user", f"msg-{i}")
        history.add("assistant", f"reply-{i}")
    # Should only keep last 2 turns (4 messages)
    msgs = history.get_messages_for_llm()
    assert len(msgs) == 4
    assert msgs[0]["content"] == "msg-1"
    assert msgs[-1]["content"] == "reply-2"


def test_system_message_preserved():
    """System messages are never trimmed, even when max_turns is exceeded."""
    history = ConversationHistory(max_turns=1)
    history.add("system", "You are helpful.")
    for i in range(3):
        history.add("user", f"msg-{i}")
        history.add("assistant", f"reply-{i}")
    msgs = history.get_messages_for_llm()
    # 1 system + 2 (1 turn)
    assert len(msgs) == 3
    assert msgs[0]["role"] == "system"
    assert msgs[1]["content"] == "msg-2"


def test_no_limit():
    """max_turns=0 disables the cap."""
    history = ConversationHistory(max_turns=0)
    for i in range(100):
        history.add("user", f"msg-{i}")
    assert len(history) == 100


def test_messages_returns_copy():
    """messages property returns a copy, not the internal list."""
    history = ConversationHistory()
    history.add("user", "test")
    msgs = history.messages
    msgs.clear()
    assert len(history) == 1

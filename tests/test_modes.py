"""Tests for the dual assistant mode architecture (R-08)."""

import pathlib

import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.modes import (
    AgentMode,
    ChatMode,
    ModeHandler,
    get_mode_handler,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_config(mode: str = "chat", scratchpad_path: str = "") -> ConfigNode:
    """Return a minimal ConfigNode for testing."""
    return ConfigNode({
        "assistant": {"name": "TestBot", "persona": "A test bot."},
        "human": {"name": "Tester"},
        "stt": {"engine": "moonshine"},
        "llm": {"provider": "ollama", "model": "gemma3:4b"},
        "tts": {"provider": "kokoro", "voice": "af_heart"},
        "mode": mode,
        "conversation": {"max_turns": 10},
        "scratchpad": {"file": scratchpad_path},
    })


@pytest.fixture
def sp_path(tmp_path):
    """Return a cross-platform temporary scratchpad path."""
    return str(tmp_path / "_test_scratchpad_modes.md")


@pytest.fixture
def chat_config(sp_path):
    return _make_config("chat", scratchpad_path=sp_path)


@pytest.fixture
def agent_config(sp_path):
    return _make_config("agent", scratchpad_path=sp_path)


@pytest.fixture
def mock_llm():
    """Return a mock LLM backend."""
    llm = MagicMock()
    llm.chat.return_value = "Mock LLM response"
    return llm


@pytest.fixture(autouse=True)
def clean_scratchpad(sp_path):
    """Ensure the test scratchpad does not exist."""
    sp = pathlib.Path(sp_path)
    sp.unlink(missing_ok=True)
    yield
    sp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Base class tests
# ---------------------------------------------------------------------------


def test_mode_handler_is_abstract(sp_path):
    """ModeHandler cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ModeHandler(config=_make_config(scratchpad_path=sp_path))


# ---------------------------------------------------------------------------
# ChatMode tests
# ---------------------------------------------------------------------------


def test_chat_mode_builds_system_prompt(chat_config, mock_llm):
    """ChatMode uses the system_prompt template."""
    handler = ChatMode(config=chat_config, llm=mock_llm)
    # System prompt should contain the assistant name
    messages = handler.history.get_messages_for_llm()
    system_msgs = [m for m in messages if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert "TestBot" in system_msgs[0]["content"]


def test_chat_mode_name(chat_config, mock_llm):
    """ChatMode reports mode_name as 'chat'."""
    handler = ChatMode(config=chat_config, llm=mock_llm)
    assert handler.mode_name == "chat"


def test_chat_mode_handle_turn(chat_config, mock_llm):
    """ChatMode.handle_turn adds messages and returns LLM response."""
    handler = ChatMode(config=chat_config, llm=mock_llm)
    response = handler.handle_turn("Hello there")

    assert response == "Mock LLM response"
    mock_llm.chat.assert_called_once()

    # Verify history contains system + user + assistant
    messages = handler.history.get_messages_for_llm()
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant"]
    assert messages[1]["content"] == "Hello there"
    assert messages[2]["content"] == "Mock LLM response"


def test_chat_mode_multi_turn(chat_config, mock_llm):
    """ChatMode maintains multi-turn history."""
    mock_llm.chat.side_effect = ["Response 1", "Response 2"]
    handler = ChatMode(config=chat_config, llm=mock_llm)

    handler.handle_turn("First message")
    handler.handle_turn("Second message")

    messages = handler.history.get_messages_for_llm()
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user", "assistant"]


def test_chat_mode_repr(chat_config, mock_llm):
    """ChatMode has a meaningful repr."""
    handler = ChatMode(config=chat_config, llm=mock_llm)
    assert "ChatMode" in repr(handler)


def test_chat_mode_with_context_files(chat_config, mock_llm, tmp_path):
    """ChatMode injects context file contents into the system prompt."""
    ctx_file = tmp_path / "notes.txt"
    ctx_file.write_text("Important reference info.")

    handler = ChatMode(
        config=chat_config, llm=mock_llm, context_files=[str(ctx_file)]
    )
    messages = handler.history.get_messages_for_llm()
    system_content = messages[0]["content"]
    assert "Important reference info." in system_content


def test_chat_mode_with_scratchpad(chat_config, mock_llm, sp_path):
    """ChatMode includes scratchpad contents in the system prompt."""
    sp = pathlib.Path(sp_path)
    sp.write_text("Remember: user prefers dark mode.")

    handler = ChatMode(config=chat_config, llm=mock_llm)
    messages = handler.history.get_messages_for_llm()
    system_content = messages[0]["content"]
    assert "user prefers dark mode" in system_content


def test_chat_mode_fallback_no_template(chat_config, mock_llm):
    """ChatMode falls back gracefully if template file is missing."""
    with patch("voice_agent.modes.render_template", side_effect=FileNotFoundError):
        handler = ChatMode(config=chat_config, llm=mock_llm)
        messages = handler.history.get_messages_for_llm()
        system_content = messages[0]["content"]
        assert "A test bot." in system_content


# ---------------------------------------------------------------------------
# AgentMode tests
# ---------------------------------------------------------------------------


def test_agent_mode_builds_system_prompt(agent_config, mock_llm):
    """AgentMode uses the agent_command_prompt template."""
    handler = AgentMode(
        config=agent_config, llm=mock_llm, commands="ls, cat, grep"
    )
    messages = handler.history.get_messages_for_llm()
    system_msgs = [m for m in messages if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert "TestBot" in system_msgs[0]["content"]
    assert "command mode" in system_msgs[0]["content"]


def test_agent_mode_includes_commands(agent_config, mock_llm):
    """AgentMode injects available commands into the prompt."""
    handler = AgentMode(
        config=agent_config, llm=mock_llm, commands="backup, restore, query"
    )
    messages = handler.history.get_messages_for_llm()
    system_content = messages[0]["content"]
    assert "backup, restore, query" in system_content


def test_agent_mode_name(agent_config, mock_llm):
    """AgentMode reports mode_name as 'agent'."""
    handler = AgentMode(config=agent_config, llm=mock_llm)
    assert handler.mode_name == "agent"


def test_agent_mode_handle_turn(agent_config, mock_llm):
    """AgentMode.handle_turn processes input and returns LLM output."""
    mock_llm.chat.return_value = "list-dir docs"
    handler = AgentMode(config=agent_config, llm=mock_llm)
    response = handler.handle_turn("List files in docs directory")

    assert response == "list-dir docs"
    messages = handler.history.get_messages_for_llm()
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant"]


def test_agent_mode_repr(agent_config, mock_llm):
    """AgentMode has a meaningful repr."""
    handler = AgentMode(config=agent_config, llm=mock_llm)
    assert "AgentMode" in repr(handler)


def test_agent_mode_with_context_files(agent_config, mock_llm, tmp_path):
    """AgentMode injects context file contents into its prompt."""
    ctx_file = tmp_path / "ref.txt"
    ctx_file.write_text("Database schema: users(id, name, email)")

    handler = AgentMode(
        config=agent_config, llm=mock_llm, context_files=[str(ctx_file)]
    )
    messages = handler.history.get_messages_for_llm()
    system_content = messages[0]["content"]
    assert "Database schema" in system_content


def test_agent_mode_fallback_no_template(agent_config, mock_llm):
    """AgentMode falls back gracefully if template file is missing."""
    with patch("voice_agent.modes.render_template", side_effect=FileNotFoundError):
        handler = AgentMode(
            config=agent_config, llm=mock_llm, commands="ls, cat"
        )
        messages = handler.history.get_messages_for_llm()
        system_content = messages[0]["content"]
        assert "TestBot" in system_content
        assert "command mode" in system_content
        assert "ls, cat" in system_content


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


def test_get_mode_handler_chat(chat_config, mock_llm):
    """get_mode_handler returns ChatMode for 'chat' config."""
    handler = get_mode_handler(chat_config, llm=mock_llm)
    assert isinstance(handler, ChatMode)
    assert handler.mode_name == "chat"


def test_get_mode_handler_agent(agent_config, mock_llm):
    """get_mode_handler returns AgentMode for 'agent' config."""
    handler = get_mode_handler(agent_config, llm=mock_llm, commands="test-cmd")
    assert isinstance(handler, AgentMode)
    assert handler.mode_name == "agent"


def test_get_mode_handler_case_insensitive(mock_llm, sp_path):
    """Mode name matching is case-insensitive."""
    config = _make_config("Chat", scratchpad_path=sp_path)
    handler = get_mode_handler(config, llm=mock_llm)
    assert isinstance(handler, ChatMode)


def test_get_mode_handler_unknown_mode(mock_llm, sp_path):
    """get_mode_handler raises ValueError for unknown mode."""
    config = _make_config("turbo", scratchpad_path=sp_path)
    with pytest.raises(ValueError, match="Unknown mode"):
        get_mode_handler(config, llm=mock_llm)


def test_get_mode_handler_default_is_chat(mock_llm, sp_path):
    """When mode is not set, defaults to chat."""
    config = ConfigNode({
        "assistant": {"name": "Bot", "persona": "Helper."},
        "llm": {"provider": "ollama", "model": "gemma3:4b"},
        "tts": {"provider": "kokoro", "voice": "af_heart"},
        "conversation": {"max_turns": 5},
        "scratchpad": {"file": sp_path},
    })
    handler = get_mode_handler(config, llm=mock_llm)
    assert isinstance(handler, ChatMode)


def test_both_modes_share_llm(mock_llm, sp_path):
    """Both modes can share the same LLM backend instance."""
    chat_cfg = _make_config("chat", scratchpad_path=sp_path)
    agent_cfg = _make_config("agent", scratchpad_path=sp_path)
    chat_handler = get_mode_handler(chat_cfg, llm=mock_llm)
    agent_handler = get_mode_handler(agent_cfg, llm=mock_llm)
    assert chat_handler.llm is mock_llm
    assert agent_handler.llm is mock_llm


def test_modes_have_independent_histories(mock_llm, sp_path):
    """Each mode handler maintains its own conversation history."""
    mock_llm.chat.side_effect = ["chat reply", "agent reply"]
    chat = ChatMode(config=_make_config("chat", scratchpad_path=sp_path), llm=mock_llm)
    agent = AgentMode(config=_make_config("agent", scratchpad_path=sp_path), llm=mock_llm)

    chat.handle_turn("Hi from chat")
    agent.handle_turn("List files")

    chat_msgs = chat.history.get_messages_for_llm()
    agent_msgs = agent.history.get_messages_for_llm()

    assert any("Hi from chat" in m["content"] for m in chat_msgs)
    assert not any("List files" in m["content"] for m in chat_msgs)
    assert any("List files" in m["content"] for m in agent_msgs)
    assert not any("Hi from chat" in m["content"] for m in agent_msgs)

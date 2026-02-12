"""Tests for the LLM abstraction layer (R-06)."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.llm import (
    AnthropicLLM,
    DeepSeekLLM,
    LLMBackend,
    OllamaLLM,
    get_llm_backend,
)


SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"},
]


# ---------------------------------------------------------------------------
# Base class tests
# ---------------------------------------------------------------------------


def test_llm_backend_is_abstract():
    """LLMBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMBackend(model="test")


# ---------------------------------------------------------------------------
# OllamaLLM tests
# ---------------------------------------------------------------------------


def test_ollama_repr():
    """OllamaLLM has a meaningful repr."""
    backend = OllamaLLM(model="gemma3:4b")
    assert "OllamaLLM" in repr(backend)
    assert "gemma3:4b" in repr(backend)


def test_ollama_default_model():
    """OllamaLLM defaults to gemma3:4b."""
    backend = OllamaLLM()
    assert backend.model == "gemma3:4b"


def test_ollama_chat():
    """OllamaLLM.chat() calls ollama.chat and returns content."""
    mock_ollama = MagicMock()
    mock_ollama.chat.return_value = {"message": {"content": "Hi there!"}}

    with patch.dict(sys.modules, {"ollama": mock_ollama}):
        backend = OllamaLLM(model="gemma3:4b")
        result = backend.chat(SAMPLE_MESSAGES)

    assert result == "Hi there!"
    mock_ollama.chat.assert_called_once_with(
        model="gemma3:4b",
        messages=SAMPLE_MESSAGES,
        options={},
    )


def test_ollama_chat_with_options():
    """OllamaLLM forwards options to ollama.chat."""
    mock_ollama = MagicMock()
    mock_ollama.chat.return_value = {"message": {"content": "response"}}

    with patch.dict(sys.modules, {"ollama": mock_ollama}):
        backend = OllamaLLM(model="gemma3:4b", options={"num_predict": 200})
        backend.chat(SAMPLE_MESSAGES)

    mock_ollama.chat.assert_called_once_with(
        model="gemma3:4b",
        messages=SAMPLE_MESSAGES,
        options={"num_predict": 200},
    )


# ---------------------------------------------------------------------------
# DeepSeekLLM tests
# ---------------------------------------------------------------------------


def test_deepseek_default_model():
    """DeepSeekLLM defaults to deepseek-chat."""
    backend = DeepSeekLLM()
    assert backend.model == "deepseek-chat"


def test_deepseek_repr():
    """DeepSeekLLM has a meaningful repr."""
    backend = DeepSeekLLM(model="deepseek-chat")
    assert "DeepSeekLLM" in repr(backend)


def test_deepseek_missing_api_key():
    """DeepSeekLLM raises when no API key is available."""
    mock_openai_mod = MagicMock()

    with patch.dict(sys.modules, {"openai": mock_openai_mod}):
        backend = DeepSeekLLM(model="deepseek-chat")
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="DeepSeek API key not found"):
                backend.chat(SAMPLE_MESSAGES)


def test_deepseek_chat():
    """DeepSeekLLM.chat() calls the OpenAI-compatible endpoint."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "DeepSeek response"
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )

    mock_openai_mod = MagicMock()
    mock_openai_mod.OpenAI.return_value = mock_client

    with patch.dict(sys.modules, {"openai": mock_openai_mod}):
        backend = DeepSeekLLM(model="deepseek-chat", api_key="test-key")
        result = backend.chat(SAMPLE_MESSAGES)

    assert result == "DeepSeek response"
    mock_openai_mod.OpenAI.assert_called_once_with(
        api_key="test-key", base_url="https://api.deepseek.com"
    )


# ---------------------------------------------------------------------------
# AnthropicLLM tests
# ---------------------------------------------------------------------------


def test_anthropic_default_model():
    """AnthropicLLM defaults to claude-sonnet-4-20250514."""
    backend = AnthropicLLM()
    assert backend.model == "claude-sonnet-4-20250514"


def test_anthropic_repr():
    """AnthropicLLM has a meaningful repr."""
    backend = AnthropicLLM(model="claude-sonnet-4-20250514")
    assert "AnthropicLLM" in repr(backend)


def test_anthropic_missing_api_key():
    """AnthropicLLM raises when no API key is available."""
    mock_anthropic_mod = MagicMock()

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
        backend = AnthropicLLM(model="claude-sonnet-4-20250514")
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="Anthropic API key not found"):
                backend.chat(SAMPLE_MESSAGES)


def test_anthropic_chat():
    """AnthropicLLM.chat() calls the Anthropic messages API."""
    mock_client = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = "Claude response"
    mock_client.messages.create.return_value = MagicMock(
        content=[mock_content_block]
    )

    mock_anthropic_mod = MagicMock()
    mock_anthropic_mod.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
        backend = AnthropicLLM(model="claude-sonnet-4-20250514", api_key="test-key")
        result = backend.chat(SAMPLE_MESSAGES)

    assert result == "Claude response"
    # Verify system message was extracted separately
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are helpful."
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]
    assert call_kwargs["max_tokens"] == 1024


def test_anthropic_chat_no_system():
    """AnthropicLLM.chat() works without a system message."""
    mock_client = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = "response"
    mock_client.messages.create.return_value = MagicMock(
        content=[mock_content_block]
    )

    mock_anthropic_mod = MagicMock()
    mock_anthropic_mod.Anthropic.return_value = mock_client

    messages = [{"role": "user", "content": "Hello"}]
    with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
        backend = AnthropicLLM(model="claude-sonnet-4-20250514", api_key="test-key")
        backend.chat(messages)

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" not in call_kwargs


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


def test_get_llm_backend_ollama():
    """get_llm_backend returns OllamaLLM for ollama provider."""
    config = ConfigNode({
        "llm": {"provider": "ollama", "model": "gemma3:4b"},
    })
    backend = get_llm_backend(config)
    assert isinstance(backend, OllamaLLM)
    assert backend.model == "gemma3:4b"


def test_get_llm_backend_deepseek():
    """get_llm_backend returns DeepSeekLLM for deepseek provider."""
    config = ConfigNode({
        "llm": {"provider": "deepseek", "model": "deepseek-chat"},
    })
    backend = get_llm_backend(config)
    assert isinstance(backend, DeepSeekLLM)
    assert backend.model == "deepseek-chat"


def test_get_llm_backend_anthropic():
    """get_llm_backend returns AnthropicLLM for anthropic provider."""
    config = ConfigNode({
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    })
    backend = get_llm_backend(config)
    assert isinstance(backend, AnthropicLLM)
    assert backend.model == "claude-sonnet-4-20250514"


def test_get_llm_backend_forwards_extra_keys():
    """get_llm_backend forwards extra config keys like api_key."""
    config = ConfigNode({
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "api_key": "sk-test"},
    })
    backend = get_llm_backend(config)
    assert isinstance(backend, AnthropicLLM)
    assert backend._api_key == "sk-test"


def test_get_llm_backend_unknown_provider():
    """get_llm_backend raises ValueError for unknown provider."""
    config = ConfigNode({
        "llm": {"provider": "unknown", "model": "x"},
    })
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_backend(config)


def test_get_llm_backend_case_insensitive():
    """Provider name matching is case-insensitive."""
    config = ConfigNode({
        "llm": {"provider": "Ollama", "model": "gemma3:4b"},
    })
    backend = get_llm_backend(config)
    assert isinstance(backend, OllamaLLM)

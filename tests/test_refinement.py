"""Tests for the LLM response refinement pipeline (R-16)."""

import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.refinement import is_refinement_enabled, refine_response


# ---------------------------------------------------------------------------
# Config helper tests
# ---------------------------------------------------------------------------


def test_refinement_disabled_by_default():
    """When no refinement section exists, refinement is disabled."""
    config = ConfigNode({"llm": {"provider": "ollama"}})
    assert is_refinement_enabled(config) is False


def test_refinement_disabled_explicitly():
    """Refinement can be explicitly disabled."""
    config = ConfigNode({"refinement": {"enabled": False}})
    assert is_refinement_enabled(config) is False


def test_refinement_enabled():
    """Refinement is enabled when config flag is True."""
    config = ConfigNode({"refinement": {"enabled": True}})
    assert is_refinement_enabled(config) is True


# ---------------------------------------------------------------------------
# refine_response tests
# ---------------------------------------------------------------------------


def test_refine_response_returns_original_when_disabled():
    """When refinement is disabled, the original response is returned."""
    config = ConfigNode({"refinement": {"enabled": False}})
    llm = MagicMock()
    result = refine_response("Hello world", llm, config=config)
    assert result == "Hello world"
    llm.chat.assert_not_called()


def test_refine_response_returns_original_when_empty():
    """Empty responses are returned as-is without calling the LLM."""
    llm = MagicMock()
    assert refine_response("", llm) == ""
    assert refine_response("   ", llm) == "   "
    llm.chat.assert_not_called()


def test_refine_response_calls_llm():
    """refine_response sends the response through the LLM for refinement."""
    llm = MagicMock()
    llm.chat.return_value = "So basically, the file has 10 lines."

    result = refine_response("The file contains 10 lines of text.", llm)

    assert result == "So basically, the file has 10 lines."
    llm.chat.assert_called_once()

    # Verify the source response is included in the prompt
    call_args = llm.chat.call_args[0][0]
    system_msg = call_args[0]["content"]
    assert "10 lines" in system_msg


def test_refine_response_with_config_enabled():
    """When refinement is enabled in config, response is refined."""
    config = ConfigNode({"refinement": {"enabled": True}})
    llm = MagicMock()
    llm.chat.return_value = "Refined output."

    result = refine_response("Raw output.", llm, config=config)

    assert result == "Refined output."
    llm.chat.assert_called_once()


def test_refine_response_without_config():
    """When no config is provided, refinement always runs."""
    llm = MagicMock()
    llm.chat.return_value = "Refined."

    result = refine_response("Raw.", llm, config=None)
    assert result == "Refined."
    llm.chat.assert_called_once()


def test_refine_response_fallback_without_template():
    """refine_response falls back to inline prompt if template is missing."""
    llm = MagicMock()
    llm.chat.return_value = "Fallback refined."

    with patch("voice_agent.refinement.render_template", side_effect=FileNotFoundError):
        result = refine_response("Original text.", llm)

    assert result == "Fallback refined."
    llm.chat.assert_called_once()

    # Verify fallback prompt contains the source response
    call_args = llm.chat.call_args[0][0]
    system_msg = call_args[0]["content"]
    assert "Original text." in system_msg


def test_refine_response_uses_refinement_template():
    """refine_response uses the refinement_prompt XML template."""
    llm = MagicMock()
    llm.chat.return_value = "Well, here is the result."

    # Don't mock render_template — let it use the real template file
    result = refine_response("The command returned exit code 0.", llm)

    assert result == "Well, here is the result."
    # Verify the system prompt was built from the template
    call_args = llm.chat.call_args[0][0]
    system_msg = call_args[0]["content"]
    assert "exit code 0" in system_msg
    assert "SUCCINCT" in system_msg or "succinct" in system_msg.lower()


def test_refine_response_preserves_multiline():
    """refine_response handles multi-line input correctly."""
    llm = MagicMock()
    llm.chat.return_value = "So you have three files there."

    input_text = "file1.txt\nfile2.txt\nfile3.txt"
    result = refine_response(input_text, llm)

    assert result == "So you have three files there."
    call_args = llm.chat.call_args[0][0]
    system_msg = call_args[0]["content"]
    assert "file1.txt" in system_msg

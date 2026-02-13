"""Tests for the config loader module (R-01)."""

import pytest
from pathlib import Path

from voice_agent.config import load_config, ConfigNode


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(tmp_path):
    """Write a minimal config YAML and return its path."""
    cfg = tmp_path / "config.yml"
    cfg.write_text(
        "assistant:\n"
        '  name: "TestBot"\n'
        '  persona: "A test bot."\n'
        "human:\n"
        '  name: "Tester"\n'
        "stt:\n"
        '  engine: "moonshine"\n'
        "llm:\n"
        '  provider: "ollama"\n'
        '  model: "gemma3:4b"\n'
        "tts:\n"
        '  provider: "kokoro"\n'
        '  voice: "af_heart"\n'
        'mode: "chat"\n'
        "conversation:\n"
        "  max_turns: 10\n"
        "scratchpad:\n"
        '  file: "scratchpad.md"\n'
    )
    return cfg


def test_load_config_dot_access(sample_config):
    """Config values are accessible via dot-path notation."""
    cfg = load_config(sample_config)
    assert cfg.assistant.name == "TestBot"
    assert cfg.llm.provider == "ollama"
    assert cfg.llm.model == "gemma3:4b"
    assert cfg.tts.provider == "kokoro"
    assert cfg.tts.voice == "af_heart"
    assert cfg.mode == "chat"
    assert cfg.conversation.max_turns == 10


def test_load_config_bracket_access(sample_config):
    """Config values are also accessible via bracket notation."""
    cfg = load_config(sample_config)
    assert cfg["assistant"]["name"] == "TestBot"
    assert cfg["llm"]["provider"] == "ollama"


def test_load_config_to_dict(sample_config):
    """to_dict() returns the raw dictionary."""
    cfg = load_config(sample_config)
    d = cfg.to_dict()
    assert isinstance(d, dict)
    assert d["assistant"]["name"] == "TestBot"


def test_load_config_missing_file():
    """FileNotFoundError is raised for a non-existent config."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.yml")


def test_load_default_config():
    """The default assistant_config.yml loads without error."""
    cfg = load_config()
    assert cfg.assistant.name == "Nova"
    assert cfg.llm.provider == "ollama"
    assert cfg.stt.engine == "moonshine"
    assert cfg.scratchpad.file == "scratchpad.md"


def test_config_node_repr():
    """ConfigNode has a meaningful repr."""
    node = ConfigNode({"key": "value"})
    assert "key" in repr(node)


def test_config_node_contains():
    """ConfigNode supports 'in' membership checks."""
    node = ConfigNode({"alpha": 1, "beta": {"nested": True}})
    assert "alpha" in node
    assert "beta" in node
    assert "gamma" not in node


def test_config_node_iter():
    """ConfigNode supports iteration over top-level keys."""
    node = ConfigNode({"x": 1, "y": 2, "z": 3})
    assert set(node) == {"x", "y", "z"}


def test_config_node_len():
    """ConfigNode supports len()."""
    assert len(ConfigNode({})) == 0
    assert len(ConfigNode({"a": 1})) == 1
    assert len(ConfigNode({"a": 1, "b": 2, "c": 3})) == 3


def test_config_node_contains_loaded(sample_config):
    """Membership check works on a loaded config."""
    cfg = load_config(sample_config)
    assert "llm" in cfg
    assert "tts" in cfg
    assert "nonexistent" not in cfg

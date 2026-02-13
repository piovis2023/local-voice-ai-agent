"""Tests for XML prompt template loader module (R-05)."""

import os
import tempfile

import pytest
from pathlib import Path

from voice_agent.prompt_loader import (
    load_template,
    render_template,
    list_templates,
)


@pytest.fixture
def prompts_dir(tmp_path):
    """Create a temporary prompts directory with a sample template."""
    tmpl = tmp_path / "greeting.xml"
    tmpl.write_text(
        '<prompt name="greeting">\n'
        "  <role>system</role>\n"
        "  <template>\n"
        "Hello, I am {assistant_name}. {persona}\n"
        "  </template>\n"
        "</prompt>\n"
    )
    return tmp_path


@pytest.fixture
def multi_prompts_dir(tmp_path):
    """Create a directory with multiple templates."""
    for name in ("alpha", "beta", "gamma"):
        (tmp_path / f"{name}.xml").write_text(
            f'<prompt name="{name}">\n'
            f"  <role>system</role>\n"
            f"  <template>{name} template</template>\n"
            f"</prompt>\n"
        )
    return tmp_path


def test_load_template(prompts_dir):
    """Template is loaded with name, role, and template text."""
    tmpl = load_template("greeting", prompts_dir)
    assert tmpl["name"] == "greeting"
    assert tmpl["role"] == "system"
    assert "{assistant_name}" in tmpl["template"]


def test_load_template_missing(tmp_path):
    """FileNotFoundError for non-existent template."""
    with pytest.raises(FileNotFoundError):
        load_template("nonexistent", tmp_path)


def test_render_template_interpolation(prompts_dir):
    """Variables are interpolated into the template."""
    result = render_template(
        "greeting",
        variables={"assistant_name": "Nova", "persona": "A helpful bot."},
        prompts_dir=prompts_dir,
    )
    assert "Nova" in result
    assert "A helpful bot." in result
    assert "{assistant_name}" not in result
    assert "{persona}" not in result


def test_render_template_missing_vars(prompts_dir):
    """Missing variables are replaced with empty strings."""
    result = render_template(
        "greeting",
        variables={"assistant_name": "Nova"},
        prompts_dir=prompts_dir,
    )
    assert "Nova" in result
    assert "{persona}" not in result


def test_render_template_no_vars(prompts_dir):
    """Rendering with no variables removes all placeholders."""
    result = render_template("greeting", prompts_dir=prompts_dir)
    assert "{assistant_name}" not in result
    assert "{persona}" not in result


def test_list_templates(multi_prompts_dir):
    """list_templates returns sorted template names."""
    names = list_templates(multi_prompts_dir)
    assert names == ["alpha", "beta", "gamma"]


def test_list_templates_empty(tmp_path):
    """Empty directory returns empty list."""
    assert list_templates(tmp_path) == []


def test_list_templates_nonexistent():
    """Non-existent directory returns empty list."""
    nonexistent = os.path.join(tempfile.gettempdir(), "no_such_dir_xyz")
    assert list_templates(nonexistent) == []


def test_default_prompts_directory():
    """Default prompts directory contains the shipped templates."""
    names = list_templates()
    assert "system_prompt" in names
    assert "agent_command_prompt" in names
    assert "concise_response_prompt" in names


def test_render_system_prompt_template():
    """The shipped system_prompt.xml renders with all variables."""
    result = render_template(
        "system_prompt",
        variables={
            "assistant_name": "TestBot",
            "persona": "Be helpful.",
            "scratchpad": "Remember: user likes cats.",
            "context": "File: notes.txt\nContent here.",
        },
    )
    assert "TestBot" in result
    assert "Be helpful." in result
    assert "user likes cats" in result
    assert "Content here." in result


def test_render_agent_command_prompt_template():
    """The shipped agent_command_prompt.xml renders correctly."""
    result = render_template(
        "agent_command_prompt",
        variables={
            "assistant_name": "Nova",
            "commands": "ls, cat, grep",
            "scratchpad": "",
            "context": "",
        },
    )
    assert "Nova" in result
    assert "ls, cat, grep" in result
    assert "command mode" in result


def test_render_concise_response_prompt_template():
    """The shipped concise_response_prompt.xml renders correctly."""
    result = render_template(
        "concise_response_prompt",
        variables={
            "assistant_name": "Nova",
            "scratchpad": "",
            "context": "",
        },
    )
    assert "Nova" in result
    assert "brief" in result

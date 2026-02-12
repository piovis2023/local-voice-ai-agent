"""Tests for context file loading module (R-04)."""

import pytest

from voice_agent.context import load_context_files, context_prompt_section


@pytest.fixture
def sample_files(tmp_path):
    """Create a few sample context files and return their paths."""
    f1 = tmp_path / "notes.txt"
    f1.write_text("Project uses Python 3.13 and FastRTC.")
    f2 = tmp_path / "guidelines.md"
    f2.write_text("# Guidelines\n\nAlways respond in English.")
    return [str(f1), str(f2)]


def test_load_context_files(sample_files):
    """Files are loaded with name and content."""
    results = load_context_files(sample_files)
    assert len(results) == 2
    assert results[0]["name"] == "notes.txt"
    assert "Python 3.13" in results[0]["content"]
    assert results[1]["name"] == "guidelines.md"
    assert "Always respond" in results[1]["content"]


def test_load_context_files_missing():
    """Missing files produce an error entry rather than raising."""
    results = load_context_files(["/nonexistent/file.txt"])
    assert len(results) == 1
    assert "Error: file not found" in results[0]["content"]


def test_load_context_files_empty_list():
    """Empty list returns empty results."""
    assert load_context_files([]) == []


def test_load_context_files_mixed(tmp_path):
    """Mix of valid and missing files returns all entries."""
    valid = tmp_path / "real.txt"
    valid.write_text("real content")
    results = load_context_files([str(valid), "/no/such/file.txt"])
    assert len(results) == 2
    assert results[0]["content"] == "real content"
    assert "Error" in results[1]["content"]


def test_context_prompt_section_empty():
    """Empty file list returns empty string."""
    assert context_prompt_section([]) == ""


def test_context_prompt_section_with_files(sample_files):
    """Section includes reference document markers and file contents."""
    section = context_prompt_section(sample_files)
    assert "Reference Documents" in section
    assert "End Reference Documents" in section
    assert "notes.txt" in section
    assert "Python 3.13" in section
    assert "guidelines.md" in section
    assert "Always respond" in section


def test_context_prompt_section_preserves_file_content(tmp_path):
    """Full file content is preserved in the prompt section."""
    f = tmp_path / "data.txt"
    content = "Line 1\nLine 2\nLine 3"
    f.write_text(content)
    section = context_prompt_section([str(f)])
    assert "Line 1\nLine 2\nLine 3" in section

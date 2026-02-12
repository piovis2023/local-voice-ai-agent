"""Tests for scratchpad persistent memory module (R-03)."""

import pytest
from voice_agent.scratchpad import (
    read_scratchpad,
    write_scratchpad,
    append_scratchpad,
    clear_scratchpad,
    scratchpad_prompt_section,
)


@pytest.fixture
def sp_path(tmp_path):
    """Return a temporary scratchpad file path."""
    return tmp_path / "scratchpad.md"


def test_read_nonexistent(sp_path):
    """Reading a non-existent scratchpad returns empty string."""
    assert read_scratchpad(sp_path) == ""


def test_write_and_read(sp_path):
    """Write then read returns the same content."""
    write_scratchpad("Hello world", sp_path)
    assert read_scratchpad(sp_path) == "Hello world"


def test_write_overwrites(sp_path):
    """Writing overwrites previous content."""
    write_scratchpad("first", sp_path)
    write_scratchpad("second", sp_path)
    assert read_scratchpad(sp_path) == "second"


def test_append(sp_path):
    """Append adds content after existing text."""
    write_scratchpad("line1", sp_path)
    append_scratchpad("line2", sp_path)
    content = read_scratchpad(sp_path)
    assert "line1" in content
    assert "line2" in content


def test_append_to_nonexistent(sp_path):
    """Append to non-existent file creates it."""
    append_scratchpad("first entry", sp_path)
    assert read_scratchpad(sp_path) == "first entry"


def test_clear(sp_path):
    """Clear removes the scratchpad file."""
    write_scratchpad("data", sp_path)
    clear_scratchpad(sp_path)
    assert not sp_path.exists()
    assert read_scratchpad(sp_path) == ""


def test_clear_nonexistent(sp_path):
    """Clear on non-existent file does not raise."""
    clear_scratchpad(sp_path)  # should not raise


def test_prompt_section_empty(sp_path):
    """Prompt section returns empty string when scratchpad is empty."""
    assert scratchpad_prompt_section(sp_path) == ""


def test_prompt_section_with_content(sp_path):
    """Prompt section wraps content with header/footer markers."""
    write_scratchpad("Remember: user prefers formal tone", sp_path)
    section = scratchpad_prompt_section(sp_path)
    assert "Scratchpad Memory" in section
    assert "user prefers formal tone" in section
    assert "End Scratchpad" in section


def test_prompt_section_whitespace_only(sp_path):
    """Whitespace-only scratchpad is treated as empty."""
    write_scratchpad("   \n  \n  ", sp_path)
    assert scratchpad_prompt_section(sp_path) == ""

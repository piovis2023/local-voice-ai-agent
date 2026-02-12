"""Persistent scratchpad memory (R-03).

Read/write a scratchpad.md file that persists across sessions.
The LLM prompt is augmented with scratchpad contents when non-empty.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_SCRATCHPAD_PATH = Path(__file__).resolve().parent.parent / "scratchpad.md"


def read_scratchpad(path: Path | str | None = None) -> str:
    """Read the scratchpad file and return its contents.

    Returns an empty string if the file does not exist.
    """
    sp_path = Path(path) if path else DEFAULT_SCRATCHPAD_PATH
    if not sp_path.exists():
        return ""
    return sp_path.read_text(encoding="utf-8")


def write_scratchpad(content: str, path: Path | str | None = None) -> None:
    """Write content to the scratchpad file (overwrite)."""
    sp_path = Path(path) if path else DEFAULT_SCRATCHPAD_PATH
    sp_path.write_text(content, encoding="utf-8")


def append_scratchpad(content: str, path: Path | str | None = None) -> None:
    """Append content to the scratchpad file."""
    existing = read_scratchpad(path)
    separator = "\n" if existing and not existing.endswith("\n") else ""
    write_scratchpad(existing + separator + content, path)


def clear_scratchpad(path: Path | str | None = None) -> None:
    """Remove the scratchpad file if it exists."""
    sp_path = Path(path) if path else DEFAULT_SCRATCHPAD_PATH
    if sp_path.exists():
        sp_path.unlink()


def scratchpad_prompt_section(path: Path | str | None = None) -> str:
    """Return a prompt section with scratchpad contents, or empty string if empty."""
    contents = read_scratchpad(path)
    if not contents.strip():
        return ""
    return (
        "\n\n--- Scratchpad Memory ---\n"
        "The following notes were saved from previous sessions:\n\n"
        f"{contents}\n"
        "--- End Scratchpad ---\n"
    )

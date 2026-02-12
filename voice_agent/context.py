"""Context file loading for LLM prompt injection (R-04).

Reads user-specified files at startup and formats their contents
for injection into the LLM system prompt as reference material.
"""

from __future__ import annotations

from pathlib import Path


def load_context_files(file_paths: list[str]) -> list[dict[str, str]]:
    """Read the given files and return a list of {name, content} dicts.

    Parameters
    ----------
    file_paths:
        List of file path strings to read.

    Returns
    -------
    list[dict[str, str]]
        Each entry has ``name`` (the file name) and ``content`` (file text).
        Files that cannot be read are skipped with a warning entry.
    """
    results: list[dict[str, str]] = []
    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            results.append({"name": fp, "content": f"[Error: file not found: {fp}]"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
            results.append({"name": path.name, "content": text})
        except (OSError, UnicodeDecodeError) as exc:
            results.append({"name": fp, "content": f"[Error reading file: {exc}]"})
    return results


def context_prompt_section(file_paths: list[str]) -> str:
    """Build a prompt section containing context file contents.

    Returns an empty string if *file_paths* is empty.
    """
    if not file_paths:
        return ""

    loaded = load_context_files(file_paths)
    if not loaded:
        return ""

    parts: list[str] = ["\n\n--- Reference Documents ---"]
    for doc in loaded:
        parts.append(f"\n### {doc['name']}\n{doc['content']}")
    parts.append("\n--- End Reference Documents ---\n")
    return "\n".join(parts)

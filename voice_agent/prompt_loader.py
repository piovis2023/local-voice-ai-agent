"""XML prompt template loader (R-05).

Reads XML template files from the prompts/ directory and interpolates
variables such as assistant name, commands, scratchpad, context, and user input.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_template(name: str, prompts_dir: Path | str | None = None) -> dict[str, str]:
    """Load a single XML prompt template by name.

    Parameters
    ----------
    name:
        Template name (without ``.xml`` extension), e.g. ``"system_prompt"``.
    prompts_dir:
        Directory containing XML templates.  Defaults to the project-level
        ``prompts/`` directory.

    Returns
    -------
    dict[str, str]
        Dictionary with ``name``, ``role``, and ``template`` keys.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist.
    """
    directory = Path(prompts_dir) if prompts_dir else DEFAULT_PROMPTS_DIR
    template_path = directory / f"{name}.xml"
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    tree = ET.parse(template_path)
    root = tree.getroot()

    return {
        "name": root.attrib.get("name", name),
        "role": _get_text(root, "role", "system"),
        "template": _get_text(root, "template", ""),
    }


def render_template(
    name: str,
    variables: dict[str, Any] | None = None,
    prompts_dir: Path | str | None = None,
) -> str:
    """Load a template and interpolate variables into it.

    Parameters
    ----------
    name:
        Template name (without ``.xml`` extension).
    variables:
        Mapping of placeholder names to their values.  Missing variables
        are replaced with empty strings.
    prompts_dir:
        Directory containing XML templates.

    Returns
    -------
    str
        The rendered prompt string with variables interpolated and
        leading/trailing whitespace stripped.
    """
    tmpl = load_template(name, prompts_dir)
    raw = tmpl["template"]
    vars_ = variables or {}
    # Replace {key} placeholders; missing keys become empty strings
    for key, value in vars_.items():
        raw = raw.replace(f"{{{key}}}", str(value))
    # Clean up any remaining unreplaced placeholders
    import re
    raw = re.sub(r"\{(\w+)\}", "", raw)
    # Collapse runs of 3+ newlines into 2
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def list_templates(prompts_dir: Path | str | None = None) -> list[str]:
    """Return the names of all available prompt templates.

    Returns
    -------
    list[str]
        Sorted list of template names (without the ``.xml`` extension).
    """
    directory = Path(prompts_dir) if prompts_dir else DEFAULT_PROMPTS_DIR
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.xml"))


def _get_text(root: ET.Element, tag: str, default: str) -> str:
    """Extract text from a child element, or return *default*."""
    elem = root.find(tag)
    if elem is None or elem.text is None:
        return default
    return elem.text

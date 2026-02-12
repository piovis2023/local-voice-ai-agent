"""Extensible command surface via Typer file discovery (R-12).

Accepts a path to a Python file containing Typer commands, parses it to
extract command signatures and docstrings, and produces a catalog string
suitable for injection into the LLM prompt.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandInfo:
    """Metadata about a single discovered Typer command."""

    name: str
    params: list[str]
    docstring: str


def discover_commands(typer_file: str | Path) -> list[CommandInfo]:
    """Parse a Typer command file and extract command metadata.

    The function performs static analysis (AST parsing) — it does **not**
    import or execute the file.

    It looks for:
    - Functions decorated with ``@app.command()``
    - Their parameter lists (names and type annotations)
    - Their docstrings

    Parameters
    ----------
    typer_file:
        Path to a Python file containing Typer commands.

    Returns
    -------
    list[CommandInfo]
        List of discovered commands with name, params, and docstring.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    path = Path(typer_file)
    if not path.exists():
        raise FileNotFoundError(f"Typer command file not found: {path}")

    source = path.read_text()
    tree = ast.parse(source, filename=str(path))

    commands: list[CommandInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not _has_command_decorator(node):
            continue

        name = node.name.replace("_", "-")
        params = _extract_params(node)
        docstring = ast.get_docstring(node) or ""

        commands.append(CommandInfo(name=name, params=params, docstring=docstring))

    return commands


def build_command_catalog(typer_file: str | Path) -> str:
    """Build a human-readable command catalog string from a Typer file.

    This string is designed to be injected into the LLM prompt so the
    model can discover available commands.

    Parameters
    ----------
    typer_file:
        Path to the Typer command file.

    Returns
    -------
    str
        Formatted multi-line string listing commands, their signatures,
        and descriptions.
    """
    commands = discover_commands(typer_file)
    if not commands:
        return "(No commands discovered.)"

    lines: list[str] = []
    for cmd in commands:
        sig = f"  {cmd.name}"
        if cmd.params:
            sig += f" {' '.join(cmd.params)}"
        lines.append(sig)
        if cmd.docstring:
            first_line = cmd.docstring.strip().split("\n")[0]
            lines.append(f"    {first_line}")
    return "\n".join(lines)


def build_catalog_from_files(typer_files: list[str | Path]) -> str:
    """Build a combined catalog from multiple Typer command files.

    Parameters
    ----------
    typer_files:
        List of paths to Typer command files.

    Returns
    -------
    str
        Combined catalog string.
    """
    sections: list[str] = []
    for f in typer_files:
        path = Path(f)
        catalog = build_command_catalog(path)
        sections.append(f"[{path.stem}]\n{catalog}")
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _has_command_decorator(node: ast.FunctionDef) -> bool:
    """Check if a function has an ``@app.command()`` decorator."""
    for decorator in node.decorator_list:
        # @app.command() — Call form
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "command"
                and isinstance(func.value, ast.Name)
            ):
                return True
        # @app.command — Attribute form (no parentheses)
        if isinstance(decorator, ast.Attribute):
            if decorator.attr == "command" and isinstance(decorator.value, ast.Name):
                return True
    return False


def _extract_params(node: ast.FunctionDef) -> list[str]:
    """Extract parameter names and annotations from a function definition."""
    params: list[str] = []
    for arg in node.args.args:
        name = arg.arg
        if arg.annotation:
            annotation = _annotation_to_str(arg.annotation)
            params.append(f"{name}:{annotation}")
        else:
            params.append(name)
    return params


def _annotation_to_str(node: ast.expr) -> str:
    """Convert an AST annotation node to a readable string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        base = _annotation_to_str(node.value)
        slice_str = _annotation_to_str(node.slice)
        return f"{base}[{slice_str}]"
    return ast.dump(node)

"""Voice-to-CLI command generation and validation (R-10).

In agent mode the LLM receives the user transcript plus available Typer
commands and outputs a CLI command string.  This module parses, validates,
and executes that output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from voice_agent.execute import ExecutionResult, execute_chain


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsing LLM output into a CLI command."""

    raw: str
    command: str
    is_valid: bool
    rejection_reason: str = ""


# Patterns that indicate the LLM declined to produce a command.
_REFUSAL_PATTERNS = [
    r"(?i)i(?:'m| am) (?:sorry|unable|not able)",
    r"(?i)(?:doesn't|does not|don't|do not) match",
    r"(?i)no (?:matching|available|valid) command",
    r"(?i)cannot (?:find|identify|determine)",
    r"(?i)i can(?:'t|not)",
]


def parse_llm_output(raw: str) -> ParsedCommand:
    """Parse raw LLM output into a structured command.

    The function strips markdown fencing, leading/trailing whitespace,
    and detects LLM refusal messages.

    Parameters
    ----------
    raw:
        The raw text returned by the LLM in agent mode.

    Returns
    -------
    ParsedCommand
        Parsed result with validity flag.
    """
    cleaned = _strip_fences(raw).strip()

    if not cleaned:
        return ParsedCommand(
            raw=raw, command="", is_valid=False, rejection_reason="Empty command output."
        )

    # Check if the LLM refused to produce a command
    for pattern in _REFUSAL_PATTERNS:
        if re.search(pattern, cleaned):
            return ParsedCommand(
                raw=raw,
                command="",
                is_valid=False,
                rejection_reason=cleaned,
            )

    return ParsedCommand(raw=raw, command=cleaned, is_valid=True)


def validate_against_catalog(
    parsed: ParsedCommand,
    known_commands: list[str],
) -> ParsedCommand:
    """Validate that the first token of each chained command is in the catalog.

    Parameters
    ----------
    parsed:
        A previously parsed command.
    known_commands:
        List of known command names (e.g. ``["ls-dir", "backup-file"]``).

    Returns
    -------
    ParsedCommand
        The same command if valid, or a new one marked invalid if the
        command is not recognised.
    """
    if not parsed.is_valid:
        return parsed

    if not known_commands:
        # No catalog loaded — skip validation
        return parsed

    segments = [s.strip() for s in parsed.command.split("&&") if s.strip()]
    for segment in segments:
        first_token = segment.split()[0] if segment.split() else ""
        if first_token not in known_commands:
            return ParsedCommand(
                raw=parsed.raw,
                command=parsed.command,
                is_valid=False,
                rejection_reason=f"Unknown command: {first_token!r}. "
                f"Available: {', '.join(sorted(known_commands))}",
            )

    return parsed


def execute_parsed_command(
    parsed: ParsedCommand,
    timeout: int = 30,
    cwd: str | None = None,
) -> list[ExecutionResult]:
    """Execute a validated parsed command (or chain).

    Parameters
    ----------
    parsed:
        A parsed command that should be valid.
    timeout:
        Per-command timeout in seconds.
    cwd:
        Working directory for subprocesses.

    Returns
    -------
    list[ExecutionResult]
        Results of executing each command in the chain.

    Raises
    ------
    ValueError
        If the parsed command is not valid.
    """
    if not parsed.is_valid:
        raise ValueError(f"Cannot execute invalid command: {parsed.rejection_reason}")

    return execute_chain(parsed.command, timeout=timeout, cwd=cwd)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```...```) from LLM output."""
    # Remove fenced code blocks — keep only the content inside
    pattern = r"```(?:\w*\n?)?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

"""Subprocess execution module (R-09).

Runs shell commands via ``subprocess.run()``, captures stdout/stderr, and
returns structured results.  Supports configurable timeouts and command
chaining with ``&&`` (R-11).
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass

# Shell metacharacters that could enable injection when using shell=True.
# Commands containing these are rejected before execution.
_DANGEROUS_PATTERN = re.compile(r"[;|`]|\$\(")


@dataclass(frozen=True)
class ExecutionResult:
    """Structured result of a subprocess execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    command: str


def execute_command(
    command: str,
    timeout: int = 30,
    cwd: str | None = None,
) -> ExecutionResult:
    """Run a single shell command and return the structured result.

    Parameters
    ----------
    command:
        The shell command string to execute.
    timeout:
        Maximum seconds to wait before killing the process.
    cwd:
        Working directory for the subprocess.  Defaults to the current
        working directory.

    Returns
    -------
    ExecutionResult
        Structured result with success flag, stdout, stderr, return_code,
        and the original command string.
    """
    # Reject commands containing shell metacharacters to prevent injection
    if _DANGEROUS_PATTERN.search(command):
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=(
                "Command rejected: contains disallowed shell metacharacters "
                "(;, |, `, $()."
            ),
            return_code=-1,
            command=command,
        )

    try:
        argv = shlex.split(command, posix=(os.name != "nt"))
    except ValueError as exc:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Failed to parse command: {exc}",
            return_code=-1,
            command=command,
        )

    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            command=command,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds.",
            return_code=-1,
            command=command,
        )
    except FileNotFoundError:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Command not found: {argv[0]!r}",
            return_code=127,
            command=command,
        )


def execute_chain(
    command_string: str,
    timeout: int = 30,
    cwd: str | None = None,
) -> list[ExecutionResult]:
    """Execute ``&&``-separated commands sequentially (R-11).

    Halts on the first failure and returns all results collected so far.

    Parameters
    ----------
    command_string:
        One or more commands separated by ``&&``.
    timeout:
        Per-command timeout in seconds.
    cwd:
        Working directory for all sub-processes.

    Returns
    -------
    list[ExecutionResult]
        A list of results, one per command executed.  If any command fails,
        subsequent commands are *not* executed.
    """
    commands = [cmd.strip() for cmd in command_string.split("&&") if cmd.strip()]
    results: list[ExecutionResult] = []

    for cmd in commands:
        result = execute_command(cmd, timeout=timeout, cwd=cwd)
        results.append(result)
        if not result.success:
            break

    return results

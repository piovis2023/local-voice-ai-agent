"""Tests for the subprocess execution module (R-09) and command chaining (R-11)."""

import sys

import pytest

from voice_agent.execute import ExecutionResult, execute_chain, execute_command

# Cross-platform command helpers using sys.executable so tests work on
# both Unix and Windows (R-25).
# NOTE: Commands must NOT contain shell metacharacters (;|`$()) because
# execute_command rejects them. Use __import__ or single-expression
# Python to avoid semicolons.
_PY = sys.executable
_ECHO_HELLO = f'{_PY} -c "print(\'hello\')"'
_ECHO_HELLO_WORLD = f'{_PY} -c "print(\'hello world\')"'
_ECHO_HI = f'{_PY} -c "print(\'hi\')"'
_ECHO_ONE = f'{_PY} -c "print(\'one\')"'
_ECHO_FIRST = f'{_PY} -c "print(\'first\')"'
_ECHO_SECOND = f'{_PY} -c "print(\'second\')"'
_ECHO_A = f'{_PY} -c "print(\'a\')"'
_ECHO_B = f'{_PY} -c "print(\'b\')"'
_ECHO_C = f'{_PY} -c "print(\'c\')"'
_ECHO_OK = f'{_PY} -c "print(\'ok\')"'
_ECHO_FAST = f'{_PY} -c "print(\'fast\')"'
_ECHO_NEVER = f'{_PY} -c "print(\'never\')"'
_EXIT_FAIL = f'{_PY} -c "raise SystemExit(1)"'
_SLEEP_LONG = f'{_PY} -c "__import__(\'time\').sleep(60)"'
_PRINT_CWD = f'{_PY} -c "print(__import__(\'os\').getcwd())"'
_STDERR_CMD = f'{_PY} -c "__import__(\'sys\').exit(__import__(\'sys\').stderr.write(\'error\\n\'))"'


# ---------------------------------------------------------------------------
# execute_command tests
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    """Tests for execute_command."""

    def test_successful_command(self):
        """A simple command returns success."""
        result = execute_command(_ECHO_HELLO)
        assert result.success is True
        assert result.return_code == 0
        assert "hello" in result.stdout
        assert result.stderr == ""

    def test_failed_command(self):
        """A command that exits non-zero returns failure."""
        result = execute_command(_EXIT_FAIL)
        assert result.success is False
        assert result.return_code != 0

    def test_stderr_captured(self):
        """stderr is captured separately from stdout."""
        result = execute_command(_STDERR_CMD)
        assert result.success is False
        assert result.stderr != ""

    def test_command_with_output(self):
        """Commands that produce output are captured."""
        result = execute_command(_ECHO_HELLO_WORLD)
        assert result.success is True
        assert "hello" in result.stdout
        assert "world" in result.stdout

    def test_shell_metacharacters_rejected(self):
        """Commands with shell metacharacters are rejected."""
        result = execute_command("echo foo; echo bar")
        assert result.success is False
        assert "rejected" in result.stderr.lower()

        result = execute_command("echo foo | cat")
        assert result.success is False
        assert "rejected" in result.stderr.lower()

    def test_timeout_kills_command(self):
        """A command exceeding the timeout is killed gracefully."""
        result = execute_command(_SLEEP_LONG, timeout=1)
        assert result.success is False
        assert result.return_code == -1
        assert "timed out" in result.stderr.lower()

    def test_custom_cwd(self, tmp_path):
        """Commands run in the specified working directory."""
        result = execute_command(_PRINT_CWD, cwd=str(tmp_path))
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_nonexistent_command(self):
        """An unknown command returns failure."""
        result = execute_command("nonexistent_cmd_xyz_12345")
        assert result.success is False
        assert result.return_code != 0

    def test_result_is_frozen(self):
        """ExecutionResult is immutable."""
        result = execute_command(_ECHO_HI)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# execute_chain tests (R-11)
# ---------------------------------------------------------------------------


class TestExecuteChain:
    """Tests for execute_chain (command chaining)."""

    def test_single_command(self):
        """A chain with one command returns one result."""
        results = execute_chain(_ECHO_ONE)
        assert len(results) == 1
        assert results[0].success is True
        assert "one" in results[0].stdout

    def test_two_successful_commands(self):
        """Two successful commands both execute."""
        results = execute_chain(f"{_ECHO_FIRST} && {_ECHO_SECOND}")
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True
        assert "first" in results[0].stdout
        assert "second" in results[1].stdout

    def test_halt_on_first_failure(self):
        """Chain stops after the first failing command."""
        results = execute_chain(f"{_ECHO_OK} && {_EXIT_FAIL} && {_ECHO_NEVER}")
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    def test_empty_string(self):
        """An empty command string returns no results."""
        results = execute_chain("")
        assert results == []

    def test_whitespace_only(self):
        """Whitespace-only string returns no results."""
        results = execute_chain("   &&   &&   ")
        assert results == []

    def test_chain_with_timeout(self):
        """Per-command timeout applies to each segment."""
        results = execute_chain(f"{_ECHO_FAST} && {_SLEEP_LONG}", timeout=1)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "timed out" in results[1].stderr.lower()

    def test_chain_with_cwd(self, tmp_path):
        """cwd is passed through to all commands in the chain."""
        results = execute_chain(
            f"{_PRINT_CWD} && {_PRINT_CWD}", cwd=str(tmp_path)
        )
        assert len(results) == 2
        for r in results:
            assert str(tmp_path) in r.stdout

    def test_three_successful_commands(self):
        """Three chained commands all succeed."""
        results = execute_chain(f"{_ECHO_A} && {_ECHO_B} && {_ECHO_C}")
        assert len(results) == 3
        assert all(r.success for r in results)

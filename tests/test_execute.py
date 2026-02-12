"""Tests for the subprocess execution module (R-09) and command chaining (R-11)."""

import pytest

from voice_agent.execute import ExecutionResult, execute_chain, execute_command


# ---------------------------------------------------------------------------
# execute_command tests
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    """Tests for execute_command."""

    def test_successful_command(self):
        """A simple echo command returns success."""
        result = execute_command("echo hello")
        assert result.success is True
        assert result.return_code == 0
        assert "hello" in result.stdout
        assert result.stderr == ""
        assert result.command == "echo hello"

    def test_failed_command(self):
        """A command that exits non-zero returns failure."""
        result = execute_command("false")
        assert result.success is False
        assert result.return_code != 0

    def test_stderr_captured(self):
        """stderr is captured separately from stdout."""
        # A command that writes to stderr (listing a non-existent path)
        result = execute_command("ls /nonexistent_path_xyz_99999")
        assert result.success is False
        assert result.stderr != ""

    def test_command_with_output(self):
        """Commands that produce output are captured."""
        result = execute_command("echo hello world")
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
        result = execute_command("sleep 60", timeout=1)
        assert result.success is False
        assert result.return_code == -1
        assert "timed out" in result.stderr.lower()

    def test_custom_cwd(self, tmp_path):
        """Commands run in the specified working directory."""
        result = execute_command("pwd", cwd=str(tmp_path))
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_nonexistent_command(self):
        """An unknown command returns failure."""
        result = execute_command("nonexistent_cmd_xyz_12345")
        assert result.success is False
        assert result.return_code != 0

    def test_result_is_frozen(self):
        """ExecutionResult is immutable."""
        result = execute_command("echo hi")
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# execute_chain tests (R-11)
# ---------------------------------------------------------------------------


class TestExecuteChain:
    """Tests for execute_chain (command chaining)."""

    def test_single_command(self):
        """A chain with one command returns one result."""
        results = execute_chain("echo one")
        assert len(results) == 1
        assert results[0].success is True
        assert "one" in results[0].stdout

    def test_two_successful_commands(self):
        """Two successful commands both execute."""
        results = execute_chain("echo first && echo second")
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True
        assert "first" in results[0].stdout
        assert "second" in results[1].stdout

    def test_halt_on_first_failure(self):
        """Chain stops after the first failing command."""
        results = execute_chain("echo ok && false && echo never")
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
        results = execute_chain("echo fast && sleep 60", timeout=1)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "timed out" in results[1].stderr.lower()

    def test_chain_with_cwd(self, tmp_path):
        """cwd is passed through to all commands in the chain."""
        results = execute_chain("pwd && pwd", cwd=str(tmp_path))
        assert len(results) == 2
        for r in results:
            assert str(tmp_path) in r.stdout

    def test_three_successful_commands(self):
        """Three chained commands all succeed."""
        results = execute_chain("echo a && echo b && echo c")
        assert len(results) == 3
        assert all(r.success for r in results)

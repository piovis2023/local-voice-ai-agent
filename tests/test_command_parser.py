"""Tests for the voice-to-CLI command parser (R-10)."""

import pytest

from voice_agent.command_parser import (
    ParsedCommand,
    execute_parsed_command,
    parse_llm_output,
    validate_against_catalog,
)


# ---------------------------------------------------------------------------
# parse_llm_output tests
# ---------------------------------------------------------------------------


class TestParseLlmOutput:
    """Tests for parse_llm_output."""

    def test_plain_command(self):
        """A simple command string is parsed as valid."""
        result = parse_llm_output("ls-dir /tmp")
        assert result.is_valid is True
        assert result.command == "ls-dir /tmp"

    def test_strips_whitespace(self):
        """Leading and trailing whitespace is removed."""
        result = parse_llm_output("  backup-file foo.txt  \n")
        assert result.is_valid is True
        assert result.command == "backup-file foo.txt"

    def test_strips_markdown_fences(self):
        """Markdown code fences are removed."""
        result = parse_llm_output("```bash\nls-dir /home\n```")
        assert result.is_valid is True
        assert result.command == "ls-dir /home"

    def test_strips_generic_fences(self):
        """Generic fences (no language) are handled."""
        result = parse_llm_output("```\nquery-db SELECT 1\n```")
        assert result.is_valid is True
        assert result.command == "query-db SELECT 1"

    def test_empty_output(self):
        """Empty LLM output is rejected."""
        result = parse_llm_output("")
        assert result.is_valid is False
        assert "empty" in result.rejection_reason.lower()

    def test_whitespace_only_output(self):
        """Whitespace-only output is rejected."""
        result = parse_llm_output("   \n  ")
        assert result.is_valid is False

    def test_refusal_sorry(self):
        """LLM refusal with 'sorry' is detected."""
        result = parse_llm_output("I'm sorry, I cannot find a matching command.")
        assert result.is_valid is False
        assert result.rejection_reason != ""

    def test_refusal_no_matching_command(self):
        """LLM refusal about no matching commands is detected."""
        result = parse_llm_output("No matching command for that request.")
        assert result.is_valid is False

    def test_refusal_unable(self):
        """LLM refusal with 'unable' is detected."""
        result = parse_llm_output("I am unable to determine the right command.")
        assert result.is_valid is False

    def test_chained_command(self):
        """A &&-chained command string is valid."""
        result = parse_llm_output("ls-dir /tmp && backup-file foo.txt")
        assert result.is_valid is True
        assert "&&" in result.command

    def test_preserves_raw(self):
        """The raw LLM output is preserved."""
        raw = "```\nmy-cmd\n```"
        result = parse_llm_output(raw)
        assert result.raw == raw


# ---------------------------------------------------------------------------
# validate_against_catalog tests
# ---------------------------------------------------------------------------


class TestValidateAgainstCatalog:
    """Tests for validate_against_catalog."""

    def test_valid_command_in_catalog(self):
        """A command whose first token is in the catalog passes."""
        parsed = ParsedCommand(raw="ls-dir /home", command="ls-dir /home", is_valid=True)
        result = validate_against_catalog(parsed, ["ls-dir", "backup-file"])
        assert result.is_valid is True

    def test_unknown_command(self):
        """A command not in the catalog is rejected."""
        parsed = ParsedCommand(raw="rm -rf /", command="rm -rf /", is_valid=True)
        result = validate_against_catalog(parsed, ["ls-dir", "backup-file"])
        assert result.is_valid is False
        assert "Unknown command" in result.rejection_reason

    def test_empty_catalog_skips_validation(self):
        """With an empty catalog, validation is skipped."""
        parsed = ParsedCommand(raw="anything", command="anything", is_valid=True)
        result = validate_against_catalog(parsed, [])
        assert result.is_valid is True

    def test_already_invalid_passed_through(self):
        """An already-invalid command stays invalid."""
        parsed = ParsedCommand(
            raw="", command="", is_valid=False, rejection_reason="Empty."
        )
        result = validate_against_catalog(parsed, ["ls-dir"])
        assert result.is_valid is False

    def test_chain_all_valid(self):
        """A chain where all commands are in the catalog passes."""
        parsed = ParsedCommand(
            raw="ls-dir /tmp && backup-file x",
            command="ls-dir /tmp && backup-file x",
            is_valid=True,
        )
        result = validate_against_catalog(parsed, ["ls-dir", "backup-file"])
        assert result.is_valid is True

    def test_chain_one_invalid(self):
        """A chain with one unknown command is rejected."""
        parsed = ParsedCommand(
            raw="ls-dir /tmp && rm -rf /",
            command="ls-dir /tmp && rm -rf /",
            is_valid=True,
        )
        result = validate_against_catalog(parsed, ["ls-dir", "backup-file"])
        assert result.is_valid is False
        assert "rm" in result.rejection_reason


# ---------------------------------------------------------------------------
# execute_parsed_command tests
# ---------------------------------------------------------------------------


class TestExecuteParsedCommand:
    """Tests for execute_parsed_command."""

    def test_execute_valid_command(self):
        """A valid parsed command executes successfully."""
        parsed = ParsedCommand(
            raw="echo hello", command="echo hello", is_valid=True
        )
        results = execute_parsed_command(parsed)
        assert len(results) == 1
        assert results[0].success is True
        assert "hello" in results[0].stdout

    def test_execute_chain(self):
        """A valid chained command executes all segments."""
        parsed = ParsedCommand(
            raw="echo a && echo b",
            command="echo a && echo b",
            is_valid=True,
        )
        results = execute_parsed_command(parsed)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_execute_invalid_raises(self):
        """Executing an invalid command raises ValueError."""
        parsed = ParsedCommand(
            raw="bad", command="", is_valid=False, rejection_reason="Invalid."
        )
        with pytest.raises(ValueError, match="Cannot execute invalid command"):
            execute_parsed_command(parsed)

    def test_execute_with_timeout(self):
        """Timeout is passed through to execution."""
        parsed = ParsedCommand(
            raw="sleep 60", command="sleep 60", is_valid=True
        )
        results = execute_parsed_command(parsed, timeout=1)
        assert len(results) == 1
        assert results[0].success is False

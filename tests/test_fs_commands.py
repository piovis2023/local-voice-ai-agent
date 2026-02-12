"""Tests for file system operations (R-13)."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from commands.fs_commands import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# list_dir tests
# ---------------------------------------------------------------------------


class TestListDir:
    """Tests for the list-dir command."""

    def test_lists_files(self, tmp_path: Path):
        """Lists files in the given directory."""
        (tmp_path / "alpha.txt").write_text("a")
        (tmp_path / "beta.txt").write_text("b")
        result = runner.invoke(app, ["list-dir", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "alpha.txt" in result.output
        assert "beta.txt" in result.output

    def test_lists_directories_with_slash(self, tmp_path: Path):
        """Directories are shown with a trailing slash."""
        (tmp_path / "subdir").mkdir()
        result = runner.invoke(app, ["list-dir", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "subdir/" in result.output

    def test_sorted_output(self, tmp_path: Path):
        """Entries are sorted alphabetically."""
        (tmp_path / "cherry.txt").write_text("")
        (tmp_path / "apple.txt").write_text("")
        (tmp_path / "banana.txt").write_text("")
        result = runner.invoke(app, ["list-dir", "--path", str(tmp_path)])
        lines = result.output.strip().splitlines()
        assert lines == ["apple.txt", "banana.txt", "cherry.txt"]

    def test_nonexistent_path(self):
        """Non-existent path returns error."""
        result = runner.invoke(app, ["list-dir", "--path", "/nonexistent/path/xyz"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_not_a_directory(self, tmp_path: Path):
        """Passing a file instead of directory returns error."""
        f = tmp_path / "file.txt"
        f.write_text("hello")
        result = runner.invoke(app, ["list-dir", "--path", str(f)])
        assert result.exit_code != 0
        assert "not a directory" in result.output

    def test_default_path(self):
        """Default path '.' lists current directory without error."""
        result = runner.invoke(app, ["list-dir"])
        assert result.exit_code == 0

    def test_empty_directory(self, tmp_path: Path):
        """An empty directory produces no output lines."""
        result = runner.invoke(app, ["list-dir", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert result.output.strip() == ""


# ---------------------------------------------------------------------------
# compare_files tests
# ---------------------------------------------------------------------------


class TestCompareFiles:
    """Tests for the compare-files command."""

    def test_identical_files(self, tmp_path: Path):
        """Identical files produce 'Files are identical.' message."""
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("hello\nworld\n")
        b.write_text("hello\nworld\n")
        result = runner.invoke(app, ["compare-files", str(a), str(b)])
        assert result.exit_code == 0
        assert "identical" in result.output.lower()

    def test_different_files(self, tmp_path: Path):
        """Different files produce a unified diff."""
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("line1\nline2\n")
        b.write_text("line1\nchanged\n")
        result = runner.invoke(app, ["compare-files", str(a), str(b)])
        assert result.exit_code == 0
        assert "---" in result.output
        assert "+++" in result.output

    def test_missing_file_a(self, tmp_path: Path):
        """Missing first file returns error."""
        b = tmp_path / "b.txt"
        b.write_text("data")
        result = runner.invoke(app, ["compare-files", "/no/such/file", str(b)])
        assert result.exit_code != 0
        assert "not a file" in result.output

    def test_missing_file_b(self, tmp_path: Path):
        """Missing second file returns error."""
        a = tmp_path / "a.txt"
        a.write_text("data")
        result = runner.invoke(app, ["compare-files", str(a), "/no/such/file"])
        assert result.exit_code != 0
        assert "not a file" in result.output


# ---------------------------------------------------------------------------
# backup_file tests
# ---------------------------------------------------------------------------


class TestBackupFile:
    """Tests for the backup-file command."""

    def test_backup_with_destination(self, tmp_path: Path):
        """Backup to an explicit destination."""
        src = tmp_path / "original.txt"
        dst = tmp_path / "copy.txt"
        src.write_text("important data")
        result = runner.invoke(
            app, ["backup-file", str(src), "--destination", str(dst)]
        )
        assert result.exit_code == 0
        assert dst.read_text() == "important data"
        assert "Backed up" in result.output

    def test_backup_default_destination(self, tmp_path: Path):
        """Backup with no destination creates a .bak file."""
        src = tmp_path / "data.txt"
        src.write_text("content")
        result = runner.invoke(app, ["backup-file", str(src)])
        assert result.exit_code == 0
        bak = tmp_path / "data.txt.bak"
        assert bak.exists()
        assert bak.read_text() == "content"

    def test_backup_missing_source(self):
        """Missing source file returns error."""
        result = runner.invoke(app, ["backup-file", "/no/such/file"])
        assert result.exit_code != 0
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# restore_file tests
# ---------------------------------------------------------------------------


class TestRestoreFile:
    """Tests for the restore-file command."""

    def test_restore_from_backup(self, tmp_path: Path):
        """Restore overwrites target with backup contents."""
        bak = tmp_path / "data.bak"
        target = tmp_path / "data.txt"
        bak.write_text("backup content")
        target.write_text("old content")
        result = runner.invoke(app, ["restore-file", str(bak), str(target)])
        assert result.exit_code == 0
        assert target.read_text() == "backup content"
        assert "Restored" in result.output

    def test_restore_creates_target(self, tmp_path: Path):
        """Restore creates the target file if it doesn't exist."""
        bak = tmp_path / "data.bak"
        target = tmp_path / "data.txt"
        bak.write_text("fresh data")
        result = runner.invoke(app, ["restore-file", str(bak), str(target)])
        assert result.exit_code == 0
        assert target.exists()
        assert target.read_text() == "fresh data"

    def test_restore_missing_backup(self, tmp_path: Path):
        """Missing backup file returns error."""
        target = tmp_path / "data.txt"
        result = runner.invoke(app, ["restore-file", "/no/such/backup", str(target)])
        assert result.exit_code != 0
        assert "not found" in result.output

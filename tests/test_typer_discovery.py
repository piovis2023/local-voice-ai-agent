"""Tests for the extensible command surface via Typer discovery (R-12)."""

import pytest
from pathlib import Path

from voice_agent.typer_discovery import (
    CommandInfo,
    build_catalog_from_files,
    build_command_catalog,
    discover_commands,
)


# ---------------------------------------------------------------------------
# Sample Typer command files for testing
# ---------------------------------------------------------------------------

SAMPLE_TYPER_FILE = '''\
import typer

app = typer.Typer()


@app.command()
def list_dir(path: str = "."):
    """List files in a directory."""
    import os
    for f in os.listdir(path):
        print(f)


@app.command()
def backup_file(source: str, destination: str):
    """Create a backup copy of a file."""
    import shutil
    shutil.copy2(source, destination)


@app.command()
def compare_files(file_a: str, file_b: str):
    """Compare two files and show differences."""
    pass


def helper_function():
    """This is NOT a command — no decorator."""
    pass
'''

SAMPLE_NO_COMMANDS = '''\
import typer

app = typer.Typer()


def not_a_command():
    """Regular function, no decorator."""
    pass
'''

SAMPLE_NO_DOCSTRINGS = '''\
import typer

app = typer.Typer()


@app.command()
def quick_cmd(name: str):
    pass
'''

SAMPLE_NO_PARENS = '''\
import typer

app = typer.Typer()


@app.command
def bare_decorator(arg: int):
    """Decorated without parentheses."""
    pass
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def typer_file(tmp_path: Path) -> Path:
    """Write the sample Typer file to a temp directory."""
    f = tmp_path / "commands.py"
    f.write_text(SAMPLE_TYPER_FILE)
    return f


@pytest.fixture
def empty_typer_file(tmp_path: Path) -> Path:
    f = tmp_path / "empty_commands.py"
    f.write_text(SAMPLE_NO_COMMANDS)
    return f


@pytest.fixture
def no_docstring_file(tmp_path: Path) -> Path:
    f = tmp_path / "no_doc.py"
    f.write_text(SAMPLE_NO_DOCSTRINGS)
    return f


@pytest.fixture
def bare_decorator_file(tmp_path: Path) -> Path:
    f = tmp_path / "bare.py"
    f.write_text(SAMPLE_NO_PARENS)
    return f


# ---------------------------------------------------------------------------
# discover_commands tests
# ---------------------------------------------------------------------------


class TestDiscoverCommands:
    """Tests for discover_commands."""

    def test_discovers_all_commands(self, typer_file: Path):
        """Discovers all @app.command() functions."""
        commands = discover_commands(typer_file)
        names = [c.name for c in commands]
        assert "list-dir" in names
        assert "backup-file" in names
        assert "compare-files" in names
        assert len(commands) == 3

    def test_ignores_non_commands(self, typer_file: Path):
        """Functions without @app.command() are ignored."""
        commands = discover_commands(typer_file)
        names = [c.name for c in commands]
        assert "helper-function" not in names

    def test_extracts_docstrings(self, typer_file: Path):
        """Docstrings are extracted for each command."""
        commands = discover_commands(typer_file)
        by_name = {c.name: c for c in commands}
        assert "List files" in by_name["list-dir"].docstring
        assert "backup copy" in by_name["backup-file"].docstring

    def test_extracts_params(self, typer_file: Path):
        """Parameter names and types are extracted."""
        commands = discover_commands(typer_file)
        by_name = {c.name: c for c in commands}
        assert "path:str" in by_name["list-dir"].params
        assert "source:str" in by_name["backup-file"].params
        assert "destination:str" in by_name["backup-file"].params

    def test_no_commands_found(self, empty_typer_file: Path):
        """A file with no @app.command() yields empty list."""
        commands = discover_commands(empty_typer_file)
        assert commands == []

    def test_missing_docstring(self, no_docstring_file: Path):
        """Commands without docstrings get empty strings."""
        commands = discover_commands(no_docstring_file)
        assert len(commands) == 1
        assert commands[0].docstring == ""

    def test_bare_decorator(self, bare_decorator_file: Path):
        """@app.command without parentheses is detected."""
        commands = discover_commands(bare_decorator_file)
        assert len(commands) == 1
        assert commands[0].name == "bare-decorator"

    def test_file_not_found(self):
        """FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError):
            discover_commands("/nonexistent/path/commands.py")

    def test_underscores_become_hyphens(self, typer_file: Path):
        """Function underscores are converted to hyphens in command names."""
        commands = discover_commands(typer_file)
        names = [c.name for c in commands]
        assert all("-" in name or len(name.split("-")) >= 1 for name in names)
        assert "list_dir" not in names


# ---------------------------------------------------------------------------
# build_command_catalog tests
# ---------------------------------------------------------------------------


class TestBuildCommandCatalog:
    """Tests for build_command_catalog."""

    def test_catalog_contains_all_commands(self, typer_file: Path):
        """Catalog string includes all discovered commands."""
        catalog = build_command_catalog(typer_file)
        assert "list-dir" in catalog
        assert "backup-file" in catalog
        assert "compare-files" in catalog

    def test_catalog_includes_descriptions(self, typer_file: Path):
        """Catalog includes first-line docstrings."""
        catalog = build_command_catalog(typer_file)
        assert "List files" in catalog
        assert "backup copy" in catalog

    def test_catalog_includes_params(self, typer_file: Path):
        """Catalog includes parameter info."""
        catalog = build_command_catalog(typer_file)
        assert "path:str" in catalog

    def test_empty_catalog(self, empty_typer_file: Path):
        """Empty file produces a placeholder message."""
        catalog = build_command_catalog(empty_typer_file)
        assert "No commands" in catalog

    def test_no_docstring_catalog(self, no_docstring_file: Path):
        """Commands without docstrings are still listed."""
        catalog = build_command_catalog(no_docstring_file)
        assert "quick-cmd" in catalog


# ---------------------------------------------------------------------------
# build_catalog_from_files tests
# ---------------------------------------------------------------------------


class TestBuildCatalogFromFiles:
    """Tests for build_catalog_from_files."""

    def test_single_file(self, typer_file: Path):
        """A single file produces a labeled section."""
        catalog = build_catalog_from_files([typer_file])
        assert "[commands]" in catalog
        assert "list-dir" in catalog

    def test_multiple_files(self, typer_file: Path, no_docstring_file: Path):
        """Multiple files produce multiple labeled sections."""
        catalog = build_catalog_from_files([typer_file, no_docstring_file])
        assert "[commands]" in catalog
        assert "[no_doc]" in catalog
        assert "list-dir" in catalog
        assert "quick-cmd" in catalog

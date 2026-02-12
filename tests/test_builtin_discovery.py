"""Integration tests: Typer discovery parses the built-in command files (Phase 6)."""

from pathlib import Path

from voice_agent.typer_discovery import (
    build_catalog_from_files,
    discover_commands,
)

COMMANDS_DIR = Path(__file__).resolve().parent.parent / "commands"


class TestFsCommandsDiscovery:
    """Verify typer_discovery can parse fs_commands.py (R-13)."""

    def test_discovers_fs_commands(self):
        commands = discover_commands(COMMANDS_DIR / "fs_commands.py")
        names = {c.name for c in commands}
        assert "list-dir" in names
        assert "compare-files" in names
        assert "backup-file" in names
        assert "restore-file" in names

    def test_fs_params(self):
        commands = discover_commands(COMMANDS_DIR / "fs_commands.py")
        by_name = {c.name: c for c in commands}
        assert "path:str" in by_name["list-dir"].params
        assert "file_a:str" in by_name["compare-files"].params
        assert "source:str" in by_name["backup-file"].params


class TestDbCommandsDiscovery:
    """Verify typer_discovery can parse db_commands.py (R-14)."""

    def test_discovers_db_commands(self):
        commands = discover_commands(COMMANDS_DIR / "db_commands.py")
        names = {c.name for c in commands}
        assert "create-table" in names
        assert "insert-row" in names
        assert "query-rows" in names
        assert "update-row" in names
        assert "delete-row" in names

    def test_db_params(self):
        commands = discover_commands(COMMANDS_DIR / "db_commands.py")
        by_name = {c.name: c for c in commands}
        assert "table:str" in by_name["create-table"].params
        assert "values:str" in by_name["insert-row"].params


class TestExportCommandsDiscovery:
    """Verify typer_discovery can parse export_commands.py (R-15)."""

    def test_discovers_export_commands(self):
        commands = discover_commands(COMMANDS_DIR / "export_commands.py")
        names = {c.name for c in commands}
        assert "export-query-json" in names
        assert "export-query-yaml" in names
        assert "export-query-csv" in names
        assert "export-scratchpad-json" in names
        assert "export-scratchpad-yaml" in names
        assert "export-scratchpad-csv" in names


class TestCombinedCatalog:
    """Verify build_catalog_from_files works with all built-in files."""

    def test_combined_catalog(self):
        files = [
            COMMANDS_DIR / "fs_commands.py",
            COMMANDS_DIR / "db_commands.py",
            COMMANDS_DIR / "export_commands.py",
        ]
        catalog = build_catalog_from_files(files)
        assert "[fs_commands]" in catalog
        assert "[db_commands]" in catalog
        assert "[export_commands]" in catalog
        assert "list-dir" in catalog
        assert "create-table" in catalog
        assert "export-query-json" in catalog

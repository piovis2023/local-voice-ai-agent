"""Tests for JSON/YAML/CSV export utilities (R-15)."""

import csv
import io
import json
import sqlite3

import pytest
import yaml
from pathlib import Path
from typer.testing import CliRunner

from commands.export_commands import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_db(tmp_path: Path) -> str:
    """Create a test database with sample data."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE items (id INTEGER, name TEXT, price REAL)")
    conn.execute("INSERT INTO items VALUES (1, 'Widget', 9.99)")
    conn.execute("INSERT INTO items VALUES (2, 'Gadget', 24.50)")
    conn.commit()
    conn.close()
    return db_path


def _setup_scratchpad(tmp_path: Path) -> str:
    """Create a scratchpad file with sample content."""
    sp = tmp_path / "scratch.md"
    sp.write_text("Note one\nNote two\nNote three\n")
    return str(sp)


# ---------------------------------------------------------------------------
# export_query_json tests
# ---------------------------------------------------------------------------


class TestExportQueryJson:
    """Tests for the export-query-json command."""

    def test_exports_all_rows(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.json")
        result = runner.invoke(
            app, ["export-query-json", "items", out, "--db", db]
        )
        assert result.exit_code == 0
        data = json.loads(Path(out).read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Widget"

    def test_exports_with_where(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.json")
        result = runner.invoke(
            app, ["export-query-json", "items", out, "--where", "name = Gadget", "--db", db]
        )
        assert result.exit_code == 0
        data = json.loads(Path(out).read_text())
        assert len(data) == 1
        assert data[0]["name"] == "Gadget"

    def test_output_message(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.json")
        result = runner.invoke(
            app, ["export-query-json", "items", out, "--db", db]
        )
        assert "2 row(s)" in result.output
        assert "JSON" in result.output


# ---------------------------------------------------------------------------
# export_query_yaml tests
# ---------------------------------------------------------------------------


class TestExportQueryYaml:
    """Tests for the export-query-yaml command."""

    def test_exports_valid_yaml(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.yaml")
        result = runner.invoke(
            app, ["export-query-yaml", "items", out, "--db", db]
        )
        assert result.exit_code == 0
        data = yaml.safe_load(Path(out).read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Widget"

    def test_output_message(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.yaml")
        result = runner.invoke(
            app, ["export-query-yaml", "items", out, "--db", db]
        )
        assert "YAML" in result.output


# ---------------------------------------------------------------------------
# export_query_csv tests
# ---------------------------------------------------------------------------


class TestExportQueryCsv:
    """Tests for the export-query-csv command."""

    def test_exports_valid_csv(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.csv")
        result = runner.invoke(
            app, ["export-query-csv", "items", out, "--db", db]
        )
        assert result.exit_code == 0
        reader = csv.reader(io.StringIO(Path(out).read_text()))
        rows = list(reader)
        assert rows[0] == ["id", "name", "price"]
        assert len(rows) == 3  # header + 2 data rows

    def test_output_message(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        out = str(tmp_path / "out.csv")
        result = runner.invoke(
            app, ["export-query-csv", "items", out, "--db", db]
        )
        assert "CSV" in result.output


# ---------------------------------------------------------------------------
# export_scratchpad_json tests
# ---------------------------------------------------------------------------


class TestExportScratchpadJson:
    """Tests for the export-scratchpad-json command."""

    def test_exports_scratchpad(self, tmp_path: Path):
        sp = _setup_scratchpad(tmp_path)
        out = str(tmp_path / "sp.json")
        result = runner.invoke(
            app, ["export-scratchpad-json", out, "--scratchpad", sp]
        )
        assert result.exit_code == 0
        data = json.loads(Path(out).read_text())
        assert "Note one" in data["scratchpad"]

    def test_empty_scratchpad(self, tmp_path: Path):
        out = str(tmp_path / "sp.json")
        result = runner.invoke(
            app, ["export-scratchpad-json", out, "--scratchpad", "/nonexistent"]
        )
        assert result.exit_code == 0
        data = json.loads(Path(out).read_text())
        assert data["scratchpad"] == ""


# ---------------------------------------------------------------------------
# export_scratchpad_yaml tests
# ---------------------------------------------------------------------------


class TestExportScratchpadYaml:
    """Tests for the export-scratchpad-yaml command."""

    def test_exports_scratchpad(self, tmp_path: Path):
        sp = _setup_scratchpad(tmp_path)
        out = str(tmp_path / "sp.yaml")
        result = runner.invoke(
            app, ["export-scratchpad-yaml", out, "--scratchpad", sp]
        )
        assert result.exit_code == 0
        data = yaml.safe_load(Path(out).read_text())
        assert "Note one" in data["scratchpad"]


# ---------------------------------------------------------------------------
# export_scratchpad_csv tests
# ---------------------------------------------------------------------------


class TestExportScratchpadCsv:
    """Tests for the export-scratchpad-csv command."""

    def test_exports_lines(self, tmp_path: Path):
        sp = _setup_scratchpad(tmp_path)
        out = str(tmp_path / "sp.csv")
        result = runner.invoke(
            app, ["export-scratchpad-csv", out, "--scratchpad", sp]
        )
        assert result.exit_code == 0
        reader = csv.reader(io.StringIO(Path(out).read_text()))
        rows = list(reader)
        assert rows[0] == ["line"]
        assert rows[1] == ["Note one"]
        assert len(rows) == 4  # header + 3 lines

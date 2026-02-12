"""Tests for SQLite database CRUD operations (R-14)."""

import sqlite3

import pytest
from pathlib import Path
from typer.testing import CliRunner

from commands.db_commands import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path, table: str = "users") -> str:
    """Create a test database with a simple table and return its path."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)"
    )
    conn.commit()
    conn.close()
    return db_path


def _insert(db_path: str, table: str, values: str) -> None:
    """Insert a row into the test database."""
    conn = sqlite3.connect(db_path)
    conn.execute(f"INSERT INTO {table} VALUES ({values})")
    conn.commit()
    conn.close()


def _count(db_path: str, table: str) -> int:
    """Count rows in a table."""
    conn = sqlite3.connect(db_path)
    (n,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    conn.close()
    return n


# ---------------------------------------------------------------------------
# create_table tests
# ---------------------------------------------------------------------------


class TestCreateTable:
    """Tests for the create-table command."""

    def test_creates_table(self, tmp_path: Path):
        db = str(tmp_path / "new.db")
        result = runner.invoke(
            app,
            ["create-table", "items", "id INTEGER PRIMARY KEY, name TEXT", "--db", db],
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        # Verify table exists
        conn = sqlite3.connect(db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor]
        conn.close()
        assert "items" in tables

    def test_create_existing_table_is_idempotent(self, tmp_path: Path):
        db = _make_db(tmp_path)
        result = runner.invoke(
            app,
            [
                "create-table",
                "users",
                "id INTEGER PRIMARY KEY, name TEXT, age INTEGER",
                "--db",
                db,
            ],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# insert_row tests
# ---------------------------------------------------------------------------


class TestInsertRow:
    """Tests for the insert-row command."""

    def test_insert_row(self, tmp_path: Path):
        db = _make_db(tmp_path)
        result = runner.invoke(
            app, ["insert-row", "users", '1, "Alice", 30', "--db", db]
        )
        assert result.exit_code == 0
        assert "inserted" in result.output.lower()
        assert _count(db, "users") == 1

    def test_insert_multiple_rows(self, tmp_path: Path):
        db = _make_db(tmp_path)
        runner.invoke(app, ["insert-row", "users", '1, "Alice", 30', "--db", db])
        runner.invoke(app, ["insert-row", "users", '2, "Bob", 25', "--db", db])
        assert _count(db, "users") == 2


# ---------------------------------------------------------------------------
# query_rows tests
# ---------------------------------------------------------------------------


class TestQueryRows:
    """Tests for the query-rows command."""

    def test_query_all_rows(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, "users", '1, "Alice", 30')
        _insert(db, "users", '2, "Bob", 25')
        result = runner.invoke(app, ["query-rows", "users", "--db", db])
        assert result.exit_code == 0
        assert "Alice" in result.output
        assert "Bob" in result.output

    def test_query_with_where(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, "users", '1, "Alice", 30')
        _insert(db, "users", '2, "Bob", 25')
        result = runner.invoke(
            app, ["query-rows", "users", "--where", "age > 26", "--db", db]
        )
        assert result.exit_code == 0
        assert "Alice" in result.output
        assert "Bob" not in result.output

    def test_query_shows_column_headers(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, "users", '1, "Alice", 30')
        result = runner.invoke(app, ["query-rows", "users", "--db", db])
        assert "id" in result.output
        assert "name" in result.output
        assert "age" in result.output


# ---------------------------------------------------------------------------
# update_row tests
# ---------------------------------------------------------------------------


class TestUpdateRow:
    """Tests for the update-row command."""

    def test_update_row(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, "users", '1, "Alice", 30')
        result = runner.invoke(
            app,
            ["update-row", "users", 'name = "Alicia"', "id = 1", "--db", db],
        )
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
        # Verify the change
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT name FROM users WHERE id = 1").fetchone()
        conn.close()
        assert row[0] == "Alicia"

    def test_update_no_match(self, tmp_path: Path):
        db = _make_db(tmp_path)
        result = runner.invoke(
            app,
            ["update-row", "users", 'name = "Ghost"', "id = 999", "--db", db],
        )
        assert result.exit_code == 0
        assert "0 row(s)" in result.output


# ---------------------------------------------------------------------------
# delete_row tests
# ---------------------------------------------------------------------------


class TestDeleteRow:
    """Tests for the delete-row command."""

    def test_delete_row(self, tmp_path: Path):
        db = _make_db(tmp_path)
        _insert(db, "users", '1, "Alice", 30')
        _insert(db, "users", '2, "Bob", 25')
        result = runner.invoke(
            app, ["delete-row", "users", "id = 1", "--db", db]
        )
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert _count(db, "users") == 1

    def test_delete_no_match(self, tmp_path: Path):
        db = _make_db(tmp_path)
        result = runner.invoke(
            app, ["delete-row", "users", "id = 999", "--db", db]
        )
        assert result.exit_code == 0
        assert "0 row(s)" in result.output


# ---------------------------------------------------------------------------
# Identifier validation tests
# ---------------------------------------------------------------------------


class TestIdentValidation:
    """Tests for SQL identifier sanitisation."""

    def test_invalid_table_name_rejected(self, tmp_path: Path):
        db = str(tmp_path / "test.db")
        result = runner.invoke(
            app,
            ["create-table", "drop table;--", "id INTEGER", "--db", db],
        )
        assert result.exit_code != 0

"""SQLite database CRUD operations (R-14).

Typer command file providing: create table, insert row, query rows,
update row, and delete row.  Operates on a configurable local ``.db`` file.
"""

from __future__ import annotations

import sqlite3

import typer

app = typer.Typer()

DEFAULT_DB = "voice_agent.db"


@app.command()
def create_table(table: str, columns: str, db: str = DEFAULT_DB) -> None:
    """Create a new table with the given column definitions.

    Columns should be a comma-separated string of 'name TYPE' pairs,
    e.g. 'id INTEGER PRIMARY KEY, name TEXT, age INTEGER'.
    """
    _validate_column_defs(columns)
    conn = sqlite3.connect(db)
    try:
        conn.execute(f"CREATE TABLE IF NOT EXISTS [{_ident(table)}] ({columns})")
        conn.commit()
        typer.echo(f"Table '{table}' created in {db}.")
    finally:
        conn.close()


@app.command()
def insert_row(table: str, values: str, db: str = DEFAULT_DB) -> None:
    """Insert a row into a table.

    Values should be a comma-separated string, e.g. '1, "Alice", 30'.
    """
    parts = [v.strip() for v in values.split(",")]
    placeholders = ", ".join("?" for _ in parts)
    bound = [_coerce_value(v) for v in parts]
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            f"INSERT INTO [{_ident(table)}] VALUES ({placeholders})", bound
        )
        conn.commit()
        typer.echo(f"Row inserted into '{table}'.")
    finally:
        conn.close()


@app.command()
def query_rows(table: str, where: str = "", db: str = DEFAULT_DB) -> None:
    """Query rows from a table with an optional WHERE clause."""
    conn = sqlite3.connect(db)
    try:
        sql = f"SELECT * FROM [{_ident(table)}]"
        params: list[object] = []
        if where:
            col, val, params = _parse_simple_where(where)
            sql += f" WHERE [{col}] = ?"
        cursor = conn.execute(sql, params)
        col_names = [desc[0] for desc in cursor.description]
        typer.echo(" | ".join(col_names))
        typer.echo("-" * (len(" | ".join(col_names))))
        for row in cursor:
            typer.echo(" | ".join(str(v) for v in row))
    finally:
        conn.close()


@app.command()
def update_row(table: str, set_clause: str, where: str, db: str = DEFAULT_DB) -> None:
    """Update rows in a table matching a WHERE clause.

    set_clause: e.g. 'name = "Bob", age = 31'
    where: e.g. 'id = 1'
    """
    set_parts = _parse_assignments(set_clause)
    where_col, where_val, where_params = _parse_simple_where(where)

    set_sql = ", ".join(f"[{col}] = ?" for col, _ in set_parts)
    params: list[object] = [val for _, val in set_parts] + where_params

    conn = sqlite3.connect(db)
    try:
        sql = f"UPDATE [{_ident(table)}] SET {set_sql} WHERE [{where_col}] = ?"
        cursor = conn.execute(sql, params)
        conn.commit()
        typer.echo(f"Updated {cursor.rowcount} row(s) in '{table}'.")
    finally:
        conn.close()


@app.command()
def delete_row(table: str, where: str, db: str = DEFAULT_DB) -> None:
    """Delete rows from a table matching a WHERE clause."""
    where_col, where_val, where_params = _parse_simple_where(where)
    conn = sqlite3.connect(db)
    try:
        sql = f"DELETE FROM [{_ident(table)}] WHERE [{where_col}] = ?"
        cursor = conn.execute(sql, where_params)
        conn.commit()
        typer.echo(f"Deleted {cursor.rowcount} row(s) from '{table}'.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ident(name: str) -> str:
    """Sanitise a SQL identifier (table/column name) to prevent injection.

    Only allows alphanumeric characters and underscores.
    """
    import re as _re

    if not _re.fullmatch(r"[A-Za-z_]\w*", name):
        raise typer.BadParameter(f"Invalid identifier: {name!r}")
    return name


def _coerce_value(raw: str) -> int | float | str:
    """Coerce a raw string token into an int, float, or stripped string."""
    raw = raw.strip().strip('"').strip("'")
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _parse_simple_where(clause: str) -> tuple[str, object, list[object]]:
    """Parse a simple 'column = value' WHERE clause.

    Returns (column_name, coerced_value, [coerced_value]).
    """
    import re as _re

    match = _re.fullmatch(r"\s*(\w+)\s*=\s*(.+)", clause)
    if not match:
        raise typer.BadParameter(
            f"WHERE clause must be 'column = value', got: {clause!r}"
        )
    col = match.group(1)
    _ident(col)  # validate column name
    val = _coerce_value(match.group(2))
    return col, val, [val]


def _parse_assignments(clause: str) -> list[tuple[str, object]]:
    """Parse a SET clause like 'name = \"Bob\", age = 31'.

    Returns a list of (column, coerced_value) pairs.
    """
    import re as _re

    pairs: list[tuple[str, object]] = []
    for part in clause.split(","):
        match = _re.fullmatch(r"\s*(\w+)\s*=\s*(.+)", part.strip())
        if not match:
            raise typer.BadParameter(
                f"SET clause must be 'col = val, ...', got segment: {part.strip()!r}"
            )
        col = match.group(1)
        _ident(col)
        val = _coerce_value(match.group(2))
        pairs.append((col, val))
    return pairs


def _validate_column_defs(columns: str) -> None:
    """Basic validation that column definitions look reasonable."""
    import re as _re

    for part in columns.split(","):
        part = part.strip()
        if not part:
            continue
        # Each part should start with a valid identifier
        tokens = part.split()
        if not tokens or not _re.fullmatch(r"[A-Za-z_]\w*", tokens[0]):
            raise typer.BadParameter(
                f"Invalid column definition: {part!r}"
            )


if __name__ == "__main__":
    app()

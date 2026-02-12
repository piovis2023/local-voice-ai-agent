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
    conn = sqlite3.connect(db)
    try:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_ident(table)} ({columns})")
        conn.commit()
        typer.echo(f"Table '{table}' created in {db}.")
    finally:
        conn.close()


@app.command()
def insert_row(table: str, values: str, db: str = DEFAULT_DB) -> None:
    """Insert a row into a table.

    Values should be a comma-separated string, e.g. '1, "Alice", 30'.
    """
    conn = sqlite3.connect(db)
    try:
        conn.execute(f"INSERT INTO {_ident(table)} VALUES ({values})")
        conn.commit()
        typer.echo(f"Row inserted into '{table}'.")
    finally:
        conn.close()


@app.command()
def query_rows(table: str, where: str = "", db: str = DEFAULT_DB) -> None:
    """Query rows from a table with an optional WHERE clause."""
    conn = sqlite3.connect(db)
    try:
        sql = f"SELECT * FROM {_ident(table)}"
        if where:
            sql += f" WHERE {where}"
        cursor = conn.execute(sql)
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
    conn = sqlite3.connect(db)
    try:
        sql = f"UPDATE {_ident(table)} SET {set_clause} WHERE {where}"
        cursor = conn.execute(sql)
        conn.commit()
        typer.echo(f"Updated {cursor.rowcount} row(s) in '{table}'.")
    finally:
        conn.close()


@app.command()
def delete_row(table: str, where: str, db: str = DEFAULT_DB) -> None:
    """Delete rows from a table matching a WHERE clause."""
    conn = sqlite3.connect(db)
    try:
        sql = f"DELETE FROM {_ident(table)} WHERE {where}"
        cursor = conn.execute(sql)
        conn.commit()
        typer.echo(f"Deleted {cursor.rowcount} row(s) from '{table}'.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ident(name: str) -> str:
    """Sanitise a SQL identifier (table name) to prevent injection.

    Only allows alphanumeric characters and underscores.
    """
    if not name.isidentifier():
        raise typer.BadParameter(f"Invalid identifier: {name!r}")
    return name


if __name__ == "__main__":
    app()

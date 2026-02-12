"""JSON / YAML / CSV export utilities (R-15).

Typer command file providing: export query results or scratchpad data
to JSON, YAML, or CSV format.  Write output to a specified file path.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from pathlib import Path

import typer
import yaml

app = typer.Typer()

DEFAULT_DB = "voice_agent.db"


@app.command()
def export_query_json(
    table: str, output: str, where: str = "", db: str = DEFAULT_DB
) -> None:
    """Export query results from a SQLite table to a JSON file."""
    rows, col_names = _query(table, where, db)
    data = [dict(zip(col_names, row)) for row in rows]
    Path(output).write_text(json.dumps(data, indent=2, default=str) + "\n")
    typer.echo(f"Exported {len(data)} row(s) to {output} (JSON).")


@app.command()
def export_query_yaml(
    table: str, output: str, where: str = "", db: str = DEFAULT_DB
) -> None:
    """Export query results from a SQLite table to a YAML file."""
    rows, col_names = _query(table, where, db)
    data = [dict(zip(col_names, row)) for row in rows]
    Path(output).write_text(yaml.dump(data, default_flow_style=False))
    typer.echo(f"Exported {len(data)} row(s) to {output} (YAML).")


@app.command()
def export_query_csv(
    table: str, output: str, where: str = "", db: str = DEFAULT_DB
) -> None:
    """Export query results from a SQLite table to a CSV file."""
    rows, col_names = _query(table, where, db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(col_names)
    writer.writerows(rows)
    Path(output).write_text(buf.getvalue())
    typer.echo(f"Exported {len(rows)} row(s) to {output} (CSV).")


@app.command()
def export_scratchpad_json(output: str, scratchpad: str = "scratchpad.md") -> None:
    """Export scratchpad contents to a JSON file."""
    content = _read_scratchpad(scratchpad)
    data = {"scratchpad": content}
    Path(output).write_text(json.dumps(data, indent=2) + "\n")
    typer.echo(f"Scratchpad exported to {output} (JSON).")


@app.command()
def export_scratchpad_yaml(output: str, scratchpad: str = "scratchpad.md") -> None:
    """Export scratchpad contents to a YAML file."""
    content = _read_scratchpad(scratchpad)
    data = {"scratchpad": content}
    Path(output).write_text(yaml.dump(data, default_flow_style=False))
    typer.echo(f"Scratchpad exported to {output} (YAML).")


@app.command()
def export_scratchpad_csv(output: str, scratchpad: str = "scratchpad.md") -> None:
    """Export scratchpad contents to a CSV file (one line per row)."""
    content = _read_scratchpad(scratchpad)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["line"])
    for line in content.splitlines():
        writer.writerow([line])
    Path(output).write_text(buf.getvalue())
    typer.echo(f"Scratchpad exported to {output} (CSV).")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _query(
    table: str, where: str, db: str
) -> tuple[list[tuple[object, ...]], list[str]]:
    """Run a SELECT query and return (rows, column_names)."""
    conn = sqlite3.connect(db)
    try:
        sql = f"SELECT * FROM [{_ident(table)}]"
        params: list[object] = []
        if where:
            col, val, params = _parse_simple_where(where)
            sql += f" WHERE [{col}] = ?"
        cursor = conn.execute(sql, params)
        col_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return rows, col_names
    finally:
        conn.close()


def _ident(name: str) -> str:
    """Sanitise a SQL identifier to prevent injection."""
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
    _ident(col)
    val = _coerce_value(match.group(2))
    return col, val, [val]


def _read_scratchpad(path: str) -> str:
    """Read scratchpad file contents."""
    p = Path(path)
    if not p.is_file():
        return ""
    return p.read_text()


if __name__ == "__main__":
    app()

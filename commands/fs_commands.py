"""File system operations (R-13).

Typer command file providing: list directory, compare files (difflib),
backup file, and restore file.
"""

from __future__ import annotations

import difflib
import os
import shutil
from pathlib import Path

import typer

app = typer.Typer()


@app.command()
def list_dir(path: str = ".") -> None:
    """List files and directories at the given path."""
    target = Path(path)
    if not target.exists():
        typer.echo(f"Error: path does not exist: {path}")
        raise typer.Exit(code=1)
    if not target.is_dir():
        typer.echo(f"Error: not a directory: {path}")
        raise typer.Exit(code=1)
    entries = sorted(target.iterdir())
    for entry in entries:
        suffix = "/" if entry.is_dir() else ""
        typer.echo(f"{entry.name}{suffix}")


@app.command()
def compare_files(file_a: str, file_b: str) -> None:
    """Compare two files and show a unified diff."""
    path_a = Path(file_a)
    path_b = Path(file_b)
    if not path_a.is_file():
        typer.echo(f"Error: not a file: {file_a}")
        raise typer.Exit(code=1)
    if not path_b.is_file():
        typer.echo(f"Error: not a file: {file_b}")
        raise typer.Exit(code=1)
    lines_a = path_a.read_text().splitlines(keepends=True)
    lines_b = path_b.read_text().splitlines(keepends=True)
    diff = difflib.unified_diff(lines_a, lines_b, fromfile=file_a, tofile=file_b)
    output = "".join(diff)
    if output:
        typer.echo(output)
    else:
        typer.echo("Files are identical.")


@app.command()
def backup_file(source: str, destination: str = "") -> None:
    """Create a backup copy of a file.

    If destination is omitted the backup is written to <source>.bak.
    """
    src = Path(source)
    if not src.is_file():
        typer.echo(f"Error: source file not found: {source}")
        raise typer.Exit(code=1)
    dst = Path(destination) if destination else src.with_suffix(src.suffix + ".bak")
    shutil.copy2(str(src), str(dst))
    typer.echo(f"Backed up {src} -> {dst}")


@app.command()
def restore_file(backup: str, target: str) -> None:
    """Restore a file from a backup copy."""
    bak = Path(backup)
    if not bak.is_file():
        typer.echo(f"Error: backup file not found: {backup}")
        raise typer.Exit(code=1)
    shutil.copy2(str(bak), str(target))
    typer.echo(f"Restored {bak} -> {target}")


if __name__ == "__main__":
    app()

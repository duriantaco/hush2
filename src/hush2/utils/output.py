"""Output formatting — rich-based console with JSON/quiet modes."""

from __future__ import annotations

import json
import sys
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class OutputMode(Enum):
    HUMAN = "human"
    JSON = "json"
    QUIET = "quiet"


class HushConsole:
    """Unified output respecting --json / --quiet flags."""

    def __init__(self, mode: OutputMode = OutputMode.HUMAN) -> None:
        self.mode = mode
        self._console = Console(stderr=True) if mode == OutputMode.JSON else Console()

    def success(self, message: str) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            return
        self._console.print(f"[green]{message}[/green]")

    def error(self, message: str) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            Console(stderr=True).print(f"[red]error:[/red] {message}")
            return
        self._console.print(f"[red]error:[/red] {message}")

    def warn(self, message: str) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            return
        self._console.print(f"[yellow]warning:[/yellow] {message}")

    def info(self, message: str) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            return
        self._console.print(f"[dim]{message}[/dim]")

    def print_value(self, value: str) -> None:
        """Print a raw value (for get command)."""
        if self.mode == OutputMode.JSON:
            self.print_json({"value": value})
        else:
            sys.stdout.write(value + "\n")

    def print_table(self, columns: list[str], rows: list[list[str]], title: str | None = None) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            self.print_json([dict(zip(columns, row)) for row in rows])
            return
        table = Table(title=title)
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        self._console.print(table)

    def print_json(self, data) -> None:
        sys.stdout.write(json.dumps(data, indent=2) + "\n")

    def print_panel(self, content: str, title: str | None = None) -> None:
        if self.mode == OutputMode.QUIET:
            return
        if self.mode == OutputMode.JSON:
            return
        self._console.print(Panel(content, title=title))

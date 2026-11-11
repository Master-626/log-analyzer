"""
CLI interface for log-analyzer.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import __version__
from .core import (
    analyze_levels,
    extract_exceptions,
    filter_by_level,
    normalize_level,
    search_keyword,
)

console = Console()

LOG_FILE = click.Path(exists=True, dir_okay=False, path_type=Path)


def _print_record(line: str) -> None:
    """Print a log line without interpreting ``[brackets]`` as Rich markup."""
    console.print(line, markup=False)


@click.group()
@click.version_option(version=__version__)
def main():
    """Log Analyzer - Smart log file analysis tool."""


@main.command()
@click.argument("file", type=LOG_FILE)
def stats(file: Path):
    """Show log level statistics."""
    console.print(f"\n[bold blue]📊 Log Statistics: {escape(str(file))}[/bold blue]\n")

    counts = analyze_levels(file)

    table = Table(title="Log Level Distribution")
    table.add_column("Level", style="cyan")
    table.add_column("Count", justify="right", style="green")

    total = sum(counts.values())
    for level, count in counts.items():
        pct = (count / total * 100) if total > 0 else 0
        table.add_row(level, f"{count} ({pct:.1f}%)")

    console.print(table)
    console.print(f"\nTotal entries: [bold]{total}[/bold]\n")


@main.command()
@click.argument("file", type=LOG_FILE)
@click.option("--keyword", "-k", required=True, help="Keyword to search")
@click.option("--case-sensitive", "-c", is_flag=True, help="Case sensitive search")
def search(file: Path, keyword: str, case_sensitive: bool):
    """Search for keyword in log file."""
    try:
        results = search_keyword(file, keyword, case_sensitive)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--keyword") from exc

    console.print(f"\n[bold blue]🔍 Searching for: {escape(keyword)}[/bold blue]\n")

    if results:
        console.print(f"Found [bold green]{len(results)}[/bold green] matches:\n")
        for line in results[:20]:  # Show first 20
            _print_record(line)
        if len(results) > 20:
            console.print(f"\n... and {len(results) - 20} more")
    else:
        console.print("[yellow]No matches found.[/yellow]")


@main.command("filter")
@click.argument("file", type=LOG_FILE)
@click.option(
    "--level",
    "-l",
    default="ERROR",
    help="Minimum level: DEBUG, INFO, WARNING, ERROR, CRITICAL (aliases: WARN, FATAL)",
)
def filter_logs(file: Path, level: str):
    """Filter log entries by level."""
    try:
        normalized = normalize_level(level)
        results = filter_by_level(file, normalized)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--level") from exc

    console.print(f"\n[bold blue]🔍 Filtering by level: {escape(normalized)}+[/bold blue]\n")

    if results:
        console.print(f"Found [bold red]{len(results)}[/bold red] entries:\n")
        for line in results[:20]:
            _print_record(line)
        if len(results) > 20:
            console.print(f"\n... and {len(results) - 20} more")
    else:
        console.print("[green]No entries found.[/green]")


@main.command()
@click.argument("file", type=LOG_FILE)
def exceptions(file: Path):
    """Extract exception tracebacks."""
    console.print("\n[bold blue]🔥 Extracting exceptions...[/bold blue]\n")

    found = extract_exceptions(file)

    if found:
        console.print(f"Found [bold red]{len(found)}[/bold red] exceptions:\n")
        for index, exc in enumerate(found[:5], 1):
            console.print(f"[bold]Exception #{index}:[/bold]")
            _print_record(exc)
            console.print("")
        if len(found) > 5:
            console.print(f"... and {len(found) - 5} more exceptions")
    else:
        console.print("[green]No exceptions found. Great![/green]")


if __name__ == "__main__":
    main()

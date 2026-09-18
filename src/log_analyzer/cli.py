"""
CLI interface for log-analyzer.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .core import analyze_levels, search_keyword, filter_by_level, extract_exceptions

console = Console()


@click.group()
@click.version_option()
def main():
    """Log Analyzer - Smart log file analysis tool."""
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def stats(file: Path):
    """Show log level statistics."""
    console.print(f"\n[bold blue]📊 Log Statistics: {file}[/bold blue]\n")

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
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--keyword", "-k", required=True, help="Keyword to search")
@click.option("--case-sensitive", "-c", is_flag=True, help="Case sensitive search")
def search(file: Path, keyword: str, case_sensitive: bool):
    """Search for keyword in log file."""
    console.print(f"\n[bold blue]🔍 Searching for: {keyword}[/bold blue]\n")

    results = search_keyword(file, keyword, case_sensitive)

    if results:
        console.print(f"Found [bold green]{len(results)}[/bold green] matches:\n")
        for line in results[:20]:  # Show first 20
            console.print(line)
        if len(results) > 20:
            console.print(f"\n... and {len(results) - 20} more")
    else:
        console.print("[yellow]No matches found.[/yellow]")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--level", "-l", default="ERROR", help="Minimum level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
def filter(file: Path, level: str):
    """Filter log entries by level."""
    console.print(f"\n[bold blue]🔍 Filtering by level: {level.upper()}+[/bold blue]\n")

    results = filter_by_level(file, level)

    if results:
        console.print(f"Found [bold red]{len(results)}[/bold red] entries:\n")
        for line in results[:20]:
            console.print(line)
        if len(results) > 20:
            console.print(f"\n... and {len(results) - 20} more")
    else:
        console.print("[green]No entries found.[/green]")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def exceptions(file: Path):
    """Extract exception tracebacks."""
    console.print(f"\n[bold blue]🔥 Extracting exceptions...[/bold blue]\n")

    exceptions = extract_exceptions(file)

    if exceptions:
        console.print(f"Found [bold red]{len(exceptions)}[/bold red] exceptions:\n")
        for i, exc in enumerate(exceptions[:5], 1):
            console.print(f"[bold]Exception #{i}:[/bold]")
            console.print(exc)
            console.print("")
        if len(exceptions) > 5:
            console.print(f"... and {len(exceptions) - 5} more exceptions")
    else:
        console.print("[green]No exceptions found. Great![/green]")


if __name__ == "__main__":
    main()

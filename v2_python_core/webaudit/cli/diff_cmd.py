"""``webaudit diff`` — compare two audit runs for regressions and improvements."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from webaudit.scoring.diff import diff_audit_runs
from webaudit.storage.runs import load_audit_run

console = Console()


def diff_command(
    baseline: Path,
    current: Path,
    *,
    json_out: bool = False,
) -> None:
    try:
        baseline_run = load_audit_run(baseline)
        current_run = load_audit_run(current)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Load error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    diff = diff_audit_runs(baseline_run, current_run)

    if json_out:
        import json

        console.print(json.dumps(diff.to_dict(), indent=2))
        return

    console.print(
        f"[bold]Baseline[/bold] {diff.baseline_url} ({diff.baseline_started_at})\n"
        f"[bold]Current[/bold]  {diff.current_url} ({diff.current_started_at})"
    )
    console.print(
        f"\nHygiene Δ {diff.delta_hygiene:+d} · Exposure Δ {diff.delta_exposure:+d}\n"
    )

    if not diff.entries:
        console.print("[green]No significant changes detected.[/green]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Kind", style="cyan")
    table.add_column("Category")
    table.add_column("Item")
    table.add_column("Detail")

    kind_style = {
        "REGRESSION": "red",
        "IMPROVEMENT": "green",
        "NEW_ISSUE": "yellow",
        "RESOLVED": "dim",
        "INFO": "white",
    }

    for entry in diff.entries:
        style = kind_style.get(entry.kind, "white")
        table.add_row(
            f"[{style}]{entry.kind}[/{style}]",
            entry.category,
            entry.item,
            entry.detail[:80] + ("…" if len(entry.detail) > 80 else ""),
        )

    console.print(table)

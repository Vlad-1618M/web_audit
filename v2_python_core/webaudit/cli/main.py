"""Typer CLI — user-facing entry point for scans.

What: Defines the ``webaudit`` console command and ``scan`` subcommand.
Where: Registered in ``pyproject.toml`` as ``webaudit.cli.main:cli_entry``.
How: ``webaudit scan https://example.com [--config PATH] [--json]`` loads settings,
      calls ``run_audit()``, prints a Rich score table, optionally dumps JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from webaudit.config.settings import load_settings
from webaudit.cli.completion_cmd import completion_app, rewrite_legacy_completion_argv
from webaudit.orchestrator import audit_run_to_json, run_audit

app = typer.Typer(
    name="webaudit",
    help="Web Audit v2 — external security hygiene for public websites",
    no_args_is_help=True,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)
app.add_typer(completion_app, name="completion")
console = Console()


@app.callback()
def main() -> None:
    """Web Audit v2 — external security hygiene for public websites."""


@app.command("scan")
def scan(
    url: Annotated[str, typer.Argument(help="Target URL (https://example.com)")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Optional webaudit YAML config"),
    ] = None,
    site_config: Annotated[
        Path | None,
        typer.Option("--site-config", help="Per-site YAML overrides"),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory for audit_logs"),
    ] = None,
    json_stdout: Annotated[
        bool,
        typer.Option("--json", help="Print audit_run.json to stdout"),
    ] = False,
) -> None:
    """Run a hygiene scan against a public URL."""
    try:
        settings = load_settings(
            config_path=config,
            site_config_path=site_config,
            target_url=url,
        )
        if output:
            settings.output.directory = str(output)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(f"[bold]Scanning[/bold] {settings.target.url}")

    try:
        run = run_audit(settings)
    except ValueError as exc:
        console.print(f"[red]Scan error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title="Scores")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Hygiene", str(run.scores.hygiene))
    table.add_row("Exposure", str(run.scores.exposure))
    table.add_row("Verdict", run.scores.verdict)
    table.add_row("Findings", str(len(run.findings)))
    console.print(table)

    if json_stdout:
        console.print(audit_run_to_json(run))


def cli_entry() -> None:
    sys.argv = rewrite_legacy_completion_argv(sys.argv)
    app()


if __name__ == "__main__":
    cli_entry()

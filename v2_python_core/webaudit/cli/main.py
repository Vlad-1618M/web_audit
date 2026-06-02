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

from webaudit.config.settings import load_settings
from webaudit.cli.completion_cmd import completion_app, rewrite_legacy_completion_argv
from webaudit.cli.output_ui import handle_open_outputs, print_scan_summary
from webaudit.cli.report_cmd import report_command
from webaudit.cli.scan_progress import ScanProgress, Verbosity, resolve_verbosity
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
    open_outputs: Annotated[
        str | None,
        typer.Option(
            "--open",
            help="Open after scan: html, json, txt, all, none, ask (default: ask on TTY, else none)",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Verbose scan progress (HTTP/DNS/TLS detail)"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("-q", "--quiet", help="Minimal output (summary only)"),
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

    try:
        verbosity = resolve_verbosity(verbose=verbose, quiet=quiet)
    except ValueError as exc:
        console.print(f"[red]Option error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    progress = ScanProgress(console, verbosity)

    try:
        run = run_audit(settings, progress=progress)
    except ValueError as exc:
        console.print(f"[red]Scan error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if json_stdout:
        console.print(audit_run_to_json(run))
        return

    if verbosity != Verbosity.QUIET:
        console.print()
    print_scan_summary(run, console=console, target_url=settings.target.url)
    handle_open_outputs(run.reports, mode=open_outputs or "ask", console=console)


@app.command("report")
def report(
    audit_json: Annotated[
        Path,
        typer.Argument(help="Path to audit_run.json from a previous scan"),
    ],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Optional webaudit YAML for default report settings"),
    ] = None,
    variant: Annotated[
        str | None,
        typer.Option("--variant", help="Report template: technical, executive, minimal, dashboard, digest"),
    ] = None,
    theme: Annotated[
        str | None,
        typer.Option("--theme", help="Report theme (currently: dark)"),
    ] = None,
    formats: Annotated[
        str | None,
        typer.Option("--formats", help="Comma-separated outputs: html, txt, pdf"),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output directory (default: same folder as JSON)"),
    ] = None,
    open_outputs: Annotated[
        str | None,
        typer.Option(
            "--open",
            help="Open after render: html, json, txt, all, none, ask (default: ask on TTY)",
        ),
    ] = None,
) -> None:
    """Re-render HTML/TXT/PDF reports from an existing audit run JSON file."""
    report_command(
        audit_json=audit_json,
        config=config,
        variant=variant,
        theme=theme,
        formats=formats,
        output=output,
        open_outputs=open_outputs,
    )


def cli_entry() -> None:
    sys.argv = rewrite_legacy_completion_argv(sys.argv)
    app()


if __name__ == "__main__":
    cli_entry()

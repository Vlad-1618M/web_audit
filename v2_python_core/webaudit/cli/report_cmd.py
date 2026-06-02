"""``webaudit report`` — re-render reports from a saved ``audit_run.json``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from webaudit.cli.output_ui import handle_open_outputs, print_scan_summary
from webaudit.config.settings import load_settings
from webaudit.render.reports import write_run_reports
from webaudit.storage.runs import load_audit_run

console = Console()


def _parse_formats(raw: str | None, default: list[str]) -> list[str]:
    if raw is None:
        return default
    parts = [part.strip().lower() for part in raw.split(",") if part.strip()]
    return parts or default


def report_command(
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
        typer.Option("--variant", help="Report template: owner, technical, executive, minimal, dashboard, digest"),
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
    try:
        settings = load_settings(config_path=config)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if not audit_json.is_file():
        console.print(f"[red]Not found:[/red] {audit_json}")
        raise typer.Exit(code=2)

    try:
        run = load_audit_run(audit_json)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Load error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    report_variant = variant or settings.report.variant
    report_theme = theme or settings.report.theme
    wanted = _parse_formats(formats, [fmt for fmt in settings.output.formats if fmt != "json"])
    if not wanted:
        wanted = ["html", "txt"]

    run_dir = output or audit_json.parent
    run_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[dim]Rendering[/dim] {report_variant} · {run.meta.target_url}")

    try:
        report_paths, warnings = write_run_reports(
            run,
            run_dir,
            formats=wanted,
            report_variant=report_variant,
            report_theme=report_theme,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]Template error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    run.reports = {key: str(run_dir / name) for key, name in report_paths.items()}
    run.warnings = warnings
    print_scan_summary(run, console=console, target_url=run.meta.target_url)
    handle_open_outputs(run.reports, mode=open_outputs or "ask", console=console)

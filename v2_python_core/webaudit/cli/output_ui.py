"""Post-scan CLI output — compact summary and optional file open."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from webaudit.models.run import AuditRun

_OPEN_ALIASES = {
    "h": "html",
    "html": "html",
    "report": "html",
    "j": "json",
    "json": "json",
    "t": "txt",
    "txt": "txt",
    "p": "html",
    "pdf": "html",
    "a": "all",
    "all": "all",
    "n": "none",
    "none": "none",
    "ask": "ask",
}


def normalize_open_mode(raw: str | None, *, is_tty: bool) -> str:
    if raw is None:
        return "ask" if is_tty else "none"
    return _OPEN_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def resolve_open_keys(mode: str, reports: dict[str, str]) -> list[str]:
    if mode in {"", "none"}:
        return []
    if mode == "all":
        keys: list[str] = []
        for key in ("html", "txt", "pdf", "json"):
            if key in reports:
                keys.append(key)
        return keys
    if mode == "html" or mode == "pdf":
        return ["html"] if "html" in reports else (["pdf"] if "pdf" in reports else [])
    if mode in reports:
        return [mode]
    return []


def prompt_open_choice(console: Console) -> str:
    try:
        answer = console.input(
            "[dim]Open outputs?[/dim] "
            "[bold]h[/bold]=html  [bold]j[/bold]=json  [bold]t[/bold]=txt  "
            "[bold]a[/bold]=all  [bold]n[/bold]=none  [dim](Enter=none)[/dim]: "
        )
    except (EOFError, KeyboardInterrupt):
        console.print()
        return "none"
    return normalize_open_mode(answer or "none", is_tty=True)


def open_path(path: Path) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        elif system == "Windows":
            import os

            os.startfile(path)  # noqa: S606
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        return


def open_report_outputs(
    reports: dict[str, str],
    keys: list[str],
    *,
    console: Console,
    requested_pdf: bool = False,
) -> None:
    opened: list[str] = []
    for key in keys:
        path = reports.get(key)
        if not path:
            continue
        open_path(Path(path))
        opened.append(key)
    if not opened:
        return
    labels = ", ".join(opened)
    console.print(f"[dim]Opened:[/dim] {labels}")
    if requested_pdf and "html" in opened:
        console.print(
            "[dim]PDF tip:[/dim] In the browser use Print → Save as PDF "
            "(enable Background graphics for dark theme)"
        )


def handle_open_outputs(
    reports: dict[str, str],
    *,
    mode: str,
    console: Console,
    is_tty: bool | None = None,
) -> None:
    if is_tty is None:
        is_tty = sys.stdin.isatty()
    normalized = normalize_open_mode(mode, is_tty=is_tty)
    if normalized == "ask":
        if not is_tty:
            return
        normalized = prompt_open_choice(console)
    keys = resolve_open_keys(normalized, reports)
    open_report_outputs(
        reports,
        keys,
        console=console,
        requested_pdf=normalized == "pdf",
    )


def _verdict_style(verdict: str) -> str:
    return {
        "PASS": "green",
        "NEEDS_ATTENTION": "yellow",
        "AT_RISK": "red",
    }.get(verdict, "white")


def print_scan_summary(run: AuditRun, *, console: Console, target_url: str) -> None:
    style = _verdict_style(run.scores.verdict)
    console.print(
        f"[{style}]✓[/{style}] [bold]{target_url}[/bold] — "
        f"[{style}]{run.scores.verdict}[/{style}] "
        f"[dim](Hygiene {run.scores.hygiene} · Exposure {run.scores.exposure} · "
        f"{len(run.findings)} findings)[/dim]"
    )
    if not run.reports:
        return
    run_dir = Path(next(iter(run.reports.values()))).parent
    console.print(f"  [dim]{run_dir}/[/dim]")
    for key, label in (
        ("html", "report.html"),
        ("txt", "report.txt"),
        ("pdf", "report.pdf"),
        ("json", "audit_run.json"),
    ):
        if key in run.reports:
            console.print(f"    {label}")

    for note in run.warnings:
        console.print(f"  [yellow]Note:[/yellow] {note}")

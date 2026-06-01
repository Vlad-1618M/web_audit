"""Shell tab-completion — install, status, and uninstall with plain-English output.

What: Manages optional Tab autocomplete files under the user's home directory.
Where: ``webaudit completion …`` subcommands; also reached via legacy ``--install-completion``.
How: Writes/removes shell-specific files (e.g. ``~/.zfunc/_webaudit``); independent of ``.venv``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer._completion_shared import _get_shell_name, get_completion_script, install as typer_install

completion_app = typer.Typer(
    name="completion",
    help="Optional Tab autocomplete — install, check status, or remove.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

console = Console()

PROG_NAME = "webaudit"
COMPLETE_VAR = "_WEBAUDIT_COMPLETE"

_INSTALL_EXPLAIN = """\
[bold]What this did[/bold]
  A small helper file was added so your shell can suggest commands when you press [bold]Tab[/bold]
  (like autocomplete on a phone keyboard).

[bold]What it did [italic]not[/italic] do[/bold]
  • It did not install Web Audit again — that comes from [bold]pip install[/bold] / [bold]./dev-venv.sh setup[/bold]
  • It did not change your website or server
  • It is [bold]optional[/bold] — [bold]webaudit scan[/bold] works without it

[bold]Where it lives on your system[/bold]
  The file is in your [bold]home directory[/bold], not inside the project [bold].venv[/bold] folder.
  Deleting [bold].venv[/bold] does [bold]not[/bold] remove Tab completion — use:
    [cyan]webaudit completion uninstall[/cyan]

[bold]When it takes effect[/bold]
  Open a [bold]new terminal window[/bold] (or run [bold]exec zsh[/bold]), then try:
    [dim]webaudit <Tab>[/dim]
"""


def _completion_paths_for_shell(shell: str) -> list[Path]:
    home = Path.home()
    if shell == "zsh":
        return [home / ".zfunc" / f"_{PROG_NAME}"]
    if shell == "bash":
        return [home / ".bash_completions" / f"{PROG_NAME}.sh"]
    if shell == "fish":
        return [home / ".config/fish/completions" / f"{PROG_NAME}.fish"]
    return []


def _dotfile_notes_for_shell(shell: str) -> list[str]:
    """Lines Typer may append to shell rc files — we do not auto-remove these."""
    if shell == "zsh":
        return [
            "~/.zshrc may contain: fpath+=~/.zfunc; autoload -Uz compinit; compinit",
            "(shared by other tools — left in place on uninstall)",
        ]
    if shell == "bash":
        return [
            f"~/.bashrc may contain: source '~/.bash_completions/{PROG_NAME}.sh'",
            "(removed on uninstall if we added that exact line)",
        ]
    return []


def _detect_shell(explicit: str | None) -> str:
    if explicit:
        return explicit
    detected = _get_shell_name()
    if not detected:
        console.print("[red]Could not detect your shell.[/red] Pass one explicitly:")
        console.print("  webaudit completion install --shell zsh")
        raise typer.Exit(code=2)
    return detected


def _scan_installed() -> list[tuple[str, Path, bool]]:
    rows: list[tuple[str, Path, bool]] = []
    for shell in ("zsh", "bash", "fish"):
        for path in _completion_paths_for_shell(shell):
            rows.append((shell, path, path.is_file()))
    return rows


def _print_install_success(shell: str, path: Path) -> None:
    console.print(
        Panel(
            _INSTALL_EXPLAIN,
            title=f"[green]Tab completion installed[/green] ({shell})",
            border_style="green",
        )
    )
    console.print(f"  [bold]File:[/bold] {path}")
    for note in _dotfile_notes_for_shell(shell):
        console.print(f"  [dim]{note}[/dim]")


@completion_app.command("install")
def completion_install(
    shell: str | None = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell to install for (default: auto-detect).",
    ),
) -> None:
    """Install Tab autocomplete for webaudit (optional convenience)."""
    shell_name = _detect_shell(shell)
    try:
        _, path = typer_install(shell=shell_name, prog_name=PROG_NAME, complete_var=COMPLETE_VAR)
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code or 1)) from exc
    _print_install_success(shell_name, path)


@completion_app.command("uninstall")
def completion_uninstall(
    shell: str | None = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell to uninstall for (default: remove all webaudit completion files found).",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove webaudit Tab autocomplete files from your home directory."""
    targets = _scan_installed()
    if shell:
        targets = [(s, p, exists) for s, p, exists in targets if s == shell]

    existing = [(s, p) for s, p, exists in targets if exists]
    if not existing:
        console.print("[yellow]No webaudit completion files found to remove.[/yellow]")
        console.print(
            "[dim]Note: deleting .venv does not touch completion — nothing was left on disk.[/dim]"
        )
        return

    table = Table(title="Will remove")
    table.add_column("Shell")
    table.add_column("Path")
    for s, p in existing:
        table.add_row(s, str(p))
    console.print(table)
    console.print(
        "[dim]This does not uninstall the webaudit command itself — only Tab suggestions.[/dim]"
    )
    console.print(
        "[dim]To remove the tool, deactivate the venv and delete .venv or run ./dev-venv.sh teardown[/dim]"
    )

    if not yes and not typer.confirm("Remove these completion files?", default=False):
        console.print("[dim]Cancelled — no files removed.[/dim]")
        raise typer.Exit(code=0)

    removed = 0
    for s, path in existing:
        path.unlink(missing_ok=True)
        ok_path = not path.exists()
        if ok_path:
            removed += 1
            console.print(f"[green]✔[/green] Removed {path}")

    if shell == "bash" or any(s == "bash" for s, _ in existing):
        _clean_bashrc_source_line()

    console.print(f"\n[green]Done.[/green] Removed {removed} file(s). Restart the terminal or run [bold]exec zsh[/bold].")


def _clean_bashrc_source_line() -> None:
    rc = Path.home() / ".bashrc"
    if not rc.is_file():
        return
    needle = f"source '{Path.home() / '.bash_completions' / f'{PROG_NAME}.sh'}'"
    lines = rc.read_text(encoding="utf-8").splitlines()
    filtered = [ln for ln in lines if ln.strip() != needle]
    if len(filtered) != len(lines):
        rc.write_text("\n".join(filtered).rstrip() + "\n", encoding="utf-8")
        console.print(f"[green]✔[/green] Removed webaudit source line from {rc}")


@completion_app.command("status")
def completion_status() -> None:
    """Show whether webaudit Tab completion is installed and where."""
    rows = _scan_installed()
    table = Table(title="webaudit shell completion status")
    table.add_column("Shell")
    table.add_column("Path")
    table.add_column("Installed")

    any_installed = False
    for shell, path, exists in rows:
        status = "[green]yes[/green]" if exists else "[dim]no[/dim]"
        if exists:
            any_installed = True
        table.add_row(shell, str(path), status)
    console.print(table)

    console.print()
    if any_installed:
        console.print(
            "[bold]Installed[/bold] = Tab autocomplete file exists in your [bold]home directory[/bold]."
        )
        console.print(
            "[yellow]Removing .venv does not remove these files.[/yellow] "
            "Use [cyan]webaudit completion uninstall[/cyan]."
        )
    else:
        console.print("[dim]Not installed — optional. Run:[/dim] [cyan]webaudit completion install[/cyan]")

    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        console.print(f"\n[dim]Active Python venv:[/dim] {venv}")
        console.print("[dim](Separate from shell completion above.)[/dim]")


@completion_app.command("show")
def completion_show(
    shell: str | None = typer.Option(None, "--shell", "-s", help="Shell script to print."),
) -> None:
    """Print the completion script (same as legacy --show-completion)."""
    shell_name = _detect_shell(shell)
    script = get_completion_script(
        prog_name=PROG_NAME,
        complete_var=COMPLETE_VAR,
        shell=shell_name,
    )
    console.print(script)


def rewrite_legacy_completion_argv(argv: list[str]) -> list[str]:
    """Map ``--install-completion`` / ``--show-completion`` to ``completion`` subcommands."""
    if len(argv) <= 1:
        return argv
    prog, *rest = argv
    if "--install-completion" in rest:
        rest = [a for a in rest if a != "--install-completion"]
        return [prog, "completion", "install", *rest]
    if "--show-completion" in rest:
        rest = [a for a in rest if a != "--show-completion"]
        return [prog, "completion", "show", *rest]
    return argv

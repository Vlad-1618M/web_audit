"""Persist completed audit runs to disk.

What: Creates timestamped run directories and writes ``audit_run.json``.
Where: Called by ``webaudit/orchestrator.py`` at the end of every scan.
How: ``write_audit_run(run, output_dir=Path(...))`` → ``audit_logs/YYYYMMDD_HHMMSS_host/audit_run.json``.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from webaudit.models.run import AuditRun
from webaudit.render.reports import write_run_reports


def load_audit_run(path: Path) -> AuditRun:
    """Load ``audit_run.json`` (schema 2.0) into an ``AuditRun`` model."""
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    schema = data.get("schema_version", "2.0")
    if schema != "2.0":
        raise ValueError(f"Unsupported audit_run schema: {schema!r} (expected '2.0')")
    return AuditRun.model_validate(data)


def _slugify_host(url: str) -> str:
    host = urlparse(url).hostname or "unknown"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", host)


def run_directory(output_dir: Path, target_url: str, started_at: str) -> Path:
    ts = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    host = _slugify_host(target_url)
    path = output_dir / f"{stamp}_{host}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_audit_run(
    run: AuditRun,
    *,
    output_dir: Path,
    formats: list[str] | None = None,
    report_variant: str = "technical",
    report_theme: str = "dark",
) -> tuple[Path, dict[str, str], list[str]]:
    run_dir = run_directory(output_dir, run.meta.target_url, run.meta.started_at)
    wanted = formats or ["json"]
    report_paths, warnings = write_run_reports(
        run,
        run_dir,
        formats=wanted,
        report_variant=report_variant,
        report_theme=report_theme,
    )

    reports = dict(report_paths)
    reports["json"] = "audit_run.json"
    run.reports = reports

    out_file = run_dir / "audit_run.json"
    with out_file.open("w", encoding="utf-8") as fh:
        json.dump(run.to_json_dict(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    return out_file, {key: str(run_dir / name) for key, name in reports.items()}, warnings

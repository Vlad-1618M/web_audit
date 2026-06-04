"""Audit run orchestrator — wires collectors, analyzers, scoring, and storage.

What: ``run_audit()`` executes the scan pipeline and returns a populated ``AuditRun``.
Where: Called from ``webaudit/cli/main.py`` after config is loaded.
How: ``pipeline.run_pipeline()`` → score → write ``audit_logs/.../audit_run.json``.
      Add Stage 2 modules in ``webaudit/pipeline.py`` (see docs/implementation_tracker.md).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from webaudit.__version__ import __version__
from webaudit.config.settings import Settings
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun
from webaudit.pipeline import run_pipeline
from webaudit.scoring.engine import score_findings
from webaudit.storage.runs import write_audit_run

if TYPE_CHECKING:
    from webaudit.cli.scan_progress import ScanProgress


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid target URL: {url!r} (expected http(s)://host)")
    return url.rstrip("/")


def run_audit(settings: Settings, *, progress: ScanProgress | None = None) -> AuditRun:
    target_url = _validate_url(settings.target.url)
    started_at = _utc_now()

    if progress:
        progress.scan_start(target_url)

    pipeline = run_pipeline(settings, progress=progress)
    scores = score_findings(
        pipeline.findings,
        settings.scoring.hygiene_weights,
        scoring=settings.scoring,
    )

    if progress:
        progress.scoring(scores)

    framework_artifact = pipeline.artifacts.get("inventory", {}).get("framework", {})
    effective_framework = framework_artifact.get("effective_framework", settings.target.framework)
    if settings.target.framework not in {"auto", "unknown", ""}:
        effective_framework = settings.target.framework

    artifacts = AuditArtifacts(
        headers=pipeline.artifacts.get("headers", {}),
        dns=pipeline.artifacts.get("dns", {}),
        tls=pipeline.artifacts.get("tls", {}),
        policy=pipeline.artifacts.get("policy", {}),
        inventory=pipeline.artifacts.get("inventory", {}),
        plugins=pipeline.artifacts.get("plugins", {}),
        extensions=pipeline.artifacts.get("extensions", {}),
        vuln=pipeline.artifacts.get("vuln", {}),
        seo_surface=pipeline.artifacts.get("seo_surface", {}),
    )

    run = AuditRun(
        meta=AuditMeta(
            target_url=target_url,
            started_at=started_at,
            finished_at=_utc_now(),
            webaudit_version=__version__,
            framework=effective_framework,
        ),
        config_snapshot={
            "runtime": settings.runtime.model_dump(),
            "paths": settings.paths.model_dump(),
            "policy": settings.policy.model_dump(),
            "collectors": settings.collectors.model_dump(),
            "scoring": settings.scoring.model_dump(),
            "report": settings.report.model_dump(),
            "output": settings.output.model_dump(),
        },
        scores=scores,
        findings=pipeline.findings,
        artifacts=artifacts,
    )

    if progress:
        progress.writing_reports()

    json_path, report_paths, warnings = write_audit_run(
        run,
        output_dir=Path(settings.output.directory),
        formats=settings.output.formats,
        report_variant=settings.report.variant,
        report_theme=settings.report.theme,
    )
    run.reports = report_paths
    run.warnings = warnings
    return run


def audit_run_to_json(run: AuditRun) -> str:
    return json.dumps(run.to_json_dict(), indent=2, ensure_ascii=False)

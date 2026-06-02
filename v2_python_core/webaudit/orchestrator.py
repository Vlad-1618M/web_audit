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
from urllib.parse import urlparse

from webaudit.__version__ import __version__
from webaudit.config.settings import Settings
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun
from webaudit.pipeline import run_pipeline
from webaudit.scoring.engine import score_findings
from webaudit.storage.runs import write_audit_run


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid target URL: {url!r} (expected http(s)://host)")
    return url.rstrip("/")


def run_audit(settings: Settings) -> AuditRun:
    target_url = _validate_url(settings.target.url)
    started_at = _utc_now()

    pipeline = run_pipeline(settings)
    scores = score_findings(pipeline.findings, settings.scoring.hygiene_weights)

    artifacts = AuditArtifacts(
        headers=pipeline.artifacts.get("headers", {}),
        dns=pipeline.artifacts.get("dns", {}),
        tls=pipeline.artifacts.get("tls", {}),
        inventory=pipeline.artifacts.get("inventory", {}),
    )

    run = AuditRun(
        meta=AuditMeta(
            target_url=target_url,
            started_at=started_at,
            finished_at=_utc_now(),
            webaudit_version=__version__,
            framework=settings.target.framework,
        ),
        config_snapshot={
            "runtime": settings.runtime.model_dump(),
            "paths": settings.paths.model_dump(),
            "collectors": settings.collectors.model_dump(),
            "scoring": settings.scoring.model_dump(),
        },
        scores=scores,
        findings=pipeline.findings,
        artifacts=artifacts,
    )

    write_audit_run(run, output_dir=Path(settings.output.directory))
    return run


def audit_run_to_json(run: AuditRun) -> str:
    return json.dumps(run.to_json_dict(), indent=2, ensure_ascii=False)

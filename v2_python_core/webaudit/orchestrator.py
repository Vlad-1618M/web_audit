"""Audit run orchestrator — wires collectors, analyzers, scoring, and storage.
What: ``run_audit()`` executes the scan pipeline and returns a populated ``AuditRun``.
Where: Called from ``webaudit/cli/main.py`` after config is loaded.
How: Collect headers + DNS → analyze → score → write ``audit_logs/.../audit_run.json``.
      ``audit_run_to_json()`` serializes a run for ``--json`` CLI output.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from webaudit.__version__ import __version__
from webaudit.analyzers.dns import analyze_dns
from webaudit.analyzers.headers import analyze_headers
from webaudit.collectors.dns import collect_dns
from webaudit.collectors.headers import collect_headers
from webaudit.config.settings import Settings
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun
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

    header_probe = collect_headers(
        target_url,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    header_findings = analyze_headers(header_probe)

    dns_probe = None
    dns_findings = []
    if settings.collectors.dns.enabled:
        dns_probe = collect_dns(
            target_url,
            timeout_seconds=settings.runtime.timeout_seconds,
            check_spf=settings.collectors.dns.check_spf,
            check_dmarc=settings.collectors.dns.check_dmarc,
            check_caa=settings.collectors.dns.check_caa,
            check_dnssec=settings.collectors.dns.check_dnssec,
            check_aaaa=settings.collectors.dns.check_aaaa,
        )
        dns_findings = analyze_dns(dns_probe, settings.collectors.dns)

    findings = header_findings + dns_findings
    scores = score_findings(findings, settings.scoring.hygiene_weights)

    artifacts = AuditArtifacts(
        headers=header_probe.to_artifact(),
        dns=dns_probe.to_artifact() if dns_probe else {},
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
            "collectors": settings.collectors.model_dump(),
            "scoring": settings.scoring.model_dump(),
        },
        scores=scores,
        findings=findings,
        artifacts=artifacts,
    )

    write_audit_run(run, output_dir=Path(settings.output.directory))
    return run


def audit_run_to_json(run: AuditRun) -> str:
    return json.dumps(run.to_json_dict(), indent=2, ensure_ascii=False)

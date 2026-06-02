"""Scan pipeline registry — ordered collector/analyzer steps for orchestrator.

What: ``run_pipeline()`` runs all registered scan steps and returns findings + artifacts.
Where: Called exclusively from ``orchestrator.run_audit()`` — add Stage 2 modules here.
How: Each step is optional (config-gated). Append findings; merge artifact dicts by key.
      Do not add scoring or HTTP calls inside analyzers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from webaudit.analyzers.dns import analyze_dns
from webaudit.analyzers.headers import analyze_headers
from webaudit.collectors.dns import collect_dns
from webaudit.collectors.headers import collect_headers
from webaudit.config.settings import Settings
from webaudit.models.finding import Finding


@dataclass
class PipelineResult:
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)


def _step_headers(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    probe = collect_headers(
        settings.target.url,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    return analyze_headers(probe), {"headers": probe.to_artifact()}


def _step_dns(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.dns.enabled:
        return [], {}
    probe = collect_dns(
        settings.target.url,
        timeout_seconds=settings.runtime.timeout_seconds,
        check_spf=settings.collectors.dns.check_spf,
        check_dmarc=settings.collectors.dns.check_dmarc,
        check_caa=settings.collectors.dns.check_caa,
        check_dnssec=settings.collectors.dns.check_dnssec,
        check_aaaa=settings.collectors.dns.check_aaaa,
    )
    return analyze_dns(probe, settings.collectors.dns), {"dns": probe.to_artifact()}


# Stage 2+: register new steps here in planned order (see docs/implementation_tracker.md)
# _step_paths, _step_tls, _step_policy, ...
_PIPELINE: tuple[Callable[[Settings], tuple[list[Finding], dict[str, dict[str, Any]]]], ...] = (
    _step_headers,
    _step_dns,
)


def run_pipeline(settings: Settings) -> PipelineResult:
    """Execute all pipeline steps; merge findings and artifact fragments."""
    result = PipelineResult()
    for step in _PIPELINE:
        findings, artifact_parts = step(settings)
        result.findings.extend(findings)
        result.artifacts.update(artifact_parts)
    return result

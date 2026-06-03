"""OpenAPI/Swagger analyzer — exposed API documentation findings.

What: ``analyze_openapi()`` flags publicly reachable OpenAPI/Swagger specs.
Where: ``pipeline._step_api`` after ``collect_api_surface()``.
How: Detected spec → VERIFY MEDIUM; unscored by default (informational hygiene).
"""

from __future__ import annotations

from webaudit.collectors.api import ApiProbeResult, OpenApiProbeEntry
from webaudit.config.settings import ApiCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_openapi(probe: ApiProbeResult, settings: ApiCollectorSettings) -> list[Finding]:
    if not settings.enabled:
        return []

    findings: list[Finding] = []
    for entry in probe.openapi_probes:
        if entry.openapi_detected:
            findings.append(_exposed_spec_finding(entry))
    return findings


def _exposed_spec_finding(entry: OpenApiProbeEntry) -> Finding:
    title_part = f" ({entry.title})" if entry.title else ""
    version_part = f" v{entry.version}" if entry.version else ""
    return Finding.from_check(
        category="API",
        item=entry.path,
        status="EXPOSED",
        severity=Severity.MEDIUM,
        detail=f"OpenAPI/Swagger documentation exposed at {entry.path}{title_part}{version_part}",
        class_=FindingClass.VERIFY,
        scored=False,
        evidence={
            "path": entry.path,
            "title": entry.title,
            "version": entry.version,
            "status_code": entry.status_code,
        },
    )

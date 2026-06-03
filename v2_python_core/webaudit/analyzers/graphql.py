"""GraphQL analyzer — introspection exposure findings.

What: ``analyze_graphql()`` flags public GraphQL introspection when enabled.
Where: ``pipeline._step_api`` after ``collect_api_surface()``.
How: Introspection enabled → VERIFY HIGH; endpoint reachable without introspection → INFO.
"""

from __future__ import annotations

from webaudit.collectors.api import ApiProbeResult, GraphqlProbeEntry
from webaudit.config.settings import ApiCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_graphql(probe: ApiProbeResult, settings: ApiCollectorSettings) -> list[Finding]:
    if not settings.enabled or not settings.graphql_probe:
        return []

    findings: list[Finding] = []
    introspection_paths: list[str] = []
    reachable_paths: list[str] = []

    for entry in probe.graphql_probes:
        if entry.introspection_enabled:
            introspection_paths.append(entry.path)
            findings.append(_introspection_finding(entry))
        elif entry.status_code == 200 and not entry.error:
            reachable_paths.append(entry.path)

    if not introspection_paths and reachable_paths:
        findings.append(
            Finding.from_check(
                category="API",
                item="GraphQL",
                status="REACHABLE",
                severity=Severity.INFO,
                detail=f"GraphQL endpoint reachable at {reachable_paths[0]} (introspection not confirmed open)",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"paths": reachable_paths[:5]},
            )
        )

    return findings


def _introspection_finding(entry: GraphqlProbeEntry) -> Finding:
    return Finding.from_check(
        category="API",
        item=entry.path,
        status="INTROSPECTION",
        severity=Severity.HIGH,
        detail=f"GraphQL introspection appears enabled at {entry.path} — schema may be publicly enumerable",
        class_=FindingClass.VERIFY,
        scored=False,
        evidence={"path": entry.path, "status_code": entry.status_code},
    )

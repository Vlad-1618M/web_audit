"""Tests for baseline diff between audit runs."""

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditMeta, AuditRun, AuditScores
from webaudit.scoring.diff import diff_audit_runs


def _run(
    *,
    hygiene: int,
    exposure: int,
    findings: list[Finding],
    started_at: str = "2026-01-01T00:00:00+00:00",
) -> AuditRun:
    return AuditRun(
        meta=AuditMeta(
            target_url="https://example.com",
            started_at=started_at,
            finished_at=started_at,
            webaudit_version="2.0.0b1",
        ),
        scores=AuditScores(hygiene=hygiene, exposure=exposure, verdict="PASS"),
        findings=findings,
    )


def test_new_open_path_is_regression():
    baseline = _run(hygiene=90, exposure=100, findings=[])
    current = _run(
        hygiene=90,
        exposure=75,
        findings=[
            Finding.from_check(
                category="PATHS",
                item=".env",
                status="OPEN",
                severity=Severity.CRITICAL,
                class_=FindingClass.ACTION,
                scored=True,
            )
        ],
        started_at="2026-02-01T00:00:00+00:00",
    )
    diff = diff_audit_runs(baseline, current)
    kinds = {e.kind for e in diff.entries}
    assert "REGRESSION" in kinds
    assert any(e.category == "PATHS" for e in diff.entries)


def test_resolved_action_finding():
    finding = Finding.from_check(
        category="HEADERS",
        item="Content-Security-Policy",
        status="MISSING",
        severity=Severity.HIGH,
        class_=FindingClass.ACTION,
        scored=True,
    )
    baseline = _run(hygiene=90, exposure=100, findings=[finding])
    current = _run(hygiene=100, exposure=100, findings=[], started_at="2026-02-01T00:00:00+00:00")
    diff = diff_audit_runs(baseline, current)
    assert any(e.kind == "RESOLVED" and e.item == "Content-Security-Policy" for e in diff.entries)

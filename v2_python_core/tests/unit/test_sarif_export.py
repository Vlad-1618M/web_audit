"""Tests for SARIF export."""
from webaudit.export.sarif import audit_run_to_sarif
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditMeta, AuditRun, AuditScores


def _run_with_findings(findings):
    return AuditRun(
        meta=AuditMeta(
            target_url="https://example.com",
            started_at="2026-05-29T12:00:00+00:00",
            finished_at="2026-05-29T12:00:05+00:00",
            webaudit_version="2.1.0b3",
            framework="wordpress",
        ),
        scores=AuditScores(hygiene=75, exposure=100, verdict="NEEDS_ATTENTION"),
        findings=findings,
    )


def test_sarif_includes_scored_action_findings():
    """SARIF results include scored ACTION findings."""
    findings = [
        Finding.from_check(
            category="PLUGIN_CVE",
            item="elementor:CVE-2024-10453",
            status="MATCH",
            severity=Severity.MEDIUM,
            detail="elementor 3.25.9 matches CVE-2024-10453",
            class_=FindingClass.ACTION,
            scored=True,
            evidence={"cve_id": "CVE-2024-10453"},
        )
    ]
    sarif = audit_run_to_sarif(_run_with_findings(findings))
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Web Audit"
    assert len(run["results"]) == 1
    assert run["results"][0]["ruleId"] == "webaudit/plugin_cve/match"
    assert run["results"][0]["level"] == "warning"


def test_sarif_skips_verify_by_default():
    """VERIFY findings are omitted unless include_verify=True."""
    findings = [
        Finding.from_check(
            category="PLUGIN_VERIFY",
            item="elementor-pro",
            status="PREMIUM_OR_UNVERIFIABLE",
            severity=Severity.INFO,
            class_=FindingClass.VERIFY,
            scored=False,
        )
    ]
    sarif = audit_run_to_sarif(_run_with_findings(findings))
    assert sarif["runs"][0]["results"] == []

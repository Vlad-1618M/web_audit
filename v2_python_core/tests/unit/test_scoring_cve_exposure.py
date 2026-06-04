"""Tests for unauth CVE exposure scoring."""
from webaudit.config.settings import HygieneWeights, ScoringSettings
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.scoring.engine import score_findings


def test_unauth_critical_cve_reduces_exposure():
    """Unauthenticated critical PLUGIN_CVE deducts from Exposure."""
    findings = [
        Finding.from_check(
            category="PLUGIN_CVE",
            item="really-simple-ssl:CVE-2026-32461",
            status="MATCH",
            severity=Severity.CRITICAL,
            class_=FindingClass.ACTION,
            scored=True,
            evidence={"auth_required": "none"},
        )
    ]
    scores = score_findings(findings, HygieneWeights(), scoring=ScoringSettings())
    assert scores.exposure == 75

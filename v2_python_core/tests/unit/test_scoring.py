"""Tests for ``webaudit.scoring.engine`` — Hygiene/Exposure/Verdict math.

What: Regression test for the worked example in ``docs/scoring.md``.
Where: Run via ``pytest`` whenever finding or weight logic changes.
How: ``pytest tests/unit/test_scoring.py``.
"""

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.scoring.engine import score_findings
from webaudit.config.settings import HygieneWeights


def test_worked_example_from_docs():
    findings = [
        Finding.from_check(
            category="HEADERS",
            item="Content-Security-Policy",
            status="MISSING",
            severity=Severity.HIGH,
        ),
        Finding.from_check(
            category="HEADERS",
            item="X-Frame-Options",
            status="MISSING",
            severity=Severity.MEDIUM,
        ),
        Finding.from_check(
            category="DNS",
            item="DMARC",
            status="MISSING",
            severity=Severity.MEDIUM,
        ),
    ]
    scores = score_findings(findings, HygieneWeights())
    assert scores.hygiene == 82
    assert scores.exposure == 100
    assert scores.verdict == "NEEDS_ATTENTION"

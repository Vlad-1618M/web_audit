"""Tests for dashboard focus pie chart data."""

from webaudit.models.finding import Finding, Severity
from webaudit.models.run import AuditScores
from webaudit.render.focus_pie import build_focus_pie_slices, focus_pie_conic_gradient


def test_focus_pie_slices_cover_full_circle():
    scores = AuditScores(hygiene=81, exposure=100, verdict="NEEDS_ATTENTION")
    findings = [
        Finding.from_check(
            category="SEO_SURFACE",
            item="meta description",
            status="MISSING",
            severity=Severity.INFO,
        ),
    ]
    slices = build_focus_pie_slices(scores, findings)
    assert len(slices) == 3
    assert slices[0]["display"] == "81"
    assert slices[1]["display"] == "100"
    assert slices[2]["display"] == "1"
    assert slices[-1]["end_pct"] == 100
    gradient = focus_pie_conic_gradient(slices)
    assert "conic-gradient" in gradient
    assert "#ffc14d" in gradient

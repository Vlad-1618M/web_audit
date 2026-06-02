"""Tests for discoverability / SEO surface executive block."""

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.render.discoverability_display import build_discoverability_section


def test_discoverability_empty_state():
    section = build_discoverability_section([])
    assert section["count"] == 0
    assert section["has_rows"] is False
    assert "No discoverability flags" in section["summary"]


def test_discoverability_lists_seo_findings():
    findings = [
        Finding.from_check(
            category="SEO_SURFACE",
            item="Meta description",
            status="MISSING",
            severity=Severity.INFO,
            detail="No meta description on homepage",
            class_=FindingClass.INFO,
            scored=False,
        ),
        Finding.from_check(
            category="SEO_SURFACE",
            item="Meta robots",
            status="NOINDEX",
            severity=Severity.INFO,
            detail="Homepage has noindex",
            class_=FindingClass.VERIFY,
            scored=False,
        ),
    ]
    section = build_discoverability_section(findings)
    assert section["count"] == 2
    assert section["info_count"] == 1
    assert section["verify_count"] == 1
    assert section["rows"][0]["item"] == "Meta description"
    assert section["rows"][1]["tone"] == "verify"

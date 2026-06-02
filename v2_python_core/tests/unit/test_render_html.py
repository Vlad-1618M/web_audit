"""Tests for HTML report rendering."""

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html


def _sample_run() -> AuditRun:
    return AuditRun(
        meta=AuditMeta(
            target_url="https://example.com",
            started_at="2026-05-29T12:00:00+00:00",
            finished_at="2026-05-29T12:00:05+00:00",
            webaudit_version="2.0.0a1",
            framework="django",
        ),
        scores=AuditScores(hygiene=78, exposure=100, verdict="NEEDS_ATTENTION"),
        findings=[
            Finding.from_check(
                category="HEADERS",
                item="Content-Security-Policy",
                status="MISSING",
                severity=Severity.HIGH,
            ),
            Finding.from_check(
                category="DNS",
                item="DMARC",
                status="MISSING",
                severity=Severity.MEDIUM,
            ),
        ],
        artifacts=AuditArtifacts(
            dns={"records": {"spf": "v=spf1 -all", "dmarc": None}},
            tls={
                "certificate": {"subject": "CN=example.com", "days_left": 90},
                "versions": [{"version": "1.3", "supported": True}],
            },
            inventory={
                "framework": {"confidence": "high", "cdn": "Cloudflare"},
                "paths": {
                    "probe_count": 2,
                    "paths": [{"path": "/.env", "final_status": 404, "note": "NOT_FOUND"}],
                },
            },
        ),
    )


def test_build_report_context_groups_action_findings():
    ctx = build_report_context(_sample_run(), variant="technical", theme="dark")
    assert len(ctx["action_findings"]) == 2
    assert ctx["verdict_label"] == "Needs attention"


def test_render_technical_html_contains_target_and_findings():
    html = render_html(_sample_run(), variant="technical")
    assert "https://example.com" in html
    assert "Content-Security-Policy" in html
    assert "NEEDS_ATTENTION" in html
    assert 'href="report.css"' in html


def test_render_executive_html():
    html = render_html(_sample_run(), variant="executive")
    assert "Website Security Snapshot" in html
    assert "Configuration score" in html

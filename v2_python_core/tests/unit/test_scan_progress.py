"""Tests for scan verbosity and progress summaries."""

from __future__ import annotations

from webaudit.cli.scan_progress import (
    Verbosity,
    resolve_verbosity,
    step_enabled,
    summarize_step,
)
from webaudit.config.settings import Settings
from webaudit.models.finding import Finding, Severity


def test_resolve_verbosity_levels():
    assert resolve_verbosity(verbose=False, quiet=False) == Verbosity.NORMAL
    assert resolve_verbosity(verbose=True, quiet=False) == Verbosity.VERBOSE
    assert resolve_verbosity(verbose=False, quiet=True) == Verbosity.QUIET


def test_resolve_verbosity_conflict():
    try:
        resolve_verbosity(verbose=True, quiet=True)
    except ValueError as exc:
        assert "not both" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_step_enabled_paths():
    settings = Settings()
    settings.paths.enabled = False
    assert step_enabled("_step_paths", settings) is False
    assert step_enabled("_step_headers", settings) is True
    assert step_enabled("_step_js", settings) is False
    settings.collectors.js.enabled = True
    assert step_enabled("_step_js", settings) is True
    assert step_enabled("_step_links", settings) is False
    settings.collectors.seo_surface.check_broken_links = True
    assert step_enabled("_step_links", settings) is True


def test_summarize_headers_step():
    findings = [
        Finding.from_check(
            category="HEADERS",
            item="Content-Security-Policy",
            status="MISSING",
            severity=Severity.HIGH,
        )
    ]
    summary, details = summarize_step(
        "_step_headers",
        findings,
        {
            "headers": {
                "status_code": 200,
                "headers": {"Strict-Transport-Security": "max-age=31536000"},
            }
        },
    )
    assert "HTTP 200" in summary
    assert "1 findings" in summary
    assert details


def test_summarize_paths_verbose_lists_each_probe():
    probes = [
        {"path": "/.env", "final_status": 404, "note": "NOT_FOUND"},
        {"path": "/robots.txt", "final_status": 200, "note": "OPEN"},
    ]
    summary, details = summarize_step(
        "_step_paths",
        [],
        {"inventory": {"paths": {"probe_count": 2, "paths": probes}}},
        verbose=True,
    )
    assert "2 probes" in summary
    assert any("exposed: /robots.txt" in line for line in details)
    assert any("[dark_orange]/.env[/dark_orange]" in line for line in details)
    assert any("[dark_orange]/robots.txt[/dark_orange]" in line for line in details)
    assert sum(1 for line in details if "[dark_orange]" in line) == 2


def test_summarize_paths_normal_hides_probe_list():
    probes = [{"path": "/.env", "final_status": 404, "note": "NOT_FOUND"}]
    _summary, details = summarize_step(
        "_step_paths",
        [],
        {"inventory": {"paths": {"probe_count": 1, "paths": probes}}},
        verbose=False,
    )
    assert not any("[dark_orange]" in line for line in details)


def test_summarize_policy_step_string_artifacts():
    findings = []
    summary, details = summarize_step(
        "_step_policy",
        findings,
        {
            "policy": {
                "hsts_detail": "max-age=31536000, includeSubDomains (raw: max-age=31536000)",
                "csp_detail": "default-src 'self'",
            }
        },
    )
    assert "HSTS max-age=31536000" in summary
    assert "CSP yes" in summary
    assert details

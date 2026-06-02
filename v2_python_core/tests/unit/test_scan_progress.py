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

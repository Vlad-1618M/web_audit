"""Tests for ``webaudit.analyzers.paths`` — exposure and verify findings."""

from webaudit.analyzers.paths import analyze_paths
from webaudit.collectors.paths import PathProbeEntry, PathsProbeResult
from webaudit.config.settings import PathsSettings
from webaudit.models.finding import FindingClass, Severity


def _probe(*entries: tuple[str, int, int, str]) -> PathsProbeResult:
    return PathsProbeResult(
        target_url="https://example.com",
        probes=[
            PathProbeEntry(path=p, raw_status=raw, final_status=final, note=note)
            for p, raw, final, note in entries
        ],
    )


def test_sensitive_open_is_scored_action():
    findings = analyze_paths(
        _probe(("/.env", 200, 200, "OPEN")),
        framework="auto",
        paths_settings=PathsSettings(),
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.category == "PATHS"
    assert f.item == ".env"
    assert f.status == "OPEN"
    assert f.severity == Severity.CRITICAL
    assert f.class_ == FindingClass.ACTION
    assert f.scored is True


def test_sensitive_server_error_is_leaking():
    findings = analyze_paths(
        _probe(("/wp-config.php", 500, 500, "SERVER_ERROR")),
        framework="auto",
        paths_settings=PathsSettings(),
    )
    assert findings[0].status == "LEAKING"
    assert findings[0].class_ == FindingClass.ACTION
    assert findings[0].scored is True


def test_not_found_emits_no_finding():
    findings = analyze_paths(
        _probe(("/.env", 404, 404, "NOT_FOUND")),
        framework="auto",
        paths_settings=PathsSettings(),
    )
    assert findings == []


def test_robots_open_is_expected():
    findings = analyze_paths(
        _probe(("/robots.txt", 200, 200, "OPEN")),
        framework="auto",
        paths_settings=PathsSettings(),
    )
    assert len(findings) == 1
    assert findings[0].class_ == FindingClass.EXPECTED
    assert findings[0].scored is False


def test_unexpected_open_is_verify_only():
    findings = analyze_paths(
        _probe(("/readme.html", 200, 200, "OPEN")),
        framework="auto",
        paths_settings=PathsSettings(),
    )
    assert len(findings) == 1
    assert findings[0].class_ == FindingClass.VERIFY
    assert findings[0].scored is False

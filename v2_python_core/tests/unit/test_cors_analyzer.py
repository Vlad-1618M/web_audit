"""Tests for ``webaudit.analyzers.cors``."""

from webaudit.analyzers.cors import analyze_cors
from webaudit.collectors.cors import CorsProbeEntry, CorsProbeResult
from webaudit.config.settings import CorsCollectorSettings
from webaudit.models.finding import Severity


def test_cors_wildcard_high():
    probe = CorsProbeResult(
        target_url="https://example.com",
        origin_sent="https://evil.example.com",
        probes=[CorsProbeEntry(path="/api/", status_code=200, acao="*")],
    )
    findings = analyze_cors(probe, CorsCollectorSettings())
    assert findings[0].status == "WILDCARD"
    assert findings[0].severity == Severity.HIGH
    assert findings[0].scored is True


def test_cors_reflected_critical():
    probe = CorsProbeResult(
        target_url="https://example.com",
        origin_sent="https://evil.example.com",
        probes=[
            CorsProbeEntry(
                path="/api/v1/",
                status_code=200,
                acao="https://evil.example.com",
            )
        ],
    )
    findings = analyze_cors(probe, CorsCollectorSettings())
    assert findings[0].status == "REFLECTED"
    assert findings[0].severity == Severity.CRITICAL


def test_cors_none_on_paths():
    probe = CorsProbeResult(
        target_url="https://example.com",
        origin_sent="https://evil.example.com",
        probes=[CorsProbeEntry(path="/api/", status_code=404, acao=None)],
    )
    findings = analyze_cors(probe, CorsCollectorSettings())
    assert findings[0].item == "API paths"
    assert findings[0].status == "NONE"

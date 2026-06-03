"""Tests for ``webaudit.pipeline`` — scan step registry (mocked I/O)."""

from unittest.mock import MagicMock, patch

import dns.resolver
import pytest

from webaudit.config.settings import Settings, TargetSettings
from webaudit.pipeline import run_pipeline


def _disable_network_heavy_collectors(settings: Settings) -> None:
    settings.paths.enabled = False
    settings.collectors.tls.enabled = False
    settings.collectors.cookies.enabled = False
    settings.collectors.artifacts.enabled = False
    settings.collectors.rate_limit.enabled = False
    settings.collectors.cors.enabled = False
    settings.collectors.framework.enabled = False
    settings.collectors.html.enabled = False
    settings.collectors.js.enabled = False
    settings.collectors.api.enabled = False
    settings.collectors.seo_surface.check_broken_links = False


def _txt_answer(*strings: str) -> MagicMock:
    answer = MagicMock()
    answer.strings = [s.encode() if isinstance(s, str) else s for s in strings]
    return answer


@patch("webaudit.collectors.dns.dns.resolver.Resolver")
def test_pipeline_merges_headers_and_dns(mock_resolver_cls, httpx_mock):
    httpx_mock.add_response(
        method="HEAD",
        url="https://example.com",
        headers={"Strict-Transport-Security": "max-age=31536000"},
    )

    resolver = MagicMock()
    mock_resolver_cls.return_value = resolver

    def resolve_side_effect(name, rdtype):
        if rdtype == "TXT" and name == "example.com":
            return [_txt_answer("v=spf1 -all")]
        if rdtype == "TXT" and name == "_dmarc.example.com":
            return [_txt_answer("v=DMARC1; p=reject")]
        if rdtype == "CAA":
            return [MagicMock(to_text=lambda: '0 issue "letsencrypt.org"')]
        if rdtype == "AAAA":
            return [MagicMock(to_text=lambda: "2001:db8::1")]
        if rdtype == "DNSKEY":
            return [MagicMock(to_text=lambda: "257 3 13 abc")]
        raise dns.resolver.NoAnswer

    resolver.resolve.side_effect = resolve_side_effect

    settings = Settings(target=TargetSettings(url="https://example.com"))
    _disable_network_heavy_collectors(settings)
    result = run_pipeline(settings)

    assert len(result.findings) > 0
    assert "headers" in result.artifacts
    assert "dns" in result.artifacts
    assert result.artifacts["headers"]["headers"].get("strict-transport-security")
    assert "policy" in result.artifacts


def test_pipeline_dns_disabled(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com", headers={})

    settings = Settings(
        target=TargetSettings(url="https://example.com"),
    )
    settings.collectors.dns.enabled = False
    _disable_network_heavy_collectors(settings)

    result = run_pipeline(settings)
    assert "headers" in result.artifacts
    assert "dns" not in result.artifacts


def test_pipeline_paths_enabled(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com", headers={})
    httpx_mock.add_response(method="GET", url="https://example.com/.env", status_code=404)
    httpx_mock.add_response(method="GET", url="https://example.com/.env", status_code=404)

    settings = Settings(target=TargetSettings(url="https://example.com"))
    settings.collectors.dns.enabled = False
    settings.collectors.tls.enabled = False
    settings.collectors.cookies.enabled = False
    settings.collectors.artifacts.enabled = False
    settings.collectors.rate_limit.enabled = False
    settings.collectors.cors.enabled = False
    settings.collectors.framework.enabled = False
    settings.collectors.html.enabled = False
    settings.paths.sensitive_builtin = False
    settings.paths.extra_paths = ["/.env"]

    result = run_pipeline(settings)
    assert "inventory" in result.artifacts
    assert "paths" in result.artifacts["inventory"]
    assert result.artifacts["inventory"]["paths"]["probe_count"] == 1


@patch("webaudit.pipeline.collect_tls")
def test_pipeline_tls_enabled(mock_collect_tls, httpx_mock):
    from webaudit.collectors.tls import TlsCertificateInfo, TlsProbeResult, TlsVersionResult

    httpx_mock.add_response(method="HEAD", url="https://example.com", headers={})
    mock_collect_tls.return_value = TlsProbeResult(
        target_url="https://example.com",
        host="example.com",
        port=443,
        versions=[TlsVersionResult(version="1.2", supported=True, negotiated="TLSv1.2")],
        certificate=TlsCertificateInfo(
            subject="CN=example.com",
            issuer="CN=CA",
            not_after="2099-01-01T00:00:00+00:00",
            days_left=9000,
            chain_length=2,
        ),
    )

    settings = Settings(target=TargetSettings(url="https://example.com"))
    settings.collectors.dns.enabled = False
    settings.collectors.cookies.enabled = False
    settings.collectors.artifacts.enabled = False
    settings.collectors.rate_limit.enabled = False
    settings.collectors.cors.enabled = False
    settings.collectors.framework.enabled = False
    settings.collectors.html.enabled = False
    settings.paths.enabled = False

    result = run_pipeline(settings)
    assert "tls" in result.artifacts
    assert result.artifacts["tls"]["host"] == "example.com"
    assert any(f.category == "TLS" for f in result.findings)

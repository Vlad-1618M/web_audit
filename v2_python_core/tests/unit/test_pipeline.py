"""Tests for ``webaudit.pipeline`` — scan step registry (mocked I/O)."""

from unittest.mock import MagicMock, patch

import dns.resolver
import pytest

from webaudit.config.settings import Settings, TargetSettings
from webaudit.pipeline import run_pipeline


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
    result = run_pipeline(settings)

    assert len(result.findings) > 0
    assert "headers" in result.artifacts
    assert "dns" in result.artifacts
    assert result.artifacts["headers"]["headers"].get("strict-transport-security")


def test_pipeline_dns_disabled(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com", headers={})

    settings = Settings(
        target=TargetSettings(url="https://example.com"),
    )
    settings.collectors.dns.enabled = False

    result = run_pipeline(settings)
    assert "headers" in result.artifacts
    assert "dns" not in result.artifacts

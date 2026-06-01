"""Tests for ``webaudit.collectors.dns`` — DNS query wiring.

What: Verifies SPF/DMARC/CAA/AAAA/DNSKEY resolution with mocked ``dns.resolver.Resolver``.
Where: Run via ``pytest``; no live DNS.
How: ``pytest tests/unit/test_dns_collector.py``.
"""

from unittest.mock import MagicMock, patch

import dns.resolver

from webaudit.collectors.dns import collect_dns


def _txt_answer(*strings: str) -> MagicMock:
    answer = MagicMock()
    answer.strings = [s.encode() if isinstance(s, str) else s for s in strings]
    return answer


@patch("webaudit.collectors.dns.dns.resolver.Resolver")
def test_collect_dns_spf_dmarc(mock_resolver_cls):
    resolver = MagicMock()
    mock_resolver_cls.return_value = resolver

    def resolve_side_effect(name, rdtype):
        if rdtype == "TXT" and name == "example.com":
            return [_txt_answer("v=spf1 include:_spf.google.com ~all")]
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

    result = collect_dns("https://www.example.com", timeout_seconds=5)
    assert result.domain == "example.com"
    assert result.records["spf"].startswith("v=spf1")
    assert result.records["dmarc"].startswith("v=DMARC1")
    assert result.records["dnssec"] == "DNSKEY_PRESENT"

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

@patch('webaudit.collectors.asn.lookup_asns_for_ips', return_value=[])
@patch('webaudit.collectors.net_tools.optional_whois_domain', return_value={})
@patch('webaudit.collectors.dns.dns.resolver.Resolver')
def test_collect_dns_spf_dmarc(mock_resolver_cls, _mock_whois, _mock_asn):
    """Ensures Collect DNS Spf Dmarc."""
    resolver = MagicMock()
    mock_resolver_cls.return_value = resolver

    def resolve_side_effect(name, rdtype):
        if rdtype == 'TXT' and name == 'example.com':
            return [_txt_answer('v=spf1 include:_spf.google.com ~all')]
        if rdtype == 'TXT' and name == '_dmarc.example.com':
            return [_txt_answer('v=DMARC1; p=reject')]
        if rdtype == 'CAA':
            return [MagicMock(to_text=lambda: '0 issue "letsencrypt.org"')]
        if rdtype == 'A':
            return [MagicMock(to_text=lambda: '93.184.216.34')]
        if rdtype == 'AAAA':
            return [MagicMock(to_text=lambda: '2001:db8::1')]
        if rdtype == 'MX':
            return [MagicMock(to_text=lambda: '10 mail.example.com.')]
        if rdtype == 'NS':
            return [MagicMock(to_text=lambda: 'ns1.example.com.')]
        if rdtype == 'DNSKEY':
            return [MagicMock(to_text=lambda: '257 3 13 abc')]
        raise dns.resolver.NoAnswer
    resolver.resolve.side_effect = resolve_side_effect
    result = collect_dns('https://www.example.com', timeout_seconds=5)
    assert result.domain == 'example.com'
    assert result.records['spf'].startswith('v=spf1')
    assert result.records['dmarc'].startswith('v=DMARC1')
    assert result.records['a'] == ['93.184.216.34']
    assert result.records['mx']
    assert result.records['ns']
    assert result.records['dnssec'] == 'DNSKEY_PRESENT'
    assert 'dig' in result.net_tools

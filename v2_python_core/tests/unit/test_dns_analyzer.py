"""Tests for ``webaudit.analyzers.dns`` — DNS finding severity and class.

What: Verifies DMARC missing is scored ACTION MEDIUM; DNSSEC stays INFO/unscored.
Where: Run via ``pytest``; no live DNS — uses synthetic ``DnsProbeResult`` fixtures.
How: ``pytest tests/unit/test_dns_analyzer.py``.
"""
from webaudit.analyzers.dns import analyze_dns
from webaudit.collectors.dns import DnsProbeResult
from webaudit.config.settings import DnsCollectorSettings
from webaudit.models.finding import FindingClass, Severity

def test_dmarc_missing_scored():
    """Ensures Dmarc Missing Scored."""
    probe = DnsProbeResult(domain='example.com', records={'spf': 'v=spf1 -all', 'dmarc': None})
    findings = analyze_dns(probe, DnsCollectorSettings())
    dmarc = next((f for f in findings if f.item == 'DMARC'))
    assert dmarc.status == 'MISSING'
    assert dmarc.severity == Severity.MEDIUM
    assert dmarc.class_ == FindingClass.ACTION
    assert dmarc.scored is True

def test_dnssec_info_only():
    """Ensures Dnssec Info Only."""
    probe = DnsProbeResult(domain='example.com', records={'dnssec': 'UNSIGNED'})
    findings = analyze_dns(probe, DnsCollectorSettings())
    dnssec = next((f for f in findings if f.item == 'DNSSEC'))
    assert dnssec.scored is False
    assert dnssec.class_ == FindingClass.INFO

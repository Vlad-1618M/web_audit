"""Tests for ``webaudit.analyzers.tls`` — version policy and certificate expiry."""

from webaudit.analyzers.tls import analyze_tls
from webaudit.collectors.tls import TlsCertificateInfo, TlsProbeResult, TlsVersionResult
from webaudit.config.settings import TlsCollectorSettings
from webaudit.models.finding import FindingClass, Severity


def _probe(**kwargs) -> TlsProbeResult:
    defaults = {
        "target_url": "https://example.com",
        "host": "example.com",
        "port": 443,
    }
    defaults.update(kwargs)
    return TlsProbeResult(**defaults)


def test_tls_11_accepted_is_scored_action():
    probe = _probe(
        versions=[
            TlsVersionResult(version="1.0", supported=False),
            TlsVersionResult(version="1.1", supported=True, negotiated="TLSv1.1"),
            TlsVersionResult(version="1.2", supported=True, negotiated="TLSv1.2"),
            TlsVersionResult(version="1.3", supported=True, negotiated="TLSv1.3"),
        ]
    )
    findings = analyze_tls(probe, TlsCollectorSettings())
    tls11 = next(f for f in findings if f.item == "TLS 1.1")
    assert tls11.status == "ACCEPTED"
    assert tls11.severity == Severity.MEDIUM
    assert tls11.class_ == FindingClass.ACTION
    assert tls11.scored is True


def test_expired_cert_is_critical():
    probe = _probe(
        versions=[],
        certificate=TlsCertificateInfo(
            subject="CN=example.com",
            issuer="CN=Test CA",
            not_after="2020-01-01T00:00:00+00:00",
            days_left=-100,
            chain_length=2,
        ),
    )
    findings = analyze_tls(probe, TlsCollectorSettings())
    expiry = next(f for f in findings if f.item == "Certificate expiry")
    assert expiry.status == "EXPIRED"
    assert expiry.severity == Severity.CRITICAL
    assert expiry.scored is True


def test_http_skipped_probe_emits_nothing():
    probe = TlsProbeResult(target_url="http://example.com", skipped=True, skip_reason="not https")
    assert analyze_tls(probe, TlsCollectorSettings()) == []


def test_chain_info_when_enabled():
    probe = _probe(
        versions=[],
        certificate=TlsCertificateInfo(
            subject="CN=example.com",
            issuer="CN=Test CA",
            not_after="2099-01-01T00:00:00+00:00",
            days_left=9000,
            chain_length=3,
            san=["example.com", "www.example.com"],
        ),
    )
    findings = analyze_tls(probe, TlsCollectorSettings(check_deprecated_versions=False))
    chain = next(f for f in findings if f.item == "Certificate chain")
    assert chain.scored is False
    assert "3 certificate" in chain.detail

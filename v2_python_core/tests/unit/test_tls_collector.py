"""Tests for ``webaudit.collectors.tls`` — target parsing and injected probes."""
import ssl
from webaudit.collectors.tls import TlsCertificateInfo, TlsProbeResult, collect_tls, parse_tls_target

def test_parse_tls_target_https_default_port():
    """Ensures Parse TLS Target Https Default Port."""
    assert parse_tls_target('https://example.com/path') == ('example.com', 443)

def test_parse_tls_target_http_returns_none():
    """Ensures Parse TLS Target HTTP Returns None."""
    assert parse_tls_target('http://example.com') is None

def test_collect_tls_skips_non_https():
    """Ensures Collect TLS Skips Non Https."""
    result = collect_tls('http://example.com', timeout_seconds=5)
    assert result.skipped is True
    assert result.skip_reason == 'Target is not HTTPS'

def test_collect_tls_uses_injected_handlers():
    """Ensures Collect TLS Uses Injected Handlers."""

    def handshake(_host, _port, min_ver, max_ver, _timeout):
        if max_ver == ssl.TLSVersion.TLSv1_1:
            return (True, 'TLSv1.1', None)
        return (False, None, 'rejected')

    def fetch_cert(_host, _port, _timeout):
        return TlsCertificateInfo(subject='CN=test', issuer='CN=CA', days_left=90, chain_length=1)
    result = collect_tls('https://example.com', timeout_seconds=5, handshake_fn=handshake, fetch_cert_fn=fetch_cert)
    assert isinstance(result, TlsProbeResult)
    assert result.host == 'example.com'
    assert len(result.versions) == 4
    tls11 = next((v for v in result.versions if v.version == '1.1'))
    assert tls11.supported is True
    assert result.certificate is not None
    assert result.certificate.subject == 'CN=test'

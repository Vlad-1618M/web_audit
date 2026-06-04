"""Tests for ``webaudit.analyzers.headers`` — header finding rules.

What: Verifies missing/present headers, INFO-only Permissions-Policy, and leak detection.
Where: Run via ``pytest``; no network — uses synthetic ``HeaderProbeResult`` fixtures.
How: ``pytest tests/unit/test_headers_analyzer.py``.
"""
from webaudit.analyzers.headers import analyze_headers
from webaudit.collectors.headers import HeaderProbeResult
from webaudit.models.finding import FindingClass, Severity

def test_missing_security_headers():
    """Ensures Missing Security Headers."""
    probe = HeaderProbeResult(target_url='https://example.com', final_url='https://example.com/', status_code=200, headers={})
    findings = analyze_headers(probe)
    items = {f.item: f for f in findings}
    assert items['Strict-Transport-Security'].status == 'MISSING'
    assert items['Strict-Transport-Security'].severity == Severity.HIGH
    assert items['Content-Security-Policy'].severity == Severity.HIGH
    assert items['Permissions-Policy'].class_ == FindingClass.INFO
    assert items['Permissions-Policy'].scored is False

def test_missing_hsts_at_cdn_edge_is_verify_not_scored():
    """Ensures Missing HSTS At Cdn Edge Is Verify Not Scored."""
    probe = HeaderProbeResult(target_url='https://example.com', final_url='https://example.com/', status_code=200, headers={'cf-ray': 'abc123-LAX', 'server': 'cloudflare'})
    findings = analyze_headers(probe)
    hsts = next((f for f in findings if f.item == 'Strict-Transport-Security'))
    assert hsts.status == 'MISSING'
    assert hsts.class_ == FindingClass.VERIFY
    assert hsts.severity == Severity.MEDIUM
    assert hsts.scored is False
    assert 'Cloudflare' in hsts.detail

def test_present_headers_and_leaks():
    """Ensures Present Headers And Leaks."""
    probe = HeaderProbeResult(target_url='https://example.com', final_url='https://example.com/', status_code=200, headers={'strict-transport-security': 'max-age=31536000', 'content-security-policy': "default-src 'self'", 'x-frame-options': 'SAMEORIGIN', 'x-content-type-options': 'nosniff', 'referrer-policy': 'strict-origin-when-cross-origin', 'x-powered-by': 'PHP/8.2', 'server': 'nginx/1.24.0'})
    findings = analyze_headers(probe)
    by_item = {f.item: f for f in findings}
    assert by_item['Strict-Transport-Security'].status == 'PRESENT'
    assert by_item['X-Powered-By'].status == 'LEAKING'
    assert by_item['Server version'].status == 'LEAKING'

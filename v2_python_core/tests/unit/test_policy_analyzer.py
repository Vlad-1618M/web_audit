"""Tests for ``webaudit.analyzers.policy`` — HSTS and CSP deep parse."""

from webaudit.analyzers.policy import analyze_policy
from webaudit.config.settings import PolicySettings
from webaudit.models.finding import FindingClass, Severity


def test_hsts_short_max_age_is_scored():
    headers = {"strict-transport-security": "max-age=86400"}
    findings, artifact = analyze_policy(headers, PolicySettings())
    hsts = next(f for f in findings if f.item == "HSTS max-age")
    assert hsts.status == "SHORT"
    assert hsts.severity == Severity.MEDIUM
    assert hsts.class_ == FindingClass.ACTION
    assert hsts.scored is True
    assert "max-age=86400" in artifact.hsts_detail


def test_hsts_long_max_age_ok():
    headers = {
        "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
    }
    findings, _artifact = analyze_policy(headers, PolicySettings())
    hsts = next(f for f in findings if f.item == "HSTS max-age")
    assert hsts.status == "OK"
    assert not any(f.item == "HSTS includeSubDomains" for f in findings)


def test_hsts_missing_include_subdomains_info():
    headers = {"strict-transport-security": "max-age=31536000"}
    findings, _artifact = analyze_policy(headers, PolicySettings())
    inc = next(f for f in findings if f.item == "HSTS includeSubDomains")
    assert inc.class_ == FindingClass.INFO
    assert inc.scored is False


def test_csp_unsafe_inline_and_wildcard():
    headers = {
        "content-security-policy": "default-src *; script-src 'unsafe-inline' https://cdn.example.com",
    }
    findings, artifact = analyze_policy(headers, PolicySettings())
    items = {f.item: f for f in findings}
    assert items["CSP unsafe-inline"].scored is True
    assert items["CSP wildcard"].severity == Severity.HIGH
    assert "default-src *" in artifact.csp_detail
    assert "CSP review" not in items


def test_csp_clean_emits_review_ok():
    headers = {"content-security-policy": "default-src 'self'; script-src 'self'"}
    findings, _artifact = analyze_policy(headers, PolicySettings())
    review = next(f for f in findings if f.item == "CSP review")
    assert review.status == "OK"
    assert review.scored is False


def test_no_headers_emits_nothing():
    findings, artifact = analyze_policy({}, PolicySettings())
    assert findings == []
    assert artifact.hsts_detail is None
    assert artifact.csp_detail is None

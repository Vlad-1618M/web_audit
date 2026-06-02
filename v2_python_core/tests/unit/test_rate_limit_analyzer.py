"""Tests for ``webaudit.analyzers.rate_limit``."""

from webaudit.analyzers.rate_limit import analyze_rate_limit
from webaudit.collectors.rate_limit import RateLimitGetResult, RateLimitPostResult, RateLimitProbeResult
from webaudit.config.settings import RateLimitCollectorSettings
from webaudit.models.finding import FindingClass


def test_post_unprotected_scored():
    probe = RateLimitProbeResult(
        target_url="https://example.com",
        login_path="/login/",
        post_kind="form",
        get=RateLimitGetResult(attempts=6),
        post=RateLimitPostResult(attempts=15),
    )
    findings = analyze_rate_limit(probe, RateLimitCollectorSettings())
    post = next(f for f in findings if f.item.endswith("POST"))
    assert post.status == "UNPROTECTED"
    assert post.class_ == FindingClass.ACTION
    assert post.scored is True


def test_post_protected_ok():
    probe = RateLimitProbeResult(
        target_url="https://example.com",
        login_path="/login/",
        post_kind="form",
        get=RateLimitGetResult(attempts=6, limited_at=3, limit_status=429),
        post=RateLimitPostResult(attempts=15, limited_at=5, limit_status=429),
    )
    findings = analyze_rate_limit(probe, RateLimitCollectorSettings())
    assert all(f.status == "PROTECTED" for f in findings)

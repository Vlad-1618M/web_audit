"""Tests for ``webaudit.analyzers.framework``."""

from webaudit.analyzers.framework import analyze_framework
from webaudit.collectors.framework import FrameworkProbeResult
from webaudit.config.settings import FrameworkCollectorSettings


def test_forced_framework_finding():
    probe = FrameworkProbeResult(
        target_url="https://example.com",
        detected="wordpress",
        effective_framework="django",
        confidence="high",
        signals="wp-content",
        forced=True,
    )
    findings = analyze_framework(probe, FrameworkCollectorSettings())
    assert findings[0].category == "FRAMEWORK"
    assert "forced" in findings[0].detail

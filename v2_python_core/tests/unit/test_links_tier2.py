"""Tests for broken link sampler (Tier 2)."""

from webaudit.analyzers.links import analyze_links
from webaudit.collectors.links import collect_link_probes
from webaudit.config.settings import SeoSurfaceSettings


def test_broken_internal_links(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com/ok", status_code=200)
    httpx_mock.add_response(method="HEAD", url="https://example.com/missing", status_code=404)

    site_links = [
        {"url": "https://example.com/ok", "kind": "a", "source": "/"},
        {"url": "https://example.com/missing", "kind": "a", "source": "/"},
    ]
    probe = collect_link_probes(
        "https://example.com",
        site_links,
        max_sample=10,
        user_agent="WebAudit/test",
        timeout_seconds=5,
    )
    findings = analyze_links(probe, SeoSurfaceSettings(check_broken_links=True))
    assert probe.to_artifact()["broken_count"] == 1
    assert any(f.status == "BROKEN" for f in findings)


def test_no_broken_links_summary(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com/page", status_code=200)

    probe = collect_link_probes(
        "https://example.com",
        [{"url": "https://example.com/page", "kind": "a", "source": "/"}],
        max_sample=5,
        user_agent="WebAudit/test",
        timeout_seconds=5,
    )
    findings = analyze_links(probe, SeoSurfaceSettings(check_broken_links=True))
    assert any(f.status == "OK" for f in findings)

"""Tests for SEO surface analyzer."""

from webaudit.analyzers.seo_surface import analyze_seo_surface
from webaudit.config.settings import SeoSurfaceSettings
from webaudit.models.finding import FindingClass


def test_noindex_and_missing_description():
    html = """
    <html><head>
      <meta name="robots" content="noindex,nofollow">
    </head><body></body></html>
    """
    settings = SeoSurfaceSettings(enabled=True, check_open_graph=False)
    findings, summary = analyze_seo_surface(html, {}, settings)
    items = {f.item: f for f in findings}
    assert items["meta robots"].class_ == FindingClass.VERIFY
    assert items["meta robots"].scored is False
    assert items["meta description"].class_ == FindingClass.INFO
    assert summary["checks_run"] >= 2


def test_robots_blocks_all():
    html = "<html><head><title>Hi</title></head><body></body></html>"
    artifacts = {"robots": {"raw": "User-agent: *\nDisallow: /\n"}}
    settings = SeoSurfaceSettings(enabled=True, check_open_graph=False)
    findings, _ = analyze_seo_surface(html, artifacts, settings)
    assert any(f.item == "robots.txt" and f.status == "BLOCKS_ALL" for f in findings)

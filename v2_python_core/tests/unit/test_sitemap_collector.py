"""Tests for sitemap index expansion."""

from webaudit.collectors.sitemap import collect_sitemap_urls, parse_sitemap_locs


def test_parse_sitemap_locs():
    body = """<?xml version="1.0"?>
    <urlset><url><loc>https://example.com/about</loc></url></urlset>"""
    assert parse_sitemap_locs(body) == ["https://example.com/about"]


def test_collect_sitemap_urls_expands_index():
    root = """<?xml version="1.0"?>
    <sitemapindex>
      <sitemap><loc>https://example.com/post-sitemap.xml</loc></sitemap>
      <sitemap><loc>https://example.com/page-sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    child = """<?xml version="1.0"?>
    <urlset>
      <url><loc>https://example.com/blog/post-1</loc></url>
      <url><loc>https://example.com/contact</loc></url>
    </urlset>"""

    class FakeResponse:
        def __init__(self, text: str):
            self.status_code = 200
            self.text = text

    class FakeClient:
        def get(self, url, headers=None):
            if "post-sitemap" in url or "page-sitemap" in url:
                return FakeResponse(child)
            return FakeResponse("")

    urls, child_count = collect_sitemap_urls(
        "https://example.com",
        root,
        user_agent="test",
        timeout_seconds=5,
        client=FakeClient(),
    )
    assert child_count >= 2
    assert "https://example.com/blog/post-1" in urls
    assert "https://example.com/contact" in urls

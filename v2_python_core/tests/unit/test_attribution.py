"""Tests for designer/creator attribution extraction."""

from webaudit.collectors.attribution import extract_attribution


def test_extracts_html_comment_credit():
    html = "<!-- Designed by Jane Developer --><html><body></body></html>"
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Jane Developer"
    assert info.source == "html_comment"


def test_extracts_meta_author():
    html = '<html><head><meta name="author" content="Acme Studio"></head><body></body></html>'
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Acme Studio"
    assert info.source == "meta_tag"


def test_extracts_visible_designed_by_with_link():
    html = """
    <html><body><footer><a href="https://designer.example/portfolio">Designed by Pat Lee</a></footer></body></html>
    """
    info = extract_attribution(html, base_url="https://example.com")
    assert info.name == "Pat Lee"
    assert info.link_url == "https://designer.example/portfolio"

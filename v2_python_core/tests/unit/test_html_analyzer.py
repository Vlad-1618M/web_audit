"""Tests for ``webaudit.analyzers.html`` — mixed content and inventory."""

from webaudit.analyzers.html import analyze_html
from webaudit.collectors.html import HtmlProbeResult, parse_html_inventory
from webaudit.config.settings import HtmlCollectorSettings
from webaudit.models.finding import FindingClass


def test_mixed_content_on_https_is_scored():
    html = """
    <html><body>
      <img src="http://example.com/insecure.png">
      <a href="/about">About</a>
    </body></html>
    """
    probe = HtmlProbeResult(
        target_url="https://example.com",
        body=html,
        pages_scanned=1,
        inventory=parse_html_inventory(html, target_url="https://example.com"),
    )
    findings = analyze_html(probe, HtmlCollectorSettings())
    mixed = next(f for f in findings if f.item == "Mixed content")
    assert mixed.category == "HTML"
    assert mixed.scored is True
    assert mixed.class_ == FindingClass.ACTION


def test_internal_link_inventory_info():
    html = '<html><body><a href="/a">A</a><a href="https://example.com/b">B</a></body></html>'
    probe = HtmlProbeResult(
        target_url="https://example.com",
        body=html,
        pages_scanned=1,
        inventory=parse_html_inventory(html, target_url="https://example.com"),
    )
    findings = analyze_html(probe, HtmlCollectorSettings())
    links = next(f for f in findings if f.item == "Internal link inventory")
    assert links.category == "MISC"
    assert links.scored is False

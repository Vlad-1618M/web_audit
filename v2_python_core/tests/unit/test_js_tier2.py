"""Tests for Playwright JS render pass (Tier 2)."""

from unittest.mock import MagicMock, patch

from webaudit.analyzers.js import analyze_js_render
from webaudit.collectors.js import collect_js_render
from webaudit.config.settings import JsCollectorSettings


def test_js_skipped_without_playwright():
    with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
        probe = collect_js_render(
            "https://example.com",
            wait_seconds=1.0,
            user_agent="WebAudit/test",
            timeout_seconds=5,
        )
    assert probe.skipped is True
    findings = analyze_js_render(probe, JsCollectorSettings(enabled=True))
    assert findings[0].status == "SKIPPED"


def test_js_render_inventory_counts():
    rendered = """
    <html><body>
      <a href="/one">One</a>
      <a href="/two">Two</a>
      <a href="/three">Three</a>
      <script src="/app.js"></script>
    </body></html>
    """
    mock_page = MagicMock()
    mock_page.url = "https://example.com/"
    mock_page.content.return_value = rendered

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_sync = MagicMock()
    mock_sync.__enter__ = MagicMock(return_value=mock_playwright)
    mock_sync.__exit__ = MagicMock(return_value=False)

    fake_sync_api = MagicMock()
    fake_sync_api.sync_playwright.return_value = mock_sync

    with patch.dict("sys.modules", {"playwright": MagicMock(), "playwright.sync_api": fake_sync_api}):
        probe = collect_js_render(
            "https://example.com",
            wait_seconds=0.0,
            user_agent="WebAudit/test",
            timeout_seconds=5,
        )

    assert probe.error is None
    assert probe.link_count == 3
    assert probe.script_count == 1
    findings = analyze_js_render(probe, JsCollectorSettings(enabled=True), static_link_count=0)
    assert any(f.status == "SCANNED" for f in findings)
    assert any(f.status == "SPA_SIGNAL" for f in findings)

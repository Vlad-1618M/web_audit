"""Tests for site discovery / inventory enrichment."""
from unittest.mock import MagicMock
from webaudit.collectors.html import HtmlInventory
from webaudit.collectors.site_discovery import enrich_site_inventory

def test_enrich_site_inventory_fetches_single_url_when_inventory_empty(monkeypatch):
    """Regression: no sitemap + empty homepage inventory must still create an HTTP client."""
    inventory = HtmlInventory()
    mock_http_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<html><a href='/about'>About</a></html>"
    mock_http_client.get.return_value = mock_response
    mock_client_cls = MagicMock(return_value=mock_http_client)
    monkeypatch.setattr('httpx.Client', mock_client_cls)
    pages_sampled, sitemap_count, homepage_body = enrich_site_inventory(inventory, target_url='https://example.com/', sitemap_urls=[], user_agent='webaudit-test', timeout_seconds=5, max_sample_pages=3, max_body_bytes=50000, max_site_links=100, max_images=50, check_mixed_content=True, check_forms=True, client=None)
    mock_client_cls.assert_called_once()
    mock_http_client.get.assert_called_once()
    mock_http_client.close.assert_called_once()
    assert pages_sampled == 1
    assert sitemap_count == 0
    assert homepage_body.startswith('<html>')
    assert inventory.link_count > 0

def test_enrich_site_inventory_skips_fetch_when_homepage_already_parsed():
    """Ensures Enrich Site Inventory Skips Fetch When Homepage Already Parsed."""
    inventory = HtmlInventory(link_count=5)
    mock_client = MagicMock()
    pages_sampled, sitemap_count, homepage_body = enrich_site_inventory(inventory, target_url='https://example.com/', sitemap_urls=[], user_agent='webaudit-test', timeout_seconds=5, max_sample_pages=3, max_body_bytes=50000, max_site_links=100, max_images=50, check_mixed_content=True, check_forms=True, client=mock_client)
    mock_client.get.assert_not_called()
    assert pages_sampled == 1
    assert sitemap_count == 0

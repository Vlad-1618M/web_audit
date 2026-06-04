"""Test helpers for URL/host assertions (CodeQL-safe patterns)."""

from __future__ import annotations

from urllib.parse import urlparse


def url_hostname(url: str) -> str:
    return urlparse(url).hostname or ""


def assert_registry_host(registry_url: str, expected_host: str) -> None:
    assert url_hostname(registry_url) == expected_host


def assert_html_references_url(html: str, url: str) -> None:
    """Rendered HTML should reference the URL (scheme + authority, not bare host substring)."""
    parsed = urlparse(url)
    assert parsed.scheme in html
    assert f"://{parsed.netloc}" in html

"""Tests for ``webaudit.collectors.headers`` — HTTP probe behavior.

What: Verifies HEAD probe and GET fallback on 405 using pytest-httpx mocks.
Where: Run via ``pytest``; no real HTTP requests.
How: ``pytest tests/unit/test_headers_collector.py``.
"""

import httpx
import pytest

from webaudit.collectors.headers import collect_headers


def test_collect_headers_head(httpx_mock):
    httpx_mock.add_response(
        method="HEAD",
        url="https://example.com",
        headers={"Strict-Transport-Security": "max-age=31536000"},
    )
    result = collect_headers(
        "https://example.com",
        user_agent="WebAudit/test",
        timeout_seconds=5,
    )
    assert result.status_code == 200
    assert result.headers["strict-transport-security"] == "max-age=31536000"


def test_collect_headers_fallback_get(httpx_mock):
    httpx_mock.add_response(method="HEAD", url="https://example.com", status_code=405)
    httpx_mock.add_response(
        method="GET",
        url="https://example.com",
        headers={"Content-Security-Policy": "default-src 'self'"},
    )
    result = collect_headers(
        "https://example.com",
        user_agent="WebAudit/test",
        timeout_seconds=5,
    )
    assert result.headers["content-security-policy"] == "default-src 'self'"

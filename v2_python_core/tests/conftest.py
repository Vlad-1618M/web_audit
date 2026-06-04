"""Shared pytest fixtures."""

from __future__ import annotations

import os
from html import escape

import pytest
from pytest_html import extras as html_extras

from tests.test_case import resolve_test_case

_TEST_CASE_ATTR = "_webaudit_test_case"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: live Docker/network tests (requires WEBAUDIT_WP_TEST_URL)",
    )
    config.addinivalue_line(
        "markers",
        "test_case(description): explicit QA description shown in the HTML report",
    )


@pytest.hookimpl(trylast=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    case = resolve_test_case(item)
    setattr(report, _TEST_CASE_ATTR, case)
    existing = list(getattr(report, "extras", []) or [])
    existing.insert(0, html_extras.text(case, name="Test case"))
    report.extras = existing


def pytest_html_results_table_html(report, data):
    """Show test case in the expandable details panel (not only 'No log output captured.')."""
    case = getattr(report, _TEST_CASE_ATTR, None)
    if not case:
        return
    block = f"{' Test case ':-^80}\n{escape(case)}\n"
    if data == ["No log output captured."]:
        data.clear()
        data.append(block)
    else:
        data.insert(0, block)


@pytest.fixture(scope="session")
def wp_test_url() -> str:
    url = os.environ.get("WEBAUDIT_WP_TEST_URL", "").strip().rstrip("/")
    if not url:
        pytest.skip("WEBAUDIT_WP_TEST_URL not set — start the WP fixture or run ./orchestrate.sh --job wp-integration")
    return url


@pytest.fixture(scope="session")
def wp_test_profile() -> str:
    return os.environ.get("WEBAUDIT_WP_PROFILE", os.environ.get("WP_PROFILE", "mid")).strip().lower()

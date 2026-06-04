"""Tests for QA test-case description helper."""

from __future__ import annotations

import types

import pytest

from tests.test_case import default_test_case_sentence, humanize_test_name, resolve_test_case


def test_humanize_test_name():
    assert humanize_test_name("test_graphql_introspection_detected") == "GraphQL Introspection Detected"


def test_resolve_test_case_uses_docstring():
    def sample_test():
        """GraphQL introspection is flagged when schema data is returned."""

    item = types.SimpleNamespace(
        name="test_sample",
        obj=sample_test,
        get_closest_marker=lambda _name: None,
    )
    assert "schema data" in resolve_test_case(item)


def test_resolve_test_case_uses_marker():
    marker = pytest.mark.test_case("Explicit QA scenario for login flow.")

    def sample_test():
        pass

    item = types.SimpleNamespace(
        name="test_sample",
        obj=sample_test,
        get_closest_marker=lambda name: marker if name == "test_case" else None,
    )
    assert resolve_test_case(item) == "Explicit QA scenario for login flow."


def test_resolve_test_case_fallback():
    def sample_test():
        pass

    item = types.SimpleNamespace(
        name="test_open_report_outputs_calls_open_path",
        obj=sample_test,
        get_closest_marker=lambda _name: None,
        callspec=None,
    )
    text = resolve_test_case(item)
    assert "Test case:" in text
    assert "open report outputs calls open path" in text.lower()


def test_default_test_case_sentence():
    assert default_test_case_sentence("test_no_broken_links_summary").startswith("Ensures")

"""Tests for semantic path probe status display."""

from webaudit.render.probe_status import (
    build_probe_status_row,
    classify_probe_outcome,
    http_status_tone,
)


def test_sensitive_not_found_is_good():
    tone, hint = classify_probe_outcome("/.env", "NOT_FOUND")
    assert tone == "good"
    assert "Hidden" in hint or "good" in hint.lower()


def test_sensitive_open_is_bad():
    tone, hint = classify_probe_outcome("/.env", "OPEN")
    assert tone == "bad"
    assert "exposure" in hint.lower() or "reachable" in hint.lower()


def test_protected_403_is_good():
    tone, _ = classify_probe_outcome("/wp-admin/", "PROTECTED_403")
    assert tone == "good"


def test_public_robots_open_is_good():
    tone, hint = classify_probe_outcome("/robots.txt", "OPEN")
    assert tone == "good"
    assert "expected" in hint.lower() or "design" in hint.lower()


def test_public_robots_not_found_is_warn():
    tone, _ = classify_probe_outcome("/robots.txt", "NOT_FOUND")
    assert tone == "warn"


def test_unexpected_open_is_warn():
    tone, _ = classify_probe_outcome("/some-random-path", "OPEN")
    assert tone == "warn"


def test_http_status_tone_uses_convention():
    assert http_status_tone(200) == "http-2xx"
    assert http_status_tone(404) == "http-4xx"
    assert http_status_tone(403) == "http-4xx-auth"
    assert http_status_tone(500) == "http-5xx"
    assert http_status_tone(None) == "http-none"


def test_build_probe_status_row_includes_tones():
    row = build_probe_status_row(
        {"path": "/.env", "final_status": 404, "note": "NOT_FOUND"},
        framework="wordpress",
    )
    assert row["status_code"] == "404"
    assert row["note_label"] == "NOT_FOUND"
    assert row["outcome_tone"] == "good"
    assert row["status_code_tone"] == "http-4xx"
    assert row["note_tone"] == "good"


def test_exposed_200_is_bad_outcome_but_green_http_code():
    row = build_probe_status_row(
        {"path": "/.git/HEAD", "final_status": 200, "note": "OPEN"},
    )
    assert row["status_code"] == "200"
    assert row["status_code_tone"] == "http-2xx"
    assert row["outcome_tone"] == "bad"
    assert row["note_tone"] == "bad"

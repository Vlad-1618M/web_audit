"""Semantic coloring for path probe HTTP status — report-friendly, non-technical hints.

HTTP codes alone are misleading on security probes: 404 is usually good for ``/.env``,
while 200 is bad. Outcome tone follows the same rules as ``analyzers.paths``.
"""

from __future__ import annotations

from typing import Any, Literal

from webaudit.analyzers.paths import _is_expected_open, _is_login_surface, _is_scored_exposure
from webaudit.collectors.path_lists import PUBLIC_BY_DESIGN, SENSITIVE_PATHS
from webaudit.config.settings import PathsSettings

OutcomeTone = Literal["good", "bad", "warn", "neutral"]

_HIDDEN_GOOD = frozenset({"NOT_FOUND", "PROTECTED_401", "PROTECTED_403"})


def classify_probe_outcome(
    path: str,
    note: str,
    *,
    framework: str = "generic",
    expected_open: frozenset[str] | None = None,
) -> tuple[OutcomeTone, str]:
    """Return display tone and a short plain-English explanation."""
    note = (note or "UNKNOWN").upper()
    settings = PathsSettings(expected_open=tuple(expected_open or ()))

    if _is_scored_exposure(path, note):
        if note == "SERVER_ERROR":
            return "bad", "Server error on a sensitive path — may indicate a leak or misconfiguration"
        return "bad", "Sensitive path is publicly reachable — treat as an exposure"

    if note in _HIDDEN_GOOD:
        if path in PUBLIC_BY_DESIGN:
            return "warn", "Expected public file was not found — check site configuration"
        if _is_login_surface(path, framework):
            return "warn", "Login path not found — URL may have changed"
        if path in SENSITIVE_PATHS or path not in PUBLIC_BY_DESIGN:
            return "good", "Hidden or blocked — good for security"
        return "good", "Not found — no exposure detected"

    if note == "OPEN":
        if _is_expected_open(path, framework, settings):
            label = "Login page reachable" if _is_login_surface(path, framework) else "Public by design"
            return "good", f"{label} — expected for this path"
        return "warn", "Returns OK — confirm public access is intentional"

    if note == "REDIRECT":
        return "warn", "Redirect — review the destination"

    if note == "CF_BLOCKED":
        return "good", "Blocked by CDN or WAF — generally good for sensitive paths"

    if note == "RATE_LIMITED":
        return "neutral", "Rate limited — probe could not finish normally"

    if note == "SERVER_ERROR":
        return "warn", "Server error — result is inconclusive"

    if note == "NO_RESPONSE":
        return "neutral", "No response — network or timeout"

    if note.startswith("OTHER_"):
        return "neutral", "Unusual response — review manually"

    return "neutral", note.replace("_", " ").title()


def format_http_status(final_status: int | None) -> str:
    if final_status is None:
        return "—"
    return str(final_status)


def http_status_tone(final_status: int | None) -> str:
    """Standard HTTP status colors — independent of security outcome."""
    if final_status is None:
        return "http-none"
    if 200 <= final_status <= 299:
        return "http-2xx"
    if 300 <= final_status <= 399:
        return "http-3xx"
    if final_status in {401, 403}:
        return "http-4xx-auth"
    if final_status == 429:
        return "http-429"
    if 400 <= final_status <= 499:
        return "http-4xx"
    if 500 <= final_status <= 599:
        return "http-5xx"
    return "http-other"


def build_probe_status_row(
    entry: dict[str, Any],
    *,
    framework: str = "generic",
    expected_open: frozenset[str] | None = None,
) -> dict[str, str]:
    path = str(entry.get("path") or "")
    note = str(entry.get("note") or "UNKNOWN")
    final_status = entry.get("final_status")
    if isinstance(final_status, str) and final_status.isdigit():
        final_status = int(final_status)

    tone, hint = classify_probe_outcome(
        path,
        note,
        framework=framework,
        expected_open=expected_open,
    )
    status_code = format_http_status(final_status if isinstance(final_status, int) else None)
    code_tone = http_status_tone(final_status if isinstance(final_status, int) else None)

    return {
        "path": path,
        "status_code": status_code,
        "note_label": note,
        "outcome_tone": tone,
        "status_code_tone": code_tone,
        "note_tone": tone,
        "outcome_hint": hint,
        "notes": note,
    }

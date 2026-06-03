"""Finding table display helpers — status tones and detail emphasis for HTML reports."""

from __future__ import annotations

import html

from webaudit.models.finding import Finding, FindingClass, Severity

_DETAIL_PREFIXES: dict[str, list[tuple[str, str]]] = {
    "verify": [
        ("Unexpected open path", "bad"),
    ],
    "action": [
        ("Sensitive path reachable", "bad"),
    ],
}

_BAD_STATUSES = frozenset(
    {
        "MISSING",
        "OPEN",
        "LEAKING",
        "STALE",
        "SHORT",
        "ALLOWED",
        "ERROR",
        "NOINDEX",
        "LEAKING",
        "UNAVAILABLE",
        "EXPIRED",
    }
)
_WARN_STATUSES = frozenset(
    {
        "UNKNOWN",
        "UNVERIFIABLE",
        "PREMIUM_OR_UNVERIFIABLE",
        "NO_VERSION",
        "CONFLICT",
    }
)
_GOOD_STATUSES = frozenset(
    {
        "OK",
        "PRESENT",
        "CURRENT",
        "PROTECTED",
        "SECURE",
        "NONE_FOUND",
        "EXPECTED",
        "OBSERVED",
    }
)


def finding_status_tone(finding: Finding, *, section: str) -> str:
    """Return CSS tone suffix: good | bad | warn | neutral."""
    status = finding.status.upper()

    if section == "expected":
        if status == "OPEN" or status in _GOOD_STATUSES or finding.severity == Severity.OK:
            return "good"
        return "neutral"

    if section == "verify":
        if status in {"OPEN", "LEAKING"}:
            return "bad"
        if status in _WARN_STATUSES:
            return "warn"
        if status in _GOOD_STATUSES:
            return "good"
        return "neutral"

    if section == "action":
        if finding.severity in {Severity.CRITICAL, Severity.HIGH}:
            return "bad"
        if status in _BAD_STATUSES:
            return "bad"
        if finding.severity == Severity.MEDIUM or status in _WARN_STATUSES:
            return "warn"
        if status in _GOOD_STATUSES:
            return "good"
        return "warn"

    return "neutral"


def format_finding_detail_html(finding: Finding, *, section: str) -> str:
    """HTML for detail cell — emphasize leading risk phrase when known."""
    detail = finding.detail or ""
    if not detail:
        return ""

    for prefix, tone in _DETAIL_PREFIXES.get(section, []):
        if detail.startswith(prefix):
            rest = detail[len(prefix) :]
            return (
                f'<span class="finding-detail-{tone}">{html.escape(prefix)}</span>'
                f"{html.escape(rest)}"
            )

    return html.escape(detail)


def enrich_findings_table(findings: list[Finding], section: str) -> list[dict[str, object]]:
    """Attach display tones for findings table rows."""
    rows: list[dict[str, object]] = []
    for finding in findings:
        rows.append(
            {
                "finding": finding,
                "status_tone": finding_status_tone(finding, section=section),
                "detail_html": format_finding_detail_html(finding, section=section),
            }
        )
    return rows


def tls_result_tone(check: str, result: str) -> str:
    """Tone for TLS protocol versions table cells."""
    check_l = check.lower()
    result_l = result.lower().strip()

    if "certificate status" in check_l:
        if result_l in {"valid", "ok"}:
            return "good"
        if result_l in {"expired", "error", "invalid", "revoked", "unavailable"}:
            return "bad"
        return "warn"

    if "hostname match" in check_l:
        if result_l.startswith("yes"):
            return "good"
        if result_l.startswith("no"):
            return "bad"
        return "warn"

    if check_l.startswith("tls "):
        if "supported" in result_l or result_l in {"tlsv1.3", "tlsv1.2"}:
            return "good"
        if "unavailable" in result_l or "unsupported" in result_l:
            return "neutral"

    return "neutral"

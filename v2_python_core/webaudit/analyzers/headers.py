"""Security header analyzer — v1 ``check_headers()`` parity.

What: ``analyze_headers()`` turns ``HeaderProbeResult`` into scored ``Finding`` list (category HEADERS).
Where: Called from ``orchestrator`` immediately after ``collect_headers()``.
How: Checks HSTS, CSP, XFO, XCTO, Referrer-Policy, Permissions-Policy, X-Powered-By, Server version.
"""

from __future__ import annotations

import re

from webaudit.collectors.framework import _detect_cdn
from webaudit.collectors.headers import HeaderProbeResult
from webaudit.models.finding import Finding, FindingClass, Severity


def _cdn_edge_detected(headers: dict[str, str]) -> str | None:
    """Return CDN label when response headers indicate an edge proxy (v1 parity)."""
    cdn = _detect_cdn(headers)
    if cdn in ("none", "unknown", ""):
        return None
    return cdn

_HEADER_CHECKS: tuple[tuple[str, Severity, str, bool, bool], ...] = (
    (
        "strict-transport-security",
        Severity.HIGH,
        "Forces HTTPS — prevents protocol downgrade attacks",
        True,
        True,
    ),
    (
        "content-security-policy",
        Severity.HIGH,
        "Controls resource loading — primary XSS mitigation",
        True,
        True,
    ),
    (
        "x-frame-options",
        Severity.MEDIUM,
        "Prevents clickjacking via iframe embedding",
        True,
        True,
    ),
    (
        "x-content-type-options",
        Severity.MEDIUM,
        "Stops MIME-type sniffing attacks",
        True,
        True,
    ),
    (
        "referrer-policy",
        Severity.LOW,
        "Controls referrer info leaked to third parties",
        True,
        True,
    ),
    (
        "permissions-policy",
        Severity.LOW,
        "Restricts browser API access (camera, mic, geolocation)",
        False,
        False,
    ),
)

_CANONICAL_NAMES = {
    "strict-transport-security": "Strict-Transport-Security",
    "content-security-policy": "Content-Security-Policy",
    "x-frame-options": "X-Frame-Options",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}


def analyze_headers(probe: HeaderProbeResult) -> list[Finding]:
    findings: list[Finding] = []

    if probe.error:
        findings.append(
            Finding.from_check(
                category="HEADERS",
                item="HTTP probe",
                status="ERROR",
                severity=Severity.HIGH,
                detail=probe.error,
                class_=FindingClass.ACTION,
            )
        )
        return findings

    headers = probe.headers

    for key, severity, description, scored_on_missing, action_on_missing in _HEADER_CHECKS:
        display = _CANONICAL_NAMES[key]
        value = headers.get(key)
        if value:
            findings.append(
                Finding.from_check(
                    category="HEADERS",
                    item=display,
                    status="PRESENT",
                    severity=Severity.OK,
                    detail=value[:80],
                    evidence={"value": value},
                )
            )
            continue

        class_ = FindingClass.ACTION if action_on_missing else FindingClass.INFO
        scored = scored_on_missing and action_on_missing
        detail = description
        if key == "strict-transport-security":
            cdn = _cdn_edge_detected(headers)
            if cdn:
                class_ = FindingClass.VERIFY
                scored = False
                severity = Severity.MEDIUM
                detail = (
                    f"{description} — not visible externally; may be configured at "
                    f"{cdn} edge or blocked by proxy SSL detection"
                )

        findings.append(
            Finding.from_check(
                category="HEADERS",
                item=display,
                status="MISSING",
                severity=severity,
                detail=detail,
                class_=class_,
                scored=scored,
            )
        )

    xpb = headers.get("x-powered-by")
    if xpb:
        findings.append(
            Finding.from_check(
                category="HEADERS",
                item="X-Powered-By",
                status="LEAKING",
                severity=Severity.LOW,
                detail=f"Discloses stack: {xpb[:120]}",
                class_=FindingClass.ACTION,
                evidence={"value": xpb},
            )
        )

    server = headers.get("server", "")
    if server and re.search(r"/[0-9.]+", server):
        findings.append(
            Finding.from_check(
                category="HEADERS",
                item="Server version",
                status="LEAKING",
                severity=Severity.LOW,
                detail=f"Version in Server header: {server[:120]}",
                class_=FindingClass.ACTION,
                evidence={"value": server},
            )
        )

    return findings

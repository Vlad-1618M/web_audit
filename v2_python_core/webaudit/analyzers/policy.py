"""Policy analyzer — HSTS and CSP deep parse (v1 ``check_policy_parse()`` parity).

What: ``analyze_policy()`` parses security headers already collected in ``artifacts.headers``.
Where: Registered in ``pipeline._step_policy`` after the headers step; no HTTP I/O.
How: Reads normalized header dict; emits POLICY findings and ``artifacts.policy`` detail strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from webaudit.config.settings import PolicySettings
from webaudit.models.finding import Finding, FindingClass, Severity

_HSTS_MAX_AGE_RE = re.compile(r"max-age=(\d+)", re.IGNORECASE)
_CSP_WILDCARD_RE = re.compile(r"(script-src|default-src)[^;]*\*", re.IGNORECASE)


@dataclass
class PolicyParseResult:
    hsts_detail: str | None = None
    csp_detail: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "hsts_detail": self.hsts_detail,
            "csp_detail": self.csp_detail,
        }


def _parse_hsts(raw: str) -> tuple[int | None, bool, bool]:
    match = _HSTS_MAX_AGE_RE.search(raw)
    max_age = int(match.group(1)) if match else None
    lower = raw.lower()
    return max_age, "includesubdomains" in lower, "preload" in lower


def _hsts_summary(max_age: int | None, include_subdomains: bool, preload: bool) -> str:
    parts = [f"max-age={max_age if max_age is not None else 'unknown'}"]
    if include_subdomains:
        parts.append("includeSubDomains")
    if preload:
        parts.append("preload")
    return ", ".join(parts)


def _csp_has_weak_patterns(csp: str) -> tuple[bool, bool, bool]:
    lower = csp.lower()
    has_unsafe_inline = "unsafe-inline" in lower
    has_unsafe_eval = "unsafe-eval" in lower
    has_wildcard = _CSP_WILDCARD_RE.search(csp) is not None
    return has_unsafe_inline, has_unsafe_eval, has_wildcard


def analyze_policy(headers: dict[str, str], settings: PolicySettings) -> tuple[list[Finding], PolicyParseResult]:
    """Parse HSTS/CSP policy from normalized response headers (lowercase keys)."""
    findings: list[Finding] = []
    artifact = PolicyParseResult()

    hsts = headers.get("strict-transport-security", "").strip()
    if hsts:
        max_age, include_subdomains, preload = _parse_hsts(hsts)
        summary = _hsts_summary(max_age, include_subdomains, preload)
        artifact.hsts_detail = f"{summary} (raw: {hsts[:120]})"

        if max_age is not None and max_age < settings.hsts_min_max_age_seconds:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="HSTS max-age",
                    status="SHORT",
                    severity=Severity.MEDIUM,
                    detail=(
                        f"HSTS max-age={max_age}s (< {settings.hsts_min_max_age_seconds // 86400} days) — "
                        "consider ≥ 31536000 for preload eligibility"
                    ),
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"max_age": max_age, "raw": hsts},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="HSTS max-age",
                    status="OK",
                    severity=Severity.OK,
                    detail=f"HSTS max-age={max_age if max_age is not None else 'unknown'}",
                    evidence={"max_age": max_age, "raw": hsts},
                )
            )

        if not include_subdomains:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="HSTS includeSubDomains",
                    status="MISSING",
                    severity=Severity.LOW,
                    detail="HSTS present but includeSubDomains not set",
                    class_=FindingClass.INFO,
                    scored=False,
                    evidence={"raw": hsts},
                )
            )

    csp = headers.get("content-security-policy", "").strip()
    if csp:
        artifact.csp_detail = csp[: settings.csp_detail_max_length]
        unsafe_inline, unsafe_eval, wildcard = _csp_has_weak_patterns(csp)

        if unsafe_inline:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="CSP unsafe-inline",
                    status="ALLOWED",
                    severity=Severity.MEDIUM,
                    detail="CSP allows unsafe-inline — weakens XSS protection",
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"raw": csp[:200]},
                )
            )
        if unsafe_eval:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="CSP unsafe-eval",
                    status="ALLOWED",
                    severity=Severity.MEDIUM,
                    detail="CSP allows unsafe-eval",
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"raw": csp[:200]},
                )
            )
        if wildcard:
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="CSP wildcard",
                    status="ALLOWED",
                    severity=Severity.HIGH,
                    detail="CSP uses wildcard (*) in script-src or default-src",
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"raw": csp[:200]},
                )
            )
        if not (unsafe_inline or unsafe_eval or wildcard):
            findings.append(
                Finding.from_check(
                    category="POLICY",
                    item="CSP review",
                    status="OK",
                    severity=Severity.OK,
                    detail="No obvious unsafe-inline/eval/wildcard patterns detected",
                    evidence={"raw": csp[:200]},
                )
            )

    return findings, artifact

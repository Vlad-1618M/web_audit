"""Cookie analyzer — HttpOnly/Secure/SameSite flag checks (v1 ``check_cookies()`` parity).

What: ``analyze_cookies()`` turns ``CookiesProbeResult`` into COOKIES findings.
Where: Called from ``pipeline._step_cookies`` after ``collect_cookies()``.
How: Framework-expected CSRF cookies → EXPECTED; CDN cookies → VERIFY; others → flag audit.
"""

from __future__ import annotations

import re

from webaudit.collectors.cookies import CookiesProbeResult
from webaudit.config.settings import CookiesCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity

_CDN_COOKIES = frozenset({"__cf_bm", "_cfuvid", "cf_clearance"})


def _flag_present(raw: str, flag: str) -> bool:
    return re.search(rf"(?:^|;)\s*{flag}\s*(?:=|;|$)", raw, re.IGNORECASE) is not None


def _missing_flags(raw: str) -> list[str]:
    missing: list[str] = []
    if not _flag_present(raw, "HttpOnly"):
        missing.append("HttpOnly")
    if not _flag_present(raw, "Secure"):
        missing.append("Secure")
    if not _flag_present(raw, "SameSite"):
        missing.append("SameSite")
    return missing


def analyze_cookies(probe: CookiesProbeResult, settings: CookiesCollectorSettings, *, framework: str) -> list[Finding]:
    if probe.error and not probe.cookies:
        return [
            Finding.from_check(
                category="COOKIES",
                item="Detection",
                status="ERROR",
                severity=Severity.LOW,
                detail=probe.error,
                class_=FindingClass.VERIFY,
                scored=False,
            )
        ]

    if not probe.cookies:
        return [
            Finding.from_check(
                category="COOKIES",
                item="Detection",
                status="NONE_FOUND",
                severity=Severity.INFO,
                detail="No Set-Cookie headers found on login page or homepage",
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    findings: list[Finding] = []
    for cookie in probe.cookies:
        name = cookie.name
        raw = cookie.raw

        if name == "csrftoken" and framework == "django":
            findings.append(
                Finding.from_check(
                    category="COOKIES",
                    item=name,
                    status="OPEN",
                    severity=Severity.INFO,
                    detail="Django CSRF cookie — HttpOnly intentionally omitted for JavaScript CSRF token access",
                    class_=FindingClass.EXPECTED,
                    scored=False,
                    evidence={"raw": raw},
                )
            )
            continue
        if name == "XSRF-TOKEN" and framework == "laravel":
            findings.append(
                Finding.from_check(
                    category="COOKIES",
                    item=name,
                    status="OPEN",
                    severity=Severity.INFO,
                    detail="Laravel CSRF cookie — readable by JavaScript by design",
                    class_=FindingClass.EXPECTED,
                    scored=False,
                    evidence={"raw": raw},
                )
            )
            continue

        if name in _CDN_COOKIES:
            if not _flag_present(raw, "Secure"):
                findings.append(
                    Finding.from_check(
                        category="COOKIES",
                        item=name,
                        status="INSECURE",
                        severity=Severity.LOW,
                        detail="CDN cookie missing: Secure",
                        class_=FindingClass.VERIFY,
                        scored=False,
                        evidence={"raw": raw},
                    )
                )
            else:
                findings.append(
                    Finding.from_check(
                        category="COOKIES",
                        item=name,
                        status="SECURE",
                        severity=Severity.OK,
                        detail="CDN cookie — acceptable flags for edge",
                        evidence={"raw": raw},
                    )
                )
            continue

        missing = _missing_flags(raw)
        if not missing:
            findings.append(
                Finding.from_check(
                    category="COOKIES",
                    item=name,
                    status="SECURE",
                    severity=Severity.OK,
                    detail="All flags present",
                    evidence={"raw": raw},
                )
            )
            continue

        severity = Severity.HIGH if any(f in {"HttpOnly", "Secure"} for f in missing) else Severity.MEDIUM
        findings.append(
            Finding.from_check(
                category="COOKIES",
                item=name,
                status="INSECURE",
                severity=severity,
                detail=f"Missing: {' '.join(missing)}",
                class_=FindingClass.ACTION,
                scored=True,
                evidence={"raw": raw, "missing": missing},
            )
        )

    return findings

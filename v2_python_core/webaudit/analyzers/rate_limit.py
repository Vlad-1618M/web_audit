"""Rate limit analyzer — GET/POST burst outcomes (v1 ``check_rate_limiting()`` parity).

What: ``analyze_rate_limit()`` turns burst probe results into RATE_LIMIT findings.
Where: Called from ``pipeline._step_rate_limit`` after ``collect_rate_limit()``.
How: PROTECTED when limited; UNPROTECTED POST → ACTION (HIGH/MEDIUM per v1 CDN heuristic stub).
"""

from __future__ import annotations

from webaudit.collectors.rate_limit import RateLimitProbeResult
from webaudit.config.settings import RateLimitCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_rate_limit(probe: RateLimitProbeResult, settings: RateLimitCollectorSettings) -> list[Finding]:
    if not settings.enabled:
        return []

    findings: list[Finding] = []
    label = probe.login_path

    if probe.get.limited_at:
        findings.append(
            Finding.from_check(
                category="RATE_LIMIT",
                item=f"{label} GET",
                status="PROTECTED",
                severity=Severity.OK,
                detail=f"Rate limiting triggered after {probe.get.limited_at} GET requests",
                evidence=probe.get.to_dict(),
            )
        )
    else:
        findings.append(
            Finding.from_check(
                category="RATE_LIMIT",
                item=f"{label} GET",
                status="UNPROTECTED",
                severity=Severity.LOW,
                detail=f"No 429/503 after {probe.get.attempts} rapid GET requests — see POST probe for login abuse signal",
                class_=FindingClass.INFO,
                scored=False,
                evidence=probe.get.to_dict(),
            )
        )

    if probe.post.limited_at:
        if probe.post.body_signal:
            detail = f"Lockout/rate-limit signal in response body after {probe.post.limited_at} POST attempts"
        else:
            detail = f"HTTP {probe.post.limit_status} after {probe.post.limited_at} POST attempts"
        findings.append(
            Finding.from_check(
                category="RATE_LIMIT",
                item=f"{label} POST",
                status="PROTECTED",
                severity=Severity.OK,
                detail=detail,
                evidence=probe.post.to_dict(),
            )
        )
    else:
        findings.append(
            Finding.from_check(
                category="RATE_LIMIT",
                item=f"{label} POST",
                status="UNPROTECTED",
                severity=Severity.HIGH,
                detail=(
                    f"No 429/503/lockout after {probe.post.attempts} POST attempts "
                    "with invalid credentials/data"
                ),
                class_=FindingClass.ACTION,
                scored=True,
                evidence=probe.post.to_dict(),
            )
        )

    return findings

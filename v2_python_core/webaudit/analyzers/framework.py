"""Framework fingerprint analyzer — platform detection findings.

What: ``analyze_framework()`` emits FRAMEWORK INFO findings from ``FrameworkProbeResult``.
Where: Called from ``pipeline._step_framework`` immediately after ``collect_framework()``.
How: No HTTP; reports detected stack, confidence, CDN, and language hints.
"""

from __future__ import annotations

from webaudit.collectors.framework import FrameworkProbeResult
from webaudit.config.settings import FrameworkCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_framework(probe: FrameworkProbeResult, settings: FrameworkCollectorSettings) -> list[Finding]:
    if not settings.enabled:
        return []

    if probe.blocked:
        return [
            Finding.from_check(
                category="FRAMEWORK",
                item="Platform detection",
                status="BLOCKED",
                severity=Severity.INFO,
                detail="Target blocked or unreachable — framework fingerprint unreliable",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"signals": probe.signals},
            )
        ]

    if probe.forced:
        detail = (
            f"{probe.effective_framework} (forced) — "
            f"auto-detect: {probe.detected} ({probe.confidence}) — signals: {probe.signals}"
        )
    else:
        detail = (
            f"{probe.effective_framework} ({probe.confidence} confidence) — "
            f"signals: {probe.signals}; language: {probe.language}; CDN: {probe.cdn}"
        )

    findings = [
        Finding.from_check(
            category="FRAMEWORK",
            item="Platform detection",
            status="DETECTED",
            severity=Severity.INFO,
            detail=detail,
            class_=FindingClass.INFO,
            scored=False,
            evidence={
                "detected": probe.detected,
                "effective_framework": probe.effective_framework,
                "confidence": probe.confidence,
                "signals": probe.signals,
                "language": probe.language,
                "cdn": probe.cdn,
            },
        )
    ]

    if probe.server_header:
        findings.append(
            Finding.from_check(
                category="FRAMEWORK",
                item="Server header",
                status="PRESENT",
                severity=Severity.INFO,
                detail=probe.server_header[:120],
                class_=FindingClass.INFO,
                scored=False,
            )
        )

    return findings

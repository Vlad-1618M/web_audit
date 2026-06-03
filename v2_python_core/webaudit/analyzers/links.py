"""Broken link analyzer — sampled internal link status (SEO_SURFACE INFO only).

What: ``analyze_links()`` turns link probe results into discoverability findings.
Where: ``pipeline._step_links`` after ``collect_link_probes()``.
How: Broken (HTTP ≥400 or fetch error) → SEO_SURFACE INFO; summary when none broken.
"""

from __future__ import annotations

from webaudit.collectors.links import LinkProbeEntry, LinkProbeResult, _is_broken
from webaudit.config.settings import SeoSurfaceSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_links(probe: LinkProbeResult, settings: SeoSurfaceSettings) -> list[Finding]:
    if not settings.enabled or not settings.check_broken_links:
        return []

    if probe.sampled == 0:
        return [
            Finding.from_check(
                category="SEO_SURFACE",
                item="Broken link sample",
                status="NO_LINKS",
                severity=Severity.INFO,
                detail="No internal links available to sample for broken-link check",
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    findings: list[Finding] = []
    broken: list[LinkProbeEntry] = [p for p in probe.probes if _is_broken(p)]

    for entry in broken[:10]:
        status = entry.status_code if entry.status_code is not None else "ERR"
        detail = (
            f"Sampled internal link returned HTTP {status}: {entry.url}"
            if not entry.error
            else f"Sampled internal link failed: {entry.url} ({entry.error[:80]})"
        )
        findings.append(
            Finding.from_check(
                category="SEO_SURFACE",
                item=entry.url,
                status="BROKEN",
                severity=Severity.INFO,
                detail=detail,
                class_=FindingClass.INFO,
                scored=False,
                evidence={"url": entry.url, "status_code": entry.status_code, "error": entry.error},
            )
        )

    if not broken:
        findings.append(
            Finding.from_check(
                category="SEO_SURFACE",
                item="Broken link sample",
                status="OK",
                severity=Severity.OK,
                detail=f"No broken links in sample of {probe.sampled} internal URL(s)",
                class_=FindingClass.INFO,
                scored=False,
            )
        )
    elif len(broken) > 10:
        findings.append(
            Finding.from_check(
                category="SEO_SURFACE",
                item="Broken link sample",
                status="MULTIPLE",
                severity=Severity.INFO,
                detail=f"{len(broken)} broken link(s) in sample of {probe.sampled} — showing first 10",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"broken_count": len(broken), "sampled": probe.sampled},
            )
        )

    return findings

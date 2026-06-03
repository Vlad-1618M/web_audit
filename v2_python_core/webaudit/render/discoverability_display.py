"""Discoverability / SEO surface block for executive reports (INFO/VERIFY only)."""

from __future__ import annotations

from webaudit.models.finding import Finding, FindingClass


def build_discoverability_section(seo_findings: list[Finding]) -> dict[str, object]:
    """Plain-language summary of SEO_SURFACE findings for owner-facing reports."""
    rows: list[dict[str, str]] = []
    verify_count = 0
    info_count = 0

    for finding in seo_findings:
        if finding.class_ == FindingClass.VERIFY:
            verify_count += 1
            tone = "verify"
        else:
            info_count += 1
            tone = "info"
        rows.append(
            {
                "item": finding.item,
                "status": finding.status,
                "class_label": finding.class_.value,
                "detail": finding.detail or "",
                "tone": tone,
            }
        )

    if rows:
        summary = (
            f"{len(rows)} discoverability note(s) — confirm with your developer; "
            "these do not change Hygiene or Leak protection scores."
        )
    else:
        summary = (
            "No discoverability flags on this scan — homepage meta and robots/sitemap "
            "cross-checks did not surface issues worth confirming."
        )

    return {
        "count": len(rows),
        "verify_count": verify_count,
        "info_count": info_count,
        "rows": rows,
        "has_rows": bool(rows),
        "summary": summary,
    }

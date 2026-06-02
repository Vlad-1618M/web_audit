"""Finding count chips for the report score area."""

from __future__ import annotations

from webaudit.models.finding import Finding, FindingClass, Severity

_EXTENSION_CATEGORIES = frozenset(
    {
        "PLUGIN",
        "PLUGIN_VERIFY",
        "PLUGIN_INFO",
        "PACKAGE",
        "PACKAGE_VERIFY",
        "PACKAGE_INFO",
        "GEM",
        "GEM_VERIFY",
        "GEM_INFO",
    }
)


def _count_action(findings: list[Finding], severity: Severity) -> int:
    return sum(
        1
        for f in findings
        if f.class_ == FindingClass.ACTION and f.severity == severity
    )


def _count_extension_chip(findings: list[Finding], *, extension_detected_count: int) -> int:
    if extension_detected_count > 0:
        return extension_detected_count
    return sum(
        1
        for finding in findings
        if finding.category in _EXTENSION_CATEGORIES
        and finding.status.upper() != "NONE_OBSERVED"
        and not (finding.item or "").startswith("Framework ")
    )


def build_metric_chips(
    findings: list[Finding],
    *,
    extension_detected_count: int = 0,
) -> list[dict[str, str | int]]:
    verify = [f for f in findings if f.class_ == FindingClass.VERIFY]
    expected = [f for f in findings if f.class_ == FindingClass.EXPECTED]
    seo = [f for f in findings if f.category == "SEO_SURFACE"]
    extensions = [f for f in findings if f.category in _EXTENSION_CATEGORIES]
    plugin_count = _count_extension_chip(findings, extension_detected_count=extension_detected_count)
    sensitive = [
        f
        for f in findings
        if f.category == "PATHS"
        and f.class_ == FindingClass.ACTION
        and f.status.upper() in {"OPEN", "LEAKING"}
    ]
    ext_stale = [
        f for f in extensions if f.status.upper() in {"STALE", "UNKNOWN", "NO_VERSION"}
    ]

    return [
        {
            "label": "Critical",
            "count": _count_action(findings, Severity.CRITICAL),
            "tone": "critical",
            "anchor": "findings-action",
        },
        {
            "label": "High action",
            "count": _count_action(findings, Severity.HIGH),
            "tone": "high",
            "anchor": "findings-action",
        },
        {
            "label": "Medium",
            "count": _count_action(findings, Severity.MEDIUM),
            "tone": "medium",
            "anchor": "findings-action",
        },
        {"label": "Verify", "count": len(verify), "tone": "verify", "anchor": "findings-verify"},
        {"label": "Expected", "count": len(expected), "tone": "expected", "anchor": "findings-expected"},
        {"label": "Sensitive leaks", "count": len(sensitive), "tone": "leak", "anchor": "paths"},
        {"label": "SEO checks", "count": len(seo), "tone": "seo", "anchor": "findings-seo"},
        {
            "label": "Plugins",
            "count": plugin_count,
            "sub": f"{len(ext_stale)} need version review" if ext_stale else "",
            "tone": "plugins",
            "anchor": "extensions",
        },
    ]

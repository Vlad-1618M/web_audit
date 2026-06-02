"""Scoring engine — Hygiene, Exposure, and Verdict from findings.

What: ``score_findings()`` and helpers compute 0–100 scores and PASS/NEEDS_ATTENTION/AT_RISK.
Where: Called by ``orchestrator`` after all analyzers; results stored in ``AuditRun.scores``.
How: Only ACTION + scored findings deduct Hygiene; PATHS leaks deduct Exposure; hard stops force AT_RISK.
      Tier 2b plugin/package caps and worst-plugin-wins apply to extension categories.
"""

from __future__ import annotations

from webaudit.config.settings import HygieneWeights, ScoringSettings
from webaudit.models.finding import Finding, FindingClass
from webaudit.models.run import AuditScores

_PLUGIN_CATEGORIES = frozenset({"PLUGIN", "PLUGIN_CVE", "PACKAGE", "PACKAGE_CVE", "GEM", "GEM_CVE"})


def _band(score: int) -> str:
    if score >= 90:
        return "GOOD"
    if score >= 70:
        return "FAIR"
    if score >= 50:
        return "POOR"
    return "CRITICAL"


def _finding_weight(finding: Finding, weight_map: dict[str, int]) -> int:
    return weight_map.get(finding.severity.value, 0)


def _plugin_deduction(
    plugin_by_category: dict[str, list[int]],
    *,
    caps: dict[str, int],
    plugin_worst_wins: bool,
) -> int:
    if not plugin_by_category:
        return 0

    if plugin_worst_wins:
        all_weights = [w for weights in plugin_by_category.values() for w in weights]
        total = max(all_weights) if all_weights else 0
        cap_keys = ("PLUGIN", "PACKAGE", "GEM")
        cap = next((caps[key] for key in cap_keys if key in caps), None)
        if cap is not None:
            total = min(total, cap)
        return total

    total = 0
    for category, weights in plugin_by_category.items():
        cat_total = sum(weights)
        cap = caps.get(category)
        if cap is not None:
            cat_total = min(cat_total, cap)
        total += cat_total
    return total


def compute_hygiene(
    findings: list[Finding],
    weights: HygieneWeights,
    *,
    scoring: ScoringSettings | None = None,
) -> int:
    weight_map = {
        "CRITICAL": weights.CRITICAL,
        "HIGH": weights.HIGH,
        "MEDIUM": weights.MEDIUM,
        "LOW": weights.LOW,
    }
    seo_affects = scoring.seo_surface_affects_scores if scoring else False
    caps = scoring.hygiene_caps if scoring else {}
    plugin_worst_wins = scoring.plugin_worst_wins if scoring else False

    plugin_by_category: dict[str, list[int]] = {}
    category_totals: dict[str, int] = {}
    other_total = 0

    for finding in findings:
        if finding.class_ != FindingClass.ACTION or not finding.scored:
            continue
        if finding.category == "SEO_SURFACE" and not seo_affects:
            continue
        weight = _finding_weight(finding, weight_map)
        if finding.category in _PLUGIN_CATEGORIES:
            plugin_by_category.setdefault(finding.category, []).append(weight)
            continue
        cap = caps.get(finding.category)
        if cap is not None:
            category_totals[finding.category] = category_totals.get(finding.category, 0) + weight
        else:
            other_total += weight

    plugin_total = _plugin_deduction(
        plugin_by_category,
        caps=caps,
        plugin_worst_wins=plugin_worst_wins,
    )

    capped_other = sum(
        min(total, caps[category]) if category in caps else total
        for category, total in category_totals.items()
    )

    total = other_total + capped_other + plugin_total
    return max(0, 100 - total)


def compute_exposure(findings: list[Finding]) -> int:
    leak_count = sum(
        1
        for f in findings
        if f.category == "PATHS"
        and f.class_ == FindingClass.ACTION
        and f.scored
        and f.status in {"OPEN", "LEAKING"}
    )
    return max(0, 100 - 25 * leak_count)


def compute_verdict(hygiene: int, exposure: int, findings: list[Finding]) -> str:
    for finding in findings:
        if (
            finding.category == "PATHS"
            and finding.class_ == FindingClass.ACTION
            and finding.severity.value == "CRITICAL"
            and finding.status == "OPEN"
            and finding.item in {".env", ".git/HEAD"}
        ):
            return "AT_RISK"

        if finding.category == "TLS" and finding.status == "EXPIRED":
            return "AT_RISK"

    h_band = _band(hygiene)
    e_band = _band(exposure)

    if e_band in {"POOR", "CRITICAL"} or h_band == "CRITICAL":
        return "AT_RISK"
    if h_band in {"FAIR", "POOR"} and e_band == "GOOD":
        return "NEEDS_ATTENTION"
    if h_band == "GOOD" and e_band == "GOOD":
        return "PASS"
    if h_band == "GOOD" and e_band == "FAIR":
        return "NEEDS_ATTENTION"
    return "NEEDS_ATTENTION"


def score_findings(
    findings: list[Finding],
    weights: HygieneWeights,
    *,
    scoring: ScoringSettings | None = None,
) -> AuditScores:
    hygiene = compute_hygiene(findings, weights, scoring=scoring)
    exposure = compute_exposure(findings)
    verdict = compute_verdict(hygiene, exposure, findings)
    return AuditScores(hygiene=hygiene, exposure=exposure, verdict=verdict)

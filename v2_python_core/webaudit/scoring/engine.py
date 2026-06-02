"""Scoring engine — Hygiene, Exposure, and Verdict from findings.

What: ``score_findings()`` and helpers compute 0–100 scores and PASS/NEEDS_ATTENTION/AT_RISK.
Where: Called by ``orchestrator`` after all analyzers; results stored in ``AuditRun.scores``.
How: Only ACTION + scored findings deduct Hygiene; PATHS leaks deduct Exposure; hard stops force AT_RISK.
"""

from __future__ import annotations

from webaudit.config.settings import HygieneWeights
from webaudit.models.finding import Finding, FindingClass
from webaudit.models.run import AuditScores


def _band(score: int) -> str:
    if score >= 90:
        return "GOOD"
    if score >= 70:
        return "FAIR"
    if score >= 50:
        return "POOR"
    return "CRITICAL"


def compute_hygiene(findings: list[Finding], weights: HygieneWeights) -> int:
    weight_map = {
        "CRITICAL": weights.CRITICAL,
        "HIGH": weights.HIGH,
        "MEDIUM": weights.MEDIUM,
        "LOW": weights.LOW,
    }
    total = 0
    for finding in findings:
        if finding.class_ != FindingClass.ACTION or not finding.scored:
            continue
        total += weight_map.get(finding.severity.value, 0)
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


def score_findings(findings: list[Finding], weights: HygieneWeights) -> AuditScores:
    hygiene = compute_hygiene(findings, weights)
    exposure = compute_exposure(findings)
    verdict = compute_verdict(hygiene, exposure, findings)
    return AuditScores(hygiene=hygiene, exposure=exposure, verdict=verdict)

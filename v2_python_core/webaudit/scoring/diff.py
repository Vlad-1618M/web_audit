"""Baseline diff — compare two audit runs for regressions and improvements.

What: ``diff_audit_runs()`` compares baseline vs current ``AuditRun`` envelopes.
Where: ``webaudit diff`` CLI and optional report sections.
How: Finding set diff on ACTION items; score deltas per docs/scoring.md Tier 2 rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from webaudit.models.finding import Finding, FindingClass
from webaudit.models.run import AuditRun


@dataclass
class DiffEntry:
    kind: str
    category: str
    item: str
    detail: str
    severity: str = "INFO"


@dataclass
class AuditDiff:
    baseline_started_at: str
    current_started_at: str
    baseline_url: str
    current_url: str
    delta_hygiene: int
    delta_exposure: int
    entries: list[DiffEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline_started_at": self.baseline_started_at,
            "current_started_at": self.current_started_at,
            "baseline_url": self.baseline_url,
            "current_url": self.current_url,
            "delta_hygiene": self.delta_hygiene,
            "delta_exposure": self.delta_exposure,
            "entries": [
                {
                    "kind": e.kind,
                    "category": e.category,
                    "item": e.item,
                    "detail": e.detail,
                    "severity": e.severity,
                }
                for e in self.entries
            ],
        }


def _finding_key(finding: Finding) -> tuple[str, str]:
    return (finding.category, finding.item)


def _action_findings(run: AuditRun) -> dict[tuple[str, str], Finding]:
    return {
        _finding_key(f): f
        for f in run.findings
        if f.class_ == FindingClass.ACTION and f.scored
    }


def diff_audit_runs(baseline: AuditRun, current: AuditRun) -> AuditDiff:
    delta_hygiene = current.scores.hygiene - baseline.scores.hygiene
    delta_exposure = current.scores.exposure - baseline.scores.exposure

    result = AuditDiff(
        baseline_started_at=baseline.meta.started_at,
        current_started_at=current.meta.started_at,
        baseline_url=baseline.meta.target_url,
        current_url=current.meta.target_url,
        delta_hygiene=delta_hygiene,
        delta_exposure=delta_exposure,
    )

    if delta_hygiene <= -10:
        result.entries.append(
            DiffEntry(
                kind="REGRESSION",
                category="SCORES",
                item="Hygiene",
                detail=f"Hygiene dropped {abs(delta_hygiene)} points ({baseline.scores.hygiene} → {current.scores.hygiene})",
                severity="HIGH",
            )
        )
    elif delta_hygiene >= 10:
        result.entries.append(
            DiffEntry(
                kind="IMPROVEMENT",
                category="SCORES",
                item="Hygiene",
                detail=f"Hygiene improved {delta_hygiene} points ({baseline.scores.hygiene} → {current.scores.hygiene})",
                severity="INFO",
            )
        )

    if delta_exposure <= -10:
        result.entries.append(
            DiffEntry(
                kind="REGRESSION",
                category="SCORES",
                item="Exposure",
                detail=f"Exposure dropped {abs(delta_exposure)} points ({baseline.scores.exposure} → {current.scores.exposure})",
                severity="HIGH",
            )
        )
    elif delta_exposure >= 10:
        result.entries.append(
            DiffEntry(
                kind="IMPROVEMENT",
                category="SCORES",
                item="Exposure",
                detail=f"Exposure improved {delta_exposure} points ({baseline.scores.exposure} → {current.scores.exposure})",
                severity="INFO",
            )
        )

    base_actions = _action_findings(baseline)
    curr_actions = _action_findings(current)

    for key, finding in curr_actions.items():
        if key in base_actions:
            continue
        kind = "REGRESSION" if finding.category == "PATHS" and finding.status in {"OPEN", "LEAKING"} else "NEW_ISSUE"
        if finding.category == "PLUGIN_CVE":
            kind = "REGRESSION"
        severity = finding.severity.value if kind == "REGRESSION" else "MEDIUM"
        result.entries.append(
            DiffEntry(
                kind=kind,
                category=finding.category,
                item=finding.item,
                detail=finding.detail or finding.status,
                severity=severity,
            )
        )

    for key, finding in base_actions.items():
        if key not in curr_actions:
            result.entries.append(
                DiffEntry(
                    kind="RESOLVED",
                    category=finding.category,
                    item=finding.item,
                    detail=finding.detail or finding.status,
                    severity="INFO",
                )
            )

    for key, finding in curr_actions.items():
        base = base_actions.get(key)
        if not base:
            continue
        if finding.category == "PLUGIN" and finding.status == "STALE" and base.status == "STALE":
            if finding.evidence.get("version") != base.evidence.get("version"):
                result.entries.append(
                    DiffEntry(
                        kind="IMPROVEMENT" if finding.evidence.get("version", "") > base.evidence.get("version", "") else "NEW_ISSUE",
                        category="PLUGIN",
                        item=finding.item,
                        detail=f"Plugin version changed ({base.evidence.get('version')} → {finding.evidence.get('version')})",
                        severity="INFO",
                    )
                )

    return result

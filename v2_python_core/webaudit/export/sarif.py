"""SARIF 2.1.0 export for GitHub Code Scanning and CI consumers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditRun

_SARIF_VERSION = "2.1.0"
_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

_SCORED_CATEGORIES = frozenset(
    {
        "HEADERS",
        "DNS",
        "PATHS",
        "TLS",
        "POLICY",
        "COOKIES",
        "CORS",
        "RATE_LIMIT",
        "PLUGIN",
        "PLUGIN_CVE",
        "THEME",
        "THEME_CVE",
        "PACKAGE",
        "PACKAGE_CVE",
        "GEM",
        "GEM_CVE",
        "ARTIFACTS",
        "HTML",
        "FRAMEWORK",
    }
)


def _sarif_level(finding: Finding) -> str:
    if finding.class_ != FindingClass.ACTION or not finding.scored:
        return "note"
    match finding.severity:
        case Severity.CRITICAL | Severity.HIGH:
            return "error"
        case Severity.MEDIUM:
            return "warning"
        case _:
            return "note"


def _rule_id(finding: Finding) -> str:
    return f"webaudit/{finding.category}/{finding.status}".lower()


def _result_message(finding: Finding) -> str:
    if finding.detail:
        return finding.detail
    return f"{finding.category} {finding.item}: {finding.status}"


def _physical_location(run: AuditRun) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {
                "uri": run.meta.target_url,
            }
        }
    }


def finding_to_sarif_result(finding: Finding, run: AuditRun) -> dict[str, Any]:
    return {
        "ruleId": _rule_id(finding),
        "level": _sarif_level(finding),
        "message": {"text": _result_message(finding)},
        "locations": [_physical_location(run)],
        "properties": {
            "category": finding.category,
            "item": finding.item,
            "status": finding.status,
            "severity": finding.severity.value,
            "class": finding.class_.value,
            "scored": finding.scored,
            "evidence": finding.evidence,
        },
    }


def audit_run_to_sarif(
    run: AuditRun,
    *,
    include_verify: bool = False,
    include_info: bool = False,
) -> dict[str, Any]:
    """Convert an audit run to SARIF 2.1.0."""
    results: list[dict[str, Any]] = []
    rule_ids: set[str] = set()

    for finding in run.findings:
        if finding.category not in _SCORED_CATEGORIES and finding.category not in {
            "PLUGIN_VERIFY",
            "THEME_VERIFY",
            "SEO_SURFACE",
        }:
            continue
        if finding.class_ == FindingClass.ACTION and finding.scored:
            pass
        elif finding.class_ == FindingClass.VERIFY and include_verify:
            pass
        elif finding.class_ == FindingClass.INFO and include_info:
            pass
        else:
            continue

        rule_ids.add(_rule_id(finding))
        results.append(finding_to_sarif_result(finding, run))

    rules = [
        {
            "id": rule_id,
            "name": rule_id.split("/", 2)[-1],
            "shortDescription": {"text": rule_id},
        }
        for rule_id in sorted(rule_ids)
    ]

    return {
        "$schema": _SARIF_SCHEMA,
        "version": _SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Web Audit",
                        "informationUri": "https://github.com/Vlad-1618M/web_audit",
                        "version": run.meta.webaudit_version,
                        "rules": rules,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "startTimeUtc": run.meta.started_at,
                        "endTimeUtc": run.meta.finished_at or run.meta.started_at,
                    }
                ],
                "results": results,
                "properties": {
                    "targetUrl": run.meta.target_url,
                    "framework": run.meta.framework,
                    "hygiene": run.scores.hygiene,
                    "exposure": run.scores.exposure,
                    "verdict": run.scores.verdict,
                },
            }
        ],
    }


def write_sarif_report(
    run: AuditRun,
    run_dir: Path,
    *,
    filename: str = "audit_run.sarif.json",
    include_verify: bool = False,
    include_info: bool = False,
) -> Path:
    payload = audit_run_to_sarif(run, include_verify=include_verify, include_info=include_info)
    out_path = run_dir / filename
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return out_path

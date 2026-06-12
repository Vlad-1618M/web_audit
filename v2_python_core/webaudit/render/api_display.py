"""GraphQL / OpenAPI probe summary for technical HTML reports."""

from __future__ import annotations

from typing import Any

from webaudit.collectors.js_errors import full_scan_enable_steps
from webaudit.models.finding import Finding, FindingClass

_STATUS_LABELS = {
    "not_used": "Not run",
    "ok": "No exposure",
    "warn": "Review recommended",
}


def _graphql_probe_row(entry: dict[str, Any]) -> dict[str, str]:
    path = str(entry.get("path") or "—")
    code = entry.get("status_code")
    code_label = str(code) if code is not None else "—"

    if entry.get("introspection_enabled"):
        return {
            "path": path,
            "status_code": code_label,
            "result": "Introspection open",
            "tone": "bad",
        }
    if entry.get("error"):
        return {
            "path": path,
            "status_code": code_label,
            "result": "Request failed",
            "tone": "neutral",
        }
    if code == 200:
        return {
            "path": path,
            "status_code": code_label,
            "result": "Reachable (introspection closed)",
            "tone": "warn",
        }
    return {
        "path": path,
        "status_code": code_label,
        "result": "No GraphQL match",
        "tone": "good",
    }


def _openapi_probe_row(entry: dict[str, Any]) -> dict[str, str]:
    path = str(entry.get("path") or "—")
    code = entry.get("status_code")
    code_label = str(code) if code is not None else "—"

    if entry.get("openapi_detected"):
        title = str(entry.get("title") or "OpenAPI/Swagger spec")
        version = str(entry.get("version") or "").strip()
        result = f"Exposed — {title}"
        if version:
            result = f"{result} ({version})"
        return {
            "path": path,
            "status_code": code_label,
            "result": result,
            "tone": "bad",
        }
    if entry.get("error"):
        return {
            "path": path,
            "status_code": code_label,
            "result": "Request failed",
            "tone": "neutral",
        }
    return {
        "path": path,
        "status_code": code_label,
        "result": "No spec match",
        "tone": "good",
    }


def _api_findings(findings: list[Finding] | None) -> list[Finding]:
    return [finding for finding in (findings or []) if finding.category == "API"]


def build_api_section(
    artifacts: dict[str, Any],
    *,
    target_url: str,
    findings: list[Finding] | None = None,
) -> dict[str, Any]:
    """Build API probe callout + optional inventory rows for the technical report."""
    inventory = artifacts.get("inventory") or {}
    api_art = inventory.get("api") or {}
    api_hits = _api_findings(findings)

    if not api_art:
        return {
            "ran": False,
            "status": "not_used",
            "status_label": _STATUS_LABELS["not_used"],
            "tone": "neutral",
            "headline": "API surface probes not run",
            "summary": (
                "This scan did not probe common GraphQL or OpenAPI/Swagger paths. "
                "Use --api to check whether schema introspection or public API docs are exposed."
            ),
            "enable_steps": full_scan_enable_steps(target_url, api=True),
            "stats": [],
            "graphql_rows": [],
            "openapi_rows": [],
            "inventory_rows": [],
            "has_verify": False,
            "verify_count": 0,
        }

    graphql = list(api_art.get("graphql") or [])
    openapi = list(api_art.get("openapi") or [])
    graphql_rows = [_graphql_probe_row(entry) for entry in graphql]
    openapi_rows = [_openapi_probe_row(entry) for entry in openapi]

    introspection_count = sum(1 for entry in graphql if entry.get("introspection_enabled"))
    openapi_count = sum(1 for entry in openapi if entry.get("openapi_detected"))
    verify_count = sum(1 for finding in api_hits if finding.class_ == FindingClass.VERIFY)

    stats = [
        {
            "label": "GraphQL paths",
            "value": str(len(graphql)),
            "tone": "cyan",
        },
        {
            "label": "Introspection open",
            "value": str(introspection_count),
            "tone": "bad" if introspection_count else "good",
        },
        {
            "label": "OpenAPI paths",
            "value": str(len(openapi)),
            "tone": "violet",
        },
        {
            "label": "Specs exposed",
            "value": str(openapi_count),
            "tone": "bad" if openapi_count else "good",
        },
    ]

    inventory_rows = [
        {"bucket": "API GraphQL paths probed", "count": str(len(graphql))},
        {"bucket": "API GraphQL introspection open", "count": str(introspection_count)},
        {"bucket": "API OpenAPI paths probed", "count": str(len(openapi))},
        {"bucket": "API OpenAPI specs exposed", "count": str(openapi_count)},
    ]

    if introspection_count or openapi_count or verify_count:
        status = "warn"
        tone = "warn"
        headline = "API surface exposure detected"
        summary = (
            "One or more GraphQL introspection or OpenAPI/Swagger probes returned a positive match. "
            "Review Verify findings — these checks are informational and do not change Hygiene scores."
        )
    else:
        status = "ok"
        tone = "good"
        headline = "API surface probes completed"
        summary = (
            "Common GraphQL and OpenAPI/Swagger paths were probed with no schema introspection "
            "or public spec exposure detected from this external scan."
        )
        reachable = [
            row for row in graphql_rows if row["result"].startswith("Reachable")
        ]
        if reachable:
            summary += (
                f" GraphQL responded at {reachable[0]['path']} but introspection did not appear open."
            )

    return {
        "ran": True,
        "status": status,
        "status_label": _STATUS_LABELS[status],
        "tone": tone,
        "headline": headline,
        "summary": summary,
        "enable_steps": [],
        "stats": stats,
        "graphql_rows": graphql_rows,
        "openapi_rows": openapi_rows,
        "inventory_rows": inventory_rows,
        "has_verify": verify_count > 0 or introspection_count > 0 or openapi_count > 0,
        "verify_count": verify_count,
    }

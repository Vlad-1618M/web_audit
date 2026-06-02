"""Report render context — group findings and artifact snippets for Jinja templates.

What: ``build_report_context()`` turns an ``AuditRun`` into a template-friendly dict.
Where: Used by ``render/html.py`` before Jinja render.
How: Pure transformation — no I/O. Findings split by class; DNS/TLS/path summaries from artifacts.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditRun

_OK_STATUSES = frozenset(
    {
        "OK",
        "PRESENT",
        "REJECTED",
        "PROTECTED",
        "SUPPORTED",
        "SECURE",
        "OFF",
        "NONE_FOUND",
        "EXPECTED",
    }
)

_CATEGORY_ORDER = (
    "HEADERS",
    "TLS",
    "DNS",
    "PATHS",
    "COOKIES",
    "POLICY",
    "CORS",
    "ARTIFACTS",
    "RATE_LIMIT",
)


def _verdict_banner_class(verdict: str) -> str:
    return {
        "PASS": "pass",
        "NEEDS_ATTENTION": "needs-attention",
        "AT_RISK": "at-risk",
    }.get(verdict, "needs-attention")


def _verdict_label(verdict: str) -> str:
    return {
        "PASS": "Pass",
        "NEEDS_ATTENTION": "Needs attention",
        "AT_RISK": "At risk",
    }.get(verdict, verdict.replace("_", " ").title())


def _hygiene_band(score: int) -> str:
    if score >= 90:
        return "good"
    if score >= 70:
        return "fair"
    if score >= 50:
        return "poor"
    return "critical"


def _exposure_band(score: int) -> str:
    return _hygiene_band(score)


def _group_findings(findings: list[Finding]) -> dict[str, list[Finding]]:
    groups: dict[str, list[Finding]] = {
        "action": [],
        "verify": [],
        "expected": [],
        "info": [],
    }
    for finding in findings:
        match finding.class_:
            case FindingClass.ACTION:
                groups["action"].append(finding)
            case FindingClass.VERIFY:
                groups["verify"].append(finding)
            case FindingClass.EXPECTED:
                groups["expected"].append(finding)
            case _:
                groups["info"].append(finding)
    return groups


def _dns_cards(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    dns = artifacts.get("dns", {})
    records = dns.get("records") or {}
    cards: list[dict[str, str]] = []
    for key, label in (
        ("spf", "SPF"),
        ("dmarc", "DMARC"),
        ("caa", "CAA"),
        ("aaaa", "AAAA"),
        ("dnssec", "DNSSEC"),
    ):
        value = records.get(key)
        if value is None and key not in records:
            continue
        cards.append({"label": label, "value": str(value) if value else "(no record)"})
    return cards


def _tls_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    tls = artifacts.get("tls", {})
    rows: list[dict[str, str]] = []
    for entry in tls.get("versions") or []:
        label = f"TLS {entry.get('version', '?')}"
        if entry.get("supported"):
            result = entry.get("negotiated") or "SUPPORTED"
        else:
            result = entry.get("error") or "UNAVAILABLE"
        rows.append({"check": label, "result": str(result)})
    cert = tls.get("certificate") or {}
    if cert.get("subject"):
        rows.append({"check": "Subject", "result": cert["subject"][:120]})
    if cert.get("issuer"):
        rows.append({"check": "Issuer", "result": cert["issuer"][:120]})
    if cert.get("days_left") is not None:
        rows.append(
            {
                "check": "Expiry",
                "result": f"~{cert['days_left']}d — {cert.get('not_after', '')}",
            }
        )
    if cert.get("chain_length"):
        rows.append({"check": "Chain", "result": f"{cert['chain_length']} certificate(s)"})
    return rows


def _path_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    paths = inventory.get("paths") or {}
    rows: list[dict[str, str]] = []
    for entry in paths.get("paths") or []:
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "path": str(entry.get("path", "")),
                "status": str(entry.get("final_status") or entry.get("note") or "—"),
                "notes": str(entry.get("note") or "—"),
            }
        )
    return rows[:50]


def _inventory_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    html = inventory.get("html") or {}
    html_inv = html.get("inventory") or {}
    paths = inventory.get("paths") or {}
    rows = [
        {"bucket": "Path probes", "count": str(paths.get("probe_count", 0))},
        {"bucket": "Homepage links", "count": str(html_inv.get("link_count", 0))},
        {"bucket": "Homepage images", "count": str(html_inv.get("image_count", 0))},
        {"bucket": "Pages scanned (DOM)", "count": str(html.get("pages_scanned", 0))},
    ]
    framework = inventory.get("framework") or {}
    if framework.get("cdn"):
        rows.append({"bucket": "CDN detected", "count": str(framework["cdn"])})
    return rows


def _host_label(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.replace("www.", "")


def _severity_bar(action_findings: list[Finding]) -> tuple[str, int]:
    if not action_findings:
        return "ok", 100
    severities = {finding.severity for finding in action_findings}
    if severities & {Severity.CRITICAL, Severity.HIGH}:
        return "bad", 35
    if Severity.MEDIUM in severities:
        return "warn", 78
    return "warn", 55


def _category_health(findings: list[Finding]) -> list[dict[str, Any]]:
    action = [finding for finding in findings if finding.class_ == FindingClass.ACTION]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in _CATEGORY_ORDER:
        cat_findings = [finding for finding in action if finding.category == category]
        level, width_pct = _severity_bar(cat_findings)
        rows.append({"name": category.title(), "level": level, "width_pct": width_pct})
        seen.add(category)
    for category in sorted({finding.category for finding in action} - seen):
        cat_findings = [finding for finding in action if finding.category == category]
        level, width_pct = _severity_bar(cat_findings)
        rows.append({"name": category.title(), "level": level, "width_pct": width_pct})
    return rows


def _alert_strip(findings: list[Finding], *, limit: int = 5) -> str:
    items = [finding.item for finding in findings if finding.class_ == FindingClass.ACTION][:limit]
    return " · ".join(items) if items else "No action items"


def _ok_highlights(run: AuditRun, artifacts: dict[str, Any]) -> list[str]:
    highlights: list[str] = []
    if run.scores.exposure == 100:
        highlights.append("No sensitive path leaks detected in probed URLs")
    for finding in run.findings:
        if finding.class_ == FindingClass.ACTION:
            continue
        if finding.status.upper() in _OK_STATUSES or finding.severity == Severity.OK:
            text = finding.detail or finding.status
            highlights.append(f"{finding.item} — {text}")
        if len(highlights) >= 6:
            break
    dns = artifacts.get("dns", {}).get("records") or {}
    if dns.get("spf"):
        highlights.append("SPF record present")
    cert = artifacts.get("tls", {}).get("certificate") or {}
    days_left = cert.get("days_left")
    if isinstance(days_left, int) and days_left > 0:
        highlights.append(f"TLS certificate valid ~{days_left} days")
    return highlights[:8]


def _digest_timeline(findings: list[Finding], *, limit: int = 8) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for finding in findings:
        if finding.class_ not in {FindingClass.ACTION, FindingClass.VERIFY}:
            continue
        if finding.class_ == FindingClass.VERIFY and finding.severity in {
            Severity.INFO,
            Severity.OK,
            Severity.LOW,
        }:
            continue
        if finding.severity in {Severity.CRITICAL, Severity.HIGH}:
            tone = "critical"
        elif finding.status.upper() in _OK_STATUSES or finding.severity == Severity.OK:
            tone = "ok"
        else:
            tone = "warn"
        items.append(
            {
                "tone": tone,
                "category": f"{finding.category} · {finding.severity.value}",
                "title": finding.item,
                "detail": finding.detail or finding.status,
            }
        )
        if len(items) >= limit:
            break
    return items


def build_report_context(run: AuditRun, *, variant: str, theme: str) -> dict[str, Any]:
    artifacts = run.artifacts.model_dump()
    groups = _group_findings(run.findings)
    framework = (artifacts.get("inventory") or {}).get("framework") or {}
    inventory = artifacts.get("inventory") or {}
    paths = inventory.get("paths") or {}
    html = inventory.get("html") or {}
    cert = (artifacts.get("tls") or {}).get("certificate") or {}

    return {
        "run": run,
        "variant": variant,
        "theme": theme,
        "target_url": run.meta.target_url,
        "host_label": _host_label(run.meta.target_url),
        "framework": run.meta.framework,
        "framework_confidence": framework.get("confidence", "—"),
        "scanned_at": run.meta.finished_at or run.meta.started_at,
        "webaudit_version": run.meta.webaudit_version,
        "scores": run.scores,
        "verdict_label": _verdict_label(run.scores.verdict),
        "verdict_banner_class": _verdict_banner_class(run.scores.verdict),
        "hygiene_band": _hygiene_band(run.scores.hygiene),
        "exposure_band": _exposure_band(run.scores.exposure),
        "findings": run.findings,
        "action_findings": groups["action"],
        "verify_findings": groups["verify"],
        "expected_findings": groups["expected"],
        "info_findings": groups["info"],
        "dns_cards": _dns_cards(artifacts),
        "tls_rows": _tls_rows(artifacts),
        "path_rows": _path_rows(artifacts),
        "inventory_rows": _inventory_rows(artifacts),
        "policy": artifacts.get("policy") or {},
        "category_health": _category_health(run.findings),
        "alert_strip": _alert_strip(run.findings),
        "ok_highlights": _ok_highlights(run, artifacts),
        "digest_timeline": _digest_timeline(run.findings),
        "probe_count": paths.get("probe_count", 0),
        "pages_scanned": html.get("pages_scanned", 0),
        "cert_days": cert.get("days_left"),
        "action_count": len(groups["action"]),
    }

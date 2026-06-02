"""Report render context — group findings and artifact snippets for Jinja templates.

What: ``build_report_context()`` turns an ``AuditRun`` into a template-friendly dict.
Where: Used by ``render/html.py`` before Jinja render.
How: Pure transformation — no I/O. Findings split by class; DNS/TLS/path summaries from artifacts.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from webaudit.collectors.paths import path_to_url
from webaudit.collectors.tls_cert import (
    build_cert_issues,
    format_cert_datetime,
    format_days_left,
    issuer_display_name,
    subject_common_name,
)
from webaudit.render.dns_display import build_dns_cards, build_whois_card, format_net_tools
from webaudit.render.extension_display import build_extension_section
from webaudit.render.focus_pie import build_focus_pie_slices, focus_pie_conic_gradient
from webaudit.render.probe_status import build_probe_status_row
from webaudit.render.report_metrics import build_metric_chips
from webaudit.render.robots_display import build_robots_section
from webaudit.render.system_info import build_report_footer

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
    cards = build_dns_cards(records)
    whois_card = build_whois_card(dns.get("whois") or {})
    if whois_card:
        cards.append(whois_card)
    return cards


def _dns_net_tools_note(artifacts: dict[str, Any]) -> str:
    dns = artifacts.get("dns", {})
    return format_net_tools(dns.get("net_tools") or {})


def _tls_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    tls = artifacts.get("tls", {})
    rows: list[dict[str, str]] = []
    cert = tls.get("certificate") or {}

    if cert:
        rows.append(
            {
                "check": "Certificate status",
                "result": str(cert.get("status") or "UNKNOWN"),
            }
        )
        if cert.get("issuer_display") or cert.get("issuer"):
            rows.append(
                {
                    "check": "Issued by (CA)",
                    "result": str(cert.get("issuer_display") or cert.get("issuer", ""))[:120],
                }
            )
        if cert.get("subject_cn") or cert.get("subject"):
            rows.append(
                {
                    "check": "Issued to (CN)",
                    "result": str(cert.get("subject_cn") or cert.get("subject", ""))[:120],
                }
            )
        if cert.get("not_before"):
            rows.append({"check": "Valid from", "result": format_cert_datetime(cert["not_before"])})
        if cert.get("not_after"):
            rows.append(
                {
                    "check": "Valid until",
                    "result": f"{format_cert_datetime(cert['not_after'])} ({format_days_left(cert.get('days_left'))})",
                }
            )
        if cert.get("hostname_match") is not None:
            rows.append(
                {
                    "check": "Hostname match",
                    "result": "Yes" if cert.get("hostname_match") else f"No — {cert.get('hostname_note', '')}",
                }
            )
        if cert.get("san"):
            preview = ", ".join(cert["san"][:6])
            if len(cert["san"]) > 6:
                preview += f" (+{len(cert['san']) - 6} more)"
            rows.append({"check": "SAN names", "result": preview})

    for entry in tls.get("versions") or []:
        label = f"TLS {entry.get('version', '?')}"
        if entry.get("supported"):
            result = entry.get("negotiated") or "SUPPORTED"
        else:
            result = entry.get("error") or "UNAVAILABLE"
        rows.append({"check": label, "result": str(result)})
    if cert.get("chain_length"):
        rows.append({"check": "Chain length", "result": f"{cert['chain_length']} certificate(s)"})
    return rows


def _cert_summary(target_url: str, artifacts: dict[str, Any]) -> dict[str, Any] | None:
    tls = artifacts.get("tls") or {}
    if tls.get("skipped"):
        return None
    cert = tls.get("certificate") or {}
    if not cert and not tls.get("versions"):
        return None

    if cert.get("error") and not cert.get("subject"):
        return {
            "available": False,
            "status": "ERROR",
            "status_label": "Certificate unavailable",
            "status_class": "error",
            "headline": "Could not read the HTTPS certificate",
            "issues": build_cert_issues(cert, tls_versions=tls.get("versions")),
        }

    status = str(cert.get("status") or "UNKNOWN").upper()
    status_map = {
        "VALID": ("Valid", "ok", "HTTPS certificate looks healthy"),
        "EXPIRING": ("Expiring soon", "warn", "Renew this certificate before visitors see browser warnings"),
        "EXPIRED": ("Expired", "bad", "Certificate has expired — browsers will block or warn"),
        "UNKNOWN": ("Unknown", "muted", "Certificate timing could not be determined"),
    }
    status_label, status_class, headline = status_map.get(status, status_map["UNKNOWN"])

    issues = build_cert_issues(cert, tls_versions=tls.get("versions"))
    san = [name for name in (cert.get("san") or []) if isinstance(name, str)]
    subject_cn = cert.get("subject_cn") or subject_common_name(cert.get("subject"))
    host = tls.get("host") or _host_label(target_url)

    return {
        "available": True,
        "status": status,
        "status_label": status_label,
        "status_class": status_class,
        "headline": headline,
        "issuer_display": cert.get("issuer_display")
        or issuer_display_name(
            issuer=str(cert.get("issuer") or ""),
            issuer_org=cert.get("issuer_org"),
            issuer_cn=cert.get("issuer_cn"),
        ),
        "issuer_detail": cert.get("issuer") or "",
        "subject_cn": subject_cn or "—",
        "subject_href": _site_href(f"https://{subject_cn}") if subject_cn and subject_cn != "—" else "",
        "not_before": format_cert_datetime(cert.get("not_before")),
        "not_after": format_cert_datetime(cert.get("not_after")),
        "days_left": cert.get("days_left"),
        "days_left_label": format_days_left(cert.get("days_left")),
        "hostname_match": cert.get("hostname_match"),
        "hostname_note": cert.get("hostname_note") or "",
        "san_preview": san[:8],
        "san_links": [
            {"name": name, "href": _site_href(f"https://{name.lstrip('*.')}")}
            for name in san[:8]
            if name
        ],
        "san_extra": max(0, len(san) - 8),
        "chain_length": cert.get("chain_length") or 0,
        "issues": issues,
        "host": host,
        "host_href": _site_href(target_url),
        "is_https": target_url.startswith("https://"),
    }


def _path_rows(artifacts: dict[str, Any], *, framework: str = "generic") -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    paths = inventory.get("paths") or {}
    rows: list[dict[str, str]] = []
    for entry in paths.get("paths") or []:
        if not isinstance(entry, dict):
            continue
        status = build_probe_status_row(entry, framework=framework)
        rows.append(status)
    return rows


def _extension_section_title(framework: str, unit: str) -> str:
    titles = {
        ("wordpress", "plugin"): "WordPress plugins inspected",
        ("django", "package"): "Python packages inspected",
        ("laravel", "package"): "Composer packages inspected",
        ("rails", "gem"): "Ruby gems inspected",
        ("php", "runtime"): "PHP runtime signals",
    }
    return titles.get((framework, unit), "Framework extensions inspected")


def _extension_status_map(findings: list[Finding]) -> dict[str, dict[str, str]]:
    categories = {
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
    mapped: dict[str, dict[str, str]] = {}
    for finding in findings:
        if finding.category not in categories:
            continue
        mapped[finding.item] = {
            "status": finding.status,
            "detail": finding.detail or "",
            "severity": finding.severity.value,
            "class": finding.class_.value,
        }
    return mapped


def _extension_rows(artifacts: dict[str, Any], findings: list[Finding]) -> list[dict[str, str]]:
    ext_art = artifacts.get("extensions") or artifacts.get("plugins") or {}
    if not ext_art:
        return []
    status_map = _extension_status_map(findings)
    rows: list[dict[str, str]] = []
    for item in ext_art.get("extensions") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("slug") or "")
        if not name:
            continue
        meta = status_map.get(name, {})
        rows.append(
            {
                "name": name,
                "version": str(item.get("version") or "—"),
                "source": str(item.get("source") or "—"),
                "unit": str(item.get("unit") or ext_art.get("unit") or "extension"),
                "status": meta.get("status", "OBSERVED"),
                "detail": meta.get("detail", ""),
                "severity": meta.get("severity", "INFO"),
            }
        )
    rows.sort(key=lambda row: row["name"])
    return rows


def _probe_url_rows(
    target_url: str,
    artifacts: dict[str, Any],
    *,
    framework: str = "generic",
) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    paths = inventory.get("paths") or {}
    rows: list[dict[str, str]] = []
    for entry in paths.get("paths") or []:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "")
        if not path:
            continue
        status = build_probe_status_row(entry, framework=framework)
        rows.append(
            {
                "url": path_to_url(target_url, path),
                "bucket": "probe",
                "source": "security_probe",
                **status,
            }
        )
    return rows


def _site_url_rows(target_url: str, artifacts: dict[str, Any]) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    html = inventory.get("html") or {}
    html_inv = html.get("inventory") or {}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in html_inv.get("site_links") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "url": url,
                "path": urlparse(url).path or "/",
                "status": "DISCOVERED",
                "notes": f"{item.get('kind', 'link')} · {item.get('source', 'homepage')}",
                "bucket": "site",
                "source": str(item.get("source") or "homepage"),
            }
        )

    return rows


def _image_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    html = inventory.get("html") or {}
    html_inv = html.get("inventory") or {}
    rows: list[dict[str, str]] = []
    for item in html_inv.get("images") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url:
            continue
        rows.append(
            {
                "url": url,
                "kind": str(item.get("kind") or "img"),
                "source": str(item.get("source") or "/"),
            }
        )
    return rows


def _inventory_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    inventory = artifacts.get("inventory") or {}
    html = inventory.get("html") or {}
    html_inv = html.get("inventory") or {}
    paths = inventory.get("paths") or {}
    rows = [
        {"bucket": "Security path probes", "count": str(paths.get("probe_count", 0))},
        {"bucket": "Site links catalogued", "count": str(html_inv.get("site_links_catalogued", len(html_inv.get("site_links") or [])))},
        {"bucket": "Pages sampled for links/images", "count": str(html_inv.get("pages_sampled", html.get("pages_scanned", 0)))},
        {"bucket": "Sitemap URLs parsed", "count": str(html_inv.get("sitemap_urls_parsed", 0))},
        {"bucket": "Images & icons catalogued", "count": str(len(html_inv.get("images") or []))},
        {"bucket": "Pages scanned (DOM)", "count": str(html.get("pages_scanned", 0))},
    ]
    ext_art = artifacts.get("extensions") or artifacts.get("plugins") or {}
    if ext_art.get("extension_count"):
        rows.insert(0, {"bucket": "Extensions inspected", "count": str(ext_art.get("extension_count", 0))})
    framework = inventory.get("framework") or {}
    if framework.get("cdn"):
        rows.append({"bucket": "CDN detected", "count": str(framework["cdn"])})
    return rows


def _host_label(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.replace("www.", "")


def _site_href(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return url
    return f"https://{url.lstrip('/')}"


def _attribution_display(artifacts: dict[str, Any]) -> dict[str, str] | None:
    inventory = artifacts.get("inventory") or {}
    data = inventory.get("attribution") or {}
    if not data.get("found"):
        return {
            "name": "",
            "source": "",
            "link_url": "",
            "placement": "",
            "summary": "No designer or creator credit detected on the homepage HTML.",
            "summary_tone": "neutral",
        }
    name = str(data.get("name") or "")
    source = str(data.get("source") or "unknown")
    link = str(data.get("link_url") or "")
    placement = str(data.get("placement") or "")
    source_labels = {
        "html_comment": "HTML comment (good — not indexed by search engines)",
        "meta_tag": "Meta tag (verify it matches site owner intent)",
        "visible_text": "Visible on-page credit",
        "footer_link": "Linked footer credit",
        "title_tag": "Site title tag (may dilute brand SEO)",
    }
    tone = "good" if placement in {"acceptable", "visible"} else "warn" if placement == "title" else "neutral"
    summary = source_labels.get(source, f"Detected via {source.replace('_', ' ')}")
    return {
        "name": name,
        "source": source,
        "link_url": link,
        "placement": placement,
        "summary": summary,
        "summary_tone": tone,
    }


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


def _technical_anchor_for_finding(finding: Finding) -> str:
    """Map a finding to a technical report section id for deep-link navigation."""
    category = finding.category.upper()
    item_lower = finding.item.lower()
    if category == "TLS" or "certificate" in item_lower or item_lower.startswith("cert"):
        return "certificate"
    if category == "DNS":
        return "dns"
    if category == "PATHS":
        return "paths"
    if category.startswith("PLUGIN") or category.startswith("PACKAGE") or category.startswith("GEM"):
        return "extensions"
    if "sitemap" in item_lower or "robots" in item_lower:
        return "discovery"
    if category == "ARTIFACTS":
        return "discovery"
    if category == "POLICY" or "csp" in item_lower or "hsts" in item_lower:
        return "findings"
    return {
        "HEADERS": "findings",
        "COOKIES": "findings",
        "CORS": "findings",
        "RATE_LIMIT": "findings",
    }.get(category, "findings")


def _alert_strip(findings: list[Finding], *, limit: int = 5) -> str:
    items = [finding.item for finding in findings if finding.class_ == FindingClass.ACTION][:limit]
    return " · ".join(items) if items else "No action items"


def _alert_strip_items(findings: list[Finding], *, limit: int = 5) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for finding in findings:
        if finding.class_ != FindingClass.ACTION:
            continue
        rows.append(
            {
                "label": finding.item,
                "anchor": _technical_anchor_for_finding(finding),
            }
        )
        if len(rows) >= limit:
            break
    return rows


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
    html_inv = html.get("inventory") or {}
    cert = (artifacts.get("tls") or {}).get("certificate") or {}
    cert_summary = _cert_summary(run.meta.target_url, artifacts)
    ext_art = artifacts.get("extensions") or artifacts.get("plugins") or {}
    probe_urls = _probe_url_rows(run.meta.target_url, artifacts, framework=run.meta.framework)
    site_urls = _site_url_rows(run.meta.target_url, artifacts)
    extension_section = build_extension_section(artifacts, run.findings, framework=run.meta.framework)
    image_rows = _image_rows(artifacts)
    path_rows = _path_rows(artifacts, framework=run.meta.framework)
    footer = build_report_footer(scanned_at=run.meta.finished_at or run.meta.started_at)
    metric_chips = build_metric_chips(run.findings)
    robots_section = build_robots_section(artifacts)
    attribution = _attribution_display(artifacts)
    focus_pie_slices = build_focus_pie_slices(run.scores, run.findings)

    return {
        "run": run,
        "variant": variant,
        "theme": theme,
        "target_url": run.meta.target_url,
        "target_href": _site_href(run.meta.target_url),
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
        "dns_net_tools_note": _dns_net_tools_note(artifacts),
        "tls_rows": _tls_rows(artifacts),
        "cert_summary": cert_summary,
        "path_rows": path_rows,
        "path_row_count": len(path_rows),
        "inventory_rows": _inventory_rows(artifacts),
        "policy": artifacts.get("policy") or {},
        "category_health": _category_health(run.findings),
        "focus_pie_slices": focus_pie_slices,
        "focus_pie_gradient": focus_pie_conic_gradient(focus_pie_slices),
        "alert_strip": _alert_strip(run.findings),
        "alert_strip_items": _alert_strip_items(run.findings),
        "ok_highlights": _ok_highlights(run, artifacts),
        "is_combined_report": variant == "owner",
        "digest_timeline": _digest_timeline(run.findings),
        "probe_count": paths.get("probe_count", 0),
        "pages_scanned": html.get("pages_scanned", 0),
        "cert_days": cert.get("days_left"),
        "cert_status_label": cert_summary.get("status_label") if cert_summary else None,
        "cert_issuer_display": cert_summary.get("issuer_display") if cert_summary else None,
        "action_count": len(groups["action"]),
        "extension_section": extension_section,
        "extension_rows": extension_section.get("rows", []) if extension_section else [],
        "extension_section_title": (
            f"{extension_section['framework_label']} {extension_section['unit_plural']} & version check"
            if extension_section
            else ""
        ),
        "extension_framework": (
            extension_section.get("framework") if extension_section else run.meta.framework
        ),
        "extension_unit": extension_section.get("unit") if extension_section else "extension",
        "extension_count": (
            extension_section.get("detected_count", 0) if extension_section else 0
        ),
        "probe_urls": probe_urls,
        "site_urls": site_urls,
        "image_rows": image_rows,
        "probe_url_count": len(probe_urls),
        "site_url_count": len(site_urls),
        "site_url_catalogued": html_inv.get("site_links_catalogued", len(site_urls)),
        "pages_sampled": html_inv.get("pages_sampled", html.get("pages_scanned", 0)),
        "sitemap_urls_parsed": html_inv.get("sitemap_urls_parsed", 0),
        "image_count": len(image_rows),
        "image_catalogued": html_inv.get("images_catalogued", len(image_rows)),
        "image_tag_count": html_inv.get("image_count", 0),
        "internal_link_count": html_inv.get("internal_link_count", 0),
        "external_link_count": html_inv.get("external_link_count", 0),
        "metric_chips": metric_chips,
        "robots_section": robots_section,
        "attribution": attribution,
        "report_footer": footer,
    }

"""JavaScript render pass summary for technical HTML reports."""

from __future__ import annotations

from typing import Any

from webaudit.collectors.js_errors import full_scan_enable_steps, js_error_from_artifact
from webaudit.models.finding import Finding

_STATUS_LABELS = {
    "not_used": "Not run",
    "skipped": "Skipped",
    "error": "Failed",
    "ok": "Completed",
}

_BROWSER_LABELS = {
    "chromium": "Chromium",
    "firefox": "Firefox",
    "webkit": "WebKit",
}


def _browser_label(js_art: dict) -> str:
    browser = str(js_art.get("browser") or "chromium")
    return _BROWSER_LABELS.get(browser, browser.title())


def _ok_stats(
    *,
    rendered_links: int,
    script_count: int,
    static_links: int,
    wait_label: str,
) -> list[dict[str, str]]:
    return [
        {"label": "Rendered links", "value": str(rendered_links), "tone": "cyan"},
        {"label": "Scripts", "value": str(script_count), "tone": "violet"},
        {"label": "Static HTML links", "value": str(static_links), "tone": "neutral"},
        {"label": "Render wait", "value": wait_label, "tone": "gold"},
    ]


def _finalize(section: dict[str, Any], *, js_art: dict | None = None) -> dict[str, Any]:
    status = str(section.get("status") or "not_used")
    section["status_label"] = _STATUS_LABELS.get(status, status.replace("_", " ").title())
    section["browser"] = _browser_label(js_art or {}) if js_art else ""
    if status == "ok" and not section.get("stats"):
        section["stats"] = _ok_stats(
            rendered_links=int(section.get("rendered_links") or 0),
            script_count=int(section.get("script_count") or 0),
            static_links=int(section.get("static_links") or 0),
            wait_label=str(section.get("wait_label") or "—"),
        )
    else:
        section.setdefault("stats", [])
    return section


def build_js_section(
    artifacts: dict[str, Any],
    *,
    target_url: str,
    findings: list[Finding] | None = None,
) -> dict[str, Any]:
    """Build JS render callout + optional inventory rows for the technical report."""
    inventory = artifacts.get("inventory") or {}
    html_inv = (inventory.get("html") or {}).get("inventory") or {}
    static_links = int(html_inv.get("link_count") or 0)
    js_art = inventory.get("js") or {}

    spa_signal = any(
        finding.category == "HTML" and finding.status == "SPA_SIGNAL"
        for finding in (findings or [])
    )

    if not js_art:
        return _finalize(
            {
                "ran": False,
                "status": "not_used",
                "tone": "neutral",
                "headline": "JavaScript render pass not run",
                "summary": (
                    "This scan read static homepage HTML only (httpx). "
                    "Client-rendered SPAs may show fewer links and assets than a real browser."
                ),
                "fix_steps": full_scan_enable_steps(target_url, js=True),
                "inventory_rows": [],
                "spa_signal": spa_signal,
                "stats": [],
            },
        )

    err = js_error_from_artifact(js_art, target_url=target_url)

    if js_art.get("skipped"):
        return _finalize(
            {
                "ran": False,
                "status": "skipped",
                "tone": "warn",
                "headline": "JavaScript render pass skipped",
                "summary": err.message if err else "Playwright was not available for this scan.",
                "fix_steps": err.fix_steps if err else full_scan_enable_steps(target_url, js=True),
                "inventory_rows": [{"bucket": "JS render (Playwright)", "count": "Skipped"}],
                "spa_signal": spa_signal,
                "stats": [],
            },
            js_art=js_art,
        )

    if js_art.get("error") and not js_art.get("link_count"):
        return _finalize(
            {
                "ran": False,
                "status": "error",
                "tone": "warn",
                "headline": "JavaScript render pass failed",
                "summary": err.message if err else "Playwright could not render the homepage.",
                "fix_steps": err.fix_steps if err else full_scan_enable_steps(target_url, js=True),
                "inventory_rows": [{"bucket": "JS render (Playwright)", "count": "Error"}],
                "spa_signal": spa_signal,
                "stats": [],
            },
            js_art=js_art,
        )

    rendered_links = int(js_art.get("link_count") or 0)
    script_count = int(js_art.get("script_count") or 0)
    wait_seconds = js_art.get("wait_seconds")
    wait_label = f"{wait_seconds:g}s" if wait_seconds is not None else "—"

    summary = (
        f"Headless browser finished loading the homepage after {wait_label}. "
        f"Compare rendered link counts to static HTML when auditing SPAs."
    )
    if spa_signal:
        summary += " Client-rendered navigation detected — see Verify findings."

    return _finalize(
        {
            "ran": True,
            "status": "ok",
            "tone": "good",
            "headline": "JavaScript render pass completed",
            "summary": summary,
            "fix_steps": [],
            "inventory_rows": [
                {"bucket": "JS rendered links (Playwright)", "count": str(rendered_links)},
                {"bucket": "Scripts after JS render", "count": str(script_count)},
                {"bucket": "Static HTML links (httpx)", "count": str(static_links)},
                {"bucket": "JS render wait", "count": wait_label},
            ],
            "spa_signal": spa_signal,
            "rendered_links": rendered_links,
            "static_links": static_links,
            "script_count": script_count,
            "wait_label": wait_label,
        },
        js_art=js_art,
    )

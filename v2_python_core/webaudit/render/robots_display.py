"""Parsed robots.txt summary for HTML reports."""

from __future__ import annotations

from typing import Any

from webaudit.analyzers.artifacts import parse_robots_txt


def build_robots_section(artifacts: dict[str, Any]) -> dict[str, Any] | None:
    inventory = artifacts.get("inventory") or {}
    art = inventory.get("artifacts") or {}
    robots = art.get("robots") or {}
    raw = (robots.get("raw") or "").strip()
    status_code = robots.get("status_code")

    if status_code is None and not raw:
        return None

    disallow: list[str] = []
    allow: list[str] = []
    sitemaps: list[str] = []
    if raw:
        disallow, allow, sitemaps = parse_robots_txt(raw)

    blocks_all = any(rule.strip() == "/" for rule in disallow)
    if status_code == 200 and raw:
        if blocks_all:
            summary = "robots.txt blocks all crawlers (Disallow: /)."
            summary_tone = "warn"
        else:
            summary = (
                f"Published — {len(disallow)} disallow rule(s), "
                f"{len(allow)} allow rule(s), {len(sitemaps)} sitemap URL(s)."
            )
            summary_tone = "good"
    elif status_code == 404:
        summary = "No robots.txt file found (HTTP 404)."
        summary_tone = "neutral"
    elif status_code:
        summary = f"robots.txt returned HTTP {status_code}."
        summary_tone = "warn"
    else:
        summary = "robots.txt was not fetched."
        summary_tone = "neutral"

    preview_lines = raw.splitlines()[:24] if raw else []
    return {
        "status_code": status_code,
        "raw_preview": "\n".join(preview_lines),
        "raw_truncated": len(raw.splitlines()) > 24 if raw else False,
        "disallow_rules": disallow[:20],
        "allow_rules": allow[:20],
        "sitemap_urls": sitemaps[:10],
        "blocks_all": blocks_all,
        "summary": summary,
        "summary_tone": summary_tone,
        "description": (
            "robots.txt tells search engine crawlers which paths they may request. "
            "It is public — not an access-control mechanism for attackers."
        ),
    }

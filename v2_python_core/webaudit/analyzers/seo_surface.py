"""SEO surface analyzer — discoverability checks (INFO/VERIFY only, never scored).

What: ``analyze_seo_surface()`` inspects homepage DOM and cross-checks robots/sitemap.
Where: ``pipeline._step_seo_surface`` after HTML/framework artifacts exist.
How: BeautifulSoup meta/canonical checks; reuses robots/sitemap from artifacts collector.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from webaudit.analyzers.artifacts import parse_robots_txt, parse_sitemap_locs
from webaudit.config.settings import SeoSurfaceSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def _meta_robots_noindex(soup: BeautifulSoup) -> bool:
    for tag in soup.find_all("meta", attrs={"name": re.compile(r"^robots$", re.I)}):
        content = (tag.get("content") or "").lower()
        if "noindex" in content:
            return True
    return False


def _canonical_hrefs(soup: BeautifulSoup) -> list[str]:
    return [
        (tag.get("href") or "").strip()
        for tag in soup.find_all("link", rel=lambda v: v and "canonical" in str(v).lower())
        if (tag.get("href") or "").strip()
    ]


def _meta_description(soup: BeautifulSoup) -> str | None:
    tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if not tag:
        return None
    content = (tag.get("content") or "").strip()
    return content or None


def _open_graph_present(soup: BeautifulSoup) -> tuple[bool, bool]:
    has_title = bool(soup.find("meta", property="og:title") or soup.find("meta", attrs={"property": "og:title"}))
    has_image = bool(soup.find("meta", property="og:image") or soup.find("meta", attrs={"property": "og:image"}))
    return has_title, has_image


def analyze_seo_surface(
    html: str,
    artifacts: dict[str, Any],
    settings: SeoSurfaceSettings,
) -> tuple[list[Finding], dict[str, Any]]:
    """Return INFO/VERIFY findings and a small seo_surface artifact summary."""
    if not settings.enabled:
        return [], {}

    if not html.strip():
        return [
            Finding.from_check(
                category="SEO_SURFACE",
                item="Homepage HTML",
                status="EMPTY",
                severity=Severity.INFO,
                detail="No homepage HTML available for SEO surface checks",
                class_=FindingClass.INFO,
                scored=False,
            )
        ], {"checks_run": 0}

    soup = BeautifulSoup(html, "html.parser")
    findings: list[Finding] = []
    summary: dict[str, Any] = {"checks_run": 0}

    if settings.check_meta_robots:
        summary["checks_run"] += 1
        if _meta_robots_noindex(soup):
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="meta robots",
                    status="NOINDEX",
                    severity=Severity.INFO,
                    detail="Homepage has meta robots noindex — confirm this is intentional on a live site",
                    class_=FindingClass.VERIFY,
                    scored=False,
                )
            )

    if settings.check_meta_description:
        summary["checks_run"] += 1
        if not _meta_description(soup):
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="meta description",
                    status="MISSING",
                    severity=Severity.INFO,
                    detail="Homepage has no meta description tag",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    if settings.check_canonical:
        summary["checks_run"] += 1
        canonicals = _canonical_hrefs(soup)
        summary["canonical_count"] = len(canonicals)
        if not canonicals:
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="canonical link",
                    status="MISSING",
                    severity=Severity.INFO,
                    detail="Homepage has no link rel=canonical",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )
        elif len(canonicals) > 1:
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="canonical link",
                    status="DUPLICATE",
                    severity=Severity.INFO,
                    detail=f"Homepage has {len(canonicals)} canonical link tags",
                    class_=FindingClass.INFO,
                    scored=False,
                    evidence={"canonicals": canonicals[:5]},
                )
            )

    if settings.check_open_graph:
        summary["checks_run"] += 1
        has_title, has_image = _open_graph_present(soup)
        if not has_title or not has_image:
            missing = []
            if not has_title:
                missing.append("og:title")
            if not has_image:
                missing.append("og:image")
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="Open Graph",
                    status="INCOMPLETE",
                    severity=Severity.INFO,
                    detail=f"Homepage missing Open Graph tags: {', '.join(missing)}",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    robots_raw = ((artifacts.get("robots") or {}).get("raw") or "").strip()
    if settings.check_robots_blocks and robots_raw:
        summary["checks_run"] += 1
        disallow, _allow, _sitemaps = parse_robots_txt(robots_raw)
        if any(rule.strip() == "/" for rule in disallow):
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="robots.txt",
                    status="BLOCKS_ALL",
                    severity=Severity.INFO,
                    detail="robots.txt contains Disallow: / — may block all crawlers",
                    class_=FindingClass.VERIFY,
                    scored=False,
                )
            )

    sitemap_art = artifacts.get("sitemap") or {}
    if settings.check_sitemap:
        summary["checks_run"] += 1
        status = sitemap_art.get("status_code")
        raw = (sitemap_art.get("raw") or "").strip()
        if status and status != 200:
            findings.append(
                Finding.from_check(
                    category="SEO_SURFACE",
                    item="sitemap.xml",
                    status="HTTP_ERROR",
                    severity=Severity.INFO,
                    detail=f"sitemap.xml returned HTTP {status}",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )
        elif raw:
            locs = parse_sitemap_locs(raw, limit=500)
            summary["sitemap_url_count"] = len(locs)
            if len(locs) < settings.sitemap_empty_threshold:
                findings.append(
                    Finding.from_check(
                        category="SEO_SURFACE",
                        item="sitemap.xml",
                        status="EMPTY",
                        severity=Severity.INFO,
                        detail=(
                            f"sitemap.xml parsed with {len(locs)} URL(s) "
                            f"(threshold {settings.sitemap_empty_threshold})"
                        ),
                        class_=FindingClass.INFO,
                        scored=False,
                    )
                )

    return findings, summary

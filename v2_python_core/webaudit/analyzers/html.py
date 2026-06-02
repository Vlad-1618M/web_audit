"""HTML DOM analyzer — inventory and mixed-content checks.

What: ``analyze_html()`` turns ``HtmlProbeResult`` into MISC/HTML findings.
Where: Called from ``pipeline._step_html`` after body is collected or reused.
How: Mixed HTTP subresources on HTTPS → HTML ACTION; inventories → MISC INFO (v1 parity).
"""

from __future__ import annotations

from webaudit.collectors.html import HtmlProbeResult, parse_html_inventory
from webaudit.config.settings import HtmlCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_html(probe: HtmlProbeResult, settings: HtmlCollectorSettings) -> list[Finding]:
    if not settings.enabled:
        return []

    if probe.error:
        return [
            Finding.from_check(
                category="MISC",
                item="Homepage HTML",
                status="ERROR",
                severity=Severity.INFO,
                detail=probe.error,
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    if probe.bot_challenge and not probe.inventory.site_links and probe.inventory.link_count == 0:
        from webaudit.collectors.bot_challenge import bot_challenge_detail

        return [
            Finding.from_check(
                category="HTML",
                item="Homepage HTML",
                status="BLOCKED",
                severity=Severity.MEDIUM,
                detail=bot_challenge_detail(status_code=probe.http_status),
                class_=FindingClass.VERIFY,
                scored=False,
            )
        ]

    if not probe.body:
        return [
            Finding.from_check(
                category="MISC",
                item="Homepage HTML",
                status="EMPTY",
                severity=Severity.INFO,
                detail="Homepage HTML empty — could not scan DOM inventory",
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    inventory = probe.inventory
    if not inventory.link_count and not inventory.image_count:
        inventory = parse_html_inventory(
            probe.body,
            target_url=probe.target_url,
            check_mixed_content=settings.check_mixed_content,
            check_forms=settings.check_forms,
            max_internal_links=settings.max_internal_links_sample,
            max_site_links=settings.max_site_links,
            max_images=settings.max_images,
        )

    findings: list[Finding] = [
        Finding.from_check(
            category="MISC",
            item="Internal link inventory",
            status="CATALOGUED",
            severity=Severity.INFO,
            detail=(
                f"{len(inventory.site_links)} site URL(s) catalogued from homepage, sitemap, and "
                f"{inventory.pages_sampled or probe.pages_scanned or 1} sampled page(s) "
                f"({inventory.internal_link_count} internal · {inventory.external_link_count} external anchors seen)"
            ),
            class_=FindingClass.INFO,
            scored=False,
            evidence={"internal_links_sample": inventory.internal_links_sample},
        ),
        Finding.from_check(
            category="MISC",
            item="Image inventory",
            status="COUNTED",
            severity=Severity.INFO,
            detail=(
                f"{len(inventory.images)} unique asset(s) including favicons/OG "
                f"({inventory.image_count} <img> tags on homepage)"
            ),
            class_=FindingClass.INFO,
            scored=False,
        ),
    ]

    if inventory.form_count:
        findings.append(
            Finding.from_check(
                category="HTML",
                item="Forms",
                status="PRESENT",
                severity=Severity.INFO,
                detail=f"{inventory.form_count} HTML form(s) on homepage",
                class_=FindingClass.INFO,
                scored=False,
            )
        )

    if settings.check_mixed_content and inventory.mixed_content_count:
        findings.append(
            Finding.from_check(
                category="HTML",
                item="Mixed content",
                status="FOUND",
                severity=Severity.MEDIUM,
                detail=(
                    f"{inventory.mixed_content_count} HTTP resource reference(s) on HTTPS page — "
                    "browsers may block or warn"
                ),
                class_=FindingClass.ACTION,
                scored=True,
                evidence={"samples": inventory.mixed_content_samples},
            )
        )

    if settings.check_forms and inventory.insecure_form_actions:
        findings.append(
            Finding.from_check(
                category="HTML",
                item="Insecure form action",
                status="HTTP",
                severity=Severity.MEDIUM,
                detail="Form submits to cleartext HTTP from HTTPS page",
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"actions": inventory.insecure_form_actions},
            )
        )

    return findings

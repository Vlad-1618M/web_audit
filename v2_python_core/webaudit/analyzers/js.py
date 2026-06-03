"""JS render analyzer — client-rendered DOM signal vs static HTML.

What: ``analyze_js_render()`` compares Playwright-rendered inventory to static HTML.
Where: ``pipeline._step_js`` after ``collect_js_render()``.
How: INFO/VERIFY only — SPA-heavy sites may show more links after JS execution.
"""

from __future__ import annotations

from webaudit.collectors.js import JsRenderResult
from webaudit.config.settings import JsCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_js_render(
    probe: JsRenderResult,
    settings: JsCollectorSettings,
    *,
    static_link_count: int = 0,
) -> list[Finding]:
    if not settings.enabled:
        return []

    if probe.skipped:
        return [
            Finding.from_check(
                category="HTML",
                item="JS render pass",
                status="SKIPPED",
                severity=Severity.INFO,
                detail=probe.error or "Playwright JS pass skipped",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"error_code": probe.error_code, "fix_steps": probe.fix_steps},
            )
        ]

    if probe.error:
        detail = probe.error
        if probe.fix_steps:
            detail = f"{probe.error} Fix: {' → '.join(probe.fix_steps[:2])}"
        return [
            Finding.from_check(
                category="HTML",
                item="JS render pass",
                status="ERROR",
                severity=Severity.INFO,
                detail=detail[:300],
                class_=FindingClass.INFO,
                scored=False,
                evidence={
                    "error_code": probe.error_code,
                    "fix_steps": probe.fix_steps,
                },
            )
        ]

    findings: list[Finding] = [
        Finding.from_check(
            category="MISC",
            item="JS-rendered DOM",
            status="SCANNED",
            severity=Severity.INFO,
            detail=(
                f"Playwright render: {probe.link_count} link(s), {probe.script_count} script(s) "
                f"after {probe.wait_seconds:g}s wait"
            ),
            class_=FindingClass.INFO,
            scored=False,
            evidence={
                "source": "js",
                "link_count": probe.link_count,
                "script_count": probe.script_count,
                "final_url": probe.final_url,
            },
        )
    ]

    if static_link_count >= 0 and probe.link_count > static_link_count + 2:
        findings.append(
            Finding.from_check(
                category="HTML",
                item="Client-rendered links",
                status="SPA_SIGNAL",
                severity=Severity.INFO,
                detail=(
                    f"Rendered page has {probe.link_count} link(s) vs {static_link_count} in static HTML — "
                    "site may rely on JavaScript for navigation/content"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"source": "js", "static_links": static_link_count, "rendered_links": probe.link_count},
            )
        )

    return findings

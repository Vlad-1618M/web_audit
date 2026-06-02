"""Focus pie chart data for dashboard — slice sizes from live scan scores."""

from __future__ import annotations

import html as html_module
from typing import Any

from webaudit.models.finding import Finding

_SEO_FLOOR = 5.0
_SEO_PER_FINDING = 12.0
_SEO_CAP = 100.0


def _seo_slice_weight(seo_count: int) -> float:
    """Convert SEO finding count to a weight comparable to 0–100 scores."""
    if seo_count <= 0:
        return _SEO_FLOOR
    return min(_SEO_CAP, float(seo_count) * _SEO_PER_FINDING)


def _normalize_pcts(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total <= 0:
        third = round(100 / 3, 1)
        return [third, third, round(100 - 2 * third, 1)]
    raw = [weight / total * 100 for weight in weights]
    rounded = [round(value, 1) for value in raw]
    drift = round(100.0 - sum(rounded), 1)
    if drift:
        rounded[-1] = round(rounded[-1] + drift, 1)
    return rounded


def build_focus_pie_slices(scores: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    """Pie slices sized by hygiene score, leak protection score, and SEO findings."""
    seo_count = sum(1 for finding in findings if finding.category == "SEO_SURFACE")
    weights = [
        float(max(0, scores.hygiene)),
        float(max(0, scores.exposure)),
        _seo_slice_weight(seo_count),
    ]
    pcts = _normalize_pcts(weights)

    slices: list[dict[str, Any]] = [
        {
            "key": "hygiene",
            "label": "Hygiene",
            "sublabel": "config & hardening · higher = better",
            "pct": pcts[0],
            "display": str(scores.hygiene),
            "display_suffix": "/100",
            "color": "#ffc14d",
        },
        {
            "key": "exposure",
            "label": "Leak protection",
            "sublabel": (
                "no sensitive paths leaked · score /100"
                if scores.exposure >= 100
                else "leak protection · higher = safer"
            ),
            "pct": pcts[1],
            "display": str(scores.exposure),
            "display_suffix": "/100",
            "color": "#39ff8c",
        },
        {
            "key": "seo",
            "label": "SEO surface",
            "sublabel": "INFO/VERIFY only · slice grows with finding count",
            "pct": pcts[2],
            "display": str(seo_count),
            "display_suffix": "finding(s)" if seo_count != 1 else "finding",
            "color": "#a855f7",
        },
    ]
    cursor = 0.0
    for slice_ in slices:
        slice_["start_pct"] = cursor
        cursor += slice_["pct"]
        slice_["end_pct"] = cursor
    return slices


def focus_pie_conic_gradient(slices: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for slice_ in slices:
        parts.append(f"{slice_['color']} {slice_['start_pct']}% {slice_['end_pct']}%")
    return f"conic-gradient({', '.join(parts)})"


def focus_pie_chart_html(*, gradient: str, hygiene: int, exposure: int) -> str:
    """Pre-render chart div so templates avoid Jinja inside CSS `style` attributes."""
    aria = html_module.escape(
        f"Scan focus: Hygiene {hygiene} of 100, Leak protection {exposure} of 100, SEO surface informational"
    )
    return (
        f'<div class="focus-pie-chart" style="background: {gradient}" '
        f'role="img" aria-label="{aria}"></div>'
    )

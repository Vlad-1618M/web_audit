"""Focus pie chart data for dashboard — mirrors docs/diagrams product focus split."""

from __future__ import annotations

from typing import Any

from webaudit.models.finding import Finding


def build_focus_pie_slices(scores: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    """Three-slice focus model: Hygiene 70% · Exposure 25% · SEO 5% (legend shows live values)."""
    seo_count = sum(1 for finding in findings if finding.category == "SEO_SURFACE")
    slices: list[dict[str, Any]] = [
        {
            "key": "hygiene",
            "label": "Hygiene",
            "sublabel": "config & hardening · higher = better",
            "pct": 70,
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
            "pct": 25,
            "display": str(scores.exposure),
            "display_suffix": "/100",
            "color": "#39ff8c",
        },
        {
            "key": "seo",
            "label": "SEO surface",
            "sublabel": "INFO/VERIFY only",
            "pct": 5,
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

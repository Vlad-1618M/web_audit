"""Jinja2 environment for report templates.

What: ``get_jinja_env()`` loads templates from ``webaudit/templates/reports/``.
Where: Used exclusively by ``render/html.py``.
How: FileSystemLoader per variant subdirectory; autoescape enabled for HTML reports.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

_SUPPORTED_VARIANTS = frozenset({"technical", "executive", "minimal", "dashboard", "digest"})


def templates_root() -> Path:
    return Path(__file__).resolve().parents[1] / "templates" / "reports"


def resolve_variant(variant: str) -> str:
    if variant in _SUPPORTED_VARIANTS:
        return variant
    return "technical"


def get_jinja_env(variant: str) -> Environment:
    variant = resolve_variant(variant)
    root = templates_root()
    template_dir = root / variant
    shared_dir = root / "_shared"
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Report template directory not found: {template_dir}")
    loaders = [FileSystemLoader(str(template_dir))]
    if shared_dir.is_dir():
        loaders.append(FileSystemLoader(str(shared_dir)))
    return Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def variant_css_path(variant: str) -> Path:
    variant = resolve_variant(variant)
    css_path = templates_root() / variant / "report.css"
    if not css_path.is_file():
        raise FileNotFoundError(f"Report CSS not found: {css_path}")
    return css_path

"""HTML report renderer — Jinja2 templates from ``AuditRun``.

What: ``render_html()`` and ``write_html_report()`` produce ``report.html`` + ``report.css``.
Where: Called from ``storage/runs.write_audit_run()`` when ``html`` is in output formats.
How: Context from ``render/context.py``; CSS copied beside HTML in the run directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from webaudit.models.run import AuditRun
from webaudit.render.context import build_report_context
from webaudit.render.jinja_env import get_jinja_env, resolve_variant, variant_css_path


def render_html(run: AuditRun, *, variant: str = "technical", theme: str = "dark") -> str:
    variant = resolve_variant(variant)
    env = get_jinja_env(variant)
    template = env.get_template("report.html")
    context = build_report_context(run, variant=variant, theme=theme)
    return template.render(**context)


def write_html_report(
    run: AuditRun,
    run_dir: Path,
    *,
    variant: str = "technical",
    theme: str = "dark",
) -> Path:
    html_path = run_dir / "report.html"
    css_path = run_dir / "report.css"
    html_path.write_text(render_html(run, variant=variant, theme=theme), encoding="utf-8")
    shutil.copy2(variant_css_path(variant), css_path)
    return html_path

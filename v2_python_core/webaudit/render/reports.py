"""Shared report output — HTML, TXT, and optional PDF for a run directory.

What: ``write_run_reports()`` writes requested formats beside ``audit_run.json``.
Where: ``storage/runs.write_audit_run()`` after scan; ``webaudit report`` CLI for re-render.
How: Delegates to ``render/html.py``, ``render/txt.py``, ``render/pdf.py``.
"""

from __future__ import annotations

from pathlib import Path

from webaudit.models.run import AuditRun


def write_run_reports(
    run: AuditRun,
    run_dir: Path,
    *,
    formats: list[str],
    report_variant: str = "technical",
    report_theme: str = "dark",
) -> tuple[dict[str, str], list[str]]:
    """Write report artifacts into ``run_dir``; return relative names and warnings."""
    wanted = set(formats)
    reports: dict[str, str] = {}
    warnings: list[str] = []

    need_html = "html" in wanted or "pdf" in wanted
    if need_html:
        from webaudit.render.html import write_html_report

        write_html_report(
            run,
            run_dir,
            variant=report_variant,
            theme=report_theme,
        )
        reports["html"] = "report.html"

    if "txt" in wanted:
        from webaudit.render.txt import write_txt_report

        write_txt_report(
            run,
            run_dir,
            variant=report_variant,
            theme=report_theme,
        )
        reports["txt"] = "report.txt"

    if "pdf" in wanted:
        from webaudit.render.pdf import PdfExportError, pdf_export_available, write_pdf_report

        if not pdf_export_available():
            warnings.append(
                "Server PDF skipped (WeasyPrint not installed). "
                "Open report.html and use Print / Save as PDF, or: pip install 'webaudit[pdf]'"
            )
        else:
            try:
                write_pdf_report(run_dir)
                reports["pdf"] = "report.pdf"
            except PdfExportError as exc:
                warnings.append(str(exc))

    if "html" not in wanted and "html" in reports:
        del reports["html"]

    return reports, warnings

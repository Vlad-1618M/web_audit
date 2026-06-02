"""PDF report export — WeasyPrint render from HTML + CSS in the run directory.

What: ``write_pdf_report()`` converts ``report.html`` + ``report.css`` to ``report.pdf``.
Where: Called from ``storage/runs.write_audit_run()`` when ``pdf`` is in ``output.formats``.
How: Optional dependency — ``pip install 'webaudit[pdf]'`` (WeasyPrint + system libs).
"""

from __future__ import annotations

from pathlib import Path


class PdfExportError(RuntimeError):
    """Raised when PDF export is requested but cannot complete."""


def pdf_export_available() -> bool:
    try:
        import weasyprint  # noqa: F401

        return True
    except ImportError:
        return False


def write_pdf_report(
    run_dir: Path,
    *,
    html_name: str = "report.html",
    css_name: str = "report.css",
    pdf_name: str = "report.pdf",
) -> Path:
    """Render ``report.pdf`` from HTML/CSS files already written in ``run_dir``."""
    html_path = run_dir / html_name
    css_path = run_dir / css_name
    pdf_path = run_dir / pdf_name

    if not html_path.is_file():
        raise PdfExportError(f"HTML report not found for PDF export: {html_path}")

    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise PdfExportError(
            "PDF export requires WeasyPrint. Install with: pip install 'webaudit[pdf]' "
            "(see docs/stages.md for system library notes on macOS/Linux)."
        ) from exc

    stylesheets = [CSS(filename=str(css_path))] if css_path.is_file() else None
    HTML(filename=str(html_path)).write_pdf(str(pdf_path), stylesheets=stylesheets)
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        raise PdfExportError(f"PDF export produced no output: {pdf_path}")
    return pdf_path

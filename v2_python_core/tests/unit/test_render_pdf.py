"""Tests for PDF report export."""
from __future__ import annotations
import sys
from unittest.mock import MagicMock, patch
import pytest
from webaudit.models.finding import Finding, Severity
from webaudit.models.run import AuditMeta, AuditRun, AuditScores
from webaudit.render.html import write_html_report
from webaudit.render.pdf import PdfExportError, pdf_export_available, write_pdf_report
from webaudit.storage.runs import write_audit_run

def _sample_run() -> AuditRun:
    return AuditRun(meta=AuditMeta(target_url='https://example.com', started_at='2026-05-29T12:00:00+00:00', finished_at='2026-05-29T12:00:05+00:00', webaudit_version='2.0.0a1', framework='django'), scores=AuditScores(hygiene=78, exposure=100, verdict='NEEDS_ATTENTION'), findings=[Finding.from_check(category='HEADERS', item='Content-Security-Policy', status='MISSING', severity=Severity.HIGH)])

def test_pdf_export_available_without_weasyprint():
    """Ensures PDF Export Available Without Weasyprint."""
    with patch.dict(sys.modules, {'weasyprint': None}):
        assert pdf_export_available() is False

def test_write_pdf_report_missing_html(tmp_path):
    """Ensures Write PDF Report Missing HTML."""
    with pytest.raises(PdfExportError, match='HTML report not found'):
        write_pdf_report(tmp_path)

def test_write_pdf_report_missing_weasyprint(tmp_path):
    """Ensures Write PDF Report Missing Weasyprint."""
    write_html_report(_sample_run(), tmp_path)
    with patch.dict(sys.modules, {'weasyprint': None}):
        with pytest.raises(PdfExportError, match='WeasyPrint'):
            write_pdf_report(tmp_path)

def test_write_pdf_report_calls_weasyprint(tmp_path):
    """Ensures Write PDF Report Calls Weasyprint."""
    write_html_report(_sample_run(), tmp_path)
    mock_html_cls = MagicMock()
    mock_css_cls = MagicMock()
    fake_weasyprint = MagicMock(HTML=mock_html_cls, CSS=mock_css_cls)

    def _write_pdf(path, *, stylesheets=None):
        from pathlib import Path
        Path(path).write_bytes(b'%PDF-1.4 mock')
    mock_html_cls.return_value.write_pdf.side_effect = _write_pdf
    with patch.dict(sys.modules, {'weasyprint': fake_weasyprint}):
        pdf_path = write_pdf_report(tmp_path)
    assert pdf_path == tmp_path / 'report.pdf'
    mock_html_cls.assert_called_once_with(filename=str(tmp_path / 'report.html'))
    mock_css_cls.assert_called_once_with(filename=str(tmp_path / 'report.css'))
    mock_html_cls.return_value.write_pdf.assert_called_once()

def test_write_audit_run_pdf_only_writes_html_but_not_in_reports(tmp_path):
    """Ensures Write Audit Run PDF Only Writes HTML But Not In Reports."""
    mock_html_cls = MagicMock()
    mock_css_cls = MagicMock()
    fake_weasyprint = MagicMock(HTML=mock_html_cls, CSS=mock_css_cls)

    def _write_pdf(path, *, stylesheets=None):
        from pathlib import Path
        Path(path).write_bytes(b'%PDF-1.4 mock')
    mock_html_cls.return_value.write_pdf.side_effect = _write_pdf
    with patch.dict(sys.modules, {'weasyprint': fake_weasyprint}):
        _, reports, warnings = write_audit_run(_sample_run(), output_dir=tmp_path, formats=['json', 'pdf'])
    assert 'pdf' in reports
    assert 'html' not in reports
    assert not warnings
    run_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / 'report.html').is_file()
    assert (run_dir / 'report.pdf').is_file()

def test_write_audit_run_pdf_skipped_without_weasyprint(tmp_path):
    """Ensures Write Audit Run PDF Skipped Without Weasyprint."""
    with patch.dict(sys.modules, {'weasyprint': None}):
        _, reports, warnings = write_audit_run(_sample_run(), output_dir=tmp_path, formats=['json', 'html', 'pdf'])
    assert 'html' in reports
    assert 'pdf' not in reports
    assert len(warnings) == 1
    assert 'WeasyPrint' in warnings[0]

@pytest.mark.optional_pdf
def test_write_pdf_report_integration(tmp_path):
    """Ensures Write PDF Report Integration."""
    pytest.importorskip('weasyprint')
    write_html_report(_sample_run(), tmp_path)
    pdf_path = write_pdf_report(tmp_path)
    assert pdf_path.stat().st_size > 1000

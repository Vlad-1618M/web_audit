"""Tests for all report template variants, TXT export, and audit_run loading."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from typer.testing import CliRunner
from webaudit.cli.main import app
from webaudit.models.finding import Finding, Severity
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html, write_html_report
from webaudit.render.reports import write_run_reports
from webaudit.render.txt import render_txt, write_txt_report
from webaudit.storage.runs import load_audit_run, write_audit_run

def _sample_run() -> AuditRun:
    return AuditRun(meta=AuditMeta(target_url='https://example.com', started_at='2026-05-29T12:00:00+00:00', finished_at='2026-05-29T12:00:05+00:00', webaudit_version='2.0.0a1', framework='django'), scores=AuditScores(hygiene=78, exposure=100, verdict='NEEDS_ATTENTION'), findings=[Finding.from_check(category='HEADERS', item='Content-Security-Policy', status='MISSING', severity=Severity.HIGH), Finding.from_check(category='DNS', item='DMARC', status='MISSING', severity=Severity.MEDIUM)], artifacts=AuditArtifacts(dns={'records': {'spf': 'v=spf1 -all', 'dmarc': None}}, tls={'certificate': {'days_left': 90}, 'versions': []}, inventory={'paths': {'probe_count': 12}, 'html': {'pages_scanned': 1}}))

@pytest.mark.parametrize('variant', ['owner', 'technical', 'executive', 'minimal', 'dashboard', 'digest'])
def test_render_all_html_variants(variant: str):
    """Ensures Render All HTML Variants."""
    html = render_html(_sample_run(), variant=variant)
    assert 'https://example.com' in html
    assert 'report.css' in html

def test_render_txt_contains_scores_and_findings():
    """Ensures Render TXT Contains Scores And Findings."""
    text = render_txt(_sample_run(), variant='technical')
    assert 'Hygiene:' in text
    assert 'Content-Security-Policy' in text
    assert 'Web Audit Report' in text

def test_write_run_reports_html_and_txt(tmp_path):
    """Ensures Write Run Reports HTML And TXT."""
    reports, warnings = write_run_reports(_sample_run(), tmp_path, formats=['html', 'txt'], report_variant='minimal')
    assert warnings == []
    assert (tmp_path / reports['html']).is_file()
    assert (tmp_path / reports['txt']).is_file()
    assert (tmp_path / 'report.css').is_file()

def test_load_audit_run_roundtrip(tmp_path):
    """Ensures Load Audit Run Roundtrip."""
    run = _sample_run()
    json_path, _, _ = write_audit_run(run, output_dir=tmp_path, formats=['json'])
    loaded = load_audit_run(json_path)
    assert loaded.meta.target_url == run.meta.target_url
    assert len(loaded.findings) == len(run.findings)
    assert loaded.scores.hygiene == run.scores.hygiene

def test_build_report_context_dashboard_fields():
    """Ensures Build Report Context Dashboard Fields."""
    ctx = build_report_context(_sample_run(), variant='dashboard', theme='dark')
    assert ctx['category_health']
    assert ctx['action_count'] == 2
    assert ctx['probe_count'] == 12

def test_report_cli_renders_from_json(tmp_path):
    """Ensures Report CLI Renders From JSON."""
    run = _sample_run()
    json_path, _, _ = write_audit_run(run, output_dir=tmp_path, formats=['json'])
    runner = CliRunner()
    result = runner.invoke(app, ['report', str(json_path), '--variant', 'digest', '--formats', 'html,txt'])
    assert result.exit_code == 0, result.output
    run_dir = json_path.parent
    assert (run_dir / 'report.html').is_file()
    assert (run_dir / 'report.txt').is_file()

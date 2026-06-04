"""Tests for JS render section in technical reports."""
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html
from webaudit.render.js_display import build_js_section

def _base_run(**artifact_inventory) -> AuditRun:
    inventory = {'html': {'pages_scanned': 1, 'inventory': {'link_count': 5, 'site_links': []}}, **artifact_inventory}
    return AuditRun(meta=AuditMeta(target_url='https://example.com', framework='unknown', started_at='2026-05-29T12:00:00+00:00', webaudit_version='2.1.0b1'), scores=AuditScores(hygiene=80, exposure=100, verdict='OK'), findings=[], artifacts=AuditArtifacts(inventory=inventory))

def test_js_section_not_used():
    """Ensures Js Section Not Used."""
    section = build_js_section({'inventory': {'html': {'inventory': {'link_count': 5}}}}, target_url='https://example.com')
    assert section['status'] == 'not_used'
    assert any(('--js' in step for step in section['fix_steps']))
    assert section['inventory_rows'] == []

def test_js_section_ok_adds_inventory_rows():
    """Ensures Js Section Ok Adds Inventory Rows."""
    section = build_js_section({'inventory': {'html': {'inventory': {'link_count': 2}}, 'js': {'link_count': 12, 'script_count': 4, 'wait_seconds': 3, 'skipped': False}}}, target_url='https://example.com', findings=[Finding.from_check(category='HTML', item='Client-rendered links', status='SPA_SIGNAL', severity=Severity.INFO, class_=FindingClass.VERIFY)])
    assert section['status'] == 'ok'
    assert section['spa_signal'] is True
    assert len(section['inventory_rows']) == 4
    assert section['fix_steps'] == []

def test_render_technical_shows_js_not_used():
    """Ensures Render Technical Shows Js Not Used."""
    html = render_html(_base_run(), variant='technical')
    assert 'id="js-render"' in html
    assert 'JavaScript render pass not run' in html
    assert 'webaudit scan https://example.com --js' in html
    assert '/Users/' not in html

def test_render_technical_shows_js_ran():
    """Ensures Render Technical Shows Js Ran."""
    run = _base_run(js={'link_count': 10, 'script_count': 3, 'wait_seconds': 3})
    ctx = build_report_context(run, variant='technical', theme='dark')
    assert any((row['bucket'].startswith('JS rendered') for row in ctx['inventory_rows']))
    html = render_html(run, variant='technical')
    assert 'JavaScript render pass completed' in html
    assert 'js-render-panel' in html
    assert 'js-render-stats' in html

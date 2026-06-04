"""Tests for API probe section in technical reports."""
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.render.api_display import build_api_section
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html

def _base_run(**artifact_inventory) -> AuditRun:
    inventory = {'html': {'pages_scanned': 1, 'inventory': {'link_count': 5, 'site_links': []}}, **artifact_inventory}
    return AuditRun(meta=AuditMeta(target_url='https://example.com', framework='unknown', started_at='2026-05-29T12:00:00+00:00', webaudit_version='2.1.0b2'), scores=AuditScores(hygiene=80, exposure=100, verdict='OK'), findings=[], artifacts=AuditArtifacts(inventory=inventory))

def test_api_section_not_used():
    """Ensures API Section Not Used."""
    section = build_api_section({'inventory': {'html': {'inventory': {'link_count': 5}}}}, target_url='https://example.com')
    assert section['status'] == 'not_used'
    assert any(('--api' in step for step in section['enable_steps']))
    assert section['inventory_rows'] == []
    assert section['graphql_rows'] == []

def test_api_section_clean_run():
    """Ensures API Section Clean Run."""
    section = build_api_section({'inventory': {'api': {'graphql': [{'path': '/graphql', 'status_code': 404, 'introspection_enabled': False}], 'openapi': [{'path': '/openapi.json', 'status_code': 404, 'openapi_detected': False}]}}}, target_url='https://example.com')
    assert section['status'] == 'ok'
    assert len(section['stats']) == 4
    assert len(section['inventory_rows']) == 4
    assert section['graphql_rows'][0]['tone'] == 'good'

def test_api_section_warn_on_introspection():
    """Ensures API Section Warn On Introspection."""
    section = build_api_section({'inventory': {'api': {'graphql': [{'path': '/graphql', 'status_code': 200, 'introspection_enabled': True}], 'openapi': []}}}, target_url='https://example.com', findings=[Finding.from_check(category='API', item='/graphql', status='INTROSPECTION', severity=Severity.HIGH, class_=FindingClass.VERIFY)])
    assert section['status'] == 'warn'
    assert section['has_verify'] is True
    assert section['graphql_rows'][0]['result'] == 'Introspection open'

def test_render_technical_shows_api_not_used():
    """Ensures Render Technical Shows API Not Used."""
    html = render_html(_base_run(), variant='technical')
    assert 'id="api-probes"' in html
    assert 'API surface probes not run' in html
    assert 'webaudit scan https://example.com --api' in html

def test_render_technical_shows_api_ran():
    """Ensures Render Technical Shows API Ran."""
    run = _base_run(api={'graphql': [{'path': '/graphql', 'status_code': 200, 'introspection_enabled': False}], 'openapi': [{'path': '/openapi.json', 'status_code': 200, 'openapi_detected': True, 'title': 'Example API', 'version': '1.0.0'}]})
    ctx = build_report_context(run, variant='technical', theme='dark')
    assert any(('API OpenAPI specs exposed' in row['bucket'] for row in ctx['inventory_rows']))
    html = render_html(run, variant='technical')
    assert 'API surface exposure detected' in html
    assert 'api-probe-panel' in html
    assert 'Example API' in html
    assert 'href="#findings-verify"' in html

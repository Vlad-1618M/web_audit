"""Tests for HTML report rendering."""
from pathlib import Path

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html, write_html_report
from tests.url_helpers import assert_html_references_url

def _sample_run() -> AuditRun:
    return AuditRun(meta=AuditMeta(target_url='https://example.com', started_at='2026-05-29T12:00:00+00:00', finished_at='2026-05-29T12:00:05+00:00', webaudit_version='2.0.0a1', framework='django'), scores=AuditScores(hygiene=78, exposure=100, verdict='NEEDS_ATTENTION'), findings=[Finding.from_check(category='HEADERS', item='Content-Security-Policy', status='MISSING', severity=Severity.HIGH), Finding.from_check(category='DNS', item='DMARC', status='MISSING', severity=Severity.MEDIUM)], artifacts=AuditArtifacts(dns={'records': {'spf': 'v=spf1 -all', 'dmarc': None}}, tls={'certificate': {'subject': 'CN=example.com', 'days_left': 90}, 'versions': [{'version': '1.3', 'supported': True}]}, inventory={'framework': {'confidence': 'high', 'cdn': 'Cloudflare'}, 'paths': {'probe_count': 2, 'paths': [{'path': '/.env', 'final_status': 404, 'note': 'NOT_FOUND'}]}}))

def test_build_report_context_groups_action_findings():
    """Ensures Build Report Context Groups Action Findings."""
    ctx = build_report_context(_sample_run(), variant='technical', theme='dark')
    assert len(ctx['action_findings']) == 2
    assert ctx['verdict_label'] == 'Needs attention'

def test_render_technical_html_contains_target_and_findings():
    """Ensures Render Technical HTML Contains Target And Findings."""
    run = _sample_run()
    html = render_html(run, variant='technical')
    assert_html_references_url(html, run.meta.target_url)
    assert 'Content-Security-Policy' in html
    assert 'NEEDS_ATTENTION' in html
    assert 'href="report.css"' in html
    assert 'Sender Policy Framework' in html
    assert 'class="sev HIGH"' in html

def test_render_technical_includes_certificate_summary():
    """Ensures Render Technical Includes Certificate Summary."""
    run = _sample_run()
    run.artifacts.tls = {'host': 'example.com', 'certificate': {'subject_cn': 'example.com', 'issuer_display': "Let's Encrypt", 'issuer': "CN=R3,O=Let's Encrypt,C=US", 'not_before': '2026-01-01T00:00:00+00:00', 'not_after': '2026-07-01T00:00:00+00:00', 'days_left': 90, 'status': 'VALID', 'hostname_match': True, 'san': ['example.com', 'www.example.com'], 'chain_length': 2}, 'versions': [{'version': '1.3', 'supported': True}]}
    html = render_html(run, variant='technical')
    assert 'HTTPS certificate' in html
    assert 'Let' in html and 'Encrypt' in html
    assert 'Valid until' in html
    assert 'days left' in html.lower()

def test_render_technical_includes_extensions_and_discovery():
    """Ensures Render Technical Includes Extensions And Discovery."""
    run = _sample_run()
    run.meta.framework = 'wordpress'
    run.artifacts.extensions = {'framework': 'wordpress', 'unit': 'plugin', 'extension_count': 1, 'extensions': [{'name': 'elementor', 'version': '3.20.0', 'source': 'html', 'unit': 'plugin'}]}
    run.artifacts.inventory['html'] = {'pages_scanned': 1, 'inventory': {'site_links': [{'url': 'https://example.com/about', 'kind': 'internal', 'source': 'homepage'}], 'images': [{'url': 'https://example.com/favicon.ico', 'kind': 'favicon', 'source': '/'}], 'internal_link_count': 1, 'external_link_count': 0}}
    run.findings.append(Finding.from_check(category='PLUGIN', item='elementor', status='STALE', severity=Severity.MEDIUM, detail='Behind latest'))
    html = render_html(run, variant='technical')
    assert 'WordPress Plugins' in html
    assert 'version check' in html
    assert 'WordPress.org Plugin Directory' in html
    assert 'elementor' in html
    assert 'View on registry' in html
    assert 'Site discovery' in html
    assert 'Security probe URLs' in html
    assert 'favicon.ico' in html
    assert 'target="_blank"' in html
    assert 'class="http-status http-4xx"' in html
    assert 'class="probe-note good"' in html or 'class="probe-hint good"' in html

def test_render_executive_html():
    """Ensures Render Executive HTML."""
    html = render_html(_sample_run(), variant='executive')
    assert 'Executive summary' in html
    assert 'Configuration score' in html
    assert 'What this report is (and is not)' in html
    assert 'Discoverability' in html
    assert 'OWASP ZAP' in html
    assert 'report-footer-brand' in html
    assert 'href="https://muzar.io/"' in html
    assert 'Passive external scan only' in html

def test_render_owner_pass_verdict_banner_is_green(tmp_path: Path):
    """Pass verdict uses green executive-summary banner styling (not default gold)."""
    run = AuditRun(
        meta=AuditMeta(
            target_url='https://example.com',
            started_at='2026-05-29T12:00:00+00:00',
            finished_at='2026-05-29T12:00:05+00:00',
            webaudit_version='2.1.0b4',
            framework='generic',
        ),
        scores=AuditScores(hygiene=91, exposure=100, verdict='PASS'),
        findings=[
            Finding.from_check(
                category='HEADERS',
                item='Strict-Transport-Security',
                status='MISSING',
                severity=Severity.MEDIUM,
            ),
        ],
        artifacts=AuditArtifacts(),
    )
    html = render_html(run, variant='owner')
    assert 'class="verdict-banner pass"' in html
    assert 'class="score-cell v pass"' in html
    assert 'No obvious sensitive files were publicly readable' in html

    write_html_report(run, tmp_path, variant='owner')
    css = (tmp_path / 'report.css').read_text(encoding='utf-8')
    assert '.verdict-banner.pass' in css
    assert '.score-cell.v.pass .n' in css
    assert 'color: var(--lime)' in css


def test_render_owner_combined_report():
    """Ensures Render Owner Combined Report."""
    html = render_html(_sample_run(), variant='owner')
    assert 'Security dashboard' in html
    assert 'Executive summary' in html
    assert 'Scan focus' in html
    assert 'Finding status' in html
    assert 'focus-pie-chart' in html
    assert 'Critical' in html
    assert 'discovery-row-pair' in html
    assert 'Priority timeline' in html
    assert 'Discoverability' in html
    assert 'Security digest' not in html
    assert 'Score rings' not in html
    assert 'Technical details' in html
    assert 'id="page-overview"' in html
    assert 'id="page-technical"' in html
    assert 'sidebar-resizer' in html
    assert 'class="alert-link-' in html or 'class="alert-link alert-link-' in html
    assert 'How to read this report' in html
    assert 'owner-overview-footer' in html
    assert 'Generated by Web Audit v' in html
    assert 'total findings' in html
    assert 'href="https://muzar.io/"' in html
    assert '>muzar.io</a>' in html
    assert 'Web Security Audit Pro' in html

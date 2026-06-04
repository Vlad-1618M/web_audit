"""Tests for report metric chips and footer."""
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.render.report_metrics import build_metric_chips
from webaudit.render.robots_display import build_robots_section
from webaudit.render.system_info import build_report_footer, format_report_timestamp

def test_metric_chips_count_severities():
    """Ensures Metric Chips Count Severities."""
    findings = [Finding.from_check(category='HEADERS', item='CSP', status='MISSING', severity=Severity.HIGH), Finding.from_check(category='PATHS', item='.env', status='OPEN', severity=Severity.CRITICAL, class_=FindingClass.ACTION), Finding.from_check(category='SEO_SURFACE', item='meta robots', status='NOINDEX', severity=Severity.INFO, class_=FindingClass.VERIFY)]
    chips = {c['label']: c['count'] for c in build_metric_chips(findings)}
    assert chips['Critical'] == 1
    assert chips['High action'] == 1
    assert chips['Verify'] == 1
    assert chips['SEO checks'] == 1
    assert chips['Plugins'] == 0
    critical = next((c for c in build_metric_chips(findings) if c['label'] == 'Critical'))
    assert critical['anchor'] == 'findings-action'
    assert next((c for c in build_metric_chips(findings) if c['label'] == 'SEO checks'))['anchor'] == 'findings-seo'

def test_robots_section_parses_rules():
    """Ensures Robots Section Parses Rules."""
    section = build_robots_section({'inventory': {'artifacts': {'robots': {'status_code': 200, 'raw': 'User-agent: *\nDisallow: /secret/\nSitemap: https://example.com/sitemap.xml\n'}}}})
    assert section is not None
    assert '/secret/' in section['disallow_rules']
    assert section['summary_tone'] == 'good'

def test_report_footer_branding():
    """Ensures Report Footer Branding."""
    footer = build_report_footer(scanned_at='2026-06-02T14:43:46+00:00')
    assert footer['brand_app_label'] == 'muzar.io'
    assert footer['brand_product'] == 'Web Security Audit Pro'
    assert footer['brand_line'] == (
        f"Created by {footer['brand_app_label']} — {footer['brand_product']} "
        f"v{footer['webaudit_version']} — {footer['report_timestamp']}"
    )
    assert footer['report_timestamp']
    assert footer['webaudit_version']
    assert footer['audit_host']

def test_format_report_timestamp_readable():
    """Ensures Format Report Timestamp Readable."""
    ts = format_report_timestamp('2026-06-02T14:43:46+00:00')
    assert '2026' in ts
    assert 'Jun' in ts

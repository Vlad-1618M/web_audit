"""Tests for finding table display tones and TLS result colors."""
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.render.finding_display import enrich_findings_table, finding_status_tone, format_finding_detail_html, tls_result_tone

def test_verify_open_path_status_is_bad():
    """Ensures Verify Open Path Status Is Bad."""
    finding = Finding.from_check(category='PATHS', item='wp-content/', status='OPEN', severity=Severity.MEDIUM, class_=FindingClass.VERIFY, scored=False)
    assert finding_status_tone(finding, section='verify') == 'bad'

def test_expected_open_status_is_good():
    """Ensures Expected Open Status Is Good."""
    finding = Finding.from_check(category='PATHS', item='robots.txt', status='OPEN', severity=Severity.INFO, class_=FindingClass.EXPECTED, scored=False)
    assert finding_status_tone(finding, section='expected') == 'good'

def test_verify_detail_highlights_unexpected_open_path():
    """Ensures Verify Detail Highlights Unexpected Open Path."""
    finding = Finding.from_check(category='PATHS', item='wp-json/', status='OPEN', severity=Severity.MEDIUM, detail='Unexpected open path — raw 200 → final 200; verify public access is intended', class_=FindingClass.VERIFY, scored=False)
    html = format_finding_detail_html(finding, section='verify')
    assert 'class="finding-detail-bad">Unexpected open path</span>' in html
    assert 'raw 200 → final 200' in html

def test_action_sensitive_path_detail_highlight():
    """Ensures Action Sensitive Path Detail Highlight."""
    finding = Finding.from_check(category='PATHS', item='.env', status='OPEN', severity=Severity.CRITICAL, detail='Sensitive path reachable — raw 200 → final 200 (OPEN)', class_=FindingClass.ACTION, scored=True)
    html = format_finding_detail_html(finding, section='action')
    assert 'class="finding-detail-bad">Sensitive path reachable</span>' in html

def test_tls_certificate_and_hostname_tones():
    """Ensures TLS Certificate And Hostname Tones."""
    assert tls_result_tone('Certificate status', 'VALID') == 'good'
    assert tls_result_tone('Certificate status', 'EXPIRED') == 'bad'
    assert tls_result_tone('Hostname match', 'Yes') == 'good'
    assert tls_result_tone('Hostname match', 'No — CN mismatch') == 'bad'

def test_enrich_findings_table_rows():
    """Ensures Enrich Findings Table Rows."""
    rows = enrich_findings_table([Finding.from_check(category='PLUGIN_VERIFY', item='elementor-pro', status='UNKNOWN', severity=Severity.INFO, class_=FindingClass.VERIFY, scored=False)], 'verify')
    assert rows[0]['status_tone'] == 'warn'

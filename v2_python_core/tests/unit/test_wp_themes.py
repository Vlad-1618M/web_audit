"""Tests for WordPress theme collector, analyzer, and report section."""
from webaudit.analyzers.wp_themes import analyze_wp_themes
from webaudit.collectors.wp_themes import collect_wp_themes, extract_theme_slug_from_html, parse_style_css_header
from webaudit.models.run import AuditArtifacts, AuditMeta, AuditRun, AuditScores
from webaudit.profiles.loader import load_framework_profile
from webaudit.render.context import build_report_context
from webaudit.render.html import render_html
from webaudit.render.theme_display import build_theme_section
_STYLE_CSS = '\n/*\nTheme Name: Test Theme\nTheme URI: https://example.com\nAuthor: Author\nVersion: 1.0.0\nTemplate: avada\nText Domain: test-theme\n*/\nbody {}\n'
_PARENT_STYLE = '\n/*\nTheme Name: Avada\nVersion: 7.11.6\n*/\n'

def test_extract_theme_slug_from_html():
    """Ensures Extract Theme Slug From HTML."""
    html = '<link href="/wp-content/themes/my-child/style.css?ver=1.2" rel="stylesheet">'
    assert extract_theme_slug_from_html(html) == 'my-child'

def test_parse_style_css_header_child_theme():
    """Ensures Parse Style Css Header Child Theme."""
    fields = parse_style_css_header(_STYLE_CSS)
    assert fields['theme_name'] == 'Test Theme'
    assert fields['version'] == '1.0.0'
    assert fields['template'] == 'avada'

def test_collect_wp_themes_parses_child_and_parent(httpx_mock):
    """Ensures Collect WordPress Themes Parses Child And Parent."""
    profile = load_framework_profile('wordpress')
    assert profile is not None
    base = 'https://example.com'
    httpx_mock.add_response(url=f'{base}/wp-content/themes/my-child/style.css', text=_STYLE_CSS)
    httpx_mock.add_response(url=f'{base}/wp-content/themes/avada/style.css', text=_PARENT_STYLE)
    html = '<link href="/wp-content/themes/my-child/style.css?ver=1.2">'
    probe = collect_wp_themes(base, html, profile, user_agent='WebAudit/test', timeout_seconds=5)
    assert probe.active is not None
    assert probe.active.is_child_theme is True
    assert probe.parent is not None
    assert probe.parent.slug == 'avada'
    assert probe.parent.version == '7.11.6'

def test_analyze_wp_themes_child_and_update_trap():
    """Ensures Analyze WordPress Themes Child And Update Trap."""
    profile = load_framework_profile('wordpress')
    assert profile is not None
    from webaudit.collectors.wp_themes import ObservedTheme, WpThemesProbeResult
    probe = WpThemesProbeResult(target_url='https://example.com', active=ObservedTheme(slug='avada', name='Avada', version='7.11.6', is_child_theme=False))
    findings = analyze_wp_themes(probe, profile, user_agent='test', timeout_seconds=5, path_probes=[{'path': '/wp-admin/', 'final_status': 200}])
    statuses = {f.status for f in findings}
    assert 'UPDATE_TRAP_RISK' in statuses
    assert 'EDITOR_UNVERIFIABLE' in statuses
    hardening = next((f for f in findings if f.item == 'wp-config hardening'))
    assert 'DISALLOW_FILE_EDIT' in hardening.detail
    assert 'DISALLOW_FILE_MODS' in hardening.detail
    assert hardening.evidence.get('wp_config_constants') == ['DISALLOW_FILE_EDIT', 'DISALLOW_FILE_MODS']

def test_analyze_wp_themes_stale_free_theme(httpx_mock):
    """Ensures Analyze WordPress Themes Stale Free Theme."""
    profile = load_framework_profile('wordpress')
    assert profile is not None
    from webaudit.collectors.wp_themes import ObservedTheme, WpThemesProbeResult
    httpx_mock.add_response(url='https://api.wordpress.org/themes/info/1.1/?action=theme_information&request[slug]=twentytwentyfour&request[fields][version]=1', json={'version': '1.3'})
    probe = WpThemesProbeResult(target_url='https://example.com', active=ObservedTheme(slug='twentytwentyfour', name='Twenty Twenty-Four', version='1.0.0'))
    findings = analyze_wp_themes(probe, profile, user_agent='test', timeout_seconds=5)
    assert any((f.status == 'STALE' and f.category == 'THEME' for f in findings))

def test_render_technical_shows_theme_section():
    """Ensures Render Technical Shows Theme Section."""
    run = AuditRun(meta=AuditMeta(target_url='https://example.com', framework='wordpress', started_at='2026-06-03T12:00:00+00:00', webaudit_version='2.1.0b2'), scores=AuditScores(hygiene=80, exposure=100, verdict='OK'), findings=[], artifacts=AuditArtifacts(extensions={'framework': 'wordpress', 'themes': {'active': {'slug': 'twentytwentyfour', 'name': 'Twenty Twenty-Four', 'version': '1.2', 'is_child_theme': False}}}))
    ctx = build_report_context(run, variant='technical', theme='dark')
    assert ctx['theme_section'] is not None
    assert ctx['theme_section']['has_rows'] is True
    html = render_html(run, variant='technical')
    assert 'id="themes"' in html
    assert 'WordPress theme' in html

def test_build_theme_section_none_for_non_wp():
    """Ensures Build Theme Section None For Non WordPress."""
    assert build_theme_section({}, [], framework='django') is None

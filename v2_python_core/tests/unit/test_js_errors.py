"""Tests for Playwright error normalization."""
from webaudit.collectors.js_errors import js_error_from_artifact, normalize_js_error
from webaudit.render.js_display import build_js_section
RAW_BROWSER_MISSING = "BrowserType.launch: Executable doesn't exist at /Users/vtool/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell\n╔════════════════════════════════════════════════════════════╗\n║ Looks like Playwright was just installed or updated.       ║\n║ Please run the following command to download new browsers: ║\n║     playwright install chromium                            ║\n╚════════════════════════════════════════════════════════════╝"

def test_normalize_browser_missing_strips_paths():
    """Ensures Normalize Browser Missing Strips Paths."""
    info = normalize_js_error(RAW_BROWSER_MISSING, target_url='https://muzar.io')
    assert info is not None
    assert info.code == 'browser_missing'
    assert '/Users/' not in info.message
    assert 'ms-playwright' not in info.message
    assert '╔' not in info.message
    assert 'playwright install chromium chromium-headless-shell' in info.fix_steps[0]
    assert 'webaudit scan https://muzar.io --js' in info.fix_steps[-1]

def test_js_section_legacy_raw_error_in_artifact():
    """Ensures Js Section Legacy Raw Error In Artifact."""
    section = build_js_section({'inventory': {'html': {'inventory': {'link_count': 5}}, 'js': {'error': RAW_BROWSER_MISSING, 'link_count': 0}}}, target_url='https://muzar.io')
    assert section['status'] == 'error'
    assert '/Users/' not in section['summary']
    assert 'Chromium is not installed' in section['summary']
    assert any(('chromium-headless-shell' in step for step in section['fix_steps']))

def test_js_error_from_artifact_prefers_normalized_fields():
    """Ensures Js Error From Artifact Prefers Normalized Fields."""
    info = js_error_from_artifact({'error_code': 'browser_missing', 'error_message': 'Chromium missing.', 'fix_steps': ['playwright install chromium'], 'error_raw': RAW_BROWSER_MISSING}, target_url='https://example.com')
    assert info is not None
    assert info.message == 'Chromium missing.'
    assert info.fix_steps == ['playwright install chromium']

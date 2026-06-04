"""Integration tests against the local WordPress Docker fixture.

Requires:
  WEBAUDIT_WP_TEST_URL=http://127.0.0.1:8080  (default when using orchestrate.sh)

Start fixture:
  ./orchestrate.sh --job wp-up --wp-profile good
"""
from __future__ import annotations
import pytest
from webaudit.config.settings import load_settings
from webaudit.orchestrator import run_audit

@pytest.mark.integration
def test_wp_fixture_detects_wordpress(wp_test_url: str) -> None:
    """Ensures WordPress Fixture Detects Wordpress."""
    settings = load_settings(target_url=wp_test_url)
    run = run_audit(settings)
    assert run.meta.framework == 'wordpress'

@pytest.mark.integration
def test_wp_fixture_observes_plugins(wp_test_url: str) -> None:
    """Ensures WordPress Fixture Observes Plugins."""
    settings = load_settings(target_url=wp_test_url)
    run = run_audit(settings)
    ext = run.artifacts.extensions or {}
    assert ext.get('framework') == 'wordpress'
    assert int(ext.get('extension_count') or 0) >= 1

@pytest.mark.integration
def test_wp_fixture_theme_section(wp_test_url: str, wp_test_profile: str) -> None:
    """Ensures WordPress Fixture Theme Section."""
    settings = load_settings(target_url=wp_test_url)
    run = run_audit(settings)
    themes = (run.artifacts.extensions or {}).get('themes') or {}
    active = themes.get('active') or {}
    assert active.get('slug'), 'expected active theme slug from HTML/style.css'
    if wp_test_profile in {'good', 'strong'} and (not active.get('is_child_theme')):
        pytest.skip('child theme not active — wp-init scaffold may have failed; check docker logs')

@pytest.mark.integration
def test_wp_fixture_hardening_advisory_when_admin_reachable(wp_test_url: str) -> None:
    """Ensures WordPress Fixture Hardening Advisory When Admin Reachable."""
    settings = load_settings(target_url=wp_test_url)
    run = run_audit(settings)
    hardening = [f for f in run.findings if f.category == 'THEME_VERIFY' and f.item == 'wp-config hardening']
    assert hardening, 'expected wp-config hardening VERIFY when wp-admin/login reachable'
    assert 'DISALLOW_FILE_EDIT' in hardening[0].detail
    assert 'DISALLOW_FILE_MODS' in hardening[0].detail

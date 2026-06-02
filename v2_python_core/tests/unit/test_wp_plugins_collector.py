"""Tests for WordPress plugin collector."""

from webaudit.collectors.wp_plugins import extract_plugins_from_html
from webaudit.profiles.loader import FrameworkProfile, ProfileProbeSettings


def test_extract_plugins_from_html_with_versions():
    html = """
    <link href="/wp-content/plugins/elementor/assets/style.css?ver=3.15.0">
    <script src="https://cdn.example.com/wp-content/plugins/contact-form-7/includes/js/scripts.js?ver=5.8.2"></script>
    <link href="/wp-content/plugins/elementor/assets/widget.css?ver=3.16.1">
    """
    observed = extract_plugins_from_html(html)
    assert observed["elementor"] == "3.16.1"
    assert observed["contact-form-7"] == "5.8.2"


def test_readme_parser_rejects_html_soft_404():
    from webaudit.collectors.wp_plugins import _parse_readme_stable_tag

    html404 = "<!DOCTYPE html><html><title>404</title></html>"
    assert _parse_readme_stable_tag(html404) is None
    assert _parse_readme_stable_tag("=== Plugin ===\nStable tag: 1.2.3\n") == "1.2.3"


def test_collect_wp_plugins_observed_only(monkeypatch):
    from webaudit.collectors import wp_plugins as mod

    profile = FrameworkProfile(
        framework="wordpress",
        probe=ProfileProbeSettings(mode="observed_only", readme_fetch="observed_only"),
    )
    html = '<script src="/wp-content/plugins/akismet/akismet.js?ver=5.3"></script>'

    def _noop_readme(*_args, **_kwargs):
        return None

    monkeypatch.setattr(mod, "_fetch_readme_version", _noop_readme)

    result = mod.collect_wp_plugins(
        "https://example.com",
        html,
        profile,
        user_agent="test",
        timeout_seconds=5,
        client=object(),
    )
    assert len(result.plugins) == 1
    assert result.plugins[0].slug == "akismet"
    assert result.plugins[0].version_html == "5.3"

"""Tests for WordPress plugin/theme CVE analyzer."""
from webaudit.analyzers.plugin_vuln import analyze_wordpress_vulns
from webaudit.config.settings import VulnCollectorSettings
from webaudit.models.finding import FindingClass
from webaudit.profiles.loader import FrameworkProfile, ProfileVulnSettings


def _settings(**kwargs) -> VulnCollectorSettings:
    return VulnCollectorSettings(cache_enabled=False, **kwargs)


def test_unauth_plugin_cve_is_scored_action():
    """Unauthenticated plugin CVE → PLUGIN_CVE ACTION."""
    profile = FrameworkProfile(framework="wordpress")
    ext = {
        "extensions": [{"name": "elementor", "version": "3.25.9", "source": "html"}],
        "themes": {},
    }
    findings, artifact = analyze_wordpress_vulns(
        ext,
        profile,
        _settings(),
        profile_vuln=ProfileVulnSettings(),
    )
    assert artifact["match_count"] >= 1
    cve = next(f for f in findings if f.evidence.get("cve_id") == "CVE-2024-10453")
    assert cve.category == "PLUGIN_CVE"
    assert cve.class_ == FindingClass.ACTION
    assert cve.scored is True


def test_contributor_plugin_cve_is_verify():
    """Contributor-auth CVE → VERIFY, not scored."""
    profile = FrameworkProfile(framework="wordpress", aliases={"wordpress-seo": "yoast-seo"})
    ext = {
        "extensions": [{"name": "yoast-seo", "version": "22.6", "source": "html"}],
        "themes": {},
    }
    findings, _artifact = analyze_wordpress_vulns(
        ext,
        profile,
        _settings(),
        profile_vuln=ProfileVulnSettings(),
    )
    cve = next(f for f in findings if f.evidence.get("cve_id") == "CVE-2024-4984")
    assert cve.class_ == FindingClass.VERIFY
    assert cve.scored is False


def test_theme_cve_match_active_theme():
    """Active theme version matches THEME_CVE finding."""
    profile = FrameworkProfile(framework="wordpress")
    ext = {
        "extensions": [],
        "themes": {
            "active": {"slug": "avada", "version": "7.11.10", "source": "style.css"},
            "parent": None,
        },
    }
    findings, artifact = analyze_wordpress_vulns(
        ext,
        profile,
        _settings(),
        profile_vuln=ProfileVulnSettings(),
    )
    assert artifact["match_count"] == 1
    theme_cve = findings[0]
    assert theme_cve.category == "THEME_CVE"
    assert theme_cve.evidence["cve_id"] == "CVE-2024-13346"


def test_vuln_disabled_returns_empty():
    """Profile vuln.enabled=false skips matching."""
    profile = FrameworkProfile(framework="wordpress")
    ext = {
        "extensions": [{"name": "elementor", "version": "3.25.9", "source": "html"}],
        "themes": {},
    }
    findings, artifact = analyze_wordpress_vulns(
        ext,
        profile,
        _settings(enabled=False),
        profile_vuln=ProfileVulnSettings(enabled=False),
    )
    assert findings == []
    assert artifact == {}

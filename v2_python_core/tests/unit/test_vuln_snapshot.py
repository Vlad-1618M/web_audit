"""Tests for shipped CVE snapshot version matching."""
from webaudit.storage.vuln_snapshot import load_vuln_snapshot, version_is_affected


def test_elementor_unauth_xss_affected_at_3259():
    """Elementor 3.25.9 is within CVE-2024-10453 affected range."""
    snapshot = load_vuln_snapshot()
    record = next(
        item for item in snapshot.plugins if item.cve_id == "CVE-2024-10453"
    )
    assert version_is_affected("3.25.9", record) is True
    assert version_is_affected("3.25.10", record) is False


def test_elementor_pro_rce_range():
    """Elementor Pro 3.18.0 matches unauth RCE fixture."""
    snapshot = load_vuln_snapshot()
    record = next(
        item for item in snapshot.plugins if item.cve_id == "WPVDB-ELEMENTOR-PRO-RCE"
    )
    assert version_is_affected("3.18.0", record) is True
    assert version_is_affected("3.18.3", record) is False


def test_avada_theme_critical_match():
    """Avada 7.11.10 matches shipped theme CVE fixture."""
    snapshot = load_vuln_snapshot()
    record = next(item for item in snapshot.themes if item.cve_id == "CVE-2024-13346")
    assert version_is_affected("7.11.10", record) is True
    assert version_is_affected("7.11.14", record) is False

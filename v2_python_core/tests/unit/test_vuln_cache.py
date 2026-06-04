"""Tests for sqlite vulnerability cache."""
import time

from webaudit.storage.vuln_cache import VulnCache


def test_vuln_cache_roundtrip(tmp_path):
    """Cache stores and returns CVE hits within TTL."""
    cache = VulnCache(tmp_path / "vuln.db", ttl_days=14)
    hits = [{"cve_id": "CVE-TEST-1", "slug": "elementor", "severity": "MEDIUM"}]
    cache.put("plugin", "elementor", "3.25.9", source="snapshot:test", hits=hits)
    loaded = cache.get("plugin", "elementor", "3.25.9", source="snapshot:test")
    assert loaded is not None
    assert loaded.hits[0]["cve_id"] == "CVE-TEST-1"


def test_vuln_cache_expires(tmp_path):
    """Expired cache entries are not returned."""
    cache = VulnCache(tmp_path / "vuln.db", ttl_days=1)
    cache.put("plugin", "elementor", "1.0.0", source="snapshot:test", hits=[{"cve_id": "X"}])
    with cache._connect() as conn:
        conn.execute(
            "UPDATE vuln_lookup SET fetched_at = ? WHERE slug = ?",
            (time.time() - 200_000, "elementor"),
        )
        conn.commit()
    assert cache.get("plugin", "elementor", "1.0.0", source="snapshot:test") is None

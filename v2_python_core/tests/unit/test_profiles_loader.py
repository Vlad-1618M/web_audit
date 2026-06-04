"""Tests for framework profile loader."""
from webaudit.profiles.loader import load_framework_profile

def test_load_wordpress_profile():
    """Ensures Load Wordpress Profile."""
    load_framework_profile.cache_clear()
    profile = load_framework_profile('wordpress')
    assert profile is not None
    assert profile.framework == 'wordpress'
    assert profile.fingerprint_unit == 'plugin'
    assert profile.scoring.hygiene_cap == 30
    assert any((entry.slug == 'elementor' for entry in profile.watchlist))

def test_load_django_profile():
    """Ensures Load Django Profile."""
    load_framework_profile.cache_clear()
    profile = load_framework_profile('django')
    assert profile is not None
    assert profile.fingerprint_unit == 'package'
    assert profile.compare.pypi_api is True
    assert any((entry.name == 'django' for entry in profile.watchlist))

def test_wordpress_alias_normalization():
    """Ensures Wordpress Alias Normalization."""
    load_framework_profile.cache_clear()
    profile = load_framework_profile('wordpress')
    assert profile is not None
    assert profile.normalize_slug('wordpress-seo') == 'yoast-seo'

"""Tests for extension report section and registry URLs."""
from webaudit.analyzers.extension_compare import registry_package_url, registry_meta
from webaudit.models.finding import Finding, Severity
from webaudit.render.extension_display import build_extension_section
from tests.url_helpers import assert_registry_host

def test_registry_package_urls():
    """Ensures Registry Package Urls."""
    assert registry_package_url('wporg', 'elementor') == 'https://wordpress.org/plugins/elementor/'
    assert registry_package_url('pypi', 'django') == 'https://pypi.org/project/django/'
    assert registry_package_url('packagist', 'laravel/framework') == 'https://packagist.org/packages/laravel/framework'
    assert registry_package_url('rubygems', 'rails') == 'https://rubygems.org/gems/rails'

def test_registry_meta_wporg():
    """Ensures Registry Meta Wporg."""
    meta = registry_meta('wporg')
    assert meta is not None
    assert meta['label'] == 'WordPress.org Plugin Directory'

def test_build_extension_section_django():
    """Ensures Build Extension Section Django."""
    findings = [Finding.from_check(category='PACKAGE', item='django', status='STALE', severity=Severity.MEDIUM, detail='django 4.2.0 is behind latest 5.2.0', evidence={'name': 'django', 'version': '4.2.0', 'latest': '5.2.0', 'registry': 'pypi'})]
    section = build_extension_section({'extensions': {'framework': 'django', 'unit': 'package', 'extensions': [{'name': 'django', 'version': '4.2.0', 'source': 'debug_page', 'unit': 'package'}]}}, findings, framework='django')
    assert section is not None
    assert section['framework_label'] == 'Django'
    assert section['registry_label'] == 'PyPI (Python Package Index)'
    assert section['compare_enabled'] is True
    assert section['rows'][0]['latest_version'] == '5.2.0'
    assert_registry_host(section['rows'][0]['registry_url'], 'pypi.org')

"""Tests for multi-framework extension collector."""

from webaudit.collectors.extensions.django import collect_django_extensions
from webaudit.collectors.extensions.laravel import collect_laravel_extensions
from webaudit.profiles.loader import FrameworkProfile, load_framework_profile


def test_django_debug_page_signal():
    profile = load_framework_profile("django")
    assert profile is not None
    html = "<html><body>You're seeing this error because you have DEBUG = True</body></html>"
    probe = collect_django_extensions("https://example.com", html, profile)
    assert any(signal.key == "debug_page" for signal in probe.signals)
    assert probe.unit == "package"


def test_django_version_extracted():
    profile = load_framework_profile("django")
    assert profile is not None
    html = "<!-- Django 4.2.11 -->"
    probe = collect_django_extensions("https://example.com", html, profile)
    assert probe.extensions[0].name == "django"
    assert probe.extensions[0].version == "4.2.11"


def test_laravel_whoops_signal():
    profile = FrameworkProfile(framework="laravel", signals={"whoops_page": "CRITICAL"})
    html = "<html><body>Whoops\\Exception\\ErrorException</body></html>"
    probe = collect_laravel_extensions("https://example.com", html, profile)
    assert any(signal.key == "whoops_page" for signal in probe.signals)

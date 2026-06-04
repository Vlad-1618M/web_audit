"""Tests for unified extension analyzer."""
from webaudit.analyzers.extensions import analyze_extensions
from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult, ObservedExtension
from webaudit.models.finding import FindingClass
from webaudit.profiles.loader import FrameworkProfile, ProfileCompareSettings, WatchlistEntry

class _FakeResponse:

    def __init__(self, status_code: int, payload: dict | None=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

class _FakeClient:

    def __init__(self, versions: dict[str, str | None]):
        self.versions = versions

    def get(self, url, headers=None):
        if 'pypi.org/pypi/django' in url:
            return _FakeResponse(200, {'info': {'version': self.versions.get('django', '5.0')}})
        if 'packagist.org' in url and 'laravel/framework' in url:
            return _FakeResponse(200, {'packages': {'laravel/framework': [{'version': self.versions.get('laravel/framework', '11.0')}]}})
        return _FakeResponse(404)

def test_django_stale_package_action():
    """Ensures Django Stale Package Action."""
    profile = FrameworkProfile(framework='django', compare=ProfileCompareSettings(pypi_api=True), watchlist=[WatchlistEntry(package='django', tier='critical')])
    probe = ExtensionsProbeResult(target_url='https://example.com', framework='django', unit='package', extensions=[ObservedExtension(name='django', version='4.2.0', unit='package')])
    findings = analyze_extensions(probe, profile, user_agent='test', timeout_seconds=5, client=_FakeClient({'django': '5.0'}))
    stale = [f for f in findings if f.status == 'STALE']
    assert len(stale) == 1
    assert stale[0].category == 'PACKAGE'
    assert stale[0].class_ == FindingClass.ACTION

def test_debug_signal_is_scored_critical():
    """Ensures Debug Signal Is Scored Critical."""
    profile = FrameworkProfile(framework='django', signals={'debug_page': 'CRITICAL'})
    probe = ExtensionsProbeResult(target_url='https://example.com', framework='django', unit='package', signals=[ExtensionSignal(key='debug_page', status='EXPOSED', detail='DEBUG visible', severity='CRITICAL')])
    findings = analyze_extensions(probe, profile, user_agent='test', timeout_seconds=5, client=_FakeClient({}))
    debug = [f for f in findings if f.item == 'debug page']
    assert len(debug) == 1
    assert debug[0].scored is True
    assert debug[0].category == 'PACKAGE'

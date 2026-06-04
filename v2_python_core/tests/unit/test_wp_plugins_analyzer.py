"""Tests for WordPress plugin analyzer."""
from webaudit.analyzers.wp_plugins import analyze_wp_plugins
from webaudit.collectors.wp_plugins import ObservedPlugin, WpPluginsProbeResult
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
        slug = url.rsplit('/', 1)[-1].replace('.json', '')
        latest = self.versions.get(slug)
        if latest is None:
            return _FakeResponse(404)
        return _FakeResponse(200, {'version': latest})

def test_stale_free_plugin_is_scored_action():
    """Ensures Stale Free Plugin Is Scored Action."""
    profile = FrameworkProfile(framework='wordpress', compare=ProfileCompareSettings(wporg_api=True), watchlist=[WatchlistEntry(slug='akismet', tier='medium')])
    probe = WpPluginsProbeResult(target_url='https://example.com', plugins=[ObservedPlugin(slug='akismet', version_html='5.0')])
    client = _FakeClient({'akismet': '5.3'})
    findings = analyze_wp_plugins(probe, profile, user_agent='test', timeout_seconds=5, client=client)
    stale = [f for f in findings if f.status == 'STALE']
    assert len(stale) == 1
    assert stale[0].category == 'PLUGIN'
    assert stale[0].class_ == FindingClass.ACTION
    assert stale[0].scored is True

def test_premium_plugin_is_verify_not_scored():
    """Ensures Premium Plugin Is Verify Not Scored."""
    profile = FrameworkProfile(framework='wordpress', watchlist=[WatchlistEntry(slug='wp-rocket', tier='high', premium=True, compare_latest=False)])
    probe = WpPluginsProbeResult(target_url='https://example.com', plugins=[ObservedPlugin(slug='wp-rocket', version_html='3.15')])
    findings = analyze_wp_plugins(probe, profile, user_agent='test', timeout_seconds=5, client=_FakeClient({}))
    assert len(findings) == 1
    assert findings[0].category == 'PLUGIN_VERIFY'
    assert findings[0].class_ == FindingClass.VERIFY
    assert findings[0].scored is False

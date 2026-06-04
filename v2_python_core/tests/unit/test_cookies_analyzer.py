"""Tests for ``webaudit.analyzers.cookies``."""
from webaudit.analyzers.cookies import analyze_cookies
from webaudit.collectors.cookies import CookieEntry, CookiesProbeResult
from webaudit.config.settings import CookiesCollectorSettings
from webaudit.models.finding import FindingClass, Severity

def test_insecure_session_cookie():
    """Ensures Insecure Session Cookie."""
    probe = CookiesProbeResult(target_url='https://example.com', source_url='https://example.com/login/', cookies=[CookieEntry(name='sessionid', raw='sessionid=abc; Path=/')])
    findings = analyze_cookies(probe, CookiesCollectorSettings(), framework='auto')
    f = findings[0]
    assert f.status == 'INSECURE'
    assert f.severity == Severity.HIGH
    assert f.scored is True

def test_secure_cookie_ok():
    """Ensures Secure Cookie Ok."""
    probe = CookiesProbeResult(target_url='https://example.com', cookies=[CookieEntry(name='sid', raw='sid=abc; Path=/; HttpOnly; Secure; SameSite=Lax')])
    findings = analyze_cookies(probe, CookiesCollectorSettings(), framework='auto')
    assert findings[0].status == 'SECURE'

def test_django_csrf_expected():
    """Ensures Django Csrf Expected."""
    probe = CookiesProbeResult(target_url='https://example.com', cookies=[CookieEntry(name='csrftoken', raw='csrftoken=abc; Path=/')])
    findings = analyze_cookies(probe, CookiesCollectorSettings(), framework='django')
    assert findings[0].class_ == FindingClass.EXPECTED
    assert findings[0].scored is False

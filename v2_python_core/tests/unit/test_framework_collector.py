"""Tests for ``webaudit.collectors.framework`` scoring logic."""
from webaudit.collectors.framework import _pick_detected, _score_framework

def test_wordpress_body_signals_win():
    """Ensures Wordpress Body Signals Win."""
    scores = _score_framework(body='<link href="/wp-content/themes/twentytwenty/style.css">', cookie_text='wordpress_logged_in=1', headers={'x-powered-by': 'WordPress'}, admin_body='')
    detected, max_score, signals = _pick_detected(scores)
    assert detected == 'wordpress'
    assert max_score >= 6
    assert 'wp-content' in signals

def test_django_admin_and_csrf_signals():
    """Ensures Django Admin And Csrf Signals."""
    scores = _score_framework(body='input name="csrfmiddlewaretoken"', cookie_text='csrftoken=abc; sessionid=xyz', headers={}, admin_body='Django administration id_username')
    detected, max_score, _signals = _pick_detected(scores)
    assert detected == 'django'
    assert max_score >= 6

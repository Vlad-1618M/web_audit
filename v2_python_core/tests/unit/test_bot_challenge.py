"""Tests for bot-protection page detection."""

from webaudit.collectors.bot_challenge import is_bot_challenge


def test_siteground_captcha_page():
    body = (
        '<html><head><link rel="icon" href="data:;">'
        '<meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/?r=%2F"></meta>'
        "</head></html>"
    )
    assert is_bot_challenge(body, status_code=202) is True


def test_normal_homepage_not_challenge():
    body = "<html><body><a href='/about'>About</a><img src='/logo.png'></body></html>"
    assert is_bot_challenge(body, status_code=200) is False

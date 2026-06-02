"""Detect bot-protection / captcha interstitial pages."""

from __future__ import annotations

_CHALLENGE_MARKERS = (
    "sgcaptcha",
    "challenge-platform",
    "cf-chl",
    "cf-browser-verification",
    "just a moment",
    "attention required",
    "checking your browser",
    "ddos protection",
)


def is_bot_challenge(body: str, *, status_code: int | None = None) -> bool:
    """Return True when the response looks like a WAF/captcha interstitial, not real HTML."""
    if status_code == 202:
        return True

    text = (body or "").strip().lower()
    if not text:
        return False

    if any(marker in text for marker in _CHALLENGE_MARKERS):
        return True

    if len(text) < 512 and "refresh" in text and ("captcha" in text or "sgcaptcha" in text):
        return True

    if status_code in {403, 503} and len(text) < 800:
        return True

    return False


def bot_challenge_detail(*, status_code: int | None = None) -> str:
    code = f"HTTP {status_code}" if status_code else "response"
    return (
        f"Homepage blocked by bot protection ({code}) — "
        "plugin inventory, site URLs, and framework fingerprint may be incomplete"
    )

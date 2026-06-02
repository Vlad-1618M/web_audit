"""Framework fingerprint collector — v1 ``detect_framework()`` parity.

What: ``collect_framework()`` scores Django/WP/Laravel/Rails signals from headers, body, cookies.
Where: Runs early in pipeline (before paths); body reused by HTML analyzer.
How: Reads ``artifacts.headers`` when available; optional ``/admin/`` probe; maps ``php_generic`` → ``php``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_FORCED_FRAMEWORKS = frozenset({"django", "wordpress", "laravel", "rails", "php"})


@dataclass
class FrameworkScores:
    django: int = 0
    wordpress: int = 0
    laravel: int = 0
    rails: int = 0
    signals_d: str = ""
    signals_w: str = ""
    signals_l: str = ""
    signals_r: str = ""


@dataclass
class FrameworkProbeResult:
    target_url: str
    detected: str = "unknown"
    effective_framework: str = "unknown"
    confidence: str = "none"
    signals: str = "no signals"
    language: str = "unknown"
    cdn: str = "none"
    server_header: str = ""
    powered_by: str = ""
    blocked: bool = False
    forced: bool = False
    body: str = ""
    cookie_text: str = ""
    scores: FrameworkScores = field(default_factory=FrameworkScores)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "detected": self.detected,
            "effective_framework": self.effective_framework,
            "confidence": self.confidence,
            "signals": self.signals,
            "language": self.language,
            "cdn": self.cdn,
            "server_header": self.server_header,
            "powered_by": self.powered_by,
            "blocked": self.blocked,
            "forced": self.forced,
            "body_length": len(self.body),
            "body": self.body,
        }


def _header_blob(headers: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in headers.items())


def _detect_cdn(headers: dict[str, str]) -> str:
    blob = _header_blob(headers).lower()
    if "cf-ray:" in blob or "cf-cache-status:" in blob:
        return "Cloudflare"
    if "x-amz-" in blob or "x-amzn-" in blob:
        return "AWS CloudFront"
    if "x-fastly-" in blob or "fastly-" in blob:
        return "Fastly"
    if "x-akamai-" in blob or "akamai-" in blob:
        return "Akamai"
    if re.search(r"via:.*varnish", blob):
        return "Varnish"
    return "none"


def _detect_language(headers: dict[str, str], powered_by: str) -> str:
    blob = _header_blob(headers).lower()
    pb = powered_by.lower()
    if "php" in pb:
        return "PHP"
    if "jsessionid" in blob or "java" in pb:
        return "Java"
    if "express" in pb or "node" in pb:
        return "Node.js"
    if "asp.net" in pb or "x-aspnet" in blob:
        return "ASP.NET"
    if "ruby" in pb or "x-rack" in blob:
        return "Ruby"
    return "unknown"


def _score_framework(
    *,
    body: str,
    cookie_text: str,
    headers: dict[str, str],
    admin_body: str,
) -> FrameworkScores:
    scores = FrameworkScores()
    header_blob = _header_blob(headers)
    body_l = body.lower()
    cookie_l = cookie_text.lower()
    header_l = header_blob.lower()
    admin_l = admin_body.lower()

    if "csrftoken" in cookie_l:
        scores.django += 3
        scores.signals_d += "csrftoken "
    if "sessionid" in cookie_l:
        scores.django += 2
        scores.signals_d += "sessionid "
    if "csrfmiddlewaretoken" in body_l:
        scores.django += 3
        scores.signals_d += "csrfmiddlewaretoken "
    if "django" in body_l:
        scores.django += 2
        scores.signals_d += "django-body "
    if "django" in header_l:
        scores.django += 2
        scores.signals_d += "django-header "
    if re.search(r"django administration|id_username|grp-", admin_l):
        scores.django += 3
        scores.signals_d += "django-admin "

    if "wp-content" in body_l or "wp-includes" in body_l:
        scores.wordpress += 3
        scores.signals_w += "wp-content "
    if "wordpress" in body_l or "wp-json" in body_l:
        scores.wordpress += 2
        scores.signals_w += "wordpress-body "
    if "wordpress_" in cookie_l or "wp-settings" in cookie_l:
        scores.wordpress += 3
        scores.signals_w += "wp-cookies "
    if re.search(r"x-powered-by:.*wordpress", header_l):
        scores.wordpress += 3
        scores.signals_w += "wp-header "

    if "laravel_session" in cookie_l or "xsrf-token" in cookie_l:
        scores.laravel += 3
        scores.signals_l += "laravel-session "
    if "laravel" in body_l or "illuminate" in body_l:
        scores.laravel += 2
        scores.signals_l += "laravel-body "
    if "laravel" in header_l:
        scores.laravel += 2
        scores.signals_l += "laravel-header "

    if "x-runtime:" in header_l or "x-request-id:" in header_l:
        scores.rails += 2
        scores.signals_r += "rails-headers "
    if "_session_id" in cookie_l or "_rails" in cookie_l:
        scores.rails += 2
        scores.signals_r += "rails-cookies "
    if "authenticity_token" in body_l:
        scores.rails += 3
        scores.signals_r += "authenticity_token "

    return scores


def _pick_detected(scores: FrameworkScores) -> tuple[str, int, str]:
    candidates = (
        ("django", scores.django, scores.signals_d.strip() or "none"),
        ("wordpress", scores.wordpress, scores.signals_w.strip() or "none"),
        ("laravel", scores.laravel, scores.signals_l.strip() or "none"),
        ("rails", scores.rails, scores.signals_r.strip() or "none"),
    )
    detected, max_score, signals = max(candidates, key=lambda item: item[1])
    if max_score == 0:
        return "unknown", 0, "no signals"
    return detected, max_score, signals


def _confidence_for_score(max_score: int) -> str:
    if max_score >= 6:
        return "high"
    if max_score >= 3:
        return "medium"
    if max_score >= 1:
        return "low"
    return "none"


def _normalize_framework(name: str) -> str:
    if name == "php_generic":
        return "php"
    if name == "blocked":
        return "unknown"
    return name


def collect_framework(
    target_url: str,
    *,
    forced_framework: str = "auto",
    headers: dict[str, str] | None = None,
    user_agent: str,
    timeout_seconds: int,
    max_body_bytes: int = 8000,
    probe_admin: bool = True,
    client: Any | None = None,
) -> FrameworkProbeResult:
    import httpx

    result = FrameworkProbeResult(target_url=target_url)
    headers = headers or {}
    result.server_header = headers.get("server", "")
    result.powered_by = headers.get("x-powered-by", "")
    result.cdn = _detect_cdn(headers)
    result.language = _detect_language(headers, result.powered_by)

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        req_headers = {"User-Agent": user_agent}
        try:
            response = client.get(target_url, headers=req_headers)
        except httpx.HTTPError:
            result.detected = "blocked"
            result.effective_framework = "unknown"
            result.confidence = "none"
            result.signals = "blocked"
            result.blocked = True
            return result

        if response.status_code in {415, 403} or response.status_code == 0:
            result.detected = "blocked"
            result.effective_framework = "unknown"
            result.confidence = "none"
            result.signals = "blocked"
            result.blocked = True
            return result

        result.body = response.text[:max_body_bytes]
        cookie_lines = response.headers.get_list("set-cookie")
        result.cookie_text = "\n".join(cookie_lines)

        admin_body = ""
        if probe_admin:
            admin_url = f"{target_url.rstrip('/')}/admin/"
            try:
                admin_resp = client.get(admin_url, headers=req_headers)
                admin_body = admin_resp.text[:2000]
            except httpx.HTTPError:
                admin_body = ""

        scores = _score_framework(
            body=result.body,
            cookie_text=result.cookie_text,
            headers=headers,
            admin_body=admin_body,
        )
        result.scores = scores
        detected, max_score, signals = _pick_detected(scores)
        result.detected = detected
        result.signals = signals
        result.confidence = _confidence_for_score(max_score)

        if detected == "unknown" and "php" in result.powered_by.lower():
            result.detected = "php"
            result.confidence = "medium"
            result.signals = "x-powered-by:php"
            result.language = "PHP"

        if detected == "django" and result.language == "unknown":
            result.language = "Python"
        elif detected in {"wordpress", "laravel", "php"} and result.language == "unknown":
            result.language = "PHP"
        elif detected == "rails" and result.language == "unknown":
            result.language = "Ruby"

        forced = forced_framework not in {"", "auto", "unknown"}
        result.forced = forced
        if forced and forced_framework in _FORCED_FRAMEWORKS:
            result.effective_framework = forced_framework
            if result.confidence == "none":
                result.confidence = "forced"
        else:
            result.effective_framework = _normalize_framework(result.detected)

        return result
    finally:
        if own_client:
            client.close()

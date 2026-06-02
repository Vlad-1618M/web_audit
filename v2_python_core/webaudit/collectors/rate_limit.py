"""Rate limit collector — login GET burst and invalid POST probes (v1 parity).

What: ``collect_rate_limit()`` rapid GETs and POSTs against the framework login path.
Where: Registered in ``pipeline._step_rate_limit``; stored in ``artifacts.inventory.rate_limit``.
How: Detects 429/503 or body lockout phrases; framework-specific CSRF token extraction for POST.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from webaudit.collectors.framework_urls import login_path_for_framework
from webaudit.config.settings import RateLimitCollectorSettings

_BODY_LIMIT_RE = re.compile(
    r"too many (login )?attempts|rate limit|locked out|temporarily blocked|"
    r"slow down|try again later|challenge-platform|cf-chl",
    re.IGNORECASE,
)

_CSRF_PATTERNS: dict[str, re.Pattern[str]] = {
    "django_admin": re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"'),
    "laravel": re.compile(r'name="_token" value="([^"]+)"'),
    "rails": re.compile(r'name="authenticity_token" value="([^"]+)"'),
}


@dataclass
class RateLimitGetResult:
    attempts: int
    limited_at: int | None = None
    limit_status: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "limited_at": self.limited_at,
            "limit_status": self.limit_status,
        }


@dataclass
class RateLimitPostResult:
    attempts: int
    limited_at: int | None = None
    limit_status: int | None = None
    body_signal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "limited_at": self.limited_at,
            "limit_status": self.limit_status,
            "body_signal": self.body_signal,
        }


@dataclass
class RateLimitProbeResult:
    target_url: str
    login_path: str
    post_kind: str
    get: RateLimitGetResult = field(default_factory=lambda: RateLimitGetResult(attempts=0))
    post: RateLimitPostResult = field(default_factory=lambda: RateLimitPostResult(attempts=0))

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "login_path": self.login_path,
            "post_kind": self.post_kind,
            "get": self.get.to_dict(),
            "post": self.post.to_dict(),
        }


def _body_indicates_rate_limit(body: str) -> bool:
    return _BODY_LIMIT_RE.search(body) is not None


def _post_kind_for_framework(framework: str) -> str:
    match framework:
        case "wordpress":
            return "wordpress"
        case "django":
            return "django_admin"
        case "laravel":
            return "laravel"
        case "rails":
            return "rails"
        case _:
            return "form"


def _extract_token(html: str, kind: str) -> str:
    pattern = _CSRF_PATTERNS.get(kind)
    if not pattern:
        return ""
    match = pattern.search(html)
    return match.group(1) if match else ""


def _run_get_burst(client: Any, url: str, headers: dict[str, str], count: int) -> RateLimitGetResult:
    result = RateLimitGetResult(attempts=count)
    for i in range(1, count + 1):
        response = client.get(url, headers=headers)
        if response.status_code in {429, 503}:
            result.limited_at = i
            result.limit_status = response.status_code
            break
    return result


def _run_post_burst(
    client: Any,
    *,
    base_url: str,
    login_path: str,
    post_kind: str,
    headers: dict[str, str],
    count: int,
) -> RateLimitPostResult:
    url = f"{base_url.rstrip('/')}{login_path}"
    result = RateLimitPostResult(attempts=count)

    for i in range(1, count + 1):
        if post_kind == "django_admin":
            page = client.get(url, headers=headers)
            token = _extract_token(page.text, post_kind)
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded", "Referer": url},
                data={
                    "username": f"audit_probe_{i}",
                    "password": "invalid_probe",
                    "csrfmiddlewaretoken": token,
                },
            )
        elif post_kind == "wordpress":
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                data={"log": f"audit_probe_{i}", "pwd": "invalid_probe", "wp-submit": "Log In"},
            )
        elif post_kind == "laravel":
            page = client.get(url, headers=headers)
            token = _extract_token(page.text, post_kind)
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "email": f"audit_probe_{i}@example.com",
                    "password": "invalid_probe",
                    "_token": token,
                },
            )
        elif post_kind == "rails":
            page = client.get(url, headers=headers)
            token = _extract_token(page.text, post_kind)
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "user[email]": f"audit_probe_{i}@example.com",
                    "user[password]": "invalid_probe",
                    "authenticity_token": token,
                },
            )
        else:
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                data={"probe": str(i)},
            )

        body = response.text
        if response.status_code in {429, 503}:
            result.limited_at = i
            result.limit_status = response.status_code
            break
        if response.status_code == 403 and _body_indicates_rate_limit(body):
            result.limited_at = i
            result.limit_status = response.status_code
            result.body_signal = True
            break
        if _body_indicates_rate_limit(body):
            result.limited_at = i
            result.body_signal = True
            break

    return result


def collect_rate_limit(
    target_url: str,
    *,
    framework: str,
    settings: RateLimitCollectorSettings,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> RateLimitProbeResult:
    import httpx

    login_path = login_path_for_framework(framework)
    post_kind = _post_kind_for_framework(framework)
    result = RateLimitProbeResult(
        target_url=target_url,
        login_path=login_path,
        post_kind=post_kind,
    )
    url = f"{target_url.rstrip('/')}{login_path}"
    headers = {"User-Agent": user_agent}

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        result.get = _run_get_burst(client, url, headers, settings.get_burst_count)
        result.post = _run_post_burst(
            client,
            base_url=target_url,
            login_path=login_path,
            post_kind=post_kind,
            headers=headers,
            count=settings.post_burst_count,
        )
        return result
    finally:
        if own_client:
            client.close()

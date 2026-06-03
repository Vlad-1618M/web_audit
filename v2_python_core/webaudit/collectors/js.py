"""JS render collector — post-render DOM via Playwright (Tier 2, optional ``[js]`` extra).

What: ``collect_js_render()`` loads the homepage in headless Chromium and captures rendered HTML.
Where: ``pipeline._step_js`` when ``collectors.js.enabled`` or CLI ``--js``.
How: Optional ``playwright`` import — clear skip message when not installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from bs4 import BeautifulSoup
from webaudit.collectors.js_errors import normalize_js_error

JsBrowser = Literal["chromium", "firefox", "webkit"]


@dataclass
class JsRenderResult:
    target_url: str
    rendered_html: str = ""
    final_url: str = ""
    link_count: int = 0
    script_count: int = 0
    wait_seconds: float = 0.0
    skipped: bool = False
    error: str | None = None
    error_raw: str | None = None
    error_code: str | None = None
    fix_steps: list[str] = field(default_factory=list)
    browser: str = "chromium"

    def to_artifact(self) -> dict[str, Any]:
        artifact: dict[str, Any] = {
            "target_url": self.target_url,
            "final_url": self.final_url or self.target_url,
            "rendered_html_length": len(self.rendered_html),
            "link_count": self.link_count,
            "script_count": self.script_count,
            "wait_seconds": self.wait_seconds,
            "skipped": self.skipped,
            "browser": self.browser,
        }
        if self.error:
            artifact["error"] = self.error
            artifact["error_message"] = self.error
        if self.error_raw:
            artifact["error_raw"] = self.error_raw
        if self.error_code:
            artifact["error_code"] = self.error_code
        if self.fix_steps:
            artifact["fix_steps"] = self.fix_steps
        return artifact


def _apply_error(result: JsRenderResult, raw: str) -> None:
    info = normalize_js_error(raw, target_url=result.target_url, browser=result.browser)
    if info is None:
        return
    result.error_raw = raw.strip()
    result.error = info.message
    result.error_code = info.code
    result.fix_steps = list(info.fix_steps)


def _inventory_counts(html: str) -> tuple[int, int]:
    if not html.strip():
        return 0, 0
    soup = BeautifulSoup(html, "html.parser")
    links = [a for a in soup.find_all("a", href=True) if (a.get("href") or "").strip()]
    scripts = soup.find_all("script")
    return len(links), len(scripts)


def collect_js_render(
    target_url: str,
    *,
    wait_seconds: float,
    user_agent: str,
    timeout_seconds: int,
    browser: JsBrowser = "chromium",
) -> JsRenderResult:
    result = JsRenderResult(target_url=target_url, wait_seconds=wait_seconds, browser=browser)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.skipped = True
        _apply_error(
            result,
            "Playwright not installed — pip install 'webaudit[js]'",
        )
        return result

    timeout_ms = max(timeout_seconds, 5) * 1000
    try:
        with sync_playwright() as playwright:
            engine = getattr(playwright, browser)
            launched = engine.launch(headless=True)
            try:
                context = launched.new_context(user_agent=user_agent)
                page = context.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                if wait_seconds > 0:
                    page.wait_for_timeout(int(wait_seconds * 1000))
                result.final_url = page.url
                result.rendered_html = page.content()
                result.link_count, result.script_count = _inventory_counts(result.rendered_html)
            finally:
                launched.close()
    except Exception as exc:  # noqa: BLE001 — normalize Playwright/network errors for reports
        _apply_error(result, str(exc))
    return result

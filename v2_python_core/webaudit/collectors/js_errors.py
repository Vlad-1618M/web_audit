"""Playwright / JS render error normalization — friendly messages for reports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

JsBrowser = Literal["chromium", "firefox", "webkit"]

_BROWSER_LABELS = {
    "chromium": "Chromium",
    "firefox": "Firefox",
    "webkit": "WebKit",
}

# Playwright 1.4x headless Chromium uses chrome-headless-shell as a separate download.
_INSTALL_PACKAGES: dict[str, str] = {
    "chromium": "chromium chromium-headless-shell",
    "firefox": "firefox",
    "webkit": "webkit",
}


@dataclass(frozen=True)
class JsErrorInfo:
    code: str
    message: str
    fix_steps: list[str] = field(default_factory=list)


def playwright_install_steps(
    browser: JsBrowser = "chromium",
    *,
    target_url: str = "",
    include_scan: bool = True,
) -> list[str]:
    """Venv-safe install commands — must match the Python env that runs webaudit."""
    packages = _INSTALL_PACKAGES.get(browser, _INSTALL_PACKAGES["chromium"])
    steps = [
        f"python -m playwright install {packages}",
        "Run from the same venv as webaudit (e.g. cd v2_python_core && .venv/bin/python -m playwright install …)",
    ]
    if browser == "chromium":
        steps.append(
            "Or try Firefox: set collectors.js.browser: firefox in webaudit.yaml, then python -m playwright install firefox"
        )
    if include_scan and target_url:
        steps.append(f"webaudit scan {target_url.rstrip('/')} --js")
    elif include_scan:
        steps.append("webaudit scan <url> --js")
    return steps


def _strip_playwright_ascii_art(text: str) -> str:
    """Remove Playwright's boxed install hint — paths and pipe characters."""
    if "╔" in text:
        text = text.split("╔", 1)[0]
    return text.strip()


def normalize_js_error(
    raw: str | None,
    *,
    target_url: str = "",
    browser: JsBrowser = "chromium",
) -> JsErrorInfo | None:
    """Map raw Playwright exceptions to a short message + fix steps (no file paths in message)."""
    if not raw or not raw.strip():
        return None

    text = _strip_playwright_ascii_art(raw.strip())
    lower = text.lower()
    label = _BROWSER_LABELS.get(browser, "Chromium")
    install_steps = playwright_install_steps(browser, target_url=target_url)

    if "no module named 'playwright'" in lower or "playwright not installed" in lower:
        return JsErrorInfo(
            code="package_missing",
            message="Playwright Python package is not installed in this environment.",
            fix_steps=["pip install 'webaudit[js]'", *install_steps],
        )

    if (
        "executable doesn't exist" in lower
        or "browser hasn't been installed" in lower
        or "please run the following command to download new browsers" in lower
        or "headless-shell" in lower
        or "headless_shell" in lower
    ):
        shell_note = (
            " (including the headless shell bundle)"
            if browser == "chromium"
            else ""
        )
        return JsErrorInfo(
            code="browser_missing",
            message=(
                f"{label} is not installed for Playwright on the machine that ran this scan{shell_note}. "
                "Install browsers with the same Python/venv that runs webaudit — not necessarily a global playwright CLI."
            ),
            fix_steps=install_steps,
        )

    if "timeout" in lower and ("exceeded" in lower or "timed out" in lower):
        return JsErrorInfo(
            code="timeout",
            message="The homepage did not finish loading within the scan timeout.",
            fix_steps=[
                "Retry with a higher timeout in webaudit.yaml: runtime.timeout_seconds: 30",
                *install_steps[-1:],
            ],
        )

    if "net::err_" in lower or "ns_error" in lower:
        return JsErrorInfo(
            code="navigation",
            message="Playwright could not load the homepage (network or TLS error in the browser).",
            fix_steps=[
                "Confirm the URL loads in a normal browser from the same machine",
                install_steps[-1],
            ],
        )

    if "target page, context or browser has been closed" in lower:
        return JsErrorInfo(
            code="browser_closed",
            message="The browser session closed before the page could be read.",
            fix_steps=install_steps,
        )

    short = re.sub(r"^[A-Za-z.]+:\s*", "", text.splitlines()[0])[:200]
    if "/" in short or "\\" in short or "ms-playwright" in short.lower():
        short = f"Playwright could not start {label} on this machine."

    return JsErrorInfo(
        code="unknown",
        message=short or "Playwright could not complete the JS render pass.",
        fix_steps=install_steps,
    )


def js_error_from_artifact(js_art: dict, *, target_url: str = "") -> JsErrorInfo | None:
    """Resolve error display from artifact — prefers stored normalization, falls back to raw error."""
    browser = str(js_art.get("browser") or "chromium")
    if browser not in _BROWSER_LABELS:
        browser = "chromium"
    if js_art.get("error_code") and js_art.get("error_message"):
        return JsErrorInfo(
            code=str(js_art["error_code"]),
            message=str(js_art["error_message"]),
            fix_steps=list(js_art.get("fix_steps") or []),
        )
    raw = js_art.get("error_raw") or js_art.get("error")
    return normalize_js_error(str(raw) if raw else None, target_url=target_url, browser=browser)  # type: ignore[arg-type]

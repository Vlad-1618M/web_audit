"""Registry lookups for latest extension versions (wp.org, PyPI, Packagist, RubyGems)."""

from __future__ import annotations

from typing import Any, Literal

Registry = Literal["wporg", "pypi", "packagist", "rubygems"]

_WPORG_API = "https://api.wordpress.org/plugins/info/1.0/{slug}.json"
_WPORG_THEME_API = (
    "https://api.wordpress.org/themes/info/1.1/"
    "?action=theme_information&request[slug]={slug}&request[fields][version]=1"
)
_PYPI_API = "https://pypi.org/pypi/{package}/json"
_PACKAGIST_API = "https://repo.packagist.org/p2/{package}.json"
_RUBYGEMS_API = "https://rubygems.org/api/v1/gems/{gem}.json"


def fetch_wporg_theme_version(
    slug: str,
    *,
    client: Any,
    user_agent: str,
) -> str | None:
    headers = {"User-Agent": user_agent}
    try:
        response = client.get(_WPORG_THEME_API.format(slug=slug), headers=headers)
        if response.status_code != 200:
            return None
        data = response.json()
        version = data.get("version")
        return str(version) if version else None
    except Exception:
        return None


def fetch_latest_version(
    registry: Registry,
    name: str,
    *,
    client: Any,
    user_agent: str,
) -> str | None:
    headers = {"User-Agent": user_agent}
    try:
        if registry == "wporg":
            response = client.get(_WPORG_API.format(slug=name), headers=headers)
            if response.status_code != 200:
                return None
            return str(response.json().get("version") or "") or None

        if registry == "pypi":
            package = name.replace("_", "-")
            response = client.get(_PYPI_API.format(package=package), headers=headers)
            if response.status_code != 200:
                return None
            return str(response.json().get("info", {}).get("version") or "") or None

        if registry == "packagist":
            response = client.get(_PACKAGIST_API.format(package=name), headers=headers)
            if response.status_code != 200:
                return None
            packages = response.json().get("packages", {}).get(name) or []
            if not packages:
                return None
            return str(packages[0].get("version") or "") or None

        if registry == "rubygems":
            response = client.get(_RUBYGEMS_API.format(gem=name), headers=headers)
            if response.status_code != 200:
                return None
            return str(response.json().get("version") or "") or None
    except Exception:
        return None
    return None


def registry_for_framework(framework: str) -> Registry | None:
    return {
        "wordpress": "wporg",
        "django": "pypi",
        "laravel": "packagist",
        "rails": "rubygems",
    }.get(framework)


_REGISTRY_META: dict[Registry, dict[str, str]] = {
    "wporg": {
        "label": "WordPress.org Plugin Directory",
        "home": "https://wordpress.org/plugins/",
    },
    "pypi": {
        "label": "PyPI (Python Package Index)",
        "home": "https://pypi.org/",
    },
    "packagist": {
        "label": "Packagist (Composer)",
        "home": "https://packagist.org/",
    },
    "rubygems": {
        "label": "RubyGems.org",
        "home": "https://rubygems.org/",
    },
}


def registry_meta(registry: Registry | str | None) -> dict[str, str] | None:
    if not registry:
        return None
    return _REGISTRY_META.get(registry)  # type: ignore[arg-type]


def registry_package_url(registry: Registry | str | None, name: str) -> str | None:
    if not registry or not name:
        return None
    if registry == "wporg":
        return f"https://wordpress.org/plugins/{name}/"
    if registry == "pypi":
        package = name.replace("_", "-")
        return f"https://pypi.org/project/{package}/"
    if registry == "packagist":
        return f"https://packagist.org/packages/{name}"
    if registry == "rubygems":
        return f"https://rubygems.org/gems/{name}"
    return None

"""Built-in sensitive path lists — v1 ``PATHS_*`` parity.

What: Static path suffixes merged per framework for ``collectors/paths.py``.
Where: Not imported by orchestrator directly; used when ``paths.sensitive_builtin`` is true.
How: ``paths_for_framework(framework)`` returns deduplicated probe list (capped by caller).
"""

from __future__ import annotations

PATHS_COMMON: tuple[str, ...] = (
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.env.backup",
    "/.git/HEAD",
    "/.git/config",
    "/backup.zip",
    "/backup.tar.gz",
    "/dump.sql",
    "/db.sql",
    "/robots.txt",
    "/sitemap.xml",
    "/.htaccess",
    "/phpinfo.php",
    "/info.php",
    "/test.php",
    "/crossdomain.xml",
    "/config.py",
    "/config.php",
    "/configuration.php",
    "/.well-known/security.txt",
    "/.dockerenv",
    "/package.json",
    "/composer.json",
    "/Gemfile",
    "/web.config",
)

PATHS_WORDPRESS: tuple[str, ...] = (
    "/wp-admin",
    "/wp-admin/",
    "/wp-admin/install.php",
    "/wp-admin/install.php?step=1",
    "/wp-login.php",
    "/wp-config.php",
    "/wp-config.php.bak",
    "/wp-content/",
    "/wp-content/plugins/",
    "/wp-content/themes/",
    "/wp-content/uploads/",
    "/wp-includes/",
    "/xmlrpc.php",
    "/wp-cron.php",
    "/wp-json/",
    "/wp-json/wp/v2/users",
    "/?author=1",
    "/feed/",
    "/readme.html",
    "/license.txt",
    "/wp-links-opml.php",
)

PATHS_DJANGO: tuple[str, ...] = (
    "/admin",
    "/admin/",
    "/admin/login/",
    "/django-admin",
    "/django-admin/",
    "/api",
    "/api/",
    "/api/v1/",
    "/api/v2/",
    "/api/schema/",
    "/api/docs/",
    "/swagger/",
    "/swagger-ui/",
    "/redoc/",
    "/openapi.json",
    "/schema.json",
    "/static/",
    "/media/",
    "/db.sqlite3",
    "/database.sqlite3",
    "/settings.py",
    "/local_settings.py",
    "/secrets.py",
    "/__debug__/",
    "/silk/",
    "/api/token/",
    "/api/token/refresh/",
    "/accounts/login/",
)

PATHS_LARAVEL: tuple[str, ...] = (
    "/storage/logs/laravel.log",
    "/public/storage/",
    "/api/user",
    "/telescope",
    "/horizon",
    "/log-viewer",
    "/_debugbar/",
    "/artisan",
    "/login",
    "/logout",
    "/register",
)

PATHS_RAILS: tuple[str, ...] = (
    "/rails/info",
    "/rails/info/properties",
    "/rails/mailers",
    "/cable",
    "/sidekiq",
    "/delayed_job",
    "/users/sign_in",
    "/users/sign_out",
)

PATHS_GENERIC: tuple[str, ...] = (
    "/administrator/",
    "/admin",
    "/admin/",
    "/login/",
    "/user/login",
    "/panel/",
    "/dashboard/",
    "/phpmyadmin/",
    "/pma/",
    "/server-status",
    "/server-info",
)

SENSITIVE_PATHS: frozenset[str] = frozenset(
    {
        "/.env",
        "/.env.local",
        "/.env.production",
        "/.env.backup",
        "/.git/HEAD",
        "/.git/config",
        "/backup.zip",
        "/backup.tar.gz",
        "/dump.sql",
        "/db.sql",
        "/wp-config.php",
        "/wp-config.php.bak",
        "/config.py",
        "/config.php",
        "/configuration.php",
        "/settings.py",
        "/local_settings.py",
        "/secrets.py",
        "/db.sqlite3",
        "/database.sqlite3",
        "/storage/logs/laravel.log",
        "/phpinfo.php",
        "/info.php",
        "/test.php",
    }
)

CRITICAL_PATHS: frozenset[str] = frozenset({"/.env", "/.git/HEAD"})

PUBLIC_BY_DESIGN: frozenset[str] = frozenset(
    {"/robots.txt", "/sitemap.xml", "/feed/", "/.well-known/security.txt"}
)


def paths_for_framework(framework: str) -> list[str]:
    """Return deduplicated built-in paths for the target framework hint."""
    buckets: list[tuple[str, ...]] = [PATHS_COMMON]
    match framework:
        case "django":
            buckets.append(PATHS_DJANGO)
        case "wordpress":
            buckets.append(PATHS_WORDPRESS)
        case "laravel":
            buckets.append(PATHS_LARAVEL)
        case "rails":
            buckets.append(PATHS_RAILS)
        case "php":
            buckets.append(PATHS_GENERIC)
        case _:
            buckets.extend(
                (PATHS_DJANGO, PATHS_WORDPRESS, PATHS_LARAVEL, PATHS_RAILS, PATHS_GENERIC)
            )

    seen: set[str] = set()
    out: list[str] = []
    for bucket in buckets:
        for path in bucket:
            if path not in seen:
                seen.add(path)
                out.append(path)
    return out

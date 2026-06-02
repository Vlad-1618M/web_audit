"""Framework URL helpers — login paths and probes shared across collectors.

What: ``login_path_for_framework()`` returns the v1 default login URL suffix.
Where: Used by cookies, rate_limit, and related Stage 2 collectors.
How: Maps ``target.framework`` hint to path; ``auto``/``unknown`` use generic ``/login/``.
"""

from __future__ import annotations


def login_path_for_framework(framework: str) -> str:
    match framework:
        case "wordpress":
            return "/wp-login.php"
        case "django":
            return "/admin/login/"
        case "laravel":
            return "/login"
        case "rails":
            return "/users/sign_in"
        case _:
            return "/login/"

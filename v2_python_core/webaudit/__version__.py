"""Package version string.

What: Single source of truth for the semver written into ``audit_run.json`` meta.
Where: Imported by ``webaudit/__init__.py`` and ``webaudit/orchestrator.py``.
How: Bump here on release; do not hard-code version elsewhere.
"""

__version__ = "2.1.0b1"

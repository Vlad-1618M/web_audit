"""Configuration package — YAML loading and validation.

What: Re-exports ``Settings`` and ``load_settings`` for callers.
Where: Imported by CLI and orchestrator; tests import directly for unit checks.
How: ``from webaudit.config import load_settings, Settings``.
"""

from webaudit.config.settings import Settings, load_settings

__all__ = ["Settings", "load_settings"]

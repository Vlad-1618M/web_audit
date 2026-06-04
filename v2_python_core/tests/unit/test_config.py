"""Tests for ``webaudit.config.settings`` — YAML merge and validation.

What: Unit tests for ``load_settings()`` defaults, overrides, and Pydantic bounds.
Where: Run via ``pytest`` from ``v2_python_core/`` (see ``pyproject.toml``).
How: ``pytest tests/unit/test_config.py`` — uses ``tmp_path`` for isolated config files.
"""
from pathlib import Path
import pytest
from webaudit.config.settings import Settings, load_settings

def test_defaults_load():
    """Ensures Defaults Load."""
    settings = load_settings(target_url='https://example.com')
    assert settings.target.url == 'https://example.com'
    assert settings.runtime.timeout_seconds == 15
    assert settings.collectors.dns.check_dmarc is True
    assert settings.paths.enabled is True
    assert settings.paths.sensitive_builtin is True
    assert settings.paths.max_probe_urls == 250
    assert settings.collectors.tls.enabled is True
    assert settings.collectors.tls.expiry_warn_days == 30
    assert settings.policy.enabled is True
    assert settings.policy.hsts_min_max_age_seconds == 15552000

def test_merge_user_config(tmp_path: Path):
    """Ensures Merge User Config."""
    cfg = tmp_path / 'webaudit.yaml'
    cfg.write_text('runtime:\n  timeout_seconds: 30\nscoring:\n  hygiene_weights:\n    HIGH: 12\n', encoding='utf-8')
    settings = load_settings(config_path=cfg, target_url='https://example.com')
    assert settings.runtime.timeout_seconds == 30
    assert settings.scoring.hygiene_weights.HIGH == 12

def test_settings_validation():
    """Ensures Settings Validation."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings.model_validate({'runtime': {'timeout_seconds': 0}})

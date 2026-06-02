"""Tests for compact scan output and open-output helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from webaudit.cli.output_ui import (
    normalize_open_mode,
    open_report_outputs,
    resolve_open_keys,
)
from webaudit.models.run import AuditMeta, AuditRun, AuditScores


def test_normalize_open_mode_defaults():
    assert normalize_open_mode(None, is_tty=True) == "ask"
    assert normalize_open_mode(None, is_tty=False) == "none"
    assert normalize_open_mode("h", is_tty=True) == "html"
    assert normalize_open_mode("all", is_tty=False) == "all"


def test_resolve_open_keys_all():
    reports = {"html": "/tmp/report.html", "json": "/tmp/audit_run.json"}
    assert resolve_open_keys("all", reports) == ["html", "json"]


def test_resolve_open_keys_pdf_opens_html():
    reports = {"html": "/tmp/report.html"}
    assert resolve_open_keys("pdf", reports) == ["html"]


def test_open_report_outputs_calls_open_path():
    reports = {"html": "/tmp/report.html", "json": "/tmp/audit_run.json"}
    with patch("webaudit.cli.output_ui.open_path") as mock_open:
        from rich.console import Console

        open_report_outputs(reports, ["html"], console=Console())
        mock_open.assert_called_once_with(Path("/tmp/report.html"))

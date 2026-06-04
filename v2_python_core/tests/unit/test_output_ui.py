"""Tests for compact scan output and open-output helpers."""
from __future__ import annotations
import io
from pathlib import Path
from unittest.mock import patch
from rich.console import Console
from webaudit.cli.output_ui import (
    handle_open_outputs,
    host_output_hint,
    normalize_open_mode,
    open_report_outputs,
    resolve_open_keys,
    running_in_docker,
    write_last_run_marker,
)
from webaudit.models.run import AuditMeta, AuditRun, AuditScores

def test_normalize_open_mode_defaults():
    """Ensures Normalize Open Mode Defaults."""
    assert normalize_open_mode(None, is_tty=True) == 'ask'
    assert normalize_open_mode(None, is_tty=False) == 'none'
    assert normalize_open_mode('h', is_tty=True) == 'html'
    assert normalize_open_mode('all', is_tty=False) == 'all'

def test_resolve_open_keys_all():
    """Ensures Resolve Open Keys All."""
    reports = {'html': '/tmp/report.html', 'json': '/tmp/audit_run.json'}
    assert resolve_open_keys('all', reports) == ['html', 'json']

def test_resolve_open_keys_pdf_opens_html():
    """Ensures Resolve Open Keys PDF Opens HTML."""
    reports = {'html': '/tmp/report.html'}
    assert resolve_open_keys('pdf', reports) == ['html']

def test_open_report_outputs_calls_open_path():
    """Ensures Open Report Outputs Calls Open Path."""
    reports = {'html': '/tmp/report.html', 'json': '/tmp/audit_run.json'}
    with patch('webaudit.cli.output_ui.open_path') as mock_open:
        buf = io.StringIO()
        open_report_outputs(reports, ['html'], console=Console(file=buf, force_terminal=False))
        mock_open.assert_called_once_with(Path('/tmp/report.html'))
        assert 'Opened:' in buf.getvalue()
        assert 'html' in buf.getvalue()

def test_running_in_docker_env():
    """Ensures Running In Docker Env."""
    with patch.dict('os.environ', {'WEBAUDIT_IN_DOCKER': '1'}, clear=False):
        assert running_in_docker() is True

def test_host_output_hint_maps_container_dir_to_host():
    """Ensures Host Output Hint Maps Container Dir To Host."""
    with patch.dict('os.environ', {'WEBAUDIT_HOST_OUTPUT_DIR': '/Users/me/audit_logs'}, clear=False):
        hint = host_output_hint(Path('/work/audit_logs/20260529_example.com'))
        assert hint == '/Users/me/audit_logs/20260529_example.com'

def test_handle_open_outputs_skips_browser_in_docker():
    """Ensures Handle Open Outputs Skips Browser In Docker."""
    reports = {'html': '/work/audit_logs/run/report.html'}
    with patch('webaudit.cli.output_ui.running_in_docker', return_value=True):
        with patch('webaudit.cli.output_ui.open_path') as mock_open:
            buf = io.StringIO()
            handle_open_outputs(reports, mode='html', console=Console(file=buf, force_terminal=False))
            mock_open.assert_not_called()
            assert 'Docker' in buf.getvalue()

def test_write_last_run_marker(tmp_path: Path):
    """Ensures Write Last Run Marker."""
    marker = tmp_path / 'last-run'
    reports = {'html': str(tmp_path / '20260529_example.com' / 'report.html')}
    with patch.dict('os.environ', {'WEBAUDIT_LAST_RUN_FILE': str(marker)}, clear=False):
        write_last_run_marker(reports)
    assert marker.read_text(encoding='utf-8').strip() == str(tmp_path / '20260529_example.com')

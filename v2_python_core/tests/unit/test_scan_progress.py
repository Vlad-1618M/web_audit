"""Tests for scan verbosity and progress summaries."""
from __future__ import annotations
import io
import re
from rich.console import Console
from webaudit.cli.scan_progress import ScanProgress, Verbosity, resolve_verbosity, step_enabled, summarize_step
from webaudit.config.settings import Settings
from webaudit.models.finding import Finding, Severity

def test_resolve_verbosity_levels():
    """Ensures Resolve Verbosity Levels."""
    assert resolve_verbosity(verbose=False, quiet=False) == Verbosity.NORMAL
    assert resolve_verbosity(verbose=True, quiet=False) == Verbosity.VERBOSE
    assert resolve_verbosity(verbose=False, quiet=True) == Verbosity.QUIET

def test_resolve_verbosity_conflict():
    """Ensures Resolve Verbosity Conflict."""
    try:
        resolve_verbosity(verbose=True, quiet=True)
    except ValueError as exc:
        assert 'not both' in str(exc)
    else:
        raise AssertionError('expected ValueError')

def test_step_enabled_paths():
    """Ensures Step Enabled Paths."""
    settings = Settings()
    settings.paths.enabled = False
    assert step_enabled('_step_paths', settings) is False
    assert step_enabled('_step_headers', settings) is True
    assert step_enabled('_step_js', settings) is False
    settings.collectors.js.enabled = True
    assert step_enabled('_step_js', settings) is True
    assert step_enabled('_step_links', settings) is False
    settings.collectors.seo_surface.check_broken_links = True
    assert step_enabled('_step_links', settings) is True

def test_summarize_headers_step():
    """Ensures Summarize Headers Step."""
    findings = [Finding.from_check(category='HEADERS', item='Content-Security-Policy', status='MISSING', severity=Severity.HIGH)]
    summary, details = summarize_step('_step_headers', findings, {'headers': {'status_code': 200, 'headers': {'Strict-Transport-Security': 'max-age=31536000'}}})
    assert 'HTTP 200' in summary
    assert '1 findings' in summary
    assert details

def test_summarize_paths_verbose_lists_each_probe():
    """Ensures Summarize Paths Verbose Lists Each Probe."""
    probes = [{'path': '/.env', 'final_status': 404, 'note': 'NOT_FOUND'}, {'path': '/robots.txt', 'final_status': 200, 'note': 'OPEN'}]
    summary, details = summarize_step('_step_paths', [], {'inventory': {'paths': {'probe_count': 2, 'paths': probes}}}, verbose=True)
    assert '2 probes' in summary
    assert any(('exposed: /robots.txt' in line for line in details))
    assert any(('/.env' in line and '[dark_orange]' in line for line in details))
    assert any(('/robots.txt' in line and '[dark_orange]' in line for line in details))
    assert sum((1 for line in details if '[dark_orange]' in line)) == 2

def test_summarize_paths_normal_hides_probe_list():
    """Ensures Summarize Paths Normal Hides Probe List."""
    probes = [{'path': '/.env', 'final_status': 404, 'note': 'NOT_FOUND'}]
    _summary, details = summarize_step('_step_paths', [], {'inventory': {'paths': {'probe_count': 1, 'paths': probes}}}, verbose=False)
    assert not any(('[dark_orange]' in line for line in details))

def test_summarize_policy_step_string_artifacts():
    """Ensures Summarize Policy Step String Artifacts."""
    findings = []
    summary, details = summarize_step('_step_policy', findings, {'policy': {'hsts_detail': 'max-age=31536000, includeSubDomains (raw: max-age=31536000)', 'csp_detail': "default-src 'self'"}})
    assert 'HSTS max-age=31536000' in summary
    assert 'CSP yes' in summary
    assert details

def _strip_ansi(text: str) -> str:
    return re.sub('\\x1b\\[[0-9;]*m', '', text)

def test_paths_probe_streaming_verbose():
    """Ensures Paths Probe Streaming Verbose."""
    buf = io.StringIO()
    progress = ScanProgress(Console(file=buf, force_terminal=True, width=120), Verbosity.VERBOSE)
    progress.step_start('paths', 'Sensitive path probes')
    progress.paths_probe_start(2)
    progress.paths_probe_done({'path': '/.env', 'final_status': 404, 'note': 'NOT_FOUND'}, 1, 2)
    progress.step_done('_step_paths', 'paths', [], {'inventory': {'paths': {'probe_count': 2, 'paths': []}}})
    out = _strip_ansi(buf.getvalue())
    assert 'probing' not in out
    assert '/.env' in out
    assert 'NOT_FOUND' in out
    assert out.count('/.env') == 1

def test_paths_probe_streaming_normal_counter_and_exposed():
    """Ensures Paths Probe Streaming Normal Counter And Exposed."""
    buf = io.StringIO()
    progress = ScanProgress(Console(file=buf, force_terminal=True, width=120), Verbosity.NORMAL)
    progress.step_start('paths', 'Sensitive path probes')
    progress.paths_probe_start(2)
    progress.paths_probe_done({'path': '/secret', 'final_status': 404, 'note': 'NOT_FOUND'}, 1, 2)
    progress.paths_probe_done({'path': '/robots.txt', 'final_status': 200, 'note': 'OPEN'}, 2, 2)
    progress.step_done('_step_paths', 'paths', [], {'inventory': {'paths': {'probe_count': 2, 'paths': [{'path': '/secret', 'note': 'NOT_FOUND'}, {'path': '/robots.txt', 'note': 'OPEN'}]}}})
    out = _strip_ansi(buf.getvalue())
    assert 'probing 1/2' in out
    assert 'probing 2/2' in out
    assert 'exposed: /robots.txt' in out
    assert '2 probes' in out

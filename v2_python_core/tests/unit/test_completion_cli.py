"""Tests for legacy completion argv rewriting."""
from webaudit.cli.completion_cmd import rewrite_legacy_completion_argv

def test_rewrite_install_completion():
    """Ensures Rewrite Install Completion."""
    assert rewrite_legacy_completion_argv(['webaudit', '--install-completion']) == ['webaudit', 'completion', 'install']

def test_rewrite_show_completion():
    """Ensures Rewrite Show Completion."""
    assert rewrite_legacy_completion_argv(['webaudit', '--show-completion']) == ['webaudit', 'completion', 'show']

def test_passthrough_scan():
    """Ensures Passthrough Scan."""
    assert rewrite_legacy_completion_argv(['webaudit', 'scan', 'https://x.com']) == ['webaudit', 'scan', 'https://x.com']

"""Tests for legacy completion argv rewriting."""

from webaudit.cli.completion_cmd import rewrite_legacy_completion_argv


def test_rewrite_install_completion():
    assert rewrite_legacy_completion_argv(["webaudit", "--install-completion"]) == [
        "webaudit",
        "completion",
        "install",
    ]


def test_rewrite_show_completion():
    assert rewrite_legacy_completion_argv(["webaudit", "--show-completion"]) == [
        "webaudit",
        "completion",
        "show",
    ]


def test_passthrough_scan():
    assert rewrite_legacy_completion_argv(["webaudit", "scan", "https://x.com"]) == [
        "webaudit",
        "scan",
        "https://x.com",
    ]

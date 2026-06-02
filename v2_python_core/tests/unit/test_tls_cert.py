"""Tests for TLS certificate display helpers."""

from webaudit.collectors.tls_cert import (
    build_cert_issues,
    format_days_left,
    issuer_display_name,
    validate_hostname,
)


def test_issuer_display_lets_encrypt():
    name = issuer_display_name(
        issuer="CN=R3,O=Let's Encrypt,C=US",
        issuer_org="Let's Encrypt",
        issuer_cn="R3",
    )
    assert "Let's Encrypt" in name


def test_issuer_display_hashicorp():
    name = issuer_display_name(
        issuer="CN=HashiCorp Vault,O=HashiCorp",
        issuer_org="HashiCorp",
        issuer_cn="HashiCorp Vault",
    )
    assert "HashiCorp" in name


def test_validate_hostname_wildcard_san():
    ok, note = validate_hostname(
        "www.example.com",
        subject="CN=example.com",
        san=["*.example.com", "example.com"],
    )
    assert ok is True
    assert "Covers" in note


def test_validate_hostname_mismatch():
    ok, note = validate_hostname(
        "shop.example.com",
        subject="CN=example.com",
        san=["example.com"],
    )
    assert ok is False
    assert "shop.example.com" in note


def test_build_cert_issues_expiring_and_tls():
    cert = {
        "days_left": 12,
        "not_after": "2026-06-15T00:00:00+00:00",
        "hostname_match": True,
    }
    versions = [{"version": "1.1", "supported": True}]
    issues = build_cert_issues(cert, tls_versions=versions, warn_days=30)
    assert any("expires soon" in issue.lower() for issue in issues)
    assert any("TLS 1.1" in issue for issue in issues)


def test_format_days_left_expired():
    assert "Expired" in format_days_left(-3)

"""TLS collector — version probes and certificate metadata (v1 ``check_tls()`` parity).

What: ``collect_tls()`` probes TLS 1.0–1.3 handshakes and reads the peer certificate.
Where: Registered in ``pipeline._step_tls``; raw output stored in ``artifacts.tls``.
How: Uses stdlib ``ssl``/``socket``; ``cryptography`` parses DER for subject, issuer, expiry, SAN.
"""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse


@dataclass
class TlsVersionResult:
    version: str
    supported: bool
    negotiated: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "supported": self.supported,
            "negotiated": self.negotiated,
            "error": self.error,
        }


@dataclass
class TlsCertificateInfo:
    subject: str | None = None
    issuer: str | None = None
    not_after: str | None = None
    days_left: int | None = None
    san: list[str] = field(default_factory=list)
    chain_length: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "not_after": self.not_after,
            "days_left": self.days_left,
            "san": self.san,
            "chain_length": self.chain_length,
            "error": self.error,
        }


@dataclass
class TlsProbeResult:
    target_url: str
    host: str | None = None
    port: int | None = None
    skipped: bool = False
    skip_reason: str | None = None
    versions: list[TlsVersionResult] = field(default_factory=list)
    certificate: TlsCertificateInfo | None = None
    errors: list[str] = field(default_factory=list)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "host": self.host,
            "port": self.port,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "versions": [v.to_dict() for v in self.versions],
            "certificate": self.certificate.to_dict() if self.certificate else None,
            "errors": self.errors,
        }


_TLS_VERSION_SPECS: tuple[tuple[str, ssl.TLSVersion, ssl.TLSVersion], ...] = (
    ("1.0", ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1),
    ("1.1", ssl.TLSVersion.TLSv1_1, ssl.TLSVersion.TLSv1_1),
    ("1.2", ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_2),
    ("1.3", ssl.TLSVersion.TLSv1_3, ssl.TLSVersion.TLSv1_3),
)

HandshakeFn = Callable[
    [str, int, ssl.TLSVersion, ssl.TLSVersion, float],
    tuple[bool, str | None, str | None],
]
FetchCertFn = Callable[[str, int, float], TlsCertificateInfo | None]


def parse_tls_target(url: str) -> tuple[str, int] | None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return None
    host = parsed.hostname
    if not host:
        return None
    return host, parsed.port or 443


def _default_handshake(
    host: str,
    port: int,
    min_version: ssl.TLSVersion,
    max_version: ssl.TLSVersion,
    timeout: float,
) -> tuple[bool, str | None, str | None]:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = min_version
    ctx.maximum_version = max_version
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return True, ssock.version(), None
    except ssl.SSLError as exc:
        return False, None, str(exc)
    except OSError as exc:
        return False, None, str(exc)


def _parse_certificate_der(der: bytes, chain_length: int) -> TlsCertificateInfo:
    from cryptography import x509

    cert = x509.load_der_x509_certificate(der)
    subject = cert.subject.rfc4514_string()
    issuer = cert.issuer.rfc4514_string()
    not_after_dt = cert.not_valid_after_utc
    not_after = not_after_dt.isoformat()
    now = datetime.now(timezone.utc)
    days_left = (not_after_dt - now).days

    san: list[str] = []
    try:
        san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san = [entry.value for entry in san_ext.value if isinstance(entry.value, str)]
    except x509.ExtensionNotFound:
        pass

    return TlsCertificateInfo(
        subject=subject,
        issuer=issuer,
        not_after=not_after,
        days_left=days_left,
        san=san,
        chain_length=chain_length,
    )


def _default_fetch_certificate(host: str, port: int, timeout: float) -> TlsCertificateInfo | None:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der = ssock.getpeercert(binary_form=True)
                if not der:
                    return TlsCertificateInfo(error="No peer certificate returned")
                chain = ssock.getpeercert_chain() if hasattr(ssock, "getpeercert_chain") else None
                chain_length = len(chain) if chain else 1
                return _parse_certificate_der(der, chain_length)
    except ssl.SSLError as exc:
        return TlsCertificateInfo(error=str(exc))
    except OSError as exc:
        return TlsCertificateInfo(error=str(exc))


def collect_tls(
    target_url: str,
    *,
    timeout_seconds: int,
    probe_versions: bool = True,
    fetch_certificate: bool = True,
    handshake_fn: HandshakeFn | None = None,
    fetch_cert_fn: FetchCertFn | None = None,
) -> TlsProbeResult:
    """Probe TLS versions and read certificate metadata for an HTTPS target."""
    result = TlsProbeResult(target_url=target_url)
    target = parse_tls_target(target_url)
    if target is None:
        result.skipped = True
        result.skip_reason = "Target is not HTTPS"
        return result

    host, port = target
    result.host = host
    result.port = port
    timeout = float(timeout_seconds)
    handshake = handshake_fn or _default_handshake
    fetch_cert = fetch_cert_fn or _default_fetch_certificate

    if probe_versions:
        for label, min_ver, max_ver in _TLS_VERSION_SPECS:
            supported, negotiated, error = handshake(host, port, min_ver, max_ver, timeout)
            result.versions.append(
                TlsVersionResult(
                    version=label,
                    supported=supported,
                    negotiated=negotiated,
                    error=error,
                )
            )

    if fetch_certificate:
        result.certificate = fetch_cert(host, port, timeout)
        if result.certificate and result.certificate.error:
            result.errors.append(result.certificate.error)

    return result

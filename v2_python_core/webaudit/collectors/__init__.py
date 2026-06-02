"""Collectors — fetch raw external data (HTTP, DNS, future TLS/paths).

What: Re-exports probe functions that return artifact dataclasses, not findings.
Where: Orchestrator calls collectors before analyzers; tests mock at this layer.
How: ``from webaudit.collectors import collect_headers, collect_dns``.
"""

from webaudit.collectors.headers import collect_headers
from webaudit.collectors.dns import collect_dns

__all__ = ["collect_headers", "collect_dns"]

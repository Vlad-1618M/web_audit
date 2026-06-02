"""Analyzers — interpret collector artifacts into ``Finding`` objects.

What: Re-exports header and DNS analyzers; future modules (TLS, paths, policy) land here.
Where: Orchestrator runs analyzers between collectors and ``scoring/engine.py``.
How: ``from webaudit.analyzers import analyze_headers, analyze_dns``.
"""

from webaudit.analyzers.headers import analyze_headers
from webaudit.analyzers.dns import analyze_dns

__all__ = ["analyze_headers", "analyze_dns"]

"""Storage layer — run artifacts and future baselines/cache.

What: Re-exports run persistence helpers.
Where: ``orchestrator`` writes via ``write_audit_run``; Tier 2 may add baselines here.
How: ``from webaudit.storage import write_audit_run``.
"""

from webaudit.storage.runs import write_audit_run

__all__ = ["write_audit_run"]

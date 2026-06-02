"""Storage layer — run artifacts and future baselines/cache.

What: Re-exports run persistence helpers.
Where: ``orchestrator`` writes via ``write_audit_run``; Tier 2 may add baselines here.
How: ``from webaudit.storage import write_audit_run``.
"""

from webaudit.storage.runs import load_audit_run, write_audit_run

__all__ = ["load_audit_run", "write_audit_run"]

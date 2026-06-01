"""Scoring package — deterministic verdict math.

What: Re-exports ``score_findings`` and low-level compute helpers for tests.
Where: Orchestrator scores runs; report templates read ``AuditRun.scores`` only.
How: ``from webaudit.scoring import score_findings``.
"""

from webaudit.scoring.engine import compute_exposure, compute_hygiene, compute_verdict, score_findings

__all__ = [
    "compute_exposure",
    "compute_hygiene",
    "compute_verdict",
    "score_findings",
]

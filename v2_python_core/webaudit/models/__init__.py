"""Domain models — findings and audit run structures.

What: Re-exports core Pydantic types used across collectors, analyzers, and storage.
Where: Imported by orchestrator, scoring, tests, and future report renderers.
How: ``from webaudit.models import Finding, AuditRun, Severity``.
"""

from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.models.run import AuditRun, AuditScores, AuditMeta, AuditArtifacts

__all__ = [
    "Finding",
    "FindingClass",
    "Severity",
    "AuditRun",
    "AuditScores",
    "AuditMeta",
    "AuditArtifacts",
]

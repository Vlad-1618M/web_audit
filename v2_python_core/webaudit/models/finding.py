"""Finding model — one check result fed into scoring and reports.

What: ``Finding`` dataclass-like Pydantic model with category, severity, class, evidence.
Where: Emitted by analyzers; collected in ``AuditRun.findings``; consumed by ``scoring/engine.py``.
How: Prefer ``Finding.from_check(...)`` — auto-downgrades OK/PRESENT statuses to INFO/unscored (v1 parity).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    OK = "OK"


class FindingClass(str, Enum):
    ACTION = "ACTION"
    VERIFY = "VERIFY"
    EXPECTED = "EXPECTED"
    INFO = "INFO"


_OK_STATUSES = frozenset(
    {
        "OK",
        "PRESENT",
        "REJECTED",
        "PROTECTED",
        "SUPPORTED",
        "SECURE",
        "OFF",
        "NONE_FOUND",
        "EXPECTED",
    }
)


class Finding(BaseModel):
    category: str
    item: str
    status: str
    severity: Severity
    class_: FindingClass = Field(alias="class")
    scored: bool = True
    detail: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @classmethod
    def from_check(
        cls,
        *,
        category: str,
        item: str,
        status: str,
        severity: Severity,
        detail: str = "",
        class_: FindingClass = FindingClass.ACTION,
        scored: bool | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> Finding:
        if status.upper() in _OK_STATUSES:
            class_ = FindingClass.INFO
            scored = False
            if severity == Severity.OK:
                severity = Severity.INFO
        if scored is None:
            scored = class_ == FindingClass.ACTION
        return cls(
            category=category,
            item=item,
            status=status,
            severity=severity,
            class_=class_,
            scored=scored,
            detail=detail,
            evidence=evidence or {},
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "item": self.item,
            "status": self.status,
            "severity": self.severity.value,
            "class": self.class_.value,
            "scored": self.scored,
            "detail": self.detail,
            "evidence": self.evidence,
        }

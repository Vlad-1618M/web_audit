"""Shared models for framework extension fingerprinting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ObservedExtension:
    """One detected plugin, package, or gem."""

    name: str
    version: str | None = None
    source: str = "html"
    unit: str = "plugin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "unit": self.unit,
        }


@dataclass
class ExtensionSignal:
    """Passive framework risk signal (debug leak, version disclosure, …)."""

    key: str
    status: str
    detail: str
    severity: str = "INFO"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass
class ExtensionsProbeResult:
    target_url: str
    framework: str
    unit: str = "plugin"
    extensions: list[ObservedExtension] = field(default_factory=list)
    signals: list[ExtensionSignal] = field(default_factory=list)
    mode: str = "observed_only"
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "framework": self.framework,
            "unit": self.unit,
            "mode": self.mode,
            "extension_count": len(self.extensions),
            "extensions": [item.to_dict() for item in self.extensions],
            "signals": [item.to_dict() for item in self.signals],
            "error": self.error,
        }

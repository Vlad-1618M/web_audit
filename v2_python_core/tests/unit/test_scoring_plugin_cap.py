"""Tests for plugin hygiene caps and SEO unscored policy."""

from webaudit.config.settings import HygieneWeights, ScoringSettings
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.scoring.engine import score_findings


def _stale_plugin(slug: str) -> Finding:
    return Finding.from_check(
        category="PLUGIN",
        item=slug,
        status="STALE",
        severity=Severity.HIGH,
        class_=FindingClass.ACTION,
        scored=True,
    )


def test_plugin_worst_wins_caps_at_thirty_with_five_stale_plugins():
    findings = [_stale_plugin(f"plugin-{i}") for i in range(5)]
    scoring = ScoringSettings(plugin_worst_wins=True, hygiene_caps={"PLUGIN": 30})
    scores = score_findings(findings, HygieneWeights(), scoring=scoring)
    # worst wins: only one HIGH (-10), not 5×10=50 capped to 30
    assert scores.hygiene == 90


def test_five_stale_plugins_without_worst_wins_caps_at_seventy():
    findings = [_stale_plugin(f"plugin-{i}") for i in range(5)]
    scoring = ScoringSettings(plugin_worst_wins=False, hygiene_caps={"PLUGIN": 30})
    scores = score_findings(findings, HygieneWeights(), scoring=scoring)
    assert scores.hygiene == 70


def test_seo_surface_never_affects_hygiene_by_default():
    findings = [
        Finding(
            category="SEO_SURFACE",
            item="meta robots",
            status="NOINDEX",
            severity=Severity.INFO,
            class_=FindingClass.VERIFY,
            scored=True,
        )
    ]
    scoring = ScoringSettings(seo_surface_affects_scores=False)
    scores = score_findings(findings, HygieneWeights(), scoring=scoring)
    assert scores.hygiene == 100

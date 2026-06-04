"""Tests for dashboard focus pie chart data."""
from webaudit.models.finding import Finding, Severity
from webaudit.models.run import AuditScores
from webaudit.render.focus_pie import build_focus_pie_slices, focus_pie_chart_html, focus_pie_conic_gradient

def test_focus_pie_slices_cover_full_circle():
    """Ensures Focus Pie Slices Cover Full Circle."""
    scores = AuditScores(hygiene=81, exposure=100, verdict='NEEDS_ATTENTION')
    findings = [Finding.from_check(category='SEO_SURFACE', item='meta description', status='MISSING', severity=Severity.INFO)]
    slices = build_focus_pie_slices(scores, findings)
    assert len(slices) == 3
    assert slices[0]['display'] == '81'
    assert slices[1]['display'] == '100'
    assert slices[1]['label'] == 'Leak protection'
    assert slices[2]['display'] == '1'
    assert sum((slice_['pct'] for slice_ in slices)) == 100
    assert slices[-1]['end_pct'] == 100
    gradient = focus_pie_conic_gradient(slices)
    assert 'conic-gradient' in gradient
    assert '#ffc14d' in gradient
    chart = focus_pie_chart_html(gradient=gradient, hygiene=81, exposure=100)
    assert 'class="focus-pie-chart"' in chart
    assert gradient in chart

def test_focus_pie_changes_with_hygiene_and_seo():
    """Ensures Focus Pie Changes With Hygiene And SEO."""
    findings_none: list[Finding] = []
    findings_seo = [Finding.from_check(category='SEO_SURFACE', item=f'check-{i}', status='MISSING', severity=Severity.INFO) for i in range(4)]
    strong = build_focus_pie_slices(AuditScores(hygiene=81, exposure=100), findings_none)
    weak = build_focus_pie_slices(AuditScores(hygiene=60, exposure=100), findings_seo)
    assert strong[0]['pct'] != weak[0]['pct']
    assert weak[2]['pct'] > strong[2]['pct']
    assert weak[0]['pct'] < strong[0]['pct']

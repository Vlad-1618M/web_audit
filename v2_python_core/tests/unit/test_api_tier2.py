"""Tests for ``webaudit.collectors.api`` and API analyzers."""
import json
from webaudit.analyzers.graphql import analyze_graphql
from webaudit.analyzers.openapi import analyze_openapi
from webaudit.collectors.api import collect_api_surface
from webaudit.config.settings import ApiCollectorSettings

def test_graphql_introspection_detected(httpx_mock):
    """Ensures GraphQL Introspection Detected."""
    body = json.dumps({'data': {'__schema': {'queryType': {'name': 'Query'}}}})
    httpx_mock.add_response(method='POST', url='https://example.com/graphql', json=json.loads(body), text=body)
    httpx_mock.add_response(method='POST', url='https://example.com/api/graphql', status_code=404)
    httpx_mock.add_response(method='POST', url='https://example.com/v1/graphql', status_code=404)
    settings = ApiCollectorSettings(enabled=True, openapi_paths=[])
    probe = collect_api_surface('https://example.com', settings=settings, user_agent='WebAudit/test', timeout_seconds=5)
    findings = analyze_graphql(probe, settings)
    assert probe.graphql_probes[0].introspection_enabled is True
    assert any((f.status == 'INTROSPECTION' for f in findings))

def test_openapi_spec_detected(httpx_mock):
    """Ensures OpenAPI Spec Detected."""
    spec = {'openapi': '3.0.0', 'info': {'title': 'Example API', 'version': '1.0.0'}, 'paths': {}}
    body = json.dumps(spec)
    for path in ApiCollectorSettings().openapi_paths:
        if path == '/openapi.json':
            httpx_mock.add_response(url=f'https://example.com{path}', text=body)
        else:
            httpx_mock.add_response(url=f'https://example.com{path}', status_code=404)
    probe = collect_api_surface('https://example.com', settings=ApiCollectorSettings(enabled=True, graphql_probe=False), user_agent='WebAudit/test', timeout_seconds=5)
    findings = analyze_openapi(probe, ApiCollectorSettings(enabled=True))
    assert probe.openapi_probes[0].openapi_detected is True
    assert findings[0].status == 'EXPOSED'
    assert 'Example API' in findings[0].detail

"""Tests for ``webaudit.analyzers.artifacts``."""

from webaudit.analyzers.artifacts import analyze_artifacts, parse_robots_txt, robots_path_disallowed
from webaudit.collectors.artifacts import ArtifactsProbeResult, RobotsArtifact, SecurityTxtArtifact
from webaudit.config.settings import ArtifactsCollectorSettings


def test_robots_disallow_match():
    disallow, allow, _ = parse_robots_txt("User-agent: *\nDisallow: /secret/\nAllow: /secret/public/")
    assert robots_path_disallowed("/secret/file", disallow, allow) is True
    assert robots_path_disallowed("/secret/public/page", disallow, allow) is False


def test_security_txt_stale_expires():
    probe = ArtifactsProbeResult(
        target_url="https://example.com",
        security_txt=SecurityTxtArtifact(
            present=True,
            body="Contact: mailto:sec@example.com\nExpires: 2020-01-01\n",
        ),
    )
    findings = analyze_artifacts(probe, ArtifactsCollectorSettings())
    expiry = next(f for f in findings if f.item == "security.txt Expires")
    assert expiry.status == "STALE"
    assert expiry.scored is True


def test_robots_open_path_conflict():
    probe = ArtifactsProbeResult(
        target_url="https://example.com",
        robots=RobotsArtifact(status_code=200, raw="Disallow: /backup/\n"),
    )
    open_paths = [{"path": "/backup/", "note": "OPEN", "final_status": 200}]
    findings = analyze_artifacts(probe, ArtifactsCollectorSettings(), open_paths=open_paths)
    assert any("robots vs probe" in f.item for f in findings)

"""Tests for ``webaudit.collectors.paths`` — path probe list and HTTP classification."""

from webaudit.collectors.paths import (
    build_probe_list,
    classify_final_status,
    collect_paths,
)
from webaudit.config.settings import PathsSettings


def test_classify_final_status():
    assert classify_final_status(200) == "OPEN"
    assert classify_final_status(403) == "PROTECTED_403"
    assert classify_final_status(500) == "SERVER_ERROR"
    assert classify_final_status(504) == "SERVER_ERROR"
    assert classify_final_status(None) == "NO_RESPONSE"


def test_build_probe_list_respects_limit_and_extra():
    settings = PathsSettings(
        sensitive_builtin=False,
        extra_paths=["/.env", "/custom"],
        max_probe_urls=2,
    )
    paths = build_probe_list(framework="auto", paths_settings=settings)
    assert paths == ["/.env", "/custom"]


def test_collect_paths_probes_with_mock_client():
    class FakeResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    class FakeClient:
        def get(self, url, headers, follow_redirects):
            if url.endswith("/.env"):
                return FakeResponse(404 if not follow_redirects else 404)
            raise AssertionError(f"unexpected url {url}")

        def close(self):
            pass

    settings = PathsSettings(sensitive_builtin=False, extra_paths=["/.env"])
    result = collect_paths(
        "https://example.com",
        framework="auto",
        paths_settings=settings,
        user_agent="test",
        timeout_seconds=5,
        client=FakeClient(),
    )
    assert len(result.probes) == 1
    assert result.probes[0].path == "/.env"
    assert result.probes[0].note == "NOT_FOUND"


def test_collect_paths_on_probe_callbacks():
    class FakeResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    class FakeClient:
        def get(self, url, headers, follow_redirects):
            return FakeResponse(404)

        def close(self):
            pass

    settings = PathsSettings(
        sensitive_builtin=False,
        extra_paths=["/a", "/b"],
    )
    started: list[int] = []
    done: list[tuple[str, int, int]] = []

    collect_paths(
        "https://example.com",
        framework="auto",
        paths_settings=settings,
        user_agent="test",
        timeout_seconds=5,
        client=FakeClient(),
        on_probe_start=started.append,
        on_probe=lambda entry, index, total: done.append((entry.path, index, total)),
    )
    assert started == [2]
    assert done == [("/a", 1, 2), ("/b", 2, 2)]

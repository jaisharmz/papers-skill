"""The cache, and the status semantics that keep a rate limit from becoming a
finding. No test here opens a socket."""
from __future__ import annotations

import urllib.error

import pytest

from scripts import fetch as F


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(F, "MIN_INTERVAL", {})


def _fake(code=200, body=b'{"a":1}'):
    calls = {"n": 0}

    class R:
        status = code
        def read(self): return body
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def opener(req, timeout=None):
        calls["n"] += 1
        if code >= 400:
            raise urllib.error.HTTPError(req.full_url, code, "err", {}, None)
        return R()
    return opener, calls


def test_a_success_is_cached_and_replayed_and_a_corrupt_entry_refetches(monkeypatch):
    """The cache is what makes iterating on selection cost nothing. A corrupt
    entry must not wedge it."""
    op, calls = _fake()
    monkeypatch.setattr(F.urllib.request, "urlopen", op)
    assert F.get("https://x/1").json() == {"a": 1}
    assert F.get("https://x/1").cached and calls["n"] == 1
    F._key("https://x/1").write_text("{not json")
    assert F.get("https://x/1").ok and calls["n"] == 2


@pytest.mark.parametrize("code,status", [(403, F.THROTTLED), (429, F.THROTTLED),
                                         (404, F.MISSING)])
def test_a_rate_limit_and_an_absence_are_different_answers(monkeypatch, code, status):
    op, _ = _fake(code)
    monkeypatch.setattr(F.urllib.request, "urlopen", op)
    r = F.get("https://x/2")
    assert r.status == status and not r.ok
    if status is F.THROTTLED:
        assert "not absent" in r.detail


def test_a_failure_is_never_cached(monkeypatch):
    """Caching a 429 turns a transient block into a permanent hole that looks
    like an answer."""
    op, calls = _fake(429)
    monkeypatch.setattr(F.urllib.request, "urlopen", op)
    F.get("https://x/4"); F.get("https://x/4")
    assert calls["n"] == 2 and F.cache_stats()["files"] == 0

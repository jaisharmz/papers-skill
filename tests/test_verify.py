"""Identifier verification: the failure that has actually shipped.

A plausible paper title welded to a genuine arXiv identifier survives every check
except following the link. Repos have a worse version, because an `owner/repo`
that does not exist looks more checkable than a title does, and a guessed commit
hash is the most confident-looking wrong answer in the pipeline.

Fixtures only. The decision logic is what decides whether a fabricated entry
ships, and that is what is tested here.
"""
from __future__ import annotations

import pytest

from scripts import verify as V

ENTRY = b"<feed><entry><title>Simple and Effective Masked Diffusion\n  Language Models</title></entry></feed>"


def test_a_plausible_title_on_a_real_id_is_caught_and_the_real_one_passes(monkeypatch):
    monkeypatch.setattr(V, "_get", lambda url, timeout=20: (200, ENTRY))
    good = V.verify_arxiv("2406.07524", "Simple and Effective Masked Diffusion Language Models")
    bad = V.verify_arxiv("2406.07524", "Discrete Flow Matching for Language Generation")
    assert good.ok and good.status == "verified"
    assert not bad.ok and bad.status == "title-mismatch"


def test_near_miss_titles_are_separated_from_matches():
    """Two real papers with overlapping authors and a shared prefix. A substring
    check passes the pair; token overlap is what tells them apart."""
    assert V.similarity("Flow Matching for Generative Modeling",
                        "Flow Matching Guide and Code") < V.MATCH_FLOOR
    assert V.similarity("Denoising Diffusion Probabilistic Models",
                        "denoising diffusion probabilistic models!") >= V.MATCH_FLOOR


@pytest.mark.parametrize("check,ref", [(V.verify_repo, "kuleshov-group/mdlm"),
                                       (V.verify_arxiv, "2406.07524")])
def test_throttling_is_never_reported_as_absence(monkeypatch, check, ref):
    """78 of 88 came back "no public repos" once and it was a rate limit. That
    read as a finding. Both paths must say throttled, because a caller that
    treats it as absence has invented one."""
    monkeypatch.setattr(V, "_get", lambda url, timeout=20: (429, b""))
    r = check(ref, "") if check is V.verify_arxiv else check(ref)
    assert r.status == "throttled" and r.status != "not-found" and not r.ok


def test_a_missing_repo_is_absence_and_a_guessed_commit_fails(monkeypatch):
    monkeypatch.setattr(V, "_get", lambda url, timeout=20: (404, b""))
    assert V.verify_repo("nobody/nothing").status == "not-found"
    assert not V.verify_commit("owner/repo", "a3f21c9").ok
    assert V.verify_commit("owner/repo", "not-a-hash").detail == "not a hash"


def test_a_run_that_hit_a_limit_reports_itself_degraded(monkeypatch):
    monkeypatch.setattr(V, "_get", lambda url, timeout=20: (403, b""))
    assert V.verify_entries([{"kind": "repo", "id": "a/b"}])["degraded"]

"""Store invariants. The unsourced-edge raise is the one that matters most."""
from __future__ import annotations

import pytest

from scripts import pgraph as G


@pytest.fixture
def conn():
    return G.connect(":memory:")


def test_edge_without_a_source_raises(conn):
    """An unsourced relationship is an assertion, and assertions do not get read."""
    a = G.upsert_node(conn, "paper", "A")
    b = G.upsert_node(conn, "paper", "B")
    for bad in ("", None, "not-a-url", "/relative"):
        with pytest.raises(G.GraphError):
            G.add_edge(conn, a, b, "cites", source_url=bad, context="builds_on")


def test_cites_requires_a_context(conn):
    """An untyped citation edge is nearly worthless. builds_on and baseline are
    opposite findings and a bare edge cannot tell them apart."""
    a, b = G.upsert_node(conn, "paper", "A"), G.upsert_node(conn, "paper", "B")
    with pytest.raises(G.GraphError):
        G.add_edge(conn, a, b, "cites", source_url="https://x/1", context="vibes")
    assert G.add_edge(conn, a, b, "cites", source_url="https://x/1", context="baseline")


@pytest.mark.parametrize("first,second", [
    ({"arxiv": "2406.07524v2"}, {}),      # id then bare title
    ({}, {"arxiv": "2406.07524v2"}),      # bare title then id
])
def test_adopt_works_in_both_directions(conn, first, second):
    """Outbound's version only covers one direction. Traversals meet a paper as a
    reference string before they resolve its identifier at least as often."""
    a = G.upsert_node(conn, "paper", "Simple and Effective Masked Diffusion", external=first)
    b = G.upsert_node(conn, "paper", "Simple and Effective Masked Diffusion", external=second)
    assert a == b
    assert conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 1


def test_arxiv_versions_are_one_work(conn):
    a = G.upsert_node(conn, "paper", "X", external={"arxiv": "2406.07524v1"})
    b = G.upsert_node(conn, "paper", "X", external={"arxiv": "arxiv.org/abs/2406.07524v3"})
    assert a == b


def test_two_real_ids_never_silently_merge(conn):
    """Merging two nodes that both carry ids is a judgment call, and a silent
    merge is unrecoverable. Record the collision instead."""
    a = G.upsert_node(conn, "paper", "Attention", external={"arxiv": "1706.03762"})
    b = G.upsert_node(conn, "paper", "Attention", external={"arxiv": "2401.99999"})
    assert a != b
    assert conn.execute("SELECT COUNT(*) FROM collisions").fetchone()[0] == 1


def test_path_count_beats_hop_count(conn):
    """A 2-hop reached three ways is more central than a 1-hop reached once, and
    that is the idea worth keeping from outbound's scorer."""
    near = G.upsert_node(conn, "paper", "near")
    far = G.upsert_node(conn, "paper", "far")
    G.record_path(conn, near, "r1", seed_node_id=1, hops=1, via="search")
    for i, via in enumerate(["refs", "citers", "author"]):
        G.record_path(conn, far, "r1", seed_node_id=1, hops=2, via=via)
    assert G.path_count(conn, far) == 3 > G.path_count(conn, near)
    s_near = G.score_node(conn, near, hops=1)
    s_far = G.score_node(conn, far, hops=2)
    assert s_far.total > s_near.total


def test_hub_is_penalised(conn):
    """Expanding a node with hundreds of edges reaches everything and
    distinguishes nothing."""
    hub = G.upsert_node(conn, "paper", "hub")
    for i in range(G.HUB_DEGREE + 40):
        n = G.upsert_node(conn, "paper", f"p{i}")
        G.add_edge(conn, n, hub, "cites", source_url=f"https://x/{i}", context="baseline")
    s = G.score_node(conn, hub, hops=1)
    assert any("hub penalty" in n for n in s.notes)


def test_coverage_takes_the_best_not_the_sum(conn):
    """Summing would make coverage grow linearly and void the prefix guarantee."""
    idea = G.upsert_node(conn, "idea", "the trick")
    a, b = G.upsert_node(conn, "paper", "A"), G.upsert_node(conn, "repo", "o/r")
    # High weight first, low weight second, so a scan that keeps the LAST value
    # instead of the best is observable. Inserted the other way round the test
    # passes either way, which is how it survived the mutation audit.
    G.add_edge(conn, a, idea, "covers", source_url="https://x/a", weight=0.9)
    G.add_edge(conn, b, idea, "covers", source_url="https://x/b", weight=0.4)
    assert G.covered_ideas(conn, [a, b]) == {idea: 0.9}


def test_expansion_refusals_are_recorded(conn):
    """This is what answers 'why is X not in here' without re-running anything."""
    n = G.upsert_node(conn, "paper", "hub")
    G.log_expansion(conn, "r1", n, "skipped", "hub: 312 edges, would not discriminate")
    row = conn.execute("SELECT decision, reason FROM expansions").fetchone()
    assert row["decision"] == "skipped" and "hub" in row["reason"]

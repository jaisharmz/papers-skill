"""The thesis, as assertions: every prefix of M is approximately the best M.

Kept deliberately small. Each test here kills at least one mutation in
tests/mutate.py, which is how "the suite is green" is made to mean something.
An earlier version of this file had twenty tests and several of them passed no
matter what the code did, because their fixtures were too small to reach the
branch they claimed to test.
"""
from __future__ import annotations

import pytest

from scripts import ordering as S
from tests.fixtures.toy import ITEMS, IDEA_WEIGHTS

KW = dict(weights=IDEA_WEIGHTS)
# "the objective this subfield optimizes" is the idea without which nothing else
# on this path is legible, so it is what position one has to touch.
FOUNDATIONAL = {"i_obj": True}


@pytest.fixture
def picks():
    seed = S.lookahead_seed(ITEMS, candidates=["survey", "seminal", "bench", "pos_a"],
                            depth=5, foundational=FOUNDATIONAL, **KW)
    return S.attach_subgroups(S.greedy(ITEMS, seed=seed, **KW), ITEMS, **KW)


def test_every_invariant_holds_on_a_realistic_path(picks):
    """The five ordering invariants plus the two structural ones, together.

    Kills: coverage summing instead of taking the best, the prerequisite gate
    opening, recompute not updating between picks, stranded items surviving.
    """
    failures = {k: v for k, v in
                S.check_all(picks, ITEMS, foundational=FOUNDATIONAL, **KW).items() if v}
    assert not failures, failures


def test_a_seed_that_cannot_stand_alone_is_never_simulated():
    """Filtering candidates before the lookahead, not grading the winner after."""
    assert S.lookahead_seed(ITEMS, candidates=["bench", "seminal"], depth=4,
                            foundational=FOUNDATIONAL, **KW) == "seminal"


def test_position_one_is_chosen_for_its_path_not_its_own_value():
    """The survey covers four ideas cheaply and teaches none of them. Greedy on
    raw coverage takes it every time; the depth-payoff damping plus the lookahead
    is what stops it. Kills: depth payoff no longer damping."""
    seed = S.lookahead_seed(ITEMS, candidates=["survey", "seminal", "bench", "pos_a"],
                            depth=5, **KW)
    assert seed != "survey"
    assert S.greedy(ITEMS, **KW)[0].item.id != "survey"


def test_value_is_recomputed_after_every_pick(picks):
    """The conditioning. A repo that only restates the trick is worth something
    cold and nothing once the trick is covered, and no static ranking produces
    that drop. Kills: coverage summing, recompute doing nothing."""
    dump = next(i for i in ITEMS if i.id == "repo_dump")
    assert S.marginal(dump, {}, IDEA_WEIGHTS)[0] > 0
    assert S.marginal(dump, {"i_trick": 0.95}, IDEA_WEIGHTS)[0] == 0
    assert all(p.marginal > 0 for p in picks[1:]), "a zero-value entry reached the path"


def test_a_disagreement_needs_both_sides_and_they_land_adjacent(picks):
    """One side alone must not claim the disagreement, or the other side scores
    nothing and never appears. Kills: pair coverage landing without its partner."""
    assert "arg" not in S.coverage([next(i for i in ITEMS if i.id == "pos_a")])
    order = [p.item.id for p in picks]
    assert abs(order.index("pos_a") - order.index("pos_b")) == 1


def test_the_prefix_check_refuses_a_reorder_that_calls_itself_a_dispute():
    """The exemption for dispute placement must not rubber-stamp any move."""
    p = S.greedy(ITEMS, **KW)
    p[-1].moved_for = "seminal"
    assert S.check_prefix_optimal(p, ITEMS, **KW)


def test_some_knowledge_is_not_readable():
    """plan.md 5.1. i_fail is covered weakly by a repo and fully only by doing it,
    so a path with no project leaves it dark. This is the argument for
    interleaving rather than three lists."""
    assert S.coverage([i for i in ITEMS if i.kind != "project"]).get("i_fail", 0) < 0.5
    assert S.coverage(ITEMS)["i_fail"] >= 0.9


def test_an_idea_with_a_single_expensive_coverer_is_reported_not_dropped():
    """Rate-greedy drops a 40-hour project, and the idea only it covers then
    stays uncovered at any budget with nothing saying so."""
    cheap = S.Item(id="cheap", kind="paper", title="C", covers={"a": .9}, cost_hours=1,
                   depth_payoff=.9, year=2024, phrase="cheap and broad")
    only = S.Item(id="only", kind="project", title="P", covers={"hands_on": .95},
                  cost_hours=40, depth_payoff=.95, phrase="the only way to learn it")
    bad = S.check_unique_coverers(S.greedy([cheap, only], limit=1), [cheap, only])
    assert bad and "hands_on" in bad[0] and "only" in bad[0]
    assert not S.check_unique_coverers(S.greedy([cheap, only]), [cheap, only])


# --- the depth dimension --------------------------------------------------


def _deep():
    """One idea with four approaches, one unrelated idea, and one item that
    covers ground already taken so it is genuinely demotable. The last part is
    what earlier fixtures lacked: nothing was ever demoted, so every test about
    demotion passed without reaching the code."""
    mk = lambda i, v, c, d: S.Item(id=i, kind="paper", title=i, covers={"obj": c},
                                   variants={"obj": v}, cost_hours=2, depth_payoff=d,
                                   year=2024, phrase=f"{i} does {v}")
    return [
        mk("parent", "the survey framing", .9, .85),
        mk("via_value", "value-aware model loss", .6, .9),
        mk("via_theory", "a bound on compounding error", .55, .95),
        mk("dupe", "value-aware model loss", .6, .5),
        S.Item(id="other", kind="paper", title="other", covers={"else": .9},
               variants={"else": "unrelated"}, cost_hours=2, depth_payoff=.8,
               year=2023, phrase="a different idea"),
    ]


def test_the_spine_carries_breadth_and_approaches_go_underneath():
    """Global redundancy is local depth: an item the spine drops because
    something already covers its idea is another approach to that idea."""
    items = _deep()
    picks = S.attach_subgroups(S.greedy(items), items)
    spine = {p.item.id for p in picks}
    assert spine == {"parent", "other"}, spine
    par = next(p for p in picks if p.item.id == "parent")
    assert par.sub and {c.item.id for c in par.sub.picks} == {"via_value", "via_theory"}


def test_a_subgroup_ranks_by_mechanism_and_never_repeats_one():
    """Coverage is the wrong ruler inside a group: everything there covers the
    parent's idea, so on coverage they all score zero. Kills: the duplicate
    approach check no longer firing."""
    items = _deep()
    par = next(p for p in S.attach_subgroups(S.greedy(items), items)
               if p.item.id == "parent")
    approaches = [c.item.variants["obj"] for c in par.sub.picks]
    assert len(approaches) == len(set(approaches))
    assert "dupe" not in {c.item.id for c in par.sub.picks}
    assert [c.rate for c in par.sub.picks] == sorted([c.rate for c in par.sub.picks],
                                                     reverse=True)
    par.sub.picks[0].item.variants["obj"] = par.sub.picks[1].item.variants["obj"]
    assert S.check_subgroups([par], items), "a repeated approach must be reported"


def test_numbering_runs_in_the_order_you_would_follow_it():
    items = _deep()
    picks = S.attach_subgroups(S.greedy(items), items)
    assert [p.number for p in picks] == [str(n) for n in range(1, len(picks) + 1)]
    for p in picks:
        if p.sub:
            assert [c.number for c in p.sub.picks] == \
                   [f"{p.number}.{n}" for n in range(1, len(p.sub.picks) + 1)]


def test_nothing_selected_is_ever_lost_between_the_spine_and_the_groups():
    """A demoted item that no subgroup takes has vanished from both places, which
    is the silent drop this skill warns about, committed by the skill.
    Kills: the orphan reinstatement being removed."""
    # `orphan` opens no new idea, so demotion reaches for it, and it carries NO
    # variant so no subgroup will take it either. That is the exact shape that
    # fell out of both places. Earlier fixtures had nothing in this state, so the
    # test passed without reaching the code it names.
    # `orphan` must be SELECTED (positive marginal) and then demoted (opens no
    # new idea) and then homeless (no variant label). Under the value rule that
    # means covering an idea partially, not covering it cheaply.
    items = _deep() + [S.Item(id="orphan", kind="paper", title="orphan",
                              covers={"else": .95}, cost_hours=2, depth_payoff=.95,
                              year=2022, phrase="deepens the other idea")]
    selected = {p.item.id for p in S.greedy(items)}
    assert "orphan" in selected, "fixture no longer exercises demotion"
    picks = S.attach_subgroups(S.greedy(items), items)
    assert selected <= S._placed(picks), f"lost: {selected - S._placed(picks)}"


def test_structural_items_are_never_demoted_off_the_spine():
    """A dispute partner and a required prerequisite both have positive value but
    open no new idea, so the demotion rule reaches for them. Both must survive.
    Kills: demotion no longer consulting the protected set."""
    a = S.Item(id="a", kind="paper", title="a", covers={"x": .9}, cost_hours=2,
               depth_payoff=.9, year=2024, phrase="one side",
               pair_covers={"arg": ("b", .95)}, disputes=["b"])
    b = S.Item(id="b", kind="paper", title="b", covers={}, cost_hours=2, depth_payoff=.8,
               year=2025, phrase="the other side",
               pair_covers={"arg": ("a", .95)}, disputes=["a"])
    base = S.Item(id="base", kind="repo", title="base", covers={"x": .5}, cost_hours=2,
                  depth_payoff=.7, year=2025, phrase="the base to build on")
    proj = S.Item(id="proj", kind="project", title="proj", covers={"hands": .95},
                  cost_hours=14, depth_payoff=.95, requires=["base"],
                  phrase="build on the base")
    items = [a, b, base, proj]
    picks = S.attach_subgroups(S.greedy(items, weights={"x": 1, "arg": 1.5, "hands": 1}),
                               items, weights={"x": 1, "arg": 1.5, "hands": 1})
    ids = [p.item.id for p in picks]
    assert "b" in ids and abs(ids.index("a") - ids.index("b")) == 1
    assert "base" in ids and not S.check_prerequisites(picks)


def test_a_row_missing_its_year_or_phrase_is_caught():
    """Both exist so a reader can decide whether to open something without
    opening it, which is the deliberation the whole skill removes."""
    items = _deep()
    items[0].year = None
    items[1].phrase = ""
    items[2].phrase = " ".join(["word"] * 20)
    bad = S.check_display_fields(S.attach_subgroups(S.greedy(items), items))
    assert any("no year" in b for b in bad)
    assert any("no phrase" in b for b in bad)
    assert any("rather than a glance" in b for b in bad)


def test_the_three_post_pass_functions_do_what_they_claim():
    """_recompute, _prune and the orphan reinstatement, exercised directly.

    All three run after the greedy and each one silently corrupted the output
    once. Reaching their branches through a fixture turned out to be luck, so
    they are driven with explicit inputs here.
    """
    a = S.Item(id="a", kind="paper", title="a", covers={"x": .9}, cost_hours=2,
               depth_payoff=.9, phrase="opens x")
    dup = S.Item(id="dup", kind="paper", title="dup", covers={"x": .5}, cost_hours=2,
                 depth_payoff=.9, phrase="says x again")
    picks = [S.Pick(item=dup, position=1, marginal=.5, rate=.2, newly_covered=["x"],
                    conditioning=""),
             S.Pick(item=a, position=2, marginal=.9, rate=.4, newly_covered=["x"],
                    conditioning="")]

    # _recompute must measure each pick against the real prefix, not a blank one.
    S._recompute(picks)
    assert picks[0].marginal == 0.5
    assert picks[1].marginal == pytest.approx(0.4), \
        "second pick must be worth only what it ADDS over the first"
    assert picks[1].newly_covered == [], "x was already covered by the first pick"

    # _prune must drop what the final order left at zero, and keep what is needed.
    zero = S.Pick(item=S.Item(id="z", kind="paper", title="z", covers={"x": .3},
                              cost_hours=1, phrase="adds nothing now"),
                  position=3, marginal=0.0, rate=0.0, newly_covered=[], conditioning="")
    assert [p.item.id for p in S._prune(picks + [zero])] == ["dup", "a"]

    base = S.Item(id="base", kind="repo", title="base", covers={"x": .2},
                  cost_hours=1, phrase="the base")
    proj = S.Item(id="proj", kind="project", title="proj", covers={"h": .9},
                  cost_hours=9, requires=["base"], phrase="build on it")
    kept = S._prune([S.Pick(item=base, position=1, marginal=0.0, rate=0.0,
                            newly_covered=[], conditioning=""),
                     S.Pick(item=proj, position=2, marginal=.9, rate=.1,
                            newly_covered=["h"], conditioning="")])
    assert [p.item.id for p in kept] == ["base", "proj"], \
        "a prerequisite worth nothing on its own must survive pruning"


def test_a_demoted_item_that_no_group_takes_comes_back():
    """Built so demotion definitely fires and no subgroup can take the result:
    `tail` opens no idea and carries no approach label. Earlier fixtures never
    reached this state, so the test that named it passed without running it."""
    # head is cheap and broad so it goes first and opens both ideas. tail then
    # has positive marginal (it covers x slightly better) but opens nothing, which
    # is exactly the demotable shape, and it names no approach so no group takes it.
    head = S.Item(id="head", kind="paper", title="head", covers={"x": .9, "y": .9},
                  cost_hours=1, depth_payoff=.95, phrase="opens both ideas")
    tail = S.Item(id="tail", kind="paper", title="tail", covers={"x": .99},
                  cost_hours=1, depth_payoff=.9, phrase="nudges x, names no approach")
    items = [head, tail]
    raw = S.greedy(items)
    assert {p.item.id for p in raw} == {"head", "tail"}
    spine, demoted = S.split_spine(raw, items=items)
    assert [d.item.id for d in demoted] == ["tail"], "fixture must demote something"
    placed = S._placed(S.attach_subgroups(S.greedy(items), items))
    assert "tail" in placed, "demoted with no home means dropped from both places"


def test_a_subgroup_forms_on_whichever_idea_has_companions():
    """The parent's top-weighted idea often has no companions while its second
    does. Using only the first left an entry with obvious companions holding an
    empty group."""
    par = S.Item(id="par", kind="paper", title="par", covers={"thin": .95, "busy": .4},
                 variants={"thin": "alone", "busy": "one reading"}, cost_hours=2,
                 depth_payoff=.9, phrase="covers a thin idea and a busy one")
    # `thin` is tried first and DOES have a companion, so "take the first idea
    # with any candidates" gets the wrong group. Only "take the idea with the
    # most" gets it right, which is the distinction the fixture has to force.
    thin1 = S.Item(id="thin1", kind="paper", title="thin1", covers={"thin": .5},
                   variants={"thin": "a second angle on thin"}, cost_hours=2,
                   depth_payoff=.8, phrase="the only companion for thin")
    c1 = S.Item(id="c1", kind="paper", title="c1", covers={"busy": .6},
                variants={"busy": "another reading"}, cost_hours=2, depth_payoff=.8,
                phrase="a second angle on busy")
    c2 = S.Item(id="c2", kind="paper", title="c2", covers={"busy": .5},
                variants={"busy": "a third reading"}, cost_hours=2, depth_payoff=.8,
                phrase="a third angle on busy")
    sg = S.subgroup_for(S.Pick(item=par, position=1, marginal=1, rate=1,
                               newly_covered=["thin"], conditioning="", number="1"),
                        [thin1, c1, c2])
    assert sg is not None and sg.idea == "busy", \
        "the group must form on the idea with the most companions, not the first"
    assert {c.item.id for c in sg.picks} == {"c1", "c2"}


def test_a_budget_bounds_the_path():
    assert sum(p.item.cost_hours for p in S.greedy(ITEMS, budget_hours=6, **KW)) <= 6


def test_position_one_must_stand_alone():
    """The failure the reader caught: a path about world models opened with an
    analysis of one system's learned model and followed it with a GitHub thread
    about a library version. Neither answers "what is a world model"."""
    found = {"i_obj": True}
    seminal = next(i for i in ITEMS if i.id == "seminal")     # covers i_obj
    bench = next(i for i in ITEMS if i.id == "bench")         # covers only i_bench
    ok = [S.Pick(item=seminal, position=1, marginal=1, rate=1, newly_covered=["i_obj"],
                 conditioning="", seeded=True)]
    assert not S.check_seed_stands_alone(ok, found)
    bad = [S.Pick(item=bench, position=1, marginal=1, rate=1, newly_covered=["i_bench"],
                  conditioning="", seeded=True)]
    msgs = S.check_seed_stands_alone(bad, found)
    assert msgs and "foundational" in msgs[0]


def test_position_one_may_not_be_a_repo_or_a_project():
    """"the best M papers" is what was asked for. A GitHub issue thread at two is
    the same error one position later."""
    repo = S.Item(id="r", kind="repo", title="o/r", covers={"i_obj": .9},
                  cost_hours=.5, phrase="a thread")
    msgs = S.check_seed_stands_alone(
        [S.Pick(item=repo, position=1, marginal=1, rate=1, newly_covered=["i_obj"],
                conditioning="", seeded=True)], {"i_obj": True})
    assert any("best M papers" in m for m in msgs)


def test_position_one_may_not_have_prerequisites():
    it = S.Item(id="x", kind="paper", title="X", covers={"i_obj": .9},
                requires=["y"], cost_hours=2, phrase="needs something first")
    msgs = S.check_seed_stands_alone(
        [S.Pick(item=it, position=1, marginal=1, rate=1, newly_covered=["i_obj"],
                conditioning="", seeded=True)], {"i_obj": True})
    assert any("better position one" in m for m in msgs)


def test_an_idea_prerequisite_unlocks_when_the_idea_is_covered():
    """A prerequisite is either an item or an IDEA. Checking only item ids made
    every idea prerequisite permanently unsatisfiable, and a real path silently
    halved with nothing saying so."""
    base = S.Item(id="base", kind="paper", title="base", covers={"i_what": .9},
                  cost_hours=2, depth_payoff=.9, year=2018, phrase="defines the thing")
    needs = S.Item(id="needs", kind="paper", title="needs", covers={"i_audit": .9},
                   requires=["i_what"], cost_hours=2, depth_payoff=.9, year=2023,
                   phrase="audits the thing")
    assert not S.available(needs, set(), {})
    assert not S.available(needs, set(), {"i_what": 0.2})
    assert S.available(needs, set(), {"i_what": 0.9})
    order = [p.item.id for p in S.greedy([needs, base])]
    assert order == ["base", "needs"], order
    assert not S.check_prerequisites(S.greedy([needs, base]))


def test_a_subgroup_candidate_gated_by_an_idea_is_not_excluded():
    """Same bug as the spine had, one level down: subgroup candidacy compared
    `requires` against item ids, so anything needing an IDEA was dropped outright.
    It cost a real run its cleanest dispute."""
    base = S.Item(id="base", kind="paper", title="base", covers={"i_what": .9},
                  cost_hours=2, depth_payoff=.9, year=2018, phrase="defines it")
    parent = S.Item(id="parent", kind="paper", title="parent", covers={"arg": .5},
                    variants={"arg": "one framing"}, requires=["i_what"],
                    cost_hours=2, depth_payoff=.9, year=2023, phrase="one side")
    side = S.Item(id="side", kind="paper", title="side", covers={"arg": .45},
                  variants={"arg": "the other framing"}, requires=["i_what"],
                  cost_hours=2, depth_payoff=.85, year=2024, phrase="the other side")
    items = [base, parent, side]
    picks = S.attach_subgroups(S.greedy(items), items)
    assert "side" in S._placed(picks), "an idea-gated candidate must still be reachable"


def test_the_prefix_check_only_offers_the_spine_things_it_would_keep():
    """A deepening-only alternative is depth, not a better spine item.

    Regression from a real run: once a paper that only deepened an idea was filed
    in a subgroup, an unplaced paper deepening the same idea was reported as beating
    later spine positions, although split_spine would have demoted it too. An
    alternative that opens a NEW idea at a higher rate must still be reported.
    """
    opener = S.Item(id="opener", kind="paper", title="O", year=2024, phrase="opens a and b",
                    covers={"a": .3, "b": .9}, depth_payoff=.8, cost_hours=1)
    later = S.Item(id="later", kind="paper", title="L", year=2024, phrase="opens c",
                   covers={"c": .4}, depth_payoff=.5, cost_hours=1)
    deepen = S.Item(id="deepen", kind="paper", title="D", year=2024, phrase="deepens a",
                    covers={"a": .8}, depth_payoff=.8, cost_hours=1)
    spine = [S.Pick(item=opener, position=1, marginal=1.2, rate=1.0, newly_covered=["a", "b"],
                    conditioning="", seeded=True, number="1"),
             S.Pick(item=later, position=2, marginal=.4, rate=.3, newly_covered=["c"],
                    conditioning="", number="2")]
    assert S.check_prefix_optimal(spine, [opener, later, deepen]) == []
    rival = S.Item(id="rival", kind="paper", title="R", year=2024, phrase="opens d",
                   covers={"d": .9}, depth_payoff=.9, cost_hours=1)
    bad = S.check_prefix_optimal(spine, [opener, later, deepen, rival])
    assert bad and "'rival'" in bad[0]

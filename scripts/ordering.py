"""The ordering. Greedy coverage per hour, with every prefix good by construction.

Named `ordering` rather than `select` because `select` is a stdlib module, and a
file of that name on sys.path breaks `import urllib` for anything run out of this
directory. That was found by running doctor.py, not by reading, and Python's own
error message is what named it.

This module is PURE: no network, no model, no subprocess. tests/test_selection_purity.py
walks the transitive imports and fails if that ever stops being true. The reason is
not tidiness. It means the ordering can be re-derived from a frozen graph, which
means the prefix property can be tested rather than hoped for, and it means tuning
the order costs nothing because the traversal is already paid for.

The guarantee, stated honestly: greedy on a monotone submodular objective is within
a constant factor of optimal at every prefix length simultaneously. That is what
"the best M you could have read" means here. Global optimality is not claimed and
is not checkable.

Three things the arithmetic does that a static ranking cannot:

  conditioning   an item's value is recomputed after every pick, so a paper that
                 sat at position two can fall to nine once the first pick covered
                 what made it valuable. That drop IS the conditioning.
  cost           items have different costs, so the rule is marginal value per
                 hour rather than marginal value. That is what makes "read three
                 papers" and "do one project" a comparable decision.
  prerequisites  a hard gate, not a score. An item you cannot read yet is worth
                 zero at this position, however good it is.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

# Cost floor in hours. Nothing is free, and a zero would make the value-per-hour
# ratio infinite and hand the first position to whatever was mislabelled.
MIN_COST = 0.25

KINDS = ("paper", "repo", "project")


@dataclass
class Item:
    """One candidate. Everything here is produced upstream by an agent except
    `covers`, which comes off the graph's `covers` edges."""
    id: str
    kind: str                       # paper | repo | project
    title: str
    covers: dict[str, float] = field(default_factory=dict)   # idea id -> weight 0..1
    variants: dict[str, str] = field(default_factory=dict)
    # idea -> the approach this item takes to it. Two papers can cover the same
    # idea by different mechanisms, and that difference is invisible to the
    # global objective: the second one adds no coverage and greedy drops it.
    #
    # It is not worthless, it is DEPTH. A field has a handful of genuinely
    # different ideas and several approaches to each, and the flat path only ever
    # showed the first dimension. Variants are what the subgroups rank on, so the
    # same prefix guarantee applies twice: across the spine for breadth, and
    # inside a subgroup for approaches to one idea.
    year: int | None = None
    phrase: str = ""        # under a sentence. What this is, at a glance.
    pair_covers: dict[str, tuple[str, float]] = field(default_factory=dict)
    # idea -> (partner item id, weight). Covered ONLY when the partner is also
    # selected. plan.md 5.4 says the idea "the field disagrees about X" is only
    # covered once BOTH sides land, and modelling it as ordinary coverage lets
    # one side claim it alone and strands the other side off the path. That is
    # exactly what happened on the first real run: `critique` took position one
    # and covered the fork by itself, so LeCun's side scored nothing and never
    # appeared, and the dispute placement had no pair to place.
    cost_hours: float = 1.0
    requires: list[str] = field(default_factory=list)         # item ids
    depth_payoff: float = 0.5                                 # 0..1, the thesis judgment
    group: str | None = None
    role: str | None = None                                   # paper role or repo archetype
    disputes: list[str] = field(default_factory=list)
    reuses: list[str] = field(default_factory=list)           # projects: earlier item ids
    meta: dict = field(default_factory=dict)


@dataclass
class Subgroup:
    """Approaches to one spine item's idea, ranked so every prefix is good."""
    parent: str
    idea: str
    label: str
    picks: list = field(default_factory=list)


@dataclass
class Pick:
    item: Item
    position: int
    marginal: float                 # coverage added
    rate: float                     # coverage added per hour
    newly_covered: list[str]
    conditioning: str               # why here, given everything before
    runners_up: list[tuple[str, float]] = field(default_factory=list)
    moved_for: str | None = None    # set when _place_disputes pulled this forward
    seeded: bool = False            # position one, chosen by lookahead not greedily
    number: str = ""                # "3" on the spine, "3.2" inside a subgroup
    sub: object = None              # a Subgroup, or None


def coverage(items, prior: dict[str, float] | None = None) -> dict[str, float]:
    """Best weight per idea across a set. Best, not sum.

    This is what makes the objective submodular: the second item covering an idea
    contributes only what it adds beyond the first. Summing would make coverage
    grow linearly and the whole prefix guarantee would be void.

    Pair coverage lands only when both partners are present, which keeps the
    objective submodular: it is zero until the pair completes and constant after,
    so no prefix ever loses value.
    """
    out = dict(prior or {})
    present = {it.id for it in items}
    for it in items:
        for idea, w in it.covers.items():
            if w > out.get(idea, 0.0):
                out[idea] = w
        for idea, (partner, w) in it.pair_covers.items():
            if partner in present and w > out.get(idea, 0.0):
                out[idea] = w
    return out


def total(cov: dict[str, float], weights: dict[str, float] | None = None) -> float:
    if not weights:
        return sum(cov.values())
    return sum(v * weights.get(k, 1.0) for k, v in cov.items())


def marginal(item: Item, cov: dict[str, float],
             weights: dict[str, float] | None = None,
             done: set[str] | None = None) -> tuple[float, list[str]]:
    """What this item adds beyond what is already covered, and which ideas it lands.

    A pair-covered idea only counts when the partner is already selected. That is
    what pulls the second side of an argument forward: alone it is worth little,
    and the moment its partner lands it becomes the highest-value item on the
    board.
    """
    gain, landed = 0.0, []
    for idea, w in item.covers.items():
        have = cov.get(idea, 0.0)
        if w > have:
            gain += (w - have) * ((weights or {}).get(idea, 1.0))
            if have == 0.0:
                landed.append(idea)
    for idea, (partner, w) in item.pair_covers.items():
        if partner not in (done or set()):
            continue
        have = cov.get(idea, 0.0)
        if w > have:
            gain += (w - have) * ((weights or {}).get(idea, 1.0))
            if have == 0.0:
                landed.append(idea)
    return gain, landed


# How much of an idea has to be covered before something that needs it unlocks.
IDEA_MET = 0.5


def available(item: Item, done: set[str], cov: dict[str, float] | None = None) -> bool:
    """The hard gate. Prerequisites are satisfied or the item is worth zero here.

    A prerequisite is either an ITEM (read that first) or an IDEA (hold that
    first). Both belong in `requires`, and the second is the more useful one: a
    paper auditing whether the model helps needs the reader to know what the
    model is, and which particular paper taught them that does not matter.

    Checking only item ids made every idea prerequisite permanently unsatisfiable,
    since `done` holds ids. The path silently halved and nothing said so.
    """
    cov = cov or {}
    return all(r in done or cov.get(r, 0.0) >= IDEA_MET for r in item.requires)


# The reader's constraint is over COUNT, not over hours: "if I read M of them,
# those M should be the best M". Dividing by cost answers a different question,
# "what are the best M hours", and the two disagree badly. A half-hour GitHub
# thread scored 2.35 against Ha & Schmidhuber's 0.69 and took position two on a
# path about world models, which is indefensible and is what this default fixes.
#
# Cost has not gone away. It bounds the path through `budget_hours`, it is
# displayed on every row, and it breaks ties. It is no longer the ruler.
BY_VALUE, BY_RATE = "value", "rate"


def _value(item: Item, gain: float) -> float:
    """What this item is worth, damped by whether it rewards slow reading.

    depth_payoff multiplies rather than adds, because a high-coverage item that
    teaches nothing in depth is the survey this skill exists to keep off position
    one, and an additive term lets coverage outvote it.
    """
    return gain * (0.4 + 0.6 * item.depth_payoff)


def _rate(item: Item, gain: float, rule: str = BY_VALUE) -> float:
    if rule == BY_RATE:
        return _value(item, gain) / max(item.cost_hours, MIN_COST)
    # Cost as a gentle tiebreak only: a fourth-root, so a 40-hour project is
    # discounted against a 3-hour paper of equal value without a 30-minute
    # artifact ever outranking a foundational text.
    return _value(item, gain) / max(item.cost_hours, MIN_COST) ** 0.25


def greedy(items, *, prior: dict[str, float] | None = None,
           weights: dict[str, float] | None = None,
           budget_hours: float | None = None,
           limit: int | None = None,
           seed: str | None = None,
           rule: str = BY_VALUE) -> list[Pick]:
    """Take the best remaining item at each step, recompute, repeat."""
    pool = {it.id: it for it in items}
    cov = dict(prior or {})
    done: set[str] = set()
    picks: list[Pick] = []
    spent = 0.0

    while pool:
        if limit is not None and len(picks) >= limit:
            break
        scored = []
        for it in pool.values():
            if not available(it, done, cov):
                continue
            if budget_hours is not None and spent + it.cost_hours > budget_hours:
                continue
            gain, landed = marginal(it, cov, weights, done)
            scored.append((_rate(it, gain, rule), gain, landed, it))
        if not scored:
            break

        # A prerequisite worth nothing on its own blocks everything behind it.
        # `base` covers what an earlier pick already covered, so its marginal is
        # zero and greedy refuses it; the project that requires it is gated and
        # never appears, and nothing says so. An item is worth what it unlocks,
        # so a zero-gain item that is the only thing standing between the path
        # and a positive-gain item takes that item's rate.
        blocked = [it for it in pool.values()
                   if not available(it, done, cov)
                   and all(r in pool or r in done or r in cov for r in it.requires)]
        if blocked:
            unlock: dict[str, float] = {}
            for it in blocked:
                g, _ = marginal(it, cov, weights, done | set(it.requires))
                if g <= 0:
                    continue
                r = _rate(it, g, rule)
                for req in it.requires:
                    if req not in done:
                        unlock[req] = max(unlock.get(req, 0.0), r)
            if unlock:
                by_id = {s[3].id: n for n, s in enumerate(scored)}
                for req, r in unlock.items():
                    if req in by_id and scored[by_id[req]][0] < r:
                        _, g, landed, it = scored[by_id[req]]
                        scored[by_id[req]] = (r, max(g, 1e-9), landed, it)

        seeded_now = bool(seed) and not picks and seed in pool
        if seeded_now:
            chosen = next(s for s in scored if s[3].id == seed)
        else:
            # Ties broken by raw gain then by id, so the order is reproducible.
            chosen = max(scored, key=lambda s: (s[0], s[1], s[3].id))
        rate, gain, landed, it = chosen
        if gain <= 0 and picks:
            break

        others = sorted((s for s in scored if s[3].id != it.id),
                        key=lambda s: -s[0])[:3]
        picks.append(Pick(
            item=it, position=len(picks) + 1, marginal=round(gain, 4),
            rate=round(rate, 4), newly_covered=landed,
            conditioning="", seeded=seeded_now,
            runners_up=[(o[3].id, round(o[0], 4)) for o in others]))
        cov = coverage([it], cov)
        done.add(it.id)
        spent += it.cost_hours
        pool.pop(it.id)

    return _prune(_recompute(_place_disputes(picks), prior, weights), prior, weights)


def _prune(picks, prior=None, weights=None, _depth: int = 0):
    """Drop anything that adds nothing once the final order is fixed.

    Reordering can strand an item. On the world models run, a paper was picked
    while the generative/non-generative fork was still uncovered, then the two
    position papers moved ahead of it and covered the fork as a pair, leaving it
    on the path contributing exactly zero. An entry that teaches the reader
    nothing they do not already have from earlier entries is worse than absent:
    it spends an evening and it makes the ordering look arbitrary.

    Position one is never pruned, because the seed is chosen for what its path
    unlocks rather than for its own marginal value.
    """
    # Never prune something a later pick depends on. An item selected only
    # because it unlocks a project has near-zero marginal by construction, and
    # dropping it leaves the project on the path with its prerequisite missing.
    needed = set()
    for p in picks:
        needed.update(p.item.requires)
        needed.update(p.item.reuses)
    keep = [p for n, p in enumerate(picks)
            if n == 0 or p.marginal > 1e-9 or p.item.id in needed]
    if len(keep) == len(picks) or _depth > 8:
        return keep
    return _prune(_recompute(keep, prior, weights), prior, weights, _depth + 1)


def _recompute(picks, prior=None, weights=None) -> list[Pick]:
    """Refresh marginal, rate and newly_covered against the FINAL order.

    _place_disputes reorders after the greedy, so anything computed during
    selection describes an order that no longer exists. On the world models run
    that showed up as an entry at position 13 claiming to newly cover an idea that
    positions 4 and 5 had already covered once the pair was moved. The numbers are
    what the page renders and what the conditioning notes are written from, so
    stale ones are wrong in the output rather than merely untidy.
    """
    cov = dict(prior or {})
    done: set[str] = set()
    for n, p in enumerate(picks, 1):
        gain, landed = marginal(p.item, cov, weights, done)
        p.position, p.marginal = n, round(gain, 4)
        p.rate, p.newly_covered = round(_rate(p.item, gain), 4), landed
        cov = coverage([p.item], cov) if not p.item.pair_covers else coverage(
            [q.item for q in picks[:n]], prior)
        done.add(p.item.id)
    return picks


def _place_disputes(picks: list[Pick]) -> list[Pick]:
    """Pull the other side of an argument next to the side that got picked.

    Coverage alone will not do this. The idea "the field disagrees about X" is
    only covered once the second one lands, so each on its own looks ordinary.
    Moving it is cheaper and more honest than special-casing the value function.
    """
    by_id = {p.item.id: p for p in picks}
    order = [p.item.id for p in picks]
    for p in list(picks):
        for other in p.item.disputes:
            if other not in by_id:
                continue
            i, j = order.index(p.item.id), order.index(other)
            if j > i + 1:
                order.insert(i + 1, order.pop(j))
                by_id[other].moved_for = p.item.id
    return [by_id[pid] for pid in order]


def lookahead_seed(items, *, candidates, depth: int = 5, foundational=None,
                   **kw) -> str | None:
    """Position one decides what everything after it can be read as.

    Greedy would take the highest-coverage item, which is usually a survey or the
    canon, and both are bad openings for someone who wants to get lost in
    something. So simulate a short path from each candidate seed and keep the one
    whose path is worth most, rather than the one that is worth most alone.
    """
    # Candidates are filtered before they are simulated, not graded afterwards.
    # A seed that cannot stand alone is not a seed however good its path is, and
    # checking that only at the end left the run free to pick one and then fail.
    by = {i.id: i for i in items}
    if foundational:
        ok = []
        for cid in candidates:
            it = by.get(cid)
            if not it:
                continue
            probe = [Pick(item=it, position=1, marginal=1.0, rate=1.0,
                          newly_covered=[], conditioning="", seeded=True)]
            if not check_seed_stands_alone(probe, foundational):
                ok.append(cid)
        candidates = ok or candidates   # never return nothing; say so upstream

    best, best_score = None, -1.0
    for cid in candidates:
        path = greedy(items, seed=cid, limit=depth, **kw)
        if not path:
            continue
        score = total(coverage([p.item for p in path], kw.get("prior")))
        score /= max(sum(p.item.cost_hours for p in path), MIN_COST)
        if score > best_score:
            best, best_score = cid, score
    return best


# ------------------------------------------------------------ subgroups


def _all_ideas(item: Item) -> dict[str, float]:
    """Everything an item speaks to, including what it covers only as a pair.

    A disagreement covered by two papers together is still an idea those papers
    own, and leaving pair coverage out of the routing left a THIRD position in a
    two-sided argument with nowhere to go. Three positions is a better subgroup
    than two, and it is exactly the depth this dimension exists to show.
    """
    out = dict(item.covers)
    for idea, (_, w) in item.pair_covers.items():
        out[idea] = max(out.get(idea, 0.0), w)
    return out


def _dominant(item: Item, spine_ideas: dict[str, str]) -> str | None:
    """Which spine item's idea this candidate mostly speaks to."""
    best, best_w = None, 0.0
    for idea, w in _all_ideas(item).items():
        if idea in spine_ideas and w > best_w:
            best, best_w = idea, w
    return best if best_w >= 0.35 else None


def _variant_gain(item: Item, idea: str, seen: set[str]) -> float:
    """A sub-item is worth what its APPROACH adds, not what its coverage adds.

    Coverage is the wrong ruler down here. Every candidate in a subgroup covers
    the parent's idea, which is why it is in the subgroup, so measured on coverage
    they are all worth nothing. What differs is the mechanism, and reading two
    papers that attack one problem two ways is the entire point of going deep.
    """
    v = item.variants.get(idea)
    if not v or v in seen:
        return 0.0
    return 1.0


def subgroup_for(parent: Pick, pool, *, weights=None, prior=None,
                 limit: int = 4, already: set | None = None,
                 cov: dict | None = None) -> Subgroup | None:
    """Rank the approaches under one spine item. Same guarantee, one level down.

    Read k of these and they are approximately the best k approaches to this
    idea, for the same reason the spine works: greedy on a diminishing-returns
    objective is good at every prefix at once. Here the objective counts distinct
    mechanisms rather than distinct ideas.
    """
    # Build the group around whichever of the parent's ideas actually has
    # companions, weighted toward the one it opened. Using only the top-weighted
    # idea left an entry with obvious companions holding an empty group, because
    # its companions clustered on its second idea rather than its first.
    already = already or set()
    order = [(parent.item.covers.get(i, 0.0) + 1.0, i)     # opened ideas first
             for i in (parent.newly_covered or [])]
    order += [(w, i) for i, w in _all_ideas(parent.item).items()]
    best = None
    for _, idea in sorted(order, reverse=True):
        # An item whose own prerequisites sit later on the spine cannot go in a
        # subgroup here: the number is a route, and 10.2 must be reachable after
        # 10. A project requiring something at position 25 landed at 10.2 before
        # this guard, and check_prerequisites could not see it because it only
        # walked the spine.
        # `available`, not a set difference against item ids. A candidate whose
        # prerequisite is an IDEA was excluded outright, which is the same bug the
        # spine had, one level down: it dropped the model-helps dispute entirely.
        cands = [c for c in pool
                 if available(c, already, cov or {})
                 and _all_ideas(c).get(idea, 0.0) >= 0.3
                 and c.variants.get(idea)
                 and c.variants.get(idea) != parent.item.variants.get(idea)]
        if cands and (best is None or len(cands) > len(best[1])):
            best = (idea, cands)
    if not best:
        return None
    idea, cands = best

    seen = {parent.item.variants.get(idea)} - {None}
    picks, spent = [], 0.0
    while cands and len(picks) < limit:
        scored = []
        for c in cands:
            g = _variant_gain(c, idea, seen)
            if g <= 0:
                continue
            scored.append((_rate(c, g), g, c))
        if not scored:
            break
        rate, gain, c = max(scored, key=lambda s: (s[0], s[1], s[2].id))
        picks.append(Pick(item=c, position=len(picks) + 1, marginal=round(gain, 4),
                          rate=round(rate, 4),
                          newly_covered=[c.variants.get(idea, "")],
                          conditioning="",
                          number=f"{parent.number}.{len(picks) + 1}"))
        seen.add(c.variants.get(idea))
        cands.remove(c)
        spent += c.cost_hours
    if not picks:
        return None
    return Subgroup(parent=parent.item.id, idea=idea,
                    label=parent.item.variants.get(idea, ""), picks=picks)


def split_spine(picks, *, min_open: float = 0.0, items=None, prior=None):
    """The spine opens ideas. Everything else is depth.

    Without this the path is flat and long: an item with a positive marginal but
    no NEW idea sits on the spine at position 15 looking like the fifteenth thing
    you must read, when it is really a second approach to something at position 3.
    A field has a handful of genuinely different ideas and several approaches to
    each, and only the first dimension was ever shown.

    Four things are never demoted, and all four are failures I caused by demoting
    them: the other side of a dispute pair, which has to stay adjacent to the side
    that got picked; anything a later item `requires`; anything a later project
    `reuses`, because that is a sequence rather than a set; and the only item that
    covers some idea, which would otherwise leave the idea uncovered at any
    budget with nothing saying so.

    Returns (spine, demoted). Position one is always spine: the seed is chosen for
    what its path unlocks, not for its own marginal.
    """
    ids = [p.item.id for p in picks]
    needed = set()
    for p in picks:
        needed.update(p.item.requires)
        needed.update(p.item.reuses)
        for d in p.item.disputes:
            if d in ids:
                needed.add(d)
    if items:
        cov = coverage([p.item for p in picks], prior)
        who = {}
        for it in items:
            for idea, w in it.covers.items():
                if w >= 0.5:
                    who.setdefault(idea, []).append(it.id)
        for idea, cs in who.items():
            if len(cs) == 1 and cov.get(idea, 0.0) >= 0.5:
                needed.add(cs[0])

    spine, demoted = [], []
    for n, p in enumerate(picks):
        opens = bool(p.newly_covered) and p.marginal > min_open
        keep = n == 0 or opens or p.item.id in needed
        (spine if keep else demoted).append(p)
    return spine, demoted


def attach_subgroups(picks, items, *, weights=None, prior=None, limit: int = 4,
                     min_open: float = 0.0):
    """Route everything the spine did not take into the group it belongs under.

    The dropped candidates are not rejects. `_prune` and the greedy discard an
    item precisely when something already on the path covers what it covers, and
    that is the definition of another approach to the same idea. Throwing them
    away threw away the depth dimension.
    """
    original = list(picks)
    spine, demoted = split_spine(picks, min_open=min_open, items=items, prior=prior)
    on = {p.item.id for p in spine}
    # Demoted picks go back in the pool: they were selected, so they are good,
    # they just belong underneath something rather than beside it.
    pool = [i for i in items if i.id not in on]
    picks = spine
    spine_ideas = {}
    for p in picks:
        for idea in (p.newly_covered or list(p.item.covers)):
            spine_ideas.setdefault(idea, p.item.id)
    for n, p in enumerate(picks, 1):
        p.number = str(n)
    for p in picks:
        mine = [c for c in pool if spine_ideas.get(_dominant(c, spine_ideas) or "") == p.item.id]
        seen_ids = set()
        for q in picks:
            if q is p:
                break
            seen_ids.add(q.item.id)
            if q.sub:
                seen_ids.update(c.item.id for c in q.sub.picks)
        upto = coverage([q.item for q in picks[:picks.index(p) + 1]], prior)
        sg = subgroup_for(p, mine, weights=weights, prior=prior, limit=limit,
                          already=seen_ids | {p.item.id}, cov=upto)
        if sg:
            p.sub = sg
            for c in sg.picks:
                pool.remove(c.item)

    # An item demoted off the spine that no subgroup then took has vanished. It
    # was good enough for the greedy to select and it is now in neither place,
    # which is the silent drop this skill keeps warning about, committed by the
    # skill itself. Demote only where there is somewhere to demote TO: put the
    # rest back where they were.
    homed = _placed(picks)
    orphans = [d for d in demoted if d.item.id not in homed]
    if orphans:
        by_id = {d.item.id: d for d in orphans}
        merged, seen = [], set()
        for p in original:
            if p.item.id in {q.item.id for q in picks}:
                merged.append(next(q for q in picks if q.item.id == p.item.id))
            elif p.item.id in by_id and p.item.id not in seen:
                merged.append(by_id[p.item.id])
            seen.add(p.item.id)
        picks = merged
        for n, q in enumerate(picks, 1):
            q.number = str(n)
        # A reinstated item never had a chance to collect a subgroup: the loop
        # above ran over the spine, and it was not on the spine at the time. Give
        # the ones that came back their pass, or a candidate whose only home was
        # under a reinstated parent disappears from the run entirely.
        homed = _placed(picks)
        left = [c for c in pool if c.id not in homed]
        for q in picks:
            if q.sub or q.item.id not in by_id:
                continue
            mine = [c for c in left
                    if spine_ideas.get(_dominant(c, spine_ideas) or "") == q.item.id
                    or (_dominant(c, {i: q.item.id for i in q.item.covers}) is not None
                        and any(i in q.item.covers for i in c.covers))]
            sg = subgroup_for(q, mine, weights=weights, prior=prior, limit=limit,
                              cov=coverage([r.item for r in picks], prior))
            if sg:
                q.sub = sg
                for c in sg.picks:
                    if c.item in left:
                        left.remove(c.item)
        for n, q in enumerate(picks, 1):
            q.number = str(n)
            if q.sub:
                for k, c in enumerate(q.sub.picks, 1):
                    c.number = f"{n}.{k}"
    return picks


# ------------------------------------------------------------------ invariants
# These are the thesis, written as assertions. tests/ calls them, `papers eval`
# calls them, and a run that fails one does not ship.


def check_monotone(picks) -> list[str]:
    """Coverage never decreases as the prefix grows."""
    bad, prev = [], -1.0
    for n in range(1, len(picks) + 1):
        t = total(coverage([p.item for p in picks[:n]]))
        if t < prev - 1e-9:
            bad.append(f"prefix {n} covers {t:.3f}, less than prefix {n-1} at {prev:.3f}")
        prev = t
    return bad


def _placed(picks) -> set:
    """Everything the run placed somewhere, spine or subgroup."""
    out = {p.item.id for p in picks}
    for p in picks:
        if p.sub:
            out.update(c.item.id for c in p.sub.picks)
    return out


def check_prefix_optimal(picks, items, *, prior=None, weights=None,
                        rule: str = BY_VALUE) -> list[str]:
    """The thesis, made checkable.

    For every prefix length M, swapping the item at position M for any item that
    was available and not yet used must not improve coverage-per-hour at M. This
    is local optimality, which is what greedy actually guarantees. Global
    optimality is not claimed, so it is not asserted.

    Positions that `_place_disputes` moved are exempt, because that move is a
    deliberate override of the arithmetic: two papers arguing with each other are
    worth more adjacent than eight positions apart, and the greedy cannot see it
    because the disagreement is only covered once the second one lands. The
    exemption is narrow on purpose. A moved position must actually dispute its
    predecessor, or it is reported. Otherwise this check would rubber-stamp any
    reordering that called itself a dispute.
    """
    # Items placed in a subgroup are not unused alternatives to a spine position.
    # They were selected and filed one level down, and counting them here made the
    # check report that a paper sitting at 6.1 should have been at 14.
    placed = _placed(picks)
    pool = {it.id: it for it in items if it.id in {p.item.id for p in picks}
            or it.id not in placed}
    bad = []
    for m in range(1, len(picks) + 1):
        pk = picks[m - 1]
        # Position one is exempt when it was seeded. lookahead_seed deliberately
        # does NOT take the highest-value item: it takes the one whose whole path
        # is worth most, because position one decides what the rest can be read
        # as. Judging it by the greedy rule asks it to be something it is not.
        if m == 1 and pk.seeded:
            continue
        if pk.moved_for:
            prev = picks[m - 2].item.id if m >= 2 else None
            if pk.moved_for != prev or prev not in pk.item.disputes:
                bad.append(f"position {m}: {pk.item.id!r} was moved for "
                           f"{pk.moved_for!r} but does not follow it as a dispute")
            continue
        before = [p.item for p in picks[:m - 1]]
        cov = coverage(before, prior)
        done = {p.item.id for p in picks[:m - 1]}
        used = {p.item.id for p in picks}
        cur = picks[m - 1].item
        cur_gain, cur_landed = marginal(cur, cov, weights, done)
        cur_rate = _rate(cur, cur_gain, rule)
        for it in pool.values():
            if it.id in used or it.id in placed or not available(it, done, cov):
                continue
            gain, landed = marginal(it, cov, weights, done)
            # A spine slot that opened an idea can only be taken by something that
            # would open one too. An alternative that only deepens is what
            # split_spine files underneath as depth, so reporting it here asks the
            # spine to hold what it is built to refuse. Found on a real run: after
            # a paper deepening an idea was demoted to a subgroup, an unplaced paper
            # deepening the same idea was reported as beating positions 10 to 13,
            # and no reordering of the spine could have satisfied the check.
            if cur_landed and not landed:
                continue
            if _rate(it, gain, rule) > cur_rate + 1e-9:
                bad.append(f"position {m}: {it.id!r} rates {_rate(it, gain, rule):.4f} "
                           f"over {cur.id!r} at {cur_rate:.4f}")
    return bad


def check_prerequisites(picks) -> list[str]:
    """Walk the path in the order a reader would follow it, subgroups included.

    An earlier version walked only the spine, so an item filed at 10.2 whose
    prerequisite sat at 25 passed. The number is a route: if it can be followed
    in order, everything it needs has to already be behind it.
    """
    seen, bad, cov = set(), [], {}
    for p in picks:
        for c in [p] + list(p.sub.picks if p.sub else []):
            missing = [r for r in c.item.requires
                       if r not in seen and cov.get(r, 0.0) < IDEA_MET]
            if missing:
                bad.append(f"{c.number or c.position}: {c.item.id!r} requires "
                           f"{missing}, none of which appear earlier")
            seen.add(c.item.id)
            # The reader holds everything above this line, ideas included, so the
            # covered set has to advance with the walk. Without this the checker
            # only ever saw item ids and every idea prerequisite read as unmet.
            cov = coverage([c.item], cov)
    return bad


def check_compounding(picks) -> list[str]:
    """Projects after the first name what they reuse, and it is genuinely earlier.

    plan.md 7 claims a project sequence beats three good projects because the
    artifacts compound. This is that claim turned into something that fails.

    Walks subgroups too: a project filed at 10.2 is still a project, and the
    reader reaches it before the one at 25.
    """
    seen, bad, nth = set(), [], 0
    for top in picks:
        for p in [top] + list(top.sub.picks if top.sub else []):
            n = p.number or p.position
            if p.item.kind == "project":
                nth += 1
                if nth > 1 and not p.item.reuses:
                    bad.append(f"{n}: project {p.item.id!r} reuses nothing from "
                               "earlier, so the sequence is not compounding")
                for r in p.item.reuses:
                    if r not in seen:
                        bad.append(f"{n}: {p.item.id!r} claims to reuse {r!r}, "
                                   "which is not earlier in the path")
            seen.add(p.item.id)
    return bad


def check_unique_coverers(picks, items, *, prior=None, weights=None) -> list[str]:
    """An idea that exactly one candidate covers, which the path left out.

    Greedy by rate is the right rule for value that has substitutes. A unique
    coverer has none: dropping it means the idea is never covered at any budget,
    and the reader is not told. This fires most often on the experiential ideas,
    since a project is usually the only thing that covers one, and the project is
    also the most expensive item on the board. Found by running, not by reading.
    """
    chosen = {p.item.id for p in picks}
    covered = coverage([p.item for p in picks], prior)
    who: dict[str, list[str]] = {}
    for it in items:
        for idea, w in list(it.covers.items()) + [(k, v[1]) for k, v in it.pair_covers.items()]:
            if w >= 0.5:
                who.setdefault(idea, []).append(it.id)
    out = []
    for idea, coverers in who.items():
        if covered.get(idea, 0.0) >= 0.5:
            continue
        if len(coverers) == 1 and coverers[0] not in chosen:
            out.append(f"{idea!r} is covered only by {coverers[0]!r}, which the path left out. "
                       "Either extend the path far enough to reach it or say on the page that "
                       "this stays uncovered.")
    return out


def check_subgroups(picks, items) -> list[str]:
    """The guarantee has to hold inside a subgroup too, or the depth is a pile.

    Three things. Every sub-item names a distinct approach, since two entries
    with the same mechanism is the flat list's redundancy problem wearing a
    disclosure triangle. Numbering runs parent.1, parent.2 in order, because the
    number is meant to be followed. And a sub-item whose dominant idea is not its
    parent's belongs on the spine, not underneath it.
    """
    bad = []
    for p in picks:
        sg = p.sub
        if not sg:
            continue
        seen = set()
        for n, c in enumerate(sg.picks, 1):
            v = c.item.variants.get(sg.idea)
            if not v:
                bad.append(f"{c.number}: {c.item.id!r} names no approach for "
                           f"{sg.idea!r}, so it reads as a duplicate of its parent")
            elif v in seen:
                bad.append(f"{c.number}: approach {v!r} already appears in this group")
            seen.add(v)
            if c.number != f"{p.number}.{n}":
                bad.append(f"expected {p.number}.{n}, got {c.number}")
            if sg.idea not in _all_ideas(c.item):
                bad.append(f"{c.number}: does not cover its parent's idea, so it is "
                           "breadth filed as depth")
    return bad


def check_seed_stands_alone(picks, ideas: dict | None = None) -> list[str]:
    """If someone reads exactly one thing, it has to be a thing worth reading alone.

    The failure this exists to stop, in full: a run about world models opened with
    a 2023 analysis of MuZero's learned model and followed it with a GitHub thread
    about a library version. Both are good artifacts and neither answers "what is
    a world model", so a reader who stopped at one or two came away with nothing.

    Two conditions on position one. It needs no prerequisites, since anything you
    must read first is by definition a better position one. And it covers at least
    one idea marked foundational, meaning the field is not legible without it.
    """
    if not picks:
        return ["the path is empty"]
    ideas = ideas or {}
    p = picks[0]
    bad = []
    if p.item.requires:
        bad.append(f"position one {p.item.id!r} requires {p.item.requires}, so one of "
                   "those is the better position one")
    found = {k for k, v in ideas.items() if v}
    if found:
        hit = found & set(_all_ideas(p.item))
        if not hit:
            bad.append(f"position one {p.item.id!r} covers no foundational idea "
                       f"({', '.join(sorted(found))}), so a reader who stops here "
                       "learns something true about a corner of the field and "
                       "nothing about the field")
    if p.item.kind != "paper":
        bad.append(f"position one is a {p.item.kind}, and the reader asked for the "
                   "best M papers")
    return bad


def check_display_fields(picks) -> list[str]:
    """Year and phrase on every entry, at every depth.

    Both are how a reader decides whether to open something without opening it,
    and a row missing either forces them to click to find out what it is, which
    is the deliberation this whole skill exists to remove.
    """
    bad = []
    for p in picks:
        for c in [p] + list(p.sub.picks if p.sub else []):
            if c.item.kind == "paper" and not c.item.year:
                bad.append(f"{c.number}: no year")
            if not c.item.phrase:
                bad.append(f"{c.number}: no phrase")
            elif len(c.item.phrase.split()) > 14:
                bad.append(f"{c.number}: phrase is {len(c.item.phrase.split())} words, "
                           "which is a sentence rather than a glance")
    return bad


def check_all(picks, items, foundational: dict | None = None, **kw) -> dict[str, list[str]]:
    return {
        "monotone": check_monotone(picks),
        "prefix_optimal": check_prefix_optimal(picks, items, **kw),
        "prerequisites": check_prerequisites(picks),
        "compounding": check_compounding(picks),
        "unique_coverers": check_unique_coverers(picks, items, **kw),
        "subgroups": check_subgroups(picks, items),
        "seed_stands_alone": check_seed_stands_alone(picks, foundational),
        "display_fields": check_display_fields(picks),
    }


def to_json(picks) -> str:
    return json.dumps([{
        "position": p.position, "id": p.item.id, "kind": p.item.kind,
        "title": p.item.title, "cost_hours": p.item.cost_hours,
        "marginal": p.marginal, "rate": p.rate, "newly_covered": p.newly_covered,
        "conditioning": p.conditioning, "runners_up": p.runners_up,
        "group": p.item.group, "role": p.item.role,
    } for p in picks], indent=2)

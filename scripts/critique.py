"""Grade a finished run against the skill's own stated bar. Run it before shipping.

The unit tests check the ordering arithmetic. Nothing checked whether the OUTPUT
was any good, and that is where the first test run was actually weak: the repo
entry was a bare URL, two group theses were placeholders, and I only noticed
because I had written down what to look for and then looked. That is not a
harness, that is remembering.

So every rule the references state as a requirement becomes a check here, and a
run that fails one does not ship. The checks are deterministic wherever the rule
is mechanical. Where a rule is genuinely a reading problem the check reports what
a human should look at rather than pretending to score it, because a rule handed
a bad proxy returns a confident wrong answer instead of an error.

Usage: python3 scripts/critique.py <run-dir>
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

FAIL, WARN, OK, LOOK = "FAIL", "warn", "ok", "look"

# The three defaults voice.md says AI writing collapses into, plus the tells the
# editor pass is told to remove. Counted, not eyeballed.
TELLS = re.compile(
    r"\b(delve|leverag(e|ing)|robust|crucial|pivotal|vital|seamless|underscore|"
    r"showcas(e|ing)|landscape|realm|tapestry|game.chang|paradigm shift|"
    r"deep dive|key takeaway|at the forefront|rapidly evolving|"
    r"it is worth noting|this document|in conclusion)\b", re.I)

HEDGE = re.compile(r"\b(may potentially|could arguably|it seems likely that perhaps|"
                   r"might possibly|somewhat unclear)\b", re.I)

PLACEHOLDER = re.compile(r"\b(placeholder|TODO|TBD|not (?:yet )?(?:written|established|"
                         r"resolved|run)|a full run|coming soon|lorem)\b", re.I)

# "read section 4" is the exact thing annotation.md forbids in layer three.
VAGUE_THINKING = re.compile(r"^\s*(read|see)\s+(section|chapter|part)\s+\d", re.I)

REPO_URL_ONLY = re.compile(r"^\s*(https?://\S+|[\w.-]+/[\w.-]+)\s*\.?\s*$")


@dataclass
class Check:
    rule: str
    status: str
    detail: str = ""
    where: list[str] = field(default_factory=list)
    source: str = ""          # which reference document states this rule


def _c(rule, status, detail="", where=(), source=""):
    return Check(rule, status, detail, list(where), source)


# --------------------------------------------------------------- entry checks


def flatten(entries):
    """Every entry at every depth. Sub-entries are entries: they need a layer
    three, a phrase and a year exactly as much as a spine entry does."""
    out = []
    for e in entries:
        out.append(e)
        out.extend((e.get("subgroup") or {}).get("items") or [])
    return out


def num(e):
    return str(e.get("number") or e.get("position") or "?")


def is_sub(e) -> bool:
    return "." in num(e)


def check_layer_three(entries) -> Check:
    """annotation.md: an entry without layer three has failed.

    This is the reader's stated reason for wanting the skill, so it is the first
    check and the one most worth failing a run over.
    """
    missing, vague = [], []
    for e in entries:
        w = (e.get("where_the_thinking_is") or "").strip()
        if not w:
            missing.append(f"{num(e)} {e.get('id')}")
        elif VAGUE_THINKING.match(w) or PLACEHOLDER.search(w):
            vague.append(f"{num(e)} {e.get('id')}")
    if missing or vague:
        d = []
        if missing:
            d.append(f"{len(missing)} with none")
        if vague:
            d.append(f"{len(vague)} vague or placeholder")
        return _c("every entry says where the thinking is", FAIL,
                  ", ".join(d), missing + vague, "annotation.md")
    return _c("every entry says where the thinking is", OK,
              f"{len(entries)} entries", source="annotation.md")


def check_repo_entries(entries) -> Check:
    """repos.md: an entry that names only a URL has failed.

    The reader can find the URL. What they cannot do cheaply is know which of
    four hundred files to open.
    """
    bad = []
    for e in entries:
        if e.get("kind") != "repo":
            continue
        w = e.get("where_the_thinking_is") or ""
        # A named source or config file, a function, a commit, or an issue or
        # pull-request thread. The thread is deliberate: repos.md calls the
        # "I cannot reproduce table 3" issue the repo's rebuttal and tells the
        # run to link it, so a check that only accepted .py paths was failing an
        # entry the reference asks for. Found by running the grader on a real run.
        has_file = bool(re.search(r"[\w/.-]+\.(py|c|cc|cpp|cu|rs|go|ts|js|h|txt|toml|ya?ml|cfg|json|md)\b", w))
        has_fn = bool(re.search(r"\bdef\s+\w+|\bfn\s+\w+|`\w+\(`|\bclass\s+\w+", w))
        has_commit = bool(re.search(r"\b[0-9a-f]{7,40}\b|\bcommit\b|\bPR\s*#?\d+|#\d{1,6}\b", w))
        has_thread = bool(re.search(r"\b(thread|issue|rebuttal|reply)\b", w, re.I))
        if not (has_file or has_fn or has_commit or has_thread) or REPO_URL_ONLY.match(w):
            bad.append(f"{num(e)} {e.get('id')}")
    if bad:
        return _c("repo entries name a file or a function", FAIL,
                  f"{len(bad)} name neither", bad, "repos.md")
    n = sum(1 for e in entries if e.get("kind") == "repo")
    return _c("repo entries name a file or a function", OK, f"{n} repos", source="repos.md")


def check_conditioning(entries) -> Check:
    """selection.md: a conditioning note that does not reference what came before
    is not conditioning, it is a restatement."""
    bad = []
    for e in entries:
        c = (e.get("conditioning") or "").strip()
        n = num(e)
        # A sub-entry's conditioning is its parent plus the approaches above it,
        # which the subgroup note already states, so only the spine is checked.
        if is_sub(e):
            continue
        if not c:
            bad.append(f"{n} missing")
        elif n not in ("1", "?") and not re.search(
                r"\b(position|one|two|three|four|five|six|seven|earlier|before|"
                r"above|previous|after|first|since|because|now that|gave|left)\b", c, re.I):
            bad.append(f"{n} does not reference what came before")
    if bad:
        return _c("conditioning notes reference the prefix", FAIL,
                  f"{len(bad)} of {len(entries)}", bad, "selection.md")
    return _c("conditioning notes reference the prefix", OK, source="selection.md")


def check_kinds_present(entries) -> Check:
    """plan.md 5.6: one interleaved path, not one track wearing three labels."""
    kinds = {}
    for e in entries:
        kinds[e.get("kind")] = kinds.get(e.get("kind"), 0) + 1
    if len(kinds) == 1:
        return _c("all three kinds represented", FAIL,
                  f"only {list(kinds)[0]}: this is a list, not a path", source="plan.md 5.6")
    if len(kinds) == 2:
        return _c("all three kinds represented", WARN,
                  f"missing {set(('paper','repo','project')) - set(kinds)}; "
                  "say why in the run notes", source="plan.md 5.6")
    return _c("all three kinds represented", OK, str(kinds), source="plan.md 5.6")


def check_interleaved(entries) -> Check:
    """A path where every paper precedes every repo is three lists concatenated."""
    seq = [e.get("kind") for e in entries]
    blocks = [seq[0]] if seq else []
    for k in seq[1:]:
        if k != blocks[-1]:
            blocks.append(k)
    if len(set(seq)) > 1 and len(blocks) <= len(set(seq)):
        return _c("the path is interleaved", WARN,
                  f"kinds appear in {len(blocks)} solid blocks: {' '.join(blocks)}. "
                  "That is three lists concatenated, which 5.6 argues against.",
                  source="plan.md 5.6")
    return _c("the path is interleaved", OK, " ".join(seq), source="plan.md 5.6")


# --------------------------------------------------------------- group checks


def check_group_theses(groups) -> Check:
    """groups.md: thesis: none is a real answer. A PLACEHOLDER is not.

    The distinction is the whole point. A group with no through line gets
    `thesis: null` plus a reason about the group. A group nobody looked at also
    gets null, with a reason about the run, and those two are not the same and
    must not read the same.
    """
    placeholders, unsourced = [], []
    for g in groups:
        t = g.get("thesis")
        why = g.get("thesis_none_why") or ""
        if t and PLACEHOLDER.search(str(t)):
            placeholders.append(g.get("slug"))
        elif t and not g.get("thesis_source"):
            unsourced.append(g.get("slug"))
        elif not t and PLACEHOLDER.search(why):
            placeholders.append(f"{g.get('slug')} (nobody looked)")
    out = []
    if placeholders:
        out.append(f"{len(placeholders)} placeholder")
    if unsourced:
        out.append(f"{len(unsourced)} thesis with no source URL")
    if out:
        return _c("group theses are real or honestly null", FAIL,
                  ", ".join(out), placeholders + unsourced, "groups.md")
    n_none = sum(1 for g in groups if not g.get("thesis"))
    return _c("group theses are real or honestly null", OK,
              f"{len(groups)} groups, {n_none} with thesis: none", source="groups.md")


def check_group_links(groups, entries) -> Check:
    """Every entry's group chip resolves to a group node, or the chip is empty."""
    slugs = {g.get("slug") for g in groups}
    dangling = [f"{num(e)} {e.get('group')}" for e in entries
                if e.get("group") and e.get("group") not in slugs]
    if dangling:
        return _c("group chips resolve", FAIL, f"{len(dangling)} dangling",
                  dangling, "groups.md")
    return _c("group chips resolve", OK, source="groups.md")


def check_affiliations_dated(groups) -> Check:
    """sourcing.md: do not guess a current affiliation. People move."""
    bad = [g.get("slug") for g in groups
           if g.get("institution") and not re.search(
               r"\b(20\d{2}|observed|as of|per the|from the|not resolved|unresolved|"
               r"unknown|not read)\b", str(g["institution"]), re.I)]
    if bad:
        return _c("affiliations are dated or attributed", WARN,
                  f"{len(bad)} bare institution strings", bad, "sourcing.md")
    return _c("affiliations are dated or attributed", OK, source="sourcing.md")


# --------------------------------------------------------------- voice checks


def check_voice(text: str, label: str) -> list[Check]:
    words = max(len(text.split()), 1)
    per_k = 1000 / words
    out = []

    dashes = text.count("—") + len(re.findall(r"\s–\s", text))
    out.append(_c(f"{label}: zero em dashes", FAIL if dashes else OK,
                  f"{dashes} found" if dashes else "", source="voice.md"))

    semis = text.count(";") * per_k
    out.append(_c(f"{label}: semicolons under 2 per 1000w",
                  FAIL if semis > 2 else OK, f"{semis:.1f}/1000w", source="voice.md"))

    tells = TELLS.findall(text)
    out.append(_c(f"{label}: no report tells", FAIL if tells else OK,
                  ", ".join(sorted({t[0] if isinstance(t, tuple) else t
                                    for t in tells})[:6]) if tells else "",
                  source="voice.md"))

    hedges = HEDGE.findall(text)
    if hedges:
        out.append(_c(f"{label}: no hedge stacking", FAIL, str(len(hedges)), source="voice.md"))

    # voice.md's binary-contrast ban: "not X, Y" and "isn't just A, it's B".
    binaries = re.findall(r"\b(?:is|are|was|were|it's|its)\s+not\s+\w+[,.]\s+(?:it'?s|they'?re)\b"
                          r"|\bnot\s+just\s+\w+[,.]\s+(?:but|it'?s)\b", text, re.I)
    if binaries:
        out.append(_c(f"{label}: no binary contrasts", WARN, str(len(binaries)),
                      source="voice.md"))
    return out


def check_uniformity(entries) -> Check:
    """voice.md's anti-uniformity rule: relative depth is information.

    If every entry is the same length, the run padded the thin ones, and that
    flattening lies to the reader about which items have more in them.
    """
    lens = [len((e.get("summary") or "") + (e.get("unlocks") or "")) for e in entries]
    if len(lens) < 4:
        return _c("entry length varies with substance", OK, "too few to judge",
                  source="voice.md")
    mean = sum(lens) / len(lens)
    spread = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5 / max(mean, 1)
    if spread < 0.18:
        return _c("entry length varies with substance", WARN,
                  f"coefficient of variation {spread:.2f}: every entry is the same size, "
                  "which usually means the thin ones were padded",
                  source="voice.md")
    return _c("entry length varies with substance", OK, f"cv {spread:.2f}", source="voice.md")


# --------------------------------------------------------------- honesty checks


def check_unverified_not_empty(conf) -> Check:
    """sourcing.md: an empty could-not-verify list means somebody quietly dropped
    what they were unsure about."""
    un = (conf or {}).get("unverified") or []
    if not un:
        return _c("could-not-verify is populated", FAIL,
                  "empty, which means the run hid something", source="sourcing.md")
    return _c("could-not-verify is populated", OK, f"{len(un)} entries", source="sourcing.md")


def check_placeholders(d) -> Check:
    """A placeholder anywhere in shipped output is a lie wearing an apology."""
    hits = []
    for e in d.get("entries", []):
        for k in ("summary", "unlocks", "where_the_thinking_is", "conditioning", "question"):
            if PLACEHOLDER.search(str(e.get(k) or "")):
                hits.append(f"{e.get('position')}.{k}")
    if hits:
        return _c("no placeholders in shipped entries", FAIL, f"{len(hits)}", hits)
    return _c("no placeholders in shipped entries", OK)


def check_anchoring(d, deep_terms) -> Check:
    """The reader's own deep areas leaking into a topic that is not theirs.

    Reported rather than scored, because whether a practitioner of THIS field uses
    that word at that frequency is a reading problem and a threshold would be a
    confident wrong answer.
    """
    text = json.dumps(d).lower()
    hits = {t: text.count(t.lower()) for t in deep_terms if text.count(t.lower()) > 2}
    if hits:
        return _c("anti-anchoring sweep", LOOK,
                  "; ".join(f"{k} x{v}" for k, v in sorted(hits.items(), key=lambda kv: -kv[1])),
                  source="SKILL.md standing rules")
    return _c("anti-anchoring sweep", OK, source="SKILL.md standing rules")


def check_experiential(d) -> Check:
    """plan.md 5.1: if nothing is experiential, the interleaving has no argument."""
    ideas = d.get("ideas") or []
    exp = [i for i in ideas if i.get("experiential")]
    if ideas and not exp:
        return _c("experiential ideas identified", WARN,
                  "none marked, so projects have no claim over papers",
                  source="plan.md 5.1")
    kinds = {e.get("kind") for e in d.get("entries", [])}
    if exp and "project" not in kinds:
        return _c("experiential ideas identified", FAIL,
                  f"{len(exp)} experiential ideas and no project on the path, "
                  "so they stay uncovered", source="plan.md 5.1")
    return _c("experiential ideas identified", OK, f"{len(exp)} of {len(ideas)}",
              source="plan.md 5.1")


# --------------------------------------------------------------- driver


def critique(run_dir: pathlib.Path, deep_terms=()) -> list[Check]:
    d = json.load(open(run_dir / "path.json"))
    entries, groups = d.get("entries", []), d.get("groups", [])
    flat = flatten(entries)
    checks = [
        check_layer_three(flat),
        check_repo_entries(flat),
        check_conditioning(entries),
        check_placeholders(d),
        check_group_theses(groups),
        check_group_links(groups, flat),
        check_affiliations_dated(groups),
        check_kinds_present(entries),
        check_interleaved(entries),
        check_experiential(d),
        check_uniformity(entries),
        check_unverified_not_empty(d.get("confidence")),
        check_anchoring(d, deep_terms),
    ]
    prose = " ".join(str(e.get(k) or "") for e in flat
                     for k in ("summary", "unlocks", "where_the_thinking_is",
                               "conditioning", "question"))
    checks += check_voice(prose, "entries")
    checks += check_voice(" ".join(str(g.get("thesis") or "") + " " +
                                   str(g.get("direction") or "") for g in groups), "groups")
    return checks


def report(checks) -> int:
    order = {FAIL: 0, WARN: 1, LOOK: 2, OK: 3}
    fails = 0
    for c in sorted(checks, key=lambda c: order[c.status]):
        if c.status == OK:
            continue
        fails += c.status == FAIL
        src = f"  [{c.source}]" if c.source else ""
        print(f"{c.status.upper():<5} {c.rule}{src}")
        if c.detail:
            print(f"      {c.detail}")
        for w in c.where[:6]:
            print(f"        - {w}")
        if len(c.where) > 6:
            print(f"        ... and {len(c.where) - 6} more")
    n_ok = sum(1 for c in checks if c.status == OK)
    print(f"\n{n_ok}/{len(checks)} clean, {fails} blocking")
    return fails


if __name__ == "__main__":
    run = pathlib.Path(sys.argv[1]).resolve()
    deep = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    sys.exit(1 if report(critique(run, deep)) else 0)

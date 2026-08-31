"""The last gate: does this read as though a machine wrote it.

`industry-research/references/voice.md` already bans the loud tells, and the
editor pass enforces them. This catches what survives that: the constructions
that are individually defensible and collectively unmistakable.

Two ideas do the work here.

**Titles are measured separately and harder.** A title is six words carrying the
whole first impression, so slop density there costs more than anywhere else. The
shape that gives it away is a real noun phrase followed by a portentous clause
that reframes it: "World models, after the score stops meaning anything." It
sounds like a thesis and states nothing, and no human names a document that way
unless they are performing.

**Everything else is a density budget, not a ban.** "Rather than" is a fine
phrase. Seventeen of them in five thousand words is a tic, and tics are what make
prose read as generated. Every budget below was set by measuring real output from
this skill rather than by taste, and the counts that set them are in the comments.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

FAIL, WARN, OK = "FAIL", "warn", "ok"


@dataclass
class Finding:
    rule: str
    status: str
    detail: str = ""
    hits: list = field(default_factory=list)
    why: str = ""


# --------------------------------------------------------------------- titles

# Each is a shape, not a word. The test is whether a person naming a document for
# a colleague would produce it, and none of these survives that.
TITLE_SHAPES = [
    (r"^[^,:]{4,60},\s+(?:after|before|when|once|and then|now that)\b",
     "noun phrase plus a portentous clause that reframes it",
     "'World models, after the score stops meaning anything'. It sounds like a "
     "thesis and states nothing. This is the single most recognisable AI title."),
    (r"^(?:the\s+)?(?:quiet|strange|curious|surprising|hidden|secret|unreasonable)\s+\w+\s+of\b",
     "'The quiet X of Y'",
     "the Gladwell shape. It promises a revelation and names no subject."),
    (r"^[^:]{4,50}:\s+(?:the|a|an)\s+\w+\s+(?:that|who|which)\b",
     "'X: the Y that Z'",
     "a colon followed by a relative clause doing the work the title should do."),
    (r"^(?:rethinking|reconsidering|revisiting|towards|toward|on the nature of)\b",
     "'Rethinking / Towards X'",
     "fine on a paper, empty on a page. It announces a posture rather than a subject."),
    (r"^when\s+\w+.*\bstops?\b|^what\s+\w+.*\breally\b",
     "'When X stops being Y' / 'What X really means'",
     "a rhetorical setup used as a name."),
    (r"\b(?:is|are|was|were)\s+not\s+what\s+(?:you|we|it)\b",
     "'X is not what you think'",
     "the reveal structure. It withholds instead of naming."),
]

# A title that is a plain noun phrase is almost always right, so the check does
# not ask for cleverness. It asks for a name.
TITLE_MAX_WORDS = 9


def check_title(title: str) -> Finding:
    t = (title or "").strip()
    if not t:
        return Finding("the title names the thing", FAIL, "no title")
    for pat, name, why in TITLE_SHAPES:
        if re.search(pat, t, re.I):
            return Finding("the title names the thing", FAIL, name, [t], why)
    if len(t.split()) > TITLE_MAX_WORDS:
        return Finding("the title names the thing", WARN,
                       f"{len(t.split())} words", [t],
                       "past about nine words a title has become a sentence, and a "
                       "sentence in the title slot is usually a claim the page has "
                       "not earned yet.")
    return Finding("the title names the thing", OK, t)


# ---------------------------------------------------------------------- prose

# (pattern, per-1000-word budget, name, why it reads as machine-written)
# Budgets set by measuring this skill's own output, not by taste. The counts in
# the comments are what a real run produced before the gate existed.
TICS = [
    (r"\brather than\b", 2.0, "'rather than'",
     "measured at 17 per 5300 words in a real run. The phrase is fine; the "
     "frequency is a tic, and tics are most of what makes prose read as generated."),
    (r",\s+and\s+(?:that|this)\s+is\b", 1.0, "', and that is ...'",
     "measured at 9. The appositive reveal: state a fact, then tell the reader "
     "what it means in the same breath. Once is emphasis, nine times is a mannerism."),
    (r"\bis the (?:whole|entire)\b", 1.0, "'is the whole X'",
     "measured at 6. 'That is the whole paper' is a good sentence to write once."),
    (r"\bwhich is (?:exactly|precisely|the whole|the entire)\b", 0.0,
     "'which is exactly'", "intensifying by assertion rather than by evidence."),
    (r"\band (?:that|this) is (?:the point|exactly|precisely|why)\b", 0.0,
     "'and that is the point'", "tells the reader what to conclude instead of "
     "leaving the conclusion to them."),
    (r"\bthe real (?:question|answer|story|reason|finding|problem)\b", 0.0,
     "'the real X'", "implies everything preceding was a decoy."),
    (r"\bit(?:'s| is) worth noting\b|\bnotably\b|\binterestingly\b", 0.0,
     "'it is worth noting'", "if it were not worth noting it would not be there."),
    (r"\bquietly\b", 1.0, "'quietly'",
     "a favourite of this register. 'Quietly productive', 'quietly short'."),
    (r"\bturns out\b", 1.0, "'turns out'", "the small reveal, used as connective tissue."),
    (r"\bhere(?:'s| is) (?:the thing|what|why)\b", 0.0, "'here is the thing'",
     "a rhetorical setup. Make the point."),
    (r"\bin (?:its|their|his|her) own words\b", 1.0, "'in its own words'", "a stock phrase."),
    (r"\bat once\b.{0,40}\band\b.{0,40}\bat once\b", 0.0, "doubled 'at once'", "rhythm padding."),
    (r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,30}\bbut\b", 0.5,
     "'not just X but Y'", "the escalation shape voice.md bans as binary contrast."),
    (r"\bdoing the work\b", 1.0, "'doing the work'",
     "this skill's own house tic. Two per page reads as a verbal signature."),
]

REPEATED_OPENERS = 3   # the same first two words starting N+ sentences


def check_prose(text: str) -> list[Finding]:
    words = max(len(text.split()), 1)
    per_k = 1000.0 / words
    out = []
    for pat, budget, name, why in TICS:
        hits = re.findall(pat, text, re.I)
        rate = len(hits) * per_k
        if not hits:
            continue
        over = rate > budget + 1e-9
        out.append(Finding(f"tic: {name}", FAIL if (over and budget == 0) else
                           (WARN if over else OK),
                           f"{len(hits)} found, {rate:.1f} per 1000 words, "
                           f"budget {budget:g}", [], why))

    # Sentences that all start the same way are the clearest rhythm tell there is.
    starts = [" ".join(s.strip().split()[:2]).lower()
              for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
    counts: dict[str, int] = {}
    for s in starts:
        counts[s] = counts.get(s, 0) + 1
    rep = sorted(((n, s) for s, n in counts.items() if n >= REPEATED_OPENERS), reverse=True)
    out.append(Finding("sentence openers vary", WARN if rep else OK,
                       "; ".join(f"{s!r} starts {n} sentences" for n, s in rep[:4]),
                       [], "real writing does not begin four sentences the same way."))
    return out


def gather(d: dict) -> tuple[str, str]:
    """Title, and every word a reader will actually read."""
    parts = []

    def walk(entries):
        for e in entries:
            for k in ("phrase", "summary", "unlocks", "where_the_thinking_is",
                      "conditioning", "question", "objection"):
                if e.get(k):
                    parts.append(str(e[k]))
            walk((e.get("subgroup") or {}).get("items") or [])
            sg = e.get("subgroup") or {}
            for k in ("label", "note"):
                if sg.get(k):
                    parts.append(str(sg[k]))

    walk(d.get("entries") or [])
    m = d.get("meta") or {}
    for k in ("opening", "degraded"):
        if m.get(k):
            parts.append(re.sub(r"<[^>]+>", " ", str(m[k])))
    for g in d.get("groups") or []:
        for k in ("thesis", "direction", "arguing_against", "thesis_none_why"):
            if g.get(k):
                parts.append(str(g[k]))
    return str(m.get("title") or ""), " ".join(parts)


def deslop(d: dict) -> list[Finding]:
    title, prose = gather(d)
    return [check_title(title)] + check_prose(prose)


def report(findings) -> int:
    order = {FAIL: 0, WARN: 1, OK: 2}
    fails = 0
    for f in sorted(findings, key=lambda f: order[f.status]):
        if f.status == OK:
            continue
        fails += f.status == FAIL
        print(f"{f.status:<5} {f.rule}" + (f": {f.detail}" if f.detail else ""))
        for h in f.hits:
            print(f"        {h}")
        if f.why:
            print(f"        why: {f.why}")
    n_ok = sum(1 for f in findings if f.status == OK)
    print(f"\n{n_ok}/{len(findings)} clean, {fails} blocking")
    return fails


if __name__ == "__main__":
    run = pathlib.Path(sys.argv[1]).resolve()
    p = run / "path.json" if run.is_dir() else run
    sys.exit(1 if report(deslop(json.loads(p.read_text()))) else 0)

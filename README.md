# papers

A Claude Code skill that builds **one ordered path** into a research topic: papers, code and
projects interleaved, numbered so you can just go in order.

The constraint it is built around: if you only get through the first M items, those M should be
approximately the best M you could have picked. Every prefix, not just the whole list.

```
/papers world models
/papers discrete diffusion
/papers ricky chen FAIR
/papers the lab that made lada
```

---

## Why this instead of a reading list

Reading lists fail in a specific way. Eleven papers of equal weight is a list nobody starts, and
the usual ways of ordering one are all wrong:

- **by citations** puts the canon and the benchmarks on top, and the second entry duplicates the
  first
- **chronologically**, because the best paper to open with is rarely the oldest
- **grouped by subtopic**, because the first paper of group two is worse than the second paper of
  group one, and a grouped list gets that wrong at every boundary

What satisfies the constraint is greedy selection against a coverage function with diminishing
returns, which is within a constant factor of optimal at every prefix length at once. That is not
decoration: `scripts/ordering.py` is pure, with no network and no model, so the ordering can be
re-derived from a frozen graph and the property is **tested rather than claimed**.

## What a run gives you

**A numbered path.** Go in order. A project sits at the position where doing it unlocks what
follows, not at the end because it is expensive.

**Two dimensions.** A field has a handful of genuinely different ideas and several approaches to
each. The spine opens ideas; the approaches sit underneath, collapsed. Read k inside a group and
they are approximately the k most *different* approaches, because down there the ruler is the
mechanism rather than the coverage.

**Where the thinking is, on every entry.** Not "read section 4". The equation, the table, the
file, the function, the commit, and a question to hold open while you are in there. An entry
without this is treated as a failure by the grader.

**The lab, on every entry**, expanding into what that group believes, read off the discussion and
limitations sections of their own recent papers rather than their landing page.

**Your reading log as the starting point, not a filter.** It seeds the covered set, so the path
starts where your knowledge stops. On a topic whose canon you have already read, this is most of
the value.

**An honest footer.** What could not be verified, which sources were rate limited, and what a
degraded run therefore does not contain.

## Install

```sh
git clone https://github.com/<you>/papers-skill && cd papers-skill && ./install.sh
```

Then copy `profile.example.md` to `~/.claude/papers/profile.md` and edit it. If you already run
[`industry-research`](https://github.com/), its profile is picked up automatically.

Python 3.11+, standard library only. `GITHUB_TOKEN` is optional and worth setting: unauthenticated
GitHub is sixty requests an hour, which cannot cover a real run.

## How it is built

**Discovery is traversal, not search.** Search finds the topic; the citation graph finds the
lineage. Typed nodes, typed edges, and `add_edge` refuses an edge with no absolute source URL,
because an unsourced relationship is an assertion and assertions do not get put on a reading path.
Every expansion decision is logged with its reason, including the refusals, which is what answers
"why is X not here" without re-running anything.

**Agentic where judgment is needed, deterministic everywhere else.** Resolving a query, judging
whether a paper rewards slow reading, reading an OpenReview thread for the real objection: those
are the model's. Storage, dedup, path counting, the greedy loop, identifier verification and the
page build are scripts with no model in them. Mixing the two produces an ordering nobody can audit.

**Three graders, and they fail builds.**

| | what it catches |
|---|---|
| `doctor.py` | run it before a run: what the run is about to lose silently, with the fix |
| `critique.py` | grades the finished run against the rules `references/` states |
| `checkpage.py` | grades the built page: what looks broken but throws no error |

Each exists because something shipped without it. `checkpage.py` was written after a published page
rendered its headline as a monospace section label, printed raw item ids in its lineage, and was
missing two features the design document promises. None of that errored.

## The test suite

**37 mutations, 0 survive.** `tests/mutate.py` breaks the code in 37 plausible ways and checks
which tests notice. A test that catches no mutation is not testing anything, and a mutation no test
catches is a behaviour nobody guards.

```sh
python3 -m pytest tests -q      # 70 tests, no network, under a second
python3 tests/mutate.py         # the audit
```

The audit is not decoration. It found that several tests passed no matter what the code did,
because their fixtures were too small to reach the branch they claimed to test: nothing was ever
demoted, so every test about demotion passed without running the demotion code. Rewriting those
fixtures then exposed a real bug, where a prerequisite worth nothing on its own blocked its entire
downstream chain and a project silently never appeared.

Tests assert both halves where a check can over-fire. Two of these graders shipped with a
false-positive rate high enough to train a reader to ignore them, and a checker that cries wolf is
worse than no checker.

## Layout

```
SKILL.md              the pipeline, and the standing rules
references/           the rationale. Change the reasoning here before the code
  selection.md          the value function, the judgments, and the two dimensions
  graph.md              node and edge kinds, the lead table, the frontier rules
  repos.md              the five repo archetypes and how each one is read
  projects.md           what builder.md gives, and the ordering it does not
  annotation.md         the three layers, and where-the-thinking-is
  groups.md             what a group node holds, and where to read a thesis off
  sources.md            which API answers which question, and where each one lies
  page.md               why the page is shaped this way. Implementation is code
agents/               subagent prompts, one per stage
scripts/              the deterministic half, plus the three graders
tests/                the suite, and the mutation audit
```

The split between `references/` and `scripts/` is deliberate. Prose cannot specify a UI precisely
enough to reproduce it, so the presentation ships as code and only the data varies. Prose is where
the *reasoning* lives, so that anyone changing the code knows what the decision was protecting.

## Credits

The graph traversal, the evidence discipline and the agentic/deterministic split are ported from
two earlier skills by the same author, `industry-research` and `outbound-sourcing`. The project
specification is `industry-research`'s `builder.md` more or less unchanged; this skill adds an
order to it.

MIT.

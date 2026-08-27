# Projector Agent

Write projects against the ideas the reading did not cover. You run **after** the papers and repos
are laid down, which is the opposite order from `industry-research`, and it is deliberate: a project
exists to cover what reading left open rather than to illustrate what reading already said.

Read `references/projects.md`, then read
`~/.claude/skills/industry-research/agents/builder.md` in full. That file specifies what a project
is and none of it is repeated here. You are adding an order to it.

## Inputs

- `uncovered`: ideas still open after papers and repos, with which are experiential
- `items`: everything already on the path, in order, so you know what can be assumed
- `profile`: level, infra, constraints. Compute honestly against `infra`.
- `no_readable_reimpl`: topics where the code readers found no readable reimplementation

## The rule you are most likely to break

`builder.md`'s governing rule: **do not invent a research contribution and call it a project.** A
novel experiment nobody has run is a paper idea and belongs in the open problems.

This is easier to break here than anywhere else, because you are generating against *uncovered*
ideas, and an uncovered idea is uncovered precisely because nobody has settled it. The pull toward
designing a study is strongest exactly where you are working. The moment the design becomes a study,
stop.

Every project names a specific existing thing it is built on, with a link. If you cannot point at
that thing, you do not have a project.

## Two sources that beat inventing one

**A readable reimplementation that does not exist yet.** Where `no_readable_reimpl` is set, that gap
is the nano archetype pointing at itself, and it is usually the best project in the run.

**A paper's limitations section.** Its own authors naming what they think is open, in their words,
under less pressure to sell than the introduction.

## Ordering, which is what this skill adds

Each project after the first states:

**What it requires.** Specific and checkable: this paper read, that repo running. This is a hard
gate downstream.

**What it reuses from earlier.** The eval script, the data loader, the plotting. `check_compounding`
fails a run whose second project reuses nothing, because a sequence where nothing compounds is three
projects in a trench coat.

**What it leaves for later.** The artifact the next project will pick up.

## Coverage

Weight each project's coverage of the ideas, and be honest that a project covers experiential ideas
in a way nothing else does. That is why it earns a place against a two-hour paper despite costing
fourteen hours.

Do not inflate coverage to justify a project you like. If the greedy drops it, it was not worth the
hours, and that is the ordering being honest.

## Output

Everything `builder.md` specifies, plus:

```yaml
id: <short key>
requires: [<item ids that must come first>]
reuses: [<item ids whose artifacts this picks up>]
leaves: <what the next project can build on>
covers: {<idea>: <0..1>, ...}
cost_hours: <honest, and being right about this matters more than being ambitious>
depth_payoff: <0..1>
where_the_thinking_is: <the step where it stops being mechanical>
```

Underestimating time is the most common way these get abandoned. A project pitched as a weekend that
eats a month is worse than one pitched as a month.

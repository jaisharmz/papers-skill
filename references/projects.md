# Projects

`industry-research/agents/builder.md` already specifies a project properly and none of it is
rewritten here. The three archetypes, the rule that every project builds on something that already
exists, the numbered build steps, `done_when`, `will_break`, the plain sentence, the headline test,
the curriculum-not-menu rule. Read it. This file covers only what it does not have.

## What it does not have

`builder.md` produces three projects at three scales, which is a menu of **time**: pick by the
weekend you have. That is right for its job, since it compares fields and the reader picks one.

This skill needs an **order**. If the reader does M projects, those M should be the best M and the
second should condition on the first. Three items at three scales is not an order.

## What conditions a project on the ones before it

**Prerequisites.** Project two assumes the paper has been read and the base runs. This is the hard
gate from `selection.md` and for projects it does most of the work, because a project's
prerequisites are specific and checkable rather than vibes about background.

**Coverage, including the experiential ideas.** A project covers ideas that reading cannot. It also
covers ordinary ones, so a project done early can make a paper redundant, and the greedy will show
that by dropping the paper. Do not fight it: that is the ordering being honest.

**Compounding artifacts.** Project two reuses project one's eval script, its data loader, its
plotting. State it explicitly: what this reuses from earlier and what it leaves for later. A
sequence where nothing compounds is three projects in a trench coat, and `check_compounding` fails
a run whose second project reuses nothing.

## The judgment

**Does it end in a sentence with a number that did not exist before?** `builder.md`'s headline test,
and it stays the bar. Here it also decides ordering, because a project ending in a number can be
checked, and a checked project is a prerequisite the next one can rely on.

*Mechanical version:* estimated hours, or covering all three archetypes. Both produce a set that
looks balanced and teaches one thing three times, which is the failure `builder.md` names.

## Where projects come from

**Generated against the ideas still uncovered after the papers and repos are laid down.** This is
the opposite order from `industry-research`, where projects come out of an avenue. Doing it last
means a project exists to cover what reading left open rather than to illustrate what reading
already said.

Two sources fall directly out of the graph and both beat inventing one:

**A readable reimplementation that does not exist yet.** `repos.md` looks for one and reports the
gap when there is none. That gap is the nano archetype pointing at itself.

**A paper's limitations section.** Its own authors naming the ideas they think are open, in their
own words, under less pressure to sell than the introduction.

## The rule that is easiest to break

`builder.md`'s governing rule: do not invent a research contribution and call it a project. A novel
experiment nobody has run is a paper idea. The moment the design becomes a study, stop, and put it
in the open problems instead.

This is easier to break here than in `industry-research`, because projects are being written
against *uncovered ideas*, and an uncovered idea is uncovered precisely because nobody has settled
it. The pull toward designing a study is strongest exactly where this skill generates from.

# Annotation

`industry-research/references/voice.md` governs everything written here. Zero em dashes, no stacked
hyphenated modifiers, no bullet list where every bullet is "**Thing**: sentence."

`builder.md` already specifies two layers per reading entry. This file adds the third, which is the
one the whole skill exists for.

## Three layers, and they must not blur

**One: what it is and why the field cares.** One or two sentences, objective, the version you would
give anyone who asked. What it did, what it found, why it gets cited. A reader scanning needs this
before a recommendation means anything, and without it every entry reads as an assertion that they
should trust you.

**Two: what it unlocks for this reader.** Not what it contains. What reading it lets them do next.
"After this you can read the 2026 papers in this cluster without looking anything up" is useful.
"This paper introduces a framework for X" belongs in layer one.

**Three: where the thinking is.** The new one.

## Layer three

Not "read section 4." The specific place the idea actually lives, and the question to hold open
while in there.

For a paper: the equation, the table, the figure.

> Equations 7 through 12 are the paper and the rest is packaging. The question to keep open is why
> the variance term survives the limit.

For a repo: the file, the function, and where possible the commit.

> `model/sampler.py`, the eighty lines under `def step`. The commit that introduced it is `a3f21c9`
> and its message says more than the paper does.

For a project: the step where it stops being mechanical.

> Steps 1 through 3 are setup. Step 4 is where you find out whether the normalization statistic was
> the whole result.

**An entry without layer three has failed.** It is the difference between a list that says what to
read and one that says what to think about while reading it, and it is the reader's stated reason
for wanting this skill at all.

The question is not decoration. It should be something the item does not fully answer, so that
reading it leaves the reader somewhere rather than finished.

## The conditioning note

Separate from the three layers and shorter. One line on why this sits at position k given 1 through
k-1. `runners_up` on each pick holds what nearly won, and "this beat X because" is usually the true
sentence.

## Per-entry facts

From `builder.md`, unchanged: venue with acceptance status, group and the senior author whose name
carries weight, time estimate, and role or archetype chip.

**Citations need care or they mislead in both directions.** State the source and the date read. For
anything published in the last six months write **"too new to cite"** rather than a raw count. A
four-month-old paper with three citations and a four-year-old paper with three citations are
opposite findings.

**Where a paper ships code, link the repo beside it** and show stars when notable. A famous paper
with an abandoned repository is worth seeing at a glance, and that gap is often exactly what makes
a reimplementation worth building.

## What not to write

Never an abstract summary. The reader can read the abstract.

Where a paper is famous but not worth reading in full, say which section to read. Where it is wrong
but influential, say so and say what people took from it anyway. Those judgments are the whole value
of an annotated list.

Good: "The method is straightforward and you can skip section 4. Read it for the failure analysis in
table 3, which is the only honest accounting of where this breaks that anyone has published."

Bad: "This paper introduces a novel framework for X and demonstrates strong results on Y."

## Length follows substance

The anti-uniformity rule from `voice.md` applies per entry. An item with a real argument inside it
runs long. An item that is one number gets two sentences saying so. Padding the thin ones to match
destroys the comparison the reader is making, and relative depth is information.

# Selection

The reader's constraint, restated: given N items in order, they will get through M, and those M
must be approximately the best subset of size M. Every prefix, not just the whole list.

`scripts/ordering.py` implements this and its invariant checks are the thesis written as assertions.
This file is the rationale. Change the reasoning here before changing the arithmetic there.

## Why greedy

Greedy on a monotone submodular objective is within a constant factor of optimal at every prefix
length simultaneously. That is precisely the guarantee asked for, and it is the only common
selection rule that has it. Global optimality is not claimed and is not checkable.

Three consequences follow and all three are visible in the output.

**Conditioning.** Value is recomputed after every pick. An item at position two before the first
pick can fall to nine after it, because the first covered most of what made it valuable. That drop
is the conditioning, and a static ranking cannot produce it.

**Cost.** Items have different costs, so the rule is marginal value per hour. That is what makes
"read three papers" and "do one project" a decision the reader can actually take. `depth_payoff`
multiplies rather than adds, because an item with broad shallow coverage would otherwise outvote a
narrow deep one and position one would always be a survey.

**Prerequisites are a gate, not a score.** An item needing an idea the reader does not hold is
worth zero here, however good it is, and becomes available the moment its prerequisites land.

## The idea nodes

Value comes from covering ideas, not from the items themselves. An idea is one thing a person who
understands this topic knows:

- the objective this subfield optimizes, and why that one
- the failure mode every method is working around
- the trick that made the current generation work
- the benchmark, and what it fails to measure
- the live disagreement about whether the framing is right
- the result that did not replicate

Twelve to twenty-five for a topic. Fewer than eight means the topic was read too narrowly. More
than thirty means the ideas are really sub-ideas and the coverage weights will be meaningless.

**Mark the experiential ones.** Some knowledge is not readable. The failure mode is a paragraph in
a paper and a fact in your hands, and those are different objects. An experiential idea is covered
at most weakly by any paper or repo, and fully only by building something. Getting these right is
what makes the interleaved path better than three lists, so do not mark everything experiential and
do not mark nothing.

## The four judgments

Each is listed with what its mechanical version gets wrong, because a reading problem handed to a
rule returns a confident wrong answer rather than an error.

### Does this reward slow reading?

The thesis. A derivation you can follow line by line, an ablation that admits something, a figure
showing the method failing, a core path you can hold in your head. A paper that is one number and a
table is worth eleven minutes and does not belong on a list meant for getting lost.

*Mechanical version:* page count, lines of code, citations per year. All three rank a well-cited
benchmark above a short dense theory paper, which inverts exactly what was asked for.

### Can it be taken on here, given what came before?

A hard gate. For projects it does most of the work, since a project's prerequisites are specific
and checkable rather than vibes about background.

*Mechanical version:* citation depth or publication date. Neither knows that flow matching is
readable without DDPM if you come at it from the ODE side.

### What kind of thing is it?

The six paper roles from `industry-research/agents/builder.md`, unchanged: seminal,
foundation-release, benchmark, result, position, survey. The five repo archetypes in `repos.md`.
The three project archetypes from `builder.md`, unchanged.

*Mechanical version:* citation count, or stars. A benchmark collects a citation from everyone who
ran it and looks seminal. A research dump collects stars from its paper and looks maintained.

### Whose is it, and what do they think?

`groups.md`.

*Mechanical version:* the affiliation string on the paper. It goes stale, and OpenAlex conflates
distinct people into one author record, per the docstring in `scripts/openalex.py`.

## Position one is chosen by lookahead

It decides what everything after it can be read as, so it is not a greedy choice. Greedy takes the
highest-rate item, which is usually a survey or the canon, and both are bad openings for someone
who wants to get lost.

Nominate three or four seeds and simulate five deep from each, then keep the seed whose *path* is
worth most rather than the item worth most alone. `lookahead_seed` does this and
`tests/test_selection.py::test_lookahead_rejects_the_survey` is the regression.

## Two adjustments after the greedy

**Dispute pairs land adjacent.** Two items that contradict each other are worth more back to back
than eight positions apart. Coverage will not do this on its own, because the idea "the field
disagrees about X" is only covered once the second one lands, so each looks ordinary alone.

The move is a deliberate override of the arithmetic, so it is narrow: a moved position must
actually dispute its predecessor, and `check_prefix_optimal` reports it if not. Otherwise the
exemption would rubber-stamp any reordering that called itself a dispute.

**Person queries reorder by arc.** For a person the value is watching one line of thinking develop,
dead ends included. Coverage still prunes and the `supersedes` chain orders.

## Two dimensions, not one

A field has a handful of genuinely different ideas and several approaches to each. The flat path
only ever showed the first dimension, which made a second approach to idea three look like the
fifteenth thing you have to read.

**The spine opens ideas. Subgroups deepen them.** An item joins the spine when it opens an idea
nothing before it covered. An item with positive value that opens nothing is not a reject, it is
another approach to something already on the spine, and it belongs underneath that item.

**The guarantee applies at both levels.** Read M of the spine and you have approximately the best
M for seeing the breadth of the field. Read k inside a subgroup and you have approximately the k
most different approaches to that one idea. Same greedy, same diminishing returns, different
ruler.

**The ruler inside a group is the approach, not the coverage.** Every candidate in a subgroup
covers the parent's idea, which is why it is in the subgroup, so measured on coverage they are all
worth nothing and the ordering would be arbitrary. What differs is the mechanism. Each item
carries a `variants` entry naming its approach to that idea, and the subgroup greedy maximises
distinct mechanisms. Two entries with the same mechanism is the flat list's redundancy problem
wearing a disclosure triangle.

**Four things are never demoted**, and every one of them is a failure caused by demoting it. The
other side of a dispute pair, which has to stay adjacent to the side that got picked. Anything a
later item requires. Anything a later project reuses, since that is a sequence rather than a set.
And the only item covering some idea, which would otherwise leave the idea uncovered at any budget
with nothing saying so.

**Demote only where there is somewhere to demote to.** An item pushed off the spine that no
subgroup then takes has vanished from both places, which is the silent drop this skill keeps
warning about, committed by the skill itself. Put those back.

## The number is a route

Spine items are 1, 2, 3. Approaches under item 3 are 3.1, 3.2. The reader goes in order, and the
ordering is built so that going in order is right: a project sits at the position where doing it
unlocks what follows, not at the end because it is expensive.

## The phrase and the year

Every entry carries a phrase under a sentence and, for anything published, a year. Both exist so a
reader can decide whether to open something without opening it. A row missing either puts back the
deliberation this whole skill exists to remove, so both are checked rather than encouraged.

A phrase is what the thing IS, not what it is called. "multi-step training is not a free win"
beats "an analysis of compounding error in learned models." If it runs past about a dozen words it
has become a summary and belongs in the layer-one annotation instead.

## The conditioning note

Every entry carries one line on why it sits at position k given 1 through k-1.

> At four because two gave you the objective and three gave the failure mode, and this is the paper
> that connects them.

Nothing else writes this down, and without it a ranked list is an assertion. It also makes the
ordering debuggable: when the order is wrong, you can see which step went wrong instead of
re-running and hoping.

`runners_up` on each pick holds what nearly won. Use it when writing the note, since "this beat X
because" is usually the true sentence.

## What ships and what does not

The invariant checks are not advisory. A run that fails one does not ship.

- **monotone**: coverage never decreases as the prefix grows. A failure means the objective is not
  submodular and the whole guarantee is void.
- **prefix_optimal**: no single swap at any prefix improves the rate. This is local optimality,
  which is what greedy actually guarantees.
- **prerequisites**: nothing appears before what it requires.
- **compounding**: every project after the first names what it reuses, and that item is genuinely
  earlier.

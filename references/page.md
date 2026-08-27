# The page

The folder is for reading and the page is for deciding, and deciding here takes four seconds because
the answer is one thing.

## This file is rationale. The implementation is code.

`assets/` is shared with `industry-research` and `scripts/build_page.py` renders it. Never
hand-author CSS in a run and never restyle for a topic. An earlier version of that skill described
the design in prose and asked each run to build from the description, and the pages drifted
immediately: right palette, right typeface, entirely different structure. Two paths from the same
skill must be readable by the same reader without relearning the page.

## It opens on one item

Not twelve. Position one at full size with its annotation and its where-the-thinking-is note.
Position two at half weight below it. Everything after that as a spine of titles with times.

**That layout is the prefix guarantee rendered.** If you do one thing tonight, this one.

A page that shows twelve equally weighted entries has thrown away the entire selection argument and
returned the reader to the deliberation this skill exists to end.

## What each entry carries

**The kind and the archetype chip, before the title.** A paper, a repo and a project are read
differently, and the chip changes how everything beneath it should be understood. Repos additionally
show liveness, since a research dump and a maintained system are different objects and the star
count hides that.

**The group chip**, expanding in place into the thesis, the direction and the links out.

**The conditioning note**, visible rather than hidden. It is what makes the order credible.

**Where the thinking is**, at full weight on position one. This is the reason the reader opened the
page.

## Simple by default, and it opens

The closed page is one column: a number, a phrase, a title, its chips, its year, its lab, its
time. That is the whole field readable in one scroll.

The depth is behind disclosures, closed. A subgroup's summary says how many approaches are inside
and what they vary, because "3 more" tells a reader nothing about whether to open it. One control
at the top opens every group at once for a reader who wants the whole thing, and collapses back.

**Nothing important lives only behind a disclosure.** The spine alone has to be a complete answer,
or the closed state is a teaser rather than a simplification.

## The rest of the page

**Three track filters**, papers, repos, projects, with the interleaved path as the default. When
filtering changes the order, say what it cost.

**Time budget on the spine**, summed. With mixed costs this is the most useful number on the page:
it answers whether the first four fit tonight.

**Marking something done advances the stack** and the next expands. `localStorage`, wrapped in
try/catch, rendering correctly when it comes back empty.

## Two things drawn from the graph, and no hairball

A force-directed citation graph is the obvious move and it is wrong. It is a picture of everything
and an answer to nothing, and it is the chart equivalent of padding a thin section.

**The lineage strip.** Descent edges along the path, so the reader sees that five came out of two
and that the repo at four implements the paper at two. Prose cannot do this and the ordering is the
axis it already needs.

**The coverage bar.** Idea nodes lighting up as things get marked done, with the experiential ones
visually distinct since those stay dark until something gets built. This is the prefix guarantee
made visible and the argument for interleaving in one picture.

When a run supports neither, ship the page without a chart. An invented chart is worse than none.

## Palette, type, theme

Inherited from `industry-research/references/report-design.md` unchanged. Three states, dead as an
absence rather than a fourth hue, the relief rule where contrast falls below the line, both themes
selected rather than flipped, no webfonts because the artifact CSP blocks font CDNs.

## The confidence footer

Counts by source tier, how many claims failed verification, and the length of the could-not-verify
list. It goes at the bottom and stays visible. A run whose footer shows nothing unverified is a run
that hid something.

## Checked, not promised

`scripts/checkpage.py` enforces this document. Every rule above that can be derived from the
built file is a check that fails a build, because the first page shipped without the marking
interaction, without the track filters, with role and group chips on two of seventeen entries,
and with its title rendering as a section label. Not one of those threw an error.

Two of the checks exist because of specificity rather than logic, and both are worth knowing:

**A tag the shared stylesheet already owns.** `h2` there is a section label, monospace and
uppercase and small. Reusing it for an entry title and overriding only `font-size` inherits the
rest, and the headline renders as a label. Reset every property the shared rule sets.

**`[hidden]` loses to an explicit `display`.** The UA rule is low specificity, so
`.spine li { display: grid }` beats it and the filter appears to do nothing to the spine while
working on the articles. That reads as broken JavaScript and is broken CSS.

## What not to do

No hero number the size of the page. No emoji as section markers. No numbered `01 / 02 / 03`
markers on anything other than the path itself, where the number is load-bearing.

Do not render the folder. The folder is for reading.

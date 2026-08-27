---
name: papers
description: Build one ordered path of papers, code repositories and projects for getting deep into a topic, where reading only the first M of them is approximately the best M you could have picked. Every entry says where the thinking actually is, which lab it came from and what that lab believes. Use when the user runs /papers <topic|person|lab|company|artifact>, or asks what to read about a field, which repo to learn something from, what to build to understand an area, or who is working on it.
argument-hint: <topic | person | lab | company | "the lab that made X"> [--quick|--deep] [--only papers|repos|projects] [--hours N] [--follow]
user-invocable: true
---

# Papers

One ordered path into a topic, deep rather than wide.

The reader's stated problem: too much time spent finding the relevant papers, not enough spent
in the weeds. They want to get lost in thinking about one thing. Everything below exists to end
the deliberation quickly and hand over one item worth an evening.

**This skill has no command line.** The user types `/papers <query>` and nothing else. The
scripts under `scripts/` are machinery you call; never tell the user to run one.

## The constraint that governs the design

Given N items presented in order, the reader will get through M of them, M anywhere from 1 to N.
Those M must be approximately the best subset of size M. Every prefix optimal, not just the whole
list.

That rules out ranking by citations, since the top of that list is canon and benchmarks and the
second entry duplicates the first. It rules out chronological order. It rules out grouping by
subtopic, since the first item of group two is worse than the second item of group one.

What satisfies it is greedy selection against a coverage function with diminishing returns, which
is within a constant factor of optimal at every prefix length at once. `scripts/ordering.py`
implements it and is pure: no network, no model, no subprocess. That purity is what lets the
ordering be re-derived from a frozen graph, which is why the guarantee is tested rather than
claimed. Read `references/selection.md` before changing anything about the order.

## Three kinds of thing, one path

Papers, repos and projects cover the same ideas with different weights and different costs, so
they are scored together and interleaved rather than listed separately.

A paper covers *why this objective and not another* well and *what it actually takes* poorly. A
repo inverts that. And some ideas are covered by neither: you do not learn that the normalization
statistic eats three days until it has eaten three days. Those are marked `experiential` and only
a project covers them.

Output the interleaved path by default. `--only papers` filters. Say what filtering cost.

## Before you start

**Run `python3 scripts/doctor.py` first.** It takes seconds and it tells you what a run is
about to lose silently. Semantic Scholar rate limited means every citation edge comes back
untyped, so `builds_on` cannot be told from `baseline`. OpenReview rate limited means no
rebuttals, which is the weeds layer. Neither produces an error anywhere downstream: they
produce a path that still looks complete. Record whatever it warns about in `run.json` and say
it on the page.

Read `references/voice.md` in `industry-research`, which governs everything this skill writes.
Zero em dashes. Then read `references/selection.md`, `references/annotation.md`, and whichever of
`references/repos.md`, `references/projects.md` and `references/groups.md` the run will reach.

`references/graph.md` holds the node and edge kinds, the lead table and the frontier rules.
`references/sources.md` says which API answers which question and where each one lies.

Subagent prompts live in `agents/`. Spawn general-purpose agents with the file's contents as the
prompt plus its inputs.

## Step 0: Resolve

The query is one of six kinds of object and each seeds a different node. `agents/resolver.md`
does this. `world models` is a topic. `ricky chen FAIR` is a person, and the output is that
person's arc rather than a topic list. `the lab that made lada` is an artifact pointing at a
group, spelled the way you say it out loud.

**Sometimes the reader cannot name the thing.** "I want to sync the latent spaces of two models,
my friend called it latent retrofitting" is a naming problem, and it is the highest-value query
this skill takes: until they have the term, every search they run comes back empty and they
conclude the area does not exist. Resolve by mechanism rather than by keyword, and come back with
the names the field actually uses plus one line each on what a path under each would contain.
The phrase they were given is usually wrong, and saying so is often worth more than the path.

**At most one exchange, never a loop.** A single `AskUserQuestion` carrying at most two questions,
which thing and how wide, and it fires only when the answer changes what gets selected: a
description resolving to several differently-named lines, readings that would not share papers,
or a topic that admits both a wide and a narrow reading. Every option says what the resulting path
would contain rather than defining a term. When confident, state the resolution in one line and
continue. Silence is the common case.

Load the profile via `scripts/config.py`, which looks at `$PAPERS_PROFILE`, then
`~/.claude/papers/profile.md`, then `~/.claude/industry-research/profile.md`. It sets the register
and the reading log, and nothing else. If none exists, say so and point at `profile.example.md`
rather than guessing a path: an invented reading log silently yields an empty covered set, and the
run then re-recommends the canon the reader finished years ago. The anti-anchoring rule from that skill applies here with more
force, because a reading path is where familiar vocabulary leaks in most easily.

## Step 1: Seed the covered set from what they have read

Call `scripts/readlog.py` on `profile.reading_log`. The result is **the initial state of the
selection, not an exclusion list.** A paper already read has covered its share, so the path starts
where their knowledge stops.

On `protein folding` this is most of the value: AlphaFold 2 and 3 and Boltz are in the folder, so
position one is neither AlphaFold 2 nor "AlphaFold 2, skipped."

Report what failed to resolve rather than dropping it. A silently dropped paper reappears on the
path, and recommending something they finished last year is the fastest way to lose their trust.

## Step 2: Traverse

Not a search. A frontier loop over a persistent graph, per `references/graph.md`. Search finds the
topic and the graph finds the lineage.

Spawn prospectors with `agents/prospector.md`, one per region of the graph, in a single message so
they run concurrently. Each expands nodes along typed edges and records what came back with its
source. Every expansion decision is logged with its reason, including the refusals, because that
is what answers "why is X not here" without re-running anything.

**Stopping is dual:** a tool budget, and consecutive dry expansions yielding neither a new item nor
a new idea. Both are needed. Budget alone lets one fascinating paper absorb the run.

**Never expand a hub.** A canonical benchmark, `pytorch/pytorch`, the survey everyone cites.
Expanding those reaches everything and distinguishes nothing. `score_node` penalises them and you
should skip them explicitly and log why.

## Step 3: Read the candidates

Three agents, pipelined per candidate rather than barriered.

`agents/reader.md` per paper: role, whether it rewards slow reading, prerequisites, and where the
thinking is.

`agents/codereader.md` per repo: which of the five archetypes, whether it is readable, whether it
is alive, whether it matches its paper, and **the file, the function and where possible the commit**
where the idea lives. A repo entry that names only a URL has failed.

`agents/projector.md` last, against the ideas still uncovered. Projects exist to cover what reading
left open, which is why they are written after rather than before.

## Step 4: Select

Assemble items and call `scripts/ordering.py`. Seed by lookahead over three or four candidates, not
greedily, because position one decides what everything after it can be read as and greedy picks a
survey.

Then run the invariant checks and **do not ship a run that fails one.** Monotone coverage,
prefix local optimality, prerequisites respected, projects compounding. They are the thesis written
as assertions.

Write the conditioning note on every entry: one line on why it sits at position k given 1 through
k-1. Without it a ranked list is an assertion.

## Step 5: Groups

`agents/grouper.md`. Every entry carries a group chip that expands into what that lab works on,
their direction and their thesis, with links out. Read the thesis off the discussion and
limitations sections of their recent papers, which is where a group says what it thinks is
unsolved in its own voice. `thesis: none` is a real answer.

## Step 6: Verify, then write, then publish

`scripts/verify.py` resolves every identifier and fuzzy-matches its title against the claim. A
plausible title welded to a real arXiv id survives every check except following the link, and it
has shipped before. Repos have their own version: an `owner/repo` that does not exist looks more
checkable than it is.

Then `agents/annotator.md` for the three-layer annotations.

**Then run `python3 scripts/critique.py <run-dir>` and fix what it fails.** It grades the run
against the rules the references state, and it exists because the first test run shipped a repo
entry that was a bare URL, three placeholder group theses and three dangling group chips, and I
only caught two of those by eye. A run with blocking failures does not ship. The checks it
cannot make mechanically it reports as `look` rather than scoring, since a reading problem given
a threshold returns a confident wrong answer instead of an error.

Then the page via `scripts/build_page.py`, and **then `python3 scripts/checkpage.py <run-dir>/report.html`**.
That one is not optional either. `build_page.py` only ever checked tag balance and em dashes,
which is how the first published page shipped with its headline rendering as a tiny uppercase
monospace label, its lineage section printing raw item ids, and two features `references/page.md`
promises missing entirely. None of those errored. Fix what it fails, rebuild, run it again.

**Then open the page and look at it.** The checker catches what can be derived from the file.
It cannot tell you that a heading inherited the wrong identity from a shared rule or that a
filter silently does nothing, and both of those shipped. Publishing to a scratch artifact and
reading it is part of the build, not a courtesy.

Publish with `Artifact` yourself, reusing the same file path for the same
topic so a re-run redeploys rather than minting a new link. Record the URL in `run.json`.

## Report back

Where the folder is, what position one is and why, the single most surprising thing, and how many
claims failed verification. Do not paste the path into the conversation. It is a folder and a page
for a reason.

## Standing rules

**Anti-anchoring.** The profile sets register and reachability. It does not decide what a topic is
about. A protein folding path must not fill with diffusion-for-proteins papers because the reader
knows diffusion. Grep the profile's `deep` list against the final order and check every hit.

**Length follows substance.** A thin topic gets a short path saying it is thin.

**Every entry says where the thinking is.** Not "read section 4." The equation, the table, the
file, the function, the commit. This is the whole point of the skill.

**Never expand what you cannot source.** `add_edge` raises without an absolute URL, by design.

**Say what you could not find.** A run that reports nothing unverified hid something.

**When the search budget runs out, the run degrades in a way nothing in the output shows.** arXiv
and OpenAlex have no session cap, so this degrades less than `industry-research` does. Semantic
Scholar, OpenReview and unauthenticated GitHub all rate-limit, and losing them loses the weeds
layer while the path still looks complete. GitHub throttling is the measured one: it reports as
absence. Say so in `run.json` and on the page.

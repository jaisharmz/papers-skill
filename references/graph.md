# The graph

Finding things is traversal, not search. Search finds the topic. The graph finds the lineage.

Keyword search returns what matches the words, which is the surface of a field and skews recent
and well-titled. The structure worth reading along lives in the edges.

## Node and edge kinds

```
NODE_KINDS = ("paper", "repo", "project", "person", "group", "idea")
EDGE_KINDS = ("cites", "authored_by", "member_of", "implements", "depends_on",
              "reimplements", "evaluates_on", "covers", "disputes", "supersedes",
              "reviews", "builds_on", "requires")
```

Two of these are the design rather than the plumbing.

**`idea` nodes are what the selection runs over.** A paper `covers` an idea with a weight, and so
does a repo, and so does a project. Coverage is an edge, so the value function is a computation
over the graph rather than a second structure sitting beside it.

**`cites` carries a context**, one of `builds_on`, `baseline`, `contrasts`. Semantic Scholar gives
the citing sentence, and that sentence separates "we extend this" from "we beat this." An untyped
citation edge is nearly worthless and a typed one carries most of the signal. `add_edge` refuses a
`cites` edge without one.

**`project` nodes are generated, not found.** Everything else exists before the run. A project is
written against the uncovered ideas and enters carrying `builds_on` to what it stands on and
`requires` to what must come first.

## The lead table

Every node kind is both a destination and a springboard. Improvise over this rather than executing
it in order, because every channel fails on some population: keyword search fails on anything badly
titled, citation counts fail on anything published this year, and the graph is what covers the gaps.

| what you have | what it is a lead to |
|---|---|
| a topic | ten to twenty papers by keyword, most of them surface, cheaply |
| a paper | its references, its citers, its authors, its repo, its OpenReview thread |
| a paper's opening paragraphs | the two or three works the subfield is built on |
| a paper's related-work section | the competing programme, named by someone who had to distinguish themselves from it |
| a paper's limitations section | the ideas nobody has covered, stated by people who would know |
| an OpenReview thread | the objection nobody published, and which paper a reviewer wanted cited |
| a rebuttal | what the authors conceded, which the camera-ready hides |
| an author | their arc, their students, their recent coauthors |
| recurring coauthors | the group, without needing a lab page to exist |
| a group page | what they consider their own work, which differs from what cites them |
| a repo | its paper, its dependents, its issues, and forks that are commits ahead |
| a repo's core file | the idea with the packaging removed, usually 200 lines of 20,000 |
| `git log -S<concept>` | the commit where the trick entered, which is the idea as a diff |
| an issue thread | "I cannot reproduce table 3", the repo's version of a rebuttal |
| a repo's dependents | who actually runs this method, as opposed to who cites it |
| a fork with commits ahead | what someone needed to change to make it work |
| a benchmark | everyone who ever ran it, which is a hub and mostly noise |
| a citation sentence | whether B builds on A or beats A, which no count can tell you |
| a failed replication | the paper it corrects, which changes how you read it |
| the reading log | the frontier: what sits one hop from what has already been read |
| a previous run | most of the above, already resolved and sourced |

That last row is why the graph persists.

## The seminal test

The honest one is not citation count. It is: **do later papers cite this in their opening
paragraphs as the thing they are building on, rather than in their results table as a baseline they
beat?** A field-founding paper gets referenced for its framing. A benchmark gets referenced for its
numbers and collects a citation from everyone who ever ran it.

A paper cited by nine of twelve candidates in their intros is the thing the subfield is built on,
whatever its count says. The `cites` context is what makes this computable.

## Scoring a frontier node

`score_node` in `pgraph.py`. Five components, all explainable, and the weights are a starting point
to be corrected against a real run rather than defended.

**Corroboration is weighted highest**, and it is the idea most worth keeping. `path_count` counts
independent routes to a node. A two-hop paper reached three different ways beats a one-hop paper
reached once. This is the honest answer to "is this actually central" and it does not go through
citations.

**Note what is absent: citation count and star count.** Both are available and both rank a
benchmark above a dense theory paper, which is the inversion this skill exists to avoid.

## The hub penalty

`HUB_DEGREE = 40`. Beyond it a node is a hub, not a lead, and expanding it reaches everything and
distinguishes nothing. Attention Is All You Need, `pytorch/pytorch`, the survey everyone cites.

Skip them explicitly and log why. A skipped hub with a recorded reason is information. A silently
skipped hub looks like an oversight.

## Identity

`upsert_node` merges on the strongest available identifier and falls back to a normalized title.
arXiv versions collapse to one work, since v1 and v3 differing in the part you care about belongs
in `attrs` on one node rather than in two nodes nobody can compare.

The adopt rule works in both directions, which the outbound version does not: a traversal meets a
paper as a reference string before it resolves the identifier at least as often as the reverse.

**Two nodes that both carry external ids never merge silently.** The collision is recorded instead,
because merging those is a judgment call and a silent merge is unrecoverable.

## The frontier loop

Score the frontier, pick a node worth expanding, expand along typed edges, store what came back
with its source, log the decision and the yield. Which node and when to stop is judgment and belongs
to the run rather than to the code.

**Stopping is dual.** A tool budget, and consecutive dry expansions yielding neither a new item nor
a new idea. Both are needed. Budget alone lets one fascinating paper absorb the entire run, and
dryness alone never terminates on a citation graph.

## Mine what exists first

The reading log, plus every prior run in `~/.claude/papers/graph.db`. Re-resolving a paper that
already has an identifier and sourced edges attached is wasted budget.

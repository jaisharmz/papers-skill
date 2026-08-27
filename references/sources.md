# Sources

Which API answers which question, and where each one lies. Every defect listed here was measured
rather than assumed, and the ones inherited from `outbound-sourcing` carry their original wording
because the correction matters more than the finding.

## arXiv

`http://export.arxiv.org/api/query`. Free, no key, no session cap. The papers themselves plus the
version history, which matters because v1 and v3 of a contested paper can differ in exactly the
part you care about.

Rate limit is one request every three seconds and it is enforced by delay rather than by error.

## OpenAlex

`https://api.openalex.org`. The graph backbone. Use `scripts/openalex.py`, which is ported from
outbound with its defects already measured in the module docstring:

- coauthorship edges are reliable, since who wrote what with whom comes from the paper
- `last_known_institutions` is a LIST and its first element is **not** the most recent. Reading
  `[0]` returns "Berkeley College" for someone at Together AI. Do not use it.
- `affiliations[]` carries institution plus the years seen. Ranked on sustained recency this
  resolves 6 or 7 of 8 spot checks, and the failures come back low confidence rather than
  confidently wrong.
- **profile conflation**: OpenAlex merges some distinct people into one author record. A works count
  wildly out of line with career stage is the tell. This bites hardest on `ricky chen FAIR`, since
  common names are exactly the query shape that resolves through an author id.

## Semantic Scholar

`https://api.semanticscholar.org/graph/v1`. The citation *context*: the sentence in which B cites A.
That sentence separates `builds_on` from `baseline` without reading either paper, and it is what
makes the `cites` edge worth storing.

Free and rate-limited, key optional and worth having. **This is the first thing a long run loses**,
and losing it degrades the graph to untyped citation edges while the output still looks complete.
Say so in `run.json`.

## OpenReview

`https://api2.openreview.net`. The part nobody surfaces and the reason this skill can deliver on
"the weeds."

The reviews and the rebuttal are where the field's actual objection to a paper is stated in public
by someone who read it carefully and was not persuaded. Reviewer 2 saying "the ablation in table 3
does not control for X" and the authors conceding it is worth more than the related-work section of
any paper. ICLR, NeurIPS and ICML are all there.

Read the rebuttal specifically. The camera-ready hides what was conceded.

## GitHub

`https://api.github.com`. Liveness, dependents, forks ahead, and the issue threads.

**Unauthenticated is sixty requests an hour, which cannot cover a real run.** Use `GITHUB_TOKEN`
when present.

**Throttling is not absence.** An unauthenticated sweep once reported "no public repos" for 78 of 88
companies and it was a rate limit. That read as a finding. Every outcome is a named status and
`throttled` never reports as absent.

For the commit that introduced an idea, a shallow clone plus `git log -S<concept> --oneline` is the
only honest route. Do not guess a hash.

## The failure that is not a failure message

**WebFetch renders a page to markdown before you see it, and anything the conversion drops is
invisible and indistinguishable from absent.** This has produced three wrong answers in this
project, every one plausible rather than an error, including a fund's portfolio grid that reported
"no current investments" while 855 companies sat in a `data-companies` HTML attribute.

When a page returns suspiciously little, `curl` the source and grep for framework JSON payloads
before concluding it has nothing. Lab pages and group rosters are exactly the client-rendered shape
that triggers this.

## Degradation

arXiv and OpenAlex have no session cap, so this skill degrades less than `industry-research` does.
Semantic Scholar, OpenReview and unauthenticated GitHub all rate-limit, and a run that loses them
loses the weeds layer and the typed edges while the path still looks complete.

Record it in `run.json` and say it on the page. A degraded run is worth shipping. A degraded run
that reads as complete is not.

If browser automation is available, use it for blocked hosts. Never complete a CAPTCHA; switch
search engines instead, since DuckDuckGo challenges quickly under automation and Bing and Brave
generally do not.

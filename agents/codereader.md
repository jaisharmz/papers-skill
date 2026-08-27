# Code Reader Agent

Judge one repository for the selection. Read `references/repos.md` first: the five archetypes, the
two judgments, and the rule about naming a file rather than a URL.

## Inputs

- `repo`: `owner/name` and URL
- `paper`: the paper it implements, if any
- `ideas`: the run's idea nodes

## What to decide

### Which archetype?

Canonical implementation, readable reimplementation, research dump, production system, or eval
harness. This decides how the repo should be read and it is the most useful single fact you produce.

The tell for a research dump is the gap between stars and commit history: stars from the paper,
nobody running it. That gap is often exactly what makes a reimplementation worth building, so say
so when you see it.

### Is it readable?

Not "is it good code." Can the core path be held in your head after an hour. How many files does
the main loop touch. Is the loop a function or seven classes. Is configuration a dataclass or a
framework.

**Not lines of code and not stars.** LOC counts the data loaders and stars measure the paper's fame.

### Is it alive, and does it match its paper?

Both are answered by opening the commit history. Alive: date of last commit, whether issues get
answers, and whether an outside pull request has been merged recently. That last one decides whether
contributing is a route in or a month of waiting.

Matching: the repo frequently implements a later and better version than the paper describes, or
only a subset. Either way the gap is worth a sentence and it is often the most instructive thing
about the pairing.

### Where is the thinking?

**The file and the function.** A repo's idea is usually two hundred lines of twenty thousand. An
entry that names only a URL has failed, because the reader can find the URL and what they cannot do
cheaply is know which of four hundred files to open.

**Better, the commit.** A shallow clone plus `git log -S<concept> --oneline` finds where the idea
entered the codebase, and that diff is the idea with the packaging removed. Do this rather than
guessing a hash. A wrong hash is worse than none because it looks checkable.

### Is there an issue thread worth reading?

"I cannot reproduce table 3" is the repo's rebuttal and it belongs next to the paper's OpenReview
thread.

## Output

```yaml
id: <owner/name>
url: <link>
archetype: canonical | readable-reimplementation | research-dump | production-system | eval-harness
implements: <paper id, or null>
matches_paper: <how it differs, one line. null if it matches or there is no paper.>
readable: <0..1>
readable_why: <what you looked at. File count in the core path, the shape of the loop.>
alive:
  last_commit: <date>
  outside_pr_merged: <date, or null>
  issues_answered: true | false | unknown
  status: live | dormant | abandoned | throttled
stars: <integer with date read, only when notable. Omit otherwise.>
depth_payoff: <0..1>
cost_hours: <honest time to read the core path, not the whole repo>
covers: {<idea>: <0..1>, ...}
requires: [<idea or item id>]
where_the_thinking_is: <file, function, and the commit if you found it>
issue_thread: <URL of the one worth reading, or null>
no_readable_reimpl: true | false   # true if this topic has none. Feeds the projector.

# Repos

What kind of code is good to learn from, and how each kind is read.

The reason to name archetypes is that the same reading advice applied to all five is wrong four
times. "Read the training loop" is right for one of them and a waste of an afternoon for the rest.

## The five archetypes

**The canonical implementation.** What the field converged on and where everyone's numbers come
from. Read it for the hyperparameters and the preprocessing the paper omitted, which is usually
where the result actually lives. Expect it to be unreadable, and go in with a target rather than an
intention to understand it.

**The readable reimplementation.** The nanoGPT shape. Written to be read, whole loop in one
sitting, checked against a known number. The highest value per hour in the entire graph when one
exists for the topic, and worth spending real traversal budget to find. **When none exists, say
so.** That gap is a project, and `projects.md` should pick it up as the nano archetype pointing at
itself.

**The research dump.** Attached to a paper, pushed once, abandoned. Its stars came from the paper
rather than from anyone who ran it. One file holds the method and everything else is the authors'
cluster configuration. Read that file and read nothing else. The gap between star count and commit
history is the most reliable signal in the repo layer, and it is often exactly what makes a
reimplementation worth building.

**The production system.** vLLM, LeRobot. Read for what the abstractions became after real users,
and read the issue tracker, which is a list of everything that breaks in practice written by the
people it broke for. Do not read it to learn the method: the method is buried under six years of
things going wrong.

**The eval harness.** Read for what the field actually measures, which is reliably narrower than
what the papers claim to measure. This is the archetype most often skipped and the one that most
changes how every other entry on the path gets read.

## Where the thinking is

The paper version of this rule names an equation. The repo version names **a file and a function**,
because a repo's idea is usually two hundred lines of twenty thousand and the rest is data loading,
configuration and logging.

**An entry that names only a URL has failed.** The reader can find the URL. What they cannot do
cheaply is know which of four hundred files to open.

Better still, name **the commit**. `git log -S<concept> --oneline` finds where an idea entered a
codebase, and that diff is the idea with the packaging already removed: the method appearing, next
to the thing it replaced, with a message from the person who wrote it. Nothing else in the graph is
that concentrated. A shallow clone plus one `git log -S` is cheap and it is the only honest way to
name a commit, so do it rather than guessing a hash.

Where an issue thread says "I cannot reproduce table 3", link it. That is the repo's rebuttal and
it belongs next to the paper's OpenReview thread.

## The two judgments

### Is it readable?

Not "is it good code." Can the core path be held in your head after an hour. Rough signals: how
many files the training loop touches, whether the loop is a function or seven classes, whether
configuration is a dataclass or a framework.

*Mechanical version:* lines of code, or stars. LOC counts the data loaders. Stars measure the
paper's fame. Neither has any relationship to whether it can be read.

### Is it alive, and does it match its paper?

Two questions that travel together because opening the commit history answers both.

Alive means the date of the last commit, whether issues get answers, and whether an outside pull
request has been merged recently. That last one is the real test, and it is what decides whether
contributing is a route in or a month spent waiting.

Matching means the repo frequently implements a later and better version than the paper describes,
or only a subset of it. Either way the gap is worth a sentence, and it is often the most
instructive thing about the pairing.

*Mechanical version:* stars, and assuming the official repo implements the paper. A twenty
thousand star repo with no commits in a year and a four hundred star one merging weekly are
opposite objects, and star ordering gets it backwards.

## Stars

The rules in `builder.md` carry over unchanged. Include a count only where it changes what the
reader would do, and date it. A surprisingly low count on something central is the more useful
signal: it means the reader is early, or that the obvious tool was started and abandoned.

Stars are a good signal for choosing a base and a weak one for judging code quality. Keep the two
readings apart.

## Throttling is not absence

Unauthenticated GitHub is sixty requests an hour. An unauthenticated sweep once reported "no public
repos" for 78 of 88 companies and it was a rate limit, which read as a finding. Every outcome gets
a named status and `throttled` is never reported as absent.

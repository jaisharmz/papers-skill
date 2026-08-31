"""Where this installation's reader profile lives, and nothing else.

Rule 2 of the outbound spec, applied here: the skill is general and the operator's
details live in config. Nothing about a particular person appears in SKILL.md, in
references/, or in any script. Swap the profile and the skill runs unchanged.

Resolution order, first hit wins:

  $PAPERS_PROFILE                        an explicit path, for a one-off run
  ~/.claude/papers/profile.md            this skill's own profile
  ~/.claude/industry-research/profile.md the sibling skill's, if that is installed

The last entry is deliberate. `industry-research` bootstraps exactly the profile
this skill needs, and asking someone who already has one to write it twice is how
a tool stops being used.
"""

from __future__ import annotations

import os
import pathlib
import re

HOME = pathlib.Path("~/.claude").expanduser()

CANDIDATES = [
    os.environ.get("PAPERS_PROFILE"),
    HOME / "papers" / "profile.md",
    HOME / "industry-research" / "profile.md",
]

GRAPH_DB = pathlib.Path(
    os.environ.get("PAPERS_GRAPH", HOME / "papers" / "graph.db")).expanduser()
CACHE_DIR = pathlib.Path(
    os.environ.get("PAPERS_CACHE", HOME / "papers" / "cache")).expanduser()


def profile_path() -> pathlib.Path | None:
    for c in CANDIDATES:
        if not c:
            continue
        p = pathlib.Path(c).expanduser()
        if p.exists():
            return p
    return None


# Personalization is OPT-IN. A path built for one person's history is a worse
# artifact for everyone else and a slightly odd one even for its owner, who did
# not ask to be reminded what they have read on a page about a field. The default
# run knows nothing about the reader; `--me` turns the profile on.
PERSONAL_FLAGS = ("--me", "--personal", "--profile")


def personalized(args: str | list | None) -> bool:
    argv = args.split() if isinstance(args, str) else list(args or [])
    return any(a in PERSONAL_FLAGS or a.startswith("--profile=") for a in argv)


def reading_log(personal: bool = True) -> pathlib.Path | None:
    """The folder of things already read, from the profile's front matter.

    Returns None rather than a guess. An invented path silently yields an empty
    covered set, and the run then re-recommends the canon the reader finished
    years ago, which is the fastest way for the output to lose them.

    Returns None unconditionally when the run is not personalized, so the covered
    set starts empty and the path is the one a stranger to the field should read.
    """
    if not personal:
        return None
    p = profile_path()
    if not p:
        return None
    m = re.search(r"^reading_log:\s*(\S+)", p.read_text(), re.M)
    if not m:
        return None
    d = pathlib.Path(m.group(1).strip("'\"")).expanduser()
    return d if d.exists() else None


def describe(personal: bool = True) -> dict:
    p, r = profile_path(), reading_log(personal)
    return {"personalized": personal,
            "profile": str(p) if p and personal else None,
            "reading_log": str(r) if r else None,
            "graph_db": str(GRAPH_DB), "cache": str(CACHE_DIR),
            "searched": [str(pathlib.Path(c).expanduser()) for c in CANDIDATES if c]}

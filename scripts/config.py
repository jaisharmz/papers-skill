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


def reading_log() -> pathlib.Path | None:
    """The folder of things already read, from the profile's front matter.

    Returns None rather than a guess. An invented path silently yields an empty
    covered set, and the run then re-recommends the canon the reader finished
    years ago, which is the fastest way for the output to lose them.
    """
    p = profile_path()
    if not p:
        return None
    m = re.search(r"^reading_log:\s*(\S+)", p.read_text(), re.M)
    if not m:
        return None
    d = pathlib.Path(m.group(1).strip("'\"")).expanduser()
    return d if d.exists() else None


def describe() -> dict:
    p, r = profile_path(), reading_log()
    return {"profile": str(p) if p else None,
            "reading_log": str(r) if r else None,
            "graph_db": str(GRAPH_DB), "cache": str(CACHE_DIR),
            "searched": [str(pathlib.Path(c).expanduser()) for c in CANDIDATES if c]}

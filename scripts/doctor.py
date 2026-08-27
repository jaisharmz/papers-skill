"""What is wrong, and the exact thing that fixes it.

Run this at the start of a session before spending a traversal budget. It
diagnoses the failures this skill actually hits rather than checking that files
parse. Every check that can fail prints a fix, because a diagnosis without a fix
just relocates the confusion.

Ordering is cheapest-first and stop-worthy problems sort to the top, since
whoever is reading this is already annoyed and will act on the first thing they
see.

The important one is the network block. Losing Semantic Scholar or OpenReview
does not produce an error anywhere downstream. It produces a path that still
looks complete and has quietly lost its typed citation edges and its weeds
layer, and the only way to know is to check before the run rather than after.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

OK, WARN, FAIL = "ok", "warn", "fail"
SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))
from scripts import config
UA = "papers-skill/0.1"


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    fix: list[str] = field(default_factory=list)
    degrades: str = ""       # what a run silently loses if this is not fixed


def _c(name, status, detail="", fix=(), degrades=""):
    return Check(name, status, detail, list(fix), degrades)


def _reach(url: str, timeout: int = 8) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, str(e.reason)
    except Exception as e:
        return 0, str(e)


# ------------------------------------------------------------------- local


def check_profile() -> Check:
    p = config.profile_path()
    if p is None:
        looked = ", ".join(config.describe()["searched"])
        return _c("profile", FAIL, f"none found. Looked in {looked}",
                  ["Copy profile.example.md to ~/.claude/papers/profile.md and edit it.",
                   "Or run /industry-research once, which bootstraps the same file.",
                   "Or set PAPERS_PROFILE to point at one."],
                  "Without it the register is guessed and the reading log is empty, so the "
                  "path starts from foundations the reader finished years ago.")
    txt = p.read_text()
    if not re.search(r"^reading_log:\s*(\S+)", txt, re.M):
        return _c("profile", WARN, f"{p.name} has no `reading_log:` key",
                  ["Add `reading_log: /path/to/your/papers/` to the front matter."],
                  "The covered set starts empty and the path re-recommends what they read.")
    return _c("profile", OK, f"{len(txt.split())} words, reading_log set")


def check_reading_log() -> Check:
    root = config.reading_log()
    if root is None:
        p = config.profile_path()
        if p is None:
            return _c("reading log", WARN, "skipped, no profile")
        return _c("reading log", FAIL, "the profile's reading_log path does not exist",
                  [f"Fix `reading_log:` in {p}, or point it at wherever the PDFs live."],
                  "Every run starts from zero coverage and re-recommends the canon.")
    sys.path.insert(0, str(SKILL))
    from scripts.readlog import scan
    s = scan(root)
    n, un = len(s["entries"]), len(s["unresolved"])
    if not n:
        return _c("reading log", FAIL, f"{root} has no resolvable PDFs",
                  ["Check the folder actually contains .pdf files."],
                  "Same as missing: the path will start from foundations.")
    status = WARN if un > n * 0.2 else OK
    return _c("reading log", status, f"{n} resolved, {un} unresolved, "
              f"{len(s['by_topic'])} topics",
              ["Unresolved files are reported rather than dropped, so this is safe. "
               "Rename them to the paper's short name if you want them counted."]
              if un else [])


def check_graph_store() -> Check:
    p = config.GRAPH_DB
    if not p.exists():
        return _c("graph store", OK, "none yet, first run will create it")
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        n = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        e = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        bad = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE source_url NOT LIKE 'http%'").fetchone()[0]
        col = conn.execute("SELECT COUNT(*) FROM collisions").fetchone()[0]
    except sqlite3.Error as ex:
        return _c("graph store", FAIL, str(ex),
                  [f"Move {p} aside and let the next run rebuild it."],
                  "A corrupt store silently returns no prior work, so every run pays full price.")
    if bad:
        return _c("graph store", FAIL, f"{bad} unsourced edges",
                  ["This should be impossible: add_edge raises without an absolute URL. "
                   "Something wrote to the DB directly. Move it aside."],
                  "Unsourced edges are assertions and they reach the reading path.")
    d = f"{n} nodes, {e} edges"
    if col:
        d += f", {col} identity collisions to review"
    return _c("graph store", OK, d)


def check_assets() -> Check:
    shared = SKILL.parent / "industry-research" / "assets"
    missing = [f for f in ("report.css", "report.js") if not (shared / f).exists()]
    if missing:
        return _c("shared assets", FAIL, f"missing {missing} in {shared}",
                  ["The page inherits industry-research's stylesheet. Install that skill, "
                   "or copy its assets/ directory into this one."],
                  "No page gets built. The folder still works.")
    return _c("shared assets", OK, str(shared))


def check_selection_purity() -> Check:
    """The invariant that makes the ordering testable, checked here too because
    doctor runs when tests do not."""
    src = (SKILL / "scripts" / "ordering.py").read_text()
    bad = [m for m in re.findall(r"^\s*(?:from|import)\s+(\w+)", src, re.M)
           if m in {"requests", "httpx", "urllib", "socket", "subprocess", "openai",
                    "anthropic"}]
    if bad:
        return _c("selection purity", FAIL, f"ordering.py imports {bad}",
                  ["Remove it. The ordering must be derivable from a frozen graph, "
                   "or the prefix guarantee cannot be tested."],
                  "The order stops being reproducible and the invariant checks become theatre.")
    return _c("selection purity", OK, "no network or model imports")


# ------------------------------------------------------------------ network


def check_apis() -> list[Check]:
    probes = [
        ("arXiv", "http://export.arxiv.org/api/query?id_list=1706.03762&max_results=1",
         "Papers and titles cannot be verified, so a fabricated identifier ships.", True),
        ("OpenAlex", "https://api.openalex.org/works?per-page=1",
         "The citation graph is unavailable and the run degrades to keyword search.", True),
        ("Semantic Scholar",
         "https://api.semanticscholar.org/graph/v1/paper/search?query=world+models&limit=1",
         "Citation CONTEXTS are lost, so every cites edge becomes untyped and "
         "builds_on cannot be told from baseline.", False),
        ("OpenReview", "https://api2.openreview.net/notes?limit=1",
         "The weeds layer is lost: no reviews, no rebuttals, no record of what "
         "authors conceded.", False),
        ("GitHub", "https://api.github.com/rate_limit",
         "Repo liveness is unknown, and throttling reads as absence unless handled.", False),
    ]
    out = []
    for name, url, degrades, critical in probes:
        code, err = _reach(url)
        if code == 200:
            extra = ""
            if name == "GitHub" and not os.environ.get("GITHUB_TOKEN"):
                extra = " (unauthenticated: 60 req/hr)"
                out.append(_c(f"{name} reachable", WARN, f"HTTP 200{extra}",
                              ["Set GITHUB_TOKEN to a fine-grained token with no scopes "
                               "selected. Public read is the default and 60/hr cannot "
                               "cover a real run."], degrades))
                continue
            out.append(_c(f"{name} reachable", OK, f"HTTP 200{extra}"))
        elif code in (403, 429):
            out.append(_c(f"{name} reachable", WARN, f"rate limited (HTTP {code})",
                          ["Wait, or run with a token where one applies. "
                           "Throttled is UNKNOWN, never absent."], degrades))
        else:
            out.append(_c(f"{name} reachable", FAIL if critical else WARN,
                          f"HTTP {code} {err}"[:90],
                          ["Check the network. If this host is blocked, use browser "
                           "automation for it and say the run was degraded."], degrades))
    return out


def run() -> int:
    checks = [check_profile(), check_reading_log(), check_selection_purity(),
              check_assets(), check_graph_store()] + check_apis()
    order = {FAIL: 0, WARN: 1, OK: 2}
    fails = 0
    for c in sorted(checks, key=lambda c: order[c.status]):
        fails += c.status == FAIL
        mark = {OK: "ok  ", WARN: "warn", FAIL: "FAIL"}[c.status]
        print(f"{mark}  {c.name}" + (f": {c.detail}" if c.detail else ""))
        if c.status != OK:
            if c.degrades:
                print(f"        silently loses: {c.degrades}")
            for f in c.fix:
                print(f"        fix: {f}")
    n_ok = sum(1 for c in checks if c.status == OK)
    print(f"\n{n_ok}/{len(checks)} clean, {fails} blocking")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

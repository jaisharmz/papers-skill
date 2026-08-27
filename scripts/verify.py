"""Every identifier resolves, and its title matches the claim.

The failure this exists to make impossible has already shipped once in this
project: a plausible paper title welded to a genuine arXiv identifier survives
every check except following the link. A second version of it is a real number
lifted from a real paper and attached to the wrong measurement, which produces a
finding fabricated entirely out of true parts.

Repos have their own version and it is worse, because an `owner/repo` that does
not exist looks more checkable than a paper title does. So does a commit hash:
a guessed hash is the most confident-looking wrong answer in the whole pipeline,
which is why references/repos.md says to run `git log -S` rather than guess.

This is deterministic. No model decides whether a title matches, because a model
asked "is this close enough" says yes.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict

UA = "papers-skill/0.1 (research reading path builder)"
ARXIV_API = "http://export.arxiv.org/api/query"
GITHUB_API = "https://api.github.com/repos"

# Below this, the title on the page is not the title in the draft and the entry
# does not ship. Tuned to pass ordinary punctuation and casing drift and to fail
# a different paper by the same group, which is the realistic confusion.
MATCH_FLOOR = 0.72

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")
_ARXIV = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?")
_HASH = re.compile(r"^[0-9a-f]{7,40}$", re.I)


@dataclass
class Result:
    ref: str
    kind: str                 # arxiv | github | commit
    ok: bool
    status: str               # verified | title-mismatch | not-found | throttled | unchecked
    found: str | None = None
    claimed: str | None = None
    score: float | None = None
    detail: str = ""

    def line(self) -> str:
        mark = "ok  " if self.ok else "FAIL"
        extra = f"  claimed {self.claimed!r} / found {self.found!r}" if self.found else ""
        return f"{mark} {self.kind:<7} {self.ref:<24} {self.status}{extra}"


def norm(s: str) -> str:
    return _WS.sub(" ", _PUNCT.sub(" ", (s or "").lower())).strip()


def similarity(a: str, b: str) -> float:
    """Token F1 over normalized titles.

    Deliberately not a substring check. "Flow Matching for Generative Modeling"
    and "Flow Matching Guide and Code" share a prefix, come from overlapping
    authors, and are different papers. Token overlap separates them and a prefix
    check does not.
    """
    ta, tb = set(norm(a).split()), set(norm(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if not inter:
        return 0.0
    p, r = inter / len(ta), inter / len(tb)
    return 2 * p * r / (p + r)


def _get(url: str, *, timeout: int = 20) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def _openalex_title(aid: str) -> str | None:
    """Fallback title lookup when arXiv is throttling.

    Added because a real run hit it: five prospectors plus a verification sweep
    exhausted arXiv's limit, and every identifier came back `throttled`. The
    status was correct and the run was still blocked, because a verifier that
    can only ask one source is one outage away from verifying nothing. OpenAlex
    indexes arXiv preprints and has no session cap, so it answers the only
    question this module actually asks: what is the real title behind this id.
    """
    # The DOI form is the reliable one. Every arXiv paper carries the registered
    # DOI 10.48550/arXiv.<id>, and looking up the abs URL instead misses recent
    # preprints that OpenAlex has indexed by DOI but not by landing page.
    code, body = _get(f"https://api.openalex.org/works/doi:10.48550/arXiv.{aid}")
    if code != 200 or not body:
        return None
    try:
        d = json.loads(body)
        return d.get("title") or (d.get("results") or [{}])[0].get("title")
    except (json.JSONDecodeError, IndexError, KeyError):
        return None


def verify_arxiv(ref: str, claimed_title: str) -> Result:
    m = _ARXIV.search(ref or "")
    if not m:
        return Result(ref, "arxiv", False, "not-found", detail="no arXiv id in reference")
    aid = m.group(1)
    url = f"{ARXIV_API}?{urllib.parse.urlencode({'id_list': aid, 'max_results': 1})}"
    code, body = _get(url)
    if code != 200 or not body:
        # arXiv is down or throttling. Ask OpenAlex the same question rather than
        # reporting an unverified entry, but say which source answered.
        alt = _openalex_title(aid)
        if alt:
            score = similarity(claimed_title, alt)
            ok = score >= MATCH_FLOOR
            return Result(aid, "arxiv", ok, "verified-via-openalex" if ok else "title-mismatch",
                          found=alt, claimed=claimed_title, score=round(score, 3),
                          detail="arXiv throttled, resolved through OpenAlex")
        return Result(ref, "arxiv", False, "throttled" if code in (429, 0) else "not-found",
                      detail=f"HTTP {code}, and OpenAlex could not resolve it either")
    text = body.decode("utf-8", "ignore")
    if "<entry>" not in text:
        return Result(aid, "arxiv", False, "not-found", detail="no entry returned")
    t = re.search(r"<entry>.*?<title>(.*?)</title>", text, re.S)
    found = _WS.sub(" ", t.group(1)).strip() if t else None
    if not found:
        return Result(aid, "arxiv", False, "not-found", detail="entry had no title")
    score = similarity(claimed_title, found)
    ok = score >= MATCH_FLOOR
    return Result(aid, "arxiv", ok, "verified" if ok else "title-mismatch",
                  found=found, claimed=claimed_title, score=round(score, 3))


def verify_repo(ref: str, claimed_desc: str = "") -> Result:
    """`owner/name` exists. Description match is advisory: repo descriptions are
    often empty or a slogan, so a mismatch there is not a failure."""
    slug = re.sub(r"^https?://(www\.)?github\.com/", "", (ref or "").strip()).strip("/")
    if slug.count("/") != 1:
        return Result(ref, "github", False, "not-found", detail="not an owner/name slug")
    code, body = _get(f"{GITHUB_API}/{slug}")
    if code == 404:
        return Result(slug, "github", False, "not-found", detail="repo does not exist")
    if code in (403, 429):
        # Throttling is not absence. 78 of 88 came back "no public repos" once and
        # it was a rate limit, which read as a finding.
        return Result(slug, "github", False, "throttled",
                      detail="rate limited: this is NOT evidence the repo is absent")
    if code != 200 or not body:
        return Result(slug, "github", False, "not-found", detail=f"HTTP {code}")
    data = json.loads(body)
    detail = (f"pushed {(data.get('pushed_at') or '')[:10]}, "
              f"{data.get('stargazers_count', 0)} stars, "
              f"archived={data.get('archived')}")
    return Result(data.get("full_name", slug), "github", True, "verified", detail=detail)


def verify_commit(repo: str, sha: str) -> Result:
    """A guessed hash is the most confident-looking wrong answer in the pipeline."""
    if not _HASH.match(sha or ""):
        return Result(sha, "commit", False, "not-found", detail="not a hash")
    slug = re.sub(r"^https?://(www\.)?github\.com/", "", repo).strip("/")
    code, body = _get(f"{GITHUB_API}/{slug}/commits/{sha}")
    if code in (403, 429):
        return Result(sha, "commit", False, "throttled", detail="rate limited, not absent")
    if code != 200:
        return Result(sha, "commit", False, "not-found",
                      detail=f"no commit {sha[:8]} in {slug}")
    msg = (json.loads(body).get("commit", {}).get("message") or "").split("\n")[0]
    return Result(sha[:8], "commit", True, "verified", found=msg[:80], detail=slug)


def verify_entries(entries, *, pause: float = 3.0) -> dict:
    """Check every identifier on a path. arXiv asks for one request per 3s."""
    results: list[Result] = []
    for e in entries:
        aid = e.get("arxiv") or e.get("id") if e.get("kind") == "paper" else None
        if aid and _ARXIV.search(str(aid)):
            results.append(verify_arxiv(str(aid), e.get("title", "")))
            time.sleep(pause)
        if e.get("kind") == "repo" or e.get("repo"):
            slug = e.get("repo") or e.get("id")
            r = verify_repo(str(slug))
            results.append(r)
            sha = e.get("commit")
            if sha and r.ok:
                results.append(verify_commit(str(slug), str(sha)))

    failed = [r for r in results if not r.ok]
    return {
        "checked": len(results),
        "verified": len(results) - len(failed),
        "failed": [asdict(r) for r in failed],
        "throttled": sum(1 for r in results if r.status == "throttled"),
        "lines": [r.line() for r in results],
        # Anything throttled is UNKNOWN, not absent. A run that reports a
        # throttled repo as missing has invented a finding.
        "degraded": any(r.status == "throttled" for r in results),
    }

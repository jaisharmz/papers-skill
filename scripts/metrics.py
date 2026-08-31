"""Citations for papers, stars for repos, and a paper's repo with its stars.

Fetched and dated, never asserted. `builder.md`'s rules on how to read these
carry over and are the reason this module returns context rather than a bare
number:

  A count moves, so it carries the source and the date it was read.
  Under six months old, report "too new to cite" rather than a raw count. A
  four-month-old paper with three citations and a four-year-old paper with three
  citations are opposite findings and the number hides that.
  A surprisingly LOW count on something central is the more useful signal. It
  means the reader is early, or the obvious tool was started and abandoned.
  Stars choose a base; they do not judge code. A research dump collects stars
  from its paper, not from anyone who ran it, and that gap is often exactly what
  makes a reimplementation worth building.

Deterministic. No judgment about what a number means lives here.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict

UA = "papers-skill/0.1 (reading path builder)"
TOO_NEW_MONTHS = 6


@dataclass
class Metric:
    kind: str                 # citations | stars
    value: int | None
    read_on: str
    source: str
    note: str = ""            # "too new to cite", "throttled", "not found"

    @property
    def ok(self) -> bool:
        return self.value is not None


def _get(url: str, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def _today() -> str:
    return _dt.date.today().isoformat()


def _months_since(year: int | None, month: int | None = None) -> float:
    if not year:
        return 99.0
    today = _dt.date.today()
    return (today.year - year) * 12 + (today.month - (month or 6))


def citations(arxiv_id: str, year: int | None = None) -> Metric:
    """OpenAlex, by the registered arXiv DOI. No key, no session cap."""
    aid = re.sub(r"v\d+$", "", (arxiv_id or "").strip())
    if not re.match(r"^\d{4}\.\d{4,5}$", aid):
        return Metric("citations", None, _today(), "openalex", "not an arXiv id")
    if _months_since(year) < TOO_NEW_MONTHS:
        return Metric("citations", None, _today(), "openalex", "too new to cite")
    code, body = _get(f"https://api.openalex.org/works/doi:10.48550/arXiv.{aid}")
    if code in (403, 429):
        return Metric("citations", None, _today(), "openalex", "throttled")
    if code != 200 or not body:
        return Metric("citations", None, _today(), "openalex", "not indexed")
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return Metric("citations", None, _today(), "openalex", "unparseable")
    return Metric("citations", d.get("cited_by_count"), _today(), "openalex")


def stars(slug: str) -> Metric:
    """GitHub. Throttling is reported as throttled, never as zero or absent."""
    s = re.sub(r"^https?://(www\.)?github\.com/", "", (slug or "")).strip("/")
    s = "/".join(s.split("/")[:2])
    if s.count("/") != 1:
        return Metric("stars", None, _today(), "github", "not an owner/repo slug")
    code, body = _get(f"https://api.github.com/repos/{s}")
    if code in (403, 429):
        # Never 0. An unauthenticated sweep once reported "no public repos" for
        # 78 of 88 targets and it was a rate limit, which read as a finding.
        return Metric("stars", None, _today(), "github", "throttled")
    if code != 200 or not body:
        return Metric("stars", None, _today(), "github", "not found")
    d = json.loads(body)
    return Metric("stars", d.get("stargazers_count"), _today(), "github")


def repo_for_paper(arxiv_id: str) -> str | None:
    """The repository a paper ships, from its arXiv abstract page.

    Only a link the authors put there themselves. Guessing a repo from a title is
    how a plausible `owner/repo` that does not exist reaches a reading path, and
    that looks more checkable than a wrong paper title does.
    """
    aid = re.sub(r"v\d+$", "", (arxiv_id or "").strip())
    code, body = _get(f"https://arxiv.org/abs/{aid}")
    if code != 200 or not body:
        return None
    html = body.decode("utf-8", "ignore")
    seen = re.findall(r"github\.com/([\w.-]+/[\w.-]+)", html)
    for cand in seen:
        cand = cand.rstrip(".,);\"'").removesuffix(".git")
        if cand.lower().startswith(("arxiv/", "github/")):
            continue
        return cand
    return None


def enrich(entry: dict) -> dict:
    """Attach what applies to this entry, leaving what does not absent.

    Absent rather than null: a page renders a missing key as nothing, and renders
    a null as a gap the reader wonders about.
    """
    out = {}
    url = entry.get("url") or ""
    aid = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", url)
    if entry.get("kind") == "paper" and aid:
        c = citations(aid.group(1), entry.get("year"))
        out["citations"] = asdict(c)
        repo = repo_for_paper(aid.group(1))
        if repo:
            st = stars(repo)
            out["code"] = {"slug": repo, "url": f"https://github.com/{repo}",
                           "stars": asdict(st)}
    if entry.get("kind") == "repo":
        slug = re.sub(r"^https?://(www\.)?github\.com/", "", url).strip("/")
        slug = "/".join(slug.split("/")[:2])
        if slug.count("/") == 1:
            out["stars"] = asdict(stars(slug))
    return out


if __name__ == "__main__":
    import pathlib
    run = pathlib.Path(sys.argv[1]).resolve()
    p = run / "path.json" if run.is_dir() else run
    d = json.loads(p.read_text())
    n = 0

    def walk(entries):
        global n
        for e in entries:
            got = enrich(e)
            if got:
                e.update(got)
                n += 1
                bits = []
                if "citations" in got:
                    c = got["citations"]
                    bits.append(f"cites={c['value'] if c['value'] is not None else c['note']}")
                if "code" in got:
                    s = got["code"]["stars"]
                    bits.append(f"code={got['code']['slug']} "
                                f"({s['value'] if s['value'] is not None else s['note']}*)")
                if "stars" in got:
                    s = got["stars"]
                    bits.append(f"{s['value'] if s['value'] is not None else s['note']}*")
                print(f"  {e.get('number','?'):>5} {e.get('id',''):<16} " + "  ".join(bits))
            walk((e.get("subgroup") or {}).get("items") or [])

    walk(d.get("entries") or [])
    p.write_text(json.dumps(d, indent=1))
    print(f"\nenriched {n} entries")

"""Every response cached to disk on first fetch, replayed forever after.

This is what makes the build loop bearable. Selection and annotation get changed
forty times and neither should cost a traversal, so the network is paid for once
per URL and every later run of the same query reads from disk.

Two rules that come from measured failures elsewhere in this project.

Every outcome is a NAMED STATUS. `throttled` is never returned as absence: an
unauthenticated sweep once reported "no public repos" for 78 of 88 companies and
that read as a finding when it was a rate limit. A caller cannot distinguish
"nothing there" from "I was blocked" unless the difference is in the type.

Nothing that failed is cached. Caching a 429 turns a transient block into a
permanent hole that looks like an answer.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

CACHE = pathlib.Path(os.environ.get("PAPERS_CACHE",
                                    "~/.claude/papers/cache")).expanduser()
UA = "papers-skill/0.1 (reading path builder; contact via github)"

# arXiv asks for one request every three seconds and enforces it by delay.
MIN_INTERVAL = {"export.arxiv.org": 3.0, "api.semanticscholar.org": 1.1,
                "api.openalex.org": 0.15, "api.github.com": 0.8,
                "api2.openreview.net": 0.5}
_last: dict[str, float] = {}

OK, THROTTLED, MISSING, ERROR = "ok", "throttled", "missing", "error"


@dataclass
class Response:
    status: str            # ok | throttled | missing | error
    code: int
    body: bytes
    cached: bool = False
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == OK

    def json(self):
        return json.loads(self.body) if self.body else None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "ignore")


def _key(url: str) -> pathlib.Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:20]
    host = urllib.parse.urlparse(url).netloc.replace(":", "_") or "other"
    return CACHE / host / f"{h}.json"


def _throttle(host: str) -> None:
    gap = MIN_INTERVAL.get(host, 0.0)
    if not gap:
        return
    wait = gap - (time.monotonic() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.monotonic()


def get(url: str, *, headers: dict | None = None, timeout: int = 25,
        max_age: float | None = None, force: bool = False) -> Response:
    """Fetch with an on-disk cache. Only successes are cached."""
    path = _key(url)
    if not force and path.exists():
        try:
            rec = json.loads(path.read_text())
            fresh = max_age is None or (time.time() - rec["at"]) < max_age
            if fresh:
                return Response(OK, rec["code"], rec["body"].encode("utf-8", "ignore"),
                                cached=True)
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)

    host = urllib.parse.urlparse(url).netloc
    _throttle(host)
    h = {"User-Agent": UA, **(headers or {})}
    if host == "api.github.com" and os.environ.get("GITHUB_TOKEN"):
        h.setdefault("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")

    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body, code = r.read(), r.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            # Not absence. A caller that treats this as "nothing there" invents
            # a finding, which is the failure this whole branch exists to stop.
            return Response(THROTTLED, e.code, b"",
                            detail="rate limited; this is UNKNOWN, not absent")
        if e.code == 404:
            return Response(MISSING, 404, b"", detail="not found")
        return Response(ERROR, e.code, b"", detail=str(e.reason))
    except Exception as e:
        return Response(ERROR, 0, b"", detail=str(e)[:120])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "url": url, "code": code, "at": time.time(),
        "body": body.decode("utf-8", "ignore")}))
    return Response(OK, code, body)


def arxiv(ids) -> Response:
    q = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": len(ids)})
    return get(f"http://export.arxiv.org/api/query?{q}")


def openalex(path: str, **params) -> Response:
    return get(f"https://api.openalex.org{path}?{urllib.parse.urlencode(params)}")


def s2(path: str, **params) -> Response:
    h = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else None
    return get(f"https://api.semanticscholar.org/graph/v1{path}"
               f"?{urllib.parse.urlencode(params)}", headers=h)


def github(path: str) -> Response:
    return get(f"https://api.github.com/{path.lstrip('/')}", max_age=86400)


def openreview(**params) -> Response:
    return get(f"https://api2.openreview.net/notes?{urllib.parse.urlencode(params)}")


def cache_stats() -> dict:
    if not CACHE.exists():
        return {"files": 0, "bytes": 0, "hosts": {}}
    hosts: dict[str, int] = {}
    n = b = 0
    for p in CACHE.rglob("*.json"):
        n += 1
        b += p.stat().st_size
        hosts[p.parent.name] = hosts.get(p.parent.name, 0) + 1
    return {"files": n, "bytes": b, "hosts": hosts}

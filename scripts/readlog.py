"""What is already in your head, resolved from a folder of PDFs.

The reading log is not an exclusion list. It is the INITIAL STATE of the
selection. A paper you have read has already covered its share of the value
function, so the path starts where your knowledge stops rather than starting
over and deleting the overlaps.

The difference is visible on `protein folding`: AlphaFold 2 and 3 and Boltz are
in the folder, so the right first item is not AlphaFold 2, and it is also not
"AlphaFold 2, skipped". It is whatever now has the highest marginal value given
AlphaFold 2 is already in your head.

Four resolution strategies, cheapest first, and each is reported by name. A title
this could not resolve is reported rather than dropped, because a silently
dropped paper reappears on the reading path and that is exactly the failure that
makes the whole document lose credibility.

No network. Title-to-identifier resolution is a separate pass in verify.py, so
this stays runnable offline and fast enough to call on every run.
"""

from __future__ import annotations

import json
import re
import unicodedata
import zlib
from dataclasses import dataclass, asdict
from pathlib import Path

# Names that carry no information about the paper. A folder full of these
# resolves to nothing useful and should say so rather than emitting noise.
JUNK_STEMS = {"paper", "papers", "main", "arxiv", "pdf", "download", "untitled",
              "document", "preprint", "final", "draft", "1", "2", "v1", "v2"}

# Titles a PDF carries that are not the paper's title. Every one of these was
# observed in the real reading log. `about:blank` comes from printing a page to
# PDF in a browser and it is the dangerous shape: it looks like a resolved title
# rather than like an error, so it would reach the resolver as a search string
# and come back with something confidently wrong.
BAD_TITLES = re.compile(
    r"^\s*(?:"
    # These are prefixes: Word stamps "Microsoft Word - whatever.docx" and a
    # whole-string match misses every one of them.
    r"microsoft word\b.*|about:blank.*|printout\b.*|slide\s*\d*\b.*"
    r"|untitled.*|[\w\-.]+\.(?:pdf|docx?|tex|pptx?)"
    r"|output|template|manuscript|paper|main|draft|final"
    r")\s*$", re.I)

ARXIV_IN_NAME = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?")
SEP = re.compile(r"[_\-\s]+")
YEAR = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class Entry:
    path: str
    topic: str                  # the containing folder, which is your own taxonomy
    title: str | None
    arxiv: str | None
    how: str                    # arxiv-in-filename | pdf-metadata | first-page | filename
    confidence: str             # high | medium | low


def _slug_to_title(stem: str) -> str | None:
    """`alphafold3_supplementary` -> `alphafold3 supplementary`.

    Deliberately dumb. This is a search string for the resolver, not a title, and
    pretending otherwise is how a plausible wrong title gets welded to a real
    identifier later.
    """
    s = SEP.sub(" ", stem).strip()
    s = re.sub(r"\b(paper|preprint|pdf|arxiv)\b", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    if not s or s.lower() in JUNK_STEMS or len(s) < 4:
        return None
    return s


def _pdf_metadata_title(data: bytes) -> str | None:
    """Read /Title out of the PDF trailer without a PDF library.

    Most research PDFs carry either nothing or the LaTeX \\title here, and when
    it is present it is the most reliable source in this module. When it is the
    filename, or a TeX temp name, it is worthless, so those are rejected.
    """
    for m in re.finditer(rb"/Title\s*\((.*?)(?<!\\)\)", data[:400_000], re.S):
        raw = m.group(1)
        try:
            txt = raw.decode("utf-16" if raw[:2] in (b"\xfe\xff", b"\xff\xfe")
                             else "latin-1", errors="ignore")
        except Exception:
            continue
        txt = re.sub(r"\\([()\\])", r"\1", txt).strip()
        txt = unicodedata.normalize("NFKC", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) < 8 or BAD_TITLES.match(txt):
            continue
        if re.fullmatch(r"[\w\-.]+", txt):        # a filename, not a title
            continue
        if not re.search(r"[a-z]{3}", txt, re.I):  # identifiers and numbers only
            continue
        return txt
    return None


def _first_page_title(data: bytes) -> str | None:
    """Last resort: the largest text run near the top of page one.

    Only attempted on uncompressed or Flate streams, and it gives up quietly.
    A wrong title here is worse than none, so the bar is high and the result is
    always marked low confidence.
    """
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data[:1_500_000], re.S):
        blob = m.group(1)
        try:
            blob = zlib.decompress(blob)
        except Exception:
            pass
        if b"Tj" not in blob and b"TJ" not in blob:
            continue
        text = b" ".join(re.findall(rb"\((?:[^()\\]|\\.)*\)", blob[:20_000]))
        s = re.sub(r"\\([()\\])", r"\1",
                   text.decode("latin-1", errors="ignore")).replace("(", "").replace(")", "")
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) > 20:
            chunks.append(s)
        if chunks:
            break
    if not chunks:
        return None
    head = chunks[0][:200]
    head = re.split(r"\b(?:abstract|introduction)\b", head, flags=re.I)[0].strip()
    if len(head) <= 15 or BAD_TITLES.match(head):
        return None
    return head if _looks_like_prose(head) else None


def _looks_like_prose(s: str) -> bool:
    """Reject mojibake from a stream that decompressed but is not text.

    Observed in the real reading log: a PDF whose first stream yielded
    `½­qhµ=Yð0jàEü-pv­ÆÖ²ôs`. It passed the length check and would have gone to
    the resolver as a search string. A title is mostly letters and spaces, and
    anything that is not is a decoding artifact rather than a hard-to-read title.
    """
    if not s:
        return False
    letters = sum(c.isalpha() and c.isascii() for c in s)
    spaces = s.count(" ")
    if letters / len(s) < 0.75:
        return False
    if spaces < 1 or len(s) / (spaces + 1) > 14:   # no word breaks: not a title
        return False
    return bool(re.search(r"\b[a-z]{3,}\b", s, re.I))


def resolve_one(path: Path) -> Entry:
    stem = path.stem
    topic = path.parent.name

    m = ARXIV_IN_NAME.search(stem)
    if m:
        return Entry(str(path), topic, _slug_to_title(stem), m.group(1),
                     "arxiv-in-filename", "high")

    data = b""
    try:
        data = path.read_bytes()
    except OSError:
        pass

    if data:
        t = _pdf_metadata_title(data)
        if t:
            return Entry(str(path), topic, t, None, "pdf-metadata", "high")

    fromname = _slug_to_title(stem)
    if fromname:
        # The filename is your own naming, which is usually the paper's short
        # name (`mdlm`, `dreamerv3`). Short names resolve well and full titles
        # resolve better, so this is medium rather than high.
        return Entry(str(path), topic, fromname, None, "filename", "medium")

    if data:
        t = _first_page_title(data)
        if t:
            return Entry(str(path), topic, t, None, "first-page", "low")

    return Entry(str(path), topic, None, None, "unresolved", "low")


def scan(root: str | Path, *, exts=(".pdf",)) -> dict:
    """Walk the reading log. Report what resolved, how, and what did not."""
    root = Path(root).expanduser()
    entries, unresolved = [], []
    if not root.exists():
        return {"root": str(root), "exists": False, "entries": [],
                "unresolved": [], "by_topic": {}, "by_method": {}}

    for p in sorted(root.rglob("*")):
        if p.is_dir() or p.suffix.lower() not in exts or p.name.startswith("."):
            continue
        e = resolve_one(p)
        (entries if e.title or e.arxiv else unresolved).append(e)

    by_topic: dict[str, int] = {}
    by_method: dict[str, int] = {}
    for e in entries:
        by_topic[e.topic] = by_topic.get(e.topic, 0) + 1
        by_method[e.how] = by_method.get(e.how, 0) + 1

    return {
        "root": str(root), "exists": True,
        "entries": [asdict(e) for e in entries],
        "unresolved": [asdict(e) for e in unresolved],
        "by_topic": dict(sorted(by_topic.items(), key=lambda kv: -kv[1])),
        "by_method": by_method,
    }


def topics_matching(scanned: dict, terms) -> list[str]:
    """Which of your own folders bear on this query.

    Your folder names are your taxonomy, and they are a better prior about what
    you have read on a topic than any similarity score over titles.
    """
    terms = [t.lower() for t in terms if len(t) > 3]
    out = []
    for topic in scanned.get("by_topic", {}):
        flat = topic.replace("_", " ").lower()
        if any(t in flat or flat in t for t in terms):
            out.append(topic)
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(scan(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))

"""The paper graph: storage, dedup, path counting and scoring.

Everything here is mechanism. Which nodes justify expansion, which edges are
worth following, when a branch has gone off-target and when marginal yield has
collapsed are judgment, and they belong to the traversal layer, which is agentic.

The graph persists across runs. A paper found today seeds tomorrow, and the
second run over an adjacent topic is cheaper than the first. For reading this
compounds harder than it does for outbound, because one person's reading is a
single connected region and every run extends it.

Ported from outbound-sourcing/scripts/graph.py with the node kinds swapped and
two components added. The two ideas worth keeping verbatim are path_count over
hop count, and the hub penalty: reaching a node three independent ways is real
evidence of centrality, and expanding a node with four hundred edges reaches
everyone and distinguishes no one.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

NODE_KINDS = ("paper", "repo", "project", "person", "group", "idea")

# cites carries a context in `attrs`: builds_on | baseline | contrasts. An
# untyped citation edge is nearly worthless and a typed one carries most of the
# signal in the graph, so the context is required at insert for `cites`.
EDGE_KINDS = (
    "cites", "authored_by", "member_of", "implements", "depends_on",
    "reimplements", "evaluates_on", "covers", "disputes", "supersedes",
    "reviews", "builds_on", "requires",
)

CITE_CONTEXTS = ("builds_on", "baseline", "contrasts", "unknown")

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  key TEXT NOT NULL,
  weak_key TEXT NOT NULL DEFAULT '',
  display_name TEXT NOT NULL,
  external_ids TEXT NOT NULL DEFAULT '{}',
  attrs TEXT NOT NULL DEFAULT '{}',
  first_seen_run TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (kind, key)
);
CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY,
  src_id INTEGER NOT NULL,
  dst_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  weight REAL,
  year INTEGER,
  attrs TEXT NOT NULL DEFAULT '{}',
  source_url TEXT NOT NULL,
  quote TEXT,
  retrieved_at TEXT NOT NULL,
  UNIQUE (src_id, dst_id, kind, source_url)
);
CREATE TABLE IF NOT EXISTS paths (
  node_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  seed_node_id INTEGER,
  hops INTEGER NOT NULL,
  via TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (node_id, run_id, seed_node_id, via)
);
CREATE TABLE IF NOT EXISTS expansions (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL,
  node_id INTEGER,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  yielded INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collisions (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  key_a TEXT NOT NULL,
  key_b TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_weak ON nodes (kind, weak_key);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges (src_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges (dst_id, kind);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes (kind);
"""


class GraphError(ValueError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ------------------------------------------------------------------ identity

_ARXIV = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")


def arxiv_base(raw: str) -> str | None:
    """2405.12345v3 and arxiv.org/abs/2405.12345 are one work.

    Version suffixes are stripped deliberately. v1 and v3 of a contested paper
    can differ in exactly the part you care about, and that difference belongs
    in attrs on one node rather than in two nodes nobody can compare.
    """
    m = _ARXIV.search(raw or "")
    return m.group(1) if m else None


def norm_title(raw: str) -> str:
    return _WS.sub(" ", _PUNCT.sub(" ", (raw or "").lower())).strip()


def norm_person(raw: str) -> str:
    return _WS.sub(" ", _PUNCT.sub(" ", (raw or "").lower())).strip()


def node_key(kind: str, display_name: str, external: dict | None = None) -> str:
    """Canonical identity, strongest available identifier first."""
    ext = external or {}
    if kind == "paper":
        for k in ("arxiv", "doi", "openalex", "s2"):
            if ext.get(k):
                v = str(ext[k]).rsplit("/", 1)[-1].lower()
                return arxiv_base(v) or v if k == "arxiv" else v
        return norm_title(display_name)
    if kind == "repo":
        # owner/repo, case-insensitive. GitHub is case-preserving and
        # case-insensitive, so Owner/Repo and owner/repo are one repo.
        return (ext.get("github") or display_name).strip().strip("/").lower()
    if kind == "person":
        if ext.get("openalex"):
            return str(ext["openalex"]).rsplit("/", 1)[-1].lower()
        return norm_person(display_name)
    return norm_title(display_name)


def upsert_node(conn: sqlite3.Connection, kind: str, display_name: str, *,
                external: dict | None = None, attrs: dict | None = None,
                run_id: str | None = None) -> int:
    """Store a node, merging into an existing one where identity says to.

    The adopt rule, ported from outbound because the failure it prevents is the
    same one here wearing a different hat. A paper met first as an arXiv id and
    later as a bare title would otherwise become two nodes.

    It has to work in BOTH directions and the outbound version only covers one,
    which is a real bug I hit on the first smoke test. Id-then-title is at least
    as common as title-then-id, since a traversal meets a paper as a reference
    string before it resolves the identifier. So every node stores a weak key
    alongside its strong one, and lookup falls back to it.

    What stays strict: two nodes that BOTH carry external ids never merge. The
    collision is recorded instead, because merging those is a judgment call and
    a silent merge is unrecoverable.
    """
    if kind not in NODE_KINDS:
        raise GraphError(f"unknown node kind {kind!r}; use one of {NODE_KINDS}")
    ext = external or {}
    key = node_key(kind, display_name, ext)
    weak = norm_person(display_name) if kind == "person" else norm_title(display_name)
    row = conn.execute("SELECT * FROM nodes WHERE kind = ? AND key = ?",
                       (kind, key)).fetchone()

    if row is None and weak:
        alt = conn.execute(
            "SELECT * FROM nodes WHERE kind = ? AND (weak_key = ? OR key = ?)"
            " ORDER BY id LIMIT 1", (kind, weak, weak)).fetchone()
        if alt is not None:
            alt_ext = json.loads(alt["external_ids"] or "{}")
            if ext and alt_ext and not _ids_agree(ext, alt_ext):
                conn.execute(
                    "INSERT INTO collisions (kind, key_a, key_b, detail, created_at)"
                    " VALUES (?,?,?,?,?)",
                    (kind, key, alt["key"], f"both carry ids: {display_name!r}", utcnow()))
            else:
                if ext:
                    conn.execute("UPDATE nodes SET key = ? WHERE id = ?", (key, alt["id"]))
                row = alt

    if row is not None:
        merged_ext = {**json.loads(row["external_ids"] or "{}"), **ext}
        merged_attrs = {**json.loads(row["attrs"] or "{}"), **(attrs or {})}
        conn.execute("UPDATE nodes SET external_ids = ?, attrs = ?, updated_at = ?"
                     " WHERE id = ?",
                     (json.dumps(merged_ext), json.dumps(merged_attrs),
                      utcnow(), row["id"]))
        return int(row["id"])

    cur = conn.execute(
        "INSERT INTO nodes (kind, key, weak_key, display_name, external_ids, attrs,"
        " first_seen_run, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (kind, key, weak, display_name.strip(), json.dumps(ext), json.dumps(attrs or {}),
         run_id, utcnow(), utcnow()))
    return int(cur.lastrowid)


def _ids_agree(a: dict, b: dict) -> bool:
    """Two id sets belong to one work if every shared namespace matches.

    Disjoint namespaces are not disagreement: a node known by arXiv id and one
    known by DOI can be the same paper, and the title match is what suggested it.
    """
    shared = set(a) & set(b)
    if not shared:
        return True
    return all(str(a[k]).rsplit("/", 1)[-1].lower() == str(b[k]).rsplit("/", 1)[-1].lower()
               for k in shared)


def add_edge(conn: sqlite3.Connection, src_id: int, dst_id: int, kind: str, *,
             source_url: str, weight: float | None = None, year: int | None = None,
             context: str | None = None, quote: str | None = None,
             attrs: dict | None = None) -> bool:
    """Record a relationship.

    Refuses an edge with no absolute source. An unsourced relationship is an
    assertion, and assertions do not get put on a reading path. This is the one
    invariant enforced in code rather than in prose, for the same reason it is
    in outbound: everything downstream trusts the store.
    """
    if kind not in EDGE_KINDS:
        raise GraphError(f"unknown edge kind {kind!r}; use one of {EDGE_KINDS}")
    if not source_url or not str(source_url).startswith("http"):
        raise GraphError(f"edge {kind!r} needs an absolute source URL, got {source_url!r}")
    if src_id == dst_id:
        return False
    a = dict(attrs or {})
    if kind == "cites":
        ctx = context or a.get("context") or "unknown"
        if ctx not in CITE_CONTEXTS:
            raise GraphError(f"cites context must be one of {CITE_CONTEXTS}, got {ctx!r}")
        a["context"] = ctx
    elif context:
        a["context"] = context
    cur = conn.execute(
        "INSERT OR IGNORE INTO edges (src_id, dst_id, kind, weight, year, attrs,"
        " source_url, quote, retrieved_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (src_id, dst_id, kind, weight, year, json.dumps(a), source_url, quote, utcnow()))
    return cur.rowcount > 0


def record_path(conn: sqlite3.Connection, node_id: int, run_id: str, *,
                seed_node_id: int | None, hops: int, via: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO paths (node_id, run_id, seed_node_id, hops, via,"
        " created_at) VALUES (?,?,?,?,?,?)",
        (node_id, run_id, seed_node_id, hops, via, utcnow()))


def path_count(conn: sqlite3.Connection, node_id: int) -> int:
    """Independent routes to a node. Three routes means more central than one."""
    return conn.execute(
        "SELECT COUNT(DISTINCT COALESCE(seed_node_id,0) || '|' || via)"
        " FROM paths WHERE node_id = ?", (node_id,)).fetchone()[0]


def degree(conn: sqlite3.Connection, node_id: int, kind: str | None = None) -> int:
    q = ("SELECT COUNT(*) FROM edges WHERE (src_id = ? OR dst_id = ?)"
         + (" AND kind = ?" if kind else ""))
    return conn.execute(q, (node_id, node_id) + ((kind,) if kind else ())).fetchone()[0]


def log_expansion(conn: sqlite3.Connection, run_id: str, node_id: int | None,
                  decision: str, reason: str, yielded: int = 0) -> None:
    """Every expansion decision, including the refusals.

    This is what answers "why is X not in here" without re-running anything. A
    decision not to expand, with its reason, is worth as much as a decision to.
    """
    conn.execute("INSERT INTO expansions (run_id, node_id, decision, reason,"
                 " yielded, created_at) VALUES (?,?,?,?,?,?)",
                 (run_id, node_id, decision, reason, yielded, utcnow()))


def covered_ideas(conn: sqlite3.Connection, node_ids) -> dict[int, float]:
    """Best coverage weight per idea node across a set of items.

    Best rather than sum: a second paper covering an idea the first already
    covered adds only what it adds beyond the first. This is what makes the
    value function submodular, and the monotone-coverage test depends on it.
    """
    out: dict[int, float] = {}
    ids = list(node_ids)
    if not ids:
        return out
    q = ("SELECT dst_id, weight FROM edges WHERE kind = 'covers' AND src_id IN"
         f" ({','.join('?' * len(ids))})")
    for r in conn.execute(q, ids):
        w = 1.0 if r["weight"] is None else float(r["weight"])
        if w > out.get(r["dst_id"], 0.0):
            out[r["dst_id"]] = w
    return out


# ------------------------------------------------------------------ scoring


@dataclass
class Score:
    total: float
    parts: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# Beyond this a node is a hub, not a lead. Tuned lower than outbound's 60
# because citation degree accumulates faster than coauthorship does, and the
# nodes this is meant to catch (a canonical benchmark, pytorch/pytorch, a
# survey everyone cites) sit well above it.
HUB_DEGREE = 40


def score_node(conn: sqlite3.Connection, node_id: int, *, hops: int,
               marginal_coverage: float = 0.0, depth_payoff: float = 0.5,
               latest_year: int | None = None, now: int | None = None) -> Score:
    """Rank a frontier node for expansion. Never filter to one shape.

    Every component is explainable and the weights are a starting point to be
    corrected against a real run, the way outbound's `topic` weight was. Note
    what is NOT here: citation count and star count. Both are available and both
    rank a benchmark above a dense theory paper, which is the inversion this
    whole skill exists to avoid. Centrality is measured by path_count instead.
    """
    year = now or datetime.now(timezone.utc).year
    paths = path_count(conn, node_id)
    deg = degree(conn, node_id)

    parts = {
        # Closer is better, but a 2-hop reached three ways beats a 1-hop reached once.
        "proximity": 1.0 / (1 + hops),
        "corroboration": min(1.0, math.log1p(paths) / math.log(4)),
        "coverage": max(0.0, min(1.0, marginal_coverage)),
        "depth_payoff": max(0.0, min(1.0, depth_payoff)),
        "recency": 0.0 if not latest_year else max(0.0, 1 - (year - latest_year) / 10),
    }
    weights = {"proximity": 0.8, "corroboration": 2.0, "coverage": 1.5,
               "depth_payoff": 1.3, "recency": 1.2}
    total = sum(parts[k] * weights[k] for k in parts) / sum(weights.values())

    notes = []
    if deg > HUB_DEGREE:
        penalty = min(0.45, 0.15 * math.log1p(deg / HUB_DEGREE))
        total -= penalty
        notes.append(f"hub penalty -{penalty:.2f} ({deg} edges): expanding this reaches "
                     f"everything and distinguishes nothing")
    if paths >= 3:
        notes.append(f"reached by {paths} independent routes")
    return Score(round(max(0.0, total), 3),
                 {k: round(v, 3) for k, v in parts.items()}, notes)

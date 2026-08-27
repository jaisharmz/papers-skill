"""Mutation audit: break the code on purpose, see which tests notice.

A test that fails for no mutation is not testing anything. A mutation that no
test catches is a behaviour nobody is guarding. Both are worth knowing and
neither is visible from reading the suite.

Every mutation below is a bug the code could plausibly have: an inverted
comparison, a dropped guard, a wrong default. Not random character noise.

    python3 tests/mutate.py            # audit
    python3 tests/mutate.py --verbose  # per-mutation detail
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (file, find, replace, what this bug would be)
MUTATIONS = [
    # --- ordering: the prefix guarantee ---
    ("scripts/ordering.py", "if w > out.get(idea, 0.0):", "if True:",
     "coverage takes the last weight instead of the best, breaking submodularity"),
    ("scripts/ordering.py", "out[idea] = w\n        for idea, (partner, w) in it.pair_covers.items():\n            if partner in present",
     "out[idea] = w\n        for idea, (partner, w) in it.pair_covers.items():\n            if True",
     "pair coverage lands without its partner, so one side claims the disagreement"),
    ("scripts/ordering.py", "return all(r in done for r in item.requires)", "return True",
     "the prerequisite gate stops gating"),
    ("scripts/ordering.py", "(gain * (0.4 + 0.6 * item.depth_payoff)) / max(item.cost_hours, MIN_COST)",
     "gain / max(item.cost_hours, MIN_COST)",
     "depth payoff stops damping, so a survey wins position one"),
    # NOTE: removing the `needed` guard from split_spine is an EQUIVALENT mutant
    # under the current design. The orphan reinstatement puts an unprotected item
    # back at its original position, so the two paths agree on output. The guard
    # stays because it expresses the intent directly and the reinstatement is a
    # backstop rather than the rule, but it is honest to say no test can tell
    # them apart and no test pretends to.
    ("scripts/ordering.py", "if n == 0 or p.marginal > 1e-9 or p.item.id in needed]",
     "if True]", "items stranded at zero value by the reorder stay on the path"),
    ("scripts/ordering.py", "if not v or v in seen:\n        return 0.0", "if not v:\n        return 0.0",
     "a subgroup repeats the same approach twice"),
    ("scripts/ordering.py", "gain, landed = marginal(p.item, cov, weights, done)\n        p.position, p.marginal = n, round(gain, 4)",
     "gain, landed = marginal(p.item, {}, weights, done)\n        p.position, p.marginal = n, round(gain, 4)",
     "recompute measures against an empty prefix instead of the real one"),
    ("scripts/ordering.py", "if orphans:", "if False:",
     "a demoted item with no subgroup home is silently dropped"),
    ("scripts/ordering.py", "elif v in seen:", "elif False:",
     "the duplicate-approach check inside a subgroup stops firing"),

    ("scripts/ordering.py", "if blocked:", "if False:",
     "a zero-value prerequisite blocks its whole downstream chain"),
    ("scripts/ordering.py", "or p.item.id in needed]", "]",
     "pruning drops a prerequisite a later project needs"),
    ("scripts/ordering.py", "if cands and (best is None or len(cands) > len(best[1])):",
     "if cands and best is None:",
     "a subgroup forms on the first idea rather than the one with companions"),
    ("scripts/readlog.py", "if letters / len(s) < 0.75:", "if False:",
     "mojibake passes the prose check"),
    ("scripts/critique.py", "elif t and not g.get(\"thesis_source\"):", "elif False:",
     "a group thesis with no source URL ships"),

    # --- graph: identity and sourcing ---
    ("scripts/pgraph.py", 'if not source_url or not str(source_url).startswith("http"):',
     "if False:", "unsourced edges are accepted into the store"),
    ("scripts/pgraph.py", "if row is None and weak:", "if False:",
     "the adopt rule stops merging, so one paper becomes two nodes"),
    ("scripts/pgraph.py", "if ext and alt_ext and not _ids_agree(ext, alt_ext):",
     "if False:", "two papers with different arXiv ids merge silently"),
    ("scripts/pgraph.py", "if ctx not in CITE_CONTEXTS:", "if False:",
     "a citation edge is stored with no context, so builds_on and baseline blur"),
    ("scripts/pgraph.py", "if w > out.get(r[\"dst_id\"], 0.0):", "if True:",
     "graph-side coverage sums instead of taking the best"),
    ("scripts/pgraph.py", "if deg > HUB_DEGREE:", "if False:",
     "hubs stop being penalised, so expanding reaches everything"),

    # --- verify: the fabricated identifier ---
    ("scripts/verify.py", "ok = score >= MATCH_FLOOR", "ok = True",
     "a plausible title on a real arXiv id passes verification"),
    ("scripts/verify.py", '"throttled" if code in (429, 0) else "not-found"',
     '"not-found"', "a rate-limited arXiv call is reported as not-found"),
    ("scripts/verify.py", "return 2 * p * r / (p + r)", "return 1.0",
     "title similarity always matches"),

    # --- readlog: what is already read ---
    ("scripts/readlog.py", "if len(txt) < 8 or BAD_TITLES.match(txt):", "if False:",
     "about:blank and other junk PDF titles reach the resolver"),
    ("scripts/readlog.py", "return head if _looks_like_prose(head) else None", "return head",
     "mojibake from a binary stream is emitted as a paper title"),
    ("scripts/readlog.py", "(entries if e.title or e.arxiv else unresolved).append(e)",
     "entries.append(e)", "unresolvable files are counted as resolved"),

    # --- fetch: the cache and the status semantics ---
    ("scripts/fetch.py", "if e.code in (403, 429):", "if False:",
     "a rate limit is returned as an ordinary error rather than throttled"),
    ("scripts/fetch.py", "if not force and path.exists():", "if False:",
     "the cache never replays, so every run pays full price"),
    ("scripts/fetch.py", "path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text",
     "path.parent.mkdir(parents=True, exist_ok=True)\n    _ = lambda *a: None; _",
     "successes are never cached"),

    # --- critique / checkpage: the graders themselves ---
    ("scripts/critique.py", "if missing or vague:", "if False:",
     "entries with no layer three ship"),
    ("scripts/critique.py", "if bad:\n        return _c(\"repo entries name a file or a function\", FAIL",
     "if False:\n        return _c(\"repo entries name a file or a function\", FAIL",
     "a repo entry that is only a URL ships"),
    ("scripts/critique.py", "if t and PLACEHOLDER.search(str(t)):", "if False:",
     "a placeholder group thesis ships"),
    ("scripts/critique.py", "un = (conf or {}).get(\"unverified\") or []\n    if not un:",
     "un = (conf or {}).get(\"unverified\") or []\n    if False:",
     "an empty could-not-verify list ships"),
    ("scripts/checkpage.py", "if not m.group(2) and m.group(1) not in defined",
     "if False", "a custom property with no definition and no fallback ships"),
    ("scripts/checkpage.py", "leaked = sorted((shared & set(IDENTITY_PROPS)) - overridden)",
     "leaked = []", "a reused tag inheriting the shared look ships"),
    ("scripts/checkpage.py", "FAIL if (hides and displayed and not guarded) else OK",
     "OK", "a display rule that defeats [hidden] ships"),
    ("scripts/checkpage.py", 'if "localStorage" not in js:', "if False:",
     "a page missing the features page.md promises ships"),
]


def run_suite() -> set[str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--tb=no",
                        "-p", "no:cacheprovider"],
                       cwd=ROOT, capture_output=True, text=True)
    # pytest prints "FAILED tests/x.py::test_y - ...". An earlier version of this
    # regex required the line to START with tests/, matched nothing, and reported
    # that every test in the suite caught every mutation and also nothing at all.
    # A broken audit is worse than no audit: it condemns good tests.
    return set(re.findall(r"^(?:FAILED|ERROR)\s+(tests/\S+::\S+)", r.stdout, re.M))


def main() -> int:
    verbose = "--verbose" in sys.argv
    baseline = run_suite()
    if baseline:
        print("suite is not green before mutating:", sorted(baseline)[:3])
        return 1

    total = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q",
                            "-p", "no:cacheprovider"], cwd=ROOT,
                           capture_output=True, text=True).stdout
    all_tests = set(re.findall(r"^(tests/\S+::\S+)", total, re.M))

    killers: dict[str, set[str]] = {t: set() for t in all_tests}
    survived = []
    for path, find, repl, what in MUTATIONS:
        f = ROOT / path
        src = f.read_text()
        if find not in src:
            print(f"  SKIP (pattern gone) {path}: {what}")
            continue
        f.write_text(src.replace(find, repl))
        try:
            caught = run_suite()
        finally:
            f.write_text(src)
        if not caught:
            survived.append(what)
            print(f"  SURVIVED  {what}")
        else:
            for t in caught:
                killers.setdefault(t, set()).add(what)
            if verbose:
                print(f"  killed by {len(caught):>2}  {what}")

    dead = sorted(t for t, k in killers.items() if not k)
    print(f"\n{len(MUTATIONS)} mutations, {len(survived)} survived uncaught")
    print(f"{len(all_tests)} tests, {len(dead)} caught nothing")
    for t in dead:
        print(f"    catches nothing: {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

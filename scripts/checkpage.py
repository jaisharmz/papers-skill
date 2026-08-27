"""Static checks on a built report.html, before anyone opens it.

build_page.py checks tag balance and em dashes and that is all it ever checked,
which is how a page can pass its build and still render wrong. These are the
failures that produce a page that looks broken rather than one that errors:

  a var(--x) with no definition and no fallback     -> silently transparent or
                                                       inherits the wrong colour
  a class in the HTML with no rule                  -> unstyled block
  a rule in the CSS matching nothing in the HTML    -> dead weight, or a typo
  a selector the shared JS binds to but never finds -> dead interaction
  a token defined only inside a media query         -> breaks in one theme only

None of these throw. They are all "the page came out ugly", which is exactly
the class of bug that needs a checker rather than an eye.
"""

from __future__ import annotations

import pathlib
import re
import sys
from dataclasses import dataclass, field

OK, WARN, FAIL = "ok", "warn", "FAIL"

VAR_USE = re.compile(r"var\(\s*(--[\w-]+)\s*(,)?")
VAR_DEF = re.compile(r"(--[\w-]+)\s*:")
CLASS_IN_HTML = re.compile(r'class="([^"]+)"')
CLASS_IN_CSS = re.compile(r"\.([A-Za-z][\w-]*)")
ID_IN_HTML = re.compile(r'id="([^"]+)"')
JS_SELECT = re.compile(r"""querySelector(?:All)?\(\s*['"]([^'"]+)['"]""")
JS_BY_ID = re.compile(r"""getElementById\(\s*['"]([^'"]+)['"]""")

# Elements the shared stylesheet styles by tag, so a class is not required.
BARE_OK = {"wrap", "viz-root", "eyebrow", "verdict", "runbar"}

# Classes the page's own script adds at runtime. Static analysis cannot see them
# and reporting them as dead rules trains the reader to ignore this check, which
# is worse than not running it.
JS_APPLIED = {"done", "next", "on", "open"}


@dataclass
class Finding:
    rule: str
    status: str
    detail: str = ""
    items: list = field(default_factory=list)


def _f(rule, status, detail="", items=()):
    return Finding(rule, status, detail, list(items))


def split_css(css: str) -> tuple[str, str]:
    """Rules inside @media / @supports blocks vs rules at top level."""
    inside, depth, out_top, out_med = [], 0, [], []
    i = 0
    while i < len(css):
        if css.startswith("@media", i) or css.startswith("@supports", i):
            j, d = css.index("{", i), 0
            k = j
            while k < len(css):
                if css[k] == "{":
                    d += 1
                elif css[k] == "}":
                    d -= 1
                    if d == 0:
                        break
                k += 1
            out_med.append(css[i:k + 1])
            i = k + 1
            continue
        out_top.append(css[i])
        i += 1
    return "".join(out_top), "\n".join(out_med)


# Properties that visibly change a heading's identity. If a shared rule sets one
# on a bare tag and a page rule reuses that tag without resetting it, the element
# renders as whatever the shared stylesheet thought that tag was for.
IDENTITY_PROPS = ("font-family", "text-transform", "letter-spacing", "font-size",
                  "color", "border-bottom", "font-weight")


def rules_for(css: str, selector: str) -> list[str]:
    out = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sels = [s.strip() for s in m.group(1).split(",")]
        if any(s == selector or s.endswith(" " + selector) for s in sels):
            out.append(m.group(2))
    return out


def props(blocks) -> set[str]:
    return {m.group(1) for b in blocks for m in re.finditer(r"([a-z-]+)\s*:", b)}


def check_tag_collisions(css: str, body: str) -> Finding:
    """A bare tag the shared stylesheet already owns, reused for something else.

    The shared sheet styles h2 as a section label: monospace, uppercase, 0.72rem,
    letter-spaced, muted, ruled. The first page reused h2 for entry titles and
    overrode only font-size, so its headline rendered as a tiny uppercase
    monospace label. Nothing errored and no class was missing. Only looking at it
    caught it, which is why it is a check now.
    """
    bad = []
    for tag in ("h1", "h2", "h3", "h4", "p", "li", "summary"):
        shared = props(rules_for(css, tag))
        if not shared:
            continue
        # page-scoped rules that reuse the tag under a class
        scoped = [m.group(2) for m in re.finditer(r"([^{}]*\.[\w-]+\s+" + tag +
                                                  r"[^{}]*)\{([^}]*)\}", css)]
        if not scoped:
            continue
        overridden = props(scoped)
        leaked = sorted((shared & set(IDENTITY_PROPS)) - overridden)
        if leaked:
            bad.append(f"{tag}: a scoped rule reuses it but does not reset "
                       f"{', '.join(leaked)}, so it inherits the shared look")
    return _f("reused tags reset the shared styling they inherit",
              FAIL if bad else OK, f"{len(bad)} collisions", bad)


def check(path: pathlib.Path) -> list[Finding]:
    html = path.read_text()
    css = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.S))
    js = "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
    body = re.sub(r"<style>.*?</style>|<script>.*?</script>", "", html, flags=re.S)

    out: list[Finding] = []

    # 1. every custom property used has a definition or a fallback
    defined = set(VAR_DEF.findall(css))
    missing = sorted({m.group(1) for m in VAR_USE.finditer(css)
                      if not m.group(2) and m.group(1) not in defined})
    out.append(_f("custom properties resolve", FAIL if missing else OK,
                  f"{len(missing)} used with no definition and no fallback", missing))

    # 2. a property defined ONLY inside a media query breaks in the other theme
    top, med = split_css(css)
    top_def, med_def = set(VAR_DEF.findall(top)), set(VAR_DEF.findall(med))
    theme_only = sorted(med_def - top_def)
    out.append(_f("no property defined only in a media query",
                  FAIL if theme_only else OK,
                  "these exist in one theme and vanish in the other", theme_only))

    # 3. every class in the markup has a rule
    used = set()
    for m in CLASS_IN_HTML.finditer(body):
        used.update(m.group(1).split())
    styled = set(CLASS_IN_CSS.findall(css))
    unstyled = sorted(used - styled - BARE_OK)
    out.append(_f("every class in the markup is styled", FAIL if unstyled else OK,
                  f"{len(unstyled)} render unstyled", unstyled))

    # 4. rules that match nothing. Usually a typo or a component that got cut.
    page_only = {c for c in styled if c not in used}
    # The shared stylesheet carries components this page does not use, which is
    # expected. Only flag classes this skill's own block introduced.
    mine = set(CLASS_IN_CSS.findall(css.split("/* --- the stack")[-1])) if "the stack" in css else set()
    dead = sorted((mine & page_only) - JS_APPLIED - set(re.findall(r'classList\.(?:toggle|add)\(\s*"([\w-]+)"', js)))
    out.append(_f("this skill's own rules all match something", WARN if dead else OK,
                  f"{len(dead)} rules match nothing in the markup", dead))

    # 5. the shared JS binds to selectors this page may not have
    ids = set(ID_IN_HTML.findall(body))
    dangling = []
    for sel in JS_SELECT.findall(js):
        base = sel.lstrip(".#").split(" ")[0].split("[")[0].split(":")[0]
        if sel.startswith(".") and base not in used:
            dangling.append(sel)
        elif sel.startswith("#") and base not in ids:
            dangling.append(sel)
    dangling += [f"#{i}" for i in JS_BY_ID.findall(js) if i not in ids]
    out.append(_f("shared JS finds what it binds to", WARN if dangling else OK,
                  f"{len(dangling)} selectors match nothing on this page",
                  sorted(set(dangling))))

    # 6. structural sanity the build script does not cover
    problems = []
    if "<title>" not in html:
        problems.append("no <title>, so the artifact gets named by filename")
    if not re.search(r'<meta charset', html):
        problems.append("no charset declaration")
    empty = re.findall(r"<(section|article|details)[^>]*>\s*</\1>", body)
    if empty:
        problems.append(f"{len(empty)} empty section/article/details elements")
    nested_a = re.findall(r"<a\b[^>]*>(?:(?!</a>).)*<a\b", body, re.S)
    if nested_a:
        problems.append(f"{len(nested_a)} nested <a> elements, which browsers unnest")
    if body.count("<h1") != 1:
        problems.append(f"{body.count('<h1')} <h1> elements, expected exactly 1")
    out.append(_f("structure", FAIL if problems else OK, "; ".join(problems)))
    out.append(check_tag_collisions(css, body))

    # An element the page hides with the `hidden` attribute, that also carries an
    # explicit display. `[hidden] { display: none }` is a UA rule at low
    # specificity and any class rule setting display beats it, so the element
    # stays visible and the feature looks broken while the script is fine.
    hides = "hidden" in js or "hidden=" in body
    guarded = re.search(r"\[hidden\][^{]*\{[^}]*display\s*:\s*none", css)
    displayed = sorted({m.group(1).strip() for m in
                        re.finditer(r"([^{}]*\[data-track\][^{}]*|[^{}]*\.spine\s+li[^{}]*)"
                                    r"\{[^}]*display\s*:", css)})
    out.append(_f("hidden elements can actually be hidden",
                  FAIL if (hides and displayed and not guarded) else OK,
                  ("these set display and would defeat [hidden]"
                   if (hides and displayed and not guarded) else ""), displayed))

    # Internal keys leaking into reader-facing prose. The first page rendered
    # "jepa_pos is attacked by critique" in its lineage section: the run's own
    # item ids shown to a reader.
    #
    # Scoped to the generated relation lists rather than to all visible text. An
    # unscoped version flagged "dual" (the word, in "dual control"), "tinyworlds"
    # and "r2dreamer" (real repository names a reader should see), which is the
    # false-positive rate that trains someone to ignore a check.
    dataids = set(re.findall(r'data-id="([^"]+)"', body))
    generated = " ".join(re.findall(r'<ul class="lineage">(.*?)</ul>', body, re.S)
                         + re.findall(r'<div class="cov">(.*?)</div>', body, re.S))
    vis = re.sub(r"<[^>]+>", " ", generated)
    # The boundary has to exclude / . @ as well as word characters, or the id
    # `tinyworlds` matches inside the title `AlmondGod/tinyworlds` and the check
    # fails a correctly rendered row. Only a bare standalone token is a leak.
    B = r"[\w/@.-]"
    leaked = sorted({i for i in dataids
                     if re.search(r"(?<!" + B + ")" + re.escape(i) + r"(?!" + B + ")", vis)})
    out.append(_f("no internal identifiers in generated relation lists",
                  FAIL if leaked else OK,
                  f"{len(leaked)} item ids rendered instead of titles", leaked))

    # 7. features page.md promises. Every one of these was missing on the first
    # real page and none of them errored: the page just quietly did less than the
    # reference document says it does, which is the failure mode a checker exists
    # for. Each entry here is a line in references/page.md.
    promised = []
    if "localStorage" not in js:
        promised.append("marking an item done: page.md says the stack advances and "
                        "the coverage bar lights up. No storage, no handler, nothing.")
    if not re.search(r'data-track|class="tracks"', body):
        promised.append("the three track filters (papers / repos / projects)")
    if 'class="cov"' in body and "addEventListener" not in js:
        promised.append("the coverage bar is static, so it can never reflect progress")
    out.append(_f("features page.md promises are present", FAIL if promised else OK,
                  f"{len(promised)} promised and absent", promised))

    # 8. every entry carries its role chip and its group, at every depth. The
    # first page rendered both only on the top two entries and dropped them for
    # the other fifteen, which loses the one thing the reader asked for by name.
    lead_like = len(re.findall(r'<article', body))
    spine = len(re.findall(r'<li><span class="n">', body))
    total = lead_like + spine
    role_chips = len(re.findall(r'class="chip (?!paper|repo|project)[\w-]+"', body))
    grouped = len(re.findall(r'class="group-chip"', body)) + len(re.findall(r'class="grp"', body))
    gaps = []
    if total and role_chips < total:
        gaps.append(f"{total - role_chips} of {total} entries show no role or archetype chip")
    if total and grouped < total:
        gaps.append(f"{total - grouped} of {total} entries show no group")
    out.append(_f("every entry shows its role and its group", FAIL if gaps else OK,
                  "; ".join(gaps)))

    # 9. an empty or trailing-space class attribute means a conditional class was
    # interpolated as "". Harmless to render and a reliable sign of a bug above it.
    sloppy = re.findall(r'class="[^"]*\s"|class=""', body)
    out.append(_f("no empty or trailing-space class attributes",
                  WARN if sloppy else OK, f"{len(sloppy)} found",
                  sorted(set(sloppy))[:5]))

    # 10. dead JS: the shared script binds to a component this page does not have.
    #     It is inert rather than broken, but it ships bytes and it means the page
    #     is carrying another page's behaviour.
    if ".cell" in js and "cell" not in used:
        out.append(_f("no inert borrowed behaviour", WARN,
                      "the shared report.js drives the openness map, which this page "
                      "does not render. Its handlers bind to nothing."))
    else:
        out.append(_f("no inert borrowed behaviour", OK))

    # Year and phrase on every row. Both exist so a reader can decide whether to
    # open something without opening it, and a row missing either puts the
    # deliberation back that this page exists to remove.
    rows = re.findall(r'<li id="e-[^"]*"[^>]*>(.*?)</li>', body, re.S)
    noyear = sum(1 for r in rows if 'class="yr"' not in r)
    nophrase = sum(1 for r in rows if 'class="ph"' not in r)
    gaps = []
    if rows and nophrase:
        gaps.append(f"{nophrase} of {len(rows)} rows show no phrase")
    if rows and noyear > sum(1 for r in rows if 'chip project' in r):
        gaps.append(f"{noyear} of {len(rows)} rows show no year")
    out.append(_f("every row shows a year and a phrase", FAIL if gaps else OK,
                  "; ".join(gaps)))

    # Depth has to be collapsed by default, or the simple view is not simple.
    subs = re.findall(r'<details class="subs"( open)?>', body)
    openby = sum(1 for s in subs if s.strip())
    out.append(_f("subgroups are collapsed by default",
                  FAIL if openby else OK,
                  f"{openby} of {len(subs)} start open" if openby else
                  f"{len(subs)} groups, all closed"))

    # A subgroup label that states a count contradicting the count beside it.
    # "two more positions" over a group of one is the kind of small wrongness that
    # makes a reader stop trusting the numbers, and it is trivially checkable.
    WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    clash = []
    for n, lab in re.findall(r'<span class="subn">(\d+)</span>\s*([^<]+)</summary>', body):
        for w, v in WORDNUM.items():
            if re.search(r"\b" + w + r"\b", lab, re.I) and v != int(n):
                clash.append(f"{lab.strip()!r} sits above a count of {n}")
    out.append(_f("subgroup labels agree with their counts",
                  FAIL if clash else OK, f"{len(clash)} disagree", clash))

    # Every control the page renders has a handler, and every handler has a
    # control. A button with no listener and a listener with no button both look
    # identical to a working page in a screenshot, and the embedded artifact
    # viewer does not always let a click through to confirm otherwise.
    controls = set(re.findall(r'class="(track|tick|depthtoggle)"', body))
    wired = []
    for c in sorted(controls):
        if f'"{c}"' not in js and f"'{c}'" not in js and f".{c}" not in js:
            wired.append(f"{c} is rendered but nothing in the script binds to it")
    for c in set(re.findall(r'closest\(["\']\.([\w-]+)["\']\)', js)) | \
             set(re.findall(r'querySelector(?:All)?\(["\']\.([\w-]+)', js)):
        if c not in controls and c not in used:
            wired.append(f"the script binds .{c}, which this page never renders")
    for target in re.findall(r'querySelectorAll\(["\'](details\.[\w-]+)["\']', js):
        if target.split(".")[-1] not in used:
            wired.append(f"the script drives {target}, which this page never renders")
    out.append(_f("every control is wired and every handler has a control",
                  FAIL if wired else OK, f"{len(wired)} mismatches", wired))

    # A disclosure whose summary does not say what is inside it is a mystery box.
    vague = [s for s in re.findall(r'<summary>(.*?)</summary>', body, re.S)
             if len(re.sub(r"<[^>]+>", "", s).split()) < 3]
    out.append(_f("every disclosure says what is inside it",
                  WARN if vague else OK, f"{len(vague)} summaries under three words",
                  [re.sub(r"<[^>]+>", "", v).strip()[:40] for v in vague]))

    # overflow risk: wide fixed widths inside the page column
    # Widths inside an @media condition are breakpoints, not element widths.
    # Reporting `max-width:760px` from a media query as an overflow risk is the
    # kind of false positive that makes a checker get ignored.
    css_no_media = re.sub(r"@media[^{]*", "", css)
    wide = re.findall(r"(?:min-)?width:\s*(\d{3,})px", css_no_media)
    risky = sorted({w for w in wide if int(w) > 700})
    out.append(_f("no fixed widths wider than the column", WARN if risky else OK,
                  f"{len(risky)} fixed widths over 700px", risky))

    return out


def report(findings) -> int:
    order = {FAIL: 0, WARN: 1, OK: 2}
    fails = 0
    for f in sorted(findings, key=lambda f: order[f.status]):
        if f.status == OK:
            continue
        fails += f.status == FAIL
        print(f"{f.status:<5} {f.rule}" + (f": {f.detail}" if f.detail else ""))
        for i in f.items[:12]:
            print(f"        {i}")
        if len(f.items) > 12:
            print(f"        ... and {len(f.items) - 12} more")
    n_ok = sum(1 for f in findings if f.status == OK)
    print(f"\n{n_ok}/{len(findings)} clean, {fails} blocking")
    return fails


if __name__ == "__main__":
    sys.exit(1 if report(check(pathlib.Path(sys.argv[1]).resolve())) else 0)

"""path.json to report.html. The presentation is code so it cannot drift.

Never hand-author CSS in a run and never restyle for a topic. An earlier version
of industry-research described its design in prose and asked each run to build
from the description; the pages drifted immediately and two runs of one skill
stopped being readable by the same reader. So this file is the design, and only
the data varies.

The stylesheet is industry-research's, unchanged, plus a small block for the
components this page has and that one does not: the stack, the entry, the group
chip, the lineage strip and the coverage bar.

The layout IS the argument. Position one at full size, position two at half
weight, the rest as a spine. If you do one thing tonight, this one. A page that
renders twelve equal entries has thrown away the entire selection and handed the
reader back the deliberation this skill exists to end.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
SHARED = SKILL.parent / "industry-research" / "assets"

KIND_LABEL = {"paper": "paper", "repo": "code", "project": "project"}

PAGE_JS = r"""
// Marking an item done, and the coverage bar that reflects it. references/page.md
// promises both; the first published page shipped neither and nothing errored,
// which is why checkpage.py now fails a build that omits them.
//
// Storage is per-viewer and per-artifact origin, and every access is wrapped:
// a private window, cleared site data or a thumbnail capture all throw or return
// empty, and the page has to render correctly with no stored value.
(function () {
  var KEY = "papers:done:" + location.pathname;
  function load() {
    try { return new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); }
    catch (_) { return new Set(); }
  }
  function save(s) {
    try { localStorage.setItem(KEY, JSON.stringify([].slice.call(s))); } catch (_) {}
  }
  var done = load();

  function paint() {
    var items = document.querySelectorAll("[data-id]");
    [].forEach.call(items, function (el) {
      el.classList.toggle("done", done.has(el.getAttribute("data-id")));
    });
    var cells = document.querySelectorAll(".cov i"), lit = 0;
    [].forEach.call(cells, function (c) {
      var by = (c.getAttribute("data-by") || "").split(",").filter(Boolean);
      var on = c.getAttribute("data-prior") === "1" ||
               by.some(function (id) { return done.has(id); });
      c.classList.toggle("on", on);
      if (on) lit++;
    });
    var n = document.querySelector(".covcount");
    if (n) n.textContent = String(lit);
    resume();
    var next = document.querySelector("[data-id]:not(.done)");
    [].forEach.call(document.querySelectorAll("[data-id]"), function (el) {
      el.classList.toggle("next", el === next);
    });
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest(".tick");
    if (b) {
      var host = b.closest("[data-id]"), id = host && host.getAttribute("data-id");
      if (!id) return;
      done.has(id) ? done.delete(id) : done.add(id);
      save(done); paint(); return;
    }
    var f = ev.target.closest && ev.target.closest(".track");
    if (!f) return;
    var want = f.getAttribute("data-filter");
    [].forEach.call(document.querySelectorAll(".track"), function (t) {
      t.setAttribute("aria-pressed", String(t === f));
    });
    [].forEach.call(document.querySelectorAll("[data-track]"), function (el) {
      el.hidden = !(want === "all" || el.getAttribute("data-track") === want);
    });
    var note = document.querySelector(".filternote");
    if (note) {
      note.textContent = want === "all" ? "" :
        "Filtered to one kind. The ordering was computed across all three, so this " +
        "is the path with entries removed rather than the best path of this kind.";
    }
  });



  // Where you are, and how to keep going without hunting for it.
  var rows = function () {
    return [].filter.call(document.querySelectorAll("[data-id]"),
                          function (el) { return !el.hidden; });
  };
  var cursor = -1;
  function resume() {
    var bar = document.querySelector(".resume");
    if (!bar) return;
    var all = rows(), next = null, doneN = 0;
    all.forEach(function (el) {
      if (el.classList.contains("done")) doneN++;
      else if (!next) next = el;
    });
    if (!next) {
      bar.hidden = doneN === 0;
      bar.querySelector(".rn").textContent = doneN ? "everything on this path is done" : "";
      bar.querySelector(".rp").textContent = doneN + "/" + all.length;
      return;
    }
    bar.hidden = doneN === 0;
    var ph = next.querySelector(".ph") || next.querySelector("h2, h3");
    bar.querySelector(".rn").textContent =
      (next.querySelector(".n") ? next.querySelector(".n").textContent + ". " : "") +
      (ph ? ph.textContent : "");
    bar.querySelector(".rp").textContent = doneN + "/" + all.length;
    bar.querySelector(".rgo").onclick = function () {
      next.scrollIntoView({block: "center", behavior: "smooth"});
    };
  }
  function moveCursor(d) {
    var all = rows();
    if (!all.length) return;
    cursor = Math.max(0, Math.min(all.length - 1, cursor < 0 ? 0 : cursor + d));
    all.forEach(function (el) { el.classList.remove("cursor"); });
    all[cursor].classList.add("cursor");
    all[cursor].scrollIntoView({block: "nearest"});
  }
  // The page runs in a sandboxed iframe, so it only sees a keydown once that
  // iframe has focus. Shipping the shortcuts with a visible hint promised
  // something the page could not keep, and the reader reported exactly that.
  //
  // Two fixes. Make the document focusable and claim focus on load and on any
  // pointer contact, so the keys work as soon as someone touches the page. And
  // keep the hint HIDDEN until a keydown has actually been observed, so the page
  // never advertises a feature that is not live in this frame.
  try { document.body.tabIndex = -1; document.body.focus({preventScroll: true}); } catch (_) {}
  ["pointerdown", "mouseenter"].forEach(function (evt) {
    document.addEventListener(evt, function () {
      try { window.focus(); document.body.focus({preventScroll: true}); } catch (_) {}
    }, {passive: true});
  });

  function keysAreLive() {
    var hint = document.querySelector(".keys");
    if (hint) hint.hidden = false;
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var tag = (ev.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;
    keysAreLive();
    if (ev.key === "j") { moveCursor(1); ev.preventDefault(); }
    else if (ev.key === "k") { moveCursor(-1); ev.preventDefault(); }
    else if (ev.key === "x") {
      var all = rows();
      if (cursor >= 0 && all[cursor]) {
        var b = all[cursor].querySelector(".tick");
        if (b) b.click();
      }
      ev.preventDefault();
    } else if (ev.key === ".") {
      var d = document.querySelector(".depthtoggle");
      if (d) d.click();
      ev.preventDefault();
    }
  });

  var depth = document.querySelector(".depthtoggle");
  if (depth) {
    depth.addEventListener("click", function () {
      var open = depth.getAttribute("aria-pressed") !== "true";
      depth.setAttribute("aria-pressed", String(open));
      depth.textContent = open ? "collapse to the spine"
                               : depth.getAttribute("data-shut");
      [].forEach.call(document.querySelectorAll("details.subs"), function (s) {
        s.open = open;
      });
    });
    depth.setAttribute("data-shut", depth.textContent);
  }

  var all = document.querySelector('.track[data-filter="all"]');
  if (all) all.setAttribute("aria-pressed", "true");
  paint();
})();
"""

EXTRA_CSS = """
/* --- the stack: position one is the page, the rest recedes --------------- */
.stack { margin: 2.5rem 0; }
.lead { border-top: 3px solid var(--ink); padding-top: 1.4rem; margin-bottom: 2.8rem; }
/* The shared stylesheet styles h2 as a SECTION LABEL: monospace, uppercase,
   0.72rem, letter-spaced, muted, with a rule under it. Reusing the tag for an
   entry title inherited all of that and the first page rendered its headline as
   a tiny uppercase monospace label. Overriding only font-size is not enough, so
   every property that rule sets is reset here explicitly. */
/* The shared stylesheet styles h2 as a SECTION LABEL: monospace, uppercase,
   0.72rem, letter-spaced, muted, with a rule under it. Reusing the tag for an
   entry title inherits all of that, so every property that rule sets is reset
   here explicitly. Overriding font-size alone is what shipped the first time. */
.lead h2 {
  font-family: inherit; text-transform: none; letter-spacing: -.01em;
  color: var(--ink); font-weight: 600; border-bottom: 0; padding-bottom: 0;
  text-wrap: balance; font-size: 1.7rem; line-height: 1.15; margin: .5rem 0 .5rem; }
.lead h2 a { color: inherit; text-decoration: none;
  border-bottom: 1px solid var(--rule); }
.lead h2 a:hover { border-bottom-color: var(--ink); }
.lead .thinking { border-left: 3px solid var(--open); padding: .7rem 0 .7rem 1rem;
  margin: 1.1rem 0; background: var(--open-bg); }
.spine { border-top: 1px solid var(--rule); }
.spine li { display: grid; grid-template-columns: 2rem 1fr auto; gap: .8rem;
  padding: .62rem 0; border-bottom: 1px solid var(--rule); align-items: baseline; }
.spine .n { font-family: var(--mono, ui-monospace, monospace); color: var(--ink-2, #52514e);
  font-variant-numeric: tabular-nums; font-size: .85rem; }
.spine .t { font-weight: 500; }
.spine .hrs { font-family: var(--mono, ui-monospace, monospace); font-size: .82rem;
  color: var(--ink-2, #52514e); font-variant-numeric: tabular-nums; }
.chips { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; margin-bottom: .3rem; }
.chip { font-size: .7rem; letter-spacing: .06em; text-transform: uppercase;
  padding: .16rem .5rem; border: 1px solid var(--rule); border-radius: 3px;
  color: var(--ink-2, #52514e); }
.chip.paper { border-color: var(--eng); color: var(--eng); }
.chip.repo { border-color: var(--open); color: var(--open); }
.chip.project { border-color: var(--contested); color: var(--contested); }
.chip.seminal { background: var(--eng); color: var(--surface); border-color: var(--eng); }
.chip.dormant, .chip.abandoned { text-decoration: line-through; opacity: .65; }
.cond { font-size: .92rem; color: var(--ink-2, #52514e); border-left: 2px solid var(--rule);
  padding-left: .8rem; margin: .8rem 0; }
.qn { font-style: italic; margin-top: .5rem; }
.group-chip { margin-top: 1rem; border: 1px solid var(--rule); border-radius: 4px; }
.group-chip summary { cursor: pointer; padding: .5rem .8rem; font-size: .9rem; }
.group-chip .body { padding: 0 .8rem .8rem; font-size: .92rem; }
/* --- coverage bar: the prefix guarantee, made visible -------------------- */
.cov { display: flex; flex-wrap: wrap; gap: 2px; margin: .8rem 0; }
.cov i { width: 26px; height: 12px; border-radius: 2px; background: var(--rule);
  display: inline-block; }
.cov i.on { background: var(--open); }
.cov i.exp { background: var(--rule); border: 1.5px dashed var(--contested); }
.cov i.exp.on { background: var(--contested); border-style: solid; }
.lineage li { font-size: .88rem; padding: .28rem 0; color: var(--ink-2, #52514e); }
.lineage b { color: var(--ink); font-weight: 500; }
.lineage a { color: var(--ink); text-decoration: none;
  border-bottom: 1px solid var(--rule); }
.lineage a:hover { border-bottom-color: var(--ink); }
.lineage .rel { color: var(--ink-2); }
.pn { font-family: var(--mono, ui-monospace, monospace); font-size: .72rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; }
.degraded { border: 1px solid var(--contested); background: var(--contested-bg);
  padding: .7rem 1rem; border-radius: 4px; margin: 1.2rem 0; font-size: .92rem; }
@media (max-width: 640px) { .spine li { grid-template-columns: 1.6rem 1fr; }
  .spine .hrs { grid-column: 2; } }

/* --- marking done, and filtering ---------------------------------------- */
/* Any element the filter hides that also carries an explicit `display` loses to
   it: the UA rule is `[hidden] { display: none }` at one class of specificity and
   `.spine li { display: grid }` beats it. The filter appeared to do nothing to
   the spine while working on the articles, which is the shape of bug that looks
   like the JS is broken when the JS is fine. */
[hidden] { display: none !important; }
.tracks { display:flex; gap:.4rem; flex-wrap:wrap; margin:0 0 1.6rem; }
.track { font:inherit; font-size:.82rem; padding:.3rem .7rem; cursor:pointer;
  border:1px solid var(--rule); background:transparent; color:var(--ink-2);
  border-radius:3px; }
.track[aria-pressed="true"] { background:var(--ink); color:var(--surface);
  border-color:var(--ink); }
.filternote { font-size:.85rem; color:var(--ink-2); margin:.4rem 0 1rem; }
.tick { position:absolute; left:-1.7rem; top:.35rem; width:1.05rem; height:1.05rem;
  border:1px solid var(--rule); border-radius:3px; background:transparent;
  cursor:pointer; padding:0; }
.tick:hover { border-color:var(--ink-2); }
.done > .tick::after { content:""; position:absolute; inset:2px;
  background:var(--open); border-radius:1px; }
article[data-id], .spine li { position:relative; }
.spine li .tick { left:-1.7rem; top:.72rem; }
.done { opacity:.5; }
.done .t a, .done h2 a, .done h3 a { text-decoration:line-through; }
[data-id].next::before { content:"next"; position:absolute; left:-4.6rem; top:.5rem;
  font-size:.62rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--open); }
.spine .meta { display:block; margin-top:.2rem; font-size:.78rem; }
.grp { font-size:.78rem; color:var(--ink-2); margin-left:.45rem;
  text-decoration:none; border-bottom:1px dotted var(--rule); }
.grp:hover { color:var(--ink); }
.chip.role { border-style:dashed; }
.cov i { transition:background .15s ease; }
.covcount { font-variant-numeric:tabular-nums; font-weight:600; color:var(--open); }
@media (max-width:760px) {
  .tick { position:static; margin-right:.5rem; }
  [data-id].next::before { display:none; }
}
@media (prefers-reduced-motion:reduce) { .cov i { transition:none; } }

/* --- the depth dimension: simple by default, opens into everything ------- */
.spine li { grid-template-columns: 2.4rem 1fr auto; align-items: start; }
.spine .n { font-variant-numeric: tabular-nums; padding-top: .12rem; }
.spine .t { display: flex; flex-direction: column; gap: .12rem; min-width: 0; }
.ph { color: var(--ink-2); font-size: .88rem; font-weight: 400; }
.spine .meta { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem;
  margin-top: .18rem; font-size: .78rem; }
.yr { font-family: var(--mono, ui-monospace, monospace); font-size: .72rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; }
.phlead { color: var(--ink-2); font-size: 1rem; margin: 0 0 .8rem; }
.subs { margin: .1rem 0 .3rem 2.4rem; border-left: 2px solid var(--rule);
  padding-left: .9rem; }
.subs > summary { font-size: .8rem; color: var(--ink-2); padding: .28rem 0;
  list-style: none; cursor: pointer; }
.subs > summary::-webkit-details-marker { display: none; }
.subs > summary::before { content: "▸"; display: inline-block; width: 1em;
  color: var(--ink-3); transition: transform .12s ease; }
.subs[open] > summary::before { transform: rotate(90deg); }
.subn { font-family: var(--mono, ui-monospace, monospace); color: var(--open);
  font-weight: 600; }
.subnote { font-size: .84rem; color: var(--ink-2); margin: .2rem 0 .5rem; }
.sublist { border-top: 0; }
.sublist li { border-bottom: 1px dashed var(--rule); padding: .45rem 0; }
.sublist li:last-child { border-bottom: 0; }
.sublist .t a { font-size: .94rem; }
article .subs { margin-left: 0; }
.tracks .spacer { flex: 1; }
.depthtoggle { font: inherit; font-size: .8rem; padding: .3rem .7rem; cursor: pointer;
  border: 1px dashed var(--rule); background: transparent; color: var(--ink-2);
  border-radius: 3px; }
.depthtoggle[aria-pressed="true"] { border-style: solid; border-color: var(--ink);
  color: var(--ink); }
@media (prefers-reduced-motion: reduce) { .subs > summary::before { transition: none; } }

/* --- the row, rebuilt: phrase leads, kind is a rail, hours accumulate ----- */
.spine { border-top: 1px solid var(--rule); }
.spine li { display: grid; grid-template-columns: 2.6rem 1fr auto;
  gap: 0 .9rem; padding: .78rem 0 .78rem .55rem; align-items: baseline;
  border-bottom: 1px solid var(--rule); position: relative; }
.spine li::before { content: ""; position: absolute; left: 0; top: .72rem;
  bottom: .72rem; width: 3px; border-radius: 2px; background: var(--rule); }
.spine li[data-track="paper"]::before  { background: var(--eng); }
.spine li[data-track="repo"]::before   { background: var(--open); }
.spine li[data-track="project"]::before{ background: var(--contested); }
.spine .n { font-family: var(--mono, ui-monospace, monospace); font-size: .8rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; text-align: right; }
.spine .t { display: flex; flex-direction: column; gap: .1rem; min-width: 0; }
.spine .ph { font-size: 1.02rem; color: var(--ink); line-height: 1.35; }
.spine .ti { font-size: .86rem; color: var(--ink-2); text-decoration: none;
  border-bottom: 1px solid transparent; }
.spine .ti:hover { border-bottom-color: var(--rule); color: var(--ink); }
.spine .meta { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem;
  margin-top: .22rem; font-size: .74rem; }
.spine .hrs { display: flex; flex-direction: column; align-items: flex-end;
  gap: .1rem; font-family: var(--mono, ui-monospace, monospace); font-size: .74rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; white-space: nowrap; }
.spine .cum { color: var(--ink-3); opacity: .55; font-size: .68rem; }
.spine li.done .ph { color: var(--ink-3); }
.spine li.cursor { background: var(--surface-2); }
.spine li.cursor::before { background: var(--ink); }
.chip.role { border-style: dashed; font-size: .64rem; }
.yr { font-family: var(--mono, ui-monospace, monospace); font-size: .7rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; }

/* --- resume bar: where you are, without scrolling to find out ------------- */
.resume { position: sticky; top: 0; z-index: 20; display: flex; gap: .7rem;
  align-items: baseline; padding: .55rem .8rem; margin: 0 0 1rem;
  background: var(--surface-2); border: 1px solid var(--rule); border-radius: 4px;
  font-size: .82rem; }
.resume .rl { font-family: var(--mono, ui-monospace, monospace); font-size: .64rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--open); }
.resume .rn { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }
.resume .rp { font-family: var(--mono, ui-monospace, monospace); font-size: .72rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; }
.resume .rgo { font: inherit; font-size: .76rem; padding: .18rem .6rem; cursor: pointer;
  border: 1px solid var(--rule); background: transparent; color: var(--ink-2);
  border-radius: 3px; }
.resume .rgo:hover { border-color: var(--ink); color: var(--ink); }

/* --- keyboard hint, shown once someone has used the page ----------------- */
.keys { font-size: .74rem; color: var(--ink-3); margin: .5rem 0 0; }
.keys kbd { font-family: var(--mono, ui-monospace, monospace); font-size: .7rem;
  border: 1px solid var(--rule); border-radius: 3px; padding: 0 .28rem; }
.grpname { font-size: .86rem; color: var(--ink-2); margin: .9rem 0 0;
  padding-top: .55rem; border-top: 1px solid var(--rule); }
.cnt { font-family: var(--mono, ui-monospace, monospace); font-size: .7rem;
  color: var(--ink-3); font-variant-numeric: tabular-nums; white-space: nowrap; }
.cnt.new { font-style: italic; }
a.cnt.code { color: var(--open); text-decoration: none;
  border-bottom: 1px solid transparent; }
a.cnt.code:hover { border-bottom-color: var(--open); }
.leadmeta { display: flex; gap: .7rem; flex-wrap: wrap; margin: .2rem 0 .8rem; }

@media (max-width: 700px) {
  .spine li { grid-template-columns: 2.1rem 1fr; }
  .spine .hrs { grid-column: 2; flex-direction: row; gap: .5rem; margin-top: .2rem; }
  .resume { position: static; }
}

@media (max-width: 700px) {
  .subs { margin-left: 0; }
  .spine li { grid-template-columns: 2rem 1fr; }
  .spine .hrs { grid-column: 2; }
}
"""


def e(s) -> str:
    return html.escape(str(s or ""), quote=False)


def raw(t: str) -> str:
    """Authored HTML, passed through.

    `meta.opening` and a group's thesis are written by the run, not supplied by a
    reader, and they legitimately carry <b> and <a>. Sending them through md()
    escaped those tags and the first published page rendered a literal
    "&lt;b&gt;Critique of World Model&lt;/b&gt;" in its opening sentence. Keep the
    two paths apart: raw() for what the run authored, md() for everything else.
    """
    return t or ""


def md(t: str) -> str:
    """Links and code spans only. Anything richer belongs in the markdown."""
    t = e(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)


def chip(label: str, *cls: str) -> str:
    """One chip. Classes are joined, so a conditional class that resolves to
    nothing leaves no trailing space rather than `class="chip "`."""
    names = " ".join(c for c in ("chip",) + cls if c)
    return f'<span class="{names}">{e(label)}</span>'


def chips(x: dict, *, compact: bool = False) -> str:
    """Kind, then role or archetype, then liveness.

    The role chip goes on EVERY entry, including the spine. The first page showed
    it only on the top two and dropped it for the other fifteen, which throws away
    the one thing builder.md says changes how an entry should be read.
    """
    out = [chip(KIND_LABEL.get(x.get("kind"), x.get("kind") or ""), x.get("kind") or "")]
    if x.get("role"):
        out.append(chip(x["role"], "role", "seminal" if x["role"] == "seminal" else ""))
    if x.get("liveness") in ("dormant", "abandoned"):
        out.append(chip(x["liveness"], x["liveness"]))
    inner = "".join(out)
    return inner if compact else f'<div class="chips">{inner}</div>'


def has_thesis(g: dict) -> bool:
    return bool(g and (g.get("thesis") or g.get("direction") or g.get("read_more")))


def group_chip(x: dict, groups: dict) -> str:
    g = groups.get(x.get("group") or "")
    if not g:
        return ""
    if not has_thesis(g):
        # Twenty-nine identical "nobody looked" disclosures is noise pretending to
        # be rigour. The lab NAME is real; only the thesis is missing.
        return f'<p class="grpname">{e(g.get("name", x["group"]))}</p>'
    thesis = g.get("thesis") or f'No single thesis. {e(g.get("thesis_none_why", ""))}'
    rows = [f"<p>{raw(thesis)}</p>"]
    if g.get("arguing_against"):
        rows.append(f"<p>Arguing against: {md(g['arguing_against'])}</p>")
    if g.get("direction"):
        rows.append(f"<p>{md(g['direction'])}</p>")
    links = " · ".join(f'<a href="{e(l["url"])}">{e(l["label"])}</a>'
                       for l in (g.get("read_more") or []))
    if links:
        rows.append(f"<p>{links}</p>")
    return (f'<details class="group-chip" id="g-{e(g["slug"])}"><summary>{e(g.get("name", x["group"]))}'
            f'{" · " + e(g.get("institution")) if g.get("institution") else ""}</summary>'
            f'<div class="body">{"".join(rows)}</div></details>')


def counts(x: dict) -> str:
    """Citations for a paper, stars for a repo, and a paper's repo with its stars.

    Every number carries the date it was read, in a title attribute, because a
    count moves and an undated one is a claim about today that stops being true.
    Under six months old a paper shows "too new to cite" instead of a raw count:
    a four-month-old paper with three citations and a four-year-old paper with
    three citations are opposite findings, and the number hides that.
    """
    out = []
    c = x.get("citations") or {}
    if c.get("value") is not None:
        out.append(f'<span class="cnt" title="{e(c["source"])}, read '
                   f'{e(c["read_on"])}">{c["value"]:,} cited</span>')
    elif c.get("note") == "too new to cite":
        out.append('<span class="cnt new">too new to cite</span>')
    s = x.get("stars") or {}
    if s.get("value") is not None:
        out.append(f'<span class="cnt" title="GitHub, read {e(s["read_on"])}">'
                   f'{s["value"]:,}&#9733;</span>')
    elif s.get("note") == "throttled":
        # Never render a throttled count as zero or as absence.
        out.append('<span class="cnt new">stars unread</span>')
    code = x.get("code") or {}
    if code.get("slug"):
        st = (code.get("stars") or {}).get("value")
        tail = f' {st:,}&#9733;' if st is not None else ""
        out.append(f'<a class="cnt code" href="{e(code["url"])}">'
                   f'{e(code["slug"])}{tail}</a>')
    return "".join(out)


def group_link(x: dict, groups: dict) -> str:
    """The lab, on every entry at every depth, as the reader asked for it.

    On the spine it is a link into the group section rather than a disclosure,
    because fifteen expandable panels in a list is not a spine any more.
    """
    g = groups.get(x.get("group") or "")
    if not g:
        return ""
    if not has_thesis(g):
        return f'<span class="grp plain">{e(g.get("name", x["group"]))}</span>'
    return f'<a class="grp" href="#g-{e(g["slug"])}">{e(g.get("name", x["group"]))}</a>'


def entry(x: dict, groups: dict, cls: str, tag: str) -> str:
    parts = [chips(x)]
    parts.append(f'<{tag}><a href="{e(x.get("url"))}">{e(x.get("title"))}</a></{tag}>')
    if counts(x):
        parts.append(f'<p class="meta leadmeta">{counts(x)}</p>')
    if x.get("phrase"):
        parts.append(f'<p class="phlead">{e(x["phrase"])}</p>')
    if x.get("conditioning"):
        parts.append(f'<p class="cond">{md(x["conditioning"])}</p>')
    if x.get("summary"):
        parts.append(f"<p>{md(x['summary'])}</p>")
    if x.get("unlocks"):
        parts.append(f"<p>{md(x['unlocks'])}</p>")
    if x.get("where_the_thinking_is"):
        q = f'<p class="qn">{md(x["question"])}</p>' if x.get("question") else ""
        parts.append(f'<div class="thinking">{md(x["where_the_thinking_is"])}{q}</div>')
    if x.get("objection"):
        parts.append(f"<p>The objection: {md(x['objection'])}</p>")
    if x.get("skip"):
        parts.append(f"<p>Skip: {md(x['skip'])}</p>")
    parts.append(group_chip(x, groups))
    parts.append(sub_rows(x, groups))
    return (f'<article class="{cls}" id="e-{e(x.get("id"))}" '
            f'data-track="{e(x.get("kind"))}" data-id="{e(x.get("id"))}">'
            f'<button class="tick" aria-label="mark done"></button>'
            f'{"".join(parts)}</article>')


def sub_rows(x: dict, groups: dict) -> str:
    """The approaches under one entry, behind a disclosure.

    Collapsed by default. The reader asked for a tool that looks simple and opens
    into more, so the closed state is the whole field in one column and the open
    state is every approach to one idea. The summary says how many and what they
    vary, because "3 more" tells you nothing about whether to open it.
    """
    sg = x.get("subgroup") or {}
    subs = sg.get("items") or []
    if not subs:
        return ""
    n = len(subs)
    label = sg.get("label") or "other approaches"
    rows = "".join(row(s, groups, sub=True) for s in subs)
    note = f'<p class="subnote">{md(sg["note"])}</p>' if sg.get("note") else ""
    return (f'<details class="subs"><summary>'
            f'<span class="subn">{n}</span> {e(label)}</summary>'
            f'{note}<ol class="spine sublist">{rows}</ol></details>')


def row(x: dict, groups: dict, *, sub: bool = False, cum: float | None = None) -> str:
    """One line of the path.

    The PHRASE is the scan line, not the title. A reader going down a list of
    twenty-six wants to know what a thing IS; the title tells them what it is
    called, which is the second question. The first page had that backwards and
    it made the column read as a bibliography.

    Kind is a coloured rail on the left rather than a chip, because a chip that
    appears on every single row carries no information and costs the same
    attention as one that does.

    `cum` is hours-so-far. A running total answers "can I get through the next
    three tonight" without arithmetic, which no single per-row duration does.
    """
    num = x.get("number") or x.get("position")
    yr = f'<span class="yr">{e(x["year"])}</span>' if x.get("year") else ""
    role = (chip(x["role"], "role", "seminal" if x["role"] == "seminal" else "")
            if x.get("role") else "")
    live = (chip(x["liveness"], x["liveness"])
            if x.get("liveness") in ("dormant", "abandoned") else "")
    cumtxt = (f'<span class="cum">{cum:g}h</span>' if cum is not None else "")
    return (f'<li id="e-{e(x.get("id"))}" data-track="{e(x.get("kind"))}" '
            f'data-id="{e(x.get("id"))}"{" data-sub=1" if sub else ""}>'
            f'<button class="tick" aria-label="mark done"></button>'
            f'<span class="n">{e(num)}</span>'
            f'<span class="t"><span class="ph">{e(x.get("phrase"))}</span>'
            f'<a class="ti" href="{e(x.get("url"))}">{e(x.get("title"))}</a>'
            f'<span class="meta">{yr}{role}{live}{counts(x)}'
            f'{group_link(x, groups)}</span></span>'
            f'<span class="hrs">{e(x.get("time"))}{cumtxt}</span>'
            f'</li>{sub_rows(x, groups) if not sub else ""}')


def stack(d: dict) -> str:
    es = d.get("entries") or []
    if not es:
        return ""
    groups = {g["slug"]: g for g in (d.get("groups") or [])}
    tracks = "".join(
        f'<button class="track" data-filter="{k}" aria-pressed="false">{v}</button>'
        for k, v in (("all", "the path"), ("paper", "papers"),
                     ("repo", "code"), ("project", "projects")))
    nsub = sum(len(((x.get("subgroup") or {}).get("items")) or []) for x in es)
    depth = (f'<button class="depthtoggle" aria-pressed="false">'
             f'open all {nsub} approaches</button>') if nsub else ""
    out = [f'<div class="tracks" role="group" aria-label="filter by kind">'
           f'{tracks}<span class="spacer"></span>{depth}</div>',
           '<p class="filternote"></p>',
           # Hidden until a keydown proves the shortcuts reach this frame.
           '<p class="keys" hidden><kbd>j</kbd> <kbd>k</kbd> move, <kbd>x</kbd> done, '
           '<kbd>.</kbd> open every approach</p>',
           entry(es[0], groups, "lead", "h2")]
    # One spine after the lead. An awkward half-weight second entry made sense
    # at twelve items and stops making sense at twenty-six: it reads as a second
    # lead rather than as the next step.
    if len(es) > 1:
        rows, run = [], float(es[0].get("cost_hours") or 0)
        for x in es[1:]:
            run += float(x.get("cost_hours") or 0)
            rows.append(row(x, groups, cum=run))
        out.append(f'<ol class="spine">{"".join(rows)}</ol>')
    total = sum(float(x.get("cost_hours") or 0) for x in es)
    spine = sum(float(x.get("cost_hours") or 0) for x in es[:4])
    subh = sum(float(s.get("cost_hours") or 0) for x in es
               for s in ((x.get("subgroup") or {}).get("items") or []))
    # One decimal, because the runbar prints 8.5 and rounding to 8 here made the
    # same number disagree with itself in two places on one page.
    fmt = lambda h: f"{h:g}"
    extra = (f' Every approach underneath adds about {fmt(subh)} more.'
             if subh else "")
    out.append(f'<p class="hrs">First four: about {fmt(spine)} hours. '
               f'The whole spine, all {len(es)}: about {fmt(total)}.{extra}</p>')
    return f'<section class="stack">{"".join(out)}</section>'


def coverage_bar(d: dict) -> str:
    """Ideas lighting up as the path advances, experiential ones distinct.

    Those stay dark until something gets built, which is the argument for
    interleaving rather than three lists, in one picture.
    """
    ideas = d.get("ideas") or []
    if len(ideas) < 4:
        return ""
    def cell(n, i):
        cls = " ".join(c for c in ("exp" if i.get("experiential") else "",
                                   "on" if i.get("covered_prior") else "") if c)
        by = ",".join(i.get("covered_by") or [])
        # No class attribute at all when there are no classes. An empty one is
        # harmless to render and a reliable sign of a conditional that resolved
        # to nothing, so the checker flags it and this keeps the signal clean.
        c = f' class="{cls}"' if cls else ""
        return (f'<i{c} data-by="{e(by)}" data-prior='
                f'"{"1" if i.get("covered_prior") else "0"}" title="{e(i.get("name"))}"></i>')
    cells = "".join(cell(n, i) for n, i in enumerate(ideas))
    n_exp = sum(1 for i in ideas if i.get("experiential"))
    prior = sum(1 for i in ideas if i.get("covered_prior"))
    note = (f"{len(ideas)} ideas in this topic. {prior} already covered by what you have read, "
            f'and <span class="covcount">{prior}</span> covered once you count what you have '
            f"marked done. {n_exp} are marked experiential, meaning no amount of reading covers "
            f"them and only building something does. Those stay dark until you build something.")
    rows = "".join(f'<tr><td>{e(i.get("name"))}</td>'
                   f'<td>{"experiential" if i.get("experiential") else "readable"}</td></tr>'
                   for i in ideas)
    n = len(ideas)
    return (f'<section><h2>What this topic contains</h2><div class="cov">{cells}</div>'
            f'<p>{note}</p>'
            f'<details><summary>all {n} ideas, and which of them only building covers</summary><table>{rows}</table></details></section>')


def lineage(d: dict) -> str:
    """Descent along the path.

    Entries are named by their titles, not their ids. The first page rendered
    `jepa_pos is attacked by critique`, which is the run's internal keys leaking
    into reader-facing prose. Anything the reader sees gets the title, and where
    an id has no entry the raw string is kept because inventing a name is worse.
    """
    ed = d.get("lineage") or []
    if not ed:
        return ""
    # Flatten: an entry filed in a subgroup is still an entry, and building the
    # name map from the spine alone made the lineage fall back to raw item ids
    # for everything that had moved down a level. That is the run's internal keys
    # rendered as prose, which is the exact failure this section was fixed for once.
    flat = []
    for x in d.get("entries") or []:
        flat.append(x)
        flat.extend((x.get("subgroup") or {}).get("items") or [])
    names = {x.get("id"): x.get("title") for x in flat}
    pos = {x.get("id"): (x.get("number") or x.get("position")) for x in flat}

    def label(k):
        if k not in names:
            return e(k)
        n = pos.get(k)
        return (f'<a href="#e-{e(k)}">{e(names[k])}</a>'
                + (f' <span class="pn">{n}</span>' if n else ""))
    rows = "".join(f"<li>{label(a)} <span class=\"rel\">{e(rel)}</span> {label(b)}</li>"
                   for a, rel, b in ed)
    return f'<section><h2>How these connect</h2><ul class="lineage">{rows}</ul></section>'


def confidence(d: dict) -> str:
    c = d.get("confidence") or {}
    if not c:
        return ""
    bits = " · ".join(f"{e(k)} {e(v)}" for k, v in c.items() if k != "unverified")
    un = c.get("unverified") or []
    lis = "".join(f"<li>{md(u)}</li>" for u in un) or "<li>Nothing, which is itself suspect.</li>"
    return (f'<section><h2>Confidence</h2><p>{bits}</p>'
            f'<details><summary>Could not verify ({len(un)})</summary><ul>{lis}</ul>'
            f"</details></section>")


def main() -> None:
    run = pathlib.Path(sys.argv[1]).resolve()
    d = json.load(open(run / "path.json"))
    css = (SHARED / "report.css").read_text() + EXTRA_CSS
    # The shared report.js drives industry-research's openness map, which this
    # page does not render, so every one of its handlers binds to nothing. Ship
    # this page's own behaviour instead of another page's dead weight.
    js = PAGE_JS
    m = d.get("meta", {})

    bar = "".join(f"<span><b>{e(k)}</b> {e(v)}</span>"
                  for k, v in (m.get("runbar") or {}).items())
    deg = (f'<div class="degraded">{raw(m["degraded"])}</div>') if m.get("degraded") else ""
    # NOT `bar`: that name already holds the runbar's contents a few lines up,
    # and reusing it silently emptied the runbar while the page still built and
    # still passed every check. Shadowing is the quietest bug in this file.
    resume = ('<div class="resume" hidden><span class="rl">next</span>'
              '<span class="rn"></span><span class="rp"></span>'
              '<button class="rgo">go</button></div>')
    head = (f'{resume}<header><p class="eyebrow">{e(m.get("eyebrow", "Reading path"))}</p>'
            f'<h1>{e(m.get("title", "Untitled"))}</h1>'
            f'<p class="verdict">{raw(m.get("opening", ""))}</p>'
            f'<div class="runbar">{bar}</div></header>')

    page = (f'<meta charset="utf-8">\n<title>{e(m.get("title", "Reading path"))}</title>\n'
            f"<style>\n{css}\n</style>\n\n"
            f'<div class="viz-root"><div class="wrap">\n{head}\n{deg}\n'
            f"{stack(d)}\n{coverage_bar(d)}\n{lineage(d)}\n{confidence(d)}\n"
            f'<div id="tip" role="tooltip"></div>\n</div></div>\n<script>\n{js}\n</script>\n')
    (run / "report.html").write_text(page)
    print(f"wrote {run / 'report.html'} ({len(page):,} bytes)")

    for tag in ("div", "section", "article", "p", "span", "ul", "ol", "li", "details", "a", "table"):
        o = len(re.findall(rf"<{tag}[\s>]", page))
        c = len(re.findall(rf"</{tag}>", page))
        if o != c:
            print(f"  WARNING unbalanced <{tag}>: {o} open, {c} close")
    if "—" in page:
        print(f"  WARNING {page.count(chr(8212))} em dashes in output")


if __name__ == "__main__":
    main()

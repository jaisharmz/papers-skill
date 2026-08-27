"""The page checker has to fail real pages, and not fail good ones.

Every case here is a defect that shipped on a published page and that
build_page.py passed, since it only ever checked tag balance and em dashes.

Each test asserts BOTH halves: the broken page fails and the fixed page passes.
Split into separate tests these read as twice the coverage and are not, and the
second half is the one that matters most in practice: two of these checks shipped
with a false-positive rate high enough to train a reader to ignore them.
"""
from __future__ import annotations

import pytest

from scripts import checkpage as C

SHELL = ('<meta charset="utf-8"><title>T</title><style>{css}</style>'
         '<div class="viz-root"><div class="wrap"><h1>H</h1>{body}</div></div>'
         '<script>{js}</script>')


def run(tmp_path, css="", body="", js=""):
    p = tmp_path / "report.html"
    p.write_text(SHELL.format(css=css, body=body, js=js))
    return {f.rule: f for f in C.check(p)}


RULE_TAGS = "reused tags reset the shared styling they inherit"
RULE_VARS = "custom properties resolve"
RULE_CLASS = "every class in the markup is styled"
RULE_FEAT = "features page.md promises are present"
RULE_ROLE = "every entry shows its role and its group"
RULE_HIDE = "hidden elements can actually be hidden"
RULE_IDS = "no internal identifiers in generated relation lists"
RULE_DEAD = "this skill's own rules all match something"
RULE_WIDE = "no fixed widths wider than the column"
RULE_COUNT = "subgroup labels agree with their counts"

SHARED_H2 = ("h2 { font-family: monospace; text-transform: uppercase; "
             "letter-spacing:.14em; color:#888; font-size:.72rem; }")


def test_a_reused_tag_must_reset_what_it_inherits(tmp_path):
    """The shared sheet styles h2 as a monospace uppercase section label. The page
    reused h2 for entry titles, overrode only font-size, and the headline rendered
    as a tiny uppercase label. Nothing errored and no class was missing."""
    body = '<article class="lead"><h2>Title</h2></article>'
    bad = run(tmp_path, css=SHARED_H2 + ".lead h2 { font-size: 1.7rem; }", body=body)
    assert bad[RULE_TAGS].status == C.FAIL
    assert any("text-transform" in i for i in bad[RULE_TAGS].items)
    good = run(tmp_path, css=SHARED_H2 + ".lead h2 { font-family: inherit; "
               "text-transform: none; letter-spacing:-.01em; color:#000; "
               "font-size:1.7rem; }", body=body)
    assert good[RULE_TAGS].status == C.OK


def test_a_custom_property_needs_a_definition_or_a_fallback(tmp_path):
    assert run(tmp_path, css=".x { color: var(--nope); }")[RULE_VARS].status == C.FAIL
    assert run(tmp_path, css=".x { color: var(--nope, #000); }")[RULE_VARS].status == C.OK


def test_a_class_in_the_markup_needs_a_rule(tmp_path):
    """The covcount bug: a span the builder emitted with no rule anywhere."""
    f = run(tmp_path, body='<p><span class="covcount">3</span></p>')[RULE_CLASS]
    assert f.status == C.FAIL and "covcount" in f.items
    assert run(tmp_path, css=".covcount { color: red }",
               body='<p><span class="covcount">3</span></p>')[RULE_CLASS].status == C.OK


def test_the_features_page_md_promises_must_be_present(tmp_path):
    """The first published page shipped neither the marking interaction nor the
    track filters, and nothing errored: it just quietly did less."""
    f = run(tmp_path, body='<div class="cov"><i></i></div>')[RULE_FEAT]
    assert f.status == C.FAIL and any("marking an item done" in i for i in f.items)
    ok = run(tmp_path, body='<div class="cov" data-track="paper"><i></i></div>',
             js='localStorage.getItem("k"); el.addEventListener("click", f)')
    assert ok[RULE_FEAT].status == C.OK


def test_every_entry_shows_its_role_and_its_group(tmp_path):
    """The first page showed both on the top two entries of seventeen."""
    bad = run(tmp_path, body='<article data-id="a"><span class="chip paper">p</span>'
              '</article><ol class="spine"><li><span class="n">2</span></li></ol>')
    assert bad[RULE_ROLE].status == C.FAIL
    assert "role" in bad[RULE_ROLE].detail and "group" in bad[RULE_ROLE].detail
    good = run(tmp_path, body='<article data-id="a"><span class="chip paper">p</span>'
               '<span class="chip role">seminal</span>'
               '<details class="group-chip">g</details></article>')
    assert good[RULE_ROLE].status == C.OK


def test_a_display_rule_must_not_defeat_the_hidden_attribute(tmp_path):
    """`.spine li { display: grid }` beats the UA `[hidden] { display: none }`, so
    filtering hid the articles and left the whole spine visible. The script was
    fine; the CSS lost."""
    body = '<ol class="spine"><li data-track="paper">x</li></ol>'
    assert run(tmp_path, css=".spine li { display: grid; }", body=body,
               js="el.hidden = true;")[RULE_HIDE].status == C.FAIL
    assert run(tmp_path, css="[hidden] { display: none !important; } "
               ".spine li { display: grid; }", body=body,
               js="el.hidden = true;")[RULE_HIDE].status == C.OK


def test_item_ids_must_not_reach_the_reader_but_real_names_must(tmp_path):
    """The lineage rendered "jepa_pos is attacked by critique". An unscoped version
    of the fix then flagged the word "dual" in "dual control" and the repository
    name inside "AlmondGod/tinyworlds", which is the false-positive rate that
    teaches a reader to skip the check."""
    ids = ('<article data-id="jepa_pos"></article><article data-id="critique"></article>'
           '<article data-id="dual"></article><article data-id="tinyworlds"></article>')
    bad = run(tmp_path, body=ids + '<ul class="lineage"><li>jepa_pos is attacked by '
              'critique</li></ul>')
    assert bad[RULE_IDS].status == C.FAIL and "jepa_pos" in bad[RULE_IDS].items
    good = run(tmp_path, body=ids + '<p>Surveys dual control, due to Feldbaum.</p>'
               '<ul class="lineage"><li>AlmondGod/tinyworlds reimplements Genie</li>'
               '<li>A Path Towards AMI is attacked by Critique of World Model</li></ul>')
    assert good[RULE_IDS].status == C.OK, good[RULE_IDS].items


def test_a_subgroup_label_must_agree_with_its_count(tmp_path):
    """"two more positions" above a group of one. Small, and exactly the kind of
    wrongness that makes a reader stop trusting every other number on the page."""
    lab = ('<details class="subs"><summary><span class="subn">{n}</span> '
           'two more positions in this argument</summary></details>')
    assert run(tmp_path, body=lab.format(n=1))[RULE_COUNT].status == C.FAIL
    assert run(tmp_path, body=lab.format(n=2))[RULE_COUNT].status == C.OK


def test_the_checker_does_not_cry_wolf(tmp_path):
    """Two false positives that shipped: a class the page's own script adds at
    runtime reported as a dead rule, and a media-query breakpoint reported as an
    overflow risk. A checker with either gets ignored, which is worse than none."""
    f = run(tmp_path, css="/* --- the stack */ .done { opacity:.5 } "
            "@media (max-width:760px) { .x { color:red } }",
            body='<div class="done x">a</div>',
            js='el.classList.toggle("done", true)')
    assert f[RULE_DEAD].status == C.OK
    assert f[RULE_WIDE].status == C.OK


def test_a_control_with_no_handler_and_a_handler_with_no_control_are_both_caught(tmp_path):
    """Both look identical to a working page in a screenshot, and the embedded
    artifact viewer does not reliably let a click through to prove otherwise."""
    RULE = "every control is wired and every handler has a control"
    orphan_button = run(tmp_path, body='<button class="depthtoggle">open</button>')
    assert orphan_button[RULE].status == C.FAIL
    orphan_handler = run(tmp_path, js='document.querySelectorAll("details.subs")')
    assert orphan_handler[RULE].status == C.FAIL
    ok = run(tmp_path, css=".depthtoggle{} .subs{}",
             body='<button class="depthtoggle">open</button>'
                  '<details class="subs"><summary>3 approaches</summary></details>',
             js='document.querySelector(".depthtoggle");'
                'document.querySelectorAll("details.subs")')
    assert ok[RULE].status == C.OK, ok[RULE].items

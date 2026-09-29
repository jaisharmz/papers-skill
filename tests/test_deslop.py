"""The last gate: does this read as though a machine wrote it.

Every title shape here is one a person naming a document for a colleague would
not produce, and every budget was set by measuring this skill's own output rather
than by taste. The counts are in scripts/deslop.py.
"""
from __future__ import annotations

import pytest

from scripts import deslop as D

RULE = "the title names the thing"


@pytest.mark.parametrize("title", [
    "World models, after the score stops meaning anything",   # what actually shipped
    "Inference, once the cache stops helping",
    "The quiet death of the benchmark",
    "Protein design: the bottleneck that nobody names",
    "Rethinking world models",
    "Towards a theory of evaluation",
    "When scaling stops working",
    "Your world model is not what you think",
])
def test_the_slop_title_shapes_are_caught(title):
    f = D.check_title(title)
    assert f.status == D.FAIL, f"{title!r} passed"
    assert f.why, "a finding with no reason teaches nobody anything"


@pytest.mark.parametrize("title", [
    "World models",
    "Discrete diffusion",
    "Reading path for protein folding",
    "Model predictive control",
])
def test_a_plain_noun_phrase_passes(title):
    assert D.check_title(title).status == D.OK


def test_a_title_that_has_become_a_sentence_is_flagged_but_not_blocking():
    f = D.check_title("A reading path through learned models of environment dynamics "
                      "for prediction and planning")
    assert f.status == D.WARN


def test_a_tic_is_a_budget_not_a_ban():
    """"rather than" is a fine phrase. Seventeen in five thousand words is a tic."""
    ok = D.check_prose("rather than this. " + "filler words here. " * 200)
    assert all(f.status == D.OK for f in ok if f.rule.startswith("tic")), \
        "one use of a common phrase must not fail"
    heavy = D.check_prose(("we chose x rather than y. " * 20) + "filler. " * 100)
    tic = next(f for f in heavy if "rather than" in f.rule)
    assert tic.status == D.WARN and "budget" in tic.detail


def test_the_zero_budget_phrases_block():
    """Some constructions have no defensible frequency."""
    for phrase in ("and that is the point", "which is exactly what happened",
                   "the real question here", "it is worth noting that"):
        fs = D.check_prose(phrase + ". " + "filler words. " * 60)
        assert any(f.status == D.FAIL for f in fs if f.rule.startswith("tic")), phrase


def test_repeated_sentence_openers_are_caught():
    """The group boilerplate opened 33 sentences the same way in a real run."""
    text = "The group region was not traversed. " * 5 + "Something else entirely happens now."
    f = next(f for f in D.check_prose(text) if f.rule == "sentence openers vary")
    assert f.status == D.WARN and "the group" in f.detail


def test_a_clean_page_passes_end_to_end():
    d = {"meta": {"title": "World models",
                  "opening": "Twenty-six steps into learned environment models."},
         "entries": [{"phrase": "the model is bad and planning works anyway",
                      "summary": "Audits MuZero's model directly and finds it "
                                 "generalises poorly to unseen policies.",
                      "conditioning": "Position one because it refuses the question."}],
         "groups": []}
    assert D.report(D.deslop(d)) == 0


def test_a_markdown_page_is_checked_as_prose():
    title, prose = D.from_markdown(
        "---\nname: x\n---\n"
        "# World models, after the score stops meaning anything\n\n"
        "The **model** is bad, and [planning](https://example.com) works anyway.\n\n"
        "```\nrather than rather than rather than\n```\n"
        "| a | b |\n")
    assert D.check_title(title).status == D.FAIL
    assert prose == "The model is bad, and planning works anyway."

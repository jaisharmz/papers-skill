"""The grader has to fail things, or it is decoration.

Every check gets a case that trips it. A grader nobody tested returns OK on
everything and is worse than not having one, because it launders a bad run as a
checked one.
"""
from __future__ import annotations

import json

import pytest

from scripts import critique as C
from tests.fixtures.runs import GOOD, BAD


def by_rule(checks):
    return {c.rule: c for c in checks}


@pytest.fixture
def good(tmp_path):
    (tmp_path / "path.json").write_text(json.dumps(GOOD))
    return by_rule(C.critique(tmp_path))


@pytest.fixture
def bad(tmp_path):
    (tmp_path / "path.json").write_text(json.dumps(BAD))
    return by_rule(C.critique(tmp_path))


def test_a_clean_run_has_no_blocking_failures(good):
    fails = [r for r, c in good.items() if c.status == C.FAIL]
    assert not fails, fails


def test_missing_layer_three_fails(bad):
    assert bad["every entry says where the thinking is"].status == C.FAIL


def test_read_section_four_is_not_layer_three(tmp_path):
    """annotation.md forbids exactly this phrasing, so the check must catch it."""
    d = json.loads(json.dumps(GOOD))
    d["entries"][0]["where_the_thinking_is"] = "Read section 4."
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path))["every entry says where the thinking is"].status == C.FAIL


def test_repo_entry_that_is_only_a_url_fails(bad):
    """repos.md: the reader can find the URL. This was a real failure in run one."""
    assert bad["repo entries name a file or a function"].status == C.FAIL


def test_repo_entry_naming_a_file_passes(good):
    assert good["repo entries name a file or a function"].status == C.OK


def test_placeholder_thesis_fails_but_honest_none_passes(bad, tmp_path):
    assert bad["group theses are real or honestly null"].status == C.FAIL
    d = json.loads(json.dumps(GOOD))
    d["groups"][0]["thesis"] = None
    d["groups"][0].pop("thesis_source")
    d["groups"][0]["thesis_none_why"] = ("They publish across four unrelated areas because "
                                         "that is what the students chose.")
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path))["group theses are real or honestly null"].status == C.OK


def test_thesis_without_a_source_fails(tmp_path):
    d = json.loads(json.dumps(GOOD))
    d["groups"][0].pop("thesis_source")
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path))["group theses are real or honestly null"].status == C.FAIL


def test_dangling_group_chip_fails(bad):
    """The failure I missed by eye in run one and the grader caught."""
    assert bad["group chips resolve"].status == C.FAIL


def test_empty_unverified_list_fails(bad):
    """sourcing.md: an empty could-not-verify means the run hid something."""
    assert bad["could-not-verify is populated"].status == C.FAIL


def test_experiential_idea_with_no_project_fails(bad):
    assert bad["experiential ideas identified"].status == C.FAIL


def test_single_kind_path_fails(tmp_path):
    d = json.loads(json.dumps(GOOD))
    for e in d["entries"]:
        e["kind"] = "paper"
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path))["all three kinds represented"].status == C.FAIL


def test_report_tells_and_em_dashes_are_counted(bad):
    assert by_rule([c for c in C.check_voice(
        "This document explores a robust and crucial framework.", "x")])[
        "x: no report tells"].status == C.FAIL
    assert by_rule(C.check_voice("A sentence — with a dash.", "x"))[
        "x: zero em dashes"].status == C.FAIL


def test_anchoring_reports_rather_than_scores(tmp_path):
    """A reading problem given a threshold returns a confident wrong answer."""
    (tmp_path / "path.json").write_text(json.dumps(GOOD))
    c = by_rule(C.critique(tmp_path, deep_terms=["orderings"]))["anti-anchoring sweep"]
    assert c.status in (C.OK, C.LOOK)
    assert c.status != C.FAIL


def test_a_default_run_may_not_address_a_particular_reader(tmp_path):
    """A path built around one person's history is a worse artifact for everyone
    else, and it is the difference between a page you can send to a colleague and
    one you cannot."""
    RULE = "a default run addresses no particular reader"
    d = json.loads(json.dumps(GOOD))
    d["entries"][0]["conditioning"] = "Position one because you have already read DreamerV3."
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path, personalized=False))[RULE].status == C.FAIL
    assert by_rule(C.critique(tmp_path, personalized=True))[RULE].status == C.OK
    (tmp_path / "path.json").write_text(json.dumps(GOOD))
    assert by_rule(C.critique(tmp_path, personalized=False))[RULE].status == C.OK


def test_ordinary_second_person_is_not_flagged(tmp_path):
    """"you can skip section 4" is normal technical writing. A check that fails it
    would make every path unwritable."""
    d = json.loads(json.dumps(GOOD))
    d["entries"][0]["summary"] = "You can skip section 4; read table 3 instead."
    (tmp_path / "path.json").write_text(json.dumps(d))
    assert by_rule(C.critique(tmp_path, personalized=False))[
        "a default run addresses no particular reader"].status == C.OK

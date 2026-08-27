"""What the reader has already read, resolved from a folder of PDFs.

Every case here is a file shape found in the real reading log. The failures that
matter are not crashes: they are a junk string emitted as a paper title, which
reaches the resolver as a search query and comes back with something confidently
wrong.
"""
from __future__ import annotations

import pathlib

import pytest

from scripts import readlog as R


def pdf(tmp_path, name: str, title: bytes | None = None, body: bytes = b"") -> pathlib.Path:
    p = tmp_path / name
    head = b"%PDF-1.4\n"
    meta = b"/Title (" + title + b")\n" if title else b""
    p.write_bytes(head + meta + body)
    return p


def test_a_browser_printed_pdf_does_not_emit_about_blank_as_a_title(tmp_path):
    """Observed in the real log. `about:blank` is the dangerous shape: it looks
    like a resolved title rather than an error, so it reaches the resolver as a
    search string instead of being reported as unresolved."""
    p = pdf(tmp_path, "cold_attacks.pdf", b"about:blank")
    e = R.resolve_one(p)
    assert "about" not in (e.title or "").lower()
    assert e.title == "cold attacks" and e.how == "filename"


# One prefix-shaped stamp and one exact match. The other cases in this family
# were removed: they exercised the same branch and killed no mutation the first
# two did not already kill.
@pytest.mark.parametrize("junk", [b"Microsoft Word - draft.docx", b"untitled"])
def test_other_junk_pdf_titles_fall_through_to_the_filename(tmp_path, junk):
    e = R.resolve_one(pdf(tmp_path, "dreamerv3.pdf", junk))
    assert e.title == "dreamerv3" and e.how == "filename"


def test_mojibake_from_a_binary_stream_is_never_a_title(tmp_path):
    """A stream that decompressed but is not text produced
    `½­qhµ=Yð0jàEü-pv­ÆÖ²ôs` in a real scan. It passed the length check."""
    # Chosen so ONLY the letters-ratio guard rejects it: it has word breaks and
    # a run of ascii letters, so the other two guards let it through.
    assert not R._looks_like_prose("½­ Yð0 jàÜ ñö abc û ¸Úæ ½­ ð0 àÜ ñö û ¸Úæ ½­")
    assert R._looks_like_prose("Simple and Effective Masked Diffusion Language Models")
    assert not R._looks_like_prose("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), "no word breaks"


def test_the_first_page_extractor_refuses_to_return_mojibake(tmp_path):
    """The guard has to sit at the call site as well as in the predicate. A page
    whose only text stream decodes to noise must yield no title at all, not a
    title made of noise."""
    stream = (b"BT (" + "½­ Yð0 jàÜ ñö abc û ¸Úæ ½­ ð0 àÜ ñö û".encode("latin-1")
              + b") Tj ET")
    body = b"stream\n" + stream + b"\nendstream"
    assert R._first_page_title(body) is None


def test_an_unresolvable_file_is_reported_rather_than_counted_as_read(tmp_path):
    """A silently dropped paper reappears on the reading path, and recommending
    something the reader finished last year is how the document loses them."""
    (tmp_path / "sub").mkdir()
    pdf(tmp_path / "sub", "2406.07524v2.pdf")
    pdf(tmp_path / "sub", "1.pdf")            # junk stem, no metadata, no text
    s = R.scan(tmp_path)
    assert len(s["entries"]) == 1 and len(s["unresolved"]) == 1
    assert s["entries"][0]["arxiv"] == "2406.07524"


def test_an_arxiv_id_in_the_filename_wins_and_keeps_no_version(tmp_path):
    e = R.resolve_one(pdf(tmp_path, "2406.07524v3.pdf", b"Some Other Title Entirely"))
    assert e.arxiv == "2406.07524" and e.confidence == "high"


def test_folder_names_are_the_readers_own_taxonomy(tmp_path):
    (tmp_path / "protein_folding").mkdir()
    pdf(tmp_path / "protein_folding", "alphafold2.pdf")
    s = R.scan(tmp_path)
    assert R.topics_matching(s, ["protein", "folding"]) == ["protein_folding"]
    assert R.topics_matching(s, ["robotics"]) == []

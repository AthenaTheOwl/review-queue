"""Strict unified-diff application for edit verdicts."""
from __future__ import annotations

import pytest

from review_queue import diff

BEFORE = "one\ntwo\nthree\nfour\n"


def test_round_trips_a_diff_built_by_unified_text_diff() -> None:
    after = "one\n2\nthree\nfour\nfive\n"
    patch = diff.unified_text_diff(BEFORE, after)
    assert diff.apply_unified_diff(BEFORE, patch) == after


def test_applies_multiple_hunks_and_pure_insertions() -> None:
    patch = "@@ -1,0 +2 @@\n+one-and-a-half\n@@ -4 +5 @@\n-four\n+4\n"
    assert diff.apply_unified_diff(BEFORE, patch) == "one\none-and-a-half\ntwo\nthree\n4\n"


def test_honours_no_newline_markers() -> None:
    patch = "@@ -1 +1 @@\n-last\n\\ No newline at end of file\n+last\n"
    assert diff.apply_unified_diff("last", patch) == "last\n"


def test_a_patch_missing_its_final_newline_still_ends_lines() -> None:
    # `--edit-diff "$(cat edit.diff)"` drops the trailing newline.
    assert diff.apply_unified_diff(BEFORE, "@@ -4 +4 @@\n-four\n+4") == "one\ntwo\nthree\n4\n"


def test_only_lf_ends_a_line() -> None:
    before = "page one\x0cpage two\n"
    patch = "@@ -1 +1 @@\n-page one\x0cpage two\n+page one\x0cpage 2\n"
    assert diff.apply_unified_diff(before, patch) == "page one\x0cpage 2\n"


def test_edit_applies_to_the_newline_normalised_review_text() -> None:
    patch = "@@ -2 +2 @@\n-b\n+B\n"
    assert diff.apply_edit(b"a\r\nb\r\n", patch) == b"a\nB\n"


@pytest.mark.parametrize(
    "patch, message",
    [
        ("-two\n+2\n", "no @@ hunk"),
        ("@@ -2 +2 @@\n-TWO\n+2\n", "does not match the candidate"),
        ("@@ -2,2 +2,2 @@\n-two\n+2\n", "truncated"),
        ("@@ -2 +2 @@\n-two\n-three\n+2\n", "more old lines"),
        ("@@ -2 +2 @@\n-two\n+2\n+3\n", "unexpected line"),
        ("@@ -2 +2 @@\n+2\n+3\n-two\n", "more new lines"),
        ("@@ -9 +9 @@\n-nine\n+9\n", "outside the candidate"),
        ("@@ -3 +3 @@\n-three\n+3\n@@ -2 +2 @@\n-two\n+2\n", "overlaps"),
        ("@@ -2 +2 @@\n*two\n", "unrecognised line"),
    ],
)
def test_refuses_a_diff_that_does_not_apply_cleanly(patch: str, message: str) -> None:
    with pytest.raises(diff.PatchError, match=message):
        diff.apply_unified_diff(BEFORE, patch)


def test_an_empty_context_line_without_its_leading_space_still_matches() -> None:
    assert diff.apply_unified_diff("a\n\nb\n", "@@ -1,3 +1,3 @@\n a\n\n-b\n+B\n") == "a\n\nB\n"

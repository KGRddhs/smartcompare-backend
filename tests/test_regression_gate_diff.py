"""Tests for scripts/regression_gate_diff.py — the Phase 7.3 free-unit
regression-gate diff helper (Faithful-Results bundle).

Plan: docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-plan.md Task 7.3.

The free-unit suite has a known baseline of pre-existing failures (captured in
tests/.pre_impl_failures.txt BEFORE any team impl landed). A "no regressions"
claim means: no test that was GREEN at baseline turned RED — i.e. the post-merge
failure set introduces no id absent from the baseline. This helper does that set
diff so 7.3 is push-button and the gate denominator is the real baseline, never
zero. Pure functions + a thin CLI; no network, no cost.
"""
from __future__ import annotations

from pathlib import Path

from scripts import regression_gate_diff as rgd


REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = REPO_ROOT / "tests" / ".pre_impl_failures.txt"


# ---------------------------------------------------------------------------
# parse_failure_ids — tolerant of the pytest "FAILED " prefix + blank lines
# ---------------------------------------------------------------------------

def test_parse_failure_ids_strips_failed_prefix_and_blanks():
    text = (
        "FAILED tests/test_a.py::test_one - AssertionError: x\n"
        "tests/test_b.py::test_two\n"
        "\n"
        "   \n"
        "FAILED tests/test_c.py::TestK::test_three\n"
    )
    ids = rgd.parse_failure_ids(text)
    assert ids == {
        "tests/test_a.py::test_one",
        "tests/test_b.py::test_two",
        "tests/test_c.py::TestK::test_three",
    }


def test_parse_failure_ids_drops_trailing_reason_after_dash():
    # pytest -q summary lines append ' - <reason>'; the id is everything before.
    ids = rgd.parse_failure_ids("FAILED tests/x.py::t - some - dashed - reason\n")
    assert ids == {"tests/x.py::t"}


def test_parse_failure_ids_empty_text_is_empty_set():
    assert rgd.parse_failure_ids("") == set()
    assert rgd.parse_failure_ids("\n\n  \n") == set()


# ---------------------------------------------------------------------------
# diff_failures — NEW (regressions) vs FIXED vs still-known
# ---------------------------------------------------------------------------

def test_diff_failures_flags_new_regressions():
    baseline = {"a", "b"}
    current = {"a", "c"}  # b fixed, c is NEW
    result = rgd.diff_failures(current, baseline)
    assert result.new_failures == {"c"}
    assert result.fixed == {"b"}
    assert result.still_failing == {"a"}
    assert result.has_regression is True


def test_diff_failures_no_regression_when_subset_of_baseline():
    baseline = {"a", "b", "c"}
    current = {"a", "b"}  # only baseline failures (one even fixed)
    result = rgd.diff_failures(current, baseline)
    assert result.new_failures == set()
    assert result.has_regression is False
    assert result.fixed == {"c"}


def test_diff_failures_identical_sets_no_regression():
    s = {"a", "b"}
    result = rgd.diff_failures(set(s), set(s))
    assert result.new_failures == set()
    assert result.fixed == set()
    assert result.has_regression is False


def test_diff_failures_all_green_current_no_regression():
    result = rgd.diff_failures(set(), {"a", "b"})
    assert result.has_regression is False
    assert result.fixed == {"a", "b"}


# ---------------------------------------------------------------------------
# load_baseline — reads the committed baseline file (UTF-8)
# ---------------------------------------------------------------------------

def test_load_baseline_reads_committed_file():
    ids = rgd.load_baseline(BASELINE_FILE)
    # The committed baseline has 59 ids at capture; assert shape, not the exact
    # count (it may be re-captured) — every id is a pytest nodeid.
    assert len(ids) >= 1
    assert all("::" in i for i in ids)
    # A couple of the documented baseline members are present.
    assert any("test_value_math.py" in i for i in ids)


def test_load_baseline_missing_file_is_empty_set(tmp_path):
    """A missing baseline file -> empty set (so the gate treats every failure as
    new — fail-LOUD, never silently passes by assuming no baseline)."""
    assert rgd.load_baseline(tmp_path / "nope.txt") == set()


# ---------------------------------------------------------------------------
# format_report — human summary
# ---------------------------------------------------------------------------

def test_format_report_lists_new_failures_and_is_ascii():
    result = rgd.diff_failures({"tests/x.py::t_new"}, set())
    text = rgd.format_report(result)
    assert "tests/x.py::t_new" in text
    assert "REGRESSION" in text.upper()
    text.encode("ascii")  # ASCII-only (Windows cp1252 capture-log trap)


def test_format_report_clean_when_no_regression():
    result = rgd.diff_failures({"a"}, {"a", "b"})
    text = rgd.format_report(result)
    low = text.lower()
    assert "no regression" in low or "no new" in low

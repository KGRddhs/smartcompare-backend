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


# ---------------------------------------------------------------------------
# Network-flaky exclude set — a flaky test never counts as a regression
# ---------------------------------------------------------------------------

def test_excluded_flaky_test_is_not_a_regression():
    """A network-flaky test (absent from baseline) that fails in the current run
    must NOT be flagged as a NEW regression — it's reported as excluded_failing."""
    flaky = next(iter(rgd.NETWORK_FLAKY_EXCLUDE))
    result = rgd.diff_failures({flaky}, set())  # flaky failed, not in baseline
    assert result.new_failures == set()
    assert result.has_regression is False
    assert flaky in result.excluded_failing


def test_excluded_flaky_alongside_real_regression():
    """A real regression still trips the gate even when a flaky also failed."""
    flaky = next(iter(rgd.NETWORK_FLAKY_EXCLUDE))
    result = rgd.diff_failures({flaky, "tests/real.py::t_reg"}, set())
    assert result.new_failures == {"tests/real.py::t_reg"}
    assert result.has_regression is True
    assert flaky in result.excluded_failing


def test_exclude_set_removed_from_baseline_too():
    """If a flaky test is (historically) in the baseline, it's removed from BOTH
    sides so it can't show up as 'fixed' either — fully neutral."""
    flaky = next(iter(rgd.NETWORK_FLAKY_EXCLUDE))
    result = rgd.diff_failures(set(), {flaky})  # flaky in baseline, passed now
    assert result.fixed == set()  # not counted as a fix
    assert result.new_failures == set()


def test_custom_exclude_overrides_default():
    result = rgd.diff_failures({"tests/x.py::t"}, set(), exclude={"tests/x.py::t"})
    assert result.new_failures == set()
    assert "tests/x.py::t" in result.excluded_failing


def test_known_network_flaky_members_present():
    """The price-cache-bust probe (Backend-flagged) + the real-GET rate-limit
    test are in the exclude set."""
    excl = rgd.NETWORK_FLAKY_EXCLUDE
    assert any("test_price_cache_bust_probe.py" in e for e in excl)
    assert any("test_rate_limiting_complete.py" in e for e in excl)


def test_format_report_shows_ignored_flaky():
    flaky = next(iter(rgd.NETWORK_FLAKY_EXCLUDE))
    result = rgd.diff_failures({flaky}, set())
    text = rgd.format_report(result)
    assert "net-flaky" in text.lower() or "ignored" in text.lower()
    text.encode("ascii")


# ---------------------------------------------------------------------------
# Canonical baseline default — reconciled identical to QA's source of truth
# ---------------------------------------------------------------------------

def test_default_baseline_matches_committed_snapshot_set():
    """The harness DEFAULT baseline (QA canonical when on disk, else the local
    mirror) must be set-identical to the committed local mirror — proving the
    dispatcher's 'ONE ignore-set' invariant holds (QA == mirror). LOCKED at 48
    (QA full-cred capture; the partial-cred 59 was discarded)."""
    default_ids = rgd.load_baseline(rgd.DEFAULT_BASELINE)
    mirror_ids = rgd.load_baseline(BASELINE_FILE)
    assert default_ids == mirror_ids


def test_local_mirror_is_locked_48():
    """The committed mirror is exactly the LOCKED 48-node canonical (re-synced
    from QA). A drift here means someone forked the ignore-set — reconcile."""
    mirror_ids = rgd.load_baseline(BASELINE_FILE)
    assert len(mirror_ids) == 48, (
        f"local mirror has {len(mirror_ids)} nodes, expected the LOCKED 48 "
        f"(re-sync from QA's .qa-discovery/BASELINE_FAILURES.txt)"
    )
    # The 9 youtube + invitee_quiz partial-cred artifacts must be GONE.
    assert not any("test_youtube" in i for i in mirror_ids)
    assert not any("test_invitee_quiz" in i for i in mirror_ids)


# ---------------------------------------------------------------------------
# main() CLI — exit 0 clean / 1 regression / 3 bad input
# ---------------------------------------------------------------------------

def test_main_exit_0_when_current_is_subset_of_baseline(tmp_path):
    """A current FAILED set ⊆ baseline → exit 0 (no regression)."""
    base = tmp_path / "base.txt"
    base.write_text("tests/a.py::t1\ntests/b.py::t2\n", encoding="utf-8")
    cur = tmp_path / "cur.txt"
    cur.write_text("FAILED tests/a.py::t1 - boom\n", encoding="utf-8")  # subset
    rc = rgd.main(["--current", str(cur), "--baseline", str(base)])
    assert rc == 0


def test_main_exit_1_on_new_failure(tmp_path, capsys):
    base = tmp_path / "base.txt"
    base.write_text("tests/a.py::t1\n", encoding="utf-8")
    cur = tmp_path / "cur.txt"
    cur.write_text("tests/a.py::t1\ntests/new.py::t_reg\n", encoding="utf-8")
    rc = rgd.main(["--current", str(cur), "--baseline", str(base)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "tests/new.py::t_reg" in out


def test_main_exit_3_on_unreadable_current(tmp_path, capsys):
    rc = rgd.main(["--current", str(tmp_path / "missing.txt")])
    assert rc == 3
    assert "ERROR" in capsys.readouterr().err


def test_main_excludes_network_flaky(tmp_path):
    """A current set that adds ONLY a network-flaky test → exit 0 (the exclude
    neutralizes it even via the CLI)."""
    flaky = next(iter(rgd.NETWORK_FLAKY_EXCLUDE))
    base = tmp_path / "base.txt"
    base.write_text("tests/a.py::t1\n", encoding="utf-8")
    cur = tmp_path / "cur.txt"
    cur.write_text(f"tests/a.py::t1\n{flaky}\n", encoding="utf-8")
    rc = rgd.main(["--current", str(cur), "--baseline", str(base)])
    assert rc == 0

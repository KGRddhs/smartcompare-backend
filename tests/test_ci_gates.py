"""CI gate configuration tests — issue #49 (`.github/workflows/*`).

CI has been RED on main since at least 2026-07-07. Two root causes:

  (a) a missing dev dependency (owned by #46, not this file), and
  (b) `tests/test_value_math.py` — 35 RED-by-design TDD stubs for the
      unimplemented Bundle C v1.1 value-math functions. CLAUDE.md:399 and
      `tests/PRE_IMPL_FAILURE_BASELINE.md` both document them as known-RED and
      "not a regression", but CI never learned that, so every PR merged against
      a red build and the signal was worthless.

This module is the executable half of the fix: it pins the *shape* of the CI
configuration so the gates cannot be silently deleted or watered down. Every
assertion here is about a file on disk (workflow YAML, the black allowlist,
the xfail marker) — no network, no credentials, no cost.

Deliberately NOT asserted: that the audits pass. Installing the gates and
recording the current state is #49; fixing what they report is separate work.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_YML = WORKFLOWS / "ci.yml"
LIVE_YML = WORKFLOWS / "live-suite.yml"
BLACK_ALLOWLIST = REPO_ROOT / ".github" / "black-clean-paths.txt"


def _load(path: Path) -> dict:
    assert path.exists(), f"missing workflow file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(cfg: dict) -> dict:
    """YAML 1.1 parses the bare key `on` as the boolean True — handle both."""
    on = cfg.get("on", cfg.get(True))
    assert isinstance(on, dict), f"expected a mapping of triggers, got {on!r}"
    return on


def _steps(job: dict) -> list:
    return list(job.get("steps") or [])


def _run_text(job: dict) -> str:
    return "\n".join(str(s.get("run", "")) for s in _steps(job))


def _allowlist_entries() -> list:
    return [
        line.strip()
        for line in BLACK_ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


# ---------------------------------------------------------------------------
# 1. Known-RED containment — the actual reason CI is red
# ---------------------------------------------------------------------------


def test_value_math_stubs_are_marked_xfail_not_left_failing():
    """The 35 Bundle C v1.1 stubs must report as xfail, not as failures.

    They stay collected and RUN (xfail executes the body) so the day the
    implementation lands they turn XPASS and become visible — unlike a skip or
    a deletion, which would lose the spec coverage entirely.
    """
    import tests.test_value_math as value_math

    marks = getattr(value_math, "pytestmark", None)
    assert marks, (
        "tests/test_value_math.py has no module-level pytestmark — its 35 "
        "RED-by-design stubs still fail the CI build"
    )
    if not isinstance(marks, list):
        marks = [marks]
    xfails = [m for m in marks if m.name == "xfail"]
    assert xfails, f"expected a module-level xfail mark, got {[m.name for m in marks]}"


def test_value_math_xfail_is_non_strict_and_explains_itself():
    """Non-strict so shipping A.6.x does not flip CI red on the same day, and
    the reason must name the tracking so the file cannot become a dumping
    ground for unrelated red tests."""
    import tests.test_value_math as value_math

    marks = getattr(value_math, "pytestmark", [])
    if not isinstance(marks, list):
        marks = [marks]
    xfail_marks = [m for m in marks if m.name == "xfail"]
    assert len(xfail_marks) == 1, f"expected exactly one xfail mark, got {xfail_marks}"
    xfail = xfail_marks[0]
    assert xfail.kwargs.get("strict") is False, (
        "the module xfail must be strict=False — strict=True would turn the "
        "whole file red the moment Bundle C v1.1 ships"
    )
    reason = str(xfail.kwargs.get("reason", ""))
    assert (
        "bundle c" in reason.lower()
    ), f"xfail reason must name the tracking, got {reason!r}"


# ---------------------------------------------------------------------------
# 2. ci.yml — the existing gates must survive untouched
# ---------------------------------------------------------------------------


def test_ci_keeps_existing_backend_and_frontend_jobs():
    jobs = _load(CI_YML)["jobs"]
    assert "backend-tests" in jobs
    assert "frontend-typecheck" in jobs


def test_ci_pr_gate_marker_selection_is_unchanged():
    """#49 must not touch the PR gate's marker selection — live_unit / live_db
    / integration stay excluded from the PR run (issue #49, Out of scope)."""
    jobs = _load(CI_YML)["jobs"]
    run = _run_text(jobs["backend-tests"])
    assert "not (live_unit or live_db or integration)" in run
    assert "--ignore=tests/test_integration.py" in run


# ---------------------------------------------------------------------------
# 3. ci.yml — new lint job
# ---------------------------------------------------------------------------


def test_ci_has_a_lint_job_running_black():
    jobs = _load(CI_YML)["jobs"]
    assert "backend-lint" in jobs, f"no backend-lint job; jobs = {sorted(jobs)}"
    assert "black" in _run_text(jobs["backend-lint"])


def test_lint_job_blocks_on_the_allowlist_and_only_reports_repo_wide_drift():
    """Scoping: the repo is 603/618 files off black at c630436, so a repo-wide
    `--check` cannot block. The allowlist step blocks (a real ratchet from day
    one); the repo-wide step reports and is explicitly non-blocking."""
    jobs = _load(CI_YML)["jobs"]
    check_steps = [
        s
        for s in _steps(jobs["backend-lint"])
        if "black --check" in str(s.get("run", ""))
    ]
    assert check_steps, "backend-lint runs no `black --check` at all"

    blocking = [s for s in check_steps if s.get("continue-on-error") is not True]
    reporting = [s for s in check_steps if s.get("continue-on-error") is True]

    assert len(blocking) == 1, (
        "expected exactly one blocking black step, got "
        f"{[s.get('name') for s in blocking]}"
    )
    assert BLACK_ALLOWLIST.name in str(blocking[0]["run"]), (
        "the blocking black step must be scoped to the clean-paths allowlist — "
        "a repo-wide blocking check would fail on 603 pre-existing files"
    )

    assert reporting, "no non-blocking repo-wide black drift report step"
    assert any(
        "app/" in str(s["run"]) for s in reporting
    ), "the drift report must cover the tree, not just the allowlist"


def test_black_allowlist_exists_and_every_entry_is_a_real_file():
    assert BLACK_ALLOWLIST.exists(), f"missing {BLACK_ALLOWLIST}"
    entries = _allowlist_entries()
    assert entries, "the black allowlist is empty — the lint gate would be a no-op"
    missing = [e for e in entries if not (REPO_ROOT / e).exists()]
    assert not missing, f"allowlist references non-existent paths: {missing}"


def test_black_allowlist_entries_are_actually_clean():
    """The allowlist is a ratchet, so adding a dirty file to it must fail here
    rather than in CI. Skips when black (a dev-only dependency) is absent."""
    black = pytest.importorskip("black", reason="black is a dev-only dependency")
    mode = black.Mode()
    dirty = []
    for entry in _allowlist_entries():
        src = (REPO_ROOT / entry).read_text(encoding="utf-8")
        try:
            black.format_file_contents(src, fast=True, mode=mode)
        except black.NothingChanged:
            continue
        dirty.append(entry)
    assert not dirty, f"allowlisted files are not black-clean: {dirty}"


# ---------------------------------------------------------------------------
# 4. ci.yml — dependency audits (non-blocking reporting)
# ---------------------------------------------------------------------------


def test_ci_has_a_non_blocking_dependency_audit_job():
    jobs = _load(CI_YML)["jobs"]
    assert "dependency-audit" in jobs, f"no dependency-audit job; jobs = {sorted(jobs)}"
    job = jobs["dependency-audit"]
    run = _run_text(job)
    assert "pip-audit" in run, "pip-audit is not run"
    assert "npm audit" in run and "--audit-level=high" in run, "npm audit is not run"

    audit_steps = [
        s
        for s in _steps(job)
        if "pip-audit" in str(s.get("run", "")) or "npm audit" in str(s.get("run", ""))
    ]
    assert audit_steps
    assert all(s.get("continue-on-error") is True for s in audit_steps), (
        "audit steps must be non-blocking reporting until #46 lands a pinned "
        "lock and the current advisory count is triaged"
    )


# ---------------------------------------------------------------------------
# 5. live-suite.yml — the scheduled scraper-drift detector
# ---------------------------------------------------------------------------


def test_live_suite_workflow_exists_and_is_scheduled_only():
    on = _triggers(_load(LIVE_YML))
    assert "schedule" in on, "the live suite must run on a cron schedule"
    assert "workflow_dispatch" in on, "the live suite must be manually dispatchable"
    assert (
        "pull_request" not in on
    ), "the live suite must never run on PRs (real credits)"
    assert "push" not in on, "the live suite must never run on push (real credits)"


def test_live_suite_cron_is_weekly_not_nightly():
    on = _triggers(_load(LIVE_YML))
    crons = [entry["cron"] for entry in on["schedule"]]
    assert crons, "schedule trigger has no cron entry"
    for cron in crons:
        fields = cron.split()
        assert len(fields) == 5, f"malformed cron {cron!r}"
        day_of_month, day_of_week = fields[2], fields[4]
        assert day_of_month != "*" or day_of_week != "*", (
            f"cron {cron!r} runs daily or more often — the live suite spends "
            "real Serper/OpenAI credits and must be weekly (issue #49)"
        )


def test_live_suite_runs_the_live_unit_marker():
    jobs = _load(LIVE_YML)["jobs"]
    run = "\n".join(_run_text(job) for job in jobs.values())
    assert re.search(
        r"-m\s+[\"']?live_unit", run
    ), f"live_unit marker not selected: {run!r}"


def test_live_suite_opens_an_issue_on_failure():
    jobs = _load(LIVE_YML)["jobs"]
    steps = [s for job in jobs.values() for s in _steps(job)]
    reporters = [s for s in steps if "github-script" in str(s.get("uses", ""))]
    assert reporters, "no actions/github-script step — a silent red run can be ignored"
    assert any(
        "failure()" in str(s.get("if", "")) for s in reporters
    ), "the issue-opening step must be gated on failure()"


def test_live_suite_documents_its_credit_cost():
    """Comments are stripped by the YAML parser, so read the raw text."""
    raw = LIVE_YML.read_text(encoding="utf-8").lower()
    assert (
        "credit" in raw
    ), "the live workflow must state that it spends real vendor credits"

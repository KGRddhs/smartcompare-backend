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

import ast
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_YML = WORKFLOWS / "ci.yml"
LIVE_YML = WORKFLOWS / "live-suite.yml"
BLACK_ALLOWLIST = REPO_ROOT / ".github" / "black-clean-paths.txt"

# The production deployment. Any live test whose HTTP target is this host makes
# the PRODUCTION server resolve a price and write it to the production price
# cache + L2 DB — `?nocache=true` bypasses the READ only. Such tests must carry
# `live_prod` so the scheduled workflow can deselect them.
PROD_HOST = "web-production-58776"


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


# The A.6.x surface the module xfail in tests/test_value_math.py is amnesty for.
# When ALL of these exist, the implementation has landed and the blanket xfail
# must come off — a `strict=False` mark on a shipped feature is a file that can
# never go red again.
A6X_SYMBOLS = {
    "app.services.scoring_service": (
        "VALUE_FORMULA_BY_PRIORITY",
        "_compute_value_score",
        "_classify_value_match",
        "_classify_budget_mismatch",
    ),
    "app.services.response_builder": (
        "build_value_delta_text",
        "build_value_match_caption",
    ),
}


def _missing_a6x_symbols() -> list:
    import importlib

    missing = []
    for module_name, symbols in A6X_SYMBOLS.items():
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 — a missing module is a missing symbol
            missing.extend(f"{module_name}.{s}" for s in symbols)
            continue
        missing.extend(f"{module_name}.{s}" for s in symbols if not hasattr(module, s))
    return missing


def test_value_math_xfail_expires_when_a6x_ships():
    """The bound on a blanket, non-strict, permanent xfail.

    `strict=False` means the file reports green whether the stubs fail OR pass,
    so once A.6.x lands a *buggy* implementation would sit behind the marker
    forever. This test is the expiry: the day every A.6.x symbol exists it goes
    RED and the implementing PR has to delete the pytestmark.

    Narrowing the mark with `raises=` was the other option and was measured to
    be wrong here — 11 of the 35 nodes fail with AssertionError because
    `VALUE_FORMULA_BY_PRIORITY` already exists with pre-v1.1 coefficients. See
    the comment block above the pytestmark in tests/test_value_math.py.
    """
    import tests.test_value_math as value_math

    marks = getattr(value_math, "pytestmark", [])
    if not isinstance(marks, list):
        marks = [marks]
    if not [m for m in marks if m.name == "xfail"]:
        return  # marker already removed — nothing left to expire

    missing = _missing_a6x_symbols()
    assert missing, (
        "every Bundle C v1.1 A.6.x symbol now exists, so the module-level "
        "xfail in tests/test_value_math.py is no longer containment — it is "
        "blanket amnesty for a shipped feature. Delete the pytestmark (and the "
        "-rxX note in ci.yml) in the PR that ships A.6.x."
    )


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
    lint = jobs["backend-lint"]

    # A job-level `continue-on-error: true` would neuter the blocking step below
    # without touching it, and a step-level-only check would not notice.
    assert lint.get("continue-on-error") is not True, (
        "backend-lint carries a JOB-level continue-on-error — every step in it, "
        "including the BLOCKING black check, becomes advisory"
    )

    check_steps = [s for s in _steps(lint) if "black --check" in str(s.get("run", ""))]
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


def test_black_is_pinned_to_an_exact_version_in_ci():
    """A floating `black>=26.1.0,<27.0.0` makes a BLOCKING step depend on which
    26.x shipped that morning: a formatting change in a point release turns the
    build red with no code change. Pin to the version the allowlist was
    measured against."""
    # Read the parsed `run:` bodies, not the raw file — a comment quoting the old
    # range would otherwise fail (or mask) this check.
    jobs = _load(CI_YML)["jobs"]
    run = "\n".join(_run_text(job) for job in jobs.values())
    installs = [
        line for line in run.splitlines() if "black" in line and "install" in line
    ]
    assert installs, "ci.yml never installs black"
    ranged = [i for i in installs if re.search(r"black[\"']?\s*[<>]", i)]
    assert not ranged, f"black is installed from a version RANGE in ci.yml: {ranged}"
    assert any(
        re.search(r"black==\d+\.\d+", i) for i in installs
    ), f"black is not pinned to an exact `black==X.Y.Z` version: {installs}"


def test_black_allowlist_exists_and_every_entry_is_a_real_file():
    assert BLACK_ALLOWLIST.exists(), f"missing {BLACK_ALLOWLIST}"
    entries = _allowlist_entries()
    assert entries, "the black allowlist is empty — the lint gate would be a no-op"
    missing = [e for e in entries if not (REPO_ROOT / e).exists()]
    assert not missing, f"allowlist references non-existent paths: {missing}"


def _black_mode():
    """Build black's Mode the way its CLI does — from pyproject.toml.

    `black.Mode()` uses library defaults. The CI step runs `python -m black`,
    which reads `[tool.black]`. There is no such section today so the two agree,
    but the day one is added (line-length, target-version, preview) this guard
    and the gate would diverge silently in opposite directions.
    """
    import black

    cfg_path = black.find_pyproject_toml((str(REPO_ROOT),))
    cfg = black.parse_pyproject_toml(cfg_path) if cfg_path else {}
    kwargs = {}
    if "line_length" in cfg:
        kwargs["line_length"] = int(cfg["line_length"])
    if "preview" in cfg:
        kwargs["preview"] = bool(cfg["preview"])
    if "skip_string_normalization" in cfg:
        kwargs["string_normalization"] = not bool(cfg["skip_string_normalization"])
    if cfg.get("target_version"):
        kwargs["target_versions"] = {
            black.TargetVersion[v.upper()] for v in cfg["target_version"]
        }
    return black.Mode(**kwargs)


def test_black_allowlist_entries_are_actually_clean():
    """The allowlist is a ratchet, so adding a dirty file to it must fail here
    rather than in CI. `backend-tests` installs black at the same pin as
    `backend-lint`, so this no longer silently skips on the runner."""
    black = pytest.importorskip("black", reason="black is a dev-only dependency")
    mode = _black_mode()
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
# 4. ci.yml — dependency audits (non-blocking reporting) and coverage
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


def test_backend_tests_measure_and_floor_coverage():
    """Issue #49 section C. Coverage must be REPORTED on every backend run and
    floored at a measured baseline, so a coverage collapse cannot merge."""
    jobs = _load(CI_YML)["jobs"]
    backend = jobs["backend-tests"]
    run = _run_text(backend)

    assert "pytest-cov" in run, "backend-tests never installs pytest-cov"
    assert "--cov=app" in run, "backend-tests does not measure coverage of app/"
    assert (
        "--cov-report=term-missing" in run
    ), "coverage is measured but not reported in the run log"

    floor = re.search(r"--cov-fail-under=(\d+(?:\.\d+)?)", run)
    assert floor, (
        "no --cov-fail-under floor: coverage would be reported but a collapse "
        "would still merge green"
    )
    assert float(floor.group(1)) > 0, "a floor of 0 is not a floor"

    cov_steps = [s for s in _steps(backend) if "--cov=app" in str(s.get("run", ""))]
    assert cov_steps and all(
        s.get("continue-on-error") is not True for s in cov_steps
    ), "the coverage step must be blocking, else the floor is decorative"


# ---------------------------------------------------------------------------
# 5. live-suite.yml — the scheduled scraper-drift detector
# ---------------------------------------------------------------------------


def _cron_violations(cron: str) -> list:
    """Return the reasons `cron` is not a once-a-week schedule.

    A weekly cron must pin BOTH the minute and the hour to a plain integer
    (`*`, `*/n`, ranges and lists all multiply the run count, and every run
    spends real Serper/OpenAI credits), and must pin exactly one of
    day-of-month / day-of-week while leaving the other `*`.
    """
    problems = []
    fields = cron.split()
    if len(fields) != 5:
        return [f"malformed cron {cron!r}: expected 5 fields, got {len(fields)}"]

    minute, hour, dom, _month, dow = fields
    for label, field in (("minute", minute), ("hour", hour)):
        if not re.fullmatch(r"\d+", field):
            problems.append(
                f"{label} field {field!r} is not a fixed integer — "
                f"{cron!r} fires many times per day"
            )

    dom_pinned = dom != "*"
    dow_pinned = dow != "*"
    if not (dom_pinned or dow_pinned):
        problems.append(f"{cron!r} runs every day: both day fields are '*'")
    if dom_pinned and dow_pinned:
        problems.append(
            f"{cron!r} pins BOTH day-of-month and day-of-week; cron ORs them, "
            "so the real cadence is not weekly"
        )
    if dom_pinned and not dow_pinned:
        problems.append(
            f"{cron!r} pins day-of-month, so it runs MONTHLY, not weekly — "
            "the live suite must run every week"
        )
    return problems


def test_live_suite_cron_is_weekly_not_nightly():
    on = _triggers(_load(LIVE_YML))
    crons = [entry["cron"] for entry in on["schedule"]]
    assert crons, "schedule trigger has no cron entry"
    for cron in crons:
        problems = _cron_violations(cron)
        assert not problems, (
            f"live-suite cron {cron!r} is not weekly: {problems}. The live "
            "suite spends real Serper/OpenAI credits per run (issue #49)."
        )


@pytest.mark.parametrize(
    "cron,why",
    [
        ("0 4 * * *", "nightly"),
        ("0 * * * 1", "24 runs on Monday"),
        ("*/5 * * * 1", "288 runs on Monday"),
        ("*/5 4 * * 1", "12 runs in the 04:00 hour"),
        ("0 4 1 * *", "monthly, not weekly"),
        ("0 4 1 * 1", "day-of-month AND day-of-week are ORed"),
        ("0 4-6 * * 1", "an hour range is three runs"),
        ("0 4,16 * * 1", "an hour list is two runs"),
        ("0 4 * *", "malformed"),
    ],
)
def test_cron_guard_rejects_costly_schedules(cron, why):
    """The guard above is only worth trusting if it is itself proven to fail.

    The pre-#49 assertion was `day_of_month != "*" or day_of_week != "*"` — it
    never looked at the minute or the hour. Seven of the nine crons below SILENTLY
    PASSED it, including `*/5 * * * 1` (288 runs a week, ~288x the intended credit
    burn). Only `0 4 * * *` (both day fields `*`) and the malformed 4-field entry
    were caught.
    """
    assert _cron_violations(cron), f"guard accepted {cron!r} ({why})"


def test_live_suite_workflow_exists_and_is_scheduled_only():
    on = _triggers(_load(LIVE_YML))
    assert "schedule" in on, "the live suite must run on a cron schedule"
    assert "workflow_dispatch" in on, "the live suite must be manually dispatchable"
    assert (
        "pull_request" not in on
    ), "the live suite must never run on PRs (real credits)"
    assert "push" not in on, "the live suite must never run on push (real credits)"


def _live_suite_pytest_step() -> dict:
    jobs = _load(LIVE_YML)["jobs"]
    steps = [s for job in jobs.values() for s in _steps(job)]
    pytest_steps = [s for s in steps if "-m pytest" in str(s.get("run", ""))]
    assert len(pytest_steps) == 1, (
        "expected exactly one pytest step in live-suite.yml, got "
        f"{[s.get('name') for s in pytest_steps]}"
    )
    return pytest_steps[0]


def test_live_suite_runs_the_live_unit_marker():
    run = str(_live_suite_pytest_step().get("run", ""))
    assert re.search(
        r"-m\s+[\"']?live_unit", run
    ), f"live_unit marker not selected: {run!r}"


def test_live_suite_deselects_production_api_tests():
    """THE cost/safety gate of the scheduled run.

    `?nocache=true` bypasses the cache READ only. A test that calls the
    production deployment makes the PRODUCTION server run
    `should_cache_price(...) -> set_cached(...) + _save_price_to_db(...)`
    (structured_comparison_service.py:5600, :6930), so an unattended weekly run
    would seed the production price cache, insert production L2 price rows, and
    burn the production vendor budget server-side.
    """
    run = str(_live_suite_pytest_step().get("run", ""))
    assert "not live_prod" in run, (
        "the scheduled selection does not exclude live_prod — this workflow "
        "would WRITE to the production price cache and L2 DB every week"
    )


def test_live_suite_is_not_given_production_cache_credentials():
    """Second layer of the production-cache guarantee: even if a future test
    walks the price path in-process on the runner, it must not be able to reach
    production Redis or the production Supabase L2."""
    step = _live_suite_pytest_step()
    env = step.get("env") or {}

    for key in ("SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY", "UPSTASH_REDIS_TOKEN"):
        assert key in env, f"live-suite pytest step does not neutralise {key}"
        assert str(env[key]).strip() == "", (
            f"{key} is set to {env[key]!r}; an empty value is what makes "
            "set_cached a no-op and _save_price_to_db raise before any network "
            "call. A real credential here would let the scheduled run write to "
            "production."
        )

    leaked = [
        k for k, v in env.items() if re.search(r"secrets\.(SUPABASE|UPSTASH)", str(v))
    ]
    assert not leaked, (
        f"live-suite hands the runner production storage secrets: {leaked}. "
        "That re-opens the production-cache write path."
    )


def test_live_suite_step_timeout_fires_before_the_job_timeout():
    """A JOB-level timeout CANCELS the job, and `failure()` is false in a
    cancelled job — so a job-level cap alone means the most likely red (the
    suite degrading against slow storefronts) opens no issue. The step cap must
    trip first so an overrun is a step FAILURE inside a still-running job."""
    jobs = _load(LIVE_YML)["jobs"]
    job = jobs["live-unit"]
    step = _live_suite_pytest_step()

    step_cap = step.get("timeout-minutes")
    assert isinstance(step_cap, int), (
        "the live pytest step has no step-level timeout-minutes; only the job "
        "cap would fire, and a cancelled job reports nothing"
    )
    job_cap = job.get("timeout-minutes")
    assert isinstance(job_cap, int), "the live job lost its backstop timeout"
    assert step_cap < job_cap, (
        f"step cap {step_cap} must be strictly below the job cap {job_cap}, "
        "otherwise the job is cancelled before the step can fail"
    )


def test_live_suite_opens_an_issue_on_failure_or_cancellation():
    jobs = _load(LIVE_YML)["jobs"]
    steps = [s for job in jobs.values() for s in _steps(job)]
    reporters = [s for s in steps if "github-script" in str(s.get("uses", ""))]
    assert reporters, "no actions/github-script step — a silent red run can be ignored"

    guarded = [s for s in reporters if "failure()" in str(s.get("if", ""))]
    assert guarded, "the issue-opening step must be gated on failure()"
    assert any("cancelled()" in str(s.get("if", "")) for s in guarded), (
        "the reporter must also fire on cancelled(): a job-level timeout "
        "CANCELS the job, and failure() is false there, so the one failure mode "
        "the alert exists for would open no issue"
    )


def test_live_suite_failure_reporter_ignores_pull_requests():
    """`issues.listForRepo` returns pull requests too. A PR carrying the
    `live-suite-failure` label would swallow every drift comment.

    Read the github-script BODY, not the raw file: `pull_request` also appears
    in the header (documenting that this workflow has no PR trigger), so a
    whole-file substring check would pass even with the filter deleted.
    """
    jobs = _load(LIVE_YML)["jobs"]
    steps = [s for job in jobs.values() for s in _steps(job)]
    scripts = [
        str((s.get("with") or {}).get("script", ""))
        for s in steps
        if "github-script" in str(s.get("uses", ""))
    ]
    assert scripts, "no actions/github-script step"
    body = "\n".join(scripts)
    assert "listForRepo" in body, "the reporter no longer looks for an existing issue"
    assert "pull_request" in body, (
        "the reporter does not filter pull requests out of listForRepo — a "
        "labelled PR would absorb the drift comments"
    )


def test_live_suite_documents_its_credit_cost_and_its_production_audit():
    """Comments are stripped by the YAML parser, so read the raw text.

    The header is load-bearing documentation: issue #49 requires a per-file
    record of which live_unit tests are read-only with respect to the production
    price cache and which are excluded.
    """
    raw = LIVE_YML.read_text(encoding="utf-8").lower()
    assert (
        "credit" in raw
    ), "the live workflow must state that it spends real vendor credits"
    for anchor in ("production-cache audit", "excluded", "read-only", "live_prod"):
        assert anchor in raw, f"the header no longer records {anchor!r} (#49 audit)"


# ---------------------------------------------------------------------------
# 6. The live_prod marker itself — it must exist and must not rot
# ---------------------------------------------------------------------------


def _marker_names(nodes) -> set:
    """Marker names from a list of decorator / pytestmark expressions."""
    names = set()
    for node in nodes:
        expr = node.func if isinstance(node, ast.Call) else node
        parts = []
        while isinstance(expr, ast.Attribute):
            parts.append(expr.attr)
            expr = expr.value
        if isinstance(expr, ast.Name):
            parts.append(expr.id)
        parts.reverse()
        if len(parts) >= 3 and parts[0] == "pytest" and parts[1] == "mark":
            names.add(parts[2])
    return names


def _module_marker_names(tree: ast.Module) -> set:
    names = set()
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "pytestmark" for t in stmt.targets):
            continue
        value = stmt.value
        values = (
            list(value.elts) if isinstance(value, (ast.List, ast.Tuple)) else [value]
        )
        names |= _marker_names(values)
    return names


def _prod_host_constants(tree: ast.Module) -> set:
    """Module-level names bound to a string containing the production host."""
    names = set()
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        value = stmt.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            if PROD_HOST in value.value:
                names |= {getattr(t, "id", "") for t in stmt.targets}
    return {n for n in names if n}


def _live_prod_offenders(path: Path) -> list:
    """Test nodes in `path` that target the production host under `live_unit`
    without carrying `live_prod`."""
    src = path.read_text(encoding="utf-8")
    if PROD_HOST not in src:
        return []
    tree = ast.parse(src)
    module_marks = _module_marker_names(tree)
    prod_names = _prod_host_constants(tree)

    def touches_prod(node) -> bool:
        segment = ast.get_source_segment(src, node) or ""
        if PROD_HOST in segment:
            return True
        return any(re.search(rf"\b{re.escape(n)}\b", segment) for n in prod_names)

    offenders = []

    def visit(node, inherited: set):
        marks = inherited | _marker_names(node.decorator_list)
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    visit(child, marks)
            return
        if not node.name.startswith("test"):
            return
        if "live_unit" in marks and "live_prod" not in marks and touches_prod(node):
            offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}::{node.name}")

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            visit(stmt, set(module_marks))
    return offenders


def _carries_live_prod_marker(path: Path) -> bool:
    """True iff `path` applies `pytest.mark.live_prod` to something.

    AST, not a substring search: a file that merely mentions the marker in a
    comment or a docstring (this module does) is not a marked test file.
    """
    src = path.read_text(encoding="utf-8")
    if "live_prod" not in src:
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    if "live_prod" in _module_marker_names(tree):
        return True
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if "live_prod" in _marker_names(node.decorator_list):
                return True
    return False


def _files_marked_live_prod() -> set:
    return {
        p.relative_to(REPO_ROOT).as_posix()
        for p in sorted(TESTS_DIR.rglob("test_*.py"))
        if _carries_live_prod_marker(p)
    }


def test_live_prod_marker_is_registered():
    """An unregistered marker is a typo away from silently selecting nothing,
    and `--strict-markers` would reject it outright."""
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(
        r'"live_prod:', raw
    ), "live_prod is not registered in [tool.pytest.ini_options].markers"


def test_every_production_host_live_test_is_marked_live_prod():
    """The ratchet behind the deselect: a NEW live_unit test pointed at the
    production deployment must carry live_prod, or the weekly run starts writing
    to the production price cache again."""
    offenders = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        offenders.extend(_live_prod_offenders(path))
    assert not offenders, (
        "these live_unit tests call the production deployment without "
        f"@pytest.mark.live_prod: {offenders}. The production server writes the "
        "resolved price to the production cache and L2 DB regardless of "
        "?nocache=true, so a scheduled run of them pollutes production."
    )


def test_live_suite_header_audit_lists_every_live_prod_file():
    """Issue #49 requires a per-file record. Tie the header to reality so the
    audit cannot silently go stale when a file is added or removed."""
    raw = LIVE_YML.read_text(encoding="utf-8")
    documented = set(re.findall(r"tests/[\w/]+\.py", raw))
    marked = _files_marked_live_prod()
    assert marked, "no test file carries live_prod — the deselect selects nothing"
    undocumented = marked - documented
    assert not undocumented, (
        "these files carry live_prod but are missing from the PRODUCTION-CACHE "
        f"AUDIT header of live-suite.yml: {sorted(undocumented)}"
    )

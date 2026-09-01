#!/usr/bin/env python3
"""Phase 7.3 free-unit regression-gate diff (Faithful-Results bundle).

The free-unit suite carries a known baseline of pre-existing failures
(tests/.pre_impl_failures.txt, captured BEFORE any team impl landed — see
tests/PRE_IMPL_FAILURE_BASELINE.md). A "no regressions" claim means no test
that was GREEN at baseline turned RED, i.e. the post-merge failure set
introduces no nodeid absent from the baseline. This module does that set diff so
7.3 is push-button and the gate denominator is the real baseline, not zero.

Pure functions + a thin CLI. No network, no cost (it only diffs failure-id sets;
the operator runs pytest separately and pipes its output in).

Usage (the 7.3 gate):
    python -m pytest tests/ -m "not (live_unit or live_db or integration)" \\
        --ignore=tests/test_integration.py -q 2>&1 | tee /tmp/post.txt
    python -m scripts.regression_gate_diff --current /tmp/post.txt
    # exit 0 = no new failures vs baseline; exit 1 = regression(s) introduced.

Exit codes:
    0 - no regression (current failures subset of baseline)
    1 - regression: at least one NEW failing nodeid not in the baseline
    3 - usage / IO error
"""
from __future__ import annotations

import argparse
import importlib.metadata
import re
import dataclasses
import sys
from pathlib import Path
from typing import Iterable, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent

# The committed, in-repo snapshot is the ONE default baseline (M13-17/M13-74).
# It was RE-CAPTURED from a clean, credential-free free-tier run (no worktree
# .env, conftest strips credentials — the exact state of CI and a fresh clone),
# so `current - baseline` is empty on an untouched tree.
#
# Previously DEFAULT_BASELINE preferred an ABSOLUTE path into a sibling
# checkout's untracked .qa-discovery/ scratch whenever that path existed, so the
# same gate returned two different verdicts: the one machine that had that file
# forgave whatever it contained, while CI and every fresh clone read the
# committed mirror — and the deciding artefact was gitignored, so the
# disagreement left no trace. A NON-default baseline is now opt-in ONLY, via the
# explicit `--baseline` argument.
DEFAULT_BASELINE = REPO_ROOT / "tests" / ".pre_impl_failures.txt"

# Network-dependent tests that are NOT mocked and so flap based on live network
# / Serper / Tier-1.5 reachability — excluded from the gate per CLAUDE.md
# ("network-dependent free test" class) so a live-net flake is never read as a
# code regression. These may be ABSENT from the baseline (they can pass when the
# live path returns) yet fail on another run; either way the gate ignores them.
NETWORK_FLAKY_EXCLUDE: Set[str] = {
    "tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_bust_skips_price_redis_read",
    "tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_specs_reviews_cache_untouched_by_price_bust",
    "tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_prices_endpoint_rate_limited",
    # Mocked-but-pollution-flaky (QA Wave-2): an async/event-loop pollution from a
    # prior test can flip this on some runs; proven pre-existing on main. Shared
    # ONE exclude list with QA's integration gate so neither side reads it as a
    # regression.
    "tests/test_algolia_service.py::test_fetch_price_happy_path_genuine_bhd",
}


def _strip_reason_suffix(line: str) -> str:
    """Drop the pytest -q trailing ' - <reason>' from a FAILED line, but only at
    a ' - ' that is OUTSIDE a '[...]' param bracket. A parametrized nodeid can
    carry a dash inside its params (e.g. 'test_x[a - b]'); the reason separator
    always comes AFTER the closing ']', so a bracket-depth scan keeps the param
    intact. (Backend review nit — inert on today's 48-baseline/smoke20 set, hardened
    for future param-with-dash ids.)"""
    depth = 0
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth = max(0, depth - 1)
        elif depth == 0 and c == " " and line[i:i + 3] == " - ":
            return line[:i].strip()
        i += 1
    return line.strip()


def parse_failure_ids(text: str) -> Set[str]:
    """Extract failing pytest nodeids from pytest output OR a saved id list.

    TWO INPUT MODES (auto-detected):
      - **pytest output** (ANY line starts with 'FAILED ') -> count ONLY the
        'FAILED '-prefixed lines. CRITICAL: pytest -rf/-q ALSO prints BARE
        `tests/...::test` lines in the WARNINGS-summary + traceback sections
        (e.g. a PASSING test's nodeid printed above its DeprecationWarning).
        Counting every '::' line there falsely flags passing tests as failures
        (the Wave-2 false-positive: 8 phantom regressions from the warnings
        section). The 'FAILED ' summary is the authoritative failure list.
      - **bare id-list** (NO 'FAILED ' anywhere -- the baseline mirror) -> count
        every bare-nodeid line, since each line IS a failure id.

    Tolerant of: a trailing ' - <reason>' (stripped at the first ' - ' OUTSIDE
    any '[...]' param bracket, so a parametrized id with a dash survives) and
    blank/whitespace-only lines."""
    lines = text.splitlines()
    pytest_mode = any(ln.lstrip().startswith("FAILED ") for ln in lines)
    ids: Set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if pytest_mode:
            # Authoritative failures = 'FAILED '-prefixed lines ONLY.
            if not line.startswith("FAILED "):
                continue
            line = line[len("FAILED "):].strip()
        line = _strip_reason_suffix(line)
        if "::" in line:
            ids.add(line)
    return ids


def load_baseline(path: Path | str = DEFAULT_BASELINE) -> Set[str]:
    """Load the committed baseline failure-id set (UTF-8). A MISSING file ->
    empty set, which makes the gate treat EVERY current failure as new
    (fail-loud: a vanished baseline must not silently pass the gate)."""
    path = Path(path)
    if not path.exists():
        return set()
    return parse_failure_ids(path.read_text(encoding="utf-8"))


@dataclasses.dataclass
class DiffResult:
    """The three partitions of current-vs-baseline failure sets (after the
    network-flaky exclude set is removed from both)."""
    new_failures: Set[str]     # in current, NOT in baseline -> REGRESSIONS
    fixed: Set[str]            # in baseline, NOT in current -> newly green
    still_failing: Set[str]    # in both -> known/expected failures
    excluded_failing: Set[str] = dataclasses.field(default_factory=set)  # ignored flaky that failed

    @property
    def has_regression(self) -> bool:
        return bool(self.new_failures)


def diff_failures(current: Iterable[str], baseline: Iterable[str],
                  exclude: Optional[Iterable[str]] = None) -> DiffResult:
    """Partition current vs baseline failure-id sets. `new_failures` (current
    minus baseline) is the regression signal.

    `exclude` (defaults to NETWORK_FLAKY_EXCLUDE) is removed from BOTH sets first
    so a network-flaky test never counts as a regression OR a fix — it's reported
    separately as `excluded_failing` for visibility, never gates."""
    excl = set(NETWORK_FLAKY_EXCLUDE if exclude is None else exclude)
    cur = set(current)
    base = set(baseline)
    excluded_failing = cur & excl
    cur -= excl
    base -= excl
    return DiffResult(
        new_failures=cur - base,
        fixed=base - cur,
        still_failing=cur & base,
        excluded_failing=excluded_failing,
    )


def format_report(result: DiffResult) -> str:
    """Human summary. ASCII-only (no em-dash/U+00B7) so captured/redirected
    gate logs don't mojibake under the Windows cp1252 console codec."""
    lines = ["=" * 60]
    if result.has_regression:
        lines.append(
            f"REGRESSION: {len(result.new_failures)} NEW failing test(s) "
            f"not in the baseline:"
        )
        for nodeid in sorted(result.new_failures):
            lines.append(f"  NEW  {nodeid}")
    else:
        lines.append("OK: no new failures vs baseline (no regression).")
    lines.append(
        f"(still-failing known: {len(result.still_failing)}; "
        f"newly-fixed: {len(result.fixed)}; "
        f"network-flaky ignored: {len(result.excluded_failing)})"
    )
    if result.fixed:
        for nodeid in sorted(result.fixed):
            lines.append(f"  FIXED {nodeid}")
    if result.excluded_failing:
        for nodeid in sorted(result.excluded_failing):
            lines.append(f"  IGNORED(net-flaky) {nodeid}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Issue #121 — a baseline captured on an OFF-LOCK environment certifies nothing.
#
# requirements.txt is the lock CI and Railway install. When the local
# interpreter runs different versions, "the suite is green here" is a statement
# about a stack nobody ships. This is not hypothetical: on 2026-09-01 the dev
# machine ran fastapi 0.115.0 against a pinned 0.141.1, whose lazy
# `include_router` returns an `_IncludedRouter` with no `.path`. Three
# route-introspection tests passed locally and failed only in CI for months —
# and one of them was the security pin asserting GET /text/price-kpi still
# carries its admin dependency. The gate therefore REFUSES to certify by
# default and makes the drift visible instead of silently blessing it.
# ---------------------------------------------------------------------------
_PIN_RE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s;#]+)")


def _canon(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def lock_drift(requirements: Path | str = REPO_ROOT / "requirements.txt") -> list:
    """Return [(package, pinned, installed)] for every INSTALLED pin that differs.

    Only installed distributions are compared: a pin absent from this
    environment is a smaller claim (that code path is not exercised here) than
    a pin present at the WRONG version, which silently changes behaviour.
    """
    try:
        text = Path(requirements).read_text(encoding="utf-8")
    except OSError:
        return []
    drift = []
    for line in text.splitlines():
        match = _PIN_RE.match(line.strip())
        if not match:
            continue
        name, pinned = _canon(match.group(1)), match.group(2).strip()
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        except Exception:  # noqa: BLE001 — a broken dist must not break the gate
            continue
        if installed != pinned:
            drift.append((name, pinned, installed))
    return sorted(drift)


def format_drift(drift: list) -> str:
    lines = [
        "REFUSING TO CERTIFY: this environment is OFF-LOCK.",
        "",
        f"{len(drift)} installed package(s) differ from requirements.txt, which is",
        "what CI and Railway install. A pass here does not describe the shipped stack.",
        "",
        f"  {'package':<24} {'lock':<14} installed",
    ]
    for name, pinned, installed in drift:
        lines.append(f"  {name:<24} {pinned:<14} {installed}")
    lines += [
        "",
        "Re-sync, then re-capture:",
        "  pip install -r requirements.txt -r requirements-dev.txt",
        "",
        "Pass --allow-off-lock to override (records the drift in the report and",
        "certifies nothing about CI or production).",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--current", required=True,
                        help="Path to a file with the CURRENT pytest -q output "
                             "(or failure-id list) to diff against the baseline.")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE),
                        help=f"Baseline failure-id file (default {DEFAULT_BASELINE}).")
    parser.add_argument("--allow-off-lock", action="store_true",
                        help="Certify even when installed packages drift from "
                             "requirements.txt (issue #121). The drift is still "
                             "printed; use only when you know the delta is inert.")
    args = parser.parse_args(argv)

    # Issue #121 — refuse before doing any diffing, so an off-lock run cannot
    # produce a green report at all.
    drift = lock_drift()
    if drift:
        print(format_drift(drift), file=sys.stderr)
        if not args.allow_off_lock:
            return 4
        print("--allow-off-lock: continuing despite the drift above.\n", file=sys.stderr)

    try:
        current_text = Path(args.current).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read --current {args.current!r}: {exc}", file=sys.stderr)
        return 3

    current = parse_failure_ids(current_text)
    baseline = load_baseline(args.baseline)
    result = diff_failures(current, baseline)
    print(format_report(result))
    return 1 if result.has_regression else 0


if __name__ == "__main__":
    raise SystemExit(main())

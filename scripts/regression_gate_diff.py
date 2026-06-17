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
import dataclasses
import sys
from pathlib import Path
from typing import Iterable, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical baseline = QA's .qa-discovery/BASELINE_FAILURES.txt (dispatcher
# ruling: ONE source of truth for the gate ignore-set, captured with .env).
# It lives in the MAIN tree's untracked .qa-discovery/ scratch, which worktrees
# do NOT carry, so it's referenced by absolute path. The committed local
# snapshot tests/.pre_impl_failures.txt (verified byte-for-set identical to QA's
# 59) is the fallback when the main tree isn't on disk (e.g. a fresh clone /
# CI). Reconcile with QA, never fork the set.
_QA_CANONICAL_BASELINE = Path(
    r"C:\Users\SynAckITPC\Documents\AI\smartcompare\.qa-discovery\BASELINE_FAILURES.txt"
)
_LOCAL_BASELINE_SNAPSHOT = REPO_ROOT / "tests" / ".pre_impl_failures.txt"
DEFAULT_BASELINE = (
    _QA_CANONICAL_BASELINE if _QA_CANONICAL_BASELINE.exists() else _LOCAL_BASELINE_SNAPSHOT
)

# Network-dependent tests that are NOT mocked and so flap based on live network
# / Serper / Tier-1.5 reachability — excluded from the gate per CLAUDE.md
# ("network-dependent free test" class) so a live-net flake is never read as a
# code regression. These may be ABSENT from the baseline (they can pass when the
# live path returns) yet fail on another run; either way the gate ignores them.
NETWORK_FLAKY_EXCLUDE: Set[str] = {
    "tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_bust_skips_price_redis_read",
    "tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_specs_reviews_cache_untouched_by_price_bust",
    "tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_prices_endpoint_rate_limited",
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
    """Extract pytest nodeids from pytest -q output (or a saved id list).

    Tolerant of:
      - a leading 'FAILED ' prefix (pytest -q summary lines),
      - a trailing ' - <reason>' the -q summary appends, stripped at the first
        ' - ' OUTSIDE any '[...]' param bracket (so a parametrized id with a dash
        in its params survives),
      - blank / whitespace-only lines.
    A nodeid is recognized by containing '::'."""
    ids: Set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("FAILED "):
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--current", required=True,
                        help="Path to a file with the CURRENT pytest -q output "
                             "(or failure-id list) to diff against the baseline.")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE),
                        help=f"Baseline failure-id file (default {DEFAULT_BASELINE}).")
    args = parser.parse_args(argv)

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

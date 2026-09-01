#!/usr/bin/env python3
"""Generate tests/PRE_IMPL_FAILURE_BASELINE.md FROM tests/.pre_impl_failures.txt.

The markdown mirror USED to be hand-maintained and drifted (M13-17: it claimed
49 nodes against the file's 48). It is now a pure render of the committed
baseline file: run this after re-capturing the baseline, and never edit the .md
by hand. `tests/test_ci_gates.py::test_baseline_count_is_rederivable_from_the_
committed_file` re-derives the count + id set from the .txt and asserts the .md
matches, so a stale mirror fails CI.

    python -m scripts.gen_baseline_mirror        # writes the .md
    python -m scripts.gen_baseline_mirror --check # exit 1 if the .md is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "tests" / ".pre_impl_failures.txt"
MIRROR = REPO_ROOT / "tests" / "PRE_IMPL_FAILURE_BASELINE.md"


def baseline_ids(text: str) -> list[str]:
    """Every line carrying a pytest node id (has '::' and is not a '#' comment),
    in file order. Matches scripts.regression_gate_diff.parse_failure_ids'
    id-list mode."""
    ids: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "::" in line:
            ids.append(line)
    return ids


def render(ids: list[str]) -> str:
    n = len(ids)
    lines = [
        "# Pre-impl free-unit failure baseline (GENERATED — do not hand-edit)",
        "",
        "<!-- BASELINE_COUNT: {} -->".format(n),
        "",
        "> **GENERATED FILE.** This mirror is rendered from "
        "`tests/.pre_impl_failures.txt` by `scripts/gen_baseline_mirror.py`. Do "
        "not edit it by hand — re-capture the baseline, then regenerate. "
        "`tests/test_ci_gates.py` re-derives the count and id set from the .txt "
        "and fails if this file drifts (the M13-17 regression: the mirror once "
        "claimed 49 against the file's 48).",
        "",
        "The free-unit regression gate (`scripts/regression_gate_diff.py`) is a "
        "SUBSET check: a branch is GREEN iff its FAILED set (minus "
        "`NETWORK_FLAKY_EXCLUDE`) is a subset of the {} node ids below. The "
        "baseline was RE-CAPTURED 2026-09-01 (M13-17) from a clean, "
        "credential-free free-tier run — the exact state of CI and a fresh "
        "clone — so `current - baseline` is empty on an untouched tree.".format(n),
        "",
        "| # | Failing node id |",
        "|---|-----------------|",
    ]
    for i, nid in enumerate(ids, 1):
        lines.append("| {} | `{}` |".format(i, nid))
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="Exit 1 if the mirror is stale instead of writing it.")
    args = ap.parse_args(argv)

    ids = baseline_ids(BASELINE.read_text(encoding="utf-8"))
    content = render(ids)

    if args.check:
        current = MIRROR.read_text(encoding="utf-8") if MIRROR.exists() else ""
        if current != content:
            print("STALE: tests/PRE_IMPL_FAILURE_BASELINE.md differs from a fresh "
                  "render — run: python -m scripts.gen_baseline_mirror", file=sys.stderr)
            return 1
        print("OK: mirror is current ({} nodes).".format(len(ids)))
        return 0

    MIRROR.write_text(content, encoding="utf-8")
    print("wrote {} ({} nodes).".format(MIRROR.relative_to(REPO_ROOT).as_posix(), len(ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

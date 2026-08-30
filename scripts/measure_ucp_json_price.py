"""M10 TRACK A / UNIT A4 — what the UCP ``/products/{handle}.json`` channel buys.

OFFLINE AND ZERO-NETWORK BY CONSTRUCTION. This script re-derives the unit's
claims from the M9 `measure-ucp-free` artifacts and the committed fixtures. It
never opens a socket, never touches Serper or OpenAI, and never fetches
fragrantica or parfumo. Run it to re-check the numbers in the adapter's module
docstring after any change to the money parser or the currency resolver::

    python -m scripts.measure_ucp_json_price
    python -m scripts.measure_ucp_json_price --m9-dir <path to measure-ucp-free>

Output is written as UTF-8 to a file (``--out``) and only ASCII is printed to
the console — the Windows console is cp1252 and mangles anything else.

WHAT IT MEASURES, and why each number is the one that matters:

  1. THE MINOR-UNIT TRAP. For every measured handle, the adapter's reading of
     the ``.json`` decimal string is compared against what the ``.js`` adapter's
     minor-unit helpers would have produced from the SAME string. The ratio is
     the size of the bug that routing this channel through the wrong parser
     would ship. It is a 100x under-price, not a rounding difference.
  2. CURRENCY PROVENANCE. How many handles carry a resolvable self-declared
     ``price_currency``, how many would fall back to the registry, and on how
     many the two DISAGREE. The disagreement count is the honest measure of how
     much the precedence rule is doing today: on the measured corpus it is
     zero, which is exactly why the rule has to be pinned by a synthetic
     fixture rather than by the corpus.
  3. WHAT THE REGISTRY WOULD HAVE STAMPED. The registry's ``currency`` for each
     host, next to what the merchant actually declared.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_M9_DIR = Path(
    os.environ.get("M9_UCP_DIR", "")
) if os.environ.get("M9_UCP_DIR") else None

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ucp_json"


def _load_m9_records(m9_dir: Optional[Path]) -> List[Dict[str, Any]]:
    """Flatten the M9 probe's per-handle records, or return [] when the probe
    directory is not on this machine. The probe artifacts live in a session
    scratchpad, NOT in the repo, so absence is normal and is reported rather
    than treated as a failure."""
    if not m9_dir:
        return []
    measured = m9_dir / "measured.json"
    if not measured.is_file():
        return []
    data = json.loads(measured.read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for host, block in (data.get("hosts") or {}).items():
        for row in block.get("products") or []:
            if row.get("status") != 200:
                continue
            out.append({
                "host": host,
                "handle": row.get("handle"),
                "registry_currency": row.get("registry_currency"),
                "declared": (row.get("currency_code_in_envelope") or [None])[0],
                "price_first": row.get("price_first"),
                "availability_present": row.get("availability_present"),
                "variant_sizes_present": row.get("variant_sizes_present"),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--m9-dir", type=Path, default=DEFAULT_M9_DIR,
        help="the M9 measure-ucp-free directory (optional; the fixture checks "
             "run without it)",
    )
    ap.add_argument(
        "--out", type=Path, default=None,
        help="write the UTF-8 report here (default: stdout). The report is pure "
             "ASCII by construction, so stdout is safe on the cp1252 Windows "
             "console; --out exists for the cases where a file is wanted.",
    )
    args = ap.parse_args()

    from app.services.price_service import parse_money
    from app.services import shopify_pdp_service as svc

    lines: List[str] = []

    def w(text: str = "") -> None:
        lines.append(text)

    w("M10 UNIT A4 - the UCP /products/{handle}.json channel, re-measured offline")
    w("=" * 78)
    w("")

    # ---------------------------------------------------------------- 1. the trap
    w("1. THE MINOR-UNIT TRAP - the .json decimal string vs the .js divisor chain")
    w("-" * 78)
    w("The .js feed ships integer minor units and ALWAYS divides by 100. The .json")
    w("feed ships a major-unit decimal string. Feeding one to the other's parser:")
    w("")
    w("  %-14s %-6s %10s %10s %10s" % ("string", "cur", "correct", "via .js", "ratio"))
    trap_rows = [("17.200", "OMR"), ("20.000", "BHD"), ("5.500", "OMR"),
                 ("30.000", "OMR"), ("31.200", "OMR")]
    for raw, cur in trap_rows:
        correct = parse_money(raw, cur)
        wrong = svc._to_major(svc._to_minor(raw))
        ratio = (correct / wrong) if wrong else float("inf")
        w("  %-14s %-6s %10s %10s %9.0fx" % (raw, cur, correct, wrong, ratio))
    w("")
    w("  om.swissarabian oud-malaki is the pin: .js says 1720, .json says '17.200'.")
    w("  1720/100 = 17.20 - NOT /1000. The .json string needs no divisor at all.")
    w("")

    # ------------------------------------------------------- 2. the fixture checks
    w("2. THE COMMITTED FIXTURES - what the adapter reads from each")
    w("-" * 78)
    sources = json.loads((FIXTURES / "SOURCES.json").read_text(encoding="utf-8"))
    for name in sorted(p.name for p in FIXTURES.glob("*.json")):
        if name == "SOURCES.json":
            continue
        meta = sources.get(name) or {}
        registry = meta.get("registry_currency")
        parsed = svc.parse_ucp_products_json(
            (FIXTURES / name).read_text(encoding="utf-8"),
            registry_currency=registry,
        )
        if parsed is None:
            w("  %-52s -> ABSTAIN (registry=%s)" % (name, registry))
            continue
        w("  %-52s -> %s %s  via %s  (registry=%s)" % (
            name, parsed["price"], parsed["currency"],
            parsed["currency_source"], registry,
        ))
    w("")
    w("  ABSTAIN is a RESULT, not a failure: with neither a self-declared code nor")
    w("  a registry row there is no currency to stamp, and an unlabelled amount is")
    w("  a wrong-price stamp waiting for a downstream default.")
    w("")

    # ------------------------------------------------------- 3. the M9 corpus
    w("3. THE M9 CORPUS - currency provenance across the 6 UCP hosts")
    w("-" * 78)
    records = _load_m9_records(args.m9_dir)
    if not records:
        w("  M9 probe directory not available on this machine - skipped.")
        w("  Pass --m9-dir (or set M9_UCP_DIR) to re-derive from measured.json.")
        w("  Recorded verdict: 34 handles tried, 32 x HTTP 200, 32/32 price present,")
        w("  32/32 self-declared currency == registry currency, 0/32 availability,")
        w("  17/32 variant sizes.")
    else:
        declared = sum(1 for r in records if r["declared"])
        agree = sum(
            1 for r in records
            if r["declared"] and r["declared"] == r["registry_currency"]
        )
        disagree = sum(
            1 for r in records
            if r["declared"] and r["declared"] != r["registry_currency"]
        )
        avail = sum(1 for r in records if r["availability_present"])
        sizes = sum(1 for r in records if r["variant_sizes_present"])
        w("  handles at HTTP 200 .................. %d" % len(records))
        w("  self-declared price_currency present . %d" % declared)
        w("    of which AGREE with the registry ... %d" % agree)
        w("    of which DISAGREE ................. %d" % disagree)
        w("  availability present ................. %d" % avail)
        w("  variant sizes present ................ %d" % sizes)
        w("")
        w("  %d disagreements means the precedence rule changes NO outcome on this" % disagree)
        w("  corpus. That is not a reason to drop it - it is the reason the rule is")
        w("  pinned by a derived fixture instead: agreement cannot tell you which")
        w("  source was read, so without the pin a coincidence reads as evidence.")
        w("")
        w("  per host:")
        seen = set()
        for r in records:
            if r["host"] in seen:
                continue
            seen.add(r["host"])
            same = [x for x in records if x["host"] == r["host"]]
            w("    %-26s registry=%-4s declared=%-4s n=%d" % (
                r["host"], r["registry_currency"] or "-",
                (same[0]["declared"] or "-"), len(same),
            ))
    w("")

    # -------------------------------------------------------------- 4. the flag
    w("4. THE FLAG")
    w("-" * 78)
    w("  ENABLE_UCP_JSON_PRICE default -> %s" % svc.ucp_json_price_enabled())
    w("  (this process's environment; the shipped default is OFF)")

    report = "\n".join(lines) + "\n"
    if args.out is None:
        sys.stdout.write(report)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print("wrote %s (%d lines)" % (args.out, len(lines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

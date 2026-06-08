#!/usr/bin/env python3
"""Gold-truth seed researcher — pre-populate expected_prices via Serper.

Pre-research Bahrain retail prices for the 50-query validation matrix so
team-lead's manual ratification step is quick edit-and-confirm rather
than full research. Output replaces data/validation_gold_truth.json
`expected_prices` with researched values + adds a sibling
`expected_prices_sources` array with retailer + url + value + timestamp.

Run:
    python scripts/research_goldtruth_seed.py
        [--limit N] [--category cat] [--dry-run] [--out PATH]

Default: read data/validation_gold_truth.json, hit search_web 3x per
product (lulu.com.bh, sharafdg, carrefourbh/geant), extract any visible
BHD/USD values from snippets, write back to the same file in place
(unless --dry-run).

Budget: 50 queries x 2 products x 3 retailers = 300 Serper calls in the
worst case. With cached returns the actual budget drops sharply.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.3
Doc:  docs/plans/2026-06-08-A-validation-matrix-50q.md § 6
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import os

from app.services.serper_service import search_web  # noqa: E402

logger = logging.getLogger(__name__)


def _require_serper_key() -> None:
    """Abort the script if SERPER_API_KEY is missing. Without a key the
    serper helper returns empty organic[] for every request, which would
    cause this script to silently mark every query as `not_in_bahrain`
    — a destructive write to the gold-truth file."""
    if not os.getenv("SERPER_API_KEY"):
        sys.stderr.write(
            "ERROR: SERPER_API_KEY env var is not set. The seed researcher needs Serper.\n"
            "  Set it via the same export the production backend uses, e.g.\n"
            "    export SERPER_API_KEY=<key>\n"
            "  Or run with --dry-run to inspect the workflow without writing.\n"
        )
        sys.exit(3)

DEFAULT_GOLD = REPO_ROOT / "data" / "validation_gold_truth.json"

# Retailer search templates — first three Bahrain visible domains. The
# fourth (boots) only fires for supplements/skincare/makeup/haircare —
# we narrow by category to keep the Serper budget tight.
RETAILER_QUERIES: List[Tuple[str, str]] = [
    ("lulu.com.bh", "site:lulu.com.bh {product}"),
    ("sharafdg.com", "site:sharafdg.com {product}"),
    ("carrefourbh", "site:carrefourbh.com OR site:geant.com.bh {product}"),
]

# Category → optional extra retailer searches.
EXTRA_RETAILERS_BY_CAT: Dict[str, List[Tuple[str, str]]] = {
    "supplements": [
        ("bn.boots.com", "site:bn.boots.com {product}"),
        ("iherb.com", "site:iherb.com {product}"),
    ],
    "skincare": [
        ("bn.boots.com", "site:bn.boots.com {product}"),
    ],
    "makeup": [
        ("bn.boots.com", "site:bn.boots.com {product}"),
    ],
    "haircare": [
        ("bn.boots.com", "site:bn.boots.com {product}"),
    ],
    "fragrances": [
        ("brandsforless", "site:brandsforless.com {product}"),
    ],
}

# Currency extraction patterns. Bahrain dinars (BHD) are most common in
# Bahrain retail snippets; iHerb shows USD only.
_BHD_RE = re.compile(r"(?:BHD|BD|\.د\.ب|د\.ب)\s*([0-9]+(?:[\.,][0-9]+)?)|([0-9]+(?:[\.,][0-9]+)?)\s*(?:BHD|BD)", re.IGNORECASE)
_USD_RE = re.compile(r"(?:USD|\$)\s*([0-9]+(?:[\.,][0-9]+)?)|([0-9]+(?:[\.,][0-9]+)?)\s*(?:USD)", re.IGNORECASE)
_AED_RE = re.compile(r"(?:AED|Dhs?)\s*([0-9]+(?:[\.,][0-9]+)?)", re.IGNORECASE)
_SAR_RE = re.compile(r"(?:SAR|SR)\s*([0-9]+(?:[\.,][0-9]+)?)", re.IGNORECASE)

# Conversion to BHD (rough static — actual conversion in production uses
# exchange_rate_service). These are conservative for seed work.
_USD_TO_BHD = 0.377
_AED_TO_BHD = 0.103
_SAR_TO_BHD = 0.100


def _to_bhd(value: float, currency: str) -> float:
    if currency == "BHD":
        return value
    if currency == "USD":
        return round(value * _USD_TO_BHD, 2)
    if currency == "AED":
        return round(value * _AED_TO_BHD, 2)
    if currency == "SAR":
        return round(value * _SAR_TO_BHD, 2)
    return value


def _extract_prices_from_text(text: str) -> List[Tuple[float, str]]:
    """Return list of (value_in_BHD, source_currency) tuples for any
    prices found in `text`. Filters out implausibly large values
    (>10000) and trivial values (<0.05)."""
    out: List[Tuple[float, str]] = []
    for pattern, cur in ((_BHD_RE, "BHD"), (_USD_RE, "USD"), (_AED_RE, "AED"), (_SAR_RE, "SAR")):
        for m in pattern.finditer(text):
            for group in m.groups():
                if group is None:
                    continue
                try:
                    val = float(group.replace(",", "."))
                except ValueError:
                    continue
                if 0.05 < val < 10000:
                    bhd = _to_bhd(val, cur)
                    if 0.05 < bhd < 10000:
                        out.append((bhd, cur))
    return out


async def _research_one_product(product_name: str, category: str, max_retailers: Optional[int] = None) -> Tuple[List[Dict[str, Any]], List[float]]:
    """Hit Serper for each retailer query, collect (sources, raw_BHD_values).

    Returns (sources_list, prices_list). sources_list has retailer + url +
    raw matched text snippet so team-lead can spot-check during
    ratification. prices_list has converted-to-BHD values for range
    inference.
    """
    queries = list(RETAILER_QUERIES) + EXTRA_RETAILERS_BY_CAT.get(category, [])
    if max_retailers is not None:
        queries = queries[:max_retailers]

    sources: List[Dict[str, Any]] = []
    prices: List[float] = []
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for retailer, qtmpl in queries:
        q = qtmpl.format(product=product_name)
        try:
            result = await search_web(q, num_results=5, country="bh")
        except Exception as exc:  # noqa: BLE001
            sources.append({"retailer": retailer, "query": q, "error": str(exc), "researched_at": timestamp})
            continue

        organic = result.get("organic") or []
        if not organic:
            sources.append({"retailer": retailer, "query": q, "results": 0, "researched_at": timestamp})
            continue

        for hit in organic[:3]:
            snippet = (hit.get("snippet") or "") + " " + (hit.get("title") or "")
            url = hit.get("link") or ""
            extracted = _extract_prices_from_text(snippet)
            if extracted:
                first_value, first_currency = extracted[0]
                sources.append({
                    "retailer": retailer,
                    "url": url,
                    "value_bhd": first_value,
                    "source_currency": first_currency,
                    "snippet": snippet[:200],
                    "researched_at": timestamp,
                })
                prices.extend(v for v, _ in extracted[:2])  # cap per hit to avoid noise
            else:
                # Track the URL even if no price extracted — useful for ratification
                sources.append({
                    "retailer": retailer,
                    "url": url,
                    "value_bhd": None,
                    "snippet": snippet[:200],
                    "researched_at": timestamp,
                })

    return sources, prices


def _infer_range_from_prices(prices: List[float]) -> Optional[Dict[str, Any]]:
    """Given a list of BHD prices observed across retailers, infer a
    sensible {min, max} range. Drop top + bottom 10% outliers when n>=5,
    else use full range. Pad by 10% on each side to stay forgiving."""
    if not prices:
        return None
    sorted_p = sorted(prices)
    n = len(sorted_p)
    if n >= 5:
        trim = max(1, n // 10)
        sorted_p = sorted_p[trim:-trim] or sorted_p
    lo = round(min(sorted_p) * 0.90, 2)
    hi = round(max(sorted_p) * 1.10, 2)
    # Guard against degenerate zero-range
    if hi - lo < 0.5:
        mid = (lo + hi) / 2.0
        lo = round(mid * 0.85, 2)
        hi = round(mid * 1.15, 2)
    return {"min": lo, "max": hi, "currency": "BHD"}


def _extract_two_products(query: str) -> Tuple[str, str]:
    """Split 'X vs Y' (case-insensitive) into (X, Y)."""
    parts = re.split(r"\s+vs\s+", query, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return query, query  # degenerate fallback


async def research_query(q: Dict[str, Any], max_retailers: Optional[int] = None) -> Dict[str, Any]:
    """Research a single gold-truth query, return updated entry."""
    p0_name, p1_name = _extract_two_products(q["query"])
    cat = q.get("category", "other")
    p0_sources, p0_prices = await _research_one_product(p0_name, cat, max_retailers=max_retailers)
    p1_sources, p1_prices = await _research_one_product(p1_name, cat, max_retailers=max_retailers)

    p0_range = _infer_range_from_prices(p0_prices)
    p1_range = _infer_range_from_prices(p1_prices)

    enriched = dict(q)
    # Only overwrite expected_prices when we have at least one usable
    # signal — preserves the hand-authored seed if Serper returned nothing.
    if p0_range or p1_range:
        enriched["expected_prices"] = {
            "product_0": p0_range if p0_range else q["expected_prices"]["product_0"],
            "product_1": p1_range if p1_range else q["expected_prices"]["product_1"],
        }
        enriched["confidence"] = "researched_seed"
    else:
        enriched["confidence"] = "hand_authored"

    # Availability check — when ZERO retailers in Bahrain returned a price
    # AND zero retailer URLs surfaced (even without prices) for BOTH
    # products, FLAG the query for ratification review. We do NOT
    # auto-set expected_prices=None here — that would risk destroying
    # the hand-authored seed when Serper happens to miss snippets.
    # Team-lead ratification confirms or overrides.
    p0_has_signal = bool(p0_prices)
    p1_has_signal = bool(p1_prices)
    p0_has_any_url = any(s.get("url") for s in p0_sources)
    p1_has_any_url = any(s.get("url") for s in p1_sources)
    if not p0_has_signal and not p1_has_signal and not p0_has_any_url and not p1_has_any_url:
        enriched["availability"] = "no_retailer_signal_review_required"
        enriched["availability_note"] = (
            f"No Bahrain retailer returned a price OR URL across {len(p0_sources) + len(p1_sources)} "
            "Serper queries. Team-lead: ratify whether products lack Bahrain retail presence "
            "OR retailers don't index searchable snippets. If genuinely absent, set "
            "expected_prices=null + availability='not_in_bahrain' to exclude from gate."
        )

    enriched["expected_prices_sources"] = {
        "product_0": p0_sources,
        "product_1": p1_sources,
    }
    enriched["expected_prices_researched_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return enriched


async def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", default=str(DEFAULT_GOLD))
    parser.add_argument("--out", default=None, help="Output JSON path (default: overwrite --gold)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--max-retailers", type=int, default=None, help="Cap retailer queries per product (budget control)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write — print summary only")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    # Hard-fail when key missing — otherwise destructive write would fire.
    if not args.dry_run:
        _require_serper_key()

    gold_path = Path(args.gold)
    out_path = Path(args.out) if args.out else gold_path

    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    queries = gold["queries"]
    if args.category:
        queries = [q for q in queries if q["category"] == args.category]
    if args.limit:
        queries = queries[: args.limit]

    if not args.quiet:
        print(f"# Researching {len(queries)} queries (gold={gold_path.name}, out={out_path.name}, dry_run={args.dry_run})")

    researched: List[Dict[str, Any]] = []
    for i, q in enumerate(queries, start=1):
        result = await research_query(q, max_retailers=args.max_retailers)
        researched.append(result)
        if not args.quiet:
            n_p0 = sum(1 for s in result["expected_prices_sources"]["product_0"] if s.get("value_bhd"))
            n_p1 = sum(1 for s in result["expected_prices_sources"]["product_1"] if s.get("value_bhd"))
            avail = result.get("availability", "ok")
            print(f"  [{i:>2}/{len(queries)}] {result['id']:<14} {result['query'][:40]:42} p0_hits={n_p0:>2} p1_hits={n_p1:>2} avail={avail}")

    # Merge researched back into full payload (preserving un-targeted queries).
    if args.category or args.limit:
        researched_ids = {r["id"] for r in researched}
        merged = []
        for q in gold["queries"]:
            if q["id"] in researched_ids:
                merged.append(next(r for r in researched if r["id"] == q["id"]))
            else:
                merged.append(q)
        gold["queries"] = merged
    else:
        gold["queries"] = researched

    # Stamp aggregate meta
    gold.setdefault("_metadata", {})["last_seed_researched_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gold["_metadata"]["seed_researcher"] = "scripts/research_goldtruth_seed.py"

    aggregate = {
        "researched_count": len(researched),
        "with_signal": sum(1 for r in researched if r.get("availability") != "not_in_bahrain"),
        "not_in_bahrain": sum(1 for r in researched if r.get("availability") == "not_in_bahrain"),
    }
    if not args.quiet:
        print()
        print(f"Aggregate: {aggregate}")

    if args.dry_run:
        if not args.quiet:
            print("(dry-run — no write)")
        return 0

    out_path.write_text(json.dumps(gold, indent=2, ensure_ascii=False), encoding="utf-8")
    if not args.quiet:
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

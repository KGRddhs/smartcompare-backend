#!/usr/bin/env python3
"""Warm the KPI truth set OFF-CLOCK, then measure the WARMED usable_exact_genuine
KPI from the cache (Redis L1) — one pass, no prod HTTP. Reports per-category.

Usage: python -m scripts.measure_warmed_kpi <out.json>
"""
from __future__ import annotations

import os

os.environ["PRICE_RACE_TIMEOUT"] = os.getenv("WARMER_PRICE_RACE_TIMEOUT", "60")
os.environ["STREAM_HARD_CAP_SECONDS"] = os.getenv("WARMER_STREAM_HARD_CAP", "150")
os.environ["FAN_OUT_BUDGET_SECONDS"] = os.getenv("WARMER_FAN_OUT_BUDGET", "35")
os.environ.setdefault("FIRECRAWL_TIMEOUT", "45")
os.environ.setdefault("SCRAPEDO_TIMEOUT", "35")

from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent / ".env"), override=False)
except Exception:
    pass

import asyncio
import io
import json
import sys


async def _resolve(svc, q, region):
    from app.services.extraction_service import parse_product_query
    from app.services.price_service import _infer_category_from_query, build_size_aware_price_cache_key
    try:
        parsed, _ = await parse_product_query(q)
    except Exception:
        parsed = {}
    p0 = ((parsed or {}).get("products") or [{}])[0]
    brand = (p0.get("brand") or "").strip()
    name = (p0.get("name") or q).strip()
    variant = p0.get("variant")
    category = (p0.get("category") or _infer_category_from_query(q) or "other")
    sq = (f"{brand} {name} {variant or ''}".strip()) or q
    key = build_size_aware_price_cache_key(brand, name, variant, region, sq)
    # WARM: nocache=True forces an off-clock resolution + the should_cache write.
    await svc._get_price(brand, name, variant, region, sq, True, category)
    return key


def _usable(cached, truth_entry=None):
    """Authoritative contract — reuse eval_runner.usable_exact_genuine_for_product
    (in_stock is-not-False + independent truth-axis identity validation) instead of
    the drifted inline check (which required in_stock is True + skipped identity).
    Construct the single-product body shape the function expects from the cached
    price dict."""
    from scripts.eval_runner import usable_exact_genuine_for_product
    if not isinstance(cached, dict):
        return False
    body = {"products": [{"price": cached}]}
    return bool(usable_exact_genuine_for_product(body, 0, truth_entry))


def _reason(cached, truth_entry=None):
    """Human-readable reason a cached price is NOT usable (diagnosis)."""
    from scripts.eval_runner import GENUINE_BH_SOURCE_METHODS as GEN
    from app.services.price_service import _is_listing_url
    if not isinstance(cached, dict):
        return "not-cached"
    if cached.get("unavailable") is True or cached.get("amount") in (None, 0):
        return "pending/no-amount"
    m = cached.get("source_method")
    if not isinstance(m, str) or m not in GEN:
        return f"non-genuine-method:{m}"
    if cached.get("in_stock") is False:
        return "out-of-stock"
    url = cached.get("url")
    if not isinstance(url, str) or not url.strip():
        return "no-url"
    if _is_listing_url(url):
        return "listing-url"
    if not (cached.get("title") or cached.get("name")):
        return "no-identity"
    if truth_entry is not None and not _usable(cached, truth_entry):
        return "identity-mismatch-vs-truth"
    return "usable"


async def main():
    from scripts.eval_runner import load_usable_exact_genuine_truth
    from app.services.structured_comparison_service import get_comparison_service
    from app.services.cache_service import get_cached
    out_path = sys.argv[1] if len(sys.argv) > 1 else ".warmed_kpi.json"
    truth = load_usable_exact_genuine_truth()
    rows = []
    for t in truth:
        svc = get_comparison_service()
        key = await _resolve(svc, t["query"], t.get("region", "bahrain"))
        cached = get_cached(key)
        c = cached if isinstance(cached, dict) else {}
        rows.append({
            "query": t["query"], "category": t.get("category"),
            "cached": isinstance(cached, dict),
            "usable": _usable(cached, t),
            "reason": _reason(cached, t),
            "source_method": c.get("source_method"),
            "amount": c.get("amount"),
            "in_stock": c.get("in_stock"),
            "url": c.get("url"),
            "title": c.get("title") or c.get("name"),
        })
    per_cat = {}
    for r in rows:
        agg = per_cat.setdefault(r["category"], [0, 0])
        agg[0] += 1 if r["usable"] else 0
        agg[1] += 1
    result = {
        "per_category": {c: {"usable": u, "requested": n, "share": round(u / n, 3) if n else 0.0}
                         for c, (u, n) in per_cat.items()},
        "overall": {"usable": sum(r["usable"] for r in rows), "requested": len(rows)},
        "rows": rows,
    }
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False, indent=2))
    print("done ->", out_path, "overall usable", result["overall"])


if __name__ == "__main__":
    asyncio.run(main())

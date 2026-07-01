#!/usr/bin/env python3
"""Warm the usable_exact_genuine KPI truth set OFF-CLOCK into the shared cache.

The KPI truth set is deliberately DISJOINT from the warmer's gold/catalog queries,
so the production warmer cron never warms it. This one-off resolves each truth
query off-clock (60s PRICE_RACE_TIMEOUT so the slow genuine curl/scrape finishes)
via the SAME path /price-kpi reads — parse_product_query -> _get_price(nocache=True)
-> the write fires inside via should_cache_price — so a subsequent warmed KPI
(`eval_runner --kpi usable_exact_genuine --read-cache`) serves genuine from cache.

Usage: python -m scripts.warm_kpi_truth <out.jsonl> [limit]

GOTCHA: nocache=True bypasses the cache READ, not the WRITE -> this WRITES to the
shared prod Upstash + product_prices. Only run with intent (the exact-SKU gate
ensures only correct SKUs cache).
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


async def _warm_one(svc, t):
    from app.services.extraction_service import parse_product_query
    from app.services.price_service import _infer_category_from_query
    q = t["query"]
    region = t.get("region", "bahrain")
    try:
        parsed, _ = await parse_product_query(q)
    except Exception as exc:  # noqa: BLE001
        parsed = {}
    p0 = ((parsed or {}).get("products") or [{}])[0]
    brand = (p0.get("brand") or "").strip()
    name = (p0.get("name") or q).strip()
    variant = p0.get("variant")
    category = (p0.get("category") or _infer_category_from_query(q) or "other")
    sq = (f"{brand} {name} {variant or ''}".strip()) or q
    try:
        price = await svc._get_price(brand, name, variant, region, sq, True, category)
    except Exception as exc:  # noqa: BLE001
        return {"query": q, "category": t.get("category"), "error": str(exc)[:120]}
    p = price if isinstance(price, dict) else {}
    return {
        "query": q, "category": t.get("category"),
        "source_method": p.get("source_method"), "amount": p.get("amount"),
        "in_stock": p.get("in_stock"), "url": p.get("url"),
        "title": p.get("title"),
    }


async def main():
    from scripts.eval_runner import load_usable_exact_genuine_truth
    from app.services.structured_comparison_service import get_comparison_service
    out_path = sys.argv[1] if len(sys.argv) > 1 else ".warm_kpi_out.jsonl"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    truth = load_usable_exact_genuine_truth()
    if limit:
        truth = truth[:limit]
    rows = []
    for t in truth:
        svc = get_comparison_service()  # per-request instance (concurrency contract)
        rows.append(await _warm_one(svc, t))
    with io.open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    genuine = sum(1 for r in rows if r.get("source_method") and "convert" not in (r.get("source_method") or "")
                  and "estimat" not in (r.get("source_method") or "") and r.get("amount"))
    print(f"warmed {len(rows)} rows -> {out_path}; genuine-ish={genuine}")


if __name__ == "__main__":
    asyncio.run(main())

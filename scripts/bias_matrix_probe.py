#!/usr/bin/env python3
"""F1.7 — Bahrain-consultation bias-matrix probe (turnkey runner).

Runs the 24-query non-luxury matrix (`.qa-bias-rerun/bias_matrix_24.json`)
against a compare backend and verifies the B.0 Bahrain-first source registry
is consulted on escalating queries.

For each query it GETs `/api/v1/text/compare?q=...&nocache=true` and inspects
`metadata.source_trace.products[*].races.price`:
  - `route` in {registry, legacy_fallback, official, tier1_5} → Tier 1.5 fired
  - `route == "registry"` → a Bahrain/registry source won the price
It also reads `products[*].price.source_method` to count how many product
prices are still `*_estimate` (the gpt_training-priced count the bundle wants
to drive down).

Cost: one compare per query (~$0.01 each, 24 ≈ $0.24) when run with
--nocache against a live backend. Run ONCE; the report is the evidence
artifact (NOT committed).

*** LOCAL-LEG CAP OVERRIDE — REQUIRED (S1-close runbook) ***
A local uvicorn pays the developer machine's RTT to OpenAI/Serper (e.g.
Bahrain→US) on EVERY call, which Railway does not. That inflates per-query
walls 5-10s past the prod-tuned STREAM_HARD_CAP_SECONDS=30, so EVERY query
trips the cap upstream of the escalation block and the probe reports 0/24
with `no-escalation` everywhere — an ENVIRONMENTAL timeout, NOT a wiring
verdict (observed run 1, 2026-06-10: all 24 died at 25-27s walls). To
isolate wiring behavior from local latency, the LOCAL leg MUST export a
relaxed cap for the uvicorn process only:
  # local leg:
  STREAM_HARD_CAP_SECONDS=60 uvicorn app.main:app --port 8000   # cap override
  python scripts/bias_matrix_probe.py --base-url http://localhost:8000 --concurrency 2
The PROD leg runs with the prod cap UNTOUCHED (the cap is a prod SLO; do
NOT raise it on Railway just to pass the probe — F4's p95-vs-cap watch is
the standing guard there).

Usage:
  # Local uvicorn leg (your worktree code) — note the cap override above:
  STREAM_HARD_CAP_SECONDS=60 uvicorn app.main:app --port 8000   # in another shell
  python scripts/bias_matrix_probe.py --base-url http://localhost:8000 --concurrency 2

  # Prod / post-merge leg (prod cap untouched):
  python scripts/bias_matrix_probe.py \
      --base-url https://web-production-58776.up.railway.app

Options:
  --base-url URL     backend root (no trailing /api). REQUIRED.
  --matrix PATH      matrix fixture (default .qa-bias-rerun/bias_matrix_24.json)
  --concurrency N    parallel requests (default 3)
  --timeout S        per-request timeout seconds (default 60)
  --no-nocache       hit caches (cheaper, but won't exercise the live cascade)
  --json-out PATH    also write the structured result JSON here
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    sys.exit("httpx is required: pip install httpx")


DEFAULT_MATRIX = Path(__file__).resolve().parent.parent / ".qa-bias-rerun" / "bias_matrix_24.json"
# A price is "gpt_training-priced" (the metric the bundle drives down) when it
# fell through to a GPT estimate rather than a scraped/structured source. The
# codebase stamps either the literal "estimated" or a specific gpt_* method
# (gpt_training_estimate / gpt_organic_extract / ...). Scraped methods
# (page_scrape*, firecrawl*, scrapedo*, *local_bhd, converted_usd, serper*)
# do NOT count.
_ESTIMATE_METHODS = {"estimated", "gpt_training_estimate", "gpt_estimate"}


def _is_estimate_method(method) -> bool:
    if not isinstance(method, str):
        return False
    return method in _ESTIMATE_METHODS or method.startswith("gpt_")


def _price_routes(response: Dict[str, Any]) -> List[Optional[str]]:
    """Pull each product's price-race `route` from metadata.source_trace."""
    routes: List[Optional[str]] = []
    trace = (response.get("metadata") or {}).get("source_trace") or {}
    for prod in trace.get("products", []) or []:
        price_race = (prod.get("races") or {}).get("price") or {}
        routes.append(price_race.get("route"))
    return routes


def _source_methods(response: Dict[str, Any]) -> List[Optional[str]]:
    """Pull each product's price.source_method (estimated vs scraped)."""
    methods: List[Optional[str]] = []
    products = response.get("products") or (response.get("overview") or {}).get("products") or []
    for p in products:
        price = p.get("price") if isinstance(p, dict) else None
        if isinstance(price, dict):
            methods.append(price.get("source_method"))
        else:
            methods.append(None)
    return methods


async def _run_one(client: httpx.AsyncClient, base_url: str, entry: Dict[str, Any],
                   nocache: bool, timeout: float) -> Dict[str, Any]:
    params = {"q": entry["query"], "region": entry.get("region", "bahrain")}
    if nocache:
        params["nocache"] = "true"
    if entry.get("category"):
        params["selected_category"] = entry["category"]
    url = base_url.rstrip("/") + "/api/v1/text/compare"
    t0 = time.perf_counter()
    out: Dict[str, Any] = {
        "id": entry["id"], "query": entry["query"], "category": entry["category"],
        "expect_bahrain_registry": entry.get("expect_bahrain_registry", False),
    }
    try:
        r = await client.get(url, params=params, timeout=timeout)
        out["status"] = r.status_code
        if r.status_code != 200:
            out["error"] = r.text[:200]
            return out
        data = r.json()
    except Exception as e:  # noqa: BLE001
        out["status"] = "exception"
        out["error"] = f"{type(e).__name__}: {e}"
        return out
    finally:
        out["wall_s"] = round(time.perf_counter() - t0, 2)

    routes = _price_routes(data)
    methods = _source_methods(data)
    out["price_routes"] = routes
    out["source_methods"] = methods
    out["escalated"] = any(rt for rt in routes)
    out["has_registry_route"] = any(rt == "registry" for rt in routes)
    out["estimated_count"] = sum(1 for m in methods if _is_estimate_method(m))
    out["product_count"] = len(methods)
    return out


async def _main_async(args: argparse.Namespace) -> int:
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    queries = matrix["queries"]
    nocache = not args.no_nocache

    print(f"[bias-probe] base_url={args.base_url}  queries={len(queries)}  "
          f"nocache={nocache}  concurrency={args.concurrency}")
    sem = asyncio.Semaphore(args.concurrency)
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        async def _guarded(entry):
            async with sem:
                res = await _run_one(client, args.base_url, entry, nocache, args.timeout)
                flag = "OK " if res.get("status") == 200 else "ERR"
                reg = "REGISTRY" if res.get("has_registry_route") else (
                    "esc:" + ",".join(r for r in (res.get("price_routes") or []) if r) if res.get("escalated") else "no-escalation"
                )
                print(f"  [{flag}] {res['id']:<10} est={res.get('estimated_count','?')}/"
                      f"{res.get('product_count','?')} {reg}  ({res.get('wall_s','?')}s)")
                return res
        results = await asyncio.gather(*(_guarded(e) for e in queries))

    # ---- Aggregate verdict ----
    ok = [r for r in results if r.get("status") == 200]
    errored = [r for r in results if r.get("status") != 200]
    escalated = [r for r in ok if r.get("escalated")]
    registry_hits = [r for r in ok if r.get("has_registry_route")]
    total_products = sum(r.get("product_count", 0) for r in ok)
    total_estimated = sum(r.get("estimated_count", 0) for r in ok)

    # Per-category registry coverage.
    by_cat: Dict[str, Dict[str, int]] = {}
    for r in ok:
        c = r["category"]
        b = by_cat.setdefault(c, {"n": 0, "registry": 0, "escalated": 0})
        b["n"] += 1
        b["registry"] += 1 if r.get("has_registry_route") else 0
        b["escalated"] += 1 if r.get("escalated") else 0

    print("\n=== BIAS MATRIX VERDICT ===")
    print(f"queries 200-OK:        {len(ok)}/{len(results)}  (errors: {len(errored)})")
    print(f"escalated to Tier 1.5: {len(escalated)}/{len(ok)}")
    print(f"registry-route hits:   {len(registry_hits)}/{len(ok)}")
    print(f"gpt_training-priced products: {total_estimated}/{total_products} "
          f"({round(100*total_estimated/total_products,1) if total_products else 0}%)")
    print("per-category registry coverage:")
    for c, b in sorted(by_cat.items()):
        print(f"  {c:<12} registry {b['registry']}/{b['n']}  escalated {b['escalated']}/{b['n']}")

    # The core F1.7 assertion: >=1 registry route across the matrix, and every
    # query flagged expect_bahrain_registry that escalated should show one.
    expected = [r for r in ok if r.get("expect_bahrain_registry")]
    expected_missing = [r["id"] for r in expected if r.get("escalated") and not r.get("has_registry_route")]

    passed = len(registry_hits) >= 1
    print("\n--- F1.7 gate ---")
    print(f"PASS condition (>=1 registry route): {'PASS' if passed else 'FAIL'}")
    if expected_missing:
        print(f"NOTE — escalated 'expect_bahrain_registry' queries with NO registry route "
              f"(may be genuine no-BH-stock): {expected_missing}")
    if errored:
        print(f"ERRORS: {[(r['id'], r.get('error','')[:80]) for r in errored]}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "base_url": args.base_url, "nocache": nocache,
            "summary": {
                "ok": len(ok), "errors": len(errored), "escalated": len(escalated),
                "registry_hits": len(registry_hits),
                "estimated_products": total_estimated, "total_products": total_products,
                "by_category": by_cat,
            },
            "results": results,
        }, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")

    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="F1.7 Bahrain-consultation bias-matrix probe")
    ap.add_argument("--base-url", required=True, help="backend root, e.g. http://localhost:8000")
    ap.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--no-nocache", action="store_true", help="hit caches (cheaper, less faithful)")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

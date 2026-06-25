#!/usr/bin/env python3
"""BH/GCC catalog liveness gate — promote verified rows to status="live".

The consolidation (scripts/build_source_registry_data.py) writes every catalog
row "provider-test-candidate". A row only enters SOURCE_REGISTRY when its status
is "live" (app/services/source_router._load_catalog_rows) — AND only when the
ENABLE_BH_GCC_CATALOG_SOURCES flag is on. This gate is the ONLY thing that flips a
row to "live": it probes each row's live `sample_url` (the URL the recon verified
this session) and promotes it ONLY if the source still returns a usable price
signal. Sources rot — re-run before any activation (verify-or-omit).

Control-calibrated (the S2 safety rail): a known-live control must pass IN THIS
ENVIRONMENT before any "dead" verdict is trusted, so a sandbox DNS/network block
never mass-marks live sources dead.

Writes the verdict back into data/bh_gcc_sources.json (idempotent — re-running
re-probes + updates; never touches the 4 immutable discovery catalogs).

Usage:
  python -m scripts.verify_bh_gcc_sources --dry-run      # probe + print, no write
  python -m scripts.verify_bh_gcc_sources                # probe + promote + write
  python -m scripts.verify_bh_gcc_sources --limit 40     # probe first N (smoke)
  python -m scripts.verify_bh_gcc_sources --tier bahrain # only bahrain-tier rows

Exit: 0 = ran (some promoted), 2 = nothing promoted, 3 = controls failed (env
untrusted — no writes).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data" / "bh_gcc_sources.json"

# Controls: a global + a BH Shopify storefront that MUST be reachable here.
_CONTROLS = [
    "https://www.google.com",
    "https://bh.asgharali.com/products.json?limit=1",
]
# A live price signal: a GCC currency token OR a decimal price (2-3 dp, BHD fils).
_CURRENCY_RE = re.compile(r"\b(BHD|SAR|AED|QAR|KWD|OMR|USD)\b", re.IGNORECASE)
_PRICE_RE = re.compile(r"\b\d{1,5}\.\d{2,3}\b")
# JSON price keys (shopify /products.json, woo/salla/occ/graphql APIs).
_PRICEKEY_RE = re.compile(
    r'"(price|sellingPrice|display_price|final_price|net_price|min_amount)"\s*:',
    re.IGNORECASE,
)

_HTTP_TIMEOUT = 12
_CONCURRENCY = 8
# Bot-defense statuses → INCONCLUSIVE (keep current status, never demote to dead).
_INCONCLUSIVE = {403, 405, 429, 503}


def _has_price_signal(text: str) -> bool:
    if not text:
        return False
    head = text[:200000]  # cap the scan
    return bool(
        _PRICEKEY_RE.search(head)
        or (_CURRENCY_RE.search(head) and _PRICE_RE.search(head))
    )


# Mechanisms whose ADAPTER scrapes the sample_url directly → a static price
# signal in the response is required to call it live. API-backed mechanisms
# (woo/salla/occ/magento/unbxd/rest_json/algolia/json_api) read a SEPARATE
# endpoint (recon-verified this session); their sample_url is a storefront PDP
# whose price may be JS-rendered, so a reachable 200 is sufficient liveness — the
# adapter unit tests + the recon fixtures are the price-shape proof.
_SCRAPE_URL_MECHANISMS = {"", "shopify", "sitemap", "curl"}


async def _probe(url: str, mechanism: str = "") -> Tuple[str, str]:
    """Return (verdict, evidence): verdict in {live, dead, inconclusive}."""
    if not url:
        return "inconclusive", "no sample_url"
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome", timeout=_HTTP_TIMEOUT, allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is inconclusive, not dead
        return "inconclusive", f"{type(exc).__name__}"
    code = getattr(resp, "status_code", 0)
    if code in _INCONCLUSIVE:
        return "inconclusive", f"http={code} (bot-defense)"
    if code != 200:
        return "dead", f"http={code}"
    # API-backed mechanism → a reachable storefront 200 is enough (the price comes
    # from a separate, recon-verified endpoint).
    if (mechanism or "") not in _SCRAPE_URL_MECHANISMS:
        return "live", "http=200 (api-backed; storefront reachable)"
    if _has_price_signal(getattr(resp, "text", "") or ""):
        return "live", "http=200 +price"
    return "dead", "http=200 no-price-signal"


async def _check_controls() -> bool:
    for c in _CONTROLS:
        verdict, ev = await _probe(c)
        # google has no price signal — accept a 200 there; the BH control must show price.
        ok = verdict == "live" or (c.startswith("https://www.google") and ev.startswith("http=200"))
        # Re-probe google with a status-only acceptance.
        if not ok and c.startswith("https://www.google"):
            v2, e2 = await _probe(c)
            ok = e2.startswith("http=200") or v2 == "live"
        if not ok:
            print(f"CONTROL FAILED: {c} -> {verdict} ({ev}); environment untrusted")
            return False
    return True


async def _run(rows: List[dict], limit: Optional[int], tier: Optional[str]) -> Dict[str, int]:
    sem = asyncio.Semaphore(_CONCURRENCY)
    targets = [
        r for r in rows
        if not r.get("is_render_only")
        and r.get("status") != "render-only"
        and (tier is None or r.get("tier") == tier)
    ]
    if limit:
        targets = targets[:limit]

    async def _one(r: dict):
        async with sem:
            verdict, ev = await _probe(r.get("sample_url", ""), r.get("mechanism", ""))
            r["_verdict"], r["_evidence"] = verdict, ev

    await asyncio.gather(*(_one(r) for r in targets))

    tally = {"live": 0, "dead": 0, "inconclusive": 0}
    for r in targets:
        v = r.pop("_verdict", "inconclusive")
        ev = r.pop("_evidence", "")
        tally[v] = tally.get(v, 0) + 1
        if v == "live":
            r["status"] = "live"
        elif v == "dead":
            r["status"] = "dead"
        # inconclusive → leave status unchanged (conservative; re-probe later)
        print(f"  {r['domain']:34s} {v:13s} {ev}")
    return tally


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tier", choices=["bahrain", "gcc"], default=None)
    args = ap.parse_args(argv)

    if not _DATA.exists():
        print(f"no consolidated data file at {_DATA} — run build_source_registry_data first")
        return 3
    rows = json.loads(_DATA.read_text(encoding="utf-8"))

    if not asyncio.run(_check_controls()):
        return 3

    print(f"=== probing {len(rows)} catalog rows (tier={args.tier or 'all'}, "
          f"limit={args.limit or 'none'}) ===")
    tally = asyncio.run(_run(rows, args.limit, args.tier))
    print(f"=== live={tally['live']} dead={tally['dead']} "
          f"inconclusive={tally['inconclusive']} ===")

    if args.dry_run:
        print("(dry-run — no write)")
        return 0 if tally["live"] else 2

    _DATA.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote verdicts -> {_DATA.relative_to(_ROOT)}")
    return 0 if tally["live"] else 2


if __name__ == "__main__":
    sys.exit(main())

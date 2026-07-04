"""Serper-free KPI truth-set freshness probe.

Run before EVERY KPI gate so a RED gate is never blamed on retired SKUs —
the 2026-06-27 electronics truth set went 4/6 dead at BH retail within days
(discontinued / zero in-stock+priced PDPs) and would have read as a code
regression. For each entry in data/usable_exact_genuine_truth.json this asks
the three Serper-free BH doors whether an in-stock PRICED hit exists and
reports the top title/price:

  - bahrain.sharafdg.com Algolia (public search-only creds — pinned in
    app/services/algolia_service.py ALGOLIA_EXPLICIT_STORES)
  - extra.com Unbxd (public site-search key — pinned in
    app/services/unbxd_service.py UNBXD_STORES)
  - noon.com BH search (--noon; x-locale: en-bh HEADER flips the catalog to
    BHD — without it the response is the SAR catalog with NO currency field)

Matching is a deliberately LOOSE token heuristic (a freshness probe, not the
correctness gate) plus two tiny guards against the recon-proven false
certifiers: accessory/game/bundle rows (a MacBook CASE / Switch-2 GAME must
not certify the console) and flanker tokens the query does not carry (an
Ultra/FE hit must not certify the base model). stdlib + curl_cffi only, NO
app-service imports (they pull the cache stack). A sharafdg price<=0 row is
NOT counted (known index quirk: in_stock=1 rows with price=0). Coverage is
partial for fashion (namshi/6thstreet/footlocker are not probed) — a STALE
verdict there means "not at these three doors", not "retired". Usage:

    python scripts/probe_truth_freshness.py <out.txt> [--noon]
"""
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

from curl_cffi import requests as curl_requests

REPO_ROOT = Path(__file__).resolve().parent.parent
TRUTH = REPO_ROOT / "data" / "usable_exact_genuine_truth.json"

ALGOLIA = {"app_id": "9KHJLG93J1", "api_key": "e81d5b30a712bb28f0f1d2a52fc92dd0",
           "index": "bahrain_products"}
UNBXD = {"api_key": "72883ca2a4420a7c7ca07cefda404539",
         "site_key": "ss-unbxd-auk-extra-bahrain-en-prod11541714990628"}
NOON_HDRS = {"x-locale": "en-bh", "x-platform": "web", "x-mp": "noon",
             "accept": "application/json"}


def _tokens(text):
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split() if w}


# "gaming" is deliberately absent — the genuine Switch-2 console title contains it
_ACCESSORY_TELLS = {"case", "cover", "skin", "protector", "charger", "cable",
                    "compatible", "game", "bundle"}
_FLANKER_TELLS = {"fe", "ultra", "plus", "pro", "max", "mini", "lite", "edge"}


def _loose_match(query, title):
    """>=60% of query tokens present — freshness heuristic, NOT _selection_match.
    The two tell-sets only reject the recon-proven false certifiers. Every
    DIGIT-BEARING query token (s25 / m3 / 128gb / 11) is a HARD requirement
    (Wave-B review MED): a successor-generation title ("Galaxy S26 5G 256GB",
    "iPad Air M4") shares enough marketing tokens to clear the 0.6 overlap and
    would false-certify the PREVIOUS entry — the exact staleness class this
    probe exists to catch. Title-side digit ADDS ("(2025)") stay loose: only
    the query's own digits must appear."""
    q, t = _tokens(query), _tokens(title)
    if not q:
        return False
    if {w for w in q if any(c.isdigit() for c in w)} - t:
        return False
    if len(q & t) / len(q) < 0.6:
        return False
    if t & _ACCESSORY_TELLS or (t - q) & _FLANKER_TELLS:
        return False
    return True


def probe_sharafdg(query):
    url = f"https://{ALGOLIA['app_id']}-dsn.algolia.net/1/indexes/{ALGOLIA['index']}/query"
    headers = {"X-Algolia-API-Key": ALGOLIA["api_key"],
               "X-Algolia-Application-Id": ALGOLIA["app_id"],
               "Content-Type": "application/json"}
    r = curl_requests.post(url, headers=headers,
                           data=json.dumps({"query": query, "hitsPerPage": 12}),
                           impersonate="chrome", timeout=15)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    for h in r.json().get("hits") or []:
        title = h.get("post_title") or h.get("name") or h.get("title") or ""
        price = h.get("price")
        # price<=0 rows are the known sharafdg index quirk — never count them
        if h.get("in_stock") and isinstance(price, (int, float)) and price > 0 \
                and _loose_match(query, title):
            return {"in_stock": True, "title": title, "price": price}
    return {"in_stock": False}


def probe_extra(query):
    url = (f"https://search.unbxd.io/{UNBXD['api_key']}/{UNBXD['site_key']}/search"
           f"?q={quote_plus(query)}&rows=12")
    r = curl_requests.get(url, impersonate="chrome", timeout=15, allow_redirects=True)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    for p in (r.json().get("response") or {}).get("products") or []:
        title = p.get("title") or p.get("name") or ""
        price = p.get("sellingPrice") or p.get("price")
        if p.get("inStockFlag") and isinstance(price, (int, float)) and price > 0 \
                and _loose_match(query, title):
            return {"in_stock": True, "title": title, "price": price}
    return {"in_stock": False}


def probe_noon(query):
    url = f"https://www.noon.com/_svc/catalog/api/v3/search?q={quote_plus(query)}&limit=10"
    r = curl_requests.get(url, headers=NOON_HDRS, impersonate="chrome",
                          timeout=20, allow_redirects=True)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    for h in r.json().get("hits") or []:
        title = h.get("name") or ""
        price = h.get("sale_price") or h.get("price")  # sale_price can be null
        if h.get("is_buyable") and isinstance(price, (int, float)) and price > 0 \
                and _loose_match(query, title):
            return {"in_stock": True, "title": title, "price": price}
    return {"in_stock": False}


def main():
    if len(sys.argv) < 2:
        sys.stdout.write("usage: probe_truth_freshness.py <out.txt> [--noon]\n")
        return 2
    out_path = sys.argv[1]
    sources = [("sharafdg", probe_sharafdg), ("extra", probe_extra)]
    if "--noon" in sys.argv[2:]:
        sources.append(("noon", probe_noon))

    truth = json.load(io.open(TRUTH, encoding="utf-8"))["products"]
    lines, stale = [], []
    for entry in truth:
        eid, query = entry["id"], entry["query"]
        found = False
        for name, fn in sources:
            try:
                res = fn(query)
            except Exception as e:  # noqa: BLE001 — probe keeps going per source
                res = {"error": repr(e)}
            if res.get("error"):
                lines.append(f"{eid} [{name}] ERROR {res['error']}")
            elif res.get("in_stock"):
                found = True
                lines.append(f"{eid} [{name}] IN-STOCK {res['price']} BHD :: {res['title']}")
            else:
                lines.append(f"{eid} [{name}] no in-stock priced hit")
            time.sleep(0.6)  # noon rate-limits rapid repeats; be polite everywhere
        if not found:
            stale.append(f"{eid} :: {query}")
        lines.append("")

    lines.append(f"STALE ({len(stale)}/{len(truth)}) — no in-stock priced BH hit at any probed source:")
    lines.extend(f"  {s}" for s in stale or ["  (none)"])
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.stdout.write(f"WROTE {out_path} (stale {len(stale)}/{len(truth)})\n")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())

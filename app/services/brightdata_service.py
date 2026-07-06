"""Bright Data SERP API fallback provider (2026-07-07).

A drop-in, Serper-SHAPED discovery provider used as a FALLBACK when the Serper
key is exhausted/erroring (the recurring free-key-depletion class the scraper
audit surfaced). Bright Data's SERP API has a 5,000-requests/MONTH forever-free
tier, so this can cover the fallback-of-last-resort volume at $0.

Request shape (verified against docs.brightdata.com/api-reference/serp):
    POST https://api.brightdata.com/request
      Authorization: Bearer <BRIGHTDATA_API_KEY>
      Content-Type: application/json
      {"zone": "<BRIGHTDATA_ZONE>",
       "url": "https://www.google.com/search?q=<q>&brd_json=1&gl=bh&hl=en&num=10",
       "format": "raw"}
  brd_json=1 → Google's PARSED SERP as JSON (organic[] + shopping[] for tbm=shop).

Returns the SAME shape serper_service does — {"organic": [...], "shopping": [...]}
— so the pipeline consumes it identically. NEVER raises (best-effort → {} / the
empty shape on any error), so a Bright Data outage can never break a compare.

ACTIVATION (Ahmed): set 3 Railway env vars — ENABLE_BRIGHTDATA_FALLBACK=true,
BRIGHTDATA_API_KEY=<token>, BRIGHTDATA_ZONE=<serp zone name>. All OFF/unset →
this module is inert and the pipeline is byte-identical to Serper-only.

MAPPER NOTE: the brd_json organic/shopping field names are read DEFENSIVELY
(link|url, description|snippet, seller|source, ...). Validate the mapping on the
first live call after activation (a one-line probe: `python -c "import asyncio,
app.services.brightdata_service as b; print(asyncio.run(b.bd_search_web('iphone 15')))"`)
and tighten `_map_bd_organic` / `_map_bd_shopping` if a field differs.
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

BRIGHTDATA_URL = "https://api.brightdata.com/request"
_GOOGLE_SEARCH = "https://www.google.com/search"
_TIMEOUT = 20.0  # Bright Data SERP is sync but proxies a real Google fetch (1-5s)


def _brightdata_enabled() -> bool:
    """True iff the Bright Data fallback is active: the flag is ON *and* both
    credentials are present. Read per-call so an env flip takes effect without a
    restart (mirrors the serper key resolution). All unset → False → inert."""
    flag = os.getenv("ENABLE_BRIGHTDATA_FALLBACK", "").strip().lower() in (
        "true", "1", "yes", "on",
    )
    return flag and bool(os.getenv("BRIGHTDATA_API_KEY")) and bool(os.getenv("BRIGHTDATA_ZONE"))


def _google_url(query: str, *, country: str, num: int, shopping: bool) -> str:
    params = {"q": query, "brd_json": "1", "gl": country, "hl": "en", "num": num}
    if shopping:
        params["tbm"] = "shop"
    return f"{_GOOGLE_SEARCH}?{urlencode(params)}"


async def _bd_post(query: str, *, country: str, num: int, shopping: bool) -> Optional[Dict[str, Any]]:
    """One Bright Data SERP request → the parsed Google SERP JSON, or None on any
    failure. Never raises."""
    key = os.getenv("BRIGHTDATA_API_KEY")
    zone = os.getenv("BRIGHTDATA_ZONE")
    if not (key and zone):
        return None
    payload = {
        "zone": zone,
        "url": _google_url(query, country=country, num=num, shopping=shopping),
        "format": "raw",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                BRIGHTDATA_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            logger.warning("[brightdata] HTTP %s for %r", resp.status_code, query[:60])
            return None
        # format:raw returns the brd_json body directly as JSON text.
        return resp.json()
    except Exception as e:  # noqa: BLE001 — fallback must never break the compare
        logger.warning("[brightdata] request failed for %r: %s", query[:60], e)
        return None


def _first(d: Dict[str, Any], *keys) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _map_bd_organic(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Bright Data parsed `organic` → Serper `organic` shape
    ({title, link, snippet}). Defensive field reads (link|url, description|
    snippet). Unknown/empty → []."""
    if not isinstance(parsed, dict):
        return []
    rows = parsed.get("organic")
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        link = _first(r, "link", "url", "display_link")
        if not link:
            continue
        out.append({
            "title": _first(r, "title") or "",
            "link": link,
            "snippet": _first(r, "snippet", "description", "desc") or "",
        })
    return out


def _map_bd_shopping(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Bright Data parsed shopping (tbm=shop) → Serper `shopping` shape
    ({title, source, link, price, ...}). Bright Data may key the array as
    `shopping` / `pla` / `products`; read defensively. Unknown/empty → []."""
    if not isinstance(parsed, dict):
        return []
    rows = _first(parsed, "shopping", "pla", "products", "shopping_results")
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        link = _first(r, "link", "url", "product_link")
        title = _first(r, "title", "name")
        if not (link or title):
            continue
        out.append({
            "title": title or "",
            "link": link or "",
            "source": _first(r, "source", "seller", "merchant", "store") or "",
            "price": _first(r, "price", "extracted_price", "price_raw"),
        })
    return out


async def bd_search_web(query: str, num_results: int = 10, country: str = "bh") -> Dict[str, Any]:
    """Serper-shaped web (organic) search via Bright Data. Returns
    {"organic": [...], "shopping": []} or {"organic": []} on miss. Never raises.
    Caller should gate on _brightdata_enabled()."""
    parsed = await _bd_post(query, country=country, num=num_results, shopping=False)
    if parsed is None:
        return {"organic": [], "error": "brightdata_unavailable"}
    return {"organic": _map_bd_organic(parsed), "shopping": []}


async def bd_search_shopping(query: str, country: str = "bh") -> Dict[str, Any]:
    """Serper-shaped shopping search via Bright Data (tbm=shop). Returns
    {"shopping": [...], "organic": []} or {"shopping": []} on miss. Never raises."""
    parsed = await _bd_post(query, country=country, num=10, shopping=True)
    if parsed is None:
        return {"shopping": [], "error": "brightdata_unavailable"}
    return {"shopping": _map_bd_shopping(parsed), "organic": _map_bd_organic(parsed)}

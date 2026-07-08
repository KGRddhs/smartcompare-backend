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


def _brightdata_budget_gate_enabled() -> bool:
    """Scraping audit 2026-07-08 — gate the monthly budget cap + circuit breaker +
    per-request metering around each Bright Data SERP call. Read per-call (env flip,
    no restart). Default OFF → the gate block is an inert `if False:` branch so the
    fallback path is BYTE-IDENTICAL to current main (unbounded, exactly as today)."""
    return os.getenv("ENABLE_BRIGHTDATA_BUDGET_GATE", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _bd_budget_precheck() -> bool:
    """When the gate is ON, allow a Bright Data dispatch only if the circuit is
    closed AND the monthly budget has headroom. Fail-OPEN on Redis outage (mirrors
    every other provider — has_budget returns True when Upstash is down). Gate OFF →
    always True (no api_budget_service call → byte-identical)."""
    if not _brightdata_budget_gate_enabled():
        return True
    try:
        from app.services import api_budget_service
        return api_budget_service.is_circuit_closed("brightdata") and api_budget_service.has_budget("brightdata")
    except Exception:  # noqa: BLE001 — a metering fault must never harden into a compare break
        return True


def _bd_record(success: bool) -> None:
    """Meter every DISPATCHED Bright Data request (it bills per request regardless of
    hit) and feed the circuit breaker. No-op when the gate is OFF → byte-identical."""
    if not _brightdata_budget_gate_enabled():
        return
    try:
        from app.services import api_budget_service
        api_budget_service.record_usage("brightdata")
        if success:
            api_budget_service.record_success("brightdata")
        else:
            api_budget_service.record_failure("brightdata")
    except Exception:  # noqa: BLE001 — metering must never break the fallback
        pass


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
            logger.warning(
                "[brightdata] HTTP %s for %r: %s", resp.status_code, query[:60],
                (resp.text or "")[:200],
            )
            return None
        # format:raw + brd_json=1 returns the PARSED Google SERP as JSON text.
        try:
            parsed = resp.json()
        except Exception:  # noqa: BLE001 — non-JSON (e.g. raw HTML) — self-diagnose
            # SELF-VALIDATION (2026-07-07) — I could not live-test the response from
            # the build machine (api.brightdata.com is TLS-blocked there). If brd_json
            # did NOT yield JSON, log the first 300 chars so the FIRST prod call reveals
            # whether the zone returns HTML (→ needs data_format:json) instead of a
            # silent empty fallback.
            logger.warning(
                "[brightdata] non-JSON response for %r (brd_json may be off / zone "
                "returns HTML) — first 300 chars: %s", query[:60], (resp.text or "")[:300],
            )
            return None
        # First-call schema visibility — log the parsed top-level shape at INFO so the
        # mapper can be validated/tightened from prod logs without a debug flag.
        if isinstance(parsed, dict):
            _org = parsed.get("organic")
            logger.info(
                "[brightdata] parsed OK for %r: top-keys=%s organic=%s org0_keys=%s",
                query[:40], list(parsed.keys())[:12],
                (len(_org) if isinstance(_org, list) else type(_org).__name__),
                (list(_org[0].keys()) if isinstance(_org, list) and _org and isinstance(_org[0], dict) else None),
            )
        return parsed
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
    if not _bd_budget_precheck():
        # Gate ON + (budget exhausted or breaker open) → skip the dispatch and
        # degrade to Serper-only. Empty shape callers already treat as a miss.
        return {"organic": [], "error": "brightdata_budget"}
    parsed = await _bd_post(query, country=country, num=num_results, shopping=False)
    _bd_record(parsed is not None)
    if parsed is None:
        return {"organic": [], "error": "brightdata_unavailable"}
    return {"organic": _map_bd_organic(parsed), "shopping": []}


async def bd_search_shopping(query: str, country: str = "bh") -> Dict[str, Any]:
    """Serper-shaped shopping search via Bright Data (tbm=shop). Returns
    {"shopping": [...], "organic": []} or {"shopping": []} on miss. Never raises."""
    if not _bd_budget_precheck():
        return {"shopping": [], "error": "brightdata_budget"}
    parsed = await _bd_post(query, country=country, num=10, shopping=True)
    _bd_record(parsed is not None)
    if parsed is None:
        return {"shopping": [], "error": "brightdata_unavailable"}
    return {"shopping": _map_bd_shopping(parsed), "organic": _map_bd_organic(parsed)}

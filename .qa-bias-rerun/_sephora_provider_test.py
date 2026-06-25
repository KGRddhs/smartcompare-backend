"""WAVE 5 (bh-source-intelligence bundle) — OUT-OF-BAND provider-test harness for
sephora.me (the lone CF/Akamai-walled `requires_super` BH beauty source).

THE OPEN QUESTION (F5a / OU-1): does a residential-BH egress (Scrape.do `super`
+ geoCode=bh, OR Zyte browserHtml + geolocation:BH) crack Akamai Bot Manager
where a plain datacenter render gets a 403 AkamaiGHost? sephora.me /bh-en is
Akamai-walled; a non-BH datacenter IP gets 403 on the PDP/category/search shapes
(only /bh-en/brands returns 200, with 0 harvestable links). This harness FORCES
`super` onto known-live sephora.me URLs — a render capability prod has NEVER
exercised (the cascade short-circuits before Tier 1.5d on every real pull, OU-6).

CRITICAL — THIS IS NOT PROD CODE:
  * NOT wired into the cascade / source_router / any request path.
  * Does NOT flip the prod SCRAPEDO_SUPER flag on Railway (it sets the flag only
    in THIS process's env, then resets the in-process cache so the local
    scrapedo_service request params include super=true for the experiment).
  * Writes NOTHING to prod Redis (UPSTASH creds blanked BEFORE the service
    import → cache_service.redis_client is None → api_budget_service.record_usage
    no-ops and the shared Scrape.do breaker fails open → never polluted/tripped).
  * No fabricated data — every recorded outcome comes from a real HTTP response.

SPEND GATE: a SCRIPT-LOCAL cap of 60 Scrape.do credits/run (the sole spend gate,
out-of-band). The harness aborts BEFORE any call if `credits_spent + 25 (super
worst-case) > 60`. Zyte has its own fixed cap (4 renders) + needs ZYTE_API_KEY
in LOCAL .env (the leg is skipped gracefully if the key is unset).

RUN STEP (NOT this build wave — a separate post-ship step that spends credits):
    python .qa-bias-rerun/_sephora_provider_test.py
Then read `.qa-bias-rerun/_sephora_provider_test_result.json` → `verdict`:
  GO_SCRAPEDO : super geoCode=bh returns 200, no Akamai marker, AND a BHD price
                OR harvestable PDP links (then a SEPARATE narrow-wire decision).
  GO_ZYTE     : super 403s but Zyte browserHtml+geolocation:BH passes.
  NO_GO       : both block all 4 real URLs → document the structural Akamai gap,
                keep SCRAPEDO_SUPER OFF (sephora.me categories are largely
                covered by boutiqaat + nasser anyway).
"""
import os
import sys
import json
import time
import asyncio
import logging
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- ENV GUARD: no-prod-write + force super, in THIS order (the footgun) -------
# 1) load_dotenv FIRST so SCRAPEDO_API_TOKEN / ZYTE_API_KEY come from LOCAL .env.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 2) Blank Upstash creds BEFORE importing any app.services module → cache_service
#    initializes redis_client = None at import → record_usage no-ops, breaker
#    fail-open. (Blanking AFTER the import would be too late — the client is
#    built at module import time.)
os.environ["UPSTASH_REDIS_URL"] = ""
os.environ["UPSTASH_REDIS_TOKEN"] = ""

# 3) Force the super/geoCode render ON for THIS process only, with a generous
#    off-clock render timeout. These touch os.environ, NOT Railway.
os.environ["SCRAPEDO_SUPER"] = "true"
os.environ["SCRAPEDO_GEOCODE"] = "bh"
os.environ["SCRAPEDO_TIMEOUT"] = "35"
os.environ["ENABLE_SCRAPEDO"] = "true"

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Import AFTER the env guard (cache_service reads the blanked creds at import).
from app.services import scrapedo_service  # noqa: E402
from app.services.price_service import extract_price_from_html  # noqa: E402

# 4) MUST reset the process-cached super-flags so render_page_with_status reads
#    the now-true SCRAPEDO_SUPER we just set (the flag is cached at first read).
scrapedo_service.reset_super_flags_cache()

# ---------------------------------------------------------------------------
# Classification — pure functions, NO network. Unit-tested in
# tests/test_sephora_provider_test_classify.py against a saved-HTML fixture.
# ---------------------------------------------------------------------------

# Akamai-block fingerprints (case-insensitive substring scan). Distinct from the
# prod Cloudflare markers; sephora.me serves "Server: AkamaiGHost" + a "Reference
# #..." access-denied body. NOTE: the prod _CF_INTERSTITIAL_MARKERS in
# structured_comparison_service.py is separately extended (OU-3) so a 403 Akamai
# render is flagged detected_cf in metadata.source_trace; this local copy keeps
# the harness self-contained (no prod import dependency for the classifier).
AKAMAI_BLOCK_MARKERS = (
    "akamaighost",
    "reference #",
    "access denied",
    "akamai",
    "you don't have permission to access",
)


def looks_akamai_blocked(html: Optional[str], status: int) -> bool:
    """True iff this response looks like an Akamai Bot-Manager block: a 403
    status, OR a body carrying any Akamai-block marker (a 200 challenge page
    still counts as blocked). Empty/None body with a non-403 status → not
    blocked on the body axis (the status carries the signal)."""
    if status == 403:
        return True
    if not html or not isinstance(html, str):
        return False
    low = html.lower()
    return any(m in low for m in AKAMAI_BLOCK_MARKERS)


def harvest_pdp_links(html: Optional[str], locale: str = "/bh-en") -> list:
    """Pure link-harvest for the category/search shapes: return the distinct
    sephora.me PDP hrefs (the `…/p/{slug}/{id}` shape) found in the HTML. A
    real harvestable category/search page yields >0; the 403/empty walls yield
    []. No network — operates on already-fetched HTML."""
    if not html or not isinstance(html, str):
        return []
    import re
    # /bh-en/p/<slug>/<digits> — the live PDP pattern (pdp_url_pattern in the
    # source_router sephora.me row). Tolerate an optional leading host, but DEDUP
    # on the locale-anchored PATH so the same PDP referenced both absolutely
    # (https://www.sephora.me/bh-en/p/…) and relatively (/bh-en/p/…) collapses to
    # one product. Capturing group = the path; findall returns the group.
    pat = re.compile(r'(?:https?://[^"\'\s]*?)?(' + re.escape(locale) + r'/p/[a-z0-9\-]+/\d+)', re.I)
    seen = []
    for path in pat.findall(html):
        if path not in seen:
            seen.append(path)
    return seen


def classify_outcome(html: Optional[str], status: int, price: Optional[dict],
                     harvested: list) -> str:
    """Classify a single fetched URL shape into one of:
      'akamai_block' — 403 or an Akamai-marker body (a wall, not a real miss).
      'pass_price'   — 200, not blocked, AND a BHD price extracted.
      'pass_harvest' — 200, not blocked, AND >0 harvestable PDP links.
      'no_price'     — 200, not blocked, but neither a price nor links (e.g. the
                       un-walled /bh-en/brands control: 200 with 0 PDP links).
      'empty'        — no body and not a 403 (timeout/short content)."""
    if looks_akamai_blocked(html, status):
        return "akamai_block"
    if not html:
        return "empty"
    if price and price.get("amount"):
        return "pass_price"
    if harvested:
        return "pass_harvest"
    return "no_price"


# ---------------------------------------------------------------------------
# Targets — the 4 LIVE-VERIFIED sephora.me URL shapes (no rediscovery needed).
# (label, kind, url, query_name)
# ---------------------------------------------------------------------------
TARGETS = [
    ("pdp", "pdp",
     "https://www.sephora.me/bh-en/p/size-up-immediate-supersized-volume-mascara/713779",
     "Size Up Immediate Supersized Volume Mascara"),
    ("category", "harvest", "https://www.sephora.me/bh-en/makeup", "makeup"),
    ("search", "harvest", "https://www.sephora.me/bh-en/search?q=mascara", "mascara"),
    ("brands_control", "control", "https://www.sephora.me/bh-en/brands", "brands"),
]

# Spend gate.
SCRAPEDO_CREDIT_CAP = 60
SUPER_WORST_CASE = 25  # super bills ~10-25 credits/req
ZYTE_RENDER_CAP = 4


# ---------------------------------------------------------------------------
# Scrape.do leg (super geoCode=bh, the real prod service, metering no-op'd).
# ---------------------------------------------------------------------------
async def _scrapedo_attempt(label: str, kind: str, url: str, qname: str,
                            credits_spent: int) -> Tuple[dict, int]:
    """Run ONE super render via the prod render_page_with_status (returns
    (html,status,cost)). Returns (record, new_credits_spent). Mirrors the prod
    _record_provider_attempt field set so a future narrow-wire can replay this
    into source_trace."""
    t0 = time.perf_counter()
    # Pre-call spend guard — abort BEFORE the call if worst-case would exceed cap.
    if credits_spent + SUPER_WORST_CASE > SCRAPEDO_CREDIT_CAP:
        rec = _make_record(label, kind, url, status=0, cost=0,
                           outcome="skipped_credit_cap", html_kb=0,
                           detected_cf=False, elapsed_ms=0,
                           extracted_price=None, harvested=[])
        return rec, credits_spent
    html, status, cost = await scrapedo_service.render_page_with_status(url)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    credits_spent += int(cost or 0)
    price = None
    harvested = []
    if html:
        if kind in ("pdp",):
            try:
                price = extract_price_from_html(html, qname, "BHD", "sephora.me", url)
            except Exception as e:  # noqa: BLE001
                print(f"    scrapedo extract_price EXC {type(e).__name__}: {e}")
        if kind in ("harvest", "control"):
            harvested = harvest_pdp_links(html)
    outcome = classify_outcome(html, status, price, harvested)
    rec = _make_record(
        label, kind, url, status=status, cost=int(cost or 0), outcome=outcome,
        html_kb=(len(html) // 1024) if html else 0,
        detected_cf=looks_akamai_blocked(html, status), elapsed_ms=elapsed_ms,
        extracted_price=(price.get("amount") if price else None),
        harvested=harvested,
    )
    print(f"    scrapedo[{label}] status={status} cost={cost} outcome={outcome} "
          f"price={rec['extracted_price']} harvested={len(harvested)} "
          f"(credits_spent={credits_spent})")
    return rec, credits_spent


# ---------------------------------------------------------------------------
# Zyte leg (A/B) — local, no repo integration exists. browserHtml +
# geolocation:BH. ZYTE_API_KEY from LOCAL .env only; skipped if unset.
# ---------------------------------------------------------------------------
async def _zyte_render(url: str) -> Tuple[Optional[str], int]:
    """POST https://api.zyte.com/v1/extract with Basic-auth (ZYTE_API_KEY, "").
    Returns (browser_html_or_none, status). No spend metering beyond the fixed
    4-render cap the caller enforces (no clean per-request credit header)."""
    key = (os.environ.get("ZYTE_API_KEY") or "").strip()
    if not key:
        return None, 0
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.zyte.com/v1/extract",
                auth=(key, ""),
                json={"url": url, "browserHtml": True, "geolocation": "BH"},
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:  # noqa: BLE001
                    return None, 200
                return data.get("browserHtml"), 200
            return None, resp.status_code
    except Exception as e:  # noqa: BLE001
        print(f"    zyte EXC {type(e).__name__}: {e}")
        return None, 0


async def _zyte_attempt(label: str, kind: str, url: str, qname: str) -> dict:
    t0 = time.perf_counter()
    html, status = await _zyte_render(url)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    price = None
    harvested = []
    if html:
        if kind in ("pdp",):
            try:
                price = extract_price_from_html(html, qname, "BHD", "sephora.me", url)
            except Exception as e:  # noqa: BLE001
                print(f"    zyte extract_price EXC {type(e).__name__}: {e}")
        if kind in ("harvest", "control"):
            harvested = harvest_pdp_links(html)
    outcome = classify_outcome(html, status, price, harvested)
    rec = _make_record(
        label, kind, url, status=status, cost=0, outcome=outcome,
        html_kb=(len(html) // 1024) if html else 0,
        detected_cf=looks_akamai_blocked(html, status), elapsed_ms=elapsed_ms,
        extracted_price=(price.get("amount") if price else None),
        harvested=harvested,
    )
    print(f"    zyte[{label}] status={status} outcome={outcome} "
          f"price={rec['extracted_price']} harvested={len(harvested)}")
    return rec


def _make_record(label, kind, url, *, status, cost, outcome, html_kb,
                 detected_cf, elapsed_ms, extracted_price, harvested) -> dict:
    """Mirror the prod _record_provider_attempt field set (provider/url/
    retailer_domain/status/cost/outcome/html_kb/detected_cf/elapsed_ms) PLUS the
    experiment-only fields (label/kind/extracted_price/harvested_count)."""
    return {
        "provider": "scrapedo_super",
        "label": label,
        "kind": kind,
        "url": url,
        "retailer_domain": "sephora.me",
        "status": status,
        "cost": cost,
        "outcome": outcome,
        "html_kb": html_kb,
        "detected_cf": detected_cf,
        "elapsed_ms": elapsed_ms,
        "extracted_price": extracted_price,
        "harvested_count": len(harvested),
        "harvested_sample": harvested[:3],
    }


def _is_pass(rec: dict) -> bool:
    return rec.get("outcome") in ("pass_price", "pass_harvest")


def _decide_verdict(scrapedo_records: list, zyte_records: list) -> str:
    """GO_SCRAPEDO if any super attempt PASSED (200, no Akamai marker, BHD price
    OR harvestable PDPs). Else GO_ZYTE if any Zyte attempt PASSED. Else NO_GO."""
    if any(_is_pass(r) for r in scrapedo_records):
        return "GO_SCRAPEDO"
    if any(_is_pass(r) for r in zyte_records):
        return "GO_ZYTE"
    return "NO_GO"


async def main():
    print("=== sephora.me provider-test harness (OUT-OF-BAND, no prod write) ===")
    print(f"scrapedo_avail={scrapedo_service.is_available()} "
          f"super_enabled={scrapedo_service._super_enabled()} "
          f"super_params={scrapedo_service._super_params()}")
    zyte_key_present = bool((os.environ.get("ZYTE_API_KEY") or "").strip())
    print(f"zyte_key_present={zyte_key_present} "
          f"scrapedo_credit_cap={SCRAPEDO_CREDIT_CAP}")

    credits_spent = 0
    scrapedo_records = []
    print("\n--- Scrape.do super (geoCode=bh) ---")
    for label, kind, url, qname in TARGETS:
        rec, credits_spent = await _scrapedo_attempt(
            label, kind, url, qname, credits_spent)
        scrapedo_records.append(rec)

    zyte_records = []
    if zyte_key_present:
        print("\n--- Zyte browserHtml (geolocation:BH) ---")
        for label, kind, url, qname in TARGETS[:ZYTE_RENDER_CAP]:
            zyte_records.append(await _zyte_attempt(label, kind, url, qname))
    else:
        print("\n--- Zyte leg SKIPPED (ZYTE_API_KEY unset in local .env) ---")

    verdict = _decide_verdict(scrapedo_records, zyte_records)
    result = {
        "experiment": "sephora.me provider-test (Scrape.do super + Zyte)",
        "retailer_domain": "sephora.me",
        "open_question": "does residential-BH egress crack Akamai Bot Manager?",
        "verdict": verdict,
        "scrapedo_credits_spent": credits_spent,
        "scrapedo_credit_cap": SCRAPEDO_CREDIT_CAP,
        "zyte_key_present": zyte_key_present,
        "scrapedo_attempts": scrapedo_records,
        "zyte_attempts": zyte_records,
        "generated_at": int(time.time()),
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_sephora_provider_test_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n=== VERDICT: {verdict} "
          f"(scrapedo_credits_spent={credits_spent}/{SCRAPEDO_CREDIT_CAP}) ===")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

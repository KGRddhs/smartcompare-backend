"""Wave C C4 — Zyte seed variant-awareness (kpi-frag-005) + seed-script scoping.

Offline (all Zyte HTTP mocked). Pins the recon_fragrances findings (2026-07-02):
  * TRUTH-CRITICAL PDP-detail extraction: `fetch_zyte_pdp_price` renders the EXACT
    pinned PDP with Zyte `product` extraction, which returns SIZE + AVAILABILITY —
    replacing the productList path's unconditional `in_stock=True` stamp
    (zyte_service.py:416 recon caveat) with the real tri-state, and pinning the
    VARIANT (the AdG caveat: a productList match landed the 50ml default variant).
  * The Carbon entry (kpi-frag-005): sephora.me P2909014?productVariantId=374448,
    size "Eau de Toilette 100ml", InStock, raw 58500.0 → fils-fix 58.5 BHD.
  * HTTP 520 /download/website-ban is TRANSIENT (alternated with 200s on identical
    URLs in recon) → one retry, and it must NOT trip the account kill-switch.
  * Brand-as-name wobble: a productList tile named exactly the BRAND string
    ("YVES SAINT LAURENT" for the Black Opium tile) falls back to the PDP URL slug
    for identity tokens before rejecting — equality gate unchanged (a flanker or
    gift-set slug still rejects).
  * Cache-key parity: the seed entry's (brand, name, variant) derive the SAME
    size-aware cache key as the plausible live-parse shapes, so the warmed key IS
    the key a live compare / measure_warmed_kpi reads.
"""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import app.services.zyte_service as zs

CARBON_PDP = (
    "https://www.sephora.me/bh-en/p/luna-rossa-carbon-eau-de-toilette/"
    "P2909014?productVariantId=374448"
)
CARBON_QUERY = "Prada Luna Rossa Carbon Eau de Toilette 100ml"


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.setenv("ZYTE_RETRY_BACKOFF", "0")
    zs.reset_account_state()
    yield
    zs.reset_account_state()


@pytest.fixture
def seed_mod():
    """Import the seed script LAZILY (its import mutates env: ENABLE_ZYTE_RENDER /
    PRICE_RACE_TIMEOUT / ZYTE_TIMEOUT) and restore those keys afterwards so this
    module never bleeds env into other test files in the same pytest process."""
    keys = ("ENABLE_ZYTE_RENDER", "PRICE_RACE_TIMEOUT", "ZYTE_TIMEOUT")
    saved = {k: os.environ.get(k) for k in keys}
    import scripts.seed_zyte_luxury as seed
    yield seed
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _resp(status, payload=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=payload or {})
    r.text = text
    return r


def _mock_calls(responses):
    """(factory, post_mock) — httpx.AsyncClient patch whose shared post mock cycles
    `responses`; call_count proves exactly how many Zyte requests were made."""
    post = AsyncMock(side_effect=list(responses))

    def factory(*a, **k):
        client = MagicMock()
        client.post = post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    return MagicMock(side_effect=factory), post


def _pdetail(name="Luna Rossa Carbon Eau de Toilette", price="58500.0",
             availability="InStock", size="Eau de Toilette 100ml",
             brand="Prada", url=CARBON_PDP):
    """A Zyte product-DETAIL payload shaped like the captured sephora fixture
    (tests/fixtures/zyte/sephora_product_oud_wood_edp.json) + the recon-confirmed
    Carbon values (raw price 58500.0, size 'Eau de Toilette 100ml', InStock)."""
    p = {
        "name": name, "price": price, "currency": "BHD", "currencyRaw": "BHD",
        "sku": "P2909014", "url": url,
        "mainImage": {"url": "https://img-product.sephora.me/x.jpg"},
        "metadata": {"probability": 0.99},
    }
    if availability is not None:
        p["availability"] = availability
    if size is not None:
        p["size"] = size
    if brand is not None:
        p["brand"] = {"name": brand}
    return {"url": url, "statusCode": 200, "product": p}


def _plist(products):
    return {"productList": {"products": products}}


# --- the Carbon truth entry + seed-script scoping ---------------------------

def test_carbon_truth_entry_shape(seed_mod):
    entries = [e for e in seed_mod.TRUTH_CRITICAL_SEEDS
               if "carbon" in f"{e.get('brand','')} {e.get('name','')}".lower()]
    assert len(entries) == 1, "exactly one Luna Rossa Carbon truth-critical entry"
    e = entries[0]
    assert e["brand"] == "Prada"
    assert e["name"] == "Luna Rossa Carbon"
    assert e["pdp_url"] == CARBON_PDP, "pinned to the EXACT recon-confirmed PDP + variant"
    assert "productVariantId=374448" in e["pdp_url"]
    assert e["domain"] == "sephora.me"
    assert e["category"] == "fragrances"
    assert "100ml" in (e.get("variant") or ""), "variant pins the 100ml size"


def test_carbon_cache_key_parity(seed_mod):
    """The entry-derived key must equal every plausible live-parse key shape —
    warmed key == the key measure_warmed_kpi / a live compare reads."""
    from app.services.price_service import build_size_aware_price_cache_key as k
    e = [x for x in seed_mod.TRUTH_CRITICAL_SEEDS if x["name"] == "Luna Rossa Carbon"][0]
    entry_key = k(e["brand"], e["name"], e.get("variant"), e.get("region", "bahrain"),
                  seed_mod._truth_label(e))
    assert entry_key == k("Prada", "Luna Rossa Carbon", None, "bahrain", CARBON_QUERY)
    assert entry_key == k("Prada", "Luna Rossa Carbon Eau de Toilette", "100ml",
                          "bahrain", CARBON_QUERY)
    assert entry_key == k("PRADA", "Luna Rossa Carbon", None, "bahrain", CARBON_QUERY)


def test_carbon_parser_axis_presence_gap_documented(seed_mod):
    """DOCUMENTED RESIDUAL (live-observed 2026-07-02, C4 seed verification): the
    REAL GPT parse of the truth query dropped the concentration ENTIRELY
    (brand='Prada', name='Luna Rossa Carbon', variant='100ml' — 'Eau de Toilette'
    retained NOWHERE, and _get_price's search_query is REBUILT from those fields)
    — so the live-derived key carries no concentration token and CANNOT equal the
    axis-complete entry key. The builder is NOT the bug (it collapses EDT ≡
    'eau de toilette' whenever the axis is PRESENT — pinned above); this is the
    Wave-1-documented PARSER axis-presence gap, durably fixable only by
    parser/resolved-identity work (Wave-2 VariantDescriptor). Pinned as an
    INEQUALITY so any change to this behavior surfaces for review. Consequence
    observed live: the parse-shaped key held a jalilaperfumes EDP-titled price
    the KPI truth-check correctly refuses, while the correct 58.5 EDT seed lives
    at the axis-complete key."""
    from app.services.price_service import build_size_aware_price_cache_key as k
    e = [x for x in seed_mod.TRUTH_CRITICAL_SEEDS if x["name"] == "Luna Rossa Carbon"][0]
    entry_key = k(e["brand"], e["name"], e.get("variant"), "bahrain", seed_mod._truth_label(e))
    live_parse_key = k("Prada", "Luna Rossa Carbon", "100ml", "bahrain",
                       "Prada Luna Rossa Carbon 100ml")
    assert live_parse_key != entry_key, (
        "the parser axis-presence gap appears CLOSED — re-verify which key the "
        "live path now derives and re-point the truth-critical seed if needed"
    )


def test_select_targets_only_scoping(seed_mod):
    pairs = list(seed_mod.LUXURY_PAIRS)
    truth = list(seed_mod.TRUTH_CRITICAL_SEEDS)
    # default: full gold-set + all truth-critical entries
    p, t = seed_mod._select_targets([])
    assert p == pairs and t == truth
    # --only carbon: no pair mentions "carbon" -> ONLY the Carbon truth entry
    p, t = seed_mod._select_targets(["--only", "carbon"])
    assert p == []
    assert len(t) == 1 and t[0]["name"] == "Luna Rossa Carbon"
    # --only is case-insensitive substring over both lists
    p, t = seed_mod._select_targets(["--only", "LUNA"])
    assert all("luna" in x.lower() for x in p)
    assert len(t) == 1
    # explicit pair args (existing CLI) stay a PAIR-only targeted re-seed
    p, t = seed_mod._select_targets(["Dior Sauvage vs Bleu de Chanel"])
    assert p == ["Dior Sauvage vs Bleu de Chanel"]
    assert t == []
    # --only that matches nothing runs nothing (never falls back to everything)
    p, t = seed_mod._select_targets(["--only", "zzz-no-such"])
    assert p == [] and t == []


# --- variant-aware PDP-detail extraction ------------------------------------

@pytest.mark.asyncio
async def test_detail_variant_aware_extraction():
    factory, post = _mock_calls([_resp(200, _pdetail())])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is not None
    assert out["amount"] == pytest.approx(58.5), "fils-fix applied on the detail path (58500.0 -> 58.5)"
    assert out["currency"] == "BHD"
    assert out["source_method"] == "zyte_render_bhd"
    assert out["in_stock"] is True, "availability from the PDP detail, not an unconditional stamp"
    assert out["retailer"] == "sephora.me"
    assert out["url"] == CARBON_PDP, "citation stays the pinned variant-exact PDP"
    assert out["brand"] == "Prada"
    assert out.get("size") == "100ml"
    title = out["title"]
    from app.services.price_service import extract_size_ml_any, extract_concentration
    assert extract_size_ml_any(title) == 100, "title carries the confirmed size"
    assert extract_concentration(title) == "EDT"
    assert "luna rossa carbon" in title.lower()
    assert post.call_count == 1


@pytest.mark.asyncio
async def test_detail_wrong_variant_rejected():
    """The AdG caveat: the PDP's selected variant is 50ml while the query pins
    100ml -> reject (never seed the wrong variant's price)."""
    payload = _pdetail(name="Acqua di Gio Eau de Toilette", price="56500.0",
                       size="50ml", brand="Giorgio Armani")
    factory, _ = _mock_calls([_resp(200, payload)])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP,
            "Giorgio Armani Acqua di Gio Eau de Toilette 100ml", brand="Giorgio Armani",
        )
    assert out is None


@pytest.mark.asyncio
async def test_detail_size_unconfirmed_rejected():
    """Query pins a size the detail cannot confirm (no size field, no ml in the
    name) -> fail-closed for a truth-critical seed."""
    payload = _pdetail(size=None)
    factory, _ = _mock_calls([_resp(200, payload)])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is None


@pytest.mark.asyncio
async def test_detail_query_without_size_accepts():
    """Bounded relaxation check (both directions): a size-UNSTATED query accepts
    the detail and still enriches the title with the PDP's size."""
    factory, _ = _mock_calls([_resp(200, _pdetail())])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, "Prada Luna Rossa Carbon Eau de Toilette",
            brand="Prada",
        )
    assert out is not None
    from app.services.price_service import extract_size_ml_any
    assert extract_size_ml_any(out["title"]) == 100


@pytest.mark.asyncio
async def test_detail_oos_pends():
    payload = _pdetail(availability="OutOfStock")
    factory, _ = _mock_calls([_resp(200, payload)])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is None, "an OOS PDP price pends at the showable gate — never seeded"


@pytest.mark.asyncio
async def test_detail_unknown_availability_tristate():
    payload = _pdetail(availability=None)
    factory, _ = _mock_calls([_resp(200, payload)])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is not None
    assert out["in_stock"] is None, "unknown availability stays tri-state None, not a True stamp"


@pytest.mark.asyncio
async def test_detail_flanker_rejected():
    """The identity gate holds on the detail path: a flanker PDP never ships as
    the query's price."""
    payload = _pdetail(name="Luna Rossa Ocean Eau de Toilette")
    factory, _ = _mock_calls([_resp(200, payload)])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is None


@pytest.mark.asyncio
async def test_detail_flag_off_no_call(monkeypatch):
    monkeypatch.setenv("ENABLE_ZYTE_RENDER", "false")
    factory, post = _mock_calls([_resp(200, _pdetail())])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is None
    assert post.call_count == 0, "fail-closed gate: no paid render when the flag is off"


# --- HTTP 520 website-ban is transient --------------------------------------

@pytest.mark.asyncio
async def test_detail_520_retries_then_succeeds():
    """Recon: Zyte 520 /download/website-ban alternated with 200s on identical
    URLs -> one transient retry recovers the render."""
    factory, post = _mock_calls([
        _resp(520, text="/download/website-ban"),
        _resp(200, _pdetail()),
    ])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is not None and out["amount"] == pytest.approx(58.5)
    assert post.call_count == 2, "exactly one retry after the transient 520"
    assert zs._ACCOUNT_DEAD is False


@pytest.mark.asyncio
async def test_detail_520_persistent_returns_none_without_killswitch():
    factory, post = _mock_calls([
        _resp(520, text="/download/website-ban"),
        _resp(520, text="/download/website-ban"),
    ])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_pdp_price(
            "sephora.me", CARBON_PDP, CARBON_QUERY, brand="Prada",
        )
    assert out is None
    assert post.call_count == 2, "bounded attempts (ZYTE_RETRIES default 2)"
    assert zs._ACCOUNT_DEAD is False, "520 is a site ban, NOT an account-terminal 4xx"


# --- brand-as-name wobble: slug fallback ------------------------------------

@pytest.mark.parametrize("brand", ["Yves Saint Laurent", "YSL"])
@pytest.mark.asyncio
async def test_plist_brand_as_name_slug_fallback(brand):
    """The recon wobble: the Black Opium tile came back named 'YVES SAINT LAURENT'
    -> identity falls back to the PDP URL slug and the genuine listing matches."""
    tile = {
        "name": "YVES SAINT LAURENT", "price": "77000.0", "currency": "BHD",
        "url": "https://www.sephora.me/bh-en/p/black-opium-eau-de-parfum/P1920022",
        "metadata": {"probability": 0.98},
    }
    factory, _ = _mock_calls([_resp(200, _plist([tile]))])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price(
            "sephora.me", f"{brand} Black Opium Eau de Parfum", brand=brand,
        )
    assert out is not None, "brand-as-name tile must match via the URL slug"
    assert out["amount"] == pytest.approx(77.0)
    title_lc = out["title"].lower()
    assert "black opium" in title_lc, "display title derived from the slug, not the bare brand"


@pytest.mark.asyncio
async def test_plist_slug_fallback_rejects_flanker_slug():
    tile = {
        "name": "YVES SAINT LAURENT", "price": "70000.0", "currency": "BHD",
        "url": "https://www.sephora.me/bh-en/p/black-opium-over-red/P1920099",
    }
    factory, _ = _mock_calls([_resp(200, _plist([tile]))])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price(
            "sephora.me", "Yves Saint Laurent Black Opium Eau de Parfum",
            brand="Yves Saint Laurent",
        )
    assert out is None, "a flanker slug still rejects — the equality gate is unchanged"


@pytest.mark.asyncio
async def test_plist_slug_fallback_rejects_set_slug():
    tile = {
        "name": "YVES SAINT LAURENT", "price": "119000.0", "currency": "BHD",
        "url": "https://www.sephora.me/bh-en/p/black-opium-set/P1920100",
    }
    factory, _ = _mock_calls([_resp(200, _plist([tile]))])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price(
            "sephora.me", "Yves Saint Laurent Black Opium Eau de Parfum",
            brand="Yves Saint Laurent",
        )
    assert out is None, "a gift-set slug is a different sellable unit — form gate holds on the slug"


@pytest.mark.asyncio
async def test_plist_normal_tiles_unaffected_by_fallback():
    """Correct-product space (tightening re-check): a normally-named tile still
    matches exactly as before the wobble fallback landed."""
    tile = {
        "name": "Black Opium - Eau de Parfum", "price": "77000.0", "currency": "BHD",
        "url": "https://www.sephora.me/bh-en/p/black-opium-eau-de-parfum/P1920022",
        "metadata": {"probability": 0.98},
    }
    factory, _ = _mock_calls([_resp(200, _plist([tile]))])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price(
            "sephora.me", "Yves Saint Laurent Black Opium Eau de Parfum",
            brand="Yves Saint Laurent",
        )
    assert out is not None and out["amount"] == pytest.approx(77.0)
    assert out["title"] == "Black Opium - Eau de Parfum"


# --- the seeded Carbon payload counts for kpi-frag-005 ----------------------

def _carbon_price():
    return {
        "amount": 58.5, "currency": "BHD", "retailer": "sephora.me",
        "url": CARBON_PDP, "in_stock": True, "estimated": False,
        "source_method": "zyte_render_bhd",
        "title": "Luna Rossa Carbon Eau de Toilette 100ml",
        "brand": "Prada", "size": "100ml", "confidence": 0.9, "image_url": None,
    }


def test_seeded_carbon_payload_usable_for_kpi_frag_005():
    """The exact dict the seed writes must (a) pass the fail-closed write gate,
    (b) be showable, (c) get the 7d genuine TTL, and (d) COUNT as
    usable_exact_genuine for the REAL kpi-frag-005 truth row."""
    from app.services.price_service import (
        should_cache_price, is_price_showable, price_cache_ttl,
    )
    from scripts.eval_runner import (
        usable_exact_genuine_for_product, load_usable_exact_genuine_truth,
    )
    price = _carbon_price()
    assert should_cache_price(CARBON_QUERY, price, "fragrances") is True
    assert is_price_showable(CARBON_QUERY, price) is True
    assert price_cache_ttl(price) == 7 * 24 * 3600
    truth = [t for t in load_usable_exact_genuine_truth()
             if t.get("id") == "kpi-frag-005"]
    assert truth, "kpi-frag-005 must exist in data/usable_exact_genuine_truth.json"
    body = {"products": [{"price": price}]}
    assert usable_exact_genuine_for_product(body, 0, truth[0]) is True


@pytest.mark.asyncio
async def test_seed_truth_entry_writes_cache_at_parity_key(seed_mod):
    from app.services.price_service import build_size_aware_price_cache_key
    e = [x for x in seed_mod.TRUTH_CRITICAL_SEEDS if x["name"] == "Luna Rossa Carbon"][0]
    expected_key = build_size_aware_price_cache_key(
        e["brand"], e["name"], e.get("variant"), e.get("region", "bahrain"),
        seed_mod._truth_label(e),
    )
    svc = MagicMock()
    price = _carbon_price()
    with patch("app.services.zyte_service.fetch_zyte_pdp_price",
               AsyncMock(return_value=price)) as fz, \
         patch("app.services.cache_service.set_cached") as sc:
        tally = await seed_mod._seed_truth_entry(svc, e)
    assert tally == {"genuine": 1, "pending": 0}
    assert fz.await_count == 1
    (key, written, ttl), _ = sc.call_args
    assert key == expected_key, "the warmed key must be the live-parse key"
    assert written["amount"] == pytest.approx(58.5)
    assert ttl == 7 * 24 * 3600
    svc._save_price_to_db.assert_called_once()
    assert svc._save_price_to_db.call_args[0][0] == expected_key


@pytest.mark.asyncio
async def test_seed_truth_entry_write_gate_refusal_no_write(seed_mod):
    """A dict the fail-closed write gate refuses (no title -> unverifiable) is
    never cached — the seed reports it pending instead."""
    e = [x for x in seed_mod.TRUTH_CRITICAL_SEEDS if x["name"] == "Luna Rossa Carbon"][0]
    svc = MagicMock()
    bad = {k: v for k, v in _carbon_price().items() if k != "title"}
    with patch("app.services.zyte_service.fetch_zyte_pdp_price",
               AsyncMock(return_value=bad)), \
         patch("app.services.cache_service.set_cached") as sc:
        tally = await seed_mod._seed_truth_entry(svc, e)
    assert tally == {"genuine": 0, "pending": 1}
    sc.assert_not_called()
    svc._save_price_to_db.assert_not_called()


@pytest.mark.asyncio
async def test_seed_truth_entry_fetch_miss_pends(seed_mod):
    e = [x for x in seed_mod.TRUTH_CRITICAL_SEEDS if x["name"] == "Luna Rossa Carbon"][0]
    svc = MagicMock()
    with patch("app.services.zyte_service.fetch_zyte_pdp_price",
               AsyncMock(return_value=None)), \
         patch("app.services.cache_service.set_cached") as sc:
        tally = await seed_mod._seed_truth_entry(svc, e)
    assert tally == {"genuine": 0, "pending": 1}
    sc.assert_not_called()

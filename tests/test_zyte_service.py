"""Offline tests for the Zyte render-tier adapter (app/services/zyte_service.py).

HTTP mocked off the captured Zyte fixtures (tests/fixtures/zyte/). Covers the
fils-fix (BHD 3-decimal mis-parse), the OFF-CLOCK gate, strict-match no-fab
(sephora returns makeup for a "Creed Aventus" search → must reject), and the
genuine stamp.
"""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import app.services.zyte_service as zs

_FX = Path(__file__).parent / "fixtures" / "zyte"


def _load(name):
    return json.loads((_FX / f"{name}.json").read_text(encoding="utf-8"))


def _mock_zyte(payload):
    """Patch httpx.AsyncClient so its .post returns a 200 with `payload`."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.setenv("ZYTE_RETRY_BACKOFF", "0")  # no real sleeps in retry tests
    zs.reset_account_state()  # clear the per-run kill-switch (module global) each test
    yield
    zs.reset_account_state()


def _plist(products):
    """A Zyte productList payload shaped like a real sephora.me search response."""
    return {"productList": {"products": products}}


def _resp(status, payload=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=payload or {})
    r.text = text
    return r


def _mock_calls(responses):
    """(factory, post_mock) — patch httpx.AsyncClient with `factory`; post_mock's
    side_effect cycles `responses` and is shared across AsyncClient() calls so its
    call_count proves exactly how many Zyte requests were made (retries included)."""
    post = AsyncMock(side_effect=list(responses))

    def factory(*a, **k):
        client = MagicMock()
        client.post = post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    return MagicMock(side_effect=factory), post


# --- fils-fix --------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("77000.0", 77.0),   # fils form (77.000 BHD)
    (77000, 77.0),
    ("11.0", 11.0),      # already-major form
    (11000.0, 11.0),     # the inconsistent fils form
    ("0", None), (-5, None), ("garbage", None), (None, None),
])
def test_normalize_bhd_fils_fix(raw, expected):
    assert zs.normalize_bhd_amount(raw) == expected


# --- genuine BHD via sephora productList -----------------------------------

@pytest.mark.asyncio
async def test_sephora_oud_wood_genuine_bhd(monkeypatch):
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum", brand="Tom Ford")
    assert out is not None, "should match the Oud Wood EDP"
    assert out["source_method"] == "zyte_render_bhd"
    assert out["currency"] == "BHD"
    assert out["amount"] == pytest.approx(77.0), "fils-fixed from 77000"
    assert out["retailer"] == "sephora.me"
    assert "sephora.me" in out["url"]
    assert out["estimated"] is False


# --- no-fab: a wrong-brand search must NOT ship a price --------------------

@pytest.mark.asyncio
async def test_wrong_brand_search_rejected(monkeypatch):
    # sephora doesn't carry Creed — the search returns makeup. Build that shape.
    makeup = {"productList": {"products": [
        {"name": "Dior Addict - Shine Lipstick", "price": "23000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/dior-addict-shine-lipstick/P1"},
        {"name": "Easy Bake Loose Baking & Setting Powder", "price": "20000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/easy-bake/P2"},
    ]}}
    with patch("httpx.AsyncClient", _mock_zyte(makeup)):
        out = await zs.fetch_zyte_price("sephora.me", "Creed Aventus")
    assert out is None, "no Creed in the makeup results → must return None, never a wrong price"


# --- gates -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_off_clock_gate(monkeypatch):
    monkeypatch.delenv("ENABLE_ZYTE_RENDER", raising=False)  # gated OFF
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum")
    assert out is None, "gated OFF (ENABLE_ZYTE_RENDER unset) → never fires"


@pytest.mark.asyncio
async def test_no_api_key(monkeypatch):
    monkeypatch.delenv("ZYTE_API_KEY", raising=False)
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum")
    assert out is None


@pytest.mark.asyncio
async def test_unknown_domain(monkeypatch):
    with patch("httpx.AsyncClient", _mock_zyte({"productList": {"products": []}})):
        out = await zs.fetch_zyte_price("random-store.com", "Tom Ford Oud Wood")
    assert out is None


# === match-tuning (2026-06-26) ============================================

# (b) concentration precision — an UNSPECIFIED query prefers the flagship EDP
# over the pricier Parfum. Uses the REAL captured Oud Wood candidate list
# (EDP 77 / body-spray 41 / Parfum 158 / set 119).

@pytest.mark.asyncio
async def test_oud_wood_unspecified_prefers_edp_not_parfum():
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is not None
    # v1 picked the 158 Parfum (fewest-extra tiebreak); must now pick the 77 EDP.
    assert out["amount"] == pytest.approx(77.0), "unspecified query → flagship EDP, not Parfum/spray/set"


@pytest.mark.asyncio
async def test_oud_wood_explicit_edp_still_77():
    """The pre-existing explicit-concentration path is preserved."""
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(77.0)


@pytest.mark.asyncio
async def test_explicit_concentration_rejects_mismatch():
    # Query asks EDP; only a Parfum is offered → reject (never ship a wrong concentration).
    payload = _plist([
        {"name": "Oud Wood Parfum", "price": "158000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/oud-wood-parfum/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum", brand="Tom Ford")
    assert out is None


# (a) brand-aware overlap — sephora OMITS the (multi-word) brand from the title.
# v1 divided overlap by all query words incl. the brand → collapsed below 0.5.

@pytest.mark.asyncio
async def test_multiword_brand_marc_jacobs_daisy():
    payload = _plist([
        {"name": "Daisy - Eau de Toilette", "price": "29000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/daisy-edt/P1"},
        {"name": "Daisy Dream - Eau de Toilette", "price": "31000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/daisy-dream/P2"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Marc Jacobs Daisy", brand="Marc Jacobs")
    assert out is not None, "brand-aware overlap must match a brand-omitted title"
    assert out["amount"] == pytest.approx(29.0), "plain 'Daisy' beats the 'Daisy Dream' flanker"


@pytest.mark.asyncio
async def test_multiword_brand_viktor_rolf_flowerbomb():
    payload = _plist([
        {"name": "Flowerbomb - Eau de Parfum", "price": "45000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/flowerbomb/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Viktor Rolf Flowerbomb", brand="Viktor Rolf")
    assert out is not None and out["amount"] == pytest.approx(45.0)


@pytest.mark.asyncio
async def test_brand_aware_still_rejects_wrong_brand():
    """Brand-awareness must NOT loosen no-fab: a wrong-brand result still rejects."""
    payload = _plist([
        {"name": "Addict - Shine Lipstick", "price": "23000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/addict/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Creed Aventus", brand="Creed")
    assert out is None


# (c) form gate — non-bottle forms never ship as the bottle's price.

@pytest.mark.asyncio
async def test_form_gate_rejects_set_and_body_spray():
    payload = _plist([
        {"name": "Oud Wood Eau de Parfum Set", "price": "119000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/set/P1"},
        {"name": "Oud Wood - All Over Body Spray", "price": "41000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/spray/P2"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is None, "only non-bottle forms offered → pend honestly"


# (c) retry — a transient EMPTY recovers; a terminal 4xx (suspended) does NOT retry.

@pytest.mark.asyncio
async def test_empty_productlist_then_recovers():
    empty = _resp(200, {"productList": {"products": []}})
    full = _resp(200, _load("sephora_productlist_oud_wood"))
    factory, post = _mock_calls([empty, full])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(77.0)
    assert post.call_count == 2, "empty result is retried once and recovers"


@pytest.mark.asyncio
async def test_suspended_403_is_terminal_no_retry():
    factory, post = _mock_calls([_resp(403, {}, text="account-suspended")])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is None
    assert post.call_count == 1, "a 4xx (billing/suspended) is terminal — never retried"


@pytest.mark.asyncio
async def test_transient_5xx_is_retried():
    err = _resp(503, {}, text="upstream")
    full = _resp(200, _load("sephora_productlist_oud_wood"))
    factory, post = _mock_calls([err, full])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(77.0)
    assert post.call_count == 2, "5xx is transient → retried"


# === no-fab hardening (2026-06-26 adversarial review) ======================
# The hard product-identity gate must PEND (return None) rather than ship a
# flanker / near-name / base when the exact product is absent.

@pytest.mark.asyncio
async def test_flanker_only_pends():
    # The live A/B matched 'Black Opium Over Red' for 'YSL Black Opium'. With only
    # the flanker present the matcher must PEND, not ship the flanker's price.
    payload = _plist([
        {"name": "Black Opium Over Red - Eau de Parfum", "price": "57000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/black-opium-over-red/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "YSL Black Opium", brand="YSL")
    assert out is None, "a flanker with extra identity tokens must not ship as the standard"


@pytest.mark.asyncio
async def test_standard_beats_flanker_when_both_present():
    payload = _plist([
        {"name": "Black Opium Over Red - Eau de Parfum", "price": "57000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/over-red/P1"},
        {"name": "Black Opium - Eau de Parfum", "price": "51000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/black-opium/P2"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "YSL Black Opium", brand="YSL")
    assert out is not None and out["amount"] == pytest.approx(51.0), "standard bottle wins, flanker rejected"


@pytest.mark.asyncio
async def test_near_name_rejected():
    # 'Ombre Nomade' (Louis Vuitton) must NOT match 'Tom Ford Ombre Leather'.
    payload = _plist([
        {"name": "Ombre Nomade - Eau de Parfum", "price": "95000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/ombre-nomade/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Ombre Leather", brand="Tom Ford")
    assert out is None, "1-of-2-token near-name must pend, not ship"


@pytest.mark.asyncio
async def test_base_not_shipped_for_flanker_query():
    # 'Dior Homme' base must NOT be shipped for a 'Dior Homme Intense' query.
    payload = _plist([
        {"name": "Homme - Eau de Toilette", "price": "33000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/dior-homme/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Dior Homme Intense", brand="Dior")
    assert out is None, "the base ('intense' missing) must pend for an Intense query"


@pytest.mark.asyncio
async def test_wrong_brand_fragrance_list_pends():
    # The dominant real failure: search returns OTHER-BRAND fragrances (each a valid
    # bottle at a plausible price) — the identity gate is the load-bearing no-fab.
    payload = _plist([
        {"name": "Bleu de Chanel - Eau de Parfum", "price": "52000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/bleu/P1"},
        {"name": "Acqua di Gio - Eau de Toilette", "price": "44000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/adg/P2"},
        {"name": "Y - Eau de Parfum", "price": "41000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/y/P3"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Dior Sauvage", brand="Dior")
    assert out is None, "no Sauvage in a list of other-brand fragrances → pend"


@pytest.mark.asyncio
async def test_brand_repeated_in_title_still_matches():
    # sephora is inconsistent — sometimes the title KEEPS the brand. Identity must
    # still match (brand stripped from both sides).
    payload = _plist([
        {"name": "Tom Ford Oud Wood - Eau de Parfum", "price": "77000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/oud-wood/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(77.0)


@pytest.mark.asyncio
async def test_probability_breaks_identity_ties():
    # Two identity-equal, same-concentration candidates → Zyte's metadata.probability
    # is the deterministic tiebreak (not Zyte return order).
    payload = _plist([
        {"name": "Libre - Eau de Parfum", "price": "60000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/libre-a/P1", "metadata": {"probability": 0.40}},
        {"name": "Libre - Eau de Parfum", "price": "42000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/libre-b/P2", "metadata": {"probability": 0.95}},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "YSL Libre", brand="YSL")
    assert out is not None and out["amount"] == pytest.approx(42.0), "higher-probability listing wins the tie"


# --- account kill-switch (fragile-trial protection) -----------------------

@pytest.mark.asyncio
async def test_402_terminal_no_retry_and_trips_killswitch():
    factory, post = _mock_calls([_resp(402, {}, text="payment required")])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is None
    assert post.call_count == 1, "402 (billing) is terminal — never retried"
    assert zs._ACCOUNT_DEAD is True, "402 trips the per-run kill-switch"


@pytest.mark.asyncio
async def test_killswitch_stops_subsequent_calls_in_run():
    # First product 403s (suspended) → kill-switch trips; the next product must NOT
    # issue any Zyte POST (protects a 20-product seed loop from hammering a dead acct).
    factory, post = _mock_calls([_resp(403, {}, text="account-suspended")])
    with patch("httpx.AsyncClient", factory):
        out1 = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
        out2 = await zs.fetch_zyte_price("sephora.me", "YSL Black Opium", brand="YSL")
    assert out1 is None and out2 is None
    assert post.call_count == 1, "second product short-circuited by the kill-switch (no POST)"


@pytest.mark.asyncio
async def test_diacritic_folding_matches_accented_title():
    # Live-observed false pend: sephora writes "Acqua di Giò" (accented) but the query
    # is "Acqua di Gio" — without diacritic folding the identity sets differ and the
    # genuine EDT is wrongly rejected.
    payload = _plist([
        {"name": "Acqua di Giò Eau de Toilette", "price": "44000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/adg-edt/P1", "metadata": {"probability": 0.97}},
        {"name": "Acqua di Giò Profondo Eau de Parfum", "price": "46000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/profondo/P2", "metadata": {"probability": 0.95}},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Giorgio Armani Acqua di Gio", brand="Giorgio Armani")
    assert out is not None, "accented 'Giò' must fold to 'gio' and match"
    assert out["amount"] == pytest.approx(44.0), "the standard EDT, not the Profondo flanker"


@pytest.mark.asyncio
async def test_edp_edt_tie_broken_by_probability():
    # EDP and EDT are co-flagship (tie); sephora's relevance (probability) decides —
    # for an EDT-iconic brand the EDT outranks the co-listed EDP.
    payload = _plist([
        {"name": "Acqua di Gio Eau de Parfum", "price": "66000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/adg-edp/P1", "metadata": {"probability": 0.80}},
        {"name": "Acqua di Gio Eau de Toilette", "price": "44000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/adg-edt/P2", "metadata": {"probability": 0.97}},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Giorgio Armani Acqua di Gio", brand="Giorgio Armani")
    assert out is not None and out["amount"] == pytest.approx(44.0), "higher-relevance EDT wins the EDP/EDT tie"


@pytest.mark.asyncio
async def test_edp_still_beats_parfum_when_unspecified():
    # The Oud Wood fix must survive the EDP/EDT tie change: EDP ≫ Parfum.
    payload = _plist([
        {"name": "Oud Wood Parfum", "price": "158000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/parfum/P1", "metadata": {"probability": 0.97}},
        {"name": "Oud Wood - Eau de Parfum", "price": "77000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/edp/P2", "metadata": {"probability": 0.90}},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(77.0), "EDP beats Parfum even with lower probability"


@pytest.mark.asyncio
async def test_explicit_conc_query_keeps_no_concentration_title():
    # Benefit-of-doubt arm: an EXPLICIT-concentration query must still MATCH a genuine
    # candidate whose sephora title OMITS the concentration suffix (t_conc None → kept).
    payload = _plist([
        {"name": "Black Orchid", "price": "55500.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/black-orchid/P1"},
    ])
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Black Orchid Eau de Parfum", brand="Tom Ford")
    assert out is not None and out["amount"] == pytest.approx(55.5), "unstated-concentration title kept on benefit-of-doubt"


@pytest.mark.asyncio
async def test_empty_twice_pends_with_bounded_calls():
    empty = _resp(200, {"productList": {"products": []}})
    factory, post = _mock_calls([empty, empty])
    with patch("httpx.AsyncClient", factory):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood", brand="Tom Ford")
    assert out is None, "two empties → pend, never a guess"
    assert post.call_count == 2, "empty-retry budget honored (ZYTE_EMPTY_RETRIES=2), not infinite"

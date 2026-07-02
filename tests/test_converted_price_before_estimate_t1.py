"""S3-reopen T1 — a real price beats a GPT estimate (ABSOLUTE-plausibility gate).

THE #1 BUG (team-lead live): iPhone 15 vs Galaxy S24 returns source_method=
"estimated" despite a gl=us-fallback returning a REAL price. Original root cause
(scs.py:2838-2841 + 3269-3270): for a high-value query, the real Tier-1/Tier-2
price was compared to the GPT TRAINING ESTIMATE and DISCARDED/annotated when it
deviated — then the cascade fell to that same GPT estimate. A real price thrown
away for a guess.

THE FIX (team-lead Decision-F 2026-06-14, Ahmed §5: converted_usd tier-7,
estimated tier-8): the GPT estimate is the judge of NOTHING. Both sanity sites
now gate on ABSOLUTE category plausibility (is_price_plausible), not
deviation-from-guess:
  - plausible real price  -> KEEP it (return over the estimate), even if it
    differs wildly from the guess (the guess being wrong is WHY it can't judge).
  - implausible real price -> wrong-scrape; DROP it (do not promote), fall to the
    tier-8 estimate (the lesser evil).
The estimate only wins when NO plausible real price exists anywhere.

Drives _get_price end-to-end with the BH cascade stubbed empty. Free-tier (no
live calls).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def clean_service(monkeypatch):
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    # Neutralize the free genuine-BH direct-fetch selectors — electronics now
    # carries a live is_algolia sharafdg + mechanism="unbxd" extra.com source that
    # fires a REAL network fetch and returns a genuine local_bhd price BEFORE the
    # converted-parking / GPT-estimate fallthrough these tests pin.
    monkeypatch.setattr(scs_mod, "get_algolia_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_unbxd_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_shopify_sources_for_category", lambda cat: [])
    # Wave C C3 — the noon-BH literal fires a REAL fetch too; neutralize alike.
    monkeypatch.setattr(scs_mod, "get_noon_sources_for_category", lambda cat: [])
    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


@pytest.mark.asyncio
async def test_converted_us_price_returned_before_gpt_estimate(monkeypatch, clean_service):
    """A gl=us-fallback iPhone price (250 BHD converted) that DEVIATES from the
    GPT estimate (100 BHD) must STILL be returned as source_method=converted_usd
    — NOT discarded for the estimated price. The real price beats the guess."""
    from app.services import structured_comparison_service as scs_mod

    # Tier-1 shopping: gl=us fallback returns a real, plausible iPhone price from
    # a NON-official retailer (retailer_score < 1.0) so the high-value sanity
    # check at scs.py:2838 actually FIRES (an official-domain score>=1.0 would
    # skip the check entirely). 300 BHD vs the 100 BHD GPT estimate trips the
    # 2.0x high band → pre-fix the price is discarded (price=None) → estimated.
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={
            "shopping": [{
                "title": "Apple iPhone 15 128GB",
                "price": "$799.00",   # ~300 BHD converted; high-value, real
                "source": "SomeGadgetStore",   # not an official/trusted domain
                "link": "https://www.somegadgetstore.example/iphone15",
            }],
            "organic": [],
            "shopping_region": "us_fallback",
        }),
    )
    # BH Tier-1.5 discovery + fan_out: empty (the electronics gap).
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    # Tier-2 GPT organic extraction: no real price found.
    monkeypatch.setattr(scs_mod, "search_price_organic",
                        AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
    monkeypatch.setattr(scs_mod, "extract_price",
                        AsyncMock(return_value=(None, {})))
    # GPT training estimate = 100 BHD — far below the ~300 BHD real price, so the
    # high-value sanity check (2838) would discard the real price pre-fix.
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=(
            {"amount": 100.0, "currency": "BHD"}, {},
        )),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )

    assert result is not None
    # The REAL converted price wins over the GPT estimate.
    assert result["source_method"] == "converted_usd"
    assert result["source_method"] != "estimated"
    assert result.get("estimated") is not True
    # And it's the real ~300 BHD price, not the 100 BHD estimate.
    assert result["amount"] > 150


@pytest.mark.asyncio
async def test_tier2_organic_real_price_not_swapped_for_estimate(monkeypatch, clean_service):
    """T1 load-bearing fix (scs.py:3271-3276): when the Tier-2 GPT-ORGANIC
    extracted a REAL price that deviates from the GPT training estimate, the old
    code SWAPPED in the estimate (source_method=estimated). Now: keep the REAL
    extracted price with its honest label — a real cited price beats a guess
    (Ahmed: estimate is tier-8 last resort)."""
    from app.services import structured_comparison_service as scs_mod

    # No Tier-1 shopping, no BH — force the cascade into the Tier-2 organic path.
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bh"}),
    )
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(
        scs_mod, "search_price_organic",
        AsyncMock(return_value={"organic": [{"link": "https://noon.com/iphone15"}],
                                "knowledge_graph": None}),
    )
    # Tier-2 GPT organic extraction: a REAL native-BHD price (310 BHD). Use
    # original_currency=BHD so _convert_gpt_price_currency is a no-op (the test
    # isolates the swap behavior, not conversion). Deviates from the 100 estimate.
    monkeypatch.setattr(
        scs_mod, "extract_price",
        AsyncMock(return_value=(
            {"amount": 310.0, "currency": "BHD", "original_currency": "BHD",
             "retailer": "noon"},
            {},
        )),
    )
    # GPT training estimate = 100 BHD — far from the real 310 (trips the band).
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 100.0, "currency": "BHD",
                                 "original_currency": "BHD"}, {})),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    # The REAL extracted price is kept, NOT swapped for the estimate.
    assert result["source_method"] != "estimated"
    assert result.get("estimated") is not True
    assert result["amount"] == pytest.approx(310.0)
    # A genuinely-BHD extracted price WITH A REAL RETAILER stays local_bhd (cited).
    assert result["source_method"] == "local_bhd"


@pytest.mark.asyncio
async def test_tier2_organic_NO_retailer_is_not_phantom_local_bhd(monkeypatch, clean_service):
    """PHANTOM-PRICE FIX (team-lead gate-review 2026-06-14): a Tier-2 GPT-organic
    extract with NO retailer is a GUESS from search snippets, NOT a cited genuine
    BH retailer price — it must NOT be stamped local_bhd (a fabricated genuine-BH
    label violates Ahmed's no-fabrication directive). retailer=None + local_bhd
    was the red flag. Such a price carries gpt_organic_extract instead."""
    from app.services import structured_comparison_service as scs_mod

    # No Tier-1, no BH curl — force the Tier-2 GPT-organic path.
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bh"}),
    )
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(
        scs_mod, "search_price_organic",
        AsyncMock(return_value={"organic": [{"link": "https://example.com/x"}],
                                "knowledge_graph": None}),
    )
    # Tier-2 GPT extract: a price with NO retailer, BHD currency (the phantom shape).
    monkeypatch.setattr(
        scs_mod, "extract_price",
        AsyncMock(return_value=(
            {"amount": 649.95, "currency": "BHD", "original_currency": "BHD"},  # no retailer
            {},
        )),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 700.0, "currency": "BHD"}, {})),
    )

    result = await clean_service._get_price(
        brand="Some", name="Luxury Bag", variant=None, region="bahrain",
        search_query="Some Luxury Bag price", nocache=True, category="fashion",
    )
    assert result is not None
    # THE FIX: a no-retailer GPT-organic extract is NOT a phantom local_bhd.
    assert result.get("source_method") != "local_bhd", (
        f"phantom: a retailer-less GPT-organic extract stamped local_bhd "
        f"(fabricated genuine-BH). Got: {result}"
    )
    assert result.get("source_method") != "converted_usd"
    # It carries the honest gpt_organic_extract label (a guess, not a cited price).
    assert result.get("source_method") == "gpt_organic_extract"


@pytest.mark.asyncio
async def test_tier2_implausible_price_dropped_not_promoted(monkeypatch, clean_service):
    """T1 refinement (team-lead Decision-F): a Tier-2 organic price that is
    grossly IMPLAUSIBLE for the category (iPhone @ 5 BHD — a mis-extracted cable
    / accessory / wrong line item) is a WRONG SCRAPE. It must be DROPPED, NOT
    promoted as the price. The cascade then falls to the tier-8 estimate (the
    lesser evil) — surfacing a 5-BHD iPhone is as bad as a fake estimate."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bh"}),
    )
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(
        scs_mod, "search_price_organic",
        AsyncMock(return_value={"organic": [{"link": "https://noon.com/iphone-cable"}],
                                "knowledge_graph": None}),
    )
    # Tier-2 GPT organic extraction: a 5 BHD "iPhone 15" price — implausible for
    # electronics (below 0.1 x budget breakpoint 100 = 10). A wrong scrape.
    monkeypatch.setattr(
        scs_mod, "extract_price",
        AsyncMock(return_value=(
            {"amount": 5.0, "currency": "BHD", "original_currency": "BHD",
             "retailer": "noon"},
            {},
        )),
    )
    # GPT training estimate = 290 BHD (the legit tier-8 fallback).
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 290.0, "currency": "BHD"}, {})),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    # The implausible 5-BHD scrape was DROPPED, not returned.
    assert result["amount"] != pytest.approx(5.0)
    # It fell to the tier-8 estimate (the honest last resort).
    assert result["source_method"] == "estimated"
    assert result["estimated"] is True
    assert result["amount"] == pytest.approx(290.0)


@pytest.mark.asyncio
async def test_estimate_still_used_when_no_real_price_anywhere(monkeypatch, clean_service):
    """Control: when NO real price exists (no shopping, no BH, no organic), the
    GPT estimate IS the answer (tier-8 last resort still works)."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bh"}),
    )
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(scs_mod, "search_price_organic",
                        AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
    monkeypatch.setattr(scs_mod, "extract_price", AsyncMock(return_value=(None, {})))
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 290.0, "currency": "BHD"}, {})),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    assert result["source_method"] == "estimated"
    assert result["estimated"] is True

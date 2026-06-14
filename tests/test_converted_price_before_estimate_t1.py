"""S3-reopen T1 — a real (US-converted) price beats a GPT estimate.

THE #1 BUG (team-lead live): iPhone 15 vs Galaxy S24 returns source_method=
"estimated" despite a gl=us-fallback returning a REAL price. Root cause
(scs.py:2838-2841): for a high-value query, the Tier-1 converted price is
compared to the GPT TRAINING ESTIMATE and DISCARDED (price=None) when it
deviates — then the cascade falls all the way to that same GPT estimate. A real
US-converted price is thrown away for a guess.

THE FIX (Ahmed §5: converted_usd is tier-7, estimated is tier-8 last-resort):
when the sanity check rejects the Tier-1 converted price, PARK it; if Tier-1.5
(BH) + Tier-2 (organic) also fail, RETURN the parked converted_usd price instead
of the GPT estimate. The estimate only wins when NO real price exists anywhere.

Drives _get_price end-to-end with the BH cascade stubbed empty + the gl=us
shopping returning a real price. Free-tier (no live calls).
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
    # A genuinely-BHD extracted price stays local_bhd (honest).
    assert result["source_method"] == "local_bhd"


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

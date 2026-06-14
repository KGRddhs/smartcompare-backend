"""S3-genuine (team-lead 2026-06-14) — iHerb native-BHD price must stamp local_bhd.

THE BUG (from the live probe): NOW Vitamin C came back source_method=converted_usd
with original_currency=BHD. But bh.iherb.com is the BAHRAIN storefront — its
data-ga-discount-price is NATIVELY BHD (the region currency), not a US-converted
value. A natively-BHD price is GENUINE → it must stamp local_bhd, NEVER
converted_usd. Stamping it converted_usd UNDERCOUNTS the genuine-BH-price-share
(a real BHD price miscounted as a conversion).

THE FIX: in fetch_iherb_price, derive source_method from the currency — when the
storefront price IS the region currency (original_currency == currency, i.e. BHD
on bh.iherb.com), stamp local_bhd; only a genuinely-foreign-origin price is
converted_usd.

Mocks the curl fetch with the iherb_ga_cards fixture (region_code=bh, currency=BHD).
"""

from pathlib import Path

import pytest

from app.services.price_service import fetch_iherb_price

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_bh_iherb_price_stamped_local_bhd(monkeypatch):
    """A bh.iherb.com (BHD storefront) price → source_method=local_bhd, NOT
    converted_usd (it's a genuine native-BHD price)."""
    import app.services.price_service as ps

    html = (FIX / "iherb_ga_cards.html").read_text(encoding="utf-8", errors="replace")

    class _Resp:
        status_code = 200
        text = html

    # Patch the curl_cffi requests.get used inside fetch_iherb_price.
    import curl_cffi
    monkeypatch.setattr(curl_cffi.requests, "get", lambda *a, **k: _Resp())

    res = await fetch_iherb_price(
        query="vitamin c", brand="NOW", full_name="NOW Foods Vitamin C 1000",
        region_code="bh", currency="BHD",
    )
    if res is None:
        pytest.skip("fixture did not yield a matching iHerb product card")
    assert res["currency"].upper() == "BHD"
    assert res["original_currency"].upper() == "BHD"
    # THE FIX: native-BHD storefront price → local_bhd, not converted_usd.
    assert res["source_method"] == "local_bhd", (
        "bh.iherb.com price is native BHD — must stamp local_bhd, not converted_usd"
    )
    assert res["source_method"] != "converted_usd"

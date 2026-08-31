"""M13-39 — the unknown-currency 1.0 stamp is killed at its source.

exchange_rate_service._fallback_rate returned 1.0 for an unknown currency — the
implicit 1:1 stamp the whole currency wave exists to eliminate — and get_rate has
ZERO production callers. CHOICE (justified): rather than DELETE the
get_rate/_fetch_rates/_lookup_rate/_fallback_rate cluster (two live test files
import it, so deletion would create NEW import failures) and rather than rewire
_convert_to_bhd to the live table (get_rate is dead and M13-38 made the hardcoded
table authoritative), replace the 1.0 branch with None at its source
(_fallback_rate) and propagate None through get_rate. The production converter
(_convert_to_bhd via _convert_gpt_price_currency) already pends an unknown
currency under strict-label; this test pins BOTH: the dead path yields None and
the production path pends — never a 1.0 stamp.
"""
import pytest

from app.services import price_service as ps
from app.services.exchange_rate_service import _fallback_rate, get_rate


def test_m13_39_fallback_rate_unknown_is_none():
    """The 1.0 stamp is gone: an unknown currency yields None."""
    assert _fallback_rate("XYZ", "BHD") is None
    assert _fallback_rate("USD", "XYZ") is None
    assert _fallback_rate("XYZ", "QQQ") is None


def test_m13_39_fallback_rate_known_pair_still_converts():
    """A known pair still converts (regression guard) and same-currency is 1.0."""
    assert _fallback_rate("USD", "USD") == 1.0
    assert _fallback_rate("EUR", "BHD") == pytest.approx(0.41, rel=0.001)


@pytest.mark.asyncio
async def test_m13_39_get_rate_unknown_is_none(monkeypatch):
    """get_rate surfaces None for an unknown pair (no live table, no cache)."""
    monkeypatch.setattr(
        "app.services.exchange_rate_service._redis_get", lambda *a, **k: None
    )

    async def _no_rates():
        return None

    monkeypatch.setattr("app.services.exchange_rate_service._fetch_rates", _no_rates)
    assert await get_rate("XYZ", "BHD") is None
    # A known pair still resolves.
    assert await get_rate("USD", "USD") == 1.0


def test_m13_39_production_unknown_currency_pends_never_stamps():
    """The production converter pends an unknown currency (returns False), never
    stamping a 1.0-rate BHD number — even with the extended table on."""
    import os
    os.environ["ENABLE_EXTENDED_FALLBACK_RATES"] = "true"
    try:
        price = {"amount": 100.0, "original_currency": "XYZ", "currency": "XYZ"}
        assert ps._convert_gpt_price_currency(price, "BHD") is False
        assert price["amount"] == 100.0  # never converted at an implicit 1.0
        assert price["currency"] == "XYZ"  # never relabelled BHD
    finally:
        os.environ.pop("ENABLE_EXTENDED_FALLBACK_RATES", None)

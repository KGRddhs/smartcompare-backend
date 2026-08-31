"""M13-38 — widen FALLBACK_RATES to the corpus currencies (ENABLE_EXTENDED_FALLBACK_RATES).

ENABLE_RSC_FLIGHT_PRICE is a dead rung because its measured TRY cohort pends: TRY
is absent from the 13-currency FALLBACK_RATES, so a TRY page returns None. The fix
widens the effective table with the currencies the _proof corpus carries (TRY,
PLN, CAD, JOD, SEK, DKK, CHF, EGP, …) behind a DEFAULT-OFF flag — off it is the
base 13 (byte-identical, so a TRY corpus page still pends and flag-OFF
extract_price_from_html is unchanged); on, a TRY page converts.
"""
from app.services import price_service as ps
from app.services.exchange_rate_service import (
    FALLBACK_RATES,
    effective_fallback_rates,
)


def test_m13_38_effective_table_is_base_when_flag_off(monkeypatch):
    """Flag OFF: the effective table IS FALLBACK_RATES (byte-identical), so TRY is
    still absent and nothing that pended before now converts."""
    monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "false")
    assert effective_fallback_rates() == FALLBACK_RATES
    assert "TRY" not in effective_fallback_rates()


def test_m13_38_effective_table_widens_when_flag_on(monkeypatch):
    """Flag ON: the corpus currencies are present; the base table is never mutated."""
    monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "true")
    eff = effective_fallback_rates()
    for cur in ("TRY", "PLN", "CAD", "JOD", "SEK", "DKK", "CHF", "EGP"):
        assert cur in eff, cur
    assert "TRY" not in FALLBACK_RATES  # base table untouched


def test_m13_38_try_page_pends_off_converts_on(monkeypatch):
    """Pin: a TRY price pends under the shipped default (flag OFF) and CONVERTS
    once the extension is on — the RSC rung's cohort stops being dead."""
    monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "false")
    off = {"amount": 5050.0, "original_currency": "TRY", "currency": "TRY"}
    assert ps._convert_gpt_price_currency(off, "BHD") is False  # pend
    assert off["amount"] == 5050.0  # untouched
    assert ps._convert_to_bhd(5050.0, "TRY") == 5050.0  # unchanged (no rate)

    monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "true")
    on = {"amount": 5050.0, "original_currency": "TRY", "currency": "TRY"}
    assert ps._convert_gpt_price_currency(on, "BHD") is True  # converts
    assert on["currency"] == "BHD"
    assert on["amount"] == round(5050.0 * 0.0094, 2)  # 47.47
    assert ps._normalize_currency_code("TRY") == "TRY"

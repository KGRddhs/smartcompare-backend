"""M13-09 — Serper-shopping strict currency guard (ENABLE_SHOPPING_STRICT_CURRENCY).

The one price tier the BLOCKER-4 wave never covered. ``detect_currency`` reads
neither GCC glyphs nor the R$ collision, so a GCC display token ("1,399 د.إ")
or a Brazilian-real "R$ 1.399" is stamped with the target currency. Flag ON:
pend such a candidate. Flag OFF: byte-identical (the whole guard is skipped).

Runs against ``price_service.extract_price_from_shopping`` with
ENABLE_EXACT_PRICE_GATE=false to isolate extraction (no network). A single-item
result of None means the candidate PENDED.
"""
from app.services import price_service as ps


def _run(price_str):
    item = {
        "title": "Acme Widget Deluxe",
        "price": price_str,
        "source": "noon.com",
        "link": "https://noon.com/p",
    }
    r = ps.extract_price_from_shopping(
        "Acme Widget Deluxe", [item], "BHD", shopping_region="bahrain",
    )
    return None if r is None else (r["amount"], r["currency"], r["source_method"])


def test_m13_09_gcc_glyph_pends_on_flag(monkeypatch):
    """A GCC glyph amount ("1,399 د.إ") pends under the flag instead of shipping
    1399 BHD (9.8x over) labelled genuine."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "false")
    off = _run("1,399 د.إ")
    # Flag OFF is the (buggy) legacy: raw 1399 stamped BHD local_bhd.
    assert off == (1399.0, "BHD", "local_bhd"), off
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "true")
    assert _run("1,399 د.إ") is None


def test_m13_09_reais_collision_pends_on_flag(monkeypatch):
    """The "$" in "R$" collision: detect_currency reads BRL as USD. Flag ON pends
    instead of converting 1399 BRL as if it were 1399 USD."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "false")
    off = _run("R$ 1.399")
    # Flag OFF: 1399 wrongly converted from USD (1399 * 0.376 = 526.02).
    assert off is not None and off[0] == 526.02, off
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "true")
    assert _run("R$ 1.399") is None


def test_m13_09_iso_aed_never_ships_target_raw(monkeypatch):
    """Pin: AED 1,399 is never 1399 BHD — it converts to ~143.3 (both modes)."""
    for flag in ("false", "true"):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", flag)
        r = _run("AED 1,399")
        assert r is not None, flag
        assert r[0] == 143.26, (flag, r)  # 1399 * 0.1024
        assert abs(r[0] - 1399.0) > 100, (flag, r)


def test_m13_09_genuine_target_and_western_symbol_unaffected(monkeypatch):
    """No over-pend: a genuine BHD price and a €-symbol price (which
    detect_currency already resolves) are unchanged under the flag."""
    for flag in ("false", "true"):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", flag)
        assert _run("BHD 12.500") == (12.5, "BHD", "local_bhd"), flag
        eur = _run("€ 73,39")
        assert eur is not None and eur[0] == 30.09, (flag, eur)  # 73.39 * 0.41


def _run_ask(price_str, ask, region):
    item = {
        "title": "Acme Widget Deluxe",
        "price": price_str,
        "source": "noon.com",
        "link": "https://noon.com/p",
    }
    r = ps.extract_price_from_shopping(
        "Acme Widget Deluxe", [item], ask, shopping_region=region,
    )
    return None if r is None else (r["amount"], r["currency"], r["source_method"])


def test_m13_09_target_currency_glyph_is_not_over_pended(monkeypatch):
    """Dispatcher-gate regression (M13-09 over-rejection).

    A price written in the TARGET currency's own Arabic glyph is GENUINE and must
    ship, not pend: "250 ر.س" on a SAR ask, "1,399 د.إ" on an AED ask. The
    separator-stripped residue ("رس"/"دإ") misses the dotted GCC keys, so the
    original guard fell through to the non-ASCII catch-all and pended a correct
    target-currency price. The strict guard must be a NO-OP for a target-currency
    glyph: flag ON == flag OFF, amount preserved."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    for ask, region, price, want in (
        ("SAR", "saudi_arabia", "250 ر.س", (250.0, "SAR", "local_bhd")),
        ("AED", "uae", "1,399 د.إ", (1399.0, "AED", "local_bhd")),
    ):
        monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "false")
        off = _run_ask(price, ask, region)
        monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "true")
        on = _run_ask(price, ask, region)
        assert off == want, (ask, off)
        assert on == want, (ask, on)   # NOT pended — genuine amount preserved
        assert on == off               # strict guard is a no-op on a target glyph


def test_m13_09_foreign_glyph_still_pends_after_over_pend_fix(monkeypatch):
    """The over-rejection fix must NOT weaken the genuine foreign-pend: an AED
    glyph on a BHD ask is a NON-target currency and still pends under the flag
    (OFF ships the buggy 1399 BHD 9.8x-over, ON pends)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "false")
    assert _run_ask("1,399 د.إ", "BHD", "bahrain") == (1399.0, "BHD", "local_bhd")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "true")
    assert _run_ask("1,399 د.إ", "BHD", "bahrain") is None

"""M13-40 — a well-formed JSON-LD PDP in a non-target, non-USD currency must be
CAPTURED (converted + relabelled converted_usd), not pushed off the channel.

Runs against ``price_service.extract_price_from_html`` (no network). The gate is
ENABLE_JSONLD_FIRST: ON = the third foreign-currency pass; OFF = the legacy
two-pass (target + USD) behaviour, where a EUR/SAR/AED-only PDP yields no
JSON-LD price at all.
"""
from app.services import price_service as ps

# A single JSON-LD Offer denominated in EUR — neither the BHD ask nor USD, so
# the legacy target+USD passes both find nothing.
_EUR_PDP = (
    '<html><head>'
    '<title>Armaf Club de Nuit Intense Man EDT 105ml</title>'
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org","@type":"Product",'
    '"name":"Armaf Club de Nuit Intense Man EDT 105ml",'
    '"brand":{"@type":"Brand","name":"Armaf"},'
    '"offers":{"@type":"Offer","price":"45.00","priceCurrency":"EUR",'
    '"availability":"https://schema.org/InStock"}}'
    '</script></head><body></body></html>'
)

_QUERY = "Armaf Club de Nuit Intense Man 105ml"


def _extract():
    return ps.extract_price_from_html(
        _EUR_PDP, _QUERY, "BHD", "someforeignstore.de",
        "https://someforeignstore.de/p",
    )


def test_m13_40_flag_off_foreign_offer_yields_no_jsonld_price(monkeypatch):
    """Flag OFF (both gate modes): the legacy behaviour — a foreign-currency-only
    JSON-LD PDP returns no price (the failure the fix repairs). Byte-identity."""
    for gate in ("false", "true"):
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "false")
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
        assert _extract() is None, gate


def test_m13_40_flag_on_captures_and_converts_foreign_offer(monkeypatch):
    """Flag ON: the EUR Offer is captured, converted to BHD, and labelled
    converted_usd — the same machinery the sibling branches use."""
    for gate in ("false", "true"):
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
        r = _extract()
        assert r is not None, gate
        # 45.00 EUR * 0.41 (FALLBACK_RATES[EUR]) = 18.45 BHD.
        assert r["amount"] == 18.45, (gate, r)
        assert r["currency"] == "BHD", (gate, r)
        assert r["original_currency"] == "EUR", (gate, r)
        assert r["source_method"] == "converted_usd", (gate, r)

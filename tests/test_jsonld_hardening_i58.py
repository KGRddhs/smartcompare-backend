"""I5.8 — JSON-LD parser hardening (defensive, dossier section 4 item 10):
list-valued @type + AggregateOffer.lowPrice."""
import json
from app.services.price_service import extract_jsonld_price


def _html(payload):
    return f'<html><script type="application/ld+json">{json.dumps(payload)}</script></html>'


def test_list_valued_type_parses():
    html = _html({"@type": ["Product", "IndividualProduct"], "name": "Acme Widget",
                  "offers": {"price": "9.90", "priceCurrency": "BHD"}})
    out = extract_jsonld_price(html, "Acme", "BHD")
    assert out and out["amount"] == 9.9


def test_aggregate_offer_lowprice_parses():
    html = _html({"@type": "Product", "name": "Acme Widget",
                  "offers": {"@type": "AggregateOffer", "lowPrice": "7.50",
                             "highPrice": "9.00", "priceCurrency": "BHD"}})
    out = extract_jsonld_price(html, "Acme", "BHD")
    assert out and out["amount"] == 7.5


def test_plain_product_unchanged():
    html = _html({"@type": "Product", "name": "Acme Widget",
                  "offers": {"price": "5.00", "priceCurrency": "BHD"}})
    out = extract_jsonld_price(html, "Acme", "BHD")
    assert out and out["amount"] == 5.0 and out["in_stock"] is True

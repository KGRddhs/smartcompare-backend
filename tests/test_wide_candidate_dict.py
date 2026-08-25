"""Widen the JSON-LD candidate dict - ``ENABLE_WIDE_CANDIDATE``.

``extract_jsonld_price`` already parses the WHOLE schema.org Product node to
reach ``offers[].price``, then throws all of it away except five keys
(``amount``/``currency``/``in_stock``/``name``/``brand``). Everything else on
that node is therefore free: it costs zero extra fetches, zero extra parses and
zero extra latency to carry it.

Measured availability on the Product node across the 86 cached fragrance PDPs
that map to a target row (``_proof/html/`` + ``_proof/sweep2_curl_cffi.jsonl``):
description 73.3%, image 79.1%, sku 68.6%, brand 55.8%, gtin-or-mpn 36.0%,
category 22.1%, aggregateRating 14.0%, reviewBody 9.3%.

THE CONVENTION, pinned by ``test_absent_fields_are_absent_never_none``: a field
that is absent, empty, whitespace-only or unparseable is **omitted from the
dict entirely**. No key is ever present carrying ``None`` / ``""`` / ``[]``, so
a downstream ``if "sku" in cand`` stays honest and never has to also test the
value.

THE TRAP, pinned by ``test_organization_aggregate_rating_is_never_carried``:
``fyzara.com`` and ``capitalstoreoman.com`` both ship an ``aggregateRating``
attached to an ``@type: Organization`` node that sits in the SAME document as
the Product - it is the STORE rating (fyzara 4.9 from 1100 ratings,
capitalstoreoman 4.6 from 10 reviews), not the product one. Only the Product
node's own ``aggregateRating`` may be carried.

THE INVARIANT, pinned by the selection tests at the bottom: this dict is
consumed by ``select_best`` -> ``_selection_match``. Adding keys must not
change which candidate wins, in either flag state.

Flag ``ENABLE_WIDE_CANDIDATE``, default ON, read per call from ``os.getenv``.
Flag OFF => the dict has exactly the five keys it has today.

No network. Synthetic minimal JSON-LD only (shapes copied from the real cached
pages named above).
"""

import json

import pytest

from app.services.price_service import (
    _WIDE_CANDIDATE_MAX_REVIEWS,
    _WIDE_CANDIDATE_MAX_REVIEW_CHARS,
    extract_jsonld_price,
    extract_price_from_html,
    select_best,
    wide_candidate_enabled,
)

QUERY = "Oud Elite So Black Eau de Parfum 100ml"
BRAND = "Oud Elite"
CURRENCY = "BHD"
CATEGORY = "fragrances"
DOMAIN = "bh.oudelite.com"
URL = "https://bh.oudelite.com/product/so-black"

LEGACY_KEYS = {"amount", "currency", "in_stock", "name", "brand"}


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _product(**overrides):
    """A minimal, matching schema.org Product node."""
    node = {
        "@type": "Product",
        "name": QUERY,
        "brand": {"@type": "Brand", "name": BRAND},
        "offers": {
            "@type": "Offer",
            "price": "79.99",
            "priceCurrency": CURRENCY,
            "availability": "https://schema.org/InStock",
        },
    }
    node.update(overrides)
    return node


def _html(*nodes):
    blocks = "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(n)
        for n in nodes
    )
    return "<html><head>%s</head><body></body></html>" % blocks


def _cand(*nodes, brand=BRAND, currency=CURRENCY, query=QUERY, category=CATEGORY):
    return extract_jsonld_price(
        _html(*nodes), brand, currency, query_name=query, category=category,
    )


# ---------------------------------------------------------------------------
# Flag OFF - exactly today's five keys
# ---------------------------------------------------------------------------

def test_flag_off_dict_has_exactly_the_five_legacy_keys(flag_off):
    cand = _cand(_product(
        description="A dark oud.", image="https://cdn/x.jpg", sku="SB-100",
        gtin13="0123456789012", mpn="MPN-1", category="Fragrance",
        aggregateRating={"@type": "AggregateRating", "ratingValue": "4.5",
                         "reviewCount": "12"},
        review=[{"@type": "Review", "reviewBody": "Lovely."}],
    ))
    assert cand is not None
    assert set(cand) == LEGACY_KEYS
    assert cand["amount"] == 79.99


def test_flag_off_with_exact_gate_off_keeps_the_legacy_four(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    cand = _cand(_product(description="A dark oud.", sku="SB-100"))
    assert cand is not None
    assert set(cand) == {"amount", "currency", "in_stock", "name"}


def test_flag_helper_default_is_on(monkeypatch):
    monkeypatch.delenv("ENABLE_WIDE_CANDIDATE", raising=False)
    assert wide_candidate_enabled() is True
    for off in ("false", "0", "no", "off", "", "  FALSE  "):
        monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", off)
        assert wide_candidate_enabled() is False


# ---------------------------------------------------------------------------
# The absent-is-absent convention
# ---------------------------------------------------------------------------

def test_absent_fields_are_absent_never_none(flag_on):
    """A bare Product carries NO wide key at all - not one present-and-None."""
    cand = _cand(_product())
    assert cand is not None
    assert set(cand) == LEGACY_KEYS
    for key in ("description", "image", "sku", "gtin", "mpn", "category",
                "aggregate_rating", "reviews"):
        assert key not in cand
    assert None not in cand.values()


@pytest.mark.parametrize("empty", ["", "   ", None, [], {}])
def test_empty_scalars_are_omitted(flag_on, empty):
    cand = _cand(_product(description=empty, sku=empty, mpn=empty, category=empty))
    assert "description" not in cand
    assert "sku" not in cand
    assert "mpn" not in cand
    assert "category" not in cand


# ---------------------------------------------------------------------------
# Scalar text fields
# ---------------------------------------------------------------------------

def test_description_sku_category_carried(flag_on):
    cand = _cand(_product(
        description="  A dark oud with leather.  ", sku="SB-100",
        category="Fragrance > Oriental",
    ))
    assert cand["description"] == "A dark oud with leather."
    assert cand["sku"] == "SB-100"
    assert cand["category"] == "Fragrance > Oriental"


def test_category_as_a_thing_node_reads_its_name(flag_on):
    cand = _cand(_product(category={"@type": "Thing", "name": "Fragrance"}))
    assert cand["category"] == "Fragrance"


def test_numeric_sku_is_stringified(flag_on):
    cand = _cand(_product(sku=100234))
    assert cand["sku"] == "100234"


# ---------------------------------------------------------------------------
# image - schema.org allows a string, a list, or an ImageObject
# ---------------------------------------------------------------------------

def test_image_string_becomes_a_one_element_list(flag_on):
    cand = _cand(_product(image="https://cdn.example/a.jpg"))
    assert cand["image"] == ["https://cdn.example/a.jpg"]


def test_image_list_of_strings(flag_on):
    cand = _cand(_product(image=["https://cdn/a.jpg", "https://cdn/b.jpg"]))
    assert cand["image"] == ["https://cdn/a.jpg", "https://cdn/b.jpg"]


def test_image_object_reads_url(flag_on):
    cand = _cand(_product(image={"@type": "ImageObject", "url": "https://cdn/a.jpg"}))
    assert cand["image"] == ["https://cdn/a.jpg"]


def test_image_object_falls_back_to_contenturl(flag_on):
    cand = _cand(_product(
        image={"@type": "ImageObject", "contentUrl": "https://cdn/c.jpg"}))
    assert cand["image"] == ["https://cdn/c.jpg"]


def test_image_mixed_list_and_dedupe_preserving_order(flag_on):
    cand = _cand(_product(image=[
        "https://cdn/a.jpg",
        {"@type": "ImageObject", "url": "https://cdn/b.jpg"},
        "https://cdn/a.jpg",
        {"@type": "ImageObject"},          # no url at all -> dropped
        "   ",                              # blank -> dropped
    ]))
    assert cand["image"] == ["https://cdn/a.jpg", "https://cdn/b.jpg"]


def test_image_with_no_usable_url_is_omitted(flag_on):
    cand = _cand(_product(image=[{"@type": "ImageObject"}, "  "]))
    assert "image" not in cand


# ---------------------------------------------------------------------------
# gtin family -> ONE "gtin" key, mpn stays separate
# ---------------------------------------------------------------------------

def test_gtin13_preferred_over_the_rest(flag_on):
    cand = _cand(_product(gtin13="0123456789012", gtin12="012345678901",
                          gtin8="01234567", gtin="GTIN-PLAIN"))
    assert cand["gtin"] == "0123456789012"


@pytest.mark.parametrize("field,value", [
    ("gtin12", "012345678901"),
    ("gtin8", "01234567"),
    ("gtin", "09501101530003"),
])
def test_each_gtin_flavour_normalises_into_gtin(flag_on, field, value):
    cand = _cand(_product(**{field: value}))
    assert cand["gtin"] == value


def test_mpn_is_a_separate_key_and_never_folded_into_gtin(flag_on):
    cand = _cand(_product(mpn="MTP-B140D-1AV"))
    assert cand["mpn"] == "MTP-B140D-1AV"
    assert "gtin" not in cand


def test_gtin_and_mpn_coexist(flag_on):
    cand = _cand(_product(gtin13="0123456789012", mpn="MPN-1"))
    assert cand["gtin"] == "0123456789012"
    assert cand["mpn"] == "MPN-1"


# ---------------------------------------------------------------------------
# aggregateRating - THE Organization trap
# ---------------------------------------------------------------------------

def test_product_aggregate_rating_is_carried(flag_on):
    cand = _cand(_product(aggregateRating={
        "@type": "AggregateRating", "ratingValue": "4.5", "reviewCount": "12"}))
    assert cand["aggregate_rating"] == {"rating_value": 4.5, "review_count": 12}


def test_rating_count_is_accepted_when_review_count_is_absent(flag_on):
    cand = _cand(_product(aggregateRating={
        "@type": "AggregateRating", "ratingValue": 4.9, "ratingCount": "1100"}))
    assert cand["aggregate_rating"] == {"rating_value": 4.9, "review_count": 1100}


def test_review_count_wins_when_both_present(flag_on):
    cand = _cand(_product(aggregateRating={
        "ratingValue": "4.0", "reviewCount": "7", "ratingCount": "999"}))
    assert cand["aggregate_rating"]["review_count"] == 7


def test_rating_without_a_count_carries_only_the_value(flag_on):
    cand = _cand(_product(aggregateRating={"ratingValue": "4.2"}))
    assert cand["aggregate_rating"] == {"rating_value": 4.2}


@pytest.mark.parametrize("bad", [
    {"ratingValue": "n/a"}, {"ratingValue": ""}, {"ratingValue": 0},
    {"reviewCount": "12"}, "4.5", [], None,
])
def test_unparseable_aggregate_rating_is_omitted(flag_on, bad):
    cand = _cand(_product(aggregateRating=bad))
    assert "aggregate_rating" not in cand


@pytest.mark.parametrize("store_type", ["Organization", "LocalBusiness", "Store"])
def test_organization_aggregate_rating_is_never_carried(flag_on, store_type):
    """The fyzara.com / capitalstoreoman.com shape: a STORE rating node sitting
    beside the Product in the same document. Shipping it as the rating of the
    product is the documented trap."""
    store = {
        "@type": store_type,
        "name": "Fyzara",
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.9",
                            "bestRating": "5", "ratingCount": "1100"},
    }
    cand = _cand(_product(), store)
    assert "aggregate_rating" not in cand


def test_store_rating_in_a_graph_does_not_leak_onto_the_product(flag_on):
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "Capital Store",
         "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.6",
                             "reviewCount": "10"}},
        _product(),
    ]}
    cand = _cand(graph)
    assert cand is not None
    assert "aggregate_rating" not in cand


def test_the_own_product_rating_still_wins_beside_a_store_rating(flag_on):
    store = {"@type": "Organization", "name": "Fyzara",
             "aggregateRating": {"ratingValue": "4.9", "ratingCount": "1100"}}
    cand = _cand(_product(aggregateRating={"ratingValue": "3.1",
                                           "reviewCount": "4"}), store)
    assert cand["aggregate_rating"] == {"rating_value": 3.1, "review_count": 4}


# ---------------------------------------------------------------------------
# review[] bodies
# ---------------------------------------------------------------------------

def test_review_bodies_are_carried(flag_on):
    cand = _cand(_product(review=[
        {"@type": "Review", "reviewBody": "Lovely and long lasting."},
        {"@type": "Review", "reviewBody": "  Too sweet for me.  "},
    ]))
    assert cand["reviews"] == ["Lovely and long lasting.", "Too sweet for me."]


def test_a_single_review_dict_is_accepted(flag_on):
    cand = _cand(_product(review={"@type": "Review", "reviewBody": "Great."}))
    assert cand["reviews"] == ["Great."]


def test_reviews_without_a_body_are_dropped(flag_on):
    cand = _cand(_product(review=[
        {"@type": "Review", "author": "A"},          # no body
        {"@type": "Review", "reviewBody": "   "},    # blank body
        "a bare string",                             # not a node
        {"@type": "Review", "reviewBody": "Real."},
    ]))
    assert cand["reviews"] == ["Real."]


def test_reviews_omitted_entirely_when_none_usable(flag_on):
    cand = _cand(_product(review=[{"@type": "Review", "author": "A"}]))
    assert "reviews" not in cand


def test_review_count_is_capped(flag_on):
    cand = _cand(_product(review=[
        {"@type": "Review", "reviewBody": "body %d" % i} for i in range(200)
    ]))
    assert len(cand["reviews"]) == _WIDE_CANDIDATE_MAX_REVIEWS
    assert cand["reviews"][0] == "body 0"


def test_each_review_body_is_length_capped(flag_on):
    huge = "x" * 10000
    cand = _cand(_product(review=[{"@type": "Review", "reviewBody": huge}]))
    assert len(cand["reviews"][0]) == _WIDE_CANDIDATE_MAX_REVIEW_CHARS


# ---------------------------------------------------------------------------
# brand is ungated by the wide flag
# ---------------------------------------------------------------------------

def test_brand_is_carried_even_with_the_exact_gate_off(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    cand = _cand(_product())
    assert cand["brand"] == BRAND


def test_brand_stays_gated_when_the_wide_flag_is_off(monkeypatch):
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    cand = _cand(_product())
    assert "brand" not in cand


# ---------------------------------------------------------------------------
# SELECTION INVARIANCE - adding keys must not move the winner
# ---------------------------------------------------------------------------

def _three_product_page(wide: bool):
    """A page with three same-brand Products at different prices. Only the
    middle one is the queried SKU; the other two are near-siblings."""
    extras = dict(
        description="d", image="https://cdn/a.jpg", sku="S", gtin13="0123456789012",
        mpn="M", category="Fragrance",
        aggregateRating={"ratingValue": "5", "reviewCount": "999"},
        review=[{"@type": "Review", "reviewBody": "b"}],
    ) if wide else {}
    cheap = _product(name="Oud Elite So Black Eau de Toilette 100ml",
                     offers={"@type": "Offer", "price": "9.99",
                             "priceCurrency": CURRENCY,
                             "availability": "https://schema.org/InStock"},
                     **extras)
    right = _product(**extras)
    dear = _product(name="Oud Elite So Black Eau de Parfum 200ml",
                    offers={"@type": "Offer", "price": "199.99",
                            "priceCurrency": CURRENCY,
                            "availability": "https://schema.org/InStock"},
                    **extras)
    return _html(cheap, right, dear)


def test_multi_product_page_picks_the_same_winner_in_both_flag_states(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "false")
    off = extract_jsonld_price(_three_product_page(False), BRAND, CURRENCY,
                               query_name=QUERY, category=CATEGORY)
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    on = extract_jsonld_price(_three_product_page(True), BRAND, CURRENCY,
                              query_name=QUERY, category=CATEGORY)
    assert off is not None and on is not None
    assert (off["amount"], off["name"], off["in_stock"], off["currency"]) == \
           (on["amount"], on["name"], on["in_stock"], on["currency"])
    assert on["amount"] == 79.99          # the middle SKU, never the cheapest


def test_select_best_outcome_is_identical_with_and_without_the_wide_keys():
    """Direct unit proof over ``select_best`` itself: two candidate sets that
    differ ONLY by the added keys must elect the same candidate."""
    wide = dict(description="d", image=["https://cdn/a.jpg"], sku="S",
                gtin="0123456789012", mpn="M", category="Fragrance",
                aggregate_rating={"rating_value": 5.0, "review_count": 999},
                reviews=["b"])
    base = [
        {"amount": 9.99, "currency": CURRENCY, "in_stock": True, "brand": BRAND,
         "name": "Oud Elite So Black Eau de Toilette 100ml"},
        {"amount": 79.99, "currency": CURRENCY, "in_stock": True, "brand": BRAND,
         "name": QUERY},
        {"amount": 199.99, "currency": CURRENCY, "in_stock": True, "brand": BRAND,
         "name": "Oud Elite So Black Eau de Parfum 200ml"},
    ]
    widened = [dict(c, **wide) for c in base]
    for order in (lambda x: x, lambda x: list(reversed(x))):
        plain = select_best(order(base), QUERY, CATEGORY,
                            drop_out_of_stock=False, require_url=False)
        fat = select_best(order(widened), QUERY, CATEGORY,
                          drop_out_of_stock=False, require_url=False)
        assert plain is not None and fat is not None
        assert plain["amount"] == fat["amount"]
        assert plain["name"] == fat["name"]


def test_the_wide_keys_do_not_leak_into_the_page_scrape_result(flag_on):
    """``extract_price_from_html`` rebuilds its own result dict, so the widened
    candidate must not change the SHIPPED price payload shape."""
    html = _html(_product(
        description="d", image="https://cdn/a.jpg", sku="S", gtin13="0123456789012",
        mpn="M", category="Fragrance",
        aggregateRating={"ratingValue": "4.5", "reviewCount": "12"},
        review=[{"@type": "Review", "reviewBody": "b"}],
    ))
    result = extract_price_from_html(html, QUERY, CURRENCY, DOMAIN, URL,
                                     category=CATEGORY)
    assert result is not None
    assert result["amount"] == 79.99
    for key in ("description", "image", "sku", "gtin", "mpn", "category",
                "aggregate_rating", "reviews"):
        assert key not in result

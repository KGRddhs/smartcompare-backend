"""BLOCKER 3 - a hostile page's numeric strings must never crash the extractor
and must never smuggle a non-finite float into a dict we JSON-serialise.

THE INSTANCE the reviewer found, in ``_jsonld_product_rating`` (reached whenever
``ENABLE_WIDE_CANDIDATE`` is on, which is the DEFAULT)::

    count = int(float(_jsonld_scalar_text(agg.get(count_field))))

``float("1e400")`` is ``inf`` - it does NOT raise - and ``int(inf)`` raises
**OverflowError**, which ``except (TypeError, ValueError)`` does not catch. The
exception escapes ``extract_jsonld_price`` -> ``extract_price_from_html`` into
``structured_comparison_service._firecrawl_scraper`` (:1312) and
``._scrapedo_scraper`` (:1391), NEITHER of which wraps the call: the only guard
out there is a broad ``except Exception`` that silently drops the retailer's
price. One hostile blob = one retailer silently missing from a comparison.

Its twin needs no exception at all: a ``ratingValue`` of ``"1e400"`` parses to
``inf`` cleanly, ``inf > 0`` is True, and the ``inf`` is stored in the candidate
dict. ``json.dumps`` then emits the bare token ``Infinity``, which is NOT valid
JSON - every strict consumer (and ``allow_nan=False``) rejects the whole
document, so the blast radius is the entire payload, not one field.

THE CLASS, not the instance. This file fuzzes the SAME hostile table through
EVERY numeric conversion this wave added - the wide candidate dict, the OG comma
parser, the Shopify ``{pdp}.js`` adapter, the widened signal text - and asserts
three properties everywhere:

  1. the call NEVER raises (any exception type, not just the expected ones);
  2. no returned value, at any depth, is ``inf`` / ``-inf`` / ``nan``;
  3. ``json.dumps(result, allow_nan=False)`` succeeds on every returned dict.

MEASUREMENT MODE. Every fuzz test runs in BOTH gate modes, because they measure
different things: ``ENABLE_EXACT_PRICE_GATE=false`` is EXTRACTION-isolation (the
identity gate cannot reject a page and mask an extraction bug) and ``true`` is
SHIPPED behaviour. A crash must not survive in either.

No network. Synthetic minimal documents only.
"""

import json
import math

import pytest

from app.services import shopify_pdp_service
from app.services.price_service import (
    _jsonld_product_rating,
    _parse_og_price_number,
    _wide_signal_capture_text,
    extract_jsonld_price,
    extract_price_from_html,
    hostile_numeric_guard_enabled,
)

QUERY = "Oud Elite So Black Eau de Parfum 100ml"
BRAND = "Oud Elite"
CURRENCY = "BHD"
CATEGORY = "fragrances"
DOMAIN = "bh.oudelite.com"
URL = "https://bh.oudelite.com/product/so-black"


# ---------------------------------------------------------------------------
# The hostile table
# ---------------------------------------------------------------------------
# Every entry is a value a hostile (or merely broken) page can put where we
# expect a number. The float-overflow family is first because it is the one that
# does NOT raise on the way in - float() happily returns inf - so it survives
# every ``except (TypeError, ValueError)`` in the codebase and only detonates at
# the int() or the json.dumps() downstream.
HOSTILE_SCALARS = [
    "1e400",        # float() -> inf, no exception. int(inf) -> OverflowError.
    "-1e400",       # -> -inf
    "1e999999",     # -> inf (exponent far past DBL_MAX_10_EXP)
    "9" * 10000,    # -> inf, WITHOUT an exponent character anywhere
    "inf",          # float() accepts every one of these spellings verbatim
    "-inf",
    "Infinity",
    "nan",
    "NaN",
    "0x10",         # float() rejects hex -> ValueError
    "1_000",        # a PYTHON literal, not a price format
    "",             # empty
    "   ",          # whitespace only
    None,           # JSON null
    [],             # JSON array where a scalar belongs
    {},             # JSON object where a scalar belongs
    True,           # a bool is an int in Python - must not read as 1
    [{"deep": ["1e400"]}],
]

def _hid(value):
    """Short, stable parametrize id - repr() of a 10000-digit string makes the
    node id (and every failure line) unreadable."""
    text = repr(value)
    return text if len(text) <= 24 else "%s...len%d" % (text[:16], len(text))

GATE_MODES = ["false", "true"]


@pytest.fixture(params=GATE_MODES, ids=["extraction_isolated", "shipped"])
def gate_mode(request, monkeypatch):
    """Both measurement modes. ``false`` isolates EXTRACTION (the identity gate
    cannot reject the page and mask the bug); ``true`` is SHIPPED behaviour."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", request.param)
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "true")
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "true")
    return request.param


# ---------------------------------------------------------------------------
# Property helpers
# ---------------------------------------------------------------------------

def _nonfinite_paths(value, path="$"):
    """Every path in a nested structure holding inf / -inf / nan."""
    bad = []
    if isinstance(value, bool):
        return bad
    if isinstance(value, float) and not math.isfinite(value):
        bad.append("%s=%r" % (path, value))
    elif isinstance(value, dict):
        for k, v in value.items():
            bad.extend(_nonfinite_paths(v, "%s.%s" % (path, k)))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            bad.extend(_nonfinite_paths(v, "%s[%d]" % (path, i)))
    return bad


def assert_total(fn, *args, **kwargs):
    """Call ``fn``; assert it does not raise, that nothing non-finite comes
    back, and that whatever comes back is STRICTLY JSON-serialisable.

    ``allow_nan=False`` on purpose: json.dumps' DEFAULT happily writes the bare
    tokens Infinity/NaN, which no other JSON parser accepts - so the default
    would pass on exactly the payload this test exists to reject."""
    name = getattr(fn, "__name__", repr(fn))
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:                  # noqa: BLE001 - that IS the point
        pytest.fail("%s raised %s: %s" % (name, type(exc).__name__, exc))
    bad = _nonfinite_paths(result)
    assert not bad, "%s returned non-finite value(s): %s" % (name, bad)
    try:
        json.dumps(result, allow_nan=False)
    except (ValueError, TypeError) as exc:
        pytest.fail("%s result is not strict JSON: %s" % (name, exc))
    return result


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

def _product(**overrides):
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


def _ld_html(*nodes):
    blocks = "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(n)
        for n in nodes
    )
    return "<html><head>%s</head><body></body></html>" % blocks


def _raw_ld_html(raw):
    """A JSON-LD block whose bytes are given VERBATIM - so the document can
    carry things json.dumps would never emit from our own builders (a bare
    ``Infinity`` token, a 10000-digit number LITERAL rather than a string)."""
    return (
        '<html><head><script type="application/ld+json">%s</script>'
        "</head><body></body></html>" % raw
    )


def _og_html(**metas):
    tags = "".join(
        '<meta property="%s" content="%s">' % (k.replace("__", ":"), v)
        for k, v in metas.items()
        if v is not None
    )
    return "<html><head><title>%s</title>%s</head><body></body></html>" % (
        QUERY, tags,
    )


def _extract(html):
    return extract_price_from_html(
        html, QUERY, CURRENCY, DOMAIN, URL, category=CATEGORY,
    )


# ---------------------------------------------------------------------------
# 1. aggregateRating - the reviewer's instance, through the REAL extractor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hostile", HOSTILE_SCALARS, ids=_hid)
@pytest.mark.parametrize(
    "field", ["ratingValue", "reviewCount", "ratingCount", "bestRating"],
)
def test_hostile_aggregate_rating_field_never_crashes(gate_mode, field, hostile):
    agg = {"@type": "AggregateRating", "ratingValue": "4.5", "reviewCount": "12"}
    agg[field] = hostile
    assert_total(_extract, _ld_html(_product(aggregateRating=agg)))


@pytest.mark.parametrize("hostile", HOSTILE_SCALARS, ids=_hid)
@pytest.mark.parametrize(
    "field", ["ratingValue", "reviewCount", "ratingCount", "bestRating"],
)
def test_hostile_aggregate_rating_never_reaches_the_candidate(
    gate_mode, field, hostile,
):
    """The candidate dict is where the widened rating actually LANDS -
    ``extract_price_from_html`` projects a narrower result - so it gets the same
    three assertions directly."""
    agg = {"@type": "AggregateRating", "ratingValue": "4.5", "reviewCount": "12"}
    agg[field] = hostile
    assert_total(
        extract_jsonld_price,
        _ld_html(_product(aggregateRating=agg)),
        BRAND, CURRENCY, query_name=QUERY, category=CATEGORY,
    )


def test_overflow_error_is_caught_not_just_type_and_value(gate_mode):
    """The exact reviewer repro, isolated: int(float("1e400")) -> OverflowError."""
    agg = {"@type": "AggregateRating", "ratingValue": "4.5",
           "reviewCount": "1e400"}
    result = assert_total(_extract, _ld_html(_product(aggregateRating=agg)))
    assert result is None or result.get("amount") == 79.99


def test_infinite_rating_value_is_rejected_not_stored(gate_mode):
    """No exception here at all - the inf just walks in through ``> 0``."""
    for raw in ("1e400", "inf", "Infinity", "9" * 10000):
        agg = {"@type": "AggregateRating", "ratingValue": raw,
               "reviewCount": "12"}
        cand = assert_total(
            extract_jsonld_price, _ld_html(_product(aggregateRating=agg)),
            BRAND, CURRENCY, query_name=QUERY, category=CATEGORY,
        )
        if cand is not None:
            assert "aggregate_rating" not in cand, raw


# ---------------------------------------------------------------------------
# 2. The rating SANITY rules
# ---------------------------------------------------------------------------

def _rating(**agg):
    node = _product(aggregateRating=dict({"@type": "AggregateRating"}, **agg))
    return _jsonld_product_rating(node)


def test_rating_must_be_a_finite_number_in_a_sane_range(gate_mode):
    assert _rating(ratingValue="4.5", reviewCount="12") == {
        "rating_value": 4.5, "review_count": 12,
    }
    # non-positive
    assert _rating(ratingValue="0") is None
    assert _rating(ratingValue="-1") is None
    # above the implicit 5 ceiling when bestRating is absent
    assert _rating(ratingValue="6") is None
    assert _rating(ratingValue="100") is None
    # against its OWN declared bestRating
    assert _rating(ratingValue="9", bestRating="10") == {"rating_value": 9.0}
    assert _rating(ratingValue="11", bestRating="10") is None
    # a hostile bestRating cannot be used to smuggle a huge rating through
    assert _rating(ratingValue="1e400", bestRating="1e400") is None
    assert _rating(ratingValue="500", bestRating="inf") is None


def test_review_count_must_be_a_finite_non_negative_int(gate_mode):
    assert _rating(ratingValue="4.5", reviewCount="1e400") == {"rating_value": 4.5}
    assert _rating(ratingValue="4.5", reviewCount="nan") == {"rating_value": 4.5}
    assert _rating(ratingValue="4.5", reviewCount="-5") == {"rating_value": 4.5}
    assert _rating(ratingValue="4.5", reviewCount="9" * 10000) == {
        "rating_value": 4.5,
    }
    got = _rating(ratingValue="4.5", reviewCount="12.9")
    assert got == {"rating_value": 4.5, "review_count": 12}
    assert isinstance(got["review_count"], int)


# ---------------------------------------------------------------------------
# 3. offers.price - the same table in the PRICE position
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hostile", HOSTILE_SCALARS, ids=_hid)
def test_hostile_offer_price_never_crashes(gate_mode, hostile):
    node = _product(offers={
        "@type": "Offer", "price": hostile, "priceCurrency": CURRENCY,
        "availability": "https://schema.org/InStock",
    })
    assert_total(_extract, _ld_html(node))
    assert_total(
        extract_jsonld_price, _ld_html(node), BRAND, CURRENCY,
        query_name=QUERY, category=CATEGORY,
    )


# ---------------------------------------------------------------------------
# 4. The OpenGraph comma parser
# ---------------------------------------------------------------------------

_OG_STRINGS = [h for h in HOSTILE_SCALARS if isinstance(h, str)]


@pytest.mark.parametrize("hostile", _OG_STRINGS, ids=_hid)
@pytest.mark.parametrize(
    "meta",
    ["og__price__amount", "product__price__amount",
     "product__sale_price__amount"],
)
def test_hostile_og_amount_never_crashes(gate_mode, meta, hostile):
    metas = {"product__price__amount": "79.99",
             "product__price__currency": CURRENCY}
    metas[meta] = hostile
    assert_total(_extract, _og_html(**metas))


@pytest.mark.parametrize("hostile", HOSTILE_SCALARS, ids=_hid)
@pytest.mark.parametrize("currency", [CURRENCY, "SAR", None, "", 7, []],
                         ids=_hid)
def test_parse_og_price_number_is_total(gate_mode, hostile, currency):
    value = assert_total(_parse_og_price_number, hostile, currency)
    assert value is None or math.isfinite(value)


def test_og_amount_of_many_nines_is_refused_not_infinite(gate_mode):
    """``"9" * 400`` carries no exponent, so nothing "looks" hostile about it -
    float() still returns inf, ``amount > 0`` still passes, and an inf price
    ships with a currency label on it."""
    for raw in ("9" * 400, "9" * 10000, "1" + "0" * 400):
        assert _parse_og_price_number(raw, CURRENCY) is None, raw
        result = assert_total(
            _extract, _og_html(**{"product__price__amount": raw,
                                  "product__price__currency": CURRENCY}),
        )
        assert result is None or math.isfinite(result["amount"])


# ---------------------------------------------------------------------------
# 5. Document-level hostility - bare Infinity / NaN / huge number LITERALS
# ---------------------------------------------------------------------------
# Python's json module accepts the non-standard bare tokens ``Infinity``,
# ``-Infinity`` and ``NaN``, so a hostile blob delivers a real float inf WITHOUT
# ever passing through a string. And a number literal longer than
# sys.get_int_max_str_digits() (4300) makes json.loads raise a PLAIN ValueError,
# not a JSONDecodeError.

@pytest.mark.parametrize("literal", ["Infinity", "-Infinity", "NaN"])
def test_bare_non_finite_json_literals(gate_mode, literal):
    raw = json.dumps(_product(aggregateRating={
        "@type": "AggregateRating", "ratingValue": "4.5", "reviewCount": "12",
    }))
    raw = raw.replace('"4.5"', literal).replace('"12"', literal)
    assert_total(_extract, _raw_ld_html(raw))
    assert_total(
        extract_jsonld_price, _raw_ld_html(raw), BRAND, CURRENCY,
        query_name=QUERY, category=CATEGORY,
    )


def test_ten_thousand_digit_number_literal(gate_mode):
    raw = json.dumps(_product(aggregateRating={
        "@type": "AggregateRating", "ratingValue": "4.5", "reviewCount": "12",
    })).replace('"12"', "9" * 10000)
    assert_total(_extract, _raw_ld_html(raw))
    assert_total(
        extract_jsonld_price, _raw_ld_html(raw), BRAND, CURRENCY,
        query_name=QUERY, category=CATEGORY,
    )


# ---------------------------------------------------------------------------
# 6. The Shopify {pdp}.js adapter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hostile",
    HOSTILE_SCALARS + [float("inf"), float("-inf"), float("nan"),
                       10 ** 400, -1],
    ids=_hid,
)
def test_to_minor_is_total(gate_mode, hostile):
    minor = assert_total(shopify_pdp_service._to_minor, hostile)
    assert minor is None or (isinstance(minor, int) and minor >= 0)
    assert_total(shopify_pdp_service._to_major, minor)


@pytest.mark.parametrize(
    "hostile", ["1e400", float("inf"), 10 ** 400, "9" * 10000, "nan"], ids=_hid,
)
@pytest.mark.parametrize(
    "field", ["price", "compare_at_price", "price_min", "price_max"],
)
def test_hostile_shopify_payload_never_crashes(gate_mode, field, hostile):
    payload = {
        "product": {
            "title": QUERY, "handle": "so-black", "price": 7999,
            "price_min": 7999, "price_max": 7999,
            "variants": [{
                "id": 1, "title": "100ml", "price": 7999,
                "compare_at_price": 9999, "available": True,
            }],
        },
    }
    payload["product"][field] = hostile
    payload["product"]["variants"][0][field] = hostile
    assert_total(
        shopify_pdp_service.parse_shopify_pdp_json, payload,
        product_url=URL, json_url=URL + ".js",
    )


# ---------------------------------------------------------------------------
# 7. The widened signal text (no numbers of its own, but the same totality bar)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hostile", HOSTILE_SCALARS, ids=_hid)
@pytest.mark.parametrize(
    "field", ["product_type", "type", "tags", "body_html", "description"],
)
def test_wide_signal_capture_text_is_total(gate_mode, field, hostile):
    text = assert_total(
        _wide_signal_capture_text, "So Black 100ml", {field: hostile},
    )
    assert isinstance(text, str)


# ---------------------------------------------------------------------------
# 8. The flag lever - ENABLE_HOSTILE_NUMERIC_GUARD
# ---------------------------------------------------------------------------
# The guard flag exists ONLY for the two sites whose lines predate this wave
# (see the helper's docstring). Everything else BLOCKER 3 hardened lives in
# functions the wave ADDED, so those guards are unconditional and the flag
# cannot resurrect the reviewer's OverflowError - proven below.

def test_flag_helper_default_is_on(monkeypatch):
    monkeypatch.delenv("ENABLE_HOSTILE_NUMERIC_GUARD", raising=False)
    assert hostile_numeric_guard_enabled() is True
    for off in ("false", "0", "no", "off", "", "  FALSE  "):
        monkeypatch.setenv("ENABLE_HOSTILE_NUMERIC_GUARD", off)
        assert hostile_numeric_guard_enabled() is False


def _legacy_off(monkeypatch):
    monkeypatch.setenv("ENABLE_HOSTILE_NUMERIC_GUARD", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")


def test_flag_off_restores_the_legacy_bytes_at_both_gated_sites(monkeypatch):
    """Pins the ROLLBACK, not the desired behaviour: with the guard off, the two
    pre-existing expressions behave exactly as they did on 8adaefb - an inf
    price is accepted, and the >4300-digit number literal escapes json.loads as
    a bare ValueError. If either of these ever stops reproducing, the flag has
    stopped being a faithful rollback lever."""
    _legacy_off(monkeypatch)

    node = _product(offers={
        "@type": "Offer", "price": "1e400", "priceCurrency": CURRENCY,
        "availability": "https://schema.org/InStock",
    })
    legacy = _extract(_ld_html(node))
    assert legacy is not None and legacy["amount"] == float("inf")

    raw = json.dumps(_product()).replace('"79.99"', "9" * 10000)
    with pytest.raises(ValueError):
        _extract(_raw_ld_html(raw))


def test_flag_off_cannot_resurrect_the_reviewer_overflow(monkeypatch):
    """The instance the reviewer actually found is in wave-ADDED code, so its
    guard is unconditional: turning the flag off must NOT bring the
    OverflowError back."""
    _legacy_off(monkeypatch)
    agg = {"@type": "AggregateRating", "ratingValue": "4.5",
           "reviewCount": "1e400"}
    cand = assert_total(
        extract_jsonld_price, _ld_html(_product(aggregateRating=agg)),
        BRAND, CURRENCY, query_name=QUERY, category=CATEGORY,
    )
    assert cand is not None and cand["aggregate_rating"] == {"rating_value": 4.5}

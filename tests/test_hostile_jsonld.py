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
    _jsonld_str,
    _parse_og_price_number,
    _wide_signal_capture_text,
    extract_jsonld_price,
    extract_price_from_html,
    hostile_numeric_guard_enabled,
    is_accessory,
    is_accessory_for_category,
    is_counterfeit_listing,
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


# ===========================================================================
# 9. BLOCKER 5 - hostile STRING fields
# ===========================================================================
# BLOCKER 3 hardened every NUMERIC conversion. It did not touch the STRING
# ones, and those are the larger surface: schema.org types every one of
# `name` / `brand` / `sku` / `description` / `category` / `availability` /
# `priceCurrency` as Text, but JSON has no Text type - a blob can put null, a
# bool, a number, an array or an object in any of them and json.loads hands
# that shape straight through.
#
# THE VERIFIED REPRO. A Product node with "name": null and a perfectly valid
# Offer:
#
#     price_service.py:951   return is_accessory(title)      # title is None
#     price_service.py:848   title_lower = title.lower()     # AttributeError
#
# :945 already guards with (title or "") - but only for the two SCOPED
# exemption branches; the unscoped fall-through at :951 hands the RAW value on.
# And even a `name` that survives is_accessory dies two lines later at
# product_name.lower().replace(" ", ""), or - with the exact gate on - earlier
# still, inside html.unescape(True).
#
# PRE-EXISTING, NOT WAVE-INTRODUCED. The 8adaefb tree fails these too (it fails
# MORE of them; see the base-vs-branch count in the wave report), and no flag in
# this wave - ENABLE_HOSTILE_NUMERIC_GUARD included - moves the number. That is
# why the coercion is UNCONDITIONAL: there is no non-crashing legacy behaviour
# to roll back to, so a flag-OFF rollback that restored the raise would be
# restoring a defect, not a decision. What flag OFF still pins is byte-identity
# for every REAL page - proven by
# test_the_string_coercion_is_a_no_op_for_every_real_string below.

HOSTILE_STRING_VALUES = [
    ("null", None),                       # THE repro
    ("empty_list", []),
    ("empty_dict", {}),
    ("true", True),
    ("false", False),
    ("zero", 0),
    ("minus_one", -1),
    ("float", 1.5),
    ("huge_int", 10 ** 40),               # str() is fine; .lower() is not
    ("digits_5000", "9" * 5000),          # a >4300-digit NUMBER, as Text
    ("thing_null_name", {"@type": "Thing", "name": [None]}),
    ("thing_dict_value", {"@value": {}}),
    ("nested_dict", {"@type": "Thing", "value": {"deep": ["x"]}}),
    ("nested_list", [[{"name": None}], {"name": []}]),
    ("list_of_nulls", [None, None]),      # kills a naive " ".join(...)
    ("long_10k", "L" * 10000),
    ("control_chars", "a\x00b\x01c\x1fd\x7fe"),
    ("blank", "   "),
]

# (where, field) - schema.org types every one of these as Text.
STRING_FIELDS = [
    ("product", "name"),
    ("product", "brand"),
    ("product", "sku"),
    ("product", "description"),
    ("product", "category"),
    ("offer", "availability"),
    ("offer", "priceCurrency"),
]

# NB a >4300-digit integer LITERAL is deliberately NOT in this table: it is
# unreachable as a parsed value, because json.loads itself raises ValueError on
# it (that is BLOCKER 3's second gated site, which turns the raise into "skip
# this block"), so it can never arrive in a string field.

# The same hostile value has to survive every SHAPE the document can take -
# a bare node, an @graph wrapper, a top-level array - crossed with every shape
# the offers field can take, because each one reaches the string fields down a
# different branch of the parser.
DOC_SHAPES = ["bare", "graph", "array"]
OFFER_SHAPES = ["offer", "offer_list", "aggregate"]
FLAG_COMBOS = [
    (gate, guard)
    for gate in ("false", "true")
    for guard in ("false", "true")
]


def _hostile_product(where, field, value, offer_shape="offer"):
    """A COMPLETE, otherwise-valid Product node with exactly one hostile field."""
    if offer_shape == "aggregate":
        offer = {
            "@type": "AggregateOffer", "price": "79.99",
            "lowPrice": "79.99", "highPrice": "79.99",
            "priceCurrency": CURRENCY,
            "availability": "https://schema.org/InStock",
        }
    else:
        offer = {
            "@type": "Offer", "price": "79.99", "priceCurrency": CURRENCY,
            "availability": "https://schema.org/InStock",
        }
    if where == "offer":
        offer[field] = value
    node = {
        "@type": "Product",
        "name": QUERY,
        "brand": {"@type": "Brand", "name": BRAND},
        "sku": "OE-SO-BLACK-100",
        "description": "So Black eau de parfum, 100ml.",
        "category": "Fragrance",
        "offers": [offer] if offer_shape == "offer_list" else offer,
    }
    if where == "product":
        node[field] = value
    return node


def _shaped_doc(node, doc_shape):
    if doc_shape == "graph":
        return {"@context": "https://schema.org", "@graph": [node]}
    if doc_shape == "array":
        return [node]
    return node


def _titled_ld_html(blob):
    """A JSON-LD page that also carries a <title>, so the OG / microdata
    fallback cascade's page-identity gate has a real signal to read when the
    JSON-LD branch declines - the hostile value must survive that path too."""
    return (
        "<html><head><title>%s</title>"
        '<script type="application/ld+json">%s</script>'
        "</head><body></body></html>" % (QUERY, json.dumps(blob))
    )


def _string_field_flags(monkeypatch, gate, guard):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    monkeypatch.setenv("ENABLE_HOSTILE_NUMERIC_GUARD", guard)
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "true")
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
    monkeypatch.setenv("ENABLE_WIDE_SIGNAL_TEXT", "true")
    monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
    monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", "true")


def _check_total(html):
    """Return a failure string, or None. The three properties the extractor owes
    a hostile page: it must not raise, it must return dict-or-None, and whatever
    dict it returns must be STRICTLY JSON-serialisable."""
    try:
        result = extract_price_from_html(
            html, QUERY, CURRENCY, DOMAIN, URL, category=CATEGORY,
        )
    except Exception as exc:                  # noqa: BLE001 - that IS the point
        return "raised %s: %s" % (type(exc).__name__, exc)
    if result is not None and not isinstance(result, dict):
        return "returned %s, not dict-or-None" % (type(result).__name__,)
    if result is not None:
        try:
            json.dumps(result, allow_nan=False)
        except (ValueError, TypeError) as exc:
            return "result is not strict JSON: %s" % (exc,)
    return None


# --- 9a. the repro, named and isolated ------------------------------------

@pytest.mark.parametrize("hostile", [v for _, v in HOSTILE_STRING_VALUES],
                         ids=[i for i, _ in HOSTILE_STRING_VALUES])
def test_hostile_jsonld_name_never_crashes_the_extractor(gate_mode, hostile):
    """THE repro: a Product `name` that is not a string, plus a valid offer."""
    assert_total(_extract, _titled_ld_html(
        _hostile_product("product", "name", hostile)))


@pytest.mark.parametrize("hostile", [v for _, v in HOSTILE_STRING_VALUES],
                         ids=[i for i, _ in HOSTILE_STRING_VALUES])
def test_hostile_jsonld_name_never_crashes_is_accessory_directly(hostile):
    """:951 handed the RAW value to is_accessory, whose :848 does
    title.lower(). Both entry points must be total on their own."""
    assert is_accessory(hostile) in (True, False)
    assert is_accessory_for_category(hostile, CATEGORY) in (True, False)
    assert is_counterfeit_listing(hostile) in (True, False)


@pytest.mark.parametrize(
    "brand_shape",
    [
        [{"name": None}],                       # list-of-dicts -> " ".join(None)
        [{"@type": "Brand"}, {"name": []}],
        [None, {"name": "Oud Elite"}],
        {"name": None},
        {"name": {"@value": None}},
        True,
        -1,
    ],
    ids=["list_null_name", "list_missing_and_list", "list_with_null_member",
         "dict_null_name", "dict_nested_null", "bool", "int"],
)
def test_hostile_jsonld_brand_shapes_never_crash(gate_mode, brand_shape):
    """The `brand` reader already isinstance-checks dict and list, but its list
    arm builds " ".join(b.get("name", "") ...) - a member whose `name` is an
    explicit JSON null puts None into the join and TypeErrors."""
    assert_total(_extract, _titled_ld_html(
        _hostile_product("product", "brand", brand_shape)))


# --- 9b. the 3000+ case grid ----------------------------------------------

def test_the_full_hostile_string_grid_is_total(monkeypatch):
    """Every string-typed JSON-LD field x every hostile value x every document
    shape x every offers shape x BOTH gate modes x BOTH guard-flag states.

    One test rather than 3780 parametrize nodes on purpose: the grid is a
    MEASUREMENT (the wave report quotes its failure count on base vs branch),
    and a single loop reports the count directly instead of making the reader
    add up node ids."""
    failures = []
    cases = 0
    for gate, guard in FLAG_COMBOS:
        _string_field_flags(monkeypatch, gate, guard)
        for doc_shape in DOC_SHAPES:
            for offer_shape in OFFER_SHAPES:
                for where, field in STRING_FIELDS:
                    for value_id, value in HOSTILE_STRING_VALUES:
                        cases += 1
                        node = _hostile_product(where, field, value, offer_shape)
                        html = _titled_ld_html(_shaped_doc(node, doc_shape))
                        problem = _check_total(html)
                        if problem:
                            failures.append(
                                "gate=%s guard=%s %s/%s %s.%s=%s -> %s" % (
                                    gate, guard, doc_shape, offer_shape,
                                    where, field, value_id, problem,
                                )
                            )
    assert cases >= 3000, "grid shrank to %d cases" % cases
    assert not failures, "%d/%d hostile string cases failed:\n%s" % (
        len(failures), cases, "\n".join(failures[:25]),
    )


def test_the_grid_also_holds_when_every_string_field_is_hostile_at_once(
    monkeypatch,
):
    """A real hostile blob does not corrupt ONE field politely. Set them all."""
    for gate, guard in FLAG_COMBOS:
        _string_field_flags(monkeypatch, gate, guard)
        for _, value in HOSTILE_STRING_VALUES:
            node = {
                "@type": "Product",
                "name": value, "brand": value, "sku": value,
                "description": value, "category": value,
                "offers": {
                    "@type": "Offer", "price": "79.99",
                    "priceCurrency": value, "availability": value,
                },
            }
            problem = _check_total(_titled_ld_html(node))
            assert not problem, "all-hostile node (%r): %s" % (value, problem)
            # ... and with a VALID currency, so the offer is actually accepted
            # and the hostile name reaches the candidate dict + the caller.
            node["offers"]["priceCurrency"] = CURRENCY
            problem = _check_total(_titled_ld_html(node))
            assert not problem, "all-hostile node, real currency (%r): %s" % (
                value, problem,
            )


# --- 9c. the coercion helper itself ---------------------------------------

@pytest.mark.parametrize("hostile", [v for _, v in HOSTILE_STRING_VALUES],
                         ids=[i for i, _ in HOSTILE_STRING_VALUES])
def test_jsonld_str_always_returns_a_str(hostile):
    assert isinstance(_jsonld_str(hostile), str)


def test_jsonld_str_is_identity_on_a_real_string():
    """The no-op guarantee the byte-identity argument rests on: a value that is
    ALREADY a str comes back unchanged - not stripped, not normalised - so no
    real page can see a different byte through this helper."""
    for text in ("  Oud Elite So Black  ", "", "   ", "A" * 10000,
                 "Nuit d Issey - 100ml", "a\x00b"):
        assert _jsonld_str(text) is text


def test_jsonld_str_digs_a_thing_node_out_but_never_a_bool():
    assert _jsonld_str({"@type": "Thing", "name": "Oud Elite"}) == "Oud Elite"
    assert _jsonld_str({"@value": "Oud Elite"}) == "Oud Elite"
    assert _jsonld_str(["", None, "Oud Elite"]) == "Oud Elite"
    assert _jsonld_str(123) == "123"
    # a bool is an int in Python - it must NOT read as the text "True"/"1"
    assert _jsonld_str(True) == ""
    assert _jsonld_str(False) == ""
    assert _jsonld_str(float("inf")) == ""
    assert _jsonld_str(float("nan")) == ""


# --- 9d. byte-identity: the coercion changes nothing for a real page -------

def _real_page():
    return _titled_ld_html(_hostile_product("product", "sku", "OE-SO-BLACK-100"))


def test_the_string_coercion_is_a_no_op_for_every_real_string(monkeypatch):
    """Why BLOCKER 5's coercion can be unconditional without breaking the
    flag-OFF rollback contract: on a page whose string fields are actually
    STRINGS - i.e. every real page - the guard flag makes no difference at all,
    in either gate mode. The only inputs the coercion changes are the ones on
    which 8adaefb raised an uncaught AttributeError/TypeError."""
    for gate in ("false", "true"):
        _string_field_flags(monkeypatch, gate, "true")
        with_guard = _extract(_real_page())
        _string_field_flags(monkeypatch, gate, "false")
        without_guard = _extract(_real_page())
        assert with_guard == without_guard
        assert with_guard is not None
        assert with_guard["amount"] == 79.99


def test_the_guard_flag_still_flips_the_two_blocker_3_legacy_sites(monkeypatch):
    """The flag is still a live lever - BLOCKER 5 did not neuter it. Guarded:
    an inf price is dropped. Unguarded: 8adaefb's bytes, the inf is returned."""
    node = _product(offers={
        "@type": "Offer", "price": "1e400", "priceCurrency": CURRENCY,
        "availability": "https://schema.org/InStock",
    })
    _string_field_flags(monkeypatch, "false", "true")
    assert _extract(_ld_html(node)) is None
    _string_field_flags(monkeypatch, "false", "false")
    legacy = _extract(_ld_html(node))
    assert legacy is not None and legacy["amount"] == float("inf")

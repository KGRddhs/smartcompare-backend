"""S81-G1 unit D08 JSONLD-WIDEN -- the frozen RED file.

Flags (new names, default OFF, read PER CALL by the new stdlib leaf
``app/services/jsonld_widen.py``): ``ENABLE_IMAGE_PIPELINE_V2`` (the JSON-LD
image + identifiers) and ``ENABLE_JSONLD_RATING`` (rating channel 1 + the LLM
rating removal). Spec: ``.qa-s80/S81-G1_UNIT_SPEC.md`` (unit D08, sections 2, 5
and 6) as amended by ``RULINGS_S81_G1`` (R-G1-1 the ROBOTS_ENTRY_LOOKUP seam with
no reader; R-G1-2 channel 1 fills only an EMPTY rating slot after the Serper
tiers; R-G1-3 IMAGE_CDN_HOSTS a constant; R-G1-4 judge.me deleted unflagged).

Row map (spec section 5):
  RED  R1-R21  ``test_d08_rNN_*``  fail at base on an AssertionError only (a
       missing leaf / symbol is asserted through find_spec / getattr helpers).
  PIN  P1-P9   ``test_d08_pN_*``   green at base. B1 rule: every flag-OFF row
       runs with the FULL configuration present -- both D08 flags OFF in every
       falsy spelling, ``ENABLE_WIDE_CANDIDATE=true``, both exact-gate modes,
       ``ENABLE_DATA_GUARDS_V2`` both ways, and (once the leaf exists) the seam
       ``ROBOTS_ENTRY_LOOKUP`` patched to an ALLOWING recorder plus counters on
       ``stamp_jsonld_facts`` / ``channel1_rating`` -- so a "not gated" mutant
       is killed, never a vacuous pass.

The flag-OFF rating golden ``tests/fixtures/s81_d08_rating_flag_off_golden.json``
was RECORDED AT BASE (6c14ac95) by running ``_p5_observe`` over ``_p5_records``.

Hermetic: no network, no .env, no real credentials; synthetic hosts only
(``store-a.example.com`` and friends); HTML is built from dicts with json.dumps;
the scs piggyback and rating block run through the REAL
``StructuredComparisonService._fetch_product_data`` with the D03 harness copied
from ``tests/test_s81_d03_deny_and_guards.py`` (never imported from it).
Digit runs are built from short parts so no literal carries 8+ digits.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

LEAF = "app.services.jsonld_widen"
IMG_FLAG = "ENABLE_IMAGE_PIPELINE_V2"
RATING_FLAG = "ENABLE_JSONLD_RATING"
TRUTHY = ["true", "1", "yes", "on", " TRUE "]
FALSY_SET = [None, "", "false", "0", "no", " OFF "]
OFF_SPELLINGS = [None, "false", "0", "off", "", " OFF "]
GOLDEN_SPELLINGS = [None, "false", "0", "off", ""]
REPO = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO / "tests" / "fixtures" / "s81_d08_rating_flag_off_golden.json"


def _vid(value):
    """A space-free test id for an env spelling (None = unset)."""
    if value is None:
        return "unset"
    if value == "":
        return "empty"
    core = value.strip().replace(" ", "_")
    return core + "_padded" if core != value else core

# Flags the extract path reads whose CODE DEFAULT the recorded literals assume:
# deleted per row so an ambient value can never move a literal.
EXTRACT_PATH_FLAGS = (
    "ENABLE_JSONLD_FIRST", "ENABLE_JSONLD_SHAPE_LADDER", "ENABLE_NOT_A_PDP_FILTER",
    "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_STRICT_CURRENCY_LABEL", "ENABLE_SALE_PRICE_FIRST",
    "ENABLE_OG_BRANCH_FIXES", "ENABLE_EXTRACTOR_FIXES_2608", "ENABLE_VISIBLE_TEXT_CURRENCY",
    "ENABLE_WALL_SIGNATURE_ANCHOR", "ENABLE_MONEY_PARSER_V2", "ENABLE_HOSTILE_NUMERIC_GUARD",
    "ENABLE_WIDE_SIGNAL_TEXT", "ENABLE_SHOWABLE_NAME_IDENTITY", "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX",
    "ENABLE_FRAGRANCE_GLASS_EXEMPTION", "ENABLE_RSC_FLIGHT_PRICE", "ENABLE_NORMALIZE_WORDS_EMPTY_FIX",
    "ENABLE_DATA_GUARDS_V2", "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_LONGEST_HOST_MATCH",
)

FIXED_NOW = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)
FIXED_NOW_Z = "2026-10-29T12:00:00Z"

# ---------------------------------------------------------------------------
# synthetic identity (no real merchant data)
# ---------------------------------------------------------------------------
QUERY = "Testhaus Oud Noir Eau de Parfum 100ml"
BRAND = "Testhaus"
CURRENCY = "BHD"
CATEGORY = "fragrances"
HOST = "store-a.example.com"
DOMAIN = HOST
PAGE_URL = "https://store-a.example.com/products/oud-noir-100ml"
IMG_HTTP = "http://store-a.example.com/img/a.jpg"
IMG_FIMGS = "https://fimgs.net/mdimg/perfume/375x500.1.jpg"
IMG_FIRST = "https://store-a.example.com/img/c.jpg"
IMG_OFF_LIST = "https://img.other-b.example.net/hero.jpg"
CASCADE_IMG = "https://cdn-a.example.com/cascade.jpg"
PHARMACY_URL = "https://pharmacy-a.example.com/p/oud-noir-100ml"
PHARMACY_NAME = "Pharmacy A"


def _digits(*parts):
    """Join short digit parts (no literal in this file carries 8+ digits)."""
    return "".join(parts)


GTIN13_OK = _digits("4006", "3813", "3393", "1")
GTIN13_BAD = _digits("4006", "3813", "3393", "2")
GTIN8_OK = _digits("9638", "5074")
GTIN12_OK = _digits("0360", "0029", "1452")
GTIN14_OK = _digits("1061", "4141", "0004", "15")


# ---------------------------------------------------------------------------
# helpers: the leaf is never imported at module top (AssertionError at base)
# ---------------------------------------------------------------------------
def _leaf_spec():
    return importlib.util.find_spec(LEAF)


def _leaf():
    assert _leaf_spec() is not None, "D08: app/services/jsonld_widen.py does not exist"
    return importlib.import_module(LEAF)


def _leaf_fn(name):
    fn = getattr(_leaf(), name, None)
    assert callable(fn), "D08: jsonld_widen.%s is missing or not callable" % name
    return fn


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _both_off(mp, value):
    _set(mp, IMG_FLAG, value)
    _set(mp, RATING_FLAG, value)


def _ps():
    return importlib.import_module("app.services.price_service")


def _es():
    return importlib.import_module("app.services.extraction_service")


def _rb():
    return importlib.import_module("app.services.response_builder")


@pytest.fixture(autouse=True)
def _d08_env(monkeypatch):
    """Every row sets its own flag state; nothing ambient leaks in. The leaf
    seams are restored after every row (monkeypatch) once the leaf exists."""
    monkeypatch.delenv(IMG_FLAG, raising=False)
    monkeypatch.delenv(RATING_FLAG, raising=False)
    for name in EXTRACT_PATH_FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_WIDE_CANDIDATE", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    if _leaf_spec() is not None:
        mod = importlib.import_module(LEAF)
        for seam in ("ROBOTS_ENTRY_LOOKUP", "_now"):
            if hasattr(mod, seam):
                monkeypatch.setattr(mod, seam, getattr(mod, seam))
    yield


# ---------------------------------------------------------------------------
# synthetic robots records (the S81-15 kb_merchants.robots shape)
# ---------------------------------------------------------------------------
def _robots(**over):
    rec = {
        "state": "allow",
        "status": 200,
        "body_sha": "synthetic-sha",
        "fetched_at": "2026-10-29T00:00:00Z",
        "next_reread": "2026-10-30T00:00:00Z",
        "crawl_delay": None,
        "origin": "https://store-a.example.com",
        "source": "datacenter",
        "rules": {
            "qarenbot": [["disallow", "/admin"]],
            "star": [["disallow", "/cart"], ["allow", "/"]],
        },
        "probed": {"/": "allow"},
    }
    rec.update(over)
    return rec


def _entry(**over):
    ent = {"status": "live", "deny": False, "robots": _robots(), "challenge": {}}
    ent.update(over)
    return ent


def _install_off_recorders(monkeypatch):
    """B1 full configuration for the flag-OFF rows: the seam answers an ALLOWING
    entry for every host, ``_now`` is pinned inside the record's freshness
    window, and the two leaf entry points are wrapped with counters. All counts
    must stay zero with the flags OFF. At base the leaf is absent (nothing to
    install; the rows then pin today's bytes)."""
    rec = {"seam": [], "stamp": 0, "channel1": 0}
    if _leaf_spec() is None:
        return rec
    mod = importlib.import_module(LEAF)

    def _seam(host):
        rec["seam"].append(host)
        return _entry()

    monkeypatch.setattr(mod, "ROBOTS_ENTRY_LOOKUP", _seam, raising=False)
    monkeypatch.setattr(mod, "_now", lambda: FIXED_NOW, raising=False)
    for name, key in (("stamp_jsonld_facts", "stamp"), ("channel1_rating", "channel1")):
        orig = getattr(mod, name, None)
        if callable(orig):
            def _wrap(*a, _o=orig, _k=key, **k):
                rec[_k] += 1
                return _o(*a, **k)

            monkeypatch.setattr(mod, name, _wrap)
    return rec


def _assert_untouched(rec):
    assert rec == {"seam": [], "stamp": 0, "channel1": 0}, (
        "flag OFF: jsonld_widen did work beyond the two env reads: %r" % (rec,)
    )


# ---------------------------------------------------------------------------
# JSON-LD page builder
# ---------------------------------------------------------------------------
def _product(**over):
    node = {
        "@type": "Product",
        "name": QUERY,
        "brand": {"@type": "Brand", "name": BRAND},
        "offers": {
            "@type": "Offer",
            "price": "45.500",
            "priceCurrency": CURRENCY,
            "availability": "https://schema.org/InStock",
        },
    }
    node.update(over)
    return node


def _full_node(**over):
    """The P1 node: image / gtin / sku / size / aggregateRating all present."""
    node = _product(
        description="A dark oud.",
        image=[IMG_HTTP, IMG_FIMGS, IMG_FIRST],
        sku="SKU-A1",
        gtin13=GTIN13_OK,
        size="100 ml",
        aggregateRating={"@type": "AggregateRating", "ratingValue": "8",
                         "bestRating": "10", "reviewCount": "120"},
    )
    node.update(over)
    return node


def _html(*nodes):
    blocks = "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(n) for n in nodes
    )
    return "<html><head><title>%s</title>%s</head><body></body></html>" % (QUERY, blocks)


def _extract(html, url=PAGE_URL, domain=DOMAIN):
    return _ps().extract_price_from_html(html, QUERY, CURRENCY, domain, url, category=CATEGORY)


def _cand(*nodes):
    return _ps().extract_jsonld_price(_html(*nodes), BRAND, CURRENCY, query_name=QUERY,
                                      category=CATEGORY)


WIDE_KEYS = ("description", "image", "sku", "gtin", "mpn", "category", "aggregate_rating",
             "reviews")


# ---------------------------------------------------------------------------
# pharmacy producer harness (the house fake httpx client)
# ---------------------------------------------------------------------------
class _FakeResp:
    status_code = 200

    def __init__(self, text):
        self.text = text


def _pharmacy(monkeypatch, html):
    ps = _ps()

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, **kwargs):
            return _FakeResp(html)

    monkeypatch.setattr(ps.httpx, "AsyncClient", _Client)
    return asyncio.run(ps._try_pharmacy_urls([(PHARMACY_URL, PHARMACY_NAME)], BRAND, CURRENCY,
                                             full_name=QUERY))


# ---------------------------------------------------------------------------
# scs harness: COPIED from tests/test_s81_d03_deny_and_guards.py (_scs_fetch /
# _scs_product_info), extended with the price url / facts, the provider
# rating_data and the reviews dict the GPT fallback reads.
# ---------------------------------------------------------------------------
SCS_PRICE_URL = "https://store-a.example.com/products/iphone-15"
PROVIDER = {
    "rating": 4.6,
    "review_count": 100,
    "rating_verified": True,
    "rating_source": {"name": "test", "url": None},
}
NO_PROVIDER = {"rating": None, "review_count": None, "rating_verified": False,
               "rating_source": None}
CH1_FACTS = {"rating": {"value": 4.4, "count": 120}}


def _scs_product_info():
    return {
        "brand": "Apple",
        "name": "iPhone 15",
        "variant": None,
        "category": "electronics",
        "search_query": "Apple iPhone 15",
    }


async def _scs_fetch(page_img=None, cascade_img=CASCADE_IMG, price_url=SCS_PRICE_URL,
                     facts=None, rating_data=None, reviews=None):
    from app.services.structured_comparison_service import get_comparison_service

    price = {"amount": 350, "currency": "BHD", "retailer": "Store A", "image_url": page_img}
    if price_url is not None:
        price["url"] = price_url
    if facts is not None:
        price["_jsonld_facts"] = json.loads(json.dumps(facts))
    service = get_comparison_service()
    with (
        patch.object(service, "_get_specs", AsyncMock(return_value={"display": "6.1"})),
        patch.object(service, "_get_price", AsyncMock(return_value=price)),
        patch.object(service, "_get_reviews", AsyncMock(
            return_value=reviews if reviews is not None else {"review_summary": {}})),
        patch.object(service, "_get_verified_rating", AsyncMock(
            return_value=dict(rating_data if rating_data is not None else PROVIDER))),
        patch("app.services.structured_comparison_service.search_web",
              AsyncMock(return_value={"organic": []})),
        patch("app.services.structured_comparison_service.get_product_image_url",
              AsyncMock(return_value=cascade_img)),
        patch("app.services.structured_comparison_service.tier2_fill_non_negotiables",
              AsyncMock(return_value={})),
        patch("app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
              AsyncMock(return_value={})),
    ):
        return await service._fetch_product_data(
            _scs_product_info(),
            region="bahrain",
            include_specs=True,
            include_reviews=True,
            nocache=True,
        )


def _seam_recorder(monkeypatch, entry_factory):
    """Patch the leaf seam with a recording callable; returns the call list."""
    calls = []
    mod = _leaf()

    def _seam(host):
        calls.append(host)
        return entry_factory()

    monkeypatch.setattr(mod, "ROBOTS_ENTRY_LOOKUP", _seam, raising=False)
    monkeypatch.setattr(mod, "_now", lambda: FIXED_NOW, raising=False)
    return calls


# ---------------------------------------------------------------------------
# response-builder harness (the tests/test_response_builder_price_pending shape)
# ---------------------------------------------------------------------------
def _rb_product(name, rating, review_count, rating_source, **extra):
    price = {"amount": 40.0, "currency": "BHD", "source_method": "local_bhd",
             "title": name, "url": "https://store-a.example.com/p/%s" % name.split()[0].lower()}
    pd = {
        "brand": name.split()[0], "name": name, "full_name": name,
        "category": "fragrances",
        "price": price, "best_price": 40.0, "retailer": "store-a.example.com",
        "specs": {}, "reviews": None,
        "rating": rating, "rating_source": rating_source, "review_count": review_count,
        "fact_check": {},
    }
    pd.update(extra)
    return pd


def _rb_scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
        "tradeoff_pairs": [], "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {}, "comparison_pair": ["product_a", "product_b"],
        "verdict_text": "Test.", "key_differences": [],
    }


def _build(product_data):
    return _rb().build_comparison_response(
        query="A vs B", product_data=product_data, scoring_result=_rb_scoring(),
        comparison=None, region="bahrain", api_calls=0, elapsed_seconds=0.0,
        total_cost=0.0, gpt_calls=0, serper_calls=0, from_cache=False,
        verdict_validation={},
    )


OTHER_SOURCE = {"name": "Retailer B", "url": "https://store-b.example.com/p/x",
                "extract_method": "serper_shopping", "confidence": "high"}


# ---------------------------------------------------------------------------
# reviews-call harness (client recorder on the router seam)
# ---------------------------------------------------------------------------
def _reviews_system_sent(monkeypatch):
    es = _es()
    sent = []

    async def _route(role, fn, client, **kwargs):
        sent.append((role, kwargs["messages"][0]["content"]))
        msg = SimpleNamespace(content=json.dumps({"review_summary": {}}))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=None)

    monkeypatch.setattr(es, "_llm_router", SimpleNamespace(route=_route))
    monkeypatch.setattr(es, "get_client", lambda: object())
    asyncio.run(es.extract_reviews("Testhaus", "Oud Noir", None, "context", "fragrances"))
    assert len(sent) == 1 and sent[0][0] == "reviews"
    return sent[0][1]


LINE_AVG = '    "average_rating": 0.0-5.0 or null,\n'
LINE_TOTAL = '    "total_reviews": estimated_count or null,\n'


# ===========================================================================
# RED rows
# ===========================================================================
@pytest.mark.parametrize("value", FALSY_SET + TRUTHY, ids=_vid)
def test_d08_r1_flag_readers_per_call(value, monkeypatch):
    """R1 (2.1): each reader True exactly for the truthy spellings, read per call
    (flipping the env after import flips the result), and the two flags are
    independent."""
    expected = value is not None and value.strip().lower() in ("true", "1", "yes", "on")
    for flag, other, reader in ((IMG_FLAG, RATING_FLAG, "image_pipeline_v2_enabled"),
                                (RATING_FLAG, IMG_FLAG, "jsonld_rating_enabled")):
        fn = _leaf_fn(reader)
        _set(monkeypatch, flag, value)
        _set(monkeypatch, other, "false" if expected else "true")
        assert fn() is expected, (flag, value)
        _set(monkeypatch, flag, "false" if expected else "true")
        assert fn() is (not expected), (flag, "flipped")
        monkeypatch.delenv(flag, raising=False)
        monkeypatch.delenv(other, raising=False)


R2_CASES = [
    ("https://store-a.example.com/img/c.jpg?v=3", "https://store-a.example.com/p/x", frozenset()),
    ("https://store-a.example.com/img/c.jpg", "https://www.store-a.example.com/p/x", frozenset()),
    ("https://www.store-a.example.com/img/c.jpg", "https://store-a.example.com/p/x", frozenset()),
    ("https://images.store-a.example.com/c.JPEG", "https://store-a.example.com/p/x", frozenset()),
    ("https://cdn.shopify.com/s/files/1/x.webp", "https://store-a.example.com/p/x", frozenset()),
    ("https://www.brand-a.example.com/img/x.png", "https://store-b.example.com/p/x",
     frozenset({"brand-a.example.com"})),
]


@pytest.mark.parametrize("url,page,brands", R2_CASES, ids=["first-party-query", "apex-image-www-page",
                                                          "www-image-apex-page", "subdomain-upper-ext",
                                                          "platform-cdn", "brand-domain"])
def test_d08_r2_image_policy_accepts(url, page, brands):
    """R2 (2.2): https + public host + raster + not denied + allowlisted
    (first-party incl. the www/apex pair, a platform CDN, a brand domain)."""
    fn = _leaf_fn("allowed_image_url")
    assert fn("  " + url + " ", page, brands) == url
    assert fn(url, page, brands) == url


def _r3_cases():
    data_uri = "data" + ":image/png;base64," + "iVBORw0KGgo"
    userinfo = "https://" + "someone" + "@" + "store-a.example.com/img/c.jpg"
    page = "https://store-a.example.com/p/x"
    return [
        ("http", "http://store-a.example.com/img/c.jpg", page),
        ("protocol-relative", "//store-a.example.com/img/c.jpg", page),
        ("data-uri", data_uri, page),
        ("ip-literal", "https://192.0.2.10/img/c.jpg", "https://192.0.2.10/p/x"),
        ("localhost", "https://localhost/img/c.jpg", "https://localhost/p/x"),
        ("userinfo", userinfo, page),
        ("svg", "https://store-a.example.com/img/c.svg", page),
        ("no-extension", "https://store-a.example.com/img/c", page),
        ("php", "https://store-a.example.com/img/c.php?id=1", page),
        ("fimgs-first-party", "https://fimgs.net/mdimg/perfume/x.jpg", "https://fimgs.net/p/x"),
        ("fragrantica-first-party", "https://www.fragrantica.com/img/x.jpg",
         "https://www.fragrantica.com/perfume/x.html"),
        ("parfumo-first-party", "https://www.parfumo.com/img/x.jpg",
         "https://www.parfumo.com/Perfumes/x"),
        ("third-party", "https://img.other-b.example.net/hero.jpg", page),
        ("test-tld", "https://store.perfume-shop.test/hero.jpg", "https://store.perfume-shop.test/p"),
        ("not-a-str", None, page),
    ]


@pytest.mark.parametrize("case", _r3_cases(), ids=lambda c: c[0])
def test_d08_r3_image_policy_refuses(case, monkeypatch):
    """R3 (2.2): every refusal -> None. ENABLE_DATA_GUARDS_V2 is UNSET here: the
    deny check is the D08 policy's own (a mutant gating it behind the D03 flag
    is killed by the first-party denied rows)."""
    monkeypatch.delenv("ENABLE_DATA_GUARDS_V2", raising=False)
    fn = _leaf_fn("allowed_image_url")
    _name, url, page = case
    assert fn(url, page, frozenset()) is None


@pytest.mark.parametrize("raw,expected", [
    (GTIN13_OK, GTIN13_OK),
    ("4006 3813-3393 1", GTIN13_OK),
    (GTIN8_OK, GTIN8_OK),
    (GTIN12_OK[:4] + "-" + GTIN12_OK[4:], GTIN12_OK),
    (GTIN14_OK, GTIN14_OK),
    (GTIN13_BAD, None),
    (GTIN13_OK[:9], None),
    (GTIN13_OK[:10], None),
    (GTIN13_OK[:11], None),
    (GTIN13_OK[:11] + "AB", None),
    ("", None),
    (None, None),
], ids=["gtin13", "gtin13-spaced-hyphen", "gtin8", "gtin12-hyphen", "gtin14", "wrong-check-digit",
        "len9", "len10", "len11", "letters", "empty", "none"])
def test_d08_r4_valid_gtin(raw, expected):
    """R4 (2.2): spaces/hyphens removed, digits only, length 8/12/13/14, GS1
    mod-10 check digit; else None."""
    assert _leaf_fn("valid_gtin")(raw) == expected


def test_d08_r5_reduced_result_image_url_on(monkeypatch):
    """R5 (2.4): image flag ON -> the reduced result carries image_url = the FIRST
    allowed entry of [http, fimgs, first-party https]; omitted when none is
    allowed; the eight wide keys stay absent."""
    _leaf()
    monkeypatch.setenv(IMG_FLAG, "true")
    result = _extract(_html(_full_node()))
    assert result is not None and result.get("amount") == 45.5
    assert result.get("image_url") == IMG_FIRST
    for key in WIDE_KEYS:
        assert key not in result, key
    none_allowed = _extract(_html(_full_node(image=[IMG_HTTP, IMG_FIMGS])))
    assert none_allowed is not None and none_allowed.get("amount") == 45.5
    assert "image_url" not in none_allowed


@pytest.mark.parametrize("gtin,expected_facts", [
    (GTIN13_OK, {"gtin": GTIN13_OK, "sku": "SKU-A1", "size": "100 ml"}),
    (GTIN13_BAD, {"sku": "SKU-A1", "size": "100 ml"}),
], ids=["valid-gtin", "bad-check-digit"])
def test_d08_r6_reduced_result_facts_on(gtin, expected_facts, monkeypatch):
    """R6 (2.4/2.5): image flag ON -> _jsonld_facts == {gtin (valid only), sku,
    size}; the rating member stays out while ENABLE_JSONLD_RATING is OFF."""
    _leaf()
    monkeypatch.setenv(IMG_FLAG, "true")
    monkeypatch.setenv(RATING_FLAG, "false")
    result = _extract(_html(_full_node(gtin13=gtin)))
    assert result is not None
    assert result.get("_jsonld_facts") == expected_facts


@pytest.mark.parametrize("agg,expected", [
    ({"ratingValue": "4.4", "reviewCount": "120"}, {"value": 4.4, "count": 120}),
    ({"ratingValue": "8", "bestRating": "10", "reviewCount": "120"}, {"value": 4.0, "count": 120}),
    ({"ratingValue": "92", "bestRating": "100", "reviewCount": "120"}, {"value": 4.6, "count": 120}),
], ids=["best-absent", "best-10", "best-100"])
def test_d08_r7_rating_fact_on_scaled(agg, expected, monkeypatch):
    """R7 (2.4/2.5): rating flag ON only -> _jsonld_facts == {"rating": ...}
    rescaled to 5 by the declared bestRating; no image_url."""
    _leaf()
    monkeypatch.setenv(RATING_FLAG, "true")
    monkeypatch.setenv(IMG_FLAG, "false")
    node = _full_node(aggregateRating=dict({"@type": "AggregateRating"}, **agg))
    result = _extract(_html(node))
    assert result is not None
    assert result.get("_jsonld_facts") == {"rating": expected}
    assert "image_url" not in result


def test_d08_r8_pharmacy_producer_on(monkeypatch):
    """R8 (3.2(d)): _try_pharmacy_urls with both flags ON stamps its dict the
    same way (first allowed first-party image of the pharmacy page, the facts)."""
    _leaf()
    monkeypatch.setenv(IMG_FLAG, "true")
    monkeypatch.setenv(RATING_FLAG, "true")
    node = _full_node(image=[IMG_FIMGS, "https://pharmacy-a.example.com/img/p.png"],
                      aggregateRating={"@type": "AggregateRating", "ratingValue": "4.4",
                                       "reviewCount": "120"})
    result = _pharmacy(monkeypatch, _html(node))
    assert result is not None and result.get("source_method") == "local_bhd"
    assert result.get("image_url") == "https://pharmacy-a.example.com/img/p.png"
    assert result.get("_jsonld_facts") == {
        "gtin": GTIN13_OK, "sku": "SKU-A1", "size": "100 ml",
        "rating": {"value": 4.4, "count": 120},
    }


@pytest.mark.parametrize("page_img,expected", [
    ("https://store-a.example.com/img/hero.jpg", "https://store-a.example.com/img/hero.jpg"),
    ("http://store-a.example.com/img/hero.jpg", CASCADE_IMG),
    (IMG_OFF_LIST, CASCADE_IMG),
    (IMG_FIMGS, CASCADE_IMG),
], ids=["https-first-party", "http", "off-allowlist", "denied"])
@pytest.mark.asyncio
async def test_d08_r9_piggyback_on(page_img, expected, monkeypatch):
    """R9 (2.6): ON, through the real _fetch_product_data, only an allowed page
    image replaces the cascade image (base promotes http and off-allowlist)."""
    _leaf()
    monkeypatch.setenv(IMG_FLAG, "true")
    result = await _scs_fetch(page_img, CASCADE_IMG)
    assert result.get("image_url") == expected


R10_CASES = [
    ("empty", [], "https://store-a.example.com/p/x", True),
    ("disallow-prefix", [["disallow", "/p/"]], "https://store-a.example.com/p/x", False),
    ("longest-allow", [["allow", "/p/x"], ["disallow", "/p/"]], "https://store-a.example.com/p/x", True),
    ("allow-wins-tie", [["disallow", "/p/"], ["allow", "/p/"]], "https://store-a.example.com/p/x", True),
    ("dollar-anchor", [["disallow", "/*.json$"]], "https://store-a.example.com/products.json", False),
    ("dollar-with-query", [["disallow", "/*.json$"]],
     "https://store-a.example.com/products.json?page=2", True),
    ("star-wildcard", [["disallow", "/p/*/buy"]], "https://store-a.example.com/p/x/buy", False),
    ("query-counts", [["disallow", "/search?q="]], "https://store-a.example.com/search?q=oud", False),
    ("malformed-action", [["allow", "/"], ["maybe", "/p/"]], "https://store-a.example.com/p/x", False),
    ("malformed-arity", [["disallow"]], "https://store-a.example.com/p/x", False),
    ("malformed-type", ["disallow /p/"], "https://store-a.example.com/p/x", False),
]


@pytest.mark.parametrize("case", R10_CASES, ids=lambda c: c[0])
def test_d08_r10_rules_allow(case):
    """R10 (2.3 item 4): longest match, allow wins a tie, empty -> allow, the
    $ and * patterns, path + query; FAIL-CLOSED on a malformed rule."""
    _name, rules, url, expected = case
    assert _leaf_fn("rules_allow")(rules, url) is expected


@pytest.mark.parametrize("label,entry,now", [
    ("fresh", _entry(), FIXED_NOW),
    ("inside-grace", _entry(), datetime(2026, 10, 30, 23, 0, 0, tzinfo=timezone.utc)),
    ("no-challenge-key", {k: v for k, v in _entry().items() if k != "challenge"}, FIXED_NOW),
    ("challenge-parked-past", _entry(challenge={"vendor": "cloudflare",
                                                "parked_until": "2026-10-20T00:00:00Z"}),
     FIXED_NOW),
])
def test_d08_r11_host_rule_allows(label, entry, now):
    """R11 (2.3): a live, fresh (before next_reread + 24 h), both-agents-allow,
    untruncated, unparked entry -> True."""
    fn = _leaf_fn("rating_host_allowed")
    assert fn(entry, PAGE_URL, now) is True, label


def _r12_cases():
    late = datetime(2026, 10, 31, 1, 0, 0, tzinfo=timezone.utc)
    no_next = _robots()
    del no_next["next_reread"]
    return [
        ("none", None, PAGE_URL, FIXED_NOW),
        ("deny", _entry(deny=True), PAGE_URL, FIXED_NOW),
        ("blocked", _entry(status="blocked"), PAGE_URL, FIXED_NOW),
        ("candidate", _entry(status="candidate"), PAGE_URL, FIXED_NOW),
        ("state-disallow", _entry(robots=_robots(state="disallow")), PAGE_URL, FIXED_NOW),
        ("state-unreadable", _entry(robots=_robots(state="unreadable")), PAGE_URL, FIXED_NOW),
        ("expired", _entry(), PAGE_URL, late),
        ("missing-next-reread", _entry(robots=no_next), PAGE_URL, FIXED_NOW),
        ("fetched-at-garbage", _entry(robots=_robots(fetched_at="not-a-date")), PAGE_URL, FIXED_NOW),
        ("star-disallows", _entry(robots=_robots(rules={
            "qarenbot": [["disallow", "/admin"]], "star": [["disallow", "/products/"]]})),
         PAGE_URL, FIXED_NOW),
        ("qarenbot-disallows", _entry(robots=_robots(rules={
            "qarenbot": [["disallow", "/products/"]], "star": [["allow", "/"]]})),
         PAGE_URL, FIXED_NOW),
        ("truncated", _entry(robots=_robots(rules_truncated=True)), PAGE_URL, FIXED_NOW),
        ("parked-future", _entry(challenge={"vendor": "cloudflare",
                                            "parked_until": "2026-11-05T00:00:00Z"}),
         PAGE_URL, FIXED_NOW),
        ("vendor-no-parked-until", _entry(challenge={"vendor": "akamai"}), PAGE_URL, FIXED_NOW),
        ("denied-host", _entry(), "https://www.fragrantica.com/perfume/x.html", FIXED_NOW),
        ("robots-not-dict", _entry(robots=None), PAGE_URL, FIXED_NOW),
        ("malformed-rules", _entry(robots=_robots(rules={"qarenbot": [["maybe", "/"]],
                                                         "star": [["allow", "/"]]})),
         PAGE_URL, FIXED_NOW),
    ]


@pytest.mark.parametrize("case", _r12_cases(), ids=lambda c: c[0])
def test_d08_r12_host_rule_refuses(case):
    """R12 (2.3): one failing condition each -> False (fail-closed)."""
    fn = _leaf_fn("rating_host_allowed")
    _label, entry, url, now = case
    assert fn(entry, url, now) is False


@pytest.mark.asyncio
async def test_d08_r13_default_seam_no_rating(monkeypatch):
    """R13 (2.3/2.7): rating ON with the DEFAULT seam (no reader until D14): no
    jsonld_rating, the rating stays None and the GPT fallback is NOT applied."""
    mod = _leaf()
    seam = getattr(mod, "ROBOTS_ENTRY_LOOKUP", None)
    assert callable(seam), "D08: ROBOTS_ENTRY_LOOKUP seam missing"
    assert seam(HOST) is None, "the default seam must answer no entry"
    monkeypatch.setenv(RATING_FLAG, "true")
    result = await _scs_fetch(facts=CH1_FACTS, rating_data=NO_PROVIDER,
                              reviews={"review_summary": {}, "average_rating": 4.2})
    assert "jsonld_rating" not in result
    assert result.get("rating") is None
    assert result.get("rating_derived") is not True
    assert result.get("rating_source") is None


CH1_LITERAL = {
    "value": 4.4, "count": 120, "source": HOST, "url": SCS_PRICE_URL,
    "extract_method": "jsonld_aggregate_rating",
}


@pytest.mark.asyncio
async def test_d08_r14_channel1_fills_empty_slot(monkeypatch):
    """R14 (2.7 step 2, R-G1-2): an allowing seam + no provider rating ->
    jsonld_rating == the literal and the EMPTY slot is filled (rating_verified
    False, rating_derived never set, retrieved_at from the _now seam)."""
    calls = _seam_recorder(monkeypatch, _entry)
    monkeypatch.setenv(RATING_FLAG, "true")
    result = await _scs_fetch(facts=CH1_FACTS, rating_data=NO_PROVIDER,
                              reviews={"review_summary": {}, "average_rating": 4.2})
    assert result.get("jsonld_rating") == CH1_LITERAL
    assert result.get("rating") == 4.4
    assert result.get("review_count") == 120
    assert result.get("rating_verified") is False
    assert result.get("rating_source") == {
        "name": "store-a.example.com (product page)",
        "url": SCS_PRICE_URL,
        "retrieved_at": FIXED_NOW_Z,
        "extract_method": "jsonld_aggregate_rating",
        "confidence": "medium",
    }
    assert "rating_derived" not in result
    assert HOST in calls


PROVIDER_UNVERIFIED = {
    "rating": 4.1,
    "review_count": 1500,
    "rating_verified": False,
    "rating_source": {"name": "test-unverified", "url": None},
}


@pytest.mark.parametrize("provider", [PROVIDER, PROVIDER_UNVERIFIED],
                         ids=["verified", "unverified"])
@pytest.mark.asyncio
async def test_d08_r15_provider_rating_wins(provider, monkeypatch):
    """R15 (2.7 step 2, R-G1-2 / orchestrator mutant 2): with a provider rating
    already in the slot (verified or not), channel 1 never overwrites it;
    jsonld_rating is still added beside it."""
    _seam_recorder(monkeypatch, _entry)
    monkeypatch.setenv(RATING_FLAG, "true")
    result = await _scs_fetch(facts=CH1_FACTS, rating_data=provider,
                              reviews={"review_summary": {}, "average_rating": 4.2})
    assert result.get("jsonld_rating") == CH1_LITERAL
    assert result.get("rating") == provider["rating"]
    assert result.get("review_count") == provider["review_count"]
    assert result.get("rating_verified") is provider["rating_verified"]
    assert result.get("rating_source") == provider["rating_source"]
    assert "rating_derived" not in result


def test_d08_r16_no_derive_on(monkeypatch):
    """R16 (2.7 step 4): rating ON -> build_comparison_response no longer derives
    a rating from the scores: pd rating stays None, no rating_derived key, and
    the overview / reviews rating and the reviews rating_source are None."""
    _leaf()
    monkeypatch.setenv(RATING_FLAG, "true")
    p0 = _rb_product("Testhaus Oud Noir", None, None, None)
    p1 = _rb_product("Otherhaus Rose Veil", 4.6, 100, dict(OTHER_SOURCE))
    resp = _build([p0, p1])
    assert p0.get("rating") is None
    assert "rating_derived" not in p0
    assert resp["overview"]["products"][0].get("rating") is None
    assert resp["reviews"]["products"][0].get("rating") is None
    assert resp["reviews"]["products"][0].get("rating_source") is None


def test_d08_r17_reviews_projection_jsonld_rating(monkeypatch):
    """R17 (2.7 step 4): ON -> reviews.products[i].jsonld_rating is present iff
    the product carries it; the overview product keys are unchanged."""
    _leaf()
    ch1 = dict(CH1_LITERAL)

    def _pair():
        return [
            _rb_product("Testhaus Oud Noir", 4.4, 120, {"name": "x"}, jsonld_rating=dict(ch1)),
            _rb_product("Otherhaus Rose Veil", 4.6, 100, dict(OTHER_SOURCE)),
        ]

    monkeypatch.setenv(RATING_FLAG, "false")
    off = _build(_pair())
    monkeypatch.setenv(RATING_FLAG, "true")
    on = _build(_pair())
    assert on["reviews"]["products"][0].get("jsonld_rating") == ch1
    assert "jsonld_rating" not in on["reviews"]["products"][1]
    for i in (0, 1):
        assert set(on["overview"]["products"][i]) == set(off["overview"]["products"][i])
    assert set(on["reviews"]["products"][0]) - set(off["reviews"]["products"][0]) == {"jsonld_rating"}


def test_d08_r18_prompt_variant(monkeypatch):
    """R18 (2.7 step 5): REVIEWS_EXTRACTION_SYSTEM_NO_RATING = the base constant
    with exactly the two ask lines removed, still fenced; the reviews call sends
    it when the flag is ON."""
    es = _es()
    variant = getattr(es, "REVIEWS_EXTRACTION_SYSTEM_NO_RATING", None)
    assert isinstance(variant, str), "D08: REVIEWS_EXTRACTION_SYSTEM_NO_RATING missing"
    base = es.REVIEWS_EXTRACTION_SYSTEM
    assert base.count(LINE_AVG) == 1 and base.count(LINE_TOTAL) == 1
    assert variant == base.replace(LINE_AVG, "").replace(LINE_TOTAL, "")
    assert es.SEARCH_RESULTS_GUARD in variant
    assert "average_rating" not in variant and "total_reviews" not in variant
    monkeypatch.setenv(RATING_FLAG, "true")
    assert _reviews_system_sent(monkeypatch) == variant


def test_d08_r19_normaliser_belt(monkeypatch):
    """R19 (2.7 step 5): ON, a disobedient model's numbers never survive."""
    _leaf()
    monkeypatch.setenv(RATING_FLAG, "true")
    out = _es()._normalize_review_response(
        {"average_rating": 4.2, "total_reviews": 900, "review_summary": {}})
    assert out.get("average_rating") is None
    assert out.get("total_reviews") is None


_TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".sql", ".yaml", ".yml", ".toml", ".cfg",
                  ".ini", ".sh", ".js", ".ts"}


def test_d08_r20_judgeme_deleted():
    """R20 (3.6, R-G1-4): judgeme_service.py, its pin file and its fixtures are
    deleted unflagged; no file under app/ or scripts/ names judgeme_service."""
    assert importlib.util.find_spec("app.services.judgeme_service") is None
    hits = []
    for root in ("app", "scripts"):
        for path in (REPO / root).rglob("*"):
            if "__pycache__" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "judgeme_service" in text:
                hits.append(path.relative_to(REPO).as_posix())
    assert hits == []
    assert not (REPO / "tests" / "fixtures" / "judgeme_c5").exists()
    assert not (REPO / "tests" / "test_m6_c5_judgeme_html_reviews.py").exists()


@pytest.mark.parametrize("size_value,expected", [
    ("100 ml", "100 ml"),
    ({"@type": "QuantitativeValue", "value": 100, "unitText": "ml"}, "100 ml"),
], ids=["text", "quantitative-value"])
def test_d08_r21_candidate_additions_on(size_value, expected, monkeypatch):
    """R21 (2.5): image ON -> cand carries the node's size text; rating ON ->
    aggregate_rating carries the declared best_rating (10)."""
    _leaf()
    monkeypatch.setenv(IMG_FLAG, "true")
    monkeypatch.setenv(RATING_FLAG, "false")
    cand = _cand(_full_node(size=size_value))
    assert cand is not None and cand.get("size") == expected
    monkeypatch.setenv(IMG_FLAG, "false")
    monkeypatch.setenv(RATING_FLAG, "true")
    cand = _cand(_full_node(size=size_value))
    assert cand is not None
    assert "size" not in cand
    assert (cand.get("aggregate_rating") or {}).get("best_rating") == 10.0


# ===========================================================================
# PIN rows (green at base; the literals were recorded at 6c14ac95)
# ===========================================================================
P1_LITERAL = {
    "true": {'amount': 45.5,
             'brand': 'Testhaus',
             'capture_outcome': 'ok',
             'confidence': 1.0,
             'currency': 'BHD',
             'estimated': False,
             'in_stock': True,
             'name': 'Testhaus Oud Noir Eau de Parfum 100ml',
             'original_currency': 'BHD',
             'retailer': 'store-a.example.com',
             'size': '100ml',
             'source_method': 'page_scrape',
             'url': 'https://store-a.example.com/products/oud-noir-100ml'},
    "false": {'amount': 45.5,
              'capture_outcome': 'ok',
              'confidence': 1.0,
              'currency': 'BHD',
              'estimated': False,
              'in_stock': True,
              'original_currency': 'BHD',
              'retailer': 'store-a.example.com',
              'size': '100ml',
              'source_method': 'page_scrape',
              'url': 'https://store-a.example.com/products/oud-noir-100ml'},
}


@pytest.mark.parametrize("guards", [None, "true"], ids=_vid)
@pytest.mark.parametrize("gate", ["true", "false"])
@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
def test_d08_p1_reduced_result_off_literal(off, gate, guards, monkeypatch):
    """P1 (2.9): the extract_price_from_html result for a node carrying image /
    gtin / sku / size / aggregateRating equals the base LITERAL, both gate modes,
    ENABLE_DATA_GUARDS_V2 both ways, both D08 flags OFF in every spelling."""
    rec = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    _set(monkeypatch, "ENABLE_DATA_GUARDS_V2", guards)
    result = _extract(_html(_full_node()))
    assert result == P1_LITERAL[gate]
    _assert_untouched(rec)


P2_LITERAL = {'amount': 45.5,
              'confidence': 1.0,
              'currency': 'BHD',
              'estimated': False,
              'in_stock': True,
              'original_currency': 'BHD',
              'retailer': 'Pharmacy A',
              'source_method': 'local_bhd',
              'title': 'Testhaus Oud Noir Eau de Parfum 100ml',
              'url': 'https://pharmacy-a.example.com/p/oud-noir-100ml'}


@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
def test_d08_p2_pharmacy_off_literal(off, monkeypatch):
    """P2 (2.9): _try_pharmacy_urls returns the base literal dict."""
    rec = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    node = _full_node(image=[IMG_FIMGS, "https://pharmacy-a.example.com/img/p.png"])
    assert _pharmacy(monkeypatch, _html(node)) == P2_LITERAL
    _assert_untouched(rec)


P3_LITERAL = {
    "true": {'aggregate_rating': {'rating_value': 8.0, 'review_count': 120},
             'amount': 45.5,
             'brand': 'Testhaus',
             'currency': 'BHD',
             'description': 'A dark oud.',
             'gtin': GTIN13_OK,
             'image': ['http://store-a.example.com/img/a.jpg',
                       'https://fimgs.net/mdimg/perfume/375x500.1.jpg',
                       'https://store-a.example.com/img/c.jpg'],
             'in_stock': True,
             'name': 'Testhaus Oud Noir Eau de Parfum 100ml',
             'sku': 'SKU-A1'},
    "false": {'aggregate_rating': {'rating_value': 8.0, 'review_count': 120},
              'amount': 45.5,
              'brand': 'Testhaus',
              'currency': 'BHD',
              'description': 'A dark oud.',
              'gtin': GTIN13_OK,
              'image': ['http://store-a.example.com/img/a.jpg',
                        'https://fimgs.net/mdimg/perfume/375x500.1.jpg',
                        'https://store-a.example.com/img/c.jpg'],
              'in_stock': True,
              'name': 'Testhaus Oud Noir Eau de Parfum 100ml',
              'sku': 'SKU-A1'},
}


@pytest.mark.parametrize("gate", ["true", "false"])
@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
def test_d08_p3_candidate_off_literal(off, gate, monkeypatch):
    """P3 (2.5/2.9): the extract_jsonld_price candidate equals the base literal
    (no size, no best_rating)."""
    rec = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    cand = _cand(_full_node())
    assert cand == P3_LITERAL[gate]
    assert "size" not in cand and "best_rating" not in cand.get("aggregate_rating", {})
    _assert_untouched(rec)


P4_PAGE_IMAGES = {
    "http": "http://store-a.example.com/img/hero.jpg",
    "https-first-party": "https://store-a.example.com/img/hero.jpg",
    "off-allowlist": IMG_OFF_LIST,
    "padded": " https://store-a.example.com/img/hero.jpg",
}
P4_LITERAL = {'true': {'http': 'http://store-a.example.com/img/hero.jpg',
                       'https-first-party': 'https://store-a.example.com/img/hero.jpg',
                       'off-allowlist': 'https://img.other-b.example.net/hero.jpg',
                       'padded': 'https://store-a.example.com/img/hero.jpg'},
              'unset': {'http': 'http://store-a.example.com/img/hero.jpg',
                        'https-first-party': 'https://store-a.example.com/img/hero.jpg',
                        'off-allowlist': 'https://img.other-b.example.net/hero.jpg',
                        'padded': 'https://cdn-a.example.com/cascade.jpg'}}


@pytest.mark.parametrize("guards", [None, "true"], ids=_vid)
@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
@pytest.mark.asyncio
async def test_d08_p4_piggyback_off(off, guards, monkeypatch):
    """P4 (2.6/2.9): through the real _fetch_product_data, an http, an https
    first-party, an off-allowlist and a padded page image each give the base
    outcome (recorded literals), ENABLE_DATA_GUARDS_V2 unset and true."""
    rec = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    _set(monkeypatch, "ENABLE_DATA_GUARDS_V2", guards)
    for label, img in P4_PAGE_IMAGES.items():
        result = await _scs_fetch(img, CASCADE_IMG)
        assert result.get("image_url") == P4_LITERAL[guards or "unset"][label], label
    _assert_untouched(rec)


# --- P5: the flag-OFF rating golden ----------------------------------------
P5_AVG = {"present": 4.2, "absent": None, "out_of_range": 7.5, "string": "4.3"}
P5_PROVIDER_SOURCE = {"name": "Retailer B", "url": "https://store-b.example.com/p/oud",
                      "retrieved_at": "2026-10-29T00:00:00Z",
                      "extract_method": "serper_shopping", "confidence": "high"}


def _p5_records():
    out = []
    n = 0
    for provider in (True, False):
        for avg in ("present", "absent", "out_of_range", "string"):
            for facts in (True, False):
                n += 1
                out.append({"id": "g%02d" % n, "provider": provider, "avg": avg, "facts": facts})
    return out


def _p5_inputs(rec):
    rating_data = (
        {"rating": 4.6, "review_count": 100, "rating_verified": True,
         "rating_source": dict(P5_PROVIDER_SOURCE)}
        if rec["provider"] else dict(NO_PROVIDER)
    )
    reviews = {"review_summary": {}}
    if rec["avg"] != "absent":
        reviews["average_rating"] = P5_AVG[rec["avg"]]
    facts = CH1_FACTS if rec["facts"] else None
    return rating_data, reviews, facts


async def _p5_observe(rec):
    """The rating block (real _fetch_product_data) then the overview / reviews
    projections (real build_comparison_response) for one golden record."""
    rating_data, reviews, facts = _p5_inputs(rec)
    result = await _scs_fetch(facts=facts, rating_data=rating_data, reviews=reviews)
    block = [
        result.get("rating"), result.get("review_count"), result.get("rating_verified"),
        result.get("rating_source"), result.get("rating_derived"), "jsonld_rating" in result,
    ]
    p0 = _rb_product("Testhaus Oud Noir", result.get("rating"), result.get("review_count"),
                     result.get("rating_source"), rating_verified=result.get("rating_verified"))
    if "rating_derived" in result:
        p0["rating_derived"] = result["rating_derived"]
    if "jsonld_rating" in result:
        p0["jsonld_rating"] = result["jsonld_rating"]
    p1 = _rb_product("Otherhaus Rose Veil", 4.6, 100, dict(OTHER_SOURCE))
    resp = _build([p0, p1])
    ov = resp["overview"]["products"][0]
    rv = resp["reviews"]["products"][0]
    projection = [
        ov.get("rating"), ov.get("review_count"), rv.get("rating"), rv.get("review_count"),
        rv.get("rating_source"), "jsonld_rating" in rv, p0.get("rating"), p0.get("rating_derived"),
    ]
    return json.loads(json.dumps({"block": block, "projection": projection}))


@pytest.mark.parametrize("off", GOLDEN_SPELLINGS, ids=_vid)
@pytest.mark.asyncio
async def test_d08_p5_rating_golden_sequence(off, monkeypatch):
    """P5 (2.9): the ordered rating-block tuples (rating, review_count,
    rating_verified, rating_source, rating_derived, jsonld_rating present) and
    the overview / reviews projections equal the golden recorded at base, for
    16 synthetic products (provider x reviews average x facts), flags OFF."""
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    records = golden["records"]
    assert [r["id"] for r in records] == [r["id"] for r in _p5_records()]
    rec_calls = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    for rec in records:
        observed = await _p5_observe(rec)
        assert observed == {"block": rec["block"], "projection": rec["projection"]}, rec["id"]
    _assert_untouched(rec_calls)


@pytest.mark.parametrize("off", [None, "false"], ids=_vid)
@pytest.mark.asyncio
async def test_d08_p6_seam_never_called_off(off, monkeypatch):
    """P6 (2.8/2.9): across the P1-P5 workloads the ALLOWING recorder seam and
    the leaf entry points see zero calls with the flags OFF."""
    rec = _install_off_recorders(monkeypatch)
    _both_off(monkeypatch, off)
    for gate in ("true", "false"):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
        _extract(_html(_full_node()))
        _cand(_full_node())
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    for rec_in in _p5_records()[:4]:
        await _p5_observe(rec_in)
    await _scs_fetch("http://store-a.example.com/img/hero.jpg", CASCADE_IMG, facts=CH1_FACTS,
                     rating_data=NO_PROVIDER)
    _assert_untouched(rec)
    p0 = _rb_product("Testhaus Oud Noir", None, None, None)
    _build([p0, _rb_product("Otherhaus Rose Veil", 4.6, 100, dict(OTHER_SOURCE))])
    _assert_untouched(rec)


P7_SHA256 = "46791e1b346c8be5780004d0245f40bc0947d4445f7950aae04224b2d64987e3"


@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
def test_d08_p7_prompt_off_sha(off, monkeypatch):
    """P7 (2.9): the reviews system prompt bytes are the base bytes and the call
    sends exactly that string with the flag OFF."""
    _both_off(monkeypatch, off)
    es = _es()
    digest = hashlib.sha256(es.REVIEWS_EXTRACTION_SYSTEM.encode("utf-8")).hexdigest()
    assert digest == P7_SHA256
    assert _reviews_system_sent(monkeypatch) == es.REVIEWS_EXTRACTION_SYSTEM


@pytest.mark.parametrize("off", OFF_SPELLINGS, ids=_vid)
def test_d08_p8_normaliser_off(off, monkeypatch):
    """P8 (2.9): flag OFF the normaliser keeps average_rating and total_reviews."""
    _both_off(monkeypatch, off)
    out = _es()._normalize_review_response(
        {"average_rating": 4.2, "total_reviews": 900, "review_summary": {}})
    assert out.get("average_rating") == 4.2
    assert out.get("total_reviews") == 900


@pytest.mark.parametrize("gate", ["true", "false"])
def test_d08_p9_wide_pin_both_states(gate, monkeypatch):
    """P9 (Q3): the eight wide keys stay out of the extract_price_from_html
    result with BOTH D08 flags ON as well; the only keys ON may add over OFF are
    image_url and _jsonld_facts (the internal key keeps its _ prefix)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    _both_off(monkeypatch, "false")
    off_result = _extract(_html(_full_node()))
    monkeypatch.setenv(IMG_FLAG, "true")
    monkeypatch.setenv(RATING_FLAG, "true")
    on_result = _extract(_html(_full_node()))
    assert on_result is not None and off_result is not None
    for key in WIDE_KEYS:
        assert key not in on_result, key
    assert set(on_result) - set(off_result) <= {"image_url", "_jsonld_facts"}
    for key, value in off_result.items():
        assert on_result.get(key) == value, key

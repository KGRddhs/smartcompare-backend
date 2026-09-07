"""Issue #55 — `DELETE /api/v1/text/cache` must clear what the LIVE price path
writes, and must report honestly what it did and did not delete.

Two independent changes are pinned here:

1. UNFLAGGED defect repair — `extraction_service.parse_product_query` returns
   `(result, usage)`. The flush route treated it as a bare dict, so
   `parsed.get(...)` raised AttributeError on EVERY real call. Pinned by driving
   the route with the REAL tuple contract.

2. `ENABLE_FLUSH_LIVE_PRICE_KEY` (default OFF) — flag ON deletes the size-aware
   L1 price key(s) `_get_price` actually writes, the `nogenuine:` sentinel
   derived from each, and the L2 `product_prices` rows; reports `success` only
   when EVERY leg landed; and accepts the operator's category chip. Flag OFF is
   byte-identical to the pre-#55 body (three legacy keys, `{"key","deleted"}`
   entries, no extra top-level fields, no Supabase call, no existence probe) —
   including when the new `category` query param is supplied.

HOW THE KEY CLAIM IS PINNED (rewritten after the flag-discipline review of the
first #55 commit). The original `_expected_price_keys` helper re-implemented
`_flush_price_cache_keys` line for line, so every flag-ON assertion could only
agree with itself and no test ever observed the key the LIVE path writes — a
wrong recipe passed. There is now no copy of the recipe anywhere in this file:

  * `_capture_live_price_key` DRIVES the real writer — `_fetch_product_data` ->
    `_get_price` with the whole cascade stubbed empty — and records the key
    handed to `set_cached`. Every "this is the live key" assertion compares the
    route's output against THAT.
  * `_flush_keys` calls the production helper itself, and is used only for
    wiring assertions (the route flushes what the helper returns).

Free tier only: nothing here touches the network, Redis or Supabase for real.
"""
import asyncio
import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import text_routes
from app.main import app
from app.services.extraction_service import (
    get_price_cache_key,
    get_reviews_cache_key,
    get_specs_cache_key,
)
from app.services.price_service import negative_cache_key

ADMIN_KEY = "test-admin-key-flush-55"
REGION = "bahrain"

# A query carrying BOTH identity axes the flush exists to repair
# (concentration + volume) — the size-aware key and the legacy key diverge here.
IDENTITY_Q = "dior sauvage edp 100ml"
IDENTITY_PRODUCT = {
    "brand": "Dior",
    "name": "Sauvage",
    "variant": "100ml",
    "category": "fragrances",
    "search_query": "Dior Sauvage EDP 100ml",
}

# A plain product with no size / storage / concentration / qualifier anywhere:
# `build_size_aware_price_cache_key` falls back to the legacy builder, so all
# three candidates collapse onto ONE key.
PLAIN_Q = "nido milk powder"
PLAIN_PRODUCT = {
    "brand": "Nido",
    "name": "Milk Powder",
    "variant": None,
    "category": "grocery",
    "search_query": "Nido Milk Powder",
}

# --- fixtures that exercise the three ways the flush recipe could DRIFT from
# --- the live writer.  Each was MEASURED against `_capture_live_price_key`.

# (a) rung 2 — the parser normalized the volume OUT of `search_query`, the raw
# operator query still carries it, and `name` carries the concentration. The
# three rungs therefore yield THREE distinct keys (rung 1 token "edp", rung 2
# token "edp.100ml", rung 3 the legacy size-agnostic hash), which is the case
# the first version of this file never produced — rung 2 could be deleted whole
# and all 28 nodes stayed green.
RUNG2_Q = "dior sauvage edp 100ml"
RUNG2_PRODUCT = {
    "brand": "Dior",
    "name": "Sauvage EDP",
    "variant": None,
    "category": "fragrances",
    "search_query": "Dior Sauvage EDP",
}

# (b) the CATEGORY divergence. The LLM emitted "other"; the user's chip said
# electronics, so `_resolve_pair_category` returned "electronics" and the A3
# write-back stamped it onto the product dict the live path keys under.
# `category` is threaded into exactly ONE axis of the key — the weight branch of
# `size_variant_token`, where a bare cellular generation is a network generation
# under electronics and 5 grams under anything else — so the demo carries both a
# "5G" and a listing weight (GCC marketplace titles routinely do).
CHIP_Q = "nord ce 5g 190g"
CHIP_PRODUCT_AS_PARSED = {          # what `parse_product_query` returns
    "brand": "OnePlus",
    "name": "Nord CE",
    "variant": None,
    "category": "other",            # the LLM abstained
    "search_query": "Nord CE 5G 190g",
}
CHIP_CATEGORY = "electronics"       # the chip -> `category_used` -> A3 write-back

# (c) a PRESENT-but-falsy `search_query`. `_fetch_product_data` uses
# `.get(key, default)`, so "" stays "" and the identity text is empty; the first
# #55 recipe used `or` and substituted the brand-carrying fallback, whose brand
# words hit the electronics qualifier set ("Pro") and changed the token.
FALSY_SQ_Q = "pro plan dog food 3kg"
FALSY_SQ_PRODUCT = {
    "brand": "Pro Plan",
    "name": "Dog Food 3kg",
    "variant": None,
    "category": "other",
    "search_query": "",
}


@pytest.fixture(autouse=True)
def _admin_env():
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}):
        yield


@pytest.fixture()
def client():
    return TestClient(app)


def _parse_mock(product):
    """`parse_product_query` returns (result, usage) — the REAL contract."""
    return AsyncMock(return_value=({"products": [product]}, {"prompt_tokens": 0}))


def _supabase_mock(data=None, exc=None):
    c = MagicMock()
    c.table.return_value = c
    c.delete.return_value = c
    c.eq.return_value = c
    if exc is not None:
        c.execute.side_effect = exc
    else:
        c.execute.return_value = MagicMock(data=data if data is not None else [])
    return c


class _FakeRedis:
    """Minimal stand-in for the module-level `cache_service.redis_client`.

    `fail_keys` makes `delete` RAISE for those keys — the Upstash 5xx/timeout
    case, where `cache_service.delete_cached` swallows the exception and returns
    False while `cache_configured` is still True.
    """

    def __init__(self, fail_keys=()):
        self.store = {}
        self.fail_keys = set(fail_keys)
        self.deleted = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, key):
        if key in self.fail_keys:
            raise RuntimeError("upstash 503 on DELETE")
        self.deleted.append(key)
        self.store.pop(key, None)


def _flush(client, q, product, env=None, supabase=None, redis=None, category=None):
    """Drive DELETE /text/cache with everything external mocked."""
    stack = []
    env = env or {}
    params = {"q": q}
    if category is not None:
        params["category"] = category
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY, **env}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(product)), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=supabase if supabase is not None else _supabase_mock()) as sb, \
            patch("app.services.cache_service.redis_client", redis):
        resp = client.delete(
            "/api/v1/text/cache", params=params,
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        stack.append(sb)
    return resp, stack[0]


def _flush_keys(q, product, category=None):
    """The key set the ROUTE will flush, from the PRODUCTION helper itself.

    Deliberately NOT a re-implementation (that was the defect the flag-discipline
    review found in the first version of this file: `_expected_price_keys` copied
    `_flush_price_cache_keys` line for line, so every flag-ON assertion agreed
    with itself and a wrong recipe passed). This only pins WIRING — that the
    route flushes what the helper returns. The recipe itself is pinned against
    the LIVE WRITER by `_capture_live_price_key` below.
    """
    return text_routes._flush_price_cache_keys(
        product["brand"], product["name"], product["variant"], REGION, q, product,
        category=category,
    )


def _capture_live_price_key(product_info, region=REGION):
    """Run the REAL live price path and report the L1 price key it WRITES.

    This is the only honest source of "the key the live path writes": nothing
    here rebuilds it. `StructuredComparisonService._fetch_product_data` picks the
    `category` / `search_query` it will use, hands them to `_get_price`, and
    `_get_price` builds the cache key and writes it — the harness just records
    the key handed to `set_cached` (and to `set_negative_cache`, the sentinel).

    Everything external is stubbed to an empty/None result (the recipe is lifted
    from the race harness in tests/test_genuine_price_clobber_guard.py) so the
    whole Tier-1 -> Tier-1.5 -> Tier-3 cascade runs offline and terminates in the
    Tier-3 estimate write. No network, no Redis, no Supabase, no OpenAI.

    `product_info` is the dict the ORCHESTRATOR hands `_fetch_product_data`,
    i.e. AFTER the A3 write-back has stamped the pair-resolved `category` onto
    it (scs.py `for _p in products: _p["category"] = category_used`) — which is
    exactly why the flush needs the chip.
    """
    from app.services import structured_comparison_service as scs

    seen = {"reads": [], "writes": [], "sentinels": []}

    def _get_cached(key):
        seen["reads"].append(key)
        return None

    with ExitStack() as stack:
        def _patch(target, value):
            stack.enter_context(patch.object(scs, target, value))

        _patch("get_cached", _get_cached)
        _patch("set_cached",
               lambda k, v, t: seen["writes"].append((k, v, t)) or True)
        _patch("set_negative_cache",
               lambda k, v, t: seen["sentinels"].append((k, v, t)) or True)
        _patch("delete_cached", lambda k: True)
        for _src in ("get_algolia_sources_for_category", "get_unbxd_sources_for_category",
                     "get_shopify_sources_for_category", "get_noon_sources_for_category"):
            _patch(_src, lambda cat: [])
        _patch("search_product_prices", AsyncMock(
            return_value={"shopping": [], "organic": [], "shopping_region": "bh"}))
        _patch("get_official_domain", lambda *a, **kw: None)
        _patch("fetch_shopify_price", AsyncMock(return_value=None))
        _patch("search_web", AsyncMock(return_value={"organic": []}))
        _patch("fan_out_price_lookup", AsyncMock(return_value={"best": None}))
        _patch("search_price_organic", AsyncMock(
            return_value={"organic": [], "knowledge_graph": None}))
        _patch("extract_price", AsyncMock(return_value=(None, {})))
        _patch("extract_price_from_training_data", AsyncMock(
            return_value=({"amount": 290.0, "currency": "BHD"}, {})))
        _patch("get_product_image_url", AsyncMock(return_value=None))
        stack.enter_context(patch(
            "app.services.product_data_service.get_cached_price",
            AsyncMock(return_value=None),
        ))

        async def _drive():
            svc = scs.StructuredComparisonService()
            svc._save_price_to_db = MagicMock()
            return await svc._fetch_product_data(
                dict(product_info), region,
                include_specs=False, include_reviews=False,
            )

        asyncio.run(_drive())

    price_writes = [w for w in seen["writes"] if str(w[0]).startswith("price:")]
    assert len(price_writes) == 1, (
        f"live path did not write exactly one L1 price key: {seen['writes']}"
    )
    key = price_writes[0][0]
    assert seen["reads"] and seen["reads"][0] == key, (
        "the live path READ a different key than it wrote — harness is lying "
        f"(read {seen['reads'][:1]}, wrote {key})"
    )
    return {
        "key": key,
        "sentinels": [s[0] for s in seen["sentinels"]],
    }


# ---------------------------------------------------------------------------
# 1. UNFLAGGED — the tuple contract
# ---------------------------------------------------------------------------

def test_route_unpacks_the_parse_product_query_tuple(client):
    """`parse_product_query` returns (result, usage). Before the repair the route
    called `.get` on the TUPLE -> AttributeError -> the endpoint 500'd on every
    real call. Flag OFF, so ONLY the unpack is under test."""
    resp, _ = _flush(client, IDENTITY_Q, IDENTITY_PRODUCT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["product"] == "Dior Sauvage"


def test_route_still_accepts_a_bare_dict_parse_result(client):
    """The tolerant unpack keeps every existing dict-returning mock working."""
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}), \
            patch("app.services.extraction_service.parse_product_query",
                  AsyncMock(return_value={"products": [IDENTITY_PRODUCT]})), \
            patch("app.services.cache_service.redis_client", None):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True


def test_unparseable_query_still_reports_failure(client):
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY}), \
            patch("app.services.extraction_service.parse_product_query",
                  AsyncMock(return_value=({"products": []}, {}))):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": "???"},
            headers={"X-Admin-Key": ADMIN_KEY},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": False, "error": "Could not parse product name"}


# ---------------------------------------------------------------------------
# 2. The flag helper itself
# ---------------------------------------------------------------------------

def test_flag_defaults_off():
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("ENABLE_FLUSH_LIVE_PRICE_KEY", None)
        assert text_routes.flush_live_price_key_enabled() is False


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("1", True), ("yes", True), ("on", True), ("TRUE", True),
    ("false", False), ("0", False), ("", False), ("off", False), ("no", False),
])
def test_flag_reader_accepts_the_repo_truthy_set(value, expected):
    with patch.dict("os.environ", {"ENABLE_FLUSH_LIVE_PRICE_KEY": value}):
        assert text_routes.flush_live_price_key_enabled() is expected


def test_flag_is_read_per_call_not_cached_at_import():
    """A Railway flip must take effect without a restart."""
    with patch.dict("os.environ", {"ENABLE_FLUSH_LIVE_PRICE_KEY": "false"}):
        assert text_routes.flush_live_price_key_enabled() is False
    with patch.dict("os.environ", {"ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}):
        assert text_routes.flush_live_price_key_enabled() is True
    with patch.dict("os.environ", {"ENABLE_FLUSH_LIVE_PRICE_KEY": "false"}):
        assert text_routes.flush_live_price_key_enabled() is False


def test_flag_is_not_read_at_module_scope():
    """AST pin — comments are absent from an AST, so prose cannot satisfy this.
    The env read must live INSIDE the helper function, never at module level.

    REWRITTEN (test-quality review finding #5): the first version only failed
    when the flag string appeared at module scope, so it PASSED at merge-base
    76ace90 where the flag does not exist at all — it could not tell "read per
    call inside the helper" from "flag deleted". It now carries the positive
    control the two sibling pins have (tests/test_negcache_genuine_invalidation
    .py, tests/test_genuine_price_clobber_guard.py): collect the Constant nodes,
    assert the flag IS referenced, then assert every reference sits inside
    `flush_live_price_key_enabled`.
    """
    import ast
    import inspect

    flag = "ENABLE_FLUSH_LIVE_PRICE_KEY"
    tree = ast.parse(inspect.getsource(text_routes))
    holder = [n for n in ast.walk(tree)
              if isinstance(n, ast.Constant) and n.value == flag]
    assert holder, f"{flag} not referenced at all"

    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "flush_live_price_key_enabled":
            fn = node
    assert fn is not None, "flag helper is not a module-level function"
    inside = {id(n) for n in ast.walk(fn) if isinstance(n, ast.Constant)}
    assert all(id(n) in inside for n in holder), (
        f"{flag} is referenced outside its per-call helper"
    )


# ---------------------------------------------------------------------------
# 3. Flag OFF — byte-identical to the pre-#55 route
# ---------------------------------------------------------------------------

def test_flag_off_body_is_the_legacy_shape_exactly(client):
    brand, name, variant = "Dior", "Sauvage", "100ml"
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "false"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached") as get_mock, \
            patch("app.services.database_service.get_admin_supabase_client") as sb:
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "success": True,
        "product": "Dior Sauvage",
        "flushed": {
            "price": {"key": get_price_cache_key(brand, name, variant, REGION),
                      "deleted": True},
            "specs": {"key": get_specs_cache_key(brand, name, variant),
                      "deleted": True},
            "reviews": {"key": get_reviews_cache_key(brand, name, variant),
                        "deleted": True},
        },
    }
    # Exactly three deletes, and NOT the size-aware key — this is the DEFECT the
    # flag exists to fix, pinned so the rollback path cannot silently drift.
    assert del_mock.call_count == 3
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    live_key = _capture_live_price_key(IDENTITY_PRODUCT)["key"]
    assert live_key not in deleted_keys
    # No existence probe, no negative sentinel, no Supabase call.
    get_mock.assert_not_called()
    sb.assert_not_called()
    assert not any(k.startswith("nogenuine:") for k in deleted_keys)


def test_flag_off_ignores_the_new_category_query_param(client):
    """The `category` param is flag-ON-only: supplying it must not move a single
    byte of the flag-OFF body, and must not change which keys are deleted."""
    def _run(category):
        with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                       "ENABLE_FLUSH_LIVE_PRICE_KEY": "false"}), \
                patch("app.services.extraction_service.parse_product_query",
                      _parse_mock(CHIP_PRODUCT_AS_PARSED)), \
                patch("app.services.cache_service.delete_cached",
                      return_value=True) as del_mock, \
                patch("app.services.database_service.get_admin_supabase_client") as sb:
            params = {"q": CHIP_Q}
            if category is not None:
                params["category"] = category
            resp = client.delete(
                "/api/v1/text/cache", params=params,
                headers={"X-Admin-Key": ADMIN_KEY},
            )
        sb.assert_not_called()
        return resp.text, [c.args[0] for c in del_mock.call_args_list]

    bare_body, bare_keys = _run(None)
    chip_body, chip_keys = _run(CHIP_CATEGORY)
    assert bare_body == chip_body, "the OFF body moved when `category` was passed"
    assert bare_keys == chip_keys == [
        get_price_cache_key("OnePlus", "Nord CE", None, REGION),
        get_specs_cache_key("OnePlus", "Nord CE", None),
        get_reviews_cache_key("OnePlus", "Nord CE", None),
    ]


# ---------------------------------------------------------------------------
# 4. Flag ON — the acceptance criteria
# ---------------------------------------------------------------------------

def test_flag_on_deletes_the_size_aware_key_for_an_identity_query(client):
    """AC1 — the key handed to delete_cached equals the key the LIVE path writes.

    The claim is now MEASURED: `live` comes out of the real
    `_fetch_product_data` -> `_get_price` write, not out of a copy of the flush
    recipe (flag-discipline review finding #2). Change any ingredient of
    `_flush_price_cache_keys` — the category source, the `search_query`
    semantics, the builder — and this goes red.
    """
    live = _capture_live_price_key(IDENTITY_PRODUCT)
    expected = _flush_keys(IDENTITY_Q, IDENTITY_PRODUCT)
    legacy = get_price_cache_key("Dior", "Sauvage", "100ml", REGION)
    assert live["key"] != legacy, (
        "fixture no longer carries an identity axis — the defect is not exercised"
    )
    assert expected[0] == live["key"], (
        "the flush recipe has DRIFTED from the live writer: flush would delete "
        f"{expected[0]}, the live path writes {live['key']}"
    )

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock()):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    assert expected[0] in deleted_keys
    # the legacy key is STILL cleared (a pre-size-aware warmed entry)
    assert legacy in deleted_keys
    body = resp.json()
    assert body["flushed"]["price"]["key"] == expected[0]


def test_flag_on_sizeless_query_issues_exactly_one_price_delete(client):
    """AC2 — when the size-aware key IS the legacy key, no duplicate delete."""
    expected = _flush_keys(PLAIN_Q, PLAIN_PRODUCT)
    legacy = get_price_cache_key("Nido", "Milk Powder", None, REGION)
    assert expected == [legacy], (
        "fixture is not identity-axis-free; pick a plainer product"
    )

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(PLAIN_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock()) as sb:
        resp = client.delete(
            "/api/v1/text/cache", params={"q": PLAIN_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    assert deleted_keys.count(legacy) == 1
    assert deleted_keys.count(negative_cache_key(legacy)) == 1
    body = resp.json()
    assert body["flushed"]["price_additional"] == []
    assert len(body["flushed"]["negative_cache"]) == 1
    # and exactly ONE L2 row delete, not three
    assert len(body["l2_product_prices"]) == 1
    assert sb.return_value.execute.call_count == 1


def test_flag_on_deletes_the_negative_cache_sentinel(client):
    """AC3 — `nogenuine:{price_key}` (TTL up to 30 days) is cleared too."""
    expected = _flush_keys(IDENTITY_Q, IDENTITY_PRODUCT)

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock()):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    for key in expected:
        assert negative_cache_key(key) in deleted_keys
    reported = [e["key"] for e in resp.json()["flushed"]["negative_cache"]]
    assert reported == [negative_cache_key(k) for k in expected]


def test_flag_on_deletes_the_l2_product_prices_row(client):
    """AC4 — a product_prices delete is issued with product_key == price_key and
    region == bahrain, so `_get_price` cannot re-promote the poisoned row."""
    expected = _flush_keys(IDENTITY_Q, IDENTITY_PRODUCT)
    sb = _supabase_mock(data=[{"id": "row-1"}, {"id": "row-2"}])

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached", return_value=True), \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=sb):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    sb.table.assert_any_call("product_prices")
    assert sb.delete.called
    eq_calls = [c.args for c in sb.eq.call_args_list]
    assert ("product_key", expected[0]) in eq_calls
    assert ("region", REGION) in eq_calls
    body = resp.json()
    assert body["l2_product_prices"][0] == {
        "product_key": expected[0], "region": REGION,
        "ok": True, "rows_deleted": 2,
    }
    assert body["success"] is False  # redis_client is None in this process
    assert body["region"] == REGION


def test_flag_on_supabase_failure_does_not_500_and_is_reported(client):
    """AC5 — the route reports the failure instead of raising, and does NOT
    claim success while a re-promotable L2 row survives."""
    sb = _supabase_mock(exc=RuntimeError("permission denied for table product_prices"))

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached", return_value=True), \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=sb):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is False
    rows = body["l2_product_prices"]
    assert rows and all(r["ok"] is False for r in rows)
    assert "permission denied" in rows[0]["error"]
    assert any("L2 product_prices deletes FAILED" in n for n in body["notes"])


def test_flag_on_unknown_row_count_is_reported_as_unknown_not_zero(client):
    """A PostgREST delete that returns no representation must NOT be reported as
    '0 rows' — the operator would read that as 'nothing was there'."""
    sb = _supabase_mock(data=None)
    sb.execute.return_value = MagicMock(data=None)

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.delete_cached", return_value=True), \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=sb):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    body = resp.json()
    assert body["l2_product_prices"][0]["rows_deleted"] is None
    assert any("UNKNOWN, not zero" in n for n in body["notes"])


# ---------------------------------------------------------------------------
# 5. Flag ON — a REAL cache round trip (only redis_client is faked)
# ---------------------------------------------------------------------------

def test_flag_on_removes_the_poisoned_entry_end_to_end(client):
    """The poisoned L1 entry, its sentinel and the legacy entry are all GONE
    after the flush, and `existed` reports which ones were really there.

    Nothing in cache_service is patched except the module-level Redis handle, so
    `get_cached` / `delete_cached` / the key builders all run for real.
    """
    from app.services import cache_service

    expected = _flush_keys(IDENTITY_Q, IDENTITY_PRODUCT)
    live_key, legacy_key = expected[0], expected[-1]
    fake = _FakeRedis()
    poison = {"amount": 999.0, "currency": "BHD", "source_method": "estimated"}
    fake.store[live_key] = json.dumps(poison)
    fake.store[negative_cache_key(live_key)] = json.dumps(poison)
    # the legacy key is deliberately ABSENT — its report must say so

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch.object(cache_service, "redis_client", fake), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock(data=[])):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # The poisoned entry and its 30-day sentinel are gone from the store.
    assert live_key not in fake.store
    assert negative_cache_key(live_key) not in fake.store
    # ...and the report is honest about what was actually there.
    assert body["flushed"]["price"] == {
        "key": live_key, "existed": True, "deleted": True,
    }
    neg = {e["key"]: e for e in body["flushed"]["negative_cache"]}
    assert neg[negative_cache_key(live_key)]["existed"] is True
    assert neg[negative_cache_key(legacy_key)]["existed"] is False
    assert body["cache_configured"] is True
    assert body["success"] is True
    assert body["notes"] == []


def test_flag_on_reports_when_redis_is_not_configured(client):
    """With no Redis handle `delete_cached` returns False for every key — the
    response must NOT claim success."""
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch("app.services.cache_service.redis_client", None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock(data=[])):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    body = resp.json()
    assert body["cache_configured"] is False
    assert body["success"] is False
    assert body["flushed"]["price"]["deleted"] is False
    assert any("Redis is not configured" in n for n in body["notes"])


# ---------------------------------------------------------------------------
# 6. The key-set builder in isolation
# ---------------------------------------------------------------------------

def test_price_key_builder_puts_the_live_key_first_and_dedupes():
    """Rung 1 is the LIVE key — measured, not re-derived."""
    keys = _flush_keys(IDENTITY_Q, IDENTITY_PRODUCT)
    assert keys[0] == _capture_live_price_key(IDENTITY_PRODUCT)["key"]
    assert get_price_cache_key("Dior", "Sauvage", "100ml", REGION) in keys
    assert len(keys) == len(set(keys))


def test_price_key_builder_falls_back_to_the_request_identity():
    """No `search_query` key at all -> BOTH sides take the same fallback string.

    This is the `.get(key, default)` mirror in its ABSENT case; the
    present-but-falsy case (where `or` and `.get` diverge) is pinned separately
    by `test_flag_on_matches_the_live_writer_on_a_present_but_empty_search_query`.
    """
    product = {"brand": "Dior", "name": "Sauvage", "variant": "100ml",
               "category": "fragrances"}
    keys = _flush_keys(IDENTITY_Q, product)
    assert keys[0] == _capture_live_price_key(product)["key"]


# ---------------------------------------------------------------------------
# 6b. The three DRIFTS the live-writer harness can now see
# ---------------------------------------------------------------------------

def test_flag_on_matches_the_live_writer_on_a_present_but_empty_search_query():
    """A PRESENT-but-falsy `search_query` must key exactly as the live path does.

    `_fetch_product_data` reads `product_info.get("search_query", <fallback>)`,
    so "" stays "" and the identity text is empty. The first #55 recipe used
    `or`, substituting `"{brand} {name} {variant}"` — and this fixture's brand
    ("Pro Plan") contributes a token from the electronics qualifier set, so the
    two recipes produced DIFFERENT keys and the flush deleted a key nothing had
    ever been written under. MEASURED here, not asserted from the recipe.
    """
    live = _capture_live_price_key(FALSY_SQ_PRODUCT)
    keys = _flush_keys(FALSY_SQ_Q, FALSY_SQ_PRODUCT)
    assert keys[0] == live["key"], (
        "the flush recipe substituted a fallback the live path did not: flush "
        f"{keys[0]} vs live {live['key']}"
    )
    # ...and the miss was REAL: no other rung covers the live key either, so
    # before the mirror the poisoned entry survived the flush entirely.
    legacy = get_price_cache_key(
        FALSY_SQ_PRODUCT["brand"], FALSY_SQ_PRODUCT["name"], None, REGION,
    )
    assert live["key"] != legacy, (
        "fixture stopped exercising the defect — the live key collapsed onto "
        "the legacy key, which rung 3 deletes anyway"
    )


def test_flag_on_deletes_the_live_key_for_an_empty_search_query(client):
    """Same divergence, driven through the ROUTE."""
    live = _capture_live_price_key(FALSY_SQ_PRODUCT)

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(FALSY_SQ_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock()):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": FALSY_SQ_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    assert live["key"] in deleted_keys
    assert negative_cache_key(live["key"]) in deleted_keys
    assert resp.json()["flushed"]["price"]["key"] == live["key"]


def test_flag_on_category_chip_targets_the_key_the_live_path_keyed_under(client):
    """The `category` query param — an electronics chip the LLM called "other".

    `_resolve_pair_category` honours the chip when the LLM emitted "other" and
    the A3 write-back stamps it onto the product dict, so the live path keys
    under "electronics" while the parser's own dict still says "other". Without
    the chip the flush reports (and deletes) a key the live path never wrote;
    with it, the two agree. BOTH directions are asserted so the param cannot
    become decorative.
    """
    live_chip = _capture_live_price_key(
        {**CHIP_PRODUCT_AS_PARSED, "category": CHIP_CATEGORY}
    )
    without = _flush_keys(CHIP_Q, CHIP_PRODUCT_AS_PARSED)
    with_chip = _flush_keys(CHIP_Q, CHIP_PRODUCT_AS_PARSED, category=CHIP_CATEGORY)

    assert live_chip["key"] not in without, (
        "fixture no longer diverges — the parser-category recipe already "
        "covers the live key, so the chip param is not exercised"
    )
    assert with_chip[0] == live_chip["key"]

    # ...and through the route.
    resp, _ = _flush(
        client, CHIP_Q, CHIP_PRODUCT_AS_PARSED,
        env={"ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}, category=CHIP_CATEGORY,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["flushed"]["price"]["key"] == live_chip["key"]

    resp_no_chip, _ = _flush(
        client, CHIP_Q, CHIP_PRODUCT_AS_PARSED,
        env={"ENABLE_FLUSH_LIVE_PRICE_KEY": "true"},
    )
    assert resp_no_chip.json()["flushed"]["price"]["key"] != live_chip["key"]


def test_flag_on_rung_two_deletes_the_key_the_raw_query_still_carries(client):
    """Rung 2 — the raw-`q` key — must be REACHABLE and deleted.

    NEW (test-quality review finding #2): under both original fixtures rung 2
    collapsed onto rung 1, so `_flush_price_cache_keys`' entire rung-2 block
    could be replaced with `pass` and all 28 nodes stayed green. This fixture
    has the parser normalizing the VOLUME out of `search_query` while the
    operator's raw query still carries it, so the three rungs are three DISTINCT
    keys: rung 1 (token "edp"), rung 2 (token "edp.100ml"), rung 3 (legacy).
    """
    keys = _flush_keys(RUNG2_Q, RUNG2_PRODUCT)
    assert len(keys) == 3 and len(set(keys)) == 3, (
        f"fixture no longer produces three distinct rungs: {keys}"
    )
    assert keys[0] == _capture_live_price_key(RUNG2_PRODUCT)["key"]

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(RUNG2_PRODUCT)), \
            patch("app.services.cache_service.delete_cached",
                  return_value=True) as del_mock, \
            patch("app.services.cache_service.get_cached", return_value=None), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock()):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": RUNG2_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    for key in keys:
        assert key in deleted_keys, f"{key} was never deleted"
        assert negative_cache_key(key) in deleted_keys, f"sentinel for {key} missing"

    body = resp.json()
    assert body["flushed"]["price"]["key"] == keys[0]
    assert [e["key"] for e in body["flushed"]["price_additional"]] == keys[1:]
    assert len(body["flushed"]["price_additional"]) == 2
    assert len(body["flushed"]["negative_cache"]) == 3
    assert len(body["l2_product_prices"]) == 3


# ---------------------------------------------------------------------------
# 6c. `success` must not outrank the L1 deletes it reports on
# ---------------------------------------------------------------------------

def test_flag_on_a_failing_l1_delete_makes_success_false_and_names_the_key(client):
    """Redis CONFIGURED but the DELETE raises -> the poisoned key survives.

    `delete_cached` swallows the exception and returns False, so before this fix
    the response said `success: true` with empty `notes` while the entry was
    still readable — the exact failure the route exists to stop, one level down
    (cache-coherence review finding #4).
    """
    from app.services import cache_service

    live_key = _capture_live_price_key(IDENTITY_PRODUCT)["key"]
    fake = _FakeRedis(fail_keys={live_key})
    fake.store[live_key] = json.dumps({"amount": 999.0, "currency": "BHD"})

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch.object(cache_service, "redis_client", fake), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock(data=[])):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Redis IS configured and every L2 delete landed — only the L1 delete failed.
    assert body["cache_configured"] is True
    assert all(row["ok"] for row in body["l2_product_prices"])
    assert body["flushed"]["price"]["deleted"] is False
    assert body["success"] is False
    assert any("L1 delete FAILED" in n and live_key in n for n in body["notes"])
    # ...and the poisoned entry really is still there, which is what `success`
    # False is telling the operator.
    assert live_key in fake.store


def test_flag_on_a_failing_sentinel_delete_also_fails_success(client):
    """Every L1 row counts, not just `flushed.price` — the 30d sentinel too."""
    from app.services import cache_service

    live_key = _capture_live_price_key(IDENTITY_PRODUCT)["key"]
    sentinel = negative_cache_key(live_key)
    fake = _FakeRedis(fail_keys={sentinel})

    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY,
                                   "ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(IDENTITY_PRODUCT)), \
            patch.object(cache_service, "redis_client", fake), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=_supabase_mock(data=[])):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    body = resp.json()
    assert body["flushed"]["price"]["deleted"] is True
    assert body["success"] is False
    assert any("L1 delete FAILED" in n and sentinel in n for n in body["notes"])


def test_flag_on_missing_redis_does_not_add_the_per_key_l1_note(client):
    """With NO Redis every delete is False by definition — naming all of them
    would bury the one note that matters. `success` is already False."""
    resp, _ = _flush(client, IDENTITY_Q, IDENTITY_PRODUCT,
                     env={"ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}, redis=None)
    body = resp.json()
    assert body["success"] is False
    assert any("Redis is not configured" in n for n in body["notes"])
    assert not any("L1 delete FAILED" in n for n in body["notes"])


# ---------------------------------------------------------------------------
# 7. Admin auth is untouched (the route is a paid/destructive debug endpoint)
# ---------------------------------------------------------------------------

def test_flush_still_requires_the_admin_key(client):
    with patch.dict("os.environ", {"ENABLE_FLUSH_LIVE_PRICE_KEY": "true"}):
        assert client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
        ).status_code in (401, 403, 422)
        assert client.delete(
            "/api/v1/text/cache", params={"q": IDENTITY_Q},
            headers={"X-Admin-Key": "wrong"},
        ).status_code == 403

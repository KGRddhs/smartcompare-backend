"""Issue #55 — `DELETE /api/v1/text/cache` must clear what the LIVE price path
writes, and must report honestly what it did and did not delete.

Two independent changes are pinned here:

1. UNFLAGGED defect repair — `extraction_service.parse_product_query` returns
   `(result, usage)`. The flush route treated it as a bare dict, so
   `parsed.get(...)` raised AttributeError on EVERY real call. Pinned by driving
   the route with the REAL tuple contract.

2. `ENABLE_FLUSH_LIVE_PRICE_KEY` (default OFF) — flag ON deletes the size-aware
   L1 price key(s) `_get_price` actually writes, the `nogenuine:` sentinel
   derived from each, and the L2 `product_prices` rows. Flag OFF is
   byte-identical to the pre-#55 body (three legacy keys, `{"key","deleted"}`
   entries, no extra top-level fields, no Supabase call, no existence probe).

Free tier only: nothing here touches the network, Redis or Supabase for real.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import text_routes
from app.main import app
from app.services.extraction_service import (
    canonicalize_category,
    get_price_cache_key,
    get_reviews_cache_key,
    get_specs_cache_key,
)
from app.services.price_service import (
    _infer_category_from_query,
    build_size_aware_price_cache_key,
    negative_cache_key,
)

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
    """Minimal stand-in for the module-level `cache_service.redis_client`."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


def _flush(client, q, product, env=None, supabase=None, redis=None):
    """Drive DELETE /text/cache with everything external mocked."""
    stack = []
    env = env or {}
    with patch.dict("os.environ", {"ADMIN_API_KEY": ADMIN_KEY, **env}), \
            patch("app.services.extraction_service.parse_product_query",
                  _parse_mock(product)), \
            patch("app.services.database_service.get_admin_supabase_client",
                  return_value=supabase if supabase is not None else _supabase_mock()) as sb, \
            patch("app.services.cache_service.redis_client", redis):
        resp = client.delete(
            "/api/v1/text/cache", params={"q": q},
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        stack.append(sb)
    return resp, stack[0]


def _expected_price_keys(q, product):
    brand = product["brand"]
    name = product["name"]
    variant = product["variant"]
    search_query = product.get("search_query") or f"{brand} {name} {variant or ''}"
    keys = []
    for k in (
        build_size_aware_price_cache_key(
            brand, name, variant, REGION, search_query,
            category=canonicalize_category(product.get("category")),
        ),
        build_size_aware_price_cache_key(
            brand, name, variant, REGION, q,
            category=_infer_category_from_query(q),
        ),
        get_price_cache_key(brand, name, variant, REGION),
    ):
        if k not in keys:
            keys.append(k)
    return keys


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
    The env read must live INSIDE the helper function, never at module level."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(text_routes))
    for node in tree.body:  # module-level statements only
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value == "ENABLE_FLUSH_LIVE_PRICE_KEY":
                pytest.fail("flag name read at module scope — must be per call")


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
    live_key = _expected_price_keys(IDENTITY_Q, IDENTITY_PRODUCT)[0]
    assert live_key not in deleted_keys
    # No existence probe, no negative sentinel, no Supabase call.
    get_mock.assert_not_called()
    sb.assert_not_called()
    assert not any(k.startswith("nogenuine:") for k in deleted_keys)


# ---------------------------------------------------------------------------
# 4. Flag ON — the acceptance criteria
# ---------------------------------------------------------------------------

def test_flag_on_deletes_the_size_aware_key_for_an_identity_query(client):
    """AC1 — the key handed to delete_cached equals the key the LIVE path writes."""
    expected = _expected_price_keys(IDENTITY_Q, IDENTITY_PRODUCT)
    legacy = get_price_cache_key("Dior", "Sauvage", "100ml", REGION)
    assert expected[0] != legacy, (
        "fixture no longer carries an identity axis — the defect is not exercised"
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
    expected = _expected_price_keys(PLAIN_Q, PLAIN_PRODUCT)
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
    expected = _expected_price_keys(IDENTITY_Q, IDENTITY_PRODUCT)

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
    expected = _expected_price_keys(IDENTITY_Q, IDENTITY_PRODUCT)
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

    expected = _expected_price_keys(IDENTITY_Q, IDENTITY_PRODUCT)
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
    keys = text_routes._flush_price_cache_keys(
        "Dior", "Sauvage", "100ml", REGION, IDENTITY_Q, IDENTITY_PRODUCT,
    )
    assert keys[0] == build_size_aware_price_cache_key(
        "Dior", "Sauvage", "100ml", REGION, "Dior Sauvage EDP 100ml",
        category="fragrances",
    )
    assert get_price_cache_key("Dior", "Sauvage", "100ml", REGION) in keys
    assert len(keys) == len(set(keys))


def test_price_key_builder_falls_back_to_the_request_identity():
    """No `search_query` from the parser -> the live path's own fallback string."""
    product = {"brand": "Dior", "name": "Sauvage", "variant": "100ml",
               "category": "fragrances"}
    keys = text_routes._flush_price_cache_keys(
        "Dior", "Sauvage", "100ml", REGION, IDENTITY_Q, product,
    )
    assert keys[0] == build_size_aware_price_cache_key(
        "Dior", "Sauvage", "100ml", REGION, "Dior Sauvage 100ml",
        category="fragrances",
    )


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

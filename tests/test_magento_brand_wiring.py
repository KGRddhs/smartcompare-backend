"""Magento brand wiring (genuine-price KPI Wave A4 — fix-ladder item 2 remainder).

Recon (live GraphQL probes, 2026-07-02) falsified the "magento is NOT wireable"
claim: klinq/trikart expose a custom `brand_name: String` returning the human
label ("Dior"/"Apple"); en-kwt.ajmal.com has NO queryable brand field (an unknown
field is a VALIDATION error that kills the whole query) but is mono-brand
("Ajmal"); the Adobe Catalog-Service Shape A carries brand generically at
`productView.attributes(roles: []) -> {name:"brand", value:...}`.

Pins:
  (a) the Shape-B query BUILDER splices the pinned brand field for klinq/trikart
      and NOT for ajmal (the validation-error class) — unpinned → byte-identical
      legacy query;
  (b) `_shape_b_price_node` carries brand from the pinned field / static_brand /
      "" fallback — NEVER the option-id fields (klinq `brand`="743", `mgs_brand`);
  (c) `_shape_a_price_node` reads the `brand` attribute entry, tolerating absence;
  (d) candidate_brand threads into strict_title_match + _selection_match inside
      `_best_match` (occ_service mirror) so a brand-omitting title is selected
      ONLY with the candidate's own matching brand;
  (e) an unpinned store rides the legacy query + candidate_brand="" (fail-safe).
"""
import json

import pytest

import app.services.magento_graphql_service as mg


# The pre-wiring Shape-B query, verbatim — the no-pin builder output must stay
# byte-identical to it (an unknown brand field would be a GraphQL validation
# error on stores without it, proven live on ajmal).
_LEGACY_SHAPE_B_QUERY = """
query($phrase: String!, $pageSize: Int!) {
  products(search: $phrase, pageSize: $pageSize) {
    items {
      name
      sku
      url_key
      stock_status
      price_range {
        minimum_price {
          final_price { value currency }
          regular_price { value currency }
        }
      }
    }
  }
}
""".strip()


class _FakeResp:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def _shape_b_item(name, brand_name=None, value=57.81, currency="BHD"):
    item = {
        "name": name,
        "sku": "sku-1",
        "url_key": "some-product",
        "stock_status": "IN_STOCK",
        "price_range": {
            "minimum_price": {
                "final_price": {"value": value, "currency": currency},
                "regular_price": {"value": value, "currency": currency},
            }
        },
    }
    if brand_name is not None:
        item["brand_name"] = brand_name
    return item


def _shape_a_pv(name, attrs=None):
    pv = {
        "name": name,
        "sku": "s",
        "urlKey": "buy-something",
        "inStock": True,
        "__typename": "SimpleProductView",
        "price": {"final": {"amount": {"value": 3.25, "currency": "BHD"}}},
    }
    if attrs is not None:
        pv["attributes"] = attrs
    return pv


@pytest.fixture(autouse=True)
def _enable_scrape(monkeypatch):
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    mg._CONFIG_CACHE.clear()
    yield
    mg._CONFIG_CACHE.clear()


# ---------------------------------------------------------------------------
# (a) Shape-B query builder + per-store pins
# ---------------------------------------------------------------------------

def test_builder_splices_pinned_brand_field():
    q = mg._build_shape_b_query("brand_name")
    assert "brand_name" in q


def test_builder_without_pin_is_byte_identical_legacy():
    assert mg._build_shape_b_query(None) == _LEGACY_SHAPE_B_QUERY


def test_store_pins_klinq_trikart_field_ajmal_static():
    assert mg._MAGENTO_STORES["klinq.com"].get("brand_field") == "brand_name"
    assert mg._MAGENTO_STORES["trikart.com"].get("brand_field") == "brand_name"
    ajmal = mg._MAGENTO_STORES["en-kwt.ajmal.com"]
    assert "brand_field" not in ajmal  # no queryable brand field in its schema
    assert ajmal.get("static_brand") == "Ajmal"


@pytest.mark.asyncio
async def test_ajmal_query_carries_no_brand_field(monkeypatch):
    """The wire query POSTed to ajmal must contain NO brand selection — an
    unknown GraphQL field returns errors[] with no data (kills the query)."""
    captured = {}
    from curl_cffi import requests as curl_requests

    def fake_post(url, *a, **k):
        captured["query"] = json.loads(k["data"])["query"]
        return _FakeResp(json.dumps({"data": {"products": {"items": []}}}))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    await mg.fetch_magento_graphql_price("en-kwt.ajmal.com", "Violet Musc Hair Mist")
    assert "brand" not in captured["query"]
    assert captured["query"] == _LEGACY_SHAPE_B_QUERY


@pytest.mark.asyncio
async def test_klinq_query_carries_brand_name(monkeypatch):
    captured = {}
    from curl_cffi import requests as curl_requests

    def fake_post(url, *a, **k):
        captured["query"] = json.loads(k["data"])["query"]
        return _FakeResp(json.dumps({"data": {"products": {"items": []}}}))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    await mg.fetch_magento_graphql_price("klinq.com", "Miss Dior EDP")
    assert "brand_name" in captured["query"]


# ---------------------------------------------------------------------------
# (b) Shape-B normalizer — brand from pinned field / static_brand / ""
# ---------------------------------------------------------------------------

def test_shape_b_node_brand_from_pinned_field():
    n = mg._shape_b_price_node(
        _shape_b_item("Miss Dior EDP", brand_name="Dior"), brand_field="brand_name"
    )
    assert n["brand"] == "Dior"


def test_shape_b_node_static_brand_fallback():
    n = mg._shape_b_price_node(_shape_b_item("Violet Musc Hair Mist"), static_brand="Ajmal")
    assert n["brand"] == "Ajmal"


def test_shape_b_node_unpinned_brand_empty_option_ids_never_used():
    """klinq also exposes `brand`="743" / `mgs_brand`=743 (attribute OPTION-IDs,
    not labels) — those must NEVER be read, even when present."""
    item = _shape_b_item("Miss Dior EDP", brand_name="Dior")
    item["brand"] = "743"
    item["mgs_brand"] = 743
    n = mg._shape_b_price_node(item)
    assert n["brand"] == ""


def test_shape_b_node_pinned_field_absent_falls_to_empty():
    n = mg._shape_b_price_node(_shape_b_item("Miss Dior EDP"), brand_field="brand_name")
    assert n["brand"] == ""


# ---------------------------------------------------------------------------
# (c) Shape-A normalizer — brand attribute entry, absence tolerated
# ---------------------------------------------------------------------------

def test_shape_a_query_requests_attributes():
    assert "attributes(roles: [])" in mg._SHAPE_A_QUERY


def test_shape_a_node_reads_brand_attribute():
    pv = _shape_a_pv(
        "Eucalyptus Body Cream",
        attrs=[
            {"name": "color", "value": "green"},
            {"name": "brand", "label": "Brand", "value": "Bath & Body Works"},
        ],
    )
    n = mg._shape_a_price_node(pv)
    assert n["brand"] == "Bath & Body Works"


def test_shape_a_node_tolerates_missing_attributes():
    n = mg._shape_a_price_node(_shape_a_pv("Eucalyptus Body Cream"))
    assert n is not None
    assert n["brand"] == ""


# ---------------------------------------------------------------------------
# (d) candidate_brand threading in _best_match (occ mirror)
# ---------------------------------------------------------------------------

def test_brand_omitted_title_selected_only_with_candidate_brand():
    """A klinq-style brand-omitting title ("Black Opium EDP 90ml") passes the
    strict gates ONLY when the node carries its own matching brand label."""
    query = "Yves Saint Laurent Black Opium EDP 90ml"
    with_brand = mg._shape_b_price_node(
        _shape_b_item("Black Opium EDP 90ml", brand_name="Yves Saint Laurent"),
        brand_field="brand_name",
    )
    r = mg._best_match([with_brand], query, resolved_category="fragrances")
    assert r is not None
    assert r["name"] == "Black Opium EDP 90ml"

    without_brand = mg._shape_b_price_node(_shape_b_item("Black Opium EDP 90ml"))
    assert mg._best_match([without_brand], query, resolved_category="fragrances") is None


def test_wrong_brand_candidate_still_rejected():
    """candidate_brand only drops the CANDIDATE's own brand tokens — a
    wrong-brand node keeps the query brand required and rejects."""
    node = mg._shape_b_price_node(
        _shape_b_item("Black Opium EDP 90ml", brand_name="Lattafa"),
        brand_field="brand_name",
    )
    assert (
        mg._best_match(
            [node], "Yves Saint Laurent Black Opium EDP 90ml",
            resolved_category="fragrances",
        )
        is None
    )


def test_variant_add_guard_holds_with_brand_dropped():
    """The alongside _selection_match still rejects a higher variant even when
    the brand token is dropped (occ mirror invariant)."""
    node = mg._shape_b_price_node(
        _shape_b_item("iPhone 15 Pro Max 256GB", brand_name="Apple"),
        brand_field="brand_name",
    )
    assert (
        mg._best_match([node], "Apple iPhone 15 256GB", resolved_category="electronics")
        is None
    )


@pytest.mark.asyncio
async def test_klinq_brand_omitted_title_end_to_end(monkeypatch):
    """Full fetch path: klinq returns a brand-omitting title + brand_name label
    → selected, genuine BHD stamp."""
    from curl_cffi import requests as curl_requests

    payload = {"data": {"products": {"items": [
        _shape_b_item("Black Opium EDP 90ml", brand_name="Yves Saint Laurent")
    ]}}}
    monkeypatch.setattr(
        curl_requests, "post", lambda *a, **k: _FakeResp(json.dumps(payload))
    )
    price = await mg.fetch_magento_graphql_price(
        "klinq.com", "Yves Saint Laurent Black Opium EDP 90ml",
        resolved_category="fragrances",
    )
    assert price is not None
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["title"] == "Black Opium EDP 90ml"


# ---------------------------------------------------------------------------
# (e) unpinned store — legacy path byte-identical
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unpinned_store_legacy_query_and_brand_required(monkeypatch):
    """A Shape-B store with NO brand pin sends the legacy query and matches with
    candidate_brand="" — a brand-omitted title is rejected exactly as before."""
    monkeypatch.setitem(
        mg._MAGENTO_STORES, "legacy-store.example", {"shape": "B", "store_view": "default"}
    )
    captured = {}
    from curl_cffi import requests as curl_requests

    payload = {"data": {"products": {"items": [_shape_b_item("Black Opium EDP 90ml")]}}}

    def fake_post(url, *a, **k):
        captured["query"] = json.loads(k["data"])["query"]
        return _FakeResp(json.dumps(payload))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    price = await mg.fetch_magento_graphql_price(
        "legacy-store.example", "Yves Saint Laurent Black Opium EDP 90ml",
        resolved_category="fragrances",
    )
    assert captured["query"] == _LEGACY_SHAPE_B_QUERY
    assert price is None


# ---------------------------------------------------------------------------
# (f) Wave B2 — Shape-A `attributes` validation-error fallback
# ---------------------------------------------------------------------------
# The attributes(roles: []) selection is live-proven on www.footlocker.com.bh
# (2026-07-02 probe: HTTP 200, no errors[], 5 nodes, brand="Nike", BHD) but is
# NOT schema-guaranteed across every Alshaya tenant: an older Catalog Service
# rejects the field with a GraphQL VALIDATION error (errors[] + no data) that
# kills the WHOLE query — the store would silently revert to built-but-dead
# with no test signal (fixtures mock the response, not the schema). On that
# error class the adapter re-POSTs ONCE without the attributes selection
# (brand="" legacy matching path).

_ATTRS_ERROR_PAYLOAD = {
    "errors": [
        {"message": 'Cannot query field "attributes" on type "ProductView".'}
    ],
    "data": None,
}


def _fake_shape_a_cfg():
    return {
        "endpoint": "https://www.bathandbodyworks.com.bh/graphql",
        "base_endpoint": "https://www.bathandbodyworks.com.bh",
        "env_id": "env-1", "api_key": "key-1", "store_view": "sv",
        "website": "w", "store_code": "sc", "customer_group": "0",
    }


def test_shape_a_attrs_rejected_detector():
    assert mg._shape_a_attrs_rejected(_ATTRS_ERROR_PAYLOAD) is True
    # string-shaped errors entries tolerated
    assert mg._shape_a_attrs_rejected(
        {"errors": ['Unknown field "attributes" on ProductView']}) is True
    # unrelated error / clean response / non-dict → NO fallback
    assert mg._shape_a_attrs_rejected(
        {"errors": [{"message": "Internal server error"}], "data": None}) is False
    assert mg._shape_a_attrs_rejected(
        {"data": {"productSearch": {"items": []}}}) is False
    assert mg._shape_a_attrs_rejected(None) is False


def test_shape_a_no_attrs_query_drops_only_the_attributes_selection():
    assert "attributes(roles: [])" in mg._SHAPE_A_QUERY
    assert "attributes" not in mg._SHAPE_A_QUERY_NO_ATTRS
    # everything else identical (same query modulo the attributes line)
    assert mg._SHAPE_A_QUERY.replace(
        "\n        attributes(roles: []) { name value }", ""
    ) == mg._SHAPE_A_QUERY_NO_ATTRS


@pytest.mark.asyncio
async def test_shape_a_attrs_error_falls_back_once_without_attributes(monkeypatch):
    """errors[] mentioning attributes → ONE re-POST with the attrs-free query;
    the node resolves with brand='' (legacy) and the price ships."""
    from curl_cffi import requests as curl_requests

    async def fake_cfg(host):
        return _fake_shape_a_cfg()

    monkeypatch.setattr(mg, "_harvest_shape_a_config", fake_cfg)

    good_payload = {"data": {"productSearch": {"items": [
        {"productView": _shape_a_pv("Eucalyptus Body Cream")}
    ]}}}
    queries = []

    def fake_post(url, *a, **k):
        queries.append(json.loads(k["data"])["query"])
        if len(queries) == 1:
            return _FakeResp(json.dumps(_ATTRS_ERROR_PAYLOAD))
        return _FakeResp(json.dumps(good_payload))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    price = await mg.fetch_magento_graphql_price(
        "bathandbodyworks.com.bh", "Eucalyptus Body Cream")
    assert len(queries) == 2
    assert "attributes" in queries[0]
    assert "attributes" not in queries[1]
    assert queries[1] == mg._SHAPE_A_QUERY_NO_ATTRS
    assert price is not None
    assert price["amount"] == pytest.approx(3.25)
    assert price["source_method"] == "magento_graphql_bhd"


@pytest.mark.asyncio
async def test_shape_a_clean_response_never_reposts(monkeypatch):
    """No errors[] → exactly ONE POST (the fallback is error-gated, not a retry)."""
    from curl_cffi import requests as curl_requests

    async def fake_cfg(host):
        return _fake_shape_a_cfg()

    monkeypatch.setattr(mg, "_harvest_shape_a_config", fake_cfg)

    good_payload = {"data": {"productSearch": {"items": [
        {"productView": _shape_a_pv("Eucalyptus Body Cream")}
    ]}}}
    calls = []

    def fake_post(url, *a, **k):
        calls.append(1)
        return _FakeResp(json.dumps(good_payload))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    price = await mg.fetch_magento_graphql_price(
        "bathandbodyworks.com.bh", "Eucalyptus Body Cream")
    assert len(calls) == 1
    assert price is not None


@pytest.mark.asyncio
async def test_shape_a_attrs_error_falls_back_exactly_once(monkeypatch):
    """Second response ALSO erroring → None, and never a third POST."""
    from curl_cffi import requests as curl_requests

    async def fake_cfg(host):
        return _fake_shape_a_cfg()

    monkeypatch.setattr(mg, "_harvest_shape_a_config", fake_cfg)
    calls = []

    def fake_post(url, *a, **k):
        calls.append(1)
        return _FakeResp(json.dumps(_ATTRS_ERROR_PAYLOAD))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    price = await mg.fetch_magento_graphql_price(
        "bathandbodyworks.com.bh", "Eucalyptus Body Cream")
    assert len(calls) == 2
    assert price is None

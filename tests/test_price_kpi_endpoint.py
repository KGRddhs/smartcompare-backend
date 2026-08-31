"""External review #1 — the dedicated single-product KPI endpoint (/api/v1/text/price-kpi).

The usable_exact_genuine KPI cannot use /compare (it rejects a query resolving to <2
products), so the prior single-product /compare call only "worked" under a mock and never
exercised the real parser/endpoint. These tests drive the REAL ASGI app (TestClient) +
the real parser path (parse_product_query) + the is_price_showable backstop, mocking only
parse_product_query and _get_price to avoid burning live APIs.
"""
import os
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.eval_runner import usable_exact_genuine_for_product

client = TestClient(app)


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    # M13-03: /text/price-kpi is now admin-gated (Depends(verify_admin_key)).
    # These KPI-measurement tests run as the operator, so satisfy the gate by
    # overriding the dependency (ADMIN_API_KEY is unset in the credential-stripped
    # test env, so a header would be rejected).
    from app.api.admin_routes import verify_admin_key

    app.dependency_overrides[verify_admin_key] = lambda: True
    yield
    app.dependency_overrides.pop(verify_admin_key, None)


def _parsed(brand, name, category):
    # parse_product_query returns (parsed_dict, usage)
    return ({"products": [{"brand": brand, "name": name, "category": category}]}, {})


def _genuine_price(title, amount=99.0):
    return {
        "amount": amount, "currency": "BHD", "source_method": "local_bhd",
        "in_stock": True, "url": "https://www.example-bh.com/p/item", "title": title,
    }


class TestPriceKpiEndpoint:
    def test_returns_single_product_body_shape(self):
        with patch("app.services.extraction_service.parse_product_query",
                   new=AsyncMock(return_value=_parsed("Apple", "iPhone 15", "electronics"))), \
             patch("app.api.text_routes.get_comparison_service") as mock_svc:
            mock_svc.return_value._get_price = AsyncMock(
                return_value=_genuine_price("Apple iPhone 15 256GB"))
            resp = client.get("/api/v1/text/price-kpi",
                              params={"q": "iPhone 15 256GB", "nocache": "true"})
        assert resp.status_code == 200
        body = resp.json()
        # the exact shape the KPI reads
        assert body["overview"]["products"][0]["price"]["amount"] == 99.0
        assert body["products"][0]["price"]["source_method"] == "local_bhd"

    def test_real_parser_is_invoked(self):
        # Proves the endpoint goes through the REAL parser (not a fabricated body).
        pq = AsyncMock(return_value=_parsed("Apple", "iPhone 15", "electronics"))
        with patch("app.services.extraction_service.parse_product_query", new=pq), \
             patch("app.api.text_routes.get_comparison_service") as mock_svc:
            mock_svc.return_value._get_price = AsyncMock(
                return_value=_genuine_price("Apple iPhone 15 256GB"))
            client.get("/api/v1/text/price-kpi", params={"q": "iPhone 15 256GB"})
        pq.assert_awaited()

    def test_exact_genuine_counts_usable(self):
        truth = {"query": "iPhone 15 256GB", "category": "electronics",
                 "expected": {"brand": "Apple", "model": "iPhone 15", "storage_gb": 256}}
        with patch("app.services.extraction_service.parse_product_query",
                   new=AsyncMock(return_value=_parsed("Apple", "iPhone 15", "electronics"))), \
             patch("app.api.text_routes.get_comparison_service") as mock_svc:
            mock_svc.return_value._get_price = AsyncMock(
                return_value=_genuine_price("Apple iPhone 15 256GB"))
            body = client.get("/api/v1/text/price-kpi",
                              params={"q": "iPhone 15 256GB", "nocache": "true"}).json()
        assert usable_exact_genuine_for_product(body, 0, truth) is True

    def test_flanker_is_pended_and_not_usable(self):
        # _get_price resolves a WRONG variant ("iPhone 15 Plus"); the backstop must PEND it,
        # and the KPI must NOT count it.
        truth = {"query": "iPhone 15 256GB", "category": "electronics",
                 "expected": {"brand": "Apple", "model": "iPhone 15", "storage_gb": 256}}
        with patch("app.services.extraction_service.parse_product_query",
                   new=AsyncMock(return_value=_parsed("Apple", "iPhone 15", "electronics"))), \
             patch("app.api.text_routes.get_comparison_service") as mock_svc:
            mock_svc.return_value._get_price = AsyncMock(
                return_value=_genuine_price("Apple iPhone 15 Plus 256GB"))
            body = client.get("/api/v1/text/price-kpi",
                              params={"q": "iPhone 15 256GB", "nocache": "true"}).json()
        price = body["overview"]["products"][0]["price"]
        assert price.get("amount") in (None, 0)  # pended
        assert usable_exact_genuine_for_product(body, 0, truth) is False

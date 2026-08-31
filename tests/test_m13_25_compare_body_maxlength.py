"""M13-25 — POST /text/compare body fields carry no max_length (unlike their GET
twins q=500 / product_a=80 / product_b=80), so a 5 MB `query` is logged in full
and written to search_logs: an unauthenticated log-flood / row-bloat primitive.

Mirror the GET constraints on the Pydantic model: query 500, product_a/product_b
80, region 20, selected_category bounded. Pin: an over-length field is 422.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.text_routes import TextCompareRequest


@pytest.fixture()
def client():
    return TestClient(app)


def test_model_rejects_overlong_query():
    with pytest.raises(ValidationError):
        TextCompareRequest(query="x" * 501)


def test_model_rejects_overlong_product_a():
    with pytest.raises(ValidationError):
        TextCompareRequest(product_a="x" * 81, product_b="y")


def test_model_rejects_overlong_product_b():
    with pytest.raises(ValidationError):
        TextCompareRequest(product_a="y", product_b="x" * 81)


def test_model_rejects_overlong_region():
    with pytest.raises(ValidationError):
        TextCompareRequest(query="a vs b", region="x" * 21)


def test_model_rejects_overlong_selected_category():
    with pytest.raises(ValidationError):
        TextCompareRequest(query="a vs b", selected_category="x" * 41)


def test_model_accepts_valid_input():
    m = TextCompareRequest(query="iPhone 15 vs Galaxy S24")
    assert m.query == "iPhone 15 vs Galaxy S24"


def test_http_overlong_query_is_422(client, monkeypatch):
    """The route rejects an over-length query at validation, before any work.
    Service is mocked so a rejected request never touches the network."""
    svc = MagicMock()
    svc.compare_from_text = AsyncMock(return_value={"success": True})
    monkeypatch.setattr("app.api.text_routes.get_comparison_service", lambda: svc)

    resp = client.post("/api/v1/text/compare", json={"query": "x" * 501})
    assert resp.status_code == 422, resp.text
    svc.compare_from_text.assert_not_awaited()

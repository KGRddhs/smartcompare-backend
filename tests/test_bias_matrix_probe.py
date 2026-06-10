"""F1.7 — unit tests for the bias-matrix probe's response parsing.

The live probe (scripts/bias_matrix_probe.py) needs network + API budget and
is run by the dispatcher (local uvicorn + post-merge prod). These tests pin
the PURE parsing logic against synthetic compare responses shaped exactly
like the source_trace this lane emits — so the runner can't silently
misread the route/source_method paths.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_PROBE = Path(__file__).resolve().parent.parent / "scripts" / "bias_matrix_probe.py"
_MATRIX = Path(__file__).resolve().parent.parent / ".qa-bias-rerun" / "bias_matrix_24.json"

spec = importlib.util.spec_from_file_location("bias_matrix_probe", _PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def _resp(products_trace, products_price):
    return {
        "metadata": {"source_trace": {"products": products_trace}},
        "products": products_price,
    }


def test_price_routes_reads_registry_route():
    resp = _resp(
        products_trace=[
            {"name": "A", "races": {"price": {"route": "registry", "source_weight": 3.0,
                                              "sources_tried": ["price"], "sources_returned_value": ["price"], "wall_ms": 100}}},
            {"name": "B", "races": {"price": {"route": "legacy_fallback", "source_weight": 0.5,
                                              "sources_tried": ["price"], "sources_returned_value": ["price"], "wall_ms": 90}}},
        ],
        products_price=[],
    )
    routes = probe._price_routes(resp)
    assert routes == ["registry", "legacy_fallback"]


def test_price_routes_absent_when_no_escalation():
    resp = _resp(
        products_trace=[
            {"name": "A", "races": {"price": {"sources_tried": ["price"], "sources_returned_value": ["price"], "wall_ms": 50}}},
        ],
        products_price=[],
    )
    assert probe._price_routes(resp) == [None]


def test_price_routes_empty_trace():
    assert probe._price_routes({}) == []
    assert probe._price_routes({"metadata": {}}) == []


def test_source_methods_top_level_products():
    resp = _resp(
        products_trace=[],
        products_price=[
            {"price": {"source_method": "page_scrape_jsonld", "amount": 100}},
            {"price": {"source_method": "gpt_training_estimate", "amount": 99}},
        ],
    )
    methods = probe._source_methods(resp)
    assert methods == ["page_scrape_jsonld", "gpt_training_estimate"]


def test_source_methods_falls_back_to_overview_products():
    resp = {
        "overview": {"products": [{"price": {"source_method": "converted_usd"}}]},
    }
    assert probe._source_methods(resp) == ["converted_usd"]


def test_estimate_methods_set_matches_enum():
    # The probe counts these as "gpt_training-priced".
    assert "gpt_training_estimate" in probe._ESTIMATE_METHODS
    assert "estimated" in probe._ESTIMATE_METHODS
    # A real scraped method must NOT count as estimated.
    assert "page_scrape_jsonld" not in probe._ESTIMATE_METHODS


# ---------- matrix fixture integrity ----------

def test_matrix_fixture_has_24_queries():
    matrix = json.loads(_MATRIX.read_text(encoding="utf-8"))
    assert len(matrix["queries"]) == 24


def test_matrix_ids_unique():
    matrix = json.loads(_MATRIX.read_text(encoding="utf-8"))
    ids = [q["id"] for q in matrix["queries"]]
    assert len(ids) == len(set(ids))


def test_matrix_every_query_has_required_fields():
    matrix = json.loads(_MATRIX.read_text(encoding="utf-8"))
    for q in matrix["queries"]:
        assert q["query"] and isinstance(q["query"], str)
        assert q["category"]
        assert q["region"]
        assert "expect_bahrain_registry" in q


def test_matrix_spans_target_categories():
    """Non-luxury bias matrix must cover the 0%-hit + mainstream classes."""
    matrix = json.loads(_MATRIX.read_text(encoding="utf-8"))
    cats = {q["category"] for q in matrix["queries"]}
    for must in ("electronics", "grocery", "supplements", "fragrances"):
        assert must in cats, f"matrix missing target category {must}"

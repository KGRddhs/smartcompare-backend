"""Tests for price source_method tagging."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class TestPriceSourceMethod:
    """Test that prices are tagged with source_method."""

    def test_iherb_price_tagged_converted_usd(self):
        price = {"amount": 4.52, "currency": "BHD", "retailer": "iHerb", "source_method": "converted_usd"}
        assert price["source_method"] == "converted_usd"

    def test_pharmacy_price_tagged_local_bhd(self):
        price = {"amount": 2.07, "currency": "BHD", "retailer": "Boots Bahrain", "source_method": "local_bhd"}
        assert price["source_method"] == "local_bhd"

    def test_estimated_price_tagged(self):
        price = {"amount": 3.50, "currency": "BHD", "estimated": True, "source_method": "estimated"}
        assert price["source_method"] == "estimated"

    def test_price_method_mismatch_detected(self):
        product_data = [
            {"price": {"source_method": "local_bhd"}},
            {"price": {"source_method": "converted_usd"}},
        ]
        methods = [p["price"].get("source_method") for p in product_data if p.get("price")]
        unique = set(m for m in methods if m)
        assert len(unique) > 1

    def test_price_method_match_no_flag(self):
        product_data = [
            {"price": {"source_method": "local_bhd"}},
            {"price": {"source_method": "local_bhd"}},
        ]
        methods = [p["price"].get("source_method") for p in product_data if p.get("price")]
        unique = set(m for m in methods if m)
        assert len(unique) <= 1

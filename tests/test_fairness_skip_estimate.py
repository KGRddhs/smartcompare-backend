"""Fairness fix (2026-07-07) — an ESTIMATE must not pend the pair's genuine price.

THE BUG (audit-confirmed): "Ajmal Aristocrat vs Rasasi Hawas" — Ajmal Aristocrat
resolves a GENUINE 21.5 BHD (75ml), but Rasasi Hawas only reaches a GPT ESTIMATE
(the real rasasistore "Hawas For Him" converted hit is rejected by the exact
gate). reconcile_pair_sizes assigns the SIZELESS estimate the flagship-100ml
default (because "Rasasi Hawas" is a recognized designer name), so the estimate
"reaches the target" and the genuine Aristocrat (75ml, no 100ml candidate) is
PENDED — hiding a real, showable price because its pair-mate only estimated.

THE FIX: an estimate is not a comparable DISPLAYED price (the chokepoint suppresses
it) and carries no real size basis, so fairness treats it as a non-comparable
amount → no reconcile → the showable genuine price stays (the estimate is
suppressed to pending at display). Gated by ENABLE_FAIRNESS_IGNORE_ESTIMATE
(default ON) → flag-OFF byte-identical (the prior pend-the-genuine behavior).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    reconcile_pair_sizes, reconcile_pair_fairness,
    _is_estimate_price, _fairness_ignore_estimate_enabled,
)


def _genuine(amount, size_ml, method="page_scrape_jsonld"):
    return {"amount": amount, "currency": "BHD", "source_method": method,
            "title": f"X EDP {size_ml}ml", "url": "https://x/p", "in_stock": True,
            "size": f"{size_ml}ml"}


def _estimate(amount=18.8):
    return {"amount": amount, "currency": "BHD", "source_method": "estimated", "estimated": True}


def _converted(amount, size_ml):
    return {"amount": amount, "currency": "BHD", "source_method": "converted_usd",
            "title": f"Y EDP {size_ml}ml", "url": "https://y/p", "in_stock": True,
            "size": f"{size_ml}ml"}


def _pair(price0, price1, name0="Ajmal Aristocrat", name1="Rasasi Hawas"):
    return [
        {"brand": name0.split()[0], "name": " ".join(name0.split()[1:]), "full_name": name0,
         "category": "fragrances", "price": price0, "variant": None},
        {"brand": name1.split()[0], "name": " ".join(name1.split()[1:]), "full_name": name1,
         "category": "fragrances", "price": price1, "variant": None},
    ]


class TestIsEstimatePrice:
    def test_estimate_by_flag_and_method(self):
        assert _is_estimate_price({"estimated": True}) is True
        assert _is_estimate_price({"source_method": "estimated"}) is True
        assert _is_estimate_price(_genuine(21.5, 75)) is False
        assert _is_estimate_price(_converted(30, 100)) is False
        assert _is_estimate_price(None) is False


class TestGenuinePlusEstimate:
    def test_genuine_not_pended_when_partner_estimates(self):
        """THE FIX — the failing-pair shape: genuine 21.5 (75ml) + estimate.
        The genuine price must STAY (not be pended); reconcile is a no-op."""
        pd = _pair(_genuine(21.5, 75), _estimate())
        changed = reconcile_pair_sizes(pd, user_query="Ajmal Aristocrat vs Rasasi Hawas")
        assert changed is False
        assert pd[0]["price"]["amount"] == 21.5  # genuine survives
        assert (pd[0]["price"].get("unavailable") or False) is False

    def test_via_reconcile_pair_fairness_fragrance_path(self):
        """The orchestrator entry (fragrances delegate to reconcile_pair_sizes)."""
        pd = _pair(_genuine(21.5, 75), _estimate())
        reconcile_pair_fairness(pd, "Ajmal Aristocrat vs Rasasi Hawas", "fragrances", candidates_by_name={})
        assert pd[0]["price"]["amount"] == 21.5
        assert (pd[0]["price"].get("unavailable") or False) is False

    def test_estimate_side_either_order(self):
        pd = _pair(_estimate(), _genuine(57.0, 100), name0="Rasasi Hawas", name1="Ajmal Amber Wood")
        reconcile_pair_sizes(pd, user_query="Rasasi Hawas vs Ajmal Amber Wood")
        assert pd[1]["price"]["amount"] == 57.0  # the genuine side survives

    def test_flag_off_byte_identical_pends_genuine(self, monkeypatch):
        """Rollback: flag OFF -> the prior (buggy) behavior — the sizeless estimate
        reaches the 100ml flagship target and PENDS the genuine 75ml side."""
        monkeypatch.setenv("ENABLE_FAIRNESS_IGNORE_ESTIMATE", "false")
        pd = _pair(_genuine(21.5, 75), _estimate())
        reconcile_pair_sizes(pd, user_query="Ajmal Aristocrat vs Rasasi Hawas")
        assert pd[0]["price"].get("unavailable") is True  # genuine pended (pre-fix)


class TestGenuinePairsUnchanged:
    def test_both_genuine_same_size_shows_both(self):
        """No estimate involved -> existing behavior untouched: two genuine 100ml
        prices are a valid common basis, both shown."""
        pd = _pair(_genuine(50.0, 100), _genuine(60.0, 100))
        reconcile_pair_sizes(pd, user_query=None)
        assert pd[0]["price"]["amount"] == 50.0 and pd[1]["price"]["amount"] == 60.0

    def test_converted_not_treated_as_estimate(self):
        """A CONVERTED price is SHOWABLE (not an estimate) -> still reconciled
        normally (the skip is estimate-only). Two converted 100ml -> both shown."""
        pd = _pair(_converted(30.0, 100), _converted(35.0, 100))
        reconcile_pair_sizes(pd, user_query=None)
        assert pd[0]["price"]["amount"] == 30.0 and pd[1]["price"]["amount"] == 35.0

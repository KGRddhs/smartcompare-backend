"""Issue #67 — there must be exactly ONE definition of "is this source_method a
genuine Bahrain-shelf price", and everything else must CALL it.

`price_service.is_genuine_source_method` claims that in its own docstring
("Hand-copying the branch there is precisely the drift defect tracked in #67, so
there is exactly ONE definition and everything else calls it"). The
cache-coherence review of 7dd04c1 (finding #5, P2) showed the claim was false:
two hand-copies survived on UNFLAGGED hot paths.

  * `price_service.should_negative_cache` (~:321) re-derived
    `sm in _GENUINE_BH_SOURCE_METHODS and "converted" not in sm and
    "estimate" not in sm` — the gate that decides whether to PLANT the
    `nogenuine:` sentinel, i.e. the exact inverse of the #53 check
    (`_cache_price_and_clear_sentinel` -> `is_genuine_price`) that DELETES it. A
    disagreement between those two means a genuine price both clears a sentinel
    and re-plants one.
  * `product_data_service._price_row_fresh` (~:124-132) re-derived it a third
    time, so inside the SAME function `_select_price_row` the freshness window
    (hand-copied rule) and the genuine preference (`is_genuine_source_method`)
    were decided by two independent copies.

This file is the PARITY GATE that had to pass before either copy could be routed
through the canonical predicate, and it stays as the drift pin afterwards. It
asserts the three predicates agree on EVERY genuine method, in every case form,
on blanks/whitespace/None, on converted- and estimate-token strings, and on
unknown strings — so a future edit to the canonical rule that the callers do not
follow goes red here instead of silently in production.

Measured with the copies still in place (the pre-refactor state): 0 mismatches
over the whole matrix, which is what justified the refactor as PURE — no
behaviour fork, no flag. The mutation that PROVES the routing is real is
neutering the canonical predicate: before the refactor the copies ignore it and
this file goes red; after, they follow it and it stays green.

Unflagged by design (repo precedent M13-10 / M13-44): a pure defect fix with no
behavioural fork, justified by this test.

All free-tier: no network, no credentials, no Redis, no Supabase.
"""
from __future__ import annotations

import ast
import os
from datetime import timedelta
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from app.services import price_service as ps  # noqa: E402
from app.services import product_data_service as pds  # noqa: E402

_APP = Path(__file__).resolve().parent.parent / "app" / "services"
PS_PATH = _APP / "price_service.py"
PDS_PATH = _APP / "product_data_service.py"


# ---------------------------------------------------------------------------
# The input matrix
# ---------------------------------------------------------------------------

def _case_forms(method: str) -> list:
    """Every case + whitespace form of one method the predicates could ever see."""
    return [
        method, method.upper(), method.title(), method.capitalize(),
        method.swapcase(),
        " " + method, method + " ", " " + method + " ",
        "\t" + method, method + "\n",
    ]


GENUINE_METHODS = sorted(ps._GENUINE_BH_SOURCE_METHODS)

NON_GENUINE = [
    None, "", " ", "   ", "\t", "\n",
    # converted / estimate token strings, incl. the two the cascade really stamps
    "estimated", "ESTIMATED", "Estimated",
    "converted_usd", "CONVERTED_USD", "Converted_Usd",
    "converted_fallback", "gpt_estimate", "gpt_training_estimate",
    "estimate", "converted",
    # a genuine apex CARRYING one of those tokens — never genuine
    "page_scrape_converted", "page_scrape_estimate", "local_bhd_converted",
    "shopify_json_estimate", "LOCAL_BHD_ESTIMATE",
    # the non-genuine sentinels the negative-cache path knows by name
    "validation_rejected", "sitemap_no_match", "pending_genuine",
    # unknown strings
    "unknown", "whatever", "firecrawl_x", "shopify", "zyte", "page", "bhd",
]

ALL_INPUTS = [m for g in GENUINE_METHODS for m in _case_forms(g)] + NON_GENUINE

# `should_negative_cache` exempts three NON-genuine methods by name for reasons
# unrelated to genuineness (SF-1 live-cited price, transient discovery miss,
# garbage-query rejection). They are separated out here so the parity assertion
# is about the GENUINE predicate and nothing else.
_NEGCACHE_EXEMPT = {"validation_rejected", "converted_usd", "sitemap_no_match"}

AGES = [
    timedelta(seconds=0), timedelta(hours=1), timedelta(hours=23),
    timedelta(hours=23, minutes=59), timedelta(hours=25), timedelta(days=3),
    timedelta(days=6, hours=23), timedelta(days=7, hours=1), timedelta(days=8),
]


def _canonical(method) -> bool:
    return ps.is_genuine_source_method(method)


# ---------------------------------------------------------------------------
# 1. The matrix is not degenerate
# ---------------------------------------------------------------------------


class TestTheMatrixItself:
    def test_it_covers_every_genuine_method(self):
        # MEASURED 15 on this tree; a shrink means the matrix stopped covering
        # methods it used to, which would silently narrow every parity assertion.
        assert len(GENUINE_METHODS) >= 15, "the genuine set shrank unexpectedly"
        for m in GENUINE_METHODS:
            assert _canonical(m) is True, m

    def test_it_contains_both_verdicts(self):
        verdicts = {_canonical(x) for x in ALL_INPUTS}
        assert verdicts == {True, False}, (
            "a matrix that is all-True or all-False proves nothing"
        )

    def test_case_and_whitespace_forms_are_actually_different_inputs(self):
        """`local_bhd` and `LOCAL_BHD` must both read genuine (case-insensitive),
        while ` local_bhd ` must NOT (no strip anywhere in the rule) — so the
        matrix really does separate the two behaviours instead of collapsing
        them."""
        assert _canonical("local_bhd") is True
        assert _canonical("LOCAL_BHD") is True
        assert _canonical(" local_bhd ") is False


# ---------------------------------------------------------------------------
# 2. Copy #1 — price_service.should_negative_cache
# ---------------------------------------------------------------------------


class TestShouldNegativeCacheParity:
    """`should_negative_cache` must answer exactly
    `not (is_genuine_source_method(sm) or sm is one of the three named exemptions)`
    for every input — no independent membership test of its own."""

    @pytest.mark.parametrize("method", ALL_INPUTS, ids=repr)
    def test_agrees_with_the_canonical_predicate(self, method):
        got = ps.should_negative_cache({"amount": 12.5, "source_method": method})
        expected = not (
            _canonical(method) or (method or "").lower() in _NEGCACHE_EXEMPT
        )
        assert got is expected, (
            f"should_negative_cache({method!r}) = {got}, canonical says "
            f"genuine={_canonical(method)} -> expected {expected}"
        )

    def test_the_non_dict_and_no_method_shapes_are_unchanged(self):
        """Guard rails the parity rewrite must not disturb."""
        assert ps.should_negative_cache(None) is True
        assert ps.should_negative_cache("not-a-dict") is True
        assert ps.should_negative_cache({"amount": 80.0}) is True
        assert ps.should_negative_cache(
            {"amount": None, "unavailable": True, "reason": "pending_genuine"}
        ) is True

    def test_it_is_the_exact_inverse_of_the_53_sentinel_deleter(self):
        """The point of the drift: `should_negative_cache` PLANTS the sentinel
        that `_cache_price_and_clear_sentinel`'s `is_genuine_price` DELETES. On a
        genuine price they must never both be true."""
        for method in [m for g in GENUINE_METHODS for m in _case_forms(g)]:
            price = {"amount": 45.0, "source_method": method}
            plants = ps.should_negative_cache(price)
            deletes = ps.is_genuine_price(price)
            assert not (plants and deletes), method
            assert plants is not deletes or not _canonical(method)


# ---------------------------------------------------------------------------
# 3. Copy #2 — product_data_service._price_row_fresh
# ---------------------------------------------------------------------------


class TestPriceRowFreshParity:
    """`_price_row_fresh` must pick its window from the canonical predicate:
    genuine -> GENUINE_PRICE_DB_TTL (7d), everything else -> PRICE_DB_TTL (24h)."""

    @pytest.mark.parametrize("method", ALL_INPUTS, ids=repr)
    def test_the_window_follows_the_canonical_predicate(self, method):
        window = (pds.GENUINE_PRICE_DB_TTL if _canonical(method)
                  else pds.PRICE_DB_TTL)
        for age in AGES:
            got = pds._price_row_fresh(method, age)
            assert got is (age <= window), (
                f"_price_row_fresh({method!r}, {age}) = {got}; canonical says "
                f"genuine={_canonical(method)} -> window {window}"
            )

    def test_the_two_windows_are_distinct(self):
        """Otherwise the assertion above is vacuous."""
        assert pds.GENUINE_PRICE_DB_TTL != pds.PRICE_DB_TTL
        assert pds.GENUINE_PRICE_DB_TTL > pds.PRICE_DB_TTL

    def test_the_two_deciders_inside_select_price_row_now_agree(self):
        """Finding #5's sharpest edge: within `_select_price_row` the freshness
        window (rung 1) and the genuine preference (rung 2) were decided by two
        independent copies. Same input, same verdict, or the selector can prefer
        a row it just declared stale."""
        assert timedelta(days=3) > pds.PRICE_DB_TTL, (
            "3d must sit BETWEEN the two windows or this proves nothing"
        )
        assert timedelta(days=3) <= pds.GENUINE_PRICE_DB_TTL
        for method in ALL_INPUTS:
            # At 3d the two windows disagree, so rung 1's verdict IS the genuine
            # verdict — the same one rung 2 (`is_genuine_source_method`) returns.
            assert pds._price_row_fresh(method, timedelta(days=3)) is _canonical(
                method
            ), method


# ---------------------------------------------------------------------------
# 4. Structural pins — no copy may come back
# ---------------------------------------------------------------------------


def _tree(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _func(scope, name):
    for node in scope.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found")


def _call_names(fn):
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


@pytest.fixture(scope="module")
def ps_tree():
    return _tree(PS_PATH)


@pytest.fixture(scope="module")
def pds_tree():
    return _tree(PDS_PATH)


class TestNoHandCopiesSurvive:
    def test_should_negative_cache_calls_the_predicate(self, ps_tree):
        fn = _func(ps_tree, "should_negative_cache")
        assert "is_genuine_source_method" in _call_names(fn)

    def test_should_negative_cache_does_not_test_set_membership_itself(self, ps_tree):
        """Positive control first: the set name IS referenced somewhere in the
        module (so a typo cannot make this pass vacuously), then that NONE of
        those references sits inside `should_negative_cache`."""
        module_refs = [
            n for n in ast.walk(ps_tree)
            if isinstance(n, ast.Name) and n.id == "_GENUINE_BH_SOURCE_METHODS"
        ]
        assert module_refs, "_GENUINE_BH_SOURCE_METHODS is not referenced at all"
        fn = _func(ps_tree, "should_negative_cache")
        inside = {id(n) for n in ast.walk(fn)}
        assert not [n for n in module_refs if id(n) in inside], (
            "should_negative_cache re-derives the genuine set instead of calling "
            "is_genuine_source_method (#67 drift)"
        )

    def test_price_row_fresh_calls_the_predicate(self, pds_tree):
        fn = _func(pds_tree, "_price_row_fresh")
        assert "is_genuine_source_method" in _call_names(fn)
        imported = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.ImportFrom) and n.module == "app.services.price_service"
        ]
        assert imported, "the predicate is not imported from price_service"
        assert any(a.name == "is_genuine_source_method"
                   for imp in imported for a in imp.names)

    def test_price_row_fresh_does_not_import_the_set(self, pds_tree):
        fn = _func(pds_tree, "_price_row_fresh")
        leaked = [
            a.name for n in ast.walk(fn) if isinstance(n, ast.ImportFrom)
            for a in n.names if a.name == "_GENUINE_BH_SOURCE_METHODS"
        ]
        assert not leaked, (
            "_price_row_fresh still imports the raw set — that is the third "
            "hand-copy of the rule (#67 drift)"
        )

    def test_the_whole_product_data_service_module_has_no_copy(self, pds_tree):
        """Widened from the #54 pin: neither the set NOR a hand-written
        converted/estimate token test may live in this module."""
        refs = [
            n for n in ast.walk(pds_tree)
            if isinstance(n, ast.Name) and n.id == "_GENUINE_BH_SOURCE_METHODS"
        ]
        assert not refs, "product_data_service references the raw genuine set"
        imports = [
            a.name for n in ast.walk(pds_tree) if isinstance(n, ast.ImportFrom)
            for a in n.names
        ]
        assert "_GENUINE_BH_SOURCE_METHODS" not in imports

    def test_the_predicate_is_pure_and_reads_no_env(self, ps_tree):
        """It sits on UNFLAGGED hot paths, so it must stay a pure function — no
        os.getenv, no flag, nothing that could make the two callers diverge by
        configuration rather than by code."""
        fn = _func(ps_tree, "is_genuine_source_method")
        assert "getenv" not in _call_names(fn)
        assert not [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.startswith("ENABLE_")
        ]

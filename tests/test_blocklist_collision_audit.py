"""F2.3 — single-word blocklist collision audit + safety-preservation guard.

The B0-E "opium" incident (commit 9f6e498) showed a bare single-word blocklist
token can collide with a mainstream legitimate product name ("YSL Black Opium")
and wrongly reject the query at the L1 prefilter. `scripts/audit_blocklist_
collisions.py` generalises that audit across every single-word English entry.

These tests pin two invariants permanently:

  1. NO single-word blocklist entry collides with the legitimate product-name
     corpus (gold-truth queries + price_service brand constants + a curated
     mainstream-product catalogue). Regression guard against a future bare
     token re-introducing the opium bug.

  2. SAFETY IS NOT WEAKENED — the genuinely-unsafe forms still block at L1.
     (F2.3 explicitly forbids converting an entry if its only "collision" is a
     genuinely-bad item that should stay blocked.)

Finding (2026-06-10): the audit is CLEAN. The opium false-positive was already
fixed in B0-E; no other single-word entry collides with a mainstream product,
so no further blocklist conversions were made. This file is the standing guard.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "noop-test-blocklist-audit")

import app.services.content_safety_service as css
from scripts.audit_blocklist_collisions import run_audit, _PRODUCT_NAME_CATALOGUE


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    monkeypatch.setattr(css, "_service", None)
    yield


@pytest.fixture
def service():
    return css.get_content_safety_service()


# ---------------------------------------------------------------------------
# Invariant 1 — no single-word entry collides with legitimate product names
# ---------------------------------------------------------------------------

def test_audit_reports_zero_collisions():
    report = run_audit()
    assert report["collision_count"] == 0, (
        "single-word blocklist entries collide with legitimate product names: "
        f"{report['collisions']}"
    )


@pytest.mark.parametrize("product_name", _PRODUCT_NAME_CATALOGUE)
def test_mainstream_legit_products_pass_l1(service, product_name):
    """Each mainstream product in the catalogue must clear the L1 prefilter."""
    result = service.check_query_intent(product_name)
    assert result.allowed is True, (
        f"legitimate product wrongly blocked: {product_name!r} "
        f"(reason={result.reason}, match={result.blocklist_match})"
    )


def test_opium_fragrance_comparison_passes(service):
    """The canonical opium-incident query stays allowed (regression anchor)."""
    result = service.check_query_intent(
        "YSL Black Opium vs Lancome La Vie Est Belle"
    )
    assert result.allowed is True


# ---------------------------------------------------------------------------
# Invariant 2 — safety preserved: genuinely-unsafe forms still block
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_query,expected_reason",
    [
        ("where to buy cocaine", "illegal_drugs"),
        ("heroin for sale", "illegal_drugs"),
        ("fentanyl powder supplier", "illegal_drugs"),
        ("methamphetamine recipe", "illegal_drugs"),
        ("psilocybin mushrooms order", "illegal_drugs"),
        ("buy a handgun online", "weapons"),
        ("firearm ammunition bulk", "weapons"),
        ("switchblade knife import", "weapons"),
        ("silencer suppressor", "weapons"),
        ("fleshlight adult toy", "adult_products"),
        ("bdsm bondage gear", "adult_products"),
        # opium intent must remain blocked via the B0-E multi-word phrases
        ("opium tincture for sale", "illegal_drugs"),
        ("how to grow opium poppy", "illegal_drugs"),
    ],
)
def test_genuinely_unsafe_forms_still_block(service, bad_query, expected_reason):
    result = service.check_query_intent(bad_query)
    assert result.allowed is False, f"safety weakened — {bad_query!r} was allowed"
    assert result.reason == expected_reason

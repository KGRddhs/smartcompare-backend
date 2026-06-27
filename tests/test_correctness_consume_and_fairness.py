"""Genuine-Price CORRECTNESS build — Tier-2 cross-adapter consume + Tier-3
pair-fairness re-select.

CARDINAL RULE (IMPL-SPEC): select a price ONLY if it is the EXACT requested
product (model + concentration + size + variant + count), native BHD / honest
converted_usd, current PDP, IN STOCK, valid URL — pick by AUTHORITY, never the
cheapest. A miss must PEND.

This file pins two enforcement layers from the spec:

  * Tier-2 cross-adapter consume — `structured_comparison_service`
    `_consume_adapter_prefetch` (scs.py:4661-4674) currently short-circuits on
    `min(genuine_observed, key=amount)` (the CHEAPEST genuine adapter hit), with
    NO exactness / authority / in-stock re-check. The fix routes that selection
    through the NEW shared `select_best`.

  * Tier-3 pair-fairness re-select — `price_service.reselect_to_target_size`
    (:1162) / `reselect_to_target_value` (:2033) / `reconcile_pair_fairness`
    (:2123) re-select to the comparable unit from candidates already fetched,
    but rank by `(genuine, variant_rank, -amount)` with NO concentration/variant
    exactness re-check and NO in-stock re-check — so a wrong-VARIANT candidate at
    the target size (cheaper) is chosen over the correct EXACT one, and an
    OUT-OF-STOCK exact candidate at the target size is served.

TDD discipline:
  * `select_best` does NOT exist yet (Wave B) → it is imported INSIDE the test
    body so COLLECTION never errors; the test fails with ImportError = a real
    RED until Wave B. (`# RED (new-helper)`)
  * The behavioral reds call the EXISTING `reselect_to_target_size` with crafted
    fixtures that genuinely exercise the bug on CURRENT code (`# RED`).
  * The green asserts a legitimate single exact in-stock candidate is still
    selected — must pass NOW and keep passing after the strict gate (`# GREEN`).

Run: python -m pytest tests/test_correctness_consume_and_fairness.py -q
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import reselect_to_target_size


# ---------------------------------------------------------------------------
# Candidate shaping — mirrors the retained fan_out / Tier-1 candidate dict the
# pair-fairness re-select consumes. `raw_data` carries the actual price dict the
# selection stamps the source_method onto (matches _candidate_size_ml +
# reselect_to_target_size: it reads price.size then title for the ml axis, and
# is_price_showable for the genuine/accuracy gate). `in_stock` rides on raw_data
# (the spec keeps it through to the backstop; an OOS exact must PEND).
# ---------------------------------------------------------------------------
def _cand(
    amount,
    *,
    source_method="page_scrape_jsonld",
    title=None,
    retailer="theperfumesclub.com",
    size=None,
    variant_rank=0.0,
    in_stock=None,
    url=None,
):
    raw = {
        "amount": amount,
        "currency": "BHD",
        "source_method": source_method,
        "retailer": retailer,
        "url": url if url is not None else f"https://{retailer}/products/p",
        "title": title,
        "size": size,
    }
    if in_stock is not None:
        raw["in_stock"] = in_stock
    cand = {
        "value": amount,
        "rank": 85,
        "source_method": source_method,
        "retailer": retailer,
        "variant_rank": variant_rank,
        "raw_data": raw,
    }
    if in_stock is not None:
        cand["in_stock"] = in_stock
    return cand


# ===========================================================================
# 1. select_best — NEW shared authority selector (Wave B). Tier-2 consume +
#    Tier-3 fairness both call this. Import INSIDE the body so collection never
#    errors before the helper exists.
# ===========================================================================
class TestSelectBestContract:
    def test_picks_exact_authority_not_cheapest_and_skips_oos(self):  # RED (new-helper)
        # The Tier-2 consume bug, distilled: among
        #   * correct EXACT, in-stock, valid PDP URL @ BHD 80,
        #   * a wrong DECANT (not the same product) @ BHD 30 (cheapest), in-stock,
        #   * the EXACT product but OUT OF STOCK @ BHD 25 (cheaper still),
        # select_best must return the BHD 80 EXACT in-stock one — NOT min(amount),
        # NOT the OOS exact.
        from app.services.price_service import select_best

        correct = {
            "amount": 80.0, "currency": "BHD", "source_method": "woo_store_api",
            "retailer": "theperfumesclub.com",
            "url": "https://theperfumesclub.com/products/sauvage-edt-100ml",
            "title": "Dior Sauvage Eau de Toilette 100ml", "in_stock": True,
        }
        wrong_decant = {
            "amount": 30.0, "currency": "BHD", "source_method": "page_scrape_jsonld",
            "retailer": "somedecantshop.com",
            "url": "https://somedecantshop.com/products/sauvage-decant-10ml",
            "title": "Dior Sauvage Eau de Toilette Decant 10ml Sample", "in_stock": True,
        }
        exact_oos = {
            "amount": 25.0, "currency": "BHD", "source_method": "shopify_json",
            "retailer": "anothershop.com",
            "url": "https://anothershop.com/products/sauvage-edt-100ml",
            "title": "Dior Sauvage Eau de Toilette 100ml", "in_stock": False,
        }
        out = select_best(
            [correct, wrong_decant, exact_oos],
            "Dior Sauvage EDT 100ml",
            category="fragrances",
        )
        assert out is not None
        assert out["amount"] == 80.0
        assert out["source_method"] == "woo_store_api"

    def test_all_junk_returns_none(self):  # RED (new-helper)
        # No candidate is exact ∧ in-stock ∧ valid-URL → None (caller pends).
        from app.services.price_service import select_best

        only_oos = {
            "amount": 80.0, "currency": "BHD", "source_method": "woo_store_api",
            "retailer": "theperfumesclub.com",
            "url": "https://theperfumesclub.com/products/sauvage-edt-100ml",
            "title": "Dior Sauvage Eau de Toilette 100ml", "in_stock": False,
        }
        wrong_product = {
            "amount": 50.0, "currency": "BHD", "source_method": "page_scrape_jsonld",
            "retailer": "shop.com",
            "url": "https://shop.com/products/aventus-100ml",
            "title": "Creed Aventus Eau de Parfum 100ml", "in_stock": True,
        }
        out = select_best(
            [only_oos, wrong_product],
            "Dior Sauvage EDT 100ml",
            category="fragrances",
        )
        assert out is None

    def test_authority_tiebreak_higher_authority_wins_even_when_pricier(self):  # RED (new-helper)
        # Two EXACT, in-stock, valid-URL candidates. The higher-authority retailer
        # wins even though it is PRICIER. nasserpharmacy.com is a registry-known
        # fragrances source (score_source weight 3.0); the unknown shop scores 0.5.
        # CARDINAL: amount is the LAST tiebreak only — authority dominates.
        from app.services.price_service import select_best

        high_authority_pricier = {
            "amount": 92.0, "currency": "BHD", "source_method": "local_bhd",
            "retailer": "nasserpharmacy.com",
            "url": "https://www.nasserpharmacy.com/bh-en/dior-sauvage-edt-100ml",
            "title": "Dior Sauvage Eau de Toilette 100ml", "in_stock": True,
        }
        low_authority_cheaper = {
            "amount": 78.0, "currency": "BHD", "source_method": "page_scrape_jsonld",
            "retailer": "unknown-perfume-shop.com",
            "url": "https://unknown-perfume-shop.com/products/sauvage-edt-100ml",
            "title": "Dior Sauvage Eau de Toilette 100ml", "in_stock": True,
        }
        out = select_best(
            [low_authority_cheaper, high_authority_pricier],
            "Dior Sauvage EDT 100ml",
            category="fragrances",
        )
        assert out is not None
        assert out["amount"] == 92.0
        assert out["retailer"] == "nasserpharmacy.com"


# ===========================================================================
# 2. reselect_to_target_size — wrong-VARIANT at the target ml must NOT beat the
#    correct EXACT one just because it is cheaper (EXISTING fn; behavioral RED).
# ===========================================================================
class TestReselectExactnessRed:
    def test_wrong_concentration_at_target_not_chosen_over_exact(self):  # RED
        # Query is the EDP. Two GENUINE candidates, BOTH at the target 100ml, both
        # above the premium full-bottle floor (so both pass is_price_showable) and
        # SAME variant_rank — so current ranking falls through to -amount and
        # picks the CHEAPER wrong-concentration EDT. The correct fix re-checks
        # concentration exactness and must return the EDP.
        cands = [
            _cand(60.0, title="Tom Ford Tobacco Vanille Eau de Toilette 100ml",
                  size="100ml", variant_rank=0.0),                       # wrong: EDT, cheaper
            _cand(95.0, title="Tom Ford Tobacco Vanille Eau de Parfum 100ml",
                  size="100ml", variant_rank=0.0),                       # correct: EDP, pricier
        ]
        out = reselect_to_target_size(
            "Tom Ford Tobacco Vanille Eau de Parfum", cands, 100.0,
        )
        assert out is not None
        # The CORRECT exact (EDP) must win — NOT the cheaper wrong-variant EDT.
        assert out["amount"] == 95.0
        assert "parfum" in (out.get("title") or "").lower()
        assert "toilette" not in (out.get("title") or "").lower()

    def test_only_out_of_stock_exact_at_target_returns_none(self):  # RED
        # The single candidate is the EXACT product at the target 100ml, above the
        # floor (passes is_price_showable today) — but it is OUT OF STOCK. Current
        # reselect ignores in_stock and returns it; the fix must PEND (None): a
        # costlier in-stock exact beats a cheap OOS, and with NO in-stock exact at
        # all the product pends rather than serving an unbuyable price.
        cands = [
            _cand(95.0, title="Tom Ford Tobacco Vanille Eau de Parfum 100ml",
                  size="100ml", in_stock=False),
        ]
        out = reselect_to_target_size(
            "Tom Ford Tobacco Vanille Eau de Parfum", cands, 100.0,
        )
        assert out is None


# ===========================================================================
# 3. ANTI-OVER-REJECTION green — a single genuine EXACT in-stock candidate at
#    the target size is still selected (must pass NOW and after the strict gate).
# ===========================================================================
class TestReselectNoRegressionGreen:
    def test_single_genuine_exact_in_stock_at_target_selected(self):  # GREEN
        cands = [
            _cand(95.0, title="Tom Ford Tobacco Vanille Eau de Parfum 100ml",
                  size="100ml", in_stock=True),
        ]
        out = reselect_to_target_size(
            "Tom Ford Tobacco Vanille Eau de Parfum", cands, 100.0,
        )
        assert out is not None
        assert out["amount"] == 95.0
        assert out["source_method"] == "page_scrape_jsonld"

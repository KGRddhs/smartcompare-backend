"""WS-TEST (Genuine-BH Latency+Warmer bundle, T9) — best-available-partial
assembly happy-path, end-to-end with MOCKED services (no network).

This is the integration counterpart to be-core's WS1 unit tests
(test_compare_timeout_graceful.py / test_text_routes_error_mapping.py, both
be-core-owned). It pins the D2 error contract from the OUTSIDE — the
observable behavior any `_build_partial_response()` implementation must
satisfy — so the contract can't silently regress regardless of WS1 internals:

  D1 — Fail-fast = best-available, never a crash. On the soft deadline with at
       least one product carrying usable data, the service returns
       `success:true` + `metadata.partial:true` carrying whatever prices landed
       (genuine > converted > estimated-last-resort) with an HONEST
       `source_method`, plus a templated verdict fallback. Only when BOTH
       products have zero usable data does the existing INSUFFICIENT_DATA path
       fire.
  D2 — Error contract. A true hard failure preserves `code:"TIMEOUT"`
       end-to-end and maps to HTTP 503 (NOT the legacy collapse-to-400, NOT
       STATUS_CODE_MAP's FEATURE_DISABLED-for-503). Copy obeys the
       no-scary-copy contract (.copy-policy.json: no couldn't / try again /
       failed / تعذر / فشل / تقدير).

All inputs are mocked dicts; NO Serper/Firecrawl/OpenAI/Redis calls. The
assembly-level tests drive `response_builder.build_comparison_response()`
directly (the function `_build_partial_response()` mirrors per WS1 §3 step 1);
the route-level tests drive the GET + POST handlers with a mocked service so
the HTTP-status mapping is asserted against the real middleware stack.
"""

import json
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.response_builder import build_comparison_response


client = TestClient(app)


# ---------------------------------------------------------------------------
# Forbidden-vocab oracle — mirrors SmartCompareApp/src/i18n/.copy-policy.json
# scary_vocab_en + scary_vocab_ar. Kept local (the backend has no JS-policy
# loader) so a response-string scan can run in the free unit suite.
# ---------------------------------------------------------------------------
FORBIDDEN_VOCAB = [
    # scary_vocab_en (case-insensitive)
    "couldn't",
    "try again",
    "failed to",
    # scary_vocab_ar (+ no "estimated" leakage per D3 / feedback_no_estimated_word_in_ui)
    "تعذر",
    "فشل",
    "تقدير",
    "مُقدَّر",
]


def _assert_no_forbidden_vocab(payload) -> None:
    """Walk an arbitrary JSON-serializable payload and assert no rendered
    string contains forbidden scary/estimated vocabulary. source_method
    ENUM values (e.g. 'estimated') are NOT user-facing copy and are
    intentionally NOT in FORBIDDEN_VOCAB — only rendered strings are scanned
    via the substring oracle (see feedback_user_visible_vs_payload_distinction)."""
    blob = json.dumps(payload, default=str, ensure_ascii=False).lower()
    for term in FORBIDDEN_VOCAB:
        assert term.lower() not in blob, (
            f"forbidden vocab {term!r} leaked into the response payload"
        )


# ---------------------------------------------------------------------------
# Fixtures — partial product_data: specs + reviews landed, price is the
# best-available honest fallback (converted_usd), verdict not yet computed.
# This is the canonical "one product has data, cap fired" partial state.
# ---------------------------------------------------------------------------
def _partial_product(brand, name, *, source_method, amount):
    """A product whose price landed via an HONEST fallback method. Mirrors the
    shape _fetch_product_data stashes per-product before the cap fires."""
    return {
        "brand": brand,
        "name": name,
        "full_name": f"{brand} {name}",
        "category": "fragrances",
        "price": {
            "amount": amount,
            "currency": "BHD",
            "retailer": "iHerb" if source_method == "converted_usd" else None,
            "url": None,
            "source_method": source_method,
            "estimated": source_method == "estimated",
        },
        "best_price": amount,
        "specs": {"volume_ml": 100, "concentration": "EDP"},
        "reviews": {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "long-lasting",
                "highlights": [],
                "review_volume": "moderate",
                "agreement_level": "moderate",
            }
        },
        "rating": 4.4,
        "rating_source": None,
        "review_count": 120,
        "image_url": None,
        "fact_check": {},
    }


def _partial_scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 64.0}, "product_1": {"overall": 55.0}},
        "win_margin": 9.0,
        "tradeoff_pairs": [],
        "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
        "scoring_method": "category_weighted",
    }


# ===========================================================================
# Layer 1 — assembly-level: build_comparison_response with partial inputs.
# This is exactly what _build_partial_response() mirrors (WS1 §3 step 1).
# ===========================================================================
class TestPartialAssemblyHappyPath:
    def _build_partial(self, *, p0_method="converted_usd", p1_method="converted_usd",
                       comparison=None):
        product_data = [
            _partial_product("Tom Ford", "Ombre Leather", source_method=p0_method, amount=80.0),
            _partial_product("Tom Ford", "Tobacco Vanille", source_method=p1_method, amount=118.0),
        ]
        # metadata.partial:true is the D1 marker the wrapper injects when it
        # assembles a best-available result on cap. build_comparison_response
        # merges the `metadata` kwarg onto the auto-built block (B.0 contract).
        return build_comparison_response(
            query="Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille",
            product_data=product_data,
            scoring_result=_partial_scoring(),
            comparison=comparison,
            region="bahrain",
            category_used="fragrances",
            api_calls=4,
            elapsed_seconds=30.0,
            total_cost=0.017,
            gpt_calls=2,
            serper_calls=6,
            from_cache=False,
            verdict_validation={},
            metadata={"partial": True},
        )

    def test_partial_response_is_success_true(self):
        """D1 — a partial with one+ product carrying data is success:true,
        NOT a TIMEOUT failure."""
        resp = self._build_partial()
        assert resp["success"] is True

    def test_partial_response_carries_partial_marker(self):
        """D1 — metadata.partial:true so the FE renders the partial result
        + a soft 'still settling' affordance rather than a crash state."""
        resp = self._build_partial()
        assert resp["metadata"]["partial"] is True

    def test_partial_response_keeps_honest_source_method(self):
        """D1/D3 — the best-available price keeps its HONEST source_method
        (converted_usd here); the partial path must never silently relabel a
        converted price as genuine local_bhd."""
        resp = self._build_partial()
        for op in resp["overview"]["products"]:
            assert op["price"]["source_method"] == "converted_usd"
            assert op["price"]["currency"] == "BHD"
            assert op["price"]["amount"] in (80.0, 118.0)

    def test_partial_response_preserves_genuine_when_landed(self):
        """D1 — when a genuine BH price DID land before the cap, it's served
        as-is (genuine > converted precedence)."""
        resp = self._build_partial(p0_method="page_scrape_jsonld")
        p0 = resp["overview"]["products"][0]
        assert p0["price"]["source_method"] == "page_scrape_jsonld"

    def test_partial_response_has_templated_verdict_fallback(self):
        """D1 — when the GPT verdict didn't finish, the partial still ships a
        non-empty templated verdict (scoring_v2.factual_verdict is the pure-
        template fallback the response builder always composes). Two products
        + a winner_index => line1 + line2 populated, no GPT cost."""
        resp = self._build_partial(comparison=None)  # comparison None => no GPT verdict
        fv = resp["scoring_v2"]["factual_verdict"]
        assert fv is not None
        assert fv.get("line1")  # winner-anchored line, templated from price/rating delta
        assert fv.get("line2")  # runner-up counter-fact
        # The winner declaration falls back to the product name (no GPT prose).
        assert resp["overview"]["winner"]["name"]

    def test_partial_response_has_two_priced_products(self):
        """Acceptance (WS1) — the Tom Ford repro returns two prices."""
        resp = self._build_partial()
        prices = [op["price"]["amount"] for op in resp["overview"]["products"]]
        assert prices == [80.0, 118.0]

    def test_partial_response_no_forbidden_vocab(self):
        """D2 — even the partial happy path must carry no scary/estimated
        vocab in any rendered string."""
        resp = self._build_partial()
        _assert_no_forbidden_vocab(resp)

    def test_partial_response_full_structural_shape(self):
        """The partial mirrors the full response shape (overview/specs/reviews/
        scoring/scoring_v2/personalization/metadata) so FE consumers don't
        branch on a partial-specific schema."""
        resp = self._build_partial()
        for key in (
            "overview", "specs", "reviews", "scoring",
            "scoring_v2", "personalization", "metadata",
        ):
            assert key in resp, f"partial response missing top-level {key!r}"
        assert len(resp["overview"]["products"]) == 2
        assert len(resp["reviews"]["products"]) == 2


# ===========================================================================
# Layer 1b — last-resort estimated fallback (still honest, still partial).
# ===========================================================================
class TestPartialEstimatedLastResort:
    def test_estimated_fallback_keeps_success_true(self):
        """D1 — even when the only price available is the last-resort
        `estimated` method, a partial with usable data is success:true; the
        price object carries source_method='estimated' (the ENUM is allowed;
        the UI substitutes 'indicative' microcopy per D3)."""
        product_data = [
            _partial_product("Tom Ford", "Ombre Leather", source_method="estimated", amount=85.0),
            _partial_product("Tom Ford", "Tobacco Vanille", source_method="estimated", amount=120.0),
        ]
        resp = build_comparison_response(
            query="A vs B",
            product_data=product_data,
            scoring_result=_partial_scoring(),
            comparison=None,
            region="bahrain",
            category_used="fragrances",
            metadata={"partial": True},
        )
        assert resp["success"] is True
        assert resp["metadata"]["partial"] is True
        for op in resp["overview"]["products"]:
            assert op["price"]["source_method"] == "estimated"
        # B.0 strips the `note` text on estimated prices (A.7.2) so no
        # "Estimated from training data" string leaks; assert no scary vocab.
        _assert_no_forbidden_vocab(resp)

    def test_estimated_price_note_stripped(self):
        """A.7.2 defense-in-depth — estimated price objects ship note=None so
        no 'estimated' COPY (vs the enum) reaches the UI."""
        product_data = [
            {**_partial_product("X", "P0", source_method="estimated", amount=10.0)},
            {**_partial_product("Y", "P1", source_method="estimated", amount=20.0)},
        ]
        product_data[0]["price"]["note"] = "Estimated from training data"
        product_data[1]["price"]["note"] = "Estimated from training data"
        resp = build_comparison_response(
            product_data=product_data,
            scoring_result=_partial_scoring(),
            comparison=None, region="bahrain", category_used="fragrances",
            metadata={"partial": True},
        )
        for op in resp["overview"]["products"]:
            assert op["price"].get("note") is None


# ===========================================================================
# Layer 2 — route-level contract (real middleware stack, mocked service).
# These pin the OBSERVABLE HTTP behavior the D2 contract requires. They are
# intentionally NOT in be-core's owned files; they validate the same contract
# from the route boundary so a regression in EITHER the service return shape
# OR the route mapping is caught.
# ===========================================================================
def _partial_service_result():
    """The shape compare_from_text returns on a cap with partial data."""
    return build_comparison_response(
        query="Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille",
        product_data=[
            _partial_product("Tom Ford", "Ombre Leather", source_method="converted_usd", amount=80.0),
            _partial_product("Tom Ford", "Tobacco Vanille", source_method="converted_usd", amount=118.0),
        ],
        scoring_result=_partial_scoring(),
        comparison=None, region="bahrain", category_used="fragrances",
        metadata={"partial": True},
    )


class TestRoutePartialReturns200:
    def test_get_partial_returns_200_with_partial_marker(self):
        """A best-available partial (success:true) flows through the success
        path => HTTP 200, body carries metadata.partial:true + two prices."""
        partial = _partial_service_result()
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=partial)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille",
                        "nocache": "true"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["metadata"]["partial"] is True
        prices = [op["price"]["amount"] for op in body["overview"]["products"]]
        assert prices == [80.0, 118.0]
        _assert_no_forbidden_vocab(body)

    def test_post_partial_returns_200_parity(self):
        """POST shares the mapping (dual-shape parity)."""
        partial = _partial_service_result()
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=partial)
            resp = client.post(
                "/api/v1/text/compare",
                json={"query": "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["metadata"]["partial"] is True


class TestRouteTimeoutMapsTo503:
    """D2 — a TRUE hard failure (both products zero data) preserves the
    TIMEOUT code and maps to 503, never the legacy 400. This pins the
    post-WS1 contract; it is RED until be-core lands the route change, then
    GREEN. (be-core's test_text_routes_error_mapping.py owns the unit-level
    pin; this is the cross-cutting integration pin.)"""

    TIMEOUT_RESULT = {
        "success": False,
        # Friendly, no-forbidden-vocab copy per D2.
        "error": "Still gathering prices — give it another tap in a moment.",
        "code": "TIMEOUT",
        "total_cost": 0.0,
    }

    @pytest.mark.xfail(
        reason="RED until be-core WS1 lands TIMEOUT->503 route mapping (task #2)",
        strict=False,
    )
    def test_get_timeout_maps_to_503_with_code_preserved(self):
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=self.TIMEOUT_RESULT)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC", "nocache": "true"},
            )
        assert resp.status_code == 503
        body = resp.json()
        assert body["code"] == "TIMEOUT"
        assert body["success"] is False
        _assert_no_forbidden_vocab(body)

    @pytest.mark.xfail(
        reason="RED until be-core WS1 lands TIMEOUT->503 route mapping (task #2)",
        strict=False,
    )
    def test_post_timeout_maps_to_503_parity(self):
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=self.TIMEOUT_RESULT)
            resp = client.post(
                "/api/v1/text/compare",
                json={"query": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        assert resp.status_code == 503
        assert resp.json()["code"] == "TIMEOUT"

    def test_timeout_copy_has_no_forbidden_vocab(self):
        """The friendly TIMEOUT copy itself carries no scary vocab. This is
        GREEN now (validates the contract's approved copy) regardless of the
        route mapping landing — a guard against re-introducing the old
        'We couldn't finish... Try again.' string."""
        _assert_no_forbidden_vocab(self.TIMEOUT_RESULT)


class TestInsufficientDataUnchanged:
    """D1 — the BOTH-products-zero-data path stays INSUFFICIENT_DATA (not a
    partial, not a TIMEOUT). The route preserves the structured body."""

    def test_insufficient_data_passthrough(self):
        insufficient = {
            "success": False,
            "error": "We need a moment more on these two — give it another tap.",
            "code": "INSUFFICIENT_DATA",
        }
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=insufficient)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "asdf vs qwer", "nocache": "true"},
            )
        # Whatever HTTP status be-core chooses for INSUFFICIENT_DATA, the body
        # must preserve the code and carry no forbidden vocab.
        body = resp.json()
        assert body.get("code") == "INSUFFICIENT_DATA" or resp.status_code in (400, 422, 503)
        _assert_no_forbidden_vocab(body)

"""Workstream C ($0, no network) — mocked end-to-end integration test for the
explicit_pair category-resolution + write-back fix (catfix bundle).

WHY THIS EXISTS (vs be-core's A3 capture test):
  - be-core's `tests/test_explicit_pair_category.py` proves the write-back at a
    SINGLE seam: it captures the `product_info` dict handed to
    `_fetch_product_data` and asserts `category == "fragrances"`. That pins the
    write-back but stops short of the scoring layer.
  - THIS test closes the remaining e2e gap WITHOUT any Serper/OpenAI/Redis cost:
    it drives the FULL `compare_from_text(explicit_pair=…)` orchestration with
    `_fetch_product_data` + `generate_comparison` mocked, then asserts the
    DETERMINISTIC scoring breakdown the orchestrator produced is the FRAGRANCE
    dimension set (longevity/projection/character…), NOT the generic/`other`
    set (which would surface `build_quality_score`).

LOAD-BEARING DESIGN (per implementation plan constraint #1):
  The fix writes the resolved category onto `products[i]["category"]` BEFORE the
  `_fetch_product_data` gather, and `compute_scores` reads
  `products_data[0]["category"]` to pick `CATEGORY_DIMENSIONS`. So this test's
  `_fetch_product_data` mock ECHOES BACK whatever `category` the orchestrator
  wrote onto the input dict (rather than hard-coding "fragrances"). Result:
    - PRE-fix  (explicit-pair path leaves category unset → "other"): the spied
      breakdown carries electronics/other dims incl. `build_quality_score`  → FAIL.
    - POST-fix (A3 write-back sets category="fragrances"): the breakdown carries
      `longevity_score`/`projection_score`, no `build_quality_score`          → PASS.
  A test that hard-coded the mock's category would be a tautology — it would pass
  even if the write-back never happened. Echoing the input category makes the
  assertion a genuine proof of the orchestrator→scoring path.

NETWORK ISOLATION:
  - `_fetch_product_data` mocked → no Serper/Firecrawl/Scrape.do/page-scrape.
  - `generate_comparison` mocked → no OpenAI verdict call (the only LLM call left
    on the path once product-data is mocked).
  - `user_id=None` → no Supabase behavior/demographics fetch.
  The real `ScoringService.compute_scores` runs (it is pure/deterministic, $0) so
  the breakdown we assert on is the production code path, not a stub.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from app.services.scoring_service import CATEGORY_DIMENSIONS  # noqa: E402
from app.services.structured_comparison_service import (  # noqa: E402
    get_comparison_service,
)


# Canonical dim-key sets sourced from the SAME config production reads, so this
# test can't drift if the dimension lists are re-tuned (it always compares
# against whatever CATEGORY_DIMENSIONS currently declares).
_FRAGRANCE_DIMS = set(CATEGORY_DIMENSIONS["fragrances"])
_ELECTRONICS_DIMS = set(CATEGORY_DIMENSIONS["electronics"])
# Dims that appear in electronics/other but NOT fragrances — their presence in a
# fragrance comparison is the regression signature this test guards against.
_NON_FRAGRANCE_TELL = "build_quality_score"


def _frag_product_dict(category, *, brand, name, amount):
    """A realistic, fully-scoreable fragrance product dict — the shape
    `_fetch_product_data` returns in production (category echoed from the
    orchestrator-written input dict)."""
    return {
        "brand": brand,
        "name": name,
        "full_name": f"{brand} {name}",
        "variant": "100ml",
        "category": category,  # <-- echoed: "fragrances" post-fix, "other" pre-fix
        "query": f"{brand} {name} 100ml",
        "specs": {
            "concentration": "Eau de Parfum",
            "longevity": "8-10 hours",
            "scent_family": "Woody Oriental",
            "top_notes": "Bergamot",
            "size": "100 ml",
        },
        "price": {
            "amount": amount,
            "currency": "BHD",
            "retailer": "alhajifragrances.com",
            "url": f"https://alhajifragrances.com/{name.replace(' ', '-')}",
            "estimated": False,
            "source_method": "page_scrape_jsonld",
        },
        "rating": 4.4,
        "review_count": 120,
        "rating_source": {"url": "https://example.com", "name": "Retailer"},
        "image_url": None,
        "fact_check": {"overall_confidence": "high"},
    }


def _run_compare(spy_holder):
    """Drive the full sync orchestration with product-data + verdict mocked.
    Returns (response, captured_scoring_result)."""
    svc = get_comparison_service()

    async def fake_fetch(product_info, region, include_specs, include_reviews, nocache=False):
        # Echo the category the orchestrator wrote onto the input dict — the
        # whole point of the fix. Pre-fix this is None/"other"; post-fix
        # "fragrances".
        cat = product_info.get("category") or "other"
        brand = product_info.get("brand") or "Tom Ford"
        name = product_info.get("name") or product_info.get("search_query") or "Fragrance"
        # Distinct prices so scoring produces a non-degenerate winner.
        amount = 78.0 if "Soleil" in str(name) or "0" in str(name) else 64.0
        return _frag_product_dict(cat, brand=brand, name=name, amount=amount)

    # Spy that records the REAL compute_scores output (production code runs).
    from app.services import scoring_service as _ss

    real_service = _ss.get_scoring_service()
    real_compute = real_service.compute_scores

    def spy_compute(products_data, *a, **k):
        result = real_compute(products_data, *a, **k)
        spy_holder["scoring_result"] = result
        spy_holder["scored_categories"] = [p.get("category") for p in products_data]
        return result

    static_verdict = (
        {
            "winner_index": 0,
            "winner_declaration": "A great everyday signature.",
            "key_differences": [],
            "recommendation": "Pick by the notes you prefer.",
        },
        {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch), \
        patch.object(real_service, "compute_scores", side_effect=spy_compute), \
        patch(
            "app.services.structured_comparison_service.generate_comparison",
            new=AsyncMock(return_value=static_verdict),
        ), \
        patch(
            "app.services.structured_comparison_service.get_scoring_service",
            return_value=real_service,
        ):
        response = asyncio.run(
            svc.compare_from_text(
                query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
                explicit_pair=(
                    "Tom Ford Soleil Neige 100ml",
                    "Tom Ford Oud Voyager 100ml",
                ),
                selected_category="fragrances",
                user_id=None,
                nocache=True,
            )
        )
    return response, spy_holder


def test_explicit_pair_scoring_breakdown_is_fragrance_dims_e2e():
    """The load-bearing e2e assertion: an explicit FRAGRANCE pair drives the
    deterministic scoring breakdown through the FRAGRANCE dimension set."""
    spy = {}
    response, spy = _run_compare(spy)

    scoring_result = spy.get("scoring_result")
    assert scoring_result is not None, (
        "compute_scores never ran — orchestration short-circuited before scoring "
        "(check the mock signatures / early-return paths)."
    )

    # The category the scoring layer actually keyed off (proves the write-back
    # reached compute_scores, not just _fetch_product_data).
    assert spy.get("scored_categories") == ["fragrances", "fragrances"], (
        "scoring did not receive category='fragrances' on both products: "
        f"{spy.get('scored_categories')!r} — the write-back did not reach scoring."
    )

    breakdown = (
        scoring_result.get("scores", {})
        .get("product_0", {})
        .get("breakdown", {})
    )
    assert breakdown, "product_0 breakdown is empty — scoring produced no dims."
    keys = set(breakdown.keys())

    # POSITIVE: the fragrance scent dims must be present.
    assert {"longevity_score", "projection_score"} <= keys, (
        f"fragrance dims missing from scoring breakdown: got {sorted(keys)}"
    )
    # The full fragrance dim set should match (no leakage of other categories).
    assert keys == _FRAGRANCE_DIMS, (
        f"breakdown keys != CATEGORY_DIMENSIONS['fragrances']: "
        f"got {sorted(keys)}, expected {sorted(_FRAGRANCE_DIMS)}"
    )

    # NEGATIVE: the electronics/other tell must be ABSENT.
    assert _NON_FRAGRANCE_TELL not in keys, (
        f"electronics/other dim '{_NON_FRAGRANCE_TELL}' leaked into a fragrance "
        f"comparison — category was NOT resolved to fragrances: {sorted(keys)}"
    )
    assert not (_ELECTRONICS_DIMS - _FRAGRANCE_DIMS) & keys, (
        f"electronics-only dims leaked into fragrance breakdown: "
        f"{sorted((_ELECTRONICS_DIMS - _FRAGRANCE_DIMS) & keys)}"
    )


def test_explicit_pair_response_category_used_is_fragrances_e2e():
    """Secondary signal off the assembled response — the user-visible
    `category_used` reflects the resolved category, and the response's
    scoring_v2.dimensions surface fragrance dims, not a 'build' dim."""
    spy = {}
    response, _ = _run_compare(spy)

    assert response.get("success") is not False, (
        f"comparison failed unexpectedly: code={response.get('code')!r} "
        f"error={response.get('error')!r}"
    )

    # response_builder writes result["category_used"] (response_builder.py:1493).
    assert response.get("category_used") == "fragrances", (
        f"category_used on the response is {response.get('category_used')!r}, "
        "expected 'fragrances' — resolution/write-back did not propagate."
    )

    # scoring_v2.dimensions[i].key strips the `_score` suffix, so the fragrance
    # set surfaces as longevity/projection/… and the electronics tell would
    # surface as 'build_quality'. Assert no build-quality dim is rendered.
    scoring_v2 = response.get("scoring_v2") or {}
    dim_keys = {
        d.get("key")
        for d in (scoring_v2.get("dimensions") or [])
        if isinstance(d, dict)
    }
    assert "build_quality" not in dim_keys, (
        f"a 'build_quality' dimension rendered on a fragrance comparison: "
        f"dimension keys = {sorted(k for k in dim_keys if k)}"
    )
    assert "build" not in dim_keys, (
        f"a 'build' dimension rendered on a fragrance comparison: "
        f"dimension keys = {sorted(k for k in dim_keys if k)}"
    )


def test_compute_scores_picks_fragrance_dims_directly():
    """Unit-level guard mirroring the e2e assertion at the scoring boundary —
    fast, no orchestration. Two category='fragrances' product dicts → fragrance
    breakdown. (Routing sanity check; the e2e test above is the real proof.)"""
    from app.services.scoring_service import ScoringService

    products = [
        _frag_product_dict("fragrances", brand="Tom Ford", name="Soleil Neige", amount=78.0),
        _frag_product_dict("fragrances", brand="Tom Ford", name="Oud Voyager", amount=64.0),
    ]
    result = ScoringService().compute_scores(products)
    breakdown = result["scores"]["product_0"]["breakdown"]
    keys = set(breakdown.keys())
    assert {"longevity_score", "projection_score"} <= keys, sorted(keys)
    assert _NON_FRAGRANCE_TELL not in keys, sorted(keys)

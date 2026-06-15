"""NO-NETWORK companion to _frag_pipeline_trace.py.

The trace harness runs the LIVE pipeline (burns Serper/Firecrawl). This one
exercises the WS1 fail-fast / best-available-partial path with FULLY MOCKED
internals — zero budget, no Redis/Serper/Firecrawl/OpenAI — so QA can verify
the graceful behavior on every run without spending a credit.

Drives the REAL `compare_from_text` hard-cap wrapper (be-core WS1 code) two
ways:
  A. impl exceeds the cap WITH partial state stashed -> expect success:true +
     metadata.partial:true + two honest prices + a templated verdict.
  B. impl exceeds the cap with NO usable data -> expect the INSUFFICIENT_DATA
     path (success:false, code:INSUFFICIENT_DATA), NOT a partial.

Until be-core lands WS1, scenario A currently surfaces the legacy
{success:false, code:TIMEOUT} (the old wrapper). This harness PRINTS the
observed shape so the before/after is obvious; it does NOT assert (the pytest
suite tests/test_timeout_partial_integration.py owns the assertions).

Run:  python .qa-bias-rerun/_partial_assembly_mock_harness.py
"""
import os
import sys
import json
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hermetic: short cap so the timeout fires fast; no real creds needed.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["UPSTASH_REDIS_URL"] = ""              # cache-disabled
os.environ["UPSTASH_REDIS_TOKEN"] = ""
os.environ["STREAM_HARD_CAP_SECONDS"] = "2"        # fire the cap quickly in scenario A
logging.basicConfig(level=logging.WARNING, format="%(message)s")

from unittest.mock import patch

from app.services.structured_comparison_service import get_comparison_service
from app.services.response_builder import build_comparison_response


def _partial_product(brand, name, *, source_method, amount):
    return {
        "brand": brand, "name": name, "full_name": f"{brand} {name}",
        "category": "fragrances",
        "price": {
            "amount": amount, "currency": "BHD",
            "retailer": "iHerb" if source_method == "converted_usd" else None,
            "url": None, "source_method": source_method,
            "estimated": source_method == "estimated",
        },
        "best_price": amount,
        "specs": {"volume_ml": 100, "concentration": "EDP"},
        "reviews": {"review_summary": {
            "overall_sentiment": "positive", "consensus": "long-lasting",
            "highlights": [], "review_volume": "moderate", "agreement_level": "moderate",
        }},
        "rating": 4.4, "rating_source": None, "review_count": 120,
        "image_url": None, "fact_check": {},
    }


def _scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 64.0}, "product_1": {"overall": 55.0}},
        "win_margin": 9.0, "tradeoff_pairs": [], "value_badges": [],
        "comparison_quality": "normal", "personalization": {"applied_shifts": []},
        "price_tiers": {}, "scoring_method": "category_weighted",
    }


def _partial_result():
    """The best-available partial body the wrapper should assemble on cap."""
    return build_comparison_response(
        query="Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille",
        product_data=[
            _partial_product("Tom Ford", "Ombre Leather", source_method="converted_usd", amount=80.0),
            _partial_product("Tom Ford", "Tobacco Vanille", source_method="converted_usd", amount=118.0),
        ],
        scoring_result=_scoring(), comparison=None, region="bahrain",
        category_used="fragrances", metadata={"partial": True},
    )


def _print_result(label, r):
    print(f"\n===== {label} =====")
    print("  success:", r.get("success"), "| code:", r.get("code"))
    meta = r.get("metadata") or {}
    print("  metadata.partial:", meta.get("partial"))
    prods = r.get("products") or (r.get("overview") or {}).get("products") or []
    for p in prods:
        pr = p.get("price") or {}
        print(f"    {str(p.get('name'))[:30]:30} {pr.get('amount')} {pr.get('currency')} "
              f"method={pr.get('source_method')}")
    fv = ((r.get("scoring_v2") or {}).get("factual_verdict")) or {}
    if fv:
        print("  verdict.line1:", str(fv.get("line1"))[:80])
    blob = json.dumps(r, default=str, ensure_ascii=False).lower()
    scary = [t for t in ("couldn't", "try again", "failed to", "تعذر", "فشل", "تقدير")
             if t in blob]
    print("  forbidden_vocab_hits:", scary or "NONE")


async def main():
    svc = get_comparison_service()

    # --- Scenario A: cap fires WITH partial state available ---
    # WS1 reads the partial from self._partial_* (stashed by the impl as stages
    # land), NOT from the impl return value. The mocked impl stashes that state
    # then hangs, so the timeout handler assembles the real partial.
    pd = [
        _partial_product("Tom Ford", "Ombre Leather", source_method="converted_usd", amount=80.0),
        _partial_product("Tom Ford", "Tobacco Vanille", source_method="converted_usd", amount=118.0),
    ]

    async def slow_impl_with_partial(*_a, **_k):
        svc._partial_build_ctx = {
            "query": "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille",
            "region": "bahrain", "from_cache": False, "user_preferences": None,
            "category_used": "fragrances",
        }
        svc._partial_product_data = pd
        svc._partial_scoring_result = _scoring()
        svc._partial_comparison = {}
        svc._partial_product_names = [p["name"] for p in pd]
        svc._shopping_items_cache = {}
        svc.total_cost = 0.017
        svc.api_calls = 4
        svc.gpt_calls = 2
        svc.serper_calls = 6
        await asyncio.sleep(10)  # exceed the 2s cap
        return _partial_result()

    with patch.object(svc, "_compare_from_text_impl", side_effect=slow_impl_with_partial):
        rA = await svc.compare_from_text(
            "Tom Ford Ombre Leather vs Tom Ford Tobacco Vanille", region="bahrain",
        )
    _print_result("A: cap fired, partial available (expect success:true + partial:true post-WS1)", rA)

    # --- Scenario B: cap fires with NO usable data ---
    # Clear the stash the real impl would have reset (we patched it out).
    async def slow_impl_no_data(*_a, **_k):
        svc._partial_product_data = None
        svc._partial_scoring_result = None
        svc._partial_comparison = None
        svc._partial_product_names = None
        await asyncio.sleep(10)
        return {"success": False, "code": "INSUFFICIENT_DATA",
                "error": "We need a moment more on these two."}

    with patch.object(svc, "_compare_from_text_impl", side_effect=slow_impl_no_data):
        rB = await svc.compare_from_text("asdf vs qwer", region="bahrain")
    _print_result("B: cap fired, no usable data (expect INSUFFICIENT_DATA)", rB)

    print("\n(NOTE: pre-WS1 the wrapper returns {success:false, code:TIMEOUT} for A; "
          "post-WS1 expect success:true + metadata.partial:true. Assertions live in "
          "tests/test_timeout_partial_integration.py.)")


if __name__ == "__main__":
    asyncio.run(main())

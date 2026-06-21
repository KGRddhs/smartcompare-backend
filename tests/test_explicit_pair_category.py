"""A3/A4: per-product category WRITE-BACK proof (sync + stream).

THE load-bearing proof for this bundle is the CAPTURE test: patch
_fetch_product_data, drive an explicit fragrance pair through compare_from_text
/ compare_from_text_streaming, and assert the captured product_info["category"]
== "fragrances". Scoring (compute_scores reads products_data[0]["category"]),
spec-schema selection, and category-aware source discovery ALL key off the
per-product `category` field via _fetch_product_data -> result["category"] —
NOT `category_used`. So a green fragrance-dims test alone is only a routing
sanity check; the write-back is what this file pins.
"""
import asyncio
import pytest
from unittest.mock import patch

from app.services.structured_comparison_service import get_comparison_service


# ============================================
# A3: SYNC path write-back (the load-bearing proof)
# ============================================

def test_explicit_pair_selected_category_is_authority_sync():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):   # _fetch_product_data(self, product_info, region, ...)
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")   # capture happens BEFORE the raise

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
                explicit_pair=("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"),
                selected_category="fragrances",
            ))
        except Exception:
            pass

    assert captured, "_fetch_product_data was never reached"
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"per-product category not written back: {[c.get('category') for c in captured]}"


def test_explicit_pair_detection_wins_over_chip_sync():
    # Names carry fragrance words -> detection overrides a wrong electronics chip.
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="Dior Sauvage perfume vs Creed Aventus cologne",
                explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                selected_category="electronics",   # wrong chip
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"detection should override chip: {[c.get('category') for c in captured]}"


def test_explicit_pair_supplements_still_classified_sync():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="NOW Foods Vitamin D3 vs Solgar Vitamin D3",
                explicit_pair=("NOW Foods Vitamin D3", "Solgar Vitamin D3"),
                selected_category=None,
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "supplements" for c in captured), \
        f"supplements not classified: {[c.get('category') for c in captured]}"


def test_explicit_pair_no_chip_no_detection_escalates_via_llm_sync():
    # Brand-only names + no chip -> resolve_category escalates -> classify_category_llm
    # is consulted. Mock it to return fragrances and assert it lands on the products.
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    async def fake_llm(_texts):
        return "fragrances"

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch), \
         patch("app.services.structured_comparison_service.classify_category_llm",
               side_effect=fake_llm):
        try:
            asyncio.run(svc.compare_from_text(
                query="Soleil Neige vs Oud Voyager",
                explicit_pair=("Soleil Neige", "Oud Voyager"),
                selected_category=None,
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"A2b escalation result not written back: {[c.get('category') for c in captured]}"


# ============================================
# A4: STREAMING path write-back + sync/stream parity
# ============================================

def test_streaming_explicit_pair_selected_category_is_authority():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    async def drive():
        agen = svc.compare_from_text_streaming(
            query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
            explicit_pair=("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"),
            selected_category="fragrances",
        )
        try:
            async for _ in agen:
                pass
        except Exception:
            pass

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(drive())
        except Exception:
            pass

    assert captured, "_fetch_product_data was never reached (stream)"
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"per-product category not written back (stream): {[c.get('category') for c in captured]}"


def test_sync_stream_category_parity():
    """Same explicit pair + chip -> same resolved category on both paths."""
    svc = get_comparison_service()

    def capture_sync():
        cap = []

        async def fake_fetch(product_info, *a, **k):
            cap.append(dict(product_info))
            raise RuntimeError("stop")

        with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
            try:
                asyncio.run(svc.compare_from_text(
                    query="Dior Sauvage perfume vs Creed Aventus cologne",
                    explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                    selected_category=None,
                ))
            except Exception:
                pass
        return [c.get("category") for c in cap]

    def capture_stream():
        cap = []

        async def fake_fetch(product_info, *a, **k):
            cap.append(dict(product_info))
            raise RuntimeError("stop")

        async def drive():
            agen = svc.compare_from_text_streaming(
                query="Dior Sauvage perfume vs Creed Aventus cologne",
                explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                selected_category=None,
            )
            try:
                async for _ in agen:
                    pass
            except Exception:
                pass

        with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
            try:
                asyncio.run(drive())
            except Exception:
                pass
        return [c.get("category") for c in cap]

    sync_cats = capture_sync()
    stream_cats = capture_stream()
    assert sync_cats and stream_cats
    assert set(sync_cats) == set(stream_cats) == {"fragrances"}, \
        f"sync/stream parity broken: sync={sync_cats} stream={stream_cats}"


# ============================================
# Routing sanity check (NOT the write-back proof — duplicates
# test_category_keystone_scoring.py): fragrance dicts -> fragrance dims.
# ============================================

# ============================================
# _resolve_pair_category — parser-hint seam (A3/A4 helper, the Option-B home of
# the parser-path category authority). The LLM-emitted per-product `category`
# outranks a user chip when the NAMES are blind; explicit_pair/vision (whose
# field is the deterministic stub) are unaffected.
# ============================================

def test_resolve_pair_category_parser_hint_overrides_chip():
    from app.services.structured_comparison_service import _resolve_pair_category
    # Parser path: brand-only names + parser category="electronics" + chip="grocery".
    products = [
        {"category": "electronics", "search_query": "Apple iPhone 15", "name": "iPhone 15"},
        {"category": "electronics", "search_query": "Samsung Galaxy S24", "name": "Galaxy S24"},
    ]
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "grocery", parser_path=True)
    )
    assert cat == "electronics"
    assert switched is True
    assert original == "grocery"


def test_resolve_pair_category_explicit_name_hit_drives():
    from app.services.structured_comparison_service import _resolve_pair_category
    # EXPLICIT/vision path (parser_path=False): the per-product field is only the
    # deterministic stub, so a confident NAME hit (perfume/cologne) drives. (On the
    # q= parser path the LLM category would be authoritative instead — see the
    # FIX-1 block below.)
    products = [
        {"category": "other", "search_query": "Dior Sauvage perfume", "name": "Dior Sauvage perfume"},
        {"category": "other", "search_query": "Creed Aventus cologne", "name": "Creed Aventus cologne"},
    ]
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=False)
    )
    assert cat == "fragrances"


def test_resolve_pair_category_explicit_stub_other_uses_chip():
    from app.services.structured_comparison_service import _resolve_pair_category
    # explicit_pair shape: field is the "other" stub, names blind -> chip honored.
    products = [
        {"category": "other", "search_query": "Soleil Neige", "name": "Soleil Neige"},
        {"category": "other", "search_query": "Oud Voyager", "name": "Oud Voyager"},
    ]
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "fragrances", parser_path=False)
    )
    assert cat == "fragrances"
    assert switched is False


def test_resolve_pair_category_blind_everything_escalates():
    from app.services.structured_comparison_service import _resolve_pair_category
    products = [
        {"category": "other", "search_query": "Mystery A", "name": "Mystery A"},
        {"category": "other", "search_query": "Mystery B", "name": "Mystery B"},
    ]

    async def fake_llm(_names):
        return "skincare"

    with patch("app.services.structured_comparison_service.classify_category_llm",
               side_effect=fake_llm):
        cat, switched, original = asyncio.run(
            _resolve_pair_category(products, None, parser_path=False)
        )
    assert cat == "skincare"


# ============================================
# FIX-1 (HIGH) — q= PARSER path: the LLM-emitted category is AUTHORITATIVE.
# A blunt category WORD inside a product NAME (is_supplement_query 'iron'/'vitamin',
# or 'skin'/'food' synonyms) must NOT override the LLM's full-context judgment from
# parse_product_query. classify_category_from_text is the FALLBACK only when the LLM
# said 'other'. (Confirmed misclassifications on merged code: iron->supplements,
# vitamin->supplements, skin->skincare, food->grocery.)
# ============================================

def _parser_products(cat0, name0, cat1, name1):
    # Parser-path shape: products[i]['category'] is the LLM's real per-product
    # judgment from parse_product_query (NOT the deterministic stub).
    return [
        {"category": cat0, "search_query": name0, "name": name0, "brand": ""},
        {"category": cat1, "search_query": name1, "name": name1, "brand": ""},
    ]


def test_parser_path_llm_category_beats_iron_supplement_keyword():
    from app.services.structured_comparison_service import _resolve_pair_category
    # "Tefal steam iron vs Philips steam iron" — is_supplement_query fires on 'iron'
    # in classify_category_from_text, but the LLM said electronics. LLM wins.
    products = _parser_products(
        "electronics", "Tefal steam iron", "electronics", "Philips steam iron"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "electronics", f"iron-keyword overrode the LLM category: {cat}"


def test_parser_path_llm_category_beats_vitamin_keyword():
    from app.services.structured_comparison_service import _resolve_pair_category
    # "Garnier Vitamin C serum ..." — 'vitamin' fires is_supplement_query, LLM said skincare.
    products = _parser_products(
        "skincare", "Garnier Vitamin C serum", "skincare", "The Ordinary Vitamin C serum"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "skincare", f"vitamin-keyword overrode the LLM category: {cat}"


def test_parser_path_llm_category_beats_skin_keyword():
    from app.services.structured_comparison_service import _resolve_pair_category
    # "... concealer" — 'skin' synonym fires (skincare), but the LLM said makeup.
    products = _parser_products(
        "makeup", "Revolution Pro concealer", "makeup", "Catrice True Skin concealer"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "makeup", f"skin-keyword overrode the LLM category: {cat}"


def test_parser_path_llm_category_beats_food_keyword():
    from app.services.structured_comparison_service import _resolve_pair_category
    # "Lock and Lock food container set ..." — 'food' fires (grocery), LLM said other.
    products = _parser_products(
        "other", "Lock and Lock food container set", "other", "Sistema food storage set"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "other", f"food-keyword overrode the LLM category: {cat}"


def test_parser_path_llm_other_is_authoritative_no_name_fallback():
    from app.services.structured_comparison_service import _resolve_pair_category
    # FIX-1: on the q= path the LLM saw the FULL names ("perfume"/"cologne") and
    # still returned "other" — that deliberate judgment is final. We do NOT fall
    # back to a blunt name keyword (that's exactly what caused the food->grocery
    # false positive). A real perfume query would have the LLM return fragrances,
    # not "other", so this scenario is the safety contract, not a realistic miss.
    products = _parser_products(
        "other", "Dior Sauvage perfume", "other", "Creed Aventus cologne"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "other", "parser-path LLM 'other' must not be overridden by a name keyword"


def test_parser_path_llm_other_with_chip_honors_chip():
    from app.services.structured_comparison_service import _resolve_pair_category
    # LLM abstained ("other") on the parser path AND a real chip is set -> chip honored.
    products = _parser_products(
        "other", "Mystery gadget A", "other", "Mystery gadget B"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "electronics", parser_path=True)
    )
    assert cat == "electronics"
    assert switched is False


def test_parser_path_iphone_galaxy_still_other_when_llm_other():
    from app.services.structured_comparison_service import _resolve_pair_category
    # The common case: brand/model names classify_category_from_text -> 'other',
    # and if the LLM also said 'other' the result stays 'other' (no false hit).
    products = _parser_products(
        "other", "iPhone 15", "other", "Galaxy S24"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=True)
    )
    assert cat == "other"


def test_parser_path_llm_category_overrides_conflicting_chip():
    from app.services.structured_comparison_service import _resolve_pair_category
    # Parser LLM=electronics + chip=grocery -> electronics + switched (aligns with
    # test_streaming::test_category_switching_in_streaming).
    products = _parser_products(
        "electronics", "Apple iPhone 15", "electronics", "Samsung Galaxy S24"
    )
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "grocery", parser_path=True)
    )
    assert cat == "electronics"
    assert switched is True
    assert original == "grocery"


def test_explicit_path_name_detection_still_authoritative():
    from app.services.structured_comparison_service import _resolve_pair_category
    # explicit_pair/vision (parser_path=False): the per-product field is just the
    # deterministic stub, so NAME detection drives. A fragrance name -> fragrances.
    products = [
        {"category": "other", "search_query": "Dior Sauvage perfume", "name": "Dior Sauvage perfume", "brand": ""},
        {"category": "other", "search_query": "Creed Aventus cologne", "name": "Creed Aventus cologne", "brand": ""},
    ]
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, None, parser_path=False)
    )
    assert cat == "fragrances"


# ============================================
# CLEANUP-1 — explicit/vision (parser_path=False) precedence cases ported from the
# soon-to-be-deleted resolve_category's 12 unit tests, so deleting the prod-dead
# resolve_category loses NO precedence coverage. (resolve_category returned a
# needs_llm sentinel for the caller; _resolve_pair_category invokes
# classify_category_llm itself, so the "escalation" cases mock it and assert the
# returned value — same semantics, inlined.)
# ============================================

def _explicit_products(name0, name1):
    # explicit/vision shape: per-product "category" is only the deterministic stub
    # (== classify_category_from_text(name)); we set it to that to mirror prod.
    from app.services.extraction_service import classify_category_from_text
    return [
        {"category": classify_category_from_text(name0), "search_query": name0, "name": name0, "brand": ""},
        {"category": classify_category_from_text(name1), "search_query": name1, "name": name1, "brand": ""},
    ]


def test_explicit_detection_overrides_conflicting_chip_switched():
    # Ported resolve_category #3: names say fragrances, chip says electronics ->
    # detection wins, switched=True, original=the chip.
    from app.services.structured_comparison_service import _resolve_pair_category
    products = _explicit_products("Dior Sauvage perfume", "Creed Aventus cologne")
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "electronics", parser_path=False)
    )
    assert cat == "fragrances"
    assert switched is True
    assert original == "electronics"


def test_explicit_other_chip_never_clobbers_name_hit():
    # Ported #4: chip="other" is not a real opinion -> name hit wins, switched=False.
    from app.services.structured_comparison_service import _resolve_pair_category
    products = _explicit_products("gaming laptop", "business laptop")
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "other", parser_path=False)
    )
    assert cat == "electronics"
    assert switched is False
    assert original is None


def test_explicit_unknown_chip_never_clobbers_name_hit():
    # Ported #5: a bogus chip canonicalizes to "other" -> ignored, name hit wins.
    from app.services.structured_comparison_service import _resolve_pair_category
    products = _explicit_products("Dior Sauvage perfume", "Creed Aventus cologne")
    cat, switched, original = asyncio.run(
        _resolve_pair_category(products, "totally-bogus-category", parser_path=False)
    )
    assert cat == "fragrances"
    assert switched is False


def test_explicit_blind_names_other_chip_still_escalates():
    # Ported #7: blind names + chip="other" -> escalate to classify_category_llm.
    from app.services.structured_comparison_service import _resolve_pair_category
    products = _explicit_products("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml")

    async def fake_llm(_names):
        return "fragrances"

    with patch("app.services.structured_comparison_service.classify_category_llm",
               side_effect=fake_llm):
        cat, switched, original = asyncio.run(
            _resolve_pair_category(products, "other", parser_path=False)
        )
    assert cat == "fragrances"  # the escalation result is returned
    assert switched is False


def test_explicit_empty_names_with_chip_honors_chip():
    # Ported #11: empty names + a real chip -> chip honored, no escalation.
    from app.services.structured_comparison_service import _resolve_pair_category
    cat, switched, original = asyncio.run(
        _resolve_pair_category([], "fragrances", parser_path=False)
    )
    assert cat == "fragrances"
    assert switched is False


def test_explicit_empty_names_no_chip_escalates():
    # Ported #12: empty names + no chip -> escalate to classify_category_llm.
    from app.services.structured_comparison_service import _resolve_pair_category

    async def fake_llm(_names):
        return "other"

    with patch("app.services.structured_comparison_service.classify_category_llm",
               side_effect=fake_llm):
        cat, switched, original = asyncio.run(
            _resolve_pair_category([], None, parser_path=False)
        )
    assert cat == "other"


def test_fragrance_dicts_score_with_fragrance_dims():
    from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS
    products = [
        {"brand": "Tom Ford", "name": "A", "category": "fragrances",
         "specs": {"longevity": "8 hours", "concentration": "edp"},
         "price": {"amount": 80, "currency": "BHD"}},
        {"brand": "Creed", "name": "B", "category": "fragrances",
         "specs": {"longevity": "10 hours", "concentration": "edp"},
         "price": {"amount": 90, "currency": "BHD"}},
    ]
    result = ScoringService().compute_scores(products)
    keys = set()
    for pk in ("product_0", "product_1"):
        keys |= set(result["scores"][pk]["breakdown"].keys())
    # fragrance dims present, electronics/other 'build' dim absent
    assert "longevity_score" in keys, f"no longevity dim: {keys}"
    assert "projection_score" in keys, f"no projection dim: {keys}"
    assert "build_score" not in keys, f"build_score leaked into fragrance dims: {keys}"
    assert keys == set(CATEGORY_DIMENSIONS["fragrances"])

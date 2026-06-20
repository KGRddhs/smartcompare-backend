"""Tests for resolve_category() + classify_category_llm() — A2 / A2b.

resolve_category(product_names, selected_category) decides the authoritative
category for an explicit-pair / vision comparison via a precedence ladder:

  1. confident deterministic detection on the product NAMES wins (overrides a
     conflicting chip -> switched=True);
  2. else a real chip (selected_category, not "other"/unknown) is honored;
  3. else (blind detection AND no usable chip) -> ("other", False, True)
     escalation sentinel -> caller fires the A2b GPT-mini classifier.

classify_category_llm(texts) is a NEW classify-only gpt-4o-mini call (NOT
parse_product_query) that returns one canonical key, "other" on any error.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.extraction_service import resolve_category


# ============================================
# A2: resolve_category precedence
# ============================================

def test_confident_detection_wins_no_chip():
    # Combined names carry a fragrance word -> fragrances, no chip needed.
    cat, switched, needs_llm = resolve_category(
        ["Dior Sauvage perfume", "Creed Aventus cologne"], None
    )
    assert cat == "fragrances"
    assert switched is False
    assert needs_llm is False


def test_chip_used_when_detection_blind():
    # Brand/model only (no category word) -> detection blind -> honor the chip.
    cat, switched, needs_llm = resolve_category(
        ["Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"], "fragrances"
    )
    assert cat == "fragrances"
    assert switched is False
    assert needs_llm is False


def test_confident_detection_overrides_conflicting_chip():
    # Names say fragrances, chip says electronics -> detection wins, switched=True.
    cat, switched, needs_llm = resolve_category(
        ["Dior Sauvage perfume", "Creed Aventus cologne"], "electronics"
    )
    assert cat == "fragrances"
    assert switched is True
    assert needs_llm is False


def test_other_chip_never_clobbers_confident_detection():
    cat, switched, needs_llm = resolve_category(
        ["gaming laptop", "business laptop"], "other"
    )
    assert cat == "electronics"
    assert switched is False     # "other" sel is not a real opinion -> no switch flagged
    assert needs_llm is False


def test_unknown_chip_never_clobbers_confident_detection():
    # An unrecognized chip canonicalizes to "other" -> ignored, detection wins.
    cat, switched, needs_llm = resolve_category(
        ["Dior Sauvage perfume", "Creed Aventus cologne"], "totally-bogus-category"
    )
    assert cat == "fragrances"
    assert switched is False
    assert needs_llm is False


def test_blind_detection_no_chip_returns_needs_llm():
    cat, switched, needs_llm = resolve_category(
        ["Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"], None
    )
    assert cat == "other"
    assert switched is False
    assert needs_llm is True


def test_blind_detection_other_chip_returns_needs_llm():
    # chip == "other" is not a real opinion -> still escalate.
    cat, switched, needs_llm = resolve_category(
        ["Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"], "other"
    )
    assert cat == "other"
    assert needs_llm is True


def test_mixed_token_pair_resolves_both():
    # One fragrance name + one ambiguous brand-only name -> a confident hit on
    # the combined string still resolves the pair to fragrances.
    cat, switched, needs_llm = resolve_category(
        ["Dior Sauvage perfume", "Bleu de Chanel"], None
    )
    assert cat == "fragrances"
    assert needs_llm is False


def test_supplement_pair_classified():
    cat, switched, needs_llm = resolve_category(
        ["NOW Foods Vitamin D3", "Solgar Vitamin D3"], None
    )
    assert cat == "supplements"
    assert needs_llm is False


def test_chip_honored_when_detection_blind_supplements():
    cat, switched, needs_llm = resolve_category(
        ["Mystery Brand A", "Mystery Brand B"], "skincare"
    )
    assert cat == "skincare"
    assert needs_llm is False


def test_empty_names_with_chip():
    cat, switched, needs_llm = resolve_category([], "fragrances")
    assert cat == "fragrances"
    assert needs_llm is False


def test_empty_names_no_chip_escalates():
    cat, switched, needs_llm = resolve_category([], None)
    assert cat == "other"
    assert needs_llm is True


# ============================================
# A2b: classify_category_llm (bounded gpt-4o-mini, classify-only)
# ============================================

def _mock_openai_response(content: str):
    """Build a fake OpenAI chat.completions response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_classify_category_llm_returns_canonical():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("fragrances")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(
            ["Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"]
        )
    assert result == "fragrances"


@pytest.mark.asyncio
async def test_classify_category_llm_canonicalizes_messy_output():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("  Fragrances  ")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "fragrances"


@pytest.mark.asyncio
async def test_classify_category_llm_error_returns_other():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "other"


@pytest.mark.asyncio
async def test_classify_category_llm_unknown_output_returns_other():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("kitchenware")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "other"

"""Regression tests for the illegal_drugs `opium` blocklist tightening.

B0-UnfinishedBiz audit (B0-D 24-query bias matrix Q16) surfaced that the L1
query prefilter rejected legitimate fragrance queries containing "Opium"
(e.g., YSL Black Opium) because the blocklist held the bare token
`"opium"`. The fix replaces the single-word entry with four multi-word
phrases that preserve the original intent (block illegal-drug references)
without colliding with legitimate product names.

Audit lives in `app/data/content_blocklist.json` (illegal_drugs.en).
"""
from __future__ import annotations

import os

import pytest

# Ensure the OpenAI client can instantiate at import time — these tests touch
# the singleton via the L1 path which loads the service lazily.
os.environ.setdefault("OPENAI_API_KEY", "test-key-noop-blocklist-opium")

import app.services.content_safety_service as css


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    monkeypatch.setattr(css, "_service", None)
    yield


@pytest.fixture
def service():
    return css.get_content_safety_service()


def test_ysl_black_opium_passes_l1_prefilter(service):
    """The flagship YSL Black Opium fragrance must NOT trip the blocklist."""
    result = service.check_query_intent("YSL Black Opium vs Lancome La Vie Est Belle")
    assert result.allowed is True, (
        f"Legitimate fragrance query was blocked: reason={result.reason}, "
        f"match={result.blocklist_match}"
    )
    assert result.reason is None


def test_opium_tincture_blocked(service):
    """The new multi-word phrase preserves illegal-drug intent."""
    result = service.check_query_intent("opium tincture for sale")
    assert result.allowed is False
    assert result.reason == "illegal_drugs"
    assert result.blocklist_match == "opium tincture"


def test_opium_poppy_blocked(service):
    """`opium poppy` blocks the cultivation/raw-source phrasing."""
    result = service.check_query_intent("how to grow opium poppy")
    assert result.allowed is False
    assert result.reason == "illegal_drugs"
    assert result.blocklist_match == "opium poppy"


def test_other_opium_compound_phrases_blocked(service):
    """Spot-check the remaining `raw opium` and `opium den` entries."""
    for phrase in ("raw opium for export", "looking for an opium den"):
        result = service.check_query_intent(phrase)
        assert result.allowed is False, f"Phrase {phrase!r} was not blocked"
        assert result.reason == "illegal_drugs"


def test_bare_opium_in_brand_name_no_longer_blocks(service):
    """Standalone `Opium` in fragrance brand context must pass."""
    for phrase in (
        "YSL Opium perfume",
        "Black Opium eau de parfum",
        "Opium Pour Homme review",
    ):
        result = service.check_query_intent(phrase)
        assert result.allowed is True, (
            f"Brand fragrance phrase {phrase!r} blocked: "
            f"reason={result.reason} match={result.blocklist_match}"
        )

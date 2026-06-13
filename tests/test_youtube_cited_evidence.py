"""L2.4 — YouTube cited-evidence surfacing (verdict prompt + response).

Mirrors the S2 I2.5 review_source_quotes surfacing exactly:
  - _extract_youtube_signal(product) pulls the signal off
    product["reviews"]["youtube_review_signal"].
  - _build_youtube_signal_block(p1, p2) renders it as a LABELED, CITED verdict
    input ("N YouTube reviews — Channel"), "" when neither product carries it.
  - _scrub_youtube_signal_if_off(product) strips a cache-carried signal from
    the verdict payload when ENABLE_YOUTUBE_SOURCE is OFF (rollback-safe).
  - response_builder surfaces youtube_review_signal per product in the reviews
    section so the frontend can render the cited line.

Copy rules (CLAUDE.md / memory): NO scary copy (couldn't/try again/failed),
NEVER the word "estimated", ALWAYS cite the source (channel).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")

import pytest

from app.services.extraction_service import (
    _extract_youtube_signal,
    _build_youtube_signal_block,
    _scrub_youtube_signal_if_off,
)


_SIGNAL_1 = {
    "review_count_signal": 5300,
    "top_video_title": "iPhone 16 Review — Worth It?",
    "top_channel": "MKBHD",
    "video_url": "https://www.youtube.com/watch?v=abc",
    "total_views": 1_200_000,
    "video_count": 5,
}
_SIGNAL_2 = {
    "review_count_signal": 800,
    "top_video_title": "Galaxy S24 Long-Term Review",
    "top_channel": "MrwhosetheBoss",
    "video_url": "https://www.youtube.com/watch?v=def",
    "total_views": 640_000,
    "video_count": 4,
}


def _product_with_signal(signal):
    return {"brand": "Apple", "name": "iPhone 16",
            "reviews": {"review_summary": {}, "youtube_review_signal": signal}}


# ---------------------------------------------------------------------------
# _extract_youtube_signal
# ---------------------------------------------------------------------------

def test_extract_returns_signal_when_present():
    assert _extract_youtube_signal(_product_with_signal(_SIGNAL_1)) == _SIGNAL_1


def test_extract_returns_none_when_absent():
    assert _extract_youtube_signal({"reviews": {"review_summary": {}}}) is None
    assert _extract_youtube_signal({"reviews": None}) is None
    assert _extract_youtube_signal({}) is None
    assert _extract_youtube_signal(None) is None


def test_extract_ignores_malformed_signal():
    # non-dict signal → None (defensive)
    assert _extract_youtube_signal({"reviews": {"youtube_review_signal": "garbage"}}) is None


# ---------------------------------------------------------------------------
# _build_youtube_signal_block — labeled, cited, no scary copy, no "estimated"
# ---------------------------------------------------------------------------

def test_block_empty_when_neither_product_has_signal():
    """Byte-identical to the no-YouTube path when neither carries a signal."""
    assert _build_youtube_signal_block({"reviews": {}}, {"reviews": {}}) == ""
    assert _build_youtube_signal_block(None, None) == ""


def test_block_renders_both_products_cited():
    block = _build_youtube_signal_block(
        _product_with_signal(_SIGNAL_1), _product_with_signal(_SIGNAL_2),
    )
    assert block  # non-empty
    # Cites the channel (the source attribution requirement).
    assert "MKBHD" in block
    assert "MrwhosetheBoss" in block
    # Surfaces a human view count + the video title.
    assert "iPhone 16 Review" in block
    # Labeled as supporting signal, not the verdict.
    assert "YouTube" in block


def test_block_only_product1():
    block = _build_youtube_signal_block(
        _product_with_signal(_SIGNAL_1), {"reviews": {}},
    )
    assert "MKBHD" in block
    assert "Product 1" in block
    assert "Product 2" not in block


def test_block_has_no_scary_copy():
    """Copy contract: forbidden EN vocab must never appear."""
    block = _build_youtube_signal_block(
        _product_with_signal(_SIGNAL_1), _product_with_signal(_SIGNAL_2),
    ).lower()
    for forbidden in ("couldn't", "try again", "failed to", "error"):
        assert forbidden not in block, f"scary copy leaked: {forbidden!r}"


def test_block_never_uses_estimated_word():
    """The word 'estimated' is banned from user/verdict-facing text."""
    block = _build_youtube_signal_block(
        _product_with_signal(_SIGNAL_1), _product_with_signal(_SIGNAL_2),
    ).lower()
    assert "estimated" not in block
    assert "estimate" not in block


def test_block_view_count_humanized():
    """1.2M views renders as a compact human figure, not a raw 1200000."""
    block = _build_youtube_signal_block(
        _product_with_signal(_SIGNAL_1), {"reviews": {}},
    )
    # Either "1.2M" or "1,200,000" acceptable — but a bare unformatted
    # "1200000" is not how we cite. Accept the humanized forms.
    assert ("1.2M" in block) or ("1,200,000" in block)


# ---------------------------------------------------------------------------
# _scrub_youtube_signal_if_off — rollback safety
# ---------------------------------------------------------------------------

def test_scrub_removes_signal_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    product = _product_with_signal(_SIGNAL_1)
    scrubbed = _scrub_youtube_signal_if_off(product)
    assert "youtube_review_signal" not in scrubbed["reviews"]
    # original object not mutated (copy semantics).
    assert "youtube_review_signal" in product["reviews"]


def test_scrub_keeps_signal_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    product = _product_with_signal(_SIGNAL_1)
    assert _scrub_youtube_signal_if_off(product) is product  # untouched passthrough


def test_scrub_noop_on_product_without_signal(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    product = {"reviews": {"review_summary": {}}}
    assert _scrub_youtube_signal_if_off(product) == product
    assert _scrub_youtube_signal_if_off(None) is None


def test_block_empty_when_flag_off_via_scrub(monkeypatch):
    """End-to-end rollback: with the flag OFF, scrubbing first then building
    yields an empty block even though the cache carried a signal."""
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    p1 = _scrub_youtube_signal_if_off(_product_with_signal(_SIGNAL_1))
    p2 = _scrub_youtube_signal_if_off(_product_with_signal(_SIGNAL_2))
    assert _build_youtube_signal_block(p1, p2) == ""


# ---------------------------------------------------------------------------
# response_builder surfaces the signal in the reviews section
# (helper _youtube_signal_for_response: flag-gated + scrubbed)
# ---------------------------------------------------------------------------

def test_response_helper_surfaces_signal_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    from app.services import response_builder as rb
    pd = _product_with_signal(_SIGNAL_1)
    assert rb._youtube_signal_for_response(pd) == _SIGNAL_1


def test_response_helper_suppresses_signal_when_flag_off(monkeypatch):
    """Rollback safety at the response surface: flag OFF → None even if the
    cache carried a signal on the product."""
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    from app.services import response_builder as rb
    pd = _product_with_signal(_SIGNAL_1)
    assert rb._youtube_signal_for_response(pd) is None


def test_response_helper_none_when_absent(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    from app.services import response_builder as rb
    assert rb._youtube_signal_for_response({"reviews": {"review_summary": {}}}) is None
    assert rb._youtube_signal_for_response({"reviews": None}) is None

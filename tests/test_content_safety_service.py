"""
Unit tests for `app.services.content_safety_service`.

Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 5.2.
Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.1.

Coverage target: 90% on `app.services.content_safety_service`.

Mock strategy
- Patch `app.services.openai_service.get_client` at SOURCE (the css module
  imports `get_client` lazily inside `moderate_output`, so patching the
  source module is what gets seen at call time).
- Singleton reset between tests via `monkeypatch.setattr(_service, None)`.
- Blocklist error-path tests redirect `_BLOCKLIST_PATH` via monkeypatch.

ZERO live OpenAI calls — every L3/L4 test patches the client.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import is_dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

# Ensure the OpenAI client can instantiate at import time even when the test
# environment is missing the real API key — the L3/L4 tests patch the client
# accessor at the call site so no live request fires.
os.environ.setdefault("OPENAI_API_KEY", "test-key-noop-content-safety")

import pytest

import app.services.content_safety_service as css


# ============================================
# Helpers — FakeOpenAI for L3 / L4
# ============================================


class _FakeModerationResult:
    def __init__(self, flagged: bool, scores: Optional[dict] = None):
        self.flagged = flagged

        class _Cats:
            def model_dump(_self):
                return scores or {}

        self.category_scores = _Cats()


class _FakeModerationResponse:
    def __init__(self, flagged: bool, scores: Optional[dict] = None):
        self.results = [_FakeModerationResult(flagged, scores)]


def _make_fake_client(*, flagged: bool = False, scores: Optional[dict] = None, raises: Optional[Exception] = None):
    """Build a fake OpenAI client whose moderations.create is an AsyncMock."""
    client = MagicMock()
    if raises is not None:
        client.moderations.create = AsyncMock(side_effect=raises)
    else:
        client.moderations.create = AsyncMock(
            return_value=_FakeModerationResponse(flagged=flagged, scores=scores)
        )
    return client


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    """Force a fresh ContentSafetyService instance per test."""
    monkeypatch.setattr(css, "_service", None)
    yield


@pytest.fixture
def service():
    """Construct a real ContentSafetyService against the committed blocklist."""
    return css.get_content_safety_service()


# ============================================
# § 1.1 — L1 query pre-filter
# ============================================


class TestL1QueryPrefilter:
    def test_clean_iphone_query_passes(self, service):
        result = service.check_query_intent("iPhone 15 vs Galaxy S24")
        assert result.allowed is True
        assert result.reason is None

    def test_clean_grocery_query_passes(self, service):
        result = service.check_query_intent("Almarai milk 1L vs Saudia milk 1L")
        assert result.allowed is True

    def test_clean_supplement_query_passes(self, service):
        result = service.check_query_intent("Centrum Silver vs One A Day")
        assert result.allowed is True

    def test_clean_cosmetic_query_passes(self, service):
        result = service.check_query_intent(
            "MAC Ruby Woo vs Charlotte Tilbury Pillow Talk"
        )
        assert result.allowed is True

    def test_empty_query_allowed(self, service):
        assert service.check_query_intent("").allowed is True

    def test_whitespace_only_allowed(self, service):
        assert service.check_query_intent("   ").allowed is True

    def test_weapons_en_glock_blocked(self, service):
        result = service.check_query_intent("buy a glock 19 today")
        assert result.allowed is False
        assert result.reason == "weapons"
        assert result.blocklist_match is not None
        assert "glock" in result.blocklist_match.lower()

    def test_weapons_en_ammunition_blocked(self, service):
        result = service.check_query_intent("ammunition box price")
        assert result.allowed is False
        assert result.reason == "weapons"

    def test_weapons_en_case_insensitive_glock(self, service):
        for variant in ("GLOCK 19", "Glock 19", "glock 19"):
            assert service.check_query_intent(variant).allowed is False, variant

    def test_weapons_ar_blocked(self, service):
        # "مسدس" — handgun (Arabic). Seeded in app/data/content_blocklist.json.
        result = service.check_query_intent("شراء مسدس جديد")
        assert result.allowed is False
        assert result.reason == "weapons"

    def test_illegal_drugs_en_cocaine_blocked(self, service):
        result = service.check_query_intent("buy cocaine online")
        assert result.allowed is False
        assert result.reason == "illegal_drugs"

    def test_illegal_drugs_ar_blocked(self, service):
        # "كوكايين" — cocaine (Arabic).
        result = service.check_query_intent("سعر كوكايين")
        assert result.allowed is False
        assert result.reason == "illegal_drugs"

    def test_adult_products_en_blocked(self, service):
        result = service.check_query_intent("fleshlight vs penis pump")
        assert result.allowed is False
        assert result.reason == "adult_products"

    def test_adult_products_ar_blocked(self, service):
        # "هزاز جنسي" — adult product (Arabic).
        result = service.check_query_intent("شراء هزاز جنسي")
        assert result.allowed is False
        assert result.reason == "adult_products"

    def test_gore_en_blocked(self, service):
        result = service.check_query_intent("dismembered body video")
        assert result.allowed is False
        assert result.reason == "gore"

    def test_gore_ar_blocked(self, service):
        result = service.check_query_intent("فيديو إعدام مباشر")
        assert result.allowed is False
        assert result.reason == "gore"

    def test_self_harm_en_blocked(self, service):
        result = service.check_query_intent("suicide method guide")
        assert result.allowed is False
        assert result.reason == "self_harm"

    def test_self_harm_ar_blocked(self, service):
        result = service.check_query_intent("طريقة انتحار سريعة")
        assert result.allowed is False
        assert result.reason == "self_harm"

    def test_word_boundary_no_false_positive_substring(self, service):
        # "ar-15" is seeded; "Bahraini market" contains "ar" substring but
        # NOT as a word — must not match. Pins the lookaround pattern.
        assert service.check_query_intent("Bahraini market overview").allowed is True

    def test_word_boundary_no_false_positive_inside_brand(self, service):
        # "lsd tabs" is seeded; "lsdr" inside "lsdream" must not match.
        assert service.check_query_intent("lsdream concert tickets").allowed is True

    def test_unicode_word_boundary_ar_inside_longer_phrase(self, service):
        # "مسدس" inside a longer Arabic phrase still matches via Unicode
        # lookaround.
        result = service.check_query_intent("أبحث عن مسدس قانوني")
        assert result.allowed is False
        assert result.reason == "weapons"


# ============================================
# § 1.5 — L2 shopping-result filter
# ============================================


class TestL2ShoppingFilter:
    def test_clean_items_pass_unchanged(self, service):
        items = [
            {"title": "iPhone 15", "snippet": "Apple flagship 2024"},
            {"title": "Galaxy S24", "snippet": "Samsung flagship 2024"},
            {"title": "Pixel 8", "snippet": "Google flagship 2024"},
        ]
        result = service.filter_shopping_items(items)
        assert len(result) == 3
        assert result == items

    def test_drops_unsafe_title(self, service):
        items = [
            {"title": "glock 19 holster premium", "snippet": "leather"},
            {"title": "iPhone 15", "snippet": "Apple flagship"},
        ]
        result = service.filter_shopping_items(items)
        assert len(result) == 1
        assert result[0]["title"] == "iPhone 15"

    def test_drops_unsafe_snippet(self, service):
        items = [
            {"title": "Combat Gear", "snippet": "includes ammunition for tactical use"},
            {"title": "iPhone 15", "snippet": "Apple flagship"},
        ]
        result = service.filter_shopping_items(items)
        assert len(result) == 1
        assert result[0]["title"] == "iPhone 15"

    def test_empty_list_returns_empty(self, service):
        assert service.filter_shopping_items([]) == []

    def test_missing_title_field_handled(self, service):
        # Item with no title but with safe snippet stays.
        items = [{"snippet": "safe iPhone snippet"}]
        result = service.filter_shopping_items(items)
        assert len(result) == 1

    def test_missing_snippet_field_handled(self, service):
        items = [{"title": "iPhone 15"}]
        result = service.filter_shopping_items(items)
        assert len(result) == 1

    def test_no_audit_log_emitted(self, service, monkeypatch):
        """Pins Backend § 1.5: L2 is item-level, NOT audit-logged."""
        from app.services import audit_service

        log_spy = AsyncMock()
        monkeypatch.setattr(audit_service, "log_content_blocked", log_spy)

        items = [
            {"title": "glock 19 case", "snippet": ""},
            {"title": "iPhone 15", "snippet": ""},
        ]
        service.filter_shopping_items(items)
        assert log_spy.await_count == 0

    def test_aggregate_logging_format(self, service, caplog):
        """Pins Backend § 1.5 log format exactly."""
        caplog.set_level(logging.INFO, logger="app.services.content_safety_service")
        items = [
            {"title": "glock 19 grip", "snippet": ""},
            {"title": "cocaine packet", "snippet": ""},
            {"title": "iPhone 15", "snippet": ""},
            {"title": "Galaxy S24", "snippet": ""},
            {"title": "Pixel 8", "snippet": ""},
        ]
        service.filter_shopping_items(items)
        messages = [r.getMessage() for r in caplog.records]
        assert any(
            "[content_safety] L2 dropped 2/5 shopping items" in m for m in messages
        ), messages

    def test_ar_keyword_in_snippet_dropped(self, service):
        items = [
            {"title": "Combat Gear", "snippet": "مسدس holster"},
            {"title": "iPhone 15", "snippet": "Apple"},
        ]
        result = service.filter_shopping_items(items)
        assert len(result) == 1
        assert result[0]["title"] == "iPhone 15"


# ============================================
# § 1.1 — L3 output moderation (omni-moderation-latest)
# ============================================


class TestL3OutputModeration:
    @pytest.mark.asyncio
    async def test_unflagged_response_allows(self, service, monkeypatch):
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: _make_fake_client(flagged=False))
        result = await service.moderate_output("Comparison of iPhone 15 vs Galaxy S24")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_flagged_violence_blocks(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"violence": 0.95}),
        )
        result = await service.moderate_output("violent product description")
        assert result.allowed is False
        assert result.reason == "violence"

    @pytest.mark.asyncio
    async def test_flagged_sexual_category(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"sexual": 0.92}),
        )
        result = await service.moderate_output("text")
        assert result.allowed is False
        assert result.reason == "sexual"

    @pytest.mark.asyncio
    async def test_flagged_hate_category(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"hate": 0.88}),
        )
        result = await service.moderate_output("text")
        assert result.allowed is False
        assert result.reason == "hate"

    @pytest.mark.asyncio
    async def test_flagged_self_harm_category(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"self_harm": 0.7}),
        )
        result = await service.moderate_output("text")
        assert result.allowed is False
        assert result.reason == "self_harm"

    @pytest.mark.asyncio
    async def test_flagged_illicit_category(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"illicit": 0.6}),
        )
        result = await service.moderate_output("text")
        assert result.allowed is False
        assert result.reason == "illicit"

    @pytest.mark.asyncio
    async def test_flagged_unspecified_when_no_scores_above_threshold(
        self, service, monkeypatch
    ):
        # flagged=True but all scores at/below 0.5 → reason="unspecified".
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(
                flagged=True, scores={"violence": 0.4, "sexual": 0.3}
            ),
        )
        result = await service.moderate_output("text")
        assert result.allowed is False
        assert result.reason == "unspecified"

    @pytest.mark.asyncio
    async def test_empty_text_skips_api_call(self, service, monkeypatch):
        fake = _make_fake_client(flagged=False)
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: fake)
        result = await service.moderate_output("")
        assert result.allowed is True
        assert fake.moderations.create.await_count == 0

    @pytest.mark.asyncio
    async def test_whitespace_only_text_skips_api_call(self, service, monkeypatch):
        fake = _make_fake_client(flagged=False)
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: fake)
        result = await service.moderate_output("   \n\t  ")
        assert result.allowed is True
        assert fake.moderations.create.await_count == 0

    @pytest.mark.asyncio
    async def test_api_timeout_fails_open(self, service, monkeypatch, caplog):
        import asyncio

        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(raises=asyncio.TimeoutError()),
        )
        caplog.set_level(logging.WARNING, logger="app.services.content_safety_service")
        result = await service.moderate_output("any non-empty text")
        assert result.allowed is True  # fail-open
        messages = [r.getMessage() for r in caplog.records]
        assert any("fail-open" in m.lower() for m in messages), messages

    @pytest.mark.asyncio
    async def test_api_generic_exception_fails_open(self, service, monkeypatch, caplog):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(raises=RuntimeError("boom")),
        )
        caplog.set_level(logging.WARNING, logger="app.services.content_safety_service")
        result = await service.moderate_output("any non-empty text")
        assert result.allowed is True
        messages = [r.getMessage() for r in caplog.records]
        assert any("fail-open" in m.lower() for m in messages)


# ============================================
# § 1.1 — L4 vision moderation
# ============================================


class TestL4VisionModeration:
    @pytest.mark.asyncio
    async def test_unflagged_vision_payload_allows(self, service, monkeypatch):
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: _make_fake_client(flagged=False))
        vision_result = {
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "size_or_count": ""},
                {"brand": "Samsung", "name": "Galaxy S24", "size_or_count": ""},
            ]
        }
        result = await service.moderate_vision_output(vision_result)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_flagged_vision_payload_blocks(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(flagged=True, scores={"violence": 0.95}),
        )
        vision_result = {
            "products": [
                {"brand": "Brand", "name": "weapon name", "size_or_count": ""},
            ]
        }
        result = await service.moderate_vision_output(vision_result)
        assert result.allowed is False
        assert result.reason == "violence"

    @pytest.mark.asyncio
    async def test_empty_products_list_short_circuits(self, service, monkeypatch):
        fake = _make_fake_client(flagged=False)
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: fake)
        result = await service.moderate_vision_output({"products": []})
        assert result.allowed is True
        # No API call burned for empty input — short-circuited by L3's empty
        # guard.
        assert fake.moderations.create.await_count == 0

    @pytest.mark.asyncio
    async def test_missing_products_key_treated_as_empty(self, service, monkeypatch):
        fake = _make_fake_client(flagged=False)
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: fake)
        result = await service.moderate_vision_output({})
        assert result.allowed is True
        assert fake.moderations.create.await_count == 0

    @pytest.mark.asyncio
    async def test_assembles_brand_name_size_in_text(self, service, monkeypatch):
        fake = _make_fake_client(flagged=False)
        monkeypatch.setattr("app.services.openai_service.get_client", lambda: fake)
        vision_result = {
            "products": [
                {"brand": "Apple", "name": "iPhone", "size_or_count": "128GB"},
                {"brand": "Samsung", "name": "Galaxy", "size_or_count": "256GB"},
            ]
        }
        await service.moderate_vision_output(vision_result)
        assert fake.moderations.create.await_count == 1
        call_kwargs = fake.moderations.create.await_args.kwargs
        assembled = call_kwargs["input"]
        assert "Apple iPhone 128GB" in assembled
        assert "Samsung Galaxy 256GB" in assembled

    @pytest.mark.asyncio
    async def test_api_timeout_fails_open(self, service, monkeypatch):
        import asyncio

        monkeypatch.setattr(
            "app.services.openai_service.get_client",
            lambda: _make_fake_client(raises=asyncio.TimeoutError()),
        )
        vision_result = {
            "products": [{"brand": "Test", "name": "Product", "size_or_count": ""}]
        }
        result = await service.moderate_vision_output(vision_result)
        assert result.allowed is True


# ============================================
# § 1.1 / § 1.2 — blocklist loading + singleton
# ============================================


class TestBlocklistLoading:
    def test_blocklist_file_missing_raises_filenotfound(self, tmp_path, monkeypatch):
        # Point _BLOCKLIST_PATH at a non-existent file, then instantiate.
        bogus = tmp_path / "missing.json"
        monkeypatch.setattr(css, "_BLOCKLIST_PATH", bogus)
        monkeypatch.setattr(css, "_service", None)
        with pytest.raises(FileNotFoundError):
            css.ContentSafetyService()

    def test_blocklist_malformed_json_raises_json_decode_error(
        self, tmp_path, monkeypatch
    ):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(css, "_BLOCKLIST_PATH", bad)
        monkeypatch.setattr(css, "_service", None)
        with pytest.raises(json.JSONDecodeError):
            css.ContentSafetyService()

    def test_blocklist_empty_categories_is_legal(self, tmp_path, monkeypatch):
        empty = tmp_path / "empty.json"
        empty.write_text(json.dumps({"categories": {}}), encoding="utf-8")
        monkeypatch.setattr(css, "_BLOCKLIST_PATH", empty)
        monkeypatch.setattr(css, "_service", None)
        svc = css.ContentSafetyService()
        # No categories → L1 always allows.
        assert svc.check_query_intent("glock 19").allowed is True

    def test_blocklist_required_categories_present_in_committed_file(self):
        blocklist = json.loads(css._BLOCKLIST_PATH.read_text(encoding="utf-8"))
        categories = blocklist.get("categories", {})
        for required in ("weapons", "illegal_drugs", "adult_products", "gore", "self_harm"):
            assert required in categories, f"Missing required category: {required}"

    def test_blocklist_each_category_has_en_and_ar_entries(self):
        blocklist = json.loads(css._BLOCKLIST_PATH.read_text(encoding="utf-8"))
        for cat, lists in blocklist["categories"].items():
            assert "en" in lists and "ar" in lists, cat
            assert len(lists["en"]) >= 5, f"{cat} EN list too small"
            assert len(lists["ar"]) >= 5, f"{cat} AR list too small"

    def test_blocklist_no_term_shorter_than_3_chars(self):
        blocklist = json.loads(css._BLOCKLIST_PATH.read_text(encoding="utf-8"))
        for cat, lists in blocklist["categories"].items():
            for term in lists.get("en", []) + lists.get("ar", []):
                assert len(term) >= 3, f"Term too short in {cat}: {term!r}"


class TestSingleton:
    def test_get_content_safety_service_returns_singleton(self, monkeypatch):
        monkeypatch.setattr(css, "_service", None)
        a = css.get_content_safety_service()
        b = css.get_content_safety_service()
        assert a is b


# ============================================
# Symbol contract — pin Backend § 1.1 surface
# ============================================


class TestSymbolContract:
    def test_safety_result_is_a_dataclass(self):
        assert is_dataclass(css.SafetyResult)

    def test_safety_result_fields(self):
        r = css.SafetyResult(allowed=False, reason="weapons", blocklist_match="glock")
        assert r.allowed is False
        assert r.reason == "weapons"
        assert r.blocklist_match == "glock"

    def test_content_safety_service_has_required_methods(self, service):
        for name in (
            "check_query_intent",
            "filter_shopping_items",
            "moderate_output",
            "moderate_vision_output",
        ):
            assert hasattr(service, name), f"Missing required method: {name}"

    def test_log_content_blocked_helper_exists(self):
        from app.services import audit_service

        assert hasattr(audit_service, "log_content_blocked")

    def test_log_content_blocked_signature(self):
        import inspect

        from app.services.audit_service import log_content_blocked

        sig = inspect.signature(log_content_blocked)
        assert list(sig.parameters.keys()) == ["layer", "query_hash"]

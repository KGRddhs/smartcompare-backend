"""Codex HIGH-3 — a transient sitemap-discovery MISS must NOT be 30d-negcached.

With the sitemap-index cron OFF (or the index cold / TTL-expired), the bolo /
boutiqaat sitemap adapters return None (no genuine PDP yet), the price cascade
falls to a Tier-3 GPT estimate, and `_record_negative_price_cache` previously
30d-froze that estimate at the Tier-3 terminal. So a product queried BEFORE the
cron warms the index would keep serving the stale estimate for 30 DAYS even after
the index became available.

The fix reuses the existing `guard_rejected` TTL-cap mechanism:
  - `sitemap_discovery_service.sitemap_discovery_is_cold(category)` is True iff at
    least one `mechanism="sitemap"` source applies to the category AND its index is
    not built;
  - `_record_negative_price_cache(..., transient_discovery=True)` caps the TTL to
    24h (PRICE_CACHE_TTL) instead of 30d (NEGATIVE_PRICE_CACHE_TTL), so the estimate
    re-resolves to a genuine price once the cron warms the index.

These tests use NO live network — the index-build state is monkeypatched, and the
negative-cache write is captured via a monkeypatched `set_negative_cache`.
"""

from unittest.mock import patch

import pytest

from app.services import sitemap_discovery_service as sds
from app.services.price_service import (
    NEGATIVE_PRICE_CACHE_TTL,
    PRICE_CACHE_TTL,
)
from app.services import structured_comparison_service as scs


# --------------------------------------------------- sitemap_discovery_is_cold ---


class TestSitemapDiscoveryIsCold:
    """A category with a `mechanism="sitemap"` source (fragrances → boutiqaat.com)
    is COLD iff that source's index is not built; a category with no sitemap source
    (electronics) is never cold by this signal. NOTE (gate-fix): cold-detection is
    GATED on the cron being enabled — a cold index is only "transient" if the cron
    will build it, so these tests force `_sitemap_index_cron_enabled` True except the
    dedicated cron-off test below."""

    def test_cold_when_index_not_built(self):
        # fragrances has exactly one sitemap source (boutiqaat.com); force its
        # index to "not built" + the cron enabled → cold.
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=True), \
                patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_discovery_is_cold("fragrances") is True

    def test_not_cold_when_cron_disabled(self):
        # GATE-FIX regression: with ENABLE_SITEMAP_INDEX OFF (the ship state) the
        # index is NEVER built, so a cold index is a REAL structural dead-end (30d),
        # NOT a transient miss — avoids re-running the scrape cascade every 24h for
        # the whole structural-gap tail on the finite Serper budget.
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=False), \
                patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_discovery_is_cold("fragrances") is False

    def test_not_cold_when_index_built(self):
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=True), \
                patch.object(sds, "_index_is_built", return_value=True):
            assert sds.sitemap_discovery_is_cold("fragrances") is False

    def test_not_cold_when_no_sitemap_source_for_category(self):
        # electronics has NO mechanism="sitemap" source → never cold by this signal
        # regardless of any index state.
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=True), \
                patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_discovery_is_cold("electronics") is False

    def test_never_raises_on_internal_error(self):
        # _index_is_built blowing up must be swallowed → conservative False (the
        # 30d structural path), never a hot-path exception.
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=True), \
                patch.object(sds, "_index_is_built", side_effect=RuntimeError("boom")):
            assert sds.sitemap_discovery_is_cold("fragrances") is False

    def test_only_sitemap_mechanism_counts_not_curl(self):
        # get_sitemap_sources_for_category also returns mechanism="curl" rows; the
        # cold signal must be scoped to mechanism="sitemap" only. We assert the
        # function asks _index_is_built ONLY about a sitemap domain (boutiqaat.com
        # for fragrances), never about a curl-only domain.
        seen = []

        def _spy(domain):
            seen.append(domain)
            return True  # all built → not cold

        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=True), \
                patch.object(sds, "_index_is_built", side_effect=_spy):
            sds.sitemap_discovery_is_cold("fragrances")
        assert "boutiqaat.com" in seen
        # every domain probed must be a real sitemap-mechanism domain
        assert set(seen) <= {"bolo.bh", "boutiqaat.com"}


# ----------------------------------- _record_negative_price_cache TTL cap ---


class TestRecordNegativeCacheTransientCap:
    """`transient_discovery=True` caps the negative-cache TTL to PRICE_CACHE_TTL
    (24h), exactly like `guard_rejected`; the default path stays at
    NEGATIVE_PRICE_CACHE_TTL (30d)."""

    def _service(self):
        from app.services.structured_comparison_service import (
            StructuredComparisonService,
        )
        return StructuredComparisonService()

    def _capture_ttl(self, *, transient_discovery=False, guard_rejected=False):
        service = self._service()
        # An estimated price DOES pass should_negative_cache (real predicate), so
        # the write fires and we capture the ttl it was called with.
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        captured = {}

        def _fake_set_negative_cache(key, value, ttl):
            captured["key"] = key
            captured["ttl"] = ttl

        with patch(
            "app.services.structured_comparison_service.set_negative_cache",
            side_effect=_fake_set_negative_cache,
        ):
            service._record_negative_price_cache(
                "price:abc123", price,
                guard_rejected=guard_rejected,
                transient_discovery=transient_discovery,
            )
        return captured

    def test_transient_discovery_caps_to_24h(self):
        captured = self._capture_ttl(transient_discovery=True)
        assert captured.get("ttl") == PRICE_CACHE_TTL
        assert captured["ttl"] != NEGATIVE_PRICE_CACHE_TTL

    def test_default_path_is_30d(self):
        captured = self._capture_ttl()  # neither flag
        assert captured.get("ttl") == NEGATIVE_PRICE_CACHE_TTL

    def test_guard_rejected_still_caps_to_24h(self):
        # Regression guard: the pre-existing guard_rejected cap is unchanged.
        captured = self._capture_ttl(guard_rejected=True)
        assert captured.get("ttl") == PRICE_CACHE_TTL

    def test_both_flags_cap_to_24h(self):
        captured = self._capture_ttl(transient_discovery=True, guard_rejected=True)
        assert captured.get("ttl") == PRICE_CACHE_TTL

    def test_genuine_price_never_negcached_regardless_of_flag(self):
        # Defense-in-depth: should_negative_cache False (a genuine local_bhd price)
        # → no write happens even with transient_discovery=True.
        service = self._service()
        price = {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache",
        ) as m_set:
            service._record_negative_price_cache(
                "price:xyz", price, transient_discovery=True,
            )
        m_set.assert_not_called()


# ============================================================================
# Codex RE-REVIEW HIGH-3 — read-side cache invalidation (still unresolved):
# activating the sitemap cron does NOT invalidate the 30d estimates negcached
# while the index was cold. The fix: STAMP the raw cold sitemap domains at WRITE,
# INVALIDATE at READ the moment any stamped domain's index becomes built.
# ============================================================================


# ----------------------------------------------- sitemap_unbuilt_domains (raw) ---


class TestSitemapUnbuiltDomains:
    """RAW (NOT cron-gated) — the mechanism="sitemap" source DOMAINS for a category
    whose index is not built. This is "which genuine sitemap sources were
    unavailable", independent of whether the cron is on; the cron-gating lives in
    sitemap_discovery_is_cold, not here."""

    def test_returns_domain_when_index_not_built(self):
        # fragrances has exactly one sitemap source (boutiqaat.com). NOT cron-gated:
        # the cron-enabled state must NOT change the answer (the gating is elsewhere).
        with patch.object(sds, "_sitemap_index_cron_enabled", return_value=False), \
                patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_unbuilt_domains("fragrances") == ["boutiqaat.com"]

    def test_returns_empty_when_index_built(self):
        with patch.object(sds, "_index_is_built", return_value=True):
            assert sds.sitemap_unbuilt_domains("fragrances") == []

    def test_empty_when_no_sitemap_source_for_category(self):
        # electronics has no mechanism="sitemap" source → never stamps anything.
        with patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_unbuilt_domains("electronics") == []

    def test_only_sitemap_mechanism_not_curl(self):
        seen = []

        def _spy(domain):
            seen.append(domain)
            return False  # nothing built → every sitemap domain returned

        with patch.object(sds, "_index_is_built", side_effect=_spy):
            sds.sitemap_unbuilt_domains("fragrances")
        # only the sitemap-mechanism domain(s) are probed, never a curl-only domain
        assert set(seen) <= {"bolo.bh", "boutiqaat.com"}

    def test_never_raises_returns_empty_on_error(self):
        with patch.object(sds, "_index_is_built", side_effect=RuntimeError("boom")):
            assert sds.sitemap_unbuilt_domains("fragrances") == []


# ------------------------------------------------- sitemap_domains_now_built ---


class TestSitemapDomainsNowBuilt:
    """The READ-side invalidation predicate: True iff ANY stamped domain now has a
    built index → the stale negcache estimate must be ignored + re-resolved."""

    def test_true_when_any_domain_built(self):
        with patch.object(sds, "_index_is_built",
                          side_effect=lambda d: d == "boutiqaat.com"):
            assert sds.sitemap_domains_now_built(["bolo.bh", "boutiqaat.com"]) is True

    def test_false_when_none_built(self):
        with patch.object(sds, "_index_is_built", return_value=False):
            assert sds.sitemap_domains_now_built(["boutiqaat.com"]) is False

    def test_false_on_empty_or_none(self):
        assert sds.sitemap_domains_now_built([]) is False
        assert sds.sitemap_domains_now_built(None) is False

    def test_never_raises_returns_false_on_error(self):
        with patch.object(sds, "_index_is_built", side_effect=RuntimeError("boom")):
            assert sds.sitemap_domains_now_built(["boutiqaat.com"]) is False


# ------------------------------- WRITE-side stamp in _record_negative_price_cache ---


class TestNegativeCacheStampsColdDomains:
    """The WRITE stamps the RAW cold sitemap domains onto a COPY of the cached
    value when `category` has a cold sitemap source — so the read-side can later
    invalidate even when the 30d TTL was used (cron OFF at write)."""

    def _service(self):
        return scs.StructuredComparisonService()

    def _capture_value(self, *, category, cold_domains):
        service = self._service()
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        captured = {}

        def _fake_set_negative_cache(key, value, ttl):
            captured["value"] = value

        with patch(
            "app.services.structured_comparison_service.set_negative_cache",
            side_effect=_fake_set_negative_cache,
        ), patch(
            "app.services.structured_comparison_service.sitemap_unbuilt_domains",
            return_value=cold_domains,
        ):
            service._record_negative_price_cache(
                "price:abc123", price, category=category,
            )
        return price, captured

    def test_stamps_cold_domains_onto_cached_value(self):
        price, captured = self._capture_value(
            category="fragrances", cold_domains=["boutiqaat.com"],
        )
        assert captured["value"].get("_sitemap_cold_domains") == ["boutiqaat.com"]

    def test_does_not_mutate_the_returned_price_dict(self):
        # The stamp goes on a COPY — the price dict the caller keeps using is clean.
        price, captured = self._capture_value(
            category="fragrances", cold_domains=["boutiqaat.com"],
        )
        assert "_sitemap_cold_domains" not in price
        assert captured["value"] is not price

    def test_no_stamp_when_no_cold_domains(self):
        price, captured = self._capture_value(
            category="electronics", cold_domains=[],
        )
        assert "_sitemap_cold_domains" not in captured["value"]
        # no cold domains → the original price object is cached as-is (no copy)
        assert captured["value"] is price

    def test_no_stamp_when_category_none(self):
        # category=None → sitemap_unbuilt_domains is never consulted; no stamp.
        service = self._service()
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        captured = {}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache",
            side_effect=lambda k, v, t: captured.update(value=v),
        ), patch(
            "app.services.structured_comparison_service.sitemap_unbuilt_domains",
        ) as m_unbuilt:
            service._record_negative_price_cache("price:abc", price, category=None)
        m_unbuilt.assert_not_called()
        assert "_sitemap_cold_domains" not in captured["value"]


# --------------------------- READ-side invalidation inside _get_price ---


class _ReachedLiveCascade(Exception):
    """Raised by a patched downstream call to prove _get_price fell THROUGH the
    negcache branch into the live cascade (i.e. it did NOT serve the stale
    sentinel)."""


@pytest.mark.asyncio
class TestGetPriceReadSideInvalidation:
    """The negcache READ: a sentinel stamped with `_sitemap_cold_domains` whose
    index is now BUILT must be IGNORED (fall through to the live cascade,
    re-resolving the genuine price); whose index is still NOT built must be SERVED
    (the 30d structural sentinel, no scrape burn). Drives _get_price directly with
    L1/L2 mocked to miss and the negcache pre-seeded — NO live network."""

    def _service(self):
        return scs.StructuredComparisonService()

    def _seed_sentinel(self):
        return {
            "amount": 70.0,
            "currency": "BHD",
            "source_method": "estimated",
            "estimated": True,
            "_sitemap_cold_domains": ["boutiqaat.com"],
        }

    async def _run(self, *, now_built):
        service = self._service()
        sentinel = self._seed_sentinel()

        async def _no_db_price(*a, **k):
            return None

        with patch.object(scs, "get_cached", return_value=None), \
                patch.object(scs, "validate_price_query", return_value=True), \
                patch.object(scs, "get_negative_cache", return_value=sentinel), \
                patch.object(scs, "sitemap_domains_now_built", return_value=now_built), \
                patch("app.services.product_data_service.get_cached_price",
                      side_effect=_no_db_price), \
                patch.object(scs, "get_shopify_sources_for_category",
                             side_effect=_ReachedLiveCascade()):
            return await service._get_price(
                "Boutiqaat", "Oud Wood", None, "bahrain",
                "Oud Wood", nocache=False, category="fragrances",
            )

    async def test_served_when_index_still_not_built(self):
        # Not built → the stale 30d sentinel is SERVED (cascade skipped, no burn).
        result = await self._run(now_built=False)
        assert result.get("_cache_source") == "negative"
        assert result.get("amount") == 70.0
        # Codex re-review #3 MEDIUM (no-leak) — the internal read-side marker must
        # be stripped from the SERVED price object (response_builder exposes it
        # raw). This assertion genuinely fails-without-fix: the seeded sentinel
        # carries `_sitemap_cold_domains`, so it leaks unless _get_price pops it.
        assert "_sitemap_cold_domains" not in result

    async def test_invalidated_when_index_now_built(self):
        # Now built → the sentinel is IGNORED and we fall through to the live
        # cascade (proven by the patched get_shopify_sources_for_category raising).
        with pytest.raises(_ReachedLiveCascade):
            await self._run(now_built=True)

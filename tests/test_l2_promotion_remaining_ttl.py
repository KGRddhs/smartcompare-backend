"""Issue #57 — an L2 (DB) price row is promoted into L1 (Redis) with its
REMAINING freshness, not a full TTL measured from now.

The defect: `_get_price`'s L2->L1 promotion wrote
`price_cache_ttl(db_price)` — a FULL 7d (genuine) / 24h (converted, estimated)
window starting at the moment of the promotion — while
`product_data_service.get_cached_price` had already admitted a row aged up to
that SAME window (`_price_row_fresh`, whose thresholds read the identical env
knobs). A 6.9-day-old genuine row was therefore re-promoted for another 7 days
and served to ~14 days of total age; a converted/estimated row reached ~48h.
Nothing in the promotion path knew the row's age, because `get_cached_price`
never returned one.

The fix ships behind ENABLE_L2_PROMOTION_REMAINING_TTL (default OFF), in two
halves governed by the one flag:
  * `get_cached_price` stamps `_l2_age_seconds` — the age of the row it actually
    SELECTED (which under the #54 clobber guard is NOT necessarily
    `response.data[0]`) — onto the returned dict.
  * `_get_price` pops that key BEFORE the promotion branch and promotes with
    `price_cache_ttl(row) - age`, skipping the promotion entirely when nothing
    is left.

Every test below pins BOTH directions: flag ON does the new thing, flag OFF is
byte-identical to the pre-#57 behaviour. All I/O is monkeypatched; zero live
calls.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from datetime import datetime, timedelta, timezone

import pytest

from app.services import price_service as ps
from app.services import product_data_service as pds
import app.services.structured_comparison_service as scs

FLAG = "ENABLE_L2_PROMOTION_REMAINING_TTL"

_DAY = 24 * 60 * 60


def _ts(age_seconds: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()


def _row(age_seconds: float, source_method: str = "woo_store_api", **over):
    row = {
        "amount": 45.0,
        "currency": "BHD",
        "retailer": "theperfumesclub",
        "url": "https://example.bh/p/dior-sauvage",
        "source_method": source_method,
        "estimated": source_method == "estimated",
        "fetched_at": _ts(age_seconds),
    }
    row.update(over)
    return row


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self.limit_arg = None

    def select(self, cols):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.limit_arg = n
        return self

    def execute(self):
        class _R:
            data = list(self._rows)
        return _R()


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows
        self.query = None

    def table(self, name):
        self.query = _FakeQuery(self._rows)
        return self.query


def _install_rows(monkeypatch, rows):
    client = _FakeClient(rows)
    monkeypatch.setattr(pds, "get_admin_supabase_client", lambda: client)
    return client


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Neutral flag state for every test — each one sets only what it pins."""
    for var in (FLAG, "ENABLE_PRICE_TITLE_PERSIST", "ENABLE_GENUINE_PRICE_CLOBBER_GUARD",
                "ENABLE_EXACT_PRICE_GATE", "PRICE_CACHE_BUST", "ENABLE_ASYNC_REDIS_OFFLOAD"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# 1. The flag helper itself
# ---------------------------------------------------------------------------


class TestFlagHelper:
    def test_default_is_off(self, monkeypatch):
        assert ps.l2_promotion_remaining_ttl_enabled() is False

    @pytest.mark.parametrize("raw", ["true", "TRUE", " 1 ", "yes", "on"])
    def test_truthy_spellings(self, monkeypatch, raw):
        monkeypatch.setenv(FLAG, raw)
        assert ps.l2_promotion_remaining_ttl_enabled() is True

    @pytest.mark.parametrize("raw", ["", "false", "0", "off", "maybe"])
    def test_falsy_spellings(self, monkeypatch, raw):
        monkeypatch.setenv(FLAG, raw)
        assert ps.l2_promotion_remaining_ttl_enabled() is False

    def test_read_per_call_not_cached_at_import(self, monkeypatch):
        """A Railway flip must take effect with no restart."""
        assert ps.l2_promotion_remaining_ttl_enabled() is False
        monkeypatch.setenv(FLAG, "true")
        assert ps.l2_promotion_remaining_ttl_enabled() is True
        monkeypatch.delenv(FLAG)
        assert ps.l2_promotion_remaining_ttl_enabled() is False

    def test_pds_delegates_to_the_one_definition(self, monkeypatch):
        """The L2 half must not re-derive the env read (drift defect #67)."""
        monkeypatch.setenv(FLAG, "true")
        assert pds._l2_promotion_remaining_ttl_enabled() is True
        monkeypatch.setattr(ps, "l2_promotion_remaining_ttl_enabled", lambda: False)
        assert pds._l2_promotion_remaining_ttl_enabled() is False


# ---------------------------------------------------------------------------
# 2. _row_age_seconds, pure
# ---------------------------------------------------------------------------


class TestRowAgeSeconds:
    def test_ages_a_normal_row(self):
        now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
        row = {"fetched_at": "2026-09-02T12:00:00+00:00"}
        assert pds._row_age_seconds(row, now) == 3 * _DAY

    def test_accepts_the_z_suffix(self):
        now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
        assert pds._row_age_seconds({"fetched_at": "2026-09-05T11:00:00Z"}, now) == 3600

    def test_future_row_clamps_to_zero_never_negative(self):
        """A clock-skewed future stamp must not BUY extra L1 lifetime."""
        now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
        assert pds._row_age_seconds({"fetched_at": "2999-01-01T00:00:00+00:00"}, now) == 0

    @pytest.mark.parametrize("row", [None, {}, {"fetched_at": None},
                                     {"fetched_at": "not-a-timestamp"}])
    def test_unparseable_is_none_not_an_exception(self, row):
        now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
        assert pds._row_age_seconds(row, now) is None


# ---------------------------------------------------------------------------
# 3. get_cached_price stamps the age (flag ON) / stamps nothing (flag OFF)
# ---------------------------------------------------------------------------


class TestGetCachedPriceStamp:
    @pytest.mark.asyncio
    async def test_flag_off_returns_no_age_key(self, monkeypatch):
        """Byte-identity: the pre-#57 dict has no `_l2_age_seconds`."""
        _install_rows(monkeypatch, [_row(3 * _DAY)])
        out = await pds.get_cached_price("price:abc", "bahrain")
        assert out is not None
        assert "_l2_age_seconds" not in out
        assert set(out) == {"amount", "currency", "retailer", "url",
                            "source_method", "estimated"}

    @pytest.mark.asyncio
    async def test_flag_on_stamps_a_three_day_old_genuine_row(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        _install_rows(monkeypatch, [_row(3 * _DAY)])
        out = await pds.get_cached_price("price:abc", "bahrain")
        assert out is not None
        assert out["_l2_age_seconds"] == pytest.approx(3 * _DAY, abs=60)

    @pytest.mark.asyncio
    async def test_flag_on_stamps_zero_for_a_brand_new_row(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        _install_rows(monkeypatch, [_row(0)])
        out = await pds.get_cached_price("price:abc", "bahrain")
        assert out is not None
        assert out["_l2_age_seconds"] == pytest.approx(0, abs=60)

    @pytest.mark.asyncio
    async def test_flag_on_ages_the_SELECTED_row_not_data_zero(self, monkeypatch):
        """#54 dependency: under the clobber guard the served row is the older
        GENUINE one, not the newest estimate — the stamp must follow it."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_CLOBBER_GUARD", "true")
        newest_estimate = _row(2 * 3600, source_method="estimated", amount=99.0)
        older_genuine = _row(3 * _DAY, source_method="woo_store_api", amount=45.0)
        _install_rows(monkeypatch, [newest_estimate, older_genuine])
        out = await pds.get_cached_price("price:abc", "bahrain")
        assert out is not None
        assert out["source_method"] == "woo_store_api", "guard should serve the genuine row"
        assert out["_l2_age_seconds"] == pytest.approx(3 * _DAY, abs=60), (
            "stamped the age of response.data[0] instead of the SELECTED row"
        )

    @pytest.mark.asyncio
    async def test_flag_on_does_not_widen_the_freshness_window(self, monkeypatch):
        """A stale row is still a miss — the stamp must not admit anything."""
        monkeypatch.setenv(FLAG, "true")
        _install_rows(monkeypatch, [_row(8 * _DAY)])
        assert await pds.get_cached_price("price:abc", "bahrain") is None

    @pytest.mark.asyncio
    async def test_flag_on_does_not_change_the_selected_columns(self, monkeypatch):
        """The age comes off `fetched_at`, already selected — no schema change."""
        monkeypatch.setenv(FLAG, "true")
        client = _install_rows(monkeypatch, [_row(3 * _DAY)])
        await pds.get_cached_price("price:abc", "bahrain")
        assert client.query.limit_arg == 1


# ---------------------------------------------------------------------------
# 4. The promotion, driven end-to-end through _get_price
# ---------------------------------------------------------------------------


@pytest.fixture
def promo(monkeypatch):
    """Drive `_get_price` to the L2 block and capture the L1 promotion write.

    The L2 hit returns from `_get_price` immediately, so the whole Tier-1/1.5/3
    cascade below it is never reached and needs no stubbing.
    """
    state: dict = {"sets": [], "db_price": None}

    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)  # L1 miss
    monkeypatch.setattr(
        scs, "set_cached", lambda k, v, t: state["sets"].append((k, dict(v), t)) or True
    )

    async def _db(*a, **k):
        row = state["db_price"]
        return dict(row) if row is not None else None

    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _db, raising=False
    )
    state["svc"] = scs.get_comparison_service()
    return state


async def _run(state):
    return await state["svc"]._get_price(
        brand="Dior", name="Sauvage", variant=None, region="bahrain",
        search_query="Dior Sauvage price bahrain", nocache=False,
        category="fragrance",
    )


def _genuine_db_price(age_seconds: int, **over):
    price = {
        "amount": 45.0,
        "currency": "BHD",
        "retailer": "theperfumesclub",
        "url": "https://example.bh/p/dior-sauvage",
        "source_method": "woo_store_api",
        "estimated": False,
        "_l2_age_seconds": age_seconds,
    }
    price.update(over)
    return price


class TestPromotionTTL:
    @pytest.mark.asyncio
    async def test_flag_off_promotes_with_the_full_ttl(self, monkeypatch, promo):
        """Pre-#57 behaviour, byte-identical: a 6-day-old genuine row is
        re-promoted for another FULL 7 days (the bug), and the stamped age — if
        one is somehow present — is ignored."""
        promo["db_price"] = _genuine_db_price(6 * _DAY)
        out = await _run(promo)
        assert out["_cache_source"] == "db"
        assert len(promo["sets"]) == 1
        assert promo["sets"][0][2] == ps.GENUINE_PRICE_CACHE_TTL

    @pytest.mark.asyncio
    async def test_flag_on_promotes_with_only_the_remaining_freshness(
        self, monkeypatch, promo
    ):
        monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(6 * _DAY)
        out = await _run(promo)
        assert out["_cache_source"] == "db"
        assert len(promo["sets"]) == 1
        ttl = promo["sets"][0][2]
        assert ttl == pytest.approx(ps.GENUINE_PRICE_CACHE_TTL - 6 * _DAY, abs=120)
        assert ttl < ps.GENUINE_PRICE_CACHE_TTL, "still promoted for a full window"

    @pytest.mark.asyncio
    async def test_flag_on_shortens_a_converted_row_against_its_own_24h_window(
        self, monkeypatch, promo
    ):
        """The subtraction is against `price_cache_ttl`'s method branch, not a
        hardcoded 7d — a 20h-old converted row keeps ~4h, not ~6 days."""
        monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(
            20 * 3600, source_method="converted_usd", estimated=False
        )
        await _run(promo)
        assert len(promo["sets"]) == 1
        assert promo["sets"][0][2] == pytest.approx(4 * 3600, abs=120)

    @pytest.mark.asyncio
    async def test_flag_on_zero_age_still_gets_the_full_ttl(self, monkeypatch, promo):
        """A brand-new row loses nothing — the fix only removes elapsed time."""
        monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(0)
        await _run(promo)
        assert promo["sets"][0][2] == ps.GENUINE_PRICE_CACHE_TTL

    @pytest.mark.asyncio
    async def test_flag_on_row_at_the_edge_is_served_but_not_promoted(
        self, monkeypatch, promo
    ):
        """Degenerate case: nothing left. Never write a zero/negative TTL."""
        monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(ps.GENUINE_PRICE_CACHE_TTL)
        out = await _run(promo)
        assert promo["sets"] == [], "promoted a row with no freshness left"
        assert out["amount"] == pytest.approx(45.0)
        assert out["_cache_source"] == "db"
        assert out["_cached"] is True

    @pytest.mark.asyncio
    async def test_flag_on_row_past_its_window_is_served_but_not_promoted(
        self, monkeypatch, promo
    ):
        """An age BEYOND the window (env TTL shrunk between write and read) must
        not produce a negative TTL."""
        monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(ps.GENUINE_PRICE_CACHE_TTL + 5 * _DAY)
        out = await _run(promo)
        assert promo["sets"] == []
        assert out["_cache_source"] == "db"

    @pytest.mark.asyncio
    async def test_flag_on_missing_age_falls_back_to_the_full_ttl(
        self, monkeypatch, promo
    ):
        """A legacy/unstamped dict (unparseable `fetched_at`) keeps today's
        answer rather than being refused promotion."""
        monkeypatch.setenv(FLAG, "true")
        price = _genuine_db_price(0)
        price.pop("_l2_age_seconds")
        promo["db_price"] = price
        await _run(promo)
        assert len(promo["sets"]) == 1
        assert promo["sets"][0][2] == ps.GENUINE_PRICE_CACHE_TTL


class TestTransportKeyNeverEscapes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_promoted_result_has_no_age_key(self, monkeypatch, promo, flag_on):
        if flag_on:
            monkeypatch.setenv(FLAG, "true")
        promo["db_price"] = _genuine_db_price(2 * _DAY)
        out = await _run(promo)
        assert promo["sets"], "expected a promotion in this case"
        assert "_l2_age_seconds" not in out
        assert "_l2_age_seconds" not in promo["sets"][0][1], (
            "the private transport key was written into the shared L1 cache"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_not_promoted_result_has_no_age_key(self, monkeypatch, promo, flag_on):
        """The NOT-promoted branch: ENABLE_PRICE_TITLE_PERSIST ON + a title-less
        legacy row refuses the promotion — the pop still has to have happened."""
        if flag_on:
            monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
        promo["db_price"] = _genuine_db_price(2 * _DAY)  # no `title`
        out = await _run(promo)
        assert promo["sets"] == [], "title-less row must not be promoted"
        assert "_l2_age_seconds" not in out
        assert out["_cache_source"] == "db"

    @pytest.mark.asyncio
    async def test_the_age_key_does_not_reach_the_price_ttl_branch(self, monkeypatch):
        """Defensive: even if the key survived, it must not flip the genuine
        branch of price_cache_ttl."""
        price = {"source_method": "woo_store_api", "_l2_age_seconds": 999}
        assert ps.price_cache_ttl(price) == ps.GENUINE_PRICE_CACHE_TTL


# ---------------------------------------------------------------------------
# 5. Safety: the fix may only SHORTEN a TTL, never bypass the _promote gate
# ---------------------------------------------------------------------------


class TestNeverWeakensASafetyCheck:
    @pytest.mark.asyncio
    async def test_flag_on_still_honours_should_cache_price_refusal(
        self, monkeypatch, promo
    ):
        """A titled row whose identity fails the STRONG write gate is refused,
        flag ON exactly as flag OFF. A variant that promoted it anyway would be
        a critical finding, not a cleanup."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
        monkeypatch.setattr(scs, "should_cache_price", lambda *a, **k: False)
        promo["db_price"] = _genuine_db_price(_DAY, title="Some Other Perfume 50ml")
        out = await _run(promo)
        assert promo["sets"] == []
        assert out["_cache_source"] == "db"

    @pytest.mark.asyncio
    async def test_flag_on_never_promotes_for_longer_than_flag_off(
        self, monkeypatch, promo
    ):
        ages = [0, 3600, _DAY, 3 * _DAY, 6 * _DAY]
        off_ttls, on_ttls = [], []
        for age in ages:
            for flag, sink in ((None, off_ttls), ("true", on_ttls)):
                promo["sets"].clear()
                if flag:
                    monkeypatch.setenv(FLAG, flag)
                else:
                    monkeypatch.delenv(FLAG, raising=False)
                promo["db_price"] = _genuine_db_price(age)
                await _run(promo)
                sink.append(promo["sets"][0][2] if promo["sets"] else 0)
        assert all(on <= off for on, off in zip(on_ttls, off_ttls, strict=True))
        assert on_ttls != off_ttls, "flag ON changed nothing"

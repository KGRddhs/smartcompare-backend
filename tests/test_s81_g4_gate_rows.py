"""S81-G4 GREEN-owned gate rows (RULINGS_FIX1_S81_G4 F1-3, the adversary's minor m3).

G4-GR1 test_g4_gr1_full_hit_carries_card_rating (GC-4 (a)): with ENABLE_KB_FIRST_SERVE
ON and two FULL cards (each carrying its own aggregate rating and review count), every
``_fetch_product_data`` result carries ``rating`` == the card's rating and
``review_count`` == the card's review count: the S81-18 H6 write lands after the
rating_data block, and the live rating leg never runs. The values are asserted, not
their presence. Mutant ADV-3 (the H6 card rating / review_count write deleted) is
killed: the result then carries the empty rating_data values (None / None).

G4-GR2 test_g4_gr2_release_owner_check (S81-19): ``EnrichRun.release`` in
scripts/cron_kb_enrich.py never deletes a single-flight lock it does not own: with
the fake Redis holding ``kbenrich:sf:<key>`` = ANOTHER run's id (str or bytes) the key
stays and no DELETE is sent; with the key = this run's id (str or bytes) it is
deleted; with a GET of None nothing is deleted. Mutant ADV-7 (release deletes
without the owner check) is killed by the ``other_*`` and ``absent`` cases.

Both rows drive the frozen RED files' seams (the S18 faked compare is reached through
``tests.test_s81_s18_kb_first_serve``, as G3-GR3 reaches the S17 file); netguard on,
every leaf faked, synthetic identities and hosts only; pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import importlib
import os

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402


def _s18():
    return importlib.import_module("tests.test_s81_s18_kb_first_serve")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    s18 = _s18()
    for name in s18.CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    for name in ("ENABLE_KB_ENRICH_WORKER", "ENABLE_KB_GAP_FILL", "ENABLE_KB_GAP_WEB_SEARCH",
                 "KB_ENRICH_LOCK_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    from app.services import kb_serve

    kb_serve._SEEN.clear()
    yield
    kb_serve._SEEN.clear()


# ---------------------------------------------------------------------------
# G4-GR1
# ---------------------------------------------------------------------------

def test_g4_gr1_full_hit_carries_card_rating(monkeypatch):
    import app.services.structured_comparison_service as scs

    s18 = _s18()
    card_a = s18._card(s18.P0)
    card_b = s18._card_b()
    card_a["rating"] = {"sources": 2, "review_count": 31, "rating": 4.6}
    card_b["rating"] = {"sources": 1, "review_count": 57, "rating": 4.2}
    s18._on(monkeypatch, {s18._pid(s18.P0): card_a, s18._pid(s18.P1): card_b})

    results = []
    original = scs.StructuredComparisonService._fetch_product_data

    async def _recording(self, *args, **kwargs):
        out = await original(self, *args, **kwargs)
        results.append(out)
        return out

    monkeypatch.setattr(scs.StructuredComparisonService, "_fetch_product_data", _recording)
    state = {}
    body = asyncio.run(s18._compare(monkeypatch, "rest", state=state))
    assert (body.get("metadata") or {}).get("kb_hit") == ["full", "full"], body.get("metadata")
    assert state["calls"]["_get_verified_rating"] == [], state["calls"]["_get_verified_rating"]
    assert len(results) == 2, len(results)
    got = sorted((r.get("rating"), r.get("review_count")) for r in results)
    assert got == [(4.2, 57), (4.6, 31)], got


# ---------------------------------------------------------------------------
# G4-GR2
# ---------------------------------------------------------------------------

class _Redis:
    def __init__(self, held):
        self.store = {}
        self.calls = []
        self._held = held

    def get(self, key):
        self.calls.append(("get", key))
        return self.store.get(key)

    def delete(self, *keys):
        self.calls.append(("delete",) + tuple(keys))
        for k in keys:
            self.store.pop(k, None)
        return len(keys)

    def set(self, *a, **k):  # pragma: no cover - release never sets
        raise AssertionError("release must never SET")


@pytest.mark.parametrize("case", ["other_str", "other_bytes", "own_str", "own_bytes", "absent"])
def test_g4_gr2_release_owner_check(monkeypatch, case):
    from datetime import datetime, timezone

    enrich = importlib.import_module("scripts.cron_kb_enrich")
    redis = _Redis(None)
    run = enrich.EnrichRun(None, redis, datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc), False)
    key = enrich.lock_key("acme|nimbus noir|-|eau de parfum")
    assert key.startswith("kbenrich:sf:")
    other = "0" * 31 + "1"
    assert other != run.run_id
    value = {"other_str": other, "other_bytes": other.encode("ascii"), "own_str": run.run_id,
             "own_bytes": run.run_id.encode("ascii"), "absent": None}[case]
    if value is not None:
        redis.store[key] = value

    run.release(key)

    deletes = [c for c in redis.calls if c[0] == "delete"]
    assert ("get", key) in redis.calls, redis.calls
    if case.startswith("own"):
        assert deletes == [("delete", key)], redis.calls
        assert key not in redis.store
    elif case == "absent":
        assert deletes == [], redis.calls
    else:
        assert deletes == [], redis.calls
        assert redis.store.get(key) == value

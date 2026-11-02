"""S81-09 DEVICE-QUOTA-RIYADH: the GREEN-owned gate rows (GATE_S81_09 GC-1, GC-2,
GC-3; RULINGS_FIX1_S81_09 F1-2, F1-3, F1-4, F1-12), kept in their own file so the frozen RED file
(tests/test_s81_s09_device_quota.py, sha256 843a6bab...) and its golden fixture
(tests/fixtures/s81_s09_flag_off_golden.json, sha256 02b29cc6...) keep their bytes.

Every row reuses the RED file's hermetic harness (the recording FakeRedis that
emulates both Lua scripts, the frozen clock, the tier stubs, the route stubs, the
referral fake client and the autouse env fixture), imported the way
tests/test_s81_s08b_gate_rows.py reaches its RED file. Synthetic values only
(the RED file's uuid-shaped ids, "a" * 64 fingerprints and the concatenated
pepper); every row sets the unit flags itself.

Row map (node prefix -> ruling; the mutant class each row kills):
  test_gc1a_  GC-1(a) under the pause the invite is marked redeemed and no
              lifetime_invites_consumed slot is read or spent (step 4 kept /
              redeemed mark skipped)
  test_gc1b_  GC-1(b) flag OFF: step 4 runs as at base (pause not gated)
  test_gc2_   GC-2    the consume result's remaining.daily is the BINDING min,
              in both directions and on a device refusal; the consume result
              never reaches the wire beyond the allow-listed keys (all six sites)
  test_gc3_   GC-3    limits.device_daily = 3 appended last without a device key
  test_g4_    the three ENABLE_DEVICE_DAILY_QUOTA readers agree (no drift)
  test_g5_    explicit consumed_keys and the stash share ONE latch (no double
              refund)
  test_g6_    the quota-path status GETs take the ST1 pool under
              ENABLE_USAGE_PATH_OFFLOOP, and a dispatch failure reads inline
  test_f1_2_  F1-2    the quota-path status under ENABLE_RIYADH_RESET after 21:00
              UTC reads the Riyadh-dated counters (status keyed on the UTC day)
  test_f1_3_  F1-3    a NULL-tier status renders the base body (a NULL tier gets
              the quota-path status)
  test_f1_4_  F1-4    reply code 2 on an account-only consume is a BadReply (the
              'code 2 only with a device key' clause dropped)
  test_f1_12_ F1-12   the debit stash cannot cross requests (the stash as a
              process-global holder)
"""

import json

import pytest

from tests.test_s81_s09_device_quota import (  # noqa: F401  (the autouse fixture + helpers)
    FAIL_RESULT,
    FP,
    OK_RESULT,
    QUOTA,
    SITES,
    UID,
    US_LOGGER,
    USER,
    T0,
    T2,
    T3,
    TestClient,
    _TRUTH,
    _D,
    _DV,
    _M,
    _arun,
    _as_user,
    _client,
    _consume,
    _device_capped_route,
    _evals,
    _freeze,
    _full_config,
    _golden,
    _install_redis,
    _logs,
    _observe_referral,
    _quota_status,
    _req,
    _s09_env,
    _set_raw,
    _status_route,
    _stub_routes,
    _tier,
    app_main,
    eh,
    rsvc,
    text_routes,
    us,
)

OFFLOOP = "ENABLE_USAGE_PATH_OFFLOOP"
_REDEEMED_TABLE = "referral_invites"
_WIRE_KEYS_UNDER_FLAG = ["code", "error", "request_id", "resets_at", "retry_after_seconds",
                         "scope", "success"]


def _ops_touching(ops, needle):
    return [op for op in ops if needle in json.dumps(op)]


# ---------------------------------------------------------------------------
# GC-1: the referral pause and Loop-2 step 4
# ---------------------------------------------------------------------------
def test_gc1a_pause_marks_redeemed_and_keeps_the_lifetime_slot(monkeypatch):
    """GC-1(a): under ENABLE_DEVICE_DAILY_QUOTA the Loop-2 chain writes exactly ONE
    Supabase op, the redeemed mark (equal to the base mark of the golden), and
    neither reads nor writes users.lifetime_invites_consumed (a paused invite
    spends no lifetime slot); no reward push."""
    golden_ops = _golden()["referral_loop2"]["ops"]
    redeemed = [op for op in golden_ops if op[0] == _REDEEMED_TABLE]
    assert len(redeemed) == 1, golden_ops
    obs = _observe_referral(monkeypatch, "loop2", quota="true")
    assert obs["ops"] == redeemed, obs["ops"]
    assert _ops_touching(obs["ops"], "lifetime_invites_consumed") == [], obs["ops"]
    assert obs["pushes"] == [], obs["pushes"]


@pytest.mark.parametrize("raw", [None, "false", "0", "off", ""], ids=["unset", "false", "0", "off", "empty"])
def test_gc1b_flag_off_step4_runs_as_at_base(monkeypatch, raw):
    """GC-1(b): flag OFF (five spellings) Loop 2 still reads the referrer's
    lifetime_invites_consumed and writes it + 1 (the base step 4), before the
    redeemed mark, exactly as the golden recorded at base."""
    obs = _observe_referral(monkeypatch, "loop2", quota=raw)
    golden_ops = _golden()["referral_loop2"]["ops"]
    step4 = _ops_touching(golden_ops, "lifetime_invites_consumed")
    assert len(step4) == 2, golden_ops
    assert _ops_touching(obs["ops"], "lifetime_invites_consumed") == step4, obs["ops"]
    update = step4[1]
    assert update[1] == ["update", [{"lifetime_invites_consumed": 2}], {}], update
    assert obs["ops"].index(step4[1]) < [op[0] for op in obs["ops"]].index(_REDEEMED_TABLE)


# ---------------------------------------------------------------------------
# GC-2: the consume result's remaining.daily is the binding axis
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("acct,dev,daily,dev_left", [
    (0, 1, 1, 1),   # after the debit: account 1 used (2 left), device 2 used (1 left)
    (1, 0, 1, 2),   # after the debit: account 2 used (1 left), device 1 used (2 left)
], ids=["device_binds", "account_binds"])
def test_gc2_consume_result_reports_the_binding_min(monkeypatch, acct, dev, daily, dev_left):
    """GC-2: a code-0 consume reports remaining.daily = min(account left, device
    left) and remaining.device_daily = the device left (the full dict, key order
    included); the status of the same state reports the same binding axis (used.daily
    the binding axis's used figure)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): acct, _DV(): dev})
    res = _arun(lambda: _consume(FP))
    want = {"allowed": True, "reason": None, "tier": "free", "consumed": True,
            "consumed_keys": {"daily": _D(), "device_daily": _DV()},
            "remaining": {"daily": daily, "monthly": 10, "lifetime_free": 0, "device_daily": dev_left}}
    assert json.dumps(res) == json.dumps(want), res
    after_acct, after_dev = red.store[_D()], red.store[_DV()]
    resp, _red = _quota_status(monkeypatch, life=5, acct=after_acct, dev=after_dev)
    body = resp.json()
    device_binds = dev_left <= 3 - after_acct
    assert body["remaining"]["daily"] == daily, body
    assert body["remaining"]["device_daily"] == dev_left, body
    assert body["used"]["daily"] == (after_dev if device_binds else after_acct), body
    assert body["counted_scope"] == ("device_daily" if device_binds else "daily"), body


def test_gc2_device_refusal_reports_daily_zero(monkeypatch):
    """GC-2: a device refusal (device at the cap, the account at 0) reports
    remaining.daily 0 (the binding axis), never the account's 3."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    _install_redis(monkeypatch, {_D(): 0, _DV(): 3})
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is False and res["reason"] == "device_daily_limit", res
    assert res["remaining"] == {"daily": 0, "monthly": 10, "lifetime_free": 0, "device_daily": 0}, res


@pytest.mark.parametrize("site", SITES)
def test_gc2_consume_result_never_reaches_the_wire(monkeypatch, site):
    """GC-2 (the site measurement): the consume result reaches a response only
    through the 429 detail, whose tier / remaining the handler drops; under the
    flag the wire carries exactly the base keys + resets_at, scope and
    retry_after_seconds, at every consume site."""
    _device_capped_route(monkeypatch)
    with _as_user(USER):
        resp = _req(_client(), site)
    assert resp.status_code == 429, resp.text
    assert sorted(resp.json()) == _WIRE_KEYS_UNDER_FLAG, resp.text


# ---------------------------------------------------------------------------
# GC-3: limits.device_daily always under the flag
# ---------------------------------------------------------------------------
def test_gc3_limits_device_daily_without_a_device_key(monkeypatch):
    """GC-3: with no device header the quota-path status still carries
    limits.device_daily = 3, appended LAST in limits; remaining.device_daily is
    absent and counted_scope is daily."""
    resp, _red = _quota_status(monkeypatch, life=7, acct=1, dev=0, fp=None)
    body = json.loads(resp.text)
    assert list(body["limits"]) == ["daily", "monthly", "monthly_base", "monthly_bonus",
                                    "lifetime_free", "device_daily"], body
    assert body["limits"]["device_daily"] == 3, body
    assert "device_daily" not in body["remaining"] and body["counted_scope"] == "daily", body


# ---------------------------------------------------------------------------
# design pins of the GREEN code (no RED row covers them)
# ---------------------------------------------------------------------------
def test_g4_the_three_quota_readers_agree(monkeypatch):
    """The usage reader, the handler's local one-liner and the referral pause read
    the SAME name with the same idiom, per call, over 13 spellings."""
    readers = (us.device_daily_quota_enabled, eh._device_quota_keys_enabled,
               rsvc._referral_rewards_paused)
    for raw, want in _TRUTH:
        _set_raw(monkeypatch, QUOTA, raw)
        assert [r() for r in readers] == [want] * 3, raw


def test_g5_explicit_keys_and_the_stash_share_one_latch(monkeypatch):
    """A refund that passes the consume's own consumed_keys refunds both keys by
    ONE EVAL and sets the stash latch, so a later refund of the same debit (no
    keys) makes no Redis call; the counters are back where they started."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    marks = {}

    async def flow():
        res = await _consume(FP)
        marks["c"] = len(red.calls)
        await us.refund_comparison_credit(UID, res["consumed_keys"])
        marks["r1"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        return res

    res = _arun(flow)
    assert res["consumed"] is True, res
    assert red.calls[marks["c"]:marks["r1"]] == [["eval", "refund", [_D(), _DV()], []]], red.calls
    assert red.calls[marks["r1"]:] == [], red.calls
    assert red.store == {_D(): 1, _DV(): 1}, red.store


def test_g6_status_counts_take_the_st1_pool_under_offloop(monkeypatch):
    """Under ENABLE_USAGE_PATH_OFFLOOP the quota-path status GETs run as jobs of
    usage_service.run_redis_offloop_pool (the ST1 placement), one per counter, and
    the body equals the inline body."""
    inline_resp, _red = _quota_status(monkeypatch, life=7, acct=1, dev=2)
    jobs = []
    real_pool = us.run_redis_offloop_pool

    async def spy(fn, *args, **kwargs):
        jobs.append((getattr(fn, "__name__", repr(fn)), args))
        return await real_pool(fn, *args, **kwargs)

    monkeypatch.setattr(us, "run_redis_offloop_pool", spy)
    monkeypatch.setenv(OFFLOOP, "true")
    pooled_resp, _red2 = _quota_status(monkeypatch, life=7, acct=1, dev=2)
    assert jobs == [("_get_redis_count", (_D(),)), ("_get_redis_count", (_DV(),))], jobs
    assert pooled_resp.text == inline_resp.text, pooled_resp.text


def test_g6_status_dispatch_failure_reads_inline(monkeypatch):
    """A pool dispatch failure under ENABLE_USAGE_PATH_OFFLOOP logs ONE WARNING
    (the type name only) and reads the counters inline: the same body."""
    inline_resp, _red = _quota_status(monkeypatch, life=7, acct=1, dev=2)

    def boom(*_a, **_kw):
        raise RuntimeError("s09 probe: pool unavailable")

    monkeypatch.setattr(us, "run_redis_offloop_pool", boom)
    monkeypatch.setenv(OFFLOOP, "true")
    with _logs(US_LOGGER) as lg:
        resp, red = _quota_status(monkeypatch, life=7, acct=1, dev=2)
    assert resp.text == inline_resp.text, resp.text
    assert lg.lines(US_LOGGER) == [[
        "WARNING",
        "[USAGE-OFFLOOP] dispatch failed fn=get_device_usage_status type=RuntimeError -- inline fallback",
    ]], lg.lines(US_LOGGER)
    assert sorted(red.calls) == sorted([["get", _D()], ["get", _DV()]]), red.calls


# ---------------------------------------------------------------------------
# fix round 1 (RULINGS_FIX1_S81_09 F1-2, F1-3, F1-4, F1-12): the adversaries'
# pin gaps on correct code (mutants X10, X07, X01, B40)
# ---------------------------------------------------------------------------
_RIYADH_DAY = "2026-10-30"  # T2 / T3 in Riyadh (00:00:00 / 00:00:30 +03:00)
_UTC_DAY = "2026-10-29"     # T2 / T3 in UTC (21:00:00Z / 21:00:30Z)


def test_f1_2_status_after_21_utc_reads_the_riyadh_day(monkeypatch):
    """F1-2 (m1, X10): under ENABLE_RIYADH_RESET at T2 and T3 (21:00:00Z and
    21:00:30Z: already 2026-10-30 in Riyadh, still 2026-10-29 in UTC) the
    quota-path /usage/status GETs exactly the Riyadh-dated account and device
    counters, never the UTC-day keys (which hold yesterday's exhausted counts
    here); the raw body, key order included, carries the Riyadh-day counts and
    resets at the NEXT Riyadh midnight."""
    want = ('{"tier":"free","used":{"daily":2,"monthly":0,"lifetime":7},'
            '"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3,'
            '"device_daily":3},'
            '"remaining":{"daily":1,"monthly":10,"lifetime_free":0,"device_daily":1},'
            '"resets_at":"2026-10-31T00:00:00+03:00","counted_scope":"device_daily"}')
    for at in (T2, T3):
        _full_config(monkeypatch, quota="true", riyadh="true")
        _freeze(monkeypatch, at)
        _tier(monkeypatch, "free", 7)
        red = _install_redis(monkeypatch, {_D(_RIYADH_DAY): 1, _DV(_RIYADH_DAY): 2,
                                           _D(_UTC_DAY): 3, _DV(_UTC_DAY): 3})
        resp = _status_route()
        assert resp.status_code == 200, (at, resp.text)
        assert sorted(red.calls) == sorted([["get", _D(_RIYADH_DAY)], ["get", _DV(_RIYADH_DAY)]]), (
            at, red.calls)
        assert resp.text == want, (at, resp.text)


def test_f1_3_null_tier_status_renders_the_base_body(monkeypatch):
    """F1-3 (m2, X07; the STATUS half of R-S09-5): under ENABLE_DEVICE_DAILY_QUOTA
    a NULL subscription_tier gets the BASE /usage/status body, byte for byte the
    body of the same state with the flag OFF (the full configuration present in
    both runs): no device-counter GET and none of the quota-path keys."""
    store = {_D(): 2, _M(): 7, _DV(): 1}
    _full_config(monkeypatch)
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, None, 5)
    _install_redis(monkeypatch, store)
    base = _status_route()
    assert base.status_code == 200, base.text
    _full_config(monkeypatch, quota="true")
    red = _install_redis(monkeypatch, store)
    resp = _status_route()
    assert resp.status_code == 200, resp.text
    assert resp.text == base.text, (resp.text, base.text)
    body = resp.json()
    assert body["tier"] is None and "counted_scope" not in body and "resets_at" not in body, body
    assert "device_daily" not in body["limits"] and "device_daily" not in body["remaining"], body
    assert [c for c in red.calls if "usage:device:" in json.dumps(c)] == [], red.calls


def test_f1_4_code_2_on_an_account_only_call_is_a_bad_reply(monkeypatch):
    """F1-4 (m3, X01; C19): reply code 2 (the device refusal) is valid only when
    a device key was sent. _parse_consume_reply reads [2, 0, 0] as BadReply
    (None) without a device key and as the refusal with one; an account-only
    consume (no device header bound) given that reply fails OPEN: allowed,
    consumed False, no consumed_keys, ONE consume EVAL over the account key
    alone, ONE WARNING type=BadReply, and no stash (a later refund makes no
    EVAL and no write)."""
    parse = us._parse_consume_reply
    assert parse([2, 0, 0], False) is None
    assert parse([2, 0, 0], True) == (2, 0, 0)
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, eval_reply=[2, 0, 0])
    marks = {}

    async def flow():
        res = await _consume(None)
        marks["c"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        return res

    with _logs(US_LOGGER) as lg:
        res = _arun(flow, headers=None)
    assert res["allowed"] is True and res.get("consumed") is False and "consumed_keys" not in res, res
    consume = _evals(red, "consume")
    assert len(consume) == 1 and consume[0][2] == [_D()], red.calls
    assert lg.tagged().count(["WARNING", "[USAGE-DEVICE] consume fail-open type=BadReply"]) == 1, lg.records
    assert _evals(red, "refund") == [], red.calls
    assert all(c[0] == "get" for c in red.calls[marks["c"]:]), red.calls


def test_f1_12_the_debit_stash_cannot_cross_requests(monkeypatch):
    """F1-12 (m-QB-4, the billing lens's probe P1; kills the stash as a
    process-global holder, B40): request 1 under ENABLE_DEVICE_DAILY_QUOTA debits
    both keys by the consume EVAL and DELIVERS (its stash is never refunded);
    the flag then goes OFF and request 2 on the SAME TestClient fails: its
    refund is the base refund of its own base debit, never a refund EVAL of
    request 1's delivered debit. The device key keeps request 1's debit, the
    account daily is 1 and the monthly 0."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 0, _DV(): 0})
    _stub_routes(monkeypatch, result=OK_RESULT)
    svc = text_routes.get_comparison_service()
    with _as_user(USER):
        with TestClient(app_main.app, raise_server_exceptions=False) as client:
            r1 = _req(client, "text_post")
            assert r1.status_code == 200, r1.text
            assert red.store.get(_D()) == 1 and red.store.get(_DV()) == 1, red.store
            monkeypatch.setenv(QUOTA, "false")
            svc._result = FAIL_RESULT
            r2 = _req(client, "text_post")
            assert r2.status_code != 429, r2.text
    assert len(_evals(red, "consume")) == 1, red.calls
    assert _evals(red, "refund") == [], red.calls
    assert red.store.get(_DV()) == 1, red.store
    assert red.store.get(_D()) == 1 and red.store.get(_M(), 0) == 0, red.store

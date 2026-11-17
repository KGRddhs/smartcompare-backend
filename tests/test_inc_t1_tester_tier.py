"""INC-T1 TESTER-TIER (S97 lane, 2026-11-17): a third TIER_LIMITS entry,
``tester`` (lifetime_free 0, monthly 30000, daily 1000), plus the module
constant ``TESTER_TIER``. No flag: the change is inert until a ``users`` row
carries ``subscription_tier = 'tester'`` exactly.

RED rows T1..T5 fail at base on an AssertionError only (the new names are read
with ``TIER_LIMITS.get`` / ``getattr``). PIN rows P1..P5 are green at base and at
head. Hermetic: Redis and Supabase are faked (the S81-09 / ST1 patterns), every
id is built at run time, no network.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import uuid

import pytest

import app.main as app_main  # noqa: F401 - FIRST: the dotenv guard (load_dotenv at import)
from app.services import category_gate as cg
from app.services import referral_service as rs
from app.services import usage_service as us
from app.utils import request_context as rc

QUOTA = "ENABLE_DEVICE_DAILY_QUOTA"
RIYADH = "ENABLE_RIYADH_RESET"
CTX = "ENABLE_REQUEST_CONTEXT_HEADERS"
PEPPER_ENV = "DEVICE_KEY_PEPPER"
EXEMPT = "DEVICE_QUOTA_EXEMPT_USER_IDS"
OFFLOOP = "ENABLE_USAGE_PATH_OFFLOOP"
ASYNC_R = "ENABLE_ASYNC_REDIS_OFFLOAD"
SYNC = "ENABLE_SYNC_DB_OFFLOAD"
S77 = "ENABLE_PRICE_PATH_REDIS_OFFLOOP"
METER = "ENABLE_PAID_ROUTE_METERING"
ANON = "ENABLE_ANON_USAGE_GATE"

CLEAN_ENV = (QUOTA, RIYADH, CTX, PEPPER_ENV, EXEMPT, OFFLOOP, ASYNC_R, SYNC, S77, METER, ANON)

TOKEN = "synthetic-access"
EXPECTED_TESTER = {"lifetime_free": 0, "monthly": 30000, "daily": 1000}
BASE_FREE = {"lifetime_free": 3, "monthly": 10, "daily": 3}
BASE_PREMIUM = {"lifetime_free": 0, "monthly": 70, "daily": 10}

_REAL_ATOMIC_ASYNC = us._atomic_consume_async
_REAL_DEVICE_QUOTA = us._consume_device_quota


def _uid():
    return str(uuid.uuid4())


def _fp():
    return secrets.token_hex(32)  # 64 lower-case hex, the X-Device-Fingerprint shape


def _dumps(obj):
    """Insertion-order JSON: equality asserts values AND key order."""
    return json.dumps(obj, default=str)


# ---------------------------------------------------------------------------
# fakes (the S81-09 FakeRedis and _tier patterns, trimmed)
# ---------------------------------------------------------------------------
class FakeRedis:
    """Recording Upstash stand-in (redis-py eval shape)."""

    def __init__(self, store=None):
        self.store = dict(store or {})
        self.calls = []

    def _int(self, key):
        return int(self.store.get(key, 0))

    def get(self, key):
        self.calls.append(["get", key])
        value = self.store.get(key)
        return None if value is None else str(value)

    def incrby(self, key, n):
        self.calls.append(["incrby", key, n])
        self.store[key] = self._int(key) + n
        return self.store[key]

    def incr(self, key):
        return self.incrby(key, 1)

    def decrby(self, key, n):
        self.calls.append(["decrby", key, n])
        self.store[key] = self._int(key) - n
        return self.store[key]

    def expire(self, key, ttl):
        self.calls.append(["expire", key, ttl])
        return True

    def expireat(self, key, when):
        self.calls.append(["expireat", key, when])
        return True

    def eval(self, script, numkeys, *keys_and_args):
        keys = list(keys_and_args[:numkeys])
        self.calls.append(["eval", keys])
        if script == us.DEVICE_CONSUME_SCRIPT:
            for key in keys:
                self.store[key] = self._int(key) + 1
            return [0, self._int(keys[0]), self._int(keys[1]) if len(keys) > 1 else 0]
        return [-1 for _ in keys]

    def evals(self):
        return [c for c in self.calls if c[0] == "eval"]


def _install_redis(mp, store=None):
    red = FakeRedis(store)
    mp.setattr(us, "redis_client", red)
    return red


def _tier(mp, tier, life=12, bonus=0, reads=None):
    async def _t(uid):
        if reads is not None:
            reads.append(("tier", uid))
        return {"subscription_tier": tier, "lifetime_comparisons_used": life}

    async def _b(uid):
        if reads is not None:
            reads.append(("bonus", uid))
        return bonus

    mp.setattr(us, "_get_user_tier_info", _t)
    mp.setattr(us, "_get_active_referral_bonus", _b)


def _atomic_spy(mp):
    calls = []

    async def _spy(user_id, daily_limit, monthly_cap):
        calls.append((user_id, daily_limit, monthly_cap))
        return await _REAL_ATOMIC_ASYNC(user_id, daily_limit, monthly_cap)

    mp.setattr(us, "_atomic_consume_async", _spy)
    return calls


def _device_quota_spy(mp):
    calls = []

    async def _spy(user_id, device_fp):
        calls.append(user_id)
        return await _REAL_DEVICE_QUOTA(user_id, device_fp)

    mp.setattr(us, "_consume_device_quota", _spy)
    return calls


def _b1_config(mp, *, quota):
    """B1: the full S81-09 configuration present, the quota flag as named, the
    allow-list set to a synthetic id that is never the tested user's."""
    if quota is None:
        mp.delenv(QUOTA, raising=False)
    else:
        mp.setenv(QUOTA, quota)
    mp.setenv(CTX, "true")
    mp.setenv(PEPPER_ENV, "t1" + "-pepper-" + uuid.uuid4().hex)
    mp.setenv(EXEMPT, _uid())
    mp.setenv(METER, "true")


def _drop_offloop_pools():
    import concurrent.futures

    from app.utils import redis_offloop as ro

    for name, value in list(vars(ro).items()):
        if isinstance(value, concurrent.futures.ThreadPoolExecutor) and str(
            getattr(value, "_thread_name_prefix", "")
        ).startswith("redis-offloop"):
            value.shutdown(wait=False, cancel_futures=True)
            setattr(ro, name, None)


@pytest.fixture(autouse=True)
def _t1_env(monkeypatch):
    for name in CLEAN_ENV:
        monkeypatch.delenv(name, raising=False)
    rc._reset_pepper_warning()
    _drop_offloop_pools()
    yield
    _drop_offloop_pools()
    rc._reset_pepper_warning()


def _run(coro):
    return asyncio.run(coro)


def _keys(uid):
    return us._daily_key(uid), us._monthly_key(uid)


def _tester_limits():
    return getattr(us, "TIER_LIMITS", {}).get("tester")


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------
def test_t1_tier_limits_has_tester_and_constant():
    """RED T1: TIER_LIMITS['tester'] is the spec literal; TESTER_TIER == 'tester'."""
    assert _tester_limits() == EXPECTED_TESTER, _tester_limits()
    assert getattr(us, "TESTER_TIER", None) == "tester"


@pytest.mark.parametrize("daily_at", [3, 10], ids=["free_cap", "premium_cap"])
@pytest.mark.parametrize("bonus", [0, 5], ids=["bonus0", "bonus5"])
def test_t2_tester_consume_past_free_and_premium_caps(monkeypatch, daily_at, bonus):
    """RED T2: a tester at the free (3) and the premium (10) daily count is
    allowed and debited; the atomic consume gets (1000, 30000 + bonus)."""
    uid = _uid()
    d, m = _keys(uid)
    red = _install_redis(monkeypatch, {d: daily_at, m: 40})
    _tier(monkeypatch, "tester", life=12, bonus=bonus)
    calls = _atomic_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN))
    assert calls == [(uid, 1000, 30000 + bonus)], calls
    assert out == {
        "allowed": True, "reason": None, "tier": "tester", "consumed": True,
        "consumed_keys": {"daily": d, "monthly": m},
        "remaining": {"daily": 1000 - (daily_at + 1), "monthly": 30000 + bonus - 41, "lifetime_free": 0},
    }, out
    assert red.store[d] == daily_at + 1 and red.store[m] == 41
    assert red.evals() == []


@pytest.mark.parametrize("daily_at,allowed", [(1000, False), (999, True)], ids=["at_cap", "one_below"])
def test_t3_tester_daily_cap_is_real(monkeypatch, daily_at, allowed):
    """RED T3: at 1000 the tester is refused (daily_limit, nothing kept); at 999
    the last credit is allowed."""
    uid = _uid()
    d, m = _keys(uid)
    red = _install_redis(monkeypatch, {d: daily_at, m: 40})
    _tier(monkeypatch, "tester", life=12, bonus=5)
    calls = _atomic_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN))
    assert calls == [(uid, 1000, 30005)], calls
    if allowed:
        assert out == {
            "allowed": True, "reason": None, "tier": "tester", "consumed": True,
            "consumed_keys": {"daily": d, "monthly": m},
            "remaining": {"daily": 0, "monthly": 30005 - 41, "lifetime_free": 0},
        }, out
        assert red.store[d] == 1000
    else:
        assert out == {
            "allowed": False, "reason": "daily_limit", "tier": "tester", "consumed": False,
            "remaining": {"daily": 0, "monthly": 30005 - 40, "lifetime_free": 0},
        }, out
        assert red.store[d] == 1000 and red.store[m] == 40


@pytest.mark.parametrize("offloop", [None, "true"], ids=["offloop_off", "offloop_on"])
@pytest.mark.parametrize("daily_at", [3, 1000], ids=["daily3", "daily1000"])
def test_t4_check_usage_allowed_tester(monkeypatch, offloop, daily_at):
    """RED T4: check_usage_allowed (the one compute body, both ST1 dispatch
    states): daily 3 allowed, daily 1000 daily_limit."""
    if offloop:
        monkeypatch.setenv(OFFLOOP, offloop)
    uid = _uid()
    d, m = _keys(uid)
    _install_redis(monkeypatch, {d: daily_at, m: 40})
    _tier(monkeypatch, "tester", life=12, bonus=5)
    out = _run(us.check_usage_allowed(uid, TOKEN))
    if daily_at == 3:
        expected = {"allowed": True, "reason": None, "tier": "tester",
                    "remaining": {"daily": 997, "monthly": 29965, "lifetime_free": 0}}
    else:
        expected = {"allowed": False, "reason": "daily_limit", "tier": "tester",
                    "remaining": {"daily": 0, "monthly": 29965, "lifetime_free": 0}}
    assert out == expected, out


TESTER_STATUS = {
    "tier": "tester",
    "used": {"daily": 7, "monthly": 40, "lifetime": 12},
    "limits": {"daily": 1000, "monthly": 30005, "monthly_base": 30000, "monthly_bonus": 5, "lifetime_free": 0},
    "remaining": {"daily": 993, "monthly": 29965, "lifetime_free": 0},
}


@pytest.mark.parametrize("path", ["body", "get_usage_status", "device_status_quota_on"])
def test_t5_usage_status_body_tester(monkeypatch, path):
    """RED T5: the /usage/status base body for a tester (fields and key order);
    no counted_scope, no resets_at; the quota-ON device status returns the
    same base body."""
    uid = _uid()
    d, m = _keys(uid)
    _install_redis(monkeypatch, {d: 7, m: 40})
    _tier(monkeypatch, "tester", life=12, bonus=5)
    if path == "body":
        out = us._usage_status_body({"subscription_tier": "tester", "lifetime_comparisons_used": 12}, 5, 7, 40)
    elif path == "get_usage_status":
        out = _run(us.get_usage_status(uid, TOKEN))
    else:
        _b1_config(monkeypatch, quota="true")
        out = _run(us.get_device_usage_status(uid, TOKEN, device_fp=_fp()))
    assert "counted_scope" not in out and "resets_at" not in out, out
    assert _dumps(out) == _dumps(TESTER_STATUS), out


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------
def test_p1_free_and_premium_entries_unchanged():
    """PIN P1a: the free and premium entries are the base literals."""
    assert us.TIER_LIMITS["free"] == BASE_FREE
    assert us.TIER_LIMITS["premium"] == BASE_PREMIUM


@pytest.mark.parametrize("tier", ["free", "premium"])
def test_p1_consume_outputs_recorded(monkeypatch, tier):
    """PIN P1b: free / premium consume for a fixed input equal the base literals."""
    uid = _uid()
    d, m = _keys(uid)
    start_daily = 1 if tier == "free" else 3
    _install_redis(monkeypatch, {d: start_daily, m: 4})
    _tier(monkeypatch, tier, life=5, bonus=2)
    calls = _atomic_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN))
    if tier == "free":
        assert calls == [(uid, 3, 12)], calls
        remaining = {"daily": 1, "monthly": 7, "lifetime_free": 0}
    else:
        assert calls == [(uid, 10, 72)], calls
        remaining = {"daily": 6, "monthly": 67, "lifetime_free": 0}
    assert out == {
        "allowed": True, "reason": None, "tier": tier, "consumed": True,
        "consumed_keys": {"daily": d, "monthly": m}, "remaining": remaining,
    }, out


def test_p1_free_lifetime_window_recorded(monkeypatch):
    """PIN P1c: the free lifetime-free window (life 1) bypasses the caps as at base."""
    uid = _uid()
    d, m = _keys(uid)
    red = _install_redis(monkeypatch, {d: 3, m: 10})
    _tier(monkeypatch, "free", life=1, bonus=2)
    calls = _atomic_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN))
    assert calls == []
    assert out == {
        "allowed": True, "reason": None, "tier": "free", "consumed": True,
        "consumed_keys": {"daily": d, "monthly": m},
        "remaining": {"daily": 3, "monthly": 12, "lifetime_free": 2},
    }, out
    assert red.store[d] == 4 and red.store[m] == 11


ALLOWED_LITERALS = [
    ("free", 1, {"allowed": True, "reason": None, "tier": "free",
                 "remaining": {"daily": 2, "monthly": 8, "lifetime_free": 0}}),
    ("free", 3, {"allowed": False, "reason": "daily_limit", "tier": "free",
                 "remaining": {"daily": 0, "monthly": 8, "lifetime_free": 0}}),
    ("premium", 3, {"allowed": True, "reason": None, "tier": "premium",
                    "remaining": {"daily": 7, "monthly": 68, "lifetime_free": 0}}),
    ("premium", 10, {"allowed": False, "reason": "daily_limit", "tier": "premium",
                     "remaining": {"daily": 0, "monthly": 68, "lifetime_free": 0}}),
]


@pytest.mark.parametrize("tier,daily,expected", ALLOWED_LITERALS,
                         ids=["free_ok", "free_daily", "premium_ok", "premium_daily"])
def test_p1_allowed_body_recorded(tier, daily, expected):
    """PIN P1d: the one compute body of check_usage_allowed for free / premium."""
    out = us._usage_allowed_body({"subscription_tier": tier, "lifetime_comparisons_used": 5}, 2, daily, 4)
    assert out == expected, out


STATUS_LITERALS = {
    "free": {
        "tier": "free",
        "used": {"daily": 1, "monthly": 4, "lifetime": 5},
        "limits": {"daily": 3, "monthly": 12, "monthly_base": 10, "monthly_bonus": 2, "lifetime_free": 3},
        "remaining": {"daily": 2, "monthly": 8, "lifetime_free": 0},
    },
    "premium": {
        "tier": "premium",
        "used": {"daily": 1, "monthly": 4, "lifetime": 5},
        "limits": {"daily": 10, "monthly": 72, "monthly_base": 70, "monthly_bonus": 2, "lifetime_free": 0},
        "remaining": {"daily": 9, "monthly": 68, "lifetime_free": 0},
    },
}


@pytest.mark.parametrize("tier", ["free", "premium"])
def test_p1_status_body_recorded(tier):
    """PIN P1e: the /usage/status base body for free / premium (key order too)."""
    out = us._usage_status_body({"subscription_tier": tier, "lifetime_comparisons_used": 5}, 2, 1, 4)
    assert _dumps(out) == _dumps(STATUS_LITERALS[tier]), out


@pytest.mark.parametrize("quota", [None, "true"], ids=["quota_off", "quota_on"])
@pytest.mark.parametrize("tier", ["tester", "free"], ids=["tester", "free_control"])
def test_p2_device_quota_never_takes_a_tester(monkeypatch, quota, tier):
    """PIN P2 (B1): with the full S81-09 config present (the flag ON or OFF, a
    synthetic fingerprint, the pepper, the allow-list naming another id), a
    tester never reaches the device EVAL: consume runs _atomic_consume_async
    and the status is the base get_usage_status body. The free control row
    proves the config is live (quota ON: one EVAL, no atomic consume)."""
    _b1_config(monkeypatch, quota=quota)
    uid = _uid()
    fp = _fp()
    d, m = _keys(uid)
    red = _install_redis(monkeypatch, {d: 1, m: 4})
    _tier(monkeypatch, tier, life=12, bonus=0)
    atomic = _atomic_spy(monkeypatch)
    device = _device_quota_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN, device_fp=fp))
    if tier == "free" and quota == "true":
        assert len(red.evals()) == 1 and device == [uid] and atomic == []
        assert out["consumed_keys"].get("device_daily"), out
        return
    assert red.evals() == [] and device == []
    assert len(atomic) == 1 and atomic[0][0] == uid, atomic
    assert out["tier"] == tier and out["allowed"] is True and "scope" not in out, out
    if tier != "tester":
        return
    red2 = _install_redis(monkeypatch, {d: 7, m: 40})
    _tier(monkeypatch, "tester", life=12, bonus=5)
    base = _run(us.get_usage_status(uid, TOKEN))
    if quota == "true":
        status = _run(us.get_device_usage_status(uid, TOKEN, device_fp=fp))
    else:
        status = base
    assert _dumps(status) == _dumps(base), (status, base)
    assert "counted_scope" not in status and "resets_at" not in status
    assert status["tier"] == "tester"
    assert red2.evals() == []
    assert not any(str(c[1]).startswith("usage:device:") for c in red2.calls), red2.calls


UNKNOWN_SPELLINGS = ["Tester", " tester ", "TESTER", "premium "]


@pytest.mark.parametrize("spelling", UNKNOWN_SPELLINGS, ids=["Title", "padded", "upper", "premium_pad"])
def test_p3_unknown_spellings_fall_to_free_limits(monkeypatch, spelling):
    """PIN P3: an inexact spelling is no key of TIER_LIMITS and hits the existing
    free fallback (daily 3, monthly 10; no lifetime-free bypass: the tier is not
    exactly 'free'), exactly as at base."""
    assert us.TIER_LIMITS.get(spelling) is None
    uid = _uid()
    d, m = _keys(uid)
    _install_redis(monkeypatch, {d: 1, m: 4})
    _tier(monkeypatch, spelling, life=0, bonus=0)
    calls = _atomic_spy(monkeypatch)
    out = _run(us.consume_comparison_credit(uid, TOKEN))
    assert calls == [(uid, 3, 10)], calls
    assert out == {
        "allowed": True, "reason": None, "tier": spelling, "consumed": True,
        "consumed_keys": {"daily": d, "monthly": m},
        "remaining": {"daily": 1, "monthly": 5, "lifetime_free": 0},
    }, out
    allowed = us._usage_allowed_body({"subscription_tier": spelling, "lifetime_comparisons_used": 0}, 0, 3, 4)
    assert allowed == {"allowed": False, "reason": "daily_limit", "tier": spelling,
                       "remaining": {"daily": 0, "monthly": 6, "lifetime_free": 0}}, allowed
    status = us._usage_status_body({"subscription_tier": spelling, "lifetime_comparisons_used": 0}, 0, 1, 4)
    assert _dumps(status) == _dumps({
        "tier": spelling,
        "used": {"daily": 1, "monthly": 4, "lifetime": 0},
        "limits": {"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, "lifetime_free": 3},
        "remaining": {"daily": 2, "monthly": 6, "lifetime_free": 0},
    }), status


class _Resp:
    def __init__(self, data):
        self.data = data


class _UsersQuery:
    def __init__(self, tier, log):
        self._tier = tier
        self._log = log

    def select(self, cols):
        self._log.append(("select", cols))
        return self

    def eq(self, col, value):
        self._log.append(("eq", col))
        return self

    def single(self):
        return self

    def execute(self):
        return _Resp({"subscription_tier": self._tier})


class _FakeAdmin:
    def __init__(self, tier):
        self.tier = tier
        self.log = []

    def table(self, name):
        self.log.append(("table", name))
        return _UsersQuery(self.tier, self.log)


class _PassAbuse:
    def evaluate_invite(self, invite, invitee):
        return {"passed": True}


@pytest.mark.parametrize("tier,grant", [("tester", 5), ("free", 5), ("premium", 10)])
def test_p4_referral_grant_for_tester_referrer_is_five(monkeypatch, tier, grant):
    """PIN P4a: try_trigger_loop2 grants a tester referrer 5 (as free; premium 10
    is the control). The referrer tier comes through the REAL
    _get_referrer_subscription_tier over a faked users read."""
    referrer, invitee = _uid(), _uid()
    admin = _FakeAdmin(tier)
    monkeypatch.setattr(rs, "get_admin_supabase_client", lambda: admin)
    monkeypatch.setattr(rs, "AbuseDetectionService", _PassAbuse)
    granted, pushed = [], []

    async def _invite(self, uid):
        return {"id": "inv-t1", "referrer_user_id": referrer, "redeemed_at": None}

    async def _one(self, uid):
        return 1

    async def _invitee(self, uid):
        return {"id": uid, "email": ""}

    async def _zero(self, uid):
        return 0

    async def _grant(self, invite, invitee_row, grant_amount=5):
        granted.append(grant_amount)

    async def _redeemed(self, invite_id, comparison_id):
        return None

    async def _push(self, referrer_id, invitee_row, grant_amount):
        pushed.append(grant_amount)

    S = rs.ReferralService
    monkeypatch.setattr(S, "_find_unredeemed_invite_for_invitee", _invite)
    monkeypatch.setattr(S, "_count_user_comparisons", _one)
    monkeypatch.setattr(S, "_load_invitee", _invitee)
    monkeypatch.setattr(S, "_referrer_device_lifetime_count", _zero)
    monkeypatch.setattr(S, "_grant_loop2_rewards", _grant)
    monkeypatch.setattr(S, "_update_invite_as_redeemed", _redeemed)
    monkeypatch.setattr(S, "_send_loop2_push", _push)
    _run(S().try_trigger_loop2(invitee, "cmp-t1-" + uuid.uuid4().hex[:6]))
    assert ("select", "subscription_tier") in admin.log
    assert granted == [grant] and pushed == [grant], (granted, pushed)


@pytest.mark.parametrize("tier,exempt", [("tester", False), ("free", False), ("premium", True)])
def test_p4_category_gate_budget_exempt_premium_only(monkeypatch, tier, exempt):
    """PIN P4b: category_gate's premium test is False for a tester (the refusal
    budget applies, as free); premium True is the control. The allow-list names
    another synthetic id."""
    monkeypatch.setenv(EXEMPT, _uid())
    _tier(monkeypatch, tier)
    assert _run(cg.budget_exempt_async(_uid())) is exempt


def test_p5_anonymous_consume_uses_free_caps(monkeypatch):
    """PIN P5: the anonymous gate debits with the free caps (3, 10) and reads no
    user row, whatever tier strings exist."""
    reads = []
    _tier(monkeypatch, "tester", reads=reads)
    fp = _fp()
    anon = "anon:" + fp
    d, m = _keys(anon)
    _install_redis(monkeypatch, {d: 2, m: 4})
    calls = _atomic_spy(monkeypatch)
    out = _run(us.check_anon_usage_allowed(fp))
    assert calls == [(anon, 3, 10)], calls
    assert reads == []
    assert out == {
        "allowed": True, "reason": None, "tier": "free", "consumed": True,
        "consumed_keys": {"daily": d, "monthly": m},
        "remaining": {"daily": 0, "monthly": 5, "lifetime_free": 0},
    }, out
    out2 = _run(us.check_anon_usage_allowed(fp))
    assert out2 == {
        "allowed": False, "reason": "daily_limit", "tier": "free", "consumed": False,
        "remaining": {"daily": 0, "monthly": 5, "lifetime_free": 0},
    }, out2

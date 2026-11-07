"""S81-G8 S81-11b RESULT-AGGREGATES (ENABLE_RESULT_AGGREGATES) -- RED and PIN rows.

Spec .qa-s80/S81-G8_UNIT_SPEC.md (unit S81-11b, section 5) as amended by RULINGS_S81_G8
(R-G8-4: the builder kwarg kb_views, the three call sites pass
kb_views=getattr(self, "_kb_views", None); R-G8-5: a card with zero servable offers ->
store_count 0 and price_checked_at null, no card -> every field null, compare_count null).
Base daf86d32.

Every RED row fails at base on an AssertionError only (the new symbols are read with getattr
and asserted; R4 / R7 assert the kb_views keyword in inspect.signature BEFORE any call
carrying it). Every PIN row is green at base and runs with the FULL companion configuration
(ENABLE_KB_FIRST_SERVE ON with both cards present, B1 ON, ENABLE_RESULT_GATE ON, both W4-13
states) plus raising recorders on the unit's helpers (installed getattr-safely), so a
not-gated mutant is killed.

The shared golden tests/fixtures/s81_g8_flag_off_golden.json is recorded at the base sha
only:  python -m tests.test_s81_s11b_result_aggregates <out.json>

Hermetic: app.main imported FIRST (the dotenv guard); the S81-18 harness reused from
tests/test_s81_s18_kb_first_serve.py; synthetic hosts store-a / store-b / store-c.example.com.
Pure ASCII, LF.
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__":  # pragma: no cover - the base recorder runs outside pytest
    import socket

    import dotenv
    import dotenv.main

    dotenv.load_dotenv = lambda *a, **k: False  # never read a developer .env
    dotenv.main.load_dotenv = lambda *a, **k: False
    for _name in ("REDIS_URL", "UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN",
                  "UPSTASH_REDIS_REST_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
                  "SUPABASE_ANON_KEY", "SENTRY_DSN"):
        os.environ.pop(_name, None)
    _LOCAL = ("127.0.0.1", "::1", "localhost", "", None)
    _real_gai = socket.getaddrinfo

    def _gai(host, *args, **kwargs):
        if host not in _LOCAL:
            raise OSError("g8 recorder: network blocked")
        return _real_gai(host, *args, **kwargs)

    socket.getaddrinfo = _gai

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import asyncio  # noqa: E402
import copy  # noqa: E402
import importlib  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
from datetime import timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

import app.main  # noqa: E402,F401  FIRST: the dotenv guard
from app.services import kb_serve  # noqa: E402
from app.services import response_builder as rb  # noqa: E402
import app.services.structured_comparison_service as scs  # noqa: E402
from tests import test_s81_s18_kb_first_serve as s18  # noqa: E402

FLAG = "ENABLE_RESULT_AGGREGATES"
LABEL_FLAG = "ENABLE_STORE_LABEL"
B1 = "ENABLE_RESULT_STATUS_METADATA"
GATE = "ENABLE_RESULT_GATE"
TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "s81_g8_flag_off_golden.json"
HOST_C = "store-c.example.com"
OFF_SPELLINGS = s18.OFF_SPELLINGS
TRUTH_STATES = (None, "true")
CLEARED = tuple(sorted(set(s18.CLEARED_ENV + (FLAG, LABEL_FLAG, B1, GATE, TRUTH,
                                              "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
                                              "ENABLE_EXACT_PRICE_GATE"))))
NOW = s18.NOW
NULLS = {"compare_count": None, "store_count": None, "price_checked_at": None}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEARED:
        monkeypatch.delenv(name, raising=False)
    seen = getattr(kb_serve, "_SEEN", None)
    if hasattr(seen, "clear"):
        seen.clear()
    yield
    if hasattr(seen, "clear"):
        seen.clear()


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _fn(name):
    f = getattr(kb_serve, name, None)
    assert callable(f), "kb_serve.%s is missing (S81-11b not implemented)" % name
    return f


def _need_kwarg(name):
    params = inspect.signature(rb.build_comparison_response).parameters
    assert name in params, "build_comparison_response has no %s keyword (not implemented)" % name


def _card3():
    pid = s18._pid(s18.P0)
    url_b = "https://" + s18.HOST_B + "/products/nimbus-noir"
    return s18._card(s18.P0, offers=[
        s18._offer(pid, s18.PDP_A, s18.HOST_A, days=2),
        s18._offer(pid, s18.PDP_A50, s18.HOST_A, days=4, ml=50),
        s18._offer(pid, url_b, s18.HOST_B, days=1),
    ])


def _view3():
    return s18._classify(_card3())


def _agg(store_count, days):
    return {"compare_count": None, "store_count": store_count,
            "price_checked_at": s18._z(NOW - timedelta(days=days))}


def _product_data():
    body = s18.json.loads((ROOT / "tests" / "fixtures" / "lane1" / "tomford_vs_creed_response.json")
                          .read_text(encoding="utf-8"))
    pd = copy.deepcopy(body["products"])
    for p in pd:
        p.setdefault("full_name", (p.get("brand", "") + " " + p.get("name", "")).strip())
    return pd


def _build(product_data=None, **extra):
    params = inspect.signature(rb.build_comparison_response).parameters
    pd = product_data if product_data is not None else _product_data()
    values = {"product_data": pd, "products": pd,
              "comparison": {"winner_index": 0, "winner_declaration": "x", "winner_reason": "y",
                             "verdict": "v", "pros": {}, "cons": {}},
              "query": "Acme vs Zephyra", "region": "bahrain", "total_cost": 0.01, "api_calls": 3}
    kwargs = {n: values[n] for n in params if n in values}
    kwargs.update(extra)
    return rb.build_comparison_response(**kwargs)


class _Boom(list):
    """A kb_views object whose every access raises."""

    def _raise(self, *a, **k):
        raise RuntimeError("g8 probe: kb_views touched")

    __iter__ = _raise
    __getitem__ = _raise
    __len__ = _raise
    __bool__ = _raise
    __eq__ = _raise
    __contains__ = _raise


# ---------------------------------------------------------------- the faked compare (S18 driver)

def _on(mp, cards):
    s18._full_config(mp, flag="true")
    client = s18._CardClient(cards)
    s18._install_kb(mp, client)
    return client


def _rest(mp, **kw):
    return asyncio.run(s18._compare(mp, "rest", **kw))


def _stream_complete(mp, **kw):
    return s18._complete(asyncio.run(s18._compare(mp, "stream", **kw)))


# ---------------------------------------------------------------- the shared golden (11b P1 + 18b P1)

SCENARIOS = {
    "rest_full": ("rest", {}),
    "stream_full": ("stream", {}),
    "camera_full": ("rest", {"vision": s18.VISION}),
    "rest_ar": ("rest", {"output_lang": "ar"}),
}


def _full_g8_config(mp, truth):
    s18._full_config(mp, flag="true")
    mp.setenv(B1, "true")
    mp.setenv(GATE, "true")
    _set(mp, TRUTH, truth)
    client = s18._CardClient({s18._pid(s18.P0): s18._card(s18.P0), s18._pid(s18.P1): s18._card_b()})
    s18._install_kb(mp, client)
    return client


def _raising_g8_recorders(mp, fired):
    """Every G8 entry point a flag-OFF compare must never reach (getattr-safe: no-ops at base)."""
    def _boom(name):
        def _f(*a, **k):
            fired.append(name)
            raise AssertionError("G8 OFF: %s called" % name)
        return _f
    mp.setattr(kb_serve, "result_aggregates", _boom("result_aggregates"), raising=False)
    if importlib.util.find_spec("app.services.store_labels") is not None:
        sl = importlib.import_module("app.services.store_labels")
        for name in ("label_prices", "label_for", "load_labels"):
            mp.setattr(sl, name, _boom(name), raising=False)


def _g8_snapshot(mp, truth):
    _full_g8_config(mp, truth)
    out = {}
    for name, (kind, kw) in SCENARIOS.items():
        state = {}
        payload = asyncio.run(s18._compare(mp, kind, state=state, **copy.deepcopy(kw)))
        out[name] = s18._normalize({"payload": payload,
                                    "calls": {k: len(v) for k, v in state["calls"].items()}})
    return json.loads(json.dumps(out))


def _golden():
    assert GOLDEN.exists(), "the G8 golden is missing: " + str(GOLDEN)
    return json.loads(GOLDEN.read_text(encoding="ascii"))


def _truth_key(truth):
    return "truth_unset" if truth is None else "truth_" + truth


# =============================================================== RED rows

def test_r1_flag_reader_house_boolean(monkeypatch):
    reader = _fn("result_aggregates_enabled")
    for value in (None, "", "false", "0", "garbage", " OFF "):
        _set(monkeypatch, FLAG, value)
        assert reader() is False, value
    for value in (" TRUE ", "1", "yes", "On"):
        monkeypatch.setenv(FLAG, value)
        assert reader() is True, value


def test_r2_helper_hosts_and_newest():
    helper = _fn("result_aggregates")
    got = helper([_view3(), None])
    assert got == [_agg(2, 1), dict(NULLS)], got
    assert [list(e) for e in got] == [["compare_count", "store_count", "price_checked_at"]] * 2


def test_r3_helper_nulls_and_zero():
    helper = _fn("result_aggregates")
    for views in (None, [], [s18._classify(None)], [s18._classify(None), s18._classify(None)], "junk"):
        assert helper(views) == [dict(NULLS), dict(NULLS)], views
    pid = s18._pid(s18.P0)
    oos = s18._classify(s18._card(s18.P0, offers=[s18._offer(pid, s18.PDP_A, s18.HOST_A, in_stock=False)]))
    assert oos["hit"] == "partial" and oos["candidates"] == [], oos["hit"]
    got = helper([oos, _view3()])
    assert got == [{"compare_count": None, "store_count": 0, "price_checked_at": None}, _agg(2, 1)], got


def test_r4_builder_stamps_under_the_flag(monkeypatch):
    _need_kwarg("kb_views")
    monkeypatch.setenv(FLAG, "true")
    out = _build(kb_views=[_view3(), None])
    assert (out.get("metadata") or {}).get("aggregates") == [_agg(2, 1), dict(NULLS)], out.get("metadata")
    for value in OFF_SPELLINGS:
        _set(monkeypatch, FLAG, value)
        out = _build(kb_views=[_view3(), None])
        assert "aggregates" not in (out.get("metadata") or {}), value


def test_r5_orchestrator_rest_and_stream(monkeypatch):
    cards = {s18._pid(s18.P0): _card3(), s18._pid(s18.P1): s18._card_b()}
    _on(monkeypatch, cards)
    monkeypatch.setenv(FLAG, "true")
    want = [_agg(2, 1), _agg(1, 2)]
    rest = _rest(monkeypatch)
    assert rest.get("success") is True, str(rest)[:300]
    assert (rest.get("metadata") or {}).get("aggregates") == want, (rest.get("metadata") or {}).get("aggregates")
    complete = _stream_complete(monkeypatch)
    assert (complete.get("metadata") or {}).get("aggregates") == want, \
        (complete.get("metadata") or {}).get("aggregates")


def _partial_svc():
    svc = scs.StructuredComparisonService()
    svc._partial_build_ctx = {"query": "Acme vs Zephyra", "region": "bahrain", "from_cache": False,
                              "user_preferences": None, "category_used": "fragrances",
                              "category_switched": False, "original_category": None}
    svc._partial_product_data = _product_data()
    svc._partial_scoring_result = None
    svc._partial_product_names = None
    svc._partial_comparison = None
    return svc


def test_r6_partial_builder_carries_it(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    svc = _partial_svc()
    svc._kb_views = [_view3(), None]
    out = svc._build_partial_response(elapsed_seconds=1.0)
    agg = (out.get("metadata") or {}).get("aggregates")
    assert isinstance(agg, list) and len(agg) == 2, agg
    assert agg[0]["store_count"] == 2 and agg[1] == NULLS, agg


def test_r7_flag_read_first(monkeypatch, caplog):
    _need_kwarg("kb_views")
    caplog.set_level(logging.WARNING)
    for value in OFF_SPELLINGS:
        _set(monkeypatch, FLAG, value)
        out = _build(kb_views=_Boom())
        assert "aggregates" not in (out.get("metadata") or {}), value
    assert [r for r in caplog.records if "RESULT_AGGREGATES" in r.getMessage()] == []
    monkeypatch.setenv(FLAG, "true")
    real = kb_serve.result_aggregates if hasattr(kb_serve, "result_aggregates") else None
    assert real is not None, "kb_serve.result_aggregates is missing"

    def _raises(views):
        raise ValueError("g8 probe")
    monkeypatch.setattr(kb_serve, "result_aggregates", _raises)
    out = _build(kb_views=[_view3(), None])
    assert "aggregates" not in (out.get("metadata") or {})
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[RESULT_AGGREGATES]")]
    assert lines == ["[RESULT_AGGREGATES] stamp skipped: ValueError"], lines


# =============================================================== PIN rows

def test_p1_flag_off_golden_full_config(monkeypatch):
    want = _golden()["scenarios"]
    for truth in TRUTH_STATES:
        for value in OFF_SPELLINGS:
            _set(monkeypatch, FLAG, value)
            _set(monkeypatch, LABEL_FLAG, value)
            fired = []
            _raising_g8_recorders(monkeypatch, fired)
            got = _g8_snapshot(monkeypatch, truth)
            exp = want[_truth_key(truth)]
            moved = sorted(n for n in SCENARIOS if got.get(n) != exp.get(n))
            assert moved == [], (truth, value, moved)
            text = json.dumps(got)
            assert '"aggregates"' not in text and '"store_label"' not in text
            assert fired == [], fired


def test_p2_kb_off_bodies_unchanged(monkeypatch):
    for value in OFF_SPELLINGS:
        s18._full_config(monkeypatch, flag=None, log_flag=None)
        _set(monkeypatch, FLAG, value)
        fired = []
        s18._raising_recorders(monkeypatch, fired)
        _raising_g8_recorders(monkeypatch, fired)
        got = json.loads(json.dumps(s18._golden_snapshot(monkeypatch)))
        want = s18._golden()["scenarios"]
        assert sorted(n for n in s18.SCENARIOS if got.get(n) != want.get(n)) == [], value
        assert fired == [], fired


def test_p3_classify_shapes_untouched():
    out = _view3()
    keys = {"amount", "currency", "retailer", "url", "source_method", "estimated", "title", "size",
            "as_of", "_cached", "_cache_source", "in_stock"}
    assert set(out["price"]) == keys, sorted(out["price"])
    assert len(out["candidates"]) == 3 and all(set(c) == keys for c in out["candidates"])
    assert [c["retailer"] for c in out["candidates"]] == [s18.HOST_B, s18.HOST_A, s18.HOST_A]


if __name__ == "__main__":  # pragma: no cover - the recorder (run at the base sha only)
    _snap = {}
    for _truth in TRUTH_STATES:
        _p = s18._Patcher()
        try:
            for _n in CLEARED:
                os.environ.pop(_n, None)
            _fired = []
            _raising_g8_recorders(_p, _fired)
            _snap[_truth_key(_truth)] = _g8_snapshot(_p, _truth)
            assert _fired == [], _fired
        finally:
            _p.undo()
    import subprocess

    _sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          cwd=str(ROOT)).stdout.strip()
    with open(sys.argv[1], "w", encoding="ascii", newline="\n") as _fh:
        json.dump({"base": _sha, "scenarios": _snap}, _fh, indent=1, sort_keys=True, ensure_ascii=True)
        _fh.write("\n")
    print("wrote", sys.argv[1], sorted(_snap))

"""INC-P2 PRICE-NOT-LOST fix round 1 (S96-FIX incident lane): the rows of FIX1_RULINGS_INC_P2.md
F1-F7, appended in a NEW file so the frozen pair (tests/test_inc_p2_price_not_lost.py and
tests/test_inc_p2_seam.py) stays byte-identical. The helpers, fixtures and the production
configuration are the frozen files' own (imported, never copied).

- F1 (corr MAJOR-1 = eng MAJ-2): no `_p2*` key and no hidden listing url on any wire copy on
  a wire fault (p2_wire_price raising) or a flag flip between the reconcile and the build:
  the overview, the legacy `products` alias, the stream complete and prices events and the
  body the GET route hands the History persist.
- F2 (corr MAJOR-2): flag OFF (and ON) an L1 hit with a truthy non-str variant returns the
  cached price exactly as at the base (5cd93c6a).
- F3 (corr MAJOR-3): the P2-7 write stores a re-selected price only (a) at the side's own
  typed size under a key text carrying it, or (b) at exactly 100 ml for an untyped side.
- F4 (eng MAJ-1): the saved-history savings readers skip a stored body whose
  metadata.pair_price_sizes.mode is present and not same_size (unflagged reader).
- F6: killing rows for the survivors X01, X04 = E09, X05, E06, E12.
- F7 (corr m4 / m5): PRICE_OUTCOME reads the miss notes under the key they are written under;
  a floor pend logs reconcile=floor.

RED rows fail at the rebased HEAD 0c66ca4e on an AssertionError only; PIN rows are green
there. Hermetic (the frozen files' fakes; hosts *.example.com). Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import contextvars
import copy
import json
import logging
import re

import pytest

from tests import test_inc_p2_price_not_lost as R  # noqa: E402  (imports app.main first)
from tests import test_inc_p2_seam as S  # noqa: E402
from app.api import home_routes as hr  # noqa: E402
from app.api import profile_routes as pfr  # noqa: E402
from app.api import text_routes  # noqa: E402
from app.services import price_service as ps  # noqa: E402
import app.services.structured_comparison_service as scs  # noqa: E402

client, authed, svc_factory = S.client, S.authed, S.svc_factory

FLAG, FIX, FRAG = R.FLAG, R.FIX, R.FRAG


def _apply(mp, on, off):
    for name in on:
        mp.setenv(name, "true")
    for name in off:
        mp.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """The frozen seam file's production configuration (its fakes answer the role calls);
    a pure row calls pure_env() to apply the frozen pure file's instead (the two Claude
    role flags ON, as on web)."""
    _apply(monkeypatch, S.PROD_ON, S.PROD_OFF)
    for name in (FLAG, FIX, R.RES):
        monkeypatch.delenv(name, raising=False)
    for name in list(__import__("os").environ):
        if name.startswith("PRODUCT_RESOLVER_"):
            monkeypatch.delenv(name, raising=False)
    scs._DEBUG_STAGE_TIMINGS = None
    yield
    scs._DEBUG_STAGE_TIMINGS = None


def pure_env(mp):
    _apply(mp, R.PROD_ON, R.PROD_OFF)
    mp.setenv("ANTHROPIC_API_KEY", "syn" + "thetic-" + "p2")


def psetflags(mp, **kw):
    pure_env(mp)
    R.setflags(mp, **kw)


_ORIG_INSTALL = S.install
CAPCELLS = R.CAPCELLS
FIXCELLS = R.FIXCELLS
DIOR_URL = R.DIOR_P["url"]


def _raise(*_a, **_k):
    raise RuntimeError("wire down")


def _json(obj):
    return json.dumps(obj, sort_keys=True, default=str)


def _no_private(obj, hidden_url=None):
    keys = R.underscore_or_p2(obj, [])
    assert keys == [], keys
    if hidden_url:
        assert hidden_url not in _json(obj), "the hidden listing url reached the wire"


def _fields(caplog):
    return [R.fields(r.getMessage()) for r in caplog.records if r.getMessage().startswith("PRICE_OUTCOME")]


# --------------------------------------------------------------------------- F1 the private keys
@pytest.mark.parametrize("cap", CAPCELLS)
def test_f1a_wire_fault_body_and_alias(monkeypatch, cap):
    """F1a RED (B18 class, extended): flag ON, p2_wire_price raising: the overview and the
    legacy alias carry no _p2 key and not the hidden Dior listing url, in both cells."""
    psetflags(monkeypatch, flag="true", fix="true")
    monkeypatch.setattr(ps, "p2_wire_price", _raise)
    body, snap = R.run_pair(R.prod("Ted Baker M 30ml", R.TED_P), R.prod("Dior Sauvage 100 ML Edp", R.DIOR_P),
                            R.TED_Q, cap=cap)
    assert isinstance(snap[1].get("_p2_shown_price"), dict), "precondition: Dior carries the stash"
    assert R.pending(R.ov(body)[1], "size_mismatch"), R.ov(body)[1]
    _no_private(body, DIOR_URL)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_f1b_flag_flip_between_reconcile_and_build(monkeypatch, cap):
    """F1b RED: the flag ON at the reconcile and OFF at the build (a flip mid-request):
    the body carries no _p2 key and not the hidden Dior listing url."""
    psetflags(monkeypatch, flag="true", fix="true")
    pd = [R.prod("Ted Baker M 30ml", R.TED_P), R.prod("Dior Sauvage 100 ML Edp", R.DIOR_P)]

    def _go():
        ps.reconcile_pair_fairness(pd, R.TED_Q, FRAG, candidates_by_name={})
        assert isinstance(pd[1].get("_p2_shown_price"), dict), "precondition: Dior carries the stash"
        monkeypatch.delenv(FLAG, raising=False)
        return R.build(pd, R.TED_Q)
    body = R.in_ctx(_go, cap)
    _no_private(body, DIOR_URL)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_f1c_wire_fault_stream_events(monkeypatch, cap):
    """F1c RED: the stream with p2_wire_price raising: no event (complete, prices or any
    other) carries a _p2 key or the hidden Dior listing url, in both cells."""
    S.has_cap_kwarg()
    R.setflags(monkeypatch, flag="true", fix="true")
    monkeypatch.setattr(ps, "p2_wire_price", _raise)
    events, _, _ = S.run("stream", S.TED_DIOR, cap=cap)
    S.complete(events)
    S.event(events, "prices")
    _no_private(events, DIOR_URL)


def _capture_history(monkeypatch):
    saved = []

    async def _noop():
        return "inc-p2-fix1-row-id"

    def _save(**kw):
        saved.append(copy.deepcopy(kw.get("full_response")))
        return _noop()
    monkeypatch.setattr(text_routes, "_persist_comparison_bounded", _save)
    monkeypatch.setattr(text_routes, "save_comparison_and_track_cohort", _save)
    return saved


@pytest.mark.parametrize("header", [None, "price_size"], ids=["cap0", "cap1"])
def test_f1d_wire_fault_history_body(monkeypatch, client, authed, svc_factory, header):
    """F1d RED: GET /api/v1/text/compare (the phone's route) with p2_wire_price raising:
    the response and the body handed to the History persist carry no _p2 key and not the
    hidden Dior listing url."""
    R.setflags(monkeypatch, flag="true", fix="true")
    S.route_env(monkeypatch)
    saved = _capture_history(monkeypatch)
    monkeypatch.setattr(ps, "p2_wire_price", _raise)
    h = {} if header is None else {"X-Client-Capabilities": header}
    resp = client.get("/api/v1/text/compare", params={"product_a": S.TED_DIOR[0], "product_b": S.TED_DIOR[1]},
                      headers=h)
    assert resp.status_code == 200, resp.text[:300]
    assert saved, "the History persist was not reached"
    _no_private(resp.json(), DIOR_URL)
    _no_private(saved[0], DIOR_URL)


@pytest.mark.parametrize("fx", sorted(R.WALK))
def test_f1e_walk_wire_fault_never_leaks(monkeypatch, fx):
    """F1e RED (walk): every pair fixture of the frozen file, flag ON, cap0 and cap1, with
    p2_wire_price raising: no _p2 key anywhere in the body."""
    psetflags(monkeypatch, flag="true", fix="true")
    monkeypatch.setattr(ps, "p2_wire_price", _raise)
    for cap in (False, True):
        a, b, q, c = R.WALK[fx]()
        body, _ = R.run_pair(a, b, q, c, cap=cap)
        stash = [p for p in (a, b) if isinstance(p.get("_p2_shown_price"), dict)]
        hidden = stash[0]["_p2_shown_price"].get("url") if stash else None
        _no_private(body)
        if hidden and not any(isinstance(v, dict) and v.get("url") == hidden for v in R.ov(body)):
            assert hidden not in _json(body), (fx, cap)


def test_f1f_flag_off_alias_is_product_data_pin(monkeypatch):
    """F1f PIN: flag OFF the legacy alias is product_data itself (no copy), as at the base."""
    psetflags(monkeypatch, flag=None, fix="true")
    pd = [R.prod("Sauvage EDP", R.SAUV_100), R.prod("Bleu de Chanel EDP", R.BLEU_100)]
    body = R.in_ctx(lambda: R.build(pd))
    assert body["products"] is pd


# --------------------------------------------------------------------------- F2 unflagged evaluation
CACHED_5 = {"amount": 50.0, "currency": "BHD", "source_method": "local_bhd", "title": "Dior Sauvage EDP 100ml",
            "url": "https://store-a.example.com/p/sv", "estimated": False}


@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
def test_f2_l1_hit_with_a_non_str_variant(monkeypatch, flag):
    """F2 PIN at the base 5cd93c6a (RED at 0c66ca4e): an L1 hit for a truthy non-str
    variant (W4-7's malformed-identity class, test_w4_7 c10) returns the cached price
    exactly as at the base; the unflagged trace line never raises out of _get_price."""
    psetflags(monkeypatch, flag=flag)
    p = S.fy._Patcher()
    try:
        p.setattr(scs, "get_cached", lambda k: copy.deepcopy(CACHED_5))
        svc = scs.StructuredComparisonService()
        try:
            got = asyncio.run(svc._get_price("Dior", "Sauvage", 5, "bahrain", "Dior Sauvage",
                                             nocache=False, category=FRAG))
            err = None
        except Exception as exc:  # noqa: BLE001 - the row asserts there is none
            got, err = None, exc
    finally:
        p.undo()
    assert err is None, repr(err)
    assert got == dict(CACHED_5, _cached=True), got


def test_f2b_trace_before_list_outside_the_guard(monkeypatch):
    """F2b RED (audit): flag OFF, reconcile_pair_fairness on a non-sliceable fragrance
    product list behaves as at the base (no new raise from the unflagged trace note)."""
    psetflags(monkeypatch, flag=None, fix="true")

    class _NoSlice(list):
        def __getitem__(self, item):
            if isinstance(item, slice):
                raise TypeError("no slicing")
            return list.__getitem__(self, item)
    pd = _NoSlice([R.prod("Sauvage EDP", R.SAUV_100), R.prod("Bleu de Chanel EDP", R.BLEU_100)])
    try:
        out = ps.reconcile_pair_fairness(pd, "Sauvage EDP vs Bleu de Chanel EDP", FRAG, candidates_by_name={})
        err = None
    except Exception as exc:  # noqa: BLE001
        out, err = None, exc
    assert err is None, repr(err)
    assert out is False


# --------------------------------------------------------------------------- F3 the P2-7 write
SV30 = R.P(30.0, "Sauvage EDP 30ml", "store-c", "p/sv-30")
DIOR_C100 = R.P(61.0, "Dior Sauvage EDP 100ml", "store-c", "p/sv-100", sm="shopify_json")
MIXED = ("Ted Baker M 30ml", "Sauvage EDP")
DIOR_BLEU = ("Dior Sauvage 100 ML Edp", "Bleu de Chanel EDP")
# One consistent world: each product name has ONE live price and ONE candidate list (Dior's
# live listing is at its typed 100 ml here; F3d drives the own-typed-size re-selection).
WORLD_PRICES = {"Ted Baker M 30ml": S.TED_P, "Dior Sauvage 100 ML Edp": S.DIOR_P, "Sauvage EDP": S.SAUV_100,
                "Bleu de Chanel EDP": S.BLEU_150, "YSL Libre EDP": S.YSL_P,
                "Lancome La Vie Est Belle EDP": S.LVEB_P}
WORLD_CANDS = {"Sauvage EDP": [SV30], "Bleu de Chanel EDP": [S.BLEU_100]}
WORLD_PAIRS = {"ted_dior": S.TED_DIOR, "ysl_lveb": S.YSL_LVEB, "sauv_bleu": S.SAUV_BLEU, "mixed": MIXED,
               "dior_bleu": DIOR_BLEU}


def _key(call):
    return ps.build_size_aware_price_cache_key(call["brand"], call["name"], call["variant"], call["region"],
                                               call["search_query"], category=call["category"])


def _cached_install(monkeypatch, cache):
    """S.install, then _get_price reads `cache` first (an L1 hit returns no candidates,
    as the real _get_price); every write lands in the recorder and, when `cache` is the
    shared store, in it."""
    orig = _ORIG_INSTALL

    def inst(p, svc, state, rec, **kw):
        orig(p, svc, state, rec, **kw)
        inner = svc._get_price

        async def _gp(brand, name, variant, region, search_query, nocache=False, category="other"):
            key = ps.build_size_aware_price_cache_key(brand, name, variant, region, search_query, category=category)
            hit = cache.get(key) if cache is not None else None
            if hit is not None:
                rec.price_calls.append({"brand": brand, "name": name, "variant": variant, "region": region,
                                        "search_query": search_query, "category": category, "typed": None})
                return dict(copy.deepcopy(hit), _cached=True)
            return await inner(brand, name, variant, region, search_query, nocache, category)
        svc._get_price = _gp
        if cache is not None:
            p.setattr(scs, "set_cached", lambda key, value, ttl: (rec.sets.append((key, copy.deepcopy(value), ttl)),
                                                                   cache.__setitem__(key, copy.deepcopy(value)))
                      and True)
    monkeypatch.setattr(S, "install", inst)


def _shown_state(payload, kind="rest"):
    body = S.complete(payload) if kind == "stream" else payload
    return _json({"ov": S.ov(body), "legacy": [p.get("price") for p in body["products"]],
                  "marker": (body.get("metadata") or {}).get("pair_price_sizes")})


def _allowed_gain(base_state, after_state):
    """True when the only change is that base-pending sides are now shown, each at a 100 ml
    listing (the basis a bare key means: an allowed entry, or the side's own live 100 ml
    listing that the entry made comparable); every base-shown side is kept byte-identical."""
    b, a = json.loads(base_state), json.loads(after_state)
    for i in range(2):
        if R.shown(b["ov"][i]):
            if b["ov"][i] != a["ov"][i] or b["legacy"][i] != a["legacy"][i]:
                return False
        elif a["ov"][i] != b["ov"][i]:
            if not (R.shown(a["ov"][i]) and R._one_strict_ml(a["ov"][i].get("title")) == 100):
                return False
    return True


@pytest.mark.parametrize("cap", CAPCELLS)
def test_f3a_partner_size_never_written_under_a_bare_key(monkeypatch, cap):
    """F3a RED: 'Ted Baker M 30ml' vs 'Sauvage EDP' (Sauvage live 100 ml, a 30 ml
    candidate): the untyped Sauvage is re-selected to the partner's typed 30 ml, and
    NOTHING is written under Sauvage's key (a size nobody typed for it)."""
    S.has_cap_kwarg()
    R.setflags(monkeypatch, flag="true", fix="true")
    body, rec, _ = S.run("rest", MIXED, cap=cap, prices=WORLD_PRICES, cands=WORLD_CANDS)
    assert S.ov(body)[1].get("amount") == 30.0, S.ov(body)[1]
    call = [c for c in rec.price_calls if c["typed"] == "Sauvage EDP"][0]
    assert [w for w in rec.sets if w[0] == _key(call)] == [], [(w[0], w[1].get("title")) for w in rec.sets]


@pytest.mark.parametrize("cell", ["off", "cap0", "cap1"])
def test_f3b_next_request_after_the_mixed_pair(monkeypatch, cell):
    """F3b RED: after run 1 ('Ted Baker M 30ml' vs 'Sauvage EDP', flag ON), the next
    'Sauvage EDP' vs 'Bleu de Chanel EDP' reading the same cache shows exactly its
    no-prior-write state: flag OFF (the state after a rollback) and flag ON, both cells."""
    S.has_cap_kwarg()
    cap = cell == "cap1"
    R.setflags(monkeypatch, flag=None if cell == "off" else "true", fix="true")
    _cached_install(monkeypatch, {})
    clean, _, _ = S.run("rest", S.SAUV_BLEU, cap=cap, prices=WORLD_PRICES, cands=WORLD_CANDS)
    cache = {}
    _cached_install(monkeypatch, cache)
    R.setflags(monkeypatch, flag="true", fix="true")
    S.run("rest", MIXED, cap=False, prices=WORLD_PRICES, cands=WORLD_CANDS)
    R.setflags(monkeypatch, flag=None if cell == "off" else "true", fix="true")
    snapshot = {k: v.get("title") for k, v in cache.items()}
    cache_run2 = dict(cache)
    _cached_install(monkeypatch, cache_run2)
    after, _, _ = S.run("rest", S.SAUV_BLEU, cap=cap, prices=WORLD_PRICES, cands=WORLD_CANDS)
    assert _shown_state(after) == _shown_state(clean), (cell, snapshot)


@pytest.mark.parametrize("fix", FIXCELLS)
def test_f3c_cross_pair_walk_then_flag_off(monkeypatch, fix):
    """F3c RED (walk; RED in the fix1 cell, a PIN in fix0 where flag OFF pends both sides of
    Sauvage / Bleu with or without HEAD's 30 ml entry): every fixture pair with the flag ON
    (cap0 then cap1, one shared cache), then every pair again with the flag OFF reading
    that cache: each flag-OFF shown state equals its no-prior-write base state, with ONE
    measured exception: a side the base pends may be shown from an entry F3 allows (an
    untyped side's 100 ml, a typed side's own size), never a shown side lost or changed."""
    S.has_cap_kwarg()
    base = {}
    for name, pair in sorted(WORLD_PAIRS.items()):
        R.setflags(monkeypatch, flag=None, fix=fix)
        _cached_install(monkeypatch, {})
        payload, _, _ = S.run("rest", pair, prices=WORLD_PRICES, cands=WORLD_CANDS)
        base[name] = _shown_state(payload)
    cache = {}
    _cached_install(monkeypatch, cache)
    R.setflags(monkeypatch, flag="true", fix=fix)
    for cap in (False, True):
        for name, pair in sorted(WORLD_PAIRS.items()):
            S.run("rest", pair, cap=cap, prices=WORLD_PRICES, cands=WORLD_CANDS)
    written = sorted((k, v.get("title")) for k, v in cache.items())
    R.setflags(monkeypatch, flag=None, fix=fix)
    frozen = dict(cache)
    bad = {}
    for name, pair in sorted(WORLD_PAIRS.items()):
        _cached_install(monkeypatch, dict(frozen))
        payload, _, _ = S.run("rest", pair, prices=WORLD_PRICES, cands=WORLD_CANDS)
        if _shown_state(payload) != base[name] and not _allowed_gain(base[name], _shown_state(payload)):
            bad[name] = _shown_state(payload)
    assert bad == {}, (sorted(bad), written)


@pytest.mark.parametrize("res", R.RESCELLS)
def test_f3d_own_typed_size_and_100_are_written(monkeypatch, res):
    """F3d PIN (the two writes F3 keeps): 'Dior Sauvage 100 ML Edp' (live 50 ml, a 100 ml
    candidate) vs 'Bleu de Chanel EDP' (live 150 ml, a 100 ml candidate): Dior's own typed
    100 ml (its key text carries 100) and Bleu's 100 ml (untyped, the bare-key basis) are
    both written, resolver OFF and ON."""
    S.has_cap_kwarg()
    R.setflags(monkeypatch, flag="true", fix="true", res="true" if res else None)
    prices = {"Dior Sauvage 100 ML Edp": R.DIOR_50, "Bleu de Chanel EDP": S.BLEU_150}
    cands = {"Dior Sauvage 100 ML Edp": [DIOR_C100], "Bleu de Chanel EDP": [S.BLEU_100]}
    body, rec, _ = S.run("rest", DIOR_BLEU, prices=prices, cands=cands, res=res)
    w = S.ov(body)
    assert w[0].get("amount") == 61.0 and w[1].get("amount") == 91.78, w
    by_key = {k: v for k, v, _t in rec.sets}
    for typed, amount in (("Dior Sauvage 100 ML Edp", 61.0), ("Bleu de Chanel EDP", 91.78)):
        calls = [c for c in rec.price_calls if c["typed"] == typed or (
            res and c["search_query"] == S.RESOLVED[typed][3])]
        assert calls, typed
        assert (by_key.get(_key(calls[0])) or {}).get("amount") == amount, (typed, sorted(by_key))


def test_f3f_typed_size_must_be_in_the_key_text(monkeypatch, caplog):
    """F3f RED (rule (a), third clause): a typed side (its full_name carries 100 ml) whose
    Step-1 brand / name / variant (the text the cache key is built from) carries no size is
    NOT written, and PRICE_CACHE_SKIP says reason=size_basis; the same side with the size
    in the key text is written."""
    R.setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)
    fn = S.need("_p2_cache_reselected", scs.StructuredComparisonService)
    sets = []

    async def _set(key, value, ttl):
        sets.append((key, value, ttl))

    async def _get_none(_k):
        return None
    monkeypatch.setattr(scs, "_cache_set_async", _set)
    monkeypatch.setattr(scs, "_cache_get_async", _get_none)
    for key_name, written in (("Bleu de Chanel EDP", False), ("Bleu de Chanel EDP 100ml", True)):
        sets.clear()
        svc = scs.StructuredComparisonService()
        svc._save_price_to_db = lambda *a, **k: None
        products = [{"brand": "", "name": "Sauvage EDP", "variant": None, "category": FRAG,
                     "search_query": "Sauvage EDP"},
                    {"brand": "", "name": key_name, "variant": None, "category": FRAG, "search_query": key_name}]
        pd = [{"full_name": "Sauvage EDP", "name": "Sauvage EDP", "price": dict(S.SAUV_100)},
              {"full_name": "Bleu de Chanel EDP 100ml", "name": key_name, "price": dict(S.BLEU_100),
               "_p2_reselected": True}]
        asyncio.run(fn(svc, products, pd, "bahrain"))
        assert bool(sets) is written, (key_name, [s[0] for s in sets])
    assert any("PRICE_CACHE_SKIP reason=size_basis" in r.getMessage() for r in caplog.records)


def test_f3e_common_size_other_than_100_not_written(monkeypatch):
    """F3e RED: two untyped sides re-selected to a common 50 ml (no 100 ml reachable): no
    write under either bare key (only a 100 ml entry means what a bare key means)."""
    S.has_cap_kwarg()
    R.setflags(monkeypatch, flag="true", fix="true")
    prices = {"Sauvage EDP": R.P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75"),
              "Bleu de Chanel EDP": R.P(95.0, "Bleu de Chanel EDP 125ml", "store-a", "p/bl-125")}
    cands = {"Sauvage EDP": [R.P(45.0, "Sauvage EDP 50ml", "store-b", "p/sv-50")],
             "Bleu de Chanel EDP": [R.P(55.0, "Bleu de Chanel EDP 50ml", "store-b", "p/bl-50")]}
    body, rec, _ = S.run("rest", S.SAUV_BLEU, prices=prices, cands=cands)
    w = S.ov(body)
    assert w[0].get("amount") == 45.0 and w[1].get("amount") == 55.0, w
    assert rec.sets == [], [(k, v.get("title")) for k, v, _t in rec.sets]


# --------------------------------------------------------------------------- F4 the savings readers
SAUV_BLEU_Q = "Sauvage EDP vs Bleu de Chanel EDP"
F4_PAIRS = {
    "t3_01": (lambda: (R.prod("Ted Baker M 30ml", R.TED_P), R.prod("Dior Sauvage 100 ML Edp", R.DIOR_P)), R.TED_Q),
    "ysl_lveb": (lambda: (R.prod("YSL Libre EDP", R.YSL_P), R.prod("Lancome La Vie Est Belle EDP", R.LVEB_P)),
                 None),
    "mixed": (lambda: (R.prod("Ted Baker M 30ml", R.TED_P), R.prod("Dior Sauvage EDP", R.DIOR_P)),
              "Ted Baker M 30ml vs Dior Sauvage EDP"),
}


def _stored(monkeypatch, mk, q, flag, cap, cands=None):
    psetflags(monkeypatch, flag=flag, fix="true")
    a, b = mk()
    body, _ = R.run_pair(a, b, q, cands, cap=cap)
    return json.loads(_json(body))


def _both(body):
    return hr._extract_winner_loser_prices(body), pfr._extract_winner_loser_prices(body)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("pair", ["t3_01", "mixed"])
def test_f4a_cross_size_rows_skipped(monkeypatch, pair, cap):
    """F4a RED: both savings extractors (home /savings, profile /monthly-stats) skip a
    stored flag-ON body of T3-01 and of the mixed pair, in cap0 and cap1."""
    mk, q = F4_PAIRS[pair]
    body = _stored(monkeypatch, mk, q, "true", cap)
    assert (body["metadata"].get("pair_price_sizes") or {}).get("mode") != "same_size", body["metadata"]
    assert _both(body) == ((None, None), (None, None)), _both(body)


def test_f4b_ysl_lveb_cap1_skipped(monkeypatch):
    """F4b RED: YSL 90 ml vs Lancome 100 ml, cap1 (both shown): skipped by both readers."""
    mk, q = F4_PAIRS["ysl_lveb"]
    body = _stored(monkeypatch, mk, q, "true", True)
    assert R.shown(body["products"][0]["price"]) and R.shown(body["products"][1]["price"])
    assert _both(body) == ((None, None), (None, None)), _both(body)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_f4c_same_size_counted_as_base_pin(monkeypatch, cap):
    """F4c PIN: Sauvage 100 ml vs Bleu 100 ml (same_size) is counted with the same amounts
    as the flag-OFF body."""
    mk = lambda: (R.prod("Sauvage EDP", R.SAUV_100), R.prod("Bleu de Chanel EDP", R.BLEU_100))  # noqa: E731
    off = _stored(monkeypatch, mk, SAUV_BLEU_Q, None, cap)
    on = _stored(monkeypatch, mk, SAUV_BLEU_Q, "true", cap)
    assert on["metadata"]["pair_price_sizes"]["mode"] == "same_size"
    assert _both(on) == _both(off) and _both(off)[0] == (58.11, 91.78), (_both(on), _both(off))


@pytest.mark.parametrize("fx", sorted(R.WALK))
def test_f4d_unmarked_body_counted_as_base_pin(monkeypatch, fx):
    """F4d PIN: a body without the marker (every flag-OFF body of the walk) is read exactly
    as the base reader reads it (the B1 gate, winner_index, BHD and the amounts)."""
    a, b, q, c = R.WALK[fx]()
    psetflags(monkeypatch, flag=None, fix="true")
    body, _ = R.run_pair(a, b, q, c)
    body = json.loads(_json(body))
    assert "pair_price_sizes" not in body["metadata"]
    prices = [(p or {}).get("price") or {} for p in body["products"]]
    if all(p.get("currency") == "BHD" for p in prices):
        exp = (prices[0].get("amount"), prices[1].get("amount"))
        exp = tuple(float(x) if isinstance(x, (int, float)) else None for x in exp)
    else:
        exp = (None, None)
    assert _both(body) == (exp, exp), (fx, _both(body), exp)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fx", sorted(R.WALK))
def test_f4e_walk_every_cross_size_body_is_marked(monkeypatch, fx, cap):
    """F4e PIN (walk): every flag-ON fixture body that shows both amounts at different or
    unknown sizes carries metadata.pair_price_sizes with mode != same_size, so the F4 skip
    covers it; a both-shown same-size body says same_size."""
    a, b, q, c = R.WALK[fx]()
    psetflags(monkeypatch, flag="true", fix="true")
    body, _ = R.run_pair(a, b, q, c, cap=cap)
    w = R.ov(body)
    if not (R.shown(w[0]) and R.shown(w[1])):
        return
    marker = body["metadata"].get("pair_price_sizes")
    sizes = [p.get("size_ml") for p in w]
    if None in sizes or sizes[0] != sizes[1]:
        assert isinstance(marker, dict) and marker.get("mode") != "same_size", (fx, sizes, marker)
    else:
        assert marker == {"mode": "same_size", "sizes_ml": sizes}, (fx, marker)


@pytest.mark.parametrize("mode,skipped", [("different_sizes", True), ("unknown", True), ("same_size", False)])
def test_f4h_every_mode_but_same_size_is_skipped(monkeypatch, mode, skipped):
    """F4h RED: a stored both-shown body whose marker says `unknown` (oz-only or two-size
    titles) is skipped like `different_sizes`; `same_size` is counted (the readers key on
    'mode present and not same_size', never on one mode name)."""
    a, b, q, c = R.WALK["a21_oz_two_size"]()
    psetflags(monkeypatch, flag="true", fix="true")
    body, _ = R.run_pair(a, b, q, c, cap=True)
    body = json.loads(_json(body))
    assert R.shown(body["products"][0]["price"]) and R.shown(body["products"][1]["price"])
    body["metadata"]["pair_price_sizes"] = {"mode": mode, "sizes_ml": [None, None]}
    amounts = (body["products"][0]["price"]["amount"], body["products"][1]["price"]["amount"])
    exp = (None, None) if skipped else tuple(float(x) for x in amounts)
    assert _both(body) == (exp, exp), (mode, _both(body))


@pytest.mark.parametrize("header", [None, "price_size"], ids=["cap0", "cap1"])
def test_f4f_persisted_history_body_carries_the_marker(monkeypatch, client, authed, svc_factory, header):
    """F4f PIN: the GET route persists `result`: the History body of a flag-ON T3-01
    compare carries metadata.pair_price_sizes (mode != same_size), so the savings readers
    skip that row after any rollback."""
    R.setflags(monkeypatch, flag="true", fix="true")
    S.route_env(monkeypatch)
    saved = _capture_history(monkeypatch)
    h = {} if header is None else {"X-Client-Capabilities": header}
    resp = client.get("/api/v1/text/compare", params={"product_a": S.TED_DIOR[0], "product_b": S.TED_DIOR[1]},
                      headers=h)
    assert resp.status_code == 200, resp.text[:300]
    assert saved, "the History persist was not reached"
    marker = (saved[0].get("metadata") or {}).get("pair_price_sizes")
    assert isinstance(marker, dict) and marker.get("mode") not in (None, "same_size"), marker


def test_f4g_reader_skip_is_unflagged(monkeypatch):
    """F4g RED: the skip is NOT flag-gated: a stored flag-ON T3-01 body read with the flag
    OFF (after a rollback) is still skipped by both readers."""
    mk, q = F4_PAIRS["t3_01"]
    body = _stored(monkeypatch, mk, q, "true", True)
    psetflags(monkeypatch, flag=None, fix="true")
    assert _both(body) == ((None, None), (None, None)), _both(body)


# --------------------------------------------------------------------------- F6 the surviving mutants
@pytest.mark.parametrize("size,passes", [(25, False), (29, False), (30, True), (50, True)])
def test_f6_x01_floor_boundary(monkeypatch, size, passes):
    """F6 X01 PIN: a 25 / 29 ml listing is under the P2R-12 floor, a 30 / 50 ml one is not;
    on a pair the under-floor side (no candidate) is pended pending_genuine."""
    psetflags(monkeypatch, flag="true", fix="true")
    price = R.P(20.0, "Dior Sauvage EDP %dml" % size, "store-a", "p/sv-%d" % size)
    assert ps.p2_passes_floor(price) is passes
    body, _ = R.run_pair(R.prod("Dior Sauvage EDP", price), R.prod("Bleu de Chanel EDP", R.BLEU_100), cap=True)
    w = R.ov(body)[0]
    if passes:
        assert not R.pending(w, "pending_genuine"), w
    else:
        assert R.pending(w, "pending_genuine"), w


def test_f6_x04_no_stamp_without_url(monkeypatch):
    """F6 X04 = E09 PIN (X1-R12): a shown fragrance price with no url gets no size_ml /
    per_ml; the same price with a url gets both."""
    psetflags(monkeypatch, flag="true")
    for url, stamped in ((None, False), ("https://store-a.example.com/p/sv", True)):
        price = dict(R.P(58.11, "Dior Sauvage EDP 100ml"), url=url)
        pd = R.prod("Dior Sauvage EDP", price)
        view, _best, _ret, state = ps.p2_wire_price(pd, FRAG, "BHD", False, True)
        assert state == "none" and view.get("amount") == 58.11, view
        assert ("size_ml" in view and "per_ml" in view) is stamped, (url, view)


@pytest.mark.parametrize("guard", [True, False], ids=["guard_on", "guard_off"])
def test_f6_x05_restore_region_currency_guard(monkeypatch, guard):
    """F6 X05 PIN: a projected open side whose found price is in another currency than the
    region's is never restored with the region-currency guard on (it ships flag OFF's
    pending dict); with the guard off it is restored."""
    psetflags(monkeypatch, flag="true")
    stash = R.P(39.0, "YSL Libre Eau de Parfum 90ml", "store-a", "p/libre-90")
    stash["currency"] = "USD"
    pd = R.prod("YSL Libre EDP", ps.make_pending_price("BHD", "size_mismatch"))
    pd.update({"best_price": None, "retailer": None, "_p2_shown_price": stash, "_p2_open": True})
    view, _best, _ret, state = ps.p2_wire_price(pd, FRAG, "BHD", guard, True)
    if guard:
        assert state != "both_shown" and R.pending(view), (state, view)
    else:
        assert state == "both_shown" and view.get("amount") == 39.0, (state, view)


def test_f6_e06_flag_off_token_logs_cap_none(monkeypatch, caplog):
    """F6 E06 PIN: flag OFF, the service called with price_size_cap=True: every
    PRICE_OUTCOME line says cap=none (the capability is bound only under the flag)."""
    S.has_cap_kwarg()
    R.setflags(monkeypatch, flag=None, fix="true")
    caplog.set_level(logging.INFO)
    S.run("rest", S.TED_DIOR, cap=True)
    f = _fields(caplog)
    assert len(f) == 2 and all(x["cap"] == "none" for x in f), f


@pytest.mark.parametrize("pair", ["ysl_lveb", "t3_01"])
def test_f6_e12_alias_mirrors_a_restored_side(monkeypatch, pair):
    """F6 E12 PIN: the legacy alias of a restored side carries best_price = the shown
    amount and retailer = the shown listing's retailer (cap1)."""
    psetflags(monkeypatch, flag="true", fix="true")
    if pair == "ysl_lveb":
        a, b, q, i, src = (R.prod("YSL Libre EDP", R.YSL_P), R.prod("Lancome La Vie Est Belle EDP", R.LVEB_P),
                           None, 0, R.YSL_P)
    else:
        a, b, q, i, src = (R.prod("Ted Baker M 30ml", R.TED_P), R.prod("Dior Sauvage 100 ML Edp", R.DIOR_P),
                           R.TED_Q, 1, R.DIOR_P)
    body, snap = R.run_pair(a, b, q, cap=True)
    assert isinstance(snap[i].get("_p2_shown_price"), dict), "precondition: the side is projected"
    alias = body["products"][i]
    assert alias["best_price"] == src["amount"] and alias["retailer"] == src["retailer"], alias


# --------------------------------------------------------------------------- F7 log truth
@pytest.mark.parametrize("shape", [("", "Sauvage EDP", "EDP"), ("Dior", "Dior Sauvage", "EDP")],
                         ids=["variant_in_name", "brand_repeated"])
def test_f7a_outcome_reads_the_notes_under_their_write_key(monkeypatch, caplog, shape):
    """F7a RED (corr m4): the price task names its ledger product in _get_price, a
    Shopping filter notes a numbers_match rejection there, and the PRICE_OUTCOME line of
    the product dict _fetch_product_data builds for the same Step-1 values reads it."""
    psetflags(monkeypatch, flag=None, fix="true")
    caplog.set_level(logging.INFO)
    brand, name, variant = shape
    q = ("%s %s %s" % (brand, name, variant)).strip()

    async def _go():
        ps.price_trace_bind()
        p = S.fy._Patcher()
        try:
            p.setattr(scs, "get_cached", lambda k: copy.deepcopy(CACHED_5))
            svc = scs.StructuredComparisonService()
            await svc._get_price(brand, name, variant, "bahrain", q, nocache=False, category=FRAG)
        finally:
            p.undo()
        ps.price_miss_note(None, "rejected", family="shopping", rule="numbers_match", title="Sauvage EDT 60ml")
        full, display = scs._product_display_identity(brand, name, variant, q, False)
        a = R.prod("x", ps.make_pending_price("BHD", "pending_genuine"))
        a.update(brand=brand, name=display, full_name=full, variant=variant)
        R.build([a, R.prod("Bleu de Chanel EDP", R.BLEU_100)], q + " vs Bleu de Chanel EDP")
    contextvars.copy_context().run(lambda: asyncio.run(_go()))
    f = _fields(caplog)
    assert len(f) == 2, f
    assert f[0]["miss"] == "rejected" and f[0]["miss_rule"] == "numbers_match", f[0]


@pytest.mark.parametrize("cap", CAPCELLS)
def test_f7b_floor_pend_logs_reconcile_floor(monkeypatch, caplog, cap):
    """F7b RED (corr m5): a floor pend logs reconcile=floor (never reselect)."""
    psetflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)

    def _go():
        ps.price_trace_bind()
        pd = [R.prod("Dior Sauvage EDP", R.P(10.0, R.TRAVEL, "store-a", "p/tr")), R.prod("Bleu de Chanel EDP",
                                                                                      R.BLEU_100)]
        ps.reconcile_pair_fairness(pd, None, FRAG, candidates_by_name={})
        return R.build(pd)
    R.in_ctx(_go, cap)
    f = _fields(caplog)
    assert f and f[0]["reconcile"] == "floor" and f[0]["miss_rule"] == "floor", f
    assert f[1]["reconcile"] != "floor", f[1]

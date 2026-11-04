"""S81-18 KB-FIRST-SERVE (+ the verdict-cache key log) RED rows (spec S81-G4, unit
S81-18 section 5, as amended by RULINGS_S81_G4: R-G4-2 the KB price keeps
``source_method "page_scrape"`` with the additive ``as_of``; R-G4-3 the verdict-cache
key's prompt digest is PRODUCT-FREE (R17 amended: a changed spec snippet or price on a
live leg does NOT change the key, a changed card version DOES, the template /
category / quality do); R-G4-4 ``as_of`` = last_seen and the capability keyword
``kb_price_asof`` through the five route call sites; R-G4-11 the text constraints).

RED rows R1..R20 fail at base on an AssertionError only: ``app.services.kb_serve`` is
reached through ``_serve()`` (find_spec + an assertion) FIRST in every row, and every
missing attribute through ``_attr``. PIN rows P1..P4 are green at base with the FULL
configuration: both flags OFF over the spellings unset / "false" / " 0 " / "OFF", the
three knobs set, ENABLE_SYNC_DB_OFFLOAD set, the capability header sent on the route
rows, raising recorders on the service-role ``rpc``, on ``kb_serve.fetch_cards`` and
``kb_serve.hashlib`` (installed getattr-safely: a no-op at base) and on the request
header getter for ``x-client-capabilities``.

The compare rows drive the REAL entries and the REAL ``_fetch_product_data`` over the
FY25 faked pipeline of tests/test_s75_fanout_identity.py (COPIED here, never
imported), with fragrance identities; every live leg is a COUNTING recorder (a raising
leg would be swallowed by the gather's return_exceptions at base and could end the
compare on a non-assertion error; the counts are asserted instead).
tests/fixtures/s81_s18_flag_off_golden.json holds the FY25-normalised REST / stream /
camera payloads recorded at base 0b19de5b under the full configuration (re-record only
at a base sha: ``python -m tests.test_s81_s18_kb_first_serve <out.json>``).

Hygiene: pure ASCII, LF; bounded runner only; netguard on (every leaf faked);
synthetic identities and hosts only; no key-shaped literal.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import re
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
            raise OSError("s18 recorder: network blocked")
        return _real_gai(host, *args, **kwargs)

    socket.getaddrinfo = _gai
    os.environ["OPENAI_API_KEY"] = "sk" + "-test-dummy"

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "s81_s18_flag_off_golden.json"
SERVE = "app.services.kb_serve"
FLAG = "ENABLE_KB_FIRST_SERVE"
LOGF = "ENABLE_VERDICT_CACHE_LOG"
KNOBS = {"KB_FIRST_SERVE_TIMEOUT_SECONDS": "1.5", "KB_FIRST_SERVE_MAX_ASOF_DAYS": "30",
         "VERDICT_CACHE_LOG_MAX_KEYS": "500"}
CLEARED_ENV = (
    FLAG, LOGF, "KB_FIRST_SERVE_TIMEOUT_SECONDS", "KB_FIRST_SERVE_MAX_ASOF_DAYS", "VERDICT_CACHE_LOG_MAX_KEYS",
    "ENABLE_SYNC_DB_OFFLOAD", "OPENAI_MODEL_VERDICT", "ENABLE_KB_INGEST", "ENABLE_FIELD_STATUS_METADATA",
    "KB_INGEST_GAP_MAX", "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH",
    "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "PARSE_TIMEOUT_SECONDS",
    "ENABLE_UNIFIED_SEARCH_BOUND", "UNIFIED_SEARCH_TIMEOUT_SECONDS",
    "ENABLE_PHASE2_RESIDUAL_GUARD", "PHASE2_MIN_RESIDUAL_SECONDS", "DEBUG_STAGE_TIMINGS",
    "ENABLE_FULL_STREAM_DEADLINE", "ENABLE_RESULT_STATUS_METADATA", "ENABLE_LLM_LEDGER_V2",
    "ENABLE_LLM_SPEND_BREAKER", "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT", "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION",
    "ENABLE_SONNET_ESCALATION", "ENABLE_OPENAI_PRE_V3", "ENABLE_FRAGRANCE_ONLY_GATE",
    "ENABLE_JSONLD_RATING", "ENABLE_IMAGE_PIPELINE_V2", "ENABLE_DATA_GUARDS_V2",
    "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_TIER_FILL_RESIDUAL_GUARD",
    "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT", "ENABLE_REQUEST_CONTEXT_HEADERS", "ENABLE_PAID_ROUTE_METERING",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_SEARCH_LOG_TRUTH", "ENABLE_COMPARISON_ID_ECHO",
    "ENABLE_ANON_USAGE_GATE", "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_VISION_IDENTITY_V2",
    "ENABLE_DEVICE_DAILY_QUOTA", "ENABLE_RIYADH_RESET", "ENABLE_ARABIC_VERDICT_OUTPUT",
)
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]
OFF_IDS = ["unset", "false", "pad0", "OFF"]
NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
PDP_A = "https://" + HOST_A + "/products/nimbus-noir"
PDP_A50 = "https://" + HOST_A + "/products/nimbus-noir-50"
PDP_B = "https://" + HOST_B + "/products/velvet-dusk"
IMG_A = "https://" + HOST_A + "/img/nimbus-noir.jpg"
IMG_B = "https://" + HOST_B + "/img/velvet-dusk.jpg"
P0 = ("Acme", "Nimbus Noir Eau de Parfum")
P1 = ("Zephyra", "Velvet Dusk Eau de Toilette")
QUERY = "Acme Nimbus Noir Eau de Parfum vs Zephyra Velvet Dusk Eau de Toilette"
VISION = [{"brand": P0[0], "name": P0[1]}, {"brand": P1[0], "name": P1[1]}]
LLM_PARSED = {"products": [
    {"brand": P0[0], "name": P0[1], "variant": None, "category": "fragrances", "search_query": " ".join(P0)},
    {"brand": P1[0], "name": P1[1], "variant": None, "category": "fragrances", "search_query": " ".join(P1)},
], "comparison_type": "value"}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50}
VOLATILE = frozenset({"elapsed_ms", "elapsed_seconds", "timestamp", "generated_at",
                      "created_at", "started_at", "cached_at", "fetched_at", "at",
                      "stage_timings_ms", "orchestrator_timings_ms", "request_id"})
VKEY_LINE = re.compile(r"^\[VERDICT_CACHE\] would_hit=[01] key=[0-9a-f]{16}$")
LEGS = ("_get_price", "_get_specs", "_get_reviews", "_get_verified_rating", "_smart_fallback_extract",
        "search_web", "get_product_image_url", "tier2_fill_non_negotiables", "tier3_synthesize_non_negotiables")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _serve():
    assert _present(SERVE), "app/services/kb_serve.py does not exist (S81-18 not implemented)"
    return importlib.import_module(SERVE)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (S81-18 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _kb():
    from app.services import kb_service as kb
    return kb


_MISSING = object()


class _Patcher:
    """monkeypatch's API outside pytest (the base recorder)."""

    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, value, raising=True):
        self._undo.append(("attr", obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)

    def setenv(self, name, value):
        self._undo.append(("env", None, name, os.environ.get(name, _MISSING)))
        os.environ[name] = value

    def delenv(self, name, raising=True):
        self._undo.append(("env", None, name, os.environ.get(name, _MISSING)))
        os.environ.pop(name, None)

    def undo(self):
        while self._undo:
            kind, obj, name, value = self._undo.pop()
            if kind == "attr":
                if value is _MISSING:
                    delattr(obj, name)
                else:
                    setattr(obj, name, value)
            elif value is _MISSING:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    if _present(SERVE):
        seen = getattr(importlib.import_module(SERVE), "_SEEN", None)
        if hasattr(seen, "clear"):
            seen.clear()
    yield
    if _present(SERVE):
        seen = getattr(importlib.import_module(SERVE), "_SEEN", None)
        if hasattr(seen, "clear"):
            seen.clear()


def _set_flag(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _full_config(mp, *, flag=None, log_flag=None):
    for k, v in KNOBS.items():
        mp.setenv(k, v)
    mp.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    _set_flag(mp, FLAG, flag)
    _set_flag(mp, LOGF, log_flag)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _z(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid(pair):
    return _kb().kb_product_id(pair[0], pair[1])


def _vid(pid, ml):
    kb = _kb()
    conc = pid.split("|")[3]
    conc = conc if conc in kb.kb_concentrations() else None
    return kb.kb_variant_key(pid, conc, ml)


def _offer(pid, url, host, *, days=2, ml=100, amount=42.5, market="BH", currency="BHD", in_stock=True):
    return {"variant_id": _vid(pid, ml), "merchant_id": host, "market": market, "observed_currency": currency,
            "amount": amount, "canonical_url": url, "last_seen": _iso(NOW - timedelta(days=days)),
            "captured_at": _iso(NOW - timedelta(days=days + 3)), "first_seen": _iso(NOW - timedelta(days=days + 3)),
            "in_stock": in_stock, "list_vs_sale": "unknown", "evidence_rung": "page_evidence", "size_ml": ml}


def _card(pair, *, host=HOST_A, url=PDP_A, image=IMG_A, identity="high", offers=None, specs=None, images=None,
          rating=True, version="2026-10-30T00:00:00+00:00"):
    pid = _pid(pair)
    conc = pid.split("|")[3]
    if offers is None:
        offers = [_offer(pid, url, host)]
    if specs is None:
        specs = {"concentration": "Eau de Parfum", "scent_family": "woody", "season": "winter"}
    if images is None:
        images = [{"url": image, "provenance_host": host, "source": "retailer_jsonld",
                   "captured_at": _iso(NOW - timedelta(days=4))}]
    variants = sorted({o["variant_id"] for o in offers})
    return {
        "product": {"id": pid, "brand": pair[0], "name": pair[1], "concentration": conc, "line": None,
                    "audience": None, "identity_confidence": identity, "updated_at": version},
        "variants": [{"id": v, "product_id": pid, "concentration": conc,
                      "size_ml": int(v.rsplit("|", 1)[1]) if v.rsplit("|", 1)[1].isdigit() else None,
                      "gtin": None, "sku": None} for v in variants],
        "offers": offers,
        "images": images,
        "specs": [{"field": f, "value": v, "lang": "en", "cited": True, "source_url": url,
                   "extractor": "retailer_jsonld"} for f, v in specs.items()],
        "rating": ({"sources": 1, "review_count": 31, "rating": 4.6} if rating
                   else {"sources": 0, "review_count": None, "rating": None}),
    }


def _card_b(**kw):
    kw.setdefault("host", HOST_B)
    kw.setdefault("url", PDP_B)
    kw.setdefault("image", IMG_B)
    return _card(P1, **kw)


class _RpcBuilder:
    def __init__(self, client, name, params):
        self.client, self.name, self.params = client, name, params

    def execute(self):
        self.client.calls.append({"name": self.name, "params": dict(self.params),
                                  "thread": threading.get_ident(), "in_run_db": self.client.flag["in"],
                                  "phase": "execute"})
        if self.client.raising is not None:
            raise self.client.raising
        data = self.client.cards.get(self.params.get("p_product_id"))
        if self.client.data_override is not _MISSING:
            data = self.client.data_override
        return types.SimpleNamespace(data=copy.deepcopy(data))


class _CardClient:
    """The service-role client recorder: rpc(name, params).execute() -> the card."""

    def __init__(self, cards=None, *, raising=None, data_override=_MISSING):
        self.cards = dict(cards or {})
        self.raising = raising
        self.data_override = data_override
        self.calls = []
        self.flag = {"in": False}

    def rpc(self, name, params=None, *args, **kwargs):
        self.calls.append({"name": name, "params": dict(params or {}), "thread": threading.get_ident(),
                           "in_run_db": self.flag["in"], "phase": "rpc"})
        return _RpcBuilder(self, name, params or {})

    def table(self, name):
        raise AssertionError("S81-18 never reads a table: " + name)


def _install_kb(mp, client, *, delay=0.0):
    """kb_serve's seams: the admin client, the clock and run_db (a recorder that runs the
    lambda; an optional async delay simulates a slow RPC)."""
    kbs = _serve()
    mp.setattr(kbs, "_admin_client", lambda: client, raising=False)
    mp.setattr(kbs, "_now", lambda: NOW, raising=False)
    from app.utils import db_offload

    async def _run_db(call):
        if delay:
            await asyncio.sleep(delay)
        client.flag["in"] = True
        try:
            return call()
        finally:
            client.flag["in"] = False
    mp.setattr(db_offload, "run_db", _run_db)
    return kbs


def _rpc_execs(client):
    return [c for c in client.calls if c["phase"] == "execute"]


# ---------------------------------------------------------------------------
# the faked compare (the FY25 driver of tests/test_s75_fanout_identity.py, copied)
# ---------------------------------------------------------------------------

def _install(mp, svc, state):
    import app.services.structured_comparison_service as scs
    from app.services import content_safety_service as _cs
    from app.services import scoring_service as _ss

    calls = state.setdefault("calls", {k: [] for k in LEGS})

    def _rec(name, args):
        calls[name].append([str(a)[:80] for a in args[:2]])

    async def _parse(query):
        return json.loads(json.dumps(LLM_PARSED)), dict(USAGE)

    async def _gen(*_a, **_k):
        state.setdefault("gen_calls", 0)
        state["gen_calls"] += 1
        if state.get("gen_raise"):
            raise RuntimeError("s18 probe: verdict failed")
        return ({"winner_index": 0, "winner_declaration": "Acme wins", "winner_reason": "longevity",
                 "verdict": "v", "pros": {}, "cons": {}}, {"prompt_tokens": 7, "completion_tokens": 3})

    async def _cat_llm(*_a, **_k):
        return "fragrances"

    async def _search(query, num_results=10, **kwargs):
        _rec("search_web", [query])
        return {"organic": [{"title": "T " + query[:20], "link": "https://example.com/a",
                             "snippet": "eau de parfum woody longevity 8 hours"}]}

    async def _specs(*a, **_k):
        _rec("_get_specs", a)
        return {"concentration": "Eau de Parfum", "scent_family": "amber", "longevity": "8 hours"}

    async def _price(*a, **_k):
        _rec("_get_price", a)
        return {"amount": 55.0, "currency": "BHD", "estimated": False, "source_method": "local_bhd",
                "retailer": "Live Store", "url": "https://live-store.example.com/p/1", "title": "x",
                "in_stock": True}

    async def _reviews(*a, **_k):
        _rec("_get_reviews", a)
        return {"highlights": ["good"], "summary": "ok"}

    async def _rating(*a, **_k):
        _rec("_get_verified_rating", a)
        return {"rating": 4.5, "review_count": 10, "rating_verified": True,
                "rating_source": {"name": "example", "url": "https://example.com/r"}}

    async def _fallback(*a, **_k):
        _rec("_smart_fallback_extract", a)
        return {}

    async def _tier2(*a, **k):
        _rec("tier2_fill_non_negotiables", [k.get("brand"), k.get("name")])
        return {}

    async def _tier3(*a, **k):
        _rec("tier3_synthesize_non_negotiables", [k.get("brand"), k.get("name")])
        return {}

    async def _image(*a, **_k):
        _rec("get_product_image_url", a)
        return None

    async def _moderate(_self, _text):
        return _cs.SafetyResult(allowed=True)

    def _reconcile(product_data, query, category, candidates_by_name=None, **kw):
        state["reconcile"] = copy.deepcopy(candidates_by_name or {})
        return None

    async def _blocked_log(*_a, **_k):
        return None

    async def _no_profile(*_a, **_k):
        return state.get("behavior_profile")

    async def _demo(*_a, **_k):
        return state.get("demographics_profile")

    from app.services import audit_service as _audit

    mp.setattr(_audit, "log_content_blocked", _blocked_log)
    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    mp.setattr(scs, "parse_product_query", _parse)
    mp.setattr(scs, "generate_comparison", _gen)
    mp.setattr(scs, "reconcile_pair_fairness", _reconcile)
    mp.setattr(scs, "classify_category_llm", _cat_llm)
    mp.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    mp.setattr(scs, "search_web", _search)
    mp.setattr(scs, "tier2_fill_non_negotiables", _tier2)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _tier3)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    mp.setattr(scs, "get_product_image_url", _image)
    mp.setattr(scs, "get_user_demographics", _demo)
    if state.get("quiet_ff"):  # a user-bound compare: the post-response writes stay local
        def _ff(coro, label=None, *a, **k):
            close = getattr(coro, "close", None)
            if callable(close):
                close()
        mp.setattr(scs, "_fire_and_forget", _ff)
    svc._get_specs = _specs
    svc._get_price = _price
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _fallback
    svc._fetch_behavior_profile = _no_profile
    return calls


async def _compare(mp, kind, *, vision=None, state=None, **kw):
    import app.services.structured_comparison_service as scs

    state = state if state is not None else {}
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
    svc = scs.StructuredComparisonService()
    _install(mp, svc, state)
    kwargs = dict(kw)
    if vision:
        kwargs["vision_products"] = copy.deepcopy(vision)
    if kind == "rest":
        payload = await asyncio.wait_for(svc.compare_from_text(QUERY, region="bahrain", nocache=True, **kwargs), 60)
    else:
        payload = []

        async def _drain():
            async for event in svc.compare_from_text_streaming(QUERY, region="bahrain", nocache=True, **kwargs):
                payload.append(list(event))
        await asyncio.wait_for(_drain(), 60)
    state["svc"] = svc
    return payload


def _normalize(obj):
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        return repr(obj)
    return obj


SCENARIOS = {
    "rest_full": ("rest", {}),
    "stream_full": ("stream", {}),
    "camera_full": ("rest", {"vision": VISION}),
}


def _golden_snapshot(mp):
    out = {}
    for name, (kind, kw) in SCENARIOS.items():
        state = {}
        payload = asyncio.run(_compare(mp, kind, state=state, **kw))
        out[name] = _normalize({"payload": payload,
                                "calls": {k: len(v) for k, v in state["calls"].items()}})
    return out


def _complete(events):
    for kind, payload in events:
        if kind == "complete":
            return payload
    raise AssertionError("no complete event: %r" % ([e[0] for e in events],))


def _count(state, leg, brand=None):
    rows = state["calls"][leg]
    if brand is None:
        return len(rows)
    return len([r for r in rows if any(brand in x for x in r)])


def _lines(caplog, prefix):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


# ---------------------------------------------------------------------------
# R1-R9 / R17: the module (pure rows)
# ---------------------------------------------------------------------------

def test_r1_module_and_flags(monkeypatch):
    """R1: kb_serve importable; both readers are house booleans read per call."""
    kbs = _serve()
    for reader, name in (("kb_first_serve_enabled", FLAG), ("verdict_cache_log_enabled", LOGF)):
        fn = _attr(kbs, reader)
        for v in (None, "", "false", "0", "apply", "garbage", " OFF "):
            _set_flag(monkeypatch, name, v)
            assert fn() is False, (reader, v)
        for v in (" TRUE ", "true", "1", "yes", "On"):
            monkeypatch.setenv(name, v)
            assert fn() is True, (reader, v)


@pytest.mark.parametrize("name,default,cases", [
    ("KB_FIRST_SERVE_TIMEOUT_SECONDS", 1.0, (("0.05", 0.2), ("9", 3.0), ("1.5", 1.5))),
    ("KB_FIRST_SERVE_MAX_ASOF_DAYS", 30, (("3", 8), ("200", 90), ("45", 45))),
    ("VERDICT_CACHE_LOG_MAX_KEYS", 10000, (("5", 100), ("1000000", 100000), ("2500", 2500))),
])
def test_r2_knobs_parse_defensively(monkeypatch, name, default, cases):
    """R2: each knob: unset / "" / "abc" / "inf" / "nan" / "-1" / "0" -> the default;
    over / under -> clamped."""
    kbs = _serve()
    fn = _attr(kbs, {"KB_FIRST_SERVE_TIMEOUT_SECONDS": "timeout_seconds",
                     "KB_FIRST_SERVE_MAX_ASOF_DAYS": "max_asof_days",
                     "VERDICT_CACHE_LOG_MAX_KEYS": "max_log_keys"}[name])
    for v in (None, "", "abc", "inf", "nan", "-1", "0"):
        _set_flag(monkeypatch, name, v)
        assert fn() == default, (name, v, fn())
    for v, want in cases:
        monkeypatch.setenv(name, v)
        assert fn() == want, (name, v, fn())


class _Headers:
    def __init__(self, value, raising=False):
        self.value, self.raising, self.calls = value, raising, []

    def get(self, key, default=None):
        self.calls.append(key)
        if self.raising:
            raise RuntimeError("s18 probe: header read")
        return self.value


def test_r3_client_price_asof(monkeypatch):
    """R3: flag OFF -> False with the header getter never called; ON: the token match is
    stripped and case-insensitive; foreign tokens, > 512 chars, non-str or a raising
    getter -> False."""
    kbs = _serve()
    fn = _attr(kbs, "client_price_asof")
    h = _Headers("price_asof")
    monkeypatch.delenv(FLAG, raising=False)
    assert fn(types.SimpleNamespace(headers=h)) is False and h.calls == []
    monkeypatch.setenv(FLAG, "true")
    for value, want in (("price_asof", True), (" Price_AsOf ,x", True), ("x,y", False),
                        ("price_asof," + "a" * 520, False), (123, False), (None, False)):
        h = _Headers(value)
        assert fn(types.SimpleNamespace(headers=h)) is want, value
    assert fn(types.SimpleNamespace(headers=_Headers("price_asof", raising=True))) is False


def test_r4_required_spec_fields_fragrances():
    """R4: fragrances -> (concentration, scent_family, season); no LICENCE_FIELDS member in
    any category's result."""
    kbs = _serve()
    lic = _attr(kbs, "LICENCE_FIELDS")
    assert tuple(lic) == ("notes_top", "notes_heart", "notes_base", "longevity", "sillage"), lic
    fn = _attr(kbs, "required_spec_fields")
    assert tuple(fn("fragrances")) == ("concentration", "scent_family", "season"), fn("fragrances")
    from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS
    for cat in sorted(CRITICAL_SCHEMA_FIELDS):
        assert not set(fn(cat)) & set(lic), (cat, fn(cat))


def test_r5_fetch_cards_one_gather_two_rpcs_through_run_db(monkeypatch):
    """R5: two rpc("kb_product_card", {p_product_id, p_lang}) calls, each built AND
    executed inside run_db; pid = kb_service.kb_product_id; a placeholder product makes
    no call; output "ar" -> p_lang "ar"."""
    kbs = _serve()
    monkeypatch.setenv(FLAG, "true")
    client = _CardClient({_pid(P0): _card(P0), _pid(P1): _card_b()})
    _install_kb(monkeypatch, client)
    fetch = _attr(kbs, "fetch_cards")
    products = [dict(LLM_PARSED["products"][0]), dict(LLM_PARSED["products"][1])]
    cards = asyncio.run(fetch(products, None))
    assert [c["product"]["id"] for c in cards] == [_pid(P0), _pid(P1)], cards
    execs = _rpc_execs(client)
    assert sorted(c["params"]["p_product_id"] for c in execs) == sorted([_pid(P0), _pid(P1)])
    assert all(c["name"] == "kb_product_card" and c["params"]["p_lang"] == "en" for c in execs), execs
    assert all(c["in_run_db"] for c in client.calls), client.calls
    client.calls.clear()
    placeholder = {"brand": "Unknown", "name": "Unknown", "variant": None, "category": "fragrances"}
    cards = asyncio.run(fetch([placeholder, products[1]], "ar"))
    assert cards[0] is None and cards[1]["product"]["id"] == _pid(P1)
    execs = _rpc_execs(client)
    assert [c["params"] for c in execs] == [{"p_product_id": _pid(P1), "p_lang": "ar"}], execs


@pytest.mark.parametrize("case", ["raise", "timeout", "client_none", "data_list"])
def test_r6_fetch_cards_total(monkeypatch, caplog, case):
    """R6: rpc raises / timeout over the knob / client None / .data a list -> [None, None];
    a failure logs ONE WARNING carrying the exception type name only; never raises."""
    kbs = _serve()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("KB_FIRST_SERVE_TIMEOUT_SECONDS", "0.2")
    client = _CardClient({_pid(P0): _card(P0), _pid(P1): _card_b()},
                         raising=RuntimeError("s18 probe") if case == "raise" else None,
                         data_override=[1, 2] if case == "data_list" else _MISSING)
    _install_kb(monkeypatch, client, delay=0.6 if case == "timeout" else 0.0)
    if case == "client_none":
        monkeypatch.setattr(kbs, "_admin_client", lambda: None)
    caplog.set_level(logging.INFO)
    started = time.monotonic()
    cards = asyncio.run(_attr(kbs, "fetch_cards")([dict(p) for p in LLM_PARSED["products"]], "en"))
    assert time.monotonic() - started < 2.0
    assert cards == [None, None], cards
    warns = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_SERVE]")]
    if case == "data_list":
        return
    want = {"raise": "RuntimeError", "timeout": "TimeoutError"}.get(case)
    assert len(warns) == 1 and warns[0].startswith("[KB_SERVE] card read failed: "), warns
    assert re.match(r"^\[KB_SERVE\] card read failed: [A-Za-z_][A-Za-z0-9_]*$", warns[0]), warns
    if want:
        assert warns[0].endswith(want), warns


def _classify(card, *, region="bahrain", accepts_asof=False, category="fragrances"):
    kbs = _serve()
    return _attr(kbs, "classify")(card, category=category, region=region, now=NOW, accepts_asof=accepts_asof)


def test_r7_classify_full_partial_miss():
    """R7: None -> miss; high + a fresh BH offer + the three cited specs + an https image
    -> full; any one missing -> partial; identity medium -> partial."""
    assert _classify(None)["hit"] == "miss"
    full = _classify(_card(P0))
    assert full["hit"] == "full", full
    assert full["pid"] == _pid(P0) and full["specs_complete"] is True and full["image_url"] == IMG_A
    assert full["price_state"] == "fresh" and full["rating"] == 4.6 and full["review_count"] == 31
    for card in (_card(P0, offers=[]), _card(P0, specs={"concentration": "EDP", "scent_family": "woody"}),
                 _card(P0, images=[]), _card(P0, identity="medium"),
                 _card(P0, images=[{"url": "http://" + HOST_A + "/img/x.jpg", "provenance_host": HOST_A,
                                    "source": "retailer_jsonld"}])):
        out = _classify(card)
        assert out["hit"] == "partial", (out["hit"], out["price_state"], out["specs_complete"], out["image_url"])
    m = _classify(None)
    assert m["price"] is None and m["specs"] is None and m["image_url"] is None and m["price_state"] == "none"


def test_r8_price_ttl_and_asof(monkeypatch):
    """R8: 6 d fresh; 8 d without as_of -> stale_refused (no price); 8 d with as_of ->
    served with as_of = last_seen (Z); 31 d with the knob at 30 -> refused; non-BHD,
    market AE, region kuwait, in_stock False -> not eligible."""
    monkeypatch.setenv("KB_FIRST_SERVE_MAX_ASOF_DAYS", "30")
    pid = _pid(P0)
    out = _classify(_card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=6)]))
    assert out["price_state"] == "fresh" and out["price"]["amount"] == 42.5, out["price_state"]
    out = _classify(_card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=8)]))
    assert out["price_state"] == "stale_refused" and out["price"] is None, out["price_state"]
    out = _classify(_card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=8)]), accepts_asof=True)
    assert out["price_state"] == "asof" and out["price"]["as_of"] == _z(NOW - timedelta(days=8)), out["price"]
    out = _classify(_card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=31)]), accepts_asof=True)
    assert out["price"] is None and out["price_state"] == "stale_refused", out["price_state"]
    for offer, region in ((_offer(pid, PDP_A, HOST_A, currency="AED"), "bahrain"),
                          (_offer(pid, PDP_A, HOST_A, market="AE"), "bahrain"),
                          (_offer(pid, PDP_A, HOST_A), "kuwait"),
                          (_offer(pid, PDP_A, HOST_A, in_stock=False), "bahrain")):
        out = _classify(_card(P0, offers=[offer]), region=region)
        assert out["price"] is None and out["price_state"] == "none", (offer, region, out["price_state"])


def test_r9_price_dict_shape():
    """R9: the exact key set, source_method page_scrape (R-G4-2), the as_of key, and the
    price passes is_price_showable for the synthetic exact identity."""
    from app.services.price_service import is_price_showable
    out = _classify(_card(P0))
    price = out["price"]
    assert set(price) == {"amount", "currency", "retailer", "url", "source_method", "estimated", "title", "size",
                          "as_of", "_cached", "_cache_source", "in_stock"}, sorted(price)
    assert price["source_method"] == "page_scrape" and price["currency"] == "BHD" and price["estimated"] is False
    assert price["retailer"] == HOST_A and price["url"] == PDP_A and price["size"] == "100ml"
    assert price["_cached"] is True and price["_cache_source"] == "kb" and price["in_stock"] is True
    assert price["as_of"] == _z(NOW - timedelta(days=2))
    assert is_price_showable(" ".join(P0), copy.deepcopy(price)) is True
    cands = out["candidates"]
    assert cands and all(set(c) == set(price) for c in cands), cands


def _vkey(**over):
    kbs = _serve()
    pd = [{"brand": P0[0], "name": P0[1], "variant": None, "category": "fragrances",
           "specs": {"scent_family": "woody"}, "price": {"amount": 42.5, "currency": "BHD"}},
          {"brand": P1[0], "name": P1[1], "variant": None, "category": "fragrances",
           "specs": {"scent_family": "amber"}, "price": {"amount": 30.0, "currency": "BHD"}}]
    args = dict(user_preferences=None, demographics_profile=None, behavior_profile=None, product_data=pd,
                scores_summary="S: 70 vs 60", winner_index=0, lang="en", category="fragrances",
                comparison_quality="normal", views=None)
    args.update(over)
    return _attr(kbs, "log_verdict_key")(**args)


def test_r17_verdict_key_inputs(monkeypatch, caplog):
    """R17 (as amended by R-G4-3): the key moves with the pids, the card versions, the
    scores summary, the winner, the language, the configured verdict model, the category
    and the quality framing; it does NOT move when a live leg's spec snippet or price
    changes; the line carries no name and no URL."""
    _serve()
    monkeypatch.setenv(LOGF, "true")
    caplog.set_level(logging.INFO)
    base = _vkey()
    assert isinstance(base, str) and re.match(r"^[0-9a-f]{64}$", base), base
    assert _vkey() == base
    pd2 = [{"brand": P0[0], "name": P0[1], "variant": None, "category": "fragrances",
            "specs": {"scent_family": "citrus", "season": "summer"}, "price": {"amount": 99.0, "currency": "BHD"}},
           {"brand": P1[0], "name": P1[1], "variant": None, "category": "fragrances",
            "specs": {"scent_family": "amber"}, "price": {"amount": 31.0, "currency": "BHD"}}]
    assert _vkey(product_data=pd2) == base, "a live spec snippet / price moved the key (R-G4-3)"
    v1 = [{"hit": "full", "pid": _pid(P0), "version": "v1"}, {"hit": "miss", "pid": None, "version": None}]
    v2 = [{"hit": "full", "pid": _pid(P0), "version": "v2"}, {"hit": "miss", "pid": None, "version": None}]
    assert _vkey(views=v1) != _vkey(views=v2)
    moved = {
        "scores": _vkey(scores_summary="S: 71 vs 60"), "winner": _vkey(winner_index=1),
        "lang": _vkey(lang="ar"), "category": _vkey(category="electronics"),
        "quality": _vkey(comparison_quality="weak"),
        "pid": _vkey(product_data=[{"brand": "Orvel", "name": "Amber Field Eau de Parfum", "variant": None},
                                   {"brand": P1[0], "name": P1[1], "variant": None}]),
    }
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "gpt-verdict-probe")
    moved["model"] = _vkey()
    monkeypatch.delenv("OPENAI_MODEL_VERDICT", raising=False)
    for name, key in moved.items():
        assert key != base, name
    lines = _lines(caplog, "[VERDICT_CACHE]")
    assert lines and all(VKEY_LINE.match(ln) for ln in lines), lines
    assert all(P0[0] not in ln and "http" not in ln for ln in lines)


# ---------------------------------------------------------------------------
# compare rows
# ---------------------------------------------------------------------------

def _on(mp, cards, *, raising=None, asof=False):
    _full_config(mp, flag="true")
    client = _CardClient(cards, raising=raising)
    _install_kb(mp, client)
    return client


def test_r10_rest_full_hit_skips_paid_legs(monkeypatch):
    """R10: flag ON, two full cards: no live leg runs (search, price, specs, reviews, image,
    rating, smart fallback, Tier 2, Tier 3); the body carries the KB price (as_of), specs
    and image; metadata.kb_hit == ["full", "full"]."""
    _serve()
    client = _on(monkeypatch, {_pid(P0): _card(P0), _pid(P1): _card_b()})
    state = {}
    body = asyncio.run(_compare(monkeypatch, "rest", state=state))
    assert {k: len(v) for k, v in state["calls"].items()} == {k: 0 for k in LEGS}, state["calls"]
    assert len(_rpc_execs(client)) == 2
    assert body.get("success") is True, str(body)[:300]
    assert (body.get("metadata") or {}).get("kb_hit") == ["full", "full"], body.get("metadata")
    price = body["products"][0]["price"]
    assert price["amount"] == 42.5 and price["as_of"] == _z(NOW - timedelta(days=2)), price
    assert "_cache_source" not in price and price["source_method"] == "page_scrape"
    text = json.dumps(body)
    assert IMG_A in text and IMG_B in text and "woody" in text


def test_r11_stream_full_hit_same(monkeypatch):
    """R11: R10 on the stream path; the complete payload's metadata.kb_hit."""
    _serve()
    _on(monkeypatch, {_pid(P0): _card(P0), _pid(P1): _card_b()})
    state = {}
    events = asyncio.run(_compare(monkeypatch, "stream", state=state))
    assert {k: len(v) for k, v in state["calls"].items()} == {k: 0 for k in LEGS}, state["calls"]
    complete = _complete(events)
    assert (complete.get("metadata") or {}).get("kb_hit") == ["full", "full"], complete.get("metadata")
    assert IMG_A in json.dumps(complete)


def test_r12_partial_runs_only_missing_legs(monkeypatch):
    """R12: slot 0 holds a price-only card (partial): its price leg never runs, specs /
    reviews / image / the unified search run once; slot 1 has no card (miss): every leg
    runs; kb_hit == ["partial", "miss"]."""
    _serve()
    _on(monkeypatch, {_pid(P0): _card(P0, specs={}, images=[], rating=False)})
    state = {}
    body = asyncio.run(_compare(monkeypatch, "rest", state=state))
    a, b = P0[0], P1[0]
    assert _count(state, "_get_price", a) == 0 and _count(state, "_get_price", b) == 1, state["calls"]["_get_price"]
    for leg in ("_get_specs", "_get_reviews", "get_product_image_url", "search_web"):
        assert _count(state, leg, a) == 1 and _count(state, leg, b) == 1, (leg, state["calls"][leg])
    assert (body.get("metadata") or {}).get("kb_hit") == ["partial", "miss"], body.get("metadata")
    assert body["products"][0]["price"]["amount"] == 42.5


def test_r13_candidates_seeded_for_fairness(monkeypatch):
    """R13: two eligible offers (50 ml, 100 ml) are both in self._price_candidates
    [full_name] (raw_data = the KB price dict) when reconcile_pair_fairness runs."""
    _serve()
    pid = _pid(P0)
    card = _card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=2, ml=100),
                             _offer(pid, PDP_A50, HOST_A, days=3, ml=50, amount=28.0)])
    _on(monkeypatch, {pid: card, _pid(P1): _card_b()})
    state = {}
    asyncio.run(_compare(monkeypatch, "rest", state=state))
    cands = state.get("reconcile", {})
    name = " ".join(P0)
    assert name in cands, sorted(cands)
    sizes = sorted(c.get("size") for c in cands[name])
    assert sizes == ["100ml", "50ml"], cands[name]
    assert all((c.get("raw_data") or {}).get("_cache_source") == "kb" for c in cands[name]), cands[name]


def test_r16_verdict_key_log_eligible_only(monkeypatch, caplog):
    """R16: ENABLE_VERDICT_CACHE_LOG ON: an anonymous compare logs ONE would_hit=0 line,
    the same compare again would_hit=1; with explicit preferences, demographics or a
    behaviour profile -> no line."""
    _serve()
    _full_config(monkeypatch, log_flag="true")
    caplog.set_level(logging.INFO)
    asyncio.run(_compare(monkeypatch, "rest"))
    asyncio.run(_compare(monkeypatch, "rest"))
    lines = _lines(caplog, "[VERDICT_CACHE]")
    assert len(lines) == 2 and all(VKEY_LINE.match(ln) for ln in lines), lines
    assert lines[0].startswith("[VERDICT_CACHE] would_hit=0 ") and lines[1].startswith("[VERDICT_CACHE] would_hit=1 ")
    assert lines[0].split("key=")[1] == lines[1].split("key=")[1]
    uid = "-".join(["facefeed", "beef", "4bad", "8cab", "deadbeefcafe"])
    for kw, st in (({"user_preferences": {"priorities": ["value"]}}, {"quiet_ff": True}),
                   ({"user_id": uid}, {"demographics_profile": {"age_group": "25-34"}, "quiet_ff": True}),
                   ({"user_id": uid}, {"behavior_profile": {"category_affinity": {"fragrances": 1.0}}, "quiet_ff": True})):
        caplog.clear()
        asyncio.run(_compare(monkeypatch, "rest", state=dict(st), **kw))
        assert _lines(caplog, "[VERDICT_CACHE]") == [], (kw, st)


def test_r18_no_seed_on_failed_verdict(monkeypatch):
    """R18: a raising verdict never seeds the key; the LRU evicts the oldest past the
    knob."""
    kbs = _serve()
    _full_config(monkeypatch, log_flag="true")
    seen = _attr(kbs, "_SEEN")
    seen.clear()
    try:
        asyncio.run(_compare(monkeypatch, "rest", state={"gen_raise": True}))
    except Exception:  # noqa: BLE001 - the verdict failure path may surface; the seed is the subject
        pass
    assert len(seen) == 0, list(seen)[:3]
    asyncio.run(_compare(monkeypatch, "rest"))
    assert len(seen) == 1
    monkeypatch.setenv("VERDICT_CACHE_LOG_MAX_KEYS", "100")
    seed = _attr(kbs, "seed_verdict_key")
    seen.clear()
    keys = [hashlib.sha256(str(i).encode("ascii")).hexdigest() for i in range(150)]
    for k in keys:
        seed(k)
    seed(None)
    assert len(seen) == 100 and keys[0] not in seen and keys[49] not in seen and keys[149] in seen


def test_r20_card_failure_falls_through(monkeypatch, caplog):
    """R20: flag ON with a raising RPC: the body equals the flag-OFF body except the
    additive metadata.kb_hit == ["miss", "miss"]; one WARNING."""
    _serve()
    _full_config(monkeypatch)
    off = _normalize(asyncio.run(_compare(monkeypatch, "rest")))
    _on(monkeypatch, {}, raising=RuntimeError("s18 probe"))
    caplog.set_level(logging.INFO)
    on = _normalize(asyncio.run(_compare(monkeypatch, "rest")))
    assert (on.get("metadata") or {}).get("kb_hit") == ["miss", "miss"], on.get("metadata")
    on["metadata"].pop("kb_hit")
    assert on == off
    assert len(_lines(caplog, "[KB_SERVE]")) == 1


# ---------------------------------------------------------------------------
# G3 rows (the C4 guard)
# ---------------------------------------------------------------------------

_CONFLICT = {
    "kb_products": ("id",), "kb_variants": ("id",),
    "kb_offers": ("variant_id", "merchant_id", "market", "observed_currency", "amount", "list_vs_sale"),
    "kb_images": ("product_id", "url"), "kb_reviews": ("product_id", "source_url"),
    "kb_gaps": ("product_key", "field"),
}


class _KbQuery:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.op, self.payload, self.kwargs, self.filters = None, None, {}, []

    def upsert(self, rows, **kw):
        self.op, self.payload, self.kwargs = "upsert", copy.deepcopy(rows), kw
        return self

    def insert(self, rows, **kw):
        self.op, self.payload, self.kwargs = "insert", copy.deepcopy(rows), kw
        return self

    def update(self, payload, **kw):
        self.op, self.payload, self.kwargs = "update", copy.deepcopy(payload), kw
        return self

    def select(self, *a, **kw):
        self.op = self.op or "select"
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _f(*args, **kwargs):
            self.filters.append([name, list(args)])
            return self
        return _f

    def execute(self):
        self.client.ops.append({"table": self.table, "op": self.op, "payload": self.payload})
        rows = self.payload if isinstance(self.payload, list) else ([self.payload] if self.payload else [])
        return types.SimpleNamespace(data=[dict(r) for r in rows] if self.op in ("upsert", "insert") else [])


class _KbClient:
    def __init__(self):
        self.ops = []

    def table(self, name):
        return _KbQuery(self, name)

    def writes(self, table):
        return [o for o in self.ops if o["table"] == table and o["op"] in ("upsert", "insert", "update")
                and o["payload"]]


def _record(origin):
    rules = [["allow", "/"]]
    return {"state": "allow", "status": 200, "fetched_at": _z(NOW - timedelta(hours=1)),
            "next_reread": _z(NOW + timedelta(hours=23)), "crawl_delay": None, "origin": origin,
            "source": "robots_txt", "rules": {"qarenbot": rules, "star": rules}, "probed": "/"}


def _g3_job(mp, price_extra):
    from app.services import kb_ingest as ki
    from app.services import live_robots as lr
    records = {HOST_A: {"host": HOST_A, "status": "live", "deny": False, "robots": _record("https://" + HOST_A),
                        "challenge": None}}
    mp.setenv("ENABLE_KB_INGEST", "true")
    mp.setattr(ki, "_now", lambda: NOW)
    client = _KbClient()
    mp.setattr(ki, "_admin_client", lambda: client)
    mp.setattr(lr, "records_snapshot", lambda: copy.deepcopy(records))
    mp.setattr(lr, "load_records_sync", lambda *_a, **_k: copy.deepcopy(records))
    price = {"amount": 42.5, "currency": "BHD", "url": PDP_A + "?ref=cmp", "retailer": HOST_A,
             "source_method": "page_scrape", "estimated": False, "size": "100ml", "in_stock": True,
             "_cached": False}
    price.update(price_extra)
    product = {"brand": P0[0], "name": P0[1], "full_name": " ".join(P0), "variant": None, "category": "fragrances",
               "price": price, "image_url": None, "specs": {"concentration": "Eau de Parfum"}, "rating": None,
               "review_count": None}
    other = copy.deepcopy(product)
    other.update({"brand": P1[0], "name": P1[1], "full_name": " ".join(P1)})
    other["price"] = None
    pd = [product, other]
    result = {"success": True, "category_used": "fragrances",
              "products": [{k: v for k, v in p.items() if not k.startswith("_")} for p in pd], "metadata": {}}
    snap = ki.build_job(result, copy.deepcopy(pd), product_categories=["fragrances", "fragrances"],
                        region="bahrain", vision=False, captured_at=NOW)
    ki.run_job(snap)
    return client


def test_r19_kb_served_price_never_reobserved(monkeypatch):
    """R19: G3 run_job over a projection whose price carries _cache_source "kb": no
    kb_offers insert / update (the C4 guard)."""
    client = _g3_job(monkeypatch, {"_cached": True, "_cache_source": "kb", "as_of": _z(NOW - timedelta(days=2))})
    assert client.writes("kb_offers") == [], client.writes("kb_offers")
    assert client.writes("kb_products"), "the product row still written (only the offer is guarded)"


def test_p4_g3_offer_written_for_live_price(monkeypatch):
    """P4 (PIN): G3 run_job on a live genuine price writes one offer (the C4 guard does not
    over-reach)."""
    client = _g3_job(monkeypatch, {})
    rows = [r for o in client.writes("kb_offers") if o["op"] == "upsert" for r in o["payload"]]
    assert len(rows) == 1 and rows[0]["canonical_url"] == PDP_A and rows[0]["merchant_id"] == HOST_A, rows


# ---------------------------------------------------------------------------
# route rows (the capability keyword)
# ---------------------------------------------------------------------------

UID = "-".join(["facefeed", "beef", "4bad", "8cab", "deadbeefcafe"])
USER = {"id": UID, "email": "s18" + "@example.test", "access_token": "tok" + "-s18-synthetic"}
JPEG = b"\xff\xd8" + b"\x00" * 64
BASE_KW = {
    "text.post": ["explicit_pair", "include_pros_cons", "include_reviews", "include_specs", "query", "region",
                  "selected_category", "user_id", "user_preferences"],
    "text.get": ["explicit_pair", "include_pros_cons", "include_reviews", "include_specs", "nocache", "query",
                 "region", "selected_category", "user_id", "user_preferences"],
    "text.stream": ["explicit_pair", "include_pros_cons", "include_reviews", "include_specs", "nocache", "query",
                    "region", "selected_category", "user_id", "user_preferences"],
    "text.quick": ["include_pros_cons", "include_reviews", "include_specs", "query", "region"],
    "image": ["nocache", "region", "vision_products"],
}


def _coro(value=None):
    async def _v():
        return value
    return _v()


class _FakeSafety:
    async def moderate_vision_output(self, _extracted):
        from app.services import content_safety_service
        return content_safety_service.SafetyResult(allowed=True)

    def check_query_intent(self, _query):
        from app.services import content_safety_service
        return content_safety_service.SafetyResult(allowed=True)

    async def moderate_output(self, _text):
        from app.services import content_safety_service
        return content_safety_service.SafetyResult(allowed=True)


def _success():
    return {"success": True, "products": [{"brand": P0[0], "name": P0[1]}, {"brand": P1[0], "name": P1[1]}],
            "metadata": {"total_cost": 0.01}, "category": "fragrances"}


class RouteH:
    """The route harness (the S81-10 shape, trimmed): the real app through TestClient,
    the paid leaves faked; ``real`` = a REAL service over the faked pipeline."""

    def __init__(self, mp, *, flag=None, header=True, real=False, state=None):
        import app.main as app_main
        from fastapi.testclient import TestClient

        from app.api import image_routes, text_routes
        from app.api.auth_routes import get_current_user, get_optional_user
        from app.services import audit_service, cache_service, content_safety_service, usage_service

        self.mp, self.rec, self.header = mp, [], header
        _full_config(mp, flag=flag)
        mp.setattr(cache_service, "redis_client", None)
        rec = self.rec
        self.state = state if state is not None else {}

        def _consume(uid, access_token="", *a, **kw):
            return _coro({"allowed": True, "reason": None, "tier": "free", "consumed": True,
                          "consumed_keys": {"daily": "usage:daily:" + uid},
                          "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2}})

        def _ff(coro, label=None, **kw):
            close = getattr(coro, "close", None)
            if callable(close):
                close()

        for mod in (text_routes, image_routes):
            mp.setattr(mod, "consume_comparison_credit", _consume)
            mp.setattr(mod, "refund_comparison_credit", lambda *a, **k: _coro(None))
            mp.setattr(mod, "record_lifetime_comparison", lambda *a, **k: _coro(None))
            mp.setattr(mod, "log_search", lambda **k: _coro(None))
            mp.setattr(mod, "save_comparison_and_track_cohort", lambda **k: _coro(None))
            mp.setattr(mod, "capture_result_status", lambda *a, **k: None)
            mp.setattr(mod, "fire_and_forget", _ff)
            mp.setattr(mod, "get_user_preferences", lambda uid: _coro({"success": True, "preferences": {}}))
        mp.setattr(image_routes, "refund_anon_comparison_credit", lambda *a, **k: _coro(None))

        harness = self

        class _Svc:
            async def compare_from_text(self, *args, **kwargs):
                rec.append(("compare", sorted(kwargs), kwargs.get("kb_price_asof")))
                return _success()

            def compare_from_text_streaming(self, *args, **kwargs):
                rec.append(("compare_stream", sorted(kwargs), kwargs.get("kb_price_asof")))

                async def _gen():
                    yield "complete", _success()
                return _gen()

        if real:
            import app.services.structured_comparison_service as scs

            def _real():
                svc = scs.StructuredComparisonService()
                _install(mp, svc, harness.state)
                harness.state["svc"] = svc
                return svc
            mp.setattr(text_routes, "get_comparison_service", _real)
        else:
            mp.setattr(text_routes, "get_comparison_service", lambda: _Svc())
        mp.setattr(image_routes, "identify_products", lambda images: _coro(
            {"products": [{"brand": P0[0], "name": P0[1]}, {"brand": P1[0], "name": P1[1]}], "cost": 0.003}))

        class _CamService:
            async def compare_from_text(self, *args, **kwargs):
                rec.append(("camera", sorted(kwargs), kwargs.get("kb_price_asof")))
                return _success()
        mp.setattr(image_routes, "StructuredComparisonService", _CamService)
        mp.setattr(content_safety_service, "get_content_safety_service", lambda: _FakeSafety())
        mp.setattr(audit_service, "log_content_blocked", lambda **kw: _coro(None))
        mp.setattr(usage_service, "_get_user_tier_info", lambda *a, **k: _coro(
            {"subscription_tier": "free", "lifetime_comparisons_used": 5,
             "referral_bonus_comparisons_this_month": 0}))
        mp.setitem(app_main.app.dependency_overrides, get_optional_user, lambda: USER)
        mp.setitem(app_main.app.dependency_overrides, get_current_user, lambda: USER)
        self.client = TestClient(app_main.app, raise_server_exceptions=False)

    def headers(self):
        out = {"X-Request-ID": "s18-rid"}
        if self.header:
            out["X-Client-Capabilities"] = "price_asof,share_v2"
        return out

    def _reset(self):
        from app.middleware.rate_limiter import limiter
        limiter.reset()

    def all_five(self):
        out = {}
        self._reset()
        out["text.post"] = self.client.post("/api/v1/text/compare", json={"query": QUERY}, headers=self.headers())
        self._reset()
        out["text.get"] = self.client.get("/api/v1/text/compare", params={"q": QUERY}, headers=self.headers())
        self._reset()
        out["text.stream"] = self.client.get("/api/v1/text/compare/stream", params={"q": QUERY},
                                             headers=self.headers())
        self._reset()
        out["text.quick"] = self.client.post("/api/v1/text/quick", json={"product1": " ".join(P0),
                                                                           "product2": " ".join(P1)},
                                             headers=self.headers())
        self._reset()
        out["image"] = self.client.post("/api/v1/image/identify",
                                        files=[("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)],
                                        headers=self.headers())
        return out


def _route_kw(rec):
    by = {}
    order = ["text.post", "text.get", "text.stream", "text.quick", "image"]
    for name, entry in zip(order, rec):
        by[name] = entry
    return by


def test_r14_asof_only_with_header(monkeypatch):
    """R14: the REAL route + service: with `X-Client-Capabilities: price_asof` a 10-day KB
    offer is served with as_of (the live price leg never runs for that product); without
    the header the live price leg runs."""
    _serve()
    pid = _pid(P0)
    card = _card(P0, offers=[_offer(pid, PDP_A, HOST_A, days=10)])
    for header, want_live in ((True, 0), (False, 1)):
        state = {"quiet_ff": True}
        h = RouteH(monkeypatch, flag="true", header=header, real=True, state=state)
        client = _CardClient({pid: card})
        _install_kb(monkeypatch, client)
        h._reset()
        resp = h.client.get("/api/v1/text/compare", params={"q": QUERY, "nocache": "true"}, headers=h.headers())
        assert resp.status_code == 200, (resp.status_code, resp.text[:300])
        body = json.loads(resp.text)
        assert _count(state, "_get_price", P0[0]) == want_live, (header, state["calls"]["_get_price"])
        price = body["products"][0]["price"]
        if header:
            assert price.get("as_of") == _z(NOW - timedelta(days=10)) and price["amount"] == 42.5, price
        else:
            assert "as_of" not in price, price


def test_r15_camera_route_forwards_capability(monkeypatch):
    """R15: every route call site passes kb_price_asof=True only with the flag ON and the
    header sent (the camera route included)."""
    _serve()
    h = RouteH(monkeypatch, flag="true", header=True)
    resp = h.all_five()
    assert all(r.status_code == 200 for r in resp.values()), {k: r.status_code for k, r in resp.items()}
    by = _route_kw(h.rec)
    assert sorted(by) == sorted(BASE_KW), h.rec
    for name, entry in by.items():
        assert entry[2] is True, (name, entry)
    h2 = RouteH(monkeypatch, flag="true", header=False)
    h2.all_five()
    for name, entry in _route_kw(h2.rec).items():
        assert "kb_price_asof" not in entry[1], (name, entry)


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def _golden():
    assert GOLDEN.exists(), "the S81-18 golden is missing: " + str(GOLDEN)
    return json.loads(GOLDEN.read_text(encoding="ascii"))


def _raising_recorders(mp, fired):
    """B1: every S81-18 entry point a flag-OFF compare must never reach, as RAISING
    recorders (installed getattr-safely: no-ops at base)."""
    from app.services import database_service

    class _BoomClient:
        def rpc(self, *a, **k):
            fired.append("rpc")
            raise AssertionError("S81-18 OFF: rpc called")

        def table(self, *a, **k):
            fired.append("table")
            raise AssertionError("S81-18 OFF: table called")

    mp.setattr(database_service, "get_admin_supabase_client", lambda *a, **k: _BoomClient())
    if _present(SERVE):
        kbs = importlib.import_module(SERVE)
        mp.setattr(kbs, "_admin_client", lambda: _BoomClient(), raising=False)

        async def _boom_fetch(*a, **k):
            fired.append("fetch_cards")
            raise AssertionError("S81-18 OFF: fetch_cards called")
        mp.setattr(kbs, "fetch_cards", _boom_fetch, raising=False)

        def _boom_sha(*a, **k):
            fired.append("sha256")
            raise AssertionError("S81-18 OFF: kb_serve hashed")
        if hasattr(kbs, "hashlib"):
            mp.setattr(kbs, "hashlib", types.SimpleNamespace(sha256=_boom_sha), raising=False)


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p1_flag_off_rest_stream_camera_golden(monkeypatch, value):
    """P1 (PIN): the FULL configuration with both flags OFF: the REST, stream and camera
    payloads (FY25-normalised) and the live-leg call counts equal the golden recorded at
    base."""
    _full_config(monkeypatch, flag=value, log_flag=value)
    fired = []
    _raising_recorders(monkeypatch, fired)
    got = json.loads(json.dumps(_golden_snapshot(monkeypatch)))
    want = _golden()["scenarios"]
    moved = sorted(name for name in SCENARIOS if got.get(name) != want.get(name))
    assert moved == [], moved
    assert fired == [], fired


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p2_flag_off_no_rpc_no_header_no_key(monkeypatch, caplog, value):
    """P2 (PIN): the same configuration: no rpc, no fetch_cards, no kb_serve hashing, no
    [VERDICT_CACHE] / [KB_SERVE] line, no kb_hit key (REST and stream)."""
    _full_config(monkeypatch, flag=value, log_flag=value)
    fired = []
    _raising_recorders(monkeypatch, fired)
    caplog.set_level(logging.INFO)
    rest = asyncio.run(_compare(monkeypatch, "rest"))
    stream = asyncio.run(_compare(monkeypatch, "stream"))
    assert fired == [], fired
    assert _lines(caplog, "[VERDICT_CACHE]") == [] and _lines(caplog, "[KB_SERVE]") == []
    assert "kb_hit" not in (rest.get("metadata") or {})
    assert "kb_hit" not in (_complete(stream).get("metadata") or {})


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p3_flag_off_service_signature_call(monkeypatch, value):
    """P3 (PIN): with the header sent and the flag OFF, the five route call sites pass
    EXACTLY the base keyword set, and the x-client-capabilities header is never read."""
    from starlette.datastructures import Headers
    reads = []
    real_get = Headers.get

    def _get(self, key, default=None):
        if isinstance(key, str) and key.lower() == "x-client-capabilities":
            reads.append(key)
        return real_get(self, key, default)
    monkeypatch.setattr(Headers, "get", _get)
    h = RouteH(monkeypatch, flag=value, header=True)
    resp = h.all_five()
    assert all(r.status_code == 200 for r in resp.values()), {k: (r.status_code, r.text[:120]) for k, r in resp.items()}
    by = _route_kw(h.rec)
    assert {k: v[1] for k, v in by.items()} == BASE_KW, by
    assert reads == [], reads


if __name__ == "__main__":  # pragma: no cover - the recorder (run at the base sha only)
    _p = _Patcher()
    try:
        import app.main  # noqa: F401
        for _n in CLEARED_ENV:
            os.environ.pop(_n, None)
        _full_config(_p)
        _fired = []
        _raising_recorders(_p, _fired)
        _snap = json.loads(json.dumps(_golden_snapshot(_p)))
        assert _fired == [], _fired
    finally:
        _p.undo()
    with open(sys.argv[1], "w", encoding="ascii", newline="\n") as _fh:
        json.dump({"base": "0b19de5bcc1416111d48bc725359b95151a658ca", "scenarios": _snap}, _fh,
                  indent=1, sort_keys=True, ensure_ascii=True)
        _fh.write("\n")
    print("wrote", sys.argv[1], sorted(_snap))

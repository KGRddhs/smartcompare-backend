"""INC-R1 RESOLVE-OR-ASK (ENABLE_PRODUCT_RESOLVER): RED and PIN rows of the seams.

The two explicit-pair Step-1 hooks of structured_comparison_service (sync and stream), the
three text routes (POST / GET /api/v1/text/compare, GET /compare/stream), the 400 builder
text_routes._surface_comparison_failure, the envelope error_handler.http_exception_handler,
the CLAUDE.md block and the black allowlist. Spec .qa-s80/INC-R1_UNIT_SPEC.md section 5.2 as
amended by the review's corrections and RULINGS_INC_R1 (R1-R1..R1-R31; precedence: the
rulings, then the review corrections, then the spec). Base 731bcddf.

RED = fails at the base on an AssertionError only (the new module is resolved inside the test
body through find_spec / getattr and ASSERTED; a route or orchestrator row runs the base path
and its assertions fail). PIN = green at the base; every PIN runs with the FULL unit
configuration (the flag at the value under test, both knobs, ENABLE_ANTHROPIC_TEXT and
ENABLE_OPENAI_PRE_V3 ON, consent 3, a synthetic Anthropic key, the fake SDK and the fake OpenAI
client, the Fragrances chip) plus the call recorders (the Anthropic and OpenAI creates, every
llm_router.route site key, every os.getenv name, every open of the lines file and the
[RESOLVE] records), so a not-gated mutant is killable (ruling B1). The flag-OFF base literals
(the Step-1 dicts and the FY digests) were RECORDED AT THE BASE by the RED author.

Rulings applied beyond the spec rows: R1-R6 (R12: consent 2 makes no call at all), R1-R9 (R07
- R09: the ask refunds WITH the consume's keys), R1-R10 (R20: the S81-10 refusal budget),
R1-R12 (R17: the Feature Flags pointer sentence), R1-R17 (R18: the three files on the black
allowlist), R1-R18 (R10 / R11: reason + candidates at both gates; the envelope reads the flag
only after the refusal marker matches; P01 carries the getenv and open spies), R1-R23 (R13:
no concentration when none is typed and the line has no seed entry), R1-R29 (C-1: R04 and R13
by [kind]; C-7: R19 the hook is total and falls back to the base dicts).

Hermetic: every network leaf faked through the FY25 harness (tests/test_s75_fanout_identity.py)
and the route ledger of tests/test_retro_w2_1.py; no .env, no real credential (the synthetic
key is built at run time). Pure ASCII, LF.
"""

from __future__ import annotations

import asyncio
import base64
import builtins
import copy
import importlib
import importlib.machinery
import importlib.util
import io
import json
import logging
import os
import pathlib
import sys
import types

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main  # noqa: F401  (FIRST: the dotenv guard)
from app.api import text_routes
from app.api.auth_routes import get_current_user, get_optional_user
from app.main import app as fastapi_app
from app.middleware import error_handler as eh
from app.services import api_budget_service as abs_
from app.services import category_gate as cg
from app.services import kb_serve
from app.services import kb_service
from app.services import llm_router as lr
from app.services import openai_service as osvc
import app.services.structured_comparison_service as scs
from app.utils import request_context as rc
from tests import test_retro_w2_1 as rw
from tests import test_s75_fanout_identity as fy

ROOT = pathlib.Path(__file__).resolve().parents[1]
PR_NAME = "app.services.product_resolver"

FLAG = "ENABLE_PRODUCT_RESOLVER"
TIMEOUT = "PRODUCT_RESOLVER_TIMEOUT_SECONDS"
ASK = "PRODUCT_RESOLVER_ASK"
TEXT = "ENABLE_ANTHROPIC_TEXT"
PRE = "ENABLE_OPENAI_PRE_V3"
EGRESS = "ENABLE_OPENAI_EGRESS_STOP"
RG = "ENABLE_RESULT_GATE"
FRAG = "ENABLE_FRAGRANCE_ONLY_GATE"
KBF = "ENABLE_KB_FIRST_SERVE"
LEDGER = "ENABLE_LLM_LEDGER_V2"
METER = "ENABLE_PAID_ROUTE_METERING"
ENVELOPE = "ENABLE_CAMERA_FAILURE_ENVELOPE"
AUTHREQ = "ENABLE_COMPARE_AUTH_REQUIRED"
CLEAR = tuple(
    sorted(
        set(
            (
                FLAG,
                TIMEOUT,
                ASK,
                EGRESS,
                RG,
                FRAG,
                KBF,
                LEDGER,
                METER,
                ENVELOPE,
                AUTHREQ,
                "ENABLE_LLM_SPEND_BREAKER",
                "ENABLE_RESULT_STATUS_METADATA",
                "ENABLE_SEARCH_LOG_TRUTH",
                "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
                "ENABLE_COMPARISON_ID_ECHO",
                "ENABLE_ANON_USAGE_GATE",
                "ENABLE_DEVICE_DAILY_QUOTA",
                "ENABLE_URL_MODE_V2",
                "ENABLE_KB_INGEST",
                "ENABLE_FIELD_STATUS_METADATA",
                "ENABLE_STRICT_OPTIONAL_AUTH",
                "ENABLE_PREVERDICT_DISCONNECT_ABORT",
                "ENABLE_REQUEST_CONTEXT_HEADERS",
                "ENABLE_LLM_PREFLIGHT_BREAKER",
                "ENABLE_CATEGORY_TOKEN_FIX",
                "FRAGRANCE_LEXICON_PATH",
                "REFUSAL_DAILY_BUDGET",
                "ENABLE_VISION_IDENTITY_V2",
                "DEVICE_KEY_PEPPER",
            )
            + fy.UNIT_ENV
        )
    )
)
SYN_KEY = "syn" + "thetic" + "-anthropic-" + "s3m9"
HAIKU = "claude-haiku-5-5"
ASK_MESSAGE = (
    "We need clearer names to tell which products these are. "
    "Add the brand and the fragrance name."
)
H6_MESSAGE = (
    "Comparison data was incomplete " + chr(0x2014) + " choose different products."
)
OFF_VALUES = (None, "", "false", "0", "off", " FALSE ", "garbage")

OWNER = ("stronger with you", "Tyger")
GOLD4 = ("Dior Sauvage EDP", "Chanel Bleu de Chanel EDP")
MODEL_PAIR = ("Tom Ford Ombre Leather", "Montblanc Explorer")
ASK_PAIR = ("Tom Ford Mystery", "Dior Sauvage EDP")
PAIRS = {"owner": OWNER, "gold4": GOLD4}
REFUSAL_KEYS = [
    "success",
    "error",
    "code",
    "elapsed_seconds",
    "total_cost",
    "api_calls",
    "reason",
    "candidates",
]
ENVELOPE_KEYS = ["success", "error", "code", "request_id"]
TF_CAND = {"brand": "Tom Ford", "line": "Tobacco Vanille", "concentration": "EDP"}
GOOD_CANDS = [[dict(TF_CAND)], []]

OWNER_A = {
    "brand": "Emporio Armani",
    "name": "Stronger With You",
    "variant": "EDT",
    "category": "fragrances",
    "search_query": "Emporio Armani Stronger With You EDT",
    "_explicit": True,
}
OWNER_B = {
    "brand": "Bvlgari",
    "name": "Tygar",
    "variant": "EDP",
    "category": "fragrances",
    "search_query": "Bvlgari Tygar EDP",
    "_explicit": True,
}
DIOR_EDP = {
    "brand": "Dior",
    "name": "Sauvage",
    "variant": "EDP",
    "category": "fragrances",
    "search_query": "Dior Sauvage EDP",
    "_explicit": True,
}


def _explicit(name, category):
    return {
        "brand": "",
        "name": name,
        "variant": None,
        "category": category,
        "search_query": name,
        "_explicit": True,
    }


# ---------------------------------------------------------------- base literals (recorded at 731bcddf)
# P01: the Step-1 dicts reaching _fetch_product_data with the flag OFF and the Fragrances chip,
# and the FY normalised digests of each (kind, pair) snapshot (fy._digest), recorded AT THE BASE.
BASE_FETCH_CHIP = {
    "owner": [_explicit(OWNER[0], "fragrances"), _explicit(OWNER[1], "fragrances")],
    "gold4": [_explicit(GOLD4[0], "fragrances"), _explicit(GOLD4[1], "fragrances")],
}
# base64 of the sha256 fy._digest returns (hex), recorded at 731bcddf twice, equal both times.
BASE_DIGEST = {
    ("rest", "owner"): "q7i69NY9KWinUh4TlrH7ZJrPGuQkEX/lwX6v7yGW+v0=",
    ("stream", "owner"): "lfcvKz4nY++P7xQcWhSsyG/5vWl0GLytYDz5XT0BRIE=",
    ("rest", "gold4"): "ZI7G6Lscn/FfuqgUu2xG3m1QqUzaWM+aXkA6U1IFbxo=",
    ("stream", "gold4"): "OHSHsAHYsaKUjM2UpFA43GhNePUhwJ/QXbk6hg0ba9Y=",
}
# The chip-free base category of a typed pair with no category word: the FY classifier fake.
BASE_FETCH_MODEL_PAIR = [
    _explicit(MODEL_PAIR[0], "electronics"),
    _explicit(MODEL_PAIR[1], "electronics"),
]
BASE_FETCH_OWNER_NOCHIP = [
    _explicit(OWNER[0], "electronics"),
    _explicit(OWNER[1], "electronics"),
]
BASE_FETCH_ASK_PAIR = [
    _explicit(ASK_PAIR[0], "fragrances"),
    _explicit(ASK_PAIR[1], "fragrances"),
]
BASE_FETCH_Q = [
    {
        "brand": "Apple",
        "name": "iPhone 15",
        "variant": None,
        "category": "electronics",
        "search_query": "Apple iPhone 15",
    },
    {
        "brand": "Samsung",
        "name": "Galaxy S24",
        "variant": None,
        "category": "electronics",
        "search_query": "Samsung Galaxy S24",
    },
]
BASE_FETCH_VISION = [
    {
        "brand": "Dior",
        "name": "Sauvage",
        "variant": "100ml",
        "category": "electronics",
        "search_query": "Dior Sauvage",
        "_vision": True,
    },
    {
        "brand": "Chanel",
        "name": "Bleu de Chanel",
        "variant": "100ml",
        "category": "electronics",
        "search_query": "Chanel Bleu de Chanel",
        "_vision": True,
    },
]
BASE_FETCH_PRESPLIT = [
    _explicit(OWNER[0], "electronics"),
    _explicit(OWNER[1], "electronics"),
]
VISION = [
    {"brand": "Dior", "name": "Sauvage", "size_or_count": "100ml"},
    {"brand": "Chanel", "name": "Bleu de Chanel", "size_or_count": "100ml"},
]


# ---------------------------------------------------------------- the RED helpers


def _pr():
    try:
        spec = importlib.util.find_spec(PR_NAME)
    except (ImportError, ValueError):
        spec = None
    assert spec is not None, "app/services/product_resolver.py is absent (INC-R1 C3)"
    return importlib.import_module(PR_NAME)


# ---------------------------------------------------------------- fakes


class _Anth:
    def __init__(self):
        self.calls = []
        self.default = None
        self.delay = 0.0


ANTH = _Anth()


def c_msg(text="{}", stop="end_turn", inp=11, out=7):
    usage = types.SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
        cache_creation=None,
        server_tool_use=None,
    )
    return types.SimpleNamespace(
        id="msg_inc_r1_seam",
        type="message",
        role="assistant",
        model=HAIKU,
        content=[types.SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        usage=usage,
    )


class _NotGiven:
    def __bool__(self):
        return False


NOT_GIVEN = _NotGiven()


class _FakeMessages:
    async def create(self, **kw):
        kw = {k: v for k, v in kw.items() if v is not NOT_GIVEN}
        ANTH.calls.append(kw)
        if ANTH.delay:
            await asyncio.sleep(ANTH.delay)
        return ANTH.default or c_msg()


class _FakeAnthropicClient:
    def __init__(self, **_kw):
        self.messages = _FakeMessages()


def _fake_anthropic_module():
    mod = types.ModuleType("anthropic")
    mod.__spec__ = importlib.machinery.ModuleSpec("anthropic", None)
    mod.AsyncAnthropic = _FakeAnthropicClient
    mod.NOT_GIVEN = NOT_GIVEN
    for name in ("APIError", "APIStatusError", "APIConnectionError"):
        setattr(mod, name, type(name, (Exception,), {}))
    return mod


OAI_CALLS = []


class _OaiCompletions:
    async def create(self, **kw):
        OAI_CALLS.append(kw)
        raise AssertionError("an OpenAI create reached the fake client")


class _OaiClient:
    def __init__(self):
        self.chat = types.SimpleNamespace(completions=_OaiCompletions())


CONSENT = {"value": None}


def _side(is_frag="true", brand="", line="", conc="none", conf="high", cands=()):
    return {
        "is_fragrance": is_frag,
        "brand": brand,
        "line": line,
        "concentration": conc,
        "confidence": conf,
        "candidates": [dict(c) for c in cands],
    }


def _answer(a, b):
    return json.dumps({"a": a, "b": b})


ASK_ANSWER = _answer(
    _side("true", conf="low", cands=[TF_CAND]),
    _side("false", "Acme", "Nothing", "none", "low"),
)
MODEL_ANSWER = _answer(
    _side("true", "Tom Ford", "Ombre Leather", "EDP"),
    _side("true", "Montblanc", "Explorer", "EDP"),
)


class Recorders:
    """Every call recorder of a PIN row: route sites, getenv names, lines-file opens."""

    def __init__(self, monkeypatch):
        self.sites = []
        self.names = []
        self.opens = []
        real_route = lr.route

        async def _route(site, dispatch, client, **kwargs):
            self.sites.append(site)
            return await real_route(site, dispatch, client, **kwargs)

        monkeypatch.setattr(lr, "route", _route)
        real_getenv = os.getenv

        def _getenv(name, default=None):
            self.names.append(name)
            return real_getenv(name, default)

        monkeypatch.setattr(os, "getenv", _getenv)
        real_open = builtins.open
        real_io_open = io.open

        def _wrap(fn):
            def _open(file, *a, **k):
                self.opens.append(str(file))
                return fn(file, *a, **k)

            return _open

        monkeypatch.setattr(builtins, "open", _wrap(real_open))
        monkeypatch.setattr(io, "open", _wrap(real_io_open))

    def knob_reads(self):
        return [n for n in self.names if str(n).startswith("PRODUCT_RESOLVER_")]

    def lines_opens(self):
        return [p for p in self.opens if "fragrance_lines" in p]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_") or name.startswith("PRODUCT_RESOLVER_"):
            monkeypatch.delenv(name, raising=False)
    ANTH.__init__()
    del OAI_CALLS[:]
    CONSENT["value"] = None
    scs._DEBUG_STAGE_TIMINGS = None
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic_module())
    monkeypatch.setattr(
        lr, "_anthropic_client_factory", lambda **kw: _FakeAnthropicClient(**kw)
    )
    monkeypatch.setattr(osvc, "get_client", lambda: _OaiClient())
    monkeypatch.setattr(rc, "consent_version", lambda: CONSENT["value"], raising=False)
    monkeypatch.setattr(
        rc,
        "header_state",
        lambda name: "ok" if isinstance(CONSENT["value"], int) else "absent",
        raising=False,
    )
    for name in ("_redis_get", "_redis_set", "_redis_incr", "_redis_expire"):
        monkeypatch.setattr(abs_, name, lambda *a, **k: None, raising=False)
    monkeypatch.setattr(abs_, "is_circuit_closed", lambda *a, **k: True, raising=False)
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(fastapi_app.dependency_overrides)
    lr._reset_router_state()
    mod = sys.modules.get(PR_NAME)
    if mod is not None and hasattr(mod, "_reset_resolver_state"):
        mod._reset_resolver_state()
    try:
        yield
    finally:
        limiter.enabled = prior
        scs._DEBUG_STAGE_TIMINGS = None
        fastapi_app.dependency_overrides.clear()
        fastapi_app.dependency_overrides.update(saved)
        lr._reset_router_state()
        mod = sys.modules.get(PR_NAME)
        if mod is not None and hasattr(mod, "_reset_resolver_state"):
            mod._reset_resolver_state()


def _full(
    monkeypatch, flag="true", *, consent=3, timeout="5.0", ask="1", text=True, pre=True
):
    """The FULL unit configuration with the flag at the value under test."""
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    monkeypatch.setenv(TIMEOUT, timeout)
    monkeypatch.setenv(ASK, ask)
    if text:
        monkeypatch.setenv(TEXT, "true")
    if pre:
        monkeypatch.setenv(PRE, "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", SYN_KEY)
    monkeypatch.setenv("ENABLE_REQUEST_CONTEXT_HEADERS", "true")
    CONSENT["value"] = consent


def _run(
    kind, pair=None, *, chip=None, query=None, vision=None, user_id=None, extra=None
):
    """One compare on the FY-faked pipeline: (payload, state, svc)."""
    p = fy._Patcher()
    state = fy._new_state()
    try:
        p.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
        svc = scs.StructuredComparisonService()
        fy._install(p, svc, state)
        if extra is not None:
            extra(p, svc, state)
        kwargs = {}
        if pair is not None:
            kwargs["explicit_pair"] = tuple(pair)
        if chip is not None:
            kwargs["selected_category"] = chip
        if vision is not None:
            kwargs["vision_products"] = vision
        if user_id is not None:
            kwargs["user_id"] = user_id
        q = query or ("%s vs %s" % tuple(pair) if pair is not None else fy.QUERY)
        if kind == "rest":
            payload = asyncio.run(
                asyncio.wait_for(
                    svc.compare_from_text(q, region="bahrain", nocache=True, **kwargs),
                    60,
                )
            )
        else:
            payload = []

            async def _drain():
                async for event in svc.compare_from_text_streaming(
                    q, region="bahrain", nocache=True, **kwargs
                ):
                    payload.append(list(event))

            asyncio.run(asyncio.wait_for(_drain(), 60))
        return payload, state, svc
    finally:
        p.undo()


def _snapshot(payload, state, svc):
    return {
        "payload": payload,
        "parse_calls": state["parse_calls"],
        "track_gpt": state["track_gpt"],
        "fetch_products": state["fetch_products"],
        "resolve": state["resolve"],
        "searches": state["searches"],
        "cost": [svc.total_cost, svc.api_calls, svc.gpt_calls, svc.serper_calls],
    }


def _complete(events):
    for kind, data in events:
        if kind == "complete":
            return data
    raise AssertionError("no complete event: %r" % ([e[0] for e in events],))


def _success_body(kind, payload):
    return payload if kind == "rest" else _complete(payload)


def _underscore_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith("_"):
                out.append(k)
            _underscore_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _underscore_keys(v, out)
    return out


def _resolve_records(caplog):
    return [r for r in caplog.records if str(r.getMessage()).startswith("[RESOLVE]")]


# ======================================================================= P01 / P02 flag OFF


@pytest.mark.parametrize("pair_name", sorted(PAIRS))
@pytest.mark.parametrize("kind", ["rest", "stream"])
@pytest.mark.parametrize("off", OFF_VALUES, ids=lambda v: repr(v))
def test_p01_flag_off_identity(monkeypatch, caplog, off, kind, pair_name):
    """P01 (2.12 + C-3): every OFF value with the FULL configuration and every recorder: the
    Step-1 dicts, the base parser_path, no call, no knob read, no lines-file open, no
    [RESOLVE] record, and the FY digest equal to the base literal."""
    _full(monkeypatch, off)
    rec = Recorders(monkeypatch)
    with caplog.at_level(logging.INFO):
        payload, state, svc = _run(kind, PAIRS[pair_name], chip="fragrances")
    monkeypatch.setattr(os, "getenv", os.environ.get)
    assert state["fetch_products"] == BASE_FETCH_CHIP[pair_name], state[
        "fetch_products"
    ]
    assert [entry[1] for entry in state["resolve"]] == [False], state["resolve"]
    assert ANTH.calls == [] and OAI_CALLS == [], (ANTH.calls, OAI_CALLS)
    assert "resolve" not in rec.sites, rec.sites
    assert rec.knob_reads() == [], rec.knob_reads()
    assert rec.lines_opens() == [], rec.lines_opens()
    assert _resolve_records(caplog) == []
    snap = _snapshot(payload, state, svc)
    got = base64.b64encode(bytes.fromhex(fy._digest(snap))).decode("ascii")
    assert got == BASE_DIGEST[(kind, pair_name)], got


def test_p02_fy25_digests_with_unit_config(monkeypatch):
    """P02: the nine FY25 scenarios with the unit's knobs set and the flag 'false' keep the
    recorded digests (the names are exported for the scenario AND restored by monkeypatch).
    """
    env = {FLAG: "false", TIMEOUT: "0.25", ASK: "1"}
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    want = json.loads(fy.FIXTURE.read_text(encoding="ascii"))["digests"]
    got = {}
    for name, (kind, query, kwargs) in fy.SCENARIOS.items():
        got[name] = fy._digest(
            asyncio.run(fy._scenario(kind, query, env=dict(env), **kwargs))
        )
    moved = sorted(n for n in fy.SCENARIOS if got.get(n) != want.get(n))
    assert moved == [], moved


# ======================================================================= R03-R06 the orchestrator seams


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_r03_owner_pair_rewritten(monkeypatch, kind):
    """R03: the owner's pair is rewritten before any fetch; every search uses the canonical
    string; no model call; the canonical brand reaches the payload; no private key leaks.
    """
    _full(monkeypatch, "false")
    off_payload, _s, _v = _run(kind, OWNER, chip="fragrances")
    _full(monkeypatch)
    payload, state, _svc = _run(kind, OWNER, chip="fragrances")
    assert state["fetch_products"] == [OWNER_A, OWNER_B], state["fetch_products"]
    queries = sorted(s[0] for s in state["searches"])
    assert queries == sorted(
        p["search_query"] + " specifications reviews price" for p in (OWNER_A, OWNER_B)
    ), queries
    assert ANTH.calls == []
    body = _success_body(kind, payload)
    assert body.get("success") is True, body.get("error")
    brands = [(p.get("brand"), p.get("name")) for p in body["overview"]["products"]]
    assert brands == [
        ("Emporio Armani", "Stronger With You"),
        ("Bvlgari", "Tygar"),
    ], brands
    # no private key beyond the ones the flag-OFF payload already carries (_debug_capture
    # rides the products at the base: measured), and never the Step-1 `_explicit` marker
    on_keys = sorted(_underscore_keys(payload, []))
    off_keys = sorted(_underscore_keys(off_payload, []))
    assert on_keys == off_keys, (on_keys, off_keys)
    assert "_explicit" not in on_keys, on_keys


def _second_skin_lines(tmp_path):
    data = json.loads(
        (ROOT / "data" / "fragrance_lines.json").read_text(encoding="utf-8")
    )
    data["lines"].append(
        {
            "house": "Acme",
            "house_aliases": ["acme"],
            "line": "Second Skin",
            "aliases": ["second skin"],
            "concentrations": ["EDT"],
            "base": "EDT",
            "flankers": [],
        }
    )
    path = tmp_path / "fragrance_lines_second_skin.json"
    path.write_text(json.dumps(data), encoding="ascii")
    return path


@pytest.mark.parametrize("case", ["owner", "second_skin"])
@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_r04_pair_category(monkeypatch, tmp_path, kind, case):
    """R04 (R1-8 / P5; C-1 by kind): a resolved pair is fragrances with NO classifier call,
    through parser_path=True; the stamp alone would give skincare for 'Second Skin'."""
    pr = _pr()
    _full(monkeypatch)
    pair = OWNER
    if case == "second_skin":
        monkeypatch.setattr(pr, "LINES_PATH", _second_skin_lines(tmp_path))
        pair = ("Acme Second Skin EDT", "Tyger")
    calls = {"n": 0}

    def _count(p, _svc, _state):
        async def _cat(*_a, **_k):
            calls["n"] += 1
            return "electronics"

        p.setattr(scs, "classify_category_llm", _cat)

    _payload, state, _svc = _run(kind, pair, extra=_count)
    cats = [p["category"] for p in state["fetch_products"]]
    assert cats == ["fragrances", "fragrances"], state["fetch_products"]
    assert calls["n"] == 0, calls
    assert [entry[1] for entry in state["resolve"]] == [True], state["resolve"]


def _ask_spies(p, svc, state):
    state["profile_calls"] = 0
    state["card_calls"] = 0

    async def _profile(*_a, **_k):
        state["profile_calls"] += 1
        return None

    async def _demo(*_a, **_k):
        return None

    async def _cards(*_a, **_k):
        state["card_calls"] += 1
        return [None, None]

    svc._fetch_behavior_profile = _profile
    p.setattr(scs, "get_user_demographics", _demo)
    p.setattr(kb_serve, "fetch_cards", _cards)


def _assert_refusal_dict(body, *, request_id=False):
    keys = REFUSAL_KEYS + (["request_id"] if request_id else [])
    assert list(body) == keys, list(body)
    assert body["success"] is False and body["error"] == ASK_MESSAGE
    assert (
        body["code"] == "INSUFFICIENT_DATA" and body["reason"] == "placeholder_identity"
    )
    assert isinstance(body["elapsed_seconds"], float) and body["elapsed_seconds"] >= 0
    assert body["total_cost"] >= 0 and body["api_calls"] == 1, body
    cands = body["candidates"]
    assert isinstance(cands, list) and len(cands) == 2, cands
    assert cands[0] == [TF_CAND], cands
    for side in cands:
        assert len(side) <= 4
        for item in side:
            assert set(item) == {"brand", "line", "concentration"}, item


def test_r05_sync_ask_before_any_fetch(monkeypatch):
    """R05 (2.8): a fragrance-intended pair with an unresolved side is refused BEFORE the pair
    category, the profile task, the KB task and any fetch; the resolver's usage is tracked.
    """
    _full(monkeypatch)
    monkeypatch.setenv(KBF, "true")
    ANTH.default = c_msg(ASK_ANSWER)
    payload, state, _svc = _run(
        "rest", ASK_PAIR, user_id="inc-r1-user", extra=_ask_spies
    )
    _assert_refusal_dict(payload)
    assert state["fetch_products"] == [] and state["resolve"] == []
    assert state["profile_calls"] == 0 and state["card_calls"] == 0, state
    assert state["track_gpt"] == 1, state["track_gpt"]


def test_r06_stream_ask_error_event(monkeypatch):
    """R06 (R1-7c): the stream refusal is a terminal `error` event, never a terminal payload."""
    _full(monkeypatch)
    ANTH.default = c_msg(ASK_ANSWER)
    events, state, _svc = _run("stream", ASK_PAIR)
    kinds = [e[0] for e in events]
    assert kinds == ["status", "error"], kinds
    assert events[0][1] == {"message": "Parsing query...", "progress": 10}
    _assert_refusal_dict(events[1][1])
    assert state["fetch_products"] == []


# ======================================================================= R07-R09 the routes


class L(rw.Ledger):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.persist = []
        self.budget_reads = []
        self.budget_records = []

    def log_search(self, **kw):
        self.rows.append(dict(kw))
        return super().log_search(**kw)


def _ledger(monkeypatch, *, spent=None):
    led = L()
    rw._install(monkeypatch, led, text_routes)
    monkeypatch.setattr(text_routes, "log_search", led.log_search, raising=False)

    async def _prefs(_uid):
        return {"success": False}

    monkeypatch.setattr(text_routes, "get_user_preferences", _prefs)

    async def _persist(**kw):
        led.persist.append(kw.get("input_type"))
        return "inc-r1-row-id"

    monkeypatch.setattr(text_routes, "_persist_comparison_bounded", _persist)
    monkeypatch.setattr(text_routes, "track_after_persist", lambda *a, **k: rw._done())

    async def _state(subject):
        led.budget_reads.append(subject)
        if isinstance(spent, list):
            return spent.pop(0) if spent else None
        return spent

    async def _record(subject):
        led.budget_records.append(subject)

    monkeypatch.setattr(cg, "budget_state_async", _state)
    monkeypatch.setattr(cg, "record_refusal_async", _record)
    return led


@pytest.fixture
def client():
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {
        "id": ("inc-r1-" + request.node.name)[:120],
        "email": "inc-r1@example.test",
        "access_token": "inc-r1-synthetic",
    }
    fastapi_app.dependency_overrides[get_optional_user] = lambda: user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture
def fy_service(monkeypatch):
    p = fy._Patcher()
    state = fy._new_state()

    async def _none(*_a, **_k):
        return None

    def _factory():
        svc = scs.StructuredComparisonService()
        fy._install(p, svc, state)
        svc._fetch_behavior_profile = _none
        p.setattr(scs, "get_user_demographics", _none)
        return svc

    monkeypatch.setattr(text_routes, "get_comparison_service", _factory)
    try:
        yield state
    finally:
        p.undo()


def _route_on(monkeypatch):
    _full(monkeypatch)
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    monkeypatch.setenv(AUTHREQ, "true")
    ANTH.default = c_msg(ASK_ANSWER)


def _keys(uid):
    return {"daily": "d:" + uid, "monthly": "m:" + uid}


def _assert_ask_ledger(led, uid, *, refund=True):
    assert led.consumes == [uid], led.consumes
    if refund:
        assert led.refunds == [uid], led.refunds
        assert led.refund_keys == [_keys(uid)], led.refund_keys
    else:
        assert led.refunds == [], led.refunds
    assert led.lifetime == [] and led.history == [] and led.persist == [], led
    assert len(led.rows) == 1 and led.rows[0].get("success") is False, led.rows
    assert led.log_success == [False], led.log_success


def _assert_ask_400(resp):
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert list(body) == ENVELOPE_KEYS + ["reason", "candidates"], list(body)
    assert body["success"] is False and body["error"] == ASK_MESSAGE
    assert (
        body["code"] == "INSUFFICIENT_DATA" and body["reason"] == "placeholder_identity"
    )
    assert body["candidates"] == [[TF_CAND], []], body["candidates"]


def test_r07_get_route_ask(monkeypatch, client, authed, fy_service):
    """R07 (+ R1-R9): GET: a coded 400 with the additive reason and candidates; ONE consume,
    ONE refund WITH the consume's keys, no lifetime, no history, one failure row."""
    _route_on(monkeypatch)
    led = _ledger(monkeypatch)
    resp = client.get(
        "/api/v1/text/compare",
        params={"product_a": ASK_PAIR[0], "product_b": ASK_PAIR[1]},
    )
    _assert_ask_400(resp)
    _assert_ask_ledger(led, authed["id"])
    assert fy_service["fetch_products"] == []


def test_r08_post_route_ask(monkeypatch, client, authed, fy_service):
    """R08 (+ R1-R9): the POST twin."""
    _route_on(monkeypatch)
    led = _ledger(monkeypatch)
    resp = client.post(
        "/api/v1/text/compare",
        json={"product_a": ASK_PAIR[0], "product_b": ASK_PAIR[1]},
    )
    _assert_ask_400(resp)
    _assert_ask_ledger(led, authed["id"])
    assert fy_service["fetch_products"] == []


def _frames(text):
    out = []
    for block in text.split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln]
        if not lines:
            continue
        ev = next(
            (ln[len("event: ") :] for ln in lines if ln.startswith("event: ")), None
        )
        data = [ln[len("data: ") :] for ln in lines if ln.startswith("data: ")]
        out.append((ev, json.loads(data[-1]) if data else None))
    return out


def test_r09_stream_route_ask(monkeypatch, client, authed, fy_service):
    """R09 (+ R1-R9): one `event: error` frame carrying the refusal dict plus request_id; no
    terminal payload; ONE refund with the consume's keys; no lifetime, no history."""
    _route_on(monkeypatch)
    led = _ledger(monkeypatch)
    resp = client.get(
        "/api/v1/text/compare/stream",
        params={"product_a": ASK_PAIR[0], "product_b": ASK_PAIR[1]},
    )
    frames = _frames(resp.text)
    kinds = [e for e, _d in frames]
    assert "complete" not in kinds and "settle_complete" not in kinds, kinds
    errors = [d for e, d in frames if e == "error"]
    assert len(errors) == 1, frames
    _assert_refusal_dict(errors[0], request_id=True)
    _assert_ask_ledger(led, authed["id"])


# ======================================================================= R10-R11 the two gates


def _envelope(detail, status=400):
    req = types.SimpleNamespace(state=types.SimpleNamespace(request_id="rid-inc-r1"))
    resp = asyncio.run(
        eh.http_exception_handler(req, HTTPException(status, detail=detail))
    )
    return json.loads(resp.body)


def _marker(cands=None):
    return {
        "code": "INSUFFICIENT_DATA",
        "error": ASK_MESSAGE,
        "reason": "placeholder_identity",
        "candidates": copy.deepcopy(GOOD_CANDS if cands is None else cands),
    }


BAD_CANDS = [
    ("three_lists", [[], [], []]),
    ("five_items", [[dict(TF_CAND)] * 5, []]),
    ("extra_key", [[dict(TF_CAND, x=1)], []]),
    ("long_line", [[dict(TF_CAND, line="L" * 81)], []]),
    ("control_char", [[dict(TF_CAND, line="A" + chr(10) + "B")], []]),
    ("unknown_concentration", [[dict(TF_CAND, concentration="Cologne Intense")], []]),
]


@pytest.mark.parametrize(
    "rg,pr_on,want",
    [
        (False, False, ENVELOPE_KEYS),
        (True, False, ENVELOPE_KEYS + ["reason"]),
    ],
    ids=["pin_rg_off_pr_off", "pin_rg_on_pr_off"],
)
def test_r10_envelope_pin(monkeypatch, rg, pr_on, want):
    """R10 PIN cases: the base envelope with the FULL configuration and the flag OFF."""
    _full(monkeypatch, "true" if pr_on else "false")
    if rg:
        monkeypatch.setenv(RG, "true")
    body = _envelope(_marker())
    assert list(body) == want, list(body)


@pytest.mark.parametrize("rg", [False, True], ids=["red_pr_on", "red_rg_on_pr_on"])
def test_r10_envelope_red(monkeypatch, rg):
    """R10 RED cases (R1-R18): under the flag the ask's reason and validated candidates pass."""
    _full(monkeypatch)
    if rg:
        monkeypatch.setenv(RG, "true")
    body = _envelope(_marker())
    assert list(body) == ENVELOPE_KEYS + ["reason", "candidates"], list(body)
    assert body["reason"] == "placeholder_identity"
    assert body["candidates"] == GOOD_CANDS


@pytest.mark.parametrize("cid,cands", BAD_CANDS, ids=[c[0] for c in BAD_CANDS])
def test_r10_envelope_bad_candidates_dropped(monkeypatch, cid, cands):
    """R10 PIN: a malformed candidates value never reaches the wire (dropped whole)."""
    _full(monkeypatch)
    body = _envelope(_marker(cands))
    assert "candidates" not in body, body


@pytest.mark.parametrize("code,status", [("TIMEOUT", 503), ("CATEGORY_NOT_LIVE", 400)])
def test_r10_envelope_other_codes(monkeypatch, code, status):
    """R10 PIN: another code carrying the same keys gets no reason / candidates from INC-R1."""
    _full(monkeypatch)
    detail = dict(_marker(), code=code)
    body = _envelope(detail, status)
    assert "reason" not in body and "candidates" not in body, body


@pytest.mark.parametrize(
    "detail,status",
    [
        ("Not found", 404),
        ({"code": "TIMEOUT", "error": "Comparison timed out."}, 503),
        ({"code": "USAGE_LIMIT", "error": "Comparison limit reached (daily)"}, 429),
    ],
    ids=["string_404", "timeout_503", "usage_429"],
)
def test_r10_envelope_no_flag_read_without_the_marker(monkeypatch, detail, status):
    """R10 PIN (R1-R18 / RC-2): the envelope reads ENABLE_PRODUCT_RESOLVER only after the
    refusal marker matches: never for a string detail or another code."""
    _full(monkeypatch)
    rec = Recorders(monkeypatch)
    _envelope(detail, status)
    monkeypatch.setattr(os, "getenv", os.environ.get)
    assert FLAG not in rec.names, rec.names


ASK_BODY = {
    "success": False,
    "error": ASK_MESSAGE,
    "code": "INSUFFICIENT_DATA",
    "elapsed_seconds": 0.5,
    "total_cost": 0.0,
    "api_calls": 1,
    "reason": "placeholder_identity",
    "candidates": GOOD_CANDS,
}
H6_BODY = {"success": False, "error": H6_MESSAGE, "code": "INSUFFICIENT_DATA"}


def _builder(result):
    try:
        text_routes._surface_comparison_failure(copy.deepcopy(result))
    except HTTPException as exc:
        return exc.status_code, exc.detail
    return None, None


R11_CASES = [
    (
        "pin_pr_off",
        "false",
        False,
        ASK_BODY,
        {"code": "INSUFFICIENT_DATA", "error": ASK_MESSAGE},
    ),
    (
        "pin_rg_on_pr_off",
        "false",
        True,
        ASK_BODY,
        {
            "code": "INSUFFICIENT_DATA",
            "error": ASK_MESSAGE,
            "reason": "placeholder_identity",
        },
    ),
    (
        "pin_h6_pr_on",
        "true",
        False,
        H6_BODY,
        {"code": "INSUFFICIENT_DATA", "error": H6_MESSAGE},
    ),
    (
        "red_pr_on",
        "true",
        False,
        ASK_BODY,
        {
            "code": "INSUFFICIENT_DATA",
            "error": ASK_MESSAGE,
            "reason": "placeholder_identity",
            "candidates": GOOD_CANDS,
        },
    ),
    (
        "red_rg_on_pr_on",
        "true",
        True,
        ASK_BODY,
        {
            "code": "INSUFFICIENT_DATA",
            "error": ASK_MESSAGE,
            "reason": "placeholder_identity",
            "candidates": GOOD_CANDS,
        },
    ),
]


@pytest.mark.parametrize(
    "case,flag,rg,body,want", R11_CASES, ids=[c[0] for c in R11_CASES]
)
def test_r11_builder_flag_mix(monkeypatch, case, flag, rg, body, want):
    """R11 (R1-R18): the 400 builder; PIN cases green at the base, RED cases under the flag."""
    _full(monkeypatch, flag)
    if rg:
        monkeypatch.setenv(RG, "true")
    status, detail = _builder(body)
    assert status == 400, (status, detail)
    assert detail == want, detail
    assert list(detail) == list(want), list(detail)


# ======================================================================= R12-R16


def test_r12_consent2_owner_still_rewritten(monkeypatch):
    """R12 RED half (R1-R6): below consent 3 the deterministic arm still rewrites the owner's
    pair, with no call."""
    _full(monkeypatch, consent=2)
    monkeypatch.setenv(EGRESS, "true")
    _payload, state, _svc = _run("rest", OWNER, chip="fragrances")
    assert state["fetch_products"] == [OWNER_A, OWNER_B], state["fetch_products"]
    assert ANTH.calls == [] and OAI_CALLS == []


def test_r12b_consent2_model_pair_as_today(monkeypatch):
    """R12 PIN half (R1-R6): consent 2, TEXT / PRE_V3 / the egress stop ON: an unseeded pair
    makes no route call and no create and runs exactly as today (a success, no 400)."""
    _full(monkeypatch, consent=2)
    monkeypatch.setenv(EGRESS, "true")
    rec = Recorders(monkeypatch)
    payload, state, _svc = _run("rest", MODEL_PAIR)
    monkeypatch.setattr(os, "getenv", os.environ.get)
    assert ANTH.calls == [] and OAI_CALLS == []
    assert "resolve" not in rec.sites, rec.sites
    assert state["fetch_products"] == BASE_FETCH_MODEL_PAIR, state["fetch_products"]
    assert payload.get("success") is True, payload.get("error")


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_r13_model_arm_through_the_seam(monkeypatch, kind):
    """R13 (C-1 by kind; R1-R23): the model arm resolves an unseeded pair (no concentration
    typed, no seed entry -> none); its usage is one more tracked call."""
    _full(monkeypatch)
    _payload, owner_state, owner_svc = _run(kind, OWNER, chip="fragrances")
    ANTH.default = c_msg(MODEL_ANSWER)
    _payload, state, svc = _run(kind, MODEL_PAIR, chip="fragrances")
    assert len(ANTH.calls) == 1, ANTH.calls
    got = [
        (p["brand"], p["name"], p["variant"], p["search_query"])
        for p in state["fetch_products"]
    ]
    assert got == [
        ("Tom Ford", "Ombre Leather", None, "Tom Ford Ombre Leather"),
        ("Montblanc", "Explorer", None, "Montblanc Explorer"),
    ], got
    assert svc.api_calls == owner_svc.api_calls + 1, (
        svc.api_calls,
        owner_svc.api_calls,
    )
    assert state["track_gpt"] == owner_state["track_gpt"] + 1


def test_r13b_model_arm_in_the_llm_ledger(monkeypatch):
    """R13: with ENABLE_LLM_LEDGER_V2 ON the payload's metadata.llm counts the resolve call."""
    _full(monkeypatch)
    monkeypatch.setenv(LEDGER, "true")
    owner, _s, _v = _run("rest", OWNER, chip="fragrances")
    ANTH.default = c_msg(MODEL_ANSWER)
    model, _s, _v = _run("rest", MODEL_PAIR, chip="fragrances")
    base_calls = ((owner.get("metadata") or {}).get("llm") or {}).get("calls", 0)
    llm = (model.get("metadata") or {}).get("llm") or {}
    assert llm.get("calls") == base_calls + 1, (llm, base_calls)


def test_r14_partial_on_timeout(monkeypatch, caplog):
    """R14 (R1-7d / R1-R7): a cut call is no verdict: no refusal; the lexicon side is rewritten,
    the other runs as typed; the [RESOLVE] line says partial."""
    _full(monkeypatch, timeout="0.05")
    ANTH.default = c_msg(ASK_ANSWER)
    ANTH.delay = 2.0
    with caplog.at_level(logging.INFO):
        payload, state, _svc = _run("rest", ASK_PAIR)
    assert payload.get("success") is True, payload.get("error")
    assert state["fetch_products"] == [
        _explicit(ASK_PAIR[0], "fragrances"),
        DIOR_EDP,
    ], state["fetch_products"]
    lines = [
        r.getMessage() for r in _resolve_records(caplog) if r.levelno == logging.INFO
    ]
    assert len(lines) == 1 and "outcome=partial" in lines[0], lines


@pytest.mark.parametrize("flag", ["true", "false"], ids=["red_flag_on", "pin_flag_off"])
def test_r15_kb_first_serve_sees_identity(monkeypatch, flag):
    """R15: with ENABLE_KB_FIRST_SERVE ON the card read receives the rewritten dicts (a KB id
    can be minted); flag OFF (PIN) the base dicts (brand '', no id)."""
    _full(monkeypatch, flag)
    monkeypatch.setenv(KBF, "true")
    seen = []

    def _spy(p, _svc, _state):
        async def _cards(products, _lang):
            seen.append([dict(x) for x in products])
            return [None, None]

        p.setattr(kb_serve, "fetch_cards", _cards)

    _run("rest", OWNER, chip="fragrances", extra=_spy)
    assert len(seen) == 1, seen
    ids = [
        kb_service.kb_product_id(p["brand"], p["name"], p["variant"]) for p in seen[0]
    ]
    if flag == "true":
        assert [p["brand"] for p in seen[0]] == ["Emporio Armani", "Bvlgari"], seen[0]
        assert all(i is not None for i in ids), ids
    else:
        assert [p["brand"] for p in seen[0]] == ["", ""], seen[0]
        assert ids == [None, None], ids


class _ResolverRecorder:
    """Installed as structured_comparison_service._product_resolver (raising=False): any
    resolver call from an out-of-scope entry is recorded."""

    OUTCOME_ASK = "ask"

    def __init__(self):
        self.calls = []

    def product_resolver_enabled(self):
        return True

    async def resolve_pair(self, names, **kwargs):
        self.calls.append(list(names))
        return types.SimpleNamespace(outcome="passthrough", usage=None, sides=())

    def apply_resolution(self, products, resolution):
        self.calls.append("apply")
        return False

    def refusal_result(self, *a, **k):
        self.calls.append("refusal")
        return {}


@pytest.mark.parametrize("entry", ["q", "vision", "presplit"])
def test_r16_other_entries_untouched(monkeypatch, entry):
    """R16 PIN (R1-1, R1-R22): the q= path, the camera's vision path and the flagged q= pre-split
    never reach the resolver; their Step-1 dicts equal the base."""
    _full(monkeypatch)
    rec = _ResolverRecorder()
    monkeypatch.setattr(scs, "_product_resolver", rec, raising=False)
    if entry == "q":
        _payload, state, _svc = _run("rest", query="stronger with you vs Tyger")
        want = BASE_FETCH_Q
    elif entry == "vision":
        _payload, state, _svc = _run(
            "rest", query="Dior Sauvage vs Bleu de Chanel", vision=VISION
        )
        want = BASE_FETCH_VISION
    else:
        monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
        _payload, state, _svc = _run("rest", query="stronger with you vs Tyger")
        want = BASE_FETCH_PRESPLIT
    assert rec.calls == [], rec.calls
    assert state["fetch_products"] == want, state["fetch_products"]


# ======================================================================= R17-R18 docs and lint


def test_r17_claude_md_block_and_pointer():
    """R17 (+ R1-R12): the INC-R1 block after the S81-07c block and before '## Tests', and the
    pointer sentence in the '**Feature Flags:**' line after the S81-07c sentence."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    heading = "**INCIDENT LANE unit (INC-R1 RESOLVE-OR-ASK"
    s07c = next(
        i
        for i, ln in enumerate(lines)
        if ln.startswith("**SESSION 81 follow-up unit (S81-07c")
    )
    tests_at = next(i for i, ln in enumerate(lines) if ln.startswith("## Tests"))
    starts = [i for i, ln in enumerate(lines) if ln.startswith(heading)]
    assert (
        len(starts) == 1
    ), "the INC-R1 block heading (column 0) is missing or repeated"
    start = starts[0]
    assert s07c < start < tests_at, (s07c, start, tests_at)
    block = []
    for ln in lines[start:tests_at]:
        if block and (ln.startswith("**SESSION") or ln.startswith("**INCIDENT")):
            break
        block.append(ln)
    block_text = "\n".join(block)
    for needle in (
        "ENABLE_PRODUCT_RESOLVER",
        "PRODUCT_RESOLVER_TIMEOUT_SECONDS",
        "PRODUCT_RESOLVER_ASK",
        "[RESOLVE]",
        "resolve",
        "resolved",
        "partial",
        "ask",
        "passthrough",
        "rollback",
    ):
        assert needle in block_text, needle
    for phrase in (
        "defeats most Cloudflare",
        "cracks Akamai",
        "residential proxies, only when",
        "#93 specifies 20+ samples",
        "controls curl cracks",
    ):
        assert phrase not in text, phrase
    flags_line = next(ln for ln in lines if ln.startswith("**Feature Flags:**"))
    assert "`ENABLE_PRODUCT_RESOLVER`" in flags_line
    assert "INC-R1 RESOLVE-OR-ASK" in flags_line
    assert flags_line.index("`ENABLE_PRODUCT_RESOLVER`") > flags_line.index(
        "S81-07c CLAUDE-ROLE-FIX"
    )
    assert all(ord(ch) < 128 for ch in block_text)


def test_r18_black_allowlist():
    """R18 (R1-R17): the resolver and both RED files are on the BLOCKING black allowlist."""
    listed = {
        ln.strip()
        for ln in (ROOT / ".github" / "black-clean-paths.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }
    for path in (
        "app/services/product_resolver.py",
        "tests/test_inc_r1_resolver.py",
        "tests/test_inc_r1_seam.py",
    ):
        assert path in listed, path


# ======================================================================= R19-R20


@pytest.mark.parametrize("case", ["apply_raises", "refusal_raises"])
def test_r19_hook_is_total(monkeypatch, caplog, case):
    """R19 (C-7): an exception in apply_resolution or refusal_result never reaches the
    orchestrator: the hook falls back to the base dicts, ONE WARNING naming the type only.
    """
    pr = _pr()
    _full(monkeypatch)
    sentinel = "Hk" + "Snt" + "z4"
    if case == "apply_raises":

        def _apply(products, _r):
            products[0]["brand"] = "Mutated"
            raise RuntimeError(sentinel)

        monkeypatch.setattr(pr, "apply_resolution", _apply)
        pair, want = OWNER, BASE_FETCH_OWNER_NOCHIP
    else:
        ANTH.default = c_msg(ASK_ANSWER)

        def _refusal(*_a, **_k):
            raise RuntimeError(sentinel)

        monkeypatch.setattr(pr, "refusal_result", _refusal)
        pair, want = ASK_PAIR, BASE_FETCH_ASK_PAIR
    with caplog.at_level(logging.INFO):
        payload, state, _svc = _run("rest", pair)
    assert payload.get("success") is True, payload.get("error")
    assert state["fetch_products"] == want, state["fetch_products"]
    warn = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "RuntimeError" in r.getMessage()
    ]
    assert len(warn) == 1, [
        r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING
    ]
    for r in caplog.records:
        assert sentinel not in r.getMessage() + repr(r.args), r.getMessage()


@pytest.mark.parametrize("gate", ["off", "on_open", "on_spent"])
def test_r20_refusal_budget(monkeypatch, client, authed, fy_service, gate):
    """R20 (R1-R10): with ENABLE_FRAGRANCE_ONLY_GATE ON an ask is counted on the S81-10 refusal
    budget exactly as S81-20 counts its refusals (spent keeps the credit); OFF nothing is read
    or counted."""
    _route_on(monkeypatch)
    spent = None
    if gate != "off":
        monkeypatch.setenv(FRAG, "true")
    if gate == "on_spent":
        spent = [None, (3600, "2026-11-15T00:00:00+03:00")]
    led = _ledger(monkeypatch, spent=spent)
    resp = client.get(
        "/api/v1/text/compare",
        params={"product_a": ASK_PAIR[0], "product_b": ASK_PAIR[1]},
    )
    _assert_ask_400(resp)
    if gate == "off":
        _assert_ask_ledger(led, authed["id"])
        assert led.budget_reads == [] and led.budget_records == []
    elif gate == "on_open":
        _assert_ask_ledger(led, authed["id"])
        assert len(led.budget_records) == 1, led.budget_records
    else:
        _assert_ask_ledger(led, authed["id"], refund=False)
        assert led.budget_records == [], led.budget_records


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_r21_hook_passes_the_chip(monkeypatch, kind):
    """R21 (R1-R8 through the seam): the hook hands the request's chip to the resolver: with
    the Fragrances chip a fuzzy single-token line resolves next to an unresolved partner.
    """
    _full(monkeypatch, text=False)
    _payload, state, _svc = _run(kind, ("Tyger", "iPhone 15"), chip="fragrances")
    assert state["fetch_products"][0] == OWNER_B, state["fetch_products"]
    assert state["fetch_products"][1]["brand"] == "", state["fetch_products"]
    assert state["fetch_products"][1]["name"] == "iPhone 15", state["fetch_products"]

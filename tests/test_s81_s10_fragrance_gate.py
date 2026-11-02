"""S81-10 FRAGRANCE-ONLY-GATE: the RED + PIN rows (ENABLE_FRAGRANCE_ONLY_GATE, default OFF).

Contract: the unit spec (.qa-s80/S81-10_UNIT_SPEC.md of the unit worktree) as amended
by its adversarial review (C1-C30) and RULINGS_S81_10 (R-S10-1..R-S10-16 + the
measurement rulings; the rulings win). Base 6c14ac95. Every RED row fails at the base
on an AssertionError only (missing symbols are read through `_gate_or_fail()` /
getattr and asserted); every PIN row is green at the base and runs with the FULL
configuration (flag OFF, every knob set, a device header bound, a Redis fake seeded
ABOVE the budget for both subjects) plus call recorders (ruling B1).

Seams this file names for GREEN (R-S10-11; the S81-09 helpers replace them at the
rebase, no new behaviour):
  * category_gate.reset_window(now) -> (day: date, next_reset: aware datetime, utc_offset_hours: int)
      = usage_service._usage_window(now) (+ the S81-09 Riyadh offset) when S81-09 is
      merged, else the UTC-midnight fallback (day = now UTC date, next = next UTC
      midnight, offset 0);
  * category_gate.budget_exempt_async(user_id) -> bool
      = the DEVICE_QUOTA_EXEMPT_USER_IDS allow-list (S81-09 parsing) or a premium
      subscription_tier read through usage_service._get_user_tier_info (read only
      when a budget is spent); S81-09's _device_quota_exempt replaces the allow-list
      half at the rebase.
Other names pinned: FLAG_ENV, BUDGET_ENV, LEXICON_ENV, fragrance_only_gate_enabled,
refusal_daily_budget, lexicon_path, load_lexicon, _reset_lexicon_cache, normalize,
scan, evaluate, kb_evidence, budget_subject, budget_keys, retry_fields,
budget_state_async, record_refusal_async, REFUSAL_INCR_SCRIPT, refusal_result,
refusal_detail, budget_detail, CODE, CATEGORIES_LIVE, SCOPE_REFUSAL_DAILY,
REFUSAL_MESSAGE, BUDGET_MESSAGE, KEY_PREFIX_DEV, KEY_PREFIX_ACCT, GateDecision,
ScanResult; error_handler._CANONICAL_CATEGORY_KEYS.

Decision semantics pinned (rulings over spec):
  * rule 1 ($0, pre-consume): a non-fragrance product-type word, no fragrance
    product-type word (concentration / form) AND no house or note hit (R-S10-4);
    a house / note hit beside it proceeds with evidence False (the classifier
    decides post-resolve);
  * evidence = (form/concentration or a house or two distinct notes or the KB seam)
    and not (a non-fragrance word without a form/concentration);
  * post-resolve (only when the route passed `fragrance_gate`): per product, a
    form/concentration hit in the product's own name makes it a fragrance on the
    explicit / vision paths (R-S10-5); any product whose chip-free category is a
    POSITIVE non-fragrance refuses (R-S10-6); 'other' always proceeds (R-S10-3);
    blind explicit / vision pairs without evidence are decided by ONE A2b call
    (reusing the resolver's when it already ran, C11); the parser path never calls
    A2b;
  * the budget has two axes (R-S10-1): the account key always, the device key in
    addition when the S81-05 device key is bound; either at the budget -> 429; one
    EVAL increments both with the same EXPIREAT;
  * the admin-key path bypasses the gate (R-S10-8); History stays whole (R-S10-10).

Golden: tests/fixtures/s81_s10_flag_off_golden.json, recorded at the base with the
flag unset and the full configuration (12 scenarios: the spec's G01-G11 + G12 the
admin-key POST of R-S10-8). Re-record only deliberately:
S81_S10_RECORD_GOLDEN=1 makes P01 (unset spelling) write the fixture and FAIL.

Hermetic: no network, no .env read, every user id / fingerprint / pepper / admin
credential synthetic and built at run time; pure ASCII (Arabic built from code points).
"""
from __future__ import annotations

import ast
import asyncio
import dataclasses
import importlib
import importlib.util
import inspect
import json
import logging
import os
import re
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request as _StarletteRequest

# C5 / C20: app.main FIRST (setup_logging clears the root handlers and the dotenv
# guard strips CREDENTIALS_UNSET at import); caplog and monkeypatch.setenv come after.
import app.main as app_main
from app.api import history_routes, home_routes, image_routes, text_routes
from app.api.auth_routes import get_current_user, get_optional_user
from app.middleware import error_handler
from app.services import (
    audit_service,
    cache_service,
    content_safety_service,
    extraction_service,
    structured_comparison_service as scs,
    usage_service,
)
from app.utils import request_context

APP = app_main.app
ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "tests" / "fixtures" / "s81_s10_flag_off_golden.json"
GATE_MOD = "app.services.category_gate"
GATE_FILE = ROOT / "app" / "services" / "category_gate.py"
LEXICON_FILE = ROOT / "data" / "fragrance_lexicon.json"
FLAG = "ENABLE_FRAGRANCE_ONLY_GATE"
BUDGET = "REFUSAL_DAILY_BUDGET"
LEXP = "FRAGRANCE_LEXICON_PATH"
OFF_SPELLINGS = [None, "false", "0", "off", ""]
OFF_IDS = ["unset", "false", "0", "off", "empty"]
ON_SPELLINGS = ["true", " TRUE ", "1", "yes", "On"]
CODE = "CATEGORY_NOT_LIVE"
REFUSAL_MESSAGE = "MYEZ compares fragrances for now. Other categories are coming soon."
BUDGET_MESSAGE = "MYEZ compares fragrances for now. The daily limit for other searches is reached."
CANONICAL = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)
NON_FRAGRANCE = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fashion")
GATE_LOGGER = "app.services.category_gate"
GOLDEN_LOGGERS = (
    "app.api.text_routes", "app.api.image_routes", "app.api.version_routes",
    "app.api.home_routes", "app.middleware.error_handler",
)
LOG_GRAMMAR = re.compile(
    r"^\[CATEGORY-GATE\] (?:"
    r"refused stage=(?:pre_consume|post_vision|post_resolve) category=(?:"
    + "|".join(CANONICAL)
    + r")(?: route=(?:text\.post|text\.get|text\.stream|image))?"
    r"|budget spent stage=pre_consume route=(?:text\.post|text\.get|text\.stream|image)"
    r"|(?:lexicon unavailable|budget read fail-open|budget record failed|kb lookup failed) type=[A-Za-z_][A-Za-z0-9_]*"
    r")$"
)


# ---------------------------------------------------------------------------
# synthetic values (built at run time; never a real person, device or credential)
# ---------------------------------------------------------------------------
def _join(*parts):
    return "".join(parts)


UID = "-".join(["facefeed", "beef", "4bad", "8cab", "deadbeefcafe"])
UID2 = "-".join(["cafebabe", "feed", "4ace", "8bed", "facadebeaded"])
FP = "5a10" * 16
FP2 = "a5e1" * 16
PEPPER_VALUE = _join("s10", "-synthetic-", "pepper")
ADMIN_VALUE = _join("s10", "-synthetic-", "adm", "in")
SENTINEL = _join("zz", "s10", "sentinel")
ACCESS = _join("tok", "-s10-synthetic")
DAY = date(2026, 10, 29)
DAY_TXT = "2026-10-29"
USER = {"id": UID, "email": _join("s10", "@example.test"), "access_token": ACCESS}
USER2 = {"id": UID2, "email": _join("s10b", "@example.test"), "access_token": ACCESS}
JPEG = b"\xff\xd8" + b"\x00" * 64


def _ar(*cps):
    return "".join(chr(c) for c in cps)


AR_SHAMPOO = _ar(0x0634, 0x0627, 0x0645, 0x0628, 0x0648)
AR_ITR = _ar(0x0639, 0x0637, 0x0631)
AR_WARD = _ar(0x0648, 0x0631, 0x062F)
AR_OUD = _ar(0x0639, 0x0648, 0x062F)
AR_MISK = _ar(0x0645, 0x0633, 0x0643)
AR_BARFAN = _ar(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646)
AR_LATTAFA = _ar(0x0644, 0x0637, 0x0627, 0x0641, 0x0629)
AR_AMWAJ = _ar(0x0623, 0x0645, 0x0648, 0x0627, 0x062C)
AR_JAWWAL = _ar(0x062C, 0x0648, 0x0627, 0x0644)
AR_TAAM = _ar(0x0637, 0x0639, 0x0627, 0x0645)
AR_FITAMIN = _ar(0x0641, 0x064A, 0x062A, 0x0627, 0x0645, 0x064A, 0x0646)
AR_MIKYAJ = _ar(0x0645, 0x0643, 0x064A, 0x0627, 0x062C)
AR_KRIM = _ar(0x0643, 0x0631, 0x064A, 0x0645)
AR_HAQIBA = _ar(0x062D, 0x0642, 0x064A, 0x0628, 0x0629)
AR_AL = _ar(0x0627, 0x0644)

EN_CONCENTRATIONS = [
    "eau de parfum", "eau de toilette", "eau de cologne", "extrait de parfum", "parfum",
    "edp", "edt", "edc", "extrait", "elixir",
]
EN_FORMS = [
    "perfume", "perfumes", "fragrance", "fragrances", "cologne", "colognes", "scent", "scents",
    "body mist", "body spray", "hair mist", "perfume oil", "attar", "oud oil",
]
EN_HOUSES = [
    "chanel", "dior", "tom ford", "creed", "yves saint laurent", "ysl", "giorgio armani",
    "versace", "gucci", "prada", "hermes", "guerlain", "jo malone", "maison francis kurkdjian",
    "byredo", "le labo", "parfums de marly", "initio", "amouage", "lattafa", "armaf", "ajmal",
    "rasasi", "swiss arabian", "arabian oud", "abdul samad al qurashi", "al haramain", "afnan",
    "montale", "mancera", "kilian", "xerjoff", "nishane", "givenchy", "paco rabanne",
    "carolina herrera", "jean paul gaultier", "burberry", "bvlgari", "montblanc",
]
EN_NOTES = [
    "oud", "musk", "amber", "vanilla", "rose", "jasmine", "sandalwood", "vetiver", "patchouli",
    "bergamot", "tonka", "iris", "neroli", "saffron", "leather", "incense", "lavender", "cedar",
]
EN_NON = {
    "electronics": [
        "phone", "phones", "smartphone", "smartphones", "mobile", "laptop", "laptops", "tablet",
        "tablets", "tv", "television", "camera", "headphones", "earbuds", "console", "smartwatch",
        "air conditioner", "refrigerator", "fridge", "washing machine", "dryer", "dishwasher",
        "microwave",
    ],
    "grocery": ["food", "beverage", "drink", "snack", "rice", "ice cream", "detergent", "cleaning"],
    "supplements": [
        "vitamin", "vitamins", "supplement", "supplements", "protein powder", "minerals", "capsules",
    ],
    "makeup": [
        "makeup", "cosmetics", "foundation", "lipstick", "mascara", "eyeshadow", "concealer",
        "blush", "primer",
    ],
    "skincare": [
        "skincare", "moisturizer", "serum", "cleanser", "sunscreen", "toner", "face wash", "cream",
        "lotion", "body lotion", "body cream", "face mist",
    ],
    "haircare": ["haircare", "hair", "shampoo", "conditioner", "hair oil", "hair mask"],
    "fashion": [
        "fashion", "clothing", "apparel", "bag", "bags", "handbag", "handbags", "shoes", "sneakers",
        "jacket", "coat", "scarf", "belt", "wallet", "dress", "watch", "watches", "jewelry",
        "sunglasses", "hat", "cap",
    ],
}


def _test_lexicon():
    """The run-time test lexicon (2.2 schema): the spec's minimum EN sets + a small AR set."""
    non = {k: list(v) for k, v in EN_NON.items()}
    non["electronics"].append(AR_JAWWAL)
    non["grocery"].append(AR_TAAM)
    non["supplements"].append(AR_FITAMIN)
    non["makeup"].append(AR_MIKYAJ)
    non["skincare"].append(AR_KRIM)
    non["haircare"].append(AR_SHAMPOO)
    non["fashion"].append(AR_HAQIBA)
    return {
        "version": 1,
        "fragrance": {
            "concentrations": EN_CONCENTRATIONS + [AR_BARFAN],
            "forms": EN_FORMS + [AR_ITR],
            "houses": EN_HOUSES + ["lancome", "chloe", AR_LATTAFA, AR_AMWAJ],
            "notes": EN_NOTES + [AR_WARD, AR_OUD, AR_MISK],
        },
        "non_fragrance": non,
    }


def _write_lexicon(path: Path, lex=None) -> Path:
    path.write_text(json.dumps(lex if lex is not None else _test_lexicon(), ensure_ascii=True, indent=1) + "\n",
                    encoding="ascii", newline="\n")
    return path


# ---------------------------------------------------------------------------
# module access (AssertionError only at the base)
# ---------------------------------------------------------------------------
def _gate_present() -> bool:
    try:
        return importlib.util.find_spec(GATE_MOD) is not None
    except (ImportError, ValueError):
        return False


def _gate_or_none():
    if not _gate_present():
        return None
    return importlib.import_module(GATE_MOD)


def _gate_or_fail():
    gate = _gate_or_none()
    assert gate is not None, "S81-10: app/services/category_gate.py does not exist"
    return gate


def _attr(mod, name):
    value = getattr(mod, name, None)
    assert value is not None, f"S81-10: {mod.__name__}.{name} does not exist"
    return value


def _coro(value=None):
    async def _v():
        return value
    return _v()


def _run(coro):
    return asyncio.run(coro)


def _body(resp):
    try:
        return json.loads(resp.text)
    except ValueError as exc:
        raise AssertionError(f"not a JSON body ({type(exc).__name__}): status={resp.status_code} {resp.text[:300]!r}")


def _gate_messages(caplog):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith("[CATEGORY-GATE]")]


def _expected_keys(day_txt=DAY_TXT, uid=UID, dk=None):
    keys = [f"refusal:daily:acct:{uid}:{day_txt}"] if uid else []
    if dk:
        keys.append(f"refusal:daily:dev:{dk}:{day_txt}")
    return keys


def _dk(fp=FP):
    return request_context.device_key(fp)


def _normalized_script(text):
    return " ".join(str(text).split())


EXPECTED_SCRIPT = (
    "for i = 1, #KEYS do\n"
    "  redis.call('INCR', KEYS[i])\n"
    "  redis.call('EXPIREAT', KEYS[i], ARGV[1])\n"
    "end\n"
    "return #KEYS\n"
)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class FakeRedis:
    """redis-py shaped: get / mget / eval(script, numkeys, *keys_and_args). The two
    budget scripts are emulated in Python (no Lua runtime on the box, R-S09-10): each
    KEYS[i] is INCRed, and EXPIREAT ARGV[1] is applied only when the script text
    carries it (so a dropped EXPIREAT leaves the key without a TTL)."""

    def __init__(self, rec, store=None, raising=None):
        self.rec = rec
        self.store = dict(store or {})
        self.expireat = {}
        self.raising = raising

    def get(self, key):
        self.rec.append(("redis.get", key))
        if self.raising == "get":
            raise RuntimeError("s10 probe: redis get")
        value = self.store.get(key)
        return None if value is None else str(value)

    def mget(self, *keys):
        if len(keys) == 1 and isinstance(keys[0], (list, tuple)):
            keys = tuple(keys[0])
        self.rec.append(("redis.mget", tuple(keys)))
        if self.raising == "get":
            raise RuntimeError("s10 probe: redis mget")
        return [None if self.store.get(k) is None else str(self.store.get(k)) for k in keys]

    def eval(self, script, *args, **kwargs):
        numkeys = int(args[0])
        keys = list(args[1:1 + numkeys])
        argv = list(args[1 + numkeys:])
        return self._emulate("positional", script, keys, argv)

    def _emulate(self, shape, script, keys, argv):
        self.rec.append(("redis.eval", shape, tuple(keys), tuple(str(a) for a in argv)))
        if self.raising == "eval":
            raise RuntimeError("s10 probe: redis eval")
        norm = _normalized_script(script)
        for key in keys:
            if "redis.call('INCR', KEYS[i])" in norm:
                self.store[key] = int(self.store.get(key) or 0) + 1
            if "redis.call('EXPIREAT', KEYS[i], ARGV[1])" in norm and argv:
                self.expireat[key] = int(argv[0])
        return len(keys)


class FakeUpstash(FakeRedis):
    def eval(self, script, keys=None, args=None):
        return self._emulate("keyword", script, list(keys or []), list(args or []))


FakeUpstash.__module__ = "upstash_redis.client"


def _redis_reads(rec):
    keys = []
    for entry in rec:
        if entry[0] == "redis.get":
            keys.append(entry[1])
        elif entry[0] == "redis.mget":
            keys.extend(entry[1])
    return keys


def _evals(rec):
    return [e for e in rec if e[0] == "redis.eval"]


def _tags(rec):
    return [e[0] for e in rec]


def _gate_summary(value):
    if value is None:
        return None
    return {
        "outcome": getattr(value, "outcome", "?"),
        "evidence": getattr(value, "evidence", "?"),
        "category": getattr(value, "category", "?"),
        "subject": getattr(value, "subject", None) is not None,
    }


def _jsonable(value):
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(type(value).__name__)


class FakeService:
    """The recording orchestrator for route rows: compare_from_text returns plan['result'],
    compare_from_text_streaming yields plan['events']."""

    def __init__(self, rec, plan):
        self.rec = rec
        self.plan = plan

    def _record(self, tag, args, kwargs):
        gate_kw = kwargs.get("fragrance_gate", None)
        plain = {k: v for k, v in kwargs.items() if k != "fragrance_gate"}
        self.rec.append((tag, _jsonable(list(args)), sorted(kwargs), _jsonable(plain), _gate_summary(gate_kw)))

    async def compare_from_text(self, *args, **kwargs):
        self._record("compare", args, kwargs)
        return json.loads(json.dumps(self.plan["result"]))

    def compare_from_text_streaming(self, *args, **kwargs):
        self._record("compare_stream", args, kwargs)
        events = json.loads(json.dumps(self.plan["events"]))

        async def _gen():
            for event_type, data in events:
                yield event_type, data
        return _gen()


class _FakeSafety:
    async def moderate_vision_output(self, _extracted):
        return content_safety_service.SafetyResult(allowed=True)

    def check_query_intent(self, _query):
        return content_safety_service.SafetyResult(allowed=True)


class _FakeSupabase:
    """Records every chained call of table(...).select(...)... .execute()."""

    def __init__(self, rec, tables):
        self.rec = rec
        self.tables = tables

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.chain = [("table", name)]

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)

        def _call(*args, **kwargs):
            self.chain.append((attr, _jsonable(list(args)), _jsonable(kwargs)))
            return self
        return _call

    def execute(self):
        self.client.rec.append(("supabase", _jsonable(self.chain)))
        return types.SimpleNamespace(data=json.loads(json.dumps(self.client.tables.get(self.name))))


def _comparison_row(id_, category, created_at, winner=0):
    p0 = {"brand": "Brand" + id_[-1], "name": "One " + category, "price": {"amount": 20.0, "currency": "BHD"}}
    p1 = {"brand": "Other" + id_[-1], "name": "Two " + category, "price": {"amount": 30.0, "currency": "BHD"}}
    return {
        "id": id_,
        "created_at": created_at,
        "full_response": {
            "winner_index": winner,
            "products": [p0, p1],
            "scoring": {"dimension_winners": {}},
            "category": category,
        },
    }


_CLEAR_ENV = (
    "ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "ENABLE_COMPARISON_ID_ECHO",
    "ENABLE_RESULT_STATUS_METADATA", "ENABLE_ANON_USAGE_GATE", "ENABLE_CAMERA_FAILURE_ENVELOPE",
    "ENABLE_VISION_IDENTITY_V2", "ENABLE_URL_MODE_V2", "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_LLM_SPEND_BREAKER",
    "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION", "ENABLE_ANTHROPIC_VERDICT",
    "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION", "ENABLE_SONNET_ESCALATION",
    "ENABLE_OPENAI_PRE_V3", "ENABLE_LLM_LEDGER_V2", "ENABLE_DEVICE_DAILY_QUOTA",
    "ENABLE_RIYADH_RESET", "DEVICE_QUOTA_EXEMPT_USER_IDS", "ENABLE_PARSE_PRESPLIT",
    "ENABLE_PARSE_BUDGET", "ENABLE_CATEGORY_TOKEN_FIX", "ENABLE_FULL_STREAM_DEADLINE",
    "ENABLE_DEFAULT_RATE_LIMITS", "ENABLE_PROXY_AWARE_RATELIMIT", "ENABLE_HOME_SAVINGS_AGGREGATE",
    "ENABLE_SMART_PICK_VERDICT_CAPTION", "ENABLE_SYNC_DB_OFFLOAD",
    "APP_MIN_VERSION", "APP_LATEST_VERSION", "APP_FORCE_UPDATE", "APP_STORE_URL", "PLAY_STORE_URL",
)


@pytest.fixture(autouse=True)
def _s10_clean(monkeypatch):
    """Every row sets the names it depends on; nothing comes from the ambient env."""
    for name in _CLEAR_ENV + (FLAG, BUDGET, LEXP, "ENABLE_REQUEST_CONTEXT_HEADERS",
                              "ENABLE_PAID_ROUTE_METERING", "ENABLE_COMPARE_AUTH_REQUIRED"):
        monkeypatch.delenv(name, raising=False)
    gate = _gate_or_none()
    reset = getattr(gate, "_reset_lexicon_cache", None) if gate is not None else None
    if callable(reset):
        reset()
    yield
    if callable(reset):
        reset()


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _full_config(monkeypatch, tmp_path, *, budget="1", header_flag=True, metering=True):
    """The B1 configuration: every knob set, the device header machinery ON, metering ON."""
    lex = _write_lexicon(tmp_path / "s10_lexicon.json")
    monkeypatch.setenv(BUDGET, budget)
    monkeypatch.setenv(LEXP, str(lex))
    if header_flag:
        monkeypatch.setenv("ENABLE_REQUEST_CONTEXT_HEADERS", "true")
    monkeypatch.setenv("DEVICE_KEY_PEPPER", PEPPER_VALUE)
    if metering:
        monkeypatch.setenv("ENABLE_PAID_ROUTE_METERING", "true")
    return lex


FIXED_NEXT = datetime(2026, 10, 30, 0, 0, 0, tzinfo=timezone.utc)


def _window_1800(now):
    """The reset-window seam pinned for route rows: a fixed day, the reset 1800 s ahead."""
    return DAY, now + timedelta(seconds=1800), 0


def _window_fixed(now):
    return DAY, FIXED_NEXT, 0


def _success_result():
    return {
        "success": True,
        "products": [{"brand": "Dior", "name": "Sauvage"}, {"brand": "Chanel", "name": "Bleu de Chanel"}],
        "metadata": {"total_cost": 0.01},
        "category": "fragrances",
    }


def _insufficient_result():
    return {
        "success": False,
        "error": "Comparison data was incomplete - choose different products.",
        "code": "INSUFFICIENT_DATA",
        "elapsed_seconds": 1.0,
        "total_cost": 0.0,
        "api_calls": 0,
    }


def _refusal_literal(category):
    return {
        "success": False,
        "error": REFUSAL_MESSAGE,
        "code": CODE,
        "category": category,
        "categories_live": ["fragrances"],
        "elapsed_seconds": 0.5,
        "total_cost": 0.0002,
        "api_calls": 1,
    }


def _stream_success_events():
    return [
        ["status", {"message": "Parsing query...", "progress": 10}],
        ["settle_complete", _success_result()],
        ["complete", _success_result()],
    ]


def _vision(*pairs, cost=0.003):
    return {"products": [{"brand": b, "name": n} for b, n in pairs], "cost": cost}


def _seeded_store(value=99, uid_list=(UID, UID2), fps=(FP, FP2)):
    """Refusal counters ABOVE any budget for every synthetic subject (B1: a gate that
    read them under OFF would refuse; the recorders would also see the read)."""
    store = {}
    for uid in uid_list:
        store[f"refusal:daily:acct:{uid}:{DAY_TXT}"] = value
    for fp in fps:
        dk = _dk(fp)
        if dk:
            store[f"refusal:daily:dev:{dk}:{DAY_TXT}"] = value
    return store


class Harness:
    """Route-level harness: the real app through TestClient, every paid leaf faked and
    recorded in ONE ordered list, the real S81-05 middleware binding the device header."""

    def __init__(self, monkeypatch, tmp_path, *, flag="true", budget="10", user=USER, header=FP,
                 auth_required=False, metering=True, header_flag=True, store=None,
                 redis_cls=FakeRedis, redis_raising=None, redis_none=False, window=_window_1800,
                 seed=False):
        self.mp = monkeypatch
        self.rec = []
        _full_config(monkeypatch, tmp_path, budget=budget, header_flag=header_flag, metering=metering)
        if seed:
            store = {**_seeded_store(), **dict(store or {})}
        _set_flag(monkeypatch, flag)
        if auth_required:
            monkeypatch.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
        self.user = user
        self.header = header
        self.admin = None
        self.redis = None if redis_none else redis_cls(self.rec, store=dict(store or {}), raising=redis_raising)
        monkeypatch.setattr(cache_service, "redis_client", self.redis)
        self.plan = {
            "result": _success_result(),
            "events": _stream_success_events(),
            "consume_allowed": True,
            "vision": _vision(("Dior", "Sauvage EDP"), ("Chanel", "Bleu de Chanel EDP")),
            "camera_result": _success_result(),
            "tier": "free",
            "supabase": {
                "users": {"preferences": {}, "behavior_profile": {}},
                "comparisons": [
                    _comparison_row("cmp-1", "electronics", "2026-10-29T10:00:00Z"),
                    _comparison_row("cmp-2", "fragrances", "2026-10-28T10:00:00Z"),
                ],
            },
        }
        self.svc = FakeService(self.rec, self.plan)
        self.supabase = _FakeSupabase(self.rec, self.plan["supabase"])
        self._install()
        monkeypatch.setitem(APP.dependency_overrides, get_optional_user, lambda: self.user)
        monkeypatch.setitem(APP.dependency_overrides, get_current_user, lambda: self.user or USER)
        gate = _gate_or_none()
        if gate is not None and hasattr(gate, "reset_window"):
            monkeypatch.setattr(gate, "reset_window", window)
        self.client = TestClient(APP, raise_server_exceptions=False)

    # -- fakes ---------------------------------------------------------------
    def _install(self):
        mp, rec, plan = self.mp, self.rec, self.plan

        async def _prefs(uid):
            rec.append(("prefs", uid))
            return {"success": True, "preferences_completed": True, "preferences": {"priorities": ["value"]}}

        def _consume(uid, access_token="", *a, **kw):
            rec.append(("consume", uid))
            if plan["consume_allowed"]:
                payload = {
                    "allowed": True, "reason": None, "tier": "free", "consumed": True,
                    "consumed_keys": {"daily": "usage:daily:" + uid, "monthly": "usage:monthly:" + uid},
                    "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
                }
            else:
                payload = {
                    "allowed": False, "reason": "daily_limit", "tier": "free", "consumed": False,
                    "remaining": {"daily": 0, "monthly": 0, "lifetime_free": 0},
                }
            return _coro(payload)

        def _refund(uid, consumed_keys=None, *a, **kw):
            rec.append(("refund", uid))
            return _coro(None)

        def _refund_anon(fp, consumed_keys=None, *a, **kw):
            rec.append(("refund_anon", "fp"))
            return _coro(None)

        def _lifetime(uid, access_token="", *a, **kw):
            rec.append(("record_lifetime", uid))
            return _coro(None)

        def _log_search(**kw):
            rec.append(("log_search", kw.get("input_type"), kw.get("success")))
            return _coro(None)

        def _save(**kw):
            rec.append(("save", kw.get("input_type")))
            return _coro(None)

        def _capture(result, input_type, **kw):
            rec.append(("capture_result_status", input_type))

        def _ff(coro, label=None, **kw):
            rec.append(("ff", label))
            close = getattr(coro, "close", None)
            if callable(close):
                close()

        for mod in (text_routes, image_routes):
            mp.setattr(mod, "consume_comparison_credit", _consume)
            mp.setattr(mod, "refund_comparison_credit", _refund)
            mp.setattr(mod, "record_lifetime_comparison", _lifetime)
            mp.setattr(mod, "log_search", _log_search)
            mp.setattr(mod, "save_comparison_and_track_cohort", _save)
            mp.setattr(mod, "capture_result_status", _capture)
            mp.setattr(mod, "fire_and_forget", _ff)
        mp.setattr(text_routes, "get_user_preferences", _prefs)
        mp.setattr(image_routes, "get_user_preferences", _prefs)
        mp.setattr(image_routes, "refund_anon_comparison_credit", _refund_anon)
        mp.setattr(text_routes, "get_comparison_service", lambda: self.svc)

        async def _identify(images):
            rec.append(("vision", len(images)))
            return json.loads(json.dumps(plan["vision"]))

        mp.setattr(image_routes, "identify_products", _identify)
        harness = self

        class _CamService:
            async def compare_from_text(self, *args, **kwargs):
                harness.svc._record("compare", args, kwargs)
                return json.loads(json.dumps(harness.plan["camera_result"]))

        mp.setattr(image_routes, "StructuredComparisonService", _CamService)
        mp.setattr(content_safety_service, "get_content_safety_service", lambda: _FakeSafety())
        mp.setattr(audit_service, "log_content_blocked", lambda **kw: _coro(None))

        async def _home_get(key):
            rec.append(("home_cache_get", key))
            return None

        async def _home_set(key, value, ex=None):
            rec.append(("home_cache_set", key, ex))
            return True

        mp.setattr(home_routes, "_redis_get_async", _home_get)
        mp.setattr(home_routes, "_redis_set_async", _home_set)
        mp.setattr(home_routes, "get_user_supabase_client", lambda *a, **k: self.supabase)
        mp.setattr(home_routes, "get_admin_supabase_client", lambda *a, **k: self.supabase)

        def _tier(uid, *a, **kw):
            rec.append(("tier_read", uid))
            return _coro({"subscription_tier": plan["tier"], "lifetime_comparisons_used": 5,
                          "referral_bonus_comparisons_this_month": 0})

        mp.setattr(usage_service, "_get_user_tier_info", _tier)

    # -- requests ------------------------------------------------------------
    def headers(self):
        out = {"X-Request-ID": "s10-rid"}
        if self.header:
            out["X-Device-Fingerprint"] = self.header
        if self.admin:
            out["X-Admin-Key"] = self.admin
        return out

    def _reset_limiter(self):
        from app.middleware.rate_limiter import limiter
        limiter.reset()

    def post(self, body):
        self._reset_limiter()
        return self.client.post("/api/v1/text/compare", json=body, headers=self.headers())

    def get(self, params):
        self._reset_limiter()
        return self.client.get("/api/v1/text/compare", params=params, headers=self.headers())

    def stream(self, params):
        self._reset_limiter()
        return self.client.get("/api/v1/text/compare/stream", params=params, headers=self.headers())

    def camera(self, n_images=2):
        self._reset_limiter()
        files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(n_images)]
        return self.client.post("/api/v1/image/identify", files=files, headers=self.headers())

    def quick(self, body):
        self._reset_limiter()
        return self.client.post("/api/v1/text/quick", json=body, headers=self.headers())

    def path(self, url, params=None):
        self._reset_limiter()
        return self.client.get(url, params=params, headers=self.headers())

    # -- reads ---------------------------------------------------------------
    def compares(self):
        return [e for e in self.rec if e[0] in ("compare", "compare_stream")]

    def tags(self):
        return _tags(self.rec)


class SvcHarness:
    """Service-level harness: a REAL StructuredComparisonService; the parse, the A2b
    classify, the fetch pair, the behaviour profile and the demographics read are
    recording fakes (plain functions returning coroutines, so the CALL order is the
    recorded order). The fetch returns a both-failed Phase 1, so a compare that passes
    the gate ends at INSUFFICIENT_DATA right after the fetch."""

    def __init__(self, monkeypatch, tmp_path, *, flag="true", a2b="electronics", parsed=None, store=None,
                 budget="10", seed=False):
        self.mp = monkeypatch
        self.rec = []
        _full_config(monkeypatch, tmp_path, budget=budget)
        if seed:
            store = {**_seeded_store(), **dict(store or {})}
        _set_flag(monkeypatch, flag)
        self.redis = FakeRedis(self.rec, store=dict(store or {}))
        monkeypatch.setattr(cache_service, "redis_client", self.redis)
        self.plan = {"a2b": a2b, "parsed": parsed}
        rec, plan = self.rec, self.plan

        def _parse(svc_self, query):
            rec.append(("parse", query))
            return _coro((json.loads(json.dumps(plan["parsed"])), {"prompt_tokens": 1, "completion_tokens": 1}))

        def _fetch(svc_self, product, region, include_specs=True, include_reviews=True, nocache=False,
                   partial_slot=None, **kw):
            rec.append(("fetch", partial_slot, product.get("category")))
            return _coro({"specs": None, "price": None})

        def _profile(svc_self, user_id):
            rec.append(("profile", user_id))
            return _coro(None)

        def _demo(user_id):
            rec.append(("demographics", user_id))
            return _coro(None)

        def _a2b(names):
            rec.append(("classify", tuple(names)))
            return _coro(plan["a2b"])

        cls = scs.StructuredComparisonService
        monkeypatch.setattr(cls, "_parse_with_budget", _parse)
        monkeypatch.setattr(cls, "_fetch_product_data", _fetch)
        monkeypatch.setattr(cls, "_fetch_behavior_profile", _profile)
        monkeypatch.setattr(scs, "get_user_demographics", _demo)
        monkeypatch.setattr(scs, "classify_category_llm", _a2b)
        monkeypatch.setattr(extraction_service, "classify_category_llm", _a2b)
        monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _FakeSafety())
        monkeypatch.setattr(audit_service, "log_content_blocked", lambda **kw: _coro(None))
        orig = scs._resolve_pair_category

        async def _resolve_spy(products, selected_category, parser_path=False):
            rec.append(("resolve", bool(parser_path)))
            return await orig(products, selected_category, parser_path=parser_path)

        monkeypatch.setattr(scs, "_resolve_pair_category", _resolve_spy)
        gate = _gate_or_none()
        if gate is not None:
            if hasattr(gate, "classify_category_llm"):
                monkeypatch.setattr(gate, "classify_category_llm", _a2b)
            if hasattr(gate, "reset_window"):
                monkeypatch.setattr(gate, "reset_window", _window_fixed)

    def decision(self, texts, *, header=True, user=USER):
        gate = _gate_or_fail()
        tokens = request_context.bind_from_headers([(b"x-device-fingerprint", FP.encode("ascii"))]) if header else None
        try:
            subject = gate.budget_subject(user)
        finally:
            if tokens is not None:
                request_context.reset_request_context(tokens)
        return gate.evaluate(texts, subject=subject)

    def compare(self, query, **kw):
        svc = scs.StructuredComparisonService()
        return _run(svc.compare_from_text(query, region="bahrain", **kw))

    def stream(self, query, **kw):
        svc = scs.StructuredComparisonService()

        async def _collect():
            return [ev async for ev in svc.compare_from_text_streaming(query, region="bahrain", **kw)]
        return _run(_collect())

    def count(self, tag):
        return sum(1 for e in self.rec if e[0] == tag)


def _parsed(cat0, cat1, n0=("Apple", "iPhone 15"), n1=("Samsung", "Galaxy S24")):
    return {
        "products": [
            {"brand": n0[0], "name": n0[1], "category": cat0, "search_query": f"{n0[0]} {n0[1]}"},
            {"brand": n1[0], "name": n1[1], "category": cat1, "search_query": f"{n1[0]} {n1[1]}"},
        ],
        "comparison_type": "value",
    }


# ---------------------------------------------------------------------------
# the golden scenarios (recorded at the base, flag unset, full configuration)
# ---------------------------------------------------------------------------
def _g01(h):
    return h.post({"query": "dior sauvage vs bleu de chanel", "selected_category": "fragrances"})


def _g02(h):
    return h.post({"product_a": "macbook air laptop", "product_b": "dell xps laptop"})


def _g03(h):
    h.plan["result"] = _insufficient_result()
    return h.get({"q": "iphone 15 vs galaxy s24"})


def _g04(h):
    return h.get({"product_a": "nivea cream", "product_b": "dove cream", "selected_category": "skincare"})


def _g05(h):
    return h.stream({"q": "dior sauvage vs bleu de chanel"})


def _g06(h):
    h.plan["events"] = [
        ["status", {"message": "Parsing query...", "progress": 10}],
        ["error", {"success": False, "error": "We don't compare this category",
                   "code": "CONTENT_UNAVAILABLE", "layer": "query_prefilter"}],
    ]
    return h.stream({"product_a": "laptop a", "product_b": "laptop b"})


def _g07(h):
    h.plan["consume_allowed"] = False
    return h.post({"query": "dior sauvage vs bleu de chanel"})


def _g08(h):
    h.plan["vision"] = _vision(("Nivea", "Soft Cream"), ("Dove", "Body Cream"))
    h.plan["camera_result"] = {
        "success": True,
        "products": [{"brand": "Nivea", "name": "Soft Cream"}, {"brand": "Dove", "name": "Body Cream"}],
        "metadata": {"total_cost": 0.01},
        "category": "skincare",
    }
    return h.camera(2)


def _g09(h):
    return h.path("/api/v1/app/version")


def _g10(h):
    return h.path("/api/v1/home/smart-pick")


def _g11(h):
    h.user = None
    return h.path("/api/v1/home/trending", {"region": "bahrain"})


def _g12(h):
    h.user = None
    h.mp.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
    h.mp.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    return h.post({"query": "best laptop vs dell laptop"})


GOLDEN_SCENARIOS = [
    ("G01", _g01), ("G02", _g02), ("G03", _g03), ("G04", _g04), ("G05", _g05), ("G06", _g06),
    ("G07", _g07), ("G08", _g08), ("G09", _g09), ("G10", _g10), ("G11", _g11), ("G12", _g12),
]


def _scenario_record(h, resp, caplog_records):
    headers = {"content-type": resp.headers.get("content-type")}
    if resp.headers.get("retry-after") is not None:
        headers["retry-after"] = resp.headers.get("retry-after")
    logs = [r.getMessage() for r in caplog_records if r.name in GOLDEN_LOGGERS and r.levelno >= logging.INFO]
    return {
        "calls": _jsonable(h.rec),
        "status": resp.status_code,
        "headers": headers,
        "body": resp.text,
        "logs": logs,
    }


def _install_raising_gate_recorders(monkeypatch, called):
    """R54 / P01: once category_gate exists, every public function except the flag
    reader RAISES when called, so a flag-OFF path that touches the gate goes red."""
    gate = _gate_or_none()
    if gate is None:
        return []
    names = []
    for name, value in sorted(vars(gate).items()):
        if name.startswith("_") or name == "fragrance_only_gate_enabled":
            continue
        if not (inspect.isfunction(value) or inspect.iscoroutinefunction(value)):
            continue
        if getattr(value, "__module__", None) != gate.__name__:
            continue

        def _boom(*a, _n=name, **k):
            called.append(_n)
            raise AssertionError(f"S81-10 flag OFF called category_gate.{_n}")
        monkeypatch.setattr(gate, name, _boom)
        names.append(name)
    return names


# EK1 (RULINGS_FIX1_S81_10 F1-1, the one sanctioned amendment of this frozen file): the
# golden's G10 body carries the smart-pick "updated_at" label, which
# home_routes._format_updated_at computes against the wall clock (its function-local
# `from datetime import datetime`). The scenarios run the REAL formatter with that clock
# frozen at the record instant, so no later date changes a recorded byte; the golden and
# app/ are unchanged.
GOLDEN_RECORD_INSTANT = datetime(2026, 11, 2, 8, 30, 0, tzinfo=timezone.utc)


class _RecordInstantDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        moment = GOLDEN_RECORD_INSTANT.astimezone(tz)
        return moment if tz is not None else moment.replace(tzinfo=None)


def _at_record_instant(real_format):
    import datetime as datetime_module

    def _format(created_at_iso):
        wall = datetime_module.datetime
        datetime_module.datetime = _RecordInstantDatetime
        try:
            return real_format(created_at_iso)
        finally:
            datetime_module.datetime = wall
    return _format


def _run_golden(monkeypatch, tmp_path, caplog, spelling, raising=True):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(home_routes, "_format_updated_at", _at_record_instant(home_routes._format_updated_at))
    called = []
    out = {}
    for name, run in GOLDEN_SCENARIOS:
        h = Harness(monkeypatch, tmp_path, flag=spelling, budget="1", seed=True)
        if raising:
            _install_raising_gate_recorders(monkeypatch, called)
        caplog.clear()
        resp = run(h)
        out[name] = _scenario_record(h, resp, caplog.records)
        out[name]["gate_lines"] = _gate_messages(caplog)
    return out, called


# ===========================================================================
# R01-R15: the pure gate (knobs, lexicon, normalisation, rule 1, evidence)
# ===========================================================================
@pytest.fixture
def lexicon_gate(monkeypatch, tmp_path):
    """Writes the run-time test lexicon and points the knob at it; the module itself is
    read INSIDE the test body (so a missing module is an AssertionError of the row, never
    a setup error)."""
    lex = _write_lexicon(tmp_path / "s10_test_lexicon.json")
    monkeypatch.setenv(LEXP, str(lex))

    def _get():
        gate = _gate_or_fail()
        reset = getattr(gate, "_reset_lexicon_cache", None)
        if callable(reset):
            reset()
        return gate
    return _get


def _mini_lexicon(extra_electronics=()):
    lex = {
        "version": 1,
        "fragrance": {
            "concentrations": ["edp"], "forms": ["perfume"], "houses": ["dior"], "notes": ["oud", "musk"],
        },
        "non_fragrance": {k: ["zzplaceholder" + k] for k in NON_FRAGRANCE},
    }
    lex["non_fragrance"]["electronics"] = list(extra_electronics) + ["zzplaceholderelectronics"]
    return lex


def test_r01_flag_reader_per_call(monkeypatch):
    gate = _gate_or_fail()
    reader = _attr(gate, "fragrance_only_gate_enabled")
    assert getattr(gate, "FLAG_ENV", None) == FLAG
    for value in ON_SPELLINGS:
        monkeypatch.setenv(FLAG, value)
        assert reader() is True, value
    for value in OFF_SPELLINGS:
        _set_flag(monkeypatch, value)
        assert reader() is False, value
    monkeypatch.setenv(FLAG, "true")
    assert reader() is True
    monkeypatch.setenv(FLAG, "off")
    assert reader() is False


@pytest.mark.parametrize("raw,expected", [
    (None, 10), ("25", 25), (" 7 ", 7), ("7.9", 7), ("0", 10), ("-3", 10), ("abc", 10),
    ("inf", 10), ("-inf", 10), ("nan", 10), ("", 10), ("  ", 10), ("0.5", 10), ("250", 100),
    ("100", 100), ("1", 1), ("1e3", 100),
])
def test_r02_budget_knob(monkeypatch, raw, expected):
    gate = _gate_or_fail()
    assert getattr(gate, "BUDGET_ENV", None) == BUDGET
    knob = _attr(gate, "refusal_daily_budget")
    if raw is None:
        monkeypatch.delenv(BUDGET, raising=False)
    else:
        monkeypatch.setenv(BUDGET, raw)
    got = knob()
    assert type(got) is int and got == expected, (raw, got)


def test_r03_lexicon_path_knob(monkeypatch, tmp_path):
    gate = _gate_or_fail()
    assert getattr(gate, "LEXICON_ENV", None) == LEXP
    path_of = _attr(gate, "lexicon_path")
    default = (ROOT / "data" / "fragrance_lexicon.json").resolve()
    monkeypatch.delenv(LEXP, raising=False)
    assert Path(path_of()).resolve() == default
    monkeypatch.setenv(LEXP, "   ")
    assert Path(path_of()).resolve() == default
    monkeypatch.setenv(LEXP, "data/x.json")
    assert Path(path_of()).resolve() == (ROOT / "data" / "x.json").resolve()
    absolute = (tmp_path / "abs_lexicon.json").resolve()
    monkeypatch.setenv(LEXP, str(absolute))
    assert Path(path_of()).resolve() == absolute


def test_r04_lexicon_reloads_without_restart(monkeypatch, tmp_path):
    gate = _gate_or_fail()
    path = tmp_path / "reload_lexicon.json"
    _write_lexicon(path, _mini_lexicon(extra_electronics=["zzqa"]))
    monkeypatch.setenv(LEXP, str(path))  # the knob set AFTER import is honoured
    first = gate.evaluate(["zzqa vs zzqa"])
    assert first.outcome == "refuse" and first.category == "electronics", first
    _write_lexicon(path, _mini_lexicon(extra_electronics=["zzqb", "zzqc", "zzqd"]))
    os.utime(path, None)
    second = gate.evaluate(["zzqa vs zzqa"])
    assert second.outcome == "proceed", second
    third = gate.evaluate(["zzqd vs zzqd"])
    assert third.outcome == "refuse" and third.category == "electronics", third


@pytest.mark.parametrize("kind,type_name", [
    ("missing", "FileNotFoundError"), ("invalid", "JSONDecodeError"), ("schema", None),
])
def test_r05_lexicon_unavailable_fails_safe(monkeypatch, tmp_path, caplog, kind, type_name):
    gate = _gate_or_fail()
    caplog.set_level(logging.INFO)
    path = tmp_path / ("lex_" + kind + ".json")
    if kind == "invalid":
        path.write_text("{not json", encoding="ascii")
    elif kind == "schema":
        path.write_text(json.dumps({"version": 1, "fragrance": {}}), encoding="ascii")
    monkeypatch.setenv(LEXP, str(path))
    caplog.clear()
    first = gate.evaluate(["best laptop vs dell laptop"])
    second = gate.evaluate(["best laptop vs dell laptop"])
    for decision in (first, second):
        assert decision.outcome == "proceed" and decision.evidence is False, decision
    lines = [m for m in _gate_messages(caplog) if "lexicon unavailable" in m]
    assert len(lines) == 1, lines
    assert LOG_GRAMMAR.match(lines[0]), lines[0]
    if type_name:
        assert lines[0].endswith("type=" + type_name), lines[0]
    warn = [r for r in caplog.records if r.getMessage() == lines[0]]
    assert warn and all(r.levelno == logging.WARNING for r in warn)


AR_DENY = [
    _ar(0x0642, 0x0647, 0x0648, 0x0629),  # qahwa (coffee)
    _ar(0x062D, 0x0644, 0x064A, 0x0628),  # halib (milk)
    _ar(0x0634, 0x0627, 0x064A),  # shay (tea)
    _ar(0x0639, 0x0633, 0x0644),  # asal (honey)
    _ar(0x0634, 0x0648, 0x0643, 0x0648, 0x0644, 0x0627, 0x062A, 0x0629),  # shukulata (chocolate)
]
EN_DENY = ["coffee", "milk", "tea", "honey", "chocolate"]


def test_r06_production_lexicon_content():
    gate = _gate_or_fail()
    assert LEXICON_FILE.exists(), "S81-10: data/fragrance_lexicon.json does not exist"
    raw = LEXICON_FILE.read_bytes()
    assert all(b < 128 for b in raw), "the lexicon must be pure ASCII (\\u escapes)"
    assert b"\r" not in raw and raw.endswith(b"\n")
    lex = json.loads(raw.decode("ascii"))
    assert set(lex) == {"version", "fragrance", "non_fragrance"} and lex["version"] == 1
    assert set(lex["fragrance"]) == {"concentrations", "forms", "houses", "notes"}
    assert set(lex["non_fragrance"]) == set(NON_FRAGRANCE)
    norm = _attr(gate, "normalize")

    def n(term):
        return tuple(norm(term))

    seen = {}
    for section in ("fragrance", "non_fragrance"):
        for group, terms in lex[section].items():
            assert isinstance(terms, list) and terms, (section, group)
            for term in terms:
                assert isinstance(term, str) and term.strip(), (section, group, term)
                key = n(term)
                assert key, (section, group, term)
                assert key not in seen, f"duplicate after normalisation: {term!r} in {group} and {seen[key]}"
                seen[key] = (section, group)
            assert any(any(ord(c) > 127 for c in t) for t in terms), f"no Arabic term in {section}.{group}"
    frag = lex["fragrance"]
    required = {
        "concentrations": EN_CONCENTRATIONS, "forms": EN_FORMS + ["hair perfume"],
        "houses": EN_HOUSES, "notes": EN_NOTES,
    }
    for group, terms in required.items():
        have = {n(t) for t in frag[group]}
        missing = [t for t in terms if n(t) not in have]
        assert not missing, (group, missing)
    assert len(frag["houses"]) >= 40
    for group, terms in EN_NON.items():
        have = {n(t) for t in lex["non_fragrance"][group]}
        missing = [t for t in terms if n(t) not in have]
        assert not missing, (group, missing)
    notes = {n(t) for t in frag["notes"]}
    deny = {n(t) for t in EN_DENY + AR_DENY}
    for group, terms in lex["non_fragrance"].items():
        for term in terms:
            assert n(term) not in notes, f"C4: non_fragrance.{group} term {term!r} is a note"
            assert n(term) not in deny, f"C4: non_fragrance.{group} term {term!r} is an ingredient / note word"


def test_r07_rule1_english(lexicon_gate):
    lex_gate = lexicon_gate()
    d = lex_gate.evaluate(["best laptop under 300 vs dell laptop"])
    assert d.outcome == "refuse" and d.category == "electronics", d
    d = lex_gate.evaluate(["nivea cream vs dove cream"])
    assert d.outcome == "refuse" and d.category == "skincare", d
    d = lex_gate.evaluate(["nivea lipstick vs loreal lipstick"])
    assert d.outcome == "refuse" and d.category == "makeup", d


def test_r08_rule1_arabic(lexicon_gate):
    lex_gate = lexicon_gate()
    shampoo_with_article = AR_AL + _ar(0x0634, 0x0640, 0x064E, 0x0627, 0x0645, 0x0628, 0x0648)
    d = lex_gate.evaluate([shampoo_with_article + " vs " + AR_SHAMPOO])
    assert d.outcome == "refuse" and d.category == "haircare", d
    d = lex_gate.evaluate([AR_AL + AR_ITR + " " + AR_LATTAFA])
    assert d.outcome == "proceed" and d.evidence is True, d


def test_r09_double_product_type_proceeds(lexicon_gate):
    lex_gate = lexicon_gate()
    s = lex_gate.scan(["dior sauvage edp vs body lotion"])
    assert s.fragrance_type is True
    assert list(s.non_fragrance) == [("skincare", "body lotion")]
    d = lex_gate.evaluate(["dior sauvage edp vs body lotion"])
    assert d.outcome == "proceed" and d.evidence is True, d


@pytest.mark.parametrize("query", [
    "gucci bag vs prada bag",
    "dior sauvage body cream",
    "dior lipstick vs chanel lipstick",
    "jo malone peony & blush suede vs dior sauvage",
    "frederic malle lipstick rose",
])
def test_r10_house_or_note_beside_a_category_word_defers(lexicon_gate, query):
    """R-S10-4: a house or note hit beside a non-fragrance product-type word is NO $0
    refusal; the decision carries evidence False so the post-resolve classifier decides."""
    lex_gate = lexicon_gate()
    s = lex_gate.scan([query])
    assert s.non_fragrance and s.fragrance_type is False, s
    assert s.houses >= 1 or s.notes >= 1, s
    d = lex_gate.evaluate([query])
    assert d.outcome == "proceed" and d.evidence is False, d


def test_r11_longest_match_masking(lexicon_gate):
    lex_gate = lexicon_gate()
    s = lex_gate.scan(["chanel no 5 hair mist vs dior hair mist"])
    assert list(s.non_fragrance) == [], s
    assert s.fragrance_type is True and s.houses == 2
    d = lex_gate.evaluate(["chanel no 5 hair mist vs dior hair mist"])
    assert d.outcome == "proceed" and d.evidence is True, d
    s = lex_gate.scan(["vanilla ice cream vs choc ice cream"])
    assert list(s.non_fragrance) == [("grocery", "ice cream"), ("grocery", "ice cream")], s
    s = lex_gate.scan(["nivea body lotion vs dove lotion"])
    assert list(s.non_fragrance) == [("skincare", "body lotion"), ("skincare", "lotion")], s


def test_r12_whole_token_boundaries(lexicon_gate):
    lex_gate = lexicon_gate()
    s = lex_gate.scan(["iphone 15 vs galaxy s24"])
    assert list(s.non_fragrance) == [] and s.fragrance_type is False and s.houses == 0 and s.notes == 0
    d = lex_gate.evaluate(["iphone 15 vs galaxy s24"])
    assert d.outcome == "proceed" and d.evidence is False, d
    d = lex_gate.evaluate(["best smartphones"])
    assert d.outcome == "refuse" and d.category == "electronics", d
    assert list(lex_gate.scan(["iphones vs pixels"]).non_fragrance) == []


def test_r13_notes_need_two(lexicon_gate):
    lex_gate = lexicon_gate()
    s = lex_gate.scan(["oud rose blend vs amber vanilla"])
    assert s.notes == 4
    assert lex_gate.evaluate(["oud rose blend vs amber vanilla"]).evidence is True
    s = lex_gate.scan(["rose water vs aloe"])
    assert s.notes == 1 and list(s.non_fragrance) == []
    d = lex_gate.evaluate(["rose water vs aloe"])
    assert d.outcome == "proceed" and d.evidence is False, d
    d = lex_gate.evaluate(["vanilla ice cream vs choc ice cream"])
    assert d.outcome == "proceed" and d.evidence is False, d  # R-S10-4: a note beside a category word


def test_r14_arabic_normalisation(lexicon_gate):
    lex_gate = lexicon_gate()
    norm = lex_gate.normalize
    tail = _ar(0x0645, 0x0648, 0x0627, 0x062C)
    forms = [norm(_ar(c) + tail) for c in (0x0623, 0x0625, 0x0622, 0x0627)]
    assert forms[0] == forms[1] == forms[2] == forms[3] == [_ar(0x0627) + tail], forms
    assert norm(AR_LATTAFA) == norm(_ar(0x0644, 0x0637, 0x0627, 0x0641, 0x0647))
    assert norm(_ar(0x0645, 0x0648, 0x0633, 0x0649)) == norm(_ar(0x0645, 0x0648, 0x0633, 0x064A))
    assert norm(_ar(0x0639, 0x0650, 0x0637, 0x0652, 0x0631)) == norm(AR_ITR) == [AR_ITR]
    assert norm(_ar(0x0639, 0x0640, 0x0640, 0x0637, 0x0631)) == [AR_ITR]
    assert norm(_ar(0x0663)) == ["3"] and norm(_ar(0x06F3, 0x06F5)) == ["35"]
    for article in ((0x0627, 0x0644), (0x0648, 0x0627, 0x0644), (0x0628, 0x0627, 0x0644),
                    (0x0643, 0x0627, 0x0644), (0x0641, 0x0627, 0x0644), (0x0644, 0x0644)):
        assert norm(_ar(*article) + AR_ITR) == [AR_ITR], article
    assert norm(AR_AL + _ar(0x0628)) == [AR_AL + _ar(0x0628)]  # the remainder keeps < 2 letters
    assert norm(AR_WARD) == [AR_WARD]  # a bare leading waw is NOT stripped
    s = lex_gate.scan([AR_WARD + " " + AR_OUD])
    assert s.notes == 2
    assert lex_gate.evaluate([AR_WARD + " " + AR_OUD]).evidence is True


def test_r15_case_separators_nfkc_and_accents(lexicon_gate):
    lex_gate = lexicon_gate()
    for text in ("EAU-DE-PARFUM", "Eau  de   Parfum", "eau/de/parfum", "Eau de Parfum!"):
        assert lex_gate.scan([text]).fragrance_type is True, text
    full_width_edp = _ar(0xFF25, 0xFF24, 0xFF30)
    assert lex_gate.scan(["dior sauvage " + full_width_edp]).fragrance_type is True
    for text in ("Herm" + _ar(0x00E8) + "s Terre", "Lanc" + _ar(0x00F4) + "me Idole", "Chlo" + _ar(0x00E9) + " Nomade"):
        s = lex_gate.scan([text])
        assert s.houses == 1, (text, s)


# ===========================================================================
# R16-R23: the text routes (rule 1 at $0, the budget before every consume)
# ===========================================================================
_PAID = {"prefs", "consume", "compare", "compare_stream", "refund", "record_lifetime", "save"}
_REDIS = {"redis.get", "redis.mget", "redis.eval"}
_REFUSAL_KEYS = ["success", "error", "code", "request_id", "category", "categories_live"]
_BUDGET_KEYS = ["success", "error", "code", "request_id", "categories_live", "scope", "resets_at",
                "retry_after_seconds"]


def _assert_rule1_refusal(h, resp, caplog, route, category="electronics"):
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    assert resp.headers.get("content-type", "").startswith("application/json"), resp.headers.get("content-type")
    body = _body(resp)
    assert list(body) == _REFUSAL_KEYS, body
    assert body == {"success": False, "error": REFUSAL_MESSAGE, "code": CODE, "request_id": "s10-rid",
                    "category": category, "categories_live": ["fragrances"]}, body
    touched = [t for t in h.tags() if t in _PAID | _REDIS | {"tier_read"}]
    assert not touched, h.rec
    lines = _gate_messages(caplog)
    assert lines == [f"[CATEGORY-GATE] refused stage=pre_consume category={category} route={route}"], lines
    assert all(r.levelno == logging.INFO for r in caplog.records if r.getMessage() in lines)


def test_r16_post_rule1_zero_cost(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true")
    caplog.clear()
    resp = h.post({"query": "best laptop vs dell laptop"})
    _assert_rule1_refusal(h, resp, caplog, "text.post")


@pytest.mark.parametrize("params", [
    {"q": "best laptop vs dell laptop"},
    {"product_a": "macbook air laptop", "product_b": "dell xps laptop"},
])
def test_r17_get_rule1_zero_cost(monkeypatch, tmp_path, caplog, params):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true")
    caplog.clear()
    resp = h.get(params)
    _assert_rule1_refusal(h, resp, caplog, "text.get")


@pytest.mark.parametrize("params", [
    {"q": "best laptop vs dell laptop"},
    {"product_a": "nivea cream", "product_b": "dove cream"},
])
def test_r18_stream_rule1_zero_cost(monkeypatch, tmp_path, caplog, params):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true")
    caplog.clear()
    resp = h.stream(params)
    category = "skincare" if "product_a" in params else "electronics"
    _assert_rule1_refusal(h, resp, caplog, "text.stream", category=category)


def test_r19_rule2_proceeds_in_order(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true")
    resp = h.post({"query": "dior sauvage vs bleu de chanel"})
    assert resp.status_code == 200, resp.text[:300]
    tags = h.tags()
    reads = [i for i, t in enumerate(tags) if t in ("redis.get", "redis.mget")]
    assert reads, h.rec
    assert "prefs" in tags and "consume" in tags and "compare" in tags, tags
    assert max(reads) < tags.index("prefs") < tags.index("consume") < tags.index("compare"), tags
    assert sorted(_redis_reads(h.rec)) == sorted(_expected_keys(dk=_dk())), _redis_reads(h.rec)
    compare = h.compares()
    assert len(compare) == 1 and "fragrance_gate" in compare[0][2], compare
    summary = compare[0][4]
    assert summary == {"outcome": "proceed", "evidence": True, "category": summary.get("category"),
                       "subject": True}, summary


@pytest.mark.parametrize("axis", ["acct", "dev"])
@pytest.mark.parametrize("route", ["post", "get", "stream"])
def test_r20_budget_spent_never_billed(monkeypatch, tmp_path, caplog, route, axis):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    dk = _dk()
    key = (f"refusal:daily:acct:{UID}:{DAY_TXT}" if axis == "acct" else f"refusal:daily:dev:{dk}:{DAY_TXT}")
    h.redis.store[key] = 10
    caplog.clear()
    query = "khamrah vs hawas"
    if route == "post":
        resp = h.post({"query": query})
    elif route == "get":
        resp = h.get({"q": query})
    else:
        resp = h.stream({"q": query})
    assert resp.status_code == 429, (resp.status_code, resp.text[:300])
    body = _body(resp)
    assert list(body) == _BUDGET_KEYS, body
    assert body["success"] is False and body["code"] == CODE and body["error"] == BUDGET_MESSAGE
    assert body["scope"] == "refusal_daily" and body["categories_live"] == ["fragrances"]
    assert body["request_id"] == "s10-rid"
    assert body["retry_after_seconds"] == 1800 and resp.headers.get("retry-after") == "1800", body
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$", body["resets_at"]), body
    touched = [t for t in h.tags() if t in _PAID | {"redis.eval"}]
    assert not touched, h.rec
    label = {"post": "text.post", "get": "text.get", "stream": "text.stream"}[route]
    assert _gate_messages(caplog) == [f"[CATEGORY-GATE] budget spent stage=pre_consume route={label}"]


def test_r21_budget_boundary(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    key = f"refusal:daily:acct:{UID}:{DAY_TXT}"
    for count, status in ((9, 200), (10, 429), (15, 429)):
        h.redis.store[key] = count
        before = len(h.compares())
        resp = h.post({"query": "khamrah vs hawas"})
        assert resp.status_code == status, (count, resp.status_code, resp.text[:200])
        assert len(h.compares()) == before + (1 if status == 200 else 0), (count, h.compares())
    monkeypatch.setenv(BUDGET, "3")  # read per call
    h.redis.store[key] = 2
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    h.redis.store[key] = 3
    assert h.post({"query": "khamrah vs hawas"}).status_code == 429


def test_r22_budget_subject_two_axes(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    # (a) header bound + pepper + account: the account key ALWAYS, the device key in addition
    h = Harness(monkeypatch, tmp_path, flag="true")
    dk = _dk()
    assert dk and dk != FP
    caplog.clear()
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert sorted(_redis_reads(h.rec)) == sorted(_expected_keys(dk=dk)), _redis_reads(h.rec)
    blob = json.dumps(_jsonable(h.rec)) + " ".join(r.getMessage() for r in caplog.records)
    assert FP not in blob, "the raw fingerprint reached a key, an argument or a log record"
    # (b) no header: the account key only
    h = Harness(monkeypatch, tmp_path, flag="true", header=None)
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert _redis_reads(h.rec) == _expected_keys(dk=None), _redis_reads(h.rec)
    # (c) auth OFF + anonymous + no header: no subject, no Redis call at all
    h = Harness(monkeypatch, tmp_path, flag="true", header=None, user=None)
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert not [t for t in h.tags() if t in _REDIS], h.rec
    assert len(h.compares()) == 1
    # (d) anonymous + header: the device key only
    h = Harness(monkeypatch, tmp_path, flag="true", user=None)
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert _redis_reads(h.rec) == [f"refusal:daily:dev:{dk}:{DAY_TXT}"], _redis_reads(h.rec)


def test_r23_budget_fail_open(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true", redis_raising="get")
    caplog.clear()
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert len(h.compares()) == 1
    lines = [m for m in _gate_messages(caplog) if "fail-open" in m]
    assert lines == ["[CATEGORY-GATE] budget read fail-open type=RuntimeError"], lines
    h = Harness(monkeypatch, tmp_path, flag="true", redis_none=True)
    caplog.clear()
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert len(h.compares()) == 1 and not [m for m in _gate_messages(caplog) if "fail-open" in m]
    h = Harness(monkeypatch, tmp_path, flag="true")  # nil replies: the first request of the day
    caplog.clear()
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert _redis_reads(h.rec) and not _gate_messages(caplog), _gate_messages(caplog)  # C14: silent
    h = Harness(monkeypatch, tmp_path, flag="true", store={f"refusal:daily:acct:{UID}:{DAY_TXT}": "abc"})
    caplog.clear()
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    lines = [m for m in _gate_messages(caplog) if "fail-open" in m]
    assert len(lines) == 1 and LOG_GRAMMAR.match(lines[0]), lines


# ===========================================================================
# R24-R32: the post-resolve decision in the orchestrator (sync + stream)
# ===========================================================================
def _assert_refusal_dict(res, category, sync=True):
    assert isinstance(res, dict), res
    head = ["success", "error", "code", "category", "categories_live"]
    assert list(res)[:5] == head, list(res)
    if sync:
        assert list(res) == head + ["elapsed_seconds", "total_cost", "api_calls"], list(res)
    assert res["success"] is False and res["error"] == REFUSAL_MESSAGE and res["code"] == CODE
    assert res["category"] == category and res["categories_live"] == ["fragrances"]


def _assert_one_incr(rec, dk=None):
    evals = _evals(rec)
    assert len(evals) == 1, evals
    keys = list(evals[0][2])
    assert sorted(keys) == sorted(_expected_keys(dk=dk if dk is not None else _dk())), keys
    assert evals[0][3] == (str(int(FIXED_NEXT.timestamp()) + 3600),), evals[0]


def test_r24_sync_post_resolve_refusal(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    sh = SvcHarness(monkeypatch, tmp_path, parsed=_parsed("electronics", "electronics"))
    decision = sh.decision(["iphone 15 vs galaxy s24"])
    assert decision.outcome == "proceed"
    caplog.clear()
    res = sh.compare("iphone 15 vs galaxy s24", user_id=UID, fragrance_gate=decision)
    _assert_refusal_dict(res, "electronics")
    assert sh.count("fetch") == 0 and sh.count("profile") == 0 and sh.count("demographics") == 0, sh.rec
    assert sh.count("classify") == 0
    _assert_one_incr(sh.rec)
    assert _gate_messages(caplog) == ["[CATEGORY-GATE] refused stage=post_resolve category=electronics"]


def test_r25_stream_post_resolve_refusal(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path, parsed=_parsed("electronics", "electronics"))
    decision = sh.decision(["iphone 15 vs galaxy s24"])
    events = sh.stream("iphone 15 vs galaxy s24", user_id=UID, fragrance_gate=decision)
    assert [e[0] for e in events] == ["status", "error"], [e[0] for e in events]
    assert events[0][1] == {"message": "Parsing query...", "progress": 10}
    _assert_refusal_dict(events[1][1], "electronics", sync=False)
    assert sh.count("fetch") == 0 and sh.count("profile") == 0
    _assert_one_incr(sh.rec)


def test_r26_chip_is_not_trusted(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path, a2b="electronics")
    decision = sh.decision(["iPhone 15 vs Galaxy S24"])
    assert decision.evidence is False
    res = sh.compare("iPhone 15 vs Galaxy S24", explicit_pair=("iPhone 15", "Galaxy S24"),
                     selected_category="fragrances", user_id=UID, fragrance_gate=decision)
    _assert_refusal_dict(res, "electronics")
    assert [e for e in sh.rec if e[0] == "classify"] == [("classify", ("iPhone 15", "Galaxy S24"))], sh.rec
    assert sh.count("resolve") == 1 and sh.count("fetch") == 0
    _assert_one_incr(sh.rec)


def test_r26b_house_evidence_skips_the_classifier(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path, a2b="electronics")
    decision = sh.decision(["Dior Sauvage vs Bleu de Chanel"])
    assert decision.evidence is True
    res = sh.compare("Dior Sauvage vs Bleu de Chanel", explicit_pair=("Dior Sauvage", "Bleu de Chanel"),
                     selected_category="fragrances", user_id=UID, fragrance_gate=decision)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert sh.count("classify") == 0 and sh.count("fetch") == 2 and not _evals(sh.rec), sh.rec


def test_r26c_no_chip_reuses_the_resolver_classifier(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path, a2b="electronics")
    decision = sh.decision(["iPhone 15 vs Galaxy S24"])
    res = sh.compare("iPhone 15 vs Galaxy S24", explicit_pair=("iPhone 15", "Galaxy S24"),
                     user_id=UID, fragrance_gate=decision)
    _assert_refusal_dict(res, "electronics")
    assert sh.count("classify") == 1, sh.rec  # C11: exactly one A2b call
    assert sh.count("fetch") == 0


@pytest.mark.parametrize("query,names,evidence", [
    ("dior sauvage vs bleu de chanel", (("Dior", "Sauvage"), ("Chanel", "Bleu de Chanel")), True),
    ("khamrah vs hawas", (("", "Khamrah"), ("", "Hawas")), False),
])
def test_r27_parser_other_proceeds(monkeypatch, tmp_path, query, names, evidence):
    """R-S10-3: 'other' from the parse proceeds with or without evidence; the parser
    path never calls the A2b classifier and never counts a refusal."""
    sh = SvcHarness(monkeypatch, tmp_path, parsed=_parsed("other", "other", names[0], names[1]))
    decision = sh.decision([query])
    assert decision.outcome == "proceed" and decision.evidence is evidence
    res = sh.compare(query, user_id=UID, fragrance_gate=decision)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert sh.count("fetch") == 2 and sh.count("classify") == 0 and not _evals(sh.rec), sh.rec


def test_r28_switched_detection_refused(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path,
                    parsed=_parsed("makeup", "makeup", ("Dior", "Rouge 999"), ("Chanel", "Rouge Allure")))
    decision = sh.decision(["dior rouge 999 vs chanel rouge allure"])
    res = sh.compare("dior rouge 999 vs chanel rouge allure", selected_category="fragrances",
                     user_id=UID, fragrance_gate=decision)
    _assert_refusal_dict(res, "makeup")
    assert sh.count("fetch") == 0
    _assert_one_incr(sh.rec)


def test_r29_proceed_keeps_the_compare(monkeypatch, tmp_path):
    sh = SvcHarness(monkeypatch, tmp_path,
                    parsed=_parsed("fragrances", "fragrances", ("Dior", "Sauvage"), ("Chanel", "Bleu de Chanel")))
    decision = sh.decision(["dior sauvage vs bleu de chanel"])
    res = sh.compare("dior sauvage vs bleu de chanel", user_id=UID, fragrance_gate=decision)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert [e for e in sh.rec if e[0] == "fetch"] == [("fetch", 0, "fragrances"), ("fetch", 1, "fragrances")]
    assert not _evals(sh.rec)


def test_r30_classifier_outage_proceeds_uncounted(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    sh = SvcHarness(monkeypatch, tmp_path, a2b="other")
    decision = sh.decision(["Khamrah vs Hawas"])
    assert decision.evidence is False
    caplog.clear()
    res = sh.compare("Khamrah vs Hawas", explicit_pair=("Khamrah", "Hawas"), selected_category="fragrances",
                     user_id=UID, fragrance_gate=decision)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert sh.count("classify") == 1 and sh.count("fetch") == 2, sh.rec
    assert not _evals(sh.rec) and not [m for m in _gate_messages(caplog) if "refused" in m]


@pytest.mark.parametrize("pair", [
    ("Chanel Coco Mademoiselle Hair Mist", "Dior Miss Dior Hair Mist"),
    ("Sol de Janeiro Cheirosa 62 Hair & Body Mist", "Kayali Vanilla 28"),
])
def test_r31_form_hit_overrides_the_name_detection(monkeypatch, tmp_path, pair):
    """R-S10-5 (M37): a concentration / form hit in a product name makes it a fragrance
    on the explicit / vision paths although the name synonym says haircare."""
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    decision = sh.decision([f"{pair[0]} vs {pair[1]}"])
    assert decision.outcome == "proceed"
    res = sh.compare(f"{pair[0]} vs {pair[1]}", explicit_pair=pair, selected_category="fragrances",
                     user_id=UID, fragrance_gate=decision)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert sh.count("fetch") == 2 and not _evals(sh.rec), sh.rec


def test_r32_mixed_pairs_refused_per_product(monkeypatch, tmp_path):
    """R-S10-6 (M36): any product whose chip-free category is a positive non-fragrance."""
    sh = SvcHarness(monkeypatch, tmp_path,
                    parsed=_parsed("fragrances", "electronics", ("Dior", "Sauvage"), ("Apple", "iPhone 15")))
    decision = sh.decision(["dior sauvage vs iphone 15"])
    assert decision.outcome == "proceed" and decision.evidence is True
    res = sh.compare("dior sauvage vs iphone 15", user_id=UID, fragrance_gate=decision)
    _assert_refusal_dict(res, "electronics")
    assert sh.count("fetch") == 0 and sh.count("classify") == 0
    _assert_one_incr(sh.rec)
    sh = SvcHarness(monkeypatch, tmp_path, a2b="fragrances")
    decision = sh.decision(["perfume vs laptop"])
    assert decision.outcome == "proceed"
    res = sh.compare("perfume vs laptop", explicit_pair=("perfume", "laptop"), user_id=UID,
                     fragrance_gate=decision)
    _assert_refusal_dict(res, "electronics")
    assert sh.count("fetch") == 0
    _assert_one_incr(sh.rec)


# ===========================================================================
# R33-R34 (+ P08): a post-resolve refusal through the routes' EXISTING failure arms
# ===========================================================================
def _assert_route_refusal_refund(h, label):
    tags = h.tags()
    assert tags.count("consume") == 1 and tags.count("refund") == 1, h.rec
    assert ("ff", label) in h.rec, h.rec
    assert not [t for t in tags if t in ("record_lifetime", "save", "capture_result_status")], h.rec


@pytest.mark.parametrize("route,label", [("post", "usage_refund.text.post"), ("get", "usage_refund.text.get")])
def test_r33_r34_route_refusal_refund_once(monkeypatch, tmp_path, route, label):
    h = Harness(monkeypatch, tmp_path, flag="true")
    h.plan["result"] = _refusal_literal("electronics")
    resp = h.post({"query": "khamrah vs hawas"}) if route == "post" else h.get({"q": "khamrah vs hawas"})
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = _body(resp)
    assert list(body) == _REFUSAL_KEYS and body == {
        "success": False, "error": REFUSAL_MESSAGE, "code": CODE, "request_id": "s10-rid",
        "category": "electronics", "categories_live": ["fragrances"]}, body
    _assert_route_refusal_refund(h, label)


def test_p08_stream_route_refusal_event_refunds_once(monkeypatch, tmp_path):
    """PIN (green at base): an SSE `error` event carrying the refusal keys reaches the
    wire with the request_id stamp and takes the EXISTING had_error refund arm once
    (no save, no lifetime, no metering), with the full configuration and the flag ON."""
    h = Harness(monkeypatch, tmp_path, flag="true", seed=False)
    refusal = _refusal_literal("electronics")
    h.plan["events"] = [["status", {"message": "Parsing query...", "progress": 10}], ["error", refusal]]
    resp = h.stream({"q": "khamrah vs hawas"})
    assert resp.status_code == 200 and resp.headers.get("content-type", "").startswith("text/event-stream")
    frames = [f for f in resp.text.split("\n\n") if f.strip()]
    errors = [f for f in frames if f.startswith("event: error\n")]
    assert len(errors) == 1, frames
    data = json.loads(errors[0].split("data: ", 1)[1])
    assert data["code"] == CODE and data["category"] == "electronics"
    assert data["categories_live"] == ["fragrances"] and data["request_id"] == "s10-rid", data
    assert ("ff", "usage_refund.text_stream") in h.rec
    _assert_route_refusal_refund(h, "usage_refund.text_stream")


# ===========================================================================
# R36-R40: the camera route (budget before the consume, rules on the identified names)
# ===========================================================================
def test_r36_camera_budget_spent(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    h.redis.store[f"refusal:daily:acct:{UID}:{DAY_TXT}"] = 10
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert list(body) == ["success", "action", "error", "code", "scope", "retry_after_seconds", "resets_at",
                          "categories_live"], body
    assert body["success"] is False and body["action"] == "error" and body["error"] == BUDGET_MESSAGE
    assert body["code"] == CODE and body["scope"] == "refusal_daily" and body["categories_live"] == ["fragrances"]
    assert type(body["retry_after_seconds"]) is int and body["retry_after_seconds"] == 1800
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$", body["resets_at"]), body
    assert not [t for t in h.tags() if t in ("consume", "vision", "compare", "refund", "redis.eval")], h.rec


def test_r37_camera_post_vision_rule1(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true")
    h.plan["vision"] = _vision(("Nivea", "Soft Cream"), ("Dove", "Body Cream"))
    caplog.clear()
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert list(body) == ["success", "action", "error", "code", "category", "categories_live", "vision_cost"], body
    assert body == {"success": False, "action": "error", "error": REFUSAL_MESSAGE, "code": CODE,
                    "category": "skincare", "categories_live": ["fragrances"], "vision_cost": 0.003}, body
    tags = h.tags()
    assert tags.count("vision") == 1 and tags.count("consume") == 1 and tags.count("refund") == 1, h.rec
    assert ("ff", "usage_refund.image.category_not_live") in h.rec, h.rec
    assert not h.compares() and not [t for t in tags if t in ("save", "record_lifetime", "log_search")]
    _assert_one_incr(_with_window_1800_expireat(h.rec))
    assert "[CATEGORY-GATE] refused stage=post_vision category=skincare route=image" in _gate_messages(caplog)


def _with_window_1800_expireat(rec):
    """The route rows run the 1800 s window seam; rewrite the EXPIREAT argument to the
    fixed-window value so _assert_one_incr compares the keys and the arity only."""
    out = []
    for e in rec:
        if e[0] == "redis.eval":
            assert len(e[3]) == 1 and e[3][0].isdigit(), e
            out.append((e[0], e[1], e[2], (str(int(FIXED_NEXT.timestamp()) + 3600),)))
        else:
            out.append(e)
    return out


def test_r38_camera_post_resolve_never_comparison_failed(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true")
    monkeypatch.setenv("ENABLE_CAMERA_FAILURE_ENVELOPE", "true")
    h.plan["vision"] = _vision(("Lattafa", "Khamrah"), ("Armaf", "Club de Nuit"))
    h.plan["camera_result"] = _refusal_literal("electronics")
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert body.get("action") == "error", body
    assert body == {"success": False, "action": "error", "error": REFUSAL_MESSAGE, "code": CODE,
                    "category": "electronics", "categories_live": ["fragrances"], "vision_cost": 0.003}, body
    tags = h.tags()
    assert tags.count("refund") == 1 and len(h.compares()) == 1, h.rec
    assert not [t for t in tags if t in ("save", "record_lifetime", "log_search")], h.rec


def test_r39_camera_fragrance_proceeds(monkeypatch, tmp_path):
    h_off = Harness(monkeypatch, tmp_path, flag=None)
    off = h_off.camera(2)
    h = Harness(monkeypatch, tmp_path, flag="true")
    resp = h.camera(2)
    assert resp.status_code == 200 == off.status_code
    compares = h.compares()
    assert len(compares) == 1 and "fragrance_gate" in compares[0][2], compares
    assert compares[0][4]["outcome"] == "proceed" and compares[0][4]["evidence"] is True
    assert resp.text == off.text  # the delivery body equals the flag-OFF body plus nothing


def test_r40_camera_single_product_rule1(monkeypatch, tmp_path):
    """R-S10-13: a rule-1 product in the 1-product exit answers CATEGORY_NOT_LIVE."""
    h = Harness(monkeypatch, tmp_path, flag="true")
    h.plan["vision"] = _vision(("Nivea", "Soft Cream"))
    resp = h.camera(1)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert body == {"success": False, "action": "error", "error": REFUSAL_MESSAGE, "code": CODE,
                    "category": "skincare", "categories_live": ["fragrances"], "vision_cost": 0.003}, body
    assert h.tags().count("refund") == 1 and not h.compares(), h.rec
    assert len(_evals(h.rec)) == 1, h.rec
    h = Harness(monkeypatch, tmp_path, flag="true")
    h.plan["vision"] = _vision(("Dior", "Sauvage EDP"))
    body = _body(h.camera(1))
    assert body.get("action") == "need_second_product" and body.get("success") is True, body


# ===========================================================================
# R41-R42 (+ P07): the error envelope block
# ===========================================================================
def _handle(status, detail):
    scope = {"type": "http", "method": "GET", "path": "/s10", "headers": [], "query_string": b""}
    req = _StarletteRequest(scope)
    req.state.request_id = "s10-rid"
    resp = _run(error_handler.http_exception_handler(req, HTTPException(status_code=status, detail=detail)))
    return resp.status_code, json.loads(resp.body), {k.lower(): v for k, v in resp.headers.items()}


_REFUSAL_DETAIL = {"code": CODE, "error": REFUSAL_MESSAGE, "category": "electronics", "categories_live": ["fragrances"]}
_BUDGET_DETAIL = {"code": CODE, "error": BUDGET_MESSAGE, "scope": "refusal_daily", "retry_after": 1800,
                  "resets_at": "2026-10-30T00:00:00+03:00", "categories_live": ["fragrances"]}


def test_r41_handler_passthrough(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    status, body, headers = _handle(400, dict(_REFUSAL_DETAIL))
    assert status == 400 and list(body) == _REFUSAL_KEYS, body
    assert body == {"success": False, "error": REFUSAL_MESSAGE, "code": CODE, "request_id": "s10-rid",
                    "category": "electronics", "categories_live": ["fragrances"]}, body
    status, body, headers = _handle(429, dict(_BUDGET_DETAIL))
    assert status == 429 and list(body) == _BUDGET_KEYS, body
    assert body["scope"] == "refusal_daily" and body["resets_at"] == "2026-10-30T00:00:00+03:00"
    assert body["retry_after_seconds"] == 1800 and headers.get("retry-after") == "1800", (body, headers)
    assert body["categories_live"] == ["fragrances"] and "category" not in body


def test_r42_handler_sanitises(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    keys = getattr(error_handler, "_CANONICAL_CATEGORY_KEYS", None)
    assert isinstance(keys, tuple), "S81-10: error_handler._CANONICAL_CATEGORY_KEYS (a tuple literal) is missing"
    assert set(keys) == set(extraction_service._CANONICAL_CATEGORIES) and len(keys) == len(set(keys))
    bad = dict(_REFUSAL_DETAIL, category="weapons", categories_live="fragrances")
    _, body, _ = _handle(400, bad)
    assert list(body) == ["success", "error", "code", "request_id"], body
    for live in ([1], ["weapons"], [], ["fragrances", 3]):
        _, body, _ = _handle(400, dict(_REFUSAL_DETAIL, categories_live=live))
        assert "categories_live" not in body and body.get("category") == "electronics", (live, body)
    _, body, headers = _handle(429, dict(_BUDGET_DETAIL, scope="daily", resets_at=5))
    assert "scope" not in body and "resets_at" not in body and body["retry_after_seconds"] == 1800, body
    for code in ("USAGE_LIMIT", "INSUFFICIENT_DATA", "NOT_PRODUCT_PAGE"):
        detail = dict(_BUDGET_DETAIL, code=code, category="electronics")
        _, body, _ = _handle(429 if code == "USAGE_LIMIT" else 400, detail)
        for extra in ("category", "categories_live", "scope", "resets_at"):
            assert extra not in body, (code, body)
    # the passthrough itself is present (so the sanitising above is not vacuous)
    _, body, _ = _handle(400, dict(_REFUSAL_DETAIL))
    assert body.get("categories_live") == ["fragrances"], body


@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p07_handler_flag_off_keeps_the_base_keys(monkeypatch, spelling):
    """PIN (C6, kills M15): flag OFF the CATEGORY_NOT_LIVE details reach the wire with
    the base keys only (+ the existing W1-9 retry fields on the 429)."""
    _set_flag(monkeypatch, spelling)
    status, body, headers = _handle(400, dict(_REFUSAL_DETAIL))
    assert status == 400 and body == {"success": False, "error": REFUSAL_MESSAGE, "code": CODE,
                                      "request_id": "s10-rid"}, body
    status, body, headers = _handle(429, dict(_BUDGET_DETAIL))
    assert status == 429 and body == {"success": False, "error": BUDGET_MESSAGE, "code": CODE,
                                      "request_id": "s10-rid", "retry_after_seconds": 1800}, body
    assert headers.get("retry-after") == "1800"


# ===========================================================================
# R43-R48: the budget mechanics (script, record, reset fields, the two seams)
# ===========================================================================
def test_r43_incr_script_static():
    gate = _gate_or_fail()
    script = _attr(gate, "REFUSAL_INCR_SCRIPT")
    assert _normalized_script(script) == _normalized_script(EXPECTED_SCRIPT), script
    assert script.count("KEYS[i]") == 2 and script.count("ARGV[1]") == 1 and "ARGV[2]" not in script
    assert "'EXPIRE'" not in script and "'SET'" not in script


def _subject(gate, header=True, user=USER):
    tokens = request_context.bind_from_headers([(b"x-device-fingerprint", FP.encode("ascii"))]) if header else None
    try:
        return gate.budget_subject(user)
    finally:
        if tokens is not None:
            request_context.reset_request_context(tokens)


@pytest.mark.parametrize("cls,shape", [(FakeRedis, "positional"), (FakeUpstash, "keyword")])
def test_r44_record_both_client_shapes(monkeypatch, tmp_path, caplog, cls, shape):
    gate = _gate_or_fail()
    _full_config(monkeypatch, tmp_path)
    monkeypatch.setattr(gate, "reset_window", _window_fixed)
    expireat = int(FIXED_NEXT.timestamp()) + 3600
    dk = _dk()
    for header, expected in ((True, _expected_keys(dk=dk)), (False, _expected_keys(dk=None))):
        rec = []
        fake = cls(rec)
        monkeypatch.setattr(cache_service, "redis_client", fake)
        _run(gate.record_refusal_async(_subject(gate, header=header)))
        evals = _evals(rec)
        assert len(evals) == 1 and evals[0][1] == shape, rec
        assert sorted(evals[0][2]) == sorted(expected) and len(evals[0][2]) == len(expected), evals
        assert evals[0][3] == (str(expireat),), evals
        for key in expected:
            assert fake.store.get(key) == 1 and fake.expireat.get(key) == expireat, (key, fake.store, fake.expireat)
    rec = []
    monkeypatch.setattr(cache_service, "redis_client", cls(rec))
    _run(gate.record_refusal_async(None))
    assert rec == []
    caplog.set_level(logging.INFO)
    caplog.clear()
    rec = []
    monkeypatch.setattr(cache_service, "redis_client", cls(rec, raising="eval"))
    _run(gate.record_refusal_async(_subject(gate)))
    assert [m for m in _gate_messages(caplog) if "record failed" in m] == [
        "[CATEGORY-GATE] budget record failed type=RuntimeError"]


def test_r45_reset_fields():
    gate = _gate_or_fail()
    fields = _attr(gate, "retry_fields")
    now = datetime(2026, 10, 29, 20, 30, tzinfo=timezone.utc)
    assert fields(now, datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc), 3) == (1800, "2026-10-30T00:00:00+03:00")
    assert fields(now, datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc), 0) == (12600, "2026-10-30T00:00:00+00:00")
    nxt = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)
    assert fields(nxt - timedelta(milliseconds=200), nxt, 0)[0] == 1
    assert fields(nxt + timedelta(seconds=5), nxt, 0)[0] == 1
    assert fields(nxt - timedelta(days=3), nxt, 0)[0] == 86400
    assert type(fields(now, nxt, 0)[0]) is int and type(fields(now, nxt, 0)[1]) is str


def test_r46_reset_window_seam():
    """R-S10-11: the window seam IS usage_service._usage_window (S81-09) when present,
    else the UTC-midnight fallback; next_reset strictly after now."""
    gate = _gate_or_fail()
    window = _attr(gate, "reset_window")
    helper = getattr(usage_service, "_usage_window", None)
    for now in (datetime(2026, 10, 29, 20, 30, tzinfo=timezone.utc),
                datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 29, 23, 59, 59, tzinfo=timezone.utc),
                datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)):
        day, nxt, offset = window(now)
        assert isinstance(day, date) and nxt.tzinfo is not None and nxt > now, (now, day, nxt)
        if helper is not None:
            h_day, h_next = helper(now)
            assert (day, nxt) == (h_day, h_next), (now, day, nxt, h_day, h_next)
            riyadh = getattr(usage_service, "riyadh_reset_enabled", None)
            assert offset == ((3 if riyadh() else 0) if callable(riyadh) else offset) and offset in (0, 3)
        else:
            assert day == now.date() and offset == 0
            assert nxt == datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)


def test_r47_budget_exempt_allow_list(monkeypatch, tmp_path):
    """R-S10-7: an allow-listed account is exempt from the BUDGET, never from the rules."""
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    monkeypatch.setenv("DEVICE_QUOTA_EXEMPT_USER_IDS", "  junk, " + UID.upper() + " ;x")
    h.redis.store[f"refusal:daily:acct:{UID}:{DAY_TXT}"] = 10
    resp = h.post({"query": "khamrah vs hawas"})
    assert resp.status_code == 200, resp.text[:300]
    assert len(h.compares()) == 1 and h.tags().count("consume") == 1
    resp = h.post({"query": "best laptop vs dell laptop"})
    assert resp.status_code == 400 and _body(resp)["code"] == CODE
    gate = _gate_or_fail()
    exempt = _attr(gate, "budget_exempt_async")
    assert _run(exempt(UID)) is True
    assert _run(exempt(UID2)) is False


def test_r48_budget_exempt_premium(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    key = f"refusal:daily:acct:{UID}:{DAY_TXT}"
    h.redis.store[key] = 10
    h.plan["tier"] = "premium"
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert h.tags().count("tier_read") == 1 and len(h.compares()) == 1, h.rec
    h.plan["tier"] = "free"
    assert h.post({"query": "khamrah vs hawas"}).status_code == 429
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    assert h.post({"query": "khamrah vs hawas"}).status_code == 200
    assert "tier_read" not in h.tags(), h.rec  # read only when a budget is spent


# ===========================================================================
# R49-R51: the surfaces (smart pick, trending, /app/version); History stays whole (P03)
# ===========================================================================
def _home_io(rec):
    return [e for e in rec if e[0] in ("supabase", "home_cache_get", "home_cache_set")]


def test_r49_smart_pick_filtered(monkeypatch, tmp_path):
    h_off = Harness(monkeypatch, tmp_path, flag=None)
    off = _body(h_off.path("/api/v1/home/smart-pick"))
    assert off["smart_pick"]["comparison_id"] == "cmp-1"  # base: the newest row, electronics
    h = Harness(monkeypatch, tmp_path, flag="true")
    on = _body(h.path("/api/v1/home/smart-pick"))
    assert on["empty_state"] is False and on["smart_pick"]["comparison_id"] == "cmp-2", on
    assert _home_io(h.rec) == _home_io(h_off.rec), (_home_io(h.rec), _home_io(h_off.rec))
    h2 = Harness(monkeypatch, tmp_path, flag="true")
    h2.plan["supabase"]["comparisons"] = [
        _comparison_row("cmp-%d" % i, cat, "2026-10-2%dT10:00:00Z" % i)
        for i, cat in enumerate(("electronics", "skincare", "makeup", "fashion", "grocery"), start=1)
    ]
    body = _body(h2.path("/api/v1/home/smart-pick"))
    assert body == {"smart_pick": None, "empty_state": True, "cta_text_key": "home.smart_pick.empty_cta"}, body


@pytest.mark.parametrize("region", ["bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"])
def test_r50_trending_filtered(monkeypatch, tmp_path, region):
    h_off = Harness(monkeypatch, tmp_path, flag=None, user=None)
    off = _body(h_off.path("/api/v1/home/trending", {"region": region}))
    h = Harness(monkeypatch, tmp_path, flag="true", user=None)
    on = _body(h.path("/api/v1/home/trending", {"region": region}))
    expected = [e for e in off["trending"] if extraction_service.canonicalize_category(e["tag"]) == "fragrances"]
    assert len(expected) == 1, expected  # measured: one Fragrances entry per region (L6)
    assert on == {"trending": expected, "region": region}, on
    assert [e for e in h.rec if e[0] == "home_cache_get"] == [("home_cache_get", f"home:trending:fragrances:{region}")]
    assert [e for e in h.rec if e[0] == "home_cache_set"] == [
        ("home_cache_set", f"home:trending:fragrances:{region}", 3600)]
    assert [e for e in h_off.rec if e[0] == "home_cache_get"] == [("home_cache_get", f"home:trending:{region}")]


def test_r51_version_categories_live(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true")
    body = _body(h.path("/api/v1/app/version"))
    assert list(body) == ["min_version", "latest_version", "force_update", "update_url_ios",
                          "update_url_android", "categories_live"], body
    assert body["categories_live"] == ["fragrances"]


# ===========================================================================
# R52-R57: hygiene, seams, static shapes
# ===========================================================================
def test_r52_log_hygiene(monkeypatch, tmp_path, caplog):
    """C5: every record of the category_gate logger and every [CATEGORY-GATE] record
    from any logger carries no query text, fingerprint, device key or account id."""
    caplog.set_level(logging.DEBUG)
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10")
    dk = _dk()
    acct = f"refusal:daily:acct:{UID}:{DAY_TXT}"
    caplog.clear()
    h.post({"query": "laptop " + SENTINEL + " vs dell laptop"})
    h.redis.store[acct] = 10
    h.post({"query": "khamrah " + SENTINEL + " vs hawas"})
    h.redis.store[acct] = 0
    h.plan["vision"] = _vision(("Nivea", "Soft Cream " + SENTINEL), ("Dove", "Body Cream"))
    h.camera(2)
    sh = SvcHarness(monkeypatch, tmp_path,
                    parsed=_parsed("electronics", "electronics", ("Apple", "iPhone " + SENTINEL), ("Samsung", "Galaxy")))
    decision = sh.decision(["iphone " + SENTINEL + " vs galaxy"])
    sh.compare("iphone " + SENTINEL + " vs galaxy", user_id=UID, fragrance_gate=decision)
    records = [r for r in caplog.records
               if r.name == GATE_LOGGER or r.getMessage().startswith("[CATEGORY-GATE]")]
    messages = [r.getMessage() for r in records]
    assert sum(m.startswith("[CATEGORY-GATE] refused") for m in messages) >= 3, messages
    assert sum(m.startswith("[CATEGORY-GATE] budget spent") for m in messages) == 1, messages
    for record in records:
        msg = record.getMessage()
        for secret in (SENTINEL, FP, dk, UID):
            assert secret not in msg, (secret[:6], msg)
        if msg.startswith("[CATEGORY-GATE]"):
            assert LOG_GRAMMAR.match(msg), msg
        assert record.levelno < logging.ERROR, msg


def test_r53_kb_seam_fails_open(monkeypatch, tmp_path, caplog):
    gate = _gate_or_fail()
    _full_config(monkeypatch, tmp_path)
    rec = []
    monkeypatch.setattr(cache_service, "redis_client", FakeRedis(rec))
    from app.services import database_service

    def _no_client(*a, **k):
        rec.append(("supabase_client",))
        raise AssertionError("the KB seam performed I/O")
    monkeypatch.setattr(database_service, "get_admin_supabase_client", _no_client)
    monkeypatch.setattr(database_service, "get_user_supabase_client", _no_client)
    seam = _attr(gate, "kb_evidence")
    assert seam(["dior sauvage vs bleu de chanel"]) is False
    assert rec == []
    caplog.set_level(logging.INFO)

    def _boom(texts):
        raise RuntimeError("s10 probe: kb")
    monkeypatch.setattr(gate, "kb_evidence", _boom)
    caplog.clear()
    try:
        decision = gate.evaluate(["iphone 15 vs galaxy s24"])
    except Exception as exc:  # noqa: BLE001 - a propagated seam failure is the defect
        raise AssertionError(f"a raising KB seam must fail open; evaluate raised {type(exc).__name__}")
    assert decision.outcome == "proceed" and decision.evidence is False, decision
    assert [m for m in _gate_messages(caplog) if "kb lookup" in m] == ["[CATEGORY-GATE] kb lookup failed type=RuntimeError"]
    monkeypatch.setattr(gate, "kb_evidence", lambda texts: True)
    assert gate.evaluate(["iphone 15 vs galaxy s24"]).evidence is True


def _load_golden():
    assert GOLDEN_PATH.exists(), "tests/fixtures/s81_s10_flag_off_golden.json is missing"
    return json.loads(GOLDEN_PATH.read_text(encoding="ascii"))


def _assert_matches_golden(out, golden):
    assert sorted(out) == sorted(golden["scenarios"]), (sorted(out), sorted(golden["scenarios"]))
    for name in sorted(out):
        got, exp = out[name], golden["scenarios"][name]
        assert got["gate_lines"] == [], (name, got["gate_lines"])
        for field in ("calls", "status", "headers", "body", "logs"):
            assert json.loads(json.dumps(got[field])) == exp[field], (name, field, got[field], exp[field])


@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_r54_off_calls_nothing_of_the_gate(monkeypatch, tmp_path, caplog, spelling):
    gate = _gate_or_fail()
    assert callable(getattr(gate, "evaluate", None))
    out, called = _run_golden(monkeypatch, tmp_path, caplog, spelling, raising=True)
    assert called == [], called
    _assert_matches_golden(out, _load_golden())


_LEAF_NEEDLES = ("device_key_pepper", "x-ai-consent-version", "x-compare-request-id", "header_state")
_P07_NEEDLE = 'valid_device_fingerprint(request.headers.get("x-device-fingerprint"))'


def test_r55_request_context_consumer_shape():
    """R-S10-2 (the S81-06 E9 form for test_s05_p01): category_gate.py is the only new
    consumer of the leaf: one function-local `from app.utils import request_context as
    _request_context`, attribute uses within {device_fingerprint, device_key}, none of the
    needle strings; the routes keep their single header read (p07)."""
    assert GATE_FILE.exists(), "S81-10: app/services/category_gate.py does not exist"
    text = GATE_FILE.read_text(encoding="utf-8")
    low = text.lower()
    for needle in _LEAF_NEEDLES:
        assert needle not in low, needle
    tree = ast.parse(text)
    froms = [n for n in ast.walk(tree)
             if isinstance(n, ast.ImportFrom) and any(a.name == "request_context" for a in n.names)]
    assert [(n.module, [(a.name, a.asname) for a in n.names]) for n in froms] == [
        ("app.utils", [("request_context", "_request_context")])], froms
    assert froms[0] not in tree.body, "the leaf import must be function-local"
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in ("app.utils.request_context", "app.middleware.request_context"), node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "request_context" not in alias.name, alias.name
    used = {n.attr for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "_request_context"}
    assert used and used <= {"device_fingerprint", "device_key"}, used
    for rel in ("app/api/text_routes.py", "app/api/image_routes.py", "app/middleware/error_handler.py",
                "app/api/version_routes.py", "app/api/home_routes.py",
                "app/services/structured_comparison_service.py"):
        assert "request_context" not in (ROOT / rel).read_text(encoding="utf-8", errors="replace"), rel
    for rel in ("app/api/text_routes.py", "app/api/image_routes.py"):
        assert (ROOT / rel).read_text(encoding="utf-8", errors="replace").count(_P07_NEEDLE) == 1, rel


_CENSUS_USER_RX = re.compile(r"(^|\W)(user_id|uid)($|\W)|current_user\s*\[")
_CENSUS_PREFIX_RX = re.compile(r"^[a-z][a-z0-9_]*(:[a-z0-9_]+)*:$")


def test_r56_budget_key_fstrings_census_shape():
    """C15 / E1: the two key writers are literal f-strings: the account one interpolates
    `user_id` (the 043 census KEPT row 'refusal:daily:acct:{user_id}:{*}'), the device one
    `device_key` (no census hit)."""
    assert GATE_FILE.exists(), "S81-10: app/services/category_gate.py does not exist"
    tree = ast.parse(GATE_FILE.read_text(encoding="utf-8"))
    acct, dev, census = [], [], set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr) or not node.values:
            continue
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append((str(v.value), None))
            elif isinstance(v, ast.FormattedValue):
                parts.append(("", ast.unparse(v.value)))
        if parts and parts[0][1] is None and _CENSUS_PREFIX_RX.match(parts[0][0]):
            if any(e is not None and _CENSUS_USER_RX.search(e) for _c, e in parts):
                census.add("".join(c if e is None else ("{user_id}" if _CENSUS_USER_RX.search(e) else "{*}")
                                   for c, e in parts))
        if parts and parts[0][0] == "refusal:daily:acct:":
            acct.append(parts)
        if parts and parts[0][0] == "refusal:daily:dev:":
            dev.append(parts)
    assert len(acct) == 1 and acct[0][1] == ("", "user_id") and acct[0][2] == (":", None) and len(acct[0]) == 4, acct
    assert len(dev) == 1 and dev[0][1] == ("", "device_key") and dev[0][2] == (":", None) and len(dev[0]) == 4, dev
    assert not _CENSUS_USER_RX.search(dev[0][3][1] or ""), dev
    assert census == {"refusal:daily:acct:{user_id}:{*}"}, census


def test_r57_constants_bodies_and_repr(monkeypatch, tmp_path):
    gate = _gate_or_fail()
    assert gate.CODE == CODE and tuple(gate.CATEGORIES_LIVE) == ("fragrances",)
    assert gate.SCOPE_REFUSAL_DAILY == "refusal_daily"
    assert gate.REFUSAL_MESSAGE == REFUSAL_MESSAGE and gate.BUDGET_MESSAGE == BUDGET_MESSAGE
    for msg in (gate.REFUSAL_MESSAGE, gate.BUDGET_MESSAGE):
        assert msg.isascii() and not any(w in msg.lower() for w in ("couldn't", "try again", "failed to"))
    assert gate.KEY_PREFIX_DEV == "refusal:daily:dev:" and gate.KEY_PREFIX_ACCT == "refusal:daily:acct:"
    assert list(gate.refusal_result("electronics").items()) == [
        ("success", False), ("error", REFUSAL_MESSAGE), ("code", CODE), ("category", "electronics"),
        ("categories_live", ["fragrances"])]
    assert list(gate.refusal_detail("skincare").items()) == [
        ("code", CODE), ("error", REFUSAL_MESSAGE), ("category", "skincare"), ("categories_live", ["fragrances"])]
    assert list(gate.budget_detail(60, "2026-10-30T00:00:00+00:00").items()) == [
        ("code", CODE), ("error", BUDGET_MESSAGE), ("scope", "refusal_daily"), ("retry_after", 60),
        ("resets_at", "2026-10-30T00:00:00+00:00"), ("categories_live", ["fragrances"])]
    _full_config(monkeypatch, tmp_path)
    decision = gate.evaluate(["khamrah vs hawas"], subject=_subject(gate))
    assert dataclasses.is_dataclass(decision)
    names = [f.name for f in dataclasses.fields(decision)]
    assert names[:4] == ["outcome", "category", "evidence", "subject"], names
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.outcome = "refuse"
    assert decision.subject is not None
    text = repr(decision)
    assert UID not in text and _dk() not in text and FP not in text, text
    assert sorted(gate.budget_keys(decision.subject, DAY)) == sorted(_expected_keys(dk=_dk()))


# ===========================================================================
# PIN rows (green at the base; full configuration + call recorders, ruling B1)
# ===========================================================================
@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p01_flag_off_golden(monkeypatch, tmp_path, caplog, spelling):
    """Five OFF spellings x the twelve scenarios: calls (order + arguments), status,
    content-type / retry-after headers, raw body text and the five loggers' lines equal
    the committed golden; with category_gate present every public function but the
    flag reader raises when called."""
    out, called = _run_golden(monkeypatch, tmp_path, caplog, spelling, raising=True)
    if os.environ.get("S81_S10_RECORD_GOLDEN") == "1":
        if spelling is not None:
            pytest.skip("recording run: only the unset spelling writes the golden")
        data = {
            "meta": {
                "unit": "S81-10 FRAGRANCE-ONLY-GATE",
                "recorded_at_base": "6c14ac954f601902d322547de04982033aca5925",
                "recorded_with": "ENABLE_FRAGRANCE_ONLY_GATE unset; full configuration (REFUSAL_DAILY_BUDGET=1, "
                                 "a run-time lexicon, the device header bound with a synthetic pepper, "
                                 "ENABLE_PAID_ROUTE_METERING=true, refusal counters seeded above the budget)",
                "scenarios": len(out),
            },
            "scenarios": {k: {f: out[k][f] for f in ("calls", "status", "headers", "body", "logs")}
                          for k in sorted(out)},
        }
        GOLDEN_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=1) + "\n", encoding="ascii", newline="\n")
        pytest.fail("S81_S10_RECORD_GOLDEN=1: the golden was written; re-run without it")
    assert called == [], called
    _assert_matches_golden(out, _load_golden())


def test_p02_non_target_callers_ungated(monkeypatch, tmp_path):
    h = Harness(monkeypatch, tmp_path, flag="true", budget="1", seed=True)
    resp = h.quick({"product1": "best laptop", "product2": "dell laptop"})
    assert resp.status_code == 200, resp.text[:300]
    compares = h.compares()
    assert len(compares) == 1 and "fragrance_gate" not in compares[0][2], compares
    assert not [t for t in h.tags() if t in _REDIS], h.rec
    for rel in ("app/api/url_routes.py", "app/services/url_extraction_service.py"):
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for needle in ("category_gate", "fragrance_gate", CODE, FLAG):
            assert needle not in text, (rel, needle)
    tree = ast.parse((ROOT / "scripts" / "cron_warm_price_cache.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", None) in ("compare_from_text", "compare_from_text_streaming")]
    assert calls and all("fragrance_gate" not in {k.arg for k in c.keywords} for c in calls)


CID = "-".join(["0ddba11a", "feed", "4bad", "9cab", "beadedfacade"])


def test_p03_history_whole_under_flag(monkeypatch, tmp_path):
    rows = []
    for id_, cat in ((CID, "electronics"), ("cmp-2", "fragrances")):
        row = _comparison_row(id_, cat, "2026-10-29T10:00:00Z")
        row.update({"query": "a vs b", "product_names": ["a", "b"], "input_type": "text", "user_id": UID})
        rows.append(row)
    seen = []
    monkeypatch.setattr(history_routes, "get_user_comparisons",
                        lambda **kw: (seen.append(("list", kw.get("limit"), kw.get("offset"))), _coro(rows))[1])
    monkeypatch.setattr(history_routes, "get_user_comparison_count",
                        lambda uid, access_token=None, **kw: (seen.append(("count",)), _coro(len(rows)))[1])
    monkeypatch.setattr(history_routes, "get_comparison_by_id",
                        lambda cid, access_token=None, **kw: (seen.append(("get", cid)), _coro(rows[0]))[1])
    bodies = {}
    for spelling in (None, "true"):
        h = Harness(monkeypatch, tmp_path, flag=spelling, budget="1", seed=True)
        lst = h.path("/api/v1/comparisons/history")
        one = h.path("/api/v1/comparisons/" + CID)
        assert lst.status_code == 200 and one.status_code == 200, (lst.text[:200], one.text[:200])
        bodies[spelling] = (lst.text, one.text)
    assert bodies[None] == bodies["true"]
    assert _body_text_total(bodies["true"][0]) == 2
    assert seen.count(("count",)) == 2


def _body_text_total(text):
    return json.loads(text)["total"]


@pytest.mark.parametrize("spelling", [None, "false", "true"])
def test_p04_surface_failure_mapping_unchanged(monkeypatch, spelling):
    _set_flag(monkeypatch, spelling)
    surface = text_routes._surface_comparison_failure
    cu = {"success": False, "error": "We don't compare this category", "code": "CONTENT_UNAVAILABLE",
          "layer": "query_prefilter"}
    assert surface(dict(cu)) == cu
    for code, status in (("TIMEOUT", 503), ("LLM_UNAVAILABLE", 503), ("INSUFFICIENT_DATA", 400)):
        with pytest.raises(HTTPException) as info:
            surface({"success": False, "error": "m", "code": code})
        assert info.value.status_code == status and info.value.detail == {"code": code, "error": "m"}
    with pytest.raises(HTTPException) as info:
        surface({"success": False, "error": "Comparison failed"})
    assert info.value.status_code == 400 and info.value.detail == "Comparison failed"
    with pytest.raises(HTTPException) as info:
        surface({"success": False, "error": "Traceback probe"})
    assert info.value.detail == {"code": "INTERNAL_ERROR", "error": text_routes.INTERNAL_ERROR_FRIENDLY_MESSAGE}


_P05_STATES = OFF_SPELLINGS + ["true"]
_P05_IDS = OFF_IDS + ["on"]


@pytest.mark.parametrize("entry", ["sync", "stream"])
@pytest.mark.parametrize("path", ["q", "pair"])
@pytest.mark.parametrize("spelling", _P05_STATES, ids=_P05_IDS)
def test_p05_orchestrator_order_without_the_kwarg(monkeypatch, tmp_path, spelling, path, entry):
    """C10 / M34: with NO fragrance_gate kwarg (every non-target caller and every flag-OFF
    route call) the orchestrator makes the base calls in the base order on NON-fragrance
    scenarios, flag ON included, with the full configuration and a bound device header."""
    sh = SvcHarness(monkeypatch, tmp_path, flag=spelling, a2b="electronics",
                    parsed=_parsed("electronics", "electronics"), budget="1", seed=True)
    if path == "q":
        query, kw = "iphone 15 vs galaxy s24", {}
        expected = [("parse", query), ("resolve", True)]
    else:
        query, kw = "iPhone 15 vs Galaxy S24", {"explicit_pair": ("iPhone 15", "Galaxy S24")}
        expected = [("resolve", False), ("classify", ("iPhone 15", "Galaxy S24"))]
    expected += [("profile", UID), ("demographics", UID), ("fetch", 0, "electronics"), ("fetch", 1, "electronics")]
    tokens = request_context.bind_from_headers([(b"x-device-fingerprint", FP.encode("ascii"))])
    try:
        if entry == "sync":
            res = sh.compare(query, user_id=UID, **kw)
            assert res.get("code") == "INSUFFICIENT_DATA", res
        else:
            events = sh.stream(query, user_id=UID, **kw)
            assert [e[0] for e in events] == ["status", "status", "settle_complete", "complete"], events
            assert events[-1][1].get("code") == "INSUFFICIENT_DATA"
    finally:
        request_context.reset_request_context(tokens)
    assert sh.rec == expected, sh.rec


def test_p06_admin_key_path_bypasses_the_gate(monkeypatch, tmp_path, caplog):
    """R-S10-8: the admin-key harness path (U13 admin credential, anonymous) is never gated."""
    caplog.set_level(logging.INFO)
    h = Harness(monkeypatch, tmp_path, flag="true", budget="1", seed=True, user=None, auth_required=True)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    caplog.clear()
    resp = h.post({"query": "best laptop vs dell laptop"})
    assert resp.status_code == 200, resp.text[:300]
    compares = h.compares()
    assert len(compares) == 1 and "fragrance_gate" not in compares[0][2], compares
    assert not [t for t in h.tags() if t in _REDIS], h.rec
    assert not _gate_messages(caplog)

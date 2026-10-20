"""B3 VISION-IDENTITY-V2 (ENABLE_VISION_IDENTITY_V2) -- RED tests, session 80.

Spec: .qa-s80/B3_UNIT_SPEC.md of the unit worktree, as amended by the
adversarial review (.qa-s80/B3_SPEC_REVIEW.md) and by the orchestrator's
binding rulings B3-R1..B3-R7 (RULINGS_BATCH1.md, section "B3"). Base
81df2b641454e0301cca51a3ba01bf8ef3d7e649.

Row classes (each test name opens with its row id):
  RED  fails at base on an AssertionError only (a symbol the unit adds is read
       with getattr(..., None) and asserted, never attribute-accessed; a call
       that must raise / must not raise is run through _capture(), never
       pytest.raises, so a base run never ends on Failed/KeyError/IndexError).
  PIN  green at base; runs with the FULL unit configuration (the flag in the
       stated state, VISION_TIMEOUT_SECONDS and OPENAI_MODEL_VISION set,
       metering + envelope ON where the route is involved) plus a recorder, so
       a "not gated" mutant is killable (ruling B1, session 79).

Rulings applied here (B3-R6): one image -> the best TWO candidates at
image_index 0, else one best per image_index; an image_index that does not
name one of the request's images is KEPT unpaired (_image_index None),
appended after the paired picks in reply order, counted as unpaired_index;
the category schema is anyOf [{type string, enum of nine}, {type null}]; the
[VISION_V2] counts line carries unknown_brand / unknown_name; is_product false
candidates are dropped; _VISION_V2_MAX_TOKENS is 1000; the orchestrator's
identity dicts carry _vision_image_index. B3-R1: P8 scopes the hygiene check
to the unit's own [VISION_V2] / [IMAGE] preferences records. B3-R2: R9 is three
COERCE items at image_index 0/1/2 with IMG(3).

Hermetic: the OpenAI client object openai_service.client is replaced by a
recorder returning types.SimpleNamespace replies; the camera route's usage,
history, search-log, moderation and compare collaborators are stubs; every
flag the rows depend on is set or deleted explicitly. No network, no .env,
no real credential (the dummy key below is built by concatenation).
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import os
import re
import time
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-" + "b3-unit-dummy-key"

import app.main  # noqa: F401,E402  (configure_logging + the dotenv sanitizer first)
from app.main import app as fastapi_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import image_routes  # noqa: E402
from app.api.auth_routes import get_optional_user  # noqa: E402
from app.middleware.rate_limiter import limiter  # noqa: E402
from app.services import (  # noqa: E402
    api_budget_service,
    content_safety_service,
    extraction_service,
    feedback_service,
    usage_service,
)
from app.services import openai_service as osvc  # noqa: E402
from app.services import structured_comparison_service as scs  # noqa: E402
from app.services.structured_comparison_service import (  # noqa: E402
    LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
)

FLAG = "ENABLE_VISION_IDENTITY_V2"
KNOB = "VISION_TIMEOUT_SECONDS"
METER = "ENABLE_PAID_ROUTE_METERING"
ENVELOPE = "ENABLE_CAMERA_FAILURE_ENVELOPE"

UNIT_ENV = (
    FLAG,
    KNOB,
    "OPENAI_MODEL_VISION",
    "ENABLE_LLM_PREFLIGHT_BREAKER",
    METER,
    ENVELOPE,
    "ENABLE_ANON_USAGE_GATE",
    "ENABLE_SEARCH_LOG_TRUTH",
    "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
    "ENABLE_COMPARE_AUTH_REQUIRED",
    "ENABLE_SYNC_DB_OFFLOAD",
    "ENABLE_STRICT_OPTIONAL_AUTH",
)

# The base vision prompt as sent (openai_service.py:135-162), measured by the
# spec through the real function with a fake client (spec 1.7).
VISION_PROMPT_SHA_OFF = "bb737687c40969abb4dea936f522d5be4a0693bcd5e2f7b09e28a78204462ae3"
VISION_KWARGS_OFF = {"model", "messages", "max_tokens", "temperature", "store"}

PUBLIC_KEYS = ("brand", "name", "size_or_count", "visible_price", "confidence")
INTERNAL_KEYS = (
    "_image_index", "_category", "_product_type", "_distinguishing_features", "_is_product",
)
NINE = (
    "electronics", "grocery", "supplements", "makeup", "skincare", "haircare",
    "fragrances", "fashion", "other",
)
ENUMERATION_TEXT = ", ".join(NINE)
COUNT_KEYS = {
    "candidates", "kept", "dropped_not_product", "unpaired_index", "dropped_non_dict",
    "unknown_brand", "unknown_name", "images", "finish_reason",
}
SIX_KEYS = {"brand", "name", "variant", "category", "search_query", "_vision"}
VISION_FIELD_KEYS = {
    "_vision_confidence", "_vision_category", "_vision_distinguishing_features",
    "_vision_is_product", "_vision_image_index",
}
JPEG = b"\xff\xd8" + b"\x00" * 64

_NULLABLE_STR = {"type": ["string", "null"]}
EXPECTED_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "vision_products_v2",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["products"],
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "image_index", "brand", "name", "category", "product_type",
                            "size_or_count", "visible_price", "distinguishing_features",
                            "is_product", "confidence",
                        ],
                        "properties": {
                            "image_index": {"type": "integer"},
                            "brand": dict(_NULLABLE_STR),
                            "name": dict(_NULLABLE_STR),
                            "category": {
                                "anyOf": [
                                    {"type": "string", "enum": list(NINE)},
                                    {"type": "null"},
                                ]
                            },
                            "product_type": dict(_NULLABLE_STR),
                            "size_or_count": dict(_NULLABLE_STR),
                            "visible_price": dict(_NULLABLE_STR),
                            "distinguishing_features": {
                                "type": "array", "items": {"type": "string"},
                            },
                            "is_product": {"type": "boolean"},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        },
                    },
                }
            },
        },
    },
}


# ---------------------------------------------------------------------------
# fixtures + environment
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _unit_env(monkeypatch):
    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(limiter, "enabled", False)
    yield


def _full_config(monkeypatch, flag):
    """B1 rule: every row runs with BOTH unit knobs present; the flag is set to
    `flag` or deleted when `flag` is None."""
    monkeypatch.setenv(KNOB, "7.5")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)


@pytest.fixture
def client():
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {
        "id": ("b3-" + request.node.name)[:120],
        "email": "b3@example.test",
        "access_token": "b3-token",
    }
    fastapi_app.dependency_overrides[get_optional_user] = lambda: user
    try:
        yield user
    finally:
        fastapi_app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def anonymous():
    fastapi_app.dependency_overrides[get_optional_user] = lambda: None
    try:
        yield None
    finally:
        fastapi_app.dependency_overrides.pop(get_optional_user, None)


# ---------------------------------------------------------------------------
# the fake OpenAI client
# ---------------------------------------------------------------------------
def _usage():
    return types.SimpleNamespace(total_tokens=100, prompt_tokens=80, completion_tokens=20)


def _reply(content, finish_reason="stop", refusal=None, usage="simple", choices=True):
    message = types.SimpleNamespace(content=content, refusal=refusal)
    choice = types.SimpleNamespace(finish_reason=finish_reason, message=message, index=0)
    return types.SimpleNamespace(
        choices=[choice] if choices else [],
        usage=_usage() if usage == "simple" else None,
        model="gpt-4o-mini",
    )


class _Completions:
    def __init__(self, replies, delay=0.0):
        self._replies = list(replies)
        self.delay = delay
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        if self.delay:
            await asyncio.sleep(self.delay)
        return self._replies[min(len(self.calls) - 1, len(self._replies) - 1)]


class _FakeClient:
    def __init__(self, replies, delay=0.0):
        self.completions = _Completions(replies, delay)
        self.chat = types.SimpleNamespace(completions=self.completions)


def _install_fake(monkeypatch, replies, delay=0.0):
    fake = _FakeClient(replies if isinstance(replies, list) else [replies], delay)
    monkeypatch.setattr(osvc, "client", fake)
    return fake


def IMG(n):
    return [{"bytes": b"\xff\xd8" + bytes([i]) * 8, "mime_type": "image/jpeg"} for i in range(n)]


def _capture(factory):
    """Run the coroutine `factory()` builds; return (result, exception). Never
    raises, so a RED row asserts on the outcome with an AssertionError."""
    try:
        return asyncio.run(factory()), None
    except Exception as exc:  # noqa: BLE001
        return None, exc


def _identify(n_images):
    return _capture(lambda: osvc.identify_products(IMG(n_images)))


def _need(module, name):
    value = getattr(module, name, None)
    assert value is not None, f"{module.__name__}.{name} is missing"
    return value


def _norm(obj):
    """JSON round trip (tuples -> lists) with every `required` list sorted."""
    obj = json.loads(json.dumps(obj))

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "required" and isinstance(v, list):
                    node[k] = sorted(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(obj)
    return obj


def _msgs(caplog, prefix):
    return [r for r in caplog.records if r.getMessage().startswith(prefix)]


def _counts(caplog):
    recs = _msgs(caplog, "[VISION_V2] candidates=")
    assert len(recs) == 1, (
        f"exactly one [VISION_V2] counts line per call, got {[r.getMessage() for r in recs]}"
    )
    rec = recs[0]
    assert rec.levelno == logging.INFO, rec.levelname
    pairs = dict(re.findall(r"(\w+)=(\S+)", rec.getMessage()))
    assert set(pairs) == COUNT_KEYS, f"counts line keys {sorted(pairs)}"
    return pairs


def _item(idx, brand, name, *, category=None, product_type=None, size=None, price=None,
          feats=(), is_product=True, confidence="high"):
    return {
        "image_index": idx, "brand": brand, "name": name, "category": category,
        "product_type": product_type, "size_or_count": size, "visible_price": price,
        "distinguishing_features": list(feats), "is_product": is_product,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# reply fixtures (the tester scenarios V04 / V07 / V01 + the rule fixtures)
# ---------------------------------------------------------------------------
V04_OBJECT = json.dumps({"products": [
    _item(0, "Sefiki", "Limited Edition", category=None, product_type="wrist watch",
          feats=["gold case"], confidence="low"),
    _item(1, "Violin", "SHAHRAZAD L'INTENSE", category="other", product_type="violin",
          confidence="low"),
]})
V07_ARRAY = json.dumps([
    _item(0, "GUESS", "GUESS!", category="fashion", product_type="t-shirt",
          feats=["white logo tee"], confidence="medium"),
    _item(1, "GUESS", "GUESS!", category="fashion", product_type="shirt",
          feats=["denim shirt", "polyurethane label"], confidence="medium"),
])
V01_OBJECT = json.dumps({"products": [
    _item(0, "OSMIA", "Woody F", category="fragrances", product_type="perfume bottle",
          confidence="high"),
    _item(1, "AL IBDAA", "EAU DE PARFUM", category="fragrances",
          product_type="perfume bottle", size="100ml", confidence="high"),
]})
# R6: highest confidence wins, ties keep the earlier (idx 0: B, A, E; idx 1: C, F).
PICK_BEST = json.dumps({"products": [
    _item(0, "PB", "B", confidence="medium"),
    _item(0, "PB", "A", confidence="high"),
    _item(0, "PB", "E", confidence="medium"),
    _item(1, "PB", "C", confidence="low"),
    _item(1, "PB", "F", confidence="low"),
]})
# R6b (ruling 2): one image -> the best two (A high, B medium), not the first two (A, D).
ONE_IMAGE_THREE = json.dumps({"products": [
    _item(0, "OI", "A", confidence="high"),
    _item(0, "OI", "D", confidence="low"),
    _item(0, "OI", "B", confidence="medium"),
]})
NON_PRODUCT = json.dumps({"products": [
    _item(0, "Chair", "Wooden", product_type="chair", is_product=False, confidence="high"),
    _item(1, "P1", "N1", confidence="low"),
]})
# R8 (ruling 3): 7, -1 and a bool are not image indices of a two-image request
# -> kept unpaired, after the paired pick, in reply order.
BAD_INDEX = json.dumps([
    _item(7, "X7", "n7"),
    _item(-1, "XM", "nm"),
    _item(True, "XT", "nt"),
    _item(0, "V0", "n0"),
])
_r8c_missing = _item(0, "XN", "nn")
del _r8c_missing["image_index"]
BAD_INDEX_2 = json.dumps([_item("0", "XS", "ns"), _r8c_missing, _item(1, "V1", "n1")])
ONE_BASED = json.dumps({"products": [_item(1, "P1", "one"), _item(2, "P2", "two")]})
NON_DICT = json.dumps([_item(0, "V", "N"), "junk", 7, None])
COERCE = json.dumps({"products": [
    {"image_index": 0, "brand": " Dior ", "name": " Sauvage ", "category": "Fragrance",
     "product_type": "  perfume bottle ", "size_or_count": "  100 ml ", "visible_price": "",
     "distinguishing_features": "not a list", "is_product": True, "confidence": "HIGH "},
    {"image_index": 1, "brand": None, "name": None, "category": "", "product_type": "",
     "size_or_count": None, "visible_price": "  BHD 8.500 ",
     "distinguishing_features": [1, "ok", "", "  padded  ", "y" * 100],
     "is_product": True, "confidence": "certain"},
    {"image_index": 2, "brand": "B2", "name": "N2", "category": None, "product_type": None,
     "size_or_count": None, "visible_price": None,
     "distinguishing_features": ["f%d" % i for i in range(10)]},
]})

# The V2-shaped products the R1 reply normalises to (also the route stubs).
V2_A = {
    "brand": "Sefiki", "name": "Limited Edition", "size_or_count": None, "visible_price": None,
    "confidence": "low", "_image_index": 0, "_category": None, "_product_type": "wrist watch",
    "_distinguishing_features": ["gold case"], "_is_product": True,
}
V2_B = {
    "brand": "Violin", "name": "SHAHRAZAD L'INTENSE", "size_or_count": None,
    "visible_price": None, "confidence": "low", "_image_index": 1, "_category": "other",
    "_product_type": "violin", "_distinguishing_features": [], "_is_product": True,
}
V1_A = {"brand": "Sefiki", "name": "Limited Edition", "size_or_count": None,
        "visible_price": None, "confidence": "low"}
V1_B = {"brand": "Violin", "name": "SHAHRAZAD L'INTENSE", "size_or_count": None,
        "visible_price": None, "confidence": "low"}


def _public(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _v2_route_stub(i):
    return {"brand": f"B{i}", "name": f"N{i}", "size_or_count": None, "visible_price": None,
            "confidence": "high", "_image_index": i, "_category": "fashion",
            "_product_type": "shirt", "_distinguishing_features": [f"mark {i}"],
            "_is_product": True}


def _vision(n):
    return {"products": [{"brand": f"B{i}", "name": f"N{i}"} for i in range(n)], "cost": 0.003}


DELIVERED = {
    "success": True,
    "products": [{"brand": "A", "name": "one"}, {"brand": "B", "name": "two"}],
    "metadata": {"total_cost": 0.01},
}
TIMEOUT_RESULT = {"success": False, "code": "TIMEOUT",
                  "error": scs.TIMEOUT_FRIENDLY_MESSAGE, "elapsed_seconds": 30.0,
                  "total_cost": 0.0}


# ---------------------------------------------------------------------------
# camera route harness (the tests/test_retro_w2_1.py idiom, re-implemented)
# ---------------------------------------------------------------------------
def _done(value=None):
    async def _r():
        return value
    return _r()


class _Ledger:
    def __init__(self):
        self.consumes, self.refunds, self.lifetime = [], [], []
        self.history, self.log_success, self.labels = [], [], []

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)
        return _done({
            "allowed": True, "reason": None, "tier": "free", "consumed": True,
            "consumed_keys": {"daily": f"d:{user_id}", "monthly": f"m:{user_id}"},
            "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
        })

    def refund(self, user_id, consumed_keys=None, *_a, **_kw):
        self.refunds.append(user_id)
        return _done()

    def anon_check(self, fp, *_a, **_kw):
        return _done({"allowed": True, "reason": None, "tier": "free", "consumed": False,
                      "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 0}})

    def anon_refund(self, fp, consumed_keys=None, *_a, **_kw):
        return _done()

    def record_lifetime(self, user_id, access_token="", *_a, **_kw):
        self.lifetime.append(user_id)
        return _done()

    def save(self, **kw):
        self.history.append(kw.get("input_type"))
        return _done()

    def log_search(self, **kw):
        self.log_success.append(kw.get("success"))
        return _done()


class _Safety:
    async def moderate_vision_output(self, _extracted):
        return content_safety_service.SafetyResult(allowed=True)


class _Spy:
    """Records every compare_from_text call (args, deep-copied kwargs)."""

    def __init__(self, result=None, raises=False):
        self.calls = []
        self._result = DELIVERED if result is None else result
        self._raises = raises
        spy = self

        class _Service:
            async def compare_from_text(self, *a, **kw):
                spy.calls.append((a, copy.deepcopy(kw)))
                if spy._raises:
                    raise RuntimeError("b3 probe: comparison unavailable")
                return copy.deepcopy(spy._result)

        self.service_class = _Service


class _Prefs:
    def __init__(self, result=None, raises=False):
        self.calls = []
        self._result = {"success": False} if result is None else result
        self._raises = raises

    async def __call__(self, user_id, *_a, **_kw):
        self.calls.append(user_id)
        if self._raises:
            raise RuntimeError("b3 probe: preferences read down")
        return copy.deepcopy(self._result)


def _stub_route(monkeypatch, *, vision=None, spy=None, prefs=None):
    """Stub every collaborator of POST /image/identify. vision=None keeps the
    REAL identify_products (driven by the fake OpenAI client); a dict stubs it."""
    ledger = _Ledger()
    if vision is not None:
        async def _identify(_images):
            return copy.deepcopy(vision)
        monkeypatch.setattr(image_routes, "identify_products", _identify)
    monkeypatch.setattr(content_safety_service, "get_content_safety_service",
                        lambda: _Safety())
    from app.services import audit_service
    monkeypatch.setattr(audit_service, "log_content_blocked", lambda **_kw: _done())
    spy = spy or _Spy()
    monkeypatch.setattr(image_routes, "StructuredComparisonService", spy.service_class)
    prefs = prefs or _Prefs()
    monkeypatch.setattr(image_routes, "get_user_preferences", prefs, raising=False)
    monkeypatch.setattr(image_routes, "log_search", ledger.log_search)
    for mod in (usage_service, image_routes):
        monkeypatch.setattr(mod, "consume_comparison_credit", ledger.consume, raising=False)
        monkeypatch.setattr(mod, "refund_comparison_credit", ledger.refund, raising=False)
        monkeypatch.setattr(mod, "check_anon_usage_allowed", ledger.anon_check, raising=False)
        monkeypatch.setattr(mod, "refund_anon_comparison_credit", ledger.anon_refund,
                            raising=False)
        monkeypatch.setattr(mod, "record_lifetime_comparison", ledger.record_lifetime,
                            raising=False)
    for mod in (feedback_service, image_routes):
        monkeypatch.setattr(mod, "save_comparison_and_track_cohort", ledger.save,
                            raising=False)
    real_ff = image_routes.fire_and_forget

    def _ff(coro, label):
        ledger.labels.append(label)
        return real_ff(coro, label=label)

    monkeypatch.setattr(image_routes, "fire_and_forget", _ff)
    return ledger, spy, prefs


def _post_identify(client, n_images=2):
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(n_images)]
    return client.post("/api/v1/image/identify", files=files)


def _no_underscore_keys(dicts):
    return all(isinstance(d, dict) and not any(str(k).startswith("_") for k in d)
               for d in dicts)


# ===========================================================================
# PIN rows: flag OFF identity of identify_products (P1, P2, P3, P3b, P10)
# ===========================================================================
OFF_VALUES = [None, "", "false", "0", "no", "off", "garbage"]


def _raising_knob():
    raise AssertionError("VISION_TIMEOUT_SECONDS must not be read with the flag OFF")


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_P1_flag_off_prompt_and_layout_byte_identical(monkeypatch, flag):
    """PIN: flag OFF (every falsy spelling) sends the base prompt (sha pinned),
    one user message, the text block then one image_url part per image with
    detail auto; the knob reader is never called."""
    _full_config(monkeypatch, flag)
    knob_calls = []

    def _knob():
        knob_calls.append(1)
        _raising_knob()

    monkeypatch.setattr(osvc, "vision_timeout_seconds", _knob, raising=False)
    fake = _install_fake(monkeypatch, _reply("[]"))

    result, exc = _identify(2)

    assert exc is None, repr(exc)
    assert knob_calls == []
    assert len(fake.completions.calls) == 1
    call = fake.completions.calls[0]
    msgs = call["messages"]
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    assert [part["type"] for part in content] == ["text", "image_url", "image_url"]
    text = content[0]["text"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == VISION_PROMPT_SHA_OFF
    for part in content[1:]:
        assert part["image_url"]["detail"] == "auto"
        assert part["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_P2_flag_off_kwargs_and_result_byte_identical(monkeypatch, flag):
    """PIN: flag OFF kwargs are exactly {model, messages, max_tokens 500,
    temperature 0, store False} (no response_format), no asyncio.wait_for wraps
    the dispatch, and the V1 result shape is returned."""
    _full_config(monkeypatch, flag)
    monkeypatch.setattr(osvc, "vision_timeout_seconds", _raising_knob, raising=False)
    real_wait_for = asyncio.wait_for
    wrapped = []

    async def _wait_for(aw, *a, **k):
        wrapped.append(getattr(getattr(aw, "cr_code", None), "co_name", type(aw).__name__))
        return await real_wait_for(aw, *a, **k)

    monkeypatch.setattr(asyncio, "wait_for", _wait_for)
    fake = _install_fake(monkeypatch, _reply("[]"))

    result, exc = _identify(2)

    assert exc is None, repr(exc)
    call = fake.completions.calls[0]
    assert set(call) == VISION_KWARGS_OFF
    assert call["model"] == "gpt-4o-mini"
    assert call["max_tokens"] == 500
    assert call["temperature"] == 0
    assert call["store"] is False
    assert "response_format" not in call
    assert "guarded_llm_create" not in wrapped, wrapped
    assert result == {"products": [], "tokens_used": 100, "cost": 2.4e-05}


def test_P3_flag_off_v1_normaliser_unchanged(monkeypatch, caplog):
    """PIN: flag OFF an object reply is dropped (base :215) and a bare array
    keeps exactly the five V1 keys with the V1 defaults; no [VISION_V2] line."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "false")
    _install_fake(monkeypatch, _reply(V04_OBJECT))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    assert result["products"] == []

    array = json.dumps([
        _item(0, "Sefiki", "Limited Edition", category="fashion", confidence="low"),
        {"name": "Something"},
    ])
    _install_fake(monkeypatch, _reply(array))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert len(products) == 2
    for p in products:
        assert list(p) == list(PUBLIC_KEYS)
    assert products[1] == {"brand": "Unknown", "name": "Something", "size_or_count": None,
                           "visible_price": None, "confidence": "medium"}
    assert _msgs(caplog, "[VISION_V2]") == []


def test_P3b_flag_off_non_dict_item_still_raises(monkeypatch):
    """PIN: the V1 normaliser is not repaired OFF (R-A1): a non-dict list item
    still raises AttributeError at base :217."""
    _full_config(monkeypatch, None)
    _install_fake(monkeypatch, _reply(NON_DICT))
    result, exc = _identify(1)
    assert isinstance(exc, AttributeError), repr(exc)


def test_P10_flag_off_usage_none_still_raises(monkeypatch):
    """PIN (P10 OFF half): a reply without usage still raises AttributeError
    OFF (base :227), the base behaviour kept."""
    _full_config(monkeypatch, "false")
    _install_fake(monkeypatch, _reply("[]", usage=None))
    result, exc = _identify(2)
    assert isinstance(exc, AttributeError), repr(exc)


# ===========================================================================
# RED rows: the V2 service path
# ===========================================================================
def test_R1_v04_object_normalised_to_public_plus_internal_keys(monkeypatch, caplog):
    """RED: the object reply becomes two products carrying the five public keys
    (V1 order) then the five internal keys. Base: the object is dropped."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(V04_OBJECT))
    pub = _need(osvc, "VISION_V2_PUBLIC_KEYS")
    internal = _need(osvc, "VISION_V2_INTERNAL_KEYS")
    assert tuple(pub) == PUBLIC_KEYS
    assert tuple(internal) == INTERNAL_KEYS

    result, exc = _identify(2)

    assert exc is None, repr(exc)
    products = result["products"]
    assert len(products) == 2, products
    assert list(products[0]) == list(PUBLIC_KEYS) + list(INTERNAL_KEYS)
    assert products[0] == V2_A
    assert products[1] == V2_B
    assert result.get("tokens_used") == 100
    assert result.get("cost") == 2.4e-05
    assert set(result) == {"products", "tokens_used", "cost"}
    c = _counts(caplog)
    assert (c["candidates"], c["kept"], c["unpaired_index"], c["images"]) == ("2", "2", "0", "2")
    assert (c["unknown_brand"], c["unknown_name"], c["finish_reason"]) == ("0", "0", "stop")


def test_R2_v07_bare_array_accepted(monkeypatch):
    """RED: a bare array reply is accepted; distinguishing features and the
    category ride the internal keys. Base: five V1 keys only."""
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(V07_ARRAY))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert len(products) == 2
    assert [p.get("_image_index") for p in products] == [0, 1]
    assert [p.get("_distinguishing_features") for p in products] == [
        ["white logo tee"], ["denim shirt", "polyurethane label"]]
    assert [p.get("_category") for p in products] == ["fashion", "fashion"]
    assert [p.get("_product_type") for p in products] == ["t-shirt", "shirt"]
    assert [_public(p) for p in products] == [
        {"brand": "GUESS", "name": "GUESS!", "size_or_count": None, "visible_price": None,
         "confidence": "medium"}] * 2


def test_R3_v2_call_shape(monkeypatch):
    """RED: flag ON sends VISION_PROMPT_V2 with response_format = the strict
    json_schema (category anyOf, ruling 4), max_tokens 1000 (ruling 7),
    temperature 0, store False, through the chokepoint; same message layout."""
    _full_config(monkeypatch, "true")
    fake = _install_fake(monkeypatch, _reply("[]"))
    max_tokens = getattr(osvc, "_VISION_V2_MAX_TOKENS", None)
    assert max_tokens == 1000

    result, exc = _identify(2)

    assert exc is None, repr(exc)
    assert len(fake.completions.calls) == 1
    call = fake.completions.calls[0]
    assert set(call) == VISION_KWARGS_OFF | {"response_format"}, sorted(call)
    assert _norm(call.get("response_format")) == _norm(EXPECTED_RESPONSE_FORMAT)
    assert call["response_format"]["json_schema"]["strict"] is True
    assert call["model"] == "gpt-4o-mini"
    assert call["max_tokens"] == 1000
    assert call["temperature"] == 0
    assert call["store"] is False
    content = call["messages"][0]["content"]
    assert len(call["messages"]) == 1 and call["messages"][0]["role"] == "user"
    assert [part["type"] for part in content] == ["text", "image_url", "image_url"]
    text = content[0]["text"]
    assert text == _need(osvc, "VISION_PROMPT_V2")
    assert text.isascii()
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() != VISION_PROMPT_SHA_OFF
    for needle in ("image_index", ENUMERATION_TEXT, "Arabic script", "is_product",
                   "distinguishing_features", "product_type"):
        assert needle in text, needle
    assert "WITHOUT packaging" not in text
    assert "JSON array" not in text


@pytest.mark.parametrize("variant", ["refusal", "none", "no_choice"])
def test_R4_no_content_raises_llm_unavailable(monkeypatch, caplog, variant):
    """RED: a refusal / None content / no choice raises LLMUnavailableError whose
    message avoids 429 / rate / quota, with one WARNING naming refused=<bool>
    and never the refusal text. Base: AttributeError / IndexError."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    reply = {
        "refusal": _reply(None, refusal="I cannot help with that"),
        "none": _reply(None),
        "no_choice": _reply("[]", choices=False),
    }[variant]
    _install_fake(monkeypatch, reply)

    result, exc = _identify(1)

    assert isinstance(exc, api_budget_service.LLMUnavailableError), repr(exc)
    text = str(exc).lower()
    for word in ("429", "rate", "quota"):
        assert word not in text, text
    recs = _msgs(caplog, "[VISION_V2] no content")
    assert len(recs) == 1, [r.getMessage() for r in caplog.records]
    assert recs[0].levelno == logging.WARNING
    expected = "refused=True" if variant == "refusal" else "refused=False"
    assert expected in recs[0].getMessage()
    assert all("I cannot help" not in r.getMessage() for r in caplog.records)


def test_R4b_route_refusal_is_coded_503_with_refund(monkeypatch, client, authed):
    """RED: through the route a refused vision reply ships the coded 503
    LLM_UNAVAILABLE (exit 1), refunds the reserved credit, never compares.
    Base: 500."""
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(METER, "true")
    ledger, spy, _prefs = _stub_route(monkeypatch)
    _install_fake(monkeypatch, _reply(None, refusal="x"))

    resp = _post_identify(client)

    assert resp.status_code == 503, resp.text[:300]
    body = resp.json()
    assert body.get("code") == "LLM_UNAVAILABLE"
    assert body.get("error") == LLM_UNAVAILABLE_FRIENDLY_MESSAGE
    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == ledger.consumes
    assert spy.calls == []


def test_R5_finish_reason_length_is_a_logged_parse_failure(monkeypatch, caplog):
    """RED: finish_reason length -> the V1-shaped parse-failure dict naming
    finish_reason=length, plus one WARNING. Base: a JSON error text, no line."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply('[{"brand"', finish_reason="length"))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    assert result.get("products") == []
    assert "finish_reason=length" in (result.get("error") or "")
    assert result.get("raw_response") == '[{"brand"'
    assert result.get("tokens_used") == 100
    assert result.get("cost") == 0
    recs = _msgs(caplog, "[VISION_V2] finish_reason=length")
    assert len(recs) == 1 and recs[0].levelno == logging.WARNING


def test_R5b_route_length_reply_is_exit_2(monkeypatch, client, authed, caplog):
    """RED: through the route a length reply is exit 2 (action error, refund,
    no compare) and the WARNING is logged. Base: same body, no WARNING."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(METER, "true")
    ledger, spy, _prefs = _stub_route(monkeypatch)
    _install_fake(monkeypatch, _reply('[{"brand"', finish_reason="length"))

    resp = _post_identify(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("action") == "error"
    assert body.get("error") == "Could not identify products in the image. Please try a clearer photo."
    assert body.get("vision_cost") == 0
    assert ledger.refunds == ledger.consumes == [authed["id"]]
    assert spy.calls == []
    assert len(_msgs(caplog, "[VISION_V2] finish_reason=length")) == 1


def test_R6_one_best_candidate_per_image_index(monkeypatch, caplog):
    """RED: two images -> one product per image_index: highest confidence, ties
    keep the earlier, ascending index. Base: five products."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(PICK_BEST))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert [p["name"] for p in products] == ["A", "C"]
    assert [p.get("_image_index") for p in products] == [0, 1]
    c = _counts(caplog)
    assert (c["candidates"], c["kept"], c["dropped_not_product"], c["unpaired_index"]) == (
        "5", "2", "0", "0")


def test_R6b_one_image_keeps_the_best_two(monkeypatch, caplog):
    """RED (ruling 2): a one-image request keeps the best TWO candidates of
    image_index 0 in rank order (A high, B medium), not the first two (A, D).
    Base: three products in reply order."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(ONE_IMAGE_THREE))
    result, exc = _identify(1)
    assert exc is None, repr(exc)
    products = result["products"]
    assert [p["name"] for p in products] == ["A", "B"]
    assert [p.get("_image_index") for p in products] == [0, 0]
    c = _counts(caplog)
    assert (c["candidates"], c["kept"], c["unpaired_index"], c["images"]) == ("3", "2", "0", "1")


def test_R7_is_product_false_candidates_dropped(monkeypatch, caplog):
    """RED (ruling 6): a non-product candidate is dropped even at higher
    confidence and counted. Base: two products."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(NON_PRODUCT))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert len(products) == 1
    assert products[0].get("_image_index") == 1
    assert products[0]["name"] == "N1"
    assert _counts(caplog)["dropped_not_product"] == "1"


def test_R7b_route_non_product_photo_is_need_second_product(monkeypatch, client, authed):
    """RED: through the route the dropped non-product leaves one product ->
    need_second_product with public keys only. Base: a comparison."""
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(METER, "true")
    ledger, spy, _prefs = _stub_route(monkeypatch)
    _install_fake(monkeypatch, _reply(NON_PRODUCT))

    resp = _post_identify(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("action") == "need_second_product", body.get("action")
    assert len(body.get("products") or []) == 1
    assert list(body["products"][0]) == list(PUBLIC_KEYS)
    assert body["products"][0]["name"] == "N1"
    assert body.get("message", "").startswith("Identified: ")
    assert ledger.refunds == ledger.consumes == [authed["id"]]
    assert spy.calls == []


def test_R8_out_of_range_index_kept_unpaired_after_paired(monkeypatch, caplog):
    """RED (ruling 3): indices 7, -1 and a bool do not name an image of a
    two-image request -> kept unpaired (_image_index None), appended after the
    paired pick in reply order, counted unpaired_index. Base: no _image_index."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(BAD_INDEX))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert [p["brand"] for p in products] == ["V0", "X7", "XM", "XT"]
    assert [p.get("_image_index", "missing") for p in products] == [0, None, None, None]
    c = _counts(caplog)
    assert (c["kept"], c["unpaired_index"]) == ("4", "3")


def test_R8c_str_and_missing_index_kept_unpaired(monkeypatch, caplog):
    """RED (ruling 3): a str index and a missing index are unpaired too."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(BAD_INDEX_2))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert [p["brand"] for p in products] == ["V1", "XS", "XN"]
    assert [p.get("_image_index", "missing") for p in products] == [1, None, None]
    assert _counts(caplog)["unpaired_index"] == "2"


def test_R8d_one_based_reply_degrades_to_v1_pairing(monkeypatch, caplog):
    """RED (review K2 / ruling 3): a reply numbering from 1 on a two-image
    request keeps BOTH products (index 1 paired, index 2 unpaired), so the scan
    still compares instead of ending in need_second_product."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(ONE_BASED))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    products = result["products"]
    assert [p["brand"] for p in products] == ["P1", "P2"]
    assert [p.get("_image_index", "missing") for p in products] == [1, None]
    assert _counts(caplog)["unpaired_index"] == "1"


def test_R8b_non_dict_items_dropped_and_counted(monkeypatch, caplog):
    """RED (review C7 / B3-R5): non-dict list items are dropped and counted,
    never raised on. Base: AttributeError at :217."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(NON_DICT))
    result, exc = _identify(1)
    assert exc is None, repr(exc)
    assert [p["brand"] for p in result["products"]] == ["V"]
    c = _counts(caplog)
    assert (c["kept"], c["dropped_non_dict"]) == ("1", "3")


def test_R9_coercion_and_string_hygiene(monkeypatch, caplog):
    """RED (ruling B3-R2 + review C8): three items at image_index 0/1/2 with
    IMG(3); confidence 'HIGH ' -> high, 'certain' -> low, missing -> low;
    category canonicalised, '' / null -> None; strings stripped, '' -> None,
    brand / name defaults; features: non-list -> [], non-str and empty dropped,
    stripped, cut at 80, at most 8; is_product missing -> True; the unknown
    counters. Base: raw values pass through."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply(COERCE))
    result, exc = _identify(3)
    assert exc is None, repr(exc)
    p = result["products"]
    assert len(p) == 3
    assert [x.get("confidence") for x in p] == ["high", "low", "low"]
    assert [x.get("_category", "missing") for x in p] == ["fragrances", None, None]
    assert [x.get("_is_product", "missing") for x in p] == [True, True, True]
    assert [x.get("_image_index", "missing") for x in p] == [0, 1, 2]
    assert (p[0].get("brand"), p[0].get("name")) == ("Dior", "Sauvage")
    assert (p[1].get("brand"), p[1].get("name")) == ("Unknown", "Unknown Product")
    assert p[0].get("_product_type", "missing") == "perfume bottle"
    assert p[1].get("_product_type", "missing") is None
    assert p[0].get("size_or_count", "missing") == "100 ml"
    assert p[0].get("visible_price", "missing") is None
    assert p[1].get("visible_price", "missing") == "BHD 8.500"
    assert p[0].get("_distinguishing_features") == []
    assert p[1].get("_distinguishing_features") == ["ok", "padded", "y" * 80]
    assert p[2].get("_distinguishing_features") == ["f%d" % i for i in range(8)]
    c = _counts(caplog)
    assert (c["kept"], c["images"], c["unknown_brand"], c["unknown_name"]) == ("3", "3", "1", "1")


def test_R10_vision_call_bounded_by_the_knob(monkeypatch, caplog):
    """RED: the V2 dispatch runs under asyncio.wait_for(VISION_TIMEOUT_SECONDS):
    a 2 s reply with the knob at 0.05 raises TimeoutError well inside 1.5 s, the
    knob is read once, one WARNING names the bound. Base: no bound."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(KNOB, "0.05")
    real = getattr(osvc, "vision_timeout_seconds", None)
    seen = []

    def _rec():
        seen.append(1)
        return real() if callable(real) else 0.05

    monkeypatch.setattr(osvc, "vision_timeout_seconds", _rec, raising=False)
    _install_fake(monkeypatch, _reply("[]"), delay=2.0)

    t0 = time.monotonic()
    result, exc = _identify(2)
    wall = time.monotonic() - t0

    assert isinstance(exc, TimeoutError), repr(exc)
    assert wall < 1.5, wall
    assert seen == [1]
    recs = _msgs(caplog, "[VISION_V2] vision call timed out after 0.1s")
    assert len(recs) == 1 and recs[0].levelno == logging.WARNING


def test_R10b_route_timeout_is_coded_503(monkeypatch, client, authed):
    """RED: through the route a vision expiry ships the coded 503
    LLM_UNAVAILABLE (ruling Q1: never TIMEOUT), refunds, never compares."""
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(KNOB, "0.05")
    monkeypatch.setenv(METER, "true")
    ledger, spy, _prefs = _stub_route(monkeypatch)
    _install_fake(monkeypatch, _reply("[]"), delay=2.0)

    resp = _post_identify(client)

    assert resp.status_code == 503, resp.status_code
    assert resp.json().get("code") == "LLM_UNAVAILABLE"
    assert ledger.refunds == ledger.consumes == [authed["id"]]
    assert spy.calls == []


KNOB_ROWS = [
    (None, 20.0, False), ("", 20.0, False), ("   ", 20.0, False),
    ("garbage", 20.0, True), ("inf", 20.0, True), ("nan", 20.0, True),
    ("0", 20.0, True), ("-3", 20.0, True), ("1e400", 20.0, True),
    (" 12.5 ", 12.5, False), ("20", 20.0, False),
]


@pytest.mark.parametrize("raw,expected,warns", KNOB_ROWS,
                         ids=[repr(r[0]) for r in KNOB_ROWS])
def test_R11_timeout_knob_parse(monkeypatch, caplog, raw, expected, warns):
    """RED: vision_timeout_seconds() -- unset / blank / garbage / inf / nan /
    <= 0 fall back to 20.0; garbage and non-positive / non-finite values log
    one WARNING naming the variable."""
    caplog.set_level(logging.INFO)
    fn = getattr(osvc, "vision_timeout_seconds", None)
    assert callable(fn), "openai_service.vision_timeout_seconds is missing"
    if raw is None:
        monkeypatch.delenv(KNOB, raising=False)
    else:
        monkeypatch.setenv(KNOB, raw)
    value = fn()
    assert isinstance(value, float)
    assert value == expected
    named = [r for r in caplog.records
             if r.levelno == logging.WARNING and KNOB in r.getMessage()]
    assert len(named) == (1 if warns else 0), [r.getMessage() for r in named]


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("TRUE", True), (" true ", True), ("1", True), ("yes", True),
    ("ON", True), ("on", True),
    (None, False), ("", False), ("false", False), ("0", False), ("no", False),
    ("off", False), ("garbage", False), ("tru e", False),
])
def test_R12_flag_reader(monkeypatch, value, expected):
    """RED: the house idiom, .strip().lower() in (true, 1, yes, on), per call."""
    fn = getattr(osvc, "vision_identity_v2_enabled", None)
    assert callable(fn), "openai_service.vision_identity_v2_enabled is missing"
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert fn() is expected


_R13_ROWS = [
    ("v2", V2_A, {"_vision_confidence": "low", "_vision_category": None,
                  "_vision_distinguishing_features": ["gold case"],
                  "_vision_is_product": True, "_vision_image_index": 0}),
    ("v2_unpaired_none_feats",
     {"brand": "b", "name": "n", "confidence": "high", "_category": "fashion",
      "_image_index": None, "_distinguishing_features": None, "_is_product": True},
     {"_vision_confidence": "high", "_vision_category": "fashion",
      "_vision_distinguishing_features": [], "_vision_is_product": True,
      "_vision_image_index": None}),
    ("v1", V1_A, {}),
    ("str", "not a dict", {}),
    ("none", None, {}),
]


@pytest.mark.parametrize("vp,expected", [(r[1], r[2]) for r in _R13_ROWS],
                         ids=[r[0] for r in _R13_ROWS])
def test_R13_vision_identity_fields(vp, expected):
    """RED: _vision_identity_fields -- presence-gated on _is_product; the five
    _vision_* keys (ruling 11 adds _vision_image_index); a NEW features list."""
    fn = getattr(scs, "_vision_identity_fields", None)
    assert callable(fn), "structured_comparison_service._vision_identity_fields is missing"
    out = fn(copy.deepcopy(vp) if isinstance(vp, dict) else vp)
    assert out == expected
    if isinstance(vp, dict) and isinstance(vp.get("_distinguishing_features"), list):
        src = vp["_distinguishing_features"]
        out2 = fn(vp)
        assert out2["_vision_distinguishing_features"] is not src


def _run_orchestrator(monkeypatch, vision_products):
    seen = []
    svc = scs.StructuredComparisonService()
    monkeypatch.setattr(scs, "classify_category_llm", AsyncMock(return_value="other"))

    async def _rec(product_info, *_a, **_k):
        seen.append(dict(product_info))
        raise RuntimeError("b3 stop")

    monkeypatch.setattr(svc, "_fetch_product_data", _rec)
    result = asyncio.run(svc.compare_from_text(
        "Sefiki Limited Edition vs Violin SHAHRAZAD L'INTENSE",
        vision_products=copy.deepcopy(vision_products),
    ))
    return result, seen


def test_R14_rest_twin_carries_vision_fields(monkeypatch):
    """RED: the REST twin's identity dicts carry the five _vision_* fields when
    the vision products are V2-shaped; the base six keys keep their values."""
    _full_config(monkeypatch, "true")
    result, seen = _run_orchestrator(monkeypatch, [V2_A, V2_B])
    assert result.get("success") is False
    assert len(seen) == 2, seen
    assert set(seen[0]) == SIX_KEYS | VISION_FIELD_KEYS, sorted(seen[0])
    assert set(seen[1]) == SIX_KEYS | VISION_FIELD_KEYS, sorted(seen[1])
    assert seen[0]["search_query"] == "Sefiki Limited Edition"
    assert seen[0]["_vision"] is True
    assert seen[0].get("_vision_confidence") == "low"
    assert seen[0].get("_vision_category", "missing") is None
    assert seen[1].get("_vision_category") == "other"
    assert seen[0].get("_vision_is_product") is True
    assert seen[0].get("_vision_distinguishing_features") == ["gold case"]
    assert [s.get("_vision_image_index") for s in seen] == [0, 1]


@pytest.mark.parametrize("flag", ["true", None, "false"])
def test_P4_P5_v1_vision_products_keep_six_keys(monkeypatch, flag):
    """PIN (P4 flag ON / P5 flag OFF): V1-shaped vision products (no _is_product)
    keep the base six identity keys exactly (presence gating)."""
    _full_config(monkeypatch, flag)
    result, seen = _run_orchestrator(monkeypatch, [V1_A, V1_B])
    assert result.get("success") is False
    assert len(seen) == 2, seen
    for s in seen:
        assert set(s) == SIX_KEYS, sorted(s)
        assert s["_vision"] is True
    assert seen[0]["search_query"] == "Sefiki Limited Edition"
    assert seen[1]["variant"] is None


def test_R15_both_twins_splat_the_vision_fields():
    """RED: source pin -- the REST and the stream twin each splat
    _vision_identity_fields(vp) on their '"_vision": True' line (lockstep)."""
    src = Path(scs.__file__).read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if "**_vision_identity_fields(vp)" in ln]
    assert len(lines) == 2, lines
    assert all('"_vision": True' in ln for ln in lines), lines


# ===========================================================================
# the camera route: forwarding (R16*, P6) and wire hygiene (R17, P7)
# ===========================================================================
PREFS_DONE = {"success": True, "preferences_completed": True,
              "preferences": {"budget": "mid", "priorities": ["value"]}}


def test_R16_route_forwards_user_id_and_completed_preferences(monkeypatch, client, authed):
    """RED: flag ON + signed in -> compare_from_text gets user_id and, with
    preferences_completed, user_preferences as kwargs. Base: neither."""
    _full_config(monkeypatch, "true")
    prefs = _Prefs(PREFS_DONE)
    ledger, spy, _ = _stub_route(monkeypatch, vision=_vision(2), prefs=prefs)

    resp = _post_identify(client)

    assert resp.status_code == 200
    assert resp.json().get("action") == "comparison"
    assert len(spy.calls) == 1
    args, kwargs = spy.calls[0]
    assert args == ("B0 N0 vs B1 N1",)
    assert kwargs == {
        "region": "bahrain", "vision_products": _vision(2)["products"], "nocache": False,
        "user_id": authed["id"], "user_preferences": {"budget": "mid", "priorities": ["value"]},
    }
    assert prefs.calls == [authed["id"]]


@pytest.mark.parametrize("case", ["not_completed", "not_success", "raises"])
def test_R16b_route_preferences_conditional_and_fail_soft(
        monkeypatch, client, authed, caplog, case):
    """RED: user_id is forwarded; user_preferences only when completed; a raising
    read logs one WARNING (type name only) and the scan still compares."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    prefs = {
        "not_completed": _Prefs({"success": True, "preferences_completed": False,
                                 "preferences": {"budget": "mid"}}),
        "not_success": _Prefs({"success": False}),
        "raises": _Prefs(raises=True),
    }[case]
    ledger, spy, _ = _stub_route(monkeypatch, vision=_vision(2), prefs=prefs)

    resp = _post_identify(client)

    assert resp.status_code == 200
    assert len(spy.calls) == 1
    _args, kwargs = spy.calls[0]
    assert kwargs.get("user_id") == authed["id"], kwargs
    assert "user_preferences" not in kwargs, kwargs
    assert prefs.calls == [authed["id"]]
    warn = _msgs(caplog, "[IMAGE] preferences read failed")
    if case == "raises":
        assert [r.getMessage() for r in warn] == ["[IMAGE] preferences read failed: RuntimeError"]
        assert warn[0].levelno == logging.WARNING
    else:
        assert warn == []
    assert all("b3 probe" not in r.getMessage() for r in caplog.records)


def test_R16c_anonymous_scan_forwards_nothing(monkeypatch, client, anonymous):
    """PIN (R16c, flag ON): no user -> the base three kwargs, no preferences read."""
    _full_config(monkeypatch, "true")
    prefs = _Prefs(PREFS_DONE)
    ledger, spy, _ = _stub_route(monkeypatch, vision=_vision(2), prefs=prefs)
    resp = _post_identify(client)
    assert resp.status_code == 200
    assert len(spy.calls) == 1
    args, kwargs = spy.calls[0]
    assert args == ("B0 N0 vs B1 N1",)
    assert kwargs == {"region": "bahrain", "vision_products": _vision(2)["products"],
                      "nocache": False}
    assert prefs.calls == []


@pytest.mark.parametrize("flag", [None, "false"])
def test_P6_flag_off_route_call_and_body_identical(monkeypatch, client, authed, flag):
    """PIN: flag OFF with the full configuration (knob + model set, metering and
    envelope ON, a signed-in user whose preferences are completed): the base
    three-kwarg call, no preferences read, the W2-1 delivery body."""
    _full_config(monkeypatch, flag)
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    prefs = _Prefs(PREFS_DONE)
    ledger, spy, _ = _stub_route(monkeypatch, vision=_vision(2), prefs=prefs)

    resp = _post_identify(client)

    assert resp.status_code == 200
    assert len(spy.calls) == 1
    args, kwargs = spy.calls[0]
    assert args == ("B0 N0 vs B1 N1",)
    assert kwargs == {"region": "bahrain", "vision_products": _vision(2)["products"],
                      "nocache": False}
    assert prefs.calls == []
    assert resp.json() == {
        "success": True,
        "products": [{"brand": "A", "name": "one"}, {"brand": "B", "name": "two"}],
        "metadata": {
            "total_cost": round(0.01 + 0.003, 6),
            "input_method": "camera",
            "vision_cost": 0.003,
            "identified_products": _vision(2)["products"],
        },
        "action": "comparison",
    }
    assert ledger.lifetime == [authed["id"]] and ledger.refunds == []


V2_STUB_2 = {"products": [_v2_route_stub(0), _v2_route_stub(1)], "cost": 0.003}
V2_STUB_1 = {"products": [_v2_route_stub(0)], "cost": 0.003}


@pytest.mark.parametrize("arm", ["a_on_delivery", "b_off_delivery", "c_need_second",
                                 "d_comparison_failed", "e_envelope",
                                 "f_envelope_meter_off"])
def test_R17_wire_bodies_carry_no_internal_keys(monkeypatch, client, authed, arm):
    """RED: every wire body (metadata.identified_products, need_second_product
    products, comparison_failed products, the failure envelope at BOTH of its
    call sites -- metering ON, and metering OFF with the envelope ON) carries
    the public keys only, while compare_from_text receives the un-stripped
    dicts. Arm b runs flag OFF: the strip is unconditional (ruling 9)."""
    _full_config(monkeypatch, "false" if arm == "b_off_delivery" else "true")
    vision = V2_STUB_1 if arm == "c_need_second" else V2_STUB_2
    spy = None
    if arm == "d_comparison_failed":
        spy = _Spy(raises=True)
    if arm == "e_envelope":
        monkeypatch.setenv(METER, "true")
        monkeypatch.setenv(ENVELOPE, "true")
        spy = _Spy(result=TIMEOUT_RESULT)
    if arm == "f_envelope_meter_off":
        monkeypatch.setenv(ENVELOPE, "true")
        spy = _Spy(result=TIMEOUT_RESULT)
    ledger, spy, _ = _stub_route(monkeypatch, vision=vision, spy=spy)

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    expected = [_public(p) for p in vision["products"]]
    if arm in ("a_on_delivery", "b_off_delivery"):
        assert body.get("action") == "comparison"
        shipped = body["metadata"]["identified_products"]
    else:
        assert body.get("action") == {
            "c_need_second": "need_second_product",
            "d_comparison_failed": "comparison_failed",
            "e_envelope": "comparison_failed",
            "f_envelope_meter_off": "comparison_failed",
        }[arm]
        shipped = body["products"]
    assert _no_underscore_keys(shipped), shipped
    assert shipped == expected
    assert '"_' not in resp.text
    if arm != "c_need_second":
        assert len(spy.calls) == 1
        sent = spy.calls[0][1]["vision_products"]
        assert sent[0].get("_category") == "fashion" and sent[0].get("_is_product") is True


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("shape", ["delivery", "need_second", "failed"])
def test_P7_v1_bodies_unchanged(monkeypatch, client, authed, flag, shape):
    """PIN: with V1-shaped products the bodies equal the base literals in both
    flag states (the copy of a V1 list is an equal list)."""
    _full_config(monkeypatch, flag)
    vision = _vision(1) if shape == "need_second" else _vision(2)
    spy = _Spy(raises=True) if shape == "failed" else None
    ledger, spy, _ = _stub_route(monkeypatch, vision=vision, spy=spy)

    resp = _post_identify(client)

    assert resp.status_code == 200
    body = resp.json()
    if shape == "delivery":
        assert body == {
            "success": True,
            "products": [{"brand": "A", "name": "one"}, {"brand": "B", "name": "two"}],
            "metadata": {"total_cost": round(0.01 + 0.003, 6), "input_method": "camera",
                         "vision_cost": 0.003,
                         "identified_products": _vision(2)["products"]},
            "action": "comparison",
        }
    elif shape == "need_second":
        assert body == {
            "success": True, "action": "need_second_product",
            "products": [{"brand": "B0", "name": "N0"}],
            "message": "Identified: B0 N0. Take another photo or type a product to compare with.",
            "vision_cost": 0.003,
        }
    else:
        body.pop("request_id", None)
        assert body == {
            "success": False, "action": "comparison_failed",
            "error": "Products identified " + chr(0x2014) + " comparing them is unavailable right now.",
            "code": "INTERNAL_ERROR", "products": _vision(2)["products"],
            "vision_cost": 0.003,
            "message": "Products identified but comparison failed. You can compare them via text.",
        }


# ===========================================================================
# end to end through the REAL identify_products (the tester scenarios)
# ===========================================================================
def _e2e(monkeypatch, client, reply):
    _full_config(monkeypatch, "true")
    monkeypatch.setenv(METER, "true")
    ledger, spy, _prefs = _stub_route(monkeypatch)
    _install_fake(monkeypatch, _reply(reply))
    resp = _post_identify(client)
    return resp, ledger, spy


def test_R18_v04_end_to_end(monkeypatch, client, authed):
    """RED: V04 (Sefiki watch vs a violin) -- the object reply is identified,
    the compare receives the V2 dicts (low confidence, categories, is_product),
    the wire carries public keys only; a delivery (refusal is B2's)."""
    resp, ledger, spy = _e2e(monkeypatch, client, V04_OBJECT)
    assert resp.status_code == 200
    assert len(spy.calls) == 1, resp.text[:300]
    args, kwargs = spy.calls[0]
    assert args == ("Sefiki Limited Edition vs Violin SHAHRAZAD L'INTENSE",)
    vp = kwargs["vision_products"]
    assert [p.get("confidence") for p in vp] == ["low", "low"]
    assert [p.get("_category", "missing") for p in vp] == [None, "other"]
    assert [p.get("_is_product") for p in vp] == [True, True]
    body = resp.json()
    assert body.get("action") == "comparison"
    ident = body["metadata"]["identified_products"]
    assert _no_underscore_keys(ident)
    assert [p["confidence"] for p in ident] == ["low", "low"]
    assert ledger.lifetime == [authed["id"]]
    assert ledger.refunds == []


def test_R19_v07_end_to_end(monkeypatch, client, authed):
    """RED: V07 (GUESS vs GUESS) -- the bare array reply; the distinguishing
    features reach the compare's vision products."""
    resp, ledger, spy = _e2e(monkeypatch, client, V07_ARRAY)
    assert resp.status_code == 200
    assert len(spy.calls) == 1, resp.text[:300]
    args, kwargs = spy.calls[0]
    assert args == ("GUESS GUESS! vs GUESS GUESS!",)
    vp = kwargs["vision_products"]
    assert vp[0].get("_distinguishing_features") == ["white logo tee"]
    assert vp[1].get("_distinguishing_features") == ["denim shirt", "polyurethane label"]
    assert _no_underscore_keys(resp.json()["metadata"]["identified_products"])


def test_R20_v01_end_to_end(monkeypatch, client, authed):
    """RED: V01 (OSMIA vs AL IBDAA) -- both fragrances, high; the route's size
    enrichment still appends 100ml; the wire carries public keys only."""
    resp, ledger, spy = _e2e(monkeypatch, client, V01_OBJECT)
    assert resp.status_code == 200
    assert len(spy.calls) == 1, resp.text[:300]
    args, kwargs = spy.calls[0]
    assert args == ("OSMIA Woody F vs AL IBDAA EAU DE PARFUM 100ml",)
    vp = kwargs["vision_products"]
    assert [p.get("_category") for p in vp] == ["fragrances", "fragrances"]
    assert [p.get("confidence") for p in vp] == ["high", "high"]
    ident = resp.json()["metadata"]["identified_products"]
    assert ident[1]["name"] == "EAU DE PARFUM 100ml"
    assert _no_underscore_keys(ident)


def test_R21_category_keys_match_the_text_path():
    """RED: VISION_CATEGORY_KEYS = the nine canonical keys in the A2b order."""
    keys = getattr(osvc, "VISION_CATEGORY_KEYS", None)
    assert keys is not None, "openai_service.VISION_CATEGORY_KEYS is missing"
    assert tuple(keys) == NINE
    assert set(keys) == set(extraction_service._CANONICAL_CATEGORIES)
    assert ", ".join(keys) + "\n" in extraction_service._CLASSIFY_CATEGORY_LLM_PROMPT


def test_R22_usage_none_is_tolerated_on(monkeypatch):
    """RED (P10 ON half): flag ON a reply without usage costs nothing and does
    not raise. Base: AttributeError at :227."""
    _full_config(monkeypatch, "true")
    _install_fake(monkeypatch, _reply("[]", usage=None))
    result, exc = _identify(2)
    assert exc is None, repr(exc)
    assert result == {"products": [], "tokens_used": 0, "cost": 0.0}


def test_R23_public_vision_products_copies_and_strips():
    """RED: public_vision_products returns a NEW list of NEW dicts without the
    underscore keys, passes a non-dict through, and maps None to []."""
    fn = getattr(osvc, "public_vision_products", None)
    assert callable(fn), "openai_service.public_vision_products is missing"
    src = [copy.deepcopy(V2_A), copy.deepcopy(V1_A), "x"]
    before = copy.deepcopy(src)
    out = fn(src)
    assert out == [_public(V2_A), V1_A, "x"]
    assert out is not src
    assert out[1] == src[1] and out[1] is not src[1]
    assert src == before
    assert fn(None) == []
    assert fn([]) == []


# ===========================================================================
# P8: log hygiene of the unit's own lines (ruling B3-R1)
# ===========================================================================
FORBIDDEN_IN_LOGS = ("Sefiki", "Violin", "SHAHRAZAD", "GUESS", "OSMIA", "IBDAA",
                     "I cannot help")
UNIT_LOG_PREFIXES = ("[VISION_V2]", "[IMAGE] preferences")
ALLOWED_ERROR_PREFIXES = ("[IMAGE] Vision call failed", "[IMAGE] Vision parse error")
WATCHED_LOGGERS = ("app.services.openai_service", "app.api.image_routes")


@pytest.mark.parametrize("scenario", [
    "service_v04", "service_refusal", "service_length", "route_v04", "route_v07",
    "route_v01", "route_refusal",
])
def test_P8_unit_log_lines_carry_no_product_text(monkeypatch, client, authed, caplog,
                                                 scenario):
    """PIN (green at base, vacuously; non-vacuous on the GREEN bytes): the
    unit's own [VISION_V2] / [IMAGE] preferences records never carry a brand, a
    name or the refusal text, and the watched loggers emit no ERROR outside the
    route's two existing vision exit lines."""
    caplog.set_level(logging.INFO)
    _full_config(monkeypatch, "true")
    if scenario.startswith("service_"):
        reply = {
            "service_v04": _reply(V04_OBJECT),
            "service_refusal": _reply(None, refusal="I cannot help with that"),
            "service_length": _reply('[{"brand": "Sefiki"', finish_reason="length"),
        }[scenario]
        _install_fake(monkeypatch, reply)
        _identify(2)
    else:
        monkeypatch.setenv(METER, "true")
        _stub_route(monkeypatch, prefs=_Prefs(raises=True))
        reply = {
            "route_v04": _reply(V04_OBJECT),
            "route_v07": _reply(V07_ARRAY),
            "route_v01": _reply(V01_OBJECT),
            "route_refusal": _reply(None, refusal="I cannot help with that"),
        }[scenario]
        _install_fake(monkeypatch, reply)
        _post_identify(client)
    for rec in caplog.records:
        msg = rec.getMessage()
        if msg.startswith(UNIT_LOG_PREFIXES):
            for word in FORBIDDEN_IN_LOGS:
                assert word not in msg, (word, msg)
        if rec.name in WATCHED_LOGGERS and rec.levelno >= logging.ERROR:
            assert msg.startswith(ALLOWED_ERROR_PREFIXES), msg

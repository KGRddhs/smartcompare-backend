"""CAM-2 VISION-GATE: the RED rows (S1-S8, R1-R3, R11, R12) and PIN rows (R4-R10) of the
camera vision gate (spec CAM2_UNIT_SPEC.md sections 2.2 and 5; gate GATE_CAM2.md CG-1..CG-12).

With ENABLE_ANTHROPIC_VISION ON the camera route sends a photo to Claude only when
X-Client-Capabilities lists vision_anthropic AND ENABLE_VISION_IDENTITY_V2 is ON; any other
Claude-bound photo is refused before any paid call with the 503 LLM_UNAVAILABLE envelope and
both refunds (VisionCapabilityRequiredError, an LLMUnavailableError). No new flag (CG-1).

RED = fails at the base d0b5a761 on an AssertionError only (a missing symbol is asserted
through the s06 _router / _sym helpers, never raised). PIN = green at the base and at head;
every PIN runs the FULL configuration (ruling B1: every KNOB, the synthetic key, TEXT +
VERDICT ON, PRE_V3 ON, EGRESS_STOP ON, HEADERS ON, V2 ON, the capability sent, consent 3)
and varies only its own axis, with recorders on identify, the consent reads, the
x-client-capabilities header reads, the route-level V2 reads and both provider fakes.

Hermetic: the s06 harness (its autouse fixture installs the ModuleSpec'd fake anthropic SDK
and clears the flags; the consent recorder; the OpenAI fakes; the route harness); no
network, no .env, synthetic values only (the sentinel is built at run time).
"""
import ast
import importlib
import inspect
import json
import logging
import types

import pytest

from tests.test_s81_s06_anthropic_router import (
    ANTH,
    IMAGES,
    JPEG_BYTES,
    ROOT,
    V1_ITEMS,
    V2_JSON,
    _ImplRec,
    _capture,
    _knobs,
    _route_harness,
    _router,
    _run,
    _s06_env,  # noqa: F401  (the autouse fixture: flags cleared, the fake SDK installed)
    _sym,
    abs_,
    c_msg,
    c_usage,
    consent,  # noqa: F401  (the consent recorder fixture)
    oai_fake,
    osvc,
    scs,
)

ROUTER_LOGGER = "app.services.llm_router"
IMAGE_LOGGER = "app.api.image_routes"
GATE_TEMPLATE = "[VISION_GATE] refused reason=%s"
VISION_FAIL_TEMPLATE = "[IMAGE] Vision call failed: %s"
CAP_HEADER = "x-client-capabilities"
VISION_CAP = "vision_anthropic"
GATE_CLASS = "VisionCapabilityRequiredError"
STOP_CLASS = "OpenAIEgressStoppedError"
CONSENT_CLASS = "ConsentUpdateRequiredError"
# The base 503 literal (recorded from scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE at d0b5a761); the
# dash is built with chr() so this file stays pure ASCII.
FRIENDLY_503 = "Still warming up the comparison engine " + chr(0x2014) + " give it another tap in a moment."
BASE_503_BODY = {"success": False, "error": FRIENDLY_503, "code": "LLM_UNAVAILABLE"}
VISION_OFF_SPELLINGS = (None, "", "false", "0", " OFF ", "garbage")
# A run-time sentinel carried in the capability header; never a real capability.
CAP_SENTINEL = "CAP" + "SENTINEL" + "v8"

# The FULL configuration of ruling B1 (the synthetic key and every knob come from _knobs).
FULL_FLAGS = {
    "ENABLE_ANTHROPIC_TEXT": "true",
    "ENABLE_ANTHROPIC_VERDICT": "true",
    "ENABLE_ANTHROPIC_VISION": "true",
    "ENABLE_OPENAI_PRE_V3": "true",
    "ENABLE_OPENAI_EGRESS_STOP": "true",
    "ENABLE_REQUEST_CONTEXT_HEADERS": "true",
    "ENABLE_VISION_IDENTITY_V2": "true",
}
# Flags the s06 autouse fixture does not clear; this file never inherits them.
CLEARED = (
    "ENABLE_OPENAI_EGRESS_STOP", "ENABLE_KB_FIRST_SERVE", "ENABLE_PRICE_NOT_LOST",
    "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_RESULT_GATE", "ENABLE_CAMERA_FAILURE_ENVELOPE",
    "ENABLE_ANON_USAGE_GATE", "ENABLE_RESULT_STATUS_METADATA", "ENABLE_COMPARE_RUN_LEDGER",
    "ENABLE_DEVICE_DAILY_QUOTA", "ENABLE_RESULT_AGGREGATES", "ENABLE_STORE_LABEL",
)


@pytest.fixture(autouse=True)
def _cam2_env(monkeypatch):
    for name in CLEARED:
        monkeypatch.delenv(name, raising=False)
    abs_._reset_openai_egress_stop_state()
    yield
    abs_._reset_openai_egress_stop_state()


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _full(monkeypatch, consent=None, **overrides):
    """The FULL unit configuration (ruling B1); an override of None unsets that name."""
    _knobs(monkeypatch)
    for name, value in {**FULL_FLAGS, **overrides}.items():
        _set(monkeypatch, name, value)
    if consent is not None:
        consent.set(3)


class _Hdrs:
    def __init__(self, value=None, raising=False):
        self.value, self.raising, self.calls = value, raising, []

    def get(self, key, default=None):
        self.calls.append(key)
        if self.raising:
            raise RuntimeError("cam2 probe: header read")
        return default if self.value is None else self.value


def _req(value=None, raising=False):
    h = _Hdrs(value, raising)
    return types.SimpleNamespace(headers=h), h


class _V2:
    def __init__(self, value=True, raising=False):
        self.value, self.raising, self.calls = value, raising, 0

    def __call__(self):
        self.calls += 1
        if self.raising:
            raise RuntimeError("cam2 probe: v2 read")
        return self.value


def _gate_lines(caplog):
    return [r for r in caplog.records if "[VISION_GATE]" in r.getMessage()]


def _gate_shape(caplog):
    return [(r.name, r.levelno, r.msg, r.args) for r in _gate_lines(caplog)]


def _fail_types(caplog):
    """The type names of the camera arm WARNING '[IMAGE] Vision call failed: %s'."""
    return [r.args[0] for r in caplog.records
            if r.name == IMAGE_LOGGER and r.levelno == logging.WARNING
            and r.msg == VISION_FAIL_TEMPLATE and r.args]


def _assert_503(resp, label=""):
    assert resp.status_code == 503, (label, resp.status_code, resp.text[:300])
    body = resp.json()
    assert body.get("code") == "LLM_UNAVAILABLE", (label, body)
    assert body.get("error") == FRIENDLY_503, (label, body)
    return body


class _Cam:
    """The r10c route harness (s06 _route_harness + the compare fake) plus the B1 recorders:
    identify (the route's own name, delegating to the real call), the x-client-capabilities
    header reads, the route-level V2 reads, both OpenAI fakes (chat + moderation) and ANTH."""

    def __init__(self, monkeypatch, request, *, v2_reply=True):
        from starlette.datastructures import Headers

        from app.api import image_routes
        from app.middleware.rate_limiter import limiter

        self.limiter = limiter
        self.oai, self.mods, self.identify, self.cap_reads, self.v2_reads = [], [], [], [], []
        self.reply(v2_reply)
        oai, mods = self.oai, self.mods
        monkeypatch.setattr(osvc, "client", oai_fake(oai, V2_JSON))
        monkeypatch.setattr(osvc, "get_client", lambda *a, **k: oai_fake(oai, mod_store=mods))

        class _Svc:
            async def compare_from_text(self, *a, **k):
                return {"success": True, "metadata": {"total_cost": 0.0}, "products": [], "overview": {}}

        monkeypatch.setattr(image_routes, "StructuredComparisonService", _Svc)

        async def _prefs(*a, **k):
            return {"success": False}

        monkeypatch.setattr(image_routes, "get_user_preferences", _prefs)
        real_identify = image_routes.identify_products
        identify = self.identify

        async def _identify(image_data_list, *a, **k):
            identify.append(len(image_data_list))
            return await real_identify(image_data_list, *a, **k)

        monkeypatch.setattr(image_routes, "identify_products", _identify)
        real_v2 = image_routes.vision_identity_v2_enabled
        v2_reads = self.v2_reads

        def _v2():
            v2_reads.append(1)
            return real_v2()

        monkeypatch.setattr(image_routes, "vision_identity_v2_enabled", _v2)
        real_get = Headers.get
        cap_reads = self.cap_reads

        def _get(hself, key, default=None):
            if isinstance(key, str) and key.lower() == CAP_HEADER:
                cap_reads.append(key)
            return real_get(hself, key, default)

        monkeypatch.setattr(Headers, "get", _get)
        self.client, self.led, self.user = _route_harness(monkeypatch, request)

    @staticmethod
    def reply(v2=True):
        text = V2_JSON if v2 else json.dumps({"products": V1_ITEMS})
        ANTH.default = c_msg(text, usage=c_usage(1000, 100))

    def reset(self):
        for rec in (self.oai, self.mods, self.identify, self.cap_reads, self.v2_reads, ANTH.calls,
                    self.led.consumes, self.led.refunds, self.led.lifetime, self.led.saves):
            del rec[:]

    def post(self, caps=None, extra=None):
        try:
            self.limiter.reset()
        except Exception:  # noqa: BLE001 - the conftest reset idiom
            pass
        headers = dict(extra or {})
        if caps is not None:
            headers["X-Client-Capabilities"] = caps
        files = [("images", ("a.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
                 ("images", ("b.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg"))]
        return self.client.post("/api/v1/image/identify", files=files, headers=headers)


def _assert_gate_refusal(cam, resp, caplog, reason, label=""):
    _assert_503(resp, label)
    assert cam.identify == [], (label, "identify_products ran", cam.identify)
    assert ANTH.calls == [], (label, "Claude was called", len(ANTH.calls))
    assert cam.oai == [] and cam.mods == [], (label, len(cam.oai), len(cam.mods))
    assert cam.led.consumes == [cam.user["id"]], (label, cam.led.consumes)
    assert cam.led.refunds == cam.led.consumes, (label, cam.led.refunds)
    assert cam.led.lifetime == [] and cam.led.saves == [], label
    assert _fail_types(caplog) == [GATE_CLASS], (label, _fail_types(caplog))
    assert [r.args for r in _gate_lines(caplog)] == [(reason,)], (label, _gate_shape(caplog))


# ===========================================================================
# S1-S8: the router symbols and the gate function (direct calls)
# ===========================================================================
def test_s1_symbols():
    """S1 RED (2.2): the constants, the error class (an LLMUnavailableError that is neither a
    ConsentUpdateRequiredError nor an OpenAIEgressStoppedError) and the two functions."""
    r = _router()
    assert _sym("VISION_CAPABILITY") == VISION_CAP
    assert _sym("VISION_CAPABILITY_MAX_CHARS") == 512
    reasons = _sym("VISION_GATE_REASONS")
    assert isinstance(reasons, tuple) and reasons == ("v1_site", "capability_absent"), reasons
    cls = _sym(GATE_CLASS)
    assert isinstance(cls, type) and issubclass(cls, abs_.LLMUnavailableError), cls
    assert not issubclass(cls, r.ConsentUpdateRequiredError)
    assert not issubclass(cls, abs_.OpenAIEgressStoppedError)
    assert str(cls()) == "vision gate refused; dispatch suppressed"
    for name, params in (("client_vision_capable", ["request"]),
                         ("camera_vision_gate_refuses", ["request", "vision_v2_enabled"])):
        fn = _sym(name)
        assert callable(fn), name
        assert list(inspect.signature(fn).parameters) == params, (name, inspect.signature(fn))


def test_s2_reader_exact_token(monkeypatch, consent, caplog):
    """S2 RED (2.2 / 2.4): client_vision_capable is the kb_serve parse (comma tokens, strip +
    lower, the 512 cap, an exception is no capability) and never logs."""
    _full(monkeypatch, consent)
    fn = _sym("client_vision_capable")
    caplog.set_level(logging.DEBUG)
    head = VISION_CAP + ","
    at_cap = head + "x" * (512 - len(head))
    over_cap = at_cap + "x"
    assert len(at_cap) == 512 and len(over_cap) == 513
    for value in (VISION_CAP, "price_size," + VISION_CAP, " VISION_ANTHROPIC ", at_cap):
        req, h = _req(value)
        assert fn(req) is True, value[:40]
        assert h.calls and all(k.lower() == CAP_HEADER for k in h.calls), h.calls
    for value in (None, "", "price_size", "x" + VISION_CAP, "vision anthropic", over_cap):
        req, h = _req(value)
        assert fn(req) is False, (value or "")[:40]
    req, h = _req(VISION_CAP, raising=True)
    assert fn(req) is False
    assert h.calls, "the raising getter was never called"
    assert [r for r in caplog.records if r.name == ROUTER_LOGGER] == []


def test_s3_vision_off_reads_nothing_else(monkeypatch, consent, caplog):
    """S3 RED (2.2 first statement): every VISION OFF spelling returns False with zero consent,
    header and V2 reads (the FULL configuration otherwise, the capability sent)."""
    _full(monkeypatch, consent)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    for value in VISION_OFF_SPELLINGS:
        _set(monkeypatch, "ENABLE_ANTHROPIC_VISION", value)
        del consent.reads[:]
        req, h = _req(VISION_CAP)
        v2 = _V2(True)
        assert gate(req, v2) is False, value
        assert consent.reads == [] and h.calls == [] and v2.calls == 0, (value, consent.reads, h.calls, v2.calls)
    assert _gate_lines(caplog) == []


def test_s4_capable_v2_passes(monkeypatch, consent, caplog):
    """S4 RED: VISION ON, consent 3, V2 ON, the capability sent: False (one V2 read, one header
    read, no gate record)."""
    _full(monkeypatch, consent)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    req, h = _req(VISION_CAP)
    v2 = _V2(True)
    assert gate(req, v2) is False
    assert v2.calls == 1 and len(h.calls) == 1, (v2.calls, h.calls)
    assert consent.reads, "decide never read the consent version"
    assert _gate_lines(caplog) == []


def test_s5_no_capability_refuses(monkeypatch, consent, caplog):
    """S5 RED: V2 ON and no vision_anthropic token (absent; the 1.0.0 'price_size'): True and
    exactly one INFO '[VISION_GATE] refused reason=capability_absent'."""
    _full(monkeypatch, consent)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    for value in (None, "price_size"):
        caplog.clear()
        req, h = _req(value)
        v2 = _V2(True)
        assert gate(req, v2) is True, value
        assert _gate_shape(caplog) == [(ROUTER_LOGGER, logging.INFO, GATE_TEMPLATE, ("capability_absent",))], (
            value, _gate_shape(caplog))
        assert v2.calls == 1 and len(h.calls) == 1, (value, v2.calls, h.calls)


def test_s6_v1_refused_before_header_read(monkeypatch, consent, caplog):
    """S6 RED (CG-2 / CG-6): V2 OFF + the capability sent: True, reason v1_site, zero header
    reads (v1_site is decided before the capability)."""
    _full(monkeypatch, consent, ENABLE_VISION_IDENTITY_V2=None)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    req, h = _req(VISION_CAP)
    v2 = _V2(False)
    assert gate(req, v2) is True
    assert _gate_shape(caplog) == [(ROUTER_LOGGER, logging.INFO, GATE_TEMPLATE, ("v1_site",))], _gate_shape(caplog)
    assert h.calls == [] and v2.calls == 1, (h.calls, v2.calls)


def test_s7_openai_decision_passes_unread(monkeypatch, consent, caplog):
    """S7 RED: decide('vision') == 'openai' (consent 2, absent, malformed; PRE_V3 ON): False with
    zero header and V2 reads, no capability sent (a gate that skipped decide would refuse)."""
    _full(monkeypatch, consent)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    for value, state in ((2, "ok"), (None, "absent"), (None, "malformed")):
        consent.set(value, state)
        del consent.reads[:]
        req, h = _req(None)
        v2 = _V2(True)
        assert gate(req, v2) is False, (value, state)
        assert h.calls == [] and v2.calls == 0, (value, state, h.calls, v2.calls)
        assert consent.reads, (value, state, "decide never read the consent version")
    assert _gate_lines(caplog) == []


def test_s8_v2_reader_raising_is_v1(monkeypatch, consent, caplog):
    """S8 RED (2.2 try): a raising V2 reader is V1: True, reason v1_site, zero header reads."""
    _full(monkeypatch, consent)
    gate = _sym("camera_vision_gate_refuses")
    caplog.set_level(logging.INFO)
    req, h = _req(VISION_CAP)
    v2 = _V2(True, raising=True)
    assert gate(req, v2) is True
    assert _gate_shape(caplog) == [(ROUTER_LOGGER, logging.INFO, GATE_TEMPLATE, ("v1_site",))], _gate_shape(caplog)
    assert h.calls == [] and v2.calls == 1, (h.calls, v2.calls)


# ===========================================================================
# R1-R12: the camera route (TestClient), the text entry, the direct harness, the source
# ===========================================================================
def test_r1_route_no_capability_header_refused(monkeypatch, consent, request, caplog):
    """R1 RED (W6): VISION ON, consent 3, V2 ON, no X-Client-Capabilities: the coded 503 with the
    friendly constant, identify 0, ANTH 0, OpenAI 0, refunds == consumes, the WARNING by type."""
    _full(monkeypatch, consent)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    _assert_gate_refusal(cam, cam.post(caps=None), caplog, "capability_absent")


def test_r2_route_100_header_refused(monkeypatch, consent, request, caplog):
    """R2 RED (W6, the 1.0.0 header): X-Client-Capabilities 'price_size' only: as R1."""
    _full(monkeypatch, consent)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    _assert_gate_refusal(cam, cam.post(caps="price_size"), caplog, "capability_absent")


def test_r3_route_v1_refused(monkeypatch, consent, request, caplog):
    """R3 RED (W5, CG-2): V2 OFF + the capability sent: as R1 (reason v1_site, no header read)."""
    _full(monkeypatch, consent, ENABLE_VISION_IDENTITY_V2=None)
    cam = _Cam(monkeypatch, request, v2_reply=False)
    caplog.set_level(logging.INFO)
    _assert_gate_refusal(cam, cam.post(caps=VISION_CAP), caplog, "v1_site")
    assert cam.cap_reads == [], cam.cap_reads


def test_r4_w7_capable_photo_reaches_claude(monkeypatch, consent, request, caplog):
    """R4 PIN (W7, the r10c harness): the FULL configuration, the capability sent: 200
    comparison, identify 1, ANTH 1, OpenAI 0, no refund, no gate record."""
    _full(monkeypatch, consent)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    resp = cam.post(caps=VISION_CAP)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    assert resp.json().get("action") == "comparison", resp.text[:300]
    assert cam.identify == [2], cam.identify
    assert len(ANTH.calls) == 1, len(ANTH.calls)
    assert cam.oai == [] and cam.mods == [], (len(cam.oai), len(cam.mods))
    assert cam.led.refunds == [], cam.led.refunds
    assert _fail_types(caplog) == [] and _gate_lines(caplog) == [], (_fail_types(caplog), _gate_shape(caplog))


def test_r5_w2_headers_off_real_consent_header(monkeypatch, request, caplog):
    """R5 PIN (W2): HEADERS OFF + a real X-AI-Consent-Version 3 (the REAL consent reader, recorded):
    every read is None, decide openai, the egress stop: 503 by OpenAIEgressStoppedError, ANTH 0."""
    _full(monkeypatch, None, ENABLE_REQUEST_CONTEXT_HEADERS=None)
    rc = importlib.import_module("app.utils.request_context")
    assert rc.parse_consent_version("3") == 3
    seen = []
    real_cv = rc.consent_version

    def _cv():
        value = real_cv()
        seen.append(value)
        return value

    monkeypatch.setattr(rc, "consent_version", _cv)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    resp = cam.post(caps=VISION_CAP, extra={"X-AI-Consent-Version": "3"})
    _assert_503(resp)
    assert _fail_types(caplog) == [STOP_CLASS], _fail_types(caplog)
    assert ANTH.calls == [], len(ANTH.calls)
    assert cam.identify == [2], cam.identify
    assert seen and all(v is None for v in seen), seen
    assert cam.cap_reads == [] and cam.v2_reads == [], (cam.cap_reads, cam.v2_reads)
    assert cam.oai == [] and cam.mods == [], (len(cam.oai), len(cam.mods))
    assert cam.led.refunds == cam.led.consumes, (cam.led.refunds, cam.led.consumes)
    assert _gate_lines(caplog) == [], _gate_shape(caplog)


def test_r6_w4_consent_2_no_capability_stopped(monkeypatch, consent, request, caplog):
    """R6 PIN (W4): consent 2, no capability sent: 503 by the egress stop, OpenAI HTTP 0, ANTH 0,
    zero header and V2 reads, no VISION_GATE record."""
    _full(monkeypatch, consent)
    consent.set(2)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    resp = cam.post(caps=None)
    _assert_503(resp)
    assert _fail_types(caplog) == [STOP_CLASS], _fail_types(caplog)
    assert cam.oai == [] and cam.mods == [], (len(cam.oai), len(cam.mods))
    assert ANTH.calls == [], len(ANTH.calls)
    assert cam.identify == [2], cam.identify
    assert cam.cap_reads == [] and cam.v2_reads == [], (cam.cap_reads, cam.v2_reads)
    assert _gate_lines(caplog) == [], _gate_shape(caplog)


def test_r7_w3_vision_off_body_identical(monkeypatch, consent, request, caplog):
    """R7 PIN (W3, B1): each VISION OFF spelling with the FULL configuration otherwise: identify
    once, zero header and V2 reads, the consent reads of camera_refuses_for_consent alone, the
    body equal to the base literal (the egress-stop 503)."""
    r = _router()
    _full(monkeypatch, consent)
    cam = _Cam(monkeypatch, request)
    caplog.set_level(logging.INFO)
    for value in VISION_OFF_SPELLINGS:
        _set(monkeypatch, "ENABLE_ANTHROPIC_VISION", value)
        del consent.reads[:]
        assert r.camera_refuses_for_consent() is False, value
        entry_reads = len(consent.reads)
        del consent.reads[:]
        cam.reset()
        caplog.clear()
        resp = cam.post(caps=VISION_CAP)
        assert resp.status_code == 503, (value, resp.status_code, resp.text[:300])
        body = resp.json()
        assert isinstance(body.get("request_id"), str), (value, body)
        assert {k: v for k, v in body.items() if k != "request_id"} == BASE_503_BODY, (value, body)
        assert cam.identify == [2], (value, cam.identify)
        assert cam.cap_reads == [] and cam.v2_reads == [], (value, cam.cap_reads, cam.v2_reads)
        assert len(consent.reads) == entry_reads, (value, len(consent.reads), entry_reads)
        assert _fail_types(caplog) == [STOP_CLASS], (value, _fail_types(caplog))
        assert ANTH.calls == [] and cam.oai == [] and cam.mods == [], value
        assert _gate_lines(caplog) == [], (value, _gate_shape(caplog))


def test_r8_text_compare_untouched(monkeypatch, consent, caplog):
    """R8 PIN: VISION ON, consent 3, no capability (no request at all): the text entry gate stays
    False and compare_from_text enters the impl; no VISION_GATE record."""
    r = _router()
    _full(monkeypatch, consent)
    caplog.set_level(logging.INFO)
    assert r.compare_refuses_for_consent() is False
    impl = _ImplRec()
    monkeypatch.setattr(scs.StructuredComparisonService, "_compare_from_text_impl", impl)
    _run(_capture(scs.StructuredComparisonService().compare_from_text("a vs b")))
    assert impl.calls == 1, impl.calls
    assert _gate_lines(caplog) == [], _gate_shape(caplog)


def test_r9_consent_gate_refuses_first(monkeypatch, consent, request, caplog):
    """R9 PIN: consent None + PRE_V3 OFF, and the key unset + consent 3, each with and without the
    capability: 503 by ConsentUpdateRequiredError, identify 0, ANTH 0, zero header and V2 reads,
    no VISION_GATE record (the consent gate is first)."""
    cam = None
    cases = (("consent_none_pre_v3_off", "ENABLE_OPENAI_PRE_V3", None),
             ("key_unset_consent_3", "ANTHROPIC_API_KEY", 3))
    for label, unset_name, consent_value in cases:
        for caps in (VISION_CAP, None):
            _full(monkeypatch, consent)
            _set(monkeypatch, unset_name, None)
            consent.set(consent_value)
            if cam is None:
                cam = _Cam(monkeypatch, request)
                caplog.set_level(logging.INFO)
            cam.reset()
            caplog.clear()
            tag = (label, caps)
            _assert_503(cam.post(caps=caps), tag)
            assert _fail_types(caplog) == [CONSENT_CLASS], (tag, _fail_types(caplog))
            assert cam.identify == [] and ANTH.calls == [], (tag, cam.identify, len(ANTH.calls))
            assert cam.oai == [] and cam.mods == [], tag
            assert cam.cap_reads == [] and cam.v2_reads == [], (tag, cam.cap_reads, cam.v2_reads)
            assert cam.led.refunds == cam.led.consumes == [cam.user["id"]], (tag, cam.led.refunds)
            assert _gate_lines(caplog) == [], (tag, _gate_shape(caplog))


def test_r10_identify_direct_keeps_v1_on_claude(monkeypatch, consent, caplog):
    """R10 PIN (L2, CG-3 route only): identify_products called directly (the S81-07 harness
    shape), VISION ON, consent 3, V2 OFF: one Claude call, no OpenAI call, two products."""
    _full(monkeypatch, consent, ENABLE_VISION_IDENTITY_V2=None)
    oai = []
    monkeypatch.setattr(osvc, "client", oai_fake(oai, json.dumps(V1_ITEMS)))
    monkeypatch.setattr(osvc, "get_client", lambda *a, **k: oai_fake(oai, mod_store=[]))
    ANTH.default = c_msg(json.dumps({"products": V1_ITEMS}), usage=c_usage(1000, 100))
    caplog.set_level(logging.INFO)
    status, out = _run(_capture(osvc.identify_products(IMAGES)))
    assert status == "ok", (status, type(out).__name__)
    assert len(ANTH.calls) == 1 and oai == [], (len(ANTH.calls), len(oai))
    assert isinstance(out, dict) and len(out.get("products") or []) == 2, out
    assert _gate_lines(caplog) == [], _gate_shape(caplog)


def test_r11_refusal_logs_carry_no_header_value(monkeypatch, consent, request, caplog):
    """R11 RED (log hygiene): the R1-R3 refusals with a run-time sentinel inside the capability
    header: each refuses with one INFO gate record whose args are in VISION_GATE_REASONS, and
    no record (message or args) carries the sentinel."""
    cam = None
    cases = (("sentinel_only", CAP_SENTINEL, "true"),
             ("price_size_and_sentinel", "price_size," + CAP_SENTINEL, "true"),
             ("v1_with_capability", VISION_CAP + "," + CAP_SENTINEL, None))
    for label, caps, v2 in cases:
        _full(monkeypatch, consent, ENABLE_VISION_IDENTITY_V2=v2)
        if cam is None:
            cam = _Cam(monkeypatch, request)
            caplog.set_level(logging.DEBUG)
        cam.reply(v2 is not None)
        cam.reset()
        caplog.clear()
        resp = cam.post(caps=caps)
        lines = _gate_lines(caplog)
        assert len(lines) == 1, (label, resp.status_code, _gate_shape(caplog))
        assert lines[0].levelno == logging.INFO and lines[0].args, (label, _gate_shape(caplog))
        reasons = _sym("VISION_GATE_REASONS")
        assert all(a in reasons for a in lines[0].args), (label, lines[0].args)
        _assert_503(resp, label)
        blob = "\n".join(r.getMessage() + " " + repr(r.args) for r in caplog.records)
        assert CAP_SENTINEL not in blob, (label, "a log record carries the header value")


def _callee(node):
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def test_r12_call_site_order_ast():
    """R12 RED (CG-3): image_routes.py calls camera_vision_gate_refuses exactly once, inside the
    identify_and_compare try, after camera_refuses_for_consent and before identify_products,
    as `if _llm_router.camera_vision_gate_refuses(request, vision_identity_v2_enabled):
    raise _llm_router.VisionCapabilityRequiredError()`."""
    src = (ROOT / "app" / "api" / "image_routes.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    gate_calls = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and _callee(n) == "camera_vision_gate_refuses"]
    assert len(gate_calls) == 1, ("camera_vision_gate_refuses calls in image_routes.py", len(gate_calls))
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.AsyncFunctionDef) and n.name == "identify_and_compare"), None)
    assert fn is not None, "identify_and_compare is missing"
    target = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Try):
            names = {_callee(c) for stmt in node.body for c in ast.walk(stmt) if isinstance(c, ast.Call)}
            if "camera_refuses_for_consent" in names and "identify_products" in names:
                target = node
                break
    assert target is not None, "the vision try (consent gate + identify_products) is missing"

    def _index(name):
        for i, stmt in enumerate(target.body):
            if any(isinstance(c, ast.Call) and _callee(c) == name for c in ast.walk(stmt)):
                return i
        return None

    i_consent, i_gate, i_identify = (_index("camera_refuses_for_consent"),
                                     _index("camera_vision_gate_refuses"), _index("identify_products"))
    assert i_gate is not None, "the gate call is not in the identify_and_compare try body"
    assert i_consent < i_gate < i_identify, (i_consent, i_gate, i_identify)
    call = gate_calls[0]
    assert isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name), ast.dump(call.func)
    assert call.func.value.id == "_llm_router", call.func.value.id
    assert all(isinstance(a, ast.Name) for a in call.args), ast.dump(call)
    assert [a.id for a in call.args] == ["request", "vision_identity_v2_enabled"], ast.dump(call)
    assert call.keywords == [], ast.dump(call)
    stmt = target.body[i_gate]
    assert isinstance(stmt, ast.If) and stmt.test is call, ast.dump(stmt)
    raises = [s for s in stmt.body if isinstance(s, ast.Raise)]
    assert raises and isinstance(raises[0].exc, ast.Call), ast.dump(stmt)
    assert _callee(raises[0].exc) == GATE_CLASS, ast.dump(raises[0])

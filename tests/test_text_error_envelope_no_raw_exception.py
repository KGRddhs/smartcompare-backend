"""W4-9 (PO-RECORDED-MEASURED-05) — the comparison orchestrators' generic
``except Exception`` must never put ``str(e)`` on the wire.

Spec: ``.qa-w4/W4_9_UNIT_SPEC.md`` § 4 AS AMENDED by its "FABLE REVIEW RULINGS
(binding, 2026-09-23)" section (R2 scope, R3 tests). This file covers the
orchestrator exits (scs sync + stream generic catch), the sync route floor in
``text_routes._surface_comparison_failure``, the SSE route floor + request_id
stamp in ``text_routes.text_compare_stream``, and the two surfaces the source
fix closes for free (``/text/quick`` and the camera ``return result`` arm).
The extraction_service layer (R2(b) parser catch, R2(c) verdict catch, the R3
rewrite of test 4) lives in ``tests/test_w49_extraction_catch_redaction.py``.

WHAT THIS IS NOT (R1): the phones run the 97b5f15 bundle with
ENABLE_EXPO_FETCH_SSE_DEFAULT=false, so a text compare is sync
``GET /api/v1/text/compare`` and the pre-OTA Alert shows the axios string
before AND after this fix. These tests pin WIRE disclosure (direct API
callers, persisted + shared payloads), never a UI improvement.

Injection sites follow R3: the phones' real request shape is
``product_a``/``product_b`` -> ``explicit_pair`` which SKIPS
``parse_product_query``, and the vision path skips it too, so failures are
injected at ``_resolve_pair_category`` (runs on every path) as well as at the
parser. Every test runs under a socket guard that blocks every non-loopback
connect + DNS lookup and fails the test if anything other than the conftest's
neutralised ``*.invalid`` sentinel host was attempted.

Numbering follows spec § 4 (test 7 DROPPED per R3 — it duplicated
``test_text_routes_error_mapping.py::test_no_code_raises_400_plain``).
RED at b63a8368: 01, 02, 05, 09, 13, 14, 16 (R3 phone shape), 15 (constant
absent). PIN (green at b63a8368): 03, 04b, 06, 08, 09b, 10, 11, 12.
Added in the fix round (floors fail CLOSED on a non-str `error`): 08b, 12b —
at b63a8368 08b fails (plain-string detail, not the envelope) and 12b fails
(raw text serialised verbatim); against a floor WITHOUT the isinstance guard
both raise TypeError.
"""
import copy
import json
import logging
import os
import socket
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.services.structured_comparison_service as scs  # noqa: E402
from app.api.text_routes import _surface_comparison_failure  # noqa: E402
from app.main import app  # noqa: E402

_SECRET = 'relation "comparisons" does not exist'
_INFRA = ('connection to server at "db.abcdefgh.supabase.co" (10.0.0.5), '
          'port 5432 failed; SQLSTATE 42P01')

# LITERAL user copy (R3: guard copy against the literal, never the imported
# constant — an imported-constant comparison cannot redden a "change the
# constant's text" mutation).
_PARSE_COPY = "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'"

_PAIR = ("Alpha One", "Beta Two")
_PAIR_QUERY = "Alpha One vs Beta Two"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """/text/compare, /compare/stream, /quick and /image/identify are 10/min
    per IP; this file makes more than 10 TestClient calls. Mirror of
    tests/test_text_routes_error_mapping.py."""
    from app.middleware.rate_limiter import limiter

    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    yield


@pytest.fixture(autouse=True)
def _default_flag_state(monkeypatch):
    """The unit is unflagged; pin the flags that fork the paths these tests
    drive to their prod-default OFF so an operator .env cannot change them."""
    for name in ("ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_COMPARISON_ID_ECHO",
                 "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_ANON_USAGE_GATE"):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def socket_guard(monkeypatch):
    """Block every non-loopback connect and DNS lookup; fail the test if
    anything but the conftest-neutralised ``*.invalid`` sentinel was tried
    (fire-and-forget log_search resolves ``neutralized.supabase.invalid`` —
    blocked here, never sent)."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _loop(host):
        return host in ("127.0.0.1", "::1", "localhost", "", None)

    def _connect(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect", str(host)))
            raise OSError(f"W4-9 socket guard: connect to {host!r} blocked")
        return real_connect(self, addr)

    def _connect_ex(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect_ex", str(host)))
            raise OSError(f"W4-9 socket guard: connect_ex to {host!r} blocked")
        return real_connect_ex(self, addr)

    def _gai(host, *a, **k):
        if not _loop(host):
            attempts.append(("getaddrinfo", str(host)))
            raise socket.gaierror(f"W4-9 socket guard: DNS for {host!r} blocked")
        return real_gai(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    yield attempts
    unexpected = [a for a in attempts if not a[1].endswith(".invalid")]
    assert not unexpected, f"W4-9 socket guard: real egress attempted: {unexpected}"


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _const(name):
    """Resolve a W4-9 constant at TEST time (not import time) so that at
    b63a8368 the file still collects and every red test reddens on an
    ASSERTION, never on an ImportError."""
    val = getattr(scs, name, None)
    assert isinstance(val, str) and val, (
        f"W4-9: structured_comparison_service.{name} is not exported"
    )
    return val


def _unescape(text):
    # json.dumps escapes the inner quotes of _SECRET/_INFRA; a naive `in`
    # over the raw body gives a FALSE NEGATIVE (spec § 4, probe v1).
    return text.replace('\\"', '"')


def _leaks(text, needle):
    return needle in _unescape(text)


def _dumps(obj):
    return _unescape(json.dumps(obj, default=str, ensure_ascii=False))


def _sse(text):
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        ev, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                ev = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((ev, data))
    return events


def _drain(agen):
    async def _go():
        return [ev async for ev in agen]
    return asyncio.run(_go())


def _inject(site):
    """Patch context for a failure raised INSIDE the orchestrator's try:.

    ``parser``        -> parse_product_query raises (the q= path).
    ``explicit_pair`` -> _resolve_pair_category raises (the phones' pair shape
                         and the vision path; parse_product_query never runs).
    """
    if site == "parser":
        return patch.object(scs, "parse_product_query",
                            AsyncMock(side_effect=Exception(_SECRET)))
    return patch.object(scs, "_resolve_pair_category",
                        AsyncMock(side_effect=Exception(_SECRET)))


def _call_kwargs(site):
    if site == "parser":
        return {"query": "alpha vs beta"}
    return {"query": _PAIR_QUERY, "explicit_pair": _PAIR}


def _stub_sync_service(result):
    svc = MagicMock()
    svc.compare_from_text = AsyncMock(return_value=copy.deepcopy(result))
    return svc


def _stub_stream_service(events):
    svc = MagicMock()
    events = copy.deepcopy(events)

    async def _gen(*a, **k):
        for ev in events:
            yield ev

    svc.compare_from_text_streaming = _gen
    return svc


def _send(client, verb, params):
    if verb == "post":
        return client.post("/api/v1/text/compare", json=params)
    return client.get("/api/v1/text/compare", params=params)


_PAIR_PARAMS = {"product_a": _PAIR[0], "product_b": _PAIR[1]}


# ===========================================================================
# Class A — the service exits (the SOURCE fix)
# ===========================================================================

@pytest.mark.parametrize("site", ["parser", "explicit_pair"])
def test_01_sync_generic_catch_returns_internal_error_envelope(site):
    """RED at b63a8368 (probe 5): the real scs generic catch returns
    {"success": False, "error": str(e)} with no code."""
    svc = scs.StructuredComparisonService()
    with _inject(site):
        result = asyncio.run(svc.compare_from_text(**_call_kwargs(site)))
    assert result.get("success") is False
    assert _SECRET not in _dumps(result), f"raw exception text on the result: {result!r}"
    assert result.get("code") == "INTERNAL_ERROR", result
    assert result.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")


@pytest.mark.parametrize("site", ["parser", "explicit_pair"])
def test_02_stream_generic_catch_yields_internal_error_envelope(site):
    """RED at b63a8368 (probe 5): the terminal stream event is
    ("error", {"success": False, "error": str(e), "total_cost": ...})."""
    svc = scs.StructuredComparisonService()
    with _inject(site):
        events = _drain(svc.compare_from_text_streaming(**_call_kwargs(site)))
    assert events, "stream yielded nothing"
    etype, payload = events[-1]
    assert etype == "error", [e[0] for e in events]
    assert _SECRET not in _dumps(events), f"raw exception text in a stream event: {payload!r}"
    assert payload.get("code") == "INTERNAL_ERROR", payload
    assert payload.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")


@pytest.mark.parametrize("path", ["sync", "stream"])
def test_03_pin_generic_catch_still_logs_raw_text_with_exc_info(path, caplog):
    """PIN (green at b63a8368): the diagnostic keeps going to the log/Sentry.
    Reddens if the fix deletes the logger.error(..., exc_info=True) line."""
    svc = scs.StructuredComparisonService()
    with caplog.at_level(logging.ERROR), _inject("explicit_pair"):
        if path == "sync":
            asyncio.run(svc.compare_from_text(**_call_kwargs("explicit_pair")))
        else:
            _drain(svc.compare_from_text_streaming(**_call_kwargs("explicit_pair")))
    hits = [r for r in caplog.records
            if r.name == "app.services.structured_comparison_service"
            and _SECRET in r.getMessage()]
    assert hits, "the raw exception text no longer reaches the scs error log"
    assert any(r.exc_info for r in hits), "the scs error log lost exc_info"


@pytest.mark.parametrize("path", ["sync", "stream"])
def test_04b_pin_parser_empty_products_keeps_literal_sentence_and_no_code(path):
    """PIN (green at b63a8368, probe 5 `parser-fail has code? False`): the
    parser exit's codeless user sentence is product copy, compared against
    the LITERAL (R3). Reddens if :3542/:4118 gain a code or their copy
    changes. The R3 rewrite of test 4 (real parser raising) lives in
    tests/test_w49_extraction_catch_redaction.py."""
    svc = scs.StructuredComparisonService()
    with patch.object(scs, "parse_product_query",
                      AsyncMock(return_value=({"products": []}, {}))):
        if path == "sync":
            out = asyncio.run(svc.compare_from_text(query="alpha vs beta"))
        else:
            events = _drain(svc.compare_from_text_streaming(query="alpha vs beta"))
            assert events[-1][0] == "error", [e[0] for e in events]
            out = events[-1][1]
    assert out.get("success") is False
    assert out.get("error") == _PARSE_COPY
    assert "code" not in out, out


# ===========================================================================
# Class B — the sync wire (ROUTE floor; the service is stubbed, so the source
# fix is bypassed by construction)
# ===========================================================================

@pytest.mark.parametrize("needle", [_SECRET, _INFRA], ids=["relation", "infra"])
@pytest.mark.parametrize("verb", ["post", "get"])
def test_05_sync_route_floor_redacts_codeless_unrecognised_message(client, verb, needle):
    """RED at b63a8368 (probe 2 A/A2): body.error == needle, code BAD_REQUEST."""
    svc = _stub_sync_service({"success": False, "error": needle, "total_cost": 0.0})
    with patch("app.api.text_routes.get_comparison_service", return_value=svc):
        resp = _send(client, verb, _PAIR_PARAMS)
    assert resp.status_code == 400, resp.text  # R4: 400 stays in this unit
    assert not _leaks(resp.text, needle), f"raw message on the wire: {resp.text}"
    body = resp.json()
    assert body.get("code") == "INTERNAL_ERROR", body
    assert body.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")
    assert body.get("request_id"), body


@pytest.mark.parametrize("verb", ["post", "get"])
def test_06_pin_parser_sentence_survives_the_sync_floor(client, verb):
    """PIN (green at b63a8368, probe 3): the one legitimate codeless sentence
    passes the allowlist unchanged — compared against the LITERAL (R3).
    Reddens under an unconditional floor, or if the allowlisted constant's
    text drifts from the literal the orchestrator emits."""
    svc = _stub_sync_service({"success": False, "error": _PARSE_COPY, "parsed": {}})
    with patch("app.api.text_routes.get_comparison_service", return_value=svc):
        resp = _send(client, verb, _PAIR_PARAMS)
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body.get("error") == _PARSE_COPY
    assert body.get("code") == "BAD_REQUEST", body
    assert body.get("request_id"), body


@pytest.mark.parametrize(
    "result, status, keeps_code",
    [
        ({"success": False, "code": "CONTENT_UNAVAILABLE",
          "error": "We don't compare this category", "layer": "query_prefilter"}, None, True),
        ({"success": False, "code": "TIMEOUT",
          "error": "Still gathering prices — give it another tap in a moment."}, 503, True),
        ({"success": False, "code": "LLM_UNAVAILABLE", "error": "soft llm copy"}, 503, True),
        ({"success": False, "code": "INSUFFICIENT_DATA",
          "error": "Comparison data was incomplete — choose different products."}, 400, True),
        # Honest limit 2 / must-NOT-touch 3 (probe 1 E6): a CODED exit is a
        # reviewed exit and passes its message through, even a raw-looking one.
        ({"success": False, "code": "WEIRD", "error": _SECRET}, 400, True),
    ],
    ids=["content_unavailable", "timeout", "llm_unavailable", "insufficient_data", "unknown_code_E6"],
)
def test_08_pin_coded_failures_pass_their_message_through(result, status, keeps_code):
    """PIN (green at b63a8368, probe 1 E2-E6): the floor sits BELOW the
    `if code:` branch. Reddens if it is hoisted above it."""
    if status is None:
        assert _surface_comparison_failure(dict(result)) == result
        return
    with pytest.raises(HTTPException) as exc:
        _surface_comparison_failure(dict(result))
    assert exc.value.status_code == status
    assert isinstance(exc.value.detail, dict), exc.value.detail
    assert exc.value.detail["code"] == result["code"]
    assert exc.value.detail["error"] == result["error"]


@pytest.mark.parametrize("bad_error", [["x", _SECRET], {"m": _SECRET}], ids=["list", "dict"])
def test_08b_pin_sync_floor_fails_closed_on_non_str_error(bad_error):
    """PIN (fix round; adversary minor): the sync floor must REDACT a codeless
    non-str `error`, never crash on it. A bare `error_msg not in frozenset`
    raised TypeError (unhashable) on a list/dict. Reddens if the floor's
    isinstance(str) guard is dropped."""
    with pytest.raises(HTTPException) as exc:
        _surface_comparison_failure({"success": False, "error": bad_error})
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": "INTERNAL_ERROR",
        "error": _const("INTERNAL_ERROR_FRIENDLY_MESSAGE"),
    }


def test_16_phone_shape_get_explicit_pair_carries_the_envelope(client):
    """RED at b63a8368 (R3 — the phones' REAL request shape): sync
    GET /api/v1/text/compare?product_a=&product_b= -> explicit_pair; the
    failure is injected at _resolve_pair_category (parse_product_query never
    runs on this path — asserted), through the REAL service and the REAL
    route. Measured today: 400, body.error == raw, code BAD_REQUEST."""
    parse_spy = AsyncMock(side_effect=AssertionError("parser must not run on explicit_pair"))
    with patch.object(scs, "parse_product_query", parse_spy), _inject("explicit_pair") as boom:
        resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
    assert parse_spy.await_count == 0
    assert boom.await_count == 1, "the failure was not injected on the phone path"
    assert resp.status_code == 400, resp.text
    assert not _leaks(resp.text, _SECRET), f"raw exception on the phone path: {resp.text}"
    body = resp.json()
    assert body.get("code") == "INTERNAL_ERROR", body
    assert body.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")
    assert body.get("request_id"), body


# ===========================================================================
# Class C — the SSE wire (route floor + request_id stamp)
# ===========================================================================

def _stream(client, svc, params=None):
    with patch("app.api.text_routes.get_comparison_service", return_value=svc):
        resp = client.get("/api/v1/text/compare/stream", params=params or _PAIR_PARAMS)
    return resp


def test_09_sse_codeless_error_event_gets_the_envelope(client):
    """RED at b63a8368 (probe 2 C): code absent, request_id absent, error raw.
    R2(d): the ROUTE floor supplies code + constant (the service is stubbed
    here), the ROUTE stamp supplies request_id."""
    svc = _stub_stream_service([
        ("status", {"message": "Parsing query...", "progress": 10}),
        ("error", {"success": False, "error": _SECRET, "total_cost": 0.0}),
    ])
    resp = _stream(client, svc)
    assert resp.status_code == 200, resp.text
    assert not _leaks(resp.text, _SECRET), f"raw exception on the SSE wire: {resp.text}"
    events = _sse(resp.text)
    assert [e for e, _ in events] == ["status", "error"], events
    payload = events[-1][1]
    assert payload.get("code") == "INTERNAL_ERROR", payload
    assert payload.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")
    assert payload.get("request_id"), payload


def test_09b_pin_sse_parser_sentence_survives_the_sse_floor(client):
    """PIN (green at b63a8368): R2(d) makes the SSE floor SYMMETRIC with the
    sync allowlist, so the legitimate codeless parser sentence (LITERAL) is
    not rewritten to INTERNAL_ERROR on the stream either."""
    svc = _stub_stream_service([
        ("status", {"message": "Parsing query...", "progress": 10}),
        ("error", {"success": False, "error": _PARSE_COPY, "parsed": {"products": []}}),
    ])
    resp = _stream(client, svc)
    assert resp.status_code == 200, resp.text
    payload = _sse(resp.text)[-1][1]
    assert payload.get("error") == _PARSE_COPY
    assert payload.get("code") != "INTERNAL_ERROR", payload


def test_10_pin_non_error_events_are_not_stamped_or_rewritten(client):
    """PIN (green at b63a8368): the stamp/floor live inside
    `if event_type == "error"`. Reddens if either is hoisted out."""
    complete = {"success": True, "products": [], "metadata": {"total_cost": 0}}
    yielded = [
        ("status", {"message": "Parsing query...", "progress": 10}),
        ("prices", {"product_0": {"amount": 1.0}}),
        ("complete", complete),
    ]
    resp = _stream(client, _stub_stream_service(yielded))
    assert resp.status_code == 200, resp.text
    events = _sse(resp.text)
    assert [e for e, _ in events] == ["status", "prices", "complete"], events
    for (etype, payload), (_, original) in zip(events, yielded, strict=True):
        assert "request_id" not in payload, (etype, payload)
        assert payload == json.loads(json.dumps(original)), (etype, payload)


def test_11_pin_coded_error_event_keeps_caller_request_id_and_code(client):
    """PIN (green at b63a8368): the stamp only fills an ABSENT request_id and
    the floor never rewrites a CODED error event."""
    svc = _stub_stream_service([
        ("error", {"success": False, "error": "We don't compare this category",
                   "code": "CONTENT_UNAVAILABLE", "request_id": "caller-supplied"}),
    ])
    resp = _stream(client, svc)
    assert resp.status_code == 200, resp.text
    payload = _sse(resp.text)[-1][1]
    assert payload.get("request_id") == "caller-supplied"
    assert payload.get("code") == "CONTENT_UNAVAILABLE"
    assert payload.get("error") == "We don't compare this category"


def test_12_pin_non_dict_error_payload_does_not_crash_the_route(client):
    """PIN (green at b63a8368): the stamp/floor need an isinstance(data, dict)
    guard. Reddens if a string payload makes the route raise mid-stream."""
    resp = _stream(client, _stub_stream_service([("error", "boom")]))
    assert resp.status_code == 200
    events = _sse(resp.text)
    assert events and events[-1][0] == "error", resp.text


def test_12b_pin_sse_floor_fails_closed_on_non_str_error(client):
    """PIN (fix round; adversary minor): a codeless error event whose `error`
    is a dict must be REDACTED, not crash the stream. Without the floor's
    isinstance(str) guard the membership test raised TypeError mid-generator:
    HTTP 200 with an EMPTY body (even the preceding status event was lost)."""
    svc = _stub_stream_service([
        ("status", {"message": "Parsing query...", "progress": 10}),
        ("error", {"success": False, "error": {"m": _SECRET}}),
    ])
    resp = _stream(client, svc)
    assert resp.status_code == 200, resp.text
    assert not _leaks(resp.text, _SECRET), f"raw text on the SSE wire: {resp.text}"
    events = _sse(resp.text)
    assert [e for e, _ in events] == ["status", "error"], resp.text
    payload = events[-1][1]
    assert payload.get("code") == "INTERNAL_ERROR", payload
    assert payload.get("error") == _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")
    assert payload.get("request_id"), payload


# ===========================================================================
# Class D — the surfaces the SOURCE fix closes for free
# ===========================================================================

def test_13_quick_route_does_not_leak(client):
    """RED at b63a8368 (probe 2 D). /text/quick keeps its own plain-string
    mapping (must-NOT-touch 7 / Honest limit 3: code stays BAD_REQUEST), so
    only the source fix can close it — the failure is raised inside the REAL
    service (quick builds "A vs B" and takes the parser path)."""
    with _inject("parser") as boom:
        resp = client.post("/api/v1/text/quick",
                           json={"product1": _PAIR[0], "product2": _PAIR[1]})
    assert boom.await_count == 1, "the failure was not injected"
    assert resp.status_code == 400, resp.text
    assert not _leaks(resp.text, _SECRET), f"raw exception on /text/quick: {resp.text}"


def test_14_camera_return_result_arm_carries_the_envelope(client):
    """RED at b63a8368 (probe 4): image_routes returns compare_from_text's
    dict verbatim at HTTP 200 (`return result`), so the raw text ships with
    no code. R3: injected at _resolve_pair_category because the vision path
    SKIPS parse_product_query (asserted: await_count 0)."""
    from app.services.content_safety_service import ContentSafetyService, SafetyResult

    parse_spy = AsyncMock(side_effect=AssertionError("parser must not run on vision"))
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 32
    with patch("app.api.image_routes.identify_products",
               AsyncMock(return_value={"products": [{"brand": "A", "name": "x"},
                                                    {"brand": "B", "name": "y"}],
                                       "cost": 0})), \
         patch.object(ContentSafetyService, "moderate_vision_output",
                      AsyncMock(return_value=SafetyResult(allowed=True))), \
         patch.object(scs, "parse_product_query", parse_spy), \
         _inject("explicit_pair") as boom:
        resp = client.post("/api/v1/image/identify", files=[
            ("images", ("a.jpg", jpeg, "image/jpeg")),
            ("images", ("b.jpg", jpeg, "image/jpeg")),
        ])
    assert parse_spy.await_count == 0
    assert boom.await_count == 1, "the failure was not injected on the vision path"
    assert resp.status_code == 200, resp.text
    assert not _leaks(resp.text, _SECRET), f"raw exception on /image/identify: {resp.text}"
    body = resp.json()
    assert body.get("code") == "INTERNAL_ERROR", body
    assert body.get("success") is False


# ===========================================================================
# Class E — copy fence
# ===========================================================================

def test_15_copy_fence_internal_error_message_has_no_scary_vocab():
    """COPY FENCE (R3). RED at b63a8368 only because the constant does not
    exist yet; green by construction once exported. Same fence
    tests/test_http_400_cap_cut_mapping.py applies to the TIMEOUT copy."""
    here = os.path.dirname(os.path.abspath(__file__))
    policy_path = os.path.join(here, "..", "SmartCompareApp", "src", "i18n", ".copy-policy.json")
    with open(policy_path, encoding="utf-8") as fh:
        forbidden = json.load(fh)["scary_vocab_en"]
    assert forbidden, "copy policy lost its scary_vocab_en list"
    msg = _const("INTERNAL_ERROR_FRIENDLY_MESSAGE")
    hits = [tok for tok in forbidden if tok.lower() in msg.lower()]
    assert not hits, f"INTERNAL_ERROR_FRIENDLY_MESSAGE carries forbidden copy: {hits}"
    assert _SECRET not in msg and "Traceback" not in msg

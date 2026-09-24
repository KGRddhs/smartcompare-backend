"""R-METER retro RED tests for W2-1 (PR #137, paid-route metering).

Spec: the retroactive adversary report for unit "W2-1 paid-route metering
ENABLE_PAID_ROUTE_METERING" (retro_adversary_results.json), narrowed by the
orchestrator's binding rulings for group R-METER:

W2-1b  (camera, adversary defect 1)
    ``POST /api/v1/image/identify`` treats a NON-success ``compare_from_text``
    result as a delivery. ``compare_from_text`` mostly does not RAISE when it
    fails -- it RETURNS ``{success: False, code: TIMEOUT | INSUFFICIENT_DATA |
    LLM_UNAVAILABLE | CONTENT_UNAVAILABLE}`` or the generic
    ``{success: False, error: str(e)}`` (structured_comparison_service.py
    :3331 / :3381 / :3389 / :3905 / :3927). The route never reads
    ``result['success']``, so with ``ENABLE_PAID_ROUTE_METERING`` ON it keeps
    the reserved credit, fires ``record_lifetime_comparison``, writes a history
    row, logs ``log_search(success=True)`` and returns ``action="comparison"``.
    RULING: under ENABLE_PAID_ROUTE_METERING the no-bill half -- refund
    (label ``usage_refund.image.comparison_unsuccessful``), no lifetime bump,
    no history write, ``log_search(success=False)``. The ENVELOPE change
    (success false + the result's code instead of ``action="comparison"``)
    is a result fork for the pre-OTA client, so it sits behind a NEW per-call
    flag ``ENABLE_CAMERA_FAILURE_ENVELOPE`` (default OFF). Both flags OFF:
    today's body byte-for-byte.

W2-1c  (url, adversary defect 2) -- UNFLAGGED, LIVE LEAK
    ``compare_from_urls`` unpacks ``generate_comparison``'s 2-tuple and wraps a
    FAILED verdict (``{'winner_index': 0, 'error': str(e)}``, the except-branch
    at extraction_service.py:2545-2547) as ``success: True, winner_index: 0``
    and ships ``comparison.error = str(e)`` to the client. RULING: after the
    unpack, when the comparison carries an ``error`` key, return
    ``success False, code LLM_UNAVAILABLE`` and a CONSTANT message, never
    str(e). Unflagged; every success path byte-identical. Fable round 3 ruled
    the check to TRUTHINESS (``comparison.get("error")``): the except-branch
    stores a non-empty string whether it is str(e) or W4-9's constant, so it
    composes with W4-9, and a verdict carrying a falsy ``error`` (None / '')
    is delivered exactly as base -- this file never edits extraction_service.

W2-1d  (anon, adversary defect 3)
    RECORD: ``/url/compare`` has NO anonymous gate at all, and the anon credit
    on ``/image/identify`` is debited BEFORE image validation and refunded on
    NO exit (``refund_anon_comparison_credit`` has zero callers). RULING:
    build the anon refund on the SIX numbered non-delivery exits under
    ENABLE_PAID_ROUTE_METERING; the /url/compare anon gate is a written
    follow-up for issue #128 and is NOT built -- pinned here as the recorded
    gap (that pin is EXPECTED to flip the day #128 is extended to it).

Also pinned here (the adversary's "tests that prove nothing" list): the
moderation-exception refund site and the /url/compare exception-branch refund
site were each deletable with the whole W2-1 suite green (mutations M1, M3).

Node classes (each docstring opens with its class; measured by running this
file against a detached worktree of base 1c6f6796 in R-METER fix round 3):

RED         fails at base 1c6f6796 on an ASSERTION about behaviour observed
            through the route (status, body, a call recorded by a stub
            installed with ``raising=False``), never on an ImportError; the
            green made it pass.
BASE PIN    passes at base 1c6f6796 AND at head -- the byte-identity /
            no-regression side. A base-vs-head check must see these green on
            both sides. (``RECORD`` nodes also pass at base: they pin a
            recorded gap that is EXPECTED to flip the day #128 closes it.)
GREEN PIN   needs the new code: it FAILS at base BY DESIGN (it pins behaviour
            the green introduced -- the constant scrub, the envelope helper,
            the flag reader, the exit-7 log/ledger, the URL surfaced-return, the
            both-flags-ON deploy state). A base run reading these as failures
            is NOT a regression. Measured at base: every GREEN PIN node fails,
            every BASE PIN / RECORD node passes.
"""
from __future__ import annotations

import asyncio
import copy
import ipaddress
import socket

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes, url_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.services import (
    content_safety_service,
    extraction_service,
    feedback_service,
    structured_comparison_service,
    url_extraction_service,
    usage_service,
)

METER = "ENABLE_PAID_ROUTE_METERING"
ENVELOPE = "ENABLE_CAMERA_FAILURE_ENVELOPE"
ANON_GATE = "ENABLE_ANON_USAGE_GATE"

JPEG = b"\xff\xd8" + b"\x00" * 64
FP = "a" * 64  # matches ^[a-f0-9]{64}$
LEAK = "Incorrect API key provided: sk-proj-RETROPROBE1234"
LEAK_MARK = "sk-proj-RETROPROBE"

# The exact shape extraction_service.generate_comparison returns on success.
REAL_VERDICT = (
    {
        "winner_index": 1,
        "recommendation": "The second one, for the price.",
        "key_differences": ["price", "size"],
    },
    {"prompt_tokens": 11, "completion_tokens": 22},
)

# Words the no-scary-copy contract (CLAUDE.md "Copy contract") forbids.
FORBIDDEN_COPY = ("couldn't", "try again", "failed to")


# ---------------------------------------------------------------------------
# autouse: zero network + clean flag state
# ---------------------------------------------------------------------------
def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    if host in ("localhost", "testserver", "testclient", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback connect and DNS lookup; FAIL the test on any
    attempt (the attempt is also raised, so nothing reaches the wire)."""
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _addr_ok(address) -> bool:
        if isinstance(address, (str, bytes)):  # AF_UNIX path
            return True
        if isinstance(address, tuple) and address:
            return _is_loopback_host(address[0])
        return False

    def guarded_connect(self, address):
        if not _addr_ok(address):
            attempts.append(("connect", repr(address)))
            raise OSError(f"retro W2-1 zero-network guard: connect {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        if not _addr_ok(address):
            attempts.append(("connect_ex", repr(address)))
            raise OSError(f"retro W2-1 zero-network guard: connect_ex {address!r}")
        return real_connect_ex(self, address)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise socket.gaierror(f"retro W2-1 zero-network guard: {host!r}")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    yield attempts
    assert not attempts, f"test attempted network access: {attempts!r}"


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in (METER, ENVELOPE, ANON_GATE, "ENABLE_LLM_PREFLIGHT_BREAKER",
                 "ENABLE_STRICT_OPTIONAL_AUTH"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {
        "id": f"retro-w2-1-{request.node.name}"[:120],
        "email": "retro-w2-1@example.test",
        "access_token": "retro-w2-1-token",
    }
    app.dependency_overrides[get_optional_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def anonymous():
    app.dependency_overrides[get_optional_user] = lambda: None
    try:
        yield None
    finally:
        app.dependency_overrides.pop(get_optional_user, None)


# ---------------------------------------------------------------------------
# recorders
# ---------------------------------------------------------------------------
def _done(value=None):
    async def _r():
        return value
    return _r()


class Ledger:
    """Records every metering side effect at CALL time (the production sites
    are ``fire_and_forget(coro(...))``, so the coroutine is BUILT synchronously
    even if the task never runs before TestClient returns)."""

    def __init__(self) -> None:
        self.consumes: list = []
        self.refunds: list = []        # authed refund_comparison_credit ids
        self.refund_keys: list = []
        self.anon_checks: list = []    # check_anon_usage_allowed fps
        self.anon_refunds: list = []   # fp, however the route spells the refund
        self.anon_refund_keys: list = []  # consumed_keys the anon refund received
        self.lifetime: list = []
        self.history: list = []
        self.log_success: list = []
        self.log_errors: list = []     # log_search error_message values
        self.labels: list = []

    # authed gate
    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)
        return _done({
            "allowed": True, "reason": None, "tier": "free", "consumed": True,
            "consumed_keys": {"daily": f"d:{user_id}", "monthly": f"m:{user_id}"},
            "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
        })

    def refund(self, counter_id, consumed_keys=None, *_a, **_kw):
        if isinstance(counter_id, str) and counter_id.startswith("anon:"):
            self.anon_refunds.append(counter_id[len("anon:"):])
        else:
            self.refunds.append(counter_id)
        self.refund_keys.append(consumed_keys)
        return _done()

    # anon gate
    def anon_check(self, fp, *_a, **_kw):
        self.anon_checks.append(fp)
        return _done({
            "allowed": True, "reason": None, "tier": "free", "consumed": True,
            "consumed_keys": {"daily": f"d:anon:{fp}", "monthly": f"m:anon:{fp}"},
            "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 0},
        })

    def anon_refund(self, fp, consumed_keys=None, *_a, **_kw):
        self.anon_refunds.append(fp)
        self.anon_refund_keys.append(consumed_keys)
        return _done()

    def record_lifetime(self, user_id, access_token="", *_a, **_kw):
        self.lifetime.append(user_id)
        return _done()

    def save(self, **kw):
        self.history.append(kw.get("input_type"))
        return _done()

    def log_search(self, **kw):
        self.log_success.append(kw.get("success"))
        self.log_errors.append(kw.get("error_message"))
        return _done()


def _install(monkeypatch, ledger: Ledger, route_module) -> None:
    for mod in (usage_service, route_module):
        monkeypatch.setattr(mod, "consume_comparison_credit", ledger.consume, raising=False)
        monkeypatch.setattr(mod, "refund_comparison_credit", ledger.refund, raising=False)
        monkeypatch.setattr(mod, "check_anon_usage_allowed", ledger.anon_check, raising=False)
        monkeypatch.setattr(mod, "refund_anon_comparison_credit", ledger.anon_refund,
                            raising=False)
        monkeypatch.setattr(mod, "record_lifetime_comparison", ledger.record_lifetime,
                            raising=False)
    for mod in (feedback_service, route_module):
        monkeypatch.setattr(mod, "save_comparison_and_track_cohort", ledger.save,
                            raising=False)

    real_ff = route_module.fire_and_forget

    def _ff(coro, label):
        ledger.labels.append(label)
        return real_ff(coro, label=label)

    monkeypatch.setattr(route_module, "fire_and_forget", _ff)


# ---------------------------------------------------------------------------
# camera harness
# ---------------------------------------------------------------------------
class _Safety:
    def __init__(self, allowed=True, raises=False):
        self._allowed = allowed
        self._raises = raises

    async def moderate_vision_output(self, _extracted):
        if self._raises:
            raise RuntimeError("retro W2-1 probe: moderation API down")
        if self._allowed:
            return content_safety_service.SafetyResult(allowed=True)
        return content_safety_service.SafetyResult(
            allowed=False, reason="violence", blocklist_match="probe")


def _vision(n: int):
    return {"products": [{"brand": f"B{i}", "name": f"N{i}"} for i in range(n)],
            "cost": 0.003}


DELIVERED = {
    "success": True,
    "products": [{"brand": "A", "name": "one"}, {"brand": "B", "name": "two"}],
    "metadata": {"total_cost": 0.01},
}


def _stub_camera(monkeypatch, ledger: Ledger, *, vision=None, vision_raises=False,
                 moderation_allowed=True, moderation_raises=False,
                 compare_result=None, compare_raises=False):
    async def _identify(_images):
        if vision_raises:
            raise RuntimeError("retro W2-1 probe: vision unavailable")
        return vision

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    monkeypatch.setattr(content_safety_service, "get_content_safety_service",
                        lambda: _Safety(moderation_allowed, moderation_raises))
    from app.services import audit_service
    monkeypatch.setattr(audit_service, "log_content_blocked", lambda **_kw: _done())

    result_template = DELIVERED if compare_result is None else compare_result

    class _Service:
        async def compare_from_text(self, *_a, **_kw):
            if compare_raises:
                raise RuntimeError("retro W2-1 probe: comparison unavailable")
            import copy
            return copy.deepcopy(result_template)

    monkeypatch.setattr(image_routes, "StructuredComparisonService", _Service)
    monkeypatch.setattr(image_routes, "log_search", ledger.log_search)
    _install(monkeypatch, ledger, image_routes)


def _post_identify(client, fp=None, n_images=2, content=JPEG, request_id=None):
    files = [("images", (f"p{i}.jpg", content, "image/jpeg")) for i in range(n_images)]
    headers = {"X-Device-Fingerprint": fp} if fp else {}
    if request_id:
        headers["X-Request-ID"] = request_id
    return client.post("/api/v1/image/identify", files=files, headers=headers)


# The {daily, monthly} keys Ledger.anon_check reports as debited for FP; the
# anon refund must hand exactly these back (M18 usage symmetry: a refund that
# recomputes its keys can land on the wrong UTC day's window near midnight).
ANON_GATE_KEYS = {"daily": f"d:anon:{FP}", "monthly": f"m:anon:{FP}"}


# The failure shapes compare_from_text actually RETURNS (not raises).
UNSUCCESSFUL_RESULTS = [
    ("TIMEOUT", {"success": False, "code": "TIMEOUT",
                 "error": structured_comparison_service.TIMEOUT_FRIENDLY_MESSAGE,
                 "elapsed_seconds": 30.0, "total_cost": 0.0}),
    ("INSUFFICIENT_DATA", {"success": False, "code": "INSUFFICIENT_DATA",
                           "error": "Comparison data was incomplete — choose different products.",
                           "elapsed_seconds": 30.0, "total_cost": 0.0, "api_calls": 3}),
    ("LLM_UNAVAILABLE", {"success": False, "code": "LLM_UNAVAILABLE",
                         "error": structured_comparison_service.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
                         "elapsed_seconds": 0.0, "total_cost": 0.0, "api_calls": 0}),
    ("CONTENT_UNAVAILABLE", {"success": False, "code": "CONTENT_UNAVAILABLE",
                             "error": "We don't compare this category",
                             "layer": "moderation_api"}),
    # structured_comparison_service.py:3927 -- the generic except branch.
    ("generic_str_e", {"success": False, "error": LEAK, "total_cost": 0.0}),
]
_UNSUCCESSFUL_IDS = [row[0] for row in UNSUCCESSFUL_RESULTS]


# ===========================================================================
# W2-1b -- camera: an UNSUCCESSFUL compare_from_text result is not a delivery
# ===========================================================================
@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS, ids=_UNSUCCESSFUL_IDS)
def test_camera_unsuccessful_result_refunds_and_does_not_bill(
    monkeypatch, client, authed, case, result
):
    """RED (W2-1b, metering half): with ENABLE_PAID_ROUTE_METERING ON and the
    envelope flag OFF, a compare_from_text result with success False must
    refund the gate credit exactly once under the named label, fire NO
    record_lifetime_comparison, write NO history row, and log the search as a
    failure. Today: refunds == [], lifetime == [uid], history == ['camera'],
    log_search success=True (adversary probe P1)."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:300]
    assert ledger.consumes == [authed["id"]], ledger.consumes
    assert ledger.refunds == [authed["id"]], (
        f"[{case}] an unsuccessful comparison must give the reserved credit back "
        f"exactly once; refunds={ledger.refunds!r} lifetime={ledger.lifetime!r}"
    )
    assert "usage_refund.image.comparison_unsuccessful" in ledger.labels, (
        f"[{case}] refund must fire under the ruled label; labels={ledger.labels!r}"
    )
    assert ledger.lifetime == [], (
        f"[{case}] no lifetime-free credit may be burned for a failed comparison; "
        f"got {ledger.lifetime!r}"
    )
    assert ledger.history == [], (
        f"[{case}] a failed comparison must not be written to history; "
        f"got {ledger.history!r}"
    )
    assert ledger.log_success == [False], (
        f"[{case}] log_search must record the failure; got {ledger.log_success!r}"
    )


@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS, ids=_UNSUCCESSFUL_IDS)
@pytest.mark.parametrize("meter_on", [False, True], ids=["meter_off", "meter_on"])
def test_camera_failure_envelope_flag_returns_failure_not_comparison(
    monkeypatch, client, authed, case, result, meter_on
):
    """RED (W2-1b, envelope half, ENABLE_CAMERA_FAILURE_ENVELOPE ON): the body
    must say what happened -- success False, the result's own code, and NOT
    action='comparison'. The generic branch carries str(e) in `error`
    (structured_comparison_service.py:3927); the envelope must never forward
    it (M13-26). The envelope is independent of the metering flag."""
    monkeypatch.setenv(ENVELOPE, "true")
    if meter_on:
        monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    rid = f"retro-w2-1-rid-{case}"
    resp = _post_identify(client, request_id=rid)
    body = resp.json()

    assert body.get("action") != "comparison", (
        f"[{case}] envelope ON: an unsuccessful comparison must not be served as "
        f"action='comparison'; got status={resp.status_code} body={resp.text[:300]}"
    )
    assert body.get("success") is False, f"[{case}] body={body!r}"
    if result.get("code"):
        assert body.get("code") == result["code"], (
            f"[{case}] envelope must carry the result's code; body={body!r}"
        )
    else:
        # R-METER fix: the documented code-less fallback is INTERNAL_ERROR,
        # exit 6's own code -- not merely "some non-empty string".
        assert body.get("code") == "INTERNAL_ERROR", (
            f"[{case}] a code-less failure takes the INTERNAL_ERROR code; body={body!r}"
        )
    # R-METER fix: `layer` is carried exactly when the result has one (the
    # client branches on it for CONTENT_UNAVAILABLE) and never invented.
    if result.get("layer"):
        assert body.get("layer") == result["layer"], (
            f"[{case}] envelope must carry the result's layer; body={body!r}"
        )
    else:
        assert "layer" not in body, f"[{case}] invented a layer; body={body!r}"
    # R-METER fix: the envelope carries the request's own id (the unified
    # error envelope's request_id), not a placeholder.
    assert body.get("request_id") == rid, f"[{case}] body={body!r}"
    assert LEAK_MARK not in resp.text, (
        f"[{case}] str(e) leaked into the camera failure envelope: {resp.text[:300]}"
    )


def test_pin_camera_flags_off_unsuccessful_result_body_and_effects_unchanged(
    monkeypatch, client, authed
):
    """BASE PIN (passes today): BOTH flags OFF, an unsuccessful result is served
    exactly as today -- the result dict plus the camera metadata injection and
    action='comparison', a history write and a success=True search log, and no
    metering. The pre-OTA client depends on this shape (ruling: the envelope
    change is a result fork, so it is flagged)."""
    ledger = Ledger()
    result = dict(UNSUCCESSFUL_RESULTS[0][1])  # TIMEOUT
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    resp = _post_identify(client)

    assert resp.status_code == 200
    expected = dict(result)
    expected["metadata"] = {
        "input_method": "camera",
        "vision_cost": 0.003,
        "identified_products": _vision(2)["products"],
    }
    expected["action"] = "comparison"
    assert resp.json() == expected
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.lifetime == []
    assert ledger.history == ["camera"]
    assert ledger.log_success == [True]


def test_pin_camera_meter_on_envelope_off_unsuccessful_body_unchanged(
    monkeypatch, client, authed
):
    """BASE PIN (passes today, must keep passing): metering ON alone moves the
    ACCOUNTING only -- the body an unsuccessful result produces stays today's
    action='comparison' shape until ENABLE_CAMERA_FAILURE_ENVELOPE is flipped."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    result = dict(UNSUCCESSFUL_RESULTS[2][1])  # LLM_UNAVAILABLE
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    body = _post_identify(client).json()

    assert body.get("action") == "comparison"
    assert body.get("success") is False
    assert body.get("code") == "LLM_UNAVAILABLE"
    assert body["metadata"]["input_method"] == "camera"


@pytest.mark.parametrize("envelope_on", [False, True], ids=["env_off", "env_on"])
def test_pin_camera_delivery_keeps_credit_and_body(monkeypatch, client, authed, envelope_on):
    """BASE PIN (passes today): a successful comparison under metering ON keeps the
    credit (no refund), bumps lifetime once, writes history once, logs
    success, and returns today's delivery body -- with or without the envelope
    flag."""
    monkeypatch.setenv(METER, "true")
    if envelope_on:
        monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2))

    resp = _post_identify(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "comparison" and body["success"] is True
    assert body["metadata"] == {
        "total_cost": round(0.01 + 0.003, 6),
        "input_method": "camera",
        "vision_cost": 0.003,
        "identified_products": _vision(2)["products"],
    }
    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == []
    assert ledger.lifetime == [authed["id"]]
    assert ledger.history == ["camera"]
    assert ledger.log_success == [True]


def test_pin_camera_partial_success_is_a_delivery(monkeypatch, client, authed):
    """BASE PIN (passes today): a best-available PARTIAL (success True,
    metadata.partial True) is a delivery -- the credit is kept."""
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    partial = {"success": True, "products": DELIVERED["products"],
               "metadata": {"total_cost": 0.0, "partial": True}}
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=partial)

    body = _post_identify(client).json()

    assert body["action"] == "comparison" and body["metadata"]["partial"] is True
    assert ledger.refunds == [] and ledger.lifetime == [authed["id"]]


def test_pin_camera_moderation_exception_refunds_once(monkeypatch, client, authed):
    """BASE PIN (passes today; kills adversary mutation M1): moderation raising
    after the gate refunds the reserved credit exactly once before re-raising."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), moderation_raises=True)

    resp = _post_identify(client)

    assert resp.status_code == 500
    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == [authed["id"]], ledger.refunds
    assert "usage_refund.image.moderation_exception" in ledger.labels


# ===========================================================================
# W2-1c -- url: a FAILED verdict is not a delivered comparison (UNFLAGGED)
# ===========================================================================
def _stub_url(monkeypatch, ledger: Ledger, *, verdict=None, get_client_raises=None,
              extract_ok=True, compare_raises=False):
    async def _extract(url):
        if not extract_ok:
            return {"success": False, "error": "retro W2-1 probe: extraction refused"}
        tag = url.rsplit("/", 1)[-1]
        return {"success": True, "product": {
            "brand": "Probe", "name": tag, "category": "electronics",
            "search_query": f"Probe {tag}", "price": {"amount": 1.0, "currency": "BHD"},
        }}

    monkeypatch.setattr(url_extraction_service, "extract_from_url", _extract)

    async def _allow(_url):
        return True

    monkeypatch.setattr(url_routes, "_validate_url_offloop_or_sync", _allow)

    async def _resolve(products, selected_category, parser_path=False):
        return "electronics", False, None

    monkeypatch.setattr(structured_comparison_service, "_resolve_pair_category", _resolve)

    if get_client_raises is not None:
        # Drive the REAL generate_comparison into its except-branch offline.
        def _boom():
            raise RuntimeError(get_client_raises)

        monkeypatch.setattr(extraction_service, "get_client", _boom)
    else:
        async def _generate(*_a, **_kw):
            # R-METER round 4 (ruling 2): the default hands the code a FRESH deep
            # copy, so an in-place edit can never reach the module constant the
            # pins build their expectations from.
            return verdict if verdict is not None else copy.deepcopy(REAL_VERDICT)

        monkeypatch.setattr(extraction_service, "generate_comparison", _generate)

    if compare_raises:
        async def _raise(*_a, **_kw):
            raise RuntimeError("retro W2-1 probe: compare_from_urls raised")

        monkeypatch.setattr(url_routes, "compare_from_urls", _raise)

    _install(monkeypatch, ledger, url_routes)


URL1 = "https://example.test/alpha"
URL2 = "https://example.test/beta"


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("error_text", [LEAK, "Expecting value: line 1 column 1 (char 0)"],
                         ids=["openai_key_error", "json_decode_error"])
def test_compare_from_urls_failed_verdict_is_llm_unavailable(monkeypatch, error_text):
    """RED (W2-1c, service level): a verdict dict carrying `error` must become
    success False / code LLM_UNAVAILABLE with a CONSTANT, no-scary message and
    no fabricated winner. Today: success True, winner_index 0, and
    comparison.error == str(e) verbatim."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger,
              verdict=({"winner_index": 0, "error": error_text},
                       {"prompt_tokens": 0, "completion_tokens": 0}))

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))

    assert result.get("success") is False, (
        f"a failed verdict must not be delivered; got {result!r}"
    )
    assert result.get("code") == "LLM_UNAVAILABLE", result
    assert error_text not in repr(result), f"str(e) leaked: {result!r}"
    assert "winner_index" not in result, f"fabricated winner: {result!r}"
    msg = result.get("error")
    assert isinstance(msg, str) and msg, result
    assert not any(w in msg.lower() for w in FORBIDDEN_COPY), msg


def test_compare_from_urls_failed_verdict_message_is_constant(monkeypatch):
    """RED (W2-1c): the user-facing message must not depend on the exception
    text -- two different failures produce the identical error string."""
    msgs = []
    for text in ("upstream 429 quota exceeded for org-XYZ", LEAK):
        ledger = Ledger()
        _stub_url(monkeypatch, ledger,
                  verdict=({"winner_index": 0, "error": text},
                           {"prompt_tokens": 0, "completion_tokens": 0}))
        result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))
        assert result.get("success") is False, result
        msgs.append(result.get("error"))
    assert msgs[0] == msgs[1], f"message varies with str(e): {msgs!r}"


def _FULL_VERDICT_WITH(marker):
    """A complete, valid verdict 2-tuple whose parsed dict carries `error: marker`."""
    return (
        {"winner_index": 1, "recommendation": "The second one, for the price.",
         "key_differences": ["price", "size"], "error": marker},
        {"prompt_tokens": 1, "completion_tokens": 1},
    )


def _delivered_url_result(verdict: dict) -> dict:
    """compare_from_urls' base-1c6f6796 delivery dict for the _stub_url pair."""
    products = [
        {"brand": "Probe", "name": tag, "category": "electronics",
         "search_query": f"Probe {tag}", "price": {"amount": 1.0, "currency": "BHD"}}
        for tag in ("alpha", "beta")
    ]
    return {
        "success": True,
        "products": products,
        "comparison": verdict,
        "winner_index": verdict.get("winner_index", 0),
        "recommendation": verdict.get("recommendation", ""),
        "key_differences": verdict.get("key_differences", []),
        "category_used": "electronics",
        "source_urls": [URL1, URL2],
    }


@pytest.mark.parametrize("marker", [None, ""], ids=["error_none", "error_empty"])
def test_pin_compare_from_urls_falsy_error_verdict_delivered_as_base(monkeypatch, marker):
    """BASE PIN (Fable round-3 ruling 2, TRUTHINESS): a valid verdict JSON that
    carries a FALSY `error` (None or '') is DELIVERED exactly as at base
    1c6f6796 -- the full return dict, key for key, the falsy marker kept inside
    `comparison`. Kills the PRESENCE mutant (`if "error" in comparison:`) and
    the `is not None` mutant (on the '' row).

    R-METER round 4 (ruling 2): the expectation is built from a DEEP COPY taken
    BEFORE the call, never from the verdict object the stub hands the code, so
    an in-place edit of the verdict (pop / clear / rewrite of the falsy
    `error`, a fabricated winner) is visible here."""
    ledger = Ledger()
    verdict = _FULL_VERDICT_WITH(marker)
    expected = _delivered_url_result(copy.deepcopy(verdict[0]))
    assert expected["comparison"]["error"] == marker
    _stub_url(monkeypatch, ledger, verdict=verdict)

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))

    assert result == expected, result
    assert list(result) == list(expected)
    assert list(result["comparison"]) == list(expected["comparison"])


@pytest.mark.parametrize("marker", [None, ""], ids=["error_none", "error_empty"])
@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_pin_url_compare_falsy_error_verdict_is_200_delivery(monkeypatch, client, verb, marker):
    """BASE PIN (ruling 2, route level, metering OFF = prod today): the same
    falsy-`error` verdict is a 200 success whose body is base's delivery dict
    (the route returns compare_from_urls' dict as-is), with no metering.
    The expectation is a deep copy taken before the request (round-4 ruling 2)."""
    ledger = Ledger()
    verdict = _FULL_VERDICT_WITH(marker)
    expected = _delivered_url_result(copy.deepcopy(verdict[0]))
    _stub_url(monkeypatch, ledger, verdict=verdict)

    if verb == "POST":
        resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": URL1, "url2": URL2})

    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == expected, resp.json()
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.history == []


@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_url_compare_llm_failure_is_not_delivered_flag_off(monkeypatch, client, verb):
    """RED (W2-1c, route level, metering OFF = prod today): the REAL
    generate_comparison's except-branch (get_client raising with a key-bearing
    message) must not come back as a 200 success with a made-up winner and
    str(e) in the body. Today: 200, success True, winner_index 0, the probe key
    string verbatim (adversary probe P2)."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, get_client_raises=LEAK)

    if verb == "POST":
        resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": URL1, "url2": URL2})

    assert LEAK_MARK not in resp.text, (
        f"{verb} /url/compare leaked str(e) to the client: {resp.text[:300]}"
    )
    body = resp.json()
    assert resp.status_code != 200 or body.get("success") is False, (
        f"{verb}: a failed verdict must not be a 200 success; "
        f"got {resp.status_code} {resp.text[:300]}"
    )
    assert "winner_index" not in body, f"{verb}: fabricated winner {body!r}"
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.history == []


def test_url_compare_llm_failure_refunds_and_skips_history_flag_on(
    monkeypatch, client, authed
):
    """RED (W2-1c, metering ON): the same failed verdict must take the
    existing non-success exit -- one consume, one refund, no lifetime bump, no
    history row. Today: refunds == [], lifetime == [uid], history == ['url']
    (adversary probe P3)."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, get_client_raises=LEAK)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == [authed["id"]], (
        f"failed verdict must refund; refunds={ledger.refunds!r} "
        f"status={resp.status_code}"
    )
    assert ledger.lifetime == [], ledger.lifetime
    assert ledger.history == [], ledger.history
    assert LEAK_MARK not in resp.text


def test_pin_compare_from_urls_success_is_byte_identical(monkeypatch):
    """BASE PIN (passes today): a verdict with no `error` key is delivered exactly
    as today -- the full return dict, key for key. The verdict is written out
    as a LITERAL (round-4 ruling 2): never compared against the object the
    stub hands the code."""
    ledger = Ledger()
    expected_verdict = {
        "winner_index": 1,
        "recommendation": "The second one, for the price.",
        "key_differences": ["price", "size"],
    }
    assert expected_verdict == REAL_VERDICT[0]
    _stub_url(monkeypatch, ledger)

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))

    products = [
        {"brand": "Probe", "name": tag, "category": "electronics",
         "search_query": f"Probe {tag}", "price": {"amount": 1.0, "currency": "BHD"}}
        for tag in ("alpha", "beta")
    ]
    assert result == {
        "success": True,
        "products": products,
        "comparison": expected_verdict,
        "winner_index": 1,
        "recommendation": "The second one, for the price.",
        "key_differences": ["price", "size"],
        "category_used": "electronics",
        "source_urls": [URL1, URL2],
    }
    assert list(result) == ["success", "products", "comparison", "winner_index",
                            "recommendation", "key_differences", "category_used",
                            "source_urls"]


def test_pin_compare_from_urls_sparse_verdict_defaults_unchanged(monkeypatch):
    """BASE PIN (passes today): a verdict WITHOUT an error key but missing the
    optional fields keeps today's defaults (winner 0, '' and [])."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, verdict=({"summary": "ok"}, {"prompt_tokens": 1,
                                                                "completion_tokens": 1}))

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))

    assert result["success"] is True
    assert result["comparison"] == {"summary": "ok"}
    assert (result["winner_index"], result["recommendation"],
            result["key_differences"]) == (0, "", [])


def test_pin_compare_from_urls_extraction_failure_shape_unchanged(monkeypatch):
    """BASE PIN (passes today): the <2-products exit keeps its exact shape."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, extract_ok=False)

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))

    assert result == {
        "success": False,
        "error": "Could not extract both products",
        "details": ["URL 1: retro W2-1 probe: extraction refused",
                    "URL 2: retro W2-1 probe: extraction refused"],
    }


@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_pin_url_compare_success_route_body_flag_off(monkeypatch, client, verb):
    """BASE PIN (passes today): flag OFF, a real verdict is a 200 success with the
    parsed verdict dict and no metering. The expected verdict is a deep copy
    taken BEFORE the request (round-4 ruling 2)."""
    ledger = Ledger()
    expected_verdict = copy.deepcopy(REAL_VERDICT[0])
    _stub_url(monkeypatch, ledger)

    if verb == "POST":
        resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": URL1, "url2": URL2})

    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["success"] is True and body["winner_index"] == 1
    assert body["comparison"] == expected_verdict
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.history == []


def test_pin_url_compare_success_flag_on_keeps_credit(monkeypatch, client, authed):
    """BASE PIN (passes today): metering ON, a real verdict keeps the credit, bumps
    lifetime and writes one url history row."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_url(monkeypatch, ledger)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    assert resp.status_code == 200
    assert ledger.consumes == [authed["id"]] and ledger.refunds == []
    assert ledger.lifetime == [authed["id"]] and ledger.history == ["url"]


def test_pin_url_compare_exception_branch_refunds_once(monkeypatch, client, authed):
    """BASE PIN (passes today; kills adversary mutation M3): compare_from_urls
    raising refunds the reserved credit exactly once."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, compare_raises=True)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    assert resp.status_code == 500
    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == [authed["id"]], ledger.refunds
    assert "usage_refund.url.compare.exception" in ledger.labels


def test_pin_url_compare_extraction_failure_400_detail_unchanged(monkeypatch, client):
    """BASE PIN (passes today): the <2-products exit is a 400 carrying the constant
    'Could not extract both products', never the per-URL details."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, extract_ok=False)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    assert resp.status_code == 400
    assert resp.json().get("error") == "Could not extract both products"
    assert "extraction refused" not in resp.text


# ===========================================================================
# W2-1d -- anon: the six camera exits refund the anon credit (under metering)
# ===========================================================================
CAMERA_SIX_EXITS = [
    ("vision_raised_500", dict(vision_raises=True), 500),
    ("vision_parse_error", dict(vision={"error": "bad json", "cost": 0.003}), 200),
    ("moderation_blocked", dict(vision=_vision(2), moderation_allowed=False), 200),
    ("zero_products", dict(vision=_vision(0)), 200),
    ("one_product", dict(vision=_vision(1)), 200),
    ("comparison_raised", dict(vision=_vision(2), compare_raises=True), 200),
]
_SIX_IDS = [row[0] for row in CAMERA_SIX_EXITS]


@pytest.mark.parametrize("exit_id,stub_kwargs,status", CAMERA_SIX_EXITS, ids=_SIX_IDS)
def test_camera_anon_non_delivery_exit_refunds_anon_credit_once(
    monkeypatch, client, anonymous, exit_id, stub_kwargs, status
):
    """RED (W2-1d): ENABLE_ANON_USAGE_GATE + ENABLE_PAID_ROUTE_METERING ON, an
    anonymous caller with a valid fingerprint -- each of the six numbered
    non-delivery exits must refund the anon credit the gate debited, exactly
    once (refund_anon_comparison_credit has ZERO callers today)."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, **stub_kwargs)

    resp = _post_identify(client, fp=FP)

    assert resp.status_code == status, resp.text[:300]
    assert ledger.anon_checks == [FP], ledger.anon_checks
    assert ledger.anon_refunds == [FP], (
        f"exit {exit_id}: the anon credit must come back exactly once; "
        f"anon_refunds={ledger.anon_refunds!r}"
    )
    assert ledger.anon_refund_keys == [ANON_GATE_KEYS], (
        f"exit {exit_id}: the anon refund must return the gate's own consumed_keys; "
        f"got {ledger.anon_refund_keys!r}"
    )
    assert ledger.consumes == [] and ledger.refunds == [], (
        "an anonymous caller must never touch the authed ledger"
    )


@pytest.mark.parametrize("exit_id,stub_kwargs,status", CAMERA_SIX_EXITS, ids=_SIX_IDS)
def test_pin_camera_anon_exits_do_not_refund_with_metering_off(
    monkeypatch, client, anonymous, exit_id, stub_kwargs, status
):
    """BASE PIN (passes today): metering OFF keeps today's anon accounting --
    the gate debits, no exit refunds. The refund lives INSIDE the metering
    flag per the ruling."""
    monkeypatch.setenv(ANON_GATE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, **stub_kwargs)

    resp = _post_identify(client, fp=FP)

    assert resp.status_code == status
    assert ledger.anon_checks == [FP]
    assert ledger.anon_refunds == [], ledger.anon_refunds


def test_pin_camera_anon_delivery_never_refunds(monkeypatch, client, anonymous):
    """BASE PIN (passes today): the anon delivery exit keeps the anon credit."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2))

    resp = _post_identify(client, fp=FP)

    assert resp.status_code == 200 and resp.json()["action"] == "comparison"
    assert ledger.anon_checks == [FP] and ledger.anon_refunds == []


def test_record_camera_anon_credit_debited_before_image_validation(
    monkeypatch, client, anonymous
):
    """RECORD / BASE PIN (passes today): the anon gate (image_routes.py:94-108) runs
    BEFORE the five image-validation 400s, so an empty upload still debits the
    anon credit. The ruling scopes the anon refund to the six numbered exits
    only, so this node asserts the debit ordering and deliberately does NOT
    assert on a refund for the validation 400 (an open item for #128)."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2))

    resp = _post_identify(client, fp=FP, content=b"")

    assert resp.status_code == 400
    assert ledger.anon_checks == [FP], (
        "the anon credit is debited before validation"
    )


def test_record_url_compare_has_no_anonymous_gate(monkeypatch, client, anonymous):
    """RECORD / BASE PIN (passes today): with ENABLE_ANON_USAGE_GATE and
    ENABLE_PAID_ROUTE_METERING both ON, an anonymous caller with a valid
    fingerprint gets an UNMETERED /url/compare -- no anon check, no consume.
    Ruling: the /url/compare anon gate is a written follow-up for issue #128
    and is NOT built in R-METER. This pin is EXPECTED to flip (and must then
    be rewritten) the day #128 is extended to /url/compare."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_url(monkeypatch, ledger)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2},
                       headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200
    assert ledger.anon_checks == [] and ledger.consumes == []
    assert ledger.anon_refunds == [] and ledger.refunds == []


# ===========================================================================
# GREEN-phase pins (R-METER green, Fable red-gate rulings 1-3)
# ===========================================================================
_GENERIC = dict(UNSUCCESSFUL_RESULTS[4][1])  # the code-less str(e) branch


@pytest.mark.parametrize("meter_on", [False, True], ids=["meter_off", "meter_on"])
@pytest.mark.parametrize("envelope_on", [False, True], ids=["env_off", "env_on"])
def test_camera_str_e_probe_never_reaches_body_in_any_flag_state(
    monkeypatch, client, authed, meter_on, envelope_on
):
    """GREEN PIN (ruling 1, UNFLAGGED): the code-less generic failure's str(e) --
    measured carrying 'Incorrect API key provided: sk-proj-...' -- never
    reaches the camera response body, in ANY of the four flag states."""
    if meter_on:
        monkeypatch.setenv(METER, "true")
    if envelope_on:
        monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=_GENERIC)

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:300]
    assert LEAK_MARK not in resp.text, resp.text[:300]
    assert "Incorrect API key" not in resp.text, resp.text[:300]
    assert resp.json().get("error") == image_routes.CAMERA_UNSUCCESSFUL_CONSTANT_ERROR


def test_pin_camera_flags_off_generic_failure_body_identical_except_error(
    monkeypatch, client, authed
):
    """GREEN PIN (ruling 1): both flags OFF, the code-less failure body is today's
    body key-for-key (result + camera metadata + action='comparison'), with
    exactly ONE value relaxed: `error` is the constant instead of str(e)."""
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=_GENERIC)

    body = _post_identify(client).json()

    expected = dict(_GENERIC)
    expected["error"] = "comparison unavailable"
    expected["metadata"] = {
        "input_method": "camera",
        "vision_cost": 0.003,
        "identified_products": _vision(2)["products"],
    }
    expected["action"] = "comparison"
    assert body == expected
    assert list(body) == list(expected)
    assert ledger.history == ["camera"] and ledger.log_success == [True]


@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS[:4], ids=_UNSUCCESSFUL_IDS[:4])
def test_pin_camera_coded_failure_error_value_untouched_flags_off(
    monkeypatch, client, authed, case, result
):
    """BASE PIN: the unflagged scrub is scoped to CODE-LESS results -- a coded
    result's own (constant, friendly) `error` passes through unchanged."""
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    body = _post_identify(client).json()

    assert body["error"] == result["error"]
    assert body["code"] == result["code"] and body["action"] == "comparison"


def test_pin_camera_envelope_shape(monkeypatch, client, authed):
    """GREEN PIN: envelope ON -> exit 6's `comparison_failed` shape carrying the
    result's code and its friendly error; products + vision_cost kept so the
    client's fall-back-to-text branch works."""
    monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    result = dict(UNSUCCESSFUL_RESULTS[0][1])  # TIMEOUT
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=result)

    body = _post_identify(client, request_id="retro-w2-1-envelope-shape").json()

    assert body["success"] is False
    assert body["action"] == "comparison_failed"
    assert body["code"] == "TIMEOUT"
    assert body["error"] == result["error"]
    assert body["products"] == _vision(2)["products"]
    assert body["vision_cost"] == 0.003
    assert "winner_index" not in body and "metadata" not in body
    # R-METER fix: the WHOLE envelope, key for key -- the flag row promises
    # this exact shape to the client.
    assert body == {
        "success": False,
        "action": "comparison_failed",
        "error": result["error"],
        "code": "TIMEOUT",
        "request_id": "retro-w2-1-envelope-shape",
        "products": _vision(2)["products"],
        "vision_cost": 0.003,
        "message": "Products identified but comparison failed. You can compare them via text.",
    }, body


def test_pin_camera_envelope_on_meter_off_keeps_todays_accounting(
    monkeypatch, client, authed
):
    """GREEN PIN (ruling: the no-bill half belongs to ENABLE_PAID_ROUTE_METERING):
    envelope ON with metering OFF changes the BODY only -- history and the
    success log are today's, and nothing is consumed or refunded."""
    monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2),
                 compare_result=dict(UNSUCCESSFUL_RESULTS[2][1]))

    body = _post_identify(client).json()

    assert body["action"] == "comparison_failed"
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.lifetime == []
    assert ledger.history == ["camera"] and ledger.log_success == [True]


@pytest.mark.parametrize("raw,expected", [
    ("true", True), ("TRUE", True), (" true ", True), ("1", True), ("yes", True),
    ("ON", True), ("", False), ("false", False), ("0", False), ("no", False),
    ("off", False),
])
def test_camera_failure_envelope_flag_reader(monkeypatch, raw, expected):
    """GREEN PIN: the new flag is read per call with .strip().lower()."""
    monkeypatch.setenv(ENVELOPE, raw)
    assert image_routes.camera_failure_envelope_enabled() is expected


def test_camera_anon_unsuccessful_result_refunds_anon_credit_once(
    monkeypatch, client, anonymous
):
    """GREEN PIN (ruling 2): the W2-1b unsuccessful-result exit is a non-delivery, so
    under ENABLE_PAID_ROUTE_METERING it refunds the anon credit once too."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2),
                 compare_result=dict(UNSUCCESSFUL_RESULTS[0][1]))

    resp = _post_identify(client, fp=FP)

    assert resp.status_code == 200
    assert ledger.anon_checks == [FP]
    assert ledger.anon_refunds == [FP], ledger.anon_refunds
    assert ledger.anon_refund_keys == [ANON_GATE_KEYS], ledger.anon_refund_keys
    assert "usage_refund.image.anon.comparison_unsuccessful" in ledger.labels
    assert ledger.consumes == [] and ledger.refunds == []


@pytest.mark.parametrize("exit_id,stub_kwargs,status", CAMERA_SIX_EXITS, ids=_SIX_IDS)
def test_camera_anon_gate_not_debited_is_never_refunded(
    monkeypatch, client, anonymous, exit_id, stub_kwargs, status
):
    """BASE PIN (R-METER fix): the anon refund is armed only when the gate reports
    it actually DEBITED (`consumed: True`). An allowed-but-not-consumed gate
    answer must never be refunded -- that would mint a free credit. (The gate
    reports consumed True on every allowed path today, fail-open included, so
    this pins the contract rather than a reachable prod path.)"""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, **stub_kwargs)

    def _not_consumed(fp, *_a, **_kw):
        ledger.anon_checks.append(fp)
        return _done({"allowed": True, "reason": None, "tier": "free", "consumed": False,
                      "consumed_keys": None,
                      "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 0}})

    monkeypatch.setattr(image_routes, "check_anon_usage_allowed", _not_consumed)

    resp = _post_identify(client, fp=FP)

    assert resp.status_code == status, resp.text[:300]
    assert ledger.anon_checks == [FP]
    assert ledger.anon_refunds == [], (
        f"exit {exit_id}: nothing was debited, so nothing may be refunded; "
        f"got {ledger.anon_refunds!r}"
    )


@pytest.mark.parametrize("kind", ["validation_400", "moderation_exception"])
def test_record_camera_anon_followups_not_refunded(monkeypatch, client, anonymous, kind):
    """RECORD (ruling 2 -- follow-ups for issue #128, deliberately NO code):
    the five image-validation 400s (the anon debit happens BEFORE them) and
    the moderation-exception re-raise do NOT refund the anon credit. This pin
    is EXPECTED to flip the day #128 wires them."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    if kind == "validation_400":
        _stub_camera(monkeypatch, ledger, vision=_vision(2))
        resp = _post_identify(client, fp=FP, content=b"")
        assert resp.status_code == 400
    else:
        _stub_camera(monkeypatch, ledger, vision=_vision(2), moderation_raises=True)
        resp = _post_identify(client, fp=FP)
        assert resp.status_code == 500
    assert ledger.anon_checks == [FP]
    assert ledger.anon_refunds == []


@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_url_compare_failed_verdict_wire_shape(monkeypatch, client, verb):
    """GREEN PIN (ruling 3): a failed verdict surfaces through the text route's
    `_surface_comparison_failure` mapping -- the structured {code, error}
    detail the error handler lifts to the TOP LEVEL of the envelope; code
    LLM_UNAVAILABLE, the constant friendly message, never str(e), never a
    winner. That mapping sends LLM_UNAVAILABLE as 503 (text_routes W1-3)."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, get_client_raises=LEAK)

    if verb == "POST":
        resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": URL1, "url2": URL2})

    body = resp.json()
    assert resp.status_code == 503, resp.text[:300]
    assert body.get("success") is False
    assert body.get("code") == "LLM_UNAVAILABLE", body
    assert body.get("error") == structured_comparison_service.LLM_UNAVAILABLE_FRIENDLY_MESSAGE
    assert "winner_index" not in body and "comparison" not in body
    assert LEAK_MARK not in resp.text


def test_pin_url_compare_extraction_failure_envelope_unchanged(monkeypatch, client):
    """BASE PIN (identity through the shared mapping): the <2-products exit's full
    envelope, minus the random request_id, is today's 400 BAD_REQUEST body."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, extract_ok=False)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    body = resp.json()
    body.pop("request_id", None)
    assert resp.status_code == 400
    assert body == {"success": False, "error": "Could not extract both products",
                    "code": "BAD_REQUEST"}, body


# ===========================================================================
# R-METER fix round (adversary round 1): the benign-survivor rows folded into
# real pins (the round-1 presence RECORD was replaced in round 3 by the
# truthiness pins, see test_green_url_compare_full_verdict_with_nonempty_error_is_503).
# ===========================================================================
def test_pin_camera_failure_envelope_helper_never_forwards_codeless_error():
    """GREEN PIN (folds adversary row `envelope_forwards_generic_error`): the
    envelope helper's own contract, called directly -- a CODE-LESS result's
    `error` is never forwarded, even if a caller hands it the raw str(e)
    unscrubbed; it becomes the constant with code INTERNAL_ERROR. A coded
    result keeps its own friendly `error`. Through the route the unflagged
    scrub runs first, so only a direct call can see this second guard."""
    from types import SimpleNamespace

    request = SimpleNamespace(state=SimpleNamespace(request_id="rid-helper"))
    codeless = image_routes._camera_failure_envelope(
        {"success": False, "error": LEAK}, request, [], 0.0)
    assert codeless["error"] == image_routes.CAMERA_UNSUCCESSFUL_CONSTANT_ERROR
    assert codeless["code"] == "INTERNAL_ERROR"
    assert LEAK_MARK not in repr(codeless)

    timeout = dict(UNSUCCESSFUL_RESULTS[0][1])
    coded = image_routes._camera_failure_envelope(timeout, request, [], 0.0)
    assert coded["error"] == timeout["error"] and coded["code"] == "TIMEOUT"
    assert coded["request_id"] == "rid-helper"


@pytest.mark.parametrize("meter_on", [False, True], ids=["meter_off", "meter_on"])
def test_pin_camera_codeless_failure_without_error_key_body_unchanged(
    monkeypatch, client, authed, meter_on
):
    """BASE PIN (folds adversary row `r1_scrub_drops_presence`): the unflagged scrub
    REPLACES an existing code-less `error`; it never ADDS one. A code-less
    unsuccessful result carrying no `error` key keeps today's body key for key
    with the envelope flag OFF (metering OFF or ON -- metering moves the
    accounting only). compare_from_text does not produce this shape today;
    the pin holds the "only that one value changes" promise for any caller."""
    if meter_on:
        monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    bare = {"success": False, "total_cost": 0.0}
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=bare)

    body = _post_identify(client).json()

    expected = dict(bare)
    expected["metadata"] = {
        "input_method": "camera",
        "vision_cost": 0.003,
        "identified_products": _vision(2)["products"],
    }
    expected["action"] = "comparison"
    assert body == expected, body
    assert list(body) == list(expected)


@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS, ids=_UNSUCCESSFUL_IDS)
def test_pin_camera_unsuccessful_log_error_message_is_code_or_constant(
    monkeypatch, client, authed, case, result
):
    """GREEN PIN (folds adversary row `r1_log_unsuccessful_error_message_raw`):
    under ENABLE_PAID_ROUTE_METERING the non-delivery exit 7 logs
    success=False with error_message = the result's CODE (a code-less result
    logs the constant) -- never the free-text `error`, and never str(e)."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=dict(result))

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:300]
    expected = result.get("code") or image_routes.CAMERA_UNSUCCESSFUL_CONSTANT_ERROR
    assert ledger.log_success == [False], ledger.log_success
    assert ledger.log_errors == [expected], ledger.log_errors
    assert LEAK_MARK not in repr(ledger.log_errors)


def test_pin_url_compare_surfaced_failure_is_returned_not_billed(
    monkeypatch, client, authed
):
    """GREEN PIN (folds adversary row `r1_url_route_ignore_surfaced_return`): when
    the shared mapping RETURNS a body (its CONTENT_UNAVAILABLE arm) the URL
    route serves exactly that body as a non-delivery -- one consume, one
    refund, no lifetime bump, no history row. compare_from_urls does not
    produce CONTENT_UNAVAILABLE today; without this pin a fall-through would
    bill it and write history the day it does."""
    monkeypatch.setenv(METER, "true")
    ledger = Ledger()
    _stub_url(monkeypatch, ledger)
    blocked = {"success": False, "code": "CONTENT_UNAVAILABLE",
               "error": "We don't compare this category", "layer": "moderation_api"}

    async def _blocked(*_a, **_kw):
        return dict(blocked)

    monkeypatch.setattr(url_routes, "compare_from_urls", _blocked)

    resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})

    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == blocked, resp.json()
    assert ledger.consumes == [authed["id"]]
    assert ledger.refunds == [authed["id"]], ledger.refunds
    assert ledger.lifetime == [] and ledger.history == [], (
        ledger.lifetime, ledger.history)


@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_green_url_compare_full_verdict_with_nonempty_error_is_503(monkeypatch, client, verb):
    """GREEN PIN (Fable round-3 ruling 2, TRUTHINESS; replaces the round-1
    presence RECORD): a verdict the model answered in full that ALSO carries a
    NON-EMPTY `error` is NOT delivered -- 503 LLM_UNAVAILABLE with the constant
    friendly message at the top level of the envelope, never the error text,
    never the winner. (Base 1c6f6796 served it as a 200 success.) Kills the
    no-check mutant; the falsy rows above kill the presence mutant."""
    ledger = Ledger()
    _stub_url(monkeypatch, ledger, verdict=_FULL_VERDICT_WITH(LEAK))

    result = _run(url_extraction_service.compare_from_urls(URL1, URL2, "bahrain"))
    assert result == {
        "success": False,
        "code": "LLM_UNAVAILABLE",
        "error": structured_comparison_service.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
    }, result

    if verb == "POST":
        resp = client.post("/api/v1/url/compare", json={"url1": URL1, "url2": URL2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": URL1, "url2": URL2})

    body = resp.json()
    assert resp.status_code == 503, resp.text[:300]
    body.pop("request_id", None)
    assert body == {
        "success": False,
        "code": "LLM_UNAVAILABLE",
        "error": structured_comparison_service.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
    }, body
    assert LEAK_MARK not in resp.text
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.history == []


# ===========================================================================
# R-METER round 3 (Fable ruling 1): the DEPLOY state the PR prescribes --
# ENABLE_PAID_ROUTE_METERING AND ENABLE_CAMERA_FAILURE_ENVELOPE both ON -- with
# an UNSUCCESSFUL comparison. These assert the LEDGER, not only the body; each
# of r2_both_flags_bill_fallthrough, r2_both_flags_skip_refunds_only,
# r2_meter_branch_envelope_before_refund and r2_both_flags_log_success_true
# turns them red.
# ===========================================================================
def _expected_envelope(result: dict, rid: str) -> dict:
    code = result.get("code")
    envelope = {
        "success": False,
        "action": "comparison_failed",
        "error": result["error"] if code else image_routes.CAMERA_UNSUCCESSFUL_CONSTANT_ERROR,
        "code": code or "INTERNAL_ERROR",
        "request_id": rid,
        "products": _vision(2)["products"],
        "vision_cost": 0.003,
        "message": "Products identified but comparison failed. You can compare them via text.",
    }
    if result.get("layer"):
        envelope["layer"] = result["layer"]
    return envelope


@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS, ids=_UNSUCCESSFUL_IDS)
def test_green_camera_both_flags_on_unsuccessful_refunds_and_does_not_bill(
    monkeypatch, client, authed, case, result
):
    """GREEN PIN (round-3 ruling 1, authed): both flags ON, an unsuccessful
    result is a NON-delivery in the ledger -- one consume, the reserved credit
    refunded exactly once under `usage_refund.image.comparison_unsuccessful`,
    NO record_lifetime_comparison, NO history row, log_search success=False
    with the code-or-constant error_message -- AND the body is the full
    `comparison_failed` envelope."""
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=dict(result))

    rid = f"retro-w2-1-both-{case}"
    resp = _post_identify(client, request_id=rid)

    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == _expected_envelope(result, rid), resp.json()
    assert ledger.consumes == [authed["id"]], ledger.consumes
    assert ledger.refunds == [authed["id"]], (
        f"[{case}] both flags ON: the reserved credit must come back exactly once; "
        f"refunds={ledger.refunds!r} labels={ledger.labels!r}"
    )
    assert ledger.labels.count("usage_refund.image.comparison_unsuccessful") == 1, ledger.labels
    assert ledger.lifetime == [], f"[{case}] lifetime burned: {ledger.lifetime!r}"
    assert ledger.history == [], f"[{case}] history written: {ledger.history!r}"
    assert ledger.log_success == [False], f"[{case}] log: {ledger.log_success!r}"
    assert ledger.log_errors == [
        result.get("code") or image_routes.CAMERA_UNSUCCESSFUL_CONSTANT_ERROR
    ], ledger.log_errors
    assert "log_search.camera.success" not in ledger.labels, ledger.labels
    assert "save_comparison.camera" not in ledger.labels, ledger.labels
    assert "record_lifetime.image" not in ledger.labels, ledger.labels
    assert LEAK_MARK not in resp.text


@pytest.mark.parametrize("case,result", UNSUCCESSFUL_RESULTS, ids=_UNSUCCESSFUL_IDS)
def test_green_camera_both_flags_on_anon_unsuccessful_refunds_anon_credit_once(
    monkeypatch, client, anonymous, case, result
):
    """GREEN PIN (round-3 ruling 1, anonymous): ENABLE_ANON_USAGE_GATE plus
    both flags ON, an unsuccessful result refunds the anon credit exactly once
    with the gate's own consumed_keys, never touches the authed ledger, meters
    no anonymous comparison, writes no history, logs success=False, and serves
    the full `comparison_failed` envelope."""
    monkeypatch.setenv(ANON_GATE, "true")
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(ENVELOPE, "true")
    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(2), compare_result=dict(result))
    anon_recorded: list = []

    def _record_anon(fp, *_a, **_kw):
        anon_recorded.append(fp)
        return _done()

    monkeypatch.setattr(image_routes, "record_anon_comparison", _record_anon)

    rid = f"retro-w2-1-both-anon-{case}"
    resp = _post_identify(client, fp=FP, request_id=rid)

    assert resp.status_code == 200, resp.text[:300]
    assert resp.json() == _expected_envelope(result, rid), resp.json()
    assert ledger.anon_checks == [FP], ledger.anon_checks
    assert ledger.anon_refunds == [FP], (
        f"[{case}] both flags ON: the anon credit must come back exactly once; "
        f"anon_refunds={ledger.anon_refunds!r} labels={ledger.labels!r}"
    )
    assert ledger.anon_refund_keys == [ANON_GATE_KEYS], ledger.anon_refund_keys
    assert ledger.labels.count("usage_refund.image.anon.comparison_unsuccessful") == 1
    assert ledger.consumes == [] and ledger.refunds == [] and ledger.lifetime == []
    assert ledger.history == [], ledger.history
    assert anon_recorded == [], f"[{case}] anon comparison metered: {anon_recorded!r}"
    assert ledger.log_success == [False], ledger.log_success

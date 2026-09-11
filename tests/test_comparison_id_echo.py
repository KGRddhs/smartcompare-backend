"""W3-2 (SESSION 65) RED tests -- echo `comparison_id` on the text compare
routes so the client can attribute what it just did.

Finding ``MB-NETWORK-CONTRACT-07``. Backend, flag ``ENABLE_COMPARISON_ID_ECHO``
(default OFF; OFF is today's fire-and-forget on all three routes). Spec:
``.qa-w1b/W3_2_UNIT_SPEC.md``.

Written BEFORE the implementation. Every red node fails on an ASSERTION about a
response the EXISTING runtime already produces -- a body key, an SSE terminal
event, a wall-clock delta -- never on an ImportError or an AttributeError for a
symbol that does not exist yet. Nothing here imports ``persist_comparison`` or
``track_after_persist``: the seam every test drives is
``feedback_service.save_comparison`` (the insert) and the four follow-up leaves,
all of which exist today and must still exist after the split.

--------------------------------------------------------------------------
WHAT IS WRONG TODAY -- MEASURED ON THIS TREE AT eecd8bf9
--------------------------------------------------------------------------

``grep -n comparison_id app/api/text_routes.py`` returns NOTHING, and the
routes could not echo it if they wanted to: persistence is
``fire_and_forget(save_comparison_and_track_cohort(...))`` at
``text_routes.py:327`` (POST), ``:476`` (GET) and ``:697`` (stream finally), so
the response is built and returned before the ``comparisons`` row exists.

Driven through the real ASGI app with the insert stubbed to return a known
UUID (harness identical to the one in this file)::

    POST /api/v1/text/compare  -> 200, top-level keys
                                  ['metadata', 'products', 'success']
                                  has comparison_id: False
    GET  /api/v1/text/compare  -> 200, has comparison_id: False
    GET  /api/v1/text/compare/stream
         terminal event 'settle_complete': has comparison_id=False
         terminal event 'complete':        has comparison_id=False

Consequence: the feedback and analytics rows the client writes afterwards carry
no ``comparison_id``, the share sheet cannot link the comparison at the
high-intent moment, and ``vw_cohort_feedback_lift`` cannot join them.

--------------------------------------------------------------------------
WHY THE RESPONSE KEY IS `comparison_id` AND NOTHING ELSE
--------------------------------------------------------------------------

The CLIENT HALF IS ALREADY SHIPPED. ``SmartCompareApp/src/services/api.ts:413``
already merges a persisted row id onto a comparison payload under exactly this
key (``return comparison?.id ? { ...full, comparison_id: comparison.id } : full``
-- "additive, shape-preserving", M18 MB-contract-03), and
``SmartCompareApp/src/types/types.ts:289`` declares ``comparison_id?: string``
on ``ComparisonResult`` with the comment "NOT emitted by /text/compare (the id
is created at save time and never echoed back)". The backend echo is the missing
half of an already-wired contract.

For the STREAM the same key must land on the TERMINAL EVENT's payload, because
``api.ts``'s ``dispatchTerminal`` (`:686`) hands that payload object straight to
``callbacks.onComplete`` -- it is the same ``ComparisonResult`` the sync POST
returns. Both ``settle_complete`` and ``complete`` are terminal and carry the
SAME payload object; the client latches FIRST-WINS (A7), so it is
``settle_complete`` the app actually reads. Both are asserted.

--------------------------------------------------------------------------
THE CONTRACT
--------------------------------------------------------------------------

1. Authed POST / GET ``/text/compare`` and the SSE stream's terminal event
   carry ``comparison_id`` == the id the insert returned.
2. An insert FAILURE must not fail the compare: 200, ``success: true``,
   ``comparison_id: null`` (the KEY IS PRESENT, the value is null -- an honest
   null, not a silent omission), and NONE of the four follow-ups run, because
   there is no id to track against.
3. The four follow-ups (savings-cache bust, ``track_event``, critique persist,
   referral Loop 2) stay FIRE-AND-FORGET: the response must not wait on them.
4. Every NON-text caller of ``save_comparison_and_track_cohort``
   (``image_routes.py:340``, ``url_routes.py:122``) keeps today's composed
   behaviour byte-for-byte -- same insert call, same four follow-ups, same
   order, same falsy-id gate.
5. An UNAUTHENTICATED compare keeps today's shape exactly: no ``comparison_id``
   key at all (nothing was persisted, so there is nothing honest to report).

--------------------------------------------------------------------------
MEASUREMENT NOTES THAT MAKE THESE NODES DETERMINISTIC
--------------------------------------------------------------------------

* Follow-up stubs record at CALL time (a plain function that appends and then
  returns an already-built coroutine), never at await time -- the production
  sites are ``fire_and_forget(...)`` and a task may never be scheduled before
  ``TestClient`` returns.
* MEASURED on this box: ``TestClient`` does NOT block on a pending
  fire-and-forget task. A 1.0 s ``track_event`` stub left the response at
  0.010 s with the follow-up still unresolved. That is what gives
  ``test_response_does_not_wait_on_the_follow_ups`` teeth rather than making it
  vacuous.
* The suppression node does not rely on a task NOT running (which would pass
  vacuously). It replaces ``text_routes.fire_and_forget`` with a recorder,
  DRAINS the captured coroutines explicitly afterwards, and then asserts no
  follow-up was reached.
* Each node uses a distinct user id and its own UUID so no ledger, counter or
  slowapi bucket is shared.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes, text_routes, url_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.services import feedback_service, referral_service


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------
def _base_result() -> dict:
    """A minimal renderable-looking compare payload. Fresh dict per call:
    `save_comparison_and_track_cohort` POPS `metadata._verdict_critique`, so a
    shared module-level literal would leak state between nodes."""
    return {
        "success": True,
        "products": [
            {"brand": "Alpha", "name": "One"},
            {"brand": "Beta", "name": "Two"},
        ],
        "metadata": {
            "total_cost": 0.011,
            "cohort_injected": True,
            "_verdict_critique": {
                "axis_scores": {"clarity": 4},
                "needs_regen": False,
                "low_axes": [],
                "critic_tokens_used": 17,
            },
        },
    }


class Insert:
    """Stand-in for `feedback_service.save_comparison` (the comparisons insert).

    `row_id=None` reproduces the real function's "unrenderable payload" /
    failed-write return of `None`; `raises=True` reproduces an exception out of
    Supabase. `delay` puts a recorded round trip on the call.
    """

    def __init__(self, row_id: str | None = None, *, raises: bool = False,
                 delay: float = 0.0) -> None:
        self.row_id = row_id
        self.raises = raises
        self.delay = delay
        self.calls: list[dict] = []

    def install(self, monkeypatch) -> "Insert":
        async def _save(**kwargs):
            self.calls.append(kwargs)
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.raises:
                raise RuntimeError("w3-2 probe: comparisons insert failed")
            return {"id": self.row_id} if self.row_id else None

        monkeypatch.setattr(feedback_service, "save_comparison", _save)
        return self


class FollowUps:
    """Records the four post-insert follow-ups AT CALL TIME.

    Order is recorded too: today's sequence is savings-cache bust ->
    track_event -> critique persist -> referral Loop 2, and the split must not
    reorder it for the non-text callers.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.track_event_kwargs: list[dict] = []
        self.slow_seconds = 0.0
        self.slow_done = threading.Event()

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def install(self, monkeypatch) -> "FollowUps":
        fu = self

        def _delete_cached(key):
            fu.calls.append(("cache_bust", key))
            return True

        # `_delete_cached_async` references the module-level `delete_cached` in
        # BOTH branches by design, so this one patch covers the redis-offload
        # flag ON and OFF alike.
        monkeypatch.setattr(feedback_service, "delete_cached", _delete_cached)

        def _track_event(**kwargs):
            fu.calls.append(("track_event", kwargs.get("comparison_id")))
            fu.track_event_kwargs.append(kwargs)

            async def _result():
                if fu.slow_seconds:
                    await asyncio.sleep(fu.slow_seconds)
                    fu.slow_done.set()
                return {"success": True, "id": "evt-w3-2"}

            return _result()

        monkeypatch.setattr(feedback_service, "track_event", _track_event)

        def _persist_critique(comparison_id, crit_meta):
            fu.calls.append(("persist_critique", comparison_id))

            async def _result():
                return None

            return _result()

        monkeypatch.setattr(feedback_service, "_persist_verdict_critique",
                            _persist_critique)

        class _FakeReferralService:
            async def try_trigger_loop2(self, **kwargs):
                fu.calls.append(("loop2", kwargs.get("comparison_id")))
                return None

        # `save_comparison_and_track_cohort` imports ReferralService lazily from
        # the module, so the module attribute is the binding that matters.
        monkeypatch.setattr(referral_service, "ReferralService",
                            _FakeReferralService)
        return self


class _FireAndForgetRecorder:
    """Replacement for `text_routes.fire_and_forget` that CAPTURES instead of
    scheduling, so a node can drain the coroutines deterministically."""

    def __init__(self) -> None:
        self.captured: list[tuple[str, object]] = []
        self.labels_drained: list[str] = []

    def __call__(self, coro, label):
        self.captured.append((label, coro))
        return None

    def drain(self) -> list[str]:
        pending = self.captured
        self.captured = []

        async def _run():
            for label, coro in pending:
                self.labels_drained.append(label)
                try:
                    await coro
                except Exception:  # noqa: BLE001 -- production swallows these too
                    pass

        asyncio.run(_run())
        return self.labels_drained

    def close(self) -> None:
        for _label, coro in self.captured:
            try:
                coro.close()
            except Exception:  # noqa: BLE001
                pass
        self.captured = []


def _stub_text_routes(monkeypatch, *, result: dict | None = None,
                      stream_payload: dict | None = None) -> None:
    """Stub every leaf `text_routes` reaches around the persistence seam, so a
    node measures ONLY the comparison-id contract."""
    payload = result if result is not None else _base_result()
    stream = stream_payload if stream_payload is not None else _base_result()

    class _Service:
        async def compare_from_text(self, *_a, **_kw):
            return payload

        async def compare_from_text_streaming(self, *_a, **_kw):
            yield ("status", {"message": "Parsing query..."})
            yield ("specs", {"product_0": {}})
            # Both terminal events carry the SAME payload object, exactly as
            # `structured_comparison_service.py:4710-4711` yields them.
            yield ("settle_complete", stream)
            yield ("complete", stream)

    monkeypatch.setattr(text_routes, "get_comparison_service", lambda: _Service())

    async def _prefs(*_a, **_kw):
        return {"success": False}

    monkeypatch.setattr(text_routes, "get_user_preferences", _prefs)

    async def _consume(*_a, **_kw):
        return {
            "allowed": True, "reason": None, "tier": "free", "consumed": True,
            "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
        }

    monkeypatch.setattr(text_routes, "consume_comparison_credit", _consume)

    def _noop(*_a, **_kw):
        async def _result():
            return None

        return _result()

    monkeypatch.setattr(text_routes, "refund_comparison_credit", _noop)
    monkeypatch.setattr(text_routes, "record_lifetime_comparison", _noop)
    monkeypatch.setattr(text_routes, "log_search", _noop)


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        lines = [ln for ln in block.strip().split("\n") if ln]
        if len(lines) < 2:
            continue
        event_type = lines[0].replace("event: ", "").strip()
        data = json.loads(lines[1][len("data: "):])
        events.append((event_type, data))
    return events


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _limiter_off():
    """The compare routes are 10/min on a bucket keyed by path; this file makes
    more than ten requests to `/api/v1/text/compare`."""
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = prior


@pytest.fixture(autouse=True)
def comparison_id_echo_flag(monkeypatch):
    """REWORK RULING item 1 (Fable, 2026-09-08): the echo now sits behind
    ``ENABLE_COMPARISON_ID_ECHO``, default OFF, read PER CALL.

    Every node in this file therefore runs with the variable at a KNOWN value
    rather than at whatever the ambient environment happens to hold:

    * DEFAULT (this autouse fixture) -- forced ``"true"``. The fourteen original
      contract nodes above are flag-ON contracts: they describe what the echo
      does once it is activated.
    * ``flag_off`` -- the variable is UNSET, which is prod's shipped state and
      the state CI runs in. Those nodes pin that flag-OFF is today's exact
      pre-W3-2 path.

    Mechanism: ``monkeypatch`` is function-scoped, so this fixture and
    ``flag_off`` receive the SAME instance and the same undo stack; ``flag_off``
    depends on this fixture BY NAME so its ``delenv`` can never be ordered
    before this ``setenv``.
    """
    monkeypatch.setenv("ENABLE_COMPARISON_ID_ECHO", "true")


@pytest.fixture
def flag_off(comparison_id_echo_flag, monkeypatch):
    """Prod's default: the flag is absent from the environment entirely."""
    monkeypatch.delenv("ENABLE_COMPARISON_ID_ECHO", raising=False)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {
        "id": f"w3-2-{request.node.name}"[:120],
        "email": "w3-2@example.test",
        "access_token": "w3-2-token",
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


@pytest.fixture
def row_id():
    return str(uuid.uuid4())


@pytest.fixture
def follow_ups(monkeypatch):
    return FollowUps().install(monkeypatch)


@pytest.fixture
def captured_fire_and_forget(monkeypatch):
    recorder = _FireAndForgetRecorder()
    monkeypatch.setattr(text_routes, "fire_and_forget", recorder)
    try:
        yield recorder
    finally:
        recorder.close()


# ===========================================================================
# 1. Sync POST -- the response carries the id of the row it just wrote
# ===========================================================================
def test_post_compare_echoes_the_persisted_comparison_id(
    monkeypatch, client, authed, follow_ups, row_id
):
    Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "alpha vs beta"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert "comparison_id" in body, (
        "POST /text/compare returned no `comparison_id`. The client already "
        "reads this key (api.ts:413, types.ts:289); the backend echo is the "
        f"missing half. Body keys: {sorted(body)}"
    )
    assert body["comparison_id"] == row_id
    uuid.UUID(str(body["comparison_id"]))  # it is the row UUID, not the query


def test_get_compare_echoes_the_persisted_comparison_id(
    monkeypatch, client, authed, follow_ups, row_id
):
    """The GET twin (`text_routes.py:476`) is one of the three text sites the
    unit changes -- echoing on POST alone would leave it inconsistent."""
    Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare?q=alpha+vs+beta")
    body = response.json()

    assert response.status_code == 200
    assert "comparison_id" in body, (
        f"GET /text/compare returned no `comparison_id`. Body keys: {sorted(body)}"
    )
    assert body["comparison_id"] == row_id


# ===========================================================================
# 2. Streaming -- the terminal event is the payload the mobile client reads
# ===========================================================================
def test_stream_terminal_events_carry_the_comparison_id(
    monkeypatch, client, authed, follow_ups, row_id
):
    """The SSE stream is the app's PRIMARY compare path (W1-3's lesson).
    `api.ts`'s `dispatchTerminal` hands the terminal payload to `onComplete`
    as a `ComparisonResult`, and latches FIRST-WINS -- so `settle_complete`,
    the first terminal event, is the one that must carry the id."""
    Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
    assert response.status_code == 200

    events = _parse_sse(response.text)
    terminals = [(t, d) for t, d in events if t in ("settle_complete", "complete")]
    assert terminals, f"no terminal event in the stream: {[t for t, _ in events]}"

    first_type, first_payload = terminals[0]
    assert first_type == "settle_complete"
    assert "comparison_id" in first_payload, (
        "the FIRST terminal SSE event carries no `comparison_id` -- this is the "
        "payload api.ts latches first-wins and delivers as the ComparisonResult. "
        f"Payload keys: {sorted(first_payload)}"
    )
    for event_type, payload in terminals:
        assert payload.get("comparison_id") == row_id, (
            f"terminal event {event_type!r} carries "
            f"{payload.get('comparison_id')!r}, expected {row_id!r}"
        )


# ===========================================================================
# 3. Insert failure -- an honest null, and no follow-up fired
# ===========================================================================
def test_insert_failure_still_succeeds_with_a_null_comparison_id(
    monkeypatch, client, authed, follow_ups
):
    """Today's behaviour on a failed insert is silence; the new behaviour is
    silence PLUS an honest null. The key must be PRESENT and null -- an omitted
    key is indistinguishable from an unauthenticated compare."""
    Insert(raises=True).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "gamma vs delta"})
    body = response.json()

    assert response.status_code == 200, "an insert failure must NOT fail the compare"
    assert body["success"] is True
    assert body.get("products"), "the comparison itself must still be delivered"
    assert "comparison_id" in body, (
        "an insert failure must report an honest null, not omit the key. "
        f"Body keys: {sorted(body)}"
    )
    assert body["comparison_id"] is None


def test_insert_failure_fires_none_of_the_four_follow_ups(
    monkeypatch, client, authed, follow_ups, captured_fire_and_forget
):
    """The failure branch has no id to track against, so the savings-cache
    bust, `track_event`, the critique persist and referral Loop 2 must all be
    skipped. Deterministic: `fire_and_forget` is captured and DRAINED here, so
    a passing assertion cannot be the vacuous "the task never got scheduled"."""
    Insert(raises=True).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "gamma vs delta"})
    assert response.status_code == 200

    captured_fire_and_forget.drain()

    assert follow_ups.names == [], (
        "an insert that failed left no comparison_id, so nothing may be tracked "
        f"against it -- but these follow-ups ran: {follow_ups.names}"
    )


# ===========================================================================
# 4. The follow-ups stay off the critical path
# ===========================================================================
def test_response_does_not_wait_on_the_follow_ups(
    monkeypatch, client, authed, follow_ups, row_id
):
    """Only the INSERT is awaited. If an implementation awaits the whole
    composition, a slow `track_event` lands on the user's critical path.

    MEASURED baseline on this box: with everything stubbed the route answers in
    ~10 ms, and TestClient does not block on a pending fire-and-forget task.
    """
    slow_seconds = 1.0
    follow_ups.slow_seconds = slow_seconds
    Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    started = time.perf_counter()
    response = client.post("/api/v1/text/compare", json={"query": "eps vs zeta"})
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < slow_seconds * 0.6, (
        f"the response waited {elapsed:.3f}s on a {slow_seconds:.1f}s follow-up "
        "-- only the insert may be awaited"
    )
    assert not follow_ups.slow_done.is_set(), (
        "the slow follow-up resolved before the response returned"
    )
    body = response.json()
    assert body.get("comparison_id") == row_id, (
        "the id must still be echoed even though the follow-ups are deferred. "
        f"Got {body.get('comparison_id')!r}; body keys: {sorted(body)}"
    )


# ===========================================================================
# 5. The non-text callers keep today's composed behaviour
# ===========================================================================
@pytest.mark.asyncio
async def test_composition_still_fires_the_insert_and_all_four_follow_ups(
    monkeypatch, follow_ups, row_id
):
    """`save_comparison_and_track_cohort` is what `image_routes.py:340` and
    `url_routes.py:122` call. After the split it must still be the same
    composition: one insert, then the four follow-ups, in this order."""
    insert = Insert(row_id).install(monkeypatch)

    returned = await feedback_service.save_comparison_and_track_cohort(
        full_response=_base_result(),
        query="alpha vs beta",
        input_type="camera",
        user_id="w3-2-nontext",
    )

    assert returned is None, "the composition's return contract is None"
    assert len(insert.calls) == 1
    assert insert.calls[0]["input_type"] == "camera"
    assert insert.calls[0]["user_id"] == "w3-2-nontext"
    assert follow_ups.names == [
        "cache_bust", "track_event", "persist_critique", "loop2",
    ], f"follow-up set/order changed: {follow_ups.names}"
    assert follow_ups.calls[0][1] == "home:savings:w3-2-nontext"
    assert follow_ups.calls[1][1] == row_id
    assert follow_ups.calls[3][1] == row_id
    assert follow_ups.track_event_kwargs[0]["event_type"] == "comparison_completed"
    assert follow_ups.track_event_kwargs[0]["event_data"] == {"cohort_injected": True}


@pytest.mark.asyncio
async def test_composition_skips_every_follow_up_when_the_insert_returns_no_id(
    monkeypatch, follow_ups
):
    """Today's `if comparison_id:` gate. `save_comparison` returns None for an
    unrenderable payload, and a failed save must never bust a valid cache."""
    insert = Insert(None).install(monkeypatch)

    await feedback_service.save_comparison_and_track_cohort(
        full_response=_base_result(),
        query="alpha vs beta",
        input_type="url",
        user_id="w3-2-noid",
    )

    assert len(insert.calls) == 1
    assert follow_ups.names == [], (
        f"a falsy comparison_id must gate every follow-up: {follow_ups.names}"
    )


@pytest.mark.asyncio
async def test_composition_swallows_an_insert_exception(monkeypatch, follow_ups):
    """The non-text callers fire-and-forget this coroutine; it must never
    raise, or `fire_and_forget`'s done-callback logs a WARNING for what is a
    handled condition."""
    Insert(raises=True).install(monkeypatch)

    await feedback_service.save_comparison_and_track_cohort(
        full_response=_base_result(),
        query="alpha vs beta",
        input_type="url",
        user_id="w3-2-raise",
    )

    assert follow_ups.names == []


def test_non_text_callers_still_bind_to_the_composition():
    """`image_routes` and `url_routes` must keep calling the composition, not
    be rewired onto the split halves -- the spec's "leave every non-text caller
    byte-for-byte in behaviour"."""
    assert (
        image_routes.save_comparison_and_track_cohort
        is feedback_service.save_comparison_and_track_cohort
    )
    assert (
        url_routes.save_comparison_and_track_cohort
        is feedback_service.save_comparison_and_track_cohort
    )


# ===========================================================================
# 6. Unauthenticated compare -- today's shape, pinned
# ===========================================================================
def test_anonymous_post_compare_gains_no_comparison_id_key(
    monkeypatch, client, anonymous, follow_ups
):
    """Nothing is persisted for an anonymous caller (`if user_id:` guards the
    save on all three text sites), so there is no id to report. PINNED AS
    MEASURED TODAY: the key is ABSENT, not null -- a null would claim a save
    was attempted and failed."""
    insert = Insert(str(uuid.uuid4())).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "alpha vs beta"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert "comparison_id" not in body, (
        "an anonymous compare persists nothing; the response must not gain a "
        f"comparison_id key. Body keys: {sorted(body)}"
    )
    assert insert.calls == []
    assert follow_ups.names == []


def test_anonymous_stream_terminal_event_gains_no_comparison_id_key(
    monkeypatch, client, anonymous, follow_ups
):
    insert = Insert(str(uuid.uuid4())).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
    assert response.status_code == 200

    terminals = [
        (t, d) for t, d in _parse_sse(response.text)
        if t in ("settle_complete", "complete")
    ]
    assert terminals
    for event_type, payload in terminals:
        assert "comparison_id" not in payload, (
            f"anonymous terminal event {event_type!r} gained a comparison_id: "
            f"{payload.get('comparison_id')!r}"
        )
    assert insert.calls == []
# ===========================================================================
# 7. M18 CD-interactions-01 -- moving the insert ahead of the terminal yield
#    must NOT start persisting comparisons nobody received
# ===========================================================================
#
# ADDED IN THE GREEN PHASE, and here is why. W3-2 moves the comparisons insert
# out of the stream's `finally` and into the loop, ahead of the terminal yield,
# because the id has to be IN the payload the client latches. The `finally`
# persisted ONLY under `complete_response and not had_error and not
# complete_after_client_gone` -- M18 CD-interactions-01's deliberate ruling that
# a client which dropped BEFORE the final payload is not persisted, not metered
# and IS refunded. An insert hoisted ahead of the yield persists
# unconditionally unless the same gate is reproduced, which would silently
# reverse that ruling.
#
# MEASURED: deleting `not client_gone and not had_error` from that gate leaves
# tests/test_m18_preverdict_disconnect_refund.py fully green (10 passed). Those
# tests assert the fire_and_forget LABEL set, and the label set does NOT move
# when the insert runs early -- the metering branch is still skipped, so no
# `save_comparison.text_stream` label appears either way. The regression is
# visible only by watching the INSERT itself, which is what these two nodes do.
#
# `TestClient` cannot drive a disconnect; the route is therefore called
# directly, with the `_FakeRequest` shape from
# tests/test_m18_preverdict_disconnect_refund.py:50-59.


class _FakeRequest:
    """`is_disconnected()` reports True once `disconnect_after` checks have
    happened."""

    def __init__(self, disconnect_after: int) -> None:
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.calls > self.disconnect_after


async def _drive_stream(fake_request, user):
    response = await text_routes.text_compare_stream(
        request=fake_request,
        q="alpha vs beta",
        product_a=None,
        product_b=None,
        region="bahrain",
        specs=True,
        reviews=True,
        pros_cons=True,
        nocache=False,
        selected_category=None,
        user=user,
    )
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return chunks


@pytest.mark.asyncio
async def test_preverdict_disconnect_still_persists_nothing(
    monkeypatch, follow_ups, captured_fire_and_forget
):
    """The client leaves on the FIRST event, long before the terminal payload.

    The stubbed stream yields status -> specs -> settle_complete -> complete, so
    `disconnect_after=0` reports gone on the status iteration's check and
    `client_gone` is already True when the terminal payload arrives.
    """
    insert = Insert(str(uuid.uuid4())).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    await _drive_stream(
        _FakeRequest(disconnect_after=0),
        {"id": "w3-2-preverdict", "email": "w3-2@example.test",
         "access_token": "w3-2-token"},
    )

    labels = [label for label, _ in captured_fire_and_forget.captured]
    assert insert.calls == [], (
        "a client that left BEFORE the final payload must not get a history "
        "row -- M18 CD-interactions-01. The insert ran anyway, so hoisting it "
        "ahead of the terminal yield reversed that ruling."
    )
    assert follow_ups.names == []
    assert "save_comparison.text_stream" not in labels
    assert "record_lifetime.text_stream" not in labels
    assert "usage_refund.text_stream.incomplete" in labels, (
        f"the gate-reserved credit must still be refunded. Labels: {labels}"
    )


@pytest.mark.asyncio
async def test_postverdict_disconnect_still_persists_exactly_once(
    monkeypatch, follow_ups, captured_fire_and_forget, row_id
):
    """M13-35's case, the control: a client that leaves AFTER the payload was
    captured still meters and still persists -- exactly once.

    Checks run on status (1) and specs (2) while connected; on the
    settle_complete iteration the payload is captured BEFORE check (3), which is
    the first to report gone.
    """
    insert = Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    await _drive_stream(
        _FakeRequest(disconnect_after=2),
        {"id": "w3-2-postverdict", "email": "w3-2@example.test",
         "access_token": "w3-2-token"},
    )

    labels = [label for label, _ in captured_fire_and_forget.captured]
    assert len(insert.calls) == 1, (
        f"expected exactly one insert, got {len(insert.calls)}"
    )
    assert insert.calls[0]["input_type"] == "text_stream"
    assert labels.count("save_comparison.text_stream") == 1
    assert labels.count("record_lifetime.text_stream") == 1
    assert not any(label.startswith("usage_refund") for label in labels), (
        f"a metered stream must not also refund. Labels: {labels}"
    )


# ===========================================================================
# 8. REWORK PINS (Fable REWORK RULING, 2026-09-08) -- the flag, the bound,
#    and the four contracts the adversary showed were undefended
# ===========================================================================
#
# The adversary ran fourteen mutations against the fourteen nodes above and
# found four that survive -- i.e. four contracts the unit OWNS but does not
# guard -- plus one unmitigated risk. The ruling's response:
#
#   1. Gate the whole echo behind `ENABLE_COMPARISON_ID_ECHO` (default OFF,
#      read per call). Flag OFF must be today's EXACT pre-W3-2 path on all
#      three routes.  -> pins 8d below (`test_flag_off_*`)
#   2. Bound the awaited insert with `asyncio.wait_for` on
#      `COMPARISON_ID_PERSIST_TIMEOUT_SECONDS` (default 5.0).  -> pin 8e
#   4a. The stream's honest null (`persisted = True` even when the insert
#      returned None).  -> pin 8a
#   4b. The `not had_error` half of the stream persist gate.  -> pin 8b
#   4c. The G6 `_verdict_critique` exclusion from the DB payload.  -> pin 8c
#
# Each was verified to survive its mutation before this section existed:
# `persisted = comparison_id is not None`, dropping `not had_error`, and
# `_without_verdict_critique(x) -> x` each left 14/14 green.


def _stub_stream_events(monkeypatch, events, *, sync_result=None):
    """Like `_stub_text_routes` but with a CALLER-SUPPLIED streaming event
    sequence, so a node can drive orderings the real orchestrator does not
    currently produce (an `error` ahead of a terminal pair, for 8b)."""
    payload = sync_result if sync_result is not None else _base_result()

    class _Service:
        async def compare_from_text(self, *_a, **_kw):
            return payload

        async def compare_from_text_streaming(self, *_a, **_kw):
            for item in events:
                yield item

    monkeypatch.setattr(text_routes, "get_comparison_service", lambda: _Service())

    async def _prefs(*_a, **_kw):
        return {"success": False}

    monkeypatch.setattr(text_routes, "get_user_preferences", _prefs)

    async def _consume(*_a, **_kw):
        return {
            "allowed": True, "reason": None, "tier": "free", "consumed": True,
            "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
        }

    monkeypatch.setattr(text_routes, "consume_comparison_credit", _consume)

    def _noop(*_a, **_kw):
        async def _result():
            return None

        return _result()

    monkeypatch.setattr(text_routes, "refund_comparison_credit", _noop)
    monkeypatch.setattr(text_routes, "record_lifetime_comparison", _noop)
    monkeypatch.setattr(text_routes, "log_search", _noop)


def _composition_coroutines(recorder, label):
    """The coroutine objects captured under `label`, checked to be the
    COMPOSITION and nothing else.

    A coroutine object carries the code object of the function that produced
    it, so `cr_code is <fn>.__code__` is an identity check that a same-named
    wrapper cannot satisfy."""
    return [coro for lbl, coro in recorder.captured if lbl == label]


# ---------------------------------------------------------------------------
# 8d. Flag OFF == today's exact path, on all three routes
# ---------------------------------------------------------------------------
def test_flag_off_post_compare_takes_todays_fire_and_forget_path(
    monkeypatch, client, authed, follow_ups, row_id, flag_off,
    captured_fire_and_forget,
):
    """Prod default. The response must gain NO `comparison_id` key, nothing may
    be awaited on the request path, and the coroutine handed to
    `fire_and_forget` under today's label must be
    `save_comparison_and_track_cohort` itself -- not a split half, not a
    wrapper."""
    insert = Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "alpha vs beta"})
    body = response.json()

    assert response.status_code == 200
    assert "comparison_id" not in body, (
        "with ENABLE_COMPARISON_ID_ECHO unset the response shape must be "
        f"byte-identical to pre-W3-2. Body keys: {sorted(body)}"
    )
    assert insert.calls == [], (
        "flag OFF must not await the insert on the request path; it ran "
        f"{len(insert.calls)} time(s) before the response returned"
    )

    coros = _composition_coroutines(captured_fire_and_forget, "save_comparison.text.post")
    assert len(coros) == 1, (
        "expected exactly one fire-and-forget under today's label; got "
        f"{[lbl for lbl, _ in captured_fire_and_forget.captured]}"
    )
    assert coros[0].__qualname__ == "save_comparison_and_track_cohort"
    assert coros[0].cr_code is (
        feedback_service.save_comparison_and_track_cohort.__code__
    ), "flag OFF must fire the COMPOSITION, not a split half"

    # ...and the composition still does the whole job when it runs.
    captured_fire_and_forget.drain()
    assert len(insert.calls) == 1
    assert follow_ups.names == ["cache_bust", "track_event", "persist_critique", "loop2"]


def test_flag_off_get_compare_takes_todays_fire_and_forget_path(
    monkeypatch, client, authed, follow_ups, row_id, flag_off,
    captured_fire_and_forget,
):
    insert = Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare?q=alpha+vs+beta")
    body = response.json()

    assert response.status_code == 200
    assert "comparison_id" not in body, f"Body keys: {sorted(body)}"
    assert insert.calls == []

    coros = _composition_coroutines(captured_fire_and_forget, "save_comparison.text.get")
    assert len(coros) == 1, (
        f"labels: {[lbl for lbl, _ in captured_fire_and_forget.captured]}"
    )
    assert coros[0].cr_code is (
        feedback_service.save_comparison_and_track_cohort.__code__
    )

    captured_fire_and_forget.drain()
    assert len(insert.calls) == 1
    assert follow_ups.names == ["cache_bust", "track_event", "persist_critique", "loop2"]


def test_flag_off_stream_takes_todays_finally_path(
    monkeypatch, client, authed, follow_ups, row_id, flag_off,
    captured_fire_and_forget,
):
    """The stream's hoisted insert block must never run with the flag OFF, so
    the `finally`'s `else` arm -- the composite under the UNCHANGED M18 gate --
    is what persists, exactly as it did before W3-2."""
    insert = Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
    assert response.status_code == 200

    terminals = [
        (t, d) for t, d in _parse_sse(response.text)
        if t in ("settle_complete", "complete")
    ]
    assert terminals, "no terminal event in the stream"
    for event_type, payload in terminals:
        assert "comparison_id" not in payload, (
            f"flag OFF, terminal event {event_type!r} gained a comparison_id: "
            f"{payload.get('comparison_id')!r}"
        )
    assert insert.calls == [], (
        "flag OFF must not hoist the insert ahead of the terminal yield"
    )

    coros = _composition_coroutines(
        captured_fire_and_forget, "save_comparison.text_stream"
    )
    assert len(coros) == 1, (
        f"labels: {[lbl for lbl, _ in captured_fire_and_forget.captured]}"
    )
    assert coros[0].cr_code is (
        feedback_service.save_comparison_and_track_cohort.__code__
    ), "flag OFF must take the finally's composite arm"

    captured_fire_and_forget.drain()
    assert len(insert.calls) == 1
    assert insert.calls[0]["input_type"] == "text_stream"
    assert follow_ups.names == ["cache_bust", "track_event", "persist_critique", "loop2"]


# ---------------------------------------------------------------------------
# 8a. Stream honest null -- `persisted = True` even when the insert gave no id
# ---------------------------------------------------------------------------
def test_stream_terminal_events_carry_an_honest_null_when_the_insert_gives_no_id(
    monkeypatch, client, authed, follow_ups, captured_fire_and_forget
):
    """REWORK 4a / revised-ruling condition 4. `save_comparison` returns None
    for an unrenderable payload or a failed write. The stream must then echo
    `comparison_id: null` with the KEY PRESENT -- the same honest null the sync
    path gives -- and fire none of the four follow-ups.

    MUTATION that this exists to catch: `persisted = comparison_id is not None`
    omits the key entirely, which is indistinguishable on the wire from an
    anonymous compare. It left 14/14 green before this node."""
    insert = Insert(None).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
    assert response.status_code == 200

    terminals = [
        (t, d) for t, d in _parse_sse(response.text)
        if t in ("settle_complete", "complete")
    ]
    assert terminals, "no terminal event in the stream"
    for event_type, payload in terminals:
        assert "comparison_id" in payload, (
            f"terminal event {event_type!r} OMITTED comparison_id after a "
            "failed insert -- the contract is an honest null, key present. "
            f"Payload keys: {sorted(payload)}"
        )
        assert payload["comparison_id"] is None, (
            f"terminal event {event_type!r} carried "
            f"{payload['comparison_id']!r}, expected null"
        )

    assert len(insert.calls) == 1, "the insert must still have been attempted"

    captured_fire_and_forget.drain()
    assert follow_ups.names == [], (
        "there is no row to track against, so no follow-up may run: "
        f"{follow_ups.names}"
    )


# ---------------------------------------------------------------------------
# 8b. The `not had_error` half of the stream persist gate
# ---------------------------------------------------------------------------
def test_stream_error_before_the_terminal_payload_persists_nothing(
    monkeypatch, client, authed, follow_ups, captured_fire_and_forget
):
    """REWORK 4b. The hoisted insert reproduces the `finally`'s metering
    condition, which has THREE terms. `not client_gone` is pinned by section 7;
    this pins `not had_error`.

    UNREACHABLE on today's orchestrator -- every `error` yield outside the tail
    `except` is immediately followed by a `return`, so an error can never
    precede a terminal pair in production. The gate nevertheless lives on the
    ROUTE, and a route test's stub can reach it, which is exactly why the
    condition is pinnable at all.

    MUTATION: dropping `not had_error` from the gate left 14/14 green."""
    payload = _base_result()
    insert = Insert(str(uuid.uuid4())).install(monkeypatch)
    _stub_stream_events(monkeypatch, [
        ("status", {"message": "Parsing query..."}),
        ("error", {"error": "w3-2 probe: orchestrator failed", "code": "TIMEOUT"}),
        ("settle_complete", payload),
        ("complete", payload),
    ])

    response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
    assert response.status_code == 200

    events = _parse_sse(response.text)
    assert any(t == "error" for t, _ in events), "the probe must emit its error"
    terminals = [(t, d) for t, d in events if t in ("settle_complete", "complete")]
    assert terminals, "the probe emits terminal events after the error"

    assert insert.calls == [], (
        "an `error` seen before the terminal payload must suppress the insert "
        "-- the row would be persisted and the credit then refunded"
    )
    for event_type, event_payload in terminals:
        assert "comparison_id" not in event_payload, (
            f"terminal event {event_type!r} gained a comparison_id after an "
            f"error: {event_payload.get('comparison_id')!r}"
        )

    labels = [label for label, _ in captured_fire_and_forget.captured]
    assert "save_comparison.text_stream" not in labels, f"labels: {labels}"
    assert "record_lifetime.text_stream" not in labels, f"labels: {labels}"
    assert "usage_refund.text_stream" in labels, (
        f"the errored stream must refund the gate-reserved credit. Labels: {labels}"
    )

    captured_fire_and_forget.drain()
    assert follow_ups.names == []


# ---------------------------------------------------------------------------
# 8c. G6 -- the comparisons row never carries `_verdict_critique`
# ---------------------------------------------------------------------------
def test_db_payload_drops_the_verdict_critique_while_the_response_keeps_it(
    monkeypatch, client, authed, follow_ups, row_id
):
    """REWORK 4c. `metadata._verdict_critique` is an INTERNAL key: history and
    the public share read `full_response` verbatim, so it must never reach the
    `comparisons` row. W3-2 rewrote that mechanism from an in-place
    `metadata.pop` into `_without_verdict_critique`, which sanitizes a COPY --
    necessary now that the insert is awaited BEFORE the route serializes its
    response, where an in-place pop would strip the key from what the user gets.

    Both halves are asserted: gone from the DB payload, still on the wire.

    MUTATION: `_without_verdict_critique(full_response)` -> `full_response`
    writes critique internals into the row and left 14/14 green. Nothing else in
    the repo asserts the comparisons row's metadata keys."""
    insert = Insert(row_id).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    response = client.post("/api/v1/text/compare", json={"query": "alpha vs beta"})
    body = response.json()
    assert response.status_code == 200

    assert len(insert.calls) == 1
    db_payload = insert.calls[0]["full_response"]
    db_metadata = db_payload.get("metadata") or {}
    assert "_verdict_critique" not in db_metadata, (
        "the comparisons row carried critique internals; history and the public "
        f"share serve this verbatim. DB metadata keys: {sorted(db_metadata)}"
    )
    assert db_metadata.get("cohort_injected") is True, (
        "sanitizing must remove ONLY `_verdict_critique`: "
        f"{sorted(db_metadata)}"
    )
    assert "comparison_id" not in db_payload, (
        "the echoed id is a RESPONSE field; it must not be written into the "
        f"row's full_response. DB payload keys: {sorted(db_payload)}"
    )

    # ...and the live payload keeps it, deterministically now that the insert is
    # awaited (pre-W3-2 the in-place pop raced serialization).
    assert "_verdict_critique" in (body.get("metadata") or {}), (
        "the route's own response must be untouched by the DB sanitization. "
        f"Response metadata keys: {sorted(body.get('metadata') or {})}"
    )
    assert body["comparison_id"] == row_id


# ---------------------------------------------------------------------------
# 8e. The bound -- `COMPARISON_ID_PERSIST_TIMEOUT_SECONDS`
# ---------------------------------------------------------------------------
def test_a_stalled_insert_is_bounded_and_echoes_an_honest_null(
    monkeypatch, client, authed, follow_ups, captured_fire_and_forget
):
    """REWORK item 2. The awaited insert has no timeout of its own: with
    `ENABLE_SUPABASE_CLIENT_REUSE` OFF (prod today) the admin client is a bare
    `create_client` with no `ClientOptions`, so the postgrest ceiling is the
    library's 120 s default. `asyncio.wait_for` on
    `COMPARISON_ID_PERSIST_TIMEOUT_SECONDS` bounds it; a timeout is an honest
    null, exactly like a failed insert.

    THIS PINS THE **EFFECTIVE** CASE ONLY, and deliberately so. The bound can
    only fire when `run_db` YIELDS -- i.e. `ENABLE_SYNC_DB_OFFLOAD` ON. With
    that flag OFF `run_db` executes the blocking `.execute()` INLINE in the
    coroutine, the event loop is blocked, and no timeout can fire until the call
    returns; the real ceiling there is W0-2's transport timeout. So this node
    drives the real `save_comparison` with `run_db` replaced by a slow
    AWAITABLE, which is what the offload flag ON looks like.

    MUTATION: remove the `wait_for` and this reddens twice over -- the response
    takes the full stall AND carries the row id instead of null."""
    stall_seconds = 2.0
    monkeypatch.setenv("COMPARISON_ID_PERSIST_TIMEOUT_SECONDS", "0.05")

    from app.services import database_service

    # `save_comparison` gates on `_validate_renderable`, which needs
    # `metadata.query`; without it the function returns before `run_db`.
    result = _base_result()
    result["metadata"]["query"] = "alpha vs beta"

    class _FakeResponse:
        data = [{"id": "w3-2-should-never-be-reached"}]

    class _FakeTable:
        def insert(self, _record):
            return self

        def execute(self):
            return _FakeResponse()

    class _FakeClient:
        def table(self, _name):
            return _FakeTable()

    monkeypatch.setattr(database_service, "get_supabase_client", lambda: _FakeClient())

    ran = {"count": 0}

    async def _slow_run_db(call):
        ran["count"] += 1
        await asyncio.sleep(stall_seconds)
        return call()

    monkeypatch.setattr(database_service, "run_db", _slow_run_db)
    _stub_text_routes(monkeypatch, result=result)

    started = time.perf_counter()
    response = client.post("/api/v1/text/compare", json={"query": "alpha vs beta"})
    elapsed = time.perf_counter() - started
    body = response.json()

    assert response.status_code == 200
    assert elapsed < stall_seconds * 0.5, (
        f"the compare waited {elapsed:.3f}s on a stalled insert -- the awaited "
        "insert is unbounded on the user-facing critical path"
    )
    assert ran["count"] == 1, "the insert must actually have been attempted"
    assert "comparison_id" in body, f"Body keys: {sorted(body)}"
    assert body["comparison_id"] is None, (
        "a timed-out insert must echo an honest null, not the id of a row it "
        f"never confirmed. Got {body['comparison_id']!r}"
    )

    captured_fire_and_forget.drain()
    assert follow_ups.names == [], (
        f"a timed-out insert leaves nothing to track against: {follow_ups.names}"
    )


def test_persist_timeout_knob_defaults_to_five_seconds_and_never_goes_unbounded(
    monkeypatch,
):
    """REWORK item 2 names the number: `COMPARISON_ID_PERSIST_TIMEOUT_SECONDS`,
    default 5.0. Pinned here because nothing else in this file reads the knob's
    default -- 8e patches it to 0.05 -- so a default of 120.0 (the supabase-py
    ceiling this bound exists to undercut) would sail through.

    The knob has no unbounded setting: garbage, non-positive AND non-finite
    values fall back to the default rather than disabling the bound --
    ``float('inf')`` parses, and an operator typo of ``inf`` would otherwise
    reinstate the exact 120 s ceiling the rework ruling closes; ``nan`` would
    fail every comparison and disable the echo.

    MUTATION: `_COMPARISON_ID_PERSIST_TIMEOUT_DEFAULT = 120.0` -> red."""
    monkeypatch.delenv("COMPARISON_ID_PERSIST_TIMEOUT_SECONDS", raising=False)
    assert text_routes.comparison_id_persist_timeout_seconds() == 5.0

    monkeypatch.setenv("COMPARISON_ID_PERSIST_TIMEOUT_SECONDS", "2.5")
    assert text_routes.comparison_id_persist_timeout_seconds() == 2.5

    for garbage in ("", "   ", "abc", "0", "-1", "0.0", "inf", "-inf", "nan", "Infinity"):
        monkeypatch.setenv("COMPARISON_ID_PERSIST_TIMEOUT_SECONDS", garbage)
        assert text_routes.comparison_id_persist_timeout_seconds() == 5.0, (
            f"{garbage!r} must fall back to the 5.0 s default, not disable the bound"
        )


@pytest.mark.parametrize("site", ["get", "stream"])
def test_a_stalled_insert_is_bounded_on_the_get_and_stream_sites_too(
    monkeypatch, client, authed, follow_ups, captured_fire_and_forget, row_id, site
):
    """REWORK item 2 says "at all three sites". 8e drives the bound through the
    real `save_comparison` on POST only; this drives the OTHER two sites with
    the insert seam itself stalled as a slow AWAITABLE (the shape `run_db`
    has with `ENABLE_SYNC_DB_OFFLOAD` ON), so a site that calls the unbounded
    `persist_comparison` directly instead of the bounded helper reddens.

    MUTATION: at the GET or stream site, `_persist_comparison_bounded(` ->
    `persist_comparison(` -> that parametrization reddens (full stall AND the
    row id echoed instead of null)."""
    stall_seconds = 2.0
    monkeypatch.setenv("COMPARISON_ID_PERSIST_TIMEOUT_SECONDS", "0.05")
    insert = Insert(row_id, delay=stall_seconds).install(monkeypatch)
    _stub_text_routes(monkeypatch)

    started = time.perf_counter()
    if site == "get":
        response = client.get("/api/v1/text/compare?q=alpha+vs+beta")
        elapsed = time.perf_counter() - started
        assert response.status_code == 200
        payloads = [("body", response.json())]
    else:
        response = client.get("/api/v1/text/compare/stream?q=alpha+vs+beta")
        elapsed = time.perf_counter() - started
        assert response.status_code == 200
        payloads = [
            (t, d) for t, d in _parse_sse(response.text)
            if t in ("settle_complete", "complete")
        ]
        assert payloads, "no terminal event in the stream"

    assert elapsed < stall_seconds * 0.5, (
        f"{site}: the compare waited {elapsed:.3f}s on a stalled insert -- the "
        "awaited insert is unbounded at this site"
    )
    assert len(insert.calls) == 1, "the insert must actually have been attempted"
    for where, payload in payloads:
        assert "comparison_id" in payload, (
            f"{site}/{where}: key must be PRESENT (honest null). Keys: {sorted(payload)}"
        )
        assert payload["comparison_id"] is None, (
            f"{site}/{where}: a timed-out insert must echo null, not the id of a "
            f"row it never confirmed. Got {payload['comparison_id']!r}"
        )

    captured_fire_and_forget.drain()
    assert follow_ups.names == [], (
        f"{site}: a timed-out insert leaves nothing to track against: {follow_ups.names}"
    )

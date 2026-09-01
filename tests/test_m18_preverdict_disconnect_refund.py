"""M18 CD-interactions-01 — a client that leaves BEFORE the verdict must not be
charged a freemium credit, and (behind a dark flag) must not keep the orchestrator
running.

W3 shipped two changes that defeat each other: M13-37 consumes a credit at the
gate before the generator starts, and M13-35 DRAINS (rather than abandons) the
generator on disconnect. Because the final payload is captured before the
disconnect check, a disconnect at second 2 still ends with `complete_response`
set, so the `finally` takes the METERING branch and the M13-37 refund — which
only fires when `complete_response` is absent — never runs. Pre-wave a dropped
connection was free.

Half A (unflagged): record whether the payload landed while the client was
already gone, and gate the metering branch on it.
Half B (`ENABLE_PREVERDICT_DISCONNECT_ABORT`, default OFF): on a pre-verdict
disconnect, close the orchestrator generator instead of draining it.

The post-verdict disconnect (M13-35) is a regression pin here, not a target.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import contextlib

import pytest

from app.api import text_routes as tr


class _StubService:
    """Copied from tests/test_m13_35_sse_disconnect_finally.py, plus drive/close
    instrumentation so Half B can assert the generator was actually closed."""

    def __init__(self, events):
        self._events = events
        self.yielded = 0
        self.closed = False

    async def compare_from_text_streaming(self, **kwargs):
        try:
            for ev in self._events:
                self.yielded += 1
                yield ev
        finally:
            # aclose() throws GeneratorExit in here; normal exhaustion also runs it.
            self.closed = True


class _FakeRequest:
    """is_disconnected() flips True once `disconnect_after` checks have happened."""

    def __init__(self, disconnect_after):
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


def _wire(monkeypatch, events, consumed=True):
    """Per-test monkeypatch block (from test_m13_35_sse_disconnect_finally.py:52-75).

    Change vs the M13-35 copy: `consumed` defaults to True so the gate-reserved
    credit exists and the refund path is reachable at all.
    """
    from app.middleware.rate_limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False, raising=False)

    stub = _StubService(events)
    monkeypatch.setattr(tr, "get_comparison_service", lambda: stub)

    async def _prefs(uid):
        return {"success": True, "preferences_completed": True, "preferences": {}}
    monkeypatch.setattr(tr, "get_user_preferences", _prefs)

    async def _usage(uid, tok):
        return {"allowed": True, "reason": None, "tier": "free", "consumed": consumed,
                "remaining": {"daily": 5, "monthly": 5, "lifetime_free": 0}}
    monkeypatch.setattr(tr, "consume_comparison_credit", _usage)

    fired = []

    def _capture_faf(coro, label):
        try:
            coro.close()  # don't actually schedule; just record intent
        except Exception:
            pass
        fired.append(label)
    monkeypatch.setattr(tr, "fire_and_forget", _capture_faf)

    return stub, fired


async def _drive(fake_req, user={"id": "u1", "access_token": "tok"}):
    resp = await tr.text_compare_stream(
        request=fake_req,
        q="A vs B",
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
    streamed = []
    async for chunk in resp.body_iterator:
        streamed.append(chunk)
    return streamed


_FULL_PAYLOAD = {
    "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
    "metadata": {"total_cost": 0.01},
}

_SIX_EVENTS = [
    ("status", {}),
    ("specs", {}),
    ("prices", {}),
    ("verdict", {}),
    ("settle_complete", _FULL_PAYLOAD),
    ("complete", _FULL_PAYLOAD),
]


@pytest.mark.asyncio
async def test_preverdict_disconnect_refunds_and_does_not_meter(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    _stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    await _drive(_FakeRequest(disconnect_after=0))

    assert "usage_refund.text_stream.incomplete" in fired
    assert "log_search.text_stream.success" not in fired
    assert "save_comparison.text_stream" not in fired
    assert "record_lifetime.text_stream" not in fired


@pytest.mark.asyncio
async def test_postverdict_disconnect_still_meters(monkeypatch):
    """M13-35 regression pin — a client leaving AFTER the verdict still meters."""
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    _stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    # 5th check (the settle_complete iteration) is the first to report gone,
    # and the payload was captured on that same iteration BEFORE the check.
    await _drive(_FakeRequest(disconnect_after=4))

    assert fired.count("log_search.text_stream.success") == 1
    assert fired.count("save_comparison.text_stream") == 1
    assert fired.count("record_lifetime.text_stream") == 1
    assert not any(label.startswith("usage_refund") for label in fired)


@pytest.mark.asyncio
async def test_preverdict_disconnect_with_consumed_false_does_not_refund(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    _stub, fired = _wire(monkeypatch, _SIX_EVENTS, consumed=False)

    await _drive(_FakeRequest(disconnect_after=0))

    assert not any(label.startswith("usage_refund") for label in fired)


@pytest.mark.asyncio
async def test_error_event_after_disconnect_refunds_exactly_once(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    _stub, fired = _wire(monkeypatch, [("status", {}), ("error", {"message": "boom"})])

    await _drive(_FakeRequest(disconnect_after=0))

    assert fired.count("usage_refund.text_stream") == 1
    assert "usage_refund.text_stream.incomplete" not in fired


@pytest.mark.asyncio
async def test_anonymous_preverdict_disconnect_does_not_refund_or_crash(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    _stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    await _drive(_FakeRequest(disconnect_after=0), user=None)

    assert not any(label.startswith("usage_refund") for label in fired)


@pytest.mark.asyncio
async def test_abort_flag_on_closes_the_orchestrator_generator(monkeypatch):
    monkeypatch.setenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "true")
    stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    await _drive(_FakeRequest(disconnect_after=0))

    assert stub.yielded <= 2, (
        f"orchestrator was driven past the disconnect ({stub.yielded} events yielded)"
    )
    assert stub.closed is True
    assert "usage_refund.text_stream.incomplete" in fired


@pytest.mark.asyncio
async def test_abort_flag_off_still_drains_and_refunds(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    await _drive(_FakeRequest(disconnect_after=0))

    assert stub.yielded == 6, "flag OFF must preserve the M13-35 drain"
    assert "usage_refund.text_stream.incomplete" in fired


@pytest.mark.asyncio
async def test_abort_flag_on_postverdict_disconnect_still_meters(monkeypatch):
    """Half B must never fire once the payload has landed — M13-35's whole point.
    The break is gated on `complete_response is None`.

    Ported from the second session's duplicate #112 implementation, which was
    otherwise dropped in favour of main's. Main's own file did not carry this
    case: it pins flag-ON against the POST-verdict path, where the abort must
    stay out of the way."""
    monkeypatch.setenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "true")
    stub, fired = _wire(monkeypatch, _SIX_EVENTS)

    await _drive(_FakeRequest(disconnect_after=4))

    assert fired.count("record_lifetime.text_stream") == 1
    assert not any(l.startswith("usage_refund") for l in fired)


# ---------------------------------------------------------------------------
# Ordering pin — the accounting must not be pre-empted by generator cleanup
# ---------------------------------------------------------------------------

class _AcloseRaisesService(_StubService):
    """An orchestrator whose unwind RAISES on aclose(). Models the day the
    generator grows a `finally` containing an await checkpoint: under Starlette's
    cancel-on-disconnect task group that unwind can surface CancelledError out of
    `aclose()`."""

    async def compare_from_text_streaming(self, **kwargs):
        try:
            for ev in self._events:
                self.yielded += 1
                yield ev
        except GeneratorExit:
            # Raise ONLY on aclose(), never on normal exhaustion — otherwise the
            # stub would blow up inside the route's `async for` and never reach
            # the finally this test is about.
            #
            # CancelledError specifically, because it is a BaseException: an
            # `except Exception` guard around aclose() does NOT catch it, so this
            # is the one shape that can actually skip the accounting block if
            # aclose() is allowed to pre-empt it. A RuntimeError would prove
            # nothing — an Exception handler swallows that either way.
            self.closed = True
            raise asyncio.CancelledError()


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [False, True])
async def test_refund_survives_an_aclose_that_raises(monkeypatch, flag_on):
    """ORDERING PIN for #112 Half B, ported from the second session.

    `aclose()` must never be positioned where a raising unwind can pre-empt the
    metering/refund decision. If it ran at the FRONT of the finally that owns the
    accounting and raised a BaseException, the whole block would be skipped — no
    metering AND no refund — silently re-opening the exact credit burn #112
    exists to close.

    Main's implementation closes the generator at the `break` site inside the
    `try` instead, so the `finally` still runs and the accounting is safe; the
    other session put it last in the `finally`, which is equally safe. This test
    pins the PROPERTY rather than either placement, so a future refactor that
    moves the close cannot silently reintroduce the hazard. Both flag states,
    because the close is reachable in one and the unwind happens in both."""
    if flag_on:
        monkeypatch.setenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "true")
    else:
        monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    stub, fired = _wire(monkeypatch, _SIX_EVENTS)
    monkeypatch.setattr(
        tr, "get_comparison_service", lambda: _AcloseRaisesService(_SIX_EVENTS)
    )
    # The CancelledError is deliberately NOT swallowed by the route — cancellation
    # must keep propagating. What matters is that the accounting already ran.
    with contextlib.suppress(asyncio.CancelledError):
        await _drive(_FakeRequest(disconnect_after=0))

    assert "usage_refund.text_stream.incomplete" in fired
    assert not any(l.startswith("log_search") for l in fired)
    assert not any(l.startswith("save_comparison") for l in fired)
    assert not any(l.startswith("record_lifetime") for l in fired)

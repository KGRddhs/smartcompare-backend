"""M20 #112 (M18 CD-interactions-01) — a PRE-verdict SSE disconnect must refund
the gate-reserved credit and must NOT meter.

Wave-3 M13-35 (drain-not-abandon) defeats Wave-3 M13-37 (the refund): because
the final payload is captured BEFORE the disconnect check and the loop DRAINS
rather than abandons, a client that leaves at second 2 still ends up with a
non-None `complete_response`, so the `finally` takes the METERING branch and the
`else`-refund is unreachable. Pre-wave the same drop was free. CLAUDE.md's
M13-37 closeout paragraph claimed the streaming else-refund covered this; it
does not on the real disconnect path.

Half A (accounting) is UNFLAGGED. Half B (stop driving the orchestrator, so the
default-unbounded OpenAI tail is not paid for a comparison nobody will read)
ships behind ENABLE_PREVERDICT_DISCONNECT_ABORT, default OFF.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.api import text_routes as tr


_FULL_PAYLOAD = {
    "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
    "metadata": {"total_cost": 0.01},
}


def _events():
    return [
        ("status", {"progress": 10}),
        ("specs", {}),
        ("prices", {}),
        ("verdict", {"winner": {"product_index": 0}, "comparison": {}}),
        ("settle_complete", dict(_FULL_PAYLOAD)),
        ("complete", dict(_FULL_PAYLOAD)),
    ]


class _StubService:
    """Counts yields and records whether the generator was CLOSED (aclose()
    throws GeneratorExit, which runs the finally)."""

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
            self.closed = True


class _FakeRequest:
    """is_disconnected() flips True once `disconnect_after` checks have happened."""

    def __init__(self, disconnect_after):
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


def _wire(monkeypatch, stub, *, consumed=True):
    from app.middleware.rate_limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False, raising=False)
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
    return fired


async def _drive(fake_req, user={"id": "u1", "access_token": "tok"}):
    resp = await tr.text_compare_stream(
        request=fake_req, q="A vs B", product_a=None, product_b=None,
        region="bahrain", specs=True, reviews=True, pros_cons=True,
        nocache=False, selected_category=None, user=user,
    )
    streamed = []
    async for chunk in resp.body_iterator:
        streamed.append(chunk)
    return streamed


@pytest.fixture(autouse=True)
def _abort_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", raising=False)
    yield


# ---------------------------------------------------------------------------
# Half A — accounting (UNFLAGGED)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preverdict_disconnect_refunds_and_does_not_meter(monkeypatch):
    """RED at 17cb981: the metering trio fires and the refund does not."""
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=0))

    assert "usage_refund.text_stream.incomplete" in fired
    assert "log_search.text_stream.success" not in fired
    assert "save_comparison.text_stream" not in fired
    assert "record_lifetime.text_stream" not in fired


@pytest.mark.asyncio
async def test_postverdict_disconnect_still_meters(monkeypatch):
    """M13-35 regression pin — GREEN before and after. The 5th check (the
    settle_complete iteration) is the first to report disconnected, AFTER the
    payload was captured on that same iteration."""
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=4))

    assert fired.count("log_search.text_stream.success") == 1
    assert fired.count("save_comparison.text_stream") == 1
    assert fired.count("record_lifetime.text_stream") == 1
    assert not any(l.startswith("usage_refund") for l in fired)


@pytest.mark.asyncio
async def test_preverdict_disconnect_with_consumed_false_does_not_refund(monkeypatch):
    """The gate found an existing reservation — nothing to give back."""
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub, consumed=False)
    await _drive(_FakeRequest(disconnect_after=0))

    assert not any(l.startswith("usage_refund") for l in fired)


@pytest.mark.asyncio
async def test_error_event_after_disconnect_refunds_exactly_once(monkeypatch):
    """GREEN today — a pin Half A must not disturb. `elif had_error` still wins,
    so exactly one refund fires and it carries the error label."""
    stub = _StubService([("status", {"progress": 10}), ("error", {"message": "boom"})])
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=0))

    assert fired.count("usage_refund.text_stream") == 1
    assert "usage_refund.text_stream.incomplete" not in fired


@pytest.mark.asyncio
async def test_anonymous_preverdict_disconnect_does_not_refund_or_crash(monkeypatch):
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=0), user=None)

    assert not any(l.startswith("usage_refund") for l in fired)


# ---------------------------------------------------------------------------
# Half B — resource (ENABLE_PREVERDICT_DISCONNECT_ABORT, default OFF)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_abort_flag_on_closes_the_orchestrator_generator(monkeypatch):
    """RED at 17cb981: the stub is driven to exhaustion (yielded == 6) and its
    finally is not run deterministically at the disconnect."""
    monkeypatch.setenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "true")
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=0))

    assert stub.yielded <= 2
    assert stub.closed is True
    assert "usage_refund.text_stream.incomplete" in fired


@pytest.mark.asyncio
async def test_abort_flag_off_still_drains_and_refunds(monkeypatch):
    """Flag OFF preserves M13-35's drain (yielded == 6); the refund half is
    unflagged and RED at 17cb981."""
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=0))

    assert stub.yielded == 6
    assert "usage_refund.text_stream.incomplete" in fired


@pytest.mark.asyncio
async def test_abort_flag_on_postverdict_disconnect_still_meters(monkeypatch):
    """Half B must never fire once the payload has landed — M13-35's whole
    point. The break is gated on `complete_response is None`."""
    monkeypatch.setenv("ENABLE_PREVERDICT_DISCONNECT_ABORT", "true")
    stub = _StubService(_events())
    fired = _wire(monkeypatch, stub)
    await _drive(_FakeRequest(disconnect_after=4))

    assert fired.count("record_lifetime.text_stream") == 1
    assert not any(l.startswith("usage_refund") for l in fired)

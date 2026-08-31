"""M13-35 pin — SSE post-stream side effects fire even if the client disconnects
AFTER the verdict/complete events.

Failure scenario: the verdict event carries the entire comparison, so a client can
consume the full result and drop the socket before record_comparison /
save_comparison / log_search ever run — the OpenAI/Serper spend is made but the
freemium counter never moves, repeatably. The fix hoists the post-stream block
into a finally around the async-for, captures the final payload before the
disconnect check, and drains (not abandons) the generator on disconnect.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.api import text_routes as tr


class _StubService:
    def __init__(self, events):
        self._events = events

    async def compare_from_text_streaming(self, **kwargs):
        for ev in self._events:
            yield ev


class _FakeRequest:
    """is_disconnected() flips True once `disconnect_after` checks have happened."""
    def __init__(self, disconnect_after):
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


@pytest.mark.asyncio
async def test_disconnect_after_verdict_still_meters(monkeypatch):
    full_payload = {
        "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
        "metadata": {"total_cost": 0.01},
    }
    events = [
        ("status", {"progress": 10}),
        ("verdict", {"winner": {"product_index": 0}, "comparison": {}}),
        ("settle_complete", full_payload),
        ("complete", full_payload),
    ]

    # Disable the slowapi decorator for the direct call.
    from app.middleware.rate_limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False, raising=False)

    monkeypatch.setattr(tr, "get_comparison_service", lambda: _StubService(events))

    async def _prefs(uid):
        return {"success": True, "preferences_completed": True, "preferences": {}}
    monkeypatch.setattr(tr, "get_user_preferences", _prefs)

    async def _usage(uid, tok):
        return {"allowed": True, "reason": "", "tier": "free", "remaining": 5}
    monkeypatch.setattr(tr, "check_usage_allowed", _usage)

    fired = []

    def _capture_faf(coro, label):
        try:
            coro.close()  # don't actually schedule; just record intent
        except Exception:
            pass
        fired.append(label)
    monkeypatch.setattr(tr, "fire_and_forget", _capture_faf)

    # Client drops right after the verdict is delivered: is_disconnected returns
    # True on the 3rd check (the settle_complete iteration).
    fake_req = _FakeRequest(disconnect_after=2)

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
        user={"id": "u1", "access_token": "tok"},
    )

    streamed = []
    async for chunk in resp.body_iterator:
        streamed.append(chunk)

    # The client left after the verdict, so only status + verdict were pushed.
    assert any("event: verdict" in c for c in streamed)
    assert not any("event: complete" in c for c in streamed), (
        "complete should NOT have been pushed to the disconnected client"
    )
    # ...but the side effects STILL fired from the finally.
    assert "log_search.text_stream.success" in fired
    assert "save_comparison.text_stream" in fired
    assert "record_comparison.text_stream" in fired


@pytest.mark.asyncio
async def test_full_stream_no_disconnect_still_meters_once(monkeypatch):
    """Control: a client that stays connected meters exactly once (no regression)."""
    full_payload = {
        "products": [{"brand": "A", "name": "1"}],
        "metadata": {"total_cost": 0.01},
    }
    events = [("status", {"progress": 10}), ("settle_complete", full_payload), ("complete", full_payload)]

    from app.middleware.rate_limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False, raising=False)
    monkeypatch.setattr(tr, "get_comparison_service", lambda: _StubService(events))

    async def _prefs(uid):
        return {"success": True, "preferences_completed": True, "preferences": {}}
    monkeypatch.setattr(tr, "get_user_preferences", _prefs)

    async def _usage(uid, tok):
        return {"allowed": True, "reason": "", "tier": "free", "remaining": 5}
    monkeypatch.setattr(tr, "check_usage_allowed", _usage)

    fired = []
    monkeypatch.setattr(tr, "fire_and_forget",
                        lambda coro, label: (coro.close(), fired.append(label)))

    # Never disconnects.
    fake_req = _FakeRequest(disconnect_after=999)

    resp = await tr.text_compare_stream(
        request=fake_req, q="A vs B", product_a=None, product_b=None,
        region="bahrain", specs=True, reviews=True, pros_cons=True,
        nocache=False, selected_category=None,
        user={"id": "u1", "access_token": "tok"},
    )
    async for _chunk in resp.body_iterator:
        pass

    assert fired.count("record_comparison.text_stream") == 1
    assert fired.count("save_comparison.text_stream") == 1
    assert fired.count("log_search.text_stream.success") == 1

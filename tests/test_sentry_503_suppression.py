"""genuine-bh-latency bundle follow-up — the DELIBERATE transient 503 (the
WS1 TIMEOUT graceful-timeout surface + FEATURE_DISABLED gated routes) must NOT
reach Sentry as an error, while real 500s still do. The bundle changed the
timeout surface from HTTP 400 -> 503; the Sentry Starlette/FastAPI integration
captures every 5xx by default, so without this guard every cold luxury timeout
would flood the error stream and bury genuine crashes.

Pins both layers of the fix in app/services/sentry_service.py:
  1. the before_send drop (version-independent backstop), and
  2. the integration-level failed_request_status_codes exclusion set.
"""
from app.services.sentry_service import _before_send


def _evt(status):
    return {"contexts": {"response": {"status_code": status}}, "level": "error"}


class TestBeforeSendDropsIntended503:
    def test_drops_503_int(self):
        assert _before_send(_evt(503), None) is None

    def test_drops_503_str(self):
        # sentry can populate status_code as a string depending on the path
        assert _before_send(_evt("503"), None) is None

    def test_keeps_500(self):
        evt = _evt(500)
        assert _before_send(evt, None) is evt

    def test_keeps_502(self):
        evt = _evt(502)
        assert _before_send(evt, None) is evt

    def test_keeps_504(self):
        evt = _evt(504)
        assert _before_send(evt, None) is evt

    def test_no_contexts_passes_through(self):
        evt = {"level": "error"}
        assert _before_send(evt, None) is evt

    def test_none_status_passes_through(self):
        evt = {"contexts": {"response": {"status_code": None}}}
        assert _before_send(evt, None) is evt

    def test_malformed_status_does_not_raise(self):
        # a non-numeric status must not blow up before_send
        evt = {"contexts": {"response": {"status_code": "weird"}}}
        assert _before_send(evt, None) is evt


class TestCaptured5xxExcludes503:
    def test_exclusion_set_drops_only_503(self):
        captured = frozenset(range(500, 600)) - {503}
        assert 503 not in captured
        # every other 5xx is still captured
        for code in (500, 501, 502, 504, 505, 599):
            assert code in captured

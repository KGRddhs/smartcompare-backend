"""Cap-cut → HTTP surface mapping (rewritten for the WS1 / D2 contract).

HISTORY: this test originally pinned TIMEOUT → HTTP 400 (the S1 baseline's
"http_400 + wall_over_cap=true" cap-cut signature). That 400 was the BUG the
genuine-bh-latency bundle fixes — a valid query that hits the hard cap was
surfaced to the app as BAD_REQUEST with scary copy ("We couldn't … Try again.").

NEW CONTRACT (WS1 fail-fast + D2 surfacing), code-traced:

  1. compare_from_text wraps _compare_from_text_impl in
     asyncio.wait_for(STREAM_HARD_CAP_SECONDS). On TimeoutError it now:
       - returns a best-available PARTIAL ({success:true, metadata.partial:true})
         when >=1 product has usable data, OR
       - returns {success:false, code:"INSUFFICIENT_DATA"} when products
         resolved but neither has data, OR
       - returns {success:false, code:"TIMEOUT", error:<friendly, non-scary>}
         when nothing usable landed at all.
     -- pinned by tests/test_compare_timeout_graceful.py
  2. The route handlers (GET + POST /text/compare) map the result code via
     _surface_comparison_failure:
       - success:true            → 200 (the partial path; never reaches the map)
       - CONTENT_UNAVAILABLE     → 200 structured body
       - TIMEOUT                 → HTTP 503, body code "TIMEOUT" (transient)
       - INSUFFICIENT_DATA / etc → HTTP 400
     -- pinned HERE.

So the cap-cut signature is now **http_503 + code "TIMEOUT"** (NOT http_400).
This test guards step 2 so the mapping can't silently regress back to 400 (or
collapse TIMEOUT into FEATURE_DISABLED via the 503 default in STATUS_CODE_MAP).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

# A true hard-cap timeout with NO usable partial data — the only case that now
# surfaces code:"TIMEOUT" from the service. Copy obeys the no-scary contract.
TIMEOUT_RESULT = {
    "success": False,
    "error": "Still gathering prices — give it another tap in a moment.",
    "code": "TIMEOUT",
    "total_cost": 0.0,
}

INSUFFICIENT_RESULT = {
    "success": False,
    "error": "Comparison data was incomplete — choose different products.",
    "code": "INSUFFICIENT_DATA",
    "total_cost": 0.0,
}


class TestCapCutMapsTo503:
    def test_get_compare_timeout_maps_to_http_503(self):
        """GET /text/compare maps a TIMEOUT service result to HTTP 503 — the
        new cap-cut signature (transient/retryable), NOT 400."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=TIMEOUT_RESULT)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC", "nocache": "true"},
            )
        assert resp.status_code == 503
        body = resp.json()
        # error_handler must surface the explicit code, NOT the 503-default
        # "FEATURE_DISABLED".
        assert body["code"] == "TIMEOUT"
        assert body["success"] is False

    def test_post_compare_timeout_maps_to_http_503(self):
        """POST shares the mapping (dual-shape parity)."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=TIMEOUT_RESULT)
            resp = client.post(
                "/api/v1/text/compare",
                json={"query": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        assert resp.status_code == 503
        assert resp.json()["code"] == "TIMEOUT"

    def test_timeout_copy_has_no_forbidden_vocab(self):
        """D2 — the TIMEOUT body must not leak scary copy (no 'couldn't' /
        'try again' / 'Failed to')."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=TIMEOUT_RESULT)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        text = resp.text.lower()
        assert "couldn't" not in text
        assert "try again" not in text
        assert "failed to" not in text

    def test_insufficient_data_maps_to_http_400(self):
        """INSUFFICIENT_DATA (both products empty) stays at 400 with its code
        preserved — distinct from the transient TIMEOUT (503)."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=INSUFFICIENT_RESULT)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "qwerty vs asdf"},
            )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INSUFFICIENT_DATA"

    def test_content_unavailable_is_200_body(self):
        """CONTENT_UNAVAILABLE early-returns the structured body (200) — the
        FE reads the body, not the status. Unchanged by WS1."""
        content_result = {
            "success": False,
            "error": "blocked",
            "code": "CONTENT_UNAVAILABLE",
            "layer": "L1",
        }
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=content_result)
            resp = client.get("/api/v1/text/compare", params={"q": "something"})
        assert resp.status_code == 200
        assert resp.json()["code"] == "CONTENT_UNAVAILABLE"

    def test_partial_success_is_200(self):
        """A best-available PARTIAL has success:true + metadata.partial:true and
        is served at HTTP 200 like any normal result — it never reaches the
        failure map."""
        partial_result = {
            "success": True,
            "products": [
                {"brand": "Carrier", "name": "1.5T AC"},
                {"brand": "LG", "name": "1.5T AC"},
            ],
            "overview": {}, "specs": {}, "reviews": {}, "scoring": {},
            "metadata": {"partial": True},
        }
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=partial_result)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        assert resp.status_code == 200
        assert resp.json()["metadata"]["partial"] is True

    def test_success_result_is_200(self):
        """Sanity anchor: a normal successful comparison is 200."""
        ok_result = {
            "success": True,
            "products": [
                {"brand": "Carrier", "name": "1.5T AC"},
                {"brand": "LG", "name": "1.5T AC"},
            ],
            "overview": {}, "specs": {}, "reviews": {}, "scoring": {},
            "metadata": {},
        }
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=ok_result)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        assert resp.status_code == 200

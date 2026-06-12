"""I5.2 (Bundle B S2) — pin the http_400 == cap-cut mechanism.

The S1 baseline's 39 http_400 rows (all carrying wall_over_cap=true) are the
30s outer wait_for surfacing as a 400. The full chain, code-traced:

  1. compare_from_text wraps _compare_from_text_impl in
     asyncio.wait_for(STREAM_HARD_CAP_SECONDS). On TimeoutError it RETURNS
     {success:false, code:"TIMEOUT"} (NOT a raise; HTTP-200 at the service).
     -- pinned by tests/test_compare_from_text_hard_cap.py
  2. The route handlers (GET + POST /text/compare) see not result["success"]
     and -- because code != "CONTENT_UNAVAILABLE" -- raise HTTPException(400).
     -- pinned HERE.
  3. eval_runner records http_{status} for non-200 (eval_runner.py:505) and
     wall_over_cap = wall_ms/1000 > cap (eval_runner.py:574).

So a cap-cut is observed as http_400 + wall_over_cap=true, exactly the
baseline signature. This test guards step 2 so the mapping can't silently
change (e.g. someone switching TIMEOUT to 200/504) and invalidate the
error-recovery arithmetic the S2 plan rests on.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

TIMEOUT_RESULT = {
    "success": False,
    "error": "We couldn't finish this comparison in time. Try again.",
    "code": "TIMEOUT",
    "total_cost": 0.0,
}


class TestCapCutMapsTo400:
    def test_get_compare_timeout_maps_to_http_400(self):
        """The eval endpoint (GET /text/compare) maps a TIMEOUT service result
        to HTTP 400 — the exact baseline http_400 signature."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=TIMEOUT_RESULT)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "Carrier 1.5T AC vs LG 1.5T AC", "nocache": "true"},
            )
        assert resp.status_code == 400

    def test_post_compare_timeout_maps_to_http_400(self):
        """The POST handler shares the mapping (dual-shape parity)."""
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=TIMEOUT_RESULT)
            resp = client.post(
                "/api/v1/text/compare",
                json={"query": "Carrier 1.5T AC vs LG 1.5T AC"},
            )
        assert resp.status_code == 400

    def test_content_unavailable_is_NOT_400(self):
        """Guard the discriminator: CONTENT_UNAVAILABLE early-returns the
        structured body (200), so it is NOT lumped into the http_400 cap-cut
        bucket. Confirms the 400 branch is specifically the non-CONTENT path
        (which TIMEOUT takes)."""
        content_result = {
            "success": False,
            "error": "blocked",
            "code": "CONTENT_UNAVAILABLE",
            "layer": "L1",
        }
        with patch("app.api.text_routes.get_comparison_service") as m_svc:
            inst = m_svc.return_value
            inst.compare_from_text = AsyncMock(return_value=content_result)
            resp = client.get(
                "/api/v1/text/compare",
                params={"q": "something"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "CONTENT_UNAVAILABLE"

    def test_success_result_is_200(self):
        """Sanity anchor: a successful comparison is 200 (so the 400 above is
        specifically the failure mapping, not a blanket status)."""
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

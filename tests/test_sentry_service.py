"""Tests for app.services.sentry_service — before_send scrubbing.

Bundle D Task 1.B.6 (R21) adds query-string scrubbing for free-text
inputs (?q=, ?query=, ?email=, ?search=, ?text=) so user queries don't
leak into Sentry events. Preserves bookkeeping query params (?nocache=,
?token=) since `token` is already handled by the wholesale-key denylist
in `_scrub_dict`.
"""
import re


class TestSensitivePatternScrubbing:
    """Pre-Bundle-D behavior — these MUST continue to GREEN."""

    def test_before_send_redacts_jwt_in_exception_value(self):
        from app.services.sentry_service import _before_send
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        event = {"exception": {"values": [{"value": f"JWT was {token}"}]}}
        scrubbed = _before_send(event, hint={})
        assert "[JWT_REDACTED]" in scrubbed["exception"]["values"][0]["value"]
        assert token not in scrubbed["exception"]["values"][0]["value"]

    def test_before_send_redacts_authorization_header(self):
        from app.services.sentry_service import _before_send
        event = {"request": {"headers": {"Authorization": "Bearer eyJhbGc.eyJ.sig"}}}
        scrubbed = _before_send(event, hint={})
        assert scrubbed["request"]["headers"]["Authorization"] == "[REDACTED]"


class TestQueryStringScrubbing:
    """Bundle D Task 1.B.6 (R21) — new behavior under test."""

    def test_before_send_scrubs_query_string_in_request_url(self):
        from app.services.sentry_service import _before_send
        event = {
            "request": {
                "url": "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone%2016%20vs%20Galaxy%20S25",
            },
        }
        scrubbed = _before_send(event, hint={})
        url = scrubbed["request"]["url"]
        assert "iPhone" not in url
        assert "Galaxy" not in url
        # The path portion must be intact
        assert "/api/v1/text/compare" in url
        # Marker proves the scrubber actually ran
        assert "q=[QUERY_REDACTED]" in url

    def test_before_send_scrubs_email_query_param(self):
        from app.services.sentry_service import _before_send
        event = {
            "request": {
                "url": "https://example.com/api/v1/auth/forgot-password?email=ahmed%40example.com",
            },
        }
        scrubbed = _before_send(event, hint={})
        assert "ahmed" not in scrubbed["request"]["url"]
        assert "example.com/api/v1/auth/forgot-password" in scrubbed["request"]["url"]
        assert "email=[QUERY_REDACTED]" in scrubbed["request"]["url"]

    def test_before_send_scrubs_query_text_search_variants(self):
        from app.services.sentry_service import _before_send
        # Each of these param names should be scrubbed.
        for param in ("q", "query", "email", "search", "text"):
            event = {"request": {"url": f"https://example.com/x?{param}=secret-value-123"}}
            scrubbed = _before_send(event, hint={})
            assert "secret-value-123" not in scrubbed["request"]["url"], (
                f"param {param!r} not scrubbed in URL"
            )
            assert f"{param}=[QUERY_REDACTED]" in scrubbed["request"]["url"]

    def test_before_send_preserves_nocache_query_param(self):
        """`?nocache=true` is a bookkeeping flag, NOT PII."""
        from app.services.sentry_service import _before_send
        event = {"request": {"url": "https://example.com/api/v1/text/compare?nocache=true"}}
        scrubbed = _before_send(event, hint={})
        assert "nocache=true" in scrubbed["request"]["url"]

    def test_before_send_preserves_pagination_query_params(self):
        """Pagination + filter params are non-PII metadata."""
        from app.services.sentry_service import _before_send
        event = {"request": {"url": "https://example.com/api/v1/comparisons?limit=20&offset=0&sort=desc"}}
        scrubbed = _before_send(event, hint={})
        assert "limit=20" in scrubbed["request"]["url"]
        assert "offset=0" in scrubbed["request"]["url"]
        assert "sort=desc" in scrubbed["request"]["url"]

    def test_before_send_scrubs_multi_param_url_partially(self):
        """Mixed URL: scrub `q=`, keep `limit=`."""
        from app.services.sentry_service import _before_send
        event = {"request": {"url": "https://example.com/search?q=private+stuff&limit=10"}}
        scrubbed = _before_send(event, hint={})
        url = scrubbed["request"]["url"]
        assert "private" not in url
        assert "q=[QUERY_REDACTED]" in url
        assert "limit=10" in url

    def test_before_send_scrubs_query_in_breadcrumb_url(self):
        """Breadcrumb URLs (sentry-sdk httpx integration) also get scrubbed."""
        from app.services.sentry_service import _strip_tokens_from_breadcrumb
        crumb = {
            "data": {"url": "https://api.example.com/v1/search?q=iPhone+16"},
        }
        scrubbed = _strip_tokens_from_breadcrumb(crumb, hint={})
        assert "iPhone" not in scrubbed["data"]["url"]
        assert "q=[QUERY_REDACTED]" in scrubbed["data"]["url"]

    def test_before_send_handles_url_without_query_string(self):
        """No `?` in URL = no-op."""
        from app.services.sentry_service import _before_send
        event = {"request": {"url": "https://example.com/api/v1/health"}}
        scrubbed = _before_send(event, hint={})
        assert scrubbed["request"]["url"] == "https://example.com/api/v1/health"

    def test_before_send_handles_missing_request_url(self):
        """Event without `request.url` shouldn't crash."""
        from app.services.sentry_service import _before_send
        event = {"request": {"headers": {}}}
        # Should not raise
        scrubbed = _before_send(event, hint={})
        assert scrubbed is not None

    def test_query_redacted_marker_is_distinct_from_token_redacted(self):
        """[QUERY_REDACTED] is its own marker — easier to grep in Sentry UI."""
        from app.services import sentry_service
        assert "QUERY_REDACTED" not in sentry_service._SENSITIVE_KEY_FRAGMENTS  # not a key-frag, it's a replacement marker


class TestRawQueryStringField:
    """Bundle D R21 follow-up (Frontend cross-QA on c12a7c6) — modern
    sentry-python populates `event.request.query_string` separately from
    `event.request.url` as raw `key=val&key2=val2` (no leading `?`).

    The lookbehind in _QUERY_STRING_SCRUB_PATTERN requires `?` or `&`
    BEFORE the param name, so the very first param of a raw query_string
    would slip through `_scrub_query_string` (which keeps the lookbehind
    guard intact for URL safety).

    `_scrub_raw_query_string` normalizes by prepending `?`, applies the
    same regex, then strips the prepended char.
    """

    def test_raw_query_string_first_param_scrubbed(self):
        from app.services.sentry_service import _scrub_raw_query_string
        # First param is q= — would slip through _scrub_query_string
        result = _scrub_raw_query_string("q=iPhone+16&limit=20")
        assert result == "q=[QUERY_REDACTED]&limit=20"

    def test_raw_query_string_mixed_params(self):
        from app.services.sentry_service import _scrub_raw_query_string
        result = _scrub_raw_query_string("limit=20&q=secret&offset=0")
        # Only q is a PII param
        assert "secret" not in result
        assert "q=[QUERY_REDACTED]" in result
        assert "limit=20" in result
        assert "offset=0" in result

    def test_raw_query_string_all_pii_params(self):
        from app.services.sentry_service import _scrub_raw_query_string
        for param in ("q", "query", "email", "search", "text"):
            result = _scrub_raw_query_string(f"{param}=secret-value-123")
            assert "secret-value-123" not in result
            assert f"{param}=[QUERY_REDACTED]" in result

    def test_raw_query_string_bookkeeping_preserved(self):
        from app.services.sentry_service import _scrub_raw_query_string
        result = _scrub_raw_query_string("nocache=true&limit=20&offset=0&sort=desc")
        # None of these are PII — all preserved
        assert result == "nocache=true&limit=20&offset=0&sort=desc"

    def test_raw_query_string_empty_returns_empty(self):
        from app.services.sentry_service import _scrub_raw_query_string
        assert _scrub_raw_query_string("") == ""

    def test_raw_query_string_none_returns_none(self):
        from app.services.sentry_service import _scrub_raw_query_string
        # None passthrough — caller may receive None from some sentry-sdk versions
        assert _scrub_raw_query_string(None) is None

    def test_raw_query_string_bytes_decoded(self):
        """Some sentry-sdk versions populate query_string as bytes."""
        from app.services.sentry_service import _scrub_raw_query_string
        result = _scrub_raw_query_string(b"q=iPhone+16")
        assert result == "q=[QUERY_REDACTED]"

    def test_before_send_scrubs_request_query_string_field(self):
        """End-to-end: _before_send must scrub event.request.query_string
        the way it scrubs event.request.url."""
        from app.services.sentry_service import _before_send
        event = {
            "request": {
                "url": "https://example.com/api/v1/text/compare?q=outer",
                "query_string": "q=inner&limit=20",
            },
        }
        scrubbed = _before_send(event, hint={})
        assert "outer" not in scrubbed["request"]["url"]
        assert "inner" not in scrubbed["request"]["query_string"]
        assert scrubbed["request"]["query_string"] == "q=[QUERY_REDACTED]&limit=20"

    def test_before_send_query_string_field_missing_does_not_crash(self):
        """Older sentry-sdk versions don't populate query_string — must be
        a clean no-op, not a KeyError."""
        from app.services.sentry_service import _before_send
        event = {"request": {"url": "https://example.com/health"}}
        scrubbed = _before_send(event, hint={})
        assert scrubbed["request"]["url"] == "https://example.com/health"
        assert "query_string" not in scrubbed["request"]

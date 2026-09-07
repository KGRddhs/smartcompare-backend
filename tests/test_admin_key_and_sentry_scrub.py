"""W1-1 — the admin key stops leaving the building on an unauthenticated request.

Findings ``CR-SECURITY-04`` (the ``TypeError``) + ``CR-SECURITY-03`` (the scrub gap).
Sources under test: ``app/api/admin_routes.py::verify_admin_key`` and
``app/services/sentry_service.py`` (``_before_send`` / ``init_sentry``).

THE CHAIN THESE TESTS CLOSE (every link re-measured on this worktree, python
3.12.9 = ``runtime.txt``, installed sentry-sdk 2.54.0):

1. ``hmac.compare_digest`` RAISES ``TypeError: comparing strings with non-ASCII
   characters is not supported`` for ``"é"`` / ``"ك"`` / ``"\\xff"`` and returns
   False for ``"wrong"`` / ``""``.
2. HTTP header bytes reach the handler latin-1 decoded, so ANY byte >= 0x80 in
   ``X-Admin-Key`` produces a non-ASCII ``str``. Measured through the real app:
   ``GET /api/v1/admin/stats/daily`` with header bytes ``b"\\xc3\\xa9"`` →
   **HTTP 500**, and the ErrorHandlerMiddleware log shows the ``TypeError``
   raised at ``admin_routes.py:37``.
3. ``sentry_sdk`` ``include_local_variables`` default is **True** (measured:
   ``sentry_sdk.consts.DEFAULT_OPTIONS["include_local_variables"] is True``) and
   ``init_sentry`` does not set it, so the captured 500 carries frame locals.
4. The raising frame is ``verify_admin_key`` and its locals are ``x_admin_key``
   and ``expected`` — the real ``ADMIN_API_KEY``. Measured with
   ``sentry_sdk.utils.event_from_exception``:
   ``vars = {'x_admin_key': "'é'", 'expected': "'SUPER-SECRET-ADMIN-KEY-123'"}``
   and the secret survives ``_before_send`` verbatim.

NOTE ON THE SCRUB TESTS' SECRET SHAPE. The spec's fix (3) extends ``_before_send``
to the unwalked regions "by applying the EXISTING ``_scrub_string`` /
``_scrub_dict`` helpers". Those helpers redact by PATTERN (or by sensitive key
NAME), so a secret only disappears if it looks like one. The admin key used here
is therefore a 64-char lowercase hex string — a realistic ``ADMIN_API_KEY`` shape
and one the existing ``[a-f0-9]{32,}`` pattern already recognises. These tests
prove the REGIONS get walked; they deliberately do not claim that an
arbitrarily-shaped admin key would be caught by pattern-scrubbing, which is
exactly why ``include_local_variables=False`` (test class
``TestInitSentryDisablesLocalVariables``) is the primary fix and not the belt.
"""
import hmac
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.admin_routes import verify_admin_key
from app.services.sentry_service import _before_send


# A realistic ADMIN_API_KEY: 64 lowercase hex chars.
ADMIN_KEY = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
# A syntactically real JWT (header.payload.signature, base64url).
USER_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFobWVkIn0"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)

# Every byte >= 0x80 in a header decodes latin-1 into a non-ASCII str.
NON_ASCII_KEYS = ["é", "ك", "\xff"]
ASCII_REJECTS = ["", "wrong"]


# ---------------------------------------------------------------------------
# 1 + 2 — verify_admin_key never raises TypeError; it always 403s
# ---------------------------------------------------------------------------

class TestVerifyAdminKeyRejectsWithout500:
    """Every rejected key must surface as HTTPException(403), never TypeError."""

    @pytest.mark.parametrize("supplied", NON_ASCII_KEYS + ASCII_REJECTS)
    def test_wrong_key_raises_403_not_typeerror(self, supplied, monkeypatch):
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        try:
            result = verify_admin_key(x_admin_key=supplied)
        except HTTPException as exc:
            assert exc.status_code == 403, (
                f"{supplied!r} rejected with {exc.status_code}, expected 403"
            )
            return
        except TypeError as exc:
            pytest.fail(
                "verify_admin_key raised TypeError for a header value the "
                f"network can deliver ({supplied!r}): {exc}. That TypeError "
                "escapes the dependency, becomes a 500, and the 500 is captured "
                "by Sentry carrying ADMIN_API_KEY in this frame's locals."
            )
        pytest.fail(
            f"verify_admin_key ACCEPTED {supplied!r} against a different "
            f"ADMIN_API_KEY (returned {result!r}) — that is a skeleton key."
        )

    def test_detail_string_is_preserved(self, monkeypatch):
        """Preserve: a wrong key is still 403 with the same detail string."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        with pytest.raises(HTTPException) as excinfo:
            verify_admin_key(x_admin_key="wrong")
        assert excinfo.value.detail == "Invalid admin key"

    def test_correct_key_still_returns_true(self, monkeypatch):
        """Preserve: the happy path is untouched."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        assert verify_admin_key(x_admin_key=ADMIN_KEY) is True

    def test_unset_admin_key_is_not_a_skeleton_key(self, monkeypatch):
        """An empty ADMIN_API_KEY env must 403 even for an empty header.

        Pins the existing ``if not expected`` guard: a misconfigured deploy must
        not turn "" into a key that opens the admin surface.
        """
        monkeypatch.setenv("ADMIN_API_KEY", "")
        with pytest.raises(HTTPException) as excinfo:
            verify_admin_key(x_admin_key="")
        assert excinfo.value.status_code == 403

    def test_comparison_is_still_constant_time(self):
        """Preserve: the comparison stays constant-time (no ``==``).

        A byte-encoding fix must keep ``hmac.compare_digest`` — an ``==`` or a
        length short-circuit would trade a 500 for a timing oracle.
        """
        import inspect

        src = inspect.getsource(verify_admin_key)
        assert "compare_digest" in src, (
            "verify_admin_key no longer uses hmac.compare_digest — the "
            "comparison must stay constant-time."
        )


# ---------------------------------------------------------------------------
# 3 + 4 — the live route: 403, never 500, never 422
# ---------------------------------------------------------------------------

ADMIN_ROUTE = "/api/v1/admin/stats/daily"


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


class TestAdminRouteNeverReturns500:
    """The route-level pin. A 403 is never captured by Sentry; a 500 is."""

    @pytest.mark.parametrize(
        "raw_header",
        [
            pytest.param(b"\xc3\xa9", id="utf8-e-acute"),
            pytest.param(b"\xd9\x83", id="utf8-arabic-kaf"),
            pytest.param(b"\xff", id="raw-0xff"),
        ],
    )
    def test_non_ascii_admin_key_header_is_403(self, client, monkeypatch, raw_header):
        """RED: 500.

        The header value is passed as BYTES on purpose. httpx encodes a ``str``
        header value as ASCII and raises ``UnicodeEncodeError`` client-side
        before a request is ever built, so a ``str`` here would test the test
        client, not the app. Bytes reproduce what the wire actually delivers:
        measured, ``b"\\xc3\\xa9"`` arrives at the handler as ``'Ã©'``.
        """
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(ADMIN_ROUTE, headers={"X-Admin-Key": raw_header})
        assert resp.status_code != 429, "rate limiter fired — re-run this file alone"
        assert resp.status_code == 403, (
            f"expected 403, got {resp.status_code}: {resp.text[:200]}. A 500 "
            "here means the TypeError escaped, which means Sentry captured the "
            "event and the event carries ADMIN_API_KEY in the frame locals."
        )

    def test_missing_admin_key_header_is_403(self, client, monkeypatch):
        """RED: 422.

        A 422 tells an unauthenticated caller that the header is the thing being
        checked, and it is a different response shape for what is the same
        "you are not an admin" answer.
        """
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(ADMIN_ROUTE)
        assert resp.status_code != 429, "rate limiter fired — re-run this file alone"
        assert resp.status_code == 403, (
            f"expected 403 for an absent X-Admin-Key, got {resp.status_code}: "
            f"{resp.text[:200]}"
        )
        assert resp.json().get("code") == "FORBIDDEN"

    def test_wrong_admin_key_header_is_still_403(self, client, monkeypatch):
        """Preserve: the already-correct rejection path does not move."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(ADMIN_ROUTE, headers={"X-Admin-Key": "definitely-wrong"})
        assert resp.status_code == 403, resp.text
        assert resp.json().get("code") == "FORBIDDEN"


class TestAdminStaticMountNeverReturns500:
    """SCOPE NOTE — NOT in the W1-1 spec's file list; found by testing it.

    The spec names ``app/api/admin_routes.py:34-38`` as the only ``TypeError``
    site, but ``_AdminAuthenticatedStaticFiles`` in ``app/main.py`` runs the
    SAME unguarded ``hmac.compare_digest`` twice on caller-controlled strings:

      * ``app/main.py:234`` — ``compare_digest(x_admin, expected)`` where
        ``x_admin`` is the ``X-Admin-Key`` header the mount itself decodes
        latin-1 at ``:229``.
      * ``app/main.py:243`` — ``compare_digest(password, expected)`` from the
        HTTP Basic password, decoded UTF-8 at ``:241``. The surrounding
        ``except (binascii.Error, UnicodeDecodeError)`` does not catch
        ``TypeError``.

    Both reproduce as HTTP 500 on the UNAUTHENTICATED ``/admin/*`` mount, so
    both feed the same Sentry capture with ``expected`` (= ADMIN_API_KEY) in the
    frame locals — ``:243`` additionally carries ``password``. Fixing only
    ``verify_admin_key`` leaves the unit's own claim ("the admin key stops
    leaving the building on an unauthenticated request") false. Raised for the
    reviewer: keep here, or split into its own unit.
    """

    STATIC_PATH = "/admin/cohort.html"

    @pytest.mark.parametrize(
        "raw_header",
        [
            pytest.param(b"\xc3\xa9", id="utf8-e-acute"),
            pytest.param(b"\xff", id="raw-0xff"),
        ],
    )
    def test_non_ascii_header_on_static_mount_is_not_500(
        self, client, monkeypatch, raw_header
    ):
        """RED: 500 raised at app/main.py:234."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(self.STATIC_PATH, headers={"X-Admin-Key": raw_header})
        assert resp.status_code == 401, (
            f"expected 401 (the mount's own reject shape), got {resp.status_code}"
        )

    def test_non_ascii_basic_password_on_static_mount_is_not_500(
        self, client, monkeypatch
    ):
        """RED: 500 raised at app/main.py:243."""
        import base64

        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        creds = base64.b64encode("operator:é".encode("utf-8")).decode("ascii")
        resp = client.get(
            self.STATIC_PATH, headers={"Authorization": f"Basic {creds}"}
        )
        assert resp.status_code == 401, (
            f"expected 401 (the mount's own reject shape), got {resp.status_code}"
        )

    def test_wrong_ascii_key_on_static_mount_is_still_401(self, client, monkeypatch):
        """Preserve: the already-correct reject path does not move."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(self.STATIC_PATH, headers={"X-Admin-Key": "nope"})
        assert resp.status_code == 401

    def test_correct_key_on_static_mount_still_serves(self, client, monkeypatch):
        """Preserve: the happy path is untouched."""
        monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
        resp = client.get(self.STATIC_PATH, headers={"X-Admin-Key": ADMIN_KEY})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5 — _before_send must walk every region that can carry a secret
# ---------------------------------------------------------------------------

def _region_event(region: str) -> dict:
    """An otherwise-minimal event carrying ADMIN_KEY / USER_JWT in ONE region.

    One region per event so a removed scrub reddens exactly one test and names
    the region it broke.
    """
    base = {"level": "error", "contexts": {"response": {"status_code": 500}}}

    if region == "exception_value":
        base["exception"] = {"values": [{"value": f"admin key was {ADMIN_KEY}"}]}
    elif region == "frame_vars":
        base["exception"] = {
            "values": [
                {
                    "type": "TypeError",
                    "value": "comparing strings with non-ASCII characters is not supported",
                    "stacktrace": {
                        "frames": [
                            {
                                "function": "verify_admin_key",
                                "filename": "app/api/admin_routes.py",
                                "vars": {
                                    "x_admin_key": "'Ã©'",
                                    "expected": f"'{ADMIN_KEY}'",
                                },
                            }
                        ]
                    },
                }
            ]
        }
    elif region == "breadcrumb_data":
        base["breadcrumbs"] = {"values": [{"data": {"note": f"key={ADMIN_KEY}"}}]}
    elif region == "breadcrumb_message":
        base["breadcrumbs"] = {"values": [{"message": f"auth with {USER_JWT}"}]}
    elif region == "request_headers":
        base["request"] = {
            "headers": {"Authorization": f"Bearer {USER_JWT}", "X-Admin-Key": ADMIN_KEY}
        }
    elif region == "request_url":
        base["request"] = {"url": f"https://api.example.com/v1/admin?q={ADMIN_KEY}"}
    elif region == "request_query_string":
        base["request"] = {"query_string": f"q={ADMIN_KEY}"}
    elif region == "request_data":
        base["request"] = {"data": {"payload": f"sent {ADMIN_KEY}", "jwt": USER_JWT}}
    elif region == "request_cookies":
        base["request"] = {"cookies": {"session": USER_JWT, "adm": ADMIN_KEY}}
    elif region == "extra":
        base["extra"] = {"debug_note": f"expected={ADMIN_KEY}", "jwt": USER_JWT}
    elif region == "contexts":
        base["contexts"]["runtime"] = {
            "name": "CPython",
            "version": "3.12.9",
            "build": f"deployed with {ADMIN_KEY}",
        }
    elif region == "logentry":
        base["logentry"] = {
            "message": f"admin auth failed for {ADMIN_KEY}",
            "params": [USER_JWT],
        }
    elif region == "tags":
        base["tags"] = {"admin_key_used": ADMIN_KEY, "session_jwt": USER_JWT}
    elif region == "user":
        base["user"] = {"id": "u-1", "note": f"bearer {USER_JWT}", "adm": ADMIN_KEY}
    else:  # pragma: no cover - guards a typo in the parametrize list
        raise AssertionError(f"unknown region {region!r}")
    return base


ALL_REGIONS = [
    # Already covered today — these five must STAY green.
    "exception_value",
    "breadcrumb_data",
    "breadcrumb_message",
    "request_headers",
    "request_url",
    "request_query_string",
    # Never walked today — these are the RED ones.
    "frame_vars",
    "request_data",
    "request_cookies",
    "extra",
    "contexts",
    "logentry",
    "tags",
    "user",
]


class TestBeforeSendWalksEveryRegion:
    """CR-SECURITY-03: the scrub covered 5 regions of 12+."""

    @pytest.mark.parametrize("region", ALL_REGIONS)
    def test_region_carries_no_secret_after_scrub(self, region):
        scrubbed = _before_send(_region_event(region), {})
        assert scrubbed is not None, "the 500 event must not be dropped"
        blob = json.dumps(scrubbed, default=str)
        assert ADMIN_KEY not in blob, (
            f"ADMIN_API_KEY survives _before_send in region {region!r} — "
            "_before_send never walks it."
        )
        assert USER_JWT not in blob, (
            f"a user JWT survives _before_send in region {region!r}."
        )

    def test_event_carrying_the_secret_everywhere_ships_clean(self):
        """The spec's combined pin: every region at once, zero occurrences.

        Merged by hand rather than by looping ``_region_event`` and assigning:
        several regions share a top-level key (``request.data`` /
        ``request.cookies`` / ``request.url`` …, ``exception.values[]``,
        ``breadcrumbs.values[]``), so a naive per-key assignment would silently
        drop all but the last of each family and under-count the leak.
        """
        merged = {"level": "error", "contexts": {"response": {"status_code": 500}}}
        for region in ALL_REGIONS:
            piece = _region_event(region)
            for key, value in piece.items():
                if key in ("level", "contexts") and key in merged:
                    if key == "contexts":
                        merged["contexts"].update(value)
                    continue
                if key in ("exception", "breadcrumbs") and key in merged:
                    merged[key]["values"].extend(value["values"])
                elif key == "request" and key in merged:
                    merged["request"].update(value)
                else:
                    merged[key] = value

        # Sanity: the merge really did keep every family member.
        assert len(merged["exception"]["values"]) == 2
        assert len(merged["breadcrumbs"]["values"]) == 2
        assert {"headers", "url", "query_string", "data", "cookies"} <= set(
            merged["request"]
        )

        scrubbed = _before_send(merged, {})
        assert scrubbed is not None
        blob = json.dumps(scrubbed, default=str)
        assert blob.count(ADMIN_KEY) == 0, (
            f"ADMIN_API_KEY appears {blob.count(ADMIN_KEY)}x in the scrubbed event"
        )
        assert blob.count(USER_JWT) == 0, (
            f"a user JWT appears {blob.count(USER_JWT)}x in the scrubbed event"
        )


# ---------------------------------------------------------------------------
# 6 — the new walk must not disturb the 503 drop or flatten contexts
# ---------------------------------------------------------------------------

class TestTraceCorrelationSurvivesTheScrub:
    """Fable review addition (W1-1), from an adversarial finding — reproduced.

    A Sentry ``trace_id`` is ``uuid4().hex``: 32 lowercase hex characters. The
    pre-existing generic token pattern ``[a-f0-9]{32,}`` matches that
    unconditionally, so walking ``contexts`` with ``_scrub_dict`` rewrote
    ``contexts.trace.trace_id`` to ``[TOKEN_REDACTED]`` on EVERY error event.
    Relay treats an invalid trace_id as a normalization error and drops the
    trace context, so every backend error would have been silently orphaned
    from its transaction and from the mobile->backend distributed trace.

    That is the observability this campaign uses to read its own canaries, and
    it would have been degraded by the OPTIONAL belt half of a security fix.
    The primary fix (include_local_variables=False) never had this cost.
    """

    def test_trace_ids_are_preserved(self):
        import uuid
        from app.services.sentry_service import _before_send

        tid, sid = uuid.uuid4().hex, uuid.uuid4().hex[:16]
        event = {"contexts": {"trace": {"trace_id": tid, "span_id": sid,
                                        "op": "http.server"}}}
        out = _before_send(event, None)
        assert out["contexts"]["trace"]["trace_id"] == tid
        assert out["contexts"]["trace"]["span_id"] == sid

    def test_trace_data_is_still_scrubbed(self):
        """Only the SDK-generated correlation ids come back. `trace.data`
        carries app-set span attributes and stays scrubbed."""
        import uuid, json
        from app.services.sentry_service import _before_send

        tid = uuid.uuid4().hex
        event = {"contexts": {"trace": {
            "trace_id": tid, "op": "http.server",
            "data": {"api_key": "sk-proj-SECRETVALUE"}}}}
        out = _before_send(event, None)
        assert out["contexts"]["trace"]["trace_id"] == tid
        assert "SECRETVALUE" not in json.dumps(out["contexts"]["trace"]["data"])

    def test_other_contexts_still_scrubbed_and_intact(self):
        import json
        from app.services.sentry_service import _before_send

        event = {"contexts": {"runtime": {"name": "CPython", "version": "3.12.9"},
                              "custom": {"api_key": "sk-proj-SECRETVALUE"}}}
        out = _before_send(event, None)
        assert out["contexts"]["runtime"]["name"] == "CPython"
        assert "SECRETVALUE" not in json.dumps(out)


class TestLogentryParamsTupleIsScrubbed:
    """Fable review addition (W1-1).

    The logging integration assigns ``event["logentry"]["params"] = record.args``
    and ``record.args`` is a TUPLE — measured, by reading the SDK's own
    ``EventHandler._emit`` source and constructing a ``LogRecord``. ``_scrub_dict``
    recursed into dicts and lists but passed tuples through the ``else`` branch
    untouched, so this unit's new ``logentry`` walk still shipped a token logged
    as a format argument. That is the same defect this unit exists to close, one
    container type over.
    """

    def test_secret_in_a_tuple_param_is_redacted(self):
        from app.services.sentry_service import _scrub_dict
        import json

        out = _scrub_dict(
            {"logentry": {"message": "token=%s uid=%s",
                          "params": ("sk-proj-SECRETVALUE", "u1")}}
        )
        assert "SECRETVALUE" not in json.dumps(out)
        # Non-secret params survive: this must not become a blanket blank.
        assert "u1" in json.dumps(out)

    def test_before_send_scrubs_a_tuple_logentry_param(self):
        from app.services.sentry_service import _before_send
        import json

        event = {"logentry": {"message": "token=%s",
                              "params": ("sk-proj-SECRETVALUE",)}}
        out = _before_send(event, None)
        assert "SECRETVALUE" not in json.dumps(out)


class TestBeforeSendPreservesTriageMetadata:
    """Do NOT blank whole regions. Scrub the patterns inside them."""

    def test_still_drops_deliberate_503(self):
        event = {"contexts": {"response": {"status_code": 503}}, "level": "error"}
        assert _before_send(event, None) is None

    def test_still_drops_503_as_string(self):
        event = {"contexts": {"response": {"status_code": "503"}}, "level": "error"}
        assert _before_send(event, None) is None

    def test_still_returns_the_event_for_500(self):
        event = {"contexts": {"response": {"status_code": 500}}, "level": "error"}
        assert _before_send(event, None) is not None

    def test_contexts_are_not_flattened(self):
        """The 503 branch READS contexts.response.status_code — and runtime/OS
        metadata is what makes an event triageable. Neither may be blanked."""
        event = {
            "contexts": {
                "response": {"status_code": 500},
                "runtime": {"name": "CPython", "version": "3.12.9"},
                "os": {"name": "Linux"},
            },
            "level": "error",
        }
        scrubbed = _before_send(event, None)
        assert scrubbed is not None
        assert scrubbed["contexts"]["response"]["status_code"] == 500
        assert scrubbed["contexts"]["runtime"]["name"] == "CPython"
        assert scrubbed["contexts"]["runtime"]["version"] == "3.12.9"
        assert scrubbed["contexts"]["os"]["name"] == "Linux"

    def test_non_secret_extra_and_tags_survive(self):
        event = {
            "contexts": {"response": {"status_code": 500}},
            "extra": {"route": "/api/v1/admin/stats/daily", "days": 30},
            "tags": {"environment": "production"},
            "user": {"id": "u-1"},
        }
        scrubbed = _before_send(event, None)
        assert scrubbed["extra"]["route"] == "/api/v1/admin/stats/daily"
        assert scrubbed["extra"]["days"] == 30
        assert scrubbed["tags"]["environment"] == "production"
        assert scrubbed["user"]["id"] == "u-1"


# ---------------------------------------------------------------------------
# 7 — init_sentry must stop shipping frame locals
# ---------------------------------------------------------------------------

class TestInitSentryDisablesLocalVariables:
    """The PRIMARY fix: closes the whole frame-vars class, not one instance.

    Measured on the installed sentry-sdk (2.54.0):
    ``sentry_sdk.consts.DEFAULT_OPTIONS["include_local_variables"] is True``,
    and ``init_sentry`` never sets it — so every captured 500 ships the raising
    frame's locals, which for ``verify_admin_key`` is the real ADMIN_API_KEY.
    """

    def _captured_init_kwargs(self, monkeypatch):
        import sentry_sdk

        from app.services import sentry_service

        captured = {}

        def fake_init(**kwargs):
            captured.update(kwargs)

        monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/1")
        monkeypatch.setattr(sentry_sdk, "init", fake_init)
        sentry_service.init_sentry()
        assert captured, "init_sentry did not call sentry_sdk.init"
        return captured

    def test_include_local_variables_is_false(self, monkeypatch):
        kwargs = self._captured_init_kwargs(monkeypatch)
        assert "include_local_variables" in kwargs, (
            "init_sentry does not pass include_local_variables at all, so the "
            "SDK default (measured True) applies and every captured 500 ships "
            "the raising frame's locals — including ADMIN_API_KEY."
        )
        assert kwargs["include_local_variables"] is False

    def test_existing_init_options_are_preserved(self, monkeypatch):
        """Preserve: the 503 exclusion, PII off, and both hooks stay wired."""
        kwargs = self._captured_init_kwargs(monkeypatch)
        assert kwargs["send_default_pii"] is False
        assert kwargs["before_send"] is _before_send
        assert kwargs["before_breadcrumb"] is not None
        for integration in kwargs["integrations"]:
            codes = getattr(integration, "failed_request_status_codes", None)
            if codes is not None:
                assert 503 not in codes
                assert 500 in codes


# ---------------------------------------------------------------------------
# Measurement pins — these hold at HEAD and must keep holding.
# They are the evidence the chain above is real, not read.
# ---------------------------------------------------------------------------

class TestMeasuredPreconditions:
    def test_compare_digest_raises_on_non_ascii_str(self):
        """The library behaviour the fix exists for. RUN, not read."""
        for supplied in NON_ASCII_KEYS:
            with pytest.raises(TypeError):
                hmac.compare_digest(supplied, ADMIN_KEY)

    def test_compare_digest_is_fine_on_bytes(self):
        """The fix's mechanism: encode both sides first."""
        for supplied in NON_ASCII_KEYS:
            assert (
                hmac.compare_digest(
                    supplied.encode("utf-8", errors="surrogateescape"),
                    ADMIN_KEY.encode("utf-8", errors="surrogateescape"),
                )
                is False
            )
        assert (
            hmac.compare_digest(
                ADMIN_KEY.encode("utf-8", errors="surrogateescape"),
                ADMIN_KEY.encode("utf-8", errors="surrogateescape"),
            )
            is True
        )

    def test_sdk_default_ships_local_variables(self):
        """Why (2) is the primary fix: the SDK default is ON."""
        from sentry_sdk.consts import DEFAULT_OPTIONS

        assert DEFAULT_OPTIONS.get("include_local_variables") is True

    def test_include_local_variables_is_a_valid_option_on_this_sdk(self):
        """Fable review addition — the fix must not SILENTLY DISABLE Sentry.

        ``sentry_sdk.init`` rejects an unknown option with
        ``TypeError: Unknown option '...'`` (measured on 2.54.0), and
        ``init_sentry`` wraps its whole body in a broad ``except Exception``
        that only logs a warning. So if a future SDK renamed or removed
        ``include_local_variables``, our explicit kwarg would raise, be
        swallowed, and Sentry would be OFF in production with nothing but a
        log line to say so — the same shape as the W1-4 ``sign_out(scope=...)``
        TypeError that a broad catch turned into a silent no-op.

        The measurements this unit rests on were taken on the INSTALLED 2.54.0,
        but ``requirements.txt`` pins 2.68.1, which is what CI and Railway
        install. This assertion is what makes that gap loud instead of silent:
        it runs on whatever version is present, so CI settles it on 2.68.1.
        """
        from sentry_sdk.consts import DEFAULT_OPTIONS

        assert "include_local_variables" in DEFAULT_OPTIONS, (
            "include_local_variables is not a valid option on sentry-sdk "
            f"{__import__('sentry_sdk').VERSION}. init_sentry passes it "
            "explicitly, so init would raise TypeError, be swallowed by its "
            "broad except, and Sentry would be silently disabled in production."
        )

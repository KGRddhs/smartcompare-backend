"""U8c (S71, issue #292): the account-deletion 500 sends no chained exception
text to Sentry.

SPEC: docs/investigations/2026-10-03-session-71-state/U8C_SENTRY_CHAIN_SPEC.md
section 5, as corrected by the review (C1-C9) and ruled by the orchestrator
(UR1-UR10).

The defect: ``DELETE /api/v1/auth/account`` raises
``HTTPException(status_code=500, ...)`` inside its ``except Exception as e``
arm with no ``from`` clause, so Python sets ``__context__ = e`` and the Sentry
Starlette integration ships the CHAINED original exception as
``exception.values[0]`` of the 500 event: the httpx URL (host, path, email
query), the AuthApiError / APIError ``.message`` and the RuntimeError text.
The fix (GREEN, not here) is `` from None`` on that one raise.

How it is measured: ONE child process per module (the W1-1b idiom of
tests/test_retro_w1_1.py) runs the REAL app with the REAL ``init_sentry()`` and
an in-memory transport, in the order fixed by C2:

  1. wrap ``sentry_sdk.init`` (inject the memory transport, force
     ``traces_sample_rate=1.0`` so the transaction item is always in the
     sweep, UR6, and count the calls);
  2. ``import app.main`` with ``SENTRY_DSN`` unset (the import-time
     ``init_sentry()`` is a no-op);
  3. set a dummy DSN;
  4. call ``init_sentry()`` exactly once;
  5. check that the client's transport is the memory one (else ``fatal``).

The SDK's integrations patch framework classes process-wide and cannot be
undone, so no Sentry client is ever installed in the pytest process (R7). The
child installs a socket guard and reports every non-loopback attempt, runs
``neutralize_credentials(); install_dotenv_guard()`` (``LIVE`` is removed from
its environment so that is never a no-op), and drives four failure shapes plus
the success path through ``TestClient(raise_server_exceptions=False)``. The
leak check runs IN the child: per envelope item, one boolean per sentinel, and
every string the child reports back is sanitised, so no sentinel travels
through the parent's assertion messages verbatim.

Sentinel hygiene (C4): plain words and ``.example`` addresses, built at run
time, passed by ENVIRONMENT (never argv: ArgvIntegration copies sys.argv into
events); none is a substring of the user id, the bearer token, the route, a
module name or the worktree path, and none matches a scrubber pattern of
``app/services/sentry_service.py`` (no long hex, no JWT, no key prefix, no
token after the word Bearer). PIN 7 is the positive control (U8d UG1): the
sentinels survive the real ``before_send`` in the event ``extra``, so a
GREEN result cannot be a scrubbed-away false negative. PIN 4 is the negative
control (C4/UR8): the success path trips no flag.

RED today (b90b5f07), each for the stated reason:
  * RED 1 - an ``event`` item carries the sentinel word / email / host (the
    chained ``exception.values[0]``);
  * RED 2 - the one exception-bearing event carries TWO values, the original
    exception and then the HTTPException.
PIN (green today and after): status + envelope (R4), the type-only route log
event in the Sentry channel (UR3), the failure path really taken, the success
path, no network, the real init_sentry, the sentinel control.

The kill set is this file PLUS tests/test_account_deletion_u8b.py and
tests/test_account_deletion_u8b_fix_pins.py (C6/UR9): two Sentry-clean log
mutants (a DEBUG log of ``e``, a WARNING with exc_info) never reach Sentry and
are killed only by the U8b pins.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_ID = "user-u8c-red"
FAILURE_SCENARIOS = ("httpx", "authapi", "runtime", "apierror")
EXPECTED_TYPE = {
    "httpx": "ConnectError",
    "authapi": "AuthApiError",
    "runtime": "RuntimeError",
    "apierror": "APIError",
}
# (cascade RPC execute calls, auth admin delete_user calls) per scenario: the
# auth-delete shapes run the cascade first; the cascade shapes stop there.
EXPECTED_CALLS = {
    "httpx": (1, 1),
    "authapi": (1, 1),
    "runtime": (1, 0),
    "apierror": (1, 0),
    "success": (1, 1),
}
ENVELOPE_500 = {"success": False, "error": "Account deletion failed", "code": "SERVER_ERROR"}
SUCCESS_BODY = {"success": True, "message": "Account and all associated data deleted"}
ROUTE_LOGGER = "app.api.auth_routes"

# Sentinels, built at run time (C4 / UR10). The word sits in EVERY failure
# message (for APIError it is the only part that reaches Sentry, C5).
_SENT = "quill" + "beacon"
_EMAIL = "harbor.owl" + "@" + "fjord" + ".example"
_HOST = "glacierproj" + ".supabase" + ".example"
_OWNER = "owner.marten" + "@" + "fjord" + ".example"

_CHILD = r'''
import ipaddress, json, os, re, socket, sys
ATTEMPTS = []
def _loop(h):
    if isinstance(h, (bytes, bytearray)): h = bytes(h).decode("latin-1")
    if h in ("localhost", "testserver", "", None): return True
    try: return ipaddress.ip_address(str(h).split("%", 1)[0]).is_loopback
    except ValueError: return False
_c, _cx, _g = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
def _h(a): return a[0] if isinstance(a, tuple) else a
def connect(self, a):
    if not _loop(_h(a)): ATTEMPTS.append(("connect", repr(a))); raise OSError("blocked")
    return _c(self, a)
def connect_ex(self, a):
    if not _loop(_h(a)): ATTEMPTS.append(("connect_ex", repr(a))); raise OSError("blocked")
    return _cx(self, a)
def gai(h, *a, **k):
    if not _loop(h): ATTEMPTS.append(("getaddrinfo", repr(h))); raise OSError("blocked")
    return _g(h, *a, **k)
socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, gai

sys.path.insert(0, os.getcwd())
from tests._env_safety import neutralize_credentials, install_dotenv_guard
neutralize_credentials(); install_dotenv_guard()

SENT = os.environ.pop("U8C_SENT")
EMAIL = os.environ.pop("U8C_EMAIL")
HOST = os.environ.pop("U8C_HOST")
OWNER = os.environ.pop("U8C_OWNER")
USER_ID = os.environ.pop("U8C_USER_ID")
NEEDLES = {
    "sent": SENT,
    "email": EMAIL,
    "email_pct": EMAIL.replace("@", "%40"),
    "host": HOST,
    "owner": OWNER,
    "owner_pct": OWNER.replace("@", "%40"),
}
_PAT = re.compile(
    "|".join(re.escape(v) for v in sorted(NEEDLES.values(), key=len, reverse=True)),
    re.IGNORECASE,
)
_NAME = {v.lower(): "<" + k.upper() + ">" for k, v in NEEDLES.items()}
def san(s):
    if s is None:
        return None
    return _PAT.sub(lambda m: _NAME.get(m.group(0).lower(), "<REDACTED>"), str(s))
def flags(text):
    low = text.lower()
    return {k: (v.lower() in low) for k, v in NEEDLES.items()}

# C2 step 1: wrap sentry_sdk.init BEFORE the app import.
import sentry_sdk
from sentry_sdk.transport import Transport
ITEMS = []
INIT_CALLS = []
class _MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            ITEMS.append((item.type, item.get_bytes().decode("utf-8", "replace")))
    def flush(self, timeout, callback=None):
        pass
    def kill(self):
        pass
_real_init = sentry_sdk.init
def _init(*a, **kw):
    INIT_CALLS.append(1)
    kw["transport"] = _MemoryTransport
    kw["traces_sample_rate"] = 1.0
    return _real_init(*a, **kw)
sentry_sdk.init = _init

# C2 step 2: the app import with SENTRY_DSN unset (import-time init is a no-op).
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import app.main as app_main

# C2 steps 3-5: the dummy DSN, init_sentry() exactly once, the transport check.
os.environ["SENTRY_DSN"] = "https://public" + "@" + "o0.ingest.example.invalid/1"
from app.services.sentry_service import init_sentry
init_sentry()
_opts = sentry_sdk.get_client().options
INIT = {
    "init_calls": len(INIT_CALLS),
    "transport_is_memory": _opts.get("transport") is _MemoryTransport,
    "traces_sample_rate": _opts.get("traces_sample_rate"),
}
if not INIT["transport_is_memory"]:
    print("RESULT " + json.dumps({"fatal": "real init_sentry() did not initialise the SDK with the memory transport", "init": INIT}))
    sys.exit(0)

import httpx
from supabase_auth.errors import AuthApiError
from postgrest.exceptions import APIError

def build(name):
    rpc_client = MagicMock()
    admin = MagicMock()
    if name == "httpx":
        admin.auth.admin.delete_user.side_effect = httpx.ConnectError(
            "connect failed for https://%s/auth/v1/admin/users/%s?email=%s" % (HOST, SENT, EMAIL))
    elif name == "authapi":
        admin.auth.admin.delete_user.side_effect = AuthApiError(
            "User %s %s not allowed" % (SENT, EMAIL), 403, "not_admin")
    elif name == "runtime":
        rpc_client.rpc.return_value.execute.side_effect = RuntimeError(
            "boom for %s %s" % (SENT, EMAIL))
    elif name == "apierror":
        rpc_client.rpc.return_value.execute.side_effect = APIError(
            {"message": "m " + SENT, "code": "P0001", "hint": None, "details": "d " + EMAIL})
    return rpc_client, admin

def describe(kind, raw):
    d = {"type": kind, "leak": flags(raw)}
    if kind == "event":
        try:
            doc = json.loads(raw)
        except ValueError:
            doc = {}
        vals = ((doc.get("exception") or {}).get("values")) or []
        d["exc"] = [[v.get("type"), san(v.get("value"))] for v in vals]
        d["logger"] = doc.get("logger")
        d["logentry"] = san((doc.get("logentry") or {}).get("formatted"))
    return d

client = TestClient(app_main.app, raise_server_exceptions=False)
SCENARIOS = {}
for name in ("httpx", "authapi", "runtime", "apierror", "success"):
    ITEMS.clear()
    rpc_client, admin = build(name)
    user = {"id": USER_ID, "email": OWNER}
    with patch("app.api.auth_routes.verify_token", AsyncMock(return_value=user)), \
         patch("app.services.database_service.get_admin_supabase_client", return_value=rpc_client), \
         patch("app.services.auth_service.get_admin_client", return_value=admin), \
         patch("app.services.cache_service.redis_client", MagicMock()), \
         patch("app.middleware.rate_limiter.limiter.enabled", False):
        r = client.delete("/api/v1/auth/account", headers={"Authorization": "Bearer u8c-token"})
    sentry_sdk.flush()
    try:
        body = r.json()
    except ValueError:
        body = {"_raw": san(r.text[:300])}
    if not isinstance(body, dict):
        body = {"_raw": san(json.dumps(body)[:300])}
    SCENARIOS[name] = {
        "status": r.status_code,
        "body_without_request_id": {k: (san(v) if isinstance(v, str) else v)
                                    for k, v in body.items() if k != "request_id"},
        "has_request_id": "request_id" in body,
        "rpc": rpc_client.rpc.return_value.execute.call_count,
        "admin_del": admin.auth.admin.delete_user.call_count,
        "items": [describe(kind, raw) for kind, raw in ITEMS],
    }

# Positive control (C4; U8d UG1): the sentinels survive the REAL before_send in
# a region no scrub rule blanks (the event extra -- U8d R1 empties every
# exception value), so a clean sweep can never be a scrubbed-away false negative.
ITEMS.clear()
with sentry_sdk.new_scope() as _scope:
    _scope.set_extra("u8c_control", "u8c control %s %s %s %s" % (SENT, EMAIL, HOST, OWNER))
    sentry_sdk.capture_message("u8c positive control")
sentry_sdk.flush()
CONTROL = [describe(kind, raw) for kind, raw in ITEMS]

print("RESULT " + json.dumps({
    "init": INIT,
    "scenarios": SCENARIOS,
    "control": CONTROL,
    "network_attempts": ATTEMPTS,
}))
'''


def _scrub_tail(text: str) -> str:
    """Sanitise child output before it reaches an assertion message."""
    for needle, name in (
        (_EMAIL, "<EMAIL>"),
        (_OWNER, "<OWNER>"),
        (_HOST, "<HOST>"),
        (_SENT, "<SENT>"),
    ):
        text = re.sub(re.escape(needle), name, text, flags=re.IGNORECASE)
    return text


@pytest.fixture(scope="module")
def u8c_child():
    """Run the real app + real init_sentry() + real SDK in ONE child process."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("SENTRY_DSN", None)
    env.pop("LIVE", None)  # neutralize_credentials() must never be a no-op here
    env.pop("LOG_LEVEL", None)  # the production default (INFO) of app/main.py
    env.update({
        "U8C_SENT": _SENT,
        "U8C_EMAIL": _EMAIL,
        "U8C_HOST": _HOST,
        "U8C_OWNER": _OWNER,
        "U8C_USER_ID": USER_ID,
    })
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=540,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (
        f"child produced no RESULT (rc={proc.returncode}).\n"
        f"stderr tail:\n{_scrub_tail(proc.stderr[-3000:])}\n"
        f"stdout tail:\n{_scrub_tail(proc.stdout[-2000:])}"
    )
    return json.loads(lines[-1][len("RESULT "):])


def _case(child: dict, name: str) -> dict:
    assert "fatal" not in child, f"the child never drove the route: {child}"
    return child["scenarios"][name]


def _leaking(items: list) -> list:
    return [
        (i, it["type"], sorted(k for k, v in it["leak"].items() if v))
        for i, it in enumerate(items)
        if any(it["leak"].values())
    ]


def _exception_events(items: list) -> list:
    return [it for it in items if it["type"] == "event" and it.get("exc")]


def _shapes(items: list) -> list:
    return [[tuple(v) for v in it["exc"]] for it in _exception_events(items)]


@pytest.mark.timeout(600)
class TestU8cSentryChain:
    # ------------------------------------------------------------------ RED

    @pytest.mark.parametrize("scenario", FAILURE_SCENARIOS)
    def test_u8c_red1_no_envelope_item_carries_the_chained_exception_text(
        self, u8c_child, scenario
    ):
        """R2 / UR6: no envelope item of ANY type (event, transaction,
        sessions; breadcrumbs and extra live inside the event items) carries
        the sentinel word, the email or the URL host. RED today: the event
        whose exception.values[0] is the chained original exception."""
        case = _case(u8c_child, scenario)
        leaks = _leaking(case["items"])
        assert leaks == [], (
            f"[{scenario}] the chained exception text left the process in "
            f"envelope item(s) (index, type, flags) = {leaks}; exception values "
            f"of the exception events = {_shapes(case['items'])}"
        )

    @pytest.mark.parametrize("scenario", FAILURE_SCENARIOS)
    def test_u8c_red2_the_500_event_carries_only_the_http_exception(
        self, u8c_child, scenario
    ):
        """R1 / R3 / UR2: the 500 stays visible in Sentry as exactly ONE
        exception-bearing event whose exception.values is exactly the
        HTTPException. RED today: two values, the chained original exception
        first. Also kills a capture-suppressed variant (MU5: zero events) and
        a note on the HTTPException (MU7: a value longer than the detail)."""
        case = _case(u8c_child, scenario)
        shapes = _shapes(case["items"])
        assert shapes == [[("HTTPException", "Account deletion failed")]], (
            f"[{scenario}] expected exactly one exception event carrying only "
            f"('HTTPException', 'Account deletion failed'); got {len(shapes)} "
            f"exception event(s) with values {shapes}"
        )

    # ------------------------------------------------------------------ PIN

    @pytest.mark.parametrize("scenario", FAILURE_SCENARIOS)
    def test_u8c_pin1_status_and_envelope_unchanged(self, u8c_child, scenario):
        """R4: status 500, the U8b error envelope, a request_id."""
        case = _case(u8c_child, scenario)
        assert case["status"] == 500, (scenario, case["status"], case["body_without_request_id"])
        assert case["body_without_request_id"] == ENVELOPE_500, (
            scenario, case["body_without_request_id"])
        assert case["has_request_id"] is True, scenario

    @pytest.mark.parametrize("scenario", FAILURE_SCENARIOS)
    def test_u8c_pin2_route_log_event_is_type_only(self, u8c_child, scenario):
        """R4 / UR3: exactly one Sentry event from the route's logger, whose
        formatted message names the exception TYPE only (the U8b line in the
        Sentry channel)."""
        case = _case(u8c_child, scenario)
        route_events = [
            it for it in case["items"]
            if it["type"] == "event" and it.get("logger") == ROUTE_LOGGER
        ]
        expected = f"Account deletion failed for user {USER_ID}: {EXPECTED_TYPE[scenario]}"
        assert [it.get("logentry") for it in route_events] == [expected], (
            scenario, [it.get("logentry") for it in route_events])

    @pytest.mark.parametrize("scenario", FAILURE_SCENARIOS)
    def test_u8c_pin3_the_failure_really_happened_where_intended(self, u8c_child, scenario):
        """The sentinel was raised on the path under test: the auth-delete
        shapes ran the cascade and then the auth delete; the cascade shapes
        stopped at the cascade."""
        case = _case(u8c_child, scenario)
        assert (case["rpc"], case["admin_del"]) == EXPECTED_CALLS[scenario], (
            scenario, case["rpc"], case["admin_del"])

    def test_u8c_pin4_success_path_unchanged(self, u8c_child):
        """R5 + the negative control (C4 / UR8): 200 and the success body, no
        exception event, and NO item trips any sentinel flag, so the sweep is
        not tripped by harness text and a RED result has the right cause."""
        case = _case(u8c_child, "success")
        assert case["status"] == 200, case
        assert case["body_without_request_id"] == SUCCESS_BODY, case["body_without_request_id"]
        assert (case["rpc"], case["admin_del"]) == EXPECTED_CALLS["success"], case
        assert _exception_events(case["items"]) == [], case["items"]
        assert _leaking(case["items"]) == [], case["items"]

    def test_u8c_pin5_child_made_no_network_attempt(self, u8c_child):
        """R7: the child's socket guard recorded nothing."""
        assert "fatal" not in u8c_child, u8c_child
        assert u8c_child["network_attempts"] == [], u8c_child["network_attempts"]

    def test_u8c_pin6_child_really_used_the_real_init_sentry(self, u8c_child):
        """C2 / UR4 / UR6: no fatal; the real init_sentry() initialised the SDK
        exactly once (the import-time call was a no-op) with the memory
        transport and traces 1.0, and every request yielded a transaction item
        (so the transaction is inside the sweep)."""
        assert "fatal" not in u8c_child, u8c_child
        init = u8c_child["init"]
        assert init["transport_is_memory"] is True, init
        assert init["init_calls"] == 1, init
        assert init["traces_sample_rate"] == 1.0, init
        for name, case in u8c_child["scenarios"].items():
            kinds = [it["type"] for it in case["items"]]
            assert "transaction" in kinds, (name, kinds)

    def test_u8c_pin7_sentinels_survive_the_real_scrubber(self, u8c_child):
        """C4 positive control (U8d UG1: it rides the event extra, because U8d
        R1 empties every exception value): an event whose extra carries every
        sentinel, captured through the real before_send, still carries each of
        them, so none matches a scrubber pattern and a clean sweep is real."""
        assert "fatal" not in u8c_child, u8c_child
        control = [it for it in u8c_child["control"] if it["type"] == "event"]
        assert len(control) == 1, u8c_child["control"]
        leak = control[0]["leak"]
        missing = sorted(k for k in ("sent", "email", "host", "owner") if not leak[k])
        assert missing == [], (
            f"the real scrubber removed sentinel(s) {missing} from the event "
            f"extra: the leak sweep can no longer see them, choose sentinels "
            f"no pattern of app/services/sentry_service.py matches"
        )

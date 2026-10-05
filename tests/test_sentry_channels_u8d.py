"""U8d (S72, issue #311): the remaining channels through which Sentry receives
exception text or user content -- the CHILD-PROCESS half (the real app, the
real ``init_sentry()``, the real SDK, an in-memory transport).

SPEC SET (later wins): docs/investigations/2026-10-05-session-72-state/specs/
U8D_SENTRY_CHANNELS_SPEC.md (R1-R9, section 8), U8D_SENTRY_CHANNELS_REVIEW.md
(binding corrections 1-14) and FABLE_RULINGS_U8D.md (SR1-SR14: R4', R5 as
corrected, R7 = ERROR, R8 = seven lines, R10, R11 = the 16,384-character cap,
R12 = trace propagation off, the OpenAI include_prompts pin).

The sentence this unit makes true (SR preamble): "Sentry receives exception
types, scrubbed message templates (which may include internal account and
comparison identifiers) and scrubbed request metadata (method, path, user
agent) - not raw exception text, request bodies, credentials, or the content
of user queries."

HOW IT IS MEASURED (the U8c idiom, tests/test_account_deletion_u8c_sentry_chain.py):
ONE module-scoped child process (a) installs a socket guard that RECORDS every
non-loopback attempt, (b) runs ``neutralize_credentials(); install_dotenv_guard()``
(``LIVE`` and every ``ENABLE_*`` flag are removed from its environment, so the
routes run on their code defaults), (c) wraps ``sentry_sdk.init`` to inject an
in-memory transport and ``traces_sample_rate=1.0``, (d) imports ``app.main``
with ``SENTRY_DSN`` unset, sets a fake DSN on a reserved ``.invalid`` host and
calls the REAL ``init_sentry()`` exactly once, (e) drives the scenarios below
through ``TestClient(raise_server_exceptions=False)``. Every failure is
INJECTED by patching (review correction 7): the URL validator of
``/url/compare`` returns False, the Supabase auth client and the audit insert
of ``/auth/login`` raise, Redis raises, the comparison service raises. No
scenario relies on a blocked socket; the attempt list must stay EMPTY.

Sentinels are plain words and ``.example`` / RFC 5737 addresses built at run
time by concatenation (the 64-hex device fingerprint and the 32-hex run are
hash digests computed at run time), passed to the child by ENVIRONMENT (never
argv: ArgvIntegration copies sys.argv into events). The leak sweep runs IN the
child (one flag set per JSON path, list indices folded to ``N``) and every
string the child reports back is sanitised (each sentinel replaced by its
``<NAME>``), so no sentinel travels through an assertion message verbatim.
The percent-encoded forms (``%40`` in an email, ``%5B``/``%5D`` in a push
token) are needles too (spec edge case 11). PIN ``positive_control`` proves
the plain sentinels survive the real scrubber (they are not pattern-shaped);
PIN ``negative_control`` proves a success request trips no flag.

THROWAWAY ROUTES (``/__u8d/*``) are added to the app object IN THE CHILD ONLY;
nothing on disk changes. They model: an exception escaping to
ErrorHandlerMiddleware with a chain and a frame local, a JSON body on a 500,
outbound httpx calls through ``httpx.MockTransport`` (a PostgREST filter, a
Scrape.do-shaped token query, an OpenAI path), the REAL
``url_extraction_service.fetch_page`` (Link mode) with its validator patched
True and its httpx client on a recording MockTransport, ``cache_service.
delete_cached`` with Redis raising, INFO/WARNING/ERROR log lines, and the
header set of review correction 3.

RULE -> NODES -> MUTANTS (spec 8.3 M1-M15, review M16-M21, SR3, SR4, SR8):

| rule | node family (this file) | kills |
|---|---|---|
| R1 values blank (HTTPException kept) | red_r1_exception_values_blanked[*] ; pin_http_exception_detail_kept[*] | M1 ; M2 |
| R2 handled text -> <TypeName> (event) | red_r2_logentry_is_template_plus_type[*] | M3, M4 (cache_delete, cache_delete_hex, login_audit have no exc_info), M16 (cache_delete_hex) |
| R2 crumb half | red_r2_error_breadcrumb_redacted[share_post] | M5 |
| R2 clean templates | pin_clean_template_unchanged[*] | (over-redaction) |
| R3 no body | red_r3_no_request_body[*] ; unit file red_r3_belt | M7 (option, see options), M8 (unit belt) |
| R4' query strings | red_r4p_query_string_user_content_dropped[*] ; pin_r4p_bookkeeping_readable[*] | M9 (product_ab_amp), M18 (compare_get_amp, product_ab_amp) |
| R5 outbound query values | red_r5_outbound_query_values_filtered[*] | M10 (span), M11 (crumb) |
| R5 user URL path (non-infra) | red_r5_outbound_user_url_path_dropped[*] ; pin_r5_host_and_infra_path_kept[*] | M20 ; over-stripping |
| R6 capability path tokens | red_r6_capability_token_not_in_url[*] | M12 |
| R7 = ERROR | red_r7_no_info_or_warning_log_breadcrumb[*] ; red_options_effective[crumb_level] | M13 |
| R9 no behaviour change | pin_r9_status_and_body_unchanged[*], pin_r9_event_count_unchanged[*], pin_r9_exception_type_lists_unchanged[*] | any status/body/capture change |
| R10 header allowlist | red_r10_header_value_filtered[*] ; pin_r10_header_names[*] | M19 |
| R12 (SR4) no trace headers out | red_r12_link_fetch_sends_no_trace_headers[*] ; pin_sr4_spans_recorded_with_propagation_off | M-SR4 (trace_propagation_targets removed) |
| options (effective client) | red_options_effective[*] ; pin_integration_list_unchanged ; pin_privacy_options_kept | M7, M13, M-SR4, M-SR8 (include_prompts removed) |
| harness | pin_no_network_attempt, pin_real_init_sentry_memory_transport, pin_positive_control, pin_negative_control, pin_no_frame_vars | a broken harness |

R8 (the seven source lines), R11 (SR3 cap), the HTTPException AST pin and the
option pins taken from ``init_sentry``'s own kwargs live in
tests/test_sentry_channels_u8d_unit.py (M6, M14, M15, M17, M21, M-SR3 there).

PIN nodes that pass at base TRIVIALLY, by construction: pin_sr4_spans_recorded
_with_propagation_off (propagation is ON at base; the pin guards the GREEN
from dropping spans together with the headers), pin_r5_host_and_infra_path_kept
(base keeps every path), pin_no_frame_vars (C9 was closed by W1-1).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- sentinels
# Built at run time; none is pattern-shaped (no long hex in the plain set, no
# JWT, no key prefix), none is a substring of a route, module, id or path.
_V = {
    "U8D_SENT": "quill" + "beacon",
    "U8D_EMAIL": "harbor.owl" + "@" + "fjord" + ".example",
    "U8D_HOST": "glacierproj" + ".supabase" + ".example",
    "U8D_QWORD": "zephyr" + "quokka",
    "U8D_QWORD2": "wombat" + "saffron",
    "U8D_QWORD3": "ibis" + "cobalt",
    "U8D_TOK": "tok" + "quasar" + "lumen" + "77",
    "U8D_SHTOK": "Shr" + "Pelican" + "Tundra" + "Kx9_ab",
    "U8D_SHTOK2": "Ref" + "Heron" + "Glacier" + "Mz4_cd",
    "U8D_IP": "203.0.113" + "." + "77",
    "U8D_LOCAL": "marmot" + "lantern",
    "U8D_NOTE": "puffin" + "meadow",
    "U8D_PTOK": "Exponent" + "PushToken[" + "otter" + "violet" + "]",
    # Hash digests computed at run time: a 64-hex device fingerprint (the
    # client sends sha256 hex) and a 32-hex run (review correction 6).
    "U8D_FP": hashlib.sha256(("otter" + "device").encode("utf-8")).hexdigest(),
    "U8D_HEX32": hashlib.md5(("u8d" + "-hex-run").encode("utf-8")).hexdigest(),
}

USER_ID = "user-u8d"
SHARE_UUID = "3f0e3c9e-1111-4222-8333-944455556666"
COMPARE_400 = {
    "success": False,
    "error": "Something went wrong on our side " + chr(0x2014) + " give it another tap in a moment.",
    "code": "INTERNAL_ERROR",
}
SERVER_500 = {"success": False, "error": "Internal server error", "code": "SERVER_ERROR"}

# R9 base values (measured at 845ece15 by this file's first run).
EXPECTED_STATUS_BODY = {
    "compare_post": (400, COMPARE_400),
    "compare_get_amp": (400, COMPARE_400),
    "product_ab_amp": (500, SERVER_500),
    "unhandled": (500, SERVER_500),
    "unhandled_body": (500, SERVER_500),
    "push_token": (500, {"success": False, "error": "Failed to register push token", "code": "INTERNAL_ERROR"}),
    "share_post": (500, {"success": False, "error": "Failed to create share link", "code": "SHARE_TOKEN_FAILED"}),
    "share_get_404": (404, {"success": False, "error": "Shared comparison not found", "code": "NOT_FOUND"}),
    "share_get_500": (500, SERVER_500),
    # The referral router is gated off by default: a deliberate 503 (dropped
    # from the error stream by the 503 rule), the transaction still recorded.
    "referral_invite": (503, {"success": False, "error": "Referral system is not enabled in this environment.",
                              "code": "FEATURE_DISABLED"}),
    "cache_delete": (200, {"ok": True}),
    "cache_delete_hex": (200, {"ok": True}),
    "login_audit": (401, {"success": False, "error": "Something went wrong. Please try again later.", "code": "AUTH_REQUIRED"}),
    "url_compare_get": (400, {"success": False, "error": "URL blocked by security policy", "code": "BAD_REQUEST"}),
    "link_fetch": (200, {"ok": True}),
    "httpx_spans": (200, {"ok": True}),
    "levels": (200, {"ok": True}),
    "headers": (500, SERVER_500),
    "success": (200, {"ok": True}),
}

# R9: the exception-bearing events' type lists (one inner list per event).
EXPECTED_EXC_TYPES = {
    "compare_post": [["RuntimeError"]],
    "compare_get_amp": [["RuntimeError"]],
    "product_ab_amp": [["RuntimeError"]],
    "unhandled": [["ValueError", "RuntimeError"]],
    "unhandled_body": [["RuntimeError"]],
    "push_token": [["APIError", "HTTPException"]],
    "share_post": [["APIError", "ShareTokenError", "HTTPException"]],
    "share_get_500": [["RuntimeError"]],
    "headers": [["RuntimeError"]],
}

# R9: number of ``event`` envelope items per scenario (filled from base where
# marked None; see EXPECTED_EVENT_COUNT_BASE below).
EXPECTED_EVENT_COUNT = {
    "compare_post": 1,
    "compare_get_amp": 1,
    "product_ab_amp": 1,
    "unhandled": 1,
    "unhandled_body": 1,
    "push_token": 1,
    "share_post": 2,
    "share_get_404": 0,
    "share_get_500": 1,
    "referral_invite": 0,
    "cache_delete": 1,
    "cache_delete_hex": 1,
    "login_audit": 2,
    "url_compare_get": 0,
    "link_fetch": 1,
    "httpx_spans": 1,
    "levels": 1,
    "headers": 1,
    "success": 0,
}

BASE_INTEGRATIONS = [
    "ArgvIntegration", "AtexitIntegration", "DedupeIntegration", "ExcepthookIntegration",
    "FastApiIntegration", "Httpx2Integration", "HttpxIntegration", "LoggingIntegration",
    "ModulesIntegration", "OpenAIIntegration", "RedisIntegration", "StarletteIntegration",
    "StdlibIntegration", "ThreadingIntegration",
]

_CHILD = r'''
import ipaddress, json, os, re, socket, sys, logging
ATTEMPTS = []
def _loop(h):
    if isinstance(h, (bytes, bytearray)): h = bytes(h).decode("latin-1")
    if h in ("localhost", "testserver", "", None): return True
    try: return ipaddress.ip_address(str(h).split("%", 1)[0]).is_loopback
    except ValueError: return False
_c, _cx, _g = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
def _h(a): return a[0] if isinstance(a, tuple) else a
def connect(self, a):
    if not _loop(_h(a)): ATTEMPTS.append("connect"); raise OSError("blocked")
    return _c(self, a)
def connect_ex(self, a):
    if not _loop(_h(a)): ATTEMPTS.append("connect_ex"); raise OSError("blocked")
    return _cx(self, a)
def gai(h, *a, **k):
    if not _loop(h): ATTEMPTS.append("getaddrinfo"); raise OSError("blocked")
    return _g(h, *a, **k)
socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, gai

sys.path.insert(0, os.getcwd())
from tests._env_safety import neutralize_credentials, install_dotenv_guard
neutralize_credentials(); install_dotenv_guard()

N = {k[4:].lower(): os.environ.pop(k) for k in list(os.environ) if k.startswith("U8D_")}
NEEDLES = dict(N)
NEEDLES["email_pct"] = N["email"].replace("@", "%40")
NEEDLES["ptok_pct"] = N["ptok"].replace("[", "%5B").replace("]", "%5D")
_PAT = re.compile("|".join(re.escape(v) for v in sorted(NEEDLES.values(), key=len, reverse=True)), re.I)
_NAME = {v.lower(): "<" + k.upper() + ">" for k, v in NEEDLES.items()}
def san(s):
    if s is None: return None
    return _PAT.sub(lambda m: _NAME.get(m.group(0).lower(), "<X>"), str(s))
def hits(s):
    low = str(s).lower()
    return sorted(k for k, v in NEEDLES.items() if v.lower() in low)
def leak_paths(obj, path=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            h = hits(k)
            if h: out.append([path + "/<key>", h])
            out += leak_paths(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for v in obj:
            out += leak_paths(v, path + "/N")
    elif isinstance(obj, str):
        h = hits(obj)
        if h: out.append([path, h])
    return out

import sentry_sdk
from sentry_sdk.transport import Transport
ITEMS = []
INIT_CALLS = []
class _MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            ITEMS.append((item.type, item.get_bytes().decode("utf-8", "replace")))
    def flush(self, timeout, callback=None): pass
    def kill(self): pass
_real_init = sentry_sdk.init
def _init(*a, **kw):
    INIT_CALLS.append(1)
    kw["transport"] = _MemoryTransport
    kw["traces_sample_rate"] = 1.0
    return _real_init(*a, **kw)
sentry_sdk.init = _init

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import app.main as app_main
os.environ["SENTRY_DSN"] = "https://public" + "@" + "o0.ingest.example.invalid/1"
from app.services.sentry_service import init_sentry
init_sentry()
_cl = sentry_sdk.get_client()
_opts = _cl.options
_ints = list(_cl.integrations.values())
_li = [i for i in _ints if type(i).__name__ == "LoggingIntegration"]
_oi = [i for i in _ints if type(i).__name__ == "OpenAIIntegration"]
INIT = {
    "init_calls": len(INIT_CALLS),
    "transport_is_memory": _opts.get("transport") is _MemoryTransport,
    "traces_sample_rate": _opts.get("traces_sample_rate"),
    "integrations": sorted(type(i).__name__ for i in _ints),
    "max_request_body_size": _opts.get("max_request_body_size"),
    "trace_propagation_targets": list(_opts.get("trace_propagation_targets") or []),
    "send_default_pii": _opts.get("send_default_pii"),
    "include_local_variables": _opts.get("include_local_variables"),
    "crumb_level": (_li[0]._breadcrumb_handler.level if _li and _li[0]._breadcrumb_handler is not None else None),
    "event_level": (_li[0]._handler.level if _li and _li[0]._handler is not None else None),
    "openai_include_prompts": (getattr(_oi[0], "include_prompts", None) if _oi else None),
}
if not INIT["transport_is_memory"]:
    print("RESULT " + json.dumps({"fatal": "real init_sentry() did not install the memory transport", "init": INIT}))
    sys.exit(0)

import httpx
from urllib.parse import urlparse
from postgrest.exceptions import APIError
from app.services import cache_service
from app.services import url_extraction_service as ues
app = app_main.app
LOG = logging.getLogger("app.u8d_probe")
SUPA_HOST = urlparse(os.environ.get("SUPABASE_URL", "")).hostname or "neutralized.supabase.invalid"

@app.get("/__u8d/ok")
async def _u8d_ok():
    return {"ok": True}

@app.get("/__u8d/unhandled")
async def _u8d_unhandled(email: str = "", ref: str = ""):
    local_secret = N["local"]  # noqa: F841 - a frame local (C9)
    try:
        raise ValueError("orig %s %s" % (N["email"], N["host"]))
    except ValueError:
        raise RuntimeError("wrap " + N["sent"])

@app.post("/__u8d/unhandled_body")
async def _u8d_unhandled_body(payload: dict):
    raise RuntimeError("constant failure")

@app.get("/__u8d/boom")
async def _u8d_boom():
    raise RuntimeError("constant boom")

RC = MagicMock()
@app.get("/__u8d/cache")
async def _u8d_cache():
    with patch.object(cache_service, "redis_client", RC):
        cache_service.delete_cached("home:smart_pick:" + "user-u8d")
    return {"ok": True}

@app.get("/__u8d/levels")
async def _u8d_levels():
    LOG.info("info crumb " + N["qword"])
    LOG.warning("warning crumb " + N["qword2"])
    LOG.error("forced constant error")
    return {"ok": True}

@app.get("/__u8d/httpx")
async def _u8d_httpx():
    def handler(req):
        return httpx.Response(200, json={"ok": True})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        c.get("https://" + SUPA_HOST + "/rest/v1/users", params={"select": "id", "email": "eq." + N["email"]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as ac:
        await ac.get("https://api.scrape.example/", params={"token": N["tok"], "url": "https://shop.example/p?x=" + N["sent"]})
        await ac.get("https://api.openai.com/v1/models")
    LOG.error("forced constant error after outbound calls")
    return {"ok": True}

OUTBOUND = []
_RealAsyncClient = httpx.AsyncClient
def _mk_client(*a, **kw):
    def handler(req):
        OUTBOUND.append({"baggage": bool(req.headers.get("baggage")),
                         "sentry_trace": bool(req.headers.get("sentry-trace")),
                         "host": req.url.host})
        return httpx.Response(200, text="<html>ok</html>")
    kw["transport"] = httpx.MockTransport(handler)
    return _RealAsyncClient(*a, **kw)

@app.get("/__u8d/link")
async def _u8d_link():
    with patch("app.utils.url_validator._validate_url_offloop_or_sync", AsyncMock(return_value=True)), \
         patch.object(ues.httpx, "AsyncClient", _mk_client):
        page = await ues.fetch_page("https://shop.invalid/products/" + N["qword"] + "-perfume?ref=" + N["sent"])
    LOG.error("forced constant error after link fetch")
    return {"ok": page is not None}

def describe(kind, raw):
    try: doc = json.loads(raw)
    except ValueError: doc = {"_raw": raw}
    d = {"type": kind, "leak": leak_paths(doc)}
    if kind in ("event", "transaction"):
        req = doc.get("request") or {}
        hdr = req.get("headers") if isinstance(req.get("headers"), dict) else {}
        d["request"] = {
            "url": san(req.get("url")),
            "query_string": san(req.get("query_string")),
            "has_data": "data" in req,
            "data": (san(req["data"]) if isinstance(req.get("data"), str)
                     else ("<" + type(req["data"]).__name__ + ">" if "data" in req else None)),
            "headers": {str(k).lower(): san(v) for k, v in hdr.items()},
        }
    if kind == "event":
        vals = ((doc.get("exception") or {}).get("values")) or []
        d["exc"] = [[v.get("type"), san(v.get("value"))] for v in vals]
        d["frames_with_vars"] = sum(1 for v in vals for f in ((v.get("stacktrace") or {}).get("frames") or []) if "vars" in f)
        d["logger"] = doc.get("logger")
        d["level"] = doc.get("level")
        le = doc.get("logentry") or {}
        d["formatted"] = san(le.get("formatted"))
        d["message"] = san(le.get("message"))
        d["crumbs"] = [[b.get("category"), b.get("level"), b.get("type"), san(b.get("message"))]
                       for b in ((doc.get("breadcrumbs") or {}).get("values") or [])]
        d["extra_path"] = san((doc.get("extra") or {}).get("path"))
    if kind == "transaction":
        spans = doc.get("spans") or []
        d["spans"] = [[s.get("op"), san(s.get("description")), san((s.get("data") or {}).get("url")),
                       san((s.get("data") or {}).get("http.query"))] for s in spans]
    return d

client = TestClient(app, raise_server_exceptions=False)
SC = {}
def run(name, fn, **extra):
    ITEMS.clear()
    try:
        r = fn()
        status = r.status_code
        try:
            body = r.json()
            if isinstance(body, dict):
                body = {k: (san(v) if isinstance(v, str) else v) for k, v in body.items() if k != "request_id"}
            else:
                body = {"_raw": san(json.dumps(body))[:300]}
        except Exception:
            body = {"_raw": san(r.text[:300])}
    except Exception as exc:
        status, body = "client-raised", {"_raw": type(exc).__name__}
    sentry_sdk.flush()
    SC[name] = {"status": status, "body": body, "items": [describe(k, raw) for k, raw in ITEMS]}
    SC[name].update(extra)

USER = {"id": "user-u8d", "email": "owner.marten" + "@" + "fjord.example", "access_token": "u8d-access"}
admin = MagicMock()
rcache = MagicMock(); rcache.get.return_value = None
audit_ok = MagicMock()
common = [
    patch("app.middleware.rate_limiter.limiter.enabled", False),
    patch("app.services.cache_service.redis_client", rcache),
    patch("app.services.database_service.get_admin_supabase_client", return_value=admin),
    patch("app.services.audit_service.get_admin_supabase_client", return_value=audit_ok),
]
for p in common: p.start()

Q = N["qword"] + "alpha phone vs " + N["qword"] + "beta phone"
parse_boom = AsyncMock(side_effect=RuntimeError("parse boom %s %s" % (N["sent"], N["email"])))
with patch("app.services.structured_comparison_service.parse_product_query", parse_boom):
    run("compare_post", lambda: client.post("/api/v1/text/compare", json={"query": Q}))
    run("compare_get_amp", lambda: client.get("/api/v1/text/compare", params={
        "q": N["qword"] + " Dolce & " + N["qword2"] + " Gabbana #" + N["qword3"], "nocache": "true"}))
    SC["compare_get_amp"]["parse_calls"] = parse_boom.call_count

svc = MagicMock()
svc.compare_from_text = AsyncMock(side_effect=RuntimeError("svc boom " + N["sent"]))
with patch("app.api.text_routes.get_comparison_service", return_value=svc):
    run("product_ab_amp", lambda: client.get("/api/v1/text/compare", params={
        "product_a": N["qword"] + " & " + N["qword2"], "product_b": N["qword3"] + "beta", "region": "bahrain"}))
    SC["product_ab_amp"]["service_calls"] = svc.compare_from_text.call_count

run("unhandled", lambda: client.get("/__u8d/unhandled", params={"email": N["email"], "ref": N["sent"]}))
run("unhandled_body", lambda: client.post("/__u8d/unhandled_body", json={"query": Q, "email": N["email"], "note": N["sent"]}))

ucli = MagicMock()
ucli.table.return_value.update.return_value.eq.return_value.execute.side_effect = APIError(
    {"message": "m " + N["sent"], "code": "23505", "hint": None, "details": "Key (email)=(" + N["email"] + ") exists"})
with patch("app.api.auth_routes.verify_token", AsyncMock(return_value=USER)), \
     patch("app.api.auth_routes.get_user_supabase_client", return_value=ucli):
    run("push_token", lambda: client.put("/api/v1/auth/push-token", json={"expo_push_token": N["ptok"]},
                                         headers={"Authorization": "Bearer u8d-token"}))

from app.services.database_service import ShareTokenError
def _share_raise(*a, **k):
    api = APIError({"message": "dup " + N["sent"], "code": "23505", "hint": None,
                    "details": "Key (share_token)=(" + N["shtok"] + ") already exists."})
    err = ShareTokenError("share_token write failed: %s" % api)
    err.__cause__ = api
    raise err
with patch("app.api.share_routes.verify_token", AsyncMock(return_value=USER), create=True), \
     patch("app.api.auth_routes.verify_token", AsyncMock(return_value=USER)), \
     patch("app.api.share_routes.create_share_token", AsyncMock(side_effect=_share_raise)):
    run("share_post", lambda: client.post("/api/v1/share/" + "3f0e3c9e-1111-4222-8333-944455556666",
                                          headers={"Authorization": "Bearer u8d-token"}))
with patch("app.api.share_routes.get_shared_comparison", AsyncMock(return_value=None)):
    run("share_get_404", lambda: client.get("/api/v1/share/" + N["shtok"]))
with patch("app.api.share_routes.get_shared_comparison", AsyncMock(side_effect=RuntimeError("constant view failure"))):
    run("share_get_500", lambda: client.get("/api/v1/share/" + N["shtok"]))
run("referral_invite", lambda: client.get("/api/v1/referrals/invite/" + N["shtok2"], params={"ref": "QR-ABCDEF"}))

RC.delete.side_effect = ConnectionError("Error 111 connecting to %s:6379. %s" % (N["host"], N["sent"]))
run("cache_delete", lambda: client.get("/__u8d/cache"))
SC["cache_delete"]["redis_delete_calls"] = RC.delete.call_count
RC.reset_mock()
RC.delete.side_effect = RuntimeError("upstream rejected key " + N["hex32"] + " after " + "retry " * 40 + "for " + N["email"])
run("cache_delete_hex", lambda: client.get("/__u8d/cache"))
SC["cache_delete_hex"]["redis_delete_calls"] = RC.delete.call_count

auth_client = MagicMock()
auth_client.auth.sign_in_with_password.side_effect = httpx.ConnectError("upstream connect failed")
audit_bad = MagicMock()
audit_bad.table.return_value.insert.return_value.execute.side_effect = httpx.ConnectError(
    "audit write failed %s %s" % (N["sent"], N["host"]))
with patch("app.services.auth_service.get_auth_client", return_value=auth_client), \
     patch("app.services.audit_service.get_admin_supabase_client", return_value=audit_bad):
    run("login_audit", lambda: client.post("/api/v1/auth/login", json={"email": N["email"], "password": "Pw-u8d-Login-1"}))
    SC["login_audit"]["sign_in_calls"] = auth_client.auth.sign_in_with_password.call_count
    SC["login_audit"]["audit_insert_calls"] = audit_bad.table.return_value.insert.return_value.execute.call_count

with patch("app.api.url_routes._validate_url_offloop_or_sync", AsyncMock(return_value=False)):
    run("url_compare_get", lambda: client.get("/api/v1/url/compare", params={
        "url1": "https://shop.invalid/p/" + N["qword"] + "?ref=" + N["sent"], "url2": "https://shop2.invalid/q"}))

run("link_fetch", lambda: client.get("/__u8d/link"))
SC["link_fetch"]["outbound"] = OUTBOUND[:]
run("httpx_spans", lambda: client.get("/__u8d/httpx"))
run("levels", lambda: client.get("/__u8d/levels"))
run("headers", lambda: client.get("/__u8d/boom", headers={
    "X-Device-Fingerprint": N["fp"], "CF-Connecting-IP": N["ip"], "True-Client-IP": N["ip"],
    "X-Envoy-External-Address": N["ip"], "Forwarded": "for=" + N["ip"], "X-Custom-Note": N["note"],
    "X-Forwarded-For": N["ip"], "X-Real-IP": N["ip"], "User-Agent": "MYEZ-u8d/1.0",
    "Authorization": "Bearer u8d-token"}))
run("success", lambda: client.get("/__u8d/ok"))

for p in common: p.stop()

# Positive control: the plain sentinels survive the REAL scrubber in a region
# no U8d rule touches (extra), so a clean sweep can never be a pattern miss.
ITEMS.clear()
_plain = [N[k] for k in ("sent", "email", "host", "qword", "qword2", "qword3", "tok", "shtok", "ip", "local", "note")]
with sentry_sdk.new_scope() as _scope:
    _scope.set_extra("u8d_probe", " ".join(_plain))
    sentry_sdk.capture_message("u8d positive control")
sentry_sdk.flush()
CONTROL = [describe(k, raw) for k, raw in ITEMS]

print("RESULT " + json.dumps({"init": INIT, "supa_host": SUPA_HOST, "scenarios": SC, "control": CONTROL,
                              "network_attempts": ATTEMPTS}))
'''


def _scrub_tail(text: str) -> str:
    """Sanitise child output before it reaches an assertion message."""
    for key, needle in sorted(_V.items(), key=lambda kv: -len(kv[1])):
        text = re.sub(re.escape(needle), "<" + key[4:] + ">", text, flags=re.IGNORECASE)
    return text


@pytest.fixture(scope="module")
def u8d_child():
    """Run the real app + real init_sentry() + real SDK in ONE child process."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ENABLE_")}
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("SENTRY_DSN", "LIVE", "LOG_LEVEL"):
        env.pop(k, None)
    env.update(_V)
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
        f"stdout tail:\n{_scrub_tail(proc.stdout[-1500:])}"
    )
    return json.loads(lines[-1][len("RESULT "):])


# ------------------------------------------------------------------ helpers

def _case(child: dict, name: str) -> dict:
    assert "fatal" not in child, f"the child never drove the routes: {child}"
    return child["scenarios"][name]


def _items(case: dict, kind: str) -> list:
    return [it for it in case["items"] if it["type"] == kind]


def _events(case: dict) -> list:
    return _items(case, "event")


def _exc_events(case: dict) -> list:
    return [it for it in _events(case) if it.get("exc")]


def _leaks_under(items: list, prefixes: tuple) -> list:
    out = []
    for i, it in enumerate(items):
        for path, needles in it["leak"]:
            if path.startswith(prefixes):
                out.append((i, it["type"], path, needles))
    return out


def _one(items: list, what: str) -> dict:
    assert len(items) == 1, f"expected exactly one {what}, got {len(items)}: {items}"
    return items[0]


def _item_of(case: dict, kind: str) -> dict:
    if kind == "event":
        return _one(_exc_events(case) or _events(case), "event")
    return _one(_items(case, "transaction"), "transaction")


def _logger_event(case: dict, logger: str) -> dict:
    return _one([it for it in _events(case) if it.get("logger") == logger], f"event from {logger}")


def _log_crumbs(event: dict) -> list:
    return [c for c in event.get("crumbs", []) if c[2] != "http" and c[0] != "httplib"]


# ======================================================================= RED

R1_SCENARIOS = ("push_token", "share_post", "compare_post", "product_ab_amp", "unhandled")


@pytest.mark.timeout(600)
class TestU8dRedChannels:

    @pytest.mark.parametrize("scenario", R1_SCENARIOS)
    def test_u8d_red_r1_exception_values_blanked(self, u8d_child, scenario):
        """R1 (C1, C2, C3 exc_info): no sentinel in any exception.values[].value,
        and every value that is not an HTTPException is ''. Base: the raw text
        (APIError 'm <SENT>', the ShareTokenError text with the share token,
        'parse boom <SENT> <EMAIL>', the middleware chain)."""
        case = _case(u8d_child, scenario)
        leaks = _leaks_under(_events(case), ("/exception/values/N/value",))
        assert leaks == [], f"[R1 {scenario}] sentinel(s) in exception values: {leaks}"
        bad = [v for it in _exc_events(case) for v in it["exc"] if v[0] != "HTTPException" and v[1] != ""]
        assert bad == [], f"[R1 {scenario}] non-HTTPException values not blanked: {bad}"

    @pytest.mark.parametrize(
        "scenario,logger,expected",
        [
            ("compare_post", "app.services.structured_comparison_service", "Comparison error: <RuntimeError>"),
            ("cache_delete", "app.services.cache_service", "Cache delete error: <ConnectionError>"),
            ("cache_delete_hex", "app.services.cache_service", "Cache delete error: <RuntimeError>"),
            ("share_post", "app.api.share_routes", "Share token creation failed: <ShareTokenError>"),
            ("login_audit", "app.services.audit_service", "Failed to log audit event 'login_failed': <ConnectError>"),
            ("unhandled", "app.middleware.error_handler", "Unhandled RuntimeError: <RuntimeError>"),
            ("product_ab_amp", "app.middleware.error_handler", "Unhandled RuntimeError: <RuntimeError>"),
        ],
        ids=["compare_post", "cache_delete", "cache_delete_hex_ordering", "share_post_route_log",
             "login_audit", "unhandled_middleware", "product_ab_middleware"],
    )
    def test_u8d_red_r2_logentry_is_template_plus_type(self, u8d_child, scenario, logger, expected):
        """R2 (C2, C3): the handled exception text in logentry.message /
        formatted is replaced by <TypeName> (review correction 6: BEFORE the
        pattern walk, so the 32-hex + email text of cache_delete_hex becomes
        <RuntimeError>, not '[TOKEN_REDACTED] for <EMAIL>')."""
        ev = _logger_event(_case(u8d_child, scenario), logger)
        leaks = _leaks_under([ev], ("/logentry/",))
        assert leaks == [], f"[R2 {scenario}] sentinel(s) in logentry: {leaks}; formatted={ev['formatted']!r}"
        assert ev["formatted"] == expected, (scenario, ev["formatted"])
        assert ev["message"] == expected, (scenario, ev["message"])

    def test_u8d_red_r2_error_breadcrumb_redacted(self, u8d_child):
        """R2 crumb half (M5): the share route's ERROR log line is a breadcrumb
        on the 500 event (R7 = ERROR keeps ERROR crumbs); before_breadcrumb
        replaces the handled text. Base: the ShareTokenError text with the
        share token in breadcrumbs.values[].message."""
        ev = _one(_exc_events(_case(u8d_child, "share_post")), "share_post exception event")
        leaks = _leaks_under([ev], ("/breadcrumbs/",))
        assert leaks == [], f"[R2 crumb share_post] sentinel(s) in breadcrumbs: {leaks}"
        msgs = [c[3] for c in _log_crumbs(ev) if c[0] == "app.api.share_routes"]
        assert msgs == ["Share token creation failed: <ShareTokenError>"], msgs

    @pytest.mark.parametrize("scenario", ("compare_post", "login_audit", "unhandled_body"))
    @pytest.mark.parametrize("kind", ("event", "transaction"))
    def test_u8d_red_r3_no_request_body(self, u8d_child, scenario, kind):
        """R3 (C5): no request body on events and transactions. The option
        (max_request_body_size 'never') stops the SDK reading it; with a
        content-length the SDK still leaves an empty annotation, which the R3
        belt turns into '[Filtered]'. Accepted: no data key, '' or
        '[Filtered]'. Base: the JSON body (the user's query, the login email,
        the throwaway body)."""
        case = _case(u8d_child, scenario)
        items = _items(case, kind)
        assert items, (scenario, kind, [it["type"] for it in case["items"]])
        leaks = _leaks_under(items, ("/request/data",))
        assert leaks == [], f"[R3 {scenario} {kind}] sentinel(s) in request.data: {leaks}"
        datas = [it["request"]["data"] for it in items]
        assert all(d in (None, "", "[Filtered]") for d in datas), (scenario, kind, datas)

    @pytest.mark.parametrize(
        "scenario,kind",
        [
            ("compare_get_amp", "event"), ("compare_get_amp", "transaction"),
            ("product_ab_amp", "event"), ("product_ab_amp", "transaction"),
            ("unhandled", "event"), ("unhandled", "transaction"),
            ("url_compare_get", "transaction"),
        ],
        ids=["q_amp_hash-event", "q_amp_hash-transaction", "product_a_amp-event", "product_a_amp-transaction",
             "unknown_key_ref-event", "unknown_key_ref-transaction", "url1-transaction"],
    )
    def test_u8d_red_r4p_query_string_user_content_dropped(self, u8d_child, scenario, kind):
        """R4' (review correction 1, SR7): the SDK URL-DECODES the query string,
        so a user value with an encoded '&' / '#' splits; the decoded tails,
        unknown keys (ref) and the new PII keys (product_a, url1) leave no
        sentinel byte. Base: q=[QUERY_REDACTED]&+<QWORD2>+Gabbana+#<QWORD3>...,
        product_a=<QWORD>+&+<QWORD2>..., ref=<SENT>, url1=...<QWORD>?ref=<SENT>."""
        items = _items(_case(u8d_child, scenario), kind)
        assert items, (scenario, kind)
        leaks = _leaks_under(items, ("/request/query_string", "/request/url"))
        assert leaks == [], (
            f"[R4' {scenario} {kind}] sentinel(s) in the query string: {leaks}; "
            f"query_string={[it['request']['query_string'] for it in items]}")

    @pytest.mark.parametrize("where", ("span", "breadcrumb"))
    def test_u8d_red_r5_outbound_query_values_filtered(self, u8d_child, where):
        """R5 (C8): outbound http.query values are filtered on spans and on http
        breadcrumbs (a PostgREST email filter, a Scrape.do-shaped token). Base:
        span/crumb data.http.query 'select=id&email=eq.<EMAIL_PCT>' and
        'token=<TOK>&url=...<SENT>'."""
        case = _case(u8d_child, "httpx_spans")
        if where == "span":
            items, prefixes = _items(case, "transaction"), ("/spans/",)
        else:
            items, prefixes = _events(case), ("/breadcrumbs/",)
        assert items, where
        leaks = _leaks_under(items, prefixes)
        assert leaks == [], f"[R5 {where}] sentinel(s) in outbound span/crumb data: {leaks}"

    @pytest.mark.parametrize("where", ("span", "breadcrumb"))
    def test_u8d_red_r5_outbound_user_url_path_dropped(self, u8d_child, where):
        """R5 as corrected by review 4: the Link-mode fetch of the USER's URL
        through the REAL url_extraction_service.fetch_page keeps scheme + host
        only (shop.invalid is not an infra host). Base: span description
        'GET https://shop.invalid/products/<QWORD>-perfume', data.url, crumb
        data.url, http.query 'ref=<SENT>'."""
        case = _case(u8d_child, "link_fetch")
        if where == "span":
            items, prefixes = _items(case, "transaction"), ("/spans/",)
        else:
            items, prefixes = _events(case), ("/breadcrumbs/",)
        assert items, where
        leaks = _leaks_under(items, prefixes)
        assert leaks == [], f"[R5 link {where}] user URL path/query in outbound span/crumb: {leaks}"

    @pytest.mark.parametrize(
        "scenario,kind,field",
        [
            ("share_get_404", "transaction", "url"),
            ("share_get_500", "event", "url"),
            ("share_get_500", "event", "extra_path"),
            ("share_get_500", "transaction", "url"),
            ("referral_invite", "transaction", "url"),
        ],
        ids=["share_404-transaction-url", "share_500-event-url", "share_500-event-extra_path",
             "share_500-transaction-url", "referral_invite-transaction-url"],
    )
    def test_u8d_red_r6_capability_token_not_in_url(self, u8d_child, scenario, kind, field):
        """R6 (C7): the path segment after /api/v1/share/ and after
        /api/v1/referrals/invite/ becomes [token] in request.url and in
        extra.path. Base: the share / invite token."""
        it = _item_of(_case(u8d_child, scenario), kind)
        leaks = _leaks_under([it], ("/extra/path",) if field == "extra_path" else ("/request/url",))
        assert leaks == [], f"[R6 {scenario} {kind} {field}] capability token in the path: {leaks}"
        value = it["extra_path"] if field == "extra_path" else it["request"]["url"]
        prefix = "/api/v1/referrals/invite/" if scenario == "referral_invite" else "/api/v1/share/"
        assert isinstance(value, str) and value.endswith(prefix + "[token]"), (scenario, kind, field, value)

    @pytest.mark.parametrize("scenario", ("compare_post", "push_token", "levels"))
    def test_u8d_red_r7_no_info_or_warning_log_breadcrumb(self, u8d_child, scenario):
        """R7 = ERROR (Q4, SR2): no INFO or WARNING log line becomes a
        breadcrumb. Base: 'Text comparison request: <QWORD>...' (INFO), the
        push-token WARNING with the APIError dict and the email, the levels
        route's INFO/WARNING lines."""
        ev = _one(_exc_events(_case(u8d_child, scenario)) or _events(_case(u8d_child, scenario)), scenario)
        low = [c for c in _log_crumbs(ev) if c[1] in ("info", "warning", "debug")]
        leaks = _leaks_under([ev], ("/breadcrumbs/N/message",))
        assert leaks == [], f"[R7 {scenario}] sentinel(s) in log breadcrumbs: {leaks}"
        assert low == [], f"[R7 {scenario}] INFO/WARNING log breadcrumbs present: {low}"

    @pytest.mark.parametrize("kind", ("event", "transaction"))
    @pytest.mark.parametrize(
        "header",
        ("x-device-fingerprint", "cf-connecting-ip", "true-client-ip", "x-envoy-external-address",
         "forwarded", "x-custom-note"),
    )
    def test_u8d_red_r10_header_value_filtered(self, u8d_child, header, kind):
        """R10 (review correction 3): a header outside the allowlist {host,
        user-agent, accept, accept-encoding, accept-language, content-type,
        content-length, connection, x-request-id} ships '[Filtered]'. Base:
        the 64-hex device fingerprint, client IPs and a custom header value
        verbatim (the SDK filters only x-forwarded-for / x-real-ip)."""
        it = _item_of(_case(u8d_child, "headers"), kind)
        leaks = _leaks_under([it], ("/request/headers/" + header,))
        assert leaks == [], f"[R10 {header} {kind}] sentinel(s) in the header value: {leaks}"
        assert it["request"]["headers"].get(header) == "[Filtered]", (header, kind, it["request"]["headers"].get(header))

    @pytest.mark.parametrize("header", ("baggage", "sentry_trace"))
    def test_u8d_red_r12_link_fetch_sends_no_trace_headers(self, u8d_child, header):
        """R12 (SR4): the Link-mode request to the user's host carries neither a
        baggage nor a sentry-trace header (trace_propagation_targets=[]).
        Base: both present (targets ['.*'])."""
        out = _case(u8d_child, "link_fetch").get("outbound") or []
        assert out, "the Link-mode fetch reached no outbound transport (scenario broken)"
        sent = [o for o in out if o[header]]
        assert sent == [], f"[R12] outbound request(s) carried {header}: {sent}"

    @pytest.mark.parametrize(
        "option,expected",
        [
            ("max_request_body_size", "never"),
            ("crumb_level", 40),
            ("trace_propagation_targets", []),
            ("openai_include_prompts", False),
        ],
    )
    def test_u8d_red_options_effective(self, u8d_child, option, expected):
        """The EFFECTIVE client after the real init_sentry(): R3 option
        (max_request_body_size 'never'), R7 (LoggingIntegration breadcrumb
        level ERROR = 40), R12 (no propagation targets), SR8 (OpenAIIntegration
        include_prompts False). Base: 'medium', 20, ['.*'], True."""
        assert "fatal" not in u8d_child, u8d_child
        assert u8d_child["init"][option] == expected, (option, u8d_child["init"][option])


# ======================================================================= PIN

@pytest.mark.timeout(600)
class TestU8dPins:

    @pytest.mark.parametrize("scenario", sorted(EXPECTED_STATUS_BODY))
    def test_u8d_pin_r9_status_and_body_unchanged(self, u8d_child, scenario):
        """R9: status code and response body (request_id dropped) equal the
        base values for every scenario."""
        case = _case(u8d_child, scenario)
        assert (case["status"], case["body"]) == EXPECTED_STATUS_BODY[scenario], (scenario, case["status"], case["body"])

    @pytest.mark.parametrize("scenario", sorted(EXPECTED_EXC_TYPES))
    def test_u8d_pin_r9_exception_type_lists_unchanged(self, u8d_child, scenario):
        """R9 / Q3 (chains kept): the 500 stays visible with the base type list."""
        case = _case(u8d_child, scenario)
        assert [[v[0] for v in it["exc"]] for it in _exc_events(case)] == EXPECTED_EXC_TYPES[scenario], (
            scenario, [[v[0] for v in it["exc"]] for it in _exc_events(case)])

    @pytest.mark.parametrize("scenario", sorted(EXPECTED_EVENT_COUNT))
    def test_u8d_pin_r9_event_count_unchanged(self, u8d_child, scenario):
        """R9: the number of event items per scenario is the base number (R7
        moves breadcrumbs only, R1/R2 rewrite text only, the 503 drop is not
        widened)."""
        case = _case(u8d_child, scenario)
        assert len(_events(case)) == EXPECTED_EVENT_COUNT[scenario], (
            scenario, [(it.get("logger"), it.get("formatted")) for it in _events(case)])

    @pytest.mark.parametrize(
        "scenario,detail",
        [
            ("push_token", "{'code': 'INTERNAL_ERROR', 'error': 'Failed to register push token'}"),
            ("share_post", "{'code': 'SHARE_TOKEN_FAILED', 'error': 'Failed to create share link'}"),
        ],
    )
    def test_u8d_pin_http_exception_detail_kept(self, u8d_child, scenario, detail):
        """R1 exemption (spec edge case 8, review correction 8): the
        HTTPException value is our own literal detail and is kept (M2)."""
        ev = _one(_exc_events(_case(u8d_child, scenario)), scenario)
        assert ev["exc"][-1] == ["HTTPException", detail], ev["exc"]

    @pytest.mark.parametrize(
        "scenario,logger,expected",
        [
            ("login_audit", "app.services.auth_service", "Auth error in login: ConnectError"),
            ("levels", "app.u8d_probe", "forced constant error"),
        ],
        ids=["auth_type_only_line", "constant_line"],
    )
    def test_u8d_pin_clean_template_unchanged(self, u8d_child, scenario, logger, expected):
        """R2 must not rewrite a clean, type-only or constant template."""
        ev = _logger_event(_case(u8d_child, scenario), logger)
        assert (ev["formatted"], ev["level"]) == (expected, "error"), (ev["formatted"], ev["level"])

    @pytest.mark.parametrize(
        "scenario,kind,part",
        [
            ("compare_get_amp", "event", "nocache=true"),
            ("compare_get_amp", "transaction", "nocache=true"),
            ("product_ab_amp", "event", "region=bahrain"),
            ("product_ab_amp", "transaction", "region=bahrain"),
        ],
    )
    def test_u8d_pin_r4p_bookkeeping_readable(self, u8d_child, scenario, kind, part):
        """The pinned R21 contract: bookkeeping parameters stay readable."""
        it = _item_of(_case(u8d_child, scenario), kind)
        assert part in (it["request"]["query_string"] or ""), (scenario, kind, it["request"]["query_string"])

    @pytest.mark.parametrize(
        "scenario,needle",
        [("link_fetch", "https://shop.invalid"), ("httpx_spans", "/rest/v1/users"), ("httpx_spans", "/v1/models")],
        ids=["user_host_kept", "infra_supabase_path_kept", "infra_openai_path_kept"],
    )
    def test_u8d_pin_r5_host_and_infra_path_kept(self, u8d_child, scenario, needle):
        """R5 keeps the outbound host (triage) and, for infra hosts (the
        SUPABASE_URL host, api.openai.com), the path. Passes at base by
        construction (base keeps everything)."""
        txn = _one(_items(_case(u8d_child, scenario), "transaction"), "transaction")
        descs = [s[1] or "" for s in txn["spans"] if s[0] == "http.client"]
        assert any(needle in d for d in descs), (needle, descs)

    @pytest.mark.parametrize("kind", ("event", "transaction"))
    @pytest.mark.parametrize(
        "header,expected",
        [("x-forwarded-for", "[Filtered]"), ("x-real-ip", "[Filtered]"), ("authorization", "[REDACTED]"),
         ("user-agent", "MYEZ-u8d/1.0")],
    )
    def test_u8d_pin_r10_header_names(self, u8d_child, header, expected, kind):
        """x-forwarded-for stays filtered, the [REDACTED] names stay, the user
        agent (in the privacy sentence) stays readable."""
        it = _item_of(_case(u8d_child, "headers"), kind)
        assert it["request"]["headers"].get(header) == expected, (header, kind, it["request"]["headers"].get(header))

    def test_u8d_pin_sr4_spans_recorded_with_propagation_off(self, u8d_child):
        """SR4: spans are still recorded for the Link-mode request (passes at
        base trivially: propagation is on there)."""
        txn = _one(_items(_case(u8d_child, "link_fetch"), "transaction"), "transaction")
        assert [s for s in txn["spans"] if s[0] == "http.client"], txn["spans"]

    def test_u8d_pin_no_frame_vars(self, u8d_child):
        """C9 stays closed: no frame carries vars, the frame local is absent."""
        case = _case(u8d_child, "unhandled")
        ev = _one(_exc_events(case), "unhandled event")
        assert ev["frames_with_vars"] == 0, ev["frames_with_vars"]
        assert not any("local" in n for it in case["items"] for _, n in it["leak"]), case["items"]

    def test_u8d_pin_negative_control_success_path(self, u8d_child):
        """A success request: no event, and no item trips any sentinel flag."""
        case = _case(u8d_child, "success")
        assert _events(case) == [], _events(case)
        assert [it["leak"] for it in case["items"] if it["leak"]] == [], case["items"]

    def test_u8d_pin_positive_control_sentinels_survive_scrubber(self, u8d_child):
        """The plain sentinels survive the real before_send in a region no U8d
        rule rewrites (extra), so none is pattern-shaped and a clean sweep is
        real (U8c PIN7 idiom)."""
        assert "fatal" not in u8d_child, u8d_child
        ev = _one([it for it in u8d_child["control"] if it["type"] == "event"], "control event")
        seen = sorted({n for path, needles in ev["leak"] if path == "/extra/u8d_probe" for n in needles})
        expected = sorted(["sent", "email", "host", "qword", "qword2", "qword3", "tok", "shtok", "ip", "local", "note"])
        assert [n for n in expected if n not in seen] == [], (expected, seen)

    def test_u8d_pin_no_network_attempt(self, u8d_child):
        """Review correction 7: every failure is injected; the child's socket
        guard recorded no attempt in any scenario."""
        assert "fatal" not in u8d_child, u8d_child
        assert u8d_child["network_attempts"] == [], u8d_child["network_attempts"]

    def test_u8d_pin_real_init_sentry_memory_transport(self, u8d_child):
        """The real init_sentry() ran once with the memory transport and traces
        1.0; every request that reached a route yielded a transaction."""
        assert "fatal" not in u8d_child, u8d_child
        init = u8d_child["init"]
        assert (init["transport_is_memory"], init["init_calls"], init["traces_sample_rate"]) == (True, 1, 1.0), init
        for name, case in u8d_child["scenarios"].items():
            assert "transaction" in [it["type"] for it in case["items"]], name

    def test_u8d_pin_scenarios_took_the_injected_path(self, u8d_child):
        """The injected failures were reached (so a clean sweep has a cause)."""
        sc = u8d_child["scenarios"]
        assert sc["cache_delete"]["redis_delete_calls"] == 1, sc["cache_delete"]
        assert sc["cache_delete_hex"]["redis_delete_calls"] == 1, sc["cache_delete_hex"]
        assert (sc["login_audit"]["sign_in_calls"], sc["login_audit"]["audit_insert_calls"]) == (1, 1), sc["login_audit"]
        assert sc["product_ab_amp"]["service_calls"] == 1, sc["product_ab_amp"]
        assert sc["compare_get_amp"]["parse_calls"] == 2, sc["compare_get_amp"]
        assert [o["host"] for o in sc["link_fetch"]["outbound"]] == ["shop.invalid"], sc["link_fetch"]["outbound"]

    def test_u8d_pin_integration_list_unchanged(self, u8d_child):
        """SR8: the integration list is the base list (OpenAIIntegration's
        include_prompts is the only change)."""
        assert u8d_child["init"]["integrations"] == BASE_INTEGRATIONS, u8d_child["init"]["integrations"]

    def test_u8d_pin_privacy_options_kept(self, u8d_child):
        """R9: send_default_pii False and include_local_variables False stay;
        the event level stays ERROR."""
        init = u8d_child["init"]
        assert (init["send_default_pii"], init["include_local_variables"], init["event_level"]) == (False, False, 40), init

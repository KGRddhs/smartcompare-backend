"""B3-B (S79): Sign in with Apple token revocation on account deletion.

SPEC: .qa-s79/B3B_APPLE_REVOKE_UNIT_SPEC.md section 5.1, with the review
B3B_SPEC_REVIEW.md and the binding Fable rulings B1-B14 (RULINGS_B3.md).

Flag: ENABLE_APPLE_TOKEN_REVOCATION (default OFF, read per call). New module:
app/services/apple_siwa_service.py (never imported at module top here; every
body reaches it through _siwa(), which turns an absent module into an
AssertionError so every RED row fails on its own assertion, never on an
import error).

Harness:
- zero network: tests._retro_r_mig_sql.install_network_guard (asserted empty
  at teardown) on top of the conftest guard; Apple is an httpx.MockTransport
  handler installed through the module seam `_TRANSPORT` (spec 2.6); the
  flag-OFF / no-op PIN rows (R7, R8, R19, R20, R25) replace
  httpx.AsyncClient.send with a base-safe recorder that never reaches the
  original (ruling B1) and run with all four APPLE_SIWA_* variables set.
- the EC P-256 key, the RSA key, every JWT and every token value are built at
  run time (spec 1.8, ruling B10): no PEM header, JWT or key-shaped literal is
  in this file, and no literal is assigned to a name containing token,
  secret or key.
- logs: a handler on the `app` logger (DEBUG) collects every record.

PIN rows (green at base AND after GREEN): R7, R8, R19, R20, R25, R29.
Every other row is RED at base for the reason in its docstring.
"""

from __future__ import annotations

import asyncio
import base64
import copy
import dataclasses
import importlib
import importlib.util
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs

import httpx
import jwt
import pytest

from tests._retro_r_mig_sql import install_network_guard

REPO_ROOT = Path(__file__).resolve().parent.parent
SIWA_MOD = "app.services.apple_siwa_service"
SIWA_PATH = REPO_ROOT / "app" / "services" / "apple_siwa_service.py"
FLAG = "ENABLE_APPLE_TOKEN_REVOCATION"
SIWA_NAMES = (
    "APPLE_SIWA_TEAM_ID",
    "APPLE_SIWA_KEY_ID",
    "APPLE_SIWA_PRIVATE_KEY",
    "APPLE_SIWA_CLIENT_ID",
)
TEAM = "TEAMID" + "0" * 4
KID = "KEYID" + "0" * 5
CLIENT = "com.example.b3b"
AUD = "https://appleid.apple.com"
TOKEN_URL = "https://appleid.apple.com/auth/token"
REVOKE_URL = "https://appleid.apple.com/auth/revoke"
UID = "b3b-user-" + "7" * 8
EMAIL = "b3b-person" + "@example.invalid"
SUB = "b3b-apple-sub-" + "1" * 6
FORM_CT = "application/x-www-form-urlencoded"
TABLE = "apple_siwa_tokens"
_HS_WORD = "b3b" * 16  # throwaway HS256 signing word for synthetic id_tokens

# Base bodies of POST /api/v1/auth/social-login for the two mocked success
# results, recorded by running R19 (a PIN) at base b965c63b: FastAPI's compact
# JSON of _success(provider).
_BASE_BODY = {
    "apple": (
        b'{"success":true,"user":{"id":"b3b-user-77777777","email":"b3b-person@example.invalid",'
        b'"preferences_completed":false},"session":{"access_token":"sess-a","refresh_token":"sess-r",'
        b'"expires_at":1234567890},"message":"Signed in with apple"}'
    ),
    "google": (
        b'{"success":true,"user":{"id":"b3b-user-77777777","email":"b3b-person@example.invalid",'
        b'"preferences_completed":false},"session":{"access_token":"sess-a","refresh_token":"sess-r",'
        b'"expires_at":1234567890},"message":"Signed in with google"}'
    ),
}

SIWA_TEMPLATES = [
    re.compile(p)
    for p in (
        r"\[SIWA\] config missing: [A-Z_]+(,[A-Z_]+)*",
        r"\[SIWA\] client secret build failed: \w+",
        r"\[SIWA\] exchange status=\d+",
        r"\[SIWA\] exchange failed: \w+",
        r"\[SIWA\] exchange response unusable",
        r"\[SIWA\] exchange sub mismatch; not stored",
        r"\[SIWA\] store failed: \w+",
        r"\[SIWA\] stored",
        r"\[SIWA\] token read failed: \w+",
        r"\[SIWA\] no stored token; revoke skipped",
        r"\[SIWA\] revoke attempt=\d+ status=\d+",
        r"\[SIWA\] revoke attempt=\d+ failed: \w+",
        r"\[SIWA\] revoke failed: \w+",  # fix ruling FB1: the call-site belt
    )
]


# ---------------------------------------------------------------------------
# fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _b3b_env(monkeypatch):
    """Every row states its own flag / config; the limiter is off; zero network.

    app.main is imported FIRST: its import-time load_dotenv(override=True)
    re-runs the conftest credential sanitizer, which (after GREEN, R24) strips
    APPLE_SIWA_PRIVATE_KEY; a row that set the key before the first app import
    would lose it."""
    import app.main  # noqa: F401

    for name in (FLAG, *SIWA_NAMES, "ENABLE_SOCIAL_DEVICE_FINGERPRINT",
                 "ENABLE_ASYNC_REDIS_OFFLOAD", "ENABLE_CONSENT_REQUIRED",
                 "ENABLE_CONSENT_PERSIST"):
        monkeypatch.delenv(name, raising=False)
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    attempts = install_network_guard(monkeypatch)
    yield
    limiter.enabled = prior
    assert not attempts, f"B3-B tests must never touch the network: {attempts}"


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def logs():
    handler = _Collect()
    app_logger = logging.getLogger("app")
    prior = app_logger.level
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(handler)
    yield handler
    app_logger.removeHandler(handler)
    app_logger.setLevel(prior)


def _msgs(handler) -> list[str]:
    out = []
    for r in handler.records:
        try:
            out.append(r.getMessage())
        except Exception:  # noqa: BLE001
            out.append(str(r.msg))
    return out


def _siwa_records(handler) -> list[logging.LogRecord]:
    return [r for r in handler.records if str(r.msg).startswith("[SIWA]")]


def _siwa_lines(handler, level=None) -> list[str]:
    return [
        r.getMessage() for r in _siwa_records(handler)
        if level is None or r.levelno == level
    ]


@pytest.fixture(scope="session")
def keys():
    """An EC P-256 key (PKCS#8 PEM text, its PKCS#8 DER bytes + public key) and
    an RSA PEM, built at run time."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa

    ec_priv = ec.generate_private_key(ec.SECP256R1())
    pem = ec_priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    der = ec_priv.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pem = rsa_priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    return {"pem": pem, "pub": ec_priv.public_key(), "rsa": rsa_pem, "der": der}


def _siwa():
    spec = importlib.util.find_spec(SIWA_MOD)
    assert spec is not None, f"RED: {SIWA_MOD} does not exist (module absent)"
    return importlib.import_module(SIWA_MOD)


def _siwa_or_none():
    return importlib.import_module(SIWA_MOD) if importlib.util.find_spec(SIWA_MOD) else None


def _set_config(mp, pem, *, skip=None):
    values = {
        "APPLE_SIWA_TEAM_ID": TEAM,
        "APPLE_SIWA_KEY_ID": KID,
        "APPLE_SIWA_PRIVATE_KEY": pem,
        "APPLE_SIWA_CLIENT_ID": CLIENT,
    }
    for name, value in values.items():
        if name == skip:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, value)


def _id_jwt(claims) -> str:
    return jwt.encode(claims, _HS_WORD, algorithm="HS256")


def _apple_ok(sub=SUB, **extra):
    """Apple's 200 token response with three DISTINCT run-time values."""
    stamp = str(time.time_ns())
    body = {
        "access_token": "acc-" + stamp,
        "refresh_token": "ref-" + stamp[::-1],
        "id_token": _id_jwt({"sub": sub, "iss": AUD} if sub is not None else {"iss": AUD}),
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    body.update(extra)
    return body


class _Apple:
    """A recording Apple endpoint for httpx.MockTransport.

    script items: (status, body) | ("raise", ExcClass) | ("raise-plain", ExcClass)
    | ("hang", None). "raise-plain" raises a non-httpx exception built without
    the request keyword (fix ruling FB1)."""

    def __init__(self, script=(), events=None):
        self.script = list(script)
        self.requests: list[dict] = []
        self.events = events

    async def handler(self, request: httpx.Request):
        raw = (await request.aread()).decode("utf-8", "replace")
        multi = parse_qs(raw, keep_blank_values=True)
        self.requests.append({
            "method": request.method,
            "url": str(request.url),
            "ctype": request.headers.get("content-type", ""),
            "multi": multi,
            "form": {k: v[0] for k, v in multi.items()},
            "timeout": dict(request.extensions.get("timeout") or {}),
        })
        if self.events is not None and request.url.path.endswith("/revoke"):
            self.events.append("revoke")
        kind, body = self.script.pop(0) if self.script else (200, {})
        if kind == "raise":
            raise body("b3b transport failure", request=request)
        if kind == "raise-plain":
            raise body("b3b non-transport failure")
        if kind == "hang":
            await asyncio.sleep(30)
            return httpx.Response(200, json={})
        if isinstance(body, (dict, list)):
            return httpx.Response(kind, json=body)
        return httpx.Response(kind, text=str(body))


def _install_apple(mp, apple):
    siwa = _siwa_or_none()
    if siwa is not None:
        mp.setattr(siwa, "_TRANSPORT", httpx.MockTransport(apple.handler))


def _install_send_recorder(mp) -> list[str]:
    """Ruling B1: a base-safe replacement of httpx.AsyncClient.send that records
    and returns a canned 599, never calling the original."""
    sends: list[str] = []

    async def _send(self, request, *args, **kwargs):
        sends.append(f"{request.method} {request.url}")
        return httpx.Response(599, request=request)

    mp.setattr(httpx.AsyncClient, "send", _send)
    return sends


def _success(provider="apple"):
    return {
        "success": True,
        "user": {"id": UID, "email": EMAIL, "preferences_completed": False},
        "session": {
            "access_token": "sess-a",
            "refresh_token": "sess-r",
            "expires_at": 1234567890,
        },
        "message": f"Signed in with {provider}",
    }


class _Chain:
    def __init__(self, admin, name):
        self._admin = admin
        self._name = name

    def __getattr__(self, method):
        def _call(*args, **kwargs):
            self._admin.calls.append((self._name, method, args, kwargs))
            if method == "execute":
                return self._admin.on_execute(self._name)
            return self
        return _call


class _RecAdmin:
    """Recording admin client: table(name) chains record (name, method, args, kwargs)."""

    def __init__(self, *, execute_exc=None, data=None, events=None, stored=None,
                 delete_exc=None):
        self.calls: list[tuple] = []
        self.tables: list[str] = []
        self.execute_exc = execute_exc
        self.data = data
        self.events = events
        self.stored = stored
        self.auth = MagicMock()

        def _delete_user(uid):
            if events is not None:
                events.append("auth_delete")
            if delete_exc is not None:
                raise delete_exc
            return None

        self.auth.admin.delete_user.side_effect = _delete_user

    def table(self, name):
        self.tables.append(name)
        return _Chain(self, name)

    def on_execute(self, name):
        if self.execute_exc is not None:
            raise self.execute_exc
        if self.stored is not None and name == TABLE:
            if self.events is not None:
                self.events.append("read_token")
            return MagicMock(data=self.stored)
        return MagicMock(data=self.data if self.data is not None else [])


def _api_error(sentinel):
    from postgrest.exceptions import APIError

    return APIError({
        "message": "permission denied for table",
        "code": "42501",
        "hint": None,
        "details": f"Failing row contains ({sentinel}).",
    })


def _social(mp, body, *, flag=None, result=None, admin=None):
    """POST /api/v1/auth/social-login with sign_in_with_social mocked."""
    from fastapi.testclient import TestClient

    from app.main import app

    if flag is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, flag)
    provider = body.get("provider", "apple")
    result = result if result is not None else _success(provider)
    sign = AsyncMock(return_value=copy.deepcopy(result))
    admin = admin if admin is not None else _RecAdmin()
    gac = MagicMock(return_value=admin)
    supa = MagicMock()
    with patch("app.api.auth_routes.sign_in_with_social", new=sign), \
            patch("app.services.auth_service.get_admin_client", new=gac), \
            patch("app.api.auth_routes.get_admin_supabase_client", new=supa):
        response = TestClient(app).post("/api/v1/auth/social-login", json=body)
    return response, sign, gac, supa, admin


def _apple_body(code="code-" + "9" * 6, **extra):
    body = {
        "provider": "apple",
        "id_token": _id_jwt({"sub": SUB, "aud": CLIENT}),
        "nonce": "nonce-word",
    }
    if code is not _MISSING:
        body["authorization_code"] = code
    body.update(extra)
    return body


_MISSING = object()


async def _delete(events, admin_factory, *, cascade_exc=None):
    from app.services import auth_service

    async def _cascade(uid):
        events.append("cascade")
        if cascade_exc is not None:
            raise cascade_exc
        return True

    gac = MagicMock(side_effect=admin_factory)
    with patch("app.services.database_service.delete_user_data_cascade", new=_cascade), \
            patch("app.services.auth_service.get_admin_client", new=gac), \
            patch("app.services.auth_service.delete_cached", create=True,
                  side_effect=lambda key: events.append("purge")):
        result = await auth_service.delete_user_account(UID)
    return result, gac


def _cfg_values(cfg):
    if isinstance(cfg, dict):
        return list(cfg.values())
    if isinstance(cfg, (tuple, list)):
        return list(cfg)
    if dataclasses.is_dataclass(cfg):
        return list(dataclasses.asdict(cfg).values())
    return list(vars(cfg).values())


def _check_client_secret(secret, pub, *, now=None):
    header = jwt.get_unverified_header(secret)
    assert header == {"alg": "ES256", "kid": KID}, f"client secret header {header}"
    claims = jwt.decode(secret, options={"verify_signature": False})
    assert set(claims) == {"iss", "iat", "exp", "aud", "sub"}, claims
    assert claims["iss"] == TEAM and claims["sub"] == CLIENT and claims["aud"] == AUD, claims
    assert claims["exp"] - claims["iat"] == 300, claims
    if now is not None:
        assert claims["iat"] == now, claims
    else:
        assert abs(claims["iat"] - time.time()) < 120, claims
    verified = jwt.decode(secret, pub, algorithms=["ES256"], audience=AUD,
                          options={"verify_exp": False})
    assert verified == claims
    return claims


def _exc_chain(exc) -> list[BaseException]:
    """exc and every __context__ / __cause__ link, each once."""
    out: list[BaseException] = []
    seen: set[int] = set()
    todo = [exc]
    while todo:
        e = todo.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        out.append(e)
        todo += [e.__context__, e.__cause__]
    return out


def _exc_chain_bytes(exc) -> list[bytes]:
    """Fix ruling FD2: every bytes value in the chain, among the args and the
    .object of a Unicode error (a decode error carries its whole input)."""
    out: list[bytes] = []
    for e in _exc_chain(exc):
        values = list(getattr(e, "args", ())) + [getattr(e, "object", None)]
        out += [bytes(v) for v in values if isinstance(v, (bytes, bytearray))]
    return out


def _exc_chain_texts(exc) -> list[str]:
    """str / repr / args of exc and of every __context__ / __cause__ link (FB4).
    Fix ruling FD2: also a str .object of a Unicode error, and every bytes
    value of the chain as its latin-1 text."""
    out: list[str] = []
    for e in _exc_chain(exc):
        out += [str(e), repr(e)]
        out += [str(a) for a in getattr(e, "args", ())]
        out += [repr(a) for a in getattr(e, "args", ())]
        obj = getattr(e, "object", None)
        if isinstance(obj, str):
            out.append(obj)
    out += [b.decode("latin-1") for b in _exc_chain_bytes(exc)]
    return out


def _assert_no_key_text_in_exception(exc, keys, *raw):
    """Fix ruling FB4 (kills S3): no PEM body line of the EC or RSA test key and
    no configured key text (as given or whitespace-joined) appears in str(exc),
    repr(exc), exc.args or anywhere in the __context__ / __cause__ chain.
    Fix ruling FD2 (kills E10, S3f): no 16-byte window of the EC key's PKCS#8
    DER appears in any bytes value of the chain (args, a Unicode error's
    .object), compared as bytes and as latin-1 text."""
    secrets: list[str] = []
    for pem in (keys["pem"], keys["rsa"]):
        secrets += [ln.strip() for ln in pem.splitlines()
                    if len(ln.strip()) >= 16 and not ln.startswith("-----")]
    for r in raw:
        if r:
            secrets += [r, "".join(r.split())]
    texts = "\n".join(_exc_chain_texts(exc))
    found = [s for s in secrets if s in texts]
    der = keys["der"]
    blobs = _exc_chain_bytes(exc)
    windows = [der[i:i + 16] for i in range(0, len(der) - 15, 8)]
    found += [w for w in windows
              if any(w in b for b in blobs) or w.decode("latin-1") in texts]
    if found:  # pytest.fail: the report never echoes the key text (fix ruling FC1)
        pytest.fail(f"key material in the exception chain: {len(found)} value(s)")


def _assert_clean_value_error(exc):
    """Fix ruling FC1 (kills S3e): the ValueError is raised outside any except
    block, so it carries no __context__ and no __cause__, and its message is
    the constant. Fix ruling FD4: reported through pytest.fail with a count
    only, so a regression never echoes the exception (or key bytes in it)
    into the pytest output."""
    failed = [
        type(exc) is not ValueError,
        exc.args != ("unparseable private key",),
        exc.__context__ is not None,
        exc.__cause__ is not None,
    ]
    if any(failed):
        pytest.fail(f"not the clean constant ValueError: {sum(failed)} check(s) failed")


class _B64Spy:
    """Fix ruling FC1 (kills S3d): stands in for the module's base64 and
    counts every b64decode call (delegating to the real one)."""

    def __init__(self):
        self.calls = 0

    def b64decode(self, *args, **kwargs):
        self.calls += 1
        return base64.b64decode(*args, **kwargs)


# ---------------------------------------------------------------------------
# R1-R5: the module (RED: module absent)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [(None, False), ("", False), ("false", False), ("0", False), ("no", False),
     ("enabled", False), ("true", True), ("1", True), ("yes", True), ("on", True),
     (" TRUE ", True)],
    ids=["unset", "empty", "false", "0", "no", "enabled", "true", "1", "yes", "on", "TRUE-padded"],
)
def test_b3b_r1_flag_reader_per_call(monkeypatch, value, expected):
    """R1 (RED: module absent): the reader is True exactly for true/1/yes/on
    (case- and space-insensitive) and is read per call (kills X1, X3)."""
    siwa = _siwa()
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert siwa.apple_token_revocation_enabled() is expected
    monkeypatch.setenv(FLAG, "true")
    assert siwa.apple_token_revocation_enabled() is True
    monkeypatch.setenv(FLAG, "false")
    assert siwa.apple_token_revocation_enabled() is False


@pytest.mark.parametrize("name", SIWA_NAMES)
@pytest.mark.parametrize("mode", ["missing", "blank"])
def test_b3b_r2_config_requires_all_four_names(monkeypatch, logs, name, mode):
    """R2 (RED: module absent): any missing / blank name -> None and exactly one
    WARNING '[SIWA] config missing: <NAME>' carrying no value; all four set ->
    the four stripped values."""
    siwa = _siwa()
    sentinels = {n: f"word{i}{n[-3:].lower()}" for i, n in enumerate(SIWA_NAMES)}
    for n, v in sentinels.items():
        monkeypatch.setenv(n, f"  {v}  ")
    cfg = siwa._siwa_config()
    assert cfg is not None
    assert sorted(_cfg_values(cfg)) == sorted(sentinels.values()), cfg
    assert not _siwa_lines(logs, logging.WARNING)
    if mode == "missing":
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, "  ")
    assert siwa._siwa_config() is None
    warnings = _siwa_lines(logs, logging.WARNING)
    assert warnings == [f"[SIWA] config missing: {name}"], warnings
    for other, v in sentinels.items():
        assert all(v not in m for m in _msgs(logs)), f"value of {other} logged"


def _key_forms(keys):
    pem = keys["pem"]
    b64 = base64.b64encode(pem.encode("ascii")).decode("ascii")
    return {
        "pem-real-newlines": pem,
        "pem-literal-backslash-n": pem.strip().replace("\n", "\\n"),
        "base64": b64,
        "base64-wrapped-76": "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76)),
        "pem-space-joined": " ".join(pem.strip().split("\n")),
    }


def _bad_key_forms(keys):
    """Fix ruling FC1 / FC2: key values that must be refused with a clean
    ValueError. The non-ASCII characters are written as escapes (the file
    stays pure ASCII); the last form is base64 of an ASCII label line plus
    the generated PEM, which decodes to non-PEM-first text that IS key
    material (the second ValueError site). Fix ruling FD1 (kills E1, E1F,
    E9): three PEM-prefixed values whose non-ASCII character sits AFTER the
    armour prefix (a trailing U+201D, a U+00A0 right before a newline, a
    U+200B inside the first body line). FD2 (kills E10, S3f): the base64 of
    the key's PKCS#8 DER, which decodes to non-ASCII bytes. FD3 (kills E11):
    the base64 of the PEM wrapped in ASCII double quotes (the strict decode
    refuses it)."""
    pem = keys["pem"]
    labelled = ("Bag Attributes\n    friendlyName: b3b-label\n" + pem).encode("ascii")
    body = [ln for ln in pem.splitlines() if ln and not ln.startswith("-----")][0]
    pem_b64 = base64.b64encode(pem.encode("ascii")).decode("ascii")
    return {
        "bom-pem": "\ufeff" + pem,
        "smart-quoted-pem": "\u201c" + pem + "\u201d",
        "zwsp-pem": "\u200b" + pem,
        "base64-of-labelled-pem": base64.b64encode(labelled).decode("ascii"),
        "pem-trailing-smart-quote": pem.strip() + "\u201d",
        "pem-nbsp-inside": pem.replace(body + "\n", body + "\u00a0\n", 1),
        "pem-zwsp-inside-body": pem.replace(body, body[:10] + "\u200b" + body[10:], 1),
        "base64-of-der-p8": base64.b64encode(keys["der"]).decode("ascii"),
        "base64-quoted": '"' + pem_b64 + '"',
    }


_NON_ASCII_FORMS = ("bom-pem", "smart-quoted-pem", "zwsp-pem", "pem-trailing-smart-quote",
                    "pem-nbsp-inside", "pem-zwsp-inside-body")


@pytest.mark.parametrize(
    "form",
    ["pem-real-newlines", "pem-literal-backslash-n", "base64", "base64-wrapped-76",
     "pem-space-joined", "garbage", "rsa", "bom-pem", "smart-quoted-pem", "zwsp-pem",
     "base64-of-labelled-pem", "pem-trailing-smart-quote", "pem-nbsp-inside",
     "pem-zwsp-inside-body", "base64-of-der-p8", "base64-quoted"],
)
def test_b3b_r3_private_key_forms(monkeypatch, keys, form):
    """R3 (RED: module absent; kills X9, X10): the three accepted key forms
    (plus wrapped base64 and a space-joined PEM, ruling B9) build a client
    secret that verifies with the generated public key at the real clock;
    garbage -> ValueError, an RSA key -> InvalidKeyError. Fix ruling FB4
    (kills S3): for garbage and RSA, neither the exception from
    build_client_secret nor the one from _normalise_private_key carries
    key text anywhere in its chain. Fix ruling FC1 / FC2 (kills S3b, S3d,
    S3e): a BOM-prefixed, smart-quoted or ZWSP-prefixed PEM and the base64
    of a labelled PEM -> ValueError from both functions, no key text in the
    chain, no __context__ / __cause__; non-ASCII input is never decoded.
    Fix ruling FD1-FD3 (kills E1, E1F, E9, E10, S3f, E11): the same for a
    PEM-prefixed value with a non-ASCII character after the armour (0
    decodes), the base64 of the key's PKCS#8 DER (no DER bytes anywhere in
    the chain; 2 decodes) and a double-quoted base64 PEM (2 decodes)."""
    siwa = _siwa()
    if form == "garbage":
        _set_config(monkeypatch, "garbage-not-a-pem")
        with pytest.raises(ValueError) as built:
            siwa.build_client_secret(siwa._siwa_config())
        _assert_no_key_text_in_exception(built.value, keys, "garbage-not-a-pem")
        _assert_clean_value_error(built.value)
        with pytest.raises(ValueError) as normalised:
            siwa._normalise_private_key("garbage-not-a-pem")
        _assert_no_key_text_in_exception(normalised.value, keys, "garbage-not-a-pem")
        _assert_clean_value_error(normalised.value)
        return
    if form in _bad_key_forms(keys):
        raw = _bad_key_forms(keys)[form]
        spy = _B64Spy()
        monkeypatch.setattr(siwa, "base64", spy)
        _set_config(monkeypatch, raw)
        with pytest.raises(ValueError) as built:
            siwa.build_client_secret(siwa._siwa_config())
        _assert_no_key_text_in_exception(built.value, keys, raw)
        _assert_clean_value_error(built.value)
        with pytest.raises(ValueError) as normalised:
            siwa._normalise_private_key(raw)
        _assert_no_key_text_in_exception(normalised.value, keys, raw)
        _assert_clean_value_error(normalised.value)
        if form in _NON_ASCII_FORMS:
            assert spy.calls == 0, f"non-ASCII key text was decoded {spy.calls} time(s)"
        else:
            assert spy.calls == 2, f"control: the spy saw {spy.calls} decode(s)"
        return
    if form == "rsa":
        _set_config(monkeypatch, keys["rsa"])
        with pytest.raises(jwt.exceptions.InvalidKeyError) as built:
            siwa.build_client_secret(siwa._siwa_config())
        _assert_no_key_text_in_exception(built.value, keys, keys["rsa"])
        return
    _set_config(monkeypatch, _key_forms(keys)[form])
    secret = siwa.build_client_secret(siwa._siwa_config())
    assert isinstance(secret, str)
    claims = jwt.decode(secret, keys["pub"], algorithms=["ES256"], audience=AUD)
    assert claims["iss"] == TEAM and claims["sub"] == CLIENT


def test_b3b_r4_client_secret_shape(monkeypatch, keys):
    """R4 (RED: module absent; kills X4-X8): header exactly {alg, kid}; claims
    exactly {iss, iat, exp, aud, sub}; exp - iat == 300 (ruling B2: verified
    with verify_exp False); the signature is the 64-byte JOSE r||s."""
    siwa = _siwa()
    _set_config(monkeypatch, keys["pem"])
    now = 1_700_000_000
    secret = siwa.build_client_secret(siwa._siwa_config(), now=now)
    claims = _check_client_secret(secret, keys["pub"], now=now)
    assert claims == {"iss": TEAM, "iat": now, "exp": now + 300, "aud": AUD, "sub": CLIENT}
    assert 0 < claims["exp"] - claims["iat"] <= 15_777_000
    sig = secret.split(".")[2]
    assert len(base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))) == 64
    assert siwa.CLIENT_SECRET_TTL_SECONDS == 300


@pytest.mark.asyncio
async def test_b3b_r5_exchange_request_is_exact(monkeypatch, keys):
    """R5 (RED: module absent; kills X7, X11, X12, X14): exactly one POST to
    /auth/token, a form with exactly client_id, client_secret, code,
    grant_type=authorization_code; every timeout extension 5.0; the total
    bound seam is 6.0 (ruling B3); returns the parsed dict."""
    siwa = _siwa()
    _set_config(monkeypatch, keys["pem"])
    ok = _apple_ok()
    apple = _Apple([(200, ok)])
    _install_apple(monkeypatch, apple)
    assert siwa._HTTP_TIMEOUT == 5.0
    assert siwa._CALL_DEADLINE == 6.0
    out = await siwa.exchange_authorization_code("code-r5")
    assert out == ok
    assert len(apple.requests) == 1, apple.requests
    req = apple.requests[0]
    assert req["method"] == "POST" and req["url"] == TOKEN_URL, req
    assert FORM_CT in req["ctype"], req["ctype"]
    assert set(req["multi"]) == {"client_id", "client_secret", "code", "grant_type"}, req["multi"]
    assert all(len(v) == 1 for v in req["multi"].values()), req["multi"]
    assert req["form"]["grant_type"] == "authorization_code"
    assert req["form"]["client_id"] == CLIENT and req["form"]["code"] == "code-r5"
    _check_client_secret(req["form"]["client_secret"], keys["pub"])
    assert req["timeout"] and set(req["timeout"].values()) == {5.0}, req["timeout"]


# ---------------------------------------------------------------------------
# R6-R11, R19, R21, R25-R28: social-login
# ---------------------------------------------------------------------------

_R6_CODE = "code-" + "9" * 6


@pytest.mark.parametrize("sent", ["plain", "padded-code"])
def test_b3b_r6_social_login_apple_with_code_stores_the_token(monkeypatch, keys, logs, sent):
    """R6 (RED: zero exchange requests, zero upserts; kills X19, X20): flag ON,
    Apple 200 with a matching sub -> 200, body byte-equal to flag OFF, one
    exchange, the admin calls are exactly upsert(payload, on_conflict=user_id)
    + execute, the stored value is the REFRESH token, one INFO '[SIWA] stored'.
    Fix ruling FC4 (kills X52): a code sent with surrounding whitespace is
    exchanged STRIPPED (the exchange form's code equals the bare code)."""
    _set_config(monkeypatch, keys["pem"])
    ok = _apple_ok()
    apple = _Apple([(200, ok)])
    _install_apple(monkeypatch, apple)
    body = _apple_body(code=_R6_CODE if sent == "plain" else "  " + _R6_CODE + " \t")
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true")
    resp_off, _, _, _, admin_off = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200, resp_on.text
    assert resp_on.content == resp_off.content
    assert len(apple.requests) == 1, f"exchange requests: {len(apple.requests)}"
    assert apple.requests[0]["multi"].get("code") == [_R6_CODE], "code not stripped"
    assert len(admin.calls) == 2, admin.calls
    (t1, m1, a1, k1), (t2, m2, a2, k2) = admin.calls
    assert (t1, m1, k1) == (TABLE, "upsert", {"on_conflict": "user_id"}), admin.calls[0]
    assert (t2, m2, a2, k2) == (TABLE, "execute", (), {}), admin.calls[1]
    payload = a1[0]
    assert set(payload) == {"user_id", "refresh_token", "updated_at"}, payload
    assert payload["user_id"] == UID
    assert payload["refresh_token"] == ok["refresh_token"]
    assert payload["refresh_token"] not in (ok["access_token"], ok["id_token"])
    stamp = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))
    assert stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, payload
    assert "[SIWA] stored" in _siwa_lines(logs, logging.INFO), _siwa_lines(logs)
    assert admin_off.calls == []


@pytest.mark.parametrize("code", [_MISSING, None, "", 123, " \t  "],
                         ids=["absent", "null", "empty", "int", "whitespace"])
def test_b3b_r7_no_code_no_call(monkeypatch, keys, logs, code):
    """R7 PIN (ruling B1; kills X18; fix ruling FB5 adds the whitespace-only
    code, which kills X51): flag ON, config set, apple without a usable code:
    zero sends, zero admin table() calls, zero [SIWA] records, body byte-equal
    to flag OFF."""
    _set_config(monkeypatch, keys["pem"])
    sends = _install_send_recorder(monkeypatch)
    body = _apple_body(code=code)
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true")
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200, resp_on.text
    assert resp_on.content == resp_off.content
    assert sends == [], sends
    assert admin.tables == [], admin.tables
    assert _siwa_records(logs) == [], _siwa_lines(logs)


def test_b3b_r8_google_never_exchanges(monkeypatch, keys, logs):
    """R8 PIN (ruling B1; kills X17): flag ON, config set, provider google WITH an
    authorization_code: zero sends, zero table() calls, zero [SIWA] records,
    body unchanged."""
    _set_config(monkeypatch, keys["pem"])
    sends = _install_send_recorder(monkeypatch)
    body = {"provider": "google", "id_token": _id_jwt({"sub": SUB}),
            "authorization_code": "code-google"}
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true")
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200, resp_on.text
    assert resp_on.content == resp_off.content
    assert sends == [], sends
    assert admin.tables == [], admin.tables
    assert _siwa_records(logs) == [], _siwa_lines(logs)


_B64_DER = object()  # marker: replaced at run time (fix ruling FD2)

_R9_CASES = {
    "apple-400": ([(400, {"error": "B3BSENTINELERR"})], None, None, "[SIWA] exchange status=400"),
    "apple-500": ([(500, {"error": "B3BSENTINELERR"})], None, None, "[SIWA] exchange status=500"),
    "connect-timeout": ([("raise", httpx.ConnectTimeout)], None, None,
                        "[SIWA] exchange failed: ConnectTimeout"),
    "200-no-refresh": ([(200, {"access_token": "acc-x", "id_token": "idt"})], None, None,
                       "[SIWA] exchange response unusable"),
    "200-text-body": ([(200, "not json at all")], None, None, "[SIWA] exchange response unusable"),
    "name-missing": ([], "APPLE_SIWA_KEY_ID", None, "[SIWA] config missing: APPLE_SIWA_KEY_ID"),
    "garbage-key": ([], None, "garbage-not-a-pem", "[SIWA] client secret build failed: ValueError"),
    # fix ruling FD2 (kills E10, S3f): _B64_DER stands for the base64 of the
    # key's PKCS#8 DER, built at run time from the keys fixture
    "der-key": ([], None, _B64_DER, "[SIWA] client secret build failed: ValueError"),
    "upsert-raises": ("ok", None, None, "[SIWA] store failed: APIError"),
}


@pytest.mark.parametrize("case", list(_R9_CASES))
def test_b3b_r9_exchange_failure_never_fails_sign_in(monkeypatch, keys, logs, case):
    """R9 (RED: no WARNING line exists; kills X15, X20, X21, X30): every Apple /
    config / store failure keeps 200 and the flag-OFF body, logs exactly its
    2.9 WARNING once, stores nothing (one attempt in the upsert case) and leaks
    no sentinel, code, token, client secret, PEM line or id_token. Fix ruling
    FD2 (kills E10, S3f): the base64 of the key's PKCS#8 DER logs the
    ValueError line, and neither exception carries key text or DER bytes."""
    script, skip, bad_pem, expected = _R9_CASES[case]
    if bad_pem is _B64_DER:
        bad_pem = base64.b64encode(keys["der"]).decode("ascii")
    _set_config(monkeypatch, bad_pem or keys["pem"], skip=skip)
    ok = _apple_ok()
    if script == "ok":
        script = [(200, ok)]
        admin = _RecAdmin(execute_exc=_api_error("B3BSENTINELROW"))
    else:
        admin = _RecAdmin()
    apple = _Apple(script)
    _install_apple(monkeypatch, apple)
    body = _apple_body(code="code-r9-" + case)
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true", admin=admin)
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200, resp_on.text
    assert resp_on.content == resp_off.content
    warnings = _siwa_lines(logs, logging.WARNING)
    assert warnings == [expected], warnings
    upserts = [c for c in admin.calls if c[1] == "upsert"]
    assert len(upserts) == (1 if case == "upsert-raises" else 0), admin.calls
    leaks = ["B3BSENTINELERR", "B3BSENTINELROW", body["authorization_code"], body["id_token"],
             ok["refresh_token"], ok["access_token"], ok["id_token"]]
    leaks += [r["form"].get("client_secret") for r in apple.requests if r["form"].get("client_secret")]
    leaks += [ln for ln in keys["pem"].splitlines() if ln and not ln.startswith("-----")]
    text = "\n".join(_msgs(logs))
    found = [s for s in leaks if s and s in text]
    assert not found, f"leaked into the logs: {len(found)} value(s)"
    if case in ("garbage-key", "der-key"):
        # fix ruling FB4 (kills S3): the exceptions themselves carry no key text
        siwa = _siwa()
        with pytest.raises(ValueError) as built:
            siwa.build_client_secret(siwa._siwa_config())
        _assert_no_key_text_in_exception(built.value, keys, bad_pem)
        with pytest.raises(ValueError) as normalised:
            siwa._normalise_private_key(bad_pem)
        _assert_no_key_text_in_exception(normalised.value, keys, bad_pem)


@pytest.mark.parametrize("variant", ["other-sub", "no-sub", "undecodable"])
def test_b3b_r10_sub_mismatch_is_not_stored(monkeypatch, keys, logs, variant):
    """R10 (RED: no exchange happens, so the WARNING is absent; kills X16):
    Apple's id_token sub missing / unequal / undecodable -> zero upserts, one
    WARNING '[SIWA] exchange sub mismatch; not stored', 200, body unchanged."""
    _set_config(monkeypatch, keys["pem"])
    if variant == "other-sub":
        ok = _apple_ok(sub="someone-else")
    elif variant == "no-sub":
        ok = _apple_ok(sub=None)
    else:
        ok = _apple_ok()
        ok["id_token"] = "not-a-jwt"
    apple = _Apple([(200, ok)])
    _install_apple(monkeypatch, apple)
    body = _apple_body()
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true")
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200 and resp_on.content == resp_off.content
    assert _siwa_lines(logs, logging.WARNING) == ["[SIWA] exchange sub mismatch; not stored"], \
        _siwa_lines(logs)
    assert [c for c in admin.calls if c[1] == "upsert"] == [], admin.calls


def test_b3b_r11_exchange_is_single_shot_and_bounded(monkeypatch, keys):
    """R11 (RED: zero requests; kills X13, X14): Apple 500 then 200 scripted ->
    exactly ONE request on the sign-in path; its timeout extensions are 5.0."""
    _set_config(monkeypatch, keys["pem"])
    apple = _Apple([(500, {}), (200, _apple_ok())])
    _install_apple(monkeypatch, apple)
    resp, _, _, _, admin = _social(monkeypatch, _apple_body(), flag="true")
    assert resp.status_code == 200
    assert len(apple.requests) == 1, f"exchange requests: {len(apple.requests)}"
    assert set(apple.requests[0]["timeout"].values()) == {5.0}, apple.requests[0]["timeout"]
    assert admin.calls == []


_R19_BODIES = {
    "apple-code": lambda: _apple_body(),
    "apple-no-code": lambda: _apple_body(code=_MISSING),
    "google-code": lambda: {"provider": "google", "id_token": "header.payload.signature",
                            "authorization_code": "code-google"},
    "apple-5000-code": lambda: _apple_body(code="c" * 5000),
    "apple-int-code": lambda: _apple_body(code=123),
    "apple-list-code": lambda: _apple_body(code=["x"]),
}


@pytest.mark.parametrize("body_id", list(_R19_BODIES))
@pytest.mark.parametrize("flag", [None, "false", "0", ""], ids=["unset", "false", "0", "empty"])
def test_b3b_r19_flag_off_social_login_identity(monkeypatch, keys, logs, flag, body_id):
    """R19 PIN (ruling B1; kills X2, X33, X34, X35): flag OFF, all four SIWA
    variables set: 200, the recorded base body, sign_in_with_social awaited once
    with the base arguments, zero admin / supabase-admin calls, zero sends,
    zero [SIWA] records."""
    from app.services.consent_service import consent_from_fields

    _set_config(monkeypatch, keys["pem"])
    sends = _install_send_recorder(monkeypatch)
    body = _R19_BODIES[body_id]()
    resp, sign, gac, supa, admin = _social(monkeypatch, body, flag=flag)
    assert resp.status_code == 200, resp.text
    assert resp.content == _BASE_BODY[body["provider"]], resp.content
    sign.assert_awaited_once_with(body["provider"], body["id_token"], body.get("nonce"),
                                  consent=consent_from_fields(None, None, None))
    gac.assert_not_called()
    supa.assert_not_called()
    assert admin.tables == []
    assert sends == [], sends
    assert _siwa_records(logs) == [], _siwa_lines(logs)


def test_b3b_r21_social_login_request_contract():
    """R21 (RED: at base the model has no authorization_code field; kills X35):
    provider facebook and a missing id_token stay 422; a non-str code
    validates to None; a str code is kept."""
    from fastapi.testclient import TestClient

    from app.api.auth_routes import SocialLoginRequest
    from app.main import app

    client = TestClient(app)
    assert client.post("/api/v1/auth/social-login",
                       json={"provider": "facebook", "id_token": "x"}).status_code == 422
    assert client.post("/api/v1/auth/social-login", json={"provider": "apple"}).status_code == 422
    assert "authorization_code" in SocialLoginRequest.model_fields, \
        "SocialLoginRequest has no authorization_code field"
    base = {"provider": "apple", "id_token": "x"}
    assert SocialLoginRequest.model_validate({**base, "authorization_code": 123}).authorization_code is None
    assert SocialLoginRequest.model_validate({**base, "authorization_code": ["x"]}).authorization_code is None
    assert SocialLoginRequest.model_validate({**base, "authorization_code": "abc"}).authorization_code == "abc"
    assert SocialLoginRequest.model_validate(base).authorization_code is None


@pytest.mark.parametrize("outcome", ["401", "terms-400"])
def test_b3b_r25_failed_sign_in_never_exchanges(monkeypatch, keys, logs, outcome):
    """R25 PIN (green at base; kills 'store moved above the success / consent
    checks'): flag ON, config set, a failed sign-in WITH a code keeps its
    status and flag-OFF body, zero sends, zero table() calls."""
    from app.services.consent_service import TERMS_ACCEPTANCE_REQUIRED

    _set_config(monkeypatch, keys["pem"])
    sends = _install_send_recorder(monkeypatch)
    if outcome == "401":
        result = {"success": False, "error": "Invalid token"}
        status = 401
    else:
        result = {"success": False, "code": TERMS_ACCEPTANCE_REQUIRED, "error": "terms"}
        status = 400
    body = _apple_body()
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true", result=result)
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None, result=result)
    assert resp_on.status_code == status == resp_off.status_code, resp_on.text
    assert resp_on.json() == resp_off.json() or (
        {k: v for k, v in resp_on.json().items() if k != "request_id"}
        == {k: v for k, v in resp_off.json().items() if k != "request_id"}
    )
    assert sends == [], sends
    assert admin.tables == [], admin.tables
    assert _siwa_records(logs) == [], _siwa_lines(logs)


@pytest.mark.parametrize("user_id", [None, ""], ids=["none", "empty"])
@pytest.mark.asyncio
async def test_b3b_r26_store_without_user_id_does_nothing(monkeypatch, keys, user_id):
    """R26 (RED: store_apple_refresh_token absent; kills the falsy-user-id guard
    removal): returns False, zero requests, zero admin calls."""
    from app.services import auth_service

    assert hasattr(auth_service, "store_apple_refresh_token"), \
        "auth_service.store_apple_refresh_token does not exist"
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    apple = _Apple([(200, _apple_ok())])
    _install_apple(monkeypatch, apple)
    gac = MagicMock(return_value=_RecAdmin())
    with patch("app.services.auth_service.get_admin_client", new=gac):
        out = await auth_service.store_apple_refresh_token(user_id, "code-r26", _id_jwt({"sub": SUB}))
    assert out is False
    assert apple.requests == []
    gac.assert_not_called()


@pytest.mark.asyncio
async def test_b3b_r27_total_bound_on_every_apple_call(monkeypatch, keys, logs):
    """R27 (RED: module absent; ruling B3, kills 'total bound removed / per-phase
    only'): a hanging Apple with the total bound seam at 0.2 s -> the exchange
    returns None within 1 s with one WARNING 'exchange failed: TimeoutError';
    the revoke makes two attempts, each 'failed: TimeoutError', and the
    deletion completes."""
    siwa = _siwa()
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setattr(siwa, "_CALL_DEADLINE", 0.2)
    apple = _Apple([("hang", None)])
    _install_apple(monkeypatch, apple)
    t0 = time.monotonic()
    out = await siwa.exchange_authorization_code("code-r27")
    assert out is None
    assert time.monotonic() - t0 < 1.0
    assert _siwa_lines(logs, logging.WARNING) == ["[SIWA] exchange failed: TimeoutError"]

    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    stored = [{"refresh_token": "stored-" + str(time.time_ns())}]
    apple2 = _Apple([("hang", None), ("hang", None)], events=events)
    _install_apple(monkeypatch, apple2)
    admin = _RecAdmin(events=events, stored=stored)
    t0 = time.monotonic()
    result, _ = await _delete(events, lambda: admin)
    assert result is True
    assert time.monotonic() - t0 < 2.0
    assert len(apple2.requests) == 2
    assert [m for m in _siwa_lines(logs) if "revoke attempt" in m] == [
        "[SIWA] revoke attempt=1 failed: TimeoutError",
        "[SIWA] revoke attempt=2 failed: TimeoutError",
    ]
    assert events.count("auth_delete") == 1


def test_b3b_r27b_sign_in_survives_a_hanging_exchange(monkeypatch, keys, logs):
    """R27 (route half; RED: module absent): with the bound at 0.2 s and a
    hanging Apple, social-login is 200 with the flag-OFF body."""
    siwa = _siwa()
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setattr(siwa, "_CALL_DEADLINE", 0.2)
    apple = _Apple([("hang", None)])
    _install_apple(monkeypatch, apple)
    body = _apple_body()
    resp_on, _, _, _, admin = _social(monkeypatch, body, flag="true")
    resp_off, _, _, _, _ = _social(monkeypatch, body, flag=None)
    assert resp_on.status_code == 200 and resp_on.content == resp_off.content
    assert "[SIWA] exchange failed: TimeoutError" in _siwa_lines(logs, logging.WARNING)
    assert admin.calls == []


@pytest.mark.asyncio
async def test_b3b_r28_client_secret_is_never_reused_past_its_ttl(monkeypatch, keys):
    """R28 (RED: module absent; kills a cached client secret): two exchanges
    with _now advanced by 301 s carry different iat / exp."""
    siwa = _siwa()
    _set_config(monkeypatch, keys["pem"])
    clock = [1_800_000_000.0]
    monkeypatch.setattr(siwa, "_now", lambda: clock[0])
    apple = _Apple([(200, _apple_ok()), (200, _apple_ok())])
    _install_apple(monkeypatch, apple)
    await siwa.exchange_authorization_code("code-a")
    clock[0] += 301
    await siwa.exchange_authorization_code("code-b")
    assert len(apple.requests) == 2
    c1, c2 = (jwt.decode(r["form"]["client_secret"], options={"verify_signature": False})
              for r in apple.requests)
    assert c2["iat"] - c1["iat"] == 301 and c2["exp"] - c1["exp"] == 301, (c1, c2)


# ---------------------------------------------------------------------------
# R12-R17, R20: account deletion
# ---------------------------------------------------------------------------

def _stored():
    return [{"refresh_token": "stored-" + str(time.time_ns())}]


@pytest.mark.asyncio
async def test_b3b_r12_delete_reads_then_cascade_purge_revoke_auth_delete(monkeypatch, keys):
    """R12 (RED: events lack read_token and revoke; kills X22-X24, X29): flag ON,
    a stored token T: read, cascade, 5 purges, revoke, auth delete; the revoke
    is one exact form POST to /auth/revoke; returns True."""
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    stored = _stored()
    apple = _Apple([(200, {})], events=events)
    _install_apple(monkeypatch, apple)
    admin = _RecAdmin(events=events, stored=stored)
    result, _ = await _delete(events, lambda: admin)
    assert events == ["read_token", "cascade"] + ["purge"] * 5 + ["revoke", "auth_delete"], events
    assert result is True
    assert len(apple.requests) == 1
    req = apple.requests[0]
    assert req["method"] == "POST" and req["url"] == REVOKE_URL, req
    assert FORM_CT in req["ctype"]
    assert set(req["multi"]) == {"client_id", "client_secret", "token", "token_type_hint"}, req["multi"]
    assert all(len(v) == 1 for v in req["multi"].values())
    assert req["form"]["token"] == stored[0]["refresh_token"]
    assert req["form"]["token_type_hint"] == "refresh_token"
    assert req["form"]["client_id"] == CLIENT
    _check_client_secret(req["form"]["client_secret"], keys["pub"])
    assert set(req["timeout"].values()) == {5.0}, req["timeout"]


@pytest.mark.parametrize("rows", [[], [{"refresh_token": ""}], [{"refresh_token": None}]],
                         ids=["no-row", "empty-token", "null-token"])
@pytest.mark.asyncio
async def test_b3b_r13_delete_without_a_stored_token(monkeypatch, keys, logs, rows):
    """R13 (RED: no read_token): flag ON, no usable stored token: read, cascade,
    5 purges, auth delete; zero requests; one INFO '[SIWA] no stored token;
    revoke skipped'."""
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    apple = _Apple([(200, {})], events=events)
    _install_apple(monkeypatch, apple)
    admin = _RecAdmin(events=events, stored=rows)
    result, _ = await _delete(events, lambda: admin)
    assert events == ["read_token", "cascade"] + ["purge"] * 5 + ["auth_delete"], events
    assert result is True
    assert apple.requests == []
    assert _siwa_lines(logs, logging.INFO) == ["[SIWA] no stored token; revoke skipped"], \
        _siwa_lines(logs)


_R14 = {
    "connecttimeout-200": ([("raise", httpx.ConnectTimeout), (200, {})],
                           ["attempt=1 failed: ConnectTimeout", "attempt=2 status=200"]),
    "500-200": ([(500, {}), (200, {})], ["attempt=1 status=500", "attempt=2 status=200"]),
    "429-200": ([(429, {}), (200, {})], ["attempt=1 status=429", "attempt=2 status=200"]),
    "400": ([(400, {"error": "invalid_request"})], ["attempt=1 status=400"]),
    "200": ([(200, {})], ["attempt=1 status=200"]),
    "503-503": ([(503, {}), (503, {})], ["attempt=1 status=503", "attempt=2 status=503"]),
    "readtimeout-twice": ([("raise", httpx.ReadTimeout), ("raise", httpx.ReadTimeout)],
                          ["attempt=1 failed: ReadTimeout", "attempt=2 failed: ReadTimeout"]),
    # fix ruling FB1: a non-transport exception is never retried (kills X49, S23)
    "runtime-error": ([("raise-plain", RuntimeError)], ["attempt=1 failed: RuntimeError"]),
    # fix ruling FB1: revoke_refresh_token itself raises; the call-site belt logs
    # it and the deletion continues (kills X50)
    "revoke-raises": ("revoke-raises", ["failed: RuntimeError"]),
}


@pytest.mark.parametrize("case", list(_R14))
@pytest.mark.asyncio
async def test_b3b_r14_revoke_retry_policy(monkeypatch, keys, logs, case):
    """R14 (RED: zero attempts; kills X25-X28): at most two attempts, the second
    only after a transport error, 429 or 5xx; the deletion returns True and
    the auth delete runs once; the log lines are attempt/status/type only.
    Fix ruling FB1: a non-transport exception (RuntimeError) is one attempt
    and a raising revoke_refresh_token is caught at the call site (one
    '[SIWA] revoke failed: RuntimeError' line). Fix ruling FB2 (kills S4): the
    failed: and non-200 status= lines are WARNING, the status=200 line INFO,
    and no [SIWA] record carries exc_info."""
    script, lines = _R14[case]
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    if script == "revoke-raises":
        apple = _Apple([], events=events)
        _install_apple(monkeypatch, apple)
        siwa = _siwa()

        async def _raising_revoke(token):
            events.append("revoke")
            raise RuntimeError("b3b revoke raised")

        monkeypatch.setattr(siwa, "revoke_refresh_token", _raising_revoke)
        attempts = 0
    else:
        apple = _Apple(script, events=events)
        _install_apple(monkeypatch, apple)
        attempts = len(lines)
    admin = _RecAdmin(events=events, stored=_stored())
    escaped = None
    try:
        result, _ = await _delete(events, lambda: admin)
    except Exception as exc:  # noqa: BLE001 -- reported as the assertion below
        escaped, result = type(exc).__name__, None
    assert escaped is None, f"{escaped} escaped delete_user_account"
    assert len(apple.requests) == attempts, f"attempts {len(apple.requests)} != {attempts}"
    assert result is True
    assert events.count("auth_delete") == 1, events
    assert events.index("auth_delete") > max(i for i, e in enumerate(events) if e == "revoke")
    expected = [f"[SIWA] revoke {x}" for x in lines]
    assert [m for m in _siwa_lines(logs) if "revoke" in m] == expected
    assert [m for m in _siwa_lines(logs, logging.WARNING) if "revoke" in m] == [
        m for m in expected if not m.endswith("status=200")]
    assert [m for m in _siwa_lines(logs, logging.INFO) if "revoke" in m] == [
        m for m in expected if m.endswith("status=200")]
    assert not [r for r in _siwa_records(logs) if r.exc_info], "a [SIWA] record carries exc_info"


@pytest.mark.parametrize("failure", ["execute-apierror", "admin-valueerror"])
@pytest.mark.asyncio
async def test_b3b_r15_token_read_failure_never_blocks(monkeypatch, keys, logs, failure):
    """R15 (RED: no WARNING; kills X28): the token read raising (a PostgREST
    APIError with a sentinel, or get_admin_client's ValueError) -> cascade,
    5 purges, auth delete; zero requests; one WARNING '[SIWA] token read
    failed: <Type>' without the sentinel; returns True."""
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    apple = _Apple([(200, {})], events=events)
    _install_apple(monkeypatch, apple)
    good = _RecAdmin(events=events, stored=_stored())
    pre_cascade_calls: list[int] = []
    if failure == "execute-apierror":
        bad = _RecAdmin(events=events, execute_exc=_api_error("B3BSENTINELREAD"))

        def factory():
            if "cascade" not in events:
                pre_cascade_calls.append(1)
                return bad
            return good
        expected_type = "APIError"
    else:
        def factory():
            if "cascade" not in events:
                pre_cascade_calls.append(1)
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set B3BSENTINELREAD")
            return good
        expected_type = "ValueError"
    result, _ = await _delete(events, factory)
    assert _siwa_lines(logs, logging.WARNING) == [f"[SIWA] token read failed: {expected_type}"], \
        _siwa_lines(logs)
    assert events == ["cascade"] + ["purge"] * 5 + ["auth_delete"], events
    assert pre_cascade_calls == [1]
    assert apple.requests == []
    assert result is True
    assert all("B3BSENTINELREAD" not in m for m in _msgs(logs))


@pytest.mark.asyncio
async def test_b3b_r16_cascade_failure_revokes_nothing(monkeypatch, keys):
    """R16 (RED: read_token absent; kills X22, X24): the read happened first,
    then the cascade raised: no purge, no revoke, no auth delete; the
    exception propagates."""
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    apple = _Apple([(200, {})], events=events)
    _install_apple(monkeypatch, apple)
    admin = _RecAdmin(events=events, stored=_stored())
    with pytest.raises(RuntimeError, match="cascade failed"):
        await _delete(events, lambda: admin, cascade_exc=RuntimeError("cascade failed"))
    assert events[:1] == ["read_token"], events
    assert events == ["read_token", "cascade"], events
    assert apple.requests == []


@pytest.mark.asyncio
async def test_b3b_r17_auth_delete_failure_after_revoke(monkeypatch, keys):
    """R17 (RED: zero revoke attempts; kills X23): the auth delete raising after
    exactly one successful revoke attempt; the exception propagates."""
    _set_config(monkeypatch, keys["pem"])
    monkeypatch.setenv(FLAG, "true")
    events: list[str] = []
    apple = _Apple([(200, {})], events=events)
    _install_apple(monkeypatch, apple)
    admin = _RecAdmin(events=events, stored=_stored(), delete_exc=RuntimeError("auth delete failed"))
    with pytest.raises(RuntimeError, match="auth delete failed"):
        await _delete(events, lambda: admin)
    assert len(apple.requests) == 1, f"revoke attempts {len(apple.requests)}"
    assert events == ["read_token", "cascade"] + ["purge"] * 5 + ["revoke", "auth_delete"], events


@pytest.mark.parametrize("flag", [None, "false", "0", ""], ids=["unset", "false", "0", "empty"])
@pytest.mark.asyncio
async def test_b3b_r20_flag_off_delete_identity(monkeypatch, keys, logs, flag):
    """R20 PIN (ruling B1; kills X2, X32): flag OFF, all four SIWA variables set:
    exactly the U8b events, get_admin_client called once and only after the
    purges, zero table() calls, zero sends, zero [SIWA] records, True."""
    _set_config(monkeypatch, keys["pem"])
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    sends = _install_send_recorder(monkeypatch)
    events: list[str] = []
    seen: list[list[str]] = []
    admin = _RecAdmin(events=events, stored=_stored())

    def factory():
        seen.append(list(events))
        return admin
    result, gac = await _delete(events, factory)
    assert result is True
    assert events == ["cascade"] + ["purge"] * 5 + ["auth_delete"], events
    assert gac.call_count == 1 and seen == [["cascade"] + ["purge"] * 5], seen
    assert admin.tables == [], admin.tables
    assert sends == [], sends
    assert _siwa_records(logs) == [], _siwa_lines(logs)


# ---------------------------------------------------------------------------
# R18: log hygiene across the scenarios
# ---------------------------------------------------------------------------

def test_b3b_r18_siwa_logs_are_type_and_status_only(monkeypatch, keys, logs):
    """R18 (RED: the control finds no [SIWA] record; kills X30, X31): R6, R9
    (Apple 400 with a sentinel body), R12, R14 (503 twice) and R14
    (ConnectTimeout then 200; fix ruling FB2, kills S4) replayed: every
    [SIWA] record is INFO / WARNING, without exc_info, matching a 2.7
    template; no record carries the code, any token, a client secret, a PEM
    line, either id_token or Apple's error body; no [SIWA] record carries the
    user id or the email."""
    _set_config(monkeypatch, keys["pem"])
    secrets_seen: list[str] = []
    # R6
    ok = _apple_ok()
    apple = _Apple([(200, ok)])
    _install_apple(monkeypatch, apple)
    b1 = _apple_body(code="code-r18-a")
    _social(monkeypatch, b1, flag="true")
    secrets_seen += [b1["authorization_code"], b1["id_token"], ok["refresh_token"],
                     ok["access_token"], ok["id_token"]]
    secrets_seen += [r["form"].get("client_secret", "") for r in apple.requests]
    # R9 400 with a sentinel error body
    apple = _Apple([(400, {"error": "B3BSENTINELAPPLE", "error_description": "B3BSENTINELDESC"})])
    _install_apple(monkeypatch, apple)
    b2 = _apple_body(code="code-r18-b")
    _social(monkeypatch, b2, flag="true")
    secrets_seen += [b2["authorization_code"], "B3BSENTINELAPPLE", "B3BSENTINELDESC"]
    secrets_seen += [r["form"].get("client_secret", "") for r in apple.requests]
    # R12, R14 (503 twice) and, fix ruling FB2, R14 (ConnectTimeout then 200)
    monkeypatch.setenv(FLAG, "true")
    for script in ([(200, {})], [(503, {}), (503, {})],
                   [("raise", httpx.ConnectTimeout), (200, {})]):
        events: list[str] = []
        stored = _stored()
        apple = _Apple(script, events=events)
        _install_apple(monkeypatch, apple)
        admin = _RecAdmin(events=events, stored=stored)
        asyncio.run(_delete(events, lambda admin=admin: admin))
        secrets_seen.append(stored[0]["refresh_token"])
        secrets_seen += [r["form"].get("client_secret", "") for r in apple.requests]
    secrets_seen += [ln for ln in keys["pem"].splitlines() if ln and not ln.startswith("-----")]

    siwa = _siwa_records(logs)
    assert siwa, "control: no [SIWA] record was logged by any scenario"
    for r in siwa:
        assert r.levelno in (logging.INFO, logging.WARNING), (r.levelname, r.getMessage())
        assert not r.exc_info, r.getMessage()
        assert any(t.fullmatch(r.getMessage()) for t in SIWA_TEMPLATES), r.getMessage()
        assert UID not in r.getMessage() and EMAIL not in r.getMessage()
    text = "\n".join(_msgs(logs))
    found = [s for s in secrets_seen if s and s in text]
    assert not found, f"{len(found)} sentinel value(s) reached a log record"


# ---------------------------------------------------------------------------
# R22-R24, R29: manifest, secret shapes, env safety, crypto pins
# ---------------------------------------------------------------------------

def _load_by_path(rel, name):
    import sys

    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_b3b_r22_new_module_hosts_are_in_the_apple_manifest_row():
    """R22 (RED: module absent, row lacks it; kills X40): the T7b scanner finds
    exactly {appleid.apple.com} in the new module; the manifest apple row
    lists the module and a host covering it; gate_flag stays null."""
    assert SIWA_PATH.is_file(), "app/services/apple_siwa_service.py does not exist"
    t7 = _load_by_path("tests/test_legal_docs_u8.py", "_b3b_legal_u8")
    hosts, _calls = t7._scan_source(SIWA_PATH.read_text(encoding="utf-8"))
    assert hosts == {"appleid.apple.com"}, hosts
    rows = json.loads((REPO_ROOT / "app" / "legal" / "processors.json").read_text(encoding="utf-8"))["rows"]
    apple = [r for r in rows if r.get("id") == "apple"]
    assert len(apple) == 1
    row = apple[0]
    assert "app/services/apple_siwa_service.py" in t7._row_modules(row), row
    assert any(t7._covers(h, "appleid.apple.com") for h in t7._row_hosts(row)), row
    assert row.get("gate_flag") is None


_PEM_RE = "-----" + "BEGIN (RSA |EC |OPENSSH )?PRIVATE " + "KEY-----"
_HOOK4_RE = re.compile(
    r"(\bsk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|" + _PEM_RE + ")"
)
_JWT_RE = re.compile("eyJ" + r"[A-Za-z0-9_-]{7,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
_CREDURL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s:@]+:[^/\s@]{12,}@")
_GMAIL = "@gmail" + ".com"
_PHONE_RE = re.compile(r"\+\d{1,3}[ -]?\d{3,4}[ -]?\d{4}\b")


def test_b3b_r23_no_secret_shapes_in_the_unit_files():
    """R23 (RED: the module and migration files are absent): the unit's added
    files exist and carry no hook credential shape, no JWT, no credentialed
    URL, no gmail address and no phone shape."""
    files = [
        SIWA_PATH,
        REPO_ROOT / "migrations" / "044_apple_siwa_tokens.sql",
        REPO_ROOT / "migrations" / "rollback" / "044_apple_siwa_tokens.sql",
        Path(__file__).resolve(),
        REPO_ROOT / "tests" / "test_migration_044_apple_siwa_tokens.py",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in files if not p.is_file()]
    assert not missing, f"unit files absent: {missing}"
    problems = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        for label, rx in (("hook4", _HOOK4_RE), ("jwt", _JWT_RE), ("credurl", _CREDURL_RE),
                          ("phone", _PHONE_RE)):
            if rx.search(text):
                problems.append(f"{p.name}: {label}")
        if _GMAIL in text:
            problems.append(f"{p.name}: gmail")
    assert not problems, problems


def test_b3b_r24_env_safety_clears_the_private_key():
    """R24 (RED: absent from CREDENTIALS_UNSET; kills X41): the sanitizer list
    names APPLE_SIWA_PRIVATE_KEY and strips it from an environment."""
    from tests import _env_safety

    assert "APPLE_SIWA_PRIVATE_KEY" in _env_safety.CREDENTIALS_UNSET
    env = {"APPLE_SIWA_PRIVATE_KEY": "word"}
    changed = _env_safety.neutralize_credentials(env)
    assert "APPLE_SIWA_PRIVATE_KEY" not in env and changed.get("APPLE_SIWA_PRIVATE_KEY", 0) is None
    assert os.environ.get("APPLE_SIWA_PRIVATE_KEY") is None


def test_b3b_r29_pyjwt_crypto_and_pins_present():
    """R29 PIN (ruling B8): PyJWT has its crypto backend, and requirements.txt
    pins both pyjwt== and cryptography== (a lock recompile that dropped the
    transitive pins would turn every exchange into a logged error)."""
    assert jwt.algorithms.has_crypto is True
    req = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"(?im)^pyjwt==\S+", req)
    assert re.search(r"(?im)^cryptography==\S+", req)


def test_b3b_r30_apple_client_keeps_tls_defaults():
    """R30 PIN (fix ruling FB3; kills S5): every httpx.AsyncClient(...) call in
    apple_siwa_service.py passes only the keywords timeout / transport (no
    positional argument, no ** splat) and never verify, trust_env, proxy or
    proxies; the one module-level _TRANSPORT assignment is the constant None and
    the live value is None (production uses httpx's default transport, TLS
    verified). Fix ruling FC3 (kills S5b): each AsyncClient's transport value
    is exactly the name _TRANSPORT and its timeout value exactly the name
    _HTTP_TIMEOUT; no call anywhere in the module (any callee) carries verify,
    trust_env, proxy or proxies; the module never names AsyncHTTPTransport or
    HTTPTransport."""
    import ast

    assert SIWA_PATH.exists(), "RED: app/services/apple_siwa_service.py is absent"
    tree = ast.parse(SIWA_PATH.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "AsyncClient":
                calls.append(node)
    assert calls, "control: no httpx.AsyncClient(...) call found in the module"
    forbidden = {"verify", "trust_env", "proxy", "proxies"}
    for call in calls:
        names = [k.arg for k in call.keywords]
        assert not call.args, f"line {call.lineno}: a positional argument"
        assert None not in names, f"line {call.lineno}: a ** splat could carry verify"
        assert set(names) <= {"timeout", "transport"}, f"line {call.lineno}: {names}"
        assert not set(names) & forbidden, f"line {call.lineno}: {names}"
        values = {k.arg: k.value for k in call.keywords}
        for kw, expected in (("transport", "_TRANSPORT"), ("timeout", "_HTTP_TIMEOUT")):
            value = values.get(kw)
            assert isinstance(value, ast.Name) and value.id == expected, (
                f"line {call.lineno}: {kw}= is not the bare name {expected}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            bad = forbidden & {k.arg for k in node.keywords}
            assert not bad, f"line {node.lineno}: a call carries {sorted(bad)}"
    transport_classes = {"AsyncHTTPTransport", "HTTPTransport"}
    named = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            named.add(node.id)
        elif isinstance(node, ast.Attribute):
            named.add(node.attr)
        elif isinstance(node, ast.alias):
            named.update({node.name.rsplit(".", 1)[-1], node.asname or ""})
    assert not named & transport_classes, sorted(named & transport_classes)
    assigns = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(getattr(t, "id", None) == "_TRANSPORT" for t in targets):
            assigns.append(node)
    assert len(assigns) == 1, f"{len(assigns)} module-level _TRANSPORT assignments"
    value = assigns[0].value
    assert isinstance(value, ast.Constant) and value.value is None, ast.dump(value)
    assert _siwa()._TRANSPORT is None

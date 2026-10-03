"""U13 -- the prod-HTTP harness scripts carry a credential only when opted in. RED file 2 of 2.

Spec (authoritative): docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md,
section 6 "File 2" (H01-H10), D9 + R10, as corrected by C7 (the smoke probe-12 bearer is
the ONE non-opt-in harness change) and ruled by UR1 (X-Admin-Key under the opt-in
HARNESS_SEND_ADMIN_KEY) and UR7 (verify_after_credits.py edited in place). Test ids are in
every node name. Expected at BASE eb86075e (UR10): 17 RED / 5 PIN.

Why opt-in (spec 2.8, measured): nine test modules set ADMIN_API_KEY at import, so in CI's
single process it is non-empty for practically every test; a harness that sent X-Admin-Key
"whenever ADMIN_API_KEY is set" would turn the W4-13 header pins RED in CI only. So every
node here sets or deletes HARNESS_SEND_ADMIN_KEY, ADMIN_API_KEY and
SEARCH_LOG_SYNTHETIC_TOKEN explicitly (`_env`).

Conventions: each script is loaded by path with importlib.util.spec_from_file_location
under a PRIVATE module name (registered only while its body executes -- dataclasses needs
it -- then removed; never the real name, never importlib.reload); the helpers this unit
creates (`harness_auth_headers` in eval_runner, `_harness_auth_headers` in the four
standalone scripts) are looked up with getattr INSIDE the bodies, so a RED is a test
failure, never a collection ERROR; every HTTP exchange goes to an httpx.MockTransport or
a recorder (zero network); the admin sentinel is `u13-admin-sentinel-key` (never an sk-
shape); pytest-asyncio strict, so every async node is marked.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
OPT_IN = "HARNESS_SEND_ADMIN_KEY"
ADMIN_ENV = "ADMIN_API_KEY"
SYN_TOKEN = "SEARCH_LOG_SYNTHETIC_TOKEN"

ADMIN_SENTINEL = "u13-admin-sentinel-key"
SYN_SENTINEL = "u13-synthetic-sentinel"
SMOKE_JWT = "u13.smoke.jwt"
BASE_URL = "http://u13.test"
HEAD_EVAL_HEADERS = {"accept", "accept-encoding", "connection", "host", "user-agent"}

SCRIPTS = {
    "eval_runner": REPO_ROOT / "scripts" / "eval_runner.py",
    "run_validation_matrix": REPO_ROOT / "scripts" / "run_validation_matrix.py",
    "bias_matrix_probe": REPO_ROOT / "scripts" / "bias_matrix_probe.py",
    "bundle_d_prod_smoke": REPO_ROOT / "scripts" / "bundle_d_prod_smoke.py",
    "verify_after_credits": (REPO_ROOT / "docs" / "investigations"
                             / "2026-09-29-session-69-state" / "verify_after_credits.py"),
}
# D9: eval_runner exposes harness_auth_headers() (run_eval -> cron_eval_nightly); each
# standalone script carries its own private _harness_auth_headers().
HELPERS = {
    "eval_runner": "harness_auth_headers",
    "run_validation_matrix": "_harness_auth_headers",
    "bias_matrix_probe": "_harness_auth_headers",
    "bundle_d_prod_smoke": "_harness_auth_headers",
    "verify_after_credits": "_harness_auth_headers",
}


def _env(mp, *, opt_in=None, key=None, token=None):
    """Set or delete every variable the harness reads (never inherit them)."""
    for name, value in ((OPT_IN, opt_in), (ADMIN_ENV, key), (SYN_TOKEN, token)):
        if value is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, value)


def _load(name):
    path = SCRIPTS[name]
    spec = importlib.util.spec_from_file_location(f"_s71_u13_private_{name}", path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


class _HttpxShim:
    """Stands in for a loaded script's module-level `httpx` name: the overridden
    attributes are recorders, everything else is the real httpx."""

    def __init__(self, **overrides):
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(httpx, name)


def _lower(headers):
    return {k.lower(): v for k, v in headers.items()}


# ===========================================================================
# H01-H04  eval_runner.run_eval (and so cron_eval_nightly)
# ===========================================================================
_EVAL_Q = [{"id": "u13-q1", "query": "a vs b", "category": "electronics", "region": "bahrain",
            "max_wall_seconds": 25.0}]


async def _eval_headers():
    mod = _load("eval_runner")
    seen: list = []

    def handler(request):
        seen.append(_lower(request.headers))
        return httpx.Response(200, json={"success": True})
    await mod.run_eval(_EVAL_Q * 2, base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return seen


@pytest.mark.asyncio
async def test_H01_run_eval_sends_admin_key_when_opted_in(monkeypatch):
    """RED H01: HARNESS_SEND_ADMIN_KEY=1 + ADMIN_API_KEY set -> every run_eval request
    carries x-admin-key == the key."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
    seen = await _eval_headers()
    assert len(seen) == 2, seen
    assert all(h.get("x-admin-key") == ADMIN_SENTINEL for h in seen), (
        f"run_eval sent no X-Admin-Key; request header names {[sorted(h) for h in seen]}")


@pytest.mark.asyncio
async def test_H02_run_eval_byte_identical_without_opt_in(monkeypatch):
    """PIN H02 (spec 2.8 collision; mutant X8): ADMIN_API_KEY SET, opt-in unset, token
    unset -> the request header set is exactly today's five headers."""
    _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL, token=None)
    seen = await _eval_headers()
    assert seen and all(set(h) == HEAD_EVAL_HEADERS for h in seen), [sorted(h) for h in seen]


@pytest.mark.asyncio
async def test_H03_run_eval_opt_in_without_a_key(monkeypatch):
    """PIN H03: opt-in set, ADMIN_API_KEY deleted -> no x-admin-key (and today's five
    headers)."""
    _env(monkeypatch, opt_in="1", key=None, token=None)
    seen = await _eval_headers()
    assert seen and all("x-admin-key" not in h for h in seen), [sorted(h) for h in seen]
    assert all(set(h) == HEAD_EVAL_HEADERS for h in seen), [sorted(h) for h in seen]


@pytest.mark.asyncio
async def test_H04_run_eval_sends_both_harness_headers(monkeypatch):
    """RED H04: opt-in + key + SEARCH_LOG_SYNTHETIC_TOKEN -> both x-admin-key and
    x-qaren-synthetic on every request (the merged headers of R10)."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL, token=SYN_SENTINEL)
    seen = await _eval_headers()
    assert len(seen) == 2, seen
    assert all(h.get("x-qaren-synthetic") == SYN_SENTINEL for h in seen), [sorted(h) for h in seen]
    assert all(h.get("x-admin-key") == ADMIN_SENTINEL for h in seen), (
        f"run_eval sent no X-Admin-Key beside the synthetic header; request header names "
        f"{[sorted(h) for h in seen]}")


# ===========================================================================
# H05-H06  run_validation_matrix.run_query (requests)
# ===========================================================================
_VM_RECORD = {"id": "u13-vm-1", "query": "a vs b", "category": "electronics",
              "region": "bahrain"}
_VM_WEIGHTS = {"price_accuracy": 0.25, "specs_correctness": 0.25,
               "winner_correctness": 0.30, "factual_claim_integrity": 0.20}


def _run_validation_query(mp):
    import requests as real_requests

    mod = _load("run_validation_matrix")
    captured: list = []

    class _Resp:
        status_code = 503

        def json(self):
            raise ValueError("u13: not json")

    class _FakeRequests:
        RequestException = real_requests.RequestException

        @staticmethod
        def get(url, **kwargs):
            captured.append({"url": url, "kwargs": kwargs})
            return _Resp()

    mp.setattr(mod, "requests", _FakeRequests)
    mod.run_query(BASE_URL, dict(_VM_RECORD), dict(_VM_WEIGHTS), 15.0, 5.0)
    return captured


def test_H05_validation_matrix_sends_admin_key_when_opted_in(monkeypatch):
    """RED H05: opted in -> requests.get(..., headers={"X-Admin-Key": key})."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
    captured = _run_validation_query(monkeypatch)
    assert len(captured) == 1, captured
    assert captured[0]["kwargs"].get("headers") == {"X-Admin-Key": ADMIN_SENTINEL}, (
        f"requests.get kwargs {sorted(captured[0]['kwargs'])} carry no X-Admin-Key header")


def test_H06_validation_matrix_unchanged_without_opt_in(monkeypatch):
    """PIN H06: key set, opt-in unset -> the call's kwargs carry NO `headers` key
    (exactly today's params + timeout)."""
    _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL)
    captured = _run_validation_query(monkeypatch)
    assert len(captured) == 1, captured
    assert "headers" not in captured[0]["kwargs"], sorted(captured[0]["kwargs"])
    assert set(captured[0]["kwargs"]) == {"params", "timeout"}, sorted(captured[0]["kwargs"])


# ===========================================================================
# H07  each script's helper, two states each
# ===========================================================================
@pytest.mark.parametrize("state", ["opted_in", "not_opted_in"])
@pytest.mark.parametrize("script", list(SCRIPTS))
def test_H07_each_script_helper(monkeypatch, script, state):
    """RED H07: the script's helper returns {"X-Admin-Key": key} when opted in and {}
    when not (ADMIN_API_KEY set in BOTH states -- the CI collision)."""
    if state == "opted_in":
        _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
        want = {"X-Admin-Key": ADMIN_SENTINEL}
    else:
        _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL)
        want = {}
    mod = _load(script)
    helper = getattr(mod, HELPERS[script], None)
    assert callable(helper), f"{script}: {HELPERS[script]}() is absent"
    assert helper() == want


# ===========================================================================
# H08  bias_matrix_probe._main_async client headers
# ===========================================================================
async def _run_bias(mp, tmp_path):
    mod = _load("bias_matrix_probe")
    built: list = []
    seen: list = []

    def handler(request):
        seen.append(_lower(request.headers))
        return httpx.Response(200, json={"success": True, "products": []})

    class _RecordingAsyncClient:
        def __init__(self, **kwargs):
            built.append(dict(kwargs))
            self._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

        async def __aenter__(self):
            await self._client.__aenter__()
            return self._client

        async def __aexit__(self, *exc):
            return await self._client.__aexit__(*exc)

    mp.setattr(mod, "httpx", _HttpxShim(AsyncClient=_RecordingAsyncClient))
    matrix = tmp_path / "u13_bias_matrix.json"
    matrix.write_text(json.dumps({"queries": [
        {"id": "u13-b1", "query": "a vs b", "category": "electronics", "region": "bahrain"},
    ]}), encoding="utf-8")
    args = argparse.Namespace(matrix=str(matrix), no_nocache=False, base_url=BASE_URL,
                              concurrency=1, timeout=5.0, json_out=None)
    await mod._main_async(args)
    return built, seen


@pytest.mark.asyncio
async def test_H08_bias_probe_client_carries_admin_key_when_opted_in(monkeypatch, tmp_path):
    """RED H08 (opted in): the probe's AsyncClient is constructed with
    headers={"X-Admin-Key": key} and the request carries it."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
    built, seen = await _run_bias(monkeypatch, tmp_path)
    assert len(built) == 1, built
    assert built[0].get("headers") == {"X-Admin-Key": ADMIN_SENTINEL}, (
        f"httpx.AsyncClient kwargs {sorted(built[0])} carry no X-Admin-Key header")
    assert seen and all(h.get("x-admin-key") == ADMIN_SENTINEL for h in seen), seen


@pytest.mark.asyncio
async def test_H08_bias_probe_client_unchanged_without_opt_in(monkeypatch, tmp_path):
    """PIN H08 (not opted in, key set): the AsyncClient is constructed with no kwargs
    at all (no `headers`), and no request carries x-admin-key."""
    _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL)
    built, seen = await _run_bias(monkeypatch, tmp_path)
    assert built == [{}], built
    assert seen and all("x-admin-key" not in h for h in seen), seen


# ===========================================================================
# H09  bundle_d_prod_smoke probe 12 (C7: the bearer is the one non-opt-in change)
# ===========================================================================
def _run_smoke(mp, *, login_ok):
    mod = _load("bundle_d_prod_smoke")
    seen: list = []
    real_client = httpx.Client

    def handler(request):
        seen.append((request.method, request.url.path, _lower(request.headers)))
        if request.url.path == "/api/v1/auth/login":
            if login_ok:
                return httpx.Response(200, json={"success": True,
                                                 "session": {"access_token": SMOKE_JWT}})
            return httpx.Response(401, json={"success": False, "error": "u13 login refused"})
        return httpx.Response(200, json={"success": True})

    def _client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    mp.setattr(mod, "httpx", _HttpxShim(Client=_client))
    mod.run_probes(BASE_URL, auth_token=None, verbose=False)
    return [h for (_m, path, h) in seen if path == "/api/v1/text/compare"]


def test_H09_smoke_compare_probe_carries_the_users_token(monkeypatch):
    """RED H09a: the login probe yields a token -> the /api/v1/text/compare request
    (probe 12) carries Authorization: Bearer <that token>, and no admin header (the
    smoke sends one credential or the other, never both)."""
    _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL)
    compares = _run_smoke(monkeypatch, login_ok=True)
    assert len(compares) == 1, compares
    assert compares[0].get("authorization") == f"Bearer {SMOKE_JWT}", (
        f"probe 12 sent no Authorization bearer; header names {sorted(compares[0])}")
    assert "x-admin-key" not in compares[0], sorted(compares[0])


def test_H09_smoke_compare_probe_falls_back_to_the_admin_key(monkeypatch):
    """RED H09b: login fails and the opt-in is set -> probe 12 carries the admin
    header instead (no Authorization)."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
    compares = _run_smoke(monkeypatch, login_ok=False)
    assert len(compares) == 1, compares
    assert compares[0].get("x-admin-key") == ADMIN_SENTINEL, (
        f"probe 12 sent no X-Admin-Key fallback; header names {sorted(compares[0])}")
    assert "authorization" not in compares[0], sorted(compares[0])


# ===========================================================================
# H10  verify_after_credits.main client (UR7: edited in place)
# ===========================================================================
def _run_verify_after_credits(mp):
    mod = _load("verify_after_credits")
    built: list = []
    seen: list = []
    real_client = httpx.Client

    def handler(request):
        seen.append((request.url.path, _lower(request.headers)))
        if request.url.path.endswith("/stream"):
            return httpx.Response(200, text="event: complete\ndata: {}\n\n",
                                  headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"success": True, "products": [],
                                         "overview": {"winner": {"name": "u13"}}})

    def _client(*args, **kwargs):
        built.append(dict(kwargs))
        kw = dict(kwargs)
        kw["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kw)

    mp.setattr(mod, "httpx", _HttpxShim(Client=_client))
    mp.setattr(sys, "argv", ["verify_after_credits.py", "--base", BASE_URL, "--pairs", "a vs b"])
    mod.main()
    return built, seen


def test_H10_verify_after_credits_client_carries_admin_key_when_opted_in(monkeypatch):
    """RED H10 (opted in): httpx.Client(timeout=150, headers={"X-Admin-Key": key}); every
    compare / stream request carries it."""
    _env(monkeypatch, opt_in="1", key=ADMIN_SENTINEL)
    built, seen = _run_verify_after_credits(monkeypatch)
    assert len(built) == 1, built
    assert built[0].get("headers") == {"X-Admin-Key": ADMIN_SENTINEL}, (
        f"httpx.Client kwargs {sorted(built[0])} carry no X-Admin-Key header")
    compare_paths = [h for (p, h) in seen if p.startswith("/api/v1/text/compare")]
    assert compare_paths and all(h.get("x-admin-key") == ADMIN_SENTINEL for h in compare_paths)


def test_H10_verify_after_credits_client_unchanged_without_opt_in(monkeypatch):
    """PIN H10 (not opted in, key set): httpx.Client(timeout=150) exactly as today -- no
    `headers` kwarg -- and no request carries x-admin-key."""
    _env(monkeypatch, opt_in=None, key=ADMIN_SENTINEL)
    built, seen = _run_verify_after_credits(monkeypatch)
    assert built == [{"timeout": 150}], built
    assert seen and all("x-admin-key" not in h for (_p, h) in seen), seen

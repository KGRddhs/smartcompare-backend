"""S81-07 MEAS-CLAUDE-GATE: the frozen RED file for scripts/meas_claude_gate.py.

Contract: .qa-s80/S81-07_UNIT_SPEC.md + .qa-s80/S81-07_SPEC_AMENDMENTS.md (one
contract), RULINGS_S81_07 (R-S07-13..34), the brief (R-S07-1..12).

R rows fail at base on an AssertionError only (the module and the fixtures are
read through find_spec / Path.exists and asserted). P rows are green at base.
Hermetic: no network (the netguard plugin), no dotenv file, a fake SDK client,
a canary built at run time (never a credential shape). No row sets a real
credential; every environment name a row depends on is set or deleted through
monkeypatch.
"""
import ast
import asyncio
import importlib
import importlib.util
import json
import math
import os
import re
import secrets
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "meas_claude_gate.py"
FIXTURES = REPO / "tests" / "fixtures" / "s81_s07"
MOD_NAME = "scripts.meas_claude_gate"
VAR = "MEAS_ANTHROPIC_TEST_KEY"
CANARY_PREFIX = "S07" + "CANARY"
_HEX_TO_SAFE = str.maketrans("0123456789abcdef", "qxzjkvwyQXZJKVWY")  # GC-3
STAGE_DIRS = ("text", "moderation", "vision", "web_search")
TEXT_SITES = (
    "classify", "parse", "specs", "price", "price_training", "reviews", "verdict",
    "image_tier3", "specs_targeted", "specs_synthesized", "disambiguate", "url_extract",
)
SCORING_FLAGS = (
    "ENABLE_SPEC_FIELD_NORM", "ENABLE_MISSING_DIM_RENORM", "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING",
    "ENABLE_CATEGORY_VALUE_BADGE", "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
)
ARABIC_RE = re.compile("[" + chr(0x0600) + "-" + chr(0x06FF) + "]")


# --------------------------------------------------------------------------
# helpers (no import of the module under test at collection time)
# --------------------------------------------------------------------------
def _mod():
    spec = importlib.util.find_spec(MOD_NAME)
    assert spec is not None, "scripts/meas_claude_gate.py does not exist"
    return importlib.import_module(MOD_NAME)


def _attr(mod, name):
    assert hasattr(mod, name), "missing %s" % name
    return getattr(mod, name)


def _fixture(name):
    path = FIXTURES / name
    assert path.exists(), "missing fixture %s" % name
    return json.loads(path.read_text(encoding="utf-8"))


def _make_canary():
    return CANARY_PREFIX + secrets.token_hex(16).translate(_HEX_TO_SAFE)


def _leaks(canary, blob):
    """True when any 4-character window of the canary's random part (or the
    prefix joined to its first 4 characters) appears in blob (R-S07-18 (a))."""
    body = canary[len(CANARY_PREFIX):]
    if (CANARY_PREFIX + body[:4]) in blob:
        return True
    return any(body[i:i + 4] in blob for i in range(len(body) - 3))


def _out_bytes(out_dir):
    chunks = []
    if out_dir.exists():
        for p in sorted(out_dir.rglob("*")):
            if p.is_file():
                chunks.append(p.read_bytes().decode("utf-8", "replace"))
    return "\n".join(chunks)


def _env_safety():
    import tests._env_safety as es
    return es


def _refused_names_all():
    es = _env_safety()
    return set(es.CREDENTIALS_UNSET) | set(es.CREDENTIAL_PLACEHOLDERS)


def _router():
    from app.services import llm_router
    return llm_router


def _msg(text="{}", stop="end_turn", model="claude-haiku-5-5", inp=100, out=20, cache_read=0, searches=0):
    import anthropic.types as T
    usage = {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": cache_read,
             "cache_creation_input_tokens": 0}
    if searches:
        usage["server_tool_use"] = {"web_search_requests": searches, "web_fetch_requests": 0}  # GC-2
    return T.Message.model_validate({
        "id": "msg_s07", "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": text}], "stop_reason": stop, "stop_sequence": None,
        "usage": usage})


def _status_exc(status, message="synthetic", headers=None, key_header=None):
    import anthropic
    import httpx2
    classes = {400: anthropic.BadRequestError, 401: anthropic.AuthenticationError,
               403: anthropic.PermissionDeniedError, 404: anthropic.NotFoundError,
               413: anthropic.RequestTooLargeError, 422: anthropic.UnprocessableEntityError,
               429: anthropic.RateLimitError, 500: anthropic.InternalServerError,
               503: anthropic.InternalServerError, 529: anthropic.OverloadedError}
    req_headers = {"x-api-key": key_header} if key_header else {}
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages", headers=req_headers)
    body = {"type": "error", "error": {"type": "x", "message": message}}
    resp = httpx2.Response(status, request=req, json=body, headers=headers or {})
    return classes[status](message, response=resp, body=body)


def _conn_exc(timeout=False):
    import anthropic
    import httpx2
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    if timeout:
        return anthropic.APITimeoutError(request=req)
    return anthropic.APIConnectionError(request=req)


class _Messages:
    def __init__(self, owner):
        self._o = owner

    async def create(self, **kw):
        self._o.creates.append(kw)
        self._o.order.append(("create", len(self._o.creates)))
        res = self._o.behaviour(kw, len(self._o.creates))
        if isinstance(res, BaseException):
            raise res
        await asyncio.sleep(0)
        return res

    async def count_tokens(self, **kw):
        self._o.counts.append(kw)

        class _C:
            input_tokens = 123
        return _C()


class _Models:
    def __init__(self, owner):
        self._o = owner

    async def retrieve(self, model_id, **kw):
        self._o.retrieves.append(model_id)

        class _M:
            id = model_id
            max_input_tokens = 200000
            max_tokens = 64000
            capabilities = None
            lifecycle = None
            retires_at = None
            display_name = "synthetic"
            type = "model"

            def model_dump(self):
                return {"id": model_id, "max_input_tokens": 200000, "max_tokens": 64000}
        return _M()


class FakeClient:
    def __init__(self, behaviour=None, **kw):
        self.kwargs = kw
        self.creates = []
        self.counts = []
        self.retrieves = []
        self.order = []
        self.behaviour = behaviour or (lambda kw, n: _msg())
        self.messages = _Messages(self)
        self.models = _Models(self)


class Harness:
    """Patches the module seams and runs main(argv)."""

    def __init__(self, mod, monkeypatch, tmp_path, behaviour=None):
        self.mod = mod
        self.out = tmp_path / "out"
        self.clients = []
        self.sleeps = []
        self.fsyncs = []
        self.key_reads = []
        self.behaviour = behaviour
        self.clock = [1000.0]

        def factory(**kw):
            c = FakeClient(self.behaviour, **kw)
            self.clients.append(c)
            return c

        async def fake_sleep(s):
            self.sleeps.append(s)

        real_read = getattr(mod, "_read_key", None)

        def read_key():
            self.key_reads.append(1)
            return real_read() if real_read else None

        def fsync(fd):
            self.fsyncs.append(fd)
            if self.clients:
                self.clients[-1].order.append(("fsync", len(self.fsyncs)))

        monkeypatch.setattr(mod, "_client_factory", factory)
        monkeypatch.setattr(mod, "_sleep", fake_sleep)
        monkeypatch.setattr(mod, "_fsync", fsync)
        monkeypatch.setattr(mod, "_monotonic", lambda: self.clock[0])
        monkeypatch.setattr(mod, "_read_key", read_key)

    @property
    def creates(self):
        return [kw for c in self.clients for kw in c.creates]

    def run(self, *argv):
        args = list(argv)
        if "--out" not in args:
            args += ["--out", str(self.out)]
        return self.mod.main(args)

    def results(self, stage):
        p = self.out / stage / "results.json"
        assert p.exists(), "missing results.json for %s" % stage
        return json.loads(p.read_text(encoding="utf-8"))

    def ledger(self, stage):
        p = self.out / stage / "spend.jsonl"
        assert p.exists(), "missing ledger for %s" % stage
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


@pytest.fixture
def canary():
    return _make_canary()


@pytest.fixture
def clean_env(monkeypatch, canary):
    """R-S07-16 (a): delete every refused name and every ENABLE_* name, set the
    variable to the canary."""
    for name in list(os.environ):
        if name.startswith(("ANTHROPIC_", "ENABLE_")) or name in _refused_names_all():
            monkeypatch.delenv(name, raising=False)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(VAR, canary)
    return canary


class _LazyHarness:
    """Builds the Harness on first use INSIDE the test body, so a missing module
    is an AssertionError of the call phase, never a fixture (setup) error."""

    def __init__(self, monkeypatch, tmp_path):
        self.__dict__["_args"] = (monkeypatch, tmp_path)
        self.__dict__["_real"] = None

    def _get(self):
        if self.__dict__["_real"] is None:
            monkeypatch, tmp_path = self.__dict__["_args"]
            self.__dict__["_real"] = Harness(_mod(), monkeypatch, tmp_path)
        return self.__dict__["_real"]

    def __getattr__(self, name):
        return getattr(self._get(), name)

    def __setattr__(self, name, value):
        setattr(self._get(), name, value)


@pytest.fixture
def hx(monkeypatch, tmp_path, clean_env):
    return _LazyHarness(monkeypatch, tmp_path)


def _done(lines):
    return [x for x in lines if x.get("state") == "done"]


def _intents(lines):
    return [x for x in lines if x.get("state") == "sent"]


# --------------------------------------------------------------------------
# R rows: the module, the constants, the start sequence
# --------------------------------------------------------------------------
def test_r01_module_and_entry():
    mod = _mod()
    for name in ("main", "ENV_VAR_NAME", "UNIT_CEILING_USD", "STAGE_DEFAULTS", "EXIT_OK", "EXIT_REFUSED",
                 "EXIT_CRASH", "EXIT_UNIT_CEILING", "EXIT_AUTH", "EXIT_STOPPED", "EXIT_INTERRUPTED",
                 "StageStop", "Budget", "Dispatcher", "worst_case_usd", "booked_usd_for_exception",
                 "usd_from_usage", "stream_usage", "percentile", "ceil_half", "timeout_proposal",
                 "host_allowed", "refused_names_present", "call_id_for", "_client_factory", "_read_key",
                 "_sleep", "_monotonic", "_fsync", "_import_app_modules", "_install_dotenv_guard", "REPO_ROOT"):
        _attr(mod, name)
    assert (mod.EXIT_OK, mod.EXIT_REFUSED, mod.EXIT_CRASH, mod.EXIT_UNIT_CEILING, mod.EXIT_AUTH,
            mod.EXIT_STOPPED, mod.EXIT_INTERRUPTED) == (0, 2, 3, 4, 5, 6, 130)
    assert Path(mod.REPO_ROOT).resolve() == REPO


def test_r02_env_var_name_and_ceilings():
    mod = _mod()
    assert mod.ENV_VAR_NAME == VAR
    assert mod.UNIT_CEILING_USD == 15.0
    caps = {k: mod.STAGE_DEFAULTS[k]["max_usd"] for k in STAGE_DIRS}
    assert caps == {"text": 4.0, "moderation": 2.0, "vision": 5.0, "web_search": 3.0}
    assert sum(caps.values()) <= 15.0
    assert mod.STAGE_DEFAULTS["text"]["max_calls"] == 700
    assert (mod.CONSECUTIVE_TRANSIENT_STOP, mod.RATE_LIMIT_RETRIES) == (3, 3)
    assert (mod.RETRY_AFTER_DEFAULT_S, mod.RETRY_AFTER_MAX_S) == (5, 60)
    assert mod.ROUND_SPACING_S == 30.0
    assert mod.CALL_TIMEOUT_S == _router().CALL_DEADLINE_DEFAULT_SECONDS
    assert mod.REPS_MAX == 2 and mod.LOCK_NAME == ".meas_lock"


@pytest.mark.parametrize("suffix", ["API_KEY", "AUTH_TOKEN", "BASE_URL", "CUSTOM_HEADERS", "LOG", "PROFILE",
                                    "MODEL_TEXT", "CONFIG_DIR"])
@pytest.mark.parametrize("value", ["", "x"])
def test_r03_refuses_each_anthropic_name(hx, monkeypatch, capsys, canary, suffix, value):
    name = "ANTHROPIC_" + suffix
    imports = []
    monkeypatch.setattr(hx.mod, "_import_app_modules", lambda *a, **k: imports.append(1))
    monkeypatch.setenv(name, value)
    code = hx.run("text", "--settings", "A1_sites")
    err = capsys.readouterr().err
    assert code == 2
    assert err.strip() == "meas_claude_gate: refused: refused_env names=" + name
    assert not _leaks(canary, err)
    assert hx.clients == [] and imports == []
    assert not hx.out.exists() or not any(hx.out.rglob("*"))


@pytest.mark.parametrize("name", ["UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN", "OPENAI_API_KEY", "SUPABASE_URL",
                                  "SERPER_API_KEY"])
def test_r04_refuses_import_time_and_credential_names(hx, monkeypatch, capsys, canary, name):
    imports = []
    monkeypatch.setattr(hx.mod, "_import_app_modules", lambda *a, **k: imports.append(1))
    monkeypatch.setenv(name, "")
    code = hx.run("text")
    err = capsys.readouterr().err
    assert code == 2
    assert err.strip() == "meas_claude_gate: refused: refused_env names=" + name
    assert not _leaks(canary, err)
    assert hx.clients == [] and imports == []


@pytest.mark.parametrize("value", [None, "", "   "])
def test_r05_key_missing_empty_blank(hx, monkeypatch, capsys, value):
    if value is None:
        monkeypatch.delenv(VAR, raising=False)
    else:
        monkeypatch.setenv(VAR, value)
    code = hx.run("text", "--settings", "A1_sites")
    err = capsys.readouterr().err
    assert code == 2
    assert err.strip() == "meas_claude_gate: refused: credential_missing names=" + VAR
    assert hx.clients == []


def test_r06_out_inside_repo_refused(hx, capsys):
    import shutil
    target = REPO / ("tmp_s07_out_refused_" + secrets.token_hex(4))  # GC-4: unique per run
    try:
        code = hx.mod.main(["text", "--dry-run", "--out", str(target)])
        assert code == 2
        assert not target.exists()
        assert "out_inside_repo" in capsys.readouterr().err
    finally:
        if target.exists():
            shutil.rmtree(str(target), ignore_errors=True)


def test_r07_client_built_explicitly(hx, monkeypatch, canary):
    import httpx2
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:1")
    code = hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert code == 6
    assert len(hx.clients) == 1
    kw = hx.clients[0].kwargs
    assert kw["api_key"] == canary
    assert kw["base_url"] == _router().ANTHROPIC_BASE_URL
    assert kw["max_retries"] == 0
    client = kw["http_client"]
    assert isinstance(client, httpx2.AsyncClient)
    assert client.trust_env is False
    assert client.follow_redirects is False
    assert len(getattr(client, "_mounts", {})) == 0
    assert hx.results("text")["proxy_env_ignored"] == ["HTTPS_PROXY"]


def test_r08_canary_absent_success_path(hx, capsys, canary):
    code = hx.run("text", "--settings", "A1_sites", "--max-calls", "3")
    assert code == 6
    cap = capsys.readouterr()
    blob = cap.out + cap.err + _out_bytes(hx.out)
    assert not _leaks(canary, blob)
    assert hx.results("text")["redactions"] == 0


def test_r09_canary_absent_sdk_error_path(monkeypatch, tmp_path, clean_env, capsys):
    canary = clean_env
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _status_exc(400, message="bad " + canary, key_header=canary))
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    cap = capsys.readouterr()
    assert not _leaks(canary, cap.out + cap.err + _out_bytes(hx.out))
    done = _done(hx.ledger("text"))
    assert done and done[0]["error_class"] == "BadRequestError" and done[0]["status"] == 400
    assert "message" not in done[0]


def test_r10_canary_absent_crash_path(monkeypatch, tmp_path, clean_env, capsys):
    canary = clean_env
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: RuntimeError(canary))
    monkeypatch.setattr(mod, "Dispatcher", _crashing_dispatcher(mod, canary))
    code = hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    cap = capsys.readouterr()
    assert code == 3
    assert cap.err == "meas_claude_gate: crashed class=RuntimeError\n"
    assert not _leaks(canary, cap.out + cap.err + _out_bytes(hx.out))


def _crashing_dispatcher(mod, canary):
    base = mod.Dispatcher

    class Crashing(base):
        async def send(self, *a, **k):
            raise RuntimeError(canary)
    return Crashing


def test_r11_no_read_of_production_key(hx, monkeypatch):
    _mod()
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"ANTHROPIC_API_KEY"' not in text and "'ANTHROPIC_API_KEY'" not in text
    assert "_anthropic_api_key" not in text and "_client_for" not in text
    stores = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and _is_os_environ(node.value):
            sl = node.slice
            if isinstance(node.ctx, ast.Store):
                assert isinstance(sl, ast.Constant) and sl.value == "OPENAI_API_KEY"
                stores += 1
            elif isinstance(node.ctx, ast.Load):
                assert isinstance(sl, ast.Name)
        if isinstance(node, ast.Call):
            f = node.func
            is_get = isinstance(f, ast.Attribute) and (
                (f.attr == "getenv" and isinstance(f.value, ast.Name) and f.value.id == "os")
                or (f.attr == "get" and _is_os_environ(f.value)))
            if is_get and node.args:
                assert isinstance(node.args[0], ast.Name), "environment read by a literal"
        if isinstance(node, ast.Name) and node.id in ("guarded_anthropic_create", "consume_escalation"):
            raise AssertionError("bare reference to %s" % node.id)
    assert stores == 1

    class Rec(dict):
        reads = []

        def get(self, k, d=None):
            Rec.reads.append(k)
            return dict.get(self, k, d)

        def __getitem__(self, k):
            Rec.reads.append(k)
            return dict.__getitem__(self, k)

    rec = Rec(os.environ)
    monkeypatch.setattr(os, "environ", rec)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert "ANTHROPIC_API_KEY" not in Rec.reads


def _is_os_environ(node):
    return isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name) \
        and node.value.id == "os"


def test_r12_sdk_loggers_pinned(hx, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    for name in ("anthropic", "httpx2", "httpx", "httpcore"):
        assert logging.getLogger(name).level >= logging.WARNING
        assert not [r for r in caplog.records if r.name.split(".")[0] == name]


def _png_set(dirpath, n):
    import struct
    import zlib
    dirpath.mkdir(parents=True, exist_ok=True)
    raw = b"\x00\xff\xff\xff"
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b""))
    manifest = []
    for i in range(n):
        name = "p%03d.png" % i
        (dirpath / name).write_bytes(png)
        manifest.append({"file": name, "label_lang": "ar" if i % 3 == 0 else "en",
                         "expected_brand": "Dior", "expected_name": "Sauvage"})
    (dirpath / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    return dirpath


def _chunk(kind, data):
    import struct
    import zlib
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _plan(hx, stage):
    p = hx.out / stage / "plan.json"
    assert p.exists(), "missing plan.json for %s" % stage
    return json.loads(p.read_text(encoding="utf-8"))


def test_r13_dry_run_no_socket_no_key(hx, tmp_path, capsys, canary):
    assert hx.run("text", "--dry-run") == 0
    plan = _plan(hx, "text")
    calls = {k: v["calls"] for k, v in plan["settings"].items()}
    assert calls == {"A0_capabilities": 2, "A1_sites": 320, "A2_ttft": 40, "A3_sonnet_between_tools": 20,
                     "A4_refusal_names": 100, "A5_count_tokens": 20, "A6_verdict_eval": 120}
    assert plan["total_calls"] == 622
    assert plan["total_worst_usd"] <= 4.0
    assert hx.run("moderation", "--dry-run") == 0
    assert _plan(hx, "moderation")["total_worst_usd"] <= 2.0
    photos = _png_set(tmp_path / "photos", 1)
    assert hx.run("vision", "--dry-run", "--set", str(photos)) == 0
    assert hx.run("web_search", "--dry-run", "--owner-line", "2026-11-12 10:00") == 0
    assert _plan(hx, "web_search")["total_worst_usd"] <= 3.0
    assert hx.clients == [] and hx.key_reads == []
    cap = capsys.readouterr()
    assert not _leaks(canary, cap.out + cap.err + _out_bytes(hx.out))


def test_r14_request_equals_router(hx, monkeypatch):
    router = _router()
    seen = []
    real = router.to_claude_request

    def spy(site, kwargs):
        req = real(site, kwargs)
        seen.append((site, req))
        return req

    monkeypatch.setattr(router, "to_claude_request", spy)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    sent = [{k: v for k, v in kw.items() if k not in ("timeout", "stream")} for kw in hx.creates]
    assert len(sent) == 16
    sites_seen = {s for s, _ in seen}
    assert sites_seen == set(TEXT_SITES)
    converted = [r for _, r in seen]
    for req in sent:
        assert req in converted
    for site, req in seen:
        spec = router.SITES[site]
        assert req["model"] == importlib.import_module("app.services.model_config").anthropic_model(spec.role)
        assert req["max_tokens"] == spec.claude_max_tokens


def test_r15_sonnet_request(hx, monkeypatch):
    router = _router()
    mc = importlib.import_module("app.services.model_config")
    hx.run("text", "--settings", "A3_sonnet_between_tools", "--max-calls", "1")
    assert len(hx.creates) == 1
    req = {k: v for k, v in hx.creates[0].items() if k != "timeout"}
    assert req["thinking"] == {"type": "between_tools"}
    assert req["model"] == mc.anthropic_escalation_model()
    assert req == router._escalation_request(dict(req, model=mc.anthropic_model("verdict"),
                                                  thinking={"type": "disabled"}))


def test_r16_pricing_from_usage():
    mod = _mod()
    import anthropic.types as T
    from app.services import llm_pricing
    u = T.Usage.model_validate({"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 300,
                                "cache_creation_input_tokens": 0})
    want = llm_pricing.price_call("anthropic", "claude-haiku-5-5", input_tokens=1000, output_tokens=200,
                                  cache_read_tokens=300)
    assert mod.usd_from_usage("claude-haiku-5-5", u, 9.0) == pytest.approx(want)
    big = T.Usage.model_validate({"input_tokens": 120000, "output_tokens": 10})
    flat = 120000 * 0.10 / 1e6 + 10 * 0.50 / 1e6
    assert mod.usd_from_usage("claude-haiku-5-5", big, 9.0) > flat * 4
    ws = T.Usage.model_validate({"input_tokens": 10, "output_tokens": 10,
                                 "server_tool_use": {"web_search_requests": 2, "web_fetch_requests": 0}})
    no_ws = T.Usage.model_validate({"input_tokens": 10, "output_tokens": 10})
    assert mod.usd_from_usage("claude-haiku-5-5", ws, 9.0) - mod.usd_from_usage(
        "claude-haiku-5-5", no_ws, 9.0) == pytest.approx(0.02)
    assert mod.usd_from_usage("claude-unpriced-model", no_ws, 0.75) == 0.75


def test_r17_worst_case_stop(hx, monkeypatch, canary):
    assert hx.run("text", "--settings", "A1_sites", "--dry-run") == 0
    first = _plan(hx, "text")["settings"]["A1_sites"]
    assert first["worst_usd"] > 0
    mod = hx.mod
    b = mod.Budget(0.001, 0.0, 0.0)
    req = {"model": "claude-haiku-5-5", "messages": [{"role": "user", "content": "x"}], "max_tokens": 4000,
           "thinking": {"type": "disabled"}, "output_config": {"effort": "low"}}
    w = mod.worst_case_usd(req)
    assert w >= 4000 * 0.50 / 1e6
    assert b.reserve(w) is False
    out2 = hx.out.parent / "out2"
    monkeypatch.setenv(VAR, canary)  # F-7 (a): the dry run above removed the variable; a live run sets it again
    code = hx.mod.main(["text", "--settings", "A1_sites", "--max-usd", "0.00001", "--out", str(out2)])
    assert code == 6
    assert hx.creates == []
    assert json.loads((out2 / "text" / "results.json").read_text(encoding="utf-8"))["stop_reason"] == "budget"


def _write_ledger(path, usd):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {"call_id": "0" * 16, "attempt": 1, "state": "done", "stage": "moderation", "setting": "M1_parity",
            "site": "moderation", "case_id": "m001", "rep": 0, "model": "claude-haiku-5-5", "kind": "create",
            "ok": True, "usd": usd, "worst_usd": usd, "input_tokens": 1, "output_tokens": 1,
            "cache_read_tokens": 0, "cache_write_tokens": 0, "web_search_requests": 0, "stop_reason": "end_turn",
            "error_class": None, "status": None, "latency_ms": 1, "ttft_ms": None, "ts": "2026-11-12T00:00:00Z"}
    path.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def test_r18_unit_ceiling(hx, capsys, monkeypatch, canary):
    _write_ledger(hx.out / "moderation" / "spend.jsonl", 11.50)
    assert hx.run("text", "--settings", "A1_sites", "--max-calls", "1") == 4
    assert hx.clients == []
    assert "unit_ceiling" in capsys.readouterr().err
    _write_ledger(hx.out / "moderation" / "spend.jsonl", 10.99)
    monkeypatch.setenv(VAR, canary)  # GC-10: a live start removes the variable; a second run sets it again
    assert hx.run("text", "--settings", "A1_sites", "--max-calls", "1") == 6
    assert len(hx.creates) == 1


@pytest.mark.parametrize("value,code", [("4.01", 2), ("nan", 2), ("inf", 2), ("-1", 2), ("x", 2), ("0", 2)])
def test_r19_max_usd_lower_only(hx, value, code):
    assert hx.run("text", "--dry-run", "--max-usd", value) == code
    assert hx.run("text", "--dry-run", "--max-usd", "0.5", "--settings", "A0_capabilities") == 0


def test_r20_ledger_per_call(hx):
    mod = hx.mod
    hx.run("text", "--settings", "A1_sites", "--max-calls", "5")
    lines = hx.ledger("text")
    done, sent = _done(lines), _intents(lines)
    assert len(done) == 5 and len(sent) == 5
    for x in done:
        assert set(x) == set(mod.LEDGER_DONE_KEYS)
    for x in sent:
        assert set(x) == set(mod.LEDGER_INTENT_KEYS)
    assert len(hx.fsyncs) == 10
    order = hx.clients[0].order
    for i, ev in enumerate(order):
        if ev[0] == "create":
            assert i > 0 and order[i - 1][0] == "fsync"


def test_r21_resume(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _status_exc(500) if n == 5 else _msg())
    hx.run("text", "--settings", "A1_sites", "--max-calls", "5")
    first = [x["call_id"] for x in _done(hx.ledger("text"))]
    ok_ids = [x["call_id"] for x in _done(hx.ledger("text")) if x["ok"]]
    transient = [x["call_id"] for x in _done(hx.ledger("text")) if not x["ok"]]
    assert len(first) == 5 and len(transient) == 1
    hx.behaviour = lambda kw, n: _msg()
    monkeypatch.setenv(VAR, clean_env)  # GC-10
    hx.run("text", "--settings", "A1_sites", "--max-calls", "5")
    second = _done(hx.ledger("text"))[5:]
    second_ids = [x["call_id"] for x in second]
    assert not set(ok_ids) & set(second_ids)
    assert transient[0] in second_ids
    resent = [x for x in second if x["call_id"] == transient[0]][0]
    assert resent["attempt"] == 2


def test_r22_max_calls(hx):
    assert hx.run("text", "--settings", "A1_sites", "--max-calls", "7") == 6
    assert len(hx.creates) == 7
    assert hx.results("text")["stop_reason"] == "max_calls"


@pytest.mark.parametrize("status", [401, 403])
def test_r23_auth_stops_at_once(monkeypatch, tmp_path, clean_env, status):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _status_exc(status))
    assert hx.run("text", "--settings", "A1_sites") == 5
    assert len(hx.creates) == 1
    assert (hx.out / "text" / "REPORT.md").exists()
    assert hx.results("text")["stop_reason"] == "auth"


@pytest.mark.parametrize("seq,stops,n_creates", [
    (("500", "529", "conn"), True, 3),
    (("500", "500", "ok", "500", "500", "ok"), False, 6),
])
def test_r24_three_consecutive_transient(monkeypatch, tmp_path, clean_env, seq, stops, n_creates):
    mod = _mod()

    def beh(kw, n):
        s = seq[n - 1] if n <= len(seq) else "ok"
        if s == "conn":
            return _conn_exc()
        if s == "ok":
            return _msg()
        return _status_exc(int(s))

    hx = Harness(mod, monkeypatch, tmp_path, behaviour=beh)
    code = hx.run("text", "--settings", "A1_sites", "--max-calls", str(len(seq)))
    assert len(hx.creates) == n_creates
    if stops:
        assert code == 6 and hx.results("text")["stop_reason"] == "transient"
    else:
        assert hx.results("text")["stop_reason"] == "max_calls"


@pytest.mark.parametrize("header,expect", [({"retry-after": "2"}, 2), ({}, 5), ({"retry-after": "999"}, 60)])
def test_r25_rate_limit_retry_after(monkeypatch, tmp_path, clean_env, header, expect):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _status_exc(429, headers=header) if n <= 4 else _msg())
    hx.run("text", "--settings", "A1_sites,A2_ttft", "--max-calls", "6")
    rate_sleeps = [s for s in hx.sleeps if s != mod.ROUND_SPACING_S]
    assert rate_sleeps[:3] == [expect, expect, expect]
    assert len([x for x in _done(hx.ledger("text")) if x["error_class"] == "RateLimitError"]) == 4
    res = hx.results("text")["settings"]
    assert res["A1_sites"]["stop_reason"] == "rate_limit"
    assert res["A2_ttft"]["calls"] >= 1


def test_r26_wall_clock(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path)

    def beh(kw, n):
        if n == 2:
            hx.clock[0] += 61.0
        return _msg()

    hx.behaviour = beh
    assert hx.run("text", "--settings", "A1_sites", "--max-minutes", "1") == 6
    assert len(hx.creates) == 2
    assert "PARTIAL" in (hx.out / "text" / "REPORT.md").read_text(encoding="utf-8")


def test_r27_interrupt(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: KeyboardInterrupt() if n == 3 else _msg())
    assert hx.run("text", "--settings", "A1_sites") == 130
    assert len([x for x in _done(hx.ledger("text")) if x["ok"]]) == 2
    assert "PARTIAL" in (hx.out / "text" / "REPORT.md").read_text(encoding="utf-8")


def test_r28_not_runnable_stages(hx):
    assert hx.run("vision") == 0
    assert hx.run("web_search") == 0
    assert hx.clients == []
    v = hx.results("vision")
    w = hx.results("web_search")
    assert v["not_runnable"] and w["not_runnable"]
    rep = (hx.out / "vision" / "REPORT.md").read_text(encoding="utf-8")
    for needle in ("100", "manifest.json", "label_lang", "expected_brand", "expected_name"):
        assert needle in rep


def test_r29_report_table(hx):
    mod = hx.mod
    g = mod.GO_THRESHOLDS
    assert set(g) == {"TEXT", "VERDICT", "SONNET_ESCALATION", "CRITIC", "MODERATION", "VISION", "WEB_SEARCH"}
    assert g["TEXT"]["json_valid_pooled_min"] == 0.98 and g["TEXT"]["json_valid_site_min"] == 0.90
    assert g["TEXT"]["p95_s"] == {"classify": 4.0, "specs": 4.0, "reviews": 5.0, "price": 7.5, "image_tier3": 2.5}
    assert g["TEXT"]["refusals_a4_max"] == 1 and g["TEXT"]["refusals_a4_arabic_max"] == 0
    assert g["VERDICT"]["a6_mismatch_max"] == 0.10 and g["VERDICT"]["a6_agreement_min"] == 0.90
    assert g["SONNET_ESCALATION"]["accepted_min"] == 20
    assert g["MODERATION"]["false_positives_max"] == 0 and g["MODERATION"]["recall_min"] == 0.90
    assert g["VISION"]["p99_s"] == 20.0 and g["CRITIC"] is None and g["WEB_SEARCH"] is None
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    for role in g:
        assert re.search(r"^\|\s*%s\s*\|" % role, rep, re.M), role
    for knob in ("ANTHROPIC_CLASSIFY_LLM_TIMEOUT", "ANTHROPIC_VISION_TIMEOUT_SECONDS",
                 "ANTHROPIC_TAIL_RESERVE_SECONDS"):
        assert knob in rep
    assert "LLM legs only: no search, no scoring" in rep
    assert VAR in rep


def test_r30_raw_without_headers(hx):
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    raws = sorted((hx.out / "text" / "raw").glob("*.json"))
    assert raws
    for p in raws:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert set(data) == {"content", "stop_reason", "usage", "model"}
        low = p.read_text(encoding="utf-8").lower()
        for needle in ("x-api-key", "authorization", "anthropic-version"):
            assert needle not in low


def test_r31_no_model_literal():
    _mod()
    pattern = re.compile(r'["\'](gpt-[0-9a-zA-Z.\-]+|omni-moderation-[a-z]+|claude-[0-9a-zA-Z.\-]+)["\']')
    assert not pattern.findall(SCRIPT.read_text(encoding="utf-8"))


def _mod_set(tmp_path, n):
    cases = [{"id": "m%03d" % (i + 1), "text": "Synthetic review of a fresh citrus fragrance %d." % i,
              "lang": "en", "expected_flagged": False, "category": "none", "shape": "l3"} for i in range(n)]
    p = tmp_path / "modset.json"
    p.write_text(json.dumps(cases), encoding="utf-8", newline="\n")
    return p


def _cases(hx):
    return hx.results("moderation")["settings"]["M1_parity"]["cases"]


def test_r32_moderation_production_path(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    router = _router()
    before = (router.guarded_anthropic_create, router.consume_escalation)
    answers = {1: _msg(json.dumps({"flagged": True, "category": "harassment", "uncertain": False})),
               2: _msg("not json"), 3: _msg("", stop="refusal")}
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: answers.get(n, _msg(
        json.dumps({"flagged": False, "category": "none", "uncertain": False}))))
    hx.run("moderation", "--set", str(_mod_set(tmp_path, 3)))
    cases = _cases(hx)
    assert [c["outcome"] for c in cases] == ["flagged", "malformed", "refusal"]
    assert cases[0]["reason"] == "harassment"
    for kw in hx.creates:
        assert kw["system"] == router.MODERATION_SYSTEM_PROMPT
        assert kw["max_tokens"] == router.MODERATION_MAX_TOKENS
        assert kw["output_config"]["format"]["schema"] == router.MODERATION_SCHEMA
    assert (router.guarded_anthropic_create, router.consume_escalation) == before


def test_r33_verdict_eval_plan(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    gold = _fixture("verdict_gold.json")
    first = gold[0]
    wrong = 1 - int(first["gold_winner_index"])
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _msg(json.dumps({"winner_index": wrong})))
    assert hx.run("text", "--dry-run", "--settings", "A6_verdict_eval") == 0
    assert _plan(hx, "text")["settings"]["A6_verdict_eval"]["calls"] == 120
    monkeypatch.setenv(VAR, clean_env)  # F-7 (a): the dry run above removed the variable
    hx.run("text", "--settings", "A6_verdict_eval", "--max-calls", "1")
    assert hx.results("text")["settings"]["A6_verdict_eval"]["mismatches"] == 1


def test_r34_count_tokens_and_capabilities(hx):
    mc = importlib.import_module("app.services.model_config")
    hx.run("text", "--settings", "A5_count_tokens,A0_capabilities")
    counts = [kw for c in hx.clients for kw in c.counts]
    assert len(counts) == 20
    assert all("max_tokens" not in kw for kw in counts)
    retrieves = [m for c in hx.clients for m in c.retrieves]
    assert set(retrieves) == {mc.anthropic_model("text"), mc.anthropic_escalation_model()}
    usd = [x["usd"] for x in _done(hx.ledger("text")) if x["kind"] in ("count_tokens", "models_retrieve")]
    assert usd and all(u == 0.0 for u in usd)


def test_r35_fixtures():
    names = _fixture("fragrance_names.json")
    pairs = _fixture("compare_pairs.json")
    gold = _fixture("verdict_gold.json")
    modset = _fixture("moderation_parity.json")
    domains = _fixture("web_search_domains.json")
    assert (len(names), len(pairs), len(gold), len(modset), len(domains)) == (100, 20, 60, 100, 3)
    assert len([n for n in names if ARABIC_RE.search(json.dumps(n, ensure_ascii=False))]) >= 30
    banned = re.compile(r'"(email|phone|user|user_id|device|device_id|cohort|profile)"')
    for name in ("fragrance_names.json", "compare_pairs.json", "verdict_gold.json", "moderation_parity.json",
                 "web_search_domains.json"):
        raw = (FIXTURES / name).read_bytes()
        assert b"\r" not in raw
        assert not banned.search(raw.decode("utf-8"))
    for case in gold:
        assert {"case_id", "product_a", "product_b", "scores_summary", "gold_winner_index"} <= set(case)
    for case in modset:
        assert case.get("category") not in ("sexual", "sexual/minors", "minors", "self-harm")


def test_r36_dotenv_guard_and_recheck(hx, monkeypatch, capsys):
    import dotenv
    during = []

    def imp(*a, **k):
        during.append(dotenv.load_dotenv)
        os.environ["ANTHROPIC_DECOY"] = "1"

    monkeypatch.setattr(hx.mod, "_import_app_modules", imp)
    before = dotenv.load_dotenv
    try:
        code = hx.run("text", "--dry-run")
    finally:
        os.environ.pop("ANTHROPIC_DECOY", None)
    assert code == 2
    assert "ANTHROPIC_DECOY" in capsys.readouterr().err
    assert during and during[0] is not before


def test_r37_env_safety_lists_the_name():
    assert VAR in _env_safety().CREDENTIALS_UNSET


def _stream_events(text="{}", stop=True, inp=50, out=7):
    import anthropic.types as T
    evs = [
        T.RawMessageStartEvent.model_validate({"type": "message_start", "message": {
            "id": "m", "type": "message", "role": "assistant", "model": "claude-haiku-5-5", "content": [],
            "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": inp, "output_tokens": 1, "cache_read_input_tokens": 0}}}),
        T.RawContentBlockStartEvent.model_validate({"type": "content_block_start", "index": 0,
                                                    "content_block": {"type": "text", "text": ""}}),
        T.RawContentBlockDeltaEvent.model_validate({"type": "content_block_delta", "index": 0,
                                                    "delta": {"type": "text_delta", "text": text}}),
    ]
    if stop:
        evs += [
            T.RawContentBlockStopEvent.model_validate({"type": "content_block_stop", "index": 0}),
            T.RawMessageDeltaEvent.model_validate({"type": "message_delta",
                                                   "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                                   "usage": {"output_tokens": out}}),
            T.RawMessageStopEvent.model_validate({"type": "message_stop"}),
        ]
    return evs


class _AStream:
    def __init__(self, events):
        self._e = list(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._e:
            raise StopAsyncIteration
        await asyncio.sleep(0)
        return self._e.pop(0)


def test_r38_stream_ttft(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _AStream(_stream_events()) if kw.get("stream") else _msg())
    hx.run("text", "--settings", "A2_ttft", "--max-calls", "2")
    assert hx.creates and all(kw.get("stream") is True for kw in hx.creates)
    done = _done(hx.ledger("text"))
    assert done[0]["kind"] == "stream" and done[0]["ttft_ms"] is not None
    import anthropic.types as T
    want = mod.usd_from_usage("claude-haiku-5-5", T.Usage.model_validate(
        {"input_tokens": 50, "output_tokens": 7, "cache_read_input_tokens": 0}), 9.0)
    assert done[0]["usd"] == pytest.approx(want)


# --------------------------------------------------------------------------
# R rows added by the rulings
# --------------------------------------------------------------------------
def test_r39_stage_m_auth_stop(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    ok = json.dumps({"flagged": False, "category": "none", "uncertain": False})
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _status_exc(401) if n == 3 else _msg(ok))
    assert hx.run("moderation", "--set", str(_mod_set(tmp_path, 5))) == 5
    assert len(hx.creates) == 3
    assert [c["outcome"] for c in _cases(hx)] == ["allowed", "allowed", "not_run", "not_run", "not_run"]
    res = hx.results("moderation")
    assert (res["n_run"], res["n_total"]) == (2, 5)


def test_r40_stage_m_budget_stop(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    ok = json.dumps({"flagged": False, "category": "none", "uncertain": False})
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _msg(ok))
    assert hx.run("moderation", "--set", str(_mod_set(tmp_path, 5)), "--max-usd", "0.00001") == 6
    outcomes = [c["outcome"] for c in _cases(hx)]
    assert "unavailable" not in outcomes and set(outcomes) == {"not_run"}
    assert hx.results("moderation")["stop_reason"] == "budget"


def test_r41_stage_stop_class():
    mod = _mod()
    assert issubclass(mod.StageStop, BaseException) and not issubclass(mod.StageStop, Exception)
    assert tuple(mod.STOP_REASONS) == ("budget", "unit_ceiling", "max_calls", "max_minutes", "transient",
                                      "rate_limit", "auth", "host_refused")
    s = mod.StageStop("auth", 5)
    assert (s.reason, s.exit_code, str(s)) == ("auth", 5, "auth")


def test_r42_last_resort_base_exception(monkeypatch, tmp_path, clean_env, capsys):
    mod = _mod()

    class Odd(BaseException):
        pass

    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: Odd(clean_env))
    assert hx.run("text", "--settings", "A1_sites", "--max-calls", "2") == 3
    assert capsys.readouterr().err == "meas_claude_gate: crashed class=Odd\n"


def test_r43_concurrent_reservation(tmp_path):
    mod = _mod()
    req = {"model": "claude-haiku-5-5", "messages": [{"role": "user", "content": "x" * 400}], "max_tokens": 512,
           "thinking": {"type": "disabled"}, "output_config": {"effort": "low"}}
    w = mod.worst_case_usd(req)
    client = FakeClient()
    budget = mod.Budget(3 * w + w / 10.0, 0.0, 0.0)
    ledger = tmp_path / "text" / "spend.jsonl"
    ledger.parent.mkdir(parents=True)
    d = mod.Dispatcher(client, budget, ledger, stage="text", max_calls=100, deadline_monotonic=float("inf"))

    async def go():
        return await asyncio.gather(*[d.send(req, setting="A1_sites", site="specs", case_id="c%d" % i, rep=0)
                                      for i in range(4)], return_exceptions=True)

    out = asyncio.run(go())
    assert len(client.creates) == 3
    stops = [x for x in out if isinstance(x, mod.StageStop)]
    assert len(stops) == 1 and stops[0].reason == "budget"
    assert budget.reserved == pytest.approx(0.0)


def test_r44_booking_table():
    mod = _mod()
    f = mod.booked_usd_for_exception
    assert tuple(mod.UNBILLED_STATUSES) == (400, 401, 403, 404, 413, 422, 429)
    for st in (400, 401, 403, 404, 413, 422, 429):
        assert f(_status_exc(st), 0.5, True) == 0.0
    for st in (500, 503, 529):
        assert f(_status_exc(st), 0.5, True) == 0.5
    assert f(_conn_exc(timeout=True), 0.5, True) == 0.5
    assert f(_conn_exc(), 0.5, True) == 0.5
    assert f(RuntimeError("x"), 0.5, True) == 0.5
    assert f(RuntimeError("x"), 0.5, False) == 0.0


def test_r45_intent_before_send(hx):
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    lines = hx.ledger("text")
    assert [x["state"] for x in lines] == ["sent", "done", "sent", "done"]
    assert lines[0]["call_id"] == lines[1]["call_id"] and lines[0]["attempt"] == lines[1]["attempt"] == 1


def test_r46_unmatched_intent_booked_and_resent(hx, monkeypatch, canary):
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    lines = hx.ledger("text")
    intent = _intents(lines)[0]
    p = hx.out / "text" / "spend.jsonl"
    p.write_text(json.dumps(intent, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    monkeypatch.setenv(VAR, canary)  # GC-10
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    res = hx.results("text")
    again = [x for x in _done(hx.ledger("text")) if x["call_id"] == intent["call_id"]]
    assert again and again[0]["attempt"] == 2
    assert res["spent_usd"] >= intent["worst_usd"]


@pytest.mark.parametrize("bad", ["not json", json.dumps({"state": "done"}),
                                 json.dumps({"call_id": "a" * 16, "attempt": 1, "state": "sent", "worst_usd": -1.0,
                                             "kind": "create", "stage": "text", "setting": "A1_sites",
                                             "site": "specs", "ts": "t"})])
def test_r47_corrupt_ledger_refuses(hx, capsys, bad):
    p = hx.out / "text" / "spend.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text(bad + "\n", encoding="utf-8", newline="\n")
    assert hx.run("text", "--dry-run") == 2
    err = capsys.readouterr().err
    assert "ledger_corrupt" in err and "line=1" in err
    assert bad not in err


def test_r48_stream_usage_merge():
    mod = _mod()
    usage, complete = mod.stream_usage(_stream_events(inp=50, out=7))
    assert complete is True
    assert usage["input_tokens"] == 50 and usage["output_tokens"] == 7
    usage2, complete2 = mod.stream_usage(_stream_events(stop=False))
    assert complete2 is False


def test_r48b_truncated_stream_books_worst(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _AStream(_stream_events(stop=False)))
    hx.run("text", "--settings", "A2_ttft", "--max-calls", "1")
    done = _done(hx.ledger("text"))[0]
    assert done["ok"] is False and done["usd"] == done["worst_usd"] > 0


def test_r49_lock(hx, capsys):
    hx.out.mkdir(parents=True)
    (hx.out / ".meas_lock").write_text("x", encoding="utf-8")
    assert hx.run("text", "--dry-run") == 2
    err = capsys.readouterr().err
    assert "lock_present" in err and str((hx.out / ".meas_lock").resolve()) in err
    assert (hx.out / ".meas_lock").exists()
    (hx.out / ".meas_lock").unlink()
    assert hx.run("text", "--dry-run", "--settings", "A0_capabilities") == 0
    assert not (hx.out / ".meas_lock").exists()


def test_r50_long_context_in_bound():
    mod = _mod()
    big = {"model": "claude-haiku-5-5", "messages": [{"role": "user", "content": "y" * 120000}], "max_tokens": 100,
           "thinking": {"type": "disabled"}, "output_config": {"effort": "low"}}
    flat = 120000 * 0.10 / 1e6 + 100 * 0.50 / 1e6
    assert mod.worst_case_usd(big) >= 120000 * 0.50 / 1e6
    assert mod.worst_case_usd(big) > flat


def test_r51_process_state_restored(hx):
    import dotenv
    import dotenv.main
    a, b = dotenv.load_dotenv, dotenv.main.load_dotenv
    assert "OPENAI_API_KEY" not in os.environ
    os.environ["ENABLE_S07_PROBE_FLAG"] = "true"
    try:
        hx.run("text", "--dry-run", "--settings", "A0_capabilities")
        assert dotenv.load_dotenv is a and dotenv.main.load_dotenv is b
        assert "OPENAI_API_KEY" not in os.environ
        assert os.environ.get("ENABLE_S07_PROBE_FLAG") == "true"
    finally:
        os.environ.pop("ENABLE_S07_PROBE_FLAG", None)


def test_r52_scrub_fires_on_canary_in_text(monkeypatch, tmp_path, clean_env, capsys):
    canary = clean_env
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _msg("echo " + canary))
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    raw = list((hx.out / "text" / "raw").glob("*.json"))
    assert len(raw) == 1 and "[redacted]" in raw[0].read_text(encoding="utf-8")
    assert hx.results("text")["redactions"] == 1
    cap = capsys.readouterr()
    assert not _leaks(canary, cap.out + cap.err + _out_bytes(hx.out))


def test_r53_results_closed_and_report_name_line(hx):
    mod = hx.mod
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    res = hx.results("text")
    assert set(res) == set(mod.RESULTS_KEYS)
    assert res["env_var_name"] == VAR
    rep = (hx.out / "text" / "REPORT.md").read_text(encoding="utf-8").splitlines()
    named = [ln for ln in rep if VAR in ln]
    assert named == [mod.REPORT_NAME_LINE] == ["Credential variable (name only): " + VAR]


@pytest.mark.parametrize("suffix,ok", [("\r\n", True), (" ", True), ("\t", True)])
def test_r54_key_stripped(hx, monkeypatch, canary, suffix, ok):
    monkeypatch.setenv(VAR, canary + suffix)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert hx.clients and hx.clients[0].kwargs["api_key"] == canary


@pytest.mark.parametrize("bad", ["a b", "a\x01b", "a" + chr(0xE9) + "b"])
def test_r54b_key_malformed_refused(hx, monkeypatch, capsys, bad):
    monkeypatch.setenv(VAR, bad)
    assert hx.run("text", "--settings", "A1_sites") == 2
    assert capsys.readouterr().err.strip() == "meas_claude_gate: refused: credential_malformed names=" + VAR
    assert hx.clients == []


def test_r55_percentiles_and_proposals():
    mod = _mod()
    samples = [float(i) for i in range(1, 21)]
    assert mod.percentile(samples, 95) == 19.0
    assert mod.percentile(samples, 99) == 20.0
    assert mod.percentile([], 95) is None
    with_timeout = samples[:-1] + [math.inf]
    assert mod.percentile(with_timeout, 99) == math.inf
    assert mod.ceil_half(4.01) == 4.5 and mod.ceil_half(4.5) == 4.5 and mod.ceil_half(4.0) == 4.0
    assert mod.timeout_proposal([3.2] * 20) == 4.0
    assert mod.timeout_proposal(with_timeout) == math.inf


def test_r56_a1_round_shape():
    mod = _mod()
    order = mod.A1_ROUND_ORDER
    assert order == ("classify", "parse", ("specs", "specs", "price", "price", "image_tier3", "image_tier3"),
                     ("reviews", "reviews"), "verdict", "price_training", "specs_targeted", "specs_synthesized",
                     "disambiguate", "url_extract")
    flat = [x for item in order for x in (item if isinstance(item, tuple) else (item,))]
    assert len(flat) == 16 and set(flat) == set(TEXT_SITES)
    assert "verdict_fallback" not in flat


def test_r56b_tail_span_recorded(hx):
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    spans = hx.results("text")["settings"]["A1_sites"]["tail_span_ms"]
    assert isinstance(spans, list) and len(spans) == 1


def test_r57_moderation_set_shape():
    cases = _fixture("moderation_parity.json")
    benign = [c for c in cases if c["expected_flagged"] is False]
    flagged = [c for c in cases if c["expected_flagged"] is True]
    assert (len(benign), len(flagged)) == (80, 20)
    assert len([c for c in benign if c["lang"] == "ar"]) >= 25
    assert len([c for c in benign if c["shape"] == "l4"]) >= 10
    assert {c["category"] for c in flagged} <= {"harassment", "violence", "illicit"}
    assert [c["id"] for c in cases] == ["m%03d" % i for i in range(1, 101)]


def test_r58_vision_plan_100_photos(hx, tmp_path):
    photos = _png_set(tmp_path / "photos100", 100)
    assert hx.run("vision", "--dry-run", "--set", str(photos)) == 0
    plan = _plan(hx, "vision")
    assert set(plan["settings"]) == {"V1_haiku_vision_v1", "V2_haiku_vision_v2", "V3_sonnet_vision_v2"}
    assert all(v["calls"] == 100 for v in plan["settings"].values())
    assert plan["total_worst_usd"] <= 5.0


@pytest.mark.parametrize("flag,value", [("--max-calls", "701"), ("--max-minutes", "91"), ("--reps", "3"),
                                        ("--max-calls", "0"), ("--reps", "x")])
def test_r59_lower_only_other_knobs(hx, flag, value):
    assert hx.run("text", "--dry-run", flag, value) == 2


def test_r60_host_guard(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    ha = mod.host_allowed
    assert mod.ALLOWED_HOST == "api.anthropic.com"
    assert ha("api.anthropic.com", 443) is True
    assert ha("api.anthropic.com", 80) is False
    assert ha("example.invalid", 443) is False
    assert ha("127.0.0.1", 50000) is True and ha("localhost", 1) is True
    import socket

    def beh(kw, n):
        try:
            socket.getaddrinfo("example.invalid", 443)
        except mod.StageStop:
            raise
        except OSError:
            return AssertionError("the harness guard did not intercept")
        return _msg()

    hx = Harness(mod, monkeypatch, tmp_path, behaviour=beh)
    real = socket.getaddrinfo
    assert hx.run("text", "--settings", "A1_sites", "--max-calls", "1") == 6
    assert hx.results("text")["stop_reason"] == "host_refused"
    assert socket.getaddrinfo is real


def test_r61_refused_names_cover_the_suite_lists():
    mod = _mod()
    want = _refused_names_all() - {VAR}
    prefixes = tuple(mod.REFUSED_ENV_PREFIXES)
    assert prefixes == ("ANTHROPIC_",)
    # GC-5: covered = a member of REFUSED_ENV_NAMES or a name under a refused prefix
    for name in sorted(want):
        assert name in mod.REFUSED_ENV_NAMES or name.startswith(prefixes), name
    assert not [n for n in mod.REFUSED_ENV_NAMES if n.startswith(prefixes)]
    assert VAR not in mod.REFUSED_ENV_NAMES
    env = {"ANTHROPIC_X": "", "SUPABASE_URL": "u", "PATH": "p", VAR: "v"}
    assert mod.refused_names_present(env) == ["ANTHROPIC_X", "SUPABASE_URL"]
    src = SCRIPT.read_text(encoding="utf-8")
    assert "_env_safety" not in src and "from tests" not in src and "import tests" not in src


def test_r62_flag_snapshot(hx, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ENABLE_ARABIC_VERDICT_OUTPUT", "true")
    ff = tmp_path / "flags.txt"
    ff.write_text("ENABLE_VERDICT_PROMPT_TRUTH=true\nENABLE_KB_FIRST_SERVE=false\n", encoding="utf-8",
                  newline="\n")
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1", "--flags-file", str(ff))
    res = hx.results("text")
    assert "ENABLE_ARABIC_VERDICT_OUTPUT" in res["flags_removed"]
    assert res["flags_case"] == "flags_file"
    assert res["flags_applied"] == {"ENABLE_VERDICT_PROMPT_TRUTH": "true", "ENABLE_KB_FIRST_SERVE": "false"}
    bad = tmp_path / "bad.txt"
    bad.write_text("SERPER_API_KEY=x\n", encoding="utf-8", newline="\n")
    out3 = tmp_path / "out3"
    assert hx.mod.main(["text", "--dry-run", "--flags-file", str(bad), "--out", str(out3)]) == 2
    assert "flags_file" in capsys.readouterr().err


def test_r63_web_search_settings(hx):
    mod = hx.mod
    assert tuple(mod.WEB_SEARCH_TOOL_TYPES) == ("web_search_20250305", "web_search_20260318")
    assert mod.WEB_SEARCH_RESULT_TOKENS_BOUND == 60000
    assert hx.run("web_search", "--dry-run", "--owner-line", "2026-11-12 10:00") == 0
    plan = _plan(hx, "web_search")
    assert set(plan["settings"]) == {"W1_one_turn_20250305", "W2_with_format_20250305",
                                     "W3_one_turn_20260318", "W4_with_format_20260318"}
    assert all(v["calls"] == 20 for v in plan["settings"].values())


def test_r64_report_sentences(hx):
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    assert ("A6 measures adherence to the deterministic scores_summary carried by the prompt (the production "
            "WINNER_INDEX_MISMATCH rule), not verdict quality against owner gold.") in rep
    assert "The unit ceiling is per output folder; the workspace spend limit is the only cross-folder backstop." in rep
    assert str(hx.out.resolve()) in rep
    assert hx.results("text")["out_dir"] == str(hx.out.resolve())


def test_r65_rate_limit_give_up_stops_setting_only(monkeypatch, tmp_path, clean_env):
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _status_exc(429, headers={"retry-after": "1"}) if n <= 4 else _msg())
    code = hx.run("text", "--settings", "A1_sites,A5_count_tokens", "--max-calls", "30")
    res = hx.results("text")
    assert res["settings"]["A1_sites"]["stop_reason"] == "rate_limit"
    assert len([kw for c in hx.clients for kw in c.counts]) == 20
    assert code in (0, 6) and res["stop_reason"] != "rate_limit"


def test_p06_gold_labels_recompute(monkeypatch):
    gold_path = FIXTURES / "verdict_gold.json"
    assert gold_path.exists(), "missing fixture verdict_gold.json"
    for name in SCORING_FLAGS:
        monkeypatch.delenv(name, raising=False)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    from app.services import scoring_service
    from app.services.text_sanitize import dedup_brand_name
    svc = scoring_service.get_scoring_service()
    assert len(gold) == 60
    for case in gold:
        pair = [case["product_a"], case["product_b"]]
        res = svc.compute_scores(pair)
        assert res["winner_index"] == case["gold_winner_index"], case["case_id"]
        names = [dedup_brand_name(str(p.get("brand") or ""), str(p.get("name") or "")) for p in pair]
        assert svc.build_scores_summary(res, names) == case["scores_summary"], case["case_id"]


# --------------------------------------------------------------------------
# P rows (green at base)
# --------------------------------------------------------------------------
def test_p01_app_never_imports_the_harness():
    for path in sorted((REPO / "app").rglob("*.py")):
        assert "meas_claude_gate" not in path.read_text(encoding="utf-8", errors="replace"), str(path)


def test_p02_router_sites_contract():
    router = _router()
    want = {"classify": ("text", 32), "parse": ("text", 768), "specs": ("text", 1536), "price": ("text", 512),
            "price_training": ("text", 384), "reviews": ("text", 1024), "verdict": ("verdict", 1536),
            "verdict_fallback": ("verdict", 1536), "image_tier3": ("text", 256), "vision_v2": ("vision", 1536),
            "vision_v1": ("vision", 768), "specs_targeted": ("text", 384), "specs_synthesized": ("text", 512),
            "disambiguate": ("text", 256), "url_extract": ("text", 1200), "critique": ("critic", 512)}
    assert {k: (v.role, v.claude_max_tokens) for k, v in router.SITES.items()} == want
    req = router.to_claude_request("classify", {"model": "x", "messages": [
        {"role": "system", "content": "s"}, {"role": "user", "content": "u"}], "max_tokens": 5})
    assert set(req) == {"model", "messages", "max_tokens", "thinking", "output_config", "system"}
    assert router.ANTHROPIC_BASE_URL == "https://api.anthropic.com"
    assert router.CALL_DEADLINE_DEFAULT_SECONDS == 25.0
    assert router.MODERATION_MAX_TOKENS == 64


def test_p03_builders_capture_offline(monkeypatch):
    for suffix in ("TEXT", "VISION", "VERDICT", "CRITIC", "MODERATION"):
        monkeypatch.setenv("ENABLE_ANTHROPIC_" + suffix, "true")
    monkeypatch.setenv("ENABLE_SONNET_ESCALATION", "true")
    router = _router()
    from app.services import extraction_service as es
    from app.services import image_service as isvc
    from app.services import openai_service as osvc
    from app.services import url_extraction_service as us
    captured = {}

    class _Cap(Exception):
        pass

    async def cap(site, dispatch, client, **kwargs):
        captured.setdefault(site, kwargs)
        raise _Cap()

    monkeypatch.setattr(router, "route", cap)
    for m in (es, osvc, isvc, us):
        for attr in ("get_client", "get_openai_client", "_get_client"):
            if hasattr(m, attr):
                monkeypatch.setattr(m, attr, lambda *a, **k: object())
    b, n, v = "Dior", "Sauvage", "Eau de Toilette 100ml"
    ctx = "<SEARCH_RESULTS>\n[snippet_0] Synthetic note: fresh and spicy, 100 ml.\n</SEARCH_RESULTS>"
    p1 = {"brand": "Dior", "name": "Sauvage", "variant": "EDT 100ml", "category": "fragrances",
          "specs": {"concentration": "EDT"}, "price": {"amount": 45.0, "currency": "BHD", "estimated": False},
          "reviews": {"average_rating": 4.5, "review_count": 10, "summary": "Fresh."}}
    p2 = dict(p1, brand="Chanel", name="Bleu de Chanel")
    calls = {
        "classify": lambda: es.classify_category_llm(["Dior Sauvage EDT 100ml", "Bleu de Chanel EDP 100ml"]),
        "parse": lambda: es.parse_product_query("Dior Sauvage EDT vs Bleu de Chanel EDP"),
        "specs": lambda: es.extract_specs(b, n, v, "fragrances", ctx, None, None),
        "price": lambda: es.extract_price(b, n, v, "bahrain", ctx),
        "price_training": lambda: es.extract_price_from_training_data(b, n, v, "bahrain"),
        "reviews": lambda: es.extract_reviews(b, n, v, ctx, "fragrances"),
        "verdict": lambda: es.generate_comparison(p1, p2, "bahrain", None, None, "Dior: 72; Chanel: 75",
                                                  "fragrances"),
        "image_tier3": lambda: isvc.extract_image_via_gpt("Dior Sauvage EDT 100ml", [
            {"title": "Dior Sauvage", "link": "https://example.com/p", "snippet": "synthetic"}]),
        "specs_targeted": lambda: osvc.extract_specs_targeted(b, n, v, "fragrances", ["top_notes"], ctx),
        "specs_synthesized": lambda: osvc.extract_specs_synthesized(b, n, v, "fragrances", ["top_notes"]),
        "disambiguate": lambda: osvc.disambiguate_variant_line("fragrances", "Dior Sauvage EDT",
                                                               "Dior Sauvage Elixir 60ml", "concentration"),
        "url_extract": lambda: us.extract_with_ai("https://example.com/p/s", "<html><h1>Dior Sauvage</h1></html>",
                                                  "example", False),
    }

    async def drive():
        for fn in calls.values():
            try:
                await fn()
            except Exception:  # noqa: BLE001 - the capture raises; a builder may wrap it
                pass

    asyncio.run(drive())
    assert set(captured) == set(TEXT_SITES)
    for site, kw in captured.items():
        router.to_claude_request(site, kw)


def test_p04_price_rows():
    from app.services import llm_pricing as lp
    assert lp.ANTHROPIC_PRICE_TABLE_AS_OF == "2026-10-22"
    assert lp.ANTHROPIC_PRICE_USD_PER_1M["claude-haiku-5-5"] == {
        "input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write_5m": 0.125, "cache_write_1h": 0.20}
    assert lp.ANTHROPIC_PRICE_USD_PER_1M["claude-sonnet-5-5"] == {
        "input": 2.00, "output": 10.00, "cache_read": 0.10, "cache_write_5m": 2.50, "cache_write_1h": 4.00}
    assert lp.HAIKU_LONG_CONTEXT["threshold_prompt_tokens"] == 100000
    assert (lp.HAIKU_LONG_CONTEXT["input"], lp.HAIKU_LONG_CONTEXT["output"]) == (0.50, 2.50)
    assert lp.WEB_SEARCH_USD_PER_REQUEST == 0.01
    assert lp.LONG_CONTEXT_THRESHOLD_PROMPT_TOKENS["claude-sonnet-5-5"] == 200000


def _mock_client(handler, **kw):
    import anthropic
    import httpx2
    return anthropic.AsyncAnthropic(base_url="https://api.anthropic.com", max_retries=0,
                                    http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)), **kw)


def _ok_json():
    return {"id": "m", "type": "message", "role": "assistant", "model": "claude-haiku-5-5", "content": [],
            "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}


_REQ = dict(model="claude-haiku-5-5", max_tokens=8, messages=[{"role": "user", "content": "hi"}])


def _fake_profile(tmp_path, monkeypatch, token):
    # The SDK's profile folder: %APPDATA%/Anthropic on Windows, ~/.config/anthropic on Linux and macOS
    # (M-11). The same fake profile is written at both; on POSIX the SDK refuses a credentials file that
    # group or others can read or write, so the folders get 0o700 and the files 0o600.
    for base in (tmp_path / "Anthropic", tmp_path / ".config" / "anthropic"):
        made = [base, base / "configs", base / "credentials"]
        if base.parent != tmp_path:
            made.insert(0, base.parent)
        (base / "configs").mkdir(parents=True)
        (base / "credentials").mkdir(parents=True)
        files = [base / "configs" / "default.json", base / "credentials" / "default.json", base / "active_config"]
        files[0].write_text(json.dumps({"authentication": {"type": "user_oauth"}}), encoding="utf-8")
        files[1].write_text(json.dumps({"type": "oauth_token", "access_token": token}), encoding="utf-8")
        files[2].write_text("default", encoding="utf-8")
        if os.name == "posix":
            for folder in made:
                os.chmod(folder, 0o700)
            for f in files:
                os.chmod(f, 0o600)
    for name in ("APPDATA", "HOME", "USERPROFILE", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(tmp_path))
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_"):
            monkeypatch.delenv(name, raising=False)


def test_p05_sdk_hazards(monkeypatch, tmp_path):
    import anthropic
    import anthropic._client as ac
    import httpx2
    probe = _make_canary()
    seen = []

    def h(req):
        seen.append(req)
        return httpx2.Response(200, json=_ok_json())

    token = "profile" + "-tok-" + secrets.token_hex(4)
    _fake_profile(tmp_path, monkeypatch, token)
    dc = []
    real_dc = ac.default_credentials
    monkeypatch.setattr(ac, "default_credentials", lambda *a, **k: dc.append(1) or real_dc(*a, **k))
    asyncio.run(_mock_client(h, api_key=probe).messages.create(**_REQ))
    r = seen[-1]
    assert str(r.url) == "https://api.anthropic.com/v1/messages"
    assert r.headers.get("x-api-key") == probe
    assert "authorization" not in {k.lower() for k in r.headers.keys()}
    assert dc == []
    n = []

    def h529(req):
        n.append(1)
        return httpx2.Response(529, json={"type": "error", "error": {"type": "overloaded_error", "message": "m"}})

    with pytest.raises(anthropic.OverloadedError):
        asyncio.run(_mock_client(h529, api_key=probe).messages.create(**_REQ))
    assert len(n) == 1
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", "X-S07-Decoy: 1")
    asyncio.run(_mock_client(h, api_key=probe).messages.create(**_REQ))
    assert seen[-1].headers.get("x-s07-decoy") == "1"
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS")
    marker = "S07BODYMARKER"

    def h400(req):
        return httpx2.Response(400, json={"type": "error", "error": {"type": "invalid_request_error",
                                                                      "message": marker}})

    with pytest.raises(anthropic.BadRequestError) as ei:
        asyncio.run(_mock_client(h400, api_key=probe).messages.create(**_REQ))
    assert marker in str(ei.value)
    assert ei.value.response.request.headers.get("x-api-key") == probe
    assert probe not in str(ei.value) and probe not in repr(ei.value)


def test_p07_stream_events_and_usage_classes():
    import anthropic.types as T
    import httpx2
    events = _stream_events(inp=25, out=15)
    body = "".join("event: %s\ndata: %s\n\n" % (e.type, e.model_dump_json()) for e in events).encode()

    def h(req):
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    async def go(b):
        def hh(req):
            return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=b)
        s = await _mock_client(hh, api_key="probe-value").messages.create(stream=True, **_REQ)
        return [e async for e in s]

    got = asyncio.run(go(body))
    assert [e.type for e in got] == ["message_start", "content_block_start", "content_block_delta",
                                     "content_block_stop", "message_delta", "message_stop"]
    assert type(got[0].message.usage).__name__ == "Usage"
    assert type(got[4].usage).__name__ == "MessageDeltaUsage"
    assert set(T.MessageDeltaUsage.model_fields) == {"cache_creation_input_tokens", "cache_read_input_tokens",
                                                     "input_tokens", "output_tokens", "output_tokens_details",
                                                     "server_tool_use"}
    assert "cache_read_input_tokens" in T.Usage.model_fields and "server_tool_use" in T.Usage.model_fields
    trunc = "".join("event: %s\ndata: %s\n\n" % (e.type, e.model_dump_json())
                    for e in _stream_events(stop=False)).encode()
    got2 = asyncio.run(go(trunc))
    assert [e.type for e in got2] == ["message_start", "content_block_start", "content_block_delta"]


def test_p08_exception_class_map():
    import anthropic
    import httpx2
    want = {400: "BadRequestError", 401: "AuthenticationError", 403: "PermissionDeniedError",
            404: "NotFoundError", 409: "ConflictError", 413: "RequestTooLargeError",
            422: "UnprocessableEntityError", 429: "RateLimitError", 500: "InternalServerError",
            502: "InternalServerError", 503: "InternalServerError", 504: "InternalServerError",
            529: "OverloadedError"}
    got = {}
    for st in want:
        def h(req, st=st):
            return httpx2.Response(st, headers={"retry-after": "2"},
                                   json={"type": "error", "error": {"type": "x", "message": "m"}})
        try:
            asyncio.run(_mock_client(h, api_key="probe-value").messages.create(**_REQ))
        except anthropic.APIStatusError as exc:
            got[st] = type(exc).__name__
            assert exc.status_code == st and exc.response.headers.get("retry-after") == "2"
    assert got == want
    for kind, cls in ((httpx2.ReadTimeout, anthropic.APITimeoutError),
                      (httpx2.ConnectTimeout, anthropic.APITimeoutError),
                      (httpx2.ConnectError, anthropic.APIConnectionError),
                      (httpx2.ReadError, anthropic.APIConnectionError)):
        def h(req, kind=kind):
            raise kind("x", request=req)
        with pytest.raises(cls) as ei:
            asyncio.run(_mock_client(h, api_key="probe-value").messages.create(**_REQ))
        assert isinstance(ei.value, anthropic.APIConnectionError)
    assert issubclass(anthropic.APITimeoutError, anthropic.APIConnectionError)


def test_p09_web_search_tool_types():
    import anthropic.types as T
    found = set()
    for attr in dir(T):
        if attr.startswith("WebSearchTool") and attr.endswith("Param") and attr[13:21].isdigit():
            found.add("web_search_" + attr[13:21])
    assert {"web_search_20250305", "web_search_20260318"} <= found
    assert found == {"web_search_20250305", "web_search_20260209", "web_search_20260318"}


def test_p10_credential_profile_control(monkeypatch, tmp_path):
    import anthropic._client as ac
    import httpx2
    token = "profile" + "-tok-" + secrets.token_hex(4)
    _fake_profile(tmp_path, monkeypatch, token)
    seen = []
    dc = []
    real_dc = ac.default_credentials
    monkeypatch.setattr(ac, "default_credentials", lambda *a, **k: dc.append(1) or real_dc(*a, **k))

    def h(req):
        seen.append(req)
        return httpx2.Response(200, json=_ok_json())

    asyncio.run(_mock_client(h).messages.create(**_REQ))
    assert dc == [1]
    assert token in seen[-1].headers.get("authorization", "")
    assert "x-api-key" not in {k.lower() for k in seen[-1].headers.keys()}


def test_p11_scripts_client_allowlist():
    allowed = {"cron_compare_judge.py", "seed_kb_batch.py", "meas_claude_gate.py"}
    pat = re.compile(r'import_module\(["\']anthropic["\']\)|^\s*import anthropic|^\s*from anthropic|AsyncAnthropic\(|'
                     r'\bAnthropic\(', re.M)
    found = {p.name for p in (REPO / "scripts").rglob("*.py") if pat.search(p.read_text(encoding="utf-8",
                                                                                        errors="replace"))}
    assert found <= allowed, sorted(found - allowed)
    assert {"cron_compare_judge.py", "seed_kb_batch.py"} <= found


def test_p12_suite_credential_lists():
    es = _env_safety()
    for name in ("UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN", "SERPER_API_KEY", "ANTHROPIC_API_KEY",
                 "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "SENTRY_DSN"):
        assert name in es.CREDENTIALS_UNSET
    for name in ("OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY", "YOUTUBE_API_KEY"):
        assert name in es.CREDENTIAL_PLACEHOLDERS


# --------------------------------------------------------------------------
# GATE rows (GATE_S81_07 GC-6..GC-14, written RED-first by GREEN's step 0)
# --------------------------------------------------------------------------
def test_r66_sticky_stop_inflight_sends_awaited(monkeypatch, tmp_path, clean_env, capsys, caplog):
    """GC-6: after a stop no new send starts; sends already made reach their done line."""
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _status_exc(401) if n == 5 else _msg())
    code = hx.run("text", "--settings", "A1_sites")
    assert code == 5
    assert len(hx.creates) == 5
    lines = hx.ledger("text")
    sent = {(x["call_id"], x["attempt"]) for x in _intents(lines)}
    done = {(x["call_id"], x["attempt"]) for x in _done(lines)}
    assert len(sent) == 5 and sent == done
    oks = [x for x in _done(lines) if x["ok"]]
    assert sorted(x["site"] for x in oks) == ["classify", "parse", "specs", "specs"]
    assert hx.results("text")["stop_reason"] == "auth"
    err = capsys.readouterr().err
    assert "never retrieved" not in err and "never retrieved" not in caplog.text


def test_r67_lock_released_on_every_exit(monkeypatch, tmp_path, clean_env, capsys):
    """GC-7: the lock is removed on every exit after its creation."""
    mod = _mod()
    Harness(mod, monkeypatch, tmp_path)

    def absent(out):
        return not (out / ".meas_lock").exists()

    o1 = tmp_path / "o1"
    _write_ledger(o1 / "moderation" / "spend.jsonl", 11.50)
    assert mod.main(["text", "--settings", "A1_sites", "--out", str(o1)]) == 4
    assert absent(o1)
    o2 = tmp_path / "o2"
    (o2 / "text").mkdir(parents=True)
    (o2 / "text" / "spend.jsonl").write_text("not json\n", encoding="utf-8", newline="\n")
    assert mod.main(["text", "--dry-run", "--out", str(o2)]) == 2
    assert absent(o2)
    o3 = tmp_path / "o3"
    bad = tmp_path / "bad_flags.txt"
    bad.write_text("SERPER_API_KEY=x\n", encoding="utf-8", newline="\n")
    assert mod.main(["text", "--dry-run", "--flags-file", str(bad), "--out", str(o3)]) == 2
    assert absent(o3)
    o4 = tmp_path / "o4"
    monkeypatch.setenv(VAR, clean_env)
    monkeypatch.setattr(mod, "Dispatcher", _crashing_dispatcher(mod, clean_env))
    assert mod.main(["text", "--settings", "A1_sites", "--max-calls", "2", "--out", str(o4)]) == 3
    assert absent(o4)

    def imp(*a, **k):
        os.environ["ANTHROPIC_DECOY"] = "1"

    monkeypatch.setattr(mod, "_import_app_modules", imp)
    o5 = tmp_path / "o5"
    try:
        assert mod.main(["text", "--dry-run", "--out", str(o5)]) == 2
    finally:
        os.environ.pop("ANTHROPIC_DECOY", None)
    assert absent(o5)
    capsys.readouterr()


def test_r68_guard_runs_in_dry_run(monkeypatch, tmp_path, clean_env):
    """GC-8: in --dry-run only loopback is allowed; another host stops the stage before the plan."""
    import socket
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path)
    router = _router()
    real_gai = socket.getaddrinfo
    real = router.to_claude_request
    escaped = []

    def spy(site, kwargs):
        try:
            socket.getaddrinfo("example.invalid", 443)
        except mod.StageStop:
            raise
        except OSError:
            escaped.append(site)
        return real(site, kwargs)

    monkeypatch.setattr(router, "to_claude_request", spy)
    code = hx.run("text", "--dry-run", "--settings", "A4_refusal_names")
    assert code == 6
    assert escaped == []
    assert not (hx.out / "text" / "plan.json").exists()
    assert hx.results("text")["stop_reason"] == "host_refused"
    assert socket.getaddrinfo is real_gai
    assert hx.clients == [] and hx.key_reads == []


def test_r69_client_hook_refuses_other_urls(hx):
    """GC-9: the harness's own HTTP client refuses any URL but https://api.anthropic.com:443."""
    import httpx2
    mod = hx.mod
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    client = hx.clients[0].kwargs["http_client"]
    left = []

    def h(req):
        left.append(str(req.url))
        return httpx2.Response(200, json={})

    client._transport = httpx2.MockTransport(h)

    async def go(url):
        try:
            await client.get(url)
        except mod.StageStop as s:
            return s.reason
        return "sent"

    for url in ("https://example.invalid/v1/messages", "http://api.anthropic.com/v1/messages",
                "https://api.anthropic.com:8443/v1/messages", "https://api.anthropic.com.example.invalid/x"):
        assert asyncio.run(go(url)) == "host_refused", url
    assert left == []
    assert asyncio.run(go("https://api.anthropic.com/v1/messages")) == "sent"
    assert left == ["https://api.anthropic.com/v1/messages"]


def test_r70_credential_leaves_the_environment(monkeypatch, tmp_path, clean_env):
    """GC-10: the variable is removed right after the read and is not restored at exit."""
    mod = _mod()
    seen = []

    def beh(kw, n):
        seen.append(VAR in os.environ)
        return _msg()

    hx = Harness(mod, monkeypatch, tmp_path, behaviour=beh)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    assert hx.clients and hx.clients[0].kwargs["api_key"] == clean_env
    assert seen == [False, False]
    assert VAR not in os.environ


def test_r71_base_sha_seam(hx, monkeypatch, canary):
    """GC-11: base_sha comes from _git_head() (git rev-parse HEAD in REPO_ROOT, 5 s, None on failure)."""
    import subprocess
    mod = hx.mod
    seam = _attr(mod, "_git_head")
    monkeypatch.setattr(mod, "_git_head", lambda: "ab" * 20)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert hx.results("text")["base_sha"] == "ab" * 20
    monkeypatch.setattr(mod, "_git_head", lambda: None)
    monkeypatch.setenv(VAR, canary)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    assert hx.results("text")["base_sha"] is None
    sp = _attr(mod, "subprocess")
    calls = []

    def boom(*a, **k):
        calls.append((a, k))
        raise OSError("synthetic")

    monkeypatch.setattr(sp, "run", boom)
    assert seam() is None
    args, kw = calls[0]
    assert list(args[0]) == ["git", "rev-parse", "HEAD"]
    assert kw.get("timeout") == 5 and Path(kw.get("cwd")).resolve() == REPO

    def slow(*a, **k):
        raise subprocess.TimeoutExpired("git", 5)

    monkeypatch.setattr(sp, "run", slow)
    assert seam() is None

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    monkeypatch.setattr(sp, "run", lambda *a, **k: _R(1, ""))
    assert seam() is None
    monkeypatch.setattr(sp, "run", lambda *a, **k: _R(0, "not-a-sha\n"))
    assert seam() is None
    monkeypatch.setattr(sp, "run", lambda *a, **k: _R(0, "cd" * 20 + "\n"))
    assert seam() == "cd" * 20


def _go_results():
    """A results set exactly ON every ruled bar (GC-12)."""
    sites = {}
    for s in ("classify", "specs", "reviews", "price", "image_tier3"):
        sites[s] = {"n": 20, "json_n": 20, "json_valid": 20, "schema_n": 20, "schema_accepted": 20,
                    "max_tokens_hits": 0, "refusals": 0, "timeouts": 0, "p95_s": 1.0}
    sites["parse"] = {"n": 100, "json_n": 100, "json_valid": 100, "schema_n": 0, "schema_accepted": 0,
                      "max_tokens_hits": 0, "refusals": 0, "timeouts": 0, "p95_s": 1.0}
    sites["verdict"] = {"n": 20, "json_n": 20, "json_valid": 20, "schema_n": 0, "schema_accepted": 0,
                        "max_tokens_hits": 0, "refusals": 0, "timeouts": 0, "p95_s": 9.0}
    sites["classify"]["json_valid"] = 18
    sites["specs"]["json_valid"] = 19
    sites["reviews"]["json_valid"] = 19
    sites["classify"]["max_tokens_hits"] = 2
    sites["specs"]["max_tokens_hits"] = 2
    for s, v in {"classify": 4.0, "specs": 4.0, "reviews": 5.0, "price": 7.5, "image_tier3": 2.5}.items():
        sites[s]["p95_s"] = v
    text = {"not_runnable": [], "settings": {
        "A1_sites": {"sites": sites},
        "A3_sonnet_between_tools": {"n": 20, "accepted": 20, "json_n": 20, "json_valid": 19},
        "A4_refusal_names": {"n": 100, "refusals": 1, "n_arabic": 30, "refusals_arabic": 0},
        "A6_verdict_eval": {"n": 80, "json_n": 80, "json_valid": 78, "mismatches": 10, "n_scored": 100,
                            "agreement": 0.90, "refusals": 1, "timeouts": 0}}}
    moderation = {"not_runnable": [], "settings": {"M1_parity": {
        "false_positives": 0, "n_benign_run": 80, "flagged_hits": 18, "n_flagworthy_run": 20, "fail_closed": 1,
        "p95_s": 3.0}}}
    vision = {"not_runnable": [], "settings": {"V2_haiku_vision_v2": {"hit_rate": 0.80, "p99_s": 20.0},
                                               "V3_sonnet_vision_v2": {"hit_rate": 0.85}}}
    web = {"not_runnable": [], "settings": {}}
    return {"text": text, "moderation": moderation, "vision": vision, "web_search": web}


def _set(path, value):
    def apply(res):
        node = res
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return apply


_A1 = ("text", "settings", "A1_sites", "sites")
_CROSSINGS = [
    ("TEXT", [_set(_A1 + ("price", "json_valid"), 19), _set(_A1 + ("image_tier3", "json_valid"), 19)],
     "json_valid_pooled_min"),
    ("TEXT", [_set(_A1 + ("classify", "json_valid"), 17), _set(_A1 + ("specs", "json_valid"), 20)],
     "json_valid_site_min"),
    ("TEXT", [_set(_A1 + ("price", "schema_accepted"), 19)], "schema_accept_min"),
    ("TEXT", [_set(("text", "settings", "A4_refusal_names", "refusals"), 2)], "refusals_a4_max"),
    ("TEXT", [_set(("text", "settings", "A4_refusal_names", "refusals_arabic"), 1)], "refusals_a4_arabic_max"),
    ("TEXT", [_set(_A1 + ("reviews", "max_tokens_hits"), 2)], "max_tokens_pooled_max"),
    ("TEXT", [_set(_A1 + ("classify", "max_tokens_hits"), 3), _set(_A1 + ("specs", "max_tokens_hits"), 1)],
     "max_tokens_site_max_hits"),
    ("TEXT", [_set(_A1 + ("classify", "p95_s"), 4.1)], "p95_s.classify"),
    ("TEXT", [_set(_A1 + ("specs", "p95_s"), 4.1)], "p95_s.specs"),
    ("TEXT", [_set(_A1 + ("reviews", "p95_s"), 5.1)], "p95_s.reviews"),
    ("TEXT", [_set(_A1 + ("price", "p95_s"), 7.6)], "p95_s.price"),
    ("TEXT", [_set(_A1 + ("image_tier3", "p95_s"), 2.6)], "p95_s.image_tier3"),
    ("TEXT", [_set(_A1 + ("parse", "timeouts"), 1)], "timeouts_max"),
    ("VERDICT", [_set(("text", "settings", "A6_verdict_eval", "json_valid"), 77)], "json_valid_pooled_min"),
    ("VERDICT", [_set(("text", "settings", "A6_verdict_eval", "mismatches"), 11)], "a6_mismatch_max"),
    ("VERDICT", [_set(("text", "settings", "A6_verdict_eval", "agreement"), 0.89)], "a6_agreement_min"),
    ("VERDICT", [_set(("text", "settings", "A6_verdict_eval", "refusals"), 2)], "a6_refusals_max"),
    ("VERDICT", [_set(_A1 + ("verdict", "refusals"), 1)], "a1_refusals_max"),
    ("VERDICT", [_set(("text", "settings", "A6_verdict_eval", "timeouts"), 1)], "timeouts_max"),
    ("SONNET_ESCALATION", [_set(("text", "settings", "A3_sonnet_between_tools", "accepted"), 19)], "accepted_min"),
    ("SONNET_ESCALATION", [_set(("text", "settings", "A3_sonnet_between_tools", "json_valid"), 18)],
     "json_valid_min"),
    ("MODERATION", [_set(("moderation", "settings", "M1_parity", "false_positives"), 1)], "false_positives_max"),
    ("MODERATION", [_set(("moderation", "settings", "M1_parity", "flagged_hits"), 17)], "recall_min"),
    ("MODERATION", [_set(("moderation", "settings", "M1_parity", "fail_closed"), 2)], "fail_closed_max"),
    ("MODERATION", [_set(("moderation", "settings", "M1_parity", "p95_s"), 3.1)], "p95_s"),
    ("VISION", [_set(("vision", "settings", "V2_haiku_vision_v2", "hit_rate"), 0.79),
                _set(("vision", "settings", "V3_sonnet_vision_v2", "hit_rate"), 0.80)], "haiku_hit_min"),
    ("VISION", [_set(("vision", "settings", "V3_sonnet_vision_v2", "hit_rate"), 0.86)], "haiku_minus_sonnet_min"),
    ("VISION", [_set(("vision", "settings", "V2_haiku_vision_v2", "p99_s"), 20.5)], "p99_s"),
]


@pytest.mark.parametrize("role", ["TEXT", "VERDICT", "SONNET_ESCALATION", "MODERATION", "VISION"])
def test_r72_go_exactly_on_every_bar(role):
    """GC-12: a results set exactly on every bar is GO."""
    mod = _mod()
    ev = _attr(mod, "evaluate_role")
    assert ev(role, _go_results()) == ("GO", [])


@pytest.mark.parametrize("role,edits,bar", _CROSSINGS, ids=["%s-%s" % (c[0], c[2]) for c in _CROSSINGS])
def test_r72b_one_bar_crossed(role, edits, bar):
    """GC-12: one bar crossed at a time gives NO-GO naming that bar."""
    mod = _mod()
    ev = _attr(mod, "evaluate_role")
    res = _go_results()
    for e in edits:
        e(res)
    assert ev(role, res) == ("NO-GO", [bar])


def test_r72c_not_run():
    """GC-12: a missing stage gives NOT RUN; CRITIC and WEB_SEARCH are never GO or NO-GO."""
    mod = _mod()
    ev = _attr(mod, "evaluate_role")
    for role in ("TEXT", "VERDICT", "SONNET_ESCALATION", "CRITIC", "MODERATION", "VISION", "WEB_SEARCH"):
        assert ev(role, {})[0] == "NOT RUN", role
    full = _go_results()
    assert ev("CRITIC", full)[0] == "NOT RUN" and ev("WEB_SEARCH", full)[0] == "NOT RUN"
    nr = _go_results()
    nr["vision"]["not_runnable"] = ["no_photo_set"]
    assert ev("VISION", nr)[0] == "NOT RUN"


def test_r73_vision_identity_rule(monkeypatch, tmp_path, clean_env):
    """GC-13 (V): brand AND name match, case-insensitive, token-wise."""
    mod = _mod()
    hit = _attr(mod, "identity_hit")
    assert hit({"products": [{"brand": "Dior", "name": "Eau Sauvage"}]}, "Dior", "Eau Sauvage") is True
    assert hit({"products": [{"brand": "Dior", "name": "Bleu"}]}, "Dior", "Eau Sauvage") is False
    assert hit({"products": [{"brand": " DIOR ", "name": "eau   SAUVAGE"}]}, "Dior", "Eau Sauvage") is True
    assert hit({"products": [{"brand": "Chanel", "name": "Eau Sauvage"}]}, "Dior", "Eau Sauvage") is False
    assert hit(json.dumps({"products": [{"brand": "Dior", "name": "Eau Sauvage"}]}), "Dior", "Eau Sauvage") is True
    assert hit("not json", "Dior", "Eau Sauvage") is False
    answers = [{"products": [{"brand": "Dior", "name": "Sauvage"}]},
               {"products": [{"brand": "Dior", "name": "Bleu"}]},
               {"products": [{"brand": "dior", "name": "  SAUVAGE "}]}]
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _msg(json.dumps(answers[(n - 1) % 3])))
    photos = _png_set(tmp_path / "ph", 3)
    assert hx.run("vision", "--set", str(photos)) == 0
    settings = hx.results("vision")["settings"]
    for name in ("V1_haiku_vision_v1", "V2_haiku_vision_v2", "V3_sonnet_vision_v2"):
        assert (settings[name]["hits"], settings[name]["n_scored"]) == (2, 3), name
        assert settings[name]["hit_rate"] == pytest.approx(2.0 / 3.0)


def _msg_cited():
    import anthropic.types as T
    return T.Message.model_validate({
        "id": "msg_s07w", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": "{}", "citations": [{
            "type": "web_search_result_location", "cited_text": "synthetic", "encrypted_index": "e",
            "title": "t", "url": "https://example.com/"}]}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5,
                  "server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 0}}})


def test_r74_web_search_accept_and_reject(monkeypatch, tmp_path, clean_env):
    """GC-13 (W): a 400 on tool + format is recorded accepted false and the setting continues; a 200 records
    accepted true, the web-search request count and the citations count."""
    mod = _mod()

    def beh(kw, n):
        if kw.get("tools") and (kw.get("output_config") or {}).get("format"):
            return _status_exc(400)
        return _msg_cited()

    hx = Harness(mod, monkeypatch, tmp_path, behaviour=beh)
    code = hx.run("web_search", "--owner-line", "2026-11-12 10:00", "--settings",
                  "W1_one_turn_20250305,W2_with_format_20250305")
    assert code == 0
    s = hx.results("web_search")["settings"]
    assert set(s) == {"W1_one_turn_20250305", "W2_with_format_20250305"}
    w1, w2 = s["W1_one_turn_20250305"], s["W2_with_format_20250305"]
    assert (w1["accepted"], w1["web_search_requests"], w1["citations"]) == (20, 20, 20)
    assert len(w1["outcomes"]) == 20 and all(o["accepted"] is True for o in w1["outcomes"])
    assert w2["calls"] == 20 and w2["accepted"] == 0
    assert all((o["accepted"], o["error_class"], o["status"]) == (False, "BadRequestError", 400)
               for o in w2["outcomes"]) and len(w2["outcomes"]) == 20


_SITECUSTOMIZE = "\n".join([
    "import os",
    "import socket",
    "_F = os.environ.get('S07_NETGUARD_FILE')",
    "def _bad(host):",
    "    h = str(host or '').strip().lower()",
    "    return not (h in ('', 'localhost', '127.0.0.1', '::1', '0.0.0.0') or h.startswith('127.'))",
    "def _rec(kind, host):",
    "    with open(_F, 'a', encoding='utf-8') as fh:",
    "        fh.write('%s %s' % (kind, host) + chr(10))",
    "    raise OSError('s07 recorder blocked')",
    "def _host(addr):",
    "    return addr[0] if isinstance(addr, tuple) else ''",
    "if _F:",
    "    _gai, _c, _cx, _cc = (socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex,",
    "                          socket.create_connection)",
    "    def getaddrinfo(host, *a, **k):",
    "        if _bad(host):",
    "            _rec('getaddrinfo', host)",
    "        return _gai(host, *a, **k)",
    "    def connect(self, addr):",
    "        if _bad(_host(addr)):",
    "            _rec('connect', _host(addr))",
    "        return _c(self, addr)",
    "    def connect_ex(self, addr):",
    "        if _bad(_host(addr)):",
    "            _rec('connect_ex', _host(addr))",
    "        return _cx(self, addr)",
    "    def create_connection(addr, *a, **k):",
    "        if _bad(_host(addr)):",
    "            _rec('create_connection', _host(addr))",
    "        return _cc(addr, *a, **k)",
    "    socket.getaddrinfo = getaddrinfo",
    "    socket.socket.connect = connect",
    "    socket.socket.connect_ex = connect_ex",
    "    socket.create_connection = create_connection",
    "",
])


@pytest.mark.timeout(180)
def test_r75_real_command_line_is_quiet(tmp_path):
    """GC-14: the real command line, a dry run with a cleaned environment: exit 0, stderr empty, the plan
    written, no non-loopback attempt recorded. The file's only subprocess row (own 120 s timeout)."""
    import subprocess
    import sys
    _mod()
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8", newline="\n")
    ng = tmp_path / "netguard.txt"
    ng.write_text("", encoding="utf-8")
    out = tmp_path / "out"
    proxies = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
    refused = _refused_names_all()
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith(("ANTHROPIC_", "ENABLE_", "QAREN_NETGUARD")) or k in refused or k == VAR
                   or k.upper() in proxies or k == "PYTHONPATH")}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(site) + os.pathsep + str(REPO)
    env["S07_NETGUARD_FILE"] = str(ng)
    proc = subprocess.run([sys.executable, "-m", MOD_NAME, "text", "--dry-run", "--out", str(out)],
                          cwd=str(REPO), env=env, capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.returncode
    assert proc.stderr == b"", len(proc.stderr)
    assert (out / "text" / "plan.json").exists()
    assert ng.read_text(encoding="utf-8") == ""


def test_p13_httpx2_request_hook_mechanism():
    """GC-9's measurement on the pinned transport: an async request hook runs before the transport, a
    BaseException raised in it propagates and nothing is sent; the default https port reads as None; a sync
    hook on an AsyncClient is a TypeError."""
    import httpx2

    class _Stop(BaseException):
        pass

    seen, hooked = [], []

    def h(req):
        seen.append(str(req.url))
        return httpx2.Response(200, json={})

    async def hook(request):
        hooked.append((request.url.scheme, request.url.host, request.url.port))
        if request.url.host != "api.anthropic.com":
            raise _Stop()

    async def go():
        c = httpx2.AsyncClient(transport=httpx2.MockTransport(h), event_hooks={"request": [hook]},
                               trust_env=False, follow_redirects=False)
        r = await c.get("https://api.anthropic.com/v1/messages")
        assert r.status_code == 200
        with pytest.raises(_Stop):
            await c.get("https://example.invalid/x")

    asyncio.run(go())
    assert seen == ["https://api.anthropic.com/v1/messages"]
    assert hooked == [("https", "api.anthropic.com", None), ("https", "example.invalid", None)]

    def sync_hook(request):
        return None

    c3 = httpx2.AsyncClient(transport=httpx2.MockTransport(h), event_hooks={"request": [sync_hook]})
    with pytest.raises(TypeError):
        asyncio.run(c3.get("https://api.anthropic.com/v1/messages"))


# --------------------------------------------------------------------------
# FIX1 rows (RULINGS_FIX1_S81_07 F-2..F-7; sanctioned amendments, listed in the
# FIX section of the amendments file)
# --------------------------------------------------------------------------
def _claude_md_s07_block():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = [i for i, x in enumerate(lines) if "SESSION 81 unit (S81-07" in x]
    assert starts, "the CLAUDE.md S81-07 block is missing"
    out = []
    for x in lines[starts[-1] + 1:]:
        if x.startswith("## ") or x.startswith("**SESSION"):
            break
        out.append(x)
    return out


def _assignment_lines(lines):
    return [x for x in lines if (VAR + "=") in x]


def _assignment_before_env(line):
    i = line.index(VAR + "=")
    return re.search(r"\benv\s", line[i:]) is not None and re.search(r"\benv\s", line[:i]) is None


def test_r76_run_command_assignment_before_env():
    """F-2 (B1): every command line naming the credential variable carries the assignment BEFORE the command
    word env (a shell prefix assignment), never after it (an argument of env.exe, visible in the process list);
    the canonical template lives in the script's module docstring and the CLAUDE.md block copies it."""
    _mod()
    src = SCRIPT.read_text(encoding="utf-8").splitlines()
    doc_end = [i for i, x in enumerate(src) if x.strip().endswith('"""')][0]
    in_doc = _assignment_lines(src[:doc_end + 1])
    assert in_doc, "no canonical run template in the module docstring"
    assert _assignment_lines(src) == in_doc, "a credential assignment outside the docstring"
    block = _assignment_lines(_claude_md_s07_block())
    assert block, "the CLAUDE.md block carries no run command"
    for line in in_doc + block:
        assert _assignment_before_env(line), line
    dry = [x for x in src[:doc_end + 1] + _claude_md_s07_block() if "--dry-run" in x and "env -u" in x]
    assert dry and not _assignment_lines(dry)


class _GuardCtx:
    def __init__(self):
        self.hosts_refused = []


def _try(fn, *a):
    mod = _mod()
    try:
        fn(*a)
    except mod.StageStop as s:
        return s.reason
    return "passed"


def test_r77_live_guard_admits_the_allowed_host_end_to_end(monkeypatch, tmp_path, clean_env):
    """F-3 (M1): one live send through the REAL pinned transport (no fake client) with a fake resolver that
    returns a loopback address, on the default loop and on a selector loop: the guard admits the allowed host,
    the resolver wrapper is reached once for it, hosts_refused stays empty, the stage does not stop on
    host_refused. Nothing leaves the machine (loopback only)."""
    import socket
    import sys
    mod = _mod()
    calls = []

    def fake_gai(host, port, *a, **k):
        calls.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", int(port or 443)))]

    async def nosleep(s):
        return None

    monkeypatch.setattr(socket, "getaddrinfo", fake_gai)
    monkeypatch.setattr(mod, "_sleep", nosleep)
    monkeypatch.setattr(mod, "_git_head", lambda: None)
    loops = ["default"]
    if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        loops.append("selector")
    for kind in loops:
        calls.clear()
        monkeypatch.setenv(VAR, clean_env)
        out = tmp_path / ("out_" + kind)
        prev = asyncio.get_event_loop_policy()
        if kind == "selector":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            code = mod.main(["text", "--out", str(out), "--settings", "A4_refusal_names", "--max-calls", "1"])
        finally:
            asyncio.set_event_loop_policy(prev)
        res = json.loads((out / "text" / "results.json").read_text(encoding="utf-8"))
        assert res["stop_reason"] != "host_refused", kind
        assert res["settings"]["A4_refusal_names"]["hosts_refused"] == [], kind
        names = [h.decode("ascii") if isinstance(h, bytes) else h for h, _ in calls]
        assert names == ["api.anthropic.com"], (kind, names)
        assert code == 6 and res["stop_reason"] == "max_calls", (kind, code)
        assert socket.getaddrinfo is fake_gai


def test_r78_other_host_refused_as_str_and_bytes():
    """F-3 (a): the host is read as str or as IDNA bytes (ASCII); another name is refused before any resolution;
    an undecodable host is refused."""
    import socket
    mod = _mod()
    ha = mod.host_allowed
    assert ha(b"api.anthropic.com", 443) is True and ha(bytearray(b"API.Anthropic.com"), 443) is True
    assert ha(b"api.anthropic.com", 80) is False and ha(b"other.invalid", 443) is False
    assert ha(b"\xff\xfe", 443) is False and ha("other.invalid", 443) is False
    assert ha(b"127.0.0.1", 9) is True and ha(b"localhost", 9) is True
    seen = []
    real = socket.getaddrinfo
    ctx, state = _GuardCtx(), {"restore": []}
    socket.getaddrinfo = lambda *a, **k: seen.append(a) or []
    try:
        mod._install_host_guard(ctx, state, True)
        try:
            for host in ("other.invalid", b"other.invalid", b"\xff\xfe"):
                assert _try(socket.getaddrinfo, host, 443) == "host_refused", host
            assert seen == []
            assert _try(socket.getaddrinfo, b"api.anthropic.com", 443) == "passed"
            assert len(seen) == 1
        finally:
            for fn in reversed(state["restore"]):
                fn()
    finally:
        socket.getaddrinfo = real
    assert "other.invalid" in ctx.hosts_refused and not [h for h in ctx.hosts_refused if h.startswith("b'")]


def test_r79_connect_admits_only_addresses_resolved_for_the_allowed_host(monkeypatch):
    """F-3 (b): at the connect step the live guard admits only an address the guarded resolver returned for the
    allowed host in this process, on port 443 (and loopback); every other literal is refused, and an address a
    loopback name resolved to does not join the set."""
    import socket
    mod = _mod()
    connects = []

    def fake_gai(host, port, *a, **k):
        name = host.decode("ascii") if isinstance(host, bytes) else host
        ip = "192.0.2.7" if name == "api.anthropic.com" else "192.0.2.9"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_gai)
    monkeypatch.setattr(socket.socket, "connect", lambda self, addr: connects.append(addr))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: connects.append(addr) or 0)
    ctx, state = _GuardCtx(), {"restore": []}
    mod._install_host_guard(ctx, state, True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        assert _try(s.connect, ("192.0.2.7", 443)) == "host_refused"
        assert _try(s.connect, ("192.0.2.1", 443)) == "host_refused"
        assert connects == []
        assert _try(socket.getaddrinfo, b"api.anthropic.com", 443) == "passed"
        assert _try(s.connect, ("192.0.2.7", 443)) == "passed"
        assert _try(s.connect_ex, ("192.0.2.7", 443)) == "passed"
        assert _try(s.connect, ("192.0.2.7", 80)) == "host_refused"
        assert _try(s.connect, ("192.0.2.1", 443)) == "host_refused"
        assert _try(socket.getaddrinfo, "localhost", 443) == "passed"
        assert _try(s.connect, ("192.0.2.9", 443)) == "host_refused"
        assert connects == [("192.0.2.7", 443), ("192.0.2.7", 443)]
    finally:
        s.close()
        for fn in reversed(state["restore"]):
            fn()


def _clocked(hx, per_create=1.0, extra=None):
    def beh(kw, n):
        hx.clock[0] += per_create
        if extra:
            return extra(kw, n)
        return _msg()
    return beh


def test_r80_resume_gives_the_same_tail_spans(monkeypatch, tmp_path, clean_env):
    """F-4 (a)(b) (MAJ-2): a replayed round contributes no span; the spans come from the ledger, so a stopped
    and resumed stage gives the spans (and the A1 site counts) of the uninterrupted stage. Kills A20 and A34."""
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path)
    hx.behaviour = _clocked(hx)
    a, b = tmp_path / "uninterrupted", tmp_path / "resumed"
    hx.run("text", "--settings", "A1_sites", "--max-calls", "32", "--out", str(a))
    ra = json.loads((a / "text" / "results.json").read_text(encoding="utf-8"))["settings"]["A1_sites"]
    monkeypatch.setenv(VAR, clean_env)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16", "--out", str(b))
    monkeypatch.setenv(VAR, clean_env)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16", "--out", str(b))
    rb = json.loads((b / "text" / "results.json").read_text(encoding="utf-8"))["settings"]["A1_sites"]
    assert ra["tail_span_ms"] == [3000.0, 3000.0]
    assert rb["tail_span_ms"] == ra["tail_span_ms"]
    assert {k: v["n"] for k, v in rb["sites"].items()} == {k: v["n"] for k, v in ra["sites"].items()}
    assert ra["sites"]["classify"]["n"] == 2
    tails = [x for x in hx_lines(b) if x.get("state") == "tail"]
    assert len(tails) == 2


def hx_lines(out):
    p = out / "text" / "spend.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_r81_timed_out_tail_leg_is_infinite_and_counted(hx):
    """F-4 (c): a timed-out tail leg makes that round's span +infinity, and the proposal line prints the number
    of censored samples."""
    hx.behaviour = lambda kw, n: _conn_exc(timeout=True) if n == 11 else _msg()
    hx.run("text", "--settings", "A1_sites", "--max-calls", "32")
    a1 = hx.results("text")["settings"]["A1_sites"]
    assert a1["tail_span_ms"][0] == math.inf and len(a1["tail_span_ms"]) == 2
    assert math.isfinite(a1["tail_span_ms"][1])
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- ANTHROPIC_TAIL_RESERVE_SECONDS")
    assert "n = 2" in line and "censored 1" in line


def test_r82_report_reads_the_current_knob_values(hx, monkeypatch):
    """F-4 (d): the report prints the CURRENT knob values read from the router, never its own literals."""
    router = _router()
    monkeypatch.setattr(router, "classify_timeout", lambda base: 7.5)
    monkeypatch.setattr(router, "vision_timeout", lambda: 33.0)
    monkeypatch.setattr(router, "tail_reserve_seconds_for_request", lambda: 9.0)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    assert "- ANTHROPIC_CLASSIFY_LLM_TIMEOUT: current 7.5," in rep
    assert "- ANTHROPIC_VISION_TIMEOUT_SECONDS: current 33.0," in rep
    assert "- ANTHROPIC_TAIL_RESERVE_SECONDS: current 9.0," in rep


def _line(rep, prefix):
    found = [x for x in rep.splitlines() if x.startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]


def _round_of(rec):
    return rec["case_id"].split(":")[0]


def _a1_costs(lines):
    per = {}
    for x in lines:
        if x.get("state") == "done" and x["setting"] == "A1_sites":
            per.setdefault(_round_of(x), []).append(x)
    return per


def test_r83_cost_per_synthetic_compare(hx):
    """F-5 (a): the cost per synthetic compare = the booked usd of an A1 round's calls from the ledger;
    nearest-rank p50 / p95 over the rounds that completed every call; n printed."""
    hx.behaviour = lambda kw, n: _msg(inp=100 if n <= 16 else 5000, out=20 if n <= 16 else 400)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "40")
    per = _a1_costs(hx.ledger("text"))
    assert sorted(per) == ["r00", "r01", "r02"] and len(per["r02"]) == 8
    c0 = sum(x["usd"] for x in per["r00"])
    c1 = sum(x["usd"] for x in per["r01"])
    assert c1 > c0 > 0
    cost = hx.results("text")["settings"]["A1_sites"].get("cost_per_compare")
    assert isinstance(cost, dict) and cost.get("n") == 2
    assert cost["p50_usd"] == pytest.approx(c0, abs=1e-9) and cost["p95_usd"] == pytest.approx(c1, abs=1e-9)
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- Cost per synthetic compare")
    assert "n = 2" in line and ("%.6f" % c0) in line and ("%.6f" % c1) in line


def test_r84_compares_per_day_under_the_code_default_cap(hx):
    """F-5 (b): compares per day = floor(cap / p95 cost) and floor(cap / p50 cost); the cap is the breaker's code
    default (its pure bound function with the knob unset), labelled so, with the formula printed."""
    from app.services import llm_spend_breaker as sb
    cap = sb.cap_usd(sb.LANE_LIVE)
    assert cap == sb.DEFAULT_CAPS_USD[sb.LANE_LIVE]
    hx.behaviour = lambda kw, n: _msg(inp=100 if n <= 16 else 5000, out=20 if n <= 16 else 400)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "40")
    cost = hx.results("text")["settings"]["A1_sites"].get("cost_per_compare")
    assert isinstance(cost, dict) and cost.get("p95_usd")
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- Compares per day")
    assert "code default, not the production value" in line
    assert "floor(cap / p95)" in line and "floor(cap / p50)" in line
    assert ("cap %s USD" % cap) in line
    assert ("= %d" % math.floor(cap / cost["p95_usd"])) in line
    assert ("= %d" % math.floor(cap / cost["p50_usd"])) in line


def test_r85_cache_read_share(hx):
    """F-5 (c): the cache_read share = cache-read input tokens / all input tokens (uncached + cache creation +
    cache read), per A1 site and pooled, from the ledger."""
    hx.behaviour = lambda kw, n: _msg(inp=100, cache_read=300 if n == 1 else 0)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    share = hx.results("text")["settings"]["A1_sites"].get("cache_read_share")
    assert isinstance(share, dict)
    assert share["pooled"] == pytest.approx(300.0 / 1900.0, abs=1e-9)
    assert share["sites"]["classify"] == pytest.approx(0.75, abs=1e-9)
    assert share["sites"]["parse"] == 0.0 and share["sites"]["specs"] == 0.0
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- cache_read share")
    assert "pooled 0.157894737" in line and "classify 0.75" in line


def _a4_groups():
    names = _fixture("fragrance_names.json")
    rows = []
    for i in range(100):
        a, b = names[i], names[(i + 1) % 100]
        rows.append({"ar": "ar" in (a["lang"], b["lang"]),
                     "sensitive": "sensitive" in (a["group"], b["group"])})
    return rows


def test_r86_sensitive_subset_of_a4(hx):
    """F-5 (d): the sensitive-looking subset of A4 (a case is in it when either name's fixture group is
    'sensitive'): n and refusals, reported beside the Arabic clause."""
    groups = _a4_groups()
    sens = [i for i, g in enumerate(groups) if g["sensitive"]]
    refuse = {sens[0], sens[3], 5}
    hx.behaviour = lambda kw, n: _msg(stop="refusal") if (n - 1) in refuse else _msg()
    hx.run("text", "--settings", "A4_refusal_names")
    a4 = hx.results("text")["settings"]["A4_refusal_names"]
    assert (a4.get("n_sensitive"), a4.get("refusals_sensitive")) == (len(sens), 2)
    assert (a4["n"], a4["refusals"]) == (100, 3)
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- A4 refusals")
    assert ("sensitive-looking names n = %d, refusals = 2" % len(sens)) in line
    assert ("Arabic-script names n = %d" % sum(1 for g in groups if g["ar"])) in line


def _report_cells(path):
    cells = {}
    for x in path.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in x.split("|")]
        if len(parts) >= 5 and parts[1] in ("TEXT", "VERDICT", "SONNET_ESCALATION", "CRITIC", "MODERATION",
                                            "VISION", "WEB_SEARCH"):
            cells[parts[1]] = (parts[2], parts[3])
    return cells


def _mod_answer(flagged):
    return json.dumps({"flagged": flagged, "category": "harassment" if flagged else "none", "uncertain": False})


def _decision_run(mod, monkeypatch, tmp_path, fail):
    """F-6: drive text (A1, A3, A4, A6), moderation and vision with the suite's fake client into one ledger
    folder, then the report. Create order (text): 1-320 A1 (16 a round), 321-340 A3, 341-440 A4, 441-560 A6
    (rep 0 cases 0-59, then rep 1)."""
    gold = [c["gold_winner_index"] for c in _fixture("verdict_gold.json")]
    cases = _fixture("moderation_parity.json")
    benign = [i for i, c in enumerate(cases) if c["expected_flagged"] is False]
    hx = Harness(mod, monkeypatch, tmp_path)

    def text(kw, n):
        if n <= 320:
            r, k = (n - 1) // 16, (n - 1) % 16 + 1
            if k == 1:
                hx.clock[0] += 2.0
            if k == 9:
                hx.clock[0] += 0.1 * (r + 1)
            if fail and k == 2 and r < 3:
                return _msg("not json")
            if fail and k == 7 and r == 0:
                return _status_exc(400)
            if fail and k == 16 and r == 3:
                return _conn_exc(timeout=True)
            if not fail and k == 11 and r < 3:
                return _msg(stop="max_tokens")
            return _msg()
        if n <= 340:
            return _status_exc(500) if fail and n == 325 else _msg()
        if n <= 440:
            i = n - 341
            return _msg(stop="refusal") if i in ((5, 49, 85) if fail else (5,)) else _msg()
        k = n - 441
        rep, idx = k // 60, k % 60
        wi = gold[idx]
        if fail and rep == 1 and idx < 10:
            wi = 1 - wi
        return _msg(json.dumps({"winner_index": wi}))

    hx.behaviour = text
    hx.run("text", "--settings", "A1_sites,A3_sonnet_between_tools,A4_refusal_names,A6_verdict_eval")

    def moderation(kw, n):
        i = n - 1
        if fail and i in benign[:2]:
            return _msg(stop="refusal")
        if fail and 10 <= i < 20:
            hx.clock[0] += 4.0
        return _msg(_mod_answer(cases[i]["expected_flagged"]))

    hx.behaviour = moderation
    monkeypatch.setenv(VAR, _make_canary())
    hx.run("moderation")
    hit = json.dumps({"products": [{"brand": "Dior", "name": "Sauvage"}]})
    miss = json.dumps({"products": [{"brand": "Dior", "name": "Bleu"}]})
    hx.behaviour = lambda kw, n: _msg(miss if fail and n in (5, 6) else hit)
    monkeypatch.setenv(VAR, _make_canary())
    hx.run("vision", "--set", str(_png_set(tmp_path / "photos", 3)))
    assert hx.run("report") == 0
    return hx


def test_r87_decision_path_pass(monkeypatch, tmp_path, clean_env):
    """F-6 (MAJ-1), the passing ledger: every metric a bar reads, by value, from a stage run; the verdict cell of
    every role parsed from REPORT.md; the proposals from the ledger. Kills A03, A26, A35 (with R88), A36, A37."""
    mod = _mod()
    hx = _decision_run(mod, monkeypatch, tmp_path, fail=False)
    text = hx.results("text")["settings"]
    sites = text["A1_sites"]["sites"]
    assert sites["verdict"]["max_tokens_hits"] == 3
    assert sum(v["max_tokens_hits"] for k, v in sites.items() if k != "verdict") == 0
    assert (sites["parse"]["json_n"], sites["parse"]["json_valid"]) == (20, 20)
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["schema_accepted"]) == (40, 40)
    assert text["A4_refusal_names"]["refusals"] == 1 and text["A4_refusal_names"]["refusals_arabic"] == 0
    assert text["A6_verdict_eval"]["agreement"] == 1.0 and text["A6_verdict_eval"]["mismatches"] == 0
    assert hx.results("moderation")["settings"]["M1_parity"]["fail_closed"] == 0
    cells = _report_cells(hx.out / "REPORT.md")
    assert cells == {"TEXT": ("GO", "-"), "VERDICT": ("GO", "-"), "SONNET_ESCALATION": ("GO", "-"),
                     "CRITIC": ("NOT RUN", "-"), "MODERATION": ("GO", "-"), "VISION": ("GO", "-"),
                     "WEB_SEARCH": ("NOT RUN", "-")}, cells
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    assert "- ANTHROPIC_CLASSIFY_LLM_TIMEOUT: current 4.0, proposed 2.5 " in rep
    assert "- ANTHROPIC_TAIL_RESERVE_SECONDS: current 6.5, proposed 2.5 " in rep
    assert ("VISION hit rate = hits / n_scored: successful calls only (a failed call is not scored).") in rep
    assert ("A6 mismatch rate = mismatches / n_scored: successful calls whose winner_index parsed only.") in rep


def test_r88_decision_path_fail(monkeypatch, tmp_path, clean_env):
    """F-6 (MAJ-1), the failing ledger: each role's bar crossed by a scripted fake; the metrics by value and the
    verdict cell of every role. Kills A01, A02, A05, A06, A24, A27, A28, A35."""
    mod = _mod()
    hx = _decision_run(mod, monkeypatch, tmp_path, fail=True)
    text = hx.results("text")["settings"]
    sites = text["A1_sites"]["sites"]
    assert (sites["parse"]["json_n"], sites["parse"]["json_valid"]) == (20, 17)
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["schema_accepted"]) == (40, 39)
    assert sites["url_extract"]["timeouts"] == 1
    a4 = text["A4_refusal_names"]
    n_ar = sum(1 for g in _a4_groups() if g["ar"])
    assert (a4["n"], a4["refusals"], a4["n_arabic"], a4["refusals_arabic"]) == (100, 3, n_ar, 1)
    a6 = text["A6_verdict_eval"]
    assert (a6["n_scored"], a6["mismatches"]) == (120, 10)
    assert a6["agreement"] == pytest.approx(50.0 / 60.0)
    assert (text["A3_sonnet_between_tools"]["accepted"], text["A3_sonnet_between_tools"]["json_valid"]) == (19, 19)
    m1 = hx.results("moderation")["settings"]["M1_parity"]
    assert (m1["fail_closed"], m1["p95_s"], m1["false_positives"]) == (2, 4.0, 0)
    v = hx.results("vision")["settings"]
    assert v["V2_haiku_vision_v2"]["hit_rate"] == pytest.approx(1.0 / 3.0)
    cells = _report_cells(hx.out / "REPORT.md")
    assert cells["TEXT"] == ("NO-GO", "json_valid_site_min, schema_accept_min, refusals_a4_max, "
                                      "refusals_a4_arabic_max, timeouts_max"), cells["TEXT"]
    assert cells["VERDICT"] == ("NO-GO", "a6_agreement_min")
    assert cells["SONNET_ESCALATION"] == ("NO-GO", "accepted_min")
    assert cells["MODERATION"] == ("NO-GO", "fail_closed_max, p95_s")
    assert cells["VISION"] == ("NO-GO", "haiku_hit_min, haiku_minus_sonnet_min")
    assert cells["CRITIC"][0] == "NOT RUN" and cells["WEB_SEARCH"][0] == "NOT RUN"


def test_r89_variable_removed_in_every_mode_before_a_child(hx, monkeypatch, canary):
    """F-7 (a) (security m3): the credential variable leaves the process environment at start in EVERY mode,
    the dry run included, before any child process is spawned: the git child of a dry run does not inherit it."""
    mod = hx.mod
    sp = _attr(mod, "subprocess")
    seen = []

    class _R:
        returncode = 0
        stdout = "ab" * 20

    def rec(*a, **k):
        env = k.get("env")
        seen.append(VAR in (env if env is not None else os.environ))
        return _R()

    monkeypatch.setattr(sp, "run", rec)
    assert hx.run("text", "--dry-run", "--settings", "A0_capabilities") == 0
    assert seen and not any(seen) and VAR not in os.environ
    for argv in (("report",), ("vision",), ("web_search",)):
        monkeypatch.setenv(VAR, canary)
        assert hx.run(*argv) == 0
        assert VAR not in os.environ, argv
    assert hx.key_reads == []


def test_r90_unit_ceiling_clause_of_the_reservation():
    """F-7 (b) (security m6, mutant S06): a reservation that fits the stage cap but crosses the unit ceiling is
    refused."""
    mod = _mod()
    b = mod.Budget(4.0, 0.0, 14.0)
    assert b.reserve(1.5) is False and b.reserved == 0.0
    assert b.reserve(0.5) is True and b.reserve(0.6) is False
    assert b.reserved == pytest.approx(0.5)


def test_r91_completed_nontransient_call_never_resent(monkeypatch, tmp_path, clean_env):
    """F-7 (c) (correctness m2, mutant A15): on a resume a call completed by a non-transient error (a 400) is
    never sent again."""
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path, behaviour=lambda kw, n: _status_exc(400) if n == 1 else _msg())
    hx.run("text", "--settings", "A1_sites", "--max-calls", "1")
    first = _done(hx.ledger("text"))
    assert len(first) == 1 and first[0]["error_class"] == "BadRequestError"
    hx.behaviour = lambda kw, n: _msg()
    monkeypatch.setenv(VAR, clean_env)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    lines = hx.ledger("text")
    assert len([x for x in _intents(lines) if x["call_id"] == first[0]["call_id"]]) == 1
    assert [x["site"] for x in _done(lines)[1:]] == ["parse", "specs"]


@pytest.mark.parametrize("value", ["0", "-5", "0.2"])
def test_r92_retry_after_floor(monkeypatch, tmp_path, clean_env, value):
    """F-7 (c) (correctness m3, mutant A32): a retry-after of 0, below 1 or negative waits the 1 s floor."""
    mod = _mod()
    hx = Harness(mod, monkeypatch, tmp_path,
                 behaviour=lambda kw, n: _status_exc(429, headers={"retry-after": value}) if n == 1 else _msg())
    hx.run("text", "--settings", "A1_sites", "--max-calls", "2")
    assert hx.sleeps[:1] == [1]


# --------------------------------------------------------------------------
# MERGE round rows (RULINGS_MERGE_S81_07 M-4; sanctioned amendments, listed in
# the MERGE section of the amendments file)
# --------------------------------------------------------------------------
def test_r93_loopback_is_a_parsed_address():
    """M-4 m5: a host counts as loopback only when it is the literal name localhost or parses as an IP address
    that is a loopback address (127.0.0.0/8 or ::1). A NAME that merely starts with '127.' is any other host
    name: refused by the guard in live mode and in loopback-only mode, as str and as bytes."""
    import socket
    mod = _mod()
    ha = mod.host_allowed
    for host in ("127.evil.example", b"127.evil.example", "127.0.0.1.evil.example", "127.example"):
        assert ha(host, 443) is False and ha(host, 9) is False, host
    for host in ("127.0.0.1", b"127.0.0.1", "127.1.2.3", "::1", b"::1", "localhost", b"LOCALHOST"):
        assert ha(host, 9) is True, host
    seen = []
    real = socket.getaddrinfo
    socket.getaddrinfo = lambda *a, **k: seen.append(a[0]) or []
    try:
        for live in (True, False):
            seen.clear()
            ctx, state = _GuardCtx(), {"restore": []}
            mod._install_host_guard(ctx, state, live)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                for host in ("127.evil.example", b"127.evil.example"):
                    assert _try(socket.getaddrinfo, host, 443) == "host_refused", (live, host)
                assert seen == [], live
                assert _try(s.connect, ("127.evil.example", 443)) == "host_refused", live
                for host in ("127.0.0.1", "127.1.2.3", "::1", "localhost"):
                    assert _try(socket.getaddrinfo, host, 443) == "passed", (live, host)
                assert seen == ["127.0.0.1", "127.1.2.3", "::1", "localhost"], live
                assert ctx.hosts_refused.count("127.evil.example") == 3, (live, ctx.hosts_refused)
            finally:
                s.close()
                for fn in reversed(state["restore"]):
                    fn()
    finally:
        socket.getaddrinfo = real


def test_r94_unmatched_intent_counts_in_its_round_cost(hx, monkeypatch, canary):
    """M-4 m1 (mutant N11; F-5 (a)): on a hand-computed ledger, a round that holds an unmatched intent (a killed
    call, re-sent and completed as attempt 2) counts that intent's worst case in the round's cost."""
    hx.behaviour = lambda kw, n: _msg(inp=100, out=20)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    p = hx.out / "text" / "spend.jsonl"
    lines = hx_lines(hx.out)
    first_done = [x for x in lines if x.get("state") == "done"][0]
    assert first_done["site"] == "classify" and first_done["ok"] is True
    cid = first_done["call_id"]
    killed_worst = 0.25
    rewritten = []
    for x in lines:
        if x.get("call_id") == cid and x.get("state") in ("sent", "done"):
            if x["state"] == "sent":
                killed = dict(x)
                killed["attempt"] = 1
                killed["worst_usd"] = killed_worst
                rewritten.append(killed)
            x = dict(x)
            x["attempt"] = 2
        rewritten.append(x)
    p.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rewritten), encoding="utf-8",
                 newline="\n")
    lines = hx_lines(hx.out)
    r00 = [x for x in lines if x.get("state") == "done" and x["setting"] == "A1_sites"]
    assert len(r00) == 16 and {_round_of(x) for x in r00} == {"r00"}
    by_hand = sum(x["usd"] for x in r00) + killed_worst
    hx.behaviour = lambda kw, n: _msg(inp=100, out=20)
    monkeypatch.setenv(VAR, canary)
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    lines = hx_lines(hx.out)
    assert [x for x in _intents(lines) if x["call_id"] == cid and x["attempt"] == 1] != []
    r01 = [x for x in lines if x.get("state") == "done" and _round_of(x) == "r01"]
    assert len(r01) == 16
    c01 = sum(x["usd"] for x in r01)
    assert by_hand > c01 > 0
    cost = hx.results("text")["settings"]["A1_sites"].get("cost_per_compare")
    assert isinstance(cost, dict) and cost.get("n") == 2
    assert cost["p95_usd"] == pytest.approx(by_hand, abs=1e-9)
    assert cost["p50_usd"] == pytest.approx(c01, abs=1e-9)


def test_r95_failed_tail_leg_excludes_its_round(hx):
    """M-4 m6: a round gives a tail span only when its three tail legs all SUCCEEDED; a timed-out leg censors
    the round (+infinity, R81); a leg that failed in any other way (an error status, a connection error)
    excludes the round from the percentiles, and the proposal line prints the number of such rounds beside the
    censored count."""
    fail = {9: _status_exc(500), 26: _status_exc(400), 43: _conn_exc()}
    hx.behaviour = _clocked(hx, extra=lambda kw, n: fail[n] if n in fail else _msg())
    hx.run("text", "--settings", "A1_sites", "--max-calls", "64")
    a1 = hx.results("text")["settings"]["A1_sites"]
    assert len(a1["tail_span_ms"]) == 1 and math.isfinite(a1["tail_span_ms"][0]), a1["tail_span_ms"]
    assert a1["tail_span_ms"] == [3000.0]
    assert a1.get("tail_n_censored") == 0 and a1.get("tail_n_failed") == 3
    tails = [x for x in hx_lines(hx.out) if x.get("state") == "tail"]
    assert [(x["round"], x["span_ms"], x["censored"]) for x in tails] == [
        ("r00", None, False), ("r01", None, False), ("r02", None, False), ("r03", 3000.0, False)]
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    line = _line(rep, "- ANTHROPIC_TAIL_RESERVE_SECONDS")
    assert "n = 1, censored 0, rounds excluded for a failed tail leg 3" in line


def test_r96_knob_values_labelled_code_default(hx):
    """M-4 m3: in a real run the three knob values read from the router are the CODE DEFAULTS (every
    ANTHROPIC_* name refuses the start, so a production override is not visible): the report lines, and the
    CLAUDE.md block, say 'code default' (at the END of each knob line: R82 and R87 pin the line heads). R82
    pins that the value is READ from the router."""
    hx.run("text", "--settings", "A1_sites", "--max-calls", "16")
    assert hx.run("report") == 0
    rep = (hx.out / "REPORT.md").read_text(encoding="utf-8")
    label = ("); current = the code default (a production override is not visible to this run: every "
             "ANTHROPIC_* name refuses the start)")
    for prefix in ("- ANTHROPIC_CLASSIFY_LLM_TIMEOUT", "- ANTHROPIC_VISION_TIMEOUT_SECONDS",
                   "- ANTHROPIC_TAIL_RESERVE_SECONDS"):
        line = _line(rep, prefix)
        assert line.endswith(label), line
        assert line.index(": current ") < line.index(", proposed ") < line.index(label)
    block = " ".join(_claude_md_s07_block())
    assert "CURRENT values" not in block
    assert "code-default values of `ANTHROPIC_CLASSIFY_LLM_TIMEOUT`" in block
    assert "a production override is not visible to this run" in block

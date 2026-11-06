"""S81-22 COMPARE-RUNS (ENABLE_COMPARE_RUN_LEDGER) -- RED and PIN rows for the request path
and migration 048.

Spec .qa-s80/S81-22_UNIT_SPEC.md section 5.1 as amended by RULINGS_S81_22 (R-S22-23..60;
the brief's R-S22-1..22 beneath). Base 18cb9e04. Every RED row fails at base on an
AssertionError only: the unit's module and symbols are resolved inside the test body through
find_spec / getattr helpers and ASSERTED, files through Path.exists asserts. Every PIN row is
green at base and runs with the FULL companion configuration (B1 ON, the echo ON, V2 ON, D05
ON, the request-context headers ON with a synthetic pepper through monkeypatch, the ledger v2
ON, metering ON, W4-13 both states) plus recorders on fire_and_forget / run_db / the admin
client and RAISING stubs on build_run_row / _insert / _query_hmac (R-S22-42), installed only
when the module exists.
Rulings applied beyond the spec rows: R-S22-24 (query_hmac = HMAC(pepper, "pair:" + the pair
identity text) for EVERY input type, R08 / R09 re-cut), R-S22-27 (llm_calls through
llm_pricing.OTEL_GENAI_ATTRIBUTES + the unmapped ledger names, R15), R-S22-37 (RUN_COLUMNS /
LLM_CALL_FIELDS; R26 narrowed to the gitleaks shape), R-S22-39 (the camera extra_records; the
url row llm_calls NULL), R-S22-40 (data_coverage smallint), R-S22-43 (R03 skips a docstring),
R-S22-53 (the prose drop on a personalised body), R-S22-54 (the refusal_reason CHECK),
R-S22-23 (the alias-free hook at chunk index 2).
Hermetic: no network, no .env, no credential; synthetic ids (s22-<node>); every 64-hex value
is built at run time. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import asyncio
import base64
import contextvars
import copy
import hashlib
import hmac
import importlib
import importlib.util
import json
import logging
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.main as app_main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from app.api import image_routes, text_routes, url_routes
from app.services import llm_pricing as lp
from app.services import openai_pricing
from app.services import result_gate as rg
from app.utils import request_context as rc
from tests import test_migration_043_delete_user_cascade as t043
from tests import test_s81_s20_result_gate as s20

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"
FIX = ROOT / "tests" / "fixtures"
MOD = "app.services.compare_runs"
FLAG = "ENABLE_COMPARE_RUN_LEDGER"
HDRS = "ENABLE_REQUEST_CONTEXT_HEADERS"
V2LEDGER = "ENABLE_LLM_LEDGER_V2"
PEPPER = rc.PEPPER_ENV
RUN_COLUMNS_WANT = (
    "comparison_id", "consent_version", "compare_request_id", "device_key", "input_type",
    "category", "product_categories", "refusal_reason", "query_hmac", "kb_product_ids",
    "sources_used", "cache_hits", "llm_calls", "stage_timings", "result_status",
    "identity_confidence", "data_coverage", "winner_supported", "field_status",
    "partial_stage", "evidence",
)
INPUT_TYPES_WANT = ("text", "text_stream", "camera", "url")
TRUTHY_TABLE = [(None, False), ("", False), ("false", False), ("0", False), ("off", False),
                ("garbage", False), ("true", True), (" TRUE ", True), ("1", True), ("yes", True),
                ("On", True)]
OFF_VALUES = [None, "false", "0", "off", ""]
CLEAR = tuple(sorted(set(s20.CLEAR + (FLAG, HDRS, V2LEDGER, PEPPER))))
# The 043 blobs at base 18cb9e04 (git rev-parse 18cb9e04:<path>), recorded at RED as base64 of the
# 20-byte ids (the added-line sweep reads hex digit runs as phone-shaped).
BASE_BLOBS = {
    "migrations/043_delete_user_cascade_full_erasure.sql": "a1yRUTmyBm1zTUMAS+yDyLLsa5I=",
    "migrations/rollback/043_delete_user_cascade_full_erasure.sql": "k1HhiCKWKI4FU8JCzpqqsiQYhCk=",
}
# sha256 over request_context.device_key of three synthetic fingerprints under PEPPER_VALUE_SYN at
# base, as base64 of the 32-byte digest.
PEPPER_VALUE_SYN = "s22-synthetic-pepper"
SYN_DEVICE_DIGEST_B64 = "ZMMZkTdIBJ6c7FQHcKYxevr+vie/eIacWp4bi7I3RKw="


def _hex(seed):
    return hashlib.sha256(("s22-" + seed).encode("ascii")).hexdigest()


def _cr():
    spec = importlib.util.find_spec(MOD)
    assert spec is not None, "app/services/compare_runs.py is missing (S81-22 not built)"
    return importlib.import_module(MOD)


def _sym(name):
    mod = _cr()
    assert hasattr(mod, name), "compare_runs.%s is missing" % name
    return getattr(mod, name)


def _maybe_cr():
    return importlib.import_module(MOD) if importlib.util.find_spec(MOD) is not None else None


def _src(rel):
    p = ROOT / rel
    assert p.exists(), "%s is missing" % rel
    return p.read_text(encoding="utf-8")


def _fixture(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def body_el():
    return _fixture("comparison_baseline_d2.json")


def body_frag():
    return _fixture("comparison_baseline_d2_post_bucket_a__fragrances.json")


def _sentinel(slot):
    return "S22SENT" + slot.upper() + "X" + hashlib.sha256(slot.encode()).hexdigest()[:6]


def personal_body():
    b = body_frag()
    b["user_id"] = _sentinel("uid")
    b["access_token"] = _sentinel("tok")
    b["query"] = _sentinel("query")
    b["metadata"]["query"] = _sentinel("mquery")
    b["metadata"]["sentry_event_id"] = _sentinel("sentry")
    b["metadata"]["prompt"] = _sentinel("prompt")
    for i, p in enumerate(b["products"]):
        p["query"] = _sentinel("pq%d" % i)
        p["price"]["url"] = "https://www.tomford.com/x?q=" + _sentinel("url%d" % i)
        p.setdefault("rating_source", {})["url"] = "https://r.example.test/?q=" + _sentinel("rs%d" % i)
    b["personalization"] = {"personalized": False, "personalized_insights": [_sentinel("ins")],
                            "factors": [_sentinel("fac")]}
    b["personalization_factors"] = [_sentinel("pf")]
    b["cohort_profile"] = {"age_group": _sentinel("cohort")}
    b["preferences"] = {"budget": _sentinel("pref")}
    b["behavior_profile"] = {"affinity": _sentinel("beh")}
    return b


SENTINEL_SLOTS = ("uid", "tok", "query", "mquery", "sentry", "prompt", "pq0", "pq1", "url0", "url1",
                  "rs0", "rs1", "ins", "fac", "pf", "cohort", "pref", "beh")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    s20.scs._DEBUG_STAGE_TIMINGS = None
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(s20.app.dependency_overrides)
    try:
        yield
    finally:
        limiter.enabled = prior
        s20.scs._DEBUG_STAGE_TIMINGS = None
        s20.app.dependency_overrides.clear()
        s20.app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return s20.TestClient(s20.app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {"id": ("s22-" + request.node.name)[:120], "email": "s22@example.test",
            "access_token": "s22-synthetic"}
    s20.app.dependency_overrides[s20.get_optional_user] = lambda: user
    s20.app.dependency_overrides[s20.get_current_user] = lambda: user
    return user


def _headers():
    return {"X-Device-Fingerprint": _hex("fp"), "X-AI-Consent-Version": "3",
            "X-Compare-Request-Id": str(uuid.UUID(_hex("rid")[:32], version=4))}


def _full(monkeypatch, truth=False):
    s20._full_config(monkeypatch, truth=truth)
    monkeypatch.setenv(HDRS, "true")
    monkeypatch.setenv(V2LEDGER, "true")
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)


class Rec:
    """fire_and_forget / run_db / admin-client recorders on the compare_runs module (closes
    every unscheduled coroutine, R-S22-49) and, under `raising`, RAISING stubs on
    build_run_row / _insert / _query_hmac (R-S22-42). Installed only when the module exists."""

    def __init__(self, monkeypatch, raising=False):
        self.labels = []
        self.rows = []
        self.db = 0
        self.admin = 0
        self.calls = []
        cr = _maybe_cr()
        self.cr = cr
        if cr is None:
            return

        def _ff(coro, label):
            self.labels.append(label)
            frame = getattr(coro, "cr_frame", None)
            if frame is not None and "row" in frame.f_locals:
                self.rows.append(frame.f_locals["row"])
            coro.close()
            return None

        monkeypatch.setattr(cr, "_async_utils", SimpleNamespace(fire_and_forget=_ff))

        async def _run_db(call):
            self.db += 1
            return None

        monkeypatch.setattr(cr, "_db_offload", SimpleNamespace(run_db=_run_db))
        from app.services import database_service

        def _admin():
            self.admin += 1
            raise AssertionError("admin client read")

        monkeypatch.setattr(database_service, "get_admin_supabase_client", _admin)
        real = cr.record_compare_run

        def _rec(result, input_type, **kw):
            self.calls.append((input_type, dict(kw)))
            return real(result, input_type, **kw)

        monkeypatch.setattr(cr, "record_compare_run", _rec)
        if raising:
            def _boom(*_a, **_k):
                raise AssertionError("compare_runs symbol reached with the flag OFF")

            for name in ("build_run_row", "_insert", "_query_hmac"):
                monkeypatch.setattr(cr, name, _boom)


def _row(body, input_type="text", **kw):
    return _sym("build_run_row")(copy.deepcopy(body), input_type, **kw)


def _in_ctx(fn):
    return contextvars.copy_context().run(fn)


# =============================================================== the module (R01-R19, R25-R27)

def test_r01_module_and_constants():
    cr = _cr()
    assert _sym("FLAG") == FLAG
    assert _sym("COMPARE_RUN_RETENTION_DAYS") == 365
    assert _sym("EVIDENCE_MAX_BYTES") == 65536
    assert _sym("LLM_CALLS_MAX") == 32
    assert tuple(_sym("INPUT_TYPES")) == INPUT_TYPES_WANT
    assert tuple(_sym("RUN_COLUMNS")) == RUN_COLUMNS_WANT and len(RUN_COLUMNS_WANT) == 21
    assert _sym("TABLE") == "compare_runs"
    assert _sym("LABEL_PREFIX") == "compare_runs.insert."
    assert _sym("LOG_SKIPPED") == "[COMPARE_RUNS] insert skipped reason=%s"
    assert _sym("QUERY_HMAC_DOMAIN") == "pair:"
    assert not hasattr(cr, "ROW_KEYS") and not hasattr(cr, "LLM_CALL_KEYS")


@pytest.mark.parametrize("raw,want", TRUTHY_TABLE)
def test_r02_flag_reader_idiom(monkeypatch, raw, want):
    fn = _sym("compare_run_ledger_enabled")
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert fn() is want
    monkeypatch.setenv(FLAG, "false" if want else "true")
    assert fn() is (not want)


def _first_stmt(fn_node):
    body = list(fn_node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body[0]


def test_r03_flag_is_first_statement():
    tree = ast.parse(_src("app/services/compare_runs.py"))
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "record_compare_run"]
    assert len(fns) == 1, "record_compare_run is missing"
    first = _first_stmt(fns[0])
    assert isinstance(first, ast.If), ast.dump(first)
    t = first.test
    assert isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not), ast.dump(t)
    assert isinstance(t.operand, ast.Call) and isinstance(t.operand.func, ast.Name)
    assert t.operand.func.id == "compare_run_ledger_enabled" and not t.operand.args
    assert len(first.body) == 1 and isinstance(first.body[0], ast.Return) and first.body[0].value is None
    assert not first.orelse


@pytest.mark.parametrize("fixture", ["el", "frag"])
@pytest.mark.parametrize("itype", INPUT_TYPES_WANT)
def test_r04_builder_closed_keys_on_real_fixtures(fixture, itype):
    body = body_el() if fixture == "el" else body_frag()
    row = _row(body, itype)
    assert isinstance(row, dict)
    assert tuple(row) == RUN_COLUMNS_WANT
    assert row["input_type"] == itype
    text = json.dumps(row, ensure_ascii=False, sort_keys=True)
    assert all(ord(c) < 128 for c in text)


def test_r05_builder_none_cases():
    build = _sym("build_run_row")
    assert build(None, "text") is None
    assert build(["x"], "text") is None
    b = body_frag()
    b["success"] = False
    assert build(b, "text") is None
    b["success"] = "true"
    assert build(b, "text") is None
    b["success"] = 1
    assert build(b, "text") is None
    assert build(body_frag(), "share") is None
    assert build(body_frag(), "TEXT") is None


def test_r06_assessment_columns_equal_result_gate():
    for body in (body_el(), body_frag()):
        a = rg.assess_result(copy.deepcopy(body), product_categories=rg.stamped_product_categories(body))
        row = _row(body)
        assert row["result_status"] == a["status"]
        assert row["identity_confidence"] == a["identity_confidence"]
        assert row["data_coverage"] == int(a["data_coverage"]) and type(row["data_coverage"]) is int
        assert 0 <= row["data_coverage"] <= 4
        assert row["winner_supported"] is (a["status"] == rg.STATUS_SUPPORTED)
    # the AUDITABLE count, never the literal one (a zero amount is literal-present, not showable)
    zero = body_frag()
    for p in zero["products"]:
        p["price"]["amount"] = 0.0
    az = rg.assess_result(copy.deepcopy(zero), product_categories=rg.stamped_product_categories(zero))
    assert az["data_coverage"] != az["data_coverage_literal"]
    assert _row(zero)["data_coverage"] == int(az["data_coverage"])
    ph = s20.body_v09()
    a = rg.assess_result(copy.deepcopy(ph), product_categories=rg.stamped_product_categories(ph))
    row = _row(ph)
    assert a["status"] == rg.STATUS_NEEDS_ID
    assert row["result_status"] == rg.STATUS_NEEDS_ID and row["winner_supported"] is False
    # winner_supported comes from the assessment, never from a body key
    b = copy.deepcopy(ph)
    b.setdefault("overview", {}).setdefault("winner", {})["supported"] = True
    b["metadata"]["result_status"] = rg.STATUS_SUPPORTED
    assert _row(b)["winner_supported"] is False and _row(b)["result_status"] == rg.STATUS_NEEDS_ID


def _bind(consent="3", fp=None, rid=None):
    hdrs = []
    if consent is not None:
        hdrs.append((rc.HEADER_CONSENT_VERSION, consent.encode("ascii")))
    if fp is not None:
        hdrs.append((rc.HEADER_DEVICE_FINGERPRINT, fp.encode("ascii")))
    if rid is not None:
        hdrs.append((rc.HEADER_COMPARE_REQUEST_ID, rid.encode("ascii")))
    rc.bind_from_headers(hdrs)


def test_r07_context_columns(monkeypatch):
    monkeypatch.setenv(HDRS, "true")
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)
    fp = _hex("fp")
    rid = str(uuid.UUID(_hex("rid")[:32], version=4))

    def bound(consent):
        _bind(consent, fp, rid)
        return _row(body_frag())

    row = _in_ctx(lambda: bound("3"))
    assert row["consent_version"] == 3 and type(row["consent_version"]) is int
    assert row["compare_request_id"] == rid
    assert row["device_key"] == rc.device_key(fp)
    assert re.fullmatch(r"[a-f0-9]{64}", row["device_key"])
    assert _in_ctx(lambda: bound("999"))["consent_version"] == 999
    unbound = _in_ctx(lambda: _row(body_frag()))
    assert (unbound["consent_version"], unbound["compare_request_id"], unbound["device_key"]) == (None, None, None)
    monkeypatch.setattr(rc, "consent_version", lambda: True)
    assert _in_ctx(lambda: _row(body_frag()))["consent_version"] is None


def _pair_mac(pepper, text):
    return hmac.new(pepper.strip().encode("utf-8"), ("pair:" + rg.norm(text)).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def test_r08_query_hmac_shape_and_domain(monkeypatch):
    qh = _sym("_query_hmac")
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)
    text = "Tom Ford Tobacco Vanille vs Dior Sauvage"
    h = qh(text)
    assert isinstance(h, str) and re.fullmatch(r"[a-f0-9]{64}", h)
    assert h == _pair_mac(PEPPER_VALUE_SYN, text)
    assert qh("  TOM FORD tobacco   vanille VS dior sauvage ") == h
    raw = hmac.new(PEPPER_VALUE_SYN.encode(), rg.norm(text).encode(), hashlib.sha256).hexdigest()
    assert h != raw and h != hashlib.sha256(text.encode()).hexdigest()
    fp = _hex("fp")
    assert qh(fp) != rc.device_key(fp)
    assert qh("") is None and qh("   ") is None and qh(None) is None
    monkeypatch.setenv(PEPPER, "s22-other-pepper")
    assert qh(text) != h
    monkeypatch.setenv(PEPPER, "   ")
    assert qh(text) is None
    monkeypatch.delenv(PEPPER)
    assert qh(text) is None


def test_r09_pair_hmac_every_input_type(monkeypatch):
    """R-S22-24: the pair identity text hashed for EVERY input type; the typed query never."""
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)
    pit = _sym("pair_identity_text")
    b = body_frag()
    want_text = " vs ".join(rg.identity_text(p.get("brand"), p.get("name")) for p in b["products"][:2])
    assert pit(b) == want_text
    hashes = set()
    for t in INPUT_TYPES_WANT:
        row = _row(b, t)
        assert row["query_hmac"] == _pair_mac(PEPPER_VALUE_SYN, want_text), t
        hashes.add(row["query_hmac"])
    assert len(hashes) == 1
    b2 = copy.deepcopy(b)
    b2["query"] = "something else entirely"
    b2["metadata"]["query"] = "another"
    assert _row(b2, "text")["query_hmac"] == _row(b, "text")["query_hmac"]
    sw = copy.deepcopy(b)
    sw["products"] = list(reversed(sw["products"]))
    assert pit(sw) != pit(b)
    assert _row(sw, "camera")["query_hmac"] != _row(b, "camera")["query_hmac"]
    one = copy.deepcopy(b)
    one["products"] = one["products"][:1]
    one.pop("overview", None)
    assert pit(one) == ""


@pytest.mark.parametrize("raw,want", [
    ("6F9619FF-8B86-D011-B42D-00C04FC964FF", "6f9619ff-8b86-d011-b42d-00c04fc964ff"),
    (None, None), ("", None), ("not-a-uuid", None), (12, None), (True, None)])
def test_r10_comparison_id_link(raw, want):
    b = body_frag()
    b["comparison_id"] = raw
    assert _row(b)["comparison_id"] == want


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


@pytest.mark.parametrize("itype", INPUT_TYPES_WANT)
def test_r11_deidentified_row(monkeypatch, itype):
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)
    row = _row(personal_body(), itype)
    text = json.dumps(row, sort_keys=True)
    for slot in SENTINEL_SLOTS:
        assert _sentinel(slot) not in text, slot
    assert "S22SENT" not in text
    assert "http" not in text and "?q=" not in text
    banned = {"user_id", "query", "url", "access_token", "personalization", "personalized_insights",
              "personalization_factors", "cohort_profile", "preferences", "behavior_profile"}
    assert not (set(_walk_keys(row)) & banned), set(_walk_keys(row)) & banned


def test_r12_evidence_shape():
    ev = _row(body_frag())["evidence"]
    assert set(ev) == {"v", "category", "products", "specs_comparison", "verdict", "scores",
                       "section_status", "truncated"}
    assert ev["v"] == 1 and ev["truncated"] is False and ev["category"] == "fragrances"
    assert len(ev["products"]) == 2
    for p in ev["products"]:
        assert set(p) == {"brand", "name", "variant", "category", "size", "concentration", "price",
                          "rating", "specs", "image"}
        assert set(p["price"]) == {"amount", "currency", "source_method", "as_of", "host", "estimated",
                                   "unavailable"}
        assert set(p["rating"]) == {"value", "count", "source"}
        assert isinstance(p["image"], bool)
    assert ev["products"][0]["price"]["host"] == "tomford.com"
    assert ev["products"][1]["price"]["host"] == "ssense.com"
    assert set(ev["verdict"]) == {"product_index", "name", "declaration", "reason", "key_tradeoff",
                                  "margin", "supported"}
    assert set(ev["scores"]) == {"overall", "scoring_method"}
    assert ev["section_status"] == rg.section_status(body_frag())


def test_r12b_prose_dropped_on_personalised_body():
    """R-S22-53: a personalised body drops the verdict prose; the structured fields stay."""
    plain = _row(body_frag())["evidence"]
    assert "prose_dropped" not in plain
    marks = [("metadata", "cohort_injected", True), (None, "personalized", True),
             ("scoring", "scoring_method", "behavioral"), ("scoring", "scoring_method", "cohort"),
             ("scoring", "scoring_method", "personalized"), ("personalization", "personalized", True)]
    for parent, key, value in marks:
        b = body_frag()
        b.setdefault("overview", {}).setdefault("winner", {}).update(
            {"reason": "a reason", "declaration": "a declaration", "key_tradeoff": "a tradeoff"})
        (b.setdefault(parent, {}) if parent else b)[key] = value
        ev = _row(b)["evidence"]
        assert ev.get("prose_dropped") == "personalized", (parent, key, value)
        assert ev["verdict"]["reason"] is None and ev["verdict"]["declaration"] is None
        assert ev["verdict"]["key_tradeoff"] is None
        assert ev["verdict"]["product_index"] == plain["verdict"]["product_index"]
        assert ev["verdict"]["supported"] == plain["verdict"]["supported"]


def _size(obj):
    return len(json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def test_r13_evidence_truncation_order():
    cap = 65536
    big = body_frag()
    for p in big["products"]:
        p["specs"] = {"k%03d" % i: "v" * 150 for i in range(40)}
    big["specs"]["specs_comparison"] = {"key_%02d" % i: ["x" * 290] * 10 for i in range(40)}
    big["overview"]["winner"]["reason"] = "short reason"
    ev = _row(big)["evidence"]
    assert ev.get("truncated") is True and _size(ev) <= cap
    assert "products" in ev and "verdict" in ev, sorted(ev)
    assert ev.get("specs_comparison", "absent") is None and all(p["specs"] is None for p in ev["products"])
    assert ev["verdict"]["reason"] == "short reason"
    # verdict text alone cannot overflow (600-char caps), so build an overflow through names x many keys
    huge = copy.deepcopy(big)
    ev2 = _row(huge)["evidence"]
    assert _size(ev2) <= cap
    build = _sym("build_run_row")
    cr = _cr()
    orig = cr.EVIDENCE_MAX_BYTES
    try:
        stage1 = _size(ev)
        cr.EVIDENCE_MAX_BYTES = stage1
        assert build(copy.deepcopy(big), "text")["evidence"]["verdict"]["reason"] == "short reason"
        cr.EVIDENCE_MAX_BYTES = stage1 - 1
        e3 = build(copy.deepcopy(big), "text")["evidence"]
        assert _size(e3) <= stage1 - 1
        assert e3.get("truncated") is True and e3["specs_comparison"] is None
        assert e3["verdict"]["reason"] is None and e3["verdict"]["declaration"] is None
        assert e3["verdict"]["key_tradeoff"] is None and "products" in e3
        cr.EVIDENCE_MAX_BYTES = 40
        assert build(copy.deepcopy(big), "text")["evidence"] == {"v": 1, "truncated": True}
    finally:
        cr.EVIDENCE_MAX_BYTES = orig


def test_r14_evidence_sizes_recorded():
    bodies = [body_el(), body_frag(), s20.body_sup(), s20._lane1("iphone15_vs_galaxys24")]
    for b in bodies:
        ev = _row(b)["evidence"]
        assert ev["truncated"] is False
        assert _size(ev) < 65536


def _otel_fields():
    m = lp.OTEL_GENAI_ATTRIBUTES
    return {m["provider"], m["model"], m["prompt_tokens"], m["completion_tokens"], m["stop_reason"],
            "role", "web_search_requests", "cost_usd", "latency_ms", "batch"}


@pytest.mark.parametrize("v2", [False, True])
def test_r15_llm_calls_otel_names_and_cap(monkeypatch, v2):
    if v2:
        monkeypatch.setenv(V2LEDGER, "true")
    assert set(_sym("LLM_CALL_FIELDS")) == _otel_fields()
    m = lp.OTEL_GENAI_ATTRIBUTES

    def bound_world():
        led = openai_pricing.start_openai_ledger()
        led.append({"model": "gpt-4o-mini", "prompt_tokens": 100, "completion_tokens": 20, "cached_tokens": 10})
        led.append({"model": "gpt-4o-mini", "prompt_tokens": 50, "completion_tokens": 5, "cached_tokens": 0})
        recs = lp.start_llm_ledger()
        recs.append(lp.anthropic_usage_record("claude-haiku-5-5", {"input_tokens": 30, "output_tokens": 7},
                                              role="verdict", latency_ms=12, stop_reason="end_turn"))
        recs.append(lp.openai_entry_record(led[0]))
        return _row(body_frag())["llm_calls"]

    calls = _in_ctx(bound_world)
    assert set(calls) == {"v", "calls", "llm_calls_dropped"} and calls["v"] == 1
    assert len(calls["calls"]) == 3 and calls["llm_calls_dropped"] == 0
    for c in calls["calls"]:
        assert set(c) == _otel_fields()
    oa = calls["calls"][0]
    assert oa[m["provider"]] == "openai" and oa[m["prompt_tokens"]] == 100 and oa[m["completion_tokens"]] == 20
    an = [c for c in calls["calls"] if c[m["provider"]] == "anthropic"]
    assert len(an) == 1 and an[0]["role"] == "verdict" and an[0][m["stop_reason"]] == ["end_turn"]
    assert an[0][m["model"]] == "claude-haiku-5-5" and an[0]["latency_ms"] == 12
    assert "gen_ai.operation.name" not in an[0]

    def many():
        recs = lp.start_llm_ledger()
        for i in range(40):
            recs.append(lp.anthropic_usage_record("claude-haiku-5-5", {"input_tokens": i, "output_tokens": 1}))
        return _row(body_frag())["llm_calls"]

    big = _in_ctx(many)
    assert len(big["calls"]) == 32 and big["llm_calls_dropped"] == 8
    assert _in_ctx(lambda: _row(body_frag())["llm_calls"]) is None

    def empty():
        lp.start_llm_ledger()
        return _row(body_frag())["llm_calls"]

    assert _in_ctx(empty) == {"v": 1, "calls": [], "llm_calls_dropped": 0}


def test_r15b_camera_extra_records(monkeypatch):
    """R-S22-39: the camera exit passes its vision ledger; the entries join the row once."""
    m = lp.OTEL_GENAI_ATTRIBUTES
    vision = [{"model": "gpt-4o-mini", "prompt_tokens": 900, "completion_tokens": 40, "cached_tokens": 0}]

    def world():
        led = openai_pricing.start_openai_ledger()
        led.append({"model": "gpt-4o-mini", "prompt_tokens": 100, "completion_tokens": 20, "cached_tokens": 0})
        return _row(body_frag(), "camera", extra_records=vision)["llm_calls"]

    calls = _in_ctx(world)["calls"]
    assert sorted(c[m["prompt_tokens"]] for c in calls) == [100, 900]

    def same_list():
        led = openai_pricing.start_openai_ledger()
        led.append(vision[0])
        return _row(body_frag(), "camera", extra_records=led)["llm_calls"]

    assert len(_in_ctx(same_list)["calls"]) == 1
    assert _in_ctx(lambda: _row(body_frag(), "url")["llm_calls"]) is None


def test_r16_sources_cache_timings_partial():
    b = body_frag()
    b["metadata"]["stage_timings_ms"] = {"phase1": 120.7, "verdict": 40, "bad key": 5, "nan_one": float("nan"),
                                         "neg": -3, "flag": True}
    b["metadata"]["kb_hit"] = ["hit", "miss"]
    b["metadata"]["cached"] = True
    b["products"][0]["price"]["_cached"] = True
    b["metadata"]["partial"] = True
    b["metadata"]["partial_stage"] = "scoring"
    b["metadata"]["field_status"] = [{"price": "ok"}, {"price": "missing"}]
    b["metadata"]["product_categories"] = ["fragrances", "Not A Cat!"]
    row = _row(b, "camera", vision_ms=812.0, compare_ms=float("inf"))
    su = row["sources_used"]
    assert su == {"v": 1, "price_method": ["page_scrape_jsonld", "page_scrape_jsonld"],
                  "price_host": ["tomford.com", "ssense.com"],
                  "rating_method": ["google_shopping", "google_shopping"], "kb_hit": ["hit", "miss"]}
    assert row["cache_hits"] == {"v": 1, "response": True, "price": [True, False]}
    st = row["stage_timings"]
    assert st["phase1"] == 120 and st["verdict"] == 40 and st["vision_ms"] == 812
    assert "bad key" not in st and "nan_one" not in st and "neg" not in st and "flag" not in st
    assert "compare_ms" not in st or isinstance(st["compare_ms"], int)
    assert row["partial_stage"] == "scoring"
    assert row["field_status"] == [{"price": "ok"}, {"price": "missing"}]
    assert row["category"] == "fragrances"
    assert row["product_categories"] == ["fragrances", None]
    b2 = copy.deepcopy(b)
    b2["metadata"]["stage_timings_ms"] = {"k%02d" % i: i for i in range(40)}
    b2["metadata"]["partial_stage"] = "unknown_stage"
    b2["metadata"]["field_status"] = [{}, {}, {}]
    b2["metadata"]["kb_hit"] = ["hit"]
    r2 = _row(b2, "text")
    assert len([k for k in r2["stage_timings"] if k.startswith("k")]) == 32
    assert r2["partial_stage"] is None and r2["field_status"] is None
    assert r2["sources_used"]["kb_hit"] is None
    b3 = copy.deepcopy(b)
    b3["metadata"]["partial"] = False
    assert _row(b3)["partial_stage"] is None
    assert _row(b3)["refusal_reason"] is None and _row(b3)["kb_product_ids"] is None


def test_r17_record_schedules_one_insert(monkeypatch):
    cr = _cr()
    _full(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    scheduled = []

    def _ff(coro, label):
        scheduled.append((coro, label))
        return None

    monkeypatch.setattr(cr, "_async_utils", SimpleNamespace(fire_and_forget=_ff))
    calls = []

    class _T:
        def __init__(self, name):
            calls.append(("table", name))

        def insert(self, row):
            calls.append(("insert", tuple(row)))
            return self

        def execute(self):
            calls.append(("execute",))
            return SimpleNamespace(data=[{}])

    admin = SimpleNamespace(table=lambda name: _T(name))
    from app.services import database_service

    monkeypatch.setattr(database_service, "get_admin_supabase_client", lambda: admin)
    db = []

    async def _run_db(call):
        db.append(call)
        return call()

    monkeypatch.setattr(cr, "_db_offload", SimpleNamespace(run_db=_run_db))
    assert cr.record_compare_run(body_frag(), "text") is None
    assert [lbl for _c, lbl in scheduled] == ["compare_runs.insert.text"]
    asyncio.run(scheduled[0][0])
    assert len(db) == 1
    assert calls == [("table", "compare_runs"), ("insert", RUN_COLUMNS_WANT), ("execute",)]


class APIError(Exception):
    pass


def test_r18_insert_failure_one_warning(monkeypatch, caplog):
    cr = _cr()
    monkeypatch.setenv(FLAG, "true")
    from app.services import database_service

    monkeypatch.setattr(database_service, "get_admin_supabase_client", lambda: SimpleNamespace())

    async def _run_db(call):
        raise APIError("42P01 relation does not exist")

    monkeypatch.setattr(cr, "_db_offload", SimpleNamespace(run_db=_run_db))
    row = _row(body_frag())
    raised = None
    with caplog.at_level(logging.DEBUG):
        try:
            out = asyncio.run(cr._insert(row))
        except Exception as exc:  # noqa: BLE001 - the row asserts the coroutine swallowed it
            raised, out = type(exc).__name__, None
    assert raised is None and out is None, raised
    recs = [r for r in caplog.records if "[COMPARE_RUNS]" in r.getMessage()]
    assert [(r.levelno, r.getMessage()) for r in recs] == [
        (logging.WARNING, "[COMPARE_RUNS] insert skipped reason=APIError")]
    assert "42P01" not in caplog.text


def test_r19_build_failure_never_raises(monkeypatch, caplog):
    cr = _cr()
    monkeypatch.setenv(FLAG, "true")
    sched = []
    monkeypatch.setattr(cr, "_async_utils", SimpleNamespace(fire_and_forget=lambda c, label: sched.append(label)))

    def _boom(*_a, **_k):
        raise KeyError("s22")

    monkeypatch.setattr(cr, "build_run_row", _boom)
    with caplog.at_level(logging.DEBUG):
        assert cr.record_compare_run(body_frag(), "text") is None
    assert sched == []
    recs = [r.getMessage() for r in caplog.records if "[COMPARE_RUNS]" in r.getMessage()]
    assert recs == ["[COMPARE_RUNS] insert skipped reason=KeyError"]
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        cr.record_compare_run({"success": False}, "text")
        cr.record_compare_run("x", "text")
    assert not [r for r in caplog.records if "[COMPARE_RUNS]" in r.getMessage()]


def test_r25_leaf_imports():
    tree = ast.parse(_src("app/services/compare_runs.py"))
    allowed_app = {"app.services.result_gate", "app.services.llm_pricing", "app.utils.request_context",
                   "app.utils.async_utils", "app.utils.db_offload"}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                assert not a.name.startswith("app"), a.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("app"):
                full = {mod + "." + a.name for a in node.names}
                assert full <= allowed_app, full
    banned = ("structured_comparison_service", "kb_service", "app.api", "app.middleware", "app.main")
    src = _src("app/services/compare_runs.py")
    for word in banned:
        assert word not in src, word
    inner = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_insert"]
    assert inner and any(isinstance(x, ast.ImportFrom) and any(a.name == "database_service" for a in x.names)
                         for x in ast.walk(inner[0]))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any(isinstance(n, ast.ImportFrom) and any(a.name == "database_service" for a in n.names) for n in top)


GITLEAKS_RX = re.compile(r"(access|auth|api|credential|creds|key|password|secret|token)", re.I)
HEXISH_RX = re.compile(r"^[0-9a-fA-F]{20,}$|^[A-Za-z0-9+/=]{20,}$")


def _module_assignments(rel):
    tree = ast.parse(_src(rel))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    yield t.id, node.value


def test_r26_no_gitleaks_keyword_names():
    """R-S22-37: no module-level name carrying a gitleaks keyword assigned a 20+ char hex / base64
    literal; and no DEVICE_KEY_* constant at all."""
    for rel in ("app/services/compare_runs.py", "scripts/cron_compare_judge.py"):
        for name, value in _module_assignments(rel):
            assert not name.upper().startswith("DEVICE_KEY"), (rel, name)
            if GITLEAKS_RX.search(name) and isinstance(value, ast.Constant) and isinstance(value.value, str):
                assert not HEXISH_RX.match(value.value), (rel, name)
    me = Path(__file__).read_text(encoding="utf-8")
    for line in me.splitlines():
        m = re.match(r"^([A-Z0-9_]+)\s*=\s*\"([^\"]*)\"", line)
        if m and GITLEAKS_RX.search(m.group(1)):
            assert not HEXISH_RX.match(m.group(2)), line


def test_r27_retention_single_definition():
    hits = []
    for base in ("app", "scripts"):
        for p in (ROOT / base).rglob("*.py"):
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.match(r"^\s*COMPARE_RUN_RETENTION_DAYS\s*=", line):
                    hits.append((p.relative_to(ROOT).as_posix(), line.strip()))
    assert hits == [("app/services/compare_runs.py", "COMPARE_RUN_RETENTION_DAYS = 365")], hits
    script = _src("scripts/cron_compare_judge.py")
    assert "COMPARE_RUN_RETENTION_DAYS" in script and "compare_runs" in script


# =============================================================== the five exits (R20-R24)

def _route_world(monkeypatch, kind, body=None, events=None):
    if kind in ("post", "get", "stream"):
        led = s20._ledger(monkeypatch, text_routes)
        s20._text_svc(monkeypatch, result=body if body is not None else s20.body_sup(),
                      events=events if events is not None else [
                          ("status", {"progress": 10}),
                          ("settle_complete", body if body is not None else s20.body_sup()),
                          ("complete", body if body is not None else s20.body_sup())])
        return led
    if kind == "camera":
        led, _cam = s20._camera(monkeypatch, s20.VISION["DISTINCT"](), result=body or s20.body_sup())
        return led
    led, _calls = s20._url(monkeypatch, body if body is not None else s20.url_v03())
    return led


def _hit(client, kind):
    h = _headers()
    if kind == "post":
        return client.post("/api/v1/text/compare", json={"query": s20.QUERY}, headers=h)
    if kind == "get":
        return client.get("/api/v1/text/compare", params={"q": s20.QUERY}, headers=h)
    if kind == "stream":
        return client.get("/api/v1/text/compare/stream", params={"q": s20.QUERY}, headers=h)
    if kind == "camera":
        files = [("images", ("p%d.jpg" % i, s20.JPEG, "image/jpeg")) for i in range(2)]
        return client.post("/api/v1/image/identify", files=files, headers=h)
    return client.post("/api/v1/url/compare", json={"url1": s20.URL1, "url2": s20.URL2}, headers=h)


KIND_TYPE = {"post": "text", "get": "text", "stream": "text_stream", "camera": "camera", "url": "url"}


@pytest.mark.parametrize("kind", list(KIND_TYPE))
def test_r20_five_exits_on_route(monkeypatch, client, authed, kind):
    cr = _cr()
    _full(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec(monkeypatch)
    _route_world(monkeypatch, kind)
    resp = _hit(client, kind)
    assert resp.status_code == 200, resp.text[:300]
    assert [c[0] for c in rec.calls] == [KIND_TYPE[kind]], rec.calls
    assert rec.labels == ["compare_runs.insert." + KIND_TYPE[kind]], rec.labels
    kw = rec.calls[0][1]
    if kind == "camera":
        assert set(kw) == {"vision_ms", "compare_ms", "extra_records"}, kw
        assert isinstance(kw["extra_records"], list)
    elif kind == "url":
        assert set(kw) == {"compare_ms"} and type(kw["compare_ms"]) is int
    else:
        assert kw == {}
    row = rec.rows[0]
    assert tuple(row) == RUN_COLUMNS_WANT and row["input_type"] == KIND_TYPE[kind]
    assert row["consent_version"] == 3 and re.fullmatch(r"[a-f0-9]{64}", row["device_key"] or "")
    assert row["compare_request_id"] == _headers()["X-Compare-Request-Id"]
    if kind == "url":
        assert row["llm_calls"] is None
    assert cr is not None


@pytest.mark.parametrize("case", ["post_gate", "stream_gate", "url_gate", "camera_error", "stream_error"])
def test_r21_no_row_on_refusals(monkeypatch, client, authed, case):
    _cr()
    _full(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(s20.FLAG, "true")
    rec = Rec(monkeypatch)
    v09 = s20.body_v09()
    if case == "post_gate":
        _route_world(monkeypatch, "post", body=v09)
        resp = _hit(client, "post")
        assert resp.status_code != 200
    elif case == "stream_gate":
        _route_world(monkeypatch, "stream", events=[("settle_complete", v09), ("complete", v09)])
        _hit(client, "stream")
    elif case == "url_gate":
        _route_world(monkeypatch, "url", body=s20.url_v09())
        assert _hit(client, "url").status_code != 200
    elif case == "camera_error":
        failed = {"success": False, "error": "x", "code": "INSUFFICIENT_DATA"}
        _route_world(monkeypatch, "camera", body=failed)
        _hit(client, "camera")
    else:
        _route_world(monkeypatch, "stream", body=s20.body_sup(), events=[
            ("error", {"error": "Streaming comparison failed", "code": "TIMEOUT"}),
            ("complete", s20.body_sup())])
        _hit(client, "stream")
    assert rec.labels == [], rec.labels
    assert rec.rows == []


def test_r22_stream_call_not_awaited():
    src = _src("app/api/text_routes.py")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "record_compare_run"]
    assert len(calls) == 3, len(calls)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    for c in calls:
        assert isinstance(parents[c], ast.Expr), ast.dump(parents[c])
        p = parents[c]
        while p in parents:
            assert not isinstance(p, ast.Await)
            p = parents[p]
    stream = [c for c in calls if c.args and isinstance(c.args[1], ast.Constant) and c.args[1].value == "text_stream"]
    assert len(stream) == 1
    block = parents[parents[stream[0]]]
    assert isinstance(block, ast.If)
    cond = ast.unparse(block.test)
    assert cond == "isinstance(complete_response, dict) and complete_response.get('success') is True", cond
    names = [ast.unparse(s) for s in block.body]
    assert names[0].startswith("capture_result_status(complete_response, 'text_stream')"), names
    assert names[1].startswith("_compare_runs.record_compare_run(complete_response, 'text_stream')"), names


def test_r23_comparison_id_echo_on_text_only(monkeypatch, client, authed):
    _cr()
    _full(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    rid = str(uuid.UUID(_hex("cmp")[:32], version=4))
    rec = Rec(monkeypatch)
    _route_world(monkeypatch, "post")

    async def _persist(**_kw):
        return rid

    monkeypatch.setattr(text_routes, "_persist_comparison_bounded", _persist)
    assert _hit(client, "post").status_code == 200
    assert rec.rows and rec.rows[-1]["comparison_id"] == rid
    monkeypatch.delenv(s20.ECHO)
    assert _hit(client, "post").status_code == 200
    assert rec.rows[-1]["comparison_id"] is None
    for kind in ("camera", "url"):
        monkeypatch.setenv(s20.ECHO, "true")
        _route_world(monkeypatch, kind)
        assert _hit(client, kind).status_code == 200
        assert rec.rows[-1]["comparison_id"] is None, kind


@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
def test_r24_w4_13_no_log_search_from_insert(monkeypatch, client, authed, truth):
    _cr()
    _full(monkeypatch, truth=truth)
    out = {}
    for state in ("off", "on"):
        if state == "on":
            monkeypatch.setenv(FLAG, "true")
        else:
            monkeypatch.delenv(FLAG, raising=False)
        rec = Rec(monkeypatch)
        led = _route_world(monkeypatch, "post")
        assert _hit(client, "post").status_code == 200
        out[state] = (_scrub(copy.deepcopy(led.rows)), list(led.labels), rec.labels)
    assert out["on"][0] == out["off"][0]
    assert out["on"][1] == out["off"][1]
    assert out["on"][2] == ["compare_runs.insert.text"]


# =============================================================== migration 048 (B01-B17)

M048 = MIG / "048_compare_runs.sql"
R048 = MIG / "rollback" / "048_compare_runs.sql"


def _sql(path):
    assert path.exists(), "%s is missing" % path.name
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _strip_comments(sql):
    return "\n".join(line for line in sql.split("\n") if not line.lstrip().startswith("--"))


def _compact(text):
    return re.sub(r"\s+", " ", text).strip()


def test_b01_048_files_exist_once():
    assert sorted(p.name for p in MIG.glob("048_*.sql")) == ["048_compare_runs.sql"]
    assert sorted(p.name for p in (MIG / "rollback").glob("048_*.sql")) == ["048_compare_runs.sql"]
    for n in ("053",):
        assert not list(MIG.glob(n + "_*.sql")), n


def test_b02_one_transaction_ascii_lf():
    for path in (M048, R048):
        assert path.exists(), path.name
        raw = path.read_bytes()
        assert b"\r" not in raw and all(b < 128 for b in raw), path.name
        body = _strip_comments(raw.decode("ascii"))
        stmts = [s.strip() for s in body.split("\n") if s.strip()]
        assert stmts[0] == "BEGIN;" and stmts[-1] == "COMMIT;", path.name
        assert body.count("BEGIN;") == 1 and body.count("COMMIT;") == 1, path.name


def _create_table(sql, name):
    m = re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \((.*?)\n\);" % name, sql, re.S)
    assert m, name
    return m.group(1)


def _columns(block):
    cols = []
    depth = 0
    cur = ""
    for ch in block:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            cols.append(_compact(cur))
            cur = ""
        else:
            cur += ch
    if cur.strip():
        cols.append(_compact(cur))
    return cols


COMPARE_RUN_TYPES = [
    ("id", "uuid PRIMARY KEY"), ("created_at", "timestamptz NOT NULL"), ("comparison_id", "uuid NULL"),
    ("consent_version", "smallint NULL"), ("compare_request_id", "uuid NULL"), ("device_key", "text NULL"),
    ("input_type", "text NOT NULL"), ("category", "text NULL"), ("product_categories", "jsonb NULL"),
    ("refusal_reason", "text NULL"), ("query_hmac", "text NULL"), ("kb_product_ids", "jsonb NULL"),
    ("sources_used", "jsonb NULL"), ("cache_hits", "jsonb NULL"), ("llm_calls", "jsonb NULL"),
    ("stage_timings", "jsonb NULL"), ("result_status", "text NULL"), ("identity_confidence", "text NULL"),
    ("data_coverage", "smallint NULL"), ("winner_supported", "boolean NULL"), ("field_status", "jsonb NULL"),
    ("partial_stage", "text NULL"), ("evidence", "jsonb NULL"), ("recompare", "boolean NOT NULL"),
    ("judged_at", "timestamptz NULL"),
]


def test_b03_compare_runs_columns_closed():
    cols = _columns(_create_table(_sql(M048), "compare_runs"))
    assert [c.split(" ")[0] for c in cols] == [n for n, _t in COMPARE_RUN_TYPES]
    for col, (name, typ) in zip(cols, COMPARE_RUN_TYPES):
        assert col.startswith(name + " " + typ), (col, typ)
    assert set(RUN_COLUMNS_WANT) <= {n for n, _t in COMPARE_RUN_TYPES}
    for col in cols:
        name = col.split(" ")[0]
        assert not t043.PERSONAL_RX.search(name) if hasattr(t043, "PERSONAL_RX") else True, name
        assert name not in ("user_id", "email", "ip_address", "query", "url")


def test_b04_checks_and_fks():
    sql = _compact(_sql(M048))
    for col in ("device_key", "query_hmac"):
        assert "%s text NULL CHECK (%s ~ '^[a-f0-9]{64}$')" % (col, col) in sql, col
    assert "input_type text NOT NULL CHECK (input_type IN ('text', 'text_stream', 'camera', 'url'))" in sql
    statuses = ", ".join("'%s'" % s for s in rg.STATUSES)
    assert "result_status text NULL CHECK (result_status IN ( %s ))" % statuses in sql
    levels = ", ".join("'%s'" % s for s in rg.CONFIDENCE_LEVELS)
    assert "identity_confidence IN (%s)" % levels in sql
    stages = ", ".join("'%s'" % s for s in ("gather", "post_gather", "scoring", "verdict"))
    assert set(rg.PARTIAL_STAGES) == {"gather", "post_gather", "scoring", "verdict"}
    assert "partial_stage IN (%s)" % stages in sql
    assert "data_coverage smallint NULL CHECK (data_coverage BETWEEN 0 AND 4)" in sql
    assert "pg_column_size(evidence) <= 131072" in sql
    assert "refusal_reason text NULL CHECK (refusal_reason ~ '^[A-Za-z0-9_:-]{1,64}$')" in sql
    assert re.match(r"^[A-Za-z0-9_:-]{1,64}$", "result_gate:placeholder_identity")
    assert re.match(r"^[A-Za-z0-9_:-]{1,64}$", "CATEGORY_NOT_LIVE")
    assert "comparison_id uuid NULL REFERENCES public.comparisons (id) ON DELETE SET NULL" in sql
    assert "run_id uuid NOT NULL REFERENCES public.compare_runs (id) ON DELETE CASCADE" in sql
    assert "judge text NOT NULL CHECK (judge IN ('programmatic', 'haiku', 'sonnet'))" in sql
    assert "note text NULL CHECK (char_length(note) <= 300)" in sql
    assert "CONSTRAINT compare_judgements_run_judge UNIQUE (run_id, judge)" in sql


def test_b05_indexes_immutable():
    sql = _compact(_sql(M048))
    want = {
        "idx_compare_runs_created": ("(created_at)", None),
        "idx_compare_runs_recompare": ("(query_hmac, device_key, created_at)", "query_hmac IS NOT NULL"),
        "idx_compare_runs_comparison": ("(comparison_id)", "comparison_id IS NOT NULL"),
        "idx_compare_runs_request": ("(compare_request_id)", "compare_request_id IS NOT NULL"),
        "idx_compare_runs_unjudged": ("(created_at)", "judged_at IS NULL"),
    }
    found = re.findall(r"CREATE INDEX IF NOT EXISTS (\w+) ON public\.compare_runs (\([^)]*\))(?: WHERE ([^;]*))?;", sql)
    assert {n: (c, w or None) for n, c, w in found} == want
    for _n, _c, w in found:
        assert "now()" not in (w or "").lower() and "current_" not in (w or "").lower()


def test_b06_service_role_only():
    sql = _compact(_strip_comments(_sql(M048)))
    assert "CREATE POLICY" not in sql.upper()
    for t in ("compare_runs", "compare_judgements"):
        assert "ALTER TABLE public.%s ENABLE ROW LEVEL SECURITY;" % t in sql
        rev = "REVOKE ALL ON TABLE public.%s FROM PUBLIC, anon, authenticated, service_role;" % t
        gra = "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%s TO service_role;" % t
        assert rev in sql and gra in sql and sql.index(rev) < sql.index(gra), t
    rev = "REVOKE ALL ON FUNCTION public.compare_runs_prune(integer) FROM PUBLIC, anon, authenticated, service_role;"
    gra = "GRANT EXECUTE ON FUNCTION public.compare_runs_prune(integer) TO service_role;"
    assert rev in sql and gra in sql and sql.index(rev) < sql.index(gra)
    assert len(re.findall(r"\bGRANT\b", sql)) == 3


def _fn(sql, name):
    m = re.search(r"CREATE OR REPLACE FUNCTION public\.%s\(.*?\n\$\$;" % name, sql, re.S)
    assert m, name
    return _compact(m.group(0))


def test_b07_prune_function():
    ours = _fn(_sql(M048), "compare_runs_prune")
    kb = _fn(_sql(MIG / "045_kb_core.sql"), "kb_prune_feedback")
    want = (kb.replace("kb_prune_feedback", "compare_runs_prune").replace("public.kb_feedback AS f", "public.compare_runs AS r")
            .replace("f.created_at", "r.created_at"))
    assert ours == want
    assert "p_days > 3650" in ours and "SECURITY INVOKER" in ours and "ROW_COUNT" in ours


def _cascade(sql):
    m = re.search(r"CREATE OR REPLACE FUNCTION public\.delete_user_cascade.*?\$function\$;", sql, re.S)
    assert m, "no cascade"
    return m.group(0)


def _body(fn_text):
    return fn_text[fn_text.index("AS $function$") + len("AS $function$"):fn_text.rindex("$function$;")]


HOOK = ("DELETE FROM public.kb_feedback WHERE compare_request_id IN ( SELECT r.compare_request_id "
        "FROM public.compare_runs AS r JOIN public.comparisons AS c ON c.id = r.comparison_id "
        "WHERE c.user_id = target_user_id AND r.compare_request_id IS NOT NULL )")


def test_b08_cascade_is_043_plus_one():
    c48 = _cascade(_sql(M048))
    c43 = _cascade(_sql(MIG / "043_delete_user_cascade_full_erasure.sql"))
    assert c48[:c48.index("AS $function$")] == c43[:c43.index("AS $function$")]
    ch48 = [t043._flat(c) for c in t043._body_chunks(_body(c48))]
    ch43 = [t043._flat(c) for c in t043._body_chunks(_body(c43))]
    assert len(ch48) == len(ch43) + 1
    assert ch48[:2] == ch43[:2] and ch48[3:] == ch43[2:]
    parsed = t043.parse_body(_body(c48))
    hook = [s for s in parsed if s.get("idx") == 2]
    assert hook and hook[0]["kind"] == "delete" and hook[0]["table"] == "kb_feedback", hook


def test_b09_hook_join_text():
    body = _body(_cascade(_sql(M048)))
    chunk = t043._body_chunks(body)[2]
    assert _compact(chunk).rstrip(";").strip() == HOOK
    for rel in re.findall(r"(?:FROM|JOIN)\s+([\w.]+)", chunk):
        assert rel.startswith("public."), rel


def test_b10_revoke_after_create_no_grant():
    for path in (M048, R048):
        sql = _strip_comments(_sql(path))
        create = sql.index("CREATE OR REPLACE FUNCTION public.delete_user_cascade")
        rev = sql.find("REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)\nFROM PUBLIC, anon, authenticated;")
        assert rev > create, path.name
        assert not re.search(r"GRANT\s+\w+\s+ON\s+FUNCTION\s+public\.delete_user_cascade", sql, re.I), path.name


def test_b11_assert_block():
    sql = _sql(M048)
    m = re.search(r"DO \$assert\$\nBEGIN\n(.*?)\nEND\n\$assert\$;", sql, re.S)
    assert m
    lines = [x.strip() for x in m.group(1).split("\n") if x.strip()]
    nil = "-".join("0" * n for n in (8, 4, 4, 4, 12))
    assert lines[0] == "PERFORM public.delete_user_cascade('" + nil + "'::uuid);"
    blk = m.group(1)
    assert "p.prosecdef" in blk and "search_path=public" in blk
    assert "'service_role', 'public.delete_user_cascade(uuid)', 'EXECUTE'" in blk
    assert "'anon'" in blk and "'authenticated'" in blk
    assert "PERFORM public.compare_runs_prune(3650);" in blk
    assert "048 assert:" in blk and "043 assert:" not in blk


def test_b12_guard_block():
    sql = _sql(M048)
    m = re.search(r"DO \$guard\$(.*?)\$guard\$;", sql, re.S)
    assert m
    g = m.group(1)
    for word in ("public.kb_feedback", "compare_request_id", "user_preference_history"):
        assert word in g, word
    for tbl in ("users", "user_events", "comparison_feedback", "comparisons", "search_logs", "user_usage",
                "referral_invites", "referral_redemptions", "deep_review_credits", "re_engagement_events",
                "pain_workflow_events", "user_preference_history", "admin_audit_log"):
        assert "'public.%s'" % tbl in g, tbl
    raises = re.findall(r"RAISE EXCEPTION '([^']*)'", g)
    assert raises and all(r.startswith("048 guard:") for r in raises), raises


def test_b13_no_comment_in_dollar_bodies():
    for path in (M048, R048):
        sql = _sql(path)
        for m in re.finditer(r"(\$\w*\$)(.*?)\1", sql, re.S):
            assert "--" not in m.group(2), (path.name, m.group(1))


def test_b14_rollback_restores_043():
    rb = _sql(R048)
    c43 = _cascade(_sql(MIG / "043_delete_user_cascade_full_erasure.sql"))
    assert _cascade(rb) == c43
    pos = [rb.index(x) for x in ("CREATE OR REPLACE FUNCTION public.delete_user_cascade",
                                 "DROP FUNCTION IF EXISTS public.compare_runs_prune(integer);",
                                 "DROP TABLE IF EXISTS public.compare_judgements;",
                                 "DROP TABLE IF EXISTS public.compare_runs;")]
    assert pos == sorted(pos)


def test_b15_header_phrases():
    head = " ".join(line[2:].strip() for line in _sql(M048).split(chr(10)) if line.startswith("--")).lower()
    for phrase in ("migration 048", "s81-22", "merging this changes nothing in production",
                   "apply order: 043 and 045 applied before 048", "rollback/048_compare_runs.sql",
                   "service role only", "de-identified", "no user id", "on delete set null",
                   "device_key and query_hmac are hmac-sha256 under device_key_pepper",
                   "compare_run_retention_days = 365", "compare_runs_prune", "kb_feedback",
                   "no comment inside a dollar body", "roll back 048 before 045", "aborts the whole account deletion"):
        assert phrase in head, phrase
    rhead = " ".join(line[2:].strip() for line in _sql(R048).split(chr(10)) if line.startswith("--")).lower()
    for phrase in ("restores the 043 delete_user_cascade body", "drops compare_runs and compare_judgements",
                   "the run rows are lost"):
        assert phrase in rhead, phrase


def test_b16_fence_green_with_048():
    assert M048.exists()
    report = t043.fence_report(t043.real_forward_files())
    assert report.get("file") == "048_compare_runs.sql", report.get("file")
    assert t043._all_gaps(report) == set()
    assert "kb_feedback" not in t043.KNOWN_USER_TABLES and "compare_runs" not in t043.KNOWN_USER_TABLES


def test_b17_sqlfluff_clean():
    import subprocess
    import sys

    for path in (M048, R048):
        assert path.exists(), path.name
        proc = subprocess.run([sys.executable, "-m", "sqlfluff", "lint", "--config", str(ROOT / ".sqlfluff"),
                               str(path)], capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=str(ROOT))
        assert proc.returncode == 0, proc.stdout[-2000:]


# =============================================================== PIN rows (green at base)

def _snapshot_response(kind, resp):
    if kind == "stream":
        return s20._frames(resp.text)
    try:
        return (resp.status_code, resp.json())
    except ValueError:
        return (resp.status_code, resp.text)


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()
                if not (k in ("request_id", "elapsed_seconds") or str(k).endswith("_ms"))}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_scrub(v) for v in obj)
    return obj


@pytest.mark.parametrize("truth", [False, True], ids=["w413_off", "w413_on"])
@pytest.mark.parametrize("value", OFF_VALUES, ids=["unset", "false", "zero", "off", "empty"])
@pytest.mark.parametrize("kind", list(KIND_TYPE))
def test_p01_flag_off_identity_all_exits(monkeypatch, client, authed, caplog, kind, value, truth):
    _full(monkeypatch, truth=truth)
    runs = []
    for phase in ("reference", "probe"):
        monkeypatch.delenv(FLAG, raising=False)
        if phase == "probe" and value is not None:
            monkeypatch.setenv(FLAG, value)
        rec = Rec(monkeypatch, raising=(phase == "probe"))
        led = _route_world(monkeypatch, kind)
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            resp = _hit(client, kind)
        runs.append({
            "resp": _scrub(_snapshot_response(kind, resp)),
            "rows": _scrub(copy.deepcopy(led.rows)), "labels": list(led.labels), "refunds": list(led.refunds),
            "lifetime": list(led.lifetime), "history": list(led.history),
            "cr": (rec.labels, rec.rows, rec.db, rec.admin, rec.calls[:0]),
            "log": [r.getMessage() for r in caplog.records if "[COMPARE_RUNS]" in r.getMessage()],
        })
    a, b = runs
    assert a["resp"] == b["resp"]
    for key in ("rows", "labels", "refunds", "lifetime", "history"):
        assert a[key] == b[key], key
    assert b["cr"] == ([], [], 0, 0, []) and a["cr"] == ([], [], 0, 0, [])
    assert a["log"] == [] and b["log"] == []
    assert not [x for x in b["labels"] if x.startswith("compare_runs.")]


@pytest.mark.parametrize("kind", list(KIND_TYPE))
def test_p02_capture_result_status_unchanged(monkeypatch, client, authed, kind):
    import sentry_sdk

    _full(monkeypatch)
    seen = {}
    for state in ("off", "on"):
        if state == "on":
            monkeypatch.setenv(FLAG, "true")
        else:
            monkeypatch.delenv(FLAG, raising=False)
        calls = []
        monkeypatch.setattr(sentry_sdk, "capture_message",
                            lambda *a, **k: calls.append((a, {x: y for x, y in k.items() if x != "extras"})))
        Rec(monkeypatch)
        _route_world(monkeypatch, kind)
        assert _hit(client, kind).status_code == 200
        seen[state] = [c for c in calls if c[0] and c[0][0] == "result_status"] or calls
    assert seen["on"] == seen["off"]
    assert seen["off"], "B1 ON: one capture per delivery"


def _stream_finally_nodes():
    tree = ast.parse((ROOT / "app/api/text_routes.py").read_text(encoding="utf-8"))
    gens = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "event_generator"]
    assert gens
    out = []
    for g in gens:
        for t in ast.walk(g):
            if isinstance(t, ast.Try) and t.finalbody:
                out.append(t.finalbody)
    return out


def test_p03_g20_gr2_still_green():
    finals = _stream_finally_nodes()
    assert finals
    for body in finals:
        for stmt in body:
            for n in ast.walk(stmt):
                assert not isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)), ast.dump(n)[:200]
    settle = 0
    for body in finals:
        for stmt in body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "fire_and_forget":
                    if n.args and isinstance(n.args[0], ast.Call) and getattr(n.args[0].func, "id", "") == "_s20_stream_settle":
                        settle += 1
    assert settle == 1, settle


def _git_blob(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_p04_043_file_untouched():
    for rel, blob in BASE_BLOBS.items():
        assert base64.b64encode(bytes.fromhex(_git_blob(ROOT / rel))).decode("ascii") == blob, rel


def test_p05_device_key_unchanged(monkeypatch):
    monkeypatch.setenv(PEPPER, PEPPER_VALUE_SYN)
    got = [rc.device_key(_hex("dk%d" % i)) for i in range(3)]
    assert base64.b64encode(hashlib.sha256("|".join(got).encode("ascii")).digest()).decode("ascii") == SYN_DEVICE_DIGEST_B64

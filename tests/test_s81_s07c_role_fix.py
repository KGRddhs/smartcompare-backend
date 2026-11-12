"""S81-07c CLAUDE-ROLE-FIX: the frozen RED file (part V = the verdict winner contract,
part T = the image_tier3 request shape).

Contract: S81_07C_UNIT_SPEC.md sections 2-6 (V1-V5, T1-T4; rows V01-V11, T01-T06).

RED rows fail at the base c6ebbd2e on an AssertionError only: a symbol the unit adds is
read through getattr / inspect.signature / ast and asserted BEFORE any call that needs it
(never a TypeError, an import error or a setup error). PIN rows are green at the base and
stay green.

Hermetic: no network (the conftest netguard plus a row-local socket recorder wherever the
harness plan runs), no dotenv file, no live marker, no real credential (one synthetic value
built at run time, set only through monkeypatch; every flag name is set or deleted only
through monkeypatch). The LLM route seam is replaced by a recorder that raises after the
capture (the scripts/meas_claude_gate.py _capture pattern), or the router's client factory
seam returns a fake client (T04).
"""
import ast
import asyncio
import hashlib
import importlib
import importlib.util
import inspect
import json
import socket
import types
from pathlib import Path

import pytest

import app.main  # noqa: F401  (the DOTENV guard: load_dotenv + the sanitizer run first)
from app.services import api_budget_service as abs_  # noqa: E402
from app.services import extraction_service as es  # noqa: E402
from app.services import image_service as isvc  # noqa: E402
from app.services import llm_router as router  # noqa: E402
from app.services import openai_service as osvc  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCS_PATH = REPO / "app" / "services" / "structured_comparison_service.py"
URL_PATH = REPO / "app" / "services" / "url_extraction_service.py"
GOLD_PATH = REPO / "tests" / "fixtures" / "s81_s07" / "verdict_gold.json"
HARNESS = "scripts.meas_claude_gate"
HARNESS_VAR = "MEAS_ANTHROPIC_TEST_KEY"

# V3: the exact block (a format string: label = index + 1, index = index; ASCII; LF).
FIXED_WINNER_TEMPLATE = (
    "\n## Fixed Winner\n"
    "The deterministic scoring above picked PRODUCT {label} as the winner. "
    'Set "winner_index" to {index}. '
    "Do not re-decide the winner from ratings, review counts, prices or any other field, "
    "and never present the other product as the winner. "
    "Name what the other product does better in key_tradeoff.\n"
)
# The last line of the base scores block (extraction_service.py:2614 at c6ebbd2e).
CROSS_TIER = ('If this is a cross-tier comparison, frame it as "different products for different needs" '
              'rather than "expensive vs cheap."\n')

# The base signature of generate_comparison (extraction_service.py:2552-2563 at c6ebbd2e).
_EMPTY = inspect.Parameter.empty
BASE_PARAMS = [("product1", _EMPTY), ("product2", _EMPTY), ("region", _EMPTY), ("concern", "value"),
               ("user_preferences", None), ("scores_summary", None), ("category", "other"),
               ("demographics_profile", None), ("comparison_quality", "normal"), ("output_lang", None)]

# Synthetic verdict inputs (no personal value; built for this file).
P1 = {"brand": "Synthbrand Alpha", "name": "Alpha Eau de Parfum", "variant": "EDP 100ml",
      "category": "fragrances", "specs": {"concentration": "EDP", "longevity": "long"},
      "price": {"amount": 45.0, "currency": "BHD", "estimated": False},
      "reviews": {"average_rating": 4.5, "review_count": 10, "summary": "Synthetic summary A."}}
P2 = {"brand": "Synthbrand Beta", "name": "Beta Eau de Toilette", "variant": "EDT 100ml",
      "category": "fragrances", "specs": {"concentration": "EDT", "longevity": "moderate"},
      "price": {"amount": 30.0, "currency": "BHD", "estimated": False},
      "reviews": {"average_rating": 4.1, "review_count": 25, "summary": "Synthetic summary B."}}
SUMMARY = ("Product scores (deterministic, qualitative summary):\n"
           "  Synthbrand Alpha Alpha Eau de Parfum: stronger overall (price tier: mid)\n"
           "  Synthbrand Beta Beta Eau de Toilette: slightly behind overall (price tier: mid)\n"
           "  Score winner: Synthbrand Alpha Alpha Eau de Parfum (narrow lead)")
PREFS = {"priorities": ["longevity", "value"], "budget": "mid", "lifestyle": ["office"],
         "brand_attitude": "best_of_both"}
INVALID_INDEXES = (None, True, False, 2, -1, "0", 0.0)

# V11: the evaluation literals recorded at the base c6ebbd2e.
GOLD_LF_SHA256 = "78134acfb3ef70c41f3067c2d223318505db970277fd7c6ed87a5db7a9e30537"
A6_SENTENCE_BASE = ("A6 measures adherence to the deterministic scores_summary carried by the prompt (the "
                    "production WINNER_INDEX_MISMATCH rule), not verdict quality against owner gold.")
TEXT_BARS_BASE = {"json_valid_pooled_min": 0.98, "json_valid_site_min": 0.90, "schema_accept_min": 1.0,
                  "refusals_a4_max": 1, "refusals_a4_arabic_max": 0, "max_tokens_pooled_max": 0.02,
                  "max_tokens_site_max_hits": 2,
                  "p95_s": {"classify": 4.0, "specs": 4.0, "reviews": 5.0, "price": 7.5, "image_tier3": 2.5},
                  "timeouts_max": 0}
VERDICT_BARS_BASE = {"json_valid_pooled_min": 0.98, "a6_mismatch_max": 0.10, "a6_agreement_min": 0.90,
                     "a6_refusals_max": 1, "a1_refusals_max": 0, "timeouts_max": 0}
A6_METRICS_BASE = {"n": 7, "json_n": 7, "json_valid": 4, "mismatches": 1, "n_scored": 3, "agreement": 0.0,
                   "refusals": 1, "timeouts": 1}
A6_VERDICT_NOGO_BASE = ("NO-GO", ["json_valid_pooled_min", "a6_mismatch_max", "a6_agreement_min",
                                  "timeouts_max"])

# T06: the other schema sites at the base c6ebbd2e (llm_router.py:110-159; the B3 V2 schema by hash).
DISAMBIGUATE_SCHEMA_BASE = {
    "type": "object",
    "properties": {"distinct_product": {"type": "string", "enum": ["true", "false", "unknown"]},
                   "confidence": {"type": "string", "enum": ["high", "low"]}},
    "required": ["distinct_product", "confidence"], "additionalProperties": False}
_NULLABLE = {"type": ["string", "null"]}
VISION_V1_SCHEMA_BASE = {
    "type": "object",
    "properties": {"products": {"type": "array", "items": {
        "type": "object",
        "properties": {"brand": _NULLABLE, "name": _NULLABLE, "size_or_count": _NULLABLE,
                       "visible_price": _NULLABLE, "confidence": _NULLABLE},
        "required": ["brand", "name", "size_or_count", "visible_price", "confidence"],
        "additionalProperties": False}}},
    "required": ["products"], "additionalProperties": False}
MODERATION_SCHEMA_BASE = {
    "type": "object",
    "properties": {"flagged": {"type": "boolean"}, "category": {"type": "string"},
                   "uncertain": {"type": "boolean"}},
    "required": ["flagged", "category", "uncertain"], "additionalProperties": False}
VISION_V2_SCHEMA_SHA256 = "bffe493b76c2e4c693e4f43cc1e9ed07968a0522e21a0c41af128e0e1c406bbe"
# Every SITES row but image_tier3 at the base: (role, claude_max_tokens, expects_json, schema tag).
OTHER_SITES_BASE = {
    "classify": ("text", 32, False, None), "parse": ("text", 768, True, None),
    "specs": ("text", 1536, True, None), "price": ("text", 512, True, None),
    "price_training": ("text", 384, True, None), "reviews": ("text", 1024, True, None),
    "verdict": ("verdict", 1536, True, None), "verdict_fallback": ("verdict", 1536, True, None),
    "vision_v2": ("vision", 1536, True, "vision_v2"), "vision_v1": ("vision", 768, True, "vision_v1"),
    "specs_targeted": ("text", 384, True, None), "specs_synthesized": ("text", 512, True, None),
    "disambiguate": ("text", 256, True, "disambiguate"), "url_extract": ("text", 1200, True, None),
    "critique": ("critic", 512, True, None)}

ROLE_FLAG_NAMES = ("ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION", "ENABLE_ANTHROPIC_VERDICT",
                   "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION", "ENABLE_SONNET_ESCALATION",
                   "ENABLE_OPENAI_PRE_V3")
PROMPT_FLAG_NAMES = ("ENABLE_GPT_WINNER", "ENABLE_ARABIC_VERDICT_OUTPUT", "ENABLE_COHORT_PERSONALIZATION",
                     "ENABLE_LLM_SPEND_BREAKER", "ENABLE_LLM_LEDGER_V2", "ENABLE_REQUEST_CONTEXT_HEADERS")
CRED_NAMES = ("ANTHROPIC_API_KEY", HARNESS_VAR)
IMG_URL = "https://images.example-retailer.test/s07c/alpha-edp.jpg"
ORGANIC = [{"title": "Synthbrand Alpha", "link": "https://www.example-retailer.test/p/alpha-edp",
            "snippet": "Synthetic product page."}]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _block(index):
    return FIXED_WINNER_TEMPLATE.format(label=index + 1, index=index)


def _gc_params():
    return list(inspect.signature(es.generate_comparison).parameters.values())


def _assert_new_param():
    """V1 read through inspect.signature: a RED row stops here at the base (AssertionError)."""
    names = [p.name for p in _gc_params()]
    assert "score_winner_index" in names, "generate_comparison has no score_winner_index parameter (V1)"


def _harness():
    spec = importlib.util.find_spec(HARNESS)
    assert spec is not None, "scripts/meas_claude_gate.py is absent"
    return importlib.import_module(HARNESS)


def _gold_cases():
    return json.loads(GOLD_PATH.read_bytes().replace(b"\r\n", b"\n").decode("utf-8"))


def _flatten(items):
    for it in items:
        if isinstance(it, list):
            for x in _flatten(it):
                yield x
        else:
            yield it


def _callee(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _calls_named(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _callee(n) == name]


def _canon(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class _Captured(Exception):
    pass


class _Cap:
    """The harness _capture pattern: route records the kwargs of the first dispatch and raises;
    get_client and the verdict model router are offline stand-ins."""

    def __init__(self, monkeypatch):
        self.got = []

        async def rec(site, dispatch, client, **kwargs):
            self.got.append((site, kwargs))
            raise _Captured()

        async def _gm(*a, **k):
            return "gpt-4o"

        from app.services.model_router_service import model_router
        monkeypatch.setattr(router, "route", rec)
        monkeypatch.setattr(es, "get_client", lambda *a, **k: object())
        monkeypatch.setattr(isvc, "get_client", lambda *a, **k: object())
        monkeypatch.setattr(model_router, "get_model", _gm)

    def _one(self, coro, site):
        self.got = []
        try:
            asyncio.run(coro)
        except _Captured:
            pass
        sites = [s for s, _ in self.got]
        assert sites == [site], "expected one %s dispatch, got %r" % (site, sites)
        return self.got[0][1]

    def verdict_kwargs(self, **kw):
        kw.setdefault("scores_summary", SUMMARY)
        kw.setdefault("category", "fragrances")
        return self._one(es.generate_comparison(P1, P2, "bahrain", **kw), "verdict")

    def verdict_system(self, **kw):
        msgs = self.verdict_kwargs(**kw)["messages"]
        assert msgs[0]["role"] == "system"
        return msgs[0]["content"]

    def image_kwargs(self):
        return self._one(isvc.extract_image_via_gpt("Synthbrand Alpha Alpha Eau de Parfum", ORGANIC),
                         "image_tier3")


@pytest.fixture(autouse=True)
def _s07c_env(monkeypatch):
    for name in ROLE_FLAG_NAMES + PROMPT_FLAG_NAMES + CRED_NAMES:
        monkeypatch.delenv(name, raising=False)
    router._reset_router_state()
    yield
    router._reset_router_state()


@pytest.fixture
def cap(monkeypatch):
    return _Cap(monkeypatch)


class _SocketGuard:
    """Records and refuses every non-loopback resolve / connect (loopback stays: the event loop's
    self-pipe is a loopback socketpair on Windows)."""
    LOOPBACK = ("127.0.0.1", "::1", "localhost")

    def __init__(self, monkeypatch):
        self.attempts = []
        real_gai = socket.getaddrinfo
        real_connect = socket.socket.connect
        guard = self

        def gai(host, *a, **k):
            h = host.decode("ascii", "replace") if isinstance(host, bytes) else host
            if h is not None and str(h).lower() not in guard.LOOPBACK:
                guard.attempts.append(("getaddrinfo", str(h)))
                raise OSError("s07c socket guard")
            return real_gai(host, *a, **k)

        def connect(sock, address):
            h = address[0] if isinstance(address, tuple) and address else address
            if str(h).lower() not in guard.LOOPBACK:
                guard.attempts.append(("connect", str(h)))
                raise OSError("s07c socket guard")
            return real_connect(sock, address)

        monkeypatch.setattr(socket, "getaddrinfo", gai)
        monkeypatch.setattr(socket.socket, "connect", connect)


@pytest.fixture
def sock_guard(monkeypatch):
    return _SocketGuard(monkeypatch)


def _text_plan(monkeypatch, tmp_path, settings):
    """The harness's own offline plan builder (_plan_text through a dry-run _Ctx): every request
    is captured at the route seam; no client, no credential read."""
    from app.services.model_router_service import model_router

    async def _gm(*a, **k):
        return "gpt-4o"

    monkeypatch.setattr(model_router, "get_model", _gm)
    mod = _harness()
    a = {"stage": "text", "dry_run": True, "--settings": ",".join(settings), "reps": mod.REPS_MAX}
    ctx = mod._Ctx(a, tmp_path / "out", "text", 0.0, {"spent": 0.0, "completed": {}, "attempts": {}})
    plan = asyncio.run(mod._plan_text(ctx))
    return mod, ctx, dict(plan)


# ===========================================================================
# V: the verdict winner contract
# ===========================================================================
def test_v01_signature_score_winner_index_last_default_none():
    """V01 RED (V1): score_winner_index is the LAST parameter of generate_comparison, default None;
    the ten base parameters keep their names, order and defaults."""
    params = _gc_params()
    assert [(p.name, p.default) for p in params[:10]] == BASE_PARAMS
    assert len(params) == 11, [p.name for p in params]
    last = params[-1]
    assert last.name == "score_winner_index"
    assert last.default is None
    assert last.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)


def test_v02_block_bytes_index_0_and_1(cap):
    """V02 RED (V2, V3): the module constant equals the V3 bytes; the captured system message
    carries the block formatted for (label 1, index 0) / (label 2, index 1) exactly once, and
    never the other index's block."""
    const = getattr(es, "_FIXED_WINNER_BLOCK", None)
    assert const == FIXED_WINNER_TEMPLATE, "extraction_service._FIXED_WINNER_BLOCK != the V3 bytes"
    assert const.isascii() and "\r" not in const
    _assert_new_param()
    for idx in (0, 1):
        system = cap.verdict_system(score_winner_index=idx)
        assert system.count(_block(idx)) == 1, idx
        assert _block(1 - idx) not in system, idx
        assert system.count("## Fixed Winner") == 1, idx


def test_v03_identity_outside_the_block(cap, monkeypatch):
    """V03 RED (V2): removing the index-0 block gives EXACTLY the system message of the same call
    without the keyword: with and without user_preferences, normal / weird / weak quality, and with
    the independent-winner block and the Arabic directive ON."""
    _assert_new_param()
    for prefs in (None, PREFS):
        for quality in ("normal", "weird", "weak"):
            kw = {"user_preferences": prefs, "comparison_quality": quality}
            plain = cap.verdict_system(**kw)
            with_block = cap.verdict_system(score_winner_index=0, **kw)
            assert with_block.count(_block(0)) == 1, (prefs is None, quality)
            assert with_block.replace(_block(0), "", 1) == plain, (prefs is None, quality)
    monkeypatch.setenv("ENABLE_GPT_WINNER", "true")
    monkeypatch.setenv("ENABLE_ARABIC_VERDICT_OUTPUT", "true")
    for prefs in (None, PREFS):
        kw = {"user_preferences": prefs, "output_lang": "ar"}
        plain = cap.verdict_system(**kw)
        with_block = cap.verdict_system(score_winner_index=1, **kw)
        assert with_block.count(_block(1)) == 1, prefs is None
        assert with_block.replace(_block(1), "", 1) == plain, prefs is None
        start = with_block.find(_block(1))
        assert with_block[:start].endswith(CROSS_TIER), prefs is None


def test_v04_placement_after_scores_before_preferences(cap):
    """V04 RED (V2): the block starts right after the cross-tier sentence of the scores block and
    ends right where the preferences block starts (no preferences: it closes the system text)."""
    _assert_new_param()
    pref_text = es._build_preferences_prompt(PREFS, demographics_profile=None)
    system = cap.verdict_system(score_winner_index=0, user_preferences=PREFS)
    start = system.find(_block(0))
    assert start >= 0
    before, after = system[:start], system[start + len(_block(0)):]
    assert before.endswith(CROSS_TIER), "the block does not follow the cross-tier sentence"
    assert ("\n## Scoring Context\n" + SUMMARY + "\n") in before
    assert after.startswith(pref_text), "the preferences block does not follow the block"
    assert after == pref_text
    bare = cap.verdict_system(score_winner_index=1)
    assert bare.endswith(CROSS_TIER + _block(1))


def test_v05_invalid_values_are_byte_identical(cap):
    """V05 RED by signature at the base (V2): None, True, False, 2, -1, "0", 0.0 -> the system
    message is byte-identical to the no-keyword call; the dispatch is still reached (no exception)."""
    _assert_new_param()
    for prefs in (None, PREFS):
        plain = cap.verdict_system(user_preferences=prefs)
        for value in INVALID_INDEXES:
            got = cap.verdict_system(score_winner_index=value, user_preferences=prefs)
            assert got == plain, (repr(value), prefs is None)
            assert "## Fixed Winner" not in got, repr(value)


def test_v06_no_scores_summary_is_byte_identical(cap):
    """V06 RED by signature at the base (V2): scores_summary None and "" with index 0 and 1 ->
    byte-identical to the no-keyword call."""
    _assert_new_param()
    for summary in (None, ""):
        plain = cap.verdict_system(scores_summary=summary)
        for idx in (0, 1):
            got = cap.verdict_system(scores_summary=summary, score_winner_index=idx)
            assert got == plain, (repr(summary), idx)
            assert "## Fixed Winner" not in got, (repr(summary), idx)


def test_v07_claude_request_keeps_the_block(cap):
    """V07 RED (V2): llm_router.to_claude_request("verdict", <the captured kwargs>)["system"]
    carries the block exactly once (the router keeps it), for index 0 and 1."""
    _assert_new_param()
    for idx in (0, 1):
        kw = cap.verdict_kwargs(score_winner_index=idx)
        req = router.to_claude_request("verdict", kw)
        assert req["system"].count(_block(idx)) == 1, idx
        assert _block(1 - idx) not in req["system"], idx
        assert req["system"].endswith(router.JSON_ONLY_INSTRUCTION)


def test_v08_both_production_callers_pass_the_scorer_index():
    """V08 RED (V4): structured_comparison_service.py holds exactly two generate_comparison calls,
    each with keyword score_winner_index whose value is scoring_result.get("winner_index")
    (no default argument)."""
    calls = _calls_named(SCS_PATH, "generate_comparison")
    assert len(calls) == 2, len(calls)
    want = ast.dump(ast.parse('scoring_result.get("winner_index")', mode="eval").body)
    for call in calls:
        kws = [k for k in call.keywords if k.arg == "score_winner_index"]
        assert len(kws) == 1, "line %d: score_winner_index keyword count %d" % (call.lineno, len(kws))
        assert ast.dump(kws[0].value) == want, "line %d: %s" % (call.lineno, ast.unparse(kws[0].value))


def test_v09_url_caller_unchanged():
    """V09 PIN (V4): url_extraction_service.py's one generate_comparison call passes no
    score_winner_index (products[0], products[1], region, category=category_used)."""
    calls = _calls_named(URL_PATH, "generate_comparison")
    assert len(calls) == 1, len(calls)
    call = calls[0]
    assert [ast.unparse(a) for a in call.args] == ["products[0]", "products[1]", "region"]
    assert [(k.arg, ast.unparse(k.value)) for k in call.keywords] == [("category", "category_used")]


def test_v10_harness_a6_and_a1_request_parity(monkeypatch, tmp_path, sock_guard):
    """V10 RED (V5): offline (no credential, the harness's own plan builder, a socket guard): for
    EVERY gold case and repeat the A6 request's system carries the block for that case's
    gold_winner_index exactly once; every A1 verdict request carries the block for index 1."""
    gold = {c["case_id"]: c["gold_winner_index"] for c in _gold_cases()}
    _mod, _ctx, plan = _text_plan(monkeypatch, tmp_path, ("A1_sites", "A6_verdict_eval"))
    a6 = plan["A6_verdict_eval"]
    assert len(a6) == 120
    assert sorted((it["case_id"], it["rep"]) for it in a6) == sorted((c, r) for c in gold for r in (0, 1))
    bad = []
    for it in a6:
        g = gold[it["case_id"]]
        system = it["request"].get("system") or ""
        if system.count(_block(g)) != 1 or _block(1 - g) in system:
            bad.append("%s/%d" % (it["case_id"], it["rep"]))
    assert not bad, "A6 requests without the case's fixed-winner block: %d of 120 (%s)" % (
        len(bad), ",".join(bad[:6]))
    a1 = [x for x in _flatten(plan["A1_sites"]) if x["site"] == "verdict"]
    assert len(a1) == 20
    for it in a1:
        system = it["request"].get("system") or ""
        assert system.count(_block(1)) == 1, it["case_id"]
        assert _block(0) not in system, it["case_id"]
    assert sock_guard.attempts == []


def test_v11_evaluation_unchanged(monkeypatch, tmp_path, sock_guard):
    """V11 PIN (V5): the gold bytes (LF-normalised), A6_SENTENCE, the TEXT and VERDICT bars, the
    plan's gold read and the A6 scoring on a synthetic record set equal their base values."""
    raw = GOLD_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == GOLD_LF_SHA256
    mod = _harness()
    assert mod.A6_SENTENCE == A6_SENTENCE_BASE
    assert mod.GO_THRESHOLDS["TEXT"] == TEXT_BARS_BASE
    assert mod.GO_THRESHOLDS["VERDICT"] == VERDICT_BARS_BASE
    assert mod.REPS_MAX == 2
    cases = json.loads(raw.decode("utf-8"))
    gold = {c["case_id"]: c["gold_winner_index"] for c in cases}
    _m, ctx, plan = _text_plan(monkeypatch, tmp_path, ("A6_verdict_eval",))
    assert ctx.gold == gold
    assert [(it["case_id"], it["rep"], it["gold"]) for it in plan["A6_verdict_eval"]] == \
        [(c["case_id"], rep, c["gold_winner_index"]) for rep in (0, 1) for c in cases]
    sc = mod._Ctx({"stage": "text", "dry_run": True, "reps": 2}, tmp_path / "score", "text", 0.0,
                  {"spent": 0.0, "completed": {}, "attempts": {}})
    sc.gold = {"g00": 0, "g01": 1, "g02": 1}
    rows = [("c1", "g00", 0, True, "end_turn", None, '{"winner_index": 0}'),
            ("c2", "g00", 1, True, "end_turn", None, '```json\n{"winner_index": 1}\n```'),
            ("c3", "g01", 0, True, "end_turn", None, '{"winner_index": 1}'),
            ("c4", "g01", 1, True, "end_turn", None, '{"winner_index": true}'),
            ("c5", "g02", 0, True, "end_turn", None, "not json"),
            ("c6", "g02", 1, False, None, "APITimeoutError", None),
            ("c7", "g03", 0, True, "refusal", None, "")]
    ps = []
    for cid, case, rep, ok, stop, err, text in rows:
        ps.append({"call_id": cid, "case_id": case, "rep": rep, "ok": ok, "stop_reason": stop,
                   "error_class": err, "setting": "A6_verdict_eval", "site": "verdict"})
        sc._texts[cid] = text
    metrics = sc._metrics("A6_verdict_eval", ps, {})
    assert metrics == A6_METRICS_BASE
    results = {"text": {"settings": {"A1_sites": {"sites": {"verdict": {
        "json_n": 20, "json_valid": 20, "refusals": 0, "timeouts": 0}}}, "A6_verdict_eval": metrics}}}
    verdict = mod.evaluate_role("VERDICT", results)
    assert (verdict[0], list(verdict[1])) == A6_VERDICT_NOGO_BASE
    assert sock_guard.attempts == []


# ===========================================================================
# T: the image_tier3 request shape
# ===========================================================================
def test_t01_image_tier3_site_option_b():
    """T01 RED (T1): SITES["image_tier3"]: output_schema None, expects_json True, role "text",
    claude_max_tokens 256."""
    spec = router.SITES["image_tier3"]
    assert spec.output_schema is None, "image_tier3 still carries an output schema"
    assert spec.expects_json is True
    assert spec.role == "text"
    assert spec.claude_max_tokens == 256


def test_t02_image_tier3_claude_request(cap):
    """T02 RED (T1): to_claude_request("image_tier3", <the kwargs extract_image_via_gpt builds>):
    no format, output_config == {"effort": "low"}, thinking disabled, max_tokens 256, system ==
    JSON_ONLY_INSTRUCTION (the Tier-3 call sends no system message of its own)."""
    kw = cap.image_kwargs()
    assert [m.get("role") for m in kw["messages"]] == ["user"]
    req = router.to_claude_request("image_tier3", kw)
    assert "format" not in req["output_config"], "image_tier3 still requests a json_schema format"
    assert req["output_config"] == {"effort": "low"}
    assert req["thinking"] == {"type": "disabled"}
    assert req["max_tokens"] == 256
    assert req.get("system") == router.JSON_ONLY_INSTRUCTION
    assert set(req) == {"model", "messages", "max_tokens", "thinking", "output_config", "system"}
    assert req["messages"] == [{"role": "user", "content": kw["messages"][0]["content"]}]


def test_t03_image_tier3_schema_constant_deleted():
    """T03 RED (T2): getattr(llm_router, "IMAGE_TIER3_SCHEMA", None) is None."""
    assert getattr(router, "IMAGE_TIER3_SCHEMA", None) is None


class _FakeClaudeMessages:
    def __init__(self, holder):
        self.holder = holder

    async def create(self, **kw):
        self.holder["calls"].append({k: v for k, v in kw.items() if k != "timeout"})
        usage = types.SimpleNamespace(input_tokens=11, output_tokens=7, cache_read_input_tokens=0,
                                      cache_creation_input_tokens=0, cache_creation=None,
                                      server_tool_use=None)
        block = types.SimpleNamespace(type="text", text=self.holder["text"])
        return types.SimpleNamespace(id="msg_s07c", type="message", role="assistant", model=kw.get("model"),
                                     content=[block], stop_reason="end_turn", usage=usage)


def test_t04_claude_branch_fence_and_parse(monkeypatch):
    """T04 RED where the base path differs (T1, T3): the REAL Tier-3 extractor on the Claude branch
    (ENABLE_ANTHROPIC_TEXT, consent 3 and a synthetic credential only through monkeypatch; a fake
    client at the router's client factory seam; the breaker read offline): a fenced object
    (```json and ```JSON) -> that URL; {"image_url": null} -> None; prose -> None; an extra key ->
    the URL; exactly one Claude call per case."""
    holder = {"calls": [], "text": ""}
    monkeypatch.setattr(router, "_anthropic_client_factory",
                        lambda **kw: types.SimpleNamespace(messages=_FakeClaudeMessages(holder)))
    rc = importlib.import_module("app.utils.request_context")
    monkeypatch.setattr(rc, "consent_version", lambda: 3, raising=False)
    monkeypatch.setattr(rc, "header_state", lambda name: "ok", raising=False)
    monkeypatch.setattr(abs_, "_redis_get", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(abs_, "_redis_set", lambda *a, **k: True, raising=False)
    monkeypatch.setattr(isvc, "get_client", lambda *a, **k: object())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "syn" + "thetic" + "-s07c-" + "a1b2")
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    cases = [
        ("```json\n" + json.dumps({"image_url": IMG_URL}) + "\n```", IMG_URL),
        ("```JSON\n" + json.dumps({"image_url": IMG_URL}) + "\n```", IMG_URL),
        (json.dumps({"image_url": None}), None),
        ("I could not find a product image in these results.", None),
        (json.dumps({"image_url": IMG_URL, "note": "synthetic extra key"}), IMG_URL),
    ]
    got = []
    for text, _want in cases:
        holder["text"] = text
        got.append(asyncio.run(isvc.extract_image_via_gpt("Synthbrand Alpha Alpha Eau de Parfum", ORGANIC)))
    assert len(holder["calls"]) == len(cases), len(holder["calls"])
    assert got == [want for _t, want in cases], got


def test_t05_harness_a1_counts_image_tier3_as_json_not_schema(tmp_path):
    """T05 RED (T1): with the new SITES the harness A1 metrics count image_tier3 under json_n /
    json_valid with schema_n 0 and schema_accepted 0; disambiguate keeps schema_n."""
    mod = _harness()
    sc = mod._Ctx({"stage": "text", "dry_run": True, "reps": 2}, tmp_path / "a1", "text", 0.0,
                  {"spent": 0.0, "completed": {}, "attempts": {}})
    rows = [("i1", "image_tier3", '{"image_url": null}'),
            ("i2", "image_tier3", '```json\n{"image_url": "' + IMG_URL + '"}\n```'),
            ("d1", "disambiguate", '{"distinct_product": "false", "confidence": "high"}'),
            ("d2", "disambiguate", '{"distinct_product": "true", "confidence": "low"}')]
    ps = []
    for cid, site, text in rows:
        ps.append({"call_id": cid, "case_id": "r00:" + cid, "rep": 0, "ok": True, "status": 200,
                   "stop_reason": "end_turn", "error_class": None, "latency_ms": 900, "site": site,
                   "setting": "A1_sites"})
        sc._texts[cid] = text
    sites = sc._metrics("A1_sites", ps, {})["sites"]
    img, dis = sites["image_tier3"], sites["disambiguate"]
    assert (img["n"], img["json_n"], img["json_valid"]) == (2, 2, 2)
    assert (img["schema_n"], img["schema_accepted"]) == (0, 0), (img["schema_n"], img["schema_accepted"])
    assert (dis["n"], dis["json_n"], dis["json_valid"], dis["schema_n"], dis["schema_accepted"]) == (2, 2, 2, 2, 2)


def test_t06_other_schema_sites_unchanged():
    """T06 PIN (T2): disambiguate, vision_v1, vision_v2 and moderation schemas byte-equal to the
    base literals; every other SITES row keeps its role, cap, expects_json and schema."""
    assert router.DISAMBIGUATE_SCHEMA == DISAMBIGUATE_SCHEMA_BASE
    assert router.VISION_V1_SCHEMA == VISION_V1_SCHEMA_BASE
    assert router.MODERATION_SCHEMA == MODERATION_SCHEMA_BASE
    assert _canon(router.DISAMBIGUATE_SCHEMA) == _canon(DISAMBIGUATE_SCHEMA_BASE)
    v2 = router.SITES["vision_v2"].output_schema
    assert v2 == osvc.VISION_RESPONSE_FORMAT_V2["json_schema"]["schema"]
    assert _canon(v2) == VISION_V2_SCHEMA_SHA256, _canon(v2)
    tags = {"vision_v2": v2, "vision_v1": router.VISION_V1_SCHEMA, "disambiguate": router.DISAMBIGUATE_SCHEMA}
    assert set(router.SITES) == set(OTHER_SITES_BASE) | {"image_tier3"}
    for site, (role, cap_, ej, tag) in OTHER_SITES_BASE.items():
        spec = router.SITES[site]
        assert (spec.role, spec.claude_max_tokens, spec.expects_json) == (role, cap_, ej), site
        if tag is None:
            assert spec.output_schema is None, site
        else:
            assert spec.output_schema == tags[tag], site

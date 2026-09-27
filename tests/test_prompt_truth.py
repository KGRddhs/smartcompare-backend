"""W4-11 -- prompt truth: the verdict prompt stops contradicting itself.

Findings PO-PROMPTS-11 (status), PO-PROMPTS-05 / -06 / -10 under the new
default-OFF flag ENABLE_VERDICT_PROMPT_TRUTH (ruling R1), plus the prompt
render-digest byte-identity gate (rulings R13/R14).

Each test's docstring says RED (fails at the base HEAD for the stated reason),
PIN (green at base and must stay green) or XFAIL(strict). New symbols
(COMPARISON_SYSTEM_TRUTH, verdict_prompt_truth_enabled, ...) are looked up
INSIDE test bodies so a missing symbol is an assertion failure, never a
collection error. Zero network (autouse socket/DNS + curl_cffi guard); every
node clears the W4-11 flags first (ruling C11: the OFF pins stay green with the
flags exported ON). extraction_service is imported at module top (R13: its
first import runs load_dotenv).
"""
import ast
import hashlib
import ipaddress
import json
import logging
import pathlib
import re
import socket
import types

import pytest

import app.services.extraction_service as es  # noqa: E402  (R13: module-top import)
from app.services import prompt_personalities as pp  # noqa: E402
from tests import w4_11_prompt_digest_recorder as recorder  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRUTH = "ENABLE_VERDICT_PROMPT_TRUTH"
MAY_DECLINE = "ENABLE_PRICE_FALLBACK_MAY_DECLINE"
NO_FAB = "ENABLE_SPECS_NO_FABRICATION"
CATS9 = ["electronics", "grocery", "supplements", "makeup", "skincare",
         "haircare", "fragrances", "fashion", "other"]
CATS10 = CATS9 + ["unknowncat"]
M45 = {"age_group": "45+", "gender": "Male", "nationality": "Bahraini"}

# --- the ruled TRUTH wording (spec 2.5 as amended by rulings R9 / R10) -----
OFF_CONS_SENTENCE_HEAD = "NEVER return empty pros[] or cons[] arrays"
TRUTH_CONS_SENTENCE = (
    "NEVER return an empty pros[] array. Return a con ONLY when the supplied product data "
    "supports it; when the data shows no weakness for a product, an honest empty cons[] is "
    "correct. A con about MISSING DATA (\"limited information on X\", \"no details on Y\", "
    "\"no cons noted in reviews\") is NEVER acceptable -- it describes our data, not the product."
)
OFF_QUOTA = "4-6 pros, 2-4 cons per product"
TRUTH_QUOTA = "4-6 pros and up to 4 cons per product"
OFF_RULE_73 = '- NO overconfidence: if data is thin or scores are close (<5 point gap), say "marginally" or "slightly"'
TRUTH_RULE_73 = (
    '- NO overconfidence: when the supplied data is thin or the two products are close, say '
    '"marginally" or "slightly" -- describe the closeness in plain words, never as a number'
)
OFF_RULE_77 = "- If scores disagree with your intuition, explain why (do not silently ignore scores)"
# R9: scores FIX the winner, facts JUSTIFY it, scores are never output text.
TRUTH_RULE_77 = (
    "- The winner is set by the supplied scoring context; justify it with the product facts "
    "that support it, and never mention, quote or allude to the scores themselves"
)
SCORES_CONSISTENCY_SENTENCE = "Your verdict MUST be consistent with the scores above."
TRUTH_REASONING = {
    "grocery": "Lead with ingredient quality and nutritional differences when the supplied product data carries them; otherwise lead with what the data does support. Health implications over taste unless products are nutritionally similar.",
    "supplements": "Lead with ingredient forms and dosages when the supplied product data carries them; otherwise lead with what the data does support. Distinguish clinical doses from marketing doses. Safety first, then efficacy.",
    "makeup": "Lead with real-world performance (wear time, shade inclusivity, skin compatibility) when the supplied product data carries it; otherwise lead with what the data does support. Specs are secondary to experience.",
    "skincare": "Lead with active ingredient analysis (what actives, what concentration, what form) when the supplied product data carries it; otherwise lead with what the data does support. Then discuss compatibility and evidence of results.",
    "haircare": "Lead with hair type compatibility and expected results when the supplied product data carries them; otherwise lead with what the data does support. Ingredients matter but outcomes matter more.",
    "fragrances": "Lead with scent description and character when the supplied product data carries them; otherwise lead with what the data does support. Longevity and projection are decisive only when the supplied product data states them. Price is secondary to the experience.",
    "fashion": "Lead with material quality and craftsmanship, then fit and style, when the supplied product data carries them; otherwise lead with what the data does support. For luxury items, brand heritage and authenticity matter.",
    "other": "Lead with how well each product fulfills its core purpose when the supplied product data shows it; otherwise lead with what the data does support. Balance specs with user reviews when category-specific expertise is limited.",
}
# The four digests the unflagged fences MUST move (T-G1); everything else equal.
FENCE_KEYS = ("targeted_system", "targeted_user", "url_extract_user", "image_tier3_user")


# ---------------------------------------------------------------------------
# autouse: zero network + clean W4-11 flags
# ---------------------------------------------------------------------------
def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    if host in ("localhost", "testserver", "testclient", "test", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _addr_ok(address) -> bool:
        if isinstance(address, (str, bytes)):
            return True
        if isinstance(address, tuple) and address:
            return _is_loopback_host(address[0])
        return False

    def guarded_connect(self, address):
        if not _addr_ok(address):
            attempts.append(("connect", repr(address)))
            raise OSError(f"W4-11 zero-network guard: connect {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        if not _addr_ok(address):
            attempts.append(("connect_ex", repr(address)))
            raise OSError(f"W4-11 zero-network guard: connect_ex {address!r}")
        return real_connect_ex(self, address)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise socket.gaierror(f"W4-11 zero-network guard: {host!r}")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    try:
        import curl_cffi.requests as _cc

        def _no_curl(*a, **kw):
            attempts.append(("curl_cffi.requests.get", repr(a[:1])))
            raise OSError("W4-11 zero-network guard: curl_cffi.requests.get")
        monkeypatch.setattr(_cc, "get", _no_curl)
    except ImportError:  # pragma: no cover - curl_cffi is pinned in CI
        pass
    yield attempts
    assert not attempts, f"test attempted network access: {attempts!r}"


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in recorder.FLAGS:
        monkeypatch.delenv(name, raising=False)
    yield


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _render(cat, cohort=None, quality="normal"):
    return es.build_verdict_prompt([{}, {}], quality, cohort, cat)


def _need(module, name):
    obj = getattr(module, name, None)
    assert obj is not None, f"{module.__name__}.{name} does not exist (W4-11 not implemented)"
    return obj


def _enc():
    from tests._tokenizer import encoding_for_model_or_skip

    return encoding_for_model_or_skip("gpt-4o-mini")


# ===========================================================================
# PO-PROMPTS-11 -- status
# ===========================================================================
_SPECS_LICENCES = ("you MUST attempt to provide a value", "fall back to your training data",
                   "a snippet or your training data", "AND your training data")


@pytest.mark.xfail(strict=True, reason=(
    "PO-PROMPTS-11: the shipped CODE default of ENABLE_SPECS_NO_FABRICATION is OFF, so the "
    "fabricating specs prefix ships. NOT permanent (ruling R6): the planned end state is to "
    "retire the flag once the Railway flip is proven, making the evidence-only prefix the code "
    "default -- remove this marker in that change (it then XPASSes and strict=True fails it)."))
def test_shipped_prompt_does_not_license_training_data(monkeypatch):
    """T-S1 XFAIL(strict): renders the specs system prompt at the shipped CODE default
    (flag delenv'd) for all 9 categories; none of the four training-data licences may appear."""
    monkeypatch.delenv(NO_FAB, raising=False)
    hits = []
    for cat in CATS9:
        system = es._build_specs_prompt("Apple", "iPhone 17", "256GB", cat, "[snippet_1] x")["system"]
        hits += [(cat, m) for m in _SPECS_LICENCES if m in system]
    assert not hits, f"training-data licences in the shipped specs prompt: {hits[:4]}"


@pytest.mark.parametrize("state", ["unset", "true"])
def test_specs_render_digests_both_states(monkeypatch, state):
    """T-S2 PIN: the 9 specs system renders equal the base fixture in both NO_FAB states."""
    fx = recorder.load_fixture()
    key = "specs_system_off"
    if state == "true":
        monkeypatch.setenv(NO_FAB, "true")
        key = "specs_system_on"
    got = {c: _sha(es._build_specs_prompt("Apple", "iPhone 17", "256GB", c, "[snippet_1] x")["system"])
           for c in CATS9}
    assert got == fx[key]


# ===========================================================================
# PO-PROMPTS-05 / -06 / -10 -- ENABLE_VERDICT_PROMPT_TRUTH
# ===========================================================================
_CONTRADICTIONS = ("If scores disagree with your intuition", "do not silently ignore scores",
                   "point gap", "follow the product facts", "disagree with your reading")


def _scoring_summary():
    from app.services.scoring_service import get_scoring_service

    svc = get_scoring_service()
    products = [
        {"name": "iPhone 17", "brand": "Apple", "category": "electronics",
         "specs": {"battery": "3500 mAh", "storage": "256GB", "display": "6.1 inch"},
         "price": {"amount": 350.0, "currency": "BHD"},
         "reviews": {"average_rating": 4.6, "total_reviews": 1200}},
        {"name": "Galaxy S25", "brand": "Samsung", "category": "electronics",
         "specs": {"battery": "4000 mAh", "storage": "256GB", "display": "6.2 inch"},
         "price": {"amount": 320.0, "currency": "BHD"},
         "reviews": {"average_rating": 4.4, "total_reviews": 900}},
    ]
    result = svc.compute_scores(products)
    return products, svc.build_scores_summary(result, ["Apple iPhone 17", "Samsung Galaxy S25"])


async def _verdict_call(monkeypatch, p1, p2, scores_summary, content='{"winner_index": 0}',
                        category="electronics"):
    from app.services.model_router_service import model_router

    async def _gm(priority="standard"):
        return "gpt-4o"

    async def _ru(model, tokens):
        return None

    calls = []
    monkeypatch.setattr(model_router, "get_model", _gm)
    monkeypatch.setattr(model_router, "record_usage", _ru)
    monkeypatch.setattr(es, "get_client", lambda *a, **k: recorder.fake_client(calls, content))
    parsed, _ = await es.generate_comparison(p1, p2, "bahrain", category=category,
                                             scores_summary=scores_summary)
    assert calls, "generate_comparison made no OpenAI call"
    return calls[0], parsed


@pytest.mark.asyncio
async def test_truth_on_no_score_rule_contradiction(monkeypatch):
    """T-D1 RED (PO-PROMPTS-06, rulings R9/C1): flag true -- every category render keeps
    'NEVER mention internal scores', carries the R9 rule (scores fix the winner, facts justify
    it, scores never output) and none of the contradicting phrasings; and the SENT verdict
    system prompt (through generate_comparison with a real build_scores_summary block) carries
    BOTH the R9 rule and the scoring block's consistency sentence with no contradiction.
    Base: the flag does not exist, 10/10 renders carry the ':77' contradiction."""
    monkeypatch.setenv(TRUTH, "true")
    bad = {}
    for cat in CATS10:
        text = _render(cat)
        assert "NEVER mention internal scores" in text, f"{cat}: the :1053 ban was dropped"
        found = [m for m in _CONTRADICTIONS if m in text]
        if found or TRUTH_RULE_77 not in text:
            bad[cat] = found or ["R9 rule absent"]
    assert not bad, f"TRUTH renders still contradict the score rules: {bad}"
    products, summary = _scoring_summary()
    assert summary, "precondition: build_scores_summary returned an empty block"
    call, _ = await _verdict_call(monkeypatch, products[0], products[1], summary)
    system = call["messages"][0]["content"]
    assert SCORES_CONSISTENCY_SENTENCE in system, "precondition: the scoring block's consistency sentence is absent"
    assert TRUTH_RULE_77 in system, "the sent verdict system lacks the R9 score rule"
    assert not [m for m in _CONTRADICTIONS if m in system], "the sent verdict system still contradicts the scoring block"


def test_truth_on_cons_rule_is_evidence_conditional(monkeypatch):
    """T-D2 RED (PO-PROMPTS-05, ruling R10/C2): flag true -- the empty-cons ban and the
    '2-4 cons' quota are gone, 'up to 4 cons' and the evidence-conditional cons sentence are
    present, the empty-PROS ban stays. Base: 10/10 renders carry the old rule."""
    monkeypatch.setenv(TRUTH, "true")
    for cat in CATS10:
        text = _render(cat)
        assert OFF_CONS_SENTENCE_HEAD not in text, f"{cat}: 'NEVER return empty pros[] or cons[]' still rendered"
        assert "2-4 cons" not in text, f"{cat}: the '2-4 cons' quota survived the TRUTH swap"
        assert TRUTH_QUOTA in text, f"{cat}: 'up to 4 cons' quota absent"
        assert "NEVER return an empty pros[] array" in text, f"{cat}: the empty-pros ban was lost"
        assert "describes our data, not the product" in text, f"{cat}: the data-gap cons rule is absent"


def test_truth_on_every_reasoning_style_is_evidence_conditional(monkeypatch):
    """T-D3 RED (PO-PROMPTS-10): flag true -- every category's rendered 'Reasoning approach:'
    line carries the #111 evidence conditional; the TRUTH reasoning_style strings are exactly
    the spec's, pairwise distinct, makeup keeps 'wear', fragrances no longer calls longevity
    'the decisive metrics'. Base: 1/9 conditional (electronics only)."""
    monkeypatch.setenv(TRUTH, "true")
    missing = []
    for cat in CATS9:
        block = pp.build_personality_prompt(cat)
        line = next((ln for ln in block.splitlines() if "Reasoning approach:" in ln), "")
        if "when the supplied product data" not in line:
            missing.append(cat)
        if "when the supplied product data" not in _render(cat).split("Reasoning approach:", 1)[-1].splitlines()[0]:
            missing.append(cat + "(verdict)")
    assert not missing, f"reasoning_style not evidence-conditional under TRUTH: {missing}"
    truth_dict = _need(pp, "CATEGORY_PROMPT_PERSONALITIES_TRUTH")
    styles = {c: truth_dict[c]["reasoning_style"] for c in CATS9}
    for cat, want in TRUTH_REASONING.items():
        assert styles[cat] == want, f"{cat}: TRUTH reasoning_style differs from the ruled string"
    assert styles["electronics"] == pp.CATEGORY_PROMPT_PERSONALITIES["electronics"]["reasoning_style"]
    assert len(set(styles.values())) == 9, "TRUTH reasoning_style strings are not pairwise distinct"
    assert "wear" in styles["makeup"]
    assert "the decisive metrics" not in styles["fragrances"]


def test_truth_on_unknown_category_falls_back_to_truth_other(monkeypatch):
    """T-D3b PIN (fixer; adversary mutant N3): flag true -- a category outside the 9 falls
    back to the TRUTH 'other' personality (never the OFF one), both in the personality block
    (flag read, and truth=True passed) and in the rendered verdict system prompt."""
    monkeypatch.setenv(TRUTH, "true")
    off_other = pp.CATEGORY_PROMPT_PERSONALITIES["other"]["reasoning_style"]
    assert off_other != TRUTH_REASONING["other"]
    for block in (pp.build_personality_prompt("unknowncat"),
                  pp.build_personality_prompt("unknowncat", truth=True),
                  _render("unknowncat")):
        line = next((ln for ln in block.split("Reasoning approach:", 1)[-1].splitlines()), "")
        assert line.strip() == TRUTH_REASONING["other"], f"unknown category fell back to {line.strip()!r}"
        assert off_other not in block, "the OFF 'other' reasoning_style leaked into a TRUTH render"


@pytest.mark.parametrize("state", ["unset", "false"])
def test_truth_off_verdict_renders_byte_identical(monkeypatch, state):
    """T-D4 PIN: flag unset AND "false" -- all 90 build_verdict_prompt renders and the 10
    personality blocks equal the base fixture (the OFF objects are literally not edited)."""
    if state == "false":
        monkeypatch.setenv(TRUTH, "false")
    fx = recorder.load_fixture()
    got = {}
    for cat in recorder.CATS:
        for cname, coh in recorder.COHORTS.items():
            for q in recorder.QUALITIES:
                got[f"{cat}|{cname}|{q}"] = _sha(es.build_verdict_prompt([{}, {}], q, coh, cat))
    diff = [k for k in fx["verdict_system"] if fx["verdict_system"][k] != got.get(k)]
    assert not diff, f"{len(diff)} verdict renders moved with the flag {state}: {diff[:5]}"
    pers = {c: _sha(pp.build_personality_prompt(c)) for c in recorder.CATS}
    assert pers == fx["personality"]


def test_truth_on_prefix_static_and_cacheable(monkeypatch):
    """T-D5 RED (constant absent at base), then PIN: flag true -- every render starts with
    COMPARISON_SYSTEM_TRUTH; with the 45+/Male cohort the first divergence from the no-cohort
    render is at or after the static per-category block (TRUTH base + TRUTH personality +
    exemplars); the common prefix is >= 1,024 tokens (OpenAI prompt-cache eligible)."""
    monkeypatch.setenv(TRUTH, "true")
    base_truth = _need(es, "COMPARISON_SYSTEM_TRUTH")
    from app.services.verdict_exemplar_loader import build_exemplar_block

    enc = _enc()
    for cat in CATS10:
        a = _render(cat)
        b = _render(cat, M45)
        assert a.startswith(base_truth), f"{cat}: TRUTH render does not start with COMPARISON_SYSTEM_TRUTH"
        static = base_truth + pp.build_personality_prompt(cat, truth=True) + build_exemplar_block(cat)
        assert a.startswith(static), f"{cat}: the static per-category block is not the render's prefix"
        n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        assert n >= len(static), f"{cat}: the cohort text diverges inside the static block ({n} < {len(static)})"
        assert len(enc.encode(a[:n])) >= 1024, f"{cat}: cohort-invariant prefix below the 1,024-token cache threshold"


@pytest.mark.parametrize("state", ["unset", "true"])
def test_hotfix_pros_rule_survives_both_states(monkeypatch, state):
    """T-D6 PIN (the Bundle C empty-pros regression guard): a 'NEVER return ... empty pros'
    rule is in every render with the flag unset and true."""
    if state == "true":
        monkeypatch.setenv(TRUTH, "true")
    pat = re.compile(r"NEVER return (an )?empty pros")
    for cat in CATS10:
        assert pat.search(_render(cat)), f"{cat}/{state}: the empty-pros ban is missing"


def test_truth_read_once_per_verdict(monkeypatch):
    """T-D7 RED (reader absent at base), then PIN (M-D5, ruling C5): the reader is patched on
    the prompt_personalities module to return True on its FIRST call and False after; one
    build_verdict_prompt call must render the TRUTH COMPARISON_SYSTEM AND the TRUTH
    personality block -- never a mix (build_verdict_prompt reads once and passes truth=)."""
    _need(pp, "verdict_prompt_truth_enabled")
    base_truth = _need(es, "COMPARISON_SYSTEM_TRUTH")
    seq = iter([True])
    monkeypatch.setattr(pp, "verdict_prompt_truth_enabled", lambda: next(seq, False))
    text = _render("fragrances")
    assert text.startswith(base_truth), "the first read (True) did not select COMPARISON_SYSTEM_TRUTH"
    assert TRUTH_RULE_77 in text and OFF_RULE_77 not in text, "mixed state: TRUTH base with the OFF trust rules"
    assert TRUTH_REASONING["fragrances"] in text, "mixed state: TRUTH base with the OFF personality"


def _readers():
    return [("verdict_prompt_truth_enabled", pp, TRUTH),
            ("price_fallback_may_decline_enabled", es, MAY_DECLINE)]


@pytest.mark.parametrize("name,module,env", _readers(), ids=["truth", "may_decline"])
def test_new_flag_readers_idiom(monkeypatch, name, module, env):
    """T-R1 RED (readers absent at base), then PIN (M-D4): the house idiom -- TRUE, ' true ',
    On, 1, yes -> True; unset, '', false, 0, no -> False; read per call."""
    reader = _need(module, name)
    for v in ("TRUE", " true ", "On", "1", "yes"):
        monkeypatch.setenv(env, v)
        assert reader() is True, f"{name}({v!r}) should be True"
    for v in ("", "false", "0", "no"):
        monkeypatch.setenv(env, v)
        assert reader() is False, f"{name}({v!r}) should be False"
    monkeypatch.delenv(env, raising=False)
    assert reader() is False
    monkeypatch.setenv(env, "true")
    assert reader() is True, "the reader is not read per call"


def test_truth_objects_differ_from_off_twins_only_at_intended_strings():
    """T-D8 RED (objects absent at base), then PIN (ruling R11/C3): imports prompt_personalities
    DIRECTLY and diffs each TRUTH object against its untouched OFF twin -- they differ ONLY at
    the ruled strings (the OFF objects are literally not edited)."""
    utr_t = _need(pp, "UNIVERSAL_TRUST_RULES_TRUTH")
    assert pp.UNIVERSAL_TRUST_RULES.count(OFF_RULE_73) == 1 and pp.UNIVERSAL_TRUST_RULES.count(OFF_RULE_77) == 1
    assert utr_t == pp.UNIVERSAL_TRUST_RULES.replace(OFF_RULE_73, TRUTH_RULE_73).replace(OFF_RULE_77, TRUTH_RULE_77)
    cpp_t = _need(pp, "CATEGORY_PROMPT_PERSONALITIES_TRUTH")
    assert set(cpp_t) == set(pp.CATEGORY_PROMPT_PERSONALITIES)
    for cat, off in pp.CATEGORY_PROMPT_PERSONALITIES.items():
        t = cpp_t[cat]
        assert set(t) == set(off)
        assert {k: v for k, v in t.items() if k != "reasoning_style"} == \
            {k: v for k, v in off.items() if k != "reasoning_style"}, f"{cat}: a non-reasoning field moved"
    cs_t = _need(es, "COMPARISON_SYSTEM_TRUTH")
    off = es.COMPARISON_SYSTEM
    start = off.index(OFF_CONS_SENTENCE_HEAD)
    end = off.index("BECAUSE they want to see them.", start) + len("BECAUSE they want to see them.")
    assert cs_t == off[:start].replace(OFF_QUOTA, TRUTH_QUOTA) + TRUTH_CONS_SENTENCE + off[end:], (
        "COMPARISON_SYSTEM_TRUTH differs from COMPARISON_SYSTEM beyond the cons sentence + quota swap"
    )


def test_truth_derivation_fails_loudly(monkeypatch):
    """T-D9 RED (ruling R11): a bad prompt edit must fail the deploy, never silently drop the
    personality block. (a) prompt_personalities' TRUTH derivation raises RuntimeError when an
    OFF sentence it swaps is edited (exec of a mutated copy of its source); (b) extraction_service
    imports prompt_personalities at MODULE TOP LEVEL outside any try (so that RuntimeError
    reaches extraction_service's import) and derives COMPARISON_SYSTEM_TRUTH under a module-level
    `raise RuntimeError` guarded by a `.count(` check; (c) no module-level `assert` in either
    file (python -O strips it)."""
    src = (ROOT / "app/services/prompt_personalities.py").read_text(encoding="utf-8")
    assert "UNIVERSAL_TRUST_RULES_TRUTH" in src, "prompt_personalities has no TRUTH derivation"
    mutated = src.replace("explain why (do not silently ignore scores)", "explain why (edited)", 1)
    assert mutated != src
    mod = types.ModuleType("_w411_pp_mutant")
    with pytest.raises(RuntimeError):
        exec(compile(mutated, "prompt_personalities_mutant.py", "exec"), mod.__dict__)  # noqa: S102
    es_tree = ast.parse((ROOT / "app/services/extraction_service.py").read_text(encoding="utf-8"))
    top_imports = [n for n in es_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
                   and "prompt_personalities" in ast.unparse(n)]
    assert top_imports, "extraction_service does not import prompt_personalities at module top level"

    def _loud_guard(tree):
        for n in tree.body:
            if isinstance(n, ast.If) and ".count(" in ast.unparse(n.test):
                if any(isinstance(x, ast.Raise) and "RuntimeError" in ast.unparse(x) for x in ast.walk(n)):
                    return True
        return False

    assert _loud_guard(es_tree), "COMPARISON_SYSTEM_TRUTH has no module-level count-checked RuntimeError"
    pp_tree = ast.parse(src)
    assert _loud_guard(pp_tree) or any(
        isinstance(n, ast.FunctionDef) and any(isinstance(x, ast.Raise) and "RuntimeError" in ast.unparse(x)
                                               for x in ast.walk(n)) for n in pp_tree.body
    ), "prompt_personalities' TRUTH derivation has no RuntimeError"
    for tree, name in ((es_tree, "extraction_service"), (pp_tree, "prompt_personalities")):
        asserts = [n for n in tree.body if isinstance(n, ast.Assert)]
        assert not asserts, f"{name} uses a module-level assert (stripped under python -O)"


@pytest.mark.parametrize("src,old,count", [("keep x", "y", 0), ("x x", "x", 2)], ids=["zero", "duplicate"])
def test_truth_swap_requires_exactly_one_match(src, old, count):
    """T-D9b PIN (fixer; adversary mutant N17, ruling R19 'exactly once'): the count-checked
    swap raises RuntimeError on zero matches AND on a duplicated anchor (a `n < 1` check
    would silently replace both copies); one match swaps."""
    with pytest.raises(RuntimeError, match=f"matched {count} times"):
        pp._truth_swap(src, old, "z", "probe")
    assert pp._truth_swap("a x b", "x", "z", "probe") == "a z b"
    if count == 2:
        # the real derivation: an OFF rule duplicated in UNIVERSAL_TRUST_RULES fails the import
        mutated = (ROOT / "app/services/prompt_personalities.py").read_text(encoding="utf-8").replace(
            OFF_RULE_77, OFF_RULE_77 + "\n" + OFF_RULE_77, 1)
        with pytest.raises(RuntimeError, match="matched 2 times"):
            exec(compile(mutated, "prompt_personalities_dup.py", "exec"),  # noqa: S102
                 types.ModuleType("_w411_dup").__dict__)


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["true", "unset"])
async def test_truth_cons_counter_logged_only_under_flag(monkeypatch, caplog, state):
    """T-D10 RED (ruling R12/C10): under the TRUTH flag one INFO line
    '[VERDICT_TRUTH] cons empty=<n> data_gap=<n>' counts empty cons arrays and data-gap cons
    ('limited information', 'no details on', 'no cons noted'); flag OFF logs nothing new.
    Base: no counter exists."""
    if state == "true":
        monkeypatch.setenv(TRUTH, "true")
    verdict = {"winner_index": 0, "product_0_pros": ["OLED display"], "product_0_cons": [],
               "product_1_pros": ["Bigger battery"],
               "product_1_cons": ["Limited information on battery life", "Heavier body"]}
    p1 = {"name": "iPhone 17", "brand": "Apple", "category": "electronics", "specs": {"battery": "3500 mAh"}}
    p2 = {"name": "Galaxy S25", "brand": "Samsung", "category": "electronics", "specs": {"battery": "4000 mAh"}}
    caplog.set_level(logging.INFO, logger=es.logger.name)
    await _verdict_call(monkeypatch, p1, p2, None, content=json.dumps(verdict))
    lines = [r.getMessage() for r in caplog.records if "[VERDICT_TRUTH]" in r.getMessage()]
    if state == "true":
        assert lines == ["[VERDICT_TRUTH] cons empty=1 data_gap=1"], f"TRUTH cons counter: {lines}"
    else:
        assert lines == [], f"flag OFF logged a TRUTH counter: {lines}"


_COUNTER_CASES = [
    # (id, product_0_cons (or "<missing>"), product_1_cons, expected line)
    ("limited_information", ["LIMITED INFORMATION about the warranty"], ["Heavier body"], "empty=0 data_gap=1"),
    ("no_details_on", ["No details on water resistance"], ["Heavier body"], "empty=0 data_gap=1"),
    ("no_cons_noted", ["No cons noted in reviews"], ["Heavier body"], "empty=0 data_gap=1"),
    ("missing", "<missing>", ["Heavier body"], "empty=1 data_gap=0"),
    ("empty_list", [], ["Heavier body"], "empty=1 data_gap=0"),
    # fixer: a model that returns one bare string instead of a list is still counted
    ("string_data_gap", "Limited information on battery", ["Heavier body"], "empty=0 data_gap=1"),
    ("string_plain", "Heavier body", ["Heavier body"], "empty=0 data_gap=0"),
    # fixer round 2 (adversary r1, Q7): every FALSY cons value counts as empty -- a JSON null
    # and an empty bare string as well as a missing key and [] (the counter's `if not _cons`).
    ("null", None, ["Heavier body"], "empty=1 data_gap=0"),
    ("empty_string", "", ["Heavier body"], "empty=1 data_gap=0"),
    # fixer round 2 (adversary r1, Q6): non-string items in a model cons list are skipped by
    # the counter, never searched -- the verdict must survive them (the row below also asserts
    # parsed has no 'error'); only the string item is matched.
    ("non_string_items", [{"text": "Limited information"}, None, 7, "Limited information on the strap"],
     ["Heavier body"], "empty=0 data_gap=1"),
    # fixer round 3 (polish ruling R27a; adversary r2 mutant X1): data_gap counts PER STRING
    # (R18), not per side -- two data-gap strings on ONE side count 2.
    ("two_gaps_one_side", ["Limited information on battery", "No details on water resistance", "Heavier body"],
     ["Heavier body"], "empty=0 data_gap=2"),
    # Fable, after adversary r3 (mutant E3): PER STRING also means a string carrying TWO
    # phrases counts ONCE -- never per regex match.
    ("two_phrases_one_string", ["Limited information on battery; no details on the strap"],
     ["Heavier body"], "empty=0 data_gap=1"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("p0_cons,p1_cons,want", [c[1:] for c in _COUNTER_CASES],
                         ids=[c[0] for c in _COUNTER_CASES])
async def test_truth_cons_counter_vocabulary_per_phrase(monkeypatch, caplog, p0_cons, p1_cons, want):
    """T-D10b PIN (red-gate ruling R18, added by the green): the counter is pinned PER
    PHRASE ('limited information', 'no details on', 'no cons noted', case-insensitive) and
    per the missing/empty pair (a missing product_i_cons key AND an empty list both count
    as empty), so dropping any one phrase or the missing-key case reddens a row."""
    monkeypatch.setenv(TRUTH, "true")
    verdict = {"winner_index": 0, "product_0_pros": ["OLED display"],
               "product_1_pros": ["Bigger battery"], "product_1_cons": p1_cons}
    if p0_cons != "<missing>":
        verdict["product_0_cons"] = p0_cons
    p1 = {"name": "iPhone 17", "brand": "Apple", "category": "electronics", "specs": {"battery": "3500 mAh"}}
    p2 = {"name": "Galaxy S25", "brand": "Samsung", "category": "electronics", "specs": {"battery": "4000 mAh"}}
    caplog.set_level(logging.INFO, logger=es.logger.name)
    _call, parsed = await _verdict_call(monkeypatch, p1, p2, None, content=json.dumps(verdict))
    assert parsed.get("error") is None, f"the TRUTH counter broke the verdict: {parsed.get('error')!r}"
    lines = [r.getMessage() for r in caplog.records if "[VERDICT_TRUTH]" in r.getMessage()]
    assert lines == [f"[VERDICT_TRUTH] cons {want}"], f"TRUTH cons counter: {lines}"


# ===========================================================================
# The byte-identity gate (rulings R13/R14)
# ===========================================================================
@pytest.mark.asyncio
async def test_render_digests_match_base_except_the_fence(monkeypatch):
    """T-G1 (R14 gate): re-run the committed recorder with every flag unset. Every key equals
    the fixture (90 verdict renders, 18 specs renders, 10 personalities, the constants, the
    benign user/system digests and every kwargs dict) EXCEPT the four unflagged-fence digests
    (targeted_system, targeted_user, url_extract_user, image_tier3_user), which must DIFFER.
    RED at base on the must-differ half only (the fences have not landed); the equality half
    is the PIN."""
    fx = recorder.load_fixture()
    got = await recorder.record(monkeypatch, _enc())
    compare = [k for k in fx if k not in recorder.METADATA_KEYS and k not in FENCE_KEYS]
    moved = [k for k in compare if fx[k] != got.get(k)]
    assert not moved, f"flag-OFF byte identity broken on: {moved}"
    still = [k for k in FENCE_KEYS if fx[k] == got.get(k)]
    assert not still, f"the unflagged fences did not land -- these digests are unchanged: {still}"

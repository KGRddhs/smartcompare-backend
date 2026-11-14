"""S95-LG URL-WINNER-GUARD: the RED rows (ENABLE_URL_WINNER_GUARD, default OFF).

Under the flag ON, ``compare_from_urls`` scores the two extracted link products
with the deterministic scorer, hands the scores summary and the scorer's winner
index to ``generate_comparison``, and after a delivered verdict runs
``reconcile_winner_prose`` on the verdict dict, so the shipped ``winner_index`` is
the scorer's and no winner-facing string names the loser. Flag OFF: the base
body, byte-identical.

Hermetic: ``extract_from_url`` (on the url_extraction_service module),
``_resolve_pair_category`` and ``generate_comparison`` (on the modules the
call-time local imports of ``compare_from_urls`` read) are patched, and the
S81-10b fragrance decision is skipped with ``fragrance_gate=None``. The scorer
and the reconcile are the REAL ones; the link products are built with the real
``normalize_product_data`` and every row that relies on the scorer's pick asserts
that pick first (a PRECONDITION), so a scorer change cannot silently flip a row.
Synthetic product names and synthetic hosts only. The new predicate is read
through ``getattr`` so every RED row fails on an AssertionError at base.
"""
import asyncio
import copy
import logging

import pytest

from app.services import extraction_service as es
from app.services import llm_router
from app.services import response_builder as rb
from app.services import scoring_service as ss
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues

FLAG = "ENABLE_URL_WINNER_GUARD"
V2_FLAG = "ENABLE_URL_MODE_V2"
PROSE_FLAG = "ENABLE_WINNER_PROSE_RECONCILE"
UES_LOGGER = "app.services.url_extraction_service"
RB_LOGGER = "app.services.response_builder"
GUARD_TAG = "[URL_GUARD]"
MISMATCH_TAG = "WINNER_INDEX_MISMATCH"

ROLE_FLAG_NAMES = tuple(sorted(
    set(getattr(llm_router, "ROLE_FLAGS", {}).values())
    | {getattr(llm_router, "ESCALATION_FLAG", "ENABLE_SONNET_ESCALATION"),
       getattr(llm_router, "PRE_V3_FLAG", "ENABLE_OPENAI_PRE_V3")}
))

URL_A = "https://shop-a.example/p/synth-a-test-scent-one"
URL_B = "https://shop-b.example/p/synth-b-test-scent-two"
NAME_A = "SynthA Test Scent One"
NAME_B = "SynthB Test Scent Two"
RETAILER = {"name": "synthstore", "currency": "BHD", "key": "generic"}

# Product A: the model's favourite (a high buyer rating on a thin page).
RAW_A = {
    "title": NAME_A, "brand": "SynthA", "name": "Test Scent One",
    "price": 44.0, "currency": "BHD", "category": "fragrances", "variant": "100ml",
    "specs": {"scent_family": "woody"},
    "rating": 4.9, "review_count": 900, "in_stock": True,
}
# Product B: the scorer's pick (cheaper, with a full spec sheet).
RAW_B = {
    "title": NAME_B, "brand": "SynthB", "name": "Test Scent Two",
    "price": 38.0, "currency": "BHD", "category": "fragrances", "variant": "100ml",
    "specs": {
        "scent_family": "amber", "notes_top": "bergamot", "notes_heart": "rose",
        "notes_base": "vanilla", "longevity": "10 hours", "sillage": "strong",
        "season": "all-season", "occasion": "evening",
    },
    "rating": 4.1, "review_count": 40, "in_stock": True,
}
PAGES = {URL_A: RAW_A, URL_B: RAW_B}

# The model's verdict: it names product A (index 0) as the winner.
VERDICT_PICKS_A = {
    "winner_index": 0,
    "winner_declaration": NAME_A,
    "winner_reason": NAME_A + " has the stronger buyer rating and the bigger following.",
    "key_tradeoff": NAME_B + " costs less.",
    "specs_comparison": {
        "product_0_advantages": ["Higher buyer rating"],
        "product_1_advantages": ["Ten hour longevity"],
        "similar": ["Eau de parfum"],
    },
}
VERDICT_ERROR = {"winner_index": 0, "error": "x"}
ZERO_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}

FROZEN_KEYS = {
    "success", "products", "comparison", "winner_index", "recommendation",
    "key_differences", "category_used", "source_urls",
}

# The base golden of the delivered dict (recorded at base 731bcddf, flag OFF).
GOLDEN_PRODUCT_A = {
    "brand": "SynthA",
    "name": "Test Scent One",
    "full_name": "SynthA Test Scent One",
    "variant": "100ml",
    "category": "fragrances",
    "price": {"amount": 44.0, "currency": "BHD", "retailer": "synthstore",
              "url": "https://shop-a.example/p/synth-a-test-scent-one", "in_stock": True},
    "specs": {"scent_family": "woody"},
    "reviews": {"rating": 4.9, "count": 900},
    "image_url": None,
    "source_url": "https://shop-a.example/p/synth-a-test-scent-one",
    "retailer": {"name": "synthstore", "currency": "BHD", "key": "generic"},
}
GOLDEN_PRODUCT_B = {
    "brand": "SynthB",
    "name": "Test Scent Two",
    "full_name": "SynthB Test Scent Two",
    "variant": "100ml",
    "category": "fragrances",
    "price": {"amount": 38.0, "currency": "BHD", "retailer": "synthstore",
              "url": "https://shop-b.example/p/synth-b-test-scent-two", "in_stock": True},
    "specs": {"scent_family": "amber", "notes_top": "bergamot", "notes_heart": "rose",
              "notes_base": "vanilla", "longevity": "10 hours", "sillage": "strong",
              "season": "all-season", "occasion": "evening"},
    "reviews": {"rating": 4.1, "count": 40},
    "image_url": None,
    "source_url": "https://shop-b.example/p/synth-b-test-scent-two",
    "retailer": {"name": "synthstore", "currency": "BHD", "key": "generic"},
}
GOLDEN_COMPARISON = {
    "winner_index": 0,
    "winner_declaration": "SynthA Test Scent One",
    "winner_reason": "SynthA Test Scent One has the stronger buyer rating and the bigger following.",
    "key_tradeoff": "SynthB Test Scent Two costs less.",
    "specs_comparison": {
        "product_0_advantages": ["Higher buyer rating"],
        "product_1_advantages": ["Ten hour longevity"],
        "similar": ["Eau de parfum"],
    },
}
GOLDEN_DELIVERED = {
    False: {
        "success": True,
        "products": [GOLDEN_PRODUCT_A, GOLDEN_PRODUCT_B],
        "comparison": GOLDEN_COMPARISON,
        "winner_index": 0,
        "recommendation": "",
        "key_differences": [],
        "category_used": "fragrances",
        "source_urls": ["https://shop-a.example/p/synth-a-test-scent-one",
                        "https://shop-b.example/p/synth-b-test-scent-two"],
    },
    True: {
        "success": True,
        "products": [GOLDEN_PRODUCT_A, GOLDEN_PRODUCT_B],
        "comparison": GOLDEN_COMPARISON,
        "winner_index": 0,
        "recommendation": "SynthA Test Scent One has the stronger buyer rating and the bigger following.",
        "key_differences": ["Higher buyer rating", "Ten hour longevity"],
        "category_used": "fragrances",
        "source_urls": ["https://shop-a.example/p/synth-a-test-scent-one",
                        "https://shop-b.example/p/synth-b-test-scent-two"],
    },
}
GOLDEN_VERDICT_CALL = (
    (GOLDEN_PRODUCT_A, GOLDEN_PRODUCT_B, "bahrain"),
    {"category": "fragrances"},
)


class SyntheticScorerFault(RuntimeError):
    """The synthetic scorer failure of G3 / the P1 tripwire."""


# ---------------------------------------------------------------- helpers


def _predicate():
    fn = getattr(ues, "url_winner_guard_enabled", None)
    assert callable(fn), "url_extraction_service.url_winner_guard_enabled is missing"
    return fn


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in (FLAG, V2_FLAG, PROSE_FLAG) + ROLE_FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def _normalized(raw, url, v2):
    return ues.normalize_product_data(copy.deepcopy(raw), dict(RETAILER), url, url_mode_v2=v2)


def _written_back(v2=False):
    products = [_normalized(RAW_A, URL_A, v2), _normalized(RAW_B, URL_B, v2)]
    for product in products:
        product["category"] = "fragrances"
    return products


def _scorer_view(v2=False):
    """The REAL scorer on the written-back pair: (result, names, summary)."""
    products = _written_back(v2)
    service = ss.ScoringService()
    result = service.compute_scores([dict(p, rating=p["reviews"]["rating"], review_count=p["reviews"]["count"]) for p in copy.deepcopy(products)])
    names = scs._display_product_names(products)
    return result, names, service.build_scores_summary(result, names)


def _assert_scorer_picks_b(v2=False):
    result, names, summary = _scorer_view(v2)
    assert result.get("winner_index") == 1, (
        "PRECONDITION: the real scorer must pick product index 1 on the synthetic pair "
        "(got %r); re-pick the fixture" % (result.get("winner_index"),))
    assert names == [NAME_A, NAME_B], "PRECONDITION: display names %r" % (names,)
    assert isinstance(summary, str) and summary, "PRECONDITION: an empty scores summary"
    return result, names, summary


class _VerdictRecorder:
    """The generate_comparison double: records each call, returns (verdict, usage)."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
        return copy.deepcopy(self.verdict), dict(ZERO_USAGE)


class _CallThrough:
    """A call-counting wrapper around a real callable."""

    def __init__(self, real):
        self.real = real
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.real(*args, **kwargs)


def _install(monkeypatch, verdict):
    async def _fake_extract(url, url_mode_v2=False):
        return {"success": True, "product": _normalized(PAGES[url], url, url_mode_v2)}

    async def _fake_resolve(*_args, **_kwargs):
        return "fragrances", False, "fragrances"

    recorder = _VerdictRecorder(verdict)
    monkeypatch.setattr(ues, "extract_from_url", _fake_extract)
    monkeypatch.setattr(scs, "_resolve_pair_category", _fake_resolve)
    monkeypatch.setattr(es, "generate_comparison", recorder)
    return recorder


def _wrap_reconcile(monkeypatch):
    wrapper = _CallThrough(rb.reconcile_winner_prose)
    monkeypatch.setattr(rb, "reconcile_winner_prose", wrapper)
    monkeypatch.setattr(ues, "reconcile_winner_prose", wrapper, raising=False)
    return wrapper


def _run(v2=False):
    return asyncio.run(ues.compare_from_urls(URL_A, URL_B, url_mode_v2=v2, fragrance_gate=None))


def _capture(caplog):
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger=UES_LOGGER)
    caplog.set_level(logging.INFO, logger=RB_LOGGER)


def _guard_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith(GUARD_TAG)]


def _mismatch_records(caplog):
    return [r for r in caplog.records
            if r.name == RB_LOGGER and r.getMessage().startswith(MISMATCH_TAG)]


def _guard_on(monkeypatch, v2=False):
    monkeypatch.setenv(FLAG, "true")
    _set(monkeypatch, V2_FLAG, "true" if v2 else None)
    monkeypatch.delenv(PROSE_FLAG, raising=False)


# ---------------------------------------------------------------- RED rows


def test_g1_on_ships_the_scorer_winner_and_drops_the_model_prose(monkeypatch, caplog):
    """G1: ON; the scorer picks index 1, the model picks 0 with a declaration and a
    reason naming product 0 -> winner_index 1 (delivered and comparison), the model's
    declaration and reason are gone, ONE WINNER_INDEX_MISMATCH record."""
    _assert_scorer_picks_b()
    _guard_on(monkeypatch)
    _capture(caplog)
    _install(monkeypatch, VERDICT_PICKS_A)
    out = _run()
    assert set(out) == FROZEN_KEYS, sorted(out)
    assert out["success"] is True
    assert out["winner_index"] == 1, "the shipped winner_index is not the scorer's"
    comparison = out["comparison"]
    assert comparison["winner_index"] == 1, "comparison.winner_index is not the scorer's"
    assert comparison.get("winner_declaration") == "", comparison.get("winner_declaration")
    assert comparison.get("key_tradeoff") == "", comparison.get("key_tradeoff")
    assert comparison.get("winner_reason") == rb._QUALITATIVE_WINNER_REASON(NAME_B), (
        comparison.get("winner_reason"))
    for field in ("winner_declaration", "winner_reason", "key_tradeoff"):
        assert NAME_A not in (comparison.get(field) or ""), field
    assert len(_mismatch_records(caplog)) == 1, [r.getMessage() for r in _mismatch_records(caplog)]


def test_g2_on_passes_the_scores_summary_and_the_scorer_winner(monkeypatch):
    """G2: ON -> the verdict call carries a non-empty str scores_summary (the
    scorer's) and score_winner_index equal to the scorer's int."""
    result, _names, summary = _assert_scorer_picks_b()
    _guard_on(monkeypatch)
    recorder = _install(monkeypatch, VERDICT_PICKS_A)
    _run()
    assert len(recorder.calls) == 1, len(recorder.calls)
    args, kwargs = recorder.calls[0]
    assert args == GOLDEN_VERDICT_CALL[0]
    assert set(kwargs) == {"category", "scores_summary", "score_winner_index"}, sorted(kwargs)
    assert kwargs["category"] == "fragrances"
    assert isinstance(kwargs["scores_summary"], str) and kwargs["scores_summary"]
    assert kwargs["scores_summary"] == summary
    assert type(kwargs["score_winner_index"]) is int
    assert kwargs["score_winner_index"] == result["winner_index"] == 1


def test_g3_on_scorer_failure_is_unguarded_base_with_one_constant_warning(monkeypatch, caplog):
    """G3: ON, the scorer raises -> the base delivery (the model's winner), the
    verdict call carries no new keyword, the reconcile never runs, and exactly ONE
    '[URL_GUARD] scorer failed type=<type>' WARNING of constants only."""
    _guard_on(monkeypatch)
    _capture(caplog)
    recorder = _install(monkeypatch, VERDICT_PICKS_A)
    reconcile = _wrap_reconcile(monkeypatch)

    def _boom(self, *_args, **_kwargs):
        raise SyntheticScorerFault("synthetic scorer fault")

    monkeypatch.setattr(ss.ScoringService, "compute_scores", _boom)
    out = _run()
    assert out == GOLDEN_DELIVERED[False]
    assert [(a, k) for a, k in recorder.calls] == [GOLDEN_VERDICT_CALL]
    assert reconcile.calls == 0
    assert _mismatch_records(caplog) == []
    guard = _guard_records(caplog)
    assert [r.getMessage() for r in guard] == ["[URL_GUARD] scorer failed type=SyntheticScorerFault"], (
        [r.getMessage() for r in guard])
    assert guard[0].levelno == logging.WARNING
    assert guard[0].name == UES_LOGGER
    for record in guard:
        text = record.getMessage()
        for needle in ("SynthA", "SynthB", "Test Scent", "shop-a.example", "shop-b.example",
                       "synthstore", "synthetic scorer fault"):
            assert needle not in text, needle


def test_g4_on_verdict_error_is_the_coded_non_delivery_without_a_reconcile(monkeypatch, caplog):
    """G4: ON, the verdict returns {"winner_index": 0, "error": "x"} -> the coded
    LLM_UNAVAILABLE result, and the reconcile is never called (a non-delivery never
    reconciles)."""
    _guard_on(monkeypatch)
    _capture(caplog)
    _install(monkeypatch, VERDICT_ERROR)
    reconcile = _wrap_reconcile(monkeypatch)
    out = _run()
    assert out == {
        "success": False,
        "code": "LLM_UNAVAILABLE",
        "error": scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
    }
    assert reconcile.calls == 0, "the reconcile ran on a non-delivery"
    assert _mismatch_records(caplog) == []


def test_g5_on_with_url_mode_v2_the_recommendation_names_the_scorer_winner(monkeypatch):
    """G5: ON with url_mode_v2 -> the V2 recommendation (filled from the reconciled
    verdict) names the scorer's winner and not the loser."""
    _assert_scorer_picks_b(v2=True)
    _guard_on(monkeypatch, v2=True)
    _install(monkeypatch, VERDICT_PICKS_A)
    out = _run(v2=True)
    assert set(out) == FROZEN_KEYS, sorted(out)
    assert out["winner_index"] == 1
    recommendation = out["recommendation"]
    assert NAME_B in recommendation, recommendation
    assert NAME_A not in recommendation, recommendation
    assert recommendation == rb._QUALITATIVE_WINNER_REASON(NAME_B), recommendation


@pytest.mark.parametrize("value,expected", [
    ("TRUE", True), (" on ", True), ("1", True), ("yes", True),
    ("", False), ("false", False), ("0", False), ("off", False), ("garbage", False),
    (None, False),
])
def test_g6_predicate_spellings(monkeypatch, value, expected):
    """G6: url_winner_guard_enabled exists and reads the house spellings per call."""
    fn = _predicate()
    _set(monkeypatch, FLAG, value)
    assert fn() is expected, (value, fn())
    monkeypatch.setenv(FLAG, "on" if not expected else "off")
    assert fn() is (not expected), "the predicate is not read per call"


# ---------------------------------------------------------------- PIN rows


def _full_off_config(monkeypatch, guard, v2):
    _set(monkeypatch, FLAG, guard)
    monkeypatch.setenv(V2_FLAG, "true" if v2 else "false")
    monkeypatch.setenv(PROSE_FLAG, "true")
    for name in ROLE_FLAG_NAMES:
        monkeypatch.setenv(name, "true")


@pytest.mark.parametrize("v2", [False, True], ids=["v1", "v2"])
@pytest.mark.parametrize("guard", [None, "false"], ids=["unset", "false"])
def test_p1_off_full_configuration_is_byte_identical_base(monkeypatch, caplog, guard, v2):
    """P1 (B1 rule): OFF with the full configuration (ENABLE_URL_MODE_V2 in both
    states, every role flag name and the prose flag set) -> the verdict call's args
    equal base, the scorer and the reconcile are never reached (tripwires that
    record and raise), and the delivered dict equals the base golden literal."""
    _full_off_config(monkeypatch, guard, v2)
    _capture(caplog)
    recorder = _install(monkeypatch, VERDICT_PICKS_A)
    reached = []

    def _tripwire(label):
        def _hit(*_args, **_kwargs):
            reached.append(label)
            raise SyntheticScorerFault(label)
        return _hit

    monkeypatch.setattr(ss, "get_scoring_service", _tripwire("get_scoring_service"))
    monkeypatch.setattr(ues, "get_scoring_service", _tripwire("ues.get_scoring_service"),
                        raising=False)
    for method in ("compute_scores", "build_scores_summary", "compute_tradeoff_pairs"):
        monkeypatch.setattr(ss.ScoringService, method, _tripwire(method))
    monkeypatch.setattr(rb, "reconcile_winner_prose", _tripwire("reconcile_winner_prose"))
    monkeypatch.setattr(ues, "reconcile_winner_prose", _tripwire("ues.reconcile_winner_prose"),
                        raising=False)
    monkeypatch.setattr(scs, "_display_product_names", _tripwire("_display_product_names"))
    monkeypatch.setattr(ues, "_display_product_names", _tripwire("ues._display_product_names"),
                        raising=False)
    out = _run(v2=v2)
    assert reached == [], "flag OFF reached %r" % (reached,)
    assert [(a, k) for a, k in recorder.calls] == [GOLDEN_VERDICT_CALL]
    assert out == GOLDEN_DELIVERED[v2]
    assert _guard_records(caplog) == []
    assert _mismatch_records(caplog) == []


@pytest.mark.parametrize("guard", [None, "false", "off"], ids=["unset", "false", "off"])
def test_p2_off_ships_the_model_winner(monkeypatch, caplog, guard):
    """P2: OFF, the verdict disagreeing with what the REAL scorer would pick -> the
    model's winner ships (base), no reconcile record, no guard record."""
    _assert_scorer_picks_b()
    _full_off_config(monkeypatch, guard, False)
    _capture(caplog)
    _install(monkeypatch, VERDICT_PICKS_A)
    out = _run()
    assert out["winner_index"] == 0
    assert out["comparison"] == GOLDEN_COMPARISON
    assert out == GOLDEN_DELIVERED[False]
    assert _mismatch_records(caplog) == []
    assert _guard_records(caplog) == []

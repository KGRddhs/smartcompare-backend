"""S95-LG URL-WINNER-GUARD: the FIX-2 rows (GATE_S95_LG ADDENDUM 2, GL-12..GL-17).

- G9 (GL-12, adversary MAJOR-1): a cross-currency link pair (BHD 45.0 vs AED
  380.0) is NOT guarded: the deterministic scorer compares raw amounts with no
  conversion, so ON ships the base verdict call (no scorer step, no new keyword,
  no reconcile), ONE constant INFO line ``[URL_GUARD] skipped reason=currency_mismatch``
  and the model's pick, byte-equal to the flag-OFF body. G9b (PINs at HEAD
  baf67584, the guard already runs there): a BHD / BHD pair, a padded lower-case
  code against its upper-case twin and a missing amount on one side still guard.
- G10 (GL-13, m4): the lift refuses a 0, 7.5, bool or str rating and a bool or
  negative count (that key is not lifted; the other key still is). G10b (PIN at
  HEAD): the boundary values (a rating of 5 or 0.1, a count of 0 or 1) are lifted.
- G11 (GL-14, m2): a reconcile that re-indexes the verdict and then raises leaves
  the delivered body byte-equal to the flag-OFF body (the verdict as the model
  wrote it). G11b: a reconcile double that also edits nested lists before it
  raises is undone too (the snapshot is a DEEP copy).
- G12 (GL-15 / GL-16, m1 / m3; PINs at HEAD): the two warning arms under caplog
  carry constants and the type name only (never the exception text, a name or a
  host); a None scorer winner takes the scorer-failed arm (a TypeError in
  build_scores_summary) and ships the base call.

Hermetic, the RED file's patch idiom: ``extract_from_url`` on the
url_extraction_service module, ``_resolve_pair_category`` on
structured_comparison_service and ``generate_comparison`` on extraction_service
(the call-time local imports of ``compare_from_urls`` read them there); the
S81-10b fragrance decision is skipped with ``fragrance_gate=None``. The REAL
scorer and the REAL reconcile except where a row patches a failure; every row that
relies on the scorer's pick asserts that pick first (a PRECONDITION). Synthetic
product names and synthetic hosts only; every flag is set or deleted only through
monkeypatch.
"""
import asyncio
import copy
import json
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
SKIP_LINE = "[URL_GUARD] skipped reason=currency_mismatch"

ROLE_FLAG_NAMES = tuple(sorted(
    set(getattr(llm_router, "ROLE_FLAGS", {}).values())
    | {getattr(llm_router, "ESCALATION_FLAG", "ENABLE_SONNET_ESCALATION"),
       getattr(llm_router, "PRE_V3_FLAG", "ENABLE_OPENAI_PRE_V3")}
))

URL_E = "https://shop-e.example/p/synth-e-test-scent-five"
URL_F = "https://shop-f.example/p/synth-f-test-scent-six"
NAME_E = "SynthE Test Scent Five"
NAME_F = "SynthF Test Scent Six"
RETAILER = {"name": "synthstore", "currency": "BHD", "key": "generic"}
CATEGORY = "fragrances"
REGION = "bahrain"
LIFTED_KEYS = ("rating", "review_count")
FAULT_TEXTS = ("scorer fault", "reconcile fault")
NEEDLES = ("SynthE", "SynthF", "Test Scent", "shop-e.example", "shop-f.example",
           "synthstore") + FAULT_TEXTS

# Equal specs and an equal buyer rating: the pair differs in its price only.
SPECS = {
    "scent_family": "woody", "notes_top": "bergamot", "notes_heart": "rose",
    "notes_base": "vanilla", "longevity": "8 hours", "sillage": "moderate",
    "season": "all-season", "occasion": "evening",
}

# The model's verdict: it names product F (index 1) as the winner.
VERDICT_PICKS_F = {
    "winner_index": 1,
    "winner_declaration": NAME_F,
    "winner_reason": NAME_F + " is the cheaper offer for the same scent profile.",
    "key_tradeoff": NAME_E + " ships from a local store.",
    "specs_comparison": {
        "product_0_advantages": ["Local store"],
        "product_1_advantages": ["Lower price"],
        "similar": ["Eau de parfum"],
    },
}
ZERO_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}


class SyntheticScorerFault(RuntimeError):
    """The synthetic scorer failure of G12a."""


class SyntheticReconcileFault(RuntimeError):
    """The synthetic reconcile failure of G11 / G12b."""


# ---------------------------------------------------------------- helpers


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in (FLAG, V2_FLAG, PROSE_FLAG) + ROLE_FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def _raw(brand, name, amount, currency, rating, count):
    return {
        "title": brand + " " + name, "brand": brand, "name": name,
        "price": amount, "currency": currency, "category": CATEGORY, "variant": "100ml",
        "specs": dict(SPECS), "rating": rating, "review_count": count, "in_stock": True,
    }


def _pages(currency_e="BHD", amount_e=45.0, currency_f="BHD", amount_f=380.0,
           rating_e=4.5, count_e=300, rating_f=4.5, count_f=300):
    return {
        URL_E: _raw("SynthE", "Test Scent Five", amount_e, currency_e, rating_e, count_e),
        URL_F: _raw("SynthF", "Test Scent Six", amount_f, currency_f, rating_f, count_f),
    }


def _written_back(pages, v2=False):
    """The two link products as compare_from_urls holds them before the verdict:
    the real normalize_product_data, then the category write-back."""
    products = [
        ues.normalize_product_data(copy.deepcopy(pages[URL_E]), dict(RETAILER), URL_E,
                                   url_mode_v2=v2),
        ues.normalize_product_data(copy.deepcopy(pages[URL_F]), dict(RETAILER), URL_F,
                                   url_mode_v2=v2),
    ]
    for product in products:
        product["category"] = CATEGORY
    return products


def _hand_lifted(products):
    """The test's own lift for VALID fixture values, independent of the unit."""
    out = []
    for product in products:
        view = dict(product)
        view["rating"] = product["reviews"]["rating"]
        view["review_count"] = product["reviews"]["count"]
        out.append(view)
    return out


def _scorer_winner(pages):
    """The REAL scorer's pick on hand-lifted copies of the written-back pair."""
    result = ss.ScoringService().compute_scores(_hand_lifted(_written_back(pages)))
    return result.get("winner_index")


class _VerdictRecorder:
    """The generate_comparison double: records each call, returns (verdict, usage)."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
        return copy.deepcopy(self.verdict), dict(ZERO_USAGE)


def _install(monkeypatch, pages, verdict=VERDICT_PICKS_F):
    async def _fake_extract(url, url_mode_v2=False):
        return {"success": True,
                "product": ues.normalize_product_data(copy.deepcopy(pages[url]), dict(RETAILER),
                                                      url, url_mode_v2=url_mode_v2)}

    async def _fake_resolve(*_args, **_kwargs):
        return CATEGORY, False, CATEGORY

    recorder = _VerdictRecorder(verdict)
    monkeypatch.setattr(ues, "extract_from_url", _fake_extract)
    monkeypatch.setattr(scs, "_resolve_pair_category", _fake_resolve)
    monkeypatch.setattr(es, "generate_comparison", recorder)
    return recorder


def _count_seams(monkeypatch):
    """Call-through counters on every seam of the guard (the real code still runs)."""
    counts = {}

    def _function(module, name):
        real = getattr(module, name)
        counts[name] = 0

        def _through(*args, **kwargs):
            counts[name] += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(module, name, _through)

    def _method(name):
        real = getattr(ss.ScoringService, name)
        counts[name] = 0

        def _through(self, *args, **kwargs):
            counts[name] += 1
            return real(self, *args, **kwargs)

        monkeypatch.setattr(ss.ScoringService, name, _through)

    _function(ss, "get_scoring_service")
    _function(scs, "_display_product_names")
    _function(rb, "reconcile_winner_prose")
    for name in ("compute_scores", "build_scores_summary", "compute_tradeoff_pairs"):
        _method(name)
    return counts


def _spy_scorer_inputs(monkeypatch):
    """Record (a deep copy of) what the REAL compute_scores receives, then call it."""
    real = ss.ScoringService.compute_scores
    seen = []

    def _spy(self, products_data, *args, **kwargs):
        seen.append(copy.deepcopy(products_data))
        return real(self, products_data, *args, **kwargs)

    monkeypatch.setattr(ss.ScoringService, "compute_scores", _spy)
    return seen


def _run(v2=False):
    return asyncio.run(ues.compare_from_urls(URL_E, URL_F, url_mode_v2=v2, fragrance_gate=None))


def _body(out):
    return json.dumps(out, sort_keys=False, ensure_ascii=True)


def _capture(caplog):
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger=UES_LOGGER)
    caplog.set_level(logging.INFO, logger=RB_LOGGER)


def _guard_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith(GUARD_TAG)]


def _guard_lines(caplog):
    return [(r.levelno, r.name, r.getMessage()) for r in _guard_records(caplog)]


def _mismatch_records(caplog):
    return [r for r in caplog.records
            if r.name == RB_LOGGER and r.getMessage().startswith(MISMATCH_TAG)]


def _assert_constant_only(caplog):
    for record in _guard_records(caplog):
        assert not record.exc_info, "a [URL_GUARD] record carries exc_info"
        text = record.getMessage()
        for needle in NEEDLES:
            assert needle not in text, (needle, text)
    for record in caplog.records:
        for text in FAULT_TEXTS:
            assert text not in record.getMessage(), record.getMessage()


def _base_call(pages, v2=False):
    products = _written_back(pages, v2)
    return ((products[0], products[1], REGION), {"category": CATEGORY})


# ---------------------------------------------------------------- G9 (GL-12)


def test_g9_cross_currency_pair_skips_the_guard_and_ships_the_model_pick(monkeypatch, caplog):
    """G9 (RED at HEAD): ON; page E BHD 45.0 vs page F AED 380.0, equal specs and an
    equal buyer rating; the real scorer on raw amounts picks E (PRECONDITION) while
    the model picks F -> the base verdict call, no scorer step and no reconcile (call
    counters), ONE INFO line ``[URL_GUARD] skipped reason=currency_mismatch``, no
    WINNER_INDEX_MISMATCH record, and the body byte-equal to the flag-OFF body (the
    model's pick F ships)."""
    pages = _pages(currency_e="BHD", amount_e=45.0, currency_f="AED", amount_f=380.0)
    assert _scorer_winner(pages) == 0, (
        "PRECONDITION: on raw amounts the real scorer must pick the BHD page (index 0)")
    _capture(caplog)
    recorder = _install(monkeypatch, pages)
    out_off = _run()
    assert out_off["winner_index"] == 1, "PRECONDITION: the OFF body ships the model's pick"
    caplog.clear()
    monkeypatch.setenv(FLAG, "true")
    counts = _count_seams(monkeypatch)
    out_on = _run()
    assert len(recorder.calls) == 2, len(recorder.calls)
    assert recorder.calls[1] == _base_call(pages), (
        "the cross-currency verdict call is not the base call: keywords %r"
        % sorted(recorder.calls[1][1]))
    assert counts == {name: 0 for name in counts}, counts
    assert _guard_lines(caplog) == [(logging.INFO, UES_LOGGER, SKIP_LINE)], _guard_lines(caplog)
    assert _mismatch_records(caplog) == []
    assert out_on["winner_index"] == 1, out_on["winner_index"]
    assert out_on["comparison"] == VERDICT_PICKS_F
    assert _body(out_on) == _body(out_off)


@pytest.mark.parametrize("currency_e,amount_e,currency_f,amount_f", [
    ("BHD", 45.0, "BHD", 380.0),
    (" bhd ", 45.0, "BHD", 380.0),
    ("BHD", 45.0, "AED", None),
], ids=["same_code", "padded_lower_code", "missing_amount"])
def test_g9b_same_code_or_missing_amount_still_guards(monkeypatch, caplog, currency_e, amount_e,
                                                     currency_f, amount_f):
    """G9b (PIN at HEAD: the guard runs there on every pair): the same code after
    strip + upper, or a missing amount on either side -> the guard runs as before:
    the verdict call carries the scorer's summary and winner, the scorer's winner
    ships, and no skip line."""
    pages = _pages(currency_e=currency_e, amount_e=amount_e, currency_f=currency_f,
                   amount_f=amount_f)
    expected = _scorer_winner(pages)
    assert type(expected) is int, "PRECONDITION: the scorer's winner %r" % (expected,)
    monkeypatch.setenv(FLAG, "true")
    _capture(caplog)
    recorder = _install(monkeypatch, pages)
    out = _run()
    assert len(recorder.calls) == 1, len(recorder.calls)
    _args, kwargs = recorder.calls[0]
    assert set(kwargs) == {"category", "scores_summary", "score_winner_index"}, sorted(kwargs)
    assert kwargs["score_winner_index"] == expected
    assert isinstance(kwargs["scores_summary"], str) and kwargs["scores_summary"]
    assert out["winner_index"] == expected
    assert SKIP_LINE not in [line for _lvl, _name, line in _guard_lines(caplog)]


# ---------------------------------------------------------------- G10 (GL-13)


@pytest.mark.parametrize("rating_e,count_e,refused,kept,kept_value", [
    (0, 300, "rating", "review_count", 300),
    (7.5, 300, "rating", "review_count", 300),
    (True, 300, "rating", "review_count", 300),
    ("4.5", 300, "rating", "review_count", 300),
    (4.5, True, "review_count", "rating", 4.5),
    (4.5, -1, "review_count", "rating", 4.5),
], ids=["rating_zero", "rating_above_five", "rating_bool", "rating_str",
        "count_bool", "count_negative"])
def test_g10_the_lift_refuses_unreal_review_values(monkeypatch, rating_e, count_e, refused,
                                                   kept, kept_value):
    """G10 (RED at HEAD): ON; page E's nested review value is not real (a rating of
    0, 7.5, a bool or a str; a count that is a bool or negative) -> the scorer's view
    of page E does not lift that key (it stays absent) while the other key is lifted,
    and page F (real values) is lifted in full."""
    pages = _pages(rating_e=rating_e, count_e=count_e)
    monkeypatch.setenv(FLAG, "true")
    _install(monkeypatch, pages)
    seen = _spy_scorer_inputs(monkeypatch)
    _run()
    assert len(seen) == 1, len(seen)
    view_e, view_f = seen[0]
    assert refused not in view_e, (
        "the scorer's view lifted an unreal %s: %r" % (refused, view_e.get(refused)))
    assert view_e.get(kept) == kept_value, (kept, view_e.get(kept))
    assert view_f.get("rating") == 4.5 and view_f.get("review_count") == 300, (
        view_f.get("rating"), view_f.get("review_count"))


@pytest.mark.parametrize("rating_e,count_e", [(5, 0), (0.1, 1), (5.0, 2)],
                         ids=["rating_five_count_zero", "rating_small", "rating_five_float"])
def test_g10b_the_lift_keeps_the_boundary_values(monkeypatch, rating_e, count_e):
    """G10b (PIN at HEAD: HEAD lifts every non-None value): the boundary values of
    GL-13 (0 < rating <= 5, count >= 0) are lifted unchanged."""
    pages = _pages(rating_e=rating_e, count_e=count_e)
    monkeypatch.setenv(FLAG, "true")
    _install(monkeypatch, pages)
    seen = _spy_scorer_inputs(monkeypatch)
    _run()
    assert len(seen) == 1, len(seen)
    view_e = seen[0][0]
    assert view_e.get("rating") == rating_e and type(view_e.get("rating")) is type(rating_e)
    assert view_e.get("review_count") == count_e and type(view_e.get("review_count")) is int


# ---------------------------------------------------------------- G11 (GL-14)


@pytest.mark.parametrize("v2", [False, True], ids=["v1", "v2"])
def test_g11_reconcile_that_reindexes_then_raises_delivers_the_model_verdict(monkeypatch, caplog,
                                                                            v2):
    """G11 (RED at HEAD): ON with ENABLE_WINNER_PROSE_RECONCILE; the real scorer picks
    E (index 0, PRECONDITION), the model picks F; the real reconcile re-indexes the
    verdict (one WINNER_INDEX_MISMATCH record) and then raises inside
    deterministic_verdict_fields -> the delivered body is byte-equal to the flag-OFF
    body: the verdict exactly as the model wrote it (winner_index 1)."""
    pages = _pages()
    assert _scorer_winner(pages) == 0, "PRECONDITION: the real scorer must pick index 0"
    if v2:
        monkeypatch.setenv(V2_FLAG, "true")
    monkeypatch.setenv(PROSE_FLAG, "true")
    _capture(caplog)
    _install(monkeypatch, pages)
    out_off = _run(v2)
    assert out_off["winner_index"] == 1, "PRECONDITION: the OFF body ships the model's pick"
    caplog.clear()
    calls = []

    def _raise_after_reindex(*_args, **_kwargs):
        calls.append(1)
        raise SyntheticReconcileFault("synthetic reconcile fault " + NAME_E)

    monkeypatch.setattr(rb, "deterministic_verdict_fields", _raise_after_reindex)
    monkeypatch.setenv(FLAG, "true")
    out_on = _run(v2)
    assert calls == [1], "the reconcile did not reach the template step"
    assert len(_mismatch_records(caplog)) == 1, "the reconcile did not re-index first"
    assert out_on["winner_index"] == 1, out_on["winner_index"]
    assert out_on["comparison"] == VERDICT_PICKS_F, out_on["comparison"]
    assert _body(out_on) == _body(out_off)


def test_g11b_nested_edits_of_a_failed_reconcile_are_undone(monkeypatch):
    """G11b (RED at HEAD; pins the DEEP snapshot of GL-14): ON; a reconcile double
    re-indexes the verdict, edits two nested lists of it and then raises -> the
    delivered body is byte-equal to the flag-OFF body (a shallow snapshot would
    keep the nested edits)."""
    pages = _pages()
    _install(monkeypatch, pages)
    out_off = _run()
    calls = []

    def _reindex_edit_then_raise(comparison, *_args, **_kwargs):
        calls.append(1)
        comparison["winner_index"] = 0
        comparison["specs_comparison"]["similar"].append("Edited by a failed reconcile")
        comparison["specs_comparison"]["product_1_advantages"].clear()
        raise SyntheticReconcileFault("synthetic reconcile fault")

    monkeypatch.setattr(rb, "reconcile_winner_prose", _reindex_edit_then_raise)
    monkeypatch.setenv(FLAG, "true")
    out_on = _run()
    assert calls == [1], "the reconcile double was not reached"
    assert out_on["winner_index"] == 1, out_on["winner_index"]
    assert out_on["comparison"] == VERDICT_PICKS_F, out_on["comparison"]
    assert _body(out_on) == _body(out_off)


# ---------------------------------------------------------------- G12 (GL-15 / GL-16)


def test_g12a_scorer_failed_arm_logs_one_constant_warning(monkeypatch, caplog):
    """G12a (PIN at HEAD): ON, compute_scores raises with names and a host in its text
    -> exactly ONE ``[URL_GUARD] scorer failed type=SyntheticScorerFault`` WARNING on
    the module logger, no exc_info, no exception text, name or host in any record,
    and the base verdict call."""
    pages = _pages()
    monkeypatch.setenv(FLAG, "true")
    _capture(caplog)
    recorder = _install(monkeypatch, pages)

    def _boom(self, *_args, **_kwargs):
        raise SyntheticScorerFault("synthetic scorer fault " + NAME_E + " " + URL_F)

    monkeypatch.setattr(ss.ScoringService, "compute_scores", _boom)
    out = _run()
    assert _guard_lines(caplog) == [
        (logging.WARNING, UES_LOGGER, "[URL_GUARD] scorer failed type=SyntheticScorerFault")], (
        _guard_lines(caplog))
    _assert_constant_only(caplog)
    assert recorder.calls == [_base_call(pages)]
    assert out["winner_index"] == 1


@pytest.mark.parametrize("source", ["tradeoffs", "template"])
def test_g12b_reconcile_failed_arm_logs_one_constant_warning(monkeypatch, caplog, source):
    """G12b (PIN at HEAD; kills the adversary's M10 / M11): ON, the scorer step
    succeeds and the reconcile step raises (compute_tradeoff_pairs, or the template
    step under ENABLE_WINNER_PROSE_RECONCILE) with a name and a host in its text ->
    exactly ONE ``[URL_GUARD] reconcile failed type=SyntheticReconcileFault`` WARNING
    on the module logger, no exc_info, no exception text, name or host in any
    record."""
    pages = _pages()
    monkeypatch.setenv(FLAG, "true")
    _capture(caplog)
    recorder = _install(monkeypatch, pages)

    def _boom(*_args, **_kwargs):
        raise SyntheticReconcileFault("synthetic reconcile fault " + NAME_F + " " + URL_E)

    if source == "tradeoffs":
        monkeypatch.setattr(ss.ScoringService, "compute_tradeoff_pairs", _boom)
    else:
        monkeypatch.setenv(PROSE_FLAG, "true")
        monkeypatch.setattr(rb, "deterministic_verdict_fields", _boom)
    _run()
    assert len(recorder.calls) == 1 and "score_winner_index" in recorder.calls[0][1], (
        "PRECONDITION: the scorer step must succeed")
    assert _guard_lines(caplog) == [
        (logging.WARNING, UES_LOGGER, "[URL_GUARD] reconcile failed type=SyntheticReconcileFault")], (
        _guard_lines(caplog))
    _assert_constant_only(caplog)


def test_g12c_none_scorer_winner_takes_the_scorer_failed_arm(monkeypatch, caplog):
    """G12c (PIN at HEAD; GL-16): ON, the real compute_scores result with its
    winner_index set to None -> build_scores_summary raises a TypeError, so the
    scorer-failed arm logs ``type=TypeError`` once, the verdict call is the base call,
    the reconcile is never called and the body is byte-equal to the flag-OFF body
    (the reconcile's legacy branch is not the arm)."""
    pages = _pages()
    _capture(caplog)
    recorder = _install(monkeypatch, pages)
    out_off = _run()
    caplog.clear()
    real = ss.ScoringService.compute_scores

    def _none_winner(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        result["winner_index"] = None
        return result

    monkeypatch.setattr(ss.ScoringService, "compute_scores", _none_winner)
    reconciles = []
    real_reconcile = rb.reconcile_winner_prose

    def _reconcile(*args, **kwargs):
        reconciles.append(1)
        return real_reconcile(*args, **kwargs)

    monkeypatch.setattr(rb, "reconcile_winner_prose", _reconcile)
    monkeypatch.setenv(FLAG, "true")
    out_on = _run()
    assert _guard_lines(caplog) == [
        (logging.WARNING, UES_LOGGER, "[URL_GUARD] scorer failed type=TypeError")], (
        _guard_lines(caplog))
    assert recorder.calls[1] == _base_call(pages)
    assert reconciles == []
    assert _body(out_on) == _body(out_off)

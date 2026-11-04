"""S81-10 FRAGRANCE-ONLY-GATE: the GREEN-owned gate rows (GATE_S81_10 GC-1, GC-5, GC-6), kept
in their own file so the frozen RED file (tests/test_s81_s10_fragrance_gate.py, blob sha256
ac6b061618319f5947ff4a89b22bc6fd83804eeb30655ebd3287f231d4db7656 since the second sanctioned
amendment EK2 of S81-10b (RULINGS_S81_10B R-S10B-4: P02's URL source clause deleted);
fe2032237c2a... after the first, EK1 of fix round 1; d988882a... before both) and its golden
keep their bytes.

Every row reuses the RED file's hermetic harness (the autouse `_s10_clean`, the route-level
`Harness`, the service-level `SvcHarness`, the run-time test lexicon and the synthetic
values), imported the way tests/test_s81_s08b_gate_rows.py reaches its RED file. Synthetic
values only, built at run time; pure ASCII (Arabic built from code points). Every row sets
the unit flag itself.

Row map (node prefix -> condition):
  test_gc1_  GC-1  a concentration / form hit in a product's own name (explicit-pair / vision)
                   proceeds AND the pair is compared as fragrances: category_used, the
                   written-back product category and the profile it selects are fragrances,
                   sync and stream; without the decision the base resolver's category stands
  test_gc5_  GC-5  a needs_second_token term (a trailing ` *` in the lexicon text) never fires
                   rule 1 ALONE; a second, different non-fragrance product-type token does;
                   the production lexicon marks krim, balsam and saa (Arabic, [NATIVE READ])
  test_gc6_  GC-6  the admin-bypass marker (request.state.paid_route_admin) is set ONLY in
                   require_paid_route_user's admin branch: never with the auth flag OFF,
                   never for a signed-in caller, never for a refused one; an anonymous caller
                   is gated on the text and camera routes

Fix round 1 (RULINGS_FIX1_S81_10; the QB rows are ported from the quota-and-billing
adversary's end-to-end probe, names kept):
  test_f1_2_  F1-2   the GC-1 override also rewrites the overridden product's own stub, so
                     B1's per-product categories agree with category_used (no
                     category_conflict); the q= path and a call without the decision keep
                     the base stubs
  test_f1_4_  F1-4   GR-2 (a) / D3: a house-evidence pair of two 'other' stubs with NO chip
                     is refused by the resolver's own A2b answer (counted once, refunded
                     once); the same pair WITH a chip proceeds without a classifier (GC-2)
  test_f1_5_  F1-5   an 'other' chip is no chip: exactly one A2b call (the resolver's)
  test_f1_6_  F1-6   retry_after rounds UP a fractional second; the camera's gate texts carry
                     the brand; the exemption allow-list matches in any case
  test_qb02_  F1-10  end to end (the REAL orchestrator behind the REAL routes): a post-resolve
                     refusal is counted ONCE and refunded ONCE on POST, GET, the stream and
                     the camera, never metered; a parse 'other' pair is never counted
  test_qb03_  F1-11  the admin-key bypass on GET and the stream (under the auth flag only)
  test_qb04_  F1-11  the camera budget exit gives the anon-gate debit back (metering ON); with
                     metering OFF the base W2-1d debit stands (a stated limit)

Rebase round onto a513ea3b (RULINGS_REBASE_S81_10 RB10-11 a):
  test_rb10_a1_  F1-15  with ENABLE_DEVICE_DAILY_QUOTA on and the device axis bound, a
                        post-resolve refusal (POST and stream) gives back S81-09's device
                        debit as well as the account credit; counted once, never metered
  test_rb10_a2_  rv-m3  a house-only partner keeps its 'other' stub when the form override
                        fires (product_categories [fragrances, other], coherent)
  test_rb10_a3_  RB10-6 the collapsed reset seam follows S81-09's usage window (day,
                        next_reset, offset; the 429's resets_at) under ENABLE_RIYADH_RESET
"""
import asyncio
import json
import math
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from starlette.requests import Request as _StarletteRequest

from app.api import image_routes, text_routes
from app.services import cache_service, result_gate, usage_service
from app.services import structured_comparison_service as scs
from tests.test_s81_s10_fragrance_gate import (  # noqa: F401  (the autouse fixture + helpers)
    ADMIN_VALUE,
    AR_KRIM,
    AR_SHAMPOO,
    CODE,
    DAY_TXT,
    FP,
    LEXICON_FILE,
    LEXP,
    UID,
    UID2,
    USER,
    FakeRedis,
    Harness,
    SvcHarness,
    _REDIS,
    _REFUSAL_KEYS,
    _ar,
    _body,
    _coro,
    _dk,
    _evals,
    _expected_keys,
    _full_config,
    _gate_or_fail,
    _join,
    _parsed,
    _s10_clean,
    _subject,
    _test_lexicon,
    _vision,
    _write_lexicon,
)

AR_SAA = _ar(0x0633, 0x0627, 0x0639, 0x0629)  # saa: a watch, and the word for an hour
AR_BALSAM = _ar(0x0628, 0x0644, 0x0633, 0x0645)  # balsam: a conditioner, and a balm
AR_LUSHAN = _ar(0x0644, 0x0648, 0x0634, 0x0646)  # lushan: a lotion
MARK = " *"

HAIR_MIST_PAIRS = [
    ("Chanel Coco Mademoiselle Hair Mist", "Dior Miss Dior Hair Mist"),
    ("Sol de Janeiro Cheirosa 62 Hair & Body Mist", "Kayali Vanilla 28"),
]


def _run(coro):
    return asyncio.run(coro)


def _fetches(rec):
    return [entry for entry in rec if entry[0] == "fetch"]


# ===========================================================================
# GC-1: the form override compares the pair as fragrances (under the flag only)
# ===========================================================================
@pytest.mark.parametrize("pair", HAIR_MIST_PAIRS)
def test_gc1_form_override_compares_as_fragrances_sync(monkeypatch, tmp_path, pair):
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    query = f"{pair[0]} vs {pair[1]}"
    decision = sh.decision([query])
    assert decision.outcome == "proceed"
    svc = scs.StructuredComparisonService()
    res = _run(svc.compare_from_text(query, region="bahrain", explicit_pair=pair,
                                     selected_category="fragrances", user_id=UID,
                                     fragrance_gate=decision))
    assert res.get("code") == "INSUFFICIENT_DATA", res
    fetches = _fetches(sh.rec)
    assert fetches == [("fetch", 0, "fragrances"), ("fetch", 1, "fragrances")], sh.rec
    ctx = svc._partial_build_ctx
    assert ctx["category_used"] == "fragrances", ctx
    assert ctx["category_switched"] is False and ctx["original_category"] is None, ctx
    assert sh.count("classify") == 0 and not _evals(sh.rec), sh.rec
    assert {entry[2] for entry in fetches} == {"fragrances"}


@pytest.mark.parametrize("pair", HAIR_MIST_PAIRS)
def test_gc1_without_the_decision_the_base_category_stands(monkeypatch, tmp_path, pair):
    """The control: the same pair with the flag ON but NO decision (every non-target
    caller) keeps the base resolver's category (the name synonym 'hair'), so the
    rewrite above is the gate's, under the flag only."""
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    query = f"{pair[0]} vs {pair[1]}"
    svc = scs.StructuredComparisonService()
    res = _run(svc.compare_from_text(query, region="bahrain", explicit_pair=pair,
                                     selected_category="fragrances", user_id=UID))
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert _fetches(sh.rec) == [("fetch", 0, "haircare"), ("fetch", 1, "haircare")], sh.rec
    ctx = svc._partial_build_ctx
    assert ctx["category_used"] == "haircare" and ctx["category_switched"] is True, ctx


@pytest.mark.parametrize("pair", HAIR_MIST_PAIRS)
def test_gc1_form_override_compares_as_fragrances_stream(monkeypatch, tmp_path, pair):
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    query = f"{pair[0]} vs {pair[1]}"
    decision = sh.decision([query])
    svc = scs.StructuredComparisonService()

    async def _collect():
        return [ev async for ev in svc.compare_from_text_streaming(
            query, region="bahrain", explicit_pair=pair, selected_category="fragrances",
            user_id=UID, fragrance_gate=decision)]

    events = _run(_collect())
    assert events[-1][0] == "complete" and events[-1][1].get("code") == "INSUFFICIENT_DATA", events
    assert _fetches(sh.rec) == [("fetch", 0, "fragrances"), ("fetch", 1, "fragrances")], sh.rec
    assert not _evals(sh.rec)


def test_gc1_override_helpers(monkeypatch, tmp_path):
    gate = _gate_or_fail()
    _full_config(monkeypatch, tmp_path)
    assert gate.form_override_category("fragrances") == ("fragrances", False, None)
    assert gate.form_override_category(None) == ("fragrances", False, None)
    assert gate.form_override_category("other") == ("fragrances", False, None)
    assert gate.form_override_category("skincare") == ("fragrances", True, "skincare")
    decision = gate.evaluate([" vs ".join(HAIR_MIST_PAIRS[0])])
    explicit = [{"name": n, "search_query": n, "category": "haircare"} for n in HAIR_MIST_PAIRS[0]]
    verdict = _run(gate.post_resolve_refusal(decision, explicit, parser_path=False,
                                             selected_category="fragrances", category_used="haircare"))
    assert verdict.refused is None and verdict.form_override is True, verdict
    # the q= path keeps the parse's word: no override, a positive non-fragrance refuses
    parsed = [{"name": n, "search_query": n, "category": "fragrances"} for n in HAIR_MIST_PAIRS[0]]
    verdict = _run(gate.post_resolve_refusal(decision, parsed, parser_path=True,
                                             selected_category="fragrances", category_used="fragrances"))
    assert verdict.refused is None and verdict.form_override is False, verdict
    parsed = [{"name": n, "search_query": n, "category": "haircare"} for n in HAIR_MIST_PAIRS[0]]
    verdict = _run(gate.post_resolve_refusal(decision, parsed, parser_path=True,
                                             selected_category="fragrances", category_used="haircare"))
    assert verdict.refused == "haircare" and verdict.form_override is False, verdict


# ===========================================================================
# GC-5: a needs_second_token term never fires rule 1 alone
# ===========================================================================
def _marked_lexicon():
    lex = _test_lexicon()
    skincare = [t for t in lex["non_fragrance"]["skincare"] if t != AR_KRIM]
    lex["non_fragrance"]["skincare"] = skincare + [AR_KRIM + MARK]
    lex["non_fragrance"]["fashion"] = lex["non_fragrance"]["fashion"] + [AR_SAA + MARK]
    return lex


def _use_lexicon(monkeypatch, path):
    gate = _gate_or_fail()
    monkeypatch.setenv(LEXP, str(path))
    gate._reset_lexicon_cache()
    return gate


def test_gc5_marked_term_never_fires_rule1_alone(monkeypatch, tmp_path):
    gate = _use_lexicon(monkeypatch, _write_lexicon(tmp_path / "gc5_marked.json", _marked_lexicon()))
    saa = gate.normalize(AR_SAA)[0]
    scan = gate.scan([AR_KRIM])
    assert list(scan.non_fragrance) == [("skincare", AR_KRIM)] and scan.rule1_trigger is False, scan
    decision = gate.evaluate([AR_KRIM])
    assert decision.outcome == "proceed" and decision.evidence is False, decision
    # the same marked term twice is still ONE term (perfume longevity: "12 hours vs 8 hours")
    decision = gate.evaluate(["12 " + AR_SAA + " vs 8 " + AR_SAA])
    assert decision.outcome == "proceed" and decision.evidence is False, decision
    assert list(gate.scan(["12 " + AR_SAA]).non_fragrance) == [("fashion", saa)]
    # a second, DIFFERENT non-fragrance product-type token fires rule 1 (first hit's category)
    decision = gate.evaluate([AR_KRIM + " vs " + AR_SHAMPOO])
    assert decision.outcome == "refuse" and decision.category == "skincare", decision
    decision = gate.evaluate([AR_SAA + " " + AR_KRIM])
    assert decision.outcome == "refuse" and decision.category == "fashion", decision
    # an unmarked term alone still fires
    decision = gate.evaluate([AR_SHAMPOO])
    assert decision.outcome == "refuse" and decision.category == "haircare", decision
    # a fragrance word beside the marked term proceeds with evidence, as for any term
    assert gate.evaluate(["edp " + AR_KRIM]).evidence is True


def test_gc5_the_mark_is_the_only_difference(monkeypatch, tmp_path):
    """The control: the SAME text with the term unmarked refuses at $0, and the mark is
    dropped by normalisation (the term's tokens are unchanged)."""
    gate = _use_lexicon(monkeypatch, _write_lexicon(tmp_path / "gc5_plain.json", _test_lexicon()))
    decision = gate.evaluate([AR_KRIM])
    assert decision.outcome == "refuse" and decision.category == "skincare", decision
    assert gate.normalize(AR_KRIM + MARK) == gate.normalize(AR_KRIM) == [AR_KRIM]


def test_gc5_production_lexicon_marks(monkeypatch):
    gate = _gate_or_fail()
    monkeypatch.delenv(LEXP, raising=False)
    gate._reset_lexicon_cache()
    raw = json.loads(LEXICON_FILE.read_text(encoding="ascii"))
    marked = {group: [t for t in terms if t.rstrip().endswith("*")]
              for group, terms in raw["non_fragrance"].items()}
    assert {g: v for g, v in marked.items() if v} == {
        "skincare": [AR_KRIM + MARK], "haircare": [AR_BALSAM + MARK], "fashion": [AR_SAA + MARK]}, marked
    for terms in raw["fragrance"].values():
        assert not [t for t in terms if t.rstrip().endswith("*")], terms
    for terms in marked.values():
        assert all(any(ord(c) > 127 for c in t) for t in terms), terms  # Arabic tokens only
    assert gate.evaluate(["12 " + AR_SAA]).outcome == "proceed"
    assert gate.evaluate([AR_KRIM]).outcome == "proceed"
    assert gate.evaluate([AR_BALSAM]).outcome == "proceed"
    decision = gate.evaluate([AR_KRIM + " " + AR_LUSHAN])
    assert decision.outcome == "refuse" and decision.category == "skincare", decision


# ===========================================================================
# GC-6: the admin-bypass marker lives only in require_paid_route_user's admin branch
# ===========================================================================
def _request(headers=None):
    raw = [(key.lower().encode("ascii"), value.encode("ascii")) for key, value in (headers or {}).items()]
    scope = {"type": "http", "method": "POST", "path": "/api/v1/text/compare", "headers": raw,
             "query_string": b""}
    return _StarletteRequest(scope)


def _marked(request):
    return getattr(request.state, "paid_route_admin", False)


def test_gc6_marker_only_on_the_admin_branch(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    guard = text_routes.require_paid_route_user
    # the auth flag OFF: both callers pass at once, an admin header changes nothing
    monkeypatch.delenv("ENABLE_COMPARE_AUTH_REQUIRED", raising=False)
    for user in (None, USER):
        request = _request({"X-Admin-Key": ADMIN_VALUE})
        assert _run(guard(request, user)) == user
        assert _marked(request) is False
    monkeypatch.setenv("ENABLE_COMPARE_AUTH_REQUIRED", "true")
    # a signed-in caller passes on the user branch (the admin header is not consulted)
    request = _request({"X-Admin-Key": ADMIN_VALUE})
    assert _run(guard(request, USER)) == USER and _marked(request) is False
    # an anonymous caller without a credential is refused (401), unmarked
    request = _request()
    with pytest.raises(HTTPException) as info:
        _run(guard(request, None))
    assert info.value.status_code == 401 and _marked(request) is False
    # a wrong admin credential is refused (403), unmarked
    request = _request({"X-Admin-Key": _join("s10", "-not-the-", "adm", "in")})
    with pytest.raises(HTTPException) as info:
        _run(guard(request, None))
    assert info.value.status_code == 403 and _marked(request) is False
    # the admin branch: the only place the marker is set
    request = _request({"X-Admin-Key": ADMIN_VALUE})
    assert _run(guard(request, None)) is None and _marked(request) is True


def test_gc6_anonymous_callers_are_gated(monkeypatch, tmp_path):
    """Route level: an anonymous caller with the auth flag OFF (the admin header is never
    read there) and a signed-in caller sending an admin header are both gated."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h = Harness(monkeypatch, tmp_path, flag="true", user=None, header=None)
    h.admin = ADMIN_VALUE
    resp = h.post({"query": "best laptop vs dell laptop"})
    assert resp.status_code == 400 and _body(resp)["code"] == CODE, resp.text[:300]
    assert not h.compares()
    h = Harness(monkeypatch, tmp_path, flag="true", auth_required=True)
    h.admin = ADMIN_VALUE
    resp = h.post({"query": "best laptop vs dell laptop"})
    assert resp.status_code == 400 and _body(resp)["code"] == CODE, resp.text[:300]
    assert not h.compares() and "consume" not in h.tags()


def test_gc6_admin_key_camera_bypasses_the_gate(monkeypatch, tmp_path):
    """R-S10-8 on the camera route: the admin-key caller (anonymous) is never budgeted
    or refused; the compare runs without the decision kwarg."""
    h = Harness(monkeypatch, tmp_path, flag="true", budget="1", seed=True, user=None, auth_required=True)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    h.plan["vision"] = _vision(("Nivea", "Soft Cream"), ("Dove", "Body Cream"))
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    assert _body(resp).get("code") != CODE, resp.text[:300]
    compares = h.compares()
    assert len(compares) == 1 and "fragrance_gate" not in compares[0][2], compares
    assert not [t for t in h.tags() if t in ("redis.get", "redis.mget", "redis.eval")], h.rec


# ===========================================================================
# F1-2: the GC-1 override also rewrites the overridden product's own stub (m5, GC-1 x B1)
# ===========================================================================
F12_BOTH = ("Kerastase Genesis Hair Mist", "Dior Sauvage EDT")  # both names carry a form word
F12_ONE = ("Kerastase Genesis Hair Mist", "Kayali Vanilla 28")  # only the first one does


def _f12_compare(entry, query, **kw):
    """One compare on the REAL orchestrator (SvcHarness fakes): the result (the stream's
    terminal event) and the partial build ctx, where B1's per-product capture lands."""
    svc = scs.StructuredComparisonService()
    if entry == "sync":
        res = _run(svc.compare_from_text(query, region="bahrain", user_id=UID, **kw))
    else:
        async def _collect():
            return [ev async for ev in svc.compare_from_text_streaming(query, region="bahrain", user_id=UID, **kw)]
        res = _run(_collect())[-1][1]
    return res, svc._partial_build_ctx


@pytest.mark.parametrize("entry", ["sync", "stream"])
def test_f1_2_form_override_rewrites_the_overridden_stub(monkeypatch, tmp_path, entry):
    """F1-2: a product the form override made a fragrance (a concentration / form word in its
    own name, explicit / vision path) takes 'fragrances' as its own stub together with
    category_used, so B1's per-product categories (captured after the gate block) agree and
    result_gate.identity_coherence no longer reports category_conflict. Only the overridden
    product's stub moves; the q= path (no override, R-S10-5) and a call without the
    decision (every flag-OFF call) keep the base stubs."""
    monkeypatch.setenv("ENABLE_RESULT_STATUS_METADATA", "true")
    # (a) both names carry a form / concentration word (stubs haircare / fragrances at base)
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    query = " vs ".join(F12_BOTH)
    res, ctx = _f12_compare(entry, query, explicit_pair=F12_BOTH, fragrance_gate=sh.decision([query]))
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert ctx["category_used"] == "fragrances", ctx
    assert ctx["product_categories"] == ["fragrances", "fragrances"], ctx
    assert result_gate.identity_coherence(ctx["product_categories"], ctx["category_used"]) is True
    assert sh.count("classify") == 0 and not _evals(sh.rec), sh.rec
    # (b) only the overridden product's own stub moves, in either position; the other
    # product keeps its 'other'
    for pair, expected in ((F12_ONE, ["fragrances", "other"]), (F12_ONE[::-1], ["other", "fragrances"])):
        sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
        query = " vs ".join(pair)
        res, ctx = _f12_compare(entry, query, explicit_pair=pair, fragrance_gate=sh.decision([query]))
        assert res.get("code") == "INSUFFICIENT_DATA", res
        assert ctx["category_used"] == "fragrances", ctx
        assert ctx["product_categories"] == expected, (pair, ctx)
    # (c) the q= path never overrides: the parse's per-product categories stand, a
    # concentration word in a parsed name included
    sh = SvcHarness(monkeypatch, tmp_path,
                    parsed=_parsed("fragrances", "other", ("Dior", "Sauvage"), ("Kayali", "Vanilla 28 EDP")))
    query = "dior sauvage vs kayali vanilla 28 edp"
    res, ctx = _f12_compare(entry, query, fragrance_gate=sh.decision([query]))
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert ctx["product_categories"] == ["fragrances", "other"], ctx
    # (d) without the decision the block never runs: the base stubs and category stand
    sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
    res, ctx = _f12_compare(entry, " vs ".join(F12_BOTH), explicit_pair=F12_BOTH)
    assert res.get("code") == "INSUFFICIENT_DATA", res
    assert ctx["category_used"] == "haircare" and ctx["product_categories"] == ["haircare", "fragrances"], ctx


# ===========================================================================
# end to end: the REAL orchestrator behind the REAL routes (the adversary's QB harness)
# ===========================================================================
def _e2e(monkeypatch, tmp_path, *, parsed=None, a2b="electronics", **hkw):
    """Route rows over the real StructuredComparisonService: only the parse, the A2b
    classifier, the fetch pair (both failed: a compare that passes the gate ends at
    INSUFFICIENT_DATA), the consume and the refund are faked (SvcHarness + Harness)."""
    sh = SvcHarness(monkeypatch, tmp_path, parsed=parsed, a2b=a2b)
    h = Harness(monkeypatch, tmp_path, flag="true", **hkw)
    monkeypatch.setattr(text_routes, "get_comparison_service", lambda: scs.StructuredComparisonService())
    monkeypatch.setattr(image_routes, "StructuredComparisonService", scs.StructuredComparisonService)
    return h, sh


def _assert_counted_once_refunded_once(h, sh):
    tags = h.tags()
    assert tags.count("consume") == 1, h.rec
    assert tags.count("refund") == 1, h.rec
    assert not [t for t in tags if t in ("record_lifetime", "save", "capture_result_status")], h.rec
    evals = _evals(h.rec)
    assert len(evals) == 1, evals
    assert sorted(evals[0][2]) == sorted(_expected_keys(dk=_dk())), evals[0]
    assert sh.count("fetch") == 0 and sh.count("profile") == 0, sh.rec


# ===========================================================================
# F1-4: D3 (GR-2 a): no chip -> the resolver's own A2b answer decides; a chip -> GC-2
# ===========================================================================
def test_f1_4_d3_house_pair_no_chip_refused_chip_proceeds(monkeypatch, tmp_path):
    """GR-2 (a): an explicit pair of two 'other' stubs WITH house evidence and NO chip is
    refused post-resolve when the resolver's own chip-free A2b answer is a positive
    non-fragrance (one A2b call, the resolver's: C11), counted once on both budget keys
    and refunded once by the route's existing arm (F1-13: such a misread spends budget);
    the same pair WITH a client chip proceeds as fragrances without a classifier call and
    is never counted (GC-2, a stated limit)."""
    pair = ("Gucci Dionysus", "Prada Galleria")
    h, sh = _e2e(monkeypatch, tmp_path, a2b="fashion")
    resp = h.post({"product_a": pair[0], "product_b": pair[1]})
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = _body(resp)
    assert body["code"] == CODE and body["category"] == "fashion", body
    assert [e for e in sh.rec if e[0] == "classify"] == [("classify", pair)], sh.rec
    _assert_counted_once_refunded_once(h, sh)
    assert ("ff", "usage_refund.text.post") in h.rec, h.rec
    h, sh = _e2e(monkeypatch, tmp_path, a2b="fashion")
    resp = h.post({"product_a": pair[0], "product_b": pair[1], "selected_category": "fragrances"})
    # the compare ran (the fetch fake ends it at INSUFFICIENT_DATA, refunded by the base arm)
    assert resp.status_code == 400 and _body(resp)["code"] == "INSUFFICIENT_DATA", resp.text[:300]
    assert sh.count("classify") == 0 and not _evals(h.rec), (sh.rec, h.rec)
    assert [e for e in sh.rec if e[0] == "fetch"] == [("fetch", 0, "fragrances"), ("fetch", 1, "fragrances")], sh.rec


def test_f1_4_qb06_camera_house_pair_refused_and_counted(monkeypatch, tmp_path):
    """The camera never sends a chip (the adversary's QB06): a brand-only fashion-house
    perfume pair the resolver's A2b misreads is refused AND counted (one EVAL on both keys,
    one refund, one A2b call): the budget consequence of D3 (F1-13, a stated limit)."""
    h, sh = _e2e(monkeypatch, tmp_path, a2b="fashion")
    h.plan["vision"] = _vision(("Gucci", "Guilty"), ("Prada", "Luna Rossa"))
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert body.get("action") == "error" and body.get("code") == CODE and body.get("category") == "fashion", body
    assert [e for e in sh.rec if e[0] == "classify"] == [("classify", ("Gucci Guilty", "Prada Luna Rossa"))], sh.rec
    _assert_counted_once_refunded_once(h, sh)
    assert ("ff", "usage_refund.image.category_not_live") in h.rec, h.rec


# ===========================================================================
# F1-5: an 'other' chip is no chip (exactly one A2b call)
# ===========================================================================
def test_f1_5_other_chip_refused_with_one_a2b_call(monkeypatch, tmp_path):
    """m3: with chip 'other' the resolver's own A2b answer is the pair detection, so a
    blind pair it classifies as a positive non-fragrance is refused with EXACTLY one A2b
    call (never a second one after the resolver's)."""
    sh = SvcHarness(monkeypatch, tmp_path, a2b="electronics")
    decision = sh.decision(["iPhone 15 vs Galaxy S24"])
    assert decision.outcome == "proceed" and decision.evidence is False, decision
    res = sh.compare("iPhone 15 vs Galaxy S24", explicit_pair=("iPhone 15", "Galaxy S24"),
                     selected_category="other", user_id=UID, fragrance_gate=decision)
    assert res.get("code") == CODE and res.get("category") == "electronics", res
    assert [e for e in sh.rec if e[0] == "classify"] == [("classify", ("iPhone 15", "Galaxy S24"))], sh.rec
    assert sh.count("fetch") == 0 and len(_evals(sh.rec)) == 1, sh.rec


# ===========================================================================
# F1-6: the three coverage gaps of m8 (A14, A17, A29)
# ===========================================================================
def test_f1_6_retry_after_rounds_up_a_fractional_second():
    """A14: retry_after is the CEILING of the seconds to the reset (a floor would answer one
    second early on any fractional instant)."""
    gate = _gate_or_fail()
    nxt = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)
    assert gate.retry_fields(nxt - timedelta(seconds=10799, milliseconds=500), nxt, 3) == (
        10800, "2026-10-30T03:00:00+03:00")
    assert gate.retry_fields(nxt - timedelta(seconds=1, microseconds=1), nxt, 0)[0] == 2


def test_f1_6_camera_vision_texts_carry_the_brand(monkeypatch, tmp_path):
    """A17: the camera's gate texts are '<brand> <name>', so a house named only in the brand
    field is evidence: 'Jo Malone' + 'Peony & Blush Suede' is no post-vision rule-1 refusal
    (a product-type word beside a house defers to the post-resolve decision, R-S10-4)."""
    gate = _gate_or_fail()
    products = [{"brand": "Jo Malone", "name": "Peony & Blush Suede"},
                {"brand": "Jo Malone", "name": "English Pear & Freesia"}]
    assert gate.vision_texts(products) == ["Jo Malone Peony & Blush Suede", "Jo Malone English Pear & Freesia"]
    h = Harness(monkeypatch, tmp_path, flag="true")
    h.plan["vision"] = _vision(("Jo Malone", "Peony & Blush Suede"), ("Jo Malone", "English Pear & Freesia"))
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    assert _body(resp).get("code") != CODE, resp.text[:300]
    compares = h.compares()
    assert len(compares) == 1 and compares[0][4] == {
        "outcome": "proceed", "evidence": False, "category": None, "subject": True}, compares


def test_f1_6_exemption_allow_list_matches_any_case(monkeypatch):
    """A29: the allow-list match is case-insensitive on both sides (the S81-09 parsing
    lower-cases the list; the account id is lower-cased at the match); a listed account is
    exempt without a tier read."""
    gate = _gate_or_fail()
    reads = []

    def _tier(uid, *a, **kw):
        reads.append(uid)
        return _coro({"subscription_tier": "free"})

    monkeypatch.setattr(usage_service, "_get_user_tier_info", _tier)
    monkeypatch.setenv("DEVICE_QUOTA_EXEMPT_USER_IDS", UID.upper())
    assert _run(gate.budget_exempt_async(UID)) is True
    assert _run(gate.budget_exempt_async(UID.upper())) is True
    assert reads == []
    assert _run(gate.budget_exempt_async(UID2)) is False and reads == [UID2]


# ===========================================================================
# F1-10 (QB02): counted once, refunded once, never metered, on every route
# ===========================================================================
@pytest.mark.parametrize("route", ["post", "get"])
def test_qb02_sync_refusal_counted_once_refunded_once(monkeypatch, tmp_path, route):
    h, sh = _e2e(monkeypatch, tmp_path, parsed=_parsed("electronics", "electronics"))
    query = "khamrah vs hawas"
    resp = h.post({"query": query}) if route == "post" else h.get({"q": query})
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = _body(resp)
    assert body["code"] == CODE and body["category"] == "electronics", body
    assert list(body) == _REFUSAL_KEYS, body
    _assert_counted_once_refunded_once(h, sh)
    assert ("ff", f"usage_refund.text.{route}") in h.rec, h.rec


def test_qb02_stream_refusal_counted_once_refunded_once(monkeypatch, tmp_path):
    h, sh = _e2e(monkeypatch, tmp_path, parsed=_parsed("electronics", "electronics"))
    resp = h.stream({"q": "khamrah vs hawas"})
    assert resp.status_code == 200, resp.text[:300]
    frames = [f for f in resp.text.split("\n\n") if f.strip()]
    errors = [f for f in frames if f.startswith("event: error\n")]
    assert len(errors) == 1, frames
    data = json.loads(errors[0].split("data: ", 1)[1])
    assert data["code"] == CODE and data["category"] == "electronics", data
    assert not [f for f in frames if f.startswith("event: complete") or f.startswith("event: settle_complete")]
    _assert_counted_once_refunded_once(h, sh)
    assert ("ff", "usage_refund.text_stream") in h.rec, h.rec


def test_qb02_camera_post_resolve_counted_once_refunded_once(monkeypatch, tmp_path):
    """QM12 dies here: the camera's post-resolve arm must not count the refusal again (the
    orchestrator already did; a second INCR would halve the budget)."""
    h, sh = _e2e(monkeypatch, tmp_path)
    h.plan["vision"] = _vision(("Samsung", "Galaxy S24"), ("Apple", "iPhone 15"))
    resp = h.camera(2)
    assert resp.status_code == 200, resp.text[:300]
    body = _body(resp)
    assert body.get("action") == "error" and body.get("code") == CODE, body
    assert body.get("category") == "electronics", body
    _assert_counted_once_refunded_once(h, sh)
    assert sh.count("resolve") == 1 and len(h.compares()) == 0, (sh.rec, h.rec)  # the real orchestrator ran
    assert ("ff", "usage_refund.image.category_not_live") in h.rec, h.rec
    assert not [t for t in h.tags() if t == "log_search"], h.rec


def test_qb02_parse_other_proceeds_billed_uncounted(monkeypatch, tmp_path):
    """R-S10-3 on the q= path: a parse 'other' / 'other' proceeds and is never counted (the
    fetch fake ends the compare at INSUFFICIENT_DATA; the base failure arm refunds it)."""
    h, sh = _e2e(monkeypatch, tmp_path, parsed=_parsed("other", "other"))
    resp = h.post({"query": "khamrah vs hawas"})
    assert not _evals(h.rec), h.rec
    assert sh.count("fetch") >= 1, sh.rec
    assert resp.status_code == 400 and _body(resp)["code"] == "INSUFFICIENT_DATA", resp.text[:300]
    assert h.tags().count("refund") == 1


# ===========================================================================
# F1-11 (QB03): the admin-key bypass on GET and the stream (P06 pins POST)
# ===========================================================================
@pytest.mark.parametrize("route", ["get", "stream"])
def test_qb03_admin_key_bypass_get_and_stream(monkeypatch, tmp_path, route):
    """R-S10-8 on the eval / smoke harness routes (A02 / A03 = QM01 / QM02 die here)."""
    h = Harness(monkeypatch, tmp_path, flag="true", budget="1", seed=True, user=None, auth_required=True)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    params = {"q": "best laptop vs dell laptop"}
    resp = h.get(params) if route == "get" else h.stream(params)
    assert resp.status_code == 200, resp.text[:300]
    compares = h.compares()
    assert len(compares) == 1 and "fragrance_gate" not in compares[0][2], compares
    assert not [t for t in h.tags() if t in _REDIS], h.rec


def test_qb03_admin_key_with_auth_flag_off_is_gated(monkeypatch, tmp_path):
    """F1-12 (m4): the bypass exists only under ENABLE_COMPARE_AUTH_REQUIRED ON (the marker
    is set in require_paid_route_user's admin branch, which the auth-OFF early return never
    reaches): with it OFF the same admin-key request is gated like any other."""
    h = Harness(monkeypatch, tmp_path, flag="true", user=None, header=None, auth_required=False)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_VALUE)
    h.admin = ADMIN_VALUE
    resp = h.get({"q": "best laptop vs dell laptop"})
    assert resp.status_code == 400 and _body(resp)["code"] == CODE, resp.text[:300]


# ===========================================================================
# F1-11 (QB04): the camera budget exit and the anon-gate credit
# ===========================================================================
def _anon_camera(monkeypatch, tmp_path, *, metering):
    h = Harness(monkeypatch, tmp_path, flag="true", budget="10", user=None, metering=metering)
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
    rec = h.rec

    async def _anon(fp):
        rec.append(("anon_consume", "fp"))
        return {"allowed": True, "reason": None, "tier": "free", "consumed": True,
                "consumed_keys": {"daily": "usage:daily:anon", "monthly": "usage:monthly:anon"},
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 0}}

    monkeypatch.setattr(image_routes, "check_anon_usage_allowed", _anon)
    h.redis.store[f"refusal:daily:dev:{_dk()}:{DAY_TXT}"] = 10
    return h


def test_qb04_camera_budget_anon_metering_on_refunds_once(monkeypatch, tmp_path):
    """QM09 dies here: an anonymous camera call at the budget (auth OFF, the anon gate ON,
    metering ON) gets the anon-gate debit back exactly once; no vision call, no consume."""
    h = _anon_camera(monkeypatch, tmp_path, metering=True)
    body = _body(h.camera(2))
    assert body.get("scope") == "refusal_daily", body
    tags = h.tags()
    assert tags.count("anon_consume") == 1 and tags.count("refund_anon") == 1, h.rec
    assert not [t for t in tags if t in ("vision", "compare", "consume", "redis.eval")], h.rec


def test_qb04_camera_budget_anon_metering_off_keeps_the_debit(monkeypatch, tmp_path):
    """F1-12 (m5), a stated limit: with ENABLE_PAID_ROUTE_METERING OFF the anon-gate debit of a
    budget-refused camera call is never given back (the base W2-1d accounting: metering OFF
    = debit at the gate, no refund anywhere); unreachable in production (auth ON)."""
    h = _anon_camera(monkeypatch, tmp_path, metering=False)
    body = _body(h.camera(2))
    assert body.get("scope") == "refusal_daily", body
    tags = h.tags()
    assert tags.count("anon_consume") == 1 and tags.count("refund_anon") == 0, h.rec


# ===========================================================================
# RB10-11 (the rebase round onto a513ea3b, RULINGS_REBASE_S81_10): a1 the S81-09 device debit
# given back on a post-resolve refusal, a2 a house-only partner keeps its 'other' stub,
# a3 the collapsed reset seam follows S81-09's usage window
# ===========================================================================
class _QuotaRedis(FakeRedis):
    """The RED's FakeRedis (the refusal budget's MGET and REFUSAL_INCR_SCRIPT, recorded as
    'redis.eval') plus S81-09's two quota scripts, emulated in Python and keyed on
    usage_service's own script constants (there is no Lua runtime on the box, R-S09-10),
    recorded as 'quota.eval' with the keys and the reply."""

    def _emulate(self, shape, script, keys, argv):
        if script == usage_service.DEVICE_CONSUME_SCRIPT:
            account = int(self.store.get(keys[0]) or 0)
            device = 0
            reply = None
            if len(keys) > 1:
                device = int(self.store.get(keys[1]) or 0)
                if device >= int(argv[1]):
                    reply = [2, account, device]
            if reply is None and account >= int(argv[0]):
                reply = [1, account, device]
            if reply is None:
                if len(keys) > 1:
                    device += 1
                    self.store[keys[1]] = device
                    self.expireat[keys[1]] = int(argv[2])
                account += 1
                self.store[keys[0]] = account
                self.expireat[keys[0]] = int(argv[2])
                reply = [0, account, device]
            self.rec.append(("quota.eval", "consume", tuple(keys), tuple(reply)))
            return reply
        if script == usage_service.DEVICE_REFUND_SCRIPT:
            reply = []
            for key in keys:
                value = int(self.store.get(key) or 0)
                if value > 0:
                    self.store[key] = value - 1
                    reply.append(value - 1)
                else:
                    reply.append(-1)
            self.rec.append(("quota.eval", "refund", tuple(keys), tuple(reply)))
            return reply
        return super()._emulate(shape, script, keys, argv)


def _a1_device_quota(monkeypatch, tmp_path):
    """The QB02 end-to-end harness with S81-09's REAL consume and refund behind the REAL text
    routes: ENABLE_DEVICE_DAILY_QUOTA on, the device axis bound (the X-Device-Fingerprint
    header through the S81-05 middleware with DEVICE_KEY_PEPPER set, both by the RED's full
    configuration), one Redis fake shared by usage_service and the refusal budget. The
    route's refund coroutine runs to completion inside the request (the RED's fire-and-forget
    fake would close it unrun); every other fire-and-forget coroutine is closed as there."""
    h, sh = _e2e(monkeypatch, tmp_path, parsed=_parsed("electronics", "electronics"))
    monkeypatch.setenv("ENABLE_DEVICE_DAILY_QUOTA", "true")
    fake = _QuotaRedis(h.rec, store=dict(h.redis.store))
    h.redis = fake
    monkeypatch.setattr(cache_service, "redis_client", fake)
    monkeypatch.setattr(usage_service, "redis_client", fake)
    monkeypatch.setattr(usage_service, "_get_active_referral_bonus", lambda uid: _coro(0))
    rec = h.rec
    real_consume = usage_service.consume_comparison_credit
    real_refund = usage_service.refund_comparison_credit

    async def _consume(uid, access_token="", **kw):
        rec.append(("consume", uid, tuple(sorted(kw))))
        return await real_consume(uid, access_token, **kw)

    async def _refund(uid, consumed_keys=None):
        rec.append(("refund", uid))
        await real_refund(uid, consumed_keys)

    def _ff(coro, label=None, **kw):
        rec.append(("ff", label))
        if isinstance(label, str) and label.startswith("usage_refund"):
            try:
                coro.send(None)
            except StopIteration:
                return
            coro.close()
            raise AssertionError("the refund suspended: " + label)
        close = getattr(coro, "close", None)
        if callable(close):
            close()

    monkeypatch.setattr(text_routes, "consume_comparison_credit", _consume)
    monkeypatch.setattr(text_routes, "refund_comparison_credit", _refund)
    monkeypatch.setattr(text_routes, "fire_and_forget", _ff)
    return h, sh, fake


@pytest.mark.parametrize("route", ["post", "stream"])
def test_rb10_a1_device_debit_refunded_on_post_resolve_refusal(monkeypatch, tmp_path, route):
    """RB10-11 (a1) = F1-15 / RB10-7 b2, a MEASUREMENT across the S81-09 merge: with
    ENABLE_FRAGRANCE_ONLY_GATE and ENABLE_DEVICE_DAILY_QUOTA both on and the device axis bound,
    a post-resolve refusal on the sync POST route and on the stream route gives back the
    DEVICE debit as well as the account credit: S81-09's ONE consume EVAL debits both usage
    keys, its ONE refund EVAL gives both back (the request-scoped stash; no route edit), the
    refusal is counted ONCE on both budget keys and never metered as a delivery (the QB02
    shape)."""
    h, sh, fake = _a1_device_quota(monkeypatch, tmp_path)
    query = "khamrah vs hawas"
    if route == "post":
        resp = h.post({"query": query})
        assert resp.status_code == 400, (resp.status_code, resp.text[:300])
        body = _body(resp)
    else:
        resp = h.stream({"q": query})
        assert resp.status_code == 200, resp.text[:300]
        frames = [f for f in resp.text.split("\n\n") if f.strip()]
        errors = [f for f in frames if f.startswith("event: error\n")]
        assert len(errors) == 1, frames
        assert not [f for f in frames if f.startswith("event: complete") or f.startswith("event: settle_complete")]
        body = json.loads(errors[0].split("data: ", 1)[1])
    assert body["code"] == CODE and body["category"] == "electronics", body
    quota = [e for e in h.rec if e[0] == "quota.eval"]
    assert [e[1] for e in quota] == ["consume", "refund"], quota
    consume_keys, refund_keys = quota[0][2], quota[1][2]
    assert len(consume_keys) == 2, consume_keys
    assert consume_keys[0].startswith(f"usage:daily:{UID}:"), consume_keys
    assert consume_keys[1].startswith(f"usage:device:{_dk()}:"), consume_keys
    assert quota[0][3] == (0, 1, 1), quota[0]  # a debit on both axes
    assert refund_keys == consume_keys and quota[1][3] == (0, 0), quota[1]
    assert fake.store[consume_keys[0]] == 0 and fake.store[consume_keys[1]] == 0, fake.store
    tags = h.tags()
    assert tags.count("consume") == 1 and tags.count("refund") == 1, h.rec
    assert ("consume", UID, ("device_fp",)) in h.rec, h.rec  # the S81-09 device axis was bound
    assert not [t for t in tags if t in ("record_lifetime", "save", "capture_result_status")], h.rec
    evals = _evals(h.rec)
    assert len(evals) == 1 and sorted(evals[0][2]) == sorted(_expected_keys(dk=_dk())), evals
    assert sh.count("fetch") == 0 and sh.count("profile") == 0, sh.rec
    label = "usage_refund.text.post" if route == "post" else "usage_refund.text_stream"
    assert ("ff", label) in h.rec, h.rec


F12_HOUSE = ("Kerastase Genesis Hair Mist", "Dior Homme")  # the partner: a house, no form word


@pytest.mark.parametrize("entry", ["sync", "stream"])
def test_rb10_a2_house_only_partner_keeps_its_other_stub(monkeypatch, tmp_path, entry):
    """RB10-11 (a2) = rv-m3: on the explicit path a house-only partner ('Dior Homme' beside
    'Kerastase Genesis Hair Mist') keeps its 'other' stub when the form override fires: B1's
    per-product categories are [fragrances, other] (either order), category_used fragrances,
    coherent (no category_conflict). Kills the mutant that widens apply_form_override_stubs'
    per-product test from scan().fragrance_type to scan().evidence (the house is evidence)."""
    monkeypatch.setenv("ENABLE_RESULT_STATUS_METADATA", "true")
    for pair, expected in ((F12_HOUSE, ["fragrances", "other"]), (F12_HOUSE[::-1], ["other", "fragrances"])):
        sh = SvcHarness(monkeypatch, tmp_path, a2b="haircare")
        gate = _gate_or_fail()
        partner = gate.scan(["Dior Homme"])
        assert partner.evidence and not partner.fragrance_type, partner  # the premise
        query = " vs ".join(pair)
        decision = sh.decision([query])
        assert decision.outcome == "proceed", decision
        res, ctx = _f12_compare(entry, query, explicit_pair=pair, fragrance_gate=decision)
        assert res.get("code") == "INSUFFICIENT_DATA", res
        assert ctx["category_used"] == "fragrances", ctx
        assert ctx["product_categories"] == expected, (pair, ctx)
        assert result_gate.identity_coherence(ctx["product_categories"], ctx["category_used"]) is True
        assert not _evals(sh.rec), sh.rec


_A3_INSTANTS = (
    datetime(2026, 11, 2, 22, 15, 30, tzinfo=timezone.utc),  # 21:00-24:00 UTC: Riyadh is already on the next day
    datetime(2026, 11, 2, 10, 15, 30, tzinfo=timezone.utc),  # 00:00-21:00 UTC: the same day in both zones
)


class _FrozenDT(datetime):
    current = None

    @classmethod
    def now(cls, tz=None):
        return cls.current if tz is None else cls.current.astimezone(tz)


def test_rb10_a3_reset_seam_follows_the_usage_window(monkeypatch, tmp_path):
    """RB10-11 (a3) = RB10-6: with ENABLE_RIYADH_RESET on, category_gate.reset_window(now),
    retry_fields and budget_keys agree with S81-09's usage window for the same instant (the
    same day, the same next_reset, the same offset; the refusal 429's resets_at is S81-09's
    own reset text) at a UTC instant between 21:00 and 24:00 and at one between 00:00 and
    21:00, and budget_state_async (the clock frozen at that instant) answers from that
    window. S81-09's offset constant moved to 5 moves the gate with it: kills the mutant
    that pins a local 3-hour offset (or a local window) instead of delegating."""
    gate = _gate_or_fail()
    _full_config(monkeypatch, tmp_path, budget="10")
    monkeypatch.setenv("ENABLE_RIYADH_RESET", "true")
    rec = []
    fake = FakeRedis(rec)
    monkeypatch.setattr(cache_service, "redis_client", fake)

    def _tier(uid, *a, **kw):
        rec.append(("tier_read", uid))
        return _coro({"subscription_tier": "free"})

    monkeypatch.setattr(usage_service, "_get_user_tier_info", _tier)
    monkeypatch.setattr(_FrozenDT, "current", _A3_INSTANTS[0])
    monkeypatch.setattr(gate, "datetime", _FrozenDT)
    subject = _subject(gate, header=True)
    assert subject is not None and subject.device_key, subject
    sanity = {
        _A3_INSTANTS[0]: (date(2026, 11, 3), datetime(2026, 11, 3, 21, 0, tzinfo=timezone.utc)),
        _A3_INSTANTS[1]: (date(2026, 11, 2), datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc)),
    }
    for patched in (None, 5):
        if patched is not None:
            monkeypatch.setattr(usage_service, "RIYADH_UTC_OFFSET_HOURS", patched)
        expected_offset = usage_service.RIYADH_UTC_OFFSET_HOURS
        zone = timezone(timedelta(hours=expected_offset))
        for now in _A3_INSTANTS:
            u_day, u_next = usage_service._usage_window(now)
            if patched is None:
                assert (u_day, u_next) == sanity[now], (now, u_day, u_next)
            day, nxt, offset = gate.reset_window(now)
            assert (day, nxt, offset) == (u_day, u_next, expected_offset), (patched, now, day, nxt, offset)
            retry_after, resets_at = gate.retry_fields(now, nxt, offset)
            assert retry_after == math.ceil((u_next - now).total_seconds()), (now, retry_after)
            assert resets_at == u_next.astimezone(zone).isoformat(timespec="seconds"), resets_at
            if patched is None:
                assert resets_at == usage_service._reset_instant_text(u_next, True), resets_at
            day_txt = u_day.strftime("%Y-%m-%d")
            keys = gate.budget_keys(subject, day)
            assert len(keys) == 2 and all(k.endswith(":" + day_txt) for k in keys), keys
            fake.store = {keys[0]: 10}
            _FrozenDT.current = now
            del rec[:]
            assert _run(gate.budget_state_async(subject)) == (retry_after, resets_at), (patched, now)
            assert [e for e in rec if e[0] == "redis.mget"] == [("redis.mget", tuple(keys))], rec

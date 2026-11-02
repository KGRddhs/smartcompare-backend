"""S81-10 FRAGRANCE-ONLY-GATE: the GREEN-owned gate rows (GATE_S81_10 GC-1, GC-5, GC-6), kept
in their own file so the frozen RED file (tests/test_s81_s10_fragrance_gate.py, sha256
d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac) and its golden keep their
bytes.

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
"""
import asyncio
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request as _StarletteRequest

from app.api import text_routes
from app.services import extraction_service, scoring_service
from app.services import structured_comparison_service as scs
from tests.test_s81_s10_fragrance_gate import (  # noqa: F401  (the autouse fixture + helpers)
    ADMIN_VALUE,
    AR_KRIM,
    AR_SHAMPOO,
    CODE,
    LEXICON_FILE,
    LEXP,
    UID,
    USER,
    Harness,
    SvcHarness,
    _ar,
    _body,
    _evals,
    _full_config,
    _gate_or_fail,
    _join,
    _s10_clean,
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
    # the downstream profile keys off the written-back category: the fragrance spec
    # schema and scoring dimensions, which differ from the haircare ones
    assert extraction_service.CATEGORY_SPEC_SCHEMAS["fragrances"] != extraction_service.CATEGORY_SPEC_SCHEMAS["haircare"]
    assert scoring_service.CATEGORY_DIMENSIONS["fragrances"] != scoring_service.CATEGORY_DIMENSIONS["haircare"]
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

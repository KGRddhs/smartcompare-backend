"""W4-10 — CR-DELTA-CORRECTNESS-07(a): `compute_scores` must spell the product the
way the display side already spells it.

M21-W3 `7fb0b0d4` (PR #129) moved the DISPLAY half of the product-name spelling
(`structured_comparison_service._display_product_names`, `winner_evidence`) onto
`text_sanitize.dedup_brand_name` and left `compute_scores`' INTERNAL half on the
raw `f"{brand} {name}".strip()`. `compute_tradeoff_pairs` joins the two by string
equality, so for every brand-repeating pair ("Xerjoff" / "Xerjoff Naxos") it
returns [] and the runner-up caption (`overview.winner.key_tradeoff`) ships
empty. The same regression feeds the gpt-4o verdict prompt a doubled-brand
`Dimension leaders:` line and `price tier: unknown` (`build_scores_summary` looks
the tier up by the deduped name in a raw-keyed map).

Binding rulings covered here (spec `.qa-w4/W4_10_UNIT_SPEC.md`, FABLE REVIEW
RULINGS 2026-09-23):
  R2 — `scripts/shadow_experiments._compute_scores_summary_offline` spells the
       offline prompt's names the way production does.
  R3 — `build_scores_summary` resolves the tier from `price_tiers_by_index`;
       the `price_tiers` KEYS stay raw.
  R4 — the new label expression coerces non-str halves (`str(x or "")`); pin 11
       is the degenerate pair that reaches `:1554` without raising at `:914`.
  R5 — pin 12 is the three-product shape asserting the post-fix (deduped) labels.
  R6 — pins 7 (all keys except `dimension_winners`), 9 and 10 are Preserve
       decoration; the Applesauce row of pin 10 is the load-bearing one against
       an argument-swap mutation.

Unflagged regression fix, so there is no flag under test. The five flags that
change `compute_scores` output are cleared by default and the core invariants
are parametrised over all-OFF / all-ON (measured at b63a8368: the RED reproduces
identically in both states).

Every test here is FREE: no network, no DB, no LLM. The joins are exercised
through the REAL production functions (`_display_product_names`,
`compute_tradeoff_pairs`, `deterministic_verdict_fields`,
`_build_partial_response`), never a re-implementation of them.
"""
from __future__ import annotations

import ipaddress
import socket
import sys

import pytest

from app.services.response_builder import deterministic_verdict_fields
from app.services.scoring_service import get_scoring_service
from app.services.structured_comparison_service import (
    _display_product_names,
    get_comparison_service,
)
from scripts import shadow_experiments as se

SENTINELS = {"tie", "N/A"}

# Every env flag `scoring_service` reads that can move `compute_scores` output.
SCORING_FLAGS = (
    "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_CATEGORY_VALUE_BADGE",
    "ENABLE_MISSING_DIM_RENORM",
    "ENABLE_SPEC_FIELD_NORM",
)


_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex
_REAL_GETADDRINFO = socket.getaddrinfo


def _is_loopback_host(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host in (None, "", "localhost"):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _socket_guard(monkeypatch):
    """Every test here is FREE: block any non-loopback connect / getaddrinfo and
    fail the test on an attempt, even if the code under test swallows the error."""
    attempts = []

    def _blocked(kind, target):
        attempts.append((kind, target))
        return OSError(f"network blocked in test: {kind} {target!r}")

    def guarded_connect(self, address):
        if isinstance(address, tuple) and not _is_loopback_host(address[0]):
            raise _blocked("connect", address)
        return _REAL_CONNECT(self, address)

    def guarded_connect_ex(self, address):
        if isinstance(address, tuple) and not _is_loopback_host(address[0]):
            raise _blocked("connect_ex", address)
        return _REAL_CONNECT_EX(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback_host(host):
            raise _blocked("getaddrinfo", host)
        return _REAL_GETADDRINFO(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    yield
    assert not attempts, f"test attempted network access: {attempts!r}"


@pytest.fixture(autouse=True)
def _scoring_flags_default_off(monkeypatch):
    """Deterministic default state regardless of a developer `.env`."""
    for name in SCORING_FLAGS + ("ENABLE_WINNER_PROSE_RECONCILE",):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(params=["all_off", "all_on"])
def flag_state(request, monkeypatch):
    if request.param == "all_on":
        for name in SCORING_FLAGS:
            monkeypatch.setenv(name, "true")
    return request.param


# ---------------------------------------------------------------------------
# Fixtures — module-level builders, fresh dicts on every call.
# ---------------------------------------------------------------------------

def _one(brand, name, amount, rating, review_count, category="fragrance"):
    return {
        "brand": brand,
        "name": name,
        "category": category,
        "specs": {
            "volume": "100ml",
            "concentration": "eau de parfum",
            "longevity": "8 hours",
            "sillage": "strong",
            "scent_family": "woody",
        },
        "price": {"amount": amount, "currency": "BHD", "source_method": "page_scrape"},
        "rating": rating,
        "review_count": review_count,
    }


def _pair(brand_a, name_a, brand_b, name_b, amt_a=78.0, amt_b=95.0,
          rat_a=4.8, rat_b=4.2, rc_a=400, rc_b=150, category="fragrance"):
    return [
        _one(brand_a, name_a, amt_a, rat_a, rc_a, category),
        _one(brand_b, name_b, amt_b, rat_b, rc_b, category),
    ]


def REPEAT():
    """Brand-repeating pair: the `name` already starts with the brand."""
    return _pair("Xerjoff", "Xerjoff Naxos", "Xerjoff", "Xerjoff Erba Pura")


def CONTROL():
    """REPEAT with the brand prefix removed from both names — same prices,
    ratings, specs, so the two differ in exactly the spelling."""
    return _pair("Xerjoff", "Naxos", "Xerjoff", "Erba Pura")


def TOMFORD():
    """The review's own `test_first` inputs (verbatim brand/name)."""
    return _pair("TOM FORD", "TOM FORD OUD WOOD", "TOM FORD", "TOM FORD TOBACCO VANILLE")


def MIXED():
    """Only product 0 repeats its brand."""
    return _pair("Dior", "Dior Sauvage", "Chanel", "Bleu de Chanel")


def _svc():
    return get_scoring_service()


def _labels(dimension_winners):
    return {v["winner"] for v in dimension_winners.values()} - SENTINELS


def _tradeoffs(products):
    """compute_scores -> compute_tradeoff_pairs exactly as `scs` sync/SSE/partial
    call it: the DISPLAY names, the deterministic winner, the per-product scores."""
    svc = _svc()
    r = svc.compute_scores(products)
    names = _display_product_names(products)
    to = svc.compute_tradeoff_pairs(
        r["dimension_winners"], names, r["winner_index"], scores=r["scores"],
    )
    return r, names, to


def _control_summary_literal():
    """`build_scores_summary(compute_scores(CONTROL), display names)` captured at
    b63a8368 — the reference the REPEAT pair must equal after the fix."""
    return "\n".join([
        "Product scores (deterministic, qualitative summary):",
        "  Xerjoff Naxos: stronger overall (price tier: mid)",
        "    Per dimension: scent character: comparable, longevity: stronger, "
        "projection: stronger, versatility: comparable, value per wear: stronger, "
        "presentation: stronger",
        "  Xerjoff Erba Pura: slightly behind overall (price tier: premium)",
        "    Per dimension: scent character: comparable, longevity: weaker, "
        "projection: weaker, versatility: comparable, value per wear: weaker, "
        "presentation: weaker",
        "  Score winner: Xerjoff Naxos (clear lead)",
        "  Dimension leaders: scent character=N/A, longevity=Xerjoff Naxos, "
        "projection=Xerjoff Naxos, versatility=N/A, value per wear=N/A, "
        "presentation=Xerjoff Naxos",
        "  Note: Products are in different price tiers — value scoring "
        "adjusted for tier expectations.",
    ])


# ===========================================================================
# RED — the regression (tests 1-6 of the spec, plus the end-to-end partial path)
# ===========================================================================

def test_tradeoffs_non_empty_for_brand_repeating_pair(flag_state):
    """[RED 1] The review's `[]`: the production join returns nothing for a
    brand-repeating pair because the winner labels are the raw doubled spelling."""
    _, _, to = _tradeoffs(REPEAT())
    assert to != [], "compute_tradeoff_pairs joined raw labels against display names"
    assert len(to) == 1


def test_dimension_winners_keys_match_winner_evidence_spelling():
    """[RED 2] Review test_first, verbatim inputs: every non-sentinel winner label
    uses the same spelling `winner_evidence` already uses."""
    r = _svc().compute_scores(TOMFORD())
    assert _labels(r["dimension_winners"]) == {"TOM FORD OUD WOOD"}
    assert r["winner_evidence"], "fixture must produce a winner_evidence line"
    assert r["winner_evidence"][0].startswith("TOM FORD OUD WOOD")
    for label in _labels(r["dimension_winners"]):
        assert any(ev.startswith(label) for ev in r["winner_evidence"]), label


def test_none_brand_labels_match_winner_evidence_spelling():
    """[RED 2b] R4's coercion form: a `None` brand half must spell like
    `winner_evidence` ("Naxos"), not the raw "None Naxos" and not the `str(None)`
    "None Naxos" a bare `str(x)` coercion would produce (spec section 3.2)."""
    products = _pair(None, "Naxos", None, "Erba Pura")
    r = _svc().compute_scores(products)
    assert r["winner_evidence"] == ["Naxos draws stronger reviewer ratings"]
    assert _labels(r["dimension_winners"]) == {"Naxos"}
    assert _labels(r["dimension_winners"]) <= set(_display_product_names(products))


def test_dimension_winner_labels_are_drawn_from_display_names(flag_state):
    """[RED 3] The invariant `compute_tradeoff_pairs` joins on, stated directly."""
    products = REPEAT()
    r = _svc().compute_scores(products)
    labels = _labels(r["dimension_winners"])
    assert labels, "fixture must produce at least one measured dimension winner"
    assert labels <= set(_display_product_names(products)), labels


def test_key_tradeoff_prose_is_non_empty_for_brand_repeating_pair():
    """[RED 4] The user-visible string the hard-cap partial path (unflagged)
    and `reconcile_winner_prose` both take from `deterministic_verdict_fields`."""
    r, names, to = _tradeoffs(REPEAT())
    fields = deterministic_verdict_fields(r, names, to)
    assert fields["key_tradeoff"] == "Xerjoff Erba Pura stays competitive on longevity."


def test_hard_cap_partial_response_ships_runner_up_caption():
    """[RED 4b] End to end through the REAL hard-cap builder
    (`_build_partial_response`, `scs:3161`) with the stashes the sync path sets:
    the REPEAT pair must ship the same overview winner block, tradeoffs and
    persisted dimension_winners as the CONTROL pair (today: empty
    `key_tradeoff`, `tradeoffs == []`, raw doubled labels in `scoring`)."""
    def _build(products):
        svc = get_comparison_service()
        svc._partial_build_ctx = {
            "query": "Xerjoff Naxos vs Xerjoff Erba Pura",
            "region": "bahrain",
            "from_cache": False,
            "user_preferences": None,
            "category_used": "fragrances",
            "category_switched": False,
            "original_category": None,
        }
        svc._partial_product_data = products
        svc._partial_scoring_result = get_scoring_service().compute_scores(products)
        svc._partial_comparison = {}
        svc._partial_product_names = _display_product_names(products)
        return svc._build_partial_response(elapsed_seconds=30.0)

    rep, ctl = _build(REPEAT()), _build(CONTROL())
    assert ctl["overview"]["winner"]["key_tradeoff"] == (
        "Xerjoff Erba Pura stays competitive on longevity."
    ), "control must produce a caption, else this test cannot discriminate"
    assert rep["overview"]["winner"]["key_tradeoff"] == ctl["overview"]["winner"]["key_tradeoff"]
    assert rep["overview"]["tradeoffs"] == ctl["overview"]["tradeoffs"]
    assert rep["scoring"]["dimension_winners"] == ctl["scoring"]["dimension_winners"]


@pytest.mark.parametrize("aspect", ["winner_labels", "tradeoff_len", "key_tradeoff_shape"])
def test_parity_repeat_vs_control(aspect):
    """[RED 5] REPEAT and CONTROL have identical display names and identical
    scores, so every name-bearing output must be identical after the fix."""
    r_rep, n_rep, to_rep = _tradeoffs(REPEAT())
    r_ctl, n_ctl, to_ctl = _tradeoffs(CONTROL())
    assert n_rep == n_ctl  # precondition: the display spelling is shared
    if aspect == "winner_labels":
        assert r_rep["dimension_winners"] == r_ctl["dimension_winners"]
    elif aspect == "tradeoff_len":
        assert len(to_ctl) == 1, "control must produce a pair, else parity is vacuous"
        assert len(to_rep) == len(to_ctl)
        assert to_rep[0]["loser_wins"]["dimension"] == to_ctl[0]["loser_wins"]["dimension"]
        assert to_rep == to_ctl
    else:
        assert deterministic_verdict_fields(r_rep, n_rep, to_rep) == (
            deterministic_verdict_fields(r_ctl, n_ctl, to_ctl)
        )


def test_mixed_pair_only_one_product_repeats():
    """[RED 6] Only product 0 repeats its brand; the join must still pair."""
    r, _, to = _tradeoffs(MIXED())
    assert _labels(r["dimension_winners"]) == {"Dior Sauvage"}
    assert len(to) == 1
    assert to[0]["loser_wins"]["product"] == "Chanel Bleu de Chanel"


def test_three_product_repeat_labels_are_deduped():
    """[RED 12 — rewritten per R5] A three-product input still reaches `:1554`
    (only products 0 and 1 are compared); the correct fix changes its labels to
    the deduped spelling. The one-product half of the original pin is dropped:
    `compute_scores([p])` returns early and never reaches `:1554`."""
    products = [
        _one("Xerjoff", "Xerjoff Naxos", 78.0, 4.8, 400),
        _one("Xerjoff", "Xerjoff Erba Pura", 95.0, 4.2, 150),
        _one("Xerjoff", "Xerjoff Alexandria II", 180.0, 4.6, 250),
    ]
    r = _svc().compute_scores(products)
    assert _labels(r["dimension_winners"]) == {"Xerjoff Naxos"}
    # keys stay raw (R3) on this shape too
    assert set(r["price_tiers"]) == {
        "Xerjoff Xerjoff Naxos", "Xerjoff Xerjoff Erba Pura", "Xerjoff Xerjoff Alexandria II",
    }


# ===========================================================================
# RED — R3: the verdict-prompt summary (the main-path live effect, R1)
# ===========================================================================

def _summary(products):
    svc = _svc()
    return svc.build_scores_summary(svc.compute_scores(products), _display_product_names(products))


def test_scores_summary_price_tier_resolves_for_brand_repeating_pair():
    """[RED R3] `price tier: unknown` is the same regression: the deduped name
    misses the raw-keyed `price_tiers`. The index mirror resolves it."""
    tier_lines = [ln for ln in _summary(REPEAT()).splitlines() if "price tier:" in ln]
    assert tier_lines == [
        "  Xerjoff Naxos: stronger overall (price tier: mid)",
        "  Xerjoff Erba Pura: slightly behind overall (price tier: premium)",
    ]


def test_scores_summary_dimension_leaders_use_display_spelling():
    """[RED R1] The gpt-4o verdict prompt's `Dimension leaders:` line (sync and
    SSE, every brand-repeating compare) must agree with its own `Score winner:`
    line, which already uses the deduped name."""
    summary = _summary(REPEAT())
    leaders = [ln for ln in summary.splitlines() if ln.startswith("  Dimension leaders:")]
    assert leaders == [
        "  Dimension leaders: scent character=N/A, longevity=Xerjoff Naxos, "
        "projection=Xerjoff Naxos, versatility=N/A, value per wear=N/A, "
        "presentation=Xerjoff Naxos",
    ]
    assert "Xerjoff Xerjoff" not in summary


def test_scores_summary_repeat_equals_control(flag_state):
    """[RED R1+R3] Same display names, same scores -> byte-identical prompt."""
    assert _summary(REPEAT()) == _summary(CONTROL())


# ===========================================================================
# RED — R2: the offline shadow harness spells names the way production does
# ===========================================================================

def test_shadow_offline_summary_matches_production_spelling():
    """[RED R2] `scripts/shadow_experiments.py:762` builds RAW names; production
    (`scs:3692-3693`, `:4424-4425`) passes `_display_product_names`."""
    offline = se._compute_scores_summary_offline(REPEAT())
    assert "Xerjoff Xerjoff" not in offline
    assert offline == _summary(REPEAT())


def test_shadow_offline_summary_repeat_equals_control():
    """[RED R2] The shadow prompt must not depend on whether the L2 row's
    `name` carries the brand."""
    assert se._compute_scores_summary_offline(REPEAT()) == (
        se._compute_scores_summary_offline(CONTROL())
    )


# ===========================================================================
# PINS — green at b63a8368, must stay green
# ===========================================================================

_CONTROL_EXPECTED = {
    "dimension_winners": {
        "character_score": {"winner": "N/A", "margin": None},
        "longevity_score": {"winner": "Xerjoff Naxos", "margin": 12.0},
        "projection_score": {"winner": "Xerjoff Naxos", "margin": 12.0},
        "versatility_score": {"winner": "N/A", "margin": None},
        "wear_value_score": {"winner": "N/A", "margin": None},
        "presentation_score": {"winner": "Xerjoff Naxos", "margin": 14.2},
    },
    "price_tiers": {"Xerjoff Naxos": "mid", "Xerjoff Erba Pura": "premium"},
    "winner_evidence": ["Xerjoff Naxos draws stronger reviewer ratings"],
    "scores": {
        "product_0": {
            "breakdown": {
                "character_score": 50, "longevity_score": 96.0,
                "presentation_score": 86.7, "projection_score": 96.0,
                "versatility_score": 50, "wear_value_score": 100.0,
            },
            "missing_data": ["character_score", "versatility_score", "wear_value_score"],
            "overall": 77.1,
            "weights_used": {
                "character_score": 0.25, "longevity_score": 0.25,
                "presentation_score": 0.1, "projection_score": 0.15,
                "versatility_score": 0.15, "wear_value_score": 0.1,
            },
        },
        "product_1": {
            "breakdown": {
                "character_score": 50, "longevity_score": 84.0,
                "presentation_score": 72.5, "projection_score": 84.0,
                "versatility_score": 50, "wear_value_score": 30.0,
            },
            "missing_data": ["character_score", "versatility_score", "wear_value_score"],
            "overall": 63.9,
            "weights_used": {
                "character_score": 0.25, "longevity_score": 0.25,
                "presentation_score": 0.1, "projection_score": 0.15,
                "versatility_score": 0.15, "wear_value_score": 0.1,
            },
        },
    },
    "win_margin": 13.2,
    "winner_index": 0,
    "category_weights": {
        "character_score": 0.25, "longevity_score": 0.25,
        "presentation_score": 0.1, "projection_score": 0.15,
        "versatility_score": 0.15, "wear_value_score": 0.1,
    },
}


@pytest.mark.parametrize("key", list(_CONTROL_EXPECTED))
def test_control_pair_byte_identical(key):
    """[PIN 7] Non-repeating input is a no-op for the fix. Literals captured at
    b63a8368. Per R6 only the `dimension_winners` row can observe the change;
    the other rows are Preserve decoration (labelled, kept)."""
    assert _svc().compute_scores(CONTROL())[key] == _CONTROL_EXPECTED[key]


def test_control_summary_and_tradeoffs_unchanged():
    """[PIN 7b] R3 'the control pair unchanged': the CONTROL verdict-prompt
    summary and the CONTROL tradeoff/caption are byte-identical to b63a8368."""
    assert _summary(CONTROL()) == _control_summary_literal()
    r, names, to = _tradeoffs(CONTROL())
    assert to == [{
        "winner_wins": {"dimension": "presentation_score", "product": "Xerjoff Naxos", "margin": 14.2},
        "loser_wins": {"dimension": "longevity_score", "product": "Xerjoff Erba Pura", "margin": 0},
    }]
    assert deterministic_verdict_fields(r, names, to)["key_tradeoff"] == (
        "Xerjoff Erba Pura stays competitive on longevity."
    )


def test_price_tiers_keys_stay_raw():
    """[PIN 8] Scope fence (spec 2.3 item 1, R3): the `price_tiers` KEYS stay the
    raw brand+name spelling; the index mirror is unchanged."""
    r = _svc().compute_scores(REPEAT())
    assert set(r["price_tiers"]) == {"Xerjoff Xerjoff Naxos", "Xerjoff Xerjoff Erba Pura"}
    assert r["price_tiers_by_index"] == {"product_0": "mid", "product_1": "premium"}


def test_value_match_lookup_still_resolves():
    """[PIN 9 — Preserve decoration per R6, duplicate of 8] The raw-key read that
    `response_builder._compute_value_match` / `_compute_budget_mismatch` do."""
    products = REPEAT()
    r = _svc().compute_scores(products)
    got = [r["price_tiers"].get(f"{p['brand']} {p['name']}".strip()) for p in products]
    assert got == ["mid", "premium"]


@pytest.mark.parametrize(
    "brand,name",
    [("", ""), ("Xerjoff", ""), ("", "Naxos"), ("Apple", "Applesauce")],
    ids=["empty_empty", "brand_only", "name_only", "apple_applesauce"],
)
def test_degenerate_and_empty_identity_unchanged(brand, name):
    """[PIN 10] Shapes where the dedup equals the raw spelling (spec 3.1). The
    pair is (shape, a distinct weaker product) so the shape's own label is
    actually emitted. Per R6 the `apple_applesauce` row is the load-bearing one:
    it reddens under an argument-swapped `dedup_brand_name(name, brand)`; the
    other three rows are Preserve decoration."""
    products = _pair(brand, name, "Zeta", "Other Thing")
    r = _svc().compute_scores(products)
    raw0 = f"{brand} {name}".strip()
    winners = {v["winner"] for v in r["dimension_winners"].values()}
    assert raw0 in winners, winners
    assert winners - SENTINELS == {raw0}


def test_non_str_brand_degenerate_pair_does_not_raise():
    """[PIN 11 — rewritten per R4] Identical products with an int brand: the tie
    yields no `winner_evidence`, so `:914` never runs and `:1554` is the first
    place `dedup_brand_name` sees the int. Green today (raw f-string); reddens if
    the fix drops the `str(x or "")` coercion (AttributeError on `int.strip`)."""
    products = [_one(123, "Naxos", 78.0, 4.5, 300), _one(123, "Naxos", 78.0, 4.5, 300)]
    r = _svc().compute_scores(products)
    assert r["winner_evidence"] == []
    assert _labels(r["dimension_winners"]) <= {"123 Naxos"}


def test_non_str_name_degenerate_pair_does_not_raise():
    """[PIN 11b] Same shape with a list-valued `name` (spec 3.2 row)."""
    products = [_one("Xerjoff", ["Naxos"], 78.0, 4.5, 300),
                _one("Xerjoff", ["Naxos"], 78.0, 4.5, 300)]
    r = _svc().compute_scores(products)
    assert r["winner_evidence"] == []
    assert _labels(r["dimension_winners"]) <= {"Xerjoff ['Naxos']"}


def test_scores_summary_without_tier_maps_reports_unknown():
    """[PIN R3-a] A hand-built scoring_result carrying neither `price_tiers` nor
    `price_tiers_by_index` (the shape tests and older callers pass) must still
    render `price tier: unknown`, never raise."""
    sr = {
        "scores": {
            "product_0": {"overall": 87, "breakdown": {"longevity_score": 80}},
            "product_1": {"overall": 76, "breakdown": {"longevity_score": 70}},
        },
        "winner_index": 0,
        "win_margin": 11,
        "dimension_winners": {},
    }
    out = _svc().build_scores_summary(sr, ["A", "B"])
    assert "  A: stronger overall (price tier: unknown)" in out.splitlines()
    assert "  B: slightly behind overall (price tier: unknown)" in out.splitlines()


def test_shadow_offline_tier_lines_still_resolve():
    """[PIN R2-a] Today the shadow harness resolves the tier only because its raw
    names happen to match the raw keys. Green today; reddens if R2 dedups the
    names without R3's index read (the tier would fall to `unknown`)."""
    tier_lines = [ln for ln in se._compute_scores_summary_offline(REPEAT()).splitlines()
                  if "price tier:" in ln]
    assert len(tier_lines) == 2
    assert tier_lines[0].endswith("(price tier: mid)")
    assert tier_lines[1].endswith("(price tier: premium)")


def test_shadow_offline_control_summary_unchanged():
    """[PIN R2-b] Non-repeating names: the shadow prompt is byte-identical."""
    assert se._compute_scores_summary_offline(CONTROL()) == _control_summary_literal()


# ===========================================================================
# PINS added by the adversary fix pass (2026-09-23)
# ===========================================================================

def _hand_built_result(**tier_maps):
    """Two-product scoring_result shaped like the hand-built dicts older callers
    and tests pass to `build_scores_summary`; tier maps supplied by the caller."""
    sr = {
        "scores": {
            "product_0": {"overall": 87, "breakdown": {"longevity_score": 80}},
            "product_1": {"overall": 76, "breakdown": {"longevity_score": 70}},
        },
        "winner_index": 0,
        "win_margin": 11,
        "dimension_winners": {},
    }
    sr.update(tier_maps)
    return sr


def test_scores_summary_legacy_name_map_fallback():
    """[PIN R3-b] Ruling 1: the legacy `price_tiers.get(name)` lookup is the
    fallback when the result carries no `price_tiers_by_index` (a hand-built or
    pre-M20 result). Reddens if R3 drops the fallback and goes index-or-unknown."""
    sr = _hand_built_result(price_tiers={"A": "budget", "B": "luxury"})
    lines = _svc().build_scores_summary(sr, ["A", "B"]).splitlines()
    assert "  A: stronger overall (price tier: budget)" in lines
    assert "  B: slightly behind overall (price tier: luxury)" in lines


def test_scores_summary_index_map_wins_over_name_map():
    """[PIN R3-c] Ruling 1 precedence: `price_tiers_by_index` first, the name
    lookup only as a fallback. Reddens if the two lookups are reordered."""
    sr = _hand_built_result(
        price_tiers={"A": "budget", "B": "budget"},
        price_tiers_by_index={"product_0": "mid", "product_1": "premium"},
    )
    lines = _svc().build_scores_summary(sr, ["A", "B"]).splitlines()
    assert "  A: stronger overall (price tier: mid)" in lines
    assert "  B: slightly behind overall (price tier: premium)" in lines


def test_shadow_offline_summary_does_not_import_orchestrator(monkeypatch):
    """[PIN R2-c] `_compute_scores_summary_offline` must stay a scoring-only
    ($0, keyless) path, as it was at b63a8368. Importing
    `structured_comparison_service` builds AsyncOpenAI at import time, so a
    keyless `prepare` run would raise OpenAIError inside `build_verdict_inputs`'
    broad except and silently write `scores_summary=""` for every input.
    Blocking both modules and the key reproduces the keyless process."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "app.services.structured_comparison_service", None)
    monkeypatch.setitem(sys.modules, "app.services.openai_service", None)
    out = se._compute_scores_summary_offline(REPEAT())
    assert out == _control_summary_literal()


def test_shadow_offline_non_str_brand_degenerate_pair_does_not_raise():
    """[PIN R2-d / R4] An L2 row with a non-str brand on a tied pair: base
    produced a summary (raw f-string names); the fixed shadow path must too.
    Reddens if EITHER the `compute_scores` label coercion or the shadow names
    coercion is dropped."""
    products = [_one(123, "Naxos", 78.0, 4.5, 300), _one(123, "Naxos", 78.0, 4.5, 300)]
    out = se._compute_scores_summary_offline(products)
    assert "  123 Naxos: stronger overall (price tier: mid)" in out.splitlines()


def test_shadow_offline_none_brand_names_read_like_production():
    """[PIN R2-e / R4] Shadow L2 rows set `brand` from `sr.get('brand')`, so the
    brand can be None. The shadow names must coerce with `str(x or '')` exactly
    like `compute_scores`' labels: the prompt reads 'Naxos', never 'None Naxos'.
    Reddens if the shadow names drop the `or ''` half (bare `str(p.get(...))`)."""
    products = _pair(None, "Naxos", None, "Erba Pura")
    out = se._compute_scores_summary_offline(products)
    lines = out.splitlines()
    assert "  Naxos: stronger overall (price tier: mid)" in lines
    assert "  Erba Pura: slightly behind overall (price tier: premium)" in lines
    assert "None" not in out
    assert out == _summary(products)

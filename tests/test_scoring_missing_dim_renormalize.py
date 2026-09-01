"""M26 #101 — one-sided-missing dim renormalization behind ENABLE_MISSING_DIM_RENORM.

`MISSING_SCORE = 50` is injected into `overall` for absent dimensions, so a
product with NO data collects 50 while a genuinely measured 2.0-star rating
normalizes to 40 — no-data beats bad-data (PO-rubric-03), inverting the
product's promise on exactly the comparisons where the truth matters most.

Fix (flag ON): a dimension whose source signal is missing for at least one
but not ALL products is EXCLUDED from every product's `overall` and the
remaining weights are renormalized to sum to 1.0 — neither side is rewarded
or punished for the gap (exclude-and-renormalize, not a clamp). Missingness
is read from the authoritative `_<dim>_missing` flags, NEVER `== 50.0`
value-equality (a real 2.5-star review normalizes to exactly 50.0). The
excluded list ships as `excluded_dims` on each product's result (list, or
None when empty — mirroring `missing_data`'s shape) so the FE can stop
rendering a synthetic 50 bar for a cell that was never measured.

NOTE on the issue's strict-`>` phrasing for tests 1-2: under the issue's own
prescribed exclude-and-renormalize semantics, an otherwise-identical pair
differing ONLY in excluded (one-sided) signals lands at honest parity — the
measured product can no longer LOSE to the void, and ties break to it via
argmax. The pins below assert exactly that invariant (measured >= missing AND
winner_index == 0), which is red today (missing WINS: ~51.8 vs ~52.5) and
green after the fix.

Composition with ENABLE_BUNDLE_C_SCORING (FALSE in prod): that flag gates ONE
site — the per-dim raw-key emission in `_compute_raw_scores` (None vs the
MISSING_SCORE sentinel). The renormalization reads only the `_<dim>_missing`
flags (set unconditionally in `_normalize_scores`) and the normalized
`breakdown` values (signal arrays, also bundle-C-independent), so it composes
identically in BOTH bundle-C states — pinned below.

Flag OFF (default) must stay byte-identical to base b073918 — pinned by the
literal golden captured at that commit (test_flag_off_matches_recorded_golden).

M26b (reviewer-proven P1 inversions in the flag-ON path, red at ab80bfd):
  P1-A — the renormalized parity made the PRE-EXISTING price-authority
  all-missing exemption the decider: only the measured product paid the
  estimated/converted_usd delta, so the VOID outright won (55.0 vs 51.0, both
  orders). Fix: under the flag the authority treatment is SYMMETRIC — every
  product pays its own provenance delta, no all-missing exemption.
  P1-B — the "5 one-sided + 1 both-sided-missing" shape bypassed the
  effective_total == 0 guard, leaving an effective set with zero measured
  signal (dead 50/50 parity decided by argmax = product order). Fix: an
  effective set whose every dim is flagged missing for ALL products AND
  sentinel-valued falls back to the legacy sum, same as effective_total == 0.
  P2 — at exact parity the winner now tie-breaks to the product with MORE
  measured dims (flag-ON only) instead of degenerating to product order.
Invariant pinned VERBATIM from the issue's Expected-behavior #2: a product
with no rating can never rank above an otherwise-identical product with a
genuinely measured rating, at any star value.
"""
import json
import os

import pytest

from app.services import scoring_service
from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    MISSING_SCORE,  # noqa: F401 — documents the sentinel this file guards against
    ScoringService,
)

GOLDEN_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "missing_dim_renorm_flag_off_golden.json"
)

_SCORING_ENV_KNOBS = (
    "ENABLE_SPEC_FIELD_NORM",
    "ENABLE_MISSING_DIM_RENORM",
    "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "DISABLE_DIM_NORM_DAMPENING",
    "WINNER_DIM_GAP_TOLERANCE",
    "WINNER_VALUE_WEIGHT_SCALE",
    "WINNER_PRICE_AUTHORITY_POINTS",
)


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def clean_env(monkeypatch):
    for name in _SCORING_ENV_KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


@pytest.fixture
def flag_on(clean_env, monkeypatch):
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    yield


def _prod(name, *, rating, review_count, specs=None, price=25.0, fact_check=None,
          category="fragrances"):
    p = {
        "name": name,
        "category": category,
        "specs": specs if specs is not None else {
            "longevity": "8 hours", "volume": "100 ml", "concentration": "EDP",
        },
        "rating": rating,
        "review_count": review_count,
        "price": {"amount": price, "currency": "BHD", "source_method": "local_bhd"},
    }
    if fact_check is not None:
        p["fact_check"] = fact_check
    return p


def _inversion_pair():
    """The PO-rubric-03 inversion fixture: identical specs and price; A carries
    a genuinely measured BAD rating, B carries no rating data at all."""
    a = _prod("Measured Bad", rating=2.0, review_count=300)
    b = _prod("Data Void", rating=None, review_count=None)
    return [a, b]


def _overalls(res):
    return (
        res["scores"]["product_0"]["overall"],
        res["scores"]["product_1"]["overall"],
    )


# ---------------------------------------------------------------------------
# Red-first pins (fail at base b073918 with the flag ON)
# ---------------------------------------------------------------------------


def test_no_rating_does_not_beat_two_star_rating(service, flag_on):
    """A product with NO rating must never rank above an otherwise-identical
    product with a measured 2.0-star rating. Fails at base: the void collects
    the injected 50 on every gap while the real 2.0 earns 40 → B wins."""
    res = service.compute_scores(_inversion_pair())
    o0, o1 = _overalls(res)
    assert o0 >= o1, f"no-data must not outscore bad-data: measured={o0} void={o1}"
    assert res["winner_index"] == 0, (
        f"the measured product must win (parity ties break to it); "
        f"got winner_index={res['winner_index']} overalls=({o0}, {o1})"
    )


def test_one_star_does_not_beat_no_rating(service, flag_on):
    """Same pair at rating=1.0 — pins that the fix is EXCLUSION, not a partial
    clamp: any clamp floor above 20 still lets the void beat a 1.0-star
    product, exclusion removes the class of bug entirely."""
    products = _inversion_pair()
    products[0]["rating"] = 1.0
    res = service.compute_scores(products)
    o0, o1 = _overalls(res)
    assert o0 >= o1, f"no-data must not outscore a 1.0-star product: {o0} vs {o1}"
    assert res["winner_index"] == 0


def test_one_sided_missing_dim_excluded_from_both_overalls(service, flag_on):
    """The service's overall must equal the weighted mean over the non-excluded
    dims with the remaining weights renormalized to 1.0 — recomputed here from
    the payload's own breakdown/weights_used/excluded_dims, for BOTH products."""
    res = service.compute_scores(_inversion_pair())
    for pk in ("product_0", "product_1"):
        entry = res["scores"][pk]
        excluded = entry["excluded_dims"]
        assert isinstance(excluded, list) and excluded, (
            f"{pk}: the one-sided fixture must exclude at least one dim, got {excluded}"
        )
        weights = entry["weights_used"]
        effective = {d: w for d, w in weights.items() if d not in excluded}
        total = sum(effective.values())
        assert total > 0
        expected = sum(entry["breakdown"][d] * w / total for d, w in effective.items())
        assert entry["overall"] == pytest.approx(expected, abs=0.35), (
            f"{pk}: overall {entry['overall']} != renormalized mean {expected}"
        )


def test_effective_weights_sum_to_one(service, flag_on):
    """The renormalized weight set must sum to 1.0 (within 1e-6) for a fixture
    with exactly 1 excluded dim and one with 3 excluded dims — and the
    service's overall must be the mean under those weights."""
    one_excluded = [
        _prod("A", rating=4.0, review_count=800,
              specs={"longevity": "9 hours", "volume": "100 ml"},
              fact_check={"specs_verified": 3, "specs_likely": 1}, price=25.0),
        _prod("B", rating=None, review_count=300,
              specs={"longevity": "6 hours", "volume": "50 ml"},
              fact_check={"specs_verified": 1, "specs_flagged": 2}, price=30.0),
    ]
    three_excluded = _inversion_pair()
    for products, want_excluded in ((one_excluded, 1), (three_excluded, 3)):
        res = service.compute_scores(products)
        for pk in ("product_0", "product_1"):
            entry = res["scores"][pk]
            excluded = entry["excluded_dims"] or []
            assert len(excluded) == want_excluded, (
                f"{pk}: expected exactly {want_excluded} excluded dims, got {excluded}"
            )
            weights = entry["weights_used"]
            effective = {d: w for d, w in weights.items() if d not in excluded}
            total = sum(effective.values())
            renormalized = {d: w / total for d, w in effective.items()}
            assert sum(renormalized.values()) == pytest.approx(1.0, abs=1e-6)
            expected = sum(
                entry["breakdown"][d] * w for d, w in renormalized.items()
            )
            assert entry["overall"] == pytest.approx(expected, abs=0.35)


def test_excluded_dims_key_present_and_shaped_like_missing_data(service, flag_on):
    """`excluded_dims` mirrors `missing_data`'s shape exactly: a list on the
    one-sided fixture, None when nothing is excluded (never a bare absence
    while the flag is ON)."""
    res = service.compute_scores(_inversion_pair())
    for pk in ("product_0", "product_1"):
        entry = res["scores"][pk]
        assert "excluded_dims" in entry
        assert isinstance(entry["excluded_dims"], list)
    clean = [
        _prod("A", rating=2.5, review_count=400,
              specs={"longevity": "9 hours", "volume": "100 ml"},
              fact_check={"specs_verified": 3, "specs_likely": 1}, price=25.0),
        _prod("B", rating=4.0, review_count=900,
              specs={"longevity": "6 hours", "volume": "50 ml"},
              fact_check={"specs_verified": 1, "specs_flagged": 2}, price=30.0),
    ]
    res = service.compute_scores(clean)
    for pk in ("product_0", "product_1"):
        entry = res["scores"][pk]
        assert "excluded_dims" in entry
        assert entry["excluded_dims"] is None, (
            f"{pk}: nothing is one-sided-missing here, got {entry['excluded_dims']}"
        )


# ---------------------------------------------------------------------------
# Green-from-day-one guards
# ---------------------------------------------------------------------------


def test_both_sided_missing_unchanged(service, clean_env, monkeypatch):
    """A signal missing on BOTH sides is not one-sided: overall must equal the
    flag-OFF value exactly (both-sided dims keep today's behavior)."""
    def build():
        return [
            _prod("A", rating=None, review_count=600,
                  specs={"longevity": "9 hours", "volume": "100 ml"},
                  fact_check={"specs_verified": 3, "specs_likely": 1}, price=25.0),
            _prod("B", rating=None, review_count=200,
                  specs={"longevity": "6 hours", "volume": "50 ml"},
                  fact_check={"specs_verified": 1, "specs_flagged": 2}, price=30.0),
        ]

    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    res_off = service.compute_scores(build())
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    res_on = service.compute_scores(build())
    for pk in ("product_0", "product_1"):
        assert res_on["scores"][pk]["overall"] == res_off["scores"][pk]["overall"]
        assert res_on["scores"][pk]["excluded_dims"] is None


def test_all_dims_one_sided_missing_does_not_divide_by_zero(service, clean_env, monkeypatch):
    """Product A fully populated vs product B with NO signals: every dim is
    one-sided-missing, the effective weight total is 0, and the service must
    fall back to the legacy un-renormalized sum instead of dividing by zero.

    M26b P1-A update: the legacy SUM is still preserved for both products, but
    the price-authority treatment is now SYMMETRIC under the flag — the
    all-missing product is no longer exempt from the provenance delta (its
    absent price is estimate-grade → −4.0), so its flag-ON overall sits the
    authority delta below its flag-OFF value. The fully-measured product
    (trusted local_bhd price, delta 0) stays exactly equal."""
    def build():
        a = _prod("Full", rating=4.4, review_count=500,
                  fact_check={"specs_verified": 3, "specs_likely": 1}, price=25.0)
        b = {
            "name": "Empty", "category": "fragrances", "specs": {},
            "rating": None, "review_count": None,
            "price": {"amount": None, "currency": "BHD"},
        }
        return [a, b]

    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    res_off = service.compute_scores(build())
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    res_on = service.compute_scores(build())  # must not raise
    assert res_on["scores"]["product_0"]["overall"] == res_off["scores"]["product_0"]["overall"], (
        "product_0: the all-one-sided edge must keep the legacy sum (trusted "
        "price → no authority delta)"
    )
    assert res_on["scores"]["product_1"]["overall"] == pytest.approx(
        max(0.0, res_off["scores"]["product_1"]["overall"] - 4.0)
    ), (
        "product_1: legacy sum preserved, minus the now-symmetric "
        "estimate-grade authority delta (M26b P1-A — no all-missing exemption "
        "under the flag)"
    )
    assert res_on["winner_index"] == 0


def test_two_point_five_star_is_not_treated_as_missing(service, flag_on):
    """The MISSING_SCORE collision guard: a real 2.5-star review normalizes to
    exactly 50.0 — the renormalization must read `_<dim>_missing`, never
    `== 50.0`, so the review dim is NOT excluded here."""
    products = [
        _prod("A", rating=2.5, review_count=400,
              specs={"longevity": "9 hours", "volume": "100 ml"},
              fact_check={"specs_verified": 3, "specs_likely": 1}, price=25.0),
        _prod("B", rating=4.0, review_count=900,
              specs={"longevity": "6 hours", "volume": "50 ml"},
              fact_check={"specs_verified": 1, "specs_flagged": 2}, price=30.0),
    ]
    res = service.compute_scores(products)
    for pk in ("product_0", "product_1"):
        excluded = res["scores"][pk].get("excluded_dims") or []
        assert "projection_score" not in excluded, (
            f"{pk}: a genuine 2.5-star review (50.0) must not be excluded; "
            f"got {excluded}"
        )


def test_renorm_composes_with_bundle_c_both_states(service, clean_env, monkeypatch):
    """ENABLE_BUNDLE_C_SCORING gates only the per-dim raw emission in
    _compute_raw_scores — the renormalization must produce the same overalls
    and the same winner in BOTH bundle-C states."""
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    results = {}
    for bundle_c in ("false", "true"):
        monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", bundle_c)
        monkeypatch.setattr(
            scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False
        )
        results[bundle_c] = service.compute_scores(_inversion_pair())
    # Reset the cached global so this test does not leak the last state.
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    for bundle_c, res in results.items():
        o0, o1 = _overalls(res)
        assert o0 >= o1 and res["winner_index"] == 0, (
            f"bundle_c={bundle_c}: inversion fix must hold; overalls=({o0}, {o1}) "
            f"winner={res['winner_index']}"
        )
    assert _overalls(results["false"]) == _overalls(results["true"]), (
        "the renormalized overalls must be identical in both bundle-C states"
    )


# ---------------------------------------------------------------------------
# M26b reviewer pins — red at ab80bfd, green after the P1-A / P1-B / P2 fixes.
# Every ranked pin runs in BOTH product orders: the base failures were proven
# order-independent (not a tie-break artifact), so the pins must be too.
# ---------------------------------------------------------------------------


def _authority_pair(source_method, *, rating=4.8):
    """The issue's otherwise-identical pair (identical specs AND identical
    price) whose SHARED price provenance is `source_method`; A carries a
    genuinely measured rating, B is a rating/review data void. With an
    estimate-grade provenance, base ab80bfd let the void OUTRIGHT WIN in both
    orders (renorm parity + the one-sided authority exemption)."""
    a = _prod("Measured", rating=rating, review_count=300)
    b = _prod("Void", rating=None, review_count=None)
    for p in (a, b):
        p["price"]["source_method"] = source_method
    return a, b


def _ordered(pair, void_first):
    a, b = pair
    products = [b, a] if void_first else [a, b]
    measured_idx = 1 if void_first else 0
    return products, measured_idx


@pytest.mark.parametrize("void_first", [False, True], ids=["measured_first", "void_first"])
@pytest.mark.parametrize("source_method", ["estimated", "converted_usd"])
def test_void_never_beats_measured_under_untrusted_price(
    service, flag_on, source_method, void_first
):
    """P1-A pins 1+2 — measured-4.8 vs void with an estimate-grade shared
    price provenance, BOTH orders: the measured product must never rank below
    the void. Red at ab80bfd: the all-missing authority exemption penalized
    ONLY the measured product on renormalized parity (void 55.0 vs measured
    51.0 estimated / 53.0 converted_usd, either order)."""
    products, midx = _ordered(_authority_pair(source_method), void_first)
    res = service.compute_scores(products)
    o = _overalls(res)
    assert o[midx] >= o[1 - midx], (
        f"{source_method}/void_first={void_first}: no-data must not outscore "
        f"measured data: measured={o[midx]} void={o[1 - midx]}"
    )
    assert res["winner_index"] == midx, (
        f"{source_method}/void_first={void_first}: the measured product must "
        f"win (parity ties break to more measured dims); got "
        f"winner_index={res['winner_index']} overalls={o}"
    )


@pytest.mark.parametrize("void_first", [False, True], ids=["measured_first", "void_first"])
def test_issue_headline_two_star_beats_void_with_estimated_price(
    service, flag_on, void_first
):
    """P1-A pin 3 — the issue's own headline fixture (measured 2.0-star vs
    void) with an ESTIMATED price, flag ON: measured >= void AND the winner is
    the measured product, at the star value the issue itself names. Red at
    ab80bfd (void 55.0 vs measured 51.0)."""
    products, midx = _ordered(_authority_pair("estimated", rating=2.0), void_first)
    res = service.compute_scores(products)
    o = _overalls(res)
    assert o[midx] >= o[1 - midx], (
        f"headline inversion: measured-2.0={o[midx]} void={o[1 - midx]}"
    )
    assert res["winner_index"] == midx


def _full_product(source_method="local_bhd"):
    """Fully-measured product: distinct specs + rating + review_count + a real
    price. Deliberately NO fact_check — reliability missing on BOTH sides is
    the prod-common shape that builds '5 one-sided + 1 both-sided-missing'."""
    return {
        "name": "Full",
        "category": "fragrances",
        "specs": {"longevity": "9 hours", "volume": "100 ml",
                  "concentration": "EDP"},
        "rating": 4.0,
        "review_count": 500,
        "price": {"amount": 25.0, "currency": "BHD",
                  "source_method": source_method},
    }


def _total_void():
    """A product with NO data at all — no specs, no rating, no reviews, no
    price amount."""
    return {
        "name": "Void", "category": "fragrances", "specs": {},
        "rating": None, "review_count": None,
        "price": {"amount": None, "currency": "BHD"},
    }


@pytest.mark.parametrize("void_first", [False, True], ids=["measured_first", "void_first"])
def test_total_void_never_beats_fully_measured_trusted_price(
    service, flag_on, void_first
):
    """P1-B pin 4 — total void vs fully-measured with a TRUSTED price, BOTH
    orders: the measured product wins, and NOT via argmax-on-parity — its
    overall must lead STRICTLY (red at ab80bfd: dead 50.0/50.0 parity crowned
    whichever product sat at index 0)."""
    products = ([_total_void(), _full_product()] if void_first
                else [_full_product(), _total_void()])
    midx = 1 if void_first else 0
    res = service.compute_scores(products)
    o = _overalls(res)
    assert res["winner_index"] == midx, (
        f"void_first={void_first}: the fully-measured product must win; got "
        f"winner_index={res['winner_index']} overalls={o}"
    )
    assert o[midx] > o[1 - midx], (
        f"void_first={void_first}: the win must NOT be an argmax-on-parity "
        f"coin toss — overalls={o} are not strictly ordered"
    )


def test_five_one_sided_plus_one_both_missing_engages_legacy_fallback(
    service, clean_env, monkeypatch
):
    """P1-B pin 5 — the '5 one-sided + 1 both-sided-missing' shape must NOT be
    decided on sentinel-only dims: the degenerate effective set (reliability
    missing on BOTH sides is the only survivor) falls back to the legacy sum,
    where the measured product's one-sided real signal is visible again. Red
    at ab80bfd: the renorm branch fired (excluded_dims == 5 dims) and produced
    dead 50/50 parity."""
    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    res_off = service.compute_scores([_full_product(), _total_void()])
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    res_on = service.compute_scores([_full_product(), _total_void()])

    # Pin the intended shape so the fixture cannot silently drift: exactly one
    # both-sided-missing dim (reliability -> versatility_score) on the
    # measured side, everything missing on the void side.
    assert res_on["scores"]["product_0"]["missing_data"] == ["versatility_score"]
    assert len(res_on["scores"]["product_1"]["missing_data"]) == 6

    # The legacy fallback engaged: nothing was renormalized/excluded.
    for pk in ("product_0", "product_1"):
        assert res_on["scores"][pk]["excluded_dims"] is None, (
            f"{pk}: the degenerate effective set must take the legacy "
            f"fallback, got excluded_dims={res_on['scores'][pk]['excluded_dims']}"
        )
    # The measured product's real data is visible again (legacy sum; trusted
    # price -> no authority delta).
    assert (res_on["scores"]["product_0"]["overall"]
            == res_off["scores"]["product_0"]["overall"])
    # And the comparison is NOT decided on sentinel-only dims.
    assert (res_on["scores"]["product_0"]["overall"]
            > res_on["scores"]["product_1"]["overall"])
    assert res_on["winner_index"] == 0


@pytest.mark.parametrize("void_first", [False, True], ids=["measured_first", "void_first"])
def test_total_void_never_beats_fully_measured_estimated_price(
    service, flag_on, void_first
):
    """P1-B companion — same total-void pair but the full product's price is
    ESTIMATED: red at ab80bfd the void won in EITHER order (46.0 vs 50.0,
    exemption + parity). After the fix the legacy fallback + symmetric
    authority keep the measured product strictly ahead."""
    products = ([_total_void(), _full_product("estimated")] if void_first
                else [_full_product("estimated"), _total_void()])
    midx = 1 if void_first else 0
    res = service.compute_scores(products)
    o = _overalls(res)
    assert res["winner_index"] == midx
    assert o[midx] > o[1 - midx]


@pytest.mark.parametrize("void_first", [False, True], ids=["measured_first", "void_first"])
def test_parity_tie_break_prefers_more_measured_dims(service, flag_on, void_first):
    """P2 — renormalized parity with a TRUSTED shared price (no authority
    deltas at all): the winner must still be the measured product in BOTH
    orders. Red at ab80bfd in the void-first order only (argmax-on-parity
    crowned index 0 = the void)."""
    products, midx = _ordered(_authority_pair("local_bhd"), void_first)
    res = service.compute_scores(products)
    o = _overalls(res)
    assert o[midx] >= o[1 - midx]
    assert res["winner_index"] == midx, (
        f"void_first={void_first}: parity must tie-break to the product with "
        f"more measured dims; got winner_index={res['winner_index']} overalls={o}"
    )


# ---------------------------------------------------------------------------
# Flag-OFF byte-identity golden (captured at base b073918)
# ---------------------------------------------------------------------------


def golden_fixture_products(category):
    """Deterministic per-category pair carrying a one-sided review/popularity
    gap (so a flag leak would move `overall` via the renormalization) plus
    real schema-driven spec signals on both sides."""
    from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS

    schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
    schema = CATEGORY_SPEC_SCHEMAS[schema_key]
    specs_a = {f: f"{(i + 3) * 4} units" for i, f in enumerate(schema[:4])}
    specs_b = {f: f"{(i + 1) * 7} units" for i, f in enumerate(schema[:3])}
    a = _prod(f"{category} A", rating=4.1, review_count=350,
              specs=specs_a,
              fact_check={"specs_verified": 3, "specs_likely": 1},
              price=40.0, category=category)
    b = _prod(f"{category} B", rating=None, review_count=None,
              specs=specs_b,
              fact_check={"specs_verified": 2, "specs_flagged": 1},
              price=55.0, category=category)
    return [a, b]


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS.keys()))
def test_flag_off_matches_recorded_golden(service, clean_env, category):
    """With ENABLE_MISSING_DIM_RENORM unset, compute_scores output must equal
    the literal golden captured at base b073918 — the mandatory flag-OFF
    byte-identity equivalent for the scoring surface."""
    with open(GOLDEN_PATH, encoding="utf-8") as fh:
        golden = json.load(fh)
    result = service.compute_scores(golden_fixture_products(category))
    assert json.loads(json.dumps(result)) == golden[category], (
        f"flag-OFF scoring output for {category!r} deviates from the base "
        f"b073918 golden"
    )

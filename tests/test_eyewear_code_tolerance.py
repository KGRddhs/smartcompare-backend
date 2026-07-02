"""KPI Wave E — Luxottica MODEL-CODE-CONFIRMED eyewear tolerance (kpi-fash-004).

THE LIVE FAILURE (2026-07-02, reproduced through the runtime): the warmed KPI
was 17/18 x3 stable; the only miss was 'Ray-Ban Aviator RB3025' -> estimated.
noon-BH search returns 10 buyable Ray-Ban RB3025 hits, but _match_noon_hits
matched 0. Bisect through the REAL gate chain (counterfeit / accessory /
numbers_match / strict / variant / _axis_mismatch all PASS) pinned the single
killing gate: _selection_match's VARIANT-ADD direction — the noon title
"Unisex Polarized Aviator Sunglasses - RB3025 002/58 58 - Lens Size: 58 mm -
Black" adds the distinctive tokens {002, 58, 58mm, lens, size, polarized}
(the Luxottica NNN/NN colorway code + the lens-size annotation + an eyewear
descriptor) over the query core {aviator, rb3025}.

THE BOUNDED FIX (the established structured-code-override principle, here
TITLE-derived, at the SHARED matcher layer so namshi/optica/6thstreet eyewear
benefit too): when the QUERY carries a Luxottica-family model-code token
((rb|rx|oo|po|ar|pr|ve|dg)\\d{3,}, 0-prefix-folded) AND the candidate title
carries the SAME code, the code is query-confirmed exact-model evidence —
tolerate title-side ONLY:
  (a) the NNN/NN Luxottica colorway code ADJACENT to the model code (and its
      trailing bare size digit run "002/58 58"),
  (b) lens-size annotations ("Lens Size: 58 mm" / bare "58 mm"),
  (c) the eyewear descriptors unisex/polarized/gradient/mirrored.
Query-CONDITIONAL (the BF3 asymmetry): a token the query itself states is
NEVER dropped from the title side, so a query-pinned colorway keeps the axis.
numbers_match is untouched globally; the tolerance lives inside
_selection_match's fashion branch only.

Both directions pinned below: the flip (noon hit-0 + the full noon gate
chain + the cache-write gate + the KPI contract) AND the fences (different
model code, different colorway, non-eyewear query, namshi 0-prefix pin).
"""
import pytest

from app.services.noon_service import _gates_pass, _hit_fields, _match_noon_hits
from app.services.price_service import (
    _selection_match,
    should_cache_price,
)


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


QUERY = "Ray-Ban Aviator RB3025"

# The REAL noon-BH search hit (raw sample from the 2026-07-02 live repro),
# trimmed to the fields _hit_fields consumes.
NOON_HIT_0 = {
    "sku": "N13000706A",
    "brand": "Ray-Ban",
    "name": ("Unisex Polarized Aviator Sunglasses - RB3025 002/58 58 - "
             "Lens Size: 58 mm - Black"),
    "price": 110.57,
    "sale_price": 60.82,
    "url": "unisex-polarized-aviator-sunglasses-rb3025-002-58-58-lens-size-58-mm-black",
    "is_buyable": True,
    "store_name": "TRI VISION OPTICALS LLC",
}
HIT_0_SURFACE = ("Ray-Ban Unisex Polarized Aviator Sunglasses - RB3025 002/58 58 - "
                 "Lens Size: 58 mm - Black")


def _sel(query, title, candidate_brand="Ray-Ban"):
    return _selection_match(query, title, "fashion", candidate_brand=candidate_brand)


# ---------------------------------------------------------------------------
# THE FLIP — the live-failing title must now pass the shared matcher and the
# full noon gate chain (this is the kpi-fash-004 unlock).
# ---------------------------------------------------------------------------

class TestTheFlip:
    def test_noon_hit0_title_passes_selection_match(self):
        assert _sel(QUERY, HIT_0_SURFACE) is True

    def test_noon_hit0_full_gate_chain_passes(self):
        assert _gates_pass(QUERY, HIT_0_SURFACE, "Ray-Ban", "fashion") is True

    def test_match_noon_hits_matches_the_real_hit(self):
        matches = _match_noon_hits([NOON_HIT_0], QUERY, "fashion")
        assert matches, "the real buyable RB3025 hit must match"
        assert matches[0]["sku"] == "N13000706A"
        assert matches[0]["amount"] == 60.82  # sale_price wins over price

    def test_hit_fields_reads_name_into_title(self):
        # NOT a bug (bisect note): the return dict's key is "title", populated
        # from hits[].name — pin the contract so a probe reading f["title"]
        # stays correct and the raw "name" key is never silently dropped.
        f = _hit_fields(NOON_HIT_0)
        assert f["title"].startswith("Unisex Polarized Aviator Sunglasses")
        assert "name" not in f

    def test_descriptors_gradient_mirrored_tolerated(self):
        title = ("Ray-Ban Gradient Mirrored Aviator Sunglasses - RB3025 002/58 - "
                 "Lens Size: 58 mm - Gold")
        assert _sel(QUERY, title) is True

    def test_zero_prefixed_title_code_confirms_too(self):
        # The catalog 0-prefix form ("0Rb3025") is the SAME code after the
        # established fold — the ADJACENT colorway + lens tolerance applies.
        title = "Ray-Ban 0Rb3025 002/58 Aviator Sunglasses - Lens Size: 58 mm"
        assert _sel(QUERY, title) is True

    def test_query_stating_same_colorway_passes(self):
        # Query-conditional subtraction keeps the query's own tokens required —
        # and a title carrying exactly them still matches.
        assert _sel("Ray-Ban Aviator RB3025 002/58", HIT_0_SURFACE) is True


# ---------------------------------------------------------------------------
# THE FENCES — both directions stay closed.
# ---------------------------------------------------------------------------

class TestTheFences:
    def test_different_model_code_still_rejects(self):
        # RB3026 is a DIFFERENT frame — no shared code, no tolerance, and the
        # leak direction (rb3025 missing) rejects.
        title = ("Ray-Ban Unisex Polarized Aviator Sunglasses - RB3026 002/58 - "
                 "Lens Size: 58 mm - Black")
        assert _sel(QUERY, title) is False

    def test_query_pinned_colorway_rejects_different_colorway(self):
        # A query that ITSELF states a colorway keeps the axis: 901/58 vs the
        # title's 002/58 must NOT match.
        assert _sel("Ray-Ban Aviator RB3025 901/58", HIT_0_SURFACE) is False

    def test_non_eyewear_query_gains_nothing(self):
        # No Luxottica code in the query -> no tolerance: the same annotation
        # junk stays a distinctive variant-add and rejects.
        title = "Nike Dunk Low 002/58 - Lens Size: 58 mm"
        assert _selection_match(
            "Nike Dunk Low", title, "fashion", candidate_brand="Nike",
        ) is False

    def test_namshi_plain_title_keeps_passing(self):
        # The pre-existing namshi unlock (0-prefix fold) is untouched.
        assert _sel(QUERY, "Ray-Ban 0Rb3025 Aviator Sunglasses") is True

    def test_descriptors_not_tolerated_without_code_confirmation(self):
        # 'polarized' stays distinctive when the title does NOT carry the
        # query's code (different-code title) — no descriptor freebie.
        title = "Ray-Ban Polarized Wayfarer Sunglasses RB2140"
        assert _sel(QUERY, title) is False


# ---------------------------------------------------------------------------
# OFFLINE CHAIN — the resolved noon dict shape must survive the cache-write
# gate and COUNT in the KPI contract against the REAL kpi-fash-004 truth entry.
# ---------------------------------------------------------------------------

RESOLVED_SHAPE = {
    "amount": 60.82,
    "currency": "BHD",
    "retailer": "noon.com",
    "url": ("https://www.noon.com/bahrain-en/"
            "unisex-polarized-aviator-sunglasses-rb3025-002-58-58-lens-size-58-mm-black/"
            "N13000706A/p/"),
    "estimated": False,
    "source_method": "page_scrape_jsonld",
    "title": ("Unisex Polarized Aviator Sunglasses - RB3025 002/58 58 - "
              "Lens Size: 58 mm - Black"),
    "confidence": 0.9,
    "brand": "Ray-Ban",
    "seller": "TRI VISION OPTICALS LLC",
    "in_stock": True,
}

TRUTH_ENTRY = {
    "id": "kpi-fash-004",
    "query": "Ray-Ban Aviator RB3025",
    "category": "fashion",
    "region": "bahrain",
    "expected": {"brand": "Ray-Ban", "model": "Aviator RB3025"},
}


class TestOfflineChain:
    def test_should_cache_price_accepts_resolved_dict(self):
        assert should_cache_price(QUERY, dict(RESOLVED_SHAPE), "fashion") is True

    def test_usable_exact_genuine_counts_it(self):
        from scripts.eval_runner import usable_exact_genuine_for_product
        body = {"overview": {"products": [{"price": dict(RESOLVED_SHAPE)}]}}
        assert usable_exact_genuine_for_product(body, 0, TRUTH_ENTRY) is True

    def test_usable_exact_genuine_rejects_wrong_code_dict(self):
        from scripts.eval_runner import usable_exact_genuine_for_product
        wrong = dict(RESOLVED_SHAPE)
        wrong["title"] = ("Unisex Polarized Aviator Sunglasses - RB3026 002/58 - "
                          "Lens Size: 58 mm - Black")
        body = {"overview": {"products": [{"price": wrong}]}}
        assert usable_exact_genuine_for_product(body, 0, TRUTH_ENTRY) is False

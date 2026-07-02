"""Wave D (genuine-price KPI) — D0: close the Wave C convergence residuals.

Every finding re-derived from the convergence re-sweeps
(wavec_leakConvergence.json CV1-CV7 + wavec_kpi18.json CV-1..4, 2026-07-02;
each repro reproduced through the REAL runtime functions before fixing):

CV1 (MED, leak) _STRUCTURED_OVERRIDE_BLOCK_TOKENS missed the baby/infant
     sibling segments (the original RS3 fix-direction listed them; C1 dropped
     them) and the multipack sellable-unit wordings ("Twin Pack" / "2-Pack" /
     "Multipack" — common GCC polo/tee listings). Each is a differently-priced
     sellable unit sharing the model's style code, so a query-confirmed code
     must not waive the variant fence. normalize_words folds hyphens
     ("twin-pack" -> "twinpack") and splits spaced forms ("twin pack" ->
     {"twin","pack"}), so BOTH the glued and the bare tokens are blocked.
     Pinned at BOTH override ends (should_cache_price parity + the algolia
     adapter override) and both directions (base L1212 unlock + query-stated
     asymmetry).

CV2 (MED, leak) the C2 laptop-noun keyboard exemption admitted a FULL-SPEC
     keyboard PART listing as the laptop when priced above the 50-BHD flagship
     floor ("Arabic Keyboard for Apple MacBook Air 13 M5 512GB" @ 59.9:
     accessory-exempt + layout-strip collapse + 'keyboard'/'for' padding ->
     _catalog_match_hit accepted). Bound chosen: the exemption requires the
     laptop DEVICE NOUN to appear BEFORE the keyboard token (GCC retailer
     laptop rows all head with the device — sharafdg/extra/IdeaPad pins — while
     part listings head with the part), AND part/compat phrasing
     ("Keyboard for ..." / "Keyboard compatible ...") always keeps the
     accessory flag. The two REJECTED alternatives: a storage-or-RAM-token
     requirement FAILS the leak (the part title carries the laptop's full spec
     set INCLUDING 512GB — that is exactly what makes it leak); a
     layout-phrase-only exemption FAILS too ("Arabic Keyboard" IS a layout
     phrase and the leak title heads with it). Fail direction of any residual
     is over-flagging -> broad is_accessory -> fail-closed.

CV3 (MED, wrong-price ingress — PRE-EXISTING catalog content) LIVE
     bahrain-tier NON-RETAIL rows in data/bh_gcc_sources.json: bh.opensooq.com
     (user classifieds) + dubizzle.com.bh (classifieds, OLX family) +
     bh.labeb.com + comparebh.com (price-comparison aggregators, the F6
     pricena/kanbkam class). All four were registry-loadable flag-ON, curl
     page-scrape-wired, and weight-3.0 bahrain-tier — a classifieds/aggregator
     page's self-asserted Product JSON-LD would serve+cache as genuine
     page_scrape_jsonld. Demoted status="dead" (the canonical liveness-gate
     write, A7 ourshopee precedent — the generator's idempotent merge preserves
     it) with a "note" field; the generator's F6 skip set is extended to the
     whole non-retail class (suffix-aware) so a re-consolidation never
     re-emits it. The tripwire below greps the REAL data file.

CV4 (LOW, over-rejection) label-BEFORE core-count phrasing ("CPU 10-core GPU
     8-core") bound the FOLLOWING word, labeling 10 as GPU — the EXACT bin
     over-rejected vs the label-after form. A cpu/gpu word immediately
     PRECEDING the count now binds too (preferred over the trailing word when
     both are present); the gap-scoped scan keeps ONE label word from binding
     twice ("10-core CPU 10-core GPU" stays cpu={10}, gpu={10}).

CV5 (LOW, over-rejection) _FASHION_NECKLINE_BIGRAM_RE was ASCII-hyphen/space
     only — a U+2011 "Crew‑Neck" title (the same unicode-hyphen family C2
     canonized as _UNICODE_HYPHENS) stayed distinctive and a genuine enriched
     title over-rejected. The bigram separator now accepts the whole family.

Wave D polish (review findings W1 + W2, 2026-07-02):

W1  (LOW, wrong-price ingress) dubizzle.com.bh stayed organic-harvest-eligible
    via the pre-existing .bh-TLD rung in scs._organic_host_bh_gcc_retail, and
    the four CV3-demoted rows remain in the ANY-status locale-path anchor. A
    non-retail blocklist (scs._ORGANIC_NON_RETAIL_DOMAINS, mirroring the
    generator's _NON_RETAIL_DOMAINS — duplicated so the deployed service
    never imports scripts/; the parity pin below keeps them in sync) now
    OVERRIDES every trust rung. Runtime pins live in test_organic_pdp_harvest.

W2  (LOW, over-rejection — the CV1 fix's own blind spot) bare "twin" is
    DROPPED from _STRUCTURED_OVERRIDE_BLOCK_TOKENS: it over-rejected Fred
    Perry "Twin Tipped" mainline polos and is REDUNDANT for the multipack
    class (bare "pack" covers every spaced "<x> Pack" form; the glued tokens
    cover "Twin-Pack"/"Twinpack"). And "baby" is BOUNDED: the "Baby Blue" /
    "Baby Pink" COLORWAY bigram is a shade name on an adult mainline SKU —
    "baby" no longer blocks when every surface occurrence is part of the
    colorway bigram; the sibling-SEGMENT sense ("Polo Baby - 6-12 months")
    keeps blocking, and a surface carrying BOTH senses stays blocked.

Run: python -m pytest tests/test_wave_d_cv_polish.py -q
"""
import json
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

import app.services.algolia_service as alg
from app.services import source_router as sr
from app.services.algolia_service import ALGOLIA_EXPLICIT_STORES
from app.services.price_service import (
    _core_count_mismatch,
    _labeled_core_counts,
    _selection_match,
    _structured_override_variant_blocked,
    is_accessory,
    is_accessory_for_category,
    should_cache_price,
)
from scripts import build_source_registry_data as build


# ---------------------------------------------------------------------------
# shared fixtures / helpers
# ---------------------------------------------------------------------------

def _pdp_price(title, brand=None, **over):
    base = {
        "amount": 20.0, "currency": "BHD", "retailer": "store-example-bh.com",
        "url": "https://store-example-bh.com/product/item-slug/",
        "in_stock": True, "estimated": False, "source_method": "local_bhd",
        "confidence": 0.9, "title": title,
    }
    if brand is not None:
        base["brand"] = brand
    base.update(over)
    return base


def _polo_hit(name, style="L1212"):
    """6thstreet-shaped algolia hit (the _match_algolia_hit path CV1 rode)."""
    return {
        "objectID": "901224",
        "name": name,
        "brand_name": "Lacoste",
        "main_brand": "Lacoste",
        "sku": f"{style}_White",
        "style_code": style,
        "url": "https://en-bh.6thstreet.com/x-l1212-white.html",
        "in_stock": 1,
        "price": [{"BHD": {"default": 40, "default_formated": "BHD 40.000"}}],
    }


_SDG_STORE = ALGOLIA_EXPLICIT_STORES["bahrain.sharafdg.com"]


def _sdg_hit(title, price, in_stock=1):
    return {"post_title": title, "price": price, "in_stock": in_stock,
            "permalink": "https://bahrain.sharafdg.com/product/x/"}


# The RAW live sharafdg MacBook title (VERBATIM bytes incl. the U+2011 in
# "8‑core"; entity-decoded as _catalog_hit_fields ingests it) — the sanctioned
# C2 unlock every CV2 bound must keep passing.
T_SDG_MBA_INGESTED = ("Apple MacBook Air M5 13-inch (2026) - 10-core CPU / "
                      "16GB RAM / 512GB SSD / 8‑core GPU / macOS Tahoe / "
                      "English & Arabic Keyboard / Sky Blue / "
                      "Middle East Version")

Q_MBA = "MacBook Air 13 M5 512GB"


def _real_rows():
    return json.loads(sr._CATALOG_DATA_PATH.read_text(encoding="utf-8"))


# ===========================================================================
# CV1 — baby/infant + multipack wordings block the structured-code override
# ===========================================================================

class TestCV1StructuredOverrideInfantMultipack:
    @pytest.mark.parametrize("marker", [
        "Baby", "Infant",
        # spaced multipack forms (normalize_words splits -> the bare tokens)
        "Twin Pack", "2 Pack", "Multi Pack",
        # hyphen/glued forms (normalize_words folds -> the glued tokens)
        "Twin-Pack", "Twinpack", "2-Pack", "Two-Pack", "3-Pack", "6-Pack",
        "Multipack", "Multi-Pack",
    ])
    def test_marker_add_blocks_override(self, marker):
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            f"Logo Detail Polo Shirt {marker} - White L1212") is True

    @pytest.mark.parametrize("title", [
        "Logo Detail Polo Shirt Baby - White",
        "Logo Detail Polo Bodysuit Infant - White",
        "L1212 Polo Shirt Twin Pack - White",
        "L1212 Polo Shirt Multipack - White",
    ])
    def test_cache_override_end_refuses(self, title):
        # the exact CV1 repro: query-confirmed code + sibling/multipack title.
        # NOTE the DIGIT-count form ("2-Pack") is a DIFFERENT, pre-existing
        # class: "2pack" is measure-shaped, so _identity_tokens_ps strips it
        # onto the COUNT axis and the ONE-SIDED count tolerance accepts at the
        # MAIN _selection_match path — the override (this fix's bound) is
        # never consulted. That documented one-sided-count trade is out of
        # CV1's scope; the block tokens still cover the digit forms wherever
        # the override IS the deciding gate.
        p = _pdp_price(title, brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is False

    @pytest.mark.parametrize("name", [
        "Logo Detail Polo Shirt Infant - White",
        "Logo Detail Polo Shirt Twin Pack - White",
    ])
    def test_algolia_adapter_override_end_refuses(self, name):
        # the OTHER override end (Wave A3): the adapter matcher must refuse too
        assert alg._match_algolia_hit(
            [_polo_hit(name)], "Lacoste L1212 Polo",
            resolved_category="fashion") is None

    def test_l1212_base_unlock_still_passes_both_ends(self):
        # both-direction bound: the sanctioned descriptive-title unlock stays
        base = "Logo Detail Short Sleeves Polo T-Shirt"
        assert alg._match_algolia_hit(
            [_polo_hit(base)], "Lacoste L1212 Polo",
            resolved_category="fashion") is not None
        p = _pdp_price(base, brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is True

    def test_query_stating_the_marker_is_unaffected(self):
        # asymmetry pin: the suppression fires only on tokens the title ADDS
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo Baby",
            "Logo Detail Polo Shirt Baby L1212") is False
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo Twin Pack",
            "L1212 Polo Shirt Twin Pack - White") is False


# ===========================================================================
# W2 (Wave D polish) — block-token collisions: bare 'twin' dropped, 'baby'
# bounded to the sibling-segment sense (the colorway bigram never blocks)
# ===========================================================================

class TestW2BlockTokenCollisions:
    def test_twin_tipped_mainline_not_blocked_helper(self):
        # bare 'twin' dropped: 'Twin Tipped' is Fred Perry's flagship LINE
        # name, not a sellable-unit add (both real title shapes)
        assert _structured_override_variant_blocked(
            "Fred Perry M3600 Polo",
            "Fred Perry Twin Tipped Polo M3600") is False
        assert _structured_override_variant_blocked(
            "Fred Perry M3600 Polo",
            "Fred Perry Twin Tipped Fred Perry Shirt - Black M3600") is False

    def test_twin_tipped_polo_caches_with_confirmed_code(self):
        # the W2 repro, e2e through the cache gate: the exact correct SKU's
        # descriptive title rides the query-confirmed style code again
        p = _pdp_price("Fred Perry Twin Tipped Polo M3600",
                       brand="Fred Perry", structured_code="M3600")
        assert should_cache_price("Fred Perry M3600 Polo", p, "fashion") is True

    @pytest.mark.parametrize("marker", ["Twin Pack", "Twin-Pack", "Twinpack"])
    def test_twin_pack_forms_still_block(self, marker):
        # zero leak cost: bare 'pack' covers the spaced form, the enumerated
        # glued tokens cover the hyphen/glued forms — dropping 'twin' loses
        # no multipack coverage
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            f"L1212 Polo Shirt {marker} - White") is True

    @pytest.mark.parametrize("shade", ["Baby Blue", "Baby Pink"])
    def test_baby_colorway_not_blocked_helper(self, shade):
        # 'Baby Blue'/'Baby Pink' is a SHADE name on an adult mainline SKU —
        # the colorway bigram consumes 'baby'
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            f"Lacoste Logo Detail Polo Shirt {shade} - White L1212") is False

    def test_baby_colorway_caches_with_confirmed_code(self):
        p = _pdp_price("Logo Detail Polo Shirt Baby Blue - White",
                       brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is True

    def test_baby_segment_still_blocks(self):
        # the sibling-SEGMENT sense (infant garment) keeps the fence up
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            "Lacoste L1212 Polo Baby - 6-12 months") is True
        p = _pdp_price("L1212 Polo Baby - 6-12 months",
                       brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is False

    def test_both_baby_senses_stay_blocked(self):
        # fail-closed: a surface carrying the colorway AND a bare segment
        # 'baby' still blocks (only when EVERY occurrence is colorway-bound
        # does the token drop)
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            "L1212 Polo Baby Blue - Baby 6-12 months") is True

    def test_query_stated_baby_asymmetry_unchanged(self):
        # a query that itself states the segment marker is unaffected
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo Baby",
            "L1212 Polo Shirt Baby - 6-12 months") is False


# ===========================================================================
# CV2 — the laptop keyboard exemption is bounded to layout-attribute phrasing
# ===========================================================================

class TestCV2KeyboardPartBound:
    LEAK = "Arabic Keyboard for Apple MacBook Air 13 M5 512GB"

    def test_full_spec_part_listing_is_accessory_again(self):
        # the CV2 repro: laptop noun on the surface no longer exempts a title
        # that HEADS with the keyboard noun ("keyboard ... for ... macbook")
        assert is_accessory_for_category(self.LEAK, "electronics") is True

    def test_part_listing_rejects_above_the_flagship_floor_e2e(self):
        # the leak fired at 59.9 BHD precisely because the floor (<50) could
        # not catch it — the accessory gate must, at the adapter ingress
        hit = _sdg_hit(self.LEAK, 59.9)
        assert alg._catalog_match_hit(
            [hit], Q_MBA, _SDG_STORE, resolved_category="electronics") is None

    def test_keyboard_for_phrase_flags_even_after_the_device_noun(self):
        # ordering alone is bypassable by "MacBook ... Keyboard for ..." —
        # part/compat phrasing keeps the flag regardless of position
        assert is_accessory_for_category(
            "Apple MacBook Air Keyboard for M5 13-inch Models",
            "electronics") is True
        assert is_accessory_for_category(
            "Arabic Keyboard compatible with MacBook Air 13",
            "electronics") is True

    def test_raw_live_sharafdg_title_keeps_the_exemption(self):
        # the sanctioned C2 unlock (device noun heads, layout segment mid-
        # title) must keep passing on the RAW live bytes
        assert is_accessory_for_category(
            T_SDG_MBA_INGESTED, "electronics") is False

    @pytest.mark.parametrize("title", [
        "Apple MacBook Pro M4 16GB 512GB Arabic Keyboard",
        "Lenovo IdeaPad 5 Laptop English-Arabic Keyboard 512GB",
    ])
    def test_layout_tail_laptop_titles_keep_the_exemption(self, title):
        assert is_accessory_for_category(title, "electronics") is False

    def test_real_keyboard_and_keyboard_accessory_still_reject(self):
        # unchanged bounds: head-noun keyboard product (no device context) and
        # any OTHER accessory keyword still flag
        assert is_accessory_for_category("Logitech MX Keys Keyboard",
                                         "electronics") is True
        assert is_accessory_for_category("Keyboard Case for MacBook Air 13",
                                         "electronics") is True

    def test_broad_is_accessory_unchanged(self):
        # the noisy Serper-shopping/zyte/rating nets keep the unscoped hit
        assert is_accessory(T_SDG_MBA_INGESTED) is True


# ===========================================================================
# CV3 — non-retail catalog rows (classifieds/aggregators) demoted + tripwire
# ===========================================================================

# The non-retail class (suffix-matched): user classifieds (used-goods/private
# listings with self-asserted JSON-LD) + price-comparison aggregators (a
# cross-store min, never a retailer shelf price). Catalog grep 2026-07-02
# found the four demoted rows; pricena/kanbkam were already generator-skipped
# (F6); ibsouq.com / souqscent.com / eideal.com are REAL retailers (souq is
# Arabic for market — not the classifieds class) and stay.
_NON_RETAIL_BLOCKLIST = (
    "opensooq.com", "labeb.com", "dubizzle.com.bh", "dubizzle.com",
    "olx.com", "comparebh.com", "pricena.com", "kanbkam.com",
)


def _blocklisted(domain: str) -> bool:
    return any(domain == b or domain.endswith("." + b)
               for b in _NON_RETAIL_BLOCKLIST)


class TestCV3NonRetailCatalogRows:
    def test_tripwire_no_live_non_retail_row(self):
        # THE TRIPWIRE: if this fires after a liveness-gate re-run, a
        # classifieds/aggregator row was re-promoted — re-check the class
        # before accepting the promotion (they are non-retail by NATURE, not
        # by probe failure: a 200-OK JSON-LD probe proves nothing here).
        bad = [r["domain"] for r in _real_rows()
               if _blocklisted(str(r.get("domain") or ""))
               and r.get("status") == "live"]
        assert bad == []

    def test_demoted_rows_are_dead_with_a_note(self):
        rows = {r["domain"]: r for r in _real_rows()}
        for d in ("bh.opensooq.com", "bh.labeb.com", "dubizzle.com.bh",
                  "comparebh.com"):
            row = rows.get(d)
            if row is None:
                # a future re-consolidation drops the class entirely — fine
                continue
            assert row["status"] == "dead", d
            assert "non-retail" in str(row.get("note") or ""), d

    def test_loader_never_admits_non_retail(self, monkeypatch):
        # real data file + flag ON — the exact admission path prod uses
        monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
        admitted = {s.domain for s in sr._load_catalog_rows()}
        assert not {d for d in admitted if _blocklisted(d)}

    def test_curl_selector_never_returns_non_retail(self, monkeypatch):
        # the CV3 repro surface: get_curl_pagescrape_sources_for_category
        # included bh.opensooq.com + bh.labeb.com (+ dubizzle/comparebh)
        monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
        registry = sr._LITERAL_ROWS + sr._load_catalog_rows()
        monkeypatch.setattr(sr, "SOURCE_REGISTRY", registry)
        for cat in ("electronics", "fashion", "other"):
            curl = {s.domain
                    for s in sr.get_curl_pagescrape_sources_for_category(cat)}
            assert not {d for d in curl if _blocklisted(d)}, cat

    def test_scs_harvest_blocklist_parity_with_generator(self):
        # W1 — the scs organic-harvest blocklist MIRRORS the generator's
        # skip set. Duplicated (not imported: the deployed service must not
        # depend on scripts/) — this pin is what keeps the two from drifting.
        from app.services.structured_comparison_service import (
            _ORGANIC_NON_RETAIL_DOMAINS,
        )
        assert _ORGANIC_NON_RETAIL_DOMAINS == frozenset(
            build._NON_RETAIL_DOMAINS)

    def test_generator_skip_set_covers_the_class(self):
        # a re-consolidation must never re-emit the class (the F6 skip,
        # extended): every blocklist apex is covered suffix-aware
        for apex in _NON_RETAIL_BLOCKLIST:
            assert any(apex == d or apex.endswith("." + d)
                       for d in build._NON_RETAIL_DOMAINS), apex

    def test_consolidation_never_reemits_non_retail(self):
        # run the REAL consolidation over the immutable discovery catalogs —
        # no non-retail domain may come back in any status
        out = {r["domain"] for r in build.consolidate()}
        assert not {d for d in out if _blocklisted(d)}

    def test_merge_preserves_the_demotion_note(self, tmp_path, monkeypatch):
        # the idempotent merge must carry status AND note forward, so a
        # regeneration can never silently strip the demotion rationale
        out = tmp_path / "bh_gcc_sources.json"
        out.write_text(json.dumps([{
            "domain": "example-bh.com", "status": "dead",
            "note": "non-retail: test",
        }]), encoding="utf-8")
        monkeypatch.setattr(build, "_ROOT", tmp_path)
        monkeypatch.setattr(build, "_OUT", out)
        monkeypatch.setattr(build, "consolidate", lambda: [{
            "domain": "example-bh.com", "status": "provider-test-candidate",
        }])
        build.main([])
        merged = json.loads(out.read_text(encoding="utf-8"))
        assert merged[0]["status"] == "dead"
        assert merged[0]["note"] == "non-retail: test"


# ===========================================================================
# CV4 — label-BEFORE core-count phrasing parses; same bin no longer rejects
# ===========================================================================

class TestCV4LabelBeforeCoreCounts:
    def test_label_before_same_bin_accepts(self):
        # the CV4 repro: the EXACT 10c/8g bin, label-before vs label-after
        assert _core_count_mismatch(
            "MacBook Air M4 10-core CPU 8-core GPU",
            "Apple MacBook Air M4 CPU 10-core GPU 8-core 512GB") is False

    def test_label_before_both_sides_same_bin_accepts(self):
        assert _core_count_mismatch(
            "MacBook Air M4 CPU 10-core GPU 8-core",
            "Apple MacBook Air M4 CPU 10-core GPU 8-core 512GB") is False

    def test_label_before_query_accepts_the_exact_sku_end_to_end(self):
        # the over-rejection the CV4 mislabel caused, through the FULL
        # selection gate (identity + every axis)
        assert _selection_match(
            "MacBook Air M4 CPU 10-core GPU 8-core 512GB",
            "Apple MacBook Air M4 10-core CPU / 8-core GPU / 512GB SSD",
            "electronics", candidate_brand="Apple") is True

    def test_label_before_swapped_bins_still_reject(self):
        # both-direction bound: a DIFFERENT cpu bin keeps rejecting
        assert _core_count_mismatch(
            "MacBook Air M4 CPU 8-core GPU 10-core",
            "Apple MacBook Air M4 10-core CPU 16-core GPU") is True

    def test_label_after_gpu_bin_still_discriminates(self):
        # the pinned RS4 semantics are untouched (10c/10g vs 10c/8g rejects)
        assert _core_count_mismatch(
            "MacBook Air M5 13 10-core CPU 10-core GPU 512GB",
            "Apple MacBook Air M5 13-inch 10‑core CPU / "
            "8‑core GPU / 512GB SSD") is True

    def test_parse_label_before(self):
        # the consumed trailing 'gpu' of "10-core GPU" cannot double-bind: the
        # PRECEDING 'cpu' wins for 10, and 8 stays unlabelled (set semantics)
        assert _labeled_core_counts("CPU 10-core GPU 8-core") == (
            {10}, set(), {8})

    def test_parse_label_after_unchanged(self):
        assert _labeled_core_counts("10-core CPU / 8-core GPU") == (
            {10}, {8}, set())

    def test_parse_shared_label_word_never_binds_twice(self):
        # "10-core CPU 10-core GPU": the 'CPU' consumed as count-1's trailing
        # label must not ALSO pre-bind count 2 (which keeps its own 'GPU')
        assert _labeled_core_counts("10-core CPU 10-core GPU") == (
            {10}, {10}, set())

    def test_parse_label_before_unicode_hyphen(self):
        assert _labeled_core_counts(
            "CPU 10‑core GPU 8‑core") == ({10}, set(), {8})

    def test_unlabelled_set_semantics_unchanged(self):
        assert _core_count_mismatch("12-core", "12-core") is False
        assert _core_count_mismatch("12-core", "10-core") is True
        assert _core_count_mismatch("MacBook Air M4", "10-core CPU") is False


# ===========================================================================
# CV5 — the neckline bigram accepts the unicode-hyphen family
# ===========================================================================

class TestCV5NecklineUnicodeHyphen:
    Q = "Nike Sportswear Club Sweatshirt"

    @pytest.mark.parametrize("hyphen", [
        pytest.param("‐", id="U+2010-hyphen"),
        pytest.param("‑", id="U+2011-nbhyphen"),
        pytest.param("–", id="U+2013-endash"),
        pytest.param("-", id="ascii"),
        pytest.param(" ", id="space"),
    ])
    def test_crew_neck_hyphen_family_tolerated(self, hyphen):
        # the CV5 repro (U+2011) + the whole C2 _UNICODE_HYPHENS canon
        title = f"Nike Sportswear Club Crew{hyphen}Neck Sweatshirt"
        assert _selection_match(self.Q, title, "fashion",
                                candidate_brand="Nike") is True

    def test_u2011_crew_neck_brandless_tolerated(self):
        # the exact CV5 repro shape (no candidate_brand threaded)
        assert _selection_match(
            self.Q, "Nike Sportswear Club Crew‑Neck Sweatshirt",
            "fashion") is True

    def test_u2011_mock_neck_stays_distinctive(self):
        # bound: only the crew/v/round garment bigrams are tolerated
        assert _selection_match(
            self.Q, "Nike Sportswear Club Mock‑Neck Sweatshirt",
            "fashion", candidate_brand="Nike") is False

    def test_both_stated_different_neckline_still_rejects(self):
        # the query-side token stays required through the unicode form
        assert _selection_match(
            "Tommy Hilfiger Essential V-Neck T-Shirt",
            "Essential Crew‑Neck T-Shirt",
            "fashion", candidate_brand="Tommy Hilfiger") is False

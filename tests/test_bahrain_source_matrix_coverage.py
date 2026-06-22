"""WS-F (G6) drift-guard + F8 parity: every CATEGORY_SPEC_SCHEMAS category must
map to >=1 registered genuine-BH-capable source (curl/JSON-LD, Shopify, or
Algolia, bahrain tier, live on the live 12s clock) OR be in KNOWN_SOURCE_GAPS
with a reason.

Render-only / requires_super rows are DEAD on live traffic today (T4: the live
12s clock starves the render tier; SCRAPEDO_SUPER is OFF by default and
fail-closed) — they do NOT count as genuine-capable here. A future edit that
strands a category (deletes its last curl/Shopify/Algolia bahrain row, or flips
it render-only) must record the gap WITH A REASON in KNOWN_SOURCE_GAPS, never
silently drop the category to converted_usd / estimated / None.

Two guards ship (DISPATCHER-GATE Q5):
  * LENIENT — gates merges. Counts lulu's empty-`categories` all-category row,
    so it proves "a genuine-BH path EXISTS" for every category. KNOWN_SOURCE_GAPS
    is EMPTY today (lulu covers everything). No false reds.
  * STRICT — documents thinness. EXCLUDES the empty-`categories` all-category
    rows (lulu) so it surfaces the lulu-only category (`other`) and the thin
    single-source categories as documented gaps via STRICT_KNOWN_SOURCE_GAPS
    reasons. Not a merge gate — a thinness ledger.

Contract doc: docs/contracts/bahrain-source-matrix.md (mirror these gaps).

No live-network calls here — pure registry-shape assertions ($0, free-unit tier).
WS-G liveness is a separate `scripts/verify_source_registry.py` manual step.
"""
from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
from app.services.price_service import PHARMACY_DOMAINS
from app.services.source_router import (
    SOURCE_REGISTRY,
    get_sources_for_category,
)

CANONICAL_CATEGORIES = frozenset(CATEGORY_SPEC_SCHEMAS.keys())

# --- LENIENT gap set (merge gate) ----------------------------------------
# A category with NO live-reachable genuine-BH source AT ALL (counting lulu's
# all-category curl row). EMPTY today: gcc.luluhypermarket.com (empty
# `categories` tuple, bahrain tier, curl/JSON-LD) is genuine-capable for EVERY
# category. Each future entry MUST carry a non-empty reason. This is the SAFETY
# NET: a strand must be recorded, never silently dropped.
KNOWN_SOURCE_GAPS: dict[str, str] = {}

# --- STRICT gap set (thinness ledger) ------------------------------------
# A category with NO category-SPECIFIC genuine-BH source — i.e. its only
# live-reachable genuine path is lulu's all-category row. Excluding lulu
# surfaces the structurally thin spots. `other` is lulu-only by design
# (mitigation is upstream category resolution, F1 — `other` is a fallback
# bucket, not a real shopping category). Each entry MUST carry a reason and
# MUST be a genuine strict-gap (test_strict_known_source_gaps_are_real_gaps).
STRICT_KNOWN_SOURCE_GAPS: dict[str, str] = {
    "other": (
        "lulu-only (all-category row) — `other` is the catch-all fallback "
        "bucket, not a real shopping category; mitigation is upstream category "
        "resolution (F1), not a category-specific BH source. No dedicated "
        "`other` retailer exists or is wanted."
    ),
}


def _genuine_bh_capable(category: str, *, strict: bool = False) -> bool:
    """True iff `category` has >=1 bahrain-tier source that is live-reachable
    for genuine BHD on today's traffic (curl/JSON-LD, Shopify, or Algolia) — NOT
    render-only and NOT requires_super (both dead on the live 12s clock /
    SCRAPEDO_SUPER OFF).

    strict=True additionally EXCLUDES empty-`categories` all-category rows (lulu)
    so the result reflects category-SPECIFIC genuine coverage.
    """
    for s in get_sources_for_category(category):
        if s.tier != "bahrain":
            continue
        if s.is_render_only or s.requires_super:
            continue  # dead on live traffic
        if strict and not s.categories:
            continue  # all-category row (lulu) — excluded from the strict count
        return True
    return False


# === LENIENT drift-guard (the merge gate) ================================

def test_every_category_has_a_genuine_bh_source_or_explicit_gap():
    uncovered = []
    for cat in sorted(CANONICAL_CATEGORIES):
        if _genuine_bh_capable(cat):
            continue
        if cat in KNOWN_SOURCE_GAPS:
            assert KNOWN_SOURCE_GAPS[cat], f"{cat} gap needs a non-empty reason"
            continue
        uncovered.append(cat)
    assert not uncovered, (
        "Categories with NO live-reachable genuine-BH source and NOT in "
        f"KNOWN_SOURCE_GAPS: {uncovered}. Either restore a curl/Shopify/Algolia "
        "bahrain source for the category, or record the gap WITH A REASON."
    )


def test_known_source_gaps_are_real_gaps():
    for cat in KNOWN_SOURCE_GAPS:
        assert cat in CANONICAL_CATEGORIES, f"unknown category in gaps: {cat}"
        assert not _genuine_bh_capable(cat), (
            f"{cat} is in KNOWN_SOURCE_GAPS but DOES have a live genuine-BH "
            "source now — remove the stale gap entry."
        )


# === STRICT drift-guard (the thinness ledger, DISPATCHER-GATE Q5) ========

def test_every_category_has_a_category_specific_bh_source_or_gap():
    """The lenient guard passes trivially on lulu's all-category reach (proves a
    path EXISTS, not that the path produces genuine BHD for the category). The
    strict guard excludes lulu so a lulu-only category surfaces as a documented
    thin spot via STRICT_KNOWN_SOURCE_GAPS — not a silent reliance on lulu's
    uneven JSON-LD coverage."""
    uncovered = []
    for cat in sorted(CANONICAL_CATEGORIES):
        if _genuine_bh_capable(cat, strict=True):
            continue
        if cat in STRICT_KNOWN_SOURCE_GAPS:
            assert STRICT_KNOWN_SOURCE_GAPS[cat], (
                f"{cat} strict gap needs a non-empty reason"
            )
            continue
        uncovered.append(cat)
    assert not uncovered, (
        "Categories with NO category-SPECIFIC genuine-BH source (lulu-only) and "
        f"NOT in STRICT_KNOWN_SOURCE_GAPS: {uncovered}. Add a category-specific "
        "BH source, or document the lulu-only reliance with a reason."
    )


def test_strict_known_source_gaps_are_real_gaps():
    for cat in STRICT_KNOWN_SOURCE_GAPS:
        assert cat in CANONICAL_CATEGORIES, (
            f"unknown category in strict gaps: {cat}"
        )
        # A strict gap means: NO category-specific source (lenient may still be
        # True via lulu). If a category-specific source now exists, drop the gap.
        assert not _genuine_bh_capable(cat, strict=True), (
            f"{cat} is in STRICT_KNOWN_SOURCE_GAPS but now HAS a "
            "category-specific genuine-BH source — remove the stale entry."
        )


def test_lenient_gaps_are_subset_of_strict_gaps():
    """Invariant: a category with no source AT ALL (lenient gap) is necessarily
    also a category with no category-specific source (strict gap). Catches a
    KNOWN_SOURCE_GAPS edit that forgets to mirror into STRICT_KNOWN_SOURCE_GAPS."""
    missing = set(KNOWN_SOURCE_GAPS) - set(STRICT_KNOWN_SOURCE_GAPS)
    assert not missing, (
        f"Lenient gaps not mirrored in strict gaps: {sorted(missing)} — a "
        "category with no source at all is also a strict gap."
    )


# === Canonical-9-keys pin ================================================

def test_canonical_set_is_the_nine_schema_keys():
    assert CANONICAL_CATEGORIES == frozenset(CATEGORY_SPEC_SCHEMAS.keys())
    assert len(CANONICAL_CATEGORIES) == 9
    # The exact set — a drift here means a new category needs matrix coverage.
    assert CANONICAL_CATEGORIES == frozenset(
        {
            "electronics", "grocery", "supplements", "other", "makeup",
            "skincare", "haircare", "fragrances", "fashion",
        }
    )


# === F8 — aldeerah / PHARMACY_DOMAINS parity =============================

def _registry_domains() -> set[str]:
    return {s.domain.lower() for s in SOURCE_REGISTRY}


def test_f8_aldeerah_in_registry_iff_verified():
    """F8 verify-or-omit (G7): aldeerahpharmacy.com ships a SOURCE_REGISTRY row
    ONLY after a passing liveness probe (HEAD-200 + a curl PDP yielding a static
    BHD JSON-LD/OG price, OR an is_render_only determination). As of this bundle
    the curl-PDP step is UNVERIFIED (the catalogsearch path 502'd, the homepage
    carried no static JSON-LD/OG price) → the row is OMITTED and recorded in
    STRICT_KNOWN_SOURCE_GAPS-adjacent pipeline notes (the contract doc's WS-G
    table) as PENDING-LIVENESS. This test pins the verify-or-omit invariant:
    aldeerah must be ABSENT from the registry until the curl-PDP evidence lands.
    If a future session ADDS the row, it MUST also flip this assertion (and
    record the verification evidence in the commit + contract doc)."""
    assert "aldeerahpharmacy.com" not in _registry_domains(), (
        "aldeerahpharmacy.com was added to SOURCE_REGISTRY — verify-or-omit (G7) "
        "requires a passing curl-PDP static-price (or is_render_only) "
        "determination first; if you verified it, update this test + the WS-G "
        "pipeline table in docs/contracts/bahrain-source-matrix.md with the "
        "evidence (don't just delete the assertion)."
    )
    # It IS already a pharmacy-search domain (price_service.PHARMACY_DOMAINS) —
    # the search template exists; only the curl-scrapeability is unproven.
    assert "aldeerahpharmacy.com" in PHARMACY_DOMAINS


def test_f8_registry_pharmacy_domain_parity():
    """Every PHARMACY_DOMAINS storefront should be EITHER a SOURCE_REGISTRY row
    OR a documented gap (verify-or-omit pending). PHARMACY_DOMAINS is the
    pharmacy-search-fallback set in price_service; SOURCE_REGISTRY is the routed
    discovery set. A pharmacy storefront that is search-fallback-only (not a
    registry row) is fine, but it must be a KNOWN, recorded state — not an
    accident. bn.boots.com + bolo.bh ARE registry rows (render-only);
    aldeerahpharmacy.com is the recorded PENDING-LIVENESS gap."""
    registry = _registry_domains()
    # Domains that are intentionally pharmacy-search-only and NOT yet a routed
    # registry row, each with the reason mirrored in the contract doc's WS-G
    # pipeline table.
    pharmacy_search_only: dict[str, str] = {
        "aldeerahpharmacy.com": (
            "PENDING-LIVENESS (F8/WS-G): HEAD-200 but the catalogsearch PDP path "
            "502'd and the homepage carried no static JSON-LD/OG price → "
            "curl-scrapeability + is_render_only undetermined; verify-or-omit "
            "(G7) → no registry row this bundle."
        ),
    }
    for domain in PHARMACY_DOMAINS:
        d = domain.lower()
        in_registry = d in registry or any(
            r == d or r.endswith("." + d) or d.endswith("." + r)
            for r in registry
        )
        if in_registry:
            continue
        assert d in pharmacy_search_only, (
            f"PHARMACY_DOMAINS entry {d!r} is neither a SOURCE_REGISTRY row nor "
            "a recorded pharmacy-search-only gap — record it (with a reason) in "
            "this test + the contract doc's WS-G pipeline table, or add a "
            "verified registry row."
        )
        assert pharmacy_search_only[d], f"{d} gap needs a non-empty reason"

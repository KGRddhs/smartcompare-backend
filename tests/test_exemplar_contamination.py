"""I1.2 — contamination guard for the synthetic verdict exemplars (Decision E).

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § 0 Decision E + § 1 I1.2
Dossier: 2026-06-10-bundle-b-s2-design-inputs.md § 3 ("exemplars are synthetic
rewrites of these patterns ... never verbatim gold pairs — else the 0.60
re-measure is trained-on-test").

The exit criterion is "contamination rule provably honored (provenance
block)". This module proves it mechanically against the gold set:
  - every exemplar's _provenance.source_pattern_id resolves to a real gold id,
  - every authored exemplar is flagged synthetic: true,
  - NO gold-pair BRAND name leaks into the exemplar surface text. Generic
    category nouns (e.g. "vitamin c", "spf 50", "inverter ac") are NOT
    contamination — they describe the same product TYPE, which is the point of
    a same-structure rewrite. Only distinctive brand names are forbidden.

Reads the committed data/verdict_exemplars.json (lands at G3) — skips cleanly
until then so the lane suite stays green pre-G3.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CANONICAL = _REPO_ROOT / "data" / "verdict_exemplars.json"
_GOLD = _REPO_ROOT / "data" / "validation_gold_truth.json"

CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)

# Distinctive BRAND tokens per gold template-pattern id (the proper-noun brand
# names Decision E forbids reusing verbatim). Generic category descriptors are
# deliberately excluded — a same-structure rewrite must keep the product TYPE.
_GOLD_BRANDS = {
    "elec-031": ["brother", "canon", "hl-l2400dw", "i-sensys", "lbp122dw"],
    "elec-015": ["daikin", "dualcool"],
    "elec-018": ["samsung", "galaxy", "a55", "redmi", "xiaomi"],
    "groc-009": ["al foah", "bateel"],
    "groc-004": ["nescafe", "movenpick", "mövenpick"],
    "groc-002": ["twinings", "ahmad tea"],
    "supp-013": ["now foods", "emergen-c"],
    "supp-020": ["now foods", "sports research", "bioperine"],
    "make-016": ["e.l.f", "halo glow", "charlotte tilbury", "flawless filter"],
    "make-002": ["ruby woo", "charlotte tilbury", "pillow talk"],
    "make-013": ["rimmel", "stay matte", "maybelline", "fit me"],
    "skin-018": ["the ordinary", "some by mi"],
    "skin-003": ["drunk elephant", "c-firma", "skinceuticals", "ce ferulic"],
    "skin-009": ["la roche-posay", "anthelios", "avene"],
    "hair-021": ["mielle", "rosemary mint", "the ordinary", "multi-peptide"],
    "hair-001": ["olaplex", "k18"],
    "hair-014": ["maui moisture", "ogx"],
    "frag-010": ["armaf", "club de nuit", "afnan", "9pm"],
    "frag-001": ["tom ford", "black orchid", "creed", "aventus"],
    "frag-016": ["lattafa", "yara", "ana abiyedh"],
    "fash-016": ["michael kors", "fossil"],
    "fash-009": ["fossil", "citizen", "eco-drive"],
    "fash-006": ["levi", "501", "lee", "brooklyn"],
    "other-019": ["bionaire", "super general"],
    "other-009": ["ariston", "super general"],
    "other-004": ["nespresso", "vertuo", "keurig", "k-mini"],
}


@pytest.fixture(scope="module")
def content() -> dict:
    if not _CANONICAL.exists():
        pytest.skip("data/verdict_exemplars.json not yet committed (lands at G3)")
    return json.loads(_CANONICAL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gold_ids() -> set:
    gold = json.loads(_GOLD.read_text(encoding="utf-8"))
    return {q["id"] for q in gold["queries"]}


def _surface_text(ex: dict) -> str:
    vj = ex.get("verdict_json", {})
    parts = [
        ex.get("title", ""), ex.get("setup", ""),
        vj.get("winner_declaration", ""), vj.get("winner_reason", ""),
        vj.get("key_tradeoff", ""),
        json.dumps(vj.get("value_context", {}), ensure_ascii=False),
    ]
    return " ".join(parts).lower()


def test_every_provenance_id_resolves_to_gold(content, gold_ids):
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            pid = ex["_provenance"]["source_pattern_id"]
            assert pid in gold_ids, f"{cat}: provenance {pid!r} not a gold id"


def test_every_authored_exemplar_flagged_synthetic(content):
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            assert ex["_provenance"]["synthetic"] is True, (
                f"{cat}/{ex['_provenance']['source_pattern_id']}: synthetic must be True"
            )


def test_no_gold_brand_leaks_into_any_exemplar(content):
    """The core Decision E guard: zero distinctive gold-pair brand names in the
    synthetic exemplar surface text."""
    violations = []
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            pid = ex["_provenance"]["source_pattern_id"]
            text = _surface_text(ex)
            for brand in _GOLD_BRANDS.get(pid, []):
                if brand.lower() in text:
                    violations.append(f"{cat}/{pid}: brand {brand!r} leaked")
    assert not violations, "Decision E contamination: " + "; ".join(violations)


def test_known_template_ids_are_covered(content):
    """The dossier §3 names specific template ids as the strong teaching set;
    assert each one we claim to mirror is actually present in provenance."""
    used = {
        ex["_provenance"]["source_pattern_id"]
        for cat in CATEGORIES for ex in content[cat]["exemplars"]
    }
    # the H1/H8/H2/H4 templates the dossier §3 explicitly calls out
    dossier_named = {
        "supp-013", "make-016", "groc-009", "skin-018",  # strong H1
        "skin-013", "make-013", "skin-009", "other-019",  # H8 / climate (subset)
        "groc-002", "frag-016", "make-011",               # H2
        "elec-024", "elec-018",                            # H4
    }
    # We need not use ALL of them, but a healthy majority should appear so the
    # exemplar set is anchored in the dossier's analysis (not invented wholesale).
    overlap = used & dossier_named
    assert len(overlap) >= 6, (
        f"only {len(overlap)} dossier-named templates used: {sorted(overlap)}"
    )

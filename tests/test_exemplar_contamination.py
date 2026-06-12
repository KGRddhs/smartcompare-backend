"""I1.2 — contamination guard for the synthetic verdict exemplars (Decision E).

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § 0 Decision E + § 1 I1.2
Dossier: 2026-06-10-bundle-b-s2-design-inputs.md § 3 ("exemplars are synthetic
rewrites of these patterns ... never verbatim gold pairs — else the 0.60
re-measure is trained-on-test").

The exit criterion is "contamination rule provably honored (provenance
block)". This module proves it mechanically against the gold set, scoping
every gold-specific guard to GOLD-SOURCED exemplars (the I1.2 synthetic seed):
  - every GOLD-SOURCED exemplar's _provenance.source_pattern_id resolves to a
    real gold id (feedback-sourced rows anchor to a comparison_id UUID, exempt),
  - every GOLD-SOURCED exemplar is flagged synthetic:true (feedback-sourced rows
    are synthetic:false — truthful — and exempt),
  - NO gold-pair BRAND name leaks into the exemplar surface text. Generic
    category nouns (e.g. "vitamin c", "spf 50", "inverter ac") are NOT
    contamination — they describe the same product TYPE, which is the point of
    a same-structure rewrite. Only distinctive brand names are forbidden.
The rotation cron (cron_few_shot_rotation) writes synthetic:false feedback rows;
both suites assert ONE coherent synthetic-vs-source contract.

POST-MEASUREMENT STATE (dispatcher ruling 2026-06-12): the canonical
data/verdict_exemplars.json now ships with exemplars[] EMPTY (a T=0 attribution
A/B found the worked exemplars add +0 over I2's anti_patterns). The 26 synthetic
exemplars are parked verbatim in data/verdict_exemplars.s3_parked.json for an S3
restore. The contamination guard's whole job — proving zero gold-pair brand
leakage — therefore now runs against the PARKED file (the content S3 restores),
plus a guard that the canonical exemplars[] are empty. The _GOLD_BRANDS map and
all leak logic are unchanged. Skips cleanly if either file is absent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
# The canonical file now holds empty exemplars[]; the 26 synthetic exemplars are
# parked for an S3 restore. The per-exemplar contamination guards read the
# PARKED file (the content that would re-enter the prompt), and a separate guard
# asserts the canonical exemplars[] are empty.
_CANONICAL = _REPO_ROOT / "data" / "verdict_exemplars.json"
_PARKED = _REPO_ROOT / "data" / "verdict_exemplars.s3_parked.json"
_GOLD = _REPO_ROOT / "data" / "validation_gold_truth.json"

CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)

# Distinctive BRAND tokens per gold template-pattern id (the proper-noun brand
# names Decision E forbids reusing verbatim). Generic category descriptors are
# deliberately excluded — a same-structure rewrite must keep the product TYPE.
_GOLD_BRANDS = {
    # in-set 45 ids my exemplars are anchored to (B4 re-anchored elec-031→033,
    # skin-003→005, frag-001→007, other-004→010; B5 added make-011).
    "elec-033": ["logitech", "c920", "anker", "powerconf", "c200"],
    "elec-015": ["daikin", "dualcool", "lg"],          # out-of-set, flagged (B4)
    "elec-018": ["samsung", "galaxy", "a55", "redmi", "xiaomi"],
    "groc-009": ["al foah", "bateel"],
    "groc-004": ["nescafe", "movenpick", "mövenpick"],
    "groc-002": ["twinings", "ahmad tea"],
    "supp-013": ["now foods", "emergen-c"],
    "supp-020": ["now foods", "sports research", "bioperine"],
    "make-016": ["e.l.f", "halo glow", "charlotte tilbury", "flawless filter"],
    "make-002": ["mac", "ruby woo", "charlotte tilbury", "pillow talk"],  # out-of-set, flagged (B4)
    "make-011": ["huda beauty", "easy bake", "laura mercier", "translucent"],
    "skin-018": ["the ordinary", "some by mi"],
    "skin-005": ["bioderma", "sensibio", "garnier", "micellar"],
    "skin-009": ["la roche-posay", "anthelios", "avene"],
    "hair-021": ["mielle", "rosemary mint", "the ordinary", "multi-peptide"],
    "hair-001": ["olaplex", "k18"],
    "hair-014": ["maui moisture", "ogx"],
    "frag-010": ["armaf", "club de nuit", "afnan", "9pm"],
    "frag-007": ["lattafa", "asad", "rasasi", "hawas"],
    "frag-016": ["lattafa", "yara", "ana abiyedh"],
    "fash-016": ["michael kors", "fossil"],
    "fash-009": ["fossil", "citizen", "eco-drive"],
    "fash-006": ["levi", "501", "lee", "brooklyn"],
    "other-019": ["bionaire", "super general"],
    "other-009": ["ariston", "super general"],
    "other-010": ["dyson", "xiaomi", "mi vacuum"],
}


@pytest.fixture(scope="module")
def content() -> dict:
    """The exemplar content under contamination test — the PARKED 26-exemplar
    set (canonical exemplars[] are empty post-measurement; the parked set is
    what an S3 restore re-injects, so it is what must stay contamination-clean)."""
    if not _PARKED.exists():
        pytest.skip("data/verdict_exemplars.s3_parked.json not present")
    return json.loads(_PARKED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def canonical_content() -> dict:
    if not _CANONICAL.exists():
        pytest.skip("data/verdict_exemplars.json not present (e.g. mid-rebase)")
    return json.loads(_CANONICAL.read_text(encoding="utf-8"))


def test_canonical_exemplars_are_empty(canonical_content):
    """Post-measurement: the live canonical file carries no exemplars (the
    worked-example layer was redundant over the anti_patterns at T=0). The
    synthetic content is preserved in the parked file, asserted clean below."""
    for cat in CATEGORIES:
        exs = canonical_content[cat].get("exemplars")
        assert exs == [], f"{cat}: canonical exemplars[] must be empty (got {len(exs or [])})"


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


def test_abridged_marker_present(content):
    """Every exemplar carries the dispatcher-mandated abridged marker so a
    JSON-mode output contract never pattern-matches a partial object."""
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            assert "EXAMPLE — abridged, do not copy structure or content" in ex["setup"], (
                f"{cat}: missing abridged marker"
            )


def test_every_provenance_id_resolves_to_gold(content, gold_ids):
    """Gold-sourced (synthetic) exemplars must anchor to a real gold id.
    Feedback-sourced (rotation) exemplars are exempt — their source_pattern_id
    is the feedback comparison_id (a UUID), not a gold id. Scoping matches the
    rotation cron contract (B3/MEDIUM: the first committed rotation output would
    otherwise red this on a mined row)."""
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            prov = ex["_provenance"]
            if prov.get("source") == "comparison_feedback":
                continue
            pid = prov["source_pattern_id"]
            assert pid in gold_ids, f"{cat}: provenance {pid!r} not a gold id"


def test_gold_sourced_exemplars_flagged_synthetic(content):
    """B3: the all-synthetic guard is scoped to GOLD-SOURCED rows. A
    gold-pattern exemplar (the I1.2 seed) MUST be synthetic:true (a rewrite,
    never a verbatim gold pair). A feedback-sourced exemplar (rotation) is
    synthetic:false and truthfully so — it is exempt from this guard. This
    matches the rotation cron's contract (test_cron_few_shot_rotation), so both
    suites assert ONE coherent synthetic-vs-source rule."""
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            prov = ex["_provenance"]
            if prov.get("source") == "comparison_feedback":
                assert prov["synthetic"] is False, (
                    f"{cat}: feedback-sourced exemplar must be synthetic:false"
                )
            else:
                assert prov["synthetic"] is True, (
                    f"{cat}/{prov['source_pattern_id']}: gold-sourced exemplar must be synthetic:true"
                )


def test_no_gold_brand_leaks_into_any_exemplar(content):
    """The core Decision E guard: zero distinctive gold-pair brand names in the
    synthetic exemplar surface text. Every gold-sourced (synthetic) exemplar
    MUST have a _GOLD_BRANDS entry so coverage can't silently lapse when a
    provenance id changes (B4 re-anchor lesson)."""
    violations = []
    missing_brand_map = []
    for cat in CATEGORIES:
        for ex in content[cat]["exemplars"]:
            prov = ex["_provenance"]
            if prov.get("source") == "comparison_feedback":
                continue  # mined rows are real, not gold-pattern rewrites
            pid = prov["source_pattern_id"]
            if pid not in _GOLD_BRANDS:
                missing_brand_map.append(f"{cat}/{pid}")
                continue
            text = _surface_text(ex)
            for brand in _GOLD_BRANDS[pid]:
                if brand.lower() in text:
                    violations.append(f"{cat}/{pid}: brand {brand!r} leaked")
    assert not missing_brand_map, (
        "gold-sourced ids missing a _GOLD_BRANDS entry (coverage gap): "
        + ", ".join(missing_brand_map)
    )
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

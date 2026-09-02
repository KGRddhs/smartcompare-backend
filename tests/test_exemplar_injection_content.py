"""I1.3 — injection CONTENT tests for the few-shot verdict layer.

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § I1.3
Contract: I1.1 (schema) + I2.1 (verdict_exemplar_loader.build_exemplar_block,
extraction_service.build_verdict_prompt injection).

POST-MEASUREMENT STATE (dispatcher ruling 2026-06-12):
  The canonical `data/verdict_exemplars.json` now ships with `exemplars[]`
  EMPTY in every category — a T=0 attribution A/B on FRESH inputs found the
  worked exemplars add +0 over I2's anti_patterns (byte-identical 9/24
  structural, 28/45 overall). I2's per-category `anti_patterns[]` carry the
  structural signal and stay LIVE; the injection mechanism + rotation cron are
  unchanged. The 26 synthetic exemplars are PARKED verbatim in
  `data/verdict_exemplars.s3_parked.json` (the loader NEVER reads that path)
  for re-evaluation once S3 ships a real Bahrain availability/service data
  layer for value reasoning to anchor on.

So this module now asserts the empty-but-valid contract on the canonical file:
  - every category's `exemplars[]` is empty, `anti_patterns[]` preserved,
  - the anti_patterns that exist still surface in the assembled verdict prompt,
  - with no exemplars the loader emits the anti-patterns-only block and NO
    abridged/exemplar scaffolding (the "emit the COMPLETE verdict schema"
    reinforcement is an exemplar-render artifact — correctly absent here),
  - the block still sits inside the static-per-category cache prefix,
  - per-category token cost stays within the dossier §3 budget,
  - the forbidden-words audit is green, _provenance never leaks,
  - the FULL output contract (COMPARISON_SYSTEM :582-611) is untouched.
And it validates the PARKED content as still-correctly-shaped (the 2-3 per
category H1/H3 discriminator set, abridged markers, strict-subset verdicts) so
S3 inherits a verified, ready-to-restore exemplar file.

Loader + injection live on the I2 branch (merged at G2). Until then, the
`verdict_exemplar_loader` import will fail and the whole module skips.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# The loader + injection are I2-owned and arrive on this branch at G2 (rebase).
# Skip the whole module cleanly until then so the lane suite stays green.
pytest.importorskip(
    "app.services.verdict_exemplar_loader",
    reason="I1.3 depends on the I2 loader (merges at G2); RED-until-G2 by design.",
)

from app.services import verdict_exemplar_loader as loader  # noqa: E402
from app.services.extraction_service import build_verdict_prompt  # noqa: E402

try:
    import tiktoken  # noqa: E402
    _ENC = tiktoken.encoding_for_model("gpt-4o")
    def _toks(s: str) -> int:
        return len(_ENC.encode(s))
except Exception:  # pragma: no cover - tiktoken always present in this repo
    def _toks(s: str) -> int:
        return len(s) // 4


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CANONICAL = _REPO_ROOT / "data" / "verdict_exemplars.json"
# The 26 synthetic exemplars, parked verbatim for S3. The loader never reads it.
_PARKED = _REPO_ROOT / "data" / "verdict_exemplars.s3_parked.json"

CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)

# Per-category exemplar-BLOCK token budget. With exemplars[] empty the live
# block is anti-patterns-only (well under budget); the ceiling is kept at the
# dossier §3 COMBINED figure so the gate still holds if exemplars are restored
# from the parked file in S3 (electronics: 3 exemplars + 3 APs ≈ 781).
_EXEMPLAR_TOK_BUDGET = 850

# Forbidden phrases — mirrors test_comparison_quality_detector.py:180 plus the
# Arabic scary/estimate vocab from the copy contract.
_FORBIDDEN = (
    "estimated", "reference price", "couldn't", "try again", "failed to",
    "تعذر", "فشل", "تقدير", "مُقدَّر",
)


@pytest.fixture(scope="module")
def canonical_content() -> dict:
    """The live (empty-exemplars) canonical content."""
    if not _CANONICAL.exists():
        pytest.skip("data/verdict_exemplars.json not yet committed (lands at G3)")
    return json.loads(_CANONICAL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parked_content() -> dict:
    """The parked 26-exemplar set (S3 restore source). Skips if absent."""
    if not _PARKED.exists():
        pytest.skip("data/verdict_exemplars.s3_parked.json not present")
    return json.loads(_PARKED.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _point_loader_at_canonical(monkeypatch):
    """Force the loader to read the canonical file and reset its cache around
    each test (the autouse F2.5 isolation lesson)."""
    monkeypatch.setattr(loader, "_EXEMPLAR_FILE", _CANONICAL)
    loader.reset_cache()
    yield
    loader.reset_cache()


# ---------------------------------------------------------------------------
# Live canonical: empty exemplars, anti_patterns preserved
# ---------------------------------------------------------------------------

def test_all_nine_categories_have_empty_exemplars(canonical_content):
    """Post-measurement: every category's exemplars[] is empty in the canonical
    file (the worked-example layer was redundant over the anti_patterns at T=0).
    The block presence/anti_patterns are validated separately."""
    for cat in CATEGORIES:
        assert cat in canonical_content, f"missing category {cat}"
        exs = canonical_content[cat].get("exemplars")
        assert exs == [], f"{cat}: exemplars[] must be empty (got {len(exs or [])})"


def test_anti_patterns_preserved_in_canonical(canonical_content):
    """The structural-signal carrier — I2's per-category anti_patterns — must
    remain intact in the canonical file. Categories that had APs keep them;
    the AP-only-vs-empty split is exercised in test_per_category_anti_patterns.

    Counts re-pinned for M21 (M18 PO-verdict-text-12): every category gained the
    'score margin cited as the why' anti-pattern (+1 across the board), and the
    four previously-EMPTY categories (supplements/haircare/fashion/other) gained
    their first category-specific AP so build_exemplar_block never returns ''
    for a live category. The old 0-count pins WERE that finding's defect."""
    expected_ap_counts = {
        "electronics": 4, "grocery": 2, "supplements": 2, "makeup": 3,
        "skincare": 2, "haircare": 2, "fragrances": 3, "fashion": 2, "other": 2,
    }
    for cat in CATEGORIES:
        aps = canonical_content[cat].get("anti_patterns")
        assert isinstance(aps, list), f"{cat}: anti_patterns must be a list"
        assert len(aps) == expected_ap_counts[cat], (
            f"{cat}: {len(aps)} anti_patterns, expected {expected_ap_counts[cat]}"
        )


def test_present_anti_patterns_surface_in_verdict_prompt(canonical_content):
    """For categories that DO carry anti_patterns, the rendered block is
    non-empty and lands in the assembled verdict prompt — proving the live
    teaching signal still wires end to end with exemplars empty."""
    ap_cats = [c for c in CATEGORIES if canonical_content[c].get("anti_patterns")]
    assert ap_cats, "expected at least one category with anti_patterns"
    for cat in ap_cats:
        prompt = build_verdict_prompt(products=[{"category": cat}])
        block = loader.build_exemplar_block(cat)
        assert block, f"{cat}: empty block despite present anti_patterns"
        assert block in prompt, f"{cat}: anti-pattern block not in verdict prompt"
        # at least one authored anti-pattern rule is present verbatim
        first_rule = canonical_content[cat]["anti_patterns"][0]["rule"]
        assert first_rule in prompt, f"{cat}: first anti-pattern rule missing from prompt"


# ---------------------------------------------------------------------------
# Prompt-cache discipline — block inside the static-per-category prefix
# ---------------------------------------------------------------------------

def test_exemplar_block_precedes_pain_workflow(canonical_content):
    """The calibration block (anti-patterns-only now) must sit BEFORE the
    cohort-varying pain-workflow section so it stays inside the
    static-per-category cache prefix (D2)."""
    cohort = {"age_group": "25-34", "gender": "Male", "nationality": "Bahraini"}
    # Use AP-carrying categories so the block is non-empty and the header renders.
    for cat in ("electronics", "makeup", "fragrances"):
        prompt = build_verdict_prompt(
            products=[{"category": cat}], user_cohort=cohort
        )
        ex_idx = prompt.find("Verdict calibration")
        pain_idx = prompt.find("Buyer pain-workflow constraints")
        assert ex_idx != -1, f"{cat}: calibration header missing"
        if pain_idx != -1:
            assert ex_idx < pain_idx, (
                f"{cat}: calibration block must precede pain-workflow (cache prefix)"
            )


def test_exemplar_block_is_cohort_independent(canonical_content):
    """The calibration block is identical regardless of cohort — it is keyed on
    category only, so the cached prefix is byte-stable per category. Uses an
    AP-carrying category so the block is non-empty."""
    block_a = loader.build_exemplar_block("electronics")
    block_b = loader.build_exemplar_block("electronics")
    assert block_a == block_b
    # And it does not vary with the cohort passed to the prompt builder.
    p_no_cohort = build_verdict_prompt(products=[{"category": "electronics"}])
    p_cohort = build_verdict_prompt(
        products=[{"category": "electronics"}],
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    )
    assert block_a in p_no_cohort and block_a in p_cohort


# ---------------------------------------------------------------------------
# Token budget
# ---------------------------------------------------------------------------

def test_per_category_token_budget_held(canonical_content):
    """B6: the BINDING gate is the per-call $-cost, not a raw token count. Assert
    every category's calibration block adds <= $0.002/call at gpt-4o input
    pricing, with a token sanity ceiling alongside. With exemplars empty the
    live block is well under budget; the ceiling still guards a future restore.
    Wires the $-gate from scripts/audit_exemplar_token_cost directly into CI."""
    usd_per_1k_4o = 0.0025          # gpt-4o input $/1K tokens
    cost_gate_usd = 0.002           # dossier §3 ceiling
    for cat in CATEGORIES:
        block = loader.build_exemplar_block(cat)
        n = _toks(block)
        cost = n / 1000.0 * usd_per_1k_4o
        assert cost <= cost_gate_usd, (
            f"{cat}: calibration block +${cost:.5f}/call exceeds the ${cost_gate_usd} gate ({n} tok)"
        )
        assert n <= _EXEMPLAR_TOK_BUDGET, (
            f"{cat}: calibration block {n} tok exceeds the {_EXEMPLAR_TOK_BUDGET} sanity ceiling"
        )


# ---------------------------------------------------------------------------
# Forbidden-words audit on the assembled prompt
# ---------------------------------------------------------------------------

def test_no_forbidden_words_in_injected_prompt(canonical_content):
    """No 'estimated' / scary copy anywhere the calibration block reaches the
    prompt."""
    for cat in CATEGORIES:
        prompt = build_verdict_prompt(products=[{"category": cat}]).lower()
        for bad in _FORBIDDEN:
            assert bad not in prompt, f"{cat}: forbidden phrase {bad!r} in prompt"


def test_provenance_never_leaks_into_prompt(canonical_content):
    """_provenance is internal-only metadata (G6 reporting) — it must never
    surface in the model-facing prompt. (Holds trivially with exemplars empty,
    and continues to hold if exemplars are restored.)"""
    for cat in CATEGORIES:
        block = loader.build_exemplar_block(cat)
        assert "_provenance" not in block
        assert "source_pattern_id" not in block


# ---------------------------------------------------------------------------
# Empty-exemplars render invariant: no abridged/exemplar scaffolding
# ---------------------------------------------------------------------------

def test_no_exemplar_scaffolding_when_empty(canonical_content):
    """With exemplars[] empty, the loader renders the anti-patterns-only block
    and emits NEITHER the abridged-example marker NOR the 'emit the COMPLETE
    verdict schema' reinforcement — those exist solely to counter the
    shortening pressure of worked examples, so they are correctly absent when
    there are none. (Counterpart to the no-reinforcement-when-empty invariant
    pinned in test_per_category_anti_patterns.)"""
    for cat in CATEGORIES:
        block = loader.build_exemplar_block(cat)
        assert "abridged" not in block.lower(), (
            f"{cat}: abridged-example scaffolding leaked with no exemplars"
        )
        assert "emit the COMPLETE verdict schema" not in block, (
            f"{cat}: exemplar reinforcement line present with no exemplars"
        )


# ---------------------------------------------------------------------------
# PARKED content stays correctly-shaped for an S3 restore
# ---------------------------------------------------------------------------

def test_parked_set_has_two_to_three_exemplars_per_category(parked_content):
    """The parked file preserves the authored 2-3 exemplars per category so S3
    can restore a verified set rather than re-authoring."""
    for cat in CATEGORIES:
        exs = parked_content[cat].get("exemplars") or []
        assert 2 <= len(exs) <= 3, f"{cat} (parked): {len(exs)} exemplars (want 2-3)"


def test_parked_each_category_has_h1_h3_discriminator_pair(parked_content):
    """The H1+H3 disjoint mirror pair is the core teaching signal (dossier §2):
    teach WHEN value wins vs WHEN a premium is licensed, never a direction. It
    is preserved in the parked set for S3."""
    for cat in CATEGORIES:
        tags = [e.get("teaches") for e in parked_content[cat]["exemplars"]]
        assert "H1" in tags, f"{cat} (parked): no H1 (value-per-dinar) exemplar"
        assert "H3" in tags, f"{cat} (parked): no H3 (premium-justified) exemplar"


def test_parked_abridged_marker_present_on_every_exemplar(parked_content):
    """Every parked exemplar carries the ABRIDGED marker
    ('EXAMPLE — abridged, do not copy structure or content') in its setup so a
    JSON-mode output contract never pattern-matches a partial object on
    restore."""
    for cat in CATEGORIES:
        for ex in parked_content[cat]["exemplars"]:
            assert "EXAMPLE — abridged, do not copy structure or content" in ex["setup"], (
                f"{cat} (parked): exemplar missing the abridged do-not-copy marker"
            )


# ---------------------------------------------------------------------------
# Output-contract integrity — the abridged exemplar CANNOT be mistaken for a
# real verdict response (dispatcher directive #2b)
# ---------------------------------------------------------------------------

# The full verdict OUTPUT contract the model must emit (COMPARISON_SYSTEM
# :582-611). An abridged exemplar carries only the discriminator fields and is
# missing the rest — so it can never satisfy the real output contract.
_FULL_VERDICT_REQUIRED = {
    "winner_index", "winner_declaration", "winner_reason", "key_tradeoff",
    "value_context", "best_for",
    "product_0_pros", "product_0_cons", "product_1_pros", "product_1_cons",
    "specs_comparison",
}
# The compact teaching subset an abridged exemplar is allowed to show.
_ABRIDGED_ALLOWED = {
    "winner_index", "winner_declaration", "winner_reason", "key_tradeoff",
    "value_context",
}


def test_parked_abridged_verdict_is_strict_subset_never_full_output(parked_content):
    """Each parked exemplar verdict_json is a STRICT subset of the discriminator
    fields — it omits best_for / pros / cons / specs_comparison, so it can
    never be confused with (or satisfy) the real :582-611 output contract on
    restore."""
    for cat in CATEGORIES:
        for ex in parked_content[cat]["exemplars"]:
            keys = set(ex["verdict_json"].keys())
            assert keys <= _ABRIDGED_ALLOWED, (
                f"{cat} (parked): abridged verdict has out-of-scope keys {keys - _ABRIDGED_ALLOWED}"
            )
            # It must be MISSING the output-only fields — proving it is not a
            # complete verdict response.
            output_only = _FULL_VERDICT_REQUIRED - _ABRIDGED_ALLOWED
            assert not (keys & output_only), (
                f"{cat} (parked): abridged verdict leaked output-only fields {keys & output_only}"
            )


def test_real_verdict_output_contract_untouched():
    """The production verdict path still demands the FULL output schema — the
    calibration block changes the prompt PREFIX, never the response_format or the
    pros/cons contract. Guarded by the standing test_verdict_response_format
    suite; here we assert COMPARISON_SYSTEM still specifies the full field set
    so emptying exemplars (or restoring them) can't have quietly narrowed it."""
    from app.services.extraction_service import COMPARISON_SYSTEM
    for required in ("best_for", "product_0_pros", "product_1_cons", "specs_comparison"):
        assert required in COMPARISON_SYSTEM, (
            f"the real verdict schema lost required field {required!r}"
        )

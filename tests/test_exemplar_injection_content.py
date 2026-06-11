"""I1.3 — injection CONTENT tests for the few-shot verdict exemplars.

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § I1.3
Contract: I1.1 (schema) + I2.1 (verdict_exemplar_loader.build_exemplar_block,
extraction_service.build_verdict_prompt injection).

These assert the I1.2-authored exemplar CONTENT once injected:
  - every category's exemplars surface in the assembled verdict prompt,
  - the exemplar block sits inside the static-per-category prefix (BEFORE the
    cohort-varying pain-workflow block) so OpenAI prompt-caching sees a
    byte-identical prefix per category (D2 discipline),
  - per-category token cost stays within the dossier §3 budget (~700 tok of
    exemplars; +<=$0.002/call vs the gate),
  - the forbidden-words audit is green on the assembled prompt
    (test_comparison_quality_detector.py:180 pattern),
  - _provenance never leaks into the prompt.

The exemplar file used is the I1-authored content (data/verdict_exemplars.json
after G3). To stay independent of merge order, each test loads the canonical
content into a temp file and points the loader at it via reset_cache() — so
the suite is green on this branch BEFORE the I2 loader lands at G2, and keeps
passing against the real file afterwards.

Loader + injection live on the I2 branch (merged at G2). Until then, the
`verdict_exemplar_loader` import will fail and the whole module skips — which
is the correct RED-until-G2 posture for a cross-lane dependency.
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

CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)

# Per-category exemplar token budget (dossier §3: ~700 tok exemplars/cat).
_EXEMPLAR_TOK_BUDGET = 700

# Forbidden phrases — mirrors test_comparison_quality_detector.py:180 plus the
# Arabic scary/estimate vocab from the copy contract.
_FORBIDDEN = (
    "estimated", "reference price", "couldn't", "try again", "failed to",
    "تعذر", "فشل", "تقدير", "مُقدَّر",
)


@pytest.fixture(scope="module")
def canonical_content() -> dict:
    """The I1-authored exemplar content. Skips if the file is absent (i.e.
    content not yet committed at G3) so the suite is honest about coverage."""
    if not _CANONICAL.exists():
        pytest.skip("data/verdict_exemplars.json not yet committed (lands at G3)")
    return json.loads(_CANONICAL.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _point_loader_at_canonical(monkeypatch):
    """Force the loader to read the canonical file and reset its cache around
    each test (the autouse F2.5 isolation lesson)."""
    monkeypatch.setattr(loader, "_EXEMPLAR_FILE", _CANONICAL)
    loader.reset_cache()
    yield
    loader.reset_cache()


# ---------------------------------------------------------------------------
# Content presence + structure
# ---------------------------------------------------------------------------

def test_all_nine_categories_have_exemplars(canonical_content):
    for cat in CATEGORIES:
        assert cat in canonical_content, f"missing category {cat}"
        exs = canonical_content[cat].get("exemplars") or []
        assert 2 <= len(exs) <= 3, f"{cat}: {len(exs)} exemplars (want 2-3)"


def test_each_category_has_h1_h3_discriminator_pair(canonical_content):
    """The H1+H3 disjoint mirror pair is the core teaching signal (dossier §2):
    teach WHEN value wins vs WHEN a premium is licensed, never a direction."""
    for cat in CATEGORIES:
        tags = [e.get("teaches") for e in canonical_content[cat]["exemplars"]]
        assert "H1" in tags, f"{cat}: no H1 (value-per-dinar) exemplar"
        assert "H3" in tags, f"{cat}: no H3 (premium-justified) exemplar"


def test_exemplars_surface_in_verdict_prompt(canonical_content):
    """Each category's exemplar titles + setups appear in the assembled
    verdict prompt — proving injection wires content end to end."""
    for cat in CATEGORIES:
        prompt = build_verdict_prompt(products=[{"category": cat}])
        block = loader.build_exemplar_block(cat)
        assert block, f"{cat}: empty exemplar block"
        assert block in prompt, f"{cat}: exemplar block not in verdict prompt"
        # at least one authored setup string is present verbatim
        first_setup = canonical_content[cat]["exemplars"][0]["setup"]
        assert first_setup in prompt, f"{cat}: first exemplar setup missing from prompt"


# ---------------------------------------------------------------------------
# Prompt-cache discipline — block inside the static-per-category prefix
# ---------------------------------------------------------------------------

def test_exemplar_block_precedes_pain_workflow(canonical_content):
    """The exemplar block must sit BEFORE the cohort-varying pain-workflow
    section so it stays inside the static-per-category cache prefix (D2)."""
    # A cohort triggers the pain-workflow block to render after the exemplars.
    cohort = {"age_group": "25-34", "gender": "Male", "nationality": "Bahraini"}
    for cat in ("electronics", "makeup", "fragrances"):
        prompt = build_verdict_prompt(
            products=[{"category": cat}], user_cohort=cohort
        )
        ex_idx = prompt.find("Verdict calibration examples")
        pain_idx = prompt.find("Buyer pain-workflow constraints")
        assert ex_idx != -1, f"{cat}: exemplar header missing"
        if pain_idx != -1:
            assert ex_idx < pain_idx, (
                f"{cat}: exemplar block must precede pain-workflow (cache prefix)"
            )


def test_exemplar_block_is_cohort_independent(canonical_content):
    """The exemplar block is identical regardless of cohort — it is keyed on
    category only, so the cached prefix is byte-stable per category."""
    block_a = loader.build_exemplar_block("skincare")
    block_b = loader.build_exemplar_block("skincare")
    assert block_a == block_b
    # And it does not vary with the cohort passed to the prompt builder.
    p_no_cohort = build_verdict_prompt(products=[{"category": "skincare"}])
    p_cohort = build_verdict_prompt(
        products=[{"category": "skincare"}],
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    )
    assert block_a in p_no_cohort and block_a in p_cohort


# ---------------------------------------------------------------------------
# Token budget
# ---------------------------------------------------------------------------

def test_per_category_token_budget_held(canonical_content):
    """Exemplar block per category stays within the dossier §3 ~700-tok
    budget — the arithmetic behind the +<=$0.002/call gate."""
    for cat in CATEGORIES:
        block = loader.build_exemplar_block(cat)
        n = _toks(block)
        assert n <= _EXEMPLAR_TOK_BUDGET, (
            f"{cat}: exemplar block {n} tok exceeds {_EXEMPLAR_TOK_BUDGET}"
        )


# ---------------------------------------------------------------------------
# Forbidden-words audit on the assembled prompt
# ---------------------------------------------------------------------------

def test_no_forbidden_words_in_injected_prompt(canonical_content):
    """No 'estimated' / scary copy anywhere the exemplars reach the prompt."""
    for cat in CATEGORIES:
        prompt = build_verdict_prompt(products=[{"category": cat}]).lower()
        for bad in _FORBIDDEN:
            assert bad not in prompt, f"{cat}: forbidden phrase {bad!r} in prompt"


def test_provenance_never_leaks_into_prompt(canonical_content):
    """_provenance is internal-only metadata (G6 reporting) — it must never
    surface in the model-facing prompt."""
    for cat in CATEGORIES:
        block = loader.build_exemplar_block(cat)
        assert "_provenance" not in block
        assert "source_pattern_id" not in block


def test_label_present_on_every_exemplar(canonical_content):
    """Every exemplar carries the 'EXAMPLE — do not copy' contamination guard
    in its setup (belt-and-suspenders with the loader's title render)."""
    for cat in CATEGORIES:
        for ex in canonical_content[cat]["exemplars"]:
            assert "EXAMPLE — do not copy" in ex["setup"], (
                f"{cat}: exemplar missing the do-not-copy label"
            )

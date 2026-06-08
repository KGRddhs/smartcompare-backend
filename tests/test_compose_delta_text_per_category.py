"""Wave-2 idle-time fix (2026-06-08) — full coverage of `_compose_delta_text`
across all 9 categories × 6 dims = 54 cells.

Before the fix: 28/54 cells fell back to the bare `"+28pt"` string,
making the design cards look like stubbed copy. After the fix: 52/54
cells emit a labelled string (e.g. `"+28pt nutrition"`, `"+28pt craft"`).
The 2 remaining bare cells (`electronics.value`, `other.value`) are
unreachable in production — `build_dimensions_v2` strips per-category
`value_*` keys via the (`value_`, `_value_`) filter because the core
`_dim_value` builder already covers value semantics.

This file's contract: every per-category dim key emits either a
specific phrase (battery %, longevity hours, dosage IU) when spec
hooks fire, OR a labelled fallback (`"+{margin}pt {label}"`) so the
FE never sees an identical-bare "+28pt" caption.
"""
from __future__ import annotations

import pytest

from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    _compose_delta_text,
)


def _expand_cells():
    """Yield (category, public_dim_key) tuples for every per-cat dim,
    skipping the 2 unreachable `value` cells."""
    skipped_public = {"value"}  # core dim — never reaches _compose_delta_text
    for cat, dim_keys in CATEGORY_DIMENSIONS.items():
        for full_key in dim_keys:
            public = full_key[:-6] if full_key.endswith("_score") else full_key
            if public in skipped_public:
                continue
            yield (cat, public)


_NON_VALUE_CELLS = list(_expand_cells())
_EMPTY_PRODUCTS = [{"specs": {}}, {"specs": {}}]


# ---------------------------------------------------------------------------
# Invariant 1 — no cell emits the bare "+28pt" stub
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category,dim_key", _NON_VALUE_CELLS)
def test_delta_text_not_bare_stub(category, dim_key):
    """No cell should emit just `"+28pt"` with no label — confirm the
    Wave-2 fallback dict covers every non-`value` per-category dim."""
    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    assert result != "+28pt", (
        f"{category}.{dim_key} fell back to bare '+28pt' stub — needs a "
        "label entry in _DIM_LABEL_FALLBACKS or a category-specific branch"
    )


# ---------------------------------------------------------------------------
# Invariant 2 — every cell emits a string containing "pt" or a unit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category,dim_key", _NON_VALUE_CELLS)
def test_delta_text_contains_quantitative_marker(category, dim_key):
    """Every cell must carry a quantitative marker — either the `pt`
    score-margin suffix OR a unit like `h` / `IU` / `mg` / `%` when a
    spec hook fires. Bare descriptive strings without a number are
    forbidden per pain-workflow priors (quantify, don't editorialize)."""
    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    has_marker = any(
        token in result.lower()
        for token in ("pt", "h", "iu", "mg", "mcg", "%", "×", "year", "ml")
    )
    assert has_marker, (
        f"{category}.{dim_key} delta_text {result!r} has no quantitative marker"
    )


# ---------------------------------------------------------------------------
# Invariant 3 — no forbidden vocabulary anywhere in the 54 cells
# ---------------------------------------------------------------------------


_FORBIDDEN = ("couldn't", "try again", "failed", "estimated", "reference price")


@pytest.mark.parametrize("category,dim_key", _NON_VALUE_CELLS)
def test_delta_text_no_forbidden_vocab(category, dim_key):
    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    text = result.lower()
    for word in _FORBIDDEN:
        assert word not in text, (
            f"{category}.{dim_key} delta_text {result!r} contains forbidden {word!r}"
        )


# ---------------------------------------------------------------------------
# Invariant 4 — banned evaluative words (matches test_dimensions_builder audit)
# ---------------------------------------------------------------------------


_BANNED_EVALUATIVE = (
    "great",
    "worst",
    "recommend",
    "good",
    "better",
    "worse",
    "best",
    "smart",
    "choose",
    "winner",
    "beats",
    "pick",
    "excellent",
)


@pytest.mark.parametrize("category,dim_key", _NON_VALUE_CELLS)
def test_delta_text_no_banned_evaluative_words(category, dim_key):
    """Pain-workflow priors — quantify, don't editorialize. Words on the
    banned list (great/best/recommend/etc.) leak subjective judgement
    into a factual delta caption."""
    import re

    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    pattern = re.compile(
        r"\b(" + "|".join(_BANNED_EVALUATIVE) + r")\b",
        re.IGNORECASE,
    )
    match = pattern.search(result)
    assert match is None, (
        f"{category}.{dim_key} delta_text {result!r} contains banned "
        f"evaluative word {match.group(0)!r}"
    )


# ---------------------------------------------------------------------------
# Invariant 5 — labels match the design-doc semantic intent
# ---------------------------------------------------------------------------


# Sample of the most user-visible labels — guards against an accidental
# rename (e.g. 'craft' → 'craftsmanship' drift).
_SEMANTIC_LABELS = {
    ("electronics", "performance"): "performance",
    ("electronics", "ecosystem"): "ecosystem",
    ("fragrances", "longevity"): "longevity",
    ("fragrances", "wear_value"): "value per wear",
    ("supplements", "efficacy"): "efficacy signal",
    ("supplements", "safety"): "safety profile",
    ("grocery", "nutrition"): "nutrition",
    ("makeup", "shade"): "shade range",
    ("skincare", "actives"): "active ingredients",
    ("haircare", "hair_match"): "hair match",
    ("fashion", "craft"): "craftsmanship",
    ("fashion", "cpw"): "cost per wear",
    ("other", "feature_match"): "feature match",
}


@pytest.mark.parametrize("key,expected_token", list(_SEMANTIC_LABELS.items()))
def test_delta_text_semantic_label_token(key, expected_token):
    category, dim_key = key
    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    assert expected_token in result.lower(), (
        f"{category}.{dim_key} delta_text {result!r} does not contain "
        f"semantic token {expected_token!r}"
    )


# ---------------------------------------------------------------------------
# Sanity — score-margin number appears in the fallback output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category,dim_key", _NON_VALUE_CELLS)
def test_delta_text_includes_score_margin(category, dim_key):
    """Default-fallback cells should include the score margin number
    (e.g. `+28pt`). Specific-branch cells may swap it for a unit (e.g.
    `10h vs 6h`, `5000 IU vs 1000 IU`) — those are still acceptable."""
    result = _compose_delta_text(dim_key, _EMPTY_PRODUCTS, 60, 88)
    has_number = any(c.isdigit() for c in result)
    assert has_number, (
        f"{category}.{dim_key} delta_text {result!r} has no numeric component"
    )

"""Pydantic v2 contract for the Bundle E `dimensions[]` payload — see design § Decision 2."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

BANNED_DELTA_WORDS: frozenset[str] = frozenset(
    {
        "best", "pick", "excellent", "great", "recommend", "winner", "worst",
        "better", "worse", "beats", "smart", "good", "choose",
    }
)

_BANNED_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(BANNED_DELTA_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

CORE_DIMENSION_KEYS: frozenset[str] = frozenset({"price", "reviews", "value"})


class Dimension(BaseModel):
    key: str
    label: str
    score_a: int
    score_b: int
    delta_text: str
    confidence: Literal["high", "medium", "low"]
    is_core: bool

    @field_validator("delta_text")
    @classmethod
    def _reject_evaluative_language(cls, v: str) -> str:
        match = _BANNED_PATTERN.search(v)
        if match:
            offending = match.group(1).lower()
            raise ValueError(
                f"delta_text contains banned evaluative word '{offending}' — "
                f"use factual phrasing only (design § Decision 5)"
            )
        return v


class OverallScore(BaseModel):
    product_a: int
    product_b: int


class ScoringV2(BaseModel):
    overall_score: OverallScore
    win_margin: int
    dimensions: list[Dimension]

    @model_validator(mode="after")
    def _validate_dimensions_invariants(self) -> "ScoringV2":
        if len(self.dimensions) > 8:
            raise ValueError(
                f"dimensions[] has {len(self.dimensions)} entries — max 8 allowed "
                f"(3 core + 0..5 contextual)"
            )
        core_keys = {d.key for d in self.dimensions if d.is_core}
        if core_keys != CORE_DIMENSION_KEYS:
            raise ValueError(
                f"core dimensions must be exactly {sorted(CORE_DIMENSION_KEYS)} — "
                f"got {sorted(core_keys)}"
            )
        return self

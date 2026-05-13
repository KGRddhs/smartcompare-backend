"""Deterministic 2-sentence verdict from dimension deltas — Bundle E § Decision 5."""
from __future__ import annotations

from typing import Any

_CONDITIONAL_OPENER = {"en": "If you want", "ar": "If you want"}


def _winner_idx(scoring: dict) -> int:
    overall = scoring.get("overall_score", {})
    idx = overall.get("winner_idx")
    if idx is not None:
        return int(idx)
    a = overall.get("product_a", 0)
    b = overall.get("product_b", 0)
    return 0 if a >= b else 1


def _dim_winner(dim: dict) -> int:
    return 0 if dim.get("score_a", 0) >= dim.get("score_b", 0) else 1


def _runner_label_token(dim: dict) -> str:
    delta = dim.get("delta_text", "")
    head = delta.split(",")[0].strip()
    return head or dim.get("label", "")


def build_factual_verdict(
    scoring: dict[str, Any],
    products: list[dict[str, Any]],
    lang: str = "en",
) -> str:
    top_idx = _winner_idx(scoring)
    runner_idx = 1 - top_idx
    dims = scoring.get("dimensions", [])

    winner_core_deltas = [
        d["delta_text"]
        for d in dims
        if d.get("is_core") and _dim_winner(d) == top_idx
    ][:3]
    line1 = ", ".join(winner_core_deltas)

    runner_dims = [d for d in dims if _dim_winner(d) == runner_idx]
    runner_brand = (
        products[runner_idx].get("brand")
        or products[runner_idx].get("name", "").split()[0]
        or "the alternative"
    )
    if runner_dims:
        token = _runner_label_token(runner_dims[0])
        line2 = f"{_CONDITIONAL_OPENER.get(lang, _CONDITIONAL_OPENER['en'])} {token}, the {runner_brand} fits."
    else:
        line2 = f"{_CONDITIONAL_OPENER.get(lang, _CONDITIONAL_OPENER['en'])} a different mix, the {runner_brand} is a fair alternative."

    if line1:
        return f"{line1}. {line2}"
    return line2

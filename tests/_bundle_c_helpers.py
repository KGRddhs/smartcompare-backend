"""Bundle C — shared assertion helpers (Section C plan, task C.0.1).

Enforces the FIVE critical rules across all Bundle C tests:
  1. NO info banners (frontend-side assertion in TS helper).
  2. NO backend internals in user-facing reveals — `assert_no_magnitude_fields`.
  3. NEVER "estimated" / "reference" / "indicative" in user-facing copy.
  4. Diagnostic-first for §1a/§1b/§1c — RED tests pre-impl, GREEN post-impl.
  5. NO scary copy in i18n EN+AR.

Import these helpers from any Bundle C test file.
"""
from __future__ import annotations

from typing import Any, Iterable

FORBIDDEN_UI_STRINGS_EN = {
    "estimated", "estimate", "reference", "indicative",
    "couldn't", "try again", "Failed to",
}
FORBIDDEN_UI_STRINGS_AR = {"تقدير", "مُقدَّر", "تعذر", "فشل"}


def assert_no_forbidden_strings(rendered_text: str) -> None:
    """Backtest rendered UI string against forbidden vocabulary.

    Used on user-visible response fields (verdict_text, pros/cons, factual_verdict
    line1/line2, captions). NOT used on backend enums like `source_method`.
    """
    if not isinstance(rendered_text, str):
        return
    lower = rendered_text.lower()
    for term in FORBIDDEN_UI_STRINGS_EN:
        assert term.lower() not in lower, (
            f"Forbidden EN UI string '{term}' found in: {rendered_text[:200]!r}"
        )
    for term in FORBIDDEN_UI_STRINGS_AR:
        assert term not in rendered_text, (
            f"Forbidden AR UI string '{term}' found in: {rendered_text[:200]!r}"
        )


FORBIDDEN_MAGNITUDE_KEYS = {
    "magnitude", "shift_pct", "weight_delta", "cap_pct",
    "coefficient", "raw_shift", "shift_value", "shift_magnitude",
    "cap_percent", "scaling_factor", "formula_weight",
}


def assert_no_magnitude_fields(payload: Any) -> None:
    """Recursively walk payload; assert no forbidden magnitude/coefficient keys.

    Spec §7b + project rule "no backend internals in user-facing reveals":
    `applied_shifts` items must be {dim_display, direction} only. The full
    response payload must not leak coefficients, cap percentages, or shift math.
    """
    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in FORBIDDEN_MAGNITUDE_KEYS, (
                    f"Forbidden magnitude key '{k}' in payload at {path or '<root>'}"
                )
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(payload)


def collect_user_visible_strings(response: dict) -> list[str]:
    """Collect every user-visible string from a comparison response.

    Excludes backend enums like `source_method`. Used by forbidden-vocabulary
    sweeps over `/api/v1/text/compare` payloads.
    """
    visible: list[str] = []
    for p in response.get("products", []) or []:
        visible.append(p.get("verdict_text", "") or "")
        visible.extend(p.get("pros", []) or [])
        visible.extend(p.get("cons", []) or [])
        # value_match captions live on scoring_v2 per product
        sv2 = p.get("scoring_v2", {}) or {}
        visible.append(sv2.get("value_match_caption", "") or "")
    comparison = response.get("comparison", {}) or {}
    visible.append(comparison.get("winner_declaration", "") or "")
    visible.append(comparison.get("winner_reason", "") or "")
    visible.append(comparison.get("best_for", "") or "")
    visible.append(comparison.get("value_context", "") or "")
    factual = (response.get("scoring_v2", {}) or {}).get("factual_verdict", {}) or {}
    visible.append(factual.get("line1", "") or "")
    visible.append(factual.get("line2", "") or "")
    return [s for s in visible if s]


def assert_response_clean_of_forbidden_strings(response: dict) -> None:
    """Convenience: assert no forbidden vocabulary anywhere user-visible."""
    for s in collect_user_visible_strings(response):
        assert_no_forbidden_strings(s)

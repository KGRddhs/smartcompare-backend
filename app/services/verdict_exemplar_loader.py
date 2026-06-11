"""Few-shot verdict exemplar + anti-pattern loader (S2 I2.1).

Loads data/verdict_exemplars.json ONCE per process and exposes
build_exemplar_block(category) — the text injected into the verdict-call
system prompt (extraction_service.build_verdict_prompt) AFTER the category
personality and BEFORE the pain-workflow block, inside the static-per-category
prefix so OpenAI prompt-caching sees a byte-identical prefix per category.

Ownership split inside the JSON file (I1.1/I2.1 contract):
  - `exemplars[]` — authored by Lane I1 (synthetic rewrites of the 45-id
    pure-bias patterns; never verbatim gold pairs — Decision E).
  - `anti_patterns[]` — authored by Lane I2 (per-category named failure modes
    + counter-rules, dossier §3).

The loader is deliberately tolerant: a missing file, malformed JSON, an
absent category, or missing inner keys all yield "" so the verdict prompt
builder degrades to its pre-S2 behaviour and never raises. This is the same
posture as pain_workflow_loader.py.

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § 2 (Lane I2)
Design: docs/plans/2026-06-10-bundle-b-s2-design-inputs.md § 3
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EXEMPLAR_FILE = _REPO_ROOT / "data" / "verdict_exemplars.json"


# ---------------------------------------------------------------------------
# Lazy load + cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_exemplars() -> Optional[Dict[str, Any]]:
    if not _EXEMPLAR_FILE.exists():
        logger.warning("verdict_exemplars.json missing — exemplar injection skipped")
        return None
    try:
        return json.loads(_EXEMPLAR_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load verdict_exemplars.json: %s", exc)
        return None


def reset_cache() -> None:
    """Drop the on-process cache. Used by tests that swap the data file."""
    _load_exemplars.cache_clear()


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

# COMPACT Option A (dispatcher ruling 2026-06-11): exemplars carry only the
# four teaching fields, rendered as a labeled ABRIDGED block (~200 tok each) —
# NOT a full verdict_json dump. Fields may sit at the exemplar top level OR
# under a nested `verdict` / `verdict_json` block; we read either.
_COMPACT_FIELDS = ("winner_index", "winner_reason", "key_tradeoff", "value_context")


def _compact_source(ex: Dict[str, Any]) -> Dict[str, Any]:
    """Return the dict that holds the compact verdict fields. Prefer a nested
    `verdict`/`verdict_json` block; fall back to the exemplar top level."""
    for key in ("verdict", "verdict_json"):
        nested = ex.get(key)
        if isinstance(nested, dict):
            return nested
    return ex


def _render_value_context(vc: Any) -> Optional[str]:
    """Render the per-product value_context dict as one readable line."""
    if isinstance(vc, dict):
        parts = []
        for pk in ("product_0", "product_1"):
            val = vc.get(pk)
            if val:
                parts.append(f"{pk}: {val}")
        if parts:
            return " | ".join(parts)
        return None
    if isinstance(vc, str) and vc.strip():
        return vc.strip()
    return None


def _first(d: Dict[str, Any], *keys: str) -> Any:
    """Return the first present, truthy value among `keys` (schema-alias
    tolerance: 'content is canon, loader is consumer' — accept the common
    field-name variants I1's ratified schema might use)."""
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _render_exemplar(ex: Dict[str, Any]) -> List[str]:
    """Render ONE exemplar as a labeled ABRIDGED teaching block (COMPACT
    Option A). `_provenance` (the source pattern id) is internal-only and MUST
    NOT surface in the prompt. Field-name aliases are accepted so the loader
    consumes whatever shape the ratified exemplar content ships."""
    lines: List[str] = []
    title = ex.get("title") or "EXAMPLE -- do not copy"
    # ABRIDGED marker — dispatcher-ratified VERBATIM string, identical to the
    # marker I1 carries in every exemplar's setup. These cases show only the
    # teaching fields, NOT the full verdict schema, so the model must never
    # copy their structure or content.
    lines.append(
        f"EXAMPLE -- abridged, do not copy structure or content "
        f"(teaches the reasoning move only): {title}"
    )
    setup = _first(ex, "setup", "context", "scenario", "pairing")
    if setup:
        lines.append(f"Setup: {setup}")

    src = _compact_source(ex)
    # winner_index — render as a 1-based "Product N wins" so it reads naturally.
    wi = src.get("winner_index")
    if wi is None:
        wi = ex.get("winner_index")
    if isinstance(wi, int) and wi in (0, 1):
        lines.append(f"Winner: Product {wi + 1}")
    reason = _first(src, "winner_reason", "reason")
    if reason:
        lines.append(f"Why: {reason}")
    tradeoff = _first(src, "key_tradeoff", "tradeoff")
    if tradeoff:
        lines.append(f"Tradeoff: {tradeoff}")
    vc_line = _render_value_context(_first(src, "value_context", "value"))
    if vc_line:
        lines.append(f"Value: {vc_line}")
    return lines


def _render_anti_pattern(ap: Dict[str, Any]) -> Optional[str]:
    name = ap.get("name")
    rule = ap.get("rule")
    if not name or not rule:
        return None
    return f"ANTI-PATTERN -- {name}: {rule}"


def build_exemplar_block(category: str) -> str:
    """Compose the verdict-prompt section carrying few-shot exemplars +
    anti-patterns for `category`.

    Returns "" when the file is unavailable, the category is absent, or both
    arrays are empty — callers can append blindly.

    G2 vs G3 state (the shipped file ships exemplars[] EMPTY but per-category
    anti_patterns POPULATED): at G2 this renders ONLY the anti-pattern block
    (section title + "Avoid these failure modes:" lines) — no examples-preamble
    and no reinforcement line, since there are no examples below. When I1's
    exemplar content lands at G3, the examples-preamble, the abridged exemplars,
    and the COMPLETE-schema reinforcement all render too.
    """
    data = _load_exemplars()
    if not data:
        return ""
    cat = (category or "other").strip().lower()
    entry = data.get(cat)
    if not isinstance(entry, dict):
        return ""

    exemplars = entry.get("exemplars") or []
    anti_patterns = entry.get("anti_patterns") or []
    if not exemplars and not anti_patterns:
        return ""

    lines: List[str] = [
        "",
        "## Verdict calibration (Bahrain-buyer reasoning)",
        "",
    ]

    if anti_patterns:
        lines.append("Avoid these failure modes:")
        for ap in anti_patterns:
            rendered = _render_anti_pattern(ap)
            if rendered:
                lines.append(f"- {rendered}")
        lines.append("")

    # F1: the examples-preamble (and the exemplars + reinforcement) render ONLY
    # when there are exemplars below — never for the AP-only / G2-skeleton state
    # (a "the examples below..." header with zero examples is incoherent).
    if exemplars:
        lines.extend([
            "The examples below are synthetic teaching cases. Mirror the REASONING",
            "MOVE they demonstrate (when value-per-dinar wins vs when a premium is",
            "licensed; how a Bahrain buyer weighs local availability and Gulf",
            "climate) -- never copy their brands, numbers, or wording.",
            "",
        ])
        for ex in exemplars:
            lines.extend(_render_exemplar(ex))
            lines.append("")
        # Reinforcement: abridged examples show only the teaching fields — the
        # model must still emit the COMPLETE verdict schema.
        lines.append(
            "The examples above are abridged. Always emit the COMPLETE verdict schema."
        )
        lines.append("")

    return "\n".join(lines)

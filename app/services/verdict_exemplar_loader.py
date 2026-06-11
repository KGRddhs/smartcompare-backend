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

def _render_exemplar(ex: Dict[str, Any]) -> List[str]:
    """Render ONE exemplar into prompt lines. `_provenance` (the source
    pattern id) is internal-only and MUST NOT surface in the prompt."""
    lines: List[str] = []
    title = ex.get("title") or "EXAMPLE -- do not copy"
    lines.append(f"EXAMPLE (do not copy -- teaches the reasoning move only): {title}")
    setup = ex.get("setup")
    if setup:
        lines.append(f"Setup: {setup}")
    verdict = ex.get("verdict_json")
    if verdict is not None:
        # Compact, deterministic JSON (sort_keys so the per-category prefix is
        # byte-stable for OpenAI prompt-caching).
        lines.append("Verdict: " + json.dumps(verdict, sort_keys=True, ensure_ascii=False))
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
    arrays are empty — so callers can append blindly (the G2 skeleton ships
    every category with empty arrays, so this returns "" until I1 content
    lands at G3).
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
        "## Verdict calibration examples (Bahrain-buyer reasoning)",
        "The examples below are synthetic teaching cases. Mirror the REASONING",
        "MOVE they demonstrate (when value-per-dinar wins vs when a premium is",
        "licensed; how a Bahrain buyer weighs local availability and Gulf",
        "climate) -- never copy their brands, numbers, or wording.",
        "",
    ]

    if anti_patterns:
        lines.append("Avoid these failure modes:")
        for ap in anti_patterns:
            rendered = _render_anti_pattern(ap)
            if rendered:
                lines.append(f"- {rendered}")
        lines.append("")

    for ex in exemplars:
        lines.extend(_render_exemplar(ex))
        lines.append("")

    return "\n".join(lines)

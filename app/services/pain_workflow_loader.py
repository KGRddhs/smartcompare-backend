"""Pain-workflow + decision-style prior loader (A-L4.2).

Loads data/pain_workflow_priors.json + data/decision_style_priors.json
ONCE per process and exposes helpers that the verdict prompt builder uses
to inject the top-3 pain-workflow instructions + the cohort's preferred
decision style.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.2
Design: docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PAIN_FILE = _REPO_ROOT / "data" / "pain_workflow_priors.json"
_STYLE_FILE = _REPO_ROOT / "data" / "decision_style_priors.json"


# Canonical decision-style → human-readable verdict-style hint (used in
# verdict prompt). Keys mirror decision_style_priors.json exactly.
DECISION_STYLE_HINTS: Dict[str, str] = {
    "show_all_details": (
        "Lead with the verdict, then surface every meaningful spec/price/review "
        "detail. Users in this segment read thoroughly before committing."
    ),
    "show_only_main_differences": (
        "Lead with the verdict, then compress to ONLY the differences that "
        "matter. Drop anything both products share."
    ),
    "show_2_or_3_options": (
        "Lead with the verdict. Frame the runner-up as a viable alternative "
        "scenario — name the conditions under which it would be the right pick."
    ),
    "suggest_one_best": (
        "Lead with the verdict. Make the recommendation unambiguous in the "
        "first sentence. Detail follows for users who tap to expand."
    ),
}


# ---------------------------------------------------------------------------
# Lazy load + cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_pain_priors() -> Optional[Dict[str, Any]]:
    if not _PAIN_FILE.exists():
        logger.warning("pain_workflow_priors.json missing — top-3 injection skipped")
        return None
    try:
        return json.loads(_PAIN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load pain_workflow_priors.json: %s", exc)
        return None


@lru_cache(maxsize=1)
def _load_style_priors() -> Optional[Dict[str, Any]]:
    if not _STYLE_FILE.exists():
        logger.warning("decision_style_priors.json missing — style hint skipped")
        return None
    try:
        return json.loads(_STYLE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load decision_style_priors.json: %s", exc)
        return None


def reset_cache() -> None:
    """Drop the on-process cache. Used by tests that swap data files."""
    _load_pain_priors.cache_clear()
    _load_style_priors.cache_clear()


# ---------------------------------------------------------------------------
# Cohort key normalisation — must match etl_survey_to_priors.py exactly
# ---------------------------------------------------------------------------

_NATIONALITY_NORMALISE: Dict[str, str] = {
    "bahraini": "bahraini",
    "non-bahraini": "non_bahraini",
    "non_bahraini": "non_bahraini",
    "expat": "non_bahraini",
}


def _cohort_key(user_cohort: Optional[Dict[str, Any]]) -> Optional[str]:
    """Produce the ETL-canonical cohort key or None if any field missing."""
    if not user_cohort:
        return None
    age = (user_cohort.get("age_group") or "").strip()
    gender = (user_cohort.get("gender") or "").strip().lower()
    nationality = (user_cohort.get("nationality") or "").strip().lower()
    if not (age and gender and nationality):
        return None
    if gender not in {"male", "female"}:
        return None
    nat = _NATIONALITY_NORMALISE.get(nationality)
    if not nat:
        return None
    return f"{age}_{gender}_{nat}"


# ---------------------------------------------------------------------------
# Top-3 pain workflow selection
# ---------------------------------------------------------------------------

# decision_speed (TL;DR-first) is the shipping floor — it's always included
# even if not in the top-3 by cohort weight, because the design § 6
# "Lead with TL;DR" instruction is non-negotiable. We append it AFTER the
# cohort top-3 if not already present.
_TLDR_WORKFLOW_NAME = "decision_speed"


def _rank_cohort_top_3(cohort_key: str, priors: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return up to 3 workflow dicts ranked by per_cohort_weight for the
    given cohort. Falls back to global rank when cohort has fewer than 3
    workflows with non-zero weight."""
    workflows = priors.get("workflows", [])
    scored: List[tuple] = []  # (weight, baseline_rank, workflow_dict)
    for w in workflows:
        per_cohort = (w.get("per_cohort_weight") or {}).get(cohort_key, 0.0)
        scored.append((per_cohort, w["rank"], w))
    # Descending weight, ascending baseline rank for ties.
    scored.sort(key=lambda t: (-t[0], t[1]))

    chosen: List[Dict[str, Any]] = []
    seen_names: set = set()
    for weight, _, w in scored:
        if weight <= 0:
            continue
        chosen.append(w)
        seen_names.add(w["name"])
        if len(chosen) >= 3:
            break

    # Top-up with global rank if cohort had < 3 non-zero entries.
    if len(chosen) < 3:
        for w in workflows:
            if w["name"] not in seen_names:
                chosen.append(w)
                seen_names.add(w["name"])
                if len(chosen) >= 3:
                    break
    return chosen


def _rank_global_top_3(priors: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the globally top-3 workflows in survey rank order."""
    workflows = priors.get("workflows", [])
    sorted_global = sorted(workflows, key=lambda w: w.get("rank", 999))
    return sorted_global[:3]


def top_pain_workflows(user_cohort: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Public entry — return the 3 pain workflows whose prompt instructions
    should be injected into the verdict prompt for this user. Order matters
    (most relevant first)."""
    priors = _load_pain_priors()
    if not priors:
        return []
    ck = _cohort_key(user_cohort)
    if ck:
        chosen = _rank_cohort_top_3(ck, priors)
        if chosen:
            return chosen
    return _rank_global_top_3(priors)


# ---------------------------------------------------------------------------
# Decision style preference
# ---------------------------------------------------------------------------

def top_decision_style(user_cohort: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return canonical name of the cohort's most-preferred style; falls
    back to _global when cohort missing or absent from priors."""
    priors = _load_style_priors()
    if not priors:
        return None
    ck = _cohort_key(user_cohort)
    chosen: Optional[Dict[str, float]] = None
    if ck and ck in priors:
        chosen = priors[ck]
    else:
        chosen = priors.get("_global")
    if not chosen:
        return None
    # Pick the style with highest share.
    return max(chosen.items(), key=lambda kv: kv[1])[0]


# ---------------------------------------------------------------------------
# Prompt block builders
# ---------------------------------------------------------------------------

def build_pain_workflow_block(user_cohort: Optional[Dict[str, Any]]) -> str:
    """Compose the verdict-prompt section that injects the top-3 pain
    workflows + a TL;DR-first instruction (design § 6).

    Returns "" when priors are unavailable so callers can append blindly."""
    workflows = top_pain_workflows(user_cohort)
    if not workflows:
        return ""

    # Append TL;DR floor if not already in top-3.
    tldr_present = any(w["name"] == _TLDR_WORKFLOW_NAME for w in workflows)
    workflows_to_inject = list(workflows)
    if not tldr_present:
        priors = _load_pain_priors() or {}
        for w in priors.get("workflows", []):
            if w["name"] == _TLDR_WORKFLOW_NAME:
                workflows_to_inject.append(w)
                break

    lines = [
        "",
        "## Buyer pain-workflow constraints",
        "Apply these constraints to the verdict prose. They are survey-derived",
        "patterns from 400+ GCC buyers — phrasing the verdict in line with these",
        "makes the recommendation feel directly useful to the reader.",
        "",
    ]
    for i, w in enumerate(workflows_to_inject, start=1):
        lines.append(f"{i}. **{w['description']}** {w['prompt_instruction']}")
    lines.append("")
    return "\n".join(lines)


def build_decision_style_block(user_cohort: Optional[Dict[str, Any]]) -> str:
    """Compose the verdict-prompt section that hints the preferred style."""
    style_name = top_decision_style(user_cohort)
    if not style_name:
        return ""
    hint = DECISION_STYLE_HINTS.get(style_name, "")
    if not hint:
        return ""
    return (
        "\n## Buyer preferred verdict style\n"
        f"This buyer cohort prefers: **{style_name.replace('_', ' ')}**. {hint}\n"
    )

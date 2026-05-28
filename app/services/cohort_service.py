"""Cohort service: matches users to survey-derived demographic cohorts.

Loads `data/cohort_priors.json` once at startup. Hierarchical fallback for
cohorts with insufficient n. Returns None only when there are no priors at
all (degraded mode — missing or malformed file).

Public surface:
- `CohortService.match(demographics)` → CohortMatch | None
- `CohortService.seed_preferences(demographics)` → preferences dict
- `CohortService.get_display_profile(demographics)` → display dict | None
- `CohortService.should_seed(existing_prefs)` → bool
- `CohortService.get_cohort_modal_for_key(key)` → modal dict | None
- `get_cohort_service()` → process-wide singleton

The service is intentionally pure (no per-request IO). Loading happens once
at construction; all `match()` calls are dict lookups against in-memory data.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Path to the runtime priors JSON. Tests monkeypatch this attribute to load
# fixtures or to simulate the missing-file degraded mode.
PRIORS_PATH = Path(__file__).resolve().parents[2] / "data" / "cohort_priors.json"

# Treated as "missing" for cohort-key construction purposes — see _key_part().
SKIP_SENTINELS = frozenset(
    [
        "",
        "Prefer not to say",
        "أفضل عدم الإجابة",
        "أفضل عدم الإجابة\u00a0",
    ]
)


# ============================================================
# CohortMatch — what callers receive from match()
# ============================================================


@dataclass
class CohortMatch:
    cohort_key: str
    match_quality: str  # "exact" | "broadened_governorate" | "broadened_language" | "broadened_age" | "population"
    confidence: str  # "high" | "medium" | "low"
    n: int
    modal: dict = field(default_factory=dict)
    distribution: dict = field(default_factory=dict)
    persona_label: str = ""


# ============================================================
# CohortService
# ============================================================


class CohortService:
    """Loads cohort priors once at startup; serves match/seed/display lookups."""

    def __init__(self) -> None:
        self._cohorts = self._load_cohort_priors()

    # ------- Loading -------

    def _load_cohort_priors(self) -> dict:
        """Read PRIORS_PATH; degrade gracefully on missing or malformed file."""
        try:
            with open(PRIORS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(
                "cohort_priors.json missing at %s — service in degraded mode", PRIORS_PATH
            )
            return {"cohorts": {}, "fallback_aggregates": {}}
        except json.JSONDecodeError as exc:
            logger.error("cohort_priors.json malformed: %s", exc)
            return {"cohorts": {}, "fallback_aggregates": {}}

    # ------- Helpers -------

    @staticmethod
    def _key_part(value: Any) -> str:
        """Return cleaned string or empty if missing/skipped."""
        if value is None:
            return ""
        s = str(value).strip()
        if s in SKIP_SENTINELS:
            return ""
        return s

    def _lookup(self, key: str) -> Optional[dict]:
        """Try exact cohort key first, then fallback aggregates. None if missing."""
        if not key:
            return None
        c = self._cohorts.get("cohorts", {}).get(key)
        if c is not None:
            return c
        return self._cohorts.get("fallback_aggregates", {}).get(key)

    @staticmethod
    def _to_match(cohort_key: str, match_quality: str, cohort: dict) -> CohortMatch:
        return CohortMatch(
            cohort_key=cohort_key,
            match_quality=match_quality,
            confidence=cohort.get("confidence", "low"),
            n=cohort.get("n", 0),
            modal=cohort.get("modal", {}),
            distribution=cohort.get("distribution", {}),
            persona_label=cohort.get("persona_label", ""),
        )

    # ------- match() — primary API -------

    def match(self, demographics: dict) -> Optional[CohortMatch]:
        """Hierarchical fallback per design Section 3.3.

        Tries: full key → drop governorate → drop language → drop age →
               gender-only → population aggregate ('all').
        Returns None ONLY when no priors at all (degraded mode).
        """
        if demographics is None:
            demographics = {}

        age = self._key_part(demographics.get("age_group"))
        gender = self._key_part(demographics.get("gender"))
        governorate = self._key_part(demographics.get("governorate"))
        language = self._key_part(demographics.get("language"))

        # 1. Exact match (all four parts present)
        if age and gender and governorate and language:
            full_key = f"{age}|{gender}|{governorate}|{language}"
            cohort = self._lookup(full_key)
            if cohort and cohort.get("n", 0) >= 5:
                return self._to_match(full_key, "exact", cohort)

        # 2. Drop governorate (try age|gender|language)
        if age and gender and language:
            broadened = f"{age}|{gender}|{language}"
            cohort = self._lookup(broadened)
            if cohort and cohort.get("n", 0) >= 5:
                return self._to_match(broadened, "broadened_governorate", cohort)

        # 3. Drop language (try age|gender)
        if age and gender:
            broadened = f"{age}|{gender}"
            cohort = self._lookup(broadened)
            if cohort and cohort.get("n", 0) >= 5:
                return self._to_match(broadened, "broadened_language", cohort)

        # 4. Drop age (try gender alone)
        if gender:
            cohort = self._lookup(gender)
            if cohort and cohort.get("n", 0) >= 5:
                return self._to_match(gender, "broadened_age", cohort)

        # 5. Population aggregate
        all_cohort = self._cohorts.get("fallback_aggregates", {}).get("all")
        if all_cohort and all_cohort.get("n", 0) >= 1:
            return self._to_match("all", "population", all_cohort)

        # Truly empty priors → None (degraded mode)
        return None

    # ------- seed_preferences() — one-shot at demographics submission -------

    def seed_preferences(self, demographics: dict) -> dict:
        """Map cohort modal answers → existing 4 preference fields with source tags.

        See design Section 5.2. Lifestyle is left empty (no clean signal in surveys).
        Each populated field tagged source="inferred"; lifestyle source is None.
        """
        from datetime import datetime, timezone

        match = self.match(demographics)
        modal = match.modal if match else {}
        cohort_key = match.cohort_key if match else "all"

        priorities = _map_priorities_from_modal(modal)
        budget = _map_budget_from_spend(modal.get("spend_bracket"))
        brand_attitude = _map_brand_attitude_from_modal(modal)

        return {
            "priorities": priorities,
            "budget": budget,
            "lifestyle": [],
            "brand_attitude": brand_attitude,
            "_sources": {
                "priorities": "inferred",
                "budget": "inferred",
                "brand_attitude": "inferred",
                "lifestyle": None,
            },
            "_seeded_at": datetime.now(timezone.utc).isoformat(),
            "_cohort_key": cohort_key,
        }

    # ------- get_display_profile() — Profile UI card -------

    def get_display_profile(self, demographics: dict) -> Optional[dict]:
        """Return display dict for Profile card, or None for low/population matches.

        Per design Section 3.6: card only when confidence >= medium AND
        match_quality is not population.

        `governorate` (Optional[str]) echoes the user's own typed value from
        onboarding Step 04 so ProfileHeaderRow can render "{governorate} · GCC"
        on their own profile. None when the user skipped Step 04 or chose
        "Prefer not to say". Owner-only display: redaction invariant from the
        cohort skill restricts governorate from GPT prompts, not from the
        user's own profile UI.
        """
        match = self.match(demographics)
        if not match:
            return None
        if match.match_quality == "population":
            return None
        if match.confidence not in ("high", "medium"):
            return None
        gov_part = self._key_part((demographics or {}).get("governorate"))
        return {
            "persona_label": match.persona_label,
            "n": match.n,
            "modal": match.modal,
            "match_quality": match.match_quality,
            "confidence": match.confidence,
            "governorate": gov_part or None,
        }

    # ------- should_seed() — preference-seeding decision -------

    @staticmethod
    def should_seed(existing_prefs: Optional[dict]) -> bool:
        """True when prefs are empty OR all _sources are inferred (no user_stated).

        Legacy preferences without a `_sources` block are assumed user-stated
        (we don't overwrite legacy data we can't classify).
        """
        if not existing_prefs:
            return True
        sources = existing_prefs.get("_sources")
        if sources is None:
            # Legacy prefs with values but no _sources → assume user_stated, don't seed
            has_values = any(
                existing_prefs.get(k) for k in ("priorities", "budget", "brand_attitude", "lifestyle")
            )
            return not has_values
        # If any source is "user_stated" → do not seed
        for v in sources.values():
            if v == "user_stated":
                return False
        return True

    # ------- get_cohort_modal_for_key() — used by extraction prompt builder -------

    def get_cohort_modal_for_key(self, cohort_key: str) -> Optional[dict]:
        """Return the modal dict for a given cohort key (or None if not found)."""
        if not cohort_key:
            return None
        cohort = self._lookup(cohort_key)
        if not cohort:
            return None
        return cohort.get("modal")


# ============================================================
# Mapping helpers — cohort modal answers → existing preference enum values
# ============================================================

# Maps from cohort survey "deciding_factor" string → existing 8-priority enum
_PRIORITY_FROM_FACTOR: dict[str, str] = {
    "Quality": "quality_reliability",
    "Quality - Reliability": "quality_reliability",
    "Quality - reliability": "quality_reliability",
    "Price": "best_price",
    "Brand": "trusted_brand",
    "Value for money": "value_for_money",
    "Warranty or After-sales support": "warranty_support",
    "Warranty - Aftersales support": "warranty_support",
    "Warranty or Aftersales support": "warranty_support",
    "Design": "design_aesthetics",
    "Trusted opinions": "trusted_brand",
    "Recommendation from someone I trust": "trusted_brand",
    "AI suggestion": "value_for_money",
    "Easy information": "value_for_money",
    "Ease of use": "value_for_money",
}


def _map_priorities_from_modal(modal: dict) -> list[str]:
    """Pull top 1-2 deciding factors and map to existing priority enum values."""
    candidates = []
    for k in ("top_deciding_factor", "second_deciding_factor"):
        v = modal.get(k)
        if v:
            mapped = _PRIORITY_FROM_FACTOR.get(v)
            if mapped and mapped not in candidates:
                candidates.append(mapped)
    return candidates[:2]  # at most 2 from cohort signal


def _map_budget_from_spend(spend_bracket: Optional[str]) -> Optional[str]:
    """Map cohort spend bracket → existing budget tier (budget/mid/premium).

    Tiers per design 5.2 + scoring_service price tiers:
      <25 BHD               → budget
      25-50 BHD, 50-100 BHD → mid
      100-250 BHD, 250+ BHD → premium
    """
    if not spend_bracket:
        return None
    s = spend_bracket.strip()
    if s in ("<25 BHD", "Less than 25 BHD"):
        return "budget"
    if s in ("25-50 BHD", "50-100 BHD"):
        return "mid"
    if s in ("100-250 BHD", "250+ BHD"):
        return "premium"
    return None


def _map_brand_attitude_from_modal(modal: dict) -> str:
    """Infer brand attitude from 'if info incomplete' modal answer.

    "Choose the brand I know" → trust_known_brands (label aligned to behavior)
    Anything else → best_of_both (a sensible neutral default)
    """
    if_incomplete = modal.get("if_info_incomplete", "") or ""
    if "Choose the brand" in if_incomplete:
        return "trust_known_brands"
    return "best_of_both"


# ============================================================
# Singleton accessor
# ============================================================

_service_singleton: Optional[CohortService] = None


def get_cohort_service() -> CohortService:
    """Return the process-wide CohortService (lazy-initialized)."""
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = CohortService()
    return _service_singleton

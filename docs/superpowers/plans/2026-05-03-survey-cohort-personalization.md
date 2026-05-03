# Survey-Driven Cohort Personalization — Implementation Plan

> **For Claude:** This plan is designed for parallel execution by a 4-Opus-agent team via `TeamCreate` (per Section 7 of the design doc). DO NOT execute single-threaded with `superpowers:executing-plans`. Spawn the team described in the "Team Spawning Instructions" section, hand each agent their assigned tasks below, and enforce the cross-QA matrix + disassembly gate before allowing any agent to terminate.

**Goal:** Use ~400 Fillout survey responses to bootstrap personalization for new/anonymous users via (B) verdict-prompt enrichment and (C) one-shot preference seeding from cohort modal answers, surfaced in the Profile screen.

**Architecture:** Build-time ETL (CSV → cohort_priors.json) + runtime cohort matching service + thin integration into existing `_build_preferences_prompt()` and a new post-first-comparison demographics bottom sheet. Zero per-request API cost. All cohort lookups in-memory.

**Tech Stack:** Python 3.12 / FastAPI / Supabase JSONB / Redis (existing) / React Native + Expo / Chart.js (CDN) / pytest / Jest.

**Design doc:** `docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md`

**Coverage target:** 80% line coverage on new code (`scripts/build_cohorts.py`, `app/services/cohort_service.py`, demographics endpoint), 90% on cohort matching algorithm specifically.

---

## Pre-Flight (manual, ONE-TIME — Ahmed runs these first)

Before spawning the team:

- [ ] **Move the survey CSVs into the repo:**
      ```
      mkdir -p data/surveys
      mv "C:/Users/SynAckITPC/Downloads/Fillout ENG results (2).csv" data/surveys/Fillout_ENG_results.csv
      mv "C:/Users/SynAckITPC/Downloads/Fillout arab results (2).csv" data/surveys/Fillout_arab_results.csv
      ```
- [ ] **Decide commit policy for raw CSVs.** If they contain emails/phones (they do — last 2 columns), gitignore them and only commit `data/cohort_priors.json`:
      ```
      echo "data/surveys/*.csv" >> .gitignore
      ```
- [ ] **Confirm Supabase project access** for applying `migrations/013_demographics_cohort.sql` post-merge (manual via SQL Editor, per CLAUDE.md gotcha).
- [ ] **Verify `ENABLE_COHORT_PERSONALIZATION` env var slot exists in Railway.** Default value: `false`. Will be flipped after Phase 1 internal QA.

---

## Team Spawning Instructions

After pre-flight, spawn 4 Opus agents in a single `TeamCreate` call with `bypassPermissions` mode. Hand each agent their numbered task block from the sections below + the design doc path.

**Common preamble for all agents:**

> Read `docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md` and `CLAUDE.md` before doing anything. You are part of a 4-agent team. Your assigned tasks are in `docs/superpowers/plans/2026-05-03-survey-cohort-personalization.md` under your agent name. Follow TDD strictly — write the failing test FIRST, run it to confirm it fails, then implement the minimal code to make it pass, then commit. Do not skip steps. Do not mark tasks complete with failing tests or partial implementation. Idle behavior: write more red-green tests for your area until QA returns or you receive a new task. NEVER idle silently. Cross-QA is mandatory before disassembly — see Section 7 of the design doc and the "Cross-QA + Disassembly Gate" section of this plan.

**Per-agent assignments:** see `Section A` (backend-cohort), `Section B` (frontend-cohort), `Section C` (test-cohort), `Section D` (qa-cohort).

---

# SECTION A — backend-cohort tasks

**Owner files:**
- `scripts/build_cohorts.py`
- `data/cohort_priors.json` (generated artifact)
- `app/services/cohort_service.py`
- `app/api/auth_routes.py` (additions: `/demographics`, `/cohort-profile`, `/preferences` extension)
- `app/services/extraction_service.py` (cohort block in `_build_preferences_prompt`)
- `app/services/database_service.py` (helpers: get/save demographics, source-tag-aware preference save)
- `migrations/013_demographics_cohort.sql`
- `app/api/admin_routes.py` (cohort metrics endpoints)
- `app/static/admin/cohort.html`

**Coverage target:** 80% on `cohort_service.py` and `build_cohorts.py`. Extraction prompt block needs snapshot test (handled by test-cohort).

## A.1 — Migration

### Task A.1.1: Write the migration SQL

**File:** Create `migrations/013_demographics_cohort.sql`

**Step 1:** Write the file with the exact contents from design doc Section 6.1:

```sql
-- Migration 013: Demographics + cohort match cache + metric views
-- Apply manually via Supabase SQL Editor

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS demographics_profile JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_at TIMESTAMPTZ DEFAULT NULL;

-- (RLS already enabled on users table per migration 010; no new policies needed
--  because demographics_profile lives on the same row that's already protected.)

CREATE OR REPLACE VIEW vw_cohort_match_rate AS
SELECT
  date_trunc('day', updated_at) AS day,
  COUNT(*) FILTER (WHERE demographics_profile->'cohort_match'->>'match_quality'
                   IN ('exact','broadened_governorate','broadened_language')) AS strong_matches,
  COUNT(*) FILTER (WHERE demographics_profile IS NOT NULL) AS total_with_demographics,
  COUNT(*) AS total_users
FROM public.users
GROUP BY day;

CREATE OR REPLACE VIEW vw_cohort_persona_distribution AS
SELECT
  demographics_profile->'cohort_match'->>'persona_label' AS persona,
  COUNT(*) AS user_count
FROM public.users
WHERE demographics_profile IS NOT NULL
GROUP BY persona
ORDER BY user_count DESC;

CREATE OR REPLACE VIEW vw_cohort_feedback_lift AS
SELECT
  cf.rating,
  ce.event_data->>'cohort_injected' AS cohort_injected,
  COUNT(*) AS n,
  AVG(cf.rating) AS avg_rating
FROM comparison_feedback cf
JOIN user_events ce ON ce.comparison_id = cf.comparison_id
GROUP BY cf.rating, cohort_injected;
```

**Step 2:** Update CLAUDE.md `### Migrations` section to add `013_demographics_cohort.sql — PENDING. demographics_profile column on users + dismissal tracking + 3 metric views.`

**Step 3:** Commit:
```bash
git add migrations/013_demographics_cohort.sql CLAUDE.md
git commit -m "migration: 013 demographics_cohort + metric views (manual apply)"
```

---

## A.2 — ETL Script

### Task A.2.1: Write failing test for Arabic-to-English value normalization

**File:** Create `tests/test_build_cohorts.py`

**Step 1:** Write the failing test:
```python
# tests/test_build_cohorts.py
import pytest
from scripts.build_cohorts import normalize_value, ARABIC_TO_ENGLISH

def test_normalize_known_arabic_value_returns_english():
    assert normalize_value("الجودة", field="deciding_factor") == "Quality"
    assert normalize_value("السعر", field="deciding_factor") == "Price"
    assert normalize_value("أنثى", field="gender") == "Female"
    assert normalize_value("محافظة العاصمة", field="governorate") == "Capital"

def test_normalize_english_passes_through():
    assert normalize_value("Quality", field="deciding_factor") == "Quality"

def test_normalize_unknown_arabic_raises():
    with pytest.raises(ValueError, match="unknown.*deciding_factor.*xyz"):
        normalize_value("XYZ_غير_موجود", field="deciding_factor")
```

**Step 2:** Run: `pytest tests/test_build_cohorts.py::test_normalize_known_arabic_value_returns_english -v`
**Expected:** FAIL with `ImportError: cannot import name 'normalize_value' from 'scripts.build_cohorts'`

### Task A.2.2: Implement minimal `normalize_value` + `ARABIC_TO_ENGLISH`

**File:** Create `scripts/build_cohorts.py`

**Step 3:** Write minimal implementation. Build the normalization mapping from inspection of both CSVs (Appendix A of design doc is a starting point — expand as needed by reading the actual CSV values):

```python
"""Build data/cohort_priors.json from Fillout survey CSVs.

One-shot ETL: reads English + Arabic CSV exports, normalizes Arabic values
to English, groups by cohort key (age|gender|governorate|language), and
writes per-cohort modal answers + distributions plus fallback aggregates.

Run: python -m scripts.build_cohorts
"""
from __future__ import annotations
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ARABIC_TO_ENGLISH = {
    # categories
    "إلكترونيات": "Electronics",
    "الكترونيات": "Electronics",
    "جهاز منزلي": "Home appliance",
    "اشتراك أو خدمة": "Subscription or Service",
    "منتج أزياء - تجميل": "Fashion or Beauty item",
    "عطور": "Fragrance",
    "منتج صحي": "Health product",
    # deciding factors
    "الجودة": "Quality",
    "السعر": "Price",
    "العلامة التجارية": "Brand",
    "القيمة مقابل السعر": "Value for money",
    "الضمان أو خدمة ما بعد البيع": "Warranty or After-sales support",
    "الشكل او التصميم": "Design",
    # gender
    "أنثى": "Female",
    "ذكر": "Male",
    # governorate
    "محافظة العاصمة": "Capital",
    "المحافظة الشمالية": "Northern",
    "محافظة المحرق": "Muharraq",
    "المحافظة الجنوبية": "Southern",
    # identity
    "بحريني - بحرينية": "Bahraini",
    # spend brackets
    "أقل من 25 دينار بحريني": "<25 BHD",
    "من 25 إلى أقل من 50 دينار بحريني": "25-50 BHD",
    "من 50 إلى أقل من 100 دينار بحريني": "50-100 BHD",
    "من 100 إلى أقل من 250 دينار بحريني": "100-250 BHD",
    # language
    "العربية": "Arabic",
    "الإنجليزية": "English",
    "كلتاهما بالتساوي": "Both equally",
    # — extend as ETL fails on unknown values during real data run —
}


def normalize_value(value: str, field: str) -> str:
    """Map Arabic value to English, pass English through, FAIL on unknown."""
    if value in ARABIC_TO_ENGLISH:
        return ARABIC_TO_ENGLISH[value]
    # heuristic: if any non-ASCII present, treat as unknown Arabic
    if any(ord(c) > 127 for c in value):
        raise ValueError(f"unknown {field} value: {value!r} — add to ARABIC_TO_ENGLISH")
    return value
```

**Step 4:** Run tests: `pytest tests/test_build_cohorts.py -v`
**Expected:** All 3 normalization tests PASS

**Step 5:** Commit:
```bash
git add scripts/build_cohorts.py tests/test_build_cohorts.py
git commit -m "feat(cohort): normalize Arabic values to English with fail-loud unknowns"
```

### Task A.2.3: Test for row dropping rules (consent, finished, multi-skip)

**Step 1:** Add failing test to `tests/test_build_cohorts.py`:
```python
from scripts.build_cohorts import should_drop_row

def test_drop_row_no_consent():
    row = {"I agree and want to continue": "false", "Status": "finished",
           "What is your age group?": "25-34"}
    assert should_drop_row(row) is True

def test_drop_row_unfinished():
    row = {"I agree and want to continue": "true", "Status": "in_progress",
           "What is your age group?": "25-34"}
    assert should_drop_row(row) is True

def test_drop_row_all_cohort_keys_empty():
    row = {"I agree and want to continue": "true", "Status": "finished",
           "What is your age group?": "", "What is your gender?": "",
           "Which governorate do you mainly live in?": "",
           "Which language do you usually use when searching for products or services?": ""}
    assert should_drop_row(row) is True

def test_keep_complete_row():
    row = {"I agree and want to continue": "true", "Status": "finished",
           "What is your age group?": "25-34", "What is your gender?": "Female",
           "Which governorate do you mainly live in?": "Northern Governorate",
           "Which language do you usually use when searching for products or services?": "English"}
    assert should_drop_row(row) is False
```

**Step 2:** Run: `pytest tests/test_build_cohorts.py::test_drop_row_no_consent -v` → FAIL

**Step 3:** Implement `should_drop_row()`:
```python
COHORT_KEY_FIELDS_EN = [
    "What is your age group?",
    "What is your gender?",
    "Which governorate do you mainly live in?",
    "Which language do you usually use when searching for products or services?",
]
# Arabic header equivalents (look them up from the Arabic CSV header)
COHORT_KEY_FIELDS_AR = [
    "ما هي فئتك العمرية؟",
    "ما هو جنسك؟",
    "في أي محافظة تعيش بشكل رئيسي؟",
    "ما اللغة التي تستخدمها غالباً عند البحث عن المنتجات أو الخدمات؟",
]


def _get_cohort_field(row: dict, idx: int) -> str:
    en = COHORT_KEY_FIELDS_EN[idx]
    ar = COHORT_KEY_FIELDS_AR[idx]
    return (row.get(en) or row.get(ar) or "").strip()


def should_drop_row(row: dict) -> bool:
    consent = (row.get(" I agree and want to continue") or row.get("أوافق وأرغب في المتابعة") or "").strip().lower()
    if consent != "true":
        return True
    if (row.get("Status") or "").strip().lower() != "finished":
        return True
    cohort_values = [_get_cohort_field(row, i) for i in range(4)]
    skip_phrases = {"", "Prefer not to say", "أفضل عدم الإجابة"}
    if all(v in skip_phrases for v in cohort_values):
        return True
    return False
```

**Step 4:** Run tests → all pass

**Step 5:** Commit:
```bash
git add scripts/build_cohorts.py tests/test_build_cohorts.py
git commit -m "feat(cohort): drop incomplete/no-consent rows during ETL"
```

### Task A.2.4: Test for cohort grouping + modal computation

**Step 1:** Add failing test:
```python
from scripts.build_cohorts import build_cohort_stats

def test_build_cohort_stats_computes_modal():
    rows = [
        {"cohort_key": "25-34|Female|Northern|Arabic",
         "deciding_factor": ["Quality"], "spend_bracket": "25-50 BHD",
         "assistance_style": "Show me 2 or 3 suitable options"},
        {"cohort_key": "25-34|Female|Northern|Arabic",
         "deciding_factor": ["Quality", "Price"], "spend_bracket": "25-50 BHD",
         "assistance_style": "Show me 2 or 3 suitable options"},
        {"cohort_key": "25-34|Female|Northern|Arabic",
         "deciding_factor": ["Price"], "spend_bracket": "<25 BHD",
         "assistance_style": "All details"},
    ]
    stats = build_cohort_stats(rows)
    cohort = stats["cohorts"]["25-34|Female|Northern|Arabic"]
    assert cohort["n"] == 3
    assert cohort["confidence"] == "low"  # 3 < 5
    assert cohort["modal"]["top_deciding_factor"] == "Quality"
    assert cohort["modal"]["preferred_assistance_style"] == "Show me 2 or 3 suitable options"
```

**Step 2:** Run → FAIL

**Step 3:** Implement `build_cohort_stats()` (~60 lines: group, count, mode, confidence flag, fallback aggregates). See design doc Section 2.4 for output schema.

**Step 4:** Run all tests → pass

**Step 5:** Commit `feat(cohort): compute per-cohort modal + confidence`

### Task A.2.5: Test for fallback aggregate generation

**Step 1:** Add failing test that asserts `fallback_aggregates` keys exist for shorter prefixes (e.g. `"25-34|Female|Arabic"`, `"25-34|Female"`, `"25-34"`, `"all"`).

**Step 2:** Run → FAIL.

**Step 3:** Implement fallback aggregate computation in `build_cohort_stats()`.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(cohort): generate fallback aggregates for hierarchical match`.

### Task A.2.6: Test for persona_label generation

**Step 1:** Add failing test:
```python
from scripts.build_cohorts import generate_persona_label

def test_persona_quality_first_focused():
    modal = {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD",
             "preferred_assistance_style": "Show me 2 or 3 suitable options"}
    assert generate_persona_label(modal) == "Quality-first focused buyer"

def test_persona_budget_value_seeker():
    modal = {"top_deciding_factor": "Price", "spend_bracket": "<25 BHD",
             "preferred_assistance_style": "Show me 2 or 3 suitable options"}
    assert generate_persona_label(modal) == "Budget-conscious value seeker"

def test_persona_premium_brand_loyal():
    modal = {"top_deciding_factor": "Brand", "spend_bracket": "100-250 BHD",
             "preferred_assistance_style": "Suggest best with reason"}
    assert generate_persona_label(modal) == "Premium brand-loyal buyer"
```

**Step 2:** Run → FAIL

**Step 3:** Implement rule table (~8-10 labels covering the modal-answer space). Default fallback: `"Balanced shopper"`.

**Step 4:** Run → pass

**Step 5:** Commit `feat(cohort): persona labels from modal answers`

### Task A.2.7: Wire ETL end-to-end + write `cohort_priors.json`

**Step 1:** Add `main()` function that:
- Reads both CSVs from `data/surveys/`
- Filters via `should_drop_row`
- Normalizes each cohort-key field via `normalize_value`
- Splits multi-select fields on commas
- Calls `build_cohort_stats`
- Writes atomically to `data/cohort_priors.json` (`.tmp` then `os.replace`)

**Step 2:** Add integration test in `tests/test_build_cohorts.py`:
```python
def test_main_writes_valid_json(tmp_path, monkeypatch):
    # use a 5-row fixture CSV; assert output JSON has expected schema
    ...
```

**Step 3:** Run: `python -m scripts.build_cohorts` against the real CSVs.
**Expected:** writes `data/cohort_priors.json`. If it raises on unknown Arabic value, expand `ARABIC_TO_ENGLISH` and re-run. Repeat until clean.

**Step 4:** Inspect output manually: `python -c "import json; d=json.load(open('data/cohort_priors.json')); print('total:', d['total_responses'], 'cohorts:', len(d['cohorts']))"`. Sanity check: total_responses around 350-400, cohorts count between 30-60.

**Step 5:** Commit:
```bash
git add scripts/build_cohorts.py tests/test_build_cohorts.py data/cohort_priors.json
git commit -m "feat(cohort): generate cohort_priors.json from survey CSVs"
```

---

## A.3 — `cohort_service.py`

### Task A.3.1: Failing test for service initialization + JSON load

**File:** Create `tests/test_cohort_service.py`

```python
import pytest
from app.services.cohort_service import CohortService, get_cohort_service

def test_service_loads_priors_on_init():
    svc = CohortService()
    assert svc._cohorts is not None
    assert "cohorts" in svc._cohorts
    assert "fallback_aggregates" in svc._cohorts

def test_get_cohort_service_returns_singleton():
    a = get_cohort_service()
    b = get_cohort_service()
    assert a is b
```

**Step 2:** Run → FAIL (`ImportError`)

**Step 3:** Create `app/services/cohort_service.py`:
```python
"""Cohort service: matches users to survey-derived demographic cohorts.

Loads data/cohort_priors.json once at startup. Hierarchical fallback for
cohorts with insufficient n. Returns None only when EVERY field is missing.
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
PRIORS_PATH = Path(__file__).resolve().parents[2] / "data" / "cohort_priors.json"


@dataclass
class CohortMatch:
    cohort_key: str
    match_quality: str  # "exact" | "broadened_*" | "population"
    confidence: str     # "high" | "medium" | "low"
    n: int
    modal: dict
    distribution: dict
    persona_label: str


class CohortService:
    def __init__(self):
        self._cohorts = self._load_cohort_priors()

    def _load_cohort_priors(self) -> dict:
        try:
            with open(PRIORS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("cohort_priors.json missing — service in degraded mode")
            return {"cohorts": {}, "fallback_aggregates": {"all": None}}
        except json.JSONDecodeError as e:
            logger.error("cohort_priors.json malformed: %s", e)
            return {"cohorts": {}, "fallback_aggregates": {"all": None}}


_service_singleton: Optional[CohortService] = None


def get_cohort_service() -> CohortService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = CohortService()
    return _service_singleton
```

**Step 4:** Run → pass

**Step 5:** Commit `feat(cohort): cohort service singleton + JSON load`

### Task A.3.2: Failing test for `match()` exact case

**Step 1:**
```python
def test_match_exact_returns_cohort(monkeypatch):
    fake_data = {
        "cohorts": {
            "25-34|Female|Northern|Arabic": {
                "n": 23, "confidence": "high",
                "modal": {"top_deciding_factor": "Quality"},
                "distribution": {}, "persona_label": "Quality-first focused buyer"
            }
        },
        "fallback_aggregates": {"all": {"n": 397, "confidence": "high",
                                         "modal": {}, "distribution": {},
                                         "persona_label": "Balanced shopper"}}
    }
    svc = CohortService()
    svc._cohorts = fake_data
    match = svc.match({"age_group": "25-34", "gender": "Female",
                       "governorate": "Northern", "language": "Arabic"})
    assert match.match_quality == "exact"
    assert match.cohort_key == "25-34|Female|Northern|Arabic"
    assert match.persona_label == "Quality-first focused buyer"
```

**Step 2:** Run → FAIL

**Step 3:** Implement `match()` with exact-key lookup first.

**Step 4:** Pass

**Step 5:** Commit `feat(cohort): exact-key match`

### Task A.3.3-A.3.6: Tests + impl for fallback chain

Each step in the fallback ladder gets its own failing test → impl → commit:
- A.3.3: drop governorate fallback (`broadened_governorate`)
- A.3.4: drop language fallback (`broadened_language`)
- A.3.5: drop age fallback (`broadened_age`)
- A.3.6: population fallback when nothing else matches

For each: failing test → run → impl → run → commit.

### Task A.3.7: Test for "Prefer not to say" handling

```python
def test_match_skips_prefer_not_to_say():
    svc = CohortService()
    # ...same fake_data with the broadened_governorate entry...
    match = svc.match({"age_group": "25-34", "gender": "Female",
                       "governorate": "Prefer not to say", "language": "Arabic"})
    assert match.match_quality == "broadened_governorate"
```

Implement: treat `"Prefer not to say"` and empty string as missing.

### Task A.3.8: Test + impl for `seed_preferences()`

```python
def test_seed_preferences_maps_modal_to_existing_fields():
    svc = CohortService()
    svc._cohorts = {...}  # fixture with known modal
    seeded = svc.seed_preferences({"age_group": "25-34", "gender": "Female",
                                   "governorate": "Northern", "language": "Arabic"})
    assert seeded["priorities"] == ["quality_reliability", "best_price"]
    assert seeded["budget"] == "mid"
    assert seeded["brand_attitude"] in ("trust_known_brands", "open_to_new")
    assert seeded["lifestyle"] == []
    assert seeded["_sources"]["priorities"] == "inferred"
    assert seeded["_sources"]["lifestyle"] is None
    assert "_seeded_at" in seeded
    assert "_cohort_key" in seeded
```

**Implement:** mapping per design doc Section 5.2.

**Commit:** `feat(cohort): seed preferences from cohort modal with source tags`

### Task A.3.9: Test + impl for `get_display_profile()`

Returns dict for Profile UI when `confidence ≥ "medium"`, else `None`.

### Task A.3.10: Performance assertion test

```python
def test_match_is_in_memory_no_io(monkeypatch):
    svc = get_cohort_service()  # singleton, already loaded
    open_called = []
    real_open = __builtins__["open"] if isinstance(__builtins__, dict) else open
    def spy_open(*a, **kw):
        open_called.append(a)
        return real_open(*a, **kw)
    monkeypatch.setattr("builtins.open", spy_open)
    for _ in range(100):
        svc.match({"age_group": "25-34", "gender": "Female",
                   "governorate": "Northern", "language": "Arabic"})
    assert open_called == [], "match() must be pure in-memory"
```

**Commit:** `test(cohort): match is in-memory (no per-request IO)`

---

## A.4 — Auth route additions

### Task A.4.1: Failing test for `PUT /api/v1/auth/demographics`

**File:** test added to `tests/test_auth_demographics.py` (created by test-cohort, but backend-cohort writes the route to make tests pass).

```python
def test_put_demographics_stores_and_seeds(client, auth_token, monkeypatch):
    response = client.put(
        "/api/v1/auth/demographics",
        json={"age_group": "25-34", "gender": "Female",
              "governorate": "Northern", "language": "Arabic"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["cohort_match"]["match_quality"] in (
        "exact", "broadened_governorate", "broadened_language", "population"
    )
    # Verify users.demographics_profile was written
    # Verify users.preferences was seeded if previously empty
```

**Step 2:** Run → FAIL (route doesn't exist)

**Step 3:** Add to `app/api/auth_routes.py`:

```python
from pydantic import BaseModel
from typing import Optional
from app.services.cohort_service import get_cohort_service

class DemographicsBody(BaseModel):
    age_group: Optional[str] = None
    gender: Optional[str] = None
    governorate: Optional[str] = None
    # language + country auto-detected; clients may override but typically don't
    language: Optional[str] = None
    country: Optional[str] = None


@router.put("/demographics")
@limiter.limit("5/minute")
async def save_demographics(
    request: Request,
    body: DemographicsBody,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    payload = body.model_dump(exclude_none=False)

    # Auto-fill language from Accept-Language if missing
    if not payload.get("language"):
        accept = request.headers.get("accept-language", "")
        payload["language"] = "Arabic" if accept.startswith("ar") else "English"

    # Auto-fill country from CF-IPCountry header (Cloudflare) if missing
    if not payload.get("country"):
        cf_country = request.headers.get("cf-ipcountry", "")
        payload["country"] = "Bahrain" if cf_country == "BH" else (cf_country or "Bahrain")

    cohort_svc = get_cohort_service()
    match = cohort_svc.match(payload)

    profile = {
        **payload,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "cohort_match": (
            {"cohort_key": match.cohort_key, "match_quality": match.match_quality,
             "confidence": match.confidence, "n": match.n,
             "persona_label": match.persona_label}
            if match else None
        ),
    }

    await save_user_demographics(user_id, profile)

    # C: seed preferences if user has none or all are inferred
    existing_prefs = await get_user_preferences(user_id)
    if cohort_svc.should_seed(existing_prefs):
        seeded = cohort_svc.seed_preferences(payload)
        await save_user_preferences(user_id, seeded, merge_inferred_only=True)

    return {"success": True, "cohort_match": profile["cohort_match"]}
```

Add helpers in `app/services/database_service.py`: `save_user_demographics(user_id, profile)`.

**Step 4:** Run test → pass.

**Step 5:** Commit `feat(auth): PUT /demographics stores profile + seeds preferences`.

### Task A.4.2: Failing test for `GET /api/v1/auth/cohort-profile`

```python
def test_get_cohort_profile_returns_display_profile(client, auth_token):
    # set up user with demographics_profile
    response = client.get("/api/v1/auth/cohort-profile",
                          headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    data = response.json()
    if data.get("display"):
        assert "persona_label" in data["display"]
        assert "n" in data["display"]
```

**Implement** the GET endpoint. Returns `{"display": null}` if confidence < "medium".

**Commit:** `feat(auth): GET /cohort-profile returns display data for Profile card`.

### Task A.4.3: Failing test for `PUT /preferences` source-flip on edit

```python
def test_put_preferences_flips_source_to_user_stated(client, auth_token):
    # User has inferred preferences seeded
    # User edits the priorities field
    # After PUT, the _sources.priorities should be "user_stated"
    ...
```

**Implement** in existing `PUT /preferences`: detect which fields changed vs the existing record; flip those `_sources` entries to `"user_stated"`.

**Commit:** `feat(auth): edits to seeded preferences flip source to user_stated`.

### Task A.4.4: Rate limit + auth checks regression

Add to `tests/test_security_regression.py`:
- `PUT /demographics` requires auth (401 without token)
- `PUT /demographics` rate limited 5/min
- `GET /cohort-profile` requires auth
- Other-user-id cannot read/write your demographics_profile (RLS)

**Commit:** `test(security): regression for demographics endpoint auth + RLS`.

---

## A.5 — Verdict prompt enrichment (B integration)

### Task A.5.1: Failing snapshot test for prompt block injection

**File:** `tests/test_extraction_cohort_prompt.py` (created by test-cohort).

```python
def test_cohort_block_injected_for_strong_match():
    user_demographics_profile = {
        "country": "Bahrain", "language": "Arabic", "governorate": "Northern",
        "cohort_match": {
            "cohort_key": "25-34|Female|Northern|Arabic",
            "match_quality": "exact", "confidence": "high", "n": 23,
            "persona_label": "Quality-first focused buyer"
        }
    }
    prompt = _build_preferences_prompt(
        explicit_prefs={...}, behavioral={...},
        demographics_profile=user_demographics_profile
    )
    assert "COHORT-LEVEL PRIORS" in prompt
    assert "USER CONTEXT: Country=Bahrain, Language=Arabic, Region=Northern" in prompt
    assert "POPULATION STATISTICS" in prompt
    # Privacy: NO raw demographics in prompt
    assert "25-34" not in prompt  # age leaked
    assert "Female" not in prompt  # gender leaked

def test_cohort_block_skipped_for_population_match():
    user_demographics_profile = {
        "country": "Bahrain", "language": "English",
        "cohort_match": {"match_quality": "population", "confidence": "high", "n": 397,
                         "persona_label": "Balanced shopper"}
    }
    prompt = _build_preferences_prompt(..., demographics_profile=user_demographics_profile)
    assert "COHORT-LEVEL PRIORS" not in prompt
```

### Task A.5.2: Implement the cohort block in `_build_preferences_prompt()`

**File:** `app/services/extraction_service.py`

Locate `_build_preferences_prompt()`. Add a new section appended AFTER explicit + behavioral blocks. Pull cohort_priors.json modal from `cohort_service.get_cohort_modal_for_key(cohort_key)` (add a small accessor method). Build the block per design doc Section 4.2. Trigger condition per Section 4.1.

**Run snapshot tests → pass.**

**Commit:** `feat(extraction): inject cohort priors into verdict prompt (B)`.

### Task A.5.3: Plumb `demographics_profile` through the call chain

`StructuredComparisonService.compare_from_text(...)` already accepts `user_id`. Fetch the user's `demographics_profile` once at the start, pass to `_build_preferences_prompt()`. Cache for the request lifetime.

Test: integration test that a comparison for a user with cohort match has the block in the GPT call (mock OpenAI, assert on prompt arg).

**Commit:** `feat(comparison): pass demographics_profile to prompt builder`.

### Task A.5.4: Feature flag `ENABLE_COHORT_PERSONALIZATION`

Read from env. When `false`: skip both B injection AND C seeding. Add tests for both states.

**Commit:** `feat(cohort): feature flag for staged rollout`.

---

## A.6 — Admin metrics endpoints

### Task A.6.1: Test + impl `GET /api/v1/admin/cohort/metrics`

Reads from `vw_cohort_match_rate` + `vw_cohort_persona_distribution`. Returns JSON. Auth via existing `X-Admin-Key`. Rate limited 30/min (existing pattern).

### Task A.6.2: Test + impl `GET /api/v1/admin/cohort/feedback`

Reads from `vw_cohort_feedback_lift`. Returns ratings stratified by `cohort_injected` (boolean event_data field).

### Task A.6.3: Test + impl `GET /api/v1/admin/cohort/retention`

Computes 7-day return rate from `user_events` table, stratified by whether the user has demographics_profile.

### Task A.6.4: Static HTML dashboard

**File:** `app/static/admin/cohort.html`

Single page. Vanilla JS (no build step). Chart.js via CDN. Fetches the 3 admin endpoints. Renders 4 visualizations per design doc Section 6.5. Auth: `prompt('X-Admin-Key:')` on first load, store in `sessionStorage`.

Add static file mounting to `app/main.py` if not already present.

**Commit:** `feat(admin): cohort metrics dashboard at /admin/cohort.html`.

### Task A.6.5: Wire `cohort_injected` event tracking

In `StructuredComparisonService.compare_from_text(...)`, after the verdict GPT call, fire-and-forget log to `user_events` with `event_type="comparison_completed"` and `event_data={"cohort_injected": <bool>}`. Required for `vw_cohort_feedback_lift` to work.

**Commit:** `feat(events): track cohort_injected on comparison events`.

---

## A.7 — Documentation updates

### Task A.7.1: Update CLAUDE.md

Add to architecture section: brief description of cohort_service + survey-driven personalization. Update migrations list. Add `ENABLE_COHORT_PERSONALIZATION` to env vars.

### Task A.7.2: Update MEMORY.md

Brief Session 41 entry (deferring details to actual session log).

**Commit:** `docs: cohort personalization in CLAUDE.md + MEMORY.md`.

---

# SECTION B — frontend-cohort tasks

**Owner files:**
- `SmartCompareApp/src/components/DemographicsBottomSheet.tsx`
- `SmartCompareApp/src/screens/ProfileScreen.tsx` (StyleProfileCard add)
- `SmartCompareApp/src/screens/EditPreferencesModal.tsx` (or extend existing PreferencesScreen)
- `SmartCompareApp/src/services/api.ts` (new `putDemographics()`, `getCohortProfile()`)
- `SmartCompareApp/src/services/preferences.ts` (dismissal cooldown state)
- `SmartCompareApp/src/i18n/en.json` + `ar.json` (new keys)

**Coverage target:** 80% on bottom sheet component logic + dismissal state.

**Blocked-by:** A.4.1 (PUT /demographics schema), A.4.2 (GET /cohort-profile schema). Frontend can stub the API calls and start UI work immediately.

## B.1 — i18n keys

### Task B.1.1: Add demographic bottom sheet copy

**File:** `SmartCompareApp/src/i18n/en.json` and `src/i18n/ar.json`

Add keys: `demographics.title`, `demographics.subtitle`, `demographics.age`, `demographics.gender`, `demographics.governorate`, `demographics.preferNotToSay`, `demographics.skip`, `demographics.save`, `profile.styleProfile.title`, `profile.styleProfile.basedOn`, `profile.styleProfile.editButton`, `profile.styleProfile.banner`.

**Commit:** `i18n: add demographics + style profile copy (en + ar)`.

## B.2 — API client

### Task B.2.1: Test + impl `putDemographics()` in `api.ts`

```typescript
export async function putDemographics(payload: {
  age_group?: string; gender?: string; governorate?: string;
  language?: string; country?: string;
}): Promise<{ success: boolean; cohort_match: CohortMatch | null }> {...}
```

### Task B.2.2: Test + impl `getCohortProfile()` in `api.ts`

```typescript
export async function getCohortProfile(): Promise<{ display: DisplayProfile | null }> {...}
```

**Commit:** `feat(api): demographics + cohort-profile client methods`.

## B.3 — Bottom sheet component

### Task B.3.1: Failing test for component renders 3 fields

**File:** `SmartCompareApp/__tests__/DemographicsBottomSheet.test.tsx`

```typescript
test("renders age, gender, governorate fields with Prefer not to say option", () => {
  const { getByText } = render(<DemographicsBottomSheet visible onSubmit={jest.fn()} onSkip={jest.fn()} />);
  expect(getByText(/age/i)).toBeTruthy();
  expect(getByText(/gender/i)).toBeTruthy();
  expect(getByText(/governorate/i)).toBeTruthy();
  expect(getAllByText(/prefer not to say/i).length).toBe(3);
});
```

### Task B.3.2: Implement minimal component

**File:** `SmartCompareApp/src/components/DemographicsBottomSheet.tsx`

Use existing design system (`src/theme`, `Button`, `Chip`). Bottom sheet via `react-native-bottom-sheet` if already in deps, else simple `Modal` with bottom-aligned animated view.

3 picker rows (age, gender, governorate). Each has options as Chips. "Prefer not to say" is always last chip in each row. Skip + Save buttons at bottom.

### Task B.3.3-B.3.5: Tests + impl for state management

- Selected values tracked in component state
- Save sends auto-detected language (from `expo-localization.locale`)
- Skip closes without sending payload
- Loading state during PUT; show toast on error

**Commit:** `feat(ui): demographics bottom sheet component`.

## B.4 — Trigger logic + dismissal cooldown

### Task B.4.1: Failing test for trigger schedule

**File:** `SmartCompareApp/__tests__/demographicsTrigger.test.ts`

Tests:
- Show on session 1 (first comparison) when `demographics_profile` is null
- Show on session 2, 3 if dismissed in session 1, 2
- After 3 dismissals: do NOT show until 7 days passed
- After 7 days: show #4
- After dismissal of #4: NEVER show again
- Do NOT show if user already submitted demographics

### Task B.4.2: Implement `shouldShowDemographicsPrompt()`

**File:** `SmartCompareApp/src/services/preferences.ts` (new file or add to existing)

```typescript
export function shouldShowDemographicsPrompt(state: {
  hasSubmitted: boolean;
  dismissedCount: number;
  lastDismissedAt: Date | null;
  currentSessionIndex: number; // 1-based count of sessions where user reached results screen
}): boolean {
  if (state.hasSubmitted) return false;
  if (state.dismissedCount === 0) return true;  // attempt #1 not yet shown — but that's caught by sessionIndex
  if (state.dismissedCount < 3) {
    // Sessions 2, 3
    return state.currentSessionIndex > state.dismissedCount;
  }
  if (state.dismissedCount === 3) {
    // 7-day cooldown
    if (!state.lastDismissedAt) return false;
    const daysSince = (Date.now() - state.lastDismissedAt.getTime()) / 86400000;
    return daysSince >= 7;
  }
  // dismissedCount >= 4: never show
  return false;
}
```

### Task B.4.3: Wire into ResultsScreen

After comparison results render, call `shouldShowDemographicsPrompt()`. If true, set bottom-sheet visible after 2-second delay. On Save → call `putDemographics`, mark `hasSubmitted=true`. On Skip → increment `dismissedCount`, set `lastDismissedAt=now`.

Persist state in `expo-secure-store` (consistent with auth token storage).

**Commit:** `feat(ui): demographics prompt trigger with 4-attempt schedule`.

## B.5 — Profile screen "Your style profile" card

### Task B.5.1: Failing test for card visibility

**File:** `SmartCompareApp/__tests__/StyleProfileCard.test.tsx`

```typescript
test("renders persona when confidence >= medium", () => {
  const display = { persona_label: "Quality-first focused buyer", n: 23, ... };
  const { getByText } = render(<StyleProfileCard display={display} />);
  expect(getByText("Quality-first focused buyer")).toBeTruthy();
  expect(getByText(/23 similar/i)).toBeTruthy();
});

test("renders nothing when display is null", () => {
  const { queryByText } = render(<StyleProfileCard display={null} />);
  expect(queryByText(/style profile/i)).toBeNull();
});
```

### Task B.5.2: Implement `StyleProfileCard.tsx`

Use existing Card primitive from `src/components`. Layout per design doc Section 5.6.

### Task B.5.3: Wire into ProfileScreen

Add `useEffect` to call `getCohortProfile()` on mount. Render `<StyleProfileCard display={...} />` above existing preferences section. Pull-to-refresh re-fetches.

**Commit:** `feat(ui): style profile card on Profile screen`.

## B.6 — Edit modal

### Task B.6.1: Test for "These were inferred" banner

When user opens preference edit while sources are inferred, show informational banner. After user saves an edit, source flips to user_stated and banner disappears for that field.

### Task B.6.2: Wire edit save to flip sources

`PUT /preferences` already handles flips (backend task A.4.3). Frontend just needs to send the FULL preferences object after edit; backend diffs and flips sources.

After save, refetch preferences, update state.

**Commit:** `feat(ui): edit seeded preferences with source-flip on save`.

---

# SECTION C — test-cohort tasks

**Owner files:**
- `tests/test_build_cohorts.py` (started by backend-cohort, expanded here)
- `tests/test_cohort_service.py` (started by backend-cohort, expanded here)
- `tests/test_auth_demographics.py`
- `tests/test_extraction_cohort_prompt.py`
- `tests/test_security_regression.py` (additions)
- `SmartCompareApp/__tests__/DemographicsBottomSheet.test.tsx` (started by frontend-cohort, expanded here)
- `SmartCompareApp/__tests__/StyleProfileCard.test.tsx` (started by frontend-cohort, expanded here)

**Coverage target:** verify 80% line coverage on `app/services/cohort_service.py` and `scripts/build_cohorts.py` via `pytest --cov`. Push to 90% on the matching algorithm.

Test-cohort can begin BEFORE backend-cohort/frontend-cohort have implemented anything — write the FAILING tests against the design doc spec. The implementations make the tests pass.

## C.1 — ETL fixture data

### Task C.1.1: Create test fixture CSV

**File:** `tests/fixtures/cohort_fixtures/sample_eng.csv` (~10 rows covering enough variety to exercise grouping, modal, fallback) + `sample_arab.csv` (5 rows of Arabic exercise normalization edge cases).

Commit fixtures.

## C.2 — Build script edge case tests

### Task C.2.1: Multi-select splitting

```python
def test_multi_select_splits_on_comma():
    row = {"deciding_factor_raw": "Quality,Price,Brand"}
    assert split_multi(row, "deciding_factor_raw") == ["Quality", "Price", "Brand"]
```

### Task C.2.2: Atomic write

```python
def test_atomic_write_does_not_leave_partial_file(tmp_path, monkeypatch):
    # Force an exception mid-build, assert no .tmp file remains and target file unchanged
    ...
```

### Task C.2.3: Cohort confidence flag boundaries

```python
def test_confidence_n_19_is_medium(): ...
def test_confidence_n_20_is_high(): ...
def test_confidence_n_4_omitted(): ...
def test_confidence_n_5_is_low(): ...
```

### Task C.2.4: Run coverage report

```bash
pytest --cov=scripts.build_cohorts --cov-report=term-missing tests/test_build_cohorts.py
```

If <80%, add tests for missing branches.

**Commit:** `test(cohort): expand build_cohorts to 80%+ coverage`.

## C.3 — Cohort service edge case tests

### Task C.3.1: Match quality propagation

Each fallback level returns the correct `match_quality` string.

### Task C.3.2: `get_display_profile` returns None for low confidence

### Task C.3.3: Service handles missing cohort_priors.json gracefully

```python
def test_service_handles_missing_priors_file():
    with mock.patch("app.services.cohort_service.PRIORS_PATH", Path("/nonexistent")):
        svc = CohortService()
        match = svc.match({"age_group": "25-34", ...})
        assert match is None  # degraded mode
```

### Task C.3.4: `should_seed()` decision logic

Returns True when prefs are empty OR all `_sources` are inferred. False when any field is `user_stated`.

**Commit:** `test(cohort): cohort_service edge cases to 90% coverage on match()`.

## C.4 — Auth demographics endpoint integration tests

### Task C.4.1: Auth required (401 without token)

### Task C.4.2: Rate limit (5/min, 6th request → 429)

### Task C.4.3: Stores demographics_profile in DB

### Task C.4.4: Triggers preference seeding when prefs empty

### Task C.4.5: Does NOT overwrite user_stated preferences

### Task C.4.6: Auto-detects language from Accept-Language header

### Task C.4.7: Auto-detects country from CF-IPCountry header

**Commit:** `test(auth): demographics endpoint full coverage`.

## C.5 — Extraction prompt snapshot tests

### Task C.5.1: Cohort block injected for strong match (snapshot)

### Task C.5.2: Cohort block skipped for population match (negative)

### Task C.5.3: Cohort block skipped when feature flag off

### Task C.5.4: NO raw demographics in prompt (privacy assertion)

```python
def test_no_raw_demographics_in_rendered_prompt():
    profile = {"age_group": "25-34", "gender": "Female", "country": "Bahrain",
               "language": "Arabic", "governorate": "Northern",
               "cohort_match": {"match_quality": "exact", "confidence": "high", ...}}
    prompt = _build_preferences_prompt(..., demographics_profile=profile)
    # The thin context line is allowed to mention country/language/region
    # but RAW age + gender must NEVER appear
    assert "25-34" not in prompt
    assert "Female" not in prompt
    assert ", Female" not in prompt  # no demographic phrase
```

**Commit:** `test(extraction): snapshot + privacy assertions on cohort prompt block`.

## C.6 — Security regression additions

### Task C.6.1: Cross-user demographics RLS

```python
def test_user_cannot_read_other_users_demographics(supabase_user_clients):
    user_a, user_b = supabase_user_clients
    # user_a sets demographics
    # user_b tries to query users.demographics_profile WHERE id = user_a.id
    # assert: empty result, not 403 (RLS quietly filters)
```

### Task C.6.2: Auth required for demographics endpoints

Add to `tests/test_security_regression.py`:
- `PUT /demographics` without token → 401
- `GET /cohort-profile` without token → 401

**Commit:** `test(security): RLS + auth regression for demographics`.

## C.7 — Frontend component test expansion

### Task C.7.1: Bottom sheet "Save" calls API with correct payload (incl auto-detected language)

### Task C.7.2: Bottom sheet "Skip" doesn't call API, increments dismissedCount

### Task C.7.3: Trigger logic — full 4-attempt schedule with Date mocking

### Task C.7.4: Style profile card hidden when display is null

### Task C.7.5: Edit modal banner shows only when sources are inferred

**Commit:** `test(ui): demographics + style profile component coverage`.

## C.8 — Verify final coverage

### Task C.8.1: Run full coverage report

```bash
pytest --cov=app/services/cohort_service --cov=scripts/build_cohorts \
       --cov=app/api/auth_routes --cov-report=term-missing \
       --cov-fail-under=80
```

If any module is below 80%, add tests for the uncovered branches.

```bash
cd SmartCompareApp && npx jest --coverage src/components/DemographicsBottomSheet
```

Same threshold check.

**Commit:** `test: verify 80%+ coverage on cohort feature surface`.

---

# SECTION D — qa-cohort tasks

**Role:** Cross-reviews ALL 3 agents' work. Runs full test suite after each commit. Verifies metric instrumentation against real Supabase. Signs off final feature. Verifies coverage. Runs end-to-end manual test.

**Idle behavior:** write integration tests spanning backend + frontend; profile slow paths.

## D.1 — Continuous integration check

After every commit by another agent:

### Task D.1.1: Run full test suite

```bash
pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180
```

If any test fails (including PRE-EXISTING tests that may regress), file a send-back to the responsible agent.

### Task D.1.2: Run TypeScript check

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Zero errors expected.

### Task D.1.3: Run security regression suite

```bash
pytest tests/test_security_regression.py -v
```

All 57+ existing tests + new demographics RLS test must pass.

## D.2 — Cross-review backend (reviews backend-cohort's work)

After backend-cohort signals "ready for QA":

- [ ] `scripts/build_cohorts.py`: ETL is idempotent, atomic write, fails loudly on unknown Arabic, drops invalid rows
- [ ] `cohort_service.py`: matches design doc Section 3.3 fallback algorithm exactly. All branches covered.
- [ ] Auth route additions: rate-limited, auth-protected, RLS-safe
- [ ] Extraction prompt block: matches design doc Section 4.2 exactly. No raw demographics leak.
- [ ] Migration: idempotent (`IF NOT EXISTS`), no DROP statements
- [ ] Admin endpoints: X-Admin-Key auth, 30/min rate limit
- [ ] HTML dashboard: renders without errors when admin endpoints return data
- [ ] Feature flag: defaults to false, disabling skips both B and C

If any item fails, send back with structured review block. See "Send-back protocol" in design doc Section 7.3.

## D.3 — Cross-review frontend (reviews frontend-cohort's work)

After frontend-cohort signals "ready for QA":

- [ ] Bottom sheet renders correctly in EN and AR (RTL layout)
- [ ] Trigger logic respects 4-attempt schedule
- [ ] Auto-detected language sent to API
- [ ] Skip + Save both work without errors
- [ ] Style profile card hidden when no display
- [ ] Edit modal banner shows correctly
- [ ] Dismissal state persists across app restarts (SecureStore)
- [ ] Loading + error states render

## D.4 — Cross-review tests (reviews test-cohort's work)

After test-cohort signals "ready for QA":

- [ ] `pytest --cov` confirms 80% on `cohort_service` + `build_cohorts`, 90% on `match()`
- [ ] All new tests are red-green (write failing, then make pass — verify by reverting impl and confirming tests fail)
- [ ] Snapshot test for prompt block is meaningful (not just `assert True`)
- [ ] RLS regression test exercises the actual Supabase RLS, not a mock
- [ ] Frontend tests render without errors and assert on visible behavior

## D.5 — End-to-end manual verification

### Task D.5.1: Local backend startup

```bash
uvicorn app.main:app --reload --port 8000
```

Verify `cohort_priors.json` loaded at startup (check logs for INFO message; if WARNING about missing file, abort and re-run ETL).

### Task D.5.2: Local frontend startup

```bash
cd SmartCompareApp && npx expo start --clear
```

Open in iOS simulator (or physical device).

### Task D.5.3: Full user flow

1. Sign up new test user.
2. Run a comparison from HomeScreen.
3. Verify results render on ResultsScreen.
4. Wait 2 seconds → demographics bottom sheet appears.
5. Fill in: 25-34 / Female / Northern / [save].
6. Verify success toast.
7. Query Supabase: `SELECT demographics_profile, preferences FROM users WHERE id = '<test-uuid>';` → demographics_profile populated, preferences seeded with `_sources` set to "inferred".
8. Run a SECOND comparison.
9. Inspect backend logs for the verdict prompt → confirm cohort block is present (or use a debug endpoint that returns the rendered prompt).
10. Open Profile screen → "Your style profile" card visible with persona_label.
11. Tap edit → preferences modal opens with banner "These were inferred...".
12. Edit one field (e.g. budget) → save.
13. Re-query Supabase: `_sources.budget` now `"user_stated"`; banner gone for that field on next open.

### Task D.5.4: Negative flow — dismissals

1. Fresh test user.
2. Run comparison → dismiss bottom sheet.
3. Run comparison again → bottom sheet appears (attempt #2).
4. Dismiss again → run comparison → bottom sheet appears (#3).
5. Dismiss again → run comparison → bottom sheet does NOT appear (cooldown).
6. (Skip the 7-day wait — verify by manipulating `lastDismissedAt` in SecureStore.)
7. After "7 days" → run comparison → bottom sheet appears (#4).
8. Dismiss → run comparison → bottom sheet does NOT appear (permanent stop).

### Task D.5.5: Admin dashboard

```bash
open http://localhost:8000/admin/cohort.html
```

Enter X-Admin-Key when prompted. Verify all 4 charts/KPIs render with non-zero data.

## D.6 — Disassembly Gate (BLOCKING)

Team disassembles ONLY when ALL of these are checked:

- [ ] All 7 deliverables marked complete by their owner agent
- [ ] Cross-QA matrix has 4 approvals (3 peer + 1 from qa-cohort) — confirmed via review messages
- [ ] `pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180` passes 100%
- [ ] `cd SmartCompareApp && npx tsc --noEmit` passes 0 errors
- [ ] `pytest --cov=app/services/cohort_service --cov=scripts/build_cohorts --cov-fail-under=80` passes
- [ ] All 5 success metrics visible in `/admin/cohort.html` with real data
- [ ] End-to-end manual test (D.5.3) passes
- [ ] Negative flow test (D.5.4) passes
- [ ] Migration `013_demographics_cohort.sql` documented as needs-manual-apply in CLAUDE.md
- [ ] Feature flag `ENABLE_COHORT_PERSONALIZATION` defaults to `false` in env config
- [ ] No security regression (`pytest tests/test_security_regression.py -v` 100%)
- [ ] No PRE-EXISTING tests regressed

**If ANY gate fails:** team continues until resolved. NO premature disassembly.

## D.7 — Final commit + handoff

After gate passes:

### Task D.7.1: Update CONTEXT_SESSION_LOG.md

Brief entry: feature shipped, commits, gotchas encountered.

### Task D.7.2: Update MEMORY.md

Add Session 41 (or next session number) entry noting:
- Feature: survey-driven cohort personalization
- Commits: list
- Tests: total count + new tests count
- Manual step: apply migration 013
- Feature flag: still off; awaiting Phase 1 internal QA

### Task D.7.3: Open Pull Request

```bash
gh pr create --title "feat: survey-driven cohort personalization (B+C)" --body "$(cat <<'EOF'
## Summary
- Use ~400 Fillout survey responses as statistical priors for personalization
- (B) Verdict prompt enrichment with aggregate cohort findings
- (C) One-shot preference seeding from cohort modal
- Demographics asked post-first-comparison via skippable bottom sheet
- Style profile surfaced in Profile screen (Option C visibility)

## Test plan
- [ ] Apply migration 013_demographics_cohort.sql via Supabase SQL Editor
- [ ] Set ENABLE_COHORT_PERSONALIZATION=false in Railway (default)
- [ ] Verify ETL: `python -m scripts.build_cohorts` produces cohort_priors.json
- [ ] Run pytest tests/ -v: all pass
- [ ] Run npx tsc --noEmit: 0 errors
- [ ] Manual end-to-end (per docs/superpowers/plans/2026-05-03-survey-cohort-personalization.md D.5.3)
- [ ] Phase 1 rollout: enable flag for admin accounts only

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Task D.7.4: Confirm safe to disassemble

Post a final message in team channel: "All gates passed. Team safe to disassemble. PR <url> open for review."

---

# Cross-QA Matrix Quick Reference

```
backend-cohort     ──reviews──▶  frontend-cohort   (D.3)
frontend-cohort    ──reviews──▶  test-cohort       (D.4)
test-cohort        ──reviews──▶  backend-cohort    (D.2)
qa-cohort          ──reviews──▶  ALL THREE         (D.2 + D.3 + D.4)
```

Each agent must complete their assigned review before disassembling.

---

# Send-Back Template (use this format)

When sending work back as subpar:

```markdown
## REVIEW: SEND BACK

**Reviewer:** <agent-name>
**Reviewing:** <other-agent-name>'s task <task-id>
**Status:** Send back

### What's wrong
<specific issue with file:line reference>

### What's missing
<specific deliverable not present>

### What's expected (per design doc)
<quote from design doc with section reference>

### Suggested fix or pointer
<concrete next step>
```

---

# Out of scope for this plan

- Continuous in-app survey collection (option E from brainstorm) — defer
- Cross-country cohort expansion — defer until non-Bahrain markets active
- RAG over individual survey responses — defer
- Fine-tuning — needs 5000+ responses, not feasible now

---

**End of implementation plan.**

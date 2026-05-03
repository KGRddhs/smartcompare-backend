# Survey-Driven Cohort Personalization — Design

**Date:** 2026-05-03
**Status:** Approved (brainstorming complete)
**Author:** Brainstormed with Claude
**Owner:** Ahmed

---

## Executive Summary

Use ~400 existing survey responses (English + Arabic Fillout exports) as **statistical priors** to bootstrap personalization for new and anonymous users.

Two reinforcing mechanisms:

- **B — Verdict prompt enrichment:** every comparison verdict prompt receives a small block of cohort-aggregated findings (top deciding factors, typical spend, preferred verdict format, top difficulties, trust signals) when a strong cohort match exists. The user's individual demographics are NOT in the prompt — only the aggregate findings — except a thin context line (country + language + governorate) that genuinely helps GPT localize.
- **C — Default-preference seeding:** when a user submits demographics (post-first-comparison bottom sheet, all skippable), the backend matches them to the most specific available cohort and seeds the existing 4 preference fields (`priorities`, `budget`, `brand_attitude`, `lifestyle`) with the cohort's modal answers. Each seeded field is tagged `source: "inferred"`. User edits flip the source to `"user_stated"`. The Profile screen exposes a "Your style profile" card showing the inferred persona with an edit affordance.

**Cost:** zero per-request. All cohort lookups are local in-memory dict reads. ETL runs once at build-time (re-run when surveys grow).

**Why this over alternatives:**
- 400 responses is too small for fine-tuning GPT-4o-mini (need thousands+) and would lose existing transparency.
- 400 IS plenty for cohort-level statistics with reasonable confidence at the strong-match level.
- Statistical aggregates injected into the prompt avoid leaking individual PII to OpenAI even though some demographic context still flows through.

**Out of scope (defer):** continuous in-app survey collection (option E from brainstorming), multi-page progressive profile capture beyond the bottom sheet, RAG over individual responses, fine-tuning.

---

## 1. Architecture Overview

```
[BUILD TIME — one-shot, re-run when surveys grow]
  data/surveys/Fillout_ENG_results.csv  ──┐
  data/surveys/Fillout_arab_results.csv ──┴─→  scripts/build_cohorts.py
                                                       ↓
                                          (normalize Arabic→English values,
                                           group by cohort key, compute
                                           modal answers + distributions)
                                                       ↓
                                          data/cohort_priors.json  (committed, ~50KB)


[RUNTIME]
  Signup → existing onboarding (preferences as-is) → first comparison
                                                            ↓
                          Bottom sheet: "Tell us about you" (3 fields, all skippable)
                                                            ↓
                                        PUT /api/v1/auth/demographics
                                                            ↓
                          cohort_service.match(demographics) → cohort priors
                                                            ↓
                              ┌────── seed users.preferences (C, one-shot) ──────┐
                              ↓                                                  ↓
                  inferred_priorities, budget,                       store full cohort profile
                  brand_attitude                                     on users.demographics_profile
                  (each tagged source: "inferred")                   (for prompt + Profile UI)

  Subsequent comparisons:
                  StructuredComparisonService → extraction_service._build_preferences_prompt()
                                                            ↓
                              Appends cohort priors block to verdict prompt (B)

  Profile screen:
                  GET /api/v1/auth/cohort-profile  →  "Your style profile" card
                                                            with EDIT affordance
```

**5 new pieces:**
1. `data/surveys/*.csv` — committed survey data (raw responses; can be gitignored if preferred since `cohort_priors.json` is the runtime artifact)
2. `scripts/build_cohorts.py` — ETL: CSV → normalized → grouped → JSON
3. `data/cohort_priors.json` — runtime lookup table, ~50KB, committed
4. `app/services/cohort_service.py` — loads JSON at startup; `match()`, `seed_preferences()`, `get_display_profile()`
5. Frontend: `DemographicsBottomSheet.tsx` (post-first-comparison) + `StyleProfileCard.tsx` (in ProfileScreen) + edit modal

**Existing code touched:**
- `app/api/auth_routes.py` — add `PUT /demographics`, `GET /cohort-profile`; existing `PUT /preferences` extended to handle the `_sources` sub-object
- `app/services/extraction_service.py` — `_build_preferences_prompt()` appends cohort priors block when match is strong enough
- `app/api/admin_routes.py` — add `GET /admin/cohort/{metrics,feedback,retention}` endpoints

**Database:** add one `demographics_profile` JSONB column to `public.users` (RLS: user reads/writes own row only). Two helper columns for dismissal tracking. Three SQL views for metrics.

---

## 2. ETL Pipeline + Cohort Schema

### 2.1 `scripts/build_cohorts.py` — runs once (and re-run when surveys grow)

**Steps:**

1. **Read** both CSVs (English + Arabic), tag each row with `source_lang`.
2. **Normalize Arabic → English** values via a static mapping table baked into the script (~80 mappings across all categorical fields).
3. **Drop** rows where: consent ≠ true, `Status ≠ "finished"`, or all 4 cohort-key fields are empty/"Prefer not to say".
4. **Split multi-selects** (e.g. `"Quality,Price"`) into individual values for distribution counting.
5. **Group by cohort key** = `(age_group, gender, governorate, language)` — 4 fields. Identity is excluded from the key (sensitive + skip rate would shrink cohorts); kept as a within-cohort distribution stat instead.
6. **Compute per-cohort stats:** modal answers, full distribution, `n`, confidence flag.
7. **Build fallback aggregates** for every shorter prefix of the cohort key, plus a population-wide aggregate.
8. **Atomic write** to `data/cohort_priors.json.tmp` then rename to final path.

### 2.2 Cohort key

`"{age}|{gender}|{governorate}|{language}"` — e.g. `"25-34|Female|Northern|Arabic"`.

With 5 × 3 × 5 × 3 = 225 possible cells against 400 responses, expect 30–50 cells with `n ≥ 5` and ~10–15 with `n ≥ 10`. Fallback chain handles the rest.

### 2.3 Confidence flags

| Range | Confidence |
|---|---|
| `n ≥ 20` | `"high"` |
| `10 ≤ n < 20` | `"medium"` |
| `5 ≤ n < 10` | `"low"` |
| `n < 5` | omitted; matcher falls back |

### 2.4 `data/cohort_priors.json` schema

```json
{
  "version": "1.0",
  "built_at": "2026-05-03T12:00:00Z",
  "total_responses": 397,
  "cohorts": {
    "25-34|Female|Northern|Arabic": {
      "n": 23,
      "confidence": "high",
      "demographics": { "age_group": "25-34", "gender": "Female",
                        "governorate": "Northern", "language": "Arabic" },
      "modal": {
        "top_deciding_factor": "Quality",
        "second_deciding_factor": "Price",
        "preferred_assistance_style": "Show me 2 or 3 suitable options",
        "spend_bracket": "25-50 BHD",
        "trust_sources": ["Store", "Word of mouth"],
        "top_difficulties": ["Too many options", "Quality-Reliability"],
        "post_purchase_pattern": "Felt right",
        "what_helps_most": ["Show main differences", "Know better value"],
        "primary_categories": ["Fashion", "Health"]
      },
      "distribution": {
        "deciding_factor": { "Quality": 0.43, "Price": 0.30, "Brand": 0.13, "Warranty": 0.09 },
        "assistance_style": { "Show 2-3 options": 0.61, "Suggest best with reason": 0.22, "All details": 0.17 }
      },
      "persona_label": "Quality-first focused buyer"
    }
  },
  "fallback_aggregates": {
    "25-34|Female|Arabic": { "...same shape..." },
    "25-34|Female": { "...same shape..." },
    "25-34": { "...same shape..." },
    "all": { "...same shape..." }
  }
}
```

### 2.5 `persona_label`

Generated from modal answers via a small rule table (~8–10 labels covering the cohort space). Example:
- `top_deciding_factor=Quality + spend≤50 + assistance="2-3 options"` → `"Quality-first focused buyer"`
- `top_deciding_factor=Price + spend<25` → `"Budget-conscious value seeker"`

Used on the Profile card.

### 2.6 ETL tests

- Arabic normalization round-trip — every Arabic value maps to a known English value or build FAILS LOUDLY with row number + unknown value (no silent drops).
- No cohort with `n < 5` appears in output.
- Modal answer for 3 spot-check cohorts matches manual count.
- Population aggregate `n` equals total responses minus drops.

---

## 3. Cohort Matching Service (`app/services/cohort_service.py`)

Loaded once at app startup (singleton-style, like `bahrain_drugs_service`). The JSON sits in memory permanently — ~50KB, negligible.

### 3.1 Public API

```python
class CohortService:
    def __init__(self):
        self._cohorts: dict = self._load_cohort_priors()

    def match(self, demographics: dict) -> CohortMatch | None:
        """Return best cohort match with hierarchical fallback.
        Returns None only if EVERY field is missing/skipped."""

    def seed_preferences(self, demographics: dict) -> dict:
        """One-shot: derive starting preferences object from cohort modal."""

    def get_display_profile(self, demographics: dict) -> dict:
        """For Profile UI 'Your style profile' card."""
```

### 3.2 `CohortMatch` shape

```python
{
    "cohort_key": "25-34|Female|Northern|Arabic",
    "match_quality": "exact",  # "exact" | "broadened_governorate" | "broadened_language" | "broadened_age" | "population"
    "confidence": "high",
    "n": 23,
    "modal": {...},
    "distribution": {...},
    "persona_label": "Quality-first focused buyer"
}
```

### 3.3 Hierarchical fallback algorithm

```
1. Try full key (age|gender|governorate|language) — if cohort exists with confidence ≥ "low" (n≥5), return it
2. Drop governorate → try (age|gender|language) — if exists with n≥10, return broadened
3. Drop language → try (age|gender) — if exists with n≥10, return broadened
4. Drop age → try (gender) — if exists with n≥20, return broadened
5. Else return population aggregate, match_quality="population"
```

### 3.4 Skipped fields ("Prefer not to say")

Treated as missing; immediately drop from key and try shorter prefixes. Skipping all 3 collected demographics → returns population aggregate (still useful — generic GCC priors).

### 3.5 Auto-detected fields (no UI ask)

- **Language** ← React Native `expo-localization` device locale; map: `ar*` → `"Arabic"`, `en*` → `"English"`, else → `"Both equally"`. Sent in `PUT /demographics` payload as backend-derived field. User can override later in Profile.
- **Country** ← request IP via `geoip2` lookup or Cloudflare `CF-IPCountry` header. Used for verdict context, NOT cohort key (surveys are Bahrain-only).

### 3.6 Match-quality used by callers

| Caller | Behavior |
|---|---|
| `extraction_service` (B injection) | Inject cohort priors block ONLY when `match_quality ∈ {exact, broadened_governorate, broadened_language}`. Population too generic to spend tokens on. |
| `seed_preferences` (C) | Seed for ANY match including population (better than empty defaults). |
| Profile UI | Show persona_label only when `confidence ≥ "medium"`. Else hide card entirely. |

### 3.7 Tests

- Exact match returns the right cohort.
- Missing governorate → broadens correctly.
- All "Prefer not to say" → returns population.
- `match_quality` propagates to caller.
- Singleton loaded once, not per-request (perf assertion).

---

## 4. Verdict Prompt Enrichment — B Integration

**File touched:** `app/services/extraction_service.py` → existing `_build_preferences_prompt()`. Append a new block.

### 4.1 Trigger

Inject cohort priors block ONLY when:
- `cohort_match.match_quality ∈ {"exact", "broadened_governorate", "broadened_language"}`
- AND `cohort.confidence ≥ "low"`

Population aggregates and weak matches → skip the block entirely (no value, costs tokens).

### 4.2 What gets injected (~120 tokens max)

```
USER CONTEXT: Country=Bahrain, Language=Arabic, Region=Northern Governorate

# COHORT-LEVEL PRIORS (statistical pattern from {N} similar users)

When tailoring this verdict, weight these signals:

- DECIDING FACTORS this group prioritizes (in order): Quality, Price, Warranty
- TYPICAL SPEND for their purchase context: 25-50 BHD
  → frame anything below 25 BHD as "below their range", 50-100 as "above range stretch"
- PREFERRED VERDICT FORMAT: Show 2-3 suitable options with clear differences
  (NOT: full detail dump; NOT: single recommendation without alternatives)
- TOP DIFFICULTIES to proactively address: Too many options, Quality-Reliability uncertainty
- TRUST SIGNALS that resonate: in-store experience, word-of-mouth recommendations
  → prefer retailer attribution from physical stores or established marketplaces over pure online-only

These are POPULATION STATISTICS, not facts about the individual user.
Use them as defaults; the user's explicit preferences and behavioral history override.
```

### 4.3 Field selection rationale

| Field IN prompt | Why |
|---|---|
| Top deciding factors | Tells GPT which dimensions to weight |
| Spend bracket | Calibrates value framing ("splurge" / "normal" / "stretch") |
| Preferred verdict format | Tells GPT HOW to structure output |
| Top difficulties | Surfaces what to proactively explain |
| Trust signals | Calibrates retailer attribution |
| Country + Language + Region (thin context line) | Genuinely helps GPT localize tone, currency, retailer mentions |

| Field EXCLUDED | Why |
|---|---|
| `post_purchase_pattern` | Temporal, doesn't change the verdict |
| `what_helps_most` | Redundant with `preferred_verdict_format` |
| `primary_categories` | Already encoded in the comparison query |
| `identity` (Bahraini/resident) | Sensitive AND not predictive once age+gender+language known |
| Distribution percentages | Clutter; GPT doesn't need "Quality 43%" to know Quality is #1 |
| Age + gender (raw) | Cohort findings encode this MORE actionably; raw values are noise to GPT |

**Toggle for full demographics:** `INJECT_FULL_DEMOGRAPHICS=true` env flag adds a raw demographics line if observed verdict quality justifies it. Default `false`.

### 4.4 Three-layer ordering inside the prompt

```
1. EXPLICIT PREFERENCES (user_stated, ±30% scoring weight)  — strongest, last word
2. BEHAVIORAL PROFILE (decay-weighted, ±10%)                 — actual behavior
3. COHORT PRIORS (statistical, NEW)                          — defaults / cold-start filler
```

The prompt explicitly instructs GPT that cohort priors are **defaults to be overridden** — prevents cohort priors from fighting stronger personal signals.

### 4.5 Privacy posture

- ✅ Sent to OpenAI: aggregate cohort findings ("group prioritizes Quality > Price > Warranty"), `N` count, country, language, region
- ❌ NOT sent to OpenAI by default: user's specific age, gender, identity (these are cohort lookup keys only — server-side)
- Even if OpenAI logs/trains on these prompts, no individual is identifiable from "this user's cohort prioritizes quality"
- Privacy policy must disclose: aggregated demographic patterns + country/language/region context shared with AI provider

### 4.6 Token budget

~120 tokens per request when injected, ~0 when not. Across all comparisons, adds <2% to verdict prompt size.

### 4.7 Tests

- Cohort priors block injected ONLY when match_quality is strong enough.
- No raw `age`, `gender`, `identity` field name appears in rendered prompt — assert via grep on prompt string.
- Block ordering: explicit > behavioral > cohort.
- Snapshot test on a sample cohort renders correctly.

---

## 5. Preference Seeding + Profile UI — C Integration

### 5.1 Backend preference seeding (one-shot at demographics submission)

**Endpoint flow:**

```
PUT /api/v1/auth/demographics
  → cohort_service.match()
  → if user has NO existing preferences (or all source="inferred"):
       cohort_service.seed_preferences()
       → database_service.save_user_preferences(merged)
  → if user has user_stated preferences:
       DON'T overwrite. Only fill BLANK fields from cohort.
```

### 5.2 Mapping cohort modal → existing 4 preference fields

| Existing field | Source from cohort | Example |
|---|---|---|
| `priorities` (1-3 of 8) | `top_deciding_factor` + `second_deciding_factor` mapped to existing 8 enum values | `"Quality"` + `"Price"` → `["quality_reliability", "best_price"]` |
| `budget` (budget/mid/premium) | `spend_bracket` → tier | `"25-50 BHD"` → `"mid"` |
| `brand_attitude` | inferred from `"if info incomplete, what do you do?"` | `"Choose the brand I know"` → `"trust_known_brands"` |
| `lifestyle` (0+ of 11) | **left empty** — no clean survey signal | (user fills via Profile if they want) |

### 5.3 Source tagging — additive, no breaking change

`preferences` JSONB grows a sibling `_sources` object. Existing code that reads `preferences.priorities` keeps working.

```json
{
  "priorities": ["quality_reliability", "best_price"],
  "budget": "mid",
  "brand_attitude": "trust_known_brands",
  "lifestyle": [],
  "_sources": {
    "priorities": "inferred",
    "budget": "inferred",
    "brand_attitude": "inferred",
    "lifestyle": null
  },
  "_seeded_at": "2026-05-03T14:23:00Z",
  "_cohort_key": "25-34|Female|Northern|Arabic"
}
```

When the user edits a preference in Profile → flip that field's source to `"user_stated"`. Scoring layer can then weight `user_stated` fields more strongly than `inferred` (recommended: `user_stated` gets full ±30%, `inferred` gets ±15%) — prevents wrong cohort guesses from over-personalizing.

### 5.4 Bottom sheet trigger (frontend)

**File:** new `SmartCompareApp/src/components/DemographicsBottomSheet.tsx`

**Trigger logic:**

```
if (
  user.is_authenticated &&
  user.demographics_profile === null &&        // never asked
  comparison.is_first_for_user_or_eligible &&  // see attempt schedule below
  attempt_count < 4
) {
  delay 2 seconds after results render → show bottom sheet
}
```

**Sheet content (3 fields, ~30 sec to fill):**
- Age group: 18-24 / 25-34 / 35-44 / 45-54 / 55+ / Prefer not to say
- Gender: Male / Female / Prefer not to say
- Governorate: Capital / Muharraq / Northern / Southern / Other / Prefer not to say
- Buttons: `[Skip for now]`  `[Save]`

**Copy (English):** *"Want recommendations tuned to people like you? 3 quick taps."*
**Copy (Arabic):** localized equivalent in `src/i18n/ar.json`.

**Auto-detected (sent in same payload, no UI):** `language` from `expo-localization`, `country` from request IP.

### 5.5 Dismissal + re-prompt schedule

```
- Session 1 (first comparison)  →  show prompt (attempt #1)
- Session 2 (next visit)        →  show prompt (attempt #2)
- Session 3 (next visit)        →  show prompt (attempt #3)
  ↓
  if all 3 dismissed:
    7-day cooldown
    ↓
  attempt #4 after 7 days
    ↓
  if dismissed: never auto-prompt again (Profile remains manually available)
```

Total 4 nudges max. Tracked via `users.demographics_dismissed_count` + `users.demographics_dismissed_at`. After attempt #4 dismissal: hard stop on auto-prompt; user can still tap "Tell us about you" in Profile.

### 5.6 Profile UI ("Your style profile" card)

**File:** add to existing `SmartCompareApp/src/screens/ProfileScreen.tsx`.

**Visibility:** card visible only when `cohort_match.confidence ≥ "medium"` AND user has submitted demographics. When confidence is `"low"` or fallback was `"population"`, hide card entirely.

**Card content:**

```
┌─────────────────────────────────────────┐
│ Your style profile                      │
│                                         │
│ Quality-first focused buyer             │
│ Based on 23 similar Qaren users         │
│                                         │
│ → Top priorities: Quality, Price        │
│ → Typical budget: 25-50 BHD             │
│ → Style: Show 2-3 options with reasons  │
│                                         │
│ [Edit my preferences →]                 │
└─────────────────────────────────────────┘
```

**Edit modal:** opens existing PreferencesScreen pre-populated with current values + a small banner: *"These were inferred from your background. Edit to make them yours."* Save flow flips relevant `_sources` from `"inferred"` to `"user_stated"`.

### 5.7 Tests

**Backend:**
- Seeding maps cohort modal → preferences correctly for 3 sample cohorts.
- Seeding does NOT overwrite user_stated fields.
- Source tags persist through `PUT /preferences` round-trip.
- Demographics endpoint records IP→country derivation correctly.

**Frontend:**
- Bottom sheet shows after first comparison only when conditions met.
- 3-attempt streak → 7-day cooldown → 4th attempt → permanent dismissal.
- All 3 fields can be set to "Prefer not to say" → still submits successfully.
- Profile card hidden when confidence is low/population.

---

## 6. Privacy, Storage, Error Handling, Success Metrics

### 6.1 Storage + DB Schema

**Migration:** `migrations/013_demographics_cohort.sql`

```sql
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS demographics_profile JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_at TIMESTAMPTZ DEFAULT NULL;

-- RLS: users can only read/write their own row (existing pattern).
-- preferences JSONB column already gets _sources sub-object — no schema change needed.

-- SQL views for metrics (Section 6.4)
CREATE OR REPLACE VIEW vw_cohort_match_rate AS
SELECT
  date_trunc('day', updated_at) AS day,
  COUNT(*) FILTER (WHERE demographics_profile->'cohort_match'->>'match_quality' IN ('exact','broadened_governorate','broadened_language')) AS strong_matches,
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

**`demographics_profile` JSONB shape:**

```json
{
  "age_group": "25-34",
  "gender": "Female",
  "governorate": "Northern",
  "language": "Arabic",
  "country": "Bahrain",
  "submitted_at": "2026-05-03T14:23:00Z",
  "cohort_match": {
    "cohort_key": "25-34|Female|Northern|Arabic",
    "match_quality": "exact",
    "confidence": "high",
    "n": 23,
    "persona_label": "Quality-first focused buyer"
  }
}
```

`cohort_match` cached at submission time, NOT re-computed per request. Re-runs only when (a) user updates demographics OR (b) `cohort_priors.json` version changes (background job re-matches all users).

### 6.2 Privacy posture (concrete data flows)

| Data | Stored where | Sent to OpenAI? | RLS protected? |
|---|---|---|---|
| `demographics_profile` (raw demographics) | Supabase `users.demographics_profile` | ❌ Not directly. Only country + language + governorate appear in verdict prompt. Age + gender + identity stay server-side. | ✅ Yes |
| `cohort_priors.json` (population stats) | Repo file, app memory | ✅ Aggregate findings injected into verdict prompt (no PII — population statistics only) | N/A (public) |
| `_sources` tags on preferences | Supabase `users.preferences._sources` | ❌ Never sent | ✅ Yes |
| `cohort_match` (per-user cache) | Supabase `users.demographics_profile.cohort_match` | ❌ Never sent | ✅ Yes |

**Privacy policy update needed:** disclose that aggregated demographic patterns inform recommendations, and that country/language/region context is shared with the AI provider.

**RLS verification test:** add to `tests/test_security_regression.py` — confirm `demographics_profile` is unreadable by other users via direct PostgREST query.

### 6.3 Error Handling

| Failure | Behavior |
|---|---|
| `cohort_priors.json` missing at startup | Service starts in degraded mode. `cohort_service.match()` returns `None`. B injection skipped. C seeding skipped. Logged WARNING. |
| `cohort_priors.json` malformed | Same as missing + ERROR log + Sentry alert. |
| `PUT /demographics` with all "Prefer not to say" | Accept submission. Cohort match falls through to population aggregate. No Profile card. No preference seeding triggered. |
| Cohort match returns population aggregate | C seeding still runs (better than empty defaults). B injection skipped. Profile card hidden. |
| User edits seeded preference, source flip fails | Treat as user_stated regardless — never let a failed source flip lose the user's choice. |
| ETL script fails mid-run | Atomic write: build to `.tmp` then rename. Never write partial JSON. |
| Arabic value not in normalization map | Build script FAILS LOUDLY with row number + unknown value. No silent drops. |
| User dismissed all 4 times, then opens Profile | Profile shows empty state with "Tell us about you" button — manual entry remains available. |

### 6.4 Success Metrics

Instrumented into `user_events` table. Surfaced via SQL views (Section 6.1) + admin endpoints (Section 6.5).

1. **Cohort match rate** — % of users with `cohort_match.match_quality ∈ {"exact", "broadened_*"}` vs population fallback. **Target:** >60% within 3 months.
2. **Demographics submission rate** — % of users who fill the bottom sheet (any of 4 attempts). **Target:** >40%.
3. **Preference edit rate post-seeding** — % of seeded users who later edit a preference. **High edit rate (>30%) = cohorts mismatching → investigate.** Low rate (<10%) = inferences are accurate.
4. **Verdict quality (qualitative)** — flag a sample of comparisons with cohort priors injected vs without; A/B compare via existing `comparison_feedback` ratings. **Look for ≥0.3 star lift.**
5. **Cohort-driven retention proxy** — 7-day return rate for users who submitted demographics vs those who didn't.

**Anti-goal kill switches:**
- Demographics submission rate <10% after 30 days → bottom sheet UX is broken; redesign or kill the prompt.
- Preference edit rate >50% → cohort mappings are wrong; pause B injection until ETL retuned.
- Feedback ratings DROP on cohort-injected verdicts → kill B (keep C only) until investigated.

### 6.5 Visualization Layer

**Three-layer approach: SQL views → admin JSON endpoints → simple HTML dashboard.**

**Layer 1 — SQL views** (defined in 6.1). Queryable from Supabase Studio immediately, zero engineering.

**Layer 2 — Admin JSON endpoints (in `app/api/admin_routes.py`):**

```
GET /api/v1/admin/cohort/metrics      → match rate, submission rate, edit rate, persona distribution
GET /api/v1/admin/cohort/feedback     → verdict feedback stratified by cohort_injected
GET /api/v1/admin/cohort/retention    → 7-day return rate stratified
```

Authed by existing `X-Admin-Key`, rate limited 30/min (existing pattern).

**Layer 3 — Simple HTML dashboard (`app/static/admin/cohort.html`):**

One static page. `<script>` fetches admin endpoints, renders via **Chart.js** (CDN, no build step):
- Line chart: cohort match rate over time
- Bar chart: persona distribution
- Stacked bar: verdict feedback ratings (cohort vs no-cohort)
- KPI tiles: submission rate, edit rate, 7-day return rate

Served at `/admin/cohort.html`. Auth via prompt for X-Admin-Key on first load (sessionStorage). Crude but sufficient for an internal tool.

**Effort:** SQL views + 3 endpoints + 1 HTML page = ~1 day for one agent. Visualization stack ships WITH the feature, not after.

### 6.6 Feature Flag + Rollout

`ENABLE_COHORT_PERSONALIZATION` env var, default `false` initially.

**Rollout phases:**
1. **Phase 1 — internal:** flag on for admin accounts only. Ship ETL, cohort_service, demographics endpoint. Verify cohort matches manually.
2. **Phase 2 — 10% canary:** flag on for 10% of new signups (`hash(user_id) mod 10 < 1`). Watch metrics 1 week.
3. **Phase 3 — full:** flag on for all users.

Each phase gated on the metrics above looking sane.

---

## 7. Implementation Team Plan (TeamCreate, all Opus)

**4 Opus agents, no Sonnet/Haiku.** `bypassPermissions` mode. Cross-QA mandatory before disassembly. Idle members write red-green tests targeting 80% coverage on new code OR wait for QA returns.

### 7.1 Team composition + delegation

| Agent | Owns (files) | Blocked-by | Idle behavior |
|---|---|---|---|
| **backend-cohort** | `scripts/build_cohorts.py`, `data/cohort_priors.json`, `app/services/cohort_service.py`, `app/api/auth_routes.py` (+ `/demographics`, `/cohort-profile`), `app/services/extraction_service.py` (cohort block in `_build_preferences_prompt`), `migrations/013_demographics_cohort.sql`, `app/api/admin_routes.py` (cohort metrics endpoints), `app/static/admin/cohort.html` | (none — starts immediately) | Write more red-green tests for `cohort_service` edge cases |
| **frontend-cohort** | `SmartCompareApp/src/components/DemographicsBottomSheet.tsx`, `SmartCompareApp/src/screens/ProfileScreen.tsx` (StyleProfileCard add), edit modal, dismissal/cooldown logic in app state, `src/i18n/en.json` + `ar.json` keys | backend-cohort: needs `PUT /demographics` + `GET /cohort-profile` schemas finalized | Write component tests for bottom sheet states + Profile card states |
| **test-cohort** | `tests/test_cohort_service.py` (matching, fallback, seeding), `tests/test_build_cohorts.py` (ETL: normalization, dedup, confidence flags), `tests/test_auth_demographics.py` (endpoints + RLS), `tests/test_extraction_cohort_prompt.py` (snapshot of injected block), `SmartCompareApp/__tests__/DemographicsBottomSheet.test.tsx` | Specs from backend + frontend agents (test stubs can start immediately from this design doc) | Add property-based tests + snapshot tests; expand coverage on existing personalization code |
| **qa-cohort** | Cross-reviews ALL 3 agents' work; runs `pytest tests/ -v` + `npx tsc --noEmit` after each commit; verifies metric instrumentation against real Supabase; signs off final feature; verifies 80% coverage on new code via `pytest --cov`; runs feature end-to-end manually with curl + iOS simulator | Each agent's "ready for QA" signal | Write integration tests spanning backend + frontend; profile slow paths |

### 7.2 Cross-QA matrix (mandatory before disassembly)

Each agent reviews ONE other agent's work — not their own:

```
backend-cohort     ──reviews──▶  frontend-cohort
frontend-cohort    ──reviews──▶  test-cohort
test-cohort        ──reviews──▶  backend-cohort
qa-cohort          ──reviews──▶  ALL THREE (final sign-off)
```

Reviewer checks: code correctness, design adherence, test coverage of THEIR area, naming/conventions per CLAUDE.md.

### 7.3 Send-back protocol

If a reviewer finds work subpar OR missed requirements:

1. Reviewer writes a structured review block: **what's wrong**, **what's missing**, **what's expected**, **suggested fix or pointer to design section**.
2. Owner agent receives review, fixes, returns for re-review.
3. Loop until reviewer approves.
4. **No agent disassembles until their work has at least one peer approval AND they've completed their assigned review.**

### 7.4 Disassembly gate (qa-cohort enforces)

Team disassembles ONLY when ALL of these are true:

- ✅ All 7 deliverables marked complete by their owner
- ✅ Cross-QA matrix has 4 approvals (3 peer + 1 from qa-cohort)
- ✅ `pytest tests/ -v -m "not (live_unit or live_db or integration)"` passes 100%
- ✅ `npx tsc --noEmit` passes 0 errors
- ✅ `pytest --cov=app/services/cohort_service --cov=scripts/build_cohorts --cov-fail-under=80` passes
- ✅ All 5 success metrics instrumented and visible in `/admin/cohort.html`
- ✅ End-to-end manual test: signup → first comparison → bottom sheet → submit demographics → verify cohort match in DB → verify verdict prompt has cohort block → verify Profile card shows persona → edit a preference → verify source flips to `"user_stated"`
- ✅ Migration `013_demographics_cohort.sql` documented as needs-manual-apply in CLAUDE.md
- ✅ Feature flag `ENABLE_COHORT_PERSONALIZATION` defaults to `false` (rollout per Section 6.6)

If ANY gate fails → team continues until resolved. **No premature disassembly.**

### 7.5 Idle behavior (explicit, not optional)

Any agent waiting for unblocking:

- **First choice:** write more red-green tests for the feature (target 80% coverage minimum, push toward 90% on the cohort matching algorithm specifically — it's the core).
- **Second choice:** write a draft of the next-session CLAUDE.md / MEMORY.md update for the new feature.
- **Last resort:** wait for QA return (only if no test surface remains).

**NEVER idle silently. NEVER skip tests because "the plan didn't mention them."**

### 7.6 Communication discipline

- Each agent posts STATUS UPDATES at: start of work, completion of each deliverable, when blocked, when sending back a review.
- Agents NEVER mark a task complete that has failing tests, partial implementation, or missing cross-QA approval.
- If an agent is told to disassemble but the gate isn't met → they refuse and report the gap to qa-cohort.

---

## 8. Out of Scope / Future Work

- **Continuous in-app survey collection (option E)** — turn Qaren itself into a survey instrument so cohorts grow organically. Defer until current cohort coverage shows clear gaps.
- **RAG over individual responses** — fuzzy similarity match to top-K past respondents instead of cohort modal. More complex; revisit if cohort approach plateaus.
- **Fine-tuning** — only viable at 5,000+ responses. Re-evaluate after Phase E.
- **Multi-page progressive profile capture** — beyond 3 demographic fields. Defer; current bottom sheet captures the 80/20 signal.
- **Cross-country cohorts** — surveys are Bahrain-only currently. When expanding to other GCC markets, re-run ETL with country in the cohort key.
- **Cohort drift detection** — automated alerting when modal answers shift significantly between ETL runs. Useful at 1000+ responses; premature now.

---

## 9. Open Questions (resolve during implementation)

1. **Should `lifestyle` field ever be seeded?** Currently left empty (no clean survey signal). If a clean mapping emerges from open-text analysis later, revisit.
2. **`identity` field in cohort key?** Currently excluded for sensitivity. If observed cohort match rate is too low (<40%), consider adding identity as a fallback tier.
3. **Re-match all users when `cohort_priors.json` changes?** Background job recommended but exact trigger (deploy hook? manual admin endpoint?) TBD during implementation.
4. **Behavioral layer weight adjustment?** Recommendation: `user_stated` = ±30%, `inferred` = ±15%. Test in canary phase before locking in.

---

## Appendix A: Survey Field → Cohort Field Mapping (Arabic→English Normalization)

To be expanded by `backend-cohort` during ETL implementation. Sample:

| Arabic | English |
|---|---|
| إلكترونيات | Electronics |
| منتج أزياء - تجميل | Fashion-Beauty |
| منتج صحي | Health product |
| الجودة | Quality |
| السعر | Price |
| العلامة التجارية | Brand |
| القيمة مقابل السعر | Value for money |
| الضمان أو خدمة ما بعد البيع | Warranty / After-sales |
| محافظة العاصمة | Capital |
| المحافظة الشمالية | Northern |
| محافظة المحرق | Muharraq |
| المحافظة الجنوبية | Southern |
| بحريني - بحرينية | Bahraini |
| أنثى | Female |
| ذكر | Male |
| من 25 إلى أقل من 50 دينار بحريني | 25-50 BHD |
| من 50 إلى أقل من 100 دينار بحريني | 50-100 BHD |
| أقل من 25 دينار بحريني | <25 BHD |
| من 100 إلى أقل من 250 دينار بحريني | 100-250 BHD |

(Build script must fail loudly on any unmapped Arabic value.)

---

**End of design document.**

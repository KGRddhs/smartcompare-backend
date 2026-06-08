# Bundle (B) Phase B.1 — DB Schema Audit & Migration Preflight

**Owner:** L4-prompts-eval (preflight authoring)
**Branch:** `wip/A-L4-goldtruth-seed-idle-time`
**Plan reference:** `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` (Sprint A → Bundle B handoff)
**Design reference:** `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 12 (Phasing)
**Author date:** 2026-06-08

---

## 1. Purpose

Phase B.1 of Bundle (B) sets up the DB + observability schema for the
Living Prompt System (§ 6 of design doc) — 4 new tables, 3 new columns
on `comparison_feedback`, plus an audit of the current schema against
RLS / FK / index hygiene. This preflight inventories live state from
the **production Supabase project** (`qulajmyxdbdkchvecmvc`) and
proposes per-table migration SQL skeletons so B.1 can land in 3–5
sequenced migrations rather than one fragile blob.

## 2. Current schema inventory (live production query)

Captured via Supabase MCP `list_tables` + `information_schema.columns`
+ `pg_indexes` queries on 2026-06-08.

### 2.1 Tables present (18 in `public` schema)

| Table | RLS | Rows |
|---|---|---|
| `users` | enabled | 16 |
| `comparisons` | enabled | 15 |
| `comparison_feedback` | enabled | 0 |
| `user_events` | enabled | 49 |
| `user_usage` | enabled | 0 |
| `admin_audit_log` | enabled | 266 |
| `search_logs` | enabled | 3,192 |
| `product_specs` | enabled | 129 |
| `product_prices` | enabled | 605 |
| `product_reviews` | enabled | 124 |
| `referral_invites` | enabled | 1 |
| `referral_redemptions` | enabled | 1 |
| `deep_review_credits` | enabled | 2 |
| `re_engagement_events` | enabled | 0 |
| `bahrain_approved_drugs` | enabled | 0 |
| `rating_cache` | enabled | 0 |
| `products` | **DISABLED** | 0 |
| `comparisons_cache` | **DISABLED** | 0 |

**🚨 Critical advisory (surface to team-lead before B.1 lands):**
`public.products` and `public.comparisons_cache` have **RLS disabled**
— anyone with the anon key can read or modify every row. Both tables
are empty today (0 rows). Action options:

- Drop both tables if confirmed unused (no production code paths).
- OR `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` AND author policies
  (enabling RLS without policies blocks all access).

This MUST be resolved before B.1 ships — it is a security boundary
issue independent of the new tables we're adding.

### 2.2 `users` columns (currently 22)

Authentication / identity:
- `id` uuid PK
- `email`, `display_name`, `auth_provider` text
- `subscription_tier`, `subscription_expires_at` (freemium tier)

Personalization (existing — relevant to B.1):
- `preferences` jsonb default `'{}'::jsonb`  → **becomes source for `user_preference_history`**
- `preferences_completed` boolean default false
- `behavior_profile` jsonb default `'{}'::jsonb` (decay-weighted, existing)
- `demographics_profile` jsonb (Migration 013, existing)
- `demographics_dismissed_count`, `demographics_dismissed_at`

Referrals:
- `referral_code`, `lifetime_invites_consumed`, `referral_bonus_*`,
  `device_fingerprint_hash`

Engagement / push:
- `expo_push_token`, `notifications_enabled`, `last_comparison_at`
- `attribution_source`, `lifetime_comparisons_used`

### 2.3 `comparison_feedback` columns (currently 7)

```
id              uuid PK
user_id         uuid (FK to users.id, RLS-scoped)
comparison_id   uuid (FK to comparisons.id)
useful          boolean NOT NULL          ← thumbs up/down
mattered_most   text[] (default {})       ← multi-select chips
change_suggestion text                    ← optional free-form
created_at      timestamptz default now()
```

**Missing per B.1 spec (design doc § 6 — eval loop):**

- `winner_correct` — 3-state: `correct | wrong | unsure`
- `price_correct` — 3-state: `correct | wrong | unsure`
- `specs_correct` — 3-state: `correct | wrong | unsure`

These feed the production 5% sample → eval-loop comparison
("Production: 5% sample scored against secondary source / failures →
root cause → prompt update").

### 2.4 `user_events` columns (currently 6)

```
id            uuid PK
user_id       uuid (FK)
event_type    text NOT NULL              ← e.g. comparison_started, share_tapped
event_data    jsonb default '{}'
comparison_id uuid (FK, nullable)
session_id    text
created_at    timestamptz default now()
```

Indexes already present: `(user_id)`, `(event_type)`, `(created_at)`.

### 2.5 `comparisons` columns (currently 9)

```
id                  uuid PK
user_id             uuid (FK)
full_response       jsonb                  ← the complete /text/compare payload
query               text
input_type          text default 'text'
product_names       text[]                 ← denormalised, indexed GIN
created_at          timestamptz
share_token         text UNIQUE            ← 22-char URL-safe
schema_version      integer NOT NULL default 2
```

**Note:** `schema_version=2` denotes a renderable payload (v1 = legacy
/ hidden). The B.1 work does NOT change this; eval reads must filter
on `schema_version=2`.

### 2.6 Index inventory (relevant FKs)

- `comparisons (user_id, schema_version, created_at DESC)` — composite, used by history list
- `comparisons (user_id, created_at DESC)` — older, partial-redundant
- `comparisons GIN(product_names)` — search
- `comparisons GIN(to_tsvector('english', query))` — full-text
- `user_events (user_id)`, `(event_type)`, `(created_at)` — single-column
- `users` device-fingerprint indexed in **two places** —
  `idx_users_device_fingerprint_active` + `idx_users_device_fp` (DUPLICATE — recommend dropping one in B.1)

### 2.7 Applied migrations (most recent 5)

```
20260512185013  023_referral_lifetime_cap
20260518000033  024_top_tier_budget
20260523121041  026_backfill_renderable_v1_comparisons
20260523134722  025_delete_user_cascade_completeness
(none since)
```

Next migration number → **027** for the first B.1 migration.

## 3. Proposed B.1 schema changes

### 3.1 New tables (4 total)

| Table | Purpose | FKs | Est. rows / month |
|---|---|---|---|
| `user_preference_history` | Append-only log of `users.preferences` jsonb snapshots so eval loop can correlate "preferences changed at T1 → verdicts at T2 felt better/worse" | `user_id → users(id)` | ~100/user × 16 users ≈ 1.6k init, grows linearly with comparisons |
| `pain_workflow_events` | Per-comparison observed pain-workflow signals (abandonment, re-query within 5min, share+immediate-purchase) — feeds the survey-weighted prior aggregator in (B) Phase B.2 | `user_id → users(id)`, `comparison_id → comparisons(id)` | ~1-2 events per comparison, 1.5x growth vs comparisons table |
| `verdict_critiques` | Self-critique scores from the GPT-4o-mini critique pass (design § 6 — bias, vagueness, hedging-language, missing-citation, pain-workflow-alignment per axis 0-10) | `comparison_id → comparisons(id)` | 1 row per shipped verdict, 1:1 with comparisons |
| `eval_runs` | Aggregate eval-loop sessions (CI runs of the 50/200-query gold set, with per-axis pass rates + drift detection) | none (no per-user data) | ~5-10/week (per PR + nightly) |

### 3.2 New `comparison_feedback` columns (3)

Each is a 3-state enum (`correct` / `wrong` / `unsure`), nullable
(early feedback doesn't require all 3). CHECK constraints enforce the
enum values without needing a separate type.

## 4. Migration SQL skeletons

### 4.1 Migration 027 — `add_comparison_feedback_correctness_columns`

```sql
-- 2026-06-XX  Migration 027 — Bundle B Phase B.1
-- Adds 3 per-axis correctness signals to comparison_feedback so the
-- eval loop can correlate user-reported wins/losses with the deterministic
-- scoring/factual outputs. Each is nullable so the existing fast-path
-- thumbs-up/down feedback continues to work without extra prompting.

ALTER TABLE public.comparison_feedback
  ADD COLUMN IF NOT EXISTS winner_correct text NULL,
  ADD COLUMN IF NOT EXISTS price_correct  text NULL,
  ADD COLUMN IF NOT EXISTS specs_correct  text NULL;

ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_winner_correct_check
    CHECK (winner_correct IS NULL OR winner_correct IN ('correct','wrong','unsure'));

ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_price_correct_check
    CHECK (price_correct IS NULL OR price_correct IN ('correct','wrong','unsure'));

ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_specs_correct_check
    CHECK (specs_correct IS NULL OR specs_correct IN ('correct','wrong','unsure'));

-- Index for eval queries that filter on any-non-null per-axis correctness.
CREATE INDEX IF NOT EXISTS idx_comparison_feedback_correctness_present
  ON public.comparison_feedback (created_at DESC)
  WHERE (winner_correct IS NOT NULL
      OR price_correct  IS NOT NULL
      OR specs_correct  IS NOT NULL);
```

Rollback (see `migrations/rollback/027_*.sql`):

```sql
ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_winner_correct_check,
  DROP CONSTRAINT IF EXISTS comparison_feedback_price_correct_check,
  DROP CONSTRAINT IF EXISTS comparison_feedback_specs_correct_check;
DROP INDEX IF EXISTS public.idx_comparison_feedback_correctness_present;
ALTER TABLE public.comparison_feedback
  DROP COLUMN IF EXISTS winner_correct,
  DROP COLUMN IF EXISTS price_correct,
  DROP COLUMN IF EXISTS specs_correct;
```

### 4.2 Migration 028 — `create_user_preference_history`

```sql
CREATE TABLE IF NOT EXISTS public.user_preference_history (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  preferences     jsonb NOT NULL,          -- snapshot of users.preferences at write time
  change_source   text  NOT NULL,          -- 'onboarding' | 'edit_profile' | 'cohort_inference' | 'system_default'
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_preference_history ENABLE ROW LEVEL SECURITY;

-- User can read own history; service role can write any.
CREATE POLICY upref_history_own_select
  ON public.user_preference_history
  FOR SELECT USING (auth.uid() = user_id);

-- Inserts go through service role only (no INSERT policy for anon/authenticated)
-- so the audit trail is tamper-resistant from the client.

CREATE INDEX idx_upref_history_user_created
  ON public.user_preference_history (user_id, created_at DESC);

CREATE INDEX idx_upref_history_change_source
  ON public.user_preference_history (change_source);
```

### 4.3 Migration 029 — `create_pain_workflow_events`

```sql
CREATE TABLE IF NOT EXISTS public.pain_workflow_events (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  comparison_id   uuid NULL  REFERENCES public.comparisons(id) ON DELETE SET NULL,
  workflow_name   text NOT NULL,           -- canonical: close_option_paralysis | too_many_specs | etc (must match data/pain_workflow_priors.json)
  signal_type     text NOT NULL,           -- 'abandonment' | 'requery_within_5min' | 'share_then_no_purchase' | 'long_dwell'
  signal_payload  jsonb NULL,              -- per-signal context (dwell_ms, requery_text, etc)
  created_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT pwe_workflow_name_check CHECK (workflow_name IN (
    'close_option_paralysis',
    'too_many_specs',
    'value_budget_uncertainty',
    'trust_paralysis',
    'post_decision_regret',
    'brand_loyalty_vs_evidence',
    'warranty_aftersales_missing',
    'decision_speed'
  ))
);

ALTER TABLE public.pain_workflow_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY pwe_own_select
  ON public.pain_workflow_events
  FOR SELECT USING (auth.uid() = user_id);

-- Anon insert allowed via service-role write only (no client INSERT).

CREATE INDEX idx_pwe_workflow_name        ON public.pain_workflow_events (workflow_name);
CREATE INDEX idx_pwe_user_workflow_time   ON public.pain_workflow_events (user_id, workflow_name, created_at DESC);
CREATE INDEX idx_pwe_comparison_id        ON public.pain_workflow_events (comparison_id);
```

### 4.4 Migration 030 — `create_verdict_critiques`

```sql
CREATE TABLE IF NOT EXISTS public.verdict_critiques (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  comparison_id      uuid NOT NULL REFERENCES public.comparisons(id) ON DELETE CASCADE,
  -- self-critique axes (0..10 ints; nullable so partial critiques can ship)
  bias_score                 integer NULL CHECK (bias_score                BETWEEN 0 AND 10),
  vagueness_score            integer NULL CHECK (vagueness_score           BETWEEN 0 AND 10),
  hedging_score              integer NULL CHECK (hedging_score             BETWEEN 0 AND 10),
  missing_citation_score     integer NULL CHECK (missing_citation_score    BETWEEN 0 AND 10),
  pain_workflow_align_score  integer NULL CHECK (pain_workflow_align_score BETWEEN 0 AND 10),
  -- if any axis < 7, the verdict was regenerated; record what was rewritten
  regenerated                boolean NOT NULL DEFAULT false,
  regen_reason               text    NULL,
  -- model + cost trace for budget audit
  critic_model               text NOT NULL,
  critic_tokens_used         integer NULL,
  created_at                 timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.verdict_critiques ENABLE ROW LEVEL SECURITY;

-- No SELECT policy by default — read access via service role only
-- (critiques are internal eval data, not user-visible).

CREATE INDEX idx_vc_comparison_id   ON public.verdict_critiques (comparison_id);
CREATE INDEX idx_vc_regenerated     ON public.verdict_critiques (regenerated) WHERE regenerated = true;
CREATE INDEX idx_vc_low_align       ON public.verdict_critiques (pain_workflow_align_score)
  WHERE pain_workflow_align_score IS NOT NULL AND pain_workflow_align_score < 7;
```

### 4.5 Migration 031 — `create_eval_runs`

```sql
CREATE TABLE IF NOT EXISTS public.eval_runs (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_kind           text NOT NULL,            -- 'ci_pr' | 'nightly' | 'manual' | 'staging_smoke'
  gold_truth_version text NOT NULL,            -- e.g. data/validation_gold_truth.json schema_version + hash
  queries_total      integer NOT NULL,
  queries_passing    integer NOT NULL,         -- per-query weighted_score >= 0.80
  pass_rate          numeric(5,4) NOT NULL,    -- redundant w/ above for fast filter
  axis_avg_price     numeric(5,4) NULL,
  axis_avg_specs     numeric(5,4) NULL,
  axis_avg_winner    numeric(5,4) NULL,
  axis_avg_factual   numeric(5,4) NULL,
  wall_p50_ms        integer NULL,
  wall_p95_ms        integer NULL,
  metadata           jsonb NULL,                -- branch SHA, env, runner version, failing query IDs
  created_at         timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT eval_runs_run_kind_check CHECK (run_kind IN ('ci_pr','nightly','manual','staging_smoke'))
);

ALTER TABLE public.eval_runs ENABLE ROW LEVEL SECURITY;
-- Service-role only — eval results are internal observability.

CREATE INDEX idx_eval_runs_kind_created  ON public.eval_runs (run_kind, created_at DESC);
CREATE INDEX idx_eval_runs_pass_rate     ON public.eval_runs (pass_rate);
```

## 5. Migration sequence — parallel vs blocking

```
┌──────────────────────────────────────┐
│ 027  comparison_feedback +3 cols     │ blocking — no FKs out, no peer deps
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ 028  user_preference_history          │   parallel — FK to users (independent)
│ 029  pain_workflow_events             │   parallel — FK to users + comparisons (independent)
│ 030  verdict_critiques                │   parallel — FK to comparisons (independent)
│ 031  eval_runs                        │   parallel — no FKs (independent)
└──────────────────────────────────────┘
```

**Recommended order:** ship 027 FIRST (smallest, lowest risk, easy
rollback), then 028-031 can land in a single MCP apply_migration batch
since they have no peer dependencies.

**Estimated DDL run-time per migration:** <2s each — small tables,
no large data backfill, indexes built fresh on empty.

## 6. RLS posture summary

All proposed new tables: **RLS enabled + SELECT policy gated on `auth.uid() = user_id`**
where user-scoped; **service-role-only writes** for tamper-resistance
on observability tables (`pain_workflow_events`, `verdict_critiques`,
`eval_runs` — these are filled by backend cron / inline middleware, not
client SDKs).

Pre-B.1 cleanup (separate from B.1 migrations themselves):

1. **Resolve RLS-disabled advisory** on `products` + `comparisons_cache`
   (drop or enable+policy — currently both 0-row, decision required).
2. **Drop duplicate `idx_users_device_fingerprint_active` OR
   `idx_users_device_fp`** — both index the same column with the same
   `WHERE` predicate. Pick one canonical name.

## 7. Application-layer follow-ups (B.1 sequence)

After DDL ships:

1. **`app/services/feedback_service.py`** — add 3 new optional fields
   (`winner_correct`, `price_correct`, `specs_correct`) to the Pydantic
   request model + DB insert. Frontend wiring is B.3.
2. **`app/services/pain_workflow_service.py`** — NEW, mirror of
   `pain_workflow_loader.py` shipped in A-L4.2. Reads `users.preferences`
   diff from `user_preference_history` to detect change events.
   Inserts into `pain_workflow_events`.
3. **`app/services/verdict_critique_service.py`** — NEW, the
   GPT-4o-mini self-critique loop (design § 6). Wraps
   `generate_comparison` post-call, runs critique, regenerates on
   low-axis-score, writes to `verdict_critiques`.
4. **`scripts/cron_eval.py`** — NEW, nightly run of
   `scripts/run_validation_matrix.py` against the prod endpoint with
   `eval_runs` write.

## 8. Data backfill / migration burden

- `users.preferences` → `user_preference_history` initial backfill:
  one `INSERT INTO user_preference_history (user_id, preferences,
  change_source) SELECT id, preferences, 'initial_backfill' FROM users
  WHERE preferences != '{}'::jsonb;` runs in <1s on 16 rows.
- `comparison_feedback`: 0 rows today, no historical correctness signals
  to backfill — new columns are NULL-default.
- `comparisons.full_response.scoring_v2` already includes the new Lane 1
  fields (`build_dimensions_v2`, `factual_verdict`, `confidence_legs`)
  — eval loop reads these directly from `full_response` rather than
  needing a denormalised eval cache.

## 9. Open questions for team-lead

1. **Drop `products` + `comparisons_cache`** vs add RLS policies?
   Both 0-row. Drop would be cleaner.
2. **Does `verdict_critiques` need a user-facing read path?** Current
   design suggests NO (internal observability), but if we want to
   surface "this verdict was regenerated 2x for quality" to the user
   in a transparency tab, we need a SELECT policy.
3. **Eval `gold_truth_version`** — adopt git SHA + JSON schema_version
   composite, or content-hash the gold-truth file? Composite is
   simpler; content-hash detects in-place edits.
4. **`change_source` enum on `user_preference_history`** — final list?
   I've proposed `onboarding | edit_profile | cohort_inference | system_default`.
   Adding `bulk_import` for survey-driven backfill in (B) Phase B.6?

## 10. Sprint A handoff readiness

This document is preflight only — no migrations applied. When (B)
Phase B.1 spins up:

1. Pull this doc into `docs/plans/2026-06-XX-bundle-b-phase1-db-schema.md`
2. Decide § 9 open questions
3. Apply migrations 027 → 028-031 (027 first, then parallel batch)
4. Resolve the RLS-disabled advisory + dedup the device-fingerprint index
5. Pre-apply rollback files into `migrations/rollback/` alongside

Sprint A's gold-truth + validation matrix work integrates naturally —
`eval_runs.gold_truth_version` references the same
`data/validation_gold_truth.json` `_metadata.schema_version` field
shipped in L4.3.

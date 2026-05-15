---
name: qaren-cohort
description: Use when touching cohort personalization, demographics endpoint, /api/v1/auth/demographics or /cohort-profile, cohort_priors.json, build_cohorts.py, cohort_service.py, ENABLE_COHORT_PERSONALIZATION flag, or admin cohort dashboard. Covers survey-driven priors, hierarchical fallback match, and privacy invariant.
last_verified: 2026-05-16
update_when_changing:
  - app/services/cohort_service.py
  - scripts/build_cohorts.py
  - data/cohort_priors.json
  - app/api/auth_routes.py (demographics / cohort-profile / preferences endpoints)
  - migrations touching users.demographics_profile
---

# Qaren Cohort Personalization

## Cohort personalization (Phase 1 LIVE 2026-05-05)

Survey-driven priors from ~400 Fillout responses bootstrap personalization for new/anonymous users. Feature flag `ENABLE_COHORT_PERSONALIZATION` is **ON in production**; code default remains `false`. Flag is global — no per-user gating yet.
- **PUT /api/v1/auth/demographics** (auth, 5/min) — age_group/gender/governorate/language/country (all optional). Auto-derives language from Accept-Language and country from CF-IPCountry. Stores `users.demographics_profile` JSONB. Seeds preferences from cohort if user has none/all-inferred — never overwrites `user_stated`.
- **GET /api/v1/auth/cohort-profile** + **PUT /api/v1/auth/preferences** (`_sources` flips `user_stated` on edit).
- **Privacy invariant:** NO raw age/gender/identity in prompt — only country/language/governorate thin context + aggregate findings. Active when `match_quality ∈ {exact, broadened_governorate, broadened_language}` AND flag on.
- **Cohort match is exact-case** — `_key_part()` doesn't normalize. Values must match `cohort_priors.json` keys exactly: `age_group: "25-34"`, `gender: "Male"/"Female"`, `governorate: "Capital"/"Muharraq"/"Northern"/"Southern"`, `language: "English"/"Arabic"/"Both equally"`, `country: "Bahrain"`. Re-run `python -m scripts.build_cohorts` to regenerate priors. Admin dashboard at `/admin/cohort.html`.

## Hierarchical fallback match

`cohort_service.py` singleton loads `data/cohort_priors.json` once at startup. Match cascade:
1. **exact** — all 5 keys (age + gender + governorate + language + country) match
2. **broadened_governorate** — drop governorate, retry
3. **broadened_language** — drop language, retry
4. **broadened_age** — drop age_group, retry
5. **population** — population-level fallback aggregate

Privacy invariant kicks in only at `exact`, `broadened_governorate`, `broadened_language` levels.

## Implementation gotchas (Session 41)

- **slowapi `@limiter.limit` decorator** validates `isinstance(request, Request)` → breaks unit tests passing MagicMock. Solved via `RATE_LIMITER_ENABLED=false` env var read by Limiter constructor (set in tests/conftest.py). Production absence of var leaves limiter active.
- **Extraction prompt tests** assume `ENABLE_COHORT_PERSONALIZATION=true` by default during tests. Only `test_default_flag_state_is_false` uses `monkeypatch.delenv` to verify the production-default off path. Set in conftest with `setdefault` so individual tests can override.
- **VALID_PRIORITIES extended:** original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). `VALID_BRAND_ATTITUDE` adds `trust_known_brands`. Validator extended without breaking existing 8.
- **ETL `normalize_value()`** must NOT flag all non-ASCII as Arabic — English values can contain NBSP (e.g. `Fashion or Beauty\u00a0 item` from Fillout). Only flag chars in U+0600..U+06FF (Arabic block).
- **cohort_priors.json IS committed** (build artifact); raw survey CSVs `data/surveys/*.csv` are gitignored (PII in email/phone columns).
- **Coverage targets achieved:** cohort_service.py 93%, build_cohorts.py 91% (target was 80%).
- **Multi-agent commit bundling gotcha:** other agents on the team committed my staged files between my `git add` and `git commit`. Files end up bundled into someone else's commit (different message). Verify via `git log --diff-filter=A -- <file>` rather than panicking when `git status` shows clean.

## Sources (verify against current code before recommending changes)

- `app/services/cohort_service.py` — singleton, `match_cohort()`, `seed_preferences()`, `get_display_profile()`, `should_seed()`
- `scripts/build_cohorts.py` — ETL: Arabic→English normalization, 388 valid responses → 24 specific cohorts + 29 fallback aggregates
- `app/api/auth_routes.py` — `PUT /demographics` (5/min), `GET /cohort-profile`, `PUT /preferences` (source-flip)
- `data/cohort_priors.json` — generated priors (re-run `python -m scripts.build_cohorts` to regenerate)
- Admin dashboard: `/admin/cohort.html`
- Plan + design: `docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md`, `docs/superpowers/plans/2026-05-03-survey-cohort-personalization.md`

# CLAUDE.md Slimming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Drop CLAUDE.md from 51.6k → ~28k chars by extracting 4 self-contained subsystems into project-local skills and moving bundle history to a lazy doc, while preserving Claude's ability to find context on-demand.

**Architecture:** Three mechanisms — project-local skills auto-surfaced via system-reminder, lazy reference doc pointed to by a breadcrumb, trimmed CLAUDE.md core. Skills load on-demand when description matches user intent; bundle history loads only when explicitly relevant. Cross-cutting patterns (price pipeline, auth, security hardening) stay inline per Session 34 finding.

**Tech Stack:** Plain Markdown files + YAML frontmatter for skills. No code changes. Git for version control.

**Design Doc:** `docs/plans/2026-05-16-claude-md-slimming-design.md` (committed at 55b7000)

---

## Reference: Exact line ranges in current CLAUDE.md

| Section | Lines | To go to |
|---|---|---|
| Deterministic scoring (zero cost) | 198-204 | qaren-scoring skill |
| Prompt personalities + trust validation | 206-207 | qaren-scoring skill |
| Personalization (zero extra cost) | 225-231 | qaren-scoring skill |
| Cohort personalization | 233-238 | qaren-cohort skill |
| Smart Decision Referrals | 259-267 | qaren-referrals skill |
| Bundle A Pre-launch P0 | 269-277 | docs/SESSION_BUNDLES.md |
| Bundle B/C/D Consolidated | 279-289 | docs/SESSION_BUNDLES.md |
| Bundle E Results Quality Overhaul | 291-303 | docs/SESSION_BUNDLES.md |
| EAS Update infrastructure | 305-310 | qaren-eas-deploy skill |

---

### Task 1: Baseline capture

**Files:**
- No file changes. Capture pre-state metrics for comparison.

**Step 1: Capture current char count + line count**

```bash
wc -c CLAUDE.md
wc -l CLAUDE.md
```

Expected: ~51,586 chars, ~370 lines.

**Step 2: Verify clean working tree**

```bash
git status
```

Expected: only ongoing unrelated changes (`.claude/settings.local.json`, `SmartCompareApp/package-lock.json`). No staged Markdown changes.

**Step 3: Record baseline in TODO scratchpad** (mental note only — these numbers feed into Task 8 verification)

No commit for this task.

---

### Task 2: Create `docs/SESSION_BUNDLES.md` with Bundle A/B/C/D/E content

**Files:**
- Create: `docs/SESSION_BUNDLES.md`

**Step 1: Create the file**

Write `docs/SESSION_BUNDLES.md` with this exact structure:

```markdown
# Qaren Session Bundle History

> Historical context for Bundles A, B/C/D, and E. Linked from CLAUDE.md.
> Read this when investigating regressions, understanding why a subsystem looks the way it does, or tracing deferred follow-ups across bundles.

## Bundle A Pre-launch P0 (PR #3 merged 2026-05-11 — `f9bf38f`)

<copy lines 270-277 of CLAUDE.md verbatim, preserving bullet structure>

---

## Bundle B/C/D Consolidated (PR #4, Session 46, 2026-05-12)

<copy lines 280-289 of CLAUDE.md verbatim, preserving bullet structure>

---

## Bundle E Results Quality Overhaul (PR #5 merged 2026-05-13 — `00a2ec1`)

<copy lines 292-303 of CLAUDE.md verbatim, preserving bullet structure>
```

**Important:** Copy the body lines (everything after each `###` header), not the `###` header lines themselves. The H2 headers in the new file replace the H3 headers from CLAUDE.md. Preserve ALL bullet text exactly — these are load-bearing implementation notes.

**Step 2: Verify char count**

```bash
wc -c docs/SESSION_BUNDLES.md
```

Expected: ~13,000 chars (give or take 500 for the new H2 headers + intro).

**Step 3: Verify content integrity**

```bash
grep -c "Bundle A\|Bundle B/C/D\|Bundle E\|Bundle F" docs/SESSION_BUNDLES.md
```

Expected: at least 8 matches (3 H2 headers + several internal cross-references).

**Step 4: Commit**

```bash
git add docs/SESSION_BUNDLES.md
git commit -m "$(cat <<'EOF'
docs: extract Bundle A/B/C/D/E history into SESSION_BUNDLES.md

Part of CLAUDE.md slimming (design: 2026-05-16). Bundle history is
historical context — read when investigating regressions, not in every
session. CLAUDE.md breadcrumb to be added in a later commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Create `qaren-referrals` skill

**Files:**
- Create: `.claude/skills/qaren-referrals/SKILL.md`

**Step 1: Create directory and file**

```bash
mkdir -p .claude/skills/qaren-referrals
```

Write `.claude/skills/qaren-referrals/SKILL.md`:

```markdown
---
name: qaren-referrals
description: Use when touching referral invites, share links, /api/v1/referrals/* routes, invite codes (QR-XXXXXX), Loop 1 / Loop 2 flow, redemption chain, abuse detection, device-fingerprint caps, bonus expiry, or referral_invites / referral_redemptions tables. Covers Smart Decision Referrals + Bundle B/C/D lifetime-cap overhaul.
last_verified: 2026-05-16
update_when_changing:
  - app/services/referral_service.py
  - app/services/abuse_detection_service.py
  - app/api/referral_routes.py
  - migrations touching referral_invites or referral_redemptions
  - SmartCompareApp/src/services/playInstallReferrerService.ts
  - SmartCompareApp/src/services/clipboardFallbackService.ts
---

# Qaren Referral System

## Smart Decision Referrals (Phase 1 LIVE 2026-05-05)

<copy lines 260-267 of CLAUDE.md verbatim — all bullets under "Smart Decision Referrals">

## Bundle B/C/D Referral Hardening (Session 46, Migration 023)

- **Cap moved to 3 LIFETIME per device** (was 3/week per user). Cross-account aggregation via `_referrer_device_lifetime_count` fingerprint SUM.
- **Decrement at receiver signup**, not at share time. Fail-OPEN on DB error (design § 6.1).
- **Share-button disabled at 3 lifetime** with gift-framing copy (`referrals.share.maxReached`).
- **Bonus expiry: 7 days** for Loop 2 (Loop 1 `deep_review_expires_at` stays at 3 days; existing rows unchanged).
- **Hybrid DIY install-survival** (Branch.io DROPPED): Android Play Install Referrer + iOS clipboard fallback (Apple-review-safe — consent banner BEFORE read) + Cloudflare Worker at `qaren.app/r/{code}`.
- **Canonical invite-code regex:** `^QR-[A-HJ-NP-Z2-9]{6}$` shared across `playInstallReferrerService.ts`, `clipboardFallbackService.ts`, `attribution_service.py`, `auth_routes._INVITE_CODE_RE`. Defense-in-depth at every layer.

## Sources (verify against current code before recommending changes)

- `app/services/referral_service.py` — invite creation, `link_invite_to_user`, `try_trigger_loop2`, `resolve_code_to_invite_id`
- `app/services/abuse_detection_service.py` — `evaluate_invite()` priority: SAME_DEVICE > DISPOSABLE_EMAIL > BELOW_REAL_ACTION_THRESHOLD
- `app/api/referral_routes.py` — 4 endpoints under `/api/v1/referrals/*`
- `migrations/023_*.sql` — `users.lifetime_invites_consumed` + partial idx on `device_fingerprint_hash`
- Plans: `docs/plans/2026-05-05-smart-referral-system.md`, `docs/plans/2026-05-12-bundle-bcd-consolidated-design.md`
```

**Step 2: Verify file structure**

```bash
ls -la .claude/skills/qaren-referrals/
wc -c .claude/skills/qaren-referrals/SKILL.md
```

Expected: file exists, ~3,500 chars.

**Step 3: Verify frontmatter parses**

```bash
head -20 .claude/skills/qaren-referrals/SKILL.md
```

Expected: YAML frontmatter with `name`, `description`, `last_verified`, `update_when_changing` fields visible.

**Step 4: Commit**

```bash
git add .claude/skills/qaren-referrals/SKILL.md
git commit -m "$(cat <<'EOF'
docs(skills): add qaren-referrals project-local skill

Extracts Smart Decision Referrals + Bundle B/C/D referral hardening from
CLAUDE.md into an on-demand skill. Loads only when referral routes /
invite codes / Loop 1+2 flow are mentioned. Sources block + maintenance
checklist mitigate staleness.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Create `qaren-cohort` skill

**Files:**
- Create: `.claude/skills/qaren-cohort/SKILL.md`

**Step 1: Create directory and file**

```bash
mkdir -p .claude/skills/qaren-cohort
```

Write `.claude/skills/qaren-cohort/SKILL.md`:

```markdown
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

<copy lines 234-238 of CLAUDE.md verbatim — all bullets under "Cohort personalization">

## Implementation gotchas (Session 41)

- **slowapi `@limiter.limit` decorator** validates `isinstance(request, Request)` → breaks unit tests passing MagicMock. Solved via `RATE_LIMITER_ENABLED=false` env var read by Limiter constructor (set in tests/conftest.py). Production absence of var leaves limiter active.
- **Extraction prompt tests** assume `ENABLE_COHORT_PERSONALIZATION=true` by default during tests. Only `test_default_flag_state_is_false` uses `monkeypatch.delenv` to verify the production-default off path.
- **VALID_PRIORITIES extended:** original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). `VALID_BRAND_ATTITUDE` adds `trust_known_brands`. Validator extended without breaking existing 8.
- **ETL `normalize_value()`** must NOT flag all non-ASCII as Arabic — English values can contain NBSP (e.g. `Fashion or Beauty\u00a0 item` from Fillout). Only flag chars in U+0600..U+06FF (Arabic block).
- **cohort_priors.json IS committed** (build artifact); raw survey CSVs `data/surveys/*.csv` are gitignored (PII in email/phone columns).
- **Coverage targets achieved:** cohort_service.py 93%, build_cohorts.py 91% (target was 80%).

## Sources (verify against current code before recommending changes)

- `app/services/cohort_service.py` — singleton, `match_cohort()`, `seed_preferences()`, `get_display_profile()`, `should_seed()`
- `scripts/build_cohorts.py` — ETL: Arabic→English normalization, 388 valid responses → 24 specific cohorts + 29 fallback aggregates
- `app/api/auth_routes.py` — `PUT /demographics` (5/min), `GET /cohort-profile`, `PUT /preferences` (source-flip)
- `data/cohort_priors.json` — generated priors (re-run `python -m scripts.build_cohorts` to regenerate)
- Admin dashboard: `/admin/cohort.html`
- Plan + design: `docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md`, `docs/superpowers/plans/2026-05-03-survey-cohort-personalization.md`
```

**Step 2: Verify char count**

```bash
wc -c .claude/skills/qaren-cohort/SKILL.md
```

Expected: ~2,500 chars.

**Step 3: Commit**

```bash
git add .claude/skills/qaren-cohort/SKILL.md
git commit -m "$(cat <<'EOF'
docs(skills): add qaren-cohort project-local skill

Extracts cohort personalization deep-dive from CLAUDE.md into an
on-demand skill. Loads only when demographics / cohort flag /
cohort_priors are mentioned. Includes Session 41 implementation
gotchas + sources for staleness defense.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Create `qaren-scoring` skill (combines 3 inline sections)

**Files:**
- Create: `.claude/skills/qaren-scoring/SKILL.md`

**Step 1: Create directory and file**

```bash
mkdir -p .claude/skills/qaren-scoring
```

Write `.claude/skills/qaren-scoring/SKILL.md`:

```markdown
---
name: qaren-scoring
description: Use when touching deterministic scoring, scoring_service.py, value badges, tradeoff pairs, dimension winners, personalization caps (plus or minus 30/10/5 percent), prompt personalities, trust validation, behavioral profiles, behavior_service.py, scoring_method enum, or the three-layer personalization system.
last_verified: 2026-05-16
update_when_changing:
  - app/services/scoring_service.py
  - app/services/prompt_personalities.py
  - app/services/trust_validation_service.py
  - app/services/behavior_service.py
  - app/models/scoring_v2.py
---

# Qaren Scoring + Personalization System

## Deterministic scoring (zero cost)

<copy lines 199-204 of CLAUDE.md verbatim — all bullets under "Deterministic scoring">

## Prompt personalities + trust validation

<copy line 207 of CLAUDE.md verbatim>

## Personalization (zero extra cost)

<copy lines 226-231 of CLAUDE.md verbatim — all bullets under "Personalization">

## Bundle E scoring_v2 contract (Phase 1 backend foundation)

- `app/models/scoring_v2.py` — Pydantic `Dimension` + `OverallScore` + `ScoringV2` with evaluative-language validator (13 banned words: best/pick/excellent/great/recommend/winner/worst/better/worse/beats/smart/good/choose).
- **3-core-keys invariant** (price/reviews/value exact set) + max-6-dim invariant.
- `scoring_service.calibrate_score()` — 60-95 perceived-score curve with floor + honesty guard.
- `scoring_service.build_dimensions_v2()` — emits 3 core + 0-3 contextual; skips any dim where either product lacks data (no empty rows).
- `response_builder` emits `scoring_v2` alongside legacy `scoring` for one release cycle (legacy slated for removal in Bundle F).

## Sources (verify against current code before recommending changes)

- `app/services/scoring_service.py` — `CATEGORY_DIMENSIONS`, `calibrate_score()`, `build_dimensions_v2()`, value badge logic
- `app/services/prompt_personalities.py` — `build_personality_prompt(category)`
- `app/services/trust_validation_service.py` — `validate_verdict()` → `{winner_aligned, claims_flagged, confidence_adjustment}`
- `app/services/behavior_service.py` — decay-weighted profiles (30-day half-life), category affinity, price range, dimension sensitivity
- `app/models/scoring_v2.py` — Pydantic models + banned-word validator
- Rollback V1: `docs/ROLLBACK_SCORING_V1.md`
- Design: `docs/plans/2026-05-13-results-quality-overhaul-design.md`, `docs/superpowers/specs/2026-03-08-smart-scoring-engine-design.md`
```

**Step 2: Verify char count**

```bash
wc -c .claude/skills/qaren-scoring/SKILL.md
```

Expected: ~3,500 chars.

**Step 3: Commit**

```bash
git add .claude/skills/qaren-scoring/SKILL.md
git commit -m "$(cat <<'EOF'
docs(skills): add qaren-scoring project-local skill

Extracts deterministic scoring + prompt personalities + personalization
+ Bundle E scoring_v2 contract from CLAUDE.md into an on-demand skill.
Loads only when scoring / dimension / personalization caps are mentioned.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Create `qaren-eas-deploy` skill

**Files:**
- Create: `.claude/skills/qaren-eas-deploy/SKILL.md`

**Step 1: Create directory and file**

```bash
mkdir -p .claude/skills/qaren-eas-deploy
```

Write `.claude/skills/qaren-eas-deploy/SKILL.md`:

```markdown
---
name: qaren-eas-deploy
description: Use when shipping OTA updates via eas update, building APKs / iOS bundles via eas build, configuring EAS channels (development / preview / production), bumping expo.version, runtime version policy, two-lever launch model, or when JS-only fixes need to reach testers. Covers Apple Developer ($99/yr) gating.
last_verified: 2026-05-16
update_when_changing:
  - SmartCompareApp/eas.json
  - SmartCompareApp/app.json
  - SmartCompareApp/package.json (when bumping expo SDK)
---

# Qaren EAS Update Infrastructure

## EAS project details

<copy lines 306-310 of CLAUDE.md verbatim — all bullets under "EAS Update infrastructure", including OTA push command + Rebuild required when... + Interactive Expo commands + eas build:configure gotcha>

## Two-lever launch model

Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update` / `eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired.

## Channels in `SmartCompareApp/eas.json`

- `development` — dev client builds, debug bundle
- `preview` — internal tester channel (current Bundle A baseline group `40719e26`; Bundle E group `d540c1e6`)
- `production` — App Store / Play (not used until Apple Developer subscription active)

## Apple Developer subscription ($99/yr) — gating dependencies

Until subscribed, the following are blocked:
- iOS production builds
- TestFlight distribution
- App Store ID swap in Cloudflare Worker (`idTBD` → real ID)
- Real-user iOS QA on Bundle E rings/dimension-bars/factual-verdict

## Sources (verify against current state before recommending changes)

- `SmartCompareApp/eas.json` — channels + `appVersionSource: "remote"`
- `SmartCompareApp/app.json` — runtime version policy, plugin list, permissions
- Expo project: `@kersher2/qaren` (ID `387a4fcb-76f6-4857-a2fb-39482ca4bd40`)
- Operational runbook: `docs/runbooks/qaren-canary-onboarding.md`
```

**Step 2: Verify char count**

```bash
wc -c .claude/skills/qaren-eas-deploy/SKILL.md
```

Expected: ~1,800 chars (slightly more than the 1k inline section because we added two-lever + channels + gating context).

**Step 3: Commit**

```bash
git add .claude/skills/qaren-eas-deploy/SKILL.md
git commit -m "$(cat <<'EOF'
docs(skills): add qaren-eas-deploy project-local skill

Extracts EAS Update infrastructure + two-lever launch model + Apple
Developer gating from CLAUDE.md into an on-demand skill. Loads only
when OTA / eas build / app version bump is mentioned.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Replace extracted sections in CLAUDE.md with breadcrumbs

**Files:**
- Modify: `CLAUDE.md` — replace 9 H3 sections with 5 breadcrumb lines.

**Step 1: Replace "Deterministic scoring" → "Personalization" block (lines 198-231)**

Use Edit tool. `old_string` = the entire block from line 198 ("### Deterministic scoring (zero cost)") through line 231 (end of Personalization section, including trailing blank line before "### Cohort personalization"). `new_string` = single breadcrumb:

```markdown
### Deterministic scoring + Prompt personalities + Personalization
See skill: `qaren-scoring` (auto-loads when scoring_service, dimension scores, personalization caps, or behavior_service are mentioned).
```

**Note:** This collapses 3 originally-separate H3 sections (Deterministic scoring, Prompt personalities, Personalization) into one breadcrumb. The "Auth + security hardening", "SSE streaming", and "Feedback and event tracking" sections that sit BETWEEN them (lines 209-223) stay inline — DO NOT remove those. Restructure carefully: replace 198-208 with breadcrumb, keep 209-223 as-is, then replace 225-231 with a pointer line saying "(covered by qaren-scoring skill above)".

Cleaner approach: replace lines 198-208 with the breadcrumb, then replace lines 225-231 with nothing (remove). The breadcrumb's description already covers all 3 sections.

**Step 2: Replace "Cohort personalization" block (lines 233-238)**

`old_string` = lines 233-238 (the full "### Cohort personalization" H3 + body).
`new_string`:

```markdown
### Cohort personalization (Phase 1 LIVE)
See skill: `qaren-cohort` (auto-loads when demographics endpoint, cohort_priors, or ENABLE_COHORT_PERSONALIZATION flag are mentioned). Note: feature flag is **ON in production**; code default remains `false`. Privacy invariant — NO raw age/gender/identity in prompt.
```

The kept inline keywords (`ENABLE_COHORT_PERSONALIZATION`, "ON in production", "Privacy invariant") preserve the most critical operational facts in CLAUDE.md itself.

**Step 3: Replace "Smart Decision Referrals" block (lines 259-267)**

`old_string` = lines 259-267 (the full H3 + body).
`new_string`:

```markdown
### Smart Decision Referrals
See skill: `qaren-referrals` (auto-loads when /api/v1/referrals/* routes, invite codes, Loop 1+2, redemption, or referral_invites table are mentioned). Gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway). Bundle B/C/D moved cap to **3 LIFETIME per device** with fail-OPEN on DB error.
```

Critical operational facts kept inline: env-var name, default state, cap value.

**Step 4: Replace Bundle A + B/C/D + E sections (lines 269-303)**

`old_string` = lines 269-303 (the three full bundle H3 sections).
`new_string`:

```markdown
### Bundle history (sessions 44-47)
See `docs/SESSION_BUNDLES.md` — historical context for Bundles A (PR #3), B/C/D (PR #4), and E (PR #5). Read when investigating regressions or tracing deferred follow-ups. Active state inline elsewhere: **Bundle E EAS group `d540c1e6` live on preview channel; Bundle F headline priority is `SCRAPING_MODE=soft` on Railway**.
```

**Step 5: Replace "EAS Update infrastructure" block (lines 305-310)**

`old_string` = lines 305-310.
`new_string`:

```markdown
### EAS Update infrastructure
See skill: `qaren-eas-deploy` (auto-loads when `eas update`, `eas build`, channel names, or runtime version bumps are mentioned). Quick recall: OTA via `cd SmartCompareApp && eas update --branch <channel>`. Rebuild required for native module / app.json plugin changes.
```

**Step 6: Verify the file still parses + no broken references**

```bash
# Confirm the 5 breadcrumb sections exist
grep -c "See skill:" CLAUDE.md
# Confirm bundle breadcrumb exists
grep -c "docs/SESSION_BUNDLES.md" CLAUDE.md
# Confirm the H2 section structure is intact
grep -c "^## " CLAUDE.md
```

Expected:
- `See skill:` matches: 4 (qaren-scoring, qaren-cohort, qaren-referrals, qaren-eas-deploy)
- `docs/SESSION_BUNDLES.md` matches: 1
- H2 sections: same count as before (this task only edits H3 sections inside Architecture and Important Patterns)

**Step 7: Verify char count dropped**

```bash
wc -c CLAUDE.md
wc -l CLAUDE.md
```

Expected: ~28,000 chars (well under 40k threshold), ~210 lines.

**Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(claude.md): replace 5 extracted sections with breadcrumbs

Drops CLAUDE.md from ~51.6k → ~28k chars. Removes inline copies of
Smart Decision Referrals, Cohort personalization, Deterministic scoring
+ Personalization, EAS Update infrastructure, and Bundle A/B/C/D/E
history. Critical operational facts (env-var names, default states,
cap values, current EAS group) kept inline in each breadcrumb.

Skills auto-load on description match; bundle history loads on demand
via docs/SESSION_BUNDLES.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Verify char count + structural integrity

**Files:**
- No file changes. Validation step only.

**Step 1: Final char count check**

```bash
wc -c CLAUDE.md
```

Expected: < 40,000 chars (target ~28,000). The 40k Claude Code performance warning should NOT trip.

**Step 2: Sum of moved content matches**

```bash
wc -c .claude/skills/qaren-referrals/SKILL.md \
       .claude/skills/qaren-cohort/SKILL.md \
       .claude/skills/qaren-scoring/SKILL.md \
       .claude/skills/qaren-eas-deploy/SKILL.md \
       docs/SESSION_BUNDLES.md
```

Expected: 5 files totaling ~23,500 chars (matching the design's reclaim target).

**Step 3: Spot-check skill content fidelity**

For each skill, grep for a unique-ish phrase from the original CLAUDE.md content to confirm it survived the move:

```bash
grep -l "3 LIFETIME per device" .claude/skills/qaren-referrals/SKILL.md
grep -l "Privacy invariant" .claude/skills/qaren-cohort/SKILL.md
grep -l "calibrate_score" .claude/skills/qaren-scoring/SKILL.md
grep -l "runtimeVersion.policy" .claude/skills/qaren-eas-deploy/SKILL.md
grep -l "Bundle E" docs/SESSION_BUNDLES.md
```

Expected: each grep returns the filename (match found).

**Step 4: No references to extracted content lost from CLAUDE.md**

Critical operational facts that must still appear in CLAUDE.md (in breadcrumbs):

```bash
grep "ENABLE_COHORT_PERSONALIZATION\|ENABLE_REFERRAL_SYSTEM\|3 LIFETIME\|d540c1e6\|SCRAPING_MODE=soft" CLAUDE.md
```

Expected: at least 5 lines of output covering all five operational landmarks.

No commit for this task (validation only).

---

### Task 9: Update MEMORY.md Session 34 note

**Files:**
- Modify: `C:\Users\SynAckITPC\.claude\projects\C--Users-SynAckITPC-Documents-ai-smartcompare\memory\MEMORY.md`

**Step 1: Find the existing Session 34 entry**

```bash
grep -n "Session 34" "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-ai-smartcompare/memory/MEMORY.md"
```

Expected: at least one line returned (the "Context File Strategy (Session 34)" block).

**Step 2: Edit the Session 34 block**

Use Edit tool to replace:

`old_string`:
```
## Context File Strategy (Session 34)
- **Keep CLAUDE.md monolithic** — verified via 3 research agents that splitting into `.claude/rules/` is dangerous for our tightly coupled architecture (pricing ↔ scoring ↔ behavior ↔ personalization)
- `.claude/rules/` without `paths:` = same tokens + fragmented = worse. With `paths:` = lazy-load but partial context = hallucination risk
- CONTEXT_SESSION_LOG.md (2,400+ lines) is safe — in `docs/`, never auto-loaded
- Target: CLAUDE.md ≤ 270 lines. Don't re-bloat with test catalogs or session refs.
```

`new_string`:
```
## Context File Strategy (Session 34 + Session 48 update)
- **Session 34 finding still valid for cross-cutting code:** splitting tightly coupled architecture (pricing ↔ scoring ↔ behavior ↔ personalization) into `.claude/rules/` is dangerous. Cross-cutting patterns stay inline.
- **Session 48 update (2026-05-16):** SELECTIVE extraction of self-contained subsystems into project-local skills under `.claude/skills/` IS safe — verified by char-count drop from 51.6k → ~28k with no loss of context-on-demand. Skills: `qaren-referrals`, `qaren-cohort`, `qaren-scoring`, `qaren-eas-deploy`. Bundle history moved to `docs/SESSION_BUNDLES.md` (lazy doc).
- `.claude/rules/` without `paths:` still rejected. Project-local skills (frontmatter + auto-surfaced via system-reminder) are the right primitive — they trigger on user-language description match, not on file paths.
- CONTEXT_SESSION_LOG.md (2,400+ lines) is safe — in `docs/`, never auto-loaded.
- Target: CLAUDE.md ≤ 270 lines. Don't re-bloat with test catalogs or session refs. When a new self-contained subsystem grows past ~2k chars in CLAUDE.md, extract it to a skill.
```

**Step 3: Commit (memory is local-only — no git, just save)**

Memory files live in `~/.claude/projects/.../memory/` and are not part of the repo. The Edit tool save is sufficient.

No git commit for this task.

---

### Task 10: Manual trigger validation (deferred — user-run)

**Files:**
- None (manual test, no automation).

**Step 1: User opens a fresh Claude Code session in this repo.**

**Step 2: User types one of these prompts and confirms Claude invokes the right skill:**

| Prompt | Expected skill invocation |
|---|---|
| "Fix the referral cap bug" | `qaren-referrals` |
| "The cohort match is broken for Bahrain users" | `qaren-cohort` |
| "Tweak the dimension scoring for fashion" | `qaren-scoring` |
| "Push an OTA update to preview" | `qaren-eas-deploy` |
| "What's the price pipeline?" | NO skill (answer from inline CLAUDE.md) |
| "Why does Bundle E ship with 51s latency?" | Read `docs/SESSION_BUNDLES.md` |

**Step 3: If a skill fails to trigger, expand its `description` field with the missing keyword + re-commit.**

No automated test for this — Claude's skill matching is heuristic and best validated by real prompts.

---

## Summary

**Total commits:** 6 (Task 2 + Task 3 + Task 4 + Task 5 + Task 6 + Task 7).
**Total time estimate:** 45-60 minutes (mechanical content copy + breadcrumb rewrites).
**Risk:** Low. All content preserved; only the loading mechanism changes. Rollback = `git revert` the 6 commits.

**Definition of done:**
- `wc -c CLAUDE.md` < 40,000
- 4 skills exist under `.claude/skills/qaren-*/SKILL.md` with valid YAML frontmatter
- `docs/SESSION_BUNDLES.md` exists with all 3 bundle bodies
- All 5 critical operational facts (env-var names + default states + cap values + current EAS group + Bundle F priority) still appear in CLAUDE.md
- MEMORY.md Session 34 entry updated to reflect the selective-extraction finding

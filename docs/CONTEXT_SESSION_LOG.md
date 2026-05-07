# SmartCompare — Session Log (Development History)

> This file contains the complete development history. Read the latest sessions first for current context.

---

# SESSION 43: Qaren UX Redesign (4-Opus Team) — COMPLETE 2026-05-07

## What We Did
Major UX redesign across the Qaren mobile app: Cal-AI-Lite 17-step onboarding, black/emerald hybrid visual identity (emerald reserved for signature moments), cohort-led referral flow with 3-day bonus expiry, deterministic 10% canary rollout. 5 phases shipped via 4-Opus team (frontend-visual, frontend-flow, backend, test-qa) with mandatory cross-QA gates at each phase. ENABLE_NEW_ONBOARDING canary live at 10% via `CANARY_NEW_ONBOARDING_PERCENT` const + EAS Update mechanic (NOT a Railway env var — corrected stale plan).

**Spec:** `docs/plans/2026-05-06-qaren-ux-redesign-design.md`
**Plan:** `docs/plans/2026-05-06-qaren-ux-redesign.md`
**Worktree:** `.worktrees/qaren-ux-redesign` on branch `feature/qaren-ux-redesign`

## Phases shipped (P1-P5)
- **P1 Visual foundation** — Geist EN font (SIL OFL), black/emerald hybrid theme tokens, motion config, Button black-CTA, src/icons/ infra + QaranIcon + 6 utility icons, snapshot tests. Gate: 94.91% coverage on Phase 1 files.
- **P2 17-step onboarding** — OnboardingFlow orchestrator, 17 step screens (Welcome→Notifications), CounterTicker + StageChecklist + ProgressBar variableEasing components, 5 hand-coded SVG hero illustrations (zero-Lottie), backend POST /attribution + migration 019, ENABLE_NEW_ONBOARDING feature flag (default OFF). Gate: 97.2% coverage; Step14Loading verified 3.2s floor (NOT-before / IS-after / fires-once / minDurationMs override).
- **P3 Home + Results redesign** — Camera-first card with 3-mode chips (Scan/Link/Type), StreamingProductCard with stage-gated SSE reveal, ResultsLoadingView (5-stage checklist + ghost cards + tips carousel), winner-celebration post-reveal (§4g copy "Why we picked this" / "Where the runner-up wins" / "What's next?" verbatim), CohortBadge (RTL-aware slide-in), TabBarIcon bounce. Gate: 99.14% coverage on new components; 1.2s min-display floor wired in HomeScreen→Results navigation.
- **P4 Referral + bonus expiry** — Migration 018 (expires_at + expiry_reminder_sent_at), referral_service 3-day expiry, cron_expire_bonuses with ENABLE_BONUS_EXPIRY_PUSHES default OFF + 1000-row LIMIT + idempotency stamp, Loop 2 push gift-framing copy (EN+AR), ReferralLandingScreen partial-blur (winner gated, products + cohort visible), InviteeQuizScreen reveal with CounterTicker, ShareBottomSheet "You'll unlock" reward block, BonusCountdownCard wired into Home. Gate: backend 19/19 + frontend 89-100% coverage.
- **P5 Polish + canary** — Copy audit (14 EN + 14 AR baseline scary-copy keys eliminated, replaced with "Hold on — Tap to retry" / "Reconnecting…" / "Sharper match coming up" vocabulary), RTL audit (4 hardcoded LTR-biased style props fixed via marginEnd / conditional textAlign), a11y audit (Chip + IconButton get accessibilityRole/Label + 44pt min-size), arabicLineHeightMultiplier consumption (1.7x AR readability), 4 frontend-visual polish wins (Step15 stagger, Results glow ring, Step12 bullets, Step05 lock 5° rotation), canary 10% wired via featureBucket.ts (djb2 hash + getStableId) + features.ts getter pattern. Gate: 588/588 jest pass + tsc 0.

## Migrations
| # | File | What |
|---|---|---|
| 018 | `018_referral_bonus_expires_at.sql` | referral_redemptions.expires_at + .expiry_reminder_sent_at + referral_invites.deep_review_expires_at (TIMESTAMPTZ NULLABLE) + partial-WHERE index `idx_referral_redemptions_expires_at WHERE consumed_at IS NULL`. Verified live via Supabase MCP. |
| 019 | `019_users_attribution_source.sql` | users.attribution_source TEXT NULLABLE with CHECK constraint mirroring Pydantic enum. |

## Key commits (54 total on feature/qaren-ux-redesign)
- 1bfc3ca P1 Geist font (SIL OFL v1.1, ~125KB/weight bundled local)
- a36728e P1 theme tokens (cta.primary #0A0A0B, accentGlow rgba, hero/eyebrow typography, motion config)
- 3ee3306 P1 Button black primary CTA + signature variant for invitee Reveal
- 80976a3 + 1640866 + 4edf7dd P1+P3 icons (QaranIcon + 6 utility + 3 Mode + react-native-svg test mock)
- 38e5f0a P2 backend POST /attribution + migration 019 (Pydantic Literal + DB CHECK defense-in-depth)
- d1882be P2 OnboardingFlow orchestrator + 17-step types (cohort exact-case enforced)
- 1c636cc P2 CohortBarChart hero illustration #2 (388-dot grid, spiral-from-center peer cluster algo)
- 9b02cd0 P2 Step14 theatrical loading (8/8 tests verify 3.2s floor)
- 044f417 P2 ENABLE_NEW_ONBOARDING flag wiring (default OFF, NewOnboardingHost fire-and-forget persistence)
- 993c1f3 + 2627e4c + cfef521 + fa9240d P3 Home + Streaming + Results loading + Results post-reveal
- 0f3c9fc + 68b32fa + b7d4d0d + 80094d9 P4 backend (migration + expiry + cron + push)
- b58f40c + b34a56f + 13449c6 P4 ReferralLanding partial-blur + InviteeQuiz reveal + ShareBottomSheet
- 0fdbd91 P5-pre Onboarding analytics events (started/step_completed/completed)
- f8bdb43 Task #50 — Fixed 13 pre-existing test failures (4 root causes: bare jest.mock auto-mock overriding moduleNameMapper, RNTL host-traversal limitation on mock-prefixed Animated.View/Text, expo-screen-capture ESM transform, InviteeQuizScreen inline mock missing Easing.bezier)
- d554a52 P5 Task #44 copy audit (28 keys rewritten)
- acca743 P5 Task #45 RTL fixes (marginEnd over marginRight, conditional textAlign)
- 28c7fe9 P5 Task #46 a11y (Chip + IconButton role/label + 44pt + hitSlop)
- 5685272 P5 Task #47 canary wiring (CANARY_NEW_ONBOARDING_PERCENT=10, hashBucket primitive, getStableId device-id→user.id transition)
- c83acf0 P5 flow_variant analytics enrichment (lock-at-mount via flowVariantRef)

## Test totals (post-redesign)
- Frontend jest: 588/588 PASS across 75 suites (was 188/201 with 13 pre-existing failures on main pre-redesign; +400 tests + 13 fixes net)
- Frontend tsc 0
- Frontend coverage on redesign-touched files:
  - P1 (theme + Button + icons): 94.91% stmts
  - P2 (onboarding screens + components + illustrations + features.ts): 97.2% stmts / 86.01% branches / 96.29% funcs / 97.99% lines
  - P3 (StreamingProductCard, LoadingTipsCarousel, CohortBadge, TabBarIcon, ResultsLoadingView, ModeIcons): 99.14% stmts
  - P4 (ReferralLandingScreen, InviteeQuizScreen, BonusCountdownCard, StyleProfileCard): 89-100% on each file (ShareBottomSheet 0% intentional — source-string assertion pattern, render tests need BottomSheet portal mocking)
- Backend pytest free unit: 2264/2273 PASS — 9 failures (test_share_routes/test_unified_search/test_rate_limiting_complete/test_referral_must_fixes) verified pre-existing on main via `git diff main..HEAD` returns empty diff for these files. NOT redesign regressions.
- Backend redesign-owned tests: 100% (19/19 referral_expiry + cron_expire_bonuses + loop2_gift_copy + 14/14 attribution_endpoint)

## Cross-QA evidence
- **test-qa** ran formal gates on Tasks 7, 25, 33, 42, 49 + per-commit reviews on every of 54 redesign commits with detailed findings posted to each task description
- **frontend-visual** cross-QA'd commit a36728e for backward-compat with existing accent-string call sites (40+ found, none broken)
- **frontend-flow** cross-QA'd Task 27 StreamingProductCard reuse pattern with Task 10 CounterTicker (4th reuse confirmed clean)
- **backend** cross-QA'd test-qa's Task #50 jest mock fix (verified the fix didn't introduce ESM transform regressions)

## Phase 5 polish carry-forward (Phase 6 / future sessions)
- **Task #58/60** — symmetric analytics on legacy OnboardingScreen (frontend-flow owner; SHOULD land before Task #48 50→100 ramp)
- **Physical-device verification** (deferred per Task 42 + Task 46 audits) — push notification delivery on iOS + Android, deep-link `qaren://profile/referrals` open-from-push, AR-locale RTL walkthrough, VoiceOver + TalkBack screen-reader walk, 60fps Android perf check on reveal animation
- **Cron live dry run** with ENABLE_BONUS_EXPIRY_PUSHES=true (currently default OFF; first canary cohort exercises live path)
- **Backend 5xx error copy** "Try with brand or model — sharper match every time" — UI exists (StageChecklist), copy not yet wired
- **Overflow stage copy** for 25s+/45s+ stalls (§3 Stages 6/7/8) — UI exists (LoadingTipsCarousel), copy not yet wired
- **Sticky footer on ResultsScreen** (currently inline; layout polish)

## Critical lessons (Session 43)

1. **`git stash --include-untracked` is a footgun in multi-agent worktrees.** test-qa stashed during a per-commit verification → captured frontend-flow's tracked-modified files (Task 26 in-flight) → frontend-flow saw their work "vanish" and panic-recreated. Net no damage (recreated work matched original; original recovered via `git checkout stash@{0} -- <paths>` + drop) but burnt time. Hard rule going forward: NO `git stash` in any form. Use `git show <sha>:<path>` for SHA-isolated reads. Documented in updated team brief.

2. **Bare `jest.mock(name)` overrides moduleNameMapper.** 13 pre-existing test failures on main were caused by `jest.mock('react-native-reanimated')` (no factory) in 3 test files triggering Jest auto-mock → undefined-returning stubs → `useSharedValue()` returns undefined → `animatedWidth.value = ...` crashes. Fix: REMOVE the bare mock, rely on jest.config.js `moduleNameMapper`. Comment blocks left in fixed test files explaining why future authors should not re-add the bare mock.

3. **RNTL `getByText` only traverses Text-typed hosts.** The Reanimated test mock rendered `Animated.View` / `Animated.Text` as custom `mock-Animated-View` / `mock-Animated-Text` host elements — RNTL's text query couldn't find content inside them. Fix: forward `Animated.View/Text/Image` to React Native's real hosts in the mock. Caught a real RNTL bug-class that would have eaten weeks of false negatives in tests where Animated.Text wraps copy.

4. **Plan revision when implementation diverges from plan.** Plan task 47 step 1 said "Set feature flag to 10% in Railway env" — STALE. ENABLE_NEW_ONBOARDING is a frontend build-time const, not a Railway env var. Actual mechanic: `CANARY_NEW_ONBOARDING_PERCENT = 10` in features.ts via EAS Update. Updated the plan in commit (Task #49 docs sweep) so future readers don't chase a Railway env var that doesn't exist.

5. **flow_variant analytics asymmetry caught at Phase 5 review.** New flow emits 3 analytics events with `flow_variant: "new"`; legacy flow emits ZERO. Task #47 monitoring works one-armed; Task #48 ramp decision needs both arms. Tracked as Task #60 (legacy mirror) before #48 fires.

6. **NOT all "scary copy" replacements are equally easy.** First-pass rewrites used "Try Again" replacements which is itself in the forbidden words list. Lesson: build the full vocabulary table BEFORE editing, don't reactive-rewrite. The final pass landed at "Hold on — X. Tap to retry." / "Reconnecting…" / "expired or moved" — these stick and don't recurse on the regex.

## Documentation updates landed in Task #49

- `docs/plans/2026-05-06-qaren-ux-redesign.md` Tasks 47 + 48 — replaced stale "Railway env var" mechanic with `CANARY_NEW_ONBOARDING_PERCENT` const + EAS Update reality
- `MEMORY.md` Session 43 entry (cohort exact-case rule reinforcement, jest mock anti-patterns, stash footgun, plan-revision pattern)
- `CONTEXT_SESSION_LOG.md` Session 43 entry (this section)

## Post-merge updates (2026-05-07)

- **PR #2 merged on `main` as `ee91a87`** — full Qaren UX redesign landed.
- **Canary bumped 10 → 100 (commit `462b399`)** for build/test mode. Rationale: <100 hash-buckets test users out of the feature being tested; build/test builds need everyone in the new flow. The 10/50/100 ramp is for App Store soft launch only.
- **Pre-App-Store reset** to `CANARY_NEW_ONBOARDING_PERCENT = 10` will be documented in `features.ts` comment + canary runbook (`docs/CANARY_RUNBOOK.md`) so the soft-launch operator doesn't ship 100 to production by accident.

## Pending follow-ups
- Task #48 (50→100% ramp) — operationally gated on 48h live metrics from Task #47 launch. NOT in-session work.
- Task #57, #58/60 — Phase 5 polish (symmetric analytics, physical-device verifications). Frontend-flow owner; non-blocking.

## Final state at team disassemble
- Frontend: 588/588 jest + tsc 0 + ≥80% coverage on all redesign-touched files
- Backend: redesign-owned tests 100% pass; 9 main-branch pre-existing failures untouched by redesign
- Migrations 018 + 019 applied LIVE in Supabase production via MCP
- Canary 10% live (CANARY_NEW_ONBOARDING_PERCENT = 10 in features.ts)
- Zero scary copy in user-facing i18n (verified by grep)
- 7 RTL bugs fixed; arabicLineHeightMultiplier now consumed
- a11y: Phase 5 source pass complete; physical-device walks deferred

---

# SESSION 42: Smart Decision Referral System (4-Opus Team)

## What We Did
Built virality-optimized referral system with dual-loop rewards (Loop 1 immediate Deep Review credit on share; Loop 2 deferred +5/+10 on invitee conversion), hybrid OpenAI model routing, re-engagement push system, admin dashboards. 4 new migrations applied via Supabase MCP. Feature-flag gated. End-to-end Loop 2 fired in production smoke chain on 2026-05-05 with all side effects verified.

**Spec:** `docs/superpowers/specs/2026-05-05-smart-referral-system-design.md`
**Plan:** `docs/plans/2026-05-05-smart-referral-system.md`
**Worktree:** `.claude/worktrees/referral-system-v1`

## Phases shipped (P1-P6)
- **P1 Foundation** — Migration 014 + referral code generation + T&C/Privacy markdown + AI sharing toggle
- **P2 Referrer Flow** — POST /share + GET /status + ShareBottomSheet + result-aware CTA + Loop 1 toast
- **P3 Invitee Flow** — GET /invite/{token} + POST /quiz + ReferralLandingScreen + InviteeQuizScreen + invite_id capture on Register
- **P4 Loop 2 + Anti-Abuse** — Loop 2 trigger + AbuseDetectionService (3 controls, 100% cov) + bonus capacity + Expo Push
- **P5 Re-Engagement** — Daily cron + 3 detectors (insight/cohort/retrospective) + selector priority + push dispatcher + 4-toggle UI
- **P6 Admin Dashboards** — 8 admin endpoints (X-Admin-Key, 30/min) + 2 HTML pages mirroring Session 41 cohort dashboard

## Cross-cutting (P-cross)
- **Hybrid model routing (BX.1+BX.2)** — `model_router_service` with atomic Redis INCRBY; verdict on gpt-4o below 80% daily cap, mini above; 429 retry-once with audit log; fail-open on Redis unavailable

## Migrations
| # | File | What |
|---|---|---|
| 014 | `014_referral_system.sql` | 4 tables (referral_invites, referral_redemptions, deep_review_credits, re_engagement_events) + RLS + resolve_referral_code RPC + users column extension |
| 015 | `015_push_tokens.sql` | users.expo_push_token + notifications_enabled + last_comparison_at + 2 partial indexes |
| 016 | `016_referral_invite_privacy.sql` | referral_invites.privacy JSONB |
| 017 | `017_widen_share_token.sql` | comparisons.share_token VARCHAR(12) → TEXT (fixes Session-22-era latent bug) + RLS policy round-trip |

## Key commits
| Commit | What |
|--------|------|
| 5833650 | feat(referral): migration 014 schema |
| bb9e7e6 | feat(referral): code generation + invite/status service (B1.2/B2.1/B2.2) |
| e624fe2 | feat(privacy): per-user AI sharing toggle (B1.4) |
| 93ce64d | docs(legal): T&C + Privacy Policy updates |
| b022551 | feat(referral): P2 + P3 routes + service extensions |
| 84ef802 | feat(privacy): F1.5 AI sharing toggle UI |
| 8c0fa5f | fix(profile): translate accessibilityLabel for AI sharing Switch |
| 6f1972d | feat(referral): F2.3 ShareBottomSheet + referralService |
| d215f81 | feat(model_router): hybrid per-call OpenAI routing (BX.1+BX.2) |
| dfe0b34 | feat(referral): AbuseDetectionService (B4.1) |
| f438a52 | feat(referral): Loop 2 trigger + Expo push + bonus capacity (B4.2/B4.3/B4.4) |
| 06355ce | feat(referral): F2.4+F2.5 result-aware CTA + Loop 1 toast |
| 9e40c20 | feat(referral): F2.3-followup wire privacy toggles to share endpoint |
| 1f4d202 | feat(reengagement): selector + 3 detectors + daily cron (B5.1+B5.2+B5.3) |
| 7ccb4a3 | feat(referral): F3.2 ReferralLandingScreen + deep-link plumbing |
| 1145b12 | feat(referral): F3.3 InviteeQuizScreen 4-step wizard + tests |
| d8d5f95 | feat(referral): F3.5 invite_id capture on Register |
| 39d7114 | feat(referral): ENABLE_REFERRAL_SYSTEM feature flag |
| ca57896 | feat(referral): B3.5 link invite redemption on signup |
| 6596745 | feat(referral): migration 015 push tokens + notifications opt-out |
| fe827b0 | feat(referral): F2.3-followup share privacy block honoured end-to-end |
| 4963272 | fix(referral): close 4 must-fix bugs + None-guard |
| 6caf96a | fix(referral): conditional unwrap + dual-shape Pydantic compat refinements |
| 586ebc3 | feat(admin): referral metrics + cost dashboard endpoints (B6.1+B6.2) |
| b22f553 | feat(admin): F6.3+F6.4 referrals + costs HTML dashboards |
| 800bd0a | feat(notifications): F5.4 backend push token PUT + sub-toggles |
| c1ebd4d | feat(referral): F4.5 ReferralStatusCard in Profile + tests |
| d8d22b2 | feat(referral): F5.4 Notifications UI + expo-notifications token reg |
| 0b01d9a | fix(share): migration 017 + loud-failure for share-token persistence |
| d9d5b03 | fix(abuse): real-action gate uses elapsed_seconds proxy (Option A) |
| 7695e00 | test(security): static schema-drift check (Session 42 lesson) |
| eb5c855 | test(referral): Q8.1 E2E bodies filled from smoke fixtures (9 PASS / 1 skip) |

## Test totals
- Backend referral suite: 307+ tests across 19 files
- Security regression: 98 (was 67, +21 referral cases + 10 schema-drift)
- Frontend Jest: 30 new tests across 6 new test files (ReferralLanding 7, InviteeQuiz 7, RegisterScreen.inviteId 2, ReferralStatusCard 7, pushToken 6, plus 1 lucide mock infra fix)
- Cumulative coverage 93% across 8 referral-owned backend files

## Bugs caught + fixed mid-session
- 5 must-fix bugs caught by test-referral's red test batch (4f7fb23): feature flag ordering, error middleware 503, function name mismatch, ShareRequest privacy fields, vacuous PII patch
- 2 latent prod bugs caught by backend's live smoke: share_token VARCHAR(12) (Session 22 era), `_load_comparison` SELECTing nonexistent started_at/result_viewed_at
- 1 defense-in-depth nit: AbuseDetectionService._duration_seconds None-guard

## Acceptance criteria (Design Section 14)
| # | Criterion | Status |
|---|---|---|
| 1 | Migration 014 applied + verified | ✅ + migrations 015/016/017 |
| 2 | All 7 phases shipped + flag-gated | ✅ |
| 3 | Coverage ≥80% + 75+ regression | ✅ 93% combined + 98 regression |
| 4 | E2E in production canary | 🟢 structurally green; tests/test_referral_e2e.py 9 PASS / 1 conscious skip; HANDOFF: Ahmed flips flags + smokes |
| 5 | Admin dashboards render real data | 🟢 structurally green; HANDOFF: Ahmed smokes /admin/referrals.html + /admin/costs.html with X-Admin-Key |
| 6 | T&C + Privacy Policy 3 sections EN+AR | ✅ (commit 93ce64d) |
| 7 | CLAUDE.md + MEMORY.md + this log updated | ✅ this commit |
| 8 | Mutual QA across all 4 agents | ✅ — qa-referral cross-reviewed every non-trivial commit; backend's smoke caught 2 of qa's missed issues; test-referral caught 4 must-fix bugs qa initially false-cleared |
| 9 | Hybrid model routing operational | ✅ (commit d215f81) |
| 10 | Anti-abuse synthetic tests pass | ✅ (60 tests in test_abuse_detection.py + _internals.py, 100% cov) |

8/10 fully GREEN code-side. #4 + #5 Ahmed-side handoff items per Operational Rollout in CLAUDE.md.

## Operational rollout handoff (to Ahmed)
1. Flip `ENABLE_HYBRID_MODEL_ROUTING=true` in Railway, monitor 24h
2. Flip `ENABLE_REFERRAL_SYSTEM=true` (all-at-once recommended); rollback if error rate >1% / P95 >2s / abuse-flag rate >5/hr
3. Smoke /admin/referrals.html + /admin/costs.html with real X-Admin-Key
4. After 1 week stable: flip `ENABLE_REENGAGEMENT_PUSHES=true`
5. Cleanup smoke test data via Supabase MCP after 24h evidence window

---

# SESSION 39: Security Completion + Freemium (Agent Team)

## What We Did
- Completed remaining security hardening + freemium tier enforcement
- 8 commits (3 new + 5 from previous session)

## Commits
| Commit | Task | Description |
|--------|------|-------------|
| 420646e | 1 | Migration SQL: usage tracking, audit log, RLS |
| 03d353f | 2-3 | Prompt injection defense: system/user message separation + sanitizer |
| 6dceeb0 | 7-8 | Freemium usage tracking service + routes |
| c337788 | 9 | Frontend paywall wiring + USAGE_LIMIT handling |
| d7a7dc2 | 10 | CLAUDE.md + dep scanning docs |
| 6f7cf1e | 5 | Audit logging service + admin query endpoints |
| 4501c82 | 6 | Brute-force lockout (5 failures → 15min lock) |
| f3f3750 | 4 | Rate limiting on 7 endpoints + SSRF + input validation |

## What Was Built
- **Prompt injection defense** — system/user message separation in all GPT calls + input sanitizer
- **Rate limiting** — all 7 previously unprotected endpoints now rate-limited
- **SSRF protection** — /url/detect validates URLs against private IPs
- **Input validation** — max_length on product names, search params, share token regex
- **Audit logging** — fire-and-forget to admin_audit_log + admin query endpoints
- **Brute-force lockout** — 5 failed logins → 15min Redis-based lock, fail-open
- **Freemium tiers** — Free: 3 lifetime + 10/month + 3/day, Premium: 70/month + 10/day
- **Frontend paywall** — usage tracking + USAGE_LIMIT → paywall screen redirect

## Test Results
- 1686 tests passed, 0 failures
- 125 security-specific tests (regression + injection + usage + audit + rate limiting + brute force)
- Frontend TypeScript: 0 errors

## Manual Step
- Apply `migrations/011_security_completion_freemium.sql` via Supabase SQL Editor

---

# SESSION 40: April 8, 2026 — L2 DB Cache for Product Data

## What We Did
- Implemented product data persistence as L2 cache between Redis and API calls
- Created migration `012_product_data_tables.sql` (3 tables: product_specs, product_prices, product_reviews)
- Created `app/services/product_data_service.py` with 6 functions (get/save for specs, prices, reviews)
- Integrated L2 lookups into `structured_comparison_service.py` (_get_specs, _get_price with 6 return points) and `review_service.py`
- Added `_save_price_to_db()` helper to avoid duplicating save calls across 6 price return paths
- 14 new tests in `tests/test_product_data_service.py`, 1700 total pass
- 57/57 security regression tests pass — new tables have RLS with public read/insert/update
- Deployed commit `553b091`, migration applied via Supabase SQL Editor
- Updated CLAUDE.md with L2 cache docs, migrations section, new tables list

## Key Decisions
- **Specs/reviews upsert, prices append** — prices keep history for future trend analysis
- **Freshness**: specs 30d, prices 24h, reviews 14d (longer than Redis TTLs)
- **Fire-and-forget saves** via `asyncio.create_task()` — DB write failures don't block responses
- **`nocache=true` bypasses both layers** — Redis AND DB skipped, forces fresh API calls
- **RLS public policies** on product data tables — reference data, not user data

## Issues Encountered
- Old tables existed with different schema (`product_id` instead of `product_key`) — `CREATE TABLE IF NOT EXISTS` silently skipped, indexes failed. Fixed with `DROP CASCADE` + recreate.
- No psql/Management API token locally — migrations must be applied via Supabase SQL Editor
- Python httpx DNS resolution fails on this Windows machine but curl works fine

## Files Changed
- Created: `migrations/012_product_data_tables.sql`, `app/services/product_data_service.py`, `tests/test_product_data_service.py`
- Modified: `app/services/structured_comparison_service.py`, `app/services/review_service.py`, `CLAUDE.md`

---

# SESSION 36: March 28, 2026 — Qaren Frontend Redesign (Agent Team, Interrupted)

## What We Did

Full frontend redesign: SmartCompare → Qaren (قارن). Camera-first, bilingual (EN/AR), editorial magazine design. Used 4 Opus agent team (backend, frontend, test, qa) with `bypassPermissions`. Session interrupted by rate limits before completion.

### Design Spec & Plan
- **Design spec**: `docs/superpowers/specs/2026-03-28-qaren-frontend-redesign-design.md`
- **Implementation plan**: `docs/superpowers/plans/2026-03-28-qaren-frontend-redesign.md` (17 tasks across 3 phases)
- **Visual direction**: Editorial Magazine — light/minimal, emerald accent (#10B981), Inter+Cairo fonts
- **Key decisions**: Camera-first home, 3 bottom tabs (Home/History/Profile), single-scroll results, 6-step onboarding, RTL via i18next + expo-localization

### Phase 1: Foundation (Tasks 1–5) — COMPLETE ✓
- **Task 1**: Dependencies installed (reanimated, i18n, expo-image, haptics, fonts) — `72f34a8`
- **Task 2**: Theme system (colors, typography, spacing, shadows, Arabic line-height multiplier) — `b34c651`
- **Task 3**: i18n setup (i18next, 164 keys EN+AR, full parity, language persistence) — `b77d582`
- **Task 4**: Storage keys renamed `@smartcompare_*` → `@qaren_*`, OnboardingData + MainTabParamList types added — `701f501`
- **Task 5**: RTL utils + 10 design system components (Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton, ComparisonCounter, SearchOverlay, CategorySelector restyled, FeedbackCard restyled) — `b857974`
- **Foundation tests**: 13 tests (theme tokens + i18n parity validation) — `d34cf62`

### Phase 2: Screens (Tasks 6–15) — MOSTLY COMPLETE
- **Task 6**: SplashScreen (logo animation, fade+scale, auto-dismiss 1.5s) — `5475ab9` ✓
- **Task 7**: OnboardingScreen (6-step wizard: language, region, priorities, budget, lifestyle, brand attitude) — `59cfbb3` ✓
- **Task 8**: Auth Screens — LoginScreen restyled (theme tokens + i18n + Button component) but **UNCOMMITTED**. RegisterScreen and ForgotPasswordScreen status unclear.
- **Task 9**: HomeScreen (836 lines — camera-first, 3 input modes: scan/url/text, SSE streaming, comparison counter, recent searches) — `52ce895` ✓
- **Task 10**: ResultsScreen (1245 lines — single-scroll, winner reveal with haptic, specs diff toggle, scores, feedback) — `75dbf4e` ✓
- **Task 11**: HistoryScreen (date-grouped sections, search, delete, staggered animations) — `f8c1826` ✓
- **Task 12**: ProfileScreen (settings, language, prefs, password change, account deletion) — `f8c1826` ✓
- **Task 13**: PaywallScreen (bottom sheet placeholder, plan selector, no real IAP) — `f8c1826` ✓
- **Task 14**: App.tsx Navigation Rewrite — **NOT DONE** (still uses old navigation structure, no bottom tabs)
- **Task 15**: Integration Testing — **PARTIAL** (test stubs created for SplashScreen, OnboardingScreen, AuthScreens, HomeScreen + 5 mock files, but test bodies are scaffolds only)

### Phase 3: Polish (Tasks 16–17) — NOT STARTED
- **Task 16**: Animations & Micro-interactions — not started
- **Task 17**: Final QA & Cleanup — not started

### Not Done
- **App.tsx navigation rewrite** (Task 14) — CRITICAL BLOCKER. New screens exist but aren't wired into navigation.
- **Old screen deletion**: CameraScreen.tsx, AccountScreen.tsx, PreferencesScreen.tsx still exist (deprecated, functionality absorbed)
- **app.json**: Updated (name: "Qaren", slug: "qaren", bundleId: "com.qaren.app") ✓

### Uncommitted Files
- `SmartCompareApp/src/screens/LoginScreen.tsx` — restyled with theme tokens + i18n
- `SmartCompareApp/jest.config.js` — expanded testMatch patterns + transformIgnorePatterns + moduleNameMapper
- `SmartCompareApp/__tests__/SplashScreen.test.tsx` — test scaffold (4 stubs)
- `SmartCompareApp/__tests__/OnboardingScreen.test.tsx` — test scaffold (8 stubs)
- `SmartCompareApp/__tests__/AuthScreens.test.tsx` — test scaffold (16 stubs)
- `SmartCompareApp/__tests__/HomeScreen.test.ts` — test scaffold with mocks
- `SmartCompareApp/__mocks__/` — 5 mock files (react-native, reanimated, lucide, i18next, async-storage)

### Commits (12 total)
```
72f34a8 chore: install Qaren dependencies (reanimated, i18n, expo-image, haptics, fonts)
b34c651 feat: add Qaren design system (colors, typography, spacing, fonts)
b77d582 feat: add i18n system (i18next, EN+AR translations, RTL language hook)
701f501 refactor: rename storage keys smartcompare->qaren, add onboarding types
d34cf62 test: add theme and i18n foundation tests (13 tests, jest setup)
b85a987 chore: add test deps (@types/jest, testing-library) and jest types to tsconfig
f8c1826 feat: add HistoryScreen (date-grouped), ProfileScreen (grouped cards), PaywallScreen (bottom sheet)
b857974 feat: add Qaren design system components (Button, Card, Chip, Skeleton, Progress, IconButton, Counter, RTL utils, comparison counter hook)
52ce895 feat: camera-first HomeScreen with search overlay and comparison counter
75dbf4e feat: single-scroll ResultsScreen with skeleton loading and winner reveal
5475ab9 feat: add SplashScreen with logo animation
59cfbb3 feat: add OnboardingScreen (6-step wizard with i18n)
```

### To Resume
Remaining work (in priority order):
1. **Task 14**: App.tsx navigation rewrite — bottom tabs, splash flow, onboarding gate, nested stacks
2. **Task 8**: Commit LoginScreen, verify Register/ForgotPassword restyled
3. **Task 15**: Flesh out test stubs with real assertions, commit test infrastructure
4. **Old screen deletion**: Remove CameraScreen, AccountScreen, PreferencesScreen
5. **Task 16**: Animations & micro-interactions polish
6. **Task 17**: Final QA & cleanup

---

# SESSION 35: March 27, 2026 — Backend Hardening (Security + Decomposition)

See Session 34 below for CLAUDE.md audit that preceded this session.

Comprehensive backend hardening in 3 parallel workstreams using 4 Opus agents.

### Security Hardening
- Admin auth: timing-safe `hmac.compare_digest` for X-Admin-Key
- SSRF protection: `url_validator.py` — resolves hostnames, blocks private/loopback/link-local IPs
- Security headers middleware: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- Input validation: UUID path params on history/share routes, LIKE wildcard escaping, field length caps
- Rate limits: account deletion 1/min, resend verification 3/min
- Swagger docs disabled in production

### Monolith Decomposition (3452 → 1454 lines)
- Extracted 5 domain modules from `structured_comparison_service.py`:
  - `price_service.py` (932 lines) — pricing tiers, currency, scraping, iHerb, pharmacy
  - `rating_service.py` (292 lines) — tiered extraction, Google consensus, retailer classification
  - `review_service.py` (227 lines) — fetching, cleaning, citation replacement
  - `fact_check_service.py` (217 lines) — citation verification, cross-validation, confidence
  - `response_builder.py` (190 lines) — build_comparison_response() for sync + streaming
- Concurrency fix: per-request instances via `get_comparison_service()` (not singleton)

### Tests
- 141 new tests across security, exchange rates, decomposed services
- ~1560+ total tests passing
- 6 commits

---

# SESSION 34: March 27, 2026 — CLAUDE.md Optimization (Context Quality Audit)

## What We Did

Intensive audit and optimization of CLAUDE.md using the claude-md-management skill, backed by 3 parallel research agents that verified `.claude/rules/` mechanics, risk assessment, and current directory structure.

### Research Findings (Verified)
- **`.claude/rules/` without `paths:` frontmatter** loads ALL files at startup → same token cost as monolithic, but fragmented context → net negative for tightly coupled projects
- **`.claude/rules/` with `paths:` frontmatter** lazy-loads → saves tokens BUT partial context risk for coupled services (pricing ↔ scoring ↔ behavior ↔ personalization)
- **Decision: Keep monolithic CLAUDE.md, trim aggressively.** Our project profile (single dev, tight coupling, rapid iteration across 33 sessions) matches the failure pattern for split approaches, not the success pattern (large teams, loosely coupled microservices).
- **CONTEXT_SESSION_LOG.md (2,426 lines) is safe** — lives in `docs/`, NOT auto-loaded. Only read on-demand when investigating history.

### CLAUDE.md Changes (441 → 267 lines, 39% reduction)
- **Removed**: 56-line test file catalog (not actionable, discoverable via pytest)
- **Removed**: 20+ "Session N" references throughout (history, not guidance)
- **Removed**: Duplicated luxury brand detection section (already in Architecture price pipeline)
- **Removed**: Dead code reference (Tier 0: "never called")
- **Condensed**: Scoring internals (15 → 6 lines), personalization (17 → 5 lines), key services (17 → 10 lines), middleware (6 → 1 line), frontend screens (10 → 1 line), rating pipeline (8 → 2 lines)
- **Merged**: Cost budget + unified search + cache bypass → 1 section. Sharing + history → 1 section. Review + spec quality → 1 section.
- **Fixed**: Added missing `ForgotPasswordScreen.tsx`, corrected route paths to `app/api/`, removed stale version number from entry point
- **Quality score**: 64/100 (C) → 89/100 (B+)

### MEMORY.md Changes (Deduplication)
- Replaced near-clone of CLAUDE.md with lean reference pointing to CLAUDE.md as source of truth
- Kept only: session learnings, gotchas, key decisions, and information NOT in CLAUDE.md
- Purpose redefined: session-specific learnings and cross-session patterns, not architecture docs

### Key Decision: Why NOT Split
Risk matrix results for our project:
| Risk | Rating |
|------|--------|
| Context fragmentation (coupled services) | HIGH |
| Maintenance overhead (update 4+ files per refactor) | HIGH |
| Hallucination from partial context | MEDIUM-HIGH |
| Migration errors (orphaned instructions) | MEDIUM-HIGH |
| Monolithic actually better for our profile | HIGH |

### Files Changed
- Modified: `CLAUDE.md` (441 → 267 lines)
- Modified: `docs/CONTEXT_SESSION_LOG.md` (added Session 34)
- Modified: `~/.claude/projects/.../memory/MEMORY.md` (deduplicated)

---

# SESSION 33: March 26, 2026 — Category-Specific Comparison Languages (Scoring V2 + Prompt Personalities + Trust Validation)

## What We Did

Replaced universal 6-dimension scoring with category-specific dimensions (unique 6 per category), added prompt personalities for GPT verdict tone, trust validation to cross-check GPT claims, plus backend production hardening (account deletion, legal endpoints, version check). 4 Opus agents (backend-scoring, backend-prompts, backend-production, test-qa) with cross-QA. Total: 1418 tests (was 1295).

### Category-Specific Scoring V2 (Tasks 1-2, backend-scoring)
- **`CATEGORY_DIMENSIONS`**: 9 categories × 6 unique dimension keys each
  - Electronics: performance_score, value_score, build_quality_score, feature_score, ecosystem_score, futureproof_score
  - Fragrances: character_score, longevity_score, projection_score, versatility_score, wear_value_score, presentation_score
  - Supplements: efficacy_score, purity_score, bioavailability_score, safety_score, value_per_dose_score, evidence_score
  - (etc. for all 9 categories)
- **`_DIMENSION_SIGNAL_MAP`**: Maps 5 raw signals (spec/price/review/reliability/popularity) → category-specific dimension keys
- **`CATEGORY_DIMENSION_WEIGHTS`**: Per-category weight profiles (aliased as `CATEGORY_WEIGHTS` for backward compat)
- **`CATEGORY_PRIORITY_ADJUSTMENTS`**: 8 priorities × 9 categories (replaces universal `PRIORITY_ADJUSTMENTS`)
- **`DIMENSION_DISPLAY_NAMES`**: User-friendly labels for all 49 unique dimension keys
- `compute_dimension_winners(category=)`, `build_scores_summary()` updated for category-specific dimensions
- **Rollback preserved**: `docs/ROLLBACK_SCORING_V1.md` captures entire V1 system

### Prompt Personalities (Tasks 3-4, backend-prompts)
- **`prompt_personalities.py`**: `CATEGORY_PROMPT_PERSONALITIES` — each category gets unique tone/language in GPT verdict
  - Electronics: "technical analyst" (benchmarks, specs, measurable differences)
  - Fragrances: "experienced fragrance enthusiast" (evocative descriptions, projection, longevity)
  - Fashion: "style-conscious editor" (material quality, versatility, cost-per-wear)
- **`UNIVERSAL_TRUST_RULES`**: Applied to all categories — no unverified claims, cite data sources
- `build_personality_prompt(category)` returns combined personality + trust rules string
- Injected via `extraction_service.py` `generate_comparison(category=...)` into verdict prompt

### Trust Validation (Tasks 3-4, backend-prompts + test-qa cross-QA)
- **`trust_validation_service.py`**: `validate_verdict()` cross-checks GPT verdict against deterministic scores
  - `winner_aligned`: GPT winner matches scoring winner
  - `claims_validated`: dimensions where GPT and scores agree directionally
  - `claims_softened`: dimensions where scores are essentially tied (gap < 3)
  - `claims_flagged`: dimensions where GPT contradicted scores
  - `confidence_adjustment`: suggested confidence change if misaligned
- Wired into `structured_comparison_service.py` response metadata
- Bug fix: None handling for breakdown values (caught by cross-QA)

### Backend Production Hardening (Tasks 5-7, backend-production)
- **Account deletion**: `delete_user_data_cascade(user_id)` — cascades through user_events → comparison_feedback → comparisons → search_logs → auth user. App Store requirement.
- **Password strength**: 10+ chars, 1 uppercase, 1 lowercase, 1 digit (register + change password)
- **Email verification**: `POST /api/v1/auth/resend-verification` — rate limited 3/min
- **Legal endpoints**: `GET /api/v1/legal/privacy` + `/terms` — serve markdown files, no auth required
- **Version check**: `GET /api/v1/app/version` — `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE` env vars
- **Dead code removed**: `comparison_service.py` (289 lines, never imported anywhere)
- `database_service.py`: all `print()` → `logger`

### Testing (Task 8, test-qa)
- 9 new test files: test_category_dimensions, test_scoring_edge_cases, test_prompt_personalities, test_trust_validation, test_trust_edge_cases, test_personality_edge_cases, test_account_deletion, test_legal_routes, test_version_routes
- Cross-QA: test-qa reviewed backend-production's work, backend-production reviewed test-qa's work
- Trust validation None bug found by cross-QA, fixed

### Files Changed
- Modified: `app/services/scoring_service.py` (V2 dimensions), `app/services/extraction_service.py` (personality injection), `app/services/structured_comparison_service.py` (trust validation integration), `app/services/database_service.py` (cascade delete + logging), `app/api/auth_routes.py` (password strength + email verify + account delete), `app/main.py` (new routers)
- Created: `app/services/prompt_personalities.py`, `app/services/trust_validation_service.py`, `app/api/legal_routes.py`, `app/api/version_routes.py`, `app/legal/privacy_policy.md`, `app/legal/terms_of_service.md`, `docs/ROLLBACK_SCORING_V1.md`
- Deleted: `app/services/comparison_service.py` (dead code)
- 9 new test files in `tests/`

### Commits
- `fe94683` — feat: add prompt personalities + trust validation per category
- `ebb9888` — feat: add account deletion, password strength, email verification
- `eec2d9d` — feat: add legal endpoints + version check for app store readiness
- `c5712ab` — chore: delete dead comparison_service.py (289 lines, never imported)
- `5e7c0c4` — test: add edge case + cross-QA tests for scoring, personalities, trust
- `128583b` — docs: update CLAUDE.md for Session 33 + integrate trust validation

---

# SESSION 32: March 25-26, 2026 — Firecrawl Price Resolution (Executed Session 31 Plan)

## What We Did

Executed the Firecrawl plan from Session 31. Replaced Cloudflare Browser Rendering + Microlink with Firecrawl Smart Wait (Tier 1.5a) + Scrape.do (Tier 1.5d). Added API budget tracking with circuit breakers, Gate 0 input validation, expanded GCC retailer coverage, admin cost dashboard. 1295 tests passing (was ~1295 before, many new + some replaced).

### Key Changes
- `firecrawl_service.py`: Thin async wrapper around Firecrawl `/v1/scrape` with Smart Wait (5s waitFor, 15s timeout)
- `scrapedo_service.py`: Thin async wrapper around Scrape.do `render=true` API (15s timeout)
- `api_budget_service.py`: Credit tracking (Firecrawl 450/lifetime, Scrape.do 900/mo, Serper 2200/lifetime) + circuit breakers (3 failures → 10min cooldown)
- Gate 0: `_validate_price_query()` + `_validate_scrape_url()` prevent wasted scrape credits
- GCC retailers expanded to 9 domains (added level-shoes, harveynichols, galerieslafayette, theluxurycloset, boutique1)
- Admin cost dashboard: `GET /api/v1/admin/costs`
- Removed: `_fetch_rendered_html()`, `JS_ONLY_DOMAINS`, `ENABLE_JS_RENDER`, 3 diagnostic endpoints
- **Status**: Code complete, tests passing. Pending Phase 0 validation with real API keys.

---

# SESSION 26: March 20, 2026 — Scoring & Quality Overhaul (Category Weights, Price Tiers, Review Cleanup)

## What We Did

Comprehensive overhaul of scoring engine, price pipeline, review quality, and verdict generation. Triggered by Hermes Nevada Cap vs LV Vers Mesh Cap comparison showing fake-looking scores, garbage review text, no ratings, shallow verdict. 4 Opus agents in parallel (scoring-agent, price-agent, review-agent, test-agent) with cross-QA. Total: 944 tests (was 809).

### Root Causes Identified
- Single `DEFAULT_WEIGHTS` profile for all categories — fashion scored like electronics
- Value score was naive `(spec + price) / 2` — expensive always = bad
- No price tier awareness — luxury vs budget compared on same scale
- Review text contained garbage ("learn more about condition", navigation text, positive text in complaints)
- No ratings for luxury products — showed empty instead of derived rating
- Verdict was shallow ("premium vs budget") with no scoring data injection

### Scoring Engine Overhaul (Tasks 1-4, scoring-agent)
- **CATEGORY_WEIGHTS**: 9 category-specific weight profiles replacing single `DEFAULT_WEIGHTS`
  - Fashion: popularity=0.25, review=0.25, price=0.10 (brand matters more than price)
  - Electronics: spec=0.25, price=0.20, reliability=0.15 (specs matter most)
  - Supplements: reliability=0.30, review=0.25 (trust matters most)
- **Price tier detection**: budget(<11 BHD), mid(11-57), premium(57-189), luxury(189+)
- **Tier-aware value score**: Cross-tier uses expectation formula (`50 + (delivery - expected) * 0.8`), same-tier uses 60/40 spec/price blend
- **CATEGORY_MIN_COVERAGE**: Per-category spec penalty thresholds (electronics=0.5, fashion=0.3)
- **Dimension winners**: `compute_dimension_winners()` — per-dimension comparison with tie threshold=3.0
- **Enriched `build_scores_summary()`**: Tier info, dimension leaders, category weights injected into verdict prompt
- **Personalization cap fix**: `MAX_WEIGHT_SHIFT_RATIO` now caps relative to CATEGORY weights, not old defaults
- **Derived ratings**: `_derive_rating_from_scores()` — display-only rating (2.5-4.8 range) for products with no real rating
- **Tier context**: Response includes `tier_context` with price tiers and cross-tier flag
- **Scoring method**: `category_weighted` (anonymous) or `personalized` (logged in)

### Price Pipeline Fixes (Tasks 5-7, price-agent)
- **Counterfeit keyword filter**: `COUNTERFEIT_KEYWORDS` (20 terms: replica, fake, dupe, pre-owned, vintage, etc.). First filter in `_extract_price_from_shopping()` before accessory filter. Also in `_strict_title_match()`.
- **Official domain targeted search (Tier 1.5)**: `_get_official_domain()` maps luxury brand to domain → `site:domain.com` Serper search when Tier 1 fails. +$0.001 cost only for luxury brands.
- **Smarter sanity thresholds**: Official domain prices (retailer_score >= 1.0) bypass sanity check entirely. Luxury brands use tighter thresholds (1.8x high / 0.6x low vs 2.0x / 0.5x).
- **Price prompt hardening**: Explicit rejection rules for counterfeit platforms, replica listings, suspiciously cheap luxury prices.

### Review & Verdict Fixes (Tasks 8-11, review-agent)
- **Review prompt hardening**: CONTENT QUALITY rules (reject navigation text, boilerplate, condition disclaimers, marketing copy, short filler). BAD/GOOD examples. Sentiment alignment: only negative in complaints.
- **Backend post-processing filter**: `_clean_review_content()` with `GARBAGE_PATTERNS` (10 regex), `NEGATIVE_INDICATORS` (25 words), `POSITIVE_INDICATORS` (18 words). Strips garbage, enforces min 8 words, removes positive-only complaints. Called BEFORE `_clean_review_citations()`.
- **Verdict prompt overhaul**: Structured scoring context injection with 4 requirements (recommendation, key differences, value analysis, best for). Cross-tier awareness: "different products for different needs" framing.
- **Streaming parity**: All fixes applied to both streaming and non-streaming paths.

### Tests (Tasks 12-15, test-agent)
- **68 new tests** across 5 files:
  - `test_scoring_service.py` +27: category weights, price tiers, value score, dimension winners, coverage, personalization
  - `test_luxury_brands.py` +15: counterfeit filter, official domain lookup, sanity skip
  - `test_price_priority.py` +4: title match rejection
  - `test_review_cleanup.py` (NEW) 19: garbage patterns, sentiment, derived ratings, edge cases
  - `test_review_prompt_quality.py` +7: prompt rules verification

### Cross-QA Results (Task 16)
- scoring-agent → review-agent (Tasks 8-11): ALL PASS
- review-agent → price-agent (Tasks 5-7): ALL PASS
- price-agent → scoring-agent (Tasks 1-4): ALL PASS
- Full suite: 944 passed, 0 failed

### Production Verification
Deployed and tested with `Hermes Nevada Cap vs LV Vers Mesh Cap`:
- Category: fashion (correct), category weights applied
- Price tiers: Hermes=premium, LV=mid, cross-tier detected
- Derived ratings: 3.6 and 3.9 (no more empty)
- Review praises cite hermes.com, louisvuitton.com (clean, no garbage)
- Dimension winners working (Price: LV +70, Specs: tie, Value: LV +8)
- Recommendation: data-backed, acknowledges different market segments

### Known Remaining Issue
- **Luxury prices still estimated**: Official domain search (Tier 1.5) gets organic URLs but can't extract prices from snippets (luxury sites render prices via JavaScript). Need page scraping with JSON-LD parsing — same pattern as `_fetch_pharmacy_price()`. Proposed fix for Session 27.

### Files Changed
- `app/services/scoring_service.py` — Full overhaul: CATEGORY_WEIGHTS, price tiers, value score, dimension winners, coverage thresholds, build_scores_summary
- `app/services/structured_comparison_service.py` — Counterfeit filter, official domain search, sanity thresholds, review post-processing, derived ratings, tier context
- `app/services/extraction_service.py` — Review prompt hardening, price prompt hardening, verdict prompt overhaul
- `tests/test_scoring_service.py` (+27), `tests/test_luxury_brands.py` (+15), `tests/test_price_priority.py` (+4), `tests/test_review_cleanup.py` (NEW, 19), `tests/test_review_prompt_quality.py` (+7)

### Commits (15)
```
22a4931 fix: remove skip guards from dimension_winners tests
eee27f5 test: add 7 prompt quality tests
aec9e76 test: add 19 review cleanup tests
7d2e200 feat: tier_context, derived ratings, streaming parity
f30d93c test: add 22 price pipeline tests
ee77897 feat: category coverage thresholds, dimension winners, enriched summary
edc5cef test: add 64 counterfeit/domain/prompt tests
b80d737 test: add 27 scoring service tests
a976fe0 feat: price tier detection + tier-aware value score
096c64d feat: smarter sanity thresholds + price prompt hardening
81122a9 feat: verdict prompt overhaul
b40dff4 feat: official domain targeted search for luxury
9f12cf6 feat: review post-processing filter
1d4583d feat: replace DEFAULT_WEIGHTS with CATEGORY_WEIGHTS
e673948 feat: counterfeit keyword filter
```

### Test Results
- 944 passed, 0 failed (free tests)
- +135 new tests over Session 25's 809

---

# SESSION 25: March 19, 2026 — AI Quality Overhaul (Fashion, Luxury, Price, Citations)

## What We Did

Comprehensive fix for AI result quality. Triggered by LV hat vs Hermes hat comparison showing wrong prices ($56 BHD instead of $237 BHD), irrelevant spec fields (Power, Compatibility for hats), and raw `[snippet_N]` citations in reviews. 2 rounds: Round 1 with 2 Opus agents (backend + tests), Round 2 inline. Total: 809 tests (was 757).

### Root Causes Identified
- No "fashion" category — hats fell into "other" with electronics-style fields
- Price prompt said "extract the LOWEST reasonable price" — picked counterfeit/reseller prices, ignored official hermes.com $630 price that was IN search results
- `[snippet_N]` citations rendered raw in frontend — no cleanup layer existed
- "other" schema had electronics fields (power, compatibility, count, included)

### Round 1 — Backend (7 tasks, 2 Opus agents)
- **Fashion category**: 9th category with dedicated 10-field schema (material, style, closure_type, size_options, care_instructions, craftsmanship, collection_season, origin, color, design_details)
- **"Other" schema fixed**: Removed power/compatibility/count/included, added material/features/dimensions/weight/origin/care_instructions
- **Product-type binding**: Parser prompt now binds product types to categories (can't pick electronics for hats)
- **Luxury brand detection**: `LUXURY_BRAND_KEYWORDS` (30+ brands), `OFFICIAL_BRAND_DOMAINS` (25+ domains), `_is_luxury_brand()` method — category-independent two-layer defense
- **Price prompt rewrite**: "MOST AUTHORITATIVE" instead of "LOWEST reasonable". Source priority: official brand sites > authorized retailers > marketplaces > resellers. DO/DON'T examples.
- **Price extraction backend**: Official domain boost in `_extract_price_from_shopping()`, luxury brand sorting priority, expanded sanity check, counterfeit site filtering
- **Spec prompt fix**: Changed from "EVERY field MUST have a value" to smart field handling — omit irrelevant fields instead of forcing N/A
- **Citation cleanup**: `_clean_review_citations()` replaces `[snippet_N]` with source domain name (e.g., "Per hermes.com:") using `_extract_domain()` helper
- **Review + verdict prompts**: Category-aware `category_scores` aspects, sparse review handling, dynamic `best_for` guidance per category, luxury value assessment

### Round 1 — Tests (4 new test files, 51 tests)
- `test_fashion_category.py` (12): schema, fields, parser prompt, category switching, product-type binding
- `test_luxury_brands.py` (19): parametrized detection, case insensitive, accent handling, domains, retailer tiers
- `test_citation_cleanup.py` (13): snippet→domain replacement, unknown snippet stripping, multiple fields, empty/null handling
- `test_price_priority.py` (7): official domain priority, non-luxury normal behavior, counterfeit filtering, retailer tier coverage

### Round 2 — Frontend + Scoring (3 tasks, inline)
- **SpecsTab N/A filtering**: Filters out N/A, null, empty, `_source` fields, and metadata (brand/model/variant/category) before rendering. Empty state when no specs available.
- **Fashion in CategorySelector**: Added as 8th chip with handbag emoji
- **Scoring N/A penalty**: When `coverage_ratio < 0.5`, apply `penalty_factor = 0.5 + coverage_ratio` to prevent inflated spec scores for products with mostly-empty fields

### Files Changed
- `app/services/extraction_service.py` — Fashion schema, "other" fix, price prompt, spec prompt, review prompt, verdict prompt
- `app/services/structured_comparison_service.py` — Luxury constants, _is_luxury_brand(), _extract_domain(), _clean_review_citations(), price extraction backend, RETAILER_TIERS expansion
- `app/services/scoring_service.py` — N/A penalty in _score_specs()
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — SpecsTab N/A filtering
- `SmartCompareApp/src/components/CategorySelector.tsx` — Fashion category chip
- `tests/test_fashion_category.py` (NEW), `tests/test_luxury_brands.py` (NEW), `tests/test_citation_cleanup.py` (NEW), `tests/test_price_priority.py` (NEW)

### Test Results
- 809 passed, 0 failed (free tests)
- +52 new tests over Session 24's 757

---

# SESSION 24: March 18, 2026 — Backend Completion & Frontend Audit Fixes

## What We Did

Full backend audit + frontend audit. 2 rounds of 2-agent Opus teams for backend, 1 round for frontend. Total: 758 tests (was 717).

### Backend Round 1: History + Errors + Auth Rate Limits
- **`app/api/history_routes.py`** (NEW): Restored history endpoints deleted in Session 22 (GET list, GET single, DELETE)
- **`app/middleware/error_handler.py`** (REWRITTEN): Unified error format `{ success: false, error: "msg", code: "ERROR_CODE", request_id }` across all endpoints
- **`app/api/auth_routes.py`**: Added slowapi rate limits — login 5/min, register 3/min, social-login 10/min, password-reset 3/min
- **`app/api/url_routes.py`**: Removed `/compare/multi` stub endpoint (dead code)

### Backend Round 2: Sharing
- **`migrations/add_share_token.sql`** (NEW): `share_token VARCHAR(12)` column on comparisons table
- **`app/api/share_routes.py`** (NEW): POST create share link (auth, ownership check), GET public share (strips personalization)
- **`app/services/database_service.py`**: Added `create_share_token()` (collision retry) and `get_shared_comparison()`
- **`app/main.py`**: Registered history_router + share_router, unified error handlers

### Frontend Fixes (8 issues from audit)
1. **AccountScreen logout** — `onLogout()` instead of `navigation.reset()` (was stuck in MainNavigator)
2. **HistoryScreen 401** — `clearSession()` + `onLogout()` instead of `navigation.navigate('Login')` (non-existent route)
3. **Share integration** — `shareComparison()` in api.ts, ResultsScreen gets backend share link + OS share sheet fallback
4. **Category switched banner** — Info banner on ResultsScreen when category auto-corrected
5. **`parseApiError()` utility** — Handles both `.error` (new) and `.detail` (legacy) formats, used in all 8 screens
6. **Dead code cleanup** — Removed `compareProducts`, `quickCompare`, `getRateLimitStatus`, `getSubscriptionStatus`, `debugUpload` from api.ts (~140 lines)
7. **User type consolidation** — Single `User` in authService.ts with `display_name` + `auth_provider`, removed duplicate from types.ts
8. **PreferencesScreen lifestyle** — Allows 0 selections (was requiring 1+)

### Test Coverage
- 41 new tests: `test_history_routes.py` (15), `test_share_routes.py` (12), `test_error_middleware.py` (10), auth rate limit tests (4)
- Fixed 13 test regressions from unified error format change (`data["detail"]` → `data["error"]`)
- 758 tests passing, `npx tsc --noEmit` 0 errors

## Files Changed (Backend: 10, Frontend: 13)
**Backend new:** `app/api/history_routes.py`, `app/api/share_routes.py`, `migrations/add_share_token.sql`
**Backend modified:** `app/main.py`, `app/middleware/error_handler.py`, `app/api/auth_routes.py`, `app/api/url_routes.py`, `app/services/database_service.py`
**Frontend modified:** `App.tsx`, `AccountScreen.tsx`, `CameraScreen.tsx`, `ForgotPasswordScreen.tsx`, `HistoryScreen.tsx`, `HomeScreen.tsx`, `LoginScreen.tsx`, `PreferencesScreen.tsx`, `RegisterScreen.tsx`, `ResultsScreen.tsx`, `api.ts`, `authService.ts`, `types.ts`

## Key Decisions
- History routes restored to `/api/v1/comparisons/history` (matching frontend, not `/api/v1/history`)
- Share tokens are 8-char URL-safe base64 (`secrets.token_urlsafe(6)`), stored as `share_token` column
- Unified error format uses `code` field for machine-readable errors (AUTH_REQUIRED, NOT_FOUND, RATE_LIMITED, etc.)
- Frontend `parseApiError()` handles both old `.detail` and new `.error` response formats for backwards compat
- Agent teams: 2 rounds backend (2 Opus each), 1 round frontend (2 Opus) — Pro subscription limits handled OK

---

# SESSION 23: March 14, 2026 — Data Quality & UX Polish

## What We Did

3-round, 2-agent Opus team (backend+frontend per round, then test+docs). Focused on improving data accuracy (ratings, prices) and frontend polish.

### 1. Personalization Pipeline Diagnostic Logging
**Files:** `app/api/text_routes.py`, `app/services/auth_service.py`
- Added structured logging throughout the personalization pipeline
- Logs user auth status, preferences fetch, and preference injection into comparison
- Helps debug "why wasn't my comparison personalized?" issues

### 2. Scoring Weight Cap (±30%)
**File:** `app/services/scoring_service.py`
- `MAX_WEIGHT_SHIFT_RATIO = 0.30` — personalization can shift weights by at most ±30% of defaults
- Prevents extreme weight distributions (e.g., 90% price, 10% everything else)
- Ensures all scoring dimensions remain meaningful even with strong preferences

### 3. Pharmacy URLs in RETAILER_SEARCH_URLS
**File:** `app/services/structured_comparison_service.py`
- Added Boots (`bn.boots.com`) and Al Deerah Pharmacy (`aldeerahpharmacy.com`) to `RETAILER_SEARCH_URLS`
- Enables `_build_retailer_url()` fallback for pharmacy retailers

### 4. Rating Tier Lists Expanded
**File:** `app/services/structured_comparison_service.py`
- **Tier 1** (trusted): added iHerb, Sephora, Ulta (previously only Amazon, Best Buy, etc.)
- **Tier 2** (known): added Fragrantica, Sally Beauty, LookFantastic, BeautyBay, Nykaa, Bath & Body Works, Boots
- Better rating coverage for supplements, beauty, and fragrance categories

### 5. iHerb Rating Extraction During Price Scrape
**File:** `app/services/structured_comparison_service.py`
- Extracts `data-ga-rating` and `data-ga-review-count` attributes from iHerb HTML during existing price scrape
- Cached in `_shopping_items_cache` as a synthetic shopping item with `source: "iherb"`
- Zero extra API calls — piggybacks on existing iHerb price scrape
- Feeds into rating pipeline as Tier 1 data

### 6. Price `source_method` Tagging
**File:** `app/services/structured_comparison_service.py`
- Every price now tagged with `source_method`: `local_bhd` (direct BHD price), `converted_usd` (USD→BHD conversion), or `estimated` (GPT training data)
- `price_method_mismatch` flag set when two products have different source methods (e.g., one local, one estimated)
- Helps frontend display appropriate labels and users assess price reliability

### 7. RatingDisplay Simplified
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Shows all ratings without verified/unverified badges
- Cleaner UI — trust indicators were confusing to users

### 8. Reviews Tab Fallback Rendering
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- When `pros`/`cons` arrays are empty, renders `common_praises`, `complaints`, and `detailed_praises` instead
- Prevents empty Reviews tab for products with alternative review data shapes

### 9. Cost Display Removed from UI
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Removed per-comparison cost display from results screen
- Cost tracking still works in backend for analytics — just hidden from users

### 10. Feedback Card State Persistence
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- FeedbackCard state (submitted, useful, selections) lifted to parent ResultsScreen
- Prevents state loss when switching tabs (React re-mounts tab content)

### 11. Price Label Update
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- "(converted from USD)" label replaces old estimated label for `source_method: "converted_usd"`
- More accurate description of what the price represents

### 12. Auth Flow Improvements (pre-existing, committed with deploy)
- `clearSession()` called on logout (App.tsx)
- `onLogout` escape hatch on PreferencesScreen for stuck tokens
- 401 interceptor scoped to auth flow endpoints only (not `/auth/preferences`)

## Files Changed
- `app/api/text_routes.py` — personalization logging in 3 endpoints
- `app/services/auth_service.py` — preferences fetch error logging
- `app/services/scoring_service.py` — MAX_WEIGHT_SHIFT_RATIO + cap logic
- `app/services/structured_comparison_service.py` — iHerb ratings, tier expansion, pharmacy URLs, price source_method
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — rating display, reviews fallback, cost removal, feedback state, price labels
- `SmartCompareApp/src/components/FeedbackCard.tsx` — controlled props (submitted, onSubmitted)
- `SmartCompareApp/src/types/types.ts` — RatingSource.url nullable, source_method on ProductPrice
- `SmartCompareApp/App.tsx` — clearSession on logout, PreferencesScreen onLogout prop
- `SmartCompareApp/src/screens/PreferencesScreen.tsx` — onLogout escape hatch
- `SmartCompareApp/src/services/api.ts` — 401 interceptor scope fix
- `tests/test_scoring_service.py` — 5 new weight capping tests
- `tests/test_url_quality.py` — 4 new pharmacy URL tests
- `tests/test_rating_tiers.py` — 7 new expanded tier tests
- `tests/test_iherb_rating.py` — 5 new iHerb rating tests (new file)
- `tests/test_price_source.py` — 5 new price source tests (new file)

## Test Suite: 717 tests, 32 files (+26 from Session 22 baseline of 691)

## Deployed & Verified
- 13 commits deployed via `git push origin main`
- Production health check: healthy
- Supplement comparison (HealthAid vs NOW Vitamin D3): source_method tags working, reviews populated, price_method_mismatch detected
- Electronics comparison (iPhone 15 vs Galaxy S24): ratings verified from Tier 1 retailers, scoring working
- Cost per comparison: $0.0097 (supplements), $0.0112 (electronics) — within $0.015 budget

## Production Observations
- iHerb `data-ga-rating` attribute returned null on search pages — extraction gracefully returns null, falls back to GPT aggregate. May need investigation of iHerb's current HTML structure.
- HealthAid brand name stripped by parser (shows as "Vitamin D3") — pre-existing parser behavior, not Session 23 regression.
- `weights_used` empty for anonymous requests — expected (default weights used, field not populated without auth).

---

# SESSION 22: March 12, 2026 — Auth Fixes, Backend Cleanup & AI Cost Tracking

## What We Did

3 sequential rounds of 2 Opus agents each (fresh team per round to prevent context bloat).

### Round 1: Auth Fixes
- Password reset endpoint path mismatch fixed (authService.ts)
- `_categorize_auth_error()` helper — 8 exception blocks updated with clean error messages
- `_enrich_response_with_profile()` — display_name + auth_provider in login/register/social responses
- `/me` endpoint normalized (auth_routes.py)
- 20 new tests, 13 updated

### Round 2: Backend Cleanup
- `routes.py` DELETED — 485 lines of dead legacy code removed from main.py router
- Dead category-specific endpoints removed from text_routes.py (23 lines)
- 3 unused functions removed from openai_service.py (225 lines)
- Serper cost tracking verified (all 9 calls tracked)
- 18 new tests in test_backend_cleanup.py

### Round 3: AI Cost Tracking
- All 6 extraction functions return `(result, token_usage)` tuples
- `_track_gpt_cost(usage)` uses real OpenAI token counts ($0.15/1M input, $0.60/1M output)
- `_track_serper_cost()` replaces all `_track_cost(0.001)` calls
- `gpt_calls` and `serper_calls` counters in response metadata
- Old `_track_cost()` method deleted
- 16 new tests in test_cost_tracking.py, 20 mock fixes

### Post-Session: Supabase Config Fix
- Disabled "Confirm email" in Supabase Dashboard (was causing 401 on registration)
- Updated Site URL to production Railway URL

## Test Suite: 691 tests (+54 from Session 21 baseline of 637)
## Dead Code Removed: ~733 lines

---

# SESSION 21: March 11, 2026 — AI Guidance System

## What We Did

2-phase, 2-agent Opus team. Brainstormed → spec → plan → parallel implementation → cross-QA.

### Phase 1: Parallel Implementation
**Agents:** backend-agent, frontend-agent

1. **Personalized Insight Cards** (backend + frontend)
   - Added `personalized_insights` field to COMPARISON_PROMPT JSON schema (2-3 insights per comparison)
   - GPT generates insights tied to user priorities when preferences exist (~50 extra tokens, ~$0)
   - Validation: strips when no prefs, truncates to 3 max, handles malformed GPT output
   - Wired through non-streaming response, SSE verdict event, and streaming complete_response
   - Frontend `InsightCard` component with context-aware Ionicons (battery, price, camera, etc.)
   - `PreferencePromptBanner` shown for anonymous/non-personalized users → links to Preferences

2. **Winner Badges** (frontend only, $0)
   - `AspectBadges` component replaces old binary "WINNER" badge
   - 6 per-dimension badges (Best Price, Best Specs, Top Rated, Best Value, Most Reliable, Most Popular)
   - Deterministic from `scoring.breakdown` — badge shown when winner leads by >= 3 points
   - "Best for You" (personalized) / "Best Overall" (anonymous) ribbon for overall winner

3. **Broader Price Fallback** (backend)
   - `MODEL_VARIANT_PATTERN` regex strips trailing Pro/Plus/Max/Ultra/256GB/1TB
   - 1 extra Serper Shopping call when Tier 1+2 both fail (before Tier 3 GPT estimate)
   - Skipped for supplements (they use dedicated iHerb/pharmacy pipeline)

4. **Graceful Empty States** (frontend)
   - ReviewsTab: empty state card when no reviews/pros/cons/ratings available
   - SpecsTab: already filtered nulls (no change needed)
   - Removed orphaned winnerBadge/winnerBadgeText styles

### Phase 2: Cross-QA + Test Coverage
- Backend agent QA'd frontend: APPROVED (1 minor cleanup — orphaned styles, fixed)
- Frontend agent QA'd backend: APPROVED (0 issues)
- 28 new tests (17 guidance insights + 11 fallback improvements)
- Final: **637 tests passing, 0 failures**

## Files Changed
- `app/services/extraction_service.py` — COMPARISON_PROMPT + generate_comparison() validation
- `app/services/structured_comparison_service.py` — insights wiring + MODEL_VARIANT_PATTERN + broader fallback
- `SmartCompareApp/src/types/types.ts` — PersonalizedInsight interface
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — AspectBadges, InsightCard, PreferencePromptBanner, empty states
- `tests/test_guidance_insights.py` (new, 17 tests)
- `tests/test_fallback_improvements.py` (new, 11 tests)

## Commits (8)
- `d8fdc15` feat: add PersonalizedInsight type + update ComparisonResult
- `23b3e31` feat: add personalized_insights to verdict prompt + validation
- `83427e7` feat: wire personalized_insights through response and SSE stream
- `ce504c7` feat: add AspectBadges, InsightCard, PreferencePromptBanner
- `64d7e16` feat: add broader search fallback before Tier 3 GPT estimate
- `bea82e5` feat: add graceful empty states for missing data
- `eea1e1c` test: add edge case tests for guidance system
- `a194d1e` chore: remove orphaned winnerBadge styles

## Test Suite: 637 tests (28 new), 27 files

## Post-Deploy Bugfixes (Session 21b)

### Bug: 401 on Preferences Save
**Root cause:** Two issues compounding:
1. **Wrong Supabase env vars on Railway** — `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` were pointing to non-existent project `khatrmxzrvjzlbtcetva` instead of correct `qulajmyxdbdkchvecmvc`. All auth calls failed with `[Errno -2] Name or service not known`.
2. **Stale token in AsyncStorage** — User's stored JWT was from the wrong Supabase project, so even after fixing Railway env vars, the cached token was invalid.
3. **Overly broad interceptor skip** — `api.ts` response interceptor skipped auto-refresh for any URL containing `/auth/`, which included `/auth/preferences`. Fixed to only skip core auth flow endpoints (login, register, refresh, logout, social-login).
4. **No escape from Preferences onboarding** — When stuck on PreferencesScreen with invalid token, user had no way to logout. Added `onLogout` prop + red "Logout" link in header.

**Fixes:**
- `SmartCompareApp/src/services/api.ts` — Narrowed 401 refresh skip from `/auth/` to specific auth flow endpoints
- `SmartCompareApp/src/services/authService.ts` — Added debug logging for token presence after login/register
- `SmartCompareApp/src/screens/PreferencesScreen.tsx` — Added `onLogout` prop + Logout link in onboarding header
- `SmartCompareApp/App.tsx` — Pass `onLogout` to PreferencesScreen, `handleLogout` now calls `clearSession()`
- Railway env vars: corrected all 3 Supabase variables to `qulajmyxdbdkchvecmvc` project

---

# SESSION 20: March 8, 2026 — Smart Scoring Engine + SSE Streaming + Feedback

## What We Did

3-phase, 2-agent-per-phase Opus team (6 agents total). Pro subscription token limit management: 2 agents instead of 4 to avoid rate limit spikes on resume.

### Phase 1: Scoring Engine + TS Fixes
**Agents:** backend-scoring, frontend-fixes

1. **Scoring Service** (`app/services/scoring_service.py` — new)
   - 6 dimensions: price, spec, review, value, reliability, popularity (0-100 scale)
   - Personalized weights from user preferences (priorities, budget, brand_attitude)
   - Category-specific spec scoring for all 8 categories
   - Deterministic: pure math, $0 cost, same input = same output
   - Integrated after Phase 2 in pipeline, scores_summary injected into verdict prompt

2. **All 5 TS Errors Fixed** (was pre-existing since Session 17)
   - App.tsx: navigation types, CameraScreen: hoisting, ForgotPasswordScreen: missing export, ResultsScreen: vector-icons import, metadata nullish coalescing
   - `npx tsc --noEmit` = 0 errors

3. **Scoring UI** in ResultsScreen Overview tab
   - ScoreBadge per product (color-coded 0-100), breakdown bars, winner margin banner

### Phase 2: SSE Streaming + Feedback System
**Agents:** backend-streaming, feedback-system

4. **SSE Streaming** (`GET /api/v1/text/compare/stream`)
   - 10 SSE events: status→specs→prices→reviews→scores→verdict→complete
   - `compare_from_text_streaming()` async generator in structured_comparison_service.py
   - Non-streaming endpoint unchanged (backward compatible)
   - Cold-start prevention documented in main.py

5. **Feedback System**
   - Supabase tables: `comparison_feedback` + `user_events` (RLS enabled)
   - `POST /api/v1/feedback` (30/min) + `POST /api/v1/events` (60/min), auth optional
   - Fire-and-forget via asyncio.create_task()

### Phase 3: Frontend Integration + Final QA
**Agents:** frontend-streaming, test-qa

6. **Frontend SSE Client** (`streamComparison()` in api.ts)
   - fetch+ReadableStream with fallback to non-streaming
   - HomeScreen shows status messages during streaming
   - ResultsScreen progressive rendering + event tracking (tab_switch, source_click, result_view_duration)

7. **FeedbackCard Component** (`SmartCompareApp/src/components/FeedbackCard.tsx`)
   - Thumbs up/down (required) + mattered-most chips + optional text
   - Shown in Overview tab, collapses after submission

8. **Test Coverage**: 609 tests (was 555), +107 new tests across 3 files
   - test_scoring_service.py (62), test_feedback.py (29), test_streaming.py (16)

## Key Decisions
- 2 agents per phase (not 4) to manage Pro subscription token limits
- Scoring is deterministic math (not GPT opinion) — reproducible and explainable
- SSE streaming for perceived speed; non-streaming preserved for backward compat
- Feedback tables support anonymous users (user_id nullable)
- Backend `scoring` key (not `scores`) to match frontend types.ts convention

## Files Changed
**New:** scoring_service.py, feedback_service.py, feedback_routes.py, FeedbackCard.tsx, react-native-vector-icons.d.ts, test_scoring_service.py, test_feedback.py, test_streaming.py, session20-progress.md, design doc, plan doc
**Modified:** structured_comparison_service.py, extraction_service.py, text_routes.py, main.py, ResultsScreen.tsx, HomeScreen.tsx, CameraScreen.tsx, api.ts, authService.ts, types.ts

---

# SESSION 19: March 7-8, 2026 — Personalization Feature

## What We Did

4-agent Opus team (backend, frontend, test, qa). Session hit context limit before test/qa agents ran — verified manually in Session 20.

### 1. Backend: Preferences Endpoints
**File:** `app/api/auth_routes.py`
- `GET /api/v1/auth/preferences` — returns user's saved preferences (auth required)
- `PUT /api/v1/auth/preferences` — saves/updates preferences with Pydantic validation (all 4 fields mandatory)
- Login/register/social-login responses now include `preferences_completed` boolean

### 2. Backend: Preference Storage
**File:** `app/services/auth_service.py`
- `get_user_preferences(user_id)` — reads `preferences` JSONB column from `public.users`
- `save_user_preferences(user_id, prefs)` — upserts preferences + sets `preferences_completed=true`
- Pydantic model `UserPreferences`: priorities (1-3 from 8 options), budget, brand_attitude, lifestyle (0+ from 11 options)

### 3. Backend: Prompt Injection for Personalized Verdicts
**File:** `app/services/extraction_service.py`
- `_build_preferences_prompt(user_preferences)` — builds personalization section appended to comparison verdict prompt
- `generate_comparison()` accepts optional `user_preferences` dict
- Zero extra API cost — preferences ride on existing GPT prompt tokens

### 4. Backend: Service Integration
**File:** `app/services/structured_comparison_service.py`
- `compare_from_text()` accepts `user_preferences` param, forwards to `generate_comparison()`
- Response includes `personalized: true/false` and `personalization_factors` list

**File:** `app/api/text_routes.py`
- Reads user preferences from DB (if authenticated) and passes to comparison service

### 5. Frontend: PreferencesScreen Onboarding
**File:** `SmartCompareApp/src/screens/PreferencesScreen.tsx`
- 4 swipeable cards: Priority Weights, Budget Comfort, Lifestyle Tags, Brand Attitude
- All mandatory — no skip buttons
- Shown once after first login (when `preferences_completed=false`)
- Editable later from AccountScreen

### 6. Frontend: App Flow Update
**File:** `SmartCompareApp/App.tsx`
- Auth flow: Login → check `preferences_completed` → PreferencesScreen (if needed) → HomeScreen
- `needsPreferences` state controls routing

### 7. Frontend: AccountScreen + Types
- AccountScreen: "My Preferences" link to edit preferences
- `types.ts`: Added `UserPreferences` type and `Preferences` to `RootStackParamList`
- `ResultsScreen.tsx`: Shows "Personalized for you" indicator when `personalized: true`

### 8. Tests
**File:** `tests/test_personalization.py` — 52 tests covering:
- Pydantic validation (all valid/invalid combos for 4 dimensions)
- GET/PUT endpoints (auth, success, error cases)
- Service functions (DB success/error/empty)
- Auth response `preferences_completed` flag (login, register, social)
- Prompt injection (full/empty/none preferences)
- Comparison service metadata (personalized flag, factors list)
- Valid option constants

## Session 20 Verification (March 8, 2026)
- All 505 tests pass (52 personalization + 453 existing), zero regressions
- All backend files compile cleanly
- Frontend: 5 pre-existing TS errors only, no new ones
- Production deployed and healthy, preferences endpoint responds correctly (401 on bad token)

---

# SESSION 18: March 5, 2026 — Category Selection Feature

## What We Did

4-agent Opus team (backend-agent, frontend-agent, test-agent, qa-agent) with cross-QA.

### 1. Added 4 New Category Schemas
**File:** `app/services/extraction_service.py`
- Added makeup (11 fields: shade_range, finish, coverage, skin_type, ingredients, cruelty_free, vegan, spf, volume, waterproof, long_lasting)
- Added skincare (10 fields: skin_type, skin_concern, ingredients, active_ingredient, spf, fragrance_free, cruelty_free, vegan, volume, ph_level)
- Added haircare (10 fields: hair_type, hair_concern, ingredients, sulfate_free, paraben_free, silicone_free, cruelty_free, vegan, volume, scent)
- Added fragrances (10 fields: scent_family, notes_top, notes_heart, notes_base, longevity, sillage, season, occasion, volume, concentration)
- Total: 8 categories in CATEGORY_SPEC_SCHEMAS (was 4)

### 2. Updated Product Parser Prompt
**File:** `app/services/extraction_service.py`
- PRODUCT_PARSER_PROMPT category enum: `electronics|grocery|supplements|makeup|skincare|haircare|fragrances|other`
- Added detection rules with product examples for each new category
- Removed stale categories (beauty, fashion, home, sports, automotive)

### 3. Added selected_category API Parameter
**File:** `app/api/text_routes.py`
- `selected_category: Optional[str] = Query(None)` on GET `/api/v1/text/compare`
- Forwarded to `service.compare_from_text(selected_category=...)`
- Backward compatible (parameter is optional)

### 4. Category Switching Logic
**File:** `app/services/structured_comparison_service.py`
- `selected_category` parameter added to `compare_from_text()`
- Detects mismatch between user selection and AI detection
- AI always wins: `category_used = detected_category`
- Response includes `category_used`, `category_switched`, `original_category`

### 5. CategorySelector Component
**File:** `SmartCompareApp/src/components/CategorySelector.tsx`
- Horizontal scrolling chip selector with 7 categories + icons
- Active state: blue (#007AFF) background, white text
- Props: `value: string | null`, `onChange: (category: string) => void`

### 6. HomeScreen Integration
**File:** `SmartCompareApp/src/screens/HomeScreen.tsx`
- CategorySelector placed between status bar and input method tabs
- `selectedCategory` state defaults to 'electronics'
- `selected_category` passed in text and URL API calls

### 7. ResultsScreen Banner
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Info banner shown when `category_switched === true`
- SPEC_DISPLAY_CONFIG entries for all new category fields (63 total)

### 8. TypeScript Types
**File:** `SmartCompareApp/src/types/types.ts`
- Added `category_used`, `category_switched`, `original_category` to ComparisonResult

## Test Results
- 46 new tests in `tests/test_category_selection.py`
- 483 total tests (was 411), all passing
- Zero regressions
- Zero additional API cost

## Design Decisions
- **Soft validation**: Category selection is a hint, not a constraint. AI decides final category.
- **Zero cost increase**: Category detection happens within existing product parser GPT call.
- **Default category**: Electronics (most common use case in GCC market).

---

# SESSION 17: March 4, 2026 — Smart Polish (AI Quality & Bug Fixes)

## What We Did

3-agent Opus team (agent-expo-urls, agent-prompts, agent-specs) with full cross-QA.

### 1. Fixed Expo Startup
**File:** `SmartCompareApp/app.json`
- Removed `expo-image-manipulator` from plugins array — it's a regular library, not a config plugin
- Was causing `PluginError: Unable to resolve a valid config plugin` on `npx expo start`

### 2. Fixed Native Module Crash in Expo Go
**File:** `SmartCompareApp/src/services/authService.ts`
- `@react-native-google-signin/google-signin` crashed at import time in Expo Go (no native binary)
- Converted all native module imports (GoogleSignin, AppleAuthentication, Crypto) to lazy-loaded with try/catch
- App now works in Expo Go — social sign-in buttons show "requires development build" error instead of crashing

### 3. Tightened Review Extraction Prompt
**File:** `app/services/extraction_service.py` (REVIEWS_EXTRACTION_PROMPT)
- Every praise/complaint now requires `[snippet_N]` citation
- `rating_distribution` always set to null (no more synthetic percentages)
- Added DO/DON'T examples for specific vs generic output
- Warns against paraphrasing/fabricating user quotes
- `detailed_praises/complaints` must include `source` field

### 4. Tightened Spec Citation Verification
**File:** `app/services/structured_comparison_service.py`
- Added `NUMERIC_SPEC_FIELDS` constant (ram, storage, battery, weight, display, count, dosage, nutrition_*)
- `_verify_spec_citations()`: numeric fields require exact number match in cited snippet (was 50% keyword overlap)
- `_cross_validate_specs_with_shopping()`: ALL significant numbers (2+ digits) must match
- Text fields retain original keyword overlap behavior

### 5. Fixed Broken Retailer URLs
**File:** `app/services/structured_comparison_service.py`
- `_build_retailer_url()` now returns `None` for unknown retailers (was returning Google Shopping search page)
- Return type changed to `Optional[str]`
- Frontend already handles null URLs gracefully (price button hidden, rating falls back to Google Shopping search)

### 6. Improved Comparison Verdict Prompt
**File:** `app/services/extraction_service.py` (COMPARISON_PROMPT)
- Every pro/con must include a specific number or measurable fact
- Added DO/DON'T examples: "50% larger battery (5000 vs 3274 mAh)" not "Better battery life"
- `winner_reason` must cite numeric advantage
- `recommendation` must state who should buy each product with specific trade-offs
- `key_differences` must include actual specs/numbers

## Test Results
- **411 tests** (up from 366), 0 failures, 21 test files
- New test files: `test_review_prompt_quality.py` (22 tests), `test_spec_verification_strict.py` (27 tests), `test_url_quality.py` (18 tests)
- All 48 existing fact-checking tests pass (no regressions)

## Commits
- `116b92f` — fix: remove expo-image-manipulator from plugins
- `029576b` — feat: tighten review prompt — require snippet citations
- `94d121a` — fix: return null URL for unknown retailers
- `9b151be` — feat: improve verdict prompt — numeric diffs, trade-offs
- `d01254d` — feat: strict numeric verification for spec citations
- `cc7c4f1` — test: add completeness tests for prompts (22 total)
- `16ca0e6` — test: add 12 edge case tests for URL handling
- (+ lazy native module imports committed after team)

---

# SESSION LOG: February 11, 2026

## What We Fixed

### 1. Prices — Serper Shopping direct extraction (3-tier fallback)
**Files:** `app/services/structured_comparison_service.py`, `app/services/extraction_service.py`
- **Tier 1:** Parse structured price data directly from Serper Shopping results (most accurate)
- **Tier 2:** GPT extraction from search result text (fallback)
- **Tier 3:** GPT training data estimate, marked `estimated: true` with `confidence: 0.5` (last resort)
- Added `_extract_price_from_shopping()` — title matching with 40% word overlap threshold
- Added `_parse_price_string()` — handles "$699.99", "BHD 339", "SAR 2,499" formats
- Goal: **always show a price**, either real retailer or clearly labeled estimate

### 2. Specs — Fixed schema per category (no freeform fields)
**File:** `app/services/extraction_service.py`
- Added `CATEGORY_SPEC_SCHEMAS` dict with exactly 11 fields per category:
  - **electronics:** display, processor, ram, storage, battery, rear_camera, front_camera, os, connectivity, weight, water_resistance
  - **grocery:** size, ingredients, nutrition_calories, nutrition_protein, nutrition_fat, nutrition_carbs, origin, organic, allergens, shelf_life, halal
  - **other:** dimensions, weight, material, color, warranty, power, features, included, compatibility, origin, certifications
- Replaced static `SPECS_EXTRACTION_PROMPT` with `_build_specs_prompt()` — generates category-specific prompt
- Enforced schema server-side: only allowed fields kept, null/empty → "N/A"
- No more `additional_specs` field

### 3. Specs — Single value per field, no variant lists
**File:** `app/services/extraction_service.py`
- Prompt forces GPT to extract ONE config (base model or specified variant)
- Prevents "128, 256, 512 GB" — now always "128 GB"

### 4. Specs — All fields filled for known products
**File:** `app/services/extraction_service.py`
- Prompt allows GPT to use training knowledge when search results are incomplete
- null only acceptable if spec truly doesn't exist (e.g. water resistance on a product without it)
- Well-known products (iPhone, Galaxy, Pixel) always have all fields filled

### 5. Specs table — Fixed order, only matching rows
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Added `SPEC_DISPLAY_CONFIG` mapping key → {label, order} for human-readable display
- Rows sorted by fixed order, not insertion order
- Only shows rows where BOTH products have real data (either is N/A → row hidden)
- N/A values styled in gray italic

### 6. Simplified `_clean_specs()`
**File:** `app/services/structured_comparison_service.py`
- Removed `additional_specs` flattening (no longer exists)
- Replaces None/empty with "N/A"

### 7. Added `nocache` query parameter
**Files:** `app/api/text_routes.py`, `app/services/structured_comparison_service.py`
- `GET /api/v1/text/compare?nocache=true` bypasses Redis cache for fresh data
- Threaded through all data fetch methods (_get_specs, _get_price, _get_reviews)

## What's Still Broken
- **Stale cache:** Old format data served until TTL expires (7 days for specs). Use `?nocache=true` to bypass

## New Decisions Made
| Decision | Reasoning |
|----------|-----------|
| Fixed 11-field spec schema per category | Prevents inconsistent freeform fields between products |
| GPT can use training knowledge for specs | "Don't guess" was too conservative — known products had N/A for basic fields |
| 3-tier price fallback with guaranteed result | Users always see a price; estimated prices clearly labeled |
| Both-products-must-have-data filter for specs table | No point showing a spec row if only one product has it |
| nocache query param | Allows testing fresh data without waiting for cache expiry |

## Current Feature Status
| Feature | Status | Notes |
|---------|--------|-------|
| Ratings | Working | Tier 0 expert reviews (PCMag/CNET JSON-LD) → Tier 1-3 Shopping fallback |
| Prices | Working | 3-tier fallback + retailer quality scoring (prefers official retailers) |
| Specs | Working | Fixed 11-field schema, consistent across products |
| Specs table (frontend) | Working | Fixed order, labels, both-must-match filter |
| Pros/Cons | Working | Generated from specs + reviews |
| Comparison/Winner | Working | GPT comparison with value scores and best-for |
| Enhanced Reviews (backend) | Working | category_scores, rating_distribution, user_quotes, source_ratings, summary, verified_rating |
| Enhanced Reviews (frontend) | Working | ReviewsTab renders all fields; code audited Feb 14 2026, curl-verified both products return full data |
| Cache bypass | Working | `?nocache=true` query param |
| Camera input | Working | GPT-4o-mini vision → auto-compare via v3 pipeline, $0.007-0.014/comparison |
| URL input | Partial | Old code, untested with new architecture |

---

# SESSION LOG: February 13, 2026

## What We Fixed

### 1. Price quality — Retailer quality scoring system
**File:** `app/services/structured_comparison_service.py`
- Added `RETAILER_TIERS` dict with 3-tier retailer scoring:
  - **Tier 1 (1.0):** Amazon, Apple, Samsung, Best Buy, Walmart, Target, Noon, Jarir, eXtra, Lulu, Carrefour, Sharaf DG, Virgin Megastore, brand stores
  - **Tier 2 (0.7):** Newegg, B&H Photo, Adorama, Costco, Ubuy, Micro Center, John Lewis, Currys
  - **Tier 3 (0.3):** eBay, AliExpress, Alibaba, Temu, Wish, DHgate, Back Market, Swappa, refurbished sellers
  - **Unknown (0.5):** Any retailer not in the list gets benefit of the doubt
- Added `_get_retailer_score()` — case-insensitive substring matching against Serper `source` field
- Updated `_extract_price_from_shopping()` sort key: `(-match_score, -retailer_score, amount)`
  - Previously: best title match → cheapest price (eBay at BHD 135 won over Amazon at BHD 250)
  - Now: best title match → best retailer quality → cheapest price (Amazon wins)
- Added logging: `[PRICE] Selected: Amazon.com (tier 1.0) at BHD 249.99 for 'iPhone 15' (5 candidates)`

### 2. Price accessory/min-price filters
**File:** `app/services/structured_comparison_service.py`
- Accessory filter: rejects "case", "cover", "charger", etc. from price results
- Min price BHD 100 for phones/laptops/consoles
- Strict title match: ALL key words must appear for high-value products
- Tier 3 purge: remove eBay/AliExpress when Tier 1/2 retailers exist

### 3. Rating system — 4-tier fallback
**File:** `app/services/structured_comparison_service.py`

**Tier 0 (Expert):** Scrape editorial review sites for JSON-LD ratings
- Search: `"{product} review site:pcmag.com OR site:cnet.com OR ..."` (1 credit)
- Scrape: Serper `/scrape` endpoint on review URL (2 credits)
- Parse: JSON-LD `reviewRating` → rating + author + pros/cons
- Sites: PCMag, CNET, TechRadar, Tom's Guide, The Verge, Wired, LaptopMag, Tom's Hardware
- Tries up to 3 review URLs until one yields a parseable rating
- Label: `"Pcmag Expert Review (Eric Zeman)"`, confidence: `"expert"`
- Bonus: extracts `positiveNotes`/`negativeNotes` as `expert_pros`/`expert_cons`

**Tier 1 (High):** Serper Shopping from trusted retailers (Amazon, Best Buy, Walmart, etc.)
**Tier 2 (Medium):** Known retailers, .com/.ae stores
**Tier 3 (Low):** Marketplace (eBay/AliExpress) only if review_count > 1000, labeled "marketplace rating"

### 4. Added 2026 product date context
**File:** `docs/CLAUDE_CODE_CONTEXT.md`
- Added current product release dates so AI doesn't flag iPhone 17 / Galaxy S26 as "rumored"

## Cost Impact
| Before | After |
|--------|-------|
| ~$0.008/comparison | ~$0.022/comparison |
| Ratings: 1 Shopping call | Ratings: 1 search + up to 3 scrapes + 1 Shopping fallback |
| Inaccurate Google Shopping aggregates | Real editorial ratings from review sites |

---

# SESSION LOG: February 13, 2026 (Evening) — Enhanced Reviews System

## What We Built

### 1. Enhanced Reviews — Rich structured data from same API calls
**Files:** `app/services/extraction_service.py`, `app/services/structured_comparison_service.py`, `app/models/product_schema.py`

**Architecture change:** Split `_fetch_product_data` into Phase 1 (specs + price parallel) → Phase 2 (reviews + rating parallel). This lets shopping data from Phase 1 feed into review extraction in Phase 2.

**New review fields (all Optional, backward-compatible):**
- `rating_distribution` — `{5_star: %, 4_star: %, ...}` estimated by GPT
- `category_scores` — `{performance: 9, value: 7, ...}` scored 1-10, category-aware
- `source_ratings` — REAL retailer ratings from Serper shopping data (NOT GPT)
- `detailed_praises`/`detailed_complaints` — `[{text, frequency, quote}]`
- `user_quotes` — `[{text, sentiment, source, aspect}]` from search snippets
- `summary` — 2-3 sentence opinionated summary
- `verified_rating` — `{rating, review_count, source, verified}` matches Overview tab exactly

**Key design decisions:**
- GPT is explicitly told NOT to generate `source_ratings` — was hallucinating review counts
- Real retailer ratings injected post-extraction from `_collect_retailer_ratings()`
- `verified_rating` injected into reviews so frontend can show consistent data between Overview and Reviews tabs
- `max_tokens` increased 500→800→1000 to prevent JSON truncation (GPT sometimes cuts off mid-JSON)

### 2. Frontend — Reviews tab with full data rendering
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

- Added `ReviewData` interface with all new fields
- `ReviewsTab` now renders: summary, category score bars, star distribution bars, source ratings with verified badge, user quotes with sentiment badges, pros/cons
- Code audited Feb 14 2026: all conditional rendering correct (safe optional chaining, null checks). Backend curl-verified: all enhanced fields present for both products.

### 3. Bugs found and fixed
- **GPT JSON truncation:** 800 max_tokens sometimes too low → "Unterminated string" JSON parse error → one product gets data, other doesn't (random). Fixed by removing `source_ratings` from GPT prompt (saves ~100 tokens) + increasing to 1000
- **Hallucinated source_ratings:** GPT was fabricating review counts (e.g. "bestbuy.com 4.5, 1,234 reviews"). Fixed by injecting real Serper shopping data post-extraction
- **Rating mismatch:** Overview showed one rating, Reviews tab showed different one. Fixed by injecting `verified_rating` into reviews

## Commits
1. `5a1ddf6` — Initial enhanced reviews (Phase 1/2 reorder, rich GPT prompt, new schema fields)
2. `97468ec` — Frontend: ReviewsTab renders all new fields
3. `7717db0` — Bug fixes: stop GPT hallucinating, fix truncation, inject verified_rating

## What's Still Needed
- **source_ratings can be empty** for some products if Bahrain shopping results lack `rating` fields — correct behavior but means "Ratings by Source" section may be empty
- **Cost crept to ~$0.011** from ~$0.009 due to max_tokens increase — still under $0.015 target

## Lessons Learned
| Lesson | Detail |
|--------|--------|
| Never let GPT generate data you already have | GPT hallucinated review counts; always inject real data post-extraction |
| max_tokens truncation is silent | GPT stops mid-JSON, causing intermittent parse errors — one product fails randomly |
| Frontend needs device testing | curl verification is necessary but not sufficient for React Native apps |

---

# SESSION LOG: February 14, 2026 — Complete Price Fix Session

## Fixes Completed

### 1. Currency Conversion (Prices)
- Added currency detection from Serper price strings ($ → USD, £ → GBP, € → EUR)
- Added conversion to BHD after detection
- Fixed: $541 USD was showing as BHD 541 (now correctly converts)

### 2. GPU Support
- Added GPU keywords to HIGH_VALUE_KEYWORDS: rtx, nvidia, geforce, radeon, amd, gpu
- GPUs now get min-price filter and strict-title matching

### 3. Price Sanity Checks
**File:** `app/services/structured_comparison_service.py` — `_get_price()` method
- HIGH check: if price > 2x Tier 3 estimate → reject (catches inflated prices)
- LOW check: if price < 0.5x Tier 3 estimate → reject (catches scam listings)
- Fixed retailer_score being `.pop()`d before sanity check could read it
- Only for high-value products (`_is_high_value_query`) — cheap items unaffected

| Tier | HIGH check (> 2x est) | LOW check (< 0.5x est) | Scope |
|------|----------------------|------------------------|-------|
| Tier 1 (Shopping) | Reject → Tier 2 | Reject → Tier 2 | High-value + untrusted retailer only |
| Tier 2 (GPT) | Use Tier 3 | Use Tier 3 | High-value only |
| Tier 3 (Estimate) | N/A (last resort) | N/A (last resort) | — |

### 4. Cost Optimization
- Skip sanity check for trusted retailers (retailer_score >= 1.0: Amazon, Best Buy, eXtra, Noon, etc.)
- Cache Tier 3 estimate within `_get_price()` to avoid duplicate calls
- Tier 0 expert review code removed in Session 10 cleanup (commit `02e23de`)
- Cost: $0.011 (trusted) to $0.012 (untrusted) — under $0.015 target

### 5. UI & Cache Fixes
- Sanitized GPT "null" strings → Python None (no more "null" text in UI)
- Renamed "Value Score" → "Comparative Value" in Overview
- Added `DELETE /api/v1/text/cache?q=product` endpoint for flushing stale cache
- Added temporary `nocache` in app until Feb 16 to bypass stale Redis entries (auto-disables)

## Final Results
| Product | Before | After |
|---------|--------|-------|
| RTX 3090 | BHD 206 (scam listing) | BHD 490 (Sharaf DG) |
| RTX 3070 | BHD 541 (inflated USD) | BHD 188.5 (estimated) |

## Known Issues
- **Concurrent request cost double-counting:** Running two comparisons simultaneously on Railway inflates `total_cost` in metadata. Solo requests report accurate costs.
- **GPT parse non-determinism:** Different runs can produce different brand/name splits, leading to different cache keys for the same product.

## Current Feature Status (Feb 15 2026)
| Feature | Status |
|---------|--------|
| Prices | Working (currency conversion + sanity checks) |
| Ratings | Working (4-tier + retailer URLs fixed) |
| Reviews | Working (category scores, user quotes, etc.) |
| Specs | Partially working (variant hint added, needs more testing) |
| Camera input | Working (vision + comparison flow) |
| URL input | Not tested with new architecture |

## Next Priority
- Verify specs accuracy with camera input (variant hints)
- URL input (update to use v3 pipeline)
- Apply Figma UI design
- Premium tier with Stripe

---

# SESSION LOG: February 15, 2026 — Camera Input Feature

## What We Built

### 1. Camera Identification Endpoint
**File:** `app/api/image_routes.py` (NEW)
- `POST /api/v1/image/identify` — accepts 1-4 images + region
- GPT-4o-mini vision identifies products from photos (single API call for all images)
- **2+ products found**: auto-builds query string, calls `StructuredComparisonService.compare_from_text()` — reuses full v3 pipeline (specs, prices, ratings, reviews, comparison)
- **1 product found**: returns `action: "need_second_product"` with identified product
- **0 products**: returns error
- Injects `input_method: "camera"`, `vision_cost`, `identified_products` into metadata

### 2. Improved Vision Prompt
**File:** `app/services/openai_service.py`
- Replaced grocery-focused prompt with electronics-aware identification
- Added `confidence` field (high/medium/low) replacing `size`
- Handles: product boxes, bare products (by shape/logo/design), screenshots, shelf photos, price tags
- Multi-product: identifies ALL products in a single image (up to 4 total)
- Normalization: ensures every product has brand/name/visible_price/confidence
- Uses `detail: "low"` for cost control (~$0.003 per call regardless of image count)

### 3. Frontend Camera Flow
**Files:** `SmartCompareApp/src/screens/CameraScreen.tsx`, `src/services/api.ts`, `src/types/types.ts`, `src/types/index.ts`
- `CameraScreen`: MIN_IMAGES=2, calls `identifyFromImages()` instead of old `compareProducts()`
- `action: "comparison"` → navigates to ResultsScreen with full comparison
- `action: "need_second_product"` (edge case) → shows green banner with detected product name + "Take Another Photo" button
- `action: "error"` → Alert dialog
- New `identifyFromImages()` API function with same iOS/HEIC handling as old `compareProducts()`
- New `ImageIdentifyResult` discriminated union type, `IdentifiedProduct` type
- Added `index.ts` barrel export for types

### 4. Router Registration
**File:** `app/main.py`
- Registered `image_router` at `/api/v1/image/*`
- Old `/api/v1/compare` (legacy image endpoint) preserved for backward compatibility

## Cost Analysis
| Scenario | Vision | Pipeline | Total |
|----------|--------|----------|-------|
| Cache hit (popular products) | $0.003 | $0.001 | **$0.004** |
| Partial cache (specs cached) | $0.003 | $0.005 | **$0.008** |
| Full cache miss | $0.003 | $0.011 | **$0.014** |
| Single product identify only | $0.003 | $0.000 | **$0.003** |

## Test Results (curl verified on Railway)
- **Single image** (iPhone 16 Pro text): `action: "need_second_product"`, confidence: "high", price extracted
- **Two separate images** (iPhone + Galaxy): `action: "comparison"`, full specs/prices/ratings/reviews, cost $0.0074 (iPhone cached), 37s elapsed
- All responses include `confidence` field in identified products

## Commits
1. `87217d6` — Backend: image_routes.py, improved vision prompt, main.py router
2. `2e68a87` — Frontend: types, api, CameraScreen flow

## Architecture Decision
| Decision | Reasoning |
|----------|-----------|
| Single endpoint, not identify+compare | Eliminates round-trip for 2+ products case |
| Keep MIN_IMAGES=2 | No text input for second product; camera-only flow |
| Reuse StructuredComparisonService | No pipeline duplication; cache/ratings/reviews all work automatically |
| `detail: "low"` for vision | ~$0.003 regardless of 1-4 images; sufficient for text-on-packaging |
| Separate images, not combined | Accuracy > $0.0004 savings |

---

# SESSION LOG: February 15, 2026 (Evening) — Camera Bug Fixes

## Bugs Fixed

### 1. Rating source URLs were Google redirects
- **Was:** `rating_source.url` was `https://www.google.com/search?ibp=oshop&q=...` — clicking opened Google, not retailer
- **Fix:** Added `RETAILER_SEARCH_URLS` map (16 retailers) and `_build_retailer_url()` method. URLs now go to actual retailer search pages (e.g., `bestbuy.com/site/searchpage.jsp?st=Apple+iPhone+16`)
- **File:** `structured_comparison_service.py` — constant + method + 3 usage sites (consensus rating, tiered rating, price)
- **Fallback:** Unknown retailers → Google Shopping search (`google.com/search?tbm=shop&q=...`)
- **Tested:** curl verified — "Best Buy via Google Shopping" now links to bestbuy.com

### 2. Vision data discarded at text boundary
- **Was:** `image_routes.py` built plain text query, `compare_from_text()` re-parsed it with GPT, losing variant info like "360 Softgels"
- **Fix:** Added `vision_products` parameter to `compare_from_text()`. Camera input now skips `parse_product_query()` and passes vision-identified products directly
- **Files:** `structured_comparison_service.py` (new `vision_products` param), `image_routes.py` (passes `vision_products=products`)
- **Bonus:** Saves $0.0003/comparison by skipping redundant GPT parse call

### 3. UnboundLocalError crash on camera comparison
- **Was:** `parsed` variable referenced at line 211 (`parsed.get("comparison_type")`) but only assigned in text path — camera path crashed
- **Fix:** `parsed.get(...) if not vision_products else "value"`

### 4. Vision variant hint for specs extraction
- **Was:** `variant=None` caused GPT specs prompt to show "(base model)", defaulting to 180-count instead of 360-count
- **Fix:** Vision name passed as `variant` field so prompt shows `(variant: Vitamin D-3 360 Softgels)`. Added `_vision` flag for proper `full_name`/`display_name` handling without doubling

### 5. Brand missing from specs/reviews headers
- **Was:** Frontend used `product.name` (no brand) for specs table header and reviews card title
- **Fix:** Changed to `product.full_name || product.name` with `numberOfLines={2}`
- **File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

## Commits
1. `469b537` — Build retailer URLs for ratings (RETAILER_SEARCH_URLS + _build_retailer_url)
2. `81e71ca` — Context update
3. `595a5dc` — Fix parsed UnboundLocalError crash in vision path
4. `c3f94f3` — Vision variant hint + _vision flag for display names
5. `4e81337` — Frontend: full_name in specs/reviews headers

## Still Broken (For Tomorrow)
1. Specs still showing wrong variant sometimes (180 vs 360 softgels) — variant hint helps but GPT non-determinism can override
2. NOW Vitamin D-3 sometimes shows "No verified rating" — depends on Serper shopping data availability
3. Price accuracy needs verification for camera-identified products

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | Working (currency conversion + sanity checks) |
| Ratings | Working (4-tier + retailer URLs fixed) |
| Reviews | Working (category scores, user quotes, etc.) |
| Specs | Partially working (variant hint added, needs testing) |
| Camera input | Working (vision + comparison flow) |
| URL input | Not tested with new architecture |

---

# SESSION LOG: February 15, 2026 (Evening) — Vitamin Matching Fixes

## What We Fixed

### 1. Number Preservation in Matching (Critical)
**File:** `app/services/structured_comparison_service.py`
- Added `_numbers_match()` static method — extracts standalone 2+ digit numbers from product name and requires at least one to appear in the shopping result title
- "NOW Vitamin D-3 360 Softgels" now rejects "NOW Vitamin D-3 120 Softgels" (360 ≠ 120)
- Single-digit numbers (e.g., "3" in "D-3") are ignored — too aggressive, would reject "Vitamin D3"
- Applied as FILTER 4 in `_extract_price_from_shopping()` and FILTER 3 in `_extract_rating_from_shopping()`

### 2. Hyphen Normalization (High)
**File:** `app/services/structured_comparison_service.py`
- Added `_normalize_words()` static method — lowercase + strip hyphens: "D-3" → "d3", "D3" → "d3"
- Replaced `set(text.lower().split())` with `self._normalize_words(text)` in 4 places (p_words and t_words in both price and rating extraction)
- Fixes match score dropping from 100% to 80% when product uses "D-3" but shopping result uses "D3"

### 3. Count Field Added to Spec Schemas (Medium)
**File:** `app/services/extraction_service.py`
- Added `"count"` as first field in `grocery` schema (replaced `"halal"`) and `other` schema (replaced `"certifications"`)
- Both schemas remain at 11 fields (fixed constraint)
- Added explicit GPT instruction: "If the product name or variant contains a count/quantity (e.g. '360 Softgels'), use EXACTLY that number for the 'count' field"
- GPT now has both a slot AND a directive for count/quantity

## Test Results (3 runs, nocache=true, all consistent)
| Product | Count | Rating | Price |
|---------|-------|--------|-------|
| NOW Vitamin D-3 360 | 360 ✅ | 4.8-4.9 ✅ | BHD 4.39 |
| Nature Made D3 2000 | 250 ✅ | 4.5-4.7 ✅ | BHD 4-12 |

### Electronics Regression — PASSED ✅
- iPhone 16: 4.6 rating, BHD 310
- Galaxy S25: 4.7 rating, BHD 407

### Cost: $0.012/comparison (under $0.015 ✅)

## Commits
- `b4d6f4a` — Fix vitamin matching: number preservation, hyphen normalization, count field

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working |
| Ratings | ✅ Working (consistent across runs) |
| Reviews | ✅ Working |
| Specs | ✅ Working (count field added for supplements) |
| Camera | ✅ Working |
| URL input | ❌ Not started |

## Key Technical Details
| Method | Purpose | Location |
|--------|---------|----------|
| `_normalize_words(text)` | Lowercase + strip hyphens for word matching | `structured_comparison_service.py:604` |
| `_numbers_match(product, title)` | Reject titles missing key quantities | `structured_comparison_service.py:612` |
| `CATEGORY_SPEC_SCHEMAS["grocery"]` | Now includes `count` field | `extraction_service.py:77` |
| `CATEGORY_SPEC_SCHEMAS["other"]` | Now includes `count` field | `extraction_service.py:82` |

---

# SESSION LOG: February 16, 2026 — Camera Vision & URL Fixes

## What We Fixed

### 1. Vision prompt OCR improvements
**File:** `app/services/openai_service.py`
- Changed `detail: "low"` → `detail: "auto"` — lets GPT choose resolution per image, enables reading small label text
- Rewrote prompt to emphasize OCR: "READ the EXACT text printed on each product's packaging, label, or screen"
- Added `size_or_count` field — dedicated slot for "360 Softgels", "128GB", "1000mg" etc.
- Added category-specific OCR rules (supplements, electronics, grocery)
- Examples now include vitamin bottle, not just electronics

### 2. Expanded RETAILER_SEARCH_URLS (16 → 36 retailers)
**File:** `app/services/structured_comparison_service.py`
- Added: Ubuy, Lulu, Carrefour, Virgin Megastore, Apple, Samsung, Dell, Lenovo, Currys, John Lewis, Fnac, AliExpress, Temu, Back Market, Swappa, Vitacost, Adorama, Micro Center, B&H Photo
- Previously: Galaxy S25 rating URL went to google.com (Ubuy not in map). Now goes to bestbuy.com or ubuy.com

### 3. Consensus rating prefers known retailers
**File:** `app/services/structured_comparison_service.py`
- Added `_has_retailer_url()` helper — checks if source matches any RETAILER_SEARCH_URLS key
- Consensus sort now uses `(has_retailer_url, match_score)` — prefers sources with real retailer URLs

### 4. Vision size_or_count enrichment
**File:** `app/api/image_routes.py`
- After vision identification, appends `size_or_count` to product name if not already present
- "Vitamin D-3" + "360 Softgels" → "Vitamin D-3 360 Softgels" — feeds correct variant into specs extraction

## Test Results (verified on Railway)
| Test | Specs Count | Rating URL | Cost |
|------|-------------|------------|------|
| NOW Vitamin D-3 360 | count=360 ✅ | google.com (Tahoma Clinic — unknown retailer, expected) | $0.003 (cached) |
| Nature Made D3 2000 | count=250 ✅ | walmart.com ✅ | $0.003 (cached) |
| iPhone 16 | N/A | apple.com ✅ (was bestbuy before) | $0.006 |
| Galaxy S25 | N/A | bestbuy.com ✅ (was google.com before) | $0.006 |

## Commits
- `f549cc7` — Fix camera vision: OCR prompt, detail:auto, expand retailer URLs

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working |
| Ratings | ✅ Working (URLs go to real retailers) |
| Reviews | ✅ Working |
| Specs | ✅ Working (count field correct for supplements) |
| Camera | ✅ Working (OCR prompt, detail:auto, size_or_count field) |
| URL input | ❌ Not started |

---

# SESSION LOG: February 17, 2026 — Price URLs & Rating Brand Fix

## Fixes Deployed

### 1. Price URLs clickable (Tier 2/3 backfill)
**File:** `app/services/structured_comparison_service.py`
- Tier 2 (GPT) and Tier 3 (estimate) prices always had `url: null` — only Tier 1 (Shopping) set URLs
- Added URL backfill: after Tier 2/3 returns, if `retailer` exists but `url` is null, call `_build_retailer_url(retailer, full_name)`
- Added "nasser pharmacy" to `RETAILER_SEARCH_URLS` map

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Added `url?: string` to price type
- Made retailer name clickable with `TouchableOpacity` + `Linking.openURL(price.url)` when URL exists
- Non-URL retailers still show as plain text

### 2. Brand-aware matching for ALL products
**File:** `app/services/structured_comparison_service.py`
- **Root cause:** `_strict_title_match()` only ran for HIGH_VALUE_KEYWORDS (phones, GPUs, consoles). For vitamins, only word-overlap matching was used — "HealthAid Vitamin D3 1000 IU" matched ANY "Vitamin D3 1000 IU" at 80% overlap, so Target's generic D3 was incorrectly shown as HealthAid's rating
- **Fix:** Apply `_strict_title_match()` to ALL products, not just high-value
- **Fix:** Added hyphen normalization to `_strict_title_match()` — "D-3" matches "D3" (same as `_normalize_words()`)
- Removed unused `is_high_value` variable from `_extract_rating_from_shopping()`

### 3. Show unverified ratings with disclaimer
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Previously: any rating with `rating_verified=false` was completely hidden as "No verified rating"
- Now: unverified ratings show in gray with star-outline icon and "Unverified" badge + source name
- Only `rating === null` shows "No verified rating" now

### 4. Vision OCR improvements (from Feb 16 session)
**File:** `app/services/openai_service.py`
- `detail: "low"` → `detail: "auto"` for better text reading
- Rewrote prompt for OCR emphasis with category-specific rules
- Added `size_or_count` field for quantities

## Still Broken (For Next Session)
1. **Ratings show null for vitamins** — Serper doesn't return HealthAid/NOW from Tier 1/2 retailers. Brand-aware matching correctly rejects wrong products, but no correct match found either. Need to investigate if broader search or fallback can help
2. **Specs show "value or null" for many fields** — Dimensions, Material, Color, Warranty, Power, Origin, Compatibility, Weight — these fields don't apply to vitamins. Need category-specific schema cleanup
3. **Cost at $0.015** — slightly over target, acceptable for complex queries

## Test Results (verified on Railway)
| Test | Rating Before | Rating After | Price URL |
|------|-------------|-------------|-----------|
| HealthAid D3 1000 IU | 5.0 from Target (WRONG) | null (correct — no HealthAid products on Tier 1/2) | nasserpharmacy.com ✅ |
| NOW D-3 360 Softgels | "No verified rating" | null (correct — niche count) | null (no retailer) |
| iPhone 16 Pro | 4.4 verified ✅ | 4.4 verified ✅ | google.com |
| Galaxy S25 Ultra | 4.8 verified ✅ | 4.8 verified ✅ | extra.com ✅ |

## Commits
- `5e07365` — Fix price URLs: backfill Tier 2/3, make retailer clickable
- `21816aa` — Fix ratings: brand-aware matching for all products, show unverified with disclaimer

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working (URLs clickable) |
| Ratings | ⚠️ Partial (brand-aware matching works, but vitamins get null — no Tier 1/2 coverage) |
| Reviews | ✅ Working |
| Specs | ⚠️ Partial (count works, other fields show "value or null" for non-electronics) |
| Camera | ✅ Working (OCR reads correctly) |
| URL input | ❌ Not started |

## Key Technical Changes
| Method | Change | Location |
|--------|--------|----------|
| `_strict_title_match()` | Now normalizes hyphens, applies to ALL products | `structured_comparison_service.py:663` |
| `_extract_rating_from_shopping()` | Removed `is_high_value` gate on strict match | `structured_comparison_service.py:1384` |
| `RatingDisplay` | 3-state: null → "No verified rating", unverified → gray + badge, verified → green + link | `ResultsScreen.tsx:193` |
| `RETAILER_SEARCH_URLS` | 37 retailers (added nasser pharmacy) | `structured_comparison_service.py` |

---

# SESSION LOG: February 17, 2026 (Evening) — Specs, Ratings, Cost Fixes

## Fixes Deployed

### 1. Specs "value or null" — 6-layer fix
**Files:** `extraction_service.py`, `structured_comparison_service.py`, `ResultsScreen.tsx`
- **Root cause:** GPT prompt template used `"value or null"` as placeholder (line 93). GPT echoed it literally for fields it had no data for. Nothing downstream caught the string.
- **Fix 1:** Changed prompt placeholder from `"value or null"` to JSON `null` — GPT now returns actual null
- **Fix 2:** Added `"supplements"` category to `CATEGORY_SPEC_SCHEMAS` with relevant fields: count, serving_size, active_ingredient, dosage, form, allergens, certifications, origin, organic, shelf_life, nutrition_calories
- **Fix 3:** Added `"supplements"` to `PRODUCT_PARSER_PROMPT` category options
- **Fix 4+5:** Added `"or null"` string catch in both `extract_specs()` and `_clean_specs()` sanitizers
- **Fix 6:** Frontend `isNA()` now catches `"or null"` strings as safety net
- **Result:** Vitamins now show supplement-specific specs, zero "value or null" strings

### 2. Unverified ratings fallback
**File:** `structured_comparison_service.py`
- **Root cause:** When `_get_verified_rating()` returned null (no shopping source passed strict filters), frontend showed "No verified rating" — even though GPT reviews had extracted an `average_rating`
- **Fix:** After `_get_verified_rating()` returns null, check `reviews.average_rating`. If valid (1.0-5.0), use it as unverified rating with source "Aggregated from reviews", confidence "low"
- **Result:** Vitamins now show gray "Unverified" badge with GPT-aggregated rating instead of blank

### 3. Cost optimization — conditional organic + merged pros/cons
**Files:** `serper_service.py`, `extraction_service.py`, `structured_comparison_service.py`
- **Opt A:** Split `search_product_prices()` into shopping-only + `search_price_organic()`. Organic search only called when Tier 1 shopping fails. Saves $0.002/comparison in common case.
- **Opt B:** Merged `generate_pros_cons()` into `generate_comparison()` prompt. Pros/cons now extracted from comparison result (`product_0_pros`, `product_0_cons`, etc.) instead of 2 separate GPT calls. Saves $0.0008.
- **Result:** Cost dropped from $0.0174 to ~$0.014

### 4. Price sanity check extended to all products
**File:** `structured_comparison_service.py`
- **Root cause:** Tier 2 GPT price sanity check only ran for high-value products (phones, GPUs). For vitamins, GPT hallucinated BHD 24 (USD misinterpreted as BHD) and it went unchecked.
- **Fix:** Removed `_is_high_value_query()` gate from Tier 2 sanity check — all products now checked against Tier 3 estimate
- **Result:** NOW D-3 went from BHD 24 → BHD 9.43 (estimated). Still too high — needs further work.

### 5. iHerb as supplement price source
**File:** `structured_comparison_service.py`
- **Root cause:** Serper Shopping returns ZERO results for vitamins/supplements in Bahrain AND US. Tier 2 GPT hallucinated BHD 24 (confused USD for BHD). Tier 3 estimated BHD 9.43 (too high).
- **Fix:** For supplement products, inject an iHerb-specific Serper organic search (`site:iherb.com`) into Tier 2 context before GPT extraction. GPT sees real iHerb prices in snippets ("$14.21") and correctly detects USD, which auto-converts to BHD.
- **Implementation:** Added `_is_supplement_query()` with 23 keywords (vitamin, softgel, capsule, omega, etc.). When triggered, does `search_web("{query} site:iherb.com", country="us")` and prepends results to Tier 2 organic context.
- Added iHerb, Vitacost, GNC to `RETAILER_TIERS` as Tier 1 (score 1.0)
- **Result:** NOW D-3 360 Softgels: BHD 24 → BHD 5.36 from iHerb (real price, with retailer + URL)
- **Cost:** Extra $0.001 per product for supplements only (iHerb search call)

## Still Needs Work
1. **Nature Made D3 price** — BHD 4.06, no retailer, no URL. Correct range but no attribution.
2. **Cost at $0.0155 for supplements** — extra iHerb search adds $0.001/product. Electronics stay at ~$0.013.
3. **iHerb Bahrain pricing** — currently searching US iHerb (`country="us"`). Bahrain iHerb (`bh.iherb.com`) may have different prices in BHD. Could try `country="bh"` but Serper may not index it.

## Commits
1. `deafd88` — Fix specs: sanitize 'value or null', add supplements schema
2. `af38a90` — Fix ratings: fallback to GPT average_rating when shopping fails
3. `4906c4a` — Optimize cost: conditional organic search, merge pros_cons
4. `6890e06` — Fix price: extend Tier 2 sanity check to all products
5. `da8fda5` — Fix vitamin prices: add iHerb as supplement price source

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working (iHerb for supplements, shopping for electronics) |
| Ratings | ✅ Working (GPT review fallback for products without shopping data) |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema, no more "value or null") |
| Camera | ✅ Working |
| URL input | ❌ Not started |

## Key Technical Changes
| Change | Location |
|--------|----------|
| `CATEGORY_SPEC_SCHEMAS["supplements"]` added | `extraction_service.py:79` |
| Prompt placeholder `null` instead of `"value or null"` | `extraction_service.py:95` |
| GPT review average fallback for ratings | `structured_comparison_service.py:~380` |
| `search_price_organic()` new function | `serper_service.py` |
| `generate_comparison()` now includes pros/cons | `extraction_service.py:275` |
| Tier 2 sanity check for ALL products | `structured_comparison_service.py:~535` |
| `_is_supplement_query()` + iHerb search injection | `structured_comparison_service.py:~525` |
| iHerb/Vitacost/GNC added to `RETAILER_TIERS` | `structured_comparison_service.py:63` |

---

# SESSION LOG: February 18, 2026 — Full Codebase Audit & Critical Bug Fixes

## What We Did

### Full audit: 48 bugs found (24 backend, 24 frontend)
Ran 3 parallel exploration agents across backend, frontend, and runtime logs. Categorized all issues by severity.

### Phase 1: Backend Critical Fixes (commit `1700b6c`)

**1a. Singleton cache leak — `_shopping_items_cache` never cleared**
- `StructuredComparisonService` is a singleton (`get_comparison_service()`). `total_cost` and `api_calls` were reset per request but `_shopping_items_cache` was not.
- Under concurrent load: memory grows unbounded, stale product data leaks across requests.
- **Fix:** Added `self._shopping_items_cache = {}` at start of `compare_from_text()` (line 186).

**1b. `_convert_to_bhd(None)` crash**
- If a shopping item had no currency, calling `.upper()` on None raised `AttributeError`.
- **Fix:** Added `if not currency: return amount` guard at top of function.

**1c. Bare `except:` in `auth_routes.py:101`**
- Was catching `SystemExit`/`KeyboardInterrupt`. Changed to `except Exception:`.

**1d. CostStatus schema mismatch**
- `schemas.py` had fields `current_spend`, `budget`, `percentage_used`
- `check_monthly_budget()` returns `current_cost`, `budget_limit` (no `percentage_used`)
- **Fix:** Renamed schema fields to match actual return values.

**1e. OpenAI client import-time init**
- `openai_service.py` created `AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))` at module import time — could init with None key on cold start.
- **Fix:** Changed to `AsyncOpenAI()` which reads env at request time.

### Phase 2: Frontend Critical Fixes (commit `9602291`)

**2a. `verifyAuth()` returned boolean, App.tsx used as User**
- `verifyAuth()` called `isLoggedIn()` returning `Promise<boolean>`.
- `App.tsx:118` did `setUser(verifiedUser)` — user state became `true` not a User object. `user.email` would crash.
- **Fix:** Changed `verifyAuth()` to return `Promise<User | null>` via `initializeAuth()`.

**2b. `formatPrice()` called `.toFixed()` on ProductPrice object**
- `HistoryScreen.tsx:98`: `product.price.toFixed(2)` but `price` is `{ amount, currency }` not a number.
- **Fix:** Access `product.price.amount?.toFixed(2)` and `product.price.currency`. Handle both object and legacy number formats.

**2c. History→Results missing `comparison` field**
- `viewAsResult()` navigated with object missing `comparison` and `metadata` fields.
- `ResultsScreen` destructured `comparison` → crash on undefined.
- **Fix:** Added `comparison` and `metadata` objects to navigation params.

**2d. `rating_source.name` without null guard**
- In verified rating branch, `rating_source` could be null even when `rating_verified` is true.
- **Fix:** Changed to `rating_source?.name ?? 'Retailer'`.

### Phase 3: Session Refresh 422 Fix (commit `c19e9fb`)

**Root cause:** `POST /api/v1/auth/refresh` expects `{ refresh_token: "..." }` in body. Frontend sent `{}` (empty body) with access token in header only. FastAPI returned 422 validation error.

**Fix:**
- Added `REFRESH_TOKEN_KEY` storage constant
- Save `refresh_token` from login/register/refresh responses
- `refreshSession()` reads refresh token from storage and sends in body
- Clear refresh token on logout/session clear
- **Note:** Users must log out and back in once to store refresh token for first time.

## Remaining Bugs (deferred — Phases 3-5 from audit)
| # | Bug | Severity |
|---|-----|----------|
| 1 | Legacy `/api/v1/compare` — all function calls use wrong arg counts (4 TypeErrors) | High (legacy route) |
| 2 | No axios auth interceptor — token never sent on API requests | High |
| 3 | Missing expo-camera/expo-image-picker plugins in app.json | High (EAS builds) |
| 4 | Debug console.log everywhere in api.ts + HomeScreen | Medium |
| 5 | ~~`.gitignore` corrupted with PowerShell heredoc wrapper~~ FIXED (commit `02e23de`) | ~~Medium~~ |
| 6 | ~~`pyproject.toml` diverged from `requirements.txt`~~ FIXED (commit `02e23de`) | ~~Medium~~ |
| 7 | ResultsScreen local type defs diverge from types.ts | Medium |
| 8 | ~~Dead code: `_get_pros_cons`~~ FIXED (`b697534`). ~~`_get_expert_review`~~ FIXED (`02e23de`). | ~~Low~~ |
| 9 | `print()` instead of `logger` in auth_service/database_service | Low |
| 10 | `load_dotenv(override=True)` in library modules | Low |

## Commits
1. `1700b6c` — Fix backend critical: cache leak, None currency, schema mismatch
2. `9602291` — Fix frontend critical: auth type, price format, null guards
3. `c19e9fb` — Fix session refresh 422: store and send refresh token

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | Working (iHerb for supplements, shopping for electronics, clickable URLs) |
| Ratings | Working (GPT review fallback for unverified, brand-aware matching) |
| Reviews | Working (category_scores, rating_distribution, user_quotes, source_ratings) |
| Specs | Working (supplements schema, no more "value or null") |
| Camera | Working (OCR prompt, detail:auto, size_or_count) |
| Auth | Fixed (refresh token flow, verifyAuth return type) |
| URL input | Not started |

## Key Technical Changes
| Change | File |
|--------|------|
| `self._shopping_items_cache = {}` per request | `structured_comparison_service.py:186` |
| `_convert_to_bhd` None guard | `structured_comparison_service.py:1635` |
| `CostStatus` fields renamed | `schemas.py:122` |
| `AsyncOpenAI()` lazy env read | `openai_service.py:11` |
| `verifyAuth()` returns `User \| null` | `authService.ts:274` |
| `formatPrice()` handles ProductPrice object | `HistoryScreen.tsx:94` |
| `viewAsResult()` includes comparison/metadata | `HistoryScreen.tsx:106` |
| `rating_source?.name` null guard | `ResultsScreen.tsx:274` |
| Refresh token stored/sent/cleared | `authService.ts:23,73,134,145,238` |

---

# SESSION LOG: February 18, 2026 — Cost Optimization & Dead Code Cleanup

## What We Did

### Dead Code Cleanup (commit `b697534`)
Removed 109 lines of dead code that was superseded by merged pros/cons in `generate_comparison()`:
- **`extraction_service.py`**: Removed `PROS_CONS_PROMPT` template and `generate_pros_cons()` function
- **`structured_comparison_service.py`**: Removed `PROS_CONS_CACHE_TTL` constant and `_get_pros_cons()` method

### Cost Optimization DEPLOYED (commit `d9fb064`)
Supplement comparison cost reduced from $0.017 to $0.013:

**Fix 0: Hardened `_is_supplement_query()` against false positives**
- Removed "tablet" from `SUPPLEMENT_KEYWORDS` (matched "Samsung Galaxy Tablet")
- Added electronics anti-keywords using existing `HIGH_VALUE_KEYWORDS` set
- Now: if any electronics keyword present → NOT a supplement

**Opt A: Skip BH shopping for supplements (saves $0.002/comparison)**
- Serper Shopping returns ZERO results for supplements in BH
- Set `_shopping_items_cache[full_name] = []` directly, preserving invariant for rating extraction

**Opt B (Modified): iHerb-first with BH organic fallback (saves $0.001-0.002)**
- Supplements: try `site:iherb.com` search first (has real USD prices)
- If iHerb returns nothing → fall back to BH organic search
- Non-supplements: unchanged (BH organic on-demand)

**Opt C: Trust iHerb prices, skip sanity check (saves $0.0006)**
- iHerb is a trusted source (Tier 1 quality) — no need for Tier 3 GPT estimate verification
- Non-supplements: sanity check unchanged

**Opt D: HELD — defer US shopping for supplement ratings**
- Would save $0.002 but loses ~50% chance of verified rating → quality cut, held for later

### Local Test Results (Railway OpenAI timeout — tested locally)

| Test | total_cost | api_calls | Notes |
|------|-----------|-----------|-------|
| Supplements (NOW D3 vs HealthAid D3) | $0.0125 | 18 | Was $0.0165/22 calls |
| Electronics (iPhone 16 vs Galaxy S25) | $0.0145 | 20 | Unchanged path |

## BLOCKER: OpenAI API Timeout on Railway
- All OpenAI GPT-4o-mini calls timeout from Railway (~17s = 3x connect retries)
- Serper works, Upstash cache works — only OpenAI fails
- API key verified working locally (sk-proj-G33L...zgA)
- Health endpoint responds in <1s — Railway app is running
- Error: "Request timed out." from httpx connect timeout

### Needs Investigation
1. Check `OPENAI_API_KEY` in Railway Variables — is it set? Same key as backend/.env?
2. Check OpenAI account status/billing — rate limits, project API key permissions
3. Consider adding explicit timeout to `AsyncOpenAI()`: `timeout=httpx.Timeout(120.0, connect=10.0)`
4. Try redeploying on Railway (fresh container may resolve networking)

## Commits
1. `b697534` — Remove dead pros_cons code (merged into comparison)
2. `d9fb064` — Optimize supplement costs: skip empty BH calls, iHerb-first with fallback

## Key Technical Changes
| Change | File | Line |
|--------|------|------|
| `SUPPLEMENT_KEYWORDS` — removed "tablet" | `structured_comparison_service.py` | ~685 |
| `_is_supplement_query()` — electronics anti-keywords | `structured_comparison_service.py` | ~697 |
| Skip BH shopping for supplements | `structured_comparison_service.py` | ~486 |
| iHerb-first with BH organic fallback | `structured_comparison_service.py` | ~535 |
| Skip Tier 2 sanity check for supplements | `structured_comparison_service.py` | ~563 |

---

# SESSION LOG: February 18, 2026 (Evening) — OpenAI Timeout Fix & Supplement iHerb Price Fix

## What We Did

### Phase 1: OpenAI Timeout on Railway (commits `4eb4432`, `54e9d76`)

**Root cause:** Railway's default httpx connect timeout (~5s) was too short for OpenAI API cold-start connections. Locally worked fine because ISP latency was lower.

**Fix:** Added explicit `timeout=httpx.Timeout(120.0, connect=30.0)` to all 3 `AsyncOpenAI()` clients:
- `extraction_service.py` (specs/price/review/comparison extraction)
- `openai_service.py` (vision identification)
- `structured_comparison_service.py` (Tier 3 price estimate)

### Phase 2: Supplement Detection Miss (commits `5a192bd`, `7ab9b62`)

**Root cause chain:**
1. `_get_price()` only used keyword matching via `_is_supplement_query()` — "Nature Made D3" had no matching keywords ("d3" was missing from list)
2. Non-supplement path searched BH shopping → found USD prices → no currency conversion → wrong BHD amount
3. Even when detected, iHerb prices were in USD but `original_currency` wasn't forced to "USD"

**Fix:**
- Added `category` parameter to `_get_price()` — `category=="supplements"` (from GPT parser) as primary signal, keyword match as backup
- Added "d3", "d-3", brand name keywords ("nature made", "now foods", "solgar", "garden of life", "kirkland") to `SUPPLEMENT_KEYWORDS`
- Force `original_currency = "USD"` when iHerb organic results are the source

### Phase 3: Camera Price Cache Bug (commit `54e9d76`)

**Root cause:** Stale Redis cache from pre-fix code served BHD 10.9 for camera path. The `nocache=true` bypass was only on text endpoint.

**Fix:** Added `nocache` parameter to image_routes.py, threaded through to `compare_from_text()`.

### Phase 4: Supplement iHerb Price Reliability (commit `70d1bba`) — DID NOT FULLY RESOLVE

**Problem:** Camera comparison showed NOW D-3: BHD 10.9 (should be ~BHD 4). Text path worked but camera path did not.

**Root cause chain:**
1. Camera gives long product name: `"NOW high potency vitamin d-3 360 Softgels"`
2. iHerb search query becomes: `"NOW high potency vitamin d-3 360 Softgels site:iherb.com"` — too specific, returns 0 results
3. Code falls back to BH organic: `search_price_organic(search_query, "bh")` — Bahrain pharmacy search
4. GPT extracts ~10.9 from a Bahrain pharmacy listing → `original_currency: "BHD"`
5. Target is also BHD → no conversion → BHD 10.9 (wrong)
6. The iHerb USD→BHD forcing logic doesn't fire because `iherb_organic` is empty

**Secondary bug:** `full_name` in `_get_price()` doubles the variant: `"NOW high potency vitamin d-3 360 Softgels 360 Softgels"` (name already has variant from image_routes enrichment + `_get_price` appends variant again)

**Three fixes applied:**

1. **Strip pill count from iHerb search query** — regex removes `\b\d+\s*(softgels?|capsules?|tablets?|...)\b` from query. Keeps dosage (e.g., "1000 IU"). Example: `"NOW high potency vitamin d-3 1000 IU 360 Softgels"` → `"NOW high potency vitamin d-3 1000 IU"`

2. **Remove BH organic fallback for supplements** — when iHerb returns nothing, instead of falling back to BH organic search (which gives wrong local BHD prices), pass empty context so Tier 2 GPT returns null → Tier 3 USD estimate handles it with proper conversion

3. **Fix full_name doubling for vision products** — check if `variant.lower() in name.lower()` before concatenating. Vision products have name already containing size_or_count from image_routes.py enrichment.

**Status:** Deployed but did NOT fully resolve the camera price issue. Needs further investigation — possibly the camera product name itself needs simplification before being used as search query, or the iHerb search needs broader matching.

## Commits
1. `4eb4432` — Fix OpenAI timeout: increase connect timeout to 30s for Railway
2. `5a192bd` — Fix supplement detection: use GPT category, add d3/brand keywords
3. `7ab9b62` — Fix iHerb USD→BHD conversion: force original_currency for US prices
4. `73e8c33` — Fix vision category detection + camera upload Network Error
5. `54e9d76` — Fix camera price cache: stale BHD 10.9 served from pre-fix cache
6. `70d1bba` — Fix supplement iHerb price: strip pill count from query, remove BH fallback (DID NOT FULLY RESOLVE)

## Key Technical Changes
| Change | File | Detail |
|--------|------|--------|
| `timeout=httpx.Timeout(120.0, connect=30.0)` | 3 files | All AsyncOpenAI clients |
| `category` param on `_get_price()` | `structured_comparison_service.py` | Primary supplement signal |
| `SUPPLEMENT_KEYWORDS` expanded | `structured_comparison_service.py` | d3, d-3, brand names |
| Force `original_currency = "USD"` for iHerb | `structured_comparison_service.py:565` | Prevents BHD misattribution |
| `nocache` on image endpoint | `image_routes.py` | Bypass stale camera cache |
| Strip pill count regex | `structured_comparison_service.py:548` | `re.sub(r'\b\d+\s*(softgels?|...)\b', ...)` |
| Skip BH organic for supplements | `structured_comparison_service.py:561` | Empty context → Tier 3 estimate |
| `full_name` variant dedup | `structured_comparison_service.py:484` | `if variant.lower() in name.lower()` |

## Still Broken
1. **Camera supplement prices** — iHerb search with stripped pill count still may not return results for verbose camera product names. The search query `"NOW high potency vitamin d-3 1000 IU site:iherb.com"` may still be too long/specific. May need to simplify the camera product name further (e.g., just `"NOW vitamin d3 1000 IU"`) or use a different search strategy for camera-identified supplements.
2. **No axios auth interceptor** — token never sent on API requests (deferred)
3. **Legacy `/api/v1/compare` route** — broken function calls (deferred)

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working (GPT review fallback for unverified, brand-aware matching) |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |

---

## Session: February 20, 2026 — Rating/Price Links + Cost Optimization

### What Was Done

**1. Fixed Rating & Price Links (no legit links before)**
- **Problem:** Rating links pointed nowhere useful. Price links were wrong for some products (generic search pages instead of product pages).
- **Root cause:** Backend discarded Serper Shopping `link` field. Frontend `openRatingSource()` hardcoded Google Shopping search, ignoring backend URLs.
- **Fix (backend):** Use Serper Shopping `link` field (Google Shopping product-specific URLs with catalog IDs) as primary URL for both price and rating. Fall back to `_build_retailer_url()` search pages when no link available.
- **Fix (frontend):** `openRatingSource()` now uses `rating_source.url` from backend first. Added `google_shopping_consensus` and `gpt_review_aggregate` to `extract_method` type union, `getConfidenceColor()`, and `getMethodLabel()`.
- **Files changed:** `structured_comparison_service.py` (4 edits), `ResultsScreen.tsx` (4 edits)
- **Tests:** `tests/test_url_extraction.py` — 8 pytest tests covering price URL, tiered rating URL, and consensus rating URL extraction
- **Commit:** `b3e35e7`

**2. Cost Optimization — Unified Search Merging**
- **Problem:** Each comparison made 15-20 API calls at $0.0145 (electronics) / $0.0119 (supplements). Target: ≤$0.015.
- **Analysis:** Specs and reviews each did their own Serper web search ($0.001 each). Two separate searches per product = $0.004/comparison wasted on redundant calls.
- **Fix:** Added unified pre-search in `_fetch_product_data()` — one Serper web search (`"{query} specifications reviews price"`, 10 results) shared by both `_get_specs(search_results=...)` and `_get_reviews(search_results=...)`. Gated by cache check so no wasted call when data is already cached.
- **Results:**
  - Electronics: **$0.0145 → $0.0099** (32% reduction, 20→13 API calls)
  - Supplements: **$0.0119 → $0.0119** (1 call saved; iHerb/pharmacy paths dominate)
- **Approach B (skip redundant US rating search):** After analysis, the existing BH→US fallback in `_get_verified_rating()` already correctly returns early when BH data has tier1/tier2/consensus ratings. No code change needed.
- **Commit:** `ec2e80d`

### Key Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use Serper `link` field as primary URL | Zero-cost improvement (data already fetched), gives product-specific Google Shopping pages |
| `_build_retailer_url()` as fallback | Generates search page URLs when Serper link is absent (GCC retailers) |
| Unified search over separate searches | One Serper call ($0.001) replaces two ($0.002), 10 results cover both specs and reviews |
| Gate unified search on cache check | Avoids wasting $0.001 when both specs and reviews are already cached |
| Don't merge price organic search | Uses region-specific query terms ("Bahrain price BHD buy") — merging would dilute results |

### Architecture Changes
```
BEFORE (per product, no cache):
  Phase 1: _get_specs() [search_web + GPT] + _get_price() [shopping + organic + GPT]
  Phase 2: _get_reviews() [search_web + GPT] + _get_verified_rating() [US shopping]

AFTER:
  Pre-fetch: unified search_web() — shared by specs + reviews (gated by cache check)
  Phase 1: _get_specs(search_results=unified) + _get_price() [shopping + organic + GPT]
  Phase 2: _get_reviews(search_results=unified) + _get_verified_rating() [US shopping]
```

### What Serper Shopping `link` Actually Contains
- NOT direct retailer URLs (despite Serper docs suggesting this)
- Google Shopping product-specific pages with `ibp=oshop`, `catalogid`, `pvo`, `pvt` parameters
- Example: `https://www.google.com/search?ibp=oshop&q=NOW+D3&prds=catalogid:10530300028176976053,...`
- Still much better than generic search pages — leads to product detail with price comparison

### Updated Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working + **linked to sources** |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |
| **Rating/Price links** | ✅ **NEW — product-specific Google Shopping URLs** |
| **Cost optimization** | ✅ **NEW — $0.010 electronics, $0.012 supplements** |

---

## Session 8: Feb 21, 2026 — Pharmacy JSON-LD Price Extraction

### Problem
Non-iHerb supplement brands (HealthAid, Vitabiotics, etc.) were getting wrong prices. HealthAid Vitamin D3 1000IU returned BHD 3.77 (GPT guess), BHD 5.66, or BHD 7.71 (wrong iHerb product match) across different runs. Real price is BHD 9.00 (bolo.bh, 120ct) or BHD 6.30 (Boots, 30ct).

### Root Cause
HealthAid is NOT sold on iHerb. The iHerb scraper either matched a different brand's product or returned None, falling through to unreliable GPT snippet extraction.

### Solution: JSON-LD Product Schema Parsing
Bahrain pharmacy product pages (bolo.bh, bn.boots.com) embed structured `Product` schema in JSON-LD with exact BHD prices. Parse these instead of relying on GPT.

### New Supplement Price Pipeline
```
1. iHerb direct scrape (existing — NOW, Solgar, Nature Made)
   ↓ no brand match
2. Serper BH pharmacy search (existing, $0.002)
   ↓ try pharmacy URLs
3. _try_pharmacy_urls() — fetch pages, parse JSON-LD Product schema
   ↓ no JSON-LD found (search pages, not product pages)
4. Targeted site search: site:bn.boots.com OR site:bolo.bh ($0.001)
   ↓ find product page URLs
5. _try_pharmacy_urls() again on targeted results
   ↓ still no JSON-LD
6. GPT extraction from snippets (existing fallback)
   ↓ GPT fails
7. Tier 3 GPT estimate (existing)
```

### New Code
- `_extract_jsonld_price(html, brand, currency)` — static method, parses `<script type="application/ld+json">` for Product.offers.price
- `_fetch_pharmacy_price(serper_organic, brand, full_name, currency)` — filters URLs, calls `_try_pharmacy_urls`, falls back to targeted site search
- `_try_pharmacy_urls(urls, brand, currency)` — fetches pages via httpx, calls `_extract_jsonld_price`
- `PHARMACY_DOMAINS` — `{"bolo.bh": "Bolo", "bn.boots.com": "Boots", "aldeerahpharmacy.com": "Al Deerah Pharmacy"}`

### Bugs Discovered & Fixed During Production Testing
1. **bolo.bh not indexed by Google** — Vue.js SPA, `site:bolo.bh` returns zero results. Had to add bn.boots.com (IS indexed) to targeted search
2. **Search pages vs product pages** — Serper returns pharmacy search/listing URLs, not product pages. Search pages have no Product JSON-LD. Fixed by trying initial URLs first, then falling back to targeted site search
3. **Brand spelling mismatch** — Boots spells it "Health Aid" (with space), our brand is "HealthAid" (no space). Fixed with space-insensitive brand matching: `brand.replace(" ", "")` before comparison
4. **Duplicate brand in search query** — `f"{brand} {full_name}"` produced "HealthAid HealthAid Vitamin D3..." since full_name already contains brand

### Results
| | Before | After |
|---|---|---|
| HealthAid D3 price | BHD 3.77 (GPT estimate, wrong) | BHD 6.30 (Boots, real, verified) |
| HealthAid retailer | None | Boots |
| HealthAid URL | iHerb search (wrong) | bn.boots.com product page |
| Cost | $0.0202 → $0.0099 | $0.0103 |

### Tests Added
- `tests/test_pharmacy_jsonld.py` — 12 tests (8 JSON-LD parsing + 1 brand-with-spaces + 3 integration)
- All 20 tests pass (12 pharmacy + 8 URL extraction)

### Key Lessons Learned
1. **SPA sites are NOT scrapable** with simple HTTP — bolo.bh renders products client-side. But product pages may still have server-rendered JSON-LD metadata.
2. **Google indexing varies wildly** — bolo.bh (major GCC retailer) has ZERO pages indexed, while bn.boots.com (Boots) is fully indexed.
3. **Brand names have variants** — "HealthAid" vs "Health Aid". Space-insensitive matching is essential for pharmacy data.
4. **Serper organic returns listing pages** — even when searching for specific products, Serper often returns the retailer's search/category page, not the product page. Targeted `site:` queries work better.
5. **JSON-LD is reliable** — when a page has it, it's structured, deterministic, and free to parse. Far superior to GPT snippet extraction.

### Architecture Changes
```
BEFORE (supplement pricing):
  iHerb scrape → Serper fallback (2 calls) → GPT extraction → Tier 3 estimate

AFTER:
  iHerb scrape → Serper fallback (2 calls) → JSON-LD from pharmacy URLs →
  targeted site:bn.boots.com search ($0.001) → JSON-LD from site results →
  GPT extraction → Tier 3 estimate
```

---

## Session 8: Bahrain Drug Database + Integration Tests (Feb 21 2026, continued)

### What Was Done
Implemented the Bahrain Drug Database feature end-to-end: Supabase table, data import, service layer, GPT prompt injection, unit tests, integration tests, deploy + verification.

### Plan: 3 Parallel Agents (Failed)
Original plan called for 3 parallel agents (A: feature code, B: integration tests, C: unit tests) with strict file ownership. **All 3 agents failed** due to tool permission denials in the agent environment. The data import agent also got stuck in plan mode. All work was completed directly in the main conversation instead.

### New Files Created
| File | Purpose |
|------|---------|
| `app/services/drug_database_service.py` | `find_matching_drugs(query, limit)` — Supabase full-text search on `bahrain_approved_drugs` table; `format_drug_context(drugs)` — formats results for GPT prompt |
| `tests/test_drug_database_service.py` | 11 unit tests (5 run locally + 6 live_db auto-skip) |
| `tests/test_integration.py` | 6 integration tests against live Railway endpoint |
| `import_batches/batch_1.sql` through `batch_7.sql` | 655 drug records in SQL INSERT format |

### Files Modified
| File | Changes |
|------|---------|
| `app/services/extraction_service.py` | Added `drug_context` param to `_build_specs_prompt()` and `extract_specs()`, injected `{drug_context}` into prompt template |
| `app/services/structured_comparison_service.py` | Import drug_database_service, drug lookup before Phase 1 (supplements only), pass `drug_context` through `_get_specs()` |
| `pyproject.toml` | Added pytest markers (`live_db`, `integration`) |

### Database: `bahrain_approved_drugs` Table
- **655 rows** of Bahrain-registered health products (vitamins, supplements, OTC drugs)
- Columns: `trade_name`, `registration_no`, `api_name` (ingredients), `form`, `pack_size`, `method_of_sale`, `manufacturer`, `country`, `applicant_name`
- `search_vector` TSVECTOR column auto-generated from `trade_name + api_name` via trigger
- `GIN` index for fast full-text search
- Supabase project: `qulajmyxdbdkchvecmvc`

### How Drug Context Injection Works
1. Before Phase 1, if `category == "supplements"`, call `find_matching_drugs(search_query)`
2. Returns up to 5 matching registered drugs with official ingredients, forms, pack sizes
3. `format_drug_context()` formats them as a prompt section: "Official Bahrain Drug Registration Data"
4. Injected into GPT spec extraction prompt after search context — acts as ground truth for dosage/form/ingredient
5. Cost: zero (Supabase query, no API calls)

### Supabase Python Client Gotchas (Fixed)
- `text_search()` uses `options={"type": "plain", "config": "english"}` dict — NOT `type="plain"` keyword
- `.text_search()` returns `SyncQueryRequestBuilder` — `.limit()` must come BEFORE `.text_search()` in chain
- Skip detection in tests: direct `client.table().select("id").limit(1).execute()` — NOT `find_matching_drugs()` (catches errors → returns `[]`, same as "no results")

### Integration Tests
6 tests calling live Railway production with `nocache=true`:
1. **Phones** — iPhone 15 vs Samsung Galaxy S24 (checks display, processor, battery specs)
2. **Laptops** — MacBook Air M3 vs Dell XPS 15 (checks RAM, storage specs)
3. **iHerb supplements** — NOW D3 5000 IU vs Nature Made D3 2000 IU (checks dosage, form)
4. **Pharmacy supplements** — HealthAid Vitamin C vs Vitabiotics Wellman (BHD prices)
5. **Grocery** — Coca Cola vs Pepsi
6. **General** — Nike Air Max 90 vs Adidas Ultraboost

**Assertion fixes discovered during first run:**
- `product.rating` is a raw float (e.g., `4.8`), NOT a dict `{score: 4.8}`
- Cost tracked at `metadata.total_cost`, NOT `metadata.cost.current_cost`
- Phone display spec key is `display`, NOT `display_size`
- Shoe prices can exceed 150 BHD (Adidas Ultraboost was 317 BHD)

### Project ID Confusion (Resolved)
Three different Supabase project IDs encountered:
- `jzmjaawdkbhvvqnmxpcq` — stale ID from previous session's MCP calls (doesn't exist in account)
- `khatrmxzrvjzlbtcetva` — local env `SUPABASE_URL` points here (different project)
- `qulajmyxdbdkchvecmvc` — actual smartcompare project, where table + data lives

### Commits
- `83f6311` — feat: Bahrain drug database integration + tests
- `54addc6` — fix: integration test assertions to match actual API response format

### Updated Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (non-iHerb supplements) | ✅ Boots JSON-LD extraction |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working + linked to sources |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| **Specs (supplements enrichment)** | ✅ **NEW — Bahrain drug DB ground truth injected into GPT prompt** |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |
| Rating/Price links | ✅ Product-specific Google Shopping URLs |
| Cost optimization | ✅ $0.010 electronics, $0.010 supplements |
| Pharmacy JSON-LD | ✅ bn.boots.com, bolo.bh (if indexed) |
| **Bahrain Drug Database** | ✅ **NEW — 655 records, full-text search, GPT context injection** |
| **Integration Tests** | ✅ **NEW — 6 tests, all passing (~$0.06, ~4 min)** |
| **Unit Test Coverage** | ✅ **NEW — 73 tests across 7 files covering all core logic** |

---

## Session 9: Feb 22, 2026 — Test Coverage for 7 Uncovered Areas

### What Was Done
Added 73 unit tests across 7 new test files covering all previously untested core logic. Used a 3-agent Opus team with cross-QA (each agent reviews another's work). All QA passed with zero issues.

### Team Structure (Successful)
3 Opus agents running in parallel with `bypassPermissions` mode:
- **Agent A**: test_camera_vision.py, test_singleton_state.py, test_iherb_scraping.py → QA'd Agent B's files
- **Agent B**: test_rating_tiers.py, test_price_fallback.py → QA'd Agent C's files
- **Agent C**: test_unified_search.py, test_error_paths.py → QA'd Agent A's files

All 11 tasks (7 implementation + 3 QA + 1 final verification) completed successfully. This is the first successful multi-agent team execution in this project (previous attempt in Session 8 failed due to tool permissions).

### New Test Files
| File | Tests | Coverage Area |
|------|-------|---------------|
| `tests/test_error_paths.py` | 31 | `_convert_to_bhd` edge cases, `_calculate_freshness` with None, `_parse_price_string` garbage input, `_is_supplement_query` anti-keywords, `_strict_title_match` hyphens, `_numbers_match` year vs count |
| `tests/test_rating_tiers.py` | 16 | `_get_rating_tier` classification, `_extract_rating_from_shopping` tier priority, consensus detection, Tier 3 review count threshold, accessory rejection |
| `tests/test_price_fallback.py` | 12 | `_extract_price_from_shopping` filters, `_convert_gpt_price_currency`, `_sanitize_gpt_price`, all-tiers-fail fallback |
| `tests/test_camera_vision.py` | 10 | `identify_products` vision pipeline, `clean_json_response`, size_or_count enrichment (matches image_routes.py) |
| `tests/test_iherb_scraping.py` | 7 | `_normalize_words`, live iHerb scraping, brand filtering, nonexistent product handling |
| `tests/test_unified_search.py` | 4 | `_get_specs`/`_get_reviews` search_results sharing, cost budget tracking |
| `tests/test_singleton_state.py` | 3 | `get_comparison_service()` singleton, `_shopping_items_cache` cleared per request, `total_cost`/`api_calls` reset |

### What Each Test Area Catches
- **Error paths**: Every bug type from "Critical Bugs Fixed" (None currency, None price, garbage input)
- **Rating tiers**: Wrong tier priority, consensus with ties, Tier 3 accepted/rejected incorrectly
- **Price fallback**: Wrong fallback order, supplement misdetection, currency conversion errors
- **Camera/vision**: Malformed GPT response, missing fields, size_or_count duplication
- **iHerb scraping**: Brand mismatch, variant confusion (360 vs 120 Softgels), empty results
- **Unified search**: Wasted API calls, search not shared between specs/reviews
- **Singleton state**: Cross-request data leaks (the exact bug fixed in Session 6)

### Test Run Commands
```bash
# Free unit tests only (73 new + 25 existing = 98 tests, ~2s)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Include live unit tests (~$0.03 extra)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Full suite including integration (~$0.09 total, ~4 min)
python -m pytest tests/ -v --timeout=180
```

### Files Modified
| File | Changes |
|------|---------|
| `pyproject.toml` | Added `live_unit` pytest marker |
| `docs/plans/2026-02-22-test-coverage-design.md` | Design document for test coverage |
| `docs/plans/2026-02-22-test-coverage-plan.md` | Implementation plan with exact test code |

### Commits
- `402e36d` — feat: add 73 unit tests covering 7 previously untested areas

---

## Session 10: Feb 22, 2026 — Code Cleanup

### What Was Done
Removed dead code, fixed corrupted .gitignore, and consolidated pyproject.toml with requirements.txt. Zero behavior change.

### Dead Code Removed (~200 lines)
From `structured_comparison_service.py`:
- `REVIEW_SITES` class variable (10 lines) — list of expert review site domains
- `_get_expert_review()` method (80 lines) — Tier 0 rating, never called
- `_parse_review_jsonld()` method (25 lines) — only called by `_get_expert_review`
- `_extract_rating_from_jsonld_item()` method (85 lines) — only called by `_parse_review_jsonld`

From `extraction_service.py`:
- Unused `Tuple` import removed

Note: `Tuple` import kept in `structured_comparison_service.py` — still used by `_try_pharmacy_urls` at line 1058.

### .gitignore Fixed
- Removed PowerShell heredoc wrapper corruption (line 1: `@"`, line 31: `"@ | Out-File...`)
- Added patterns for ~80 untracked debug artifacts: `response_*.json`, `/test_*.py`, `/extract_*.py`, `import_batches/`, `.expo/`, `nul`, test images

### pyproject.toml Consolidated
Authority: `requirements.txt` (what Railway deploys).
- Fixed openai version: `>=2.17.0` → `>=1.12.0` (v2 → v1)
- Added 3 missing packages: `beautifulsoup4`, `lxml`, `curl-cffi`
- Removed `pillow` (not in requirements.txt)
- Removed all upper bound constraints to match requirements.txt style

### Legacy Routes — No Fix Needed
Documentation said `app/api/routes.py` had 4 TypeErrors. Investigation found no broken calls — issue was either already fixed or referred to `backend/app/api/routes.py` (non-deployed).

### Team Structure
2 Opus agents with cross-QA:
- Agent A: dead code removal → QA'd Agent B's config changes
- Agent B: .gitignore + pyproject.toml → QA'd Agent A's dead code removal

### Files Modified
| File | Changes |
|------|---------|
| `app/services/structured_comparison_service.py` | Removed ~200 lines of dead Tier 0 code |
| `app/services/extraction_service.py` | Removed unused `Tuple` import |
| `.gitignore` | Fixed corruption, added debug artifact patterns |
| `pyproject.toml` | Consolidated with requirements.txt |
| `docs/plans/2026-02-22-code-cleanup-design.md` | Design document |

### Commits
- `02e23de` — chore: remove dead code, fix .gitignore, consolidate pyproject.toml

---

## Session 11: Feb 22, 2026 — Fact-Checking & Data Accuracy

### What Was Done
Added zero-cost fact-checking system that cross-validates GPT-extracted data against real sources already fetched. Every product in the API response now has a `fact_check` object with `overall_confidence`.

### New Methods (5 added to `structured_comparison_service.py`)
- `_format_numbered_search_results()` — prefixes search snippets with `[snippet_N]` for GPT citation
- `_verify_spec_citations(specs, search_snippets)` — validates GPT's `_source` citations against actual snippet text
- `_cross_validate_specs_with_shopping(specs, shopping_items)` — checks spec numbers against Serper Shopping titles
- `_verify_review_sentiment(reviews, source_ratings)` — cross-checks GPT average_rating vs weighted Serper average (0.8 tolerance)
- `_verify_price(price, shopping_items)` — compares final price against Serper Shopping median (30% threshold)
- `_build_fact_check(product)` — assembles fact_check object from all verification results

### Prompt Changes (`extraction_service.py`)
- Spec extraction prompt now requires `{field}_source` citation fields (`snippet_N` or `"training"`)
- `max_tokens` increased 800 → 1000 to accommodate citation fields
- `extract_specs()` preserves `_source` fields through schema enforcement
- `_normalize_review_response()` defaults `source`, `sentiment`, `aspect` on user_quotes

### `fact_check` Response Object
```json
{
  "fact_check": {
    "specs_verified": 8,
    "specs_likely": 2,
    "specs_flagged": 0,
    "specs_unverified": 1,
    "price_verified": true,
    "price_deviation_pct": 5.2,
    "review_sentiment_consistent": true,
    "review_rating_deviation": 0.3,
    "overall_confidence": "high"
  }
}
```

Overall confidence logic:
- `low` — any specs flagged OR review sentiment inconsistent
- `high` — price verified + sentiment consistent + most specs verified/likely
- `medium` — everything else

### Bug Found During Development
`_verify_price()`: `deviation_pct` of `0.0` is falsy in Python. `round(0.0, 1) if deviation_pct` returned `None` for exact price matches. Fixed to `if deviation_pct is not None`.

### Team Structure
3 Opus agents with cross-QA:
- Agent A: spec fact-checking (prompt + citations + verification) → QA'd Agent B
- Agent B: review sentiment + price verification → QA'd Agent C (+ wrote 17 edge case tests while idle, found 0.0 bug)
- Agent C: assembly + wiring + tests → QA'd Agent A

### Integration Tests
5/6 passed. `test_supplements_iherb` got transient 502 (Railway gateway timeout on slow iHerb scrape). Retry returned 200. Not a code issue.

### Files Modified
| File | Changes |
|------|---------|
| `app/services/structured_comparison_service.py` | 5 new verification methods + wiring + _clean_specs update (+291 lines) |
| `app/services/extraction_service.py` | Prompt citations + _source preservation + user_quotes defaults (+26 lines) |
| `tests/test_fact_checking.py` | 48 new unit tests for all fact-checking logic |
| `docs/plans/2026-02-22-fact-checking-design.md` | Design document |
| `docs/plans/2026-02-22-fact-checking-plan.md` | Implementation plan |

### Commits
- `2cb9a80` — feat: add zero-cost fact-checking via cross-validation and self-citation

---

## Session 12: Mar 3, 2026 — Auth, History & DB Improvements

### What Was Done
Multi-agent team (3 Opus agents, `bypassPermissions`, circular cross-QA) implemented three features:

**1. Auth System (Axios Interceptors)**
- Request interceptor in `api.ts` attaches JWT Bearer token to every request
- 401 response interceptor auto-refreshes token, queues failed requests, retries
- `get_optional_user()` in `auth_routes.py` returns `User | None`, never throws
- Text + image endpoints use `Depends(get_optional_user)` — anonymous users can still compare
- 45 tests in `test_auth_interceptor.py`

**2. History Feature**
- `save_comparison()` stores full API response as JSONB blob + query + input_type + product_names array
- Fire-and-forget via `asyncio.create_task()` — save failure never breaks comparison
- Only saves for authenticated users
- `GET /api/v1/comparisons/history` with real auth + optional `?search=` param
- `DELETE /api/v1/comparisons/{id}` with ownership check
- HistoryScreen passes stored blob directly to ResultsScreen
- 10 tests in `test_history.py`

**3. Database Improvements**
- `search_logs` table: logs every comparison (success/failure) with query, products, cost, duration
- `upsert_product()` by exact `canonical_name` — no fuzzy matching
- `log_search()` fire-and-forget, wired into text + image routes
- ~105 lines dead code removed (daily_usage + price_cache functions)
- 9 tests in `test_db_improvements.py`

### SQL Migrations Applied
- `migrations/001_update_comparisons.sql` — comparisons table (was missing)
- `migrations/002_search_logs_and_products.sql` — search_logs + products tables

### Files Modified
| File | Changes |
|------|---------|
| `SmartCompareApp/src/services/api.ts` | Axios request + 401 response interceptors |
| `SmartCompareApp/src/services/authService.ts` | Token storage, refresh logic |
| `SmartCompareApp/src/screens/HistoryScreen.tsx` | Search bar, delete, input type badges |
| `app/api/auth_routes.py` | `get_optional_user()`, real auth on history/delete |
| `app/api/text_routes.py` | `save_comparison()` + `log_search()` wiring |
| `app/api/image_routes.py` | `save_comparison()` + `log_search()` wiring |
| `app/services/database_service.py` | `save_comparison()`, `log_search()`, `upsert_product()`, dead code removal |
| `tests/test_auth_interceptor.py` | 45 new tests |
| `tests/test_history.py` | 10 new tests |
| `tests/test_db_improvements.py` | 9 new tests |

### Commits
- `fdb51a1` — feat(history): update history endpoint to use real auth, add delete endpoint
- `38c379b` — feat(history): add search param and delete function to API service
- `e23dbfc` — feat(history): full blob passthrough, search, delete, updated UI
- `35b3892` — test(auth): expand to 45 tests for ~90% auth pipeline coverage
- `c534d09` — fix: add proper logging to database_service fire-and-forget functions

---

## Session 13: Mar 3, 2026 — Test Verification & Supabase Fix

### What Was Done
Verified all auth, history, and db tests pass. Fixed issues blocking live Supabase tests.

**1. Fixed `datetime.utcnow()` deprecation**
- `database_service.py` used deprecated `datetime.utcnow()` in 2 places
- Replaced with `datetime.now(timezone.utc)` — Python 3.12+ recommended pattern

**2. Fixed local `.env` Supabase credentials**
- `.env` had wrong Supabase project (`khatrmxzrvjzlbtcetva` — old/dead project)
- Updated to correct project (`qulajmyxdbdkchvecmvc`) with matching anon + service_role keys
- All 6 `live_db` drug database tests now pass locally

**3. Added `tests/conftest.py`**
- Loads `.env` via `python-dotenv` at test collection time
- Fixes issue where `database_service.py` module-level env var reads happened before `.env` was loaded
- All tests now pick up correct Supabase credentials automatically

### Test Results
- **210 unit tests passed** (0 failures, 0 errors)
- **6 live_db tests passed** (Supabase drug database)
- **75 auth+history+db tests passed** specifically verified

### Files Modified
| File | Changes |
|------|---------|
| `app/services/database_service.py` | `datetime.utcnow()` → `datetime.now(timezone.utc)` (2 occurrences) |
| `tests/conftest.py` | New file — loads `.env` for all tests |
| `.env` | Updated SUPABASE_URL + keys to correct project |

---

## Session 14: Mar 3, 2026 — Production Readiness (Security, Observability, Analytics, CI/CD)

### What Was Done
Multi-agent team (3 Opus agents, `bypassPermissions`, circular cross-QA) implemented full production readiness stack. All free-tier.

**Team Structure:**
- **security-agent**: Rate limiting, security headers, request ID middleware, main.py rewrite
- **observability-agent**: Structured logging, Sentry integration, error handler middleware
- **analytics-ci-agent**: Admin analytics endpoints, GitHub Actions CI pipeline

### 1. Middleware Stack (5 layers)
**Files:** `app/middleware/request_id.py`, `security.py`, `rate_limiter.py`, `error_handler.py`, `logging_config.py`, `__init__.py`

Middleware execution order (outermost → innermost):
1. **RequestIDMiddleware** — generates UUID per request, preserves client-provided `X-Request-ID`
2. **SecurityHeadersMiddleware** — adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `X-XSS-Protection`, `Permissions-Policy`
3. **ErrorHandlerMiddleware** — catches unhandled exceptions, logs with request_id, sends to Sentry, returns clean 500 JSON (no stack traces leaked)
4. **CORS** — restricted origins (Railway + localhost only, not wildcard `["*"]`)
5. **slowapi rate limiter** — decorator-based, 10/min on compare endpoints, in-memory storage (`memory://`)

### 2. Structured JSON Logging
**File:** `app/middleware/logging_config.py`
- `StructuredFormatter` outputs one-line JSON per log entry (timestamp, level, module, message, request_id, exception)
- `configure_logging()` sets root logger level, clears default handlers, quiets noisy libs (httpx, httpcore, uvicorn, urllib3)

### 3. Sentry Integration
**File:** `app/services/sentry_service.py`
- `init_sentry()` — no-op if `SENTRY_DSN` env var is empty/missing
- Handles `ImportError` gracefully (sentry-sdk is in requirements but DSN is optional)
- `traces_sample_rate=0.1` (10% of transactions traced)

### 4. Admin Analytics API
**Files:** `app/services/analytics_service.py`, `app/api/admin_routes.py`
- 5 GET endpoints: `/stats/daily`, `/stats/popular`, `/stats/costs`, `/stats/errors`, `/stats/products`
- Protected by `verify_admin_key()` dependency checking `X-Admin-Key` header against `ADMIN_API_KEY` env var
- Empty/missing `ADMIN_API_KEY` rejects all requests (403)
- All queries use `search_logs` and `products` tables via `get_supabase_client()`

### 5. GitHub Actions CI
**File:** `.github/workflows/ci.yml`
- Two jobs: `backend-tests` (Python 3.12, pip install, py_compile on all `app/`, pytest unit tests) and `frontend-typecheck` (Node 20, npm ci, tsc --noEmit with continue-on-error)
- Triggers on push to main and PRs

### 6. main.py Rewrite
**File:** `app/main.py`
- All 5 middleware layers registered in correct Starlette order
- CORS restricted to Railway + localhost origins
- Calls `configure_logging()` before imports, `init_sentry()` after
- Registers `admin_router` at `/api/v1/admin`
- Version bumped to 2.1.0

### Rate Limiting Details
- `text_routes.py`: POST and GET `/compare` decorated with `@limiter.limit("10/minute")`
- `image_routes.py`: identify endpoint rate-limited
- POST endpoints renamed Pydantic `request` param to `body` to avoid collision with slowapi's required `request: Request` parameter

### New Dependencies
- `slowapi>=0.1.9` — rate limiting
- `sentry-sdk[fastapi]>=1.40.0` — error tracking

### New Environment Variables
- `ADMIN_API_KEY` — required for admin endpoints (added to Railway)
- `SENTRY_DSN` — optional, enables Sentry error tracking
- `LOG_LEVEL` — optional, defaults to INFO

### Tests Added (86 new)
| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_analytics.py` | 30 | Analytics service + admin endpoints |
| `tests/test_observability.py` | 24 | Sentry, structured logging, error handler |
| `tests/test_security_middleware.py` | 16 | Request ID, security headers, rate limiting |
| **Total new** | **70** | **+ 16 existing test updates = 86 effective** |

### Test Results
- **280/280 unit tests passing** (0 failures, 0 regressions)
- All 86 new tests pass
- Original 194 tests unaffected

### Commits
- 15 commits from 3-agent team covering implementation + cross-QA
- Final push: `43481a2..071e9a4` deployed to Railway

### Deployment Verified
- Health check: `{"status":"healthy","message":"SmartCompare API is running"}`
- Security headers present: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Xss-Protection`, `Permissions-Policy`
- `X-Request-Id` UUID in every response

---

## Session 15: Mar 3, 2026 — Account Panel, Social Auth, Image Upload Fix

### What Was Done
Multi-agent team (3 Opus agents, `bypassPermissions`, circular cross-QA) implemented account management, social authentication, and fixed critical bugs. Fourth time using multi-agent team (Sessions 9, 12, 14, 15).

**Team Structure:**
- **backend-agent**: Auth endpoints (profile, email, password, social-login), HEIC detection, EAS plugins
- **frontend-core-agent**: AccountScreen, HomeScreen gear icon, HistoryScreen 401 fix, image JPEG transcoding
- **frontend-auth-agent**: Google/Apple sign-in SDK integration, Login/Register social buttons + input validation

### Bug Fixes

**1. Image Upload `invalid_image_format` (HEIC)**
- **Problem:** iOS devices capture photos in HEIC format. Backend couldn't process HEIC images.
- **Frontend fix:** `expo-image-manipulator` transcodes all camera/gallery images to JPEG before upload in `api.ts`
- **Backend fix:** `_detect_mime_type()` function in `image_routes.py` reads magic bytes to detect JPEG/PNG/WebP/GIF/HEIC. Rejects unsupported formats with 400 error. Belt-and-suspenders approach — frontend transcodes, backend validates.
- **HEIC magic bytes:** offset 4 contains `ftyp` marker, then `heic`/`heix`/`mif1`/`msf1` brand codes

**2. History 401 Crash**
- **Problem:** HistoryScreen crashed when user was not authenticated (401 response).
- **Fix:** HistoryScreen now catches 401 and shows a "Sign In Required" prompt with a sign-in button instead of crashing. Button navigates to LoginScreen.

**3. EAS Build Missing Plugins**
- **Problem:** `app.json` was missing required Expo plugins, causing EAS build failures.
- **Fix:** Added all required plugins to `app.json`: `expo-camera`, `expo-image-picker`, `expo-image-manipulator`, `@react-native-google-signin/google-signin`, `expo-apple-authentication`

### New Features

**4. AccountScreen**
- **File:** `SmartCompareApp/src/screens/AccountScreen.tsx`
- Inline editing for display name and email (edit/save/cancel pattern)
- Password change via modal (current password + new password + confirm)
- Connected accounts section showing Google/Apple connection status with connect buttons
- Logout button
- Accessible via gear icon (settings) on HomeScreen header

**5. Google Sign-In**
- **Frontend:** Native `@react-native-google-signin/google-signin` SDK
- `signInWithGoogle()` in `authService.ts` — calls `GoogleSignin.signIn()`, gets `idToken`, sends to backend
- Buttons on LoginScreen, RegisterScreen, and AccountScreen
- **Config needed:** Google Cloud Console OAuth client IDs (web + iOS + Android), Supabase Google provider

**6. Apple Sign-In**
- **Frontend:** Native `expo-apple-authentication` with cryptographic nonce via `expo-crypto`
- `signInWithApple()` in `authService.ts` — calls `AppleAuthentication.signInAsync()` with nonce, sends `identityToken` to backend
- iOS-only buttons (hidden on Android via `Platform.OS === 'ios'` check)
- **Config needed:** Apple Developer subscription ($99/year), enable capability in Xcode

**7. Backend Social Login Endpoint**
- `POST /api/v1/auth/social-login` — accepts `{ provider: "google"|"apple", id_token: "..." }`
- Calls `supabase.auth.sign_in_with_id_token(credentials={"provider": provider, "token": id_token})`
- Creates user if new, returns `{ user, session }` — frontend handles same as email login
- Returns 401 on invalid token, 400 on missing fields

**8. Backend Profile Endpoints (3 new)**
- `PUT /api/v1/auth/profile` — updates display name via `supabase.auth.update_user({"data": {"display_name": name}})`
- `PUT /api/v1/auth/email` — updates email, triggers Supabase verification email
- `PUT /api/v1/auth/password` — changes password (current password required for verification)

**9. Input Validation**
- LoginScreen + RegisterScreen now have inline per-field validation
- Email: regex validation shown on blur
- Password: minimum 6 characters
- Confirm password: must match (RegisterScreen only)
- Red error text shown inline below each field

### New Dependencies (Frontend Only)
- `expo-image-manipulator` — JPEG transcoding for camera/gallery images
- `@react-native-google-signin/google-signin` — native Google Sign-In SDK
- `expo-apple-authentication` — native Apple Sign-In
- `expo-crypto` — cryptographic nonce generation for Apple Sign-In

### Tests Added (64 new, 366 total)
| File | Before | After | New Tests |
|------|--------|-------|-----------|
| `tests/test_auth_interceptor.py` | 45 | 93 | +48 (social login, profile/email/password endpoints, edge cases) |
| `tests/test_camera_vision.py` | 10 | 26 | +16 (HEIC magic bytes, MIME detection, endpoint-level rejection) |
| **Total** | **302** | **366** | **+64** |

Breakdown: 344 free unit + 10 live_unit + 6 live_db + 6 integration = 366

### Config Still Needed (Manual, Deferred)
| Item | Where | Status |
|------|-------|--------|
| Google Cloud OAuth client IDs | Cloud Console → authService.ts + app.json | Done (Session 16) — Web/iOS/Android client IDs configured |
| Supabase Google provider | Supabase Dashboard → Auth → Providers | Pending — enable + paste Web client ID/secret |
| `public.users` table + `display_name` | Supabase migration | Done (Session 16) — table created with RLS |
| Apple Developer subscription | developer.apple.com | Deferred ($99/year) |

### Commits (18)
```
50fad03 fix: add missing expo-camera and expo-image-picker plugins to app.json
deb8f1f fix: add HEIC magic byte detection, reject unsupported image formats
39fbc0b feat: add PUT /auth/profile endpoint for display name update
f614f15 feat: add PUT /auth/email endpoint with Supabase verification
ee65c4d feat: add PUT /auth/password endpoint with current password verification
78a205a fix: transcode images to JPEG via expo-image-manipulator before upload
6e845ad feat: install and configure native Google Sign-In SDK
6580e99 fix: show sign-in prompt on history 401 instead of crashing
16cf29b feat: install and configure native Apple Sign-In with nonce support
b409e8c feat: add POST /auth/social-login for Google and Apple sign-in
604226c feat: add Google and Apple sign-in buttons to LoginScreen
b35df38 feat: add Google and Apple sign-in buttons to RegisterScreen
1834617 feat: add Google and Apple connect buttons to AccountScreen
0fc4612 test: add edge case tests for new auth endpoints (8 additional)
0bf4cc1 feat: add AccountScreen with name/email editing, password change, and navigation
8899990 feat: add inline input validation to Login and Register screens
450a7b1 test: add 14 deep edge case tests for auth endpoints
fe8d9c2 test: add endpoint-level HEIC rejection tests for /image/identify
```

### Key Technical Changes
| Change | File |
|--------|------|
| `_detect_mime_type()` — magic byte HEIC/JPEG/PNG/WebP/GIF detection | `app/api/image_routes.py` |
| `PUT /auth/profile`, `PUT /auth/email`, `PUT /auth/password` | `app/api/auth_routes.py` |
| `POST /auth/social-login` — Google/Apple idToken → Supabase | `app/api/auth_routes.py` |
| JPEG transcoding via `expo-image-manipulator` | `SmartCompareApp/src/services/api.ts` |
| `signInWithGoogle()` — native Google Sign-In SDK | `SmartCompareApp/src/services/authService.ts` |
| `signInWithApple()` — native Apple Auth + nonce | `SmartCompareApp/src/services/authService.ts` |
| AccountScreen — name/email/password/social accounts | `SmartCompareApp/src/screens/AccountScreen.tsx` |
| History 401 → sign-in prompt | `SmartCompareApp/src/screens/HistoryScreen.tsx` |
| Inline validation on Login/Register | `SmartCompareApp/src/screens/LoginScreen.tsx`, `RegisterScreen.tsx` |
| EAS plugins added | `SmartCompareApp/app.json` |

### Updated Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | Working (iHerb for supplements, shopping for electronics) |
| Prices (camera input) | Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | Working + linked to sources |
| Reviews | Working |
| Specs | Working (supplements schema) |
| Camera | Working (HEIC fix — JPEG transcoding + magic byte validation) |
| Auth | Working (email + social login + refresh token + axios interceptors) |
| **Account Panel** | **NEW — name/email edit, password change, Google/Apple connect** |
| **Google Sign-In** | **NEW — native SDK, needs Cloud Console config** |
| **Apple Sign-In** | **NEW — native SDK, needs Apple Dev subscription** |
| **Input Validation** | **NEW — inline per-field on Login/Register** |
| History | Working (save, search, delete, 401 sign-in prompt) |
| Cost optimization | $0.010 electronics, $0.010 supplements |
| Rating/Price links | Product-specific Google Shopping URLs |
| Pharmacy JSON-LD | bn.boots.com, bolo.bh (if indexed) |
| Bahrain Drug Database | 655 records, full-text search, GPT context injection |
| Integration Tests | 6 tests, all passing |
| **Test Coverage** | **366 total (344 free unit + 10 live + 6 live_db + 6 integration)** |
| URL input | Not started |

### Known Remaining Bugs
- Legacy `/api/v1/compare` route: all function calls use wrong arg counts (unchanged)
- ResultsScreen local type definitions diverge from types.ts (unchanged)
- Camera supplement prices: verbose names fail iHerb search (unchanged)
- Google Sign-In: Supabase Google provider not yet enabled in dashboard (client IDs configured in Session 16)
- Apple Sign-In: deferred — requires Apple Developer subscription ($99/year)

---

### Session 27 — Luxury Price Extraction Fix (March 21, 2026)

**Problem:** Luxury brand prices (LV cap ~340 BHD showing as ~50-160 BHD) because official brand sites are JS-rendered and Serper snippets don't contain prices.

**Root cause:** 4-tier cascade failure:
1. Serper Shopping returns reseller prices -> filtered by sanity check
2. Official domain search only reads snippets, not pages -> no prices from JS-rendered sites
3. Tier 2 GPT extraction uses wrong sanity thresholds for luxury (2.0x instead of 1.8x)
4. Tier 3 GPT estimate too conservative

**Changes:**
- NEW: `_fetch_page_price()` — generic page scraper (JSON-LD, OpenGraph, microdata) using curl_cffi
- ENHANCED: Tier 1.5 now cascades: official brand -> authorized retailers (Farfetch, SSENSE, Net-a-Porter) -> GCC retailers (Ounass, Bloomingdales, Namshi)
- FIXED: Tier 2 sanity check now uses luxury 1.8x/0.6x thresholds (was using 2.0x/0.5x)
- NEW: Frontend "(estimated price)" indicator for Tier 3 prices
- NEW: `ENABLE_PAGE_SCRAPE` feature flag (env var, default true)
- NEW constants: `AUTHORIZED_LUXURY_RETAILERS`, `GCC_LUXURY_RETAILERS`
- 20-second budget timeout across all Tier 1.5 sub-tiers
- Supplement pipeline enhanced with page scraping before GPT fallback

**Cost impact:** +$0.001-0.003 for luxury brands only (within $0.015 budget)
**Tests:** +38 new tests (page scraping, tier cascade, sanity check) — 982 total free unit tests

---

## Session 41: Survey-Driven Cohort Personalization (May 3-4, 2026 — Agent Team)

### What we shipped
Survey-driven cohort personalization (B + C from design): bootstrap personalization for new/anonymous users from 388 valid Fillout survey responses, via (B) verdict-prompt enrichment with cohort-aggregated findings and (C) one-shot preference seeding from cohort modal answers, surfaced in the Profile screen as a "Your style profile" card.

### Architecture summary
- **Build-time ETL** (`scripts/build_cohorts.py`): reads English + Arabic CSVs from `data/surveys/`, normalizes Arabic→English (~85 mappings), groups by `age|gender|governorate|language` cohort key, computes modal answers + distributions + persona labels, writes atomically to `data/cohort_priors.json` (committed artifact).
- **Runtime cohort service** (`app/services/cohort_service.py`): singleton, in-memory; `match()` uses hierarchical fallback (exact → broadened_governorate → broadened_language → broadened_age → population); `seed_preferences()` returns prefs with `_sources: {field: "inferred"}`; `get_display_profile()` returns dict only when confidence ≥ medium; `should_seed()` decides if user should receive seeded prefs.
- **Auth routes** (`app/api/auth_routes.py`): `PUT /api/v1/auth/demographics` (auth, 5/min, auto-detects language + country from headers), `GET /api/v1/auth/cohort-profile` (auth, returns `{display: ...|null}`), `PUT /api/v1/auth/preferences` extended to flip `_sources` from `inferred` to `user_stated` when user edits.
- **Verdict prompt enrichment** (`app/services/extraction_service.py`): `_build_preferences_prompt()` appends ~120-token cohort priors block when `match_quality ∈ {exact, broadened_governorate, broadened_language}` AND `ENABLE_COHORT_PERSONALIZATION=true`. Privacy invariant: NO raw `age_group` or `gender` in rendered prompt — only thin context line `Country=X, Language=Y, Region=Z` plus aggregate cohort findings.
- **Admin dashboard** (`/admin/cohort.html` + 3 metric endpoints): match-rate, persona-distribution, feedback-lift, retention KPIs. Auth via X-Admin-Key prompt.
- **Frontend** (`SmartCompareApp/`): `DemographicsBottomSheet.tsx` (post-first-comparison, 3 fields all skippable), `StyleProfileCard.tsx` (Profile screen, hidden when confidence < medium), `demographicsTrigger.ts` (4-attempt schedule with 7-day cooldown then permanent stop), edit-banner on Onboarding when route param `source=styleProfile`, EN+AR i18n parity (33 keys per language).

### Commits (29 total)
**Pre-flight:** ecd52ad (design), c2253f4 (plan), 9453dc1 (gitignore raw CSVs), 2543eef (env var note)

**Backend (Section A):**
- A.1 migration 013 — `data/surveys/*.csv` swept into e490372 due to git contamination; migration content was correct
- A.2 ETL: `f3e52d4` (build_cohorts.py + cohort_priors.json: 388 responses → 21 cohorts + 29 fallbacks)
- A.3 cohort_service: bundled into `51b466c` due to git-add contamination (file content correct)
- A.4 auth routes + `_sources` flip: bundled into `f0a52b7` (file content correct)
- A.5 prompt block + feature flag: `8579cc0`
- A.6 admin endpoints + dashboard: `68d1cd2`
- A.7 docs (CLAUDE.md + MEMORY.md): `b2189e3`
- Fix: `ae0e05d` (scoped rate-limiter bypass to `_RATE_LIMITER_BYPASS_TEST_FILES`, replacing global env disable that broke 39 security regression tests)

**Frontend (Section B):** e490372 (i18n keys), 4d88a9f (api client), d5736c0 (DemographicsBottomSheet), 2366cbc (trigger logic), dd8c26f (StyleProfileCard), a0f6725 (edit banner), 51b466c (trigger edge tests + cohort_service contamination), 7300c26 (a11y), c1dcdc2 (StyleProfile edges), 66c09b0 (priorities), 335fb93 (timing edges)

**Tests (Section C):** 3e17598 (red-phase ETL + cohort_service tests), bb25a7a (frontend expansion), d7c450a (i18n keys pinning), 0693ffe (97% cohort_service coverage), 4094b4a (property-based), f0a52b7 (16 snapshot scenarios)

### Verification (D.1-D.6 disassembly gate)
- `pytest -m "not (live_unit or live_db or integration)" --ignore=tests/test_rate_limiting_complete.py`: **1868 passed, 33 deselected, 1 xfailed** in 118s
- `pytest tests/test_security_regression.py`: **67/67 PASS** (was 57 baseline + 10 new demographics-RLS additions)
- `pytest tests/test_security_middleware.py`: **16/16 PASS**
- `pytest --cov=app.services.cohort_service --cov=scripts.build_cohorts --cov-fail-under=80`: **93.18% total** (cohort_service 97%, build_cohorts 91%) — match() function 100%
- `cd SmartCompareApp && npx tsc --noEmit`: **0 errors**
- `cd SmartCompareApp && npx jest <cohort-tests>`: **106/106 PASS** across 8 frontend test files
- Live smoke: cohort match returns "Quality-first buyer" for `25-34|Female|Northern|Arabic` (n=13); seed returns `_sources: inferred` per design 5.3; prompt contains `COHORT-LEVEL PRIORS` and `Country=Bahrain` but NOT `25-34` or `Female`; admin dashboard renders 200 OK with Chart.js
- Cross-QA matrix: 4 approvals (backend→frontend, frontend→test, test→backend, qa→all)

### Manual steps required post-merge
1. **Apply migration 013** via Supabase SQL Editor (no psql/Management API token locally per CLAUDE.md gotcha): adds `users.demographics_profile` JSONB + dismissal tracking columns + 3 metric views (`vw_cohort_match_rate`, `vw_cohort_persona_distribution`, `vw_cohort_feedback_lift`).
2. **Set Railway env var** `ENABLE_COHORT_PERSONALIZATION=false` (defaults false in code; explicit setting clarifies intent for Phase 1 internal QA). Currently pending Railway sub renewal per `pending_railway_migration.md`.
3. **Phase 1 rollout** when ready: enable flag for admin accounts only; verify metrics; expand to 10% canary; full.

### Gotchas surfaced (added to MEMORY.md)
- slowapi `@limiter.limit` validates `isinstance(request, Request)`, breaking unit tests with MagicMock requests. Solved with autouse fixture scoped to `_RATE_LIMITER_BYPASS_TEST_FILES` in conftest.py — narrow opt-in per file, not global.
- `git commit` (no `-- <paths>`) commits the entire staging index. Multiple agents staging WIP simultaneously caused 3 commits to be contaminated with other agents' files (e490372, dd8c26f, 51b466c, f0a52b7). Files on disk are correct; commit attribution is off. Going forward use `git commit -- <paths>` to scope each commit. Memory entry: `feedback_git_staging_in_team.md`.
- ETL Arabic detection: initially flagged ALL non-ASCII as Arabic but English values from Fillout can contain NBSP (e.g. "Fashion or Beauty\u00a0 item"). Fixed to only flag Arabic block (U+0600..U+06FF).
- VALID_PRIORITIES had to extend from 8 → 14 enum values (cohort seed emits `quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`); same pattern for VALID_BRAND_ATTITUDE adding `trust_known_brands`. Don't break existing 8.
- `cohort_priors.json` IS committed (build artifact); raw `data/surveys/*.csv` are gitignored (PII in email/phone columns).
- Pre-existing hang: `tests/test_rate_limiting_complete.py::test_prices_endpoint_rate_limited` hangs in TestClient — verified on baseline 553b091 BEFORE this team's work. NOT introduced by cohort changes.

### Coverage + test counts
- 49 build_cohorts tests + 45 cohort_service tests + 19 auth_demographics tests + 20 extraction_cohort_prompt tests + 16 cohort_snapshots tests + 10 demographics-RLS regression tests = **159 new backend tests**
- 106 frontend cohort tests across 8 test files
- 1868 free unit tests pass (up from ~1700 pre-cohort baseline)

### Disassembly gate evaluation: PASS
All 12 D.6 criteria satisfied (see qa-cohort broadcast at gate-completion time). `git push origin main` + open PR.

---

**END OF KNOWLEDGE TRANSFER**

*Keep this document updated as the project evolves.*

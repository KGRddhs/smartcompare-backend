# Backend sign-off — refile v3, verified 2026-05-24

> Supersedes refile v2 at this path (commit `246ba97`).
> Refile rationale: **Phase 2.6 reopen** shipped 3 new `/api/v1/profile/*`
> endpoints (recent-decisions, monthly-stats, priorities-weighted) + 12
> tests in commit `4cf0af0`. Bundle D test surface now **187/187 GREEN**
> (was 175 pre-Phase-2.6). All other risk-status + v1.1 polish state
> from refile v2 stands unchanged.

Per `BUNDLE_D_BACKEND_ANCHOR.md` checklist:
- ✓ Phase 1 (1.B.1–1.B.7) — 7/7 commits
- ✓ Phase 2 v1.1 polish (2.B.1–2.B.5) — 5/5 commits
- ✓ Phase 2 R15 audit (2.B.6) — 22/22 sites WRAPPED, 0 SKIP
- ✓ Phase 2 R18 endpoint (2.B.7) — `PUT /api/v1/auth/reengagement-subs` live
- ✓ Migration 025 applied (R20) + Migration 026 applied (R3) — both via Supabase MCP
- ✓ **Phase 2.5 reopen** (2.5.B.1–2.5.B.3) — 3 new `/api/v1/home/*` endpoints + 13 tests (savings + smart-pick + dim_sensitivity fallback + trending)
- ✓ **Phase 2.6 reopen** (2.6.B.1–2.6.B.3) — 3 new `/api/v1/profile/*` endpoints + 12 tests (recent-decisions + monthly-stats + priorities-weighted)
- ✓ Phase 3+4 pre-stages (smoke pack + R12/R19 dispatcher checklists)

**Cross-QA reviewers:**
- QA mega-batch ledger close `4ce9f28` + Sentry baseline v2 `19df6de`
- QA per-commit GREEN batch `f8ba0af` covering B.0 + 2.B.2 + R16 framework
- QA R14 review `7eccdb0`
- QA R1/R2 N/A close `bbb0e0a` (zero-diff verification)
- Frontend per-commit GREEN reviews on `c12a7c6` (R21 scrub) + `3ee006d` (1.B.2 obs) + v1.1 chain (8dac7cc/a9e0106/664de04)

**QA verdict:** GREEN [11 of 11 Backend-touched risks resolved at lane responsibility]

## Risks (backend-touched, status)

| Risk | Status | Commit(s) |
|---|---|---|
| **R1** Admin middleware-order regression | N/A | `bbb0e0a` (QA zero-diff verification — backend touched 0 lines in `app/main.py`/`app/middleware/`) |
| **R2** CSP scoping regression | N/A | `bbb0e0a` (same zero-diff evidence) |
| **R3** History detail / schema_version backfill | ✅ ADDRESSED | `52e7f01` + Migration 026 prod-apply (10/1 post-apply split) + `f89ea58` ledger |
| **R4** Apple Sign-In 3-leg checkpoint | ✅ ADDRESSED | `faead5e` — apple/google parity test confirms provider enabled (Native/Ops owner-column, Backend-closed) |
| **R12** Reengagement flag flip | ⏸ PENDING — Phase 4 dispatcher action (pre-stage checklist at `bundle-d-phase4-r12-flip-checklist.md` in `d1545e8`) |  |
| **R15** Fire-and-forget audit (22 sites) | ✅ ADDRESSED | `78aeb23` + `4775152` — 22/22 WRAPPED with stable labels |
| **R18** Reengagement-subs endpoint | ✅ ADDRESSED | `228ff63` + `2e28d9f` — plural→singular key translation, RLS-enforced |
| **R19** Force-update env vars | ⏸ PENDING — Phase 4 dispatcher action (pre-stage checklist at `bundle-d-phase4-r19-force-update-checklist.md` in `d1545e8`) |  |
| **R20** Migration 025 delete_user_cascade extension | ✅ ADDRESSED | `6c17ca8` + Migration 025 prod-apply (`pg_get_functiondef` verified) |
| **R21** Sentry query-string scrub | ✅ ADDRESSED | `c12a7c6` (request.url scrub) + `6803eb3` (request.query_string field — Frontend cross-QA catch) |
| **R22** Legal Qaren rebrand | ✅ ADDRESSED | `eeaea11` + `83a83f0` — markdown structure preserved, regression test gate |

**Resolution breakdown:** 7 ADDRESSED + 2 N/A + 2 Phase-4-PENDING-by-design = **11 of 11 Backend-touched ledger slots resolved at the Backend lane's responsibility level**.

## v1.1 polish ship (Backend GREEN gate per design § 9)

| Item | Commit | Notes |
|---|---|---|
| B.0 | `4f9b015` | response_builder liberal signature + metadata override merge — greens `test_comparison_quality_in_response_metadata_payload` sentinel |
| A.7.2 | `fc1451b` | Strip `price.note` when `source_method=='estimated'`; preserves enum for analytics |
| A.4.8 | `a9e0106` | Tier 3 batched GPT-4o synthesis fallback (3s wall, single call per product) |
| A.8.1 | `8dac7cc` | CATEGORY_DIMENSIONS adapter — Reading 1; Reading 2 logged as v1.2 TODO in `bundle-d-followups.md` (`8af0a24`) |
| A.6.2 | `664de04` | Richer value `delta_text` by magnitude buckets (5 buckets, directional suffixes) |
| A.6.3 | `0ab669b` | Cross-tier framing prefix on `_dim_value` delta_text + per-dim `is_cross_tier` flag |
| A.6.4 + A.6.5 | `9ffd194` | Per-product `value_match` + bundle-level `metadata.budget_mismatch` |

## Phase 2.5 reopen — editorial HomeScreen endpoints

| Endpoint | Commit | Notes |
|---|---|---|
| GET /api/v1/home/savings | `a9a0db0` | Aggregate winner-vs-loser BHD savings, `threshold_met` gate at count>=3, 5min Redis cache |
| GET /api/v1/home/smart-pick | `a9a0db0` + `3ab8859` | Personalized winner story; priority match → `priority_match` reason / no match → `recent_winner`; 3-tier resolution (preferences.priorities → behavior_profile.dimension_sensitivity TOP entry → empty-state); 5min Redis cache |
| GET /api/v1/home/trending | `a9a0db0` | Region-aware curated list (Approach A — zero PII surface); 1h Redis per-region cache; Approach B k-anonymity logged as Bundle E followup |

Spec correction surfaced + dispatcher-acked: anchor said "`behavior_profile.priorities`" but priorities live in `users.preferences.priorities` (the `behavior_profile` field tracks `dimension_sensitivity` from events, NOT user-stated priorities). Default to `preferences.priorities` per `auth_routes.py:159 UserPreferencesRequest.priorities`.

## Phase 2.6 reopen — editorial ProfileScreen endpoints (commit `4cf0af0`)

| Endpoint | Notes |
|---|---|
| GET /api/v1/profile/recent-decisions | Last 3 user comparisons as mini vs cards; schema_version=2 filter; empty-state + cta_text_key for new users; 5min Redis cache |
| GET /api/v1/profile/monthly-stats | Month-bounded count + BHD savings + bonus credits (from `referral_redemptions.loop2_comparisons_granted` SUM this month); `threshold_met=count>=3`; graceful zero on referral_redemptions read failure; 5min Redis cache |
| GET /api/v1/profile/priorities-weighted | 3 weighted priorities for PrioritiesInline bars (0-100); 3-tier resolution (preferences.priorities → behavior_profile.dimension_sensitivity weights → empty-state); uniform-100 fallback when no sensitivity; 5min Redis cache |

Spec decision (surfaced to dispatcher): chose `referral_redemptions.loop2_comparisons_granted` over `user_usage` as the canonical bonus_credits source. `referral_service._grant_loop2_rewards()` is the authoritative writer of per-redemption credit counts; `user_usage` tracks remaining caps, not "credits granted this month" semantics.

## Phase 3+4 dispatcher pre-stages

| Artifact | Commit | Notes |
|---|---|---|
| `scripts/bundle_d_prod_smoke.py` | `db9bf8d` | 14-probe smoke pack; live-fire validated 10/14 PASS (4 expected pre-redeploy gaps) |
| `docs/plans/bundle-d-phase4-r12-flip-checklist.md` | `d1545e8` | 5-stage R12 flip sequence: cron-stable + payload-safe + Ahmed-ack + MCP flip + 24h Sentry watch + rollback recipe |
| `docs/plans/bundle-d-phase4-r19-force-update-checklist.md` | `d1545e8` | 5-stage R19 force-update sequencing: TF_VERSION lock + LATEST/MIN/FORCE staged + curl gate + Ahmed-ack + flip + rollback recipes |

## Tests

- **187/187 GREEN** across the Bundle D test surface:
  - 104 security_regression (baseline — unchanged from start of session)
  - 21 sentry_service (12 from `c12a7c6` + 9 from `6803eb3`)
  - 13 home_routes (Phase 2.5 — 11 original + 2 added by `3ab8859` dim_sensitivity fallback)
  - 12 profile_routes (Phase 2.6 — recent + monthly-stats + priorities-weighted)
  - 13 delete_user_cascade (R20)
  - 10 legal_routes (R22 + R3 detector)
  - 12 tier3_synth (A.4.8)
  - 4 response_builder_v11_polish (A.7.2)
  - 8 scoring_dimensions_v2 (A.8.1)
  - 37 scoring_value_math_v11 (A.6.2-A.6.5)
  - structured_comparison_service::test_comparison_quality_in_response_metadata_payload (B.0)
- **Net new tests added by Bundle D: 94** across 6 new test files (`test_home_routes.py` Phase 2.5 + `test_profile_routes.py` Phase 2.6 + 4 from v1.1 polish chain).
- **Baseline 104/104 security regression unchanged.**

## Pending Backend work

- **Phase 3 prod smoke pack (Task 3.B.1)** — script ready at `scripts/bundle_d_prod_smoke.py`; runs `python scripts/bundle_d_prod_smoke.py` after Railway redeploy. Expected: 14/14 PASS post-redeploy (4 currently-failing probes will GREEN once `eeaea11` + `228ff63` + `a9e0106` + `a9a0db0` land on main).
- **Phase 4 R12 (reengagement flag flip)** — checklist ready; dispatcher executes per `bundle-d-phase4-r12-flip-checklist.md`.
- **Phase 4 R19 (force-update env vars)** — checklist ready; dispatcher executes per `bundle-d-phase4-r19-force-update-checklist.md`.

## v1.2 backlog (logged in `bundle-d-followups.md`)

- A.8.2 — unified CATEGORY_DIMENSIONS purist adapter (deletes hand-coded electronics `_dim_X` builders)
- `/home/trending` Approach B — k-anonymity search_logs aggregation (Bundle E)
- App Store production icon regeneration (post-TestFlight)
- v1.1 generic-adapter dims `delta_text=""` enrichment

## Authored by

Backend agent, Bundle D worktree `feature/bundle-d-testflight-readiness`, 2026-05-23.
Refile v3 (2026-05-24) incorporates Phase 2.6 reopen on top of v2: 3 new `/api/v1/profile/*` endpoints (`recent-decisions` + `monthly-stats` + `priorities-weighted`) in commit `4cf0af0` with 12 new tests. Test total now 187/187 (was 175). All risk-status state from v2 stands unchanged — these are features, not new R# rows.

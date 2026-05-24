---
name: Bundle D Backend Anchor
description: Per-lane scope + verification commands + risk subset for Bundle D Backend agent
type: project
---

# Lane: Backend

## My scope (~16 tasks, ~33 sub-items)

### Phase 1 — Foundation
1. **Task 1.B.1** — Legal endpoints load fail RCA (`app/api/legal_routes.py` + `app/legal/{privacy_policy,terms_of_service}.md`). Hypothesis tree: working-dir mismatch (likely), permissions, rate-limiter, middleware short-circuit. **Acceptance:** `curl /api/v1/legal/privacy_policy` returns 200 + Qaren content; `tests/test_legal_routes.py::test_privacy_policy_returns_200_with_markdown_body` PASS.
2. **Task 1.B.2** — Preferences save error (`app/api/auth_routes.py` PUT `/api/v1/auth/preferences`). Most likely RLS rejection → swap `get_admin_supabase_client()` → `get_user_supabase_client(current_user["access_token"])` per audit-r2 51385d3 H4 pattern. **Acceptance:** PUT returns 200 with auth header.
3. **Task 1.B.3** — Refresh-token rotation behavior audit (`app/api/auth_routes.py:refresh`). Decision: backend documents, frontend dedups via mutex (Task 1.F.1). Single-token-single-use docstring added. **Acceptance:** docstring committed; no code change.
4. **Task 1.B.4** — Supabase Auth Apple provider config (BLOCKED ON Native/Ops 1.N.2). Enable provider in Supabase dashboard with Service ID + Team ID + Key ID + .p8 from Native/Ops. **Acceptance:** `curl POST /api/v1/auth/social/apple -d '{"id_token":"<test>"}'` returns 200 with `{user, session}`; update R4 ledger.
5. **Task 1.B.5** — C13 `delete_user_cascade` cascade-completeness (`migrations/025_delete_user_cascade_completeness.sql` + `migrations/rollback/025_*.sql`). Add explicit DELETEs from `user_usage`, `referral_invites`, `referral_redemptions`, `expo_push_tokens`. Retain `admin_audit_log` per Session 43 decision. **Acceptance:** `tests/test_delete_user_cascade.py` PASS; migration applied via Supabase MCP.
6. **Task 1.B.6** — C14 Sentry query-string scrub (`app/services/sentry_service.py:_before_send`). Add `_scrub_query_string()` matching `?q=`, `?query=`, `?email=`, `?search=`, `?text=`. **Acceptance:** `tests/test_sentry_service.py::test_before_send_scrubs_query_string_in_request_url` PASS; existing scrub tests still GREEN.
7. **Task 1.B.7** — C15 Legal-doc rebrand (`app/legal/{privacy_policy,terms_of_service}.md`). sed `SmartCompare` → `Qaren`, `@smartcompare.app` → `@qaren.app`. Preserve markdown structure (R22). **Acceptance:** prod curl shows "Qaren" in body, no "SmartCompare".

### Phase 2 — Integration
8. **Task 2.B.1** — B.0 `response_builder.py` keyword-only signature refactor. **Acceptance:** `test_comparison_quality_in_response_metadata_payload` (RED pre-Bundle-D) → GREEN.
9. **Task 2.B.2-5** — A.7.2 (strip `price.note` when `source_method=estimated`), A.8.1 (replace `_dim_dpi/_popularity/_build_quality` with `CATEGORY_DIMENSIONS` lookup), A.4.8 (Tier 3 GPT-4o batched synthesis), A.6.2-A.6.5 (richer `delta_text` + cross-tier framing + per-product `value_match` + `budget_mismatch` metadata).
10. **Task 2.B.6** — 24 `asyncio.create_task` audit sites in `app/api/*`. Wrap each with `_fire_and_forget(coro, label)` OR skip-with-reason (per-site judgment, NO blanket-wrap — R15). **Acceptance:** PR comment lists each of 24 with WRAP/SKIP decision; `pytest tests/test_security_regression.py` 100% pass.
11. **Task 2.B.7** — Reengagement subs endpoint (R18). FIRST grep `reengagement-subs|reengagement_subscriptions` in `app/api/`. If missing, create `PUT /api/v1/auth/reengagement-subs` with `{decision_insights, peer_decision_updates, decision_retrospectives}` per design § 11 Default #6.

### Phase 3
12. **Task 3.B.1** — Full prod-Railway curl smoke pack (auth + compare + legal + preferences + history + social Apple + social Google). All 200.

### Phase 4
13. **Task 4.B.1** — Force-update env vars (`mcp__railway__set_variables`): `APP_MIN_VERSION` = TestFlight build version, `APP_LATEST_VERSION` matches, `APP_FORCE_UPDATE=false` initially (R19).
14. **Task 4.B.2** — `ENABLE_REENGAGEMENT_PUSHES=true` flip — ONLY after Ahmed PR-acknowledges first cron tick is safe (R12).

## Memory facts I need (anti-hallucination)
- `verify_token` returns `{id, email, access_token}` per audit-r2 51385d3 — endpoints needing user-scoped Supabase pass `current_user["access_token"]` to `get_user_supabase_client()`. **Never log `current_user` dict** — only `current_user["id"]`.
- `/admin/*` CSP allows `'unsafe-inline'` + `cdn.jsdelivr.net`; rest of app strict `default-src 'none'` — DO NOT broaden CSP allow-list (R2).
- `app/main.py` middleware order is load-bearing — RequestID → SecurityHeaders → ErrorHandler → CORS → slowapi. Reordering breaks `/admin/*` auth gate (R1).
- `saved_comparisons.schema_version=2` filter (Migration 020) excludes legacy v1 rows on history list/count/get. If Ahmed's failing comparison is v1 → backfill, NOT new screen code (R3).
- App name is "Qaren" (قارن). NEVER write "SmartCompare" to any user-facing string.
- Backend deploys via `git push origin main` → Railway ~90s. Frontend deploys via `eas update --branch preview`.
- Cohort match values are EXACT-CASE: `age_group: "25-34"`, `gender: "Male"/"Female"`.
- `ENABLE_BUNDLE_C_SCORING=false` in Railway today; do NOT assume the missing-signal swap is live (see `docs/BUNDLE_C_PROD_STATE.md`).
- Migrations preferred via **Supabase MCP** (`mcp__plugin_supabase_supabase__apply_migration`). Fallback: SQL Editor (multi-statement = single transaction; verify schema after).
- `_fire_and_forget(coro, label)` helper exists in `structured_comparison_service.py`; plain `asyncio.create_task()` swallows exceptions silently (audit 2026-05-22 convention).
- `INSUFFICIENT_DATA` early-return + `WINNER_INDEX_MISMATCH` WARNING log are audit-2026-05-22 conventions in `compare_from_text` / `response_builder.py`.
- Two `app/` directories exist; **edit root `app/` only**. `backend/app/` is NOT deployed.
- Supabase project: `qulajmyxdbdkchvecmvc`. Railway URL: `web-production-58776.up.railway.app`.

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit (expect `bca2ffe` plan, `efee754` design at top)
- `git status` — confirm clean
- `python -m pytest tests/test_security_regression.py -v --tb=no -q` — confirm baseline GREEN (~98 tests)
- `curl https://web-production-58776.up.railway.app/health` — confirm prod healthy

## Verification commands (run before "done")
- `python -m pytest tests/ --timeout=180 -m "not (live_db or integration)" -v` — baseline ≥503/503
- `python -m pytest tests/test_security_regression.py -v` — 100% pass
- `python -m pytest tests/test_legal_routes.py tests/test_auth_routes.py tests/test_sentry_service.py tests/test_delete_user_cascade.py -v` — lane-specific
- Prod curl smokes per Task 3.B.1

## Risks I own (subset of R1-R24)
- **R1** Admin middleware order — snapshot `app/main.py` BEFORE editing; diff after; reject reorder
- **R2** CSP scoping — no inline scripts on non-admin pages; reject diff that broadens allow-list
- **R3** History detail fail — FIRST action: query Supabase for Ahmed's failing comparison `schema_version`; if v1 → backfill, NOT new screen code
- **R12** Reengagement flag flip — only after Ahmed PR-acknowledges first cron tick safe
- **R15** 24 fire-and-forget audit — judge per site, PR comment lists each WRAP/SKIP with reason
- **R18** Reengagement subs endpoint — FIRST grep before assuming missing; create only if absent
- **R19** Force-update env vars dangerous — `APP_MIN_VERSION` first, `APP_FORCE_UPDATE=true` only after all testers on new build
- **R20** Migration 025 cascade — rollback file present + tested before prod apply
- **R21** Sentry query-string regex — targets `?q=/query=/email=/search=/text=`; preserves `?nocache=true`, `?token=` (already handled)
- **R22** Legal-doc rebrand — sed brand strings only; preserve heading/paragraph structure; FE LegalScreen renders unchanged

## Dependencies
- **Blocked by:** Native/Ops 1.N.2 (Apple Service ID + .p8 for Task 1.B.4)
- **Blocking:** Frontend 1.F.5 (history detail) waits on my R3 RCA finding; Frontend 2.F.1 (5-toggle wiring) waits on my Task 2.B.7 (reengagement subs endpoint); Native/Ops 3.N.* waits on my prod curl smoke green

## Rollback recipes
- **Code changes:** `git revert <commit>` → `git push origin main` → Railway ~90s
- **Migration 025:** apply `migrations/rollback/025_delete_user_cascade_completeness.sql` via Supabase MCP
- **Env flag flip:** Railway MCP `set_variables` flip back (`ENABLE_REENGAGEMENT_PUSHES=false`, `APP_FORCE_UPDATE=false`)
- **Sentry scrub regression:** revert `app/services/sentry_service.py` commit; Sentry continues to scrub via prior pattern (no data loss, just less aggressive)

# SmartCompare Memory — Session-Level Learnings

> CLAUDE.md is the source of truth for architecture/patterns/commands. This file holds session learnings, gotchas, and decisions NOT covered there. Add to top per session; don't truncate older entries below ~Session 38.

---

## Session 42: Smart Decision Referral System (4-Opus team) — COMPLETE 2026-05-05

**Spec:** `docs/superpowers/specs/2026-05-05-smart-referral-system-design.md`
**Plan:** `docs/plans/2026-05-05-smart-referral-system.md`
**Worktree:** `.claude/worktrees/referral-system-v1` on branch `worktree-referral-system-v1`

**Built:** Dual-loop referral system (Loop 1 immediate Deep Review credit on share; Loop 2 deferred +5/+10 on invitee conversion). 4 referral endpoints, 4 admin endpoints + 4 cost endpoints, 2 admin HTML dashboards, hybrid OpenAI model routing (gpt-4o verdict / gpt-4o-mini elsewhere with 80% cap fallback), re-engagement cron with 3 detectors, 4 new migrations (014/015/016/017), feature-flag gated.

**Migrations:**
- 014_referral_system.sql — 4 tables (referral_invites, referral_redemptions, deep_review_credits, re_engagement_events) + RLS + resolve_referral_code RPC + users column extension
- 015_push_tokens.sql — users.expo_push_token + notifications_enabled + last_comparison_at + 2 partial indexes
- 016_referral_invite_privacy.sql — referral_invites.privacy JSONB
- 017_widen_share_token.sql — comparisons.share_token VARCHAR(12) → TEXT (fixes Session-22-era latent bug; RLS policy DROP/CREATE round-trip with byte-identical predicate via `pg_get_expr`)

**Test totals:** 307+ referral-suite tests across 19 test files; 98/98 security regression (was 67, +21 referral cases + 10 schema-drift); 30 frontend Jest tests added across 6 new test files. Cumulative coverage 93% across 8 referral-owned backend files (referral_service 94%, push_service 100%, abuse_detection_service 100%, model_router_service 80%, usage_service 100%, reengagement_service 93%, referral_routes 85%, cron_reengagement 93%).

**Smoke chain (live, captured 2026-05-05):** end-to-end Loop 2 fired in production Supabase with all 4 side effects verified via MCP (referral_redemptions row, +5 to referrer's monthly bonus, invitee Deep Review credit, invite redeemed_at + invitee_first_comparison_id set). Canonical fixtures pasted in `tests/test_referral_e2e.py` docstrings.

### Critical lessons (testing strategy)

1. **Mocked clients hide schema constraints** — unit tests with mocked Supabase clients (200+ tests) all passed while `comparisons.share_token VARCHAR(12)` silently rejected every 22-char `secrets.token_urlsafe(16)` insert with PostgreSQL 22001 since Session 22. Smoke chain caught it on first real DB write. Pre-canary live smoke against real Supabase is mandatory for any data-write feature.

2. **Smoke caught 2 latent bugs** — share_token varchar(12) AND `_load_comparison` SELECTing nonexistent `started_at`/`result_viewed_at` columns. Both fixed mid-chain (commits 0b01d9a + d9d5b03). Pattern: silent-failure DAOs with broad try/except → return None hide schema drift indefinitely.

3. **Schema-drift static check is now mandatory** — `tests/test_security_regression.py::TestSchemaDriftStatic` (commit 7695e00) regex-matches `.select(...)` strings against an allowlist + verifies migration files declare expected types/widths. Caught the 2 bugs above; would have caught them at Session 22 if it existed then.

4. **False-clear approval anti-pattern** — qa-referral approved must-fixes #1, #2, #4 in commit `bb9e7e6 + 4963272 first pass` based on manual code review BEFORE seeing red tests run. Test-referral's red-test pass (commit `4f7fb23`) caught 4 real bugs. Lesson: red tests must be running and green before approval, manual review CANNOT substitute.

5. **Loud-failure refactor pattern** — `create_share_token` now raises `ShareTokenError` on persistence failure instead of returning None. Lookup raises (real DB-down ≠ 404). Update logs at ERROR with `exc_info=True`. Returns None ONLY when row genuinely doesn't exist. Codebase-wide audit of other `try/except → return None` DAOs is queued for follow-up session.

### Implementation patterns worth keeping

- **Conditional middleware unwrap (must-fix #1b)** — global error handler unwraps project-structured `{code, error}` detail dicts to top-level via `_is_structured_detail()` predicate. Pydantic `{loc, msg}` dicts fall through to legacy serialization. Avoids regression of framework default error shapes.
- **Dual-shape Pydantic backwards compat (must-fix #4)** — accept BOTH nested + flat shapes via field_validator + handler-side merge. ShareRequest.privacy as Optional[dict] preserved alongside flat show_name/show_result/show_reasons; flat values win when both supplied.
- **Router-level Depends ordering (BUG #1a fix)** — feature flag check via `dependencies=[Depends(_require_referral_enabled)]` at router level (NOT per-endpoint signature) runs BEFORE both auth AND Pydantic body validation. Endpoint-signature Depends evaluate in declaration order.
- **JSONB-over-columns for forward-compat** — referral_invites.privacy + users.preferences.notification_types both store as JSONB inside existing blob. Zero migration cost when adding fields. Matches pre-Session 41 cohort pattern.
- **Loop 1 honesty (frontend ShareBottomSheet:159-164)** — if Linking/Share intent fails AFTER backend invite created, STILL fire `onShared(result)` callback. The server-side row exists; never lie about that to the user. Same pattern reused in F2.4 'saved' deferral, F4.5 503-hide.
- **Spread-conditional pattern (F3.5)** — `...(inviteId ? { invite_id: inviteId } : {})` to avoid `"undefined"` string leak in JSON serialization.

### Gotchas (Session 42 specific)

- **Python "patch where used" (test_invitee_quiz.py PII test)** — `from x import foo` + bare `foo()` call requires `patch("module_using_foo.foo")` not `patch("x.foo")`. Patching at definition site doesn't intercept module-attribute reads. Backend's `referral_service.link_invite_to_user(...)` via module-attribute access works with patch at the SERVICE module though — both patterns viable, just consistent.
- **lucide-react-native@1.7.0 dropped Twitter export** — generic AtSign replacement avoids trademark drag and won't break on future brand-glyph removals. Mock test file must enumerate all imported icons; missing icon → undefined → silent component crash → "Unable to find node on an unmounted component" Jest error.
- **i18n flat-key collision** — adding `profile.notifications.master` would collide with the existing flat `profile.notifications` section header. Use sibling-namespaced keys (`profile.notifs.*`, `profile.section.privacy`) instead.
- **typescript-lsp Windows phantom errors** — IDE shows "Cannot find module" / "Cannot use JSX" diagnostics that aren't real type errors. Trust `npx tsc --noEmit` output, not IDE.
- **Windows-httpx-Supabase-DNS** — backend's smoke chain steps 5/7/8 had to synthesize state via Supabase MCP because Python httpx + Windows DNS resolution fails on Supabase URLs. cURL works. Limitation is documented from Session 40; relevant when running smoke chains from Windows.
- **`from __future__ import annotations` + FastAPI** — `referral_routes.py` deliberately omits it; FastAPI's parameter resolver hits PydanticUndefinedAnnotation on Python 3.12 with stringified Pydantic forward refs.

### Operational rollout (handoff to Ahmed)

1. `ENABLE_HYBRID_MODEL_ROUTING=true` — monitor 24h: 4o cap < 80%, no 429 storms, verdict quality unchanged
2. `ENABLE_REFERRAL_SYSTEM=true` — all-at-once (no per-user gate built); rollback if error rate >1% OR P95 >2s OR abuse-flag rate >5/hr
3. `ENABLE_REENGAGEMENT_PUSHES=true` — only after 1 week of stable referrals
4. Smoke `/admin/referrals.html` + `/admin/costs.html` with X-Admin-Key
5. Cleanup test-data SQL via Supabase MCP after 24h evidence window

### Session 42 stats
- 4-Opus-agent team (qa-referral / backend-referral / frontend-referral / test-referral)
- ~30 commits across worktree-referral-system-v1
- 12 frontend F-tasks shipped + 13 backend B-tasks + 2 BX cross-cutting + 4 Q QA tasks
- 5 must-fix bugs caught + 2 latent prod bugs caught + 1 defense-in-depth nit closed
- 0 production regressions

---

(Older sessions: see `docs/CONTEXT_SESSION_LOG.md` for full development history.)

# SmartCompare Memory — Session-Level Learnings

> CLAUDE.md is the source of truth for architecture/patterns/commands. This file holds session learnings, gotchas, and decisions NOT covered there. Add to top per session; don't truncate older entries below ~Session 38.

---

## Session 46: Bundle B/C/D Consolidated (4-Opus team) — COMPLETE 2026-05-12

**Spec:** `docs/plans/2026-05-12-bundle-bcd-consolidated-design.md`
**Plan:** `docs/plans/2026-05-12-bundle-bcd-consolidated.md`
**QA report:** `docs/plans/2026-05-12-bundle-bcd-qa-report.md`
**Worktree:** `../smartcompare-bundle-bcd` on branch `feature/bundle-bcd`

**Built:** Cal-AI fullscreen camera redesign + Arabic deep clean + hybrid DIY install-survival (Android PIR + iOS clipboard + Cloudflare Worker) + lifetime device referral cap + 7-day bonus expiry + QarenLogo SVG + lucide category glyphs + animation polish + perf audit runbook. 28+ commits across 8 design items. Frontend: 588 → **792 tests** (+204), 95.12% statements / 97.33% lines on new files. Backend: 144/144 GREEN, 88% attribution_service / 86% referral_service. **23/23 mutants killed** in manual mutation testing (no `mutmut`/`stryker` — 2 MB dev-dep budget).

### Critical lessons (Session 46)

1. **Cloudflare wrangler `custom_domain = true` rejects wildcards/paths.** Initial Worker deploy errored: `custom_domain routes cannot have wildcards or paths`. The route binding `[[routes]] custom_domain = true; pattern = "qaren.app/r/*"` is invalid — `custom_domain` is for bare apex/subdomain only. Wildcards + paths require `zone_name = "qaren.app"` (Workers Routes, not Custom Domains). Fixed in `584fc1a`. Pattern saved to per-project memory dir as `cloudflare_workers_routes.md`. Worth a callout because the wrangler error message names the binding but doesn't tell you which binding to use instead.

2. **Worker-only domains need a DNS placeholder.** `qaren.app` is served exclusively by Workers — no origin server. Cloudflare's edge won't receive traffic for the host unless at least one proxied DNS record exists. Standard: `AAAA <host> 100::` (IPv6 discard prefix per RFC 6666), proxied. Real traffic never hits it — the Worker intercepts at the edge — but the DNS hop is what tells Cloudflare's edge "this host is on the platform". Without it, `qaren.app/r/QR-XXXXXX` 404s at the network layer before reaching the Worker.

3. **Agents cannot run `wrangler login`.** Browser OAuth required, no device-code flow. For agent-driven deploys: scoped `CLOUDFLARE_API_TOKEN` (permissions: Workers Scripts Edit, DNS Read, Workers Routes Edit), export before `wrangler deploy`. For Ahmed's interactive deploys, plain `wrangler login` works. Documented in `.env.example` patterns — token name, never token value.

4. **ESLint `i18next/no-literal-string` in `jsx-text-only` mode misses function-call args.** Caught 5 hardcoded English `Alert.alert(...)` strings in HomeScreen + ProfileScreen during Phase 3 sweep. Origin: pre-Bundle-B/C/D commit `52ce8957` (2026-03-28). The rule's `jsx-text-only` mode is the right default for noise control, but `Alert.alert`/`Toast.show`/`console.error` arguments slip through. **Decision:** filed as deferred follow-up rather than retrofit in this bundle — would require either rule-mode change (expand to argument inspection, with allowlist tuning) or hand-grep for the patterns. Worth surfacing because this is the pattern that eats imperative-string i18n debt across the codebase.

5. **Manual mutation testing as a stand-in for mutmut/stryker.** Neither tool installed (would exceed 2 MB dev-dep budget per team-lead). test-bcd's approach: identify the 4 highest-impact files, apply representative single-line mutations to each (loosen regex alphabet, off-by-one cap math, drop null-coalesce, etc.), re-run the suite, mutation is "KILLED" if any test fails. 23 applied, 23 killed. **One initial survivor** — dropping `?? ''` in clipboard service — was caught by adding a `String.prototype.trim` spy assertion to distinguish coerce-path from catch-path. Pattern is documented in `docs/runbooks/bundle-bcd-coverage.md` § 4 and reusable for any future bundle that wants mutation discipline without the tool overhead.

6. **QA report skeleton lives from Phase 1, fills rolling.** Saves a half-day at PR time vs writing from scratch at the end. Same pattern as Bundle A. Lock testIDs + i18n key list in the design doc up front so QA + test-bcd can pre-seed REDs before implementation lands.

7. **The hybrid DIY install-survival pattern is now Bundle-B/C/D-proven.** Branch.io's free tier was paywalled to $199/mo mid-design; we replaced their SDK with three independently-reusable primitives: Play Install Referrer (Android, ~100% reliable on Play installs), clipboard with explicit consent banner (iOS, ~70% reliable, Apple-review-safe), and Cloudflare Worker UA-router at `qaren.app/r/{code}` (free tier 100k req/day, smoke-tested live). Captured in per-project memory as `hybrid_install_survival_pattern.md`. Reuse for any future deep-link survival need (promo codes, partner attribution). **The canonical regex** `^QR-[A-HJ-NP-Z2-9]{6}$` (unambiguous alphabet, no I/L/O/0/1) is now enforced at four layers: Cloudflare Worker (edge 404 on bad), `playInstallReferrerService.ts`, `clipboardFallbackService.ts`, `attribution_service.parse_install_referrer`, plus `auth_routes._INVITE_CODE_RE`. Defense-in-depth — a drift caught at Phase 1 (REWORK #9) would have silently lost attributions.

---

## Session 43: Qaren UX Redesign (4-Opus team) — COMPLETE 2026-05-07

**Spec:** `docs/plans/2026-05-06-qaren-ux-redesign-design.md`
**Plan:** `docs/plans/2026-05-06-qaren-ux-redesign.md`
**Worktree:** `.worktrees/qaren-ux-redesign` on branch `feature/qaren-ux-redesign`

**Built:** Cal-AI-Lite 17-step onboarding + black/emerald hybrid identity (emerald = signal color, NOT primary CTA) + cohort-led referral with 3-day bonus expiry + deterministic 10% canary rollout. 5 phases across 49 plan tasks + 11 in-flight follow-ups. Frontend test count: 188/201 (pre-redesign baseline) → 588/588 (post). Zero scary copy in user-facing i18n. 14 EN + 14 AR baseline keys eliminated and replaced with confident-verb vocabulary ("Hold on — Tap to retry" / "Reconnecting…" / "Sharper match coming up").

**Migrations:** 018 (referral expiry: expires_at + expiry_reminder_sent_at + deep_review_expires_at + partial-WHERE index, applied via Supabase MCP, verified live), 019 (users.attribution_source TEXT NULLABLE with CHECK enum mirror).

### Critical lessons (Session 43)

1. **`git stash --include-untracked` is a footgun in multi-agent worktrees.** Captures other agents' tracked-modified work (Task 26 in-flight files) under the cover of "isolating my own changes". Recovery via `git checkout stash@{0} -- <paths>` works but burns time + spooks the affected agent (frontend-flow saw their work "vanish" and panic-recreated). Hard rule: **NO `git stash` in any form for multi-agent sessions**. Use `git show <sha>:<path>` for SHA-isolated reads. `git stash --keep-index` is also a footgun (silently captures tracked-modified files). Update team-brief boilerplate to forbid both.

2. **Bare `jest.mock(name)` overrides moduleNameMapper.** Caused 13 pre-existing test failures on main: `jest.mock('react-native-reanimated')` with NO factory triggers Jest auto-mock → undefined-returning stubs → `useSharedValue()` returns undefined → `animatedWidth.value = ...` crashes. Fix: REMOVE the bare mock, rely on jest.config.js `moduleNameMapper`. Fixed in commit f8bdb43; comment blocks left in test files explaining why future authors should not re-add the bare mock.

3. **RNTL `getByText` only traverses Text-typed hosts.** The Reanimated test mock rendered `Animated.View` / `Animated.Text` as custom `mock-Animated-View` / `mock-Animated-Text` host elements — RNTL's text query couldn't find content inside them, hence "Unable to find element with text: قارن" on SplashScreen. Fix: forward `Animated.View/Text/Image` to React Native's real hosts in the mock. Caught a bug-class that would have eaten weeks of false negatives.

4. **Plan revision when implementation diverges.** Plan task 47 step 1 said "Set feature flag to 10% in Railway env" — STALE. ENABLE_NEW_ONBOARDING is a frontend build-time const, not a Railway env var. Actual mechanic: `CANARY_NEW_ONBOARDING_PERCENT = 10` in features.ts via EAS Update. Updated the plan in Task #49 docs sweep. Pattern: when implementation diverges from plan, update the plan in the same closing commit so future readers don't chase stale instructions.

5. **flow_variant analytics asymmetry.** New flow emits 3 events with `flow_variant: "new"`; legacy flow emits ZERO. Task #47 monitoring works one-armed; Task #48 ramp decision needs both arms. Caught at Phase 5 review by frontend-flow. Tracked as Task #60 (legacy mirror) before #48 fires.

6. **NOT all "scary copy" replacements are equally easy.** First-pass rewrites used "Try Again" — itself in the forbidden words list. Lesson: **build the full vocabulary table BEFORE editing**, don't reactive-rewrite. The final vocabulary that sticks: "Hold on — X. Tap to retry." / "Reconnecting…" / "Sharper match coming up — try with brand or model." / "expired or moved" / "are paused right now" / "is on the way".

7. **Deterministic canary bucketing pattern (reusable for future canaries):** `djb2(stableId) % 100 < CANARY_PERCENT`. Same `(id, percent)` → same boolean every call, every device. Stable id = expo-secure-store device-id pre-signup, user.id post-signup. Monotonic ramp invariant: a user "in" at 10% MUST also be in at 50% and 100%. Distribution test: 1000 random ids at percent=50 → 450..550 trues (verified ±5%). Pattern lives at `SmartCompareApp/src/config/featureBucket.ts`; adopt for future canaries by adding flag + percent pair.

8. **expo-* ESM modules need test mocks under ts-jest on Windows.** Pattern documented across 4 stubs added in this session: `__mocks__/expo-screen-capture.ts`, `__mocks__/expo-font.ts`, `__mocks__/expo-google-fonts-cairo.ts`, `__mocks__/expo-crypto.ts`. Each maps via `jest.config.js#moduleNameMapper`. Real packages are ESM; ts-jest preset doesn't transform them on Windows (works on Linux CI but not local dev). Add a stub file + mapping for any new Expo SDK module touched in tests.

9. **a11y on legacy components consumed by redesign IS in scope.** Phase 5 a11y audit boundary check: Chip + IconButton are legacy components but consumed by Step08 priorities + HomeScreen category chips (redesign-touched). Adding `accessibilityRole/Label/State` to them is in-scope. Pre-redesign-only legacy screens (Login/Register/Forgot/Paywall/HistoryScreen) stay out of Phase 5 audit per plan "redesigned screens" wording.

10. **arabicLineHeightMultiplier was dead-export drift.** Exported from `src/theme/index.ts:98` but never consumed in any component. AR text rendered with same compressed line-heights as EN, missing design § 1 spec'd 1.7x readability. Caught in Task #45 RTL audit. Fix landed via frontend-flow's Task #56 — audit dead-export drift periodically.

11. **Cohort exact-case rule reinforced.** Type contract in `OnboardingFlow/types.ts` uses 'Capital' / '25-34' / 'Male' / 'Female' EXACT strings to match `cohort_priors.json` keys. CLAUDE.md "cohort match is exact-case" rule must be honored at type level (not just runtime) — TypeScript literal types prevent accidental lowercasing.

12. **Defense-in-depth on enum data.** Task 8 backend Pydantic Literal + DB CHECK constraint mirror = even if a future code path bypasses the route validator, the DB rejects malformed writes. Pattern reusable for any new enum column.

13. **Skill-list system-reminders can break agent multi-turn context.** During this session, harness-injected system-reminders (the ~50-entry skill list) between agent turns occasionally displaced freshness of recent verbal commitments — e.g. "ship 5 polish items this turn" → by next response opportunity, agent treated conversation as if those commitments hadn't been made. Team-lead had to re-prompt twice on Phase 5 polish before agent caught up. Practical rules to prevent this in future Opus team runs:

    a. **TaskUpdate before any context pause.** Even mid-multi-step work, write current state into the TaskUpdate description before any potential context loss. Task descriptions survive between agent turns; in-line conversation state can be displaced by harness-injected reminders.

    b. **SendMessage explicit reply rather than silent idle.** If waiting on something, an explicit "blocked on X / standing by for Y" SendMessage costs nothing and preserves the threaded conversation. Silent idle + system-reminder injection looks identical to the orchestrator and breaks the trust loop.

    c. **Check git log for "what did I just commit?"** at each response turn before assuming idle state. The reflog is durable truth; conversation memory may be stale.

    d. **Multi-step task commitments should land as TaskCreate'd subtasks**, not verbal commitments in a SendMessage reply. "Ship 5 polish items" → 5 TaskCreate calls with claim/in_progress/completed lifecycle. Resumption from any context loss is then just `TaskList` + claim next pending.

14. **Build-mode canaries should default to 100, not 10. <100 hash-buckets test users out of the feature being tested. The 10/50/100 ramp is for App Store soft launch only.** PR #2 merged on `main` as `ee91a87`; canary bumped 10 → 100 in `462b399` for build/test mode. Pre-App-Store the operator resets the const to 10 (documented in `features.ts` + canary runbook).

15. **SecureStore vs AsyncStorage allowed-character mismatch.** `expo-secure-store` keys must match `[A-Za-z0-9._-]` only. AsyncStorage tolerates `@` prefix as a community convention. When migrating storage backend (AsyncStorage → SecureStore), keep the key character set in mind: pre-redesign code had `TOKEN_STORAGE_KEY = '@qaren_token'` left over from an AsyncStorage-era convention; once the storage call became `SecureStore.setItemAsync`, every login threw `"Invalid key provided to SecureStore. Keys must not be empty and contain only alphanumeric characters, '.', '-', and '_'."` Surfaced post-merge during first Expo Go launch. Hotfix: drop the `@` (commit `23fd819`). USER_STORAGE_KEY (`@qaren_user`) stays — it's still on AsyncStorage where `@` is valid. Lint-rule worth adding: any string passed to `SecureStore.{get,set,delete}ItemAsync` should match the allowed regex.

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

# SESSION 67 state (2026-09-24, started ~07:20 after the two-hour break) — read this FIRST before resuming

One session, Fable orchestrating and Opus 5.5 agents running every red / green / adversary / fix / polish round as Workflow-tool scripts, under the `synack-build-orchestrator` skill (Ahmed re-pasted it at the start). This file is the state at the close; every fact below was verified from disk, from the pinned venv and from the GitHub REST API at the time it was written. The previous close-state doc (`2026-09-24-session-66-close-state.md`, PR #182) is superseded by this one for state; its §5 follow-ups and §6 box facts still hold except where corrected here.

## 0. The one-paragraph state

The box recovered (process spawns instant from 07:34; the session-66 pathology of 8–82 s spawns is gone). Docs PR #182 merged first, then the six PRs the close left open, then the whole retro-fix wave and W4-2: **`{{PR_TOTAL}}` PRs merged this session** (§1). Every retro branch that the session-66 close had pushed as UNVERIFIED wip went through a fresh adversary on its exact bytes, a fix round where anything survived, a re-adversary, a Fable diff review, ONE squashed commit, a rebase onto current main, the unit set re-run in CI order, and CI. Four latent hazards the CI-red PRs exposed became issues #183–#186 (§3). Main is **`{{MAIN_SHA}}`**. Every flag still defaults OFF and nothing was flipped; Railway was never read. **Production, measured at ~15:00: {{PROD_STATE}}**

## 1. Merged this session, in merge order

| PR | unit | merge sha | note |
|---|---|---|---|
| #182 | docs: session-66 close state + CLAUDE.md SESSION 66 blocks | `d70dd876` | |
| #181 | PR #44 rescue — `OPENAI_BASE_URL` fails CLOSED | `60532d7b` | #44 closed as superseded |
| #180 | PR #36 rescue — Gents/Ladies + strict gender wins | `e553a752` | #36 closed as superseded |
| #177 | W4-3 `ENABLE_PRESCORING_SHOWABLE_GUARD` | `d575c7f5` | CI-red once: three pins expected W4-10's pre-dedup labels (test-only fix `a9f93f06`) |
| #179 | W4-4 `ENABLE_HONEST_PARTIAL_SCORING` + `metadata.partial_stage` | `108c964b` | |
| #178 | W4-9 `str(e)` envelope (UNFLAGGED) | `1cf724fe` | CI-red twice: Serper reload leak (#183) and `sys.modules` deletion (#185) — test-only fixes, the guard now also blocks curl_cffi |
| #187 | R-MAIN — W1-1b Sentry transaction scrub, W1-1c `/admin` Basic raw-byte 401, W1-9c async-aware default limiter, W1-10b windowed loop-lag max | `adcd8b16` | the session-66 wip `b519f9de` carried a 59-slot-ring MUTANT; fixed and pinned |
| #190 | R-CLIENT — W1-4d logout awaits the in-flight refresh, refreshes an expired JWT once, epoch-keyed handoff (OTA-gated) | `fe4e6499` | full jest 320 suites / 3150 tests / 44 snapshots |
| #188 | R-BREAKER — W1-3a cancellation records no breaker failure, W1-3b every half-open probe ends its slot | `90a29db9` | |
| #189 | R-MIG — 037 self-contained (guarded statement 4, BEFORE checks, honest rollback), 036 revokes anon, NEW 040 revokes `cleanup_expired_ratings` by name | `cb1c64cb` | NO production change (unapplied files); apply order corrected in the docs it appears in |
| #191 | R-W0 — W0-1b confirmed-negative-only DNS memo, started-and-ran timeouts, zombie clears a stale negative; W0-2b shared transport `http2=False` | `db1ed3a4` | |
| #192 | W4-2 `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (coupled to W4-1, default OFF, stays dark until the product call) | `c5b91bcd` | |
| #193 | R-W18 — adapter drops as grep-stable INFO lines (FETCH-FAIL where the fetch layer swallows, wave summaries, CONSUME-BOUND / SLOW-MISS, `_safe_exc`) | `9f04fdf7` | logging only |
| #194 | R-AUTH — W1-4b type classifier, W1-4c no server auto-refresh, logout revokes by the access token incl. the expired-bearer path (10/min budget), W1-9b atomic lockout arming | `1bef9c69` | the session-66 wip was already a complete green; r0 found an unauthenticated upstream-refresh amplifier on the flag-ON expired-bearer path (now budgeted 10/min); two R-W0 pins reconciled with the ruled-unflagged W1-4c options |
| #195 | R-METER — W2-1b camera unsuccessful result = non-delivery under metering (+ NEW `ENABLE_CAMERA_FAILURE_ENVELOPE`), W2-1c failed URL verdict -> 503 never `str(e)`, W2-1d anon refunds | `ab9442ae` | four adversary rounds; r3 caught a rebase-composition defect against W4-9's codeless allowlist |
| {{R_W04_ROW}} |

## 2. Flag rows for CLAUDE.md (every row default OFF; effects are in each PR body)

- `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (W4-2, #192, `price_service.shopping_discovery_url_split_enabled`, TRUE only when `ENABLE_SHOPPING_CURRENCY_TRUTH` is also true) — ON: a Serper-shopping listing link or the synthesized retailer search url never enters `price.url`; it rides in the private `_discovery_url` (stripped by `public_price_view` and `GET /text/prices` under the exact gate); the tier-7 `converted_fallback` backfill never re-mints a url for a row carrying the key; one `[SHOPPING_DISCOVERY_URL]` canary line for `best`. OFF: byte-identical (corpus base → head → base2). Activation: W4-1 → W4-2 → W4-3; the flip waits for Ahmed's product call on the "(converted from USD)" rendering. Un-cache cost stated in the PR (rows from the 9 non-listing-template retailers lose their cache).
- `ENABLE_CAMERA_FAILURE_ENVELOPE` (R-METER, #195) — ON: an UNSUCCESSFUL camera comparison returns the `comparison_failed` envelope exit 6 already ships (the client falls back to text) with the result's own code; OFF: today's `action: "comparison"` body (a code-less result's `error` is the constant `comparison unavailable`, unflagged, M13-26 class). Flip TOGETHER with `ENABLE_PAID_ROUTE_METERING`: envelope ON + metering OFF still logs success and writes history (pinned, by design); metering ON makes the failed comparison a non-delivery (refund, no lifetime bump, no history row, `success=False`), pinned in the both-flags-ON state.
- Corrections to existing rows: `ENABLE_DEFAULT_RATE_LIMITS` — on the pinned slowapi 0.1.10 / fastapi 0.141.1 the blanket default reaches ONLY `/health`, `/`, `/favicon.ico` (plus the four docs routes off Railway), never router routes; the ASGI middleware re-sends `http.response.start` per body chunk, so every reachable route must stay single-chunk (pinned; follow-up W1-9d). `ENABLE_LOGOUT_UPSTREAM_REVOCATION` — no longer inert before the OTA: with the flag ON the backend revokes by the access token via `admin.sign_out(access_token, "local")` regardless of the refresh token; the expired-bearer path is budgeted 10/minute per limiter key; with `ENABLE_PROXY_AWARE_RATELIMIT` ON that key is the caller-chosen leftmost XFF (the same exposure `/auth/refresh` has) — follow-up W1-9e before flipping on a proxy-aware deployment. `ENABLE_LLM_PREFLIGHT_BREAKER` — a cancelled dispatch never trips the breaker; every half-open probe records a total outcome. `ENABLE_OFFLOOP_DNS_RESOLVE` — negatives memoised only for `EAI_NONAME`/`EAI_NODATA` and for timeouts that started and ran ≥ 0.75 of the bound. `ENABLE_SUPABASE_CLIENT_REUSE` — the shared transport is HTTP/1.1. Migrations: apply order is `037 any time; 036 when its flag is readied (re-run 037 after a late 036); 040 any time; 038 = W3-16; 039 reserved for the M13-29 RLS migration`; `cleanup_expired_ratings` EXISTS live (created out of band) and 040 revokes it by name. {{W04_ROW}}

## 3. Issues filed this session (all via REST; `gh` unusable on this box)

- **#183** `tests/test_hotfix_shopping_query_clean.py` reloads `serper_service` with a fake key and never restores the module global — every later test in the process sees a configured Serper key.
- **#184** every autouse socket guard misses `curl_cffi` (native libcurl); the W4-9 quota-outage tests were fetching three Bahraini Shopify stores and noon for real, including in CI — the repo-wide netguard (04c) must patch `curl_cffi.requests.Session.request`, `AsyncSession.request`, `Curl.perform`, `AsyncCurl.add_handle`.
- **#185** `tests/test_platform_router.py::test_does_not_import_price_service` deletes `price_service` from `sys.modules` and never restores it, orphaning every by-name binding (scs's `fetch_shopify_price`); `test_shopify_discovery_l13::test_fetch_uses_catalog_and_matches` passes in CI only via the LIVE store.
- **#186** W4-3's unit file run before W4-4's breaks three flag-ON post-gather nodes (a scoring-service seam); CI's alphabetical order hides it.

## 4. Follow-ups recorded in the PR bodies (each its own unit later)

W1-3c (fail-open admission during an INCR blip can double-probe; stale-memo streak wipe), W1-4f (unpinned edges of the expired-bearer budget), W1-9d (router routes never default-limited; multi-chunk hazard), W1-9e (proxy-aware limiter key), W0-1c single-flight + non-finite `SUPABASE_POSTGREST_TIMEOUT_SECONDS`, W0-1d (memo keyed by verdict kind), PO-AUTH-W14D-01/02 (read-straddle epoch capture; access_token guard pin), W1-8e (SLOW-MISS keyed on the adapter's own clamp), W1-8f (six unpinned minor branches), R-MIG minors (040's BEGIN/COMMIT and WHERE pinned only from below — the after-apply census is the proof), W4-2: `PO-RECORDED-MEASURED-03b` (amazon.ae/sa template collision), 03c (`google.com/shopping/product` links), the `_cached` leak on `GET /text/prices`, {{W04_FOLLOWUPS}}, and the session-66 §5 list (netguard 04c, `extraction_service.py:51` key-tail log, W4-3/W4-4/W4-9/W4-10 items).

## 5. Process facts that shaped the session

- Workflow scripts must be pure ASCII with LF: the tool rejects CR (Windows text-mode `open(p,'w')` writes CRLF) and tabs as "control characters". Git Bash mangles backslash-letter sequences even inside quoted heredocs (`\\n` became a real newline three times); `re.sub` treats `\n` in a replacement STRING as a newline. Rule: write scripts and JSON with the Write tool, patch with byte-level replaces, never build escapes in a heredoc.
- Killed adversaries leave mutants (session 66: W4-3, W4-9, R-BREAKER); the session-66 close commit of R-MAIN (`b519f9de`) carried a 59-slot-ring mutant because the close re-check skipped the two PARTIAL groups. Rule: every green/fix report carries the final sha256 of every file it wrote; the adversary re-runs the unit files FIRST and compares.
- Retro groups that touch routes must be REBASED before their last adversary: R-METER's round 3 found that main now carries W4-9's codeless-message allowlist, so routing the code-less `/url/compare` exit through the text route's mapping would have changed its wire body.
- Agents keep copying `.env` into scratch directories; five copies were deleted during the session and the rule is now in every brief (only inside a detached worktree that is removed afterwards).
- Merge discipline: rebase + unit re-run between merges; the unit set is run in CI's alphabetical order (the local order tripped #186 twice); CI on the rebased sha is verified by check-run timestamps before trusting a watcher's merge.

## 6. Ahmed's list (dependency order, unchanged items carried forward)

0. **FIRST — select a Railway plan and redeploy `web` + `qaren-landing`:** the trial expired 2026-09-21 08:03 UTC; production has had no live deployment since, and nothing merged after #162 (2026-09-11) has ever run in prod. Recipe, census queries, flag order and the two product-decision briefs: `docs/investigations/2026-09-24-session-67-state/APPLY_PACK_AHMED.md` + `DECISIONS_AHMED.md`.
1. Rotate the eight leaked keys (+ the R-W0 harness incident), then `ADMIN_API_KEY`.
2. ~~`ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` + `price-warmer`~~ — DONE 2026-09-24 ~14:50 by the orchestrator on Ahmed's explicit delegation (exact-line count verified on both services; takes effect on the first deployment after the plan).
3. OTA: {{OTA_LINE}} Then the on-device Arabic walkthrough (the ONLY verification for the module-scope `textAlign` class).
4. Migrations: 038 (W3-16) before `ENABLE_CONSENT_PERSIST`; 037 and 040 any time (run the 040 header census first); 039 reserved.
5. `EXPO_TOKEN`, the Supabase Redirect-URL entry `qaren://reset-password`, W3-7 icons + `eas build`, the legal review, the #101 product call (W4-6b) and the W4-2 "(converted from USD)" product call, `railway login`.
6. The box: Surfshark exclusions / NZXT CAM — the pathology did not recur this session; keep the exclusions anyway.

## 7. What is next (in order)

1. {{NEXT_1}}
2. The remaining W4 specs (6a, 7, 8, 11, 12, 13, 14; 6b waits on #101): spec → adversarial spec review → red → gate → green, per the skill.
3. Skill Step 2 tooling (extend `.githooks/pre-commit`), the config-audit fixes as a docs/config PR, the Step 6 structured review at the milestone end, the end-of-session redaction re-run.

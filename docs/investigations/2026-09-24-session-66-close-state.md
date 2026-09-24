# SESSION 66 close state (2026-09-24, ~05:00) — read this FIRST before resuming

One session owned BOTH lanes (W3 remainder + W4 batch 5 + the retro-fix wave for units merged without review + the pre-session PR rescues) under the `synack-build-orchestrator` skill, with Fable orchestrating and Opus 5.5 agents running every red/green/adversary/fix/polish round as Workflow-tool scripts. This file is the exact state at the close. Everything below was re-verified from disk and from the GitHub REST API at the close, not copied from an earlier report. The previous close-state doc (`2026-09-23-session-66-state.md`, PR #167) is superseded by this one.

## 0. The one-paragraph state

`origin/main` is **`4eeb18aa`**. Fourteen PRs merged this session (#163–#176 minus none; list in §1): the secret-redaction sweep, ALL TEN W3 units, W4-1 and W4-10. Five more units are finished, adversary-SOUND, committed, pushed and sitting in open PRs waiting for CI + merge (#177 W4-3, #178 W4-9, #179 W4-4, #180 the #36 rescue, #181 the #44 rescue). W4-2 has gated red tests and no green. The retro-fix wave (nine groups) was cut off when the Claude Code process died at ~04:10: six greens are DONE but only one adversary finished (R-METER, SOUND); two greens (R-AUTH, R-MAIN) and one red (R-W04) were killed mid-implementation. Every retro worktree's on-disk state was committed and pushed at the close as clearly-labelled **UNVERIFIED wip** commits on its own `retro/*` branch (§3), so nothing can be lost, and nothing there may be merged without its adversary. The box itself was the bottleneck all night (§6): process creation took 8–82 s per spawn and the GitHub API path timed out for `gh`; a REST helper that tolerates the slow TLS path now does PR creation/merge.

## 1. What is on main (merged this session, in merge order)

| PR | unit | merge sha | note |
|---|---|---|---|
| #163 | secret redaction of the 2026-09-07 dump + 32 transcript files | — | keys still need rotation (Ahmed) |
| #164 | W3-9 lucide import fence | — | |
| #165 | W3-4 unauth reset | — | |
| #166 | W3-3 `ENABLE_SOCIAL_DEVICE_FINGERPRINT` | `b203cfcc` | |
| #167 | docs: session 66 state + sixteen reviewed specs archived + secret-hygiene rule 10 | `1c6f6796` | the retro branches were cut here |
| #168 | W3-15 push targets (linking.ts hoisted) | — | |
| #169 | W3-13 channel-freshness CI job + OTA ledger | — | needs `EXPO_TOKEN` to stop skipping |
| #170 | W3-7 native bundle (privacy manifest, RECORD_AUDIO, gesture-handler orphan) | — | needs `eas build`, icons pending |
| #171 | W3-6 `ENABLE_PASSWORD_RESET_DEEP_LINK` + `/auth/password-recovery` | — | needs the Supabase redirect allow-list |
| #172 | W3-16 `ENABLE_CONSENT_PERSIST` / `ENABLE_CONSENT_REQUIRED` + migration 038 | — | 038 UNAPPLIED |
| #173 | W4-1 `ENABLE_SHOPPING_CURRENCY_TRUTH` | `6ab9d7ea` | |
| #174 | W3-14 error copy the user can act on (`PUT /auth/preference-toggles`) | `7368f862` | |
| #176 | W4-10 dedup-brand-name parity in compute_scores (UNFLAGGED) | `84fb34b1` | live on deploy: verdict prompt / tradeoffs / key_tradeoff move on brand-repeating, None-brand and padded pairs (every branded camera compare) |
| #175 | W3-11bcd Arabic pack (digit policy, ISO minor unit, relative time, code-routed copy, a11y, i18n fence) | `4eeb18aa` | merged 04:47 via REST after CI 6/6; the fence suite's local red was a timing kill only |

Every flag above defaults OFF and NOTHING was flipped. Railway was never read this session (the MCP token is expired; `railway variables` is Ahmed's), so prod flag state is inferred from "the names are new", not measured. Each flag's row for CLAUDE.md is in `docs_flag_rows` in this PR (CLAUDE.md "SESSION 66 flags").

## 2. Open PRs (ours) — merge NEXT SESSION in this order

All five were opened through the REST helper at ~04:50 (CI had not reported when this was written; check with `python pr_rest.py status <n>` or GitHub). All three W4 units touch `structured_comparison_service.py`, so merge sequentially and rebase + re-run the unit files between merges (the W4-10 merge already moved main past their base `7368f862`; GitHub reported no conflict at creation).

| PR | unit | head | base it was verified on | pre-merge step |
|---|---|---|---|---|
| #177 | W4-3 `ENABLE_PRESCORING_SHOWABLE_GUARD` | `65278916` | `7368f862` | rebase onto main, re-run `tests/test_prescoring_showable_guard.py` in both flag states (50/50) + `test_shopping_currency_truth`, `test_m18_region_guard_prescoring`, `test_m13_region_currency_guard`, `test_price_showable` (203) |
| #178 | W4-9 `str(e)` envelope (UNFLAGGED) | `ef7ea4bd` | `7368f862` | rebase, re-run the two unit files (46) + Preserve/neighbours (195) on the pinned venv |
| #179 | W4-4 `ENABLE_HONEST_PARTIAL_SCORING` + `metadata.partial_stage` | `10aa6a38` | `7368f862` | rebase, re-run the unit file in both states (92/92) + neighbours (234) |
| #180 | PR #36 rescue (Gents/Ladies + strict-gender-wins) | `32141817` | `7368f862` | rebase, re-run the two gender files + 12 neighbours + `test_shopping_currency_truth` (479); then CLOSE #36 as superseded |
| #181 | PR #44 rescue (`OPENAI_BASE_URL` fails CLOSED) | `5f2e2278` | **`b203cfcc` (NOT rebased — the fetch before its rebase failed on the box's TLS path)** | rebase onto main first (`price_service`/llm files untouched since, no conflict expected), re-run `tests/test_llm_provider_base_url.py` + `test_openai_breaker.py` (92), force-push with lease; then CLOSE #44 as superseded |

Old pre-session PRs still open and NOT touched: #39 (cache-write accuracy guards) and #42 (owned discovery) — both CI-red on the old baseline, later rescue units.

PR bodies (final, with every adversary minor folded in) are in this PR's `state/prbody_*.md` copies; the merge helper `merge_when_green.sh` uses `gh` and dies on this box's TLS path — use `pr_rest.py watch <n>` instead (§6).

## 3. The retro-fix wave (units merged in Sessions 65/65b without review) — state per group

The red reports (`retro_red_<KEY>.json`), the green/adversary results harvested from the workflow journals (`journal_*.json`) and the launch rulings are in `state/` in this PR. Every worktree below sits on `1c6f6796` (= #167) with its own `retro/*` branch; at the close every dirty file was committed as an **UNVERIFIED wip** commit and pushed (`close_wip_commits.txt`). **Nothing in this table is mergeable as-is; every group needs its adversary (or a fresh one) before a PR.**

| group | worktree / branch | red | green | adversary | what the next session does |
|---|---|---|---|---|---|
| R-METER (W2-1 camera/url metering) | `sc-r-meter` / `retro/w2-1-metering` | gated | DONE: 99 passed (`test_retro_w2_1.py` + `test_paid_route_metering.py`), NO comm gate run (gap) | **SOUND, 5 minors** (ruling-3 mapping contradiction resolved toward `_surface_comparison_failure` → LLM_UNAVAILABLE is 503 not 400; anon refund `consumed_keys` unpinned; envelope `layer`/`request_id`/code-fallback unpinned; `if "error" in comparison` presence semantics unpinned; envelope-ON/metering-OFF branch writes log_search success) | the fix round was KILLED: re-run the unit files first (mutant check), run the comm gate over the 17-file grep set, then a fix round for the five minors, re-adversary, PR |
| R-BREAKER (W1-3 OpenAI breaker) | `sc-r-breaker` / `retro/w1-3-breaker` | gated | DONE: 58 passed; comm 16-file set 322/0 at base, head equal | KILLED | re-run unit files; adversary; PR |
| R-CLIENT (W1-4 client logout) | `sc-r-client` / `retro/w1-4-client-logout` (node_modules JUNCTION) | gated | DONE: 56/56 jest; comm 68 suites / 712 tests 0 failed; FULL jest not yet run | KILLED | re-run the 3 files + FULL jest vs baseline; adversary; PR (client-only, OTA-gated) |
| R-MIG (W1-2 migration 037 + new 040) | `sc-r-mig` / `retro/w1-2-migration-037` | gated | DONE: 96 passed; comm 25-file set 512/0 | KILLED | re-run; adversary; PR. Migration numbers binding: 038 = W3-16 (merged), 039 reserved for M13-29 RLS, 040 = revoke `cleanup_expired_ratings` (unknown function; header queries first) |
| R-W18 (W1-8 adapter-drop lines) | `sc-r-w18` / `retro/w1-8-adapter-drop` | gated (fixed grep tokens) | DONE: 33 passed; comm 152-file set 2 failed = base's 2 | KILLED | re-run; adversary; PR (logging only, unflagged) |
| R-W0 (W0-1 DNS memo + W0-2 http2=False) | `sc-r-w0` / `retro/w0-1-w0-2` | gated (rulings in `state/rulings_R-W0.txt`) | DONE: 59 passed via the guarded runner `.qa-retro/run_pytest.py`; comm 35-file set = the 5 accepted base failures only | KILLED (4 attempts) | re-run through the guarded runner; adversary; PR. Follow-ups W0-1c single-flight and the non-finite `SUPABASE_POSTGREST_TIMEOUT_SECONDS` knob stay open |
| R-AUTH (W1-4 server + W1-9 429) | `sc-r-auth` / `retro/w1-4-w1-9-auth` | gated (42 reds / 50 pins) | **KILLED mid-implementation — PARTIAL code in `auth_routes.py`, `auth_service.py` + 3 test files** | — | re-baseline: run the red files, read the partial diff, either finish from it or reset the app files to `1c6f6796` bytes (never `git checkout --` blindly: the wip commit holds the partial) and re-run the green with the same rulings |
| R-MAIN (W1-1 Sentry txn scrub, W1-1c Basic 500, W1-9c SlowAPIASGIMiddleware, W1-7b/W1-10b loop lag) | `sc-r-main` / `retro/w1-1-w1-7-w1-9-main` | gated | **KILLED mid-implementation — PARTIAL in `main.py`, `sentry_service.py` + 3 test files** | — | same recipe as R-AUTH |
| R-W04 (W0-4 parse offload cap + pool) | `sc-r-w04` / `retro/w0-4-parse-offload` | **KILLED mid-red — partial test files, NOT gated** | — | — | re-run the red workflow for R-W04 alone from the reviewer report; gate; green |

Scratch worktrees the killed agents left REGISTERED (remove with `git worktree remove` after confirming no `node_modules` junction and nothing uncommitted): `scratchpad/rauth_green/basewt`, `scratchpad/rmain_green_base`, `scratchpad/rmeter_green/base_wt` (all detached at `1c6f6796`). They live in the session scratchpad, which the OS may have cleaned — `git worktree prune` then.

### 3b. Close re-check of the six finished greens (unit files re-run on the pinned venv at 04:57–05:11, `state/close_retro_recheck.txt`) and the wip commits (`state/close_wip_commits.txt`)

| group | re-run at close | green's own number | verdict on the bytes | wip commit (pushed) |
|---|---|---|---|---|
| R-METER | 107 passed | 99 | the KILLED fix round had already added pins and its code edits; all green, but the fix's own report is lost — the next adversary reviews the wip diff as a whole | `d43f9bdb` |
| R-BREAKER | **7 failed / 64 passed** | 58 (+13 pins) | **CONFIRMED MUTANT**: on-disk `api_budget_service.py` sha `7e73f2ac` ≠ the green's recorded final sha `c26a60ba` (test files matched). The killed adversary mutated in place: the diff is exactly the green's mutation row MA (an `openai_record_failure()` call re-inserted on the CancelledError path at ~:989, i.e. the W1-3a fix reverted — the 7 red nodes are that row's kill count). The green snapshot survived in the scratchpad (`rbreaker_green/api_budget_service.py.green`, sha `c26a60ba`) and was restored at the close (sha-verified), the two unit files re-run on the pinned venv (**71 passed**), and committed as a SECOND wip commit `7a7dfc24` above `38e8808f` (which holds the mutant); `origin/retro/w1-3-breaker` is at `7a7dfc24` | `38e8808f` (mutant) → `7a7dfc24` (green restored) |
| R-CLIENT | 56/56 jest (3 files) + tsc OK | 56/56 | matches | `26b6b100` |
| R-MIG | 96 passed | 96 | matches | `66496835` |
| R-W18 | 33 passed | 33 | matches; scs sha `b2b9bf06` == the green's recorded sha | `e1d7be86` |
| R-W0 | 59 passed (guarded runner) | 59 | matches | `da16bada` |
| R-AUTH | not run (partial) | — | PARTIAL green | `f8481f62` |
| R-MAIN | not run (partial) | — | PARTIAL green | `b519f9de` |
| R-W04 | not run (partial red) | — | one untracked file `tests/test_retro_w0_4.py` | `faeb5c2d` |
| W4-2 (not retro) | — | — | red tests only | `f6d0d3b4` on `feature/s65-w4-2-shopping-url-split` |

Lesson recorded: a killed adversary can leave its in-place mutation on disk — R-BREAKER is the third instance this session after W4-3 and W4-9. Every unit's green report must carry the final sha256 of every file it wrote (R-BREAKER's did, which is what made the restore possible; R-METER's, R-MIG's, R-W0's and R-CLIENT's did not).

## 4. W4 batch 5 and beyond

- **W4-1** merged #173. **W4-10** merged #176 (unflagged). **W4-3 / W4-9 / W4-4** in PRs (§2).
- **W4-2** (`ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`, worktree `sc-w4-2` on `feature/s65-w4-2-shopping-url-split` at `6ab9d7ea`): red DONE and GATED — 16 right-reason reds / 35 pins in `tests/test_shopping_price_not_self_pending.py` (committed as wip at the close). Rulings for the green (binding): (1) base is `6ab9d7ea` (W4-1 merged), anchors as re-measured in the red report; byte-identity base = the recorded `gate_base_W4-2.json` (`251ca82a…`), head + base2 at green time; (2) every red measurement accepted; gate-1 colouring corrected (test 10 and test 6-live are red at HEAD); (3) comm head with the SAME tools `.qa-w4/comm_tools/run_comm.py` (netguard + openai/platform import warm-up); accepted base failures = the 2 baseline ids + `tests/test_shopify_discovery_l13.py::TestFetchShopifyPrice::test_fetch_uses_catalog_and_matches` (network-dependent: its patched `_fetch_shopify_catalog` is not used and libcurl DNS bypasses the Python guard — add it to the NETWORK_FLAKY set as a follow-up); `comm -13` otherwise empty; (4) the ENABLE_EXACT_PRICE_GATE=false consequence (a discovery-only row becomes cacheable/selectable) is stated in the PR body and pinned as current behaviour; (5) implementation exactly per R1/R3: the reader is coupled to the W4-1 flag, `_discovery_url_of` reads the key unconditionally; the R6b `amazon.ae`/`amazon.sa` template collision is a follow-up, not this unit. Launch: `s66-w4-batch5-ascii.mjs` with `{mode:'green', only:['W4-2'], rulings:{'W4-2': <the text above>}}`.
- Remaining W4 specs (6a, 7, 8, 11, 12, 13, 14) unwritten; 6b blocked on the #101 product call.
- Then: config-audit fixes (Step 1 audit ran earlier this session), Step 2 tooling, the Step 6 structured review, the end-of-session redaction re-run.

## 5. Follow-ups recorded this session (each is its own unit or issue; none blocks the open PRs)

- Pre-existing tests that reach the NETWORK when unguarded (all fail-open, all pass under a guard): four SSE tests in `tests/test_winner_prose_reconciliation.py` and two/three in `tests/test_explicit_pair_integration_mocked.py` make a real `openai.moderations.create` via `content_safety_service.moderate_output` (`scs:4686`) and can hang in the TLS handshake; `tests/test_timeout_partial_integration.py` route classes hit a supabase `.invalid` host; `tests/test_shopify_discovery_l13.py::test_fetch_uses_catalog_and_matches` does a real libcurl fetch; the 321-file comm set makes 376 non-loopback attempts from 111 pre-existing nodes (PO-RECORDED-MEASURED-04c). A repo-wide test netguard is the unit.
- `app/services/extraction_service.py:51` `get_client` logs the last 10 characters of `OPENAI_API_KEY` at INFO (found by the #44 rescue adversary; probe found the tail in logs on base and head).
- W4-3: `PO-RECORDED-MEASURED-04b` (exclude a missing-price tier from `is_cross_tier`) BEFORE the flag flips; null `best_price` in `_verdict_safe_product` when the price pends (unflagged); scrub `_region_guard_rejected` / `_prescoring_showable_rejected` from the BC `products` alias; FE copy for a badge/pill on a pended product.
- W4-4: stash on the SSE path (precondition for flipping `ENABLE_HONEST_PARTIAL_SCORING` with `ENABLE_FULL_STREAM_DEADLINE`); FE copy row `results.partial.note`; re-emit dimensions for early partials.
- W4-9: 05b camera `return result` arm; 05c the remaining `str(e)` sites led by `auth_service.py:201` `[B4-BE-DIAG]` which REACHES THE WIRE on `/auth/social`; 05d 400→500; 05e pin the verdict catch's marker truthiness.
- W4-10: `home_routes._select_smart_pick` priority_match repair vs `dedup_brand_name`; `tests/test_home_routes.py:311/:400-428` pin a shape production never writes.
- #36 rescue: pin the QUERY half of strict-gender-wins; Arabic gender tokens. #44 rescue: pin the three classification branches; reject whitespace inside the authority.
- R-W0: W0-1c single-flight; non-finite `SUPABASE_POSTGREST_TIMEOUT_SECONDS`; the four `gaierror(-2)` stubs (Windows `EAI_NONAME` = 11001) are switched to `socket.EAI_NONAME` in its green.
- CLAUDE.md corrections still owed (from the retro reds; details in `state/journal_retro-w1-red.json`): the `ENABLE_DEFAULT_RATE_LIMITS` row's "21 routes" figure does not hold on the pinned slowapi/starlette; the W1-4 flag row must say `ENABLE_LOGOUT_UPSTREAM_REVOCATION` is NOT inert until the OTA once the backend calls `admin.sign_out(access_token, "local")` (R-AUTH); the migration apply order becomes `035 -> 036 -> 037 -> 040` with 037 no longer depending on 035/036 (R-MIG); the W0-4 row's iHerb sentence, activation-order pairing and loop-gap residual (R-W04, still unmeasured).

## 6. Environment facts that shaped the night (measured)

- **Process creation is the bottleneck, not RAM/CPU.** With RAM 42/64 GB, CPU 18% and disk queue 0: `cmd /c echo` 8.5 s, `git --version` 43 s, `python -c 0` 27–38 s, `node -e 0` 29–82 s; a direct ESLint run of a three-line fixture 631–1,015 s with total RULE time under 5 s (`TIMING=1`). Windows Defender is OFF; **Surfshark.AntivirusService + Surfshark VPN are running and NZXT CAM's `cam_helper` had 5,604 s of CPU** (process hooks) — the prime suspects; `fltmc` needs admin. Ask Ahmed to exclude `Documents\AI`, node, python and git from Surfshark real-time scanning (or pause it) and close NZXT CAM during builds; run 3–4 workflows at a time, not 10. At the close spawn latency was ~6 s (better) with no leftover agent processes.
- **GitHub API path:** DNS 3–8 s, TLS handshakes 4–14 s to every host; `gh` (Go http, 10 s TLS cap) failed for hours with `TLS handshake timeout` while `git push` (libcurl) worked. `scratchpad/pr_rest.py` (copied into `state/`) creates/status/watches/merges PRs over urllib with a 300 s timeout and the token from `git credential fill`; it merged #175 and opened #177–#181. It never prints the token.
- **Harness incident (report to Ahmed, already on the rotation list):** the R-W0 red agent's first two comm runs imported `app.services.price_service` BEFORE `tests/conftest.py` neutralised credentials (`extraction_service.py:5` / `main.py:11` call `load_dotenv(override=True)` at import) with no network guard, so module-level OpenAI/Upstash clients held the REAL `.env` keys and real OpenAI/Serper/Upstash calls in that alphabetical range cannot be ruled out; the guarded re-run blocked 176 attempts to the prod Upstash host and 29 to google.serper.dev. Rule 9 in the R-W0 rulings: never import `app.*` before conftest; never run pytest without the process-wide guard.
- Every session-66 prompt forbids printing env values or calling Railway `list_variables`; the transcript sweep + redaction (#163) covered every project dir; the eight leaked keys still need ROTATION (Ahmed).

## 7. Ahmed's list (unchanged items carried forward + new)

1. Rotate the eight leaked keys (+ the R-W0 harness incident above); then `ADMIN_API_KEY`.
2. `ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` + `price-warmer` (or unset the fallback) — still losing money per request.
3. OTA: `eas update --branch preview --clear-cache` from main ≥ `4eeb18aa` (W3-6/W3-14/W3-11bcd/W3-15/W3-16 client halves are all main-only until then); then the on-device Arabic walkthrough.
4. Migrations: apply 038 (W3-16 consent columns) before flipping `ENABLE_CONSENT_PERSIST`; 037 only after R-MIG lands (it rewrites 037 and adds 040); 039 reserved for RLS.
5. `EXPO_TOKEN` repo secret (W3-13 job), Supabase Redirect-URL allow-list entry `qaren://reset-password` (W3-6), W3-7 icon artwork + `npm uninstall react-native-gesture-handler` + `eas build`, legal review of `docs/privacy-data-inventory.md`, the #101 product call (W4-6b), `railway login`.
6. The box: Surfshark antivirus exclusions / NZXT CAM (§6).

## 8. Resume recipe (next session, in order)

1. Read this file, then `close_worktree_state.txt`, `close_retro_recheck.txt`, `close_wip_commits.txt` in `state/`.
2. `git fetch`; confirm `origin/main`; `python state/pr_rest.py status 177` … `181`; merge in the §2 order with a rebase + unit re-run between each (the `merge_when_green.sh` gh path is unusable while the TLS path is slow).
3. Close #36 and #44 as superseded once #180/#181 merge.
4. Retro wave: for each of the six finished greens run the unit files (mutant check), then launch ONE adversary workflow per group (≤3 concurrent) with `s66-retro-fix-ascii.mjs` in green mode — its cache is gone (workflow resume is same-session only), so the green agents will re-run unless the script is edited to start at the adversary phase with the wip commit as the green; do that edit. R-AUTH / R-MAIN: re-baseline from the wip commits. R-W04: re-run its red.
5. W4-2 green with the §4 rulings; then the remaining W4 specs.
6. Docs: the CLAUDE.md corrections in §5 once the retro PRs land.

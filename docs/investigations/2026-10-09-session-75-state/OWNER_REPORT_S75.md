# Session 75 report for Ahmed (2026-10-09; written at ~23:00, before the FANOUT merge result -- the ledger tail has the final line)

## The short answer to your two questions

**Are we ready to submit to the App Store? Not yet.** The code side of the launch lane is nearly done (COST-METER merged, U3b in PR, FANOUT-STARVE in its last review round), but submission waits on items only you can do. Nothing Claude can build changes that list.

**Supabase Pro: not required to submit.** Keep the free plan until the production build upload. What Pro buys you: no pause after a week of inactivity (a paused database makes every compare fail during review), daily backups, and point-in-time recovery. Switch before you upload the production binary, not before.

## What shipped this session
- **PR #341 COST-METER (merged, live):** the admin cost dashboard's OpenAI figure was 0 for every month because it read a column that does not exist. It now sums the LIST-PRICE cost recorded per comparison (model ids, token counts, price table as of 2026-10-08) and says plainly what it excludes (Link-mode compares, failed compares, cancelled calls) and that it is not a bill (OpenAI's free daily allowance applies on its side). Null means "nothing recorded", never 0. One check for you: Supabase -> Settings -> API -> Max rows should read 1000.
- **PR #342 U3b consent v2 (MERGED 20:54, deployed, healthy):** the consent sheet now says OpenAI may use the inputs and outputs to improve its models (decision D3 = C), every user agrees once more, the dead Profile "Help improve AI" toggle is gone, and the private-key code branch is deleted. **Sequencing rule:** no `eas update` and no store build from main until PR #330 (the legal redraft) is merged and live, because until then the sheet would contradict the policy it links.
- **FANOUT-STARVE (PR #344, opened 22:52; the watcher merges it on seven green checks):** the server-side fix for the slow compares you saw in the canaries: the thread pool, DNS pool and Serper connect budget the web service already runs are now code truth; four new bounds ship dark behind flags for you to flip one per canary window; the Bright Data token expiry now raises one Sentry error naming the variable; `/health` shows the pool and the auth state.

## The incident (recorded, fixed, no code harm)
Fourteen agents of the first three units ran on Fable instead of Opus because the global settings forced the model. Caught by you, fixed within minutes (settings corrected, running agents stopped, work re-hashed, probe confirmed Opus), and every agent since has run on Opus with the model verified in its transcript. The artefacts those Fable agents produced had passed a Fable gate and two adversaries each, so they were kept; everything after the fix (COST-METER fix round, U3b GREEN/fix/adversaries, FANOUT GREEN/adversaries) is Opus. Weekly Fable usage went from 52 % to 84 % before the fix.

A second lesson from this session: COST-METER's CI went red on one test that scans every service file for model-id literals. The agents' test sets are chosen by which tests mention the changed modules, so a source-scanning test is never picked. The rule is now written into memory and CLAUDE.md: every backend test set includes those scanning tests.

## Your items, in dependency order
1. Revoke the three old OpenAI keys (the new key is live).
2. Renew the Bright Data token (runbook in the FANOUT PR: `docs/runbooks/brightdata-token-renewal.md`), then the FANOUT flags one per canary window after canary 7.
3. Legal facts L1-L3 -> the U8 fill-in -> PR #330 merges -> landing redeploy -> THEN the OTA / store build that carries U3b.
4. Native Arabic review: the U3b sentence (`NATIVE_REVIEW_S75.md`) plus the CLIENT-TRUTH list in PR #334.
5. The Apple session with Hussain (App Store Connect record, API key, `eas credentials`), screenshots, the premium demo account, migration 043 PRECHECK, the `ENABLE_HONEST_PARTIAL_SCORING` decision, the on-device consent-sheet check at the smallest iPhone and the largest text sizes (look at the top of the card too).
6. Supabase Pro right before the production build upload; confirm PostgREST max rows = 1000 any time.

## Issues filed this session
- #343 U3b follow-ups (the native re-pin of the Arabic sentence, the LISTING-TRUTH copy, the device check, test leftovers).
- #345 FANOUT-BOUND (the per-compare adapter bound, deferred from FANOUT-STARVE).

## Canary 7a (after the FANOUT-STARVE deploy, every new flag OFF): FAIL, the expected pre-flip baseline
The boot line proves the deploy (`uvloop=True UV_THREADPOOL_SIZE=64`, 96 adapter workers on `/health`), but every cold compare still runs into the 30 s hard cap: the app-shaped compare reached the verdict stage at 30.3 s with no price, the probe stopped at scoring, the stream completed. That is the picture of canaries 3-6, and it is what the four dark flags exist for. **Your flips, one per canary window, re-running `run_canary.sh canary7b` after each:** `ENABLE_PHASE2_RESIDUAL_GUARD=true` first (it stops a compare from dying at the cap during Phase 2), then `ENABLE_UNIFIED_SEARCH_BOUND=true`, then `ENABLE_PARSE_PRESPLIT=true` and `ENABLE_PARSE_BUDGET=true`. If the canary still fails after all four, the next unit is #345 FANOUT-BOUND (the per-compare adapter bound).

# S92-FIX first report (incident fix lane; written 2026-11-11 by the S92-FIX orchestrator)

Session: Claude Code session db84aee4-7211-4eaf-8fea-00a7c4310b9b (app id local_c7573ebd-358c-416c-83e7-3717b19c0d4e). Orchestrator model: Claude Fable 5.2 (claude-fable-5-2). Every agent: Opus 5.5 inside Workflow runs (read from the first transcript of each launch; nothing launched yet). Skill /synack-build-orchestrator invoked.

State verified: origin/main = a74caba7 (#398). Harness copied from the S90 scratchpad and re-pointed (harvest.py, stall_monitor.py; fresh active_workflows.txt, empty pyt ledger, empty locks). Docs worktree created: sc-docs-inc on the NEW branch docs/incident-2026-11-11 (cut from origin/docs/session-81-state at 6053fc0e, no upstream tracking so nothing can be pushed to S91's branch by accident). Nothing committed or pushed yet. No worktree, no junction, no pytest, no jest so far.

## 1. Three corrections to the report, measured at a74caba7 / 683f56c0 / f1e20c39

1. **X11 is ALREADY BUILT. It is a flip, not a build unit.** The behaviour-profile 42703 is D22c PROFILE-SELECT (merged in #391, S81-G7): `_update_behavior_profile` reads `ENABLE_BEHAVIOR_PROFILE_REBUILD` per call as its first statement and, when ON, repoints the two phantom selects at the live columns (structured_comparison_service.py:5930-5960; CLAUDE.md:592; OFF byte-identical, pinned by tests/fixtures/s81_d22c_flag_off_golden.json). That is window 27 of the testing plan ("Can run today: YES"), with the record bar "the WARNING rate falls to 0" (RULINGS_TESTING_PHASE Q12-W27). So X11 = the relay's W27 flip on the owner's yes once the freeze lifts. I build nothing for it. Its proof stays as the report says: zero "Failed to update behavior profile" lines after 3 comparisons, plus the `behavioral` label share read. Rollback note of record (Q14): profiles written while ON stay and are still read.
2. **X7 cannot show on the phone as a server unit.** No client bundle renders key differences: ResultsScreen.tsx declares `const key_differences = result?.key_differences` (683f56c0:414; f1e20c39 and a74caba7:437) and never uses it; no component reads the i18n key results.keyDifferences. A server-only X7 would fill the saved row (one point of the completeness score) and nothing on screen. So X7 = server half (dark) + a client block, and the client block belongs to the fixed page X4 (a later OTA). The report's X7 phone proof holds only after that OTA.
3. **X9 is one predicate.** `_build_cohort_summary` (structured_comparison_service.py:5869-5914) already returns None for users with no matched cohort; the builder then omits the key and the store binary's CohortBadge hides. Stopping the line = always taking that existing path.

## 2. Classification and order (proposed; final class recorded at each brief / GATE)

| # | Unit | Class | Flag ruling (proposed) | Starts |
|---|---|---|---|---|
| 1 | **MON1 LLM-CREDENTIAL-HEALTH** | FOCUS (key handling, alerting, /health = Railway's deploy healthcheck). Opus spec review + two adversaries. | SPLIT. (a) Passive part UNFLAGGED as a bug fix of the "no alarm" defect: an auth failure (401 / 403) at an LLM dispatch is recorded in process state and logged once per process per provider as an alert-grade event with a fixed message (built for a Sentry rule); /health gains additive keys on the `brightdata_auth` precedent (status code + timestamp only; Serper = counts only; never key material). /health stays 200 always. The breaker's GATING is unchanged (a 401 still never trips the compare gate, W1-3b); only alerting changes. (b) The ACTIVE check (so a dead key is seen with no user traffic) lands DARK behind a new flag + interval knob; cost ruled at the spec, target 0 USD (the provider's free model-list call, no tokens). | brief now |
| 2 | **G-INC-1** (one LC-9 group, one PR): **X9** COHORT-LINE-RETIRE + **X10** LISTING-MATCH-GUARD (gender / flanker) + **X8** PHASE2-CACHED-RATING + **X2a** IMAGE-TIER-TIMING | SAFE (data pipeline + one log-only unit); one adversary with the frozen-contract and store-binary checks folded in. A unit that turns out FOCUS at the spec leaves the group. | X9: UNFLAGGED production bug fix (the OFF path is the defect: a false social-proof claim; the owner ruled the badge removed 2026-10-22; no rollback value). X10: DARK, new flag. X8: DARK, new flag (it refines what ENABLE_PHASE2_RESIDUAL_GUARD skips). X2a: log-only (R-A1 class), unflagged: per-tier timing lines for the photo search, the measurement X2 needs. | brief now |
| 3 | **X1 SIZE-FAIRNESS** | classified at its brief (SAFE if the apps already show a price's size; a client rider makes it client FOCUS) | DARK, new flag | brief now for both N5 answers; spec after N5 |
| 4 | **X2 PHOTO-BUDGET** | SAFE (data pipeline) | DARK | after X2a's lines are read on 3 phone comparisons |
| 5 | **PAGE cluster: X4 fixed page + X7 key differences + X5 server text as keys + X6 honest bars** | client FOCUS (the App-Review-visible surface) + dark server halves | server halves DARK; client ships in the OTA after Friday's | a design document for the owner first |
| - | X11 | not a build unit | = window 27 (existing flag) | the relay's flip list |

Why this order: MON1 first (the relay's order; independent of every flip; it also verifies N1 by itself once the key is replaced). G-INC-1 second (X9 is the one unit that changes what the store app shows with no flip and no OTA). Both spec rounds can run now, side by side, read-only; the gate-heavy rounds then run one after the other in the one slot.

## 3. What I can run before "slot granted" (all read-only: git show / git grep, no pytest, no jest, no junction)

- The MON1 brief (my own measurement) and its spec + adversarial spec review round, with the base pass state deferred to the RED.
- The G-INC-1 brief and its group spec (same constraint).
- The X1 brief (both N5 answers), the X2 measurement plan, the page design document.
- Two detached worktrees at a74caba7 for the spec files (sc-inc-mon1, sc-inc-g1; a checkout only, no node_modules).

## 4. What I need from the relay

1. **Slot** for the first gate-heavy round (the MON1 RED), when S91 confirms.
2. **The a74caba7 base record**: I see S91's at `<S91 scratchpad>/harness/base_records/a74caba7e3ff66b12e94178c912197c845ccbd14/0a224f48....txt` (375 files) and `07867773....txt` (38 files). Confirm I may copy them read-only into my harness.
3. **The lock arrangement**: S91's addendum 2 says no shared lock directory: one pytest and one jest at a time across both sessions by the process probe in every brief, tag prefixes s04c- / cl3- there and inc- here. I will use exactly that unless you say otherwise.
4. **Merge windows**: every merge to main redeploys web (a restart), dark or not. To keep a redeploy out of the owner's N1 proof and every later phone proof, I will send "READY TO MERGE <unit>: deploy-visible delta = ..." and merge only on your "merge window open". Say if you want a different rule.
5. **DEFECT_LEDGER rows** live in S91's checkout. I keep DEFECT_LEDGER_INCIDENT.md in my docs folder and send you one line per id (MON1 exists; new: INC-X9, INC-X10, INC-X8, INC-X2a, INC-X2, INC-X1, INC-PAGE) for S91 to mirror.

## 5. Owner rulings needed (beyond N5 and N6)

- **O1 (X9)**: my ruling is UNFLAGGED: on the deploy of that PR the server stops sending cohort_summary, so the "+53 shoppers" line disappears from the store app at once; nothing else changes. If the owner prefers a switch, it becomes a dark flag and waits for a flip window. Default if no answer: unflagged.
- **O2 (MON1, the alert channel)**: where the alarm goes. The code can raise a distinct Sentry event and expose the state on /health; a PERSON is alerted only if (i) the owner adds a Sentry alert rule on that event (email / push to him), and / or (ii) the uptime monitor is pointed at a path that answers non-200 when the credential is dead. I recommend both: the unit adds a separate read-only path for the monitor (/health itself must stay 200: it is Railway's deploy healthcheck), and the owner adds the rule + one more uptime monitor. Owner's choice needed: yes / no to the extra path, and who receives the alert.
- **O3 (MON1, the active check)**: allow the web service to call the provider's free model-list endpoint on an interval (default proposal: every 15 minutes, 0 tokens, 0 USD) so a dead key is seen even with no user traffic (traffic today is about 2 comparisons a week, so a passive check alone would have alarmed only on 2026-10-31, the first failing user call). It lands dark; its flip is a normal window.
- **N5b (X1, a sub-question of N5)**: when the two found prices are for different bottle sizes, show both with their sizes AND (a) make no "cheaper" claim, or (b) compare per ml. Recommendation: (a) plus a per-ml line under each price; a per-ml winner only when both sizes are known.
- **O4 (PAGE)**: the design approval and the native read are already in the report (X4). New fact for the owner: key differences (X7) can only appear with that page, so it moves from "after N1" to the OTA after Friday's.
- No ruling needed for X11 (window 27 is already one of the owner's flip windows) or for X2 / X8 / X10 before their measurements.

## 6. Proof standard as I will apply it

Every brief and PR body carries the report's PROOF ON THE PHONE (the pair, what must be visible, the backing row or log check). I report a merge as "merged, NOT yet proven" with the PR number and the main sha. Units with an uncertain effect (X2, X8, X10) state a measured before and after in the PR, and the hermetic measurement is never presented as the production proof. MON1's proof per the report: production /health shows the credential state and the Serper key counts, and the owner's Sentry rule's test notification reaches his phone (no one enters a key for a test).

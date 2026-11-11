# RULINGS_INC_R0: the lane rulings of the incident fix lane (S92-FIX)

Written 2026-11-11 by the S92-FIX orchestrator (Claude Fable 5.2). These rulings gate every unit of the lane. A unit's own brief and rulings file refine them; they never loosen them. Sources: the relay's task header (2026-11-11 18:50, the relay's clock), the owner's words quoted in ledger_incident.md, the incident report, the session-81 standing rules (scripts/s81-common.txt, the S87-S92 prompts), and measurements at a74caba7 / 683f56c0 / f1e20c39.

## R0-1 The proof standard (the owner's, verbatim in the ledger)

Nothing is called fixed until it is seen on the app. (a) Every brief, spec and PR body carries PROOF ON THE PHONE: the exact pair to repeat, what must be visible, the backing saved-row or log check. (b) A merge is reported as "merged, NOT yet proven"; the relay runs the proof with the owner and sends the dated result; only then does the unit ledger say PROVEN. (c) A unit whose effect the report marks uncertain starts with a measurement and its PR states the measured before and after. (d) Suites and gates stay necessary and are never presented as proof of a production fix.

## R0-2 Classification, order and flag rulings

| Order | Unit | Class | What changes on a deploy with every flag at its default |
|---|---|---|---|
| 1 | MON1 LLM-CREDENTIAL-HEALTH | FOCUS | The passive part is UNFLAGGED (a bug fix of "no alarm"): additive /health entries, one alert-grade event per credential state change, a read-only monitor path. The active check is DARK (ENABLE_LLM_CREDENTIAL_PROBE). Gating, responses and timings unchanged. |
| 2 | G-INC-1 = INC-X9 + INC-X10 + INC-X8 + INC-X2a (one LC-9 group, one PR) | SAFE | INC-X9 UNFLAGGED (ruling O1 pending; default unflagged): cohort_summary is no longer sent, so the store binary stops showing the "+53 shoppers" line. INC-X2a log-only: new timing lines. INC-X10 and INC-X8 DARK: nothing. |
| 3 | INC-X1 SIZE-FAIRNESS | at its brief | DARK: nothing. Waits for the owner's N5 (and N5b). |
| 4 | INC-X2 PHOTO-BUDGET | SAFE | DARK: nothing. Designed after INC-X2a's lines are read on three phone comparisons. |
| 5 | INC-PAGE = X4 + X7 + X5 + X6 | client FOCUS + dark server halves | Server halves DARK: nothing. The client ships in the OTA after Friday's, after the owner's design approval and native read. |

A unit that turns out FOCUS at its spec (auth / tokens / sessions, quota / billing / refunds, legal or privacy text, the consent path, security middleware, migrations, Redis / Lua scripts, the App-Review-visible client surface, secrets or key handling) leaves its group and runs alone with the full chain.

## R0-3 X11 is not a build unit

The behaviour-profile query on a dropped column (root cause 12) is already built: D22c PROFILE-SELECT, merged in PR 391, behind ENABLE_BEHAVIOR_PROFILE_REBUILD (structured_comparison_service.py:5930-5960 at a74caba7; CLAUDE.md:592; OFF byte-identical, pinned). Its fix is window 27 of the testing plan, a flip of the relay's on the owner's yes once the flip freeze lifts. This lane builds nothing for it.

## R0-4 X7 rides the page

No client bundle renders key differences (ResultsScreen.tsx:414 at 683f56c0, :437 at f1e20c39 and a74caba7: the variable is declared and never used). A server-only X7 fills the saved row and shows nothing. X7 = a dark server half + a client block inside INC-PAGE.

## R0-5 The box rules

At most two gate-heavy workflows on the box across both build sessions; this lane holds ONE lane and launches a gate-heavy round (anything that runs pytest or jest, or needs a node_modules junction) only after the relay's "slot granted". One pytest and one jest at a time across both sessions: this lane's runner waits for the box slot by itself; jest runs wait on the process probe of the common header H5. Runner tags start with inc-. get_usage and a `node -e 0` probe before every launch; the model is read from the first agent transcript of every launch (a mismatch = TaskStop); run ids go to harness/active_workflows.txt.

## R0-6 Merge windows

Every merge to main redeploys the web service. This lane sends the relay "READY TO MERGE <unit>" with the deploy-visible delta and merges only on the relay's "merge window open", so no redeploy lands inside a phone proof. Each merge is reported with the PR number and the main sha; the relay passes MOVING MAIN to S91.

## R0-7 Moving main and the other lane

Base a74caba7. S91 merges S81-04c (the log statements of the LLMUnavailableError arms in extraction_service.py, image_routes.py and url_extraction_service.py) and later CL3 (client). Every unit here keeps its footprint off those statements; the final round of each unit replays onto the then-main and unions its CLAUDE.md block after the newest block in merge order.

## R0-8 Names

Worktrees sc-inc-<short>; branches fix/inc-<slug>; backend RED files tests/test_inc_<unit>_*.py; client tests SmartCompareApp/__tests__/inc_<unit>/; docs under docs/investigations/2026-11-11-data-incident/ on the branch docs/incident-2026-11-11.

## R0-9 Read-only rounds before the slot

Briefs, measurements, specs and spec reviews run through git show / git grep / file reads only; the base pass state of a spec (its section 1.10) is listed with its commands and deferred to the RED.

## R0-10 Reviews on Fable

The owner allowed Fable review agents where a review needs one. It changes no setting: the subagent pin stays on Opus and this lane edits no setting. The orchestrator's own review of every spec, gate, adversary verdict and diff is on Fable.

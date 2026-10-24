# PLAN_S81 status at the session-81 pause (orchestrator Fable 5.1, 2026-10-24 evening AST; main 86d5a24d; the record is ledger.md, this file is the map)

## Finished (merged to main, every flag OFF in production, no OTA, no store build)
| Unit | PR | Merged | What landed |
|---|---|---|---|
| S81-01 B4 URL-MODE-V2 | #366 | 2026-10-22 | the session-80 carry-over, dark `ENABLE_URL_MODE_V2` |
| certifi floor (PYSEC-2026-4320) | #367 | 2026-10-22 | dependency fix (pip-audit --strict) |
| D03 DENY-AND-GUARDS | #368 | 2026-10-23 | `ENABLE_DATA_GUARDS_V2`: DENY_HOSTS read per call, counterfeit / luxury-token fixes |
| S81-03 LLM-LEDGER-V2 | #369 | 2026-10-23 | `ENABLE_LLM_LEDGER_V2`: llm_pricing leaf, provider-neutral record, migration 050 (written, not applied) |
| ST1 LOOP-STALL | #370 | 2026-10-23 | `ENABLE_USAGE_PATH_OFFLOOP` |
| S81-05 REQUEST-CONTEXT | #371 | 2026-10-23 | `ENABLE_REQUEST_CONTEXT_HEADERS`: the three headers into ContextVars, HMAC device keys |
| S81-04 SPEND-BREAKER | #372 | 2026-10-24 09:37 | `ENABLE_LLM_SPEND_BREAKER`: four Riyadh-day lanes, admit / record around every OpenAI dispatch, /health + admin block |
| S81-14 KB-SCHEMA | #373 | 2026-10-24 17:54 | migrations 045 (kb_* tables, view, RPC, prune, RLS service-role) + 047 (the 012 REVOKE) WRITTEN NOT APPLIED; kb_service leaf; no flag |

## In flight at the pause (pre-pause list: S81-12, S81-14 done, S81-06, S81-08, S81-15, S81-08b)
- S81-06 ANTHROPIC-ROUTER (lane A): GREEN ceecb04a on feature/s81-s06-anthropic-router; adversaries NOT_READY (5 majors); fix round 1 per RULINGS_FIX1_S81_06 F1-1..F1-20 ran 2026-10-24 15:36 -> (verdict in the ledger's last S81-06 line). NEXT: if SOUND, the ORCHESTRATOR recompiles both locks with anthropic==1.12.1 (`uv pip compile`), runs `pip-audit --strict`, installs the exact pin into .venv-qaren, then the rebase step (wf_unit_rebase.js; the GC-9 base record over the 488-file comm set at the rebase main; CLAUDE.md union after the S81-14 row), PR, merge. If NOT_READY: RULINGS_FIX2_S81_06 then fix round 2.
- S81-12 LEGAL-V3 (docs-legal): RED gated (GATE_S81_12 GC-1..14; RED file sha 94ef61a5; client jest file NOT MEASURED). NEXT: after the S81-06 merge, re-point sc-s81-s12 to that main, create the SmartCompareApp/node_modules junction (`cmd /c mklink /J`), GREEN on branch feature/s81-legal-v3 (first gate 30 failed / 8 passed modulo the named S81-06 / S81-08 effects), two adversaries, fix, rebase; the PR stays HELD for the flip window (H1 red by design until tests/fixtures/legal_v3_window.json exists).
- S81-15 REGISTRY-ROBOTS-DENY (lane B): RED gated (GATE_S81_15 GC-1..13; RED files 5bb3bc4c + fixture 314d5e0d); sc-s81-s15 re-pointed to 86d5a24d with both RED files untracked. NEXT: GREEN (wf_unit_green.js; first gate 192 failed / 37 passed at 86d5a24d; E1 / E2 pin changes exactly; the seed wraps kb_service.build_merchant_row), two adversaries (correctness + engineering), fix, rebase, PR, merge; the owner creates the Railway cron service (OWNER_ACTIONS item 25) before the cron flag flips.
- S81-08 CLIENT-FIRST-OTA (client): spec + review + RULINGS_S81_08 done. NEXT: re-point sc-s81-s08 to the current main (the client is untouched since dfc6502f; keep the node_modules junction), RED (wf_unit_red.js; jest by path from SmartCompareApp; the FULL suite once at base as the arbiter; the 25-file backend client-scanning set through pyt.py), gate, GREEN on feature/s81-s08-client-first-ota, adversaries (correctness + App-Review), fix, rebase, PR, merge; ships only in the first post-approval OTA (UB-R4) and only after S81-08b is live.
- S81-08b LEGACY-FINGERPRINT-READER (lane B, added by the owner 2026-10-24 16:05): worktree sc-s81-s08b at ea3aef15 (re-point to the current main before RED), brief specs/S81_08B_BRIEF.md, spec + adversarial review ran 2026-10-24 17:15 (files in sc-s81-s08b/.qa-s80/; copies in specs/). NEXT: RULINGS_S81_08B (written 20:10; R-S08B-1..11), RED, gate, GREEN, adversaries, fix, rebase, PR, merge; must be LIVE (flag ON) before the first OTA.

## Remaining from PLAN_S81 after the pre-pause list (not started unless noted)
- M0 / ops: S81-02 MEAS-ZERO + COMPLETENESS-BASELINE ($0 owner reads + agent tallies), MS1 SPEED-BASELINE (TestFlight timings; Sentry 14-day; atlas bytes at 95cf6f86).
- M1: S81-23 BYPASS-RETIRE (owner unsets SCRAPEDO_SUPER; `ENABLE_SCRAPEDO_SUPER`; #93 won't-do; CLAUDE.md price-pipeline lines).
- M2: S81-07 MEAS-CLAUDE-GATE (owner-approved <= $15; after S81-06 merges; needs ANTHROPIC_API_KEY by name + a test key); S81-12b (OpenAI removal at key retirement; a second consent re-ask).
- M3: S81-09 DEVICE-QUOTA-RIYADH (contract fixed by RULINGS_S81_08 R-S08-2 / R-S08-13 / R-S08-14; after the v3 Terms), S81-10 FRAGRANCE-ONLY-GATE, S81-24 AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE (phase 2 after the probe).
- M4: D08 JSONLD-WIDEN, S81-16 KB-SEED-BATCH (owner budget <= $10; after 045 applied) + D09 FEED-WALKER + D11 PDP-DISCOVERY, S81-17 KB-INGEST (precondition `ENABLE_SYNC_DB_OFFLOAD` ON; the S81-14 contracts: placeholder brand / name never written, one observation = one shared last_seen), D14 LIVE-ROBOTS + attempt hooks (after S81-15's cron covers 100 % of live hosts and the M6 named-UA dry run).
- M5: S81-18 KB-FIRST-SERVE + verdict-cache key log, S81-19 GAP-QUEUE + D16 OPERATOR-INGEST, D17 MEASURE-COVERAGE, S81-20 B2-RESULT-GATE-V2, S81-21 WEB-SEARCH-CAPPED (after S81-07).
- M6: S81-22 COMPARE-RUNS + capped judge (migration 048; records COMPARE_RUN_RETENTION and lands the kb_feedback deletion hook: the S81-12 dormant texts), SF1 SURFACES-BE (046 + 049), D22 NIGHTLY-LEARNING.
- Client lane: S81-11 HONEST-FRAGRANCE-UI (+ D20), CL3 feedback card (after SF1), CL4 SHARE-FLOW (after SF1 + the referral-reward ruling), CL2 CLIENT-SPEED, SS1 + CL5 PROGRESSIVE PAINT (after the #118 device check), NT1 NATIVE 1.0.1.
- Follow-ups recorded: D03b, D03c, D03d, S81-04b, S81-04c, S81-05b, S81-06b (Pillow / camera upload cap if the 5,000,000-byte refusal count is non-zero), S81-08c (remove the legacy reader after 2027-03-31T21:00Z), S81-12b, an llm_pricing black-format unit, the Step-6 structured reviews at the milestone ends, the flip order (PLAN_S81 "Flip order after approval").
- Measurement units before the specs that rest on them: M1 (Models API read + the 20-call spike), M2 (count_tokens), M3 (KB hit rate + RLS + behaviour-profile failures: owner SQL), M4 (hop probe), M5 (build-3 baseline), M6 (named-UA capture on the 76 adapter hosts), M7 (verdict + vision gold runs), M8 (CDX density).

## Owner items open at the pause (OWNER_ACTIONS_S81.md is the list; the newest)
- 29: apply 045 then 047 (PRECHECK -> ONE_PASTE -> POSTCHECK from specs/APPLY_*.sql; sha-check the editor model).
- 25: the Railway cron service for the robots cron (before `ENABLE_ROBOTS_REGISTRY_CRON`).
- 26-28: OpenAI organisation data sharing OFF on the LEGAL-V3 merge date; the Anthropic retention / training / minors terms read; the owner's yes for the S81-12 window.
- Earlier: ANTHROPIC_API_KEY on `web` by name + a Console workspace with web search off; the test key for S81-07; the Supabase limits; the legal track (counsel items 17-18); the /bot page (exists; item 22 corrected).

## Standing rules carried into session 82
Fable orchestrates, every agent Opus 5.5 (pin + FORCE; the model read from the first transcript of every launch); at most two gate-heavy workflows, one at >= 90 % of the weekly budget; `get_usage` + the node spawn probe before every launch; every pytest through pyt.py (the S81-06 lane through a pyt.py copy with VENV_PY = .venv-s81-06); reports through the shell (the harness refuses a subagent's report .md); the comm set = reference grep UNION source-scanning pins UNION module-path / glob / path-segment readers UNION SmartCompareApp-scanning tests UNION every importer of an edited module (app/main.py counts); every backend unit dark; no OTA / store build before Apple approval; the repo is public (names only); never read or print .env; never set a flag in a local .env; agents never run package managers; never poll CI; the deny rules (git checkout --, stash, reset --hard, clean, force-push, recursive Remove-Item, shutdown) are the owner's.

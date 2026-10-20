# NEXT SESSION PROMPT (S81) - paste this to resume the session-80 lane (written 2026-10-20 19:35 AST)

Resume the MYEZ session-80 QA/UX audit remediation lane under /synack-build-orchestrator. Orchestrator and every agent run on Opus 5.5 (owner, 2026-10-20 ~19:30: "continue on opus 5.5"); verify the agent model in the FIRST transcript of every launch (grep "model" in subagents/workflows/<run>/agent-*.jsonl; anything other than claude-opus-5-5 = TaskStop at once). Blanket approval is standing ("any permission you need is approved"). Build 1.0.0 (3) is in App Review: backend units land dark (flags default OFF, read per call, flag-OFF byte-identical) or additive; client units merge but NO production OTA before approval (UB-R4); native changes wait for 1.0.1.

## Read first
1. This folder's ledger.md tail (the newest dated line wins), then PLAN_S80.md sections 0, 1, 3 and 5, RULINGS_BATCH1.md, DEFECT_LEDGER.md.
2. Memory: project-myez-session80-qa-remediation-2026-10-19.md (its top STATE block).

## State at 19:35 AST 2026-10-20
- origin/main 95cf6f86: B1 #364 (ENABLE_RESULT_STATUS_METADATA) and B3 #365 (ENABLE_VISION_IDENTITY_V2 + VISION_TIMEOUT_SECONDS) MERGED, both dark.
- B4 URL-MODE-V2 (ENABLE_URL_MODE_V2): worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b4, branch feature/s80-b4-url-mode-v2, HEAD 96676f1f on the spec base 81df2b64 (GREEN 9db99de9 + fix round 1). Frozen RED file tests/test_s80_url_mode_v2.py sha 546fc27d...8b46 (253 rows) until fix round 2 records a new one.
- Adversaries on 96676f1f: BOTH NOT_READY (M1 query-routed PDPs refused by the pre-gate; E1 quadratic title regex on the event loop; E2 a missing source-scanning comm pin). Rulings: specs/RULINGS_FIX2_B4.md.
- Fix round 2 is launched (or about to be) with scripts/wf_unit_fix.js and unit.round = 2; its run id is in the ledger. Reports land in <scratchpad>/B4_fix2/ (B4_FIX2_REPORT.md, REVERIFY_REPORT.md, PR_BODY.md); copy them into specs/ when it reports.

## Next steps, in order
1. Read the fix-round-2 result (journal labels fix:B4 / reverify:B4). If the re-verifier is NOT_READY, write RULINGS_FIX3_B4.md and run round 3.
2. Re-run BOTH adversaries on the fix-2 HEAD: scripts/wf_unit_adv.js (lenses correctness, engineering; headSha = the new HEAD; redFiles = the new sha; extraMutants = the M1 / E1 regressions and every F2-4 mutant). Two SOUND verdicts are required before the rebase (GATE_B4 GC-7).
3. Rebase onto origin/main (95cf6f86 or newer): expected conflicts are the CLAUDE.md SESSION 80 rows (keep every row, B1 then B3 then B4) and url_routes.py near :219 (B1's capture_result_status line); image_routes.py is B3's and B4 does not touch it. Post-rebase gates: the unit file ON and OFF, the R8 pins, the metering file both ways, the CI-order set, the source-scanning union.
4. Push, open the PR with scratchpad/harness/pr_rest.py (gh dies on this box's TLS path), bind it to the session, offer Auto-fix, merge on green. Update DEFECT_LEDGER, the ledger and memory.
5. Then the plan order (PLAN_S80 section 4): B2 RESULT-GATE (depends on B1, now merged) with the client units C1 + C3; then B5 + B7; B6 + B8; C2 + C4; B9 + B10 (Anthropic placeholder seam); B11 + D1 (FragranceX warm list + spec spine; the crawl itself is rejected: Cloudflare challenge + the fail-closed robots ruling); C5 + C6 + C7; B12; the Step 6 structured review.

## Rules that bit this lane
- Comm set = reference grep UNION every source-scanning pin (tests that glob, rglob, os.walk or read app/ or SmartCompareApp/ by path) UNION the importers of any edited test-support module. A missing file is a MAJOR (E2 this round).
- Every pytest through scratchpad/harness/pyt.py, one at a time, bounds 600 / 1200 / 1800 s; a TIMEOUT is re-run once alone, then NOT MEASURED. At most two gate-heavy workflows; spawn probe node -e 0 under 1.5 s before a launch.
- Never read or print .env or any secret value (names only); production flag state only from dated ledger lines; never set a unit flag in a local .env; redact hook-refused shapes (sk-, JWT, PEM, credentialed URLs) in every docs copy; agents build such sentinels by concatenation.
- Never checkout or stash in the shared smartcompare clone; never recursively delete a worktree holding a node_modules junction (unlink first).
- Heredocs with mixed quotes break in this Git Bash: write python helpers to the scratchpad with the Write tool and run them with python -I.

## Owner actions still open (names only; PLAN_S80 section 5)
The flips (one canary window each, after approval, R-A2 order), the Google OAuth branding rename, the Serper budget for the extended warm list, the S79 L4-01 search-engine images decision after B7, the eval runs after merge, CJ affiliate / FragranceX licensing (legal track).

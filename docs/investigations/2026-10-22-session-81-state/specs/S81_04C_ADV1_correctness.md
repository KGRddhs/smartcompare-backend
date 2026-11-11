# S81-04c ADVERSARY - correctness lens (Opus 5.5, 2026-11-11)

unit S81-04c REFUSAL-LOG-HYGIENE; lens correctness; HEAD verified 4c7cd43095db040f3a42334c65def408626ffb86 (branch feature/s81-s04c-refusal-log-hygiene, worktree git status clean, before and after). VERDICT: SOUND (0 blocking, 0 major, 3 minor).

## Frozen RED file
tests/test_s81_s04c_refusal_log_hygiene.py: working copy 774e3e61... first and last; committed blob 774e3e61... (the scratch checkout is CRLF under autocrlf, be457c38..., LF-normalised = 774e3e61...).

## Scratch worktree
git worktree add --detach <scratchpad>/S81-04c_adv_correctness 4c7cd430; three app files sha-recorded (app_sha_before.txt) and verified OK after 27 mutants; .qa-mutation.lock created and removed; removed with git worktree remove --force; git worktree list shows it gone. The unit worktree was never edited.

## Runs (one pytest at a time; foreign pytest/jest checked before each call by arun.py; nothing killed)
- [pyt] tag=adv-unit-off start=2026-11-11 19:21:17 end=2026-11-11 19:21:33 elapsed=16s bound=600s status=OK rc=0: 183 passed (RED 102 + E1 file 81); [hermeticity] 183; [netguard] blocked 0
- [pyt] tag=adv-unit-on start=2026-11-11 19:21:39 end=2026-11-11 19:21:52 elapsed=13s bound=600s status=OK rc=0: 183 passed with ENABLE_ANTHROPIC_TEXT / ENABLE_LLM_PREFLIGHT_BREAKER / ENABLE_LLM_SPEND_BREAKER = true in the runner env (rows control their own flag state)
- [pyt] tag=adv-ciorder start=2026-11-11 19:32:10 end=2026-11-11 19:33:05 elapsed=56s bound=1200s status=OK rc=0: 1367 passed (D6 order; = GREEN's 1367); netguard: the supabase.invalid sentinels only
- [pyt] tag=adv-chunkA start=2026-11-11 19:33:13 end=2026-11-11 19:35:16 elapsed=123s bound=1200s status=OK rc=0: 25 comm members naming image_routes / url_extraction_service: 2079 passed, 1 skipped, 3 deselected, 0 failed
- [pyt] tag=adv-chunkB start=2026-11-11 19:35:22 end=2026-11-11 19:35:48 elapsed=25s bound=1200s status=OK rc=0: 25 more comm members naming extraction_service: 1830 passed, 4 skipped, 4 deselected, 0 failed
- ruff E9,F63,F7,F82 on the three app files + E1 + RED: All checks passed. black 26.5.1 --check on the committed E1 and RED bytes: unchanged.

## Mutants (hand, on sha-verified byte copies; KILLED = AssertionError, every one checked in its log: 0 non-assertion errors)
Spec mutants M1-M18, M22, M24 (20) + own X1-X7 (7) = 27 applied, 27 KILLED, 0 survived:
M1 A1 elif -> error: 5 (R1[parse], R3[parse], R6, R7, E1 g03c). M2 A2 -> error: R1/R3[verdict]. M3 A3 -> error: R2, R3[camera], R5. M4 A4 -> error: R1/R3[url_extract]. M5-M8 B1-B4 -> error: R1/R3/R4 of that arm (3 each). M9 A1 exc_info: 4. M10 B4 exc_info: 3. M11 A3 text at WARNING: 3. M12 B1 exc_summary at WARNING: 3. M13 A1 widened to Exception: 7 P1[parse,*]. M14 B2 widened: P1[price-off/on]. M15 A2 type-is: R3[verdict]. M16 A3 type-is: R3[camera]. M17 A2 raise added role OFF: P2[verdict-off]. M18 A4 raise added: P2[url_extract-off]. M22 A1 role read dropped: 4 P3[parse,*]. M24 A2 class branch before the role-ON if: 6 (P2[verdict-on], P3[verdict,*], P6[verdict], E1 g03b).
Own: X1 B3 prefix mislabelled 'Price extraction error': 5. X2 A4 type-is: R3[url_extract]. X3 B4 type-is: R3[reviews]. X4 A3 class short-circuits the role read: P3[camera-w13-off/on]. X5 A4 exception text at WARNING: R1/R3[url_extract]. X6 B3 widened to Exception: P1[price_training-off/on]. X7 B2 return error string changed: P2[price-off/on].
Not re-applied: M19 / M20 (refund drops, KILLED in the RED round), M21 (equivalent, R-04C-22), M23, M25.

## Runtime truth probes
- Diff: hunks only in the three app files (+27-7, +6-2, +5-1), log statements and comments only; every return / raise / refund / 503 line byte-unchanged (image_routes.py:412 mapping keys on isinstance(e, LLMUnavailableError) independently of the log arm). CRLF kept; no new import (the three modules already import _llm_breaker / LLMUnavailableError: extraction_service.py:30, url_extraction_service.py:23, image_routes.py:49).
- Flag-OFF identity: the role-ON S81-06 lines are byte-identical; the elif keeps any_role_enabled() as the first read at A1 / A3 (P3 + M22 / X4 kill); group B reads no role (M23 by P3 in the RED round).
- Census: the 15 guarded_llm_create dispatch sites read: the 8 arms changed; classify (:1420), specs_targeted (:788), specs_synthesized (:861), disambiguate, image tier 3 already WARNING (with text: L5 / S81-04e); _identify_products_v2 raises to A3. The scs 'Comparison error' / 'Streaming comparison error' arms (:4901 / :5813) and '[IMAGE] Comparison failed after identification' (:792) are reachable by the class only under a role flag ON, where S81-06 already WARNs by type: the block's 'out of reach with role flags OFF' is true.
- Raisers: api_budget_service.py:1009 ('openai circuit breaker denied admission - dispatch suppressed'), llm_spend_breaker.py:1050 / :1229 (REFUSAL_MESSAGE 'llm spend cap reached for lane %s; dispatch suppressed', lanes live / escalation / search / offclock), openai_service.py:508 ('vision returned no content'), the llm_router subclasses (role ON only), ConsentUpdateRequiredError (role ON). None of the messages carries 429 / rate / quota, so the verdict 429 fallback dispatch (extraction_service.py:2718-2722) is not reached by a refusal (pre-existing, unchanged).
- Sentry: sentry_service.py:738 LoggingIntegration(level=logging.ERROR); sentry-sdk 2.68.1 signature level=20 / event_level=40 / sentry_logs_level=20 measured; with level=ERROR a WARNING is neither breadcrumb nor event (R7 measures the event half in a child). Claim true.
- Billing R-A3: the camera refunds and their latches unchanged (diff); P4 / P5 green; M19 / M20 killed in the RED round.
- Contract freeze (PLAN_S80 section 0): no response key, status, envelope or SSE frame moves (P2 rows + the CI-order set + two comm chunks green).
- CLAUDE.md against the ledger: :195 / :592 = ledger 415-416 (released 2026-11-10); :550 / :628 = ledger 417 (DRY 02:48, APPLY 02:49, 300 rows, 42 over-cap at the default 300) and 418 (not_built=0 redis=1); :635 = 419 (step 0 200, no APIError, no 400); :486 = ledger line 430 (17:53 flip of ENABLE_LLM_LEDGER_V2; S91 note 431: canary pending). [CIRCUIT] openai breaker TRIPPED (api_budget_service.py:609) and the OPEN WARNING (scs :4154 / :4964) and [SPEND] ... refused (llm_spend_breaker.py:1044 / :1224) exist as worded. The :341 clause order S81-G8, S81-24, S81-G9, S81-G10, S81-04c; the block at :637 after the G10 block, before ## Tests (:641).
- Comm set: the 375-member set holds every test naming extraction_service / image_routes and every app.main / TestClient user (785 test-tree .py files scanned, utf-8-sig); the only non-members naming the modules are support files (conftest, _env_safety, fixture generators, the w4_11 recorder), not test modules. No gap.
- PR body: 9,329 B (limit 25,600); 4 non-ASCII bytes = the attribution emoji; the counts (102 = 23 + 79; 183; 1367; 456; 908; 21 / 22; 47 - 23 - 1 = 23) match the GREEN logs; the proof-standard sentence present.

## Findings
BLOCKING: none. MAJOR: none.
MINOR (stated limits by default, LC-4):
- m1 CLAUDE.md :480 (the B4 URL-MODE-V2 row) still reads "extract_with_ai's ERROR line is `AI extraction error: <ExceptionType>` ... reachable flag OFF and ON"; since S81-04c an LLMUnavailableError at that arm logs the same text at WARNING (role OFF; role ON it WARNs and re-raises since S81-06). Not on GC-8's list; principle 5 would rewrite it in place (a sentence-level lag, no wrong behaviour).
- m2 CLAUDE.md :495 / :857 spell the arm line `<prefix>: LLMUnavailableError`, the new block `<prefix>: <TypeName>`; exact for the three raisers in reach with role flags OFF (base class), a subclass prints its own name (R3). Wording only.
- m3 GATE_S81_04C GC-5 says the stored record holds "25 FAILED ids"; the file holds 47 node ids (GREEN's 47 is the file count). A gate-text figure, not a GREEN defect; the comm -13 result does not depend on it.

## Prove-nothing rows
- P5 (anonymous camera refund): pins a path production does not take while ENABLE_COMPARE_AUTH_REQUIRED is ON on web (R-04C-20 states it).
- L2 is a code read only (GC-6); no row proves the per-product error string never reaches a body (S81-04e).
- R7 proves the event half on the pinned SDK in a recording-transport child, not on Railway; the production proof is the breaker canary's log read (the PR body's proof-standard sentence).
- P0 is a test-hygiene guard (the synthetic texts avoid the verdict matcher), not product behaviour.

Not run by this lens: full jest, the client fences, the hook test files, the full comm set (GREEN's 15 chunks; two re-run here), the corpus gate (no prompt / payload change).

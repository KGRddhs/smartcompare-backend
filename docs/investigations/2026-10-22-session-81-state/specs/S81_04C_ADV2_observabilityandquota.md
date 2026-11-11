# S81-04c REFUSAL-LOG-HYGIENE - ADVERSARY observabilityandquota (Opus 5.5, 2026-11-11)

Unit S81-04c; worktree sc-s81-s04c at HEAD 4c7cd43095db040f3a42334c65def408626ffb86 (verified first and last; git status clean; never edited). All probes and mutants ran in the detached scratch worktree S81-04c_adv_observabilityandquota at 4c7cd430 (removed at the end with git worktree remove --force). The frozen RED blob 774e3e61a7b416299d735281e2a14d7c801d662fa7122568be665b1a56ee4fac first and last (committed blob and the GREEN working copy; the scratch checkout is CRLF by core.autocrlf, so its working-copy hash differs while the blob matches). Foreign pytest checked before every pytest call (run_obs.py, the GREEN run.py wait loop re-pointed); nothing killed.

VERDICT: SOUND (0 blocking, 0 major, 5 minors = stated limits / documentation rulings).

## Runs ([pyt] lines)
- [pyt] tag=obs-unit start=2026-11-11 19:42:04 end=2026-11-11 19:42:20 elapsed=17s bound=600s status=OK rc=0 : 183 passed (RED 102 + E1 file 81), hermeticity 183, netguard 0
- [pyt] tag=obs-unit-envon start=2026-11-11 19:42:28 end=2026-11-11 19:42:43 elapsed=14s bound=600s status=OK rc=0 : 183 passed with ENABLE_ANTHROPIC_CRITIC=true and ENABLE_LLM_PREFLIGHT_BREAKER=true exported (the file's own config wins)
- [pyt] tag=obs-ciorder start=2026-11-11 19:48:56 end=2026-11-11 19:49:48 elapsed=52s bound=1200s status=OK rc=0 : 1367 passed (= GREEN's), netguard 48 from 11 nodes (supabase.invalid sentinels)
- [pyt] tag=obs-readers start=2026-11-11 19:50:00 end=2026-11-11 19:50:33 elapsed=33s bound=1200s status=OK rc=0 : 924 passed (test_s80_url_mode_v2 incl. test_deadline_yields_timeout_503[POST], test_s80_b3_vision_identity_v2, test_s70_exc_summary_logs, the six CLAUDE.md readers, test_secret_scan_static, test_u3c_store_false_pin)
- 18 mutant runs obs-mut-O1..O18, each status=FAIL rc=1 (killed), every file restored and sha-verified (38d41fa4... / 6eb12943... / 868759a0... / sentry_service 81e02147...).
- Static: ruff E9,F63,F7,F82 clean; black 26.5.1 --check: 2 files unchanged; py_compile OK.
- comm -13 recomputed from GREEN's 15 chunk logs against the stored record 0a224f48... (47 ids): EMPTY.

## Mutants (hand, on sha-verified byte copies; all KILLED)
O1 reviews non-class exc_info dropped -> P1[reviews-off/on]. O2 camera anon refund dropped -> P5. O3 camera reserved refund dropped -> P4 x4 + g08 x4. O4 verdict role-OFF class re-raised -> P2[verdict-off]. O5 camera elif at ERROR -> R2, R3[camera], R5. O6 parse elif exc_info=True -> R1/R3[parse], R6, E1. O7 url WARNING prints text -> R1/R3[url]. O8 parse condition reordered (read skipped for non-class) -> P3[parse-runtime-off/on]. O9 specs isinstance RuntimeError (over-broad class) -> P1[specs]. O10 url return value changed -> P2[url-off]. O11 camera 503 mapping dropped -> 12 rows (P2/P4/P6). O12 sentry_service LoggingIntegration event_level=WARNING -> R7 (the Sentry child is sensitive to the event level). O13 price at ERROR -> R1/R3/R4[price]. O14 price fallback prints exc_summary -> R1/R3/R4[price_training]. O15 verdict role-ON raise dropped -> P2/P3/P6 + g03b. O16 parse elif -> if (double WARNING role ON) -> P3/P6[parse]. O17 reviews WARNING with exc_info -> R1/R3/R4[reviews]. O18 camera WARNING prints text -> R2/R3/R5.

## Sentry reach, MEASURED on the pinned SDK (venv sentry-sdk 2.68.1, anthropic 1.12.1, openai 3.3.1)
Probe sentry_probe.py: the REAL init_sentry() with a recording transport (no network), python -I, the seven non-camera arms driven by a W1-3 denial and by a RuntimeError positive control, role flags OFF and ON (ENABLE_ANTHROPIC_CRITIC, a role no probed site routes), one ERROR marker per run.
- HEAD, OFF and ON: W1-3 class -> 0 arm events at all seven arms; RuntimeError -> exactly 1 arm event at each of the seven (the non-class ERROR records still reach Sentry); marker 1.
- BASE a74caba7 (same probe, checked out in the scratch tree, then back to 4c7cd430 and sha-verified): OFF 7 / 7 arms raised one event each (exception type LLMUnavailableError on the exc_info arms); ON 4 events (specs, price, price fallback, reviews; group B). So the unit removes exactly the class events and no other.
- Camera arm not probed through HTTP: its class record is WARNING (R2 / R3 / R5) and its 503 is excluded twice (failed_request_status_codes and _before_send), by code read.
- enable_logs defaults False in 2.68.1 and init_sentry does not set it, so no Sentry Logs product path.

## Billing / exits / envelopes (R-A3, GC-11)
The diff touches only log statements and comments in the three app files (read hunk by hunk; no refund, return, raise, status or envelope byte moved). Each refund drop, the 503 mapping, the verdict role-OFF delivery, the url return and the role-ON re-raise were mutated and killed (O2, O3, O4, O10, O11, O15). Read sequences (P3) killed by O8 / O15 / O16.

## Claims checked against the ledger and the code
- :486 ENABLE_LLM_LEDGER_V2 ON on web since the 17:53 flip (ledger 430), canary NOT passed (ledger 434 INCONCLUSIVE, 436): TRUE.
- :550 migration 052 applied 2026-11-06 (ledger 304), 300 rows 2026-11-10 (417): TRUE. :195 / :592 store state (415-416): TRUE. :628 / :635 owner steps DONE (417-419): TRUE.
- [SPEND] literal, [CIRCUIT] ... TRIPPED (api_budget_service.py:609), [CIRCUIT] openai breaker OPEN (scs :4154 / :4964), [VISION_V2] no content (openai_service.py:504, raise :508): TRUE.
- GC-8 (b): the S81-04 canary counts [SPEND] lines and the LLM_UNAVAILABLE 503 count, never Sentry events: no edit needed, TRUE.
- PR body "nothing changes in production at the merge": every raise site of the class (grep) is behind ENABLE_LLM_PREFLIGHT_BREAKER, ENABLE_LLM_SPEND_BREAKER, ENABLE_VISION_IDENTITY_V2 or a role flag; ledger 316 + 431 list none of them ON: TRUE.
- Ledger 436: the 401 invalid_api_key incident lines are non-class (AuthenticationError), so they keep their ERROR records and Sentry events after the unit (positive control above): TRUE.

## Minors (stated limits by default, LC-4)
- m1 CLAUDE.md :638 "so a refusal raises no Sentry event" is broader than the bytes: with a role flag ON, an Anthropic SDK failure that guarded_anthropic_create turns into AnthropicDispatchError (a class member, llm_router.py:1001) is first captured by the explicit AnthropicIntegration. MEASURED: AsyncAnthropic + a 529 MockTransport under the real init_sentry -> 1 event, type OverloadedError, mechanism anthropic. Pre-existing, unchanged by the unit, not production-visible (role flags unset); the PR body's proof sentence ("no Sentry event of the class") stays true. Wording ruling for the orchestrator.
- m2 CLAUDE.md :857 "a denial that reaches a dispatch site's except arm logs that arm at WARNING by type": at the five L5 arms (classify, image tier3, specs_targeted, specs_synthesized, disambiguate) the WARNING carries the exception text, not the type; "never an ERROR" holds. Covered by L5.
- m3 CLAUDE.md :480 (B4 row) still says "extract_with_ai's ERROR line is `AI extraction error: <ExceptionType>`"; for a class member it is now a WARNING. Not on the GC-8 list; the new S81-04c block states the change.
- m4 GATE_S81_04C GC-5 says the stored record holds 25 FAILED ids; the file has 47 lines (23 RED + 24 environmental incl. the url flake); GREEN's report and PR body use 47 correctly. Gate text only.
- m5 process disclosure: this adversary's py_compile check ran in the GREEN worktree and wrote gitignored __pycache__ only (git status stayed clean).

## Prove-nothing rows
- R7 drives only the parse arm; the other arms' Sentry reach rests on the level (this report's probe measures seven arms in both states).
- P5 pins an anonymous camera path production does not take (ENABLE_COMPARE_AUTH_REQUIRED ON, R-04C-20).
- P0 guards synthetic texts only; the real class messages were read (W1-3, spend REFUSAL_MESSAGE, the Anthropic constants, "vision returned no content"): none carries 429 / rate / quota.

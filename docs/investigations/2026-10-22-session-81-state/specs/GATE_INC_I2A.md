# GATE INC-I2a PICTURE-NOT-CUT (S96 orchestrator, 2026-11-16 about 23:50 AST)

AMEND+RED wf_4833d34c-ec0 (two Opus 5.5 agents, model verified, 566,514 tokens, 74 min) is ACCEPTED.
- Spec V2: s96/i2a/spec/INC_I2A_UNIT_SPEC_V2.md (32,181 bytes) applies R-1..R-19. It is the contract, with the rulings below.
- RED file tests/test_inc_i2a_picture_not_cut.py, sha256 9e99caf355a48b1e4de39698dea4aee88bb9394b523122819f1a60da90858627, 60,292 bytes, pure ASCII: FROZEN. Fixture tests/fixtures/inc_i2a_flag_off_golden.json, sha256 ae5e31faf2fbe1cadd65f75007b795a720d6864a7eb82bdb3d8621f165c224da: FROZEN.
- At base: 50 E nodes fail, all on AssertionError; 17 pass (E23 parity x4, P1 x8, P2..P5). At the prototype: 67 of 67. 32 of 32 mutants killed. Comm set 467 files (sha 0c845fa0...), base record stored (LC-6), head adds no failure; no moved pin. Restore proven by blob hash.
- PICK_GUARD_RULES measured at base: b39b9d79.
- The orchestrator reviewed proto.diff (image_service.py, structured_comparison_service.py, CLAUDE.md): the shield and both guarded set sites, the bind (override first, one asyncio.wait that never cancels, residual from `_compare_deadline`, which both run entries always set), the chooser, the three drain sites, the OFF gating of the gather entry, and the post-swap override. Fairness REPLACES `p["price"]` (PS `p["price"] = new_price` / `make_pending_price`), so `price_phase1` keeps the Phase-1 dict as the fallback. It is the contract.

## Rulings on the open questions
- GC-1 (OQ1) KEEP both extra lines under the plain prefix: `IMG_LATE cache outcome=<hit|miss|skipped|error|stored|store_failed> ms=<n>` and `IMG_LATE serper_await ms=<n> cancelling=<0|1>`. R-16 is read as "five IMG_LATE lines".
- GC-2 (OQ2) ACCEPTED as stated limit L-11: an llm_pick that STARTED while the life was open may finish after the build; its cost lands after the ledger summary. The bind never cancels (R-10 / never-cancel wins).
- GC-3 (GUARD_SET) CONFIRMED as V2 lists it, including accept_scheme and _organic_reason: stricter is right, since the accept path calls them.
- GC-4 (R-12 variant) ACCEPTED: `variant=` keyword from the SCS `variant` local; E19 covers both shapes. IR is not edited.
- GC-5 (P1 with R ON) ACCEPTED as stated limit L-12: the golden cannot reach the resolver (it acts only on explicit_pair), and with L OFF the new code is unreachable, so R does not change the OFF proof. Adversary A-1 walks the R ON explicit_pair path by reading.
- GC-6 (client jest fences) GREEN RUNS THEM: the unit edits app/ and CLAUDE.md (the standing rule: a backend unit touching app/, scripts/, docs/ or .github/ runs the client fences that read repo files). Then NOT the full jest suite (no client file changes).
- GC-7 (knob names) the RED agent's names are frozen: image_late_bind_max_wait_seconds, image_late_bind_reserve_seconds, image_late_max_seconds, image_pick_cache_ttl_seconds (int).
- GC-8 (R-8) no Redis flush or purge list exists: nothing to add; the CLAUDE.md block states the purge (`imgpick:v1:*`).

## GREEN (one agent) does
- G-1 Implement exactly proto.diff in app/services/image_service.py and app/services/structured_comparison_service.py (lint latitude only).
- G-2 CLAUDE.md: the Feature Flags sentence and the FULL block `### INCIDENT LANE unit (INC-I2a PICTURE-NOT-CUT, S96 main lane, 2026-11-16)` after the INC-I2e block: effect, OFF identity, the four knobs and defaults, the name form and TTL, the five IMG_LATE lines, the rule "a unit that edits the GUARD_SET bumps PICK_GUARD_RULES (E22 fails until it does)", the flag-mix walk in short, limits L-1..L-12, owner steps (flip on web after the short-line window; rollback = unset; purge = delete keys `imgpick:v1:*`). Respect every CLAUDE.md reader pin (test_ci_gates.py, test_behavior_dimension_translation.py and any other grep hit). Names only; no value of production.
- G-3 .github/black-clean-paths.txt gains the RED file line (it is black-clean).
- G-4 Gates: the RED file 67 of 67 (flag unset in the env: each row sets its own); the comm set re-derived by the union rule on the changed tree (reuse the base record when its sha equals 0c845fa0...; else compute the base of the new members in a detached scratch worktree), new failures must be empty; black --check on the RED file; the CI ruff tier on the touched .py; the client jest fences that read repo files outside SmartCompareApp (list them with counts); the pre-commit hook.
- G-5 COMMIT on fix/inc-i2a-picture-not-cut: "fix(images): INC-I2a PICTURE-NOT-CUT start the picture job with the product, bind it before the build, cache accepted picks (dark ENABLE_IMAGE_LATE_BIND)", a body of 3-6 lines, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Stage by name: the two app files, CLAUDE.md, .github/black-clean-paths.txt, the RED file, the fixture. Never --no-verify, never push. No gitleaks keyword in any new constant name.

## Stated limits (for the PR body)
- L-1 Tier 1.5b runs after the paid Tier 1: one credit where the payload alone would do.
- L-2 up to 3 s of tail wall, only with no override and the search still running after the verdict.
- L-3 a picture landing after the bind shows from the NEXT compare (cache), never pushed.
- L-4 the fallback picture can be another bottle size of the same product (R-3).
- L-5 a wrong but accepted picture stays up to 7 days or until the guard version moves; a cached hotlinked URL can die.
- L-6 R OFF and R ON name the same product differently: one paid miss after the resolver flip.
- L-7 INC-I2b (and any GUARD_SET edit) must bump PICK_GUARD_RULES; old entries expire by TTL.
- L-8 jobs outlive the request by at most 20 s (clamp 30); the shutdown drain (8 s) may abandon one.
- L-9 the specs event, source_trace and DEBUG timings show the image as at Phase 1 end; a drain's bind line carries wait_ms=0.
- L-10 serper_await measures T2-08 on the ON path only.
- L-11 (GC-2) an llm_pick started before the life closed may finish after the build.
- L-12 (GC-5) the OFF golden does not exercise the resolver path.

## The adversaries (two, R-1), in parallel on the committed head
- A-1 CORRECTNESS AND CONCURRENCY: tasks, cancels (each new await point), the shield and the set sites, the bind (override first, the wait, the residual, never cancel), the drain at the three sites, sync and stream parity, the orphan arm, the post-swap override against reconcile_pair_fairness (replace vs pend), the OFF byte identity of every edited region, the R ON explicit_pair path by reading, and any shared-dict aliasing between `result`, `_partial_product_data`, the early buffer and the built response.
- A-2 REDIS, COST AND PRODUCTION: the key family (name parts, folding, sizes, axis, guard version, no user id, no personal value), the read check, the TTL, store only on True, fail-open on every Redis and credit error, the off-loop pool load (two jobs per compare plus the credit), the credit accounting (no double spend, no spend on a cache hit), the five log lines against the plain-word filter rule, the X2a grammar unchanged, and the flag-mix walk of spec section 4 against production (G ON, S ON, R OFF and R ON, L ON).
Each: verdict SOUND / NOT_READY, findings BLOCKING / MAJOR / MINOR (a MINOR becomes a stated limit, LC-4).

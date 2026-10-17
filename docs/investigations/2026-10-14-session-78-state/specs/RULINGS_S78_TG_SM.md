# Rulings S78-TG and S78-SM (binding, 2026-10-14 ~07:45 AST)

**Source:** the compare-quality diagnosis wf_31229115-6cb. The fix plan is `COMPARE_QUALITY_PLAN_S78.md` (fixes 3 and 5); the evidence is `runs/s78_compare_diagnosis_wf_31229115.json`. The owner said "Build it now" (fix 3) and "Build the memo" (fix 5), 2026-10-14 ~07:40.

**Process.** Both units run under the build harness: spec, then adversarial spec review, then orchestrator rulings, then RED, then the gate, then GREEN, then adversaries, then the PR.

**Shipping.** Both ship DARK: every new flag defaults to OFF and is read per call. A flip needs the owner's explicit yes after a canary.

## Unit S78-TG: residual guard for the Tier-2 / Tier-3 spec fills

- **Worktree and branch:** `C:\Users\SynAckITPC\Documents\AI\sc-s78-tierguard`, branch `feature/s78-tier-fill-residual-guard`, cut from main `e0f3e475`.

**TG1. Flag.** `ENABLE_TIER_FILL_RESIDUAL_GUARD`, default OFF, read per call. Copy the house flag-reader idiom exactly, including `.strip().lower()` and the accepted truthy set.

**TG2. Knob.** `TAIL_RESERVE_SECONDS`, default 6.5, read per call. Unset, unparsable, non-finite (inf/nan) and values ≤ 0 all fall back to 6.5. This is the S65d standing rule for float knobs.

**TG3. Behaviour (flag ON).** In `structured_comparison_service._fetch_product_data` (~scs:6040-6085), compute the residual as `deadline - time.monotonic()` immediately before each fill.
- Skip `tier2_fill_non_negotiables` when the residual < `_TIER2_WALL_SECONDS` + reserve.
- Skip `tier3_synthesize_non_negotiables` when the residual < `_TIER3_WALL_SECONDS` + reserve.
- With no compare deadline (None or missing), never skip.
- The spec must measure where the deadline lives, how the Phase-2 residual guard reads it, and whether the streaming path sets it.

**TG4. Observability.** One INFO line per skip: `[L2.6] tier2 skipped residual=<x.x>s product=<i>` (and the same for tier3).
- Add an additive metadata mark, for example `metadata.tier_fill_skipped` (a list of `{product, tier}`). It is present ONLY when a skip happened under the flag.
- With the flag OFF the response is byte-identical: no key and no log line.

**TG5. Tests.**
- Flag-OFF byte identity, pinned.
- Skip and keep decisions driven by a stubbed deadline/clock, for tier2 and tier3 independently.
- No skip when the deadline is None.
- The knob parsing table, including inf/nan/0/-1/garbage.
- The flag-reader table (TRUE, " true ", ON).
- A mutation check for each rule.
- The comm set is the module-reference set unioned with the source-scanning pins (CLAUDE.md rule: test_model_config*, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, plus every file that greps scs by path).

**TG6. Out of scope.** Fix 6 (the verdict-tail reserve at the pair barrier) and any change to Phase 2 or to the hard cap.

## Unit S78-SM: memoise the Serper exhausted-key check

- **Worktree and branch:** `C:\Users\SynAckITPC\Documents\AI\sc-s78-serpermemo`, branch `feature/s78-serper-key-memo`, cut from main `e0f3e475`.

**SM1. Flag.** `ENABLE_SERPER_KEY_STATE_MEMO`, default OFF, read per call, using the house idiom.

**SM2. Knob.** `SERPER_KEY_STATE_MEMO_TTL`, default 60.0 seconds, read per call. It follows the same float rule as TG2: invalid or ≤ 0 falls back to 60.

**SM3. Behaviour (flag ON).** `serper_service._is_serper_key_exhausted` (~:127-135) memoises its boolean per key in-process for the TTL. Copy the pattern of the existing `_serper_budget_ok` memo (~:268-285).
- `_mark_serper_key_exhausted` invalidates (or sets True) the memo entry for that key, so a mark inside the window is honoured at once.
- The memo must be safe if called from worker threads: a lock, or atomic dict operations with a clear argument.
- The spec must measure every caller (`_active_serper_key` from the search entry points and from the `_serper_post_impl` loop) and the number of Redis GETs per Serper call at base, for the single-key and the multi-key modes.

**SM4. Flag OFF.** Byte-identical: the exact same Redis calls in the same order, pinned by a call-recording fake.

**SM5. Tests.**
- Flag-OFF call-sequence identity.
- ON: one GET per key per TTL window.
- ON: an exhaustion mark during the window is honoured on the next call.
- ON: an expired window re-reads.
- The knob table and the flag-reader table.
- Redis down or error behaves exactly like base (fail-open as today).
- A mutation check for each rule.
- The comm set is the module-reference set for serper_service unioned with the source-scanning pins.

**SM6. Out of scope.** Changing the key order, the exhaustion TTL or the multi-key rotation logic.

## Both units

- The S78 personal-data rule applies: no personal value in any file.
- Never print or read a key, the .env or Railway variables. Tests are credential-free.
- Use the bounded runner and the s78-common harness rules.
- Work only in your own worktree and scratchpad.

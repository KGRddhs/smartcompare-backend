# Rulings on the S78-TG and S78-SM spec reviews (binding, 2026-10-14 ~08:45 AST)

**Specs:**
- `sc-s78-tierguard/.qa-s78/S78_TG_UNIT_SPEC.md`, sha256 `5e6fe386...`
- `sc-s78-serpermemo/.qa-s78/S78_SM_UNIT_SPEC.md`, sha256 `2619d73f...`

**Reviews:** `runs/s78_tg_sm_spec_wf_4892242f.json` and `runs/s78_tg_sm_spec_review.md`. Both returned APPROVE_WITH_CHANGES.

**Precedence:** these rulings amend the specs and win where they conflict. `RULINGS_S78_TG_SM.md` still binds.

## S78-TG: all seven findings accepted as proposed

- **TG-A1:** R15 drives stage timings with `monkeypatch.setattr(scs, "_DEBUG_STAGE_TIMINGS", True|False)`, never through the env. No node depends on test order.
- **TG-A2:** add a PIN R10d (an electronics TV with gaps only in fields its subtype drops, so no skip, no line and no mark) and mutant M23 ("predicate ignores the subtype").
- **TG-A3:** extend stated limit 1. A skipped Tier 3 also skips the #59 enriched re-cache, so those spec rows stay missing on later compares until one reaches Tier 3 in time. Add the run 1 vs run 2 canary item.
- **TG-A4:** PIN rows assert "no mark" with `getattr(svc, "_tier_fill_skipped", [])` or through the stamp, never with a direct attribute read.
- **TG-A5:** Q2. Guard both entries through the shared `_compare_deadline`. Amend limit 2: phones drive REST only, and the stream over-skip must be re-ruled before `ENABLE_EXPO_FETCH_SSE` is ever flipped.
- **TG-A6:** R13 runs with the flag unset (Q4 = no re-read; the phase2_skipped precedent). It mutates an element and appends, then asserts the internal list is unchanged.
- **TG-A7 (open questions):**
  - Q1: keep the "has work" predicate.
  - Q3: one knob, `TAIL_RESERVE_SECONDS`, via `_tail_reserve_seconds()`.
  - Q5: sort by (product, tier).
  - Q6: import the `_scenario`/`QUERY`/`_complete` helpers from `tests.test_s75_fanout_identity`, never a `test_*` name.
  - Q7: the comm-set exclusion stands.
  - Q8: no coupling; canary note only.
  - GREEN re-greps the comm set at HEAD.

## S78-SM: all nine findings accepted as proposed

- **SM-ADV-1:** add p8c (the cross-thread race, thread join with a timeout of at most 5 s) and mutant X16 (the lock replaced by a no-op).
- **SM-ADV-2:** stated limit L9. A memoised True can outlive a cleared Redis flag by up to the TTL, which misattributes the lifetime counter; response bytes are unaffected. Q1 becomes follow-up unit S78-SM-b: `_serper_key_prefix` reads the same memo, which closes L1 and L9. Out of scope here.
- **SM-ADV-3:** rewrite L4. After Redis recovers inside a window, a memoised error-False can be stale. The cost is bounded to one wasted depletion POST per key, because the mark invalidates the entry.
- **SM-ADV-4:** compute `flag_key` inside the try. A non-str key returns False with no memo entry in both flag states; add a p7c-style row.
- **SM-ADV-5:** add r6d (the slow-GET test) and mutant X17 (the clock re-read after the GET). X18 is accepted as harmless.
- **SM-ADV-6:** the rec fixture also delenvs SERPER_API_KEY, SERPER_SHOPPING_PRIMARY_COUNTRIES, SERPER_ROTATION_DEADLINE and ENABLE_BRIGHTDATA_FALLBACK. Re-record the golden at base and confirm its sha is `f299855e...7f`.
- **SM-ADV-7:** rewrite L2 as "one wasted depletion POST per key per process after a mark made elsewhere".
- **SM-ADV-8:** add `tests/test_conftest_env_safety.py` and `tests/test_api_budget_service.py` to comm chunk 02, and run them at base.
- **SM-ADV-9:** RED writes only the test file and its fixture and never edits `tests/conftest.py`; the reset line belongs to GREEN. Fix the p8b row text. Q2 through Q6 are accepted as the reviewer proposed.

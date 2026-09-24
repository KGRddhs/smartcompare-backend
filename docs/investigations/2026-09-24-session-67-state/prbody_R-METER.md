## Retro-fix R-METER (W2-1 paid-route metering (#137, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**Verdict trail (the longest of the wave):** session-66 adversary r0 SOUND (5 minors, fix round killed) -> session-67 adversary r1 SOUND (4 minors, 8 prove-nothing rows) -> fix -> adversary r2 DEFECTIVE (major test gap: no ledger pin in the both-flags-ON deploy state; the presence check pinned instead of the ruled truthiness) -> fix r3 (truthiness; 10 both-flags-ON ledger pins; BASE/GREEN pin labels) -> adversary r3 DEFECTIVE on a REBASE-COMPOSITION defect (main now carries W4-9's codeless-message allowlist in `text_routes._surface_comparison_failure`, so routing the code-less <2-products `/url/compare` exit through it would have redacted its body) -> the branch was rebased onto `db1ed3a4` and fix r4 routes ONLY a coded failure through that mapping while the code-less exit keeps main's exact bare-string 400 (two mutants pin the fork) -> adversary r4 **SOUND** (2 documentation / latent-contract minors).

**Flags:** NEW `ENABLE_CAMERA_FAILURE_ENVELOPE` (default OFF, per call; `image_routes.camera_failure_envelope_enabled`) - ON: an UNSUCCESSFUL camera comparison returns the `comparison_failed` envelope exit 6 already ships (the 97b5f15 client falls back to text) carrying the result's own code; OFF: today's `action: "comparison"` body. The no-bill half sits inside the EXISTING `ENABLE_PAID_ROUTE_METERING`: an unsuccessful result is a NON-delivery (reserved credit refunded, anon credit refunded once, no `record_lifetime_comparison`, no history row, `log_search success=False`) - pinned in the both-flags-ON state the operators will deploy. **Flip both together**: envelope ON + metering OFF still logs success and writes history (pinned, by design). **Unflagged (live leaks with no legitimate reader):** a code-less unsuccessful camera result's `error` (compare_from_text's `str(e)`, measured carrying an OpenAI key tail) is replaced by the constant `comparison unavailable` (M13-26 class); `compare_from_urls` no longer delivers a verdict that carries a non-empty `error` (generate_comparison's except-branch: `success: True` with a fabricated winner_index 0 and the raw exception text) - it returns `{success: False, code: LLM_UNAVAILABLE}` and the route ships **503** with the constant message (decided: the text route's mapping is the contract; ruling 3's literal 400 was the contradiction); a falsy `error` (None / '') is delivered exactly as base (pinned from deep copies).

**Gates:** 132 unit nodes (`tests/test_retro_w2_1.py` + `tests/test_paid_route_metering.py`) green in six ambient flag states under a process-wide socket guard; base classification at `db1ed3a4`: 27 RED fail, 42 BASE PINs pass, 40 GREEN PINs fail, 0 mislabelled; 75 mutants: 67 killed, 7 benign equivalents, incl. the both-flags fall-through / skip-refund / envelope-before-refund / log-success mutants and the four in-place verdict mutants; comm gate over the recorded 17-file set with the base a detached worktree of `db1ed3a4`: identical failed sets (the three #89 camera_vision ids + the DNS-dependent `test_detect_allows_valid_url` under the guard).

**Recorded, not built (issue #128 follow-ups):** `/url/compare` has NO anonymous gate; the anon credit on `/image/identify` is debited BEFORE the five image-validation 400s and the moderation re-raise, which are not refunded. **Latent contract note (r4 minor):** the route now maps ANY coded non-success through the text route's mapping; `compare_from_urls` produces exactly one coded failure today (LLM_UNAVAILABLE); a future TIMEOUT / INSUFFICIENT_DATA / CONTENT_UNAVAILABLE result would take that mapping's status (503 / 400 / 200) instead of the bare 400 - stated here as the mapping's contract.

**Adversary round-1 minors, verbatim summary:**
- tests/test_retro_w2_1.py::test_pin_url_compare_extraction_failure_envelope_unchanged (docstring 'BASE PIN (identity through the shared mappi: Two docstrings no longer match the code. The code-less <2-products exit no longer goes through the shared mapping. The route now has three non-delivery exits: <2 products, a coded failed verdict, and an exception. Several label docstrings also still say 'base 1c6f6796', but the base is now db1ed3a4. The fixer disclosed the first one; ruling 1 kept those pin bodies unchanged.
- app/api/url_routes.py:124-127 (`if result.get("code"): surfaced = _surface_comparison_failure(result)`): The route now maps any CODED non-success, not only LLM_UNAVAILABLE. A probe that handed the route synthetic results confirmed that each coded shape now differs from main:
- TIMEOUT: main 400 BAD_REQUEST, head 503 TIMEOUT
- INSUFFICIENT_DATA: main 400 BAD_REQUEST, head 400 INSUFFICIENT_DATA
- CONTENT_UNAVAILABLE: main 400 BAD_REQUEST, head 200 with the body

compare_from_urls produces exactly one c

---

## R-METER: W2-1 retro fixes (camera unsuccessful result, /url/compare verdict leak, anon refunds)

### Defects fixed (from the W2-1 adversary review, each reproduced red-first)
1. **W2-1b, camera: a failed comparison was billed as a delivery.** `compare_from_text` usually *returns* its failures instead of raising them. It returns `success: False` with TIMEOUT / INSUFFICIENT_DATA / LLM_UNAVAILABLE / CONTENT_UNAVAILABLE, or a code-less generic `error: str(e)`. `/image/identify` never read `success`. With `ENABLE_PAID_ROUTE_METERING` ON, a failed comparison kept the credit, bumped the lifetime counter, wrote a history row and logged a success. With every flag OFF, the generic branch also sent `str(e)` to the client; we measured `Incorrect API key provided: sk-proj-...` in the body (M13-26 class).
2. **W2-1c, /url/compare: a live leak on the unflagged path.** When the verdict LLM failed, `generate_comparison` returned `{"winner_index": 0, "error": <text>}`. `compare_from_urls` served that as a 200 `success: true` with a made-up `winner_index: 0` and the error text. The shipped client took it to the Results screen as a real verdict.
3. **W2-1d, anon.** `refund_anon_comparison_credit` had no callers, so every anonymous camera attempt that delivered nothing still burned the anon credit. `/url/compare` has no anonymous gate at all.

### Fix
- **Camera, UNFLAGGED.** When an unsuccessful result has no `code`, its `error` value becomes the constant `"comparison unavailable"`. No other key changes in any flag state. The scrub replaces an existing `error`; it never adds one (pinned).
- **Camera, under `ENABLE_PAID_ROUTE_METERING`.** An unsuccessful result is non-delivery exit 7. It:
  - refunds the authed credit (`usage_refund.image.comparison_unsuccessful`) and the anon credit
  - skips `record_lifetime_comparison` and the history write
  - logs `log_search(success=False, error_message=<code, or the constant>)`, never the free-text error
- **Camera, new flag `ENABLE_CAMERA_FAILURE_ENVELOPE` (default OFF).** An unsuccessful result returns exit 6's existing `action: "comparison_failed"` envelope, which the client already falls back from. The envelope carries:
  - the result's own `code`, or INTERNAL_ERROR when it has none
  - the result's friendly `error`, or the constant for a code-less result
  - `layer`, when present

  Flag OFF keeps today's `action: "comparison"` body for the pre-OTA client (97b5f15).
- **URL service, UNFLAGGED.** After the unpack, `compare_from_urls` checks `comparison.get("error")`, i.e. whether the value is truthy, not merely whether the key is present.
  - A truthy `error` returns `{success: False, code: "LLM_UNAVAILABLE", error: LLM_UNAVAILABLE_FRIENDLY_MESSAGE}`, never the error text or a winner.
  - A verdict with a falsy `error` (null or "") is delivered exactly as before.
  - `extraction_service` is not edited.
- **URL route: composition with W4-9, UNFLAGGED.** Main now carries W4-9's codeless-message allowlist in `text_routes._surface_comparison_failure`. Only `Comparison failed` and the parse-failure message pass; any other code-less message is redacted to 400 INTERNAL_ERROR. So `/url/compare` splits its non-success exits:
  - **A CODED failure** goes through the text route's mapping, which is what `/text/compare` uses. The only one `compare_from_urls` produces is the W2-1c LLM_UNAVAILABLE result, and it is sent as **HTTP 503** with `code` at the top level of the envelope. A returned CONTENT_UNAVAILABLE body is served as a non-delivery: refunded, no lifetime bump, no history. The route never produces that today, but it is pinned.
  - **A CODE-LESS failure** (the <2-products exit) keeps main's exact statement, `raise HTTPException(status_code=400, detail=result.get("error", "Comparison failed"))`. Its body stays byte-identical to origin/main: `400 {success:false, error:"Could not extract both products", code:"BAD_REQUEST"}`. It is pinned, and the pins pass at db1ed3a4.
  - W4-9's allowlist is NOT widened, and `text_routes` is not edited.
  - Mutation-checked both ways: routing the code-less exit through the mapping turns the two <2-products pins red, and dropping the coded branch turns the 503 and CONTENT_UNAVAILABLE pins red.
- **Anon, under `ENABLE_PAID_ROUTE_METERING`.** `refund_anon_comparison_credit(fp, consumed_keys)` fires at most once per request on the six numbered camera exits plus exit 7. It returns the gate's own consumed_keys. It is armed only when the anon gate actually debited and metering is ON. Metering OFF keeps today's anon accounting.

### Decided
- **A failed URL verdict returns 503. This is DECIDED, not open.** The shared text-route mapping is the contract, and it sends LLM_UNAVAILABLE as 503 because a server-side outage is not a client error (W1-3). It is pinned on POST and GET.

  On the shipped client (97b5f15), `parseApiError` turns the 503 into `TIMEOUT`, so the user sees the friendly `home.errors.timeout` copy and never the backend string.
- **The W2-1c check tests truthiness, not presence** (Fable round 3). Two pins cover it:
  - A full verdict carrying `error: null` or `error: ""` is DELIVERED as a 200 success, byte-identical to base.
  - A full verdict carrying a NON-EMPTY `error` is 503 LLM_UNAVAILABLE with the constant message.
- **The "delivered as base" pins build their expectation from a deep copy taken BEFORE the call** (round 4). They never compare against the verdict object the stub hands the code, and the stub's default verdict is itself a fresh deep copy. This makes an in-place edit of the verdict visible. The four in-place mutants that survived round 3 (pop / clear / null-out of a falsy `error`, a fabricated winner) are now killed, and so is an unconditional in-place key add on the success path. Run against the pre-round-4 test file, the same mutants survive; this was measured.
- **W4-9 composition was measured, not assumed.** On main, `generate_comparison`'s catch stores the non-empty constant `COMPARISON_GENERATION_ERROR`, so the truthiness check fires. The tests that drive the REAL catch return 503 LLM_UNAVAILABLE with the constant message, no leak, and one refund under metering.
- **Envelope ON with metering OFF keeps today's accounting. This is ACCEPTED as designed** and pinned by `test_pin_camera_envelope_on_meter_off_keeps_todays_accounting`.

### Flag row (for CLAUDE.md)
`ENABLE_CAMERA_FAILURE_ENVELOPE` defaults to OFF and is read per call in `image_routes.camera_failure_envelope_enabled` (strip/lower; true/1/yes/on).
- **ON:** a `success: False` camera comparison returns `{success: false, action: "comparison_failed", error, code, request_id, products, vision_cost, message[, layer]}` instead of `action: "comparison"`.
- **OFF:** today's body.
- **Flip it TOGETHER with `ENABLE_PAID_ROUTE_METERING`.** That deploy state is pinned on the ledger: the reserved credit is refunded once, the anon credit is refunded once with the gate's keys, there is no lifetime bump, no history row, no anon metering, `log_search(success=False)`, and the full envelope body.

### Activation gate
- The unflagged halves go live on deploy: the camera `str(e)` scrub, the URL failed-verdict fix and the coded-failure URL mapping. The <2-products body does not change.
- Flip `ENABLE_CAMERA_FAILURE_ENVELOPE` and `ENABLE_PAID_ROUTE_METERING` together, after checking that the shipped client renders `comparison_failed` for a TIMEOUT.
- The adversary's other metering preconditions still stand: the size_or_count 500 window, the strict-auth coupling on /url/compare, and the 429 note on the admin probe.

### Records (pinned, not built)
- **/url/compare has NO anonymous gate.** With ENABLE_ANON_USAGE_GATE and metering both ON, a caller with a valid fingerprint and no auth gets 200 with zero anon checks. This is a follow-up for issue #128.
- **The anon credit on /image/identify is debited BEFORE image validation.** The five pre-validation 400s and the moderation-exception re-raise do not refund it. These are follow-ups for #128.
- **The refund latches need no pin** (ruling 5). The anon refund's `not device_fp` guard is redundant and is kept as a defensive check.

### Verification (on the rebased tree, base = origin/main db1ed3a4)
- **Unit files** (`tests/test_retro_w2_1.py` + `tests/test_paid_route_metering.py`): 132 passed in each of six ambient flag states (none; METER; ENVELOPE; ANON_GATE; METER+ENVELOPE; all three), on the pinned CI venv, with a process-wide non-loopback socket guard.
- **Test labels** were checked against db1ed3a4 with 0 mislabelled across 111 nodes: 27 RED fail, 44 BASE PIN / RECORD pass, 40 GREEN PIN fail.
- **Round-4 mutants: 9, with 8 killed.**
  - Both url_routes branches are killed (see Fix).
  - All four round-3 in-place survivors and the success-path in-place mutant are killed.
  - The one survivor turns the code-less detail into a structured `{code: BAD_REQUEST, error}`, which the error handler lifts to the identical envelope. It is wire-equivalent.
- **Earlier rounds:** 75 mutants, 67 killed. The 7 survivors are benign: two refund latches, the redundant device_fp guard, a log variant equivalent under the scrub, a server-side-only log, and two str-only truthiness variants.
- **Comm gate** over the 17 test files that reach these modules, run sequentially with the socket guard: base db1ed3a4 and HEAD both gave 4 failed and 393 passed, with identical failed ids (the three #89 `TestIdentifyProductsMocked` nodes, plus `test_detect_allows_valid_url`, which needs DNS and fails under the guard on both sides). No new failures.

### Follow-ups (adversary minors not addressed here)
- size_or_count numeric -> AttributeError -> 500 with the credit kept (round-0 defect 4).
- Unflagged `Depends(get_optional_user)` on /url/compare and its strict-auth coupling (defect 5).
- The shared 429 bucket on the admin prices probe (defect 6).
- The /text/parse bare-dict mock, M4 (defect 7).
- The authed refunds drop `consumed_keys` (defect 8).
- CLAUDE.md drift, plus the camera category and camera memory items (defect 9).
- The /url/compare anon gate and the anon refunds on the validation 400s and moderation exception, for #128.
- Add the new flag row to CLAUDE.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

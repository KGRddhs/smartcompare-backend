Incident 2026-11-11, fact F3 (the code still sends every compare, scan and link comparison to OpenAI, which refuses it with HTTP 401); the main lane's RB2-14 / IT26-7 ("S81-12d OPENAI-DISPATCH-OFF"). Class FOCUS (the privacy text will rest on it): two adversaries.

Status wording (the owner's proof standard): when merged this unit is **merged, NOT yet proven**. Green suites are necessary and are not the proof; the PROOF ON THE PHONE section below decides. Nothing in this PR says a production problem is fixed.

## What the flag does

`ENABLE_OPENAI_EGRESS_STOP` (ONE new dark flag, default OFF, read PER CALL with the house idiom as the first statement of `api_budget_service.stop_openai_egress_if_enabled(surface)`; only `true` / `1` / `yes` / `on` after strip and lower are ON). ON, every call that would go to OpenAI fails LOCALLY, before any network activity, with the new typed refusal `OpenAIEgressStoppedError` (a subclass of `LLMUnavailableError`, with no subclass of its own):

- H1 `guarded_llm_create` (all 15 routed sites): after the store=False privacy prologue and BEFORE the spend admit, the W1-3 admission, the dispatch, MON1's credential-health notes and every record (R-12D-5).
- H2 `content_safety_service.moderate_output`: after the Claude branch, inside the try; the arm fails OPEN exactly as on today's 401 (R-12D-8).
- H3 / H4 the two operator scripts that call OpenAI directly (`scripts/seed_spec_spine.py`, `scripts/shadow_experiments.py`; only where the flag is set in the operator's shell).
- H5 (gate GC-5) MON1's active check `llm_credential_probe._metadata_call`: the first statement of its openai branch raises the stop class (by module attribute, not through the stop helper; no log line).
- J-3: the two role-ON re-raise arms (the verdict arm of `extraction_service.generate_comparison`, the url_extract arm of `url_extraction_service.extract_with_ai`) each gain ONE operand `and not isinstance(e, _llm_breaker.OpenAIEgressStoppedError)`: a stop falls to the arm's existing S81-04c WARNING and the base return in EVERY flag configuration; every other `LLMUnavailableError` (consent refusal, Anthropic failure, breaker or spend denial) is re-raised exactly as today.
- K-2 (3.11): with the stop ON, OpenAI is not counted as in use by the credential alarm: `llm_credential_health.providers_in_use()` leaves openai out (a function-local import, the predicate read by module attribute), so the active check never calls OpenAI and `/health/llm` is not held at its 503 by a stale openai state; the last recorded state is kept, not erased.
- One WARNING `[OPENAI_EGRESS] dispatch stopped locally surface=<chat_completions|moderations|script>` per process per surface; never ERROR, never a Sentry event (R-12D-7).

Delivery with ON: under the stop every entry delivers, in every flag configuration, what it delivers today with the rejected credential in that same configuration, except the camera's coded 503 `LLM_UNAVAILABLE` (both refunds kept) instead of today's 500 `SERVER_ERROR` (the ruled exception R-12D-3; both live bundles render either as the engine-unavailable state). OFF: byte-identical (one getenv per dispatch attempt, one call frame per hook and, in the moderation arm, the scripts and the probe, one inline import; `providers_in_use()` adds one inline import and, while `OPENAI_API_KEY` is set, one getenv per GET /health/llm and per probe pass), pinned with the FULL configuration and the transport and call recorders.

Not touched: the router, the consent decision, `ENABLE_OPENAI_PRE_V3`, `OPENAI_API_KEY`, every route, client, migration, legal text and processors.json row.

## Files (ONE commit)

app/services/api_budget_service.py (the flag block, H1, the docstring sentence, one census-comment line); app/services/content_safety_service.py (H2); scripts/seed_spec_spine.py (H3); scripts/shadow_experiments.py (H4); app/services/extraction_service.py + app/services/url_extraction_service.py (ONE operand each); app/services/llm_credential_health.py (the in-use exclusion); app/services/llm_credential_probe.py (H5); tests/test_s81_s03_llm_ledger_v2.py (E1 only); CLAUDE.md (this unit's block after the newest block in merge order, S81-07's; the Feature Flags pointer sentence after the newest sentence, S81-07's; MON1's heading date 2026-11-xx -> 2026-11-12); the two frozen RED files (file A amended twice on the replay onto c6ebbd2e, RP-2 and RP-7, see below); the NEW gate-rows file tests/test_s81_s12d_gate_rows.py. Base: main c6ebbd2e.


## Defect / ruling ids -> test nodes -> flag -> precondition

File A = tests/test_s81_s12d_openai_egress_stop.py, file B = tests/test_s81_s12d_no_byte_e2e.py, G = tests/test_s81_s12d_gate_rows.py. Flag of every row: `ENABLE_OPENAI_EGRESS_STOP`. Precondition of every ON row in production: the web deployment contains this merge (owner step 0).

| Id | What | Nodes |
|---|---|---|
| F3 / R-12D-2 NO BYTE | zero OpenAI requests per entry, site and script | A::test_s12d_03, ::test_s12d_14 (16 sites), ::test_s12d_18, ::test_s12d_20 (the census; amended by RP-2 on the replay); B::test_e01_e02, ::test_e03, ::test_e05, ::test_e06, ::test_e07, ::test_e09 |
| R-12D-3 today's delivery (+ the camera 503) | ON answer == the stop-OFF / 401 answer, normalised | A::test_s12d_14, ::test_s12d_16 (8 S81-04c arms); B::test_e01_e02 .. ::test_e07, ::test_e04 (503 LLM_UNAVAILABLE, same refund) |
| J-3 / J-5 the two re-raise arms | a stop never becomes a role-ON non-delivery; other class members still re-raised | A::test_s12d_21, ::test_s12d_22; B::test_e10, ::test_e11, ::test_e12 |
| R-12D-4 not by other switches | Claude-routed calls untouched; pre-v3 lands on the stop | A::test_s12d_07, ::test_s12d_08, ::test_s12d_09 |
| R-12D-5 order | the stop precedes the spend admit, the W1-3 admission, every record | A::test_s12d_03, ::test_s12d_04, ::test_s12d_05 |
| R-12D-6 / K-2 / K-3 MON1 contract | no credential outcome from a stop; openai not in use; probe sends nothing | A::test_mc_1 .. ::test_mc_4; G::test_g1, ::test_g1b (H5) |
| R-12D-7 logging | one WARNING per process per surface; no ERROR, no Sentry | A::test_s12d_10, ::test_s12d_11 |
| R-12D-8 moderation | not made; fails open | A::test_s12d_06, ::test_s12d_13 |
| reader / class | house idiom per call; class, message, surfaces | A::test_s12d_01, ::test_s12d_02, ::test_s12d_15, ::test_s12d_17 |
| flag-OFF identity (PIN) | byte identity with the FULL configuration (D-2) | A::test_s12d_12, ::test_s12d_13, ::test_s12d_19; B::test_e08 (12 entries x unset / "false" / " garbage ") |

Counts: 31 RED rows + 7 PIN rows in the frozen files (62 RED nodes failing at base on an AssertionError only, 62 PIN nodes green at base); gate rows G1 (2 nodes: stop_on, stop_off_pin_half) and G1b (1 node). Mutation table: 32 mutants of the RED round ALL KILLED (M01-M29, MM-1..3), M-D9 the ruled-equivalent survivor (D-9); the gate-row mutants GM-1 (H5 removed: G1[stop_on] + G1b), GM-2 (H5 moved after the client build: G1b), GM-3 (H5 routed through the stop helper: G1b) all KILLED on an AssertionError.

## Deliberate pin changes (E-rows)

| E | File | Before | After | Reason |
|---|---|---|---|---|
| E1 | tests/test_s81_s03_llm_ledger_v2.py `K1_GUARDED_AST_SHA` (read by test_k1_guarded_llm_create_untouched) | `372cee1c8...` (MON1's re-pin) | `d93d6b0a0...` measured on the GREEN bytes (CPython 3.12.9), split in two fragments, no 8-digit run | H1 + the docstring sentence change guarded_llm_create by design (R-12D-2); the row's purpose (no unreviewed chokepoint edit) is served by re-pinning to the reviewed bytes |

No other pin moved (measured on the prototype and again at GREEN: the S81-04c arm rows, the S81-06 router rows, every MON1 row incl. G01 GATING_AST_B64 / L01 / Y01, U3c, S81-04 R37, M1 / M5, U8d R8).

## Gates at the head (d0a1fd70 on main c6ebbd2e; every pytest through the lane's gate wrapper, one at a time)

| Gate | Result |
|---|---|
| py_compile + ruff E9,F63,F7,F82 on the 9 edited and 3 unit files | clean; the hook's black check on the two allowlisted files (llm_credential_health.py, llm_credential_probe.py) clean |
| the unit files with the flag unset, and again with it exported ON (127 nodes; the ON run proves the rows are hermetic to an ambient flag, since every row sets the flag itself) | 127 / 127 passed each |
| the pins (GREEN's 24 files plus the source-scanning pins of spec 7.2, 31 files) | 2,084 passed |
| the CI-order set in both orders (GC-10) | 1,594 passed; 293 passed |
| the whole-tree head pass (RP-3): 567 files re-used from the recorded old-head chunks (their failures equal the 27 ids of the base record exactly); 210 files re-run at c6ebbd2e in 9 chunks (every file of those chunks that reads CLAUDE.md, walks a directory, shells out to git or names the S81-07 harness, its fixtures or the env-safety lists; the never-run remainder; the new S81-07 test file) | head-only failures against the base record: NONE. `test_s81_s07_meas_harness.py::test_r35_fixtures` fails at base c6ebbd2e too (its fixture JSON is checked out with CRLF here): a local-environment row like the other 27 |
| the full jest suite once (GC-14) | 4,039 passed, 13 skipped, 13 todo, 4 failed = the four accepted `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5); the thirteen other backend-scanning client fences pass |
| mutation | the RED round's 32 mutants were all killed on its prototype (M-D9 the ruled survivor); on the committed bytes the correctness adversary re-applied 26 of them plus GM-1, all killed on an AssertionError; the gate-row mutants GM-1 to GM-3 killed at GREEN; the four RP-2 census mutants killed |

## The replay onto c6ebbd2e (RULINGS_REPLAY_S81_12D)

- The GREEN implementation was finished but uncommitted on 445f8de3 when main moved to c6ebbd2e (#402, S81-07 MEAS-CLAUDE-GATE). It was moved with no stash and no commit at the old base: a fast-forward of the branch, then CLAUDE.md re-composed as c6ebbd2e's file plus the unit's three edits. `git patch-id --stable` of the code diff is unchanged (67705672...).
- RP-2: the frozen census row (`test_s12d_20`) counted `scripts/meas_claude_gate.py::_attempt` (S81-07's capability check, `models.retrieve` on the harness's own AsyncAnthropic client) as an OpenAI dispatch. The row now counts it, exempts it by name, and asserts that the file builds exactly one SDK client (AsyncAnthropic) and names no openai module; four mutants (an AsyncOpenAI constructor, an `import openai`, an importlib "openai" string, a second retrieve) are killed.
- RP-7: the head pass found that file A's FULL-configuration rows left the spend breaker's process state set, so `tests/test_s81_s24_auth_throttle.py::test_p73_hop_probe_off_silent` (an exact `/health` key set) failed all 12 nodes when it ran after file A in one process, as it does in CI. File A's autouse fixture now drops the breaker state before and after every row, as `test_s81_s04_spend_breaker.py` does; no assertion changed. Measured after the fix: the three unit files then test_s81_s24 in CI order pass every p73 node.
- File A's frozen sha256 (after RP-2 and RP-7) is now 85f89380dc40abba668ba31ba72b845e44304bed562986df5ec99f4cd4bf30e9 (was 817530e2...); file B is unchanged (e563bc1d...); the gate-rows file cb643f7a....

## Adversaries (two, in parallel, Opus 5.5, on d0a1fd70): both SOUND

- correctness: SOUND, no blocking, no major. Unit files OFF and ON 127 / 127; file B's 12 E08 digests re-measured from the exact bytes, all equal; 26 RED-table mutants plus GM-1 re-applied by hand on the committed bytes, all killed; J-3 by run over all eight LLMUnavailableError family classes (only the stop class takes the base return); MC-1 to MC-4 against MON1's real modules, and the moderation arm's note_failure with the stop class moves no credential state, sends no alert and leaves /health/llm unchanged; RP-2 and RP-7 confirmed by run; the CLAUDE.md union checked claim by claim.
- privacy-and-egress: SOUND, no blocking, no major. An AST scan of app/ and scripts/ found exactly the census set; with OPENAI_BASE_URL pointed elsewhere every site is stopped too; no Anthropic-to-OpenAI fallback (all roles ON with every Claude dispatch failing: zero OpenAI requests); 21 extra flag-mix pairs (pre-v3, staged text, all roles) x text, stream, link, parse, warmer and camera: ON sent zero requests and delivered what OFF delivers; the stop precedes the spend admit, the W1-3 admission and every MON1 hook; zero ERROR records and zero capture calls from a stop (the OFF / 401 text compare logs 9); the stop line carries only the surface word; both camera refunds hold; flag-OFF identity holds.
- Their minors are folded in above as wording fixes and the stated limits L4, L7, L11, L12 and the last two bullets of the stated limits (the leaner chain: SOUND + minors = the PR).


## PROOF ON THE PHONE (after the flip; by the relay with the owner; needs no AI text)

The flip changes NO screen (measured by code reading of both live bundles 683f56c0 and f1e20c39: SmartCompareApp/src/services/failureClassification.ts already maps today's camera 500 SERVER_ERROR and the coded 503 to the same engine-unavailable state). The visible change is in the deploy log, Railway's HTTP log and Sentry. The detector: httpx2 logs every SDK request at INFO (`HTTP Request: POST https://api.openai.com/... 401`), and app/middleware/logging_config.py does not quiet httpx2, so the zero-lines check means something only while the log level is INFO.

| Step | The owner does | Must be visible | Backing check (the relay) |
|---|---|---|---|
| P0 positive control (REQUIRED, before the flip) | one text comparison of a golden pair (e.g. Aventus vs Layton) | today's result (scores, prices, no AI text) | the deploy log shows the 401 request lines to the OpenAI host for those minutes; without this read the after-read proves nothing |
| P1 | the same text comparison after the flip | the result looks as before the flip | ZERO `HTTP Request: POST https://api.openai.com` lines for those minutes; the arms' `<prefix>: OpenAIEgressStoppedError` WARNINGs and the moderation WARNING carrying the constant message; the once-per-process `[OPENAI_EGRESS] ... surface=chat_completions` and `... surface=moderations` lines SINCE THE DEPLOYMENT STARTED (an earlier user compare may have emitted them); no new Sentry "Specs extraction error" / "Comparison generation error" events |
| P2 | one camera scan of two bottles | the screen stays the engine-unavailable state | 503 (today 500) in Railway's HTTP log for POST /api/v1/image/identify (the app writes no access line); in the deploy log the WARNING `[IMAGE] Vision call failed: OpenAIEgressStoppedError` (today an ERROR with the 401 text); the scan is not charged (refund); no new Sentry event |
| P3 | one link comparison of two product links | the same AI-engine-unavailable message as before the flip | 503 LLM_UNAVAILABLE as before; ZERO OpenAI request lines; the refund as before |
| P4 (non-regression read, NOT evidence of the stop) | - | - | the saved rows of P1 keep zero OpenAI calls and zero cost, as today |
| P5 | - | - | the dated ledger line (service, deployment commit, time, ON) |

What is NOT provable in production: the absence of packets (the deploy log shows the absence of SDK request lines, not of bytes; the hermetic transport rows are the only per-byte measure and are necessary, never the proof); OpenAI's side; that no operator runs a script without the flag in its shell.

## Owner steps (names only; a dated ledger line per step; nobody but the owner decides)

None to merge. (0) Before the flip the relay confirms, read-only, that the running WEB deployment's commit contains the S81-12d merge, and that no Railway service deploys from the legacy `backend/` tree (names only; see L12). (1) The positive control P0. (2) `ENABLE_OPENAI_EGRESS_STOP` is set ON on the web service by the relay on the owner's yes, in its own window (a variable change redeploys web; no other proof runs in that window). (3) The proof above. (4) The dated ledger line: the service name, its deployment commit, the time, "ON": that date is the one a legal text may carry for "our services stopped sending requests to OpenAI" (never "the code": the operator scripts stop only where the flag is in the shell). (5) price-warmer: the same variable may be set there in the same window and the line then records that service's deployment commit. STANDING PRECONDITION on the `ENABLE_PRICE_CACHE_WARMER` flip: the warmer is not switched on until the price-warmer deployment contains the S81-12d merge AND the stop is set there (a merge to main does not redeploy that service; a variable on an older deployment does nothing).


## Stated limits

- L2 The str(e) of four internal failure values (specs, price, price_training, url_extract) reads the stop constant instead of the SDK's 401 text under ON; none reaches a response body on the phone path; the pair rows normalise exactly these texts and fail on any other difference.
- L3 The once-per-process latch is NOT locked and stays so: the add precedes the log line and nothing awaits between the membership test and the add, so on an event loop it cannot log twice; only a caller on several OS threads could log one extra line per surface, and no such caller exists at the base. A lock's effect could not be pinned by a deterministic row.
- L4 `OPENAI_API_KEY` must STAY SET. With it unset, `app/services/openai_service.py` raises at import (its module-level `AsyncOpenAI(...)` client), so `app.main` cannot import and the web service does NOT START (pre-existing behaviour, measured by the privacy adversary). Removing the credential is never the way to stop OpenAI; this flag is (R-12D-4).
- L5 The stop is host-blind: an `OPENAI_BASE_URL` override is stopped too (the flag means "no request through the OpenAI SDK").
- L6 Not stopped: Claude traffic (by design), the judge and KB-seed batch services (anthropic SDK), every non-LLM outbound call.
- L7 The two operator scripts that call OpenAI directly stop only when the flag is in the shell that runs them; the operator scripts that run through the chokepoint (measure_warmed_kpi, warm_kpi_truth, seed_zyte_luxury) stop the same way. The S81-07 measurement harness drops every ENABLE_* name at its start, so the stop never applies in that process; it reaches no OpenAI host anyway (its own guard admits only api.anthropic.com).
- L8 Nothing on /health names the stop itself; with the stop ON OpenAI is not counted as in use by the credential alarm (its last recorded state stays visible in `/health` `llm_credential`).
- L9 Moderation: with the stop ON the OpenAI moderation call is not made and the arm fails OPEN, exactly as today on the rejected credential; AI text is therefore unmoderated by a provider until the Claude moderation role is ON (the main lane's window 14). The stop does not make this worse than today.
- L10 `scripts/audit_exemplar_token_cost.py` imports tiktoken, which can download a public encoding file from an OpenAI-operated host on first use; operator-run only, no user content, not an API request: outside the stop. The census row pins that no module under app/ imports tiktoken.
- The e2e flag-OFF identity rows (E08) freeze per entry the status, the per-path request counts and a base64 sha256 of the normalised body; the lists under `metadata.source_trace` are compared order-free (their order was measured flipping between two runs of one process): that order is not pinned.
- File B imports helpers (not tests, not fixtures) from file A; the gate-rows file does the same.
- The flag must NEVER be exported ambient for a whole-tree or CI run: measured at RED, with it ON 255 nodes of other files fail because they assert OpenAI traffic (CI never exports it; the unit files are hermetic to it).
- The CLAUDE.md MON1 block still says openai is in use while `OPENAI_API_KEY` is set "(no flag moves it out)"; this unit's block states the exception. (Left in place: the gate's CLAUDE.md footprint names only the heading date of MON1's block.)
- L11 The census row (test_s12d_20) counts dispatches by their callee-chain suffix: it would not see the `.with_raw_response` / `.with_streaming_response` / `.parse` / `.stream` helpers, the legacy `completions.create`, a generic `client.post` or raw HTTP to the provider base URL (none exists at this head: an AST scan of every OpenAI-resource-named call found exactly the census set). The RP-2 exemption of S81-07's `_attempt` checks that file's client constructors and openai module names, not the receiver of that one call: a receiver swap to an app getter would pass the row (mutants MP1 / RP2e / RP2f survive), while the harness's host guard would still refuse the OpenAI host.
- L12 The legacy `backend/` tree (its own railway.json and Procfile, five modules that import openai) is outside the census and the stop; CLAUDE.md says it is NOT deployed. The legal sentence rests on that, so owner step 0 includes a read-only check that no Railway service deploys from it.
- File B's E10 docstring promises no ERROR record from a stop but asserts only the patched Sentry capture calls; the claim was measured true at Logger.callHandlers by the privacy adversary and is pinned at unit level (S12D-11, -16, -21).
- Wording carried to the next CLAUDE.md touch: the K1 comment of tests/test_s81_s03_llm_ledger_v2.py still names MON1 as the last re-recorder (this unit re-pinned it, E1); the unit block's L4 and OFF-delta sentences are shorter than this body's; MON1's block line above.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

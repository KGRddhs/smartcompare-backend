# fix(monitoring): MON1 LLM-CREDENTIAL-HEALTH: an operator signal for a dead LLM credential (passive part unflagged, active probe dark)

Incident 2026-11-11, root cause 2 "no alarm" (incident fix S7; DEFECT_LEDGER row MON1). The production OpenAI credential was rejected (HTTP 401) for 8+ days and nothing told the owner: the chokepoint records nothing an operator sees for a 401 (correct for gating, wrong for alerting), `/health` carries no LLM or Serper state, and the per-call ERROR records became 48 untagged Sentry events with nothing to hang a rule on.

Status wording (the owner's proof standard): when merged this unit is **merged, NOT yet proven**. Green suites are necessary and are not the proof; the PROOF ON THE PHONE section below decides. It does not merge before the owner answers O2 and O3 and the relay opens a merge window (the merge freeze of addendum A2-2).

## What it does

- **Recorder** (`app/services/llm_credential_health.py`, a new stdlib leaf): per provider (openai, anthropic) the credential state ok / rejected / quota, by exception class + `status_code` + the SDK's structured `code` / `type`, never message text. `quota` = openai 429 with one of the five structured codes of R-MON1-16 or type insufficient_quota; anthropic type billing_error. A timeout, 5xx, plain 429 or 400 changes nothing.
- **Hooks** (exception-transparent: the same exception object re-raised, no await, no I/O): both branches and both success tails of `api_budget_service.guarded_llm_create`; the except arm and success tail of `llm_router.guarded_anthropic_create` (incl. the Claude moderation site); the OpenAI moderation call in `content_safety_service.moderate_output`. Gating is byte-identical (G01 AST digests of the ten gating functions; G02: ten 401s are each admitted and never open the breaker).
- **Alert event** (`sentry_service.capture_credential_alert`): ONE message `credential_state`, level error (info for a recovery), tags `alert=llm_credential`, `provider`, `state`, `status`, fingerprint [alert, provider, state], emitted in a scope with no request region (R-MON1-20; the private `_event_processors` recipe measured on sentry-sdk 2.68.1, SE04; fail-safe GC-5: any failure of the recipe still sends exactly one event and logs one constant WARNING, gate row G1). One event per state CHANGE, at most one per (provider, state) per 900 s (R-MON1-21), a FIXED window measured from the last event actually emitted (fix round 1, F1-2; G10). A change the cool-down suppresses logs `[LLM_CREDENTIAL] alert suppressed provider=%s state=%s cooldown_s=%d` (G2) and is never lost (F1-1): it is held pending, the first outcome that confirms the held state after the window (a failure of the same class while rejected or quota; a served call while ok) emits it once, and a change out of that state drops it without an event, so the newest event always agrees with the held state (G11, G12). No new log line. `alert=serper_keys` fires once when every Serper key is found exhausted.
- **`/health`**: two additive entries, present only after an outcome in this process: `llm_credential` {provider: {state, last_status, at, source, count}} and `serper_keys` {configured, marked_exhausted, none_left, at} (counts only, never a key or prefix). `status`, `message`, the 200 and every existing entry are unchanged.
- **Monitor path `GET /health/llm`** (public, GET only, not in the schema, limiter-exempt, no I/O): 503 `LLM_CREDENTIAL_UNUSABLE` while an in-use provider is rejected or quota; with the probe ON, 503 `LLM_CREDENTIAL_UNKNOWN` while an in-use provider has no outcome after 120 s of uptime (R-MON1-22); else 200. Never a codeless 503.
- **Active probe (DARK)**: `ENABLE_LLM_CREDENTIAL_PROBE` (default OFF, read as the FIRST statement of `tick()`, R-MON1-19) + `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` (default 900, floor 300). A lifespan task (cancelled before the drain); ON: one `models.retrieve` per in-use provider per interval (no tokens, 5 s, no retry), first 20 s after start; no spend admit, no ledger record. A probe 401 rejects only with the structured invalid-credential signal (R-MON1-18) and a probe success never clears quota or a dispatch 403 (R-MON1-17). A moderation success (the OpenAI moderation call or the Claude moderation site) proves authentication only in the same way (F1-3, G13, G14): it clears a `rejected` that carried a 401 or was raised by moderation itself, never a quota state and never a dispatch 403, and so emits no recovery event while one is held; its record still runs only after the awaited call returns. A served dispatch (a real chat or message call) clears any state, as before.

## The deploy-visible delta (flag OFF = production), each unflagged part behind its ruling

| Part | Ships | Ruling |
|---|---|---|
| Recorder + hooks (one lock + one dict write per LLM outcome; one try frame around the production create) | unflagged | R-MON1-1 (a) |
| One Sentry event per credential state change (cool-down 900 s per provider and state); one `serper_keys` event when no Serper key is left | unflagged | R-MON1-1 (a), R-MON1-6, R-MON1-21 |
| `/health` entries `llm_credential`, `serper_keys` (absent until an outcome) | unflagged | R-MON1-7 |
| `GET /health/llm` | unflagged, **owner ruling O2 OPEN** (default IN) | R-MON1-8, R-MON1-22 |
| WARNING `[LLM_CREDENTIAL] ...` per state change; WARNING / INFO `[SERPER_KEYS] ...` on the none-left transitions | unflagged (log-only) | R-MON1-1 (a) |
| One idle lifespan task (wakes 20 s after start, then every 900 s, reads two env names; OFF builds no client) | the task always; its work DARK | R-MON1-9, R-MON1-19 |
| The probe's outbound GET /v1/models/{model} | DARK, its own window, **owner ruling O3 OPEN** | R-MON1-1 (b) |

Compare / camera / URL response bodies, stream frames, stored rows, breakers, admissions, the spend breaker and every client-read key are unchanged.

## Provider-neutral (A1-3)

The same recorder, event, `/health` entry and monitor path cover the Anthropic credential through the hooks on `guarded_anthropic_create` (rows H07, H08, H09, P07, P16, gate row G4). "In use", as implemented: openai while `OPENAI_API_KEY` is set (no flag moves it out); anthropic while `ANTHROPIC_API_KEY` is set AND an `ENABLE_ANTHROPIC_*` role flag is ON (`llm_router.any_role_enabled`). After the text roles move to Claude, OpenAI is still called by the OpenAI moderation call (until `ENABLE_ANTHROPIC_MODERATION`), the camera path (until `ENABLE_ANTHROPIC_VISION`) and the pre-v3 route (`ENABLE_OPENAI_PRE_V3` for clients below consent 3), so OpenAI stays "in use" while its key is set; the state is per provider (A2-3), so a held OpenAI rejection stays quiet while an Anthropic rejection still alarms (G4). Removing OpenAI from "in use" = unsetting `OPENAI_API_KEY` on web (an owner step, after its last caller flips). In plain words: the monitor path `GET /health/llm` stays degraded (503) for OpenAI until that variable is removed after OpenAI's last caller has moved (stated limit A2-4 / MON1c below).

## PROOF ON THE PHONE (spec 8b as amended by R-MON1-22, R-MON1-24, R-MON1-26, A1-1, A1-2)

The owner declined a bridge OpenAI credential ("No, wait for Claude"), so the steady state for the coming days is `rejected` on OpenAI. Nothing below needs AI text. What the owner sees until the Claude switch: ONE alert event at the first comparison after each deploy or restart; `/health` showing `llm_credential.openai.state = rejected` (last_status 401) from that comparison on; `GET /health/llm` answering its coded 503 from then on (so no uptime monitor is pointed at it before the switch); no further event while the state does not change.

| # | Repeat (run by the relay with the owner) | What must be visible | Backing check |
|---|---|---|---|
| PP1 | After the deploy, ONE comparison on the phone (e.g. Creed Aventus EDP vs Parfums de Marly Layton EDP), then one GET of production `/health` | `llm_credential.openai` with state `rejected`, last_status 401, source dispatch; `serper_keys` appears ONLY if production holds two or more Serper keys and that comparison made a multi-key selection (then configured >= 2; otherwise its absence is expected) | the deploy log has exactly ONE `[LLM_CREDENTIAL] provider=openai state=rejected status=401 source=dispatch` line for that comparison; Sentry shows ONE `credential_state` event tagged alert=llm_credential provider=openai state=rejected status=401 with no request region |
| PP2 | The owner's Sentry rule (owner step 1) | the notification of PP1's event arrives on the owner's phone | the rule: "an event is seen", filter tag `alert` = `llm_credential`, action interval 24 hours |
| PP3 | A redeploy (or restart) while the credential is still rejected, then one comparison | the SAME Sentry issue (fingerprint llm_credential / openai / rejected) gains ONE event: its event count rises by one and its "last seen" moves to that comparison. A second NOTIFICATION arrives only if 24 hours have passed since the previous one (the rule's action interval, A1-2); inside 24 h no second notification is expected and its absence is not a failure | a second L1 line `[LLM_CREDENTIAL] provider=openai state=rejected status=401 source=dispatch` in the new deployment's log |
| PP4 | Optional manual trigger (R-MON1-26): owner step 4, once | one `credential_state` event with state `test` (level error) and its notification | the event in the same issue family, tag state=test |
| PP5 | After the Claude switch (the first Claude text role live; the OpenAI credential stays rejected): one comparison | `/health` `llm_credential.anthropic.state = ok`; no Anthropic alert event | marked "after the Claude switch" (A1-1) |
| PP6 | After the probe's window (O3; owner step 3): a redeploy, NO comparison, wait 60 s, GET `/health` | `llm_credential.<provider>` present with source `probe` | one `[LLM_PROBE] provider=... outcome=...` INFO line per provider per interval; zero `[LLM_PROBE] tick failed`; no added token spend in the console |

Measured before (2026-11-11): production `/health` carries neither key; the 401s were per-call WARNING / ERROR records (48 untagged events since 2026-10-31); no monitor path. A hermetic measurement (fake clients raising the real SDK classes) is not this proof.

## Defect ids -> RED node ids

| Defect (MON1, incident root cause 2) | Rows (tests/test_inc_mon1_credential_health.py unless named) |
|---|---|
| D1 a 401 / 403 / out-of-credit answer records nothing an operator sees | L01-L07, L10, H01-H10 (incl. the R-MON1-16 quota-code and type-only cases of L02) |
| D2 no single alertable event; once per process would mute a second outage | L08, L09, L11, L12, SE01-SE05, T01; gate rows G1, G2, G3 (tests/test_inc_mon1_gate_rows.py) |
| D3 `/health` carries no LLM or Serper state | HE01-HE05, G03, S01-S05 |
| D4 no monitor path an uptime check can read | M01-M07 |
| D5 a dead credential is seen only with user traffic (about two compares a week) | tests/test_inc_mon1_probe.py P01-P16 |
| Gating unchanged (R-MON1-2) | G01, G02 (PIN) |
| Per-provider independence (A2-3) | gate row G4 |
| Fix round 1: GC-13 named checks pinned (monitor fail-open, shutdown cancel + await, one event after a raising scope exit, the closed-set guard, snapshot copies) | gate rows G5, G6, G7, G8, G9 |
| Fix round 1: F1-2 fixed cool-down window; F1-1 a suppressed transition is never lost | gate rows G10, G11 (two rows), G12 |
| Fix round 1: F1-3 a moderation success proves authentication only | gate rows G13, G14 |

Mutants: 36 killed on the RED prototype (GATE_MON1 GC-3); the four gate rows each killed by a named mutant on the GREEN bytes (MG1 fallback send removed -> G1; MG2 suppressed WARNING removed -> G2; MG3 level info for `test` -> G3; MG4 cool-down keyed on the state alone -> G4). Fix round 1, each on sha-verified byte copies with a sha-verified restore: at HEAD c6592b53 the pins G5-G10 and G14 were each killed by the adversaries' surviving mutant (A09 and A09b -> G5; A17b and AM17 -> G6; A15 -> G7; AM18 -> G8; AM22 -> G9; AM08 -> G10; A16 -> G14); on the fix bytes eight mutants were killed (pending mark removed -> G11/G12; pending emitted without waiting -> G11; sliding window -> G10; moderation success clears quota -> G13; moderation success clears a dispatch 403 -> G13; note_success moved above the moderation call -> G14; mark survives a transition out -> G11 transition-out row; two events for one mark -> G11).

## Deliberate pin changes (spec 4.1, GATE_MON1 GC-4)

| E | File | Change | Why |
|---|---|---|---|
| E1 | tests/test_s81_s03_llm_ledger_v2.py `K1_GUARDED_AST_SHA` (+ the test_k1 docstring) | re-recorded to the AST digest of `guarded_llm_create` with the H1-H4 hooks (two-piece literal, no 8-digit run; the name has no scanner keyword) | H1-H4 edit that function body by ruling (R-MON1-5); the S81-04 precedent |
| E2 | tests/test_s81_s04_spend_breaker.py::test_p05_flag_off_health_has_no_spend_key | the allowed key set widened by exactly `llm_credential` and `serper_keys`; its subject (no spend key with the flag off) and every other assertion unchanged; no recorder reset inside the test | its served dispatch records the OpenAI outcome (found by the RED prototype) |

## Gates of fix round 1 (fix HEAD 95f50119 on c6592b53; not production proof)

- RED step at c6592b53 (gate rows appended, code unchanged): `[pyt] tag=inc-mon1-fix1-red ... elapsed=7s bound=600s status=FAIL rc=1` (3 failed on AssertionError: G11, G12, G13; 13 passed). G10, the G11 transition-out row and G14 pin parts of F1-1 / F1-2 / F1-3 the base bytes already had; each, and each of G5-G9, was killed by its named mutant at c6592b53 (nine runs, `inc-mon1-fix1-red-<id>`, 4 s each, all KILLED on AssertionError).
- Unit files + gate rows (146 nodes): `[pyt] tag=inc-mon1-fix1-unit-on ... elapsed=27s bound=600s status=OK rc=0` (ENABLE_LLM_CREDENTIAL_PROBE=true, 146 passed); `[pyt] tag=inc-mon1-fix1-unit-off ... elapsed=27s bound=600s status=OK rc=0` (=false, 146 passed).
- Fix mutants (eight, `inc-mon1-fix1-green-<id>`, all KILLED on AssertionError; every restore sha256-verified).
- CI-order set (GC-11, plus tests/test_sentry_service.py and tests/test_sentry_503_suppression.py): `[pyt] tag=inc-mon1-fix1-ciorder ... elapsed=87s bound=1200s status=FAIL rc=1` (1533 passed; the two base CRLF rows of tests/test_s81_s24_auth_throttle.py, GC-2).
- Comm chunks (the 69 test files that name llm_credential_health, content_safety_service, sentry_service or /health, plus the gate-rows file; 3 chunks): `inc-mon1-fix1-comm-00` OK (2004 passed), `-01` OK (2498 passed), `-02` FAIL rc=1 (2559 passed, 3 failed: test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content and the two s24 CRLF rows, all in the base record 23f5330f). branch-only-NEW = EMPTY.
- ruff (E9,F63,F7,F82; F401,F811,F841) and py_compile clean on the two changed python files; black 26.5.1 clean on the 34 ratchet files; added lines pure ASCII. The client jest fences were not re-run: no literal they read moves.

## Gates and comm set (GREEN, base a74caba7, branch HEAD c6592b53; not production proof)

- RED files + gate rows (135 nodes): `[pyt] tag=inc-mon1-green-red-on2 ... elapsed=31s bound=600s status=OK rc=0` (ENABLE_LLM_CREDENTIAL_PROBE=true, 135 passed); `[pyt] tag=inc-mon1-green-red-off ... elapsed=47s bound=600s status=OK rc=0` (=false, 135 passed).
- Named pins of spec 4.2 (48 files): `[pyt] tag=inc-mon1-green-pins ... elapsed=170s bound=1200s status=FAIL rc=1` (4324 passed, 2 failed = tests/test_s81_s24_auth_throttle.py::test_r92_hygiene + ::test_p83_red_file_setenv_hygiene, the CRLF working-copy rows in the stored base record, GC-2).
- Comm set by the union rule: the whole backend test tree (conftest.py edited) = 766 files (the RED agent's 763 + the two RED files + the gate-rows file), minus the four test_precommit_hook*.py, 31 chunks of at most 25 files (bound 1200 each): 29,536 passed, 25 + 2 = 27 distinct FAILED ids at HEAD, every one in the stored base record harness/base_records/a74caba7.../23f5330f... (28 ids; the one not reproduced is the known wall-clock flake tests/test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST]). **branch-only-NEW = EMPTY.** Per-chunk [pyt] lines: `MON1_green/comm/pyt_lines.txt` (to be filed by the orchestrator).
- CLAUDE.md readers re-run after the CLAUDE.md edit: `[pyt] tag=inc-mon1-green-claudemd ... elapsed=19s bound=600s status=OK rc=0` (510 passed).
- CI-order set (GC-11: the lifespan user tests/test_s81_s20_result_gate.py first, the RED files, then the gate rows): `[pyt] tag=inc-mon1-green-ciorder ... elapsed=84s bound=1200s status=FAIL rc=1` (1492 passed; the same two base CRLF rows).
- ruff (E9,F63,F7,F82) and py_compile clean on the 14 python files; black 26.5.1 clean on the ratchet files (llm_router.py + the five new files, added to `.github/black-clean-paths.txt`); added lines pure ASCII, no 8-digit run, no key shape. The fourteen client jest fences and the full jest suite run in the final round (LC-7; no client literal moves).

## Stated limits

- L-1 Per-process state: a restart forgets it; the first outcome after each start re-emits the event (by design: A1-2). With the probe OFF and no traffic `/health` shows no entry and `/health/llm` says unknown.
- L-2 A single uvicorn worker is assumed; more workers each keep their own state and events.
- L-3 A model-specific 403 on dispatch marks the credential rejected while other dispatch calls succeed; the state flaps, each change logs one line, and the cool-down bounds the events to one per (provider, state) per 900 s; a change it suppresses is held pending and emitted once by the first confirming outcome after the window (F1-1), so the last event cannot stay "recovered" while the state is rejected. A moderation or probe success no longer feeds this flap (F1-3, R-MON1-17).
- L-4 / MON1b Anthropic's too-low credit balance is a 400 identified by message text only, and the Anthropic spend LIMIT (400) / tier spend CAP (429 with a body detail the SDK does not surface) are not classified as quota. Follow-up MON1b: re-measure and close before the Claude text roles flip (window 13).
- MON1c While one in-use provider stays rejected (OpenAI during the transition), `GET /health/llm` stays degraded and cannot signal the other provider; in that period the per-provider Sentry rule is the alarm and no uptime monitor is pointed at the path. A per-provider monitor path is follow-up MON1c, ruled with O2.
- L-5 `serper_keys.marked_exhausted` counts this process's marks since start (never decays) while the Redis flag lives 6 h; a single-key configuration shows no `serper_keys` entry (single-key inert, unchanged).
- L-6 The moderation except arm keeps logging the exception text at WARNING (base behaviour, not an event).
- L-7 `GET /health/llm` answers HEAD with 405: a monitor must use GET.
- L-8 With `OPENAI_BASE_URL` pointing at a non-OpenAI gateway the probe's models.retrieve may be unsupported: inconclusive, no state change.
- L-9 `/health/llm` fails OPEN (200) if its own view raises or the leaf is absent (pinned by G5).
- L-10 The alert recipe empties a PRIVATE scope attribute of sentry-sdk 2.68.1 (`_event_processors`); a future SDK that drops it takes the fail-safe path (one event from the current scope, request region as `_before_send` leaves it, one WARNING `[LLM_CREDENTIAL] alert scope recipe unavailable; sent from the current scope`), pinned by G1. Re-measure SE04 on every sentry-sdk bump.
- L-11 Nobody enters a key for a test: the alarm is proven end to end only by production itself (PP1-PP3) while the OpenAI credential stays rejected.
- L-12 Disclosure class (R-MON1-28): `/health` and `/health/llm` are public and tell anyone that an AI credential is rejected or out of credit (state names, a status code, a timestamp, a count only), the `brightdata_auth` precedent.
- L-13 The probe's metadata endpoints are unbilled by the vendors' official pages only by omission (spec 11 Q8); PP6 checks the console.
- L-14 The SDKs' own request lines: openai 3.3.1 and anthropic 1.12.1 log `HTTP Request: METHOD URL "status"` at INFO from the `httpx2` logger (logging_config quiets only `httpx`). Pre-existing for every dispatch; with the probe ON, one more such line per provider per tick (the models URL); no credential is in them.
- L-15 The `count` in the public `/health` entry is the number of calls since the last state change (ruled in R-MON1-28: a count only); it discloses LLM call volume since that change and is named here for the owner's ruling O2.
- L-16 The first verified `ok` of a provider in a process logs the transition line `[LLM_CREDENTIAL] provider=<p> state=ok status=none source=<s>` once (none -> ok, no event): expected, and useful when reading the deploy log.
- L-17 A process that never imported `app.services.sentry_service` sends no event (the sender is looked up through sys.modules); the web process imports it at startup (`app.main`), so production web is unaffected. The leaf stamps the cool-down before it looks the sender up (ruled as is, F1-7), so in such a process the stamp is spent without a send.

## Owner steps (names only; nobody but the owner enters any credential)

1. A Sentry alert rule: trigger "an event is seen", filter tag `alert` equals `llm_credential` (a second rule, or a second value, for `serper_keys`), action interval 24 hours (A1-2: at most one notification a day while the state holds), action: notify the owner's phone. One sentence on what follows from that: a redeploy while the credential is still rejected adds one EVENT to the same issue (its count rises, its last seen moves), and a second NOTIFICATION arrives only once 24 hours have passed since the previous one. Who receives it: ruling O2 (OPEN).
2. Only in the probe's window (after O3): one uptime monitor on `GET /health/llm` (GET, never HEAD), alert on non-200. Not before the Claude switch (A1-2, MON1c).
3. The flip of `ENABLE_LLM_CREDENTIAL_PROBE` on web in its own canary window, set by the relay on the owner's yes, after a working credential (ruling O3, OPEN). `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` stays unset (900). Within the first tick `/health` must show the probe-sourced state while a comparison succeeds; an `unknown` that persists with the probe ON is the signal to roll the flag back or fix the credential's permissions (R-MON1-18).
4. Optional manual trigger (R-MON1-26), once, through the ops lane's existing run path in web's environment (no value printed): `railway run -s web python -c "import app.main, sentry_sdk; from app.services.sentry_service import capture_credential_alert as f; f('llm_credential', 'openai', 'test', None); sentry_sdk.flush(5)"`.
5. Optional, no code: a Sentry metric alert on the existing ERROR events for a failure-rate threshold.

Open owner rulings: **O2** (the monitor path and who receives the alert) and **O3** (the probe's window). The unit does not merge before both are answered.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

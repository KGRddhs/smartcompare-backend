# fix(monitoring): MON1 LLM-CREDENTIAL-HEALTH: an operator signal for a dead LLM credential (passive part unflagged, active probe dark)

Incident 2026-11-11, root cause 2 "no alarm" (incident fix S7; DEFECT_LEDGER row MON1). The production OpenAI credential was rejected (HTTP 401) for 8+ days and nothing told the owner: the chokepoint records nothing an operator sees for a 401 (correct for gating, wrong for alerting), `/health` carries no LLM or Serper state, and the per-call ERROR records became 48 untagged Sentry events with nothing to hang a rule on.

Status wording (the owner's proof standard): when merged this unit is **merged, NOT yet proven**. Green suites are necessary and are not the proof; the PROOF ON THE PHONE section below decides. It does not merge before the owner answers O2 and O3 and the relay opens a merge window (the merge freeze of addendum A2-2).

## What it does

- **Recorder** (`app/services/llm_credential_health.py`, a new stdlib leaf): per provider (openai, anthropic) the credential state ok / rejected / quota, by exception class + `status_code` + the SDK's structured `code` / `type`, never message text. `quota` = openai 429 with one of the five structured codes of R-MON1-16 or type insufficient_quota; anthropic type billing_error. A timeout, 5xx, plain 429 or 400 changes nothing.
- **Hooks** (exception-transparent: the same exception object re-raised, no await, no I/O): both branches and both success tails of `api_budget_service.guarded_llm_create`; the except arm and success tail of `llm_router.guarded_anthropic_create` (incl. the Claude moderation site); the OpenAI moderation call in `content_safety_service.moderate_output`. Gating is byte-identical (G01 AST digests of the ten gating functions; G02: ten 401s are each admitted and never open the breaker).
- **Alert event** (`sentry_service.capture_credential_alert`): ONE message `credential_state`, level error (info for a recovery), tags `alert=llm_credential`, `provider`, `state`, `status`, fingerprint [alert, provider, state], emitted in a scope with no request region (R-MON1-20; the private `_event_processors` recipe measured on sentry-sdk 2.68.1, SE04; fail-safe GC-5: any failure of the recipe still sends exactly one event and logs one constant WARNING, gate row G1). One event per state CHANGE, at most one per (provider, state) per 900 s (R-MON1-21; the suppressed change logs `[LLM_CREDENTIAL] alert suppressed provider=%s state=%s cooldown_s=%d`, G2). `alert=serper_keys` fires once when every Serper key is found exhausted.
- **`/health`**: two additive entries, present only after an outcome in this process: `llm_credential` {provider: {state, last_status, at, source, count}} and `serper_keys` {configured, marked_exhausted, none_left, at} (counts only, never a key or prefix). `status`, `message`, the 200 and every existing entry are unchanged.
- **Monitor path `GET /health/llm`** (public, GET only, not in the schema, limiter-exempt, no I/O): 503 `LLM_CREDENTIAL_UNUSABLE` while an in-use provider is rejected or quota; with the probe ON, 503 `LLM_CREDENTIAL_UNKNOWN` while an in-use provider has no outcome after 120 s of uptime (R-MON1-22); else 200. Never a codeless 503.
- **Active probe (DARK)**: `ENABLE_LLM_CREDENTIAL_PROBE` (default OFF, read as the FIRST statement of `tick()`, R-MON1-19) + `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` (default 900, floor 300). A lifespan task (cancelled before the drain); ON: one `models.retrieve` per in-use provider per interval (no tokens, 5 s, no retry), first 20 s after start; no spend admit, no ledger record. A probe 401 rejects only with the structured invalid-credential signal (R-MON1-18) and a probe success never clears quota or a dispatch 403 (R-MON1-17).

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

The same recorder, event, `/health` entry and monitor path cover the Anthropic credential through the hooks on `guarded_anthropic_create` (rows H07, H08, H09, P07, P16, gate row G4). "In use", as implemented: openai while `OPENAI_API_KEY` is set (no flag moves it out); anthropic while `ANTHROPIC_API_KEY` is set AND an `ENABLE_ANTHROPIC_*` role flag is ON (`llm_router.any_role_enabled`). After the text roles move to Claude, OpenAI is still called by the OpenAI moderation call (until `ENABLE_ANTHROPIC_MODERATION`), the camera path (until `ENABLE_ANTHROPIC_VISION`) and the pre-v3 route (`ENABLE_OPENAI_PRE_V3` for clients below consent 3), so OpenAI stays "in use" while its key is set; the state is per provider (A2-3), so a held OpenAI rejection stays quiet while an Anthropic rejection still alarms (G4). Removing OpenAI from "in use" = unsetting `OPENAI_API_KEY` on web (an owner step, after its last caller flips).

## PROOF ON THE PHONE (spec 8b as amended by R-MON1-22, R-MON1-24, R-MON1-26, A1-1, A1-2)

The owner declined a bridge OpenAI credential ("No, wait for Claude"), so the steady state for the coming days is `rejected` on OpenAI. Nothing below needs AI text. What the owner sees until the Claude switch: ONE alert event at the first comparison after each deploy or restart; `/health` showing `llm_credential.openai.state = rejected` (last_status 401) from that comparison on; `GET /health/llm` answering its coded 503 from then on (so no uptime monitor is pointed at it before the switch); no further event while the state does not change.

| # | Repeat (run by the relay with the owner) | What must be visible | Backing check |
|---|---|---|---|
| PP1 | After the deploy, ONE comparison on the phone (e.g. Creed Aventus EDP vs Parfums de Marly Layton EDP), then one GET of production `/health` | `llm_credential.openai` with state `rejected`, last_status 401, source dispatch; `serper_keys` with configured >= 2 | the deploy log has exactly ONE `[LLM_CREDENTIAL] provider=openai state=rejected status=401 source=dispatch` line for that comparison; Sentry shows ONE `credential_state` event tagged alert=llm_credential provider=openai state=rejected status=401 with no request region |
| PP2 | The owner's Sentry rule (owner step 1) | the notification of PP1's event arrives on the owner's phone | the rule: "an event is seen", filter tag `alert` = `llm_credential`, action interval 24 hours |
| PP3 | A redeploy (or restart) while the credential is still rejected, then one comparison | a SECOND notification arrives (R-MON1-24) | a second L1 line in the new deployment's log; the same Sentry issue gains an event |
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

Mutants: 36 killed on the RED prototype (GATE_MON1 GC-3); the four gate rows each killed by a named mutant on the GREEN bytes (MG1 fallback send removed -> G1; MG2 suppressed WARNING removed -> G2; MG3 level info for `test` -> G3; MG4 cool-down keyed on the state alone -> G4).

## Deliberate pin changes (spec 4.1, GATE_MON1 GC-4)

| E | File | Change | Why |
|---|---|---|---|
| E1 | tests/test_s81_s03_llm_ledger_v2.py `K1_GUARDED_AST_SHA` (+ the test_k1 docstring) | re-recorded to the AST digest of `guarded_llm_create` with the H1-H4 hooks (two-piece literal, no 8-digit run; the name has no scanner keyword) | H1-H4 edit that function body by ruling (R-MON1-5); the S81-04 precedent |
| E2 | tests/test_s81_s04_spend_breaker.py::test_p05_flag_off_health_has_no_spend_key | the allowed key set widened by exactly `llm_credential` and `serper_keys`; its subject (no spend key with the flag off) and every other assertion unchanged; no recorder reset inside the test | its served dispatch records the OpenAI outcome (found by the RED prototype) |

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
- L-3 A model-specific 403 on dispatch marks the credential rejected while other calls succeed; the state flaps, each change logs one line, and the cool-down bounds the events to one per (provider, state) per 900 s.
- L-4 / MON1b Anthropic's too-low credit balance is a 400 identified by message text only, and the Anthropic spend LIMIT (400) / tier spend CAP (429 with a body detail the SDK does not surface) are not classified as quota. Follow-up MON1b: re-measure and close before the Claude text roles flip (window 13).
- MON1c While one in-use provider stays rejected (OpenAI during the transition), `GET /health/llm` stays degraded and cannot signal the other provider; in that period the per-provider Sentry rule is the alarm and no uptime monitor is pointed at the path. A per-provider monitor path is follow-up MON1c, ruled with O2.
- L-5 `serper_keys.marked_exhausted` counts this process's marks since start (never decays) while the Redis flag lives 6 h; a single-key configuration shows no `serper_keys` entry (single-key inert, unchanged).
- L-6 The moderation except arm keeps logging the exception text at WARNING (base behaviour, not an event).
- L-7 `GET /health/llm` answers HEAD with 405: a monitor must use GET.
- L-8 With `OPENAI_BASE_URL` pointing at a non-OpenAI gateway the probe's models.retrieve may be unsupported: inconclusive, no state change.
- L-9 `/health/llm` fails OPEN (200) if its own view raises.
- L-10 The alert recipe empties a PRIVATE scope attribute of sentry-sdk 2.68.1 (`_event_processors`); a future SDK that drops it takes the fail-safe path (one event from the current scope, request region as `_before_send` leaves it, one WARNING `[LLM_CREDENTIAL] alert scope recipe unavailable; sent from the current scope`), pinned by G1. Re-measure SE04 on every sentry-sdk bump.
- L-11 Nobody enters a key for a test: the alarm is proven end to end only by production itself (PP1-PP3) while the OpenAI credential stays rejected.
- L-12 Disclosure class (R-MON1-28): `/health` and `/health/llm` are public and tell anyone that an AI credential is rejected or out of credit (state names, a status code, a timestamp, a count only), the `brightdata_auth` precedent.
- L-13 The probe's metadata endpoints are unbilled by the vendors' official pages only by omission (spec 11 Q8); PP6 checks the console.

## Owner steps (names only; nobody but the owner enters any credential)

1. A Sentry alert rule: trigger "an event is seen", filter tag `alert` equals `llm_credential` (a second rule, or a second value, for `serper_keys`), action interval 24 hours (A1-2: at most one notification a day while the state holds), action: notify the owner's phone. Who receives it: ruling O2 (OPEN).
2. Only in the probe's window (after O3): one uptime monitor on `GET /health/llm` (GET, never HEAD), alert on non-200. Not before the Claude switch (A1-2, MON1c).
3. The flip of `ENABLE_LLM_CREDENTIAL_PROBE` on web in its own canary window, set by the relay on the owner's yes, after a working credential (ruling O3, OPEN). `LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS` stays unset (900). Within the first tick `/health` must show the probe-sourced state while a comparison succeeds; an `unknown` that persists with the probe ON is the signal to roll the flag back or fix the credential's permissions (R-MON1-18).
4. Optional manual trigger (R-MON1-26), once, through the ops lane's existing run path in web's environment (no value printed): `railway run -s web python -c "import app.main, sentry_sdk; from app.services.sentry_service import capture_credential_alert as f; f('llm_credential', 'openai', 'test', None); sentry_sdk.flush(5)"`.
5. Optional, no code: a Sentry metric alert on the existing ERROR events for a failure-rate threshold.

Open owner rulings: **O2** (the monitor path and who receives the alert) and **O3** (the probe's window). The unit does not merge before both are answered.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

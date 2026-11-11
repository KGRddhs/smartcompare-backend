# MON1 ADVERSARY: observability-and-secrets (GATE_MON1 GC-13 named checks)

Agent: Opus 5.5. HEAD verified c6592b539920b6189552dbc6aa23d7d7be435d91 (sc-inc-mon1, fix/inc-mon1-llm-credential-health), status clean at start and end. Frozen RED files re-hashed at start and end (committed bytes): 10061c0a...6c71 and 2950c33e...0845880, unchanged. The worktree was never edited; its node_modules junction checked present at the end.

Scratch worktree: the prescribed path <SP>/MON1_adv_observabilityandsecretsthenamedchecksofgate failed `git worktree add` (Could not reset index file: a Windows path-length failure); pruned, and made instead at <SP>/m1ao (detached at c6592b53, no junction), sha-verified; every mutant restore sha-verified; removed with `git worktree remove --force` + prune.

## VERDICT: NOT_READY (1 MAJOR in the PR body, 0 BLOCKING; the code passes every GC-13 named check at runtime)

## Every [pyt] line
```
[pyt] tag=inc-mon1-advobs-on  elapsed=31s bound=600s status=OK rc=0  (PROBE=true; 135 passed: 2 RED files + gate rows)
[pyt] tag=inc-mon1-advobs-off elapsed=30s bound=600s status=OK rc=0  (PROBE=false; 135 passed)
[pyt] tag=inc-mon1-advobs-a01..a16, a17 (invalid), A17b, a18: one line each, see the table (bound 600s)
[pyt] tag=inc-mon1-advobs-ciorder elapsed=84s bound=1200s status=FAIL rc=1  (1522 passed, 2 failed = s24 test_r92_hygiene + test_p83_red_file_setenv_hygiene, the base CRLF rows of GC-2; GREEN's CI-order set + test_sentry_service.py + test_sentry_503_suppression.py)
[pyt] tag=inc-mon1-advobs-c10 elapsed=63s bound=1200s status=OK rc=0  (1394 passed, 1 skipped)
[pyt] tag=inc-mon1-advobs-c25 elapsed=67s bound=1200s status=OK rc=0  (911 passed)
[pyt] tag=inc-mon1-advobs-c26 elapsed=23s bound=1200s status=OK rc=0  (716 passed, 1 skipped)
```
Chunks 10/25/26 (GREEN's lists) hold the sentry, health, shutdown-drain and serper-memo suites. ruff (E9,F63,F7,F82; F401,F811,F841 on the two leaves) and py_compile clean on 12 files. Added lines: one non-ASCII line = the pre-existing CLAUDE.md Feature-Flags line (em dash already there, CRLF kept); no key/JWT/PEM/credentialed-URL shape. The six deleted lines are each justified (CLAUDE.md line rewritten in place, a docstring sentence, the create wrapped in try, K1 E1 re-pin + docstring, the E2 allowed set).

## GC-13 named checks (runtime probes on the real stack)
1. No credential, key prefix, header, URL or exception text in the unit's log lines, events, tags or /health: HOLDS. Real TestClient request through the full middleware, real sentry-sdk 2.68.1 with an in-memory transport, a sentinel in the query, Authorization header, exception message, a request tag, user, extra, context and breadcrumb: the alert event carries only tags alert/provider/state/status (+ any GLOBAL-scope tag), no request, user, breadcrumbs or transaction; sentinel absent; /health and /health/llm sentinel-free. A11, A12, A13 killed.
2. One event per transition: HOLDS (A03, A04, A18 killed). The alert scope is a fork: a capture later in the SAME request still carries the request region (measured).
3. Cool-down per (provider, state): HOLDS (A04 killed; GREEN MG4).
4. GC-5 fail-safe: HOLDS on the real SDK: recipe forced to raise -> exactly one event per transition from the current scope; request region as _before_send leaves it (authorization [REDACTED], x-device-fingerprint [Filtered], q=[QUERY_REDACTED]); transaction name present (gate-allowed).
5. Probe never clears quota or a dispatch 403: HOLDS (A05, A06 by P13; A07 by P15).
6. /health 200, status/message unchanged, entries additive: HOLDS (measured).
7. Monitor path never a bare 503: HOLDS at runtime (A08 killed; view raising or leaf absent -> 200 {"status":"ok","providers":{}} measured). Branch unpinned: m1.
8. Lifespan task cannot outlive shutdown / delay the drain: HOLDS at runtime (after TestClient exit the task is done AND cancelled, pointer None, 0.0 s; order heartbeat < probe < drain pinned by P10). Cancellation unpinned: m2.

## Mutants (by hand; sha-verified copies; each restore sha-verified)
| id | change | result |
|---|---|---|
| A01 | keep the scope's event processors | KILLED test_se04 |
| A02 | fingerprint [kind] only | KILLED test_se01 |
| A03 | alert on every first transition (incl. first ok) | KILLED test_l09 |
| A04 | no cool-down | KILLED test_l08 |
| A05 | probe success clears everything | KILLED test_p13[quota] |
| A06 | probe success clears a dispatch 403 | KILLED test_p13[dispatch403] |
| A07 | probe rejects on any 401/403 | KILLED test_p15[oa401-nocode] |
| A08 | UNUSABLE body without code | KILLED test_m02 |
| A09 | /health/llm fails CLOSED, codeless 503, when the view raises | SURVIVED (m1) |
| A10 | probe stop handler not registered | KILLED test_p10 |
| A11 | serper_keys exposes a key prefix | KILLED test_he05 |
| A12 | state record gains a field | KILLED test_l04 |
| A13 | inconclusive INFO line carries exception text | KILLED test_p11 |
| A14 | tick awaits before the flag read | KILLED test_p01 |
| A15 | fail-safe resends after a post-send scope error | SURVIVED (m3) |
| A16 | moderation note_success moved above the call | SURVIVED (m4) |
| A17 | invalid (SyntaxError), discarded | - |
| A17b | shutdown sets None without cancel/await | SURVIVED (m2) |
| A18 | serper alert on every none-left selection | KILLED test_s01 |
14 valid kills, 4 survivors (coverage gaps on correct code). The 36 GC-3 RED mutants were not re-run (correctness lens).

## MAJOR
M1. PR_BODY.md PROOF ON THE PHONE row PP3 contradicts owner step 1. PP3: a redeploy while still rejected makes "a SECOND notification arrive (R-MON1-24)". Owner step 1 (addendum A1-2, which amended R-MON1-24) sets the Sentry rule's action interval to 24 HOURS, and the fixed fingerprint [llm_credential, openai, rejected] puts every rejection in ONE issue; the action interval is per issue. A redeploy within 24 h of PP1 adds a second EVENT to the issue but sends NO second notification. Run as written (same day), PP3 fails deterministically and the owner reads a working alarm as broken (H6 / GC-14). Fix, wording only: PP3 = the same issue gains a second event plus a second L1 line; a second NOTIFICATION only if the redeploy is more than 24 h after the last one (or run PP3 the next day). R-MON1-24 vs A1-2 carries the same inconsistency: re-rule PP3. No code change.

## MINORS (documentation rulings / stated limits; code correct)
m1. A09 survives: no row drives GET /health/llm with monitor_view raising or the leaf absent; L-9 and "never a bare 503" on that branch are unpinned (runtime correct). Suggest gate row G5 killing A09.
m2. A17b survives: P10 asserts only `_llm_probe_task is None`, not that the task was cancelled; "cannot outlive shutdown" is unpinned (runtime correct). Suggest a gate row asserting task.done() and task.cancelled() after the TestClient exits.
m3. A15 survives: the `if sent: return` guard (no second event when a scope exit raises after the send) is unpinned.
m4. A16 survives: no row moves a moderation call from a HELD rejected state; a code-motion of the moderation note_success above the call would emit a false recovery event. Suggest an H10 variant.
m5. Stale last word (not in the stated limits): rejected (alert) -> ok (recovery) -> rejected within 900 s is suppressed and never re-emitted after the window, so the LAST Sentry event can say ok while the held state is rejected (L-3's 403 flap; R-MON1-17's probe clearing a dispatch 401). /health stays truthful as ruled; add a sentence to L-3.
m6. The SDK transport logger is `httpx2` (openai 3.3.1 / anthropic 1.12.1; measured level NOTSET) while logging_config quiets only `httpx`, so every SDK request logs `HTTP Request: METHOD URL "status"` at INFO. Pre-existing for every dispatch; with the probe ON one more per provider per tick (the models URL, no credential). State it or quiet `httpx2` later.
m7. /health `count` = consecutive same-state outcomes = LLM call volume since the last change, on a public endpoint. In the spec, the CLAUDE.md row and R-MON1-28 ("a count only"): ruled; noted for O2.
m8. emit_alert stamps the cool-down before the sys.modules sender lookup; a process that never imported sentry_service sends and logs nothing. web imports it at app.main:45 (init_sentry at import): production web unaffected.

## Prove-nothing rows
None in this lens; the four survivors are gaps, not rows that prove nothing.

## Claims vs bytes
CLAUDE.md MON1 block (tags, fingerprint, 900 s, suppressed-line text, /health shapes, 503 codes, 120 s, in-use rule, probe defaults 900/300/5 s/20 s/no retry, cancel before drain) matches the code. PR body matches except PP3 (M1). GREEN's 135/135 ON and OFF and the CI-order failures reproduced.

# MON1 adversary report, lens CORRECTNESS (Opus 5.5), 2026-11-11

HEAD verified: c6592b539920b6189552dbc6aa23d7d7be435d91 (worktree sc-inc-mon1, status clean). Scratch: detached worktree MON1_adv_correctness at the same sha, made with core.autocrlf=false so the bytes equal the blobs (a first autocrlf=true checkout gave CRLF copies of the frozen files with other shas; discarded at once). Frozen RED files re-hashed at start and end in both checkouts: 10061c0a... and 2950c33e..., unchanged. Nothing in sc-inc-mon1 was edited.

VERDICT: SOUND (no blocking, no major). The minors are documentation or stated-limit rulings.

## Runs ([pyt] lines)
- [pyt] tag=inc-mon1-advc-unit-on start=2026-11-11 21:45:07 end=21:45:36 elapsed=29s bound=600s status=OK rc=0 (ENABLE_LLM_CREDENTIAL_PROBE=true; 2 RED files + gate rows: 135 passed; netguard 0)
- [pyt] tag=inc-mon1-advc-unit-off start=2026-11-11 21:46:04 end=21:46:33 elapsed=30s bound=600s status=OK rc=0 (=false; 135 passed)
- 46 mutants, one pytest each (tags inc-mon1-advc-mut-<id>, bound 600, -x over the three unit files), every restore sha256-verified (restore_ok x46), lock created and removed. Per-mutant [pyt] lines: MON1_adv/logs/mut_driver.out (batch 1) and MON1_adv/logs/mut/*.log.

## Mutants (42 KILLED on AssertionError, 4 SURVIVED)
Spec: MU01 h01, MU02 h03, MU03 h02, MU04 h01, MU06 l02 (400 with invalid_api_key text), MU07 l02 quota codes, MU08 l03 billing, MU10 l08, MU11 h03, MU12 he01, MU13 m02, MU14 m01, MU15 p01, MU16 p03, MU18 s02, MU19 s01, MU21 se01, MU22 he05, MU23 l07: KILLED.
Gate rows by hand: MG1 g1, MG2 l12, MG3 g3, MG4 g4: KILLED.
Adversary: AM01 probe clears quota (p13); AM02 probe clears dispatch 403 (p13); AM03 openai probe signal dropped (p15); AM04 anthropic probe signal dropped (p15); AM05 R-MON1-16 type branch dropped (l02 type-only); AM06 grace comparison inverted (m07); AM07 processors not emptied (se04); AM09 moderation source (h10); AM10 router site mapping (h08); AM11 monitor ignores quota (m03); AM12 unbounded probe await (p06); AM13 H7 dropped (h10); AM14 H6 dropped (h08); AM15 recovery at level error (g3); AM16 openai dispatch 403 not rejected (l02); AM19 / AM23 count (l04); AM20 probe success not noted (p04); AM21 UNKNOWN ignores the flag (m07): KILLED.
SURVIVED (test gaps; the bytes behave correctly):
- AM08 a suppressed send also re-arms the cool-down (sliding window): no row tells fixed from sliding.
- AM17 _stop_llm_credential_probe cancels without awaiting the task: P10 does not prove the await.
- AM18 the closed-set guard of capture_credential_alert (GREEN deviation 5) removed: no row sends an out-of-set value.
- AM22 health_snapshot returns live records instead of copies: equivalent at runtime (serialised at once).

## Runtime-truth probes (MON1_adv/probes/)
- p1 REAL SDK errors through each client's own response-to-exception path (openai 3.3.1, anthropic 1.12.1): openai 401 invalid_api_key -> rejected (dispatch, probe); 429 insufficient_quota -> quota; 429 rate_limit_exceeded -> none; 403 unsupported_country -> rejected (dispatch) / none (probe); anthropic 401 authentication_error -> rejected; 403 permission_error -> rejected / none; 402 billing_error -> quota; 400 credit text -> none (MON1b); 429 -> none. Matches R-MON1-16/18 and the CLAUDE.md row.
- p2 scope recipe on sentry-sdk 2.68.1 with a capturing transport and the real _before_send: the alert has no request-scope tag, no processor extra, no transaction; the caller's isolation scope keeps its processor and tags afterwards; the global scope is untouched; the fail-safe path sends exactly one event.
- p3 the probe through REAL AsyncOpenAI / AsyncAnthropic over a mock transport: with_options(max_retries=0) gives one GET per provider (/v1/models/gpt-4o-mini, /v1/models/claude-haiku-5-5) though the base client has max_retries=3; structured 401 -> rejected source probe and monitor 503 LLM_CREDENTIAL_UNUSABLE; 200 -> ok; a held dispatch 403 is not cleared by a probe success; an unsignalled probe 403 -> inconclusive.
- Flag-OFF identity / contract freeze: /health keeps status healthy, message and every key; the client reads only response.data.status (SmartCompareApp/src/services/api.ts:531-537); new keys absent until an outcome; tick() returns before any client (MU15).
- Error-handler mapping: /health/llm returns a JSONResponse with an explicit code; STATUS_CODE_MAP applies to HTTPException only (MU13 killed by m02).
- Census: the only create sites in app/ are the two guarded_llm_create arms, the content_safety moderation call and guarded_anthropic_create; all hooked; the CancelledError arm records nothing.
- Billing R-A3: no quota, refund or history code in the footprint; gating unchanged (G01/G02, MU11).
- GC-12: no line of extraction_service.py, image_routes.py, url_extraction_service.py. Six deleted lines, each replaced in place. Added lines ASCII (the one non-ASCII added line is the pre-existing CLAUDE.md :341 line; the inserted clause is ASCII).

## Prove-nothing rows
None found on the real SDK: an_err force-sets status/type only when a sibling suite installed the S81-06 fake hierarchy. test_g1_control_* is a control row.

## MINORS (documentation / stated-limit rulings)
1. PP3 of the PR body cannot pass as written within 24 h: owner step 1 sets the Sentry action interval to 24 h (A1-2) on ONE issue (fingerprint llm_credential/openai/rejected), so a redeploy inside 24 h of PP1 adds an event but sends NO second notification. Reword PP3 (redeploy at least 24 h after PP1, or the visible item = the issue's event count rises).
2. A flap inside the cool-down silences the alarm (measured, probes/p4_stuck.py): rejected (alert) -> ok (recovery, e.g. a moderation success) -> rejected 5 s later (suppressed) -> ten more failures over 10 h: events = [rejected, ok]; /health says rejected while the last Sentry event says recovered; only transitions emit, so nothing re-alerts. R-MON1-21 rules the suppression as written; state it as a limit or follow-up (re-emit a suppressed transition at the next same-state outcome after the cool-down).
3. A moderation success has no R-MON1-17 restriction, so it clears a dispatch quota or dispatch 403 state. If the free moderation endpoint answers 200 while chat answers 429 insufficient_quota or a model/project 403 (not measured), the state and /health/llm flap per compare. Same class as L-3: add moderation to it.
4. Surviving mutants AM08, AM17, AM18, AM22: untested properties (AM17 stop-handler await and AM18 closed-set guard are claimed in the GREEN report / docstrings without a row).
5. GREEN report "sha256 after, at HEAD" lists working-copy CRLF shas, not blob shas (app/main.py blob d71aa1ba vs listed 35bcf11e; CLAUDE.md blob 3d6bef07 vs 4b9bb8be); only the two new LF files agree. Label them.
6. PP1 expects serper_keys with configured >= 2: true only if production has two or more Serper keys and the comparison makes a multi-key selection; state it as conditional.
7. The first-ever ok of a provider logs the L1 WARNING once per process (none -> ok): harmless; name it or rule it.

Scratch worktree removed at the end (git worktree remove --force) after a clean status at c6592b53.

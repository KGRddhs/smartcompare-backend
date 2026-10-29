# S81-08 CLIENT-FIRST-OTA - adversary report, lens: CORRECTNESS (Opus 5.5)

Unit S81-08 CLIENT-FIRST-OTA (client lane, SmartCompareApp, no runtime flag). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08, branch feature/s81-s08-client-first-ota, HEAD 3f990a6908be12312fdc8a440a875ddfa8d0d6b5 VERIFIED at start (git status clean); base e7c81956f11749b1378aa449c4ac616c82bfe6a9. Notes folder <scratchpad>/S81-08_adv/corr (notes.md, mutate.py, mutants_spec.json, mutants_x.json, mut/*.tsv + per-mutant jest JSON, bytecopies/, memo_probe.js + .log, base_revert.py, baserev/). Scratch worktree <scratchpad>/S81-08_adv_correctness (git worktree add --detach at 3f990a69, no junction, no node_modules; used for the backend parser probe; removed at the end). This report (and every notes file) is written THROUGH THE SHELL (python heredoc chunks -> report_body.md -> mkreport.py -> this .md); pure ASCII, LF. <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad.

Inputs read: s81-common.txt; GATE_S81_08 (GC-1..GC-11, read twice); RULINGS_S81_08 (R-S08-1..15 + Measurement rulings + the R-S08B amendment); the GREEN report and PR_BODY.md; spec section 6; RED report sections 6-8 + Appendix B; the full GREEN diff of every src file; the nine RED files' row titles and the harness parts of requestHeaders / sseHeaders / consentRecord / deviceId / resetRender; backend error_handler.py, text_routes / url_routes / image_routes USAGE_LIMIT sites, app/utils/request_context.py, llm_router consent constant (read-only).

RED files: all nine re-hashed at start (and at the end, section 7): equal to the frozen sha256 values.

## 0. Verdict

NOT_READY: 0 blocking, 1 MAJOR (MAJ-1: spec mutant M24 is NON-EQUIVALENT and SURVIVES the FULL jest suite on the GREEN bytes: the per-account key of the request-path consent memo, the only guard of R-S08-3 / BL3 on the X-AI-Consent-Version header across an account switch, is unpinned; RED Appendix B's "M24 KILLED by E9" does not hold on these bytes). The GREEN product code itself is correct on every path I probed; MAJ-1 is a proof gap whose fix is test-only (one added row). Minors are documentation / equivalent-survivor rulings.

## 1. Findings

### MAJOR

MAJ-1 (proof gap on R-S08-3 / BL3; GC-11 "the consent memo and the per-account rule"): spec mutant M24 "consent memo ignores the account" (src/services/aiConsent.ts, `if (memo !== null && memo.userId === userId) return memo.current;` -> `if (memo !== null) return memo.current;`) SURVIVES on the GREEN bytes: consentRecord alone (17 s, rc=0), and the FULL jest suite (M24full, section 2). RED Appendix B and the spec section 6 list it KILLED by E9; that held on the RED prototype, not on GREEN's design. Mechanism: GREEN's hasCurrentAiConsentForRequest(null) DROPS the memo (forgetRequestConsent) on a signed-out request, and E9 always passes through `getSavedUser -> null` before it switches to USER_B, so the account key is never exercised while the memo is populated; B15 runs under the global consent mock (no memo export) and never reaches the memo either. Non-equivalence PROVEN without touching the worktree: memo_probe.js transpiles the HEAD aiConsent.ts + requestContext.ts (sha-checked: 35a35340... / 121634bd..., head_bytes_ok=true) and runs them in plain node with stubbed AsyncStorage / getSavedUser: A agrees -> A's metered request sends "2"; the saved user then switches to B with NO signed-out request in between (the realistic flow: no metered request leaves the Auth stack) -> HEAD sends NO header (correct), M24 sends "2" while hasCurrentAiConsent(B) = false (log: memo_probe.log). Because GREEN invalidates the memo only on record / clear / a signed-out REQUEST (not in logout(); R-S08-3 says "invalidated by recordAiConsent / clearAiConsent / sign-out"), the account key is the ONLY guard of the per-account rule across an account switch, and no row pins it. Product impact today: none (HEAD is correct). Impact of the unpinned regression it would let through: the header would claim consent for an account that never agreed on its metered requests until that account passes the UI gate (withAiConsent -> recordAiConsent drops the memo before any compare, so the compare/LLM path is still gated; the usage-status requests are not), and a consented account could send no header after a non-consented one (S81-06 routes by this header from consent v3). FIX (test-only; RED files are frozen, so a new row in a new file for the gate to name): plant A's current record, getSavedUser -> A, buildContextHeaders -> X-AI-Consent-Version = String(AI_CONSENT_VERSION); getSavedUser -> B directly (no null step), buildContextHeaders -> NO X-AI-Consent-Version (B has no record); optionally the reverse (A without a record, B current -> B gets the header). Passes on HEAD (probe), fails under M24. No product code change needed.

### MINOR (documentation / equivalent-survivor rulings)

m1 (equivalent survivor M26): `if (!current || !userId) return null;` -> `if (!current) return null;` survives (REQ, and the FULL suite as M26full, section 2). Equivalent on these bytes: the null user is refused twice before that line (the real hasCurrentAiConsentForRequest(null) returns false; the global-mock else-branch returns null early), so the `|| !userId` is a third, redundant guard. B15 exercises only the else-branch (consent:'global'). Ruling asked: accept as equivalent.

m2 (equivalent survivor M31): `if (kind === 'monthly') return null;` in sheetResetClock survives (RR): PaywallScreen's monthly branch never reads resetClock (`resets = t('paywall.limit.resets_monthly')`, unchanged from base), so the helper guard is redundant. The EFFECTIVE form on these bytes (M31p: the monthly branch renders the daily clock) is in section 2. Ruling asked: accept M31 as equivalent.

m3 (PR body precision): "Nothing new rides history, feedback, events, legal, the auth refresh or share" is true for HEADERS, but the share BODY's device_fingerprint_hash VALUE changes from the build-3 composition to the new id (ShareBottomSheet -> getDeviceFingerprint, unchanged call, new value), so invite rows written by OTA clients carry new-composition values beside build-3 legacy rows. The CLAUDE.md row states it ("The share body carries the new value"); the PR body should say it too, with the note that a revived SAME_DEVICE check (S81-08d) must match both compositions.

m4 (jest-only branch in production code, GREEN deviation 6 / Q3): consentHeaderValue's else-branch (hasCurrentAiConsent when hasCurrentAiConsentForRequest is absent) is unreachable in production (the real module always exports it) and exists only because __tests__/setup.ts's global aiConsent mock lacks the new export. Harmless; record a later unit that adds the export to the global mock and deletes the branch.

m5 (ruling wording vs implementation): R-S08-3 names "sign-out" as a memo invalidation; GREEN invalidates on a signed-out REQUEST and relies on the account key otherwise (no logout() hook). Behaviourally equivalent while the account key holds (which is exactly MAJ-1's point); the CLAUDE.md row and the PR body describe GREEN's behaviour accurately ("and by a signed-out request"). Ruling asked: accept the lazy invalidation, or add the logout() drop (either way MAJ-1's row is needed).

m6 (stated-limit candidate, reset clock): a RELATIVE reset (retry_after_seconds / retry_after from the 429 initialUsage) is re-anchored to Date.now() at every PaywallScreen render, so the re-render after the /usage/status fetch shifts the shown clock by the fetch latency (sub-minute in practice; it can flip the rounded minute). Once S81-09 sends an absolute resets_at on /usage/status it takes precedence (G11) and the drift disappears. Neither the sheet nor the pill re-renders when the instant passes (the line stays until the next render). Add to the stated limits.

m7 (stale doc comment): src/services/sentry.ts lines 6-7 still say "Sensitive request headers (authorization, x-admin-key, cookie) are also redacted"; the set now also holds x-device-fingerprint and x-device-fingerprint-legacy.

m8 (CLAUDE.md row precision): "no request body, query, URL or method changes" holds for SHAPES; the X-Device-Fingerprint VALUE at register / social sign-in and the share body value change (the row says so two bullets earlier). Optional rewording: "no request shape changes; the device value changes as above".

m9 (unpinned guards, X probes that SURVIVED; none is a product defect, the HEAD code is correct on each): X4 the consent-memo GENERATION guard (a read racing an Agree could memoise a stale false and drop the header for that account until the next record / clear; unlikely timing); X5 'an empty explicit header counts as absent' and X6 'only-if-absent in ANY letter case' (both stated as facts in the GREEN report, the CLAUDE.md row and the PR body: unpinned); X9 'a failed LEGACY read is not replayed' (with the finally removed, one transient SecureStore failure would drop X-Device-Fingerprint-Legacy from every later register / social sign-in in that process, i.e. no S81-08b match for that sign-up; the deviceFingerprint.ts comment claims it, no row pins it); X10 / X11 / X12 the shape checks of the legacy / consent / device values (GREEN deviation 7; equivalent under valid values); X24 'legacy only beside a resolved X-Device-Fingerprint' (near-equivalent: a null device id implies a failed nonce read, so the legacy read fails too unless the failure was transient); X30 the request path bypassing the memo (equivalent: same answers, more storage reads); X31 a signed-out request not dropping the memo (equivalent while the account key holds, MAJ-1). Ruling asked: accept as stated limits, or add rows for X4 / X6 / X9 in the MAJ-1 fix file (cheap, same harness).

## 2. Mutation runs (in place in sc-s81-s08 per GC-11, byte copies + sha256 restore after EVERY mutant, .qa-mutation.lock held, one jest at a time, a node.exe-jest process probe before every mutant: wait 0 s throughout)

Spec section 6 / RED Appendix B table re-derived on the GREEN bytes (51 mutants; counts {"KILLED": 48, "SURVIVED": 3}):

| id | file | verdict | failing rows | expected (spec/RED) | restore | desc |
|---|---|---|---|---|---|---|
| M1 | services/deviceFingerprint.ts | KILLED | A10 A2 A3 A6 A7 A8 hashes retries | A2,A3 | restored-sha-OK | getDeviceFingerprint returns the legacy composition |
| M2 | services/deviceFingerprint.ts | KILLED | A13 A2 A3 A6 | A3 | restored-sha-OK | the new raw string includes Device.osBuildId |
| M3 | services/deviceFingerprint.ts | KILLED | A13 A2 A6 A7 | A2 | restored-sha-OK | drop toLowerCase on the stable id |
| M4 | services/deviceFingerprint.ts | KILLED | A4 | A4 | restored-sha-OK | legacy composition lower-cases the nonce |
| M5 | services/deviceFingerprint.ts | KILLED | A6 | A6 | restored-sha-OK | fallback value stored in the cache |
| M7 | services/deviceFingerprint.ts | KILLED | A13 A7 | A7 | restored-sha-OK | Android branch calls IDFV |
| M8 | services/deviceFingerprint.ts | KILLED | A10 | A10 | restored-sha-OK | separate SecureStore read per hash (memo removed) |
| M9 | services/deviceFingerprint.ts | KILLED | A12 B11 | A12,B11 | restored-sha-OK | cutoff comparison inverted |
| M9b | services/deviceFingerprint.ts | KILLED | A8 retries | A8 | restored-sha-OK | no fallback: rejects with a new error instead of the original |
| M10 | services/requestContext.ts | KILLED | B4 | B4 | restored-sha-OK | interceptor overwrites an explicit header |
| M12 | services/requestContext.ts | KILLED | B11 B2 | B2 | restored-sha-OK | compare id not lower-cased |
| M13 | services/requestContext.ts | KILLED | B14b B5 E9 | B5,E9 | restored-sha-OK | consent header sent without a current record |
| M14 | services/authService.ts | KILLED | B8 I4 | B8,I4 | restored-sha-OK | legacy window check removed |
| M15a | services/requestContext.ts | KILLED | B14a | B14a | restored-sha-OK | device builder failure throws through |
| M15b | services/requestContext.ts | KILLED | B14b | B14b | restored-sha-OK | consent builder failure throws through |
| M15c | services/authService.ts | KILLED | B13 B14c I3 I5 | B14c,I3 | restored-sha-OK | legacy builder failure throws through |
| M16 | services/requestContext.ts | KILLED | B10 | B10 | restored-sha-OK | headers logged via console.log |
| M17 | services/requestContext.ts | KILLED | B1 B13 B14a B14b B14d B7 B9 | B9 | restored-sha-OK | capabilities header sent while empty |
| M18 | services/api.ts | KILLED | C2 | C2 | restored-sha-OK | camera retry sends Authorization only (base line) |
| M19 | services/api.ts | KILLED | C2 C5 | C2 | restored-sha-OK | camera retry mints a new id |
| M20 | services/api.ts | KILLED | D2 D4 | D2,D4 | restored-sha-OK | REST compare (SSE fallback) mints a new id |
| M21 | services/api.ts | KILLED | D3 D4 | D3 | restored-sha-OK | returned compareRequestId differs from the sent id |
| M22 | services/aiConsent.ts | KILLED | E9 | E9 | restored-sha-OK | consent memo not invalidated by recordAiConsent |
| M23 | services/aiConsent.ts | KILLED | E9 | E9 | restored-sha-OK | consent memo not invalidated by clearAiConsent |
| M24 | services/aiConsent.ts | SURVIVED | - | E9 | restored-sha-OK | consent memo ignores the account |
| M26 | services/requestContext.ts | SURVIVED | - | B15 | restored-sha-OK | consent header for a signed-out device |
| M27 | utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK | resolveResetAt accepts past times |
| M28 | utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK | 48 h bound removed |
| M29 | utils/resetTime.ts | KILLED | F3 | F3 | restored-sha-OK | precedence swapped (resets_at before the retry fields) |
| M30 | utils/resetTime.ts | KILLED | F2 F5 | F5 | restored-sha-OK | 12-hour clock |
| M30b | utils/resetTime.ts | KILLED | F5 | F5 | restored-sha-OK | truncation instead of rounding |
| M31 | utils/resetTime.ts | SURVIVED | - | G4 | restored-sha-OK | monthly state renders the daily time |
| M32 | screens/PaywallScreen.tsx | KILLED | G2 | G2 | restored-sha-OK | the daily resets line always uses the resets_at copy |
| M33 | screens/HomeScreen.tsx | KILLED | G9 G9b | G9 | restored-sha-OK | pill resets node rendered when absent |
| M36 | services/requestContext.ts | KILLED | B2b | B2b | restored-sha-OK | v4 check removed in newCompareRequestId |
| M37 | utils/resetTime.ts | KILLED | G11 | G11 | restored-sha-OK | the sheet prefers initialUsage over the fetched status |
| M38 | screens/HomeScreen.tsx | KILLED | G9b | G9b | restored-sha-OK | pill renders the raw resetsAt without resolveResetAt |
| M40 | services/requestContext.ts | KILLED | B16 | B16 | restored-sha-OK | device-id read not bounded at 1,000 ms |
| M41 | services/api.ts | KILLED | B12 B18 | B18 | restored-sha-OK | context headers on every request (marker ignored) |
| M44 | services/sentry.ts | KILLED | B19 | B19 | restored-sha-OK | Sentry legacy header name not added |
| M44b | services/sentry.ts | KILLED | B19 | B19 | restored-sha-OK | Sentry device header name not added |
| M45 | hooks/useComparisonCounter.ts | KILLED | G7b | G7b | restored-sha-OK | hook drops a status without used.lifetime |
| M46 | hooks/useComparisonCounter.ts | KILLED | G7 | G7 | restored-sha-OK | hook ignores counted_scope |
| M47 | utils/resetTime.ts | KILLED | G5b G6 | G5b,G6 | restored-sha-OK | open / unknown sheet states ignore the scope |
| M48 | services/api.ts | KILLED | C6 | C6 | restored-sha-OK | camera compare id not exposed |
| M49 | screens/HomeScreen.tsx | KILLED | L1 | L1 | restored-sha-OK | Link mode sends no compare id |
| M50 | screens/HomeScreen.tsx | KILLED | L1 | L1 | restored-sha-OK | Link mode request not on the metered allowlist (id kept) |
| M51 | services/usageService.ts | KILLED | B1 B11 B13 B14a B14b B16 B4 B5 B8 | B1 | restored-sha-OK | /usage/status not marked |
| M52 | services/authService.ts | KILLED | B11 B12 | B12 | restored-sha-OK | legacy header not sent at register |
| M53g | services/authService.ts | KILLED | I1 | I1 | restored-sha-OK | legacy header not sent on the Google sign-in |
| M53a | services/authService.ts | KILLED | I1 | I1 | restored-sha-OK | legacy header not sent on the Apple sign-in |

Adversary probes (X series + M24full / M26full on the FULL suite, the 4 nativeBundle.w37 drift nodes excluded from the kill test; + M31p; counts {"SURVIVED": 12, "KILLED": 16}):

| id | file | verdict | failing rows | expected (spec/RED) | restore | desc |
|---|---|---|---|---|---|---|
| M24full | services/aiConsent.ts | SURVIVED | - | E9 | restored-sha-OK | consent memo ignores the account (FULL suite) |
| M26full | services/requestContext.ts | SURVIVED | - | B15 | restored-sha-OK | consent header guard for a signed-out device dropped (FULL suite) |
| M31p | screens/PaywallScreen.tsx | KILLED | G4 | G4 | restored-sha-OK | monthly state renders the daily time (effective form on the GREEN bytes) |
| X1 | services/api.ts | KILLED | D1 D2 D3 D5 | D1 | restored-sha-OK | SSE request drops the context headers |
| X2 | services/api.ts | KILLED | B14d | B14d | restored-sha-OK | REST compare / SSE fallback keeps the id but drops the metered marker |
| X3 | services/api.ts | KILLED | C1 C2 C3 C6 | C1 | restored-sha-OK | camera attempt 1 drops the context headers |
| X4 | services/aiConsent.ts | SURVIVED | - |  | restored-sha-OK | consent memo generation guard removed (stale read memoised after a concurrent Agree) |
| X5 | services/requestContext.ts | SURVIVED | - |  | restored-sha-OK | an empty explicit header counts as present |
| X6 | services/requestContext.ts | SURVIVED | - |  | restored-sha-OK | only-if-absent check becomes case-sensitive |
| X7 | services/deviceFingerprint.ts | KILLED | A6 retries | DFT W3-3 | restored-sha-OK | a failed nonce read is replayed for the process (W3-3 C5 regression) |
| X8 | services/deviceFingerprint.ts | KILLED | A6 retries | DFT W3-3 | restored-sha-OK | a failed identity read is replayed for the process |
| X9 | services/deviceFingerprint.ts | SURVIVED | - |  | restored-sha-OK | a failed legacy read is replayed for the process |
| X10 | services/authService.ts | SURVIVED | - |  | restored-sha-OK | legacy header shape check removed |
| X11 | services/requestContext.ts | SURVIVED | - |  | restored-sha-OK | consent version shape check removed |
| X12 | services/requestContext.ts | SURVIVED | - |  | restored-sha-OK | device header shape check removed |
| X13 | services/api.ts | KILLED | T1 T12 T17b T19 T8 T9 | U13C T1 | restored-sha-OK | camera result field set even without an id (null) |
| X14 | services/deviceFingerprint.ts | KILLED | A10 A13 A2 A4 A5 A6 A7 A8 coalesces creates hashes retries returns reuses | A5 | restored-sha-OK | nonce never read back: a new id every process |
| X17 | utils/resetTime.ts | KILLED | G3 | G1,G3 | restored-sha-OK | the daily sheet state also requires a daily scope |
| X18 | screens/HomeScreen.tsx | KILLED | G8 | G8 | restored-sha-OK | pill a11y label never switches to a11yResets |
| X19 | utils/resetTime.ts | KILLED | G5b G7 | G5b,G6,G7 | restored-sha-OK | monthly / lifetime scopes treated as daily |
| X20 | utils/resetTime.ts | KILLED | G5 G7 G7b |  | restored-sha-OK | device_daily scope not treated as daily |
| X21 | utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK | relative retry window unbounded |
| X22 | utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK | non-integer retry seconds accepted |
| X24 | services/authService.ts | SURVIVED | - |  | restored-sha-OK | legacy header sent without a resolved X-Device-Fingerprint |
| X28 | screens/PaywallScreen.tsx | KILLED | G5 | G5 | restored-sha-OK | open sheet state never shows the time |
| X29 | screens/PaywallScreen.tsx | KILLED | G5 | G5 | restored-sha-OK | unknown sheet state never shows the time |
| X30 | services/requestContext.ts | SURVIVED | - | E9 | restored-sha-OK | request path bypasses the consent memo (falls back to the jest-only branch) |
| X31 | services/aiConsent.ts | SURVIVED | - |  | restored-sha-OK | a signed-out request does not drop the memo |

## 3. Runtime truth of the GREEN report / CLAUDE.md row / PR body claims (each checked against the GREEN code at 3f990a69)

- Headers at every call site (GC-11): /usage/status (usageService.getUsageStatus, marked), REST GET /text/compare (the ONE api.get call site in streamComparison, shared by the default transport and the SSE fallback, marked with the attempt id), POST /text/compare (compareTextPair, 0 callers, marked with its own id), /url/compare (HomeScreen Link mode, marked + ref), the SSE request (buildContextHeaders + Object.assign), camera attempt 1 (Object.assign) and the U13c retry ({Authorization: new, ...contextHeaders}, same id): TRUE. No other client caller of these routes exists (grep of src). The fallback's device/consent headers are proven by composition: D2 (fallback = same call site, same id) + B14d / restCompareSent (that call site through the REAL interceptor); X2 (marker dropped, id kept) checks it directly (section 2).
- Unmarked requests take the base path (interceptor: context = null, no await added): TRUE. Register / social keep {X-Device-Fingerprint} as today plus the legacy header: TRUE. Share: no new header, new body VALUE (m3).
- Device id: new = sha256(trim(lower(nonce))), never osBuildId; fallback IDFV / ANDROID_ID only when readNonce() throws (that also covers a setItemAsync or randomUUID throw on first launch: wording "when SecureStore throws" is slightly narrow, harmless), never cached / persisted; original error rethrown; legacy = base composition byte-identical (diffed against git show e7c81956), own cache, shares ONE nonce read; failed reads are not replayed (X7 / X8 / X9 in section 2): TRUE.
- Legacy window: LEGACY_FINGERPRINT_HEADER_UNTIL_MS = Date.UTC(2027, 2, 31, 21, 0, 0) = 2027-04-01T00:00+03:00; strict `<`; checked per call; legacy only beside a resolved X-Device-Fingerprint, only at register + the two social sign-ins (read after the native sheet): TRUE (I1-I5, B8, B12, M14 / M52 / M53g / M53a killed).
- Consent: per account, no device copy, memo dropped by record / clear (finally, after the write) and by a signed-out request, generation guard against a racing read; storage throw not memoised: TRUE in code; the account key is unpinned (MAJ-1); the generation guard and the signed-out drop are probed as X4 / X31.
- Reset: precedence retry_after_seconds > retry_after > resets_at (GC-2), relative 1..172800 whole seconds, absolute strictly after now and <= now+48 h, HH:MM rounded, device-local offset at that instant; sheet daily always / open+unknown only for daily|device_daily / monthly never (M31 equivalent, M31p), fetched first; pill only for a daily counted_scope via the hook (GC-5): TRUE.
- Error-handler mapping (live backend, read-only): every USAGE_LIMIT 429 detail today is {error, code, tier, remaining} (text_routes 625 / 842 / 1029 / 1413, url_routes 95, image_routes 236 / 332) and http_exception_handler flattens it to {success, error, code, request_id} (+ retry_after_seconds / Retry-After ONLY when detail.retry_after is a positive int); getUsageLimitDetail hands the unified envelope to the sheet as initialUsage. So TODAY no reset field reaches the client: the sheet keeps resets_daily / null / resets_unknown and the pill nothing, byte for byte (GREEN claim TRUE); S81-09's retry_after lands as top-level retry_after_seconds, which the client reads first.
- Contract freeze (PLAN section 0) / flag-OFF identity: no backend file in the diff (git diff --stat: CLAUDE.md + SmartCompareApp only); the client only ADDS optional reads (resets_at, counted_scope, scope, retry_after*, used.lifetime optional) and headers; the live backend reads x-device-fingerprint only in the dark anon gates (ENABLE_ANON_USAGE_GATE, anonymous callers only) and in register / social as today; the S81-05 binder is flag-gated. Backend parser probe in my scratch worktree (python -B, stdlib leaf loaded by path, no pytest): parse_consent_version('2') = 2, parse_device_fingerprint(64 lower hex) ok (upper -> None; the client sends lower), parse_compare_request_id(lower v4) ok: every client-built shape is accepted. llm_router MIN_CONSENT_VERSION = 3 while AI_CONSENT_VERSION = 2: the header changes no routing until S81-12's bump (cross-unit, expected).
- Billing R-A3: untouched (no backend change; the client's local increment path is unchanged).
- CLAUDE.md row (GC-6): placed after the S81-15 row, before ## Tests; no device-mirror sentence; legacy only at register + the two social sign-ins; "ships only ... after the owner's DATED ledger line of ENABLE_LEGACY_FINGERPRINT_READER=true on web (item 32)": TRUE; precision notes m5 / m8.
- PR body: E1 / E2 / E4 re-pins match the diff (titles kept); E3 none (u13c green in every full run here); 48-suite / R-S08-11 numbers not re-run (GREEN's); precision note m3.

## 4. Prove-nothing rows (at the GREEN bytes)

- E9, its account-switch step (`getSavedUser -> { id: USER_B }` after the `null` step): cannot tell an account-keyed memo from an account-ignoring one, because the preceding signed-out step drops the memo (MAJ-1; M24 / M24full survive).
- B15, its signed-out half: runs world({consent:'global'}), so it proves only the else-branch early return, which is jest-only code (m4); the production null-user path is covered by E9's null step instead. M26 / M26full survive (equivalent).
- G4 as a guard of sheetResetClock's monthly rule: proves nothing at these bytes (PaywallScreen's monthly branch never consults the helper; M31 equivalent); it does pin the observable monthly copy (M31p KILLED).
- PIN rows that no mutant here (51 spec + the X series) or in RED Appendix B kills: A9, A9b, B6, C4, E2, E3, E5, E6, E7, E8, E10, H3 (A5 is killed by X14 if section 2 says so). These pin BASE behaviour of code the unit leaves alone or only refactors (per-account keys, version bump, no-user no-write, delete-one-record, the {version, at} read shape, Authorization unchanged, the camera request shape, key-set parity): regression guards, NOT vacuous; listed for completeness.

## 5. Procedure notes and deviation from the generic adversary template

- The generic line "Never edit the worktree; all probes and mutants in YOUR OWN scratch worktree" conflicts with GC-11 (binding, gate over rulings): "the section-6 mutants re-applied on byte copies IN PLACE in the real worktree (restored and sha-verified under .qa-mutation.lock; a scratch worktree has NO node_modules, so jest runs only in sc-s81-s08)". I followed GC-11 for every jest-measured mutant: .qa-mutation.lock (label + time) created before the first mutant and deleted after the last restore; a byte copy of each target file (bytecopies/) before its first mutant; an exact-string edit matching once (CRLF-aware); the jest run; the file rewritten from the in-memory original and sha256-compared after EVERY mutant (restored-sha-OK on every row); a final restore check per file. Before each mutant a probe counted other node.exe jest processes (0 every time, wait=0 s), so no concurrent jest saw a mutated file. The scratch worktree was used for the backend parser probe; memo_probe.js read the worktree only (no write).
- Harness incident (mine, no effect): the first mutate.py launch (08:56) had a process probe that matched its own PowerShell command line and would have waited 300 s per mutant; I stopped my own python process at 08:58 BEFORE any mutant was applied (verified: sha256sum -c of the 11 target files all OK, git status = only my lock), fixed the probe (node.exe processes whose command line holds 'jest'), and re-ran from scratch.
- No pytest was run (the unit changes no backend file; the backend probe was a stdlib import by path, python -B, in the scratch worktree). No package manager, no npx, no git write in the real worktree; the junction untouched.

## 6. Every run (in order; tools by path from sc-s81-s08/SmartCompareApp through the junction: node v24.11.1, jest 29.7.0, tsc 5.9.3, coreutils timeout 8.32; node_modules/@babel/core + .bin/jest present at start and end)

- [jest] tag=adv-corr-red-head start=1793252877 end=1793252912 rc=0 elapsed=35s -> 9 suites, 87 passed / 87 (ON = the HEAD bytes).
- mutate.py spec run (09:01-09:28): 51 mutants, one jest --ci --json per mutant over the listed RED / pin files, 9-33 s each, restored-sha-OK x51, wait=0 s x51; tsv mut/spec.tsv.
- memo_probe.js (09:19, plain node, transpiled HEAD aiConsent.ts + requestContext.ts, head_bytes_ok=true): HEAD b_first_request=null, M24 b_first_request="2", b_record_current=false.
- backend parser probe (scratch worktree, python -B, stdlib leaf by path; no pytest): consent '2'->2, '3'->3; device 64 lower hex ok, upper None; compare id lower v4 ok, upper normalised.
- mutate.py X run (09:28-09:47): 28 mutants incl. M24full / M26full on the FULL suite (each: 388 suites, 3811 tests, 3781 passed, 4 failed = d5 / k2 / k4 / k5 only), restored-sha-OK x28, wait=0 s x28; tsv mut/x.tsv.
- [jest] tag=adv-corr-full-head start=1793256450 end=1793256532 rc=1 elapsed=82s -> Test Suites: 1 failed, 3 skipped, 384 passed, 385 of 388; Tests: 4 failed, 13 skipped, 13 todo, 3781 passed, 3811 total; Snapshots 42 / 42. The 4 failures = nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes); api.cameraAuthRetry.u13c 20 / 20 (E3: no move). 3781 = 3694 + 87: GREEN's figure CONFIRMED on clean HEAD bytes (sha-verified before the run).
- [jest] tag=adv-corr-red-at-base rc=1 elapsed=34s (base_revert.py: the 12 changed src files rewritten from git show e7c81956, the 2 new files removed, the nine RED files run, every file restored from memory and sha-compared: restore mismatches []) -> failed=54 passed=33, non-assert failures 0, suite errors 0 (OFF = the base bytes): GREEN's / RED's base record CONFIRMED.
- Not re-run by me (GREEN's records stand, nothing in my findings depends on them): tsc / eslint, the 48-suite set, the R-S08-11 seven, the in-band order pairs, the backend 30-file comm set (no backend file in the diff).

## 7. State at hand-off

- sc-s81-s08: HEAD 3f990a6908be12312fdc8a440a875ddfa8d0d6b5 (unchanged), branch feature/s81-s08-client-first-ota, `git status --short` EMPTY; the 11 mutated files sha256-equal to pre_mut_sha.txt (= the GREEN report's "after" column); types.ts / en.json / ar.json equal the GREEN after values; requestContext.ts and resetTime.ts present with their GREEN sha; no .qa-mutation.lock; the junction intact.
- RED files re-hashed at the end: all nine equal the frozen sha256 (ab242206..., c8b489fb..., 66f3ffb5..., c57792aa..., e76fa815..., 5ab229ee..., b5527c05..., d44e06de..., f01bd05b...).
- Scratch worktree <scratchpad>/S81-08_adv_correctness removed with `git worktree remove --force` (0 entries in `git worktree list`, gone from disk); it never held a junction.
- No pytest started; no process of mine left running (the first harness process was stopped by me at 08:58 before applying anything); no git write in the real worktree; nothing pushed.

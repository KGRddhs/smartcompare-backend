
## Orchestrator rulings (BINDING - supersede the review corrections and the body; 2026-10-03 17:40)

Review verdict APPROVED_WITH_CORRECTIONS; corrections 1-11 are accepted as written and bind the RED and GREEN agents. Rulings on the open questions:

- **UR1 (Q1 = A).** A second 401 after a successful refresh is thrown by the service as the existing 401 error; ResultsScreen shows a camera-only sign-in state built from the existing i18n keys (title common.signInRequired, CTA auth.signIn) reusing the existing empty-state return (correction 8: no new header, no new ArrowLeft); the CTA awaits clearSession() and then calls emitSessionInvalid() (correction 10 pins the order). sessionEvents.ts gets the comment-only update about the second emission site.
- **UR2 (Q2).** A failed refresh, transient or dead, shows the same sign-in state (correction 11: no performRefresh edit).
- **UR3 (Q3, correction 1).** One shared IDENTIFY_TIMEOUT_MS budget: the refresh WAIT is raced against controller.signal (the P-A3 shape at api.ts:169-170); the signal is never passed into the refresh; an abort during the wait maps to TIMEOUT with no retry; the listener is removed when the race settles; no unhandled rejection.
- **UR4 (Q4, correction 5).** Any 401 triggers the single refresh, regardless of body shape; a 403 never does (correction 4).
- **UR5 (Q5).** No server-side revocation from the CTA.
- **UR6 (files).** RED writes only the two new test files of section 5 (the service file and the screen file) and nothing else; GREEN touches only src/services/api.ts (identifyFromImages and its helpers), src/screens/ResultsScreen.tsx (the auth state), src/services/sessionEvents.ts (comment only); the aiDispatchFence (exactly one /image/identify literal inside identifyFromImages) and bootOptimistic (the zero-argument getOrStartRefresh) pins stay green; no snapshot, no i18n key, no app.json / eas.json / package.json / lock change.
- **UR7 (gates).** The RED counts of the review (service file 20 nodes: 13 RED + 7 PIN; screen file 4: 2 RED + 2 PIN); G1, G2 and G2b (the 19 ResultsScreen suites), G3 the FULL suite with totals derived from base (357 passed of 360 suites, 3,485 tests, 42 snapshots, plus the 24 new nodes), tsc, eslint by path, gate_untouched.py; mutants M1-M23 as corrected.
- **UR8 (shipping).** OTA-capable; must be in the store binary; after merge the preview OTA from main is the tester lever (npm ls first).

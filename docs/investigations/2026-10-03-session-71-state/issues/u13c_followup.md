=== TITLE: Camera 401 retry: five unpinned behaviours and the camera upload that outlives the Results screen
=== LABELS: mobile,tests
## Context
U13c (PR #U13PR) added the one refresh-and-retry on a 401 to `identifyFromImages` and the camera-only sign-in state. Two Opus adversaries measured these gaps; the shipped code is correct for each (the two U13c test files are frozen, so the pins need a new file).

## Test-strength gaps (mutants that pass today)
1. **Race listener removal** (ruling UR3): dropping both `removeEventListener` calls in `waitForIdentifyRefresh` passes 24/24. Pin: count the `abort` listeners on the captured signal after T1 and T4 settle (Node `events.getEventListeners(signal, 'abort')`), expect 0.
2. **Abort during the first 401 body read**: removing the already-aborted-at-entry branch passes. Pin: a 401 whose `text()` resolves only after the deadline must give TIMEOUT within `IDENTIFY_TIMEOUT_MS` and no second fetch.
3. **Auth state through a new top-level return** without a header passes (correction 8 is fenced only by the ArrowLeft count). Pin: the auth state renders inside the existing empty-state container (same testID parent / same style object).
4. **Bare 401 at the screen level**: making the screen show sign-in only for the `AUTH_REQUIRED` envelope passes; T19 pins the service only. Pin: a 401 with `{error: 'Unauthorized'}` through the camera path shows the sign-in state.
5. **Extra option on the retry fetch** (`credentials: 'include'`) passes. Pin: `Object.keys(fetch.mock.calls[1][1])` equals `['method','body','headers','signal']`.

## Pre-existing design limit, measured by the auth-flow adversary
`identifyFromImages` is not aborted when ResultsScreen unmounts (the `cancelled` flag only suppresses setState), so an upload can stay in flight for up to 120 s. A late 401 after the user signed in again refreshes and retries under the NEW session (metered, saved to history, result discarded), and a late 401 after a dead-session refresh clears and emits again (idempotent for App's listener). The axios replay has the same property. Fix: pass an `AbortSignal` into `identifyFromImages` and abort it in the effect cleanup; this changes the exported signature and a fifth ResultsScreen site, so it is its own unit.

## Device check owed (after the next preview OTA)
The React Native multipart re-send of the same FormData is proven in jest only (Node FormData, mocked fetch, a near-device whatwg-fetch transport); on a phone: an expired token on the camera gives one silent refresh then the result; a dead session gives the sign-in state whose CTA lands on Auth.

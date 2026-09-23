# W3-4 — the referral screens' escape hatches reset to a route the navigator does not have

## 1. Header

| | |
|---|---|
| unit | **W3-4 unauth reset -> Auth** (full-review W3 table, `docs/investigations/2026-09-06-full-review.md:131`) |
| finding | `MB-FLOWS-STATE-04` (verified.json `/findings/352`, P1, `measured`, verify CONFIRMED + second-vote CONFIRMED) |
| OTA class | **OTA-safe** — client only (two screens + one new pure helper + tests). No `app.json`, no native dep, no backend half, no flag, no migration. |
| base SHA | `ed75dc70` (`origin/main`; worktree `C:/Users/SynAckITPC/Documents/AI/sc-w3-reset`) |
| installed libs measured | `@react-navigation/native` **7.2.4** (pin `^7.1.28`), `/core` **7.17.4** (dep `^7.17.4`), `/routers` **7.5.5** (dep `^7.5.5`, transitive), `/native-stack` **7.15.0** (pin `^7.12.0`); `typescript` **5.9.3** (pin `~5.9.2`, `tsc -v` = "Version 5.9.3"); `jest` 29.7.0, `ts-jest` 29.4.9; node v24.11.1 |
| plan line anchors | `ReferralLandingScreen.tsx:118/160` — **unchanged** at ed75dc70 (reset calls open at `:118` and `:160`, payload lines `:120` and `:162`). `InviteeQuizScreen.tsx:275` — **moved to `:274`** (six commits touched the file since 76ace90; `git show 76ace90:…InviteeQuizScreen.tsx` has the reset at `:275`, HEAD at `:274`; the line's text is byte-identical). |

## 2. Scope correction — what is ALREADY on main

The plan lists ONE red test for W3-4: *"router-level test with the unauth route-name set: reset to the chosen route is handled (RED: `'Main'` dropped)"*. Verified at ed75dc70: **still RED**, nothing to drop (§10, probe B: `unauth: reset->Main = NULL`). All three reset sites read verbatim at HEAD (§3).

Two things the plan row under-states, both measured, both kept in scope because they are the same defect at the same call sites:

* **There are THREE route-name sets, not two.** App.tsx's root navigator is a three-way ternary (`!isAuthenticated` → `needsPreferences` → authed). In the `needsPreferences` branch `'Main'` is ALSO absent (only `Onboarding` + the two hoisted screens), so a freshly-registered invitee who has not finished onboarding and re-enters via the deep link hits the same dead controls. The finding's `isAuthenticated ? 'Main' : 'Auth'` fix would still drop there (probe B: `needsPreferences: reset->Auth = NULL`). The fix below resolves the target from the mounted route names, which covers all three.
* **The back arrow is in the finding, not in the plan row.** `MB-FLOWS-STATE-04`'s title ends "…and on a cold-start deep link the back arrow is dead too"; its fix text names `canGoBack() ? goBack() : reset(<branch root>)`; both verifiers measured `goBack` → `null` on the one-route deep-link state. Measured again here (probe 1/B: `goBack on the 1-route deep-link state: NULL` for all three sets). It is one guard at two sites (`ReferralLandingScreen.tsx:170`, `InviteeQuizScreen.tsx:92`) and is included. If the orchestrator wants the narrowest possible unit, drop red test 3 and the two `backOrExit` edits — nothing else depends on them.

Already green on main and NOT re-filed: nothing from this finding has landed. Related-but-different items verified so as not to re-file: `App.distinctRouteNames.test.ts` (F-S1.5m — the hoisting of these two screens out of the auth branches; it is what makes them reachable in every branch and is the precondition for this defect); the M13 referral row (Auth.Register resolution) which the verifier noted "now resolves".

## 3. The defect — measured

### The three call sites at ed75dc70

`SmartCompareApp/src/screens/ReferralLandingScreen.tsx:114-121` — the error card's ONLY control:
```tsx
            onPress={() => {
              // "Open Qaren" — drop the user into the main app flow. If they're
              // unauth they'll hit Auth; if they're authed they'll see Home.
              navigation.reset({
                index: 0,
                routes: [{ name: 'Main' as never }],
              });
            }}
```
`ReferralLandingScreen.tsx:155-164` — "Maybe later" (`testID="referral-cta-skip"` at `:252`):
```tsx
  const handleSkipPath = () => {
    // Cool path: drop the invitee into the main app flow. They'll hit
    // Auth (unauth) or Main (authed); the invitee credit is applied
    // server-side at signup time so they can revisit the comparison
    // from History after registering.
    navigation.reset({
      index: 0,
      routes: [{ name: 'Main' as never }],
    });
  };
```
`ReferralLandingScreen.tsx:169-171` — the back arrow:
```tsx
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.headerButton}
```
`SmartCompareApp/src/screens/InviteeQuizScreen.tsx:272-275` — "skip signup" on the result view:
```tsx
            <TouchableOpacity
              onPress={() =>
                navigation.reset({ index: 0, routes: [{ name: 'Main' as never }] })
              }
```
`InviteeQuizScreen.tsx:90-96` — back from question 1:
```tsx
  const handleBack = () => {
    if (step === 0) {
      navigation.goBack();
    } else {
      setStep(step - 1);
    }
  };
```
Both comments ("If they're unauth they'll hit Auth") describe what the authors believed `reset -> 'Main'` would do. It does not.

### The route sets the root navigator actually mounts (`App.tsx:384-508`)

```tsx
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!isAuthenticated ? (
          <>
            <Stack.Screen name="Auth">
              {(props) => <AuthNavigator {...props} onLoginSuccess={handleLoginSuccess} />}
            </Stack.Screen>
          </>
        ) : needsPreferences ? (
          <Stack.Screen name="Onboarding">
            …
          </Stack.Screen>
        ) : (
          <>
            <Stack.Screen name="Main">
            … Results, Legal, ContactUs, EditProfile, EditPreferences, OnboardingEdit, ScanCamera, Paywall …
          </>
        )}
        {/* Bundle E F-S1.5m … Both screens
            handle their own auth-state branching internally, so they
            don't need to live inside the conditional. … */}
        <Stack.Screen name="ReferralLanding" component={ReferralLandingScreen} />
        <Stack.Screen name="InviteeQuiz" component={InviteeQuizScreen} />
      </Stack.Navigator>
```
Extracted statically (same regex as `__tests__/App.distinctRouteNames.test.ts`, branches split on the ternary markers, hoisted tail = after the last `</>`), measured in probe 1 and probe B:

| branch | route names mounted |
|---|---|
| unauth (`!isAuthenticated`) | `["Auth","ReferralLanding","InviteeQuiz"]` |
| `needsPreferences` | `["Onboarding","ReferralLanding","InviteeQuiz"]` |
| authed | `["Main","Results","Legal","ContactUs","EditProfile","EditPreferences","OnboardingEdit","ScanCamera","Paywall","ReferralLanding","InviteeQuiz"]` |

`'Main'` exists in exactly one of the three. The App.tsx:496-498 comment "Both screens handle their own auth-state branching internally" is **false at HEAD**: `grep -n "authService\|getToken\|isAuthenticated" src/screens/ReferralLandingScreen.tsx src/screens/InviteeQuizScreen.tsx` returns nothing (§10). Neither screen reads auth state.

### What `reset` to an unknown route name does on the INSTALLED version (measured, not read from docs)

`@react-navigation/routers@7.5.5`, `src/StackRouter.tsx:744-745` falls through to `BaseRouter`, whose RESET branch (`src/BaseRouter.tsx:45-57`) is:
```ts
      case 'RESET': {
        const nextState = action.payload as State | PartialState<State>;
        const routeNamesSet = new Set(state.routeNames);
        if (
          nextState.routes.length === 0 ||
          nextState.routes.some(
            (route: { name: string }) => !routeNamesSet.has(route.name)
          )
        ) {
          return null;
        }
```
`@react-navigation/core@7.17.4`: `useOnAction.tsx:83` calls `router.getStateForAction`; a `null` result ends in `return false` (`:151`); `useNavigationHelpers.tsx:49-56`:
```ts
    const dispatch = (op: Action | ((state: State) => Action)) => {
      const action = typeof op === 'function' ? op(getState()) : op;
      const handled = onAction(action);
      if (!handled) {
        onUnhandledAction?.(action);
      }
    };
```
and the container's default handler (`BaseNavigationContainer.tsx:401-441`):
```ts
    const defaultOnUnhandledAction = useLatestCallback(
      (action: NavigationAction) => {
        if (process.env.NODE_ENV === 'production') {
          return;
        }
        …
        let message = `The action '${action.type}'${payload ? ` with payload ${JSON.stringify(action.payload)}` : ''} was not handled by any navigator.`;
        …
        message += `\n\nThis is a development-only warning and won't be shown in production.`;
        console.error(message);
```
So the answer to the brief's question: **it does not throw, in dev or prod; it does not change state; the screen the user is on stays exactly as it was.** Dev builds print `The action 'RESET' with payload {"index":0,"routes":[{"name":"Main"}]} was not handled by any navigator.` to the console; release builds (what the `preview` channel runs) return before building the message. In jest, `__tests__/setup.ts:15` replaces `console.error` with a no-op, so even the dev message is invisible to a test that does not assert on the router result directly — which is why the red test must call the router, not watch the console.

**Probe output (probe B, installed router lowered to CJS and run in-process; probe 1 = same via plain node ESM, identical verdicts):**
```
unauth: reset->Main = NULL
unauth: reset->Auth = handled
unauth: reset->Onboarding = NULL
unauth: goBack on 1-route state = NULL
needsPreferences: reset->Main = NULL
needsPreferences: reset->Auth = NULL
needsPreferences: reset->Onboarding = handled
needsPreferences: goBack on 1-route state = NULL
authed: reset->Main = handled
authed: reset->Auth = NULL
authed: reset->Onboarding = NULL
authed: goBack on 1-route state = NULL
```
The cold-start deep-link state is a ONE-route stack — real `getStateFromPath` on the App.tsx linking config (probe 1):
```
getStateFromPath("c/abc123?ref=QR-ABCDEF") = {"routes":[{"name":"ReferralLanding","params":{"share_token":"abc123","ref":"QR-ABCDEF"},"path":"c/abc123?ref=QR-ABCDEF"}]}
```
so `goBack` is `null` too and `navigation.canGoBack()` (computed at `useNavigationHelpers.tsx:78-87` from the same `getStateForAction(goBack)` plus the parent chain — there is none at the root) returns `false`.

### Consequence, stated plainly

A logged-out invitee cold-starting on `qaren://c/<token>?ref=<code>` (reachable today through the `qaren://` catch-all intent filter; the default path for every invitee once `qaren.app` DNS is attached — MB-FLOWS-STATE-01) has: a back arrow that does nothing, a "Maybe later" that does nothing, and — when `resolveInvite` 404s/503s — an error card whose only control does nothing. The one working exit is Take the quiz → Register. Nothing is logged in the release build.

### The `as never` casts hide the type error that would have caught this

Probe 2 (tsc 5.9.3 against the real `NativeStackScreenProps<RootStackParamList,'ReferralLanding'>['navigation']`):
```
../.qa-w3b/probes/asNever.probe.ts(15,43): error TS2322: Type '"NotARoute"' is not assignable to type 'keyof RootStackParamList'.
tsc exit=2
```
Only the deliberately-wrong line errored. `reset({ routes: [{ name: 'Main' }] })`, `'Auth'`, `'Onboarding'` and `navigation.getState().routeNames` all type-check **without** a cast. The casts are unnecessary today and defeat the only static check on the route name; they go.

## 4. The fix — MINIMAL design

Client-only, unflagged by nature, OTA-gated. Backward-compatible with the backend on main (no network call is added, changed or removed).

### Principle
Resolve the exit target from what the navigator has actually mounted — `navigation.getState().routeNames` — at press time. Not from `authService.getToken()` (a second source of truth that can disagree with App state: `initializeAuth` failing leaves a token on disk and `isAuthenticated=false`), and not from a static `initialRouteName` in the linking config (it would fix `goBack` for the unauth branch only; `StackRouter.getRehydratedState` at `src/StackRouter.tsx:209-210` filters out route names the branch does not mount, so it silently does nothing for the other two — and it does not fix `reset` at all). `getState()` is synchronous, is the navigator's own state (`useNavigationCache.tsx:78-101` spreads the navigator helpers, `getState` included, into every screen's `navigation` prop), and `routeNames` is refreshed on every branch flip (`useNavigationBuilder.tsx:639-651`: `!isArrayEqual(state.routeNames, routeNames)` → `router.getStateForRouteNamesChange`). The one documented caveat — "`getState` should never be called during render" (`useNavigationHelpers.tsx:105-110`) — does not apply: both call sites are press handlers.

### Files to touch

1. **NEW `SmartCompareApp/src/utils/branchRoot.ts`** (pure, no React, no RN import so it is trivially testable):
   ```ts
   import type { NavigationProp } from '@react-navigation/native';
   import type { RootStackParamList } from '../types';

   export type BranchRoot = 'Main' | 'Onboarding' | 'Auth';

   /** The root screen of whichever branch App.tsx's root navigator has mounted. */
   export function resolveBranchRoot(routeNames: readonly string[]): BranchRoot {
     if (routeNames.includes('Main')) return 'Main';
     if (routeNames.includes('Onboarding')) return 'Onboarding';
     return 'Auth';
   }

   type RootNav = Pick<NavigationProp<RootStackParamList>, 'getState' | 'reset' | 'canGoBack' | 'goBack'>;

   /** Leave the referral flow for the mounted branch's root. Never dispatches a route the navigator lacks. */
   export function exitToBranchRoot(navigation: RootNav): void {
     navigation.reset({ index: 0, routes: [{ name: resolveBranchRoot(navigation.getState().routeNames) }] });
   }

   /** Back if there is anything beneath us (in-app entry); otherwise exit (cold-start deep link). */
   export function backOrExit(navigation: RootNav): void {
     if (navigation.canGoBack()) navigation.goBack();
     else exitToBranchRoot(navigation);
   }
   ```
   The implementer picks the exact type import (`NavigationProp` from `@react-navigation/native` is a type-only import — jest never loads the ESM package for it, and `NativeStackScreenProps<…>['navigation']` is assignable to the `Pick`; verify with tsc, not by reading). Keep `'Auth'` as the fallback: it is the branch a navigator with no known root can only be in.

2. **`src/screens/ReferralLandingScreen.tsx`** — three edits, nothing else:
   * `:118-121` → `exitToBranchRoot(navigation)`; rewrite the `:114-116` comment to say what is now true (target = mounted branch root).
   * `:160-163` (`handleSkipPath`) → `exitToBranchRoot(navigation)`; fix the `:155-159` comment likewise.
   * `:170` → `onPress={() => backOrExit(navigation)}`.
   * Import the helper. **Do not** touch the `Linking` unused import at `:28` (pre-existing eslint warning, not this unit) and keep exactly ONE `<DirectionalIcon><ArrowLeft` site — `__tests__/rtl/directionalIconWiring.contract.test.ts:26-27` pins the count at 1 per screen.
3. **`src/screens/InviteeQuizScreen.tsx`** — two edits:
   * `:273-275` → `onPress={() => exitToBranchRoot(navigation)}`.
   * `:92` → `backOrExit(navigation)` (the `step === 0` branch only; `setStep(step - 1)` untouched).
   * Import the helper. Leave `handleSignup` (`:129-140`, `(navigation as any).navigate('Auth', …)`) alone — see §8.
4. **Tests** — the five screen suites' `mockNavigation` objects (`ReferralLandingScreen.test.tsx:98-102`, `ReferralLandingScreen.redesign.test.tsx:81-85`, `InviteeQuizScreen.test.tsx:94-98`, `InviteeQuizScreen.redesign.test.tsx`, `InviteeQuizScreen.matchScore.m18.test.tsx:86-90`) carry only `navigate/goBack/reset`. After the fix, `ReferralLandingScreen.redesign.test.tsx:177` (presses `referral-cta-skip`) and `InviteeQuizScreen.test.tsx:244-253` (presses Back at Q1) would throw `navigation.getState is not a function` / `navigation.canGoBack is not a function`. Add `getState: () => ({ routeNames: ['Auth', 'ReferralLanding', 'InviteeQuiz'] })` and `canGoBack: () => true` to those mocks (test-only edits; assertions unchanged — `:179` asserts only `reset` was called, `:253` asserts `goBack` once, both still true).
5. **NEW `__tests__/helpers/routerSandbox.ts`** — the loader that lets a test run the INSTALLED router (see §5, "why a helper").

### What does NOT change
* `App.tsx` — untouched. No `initialRouteName`, no linking change, no navigator change. (W3-6 and W3-15 both edit the linking config; keeping this unit out of App.tsx avoids a three-way merge on one object literal.) The false comment at `App.tsx:496-498` is called out in the PR body for whoever next edits that block; it is not edited here.
* `src/types/types.ts` — untouched; `RootStackParamList` already has `Main: undefined`, `Auth`, `Onboarding` (`:571-584`).
* The `Auth`/`Register` navigate at `InviteeQuizScreen.tsx:136-139`, the quiz submit path, the `resolveInvite` flow, i18n keys, testIDs, accessibility labels — all unchanged.
* No `package.json`, lockfile, `jest.config.js`, `babel.config.js` or `app.json` edit. (The helper needs `@babel/core` 7.29.0 and `@babel/plugin-transform-modules-commonjs` 7.28.6 — both installed; both transitive: the plugin is a dependency of the declared `babel-preset-expo` 54.0.10, and `@babel/core` is a peer of `babel-jest`, a dependency of the declared `jest`. `__tests__/helpers/w312BootSandbox.ts` already relies on transitive `@babel/core` + `metro-transform-plugins` the same way — precedent, not a new class of dependency.)

## 5. Red tests

**Why a helper.** The repo's jest cannot load the real router: `@react-navigation/*` ship `"main": "./lib/module/index.js"` (ESM — `import * as CommonActions from "./CommonActions.js"`), the packages' `exports` map exposes only `.` (no `/src` subpath), and `jest.config.js` `transformIgnorePatterns` does not allow-list `@react-navigation` (ts-jest would not transform `.js` even if it did). Measured (probe A): `require('@react-navigation/routers')` → `SyntaxError: Cannot use import statement outside a module`; `require('@react-navigation/native')` → `SyntaxError: Unexpected token 'export'`. That is why every existing suite `jest.mock`s `@react-navigation/native` with a factory (20 files) and why no test today exercises the router. `__tests__/helpers/routerSandbox.ts` reads `node_modules/@react-navigation/routers/lib/module/*.js`, lowers each with `@babel/core` + `@babel/plugin-transform-modules-commonjs` (`configFile:false, babelrc:false`), evaluates it with a `require` that resolves `./x.js` through the same loader and bare specifiers (`nanoid/non-secure`) through the real `require`. Measured working in probe B (`.qa-w3b/probes/routerSandbox.probe.test.ts`, ~30 lines of loader). The helper also exports `rootRouteNameSets()` — the App.tsx static extraction (§3 table) with a sanity assertion that the unauth set is exactly `['Auth','ReferralLanding','InviteeQuiz']`, the `needsPreferences` set exactly `['Onboarding','ReferralLanding','InviteeQuiz']`, and the authed set contains `'Main'` — so a drift in App.tsx's ternary shape fails loudly instead of silently extracting the wrong set (the first version of the probe did exactly that: keyed on the first `)}` after the authed branch and leaked four authed-only names into the hoisted tail; the `lastIndexOf('</>')` split is the corrected one).

### Red test 1 — `__tests__/navigation.branchRootExit.w34.test.tsx` (the plan's test, bound to the screens)
Renders each screen with the real component and a `mockNavigation` whose `getState()` returns one of the three route-name sets and whose `reset` records its payload; presses the control; feeds the recorded payload to the INSTALLED `StackRouter({}).getStateForAction(deepLinkState, CommonActions.reset(payload), { routeNames, routeParamList: {}, routeGetIdList: {} })` where `deepLinkState = router.getRehydratedState({ routes: [{ name: 'ReferralLanding'|'InviteeQuiz', params }] }, opts)` (the one-route cold-start stack `getStateFromPath` yields — probe 1).
* `it.each` over 3 sets × 3 controls:
  * ReferralLanding **skip** (`fireEvent.press(getByTestId('referral-cta-skip'))`, happy resolution mocked as in `ReferralLandingScreen.redesign.test.tsx:77-96`);
  * ReferralLanding **Open Qaren** (`mockResolveInvite.mockRejectedValueOnce(new FakeReferralError('not found','NOT_FOUND',404))`, then press `findByText('referrals.landing.openQaren')` — the error test at `ReferralLandingScreen.test.tsx:146-158` renders it but never presses it);
  * InviteeQuiz **skip signup** (drive the 4 questions + submit exactly as `InviteeQuizScreen.test.tsx:201-213`, then press `getByText('referrals.quiz.skipSignup')`).
* Assertions per cell: `reset` called exactly once; `payload.routes.length === 1`; **`router.getStateForAction(deepLinkState, reset(payload), opts) !== null`**; and `payload.routes[0].name === resolveBranchRoot(routeNames)`.
* **RED today, measured:** the recorded payload is `{ index: 0, routes: [{ name: 'Main' }] }` at every site (quoted source §3; `ReferralLandingScreen.redesign.test.tsx:179` confirms the press reaches `reset`), and `reset -> 'Main'` is `NULL` on the unauth and `needsPreferences` sets (probe B) → **6 of 9 cells red**. The 3 authed cells are green today and stay as regression pins (an implementer who hard-codes `'Auth'` turns them red — that is the point).
* Also in this file, a static guard: neither screen's source contains `as never` — RED today (3 occurrences: `ReferralLandingScreen.tsx:120,162`, `InviteeQuizScreen.tsx:274`).
* **Mutations that must redden it:** (a) hard-code any single literal → red on the other two sets; (b) revert to `'Main'` → 6 red; (c) `resolveBranchRoot` returning `'Auth'` unconditionally → red on authed + needsPreferences; (d) swapping `getState().routeNames` for an `authService` read → `getState` never called and the recorded payload no longer tracks the mounted set → red on at least one set (the mock's `getState` is the only source of the set); (e) deleting the router call from the test would make it decoration — the assertion on the router result is the load-bearing line, keep it.

### Red test 2 — `__tests__/utils/branchRoot.test.ts` (pure)
`resolveBranchRoot(['Auth','ReferralLanding','InviteeQuiz']) === 'Auth'`; `(['Onboarding','ReferralLanding','InviteeQuiz']) === 'Onboarding'`; `([ 'Main', …authed ]) === 'Main'`; `([]) === 'Auth'`; and `exitToBranchRoot` with a stub `{ getState: () => ({ routeNames }), reset: jest.fn() }` dispatches `{ index: 0, routes: [{ name: <expected> }] }` for each set. Additionally feed each dispatched payload to the installed router via the helper: non-null for all three sets (this is the plan's literal "router-level test built from the route-name set", without a render).
* **RED today:** module `src/utils/branchRoot` does not exist (expected, per the W3-12 ruling — "red because the module does not exist yet is expected, not a fourth defect").
* **Mutations:** `'Onboarding'` check before `'Main'` — still green (authed set has `OnboardingEdit`, not `Onboarding`) so that ordering is NOT load-bearing and the test must not pretend it is; `return 'Main'` always → red on two sets; drop the `index: 0` → the router still accepts it (`BaseRouter` does not check index on a stale reset), so do NOT assert on `index` as if the router required it — assert it as the screen contract only.

### Red test 3 — the back arrow (`__tests__/navigation.branchRootExit.w34.test.tsx`, second `describe`)
* ReferralLanding header back (`getByLabelText('common.back')` — with this suite's `t` mock the label may render as `common.back|Back`; match by regex `/^common\.back/` or use the label the existing suites use, `InviteeQuizScreen.test.tsx:251` uses `'common.back|'`): with `canGoBack: () => false` and `getState` = unauth set → `goBack` NOT called, `reset` called once with `routes[0].name === 'Auth'`, router-verified non-null. With `canGoBack: () => true` → `goBack` called once, `reset` not called.
* InviteeQuiz back at step 0: same two cases.
* **RED today, measured:** both sites call `navigation.goBack()` unconditionally (`ReferralLandingScreen.tsx:170`, `InviteeQuizScreen.tsx:92`); the `canGoBack:false` cells fail on `goBack` having been called and `reset` not. The `canGoBack:true` cells are green today (regression pins; `InviteeQuizScreen.test.tsx:244-253` already covers the InviteeQuiz one — do not duplicate its assertion, reference it).
* **Mutations:** remove the guard → red; invert it → red on both.

## 6. Preserve

| behaviour | proof |
|---|---|
| Authed user: "Maybe later" / "Open Qaren" / skip-signup still land on `Main` | red test 1's three authed cells (green today; router-verified) |
| In-app entry (something beneath us): back arrow still `goBack()`s, never resets | red test 3 `canGoBack:true` cells + existing `InviteeQuizScreen.test.tsx:244-253` ("Back from Q1 calls navigation.goBack (not setStep)") |
| Quiz CTA still navigates to `InviteeQuiz` with `invite_id/share_token/ref` | existing `ReferralLandingScreen.test.tsx:215-233` |
| Signup CTA still navigates `Auth → Register` with `invite_id` | existing `InviteeQuizScreen.test.tsx:201-223` — untouched code path |
| Exactly one `DirectionalIcon`-wrapped `ArrowLeft` per screen | existing `__tests__/rtl/directionalIconWiring.contract.test.ts:26-27` (count pinned at 1) |
| `InviteeQuizScreen.charCount` textAlign stays the bare physical `'right'` | existing `__tests__/rtl/textAlignLogical.contract.test.ts:141-145` |
| No phantom `scoring.products` read in InviteeQuiz | existing `__tests__/ResultsScreen.comparisonId.m18.test.ts:97` (static scan of the file) |
| Root navigator registers each screen name once | existing `__tests__/App.distinctRouteNames.test.ts` (App.tsx is untouched anyway) |
| Route names accepted by `reset` are checked by tsc (no `as never`) | the tsc gate itself + red test 1's static guard |
| `resolveInvite` error states render the same copy | existing `ReferralLandingScreen.test.tsx:146-170` |

## 7. Gates

Client only; no backend half ⇒ no pytest / ruff / comm gate.

1. **Red-first**: tests 1–3 fail for the measured reasons in §5 before any source edit (test 2 on missing module; test 1 on `NULL`/`'Main'`/`as never`; test 3 on unconditional `goBack`).
2. **Unit test files**: `__tests__/navigation.branchRootExit.w34.test.tsx`, `__tests__/utils/branchRoot.test.ts` (+ helper `__tests__/helpers/routerSandbox.ts`, not collected by `testMatch`).
3. **Neighbour suites** (every test that imports or scans a touched module — grep of `__tests__` and `src` for `ReferralLandingScreen|InviteeQuizScreen|branchRoot`), run by path, baseline measured at ed75dc70 = **10 suites / 79 tests passed**:
   `__tests__/ReferralLandingScreen.test.tsx`, `__tests__/ReferralLandingScreen.redesign.test.tsx`, `__tests__/InviteeQuizScreen.test.tsx`, `__tests__/InviteeQuizScreen.redesign.test.tsx`, `__tests__/InviteeQuizScreen.matchScore.m18.test.tsx`, `__tests__/ResultsScreen.comparisonId.m18.test.ts`, `__tests__/rtl/directionalIconWiring.contract.test.ts`, `__tests__/rtl/textAlignLogical.contract.test.ts`, `__tests__/components/ProgressBar.test.tsx`, `__tests__/App.distinctRouteNames.test.ts`.
   Command: `node node_modules/jest/bin/jest.js --ci <those paths>` from `SmartCompareApp`.
4. **tsc**: `node node_modules/typescript/bin/tsc --noEmit` — exit 0 at ed75dc70 (7.6 s); must stay 0 with the casts removed and the helper typed against `RootStackParamList`.
5. **eslint**: `node node_modules/eslint/bin/eslint.js src/utils/branchRoot.ts src/screens/ReferralLandingScreen.tsx src/screens/InviteeQuizScreen.tsx __tests__/helpers/routerSandbox.ts __tests__/navigation.branchRootExit.w34.test.tsx __tests__/utils/branchRoot.test.ts` — baseline on the two screens is exit 0 with **2 pre-existing warnings** (`InviteeQuizScreen.tsx:127:6 react-hooks/exhaustive-deps`, `ReferralLandingScreen.tsx:28:3 no-unused-vars 'Linking'`); neither is this unit's, neither may become an error, no new warnings. The helper's `require`/`new Function` lines need the same `eslint-disable-next-line` comments `w312BootSandbox.ts` carries.
6. **Full jest suite once** in the green phase (baseline 2,729 passed / 0 failed / 278 suites, 3 skipped, 44 snapshots at ece0fbbe — re-measure at the unit's base).
7. Fable review before commit. Agents never commit.

## 8. What this unit CANNOT do / Ahmed dependencies / device-only

* **Cannot reach a phone by itself.** Phones run `preview` from 97b5f15; this lands only with Ahmed's `eas update --branch preview --clear-cache` from main. Until then every invitee on the `qaren://c/…` path has the dead controls described in §3.
* **No Ahmed dependency for the code half.** No secret, store setting, migration, artwork or dependency change. (`qaren.app` DNS — MB-FLOWS-STATE-01 — is Ahmed's and is what turns this from "reachable via the catch-all intent filter" into "the default invitee path"; the verifiers' warning stands: fixing 01 without this makes it worse.)
* **Device-only verification** (post-OTA walkthrough, logged-OUT phone): cold-start `qaren://c/<valid token>?ref=<code>` → (a) back arrow → Login; (b) "Maybe later" → Login; (c) with an invalid token → error card → "Open Qaren" → Login; (d) `qaren://q/<token>` → back at question 1 → Login. Logged-IN phone: (a)–(c) → Home tab. A phone mid-onboarding (registered, Step-17 not done): → Onboarding. jest proves the router accepts the action for each mounted set; it does not prove the native stack animates or that `getState().routeNames` on device matches the static extraction — the static extraction is asserted against App.tsx's source, the runtime `routeNames` is React Navigation's, and the device walkthrough is where the two are shown to agree.
* **Out of scope, flagged for follow-up (do not fold in):** `InviteeQuizScreen.tsx:136-139` `(navigation as any).navigate('Auth', { screen: 'Register', … })` is dropped the same way for an AUTHED user who takes the quiz (the `Auth` route is not mounted in the authed set — probe B `authed: reset->Auth = NULL` is the same `state.routeNames.includes(action.payload.name)` membership check the `PUSH`/`NAVIGATE` case makes at `StackRouter.tsx:361-364`). The result view shows a signup CTA to a signed-in user, which is a product question before it is a navigation one. The App.tsx:496-498 comment claiming the screens "handle their own auth-state branching internally" is false and should be corrected by whoever next edits that block (W3-6 / W3-15 both do).

## 9. PR-body facts

* Finding MB-FLOWS-STATE-04 (P1, measured). Three `navigation.reset({ routes: [{ name: 'Main' }] })` sites — `ReferralLandingScreen.tsx:118` (error card "Open Qaren"), `:160` ("Maybe later"), `InviteeQuizScreen.tsx:274` (skip signup) — and two unconditional `goBack()` sites (`ReferralLandingScreen.tsx:170`, `InviteeQuizScreen.tsx:92`) now exit to the ROOT OF THE MOUNTED BRANCH, resolved at press time from `navigation.getState().routeNames`.
* App.tsx's root navigator mounts one of three route sets; `'Main'` exists in exactly one (authed). Unauth: `["Auth","ReferralLanding","InviteeQuiz"]`; needs-preferences: `["Onboarding","ReferralLanding","InviteeQuiz"]`. On the other two, the installed `@react-navigation/routers` 7.5.5 (`BaseRouter.tsx:45-57`) returns `null` for the reset; `@react-navigation/core` 7.17.4 then calls `onUnhandledAction`, which in a release build returns silently (`BaseNavigationContainer.tsx:401-404`) and in dev prints `The action 'RESET' … was not handled by any navigator.` Nothing throws; the screen stays. A cold-start deep link is a one-route stack (`getStateFromPath('c/abc123?ref=…')` → one `ReferralLanding` route), so `goBack` is `null` as well.
* User-visible today (logged-out invitee on the `qaren://c/…` path, reachable via the catch-all intent filter; the default path once qaren.app DNS lands): back arrow, "Maybe later" and the error card's only button all do nothing; the only exit is Take the quiz → Register.
* Fix: new pure helper `src/utils/branchRoot.ts` (`resolveBranchRoot` → `'Main' | 'Onboarding' | 'Auth'`, `exitToBranchRoot`, `backOrExit`); 5 call-site edits across the two screens; the three `as never` casts removed (tsc 5.9.3 accepts the real route names without them and rejects an unknown name — `TS2322` — only without the cast). `App.tsx`, `types.ts`, linking config, backend: untouched. No flag (client, OTA-gated). No dependency change.
* Tests: 2 new suites + 1 helper. Red before the fix: 6 of 9 screen×branch cells in the router-verified exit test (`reset -> 'Main'` NULL on 2 of 3 sets), the `as never` static guard (3 hits), the pure helper (module absent), the back-arrow guard (2 sites). Green after. The real router is exercised — the repo's jest could not load `@react-navigation/*` (ESM `lib/module`, no `/src` export; every existing suite mocks it), so `__tests__/helpers/routerSandbox.ts` lowers the installed package with the transitive `@babel/core` + `@babel/plugin-transform-modules-commonjs`, the same pattern as `w312BootSandbox.ts`.
* Five existing screen suites' `mockNavigation` gained `getState` + `canGoBack` (assertions unchanged). Neighbour gate: 10 suites / 79 tests green before and after; tsc exit 0; eslint 0 errors (2 pre-existing warnings untouched); full jest suite run once.
* Ships to phones only with `eas update --branch preview --clear-cache` (Ahmed). Device walkthrough items listed in §8.
* Follow-ups, not in this diff: authed-user `navigate('Auth', …)` at `InviteeQuizScreen.tsx:136` is dropped by the same membership check; `App.tsx:496-498`'s "handle their own auth-state branching internally" comment is false.

## 10. Measurements run

All from `C:/Users/SynAckITPC/Documents/AI/sc-w3-reset` (HEAD `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`) or `…/SmartCompareApp`. Probe files under `.qa-w3b/probes/` (gitignored by `.gitignore:72 .qa-*/`, `git check-ignore -v` confirmed). `git status --short` at the end: empty.

1. **Versions** — `node -p require('./node_modules/<pkg>/package.json').version`: `@react-navigation/native 7.2.4`, `/core 7.17.4`, `/routers 7.5.5`, `/native-stack 7.15.0`, `/bottom-tabs 7.16.0`, `react-native 0.81.5`, `expo 54.0.34`, `jest 29.7.0`, `ts-jest 29.4.9`, `typescript 5.9.3`; `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`; `node -v` → `v24.11.1`. package.json pins: `@react-navigation/native ^7.1.28`, `/native-stack ^7.12.0`, `/bottom-tabs ^7.15.8`, `typescript ~5.9.2`, `ts-jest ^29.4.6`, `jest ^29.7.0`. `@react-navigation/routers` is not in package.json (transitive via core `^7.5.5`). `@babel/core 7.29.0`, `@babel/plugin-transform-modules-commonjs 7.28.6` installed, not declared (plugin is a dependency of `babel-preset-expo 54.0.10`; core is `babel-jest`'s peer); routers `package.json`: `"main": "./lib/module/index.js"`, `exports` = `{".": {source, types, default: "./lib/module/index.js"}, "./package.json"}`, `lib/` contains only `module/` and `typescript/`, no `"type"` field.
2. **Code quotes** — `sed -n 100,175p src/screens/ReferralLandingScreen.tsx`, `sed -n 84,100p; sed -n 255,300p src/screens/InviteeQuizScreen.tsx`, `sed -n 340,512p App.tsx`, `sed -n 571,600p src/types/types.ts` (§3, §4). `grep -n "authService\|getToken\|isAuthenticated\|handleSignup\|navigate(" src/screens/{ReferralLandingScreen,InviteeQuizScreen}.tsx` → only `ReferralLandingScreen.tsx:148 navigate('InviteeQuiz'`, `InviteeQuizScreen.tsx:129 handleSignup`, `:136 (navigation as any).navigate('Auth'`. No auth reads.
3. **Anchor drift** — `git log --oneline 76ace90..ed75dc70 -- <two screens> App.tsx` → 6 commits (b4b3c27e, cc7c7ace, da79066d, 0991ec8f, 2438d82d, a82ff08c); `git show 76ace90:SmartCompareApp/src/screens/InviteeQuizScreen.tsx | grep -n "reset("` → `275:`; HEAD → `274:`. ReferralLanding `118`/`160` at both.
4. **Library source (installed)** — `routers/src/BaseRouter.tsx:45-57` (RESET membership check → `null`), `routers/src/StackRouter.tsx:744-745` (`default: return BaseRouter.getStateForAction`), `:202-210` (`getRehydratedState` filters unknown route names), `core/src/useOnAction.tsx:83,151`, `core/src/useNavigationHelpers.tsx:49-56` (dispatch → `onUnhandledAction`), `:78-87` (`canGoBack`), `:105-115` (`getState` render caveat), `core/src/BaseNavigationContainer.tsx:401-441` (production early return; dev `console.error`), `core/src/useNavigationBuilder.tsx:639-651` (`routeNames` change → `getStateForRouteNamesChange`), `core/src/useNavigationCache.tsx:78-101` (screen prop spreads helpers). Quoted in §3/§4.
5. **Probe 1** `node ../.qa-w3b/probes/router_reset.mjs` (plain node ESM import of `routers/lib/module/index.js` and `core/lib/module/index.js`): output in §3 — per set: `reset->'Main'` NULL/NULL/handled (unauth/needsPrefs/authed), `reset->'Auth'` handled/NULL/NULL, `reset->'Onboarding'` NULL/handled/NULL, `goBack` on the 1-route state NULL ×3, `getInitialState` → `["Auth"]`/`["Onboarding"]`/`["Main"]`; `getStateFromPath("c/abc123?ref=QR-ABCDEF")` → one `ReferralLanding` route; with `initialRouteName:"Auth"` → `{"index":1,"routes":[{"name":"Auth"},{"name":"ReferralLanding",…}]}`.
6. **Probe 2** `node node_modules/typescript/bin/tsc -p ../.qa-w3b/probes/tsconfig.asnever.json` → exactly one error, `asNever.probe.ts(15,43): error TS2322: Type '"NotARoute"' is not assignable to type 'keyof RootStackParamList'.`, exit 2; the un-cast `'Main'|'Auth'|'Onboarding'` resets, the `as never`-cast unknown name, and `getState().routeNames` all compiled.
7. **Probe A** `node node_modules/jest/bin/jest.js --ci --roots ../.qa-w3b/probes --modulePaths node_modules --testMatch "**/routerLoad.probe.test.ts"` → `routers require FAILED: SyntaxError: Cannot use import statement outside a module`; `native require FAILED: SyntaxError: Unexpected token 'export'`; 2 failed. (`--roots` + `--modulePaths` were needed because `.qa-w3b` is outside jest's `rootDir` and has no `node_modules` ancestor; the default `testMatch` does not collect `*.probe.test.ts`.)
8. **Probe B** same invocation with `routerSandbox.probe.test.ts` → loader works; `sets=` line equals the §3 table; the 12 verdict lines in §3; the plan's assertion (`reset -> 'Main'` non-null) fails on `unauth` and `needsPreferences`, passes on `authed` (`1 failed suite: 2 failed / 2 passed tests`). First run of this probe used `indexOf(')}')` for the branch split and leaked `EditPreferences,OnboardingEdit,ScanCamera,Paywall` into the unauth/needsPrefs sets — corrected to `lastIndexOf('</>')`, re-run, sets exact.
9. **Existing tests** — `grep -n "reset\|goBack\|Main\|Auth"` across the 5 screen suites: mocks carry `navigate/goBack/reset` only (`ReferralLandingScreen.test.tsx:100-101`, `.redesign:83-84`, `InviteeQuizScreen.test.tsx:96-97`, `.matchScore.m18:88-89`); `.redesign:172-180` presses skip and asserts only `reset` called; `InviteeQuizScreen.test.tsx:244-253` presses Back at Q1 → `goBack` ×1; `ReferralLandingScreen.test.tsx:146-158` renders "Open Qaren" without pressing it; no test presses `skipSignup`. `grep -rn "@react-navigation" __tests__` → 20 files `jest.mock('@react-navigation/native', …)`, 0 `requireActual`.
10. **Neighbour baseline** — `node node_modules/jest/bin/jest.js --ci <10 paths in §7>` → `Test Suites: 10 passed, 10 total; Tests: 79 passed, 79 total; Snapshots: 0 total`.
11. **tsc baseline** — `node node_modules/typescript/bin/tsc --noEmit` → exit 0, 7.6 s.
12. **eslint baseline** — `node node_modules/eslint/bin/eslint.js src/screens/ReferralLandingScreen.tsx src/screens/InviteeQuizScreen.tsx` → `2 problems (0 errors, 2 warnings)`: `InviteeQuizScreen.tsx 127:6 react-hooks/exhaustive-deps ('isStepValid')`, `ReferralLandingScreen.tsx 28:3 @typescript-eslint/no-unused-vars ('Linking')`; exit 0.
13. **Contract pins read** — `directionalIconWiring.contract.test.ts:19-30` (1 site per screen), `textAlignLogical.contract.test.ts:141-145` (`InviteeQuizScreen.charCount` = `'right'`), `App.distinctRouteNames.test.ts` (regex reused for the extraction).
14. **Not run**: the full jest suite (278 suites — green phase runs it once); anything network, EAS, Railway, DB; no source edit, no git write.

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS.** Every anchor, version, library quote, probe and baseline in §1–§10 was re-measured at `ed75dc70` and reproduced (see "Re-measured" at the end). The defect, the three route sets, the router verdicts and the fix design stand. The rulings below correct five things the red phase would otherwise trip on — two of them fail a stated gate as written — and close the two open questions. Read them as amendments to §4/§5/§7; where a ruling and the body disagree, the ruling wins.

1. **Split the helper's parameter types; the spec's own Red test 2 stub does not compile against `RootNav`.** Measured (probe `.qa-w3b/probes/branchRootTypes.probe.ts`, tsc 5.9.3, the §4.1 code verbatim): `exitToBranchRoot({ getState, reset })` → `error TS2345 … missing the following properties from type 'RootNav': goBack, canGoBack`. And `__tests__/**` IS in the tsc gate's compile set — `SmartCompareApp/tsconfig.json` has no `include`, and `expo/tsconfig.base.json` excludes only `node_modules`, `babel.config.js`, `metro.config.js`, `jest.config.js`, `android`, `ios` — so gate 4 (`tsc --noEmit` exit 0) would go RED on the test file. Ruling: `exitToBranchRoot(navigation: Pick<NavigationProp<RootStackParamList>, 'getState' | 'reset'>)` and `backOrExit(navigation: Pick<NavigationProp<RootStackParamList>, 'getState' | 'reset' | 'canGoBack' | 'goBack'>)`. Every test-side navigation stub is typed `any` (the four existing suites already do `const mockNavigation: any = …`), never structurally — `getState()`'s declared return is `NavigationState<RootStackParamList>` whose `routeNames` is `Extract<keyof RootStackParamList, string>[]`, so a `{ routeNames: string[] }` literal would not satisfy it either. The same probe confirms the good half of §4.1: both `NativeStackScreenProps<RootStackParamList, 'ReferralLanding'>['navigation']` and `…'InviteeQuiz'…` are assignable to the `Pick` with NO cast, `import type { NavigationProp } from '@react-navigation/native'` resolves, and `'NotARoute'` is rejected with `TS2322` — `BranchRoot` is load-bearing.

2. **Gate 5 as written fails on a helper copied from probe B; fix the eslint directives.** Measured by linting a copy of `.qa-w3b/probes/routerSandbox.probe.test.ts` under `__tests__/helpers/` with the repo's `eslint.config.js`: `29:74 warning A require() style import is forbidden (@typescript-eslint/no-require-imports)` — the `require.resolve('@babel/plugin-transform-modules-commonjs')` on the `plugins:` line, which the line-8 directive does not cover — and `30:3 warning Unused eslint-disable directive (no problems were reported from 'no-new-func')`. `w312BootSandbox.ts` lints clean with ZERO directives for its `new Function` (measured, exit 0, no output), so §7.5's "the same `eslint-disable-next-line` comments `w312BootSandbox.ts` carries" is right for `require` and wrong for `new Function`. Ruling: `__tests__/helpers/routerSandbox.ts` carries `// eslint-disable-next-line @typescript-eslint/no-require-imports` immediately above EVERY line containing `require(` or `require.resolve(` (three sites in the probe-B shape: the `@babel/core` require, the plugin `require.resolve`, and the bare-specifier fallback inside `localRequire`), and carries NO `no-new-func` directive. Gate 5 bar for the three new files (`src/utils/branchRoot.ts`, the helper, the two tests): **0 errors AND 0 warnings**; the two pre-existing screen warnings (`InviteeQuizScreen.tsx:127:6`, `ReferralLandingScreen.tsx:28:3`, re-measured) stay exactly two.

3. **§4.4 names five `mockNavigation` objects; there are four.** Measured: `grep -c navigation __tests__/InviteeQuizScreen.redesign.test.tsx` → `0` — it is a source-string suite (`fs.readFileSync(… InviteeQuizScreen.tsx)`) and renders nothing. Ruling: add `getState: () => ({ routeNames: ['Auth', 'ReferralLanding', 'InviteeQuiz'] })` and `canGoBack: () => true` to the FOUR mocks (`ReferralLandingScreen.test.tsx:98-102`, `ReferralLandingScreen.redesign.test.tsx:81-85`, `InviteeQuizScreen.test.tsx:94-98`, `InviteeQuizScreen.matchScore.m18.test.tsx:86-90`); `InviteeQuizScreen.redesign.test.tsx` is untouched. For the record, only two of the four are load-bearing after the fix — `ReferralLandingScreen.redesign.test.tsx:177` (presses skip → `getState`) and `InviteeQuizScreen.test.tsx:252` (presses Back at Q1 → `canGoBack`); the other two never press a control that reaches the helper (the `.test.tsx` presses only the quiz CTA at `:224`; `.matchScore.m18` drives submit at `:134-140` and never presses `skipSignup`). Add to all four anyway so a future press does not throw `is not a function`.

4. **Red test 1 must compare against LITERAL roots, not `resolveBranchRoot(routeNames)`; as specified it is part tautology with a real hole.** §5 test 1 asserts `payload.routes[0].name === resolveBranchRoot(routeNames)` — that reads the fix's own function back (the brief's hazard "a test that reads the fix's own constant back"). The router assertion covers most mutations but NOT this one: a `resolveBranchRoot` that returns `'Results'` whenever `'Main'` is present dispatches `'Results'`, which IS in the authed set (router → non-null) and equals the tautological expectation → the authed cells stay green while a signed-in invitee is dumped on an empty Results modal. Ruling: the `it.each` table carries the expected root as a LITERAL per set — `unauth → 'Auth'`, `needsPreferences → 'Onboarding'`, `authed → 'Main'` — and `__tests__/navigation.branchRootExit.w34.test.tsx` does NOT import `resolveBranchRoot` (it may import nothing from `src/utils/branchRoot`). Red test 2 (`__tests__/utils/branchRoot.test.ts`) likewise asserts `exitToBranchRoot`'s dispatched name against those literals. The `resolveBranchRoot([]) === 'Auth'` case stays but is labelled in the test name as the unreachable fallback (no App.tsx branch produces it), so nobody counts it as coverage. Named mutation this ruling adds to §5's list: `resolveBranchRoot` returning any OTHER member of the authed set (`'Results'`, `'Paywall'`…) → red on the authed cells.

5. **Red test 3's selector: the new suite owns its `t` mock, so pin it and the label.** Measured: the shared `__mocks__/react-i18next.ts` is NOT what the screen suites use — each carries a per-file `jest.mock('react-i18next', …)` and they disagree: `InviteeQuizScreen.test.tsx:54-62` and `.matchScore.m18:56-64` render `t('common.back', {defaultValue:'Back'})` as `'common.back|'`; `ReferralLandingScreen.redesign.test.tsx:50-58` returns the `defaultValue`, i.e. `'Back'`; `ReferralLandingScreen.test.tsx:57-68` returns `key|args` / `key`. Ruling: the new suite's mock is `t: (key: string) => key` (no interpolation, `defaultValue` ignored), and both back arrows are selected with `getByLabelText('common.back')` — both sites pass exactly `t('common.back', { defaultValue: 'Back' })` (`ReferralLandingScreen.tsx:171`, `InviteeQuizScreen.tsx:296`). Every other selector in the suite (`referral-cta-skip` testID, `findByText('referrals.landing.openQaren')`, `getByText('referrals.quiz.skipSignup')`, the four quiz option/next/submit keys) works unchanged under a key-returning `t`. Do not "match by regex" as §5 hedges — one deterministic string.

6. **Scope, closed: the back-arrow half STAYS IN; the `needsPreferences` set STAYS IN; nothing else is added.** Evidence for the first: `docs/investigations/2026-09-06-full-review-verified.json` `/findings/352` title ends "…and on a cold-start deep link the back arrow is dead too" and its `fix` text names `navigation.canGoBack() ? goBack() : reset(<branch root>)` verbatim (re-read); the plan row (`full-review.md:131`) is a one-line summary of that finding, not a narrower brief. Measured dead on all three sets (`goBack on 1-route state = NULL` ×3, probes 1 and B re-run). It is one guard at two sites and its red test is real (both sites call `goBack()` unconditionally at `ReferralLandingScreen.tsx:170` and `InviteeQuizScreen.tsx:92`, re-read). The `InviteeQuizScreen.tsx:136` `(navigation as any).navigate('Auth', …)` for an AUTHED quiz-taker and the false `App.tsx:496-498` comment stay OUT (product question; untouched file) — PR body only, as §8 says.

7. **Test mechanism, closed: the transitive-babel reliance is acceptable; no `package.json` edit; no human step.** Measured: `package-lock.json` pins `node_modules/@babel/core` **7.29.0** (line 107) and `node_modules/@babel/plugin-transform-modules-commonjs` **7.28.6** (line 1064) — CI's `npm ci` installs the lockfile, so both exist on the runner exactly as here; `babel-preset-expo 54.0.10` (declared, `~54.0.10`) depends on the plugin at `^7.24.8`, `babel-jest 29.7.0` (a dep of declared `jest`) peers `@babel/core ^7.8.0`. `__tests__/helpers/w312BootSandbox.ts` (merged, #145) already relies on transitive `@babel/core` + `metro-transform-plugins` the same way. Ruling: the helper's header comment states the reliance and the two lock versions in one line so the next dependency audit sees it. `@react-navigation/routers` is a leaf (its only dependency is `nanoid ^3.3.11`; installed 3.3.12 resolves `nanoid/non-secure` — probe B ran), so the loader never has to lower `core`.

8. **Corrected counts, no design change.** §5/§10.9 "20 files `jest.mock('@react-navigation/native', …)`": measured **16** files mock that exact specifier (17 mention `@react-navigation` at all, 0 `requireActual`, 0 mock `native-stack`). The conclusion — no existing suite exercises the real router — holds. §7.3's neighbour set of 10 = the 9 files the reference-grep (`ReferralLandingScreen|InviteeQuizScreen|branchRoot` over `__tests__` + `src`) returns plus `App.distinctRouteNames.test.ts`, which the grep does NOT return (it says "ReferralLanding", not "ReferralLandingScreen"); keep it in the set, it is a judgement add and App.tsx is untouched. Baseline re-measured: `10 passed / 79 tests / 0 snapshots` (7.3 s). tsc: exit 0 (5.5 s). eslint two screens: `0 errors, 2 warnings`, exit 0.

9. **One backend gate line, per the CLAUDE.md rule "backend tests that SCAN `SmartCompareApp/` belong in the mobile comm set even when no backend file changed".** §7 says "no pytest". Measured: 9 backend files grep the client tree (`tests/test_b2_strict_optional_auth.py`, `test_events_allowlist_superset.py`, `test_feature_bucket_parity.py`, `test_feedback_allowlist_superset.py`, `test_migration_037_security_definer_grants.py`, `test_paid_route_metering.py`, `test_review_paraphrase.py`, `test_security_regression.py`, `test_timeout_partial_integration.py`); none names the two screens, `src/utils` or `branchRoot`, and this unit adds no `trackEvent(`, feedback chip, flag read or route. Ruling: the green phase runs those 9 once — `PYTHONIOENCODING=utf-8 python -m pytest <the 9 files> -q -p no:randomly -p no:cacheprovider -m "not (live_unit or live_db or integration)"` from the worktree root — and records pass/fail; expected unchanged. It is a 30-second rule-compliance check, not a design dependency.

10. **The static `as never` guard matches `as never` ONLY.** `InviteeQuizScreen.tsx:136` keeps its `(navigation as any)` (ruling 6). The guard regex is `/\bas never\b/` over the two screen sources; 3 hits today (`ReferralLandingScreen.tsx:120,162`, `InviteeQuizScreen.tsx:274`, re-read), 0 after.

11. **`rootRouteNameSets()` fails loudly on marker drift.** The extraction keys on four string markers in App.tsx (`{!isAuthenticated ? (`, `) : needsPreferences ? (`, `) : (`, last `</>`); all four exist at `ed75dc70` and the exact-array assertions passed in probe B (re-run). Ruling: before slicing, the helper asserts every marker index is `> -1` and that they are strictly increasing, throwing an error that names the missing marker — the probe's first cut silently leaked four authed-only names on a bad split; a named throw is the cheap insurance.

12. **Nothing else changes.** Files-to-touch list in §4 stands (with the redesign suite struck per ruling 3). `App.tsx`, `src/types/types.ts`, linking config, `package.json`, lockfile, `jest.config.js`, `babel.config.js`, `app.json`, backend: untouched. OTA-safe as claimed: pure TS helper, two screen edits, tests; no native, no flag, no migration, no backend behaviour. Ahmed's only lever is the `eas update --branch preview --clear-cache` already listed in §8.

**Re-measured at `ed75dc70` (this review, 2026-09-11):** `git rev-parse HEAD` = `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git status --short` empty before and after; anchors `ReferralLandingScreen.tsx:118/120/160/162/170`, `InviteeQuizScreen.tsx:92/274` re-read verbatim; `git log --oneline 76ace90..ed75dc70` on the three files = the 6 commits listed in §10.3; `git show 76ace90:…InviteeQuizScreen.tsx | grep -n "reset("` → `275`, HEAD → `274`. Versions: native 7.2.4 / core 7.17.4 / routers 7.5.5 / native-stack 7.15.0 / bottom-tabs 7.16.0 / typescript 5.9.3 (`tsc -v` "Version 5.9.3") / jest 29.7.0 / ts-jest 29.4.9 / @babel/core 7.29.0 / plugin-transform-modules-commonjs 7.28.6 / babel-preset-expo 54.0.10 / nanoid 3.3.12 / node v24.11.1; pins `^7.1.28`, `^7.12.0`, `~5.9.2`, `^29.7.0`, `^29.4.6`, `~54.0.10`; routers `main` = `./lib/module/index.js`, `exports` = `.` + `./package.json`, `lib/` = `module` + `typescript`. Library lines re-read at the cited numbers: `routers/src/BaseRouter.tsx:45-57`, `StackRouter.tsx:202-210/361-364/744-745`, `core/src/useOnAction.tsx:83,151`, `useNavigationHelpers.tsx:49-56/78-87/105-115`, `BaseNavigationContainer.tsx:401-441`, `useNavigationBuilder.tsx:639-651`, `useNavigationCache.tsx:78-101`. Probe 1 (`node ../.qa-w3b/probes/router_reset.mjs`): 12 verdict lines + both `getStateFromPath` results identical to §3. Probe A: both `require`s fail with the quoted `SyntaxError`s. Probe B: `sets=` exact, 12 verdict lines identical, `2 failed / 2 passed` on the plan's assertion (unauth + needsPreferences red, authed green). Probe 2: exactly one error, `asNever.probe.ts(15,43) TS2322`, exit 2. New probe `branchRootTypes.probe.ts` (+ `tsconfig.branchRoot.json`, both under `.qa-w3b/probes/`): exit 2 with exactly the two expected errors (ruling 1's TS2345 on the stub; TS2322 on `'NotARoute'`), zero errors on the two screen-prop assignability functions. `jest.config.js` `testMatch` = `**/__tests__/**/*.test.ts(x)` (helper not collected; `__tests__/utils/` already exists with `deriveTone.test.ts`); `__tests__/setup.ts:15` `console.error = noop`. `App.tsx:350-355` linking `prefixes: ['qaren://', 'https://qaren.app']`, `ReferralLanding: 'c/:share_token'`, `InviteeQuiz: 'q/:share_token'`, no `initialRouteName`; the only in-app navigator to either screen is `ReferralLandingScreen.tsx:148 navigate('InviteeQuiz', …)`. `ReferralLandingScreen.tsx:60-76` maps `status 404/503/other` → `not_found/unavailable/network`; the error view's only control is the `openQaren` Button. `InviteeQuizScreen.test.tsx:69-116` `mockSubmitInviteeQuiz` + `RESULT_PAYLOAD` reach the result view. Not run: the full jest suite; anything network/EAS/Railway/DB; no source or git write.

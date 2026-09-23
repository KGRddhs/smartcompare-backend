# W3-16 — consent capture: ToS acceptance + 13+ attestation, persisted, on every account-creation path

> Draft written by a previous spec agent (killed before reporting). **Re-verified line by line at `ed75dc70` on 2026-09-11 by the resume agent**; every anchor below was re-located and quoted, both probes were re-run (outputs in §10), and the corrections are folded IN PLACE. The corrections that changed the design or a test are called out with **[CORRECTED]**.

## 1. Header

| field | value |
|---|---|
| unit | **W3-16 consent capture** (critic-found, Fable-verified; `docs/investigations/2026-09-06-full-review.md:144`, critic gap (c) at `:192`, verifier text `…-verified.json:1972`) |
| absorbs | the Legal-route-hoist half of **`MB-FLOWS-STATE-08`** (`…-tables.md:211`, P2) — the verifier's own warning: *"adding a link to RegisterScreen without first hoisting the Legal Stack.Screen out of the authenticated branch produces another silently-dropped navigate"* (`…-verified.json:12735`). Its "consent line" half becomes the explicit control below. **NOT absorbed:** `MB-FLOWS-STATE-03` (Paywall links, `:209`). |
| base SHA | `ed75dc70` (`git rev-parse HEAD` = `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`, "Merge pull request #154 from KGRddhs/docs/session-65-part4", Fri Sep 11 00:46:43 2026 +0300; `git status --short` = empty) |
| OTA class | **mixed** — client half **OTA-safe** (TS/TSX + i18n JSON only; no `app.json`, no plugin, no native dep); backend half **backend-only** + **migration 038, UNAPPLIED on merge**; nothing CI-only. |
| flags (backend, both default OFF, read PER CALL) | `ENABLE_CONSENT_PERSIST` (write the three new `users` columns; needs 038 applied) · `ENABLE_CONSENT_REQUIRED` (reject an account creation that carries no acceptance; needs the client half on phones) |
| gate SHAPE | **Ahmed's call** — §4.1 specs the minimal shape and names the alternatives; the code half is written so the shape can be swapped without touching the backend. |
| installed toolchain (measured, §10.2) | `node node_modules/typescript/bin/tsc -v` → **Version 5.9.3** (pin `~5.9.2`); jest 29.7.0 (pin `^29.7.0`); ts-jest 29.4.9 (pin `^29.4.6`); `@testing-library/react-native` 13.3.3 (pin `^13.3.3`); react-native 0.81.5 (pin `0.81.5`); expo 54.0.34 (pin `~54.0.33`); `@react-navigation/core` 7.17.4 / `native` 7.2.4 (pin `^7.1.28`) / `native-stack` 7.15.0 (pin `^7.12.0`); react-i18next 17.0.7 (pin `^17.0.1`); axios 1.20.0 (pin `^1.20.0`). `node_modules/@babel/core` and `.bin/jest` present (junction healthy). **Python drift (recorded, not fixable here):** Python 3.12.9; local fastapi 0.115.0 / starlette 0.38.6 / pydantic 2.7.0 / supabase 2.28.0 / supabase_auth 2.28.0 vs pins fastapi==0.141.1 (`requirements.txt:47`) / starlette==1.6.0 (`:150`) / pydantic==2.13.4 (`:109`) / supabase==2.31.0 (`:156`) / supabase-auth==2.31.0 (`:158`). Every pydantic claim below was probed on 2.7.0; CI runs 2.13.4 — the extra-field default (`ignore`) is the same across the v2 line, but the green phase must trust CI, not this box, for anything pydantic-shaped. |
| harness facts settled by probe (§10.6) | (a) `getByRole('checkbox')` + `{ checked }` filter + press-toggle WORK under `__mocks__/react-native.ts` for BOTH `Pressable` and `TouchableOpacity` (both render a host `View` with props spread + `accessible: true`, mock `:18-19` / `:68-69`); (b) `navigation.getParent()?.navigate('Legal', { doc })` TYPE-CHECKS from an `AuthStackParamList` screen on the installed tsc 5.9.3 / core 7.17.4 (negative controls error as expected); (c) the mock's `Platform.OS` is `'ios'` by default (`:70`), so the Apple leg is testable on both screens. |

## 2. Scope correction — what is ALREADY on main at `ed75dc70`

The plan lists one compound red test: *"register/social sign-in cannot complete without an explicit acceptance and the accepted version is persisted (RED)"*. **Both halves are RED today; nothing is dropped.** Evidence:

* Client: the probe (`.qa-w3b/probes/w316_consent_absent.probe.test.tsx`, output §10.6) shows `register()` called with `["user@example.com","StrongPass1!",{}]`, `signInWithGoogle()` called with `[]` from BOTH RegisterScreen and LoginScreen, `0` checkbox roles on either screen, and no `common.terms` / `common.privacy` text on Register.
* Backend: the probe (`.qa-w3b/probes/probe_w316_backend.py`, output §10.5) shows `POST /register` → 200 with no consent, `POST /social-login` → 200 with no consent, `register_user` signature `('email','password')`, `sign_in_with_social` signature `('provider','id_token','nonce')`, and the two `users` INSERT dicts are `{'id','email','subscription_tier'}` and `{'id','email','auth_provider','subscription_tier'}` — no consent column exists to write to (`grep -rniE "terms_accepted|terms_version|age_gate|attest" migrations/ docs/CONTEXT_DATABASE_API.md` = 0 hits).
* Repo-wide: `grep -rniE "terms_accepted|termsAccepted|acceptedTerms|terms_version|termsVersion|age_gate|ageGate|is_over_13|over13|attest" SmartCompareApp/src app/ SmartCompareApp/App.tsx migrations/ docs/CONTEXT_DATABASE_API.md` = 0 source hits (the only matches are `anon_usage_gate_enabled` source lines and three `__pycache__/*.pyc` binaries, §10.1).

**One thing the plan's red test 11 would have DUPLICATED [CORRECTED]:** `__tests__/App.distinctRouteNames.test.ts` already scans `App.tsx` and asserts every `<Stack.Screen name="X">` appears EXACTLY once (its first `it`, regex over the source; 3 tests, green today). So "one `name="Legal"`" is an EXISTING pin, and the duplicate-name mutation is already caught. The new test pins only what is NOT covered: the POSITION of `Legal` (outside both auth branches) — §5-A.11.

**Already on main and RELIED ON (verify, do not re-file):** the `Legal` screen + route exist (`App.tsx:414-419`, `src/screens/LegalScreen.tsx` maps `terms: '/api/v1/legal/terms_of_service'` at `:34` and fetches at `:53` `const res = await api.get(endpoint);`); `RootStackParamList.Legal: { doc: 'privacy' | 'terms' }` at `src/types/types.ts:599`; `common.terms` / `common.privacy` exist in BOTH catalogs as **FLAT keys** (`en.json:915` `"common.terms": "Terms"`, `:914` `"common.privacy": "Privacy"`; `ar.json:912` `"common.terms": "الشروط"`, `:911` `"common.privacy": "الخصوصية"`) — the catalogs are flat `"a.b.c"` maps, NOT nested objects, so the three new keys are added as flat strings too; account deletion is wired (not this unit).

**Line anchors that moved since the finding docs (76ace90 / 98f320fb → ed75dc70):**

| doc anchor | at ed75dc70 |
|---|---|
| `RegisterScreen.tsx:465` (STATE-08 row) | Google/Apple block is `:442-463` (Google `Button` `:442-448`, `{showApple && (` `:450`), benefits `:467-473`, footer `:477-482` |
| `App.tsx:347-352` Legal Stack.Screen (verifier) | `:414-419` (comment at `:414`, `name="Legal"` at `:416`) |
| `App.tsx:338` authenticated branch open | `:385` `{!isAuthenticated ? (` … `:404` `) : (` (the `) : (` at `:399` and `:463` are inner ternaries) |
| `App.tsx:427-440` ReferralLanding/InviteeQuiz | `:503-507` (`name="ReferralLanding"` `:504`, `name="InviteeQuiz"` `:507`), comment block `:492-502`, `</Stack.Navigator>` `:508` |
| `auth_routes.py` register / social-login | `:408-410` / `:849-851` |
| `auth_service.py` users inserts | `:242-246` (register) / `:582-587` (social, first sign-in; `existing` lookup `:580`, `if not existing.data:` `:581`) |

## 3. The defect — measured

### 3.1 No control, no field, no column

`SmartCompareApp/src/screens/RegisterScreen.tsx:222-225` — the only thing Register sends:

```ts
      const result = await register(email.trim().toLowerCase(), password, {
        inviteId,
        inviteCode: inviteCode || undefined,
      });
```

`RegisterScreen.tsx:122-126` / `:149-153` — social taps go straight to the service, no gate:

```ts
  const handleGoogleSignIn = async () => {
    setSocialLoading('google');
    setError('');
    try {
      const result = await signInWithGoogle();
```

`LoginScreen.tsx:210-214` / `:238-242` — identical shape; `:382-409` renders the social row (`login-social-apple` / `login-social-google` / `login-social-email`) with no legal line anywhere on the screen.

`src/services/authService.ts:139-149` — the register body:

```ts
    const response = await api.post(
      '/api/v1/auth/register',
      {
        email,
        password,
        ...(options.name ? { name: options.name } : {}),
        ...(options.inviteId ? { invite_id: options.inviteId } : {}),
        ...(options.inviteCode ? { invite_code: options.inviteCode } : {}),
      },
      fingerprint ? { headers: { 'X-Device-Fingerprint': fingerprint } } : undefined,
    );
```

`authService.ts:718` **[CORRECTED from `:723`]** (`const body: Record<string, string> = { provider: 'google', id_token: idToken };`) and `:868-872` **[CORRECTED from `:869-873`]** (`body: JSON.stringify({` `:868`, `provider: 'apple',` `:869`, `id_token: idToken,` `:870`, `nonce: rawNonce,` `:871`, `}),` `:872`) — the two social bodies. `__tests__/services/authService.b4.test.ts:170` PINS the Google body: `it('body keys are EXACTLY { provider, id_token } — no leaked extras'` — this shapes the design (§4.2: fields only when a consent object is passed).

`app/api/auth_routes.py:79-87` — `RegisterRequest` has `email` (`:80`), `password` (`:81`), `invite_id` (`:85`), `invite_code` (`:87`) and NO `model_config` (the only `model_config = {"extra": "ignore"}` in the file is `:264`, `AttributionBody`); `:268-271` `SocialLoginRequest` has `provider`, `id_token`, `nonce`. Probed on installed pydantic 2.7.0: `RegisterRequest.model_validate({... "terms_accepted": True ...}).model_dump()` = `{'email','password','invite_id': None,'invite_code': None}` — **a new client that sends consent to today's backend has it silently dropped** (§10.5 block 1). That is the backward-compat property the client half relies on, and also why the backend half must land first.

`app/services/auth_service.py:242-246` (register) and `:580-587` (social):

```py
            admin.table("users").insert({
                "id": response.user.id,
                "email": email,
                "subscription_tier": "free"
            }).execute()
```
```py
        existing = admin.table("users").select("id").eq("id", response.user.id).execute()
        if not existing.data:
            admin.table("users").insert({
                "id": response.user.id,
                "email": response.user.email,
                "auth_provider": provider,
                "subscription_tier": "free",
            }).execute()
```

**Where the social account is created:** `sign_in_with_social` (`:551`) at `:573` calls `auth_client.auth.sign_in_with_id_token(credentials)` (Supabase creates the `auth.users` row on first id-token sign-in), then `:580-587` creates OUR `public.users` row iff `existing.data` is empty. That `if not existing.data` branch is the ONE place a social account becomes a Qaren account, and it is reachable from BOTH screens (LoginScreen's Google/Apple buttons create accounts exactly like Register's). Consent for the social path therefore has to travel in the `/social-login` request and be decided at that branch.

`users` table (`docs/CONTEXT_DATABASE_API.md:83-92`, the `CREATE TABLE public.users` block; columns added later via `ALTER TABLE users ADD COLUMN IF NOT EXISTS …` in `migrations/011_…:28-29`, `014_…:11-13`, `015_…:13/18/27`): no consent column. `migrations/` tops out at `037_security_definer_grants_and_rls.sql`; `migrations/rollback/` mirrors 032-037 → the new one is **038**.

### 3.2 Why the Terms/Privacy spans need the Legal hoist

`App.tsx:385-419`: the `Legal` Stack.Screen is registered INSIDE the `isAuthenticated` `: (` branch (`:404`), so while the user is on Register/Login the route does not exist and `navigate('Legal')` is silently dropped. Bubbling itself is fine: installed `@react-navigation/core` 7.17.4 `src/useOnAction.tsx:127-129` — *"Bubble action to the parent if the current navigator didn't handle it"* — so a nested AuthStack screen CAN reach a root-level `Legal` once it is registered at navigator level, exactly as `ReferralLanding`/`InviteeQuiz` are at `:503-507` (comment `:492-502` explains why root-level registration is the v7-safe pattern and why the same `name` must never appear in two branches — and `__tests__/App.distinctRouteNames.test.ts` enforces it).

### 3.3 Policy inputs (fixed, not designed here)

`CLAUDE.md:466` names "ToS clickwrap + 13+ gate" as code-side blockers; `CLAUDE.md:468`: **"Age policy (locked): 13+ general audience including teens. Apple 12+, Google Play Teen. Do NOT enroll in Apple 'Kids' or Google 'Designed for Families'."** `docs/plans/2026-05-06-tos-fact-base.md:774`: *"The app does not collect date of birth and does not target minors, but does NOT have an age gate. The ToS should include a 13+ minimum age statement"* → an **attestation**, not a date-of-birth collection, is the policy-consistent gate. `app/legal/terms_of_service.md:5` "*Last Updated: March 26, 2026*" (and `:7` "*DRAFT — This document is a template…*") and `legal_routes.py:30` / `:47` **[CORRECTED from `:31/48`]** `"last_updated": "2026-03-26"` → the current terms version string is **`2026-03-26`** (still DRAFT — ship-blocker #2, `CLAUDE.md:15`; the version bumps when the redraft lands, §8). `tests/test_legal_routes.py:57` `test_last_updated_is_date_format` already pins the field's format.

## 4. The fix — MINIMAL design

### 4.1 The gate SHAPE (recommended minimal; Ahmed confirms — see alternatives)

**One explicit control, one line of copy, both screens' account-creating actions gated by it:**

> ☐ *I am 13 or older and I agree to the* **Terms** *and* **Privacy Policy**

* A `ConsentRow` (unchecked by default, `accessibilityRole="checkbox"`, `accessibilityState={{ checked }}`, `testID="consent-checkbox"`), with **Terms** and **Privacy Policy** as pressable spans opening `Legal { doc }`. One tick = ToS acceptance **and** the 13+ attestation (the sentence states both; the payload records both as separate booleans so a two-checkbox shape later needs no backend change).
* **RegisterScreen:** gates *Create Account*, *Google*, *Apple*. Unticked → inline `auth.consent.required` under the row (`testID="consent-error"`), the service is NOT called.
* **LoginScreen:** the row sits directly above the social row and gates **only** *Google* / *Apple* (the account-creating actions). Email/password *Sign in* is NOT gated (an existing account is not being created). Yes, a returning Google user re-ticks on every Login — Login is reached only after logout/token loss, and a fresh acceptance of the current version is a legal plus, not a cost.
* Payload (client → backend, both paths): `terms_accepted: true`, `terms_version: TERMS_VERSION`, `age_attested: true`.

**Alternatives for Ahmed (each is a client-only swap; the backend contract above is unchanged):**
1. **Two checkboxes** (age + terms separately) — clearer evidence per attestation; one more tap; same payload.
2. **Login social = reveal-on-demand**: no row on Login; a NEW social account with the backend flag ON returns `TERMS_ACCEPTANCE_REQUIRED`, the client then reveals the row and re-taps. Zero friction for returning users **but no consent UI at all on Login while `ENABLE_CONSENT_REQUIRED` is OFF** — a reviewer creating an account via Login → Apple would see none. Rejected as the default for that reason.
3. **Date-of-birth picker** — collects data the fact-base says we do not collect and is the "Kids"-style gate the locked policy avoids. Rejected.
4. **Sign-in-wrap line only** ("By continuing you agree…", no control) — the weakest form of assent; does not carry an age attestation. Rejected for the 13+ half; fine as a *supplement* under the email/password Sign-in button (not specced; Ahmed may ask for it).

### 4.2 Client (OTA-safe) — files to touch

| file | change | unchanged |
|---|---|---|
| **new** `src/services/consent.ts` | `export const TERMS_VERSION = '2026-03-26';` `export interface ConsentPayload { terms_accepted: true; terms_version: string; age_attested: true }` `export function buildConsentPayload(): ConsentPayload`. Pure module, no imports. | — |
| **new** `src/components/ConsentRow.tsx` | Props `{ checked, onToggle, onOpenLegal: (doc: 'terms'\|'privacy') => void, error?: boolean, disabled?: boolean, testID? }`. A `Pressable` row (role checkbox, state checked, `hitSlop` so the 44-pt rule holds; `TouchableOpacity` is equally fine — both are in the RN mock and both answer `getByRole('checkbox')`, §10.6b) + a `Text` line built from `t('auth.consent.prefix')`, pressable `t('common.terms')`, `t('auth.consent.and')`, pressable `t('common.privacy')`; error `t('auth.consent.required')` with `testID="consent-error"`. Uses `flexDirection: 'row'` so RN mirrors it under RTL; NO directional icon (keeps `__tests__/rtl/directionalIconWiring.contract.test.ts` table untouched); the tick glyph `✓` is allowed by eslint's `wordsExclude` (`eslint.config.js:20-28`: the `/^[\p{P}\p{S}\p{Z}]+$/u` symbol class). | theme tokens only; no new dependency |
| `src/screens/RegisterScreen.tsx` | state `consentAccepted` / `consentError`; in `handleRegister` (`:175`) add the unticked → error + `hasError` branch alongside the existing field checks; pass `consent: buildConsentPayload()` in the `RegisterOptions` object at `:222-225`; in `handleGoogleSignIn` (`:122`) / `handleAppleSignIn` (`:149`) return early with the error when unticked, else call `signInWithGoogle(buildConsentPayload())` / `signInWithApple(buildConsentPayload())`; render `<ConsentRow>` between the invite-code block (`:381-426`) and the Create Account `Button` (`:428-433`); spans navigate via **`navigation.getParent()?.navigate('Legal', { doc })`** — **[CORRECTED: no longer a hedge]** this type-checks on the installed toolchain (probe §10.6c: `NativeStackScreenProps<AuthStackParamList,'Register'>['navigation'].getParent()` is `NavigationProp<ParamListBase> \| undefined`, core `src/types.tsx:630`; the bare `navigation.navigate('Legal', …)` is the negative control and errors TS2345 because `AuthStackParamList` (`types.ts:624`) has no `Legal`). The `(navigation as any).navigate(...)` precedent at `InviteeQuizScreen.tsx:136` also compiles but is not needed. Existing test mocks pass `{ navigate, goBack, canGoBack }` with no `getParent`, so the `?.` keeps them green; the new test supplies `getParent: () => ({ navigate: parentNavigate })`. | email/password/confirm/invite validation, the `confirmationEmail` early-return card (`if (confirmationEmail) {` `:249`, `testID="email-confirmation-card"` `:257`), clipboard-consent banner, P-A8 error-key handling (`setError(parseApiError(err).message)` `:240` **[CORRECTED from `:239`]**) — byte-unchanged |
| `src/screens/LoginScreen.tsx` | same state pair; `<ConsentRow>` rendered above the social row (`:382-409`); `handleGoogleSignIn` (`:210`) / `handleAppleSignIn` (`:238`) gated exactly as on Register; `handleLogin` (`:259` **[CORRECTED from `:260`]**) **untouched**; `handleEmailSocialPress` (`:314`) untouched. | the B9 back-arrow/`canGoBack` logic, `disabled` latch `:323`, `SocialButton` local component (`interface SocialButtonProps` `:65`, `function SocialButton` `:74-103`) |
| `src/services/authService.ts` | `RegisterOptions` (`:107-111`) gains `consent?: ConsentPayload`; register body (`:139-149`) spreads `...(options.consent ?? {})`; `signInWithGoogle(consent?: ConsentPayload)` (`:665`) builds `{ provider, id_token, ...(consent ?? {}) }` at `:718`; `signInWithApple(consent?: ConsentPayload)` (`:814`) spreads into the JSON at `:868-872`. **Fields are added ONLY when a consent object is passed** — the b4 "EXACTLY { provider, id_token }" pin (`b4.test.ts:170`) stays green and stays meaningful. Note `body` at `:718` is typed `Record<string, string>` — a boolean `terms_accepted` needs the type widened to `Record<string, string \| boolean>` (or the spread object typed separately); tsc will say so. | fingerprint header, deadline/timeout handling, Sentry diagnostics, token/user persistence |
| `App.tsx` | **Hoist** the `Legal` `Stack.Screen` (`:414-419`, keep `options={{ presentation: 'modal' }}`) out of the authenticated branch to navigator level, AFTER `InviteeQuiz` (`:507`), and DELETE it from the branch (two `Stack.Screen`s with one `name` collapse in v7 — the `:492-502` comment, `memory feedback_react_navigation_duplicate_route_name.md`, and `__tests__/App.distinctRouteNames.test.ts` which reds on any duplicate). | linking config (`const linking` `:350-379`), both auth branches otherwise |
| `src/i18n/en.json` + `src/i18n/ar.json` | add **the same three FLAT keys** to both (the catalogs are flat `"dotted.key": "value"` maps — see `en.json:914-915`): `"auth.consent.prefix"` ("I am 13 or older and I agree to the"), `"auth.consent.and"` ("and"), `"auth.consent.required"` ("Please accept the Terms and confirm you are 13 or older to continue") + Arabic. Reuse `common.terms` / `common.privacy`. The fences enforce this: `__tests__/i18n.test.ts` (key-set + interpolation parity), `__tests__/i18n/no-deleted-keys.test.ts` (exact count parity), `__tests__/i18n/no-missing-referenced-keys.test.ts` (every static `t('…')` in `src/` exists in en.json). | all other keys |
| existing tests (green phase, NOT the red phase) | 24 press sites in 7 files must tick the box first (`fireEvent.press(getByTestId('consent-checkbox'))`) — re-enumerated at `ed75dc70`, §10.8: `RegisterScreen.inviteCode.test.tsx:104,126,137`; `RegisterScreen.inviteId.test.tsx:99,116`; `RegisterScreen.emailConfirmation.m18.test.tsx:80,97,116`; `AuthScreens.test.tsx:120` (Login, `getAllByText('auth.googleSignIn')[0]`); `AuthScreens.socialDiagnostic.pa8.test.tsx:153,165,179,190,205,214` (Login) `,236,246` (Register); `AuthScreens.socialTimeout.a8.test.tsx:76,89,100,112,116` (Login) `,136,149` (Register). Their assertions do not change — only the precondition. Any OTHER test edit is a smell. | `LoginScreen.noopControls.b9.test.tsx` (0 social presses), `RegisterScreen.deferredCode.test.tsx` (0), `Screens.bundleD.contract.test.ts` (source-shape pins; re-run, expect green), `App.distinctRouteNames.test.ts` (must stay green after the hoist) |

Backward-compatibility with the backend on main (client ships first is NOT the plan, but must be safe): the new fields are silently ignored by today's `RegisterRequest`/`SocialLoginRequest` (§3.1 probe) → a phone on the new OTA against an old backend still registers; consent is simply not recorded. No `app.json`, no plugin, no dependency → **OTA-safe**; nothing here is needs-build.

### 4.3 Backend (backend-only + migration 038) — files to touch

| file | change | unchanged |
|---|---|---|
| **new** `app/services/consent_service.py` | `TERMS_VERSION = "2026-03-26"`; `consent_persist_enabled()` → `os.getenv("ENABLE_CONSENT_PERSIST", "false").strip().lower() in ("true","1","yes","on")`; `consent_required_enabled()` same for `ENABLE_CONSENT_REQUIRED` (the `strict_optional_auth_enabled` idiom at `auth_routes.py:317-348`: read PER CALL, Railway flip needs no restart); `consent_from_fields(terms_accepted, terms_version, age_attested) -> Optional[dict]` returns `{"terms_accepted_at": <utc iso now>, "terms_version": <str>, "age_attested_at": <same ts>}` iff `terms_accepted is True and age_attested is True and terms_version` (non-empty), else `None`; `consent_columns(consent) -> dict` returns `consent or {}` iff `consent_persist_enabled()` else `{}`; `consent_rejection() -> HTTPException(400, detail={"code": "TERMS_ACCEPTANCE_REQUIRED", "error": "Please accept the Terms and confirm you are 13 or older."})` — the `error_handler._is_structured_detail` shape (`error_handler.py:74-91`) so the wire envelope is the standard `{"success": false, "code": "TERMS_ACCEPTANCE_REQUIRED", "error": …}`. | — |
| `app/api/auth_routes.py` | `RegisterRequest` (`:79`) and `SocialLoginRequest` (`:268`) each gain `terms_accepted: Optional[bool] = None`, `terms_version: Optional[str] = Field(default=None, max_length=32)`, `age_attested: Optional[bool] = None` — **optional; phones on 97b5f15 and the pending OTA send nothing and keep working**. `register` (`:410`): `consent = consent_from_fields(...)`; `if consent is None and consent_required_enabled(): raise consent_rejection()` BEFORE `register_user` (so no Supabase account is created without acceptance); call `register_user(body.email, body.password, consent=consent)`. `social_login` (`:851`; body `:853` `result = await sign_in_with_social(body.provider, body.id_token, body.nonce)`, `:854-855` the 401): pass `consent=consent` as a KEYWORD to `sign_in_with_social`; on `not result["success"]`, `if result.get("code") == "TERMS_ACCEPTANCE_REQUIRED": raise consent_rejection()` else the existing 401. | rate-limit decorators (`:409` `3/minute`, `:850` `10/minute`), fingerprint inheritance, invite linking, audit log, every other route |
| `app/services/auth_service.py` | `register_user(email, password, consent: Optional[dict] = None)` (`:227`): insert dict becomes `{"id", "email", "subscription_tier": "free", **consent_columns(consent)}` — with `ENABLE_CONSENT_PERSIST` OFF this is the byte-identical three-key dict (§10.5 block 4). `sign_in_with_social(provider, id_token, nonce=None, consent: Optional[dict] = None)` (`:551`): inside `if not existing.data:` (`:581`), FIRST `if consent is None and consent_required_enabled(): return {"success": False, "code": "TERMS_ACCEPTANCE_REQUIRED", "error": …}` (no insert; the `auth.users` row Supabase already created is harmless — the retry with consent creates OUR row), ELSE insert `{… "subscription_tier": "free", **consent_columns(consent)}`. **Existing accounts (`existing.data` non-empty) are never gated** — re-consent of existing users is policy (§8). Positional callers (`tests/test_auth_interceptor.py:1050` `sign_in_with_social("google", "id-token-123")`) keep working because both new params default. | `_categorize_auth_error` (incl. the `[B4-BE-DIAG]` branch `:198-202`), `_enrich_response_with_profile`, `preferences_completed` lookup (`:589-590`), every other function |
| **new** `migrations/038_users_consent_capture.sql` | Header in the 033 style (`migrations/033_product_prices_title.sql:1-26`: why, ROLLOUT ORDER, rollback path, "Additive + nullable → safe, no backfill"). `BEGIN; ALTER TABLE public.users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ; ADD COLUMN IF NOT EXISTS terms_version TEXT; ADD COLUMN IF NOT EXISTS age_attested_at TIMESTAMPTZ; COMMENT ON COLUMN … (three); COMMIT;` Additive, nullable, no backfill, no index, no function. **Rollout order stated in the file: apply 038 FIRST, then `ENABLE_CONSENT_PERSIST=true`, then (after the OTA is on phones) `ENABLE_CONSENT_REQUIRED=true`.** The file WILL be scanned by the 16 backend tests that glob `migrations/*.sql` (§7 backend gate 3) — none of them can object to a plain nullable `ADD COLUMN` (no `CREATE INDEX … WHERE`, no `SECURITY DEFINER`), but they run in the gate to prove it. | RLS (the writes go through the service-role admin client exactly like today's inserts) |
| **new** `migrations/rollback/038_users_consent_capture.sql` | `033`-style (`migrations/rollback/033_product_prices_title.sql:1-12`): flip BOTH flags OFF first, then `DROP COLUMN IF EXISTS` ×3. | — |
| `docs/CONTEXT_DATABASE_API.md` | `users` block (`:83-92`) gains the three columns with "(migration 038, UNAPPLIED)"; `POST /api/v1/auth/register` (`:187-193` **[CORRECTED from `:186-192`]**) gains the three optional fields. | — |
| `CLAUDE.md` | two flag rows in the SESSION 65 flag block (format of the `ENABLE_STRICT_OPTIONAL_AUTH` row at `:420`): effect ON, preconditions (038 applied → PERSIST; OTA on phones → REQUIRED), per-call read, canary log line. | — |

**Why two flags, not one.** With ONE flag, persisting consent from new phones would also reject registrations from phones still on 97b5f15. `PERSIST` can go on the day 038 is applied (records what new clients send, ignores old ones); `REQUIRED` waits for the OTA. `REQUIRED` ON with `PERSIST` OFF rejects but does not record — legal, pointless; the CLAUDE.md row says flip PERSIST first, and test §5-B.11 pins that the two reads are independent so nobody "fixes" that by coupling them.

**Why not the `users.preferences` JSONB.** `save_user_preferences` (`auth_service.py:689`, update at `:712-715`) does `update({"preferences": preferences, "preferences_completed": True})` wholesale — a consent record living there would be overwritten by the next preferences save. Legal evidence gets its own nullable columns.

**Not in scope (deliberately):** exposing `version` on `GET /api/v1/legal/*` (additive but unnecessary — the parity pin §5-B.12 ties the constants directly); re-consent of existing accounts on a version bump; the `terms_version`-mismatch policy (client sends an older constant than the backend's: accepted and persisted as sent — what the user actually saw); a legal `version` on `LegalScreen`; an i18n mapping for `TERMS_ACCEPTANCE_REQUIRED` in `errorCopy.ts` (the new client never triggers it — it always sends consent; old clients render the envelope `error` string, §8).

## 5. Red tests — exact files, assertions, why RED today (measured), and the mutation that must redden each

### 5-A. Client (jest; run each by path with `node node_modules/jest/bin/jest.js --ci <path>`)

**`__tests__/RegisterScreen.consent.w3-16.test.tsx`** (harness = `RegisterScreen.inviteCode.test.tsx:17-95` mock set. Apple leg **[CORRECTED — no skip]**: mock `isAppleSignInAvailable: jest.fn().mockResolvedValue(true)`; the RN mock's `Platform.OS` is already `'ios'` (`__mocks__/react-native.ts:70`) so `RegisterScreen.tsx:71-72` sets `showApple` — `await waitFor(() => getByText('auth.appleSignIn'))`; precedent `AuthScreens.socialDiagnostic.pa8.test.tsx:165` presses `login-social-apple` the same way. Navigation mock: `{ navigate, goBack, canGoBack: () => false, getParent: () => ({ navigate: parentNavigate }) }`.)
1. *Control exists and opens the docs:* `getByRole('checkbox', { checked: false })` present (the role query works under the mock — §10.6b); pressing `getByText('common.terms')` → `parentNavigate` called with `('Legal', { doc: 'terms' })`; same for `common.privacy`. **RED:** probe = 0 checkbox roles, `common.terms` absent. *Mutation:* remove the spans' `onPress` → red.
2. *Unticked submit is blocked:* fill email/password/confirm, press `auth.register` → `mockRegister` NOT called, `getByTestId('consent-error')` visible. **RED:** probe shows `register()` called with `{}`. *Mutation:* drop the `hasError` branch → red.
3. *Ticked submit carries the payload:* tick, press → `mockRegister` called with `expect.objectContaining({ consent: { terms_accepted: true, terms_version: TERMS_VERSION, age_attested: true } })` (import `TERMS_VERSION` from `src/services/consent`). **RED:** third arg is `{}` today (and `src/services/consent` does not exist → the import fails, which is the honest red). *Mutation:* stop passing `consent` → red.
4. *Google gated:* unticked press `auth.googleSignIn` → `signInWithGoogle` NOT called + error visible; ticked → called with `[{ terms_accepted: true, terms_version: TERMS_VERSION, age_attested: true }]`. **RED:** probe = called with `[]`. *Mutation:* remove the guard in `handleGoogleSignIn` → red.
5. *Apple gated:* same as 4 for `auth.appleSignIn` (`showApple` resolved as above). **RED** for the same reason.

**`__tests__/LoginScreen.consent.w3-16.test.tsx`** (harness = `AuthScreens.socialDiagnostic.pa8.test.tsx` Login block; `getByTestId('login-social-google')` / `'login-social-apple'`)
6. *Google/Apple gated on Login:* unticked → `signInWithGoogle` NOT called + `consent-error`; ticked → called with the payload. **RED:** probe = `[]`. *Mutation:* remove the Login guard → red.
7. *Email/password Sign in is NOT gated* (preserve pin, green today and after): fill email+password, leave the box unticked, press `auth.signIn` → `login` called. *Mutation:* gate `handleLogin` on the box → red. (Decoration otherwise — the mutation is the point.)

**`__tests__/services/authService.consent.w3-16.test.ts`** (harness = `authService.b4.test.ts:1-40` — virtual `@react-native-google-signin/google-signin` + Sentry mocks, `global.fetch = mockFetch`, `sentBodyFor()`; register via the axios `api.post` mock as in `authService.m18.test.ts`)
8. `register(e, p, { consent })` → posted body `toMatchObject({ terms_accepted: true, terms_version: TERMS_VERSION, age_attested: true })`. **RED:** body has no such keys (`:139-149`); `src/services/consent` absent. *Mutation:* drop the spread → red.
9. `register(e, p, {})` → posted body has NONE of the three keys (compat pin; green today). *Mutation:* spread unconditionally → red.
10. `signInWithGoogle(consent)` → fetch body has the three keys AND still `provider`/`id_token`; `signInWithApple(consent)` → same plus `nonce`. **RED:** `:718` / `:868-872` ignore any argument (the functions take none today, `:665` / `:814`). *Mutation:* ignore the argument → red. (`signInWithGoogle()` with no args stays exactly `{provider,id_token}` — already pinned by `authService.b4.test.ts:170`; do not duplicate.)

**`__tests__/App.legalRouteHoist.w3-16.test.ts`** (static source pin in the `App.distinctRouteNames.test.ts` style — that file's regex `/<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g` is the one to reuse; a render of `App.tsx` is not feasible under the jest setup — `App.navigation.test.tsx:36-39` records why: "runtime require pulls i18n init which is not module-safe in the jest node env")
11. **[CORRECTED]** Position ONLY: the index of `name="Legal"` in `App.tsx` is GREATER than the index of `name="InviteeQuiz"` (i.e. registered at navigator level after the hoisted pair) and LESS than the index of `</Stack.Navigator>`. **RED:** today `name="Legal"` is at `:416`, `name="InviteeQuiz"` at `:507`, `</Stack.Navigator>` at `:508`. *Mutation:* move `Legal` back inside the authenticated branch → red. The "exactly one `name="Legal"`" count is NOT re-asserted here — `App.distinctRouteNames.test.ts` (existing, 3 tests, green) already reds on any duplicate and is in the gate (§6); duplicating it would be decoration.

i18n: no new test — adding `t('auth.consent.*')` to `ConsentRow.tsx` turns `no-missing-referenced-keys.test.ts` RED until both catalogs carry the keys, and `i18n.test.ts` / `no-deleted-keys.test.ts` RED if only one does. Those three ARE the gate.

### 5-B. Backend (pytest) — `tests/test_consent_capture_w3_16.py`

Harness: `TestClient(app)` + the `_disable_limiter` autouse fixture (`tests/test_auth_routes_invite_fingerprint.py:18-25`) and the route-boundary `AsyncMock` patch (`:28-41`); service tests use the `MagicMock` admin/auth clients from `tests/test_auth_interceptor.py::test_register_user_success` (`:422`) and `::test_sign_in_with_social_service_success` (`:1024`). Flags via `monkeypatch.setenv/delenv` (the `test_b2_strict_optional_auth.py:57-60` autouse `delenv` + `:101-113` per-call idiom); every test starts with BOTH flags `delenv(raising=False)`.

1. *Route passes parsed consent through (flags OFF):* `POST /register` with the three fields → 200 and `register_user.call_args.kwargs["consent"]` is a dict with `terms_version == "2026-03-26"` and ISO timestamps; without them → 200 and `kwargs["consent"] is None`. **RED:** today `register_user` is called positionally with `('u@example.com','ValidP@ss123')` and `kwargs = {}` (§10.5 block 2) → `KeyError`. *Mutation:* stop threading `consent` → red.
2. *REQUIRED ON rejects a bare register before any account exists:* `setenv("ENABLE_CONSENT_REQUIRED","true")`, `POST /register` `{email,password}` → **400**, JSON `success is False`, `code == "TERMS_ACCEPTANCE_REQUIRED"`, and `register_user` NOT called. **RED:** 200 today. *Mutation:* move the check after `register_user` → the not-called assertion reds.
3. *Both attestations are required:* REQUIRED ON, `terms_accepted: true` + `terms_version` but `age_attested` absent → 400; `age_attested: true` but `terms_accepted` absent → 400; all three → 200. **RED:** 200 today. *Mutation:* `or` instead of `and` in `consent_from_fields` → red.
4. *REQUIRED OFF is byte-identical for the bare body:* flags unset, bare `POST /register` → 200 (pins today's contract; green today). *Mutation:* default the flag ON → red.
5. *PERSIST ON writes the columns:* `register_user("new@test.com","pw", consent={…})` with `setenv("ENABLE_CONSENT_PERSIST","true")` → `insert.call_args.args[0]` == `{"id","email","subscription_tier":"free","terms_accepted_at","terms_version","age_attested_at"}` (exact key set). **RED:** `TypeError: unexpected keyword argument 'consent'` today (signature `('email','password')`, §10.5 block 4). *Mutation:* drop `**consent_columns(consent)` → red.
6. *PERSIST OFF is byte-identical even with consent supplied:* flags unset, same call → insert dict `== {"id": "new-id", "email": "new@test.com", "subscription_tier": "free"}` EXACTLY. **RED** today (TypeError); after the fix it is the byte-identity pin. *Mutation:* merge unconditionally → red.
7. *Social NEW account, REQUIRED ON, no consent → refused, no row:* `existing` mock `data=[]`, `sign_in_with_social("google","a.b.c")` → `{"success": False, "code": "TERMS_ACCEPTANCE_REQUIRED", …}` and `table().insert` NOT called. **RED:** success True + insert called today (§10.5 block 5). *Mutation:* put the check after the insert → red.
8. *Social EXISTING account, REQUIRED ON, no consent → signed in:* `existing` mock `data=[{"id": "x"}]` → `success True`, insert NOT called. GREEN today (no kwarg is passed here) — it is the pin that the gate never touches existing users. *Mutation:* gate before the `existing` lookup → red.
9. *Social NEW account, PERSIST ON, consent given → row carries the columns:* insert dict key set == `{"id","email","auth_provider","subscription_tier","terms_accepted_at","terms_version","age_attested_at"}`. **RED:** TypeError today (signature `('provider','id_token','nonce')`). *Mutation:* as 5.
10. *Route maps the code to 400, not 401:* patch `app.api.auth_routes.sign_in_with_social` → `{"success": False, "code": "TERMS_ACCEPTANCE_REQUIRED", "error": "x"}`; `POST /social-login` → **400** with `code == "TERMS_ACCEPTANCE_REQUIRED"`; a plain `{"success": False, "error": "Invalid token"}` still → **401** (`tests/test_social_login_smoke.py:131-143` also pins the 401). **RED:** 401 today for both (`auth_routes.py:854-855`). *Mutation:* map every failure to 400 → the second half reds.
11. *Per-call reads, independent flags:* with the module already imported, `setenv` REQUIRED → bare register 400; `delenv` → 200 again, in the SAME test (no reload); PERSIST ON + REQUIRED OFF → `register_user` receives `consent=None` for a bare body and the insert path writes nothing (no coupling). *Mutation:* cache the env at import → red.
12. *Cross-language `TERMS_VERSION` parity:* `consent_service.TERMS_VERSION == "2026-03-26" == (await legal_routes.get_terms_of_service())["last_updated"]` (`legal_routes.py:36` is `async def`; the literal is at `:47`) and equals the `TERMS_VERSION = '…'` literal regex-read from `SmartCompareApp/src/services/consent.ts` (the `test_security_regression.py:510` `Path("SmartCompareApp/…").read_text()` pattern). **RED:** neither module exists. *Mutation:* bump one side → red. (This test reads `SmartCompareApp/` → it joins the mobile comm set per `CLAUDE.md:714`.)
13. *Migration 038 is additive and reversible (static):* `migrations/038_users_consent_capture.sql` exists, contains exactly three `ADD COLUMN IF NOT EXISTS` (`terms_accepted_at`, `terms_version`, `age_attested_at`), no `NOT NULL`, no `DROP`, names its rollback; `migrations/rollback/038_users_consent_capture.sql` exists with three `DROP COLUMN IF EXISTS`. **RED:** files absent. *Mutation:* add `NOT NULL` → red.

## 6. Preserve — behaviours that must stay identical, with the proof

| behaviour | proof |
|---|---|
| Bare `POST /register` `{email,password}` → 200 with flags OFF (phones on 97b5f15 / pending OTA) | §5-B.4 + existing `tests/test_auth_routes_invite_fingerprint.py`, `test_register_invite_linking.py`, `test_referral_must_fixes.py` (all patch `register_user` and post bare bodies; they run in the gate) |
| `register_user` insert dict with flags OFF is byte-identical | §5-B.6 + `tests/test_auth_interceptor.py::test_register_user_success` (`:422`) |
| Social existing-account sign-in never gated; new-account insert unchanged with flags OFF | §5-B.8, §5-B.9's OFF sibling; `test_auth_interceptor.py::test_sign_in_with_social_service_success` (`:1024`, asserts `insert.assert_called_once()` at `:1056`) and `::test_sign_in_with_social_existing_user` (`:1060`, `insert.assert_not_called()` at `:1092`) |
| `/social-login` failure envelope stays 401 for non-consent failures | §5-B.10 second half + `tests/test_social_login_smoke.py:131-143` |
| Positional `sign_in_with_social(provider, id_token)` / `(…, nonce)` callers keep working | `test_auth_interceptor.py:1050` (positional two-arg) — in the gate |
| `GET /api/v1/legal/*` untouched (`last_updated` present, date-formatted) | `tests/test_legal_routes.py` (11 tests, green at base) — in the gate because §5-B.12 imports `legal_routes` |
| Google social body with no consent is EXACTLY `{provider,id_token}` | `__tests__/services/authService.b4.test.ts:170` — in the gate, unmodified |
| `register(e,p,{})` sends no consent keys | §5-A.9 |
| Email/password login needs no checkbox | §5-A.7 |
| Register's email-confirmation card, invite-code/invite-id forwarding, clipboard consent banner | the 3 `RegisterScreen.*` suites, edited ONLY by adding the tick precondition (§4.2) |
| P-A8 diagnostic-never-rendered and A8 deadline copy on both screens | `AuthScreens.socialDiagnostic.pa8` / `socialTimeout.a8` — tick precondition only |
| B9 Login back-arrow / no phantom latch | `LoginScreen.noopControls.b9.test.tsx` — untouched, must stay green |
| **Every `Stack.Screen` name registered exactly once** (the v7 duplicate-name trap the hoist could reintroduce) | `__tests__/App.distinctRouteNames.test.ts` (existing, 3 tests) — untouched, must stay green |
| `LegalScreen` itself unchanged | `__tests__/LegalScreen.test.tsx` (existing, 7 tests) — untouched |
| Deep links `c/:share_token`, `q/:share_token`, `r/:code` and the ReferralLanding/InviteeQuiz root registration | `App.tsx:350-379` untouched; §5-A.11 pins Legal is registered AFTER InviteeQuiz, not instead of it |
| EN/AR key parity and count | `__tests__/i18n.test.ts`, `__tests__/i18n/no-deleted-keys.test.ts` |
| RTL directional-icon wiring table | `__tests__/rtl/directionalIconWiring.contract.test.ts` — ConsentRow adds no `ArrowLeft/ChevronLeft/ChevronRight` |
| 2 baselined failures in `tests/test_auth_interceptor.py` (`test_sign_in_with_social_exception` `:1114`, `test_social_login_user_insert_fails_gracefully` `:1507`; `tests/.pre_impl_failures.txt:79-80` — the `[B4-BE-DIAG]` string from `auth_service.py:198-202`) stay EXACTLY 2 | comm gate base-vs-head diff (§7) |

## 7. Gates

**Client (from `SmartCompareApp`, tools by path):**
1. Red-first: §5-A.1-6, 8, 10, 11 must FAIL for the stated reason before any source edit; §5-A.7 and 9 must PASS before and after (pins).
2. Unit files: the four new `__tests__/*w3-16*` files.
3. Neighbour suites. The module-reference grep at `ed75dc70` — `grep -rlE "App\.tsx|screens/(Register|Login)Screen|services/authService|i18n/(en|ar)\.json|components/ConsentRow|services/consent" __tests__ src --include="*.test.ts" --include="*.test.tsx"` — returns **90 files** (§10.4; over-inclusive because `App.tsx` appears in comments, which is the safe direction). The green phase runs that 90-file set plus the four new files. **Core-subset baseline measured at `ed75dc70` (two runs, identical): 15 suites / 180 passed / 8 todo / 188 total / 10.3 s** for `RegisterScreen.{inviteCode,inviteId,emailConfirmation.m18,deferredCode}`, `AuthScreens.{test,socialDiagnostic.pa8,socialTimeout.a8}`, `LoginScreen.noopControls.b9`, `services/authService.{b4,socialTimeout.a8}`, `authService.m18`, `i18n.test`, `i18n/no-missing-referenced-keys`, `i18n/no-deleted-keys`, `Screens.bundleD.contract`; **+ `App.distinctRouteNames.test.ts` + `LegalScreen.test.tsx` = 17 suites / 190 passed / 8 todo / 198 total / 11.7 s** (§10.7). Re-run the grep at green time to catch any suite this list misses.
4. `node node_modules/typescript/bin/tsc --noEmit` (installed 5.9.3; never bare `npx`).
5. `node node_modules/eslint/bin/eslint.js App.tsx src/screens/RegisterScreen.tsx src/screens/LoginScreen.tsx src/services/authService.ts src/services/consent.ts src/components/ConsentRow.tsx <new test files>` — the `i18next/no-literal-string` rule applies to `src/screens/**` and `src/components/**` (`eslint.config.js:49-58`, `mode: 'jsx-text-only'`): every JSX text in `ConsentRow` goes through `t()`.
6. Full jest suite ONCE in the green phase (baseline at ece0fbbe: 2,729 passed / 0 failed / 278 suites / 44 snapshots).

**Backend (worktree root):**
1. Red-first: §5-B.1-3, 5-7, 9, 10, 12, 13 FAIL for the stated reason; §5-B.4, 8 PASS before and after.
2. `PYTHONIOENCODING=utf-8 python -m pytest tests/test_consent_capture_w3_16.py -q -p no:randomly -p no:cacheprovider`.
3. Comm gate (module-reference set, base `ed75dc70` vs head) = the UNION of: (a) `grep -rlE "register_user|sign_in_with_social|/auth/register|/auth/social-login|auth_routes|auth_service" tests/ --include="*.py"` → **43 `.py` files = 41 `test_*.py` + `conftest.py` + `_env_safety.py`** (§10.4; the unfiltered grep lists 52 paths, the extra 9 being `__pycache__/*.pyc`, `.pre_impl_failures.txt`, `PRE_IMPL_FAILURE_BASELINE.md`, `integration/bundle-e-smoke.sh` — exclude those); includes `test_auth_interceptor.py`, `test_social_login_smoke.py`, `test_auth_routes_invite_fingerprint.py`, `test_register_invite_linking.py`, `test_referral_must_fixes.py`, `test_account_deletion.py`, `test_referral_e2e.py`, `test_b2_strict_optional_auth.py`, `test_auth_refresh_and_revocation.py`, `test_security_regression.py`, …; (b) `tests/test_legal_routes.py` (the only file naming `legal_routes`; §5-B.12 imports it); (c) the mobile comm set `grep -rl "SmartCompareApp" tests/` → **9 files** (§10.4; `CLAUDE.md:714`); (d) **the 16 files that read `migrations/`** (`grep -rlE "migrations[/\"']|MIGRATIONS_DIR" tests/ --include="*.py"`, §10.4) because 038 is a new file they will glob — `test_migration_037_security_definer_grants.py` (`:295` `MIGRATIONS_DIR.glob("*.sql")`, `:299` + rollback), `test_migration_index_predicate_immutability.py` (`:81`), `test_sqlfluff_config.py`, `test_delete_user_cascade.py`, `test_migration_02{3,7,8,9}*.py`, `test_migration_03{0,1,2}*.py`, `test_m13_29_feedback_uuid.py`, `test_eval_persistence.py`, `test_preference_history_wiring.py`, `test_referral_full_response_column.py`, `test_security_regression.py`; (e) the unit file. **Base measured on the 7 closest files: 201 passed / 2 failed** (both in `.pre_impl_failures.txt:79-80`; §10.7). Head must show **branch-only-NEW = ∅**. Never `live_db` / `live_unit` / `integration` markers, never `LIVE=1`.
4. `python -m ruff check --select E9,F63,F7,F82 app/ tests/` (installed ruff 0.16.5 = the dev-lock pin; SQL is not ruff's business — `.sqlfluff` exists at the root and `.githooks/pre-commit` lints staged migrations if sqlfluff is installed, `test_sqlfluff_config.py:127`).
5. Byte-identity: N/A as an artifact; the flag-OFF pins are §5-B.4/6/8 + the insert-dict equality.
6. Fable review before commit. Agents never commit.

**Local-vs-CI caveat (must be in the PR):** pytest here runs fastapi 0.115.0 / starlette 0.38.6 / pydantic 2.7.0 (pins 0.141.1 / 1.6.0 / 2.13.4). The three new pydantic fields are plain `Optional` with a `max_length` — the shape that the 2026-09-01 drift incident showed to be stable — but the CI run is the authority; a local green is not a claim.

## 8. What this unit CANNOT do / Ahmed dependencies / device-or-store-only

**Cannot (by design):** flip either flag; apply 038; make consent effective for accounts created before the flags; redraft the DRAFT legal docs; know whether Apple/Google accept a single-checkbox attestation for the 12+/Teen rating (they generally do, but the reviewer decides); test a real Google/Apple SDK round trip or a real Supabase `sign_in_with_id_token` (jest and pytest both mock the SDK/provider boundary).

**Ahmed dependencies, in order:**
1. **Confirm the gate SHAPE** (§4.1: single checkbox vs alternatives 1/4). Client-only swap; do it before the client half is built, not after.
2. **Apply migration 038** (with 033-037, still unapplied) → then `ENABLE_CONSENT_PERSIST=true` on `web`. Nothing written before that.
3. **`eas update --branch preview --clear-cache`** from a main that contains this client half → phones stop sending bare registrations → then `ENABLE_CONSENT_REQUIRED=true`. Flipping REQUIRED before the OTA rejects every registration from phones on 97b5f15 (400 `TERMS_ACCEPTANCE_REQUIRED`; those clients render the envelope's `error` string — `parseApiError` at `api.ts:969-970` returns `data.error` when present, and `RegisterScreen.tsx:240` does `setError(parseApiError(err).message)` — legible English, unlocalised). **Canary line:** count of `TERMS_ACCEPTANCE_REQUIRED` 400s on `/register` + `/social-login` after the flip — any non-zero rate = phones without the OTA.
4. **Legal-doc redraft (ship-blocker #2)** and then bump `TERMS_VERSION` in BOTH `SmartCompareApp/src/services/consent.ts` and `app/services/consent_service.py` (§5-B.12 fails if only one moves) AND `legal_routes.py:30/:47` `last_updated`.
5. **Re-consent policy** for accounts created before REQUIRED went on (and on every version bump): a post-auth gate keyed on `users.terms_version != TERMS_VERSION` is a separate unit, not this one.
6. **Store side:** App Store age rating 12+, Play "Teen" questionnaire, Data Safety form — nothing in code.

**Only a device or the store can verify:** the checkbox's 44-pt hit target and RTL mirroring on a phone (jest cannot read `StyleSheet`-frozen layout); that `Legal` opens as a modal from the unauthenticated stack on-device (jest pins only the registration order, §5-A.11); the Google/Apple picker re-prompt UX after a first unticked tap; that the reviewer accepts the attestation wording; Arabic copy of the three new keys read by a native speaker (the walkthrough CLAUDE.md already owes).

## 9. PR-body facts (every sentence, with numbers)

* Finding: W3-16 consent capture (critic gap (c), Fable-verified) + the Legal-hoist half of MB-FLOWS-STATE-08. Base `ed75dc70`.
* At base, zero hits for any ToS acceptance or age attestation in `SmartCompareApp/src`, `App.tsx`, `app/`, `migrations/`; `POST /register` and `POST /social-login` return 200 with no consent; the `users` inserts are `{id,email,subscription_tier}` / `{id,email,auth_provider,subscription_tier}`; `RegisterRequest`/`SocialLoginRequest` silently drop `terms_accepted`/`terms_version`/`age_attested` (pydantic default `extra` ignore, probed on 2.7.0).
* Shape shipped: one checkbox "I am 13 or older and I agree to the Terms and Privacy Policy" gating Create Account + Google + Apple on Register and Google + Apple on Login (email/password Sign in ungated); Terms/Privacy spans open `Legal` via `navigation.getParent()?.navigate` (type-checked on tsc 5.9.3), and `Legal` is hoisted to navigator level (after `InviteeQuiz`; `App.distinctRouteNames` still green). Shape confirmed by Ahmed on <date> / or: pending, alternatives §4.1.
* Payload: `terms_accepted: true`, `terms_version: "2026-03-26"`, `age_attested: true`, sent on `/register` (axios) and `/social-login` (fetch) ONLY when the screen passes a consent object; `signInWithGoogle()` with no argument still posts exactly `{provider,id_token}` (b4 pin unchanged).
* Backend: three optional request fields on both models; `ENABLE_CONSENT_PERSIST` (default OFF, per-call) writes `users.terms_accepted_at/terms_version/age_attested_at` on the insert; `ENABLE_CONSENT_REQUIRED` (default OFF, per-call) → `400 {"success":false,"code":"TERMS_ACCEPTANCE_REQUIRED"}` on `/register` (before any Supabase account is created) and on `/social-login` for a NEW account only (no `public.users` row written; existing accounts never gated). Both flags OFF: insert dicts byte-identical (pinned), bare bodies 200 (pinned), non-consent social failures still 401 (pinned).
* Migration 038 (`users` +3 nullable columns, `IF NOT EXISTS`, rollback file) is written and **UNAPPLIED**; rollout order in the file header: 038 → PERSIST → OTA → REQUIRED.
* Client is OTA-safe (no `app.json`/plugin/native dep); backend is a deploy; nothing native.
* Tests: N new client tests in 4 files (list), 13 backend tests in 1 file; 24 existing press sites in 7 files gained a tick-the-box precondition, assertions unchanged. Full jest: X passed / 0 failed / 282 suites (baseline 2,729 / 278). Comm gate: base 201 passed / 2 baselined on the 7 closest files; head over the 41 + 1 + 9 + 16 module-reference set: branch-only-NEW = ∅; `tsc` 0 errors on 5.9.3; eslint 0 on the changed files; ruff `E9,F63,F7,F82` clean on 0.16.5.
* Local pytest ran on fastapi 0.115.0 / pydantic 2.7.0 vs pins 0.141.1 / 2.13.4 — CI is the authority.
* i18n: +3 flat keys in en.json and ar.json (parity + referenced-key fences green).
* Ahmed: shape confirmation; apply 038 then PERSIST; OTA then REQUIRED; bump `TERMS_VERSION` in both constants + `legal_routes.py` when the redraft lands; re-consent policy is a separate unit; store questionnaires.
* Not done here: Paywall legal links (STATE-03), `version` on the legal endpoints, re-consent for existing accounts, DOB collection, an `errorCopy.ts` entry for `TERMS_ACCEPTANCE_REQUIRED`.

## 10. Measurements run — command → observed output (all re-run 2026-09-11 at `ed75dc70`)

**10.1 base + repo greps**
```
$ git rev-parse HEAD
ed75dc708b82c0b911c9de8a3e59d4418c6e278c
$ git log -1 --format='%H %cd %s'
ed75dc708b82c0b911c9de8a3e59d4418c6e278c Fri Sep 11 00:46:43 2026 +0300 Merge pull request #154 from KGRddhs/docs/session-65-part4
$ git status --short | wc -l
0
$ grep -rniE "terms_accepted|termsAccepted|acceptedTerms|terms_version|termsVersion|age_gate|ageGate|is_over_13|over13|attest" SmartCompareApp/src app/ SmartCompareApp/App.tsx migrations/ docs/CONTEXT_DATABASE_API.md | grep -viE "anon_usage_gate"
Binary file app/api/__pycache__/image_routes.cpython-312.pyc matches
Binary file app/api/__pycache__/text_routes.cpython-312.pyc matches
Binary file app/services/__pycache__/usage_service.cpython-312.pyc matches
  → 0 source hits (the source matches are all `anon_usage_gate_enabled`; the three .pyc are the compiled forms of those same files)
$ ls migrations/ | tail -3 ; ls migrations/rollback/ | tail -2
035_spec_spine.sql 036_home_savings_aggregate.sql 037_security_definer_grants_and_rls.sql (+ add_share_token.sql, rollback/) · rollback: 036_… 037_…
```

**10.2 versions**
```
$ node node_modules/typescript/bin/tsc -v            → Version 5.9.3
jest 29.7.0 · ts-jest 29.4.9 · @testing-library/react-native 13.3.3 · react-native 0.81.5 · expo 54.0.34 · react-i18next 17.0.7 · axios 1.20.0
@react-navigation/core 7.17.4 · @react-navigation/native 7.2.4 · @react-navigation/native-stack 7.15.0
package.json pins: typescript ~5.9.2 · jest ^29.7.0 · ts-jest ^29.4.6 · @testing-library/react-native ^13.3.3 · react-native 0.81.5 · expo ~54.0.33 · react-i18next ^17.0.1 · axios ^1.20.0 · @react-navigation/native ^7.1.28 · native-stack ^7.12.0
node_modules/@babel/core present · node_modules/.bin/jest + jest.cmd present
$ python --version → Python 3.12.9
$ python -c "import fastapi,pydantic,supabase,supabase_auth,starlette; print(...)"
fastapi 0.115.0 pydantic 2.7.0 supabase 2.28.0 supabase_auth 2.28.0 starlette 0.38.6
requirements.txt: fastapi==0.141.1 (:47) pydantic==2.13.4 (:109) starlette==1.6.0 (:150) supabase==2.31.0 (:156) supabase-auth==2.31.0 (:158)
$ python -m ruff --version → ruff 0.16.5
```

**10.3 pydantic extra-field default (installed 2.7.0)**
```
$ python -c "from pydantic import BaseModel
class R(BaseModel): email: str
r = R.model_validate({'email':'a@b.c','terms_accepted':True}); print(r.model_dump(), R.model_config.get('extra'))"
{'email': 'a@b.c'} None
$ grep -nE "model_config|ConfigDict|extra=" app/api/auth_routes.py
264:    model_config = {"extra": "ignore"}          # AttributionBody, not RegisterRequest
```

**10.4 test-set enumeration**
```
$ grep -rlE "register_user|sign_in_with_social|/auth/register|/auth/social-login|auth_routes|auth_service" tests/ | wc -l        → 52 (incl. 7 __pycache__/*.pyc, .pre_impl_failures.txt, PRE_IMPL_FAILURE_BASELINE.md, integration/bundle-e-smoke.sh)
$ … --include="*.py" | wc -l                                                                                                        → 43 (41 test_*.py + tests/conftest.py + tests/_env_safety.py)
$ grep -rlE "legal_routes|consent_service" tests/                                                                                   → tests/test_legal_routes.py
$ grep -rl "SmartCompareApp" tests/
tests/test_b2_strict_optional_auth.py tests/test_events_allowlist_superset.py tests/test_feature_bucket_parity.py tests/test_feedback_allowlist_superset.py tests/test_migration_037_security_definer_grants.py tests/test_paid_route_metering.py tests/test_review_paraphrase.py tests/test_security_regression.py tests/test_timeout_partial_integration.py   (9)
$ grep -rlE "migrations[/\"']|MIGRATIONS_DIR" tests/ --include="*.py"
tests/test_delete_user_cascade.py tests/test_eval_persistence.py tests/test_m13_29_feedback_uuid.py tests/test_migration_023.py tests/test_migration_027_comparison_feedback_correctness.py tests/test_migration_028_pain_workflow_events.py tests/test_migration_029_user_preference_history.py tests/test_migration_030_verdict_critiques.py tests/test_migration_031_eval_runs.py tests/test_migration_032_b1_pre_hardening.py tests/test_migration_037_security_definer_grants.py tests/test_migration_index_predicate_immutability.py tests/test_preference_history_wiring.py tests/test_referral_full_response_column.py tests/test_security_regression.py tests/test_sqlfluff_config.py   (16)
$ grep -rnE "patch\([\"'](app\.)?(api\.auth_routes|services\.auth_service)\.(register_user|sign_in_with_social)" tests/
tests/test_auth_interceptor.py:288,299,970,990,1013 · tests/test_referral_e2e.py:238 · tests/test_referral_must_fixes.py:135,171,194
(client) $ grep -rlE "App\.tsx|screens/(Register|Login)Screen|services/authService|i18n/(en|ar)\.json|components/ConsentRow|services/consent" __tests__ src --include="*.test.ts" --include="*.test.tsx" | wc -l   → 90
```

**10.5 backend probe** — `PYTHONIOENCODING=utf-8 python .qa-w3b/probes/probe_w316_backend.py` (conftest's `neutralize_credentials()` + `install_dotenv_guard()` replicated before `app.main` import; log lines confirm "Redis not configured", "SENTRY_DSN not set"; re-run output identical to the draft's)
```
== 1. Pydantic models silently DROP consent fields sent by a new client ==
RegisterRequest.model_dump() = {'email': 'u@example.com', 'password': 'ValidP@ss123', 'invite_id': None, 'invite_code': None}
RegisterRequest field names  = ['email', 'invite_code', 'invite_id', 'password']
SocialLoginRequest.model_dump() = {'provider': 'google', 'id_token': 'a.b.c', 'nonce': None}
== 2. POST /register WITHOUT any consent -> 200 today (route boundary patched) ==
status = 200 | register_user called with args = ('u@example.com', 'ValidP@ss123') kwargs = {}
== 3. POST /social-login WITHOUT any consent -> 200 today ==
status = 200 | sign_in_with_social called with args = ('google', 'a.b.c', None) kwargs = {}
== 4. register_user(): the users INSERT dict has NO consent columns ==
register_user insert dict = {'id': 'new-id', 'email': 'new@test.com', 'subscription_tier': 'free'}
register_user signature   = ('email', 'password')
== 5. sign_in_with_social(): FIRST social sign-in creates the users row here, with NO consent columns ==
sign_in_with_social insert dict = {'id': 'new-id', 'email': 'new@test.com', 'auth_provider': 'google', 'subscription_tier': 'free'}
sign_in_with_social signature   = ('provider', 'id_token', 'nonce')
== 6. flag names in the process env (must all be unset/OFF) ==
ENABLE_CONSENT_PERSIST = None
ENABLE_CONSENT_REQUIRED = None
```

**10.6 client probes** — from `SmartCompareApp`: `node node_modules/jest/bin/jest.js --ci --roots "C:/Users/SynAckITPC/Documents/AI/sc-w3-consent/.qa-w3b/probes" --testMatch "**/<file>" --modulePaths "C:/Users/SynAckITPC/Documents/AI/sc-w3-consent/SmartCompareApp/node_modules"` (rootDir stays `SmartCompareApp` so `jest.config.js` mappers (`:18-55`) + `setupFilesAfterEnv: __tests__/setup.ts` (`:57`) apply; `--roots`/`--testMatch` because the default testMatch (`jest.config.js:4`) is `**/__tests__/**/*.test.ts(x)`; `--modulePaths` because bare `react` does not resolve from outside the rootDir)

10.6a `w316_consent_absent.probe.test.tsx` (re-run, identical to the draft):
```
[PROBE] register() args = ["user@example.com","StrongPass1!",{}]
[PROBE] checkbox roles on RegisterScreen = 0
[PROBE] 'common.terms' text present = false
[PROBE] 'common.privacy' text present = false
[PROBE] Register google args = []
[PROBE] Login google args = []
[PROBE] checkbox roles on LoginScreen = 0
Test Suites: 1 passed, 1 total · Tests: 3 passed, 3 total · Time: 0.95 s
```

10.6b `w316_role_query.probe.test.tsx` (NEW — harness control for §5-A.1; `Pressable`/`TouchableOpacity` from the mocked `react-native`, `accessibilityRole="checkbox"` + `accessibilityState={{ checked }}`):
```
[PROBE] Pressable: role=checkbox found, checked filter works, press toggles
[PROBE] TouchableOpacity: role=checkbox found, checked filter works, press toggles
Test Suites: 1 passed, 1 total · Tests: 2 passed, 2 total
```

10.6c `w316_getParent_typing.probe.tsx` (NEW — typing control for §4.2; run with the `expo/tsconfig.base.json` flags replicated on the CLI because the file is outside the project: `node node_modules/typescript/bin/tsc --noEmit --strict --jsx react-native --esModuleInterop --moduleResolution bundler --module preserve --target ESNext --lib DOM,ESNext --skipLibCheck --customConditions react-native --resolveJsonModule --types jest,node ../.qa-w3b/probes/w316_getParent_typing.probe.tsx`). Three `ok` lines (`getParent()?.navigate`, `(navigation as any).navigate`, typed `getParent<RootStack…>()`) compile; the two negative controls are the ONLY errors:
```
w316_getParent_typing.probe.tsx(32,23): error TS2345: Argument of type '["Legal", { doc: string; }]' is not assignable to parameter of type '[screen: "Login", …] | [screen: "Register", …] | [screen: …]'.   ← bad1: navigation.navigate('Legal', …) from AuthStackParamList
w316_getParent_typing.probe.tsx(34,117): error TS2322: Type '"cookies"' is not assignable to type '"privacy" | "terms"'.   ← bad2: wrong param under the typed parent
tsc exit=2
```

**10.7 baselines at ed75dc70**
```
$ PYTHONIOENCODING=utf-8 python -m pytest tests/test_auth_routes_invite_fingerprint.py tests/test_social_login_smoke.py tests/test_auth_interceptor.py tests/test_register_invite_linking.py tests/test_referral_must_fixes.py tests/test_account_deletion.py tests/test_legal_routes.py -q -p no:randomly -p no:cacheprovider
FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception
FAILED tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
2 failed, 201 passed, 19 warnings in 12.24s
  → both listed in tests/.pre_impl_failures.txt:79-80 (CI deselects); the draft's 190/2 was the same set minus test_legal_routes.py (11 tests).

$ node node_modules/jest/bin/jest.js --ci <15 core suites, §7.3>          (run twice)
Test Suites: 15 passed, 15 total · Tests: 8 todo, 180 passed, 188 total · Time: 10.271 s
$ … <the 15 + App.distinctRouteNames.test.ts + LegalScreen.test.tsx>
Test Suites: 17 passed, 17 total · Tests: 8 todo, 190 passed, 198 total · Time: 11.665 s
  (the draft recorded 181/189 for the 15-suite set; two fresh runs both give 180/188 — use 180/188.)
```

**10.8 existing press sites a consent gate intercepts (grep re-run, §4.2 table)** — 24 sites: Register `auth.register` ×8 (inviteCode :104/:126/:137, inviteId :99/:116, emailConfirmation :80/:97/:116); Register Google ×4 (socialDiagnostic :236/:246, socialTimeout :136/:149, both via `getByText(EN['auth.googleSignIn'])`); Login Google/Apple ×12 (AuthScreens.test :120 `getAllByText('auth.googleSignIn')[0]` inside a `<LoginScreen>` render; socialDiagnostic :153/:165(apple)/:179/:190/:205/:214; socialTimeout :76/:89(apple)/:100/:112/:116). `LoginScreen.noopControls.b9` and `RegisterScreen.deferredCode`: 0.

**10.9 React Navigation bubbling (installed 7.17.4)** — `node_modules/@react-navigation/core/src/useOnAction.tsx:127-129`: `if (onActionParent !== undefined) { // Bubble action to the parent if the current navigator didn't handle it  if (onActionParent(action, visitedNavigators)) {`. `getParent` typing: `src/types.tsx:630` `getParent<T = NavigationProp<ParamListBase> | undefined>(id?: NavigatorID): T;`.

**10.10 anchors quoted in §3-§4 (all from `sed -n` / `grep -n` at ed75dc70)** — `RegisterScreen.tsx` `:71-72` (`Platform.OS === 'ios'` → `isAppleSignInAvailable().then(setShowApple)`), `:122`, `:149`, `:175`, `:222-225`, `:240`, `:249`, `:257`, `:381-426`, `:428-433`, `:442-448`, `:450`, `:467-473`, `:477-482` (715 lines); `LoginScreen.tsx` `:65`, `:74-103`, `:210`, `:238`, `:259`, `:314`, `:323`, `:382-409` (720 lines); `authService.ts` `:107-111`, `:139-149`, `:665`, `:718`, `:814`, `:868-872`; `App.tsx` `:350` `const linking`, `:385`, `:404`, `:414-419`, `:492-502`, `:503-507`, `:508`; `types.ts:599`, `:624`; `en.json:914-915` / `ar.json:911-912`; `LegalScreen.tsx:33-34`, `:53`; `InviteeQuizScreen.tsx:136`; `__mocks__/react-native.ts` `:18-19`, `:68-70`; `eslint.config.js:20-28`, `:49-58`; `jest.config.js:4`, `:57`; `auth_routes.py:79-87`, `:264`, `:268-271`, `:317-348`, `:408-410`, `:849-856`; `auth_service.py:198-202`, `:227-246`, `:551`, `:573`, `:580-587`, `:689`, `:712-715`; `legal_routes.py:19`, `:30`, `:36`, `:47`; `terms_of_service.md:5`, `:7`; `error_handler.py:74-91`; `api.ts:923`, `:969-970`; `CLAUDE.md:15`, `:420`, `:466`, `:468`, `:714`; `tos-fact-base.md:774`; `CONTEXT_DATABASE_API.md:83-92`, `:187-193`; `full-review.md:144`, `:192`; `-tables.md:209`, `:211`; `-verified.json:1972`, `:12735`; `.pre_impl_failures.txt:79-80`; `test_auth_interceptor.py:422`, `:1024`, `:1050`, `:1056`, `:1060`, `:1092`, `:1114`, `:1507`; `test_auth_routes_invite_fingerprint.py:18-25`, `:28-41`; `test_b2_strict_optional_auth.py:57-60`, `:101-113`; `test_security_regression.py:510`; `test_social_login_smoke.py:131-143`; `test_legal_routes.py:57`; `test_migration_037_security_definer_grants.py:295`, `:299`; `test_migration_index_predicate_immutability.py:81`; `migrations/033_…:1-26`, `rollback/033_…:1-12`; `migrations/011:28-29`, `014:11-13`, `015:13/18/27`.

**10.11 existing pin discovered during re-verification** — `__tests__/App.distinctRouteNames.test.ts:31` regex `/<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g`; `it('every Stack.Screen registers a distinct name')` asserts `duplicates` = `[]`. Green at base (§10.7, 17-suite run). This is why §5-A.11 pins position only.

---

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Adversarial re-measurement of every claim in §1-§10 above, run on **`b63a8368`** (see ruling 1), on the installed toolchain only. The spec is **sound**: the design is right, the flags are right, the OTA ordering is right, and every red test is red today for the reason stated. **Verdict: APPROVED_WITH_RULINGS.** The rulings below are corrections and additions; where a ruling contradicts the body above, **the ruling wins**. Rulings 7-10 are missed hazards that would have cost a rework.

### Ruling 1 — the base SHA in §1 is STALE. The unit is built on `b63a8368`, and every anchor still holds.

`git rev-parse HEAD` in this worktree = **`b63a8368b7910a946020438a5447bbcd6b792805`** ("Merge pull request #159 from KGRddhs/fix/s65-brittle-403-assert"), and `git rev-parse origin/main` = the same. `ed75dc70` is five merges behind: #155 (W3-2 comparison-id echo), #156 (W1-5 limiter endpoint key), #157 (W1-6 shutdown drain), #158 (W4-5 showable-name identity), #159 (brittle 403 assert). `git status --short | wc -l` = **0**.

`git diff --name-only ed75dc70 HEAD` touches 13 files: `Procfile`, `app/api/text_routes.py`, `app/main.py`, `app/middleware/rate_limiter.py`, `app/services/feedback_service.py`, `app/services/price_service.py`, `app/utils/async_utils.py`, `railway.json`, `tests/test_comparison_id_echo.py`, `tests/test_limiter_endpoint_key.py`, `tests/test_security_regression.py`, `tests/test_showable_name_identity.py`, `tests/test_shutdown_drain.py`. Filtering that list through `grep -iE "SmartCompareApp|auth_routes|auth_service|legal_routes|migrations|CONTEXT_DATABASE"` returns **nothing** — not one file this unit touches moved.

I re-located every `file:line` in §10.10 at `b63a8368`. **All of them hold unchanged**, including all four anchors the draft's resume agent had itself corrected (`authService.ts:718`, `:868-872`, `RegisterScreen.tsx:240`, `LoginScreen.tsx:259`). Two enumerations drifted (rulings 2-3) and one "correction" was wrong (ruling 4). Read every `ed75dc70` in the body above as `b63a8368`; the PR body (§9) must state `b63a8368`.

### Ruling 2 — the backend comm set is **44** `.py` files, not 43.

`grep -rlE "register_user|sign_in_with_social|/auth/register|/auth/social-login|auth_routes|auth_service" tests/ --include="*.py" | wc -l` → **44** at `b63a8368` (was 43 at `ed75dc70`). The added file is **`tests/test_comparison_id_echo.py`** (new in #155). §7 backend gate 3(a) reads 44 = 42 `test_*.py` + `conftest.py` + `_env_safety.py`. Re-run the grep at green time rather than trusting either number.

### Ruling 3 — the mobile comm set is **10** files, not 9.

`grep -rl "SmartCompareApp" tests/ | wc -l` → **10**: `test_b2_strict_optional_auth.py`, **`test_comparison_id_echo.py`** (new in #155), `test_events_allowlist_superset.py`, `test_feature_bucket_parity.py`, `test_feedback_allowlist_superset.py`, `test_migration_037_security_definer_grants.py`, `test_paid_route_metering.py`, `test_review_paraphrase.py`, `test_security_regression.py`, `test_timeout_partial_integration.py`. §7 backend gate 3(c) and the `CLAUDE.md:714` rule take **10**.

### Ruling 4 — §4.3's "[CORRECTED from `:186-192`]" on `docs/CONTEXT_DATABASE_API.md` is itself WRONG. Revert it.

Measured:

```
$ grep -n 'POST `/api/v1/auth/register`' docs/CONTEXT_DATABASE_API.md
186:### POST `/api/v1/auth/register`
$ awk 'NR>=186 && NR<=193' docs/CONTEXT_DATABASE_API.md
186: ### POST `/api/v1/auth/register`
187: ```json
188: {
189:   "email": "user@example.com",
190:   "password": "password123"
191: }
192: ```
193: (blank)
```

The block is **`:186-192`** — the draft's original anchor. The resume agent's "correction" to `:187-193` is off by one in both bounds. `docs/CONTEXT_DATABASE_API.md:83-92` (the `CREATE TABLE public.users` block) is **correct as written** and has no consent column. §10.10 must read `CONTEXT_DATABASE_API.md:83-92`, `:186-192`.

### Ruling 5 — two paths the spec leaves the red agent to guess. Use these verbatim.

* **`__tests__/services/authService.m18.test.ts` does not exist.** The file is **`SmartCompareApp/__tests__/authService.m18.test.ts`** (top level of `__tests__/`, not `__tests__/services/`). `__tests__/services/` holds only `authService.b4.test.ts` and `authService.socialTimeout.a8.test.ts`. §5-A.8's harness reference ("the axios `api.post` mock as in `authService.m18.test.ts`") means that top-level file. §7's core-subset list is already correct; running it with a `services/` prefix silently drops the suite and yields 16/187 instead of 17/198.
* **`error_handler.py` is `app/middleware/error_handler.py`**, not `app/utils/`. `_is_structured_detail` at `:74-91` confirmed; `http_exception_handler` at `:112` builds `content = {"success": False, "error": message, "code": code, "request_id": ...}` at `:131-136`, and `app/main.py:149` registers it (`app.add_exception_handler(HTTPException, http_exception_handler)`). The `TERMS_ACCEPTANCE_REQUIRED` envelope §4.3 describes is therefore real and reaches the wire under `TestClient(app)`.

### Ruling 6 — the new test files must NOT import the not-yet-existing modules at module scope. This invalidates three of the spec's "green today" PINs as written.

§5-A.9, §5-B.4 and §5-B.8 are declared "PIN, green today". They are **not**, as the files are specced:

* `__tests__/services/authService.consent.w3-16.test.ts` imports `TERMS_VERSION` from `src/services/consent` (tests 8 and 10). That module does not exist → **the whole suite fails to run** with `Cannot find module`, so test 9 is not "green today", it is un-runnable. Same for `RegisterScreen.consent.w3-16.test.tsx`: test 3's module-scope import reddens tests 1, 2, 4 and 5 on module resolution, not on the missing checkbox — the red is real but it is red for the WRONG reason, which is exactly what the red phase is supposed to rule out.
* `tests/test_consent_capture_w3_16.py` imports `app.services.consent_service` (B.12, B.5, B.6 …). A module-scope import fails **collection**, so B.4 and B.8 never run.

**Binding:**
1. **Backend:** every import of `app.services.consent_service` goes **inside the test function**, which is this repo's house idiom — `tests/test_auth_interceptor.py:424` (`from app.services.auth_service import register_user` inside the `async def`), `tests/test_register_invite_linking.py:123` (`from app.api.auth_routes import RegisterRequest` inside the `def`). Collection then succeeds and **only** the tests that need the new module red. B.4 and B.8 are then genuinely green before and after, as claimed.
2. **Client:** the red phase creates `SmartCompareApp/src/services/consent.ts` (the `TERMS_VERSION` constant, the `ConsentPayload` type and `buildConsentPayload` — pure, no imports, no UI, no wiring into any screen or service) as **step 0, before running the red tests**. Every other red then fires on its own assertion. Record both observations in the red log: the module-resolution failure first, then the assertion failures after step 0.
3. The tautology §5-A.3 / §5-A.8 create by reading `TERMS_VERSION` back is **closed by §5-B.12**, which ties `consent_service.TERMS_VERSION` to `legal_routes.get_terms_of_service()['last_updated']` (an independent literal at `legal_routes.py:47`) and regex-reads the client constant out of `consent.ts`. Keep B.12; without it the client assertions prove nothing about the value.

### Ruling 7 — the green-phase instruction "tick the box at the 24 press sites" BREAKS one existing test. One tick per RENDER, never per press.

Re-enumerated at `b63a8368`: the 24 sites are in the 7 stated files at exactly the stated lines (3+2+3+1+8+7 = 24; `LoginScreen.noopControls.b9` and `RegisterScreen.deferredCode` = 0). §4.2's enumeration is exact.

But 23 of the 24 are one press per `render()`, and **one is not**:

```
__tests__/AuthScreens.socialTimeout.a8.test.tsx
105:  it('releases the screen after a timeout (buttons are pressable again)', async () => {
111:    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
112:    fireEvent.press(screen.getByTestId('login-social-google'));
116:    fireEvent.press(screen.getByTestId('login-social-google'));
117:    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(2));
```

`:112` and `:116` are two presses against the **same render**. A checkbox is a TOGGLE: inserting `fireEvent.press(getByTestId('consent-checkbox'))` before each of them ticks it, then **un**ticks it, so the second Google press is blocked by the new guard and `toHaveBeenCalledTimes(2)` fails. **Binding: tick exactly once per `render()`/`renderLogin()`/`renderRegister()`/`renderScreen()` call, immediately after the render, not before each press.** In that file the single tick goes between `:111` and `:112` and `:116` is left alone. I verified the other six files: `AuthScreens.socialDiagnostic.pa8` renders fresh at `:152/:163/:178/:189/:204/:213/:235/:245` (one press each), `AuthScreens.test.tsx:116` renders once for `:120`, and all eight `auth.register` sites in the three `RegisterScreen.*` files are one press per `renderScreen()`.

### Ruling 8 — `ENABLE_CONSENT_REQUIRED=true` will turn the PROD SMOKE SCRIPT red. Name it before Ahmed flips.

Not mentioned anywhere in §7, §8 or §9. `scripts/bundle_d_prod_smoke.py` posts **bare** bodies against production:

```
297:            path="/api/v1/auth/register",
298:            expected_status=(200, 201),
303:                f"{base_url}/api/v1/auth/register",
304:                json={"email": test_email, "password": test_password},
```

and the same for `/api/v1/auth/social-login` at `:414-445` (apple parity, google baseline). With `REQUIRED` ON these three probes get **400 `TERMS_ACCEPTANCE_REQUIRED`** and the smoke reports a false regression at exactly the moment Ahmed is watching the canary.

**Binding:** the `ENABLE_CONSENT_REQUIRED` row in `CLAUDE.md` and Ahmed step 3 in §8 must state that `scripts/bundle_d_prod_smoke.py` probes 5, 10 and 11 need the three consent fields added to their bodies **before** the flag flips, or the flip must be announced as expected-red for those three probes. Editing that script is NOT in this unit's scope (it is a prod-touching script and no test covers it) — it is a named Ahmed precondition.

I checked for other non-mobile callers: there is no web signup. `landing/` is four static HTML pages (`index`, `privacy`, `support`, `terms`) with no form posting to `/auth/register`; the only `register`-ish hit is prose in `landing/terms.html:264`. The mobile client and this smoke script are the only callers.

### Ruling 9 — the terms-version literal lives in **SIX** places, not three. §8 step 4 undercounts and B.12 only pins half of them.

All six currently agree on 26 March 2026:

| file:line | literal |
|---|---|
| `app/api/legal_routes.py:30` | `"last_updated": "2026-03-26"` (privacy) |
| `app/api/legal_routes.py:47` | `"last_updated": "2026-03-26"` (terms) |
| `app/legal/terms_of_service.md:5` | `*Last Updated: March 26, 2026*` |
| `app/legal/privacy_policy.md:5` | `*Last Updated: March 26, 2026*` |
| `landing/terms.html:184` | `<p class="subtitle"><em>Last Updated: March 26, 2026</em></p>` |
| `landing/privacy.html:195` | `<p class="subtitle"><em>Last Updated: March 26, 2026</em></p>` |

Plus the two this unit adds (`consent_service.TERMS_VERSION`, `consent.ts` `TERMS_VERSION`) = eight. §5-B.12 pins only three of the eight (`consent_service` ↔ `legal_routes` ↔ `consent.ts`), so after the redraft the markdown and the two landing pages can drift silently while every test stays green — the "a number two documents disagree on" hazard, live. **Binding:** §8 step 4 must list all eight anchors above. Widening B.12 to cover the markdown and the landing HTML is explicitly **out of scope for this unit** (the landing pages are a separate deploy and the markdown date format differs) — record it as a follow-up, do not grow the unit.

### Ruling 10 — §6's Preserve row for `tests/test_register_invite_linking.py` states a false reason. Keep the file, fix the reason.

§6 says `test_auth_routes_invite_fingerprint.py`, `test_register_invite_linking.py` and `test_referral_must_fixes.py` "all patch `register_user` and post bare bodies". `grep -n "register_user\|/auth/register" tests/test_register_invite_linking.py` returns **nothing** — the file patches `app.services.referral_service.get_admin_supabase_client` (`:34, :52, :72, :88, :98, :114`) and tests `link_invite_to_user`. Its real relevance to this unit is stronger than the stated one: `class TestRegisterRequestAcceptsInviteId` constructs `RegisterRequest` **directly** —

```
122:    def test_invite_id_accepted_when_provided(self):
124:        from app.api.auth_routes import RegisterRequest
126:        req = RegisterRequest(email="x@example.com", password="ValidPass123!", invite_id="…")
132:    def test_invite_id_optional(self):
136:        req = RegisterRequest(email="x@example.com", password="ValidPass123!")
137:        assert req.invite_id is None
```

— so it is the direct pin that the three new `Optional` fields must not break. Both tests only assert `invite_id`, so adding `terms_accepted` / `terms_version` / `age_attested` as `Optional[...] = None` leaves them green; it stays in the gate for that reason. Correct the Preserve row's proof text accordingly. (`test_auth_routes_invite_fingerprint.py` and `test_referral_must_fixes.py` DO patch `register_user` and post bare bodies — those halves of the row are right; the `_disable_limiter` autouse fixture is at `:17-25`, `def` at `:18`.)

Related and confirmed safe: `grep -rn "register_user\|sign_in_with_social" tests/*.py | grep -iE "called_with|call_args|assert_called"` returns **nothing** — no test anywhere asserts an exact call signature on either function, so adding a defaulted `consent=` keyword is comm-safe, and the positional caller `test_auth_interceptor.py:1050` (`sign_in_with_social("google", "id-token-123")`) keeps working as §4.3 claims.

### Ruling 11 — naming: `consentRow` is already taken inside `RegisterScreen.tsx`. The specced testIDs are nonetheless safe; do not rename them.

`RegisterScreen.tsx` already carries the **iOS clipboard** consent banner: `testID="clipboard-consent-banner"` (`:345`), `styles.consentBanner` (`:346`), `styles.consentTitle` (`:348`), `styles.consentMessage` (`:351`), **`styles.consentRow` (`:356`)**, `testID="clipboard-consent-reject"` (`:358`), `styles.consentButton` / `styles.consentReject` (`:360`). The new component is also called `ConsentRow`.

I checked every existing query: `__tests__/RegisterScreen.deferredCode.test.tsx:116,124,134,139,158` are the only consent queries in the suite and all five are exact-string `clipboard-consent-*`; no `ByTestId(/regex/)` anywhere in `__tests__/` matches `consent` (the four regex-testID sites are `bars-row-*`, `stage-*-icon`, `image-slot-\d`). **`consent-checkbox` and `consent-error` are therefore unambiguous — keep them exactly as §4.1/§5 specify.** Two constraints follow: (a) the new row lives in its own file `src/components/ConsentRow.tsx` and must **not** add a `consentRow` key to `RegisterScreen.tsx`'s own `StyleSheet.create` (it already has one, for the clipboard banner's button row); (b) the new tests query by `testID`, never by the consent copy text, because the clipboard banner's strings render on the same screen.

### Ruling 12 — probe `w316_nested_text_press.probe.test.tsx` exists, passes, and is the direct evidence for §5-A.1. Fold it into §10.

`.qa-w3b/probes/` holds **four** probes; §10 reports three. The unreported one is the one that proves the §5-A.1 mechanism end to end. Re-run at `b63a8368`:

```
PASS ../.qa-w3b/probes/w316_nested_text_press.probe.test.tsx
  [PROBE] nested span presses = [["terms"],["privacy"]]
  [PROBE] parentNavigate calls = [["Legal",{"doc":"terms"}]]
```

A pressable `Text` nested inside a parent `Text` fires its own `onPress` under `__mocks__/react-native.ts`, and the `getParent?.()` optional-call form is a silent no-op on a navigation mock that lacks `getParent` — which is exactly why the 24 existing press sites stay green while §5-A.1 can still assert the navigate.

### Ruling 13 — the probe invocation in §10 is incomplete; without `--modulePaths` all three jest probes fail to resolve `react`.

`node_modules` here is a junction into `../../sc-scraper-proof/SmartCompareApp/node_modules`, and a probe living **outside** `rootDir` does not inherit that resolution. The command that works, run from `SmartCompareApp`:

```
node node_modules/jest/bin/jest.js --ci --rootDir . --roots ../.qa-w3b/probes \
  --testMatch "**/*.probe.test.tsx" \
  --modulePaths "C:/Users/SynAckITPC/Documents/AI/sc-w3-consent/SmartCompareApp/node_modules"
```

Without `--modulePaths` every probe dies with `Cannot find module 'react' from '../.qa-w3b/probes/…'`. This affects probes only — the four new unit test files live under `__tests__/` (inside `rootDir`) and run with a plain `node node_modules/jest/bin/jest.js --ci <path>`, as §7 gate 1 says. Never delete or reinstall that junction.

### Ruling 14 — everything below was re-measured and the spec is CORRECT. A red agent may rely on these without re-checking.

**Probes reproduce exactly at `b63a8368`.**

Backend (`PYTHONIOENCODING=utf-8 python .qa-w3b/probes/probe_w316_backend.py`) — all six blocks byte-for-byte as §10.5:

```
RegisterRequest.model_dump() = {'email': 'u@example.com', 'password': 'ValidP@ss123', 'invite_id': None, 'invite_code': None}
SocialLoginRequest.model_dump() = {'provider': 'google', 'id_token': 'a.b.c', 'nonce': None}
POST /register  status = 200 | register_user called with args = ('u@example.com', 'ValidP@ss123') kwargs = {}
POST /social-login status = 200 | sign_in_with_social called with args = ('google', 'a.b.c', None) kwargs = {}
register_user insert dict = {'id': 'new-id', 'email': 'new@test.com', 'subscription_tier': 'free'}   signature ('email', 'password')
sign_in_with_social insert dict = {'id': 'new-id', 'email': 'new@test.com', 'auth_provider': 'google', 'subscription_tier': 'free'}   signature ('provider', 'id_token', 'nonce')
ENABLE_CONSENT_PERSIST = None   ENABLE_CONSENT_REQUIRED = None
```

The `nonce` arriving **positionally** confirms §4.3's requirement that `consent` be threaded as a **keyword**. The silent-drop of the three fields on both models is the backward-compatibility property the whole rollout order rests on, and it is real.

Client (3 suites / 7 tests passed):

```
[PROBE] register() args = ["user@example.com","StrongPass1!",{}]
[PROBE] checkbox roles on RegisterScreen = 0      [PROBE] checkbox roles on LoginScreen = 0
[PROBE] 'common.terms' text present = false       [PROBE] 'common.privacy' text present = false
[PROBE] Register google args = []                 [PROBE] Login google args = []
[PROBE] Pressable: role=checkbox found, checked filter works, press toggles
[PROBE] TouchableOpacity: role=checkbox found, checked filter works, press toggles
```

Typing probe on the installed `tsc 5.9.3` — **exactly two errors, both negative controls**, so `ok1` (`getParent()?.navigate('Legal',{doc})`), `ok2` (`as any`) and `ok3` (typed parent) all compile:

```
w316_getParent_typing.probe.tsx(32,23): error TS2345: … Type '"Legal"' is not assignable to type '"ForgotPassword"'.
w316_getParent_typing.probe.tsx(34,117): error TS2322: Type '"cookies"' is not assignable to type '"privacy" | "terms"'.
```

**Baselines reproduce exactly.**

* Client, the §7 17-suite core subset (with `__tests__/authService.m18.test.ts` per ruling 5): **`Test Suites: 17 passed, 17 total` / `Tests: 8 todo, 190 passed, 198 total`** — identical to §10.7.
* Backend, the 7 closest files: **`2 failed, 201 passed`**, and both failures are `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully`, which are `tests/.pre_impl_failures.txt:79` and `:80`. Identical to §10.7.
* `python -m ruff check --select E9,F63,F7,F82 app/ tests/` on **ruff 0.16.5** → `All checks passed!` (one unrelated warning about an invalid `# noqa` in `tests/test_rate_limiting_complete.py:69`).
* `node node_modules/typescript/bin/tsc -v` → **`Version 5.9.3`**.

**Design claims verified against the source, not docs.**

* **The `getParent()` design is sound at runtime.** `App.tsx:386-388` registers `<Stack.Screen name="Auth">` whose element is `<AuthNavigator …>`, and `App.tsx:91` declares `const AuthStack = createNativeStackNavigator<AuthStackParamList>()`. Register and Login are therefore genuinely **one level nested**, so `getParent()` returns the root navigator that will own the hoisted `Legal`. Had they been direct root children, `getParent()` would be `undefined` and the `?.` would have made both spans silent no-ops on device — the spec's design survives that check. `LoginScreen.tsx:58` types navigation as `NativeStackNavigationProp<AuthStackParamList,'Login'>`, which is the same type the probe exercised via `NativeStackScreenProps<…>['navigation']`.
* **The hoisted `Legal` works unauthenticated.** `app/api/legal_routes.py:5` is `APIRouter(prefix="/api/v1/legal", tags=["legal"])` with **no dependency**, and neither route declares one — `GET /privacy_policy` and `/terms_of_service` are open. `LegalScreen.tsx:49` calls `api.get(endpoint)` with an AsyncStorage fallback. No auth hazard.
* **The position pin §5-A.11 is sufficient.** `App.tsx:489-490` closes the authenticated branch (`</>` then `)}`) before the `:492-502` comment; `name="ReferralLanding"` is `:504`, `name="InviteeQuiz"` `:507`, `</Stack.Navigator>` `:508` (the only occurrence). Anything indexed after InviteeQuiz is unambiguously at navigator level. Today `name="Legal"` is `:416`, inside the `:404` branch → red, for the right reason.
* **`__tests__/App.distinctRouteNames.test.ts` really does make the uniqueness half a duplicate.** `:31` regex `/<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g`, `:41` `it('every Stack.Screen registers a distinct name')`, asserts `duplicates` = `[]`. Green in the 17-suite run. The §2 drop is correct.
* **`__tests__/Screens.bundleD.contract.test.ts` DOES pin Register and Login** (`describe` blocks at `:199` and `:230`) — §4.2's Preserve entry understates it, but all four relevant pins survive the planned change: `/login\(\s*email\.trim\(\)\.toLowerCase\(\)\s*,\s*password\s*\)/` (`:210`, `handleLogin` untouched), `/register\(\s*email\.trim\(\)\.toLowerCase\(\)\s*,\s*password/` (`:241`, the change only extends the third argument), the two import regexes (`:203`, `:234`, unchanged), and `isAppleSignInAvailable` (`:221`, `:250`).
* **The `✓` glyph passes eslint.** `eslint.config.js:20-28` `wordsExclude` contains `/^[\p{P}\p{S}\p{Z}]+$/u`; U+2713 is `\p{So}` ⊂ `\p{S}`. The `i18next/no-literal-string` block at `:47-58` applies `mode: 'jsx-text-only'` to `src/screens/**` and `src/components/**` — so `ConsentRow.tsx` is in scope and every other JSX text in it must go through `t()`.
* **The i18n fence reaches `src/components/`.** `__tests__/i18n/no-missing-referenced-keys.test.ts:27` `SRC_DIR = path.resolve(__dirname,'../../src')`, `:33-45` walks it recursively, `:64` asserts every literal `t()` key exists **in `en.json`**. `ar.json` parity is enforced separately by `i18n.test.ts` and `i18n/no-deleted-keys.test.ts`, exactly as §4.2 states. The three new keys must be FLAT: `en.json:914` `"common.privacy"`, `:915` `"common.terms"`; `ar.json:911`, `:912`. `grep -n 'auth.consent' src/i18n/*.json` → nothing today.
* **The RN mock supports the whole client design.** `__mocks__/react-native.ts:18-19` `TouchableOpacity`, `:68-69` `Pressable` (both spread props onto a host `View` with `accessible: true`), `:70` `export const Platform = { OS: 'ios', select: (obj) => obj.ios }`. Both screens gate Apple on `Platform.OS === 'ios'` inside a `useEffect` (`RegisterScreen.tsx:70-74`, `LoginScreen.tsx:204-208`), so the Apple legs are testable on both screens with no skip — §2's third drop is correct.
* **Migration 038 will be scanned and will pass.** `tests/test_migration_037_security_definer_grants.py:294-296` globs `MIGRATIONS_DIR.glob("*.sql")` (forward) and `:298-300` adds `ROLLBACK_DIR`; `tests/test_migration_index_predicate_immutability.py:80-81` globs forward files and `:93` parametrizes over them. Neither can object to a nullable `ADD COLUMN IF NOT EXISTS` (no `SECURITY DEFINER` grant, no `CREATE INDEX … WHERE`). 16 test files read `migrations/`. `ls migrations/` tops out at `037_security_definer_grants_and_rls.sql`; `migrations/rollback/` at `037_…`. **038 is correct**, and the `033_product_prices_title.sql:1-12` header style the spec copies is real.
* **The finding-doc anchors are all live at `b63a8368`**: `full-review.md:144` (the W3-16 row, quoted verbatim in §1), `:192` critic gap (c) "**consent capture** (ToS clickwrap, the 13+ age gate CLAUDE.md names as code-side blockers) was never checked"; `-tables.md:211` MB-FLOWS-STATE-08, `:209` MB-FLOWS-STATE-03 (correctly NOT absorbed); `tos-fact-base.md:774` the 13+-statement sentence; `CLAUDE.md:15` ship-blocker #2, `:420` the `ENABLE_STRICT_OPTIONAL_AUTH` row whose format the two new rows copy, `:466` "ToS clickwrap + 13+ gate", `:468` the locked age policy, `:714` the mobile-comm-set rule.
* `tests/test_b2_strict_optional_auth.py` autouse `_clean_strict_flag` is at `:56-60` (decorator `:56`); `tests/test_social_login_smoke.py:131` `test_signin_invalid_token_shape_returns_401` is the existing pin for the 401 half of §5-B.10; `tests/test_auth_interceptor.py:444-452` is the `MagicMock` admin harness B.5/B.6 reuse, and `mock_admin.table.return_value = mock_admin_table` with `mock_admin_table.insert.return_value.execute.return_value` makes `insert.call_args.args[0]` reach the dict, so B.5/B.6's exact-key-set assertions are executable. `register_user` inserts `"email": email` (the **argument**), so B.6's expected `{'id':'new-id','email':'new@test.com','subscription_tier':'free'}` is right.

### Ruling 15 — scope is clean; nothing extra, nothing wrongly dropped.

The plan's one compound red test ("register/social sign-in cannot complete without an explicit acceptance and the accepted version is persisted") is **red in both halves** and nothing was dropped from it — re-verified by both probes above. The three things §2 drops are each genuinely already-green or genuinely duplicated (uniqueness → `App.distinctRouteNames`; the Apple `Platform` hedge → mock `:70`; the `getParent` typing hedge → the tsc probe). The Legal-route hoist is the absorbed half of `MB-FLOWS-STATE-08` the brief named; `MB-FLOWS-STATE-03` (Paywall links) is correctly out. `grep -rniE "terms_accepted|termsAccepted|acceptedTerms|terms_version|age_gate|attest"` over `SmartCompareApp/src`, `app/`, `App.tsx`, `migrations/`, `docs/CONTEXT_DATABASE_API.md` still returns **0 source hits** at `b63a8368` (only `anon_usage_gate_enabled` lines and three `__pycache__` binaries). Both flags default OFF and are read per call, both flag-OFF paths are byte-identity pinned (B.4/B.6/B.8), and a phone on `97b5f15` is unaffected on merge — the OTA-before-`REQUIRED` ordering in §8 is right and is the only ordering that is safe.

### ready_for_red

**Yes**, with rulings 1-13 applied. A red-phase agent executing this file needs to ask nothing: the base is `b63a8368`, the anchors hold, the probe commands are complete, the two module-scope traps (ruling 6) and the toggle trap (ruling 7) are disarmed, and the one genuinely open item — the gate SHAPE — is Ahmed's, is flagged as such in §4.1 with alternatives, and does not block writing a single red test, because every red test asserts the PAYLOAD and the GATING, not the number of checkboxes.

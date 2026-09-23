# W3-6 — password reset that can actually be completed

## 1. Header

| field | value |
|---|---|
| unit | **W3-6 password reset flow** |
| finding | `MB-FLOWS-STATE-02` (tables row 51: "Password reset is unrecoverable: the app has no recovery deep link or set-new-password screen anywhere"; review §0 item 6: "Password reset cannot be completed by any email/password user (no recovery route, no `redirect_to`)"; verified.json unit U13) |
| base | `origin/main` = `ed75dc708b82c0b911c9de8a3e59d4418c6e278c` (worktree `sc-w3-pwreset`, HEAD == origin/main, `git status` empty) |
| OTA class | **mixed** — CLIENT half **OTA-safe** (JS-only: a route, a screen, a service function, i18n keys, one jest.config.js token; `app.json` untouched — the `qaren` scheme is already declared at `app.json:15` and the Android intent filter `"data": [{ "scheme": "qaren" }]` at `:67` carries no host/path restriction, so `qaren://reset-password` is already an app-owned URL on both platforms). BACKEND half = one **flagged** behaviour change (`ENABLE_PASSWORD_RESET_DEEP_LINK`, default OFF, read per call) + one **additive** unauthenticated route. The universal-link variant (`https://qaren.app/reset-password`) is **needs-build + Ahmed** (Android `intentFilters` `pathPrefix` list at `app.json:59-61` is native; iOS `applinks:qaren.app` needs an AASA on a host that answers 522 today) and is explicitly OUT of this unit. |
| flag | `ENABLE_PASSWORD_RESET_DEEP_LINK` (default OFF; OFF = byte-identical SDK call) + knob `PASSWORD_RESET_REDIRECT_URL` (default `qaren://reset-password`, read per call) |
| toolchain measured | `node node_modules/typescript/bin/tsc -v` → **Version 5.9.3** (package.json `~5.9.2`); jest 29.7.0 (`^29.7.0`); ts-jest 29.4.9 (`^29.4.6`); `@react-navigation/native` **7.2.4** (`^7.1.28`), `@react-navigation/core` **7.17.4**; expo 54.0.34; RN 0.81.5. `expo-linking` is **NOT installed** and not a dependency — the client's deep links ride React Native's `Linking` through `NavigationContainer` (`useLinking.native.tsx:27-39`), nothing to add. Backend: installed `supabase`/`supabase_auth` **2.28.0** vs lock `supabase==2.31.0` / `supabase-auth==2.31.0` (`requirements.txt:156/158`) — every SDK claim below is from the INSTALLED 2.28.0 source; the tests are written version-agnostic so CI settles them on 2.31.0. ruff 0.16.5. |

## 2. Scope correction — what is ALREADY on main

The plan lists two red tests. **Both are RED at `ed75dc70` — nothing to drop.** Measured (§10 M4, M6):

* `getStateFromPath('reset-password#access_token=x&type=recovery', <real config>)` → `undefined` (probe P2).
* `request_password_reset("user@test.com")` → `reset_password_email` called with `('user@test.com')` and nothing else; on the wire `POST /recover redirect_to=None` (probe A/B).

**Both plan line anchors have moved:**

* Plan/tables cite `App.tsx:283` — at `ed75dc70` line 283 is a blank line inside the boot effect. The linking config is `App.tsx:350-379`: `const linking` `:350`, `prefixes` `:351`, `config.screens` `:353-364` (`ReferralLanding: 'c/:share_token'` `:354`, `InviteeQuiz: 'q/:share_token'` `:355`, `Auth.screens.Register.path: 'r/:code'` `:359`), the `getStateFromPath` override `:366-378`, `<NavigationContainer linking={linking}>` `:382`. Zero hits for `reset-password` / `ResetPassword` / `recovery` anywhere in `App.tsx`.
* Plan cites `app/services/auth_service.py:539` — blank line at `ed75dc70`. `request_password_reset` is `auth_service.py:752-761`; the bare call is `:756`.

**Already on main and therefore NOT built here (verified):**

* The REQUEST side exists end to end: `ForgotPasswordScreen.tsx` (registered at `App.tsx:103`), `authService.requestPasswordReset` (`:624-636`, `POST /api/v1/auth/password-reset` `:626`), route `auth_routes.py:725-735` (`@limiter.limit("3/minute")` `:726`, anti-enumeration constant response), service `auth_service.py:752-761`. This unit changes ONE line of that chain (the SDK call at `:756`) and only under the flag.
* The `qaren` URL scheme and its Android intent filter (`app.json:15`, `:67`). No native change is needed for the custom-scheme link.
* The password-strength rule is one function, `auth_routes._validate_password_strength` (`:66-76`), already reused by `RegisterRequest` (`:89-92`) and `ChangePasswordRequest` (`:140-143`); the client mirrors it at `RegisterScreen.tsx:192`. Both are reused, not re-implemented.
* verified.json's suggestion to "change ForgotPasswordScreen's success copy in the same OTA" is **dropped**: the copy (`auth.resetMessage`, en.json:853: "If an account exists for {{email}}, you'll receive a reset link shortly.") is neutral and becomes true the moment the flag + allow-list land; a copy change would be a second surface for no gain. `Screens.bundleD.contract.test.ts:257-274` pins that screen's shape and stays green because the file is untouched.

## 3. The defect — measured

### 3a. The client has no route for the recovery link

`App.tsx:350-378` @ `ed75dc70`:

```ts
  const linking: LinkingOptions<RootStackParamList> = {
    prefixes: ['qaren://', 'https://qaren.app'],
    config: {
      screens: {
        ReferralLanding: 'c/:share_token',
        InviteeQuiz: 'q/:share_token',
        Auth: {
          screens: {
            Register: {
              path: 'r/:code',
              parse: { code: (c: string) => c.toUpperCase() },
            },
          },
        },
      },
    },
    getStateFromPath: (path: string, options: any) => {
      // Rewrite `redeem?code=QR-XXXXXX` → `r/QR-XXXXXX` so the existing
      // pattern handles both URL shapes from social-share copy.
      const redeemMatch = path.match(/^\/?redeem\??(.*)$/);
      if (redeemMatch) {
        const params = new URLSearchParams(redeemMatch[1]);
        const code = params.get('code');
        if (code) {
          return getStateFromPath(`r/${code.toUpperCase()}`, options);
        }
      }
      return getStateFromPath(path, options);
    },
  };
```

`AuthNavigator` (`App.tsx:94-105`) registers `Login`, `Register`, `ForgotPassword` only; `AuthStackParamList` (`types.ts:624-633`) likewise. There is no screen anywhere that takes a new password from an unauthenticated user: `PUT /auth/password` (`auth_routes.py:819-847`) requires `Depends(get_current_user)` AND the current password.

**Probe P2 (§10 M4):** `getStateFromPath('reset-password#access_token=x&type=recovery', CONFIG_TODAY)` → `undefined`. The link the backend would emit lands nowhere; `useLinking.native.tsx:157/163` passes it to `onUnhandledLinking` and the app simply opens.

### 3b. The token arrives in the URL FRAGMENT, and the installed router ignores fragments

Measured on the installed `@react-navigation/core` 7.17.4 / `native` 7.2.4:

* `native/src/extractPathFromURL.tsx:20-31` splits the URL on `?` only and strips the prefix; **the `#…` fragment survives in the returned path** — probe P1: `extractPathFromURL(['qaren://','https://qaren.app'], 'qaren://reset-password#access_token=x&refresh_token=y&type=recovery')` → `"reset-password#access_token=x&refresh_token=y&type=recovery"`.
* `core/src/getStateFromPath.tsx:749-750` is the ONLY place the path is split for parameters: `const query = path.split('?')[1]; const params = queryString.parse(query);` — `grep -n "#\|fragment\|hash"` over the file returns **nothing**. The `#…` therefore stays glued to the first segment, so even with `ResetPassword: 'reset-password'` in the config the segment `reset-password#access_token=…` does not match the pattern — probe P3: `undefined`. Putting the tokens in the QUERY instead (probe P4) does match, but then `access_token` lands in `routes[].params` and `routes[].path` of the navigation state, i.e. in anything that serialises navigation state.
* Therefore the fragment MUST be intercepted in the app's own `getStateFromPath` override (`App.tsx:366`, which `useLinking.native.tsx:133` calls for BOTH the cold-start `Linking.getInitialURL()` path (`:146-166`) and the warm `Linking.addEventListener('url')` path (`:172-186`)), the tokens parked in a module-scoped slot, and the path rewritten to the bare `reset-password` — probe P5: bare path → `['Auth','ResetPassword']` with **no `params` key** on the leaf.

### 3c. The backend never tells Supabase where to send the user

`auth_service.py:752-761` @ `ed75dc70`:

```py
async def request_password_reset(email: str) -> Dict:
    """Send password reset email."""
    try:
        client = get_auth_client()
        client.auth.reset_password_email(email)
        return {
            "success": True,
            "message": "Password reset email sent"
        }
    except Exception as e:
        return _categorize_auth_error(e, "password_reset")
```

Installed `supabase_auth/_sync/gotrue_client.py` (2.28.0): `reset_password_email(self, email, options=None)` → `reset_password_for_email(email, options or {})` → `self._request("POST", "recover", body={...}, redirect_to=reset_options.get("redirect_to"))`; `gotrue_base_api.py::_request`: `if redirect_to: query = query.set("redirect_to", redirect_to)`. So with no options the `recover` call carries **no `redirect_to`** and GoTrue sends the user to the project's Site URL after verifying the email link — which is not the app. Probe A/B (§10 M6): today `POST /recover redirect_to=None`; with `{"redirect_to": "qaren://reset-password"}` the same call carries `redirect_to='qaren://reset-password'`.

`reset_password_for_email` sends **no `code_challenge`** (measured: `"code_challenge" in source` → False) even though `SyncClientOptions().flow_type` defaults to `pkce` — so the recovery link is an IMPLICIT-flow link and GoTrue's post-verify redirect carries the session in the **URL fragment** (`#access_token=…&expires_in=…&refresh_token=…&token_type=bearer&type=recovery`). That fragment shape is GoTrue server behaviour I could NOT measure offline (no network) — the client parser below therefore accepts both `#` and `?` forms, requires `type=recovery`, and reads only `access_token`.

## 4. The fix — MINIMAL design

### Client (OTA-safe, unflagged by nature — RN has no per-call env flag; backward-compatible with main's backend: the new route exists only after this unit's backend deploys, and until then the screen's submit gets a 404 → the existing `parseApiError` message; the deep link itself only reaches phones once the flag AND the allow-list are on)

1. **NEW `src/services/passwordRecoveryLink.ts`** (mirrors `src/services/deferredInviteCode.ts` exactly: module-scoped slot, `set`/`consume`/`__reset…ForTests`):
   * `parseRecoveryLink(path: string): { accessToken: string } | null` — pure. Accepts the string `extractPathFromURL` hands to the override: optional leading `/`, first segment exactly `reset-password`, then `#` OR `?` followed by `k=v&…`. Returns non-null ONLY when `type === 'recovery'` AND `access_token` is non-empty. `refresh_token`, `expires_in`, everything else is **discarded** — the backend half needs only the access token, so the client never retains a second credential.
   * `setPendingRecovery(r)`, `consumePendingRecovery(): PendingRecovery | null` (clears on read), `__resetPendingRecoveryForTests()`.
   * **No logging anywhere in this module**, no analytics call, no Sentry breadcrumb. The token lives in process memory only and dies with the process or on first consume.
2. **MOVE the linking object out of `App.tsx` into NEW `src/navigation/linking.ts`** exporting `linking: LinkingOptions<RootStackParamList>` — the same `prefixes`/`config`/override, verbatim, plus:
   * `config.screens.Auth.screens.ResetPassword: 'reset-password'`
   * the override gains a FIRST branch: `const recovery = parseRecoveryLink(path); if (recovery) { setPendingRecovery(recovery); return getStateFromPath('reset-password', options); }` — then the existing `redeem` branch, then the default. Tokens never enter the navigation state (probe P5 shape).
   * `App.tsx:350-379` becomes `import { linking } from './src/navigation/linking'`; `:382` unchanged. Why move: the unit's behaviour test must call the REAL override with the REAL config through the REAL parser, and importing `App.tsx` drags in the whole app (fonts, Sentry, 20 screens) — every existing `App.*.test` deliberately avoids that (`App.referral.test.tsx:4-8`). The module imports only `getStateFromPath` + the `LinkingOptions` type from `@react-navigation/native`, `RootStackParamList`, and the slot module.
3. **`App.tsx`**: `import ResetPasswordScreen from './src/screens/ResetPasswordScreen'`; `AuthNavigator` (`:94-105`) gains `<AuthStack.Screen name="ResetPassword" component={ResetPasswordScreen} />`. (The `App.distinctRouteNames` fence scans `<Stack\.Screen` only — `AuthStack.Screen` is outside its regex, and the name is unique regardless.) Nothing else in `App.tsx` changes.
4. **`src/types/types.ts:624-633`**: `AuthStackParamList` gains `ResetPassword: undefined;`.
5. **NEW `src/screens/ResetPasswordScreen.tsx`** (shape of `ForgotPasswordScreen.tsx`: `usePreventScreenCapture()`, theme tokens, `Button`, all copy via `t()` so the `i18next/no-literal-string` eslint rule passes):
   * on mount: `const [recovery] = useState(() => consumePendingRecovery())` — consumed ONCE, held in component state, never rendered, never logged.
   * `recovery === null` → "link expired" state: `auth.resetLinkExpired` / `auth.resetLinkExpiredMessage` + `Button` → `navigation.navigate('ForgotPassword')`.
   * form: new password + confirm (`auth.newPassword`, `auth.confirmPassword` [exists en.json:266]); client rule identical to `RegisterScreen.tsx:192` (`length < 10 || !/[A-Z]/ || !/[a-z]/ || !/[0-9]/` → `auth.passwordRequirements` [exists :910]); mismatch → `auth.passwordsDoNotMatch`.
   * submit → `completePasswordRecovery(recovery.accessToken, password)`; success → state `auth.passwordUpdated` / `auth.passwordUpdatedMessage` + `Button` `auth.signIn` → `navigation.navigate('Login')` (navigate, not goBack: when the app cold-starts from the link the Auth stack holds ONLY `ResetPassword`); failure → `parseApiError(err).message` in the same error box `ForgotPasswordScreen` uses.
6. **`src/services/authService.ts`**: `export async function completePasswordRecovery(accessToken: string, newPassword: string): Promise<void>` → `api.post('/api/v1/auth/password-recovery', { access_token: accessToken, new_password: newPassword })`, same error unwrapping as `requestPasswordReset` (`:624-636`). The `api` request interceptor (`api.ts:50-57`) attaches a stored Bearer if one exists; the route ignores headers, so that is harmless. The response interceptor's refresh dance fires ONLY on 401 (`api.ts:207-209`) — which is why the backend maps a bad recovery token to **400**, never 401 (a 401 on an unauthenticated device would run `getOrStartRefresh` with no refresh token and could emit `sessionInvalid` for nothing).
7. **i18n** — 8 keys added to BOTH `en.json` and `ar.json` (parity fence `__tests__/i18n.test.ts:8-9`; referenced-key fence `__tests__/i18n/no-missing-referenced-keys.test.ts`): `auth.setNewPassword`, `auth.newPassword`, `auth.passwordsDoNotMatch`, `auth.passwordUpdated`, `auth.passwordUpdatedMessage`, `auth.resetLinkExpired`, `auth.resetLinkExpiredMessage`, `auth.requestNewLink`. Copy must clear `src/i18n/.copy-policy.json` (`scary_vocab_en`: `couldn't`, `try again`, `Failed to`; `scary_vocab_ar`: `تعذر`, `فشل`, `تقدير`, `مُقدَّر`) — e.g. expired: "This reset link is no longer valid. Request a new one below." / "هذا الرابط لم يعد صالحاً. اطلب رابطاً جديداً من الأسفل."
8. **`jest.config.js` `transformIgnorePatterns`** — add `@react-navigation` to the existing allowlist group (`'node_modules/(?!(@expo-google-fonts|…|react-native-reanimated)/)'` → `…|react-native-reanimated|@react-navigation)/)'`). Why: the packages ship ESM-only `lib/module` (measured: `lib/` contains only `module` + `typescript`; `exports` maps `"."` → `./lib/module/index.js` and blocks deep imports), so the only way to run the REAL parser under ts-jest is to `jest.requireActual` the TSX SOURCE by relative path (`../node_modules/@react-navigation/core/src/getStateFromPath`), and ts-jest transforms a `.tsx` under `node_modules` only if the ignore pattern lets it through. Probe §10 M4 ran exactly this override. **Blast radius: inert for the existing 278 suites** — today no suite loads the real `@react-navigation/*` (they would fail on ESM); the three importers (`EditProfileScreen.bundleE.s3.integration`, `HistoryScreen.mobileJank.m21`, `HistoryScreen.searchState.a12`) all `jest.mock('@react-navigation/native', factory)`, and a `.js` under `lib/module` is still not transformed by the ts-jest preset (`^.+\.tsx?$`). The full-suite run in the green phase is the proof.

**What does NOT change (client):** `ForgotPasswordScreen.tsx` (byte-identical), `LoginScreen`, `app.json`, `package.json`/lockfile, `api.ts`, `sentry.ts`, any analytics call. The `redeem` / `r/:code` / `c/` / `q/` resolution is byte-for-byte the same code, moved.

### Backend (deploy; phones on `97b5f15` AND the pending OTA are unaffected: flag OFF = identical SDK call; the new route is unreachable from any shipped client)

9. **`app/services/auth_service.py`**:
   * `password_reset_deep_link_enabled() -> bool` — copy of `logout_upstream_revocation_enabled` (`:418-433`): `os.getenv("ENABLE_PASSWORD_RESET_DEEP_LINK", "false").strip().lower() in ("true","1","yes","on")`, read PER CALL. `password_reset_redirect_url() -> str` — `os.getenv("PASSWORD_RESET_REDIRECT_URL", "qaren://reset-password").strip() or "qaren://reset-password"`, read per call.
   * `request_password_reset` (`:752-761`): flag ON → `client.auth.reset_password_email(email, {"redirect_to": password_reset_redirect_url()})`; flag OFF → **exactly today's** `client.auth.reset_password_email(email)` (one positional, no second argument — `tests/test_auth_interceptor.py:684` pins `assert_called_once_with("user@test.com")`). Docstring states: the `options` dict is the SDK's signature (`reset_password_email(email, options: Optional[Options] = None)` on 2.28.0; `redirect_to` becomes the `?redirect_to=` query param of `POST /auth/v1/recover`); GoTrue honours it ONLY if the value is on the project's Redirect URL allow-list, otherwise it silently falls back to the Site URL — Ahmed's dashboard step, which is why this ships dark.
   * NEW `complete_password_recovery(access_token: str, new_password: str) -> Dict`:
     1. `client = get_auth_client()`; `user_response = client.auth.get_user(access_token)` (`SyncGoTrueClient.get_user(self, jwt=None)` on 2.28.0 — a `GET /user` with the token as Bearer; GoTrue verifies signature + expiry; an invalid/expired token RAISES an `AuthApiError`, a missing user returns `None`). Both → `{"success": False, "code": "RECOVERY_TOKEN_INVALID", "error": "This reset link is no longer valid."}` and NO admin call.
     2. **AMR gate, fail-closed:** decode the token's payload segment WITHOUT verification (base64url of `token.split('.')[1]`, verification already happened upstream in step 1) and require `any(m.get("method") == "recovery" for m in claims.get("amr", []))`; otherwise the same `RECOVERY_TOKEN_INVALID` result. Rationale: `PUT /auth/password` exists precisely so a stolen bearer cannot rotate the password without the current one (`auth_routes.py:819-847`); a recovery endpoint that accepts ANY live session token would be a new "change password without the current password" door. GoTrue stamps `amr: [{"method": "recovery", "timestamp": …}]` on sessions minted from a recovery link — **UNMEASURED offline (open question §8)**; on rejection log ONE line `[auth] password recovery rejected: amr=%s` with the METHOD NAMES only (never the token), so the first canary reset tells us immediately if the claim shape differs.
     3. `admin = get_admin_client(); admin.auth.admin.update_user_by_id(user_response.user.id, {"password": new_password})` — the same admin call `change_user_password` makes at `:629`, so the password-write path is unchanged code.
     4. `_revoke_token(access_token)` (`:514`) — the recovery token is blacklisted for our API for the 1 h TTL the moment it is spent; it can never be replayed against `/auth/me` etc.
     5. return `{"success": True, "message": "Password updated"}`; any other exception → `_categorize_auth_error(e, "password_recovery")`.
     * **Token scrub (W1-4 lesson, `:488-503`):** before any `logger.*` or `str(e)` reaches a log, `detail = str(e).replace(access_token, "<access_token>")`. `UserDoesntExist(access_token)`'s `str()` IS the bearer on this SDK.
     * Why `get_user` + admin update, not `set_session` + `update_user`: it needs only the access token (so the client never sends the refresh token), it reuses the exact admin call the codebase already trusts, and it avoids `set_session`'s measured side effects (JWT decode raise on non-JWT input; `_refresh_access_token` rotation on an expired token — W1-4 block in CLAUDE.md).
10. **`app/api/auth_routes.py`**:
    * `class PasswordRecoveryRequest(BaseModel)`: `access_token: str = Field(..., min_length=20, max_length=4096)`, `new_password: str = Field(..., min_length=10)` + `@field_validator("new_password")` → `_validate_password_strength` (`:66`), exactly like `ChangePasswordRequest` (`:136-143`).
    * `@router.post("/password-recovery")` + `@limiter.limit("5/minute")` (the same tier as `PUT /password`; decorator BELOW the route decorator like every sibling) → `result = await complete_password_recovery(body.access_token, body.new_password)`; `if not result["success"]: raise HTTPException(status_code=400, detail={"code": result.get("code", "RECOVERY_FAILED"), "error": result["error"]})` — the STRUCTURED detail so `error_handler._is_structured_detail` (`:72-90`) lets `code` override `STATUS_CODE_MAP[400] = "BAD_REQUEST"`; success → `{"success": True, "message": "Password updated"}`.
    * Path is `/password-recovery`, NOT `/reset-password`: `tests/test_auth_interceptor.py:1626` asserts `"/api/v1/auth/reset-password" not in routes`.
    * No auth dependency (the token IS the credential), no flag (additive route, nothing shipped calls it, and it is safe by itself: an upstream-verified recovery-AMR JWT is required).
    * `POST /password-reset` (`:725-735`) is byte-unchanged.

**What does NOT change (backend):** `get_auth_client`/`get_admin_client`, `_categorize_auth_error`, `PUT /password`, `logout_user`, any migration (none — `038` is not needed), `requirements*.in/txt`.

**Ahmed dependencies (the code half lands without them):** Supabase dashboard → Authentication → URL Configuration → Redirect URLs: add `qaren://reset-password` (and later `https://qaren.app/reset-password` when that origin is alive); Railway `web`: `ENABLE_PASSWORD_RESET_DEEP_LINK=true` AFTER the OTA carrying this client half is on phones (order in §8).

## 5. Red tests

All node names are final; every RED reason below was measured on `ed75dc70` (§10). A test that is red ONLY because a new module does not exist yet is marked `(new-module red)` and is paired with a mutation that must redden it AFTER the fix so it is not decoration.

### Client — `SmartCompareApp/__tests__/`

**`linking.resetPassword.w36.test.ts`** — mocks `@react-navigation/native` with a factory whose `getStateFromPath` is `jest.requireActual('../node_modules/@react-navigation/core/src/getStateFromPath').getStateFromPath` (needs the jest.config.js allowlist token, §4.8), imports `{ linking } from '../src/navigation/linking'` and `{ consumePendingRecovery, __resetPendingRecoveryForTests } from '../src/services/passwordRecoveryLink'`. Helper `focused(state)` walks `routes[index].state` (as in the probe).
1. `App.tsx source contains 'reset-password' inside the linking config OR imports './src/navigation/linking'` — source-scan node so the file is RED for the right reason on TODAY's tree, not only by import failure. **RED: 0 hits** (`grep -n reset-password App.tsx` → nothing). Mutation after fix: delete the `ResetPassword: 'reset-password'` entry → node 2 reddens (this node stays green — it is the today-red anchor only).
2. `linking.getStateFromPath('reset-password#access_token=tok-SECRET-1&refresh_token=r&type=recovery', linking.config)` → `focused(state)` equals `['Auth','ResetPassword']`. **RED: `undefined` today (probe P2; and `src/navigation/linking` does not exist).** Mutation: remove the recovery branch from the override → `undefined` (probe P3) → red.
3. same call: `JSON.stringify(state)` does NOT contain `tok-SECRET-1`, the leaf route has no `params`, and `consumePendingRecovery()` returns `{ accessToken: 'tok-SECRET-1' }` with no `refreshToken` key. Mutation: rewrite the override to forward the fragment as a query (`reset-password?…`) → params carry the token (probe P4) → red. Second mutation: keep `refresh_token` in the slot → red.
4. `consumePendingRecovery()` a second time → `null` (consume clears). Mutation: make `consume` non-clearing → red.
5. `'reset-password#access_token=x&type=signup'` and `'reset-password#type=recovery'` (no token) → `getStateFromPath` returns `undefined`… **correction:** with the route registered, a bare/unparseable `reset-password…#…` path falls to the default parser → P3 shows `undefined` for a fragment-bearing path; assert `state === undefined` AND `consumePendingRecovery() === null`. Mutation: drop the `type === 'recovery'` check → slot filled on `type=signup` → red.
6. Preserve pins (green after the move, NEW as tests — today they cannot be written because the config is inline in `App.tsx`): `redeem?code=qr-abc123` → `['Auth','Register']` with `params.code === 'QR-ABC123'`; `r/qr-abc123` → Register with `code === 'QR-ABC123'`; `c/tok` → `['ReferralLanding']` with `share_token === 'tok'`; `q/tok` → `['InviteeQuiz']`. Mutation: delete the `redeem` branch → red; change the `parse` upper-casing → red.
7. `linking.prefixes` deep-equals `['qaren://', 'https://qaren.app']` (the move must not drop the universal-link prefix).

**`passwordRecoveryLink.w36.test.ts`** `(new-module red)`: `parseRecoveryLink` → fragment form; query form (`reset-password?access_token=x&type=recovery`); leading slash (`/reset-password#…`); `type` missing → null; `access_token` empty → null; a different first segment (`reset-passwordx#…`, `r/reset-password#…`) → null; the returned object has exactly one key `accessToken`; set/consume/consume → value then null; `__reset…` clears. Mutation for each: loosen the segment regex / drop the type check / return `refreshToken` → the matching node reddens. Also: the module source contains no `console.` and no `Sentry` / `trackEvent` identifier (source-scan; mutation: add a `console.log` → red).

**`ResetPasswordScreen.w36.test.tsx`** `(new-module red)` — `jest.mock('../src/services/authService', () => ({ completePasswordRecovery: jest.fn() }))`, `jest.mock('expo-screen-capture', …)` as `AuthScreens.test.tsx:11-30` does, slot pre-set via `setPendingRecovery({accessToken:'tok'})`:
1. valid `NewPassw0rd!x` twice + submit → `completePasswordRecovery` called ONCE with `('tok', 'NewPassw0rd!x')`; then the success title (`auth.passwordUpdated`) renders and its button navigates to `'Login'`. Mutation: call with the confirm field / drop the navigate → red.
2. mismatched confirm → 0 calls, `auth.passwordsDoNotMatch` rendered. 3. `short1` → 0 calls, `auth.passwordRequirements` rendered.
4. slot EMPTY → the expired state renders (`auth.resetLinkExpired`) and its button navigates to `'ForgotPassword'`; no form. Mutation: render the form when the slot is empty → red.
5. rejected promise (`{response:{data:{error:'This reset link is no longer valid.', code:'RECOVERY_TOKEN_INVALID'}}}`) → that message renders, no success state.
6. `render` output (the test renderer JSON) never contains the string `tok`. Mutation: render the token in a debug `<Text>` → red.

**`authService.passwordRecovery.w36.test.ts`** `(new-module red)` — mock `../src/services/api` as `authService.logoutRevoke.w1-4.test.ts` does: `completePasswordRecovery('tok','NewPassw0rd!x')` posts to `'/api/v1/auth/password-recovery'` with body deep-equal to `{ access_token: 'tok', new_password: 'NewPassw0rd!x' }` (no other keys — mutation: add `refresh_token` → red); `{success:false, error:'x'}` body → rejects with `'x'`.

**`App.resetPasswordRoute.w36.test.ts`** — source-scan of `App.tsx`: `/<AuthStack\.Screen\s+name=["']ResetPassword["']/` **RED: 0 hits**; `AuthStackParamList` key check `const k: keyof AuthStackParamList = 'ResetPassword'` **RED at tsc** (mirrors `App.routing.test.tsx:9-14`).

### Backend — `tests/test_password_reset_deep_link.py` (single file; `-p no:randomly`; every env read goes through `monkeypatch.setenv` / `monkeypatch.delenv(..., raising=False)`)

1. `FLAG=true` (`monkeypatch.setenv("ENABLE_PASSWORD_RESET_DEEP_LINK","true")`, knob unset): `await request_password_reset("u@t.com")` with `get_auth_client` patched to a `MagicMock` → `mock.auth.reset_password_email.assert_called_once_with("u@t.com", {"redirect_to": "qaren://reset-password"})`. **RED: called with `("u@t.com")` (probe A).** Mutation: hard-code no options → red.
2. `FLAG=true` + `PASSWORD_RESET_REDIRECT_URL=https://qaren.app/reset-password` → that exact string forwarded. **RED.** Mutation: ignore the knob → red.
3. `FLAG` deleted from env → `assert_called_once_with("u@t.com")` — **GREEN today; the flag-OFF byte-identity pin** (duplicates `test_auth_interceptor.py:684` under an explicit env pop). Mutation: always pass options → red. Also `FLAG=false`/`0`/garbage → same.
4. Wire pin, version-agnostic: patch `supabase_auth._sync.gotrue_client.SyncGoTrueClient._request` with a recorder; build `SyncGoTrueClient(url="https://example.invalid/auth/v1", headers={})`; call `reset_password_email("u@t.com", {"redirect_to": "qaren://reset-password"})` → recorded `(method, path, redirect_to)` == `("POST", "recover", "qaren://reset-password")`. **GREEN today (probe B) — it is the "the kwarg name matches the INSTALLED SDK" pin**; it runs on whatever version is present (2.28.0 here, 2.31.0 in CI). Mutation in OUR code cannot redden it — it is a library-contract pin, kept deliberately and labelled so.
5. Route existence: `TestClient(app).post("/api/v1/auth/password-recovery", json={"access_token": "x"*32, "new_password": "NewPassw0rd!x"})` with `app.api.auth_routes.complete_password_recovery` patched `AsyncMock(return_value={"success": True, "message": "Password updated"})` → 200, `body["success"] is True`. **RED: 404.**
6. Failure mapping: patched to return `{"success": False, "code": "RECOVERY_TOKEN_INVALID", "error": "This reset link is no longer valid."}` → **400** and TOP-LEVEL `body["code"] == "RECOVERY_TOKEN_INVALID"` (envelope trap: never `body["detail"]["code"]`). **RED: 404.** Mutation: raise 401 → red; raise bare `HTTPException(400, msg)` → `code == "BAD_REQUEST"` → red.
7. Validation: `new_password="short1"` → **422** (`_validate_password_strength`); missing `access_token` → 422. RED: 404. Mutation: drop the validator → 200 → red.
8. `/api/v1/auth/reset-password` NOT in `router.routes` and `/api/v1/auth/password-recovery` IS. (First half is the existing `test_auth_interceptor.py:1626` pin, restated; second half RED.)
9. Limiter: decorator-aware source scan — within the 3 lines above `async def password_recovery(` there is `@limiter.limit("5/minute")`. **RED: no such def.** Mutation: remove the decorator → red.
10. Service happy path: `get_auth_client` → mock whose `auth.get_user("tok.jwt")` returns an object with `.user.id == "u1"`; `get_admin_client` → mock; token payload segment carries `{"amr":[{"method":"recovery"}]}` (build a real 3-segment `a.b.c` string with base64url JSON in `b`); `_revoke_token` patched. `await complete_password_recovery(tok, "NewPassw0rd!x")` → `{"success": True, …}`, `admin.auth.admin.update_user_by_id.assert_called_once_with("u1", {"password": "NewPassw0rd!x"})`, `_revoke_token.assert_called_once_with(tok)`, and `get_user` was called BEFORE `update_user_by_id` (order via a shared `Mock()` manager `mock_calls`). **RED: function missing.** Mutations: skip `_revoke_token` → red; call admin before get_user → red.
11. `get_user` raises `Exception("invalid JWT")` → `{"success": False, "code": "RECOVERY_TOKEN_INVALID"}`, admin never called, `_revoke_token` never called. Mutation: fall through to `_categorize_auth_error` (no `code`) → red.
12. `get_user` returns `None` → same as 11.
13. AMR gate: valid `get_user`, payload `{"amr":[{"method":"password"}]}` → `RECOVERY_TOKEN_INVALID`, admin never called; payload with no `amr` → same; caplog contains `amr=` with `password` and does NOT contain the token string. Mutation: drop the gate → admin called → red.
14. Token scrub: `get_user.side_effect = Exception(tok)` (the `UserDoesntExist(access_token)` shape) → `tok` appears NOWHERE in `caplog.text`. Mutation: log `str(e)` raw → red.
15. Both predicates read PER CALL: set env → True, delete env → False, in one test without reload (the W0-3 lesson: never `importlib.reload` the real module).

## 6. Preserve

| behaviour | proof |
|---|---|
| flag OFF: `reset_password_email(email)` called with ONE positional, nothing else | existing `tests/test_auth_interceptor.py::test_request_password_reset_success` (`:674-684`) + backend node 3 |
| `POST /password-reset` still 3/minute, still the constant anti-enumeration body | existing `tests/test_429_contract.py` (route `:55`, 3/min), `test_auth_interceptor.py::test_password_reset_always_succeeds` / `_succeeds_even_on_error` (`:385-403`), `test_security_regression.py::test_password_reset_no_email_enumeration` |
| `/api/v1/auth/reset-password` absent | existing `test_auth_interceptor.py::test_password_reset_endpoint_path` (`:1619-1626`) + backend node 8 |
| existing limiter pins (`5/minute`, `3/minute`, `1/minute` present in source) | `test_security_regression.py:419-433` (additive — a new `5/minute` cannot break a substring pin) |
| `PUT /password` still requires the current password | untouched; `test_security_regression` password tests |
| `logout_user` / W1-4 paths | untouched; `tests/test_auth_refresh_and_revocation.py` in the comm set |
| `redeem?code=` rewrite, `r/:code` upper-casing, `c/`, `q/` resolution, both prefixes | client nodes 6-7 (new pins; the code is moved verbatim) |
| `ForgotPasswordScreen` shape | `__tests__/Screens.bundleD.contract.test.ts:257-274` (file untouched) |
| `App.tsx` Stack.Screen names distinct | `__tests__/App.distinctRouteNames.test.ts` |
| en/ar key parity (915 == 915 key-lines measured today), every referenced key present, copy policy | `__tests__/i18n.test.ts:8-9`, `__tests__/i18n/no-missing-referenced-keys.test.ts`, `__tests__/copy-policy.test.ts` |
| existing 278 suites unaffected by the jest.config.js allowlist token | full-suite run in the green phase (mandatory here because jest.config.js changes) |
| backend tests that scan `SmartCompareApp/` (`test_events_allowlist_superset` etc.) | included in the comm set (§7) — the new screen fires NO `trackEvent` |

## 7. Gates

**Client (from `SmartCompareApp`, tools by path):**
1. Unit files: `node node_modules/jest/bin/jest.js --ci __tests__/linking.resetPassword.w36.test.ts __tests__/passwordRecoveryLink.w36.test.ts __tests__/ResetPasswordScreen.w36.test.tsx __tests__/authService.passwordRecovery.w36.test.ts __tests__/App.resetPasswordRoute.w36.test.ts` — red-first, then green; then the mutation list of §5 (delete the fix, confirm red, restore).
2. Neighbour set — every suite that references a touched module: `grep -rlE "\.\./App'|\.\./App\"|App\.tsx|src/types|services/authService|ForgotPasswordScreen|i18n/(en|ar)\.json|LoginScreen" __tests__` = **98 files at `ed75dc70`** (listed in §10 M11), plus `__tests__/i18n/**`, `__tests__/copy-policy.test.ts`, `__tests__/App.distinctRouteNames.test.ts`, `__tests__/Screens.bundleD.contract.test.ts`, `__tests__/types.contract.test.ts` (already inside the 98). Base vs head, `comm -13` of the sorted FAILED node ids must be empty. Because `jest.config.js` changes, the green phase's one FULL run (278 suites / 2,729 passed baseline) is the authoritative gate for this unit, not the neighbour set.
3. `node node_modules/typescript/bin/tsc --noEmit` (print `-v` = 5.9.3) — exit 0.
4. `node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}" __tests__/*w36*` — 0 errors (CI's exact glob is `npx eslint "src/**/*.{ts,tsx}"`, `ci.yml:270`); the new screen must not add a `i18next/no-literal-string` error.

**Backend (worktree root; `.env` present; never `LIVE=1`):**
5. `PYTHONIOENCODING=utf-8 python -m pytest tests/test_password_reset_deep_link.py -q -p no:randomly -p no:cacheprovider` red-first, then green, then mutations.
6. `python -m ruff check --select E9,F63,F7,F82 app/services/auth_service.py app/api/auth_routes.py tests/test_password_reset_deep_link.py`; `python -m py_compile` both.
7. Comm gate = UNION of (a) `grep -rlE "auth_service|auth_routes" tests/` → **44 paths at `ed75dc70`** (42 `test_*.py`; the other two are `tests/.pre_impl_failures.txt` and `tests/_env_safety.py`/`tests/integration/bundle-e-smoke.sh` — not collectable, listed in §10 M10), (b) the mobile-scanning set `grep -rl "SmartCompareApp" tests/` → **9 files** (§10 M10), (c) the unit file. Run at BASE (`git worktree add --detach <tmp> ed75dc70` + copy `.env`) and HEAD with `-m "not (live_unit or live_db or integration)" -p no:randomly --timeout=60`, `comm -13` the sorted FAILED sets → `branch-only-NEW == []`. Expected identical on both sides: `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully` (rows 1-2 of `tests/.pre_impl_failures.txt`). `tests/test_rate_limiting_complete.py` is not in the set (network GET).
8. Fable review before commit; agents never commit.

## 8. What this unit CANNOT do / Ahmed dependencies / device-or-store only

* **Supabase Redirect URL allow-list** (Ahmed, dashboard: Authentication → URL Configuration → Redirect URLs → add `qaren://reset-password`). Without it GoTrue ignores `redirect_to` and falls back to the Site URL — documented GoTrue behaviour, NOT measured here (no network). The code half lands and stays inert under the flag until this exists.
* **Activation ORDER (Ahmed):** (1) `eas update --branch preview --clear-cache` carrying this client half; (2) allow-list entry; (3) `ENABLE_PASSWORD_RESET_DEEP_LINK=true` on `web` only. Flipping (3) before (1) sends every reset email to a link that phones on `97b5f15` cannot route (they open on Login with the tokens in an unhandled URL) — no worse than today's Site-URL dead end, but pointless.
* **Universal link `https://qaren.app/reset-password`**: needs the Android `pathPrefix` entry (`app.json:59-61`, native → `eas build`), an AASA file at a `qaren.app` that answers (522 today, `MB-FLOWS-STATE-01`), and a second allow-list row. Out of scope; `PASSWORD_RESET_REDIRECT_URL` is the knob that will switch it later without a code change.
* **GoTrue's post-verify redirect shape** (`#access_token=…&refresh_token=…&type=recovery` for a non-PKCE recover) and the **`amr: [{"method":"recovery"}]` claim** are documented behaviour I could not observe offline. The parser accepts `#` and `?`; the AMR gate fails CLOSED and logs the method names — **the first canary reset is the measurement.** If `amr` turns out not to carry `recovery`, the gate must be re-specified (not silently removed): options are checking `aal`/`session_id` freshness or moving to `set_session` + `update_user` under the recovery session.
* **Device-only verification:** email client → GoTrue `/auth/v1/verify` 302 → `qaren://…` hand-off on iOS Mail/Gmail and Android Gmail/Chrome; the cold-start path (`Linking.getInitialURL`) vs the warm path (`addEventListener('url')`); a link tapped while the app sits on the SPLASH (NavigationContainer not yet mounted, so the `url` event has no subscriber — `useLinking.native.tsx:172`) is expected to be dropped on warm start — verify and, if it bites, that is a follow-up (an `Linking.getInitialURL` re-read after splash), not this unit; Arabic rendering of the new screen (RTL: `textAlign` sites are module-scope `StyleSheet.create`, unreachable by jest — the standing rule).
* **A user who is SIGNED IN on the device and taps a recovery link** lands nowhere (`Auth` is not mounted in the authenticated branch; `Auth`→`ResetPassword` is unregistered there) and the slot holds the token until process death or the next unauthenticated link. Accepted: a signed-in user changes the password from Edit Profile; recorded, not fixed.
* **Local/lock drift:** `supabase`/`supabase_auth` 2.28.0 installed vs 2.31.0 pinned — every SDK number above is from 2.28.0; node 4 re-measures the wire contract on CI's 2.31.0. `sign_out` line anchors in the neighbouring W1-4 docstring already record the same drift.
* The client cannot reach the endpoint until the backend deploys (a 404 shows the generic `parseApiError` message); the endpoint cannot be reached by any shipped client until the OTA. Neither half breaks the other.

## 9. PR-body facts

* Finding `MB-FLOWS-STATE-02`; base `ed75dc70`; plan anchors `App.tsx:283` and `auth_service.py:539` were blank lines at base — the linking config is `App.tsx:350-379`, the SDK call `auth_service.py:756`.
* Measured on `@react-navigation/core` 7.17.4 / `native` 7.2.4: `extractPathFromURL` keeps the `#…` fragment (probe P1), `getStateFromPath.tsx:749` splits on `?` only and contains no fragment handling, so `reset-password#access_token=…` matches NO pattern even with the route registered (P2/P3); a query-form link WOULD match but writes the token into `routes[].params` (P4). The fix intercepts in the app's own `getStateFromPath` override, parks `{accessToken}` in a memory-only slot (`src/services/passwordRecoveryLink.ts`, zero logging), and rewrites to the bare `reset-password` → `Auth > ResetPassword` with no params (P5). `refresh_token` is never retained.
* Backend: `request_password_reset` now passes `{"redirect_to": PASSWORD_RESET_REDIRECT_URL}` (default `qaren://reset-password`) ONLY under `ENABLE_PASSWORD_RESET_DEEP_LINK` (default OFF, read per call); OFF is the one-positional call pinned by `test_auth_interceptor.py:684`. On the installed supabase-auth 2.28.0 the option becomes the `?redirect_to=` query of `POST /auth/v1/recover` (probe B); `reset_password_for_email` sends no PKCE challenge, so the link is implicit-flow (fragment). GoTrue honours `redirect_to` only when it is on the project allow-list — Ahmed.
* NEW `POST /api/v1/auth/password-recovery` (`5/minute`, no auth dependency, additive, unflagged): `get_user(access_token)` upstream verification → fail-closed `amr` contains `recovery` → the same `admin.update_user_by_id(uid, {"password"})` call `change_user_password` makes → the token is blacklisted locally for 1 h. Bad token → **400** `code: RECOVERY_TOKEN_INVALID` (400 not 401 on purpose: the client's 401 interceptor at `api.ts:207` would otherwise start a refresh on an unauthenticated device). Path is deliberately not `/reset-password` (`test_auth_interceptor.py:1626`).
* Client: `ResetPasswordScreen` (unauth `AuthNavigator` only), `AuthStackParamList.ResetPassword`, `authService.completePasswordRecovery`, 8 i18n keys ×2 locales (parity 915→923 key-lines), `jest.config.js` gains `@react-navigation` in the transform allowlist (measured inert for the existing suites — no suite loads the real ESM build today).
* Red tests: 5 client files (N nodes) + 1 backend file (15 nodes); mutation list executed. Full mobile suite: N suites / N passed vs 278 / 2,729 baseline; backend comm set 42+9+1 files, `branch-only-NEW == []`, the two `test_auth_interceptor` baseline rows identical both sides.
* Unmeasured, to be settled by the first canary reset: the `amr` claim shape (gate fails closed, logs method names only) and the fragment shape (parser accepts `#` and `?`).
* Activation: OTA → allow-list → flag. Nothing flips in this PR.

## 10. Measurements run

**M1 — worktree state**
```
$ git rev-parse HEAD && git rev-parse origin/main && git status --short
ed75dc708b82c0b911c9de8a3e59d4418c6e278c
ed75dc708b82c0b911c9de8a3e59d4418c6e278c
(empty)
SmartCompareApp/node_modules -> /c/Users/SynAckITPC/Documents/AI/sc-scraper-proof/SmartCompareApp/node_modules   (junction; @babel/core + .bin/jest present)
.env present
```

**M2 — versions**
```
$ node node_modules/typescript/bin/tsc -v            → Version 5.9.3
@react-navigation/native 7.2.4 | native-stack 7.15.0 | bottom-tabs 7.16.0 | @react-navigation/core 7.17.4
expo-linking MISSING | expo 54.0.34 | react-native 0.81.5 | jest 29.7.0 | ts-jest 29.4.9 | expo-secure-store 15.0.8
package.json: expo ~54.0.33, @react-navigation/native ^7.1.28, jest ^29.7.0, ts-jest ^29.4.6, typescript ~5.9.2
node v24.11.1
installed supabase 2.28.0 / supabase_auth 2.28.0 ; requirements.txt:156 supabase==2.31.0, :158 supabase-auth==2.31.0
ruff 0.16.5
@react-navigation/{native,core}/lib = module, typescript (no commonjs); exports {".": {default: ./lib/module/index.js}}; escape-string-regexp 4.0.0 (CJS); query-string 7.1.3 (CJS)
```

**M3 — zero hits in App.tsx**
```
$ grep -n -i "reset-password\|ResetPassword\|resetPassword\|reset_password\|type=recovery\|recovery" SmartCompareApp/App.tsx   → (nothing)
$ sed -n 283p SmartCompareApp/App.tsx → (blank)      $ sed -n 539p app/services/auth_service.py → (blank)
```

**M4 — react-navigation fragment probe** (`.qa-w3b/probes/w36_linking.probe.test.ts`; invoked from `SmartCompareApp`:
`node node_modules/jest/bin/jest.js --ci --rootDir . --roots ../.qa-w3b/probes --testMatch "**/*.probe.test.ts" --transformIgnorePatterns "node_modules/(?!(@react-navigation)/)"` — the `--roots`/`--testMatch` overrides are needed because `jest.config.js` `testMatch` only covers `**/__tests__/**`; the transform override is the §4.8 change)
```
P1 extractPathFromURL -> "reset-password#access_token=x&refresh_token=y&type=recovery"
P2 today -> undefined
P3 proposed+fragment -> undefined
P4 proposed+query -> {"routes":[{"name":"Auth","state":{"routes":[{"name":"ResetPassword","path":"reset-password?access_token=x&type=recovery","params":{"access_token":"x","type":"recovery"}}]}}]}
P5 proposed bare -> {"routes":[{"name":"Auth","state":{"routes":[{"name":"ResetPassword","path":"reset-password"}]}}]}
PASS  6 passed (P6: r/qr-abc123 → Auth>Register, c/tok → ReferralLanding, q/tok → InviteeQuiz under the proposed config)
```

**M5 — installed router source**
```
core/src/getStateFromPath.tsx:749  const query = path.split('?')[1];
core/src/getStateFromPath.tsx:750  const params: Record<string, unknown> = queryString.parse(query);
grep -n "#\|fragment\|hash" core/src/getStateFromPath.tsx → (nothing)
native/src/useLinking.native.tsx:27-39 Linking.getInitialURL() / Linking.addEventListener('url'); :129 extractPathFromURL; :133 getStateFromPathRef.current(path, configRef.current); :23 enabled = true
```

**M6 — backend probe** (`PYTHONPATH=. PYTHONIOENCODING=utf-8 python .qa-w3b/probes/w36_backend_probe.py`)
```
A. request_password_reset -> {'success': True, 'message': 'Password reset email sent'}
A. reset_password_email call args: call('user@test.com')
B. POST /recover redirect_to=None body={'email': 'user@test.com', 'gotrue_meta_security': {'captcha_token': None}}
B. POST /recover redirect_to='qaren://reset-password' body={'email': 'user@test.com', 'gotrue_meta_security': {'captcha_token': None}}
C. _request: redirect_to: Optional[str] = None,  /  if redirect_to:  /  query = query.set("redirect_to", redirect_to)
D. SyncClientOptions().flow_type = pkce
D. reset_password_for_email mentions code_challenge: False
E. get_user sig: (self, jwt: 'Optional[str]' = None) -> 'Optional[UserResponse]'
E. admin.update_user_by_id sig: (self, uid: 'str', attributes: 'AdminUserAttributes') -> 'UserResponse'
```
Also read: `reset_password_email(self, email, options=None)` → `reset_password_for_email(email, options or {})`; `set_session(self, access_token, refresh_token)`; `update_user` requires a stored session (`AuthSessionMissingError`).

**M7 — existing pins that shape the design**
```
tests/test_auth_interceptor.py:684   mock_client.auth.reset_password_email.assert_called_once_with("user@test.com")
tests/test_auth_interceptor.py:1624-1626  "/api/v1/auth/password-reset" in routes ; "/api/v1/auth/reset-password" not in routes
tests/test_429_contract.py:55  _ROUTE = "/api/v1/auth/password-reset" (3/minute)
tests/test_security_regression.py:419-433  '@limiter.limit("5/minute")' / ("3/minute") / ("1/minute") substring pins
app/middleware/error_handler.py:23-34 STATUS_CODE_MAP {400: BAD_REQUEST, 401: AUTH_REQUIRED, …, 503: FEATURE_DISABLED}; :72-90 _is_structured_detail
app/api/auth_routes.py:66 _validate_password_strength; :123 PasswordResetRequest; :136-143 ChangePasswordRequest; :725-735 password_reset (3/minute); :819 PUT /password (5/minute, Depends(get_current_user))
app/services/auth_service.py:418-433 logout_upstream_revocation_enabled (per-call os.getenv idiom); :514 _revoke_token; :629 admin.auth.admin.update_user_by_id(user_id, {"password": new_password}); :752-761 request_password_reset
SmartCompareApp/src/services/api.ts:50-57 request Bearer; :207-209 refresh only on 401; :212-216 authFlowEndpoints skip list
SmartCompareApp/src/services/sentry.ts:28-40 SENSITIVE_PATTERNS — query rung covers q/query/email/search/text ONLY (no access_token rung); JWT rung eyJ…; hex-32 rung
SmartCompareApp/app.json:15 "scheme": "qaren"; :59-61 https pathPrefix /r/ /c/ /q/; :67 {"scheme": "qaren"}
SmartCompareApp/__mocks__/react-native.ts:128-133 Linking mock (getInitialURL → null, addEventListener → {remove})
```

**M8 — i18n / copy fences**
```
grep -c '^  "' src/i18n/en.json src/i18n/ar.json → 915 / 915
__tests__/i18n.test.ts:8-9 same keys; __tests__/i18n/no-missing-referenced-keys.test.ts walks src/**; src/i18n/.copy-policy.json scary_vocab_en ["couldn't","try again","Failed to"], scary_vocab_ar ["تعذر","فشل","تقدير","مُقدَّر"]
existing keys reused: auth.confirmPassword (en:266), auth.passwordRequirements (:910), auth.signIn (:272), auth.resetPassword (:275)
```

**M9 — client validation rule** `RegisterScreen.tsx:192  password.length < 10 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)`

**M10 — backend comm sets**
```
$ grep -rlE "auth_service|auth_routes" tests/ | wc -l → 44
(42 test files: test_429_contract, test_account_deletion, test_attribution_endpoint, test_attribution_service, test_attribution_service_edges, test_auth_ai_sharing_toggle, test_auth_demographics, test_auth_interceptor, test_auth_preferences_completed_warning, test_auth_refresh_and_revocation, test_auth_routes_invite_fingerprint, test_b2_strict_optional_auth, test_brute_force, test_budget_value_literal, test_bundle_c_feature_flag, test_cohort_profile_governorate, test_cohort_summary_orchestrator, test_endpoint_shapes_vs_jsx, test_error_middleware, test_history_routes, test_home_routes, test_invitee_quiz, test_m13_01_slowapi_middleware, test_m18_offload_sweep_residual, test_paid_route_metering, test_personalization, test_preference_history_wiring, test_profile_routes, test_push_token_endpoint, test_referral_e2e, test_referral_feature_flag, test_referral_must_fixes, test_referral_routes, test_referral_share_privacy, test_register_invite_linking, test_security_regression, test_share_routes, test_social_login_smoke, test_supabase_client_reuse, test_tier_detection, test_usage_device_inheritance; non-tests: tests/.pre_impl_failures.txt, tests/_env_safety.py, tests/integration/bundle-e-smoke.sh)
$ grep -rl "SmartCompareApp" tests/ → 9: test_b2_strict_optional_auth, test_events_allowlist_superset, test_feature_bucket_parity, test_feedback_allowlist_superset, test_migration_037_security_definer_grants, test_paid_route_metering, test_review_paraphrase, test_security_regression, test_timeout_partial_integration
tests/.pre_impl_failures.txt rows in the set: test_auth_interceptor::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully
```

**M11 — mobile neighbour set** `grep -rlE "\.\./App'|\.\./App\"|App\.tsx|src/types|services/authService|ForgotPasswordScreen|i18n/(en|ar)\.json|LoginScreen" __tests__ | wc -l → 98` (full list captured in the session transcript; it spans every `App.*`, `AuthScreens.*`, `HomeScreen.*`, `ResultsScreen.*`, `api.*`, `authService.*`, `i18n*`, `rtl/*`, `bootSentry*.w312`, `types.contract`, `Screens.bundleD.contract`).

**M12 — finding text** `docs/investigations/2026-09-06-full-review-tables.md:51`, `2026-09-06-full-review.md:18` and W3 table `:133`, `2026-09-06-full-review-verified.json` unit "U13" (`tests_first` two entries — both confirmed RED above). `2026-09-02-mobile-checkup-findings.md` has no password-reset row.

**Not run (by rule):** the full jest suite; any `LIVE=1`/network test; `_proof/sweep2.py`; no `git` mutation. `git status` at the end of this batch: empty (only `.qa-w3b/` — gitignored via `.gitignore:72 .qa-*/`).

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS**. Every anchor, probe and library claim in sections 1-10 was re-measured at `ed75dc70` (worktree HEAD == origin/main, `git status` empty; tsc 5.9.3, node v24.11.1, `@react-navigation/native` 7.2.4 / core 7.17.4 / native-stack 7.15.0, expo 54.0.34, RN 0.81.5, jest 29.7.0, ts-jest 29.4.9, `expo-linking` absent; supabase/supabase_auth 2.28.0 installed vs 2.31.0 pinned at `requirements.txt:156/158`; ruff 0.16.5). Both probes were re-run and reproduce byte-for-byte (P1-P6 pass; backend A-E identical). Nothing below rejects the design; each ruling closes a gap a red-phase agent would otherwise guess at, or that would ship a defect.

1. **`complete_password_recovery` MUST consult the local blacklist BEFORE `get_user`, and a 16th backend node pins it.** As specified, `_revoke_token(access_token)` only protects `verify_token` callers; the new route itself never reads the blacklist, so the SAME recovery token could be replayed against `POST /password-recovery` for its whole upstream lifetime (open question 4 admits the upstream invalidation is unmeasured). First statement of the service: `if await _is_token_revoked_async(access_token): return {"success": False, "code": "RECOVERY_TOKEN_INVALID", "error": "This reset link is no longer valid."}` (`auth_service.py:525-548`, fail-open when Redis is absent, patchable at `auth_service._is_token_revoked` — both branches reference the module-level name). Node 16: patch `_is_token_revoked` to return True → result code `RECOVERY_TOKEN_INVALID`, `get_user` NOT called, admin NOT called. Mutation: drop the check → red.

2. **Upstream calls go through `run_db`, exactly like `verify_token` (`auth_service.py:392`).** `client.auth.get_user(access_token)` and `admin.auth.admin.update_user_by_id(...)` are blocking Supabase round trips; wrap each in `await run_db(lambda: ...)` (`from app.utils.db_offload import run_db` is already imported at `:29`; flag OFF it runs inline, byte-identical). Tests are unaffected (mocks return synchronously).

3. **The route module must import the new service name into its own namespace, and the handler takes `request: Request` first.** `auth_routes.py:25` is `from app.services.auth_service import (...)`; add `complete_password_recovery` to that list, otherwise `patch("app.api.auth_routes.complete_password_recovery")` (nodes 5-7) raises `AttributeError`. Every `@limiter.limit` sibling takes `request: Request` as its FIRST parameter (`:727`, `:822`) — slowapi requires it; the new signature is `async def password_recovery(request: Request, body: PasswordRecoveryRequest)`. The conftest autouse `_reset_rate_limiter` (`tests/conftest.py:237-243`) clears the in-memory limiter before each test, so nodes 5-7 cannot trip the new `5/minute` on each other.

4. **AMR decode: base64url with padding restored; the rejection log is WARNING; caplog must name the logger.** GoTrue strips `=` padding; decode `seg = token.split(".")[1]` as `base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))`; ANY exception in the decode (non-JWT input, bad JSON, fewer than 3 segments) → `RECOVERY_TOKEN_INVALID`, admin NOT called (same fail-closed branch as "amr missing"). Node 13's fixture builds the payload segment the same way (`base64.urlsafe_b64encode(json.dumps(...).encode()).rstrip(b"=")`), so a padding bug reddens it. The one rejection line `[auth] password recovery rejected: amr=%s` is emitted at **WARNING**, and nodes 13/14 read it with `caplog.at_level(logging.WARNING, logger="app.services.auth_service")` — the pattern `tests/test_auth_refresh_and_revocation.py:655` already uses; without the explicit logger/level the records are not captured and both nodes would be vacuous.

5. **Node 4 (wire pin) gains a PKCE guard; a red there on CI is a STOP, not a fix-forward.** Measured on installed 2.28.0: `reset_password_for_email` (`gotrue_client.py:819-836`) sends `body={'email', 'gotrue_meta_security'}` and no `code_challenge`, even though `SyncClientOptions().flow_type == 'pkce'` (the SDK's own `SyncGoTrueClient.__init__` default is `flow_type='implicit'`; `code_challenge` appears in that file only at `:1173-1179`, the OAuth URL builder). The 2.31.0 wheel is NOT in the local pip cache (`pip cache list` → nothing), so the pinned build is unverifiable offline. Add to node 4: the recorded `body` carries no truthy `code_challenge`. If 2.31.0 ever sends a challenge, GoTrue redirects with `?code=…` instead of `#access_token=…`, the verifier lives in a per-call throw-away client, and this unit's parser cannot complete the flow — the writer re-specs; nobody loosens the pin.

6. **The override routes EVERY `reset-password` path to the screen, tokens or not; node 5 changes accordingly.** GoTrue's failure redirect for an expired/used link is `qaren://reset-password#error=access_denied&error_code=otp_expired&error_description=…`. Under the spec as written that path falls to the default parser → `undefined` (P3) → the app opens on Login with no message: the most common failure has no UX. Ruling: the FIRST branch of the override is `if (/^\/?reset-password(?:[#?]|$)/.test(path)) { const r = parseRecoveryLink(path); if (r) setPendingRecovery(r); return getStateFromPath('reset-password', options); }` — the screen's empty-slot branch already renders `auth.resetLinkExpired` + request-new-link. Node 5 therefore asserts, for `reset-password#access_token=x&type=signup`, for `reset-password#type=recovery` (no token) and for `reset-password#error=access_denied&error_code=otp_expired`: `focused(state)` equals `['Auth','ResetPassword']`, `consumePendingRecovery() === null`, and `JSON.stringify(state)` contains none of the fragment's values. The `type === 'recovery'` mutation still reddens it (slot filled on `type=signup`). `parseRecoveryLink` itself stays as specified (returns null for those inputs — `passwordRecoveryLink.w36` nodes unchanged).

7. **The two CTAs use `navigation.reset`, not `navigate`, so Back can never land on a spent screen.** On the cold-start path the Auth stack is exactly `[ResetPassword]`; `navigate('Login')` PUSHES Login and the back gesture returns to a screen whose slot is spent (renders "expired"). Success CTA: `navigation.reset({ index: 0, routes: [{ name: 'Login' }] })`. Expired-state CTA: `navigation.reset({ index: 1, routes: [{ name: 'Login' }, { name: 'ForgotPassword' }] })` (ForgotPasswordScreen's own back link is `goBack()` at `:129`, which must land on Login). `ResetPasswordScreen.w36` nodes 1 and 4 assert `reset` was called once and the LAST route name is `'Login'` / `'ForgotPassword'` respectively; `mockNavigation` gains `reset: jest.fn()`.

8. **i18n keys are FLAT top-level entries.** `en.json`/`ar.json` are flat maps (`"auth.confirmPassword": …` at en:266; `__tests__/i18n.test.ts:5-6` compares TOP-LEVEL `Object.keys`; 915 == 915 measured, set-equal). The 8 new keys are written as `"auth.setNewPassword": "…"` top-level strings — a nested `"auth": { … }` object would pass the parity test while breaking `t()` resolution. Existing keys confirmed: en:266 `auth.confirmPassword`, :272 `auth.signIn`, :910 `auth.passwordRequirements`, :853 `auth.resetMessage`. The anchor `RegisterScreen.tsx:192` carries the RULE but its copy is a hard-coded English literal (`'Password must be at least 10 characters with 1 uppercase…'`), so the new screen mirrors the regex only and renders `t('auth.passwordRequirements')`.

9. **jest.config.js allowlist token — the spec's "three importers" is a miscount; the conclusion holds and was measured.** 17 files under `__tests__` reference `@react-navigation`; 16 replace it with a `jest.mock(...)` factory and the 17th (`refetchOnFocus.test.ts:37-63`) is a source-regex scan with no import. The `ts-jest` preset transforms only `^.+\.tsx?$`, so `lib/module/*.js` stays untransformed either way. Measured: `HistoryScreen.searchState.a12`, `refetchOnFocus`, `AuthScreens` = 3 suites / 35 tests PASS under the exact proposed pattern `node_modules/(?!(…|react-native-reanimated|@react-navigation)/)`. The green-phase full run remains mandatory.

10. **Sensitive-copy inventory the PR body must record (no code change):** (a) `useLinking.native.tsx:157/163` passes `extractPathFromURL(prefixes, url)` — the RAW path WITH the fragment — to `onUnhandledLinking` on EVERY initial URL, and `NavigationContainer.tsx:98-141` keeps it in React state as `lastUnhandledLink`, cleared only when `getCurrentRoute().path` equals it — which, after the rewrite to bare `reset-password`, it never does. Nothing in the installed core/native reads that state (only the `UNSTABLE_UnhandledLinkingContext` export at `native/src/index.tsx:10`), and `src/` registers no Sentry navigation integration (grep `reactNavigationIntegration|registerNavigationContainer` → 0), so it is an in-memory copy, not a leak — but it exists and is named. (b) `sentry.ts:28-40`: the JWT rung covers the access token; a refresh token is NOT JWT-shaped and would not be scrubbed — a second reason the client discards it. (c) Backend 422s do not echo input (`error_handler.py:146-162` summarises `loc` + `msg` only), so a weak-password 422 never returns the password; the same handler already governs `ChangePasswordRequest`.

11. **Cold-start structure is confirmed, not assumed.** `App.tsx:331-335` returns `<SplashScreen/>` BEFORE the container mounts; `<NavigationContainer linking>` (`:382`) mounts only after `isLoading`/`showSplash` clear, with `Auth` registered in the `!isAuthenticated` branch (`:386-390`) — the identical mechanism `r/:code` relies on today, so `Linking.getInitialURL()` is read after the splash and `Auth > ResetPassword` is resolvable. The `linking` object is defined INSIDE the component (`:350`) but closes over nothing, so moving it to module scope in `src/navigation/linking.ts` is behaviour-neutral. `App.distinctRouteNames.test.ts:31` uses `/<Stack\.Screen…/` — `<AuthStack.Screen` does not match (the `<` anchors). No `StrictMode` wrapper exists (`App.tsx`/`index.ts` grep → 0), so the `useState(() => consumePendingRecovery())` initializer runs once.

12. **Finding-text anchors, corrected where two documents disagree.** `tables.md:51` and `verified.json:12535` cite `App.tsx:283` / `App.tsx:318-322`; both are blank/moved at `ed75dc70` — the linking config is `App.tsx:350-379`, `AuthNavigator` `:94-105`. `verified.json` has THREE units named "U13" (code lane `:392`, CI lane `:929`, mobile lane `:1919`); the spec means the mobile-lane one at `:1919-1934`, whose two `tests_first` entries are the plan's two red tests — both re-confirmed RED. `verified.json:12535`'s proposed fix (client-side `setSession` + `updateUser`) is superseded by this spec's backend completion route; the spec's rationale (`set_session` side effects, refresh token never retained) stands.

13. **Accepted as specified (each re-verified on disk):** structured 400 detail → top-level `code` via `_is_structured_detail` (`error_handler.py:72-90`, handler `:112-141`); `api.ts:207-209` refreshes ONLY on 401 (400 is correct; `/auth/password-recovery` is deliberately NOT added to the `authFlowEndpoints` list at `:213`); `parseApiError` surfaces `data.error` (`api.ts:966-968`); `test_auth_interceptor.py:684` one-positional pin and `:1626` `/reset-password`-absent pin; `test_security_regression.py:419-433` are substring pins (additive-safe); `PUT /password` `5/minute` at `:820`; `_validate_password_strength` `:66-76` reused by `:89-92` / `:140-143`; `UserDoesntExist(access_token)` records the token in `args` (no `super().__init__`, but `BaseException.__new__` stores the constructor args), so `str(e)` IS the bearer — the scrub stays; `deferredInviteCode.ts` slot idiom; `app.json:15` scheme + `:67` `{scheme: qaren}` intent filter (no host/path restriction); `eslint.config.js:48-58` applies `i18next/no-literal-string` to `src/screens/**` (the new screen) and `:63-77` turns it off for `__tests__` and `src/services/**` (`src/navigation/**` is in neither list — rule not enabled there); comm sets 44 paths / 42 test files / 9 mobile-scanning files and the 98-file mobile neighbour set reproduce exactly; the two `test_auth_interceptor` baseline rows are the only expected both-sides failures; `verify_token` (`:365-400`) already uses `client.auth.get_user(access_token)` with an explicit jwt on the anon client, so the recovery path reuses a proven call shape.

14. **Ahmed dependencies and open questions stand as written (§8).** One addition for the PR body: with the flag ON the email link is only useful once the Supabase allow-list holds `qaren://reset-password`; until then GoTrue silently falls back to the Site URL — documented, unmeasured here, and exactly why activation order is OTA → allow-list → flag.

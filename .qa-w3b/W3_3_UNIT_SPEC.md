# W3-3 — device fingerprint on social sign-in + share

## 1. Header

| | |
|---|---|
| Unit | W3-3 |
| Findings | `MB-NETWORK-CONTRACT-03` (social sign-up never carries `X-Device-Fingerprint`; social backend path never writes `users.device_fingerprint_hash`), `MB-NETWORK-CONTRACT-04` (share payload never carries `device_fingerprint_hash`) |
| Base | `ed75dc70` (origin/main; worktree `sc-w3-fp`) |
| OTA class | **mixed** — client half **OTA-safe** (two `.ts`/`.tsx` edits, no native surface); backend half **backend-only**, additive, behind **`ENABLE_SOCIAL_DEVICE_FINGERPRINT` default OFF, read per call** |
| Flag | `ENABLE_SOCIAL_DEVICE_FINGERPRINT` (backend only; the client half is unflagged by nature) |
| Migration | none (column `users.device_fingerprint_hash` exists since migration 021; `referral_invites.device_fingerprint_hash` since 014) |
| Toolchain measured | TypeScript **5.9.3** installed (package.json `~5.9.2`), jest 29.7.0, ts-jest 29.4.9, expo-crypto 15.0.9 (`~15.0.8`), expo-application 7.0.8 (`~7.0.8`); Python 3.12.9, ruff 0.16.5. **Backend local-vs-pin drift, recorded not fixed:** installed fastapi 0.115.0 / starlette 0.38.6 / supabase 2.28.0 / pydantic 2.7.0 vs `requirements.txt` fastapi==0.141.1 / starlette==1.6.0 / supabase==2.31.0 / pydantic==2.13.4 (the M13 drift class). Nothing in this unit depends on a version-specific shape — `request.headers.get`, `TestClient(..., headers=)`, `MagicMock` chains — but the green phase must state which version its pytest numbers came from. |

## 2. Scope correction — what is ALREADY on main at `ed75dc70`

The plan (`docs/investigations/2026-09-06-full-review.md:130`) lists three red tests. **All three are still RED — measured, not assumed (§3, §10). Nothing is dropped.** What HAS moved is the anchors and one design instruction:

* **Plan anchor `authService.ts:570/682` → `:665` (`signInWithGoogle`) and `:814` (`signInWithApple`).** The two raw `fetchWithDeadline` calls are at `:728-736` (google, headers at `:732`) and `:863-875` (apple, headers at `:867`). Register's header send is at `:148`, its fingerprint read at `:131-136`.
* **Plan anchor `ResultsScreen.tsx:797-810` → `:829-841`** (the single `<ShareBottomSheet …/>` mount). It passes `visible / comparison / onClose / onShared / lifetimeRemaining` and **no `deviceFingerprintHash`** (grep of `ResultsScreen.tsx` for `deviceFingerprint` = 0 hits). `ShareBottomSheet.tsx:43` declares the prop, `:118` destructures it, `:159` forwards it — the three declaring lines the verifier found, still no caller.
* **Plan anchor `auth_routes.py:365-391` → `:444-472`** (the register fingerprint block); the social route is at `:849-856`.
* **-04 is NOT already closed.** The `device_fingerprint_hash` field at `ShareBottomSheet.tsx:159` has existed since the sheet shipped; the bug is that its only source is an optional prop nobody sets. Measured: a share-target tap sends `{"comparison_id","share_target","privacy"}` and no hash (§3.2).
* **-04's BACKEND half is already green and is dropped from the red list:** `referral_routes.py:117-119` validates `device_fingerprint_hash` with `pattern=r"^[a-f0-9]{64}$"`, `:209` passes it to `service.create_invite(...)`, and `referral_service.py:322` writes it into the `referral_invites` insert payload. `tests/test_abuse_detection.py::TestEvaluateInvite::test_same_device_short_circuits` (`:241-254`) already pins `evaluate_invite → flagged_reason == "SAME_DEVICE"`. The plan's "evaluate_invite returns SAME_DEVICE" test would be green today = decoration; do not build it. (An optional route-level pin that the hash reaches `create_invite(device_fingerprint_hash=…)` is listed in §6 — green today, cheap, not a red test.)
* **The plan's "extract `_apply_device_fingerprint` and apply it on the social route" must NOT be done verbatim** — reusing the register block unchanged on the social route would RESET an existing social user's `lifetime_comparisons_used` (§4.2, hazard H1). The extraction is kept but split so the register path is byte-identical and the social path is monotone.
* **A fourth defect surfaced while designing the failure-tolerance path and is measured RED (§3.4):** `deviceFingerprint.ts:17-41` clears `inflight` only on success, so ONE transient SecureStore/crypto rejection poisons every later `getDeviceFingerprint()` call for the process lifetime. Both new call sites (and register today) swallow the failure, so after one keychain hiccup the device would silently send no fingerprint anywhere for the session. It is a 3-line fix in a file this unit already reasons about; it is listed as red test C5 and the reviewer may cut it to keep the diff minimal — if cut, the PR must say the tolerance path is permanent-on-first-failure.

## 3. The defect — measured at `ed75dc70`

### 3.1 Social sign-in never sends the header (-03, client)

`SmartCompareApp/src/services/authService.ts:728-736` (google):

```ts
      response = await fetchWithDeadline(
        `${API_BASE_URL}/api/v1/auth/social-login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
        SOCIAL_LOGIN_TIMEOUT_MS
      );
```

`:863-875` (apple) is the same shape with `headers: { 'Content-Type': 'application/json' }` at `:867`. Contrast register, `:131-148`:

```ts
  let fingerprint: string | null = null;
  try {
    fingerprint = await getDeviceFingerprint();
  } catch (e) {
    if (__DEV__) console.warn('[AUTH] device fingerprint unavailable:', e);
  }
  …
      fingerprint ? { headers: { 'X-Device-Fingerprint': fingerprint } } : undefined,
```

`fetchWithDeadline` (`src/services/fetchWithDeadline.ts:66-107`) forwards `init` verbatim (`fetch(input, { ...init, signal })`), so adding a header key to the `init.headers` object reaches the wire unchanged.

Probe `.qa-w3b/probes/socialFingerprintHeader.probe.test.ts` (harness = `__tests__/services/authService.socialTimeout.a8.test.ts` + a recorder on `deviceFingerprint`):

```
[PROBE google] headers = {"Content-Type":"application/json"} getDeviceFingerprint calls = 0
[PROBE apple] headers = {"Content-Type":"application/json"} getDeviceFingerprint calls = 0
  × google: POST /auth/social-login carries X-Device-Fingerprint   Expected: "bbb…b" Received: undefined
  × apple: POST /auth/social-login carries X-Device-Fingerprint    Expected: "bbb…b" Received: undefined
Tests: 2 failed, 2 total
```

### 3.2 Share payload never carries the hash (-04, client)

`SmartCompareApp/src/components/ShareBottomSheet.tsx:151-165`:

```tsx
  const handleTargetPress = async (target: ShareTarget) => {
    if (submitting) return;
    setErrorMessage(null);
    setSubmitting(target);
    try {
      const result = await createShare({
        comparison_id: comparison.id,
        share_target: target,
        device_fingerprint_hash: deviceFingerprintHash,
        privacy: { … },
      });
```

`deviceFingerprintHash` is the optional prop at `:43`; `ResultsScreen.tsx:830-841` — the ONLY mount (`grep -rlE ShareBottomSheet src` = ResultsScreen, ResultsContent (comment), deriveTone (comment)) — does not pass it. `createShare` (`referralService.ts:106-113`) posts `input` as-is, so `undefined` is dropped by `JSON.stringify` and the backend's `Optional` field stays `None` → `referral_invites.device_fingerprint_hash` NULL → `abuse_detection_service._get_referrer_device_hash` (`:132-150`) returns None → `is_same_device` False → control 1 dead.

Probe `.qa-w3b/probes/sharePayloadFingerprint.probe.test.tsx` (harness = `__tests__/ShareBottomSheet.lifetimeLimit.test.tsx`, press `share-target-copy`):

```
[PROBE share] payload = {"comparison_id":"cmp-123","share_target":"copy","privacy":{"show_name":true,"show_result":true,"show_reasons":true}} getDeviceFingerprint calls = 0
  × tapping a share target sends a 64-hex device_fingerprint_hash   Received has value: undefined
Tests: 1 failed, 1 total
```

### 3.3 The social route never writes the hash (-03, backend)

`app/api/auth_routes.py:849-856`:

```python
@router.post("/social-login")
@limiter.limit("10/minute")
async def social_login(request: Request, body: SocialLoginRequest):
    """Authenticate via Google or Apple ID token. Creates account if new."""
    result = await sign_in_with_social(body.provider, body.id_token, body.nonce)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result
```

`request` is accepted (slowapi needs it) and never read. `grep -c device_fingerprint app/services/auth_service.py` = **0**; `sign_in_with_social` (`auth_service.py:551-617`) inserts `{"id","email","auth_provider","subscription_tier":"free"}` for a new user (`:580-586`) and nothing else. The only writer of `users.device_fingerprint_hash` in the codebase is the register block `auth_routes.py:444-472`:

```python
    fp = request.headers.get("X-Device-Fingerprint")
    if fp and not _DEVICE_FINGERPRINT_RE.match(fp):
        logger.info("device-fp header rejected: invalid format (expected 64-char hex), len=%d", len(fp))
        fp = None
    if fp and new_user_id:
        try:
            admin_client = get_admin_supabase_client()
            prior = (admin_client.table("users").select("lifetime_comparisons_used")
                     .eq("device_fingerprint_hash", fp)
                     .order("lifetime_comparisons_used", desc=True).limit(1).execute())
            inherited = 0
            if prior.data:
                inherited = prior.data[0].get("lifetime_comparisons_used", 0) or 0
            admin_client.table("users").update(
                {"device_fingerprint_hash": fp, "lifetime_comparisons_used": inherited}
            ).eq("id", new_user_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"device-fp inheritance failed (silent): {exc}")
```

Probe `.qa-w3b/probes/probe_social_fp.py` (seams = `tests/test_social_login_smoke.py` route-level `sign_in_with_social` patch + `tests/test_auth_routes_invite_fingerprint.py` recording admin chain; env `ENABLE_SOCIAL_DEVICE_FINGERPRINT=true` forced to show that nothing on main reads it):

```
[PROBE social-login] status=200 sign_in_with_social awaited=1 get_admin_supabase_client calls=0 tables=[] update_called=False update_args=None
E   AssertionError: social-login never wrote device_fingerprint_hash
1 failed
```

Downstream consumers that fail OPEN on the NULL: `referral_service._referrer_device_lifetime_count` (`:773-812`, `if not fp: return 0` → `LIFETIME_CAP` never reached for social referrers), and `abuse_detection_service.evaluate_invite` (`:240-262`, `invitee.get("device_fingerprint_hash")` None → `is_same_device` False).

### 3.4 One rejection poisons `getDeviceFingerprint()` for the session (new, client)

`SmartCompareApp/src/services/deviceFingerprint.ts:17-41`:

```ts
export async function getDeviceFingerprint(): Promise<string> {
  if (cached) return cached;
  if (inflight) return inflight;
  inflight = (async () => {
    let nonce = await SecureStore.getItemAsync(NONCE_KEY);
    …
    cached = hash;
    inflight = null;
    return hash;
  })();
  return inflight;
}
```

`inflight = null` runs only on the success path. Probe `.qa-w3b/probes/fingerprintInflightPoison.probe.test.ts` (SecureStore rejects once, then resolves):

```
[PROBE inflight] second call REJECTED with: keychain busy getItemAsync calls = 1
  × second call after a transient SecureStore failure
```

The second call never re-reads SecureStore; it returns the first rejected promise. Register (`:131-136`) already swallows this, so today a phone that hit one keychain error at first register sends no fingerprint until the process restarts. The two new tolerant call sites inherit the same exposure.

## 4. The fix — MINIMAL design

### 4.1 Client half (OTA-safe, unflagged, backward-compatible with the backend on main)

**`SmartCompareApp/src/services/authService.ts`** — in `signInWithGoogle` and `signInWithApple`, immediately before the `fetchWithDeadline` call (i.e. AFTER the native SDK sign-in has returned an id token, so the `SIGN_IN_CANCELLED` / no-idToken branches are untouched), add the register-shaped block:

```ts
    let fingerprint: string | null = null;
    try {
      fingerprint = await getDeviceFingerprint();
    } catch (e) {
      if (__DEV__) console.warn('[AUTH] device fingerprint unavailable:', e);
    }
```

and change ONLY the headers literal at `:732` / `:867`:

```ts
          headers: {
            'Content-Type': 'application/json',
            ...(fingerprint ? { 'X-Device-Fingerprint': fingerprint } : {}),
          },
```

What does NOT change: the body (`{ provider, id_token }` for google — the B4 no-nonce invariant; `{ provider, id_token, nonce }` for apple), the deadline (`SOCIAL_LOGIN_TIMEOUT_MS`), the `isDeadlineError` branch, every `[B4-DIAG]` capture, the response handling, the outer catch. `getDeviceFingerprint` is already imported at `:53`. A header the backend on main ignores is harmless: `social_login` never reads `request.headers` today, and CORS/pinning do not inspect custom request headers (the register path already sends the same header through the same origin).

**Extra `__DEV__` console.warn** must stay single-line (the backend `test_security_regression.py` / M13-55 bare-console detector scans `SmartCompareApp` for console calls in auth; the existing `:135` line is the accepted form).

**`SmartCompareApp/src/components/ShareBottomSheet.tsx`** — resolve the hash inside `handleTargetPress` (the verifier's "safer shape given this prop has been optional-and-unset since it shipped"), keeping the prop as an explicit override:

```tsx
import { getDeviceFingerprint } from '../services/deviceFingerprint';
…
    try {
      let fp: string | undefined = deviceFingerprintHash;
      if (!fp) {
        try {
          fp = await getDeviceFingerprint();
        } catch {
          fp = undefined; // never block a share on a fingerprint failure
        }
      }
      const result = await createShare({
        comparison_id: comparison.id,
        share_target: target,
        device_fingerprint_hash: fp,
        privacy: { … },
      });
```

`ResultsScreen.tsx` is **not touched**. The wire format already matches the backend's `^[a-f0-9]{64}$` (`referral_routes.py:117-119`): `deviceFingerprint.ts:32-35` returns `Crypto.digestStringAsync(SHA256, raw)`, which on expo-crypto 15.0.9 is lowercase hex (the `CryptoEncoding.HEX` default; the register path has relied on it since Bundle A and `_DEVICE_FINGERPRINT_RE` accepts it in prod). A backend on main accepts the field today (Optional + pattern), so the client half alone is safe to ship and immediately makes `referral_invites.device_fingerprint_hash` non-NULL for new shares — **-04 closes with the client half alone (OTA), no backend change.**

**`SmartCompareApp/src/services/deviceFingerprint.ts`** (red test C5, reviewer may cut) — clear `inflight` on rejection too:

```ts
  inflight = (async () => { … })().catch((e) => { inflight = null; throw e; });
```

(or a `finally`). `cached` stays null on failure; the next call retries from SecureStore. No change to the success path, the nonce persistence, or `_resetCacheForTests`.

### 4.2 Backend half (additive, default OFF)

**`app/api/auth_routes.py` only.** No service change, no new module, no migration.

1. Add the flag helper next to `strict_optional_auth_enabled` (`:317-349`), same truthy set, read per call:

```python
def social_device_fingerprint_enabled() -> bool:
    return os.getenv("ENABLE_SOCIAL_DEVICE_FINGERPRINT", "false").strip().lower() in ("true", "1", "yes", "on")
```

2. Split the register block into two module-level helpers so register stays **call-for-call identical** (the existing `test_register_with_fingerprint_inherits_lifetime_counter` records the exact chain `table("users").select(...).eq(...).order(...).limit(...).execute()` then `table("users").update({...}).eq("id", …).execute()` and must stay green unchanged):

```python
def _read_valid_device_fingerprint(request: Request) -> Optional[str]:
    # verbatim :444-450 — header read + _DEVICE_FINGERPRINT_RE + the logger.info
def _inherit_device_counter(admin_client, fp: str, user_id: str, *, floor: int = 0) -> None:
    # verbatim :454-471 with ONE change: inherited = max(floor, prior)  (floor=0 ⇒ today's value)
```

`register` becomes `fp = _read_valid_device_fingerprint(request)` / `if fp and new_user_id: try: _inherit_device_counter(get_admin_supabase_client(), fp, new_user_id) except Exception as exc: logger.warning(...)` — same statements, same order, same log text.

3. In `social_login`, AFTER the `if not result["success"]: raise` and BEFORE `return result`:

```python
    if social_device_fingerprint_enabled():
        _apply_social_device_fingerprint(request, (result.get("user") or {}).get("id"))
    return result
```

with

```python
def _apply_social_device_fingerprint(request: Request, user_id: Optional[str]) -> None:
    """Best-effort; never raises; never touches the response body."""
    fp = _read_valid_device_fingerprint(request)
    if not fp or not user_id:
        return
    try:
        admin = get_admin_supabase_client()
        own = (admin.table("users").select("device_fingerprint_hash, lifetime_comparisons_used")
               .eq("id", user_id).limit(1).execute())
        row = (own.data or [{}])[0]
        if row.get("device_fingerprint_hash"):
            return                      # first-device binding already set — never re-bind
        _inherit_device_counter(admin, fp, user_id, floor=int(row.get("lifetime_comparisons_used") or 0))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"device-fp social apply failed (silent): {exc}")
```

**Why the social path cannot reuse the register block verbatim (hazard H1, design-changing):** `social_login` serves BOTH brand-new and returning users, and every social user on main today has `device_fingerprint_hash = NULL`. The register block computes `inherited` from OTHER rows carrying `fp` (the caller's own row has NULL so it is excluded) and then **overwrites** `lifetime_comparisons_used` with it — for a returning social user with `used=5` and no other row on the device that is `UPDATE … lifetime_comparisons_used = 0`: a fresh free quota on every social login, the exact opposite of the finding. `max(own, device-max)` is monotone (never lowers anyone), gives a NEW user exactly the register semantics (own=0), and backfills the existing social population on their next login — which is the only way the finding's impact (a) ever closes for accounts that already exist. Red test B2 pins the max; the mutation "reuse the register block" reddens it.

**Why write only when the row's hash is NULL:** register binds a user to the device of first signup and never re-binds; the social path mirrors that. A user signing in on a second device keeps the first binding. (Open question O1 records the alternative.)

**Cost with the flag ON:** one extra `SELECT … WHERE id = ?` per social login (indexed PK), plus the register-shaped SELECT+UPDATE only on the first login per user. Same sync supabase client on the event loop as the register block today (the LS-* sync-I/O class is a known, separately-tracked pattern; this unit does not offload it and does not make it worse per call than `/register` already is).

**Flag OFF (default):** `social_login` executes exactly today's four statements; `request.headers` is never read, `get_admin_supabase_client` is never called (red test B5 pins `call_count == 0`). The response body is returned verbatim in both states (B7 pins byte-equality to the mocked payload — nothing like `is_new_user` is added).

**Old clients** (97b5f15 and the pending OTA without this unit) send no header → `_read_valid_device_fingerprint` returns None → no DB call even with the flag ON.

### 4.3 Files to touch

| file | change |
|---|---|
| `SmartCompareApp/src/services/authService.ts` | fingerprint read + header on the two social fetches (`:728-736`, `:863-875`) |
| `SmartCompareApp/src/components/ShareBottomSheet.tsx` | import + in-tap resolution with prop override (`:151-165`) |
| `SmartCompareApp/src/services/deviceFingerprint.ts` | clear `inflight` on rejection (C5; optional) |
| `app/api/auth_routes.py` | flag helper; split `:444-472` into `_read_valid_device_fingerprint` + `_inherit_device_counter`; `_apply_social_device_fingerprint`; one gated call in `social_login` |
| `SmartCompareApp/__tests__/authService.socialFingerprint.w3-3.test.ts` | new (C1-C4, C6) |
| `SmartCompareApp/__tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx` | new (C7-C9) |
| `SmartCompareApp/__tests__/deviceFingerprint.test.ts` | + C5 |
| `tests/test_social_login_device_fingerprint.py` | new (B1-B8) |
| `CLAUDE.md` flag table | one row for `ENABLE_SOCIAL_DEVICE_FINGERPRINT` (at merge time, same block style as `ENABLE_LOGOUT_UPSTREAM_REVOCATION`) |

NOT touched: `ResultsScreen.tsx`, `auth_service.py`, `referral_routes.py`, `referral_service.py`, `abuse_detection_service.py`, `referralService.ts`, any migration, `package.json`, `app.json`.

## 5. Red tests

### Client — `SmartCompareApp/__tests__/authService.socialFingerprint.w3-3.test.ts`

Harness: copy the mocks of `__tests__/services/authService.socialTimeout.a8.test.ts:27-75` (google-signin virtual mock, `expo-apple-authentication` virtual mock, `expo-crypto` factory, Sentry shim, `global.fetch` recorder) **plus** `jest.mock('../src/services/deviceFingerprint', () => ({ getDeviceFingerprint: (...a) => mockGetDeviceFingerprint(...a) }))` (the `authService.m18.test.ts:41` idiom). Do not rely on the real `deviceFingerprint.ts` here — under the a8 `expo-crypto` factory `randomUUID` is undefined and the real module rejects, which is exactly what §3.4 measures.

| id | assertion | RED today because (measured) | mutation that must redden it after the fix |
|---|---|---|---|
| C1 | `signInWithGoogle()` with fetch → 200: `mockFetch.mock.calls[0][1].headers['X-Device-Fingerprint'] === 'b'.repeat(64)` AND `headers['Content-Type'] === 'application/json'` | headers = `{"Content-Type":"application/json"}`, `getDeviceFingerprint` calls = 0 | remove the spread on the google headers |
| C2 | same for `signInWithApple()` | identical output for apple | remove the spread on the apple headers |
| C3 | google body is still exactly `{provider:'google', id_token}` (`Object.keys(JSON.parse(body)).sort()` equals `['id_token','provider']`) while the header is present | green-today half is the B4 invariant; keep it in the same file so C1's implementer cannot "fix" by moving the hash into the body | put the hash in the body |
| C4 | `mockGetDeviceFingerprint.mockRejectedValue(new Error('keychain'))` → google AND apple still POST (fetch called once, no `X-Device-Fingerprint` key) and return `success:true` | **pin, green today** (fingerprint never called) — label "tolerance pin" | remove the try/catch around `getDeviceFingerprint()` (the rejection then reaches the outer catch → `success:false` `[B4-DIAG] threw before fetch`) |
| C6 | `SIGN_IN_CANCELLED` from `gs.signIn()` → `getDeviceFingerprint` NOT called and result `{success:false,error:'Sign-in cancelled'}` | pin, green today | move the fingerprint read above `gs.signIn()` |

### Client — `SmartCompareApp/__tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx`

Harness: `__tests__/ShareBottomSheet.lifetimeLimit.test.tsx:11-49` (haptics, i18n, `referralService` mock with a `createShare` recorder) + the `deviceFingerprint` recorder; `fireEvent.press(getByTestId('share-target-copy'))`; `await waitFor(() => expect(mockCreateShare).toHaveBeenCalledTimes(1))`. `Share.share` is not exported by `__mocks__/react-native.ts` (`Linking` is, `:128`; `canOpenURL` resolves false on purpose) — the TypeError is swallowed by the sheet's inner try and `onShared` still fires, which the probe confirmed; assert on `createShare`'s argument, not on `Share`.

| id | assertion | RED today because | mutation |
|---|---|---|---|
| C7 | mounted WITHOUT `deviceFingerprintHash` (as ResultsScreen mounts it): `createShare` payload `device_fingerprint_hash` matches `/^[a-f0-9]{64}$/` and equals the mocked value; `comparison_id`/`share_target`/`privacy` unchanged | payload = `{"comparison_id":"cmp-123","share_target":"copy","privacy":{…}}`, `getDeviceFingerprint` calls = 0 | drop the in-tap resolution |
| C8 | mounted WITH `deviceFingerprintHash='d'.repeat(64)`: payload carries `'d'*64` and `getDeviceFingerprint` is not called | pin, green today | ignore the prop / always resolve |
| C9 | `getDeviceFingerprint` rejects → `createShare` still called once with `device_fingerprint_hash: undefined`, `onShared` fires, no error text rendered | pin, green today | remove the inner catch (the rejection then hits the outer catch → `errorMessage` set, `createShare` never called) |

### Client — `SmartCompareApp/__tests__/deviceFingerprint.test.ts` (+1 case, optional C5)

| id | assertion | RED today because | mutation |
|---|---|---|---|
| C5 | `getItemAsync.mockRejectedValueOnce(err)` then resolved: first call rejects with `err`, second call resolves to a 64-hex string and `getItemAsync` was called twice | `[PROBE inflight] second call REJECTED with: keychain busy getItemAsync calls = 1` | revert the `.catch(() => { inflight = null })` |

### Backend — `tests/test_social_login_device_fingerprint.py`

Harness: `tests/test_social_login_smoke.py` autouse `limiter.enabled = False` fixture + `patch("app.api.auth_routes.sign_in_with_social", new=AsyncMock(return_value=SUCCESS))` + `patch("app.api.auth_routes.get_admin_supabase_client", return_value=admin)` with a `table()` side-effect that records table names and returns per-call chains (the `test_auth_routes_invite_fingerprint.py:170-215` idiom, extended so the FIRST `users` chain answers the own-row SELECT and the SECOND answers the device SELECT). Flag via `monkeypatch.setenv("ENABLE_SOCIAL_DEVICE_FINGERPRINT", "true")` / `delenv`. `FP = "a" * 64`.

| id | assertion | RED today because (measured) | mutation |
|---|---|---|---|
| B1 | flag ON, header FP, own row `{hash: None, used: 0}`, device max 3 → `update` called with exactly `{"device_fingerprint_hash": FP, "lifetime_comparisons_used": 3}` and `.eq("id", "00000000-…0001")`; status 200 | `get_admin_supabase_client calls=0 tables=[] update_called=False` | remove the gated call |
| B2 | flag ON, header FP, own row `{hash: None, used: 5}`, device max 3 → `update` with `lifetime_comparisons_used == 5` (max), hash FP | same as B1 | reuse the register block verbatim (writes 3) — hazard H1 |
| B3 | flag ON, header FP, own row hash already `"f"*64` → NO `update` call, status 200 | pin, green today (nothing writes) | drop the NULL check |
| B4 | flag ON, header `"zz" * 32` (64 non-hex) and `"a" * 63` → `get_admin_supabase_client` not called | pin, green today | skip `_DEVICE_FINGERPRINT_RE` on the social path |
| B5 | flag UNSET, header FP → `get_admin_supabase_client.call_count == 0`, `request.headers` never consulted (assert no `users` table access), body == SUCCESS | **byte-identity pin**, green today | drop the flag check |
| B6 | flag ON, header FP, `get_admin_supabase_client` raises → status 200, body == SUCCESS, a WARNING log line contains `device-fp social apply failed` | pin, green today (trivially) | remove the try/except |
| B7 | flag ON, header FP, `sign_in_with_social` returns `{"success": False, "error": "x"}` → 401 and admin client not called | pin, green today | apply before the success check |
| B8 | register regression: `tests/test_auth_routes_invite_fingerprint.py::test_register_with_fingerprint_inherits_lifetime_counter` and `::test_register_without_fingerprint_does_not_update_user` stay green UNCHANGED (they encode the exact chain order and values the extraction must preserve) | existing, green today | change register's `inherited` semantics (e.g. pass a non-zero floor) |

B1/B2 are the unit's red backend tests; B3-B7 are pins with named mutations. Anything that would still pass after `_apply_social_device_fingerprint` is deleted is B3-B7 and is labelled as a pin in its docstring.

## 6. Preserve — behaviours that must stay identical

| behaviour | proof |
|---|---|
| Google body has no `nonce` and is `{provider,id_token}` | `__tests__/services/authService.b4.test.ts` (existing) + C3 |
| Social deadline / `SIGN_IN_TIMEOUT_KEY` / breadcrumb on timeout, google + apple | `__tests__/services/authService.socialTimeout.a8.test.ts` (existing, 24 tests green at base with the b4 + lifetimeLimit suites). Note: under a8's `expo-crypto` factory the REAL `deviceFingerprint` rejects (`randomUUID` undefined) → the new try/catch swallows it → header absent, fetch still called → suite unaffected. The SecureStore mock is promise-only (no timers), so fake timers cannot stall the fingerprint await. |
| `[B4-DIAG]` network / backend-reject / threw-before-fetch captures | a8 "no regression" block + C6 |
| Register still sends `X-Device-Fingerprint` via `api.post(..., { headers })` | **no existing client test asserts this** (`grep X-Device-Fingerprint __tests__` = 0). Add a cheap pin in the new file with `jest.mock('../src/services/api')` (the `authService.m18.test.ts` harness) asserting the third `api.post` argument — green today. |
| Share sheet lifetime gating (copy stays enabled at cap, others disable, banner) | `__tests__/ShareBottomSheet.lifetimeLimit.test.tsx` (existing) |
| Share sheet copy / reward block / i18n keys | `__tests__/ShareBottomSheet.redesign.test.tsx` (source assertions; the import + resolution must not move `share-reward-block` below "Privacy toggles") |
| ResultsScreen still mounts `ShareBottomSheet` with the same five props | `__tests__/ResultsScreen.bundleE.s3.test.tsx:230` + `__tests__/screens/ResultsScreen.test.tsx:142` (source assertions); ResultsScreen is untouched |
| `deviceFingerprint` nonce persistence, cache, single SecureStore read on the success path | `__tests__/deviceFingerprint.test.ts` (existing) |
| Register fingerprint inheritance chain + no-header no-op | B8 |
| Social-login route contract (200 shape, 401 on service failure, 422 on schema) | `tests/test_social_login_smoke.py` (6 tests, existing) — unchanged, and B7 |
| Social-login response body has no new keys in either flag state | B5 + B7 (byte-equality to the mocked payload) |
| `/referrals/share` forwards `device_fingerprint_hash` to `create_invite` and the insert payload carries it | `tests/test_referral_e2e.py::test_e2e_referrer_shares…` sends `CANONICAL_DEVICE_FP` (`:138`) but asserts only `share_target`/`comparison_id` (`:157-159`); `tests/test_referral_share_status_lifetime.py:119` passes it through the service. Optional one-line pin: add `assert call_kwargs["device_fingerprint_hash"] == CANONICAL_DEVICE_FP` — green today. |
| `evaluate_invite` SAME_DEVICE priority | `tests/test_abuse_detection.py::test_same_device_short_circuits`, `::test_priority_order_same_device_first` (existing) |
| Backend bare-console detector on the client auth files | `tests/test_security_regression.py` (in the `SmartCompareApp` scanner set) — the new `__DEV__` warn must be single-line |

## 7. Gates

### Client
1. Red-first: C1, C2, C7 (and C5 if kept) must fail for the reasons in §5 before any edit; C3/C4/C6/C8/C9 must pass before AND after (they are pins) — run each named mutation once and paste the red.
2. Unit files: `__tests__/authService.socialFingerprint.w3-3.test.ts`, `__tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx`, `__tests__/deviceFingerprint.test.ts`.
3. Neighbour suites (grep `__tests__` + `src` for every module touched — `services/authService`, `ShareBottomSheet`, `deviceFingerprint`, `referralService`; measured: 46 + 4 + 4 + 11 test files, **55 suites after dedup** — `grep -rlE "services/authService|ShareBottomSheet|deviceFingerprint|referralService" __tests__ | wc -l` = 55): run them by path, e.g. `node node_modules/jest/bin/jest.js --ci __tests__/services __tests__/authService* __tests__/ShareBottomSheet* __tests__/deviceFingerprint.test.ts __tests__/AuthScreens* __tests__/LoginScreen* __tests__/RegisterScreen* __tests__/HomeScreen* __tests__/ProfileScreen* __tests__/ResultsScreen* __tests__/screens __tests__/api.* __tests__/InviteeQuizScreen* __tests__/ReferralLandingScreen* __tests__/HistoryScreen* __tests__/EditProfileScreen* __tests__/errorCopy.a11.test.ts __tests__/refetchOnFocus.test.ts`. Baseline at base for the three closest: 3 suites / 24 tests green.
4. `node node_modules/typescript/bin/tsc --noEmit` (5.9.3 — print `-v`) exit 0.
5. `node node_modules/eslint/bin/eslint.js src/services/authService.ts src/components/ShareBottomSheet.tsx src/services/deviceFingerprint.ts <new tests>` — base is **0 errors / 7 warnings** on authService.ts and 0 on ShareBottomSheet.tsx; the diff must add no error and no new warning.
6. Full jest suite once in the green phase (baseline 2,729 passed / 278 suites at ece0fbbe; W3-12 reported 281 / 2,752 later — take the number from the run, not from here).

### Backend
1. Red-first: B1, B2 fail as in §3.3; B3-B8 green before and after; each mutation pasted.
2. Unit file: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_social_login_device_fingerprint.py tests/test_auth_routes_invite_fingerprint.py tests/test_social_login_smoke.py -q -p no:randomly -p no:cacheprovider` (base: 32 passed for the last two).
3. `python -m ruff check --select E9,F63,F7,F82 app/api/auth_routes.py` (base: clean) + `python -m py_compile app/api/auth_routes.py`.
4. **Module-reference comm gate** (base `ed75dc70` vs HEAD, same deselect list `_deselect_args.txt` idiom, both sides in one shell): the set is the UNION of
   * `grep -rlE "auth_routes" tests/` → **38 files** (§10; includes `test_b2_strict_optional_auth.py`, `test_auth_refresh_and_revocation.py`, `test_m13_01_slowapi_middleware.py`, `test_security_regression.py`, `test_endpoint_shapes_vs_jsx.py`),
   * `grep -rlE "sign_in_with_social|social-login|social_login" tests/` → `test_auth_interceptor.py`, `test_auth_preferences_completed_warning.py`, `test_personalization.py`, `test_social_login_smoke.py`,
   * `grep -rl "SmartCompareApp" tests/` → **9 files** (CLAUDE.md:714 rule — the client half changes `authService.ts` / `ShareBottomSheet.tsx`, which `test_security_regression.py` and `test_endpoint_shapes_vs_jsx.py` scan),
   * judgement importers of the touched symbols: `test_usage_device_inheritance.py` (documents the register inheritance contract), `test_referral_lifetime_cap.py`, `test_referral_loop2.py`, `test_abuse_detection.py`, `test_abuse_detection_internals.py` (consumers of `device_fingerprint_hash`),
   * the unit file.
   `comm -13` of the sorted FAILED node-id sets ⇒ branch-only-NEW must be empty. Known baseline failures in the set (deselect, do not "fix"): `tests/test_auth_interceptor.py::test_sign_in_with_social_exception`, `::test_social_login_user_insert_fails_gracefully` (`tests/.pre_impl_failures.txt:79-80`).
5. Never `LIVE=1`, never `live_db`/`live_unit`/`integration` markers; `tests/conftest.py` neutralises credentials at module scope.

### Both
Fable review before commit; agents never commit.

## 8. What this unit CANNOT do / Ahmed dependencies / device-only verification

* **Nothing reaches phones until Ahmed's `eas update --branch preview --clear-cache` from a main that includes this unit.** Phones on 97b5f15 keep sending no header and no share hash; the backend half is a no-op for them with the flag ON or OFF.
* **`ENABLE_SOCIAL_DEVICE_FINGERPRINT=true` on Railway `web` is Ahmed's flip** (per-call read, no restart). Sequence: OTA first (so the header exists), then the flag. With the flag ON before the OTA nothing happens; with the OTA before the flag the client half still closes -04 on its own and `X-Device-Fingerprint` is simply ignored by `social_login`.
* **No dependency, secret, store setting, migration or artwork is needed.** `users.device_fingerprint_hash` (021) and `referral_invites.device_fingerprint_hash` (014) are live columns (register and share already write them for email users). Migrations 033-037 remain unapplied and are unrelated.
* **Backfill is opportunistic, not a data migration:** an existing social user gets a hash on their NEXT social login only. Users who never sign in again stay NULL and stay fail-open in `_referrer_device_lifetime_count` / `evaluate_invite`. A one-off backfill is impossible (the fingerprint lives only on the device).
* **Only a device can verify:** that expo-crypto's real `digestStringAsync` output on iOS/Android matches `^[a-f0-9]{64}$` on the CURRENT native build (jest mocks it) — checked indirectly today by the register path writing rows that the regex accepted; that Google/Apple native SDKs still return a token after the extra await (no ordering change before `signIn()`); and that a real SecureStore failure (C5) recovers on the next tap. Post-OTA walkthrough: sign in with Google on a fresh install → Supabase `users` row has a 64-hex `device_fingerprint_hash` (flag ON); share from Results → `referral_invites` row non-NULL (flag-independent).
* **Not fixed here (state in the PR):** the sync supabase client on the event loop in both the register block and the new social block (LS-* class, tracked separately); the missing client test for register's header (added as a pin only); whether re-binding on a second device is desirable (O1).

## 9. PR-body facts

* Closes `MB-NETWORK-CONTRACT-03` and `-04`. Base `ed75dc70`. Mixed: client OTA-safe (unflagged), backend behind `ENABLE_SOCIAL_DEVICE_FINGERPRINT` default OFF, read per call via `os.getenv` (the `strict_optional_auth_enabled` idiom, `auth_routes.py:317-349`).
* Measured at base: `signInWithGoogle` / `signInWithApple` POST with headers `{"Content-Type":"application/json"}` only and never call `getDeviceFingerprint` (0 calls); a share-target tap posts `{comparison_id, share_target, privacy}` with no `device_fingerprint_hash`; `POST /auth/social-login` with a valid header makes 0 admin-client calls (`grep -c device_fingerprint app/services/auth_service.py` = 0); the only writer of `users.device_fingerprint_hash` was `/register` (`auth_routes.py:444-472`).
* Client: the two social fetches now carry `X-Device-Fingerprint` (64-hex, same try/catch tolerance as register `:131-136`; sign-in never blocks on a fingerprint failure); the body is unchanged (`{provider,id_token}` google — B4 no-nonce invariant pinned; `{provider,id_token,nonce}` apple). `ShareBottomSheet.handleTargetPress` resolves the hash itself when the prop is absent (prop still wins); `ResultsScreen.tsx` untouched. -04 closes with the client half alone — the backend already validates (`referral_routes.py:117-119`), forwards (`:209`) and stores (`referral_service.py:322`) the field.
* Client (if C5 kept): `deviceFingerprint.ts` cleared `inflight` only on success, so one transient SecureStore/crypto rejection returned the same rejected promise for the rest of the process (measured: second call rejected, `getItemAsync` called once). Now retried on the next call.
* Backend: `_read_valid_device_fingerprint` + `_inherit_device_counter(…, floor=0)` extracted from the register block with the register path call-for-call identical (`test_register_with_fingerprint_inherits_lifetime_counter` unchanged and green). `social_login`, flag ON and a valid header: reads the caller's own row once; if `device_fingerprint_hash` is NULL, writes the hash and sets `lifetime_comparisons_used = max(own, highest on this device)`; if already set, no write. **The register block was deliberately NOT reused verbatim on the social route: it overwrites the counter with the device maximum computed from OTHER rows, which for a returning social user (own row NULL-hashed, `used=5`) would write 0 — a fresh free quota on every social login.** Pinned by B2.
* Flag OFF or no header or old client: `social_login` runs exactly today's four statements — `request.headers` unread, `get_admin_supabase_client` uncalled (pinned, `call_count == 0`), response body byte-equal (pinned). No new response keys in either state.
* Blast radius with the flag ON: `POST /auth/social-login` only — +1 indexed PK SELECT per social login; +1 SELECT and +1 UPDATE on the first login per user. Nothing else changes.
* Downstream that starts working once BOTH halves are live and the flag is ON: `referral_service._referrer_device_lifetime_count` (LIFETIME_CAP for social referrers, `:773-812`) and `abuse_detection_service.evaluate_invite` SAME_DEVICE (`:240-262`, needs the invitee's users-row hash from this unit's backend half AND the referrer's invite-row hash from this unit's share half). Backfill is per-login; never-returning social users stay NULL and fail open.
* Activation order for Ahmed: `eas update --branch preview --clear-cache` (client half) → `ENABLE_SOCIAL_DEVICE_FINGERPRINT=true` on `web`. Either alone is inert for the backend half; the client half alone closes -04.
* Numbers to fill from the green run: jest suites/tests (baseline 2,729 / 278 at ece0fbbe), pytest counts for the unit file + comm set with branch-only-NEW = ∅ and the two `.pre_impl_failures.txt` social ids deselected, `tsc -v` = 5.9.3, eslint 0 errors, ruff clean. Backend measured on installed fastapi 0.115.0 / starlette 0.38.6 / supabase 2.28.0 vs pins 0.141.1 / 1.6.0 / 2.31.0 — CI runs the pins.
* Line convention: `:NNN` cites the line at `ed75dc70`; `@router` lines cited for routes (`/register` `:408`, `/social-login` `:849`, `/referrals/share` `:176`).

## 10. Measurements run (2026-09-11, worktree `sc-w3-fp`, HEAD `ed75dc70`)

1. `git rev-parse HEAD` → `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git status --short` → empty; `git status --short --ignored | grep qa-w3b` → `!! .qa-w3b/` (`.gitignore:72` `.qa-*/`).
2. `grep -nE "Device-Fingerprint|getDeviceFingerprint|deviceFingerprint|device_fingerprint" -r src __tests__ App.tsx` (SmartCompareApp) → src hits ONLY: `ShareBottomSheet.tsx:43,118,159`, `authService.ts:53,117,133,148`, `deviceFingerprint.ts:1,17`, `referralService.ts:36`, `appVersionService.ts:35` (comment); `__tests__` hits: a3/w1-4/m18 mock `getDeviceFingerprint`, `deviceFingerprint.test.ts`. **Zero `X-Device-Fingerprint` in `__tests__`.**
3. `sed -n 640,900p src/services/authService.ts` → `signInWithGoogle` `:665`, body `:718`, fetch `:728-736` (headers `:732`), `signInWithApple` `:814`, fetch `:863-875` (headers `:867`); `getGoogleSignin/getAppleAuth/getCrypto` lazy `require`s `:20-51`; `import { getDeviceFingerprint }` `:53`.
4. `grep -n "ShareBottomSheet|createShare|deviceFingerprint" src/screens/ResultsScreen.tsx` → mount `:830-841` (props `visible, comparison, onClose, onShared, lifetimeRemaining`), **0 `deviceFingerprint` hits**. `grep -rlE ShareBottomSheet __tests__ src` → 4 tests + `ShareBottomSheet.tsx`, `ResultsContent.tsx`, `ResultsScreen.tsx`, `deriveTone.ts`.
5. `grep -n "device_fingerprint|_DEVICE_FINGERPRINT_RE|X-Device-Fingerprint" app/api/auth_routes.py …` → `auth_routes.py:18-23` (regex), `:421`, `:444-472` (register block), **nothing else in auth_routes**; `referral_routes.py:117,209`; `referral_service.py:247,322,680,728,776-802`; `abuse_detection_service.py:132-150,249`. `grep -c device_fingerprint app/services/auth_service.py` → **0**.
6. `sed -n 845,860p app/api/auth_routes.py` → `social_login` `:849-856` quoted in §3.3; `sed -n 540,625p app/services/auth_service.py` → `sign_in_with_social` `:551-617`, users insert `:580-586` (`id,email,auth_provider,subscription_tier`).
7. `sed -n 317,349p app/api/auth_routes.py` → `strict_optional_auth_enabled` flag idiom (truthy set `"true","1","yes","on"`, per-call `os.getenv`).
8. `cat migrations/021_device_fingerprint_users.sql` → `ALTER TABLE users ADD COLUMN IF NOT EXISTS device_fingerprint_hash TEXT` + partial index; `migrations/011:29` → `lifetime_comparisons_used INT DEFAULT 0`; `ls migrations | tail` → 037 is the last (038 would be next; none needed).
9. `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`; `node -e` versions → jest 29.7.0, ts-jest 29.4.9, expo-crypto 15.0.9, expo-application 7.0.8; package.json pins `typescript ~5.9.2`, `jest ^29.7.0`, `ts-jest ^29.4.6`, `expo-crypto ~15.0.8`, `expo-application ~7.0.8`.
10. `python --version` → 3.12.9; `python -m ruff --version` → 0.16.5; installed fastapi 0.115.0 / starlette 0.38.6 / supabase 2.28.0 / pydantic 2.7.0; `requirements.txt` fastapi==0.141.1 (`:47`), starlette==1.6.0 (`:150`), supabase==2.31.0 (`:156`), pydantic==2.13.4 (`:109`), httpx==0.28.1 (`:66`).
11. `node node_modules/jest/bin/jest.js --ci __tests__/services/authService.b4.test.ts __tests__/services/authService.socialTimeout.a8.test.ts __tests__/ShareBottomSheet.lifetimeLimit.test.tsx` → `Test Suites: 3 passed, Tests: 24 passed` (4.2 s).
12. `PYTHONIOENCODING=utf-8 python -m pytest tests/test_auth_routes_invite_fingerprint.py tests/test_social_login_smoke.py -q -p no:randomly -p no:cacheprovider` → `32 passed, 11 warnings in 5.52s`.
13. `node node_modules/eslint/bin/eslint.js src/services/authService.ts src/components/ShareBottomSheet.tsx src/screens/ResultsScreen.tsx` → `0 errors, 67 warnings` (authService.ts 7 warnings: 3× `no-require-imports` `:23,34,45`, 2× `import/first` `:52,53`, `import/no-named-as-default` `:52`, unused `e` `:262`; ShareBottomSheet.tsx 0; ResultsScreen.tsx 60 pre-existing).
14. `python -m ruff check --select E9,F63,F7,F82 app/api/auth_routes.py` → `All checks passed!`.
15. Probe harness: `.qa-w3b/probes/jest.probe.config.js` = `SmartCompareApp/jest.config.js` spread with `rootDir: SmartCompareApp`, `roots: [SmartCompareApp, probes dir]`, `testMatch: **/.qa-w3b/probes/**/*.probe.test.ts(x)`, `modulePaths: [SmartCompareApp/node_modules]` (needed because the probe dir is outside the app — first run failed with `Cannot find module 'react'`). Invoked from SmartCompareApp as `node node_modules/jest/bin/jest.js --ci --config ../.qa-w3b/probes/jest.probe.config.js <probe>`.
16. `socialFingerprintHeader.probe.test.ts` → output in §3.1 (2 failed / 2; `getDeviceFingerprint calls = 0` both paths).
17. `sharePayloadFingerprint.probe.test.tsx` → output in §3.2 (1 failed / 1; payload has no hash; `getDeviceFingerprint calls = 0`).
18. `fingerprintInflightPoison.probe.test.ts` → `[PROBE inflight] second call REJECTED with: keychain busy getItemAsync calls = 1` (1 failed / 1).
19. `PYTHONIOENCODING=utf-8 python -m pytest .qa-w3b/probes/probe_social_fp.py -q -s -p no:randomly -p no:cacheprovider` → `[PROBE social-login] status=200 sign_in_with_social awaited=1 get_admin_supabase_client calls=0 tables=[] update_called=False update_args=None` → `AssertionError: social-login never wrote device_fingerprint_hash` (1 failed).
20. Comm-set greps (backend): `grep -rlE "auth_routes" tests/` → 38 files (`test_429_contract, test_account_deletion, test_attribution_endpoint, test_attribution_service, test_attribution_service_edges, test_auth_ai_sharing_toggle, test_auth_demographics, test_auth_interceptor, test_auth_refresh_and_revocation, test_auth_routes_invite_fingerprint, test_b2_strict_optional_auth, test_budget_value_literal, test_bundle_c_feature_flag, test_cohort_profile_governorate, test_cohort_summary_orchestrator, test_endpoint_shapes_vs_jsx, test_error_middleware, test_history_routes, test_home_routes, test_invitee_quiz, test_m13_01_slowapi_middleware, test_paid_route_metering, test_personalization, test_profile_routes, test_push_token_endpoint, test_referral_e2e, test_referral_feature_flag, test_referral_must_fixes, test_referral_routes, test_referral_share_privacy, test_register_invite_linking, test_security_regression, test_share_routes, test_social_login_smoke, test_supabase_client_reuse, test_tier_detection, test_usage_device_inheritance` + `integration/bundle-e-smoke.sh` (shell, not pytest)); `grep -rlE "sign_in_with_social|social-login|social_login" tests/` → `test_auth_interceptor, test_auth_preferences_completed_warning, test_personalization, test_social_login_smoke` (+ 2 baseline docs, 2 fixtures); `grep -rl "SmartCompareApp" tests/` → `test_b2_strict_optional_auth, test_events_allowlist_superset, test_feature_bucket_parity, test_feedback_allowlist_superset, test_migration_037_security_definer_grants, test_paid_route_metering, test_review_paraphrase, test_security_regression, test_timeout_partial_integration`. App importers of `auth_routes` (17 files incl. every route module and `rate_limiter.py`) — no signature of an imported symbol changes, so no importer needs editing.
21. Comm-set greps (client, `SmartCompareApp/__tests__`): `services/authService` → 46 test files (+ 8 screens in `src`); `ShareBottomSheet` → 4; `deviceFingerprint` → 4; `referralService` → 11; union `grep -rlE "services/authService|ShareBottomSheet|deviceFingerprint|referralService" __tests__ | wc -l` → **55 suites**. Reproduce with those greps; the green phase pastes the file list it ran.
22. Baseline failures to deselect: `tests/.pre_impl_failures.txt:79-80` = `test_auth_interceptor.py::test_sign_in_with_social_exception`, `::test_social_login_user_insert_fails_gracefully` (also in `_deselect_args.txt` of the W1-5 unit).
23. `tests/test_referral_e2e.py:130-159` → share e2e sends `CANONICAL_DEVICE_FP` but asserts only `share_target` + `comparison_id` on `create_invite`; `tests/test_abuse_detection.py:241-254` → SAME_DEVICE short-circuit pinned; `referral_routes.py:176` `@router.post("/share", status_code=201)`, `:209` `device_fingerprint_hash=body.device_fingerprint_hash`; `referral_service.py:242` `create_invite`, `:322` insert payload.
24. `__mocks__/expo-secure-store.ts` → promise-only in-memory store (no timers); `__mocks__/expo-crypto.ts` → `randomUUID` only (no `digestStringAsync`); `__mocks__/react-native.ts:128` exports `Linking` (`canOpenURL` → false by design), no `Share` export.

## Open questions for the reviewer (do not block the red phase)

* **O1 — re-bind on a second device?** Design writes the hash only when the row's hash is NULL (first-device binding, mirrors register). Alternative: always overwrite with the latest device (tracks the current phone, loses the first-device lock). Default = NULL-only; say so in the flag row.
* **O2 — keep C5 (`inflight` poisoning fix)?** Real, measured, 3 lines, in a file the unit already touches conceptually; cut it if the reviewer wants the diff to be strictly the two findings, and then state the permanent-on-first-failure limitation in the PR.
* **O3 — `max(own, device)` vs register's overwrite for NEW social users:** identical for a new row (own=0). The only divergence is the returning-user backfill, which is the point (H1).

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS.** Every anchor, probe output, version and count in §1-§10 was re-measured at `ed75dc708b82c0b911c9de8a3e59d4418c6e278c` (`git status --short` empty before and after; `.qa-w3b/` is `!!` ignored via `.gitignore:72`). All four writer probes reproduce byte-for-byte (§3.1 / §3.2 / §3.3 / §3.4 outputs identical on re-run). The rulings below correct the defects found; the red phase executes §4-§7 **as amended here**. Where a ruling and the body disagree, the ruling wins.

**R1 — C5 is KEPT (O2 decided), but its assertion as written can never go green in the file the spec puts it in.** `__tests__/deviceFingerprint.test.ts:26-30` mocks `expo-crypto` with `digestStringAsync: async (_alg, raw) => \`hash(${raw})\``, so the second call resolves to `hash(app.qaren.test|iPhone15,2/21D|nonce-ok)`, NOT a 64-hex string; the writer's probe used the default `__mocks__/expo-crypto` (no `digestStringAsync` at all — `Crypto.CryptoDigestAlgorithm` is undefined), under which the second call rejects with `Cannot read properties of undefined (reading 'SHA256')` even after the fix. Binding shape for C5 (in `__tests__/deviceFingerprint.test.ts`, that file's mocks unchanged): `getItemAsync.mockRejectedValueOnce(err).mockResolvedValue('nonce-ok')`; `await expect(getDeviceFingerprint()).rejects.toBe(err)`; `await expect(getDeviceFingerprint()).resolves.toBe('hash(app.qaren.test|iPhone15,2/21D|nonce-ok)')`; `expect(SecureStore.getItemAsync).toHaveBeenCalledTimes(2)`; `expect(SecureStore.setItemAsync).not.toHaveBeenCalled()`. RED today for the reason in §3.4 (second call rejects with the FIRST error, `getItemAsync` called once). Fix form is fixed: `inflight = (async () => { … })().catch((e) => { inflight = null; throw e; });` — not `finally` (a `finally` re-nulls on the success path after the IIFE already did; harmless but two writers of the same variable is the kind of thing the next reader "simplifies"). The 5 existing cases in that file stay byte-identical. Why keep it: the two new call sites make one transient keychain error a permanent no-fingerprint-for-the-process on EVERY social login and share, i.e. C5's blast radius is created by this unit. PR body names it as a third, measured defect.

**R2 — Measured side-effect the spec did not record: under the default `__mocks__` (the b4 harness, `jest.config.js` `moduleNameMapper` → `__mocks__/expo-crypto.ts` which HAS `randomUUID` but NO `digestStringAsync`), the REAL `deviceFingerprint` persists the nonce BEFORE it throws.** Review probe `.qa-w3b/probes/b4HarnessFingerprintSideEffect.review.probe.test.ts`: `first rejected = Cannot read properties of undefined (reading 'SHA256') | setItemAsync keys after first = ["device_fp_nonce"] getItemAsync calls = 1 | second rejected = (same) | setItemAsync keys after second = ["device_fp_nonce"] getItemAsync calls = 1`; third call after `_resetCacheForTests` with the nonce already in the in-memory store: `setItemAsync keys = []`. Consequence after the fix: in `__tests__/services/authService.b4.test.ts` the FIRST test that drives `signInWithGoogle` records one extra `saveTokenSpy` call (`'device_fp_nonce'`); the suite's `expect(saveTokenSpy).not.toHaveBeenCalled()` (the "does NOT save token on backend error response" case) survives ONLY because it runs later, after the nonce is persisted (and, without C5, because `inflight` is poisoned). a8 is unaffected for a different reason: its `expo-crypto` factory has no `randomUUID`, so the real module throws BEFORE `setItemAsync`. Rulings: (a) do NOT edit b4 or a8; (b) the green phase runs b4 + a8 + lifetimeLimit by path and pastes the result (base: 3 suites / 24 tests); (c) the new w3-3 suites MUST mock `deviceFingerprint` exactly as §5 says — never rely on the real module under the default mocks; (d) if b4 reddens on `saveTokenSpy`, that is THIS coupling, not a product bug — stop and report, do not "fix" b4.

**R3 — Backend harness for B1-B7 is under-specified; binding call sequence.** With flag ON + valid header, `_apply_social_device_fingerprint` makes exactly THREE `admin.table("users")` calls in this order: (1) own-row `select("device_fingerprint_hash, lifetime_comparisons_used").eq("id", uid).limit(1).execute()` (no `.single()`; `row = (own.data or [{}])[0]`), (2) device-max `select("lifetime_comparisons_used").eq("device_fingerprint_hash", fp).order("lifetime_comparisons_used", desc=True).limit(1).execute()`, (3) `update({"device_fingerprint_hash": fp, "lifetime_comparisons_used": N}).eq("id", uid).execute()`. With the own-row hash already set: exactly ONE `table()` call and `update` never invoked — B3 asserts `admin.table.call_count == 1` AND no chain's `update` called. Build the harness with `admin.table.side_effect` popping SEPARATE `MagicMock` chains from a list in that order (the `test_auth_routes_invite_fingerprint.py:170-215` single-shared-chain idiom cannot distinguish the two selects' `eq` calls); assert the update payload via a recording `update(data)` and `update_chain.eq.assert_called_once_with("id", uid)`. The new file is NOT in `tests/conftest.py::_RATE_LIMITER_BYPASS_TEST_FILES` (`:48-56`), so it MUST carry its own autouse `limiter.enabled = False` fixture (copy `tests/test_social_login_smoke.py:23-30`). `user_id` comes from `(result.get("user") or {}).get("id")` — verified that `sign_in_with_social` (`auth_service.py:551-617`) and `_enrich_response_with_profile` (`:206-224`) keep `user.id`; `social_login` has no `response_model`, so the dict is returned verbatim in both flag states.

**R4 — `tests/_deselect_args.txt` does NOT exist in this worktree** (`ls` fails; the only reference to that name anywhere is this spec). §7 Backend gate 4 is amended: the green phase builds the deselect list itself from the node ids in `tests/.pre_impl_failures.txt` (header `:1-12` documents the format) intersected with the comm set — at minimum `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully` (`:79-80`, re-read) — and pastes the exact `--deselect` arguments it used. Comm-set counts: quote the LIST, not the number — `grep -rlE "auth_routes" tests/` is 40 unfiltered (38 `.py` + `integration/bundle-e-smoke.sh` + one non-py file); `--include=*.py` social grep = 4 (`test_auth_interceptor, test_auth_preferences_completed_warning, test_personalization, test_social_login_smoke`, matches); `grep -rl "SmartCompareApp" tests/ --include=*.py` = 9 (matches). Doc correction: §7 Backend 4 says `test_endpoint_shapes_vs_jsx.py` "scans SmartCompareApp" — it does not (zero `SmartCompareApp`/`.ts` references in that file); it is in the set via the `auth_routes` grep anyway.

**R5 — B5/B6/B7 precision.** B5: parametrize over flag UNSET (`monkeypatch.delenv("ENABLE_SOCIAL_DEVICE_FINGERPRINT", raising=False)`, the `tests/test_b2_strict_optional_auth.py:59` idiom) AND `"false"`; operationalize "request.headers never consulted" as `get_admin_supabase_client.call_count == 0` plus `resp.json() == SUCCESS` (a header read is not observable through TestClient; the admin-call count is the real invariant). B6: use `caplog` at WARNING on logger `app.api.auth_routes` (`logger = logging.getLogger(__name__)` at `:57`; precedent `tests/test_auth_refresh_and_revocation.py` already asserts these loggers via caplog, so propagation works) and assert the record message contains `device-fp social apply failed`. B7: also assert `get_admin_supabase_client.call_count == 0` when `sign_in_with_social` returns `success: False` — the apply call must sit AFTER the `raise HTTPException(401)`.

**R6 — Path hygiene for the new client suites.** Both new files live at `__tests__/` ROOT, while the a8 harness they copy lives in `__tests__/services/`: every `'../../src/...'` in the copied mocks becomes `'../src/...'` (`jest.mock('../src/services/deviceFingerprint', …)`, `require('../src/services/authService')`). A wrong path silently mocks nothing and C1/C2 would then read the real module (R2). The Sentry factory must export `captureMessage` + `addBreadcrumb` (b4 comment `:72-76`); the `expo-haptics` mock for C7-C9 should carry `NotificationFeedbackType: { Success, Error }` (the writer's share probe form; `lifetimeLimit`'s lacks `Error` — harmless under the try/catch but include it). `Share` is NOT exported by `__mocks__/react-native.ts` (verified: only `Linking` `:128`, `canOpenURL` → false) — the TypeError is swallowed by the sheet's inner try and `onShared` still fires; assert on `createShare`'s argument only. `__tests__/setup.ts:11` sets `__DEV__ = false` and no-ops `console.warn` — never assert on the new warn.

**R7 — O1 decided: NULL-only first-device binding is BINDING.** Always-overwrite would let a referrer (or a delete-and-re-signup farm) move its hash off a saturated device by reinstalling (the nonce resets on uninstall, `deviceFingerprint.ts:3`), defeating both `_referrer_device_lifetime_count` (`referral_service.py:772-812`) and `evaluate_invite` SAME_DEVICE. The CLAUDE.md flag row states: "writes `users.device_fingerprint_hash` only when NULL (first-device binding, mirrors `/register`); a second device never re-binds".

**R8 — O3 confirmed: `max(own, device-max)` + NULL-only write is CORRECT and the plan's verbatim extraction is WRONG (H1 verified by reading).** `auth_routes.py:453-471`: the device SELECT is `.eq("device_fingerprint_hash", fp)`; the caller's own row has hash NULL (every social user on main) so it can never match; `inherited` is the OTHER rows' max or `0`; the UPDATE then overwrites `lifetime_comparisons_used` with it. Verbatim reuse on `/social-login` = `used 5 → 0` for every returning social user with no sibling row. B2 (own 5, device 3 → writes 5) is the correct pin and its mutation ("reuse the register block verbatim") is real. The register path keeps `floor=0` ⇒ `max(0, prior)` = today's value (prior is `... or 0`, never negative); B8 stays green unchanged.

**R9 — Scope: `MB-NETWORK-CONTRACT-09` is OUT.** The verifier's U6 (`full-review-verified.json:1735-1737`) bundles -03/-04 with -09 and lists `app/services/auth_service.py`; the unit brief gives -03/-04 only. -09 is P2, anchored on `api.ts:216` (camera identify never sends the header; anon gate extension) and is a precondition of `#128` — a different behaviour change with its own flag. Do not touch `api.ts`; `auth_service.py` stays untouched as §4.3 says. Scope verdict on the rest of §2: honest — -04 is NOT closed (payload re-measured without hash; `ResultsScreen.tsx:830-841` passes no prop; 0 `deviceFingerprint` hits), -04's backend half IS green (`referral_routes.py:117-119/:176/:209`, `referral_service.py:242/:322` re-read), the SAME_DEVICE test would be decoration (`test_abuse_detection.py:241-254` re-read), and nothing red was dropped. All plan anchors re-confirmed at ed75dc70 exactly as §2 lists them.

**R10 — Toolchain/installed-version facts confirmed on disk; nothing in the unit is version-shaped.** `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3` (package.json `~5.9.2`); jest 29.7.0, ts-jest 29.4.9, expo-crypto 15.0.9 (`~15.0.8`), expo-application 7.0.8, expo-secure-store 15.0.8, expo-device 8.0.10, RN 0.81.5. `node_modules/expo-crypto/build/Crypto.js:113` — `digestStringAsync(algorithm, data, options = { encoding: CryptoEncoding.HEX })`, `Crypto.types.js:43` `HEX = "hex"`: the default really is hex (case is native-side; the device walkthrough in §8 stays the only proof of lowercase, exactly as the spec says). Python 3.12.9, ruff 0.16.5; installed fastapi 0.115.0 / starlette 0.38.6 / supabase 2.28.0 / pydantic 2.7.0 vs `requirements.txt` pins `:47` 0.141.1 / `:150` 1.6.0 / `:156` 2.31.0 / `:109` 2.13.4 — the green phase states which versions its pytest numbers came from; CI settles it on the pins.

**R11 — Console detector rule, verified.** `tests/test_security_regression.py:508-517`: a line is a violation iff `stripped.startswith("console.") and "__DEV__" not in line`. A single-line `if (__DEV__) console.warn(...)` starts with `if` and passes; a multi-line block puts `console.warn(` on its own line and FAILS. The new warn in `authService.ts` is one line. `ShareBottomSheet.tsx` gets no console call.

**R12 — CORS is not a blocker and is out of scope.** `app/main.py:118` `allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"]` lacks `X-Device-Fingerprint`; RN's native fetch enforces no CORS preflight and `/register` already ships the same header from the same app (prod `users` rows carry regex-accepted hashes). Do not touch `main.py`.

**R13 — Header literal form is fixed.** Use the object-literal spread in §4.1 (`headers: { 'Content-Type': 'application/json', ...(fingerprint ? { 'X-Device-Fingerprint': fingerprint } : {}) }`); never a `Headers` instance — a8 and C1/C2 index `mockFetch.mock.calls[0][1].headers['X-Device-Fingerprint']` and `.signal` on the init object.

**R14 — Red/decoration audit passed.** Red tests: C1, C2, C7 (client), C5 (client, amended per R1), B1, B2 (backend) — each measured red today for the stated reason and each carries a named mutation that re-reddens it after the fix. Pins C3/C4/C6/C8/C9/B3-B8 are labelled as pins with named mutations. No tautology: C1/C7 assert plumbing of a mocked value, B1 asserts the device-max reaching the UPDATE, B2 asserts the monotone semantics. Both new client suites have no exact-payload collision with existing suites (0 `createShare … toHaveBeenCalledWith` exact-payload assertions in `__tests__`; `ShareBottomSheet.redesign.test.tsx:39-40` is a SOURCE-order pin `share-reward-block` < "Privacy toggles", unaffected by an import + an in-tap block above `:225`).

**R15 — Ahmed dependencies confirmed, none hidden.** No package, secret, migration apply, native rebuild or store setting: `users.device_fingerprint_hash` (021) and `referral_invites.device_fingerprint_hash` (014) exist (`grep -l device_fingerprint migrations/*.sql`); 037 is the last file, 033-037 unapplied and unrelated. Activation order stands: `eas update --branch preview --clear-cache` from a main containing this unit → `ENABLE_SOCIAL_DEVICE_FINGERPRINT=true` on `web`. Phones on 97b5f15 send neither header nor share hash, so the backend half is inert for them in both flag states — old-client compatibility holds.

**R16 — Hygiene reminders that bind the green phase.** `ResultsScreen.tsx`, `auth_service.py`, `referral_*`, `abuse_detection_service.py`, `referralService.ts`, `api.ts`, `main.py`, `package.json`, `app.json` untouched. eslint base on the three client files: 0 errors / 7 warnings (`authService.ts` 7, `ShareBottomSheet.tsx` 0, `deviceFingerprint.ts` 0) — no new error or warning; the new `ShareBottomSheet` import sits with the existing imports (`:14-31`) so `import/first` stays clean. ruff `E9,F63,F7,F82` on `auth_routes.py` base: clean. Run the 55-suite client union by the greps in §10.21 and paste the file list; full jest once in the green phase. Agents never commit.

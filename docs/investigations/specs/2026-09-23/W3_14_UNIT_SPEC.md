# W3-14 — error copy the user can act on

## 1. Header

Unit **W3-14**. Findings `MB-NETWORK-CONTRACT-05`, `MB-NETWORK-CONTRACT-06`, `MB-RECONCILE-18(12)`.
Base: origin/main **`ed75dc708b82c0b911c9de8a3e59d4418c6e278c`** (worktree `sc-w3-copy`; every
file:line below was re-located and quoted at this SHA on 2026-09-11; `git status --short` empty
before and after every measurement).

OTA class: **mixed**.
* Client half — **OTA-safe** (TypeScript + the two flat JSON catalogs; no `app.json`, no
  plugin, no native dep). Reaches phones only with Ahmed's `eas update --branch preview --clear-cache`.
* Backend half — **backend-only, additive, UNFLAGGED**: ONE new route
  (`PUT /api/v1/auth/preference-toggles`) and nothing else on the wire changes. No migration,
  no secret, no env var. Rationale for "no `ENABLE_*` flag" in §4 (a default-OFF flag would
  404/503 the OTA'd client's privacy toggle until Ahmed flips it — strictly worse than the
  additive-route precedent `228ff63`, which is an ancestor of HEAD).

Toolchain measured here (installed / pin): TypeScript `5.9.3` / `~5.9.2`
(`node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`), jest `29.7.0` / `^29.7.0`,
axios `1.20.0` / `^1.20.0`, react-native `0.81.5` / `0.81.5`, RNTL `13.3.3` / `^13.3.3`,
i18next `26.1.0` / `^26.0.1`, react-i18next `17.0.7` / `^17.0.1`, intl-pluralrules `2.0.1` /
`^2.0.1`, eslint `9.39.4` / `^9.39.4`, expo `54.0.34` / `~54.0.33`. Backend: Python `3.12.9`;
**local-vs-lock drift** — fastapi `0.115.0` installed vs `0.141.1` pinned (`requirements.txt:47`),
pydantic `2.7.0` vs `2.13.4` (`:109`), slowapi `0.1.9` vs `0.1.10` (`:144`), starlette `0.38.6`
vs `1.6.0` (`:150`). Every backend number below was measured on the INSTALLED versions; CI
settles the pinned ones. `pydantic.model_validator` imports on 2.7.0 (measured) and exists on
2.13.4; **it is NOT currently imported in `auth_routes.py`** (`:9` imports only
`BaseModel, EmailStr, Field, field_validator`) — the implementer adds it.

---

## 2. Scope correction — what is ALREADY on main

The plan row (`docs/investigations/2026-09-06-full-review.md:141`) lists two red tests and names
"the five screens + `src/utils/failureClassification.ts`". The verifier rows
(`-verified.json`, ids above) name the five screens as Home / History / Profile / EditProfile /
Results and the raw sites as `ProfileScreen :160/:183/:225/:298`. Measured at `ed75dc70`:

| plan item | status | evidence at ed75dc70 |
|---|---|---|
| (a) HomeScreen text path: synthetic `429 {code:'RATE_LIMITED'}` renders `t('home.errors.rateLimited')`, never "Rate limit exceeded" | **ALREADY GREEN — dropped** | A11 (`74d041cb`, ancestor of HEAD): `HomeScreen.tsx:482` `Alert.alert(t('common.error'), t(friendlyErrorKey(parsed.code)));` inside the SSE/REST `onError` handler `:436-483`; `errorCopy.ts:39-43` `case 'RATE_LIMITED': … return 'home.errors.rateLimited'`; `en.json:119` / `ar.json:116` carry the key. Probe: `friendlyErrorKey(parseApiError(slowapi429).code) = home.errors.rateLimited`. Pinned at runtime by `__tests__/HomeScreen.errorCopy.a11.test.tsx:304-322` (asserts the Alert body `=== EN['home.errors.rateLimited']`) and by `__tests__/errorCopy.a11.test.ts:153-168`. The plan's "RED: zero `RATE_LIMITED` references in the client" is stale — grep finds `errorCopy.ts:39/43`, `HomeScreen.tsx:479` (comment) and the two a11 pins. |
| (a) HomeScreen URL path | **ALREADY GREEN — dropped** | `HomeScreen.tsx:573` same coded call; `__tests__/ResultsScreen.networkMatrix.m18.test.ts:100-106` requires exactly 2 matches of `Alert.alert(t('common.error'), t(friendlyErrorKey(parsed.code)))` and `:108+` extracts every `Alert.alert(` by balancing parens and forbids `parsed.message` / `error.message`. |
| (a) `HistoryScreen.loadHistory` renders the raw string | **ALREADY GREEN — dropped** | `HistoryScreen.tsx:698-709`: `catch (error) { … if (status === 401) {…} else { … setLoadError(true); } }` — every non-401 failure (a 429 included) lands on the retryable state, rendered at `:909-910` as `t('history.loadError.title')` / `t('history.loadError.body')` ("The connection paused — give it another tap."). A12. Pinned by `__tests__/HistoryScreen.searchState.a12.test.tsx:182-201` (rejected load → `history-load-error` testID, retry re-fetches). The pin rejects with `ERR_NETWORK`, not a 429, but the branch is status-agnostic, so a 429 pin would be decoration. |
| "the plan says `src/utils/failureClassification.ts`" | **anchor moved** | the file is `src/services/failureClassification.ts` (57 lines; no `src/utils/failureClassification.ts` exists). |
| (a) `classifyLoadFailure` maps 429 → busy/timeout | **RED — kept** | probe: `classifyLoadFailure(429 RATE_LIMITED) = generic`, `classifyLoadFailure(429 no code) = generic`. §3b. Two consumers: `ResultsScreen.tsx:237-248` (history load) and `:328-329` (camera path). |
| (a) Profile / EditProfile / Results(demographics) render `parseApiError().message` raw | **RED — kept** | measured renders in §3c. |
| (a) client reads `retry_after_seconds` (W1-9 #152 `a4e7b08b`, ancestor of HEAD) | **RED — kept** | probe: `Object.keys(parseApiError(slowapi429)) = ['message','code']`. `grep -rn "retry_after\|Retry-After\|retryAfter" src __tests__` → zero hits. The text path is REST under the shipped default (`features.ts:52` `ENABLE_EXPO_FETCH_SSE_DEFAULT = false`; `api.ts:637` `if (!features.ENABLE_EXPO_FETCH_SSE)` → `runRestCompare` → `api.get('/api/v1/text/compare')`), so a 429 reaches `onError` as a real axios error whose `response.data` carries the field; the interceptor lets a non-USAGE_LIMIT 429 through (`api.ts:198-201`; pinned `__tests__/api.refreshInterceptor.test.ts:194-202`). The field is on the wire and dropped on the floor. |
| (b) "Profile with `getPreferences → null` + AI-sharing switch issues no `priorities:[]` PUT / no raw Pydantic string" | **ALREADY GREEN as worded — but the DEFECT is not fixed; re-scoped** | F-S1.5i gating at `ProfileScreen.tsx:249-250` disables the switch: probe b1 → AI row `accessibilityState {"checked":false,"disabled":true}`; `savePreferences` calls after pressing the row AND after `Switch.onValueChange(true)` = **0**; caption "Pick your priorities first" rendered ×1. So no PUT and no Pydantic string. **But the finding's impact — "a privacy control the user cannot exercise" — is exactly what the gate now does deliberately** (and `getPreferences` returns `null` on ANY thrown error, `api.ts:472-474`, so one failed GET gates a user WHO HAS priorities too). The unit's (b) becomes: let a user WITHOUT priorities flip AI-sharing / notifications, and never render a raw string when it fails. §3d, §4. |
| The brief's anchor "`api.ts:1266` returns `{priorities: [], empty_state: true}`" | **anchor is a different function** | `api.ts:1261-1269` is `getProfilePrioritiesWeighted`'s catch (the weighted-bars read for `PrioritiesInline`), not `getPreferences` (`:455-475`). `EditPreferencesFlow.tsx:36-41` `DEFAULT_PREFS` seeds `priorities: []` as the brief says; that flow still requires ≥1 priority client-side and is untouched here. |
| MB-RECONCILE-18 item 12 "pass tier/remaining through the unified envelope" | **DROPPED — no consumer** | backend drop is real: `text_routes.py:244-252` raises `detail={"error":…,"code":"USAGE_LIMIT","tier":…,"remaining":…}` (same at `:411-412`, `:562-563`, `:780-781`) and `error_handler.py::http_exception_handler` (`:112-145`) emits only `success/error/code/request_id` (+ `retry_after_seconds` on a 429 whose detail carries `retry_after`) — probe B4 output has neither `tier` nor `remaining`. But the ONLY client consumer, `PaywallScreen.tsx:224-233`, reads `initialUsage` for truthiness alone (`const [, setUsage] = useState…` — the state is never read; `initialUsage` only skips `getUsageStatus()`), and `getUsageLimitDetail` (`usageService.ts:71-74`) returns the whole payload. Passing them through is a backend change with no observable effect — decoration under this unit's own rule. Open question §8. |

Line anchors in the finding texts (taken at 76ace90) that moved: `HomeScreen.tsx:470` → the
`onError` handler is `:436-483`, its coded alert `:482`; `HomeScreen.tsx:394-399` ("the pattern
already used for text") → `:429-433` — that is the SSE `onComplete` `!data.success` ternary
(`isTimeout ? t('home.errors.timeout') : data.error || t('home.errors.comparison')`), NOT the A11
map; see §8 for why it is out of scope. `ProfileScreen.tsx:134` → still `:134`
(`priorities: previous?.priorities ?? [],`); the raw renders are at `:156/:160/:179/:183/:219/:225-227/:298`
as the finding says. `auth_routes.py` `UserPreferencesRequest` → `:183-184`.

---

## 3. The defect — measured

### 3a. `retry_after_seconds` is emitted on both 429 classes and never read

Backend, `app/middleware/error_handler.py`:
```
64	    if retry_after_seconds is not None:
65	        content["retry_after_seconds"] = retry_after_seconds
66	        headers = {"Retry-After": str(retry_after_seconds)}
…
130	    # W1-9 (ruling 4): a 429 whose structured detail carries a usable
131	    # retry_after gets the same additive header + field as the slowapi path.
132	    retry_after = _detail_retry_after(detail) if exc.status_code == 429 else None
```
`_detail_retry_after` (`:105-110`) accepts only a positive non-bool `int`. The lockout side:
`auth_routes.py:763-782` `_account_locked_response` raises
`detail={"error": "Account temporarily locked…", "code": "ACCOUNT_LOCKED", "retry_after": retry_after}`;
called from `PUT /password` at `:832-833`. `tests/test_429_contract.py` → **17 passed** at HEAD.

Client, `src/services/api.ts:923-979`, returns only `{ message, code }`:
```
923	export function parseApiError(error: any): { message: string; code: string | null } {
…
966	  if (data?.error) {
967	    return { message: data.error, code: rawCode };
```
Probe (`.qa-w3b/probes/w314_measure.test.tsx`, real modules):
```
PROBE parseApiError(slowapi 429) = {"message":"Rate limit exceeded. Please try again later.","code":"RATE_LIMITED"}
PROBE parseApiError(ACCOUNT_LOCKED 429) = {"message":"Too many failed attempts. Try again in 15 minutes.","code":"ACCOUNT_LOCKED"}
PROBE friendlyErrorKey(ACCOUNT_LOCKED) = home.errors.comparison
PROBE parsed has retry_after_seconds? keys = [ 'message', 'code' ]
```

### 3b. Results history-load (and camera load): a 429 lands on the permanent "No comparison loaded"

`src/services/failureClassification.ts:42-57` has no 429 branch; `:56 return 'generic'`.
`ResultsScreen.tsx:237-248`: `generic` → `setLoadError('generic')` → `:703-728` renders
`t('results.emptyState.title')` = "No comparison loaded" with CTA `t('results.emptyState.cta')`
= "Back to history" and NO retry (`isTimeout` false). Second consumer `:328-329`
`setLoadError(kind === 'timeout' ? 'timeout' : 'generic')`. `GET /api/v1/comparisons/{id}` is
`20/minute` (W1-5 blast-radius table). Probe:
```
PROBE classifyLoadFailure(429 RATE_LIMITED) = generic
PROBE classifyLoadFailure(429 no code) = generic
PROBE en[results.emptyState.title] = No comparison loaded
```

### 3c. Profile, EditProfile, Results-demographics render raw backend / axios strings

`ProfileScreen.tsx`:
```
156	        setAiSharingError(result.error || t('profile.aiSharing.errorSave'));
160	      setAiSharingError(parseApiError(err).message || t('profile.aiSharing.errorSave'));
179	        setNotifsError(result.error || t('profile.notifs.errorSave'));
183	      setNotifsError(parseApiError(err).message || t('profile.notifs.errorSave'));
219	        const msg = result.error || t('profile.notifs.errorSave');
225	      const msg = parseApiError(err).message || t('profile.notifs.errorSave');
227	      Alert.alert(t('profile.notifs.errorTitle'), msg);
298	      setPasswordError(parseApiError(err).message);
```
`EditProfileScreen.tsx:140` `Alert.alert(t('editProfile.error.deleteTitle'), parseApiError(err).message);`
`ResultsScreen.tsx:580-581` `const { message } = parseApiError(err); setDemographicsError(message || t('demographics.error.network'));`

Measured renders (`.qa-w3b/probes/w314_profile.test.tsx` — the `bundleE.s3` harness but with the
REAL `parseApiError` and the REAL `en.json` through `t`; prefs carry a priority so the switch is live):
```
PROBE(b2) PUT body = {"priorities":["quality"],"budget":"mid","lifestyle":[],"brand_attitude":"best_of_both","ai_sharing_enabled":true,"notifications_enabled":true,"notification_types":{}}
PROBE(b2) rendered error text = "Validation error: body → lifestyle → 0: Input should be ..."
PROBE(b3) rendered error text = "Failed to save preferences"          <- scary_vocab_en "Failed to" (src/i18n/.copy-policy.json)
PROBE(b4) rendered error text = "Request failed with status code 502" <- the A11 leak class (axios fall-through)
```
The limiters behind these surfaces (decorator-aware scan of `auth_routes.py` — the
`@limiter.limit` sits BELOW `@router.*`), so a raw "Rate limit exceeded. Please try again later."
("try again" = scary vocab) IS reachable: `PUT /reengagement-subs` `10/minute` (`:1052-1053`),
`PUT /password` `5/minute` (`:819-820`) + `ACCOUNT_LOCKED` (`:832-833`, 900 s), `DELETE /account`
**`1/minute`** (`:859-860` — a second tap inside a minute is a guaranteed 429), `PUT /demographics`
`5/minute` (`:1131-1132`). `PUT /preferences` (`:938`) carries no limiter.

### 3d. A user without priorities cannot exercise the AI-sharing opt-out

Backend `auth_routes.py`:
```
183	class UserPreferencesRequest(BaseModel):
184	    priorities: List[str] = Field(..., min_length=1, max_length=3)
```
Probe (`.qa-w3b/probes/test_w314_probe.py`, TestClient on the real app, `get_current_user`
overridden, services mocked, free tier):
```
PROBE(B1) PUT /preferences priorities=[] -> 422 {"success": false, "error": "Validation error: body → priorities: List should have at least 1 item after validation, not 0", "code": "VALIDATION_ERROR", "request_id": "…"}
PROBE(B1) save_user_preferences called: 0
PROBE(B2) PUT /preferences {ai_sharing_enabled:false} -> 422 {"success": false, "error": "Validation error: body → priorities: Field required", "code": "VALIDATION_ERROR", …}
PROBE(B3) PUT /api/v1/auth/ai-sharing -> 404 {"detail": "Not Found"}
PROBE(B3) PUT /api/v1/auth/notifications -> 404 {"detail": "Not Found"}
PROBE(B5) pydantic 2.7.0 -> ValidationError [… 'List should have at least 1 item after validation, not 0 [type=too_short, …]']
```
So there is NO body a no-priorities user can send today. Note the B3 shape: an unknown route is
Starlette's bare `{"detail": "Not Found"}` — no `success`, no `code` — which `parseApiError`
turns into `{message: 'Not Found', code: null}`. The client's answer today (F-S1.5i,
`ProfileScreen.tsx:239-250`) is to disable the switch and route the ROW tap to EditPreferences:
```
249	  const hasPriorities = (preferences?.priorities?.length ?? 0) > 0;
250	  const togglesGated = preferences === null || !hasPriorities;
```
and `getPreferences` (`api.ts:455-475`) returns `null` for a `{}` row AND for ANY thrown error
(`:472-474` bare `catch { return null; }`). Probe b1 (prefs `null`) and b5 (row
`{ai_sharing_enabled:false, notification_types:{}}` — exactly what the new route will write) both
→ `disabled:true`, 0 PUTs. The privacy control is unreachable in both.

---

## 4. The fix — MINIMAL design

### Client (OTA-safe, unflagged, backward-compatible with the backend on main)

**`src/services/api.ts`**
* `parseApiError` return type gains `retryAfterSeconds?: number`, set only when
  `data.retry_after_seconds` is a positive integer (`Number.isInteger(v) && v > 0`; mirror
  `_detail_retry_after`'s bool/float/≤0/string rejection). Added on the two envelope branches
  (`data.error` `:966`, `data.detail` `:969`); the TIMEOUT / transport / `error.message` /
  fallback branches are untouched (they never carry it). Every existing `{ message, code }`
  destructuring compiles unchanged.
* New `putPreferenceToggles(body: { ai_sharing_enabled?: boolean; notifications_enabled?: boolean })`
  → `api.put('/api/v1/auth/preference-toggles', body)`, returns `response.data`
  (`{ success, ai_sharing_enabled, notifications_enabled, error? }`). Placed next to
  `putReengagementSubs` (`:504-509`). `savePreferences` (`:477-480`) and `getPreferences`
  unchanged — `EditPreferencesFlow` keeps using them.

**`src/services/errorCopy.ts`**
* `friendlyErrorKey` UNCHANGED (its default `'home.errors.comparison'` and totality are pinned by
  `errorCopy.a11.test.ts`).
* New `settingsErrorKey(code: string | null | undefined, fallbackKey: string): string`:
  `RATE_LIMITED → 'common.errors.rateLimited'`, `ACCOUNT_LOCKED → 'common.errors.locked'`,
  everything else (incl. `null`/`undefined`/`''`) → `fallbackKey`. Total by construction; zero imports.

**`src/services/failureClassification.ts`** — insert `if (status === 429) return 'timeout';`
AFTER the `USAGE_LIMIT` check (`:49`) and BEFORE `not_found` (`:50`) — a `USAGE_LIMIT` 429 must
keep `'usage_limit'`. Update the matrix comment (`:10-22`). Reuses the existing soft retryable
state (`results.timeout.*`, tap-to-retry, `:713-726`) — the finding's first option; a dedicated
`'busy'` kind is deliberately NOT added (one more ResultsScreen branch + 2 keys for a sentence
that would differ from "Still gathering prices" only in nuance). Covers both consumers
(`:237`, `:328`).

**`src/screens/HomeScreen.tsx:482` and `:573`** — the two coded alerts become
`Alert.alert(t('common.error'), t(friendlyErrorKey(parsed.code), { count: parsed.retryAfterSeconds }))`.
Measured on the installed i18next 26.1.0 (scratchpad `i18next_count_probe.js`): a key with no
plural siblings resolves to the base key with no opts, with `count: undefined` AND with `count: 5`;
a key WITH `_one/_other` siblings resolves to the base key with no opts / `count: undefined` and to
the sibling with a number. So every non-RATE_LIMITED key, and every response without the field,
renders exactly today's sentence — and the a11 harness's `t` mock ignores `opts`
(`HomeScreen.errorCopy.a11.test.tsx:191-197`), so that suite stays green unchanged.

**`src/i18n/en.json` + `ar.json`** (flat dotted keys; `i18n.test.ts:8-10` requires the SAME key set
in both — 915 == 915 today; `home.savings.count_zero…_other` at `en.json:29-34` shows en carrying
all six Arabic forms, follow that):
* `home.errors.rateLimited_zero/_one/_two/_few/_many/_other` in BOTH files. en `_other`:
  "Plenty of compares in flight — give it {{count}} seconds, then tap."; en `_one`: "…give it a
  second, then tap."; en `_zero/_two/_few/_many` carry the `_other` sentence. ar `_few` uses ثوانٍ,
  `_many/_other` ثانية, `_two` ثانيتين, `_one` ثانية واحدة, `_zero` = today's base sentence.
  The BASE key stays in both (field absent / older backend).
* `common.errors.rateLimited` (NEW family — no `common.errors.*` key exists today): en "Plenty going
  on right now — give it a moment, then tap." ar "الضغط كبير الآن — أمهلها لحظة ثم اضغط."
* `common.errors.locked`: en "Too many tries just now — give it a while, then come back."
  ar "محاولات كثيرة الآن — أمهلها فترة ثم عُد."
  (No "couldn't", "try again", "Failed to", تعذر, فشل, تقدير — `copy-policy.test.ts` scans every
  string of both catalogs against `src/i18n/.copy-policy.json`.)
* `profile.toggle.disabledReason` becomes unreferenced from `src/` (its only readers are
  `ProfileScreen.tsx:501/:529/:569`, all deleted below) but STAYS in both files. Correction of the
  earlier draft's rationale: `i18n/no-deleted-keys.test.ts` pins only `results.whatsNext` /
  `results.save` absent plus en/ar COUNT parity, and `no-missing-referenced-keys.test.ts` only
  checks that referenced keys exist — so deleting it from both catalogs would ALSO stay green.
  Keeping it is simply the smaller diff; either is acceptable, say which in the PR.
* Settings surfaces deliberately do NOT interpolate seconds: their windows are 1/5/10-minute
  limiters plus the 900 s lockout, where "give it 900 seconds" is worse than "a moment". Compare is
  where the re-hammer impact lives and where the window is always ≤ 61 s (W1-9 measured 60/61).

**`src/screens/ProfileScreen.tsx`**
* `handleAiSharingToggle(value)` (`:145-163`) → `putPreferenceToggles({ ai_sharing_enabled: value })`;
  `handleNotificationsToggle` (`:168-186`) becomes `(value: boolean)` →
  `putPreferenceToggles({ notifications_enabled: value })` (its only caller, `:540`, passes
  `{ notifications_enabled: v }` — simplify the signature). Optimistic `setPreferences(next)` /
  rollback `setPreferences(previous)` unchanged; `buildNextPrefs` (`:131-143`) stays for the
  optimistic local state (it is what `aiSharingEnabled`/`notificationsEnabled` render from).
* Every error render becomes i18n-only: `:156/:160` → `t(settingsErrorKey(code, 'profile.aiSharing.errorSave'))`;
  `:179/:183/:219/:225-227` → `t(settingsErrorKey(code, 'profile.notifs.errorSave'))` — the
  `result.error ||` arms too (`result.error` is the backend's English `{success:false,error}` body,
  e.g. "Failed to update notification preferences" from `:1096-1099`). `code` =
  `parseApiError(err).code` in the catch arms; `null` in the `!result.success` arms.
* `:298` (password): ONLY the two 429 codes route to i18n —
  `parsed.code === 'RATE_LIMITED' || parsed.code === 'ACCOUNT_LOCKED' ? t(settingsErrorKey(parsed.code, 'profile.aiSharing.errorSave')) : parsed.message`.
  The 400 arm keeps the backend string on purpose: "Current password is incorrect"
  (`auth_service.py:634/652`) is a plain-string detail with no code (`auth_routes.py:846`
  `raise HTTPException(status_code=400, detail=result["error"])`), and it IS the actionable
  information. Making it code-keyed is a backend contract choice (§8). `:295`'s hard-coded
  `'Password change failed'` and the client-side validation strings at `:281-283` are the password
  modal's own (un-i18n'd) copy — outside this finding, §8.
* Delete the F-S1.5i gate: `hasPriorities`, `togglesGated` (`:249-250`); the two TouchableOpacity
  hosts' `onPress/activeOpacity/disabled/accessibilityRole/accessibilityLabel` gating props
  (`:494-505`, `:519-533`) — the hosts stay as plain `View`s (or keep the TouchableOpacity with
  `disabled` and no press handler; say which); `disabled={… || togglesGated}` (`:513`, `:541`);
  the `!togglesGated` in the sub-toggle guard (`:543`); the caption block (`:567-573`); styles
  `flatRowToggleHostMuted` (`:778-780`) and `toggleGatedCaption` (`:781-786`); the F-S1.5i
  comments (`:239-248`, `:489-492`, `:775-777`). `handleEditStyleProfile` (`:276-278`) STAYS —
  `PrioritiesInline` at `:436` uses it. The sub-toggles never needed the gate (they go through
  `/reengagement-subs`, which has no priorities requirement) — the gate was over-broad.
* `savePreferences` leaves ProfileScreen's import list (`:63`; unused after this).

**`src/screens/EditProfileScreen.tsx:140`** →
`Alert.alert(t('editProfile.error.deleteTitle'), t(settingsErrorKey(parseApiError(err).code, 'common.error')))`
(`common.error` = "Hold on — give it another tap." / "لحظة — جرّب الضغط مرّة ثانية." exists in both
catalogs; no new key).

**`src/screens/ResultsScreen.tsx:580-581`** →
`setDemographicsError(t(settingsErrorKey(parseApiError(err).code, 'demographics.error.network')))`.

**Neighbour tests that MUST be rewritten in the same PR (they pin the gate / the old call):**
* `__tests__/ProfileScreen.togglesGated.test.tsx` — all 8 tests (`:29-76`) pin F-S1.5i by source
  regex; DELETE the file (its contract is what this unit removes; R5 replaces it).
* `__tests__/ProfileScreen.bundleE.s3.integration.test.tsx` — (i) `:233-297` three tests
  `expect(mockSavePreferences).toHaveBeenCalled()` on the AI / notifications switches → expect
  `mockPutPreferenceToggles` (add it to the api mock at `:34-42`); (ii) **`:301-317`**
  `'renders the togglesGated caption when preferences.priorities is empty'` asserts
  `getByText('Pick your priorities first')` — DELETE or invert it (R5(i)/(ii) cover the new
  contract). The earlier draft missed (ii).
* `__tests__/Screens.bundleD.contract.test.ts:129-133` — regex requires `savePreferences` in
  ProfileScreen's api import → require `putPreferenceToggles` alongside `putReengagementSubs`.
  (`:308`'s `/savePreferences/` is `NewOnboardingHost.tsx`'s SRC, `:281-285` — untouched.)
* `__tests__/ResultsScreen.networkMatrix.m18.test.ts:100-106` — the regex
  `t\(friendlyErrorKey\(parsed\.code\)\)` → the new `{ count: parsed.retryAfterSeconds }` shape,
  still exactly 2 matches; the balanced-paren "no alert renders `.message`" test at `:108+` stays.
* `__tests__/ProfileScreen.optimistic.test.tsx:7` header comment says the masters go to
  `/preferences` — comment only, no assertion on it; update the sentence.
* `__tests__/api.networkMatrix.m18.test.ts:240-246` (plain 4xx → generic) uses 400/422 — stays
  green; R4 adds the 429 rows next to it.
* `__tests__/ProfileScreen.logoutCopy.b6.test.tsx:76` mocks `savePreferences` — harmless (extra
  mock key); it never triggers a toggle, so `putPreferenceToggles` being absent from that mock
  cannot fire. Leave it.

### Backend (additive, one route, no flag) — `app/api/auth_routes.py`

Placed next to `update_reengagement_subs` (`:1052-1104`) and shaped exactly like it:
```python
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator   # + model_validator (NOT imported today, :9)

class PreferenceTogglesBody(BaseModel):
    ai_sharing_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    @model_validator(mode="after")
    def _at_least_one(self):
        if self.ai_sharing_enabled is None and self.notifications_enabled is None:
            raise ValueError("provide ai_sharing_enabled and/or notifications_enabled")
        return self

@router.put("/preference-toggles")
@limiter.limit("10/minute")
async def update_preference_toggles(request: Request, body: PreferenceTogglesBody,
                                    current_user: dict = Depends(get_current_user)):
    client = get_user_supabase_client(access_token) if access_token else get_admin_supabase_client()   # :1066-1069 idiom
    row = client.table("users").select("preferences").eq("id", user_id).single().execute()
    prefs = (row.data or {}).get("preferences") or {}
    for k in ("ai_sharing_enabled", "notifications_enabled"): if getattr(body, k) is not None: prefs[k] = getattr(body, k)
    client.table("users").update({"preferences": prefs}).eq("id", user_id).execute()
    return {"success": True, "ai_sharing_enabled": prefs.get("ai_sharing_enabled"),
            "notifications_enabled": prefs.get("notifications_enabled")}
```
* Writes ONLY the provided key(s). Does NOT touch `preferences_completed` (onboarding's completion
  signal — `save_user_preferences` sets it), `_sources`, `priorities`, or `notification_types`;
  does NOT call `save_user_preferences` / `record_preference_history`.
* Same `except Exception → 500 {"code":"INTERNAL_ERROR"}` shape as `:1089-1101`.
* Pydantic-shaped: a bool field rejects `"yes"` → 422 VALIDATION_ERROR through the existing
  handler; `{}` → 422 via the model validator.
* Readers tolerate a toggle-only row: `grep -rn '\["priorities"\]' app/` → **0**; nine
  `.get("priorities"` sites; `openai_service.py:88` reads `user_prefs.get("ai_sharing_enabled") is False`;
  `reengagement_service.py:108` reads `prefs.get("notifications_enabled") is False` — the same
  keys this route writes.
* The two `.execute()` calls are SYNCHRONOUS on the event loop, exactly like the precedent route
  they mirror (`:1080-1086` is not wrapped in `run_db` either). Matching the precedent is the
  minimal choice; wrapping both routes in `run_db` (M13-05 class, `ENABLE_SYNC_DB_OFFLOAD`) is a
  separate hygiene unit, §8.
* Why no `ENABLE_*` flag: the route is additive (every existing route byte-identical; the flag
  rule exists for BEHAVIOUR changes on existing routes); its ONLY caller is the OTA'd client, and
  a default-OFF flag would make that client's privacy toggle 503/404 (rendered as "didn't save")
  until Ahmed flips it — strictly worse than the precedent. If a reviewer wants it dark anyway,
  `ENABLE_PREFERENCE_TOGGLES` read per call inside the handler (503 `FEATURE_DISABLED` when off)
  is the shape; the client already renders that 503 as the neutral fallback via `settingsErrorKey`.
* `PUT /preferences` and `UserPreferencesRequest.min_length=1` are NOT relaxed (that would be a
  behaviour change on an existing route → flag → downstream "empty priorities" semantics in
  `EditPreferencesFlow` and cohort seeding).

**Ordering / compatibility:** the backend deploys on merge; the OTA is Ahmed's lever and lags.
Phones on 97b5f15 never call the route. An OTA'd phone against a backend WITHOUT the route gets
Starlette's bare 404 `{"detail":"Not Found"}` → `parseApiError` → `{message:'Not Found', code:null}`
→ `settingsErrorKey(null, 'profile.aiSharing.errorSave')` → neutral copy, and the optimistic value
rolls back — degraded, never a raw string, never a crash (R5(iv) pins that exact shape).

---

## 5. Red tests — exact paths, assertions, measured reason each is RED today

**R1 `__tests__/api.parseApiError.retryAfter.w314.test.ts`** (real `parseApiError`, axios-shaped errors)
* W1-9 slowapi shape (`retry_after_seconds: 61`, `code: RATE_LIMITED`) → `retryAfterSeconds === 61`;
  ACCOUNT_LOCKED shape (`900`) → `900`; the same envelope without the field → `retryAfterSeconds`
  is `undefined` and the object still deep-equals `{message, code}` (no key added); `0`, `-5`,
  `61.5`, `"61"`, `true` → `undefined`; the `data.detail` legacy shape with the field → read too.
  RED: field absent (`keys = ['message','code']`).
  Mutation: accept any number → the `61.5`/`"61"` rows redden; drop the `detail` branch → that row reddens.

**R2 `__tests__/errorCopy.w314.test.ts`**
* `settingsErrorKey('RATE_LIMITED', 'x') === 'common.errors.rateLimited'`,
  `('ACCOUNT_LOCKED','x') === 'common.errors.locked'`,
  `(null|undefined|''|'VALIDATION_ERROR'|'BAD_REQUEST'|'NOT_FOUND'|'TIMEOUT', 'x') === 'x'`.
  RED: function does not exist.
* Every key it can emit + the six `home.errors.rateLimited_*` exist in BOTH catalogs, non-empty,
  and obey the copy contract (`/couldn't|try again|Failed to/` and `تعذر|فشل|تقدير|مُقدَّر` absent —
  read the lists from `src/i18n/.copy-policy.json`, don't retype them). RED: keys absent.
* Real i18next instance on the real catalogs (the `i18n/plurals.test.ts:28-41` pattern):
  `t('home.errors.rateLimited', { count: 61 })` contains `"61"` and is not the base sentence;
  `{ count: undefined }` and no-opts both equal the base sentence; ar with count 1/2/3/11/61 yields
  ≥ 4 distinct strings, none containing ASCII letters. RED: no plural siblings → base sentence.
  Mutation: drop the `_other` key → red; drop `{{count}}` from the sentence → the "contains 61" row reddens.

**R3 `__tests__/HomeScreen.rateLimitedSeconds.w314.test.tsx`** (clone of the a11 harness, but
`parseApiError: jest.requireActual('../src/services/api').parseApiError` — the a11 harness
re-implements it WITHOUT the field, `:79-95` — and a `t` mock that honours `count` by resolving
`key + '_one' / '_other'` when present; the a11 `t` ignores opts)
* Text path: `onError` with the W1-9 429 shape (`retry_after_seconds: 42`) → the Alert body
  equals `EN['home.errors.rateLimited_other'].replace('{{count}}','42')` and never matches
  `/Rate limit|try again|per 1 minute/i`. Same for the URL `catch`. Without the field → body equals
  the base key. RED: body is the base sentence (call site passes no `count`).
  Mutation: remove `{ count }` at either call site → that path's row reddens.

**R4 `__tests__/api.networkMatrix.w314.test.ts`** (or rows appended next to
`api.networkMatrix.m18.test.ts:240-246`)
* `classifyLoadFailure({response:{status:429,data:{code:'RATE_LIMITED'}}}) === 'timeout'`;
  `429` with `data: {}` → `'timeout'`; `429 USAGE_LIMIT` (both the `data.code` and the tagged
  `err.code` shapes) → `'usage_limit'` (preserve, ordering); `400`/`422` → `'generic'` (preserve).
  RED: measured `generic`. Mutation: place the 429 line above the USAGE_LIMIT check → the
  usage_limit row reddens.

**R5 `__tests__/ProfileScreen.toggles.w314.test.tsx`** (render harness = `.qa-w3b/probes/w314_profile.test.tsx`:
real `parseApiError`, real `en.json` through `t`, `putPreferenceToggles` + `savePreferences` +
`putReengagementSubs` mocked; `ToggleRow` exposes `accessibilityRole="switch"`,
`accessibilityState={{checked, disabled}}`, `accessibilityLabel = label` — `ToggleRow.tsx:44-46`)
* (i) `getPreferences → null`: `getByLabelText('Help improve AI quality').props.accessibilityState.disabled === false`;
  `fireEvent(UNSAFE_getAllByType(Switch)[0], 'valueChange', true)` → `putPreferenceToggles`
  called ONCE with exactly `{ ai_sharing_enabled: true }`; `savePreferences` never called;
  `queryAllByText('Pick your priorities first').length === 0`. RED (measured b1): disabled true,
  0 calls, caption ×1.
* (ii) prefs row `{ ai_sharing_enabled: false, notification_types: {} }` (no priorities): same as
  (i). RED (b5).
* (iii) notifications master `valueChange(false)` → `{ notifications_enabled: false }` exactly;
  the three sub-toggle rows render while the master is on, even with no priorities (5 Switches
  total). RED: gated/hidden (`:543 notificationsEnabled && !togglesGated`).
* (iv) `putPreferenceToggles` rejects with the 422 envelope / the 400
  `{success:false,error:'Failed to save preferences',code:'BAD_REQUEST'}` envelope /
  `new Error('Request failed with status code 502')` / the bare Starlette 404
  `{response:{status:404,data:{detail:'Not Found'}}}` → rendered error text
  `=== EN['profile.aiSharing.errorSave']` and never matches `/Validation error|Failed to|Request failed|Not Found/`;
  the switch value rolls back. RED today on the `savePreferences` path (b2/b3/b4 rendered the raw strings).
* (v) rejects with the RATE_LIMITED envelope → `EN['common.errors.rateLimited']`; resolves
  `{ success:false, error:'oops' }` → `EN['profile.aiSharing.errorSave']`, never "oops".
* (vi) sub-toggle: `putReengagementSubs` rejects with the RATE_LIMITED envelope → `Alert.alert`
  second arg `=== EN['common.errors.rateLimited']` and the inline text the same. RED: raw
  "Rate limit exceeded. Please try again later.".
  Mutation for (iv)-(vi): restore `parseApiError(err).message ||` at any one site → its row reddens.

**R6 `__tests__/EditProfileScreen.deleteCopy.w314.test.tsx`** (harness =
`EditProfileScreen.bundleE.s3.integration.test.tsx:30-60` — `default.delete` is `mockApiDelete`,
`:39` — but with the real `parseApiError` and the real `en.json` through `t`): confirm delete
(`:253-262` drives `edit-delete-account-row` then the Alert's destructive button) with
`mockApiDelete` rejecting the RATE_LIMITED envelope → Alert body `EN['common.errors.rateLimited']`;
rejecting `new Error('Request failed with status code 502')` → `EN['common.error']`, never `/failed/i`.
RED: raw message. Mutation: restore `parseApiError(err).message` → both rows redden.

**R7 `__tests__/ResultsScreen.demographicsCopy.w314.test.ts`** (source-contract in the m18 style:
extract the `handleDemographicsSubmit` catch by balancing braces): asserts `setDemographicsError(`'s
argument is a `t(` call and the block contains no `message` identifier from `parseApiError`.
RED: `const { message } = parseApiError(err); setDemographicsError(message || …)`. (A render
test would need the demographics modal path of a 700-line screen; the source contract is what
this repo already accepts for this class — `ResultsScreen.networkMatrix.m18.test.ts:108+`.)
Mutation: restore the destructuring → red.

**B1 `tests/test_auth_preference_toggles_w314.py`** (TestClient on the real app,
`app.dependency_overrides[get_current_user]` as `tests/test_push_token_endpoint.py:68-86` does,
`patch('app.api.auth_routes.get_user_supabase_client')` returning a MagicMock whose
`.table().select().eq().single().execute()` yields a row; free tier, no network; conftest's autouse
`_reset_rate_limiter` (`conftest.py:237-243`) gives each test a clean window)
* `PUT /api/v1/auth/preference-toggles {"ai_sharing_enabled": false}` on a row with
  `preferences: {}` → 200 `{"success": true, "ai_sharing_enabled": false, "notifications_enabled": None}`;
  `update` was called with `{"preferences": {"ai_sharing_enabled": False}}` and the payload has
  no `preferences_completed` key. RED: 404 (probe B3).
* `{"notifications_enabled": false}` on a row with priorities/budget/_sources/notification_types →
  the update payload preserves every other key byte-for-byte and flips only that one. RED: 404.
* `{}` → 422 with `code == "VALIDATION_ERROR"`; `{"ai_sharing_enabled": "yes"}` → 422. RED: 404
  (assert on `code`, not on the Pydantic message text — pydantic 2.7.0 local vs 2.13.4 pinned).
* 11th call inside the window → 429 with `code == "RATE_LIMITED"`, `retry_after_seconds` a positive
  int `<= 61` and `Retry-After` header equal to it (the W1-9 contract carried onto the new route;
  `test_429_contract.py`'s docstring records slowapi 0.1.9's `+1`). RED: 404.
* supabase raises → 500 `{"code": "INTERNAL_ERROR"}` (same as reengagement-subs). RED: 404.
* Without the override → 401 `AUTH_REQUIRED`. RED: 404.
* Regression pin, already green, say so in the docstring: `PUT /preferences` with
  `priorities: []` still → 422 and `save_user_preferences` is not awaited (probe B1).
* Mutation: route the write through `save_user_preferences` → the "no `preferences_completed`" row
  reddens; drop the RMW read → the preserve-other-keys row reddens; drop `@limiter.limit` → the
  429 row reddens.

---

## 6. Preserve — with the pin that proves it

| behaviour | pin |
|---|---|
| Home text + URL 429 render `home.errors.rateLimited` (base) when the field is absent; codeless 502 renders neutral copy; INSUFFICIENT_DATA / TIMEOUT copy | `HomeScreen.errorCopy.a11.test.tsx` (its `parseApiError` mock lacks the field and its `t` ignores opts → base sentence; stays green unchanged) + R3's no-field row |
| `friendlyErrorKey` totality, default key, TIMEOUT mapping | `errorCopy.a11.test.ts` (unchanged) |
| No HomeScreen alert renders `.message` | `ResultsScreen.networkMatrix.m18.test.ts:108+` (unchanged) |
| A non-USAGE_LIMIT 429 passes the axios interceptor untouched (so the field reaches the screen) | `api.refreshInterceptor.test.ts:194-202` (unchanged) |
| USAGE_LIMIT 429 → Paywall on Home and Results; camera raw-fetch tagged error | `api.networkMatrix.m18.test.ts:203-206, :291`; R4's USAGE_LIMIT rows |
| `parseApiError` 503→TIMEOUT, transport→TIMEOUT, `{message, code}` shape | `api.networkMatrix.m18`, `errorCopy.a11` (unchanged) + R1's no-field deep-equal |
| History load failure → retryable state (any status) | `HistoryScreen.searchState.a12.test.tsx:182-201` |
| Sub-toggles → `PUT /reengagement-subs` with plural keys, optimistic rollback | `ProfileScreen.optimistic.test.tsx`, `bundleE.s3.integration:282+` |
| `ai_sharing_enabled` undefined → OFF (R23) | `ProfileScreen.aiSharingDefault.test.tsx` (unchanged) |
| `getPreferences` `{}`/throw → null; EditPreferencesFlow still requires ≥1 priority | `getPreferences.emptyObject.test.ts`, `EditPreferencesFlow*.test.tsx` (unchanged) |
| `PUT /preferences` still rejects `priorities: []` with 422 and does not write | regression pin in B1's file |
| `PUT /reengagement-subs` untouched | `git diff` shows no change at `:1052-1104`; `tests/test_push_token_endpoint.py` |
| Both 429 classes still carry `Retry-After` + `retry_after_seconds` | `tests/test_429_contract.py` (17 green at HEAD) |
| en/ar key parity (915 == 915 today), no deleted `results.*` keys, copy policy, every `t('…')` literal exists | `i18n.test.ts`, `i18n/no-deleted-keys.test.ts`, `copy-policy.test.ts`, `i18n/no-missing-referenced-keys.test.ts`, `demographics.i18n.test.ts:35` (`demographics.error.network` required) |
| W3-8 / W3-12 / A11 / A12 / W1-9 untouched | none of their files are in §4 |

---

## 7. Gates

1. Red-first: R1-R7 and B1 fail for the measured reasons BEFORE any source edit; paste the
   failure lines. A red test that fails only because a module/route is missing must ALSO be
   shown red for its assertion once the stub exists (R2, R5, B1).
2. Unit jest files by path: `node node_modules/jest/bin/jest.js --ci <R1..R7>` from `SmartCompareApp`.
3. Neighbour suites. Rule-grep: `grep -rlE "ProfileScreen|HomeScreen|HistoryScreen|EditProfileScreen|ResultsScreen|errorCopy|parseApiError|getPreferences|savePreferences|failureClassification|putReengagementSubs" __tests__`
   → **97** files at HEAD (86 with path-strict patterns; list in scratchpad `neighbours.txt`).
   Run the whole 97 at base and head. Measured baseline of the 18 most sensitive
   (`HomeScreen.errorCopy.a11`, `errorCopy.a11`, `ResultsScreen.networkMatrix.m18`,
   `api.networkMatrix.m18`, `HistoryScreen.searchState.a12`, `ProfileScreen.togglesGated`,
   `ProfileScreen.bundleE.s3.integration`, `ProfileScreen.optimistic`, `ProfileScreen.aiSharingDefault`,
   `Screens.bundleD.contract`, `EditProfileScreen.bundleE.s3.integration`, `i18n.test`, `i18n/plurals`,
   `copy-policy`, `getPreferences.emptyObject`, `i18n/no-deleted-keys`, `i18n/no-missing-referenced-keys`,
   `demographics.i18n`): **18 passed / 233 passed, 8 todo / 0 snapshots**.
4. `node node_modules/typescript/bin/tsc --noEmit` exit 0 (baseline exit 0; `tsc -v` = 5.9.3).
5. `node node_modules/eslint/bin/eslint.js` on every touched `.ts/.tsx` — 0 errors; warnings not
   above the baseline **74** measured on the 7 files in §4 (`api.ts`, `errorCopy.ts`,
   `failureClassification.ts`, `HomeScreen.tsx`, `ProfileScreen.tsx`, `EditProfileScreen.tsx`,
   `ResultsScreen.tsx`); the removed ProfileScreen code should lower it.
6. Full jest suite once in the green phase (baseline at `ece0fbbe`: 2,729 passed / 0 failed /
   278 suites, 3 skipped suites, 44 snapshots). Expect −1 suite (togglesGated deleted) +7 new.
7. Backend: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_auth_preference_toggles_w314.py tests/test_429_contract.py tests/test_error_middleware.py tests/test_auth_ai_sharing_toggle.py tests/test_personalization.py tests/test_push_token_endpoint.py -q -p no:randomly -p no:cacheprovider`
   (all six exist at HEAD); `python -m ruff check --select E9,F63,F7,F82 app/api/auth_routes.py`
   (clean at HEAD, with `error_handler.py`).
8. Module-reference comm gate (backend): union of `grep -rlE "auth_routes" tests/` (**39** files at
   HEAD) + judgement importers (`test_endpoint_shapes_vs_jsx.py`, `test_brute_force.py`,
   `test_m13_01_slowapi_middleware.py` — all exist) + **the 9 backend tests that scan
   `SmartCompareApp/`** (`grep -rl "SmartCompareApp" tests/` — the mobile-gate rule from CLAUDE.md;
   `test_endpoint_shapes_vs_jsx.py` is one of them and the new client route call is exactly what it
   reads) + the unit file; base vs head, identical pass counts plus the new file's; branch-only-NEW = ∅.
9. Mutation checks named in §5 executed once each and reverted (delete the fix, confirm the test reddens).
10. Fable review before commit; agents never commit.

---

## 8. What this unit CANNOT do / Ahmed dependencies / what only a device or store can verify

* **OTA (Ahmed)** — every client change reaches phones only via `eas update --branch preview --clear-cache`.
  Until then phones on 97b5f15 keep the gated Profile toggles and the raw strings; the new backend
  route sits unused. Deploy order: backend on merge (automatic), THEN the OTA — state it in the PR.
* **Device-only** — the Arabic plural sentences with real seconds on Hermes (`intl-pluralrules`
  polyfill; jest runs node's native Intl — `i18n/plurals.test.ts:26-41` exercises the polyfill
  CLASS, not Hermes), RTL alignment of the now caption-less toggle rows, and an actual 429 on a
  phone against Railway's shared-IP bucket (`ENABLE_PROXY_AWARE_RATELIMIT` is OFF — one bucket per
  route deployment-wide, so a tester CAN trigger it by hand).
* **No live verification** of RLS on the new route's user-scoped write (same client factory as
  reengagement-subs, live since `228ff63`); a wrong RLS policy surfaces as 500 INTERNAL_ERROR →
  neutral copy, never a raw string.
* **`HomeScreen.tsx:432` and `:540` render `data.error` / `response.data.error` raw** on the HTTP-200
  `success:false` arms. Measured: `:432` is the SSE `onComplete` arm, unreachable under the shipped
  `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` (the REST fallback `api.ts:606-619` re-routes a 200
  `success:false` into `onError` with `{status:200, data:{code,error}}`, which lands on the A11
  map); `:540` is the URL path's 200 `success:false` (`url_extraction_service.py:443/:576` produce
  such bodies). Neither can carry a 429, so they are outside this finding; they are W4's
  "`str(e)` shipped as the user-facing error" territory (another session owns W4). The one-line
  fold-in if the reviewer wants it: `t(friendlyErrorKey(data.code))` — it keeps the m18 count at 2
  because the regex keys on `parsed.code`. NOT in this diff unless ruled.
* Item 12 (tier/remaining) — dropped, no consumer (§2). Needs a product decision on whether the
  Paywall should show remaining credits at all before any backend pass-through is worth a diff.
* `PUT /password` 400 arm still renders "Current password is incorrect" raw (English-only), and
  `ProfileScreen.tsx:281-283/:295` carry hard-coded English validation copy incl. the token
  "failed" — needs a backend code (e.g. `INVALID_CURRENT_PASSWORD`) plus an i18n pass on the
  password modal; not this unit.
* Login/Register/ForgotPassword `setError(parseApiError(err).message)` (`LoginScreen.tsx:308`,
  `RegisterScreen.tsx:240`, `ForgotPasswordScreen.tsx:52`) are outside the five screens; the
  900 s ACCOUNT_LOCKED renders raw there today. M18 MB-flows-11 territory — re-file, do not fold in.
* The new route (and its precedent) run sync `.execute()` on the loop — wrapping both in `run_db`
  is the M13-05 hygiene class, its own unit.
* A compare-CTA cooldown driven by `retryAfterSeconds` (stop the re-hammer mechanically rather
  than by copy) is a behaviour change on HomeScreen with many pins; explicitly NOT in this unit.
* Local backend drift (fastapi 0.115.0 / pydantic 2.7.0 / slowapi 0.1.9 / starlette 0.38.6 vs the
  pins) — the 422 message text and slowapi's `+1` are CI-settled; assert on `code` and ranges.

---

## 9. PR-body facts

1. Base `ed75dc70`. Findings MB-NETWORK-CONTRACT-05, -06; MB-RECONCILE-18(12) dropped with
   evidence (`PaywallScreen.tsx:224-233` never reads `initialUsage` fields).
2. Already green and NOT re-filed: Home text+URL 429 copy (A11 `74d041cb`, `HomeScreen:482/:573`,
   pinned by `HomeScreen.errorCopy.a11:304-322`), History load failure (A12, `HistoryScreen:698-709`),
   backend `retry_after_seconds` on both 429 classes (W1-9 #152, 17 green). The plan's (b) as
   worded is green because F-S1.5i disables the switch — which is the defect.
3. Client: `parseApiError` gains `retryAfterSeconds` (positive-int only, additive, no key when
   absent); `settingsErrorKey` added, `friendlyErrorKey` untouched; `classifyLoadFailure` 429 →
   `timeout` (USAGE_LIMIT ordering preserved, both ResultsScreen consumers); Home's two coded alerts
   pass `{ count }`; 6+6 plural keys + 2+2 new keys in en/ar, 0 keys deleted (915 → 923 each);
   ProfileScreen's two master toggles move to `PUT /api/v1/auth/preference-toggles`; the F-S1.5i
   gate is removed (8-test file deleted, 3 integration expectations + 1 caption test + 1 contract
   regex + 1 m18 regex updated); 9 raw-string render sites (Profile ×7 incl. the Alert, EditProfile
   ×1, Results ×1) now render catalog copy only; Profile password 400 arm intentionally still shows
   the backend sentence.
4. Backend: ONE additive route, 10/min, RMW of `users.preferences` touching only the provided
   key(s), never `preferences_completed`/`_sources`/history; `PUT /preferences` and
   `min_length=1` unchanged; no flag (rationale §4), no migration, no env var; `model_validator`
   import added.
5. Compatibility: phones on 97b5f15 unaffected; OTA'd client vs a backend without the route →
   bare 404 → `code:null` → neutral copy + rollback. Backend deploys on merge; OTA is Ahmed's.
6. Numbers: probe renders "Validation error: body → lifestyle → 0…", "Failed to save
   preferences", "Request failed with status code 502" at HEAD; `classifyLoadFailure(429)=generic`
   at HEAD; `PUT /preference-toggles` = 404 at HEAD; neighbour 18-suite baseline 233/8 todo;
   jest full-suite before/after; tsc 0; eslint 0 errors / 74 warnings baseline; ruff clean;
   backend comm gate branch-only-NEW = ∅.
7. Device checklist after the OTA: Profile → AI-sharing on a fresh account with no preferences
   flips and persists across a reload; Arabic seconds sentence on a forced 429 (tap compare 11×
   inside a minute); the three re-engagement sub-toggles visible with no priorities.

---

## 10. Measurements run (command → observed, this session, 2026-09-11)

1. `git rev-parse HEAD` → `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git status --short` → empty
   before and after all runs (`.qa-*/` gitignored, `.gitignore:72`).
2. `git merge-base --is-ancestor <sha> HEAD` → yes for `74d041cb` (A11), `a4e7b08b` (#152 W1-9),
   `08167de1` (#151), `228ff63` (reengagement-subs).
3. `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`; `tsc --noEmit` → exit 0 (12 s under load).
4. `node -e` over `node_modules/<pkg>/package.json` vs `package.json` pins → the table in §1.
5. `python --version` → 3.12.9; `python -c "import pydantic, fastapi, slowapi, starlette; from pydantic import model_validator"` →
   pydantic 2.7.0 / fastapi 0.115.0 / starlette 0.38.6 / slowapi 0.1.9, import ok; `requirements.txt`
   `:47 fastapi==0.141.1`, `:109 pydantic==2.13.4`, `:144 slowapi==0.1.10`, `:150 starlette==1.6.0`.
6. `grep -rn "retry_after\|Retry-After\|retryAfter\|RATE_LIMITED\|rateLimited\|ACCOUNT_LOCKED" src __tests__`
   (excluding `src/i18n`) → `HomeScreen.tsx:479` (comment), `errorCopy.ts:39/43`,
   `api.refreshInterceptor.test.ts:196`, `errorCopy.a11.test.ts:16/153/157/163/198`,
   `HomeScreen.errorCopy.a11.test.tsx:304/315/321`. Zero `retry_after` readers.
7. `node node_modules/jest/bin/jest.js --ci --roots ../.qa-w3b/probes --testMatch "**/*.test.tsx" --modulePaths C:/Users/SynAckITPC/Documents/AI/sc-w3-copy/SmartCompareApp/node_modules`
   (from `SmartCompareApp`; `--modulePaths` is needed because a bare `jest.mock('@react-navigation/native')`
   from outside `SmartCompareApp` cannot resolve through the junction otherwise) → 2 suites / 8 passed;
   outputs quoted verbatim in §3a/§3b/§3c/§3d (b1: disabled true, 0 PUTs after row press AND after
   `Switch.onValueChange(true)`, caption ×1, Switch count 2; b2 PUT body + "Validation error: body →
   lifestyle → 0: Input should be ..."; b3 "Failed to save preferences"; b4 "Request failed with
   status code 502"; b5 disabled true, 0 PUTs). Harness caveat: b1's `navigation.navigate calls = []`
   is an artifact — `getByLabelText('Help improve AI quality')` resolves the inner disabled
   `ToggleRow`, so RNTL never reached the gated host's `onPress`; nothing in this spec relies on it.
8. `PYTHONIOENCODING=utf-8 python -m pytest .qa-w3b/probes/test_w314_probe.py -q -s -p no:randomly -p no:cacheprovider`
   → 5 passed; B1 422 (Pydantic string, `save_user_preferences` awaited 0), B2 422 "Field required",
   B3 404 ×2 as bare `{"detail": "Not Found"}`, B4 envelope drops `tier`/`remaining`
   (`{"success":false,"error":"Comparison limit reached (monthly)","code":"USAGE_LIMIT","request_id":"unknown"}`),
   B5 pydantic 2.7.0 `too_short`.
9. `PYTHONIOENCODING=utf-8 python -m pytest tests/test_429_contract.py -q -p no:randomly -p no:cacheprovider` → 17 passed.
10. `NODE_PATH=<junction> node scratchpad/b5/W3-14/i18next_count_probe.js` → i18next 26.1.0; base key
    with no opts / `count: undefined` / `count: 5` → base sentence; `_one/_other` siblings: no opts /
    `count: undefined` → base, `count: 1` → `_one`, `count: 61` → `_other`; ar 0/1/2/3/11/100 →
    zero/one/two/few/many/other.
11. 18 neighbour suites (list in §7.3) → 18 passed / 233 passed / 8 todo / 0 snapshots.
12. `node node_modules/eslint/bin/eslint.js` on the 7 client files → 0 errors / 74 warnings, exit 0.
13. `python -m ruff check --select E9,F63,F7,F82 app/api/auth_routes.py app/middleware/error_handler.py` → All checks passed.
14. Decorator-aware limiter scan (`grep -n "@router\.\(put\|post\|delete\|get\)\|@limiter.limit" app/api/auth_routes.py`):
    `/password` `:819-820` 5/min, `/account` `:859-860` 1/min, `/preferences` `:938` none,
    `/reengagement-subs` `:1052-1053` 10/min, `/demographics` `:1131-1132` 5/min; lockout helper
    `_account_locked_response` `:763-782`, called `:832-833`.
15. `grep -rn '\["priorities"\]' app/ | wc -l` → 0; `grep -rn 'get("priorities"' app/ | wc -l` → 9;
    `openai_service.py:88`; `reengagement_service.py:108`.
16. `grep -rlE "auth_routes" tests/ | wc -l` → 39; `grep -rl "SmartCompareApp" tests/ | wc -l` → 9;
    the six pytest files in §7.7 and the three judgement importers all exist (`ls`).
17. `grep -rlE "<11 module names>" __tests__ | wc -l` → 97 (86 path-strict; `neighbours.txt` in scratchpad).
18. `node -e` key counts → en 915 / ar 915; `grep -c '"home.savings.count_'` → 6 / 6; no
    `"common.errors.` key in either catalog; `home.errors.rateLimited` at `en:119` / `ar:116`;
    `profile.toggle.disabledReason` at `en:823` / `ar:820`, referenced only from
    `ProfileScreen.tsx:501/:529/:569` and `togglesGated.test.tsx:70-73`.
19. i18n fences read: `i18n.test.ts:5-10` (set equality), `i18n/no-deleted-keys.test.ts:31-77`
    (`results.whatsNext`/`results.save` absent + count parity — does NOT pin any other key),
    `i18n/no-missing-referenced-keys.test.ts:4/:64` (every literal `t('key')` in `src/` exists in
    en), `copy-policy.test.ts` + `src/i18n/.copy-policy.json` (`scary_vocab_en` =
    `couldn't`/`try again`/`Failed to`; `scary_vocab_ar` = `تعذر`/`فشل`/`تقدير`/`مُقدَّر`),
    `demographics.i18n.test.ts:35`, `i18n/plurals.test.ts:26-41` (polyfill class, real i18next instance).
20. `PaywallScreen.tsx:224-233` → `initialUsage` truthiness only; `const [, setUsage]` never read;
    `usageService.ts:71-74` `getUsageLimitDetail` returns `_usageLimitPayload` whole.
21. `features.ts:52` `ENABLE_EXPO_FETCH_SSE_DEFAULT = false`; `api.ts:637` REST branch;
    `api.ts:606-619` 200 `success:false` → `onError` with `{status:200, data:{code,error}}`;
    `api.ts:198-201` interceptor 429 branch is USAGE_LIMIT-only.
22. Finding texts: `full-review-tables.md:227/:228/:420`; `full-review.md:141` (W3-14 row) and
    `:117` (W1-9 row: "client half … = W3-14's 429 row"); `-verified.json` rows for the three ids
    plus the U12 unit row (extracted to scratchpad `verified_rows.json`).

---

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Adversarial re-measurement of every claim above, run in worktree `sc-w3-copy` on
2026-09-11. `git status --short` empty before and after. Verdict:
**APPROVED WITH RULINGS.** The spec's design is sound and its measured RED reasons all
reproduce. Three claims are REFUTED (R-2, R-3, R-9), six anchors or counts are stale, and
one red-test row is a tautology. Rulings 1-20 are binding and supersede the body of the
spec wherever they conflict. Nothing here requires the writer to redo the unit.

### R-1. BASE SHA IS WRONG. The unit's base is `b63a8368`, not `ed75dc70`.

Measured: `git rev-parse HEAD` -> `b63a8368b7910a946020438a5447bbcd6b792805`
(branch `feature/s65-w3-14-error-copy`, equal to `origin/main`).
`git merge-base --is-ancestor ed75dc70 HEAD` -> yes: the spec's base is an ancestor, four
merges behind (#155 W3-2, #156 W1-5, #157 W1-6, #158 W4-5, #159 brittle-403-assert).

`git diff --name-only ed75dc70 HEAD -- SmartCompareApp/` -> **EMPTY**. The entire client
tree is byte-identical, so every client claim in section 2/3b/3c/4/5 survives the move
unchanged (each was independently re-verified below).
`git diff --name-only ed75dc70 HEAD -- app/api/auth_routes.py app/middleware/error_handler.py`
-> **EMPTY**: the two backend files this unit touches or reads are byte-identical too.
Changed in between: `Procfile`, `app/api/text_routes.py` (+276), `app/main.py`,
`app/middleware/rate_limiter.py`, `app/services/feedback_service.py`,
`app/services/price_service.py`, `app/utils/async_utils.py`, `railway.json`, and four new
`tests/` files.

**Binding:** the header, section 9.1 and section 10.1 read
`b63a8368b7910a946020438a5447bbcd6b792805`.
Re-verified at the new HEAD and still true: `tsc --noEmit` exit 0 (`tsc -v` = `Version 5.9.3`);
`pytest tests/test_429_contract.py` -> **17 passed**; `ruff check --select E9,F63,F7,F82
app/api/auth_routes.py app/middleware/error_handler.py` -> `All checks passed!`;
eslint on the 7 client files -> **0 errors / 74 warnings**, exit 0; the 18-suite neighbour
baseline -> **18 passed / 233 passed / 8 todo / 0 snapshots** (identical to section 7.3);
`grep -rlE "<11 module names>" __tests__ | wc -l` -> **97**;
`ProfileScreen.togglesGated.test.tsx` -> **8** `it(` blocks.

W1-5 (`rate_limiter.py`) is a **default-OFF** `ENABLE_LIMITER_ENDPOINT_KEY` read once at
`Limiter` construction; with it off the constructor call is byte-identical and slowapi's
`"url"` default applies. `/preference-toggles` carries no path parameter, so url-keying and
endpoint-keying agree on it either way. **No interaction with this unit.**

### R-2. REFUTED -- `{"ai_sharing_enabled": "yes"}` returns **200**, not 422. B1's row is false.

Pydantic v2 lax mode coerces the *string* `"yes"` to `True`. Measured on the installed
pydantic 2.7.0 with a throwaway FastAPI app carrying the REPO's own
`http_exception_handler` + `validation_exception_handler` + the repo's `limiter`
(`.qa-w3b/probes/test_rev_w314_probe.py`, 1 passed):

```
P2 'yes'      -> 200 {'success': True, 'echo': {'ai_sharing_enabled': True,  'notifications_enabled': None}}
P3 'on'       -> 200 {'success': True, 'echo': {'ai_sharing_enabled': True,  'notifications_enabled': None}}
P3 1          -> 200 {'success': True, 'echo': {'ai_sharing_enabled': True,  'notifications_enabled': None}}
P3 false      -> 200 {'success': True, 'echo': {'ai_sharing_enabled': False, 'notifications_enabled': None}}
P3 extra key  -> 200 (unknown keys ignored; the model is not extra="forbid")
P3 'banana'   -> 422 {'code': 'VALIDATION_ERROR', 'error': 'Validation error: body -> ai_sharing_enabled: Input should be a valid boolean, unable to interpret input'}
P3 1.5        -> 422 {'code': 'VALIDATION_ERROR', 'error': 'Validation error: body -> ai_sharing_enabled: Input should be a valid boolean'}
```

**Binding:** delete the `{"ai_sharing_enabled": "yes"} -> 422` row from B1. Replace it with
`{"ai_sharing_enabled": "banana"} -> 422 code VALIDATION_ERROR` and
`{"ai_sharing_enabled": 1.5} -> 422 code VALIDATION_ERROR`. Optionally add a
**documentation** row pinning the measured coercions (`"yes"` / `"on"` / `1` -> `True`) so a
future reader does not re-derive them from docs. Do NOT add `strict=True` to buy the
original assertion: that is a behaviour choice the finding does not ask for, and the
OTA'd client only ever sends real JSON booleans.

### R-3. REFUTED (decoration) -- `toEqual` cannot pin "no key added". R1 must use `toStrictEqual`.

R1 asserts that on an envelope without the field the result "still deep-equals
`{message, code}` (no key added)". Measured on the installed jest 29.7.0
(`.qa-w3b/probes/rev_toequal.test.ts`, 1 passed):

```
toEqual({message,code,retryAfterSeconds:undefined}, {message,code})       = true
toStrictEqual({message,code,retryAfterSeconds:undefined}, {message,code}) = false
Object.keys({message,code,retryAfterSeconds:undefined}) = [ 'message', 'code', 'retryAfterSeconds' ]
```

An implementation that unconditionally writes `retryAfterSeconds: undefined` passes the
row as written. **Binding:** R1's no-field row asserts BOTH
`expect(parsed).toStrictEqual({ message, code })` AND
`expect('retryAfterSeconds' in parsed).toBe(false)`. The same applies to every
`0 / -5 / 61.5 / '61' / true -> undefined` row: assert key-absence, not `undefined`.

### R-4. REFUTED (anchors) -- the two `parseApiError` envelope branches are `:968` and `:971`.

Measured `grep -n` in `src/services/api.ts`: `923 export function parseApiError`,
**`968  if (data?.error) {`**, `969 return { message: data.error, code: rawCode };`,
**`971  if (data?.detail) {`**, `977 if (error?.message)`,
`980 return { message: 'Something went wrong', ... }`.
Section 3a's quoted listing (`966` / `967`) and section 4's "`data.error` `:966`,
`data.detail` `:969`" are both off by two. **Binding:** the branches are `:968` and `:971`.

### R-5. BINDING -- `retryAfterSeconds` is read from `data.retry_after_seconds` (top level) in BOTH branches.

Section 4 and R1 are ambiguous about where the field lives on the `data.detail` shape.
Measured: the backend only ever puts it at the TOP level of the body.
`error_handler.py:64-66` (`_build_error_response`, reached by the slowapi 429 path via
`rate_limit_handler` at `:202-227`) writes `content["retry_after_seconds"]`;
`http_exception_handler:132/141-142` (the ACCOUNT_LOCKED path) likewise writes
`content["retry_after_seconds"]`. There is **no** nested `detail.retry_after_seconds` on the
wire -- `detail.retry_after` is the *input* to `_detail_retry_after`
(`error_handler.py:94-110`, not `:105-110` as section 3a says) and is consumed server-side.

**Binding:** the implementation reads `data?.retry_after_seconds` in both the `:968` and
`:971` branches. R1's "legacy `data.detail` shape" row is therefore
`{ response: { status: 429, data: { detail: {...}, retry_after_seconds: 61 } } }` ->
`retryAfterSeconds === 61`. Guard exactly as `_detail_retry_after` does:
`typeof v === 'number' && Number.isInteger(v) && v > 0` (a JS boolean is not
`typeof 'number'`, so `true` is rejected by the typeof alone -- keep the row anyway).

### R-6. CONFIRMED -- the i18next mechanism holds on the INSTALLED version, with the base key kept.

The repo has **no precedent** for a base key coexisting with plural siblings
(`home.savings.count` has all six siblings and **no** base key -- measured
`'home.savings.count' in en === false`), so this was re-measured rather than trusted.
`.qa-w3b/probes/rev_i18next.test.ts` (1 passed) runs the app's EXACT init options from
`src/i18n/index.ts:31-41` (default `keySeparator` / `ignoreJSONStructure`, flat dotted keys)
on i18next **26.1.0** over the real catalogs plus injected siblings:

```
BASE value            = "Plenty of compares in flight - give it a moment, then tap."
en no opts            = <base>          en {count:undefined} = <base>
en {count:0}  = "EN_ZERO 0"   en {count:1} = "EN_ONE"   en {count:2} = "EN_OTHER 2"
en {count:42} = "EN_OTHER 42"           en {count:61} = "EN_OTHER 61"
en NOBASE no opts     = "zz.nobase"   (siblings without a base key return the KEY)
en home.errors.comparison {count:42}  = <its own sentence>   (no siblings -> count ignored)
ar 0/1/2/3/11/61/100 = ZERO/ONE/TWO/FEW/MANY/MANY/OTHER
ar no opts / {count:undefined} = <base>
```

Three consequences, binding:

* **Keeping the base key is REQUIRED, not optional.** `en NOBASE no opts = "zz.nobase"` --
  drop the base and every field-absent 429 renders the raw key string on screen.
  Section 4's "The BASE key stays in both" is now a hard requirement; say so in the PR.
* **English honours `_zero`.** `en {count:0} -> EN_ZERO`, even though CLDR-en has no zero
  category. Harmless here only because R1 pins `0 -> undefined`, so `count` is never 0.
  Keep that R1 row; it is what makes the `_zero` sentence unreachable.
* **R2's "ar 1/2/3/11/61 yields >= 4 distinct" is at its boundary, not above it.**
  Measured ar 11 and ar 61 are BOTH `many`. Those five counts yield exactly **4** distinct
  strings. Write the assertion as `>= 4` (as section 5 does) and add
  `expect(ar(3)).not.toBe(ar(11))` plus `expect(ar(1)).not.toBe(ar(2))` so it cannot pass on
  a 2-form catalog.

### R-7. CONFIRMED -- the copy fence, with two mechanics the red phase must not re-derive.

`__tests__/copy-policy.test.ts:171-186`: the EN scary check is
`visible.toLowerCase().includes(term.toLowerCase())` -- **case-INSENSITIVE**, so `Failed to`
also blocks `failed to`. `visibleCopy()` (`:91-93`) **strips `{{...}}` before checking**, so
`{{count}}` can never itself trip a pattern. `.copy-policy.json` measured:
`scary_vocab_en = ["couldn't","try again","Failed to"]`,
`scary_vocab_ar = ["tazur","fashal","taqdir","muqaddar"]` (the four Arabic literals as
stored). The proposed en/ar sentences in section 4 clear all seven. **Binding:** R2 reads
both arrays from `.copy-policy.json` at runtime (as section 5 says) and must lowercase the
EN comparison.

### R-8. CONFIRMED -- the i18n fences leave `profile.toggle.disabledReason` genuinely free.

`__tests__/i18n/no-deleted-keys.test.ts` pins exactly: `results.whatsNext` absent (plus no
nested variant), `results.save` absent, `Object.keys(en).length === Object.keys(ar).length`
(`:60-65`), and `results.whyWePicked` + `results.runnerUpWins` **present** (`:67-75`) --
nothing else. `__tests__/i18n/no-missing-referenced-keys.test.ts` extracts only literal
`t('key')` / `t("key")` from `src/` and asserts referenced is a subset of en; it never
asserts the converse, so an unreferenced catalog key is fine. Section 4's corrected
rationale is **upheld**: keep or delete, both stay green. **Binding:** keep it (smaller diff)
and say so in the PR. Key counts 915 -> 923 in both files (6 siblings +
`common.errors.rateLimited` + `common.errors.locked`), 0 deletions -- measured en 915 /
ar 915, `common.errors.*` = `[]` today.

### R-9. REFUTED (self-contradictory) -- R5(iii) cannot assert both halves in one render.

Measured `ProfileScreen.tsx:233`:
`const notificationsEnabled = preferences?.notifications_enabled !== false;`
-- for `preferences === null` AND for a row without the key this is **true**, so the master
starts ON. `:543` renders the sub-toggles only while `notificationsEnabled && !togglesGated`.
Flipping the master to **false** (R5(iii)'s first half) therefore **unmounts** the three
sub-toggles R5(iii)'s second half wants to see.

**Binding:** split R5(iii) into two ordered assertions inside one render, in this order:

* (iii-a) with no priorities and the gate gone, `UNSAFE_getAllByType(Switch)` has length
  **5** (AI master + notifications master + 3 subs) and each sub row's
  `accessibilityState.disabled === false`;
* (iii-b) THEN `fireEvent(masterSwitch, 'valueChange', false)` -> `putPreferenceToggles`
  called once with exactly `{ notifications_enabled: false }`, and the sub-toggles unmount
  (`UNSAFE_getAllByType(Switch)` back to 2).

Do not assert (iii-b) before (iii-a).

### R-10. CONFIRMED -- every other measured RED reason reproduces at `b63a8368`.

The writer's probes were re-run verbatim (`w314_measure.test.tsx` + `w314_profile.test.tsx`,
2 suites / 8 passed) and the backend probe (`test_w314_probe.py`). Reproduced exactly:

```
parseApiError(slowapi 429) keys = [ 'message', 'code' ]                    -> R1 red
classifyLoadFailure(429 RATE_LIMITED) = generic ; (429 no code) = generic  -> R4 red
(b1) AI row accessibilityState = {"checked":false,"disabled":true}; savePreferences calls = 0
     after row press AND after Switch.onValueChange(true); captions rendered = 1; Switch count = 2
(b5) {ai_sharing_enabled:false, notification_types:{}} -> disabled:true, 0 PUTs
(b2) PUT body = {"priorities":["quality"],...} ; rendered = "Validation error: body -> lifestyle -> 0: Input should be ..."
(b3) rendered = "Failed to save preferences"      (trips scary_vocab_en "Failed to")
(b4) rendered = "Request failed with status code 502"
```

Independently re-located at HEAD and quoted: `HomeScreen.tsx:436` (`onError:`), `:482`,
`:573` (both `Alert.alert(t('common.error'), t(friendlyErrorKey(parsed.code)));`);
`HistoryScreen.tsx:708` `setLoadError(true)`, `:909-910`
`t('history.loadError.title'/'body')`;
`ProfileScreen.tsx:129/131-143/145/156/160/168/179/183/216/219-220/225-227/233/249-250/281-283/295/298/489-505/512-513/519-541/543/567-573`;
`ResultsScreen.tsx:237/245/247/328-329/580-581`; `EditProfileScreen.tsx:140`;
`PaywallScreen.tsx:224 initialUsage`, `:226 const [, setUsage]`, `:230-233` (truthiness only
-- **item-12 drop UPHELD**); `features.ts:52 = false`; `api.ts:198-201` (429 branch is
USAGE_LIMIT-only), `:455-473` (`getPreferences`; the bare `catch { return null; }` is
**`:471-473`**, not `:472-474`), `:504-509` (`putReengagementSubs`), `:606-619`, `:637`;
`ToggleRow.tsx:44-46` (`accessibilityRole="switch"`,
`accessibilityState={{checked, disabled:!!disabled}}`, `accessibilityLabel ?? label`);
backend `auth_routes.py:9` (imports `BaseModel, EmailStr, Field, field_validator` -- **no**
`model_validator`), `:10` (**`Optional` IS already imported**), `:183-184`, `:763`,
`:819-820`, `:859-860`, `:938` (no limiter), `:1052-1053`, `:1131-1132`;
`error_handler.py:31 429:"RATE_LIMITED"`, `:64-66`, `:94-110`, `:113`, `:132`, `:141-142`,
`:202` `rate_limit_handler`; `main.py:149-151` registers all three handlers.

### R-11. CONFIRMED -- the backend model design works, and there is an IN-REPO precedent the spec missed.

`.qa-w3b/probes/test_rev_w314_probe.py` mounted the spec's exact `PreferenceTogglesBody` on a
throwaway app with the repo's real handlers:

```
P1 {}                          -> 422 {'code':'VALIDATION_ERROR','error':'Validation error: body: Value error, provide ai_sharing_enabled and/or notifications_enabled'}
P3 {"ai_sharing_enabled":null} -> 422 {'code':'VALIDATION_ERROR', ... same ...}
P4 first 429 on call #11 for a 10/minute limit
```

`@model_validator(mode="after")` raising `ValueError` **does** surface as 422 /
`VALIDATION_ERROR` through `validation_exception_handler`, and the "11th call" arithmetic in
B1 is right. **Precedent the spec should cite instead of introducing the pattern cold:**
`app/api/text_routes.py:13` already does
`from pydantic import BaseModel, Field, model_validator` and `:240-252` is a
`@model_validator(mode="after")` raising `ValueError`. Same repo, same handler chain.
**Binding:** cite it in section 4.

Caveat on B1's 429 row: my throwaway app deliberately did NOT register
`RateLimitExceeded -> rate_limit_handler`, so its 429 came back as slowapi's bare
`{'detail': '10 per 1 minute'}` with no `Retry-After`. The REAL app registers it
(`main.py:151`), and `rate_limit_handler` (`error_handler.py:202-227`) routes through
`_build_error_response`, which maps 429 -> `code: "RATE_LIMITED"` (`STATUS_CODE_MAP:31`) and
emits `retry_after_seconds` + `Retry-After` from the same single value. B1 must therefore be
written against `app.main.app` (as section 5 says), never a hand-built app -- a hand-built
app silently loses the envelope and the row would pass for the wrong reason.

### R-12. BINDING -- stale gate counts and one false gate claim in section 7.8.

Measured at HEAD: `grep -rlE "auth_routes" tests/ | wc -l` -> **40** (spec says 39);
`grep -rl "SmartCompareApp" tests/ | wc -l` -> **10** (spec says 9). The 10 are:
`test_b2_strict_optional_auth.py`, `test_comparison_id_echo.py`,
`test_events_allowlist_superset.py`, `test_feature_bucket_parity.py`,
`test_feedback_allowlist_superset.py`, `test_migration_037_security_definer_grants.py`,
`test_paid_route_metering.py`, `test_review_paraphrase.py`, `test_security_regression.py`,
`test_timeout_partial_integration.py`.

**`test_endpoint_shapes_vs_jsx.py` is NOT among them** -- section 7.8's claim that it "is one
of them and the new client route call is exactly what it reads" is **false**. What it
actually does (`:451-486`): walks the route table and requires a manifest entry only for
**GET** routes under `/api/v1/home/` or `/api/v1/profile/`. A `PUT` under `/api/v1/auth/`
needs **no** manifest entry and cannot trip it. Keep the file in the gate run (it imports the
app), but drop the claim. The file that genuinely reads the client is
**`tests/test_security_regression.py`**, which `read_text()`s
`SmartCompareApp/src/services/api.ts` (`:527`, `:554`), `authService.ts`
(`:516/:538/:559`), `certificatePinning.ts` (`:545`) and walks `SmartCompareApp/src`
(`:503`) -- **that** is the suite an `api.ts` edit must clear.
**Binding:** section 7.8 reads 40 / 10, names `test_security_regression.py` as the
api.ts-reading gate, and drops the `test_endpoint_shapes_vs_jsx.py` sentence.

### R-13. BINDING -- item-12's four backend anchors moved at HEAD (documentation only).

`text_routes.py:244-252` at `ed75dc70` was the USAGE_LIMIT raise; at `b63a8368` that range is
`TextCompareRequest.normalize_shape`. Measured `grep -n '"tier"' app/api/text_routes.py` ->
**`:361`, `:559`, `:727`, `:1018`** (spec says `:244-252`, `:411-412`, `:562-563`,
`:780-781`). The DROP itself is upheld (`PaywallScreen.tsx:224-233` re-verified:
`initialUsage` truthiness only, `const [, setUsage]` never read).
**Binding:** section 2's item-12 row and section 10 cite the new line numbers, or drop line
numbers and cite `grep -n '"tier"' app/api/text_routes.py`.

### R-14. BINDING -- name the commit this unit REVERSES. The F-S1.5i gate is not incidental.

`git log -S togglesGated -- SmartCompareApp/src/screens/ProfileScreen.tsx` ->
**`dbf152d9` "fix(s1/editprefs): root-cause empty-priorities 422 + ProfileScreen toggle
gating"** (2026-05-28, ancestor of HEAD). Its message states it came from **Ahmed's own S1
round-2 device walkthrough**, names this exact root cause, and lands three surfaces:
**A** `getPreferences` null-and-empty coercion, **B** EditPreferencesFlow Continue gating,
**C** ProfileScreen toggle gating. It explicitly chose "FE only, backend invariant preserved".

This unit reverses **surface C only** and keeps A and B (verified: section 4 leaves
`getPreferences` and `EditPreferencesFlow` untouched). That is the correct call -- the
finding's whole complaint is that C makes a privacy control unreachable, and `dbf152d9` had
no backend route available to it. But a shipped, device-driven decision is being reversed,
and the spec never says so. **Binding:** sections 2, 4 and 9 name `dbf152d9`, state that
surfaces A and B are RETAINED and only C is reversed, and state that the reversal is only
sound *because* the new additive route removes the `min_length=1` constraint from this path.

Correct one sub-claim while doing it: section 4 says "the sub-toggles never needed the gate
-- the gate was over-broad". `228ff63` (2026-05-23, the `/reengagement-subs` route)
**predates** `dbf152d9` (2026-05-28), and `dbf152d9`'s own prose says all five toggles were
gated deliberately. The substantive claim still holds and is measured --
`update_reengagement_subs` (`auth_routes.py:1052-1104`) reads and writes only
`preferences.notification_types` and never touches `priorities`, so it cannot 422 on empty
priorities -- but state it as **measured from the route**, not as "the gate was over-broad".

### R-15. BINDING -- the m18 regex replacement must be newline-tolerant.

`ResultsScreen.networkMatrix.m18.test.ts:101-106` is today
`/Alert\.alert\(\s*t\('common\.error'\),\s*t\(friendlyErrorKey\(parsed\.code\)\)\s*\)/g` with
`expect(coded.length).toBe(2)`. Adding `, { count: parsed.retryAfterSeconds }` pushes both
calls past the print width, so prettier / eslint will wrap them across lines.
**Binding:** the replacement regex uses `\s*` at every join (including inside the object
literal) so it matches a wrapped call, and the red phase verifies `coded.length === 2`
against the ACTUAL formatted source, not against a hand-written one-liner. The sibling test
at `:109-142` (comment-stripped, paren-balanced,
`/(parsed|error|err)\??\.message/`) is unaffected -- `parsed.retryAfterSeconds` contains no
`.message` -- and stays UNCHANGED as a preserve pin.

### R-16. BINDING -- R3's count-aware `t` mock is a tautology unless anchored twice.

R3 proposes a hand-rolled `t` that resolves `key + '_one' / '_other'` and then asserts the
body equals `EN['home.errors.rateLimited_other'].replace('{{count}}','42')`. That reads the
fix's own catalog entry back through the test's own suffix logic -- it would pass even if
real i18next resolved differently. The real proof lives in **R2** (real i18next instance,
real catalogs, R-6 above) and the real call-site proof lives in the **R-15 m18 regex**
(source contract). **Binding:** keep R3, but (a) R3 must also assert
`body !== EN['home.errors.rateLimited']` (the base sentence) on the with-field rows, which is
the only thing the mock cannot fake, and (b) section 5 must state in R3's own text that R2
plus the m18 regex are its anti-tautology anchors, so a future reader does not mistake R3 for
the proof of plural resolution.

Confirmed and unchanged: the a11 harness's `t` mock
(`HomeScreen.errorCopy.a11.test.tsx:188-197`) ignores `opts` entirely
(`if (catalog[key] !== undefined) return catalog[key];`) and its inlined `parseApiError`
(`:79-97`) never returns the new field, so `HomeScreen.errorCopy.a11.test.tsx:304-322` stays
green with no edit after the `{ count }` change. Re-verified in the 18-suite run.

### R-17. RULING -- NO `ENABLE_*` FLAG. The additive route ships unflagged. Fallback NOT taken.

The campaign rule is "backend behaviour changes go behind a default-OFF `ENABLE_*` flag read
per call; **additive-only otherwise**". Measured: every existing route is byte-identical
(`git diff` on `auth_routes.py` will show one new model plus one new handler and nothing
else), so this is additive-only and the rule's own exemption applies. Two further reasons,
both measured: (1) the route's ONLY caller is the OTA'd client, so a default-OFF flag would
make a privacy toggle return 503 `FEATURE_DISABLED` until Ahmed flips it -- the flag would
*cause* the outage it exists to prevent; (2) the precedent `228ff63`
(`PUT /reengagement-subs`, ancestor of HEAD) shipped the identical shape unflagged.
**Binding: no flag.** The `ENABLE_PREFERENCE_TOGGLES` fallback in section 4 is NOT taken;
leave it documented as a rejected alternative, do not implement it.

Compatibility re-verified against the two hazards this campaign has been bitten by:

* **Phones on `97b5f15` are untouched** -- that bundle has no `putPreferenceToggles`, so it
  never calls the new path, and no existing route or response shape changes.
* **OTA'd client vs a backend without the route** cannot happen by ordering (backend deploys
  on merge, OTA is later), but is handled anyway: measured probe B3 -> bare Starlette
  `404 {"detail":"Not Found"}` -> `parseApiError` -> `{message:'Not Found', code:null}` ->
  `settingsErrorKey(null, fallback)` -> neutral copy plus optimistic rollback. **R5(iv) must
  keep that exact row.**
* **No hidden dependency.** The diff is `.ts` / `.tsx` / `.json` catalogs plus one `.py`. No
  `package.json` / lockfile change, no `app.json`, no plugin, no native dep, no new secret, no
  env var, **no migration** (038 is not needed -- the route writes the existing
  `users.preferences` JSON column), no store setting. Client half OTA-safe; backend half
  deploys on merge.

### R-18. BINDING -- small anchor and wording corrections, no design impact.

* `_detail_retry_after` is `error_handler.py:94-110` (section 3a says `:105-110`).
* `getPreferences`'s bare catch is `api.ts:471-473` (section 3d says `:472-474`).
* `EditProfileScreen.bundleE.s3.integration.test.tsx`: `const mockApiDelete` is `:31`; the
  `delete: (...args) => mockApiDelete(...args)` mapping is `:39`; the delete drive R6 clones
  is `:253-266`. Section 5's "mockApiDelete at `:39`" means the mapping line -- say which.
* `ProfileScreen.tsx:227` is `Alert.alert(t('profile.notifs.errorTitle'), msg);` and
  `:220` / `:226` are the two `setNotifsError(msg)` calls -- confirmed, keep section 3c's
  list as written.
* `Screens.bundleD.contract.test.ts:129-133` confirmed: the regex requires `savePreferences`
  **and** `putReengagementSubs` in ProfileScreen's api import. Since section 4 drops
  `savePreferences` from that import (`:63`), this test goes RED if not updated -- section 4
  is right to list it.
* `ProfileScreen.optimistic.test.tsx` re-verified as comment-only risk: its assertions are all
  about `putReengagementSubs` (`:35-62`) plus a runtime body-shape check (`:66-105`); the only
  `savePreferences` occurrence is prose at `:16`. `ProfileScreen.aiSharingDefault.test.tsx` is
  a pure source-pattern suite (`:26-42`) and is unaffected. Both stay green.
* `ProfileScreen.bundleE.s3.integration.test.tsx:301-317` confirmed: it asserts
  `getByText('Pick your priorities first')`. It MUST be deleted or inverted -- section 4 is
  right.

### R-19. BINDING -- B1 asserts codes and ranges, never Pydantic message text.

Local backend drift is real and re-measured: python 3.12.9; pydantic **2.7.0** installed vs
**2.13.4** pinned (`requirements.txt:109`), fastapi **0.115.0** vs **0.141.1** (`:47`),
slowapi **0.1.9** vs **0.1.10** (`:144`), starlette **0.38.6** vs **1.6.0** (`:150`). The 422
strings quoted in section 3d and in R-2 above are 2.7.0 wording. **Binding:** every B1
assertion is on `response.status_code` and `body["code"]`, on `retry_after_seconds` being
`isinstance(v, int) and not isinstance(v, bool) and 0 < v <= 61` and
`== int(headers["Retry-After"])`, and on the mock's recorded `update()` payload -- never on a
Pydantic sentence. The already-green regression pin (`PUT /preferences` with
`priorities: []` -> 422, `save_user_preferences` not awaited) keeps that discipline too.

### R-20. RULING -- scope is honest; the open questions are settled as follows.

The already-green drops were verified honestly and each one reproduces (R-10): Home text
path, Home URL path, HistoryScreen, the W1-9 backend half, item 12, and (b)-as-worded.
Nothing red was dropped; nothing green was kept. The plan row (`full-review.md:141`) and the
two finding rows (`full-review-tables.md:227/:228`) were re-read and match the spec's
characterisation, including the plan's own stale anchors (`HomeScreen.tsx:470`, and
`src/utils/failureClassification.ts`, which does not exist -- the file is
`src/services/failureClassification.ts`, 57 lines, re-read in full). The plan explicitly
sanctions "backend `auth_routes.py` or single-purpose preference routes", so the backend half
is in scope and not creep.

Settling section 8's open questions so the red phase asks nothing:

1. **`HomeScreen.tsx:432` / `:540` (HTTP-200 `success:false` arms rendering `data.error`
   raw): NOT in this diff.** Ruled out. Measured out of the 429 finding's reach and it is
   W4's `str(e)`-as-user-facing-error class, owned by another session. Re-file, do not fold
   in.
2. **`profile.toggle.disabledReason`: KEEP in both catalogs** (R-8). Smaller diff; every
   fence green either way; PR says so explicitly.
3. **No flag** (R-17). Settled, not an open question.
4. **Item 12: stays dropped** (R-13). The product call on whether the Paywall renders
   remaining credits is Ahmed's and is non-blocking.
5. `PUT /password` 400 raw English, the Login / Register / ForgotPassword raw `.message`, and
   the `run_db` offload for the new route plus its precedent: all correctly deferred to
   separate units. Leave section 8 as written.

**READY FOR RED: yes**, once R-2, R-3, R-5, R-9, R-15 and R-16 are folded into the test
bodies and R-1, R-4, R-12, R-13, R-14, R-18 into the prose. No further measurement is owed.

### Review probes (gitignored, re-runnable)

* `.qa-w3b/probes/rev_i18next.test.ts` -- i18next 26.1.0 base-plus-siblings on the app's
  exact init.
* `.qa-w3b/probes/rev_toequal.test.ts` -- jest 29.7.0 `toEqual` vs `toStrictEqual` on an
  undefined-valued key.
* `.qa-w3b/probes/test_rev_w314_probe.py` -- `model_validator` -> 422 through the repo's real
  handlers, the pydantic bool-coercion table, and the 10/minute trip point.

Client probes: from `SmartCompareApp`,
`node node_modules/jest/bin/jest.js --ci --roots ../.qa-w3b/probes --testMatch "**/rev_*.test.ts" --modulePaths C:/Users/SynAckITPC/Documents/AI/sc-w3-copy/SmartCompareApp/node_modules`.
Backend probe: from the worktree root,
`PYTHONIOENCODING=utf-8 python -m pytest .qa-w3b/probes/test_rev_w314_probe.py -q -s -p no:randomly -p no:cacheprovider`.

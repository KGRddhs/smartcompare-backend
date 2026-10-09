# U3B - AI consent v2 + toggle removal (D3 = C: OpenAI sharing ON for all, disclosed, no per-user switch)

Session 75, 2026-10-09. Base: main 4c0f3c99 (every file:line below is at that sha). Rulings: FABLE_RULINGS_S74_OPENAI.md OA2/OA3,
DECISIONS_ACCEPTED_2026-10-08.md:7 (D3=C), pre-rulings U1-U6 in the brief. Parent spec: 2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md R4 (D3=A structure) + T3 A.
AR strings: scratchpad/specs/U3B_AR_COPY.txt (UTF-8; never printed). Client half is unflagged, OTA-capable and MUST be in the store binary.

## 0. Scope and non-goals
In: remove the Profile "Help improve AI quality" toggle, its state/handlers/keys/types; add ONE disclosure sentence to the consent sheet body (EN+AR);
AI_CONSENT_VERSION 1 -> 2 with the sha256 fence re-pinned; delete select_client_for_user and the OPENAI_API_KEY_PRIVATE branch (backend); one inventory line.
Out: legal text (app/legal, landing/ = U8 PR #330), any server consent record (R3 stays client-only), the onboarding Step 5 card (OA2: lists what is sent, not the use),
App Privacy answers (LISTING-TRUTH), the DB column users.preferences.ai_sharing_enabled (stays, inert), store=False (U3c; dashboard logs only, unrelated to sharing - U6),
any new flag, any change to what is sent to OpenAI.

## 1. Measured base (main 4c0f3c99)
Client toggle - SmartCompareApp/src/screens/ProfileScreen.tsx: :53 `Shield` import (only use :504); :106-107 aiSharingSaving/aiSharingError state; :138-140 comment +
`aiSharingEnabled = preferences?.ai_sharing_enabled ?? false`; :149 `ai_sharing_enabled: previous?.ai_sharing_enabled` in buildNextPrefs; :156-182 comment + handleAiSharingToggle
(putPreferenceToggles({ ai_sharing_enabled }), errors via settingsErrorKey(..., 'profile.aiSharing.errorSave') :172,:177); :309 the PASSWORD catch borrows
'profile.aiSharing.errorSave' as the fallback key (unreachable: the ternary enters only on RATE_LIMITED/ACCOUNT_LOCKED, for which settingsErrorKey never returns the fallback,
src/services/errorCopy.ts:109-118); :502-512 `<View style={styles.flatRowToggleHost}>` + ToggleRow(label profile.aiSharing.title, subtitle .subtitle, value, onValueChange, disabled)
+ error Text; :513 the notifications host already carries flatRowToggleHostLast (:740-746 styles). No other client file renders the toggle.
Client types/API: src/services/api.ts:588-592 comment names the "AI-sharing opt-out", :594 PreferenceTogglesBody.ai_sharing_enabled, :600 response field;
src/types/types.ts:557 UserPreferences.ai_sharing_enabled. Zero other src/ references (grep ai_sharing|aiSharing over SmartCompareApp minus node_modules).
Catalogs: en.json:431-433 and ar.json:428-430 = profile.aiSharing.{title,subtitle,errorSave}; 1007 keys each, key sets equal. Consent copy: en.json:704-708,
ar.json:701-705 (title, body, link, agree, notNow); body EN 384 chars / 3 sentences, AR 336 chars / 3 sentences, each ending with the "not sent" sentence.
onboarding.s5.privacy_anon_body en.json:576 (UNCHANGED).
Consent module: src/services/aiConsent.ts:44 `AI_CONSENT_VERSION = 1`; :74-75 hasCurrentAiConsent = strict `record.version === AI_CONSENT_VERSION`; :79-81 recordAiConsent writes
{version, at} under `@qaren_ai_consent_<userId>` (:46-54; same key per user, so a v2 Agree overwrites the v1 record: no migration); :112-118 ensureAiConsent; :36-38 header
comment says the sheet must not promise an opt-out because the toggle routes nothing. Sheet: src/components/AiConsentSheet.tsx:52 renders t('aiConsent.body') in one Text
inside a Modal card (styles :95-144: paddings only, no maxHeight/ScrollView).
Fence: __tests__/consent/aiConsentVersion.s69.test.ts:32-35 PINNED {version: 1, sha256: cafab3ffe656d44c03ac82120b40514278c8337e29e632d0f6bb57e9b5c95ae2}; :37-43 hashes
EXACTLY [EN['aiConsent.title'], EN['aiConsent.body'], AR['aiConsent.title'], AR['aiConsent.body']].join('\n') as utf8 (no trailing LF; flat keys). Recomputed in Python
over the catalogs at main: identical (deterministic). __tests__/setup.ts:18-40 global granted mock with `AI_CONSENT_VERSION: 1` at :20.
i18n fences a key removal can redden: __tests__/i18n.test.ts:8 (EN==AR key sets); __tests__/i18n/no-deleted-keys.test.ts:64 (equal key COUNTS); __tests__/i18n/
brand.myez.s69.test.ts:58-89 BRAND_KEYS lists 'profile.aiSharing.subtitle' (:69) and :143-156 pin "en values carrying MYEZ == BRAND_KEYS" and "ar values with standalone
MYEZ_AR == BRAND_KEYS", :186 `countMatches(all AR, MYEZ_AR_WORD) === BRAND_KEYS.length` (one standalone brand per brand key: the new sentence must NOT repeat the brand);
__tests__/i18n/no-missing-referenced-keys.test.ts walks src/ only; __tests__/copy-policy.test.ts:96-130,157-200 scans every en/ar value (.copy-policy.json banned_*/scary_*);
__tests__/onboarding/step05Trust.s69.test.tsx:64 OPT_OUT_EN = /opt[\s-]?out|turn (it )?off|switch (it )?off|toggle|disable|settings/i (Step 5 card only; reused below).
Profile tests the removal reddens: __tests__/ProfileScreen.aiSharingDefault.test.tsx (54 lines, 3 source-pin nodes on `ai_sharing_enabled ?? false`);
__tests__/Screens.bundleD.contract.test.ts:151-154 same pin; __tests__/ProfileScreen.bundleA.test.tsx:34-37 `<ToggleRow` count >= 5; __tests__/ProfileScreen.toggles.w314.test.tsx
(:113 AI_LABEL = EN['profile.aiSharing.title']; :186-191 mount() waits on getByLabelText(AI_LABEL) so EVERY node depends on it; :173 errorLines list; :205-219 AI describe (2 nodes);
:222-256 counts 5 switches then 2, master at index [1]; :259-320 counts 2 switches, master at [0]..[1]; :322-357 AI failure describe; :360-384 two AI nodes; :385-536 notifications/
password/preserve nodes use mount() + indices); __tests__/ProfileScreen.bundleE.s3.integration.test.tsx:238-275 two AI nodes (switches[0]), :317-343 "5 switches" + AI flip;
__tests__/ProfileScreen.logoutCopy.b6.test.tsx:162 and toggles.w314:128,:198 pass ai_sharing_enabled in untyped jest.fn() fixtures (runtime-harmless). __tests__/errorCopy.w314.test.ts:80-81
uses the key as an opaque string (stays green).
Backend: app/services/openai_service.py:7 `import os` (its ONLY use is :71); :40-45 cache comment + `_client_cache: Dict[bool, AsyncOpenAI]`; :48-79 get_client(use_shared_project=True)
with the private arm :69-77 (`os.getenv("OPENAI_API_KEY_PRIVATE") or os.getenv("OPENAI_API_KEY")`); :82-91 select_client_for_user (reads user_prefs["ai_sharing_enabled"]).
Callers: get_client() no-arg at :326,:398,:463; select_client_for_user has ZERO callers in app/ (grep); no app/ call passes use_shared_project. Typing imports: Dict/Any/Optional
stay used elsewhere (:293-:430). Tests naming the branch: tests/test_auth_ai_sharing_toggle.py (156 lines; :27-63 3 UserPreferencesRequest shape nodes KEEP; :71-124
TestSelectClientForUser 5 nodes; :131-156 TestGetClientFactory 2 nodes, :153-154 call get_client(use_shared_project=...)); tests/test_llm_provider_base_url.py:264-269 and
:471-477 call get_client(use_shared_project=True/False) and monkeypatch _client_cache to {}; tests/test_m18_openai_tpm_sizing.py:112-119 saves/clears/updates _client_cache AS A DICT;
tests/test_backend_cleanup.py:172-200 test_unused_imports_cleaned: if 'import os' is in the module source, some `os.<attr>` must be referenced; tests/test_conftest_env_safety.py:72
and tests/_env_safety.py:117 list the NAME OPENAI_API_KEY_PRIVATE in guard lists (keep). Route: app/api/auth_routes.py:218-219 UserPreferencesRequest.ai_sharing_enabled with a
"False = opt out (private project)" comment; :1414-1433 PreferenceTogglesBody (docstring :1415-1421 names the "AI-sharing (PDPL) opt-out" - a Pydantic docstring = OpenAPI text);
:1436-1484 update_preference_toggles stores both keys (:1462-1464) and echoes them (:1483). OpenAPI baseline: tests/fixtures/s71_u13_flag_off_baseline.json:1217,:1284,:1709 carry
these schemas/docstrings and tests/test_s71_u13_compare_auth_required.py:489 compares app.openapi() -> NO docstring or Field edits in auth_routes.py. Existing route pins that
already prove old clients keep working: tests/test_auth_preference_toggles_w314.py::TestPreferenceTogglesWrites::test_ai_sharing_off_on_empty_preferences_row (:152),
::test_both_keys_in_one_body (:203), ::TestPreferenceTogglesValidation::test_documented_lax_coercions_write_true (:273). CI baseline tests/.pre_impl_failures.txt names none
of the touched nodes. Inventory: docs/privacy-data-inventory.md has NO line mentioning OpenAI/train (grep): rows 1-13 (:31-43) are parsed by nativeBundle.w37.test.ts c5
(:715-745: only lines matching /^\|\s*\d+\s*\|/ inside "## Collected data types", section ends at the next "\n## "), c3 reads the first json fence; row 3 (:33 PhotosorVideos),
row 4 (:34 OtherUserContent: typed product text), row 12 (:42 preferences) are the compare inputs. CLAUDE.md:19,:560 mention select_client_for_user (docs checkpoint, not U3b).

## 2. Target
T-A Sheet copy (EN, en.json:705 aiConsent.body). Insert, between the current second sentence ("...your country, language and area.") and the final sentence
("Your name, email and account details are not sent."), exactly this sentence:
  OpenAI may use these inputs and the outputs it generates from them to identify usage patterns, measure model quality and inform the evaluation and training of its models.
New EN body = S1 + " " + S2 + " " + NEW + " " + S3 (555 chars, 4 sentences). AR (ar.json:702): the same insertion before the AR final sentence; the sentence is section 1 of
U3B_AR_COPY.txt and the full value is section 2 (482 chars; [SPEC] tag; native review required). The brand is NOT repeated in either language (A2). Title/link/agree/notNow unchanged.
T-B Version: aiConsent.ts:44 `AI_CONSENT_VERSION = 2`; reword :36-38 (the toggle is gone; the sheet discloses the programme and promises no opt-out). Every user is re-asked
once (strict equality :74-75; v1 records are overwritten by the next Agree). __tests__/setup.ts:20 `AI_CONSENT_VERSION: 2` (the mock keeps granting). Fence re-pin
(aiConsentVersion.s69.test.ts:32-35): PINNED = {version: 2, sha256: '372c50484085fa859a576a62367c743365735fab6dda31f336552a4ae2a21a02'} - computed over the target strings
with the fence's own formula; GREEN re-derives it with the node -e one-liner in that file's header (run from SmartCompareApp/) and MUST get the same hex, else the strings differ.
T-C Toggle removal (ProfileScreen.tsx): delete :53 Shield import, :106-107, :138-140, :149, :156-182, :502-512 (the whole AI host View); the notifications host :513 keeps
`[styles.flatRowToggleHost, styles.flatRowToggleHostLast]` (unchanged); :309 fallback key -> 'common.error' (A6). Delete en.json:431-433 and ar.json:428-430 (3 keys each ->
1004/1004, sets equal). api.ts: delete :594 and :600, reword :588-592 to name only the notifications master; types.ts: delete :557. ai_sharing_enabled then appears nowhere in src/.
T-D Backend (openai_service.py): delete :7 `import os`; replace :40-45 with a 2-line comment + `_client_cache: Dict[str, AsyncOpenAI] = {}` and `_CLIENT_KEY = "default"`;
`def get_client() -> AsyncOpenAI:` memoises one AsyncOpenAI(base_url=provider_base_url(), timeout=httpx.Timeout(120.0, connect=30.0), max_retries=openai_max_retries()) under
_CLIENT_KEY (the shared arm :62-67 verbatim; the private arm :69-77 and the parameter go); delete :82-91. Grep fence: no .py under app/ contains select_client_for_user,
OPENAI_API_KEY_PRIVATE or use_shared_project, and the only app/ file naming ai_sharing_enabled is app/api/auth_routes.py.
T-E Route for old bundles (auth_routes.py): PUT /auth/preference-toggles and PUT /auth/preferences KEEP accepting ai_sharing_enabled (phones on older bundles send it);
the value is stored and echoed exactly as today and READ BY NOTHING (inert). Only the `#` comment at :218-219 changes ("accepted for older bundles; inert since U3b (D3=C)").
No docstring/Field/validator edit (OpenAPI baseline). T-F Inventory: after the table (:43) add one blank line and ONE bullet before "## Not collected":
"- **Used to train AI models: YES** for the comparison inputs of rows 3, 4 and 12 that ride a compare (photos; typed product names, links and their page text; the preference
fields named by the consent sheet) and for the comparison text OpenAI returns: the organisation participates in OpenAI's data-sharing programme (owner decision D3 = C,
2026-10-08; rulings OA2/OA3), so OpenAI may use those inputs and outputs to identify usage patterns, measure model quality and inform the evaluation and training of its models.
Tracking stays false; `store=False` on every chat call (U3c) only keeps dashboard logs empty. The App Privacy answer itself is LISTING-TRUTH (out of U3b)." (pure ASCII).

## 3. Tests
NEW __tests__/consent/aiConsentV2.s75.test.ts (jest.mock aiConsent -> jest.requireActual, jest.mock authService getSavedUser, repo AsyncStorage mock; EN/AR via require of
the catalogs; the AR sentence as ASCII \u escapes produced with python encode('ascii','backslashreplace') from U3B_AR_COPY.txt section 1; file byte-checked 0 non-ASCII):
 V1 RED  AI_CONSENT_VERSION === 2.
 V2 RED  a stored {version: 1, at: ISO} for 'u1' -> hasCurrentAiConsent('u1') false; ensureAiConsent(ask) with ask -> true calls ask once and the stored record is version 2;
         a stored {version: 2} skips ask (ask not called).
 V3 RED  EN body contains the EN sentence exactly once, it precedes 'Your name, email and account details are not sent.', the body still ENDS with that sentence, and the
         body has exactly 3 '. ' separators (4 sentences).
 V4 RED  AR body: the same three checks with the AR sentence and AR final sentence (section 2 of the AR file is the whole expected value: also pin equality to it).
 V5 PIN  no opt-out wording: every EN aiConsent.* value fails OPT_OUT_EN; every AR aiConsent.* value contains none of the AR words for turn off/disable/settings/cancel
         (escapes: \u0625\u064a\u0642\u0627\u0641, \u062a\u0639\u0637\u064a\u0644, \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a, \u0625\u0644\u063a\u0627\u0621).
 V6 PIN  __tests__/setup.ts source `AI_CONSENT_VERSION:\s*(\d+)` equals the real constant (green at main 1==1; guards the GREEN edit order).
 V7 RED  no key in EN or AR starts with 'profile.aiSharing'; key sets equal; counts equal.
 V8 RED  no file under src/ (walk .ts/.tsx/.json) contains 'ai_sharing_enabled' or 'aiSharing'.
AMEND (in place where the old contract is inverted; append-only is impossible there): aiConsentVersion.s69.test.ts:32-35 PINNED pair (the file's own RULE);
setup.ts:20 (1 -> 2); brand.myez.s69.test.ts: drop :69 and fix the "28" in :58,:143,:152 to 27; bundleA.test.tsx:34-37 "at least 4 (notifications master + 3 subs)";
Screens.bundleD.contract.test.ts:151-154 -> "ProfileScreen no longer reads ai_sharing_enabled" (expect(SRC).not.toMatch(/ai_sharing_enabled/)); DELETE
ProfileScreen.aiSharingDefault.test.tsx (A7); toggles.w314.test.tsx: AI_LABEL -> MASTER_LABEL = EN['profile.notifs.master.title'] in mount(); delete describes :205-219,
:322-357 and nodes :360-384; drop EN['profile.aiSharing.errorSave'] from :173; counts 5 -> 4 and 2 -> 1; every Switch index shifts by -1 (master [1] -> [0], subs [2..4] -> [1..3]);
FULL_PREFS :128 and the mock at :196-200 drop ai_sharing_enabled; bundleE.s3.integration.test.tsx: delete :238-275; rewrite :317-343 to flip switches[0] (the master) and
expect {notifications_enabled: false} with 4 switches; drop ai_sharing_enabled from :124,:323. logoutCopy.b6:162 optional (runtime-harmless).
NEW tests/test_u3b_sharing_branch_removed.py (pure ASCII, LF, no network, no env reads):
 B1 RED  grep fence: for every .py under app/ (os.walk) none contains 'select_client_for_user', 'OPENAI_API_KEY_PRIVATE' or 'use_shared_project'.
 B2 RED  import fence: not hasattr(openai_service, 'select_client_for_user'); inspect.signature(openai_service.get_client).parameters == {}.
 B3 PIN  memo: monkeypatch _client_cache {} and openai_service.AsyncOpenAI to a spy class (pattern of test_llm_provider_base_url.py:462-470): two get_client() calls build once
         and return the same object; isinstance(openai_service._client_cache, dict) (test_m18's contract).
 B4 RED  inert-reader fence: the set of app/ files containing 'ai_sharing_enabled' == {'app/api/auth_routes.py'}.
Route-acceptance pins for old clients = the three existing w314 nodes named in section 1 plus test_auth_ai_sharing_toggle.py::TestAISharingPreferenceShape (3 nodes): stay green.
AMEND backend: test_auth_ai_sharing_toggle.py delete :67-156 (TestSelectClientForUser, TestGetClientFactory), rewrite the module docstring :1-13 (no routing claim), drop the now
unused imports MagicMock/patch/pytest; test_llm_provider_base_url.py :267-269 -> `clients = [osvc.get_client(), esvc.get_client(), usvc.get_client()]` (drop the second cache
reset), :475-477 -> one `osvc.get_client()` (drop the reset + second call). test_backend_cleanup::test_unused_imports_cleaned stays green only because `import os` goes with :71.

## 4. Gates (U5)
Client, from <worktree>/SmartCompareApp (node_modules present or the sc-s74-ct junction; print versions first; one jest at a time across sc-s74-ct/sc-s70-u4b):
 timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/consent __tests__/ProfileScreen.toggles.w314.test.tsx __tests__/ProfileScreen.bundleE.s3.integration.test.tsx
   __tests__/ProfileScreen.bundleA.test.tsx __tests__/Screens.bundleD.contract.test.ts __tests__/ProfileScreen.optimistic.test.tsx __tests__/ProfileScreen.logoutCopy.b6.test.tsx
   __tests__/i18n __tests__/i18n.test.ts __tests__/copy-policy.test.ts __tests__/errorCopy.w314.test.ts __tests__/onboarding/step05Trust.s69.test.tsx __tests__/config/nativeBundle.w37.test.ts __tests__/clientTruth
 RED phase: V1-V4, V7, V8, the amended counts and the re-pinned fence are red at main; V5/V6/B3 are pins (green at main, stay green).
 FULL suite (orchestrator): timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci ; tsc: timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit ;
 eslint by path: timeout -k 15 600 node node_modules/eslint/bin/eslint.js <git diff --name-only --relative inside SmartCompareApp> ; no .snap in the diff.
Backend (bounded runner only; ONE pytest at a time): PYTHONIOENCODING=utf-8 <venv python> <scratchpad>/harness/pyt.py --bound 1200 --tag u3b-be --log <notes>/u3b-be.log --cwd <worktree> --
 tests/test_u3b_sharing_branch_removed.py tests/test_auth_ai_sharing_toggle.py tests/test_llm_provider_base_url.py tests/test_backend_cleanup.py tests/test_m18_openai_tpm_sizing.py
 tests/test_auth_preference_toggles_w314.py tests/test_s71_u13_compare_auth_required.py tests/test_openai_breaker.py tests/test_u3c_store_false_pin.py
 then ruff: <venv python> -m ruff check --select E9,F63,F7,F82 --no-cache app/services/openai_service.py app/api/auth_routes.py tests/test_u3b_sharing_branch_removed.py
 tests/test_auth_ai_sharing_toggle.py tests/test_llm_provider_base_url.py (count unchanged; also no new F401 - the only os use leaves with its import); py_compile the same files.
 auth_routes.py is CRLF on disk (Edit tool preserves): a whole-file diff in `git diff --stat` is a defect. app.openapi() byte-identical to the U13 baseline.

## 5. Diff plan (approximate line counts)
Client src: ProfileScreen.tsx -45/+1 (:309); en.json -3/+1 (body), ar.json -3/+1 (body); api.ts -2/+2 (comment); types.ts -1; aiConsent.ts +0/-0 with 3 lines changed (:36-38,:44);
AiConsentSheet.tsx untouched. Client tests: NEW aiConsentV2.s75.test.ts ~130; aiConsentVersion.s69 2 changed; setup.ts 1; brand.myez 4; bundleA 2; bundleD 3; aiSharingDefault -54 (deleted);
toggles.w314 about -70/+12; bundleE.s3.integration about -40/+14. Backend: openai_service.py about -34/+10 (509 -> ~485 lines); auth_routes.py 2 comment lines; NEW
tests/test_u3b_sharing_branch_removed.py ~80; test_auth_ai_sharing_toggle.py -92/+6; test_llm_provider_base_url.py -4/+2. Docs: privacy-data-inventory.md +2. No package/lock/
requirements/.pre_impl_failures/app.json/landing/app/legal change. No migration (column stays). PR body records: U8 fill-in (PR #330) must not ship before this merges
(U8_LEGAL_REDRAFT_SPEC.md:270); the native binary that ships this copy is the next eas build.

## 6. Native-review list entry (append to the session-75 copy of the CLIENT_TRUTH_NATIVE_REVIEW.md format)
- aiConsent.body [SPEC: one sentence inserted before the final sentence; composed by the U3b spec writer, no native review yet] (EN: 'OpenAI may use these inputs and the
  outputs it generates from them to identify usage patterns, measure model quality and inform the evaluation and training of its models.'). AR text = U3B_AR_COPY.txt section 1;
  the brand is deliberately absent from the sentence (brand fence counts one standalone brand per brand key); Western digits only (none); check that "inform the evaluation
  and training" reads as "istiaana biha fi taqyeem namaadhijiha wa tadreebiha" and not as a promise; a native change must re-pin the fence sha and the V4 constant together.
- AR keys REMOVED (both catalogs): profile.aiSharing.title, profile.aiSharing.subtitle, profile.aiSharing.errorSave (values recorded in U3B_AR_COPY.txt section 3). en/ar 1004 keys each.

## 7. Assumptions (A) and open questions (Q)
A1 Placement before the "not sent" sentence (not appended): "these inputs" binds to the list just given, the reassurance stays last, EN and AR keep one order; no test pins the tail.
A2 No second brand mention: brand.myez :186 pins the aggregate standalone-brand count to the number of brand keys and :152 pins the AR key set; a second standalone MYEZ_AR
   in aiConsent.body reddens both. EN tolerates a repeat but parallel wording wins for the reviewer.
A3 The OA2 triple (identify usage patterns / measure model quality / inform the evaluation and training) instead of a bare "improve its models": the same words as the U8
   section-4 fork, so sheet and policy agree; still exactly one sentence; TRUE of the code (org-level sharing on every project key; store=False irrelevant - U6/OA3).
A4 get_client() loses the parameter and keeps a dict cache under a constant key: test_m18 :112-119 treats _client_cache as a dict (untouched); the kwarg sites in
   test_llm_provider_base_url must change anyway because a parameter that selects nothing would be a lie (U1 deletes the branch, not just the function).
A5 `import os` goes with its only use (:71): otherwise test_backend_cleanup :172-200 reddens and ruff F401 appears.
A6 :309 fallback -> 'common.error' (en.json:386, present in AR): the fallback is unreachable there, U1 forbids keeping an aiSharing key, and 'common.error' is the fallback
   EditProfileScreen.tsx:154 already uses for the same helper; 'profile.notifs.errorSave' would mislabel a password error.
A7 aiSharingDefault.test.tsx is deleted rather than inverted: all three nodes exist only to pin the removed line; V8 + bundleD carry the inverse.
A8 auth_routes.py edits are `#` comments only: Pydantic docstrings are OpenAPI text and the U13 baseline fixture pins app.openapi().
A9 The inventory line is a bullet after the table, not a column: c5 parses only numbered table rows and would reject a new column; the App Privacy answers are LISTING-TRUTH.
Q1 AiConsentSheet has no maxHeight/ScrollView (styles :95-144); the body grows 384 -> 555 (EN) / 336 -> 482 (AR) chars. A 4.7-inch class device may clip the CTAs. Ruling
   needed: accept, or allow GREEN one ScrollView/maxHeight wrapper in AiConsentSheet.tsx (not copy, not fenced). Not verifiable here (no node_modules, no device).
Q2 PreferenceTogglesBody :1415-1421 and the route docstring :1441-1449 still say "AI-sharing (PDPL) opt-out" (OpenAPI-visible). Accept the stale words, or the orchestrator
   re-captures tests/fixtures/s71_u13_flag_off_baseline.json in the same PR (a fixture edit U3b is not assigned).
Q3 tsc scope: tsconfig.json has no include, so __tests__ is type-checked; the remaining ai_sharing_enabled literals sit in untyped jest.fn() fixtures (no excess-property error
   expected) - unverified without node_modules; GREEN confirms with tsc.
Q4 The AR sentence has had no native review (tag [SPEC]); the reviewer may prefer "tahseen" (improve) wording; any change re-pins the fence sha and V4 in one edit.
Q5 Stored v1 records are never deleted (overwritten by the next Agree); a user who never agrees again keeps a dead v1 record - acceptable (R-B precedent), noted for U8/legal.
Q6 Users who decline v2: the compare is blocked exactly as for a new user (R1 "Not now"); no grace period. Confirm this is the intended behaviour for existing users.

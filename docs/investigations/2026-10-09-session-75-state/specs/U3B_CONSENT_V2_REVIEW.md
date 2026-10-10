# U3B_CONSENT_V2_REVIEW - adversarial spec review (session 75, 2026-10-09)

Reviewed: scratchpad/specs/U3B_CONSENT_V2_SPEC.md sha256 0051f9db58b18c83d5f5d34e0ec84f749938623c1619d778ad5de41f5daa8281 (24519 bytes)
and scratchpad/specs/U3B_AR_COPY.txt sha256 c277db33e3c87e12097b4f712a8c132cef3a47cdb7ab578548f8a08d261e2640 (2346 bytes, UTF-8, LF, no BOM;
read into Python only, never printed). Code read at main 4c0f3c99 in the read-only worktree sc-s71-t0b (HEAD verified 4c0f3c99c786f93e3d0fed5ffc94d54f19ea74d5);
every file:line below is at that sha. No jest, no pytest and no device run this round (reading-only worktree, no node_modules): every "red"/"green"
statement is reasoned from the test source, not measured.

VERDICT: NOT READY - one blocking and three major defects, all fixable in the spec text; the copy, the fence math and the design are sound.

## 1. Findings

### BLOCKING

B-1 tests/test_m18_openai_tpm_sizing.py:115-116 calls get_client POSITIONALLY and the spec leaves it untouched.
  :115 `assert osvc.get_client(True).max_retries == 1` / :116 `assert osvc.get_client(False).max_retries == 1`. Spec section 1 and A4 say
  test_m18 :112-119 "treats _client_cache as a dict (untouched)" and section 4 puts the file in the must-stay-green gate set. After T-D
  (`def get_client() -> AsyncOpenAI`) both calls raise TypeError (0 positional parameters), so the backend gate reddens on a file the spec
  declares green. The spec writer grepped for the kwarg name (use_shared_project) and missed the two bare-positional sites.
  Fix: add test_m18 :108-119 to AMEND backend: one `assert osvc.get_client().max_retries == 1` inside the same save/clear/update block (rename
  the node to test_lazy_client_respects_max_retries or keep the name); add the file to files_to_touch and to the section 5 diff plan (-2/+1).

### MAJOR

M-1 tests/test_llm_provider_base_url.py:481 `assert len(seen) == 4, seen` is not amended.
  The spec rewrites :475-477 to ONE `osvc.get_client()` (the reset and the second call go), leaving three spy constructions (osvc once, esvc,
  usvc at :478-479). :481 still expects 4 -> red. Section 5 says "-4/+2" for this file; it needs :481 -> `== 3` (and the :457 docstring
  "Every AsyncOpenAI factory" stays true). :267-269 rewrite is complete (the loop at :271 has no count).

M-2 __tests__/ProfileScreen.bundleE.s3.integration.test.tsx:277-292 is reddened by the removal and is not in the amendment list.
  :286-287 `if (switches.length >= 2) fireEvent(switches[1], 'valueChange', false)` then :288-290 waits for mockPutPreferenceToggles. At main
  switches[1] is the notifications master; after T-C switches[1] is the decision_insight sub-toggle (ProfileScreen.tsx:522-527), which routes to
  putReengagementSubs (:217-243), so the waitFor on mockPutPreferenceToggles times out. The spec amends :238-275, :317-343, :124 and :323 only.
  Fix: :287 switches[1] -> switches[0] and the :285 comment; :294-309 (switches[2], still a sub after the shift) stays green as written.

M-3 Cross-unit sequencing: the policy the sheet links contradicts the new sentence until U8 lands (guideline 5.1.2(i), attack 7).
  aiConsent.link opens LegalScreen (HomeScreen.tsx:141 navigate('Legal', {doc:'privacy'})) -> GET /api/v1/legal/privacy_policy
  (LegalScreen.tsx:33) -> app/legal/privacy_policy.md (legal_routes.py:29). Its section 11 (:80-88) says "you can disable AI sharing in
  Settings -> Privacy -> 'Help improve AI quality'. When off, your queries are processed without contributing to AI evaluation." U3b deletes
  that control and adds "OpenAI may use these inputs ... training of its models". The client half is unflagged and OTA-capable (spec header),
  so from the first `eas update` carrying U3b until PR #330 (U8, D3=C fork per OA2) is merged AND deployed, every user who taps the link reads
  a policy that promises a control the same bundle removed, and the sheet and policy state opposite data-use facts. The spec records only the
  reverse guard (section 5: "U8 fill-in must not ship before this merges"; U8 spec :156 "U3b merges first", :270).
  Fix: section 5 and the PR body must add: no `eas update` and no store submission carrying U3b's client half before #330 (section-4 D3=C fork
  + section-11 rewrite) is merged and live on the API; merge order U3b -> U8 stays, but DEPLOY of the client waits for both. Also tell the U8
  orchestrator: U8's `<PLACEHOLDER:WITHDRAW_PATH>` (U8 spec :236, "derived from U3b's merged code") has no per-user control under D3=C - the
  only withdrawal paths are "Not now" (blocks the compare) and account deletion (clearAiConsent, EditProfileScreen); U8 needs that answer, not
  a Profile path. landing/privacy.html:280 carries the same paragraph (U8).

### MINOR

m-1 A8/Q2 rest on a wrong premise; the docstrings CAN be fixed without a fixture re-capture.
  tests/test_s71_u13_compare_auth_required.py:981-997 (T23) compares ONLY the ten operation objects of ROUTES (:142-154: text/url/image compare,
  quick, prices, extract) and the $ref closure reachable from them (:948-977). The fixture's direct refs from those ten operations are
  Body_identify_and_compare_api_v1_image_identify_post, HTTPValidationError, QuickCompareRequest, TextCompareRequest, URLCompareRequest,
  URLExtractRequest (computed from tests/fixtures/s71_u13_flag_off_baseline.json). PreferenceTogglesBody (:1214), ReengagementSubsBody (:1283)
  and UserPreferencesRequest (:1707) sit in the fixture's components but outside the closure, so rewording auth_routes.py:1415-1421 and
  :1441-1449 ("AI-sharing (PDPL) opt-out") cannot redden T23. Recommend rewording both docstrings in the PR (they are the public /docs text
  and would otherwise claim an opt-out that no longer exists); Field/validator lines stay. Reasoned from the test source; not run.

m-2 bundleA ">= 4" is green at main (5 >= 4). Section 4 lists "the amended counts" as red at main. Either make it `toBe(4)` (red at main,
  green after; the source has exactly 4 `<ToggleRow` after T-C, 5 today) or drop the red claim for that node.

m-3 Line references GREEN will edit by: brand.myez.s69.test.ts carries "28" in the it-names at :145 and :152 (spec: ":58,:143,:152"; :58 is a
  comment without a number, :143 is `});`); the aggregate standalone-brand pin is :183 (spec: :186); the aiConsent.ts header sentence to reword
  is :33-35 (spec: ":36-38", which is ` */`, blank, import). No behavioural impact; the strings in it-names are not asserted.

m-4 AiConsentSheet.tsx:6-7 "(the Profile AI-sharing toggle routes nothing today, #266)" becomes a stale comment; the spec keeps the file
  untouched. aiProcessingConsent.s69 T1.23's it-name (:790) cites #266 too (string only). A one-line comment edit in AiConsentSheet.tsx is
  safe (no test pins the header); or accept and list it as known-stale.

m-5 docs/privacy-data-inventory.md row 12 (:42) still anchors `src/types/types.ts:546-556 { priorities, budget, lifestyle, brand_attitude,
  ai_sharing_enabled, notifications_* }`. After T-C the type has no ai_sharing_enabled and the line range moves. c5 (nativeBundle.w37:744-760)
  never reads cells[2], so nothing reddens, but the inventory is the ASC label source. Edit the cell with the bullet (keep 6 cells, no `|`).

m-6 ProfileScreen.tsx:156-160 is the W3-14 comment explaining BOTH masters' route and the "catalog copy keyed by code" rule; the spec deletes
  :156-182 wholesale, leaving handleNotificationsToggle (:184-205) without its rationale. Reword the comment to the notifications master
  instead of deleting it.

m-7 V2 tautology risk inside the new file: __mocks__/async-storage.ts keeps one module-global `store`. V2's third case ("stored {version: 2}
  skips ask") passes on the record the second case persisted unless the cases use distinct user ids or clear `_store` between them. Spec
  should state the isolation rule (per-case userId or `AsyncStorage._store` reset in beforeEach).

m-8 V5 duplicates aiProcessingConsent.s69 T1.23 (:755-757, :790-795) with a WEAKER EN regex: T1.23's OPT_OUT_EN also has `you can stop`
  and step05Trust's (:64) does not. Reuse T1.23's regex in V5 (both are satisfied by the target copy - measured below) so the two pins agree.

### NOTES (verified, no change needed)

n-1 Fence math. Recomputed at main with the fence's formula (hashlib over [EN title, EN body, AR title, AR body].join('\n') utf-8) =
  cafab3ffe656d44c03ac82120b40514278c8337e29e632d0f6bb57e9b5c95ae2 (= PINNED); over the target strings (EN body = S1 + S2 + NEW + S3, AR body =
  U3B_AR_COPY.txt section 2) = 372c50484085fa859a576a62367c743365735fab6dda31f336552a4ae2a21a02 (= spec). The hash is over parsed JSON values,
  so CRLF/LF of the catalogs cannot change it (`file` reports both catalogs as plain JSON text). New EN body 555 chars / 3 '. ' separators;
  AR section 2 482 chars / '. ' at 128, 285, 431; section 2 == old AR body with the sentence inserted before the final sentence (byte-equal
  reconstruction); the sentence occurs once and precedes the final sentence. Section 3 values == ar.json:428-430 (byte-equal).

n-2 Arabic copy checks (Python, never printed): 0 diacritics in the sentence and 0 in section 2 outside the brand token (T1.24 :822 rule);
  no Arabic-Indic or ASCII digit (digitPolicy.w311 :49); Latin letters only in "OpenAI" (already present in the old body); no Arabic comma
  and no ASCII comma in the sentence (the old body has 3 Arabic commas; the EN sentence has one comma - a style point for the native
  reviewer, not a fence); ends with an ASCII period like the old body; no tatweel / zero-width / BOM; standalone brand count 0 in the sentence,
  1 in section 2 (= old body), so brand.myez :183 aggregate 28 -> 27 and BRAND_KEYS 28 -> 27 stay equal; banned_ar (5 patterns), scary_vocab_ar
  (4 terms), the spec's four opt-out words and T1.23's OPT_OUT_AR regex: no hit. Reading the escaped words: "wa-qad tastakhdim OpenAI hadhihi
  al-mudkhalat wa-l-mukhrajat allati tuntijuha minha li-l-ta'arruf 'ala anmat al-istikhdam wa-qiyas jawdat al-namadhij wa-l-isti'ana biha fi
  taqyim namadhijiha wa-tadribiha." - faithful to the OA2 triple, no promise, no opt-out; native review still required (tag [SPEC]).

n-3 English copy checks: banned_en (12 patterns, case-insensitive), scary_vocab_en (3), OPT_OUT_EN of T1.23 incl. "you can stop" and of
  step05Trust :64: no hit on the new body; no "MYEZ" in the sentence (brand.myez :145 set unchanged except the removed key). T1.22 (:767-788)
  regexes (OpenAI, \bMYEZ\b, product name, link, photo, preference, \bname\b, \bemail\b) all still match. T1.21 (AR != EN) holds.

n-4 Copy truth (attack 4, U6). "these inputs" binds to S1+S2 (product names, links + page text, photos, profile preferences incl. onboarding-
  suggested ones, country/language/area) - exactly the compare payload. Under OA2 all three Sharing settings are "Enabled for all projects"
  (org level) and OA3 says store=False does not touch the programme; the sentence names neither store nor logs, so U3c is not conflated. No
  existing sentence becomes false: S1/S3 and the title describe what is sent / not sent; onboarding.s5.privacy_anon_body (en.json:576) lists
  what is sent. onboarding.s5.privacy_never_body ("Your name. Your email. Not now, not ever.") is U8's C31 (U8 spec :135) and outside OA2's
  "Step 5 unchanged" - not U3b. onboarding.s5.bullet_1 "Your data lives on your device" (en.json:580) is not rendered by Step05Trust.tsx
  (only privacy_use_body :80 / privacy_anon_body :95 / never_body) - dead key, pre-existing.

n-5 Old-client compatibility (attack 2). UserPreferencesRequest.ai_sharing_enabled (auth_routes.py:219), PreferenceTogglesBody (:1423), the
  RMW loop (:1462-1464) and the echo (:1483) are untouched by T-E; GET /preferences returns the stored dict. Pins that prove acceptance exist:
  test_auth_preference_toggles_w314.py:152, :203, :273 and TestAISharingPreferenceShape (test_auth_ai_sharing_toggle.py:26-63, kept). After
  the deletion no app/ file reads the key (grep: only auth_routes.py and openai_service.py:87,:89 today; B4 pins the set). A user on an old
  bundle who flips the dead toggle writes an inert false - unchanged since #266. "Inert" is the right word.

n-6 Version bump vs the suites (attack 3). __tests__/setup.ts:18-39 stubs hasCurrentAiConsent/ensureAiConsent to true and runs withAiConsent
  synchronously; AI_CONSENT_VERSION:1 at :20 is informational (V6 pins it to the real constant). aiProcessingConsent.s69 reads the real
  constant through consentVersion() (:254-258) and olderVersionThan() (:260-262); T1.5/T1.6/T1.7 (:450-490) are version-generic and stay
  green at 2. aiDispatchFence.s69 is a source fence over dispatch sites (ProfileScreen is none). EditProfileScreen.bundleE.s3.integration
  :272 uses the mocked clearAiConsent only. No .snap contains "ai-consent" or the body text (17 .snap files grepped): the "no .snap change"
  gate is safe. jest.config.js testMatch covers `**/__tests__/**/*.test.ts`, so the new file collects.

n-7 Backend blast radius (attack 6). Every tests/ call of get_client with an argument: test_auth_ai_sharing_toggle.py:153-154 (deleted),
  test_llm_provider_base_url.py:267,:269,:475,:477 (amended), test_m18_openai_tpm_sizing.py:115-116 (MISSED - B-1). test_openai_breaker.py
  patches get_client with return_value (:276,:368,:590,:668,:679,:735; signature-agnostic). select_client_for_user is imported/patched only by
  test_auth_ai_sharing_toggle.py. OPENAI_API_KEY_PRIVATE as a NAME: tests/_env_safety.py:117, tests/test_conftest_env_safety.py:72 (guard
  lists - keep), tests/test_backend_cleanup.py:178 and tests/.pre_impl_failures.txt:30 (docstring/comment; B1 walks app/ only, correct).
  openai_service.py: `os.` is used only at :71 (grep), so A5 holds; Any/Optional/Dict stay used at :293-:430. B1 at main is red (openai_service.py
  :41-42,:48-91), B2 red, B4 red (openai_service.py:87,:89), B3 green (pin), as declared. Docs still naming the branch after U3b (docs
  checkpoint, not U3b): CLAUDE.md:19,:502,:560; docs/CONTEXT_SESSION_LOG.md:41,:67; docs/claude-design-handoff/project-README.md:119
  (lists the toggle copy); docs/plans/* historical; app/legal/privacy_policy.md:88 and landing/privacy.html:280 (U8).

n-8 Client removal blast radius (attack 1). ai_sharing_enabled / aiSharing in SmartCompareApp outside node_modules: src = ProfileScreen.tsx
  (:106-107,:140,:149,:162-177,:309,:505-511), api.ts:594,:600, types.ts:557, en.json:431-433, ar.json:428-430 - all in T-C. Tests: the spec
  names every one except bundleE.s3.integration :277-292 (M-2); errorCopy.w314.test.ts:80-81 opaque string (green); logoutCopy.b6:162 untyped
  fixture (green); optimistic.test.tsx mentions "aiSharing" only in its header comment (:5,:7) and pins putReengagementSubs shapes only.
  i18n fences: i18n.test.ts:8 set parity and no-deleted-keys:65 count parity hold at 1004/1004; no-missing-referenced-keys walks src/ and
  loses the three t('profile.aiSharing.*') sites (:505-506, :172/:177/:309 after the 'common.error' switch; en.json:386 and the AR key exist);
  brand.myez :69 removal keeps :145/:152/:183/:210 consistent; copy-policy scans values (clean); clientTruth/* pin other keys and inventory
  row 5 only (privacyManifest.s74:42-51 reads the `| 5 |` row; the bullet is not a row). No deep link, onboarding step, Settings copy or
  __mocks__ file reaches the toggle. profile.section.privacy (en.json:430) is already unreferenced in src - pre-existing dead key, not U3b's.
  `Shield` has one use (:504), `styles.errorText` keeps :544/:613, flatRowToggleHost keeps :513, buildNextPrefs keeps :190/:217.

n-9 RED-tautology audit (attack 8): V1-V4, V7, V8, B1, B2, B4, the fence re-pin, bundleD's inversion, toggles.w314 5->4 / 2->1, the bundleE gate
  node 5->4 are red at main; V5, V6, B3 are declared pins; bundleA >=4 is green at main (m-2). V3's "exactly 3 '. '" is red at main (2).

n-10 Q1 (sheet height) stays open and is the one ruling GREEN needs: AiConsentSheet.tsx:94-102 card has paddings and gap only, no maxHeight
  and no ScrollView; the body grows 384 -> 555 (EN) / 336 -> 482 (AR) characters under typography.body. Not measurable here. Recommendation:
  allow GREEN a `maxHeight` on the card plus a ScrollView around the body Text only (testIDs and copy untouched; aiProcessingConsent.s69
  queries by testID / text, so neither fence moves).

n-11 Q6: a user who declines v2 is blocked exactly like a new user (R1 "Not now", aiConsent.ts:112-118); with no per-user switch under D3=C
  this is the only "no" the design has, so it is consistent, but the owner should hear it in one sentence: existing users see the sheet once
  more and cannot compare until they agree.

n-12 Q5: v1 records are overwritten by the next Agree (same key, recordAiConsent :78-86); a never-again user keeps a dead v1 record. Acceptable.

## 2. Assumptions (with the reason each beats its alternative)

A-1 T23's closure excludes the preference models (m-1): read from _referenced_components :948-977 and ROUTES :142-154 plus the fixture's
  direct refs; the alternative (components compared whole) is contradicted by the function's docstring and body. Not executed.
A-2 bundleE.s3.integration :286 reaches the sub-toggle after the shift: the subs render only when notificationsEnabled && prefsRowLoaded
  (:521), and the :119-131 fixture has notifications_enabled: true with a full notification_types row, so 4 switches render and [1] is insight.
A-3 test_m18 :115-116 fail with TypeError rather than being skipped: no marker on the node (:108), the file is in the spec's gate list.
A-4 The AR sentence is acceptable pending native review: faithful to the OA2 triple, every fence clean; the alternative (reject until review)
  would block GREEN on an owner item that the native-review list already carries.
A-5 The in-app policy is app/legal/privacy_policy.md, not landing/privacy.html: LegalScreen.tsx:33 and legal_routes.py:29.

## 3. Not verified (no runtime this round)

- No jest or pytest executed; every red/green claim is from source. GREEN must run the section 4 gates and the FULL suite.
- Q1 rendering on a 4.7-inch device; Q3 tsc over the untyped fixtures (logoutCopy.b6:162 etc.).
- Whether CI has any node-count or collect-only gate that a deleted test file could trip (grep over .github/workflows found none).
- The exact wording the orchestrator wants for the two auth_routes.py docstrings (m-1) and the inventory row-12 cell (m-5).

## 4. Required spec edits before GREEN (summary)

1. B-1: amend tests/test_m18_openai_tpm_sizing.py:108-119 to a single get_client() call; add to files_to_touch, section 3 and section 5.
2. M-1: tests/test_llm_provider_base_url.py:481 -> `== 3`.
3. M-2: __tests__/ProfileScreen.bundleE.s3.integration.test.tsx:285-287 switches[1] -> switches[0].
4. M-3: section 5 / PR body: no eas update and no store submission with U3b's client half until #330 (D3=C fork) is merged and live; note the
   WITHDRAW_PATH answer for U8.
5. m-1..m-8 as listed (docstrings, bundleA exactness, line refs, stale comments, inventory row 12, comment reword, V2 isolation, V5 regex).

Files written by this review (sha256 in the StructuredOutput): this file at scratchpad/u3b/review/ and its copy at scratchpad/specs/;
helper outputs scratchpad/u3b/review/ar_sentence_escaped.txt and ar_words_escaped.txt (ASCII escapes of the AR sentence, for the record).

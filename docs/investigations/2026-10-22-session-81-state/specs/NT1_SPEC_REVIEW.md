# NT1_SPEC_REVIEW: adversarial spec review of NT1a (NATIVE 1.0.1, the P0 only)

- Reviewer: adversarial spec reviewer (lens: correctness, the OTA runtime, comm set, pins). The second lens (app-review-and-privacy) is separate.
- Spec: .qa-s80/NT1_UNIT_SPEC.md, sha256 4cfb0ec2d5b966f4813c9e95ec87bbd438c565e9b655f446904631d646b8c3fb (re-hashed first: MATCH).
- Base: 6b909e0a92067d6b3562eee325e4956c116441f7. Worktree read-only; `git status --short` empty before and after. Probes ran on copies under the scratchpad (nt1rev/), git plumbing only; no jest (brief), no pytest needed (no backend claim depended on a new run), no eas / npm / network.

## VERDICT: APPROVE_WITH_CHANGES

The code-side design is sound and every measured value I re-derived reproduces exactly. One process defect in the owner steps (B1: what the App Reviewer's camera does during the 1.0.1 review) must be ruled and written into sections 2.6 c / 8 before the spec is final; RED can start in parallel, because no RED row depends on it.

## 1 RE-MEASURED (all at 6b909e0a; each CONFIRMED unless listed in section 2)

- app.json:5 version "1.0.0"; :16-19 locales; :152-154 ios.infoPlist holds only ITSAppUsesNonExemptEncryption (no NSCamera / NSPhotoLibrary override); :220 / :228 the two OpenAI sentences; :221 / :229 MIC; :272-274 runtimeVersion { policy: appVersion }; :275-277 updates.url. No app.config.js / .ts and no ios/ or android/ directory (managed workflow).
- locales/en.json:4-5 byte-equal to app.json:220 / :228. ar.json: camera sha 8e418902..., photos sha 4a5e381e..., mic sha 999e6f18..., display sha 5d3c4d53...; OPENAI_AR occurs exactly once in each AR purpose string.
- The drafts (my own probe, nt1rev/probe.py): NEW_CAM_EN aa17e72b... 169 B; NEW_PHOTOS_EN 23ffac74... 158 B; NEW_CAM_AR cf0a067d... 278 B; NEW_PHOTOS_AR b0506c29... 246 B. On both AR drafts: no diacritic outside the brand, no Latin letter, no `"` or `\`, banned_ar [], scary_vocab_ar [] (src/i18n/.copy-policy.json), servers token once, AI_PROVIDERS_AR once.
- Every canonical hash of 2.4 reproduces in Python (expo-minus caf4a65e..., plugins-minus 5d26fd82..., privacy b404a4ad..., eas d5be08d3..., package 3dc071e5..., en-minus 976decc1..., ar-minus a71cf201..., expo-full 0e5d050f...). JS-twin hazards checked: no float in the expo object, all keys ASCII (code-point vs UTF-16 sort identical), neither side escapes `/`; the JS twin should match.
- Readers of the sentences: the w37 literals :66-67 (a5 :201-206, a6 :208-213, u10 :1394-1408), b3a_copy.json:91-92 / :95-96, b3a nativeStrings :29 / :90-98 / :100-111 / :113-122 / :171-185; honestCopy.b3a reads changed_keys / new_keys / learning_keys / brand_keys, never `native` (CONFIRMED). w37 e1 :1107 / :1108-1128 / :1130. w37 u9 / u11 / u12 lines as cited.
- #378 (origin/feature/s81-legal-v3 e8c8c1dc): three-dot diff touches none of app.json, locales, eas.json, package.json, __tests__/config, __tests__/b3a, the b3a fixture, docs/privacy-data-inventory.md. Its new tests (test_s81_12_legal_v3.py, test_s81_12_gate_rows.py, legalV3.s81_12.test.ts) read no purpose string, no app.json and no expo.version (grep).
- Store-build identity: `git diff --stat 683f56c0 6b909e0a -- app.json eas.json package.json locales` EMPTY.
- eas-cli 18.8.1 (oclif.manifest.json read offline): `update` flags = auto, branch, channel, clear-cache, emit-metadata, environment, input-dir, json, message, no-bytecode, non-interactive, platform, private-key-path, rollout-percentage, skip-bundler, source-maps: NO runtime flag (CONFIRMED). `update:list` has --runtime-version (CONFIRMED). build/build/ios/version.js:95-107 and build/build/ios/build.js:42-48 / :71-73 as cited.
- CLAUDE.md readers by path: test_behavior_dimension_translation.py:226, test_ci_gates.py:934, test_s81_s04_spend_breaker.py:1657, test_s81_s08b_legacy_fingerprint.py:74, test_s81_s23_bypass_retire.py:316 (+ s08b_gate_rows through its import): matches G5 (c).
- No version mirror in src (sentry.ts sets no release; the @sentry plugin block carries no version), App.tsx, index.ts.

## 2 REFUTED CLAIMS (measured truth)

- RC1 (section 1.2, "resolveRuntimeVersionAsync.js:36 Updates.getRuntimeVersionNullableAsync"): :36 is the FALLBACK branch, taken only when the project's expo-updates lacks the runtimeversion CLI (`isModernExpoUpdatesCLIWithRuntimeVersionCommandSupportedAsync`, :32). With expo-updates ~29 the modern branch runs the PROJECT's installed expo-updates to resolve the runtime. The outcome is the same (appVersion -> exp.version) but the runtime of a release/1.0.x publish is resolved by THAT checkout's node_modules, which makes the `npm ci` of step 2 load-bearing, not hygiene.
- RC2 (2.6 b step 4, "build/commands/update/republish.js: it copies the group's updates"): the runtime-preserving code is build/update/republish.js:41 / :48 / :98 / :107 (`const { runtimeVersion } = arbitraryUpdate`, reused for every republished update). The claim is true; the citation is wrong.
- RC3 (section 2.6 b, the lever list is complete): eas-cli 18.8.1 also has `update:roll-back-to-embedded --runtime-version` and `channel:rollout --runtime-version` (manifest). roll-back-to-embedded targets a runtime explicitly and needs no bundle, so it is a 1.0.0-fleet rollback lever usable from ANY checkout (main included) after the bump; the procedure should name it.
- RC4 (L2: "the v3 legal AR text carries the shadda"; the purpose string differs from the v3 phrase): true for the policy (privacy_policy_ar.md on #378: shadda form 7x, plain form 0x), but the in-app consent sheet v3, the surface the reviewer and the user read next to the prompt, ALREADY writes the shadda-free form: #378 src/i18n/ar.json `aiConsent.body` and `onboarding.s5.privacy_anon_body` contain the plain phrase (with the possessive "ladayhi", its) and not the shadda form. So the draft matches the consent sheet; L2 understates the consistency and should cite the sheet.
- RC5 (1.3 / 1.4 reader tables complete): two readers are missing (both inert, no edit): SmartCompareApp/__tests__/onboarding/step05Trust.s69.test.tsx:17 (comment "states what is sent to OpenAI"; #378 already edits that file) and SmartCompareApp/__mocks__/expo-application.ts:6 `nativeApplicationVersion = '1.0.0'` (the global mock every appVersionService suite inherits; STAY, but it belongs in 1.4).
- RC6 (2.4 / 3 / G0: "every byte outside ... is identical to base"): NOT pinned by any row. P1-P7 pin CANONICAL JSON (key-sorted, whitespace-free), so a reformatting write (json.dump of app.json or ar.json, key reorder, indentation change, a lost trailing newline) passes every PIN; G0 checks only names and CRLF. Step 4 and step 7 rewrite ar.json and the fixture with Python, which is exactly where this drift happens. See correction C1.

## 3 BLOCKING (spec revision required; RED may proceed)

- B1 THE REVIEWER'S CAMERA (the camera failure envelope interaction; Q7). The spec orders ENABLE_ANTHROPIC_VISION AFTER the 1.0.1 release (O6) and keeps no bridge OpenAI key (owner ruling). Then during App Review of 1.0.1 every camera / photo scan runs the OpenAI vision call on the dead credential. Measured: a 401 is NOT transient (app/services/api_budget_service.py `_openai_failure_is_transient`: 401 / 403 return False), so app/api/image_routes.py:412-417 does NOT take the coded 503 LLM_UNAVAILABLE arm; it raises the codeless 500 "Image analysis failed. Please try again." (:417). The reviewer therefore sees the core feature named in the two new permission prompts fail, right after granting them: a predictable guideline 2.1 (completeness) rejection, and the Notes draft would describe a camera that does not work. The spec must rule one of: (a) flip ENABLE_ANTHROPIC_VISION before submitting 1.0.1 (the reviewer accepts consent v3 on the 1.0.1 build, so vision routes to Claude), accepting for the review window that 1.0.0 installs on consent v3 send photos to Anthropic while their Info.plist still says OpenAI (CLAUDE.md:508 already names this as "risk accepted or 1.0.1 live": the owner's call); or (b) keep vision OFF and state in the Notes that photo identification is temporarily unavailable (rejection risk stays high); or (c) another lever the orchestrator names. Write the ruling into 2.6 c, O5 / O6 and the Notes draft. (The codeless 500 itself is outside NT1a's no-backend scope; it should get its own follow-up id, since "try again" is also forbidden copy if any client surface echoes it.)

## 4 CORRECTIONS

- C1 (RC6) Add to G0, and to the RED file as a P-row if cheap: `git diff --numstat <base>..HEAD` per file EXACT: app.json 3/3, locales/en.json 2/2, locales/ar.json 2/2, b3a_copy.json 4/4, nativeBundle.w37.test.ts and nativeStrings.b3a.test.ts the hunk counts of E1 / E2 / E4; plus a raw-bytes check: each edited JSON file, with the edited lines replaced by the base lines, sha256-equal to the base blob (LF-normalized). Byte identity must be pinned, not inferred from canonical JSON.
- C2 (RC1) Section 1.2 and 2.6 b step 2: cite the modern branch (the project's expo-updates resolves the runtime); in step 2 make `npm ci` in the release/1.0.x checkout MANDATORY before every 1.0.0 publish, and the read-only proof `eas update:list --branch production --runtime-version 1.0.0` after it (owner side).
- C3 (RC2) Re-cite republish to build/update/republish.js:48 / :98 / :107.
- C4 (RC3) Add `eas update:roll-back-to-embedded --branch production --runtime-version 1.0.0` as the 1.0.0-fleet rollback lever (no maintenance branch needed for a rollback), names only.
- C5 (RC4) Rewrite L2: the purpose string matches the consent sheet v3 AR spelling (shadda-free); only the policy / Terms carry the shadda. Keep [NATIVE READ].
- C6 (RC5) Add the two missing readers to 1.3 / 1.4 as STAY.
- C7 Notes for Review: (a) use the policy URL recorded in App Store Connect, https://getmyez.com/privacy.html (CLAUDE.md:690); /privacy also resolves through nginx `try_files $uri $uri.html` (landing/nginx.conf.template:81-83) but one URL avoids a reviewer-visible mismatch; (b) "it names Anthropic and OpenAI" and "MYEZ now uses more than one" are true for #378's copy (measured: aiConsent.body names both) but become false if S81-12b (the OpenAI-removal part, RULINGS_CLAUDE_PATH step 8) lands before submission: add an owner step "re-read the live consent sheet and policy at submission and edit the Notes to match"; (c) after B1's ruling, state the camera's behaviour truthfully.
- C8 Section 2.6 a G-ORDER: add "and the 1.0.1 build is cut promptly after the merge" (see Q3): every hour between the NT1a merge and the 1.0.1 release is an hour in which a 1.0.0 hotfix needs the maintenance branch.
- C9 Section 1.10 / G5: the 12-file base record is fine; record it in the LC-6 base file at RED with the [pyt] lines (no change of substance).

## 5 CONTRACT RISKS

- CR1 Runtime split: from the merge on, any `eas update` from main strands 1.0.0 (the whole fleet until 1.0.1 is released and adopted). The procedure is right but relies on humans; nothing in the repo refuses a mistaken publish. OTA_READINESS must carry it as a red line (the spec says so).
- CR2 The 1.0.1 binary embeds main's JS at its build commit (2.6 c): any client unit merged between NT1a and the build whose backend precondition is unmet ships to the reviewer. The checklist is right; it must be executed against the exact build sha (the asterisk rule).
- CR3 L7 / Q-O4: #378's policy says the OpenAI data-sharing programme ENDED (privacy_policy.md:7 on the branch), while the manifest keeps PurposeOther on five types, documented in docs/privacy-data-inventory.md:46 as that programme. 1.0.1 ships a manifest whose documented meaning no longer holds. Not a correctness defect of this unit (byte-identical by design) but a reviewer-visible / label mismatch for the second lens and the owner (Q-O4).
- CR4 APP_MIN_VERSION / APP_FORCE_UPDATE stay at their defaults; once 1.0.1 is live, 1.0.0 installs keep the OpenAI strings and (per B1 a) may send photos to Anthropic under consent v3. Owner's call 4; documented only.

## 6 PIN COLLISIONS

- None beyond section 4.1's E1-E5. Checked: T23 OpenAPI, FY25 digests, w4_11 prompt digests, test_retro_w2_1 URL pins, the W4-13 ledger fixture (no backend file moves); copy-policy fences (src/i18n only; locales fenced by w37 u11, which passes on the drafts); the four drift nodes d5 / k2 / k4 / k5 read package / lock / node_modules only; the backend config readers' needles (u.expo.dev, the SmartCompareApp/app.json module path, eas.json keys) do not move; #378's new tests read none of the unit's files. CLAUDE.md is the only shared file with #378 (known rebase; the R-NT1-7 order).

## 7 CLASS CHECKLIST (session-79 defect classes)

- Vacuous PIN rows: none (no flag, no config gate precedes the reads; every PIN reads the real files).
- Mutants no RED row can kill: none found; an added ios.infoPlist override is killed by P3 (the R9 recipe starts from empty modResults and would not see it, P3 does); a non-listed provider name in EN / AR is killed by R4 / R5 / R6 exact equality.
- Comm-set gaps: none material (RC5 readers are inert).
- Flag-OFF byte identity: replaced by the canonical invariant; NOT byte-pinned (RC6 / C1).
- Response keys, refusals reaching build 3, billing, cache keys, error-code mapping: not applicable (no backend change); the camera envelope interaction is B1.
- Stated limit that is a defect: L1 / O6 ordering hides B1.

## 8 QUESTIONS FOR THE ORCHESTRATOR

1. B1: which camera state does the App Reviewer get on 1.0.1: ENABLE_ANTHROPIC_VISION ON before submission (accepting the 1.0.0 string mismatch for the review window), OFF with a Notes disclosure, or another lever? It decides O5 / O6 and the Notes.
2. Should the codeless 500 of image_routes.py:417 on a non-transient OpenAI failure (401 dead key) get its own follow-up id (backend, coded envelope) independent of NT1a?
3. Version-bump timing: keep the bump in NT1a (R-NT1-3, merge after G-ORDER), or merge the strings first (runtime-neutral: Info.plist strings are not JS-visible) and land `expo.version` 1.0.1 only in the build commit, so main keeps reaching the 1.0.0 fleet until the owner actually builds? The second shrinks the maintenance-branch window to the review period.
4. Q-O1: agree jest only (the python twin would duplicate rows and cannot run R9 / P8).
5. Q-O2: agree package.json stays 1.0.0 (P6 pins it; moving it edits the lock).
6. Q-O4 / CR3: is the PurposeOther manifest change a separate native-config unit before the 1.0.1 build (it would have to ride the same binary to fix the label mismatch), or a stated limit for 1.0.1?
7. Should the Notes for Review be re-measured against the LIVE consent sheet and policy at submission (C7 b) as a named owner step?

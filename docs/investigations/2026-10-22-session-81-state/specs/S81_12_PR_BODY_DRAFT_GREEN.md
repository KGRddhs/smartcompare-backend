# S81-12 LEGAL-V3: the legal texts name Anthropic beside OpenAI, the data-sharing programme ends, consent v3 (HELD PR)

**HELD: do not merge before the flip window.** H1 (`tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded`) is red by design until the merge-window record exists; the flip-window checklist is below, beside H1.

## What this changes (no runtime flag)
Docs-legal lane: there is NO dark flag, so there is no flag-OFF identity to prove. Through the U8 machinery only (pre-fill snapshot -> `scripts/legal_variants_u8.json` + `tests/fixtures/legal_fill_in_u8.json` -> restore -> `scripts/fill_in_legal.py` -> `scripts/render_legal_landing.py --check`):
- privacy policy and Terms (EN + AR) name both AI providers with the R-S12-1 dual-provider sentence (privacy s2, s4; Terms s8) and one Anthropic + one OpenAI bullet in privacy s5;
- Anthropic's facts in privacy s4: no training, retention up to 30 days (batch up to 29 days) with the usage-policy / legal exception, a conditional web-search sentence;
- OpenAI's data-sharing programme is told in the past (ONE dated history sentence in privacy s4, short past-tense sentences in privacy s2 and Terms s8); d3 recorded 'A'; forks d3_training / openai_retention retired; the s5 carve-out is dated; the not-sold promise is bare;
- privacy s6: the owned catalogue, the crawler named by its user-agent page https://getmyez.com/bot/ (never the old brand token), operator entry, licensed data, Sponsored store links that never change the ranking; Terms s7: Sponsored is not a recommendation;
- privacy s12 AI disclosure; privacy s14 device identifiers (R-S12-10 as amended);
- dormant texts (null until recorded): DEVICE_QUOTA_RESET (Terms s4 / s9, privacy s8 counters), COMPARE_RUN_RETENTION (the compare-run bullet AND the kb_feedback device-key bullet: one key gates both, GC-2), AUTH_THROTTLE_RETENTION; both retention keys join RETENTION_KEYS (UL8);
- processors.json: the anthropic row (S81-06) becomes public_name true; the eighth fill-in flag ENABLE_ANTHROPIC_TEXT is recorded 'on' (GC-5);
- consent v3: AI_CONSENT_VERSION 3, setup mirror 3, EN + AR body (both providers; 'some or all requests, including photos' on OpenAI until the move is complete; the training sentence gone), the fence re-pinned in the same edit (77ac6348...ebcc1); onboarding Step 5 copy + Step05Trust defaults;
- dates: AI_SWITCH_DATE / _AR, both TERMS_VERSION literals and the twelve anchors carry the PROVISIONAL date 2026-10-29 (the GREEN day);
- CLAUDE.md: ship-blocker item 2 and the consent sentence rewritten in place; a no-flag unit row before ## Tests.

## Defect ids -> RED nodes
| RED row | what it pins | state on the GREEN bytes |
|---|---|---|
| R1 [en/ar] | privacy s4 names both processors, Anthropic no-training + up-to 30/29-day retention, usage-policy exception, conditional web search, photo guidance once | GREEN |
| R1b [en/ar] | R-S12-1 dual-provider sentence verbatim in privacy s2 / s4 and Terms s8; both names in s2 / s5 / Terms s8 | GREEN |
| R2 [en/ar] | no present-tense sharing anywhere; ONE dated 'programme ended on <date>' sentence in privacy s4 | GREEN |
| R3 [en/ar] | bare not-sold promise; the 'Apart from OpenAI's programme' qualifier gone | GREEN |
| R4 [en/ar] | privacy s5: one Anthropic + one OpenAI bullet, dated carve-out, email-delivery fragment | GREEN |
| R6 [en/ar] | privacy s6: crawler by its user-agent page https://getmyez.com/bot/, by hand, licensed data, Sponsored, never changes ranking | GREEN |
| R7 [en/ar] | privacy s12 AI-disclosure sentence | GREEN |
| R8 [en/ar] | Terms s7 Sponsored / not a recommendation / catalogue; s8 no 'Our AI provider is OpenAI' | GREEN |
| R9 | anthropic row public_name true, named + categorised in both policies, PUBLIC_NAME_IDS in both test files, openai row unchanged | GREEN |
| R10 | d3 'A', forks retired, dormant forks / clauses, placeholder keys, AI_SWITCH_DATE recorded | GREEN |
| R11 / R12 / R18 | dormant device-rule, compare-run / throttle and kb_feedback texts (temp copies, synthetic values) | GREEN |
| R13 | AI_SWITCH_DATE (EN, AR) == the four anchors == TERMS_VERSION, in privacy s4 | GREEN |
| R14 / R15 | consent v3 (version 3, setup mirror, copy, fence digest); Step 5 copy + Step05Trust defaults | GREEN |
| R16 [en/ar] | OpenAI census (allowed sections and sentence classes; regions equal sources) | GREEN |
| R17 [en/ar] | privacy s14 per amended R-S12-10 | GREEN |
| R19 | COMPARE_RUN_RETENTION / AUTH_THROTTLE_RETENTION (+ _AR) in RETENTION_KEYS (UL8) | GREEN |
| H1 | merge-window record == TERMS_VERSION == AI_SWITCH_DATE | RED BY DESIGN (green with a window record, measured on a temp file) |
| H1b, P1, P3, P4, P5 [en/ar], P6, P7 | pins | GREEN |
| C1, C3, C4, C5 (jest) | version 3 + fence; v3 body structure; rendered sheet; Step05Trust | GREEN |
| C2 (jest, 2 nodes) | v2 record no longer counts / a v3 record counts | RED: wrong row (calls the record API without the user id; see Open questions) |

## Hold (H1) and the flip-window checklist
H1 reads `tests/fixtures/legal_v3_window.json` (absent by design) and requires `openai_sharing_off_on` == `TERMS_VERSION` == AI_SWITCH_DATE / _AR. Measured on the GREEN bytes with a temporary record = 2026-10-29: H1 and H1b pass (the file was removed and is not committed). Window steps, in order:
1. the owner turns OFF OpenAI organisation data sharing (dashboard; ends the free-token allowance: OpenAI traffic is billed at list price from that day) and writes the names-only dated ledger line;
2. Anthropic's current commercial terms / privacy policy are read (an agent with a documentation grant, or the owner) for retention (30-day default, batch 29 days, any zero-data-retention option), training (none on API inputs by default), the usage-policy exception and the minors policy (R-S12-13); the reading is recorded in the window commit;
3. the orchestrator re-dates by restore + record + fill + render --check (the four snapshot date lines, AI_SWITCH_DATE / _AR, app/services/consent_service.py TERMS_VERSION, SmartCompareApp/src/services/consent.ts TERMS_VERSION, tests/test_consent_capture_w3_16.py TERMS_VERSION, and tests/fixtures/legal_v3_window.json openai_sharing_off_on), then runs the unit file, the legal set and the consent jest suites: H1 turns green;
4. the frozen RED file tests/test_s81_12_legal_v3.py is committed after the gitleaks ruling (Open question 2);
5. merge in the same window as the first S81-06 text-role flip (ENABLE_ANTHROPIC_TEXT ON; the eighth fill-in flag is already recorded 'on'); Railway deploys the backend;
6. the landing is redeployed from a clean checkout of the merge sha (railway up landing --path-as-root -s qaren-landing -d);
7. the App Privacy label is checked against the v3 policy;
8. only then the first post-approval OTA (the consent v3 copy, with S81-08).

## Deliberate pin changes (each with its reason; gate GC-8)
| node / file | reason |
|---|---|
| tests/test_consent_capture_w3_16.py::test_b12_terms_version_parity_backend_legal_route_and_client | E26: the TERMS_VERSION literal moves with the anchors to the provisional switch date 2026-10-29 (the re-date recipe edits it again in the window). |
| tests/test_legal_disclosure_s77.py::test_s77_d1[en/ar], d3[en/ar], d4 | E22 / R-S12-4: GENERAL_EN is the bare promise, P2_DISCLOSURE_EN / T8_DISCLOSURE_EN / the AR fixture disclosures tell the programme in the past; the AR helpers no longer require OpenAI in the promise sentence (the exception ended) and flag the S77 programme qualifier instead; D4's AR control flipped accordingly; the S77 sentences moved to RETIRED_EN / retired_ar (appended). Test bodies of D1 / D3 unchanged. |
| tests/test_legal_disclosure_s77.py::test_s77_d2[en/ar] | E22: rewritten for v3 (the past-tense exchange head once, dated in its line with AI_SWITCH_DATE, before the photo guidance; forks retired; S77 sentences gone). |
| tests/test_legal_disclosure_s77.py::test_s77_d5[en/ar], d10, d13[en/ar], d18[en/ar] | NOT edited (GC-8): green by construction. d5 / d10 read the moved constants through _privacy_expected / _terms_expected; d10 pins no snapshot bytes; d13 reads d3c.S5_CARVEOUT_EN / fix2_ar.s5_carveout (moved with d3c (n)) and Google stays named in s5; d18's only red was the address count, re-pinned by GC-4 (PRIVACY_PAGE_ADDRESSES 14 -> 15). |
| tests/test_legal_docs_u8.py::test_t8_policy_ai_section_agrees_with_consent_copy_ar (+ _en, + the keyword maps) | R-S12-4 / E9: D3_FORBIDDEN_EN['A'] reads the hyphenated programme name too; the ONE dated history sentence of s4 is allow-listed by exact text (_d3_scan_text, dated from the fill-in data); the 'Anthropic' key joins both keyword maps (required in s4 and the consent copy); latin_ok names Anthropic. NEW pin node test_t8_history_allow_list_is_exact (positive control: the S77 present-tense EN and AR sentences still caught; mutant: the history sentence with another date caught). |
| tests/test_legal_docs_u8.py::test_t7_processor_manifest_schema | R-S12-11: PUBLIC_NAME_IDS gains 'anthropic' (public_name true exactly for the named recipients). |
| tests/test_legal_docs_u8_d3c.py::test_d3c_a (x3), c (existing_t8_routes_c), d, e_en, e_ar, i, j, n[C/A] | E20 / R-S12-4: re-scoped to the retired fork: (a) forks retired, no fork reads d3 / openai_store_pinned, consent v3 drops the OA2 clause, generic variant locatability; (c) the retired C text from the fixture; (d) d3 'C' is accepted and selects nothing (plan == d3 'A' plan); (e) the C rule still recognises the retired text, the v3 s4 makes no C-only claim; (i) / (j) bare promise + past-tense history, the s3.6 programme purpose line must be ABSENT; (n) carve-out tail + dated head, the dated history sentence instead of the retired fork. Fixture: retired_d3_c (control), ar_values.AI_SWITCH_DATE_AR, ug12_ar / fix2_ar re-recorded. |
| tests/test_legal_docs_u8_d3c.py::test_d3c_f[B/C], g, k (no_sentence_claims), l, m | GC-8: only the synthetic data gained AI_SWITCH_DATE / _AR (COMPLETE_VALUES_EN + fixture ar_values); bodies unchanged. |
| tests/test_legal_docs_u8_polish.py::test_fix2_p1[x5], a10, a11, a12a[x3], a12b, a12c, a15[x3], b2, b5[x3], f1[x5] | GC-8: COMPLETE_VALUES gains AI_SWITCH_DATE / _AR; bodies unchanged. |
| tests/test_legal_docs_u8_polish.py::test_polish_a16_d3_b_names_openai_terms_for_shared_data | E21: now pins the retirement (no d3 fork, no B sentence or 30-day-limit phrase in any variant, snapshot or source). |
| tests/test_legal_docs_u8_polish.py::test_polish_b4_fill_in_end_to_end | E21: the fork-flip case uses territories (a fork that still exists) instead of d3. |
| tests/test_legal_s78.py::test_s78_r11_providers_on_request_sentence | E17 / R-S12-4: the carve-out is dated; CARVEOUT_EN and the fixture's s5_carveout_ar carry a {date} slot filled from the fill-in data (LT10's mailbox clause unchanged). |
| tests/test_legal_s78.py::test_s78_r22_manifest_categories | R-S12-11: PUBLIC_NAME_IDS gains 'anthropic' (manifest_base unchanged: S81-06's row keys are kept). |
| tests/test_legal_s78.py::test_s78_r24_privacy_keeps_the_required_elements | R-S12-5: fixture privacy_headings_en / _ar s4 re-recorded ('Anthropic and OpenAI'). |
| tests/test_legal_s78.py::test_s78_r25_new_text_passes_the_existing_scans | E15: TOS_S8_OPENAI_EN / fixture tos_s8_openai_ar = the dual-provider sentence + the list sentence; the scans it loads (s77 AR not-sold helper) moved with D4. |
| tests/test_s81_s06_anthropic_router.py::test_r36_manifest_row | R-S12-11 (NOT in GC-8's list: S81-06 merged after the prototype): S81-06's interim public_name False becomes True; every other key of the row is unchanged. |
| SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts (fence) | E1: PINNED {version: 3, sha256: 77ac6348...ebcc1} recorded in the same edit as the copy. |
| SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts V1-V4 | E2-E5: version 3; a v2 record no longer counts, Agree writes 3, a v3 record skips; the transition sentence precedes the final one and the v2 training sentence is absent (EN + AR). |
| SmartCompareApp/__tests__/setup.ts | E8: mirror 3. |
| SmartCompareApp/__tests__/consent/aiProcessingConsent.s69.test.tsx T1.19 / T1.22 | E6: also require Anthropic (EN + AR). |
| SmartCompareApp/__tests__/onboarding/step05Trust.s69.test.tsx T2.6-T2.8, T2.11-T2.12 | E7: the heading names the AI providers; the bodies name Anthropic too. |
| SmartCompareApp/__tests__/landing.brand.s69.test.ts ADDRESS_COUNTS | GC-4: privacy.html and ar/privacy.html 14 -> 15 (the /bot/ page address). |
| tests/test_legal_disclosure_s77.py PRIVACY_PAGE_ADDRESSES | GC-4: 14 -> 15. |

Not changed and green (GC-8): d5, d10, d13, d18 of tests/test_legal_disclosure_s77.py (bodies untouched), T3, T6, T7a/b, R12, D9, D14, the landing.brand brand-token assertions, test_legal_routes (the s9 phrases stay: referral_rewards selects 'empty').

## Gates
- `[pyt] tag=s12green-gate0 start=2026-10-29 04:07:42 end=2026-10-29 04:08:00 elapsed=19s bound=600s status=FAIL rc=1 (30 failed, all AssertionError / 8 passed; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[pyt] tag=s12green-legal16-pre start=2026-10-29 04:35:23 end=2026-10-29 04:36:02 elapsed=39s bound=1200s status=FAIL rc=1 (66 failed / 466 passed: the prototype's 63 E-rows + T7 schema + R9 (both the PUBLIC_NAME_IDS edit) + H1; [hermeticity] sentinel checked 532 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[pyt] tag=s12green-legal16-a start=2026-10-29 04:43:41 end=2026-10-29 04:45:07 elapsed=86s bound=1200s status=FAIL rc=1 (1 failed = H1 by design / 532 passed; [hermeticity] sentinel checked 533 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[pyt] tag=s12green-h1window start=2026-10-29 05:12:38 end=2026-10-29 05:13:01 elapsed=23s bound=600s status=OK rc=0 (H1 + H1b 2 passed with a TEMPORARY tests/fixtures/legal_v3_window.json = 2026-10-29, removed after the run, absent from the commit)`
- `[pyt] tag=s12green-ci-order start=2026-10-29 05:13:31 end=2026-10-29 05:17:08 elapsed=217s bound=1200s status=FAIL rc=1 (1 failed = H1 / 1157 passed; 18 files in sorted order: the 15-file legal set + the unit file + test_s81_s06_anthropic_router + test_s81_s04_spend_breaker; [hermeticity] sentinel checked 1158 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))`
- `[pyt] tag=s12green-unit-final start=2026-10-29 05:26:36 end=2026-10-29 05:26:58 elapsed=23s bound=600s status=FAIL rc=1 (1 failed = H1 by design / 37 passed; on the committed bytes; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[jest] tag=s12green-jest-subset start=04:46:12 end=04:46:53 rc=1 (by path: the client RED file + the five jest E-row files; 62 passed / 2 failed = the two C2 rows of the frozen client RED file; node v24.11.1, jest 29.7.0, @babel/core 7.29.0, junction verified: LinkType Junction -> the clone's SmartCompareApp/node_modules)`
- `[jest] tag=s12green-jest-full start=04:48:27 end=04:50:15 rc=1 (FULL suite once, no -u: Test Suites 2 failed, 3 skipped, 375 passed; Tests 6 failed, 13 skipped, 13 todo, 3701 passed; Snapshots 42 passed, none written; failed = the 4 accepted nativeBundle.w37 drift nodes (d5, k2, k4, k5) + the 2 C2 rows)`
- `[tsc] tag=s12green-tsc start=04:47:41 end=04:48:12 rc=0 (node node_modules/typescript/bin/tsc --noEmit, TypeScript 5.9.3)`
- machinery on the committed bytes: `fill_in_legal.py --dry-run` rc 0, nothing to write (idempotent); `render_legal_landing.py --check` rc 0; ruff E9/F63/F7/F82 'All checks passed!' and py_compile OK on the changed .py files (the default-config ruff shows the same 9 pre-existing findings as base); the commit passed the pre-commit hook.

## Comm set (zero-regression gate)
106 files (the RED's 94, re-derived at HEAD with the union rule + 12 new readers), 5 chunks of <= 25, base = a FRESH record at a8f01379 in a detached scratch worktree (no junction; removed and verified gone), HEAD = the GREEN tree. Base failures: the 30 RED rows + the 2 cold-tiktoken ERRORs of tests/test_prompt_truth.py. HEAD failures: H1 (by design, red at base too) + the same 2 ERRORs. **branch-only-new: EMPTY.** The four tests/test_precommit_hook*.py stay excluded.
- `[pyt] tag=s12green-base-00 start=2026-10-29 04:54:07 end=2026-10-29 04:54:35 elapsed=28s bound=1200s status=OK rc=0` (1274 passed; [netguard] blocked 3 attempt(s) from 1 node(s); [hermeticity] sentinel checked 1274 test(s))
- `[pyt] tag=s12green-base-01 start=2026-10-29 04:54:43 end=2026-10-29 04:56:33 elapsed=109s bound=1200s status=OK rc=0` (2202 passed, 4 deselected; [netguard] blocked 56 attempt(s) from 33 node(s); [hermeticity] sentinel checked 2202 test(s))
- `[pyt] tag=s12green-base-02 start=2026-10-29 04:56:40 end=2026-10-29 04:58:29 elapsed=109s bound=1200s status=FAIL rc=1` (1342 passed, 23 skipped, 2 deselected, 1 xfailed, 2 errors (tests/test_prompt_truth.py cold tiktoken x2); [netguard] blocked 2 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1345 test(s))
- `[pyt] tag=s12green-base-03 start=2026-10-29 04:58:36 end=2026-10-29 05:02:15 elapsed=219s bound=1200s status=FAIL rc=1` (30 failed (the 30 RED rows) / 3827 passed, 1 skipped; [netguard] blocked 63 attempt(s) from 31 node(s); [hermeticity] sentinel checked 3858 test(s))
- `[pyt] tag=s12green-base-04 start=2026-10-29 05:02:26 end=2026-10-29 05:02:40 elapsed=14s bound=1200s status=OK rc=0` (474 passed, 35 xfailed; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 509 test(s))
- `[pyt] tag=s12green-head-00 start=2026-10-29 05:02:48 end=2026-10-29 05:03:21 elapsed=32s bound=1200s status=OK rc=0` (1274 passed; [netguard] blocked 3 attempt(s) from 1 node(s); [hermeticity] sentinel checked 1274 test(s))
- `[pyt] tag=s12green-head-01 start=2026-10-29 05:03:31 end=2026-10-29 05:06:22 elapsed=171s bound=1200s status=OK rc=0` (2203 passed, 4 deselected (+1 = the new u8 control node); [netguard] blocked 53 attempt(s) from 32 node(s); [hermeticity] sentinel checked 2203 test(s))
- `[pyt] tag=s12green-head-02 start=2026-10-29 05:06:30 end=2026-10-29 05:08:17 elapsed=107s bound=1200s status=FAIL rc=1` (1342 passed, 23 skipped, 2 deselected, 1 xfailed, 2 errors (the same two cold-tiktoken ERRORs); [netguard] blocked 2 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1345 test(s))
- `[pyt] tag=s12green-head-03 start=2026-10-29 05:08:24 end=2026-10-29 05:10:37 elapsed=133s bound=1200s status=FAIL rc=1` (1 failed (H1, by design) / 3856 passed, 1 skipped; [netguard] blocked 63 attempt(s) from 31 node(s); [hermeticity] sentinel checked 3858 test(s))
- `[pyt] tag=s12green-head-04 start=2026-10-29 05:10:43 end=2026-10-29 05:10:54 elapsed=11s bound=1200s status=OK rc=0` (474 passed, 35 xfailed; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 509 test(s))

## Stated limits
- OpenAI stays named as a processor until S81-12b at key retirement; S81-12b re-pins the fence and bumps the consent version (a second re-ask, accepted by R-S12-1).
- During the OTA lag build 3 shows the v2 sheet (OpenAI + the training sentence) beside the v3 policy: over-disclosure (R-S12-1 contract risk 2). Build 3's native permission strings say OpenAI (true during the transition; provider-neutral strings in 1.0.1).
- The Anthropic facts (30-day API / 29-day batch retention, no training on API inputs, the usage-policy exception) were not read from Anthropic's documents by this agent (no web grant); every period says 'up to' and the window reading confirms them (R-S12-13).
- The web-search sentence is conditional (S81-21 not built); the catalogue, crawler and Sponsored sentences are 'may' sentences (the KB is not live: 045 unapplied, no writer flag ON).
- The dormant texts describe units not merged (S81-09, S81-22, S81-24); each recording unit re-verifies its text against its merged code and may re-word it through restore + fill (R-S12-9). One RETENTION_CLEANUP_LIVE switch covers the 044 cleanup and the two new keys.
- The deletion clause (privacy s9, Terms s13) and privacy s3.5 are unchanged (P6 / GC-1): Terms s13 still names data shared with OpenAI under its programme (true: it is kept under OpenAI's terms); generalising it is S81-12b with S81-09's device-counter wording.
- The transfer basis stays no stronger than today (LR3, P5): no PDPL art. 12-13 sentence until counsel answers (a counsel variant re-fill).
- The provisional switch date is the GREEN day (2026-10-29); the window re-dates it. The s14 device-identifier text describes the post-OTA app (S81-08), not build 3.
- Every AR string is a model draft, not a native review (list below).

## Open questions for the orchestrator
- Q1 (client RED row C2, 2 nodes, wrong row): the frozen SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts C2 calls aiConsent.hasCurrentAiConsent() and aiConsent.recordAiConsent() with NO user id, but on main both take the user id explicitly (src/services/aiConsent.ts: hasCurrentAiConsent(userId: string | null), recordAiConsent(userId: string | null, now?)); with no argument they read 'no user' (false / nothing persisted), so C2 cannot pass without changing the record API (S81-08's lane, R-S08-3). The contract C2 meant (a v2 record no longer counts; Agree writes 3; a v3 record counts) is GREEN in aiConsentV2.s75 V2a-V2c through ensureAiConsent (E3). Ruling needed: re-write C2 with the user id (e.g. hasCurrentAiConsent(userId) / ensureAiConsent(ask)), or accept a default-argument API change (not made here). tsc passes (the RED file loads the module with require, so the calls are untyped).
- Q2 (the frozen RED .py file is not committed): the hook's gitleaks step (rule generic-api-key) refuses tests/test_s81_12_legal_v3.py:211, BASE_I18N_KEYS_SHA256 = "9ff8684f..." "...14273" (a hex literal, split, under a KEY-named variable). The hook passes --ignore-gitleaks-allow and reads .gitleaks.toml from HEAD (a .gitleaksignore is refused), so only an edit of that frozen line clears it, e.g. rename the constant to a name without key/token/secret (BASE_I18N_NAMESET_SHA256, 3 occurrences incl. the P3 docstring) or wrap the literal in parentheses. The file is byte-identical (94ef61a5...d6b5), staged, uncommitted. Ruling needed before the PR.
- Q3 (an E-row outside GC-8's list): tests/test_s81_s06_anthropic_router.py::test_r36_manifest_row pinned S81-06's interim public_name False; R-S12-11 assigns the flip to this unit and R9 requires True, so the pin moved (one assertion + a dated docstring sentence). Confirm.
- Q4 (T8 EN): beyond GC-8's T8-AR, R-S12-4 asks the EN pattern amended too: D3_FORBIDDEN_EN['A'] now reads 'data[- ]sharing program' (case-insensitive), with the same exact-sentence allow-list, and a new pin node test_t8_history_allow_list_is_exact carries the positive control and the date mutant. Confirm.
- Q5 (comm set): re-derived at HEAD = 106 files (the RED's 94 + 12: test_s81_s06_anthropic_router, test_s81_s06_router_gate_rows, test_s81_kb_schema, test_s81_s04_spend_breaker (opens CLAUDE.md), five module-path readers, two .github readers, test_channel_freshness). The CLAUDE.md-mention class was narrowed to tests that open CLAUDE.md by a string path (3 files); 23 files only mention it in prose and were not added.

## [NATIVE READ] Arabic strings (model-drafted MSA; the owner's reading list)
- [NATIVE READ] privacy s2 / s4, Terms s8 (dual-provider sentence): يستخدم ميّز مزوّدي ذكاء اصطناعي لمعالجة طلباتك: Anthropic, PBC وOpenAI, L.L.C. وننقل هذه المعالجة إلى Anthropic؛ وإلى أن يكتمل الانتقال، تعالج OpenAI بعض الطلبات أو جميعها، بما فيها الصور.
- [NATIVE READ] privacy s2 (AI use): ونستخدم الذكاء الاصطناعي لتحديد المنتجات وكتابة المقارنات (القسم 4)، ونبحث في مواقع المتاجر الإلكترونية عن الأسعار.
- [NATIVE READ] privacy s2, Terms s8 (bare not-sold promise (base text, unchanged words)): لا نبيع بياناتك الشخصية ولا نبادلها مقابل أي شيء ذي قيمة، ولا نشاركها مع وسطاء البيانات أو المعلنين.
- [NATIVE READ] privacy s2 (past-tense programme sentence): وكنا نشارك في برنامج مشاركة البيانات لدى OpenAI، الذي كان يسمح لها باستخدام المدخلات التي أرسلناها إليها والمخرجات التي أنتجتها منها لتقييم نماذجها وتدريبها مقابل قدر من الاستخدام المجاني لخدمتها؛ وقد انتهت مشاركتنا فيه (القسم 4).
- [NATIVE READ] privacy s3.2 / s3.3 / s3.6 / s4 ('our AI providers' phrase): مزوّدي الذكاء الاصطناعي لدينا
- [NATIVE READ] privacy s4 (heading): ## 4. المقارنات المُعدّة بالذكاء الاصطناعي (Anthropic وOpenAI)
- [NATIVE READ] privacy s4 (Anthropic facts): تعالج Anthropic, PBC المعلومات التي نرسلها إليها لتقديم خدمتها لنا وفق شروطها التجارية، ولا تستخدم هذه المعلومات لتدريب نماذجها. وتحتفظ Anthropic بالمعلومات التي تتلقاها لمدة تصل إلى 30 يومًا، وبالطلبات التي نرسلها على دفعات ونتائجها لمدة تصل إلى 29 يومًا، ما لم تحتج إلى الاحتفاظ بها مدة أطول لإنفاذ سياسات الاستخدام لديها أو للامتثال للقانون.
- [NATIVE READ] privacy s4 (conditional web search): وإذا استخدمنا خدمة البحث على الويب لدى Anthropic للبحث عن معلومات المنتجات، يتلقى مزوّد البحث لديها عبارات البحث، مثل أسماء المنتجات، ولا يتلقى هويتك أبدًا.
- [NATIVE READ] privacy s4 (OpenAI transition): وإلى أن يكتمل الانتقال إلى Anthropic، تعالج OpenAI بعض الطلبات أو جميعها، بما فيها الصور، وتتلقى أنواع المعلومات نفسها الموضّحة أعلاه.
- [NATIVE READ] privacy s4 (dated history sentence ({date} = AI_SWITCH_DATE_AR)): وكنا نشارك في برنامج مشاركة البيانات لدى OpenAI، الذي أتاح لها استخدام المدخلات التي أرسلناها إليها والمخرجات التي أنتجتها منها لتقييم نماذجها وتدريبها مقابل قدر من الاستخدام المجاني لخدمتها، وانتهت مشاركتنا في هذا البرنامج في {date}.
- [NATIVE READ] privacy s4 (OpenAI since the switch): ومنذ ذلك التاريخ لا تستخدم OpenAI البيانات التي نرسلها إليها لتدريب نماذجها، وقد تحتفظ بها في سجلات مراقبة إساءة الاستخدام لمدة تصل إلى 30 يومًا. وتظل البيانات التي شوركت مع OpenAI ضمن هذا البرنامج قبل ذلك التاريخ خاضعة لشروط OpenAI.
- [NATIVE READ] privacy s5 (Anthropic bullet): - **Anthropic:** تعالج الطلبات التي نرسلها إليها لتحديد المنتجات وكتابة المقارنات (القسم 4).
- [NATIVE READ] privacy s5 (OpenAI bullet): - **OpenAI:** تعالج بعض الطلبات أو جميعها، بما فيها الصور، إلى أن يكتمل انتقالنا إلى Anthropic (القسم 4).
- [NATIVE READ] privacy s5 (email-delivery fragment): ، مباشرة أو عبر مزوّد لإرسال البريد الإلكتروني
- [NATIVE READ] privacy s5 (carve-out head ({date})): باستثناء ما يوضّحه القسم 4 بشأن البيانات التي شوركت مع OpenAI قبل {date} وما يوضّحه هذا القسم
- [NATIVE READ] privacy s6 (catalogue + crawler): وقد نحتفظ أيضًا بكتالوج خاص بنا لمعلومات المنتجات (أسماء المنتجات وأحجامها وأسعارها، وعناوين صور المنتجات على الويب وعناوين الصفحات التي جاءت منها) لتصبح المقارنات اللاحقة أسرع وأكمل. ويقرأ زاحف الكتالوج لدينا صفحات المتاجر التي يسمح بها ملف robots.txt الخاص بكل منها، ويعرّف نفسه بسلسلة وكيل المستخدم المنشورة على الصفحة https://getmyez.com/bot/ في موقعنا. وقد نضيف أيضًا تفاصيل منتجات يُدخلها فريقنا يدويًا من صفحات يزورها بالطريقة المعتادة، وموجزات منتجات وبيانات يرخّصها لنا شركاؤنا، وتفاصيل المنتجات التي نجدها أثناء المقارنات. ولا يحتوي الكتالوج إلا على معلومات المنتجات، ولا يحتوي أبدًا على هوية من أجرى المقارنة.
- [NATIVE READ] privacy s6 (Sponsored): وقد تدفع المتاجر مقابل عرض رابط إلى موقعها الإلكتروني أو متجرها بجانب أحد المنتجات؛ ويحمل هذا الرابط علامة «مموّل». ولا يغيّر الدفع أبدًا طريقة مقارنة المنتجات أو تقييمها أو ترتيبها. وقد يُسجَّل النقر على رابط متجر مع نشاطك الآخر داخل التطبيق (القسم 3.4).
- [NATIVE READ] privacy s8 (photos line): ويوضّح القسم 4 ما يحتفظ به مزوّدو الذكاء الاصطناعي لدينا.
- [NATIVE READ] privacy s12 (AI disclosure):  ويوضّح التطبيق أن المقارنات يكتبها الذكاء الاصطناعي، ويطلب إذنك قبل مقارنتك الأولى، ونفحص الطلبات والنتائج بحثًا عن المحتوى غير الآمن.
- [NATIVE READ] privacy s14 (device identifiers): يحتفظ التطبيق برموز تسجيل الدخول وبمعرّف تثبيت عشوائي مخزّن بأمان في Keychain على جهاز iPhone، ويحتفظ في مساحة تخزين التطبيق بملخص ملفك الشخصي، وعمليات بحثك الأخيرة، وإجاباتك في أسئلة البداية التي لم تُرسَل بعد، وسجل إذنك بالمعالجة بالذكاء الاصطناعي، وإعدادات اللغة، ونسخة محفوظة من هذه السياسة. وخلال مرحلة انتقالية، قد يرسل التطبيق أيضًا إلى خوادمنا معرّفًا أقدم مشتقًا من خصائص الجهاز، وذلك فقط عند إنشاء الحساب وتسجيل الدخول عبر Apple أو Google والمشاركة. يؤدي تسجيل الخروج إلى إزالة رموز تسجيل الدخول وملخص الملف الشخصي؛ ويؤدي حذف حسابك أيضًا إلى إزالة سجل إذن المعالجة بالذكاء الاصطناعي. وقد تبقى العناصر المحفوظة في Keychain على جهاز iPhone بعد حذف التطبيق.
- [NATIVE READ] Terms s7 (Sponsored + catalogue): وقد تدفع المتاجر مقابل عرض رابط إلى موقعها الإلكتروني أو متجرها بجانب أحد المنتجات؛ ويحمل هذا الرابط علامة «مموّل». ولا يغيّر الدفع أبدًا طريقة مقارنة المنتجات أو تقييمها أو ترتيبها، ولا يُعدّ الرابط المموّل توصية من ميّز. وقد تأتي بعض معلومات المنتجات من كتالوج المنتجات الخاص بنا، الذي يوضّحه القسم 6 من سياسة الخصوصية.
- [NATIVE READ] Terms s8 (list sentence): ويبيّن القسم 4 من سياسة الخصوصية ما نرسله إليهما، ويطلب التطبيق إذنك قبل مقارنتك الأولى أو أول عملية مسح.
- [NATIVE READ] Terms s8 (past-tense programme sentence): وكنا نشارك في برنامج مشاركة البيانات لدى OpenAI على النحو الذي يوضّحه القسم 4 من سياسة الخصوصية؛ وقد انتهت مشاركتنا فيه.
- [NATIVE READ] variants (dormant) (free_limits nonempty): استخدام ميّز مجاني. يمكن لكل جهاز إجراء ما يصل إلى 3 مقارنات في اليوم، تتشاركها جميع الحسابات المستخدمة على ذلك الجهاز؛ ويُعاد ضبط العدد عند <PLACEHOLDER:DEVICE_QUOTA_RESET_AR>. وقد تختلف هذه الحدود من حساب أو جهاز إلى آخر، وقد نغيّرها. ولا يبيع هذا الإصدار من التطبيق أي اشتراكات أو مشتريات داخل التطبيق، ولا تمنحك هذه الشروط حقًا في فئة مدفوعة أو في حدود أعلى.
- [NATIVE READ] variants (dormant) (referral_rewards nonempty): عندما تشارك مقارنة من ميّز مع صديق، يرى صديقك المقارنة؛ ومكافآت الإحالة متوقفة مؤقتًا إلى أن نعيد تصميمها.

**المكافآت متوقفة مؤقتًا:** لا تضيف الدعوة الناجحة مقارنات في الوقت الحالي. وتظل المقارنات الإضافية التي مُنحت سابقًا قابلة للاستخدام إلى أن تنتهي صلاحيتها أو يسري الحد اليومي للجهاز. ولا يزال بإمكانك أن تكون مصدر ما يصل إلى **3 دعوات ناجحة لكل جهاز** طوال عمر ذلك الجهاز.
- [NATIVE READ] variants (dormant) (usage_counters nonempty): - **عدادات الاستخدام:** تُحفظ العدادات اليومية لحسابك ولجهازك (ويُحفظ عداد الجهاز برمز أحادي الاتجاه مشتق من معرّف الجهاز) في التخزين المؤقت، وتنتهي صلاحيتها خلال مدة تصل إلى ساعة تقريبًا بعد إعادة الضبط اليومية التالية عند <PLACEHOLDER:DEVICE_QUOTA_RESET_AR>. ويبقى العدد الإجمالي لمقارناتك مرتبطًا بحسابك؛ ويوضّح القسم 9 ما يزيله حذف حسابك.
- [NATIVE READ] variants (dormant) (COMPARE_RUNS_CLAUSE nonempty): - **سجلات تشغيل المقارنات:** سجل لكل مقارنة (وقت إجرائها، والمصادر ونماذج الذكاء الاصطناعي التي استُخدمت فيها، ومدة كل خطوة، ونتيجتها) مع رمز أحادي الاتجاه مشتق من معرّف جهازك، ويبقى مرتبطًا بحسابك عبر تلك المقارنة إلى أن تحذف المقارنة أو حسابك، ثم يُحتفظ به دون هذا الارتباط لمدة تصل إلى {value}.
- [NATIVE READ] variants (dormant) (KB_FEEDBACK_CLAUSE nonempty): - **ملاحظاتك على نتائج المقارنات:** تُحفظ إجاباتك عن أسئلتنا حول النتيجة بمفتاح مستعار، وهو رمز أحادي الاتجاه (HMAC) مشتق من معرّف جهازك وليس المعرّف نفسه أبدًا، لمدة تصل إلى 12 شهرًا، وتُحذف مع سجلات المقارنات المرتبطة بحسابك.
- [NATIVE READ] variants (dormant) (AUTH_THROTTLE_CLAUSE nonempty): - **عدادات محاولات تسجيل الدخول وإنشاء الحساب وإعادة تعيين كلمة المرور:** تُحفظ في التخزين المؤقت برمز أحادي الاتجاه مشتق من عنوان البريد الإلكتروني أو الحساب، لمدة تصل إلى {value}.
- [NATIVE READ] app (i18n ar.json) (aiConsent.body v3): لتحديد المنتجات وكتابة المقارنة، يرسل ميّز أسماء المنتجات أو الروابط (مع نص صفحاتها) أو الصور التي تلتقطها أو تختارها إلى مزودي الذكاء الاصطناعي لديه، Anthropic وOpenAI. وقد يرسل أيضا التفضيلات المحفوظة في ملفك الشخصي (ومنها تفضيلات مقترحة بناء على إجاباتك في أسئلة البداية)، مثل الأولويات وفئة الميزانية، وبلدك ولغتك ومنطقتك. وننقل هذه المعالجة إلى Anthropic، وإلى أن يكتمل الانتقال، تعالج OpenAI بعض الطلبات أو جميعها، بما فيها الصور. لا يرسل اسمك أو بريدك الإلكتروني أو بيانات حسابك.
- [NATIVE READ] app (i18n ar.json) (onboarding.s5.privacy_anon_head): ما يصل إلى مزودي الذكاء الاصطناعي
- [NATIVE READ] app (i18n ar.json) (onboarding.s5.privacy_anon_body): لكتابة كل مقارنة، يرسل ميّز إلى مزودي الذكاء الاصطناعي لديه، Anthropic وOpenAI، أسماء المنتجات وتفضيلاتك مثل الأولويات وفئة الميزانية، دون اسمك أو بريدك أو حسابك.

Owner steps (names only): the flip-window checklist above; counsel item 17 of OWNER_ACTIONS_S81 (transfer basis, minors, Sponsored, operator capture, retention wording) answers through TRANSFER_BASIS_COUNSEL(_AR) / LEGAL_BASIS_COUNSEL(_AR) with counsel_review true, never a hand edit; the native read of the list above or the owner's explicit acceptance of the drafts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

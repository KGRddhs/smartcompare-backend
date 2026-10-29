# S81_12_REBASE_EVIDENCE (rebase round, RULINGS_REBASE_S81_12; agent Opus 5.5, 2026-10-29)

Base origin/main 6c14ac954f601902d322547de04982033aca5925; HEAD 5ae65723f37bc8089cb88050b9a047871db05a29; gate-rows blob b98caa6aebff37eea7ad4c8078cad55e9fde3538c261da4d9609f56b52c10436.

## Full E-rows table (unabridged, from the fix-round-2 draft, plus the rebase rows)
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
| tests/test_s81_12_legal_v3.py (frozen RED file) BASE_I18N_KEYS_SHA256 -> BASE_I18N_NAMESET_SHA256 | EK1 (F1-1, sanctioned): gitleaks generic-api-key matched the KEY-named constant; rename only, the literal unchanged; new frozen sha in the fix report. |
| SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts (frozen client RED file) C2 | ECF1 (F1-11, sanctioned): hasCurrentAiConsent(userId) / recordAiConsent(userId) with the synthetic user id (consent is per account, R-S08-3; the record API unchanged); C2 green at once. |
| tests/test_legal_docs_u8_d3c.py TERMS_LICENCE_EN (d3c i; read by test_legal_disclosure_s77 d3[en]) | EF6a (F1-6): the Terms s8 licence names 'our AI providers'. |
| tests/test_legal_s78.py TOS_HEADINGS_EN (s78 R16) | EF6b (F1-6): the Terms s8 heading names 'our AI providers'. |
| tests/fixtures/legal_d3c_u8.json ug12_ar.terms_licence (d3c i; s77 d3[ar]) | EF6c (F1-6): the AR licence names 'our AI providers' (the plural construct). |
| tests/fixtures/legal_fill_in_u8.json _values_comment (no row reads it) | F1-4: the GC-5 sentence restated ('public at publication'; the merge-time premise withdrawn); the notice re-dates with AI_SWITCH_DATE. |
| tests/test_s81_12_legal_v3.py (frozen RED file) R17[en]: S14_EN_REQUIRED, S14_EN_FORBIDDEN, the older-form sentence check, the R17 docstring | EK2 (F2-1, sanctioned): re-pinned to the F1-2 s14 wording (the proposed diff applied exactly); sha256 9a9dcb0ee1da55f94f9ce109dfaa3caa94871d70938cd1b6fd7cbff85f4db344 -> 1372db2462a6713455f5b4ecb09d989c76278daafcca1ba60b03f3bbacf84f29; the file 37 / 38 (H1 only). |
| tests/test_s81_12_gate_rows.py::test_g_d_anthropic_no_training_sentence_unqualified[en/ar] | F2-2(a): + the Anthropic no-training sentence VERBATIM as rendered, EN + AR (the G-a pattern); kills S4 (MS4). |
| tests/test_s81_12_gate_rows.py::test_g_b_no_openai_training_permission_outside_the_history_sentence[en] | F2-2(b): PERMIT_EN widened to the 'may use' / 'may train' forms, and 'its models' counts like training, outside the ONE dated history sentence; kills S3 (MS3). |
| tests/test_s81_12_gate_rows.py::test_g_i_s14_two_random_identifiers_and_the_older_form_cutoff[en/ar] (NEW) | F2-2(c): the F1-2 s14 wording EN + AR, 'device properties' absent; kills S2 (MS2). |
| tests/test_s81_12_gate_rows.py::test_g_j_crawler_sentence_hedged[en/ar] (NEW) | F2-2(d): the F1-7 crawler hedge EN ('When we run it, our catalogue crawler') + the AR hedged opening as rendered; kills S1 (MS1). |

Not changed and green (GC-8): d5, d10, d13, d18 of tests/test_legal_disclosure_s77.py (bodies untouched), T3, T6, T7a/b, R12, D9, D14, the landing.brand brand-token assertions, test_legal_routes (the s9 phrases stay: referral_rewards selects 'empty').

Not changed and green: every frozen row except the three sanctioned amendments (EK1, ECF1, EK2); R17[en] is green since EK2.
| tests/test_s81_12_gate_rows.py::test_g_i2_s14_keychain_fallback_identifier_clause[en/ar] (NEW, rebase) | RB12-6 / F2-7: the clause once in s14 (EN verbatim; AR twin) and in landing/privacy.html / landing/ar/privacy.html; killed by MR-ar. |
| SmartCompareApp/__tests__/setup.ts (rebase) | RB12-3: S81-08 mockConsent shape, AI_CONSENT_VERSION 3. |
| PROPOSED EK3: tests/test_s81_12_legal_v3.py P3 constants | BASE_I18N_KEY_COUNT 1010 -> 1013; BASE_I18N_NAMESET_SHA256 9ff8684f8b72ed2dc7a6d3c7e80c684696bb0d5f4952aed43fabc4a13cb14273 -> 3d786372b3ca325bc294b675e4e7c0cf3ec39140e4b919860483a3987ee4ab9f (keep the split literal), recomputed from main 6c14ac95 per the row docstring; NOT applied. |
| PROPOSED E-S08a: SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts:338 | `plantConsent(2);` -> `plantConsent(3);` (or the module constant): the planted record encodes the old consent version; 7 nodes red under v3. NOT applied. |
| PROPOSED E-S08b: SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx:430 | `toBe('2')` -> `toBe('3')` (or String(AI_CONSENT_VERSION)): L1 red under v3. NOT applied; probe with both edits 37 / 37, restored, sha_ok. |

## Mutation tables
## Mutation table (F1-3 rows, fix round 1, through the U8 machinery; F2-2 rows MS1-MS4, fix round 2, on byte copies of the rendered policies under .qa-mutation.lock; every mutant restored and sha-checked)
| mutant | what | killing rows | verdict | run |
|---|---|---|---|---|
| M0 | control: restore + fill with no edit | - | NEUTRAL | `[pyt] tag=s12fix1-mut-M0 start=2026-10-29 08:04:36 end=2026-10-29 08:04:55 elapsed=19s bound=600s status=OK rc=0` |
| Ma_en | X1 / L10m: OpenAI may train since the switch (EN s4) | test_g_a_openai_no_training_since_the_switch[en], test_g_b_no_openai_training_permission_outside_the_history_sentence[en] | KILLED | `[pyt] tag=s12fix1-mut-Ma_en start=2026-10-29 08:04:58 end=2026-10-29 08:05:23 elapsed=25s bound=600s status=FAIL rc=1` |
| Ma_ar | X10: OpenAI may train since the switch (AR s4) | test_g_a_openai_no_training_since_the_switch[ar], test_g_b_no_openai_training_permission_outside_the_history_sentence[ar] | KILLED | `[pyt] tag=s12fix1-mut-Ma_ar start=2026-10-29 08:05:28 end=2026-10-29 08:05:58 elapsed=30s bound=600s status=FAIL rc=1` |
| Mb_en | a present-tense training permission in privacy s2 (EN), outside the dated history sentence | test_g_b_no_openai_training_permission_outside_the_history_sentence[en] | KILLED | `[pyt] tag=s12fix1-mut-Mb_en start=2026-10-29 08:06:04 end=2026-10-29 08:06:19 elapsed=15s bound=600s status=FAIL rc=1` |
| Mb_ar | a training permission verb in privacy s2 (AR), outside the dated history sentence | test_g_b_no_openai_training_permission_outside_the_history_sentence[ar] | KILLED | `[pyt] tag=s12fix1-mut-Mb_ar start=2026-10-29 08:06:21 end=2026-10-29 08:06:41 elapsed=20s bound=600s status=FAIL rc=1` |
| Mc_en | X4: the pre-switch carve-out sentence dropped (EN s4) | test_g_c_pre_switch_carve_out_sentence[en] | KILLED | `[pyt] tag=s12fix1-mut-Mc_en start=2026-10-29 08:06:43 end=2026-10-29 08:07:06 elapsed=23s bound=600s status=FAIL rc=1` |
| Mc_ar | the pre-switch carve-out sentence dropped (AR s4) | test_g_c_pre_switch_carve_out_sentence[ar] | KILLED | `[pyt] tag=s12fix1-mut-Mc_ar start=2026-10-29 08:07:08 end=2026-10-29 08:07:27 elapsed=19s bound=600s status=FAIL rc=1` |
| Md_en | X12: the Anthropic no-training sentence qualified (EN) | test_g_d_anthropic_no_training_sentence_unqualified[en] | KILLED | `[pyt] tag=s12fix1-mut-Md_en start=2026-10-29 08:07:29 end=2026-10-29 08:07:46 elapsed=16s bound=600s status=FAIL rc=1` |
| Md_ar | X9: Anthropic may train (AR s4) | test_g_d_anthropic_no_training_sentence_unqualified[ar] | KILLED | `[pyt] tag=s12fix1-mut-Md_ar start=2026-10-29 08:07:48 end=2026-10-29 08:08:04 elapsed=16s bound=600s status=FAIL rc=1` |
| Me_en | Anthropic retention 30 -> 90 days (EN s4) | test_g_e_anthropic_retention_up_to_30_days[en] | KILLED | `[pyt] tag=s12fix1-mut-Me_en start=2026-10-29 08:08:07 end=2026-10-29 08:08:22 elapsed=15s bound=600s status=FAIL rc=1` |
| Me_ar | X8: Anthropic retention 30 -> 90 days (AR s4) | test_g_e_anthropic_retention_up_to_30_days[ar] | KILLED | `[pyt] tag=s12fix1-mut-Me_ar start=2026-10-29 08:08:24 end=2026-10-29 08:08:36 elapsed=12s bound=600s status=FAIL rc=1` |
| Mf_en | 'including photos' dropped from privacy s2 (EN) | test_g_f_dual_provider_sentence_carries_including_photos[en] | KILLED | `[pyt] tag=s12fix1-mut-Mf_en start=2026-10-29 08:08:37 end=2026-10-29 08:08:47 elapsed=10s bound=600s status=FAIL rc=1` |
| Mf_ar | X2: 'including photos' dropped from privacy s2 (AR) | test_g_f_dual_provider_sentence_carries_including_photos[ar] | KILLED | `[pyt] tag=s12fix1-mut-Mf_ar start=2026-10-29 08:08:48 end=2026-10-29 08:08:54 elapsed=5s bound=600s status=FAIL rc=1` |
| Mg_en | M6s: the Terms s7 labelling clause dropped (EN) | test_g_g_terms_s7_sponsored_label_clause[en] | KILLED | `[pyt] tag=s12fix1-mut-Mg_en start=2026-10-29 08:08:56 end=2026-10-29 08:09:17 elapsed=21s bound=600s status=FAIL rc=1` |
| Mg_ar | the Terms s7 labelling clause dropped (AR) | test_g_g_terms_s7_sponsored_label_clause[ar] | KILLED | `[pyt] tag=s12fix1-mut-Mg_ar start=2026-10-29 08:09:19 end=2026-10-29 08:09:30 elapsed=11s bound=600s status=FAIL rc=1` |
| Mh_en | the privacy notice carries a stale literal date (EN) | test_g_h_dated_change_notice_at_the_top[en] | KILLED | `[pyt] tag=s12fix1-mut-Mh_en start=2026-10-29 08:09:32 end=2026-10-29 08:09:52 elapsed=20s bound=600s status=FAIL rc=1` |
| Mh_ar | the Terms AR notice loses 'your permission again' | test_g_h_dated_change_notice_at_the_top[ar] | KILLED | `[pyt] tag=s12fix1-mut-Mh_ar start=2026-10-29 08:09:55 end=2026-10-29 08:10:15 elapsed=19s bound=600s status=FAIL rc=1` |
| MS1 | S1: the crawler hedge removed (privacy s6, EN + AR) | test_g_j_crawler_sentence_hedged[en], [ar] | KILLED | `[pyt] tag=s12fix2-ms1 start=2026-10-29 10:42:26 end=2026-10-29 10:43:14 elapsed=48s bound=600s status=FAIL rc=1` |
| MS2 | S2: the second-identifier clause dropped from privacy s14 (EN + AR) | test_g_i_s14_two_random_identifiers_and_the_older_form_cutoff[en], [ar] | KILLED | `[pyt] tag=s12fix2-ms2 start=2026-10-29 10:43:38 end=2026-10-29 10:44:16 elapsed=38s bound=600s status=FAIL rc=1` |
| MS3 | S3: 'OpenAI may train its models on its abuse-monitoring logs.' appended to privacy s4 (EN) | test_g_b_no_openai_training_permission_outside_the_history_sentence[en] | KILLED | `[pyt] tag=s12fix2-ms3 start=2026-10-29 10:44:36 end=2026-10-29 10:45:10 elapsed=34s bound=600s status=FAIL rc=1` |
| MS4 | S4: the Anthropic no-training sentence qualified with ' without our permission' (EN + the AR twin) | test_g_d_anthropic_no_training_sentence_unqualified[en], [ar] | KILLED | `[pyt] tag=s12fix2-ms4 start=2026-10-29 10:45:28 end=2026-10-29 10:46:02 elapsed=34s bound=600s status=FAIL rc=1` |
| MR-ar (rebase) | the RB12-6 clause dropped from the AR pre-fill snapshot, restore + fill (only app/legal/privacy_policy_ar.md, landing/ar/privacy.html and the AR snapshot moved) | test_g_i2_s14_keychain_fallback_identifier_clause[ar] (AssertionError; [en] green) | KILLED | see the s12rb-mut-ar [pyt] line below; restore of 20 files sha-verified |

## Every [pyt] line of this round (with [netguard] / [hermeticity])
```
[pyt] tag=s12rb-units-pre start=2026-10-29 17:10:30 end=2026-10-29 17:16:32 elapsed=362s bound=600s status=FAIL rc=1  (both unit files; the first gate-rows node hit the per-test 120 s Timeout inside an openai import: a measurement failure, re-run once)
[pyt] tag=s12rb-units-pre2 start=2026-10-29 17:17:44 end=2026-10-29 17:19:39 elapsed=114s bound=600s status=FAIL rc=1  (2 failed = H1 by design + P3 / 58 passed; [hermeticity] sentinel checked 60 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s12rb-mut-ar start=2026-10-29 17:22:15 end=2026-10-29 17:22:40 elapsed=25s bound=600s status=FAIL rc=1  (MR-ar: 1 failed = G-i2[ar] AssertionError / 1 passed, 20 deselected; [hermeticity] sentinel checked 2 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s12rb-test_legal_disclosure_s77 start=2026-10-29 17:29:14 end=2026-10-29 17:29:53 elapsed=38s bound=600s status=OK rc=0  (31 passed; [hermeticity] sentinel checked 31 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s12rb-test_legal_s78 start=2026-10-29 17:30:02 end=2026-10-29 17:30:48 elapsed=46s bound=600s status=OK rc=0  (29 passed; [hermeticity] sentinel checked 29 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s12rb-r8unit start=2026-10-29 17:34:50 end=2026-10-29 17:37:28 elapsed=157s bound=600s status=FAIL rc=1  (tests/test_sentry_channels_u8d_unit.py: 33 passed then the per-test Timeout inside test_u8d_red_options_init_kwargs -> init_sentry import chain)
[pyt] tag=s12rb-r8 start=2026-10-29 17:37:34 end=2026-10-29 17:41:47 elapsed=253s bound=600s status=OK rc=0  (tests/test_sentry_channels_u8d.py: 132 passed; [hermeticity] sentinel checked 132 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s12rb-paidmeter start=2026-10-29 17:41:56 end=2026-10-29 17:43:26 elapsed=90s bound=600s status=OK rc=0  (tests/test_paid_route_metering.py, no flag exists: 21 passed; [hermeticity] sentinel checked 21 test(s); [netguard] blocked 2 attempt(s) from 2 node(s): neutralized.supabase.invalid:443 sentinel)
[pyt] tag=s12rb-r8unit-rerun start=2026-10-29 17:47:29 end=2026-10-29 17:50:01 elapsed=152s bound=600s status=FAIL rc=1  (the re-run: per-test Timeout in the first node, inside the conftest _reset_variant_descriptor_memo import of price_service -> extraction_service: NOT MEASURED)
[pyt] tag=s12rb-ci-order start=2026-10-29 17:52:36 end=2026-10-29 17:59:09 elapsed=393s bound=1200s status=FAIL rc=1  (11 files: 2 failed = H1 by design + P3 / 694 passed; [hermeticity] sentinel checked 696 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
ci_order.log: [hermeticity] sentinel checked 696 test(s)
ci_order.log: [netguard] blocked 0 attempt(s) from 0 node(s)
mut_ar.log: [hermeticity] sentinel checked 2 test(s)
mut_ar.log: [netguard] blocked 0 attempt(s) from 0 node(s)
paidmeter.log: [hermeticity] sentinel checked 21 test(s)
paidmeter.log: [netguard] blocked 2 attempt(s) from 2 node(s)
r8.log: [hermeticity] sentinel checked 132 test(s)
r8.log: [netguard] blocked 0 attempt(s) from 0 node(s)
test_legal_disclosure_s77.log: [hermeticity] sentinel checked 31 test(s)
test_legal_disclosure_s77.log: [netguard] blocked 0 attempt(s) from 0 node(s)
test_legal_s78.log: [hermeticity] sentinel checked 29 test(s)
test_legal_s78.log: [netguard] blocked 0 attempt(s) from 0 node(s)
units_pre2.log: [hermeticity] sentinel checked 60 test(s)
units_pre2.log: [netguard] blocked 0 attempt(s) from 0 node(s)
```

## Client, conflict and probe records
### jest_summary.txt
```
node v24.11.1 jest 29.7.0 @babel/core 7.29.0
[jest] tag=s12rb-s81_08 start=2026-10-29 17:33:38 end=2026-10-29 17:35:56 rc=1
Test Suites: 2 failed, 8 passed, 10 total
Tests:       8 failed, 92 passed, 100 total
Snapshots:   0 total
FAIL __tests__/s81_08/requestHeaders.s81_08.test.ts (19.362 s)
FAIL __tests__/s81_08/resetRender.s81_08.test.tsx (33.469 s)
[jest] tag=s12rb-s81_12 start=2026-10-29 17:36:03 end=2026-10-29 17:36:56 rc=0
Test Suites: 6 passed, 6 total
Tests:       64 passed, 64 total
Snapshots:   0 total
[jest] tag=s12rb-fences start=2026-10-29 17:37:09 end=2026-10-29 17:38:31 rc=1
Test Suites: 1 failed, 13 passed, 14 total
Tests:       4 failed, 236 passed, 240 total
Snapshots:   0 total
FAIL __tests__/config/nativeBundle.w37.test.ts (32.82 s)
[jest] tag=s12rb-full start=2026-10-29 17:38:45 end=2026-10-29 17:42:16 rc=1
Test Suites: 3 failed, 3 skipped, 384 passed, 387 of 390 total
Tests:       12 failed, 13 skipped, 13 todo, 3795 passed, 3833 total
Snapshots:   42 passed, 42 total
FAIL __tests__/s81_08/requestHeaders.s81_08.test.ts (23.599 s)
FAIL __tests__/s81_08/resetRender.s81_08.test.tsx (29.107 s)
FAIL __tests__/config/nativeBundle.w37.test.ts (30.345 s)
FAIL __tests__/s81_08/requestHeaders.s81_08.test.ts (23.599 s)
FAIL __tests__/s81_08/resetRender.s81_08.test.tsx (29.107 s)
FAIL __tests__/config/nativeBundle.w37.test.ts (30.345 s)
DONE 17:42:25
```

### tsc.log
```
node v24.11.1 typescript 5.9.3
[tsc] tag=s12rb-tsc start=17:29:08 end=17:30:12 rc=0
```

### eslint.log
```
[eslint] tag=s12rb-eslint start=18:01:56 end=18:05:50 rc=0 eslint 9.39.4
```

### probe_s08_result.txt
```
[jest] tag=s12rb-probe-s08 start=2026-10-29 17:59:55 end=2026-10-29 18:01:25 rc=0 Test Suites: 2 passed, 2 total | Tests:       37 passed, 37 total
restored __tests__/s81_08/requestHeaders.s81_08.test.ts sha_ok=True
restored __tests__/s81_08/resetRender.s81_08.test.tsx sha_ok=True
```

### resolve_1.log
```
replaying 3c4a198dca34745ad105aef404f381f13a393f58 conflicted ['CLAUDE.md', 'SmartCompareApp/__tests__/setup.ts']
CLAUDE.md index_sha b744e8c606b9e29a3a1880f8407adb37ceb6377f79b2736b1ed39484bac50d25 expected_sha b744e8c606b9e29a3a1880f8407adb37ceb6377f79b2736b1ed39484bac50d25 MATCH {'lines': 995, 'diff_vs_base_lines': [16, 198], 'row_index_1based': 531, 'nonascii_main': (1353, 3937), 'nonascii_x': (1353, 3937), 'nonascii_base': (1353, 3937), 'nonascii_out': (1353, 3937), 'session81_order': ['**SESSION 81 flag (D03 DENY-AND-GUARDS, 2026-10-22; default ', '**SESSION 81 flag (S81-03 LLM-LEDGER-V2, 2026-10-23; default', '**SESSION 81 flag (ST1 LOOP-STALL, 2026-10-23; default OFF, ', '**SESSION 81 flag (S81-05 REQUEST-CONTEXT, 2026-10-23; defau', '**SESSION 81 flag (S81-04 SPEND-BREAKER, 2026-10-23; default', '**SESSION 81 unit (S81-14 KB-SCHEMA, 2026-10-24; NO flag and', '**SESSION 81 flags (S81-06 ANTHROPIC-ROUTER, 2026-10-24; def', '**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, 2026-1', '**SESSION 81 flags (S81-15 REGISTRY-ROBOTS-DENY, 2026-10-28;', '**SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, 2026-10-29; NO r', '**SESSION 81 unit (S81-12 LEGAL-V3, 2026-10-29; NO flag; a H']}
SmartCompareApp/__tests__/setup.ts index_sha 1b7eda0735c9ff74f83cdf2386505d0e8d2eca5b16492f267e2fd4e2d2597d4d expected_sha 1b7eda0735c9ff74f83cdf2386505d0e8d2eca5b16492f267e2fd4e2d2597d4d MATCH {'lines': 53}
still conflicted: []
```

### resolve_2.log
```
replaying e3bcf76839ee87f6908aac04f0f06e8f81211a31 conflicted ['CLAUDE.md']
CLAUDE.md index_sha a04000ed53d2340ab214b8bce7db494f0d311c29bfc93964c98094ed8cf1dcf1 expected_sha a04000ed53d2340ab214b8bce7db494f0d311c29bfc93964c98094ed8cf1dcf1 MATCH {'lines': 995, 'diff_vs_base_lines': [16, 198], 'row_index_1based': 531, 'nonascii_main': (1353, 3937), 'nonascii_x': (1353, 3937), 'nonascii_base': (1353, 3937), 'nonascii_out': (1353, 3937), 'session81_order': ['**SESSION 81 flag (D03 DENY-AND-GUARDS, 2026-10-22; default ', '**SESSION 81 flag (S81-03 LLM-LEDGER-V2, 2026-10-23; default', '**SESSION 81 flag (ST1 LOOP-STALL, 2026-10-23; default OFF, ', '**SESSION 81 flag (S81-05 REQUEST-CONTEXT, 2026-10-23; defau', '**SESSION 81 flag (S81-04 SPEND-BREAKER, 2026-10-23; default', '**SESSION 81 unit (S81-14 KB-SCHEMA, 2026-10-24; NO flag and', '**SESSION 81 flags (S81-06 ANTHROPIC-ROUTER, 2026-10-24; def', '**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, 2026-1', '**SESSION 81 flags (S81-15 REGISTRY-ROBOTS-DENY, 2026-10-28;', '**SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, 2026-10-29; NO r', '**SESSION 81 unit (S81-12 LEGAL-V3, 2026-10-29; NO flag; a H']}
still conflicted: []
```

### resolve_3.log
```
replaying b8d283058ceef969e95361d5d45bab6ca35b8f3a conflicted ['CLAUDE.md']
CLAUDE.md index_sha 1a863e0b8d768c0df16259efa7cb5c136b102e9d4a5ef7320cf82156511e7e18 expected_sha 1a863e0b8d768c0df16259efa7cb5c136b102e9d4a5ef7320cf82156511e7e18 MATCH {'lines': 995, 'diff_vs_base_lines': [16, 198], 'row_index_1based': 531, 'nonascii_main': (1353, 3937), 'nonascii_x': (1353, 3937), 'nonascii_base': (1353, 3937), 'nonascii_out': (1353, 3937), 'session81_order': ['**SESSION 81 flag (D03 DENY-AND-GUARDS, 2026-10-22; default ', '**SESSION 81 flag (S81-03 LLM-LEDGER-V2, 2026-10-23; default', '**SESSION 81 flag (ST1 LOOP-STALL, 2026-10-23; default OFF, ', '**SESSION 81 flag (S81-05 REQUEST-CONTEXT, 2026-10-23; defau', '**SESSION 81 flag (S81-04 SPEND-BREAKER, 2026-10-23; default', '**SESSION 81 unit (S81-14 KB-SCHEMA, 2026-10-24; NO flag and', '**SESSION 81 flags (S81-06 ANTHROPIC-ROUTER, 2026-10-24; def', '**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, 2026-1', '**SESSION 81 flags (S81-15 REGISTRY-ROBOTS-DENY, 2026-10-28;', '**SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, 2026-10-29; NO r', '**SESSION 81 unit (S81-12 LEGAL-V3, 2026-10-29; NO flag; a H']}
still conflicted: []
```

### both_sides.txt
```
SmartCompareApp/src/services/aiConsent.ts
main: +63 lines (missing in HEAD 0), -2 lines (still in HEAD 0)
branch: +10 lines (missing in HEAD 0), -6 lines (still in HEAD 0)
SmartCompareApp/src/i18n/en.json
main: +3 lines (missing in HEAD 0), -0 lines (still in HEAD 0)
branch: +3 lines (missing in HEAD 0), -3 lines (still in HEAD 0)
SmartCompareApp/src/i18n/ar.json
main: +3 lines (missing in HEAD 0), -0 lines (still in HEAD 0)
branch: +3 lines (missing in HEAD 0), -3 lines (still in HEAD 0)
tests/test_legal_disclosure_s77.py
main: +1 lines (missing in HEAD 0), -0 lines (still in HEAD 0)
branch: +67 lines (missing in HEAD 0), -34 lines (still in HEAD 0)
tests/test_legal_s78.py
main: +1 lines (missing in HEAD 0), -1 lines (still in HEAD 0)
branch: +22 lines (missing in HEAD 0), -8 lines (still in HEAD 0)
SmartCompareApp/__tests__/setup.ts
main: +31 lines (missing in HEAD 1), -22 lines (still in HEAD 0)
   MISSING[main]:     AI_CONSENT_VERSION: 2,
branch: +1 lines (missing in HEAD 1), -1 lines (still in HEAD 0)
   MISSING[branch]:   AI_CONSENT_VERSION: 3,
CLAUDE.md
main: +25 lines (missing in HEAD 0), -4 lines (still in HEAD 0)
branch: +4 lines (missing in HEAD 0), -2 lines (still in HEAD 0)
```

### merge_tree.txt
```
cf8abcb3f82c22e5e1eaeffda90d14802098a59a
CLAUDE.md
SmartCompareApp/__tests__/setup.ts

Auto-merging CLAUDE.md
CONFLICT (content): Merge conflict in CLAUDE.md
Auto-merging SmartCompareApp/__tests__/setup.ts
CONFLICT (content): Merge conflict in SmartCompareApp/__tests__/setup.ts
Auto-merging SmartCompareApp/src/i18n/ar.json
Auto-merging SmartCompareApp/src/i18n/en.json
Auto-merging SmartCompareApp/src/services/aiConsent.ts
Auto-merging tests/test_legal_disclosure_s77.py
Auto-merging tests/test_legal_s78.py
```

## Comm set re-derived at 6c14ac95 (NOT run this round)
```
tests/test_account_deletion.py
tests/test_adapter_drop_visibility.py
tests/test_admin_key_and_sentry_scrub.py
tests/test_arabic_verdict_output_w414.py
tests/test_attribution_endpoint.py
tests/test_auth_demographics.py
tests/test_auth_error_log_hygiene.py
tests/test_b2_strict_optional_auth.py
tests/test_backend_cleanup.py
tests/test_behavior_dimension_translation.py
tests/test_category_aware_discovery_i55.py
tests/test_channel_freshness.py
tests/test_ci_gates.py
tests/test_cohort_summary_orchestrator.py
tests/test_comparison_id_echo.py
tests/test_comparison_quality_v2.py
tests/test_comparison_response_image_url.py
tests/test_consent_capture_w3_16.py
tests/test_content_blocklist_arabic_parity.py
tests/test_cost_meter_s74.py
tests/test_diagnostics_flag_gated.py
tests/test_dimension_label_catalog_parity_w414.py
tests/test_discovery_window_i54.py
tests/test_domain_s76.py
tests/test_events_allowlist_superset.py
tests/test_feature_bucket_parity.py
tests/test_feedback_allowlist_superset.py
tests/test_flush_live_price_key.py
tests/test_genuine_predicate_parity.py
tests/test_genuine_price_clobber_guard.py
tests/test_genuine_price_priority.py
tests/test_genuine_reach_cascade.py
tests/test_hermeticity_pins.py
tests/test_iherb_page_currency_signal.py
tests/test_js_rendering.py
tests/test_landing_fallback_pages_s69.py
tests/test_legal_disclosure_s77.py
tests/test_legal_docs_u8.py
tests/test_legal_docs_u8_d3c.py
tests/test_legal_docs_u8_polish.py
tests/test_legal_routes.py
tests/test_legal_s78.py
tests/test_logger_no_query_leak.py
tests/test_loop2_gift_copy.py
tests/test_m18_factcheck_honest.py
tests/test_migration_037_security_definer_grants.py
tests/test_migration_043_delete_user_cascade.py
tests/test_migration_index_predicate_immutability.py
tests/test_model_config.py
tests/test_model_config_enforced.py
tests/test_multiplicity_discriminator_policy.py
tests/test_nasser_adapter.py
tests/test_negcache_genuine_invalidation.py
tests/test_not_a_pdp_filter.py
tests/test_og_cascade_position.py
tests/test_openai_key_log_hygiene_s69.py
tests/test_paid_route_metering.py
tests/test_password_reset_deep_link.py
tests/test_phase1_per_race_timeouts.py
tests/test_prompt_fence.py
tests/test_prompt_truth.py
tests/test_register_benefits_parity_s69.py
tests/test_response_builder_phase1_none_guard.py
tests/test_retro_w0_4.py
tests/test_retro_w0_4_efg.py
tests/test_retro_w1_2b.py
tests/test_retro_w1_9.py
tests/test_review_paraphrase.py
tests/test_robots_unreadable_ruling.py
tests/test_s70_exc_summary_logs.py
tests/test_s70_prefetch_gather_retrieved.py
tests/test_s71_u13_compare_auth_required.py
tests/test_s75_fanout_starve.py
tests/test_s77_redis_offloop.py
tests/test_s79_b3b_apple_revoke.py
tests/test_s80_b1.py
tests/test_s80_b3_vision_identity_v2.py
tests/test_s80_url_mode_v2.py
tests/test_s81_12_gate_rows.py
tests/test_s81_12_legal_v3.py
tests/test_s81_d03_deny_and_guards.py
tests/test_s81_kb_schema.py
tests/test_s81_s03_llm_ledger_v2.py
tests/test_s81_s04_spend_breaker.py
tests/test_s81_s05_request_context.py
tests/test_s81_s06_anthropic_router.py
tests/test_s81_s06_router_gate_rows.py
tests/test_s81_s08b_gate_rows.py
tests/test_s81_s08b_legacy_fingerprint.py
tests/test_s81_s15_registry_robots.py
tests/test_s81_st1_usage_path_offloop.py
tests/test_secret_scan_static.py
tests/test_security_hardening.py
tests/test_security_regression.py
tests/test_sentry_channels_u8d_unit.py
tests/test_shopify_pdp_json.py
tests/test_specs_no_fabrication_guard.py
tests/test_start_command.py
tests/test_text_error_envelope_no_raw_exception.py
tests/test_text_routes_sse_contract.py
tests/test_timeout_partial_integration.py
tests/test_u3b_sharing_branch_removed.py
tests/test_u3c_referral_push_name.py
tests/test_u3c_store_false_pin.py
tests/test_value_math.py
tests/test_w4_13_measurement_truth.py
tests/test_w4_7_confidence_single_computation.py
tests/test_w4_7_factcheck_shopping_key.py
tests/test_wall_caps_i57.py
tests/test_youtube_flag_and_cache.py
```

## [NATIVE READ] Arabic strings (full text)
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
- [NATIVE READ] privacy s6 (catalogue + crawler, hedged per F1-7): وقد نحتفظ أيضًا بكتالوج خاص بنا لمعلومات المنتجات (أسماء المنتجات وأحجامها وأسعارها، وعناوين صور المنتجات على الويب وعناوين الصفحات التي جاءت منها) لتصبح المقارنات اللاحقة أسرع وأكمل. ويقرأ زاحف الكتالوج لدينا، عندما نشغّله، صفحات المتاجر التي يسمح بها ملف robots.txt الخاص بكل منها، ويعرّف نفسه بسلسلة وكيل المستخدم المنشورة على الصفحة https://getmyez.com/bot/ في موقعنا. وقد نضيف أيضًا تفاصيل منتجات يُدخلها فريقنا يدويًا من صفحات يزورها بالطريقة المعتادة، وموجزات منتجات وبيانات يرخّصها لنا شركاؤنا، وتفاصيل المنتجات التي نجدها أثناء المقارنات. ولا يحتوي الكتالوج إلا على معلومات المنتجات، ولا يحتوي أبدًا على هوية من أجرى المقارنة.
- [NATIVE READ] privacy s6 (Sponsored): وقد تدفع المتاجر مقابل عرض رابط إلى موقعها الإلكتروني أو متجرها بجانب أحد المنتجات؛ ويحمل هذا الرابط علامة «مموّل». ولا يغيّر الدفع أبدًا طريقة مقارنة المنتجات أو تقييمها أو ترتيبها. وقد يُسجَّل النقر على رابط متجر مع نشاطك الآخر داخل التطبيق (القسم 3.4).
- [NATIVE READ] privacy s8 (photos line): ويوضّح القسم 4 ما يحتفظ به مزوّدو الذكاء الاصطناعي لدينا.
- [NATIVE READ] privacy s12 (AI disclosure):  ويوضّح التطبيق أن المقارنات يكتبها الذكاء الاصطناعي، ويطلب إذنك قبل مقارنتك الأولى، ونفحص الطلبات والنتائج بحثًا عن المحتوى غير الآمن.
- [NATIVE READ] privacy s14 (device identifiers, F1-2): يحتفظ التطبيق برموز تسجيل الدخول، وبمعرّف تثبيت عشوائي (يُستخدم مع حسابك لتطبيق حدود المقارنات المجانية)، وبمعرّف عشوائي آخر يستخدمه التطبيق لاختيار الميزات الجديدة التي تظهر لك، وكلها مخزّنة بأمان في Keychain على جهاز iPhone، ويحتفظ في مساحة تخزين التطبيق بملخص ملفك الشخصي، وعمليات بحثك الأخيرة، وإجاباتك في أسئلة البداية التي لم تُرسَل بعد، وسجل إذنك بالمعالجة بالذكاء الاصطناعي، وإعدادات اللغة، ونسخة محفوظة من هذه السياسة. وحتى 31 مارس 2027، يرسل التطبيق أيضًا صيغة أقدم من معرّف التثبيت كانت تجمع ذلك المعرّف العشوائي مع إصدار برنامج جهازك، لكي ينتقل سجل مقارناتك المجانية؛ وبعد ذلك التاريخ لا يُستخدم إلا معرّف التثبيت العشوائي. يؤدي تسجيل الخروج إلى إزالة رموز تسجيل الدخول وملخص الملف الشخصي؛ ويؤدي حذف حسابك أيضًا إلى إزالة سجل إذن المعالجة بالذكاء الاصطناعي. وقد تبقى العناصر المحفوظة في Keychain على جهاز iPhone بعد حذف التطبيق.
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
- [NATIVE READ] privacy policy (dated notice before section 1, F1-5; date = AI_SWITCH_DATE_AR): **التغييرات في 29 أكتوبر 2026:** أضفنا Anthropic إلى مزوّدي الذكاء الاصطناعي لدينا (القسم 4)، وانتهت مشاركتنا في برنامج مشاركة البيانات لدى OpenAI في ذلك التاريخ (القسم 4)، وسيطلب التطبيق إذنك مرة أخرى لإرسال طلباتك إلى مزوّدي الذكاء الاصطناعي لدينا.
- [NATIVE READ] Terms (dated notice before section 1, F1-5; date = AI_SWITCH_DATE_AR): **التغييرات في 29 أكتوبر 2026:** أضفنا Anthropic إلى مزوّدي الذكاء الاصطناعي لدينا (القسم 8)، وانتهت مشاركتنا في برنامج مشاركة البيانات لدى OpenAI في ذلك التاريخ (القسم 4 من سياسة الخصوصية)، وسيطلب التطبيق إذنك مرة أخرى لإرسال طلباتك إلى مزوّدي الذكاء الاصطناعي لدينا.
- [NATIVE READ] Terms s8 (heading, F1-6; the plural construct in the nominative): ## 8. الملكية الفكرية والمحتوى الذي ترسله ومزوّدو الذكاء الاصطناعي لدينا
- [NATIVE READ] Terms s8 (licence grant, F1-6): وللحصول على المقارنات من مزوّدي الذكاء الاصطناعي لدينا على النحو الذي توضّحه سياسة الخصوصية
- [NATIVE READ] unpinned facts to check in the AR texts (correctness m4): the gate rows now pin 'including photos' in privacy s2, Anthropic's '30' inside its own retention sentence, Anthropic's and OpenAI's no-training sentences and the carve-out, but the native read remains the only check of the AR wording itself.
- [NATIVE READ] privacy s14 (NEW, rebase RB12-6; the Keychain / Keystore fallback clause): وعندما لا يمكن قراءة Keychain (أو Keystore على أجهزة Android)، يستخدم التطبيق بدلًا من ذلك المعرّف الذي توفّره Apple أو Google لمطوّري التطبيقات لذلك الجهاز (معرّف المورّد على iPhone، ومعرّف Android ID على أجهزة Android)، وذلك لتطبيق حدود المقارنات المجانية فقط.

## Earlier gate logs (fix rounds 1 and 2), as recorded in the fix-round-2 draft
## Gates (fix round 2, on the committed bytes b8d283058ceef969e95361d5d45bab6ca35b8f3a)
- pre-commit sanity on the working bytes: `[pyt] tag=s12fix2-precommit-units start=2026-10-29 10:35:45 end=2026-10-29 10:36:20 elapsed=36s bound=600s status=FAIL rc=1` (both unit files: 1 failed = H1 / 57 passed; [hermeticity] sentinel checked 58 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- COMMIT b8d283058ceef969e95361d5d45bab6ca35b8f3a through the pre-commit hook (gitleaks, secret shapes, py_compile, ruff 'All checks passed!'; rc 0, never --no-verify): 3 files changed, 156 insertions(+), 20 deletions(-); `git status --short` empty.
- G1 the python RED file alone: `[pyt] tag=s12fix2-g1-red start=2026-10-29 10:39:10 end=2026-10-29 10:39:32 elapsed=22s bound=600s status=FAIL rc=1` (1 failed = H1 (AssertionError, by design) / 37 passed; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- G2 the gate-rows file alone: `[pyt] tag=s12fix2-g2-gaterows start=2026-10-29 10:39:44 end=2026-10-29 10:40:27 elapsed=42s bound=600s status=OK rc=0` (20 passed; [hermeticity] sentinel checked 20 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)); MS1-MS4 KILLED (the mutation table).
- G3 the 15-file legal set + both unit files: `[pyt] tag=s12fix2-g3-legal start=2026-10-29 10:46:28 end=2026-10-29 10:49:39 elapsed=191s bound=1200s status=FAIL rc=1` (1 failed = H1 / 552 passed; [hermeticity] sentinel checked 553 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- G4 the CI-order set (GREEN's 18 files + tests/test_s81_12_gate_rows.py, sorted, -rfE): `[pyt] tag=s12fix2-g4-ci-order start=2026-10-29 10:49:58 end=2026-10-29 10:54:14 elapsed=256s bound=1200s status=FAIL rc=1` (1 failed = H1 / 1177 passed; [hermeticity] sentinel checked 1178 test(s); [netguard] blocked 24 attempt(s) from 2 node(s): test_s81_s04_spend_breaker r42 / p08, neutralized.supabase.invalid:443)
- G5 ruff 0.16.5 --select E9,F63,F7,F82 --no-cache 'All checks passed!' and py_compile rc 0 on the two edited test files (committed bytes); the hook passed on the commit.
- G6 `git diff e3bcf768 HEAD -- app/ landing/ scripts/ tests/fixtures/ SmartCompareApp/` EMPTY (0 bytes); `git diff --name-only e3bcf768 HEAD` = CLAUDE.md, tests/test_s81_12_gate_rows.py, tests/test_s81_12_legal_v3.py; the footprint `git diff --name-only origin/main...HEAD` = the 43 unit files exactly; `git diff --check` clean. No jest this round (no client byte moved, F2-5).

## Gates (fix round 1, on the fix bytes)
- RED step (before any text change):
- `[pyt] tag=s12fix1-red-gaterows start=2026-10-29 07:51:01 end=2026-10-29 07:51:12 elapsed=11s bound=600s status=FAIL rc=1 (2 failed = G-h [en/ar], AssertionError / 14 passed; [hermeticity] sentinel checked 16 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[pyt] tag=s12fix1-red-unit start=2026-10-29 07:51:28 end=2026-10-29 07:51:47 elapsed=19s bound=600s status=FAIL rc=1 (1 failed = H1 / 37 passed, after the F1-1 rename; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[jest] tag=s12fix1-red-client start=07:52:00 end=07:52:24 rc=0 (the amended client RED file by path: 9 passed / 9; node v24.11.1, jest 29.7.0, @babel/core 7.29.0; junction -> the clone's SmartCompareApp/node_modules, @babel/core and .bin/jest present)`
- GREEN step (after the machinery edits):
- `[pyt] tag=s12fix1-legal-pre start=2026-10-29 07:55:37 end=2026-10-29 07:56:54 elapsed=76s bound=1200s status=FAIL rc=1 (6 failed: s77 d3[en/ar], d3c_i, s78 r16 = the F1-6 pins; R17[en]; H1 / 543 passed; the 15-file legal set + both unit files; [hermeticity] sentinel checked 549 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- `[pyt] tag=s12fix1-legal-a start=2026-10-29 07:58:33 end=2026-10-29 08:01:18 elapsed=165s bound=1200s status=FAIL rc=1 (2 failed = R17[en] (open ruling) + H1 (by design) / 547 passed; after EF6a-c; [hermeticity] sentinel checked 549 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- Mutation table: 17 runs of the gate-rows file through pyt.py (M0 + 16 mutants), lines in the mutation table below.
- `[tsc] tag=s12fix1-tsc start=08:09:52 end=08:10:18 rc=0 (node node_modules/typescript/bin/tsc --noEmit, TypeScript 5.9.3)`
- EK2 probe (an untracked copy, deleted after): [pyt] tag=s12fix1-ek2-fix start=2026-10-29 08:10:39 end=2026-10-29 08:11:00 elapsed=21s bound=600s status=FAIL rc=1 (the amended copy on the fix bytes: 1 failed = H1 / 37 passed)
- EK2 probe control: [pyt] tag=s12fix1-ek2-green_wording start=2026-10-29 08:11:03 end=2026-10-29 08:11:28 elapsed=24s bound=600s status=FAIL rc=1 (GREEN's s14 wording restored through the machinery: 2 failed = R17[en] + H1 / 36 passed; restored, sha ok)
- `[jest] tag=s12fix1-jest-subset start=08:11:48 end=08:12:17 rc=0 (by path: the client RED file + aiConsentVersion.s69 + aiConsentV2.s75 + aiProcessingConsent.s69 + step05Trust.s69 + landing.brand.s69: Test Suites 6 passed; Tests 64 passed / 64)`
- `[jest] tag=s12fix1-jest-full start=08:12:31 end=08:13:32 rc=1 (FULL suite once, no -u: Test Suites 1 failed (config/nativeBundle.w37), 3 skipped, 376 passed; Tests 4 failed (the 4 accepted nativeBundle.w37 drift nodes d5, k2, k4, k5), 13 skipped, 13 todo, 3703 passed = GREEN's 3701 + the 2 C2 rows; Snapshots 42 passed, none written)`
- `[eslint] tag=s12fix1-eslint start=08:14:00 end=08:14:26 rc=0 (node node_modules/eslint/bin/eslint.js, eslint 9.39.4, on the edited client file __tests__/s81_12/legalV3.s81_12.test.ts)`
- `[pyt] tag=s12fix1-ci-order start=2026-10-29 08:14:44 end=2026-10-29 08:17:37 elapsed=173s bound=1200s status=FAIL rc=1 (19 files = GREEN's 18 + tests/test_s81_12_gate_rows.py: 2 failed = R17[en] (open ruling) + H1 (by design) / 1172 passed; [hermeticity] sentinel checked 1174 test(s); [netguard] blocked 24 attempt(s) from 2 node(s): test_s81_s04_spend_breaker r42 / p08, neutralized.supabase.invalid:443)`
- machinery on the fix bytes: scripts/fill_in_legal.py --dry-run rc 0 (nothing to write); scripts/render_legal_landing.py --check rc 0; ruff 0.16.5 E9/F63/F7/F82 'All checks passed!' and py_compile OK on the four edited .py files; both edited JSON fixtures json.load OK
- Comm set (5 chunks, bound 1200 each; lines in the comm section): branch-only-new EMPTY.
- COMMIT e3bcf76839ee87f6908aac04f0f06e8f81211a31 through the pre-commit hook (gitleaks, secret shapes, py_compile, ruff 'All checks passed!'): 20 files changed, 1758 insertions(+), 33 deletions(-); git status --short empty.
- `[pyt] tag=s12fix1-head-unit-final start=2026-10-29 08:39:13 end=2026-10-29 08:39:37 elapsed=24s bound=600s status=FAIL rc=1 (on the COMMITTED bytes: tests/test_s81_12_legal_v3.py + tests/test_s81_12_gate_rows.py: 2 failed = R17[en] (open ruling) + H1 (by design) / 52 passed; [hermeticity] sentinel checked 54 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`
- on the committed bytes: scripts/fill_in_legal.py --dry-run rc 0, nothing to write; scripts/render_legal_landing.py --check rc 0.

## Comm set (zero-regression gate)
Restated in fix round 2 (F2-5; this round moves test and docs bytes only, so the comm set was not re-run): 107 files (GREEN's 106 + tests/test_s81_12_gate_rows.py) against GREEN's FRESH base record at a8f01379, as re-measured by the fix-round-1 re-verifier in 5 chunks of 20-23 files (at most 25, m6), bound 1200 each: branch-only-new EMPTY, 9164 passed, the same 4 HEAD failures as below. After EK2 R17[en] passes on HEAD (G1 / G3 / G4 above), so the HEAD failure set is 3: the two cold-tiktoken ERRORs of tests/test_prompt_truth.py + H1 (all three in the base record or red by design). The fix-round-1 record follows (its chunks were of <= 26, m6).

106 files (the F1-13 set: GREEN's comm_files_head.txt) + the NEW tests/test_s81_12_gate_rows.py, 5 chunks of <= 26, HEAD = the fix-round bytes, base = GREEN's FRESH record at a8f01379 (comm_base_failed.txt: the 30 RED rows + the 2 cold-tiktoken ERRORs of tests/test_prompt_truth.py). HEAD failures (4): ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence; ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable; FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded; FAILED tests/test_s81_12_legal_v3.py::test_r17_privacy_s14_ai_permission_and_device_identifiers[en]. **branch-only-new: EMPTY.** R17[en] and H1 are red at base too (RED rows), so they are not branch-only-new; the four tests/test_precommit_hook*.py stay excluded.
- `[pyt] tag=s12fix1-head-00 start=2026-10-29 08:18:07 end=2026-10-29 08:19:51 elapsed=104s bound=1200s status=OK rc=0 (1274 passed, 21 warnings in 99.50s (0:01:39); [hermeticity] sentinel checked 1274 test(s); [netguard] blocked 3 attempt(s) from 1 node(s); [netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443)`
- `[pyt] tag=s12fix1-head-01 start=2026-10-29 08:19:52 end=2026-10-29 08:27:58 elapsed=486s bound=1200s status=OK rc=0 (2203 passed, 4 deselected, 16 warnings in 481.62s (0:08:01); [netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_an_asyncio_connect_to_a_public_literal[proactor] [ip_literal] socket.connect 192.0.2.1:443; [netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_a_loopback_curl_url_through_a_public_proxy[call_proxy] [ip_literal] curl_cffi.Session.request http://192.0.2.1:8080 (proxy for http://127.0.0.1:57339/); [netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_a_loopback_curl_url_through_a_public_proxy[call_proxies] [ip_literal] curl_cffi.Session.request http://192.0.2.1:8080 (proxy for http://127.0.0.1:57340/); [netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_a_loopback_curl_url_through_a_public_proxy[session_proxies] [ip_literal] curl_cffi.Session.request http://192.0.2.1:8080 (proxy for http://127.0.0.1:57341/); [netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_a_loopback_curl_url_through_a_public_proxy[async_call_proxy] [ip_literal] curl_cffi.AsyncSession.request http://192.0.2.1:8080 (proxy for http://127.0.0.1:57342/); [netguard]   tests/test_hermeticity_pins.py::test_non_loopback_lookup_is_blocked_without_the_marker [egress] socket.getaddrinfo example.com:80)`
- `[pyt] tag=s12fix1-head-02 start=2026-10-29 08:28:00 end=2026-10-29 08:31:17 elapsed=197s bound=1200s status=FAIL rc=1 (1342 passed, 23 skipped, 2 deselected, 1 xfailed, 263 warnings, 2 errors in 188.80s (0:03:08); [hermeticity] sentinel checked 1345 test(s); [netguard] blocked 2 attempt(s) from 2 node(s); [netguard]   tests/test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds [sentinel] socket.create_connection neutralized.supabase.invalid:443; [netguard]   tests/test_paid_route_metering.py::test_url_compare_saves_history_with_input_type_url [sentinel] socket.create_connection neutralized.supabase.invalid:443)`
- `[pyt] tag=s12fix1-head-03 start=2026-10-29 08:31:18 end=2026-10-29 08:35:22 elapsed=244s bound=1200s status=FAIL rc=1 (2 failed, 3855 passed, 1 skipped, 97 warnings in 237.57s (0:03:57); [netguard]   tests/test_timeout_partial_integration.py::TestRoutePartialReturns200::test_post_partial_returns_200_parity [sentinel] socket.create_connection neutralized.supabase.invalid:443; [netguard]   tests/test_timeout_partial_integration.py::TestRouteTimeoutMapsTo503::test_get_timeout_maps_to_503_with_code_preserved [sentinel] socket.create_connection neutralized.supabase.invalid:443; [netguard]   tests/test_timeout_partial_integration.py::TestRouteTimeoutMapsTo503::test_post_timeout_maps_to_503_parity [sentinel] socket.create_connection neutralized.supabase.invalid:443; [netguard]   tests/test_timeout_partial_integration.py::TestInsufficientDataUnchanged::test_insufficient_data_passthrough [sentinel] socket.create_connection neutralized.supabase.invalid:443; [netguard]   tests/test_timeout_partial_integration.py::TestStreamingTimeoutD2Contract::test_stream_hardcap_yields_stream_timeout_partial [egress] socket.getaddrinfo api.openai.com:443; [netguard]   tests/test_timeout_partial_integration.py::TestStreamingTimeoutD2Contract::test_stream_timeout_copy_has_no_forbidden_vocab [egress] socket.getaddrinfo api.openai.com:443)`
- `[pyt] tag=s12fix1-head-04 start=2026-10-29 08:35:24 end=2026-10-29 08:36:31 elapsed=67s bound=1200s status=OK rc=0 (490 passed, 35 xfailed, 11 warnings in 59.61s; [hermeticity] sentinel checked 525 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))`

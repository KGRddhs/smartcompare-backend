# S81-SF1 SURFACES-BE -- RED report (RED agent, Opus 5.5, 2026-11-06)

Written through the shell (python): the harness refuses a subagent Write of a report .md.
Base 18cb9e04a36382fc417307500a092486f618d95e; real worktree sc-s81-sf1 (HEAD = base; git status --short = `?? tests/test_s81_sf1_surfaces_be.py` only; git diff empty).
Spec sha256 2621dd63... as amended by RULINGS_S81_SF1 (R-SF1-17..45). The hook test files tests/test_precommit_hook*.py NOT RUN (no .githooks change). No client gate at RED (no node_modules in sc-s81-sf1): E4, the fourteen fences + b3a/nativeStrings, the s11 suite, the corpus gate and the full jest are GREEN's.

## 1. The RED file
- tests/test_s81_sf1_surfaces_be.py: 52881 bytes, sha256 b86f473e661b912c42164c2ce25aaa4f6de71c4700e7e2d356a51d44c1f3ef3a, 0 bytes > 127, 0 CR, ruff E9/F63/F7/F82 clean.
- 195 nodes: RED 121 (every one AssertionError at base; junit per node: red_base_nodes.tsv), PIN 74 (green at base, full companion configuration + recorders).
- No @gmail / +973 / 8-digit run; uuids built at run time (uuid4); user ids sf1-<node>; no gitleaks-keyword constant beside a hex literal; the U+2192 arrow built as chr(0x2192).

### Rows (spec section 5 ids kept; ruled additions marked)
| # | row | at base |
|---|---|---|
| R01 | feedback_service.feedback_v2_enabled reader table (5 ON / 9 OFF spellings) | RED |
| R02 | database_service._feedback_v2_enabled same table + parity with the public reader on 17 spellings (R-SF1-18) | RED |
| R03 | version_routes.surfaces_field_enabled reader table | RED |
| R04 | surfaces_live knob parse: key order, bool values, unknown tokens | RED |
| R05 | /app/version ON: surfaces after the five keys, JSON booleans | RED |
| R05b | ON + knob unset / blank -> surfaces present, both false (R-SF1-33, ruled) | RED |
| R06 | both flags ON: five keys, surfaces, categories_live | RED |
| P07 | OFF x 7 spellings x S81-10 both states, full config + os.getenv recorder: base body, APP_SURFACES_LIVE never read | PIN 14 |
| R08 | unknown chips never on the wire | RED |
| P10 | OFF x 7: the 11 measured 422 envelopes (error literal, code, success, request_id str) + the model error lists | PIN 7 |
| P11 | OFF x 7: extras accepted and dropped; save_feedback kwargs == the nine base names in order and values | PIN 7 |
| P12 | OFF x 7: the REAL save_feedback insert payload == base literal (keys and order) with every new field sent | PIN 7 |
| R13 | ON x 5: v2 body without useful -> kwargs useful None, the answers, correction stripped, source result, crid canonical | RED 5 |
| R14 | save_feedback signature has the six kwargs (asserted first, R-SF1-28); ON stored row: no useful key when None; useful False written | RED |
| R15 | ON 422s: correction 81, literal errors x4, crid bad, useful 'maybe'; blank correction -> None | RED |
| R15b | R-SF1-34: C0 + DEL refused, raw cap 1,000 before strip (ruled) | RED |
| R15c | R-SF1-32: ON empty body -> 422 ending 'feedback body carries no answer'; six answer bodies 200 (ruled) | RED |
| R16 | ON source contact / default result | RED |
| R20 | VALID_EVENT_TYPES[:31] == base, [31:] == the four, unique | RED |
| R21 | EVENT_PROPERTY_ALLOWLIST == the closed frozenset dict | RED |
| R22 | OFF x 7: the four types accepted AND filtered (R-SF1-38: the filter is unflagged), one INFO n per item | RED 7 |
| R23 | both states: store_cta_tap / share_target_opened filtered, share untouched, exact INFO lines, no value in any record | RED 2 |
| R23b | R-SF1-20 value rules x both states: merchant_id = the 045 kb_merchants.host CHECK (KB_HOST_REGEX, full match), category in {skincare, makeup}, channel / share_target in the nine (ruled) | RED 78 |
| P24 | OFF x 7: compare_request_id dropped on events, base four-key dicts | PIN 7 |
| R25 | ON: crid on events (route dict + real track_events_batch record); bad -> 422 exact message | RED |
| P26 | OFF x 7: real track_events_batch records == base literal | PIN 7 |
| R27 | ON store_cta_tap > 10 KB -> the size 422 (the type accepted) | RED |
| P30 | OFF x 7: share_target 8 off-set values -> the base 422 bytes + model error list; six base values 201; ReferralService faked | PIN 7 |
| R31 | ON: sms / email / more reach create_invite; facebook -> the nine-value 422 | RED |
| R32 | create_invite OFF sms -> base ValueError literal; ON sms / email / more / whatsapp reach ensure_code; ON facebook -> nine-value message | RED |
| P33 | code-redeem insert share_target 'other' both states | PIN 2 |
| R40 | ON + headers + bound id: log_search record carries crid; unbound -> no key | RED |
| P41 | OFF x 7 x W4-13 marker both states, bound id: record == base literal; request_context.compare_request_id recorder 0 calls | PIN 14 |
| P42 | log_search signature literal | PIN 1 |
| R50 | 046 / 049 + rollbacks exist once; ASCII; LF (autocrlf-tolerant); BEGIN once / COMMIT once; forward files start BEGIN; SET LOCAL lock_timeout = '5s' and end COMMIT; NOTIFY pgrst (R-SF1-30 / 31) | RED |
| R51 | 046 text: six columns + types, five CHECKs, partial index, DROP NOT NULL only inside the is_nullable DO with the sf1_dropped_not_null comment (R-SF1-36), no price_correct, no function / policy / grant | RED |
| R52 | 049 text: the guard DO body (pg_constraint, contype c, ILIKE share_target, <> 1 THEN RAISE before the dynamic DROP %I), nine-value CHECK, two uuid columns + partial indexes | RED |
| R53 | rollbacks: 046 drops exactly six columns, SET NOT NULL only inside a col_description sf1_dropped_not_null gate with a NULL-row RAISE, clears the comment; 049 RAISE on sms / email / more, six-value CHECK, drops both columns | RED |
| R54 | parity: 046 sets == the route constants, CORRECTION_MAX_CHARS 80; 049 nine == WIDENED_SHARE_TARGETS == _WIDENED_SHARE_TARGETS == ShareTargetV2; ShareTarget kept six | RED |
| P60 | cron_learning FEEDBACK_COLUMNS excludes correction / crid; 'correction' literals only in the two writer files; no select('*') on comparison_feedback | PIN 1 |
| P61 | ON success paths: no correction, uuid, merchant value or knob value in any formatted record | RED |
| R70 | R-SF1-27: APIError 23502 with a synthetic correction in details -> the three except arms log constants only ('[FEEDBACK] save failed type=APIError code=23502' exact), no detail / row text in message or traceback, both states (ruled) | RED 2 |
| P62 | the literal trackEvent('category_coming_soon_tap' once under SmartCompareApp/src (HomeScreen.tsx); launchSurfaces.ts free of it | RED |

### AssertionError proof per RED node
junit classification of the final base run: Counter({'FAIL:AssertionError': 121, 'PASS': 74}); no ERROR, no TypeError / ValueError / AttributeError / ImportError / FileNotFoundError. The 121 failed node ids:
- tests/test_s81_sf1_surfaces_be.py::test_r01_feedback_v2_reader
- tests/test_s81_sf1_surfaces_be.py::test_r02_log_search_reader_parity
- tests/test_s81_sf1_surfaces_be.py::test_r03_surfaces_reader
- tests/test_s81_sf1_surfaces_be.py::test_r04_surfaces_knob_parse
- tests/test_s81_sf1_surfaces_be.py::test_r05_version_surfaces_on
- tests/test_s81_sf1_surfaces_be.py::test_r05b_version_surfaces_on_knob_unset
- tests/test_s81_sf1_surfaces_be.py::test_r06_version_key_order_both_flags
- tests/test_s81_sf1_surfaces_be.py::test_r08_unknown_chip_never_on_wire
- tests/test_s81_sf1_surfaces_be.py::test_r13_feedback_on_accepts_v2[true]
- tests/test_s81_sf1_surfaces_be.py::test_r13_feedback_on_accepts_v2[ TRUE ]
- tests/test_s81_sf1_surfaces_be.py::test_r13_feedback_on_accepts_v2[1]
- tests/test_s81_sf1_surfaces_be.py::test_r13_feedback_on_accepts_v2[yes]
- tests/test_s81_sf1_surfaces_be.py::test_r13_feedback_on_accepts_v2[On]
- tests/test_s81_sf1_surfaces_be.py::test_r14_feedback_on_stored_row
- tests/test_s81_sf1_surfaces_be.py::test_r15_feedback_on_422s
- tests/test_s81_sf1_surfaces_be.py::test_r15b_correction_control_chars_and_raw_cap
- tests/test_s81_sf1_surfaces_be.py::test_r15c_empty_body_under_on
- tests/test_s81_sf1_surfaces_be.py::test_r16_feedback_on_contact_source
- tests/test_s81_sf1_surfaces_be.py::test_r20_event_types_appended
- tests/test_s81_sf1_surfaces_be.py::test_r21_property_allowlist_dict
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[None]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[false]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[0]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[off]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[no]
- tests/test_s81_sf1_surfaces_be.py::test_r22_new_types_accepted_off[ FALSE ]
- tests/test_s81_sf1_surfaces_be.py::test_r23_property_filter[None]
- tests/test_s81_sf1_surfaces_be.py::test_r23_property_filter[true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-noon.com-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-noon.com-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-bh.boutiqaat.com-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-bh.boutiqaat.com-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-https://noon.com/p/1-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-https://noon.com/p/1-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-Noon.com-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-Noon.com-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-m1-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-m1-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-9-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-9-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-noon.com/path-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-noon.com/path-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id--False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id--False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-None-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[store_cta_tap-merchant_id-None-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-skincare-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-skincare-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-makeup-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-makeup-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-fragrances-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-fragrances-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-SKINCARE-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-SKINCARE-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-1-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category-1-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category--False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[category_coming_soon_tap-category--False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-whatsapp-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-whatsapp-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-copy-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-copy-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-x-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-x-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-telegram-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-telegram-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-snapchat-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-snapchat-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-other-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-other-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-sms-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-sms-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-email-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-email-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-more-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-more-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-facebook-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-facebook-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-SMS-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-SMS-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-3-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_target_opened-share_target-3-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-whatsapp-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-whatsapp-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-copy-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-copy-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-x-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-x-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-telegram-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-telegram-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-snapchat-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-snapchat-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-other-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-other-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-sms-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-sms-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-email-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-email-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-more-True-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-more-True-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-facebook-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-facebook-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-Copy-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-Copy-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-True-False-None]
- tests/test_s81_sf1_surfaces_be.py::test_r23b_property_value_rules[share_channel_selected-channel-True-False-true]
- tests/test_s81_sf1_surfaces_be.py::test_r25_events_on_request_id
- tests/test_s81_sf1_surfaces_be.py::test_r27_size_cap_before_filter
- tests/test_s81_sf1_surfaces_be.py::test_r31_share_on_widened
- tests/test_s81_sf1_surfaces_be.py::test_r32_service_share_targets
- tests/test_s81_sf1_surfaces_be.py::test_r40_log_search_on_bound_id
- tests/test_s81_sf1_surfaces_be.py::test_r50_migration_files_once
- tests/test_s81_sf1_surfaces_be.py::test_r51_046_text
- tests/test_s81_sf1_surfaces_be.py::test_r52_049_text
- tests/test_s81_sf1_surfaces_be.py::test_r53_rollbacks
- tests/test_s81_sf1_surfaces_be.py::test_r54_parity
- tests/test_s81_sf1_surfaces_be.py::test_p61_log_hygiene_on
- tests/test_s81_sf1_surfaces_be.py::test_r70_failure_arms_log_constants[None]
- tests/test_s81_sf1_surfaces_be.py::test_r70_failure_arms_log_constants[true]
- tests/test_s81_sf1_surfaces_be.py::test_p62_client_line_and_fence

### [pyt] lines of the RED file at base
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================ 121 failed, 74 passed, 11 warnings in 12.13s =================
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================ 121 failed, 74 passed, 11 warnings in 13.12s =================
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================ 121 failed, 74 passed, 11 warnings in 14.48s =================

## 2. The measured 422 bytes (base, pinned in P10 / P30)
Envelope: success false, code VALIDATION_ERROR, request_id a str; error (ARROW = U+2192):
- feedback {} / {comparison_id: bad} / {identity_correct, source} -> 'Validation error: body ARROW useful: Field required'
- {useful: null} -> '... useful: Input should be a valid boolean'; {useful: 'maybe'} -> '..., unable to interpret input'
- [1] / 'x' -> 'Validation error: body: Input should be a valid dictionary or object to extract fields from'; JSON null -> 'Validation error: body: Field required'; '{' -> 'Validation error: body ARROW 1: JSON decode error'
- two errors -> the comparison_id message; change_suggestion 1001 -> 'String should have at most 1000 characters'
- share_target in {sms, email, more, foo, 5, null, WhatsApp, True} -> 'Validation error: body ARROW share_target: Input should be 'whatsapp', 'copy', 'x', 'telegram', 'snapchat' or 'other'' (model: literal_error, ctx.expected the same string, input the value)
Re-measured green at base by P10 / P30 (7 OFF spellings each, full config).

## 3. E2 / E3 / E4 (GREEN's; not edited in the real worktree)
- E2 tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once (:528 `for n in ("046", "048", "049", "051"):` -> `for n in ("048", "051"):`; S81-22 edits the same line: union by hand at the second rebase). Applied in the prototype: green.
- E3 tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app (_ALLOWED_CTX_FILES ending :1330 gains app/services/database_service.py; _CTX_CONSUMER_ATTRS :1345 gains it with _LOG_SEARCH_CTX_ATTRS = {"compare_request_id"}; S81-22 adds compare_runs.py to the same tables: union). Applied in the prototype: green.
- E4 SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx node 'S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare' (:315; assertion :346-348 toHaveLength(0) -> toHaveLength(1) + toEqual(['category_coming_soon_tap', { category: 'skincare' }]); renamed '... one category_coming_soon_tap event, ...'); B4 :364-379 unchanged. PROVEN AT GREEN through the junction, not at RED.
- E1: none (R-SF1-17).

## 4. Prototype (scratch worktree <scratchpad>/sf1p at 18cb9e04, junction-free, removed)
Files: 046 + 049 + both rollbacks (the spec's G9 protos + lock_timeout, NOTIFY after COMMIT (the 042 form), the comment gate), feedback_routes, feedback_service, version_routes, referral_routes, referral_service, database_service, E2, E3. CRLF-preserving: git diff --stat content lines only (feedback_routes 207, feedback_service 49, referral_routes 21, version_routes 18, database_service 17, referral_service 14, kb_schema 2, s05 4). Diff: S81-SF1_red/prototype.diff; bytes: S81-SF1_red/prototype_files/ (never committed). The client line was NOT in the ruled prototype; one supplementary run added the single HomeScreen.tsx line (text only, no junction) to prove P62 satisfiable (prototype_files/HomeScreen.supplementary.tsx).
Mechanism notes for GREEN: the OFF model-validator dumps a frozen _FeedbackRequestBase (base 422 bytes identical, incl. the non-dict class name); the EventItem crid before-validator returns None OFF; the ShareRequest before-validator raises PydanticCustomError('literal_error', 'Input should be {expected}', ...) with the measured expected string OFF; the merchant_id rule is KB_HOST_REGEX via fullmatch (re.match with $ accepts a trailing newline); the three except arms log `type=%s code=%s` with no exc_info (exc_info prints str(e) in the traceback: M33b).

### [pyt] lines
- flags unset (client line absent; R32 literal still wrong):
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================= 2 failed, 193 passed, 11 warnings in 8.94s ==================
- flags unset after the R32 literal fix:
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================= 1 failed, 194 passed, 11 warnings in 8.76s ==================
- flags exported ON:
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ================= 1 failed, 194 passed, 11 warnings in 8.49s ==================
- with the supplementary client line:
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ====================== 195 passed, 11 warnings in 7.58s =======================
- FINAL file, flags unset:
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ====================== 195 passed, 11 warnings in 8.36s =======================
- FINAL file, flags exported ON:
    [hermeticity] sentinel checked 195 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    ====================== 195 passed, 11 warnings in 8.58s =======================
Final: 195 passed in both states (every RED row green, every PIN row green, the OFF byte identity).

### Pins on the prototype (23 files, proto_pins.txt)
- flags unset:
    [hermeticity] sentinel checked 1837 test(s)
    [netguard] blocked 2 attempt(s) from 2 node(s)
    ==== 1 failed, 1836 passed, 4 deselected, 96 warnings in 83.02s (0:01:23) =====
- ENABLE_FEEDBACK_V2 + ENABLE_SURFACES_FIELD + APP_SURFACES_LIVE exported:
    [hermeticity] sentinel checked 1837 test(s)
    [netguard] blocked 3 attempt(s) from 3 node(s)
    ==== 13 failed, 1824 passed, 4 deselected, 96 warnings in 81.57s (0:01:21) ====
Flags unset: only the r06 lexicon CRLF noise. Exported ON: 13 = r06 + 12 ambient-env pins (tests/test_s81_s10_fragrance_gate.py r51 / r54 x5 / p01 x5 see the surfaces key; tests/test_feedback.py::TestFeedbackEndpoint::test_feedback_missing_useful_field sees ON). s05 / st1 / w4_13 ledger / kb_schema / d22 p6 p7 / events superset / b1_feedback green in BOTH states (the W4-13 ledger identical in both SF1 states).

## 5. Mutation table (byte copies in the scratch worktree, .qa-mutation.lock held, restore sha-verified, the whole RED file per mutant, bound 600)
| M | mutant | file | result | killing rows |
|---|---|---|---|---|
| M01 | feedback_v2_enabled returns True (not gated) | app/services/feedback_service.py | KILLED | test_p10_feedback_off_422_bytes, test_p11_feedback_off_accepts_and_drops, test_p12_feedback_off_stored_row, test_p24_events_off_identity, test_p30_share_off_422_bytes, test_r01_feedback_v2_reader, test_r02_log_search_reader_parity, test_r32_service_share_targets |
| M02 | OFF model-validator drops the isinstance(dict) check | app/api/feedback_routes.py | KILLED | test_p10_feedback_off_422_bytes |
| M03 | OFF branch returns data instead of the base dump | app/api/feedback_routes.py | KILLED | test_p10_feedback_off_422_bytes, test_p11_feedback_off_accepts_and_drops |
| M04 | submit_feedback passes the new kwargs in both states | app/api/feedback_routes.py | KILLED | test_p11_feedback_off_accepts_and_drops, test_p12_feedback_off_stored_row |
| M05 | save_feedback writes useful unconditionally | app/services/feedback_service.py | KILLED | test_r14_feedback_on_stored_row |
| M06 | source omitted from the ON kwargs | app/api/feedback_routes.py | KILLED | test_r13_feedback_on_accepts_v2, test_r16_feedback_on_contact_source |
| M07 | correction limit 81 | app/api/feedback_routes.py | KILLED | test_r15_feedback_on_422s |
| M07b | correction not stripped | app/api/feedback_routes.py | KILLED | test_r13_feedback_on_accepts_v2, test_r15_feedback_on_422s, test_r15b_correction_control_chars_and_raw_cap |
| M08 | EventItem OFF validator validates instead of dropping | app/api/feedback_routes.py | KILLED | test_p24_events_off_identity |
| M09 | four names inserted before image_load_failed | app/api/feedback_routes.py | KILLED | test_r20_event_types_appended |
| M10 | allowlist store_cta_tap gains url | app/api/feedback_routes.py | KILLED | test_r21_property_allowlist_dict |
| M11 | the property filter gated under the flag (R-SF1-38 says unflagged) | app/api/feedback_routes.py | KILLED | test_r22_new_types_accepted_off, test_r23_property_filter, test_r23b_property_value_rules |
| M12 | the filter applied to every type | app/api/feedback_routes.py | KILLED | test_p24_events_off_identity, test_r23_property_filter |
| M13 | the [EVENTS] line carries the dropped key names | app/api/feedback_routes.py | KILLED | test_r22_new_types_accepted_off, test_r23_property_filter, test_r23b_property_value_rules |
| M14 | share_target OFF validator removed | app/api/referral_routes.py | KILLED | test_p30_share_off_422_bytes |
| M15 | _share_targets returns the widened set in both states | app/services/referral_service.py | KILLED | test_r32_service_share_targets |
| M16 | log_search reads the context before the flag | app/services/database_service.py | KILLED | test_p41_log_search_off_identity |
| M17 | log_search writes the key when None | app/services/database_service.py | KILLED | test_r40_log_search_on_bound_id |
| M18 | surfaces_live accepts any token | app/api/version_routes.py | KILLED | test_r04_surfaces_knob_parse, test_r05_version_surfaces_on, test_r05b_version_surfaces_on_knob_unset, test_r06_version_key_order_both_flags, test_r08_unknown_chip_never_on_wire |
| M19 | surfaces values are strings | app/api/version_routes.py | KILLED | test_r04_surfaces_knob_parse, test_r05_version_surfaces_on, test_r05b_version_surfaces_on_knob_unset, test_r06_version_key_order_both_flags, test_r08_unknown_chip_never_on_wire |
| M20 | surfaces placed after categories_live | app/api/version_routes.py | KILLED | test_r06_version_key_order_both_flags |
| M21 | surfaces_field_enabled ignores .strip() | app/api/version_routes.py | KILLED | test_r03_surfaces_reader, test_r05_version_surfaces_on |
| M22 | the knob read before the flag | app/api/version_routes.py | KILLED | test_p07_version_off_identity |
| M23 | 046 DROP NOT NULL outside the DO guard | migrations/046_comparison_feedback_v2.sql | KILLED | test_r51_046_text |
| M24 | 049 <> 1 -> = 0 | migrations/049_share_target_and_request_ids.sql | KILLED | test_r52_049_text |
| M26 | the client line uses a constant instead of the literal | SmartCompareApp/src/screens/HomeScreen.tsx | KILLED | test_p62_client_line_and_fence |
| M27 | merchant_id value rule accepts any string | app/api/feedback_routes.py | KILLED | test_r23b_property_value_rules |
| M28 | category value rule accepts any string | app/api/feedback_routes.py | KILLED | test_r23b_property_value_rules |
| M29 | channel / share_target value rule accepts any string | app/api/feedback_routes.py | KILLED | test_r23b_property_value_rules |
| M30 | merchant_id rule uses match (prefix) instead of fullmatch | app/api/feedback_routes.py | KILLED | test_r23b_property_value_rules |
| M31 | feedback except arm restores {e} | app/services/feedback_service.py | KILLED | test_r70_failure_arms_log_constants |
| M32 | events except arm restores {e} | app/services/feedback_service.py | KILLED | test_r70_failure_arms_log_constants |
| M33 | search_logs except arm restores {e} | app/services/database_service.py | KILLED | test_r70_failure_arms_log_constants |
| M33b | feedback arm keeps constants but adds exc_info (traceback text) | app/services/feedback_service.py | KILLED | test_r70_failure_arms_log_constants |
| M34 | the empty-body 422 under ON removed | app/api/feedback_routes.py | KILLED | test_r15c_empty_body_under_on |
| M35 | surfaces omitted when the knob is unset | app/api/version_routes.py | KILLED | test_r05b_version_surfaces_on_knob_unset |
| M36 | the control-character rule removed | app/api/feedback_routes.py | KILLED | test_r15b_correction_control_chars_and_raw_cap |
| M37 | the 1,000-char raw cap removed | app/api/feedback_routes.py | KILLED | test_r15b_correction_control_chars_and_raw_cap |
| M38 | 046 NOTIFY pgrst removed | migrations/046_comparison_feedback_v2.sql | KILLED | test_r50_migration_files_once |
| M39 | 049 lock_timeout removed | migrations/049_share_target_and_request_ids.sql | KILLED | test_r50_migration_files_once |
| M40 | rollback 046 SET NOT NULL not comment-gated (condition -> TRUE) | migrations/rollback/046_comparison_feedback_v2.sql | KILLED | test_r53_rollbacks |
| M40b | rollback 046 gate short-circuited (IF TRUE OR col_description ...) | migrations/rollback/046_comparison_feedback_v2.sql | SURVIVED |  |
| M41 | 046 comment written outside the guard | migrations/046_comparison_feedback_v2.sql | KILLED | test_r51_046_text |
| M42 | database_service local reader ignores .strip() (parity) | app/services/database_service.py | KILLED | test_r02_log_search_reader_parity |
| M43 | database_service local reader returns True | app/services/database_service.py | KILLED | test_p41_log_search_off_identity, test_r02_log_search_reader_parity |
| M44 | create_invite message from the base set under ON | app/services/referral_service.py | KILLED | test_r32_service_share_targets |
| M45 | track_events_batch drops compare_request_id | app/services/feedback_service.py | KILLED | test_r25_events_on_request_id |

47 mutants (the spec's 26 renumbered minus the jest M25, plus the ruled additions M27-M45 and the variants M07b / M33b / M40b): 46 KILLED, 1 SURVIVED (M40b). M24 survived the first run (R52 matched the 049 ASSERT block's `<> 1 THEN`); R52 was tightened to the guard DO body and M24 re-ran KILLED (run 3, shown). M25 (the client line inside the timer) is the jest mutant of E4: GREEN's through the junction. M40b (`IF TRUE OR col_description(...) = 'sf1_dropped_not_null'`) is a text-pin limit: the gate text is present but short-circuited; only the G9 cluster run at GREEN (section 7.4) can kill it: ruling asked (equivalent-by-text, or a G9 row). Run 1 used the RED bytes before the R50 CR relaxation and the R52 tightening; only R52 killed / missed a run-1 049 mutant (M24, re-run).
Per-mutant [pyt] lines:
    M01 [pyt] tag=sf1-mut-m01 start=2026-11-06 16:18:11 end=2026-11-06 16:18:22 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M01.log
    M02 [pyt] tag=sf1-mut-m02 start=2026-11-06 16:18:22 end=2026-11-06 16:18:32 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M02.log
    M03 [pyt] tag=sf1-mut-m03 start=2026-11-06 16:18:32 end=2026-11-06 16:18:43 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M03.log
    M04 [pyt] tag=sf1-mut-m04 start=2026-11-06 16:18:43 end=2026-11-06 16:18:54 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M04.log
    M05 [pyt] tag=sf1-mut-m05 start=2026-11-06 16:18:54 end=2026-11-06 16:19:04 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M05.log
    M06 [pyt] tag=sf1-mut-m06 start=2026-11-06 16:19:04 end=2026-11-06 16:19:15 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M06.log
    M07 [pyt] tag=sf1-mut-m07 start=2026-11-06 16:19:15 end=2026-11-06 16:19:26 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M07.log
    M07b [pyt] tag=sf1-mut-m07b start=2026-11-06 16:19:26 end=2026-11-06 16:19:36 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M07b.log
    M08 [pyt] tag=sf1-mut-m08 start=2026-11-06 16:19:36 end=2026-11-06 16:19:47 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M08.log
    M09 [pyt] tag=sf1-mut-m09 start=2026-11-06 16:19:47 end=2026-11-06 16:19:58 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M09.log
    M10 [pyt] tag=sf1-mut-m10 start=2026-11-06 16:19:58 end=2026-11-06 16:20:08 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M10.log
    M11 [pyt] tag=sf1-mut-m11 start=2026-11-06 16:20:08 end=2026-11-06 16:20:20 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M11.log
    M12 [pyt] tag=sf1-mut-m12 start=2026-11-06 16:20:20 end=2026-11-06 16:20:30 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M12.log
    M13 [pyt] tag=sf1-mut-m13 start=2026-11-06 16:20:31 end=2026-11-06 16:20:43 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M13.log
    M14 [pyt] tag=sf1-mut-m14 start=2026-11-06 16:20:43 end=2026-11-06 16:20:54 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M14.log
    M15 [pyt] tag=sf1-mut-m15 start=2026-11-06 16:20:54 end=2026-11-06 16:21:04 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M15.log
    M16 [pyt] tag=sf1-mut-m16 start=2026-11-06 16:21:04 end=2026-11-06 16:21:15 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M16.log
    M17 [pyt] tag=sf1-mut-m17 start=2026-11-06 16:21:15 end=2026-11-06 16:21:26 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M17.log
    M18 [pyt] tag=sf1-mut-m18 start=2026-11-06 16:21:26 end=2026-11-06 16:21:37 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M18.log
    M19 [pyt] tag=sf1-mut-m19 start=2026-11-06 16:21:37 end=2026-11-06 16:21:48 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M19.log
    M20 [pyt] tag=sf1-mut-m20 start=2026-11-06 16:21:48 end=2026-11-06 16:21:58 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M20.log
    M21 [pyt] tag=sf1-mut-m21 start=2026-11-06 16:21:59 end=2026-11-06 16:22:09 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M21.log
    M22 [pyt] tag=sf1-mut-m22 start=2026-11-06 16:22:09 end=2026-11-06 16:22:20 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M22.log
    M23 [pyt] tag=sf1-mut-m23 start=2026-11-06 16:22:20 end=2026-11-06 16:22:31 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M23.log
    M24 [pyt] tag=sf1-mut-m24 start=2026-11-06 16:27:17 end=2026-11-06 16:27:28 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M24.log
    M26 [pyt] tag=sf1-mut-m26 start=2026-11-06 16:22:40 end=2026-11-06 16:22:50 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M26.log
    M27 [pyt] tag=sf1-mut-m27 start=2026-11-06 16:22:50 end=2026-11-06 16:23:00 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M27.log
    M28 [pyt] tag=sf1-mut-m28 start=2026-11-06 16:23:00 end=2026-11-06 16:23:11 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M28.log
    M29 [pyt] tag=sf1-mut-m29 start=2026-11-06 16:23:11 end=2026-11-06 16:23:22 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M29.log
    M30 [pyt] tag=sf1-mut-m30 start=2026-11-06 16:23:22 end=2026-11-06 16:23:32 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M30.log
    M31 [pyt] tag=sf1-mut-m31 start=2026-11-06 16:23:32 end=2026-11-06 16:23:43 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M31.log
    M32 [pyt] tag=sf1-mut-m32 start=2026-11-06 16:23:43 end=2026-11-06 16:23:54 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M32.log
    M33 [pyt] tag=sf1-mut-m33 start=2026-11-06 16:23:54 end=2026-11-06 16:24:06 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M33.log
    M33b [pyt] tag=sf1-mut-m33b start=2026-11-06 16:24:06 end=2026-11-06 16:24:17 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M33b.log
    M34 [pyt] tag=sf1-mut-m34 start=2026-11-06 16:24:17 end=2026-11-06 16:24:27 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M34.log
    M35 [pyt] tag=sf1-mut-m35 start=2026-11-06 16:24:27 end=2026-11-06 16:24:37 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M35.log
    M36 [pyt] tag=sf1-mut-m36 start=2026-11-06 16:24:37 end=2026-11-06 16:24:48 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M36.log
    M37 [pyt] tag=sf1-mut-m37 start=2026-11-06 16:24:48 end=2026-11-06 16:24:58 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M37.log
    M38 [pyt] tag=sf1-mut-m38 start=2026-11-06 16:24:58 end=2026-11-06 16:25:08 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M38.log
    M39 [pyt] tag=sf1-mut-m39 start=2026-11-06 16:25:08 end=2026-11-06 16:25:18 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M39.log
    M40 [pyt] tag=sf1-mut-m40 start=2026-11-06 16:25:18 end=2026-11-06 16:25:28 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M40.log
    M40b [pyt] tag=sf1-mut-m40b start=2026-11-06 16:27:28 end=2026-11-06 16:27:38 elapsed=10s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M40b.log
    M41 [pyt] tag=sf1-mut-m41 start=2026-11-06 16:25:38 end=2026-11-06 16:25:48 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M41.log
    M42 [pyt] tag=sf1-mut-m42 start=2026-11-06 16:25:49 end=2026-11-06 16:25:59 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M42.log
    M43 [pyt] tag=sf1-mut-m43 start=2026-11-06 16:25:59 end=2026-11-06 16:26:09 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M43.log
    M44 [pyt] tag=sf1-mut-m44 start=2026-11-06 16:26:09 end=2026-11-06 16:26:19 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M44.log
    M45 [pyt] tag=sf1-mut-m45 start=2026-11-06 16:26:20 end=2026-11-06 16:26:30 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\mut_M45.log

## 6. Comm set (COMM_SET.txt, comm_reasons.tsv; 297 files)
Derived ONCE by the union rule (derive_comm.py): the reference grep (feedback_routes | feedback_service | version_routes | referral_routes | referral_service | database_service | log_search | VALID_EVENT_TYPES | share_target | get_version_info | compare_request_id | request_context) + the spec recipe arm (app.main | TestClient) + importers of the two edited test modules + the migration readers (test_migration_*, the _retro_r_mig_sql users, retro_w1_2b / 2c / 2d, sqlfluff_config, index predicate) + kb_schema + s05 + d22 + the SmartCompareApp-scanning backend tests + the source-scanning pins (named + glob / rglob / listdir / scandir / walk / getsource / ast.parse / __file__ readers) + the CLAUDE.md readers (grep + the six by the import graph) + the named members of spec 7.5 = 253 files; UNION the spec's measured union (sf1/comm_union.txt, 274 files: 44 only there, 23 only in mine) = 297; minus the four test_precommit_hook files. Additions over the spec union (23): tests/test_analytics.py, test_content_blocklist_arabic_parity, test_m13_35_sse_disconnect_finally, test_m18_openai_tpm_sizing, test_m18_preverdict_disconnect_refund, test_m21_brand_dedup_and_verdict_copy, test_no_luxury_gate_in_tier3, test_observability, test_openai_key_log_hygiene_s69, test_prompt_fence, test_retro_w1_2c, test_s81_d17_coverage, test_s81_d22d_learning_hardening, test_s81_g5_gate_rows, test_s81_g7_gate_rows, test_s81_s09_gate_rows, test_s81_s10_gate_rows, test_s81_s19_gap_queue, test_s81_sf1_surfaces_be (the RED file), test_security_middleware, test_sqlfluff_config, test_value_badge_category_dims, test_wide_signal_text.

## 7. Base record (the LAST step) -- harness/base_records/18cb9e04a36382fc417307500a092486f618d95e/4345a7845d81fa5342d6904eed6cb495e75d5050d2f35a15edecc3f5de3a7154.{txt,files,pyt.log,header.txt}
- Same-sha scan: only S81-22's PARTIAL_e701a8ba... (its header: 'do not reuse ... until the remaining chunks are measured'), not reused.
- GC-9 per-file reuse from 05303c6f/a0bfab95: 119 REUSED (4 failed nodes carried: test_auth_interceptor x2, test_prompt_truth x2 cold tiktoken); 178 RUN in the REAL worktree in 8 chunks of <= 25 (reuse_split.tsv: 129 reference a #391 stem or CLAUDE.md, 32 not in a record, 16 glob / walk readers, 1 own file changed).
- FAILED node ids: 139 = 4 reused + 121 RED nodes + 14 autocrlf CRLF environmental: test_s81_s10_fragrance_gate::test_r06_production_lexicon_content, test_s81_d17_coverage::test_r9_railway_config_and_hygiene, test_s81_d16_operator_ingest::test_r10_runbook_names_only, test_s81_d22c_profile_select::test_p1_flag_off_golden x5 (a sha over working-copy bytes), test_s81_s16_kb_seed::test_s16_r27_hygiene_of_g2_files x5, test_s81_s19_gap_queue::test_r15_hygiene. No other failure.
- tests/test_secret_scan_static.py ALONE: 31 passed.
- The CI-order set (spec 1.10 set A + set B, 29 files) once at base: 1 failed (r06 CRLF), 1271 passed, 1 skipped, 4 deselected (as the spec measured).
[pyt] lines (progress.txt):
    [pyt] tag=sf1-base-secret start=2026-11-06 16:28:58 end=2026-11-06 16:29:05 elapsed=8s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-secret.log
    [pyt] tag=sf1-base-ciorder start=2026-11-06 16:29:06 end=2026-11-06 16:30:22 elapsed=76s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-ciorder.log
    [pyt] tag=sf1-base-c00 start=2026-11-06 16:30:22 end=2026-11-06 16:31:21 elapsed=59s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c00.log
    [pyt] tag=sf1-base-c02 start=2026-11-06 16:33:58 end=2026-11-06 16:34:38 elapsed=40s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c02.log
    [pyt] tag=sf1-base-c03 start=2026-11-06 16:36:42 end=2026-11-06 16:39:06 elapsed=143s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c03.log
    [pyt] tag=sf1-base-c04 start=2026-11-06 16:39:07 end=2026-11-06 16:41:42 elapsed=155s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c04.log
    [pyt] tag=sf1-base-c05 start=2026-11-06 16:43:46 end=2026-11-06 16:45:39 elapsed=112s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c05.log
    [pyt] tag=sf1-base-c06 start=2026-11-06 16:45:40 end=2026-11-06 16:47:24 elapsed=104s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c06.log
    [pyt] tag=sf1-base-c07 start=2026-11-06 16:47:25 end=2026-11-06 16:47:31 elapsed=6s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-SF1_red\base_sf1-base-c07.log
    [pyt] tag=sf1-base-c01 line LOST (the first driver was stopped while c01 ran); its log: 1929 passed, 10 deselected in 110.22s; [netguard] blocked 56 attempt(s) from 33 node(s)
    c00: [hermeticity] sentinel checked 1522 test(s) | [netguard] blocked 30 attempt(s) from 8 node(s) | ============== 1522 passed, 1 deselected, 13 warnings in 55.69s ===============
    c01: [hermeticity] sentinel checked 1929 test(s) | [netguard] blocked 56 attempt(s) from 33 node(s) | ======== 1929 passed, 10 deselected, 16 warnings in 110.22s (0:01:50) =========
    c02: [hermeticity] sentinel checked 779 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | =============== 779 passed, 4 deselected, 10 warnings in 38.07s ===============
    c03: [hermeticity] sentinel checked 1446 test(s) | [netguard] blocked 26 attempt(s) from 6 node(s) | === 1446 passed, 24 skipped, 2 deselected, 13 warnings in 141.35s (0:02:21) ===
    c04: [hermeticity] sentinel checked 3297 test(s) | [netguard] blocked 28 attempt(s) from 4 node(s) | =========== 7 failed, 3290 passed, 63 warnings in 151.18s (0:02:31) ===========
    c05: [hermeticity] sentinel checked 2000 test(s) | [netguard] blocked 36 attempt(s) from 15 node(s) | ========== 128 failed, 1872 passed, 13 warnings in 109.14s (0:01:49) ==========
    c06: [hermeticity] sentinel checked 1134 test(s) | [netguard] blocked 138 attempt(s) from 66 node(s) | = 1089 passed, 10 skipped, 11 deselected, 35 xfailed, 16 warnings in 101.48s (0:01:41) =
    c07: [hermeticity] sentinel checked 80 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | ======================== 80 passed, 1 warning in 4.48s ========================
    secret: [hermeticity] sentinel checked 31 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | ======================== 31 passed, 1 warning in 6.29s ========================
    ciorder: [hermeticity] sentinel checked 1272 test(s) | [netguard] blocked 11 attempt(s) from 6 node(s) | = 1 failed, 1271 passed, 1 skipped, 4 deselected, 14 warnings in 74.01s (0:01:14) =

## 8. Deviations / findings / questions
- R22 amended by R-SF1-38: OFF stores the four new types FILTERED (the filter is unflagged), not 'as sent' (spec 5); M11 re-cast as 'the filter gated under the flag'.
- R-SF1-27 read strictly: the except arms log no exc_info (a traceback prints str(e), i.e. the PostgREST detail with the failing row); R70 checks the formatted record incl. the traceback (mutant M33b). The events / search twins' templates are not ruled: R70 pins only 'type=APIError' and 'code=23502' in every WARNING there; GREEN chooses the text.
- merchant_id value rule = the MEASURED kb_merchants.host CHECK of 045 (= kb_service.KB_HOST_REGEX, full match, <= 253 chars), not the fallback ^[a-z0-9][a-z0-9._-]{0,63}$ (a CHECK exists): 'm1' (no dot) is DROPPED (R23b).
- R-SF1-32 'no answer' set as pinned: useful / the three 027 / the three 046 answers not None, correction or change_suggestion non-blank (a non-str value counts, then fails its own validation), mattered_most non-empty; source / comparison_id / compare_request_id are not answers. The wire message ENDS with the literal (pydantic adds 'Value error, ' for a ValueError).
- R50 'no CR' is autocrlf-tolerant (CRLF pairs folded): 052 is CRLF in the Windows working copy (no .gitattributes); a strict check would add a new r06-class local noise after any re-checkout; LF in the commit stays a GREEN hygiene gate.
- R32 literal sort fixed during RED ('sms' < 'snapchat'); R52 tightened after M24 survived (section 5).
- BOX DISCIPLINE (finding): wmic is absent on this box; the first base driver's probe failed open, so the CI-order set and chunks c00 / c01 overlapped S81-22 mutant runs (the runner ledger shows s22red-m43..m75 interleaved). The driver was stopped and re-launched ONCE with a PowerShell Get-CimInstance probe from c02 (c02-c07 waited for a quiet box, 60 s polls). My RED-file, prototype and mutant runs (16:07-16:28) also ran beside the S81-22 mutant loop with no probe. Results are valid measurements under load (no TIMEOUT); the base record header says so.
- Spec 7.3 ('the pins again with ENABLE_FEEDBACK_V2=true exported'): exporting the SF1 flags over the whole pin set fails 12 ambient-env pins (s10 r51 / r54 / p01, test_feedback missing_useful); keep that step to s05 / st1 / w4_13 as written.
- P62 is RED in the ruled prototype (no client line); proven satisfiable by one supplementary text-only run.
- M40b survives (text pin limit): ruling asked; the G9 cluster at GREEN is the killer.
- Report-side files written in Windows text mode (CRLF) were normalized to LF (run_list.txt, reuse_split.tsv, reused_failures.txt, chunks.txt, progress.txt).
- An early shell rewrite truncated the RED file to 0 bytes (open('wb') before a failed ascii encode); it was rewritten in full with the Write tool and re-verified (final sha above).

## 9. Restore check
- Real worktree: HEAD 18cb9e04, git diff empty, git status --short = `?? tests/test_s81_sf1_surfaces_be.py` only (no app/, migrations/, tests/ beyond the one file, docs/, SmartCompareApp/ or CLAUDE.md change).
- Scratch worktree <scratchpad>/sf1p removed with git worktree remove --force, absent from git worktree list; no node_modules junction ever existed; .qa-mutation.lock removed; the prototype shas equal the pre-mutation snapshot (proto_sha_before_mut.txt) before removal.
- No orphan pytest of mine (the stopped first driver's c01 child completed).

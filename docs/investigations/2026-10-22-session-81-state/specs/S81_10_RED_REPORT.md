# S81-10 FRAGRANCE-ONLY-GATE: RED report

- Agent: Opus 5.5 RED agent (resumed run, 2026-11-02 10:44-11:4x local; the 2026-10-29 21:08 run had stopped after reading).
- Base: 6c14ac954f601902d322547de04982033aca5925 (real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10, detached; HEAD = base before and after).
- Precedence applied: RULINGS_S81_10 (R-S10-1..16 + measurement rulings) > review corrections C1-C30 > spec; the brief beneath.
- Written through the shell (python), per the harness rule: this report, notes.md, comm_files.txt, comm_reasons.tsv, S81-10_MUTATION_TABLE.tsv, S81-10_prototype.diff (all under <scratchpad>/S81-10_red/, <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad); a copy of this report at <scratchpad>/S81-10_RED_REPORT.md.

## 0. Files written in the real worktree (the only two; untracked)

| file | bytes | sha256 | bytes > 127 | CR |
|---|---|---|---|---|
| tests/test_s81_s10_fragrance_gate.py | 110,434 | d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac | 0 | 0 |
| tests/fixtures/s81_s10_flag_off_golden.json | 17,123 | 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a | 0 | 0 |

gitleaks 8.30.1 with HEAD:.gitleaks.toml (the hook's config, --ignore-gitleaks-allow, dir mode over copies): rc=0, [] (no finding; the GC-14 trap avoided: every synthetic credential-like value is built by concatenation). py_compile + ruff E9,F63,F7,F82,F401,F811,F841: clean.

## 1. Measurements at the base (6c14ac95)

- e7c81956..6c14ac95 (git diff --name-only): SmartCompareApp files + CLAUDE.md + docs/privacy-data-inventory.md only; 0 files under app/ tests/ scripts/ data/ migrations/ .github/. Every app/ and tests/ line the spec cites holds at 6c14ac95.
- CLAUDE.md anchors at 6c14ac95: Feature Flags line :341 (unchanged); the S81-15 block :517; NEW the S81-08 CLIENT-FIRST-OTA block :522; `## Tests` :531 (the spec measured :522 at e7c81956). The S81-10 row goes after the S81-08 block (and after S81-09's once merged), before `## Tests`, one column-0 paragraph, no new `## ` heading (C19 / RB8-5a).
- The spec's 14 pin files re-run: [pyt] tag=s10red-pins14 start=2026-11-02 10:51:23 end=2026-11-02 10:52:00 elapsed=37s bound=1200s status=OK rc=0 ; 717 passed, 4 deselected ; [hermeticity] sentinel checked 717 test(s) ; [netguard] blocked 53 attempt(s) from 26 node(s) (the same pre-existing nodes as the spec's run).
- Probe rows (scratch worktree, base bytes): [pyt] tag=s10red-probe-ab start=2026-11-02 11:23:52 end=2026-11-02 11:23:56 elapsed=4s bound=600s status=OK rc=0 (2 passed; [hermeticity] 2; [netguard] blocked 0): classify_category_from_text: the two hair-mist pairs -> haircare, 'Hair & Body Mist' -> haircare, hair perfume -> fragrances, 'Khamrah Hawas' -> other, 'perfume laptop' -> fragrances, 'Dior Sauvage iPhone 15' -> other; POST /text/compare logs 'Text comparison request: <query>' at INFO (text_routes :596).
- p01 probe: [pyt] tag=s10red-probe-p01 start=2026-11-02 11:24:06 end=2026-11-02 11:24:10 elapsed=4s bound=600s status=FAIL rc=1 ([netguard] blocked 0): with a 14-line spec-shaped app/services/category_gate.py (function-local `from app.utils import request_context as _request_context`) test_s05_p01_no_consumer_in_app fails with exactly `AssertionError: app/services/category_gate.py`; test_s05_p07 stays green. The probe module was removed right after.

## 2. The RED file: structure and contract

140 nodes = 99 RED nodes (57 row functions R01-R57; R26b / R26c added, R33+R34 one parametrised function, the spec's stream refund row became PIN P08) + 41 PIN nodes (8 functions P01-P08). Harnesses: `Harness` (route level: the real app through TestClient, the REAL S81-05 middleware binding a synthetic X-Device-Fingerprint, every paid leaf faked into ONE ordered recorder, a redis-py / upstash-shaped Redis fake installed as cache_service.redis_client emulating the INCR script), `SvcHarness` (a REAL StructuredComparisonService; parse / A2b / fetch / profile / demographics as plain functions returning coroutines so the CALL order is the recorded order; the fetch returns a both-failed Phase 1 so a compare that passes the gate ends at INSUFFICIENT_DATA right after the fetch). The full B1 configuration on every PIN: REFUSAL_DAILY_BUDGET=1, a run-time lexicon that would refuse G02 / G04 / G12, ENABLE_REQUEST_CONTEXT_HEADERS=true + a synthetic DEVICE_KEY_PEPPER (set after app.main import, C20), ENABLE_PAID_ROUTE_METERING=true, refusal counters seeded ABOVE the budget for both subjects.

Names the RED pins for GREEN (the spec's 3.1 list, plus the seams R-S10-11 asks for, named here because the rulings do not name them): `reset_window(now) -> (day, next_reset, utc_offset_hours)` (usage_service._usage_window + the Riyadh offset once S81-09 merges, else the UTC-midnight fallback; R46 adapts to both), `budget_exempt_async(user_id)` (the DEVICE_QUOTA_EXEMPT_USER_IDS allow-list with the S81-09 parsing, or subscription_tier premium via usage_service._get_user_tier_info, read only when a budget is spent), `retry_fields(now, next_reset, offset)`, `budget_keys(subject, day)`, `REFUSAL_INCR_SCRIPT` (a two-key loop, R-S10-1), GateDecision(outcome, category, evidence, subject repr=False) frozen, ScanResult(non_fragrance, fragrance_type, houses, notes, evidence), `error_handler._CANONICAL_CATEGORY_KEYS`.

| Row | Asserts (short) | At base | Kills |
|---|---|---|---|
| R01 | flag reader: five ON spellings True, five OFF False, flips per call | RED | - |
| R02 | REFUSAL_DAILY_BUDGET: 17 spellings (10 default, 7.9->7, 1e3->100, inf/nan/<=0/garbage->10) | RED | M25 |
| R03 | FRAGRANCE_LEXICON_PATH: unset/blank -> repo data/fragrance_lexicon.json, relative -> repo, absolute as is | RED | - |
| R04 | the lexicon re-read on change (path, mtime_ns, size), the knob set after import honoured | RED | M06 |
| R05 | missing / invalid JSON / wrong schema: proceed, evidence False, ONE WARNING per state (type=FileNotFoundError / JSONDecodeError) | RED | - |
| R06 | data/fragrance_lexicon.json: ASCII, LF, exact schema, the 2.2 EN minimum (+ hair perfume, R-S10-5), an Arabic term in every list, no duplicate / cross-section term, C4 (no note word and no coffee / milk / tea / honey / chocolate, EN + AR, in non_fragrance) | RED | - |
| R07 | rule 1 EN: laptop -> electronics, cream -> skincare, lipstick (no house) -> makeup | RED | - |
| R08 | rule 1 AR: article + tatweel + fatha shampoo -> haircare; AR perfume + house -> proceed evidence True | RED | M23 |
| R09 | edp + body lotion proceeds, evidence True; scan non_fragrance exact | RED | M31 |
| R10 | R-S10-4: house / note beside a category word -> proceed with evidence False (gucci bag x2, Dior body cream, Dior / Chanel lipstick, Jo Malone Blush Suede, Frederic Malle Lipstick Rose) | RED | M05, M05b |
| R11 | longest-first masking (C8: hair mist leaves non_fragrance []; ice cream x2; body lotion before lotion) | RED | M24, M31 |
| R12 | whole tokens: iphone never phone; smartphones refused | RED | - |
| R13 | notes need two; vanilla ice cream proceeds evidence False (R-S10-4) | RED | M05b |
| R14 | AR normalisation: alef forms, ta marbuta, alef maqsura, diacritics, tatweel, both digit sets, the six articles once, >= 2 letters, waw kept | RED | M23 |
| R15 | separators, NFKC full-width EDP, Latin accents stripped (C23: Hermes / Lancome / Chloe) | RED | M30 |
| R16 | POST rule 1 $0: 400, keys [success,error,code,request_id,category,categories_live], no prefs / Redis / consume / compare / refund, one INFO pre_consume line | RED | M01, M21 |
| R17 | GET rule 1 (q and pair) | RED | - |
| R18 | stream rule 1: a JSON 400 (not text/event-stream) | RED | - |
| R19 | order: budget reads < prefs < consume < compare; reads = acct + dev keys; compare carries fragrance_gate (proceed, evidence True, subject) | RED | - |
| R20 | budget spent (POST/GET/stream x account axis / device axis): 429, keys [..., categories_live, scope, resets_at, retry_after_seconds], Retry-After 1800, never billed, one INFO | RED | M04, M42 |
| R21 | boundary budget-1 / budget / budget+5; the knob per call | RED | M13 |
| R22 | R-S10-1 subjects: header + account -> both keys; no header -> account key; anonymous no header -> no Redis call; anonymous + header -> device key; the raw fp in no key / arg / log | RED | M14, M42 |
| R23 | fail-open: raising GET -> one WARNING type=RuntimeError; client None silent; nil reply silent (C14); non-numeric -> one WARNING | RED | - |
| R24 | sync post-resolve refusal (parser path): result keys exact, no fetch / profile / demographics / A2b, ONE EVAL (both keys, EXPIREAT next reset + 3600), one INFO post_resolve | RED | M02, M10, M29, M33 |
| R25 | stream: exactly [(status 10), (error, refusal)] | RED | M03 |
| R26 | chip not trusted: blind pair + chip fragrances -> ONE A2b -> refused electronics; resolver called once | RED | M09 |
| R26b | house evidence on a blind pair: no A2b, proceeds | RED | M22 |
| R26c | no chip: the resolver's A2b reused, exactly one call (C11) | RED | M38 |
| R27 | R-S10-3: parser 'other' proceeds with or without evidence; no A2b, no INCR | RED | M10 |
| R28 | chip fragrances, parse makeup (switched) -> refused makeup | RED | - |
| R29 | a fragrance pair proceeds; fetch x2 carries category_used | RED | - |
| R30 | R-S10-3: A2b outage ('other') proceeds, never counted, no refusal line | RED | M39 |
| R31 | R-S10-5: the two hair-mist pairs proceed on the pair path (fetch x2, no INCR) | RED | M37 |
| R32 | R-S10-6: 'dior sauvage vs iphone 15' (parse per product) and ('perfume', 'laptop') (explicit) refused, counted | RED | M36 |
| R33/R34 | POST / GET post-resolve refusal through the EXISTING failure arm: 400 with category + categories_live, consume 1, refund 1 + its label, no lifetime / save / capture | RED | M27 |
| R36 | camera budget spent: 200 action error budget body (key order), no consume, no vision | RED | M28 |
| R37 | camera post-vision rule 1: refusal body, refund 1 (usage_refund.image.category_not_live), INCR 1, no compare / save / lifetime / log_search, one INFO post_vision | RED | M20, M32 |
| R38 | camera post-resolve with ENABLE_CAMERA_FAILURE_ENVELOPE ON -> action error (never comparison_failed), refund 1, no search_logs row | RED | M19 |
| R39 | camera fragrance pair: compare gets fragrance_gate (evidence True); body == the flag-OFF body | RED | - |
| R40 | R-S10-13: 1-product rule-1 exit -> CATEGORY_NOT_LIVE action error, refund 1, INCR 1; a fragrance single stays need_second_product | RED | - |
| R41 | handler passthrough: 400 and 429 key order, Retry-After | RED | - |
| R42 | handler sanitises (non-canonical category; categories_live str / [1] / ['weapons'] / [] / mixed, C25; scope 'daily'; resets_at 5; other codes gain nothing); _CANONICAL_CATEGORY_KEYS tuple == extraction set | RED | M16 |
| R43 | REFUSAL_INCR_SCRIPT == the two-key loop (whitespace-normalised); no EXPIRE / SET | RED | M11, M12 |
| R44 | record through redis-py and upstash shapes: ONE eval, both keys, ARGV [expireat], TTL set, subject None no call, raising EVAL one WARNING | RED | M11, M12, M33 |
| R45 | retry_fields: 1800 / +03:00, 12600 / +00:00, ceil to 1, clamp 1..86400, int + str | RED | - |
| R46 | reset_window seam == usage_service._usage_window (+ Riyadh offset) when present, else the UTC fallback; next strictly after now | RED | - |
| R47 | R-S10-7 allow-list: an exempt account at the budget proceeds; the rules still refuse it | RED | M41 |
| R48 | R-S10-7 premium tier exempt; the tier read only when a budget is spent | RED | M41 |
| R49 | smart pick: the fragrance row picked; query args + cache key == OFF; five non-fragrance -> empty state | RED | M18 (OFF half via P01) |
| R50 | trending (6 regions): the one Fragrances entry; key home:trending:fragrances:<region> (GET + SET 3600); OFF key unchanged | RED | M17, M35 |
| R51 | /app/version: categories_live last | RED | - |
| R52 | C5: the category_gate logger + every [CATEGORY-GATE] record: no sentinel / fp / device key / uid, the 2.10 grammar, below ERROR; non-vacuous (>= 3 refused, 1 budget line) | RED | M14 |
| R53 | KB seam: False with no I/O; raising -> proceeds + one WARNING (an escaping exception is converted to an AssertionError); a KB match adds evidence | RED | M07 |
| R54 | five OFF spellings: raising recorders on every public category_gate function but the flag reader; the 12 golden scenarios equal | RED | M08, M18, M35 |
| R55 | R-S10-2: one function-local `from app.utils import request_context as _request_context`, attrs within {device_fingerprint, device_key}, no needle strings; no other edited file names request_context; p07 needle count 1 in both routes | RED | - |
| R56 | C15 / E1: the acct f-string interpolates `user_id` (census 'refusal:daily:acct:{user_id}:{*}'), the dev one `device_key`; no other census hit | RED | - |
| R57 | constants, body helpers' key order, GateDecision frozen + subject repr=False (C24), budget_keys | RED | - |
| P01 | flag-OFF golden: five OFF spellings x 12 scenarios (calls with arguments, status, content-type / retry-after, raw body, the five loggers' lines); raising recorders once the module exists | PIN | M08, M18, M35 |
| P02 | non-target callers ungated (flag ON + full config): /text/quick passes no fragrance_gate, no Redis; url_routes / url_extraction_service name no gate; the warmer's compare call passes no fragrance_gate | PIN | (M26 equivalent) |
| P03 | R-S10-10: History list + GET by id bodies identical OFF / ON | PIN | - |
| P04 | _surface_comparison_failure mapping unchanged (unset / false / true) | PIN | - |
| P05 | C10: without the kwarg, six flag states x q / pair x sync / stream, NON-fragrance scenarios: the literal base call order | PIN | M34 |
| P06 | R-S10-8: the admin-key path is never gated (rule-1 query proceeds, no Redis, no gate line) | PIN | M40 |
| P07 | C6: flag OFF the CATEGORY_NOT_LIVE details keep the base keys (+ W1-9 retry) | PIN | M15 |
| P08 | an SSE error event with the refusal keys takes the EXISTING had_error refund once (request_id stamped, no save / lifetime / metering) | PIN | - |

## 3. The unit file at the base (real worktree, the two new files only)

- [pyt] tag=s10red-golden-record start=2026-11-02 11:21:55 end=2026-11-02 11:21:59 elapsed=4s bound=600s status=FAIL rc=1 (BY DESIGN: S81_S10_RECORD_GOLDEN=1 makes P01[unset] write the fixture and fail; recorded at 6c14ac95, flag unset, full configuration).
- [pyt] tag=s10red-unit-base start=2026-11-02 11:22:12 end=2026-11-02 11:22:23 elapsed=11s bound=600s status=FAIL rc=1: 99 failed / 41 passed, but 13 were setup ERRORs (the lexicon fixture asserted in setup) -> the fixture was made lazy (the module is read in the row body).
- [pyt] tag=s10red-unit-base2 start=2026-11-02 11:22:56 end=2026-11-02 11:23:08 elapsed=11s bound=600s status=FAIL rc=1: 99 failed (AssertionError only) / 41 passed.
- FINAL bytes: [pyt] tag=s10red-unit-base-final start=2026-11-02 11:40:14 end=2026-11-02 11:40:25 elapsed=11s bound=600s status=FAIL rc=1 ; 99 failed, 41 passed, 11 warnings ; [hermeticity] sentinel checked 140 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s). junit: every one of the 99 failures is a `failure` whose message starts AssertionError / assert (0 errors, 0 other types); the 41 passing nodes are exactly the PIN nodes.

Failed node ids at base (99):
```
tests/test_s81_s10_fragrance_gate.py::test_r01_flag_reader_per_call
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[None-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[25-25]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[ 7 -7]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[7.9-7]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[0-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[-3-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[abc-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[inf-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[-inf-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[nan-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[  -10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[0.5-10]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[250-100]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[100-100]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[1-1]
tests/test_s81_s10_fragrance_gate.py::test_r02_budget_knob[1e3-100]
tests/test_s81_s10_fragrance_gate.py::test_r03_lexicon_path_knob
tests/test_s81_s10_fragrance_gate.py::test_r04_lexicon_reloads_without_restart
tests/test_s81_s10_fragrance_gate.py::test_r05_lexicon_unavailable_fails_safe[missing-FileNotFoundError]
tests/test_s81_s10_fragrance_gate.py::test_r05_lexicon_unavailable_fails_safe[invalid-JSONDecodeError]
tests/test_s81_s10_fragrance_gate.py::test_r05_lexicon_unavailable_fails_safe[schema-None]
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s10_fragrance_gate.py::test_r07_rule1_english
tests/test_s81_s10_fragrance_gate.py::test_r08_rule1_arabic
tests/test_s81_s10_fragrance_gate.py::test_r09_double_product_type_proceeds
tests/test_s81_s10_fragrance_gate.py::test_r10_house_or_note_beside_a_category_word_defers[gucci bag vs prada bag]
tests/test_s81_s10_fragrance_gate.py::test_r10_house_or_note_beside_a_category_word_defers[dior sauvage body cream]
tests/test_s81_s10_fragrance_gate.py::test_r10_house_or_note_beside_a_category_word_defers[dior lipstick vs chanel lipstick]
tests/test_s81_s10_fragrance_gate.py::test_r10_house_or_note_beside_a_category_word_defers[jo malone peony & blush suede vs dior sauvage]
tests/test_s81_s10_fragrance_gate.py::test_r10_house_or_note_beside_a_category_word_defers[frederic malle lipstick rose]
tests/test_s81_s10_fragrance_gate.py::test_r11_longest_match_masking
tests/test_s81_s10_fragrance_gate.py::test_r12_whole_token_boundaries
tests/test_s81_s10_fragrance_gate.py::test_r13_notes_need_two
tests/test_s81_s10_fragrance_gate.py::test_r14_arabic_normalisation
tests/test_s81_s10_fragrance_gate.py::test_r15_case_separators_nfkc_and_accents
tests/test_s81_s10_fragrance_gate.py::test_r16_post_rule1_zero_cost
tests/test_s81_s10_fragrance_gate.py::test_r17_get_rule1_zero_cost[params0]
tests/test_s81_s10_fragrance_gate.py::test_r17_get_rule1_zero_cost[params1]
tests/test_s81_s10_fragrance_gate.py::test_r18_stream_rule1_zero_cost[params0]
tests/test_s81_s10_fragrance_gate.py::test_r18_stream_rule1_zero_cost[params1]
tests/test_s81_s10_fragrance_gate.py::test_r19_rule2_proceeds_in_order
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[post-acct]
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[post-dev]
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[get-acct]
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[get-dev]
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[stream-acct]
tests/test_s81_s10_fragrance_gate.py::test_r20_budget_spent_never_billed[stream-dev]
tests/test_s81_s10_fragrance_gate.py::test_r21_budget_boundary
tests/test_s81_s10_fragrance_gate.py::test_r22_budget_subject_two_axes
tests/test_s81_s10_fragrance_gate.py::test_r23_budget_fail_open
tests/test_s81_s10_fragrance_gate.py::test_r24_sync_post_resolve_refusal
tests/test_s81_s10_fragrance_gate.py::test_r25_stream_post_resolve_refusal
tests/test_s81_s10_fragrance_gate.py::test_r26_chip_is_not_trusted
tests/test_s81_s10_fragrance_gate.py::test_r26b_house_evidence_skips_the_classifier
tests/test_s81_s10_fragrance_gate.py::test_r26c_no_chip_reuses_the_resolver_classifier
tests/test_s81_s10_fragrance_gate.py::test_r27_parser_other_proceeds[dior sauvage vs bleu de chanel-names0-True]
tests/test_s81_s10_fragrance_gate.py::test_r27_parser_other_proceeds[khamrah vs hawas-names1-False]
tests/test_s81_s10_fragrance_gate.py::test_r28_switched_detection_refused
tests/test_s81_s10_fragrance_gate.py::test_r29_proceed_keeps_the_compare
tests/test_s81_s10_fragrance_gate.py::test_r30_classifier_outage_proceeds_uncounted
tests/test_s81_s10_fragrance_gate.py::test_r31_form_hit_overrides_the_name_detection[pair0]
tests/test_s81_s10_fragrance_gate.py::test_r31_form_hit_overrides_the_name_detection[pair1]
tests/test_s81_s10_fragrance_gate.py::test_r32_mixed_pairs_refused_per_product
tests/test_s81_s10_fragrance_gate.py::test_r33_r34_route_refusal_refund_once[post-usage_refund.text.post]
tests/test_s81_s10_fragrance_gate.py::test_r33_r34_route_refusal_refund_once[get-usage_refund.text.get]
tests/test_s81_s10_fragrance_gate.py::test_r36_camera_budget_spent
tests/test_s81_s10_fragrance_gate.py::test_r37_camera_post_vision_rule1
tests/test_s81_s10_fragrance_gate.py::test_r38_camera_post_resolve_never_comparison_failed
tests/test_s81_s10_fragrance_gate.py::test_r39_camera_fragrance_proceeds
tests/test_s81_s10_fragrance_gate.py::test_r40_camera_single_product_rule1
tests/test_s81_s10_fragrance_gate.py::test_r41_handler_passthrough
tests/test_s81_s10_fragrance_gate.py::test_r42_handler_sanitises
tests/test_s81_s10_fragrance_gate.py::test_r43_incr_script_static
tests/test_s81_s10_fragrance_gate.py::test_r44_record_both_client_shapes[FakeRedis-positional]
tests/test_s81_s10_fragrance_gate.py::test_r44_record_both_client_shapes[FakeUpstash-keyword]
tests/test_s81_s10_fragrance_gate.py::test_r45_reset_fields
tests/test_s81_s10_fragrance_gate.py::test_r46_reset_window_seam
tests/test_s81_s10_fragrance_gate.py::test_r47_budget_exempt_allow_list
tests/test_s81_s10_fragrance_gate.py::test_r48_budget_exempt_premium
tests/test_s81_s10_fragrance_gate.py::test_r49_smart_pick_filtered
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[bahrain]
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[saudi_arabia]
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[uae]
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[kuwait]
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[qatar]
tests/test_s81_s10_fragrance_gate.py::test_r50_trending_filtered[oman]
tests/test_s81_s10_fragrance_gate.py::test_r51_version_categories_live
tests/test_s81_s10_fragrance_gate.py::test_r52_log_hygiene
tests/test_s81_s10_fragrance_gate.py::test_r53_kb_seam_fails_open
tests/test_s81_s10_fragrance_gate.py::test_r54_off_calls_nothing_of_the_gate[unset]
tests/test_s81_s10_fragrance_gate.py::test_r54_off_calls_nothing_of_the_gate[false]
tests/test_s81_s10_fragrance_gate.py::test_r54_off_calls_nothing_of_the_gate[0]
tests/test_s81_s10_fragrance_gate.py::test_r54_off_calls_nothing_of_the_gate[off]
tests/test_s81_s10_fragrance_gate.py::test_r54_off_calls_nothing_of_the_gate[empty]
tests/test_s81_s10_fragrance_gate.py::test_r55_request_context_consumer_shape
tests/test_s81_s10_fragrance_gate.py::test_r56_budget_key_fstrings_census_shape
tests/test_s81_s10_fragrance_gate.py::test_r57_constants_bodies_and_repr
```
Passing (PIN) node ids at base (41):
```
tests/test_s81_s10_fragrance_gate.py::test_p08_stream_route_refusal_event_refunds_once
tests/test_s81_s10_fragrance_gate.py::test_p07_handler_flag_off_keeps_the_base_keys[unset]
tests/test_s81_s10_fragrance_gate.py::test_p07_handler_flag_off_keeps_the_base_keys[false]
tests/test_s81_s10_fragrance_gate.py::test_p07_handler_flag_off_keeps_the_base_keys[0]
tests/test_s81_s10_fragrance_gate.py::test_p07_handler_flag_off_keeps_the_base_keys[off]
tests/test_s81_s10_fragrance_gate.py::test_p07_handler_flag_off_keeps_the_base_keys[empty]
tests/test_s81_s10_fragrance_gate.py::test_p01_flag_off_golden[unset]
tests/test_s81_s10_fragrance_gate.py::test_p01_flag_off_golden[false]
tests/test_s81_s10_fragrance_gate.py::test_p01_flag_off_golden[0]
tests/test_s81_s10_fragrance_gate.py::test_p01_flag_off_golden[off]
tests/test_s81_s10_fragrance_gate.py::test_p01_flag_off_golden[empty]
tests/test_s81_s10_fragrance_gate.py::test_p02_non_target_callers_ungated
tests/test_s81_s10_fragrance_gate.py::test_p03_history_whole_under_flag
tests/test_s81_s10_fragrance_gate.py::test_p04_surface_failure_mapping_unchanged[None]
tests/test_s81_s10_fragrance_gate.py::test_p04_surface_failure_mapping_unchanged[false]
tests/test_s81_s10_fragrance_gate.py::test_p04_surface_failure_mapping_unchanged[true]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[unset-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[unset-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[unset-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[unset-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[false-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[false-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[false-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[false-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[0-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[0-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[0-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[0-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[off-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[off-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[off-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[off-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[empty-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[empty-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[empty-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[empty-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[on-q-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[on-q-stream]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[on-pair-sync]
tests/test_s81_s10_fragrance_gate.py::test_p05_orchestrator_order_without_the_kwarg[on-pair-stream]
tests/test_s81_s10_fragrance_gate.py::test_p06_admin_key_path_bypasses_the_gate
```

## 4. Prototype (scratch worktree <scratchpad>/S81-10_red/wt detached at 6c14ac95, removed afterwards)

Diff: <scratchpad>/S81-10_red/S81-10_prototype.diff (42,218 B; 8 tracked files 121+/3-, CRLF kept, + the new app/services/category_gate.py and data/fragrance_lexicon.json; its 12 non-ASCII bytes are repository CONTEXT lines (em dashes), no added line). Copies: proto/category_gate.prototype.py, proto/fragrance_lexicon.prototype.json, proto/apply_proto.py, proto/build_lexicon.py. The two E-rows applied: E1 (test_migration_043 KEPT 'refusal:daily:acct:{user_id}:{*}') and R-S10-2 (test_s81_s05 _ALLOWED_CTX_FILES += app/services/category_gate.py). A REFERENCE for GREEN, never committed.

- [pyt] tag=s10red-proto-on-final start=2026-11-02 11:40:35 end=2026-11-02 11:40:40 elapsed=5s bound=600s status=OK rc=0 ; 140 passed ; [hermeticity] 140 ; [netguard] blocked 0 (ambient ENABLE_FRAGRANCE_ONLY_GATE=true; every row sets its own flag).
- [pyt] tag=s10red-proto-off-final start=2026-11-02 11:40:40 end=2026-11-02 11:40:46 elapsed=5s bound=600s status=OK rc=0 ; 140 passed ; [hermeticity] 140 ; [netguard] blocked 0 (ambient unset).
- Existing pins under the prototype: [pyt] tag=s10red-proto-pins start=2026-11-02 11:32:36 end=2026-11-02 11:33:33 elapsed=57s bound=1200s status=OK rc=0 ; 1524 passed, 4 deselected (the 14 spec pin files + test_s81_s05_request_context + test_s71_u13_compare_auth_required (T23) + test_s81_s06_router_gate_rows + test_w4_13_measurement_truth + test_w4_13_flag_off_ledger + test_s75_fanout_identity + test_retro_w1_9 + test_security_regression + test_ci_gates).

What the spec got wrong or left open (measured on the prototype):
- The admin-key bypass (R-S10-8) needs a signal the route can read: `require_paid_route_user` returns None for both an admin caller and an anonymous one. The prototype sets `request.state.s10_paid_route_admin = True` in the admin branch (no byte / log change OFF); GREEN chooses.
- A hair-mist pair proceeds (R-S10-5) but is COMPARED under the base resolver's category_used (haircare for the Chanel / Dior hair-mist pair: the name synonym 'hair'); the rulings keep category_used for scoring (spec R29). Question Q1.
- The spec's single-key INCR script cannot serve R-S10-1 (two keys): the RED pins a `for i = 1, #KEYS` loop with one ARGV.
- The spec's budget_key (one key) became budget_keys(subject, day) (two axes).
- The camera evaluates the first TWO identified products (the compared pair), not every identified product (a third product in frame is never compared).

## 5. Mutation table (43 mutants on byte copies of the prototype; .qa-mutation.lock held; every restore sha256-verified)

| M | Mutant | File | Rows run (-k) | Verdict | Killed by |
|---|---|---|---|---|---|
| M01 | the POST gate block moved below the consume | text_routes.py | `test_r16` | KILLED (1/1) | test_r16_post_rule1_zero_cost |
| M02 | the sync post-resolve block moved after the fetch gather | structured_comparison_service.py | `test_r24` | KILLED (1/1) | test_r24_sync_post_resolve_refusal |
| M03 | the stream refusal yields ('complete', refusal) | structured_comparison_service.py | `test_r25` | KILLED (1/1) | test_r25_stream_post_resolve_refusal |
| M04 | the POST budget read placed after the consume | text_routes.py | `test_r20` | KILLED (1/6) | test_r20_budget_spent_never_billed[post-acct] |
| M05 | rule 1 NOT rescued by a house / note hit (the pre-ruling semantics; R-S10-4) | category_gate.py | `test_r10` | KILLED (5/5) | test_r10_house_or_note_beside_a_category_word_defers[dior lipstick vs chanel lipstick] |
| M05b | house / note beside a category word keeps evidence True (R-S10-4 override removed) | category_gate.py | `test_r10 or test_r13` | KILLED (4/6) | test_r10_house_or_note_beside_a_category_word_defers[dior lipstick vs chanel lipstick] |
| M06 | the lexicon cached once (never invalidated) | category_gate.py | `test_r04` | KILLED (1/1) | test_r04_lexicon_reloads_without_restart |
| M07 | the KB seam exception propagates | category_gate.py | `test_r53` | KILLED (1/1) | test_r53_kb_seam_fails_open |
| M08 | categories_live added to /app/version unconditionally | version_routes.py | `test_p01 or test_r54` | KILLED (10/10) | test_p01_flag_off_golden[0] |
| M09 | the post-resolve check uses the chip-aware category_used | category_gate.py | `test_r26 or test_r28 or test_r32` | KILLED (2/5) | test_r26_chip_is_not_trusted |
| M10 | A2b also called on the parser path | category_gate.py | `test_r24 or test_r27` | KILLED (3/3) | test_r24_sync_post_resolve_refusal |
| M11 | the script drops the EXPIREAT line | category_gate.py | `test_r43 or test_r44` | KILLED (3/3) | test_r43_incr_script_static |
| M12 | EXPIRE 90000 instead of EXPIREAT ARGV[1] | category_gate.py | `test_r43 or test_r44` | KILLED (3/3) | test_r43_incr_script_static |
| M13 | count > budget instead of >= | category_gate.py | `test_r21` | KILLED (1/1) | test_r21_budget_boundary |
| M14 | the device subject uses the raw fingerprint | category_gate.py | `test_r22 or test_r52` | KILLED (1/2) | test_r22_budget_subject_two_axes |
| M15 | the error_handler block not gated on the flag | error_handler.py | `test_p07` | KILLED (5/5) | test_p07_handler_flag_off_keeps_the_base_keys[0] |
| M16 | the handler copies scope for any str | error_handler.py | `test_r42` | KILLED (1/1) | test_r42_handler_sanitises |
| M17 | the trending cache key unchanged under ON | home_routes.py | `test_r50` | KILLED (6/6) | test_r50_trending_filtered[bahrain] |
| M18 | the smart-pick filter applied regardless of the flag | home_routes.py | `test_p01 or test_r49 or test_r54` | KILLED (11/11) | test_p01_flag_off_golden[0] |
| M19 | the camera CATEGORY_NOT_LIVE arm placed after exit 7 | image_routes.py | `test_r38` | KILLED (1/1) | test_r38_camera_post_resolve_never_comparison_failed |
| M20 | the camera post-vision rule-1 exit without _refund_reserved_credit | image_routes.py | `test_r37` | KILLED (1/1) | test_r37_camera_post_vision_rule1 |
| M21 | the POST gate placed after the preferences read | text_routes.py | `test_r16` | KILLED (1/1) | test_r16_post_rule1_zero_cost |
| M22 | the A2b skip without the evidence test | category_gate.py | `test_r26b` | KILLED (1/1) | test_r26b_house_evidence_skips_the_classifier |
| M23 | the Arabic article not stripped | category_gate.py | `test_r14 or test_r08` | KILLED (1/2) | test_r14_arabic_normalisation |
| M24 | masking removed | category_gate.py | `test_r11` | KILLED (1/1) | test_r11_longest_match_masking |
| M25 | the > 100 clamp removed | category_gate.py | `test_r02` | KILLED (2/17) | test_r02_budget_knob[1e3-100] |
| M26 | compare_from_text always forwards fragrance_gate=None (EQUIVALENT, C7 ruling) | structured_comparison_service.py | `test_p01 or test_p02 or test_p05` | SURVIVED (EQUIVALENT by ruling C7) (0/30) | [] |
| M27 | the _surface_comparison_failure arm removed (the generic coded arm drops category) | text_routes.py | `test_r33` | KILLED (2/2) | test_r33_r34_route_refusal_refund_once[get-usage_refund.text.get] |
| M28 | the camera budget check placed after the consume | image_routes.py | `test_r36` | KILLED (1/1) | test_r36_camera_budget_spent |
| M29 | record_refusal_async not awaited on the sync post-resolve refusal | structured_comparison_service.py | `test_r24` | KILLED (1/1) | test_r24_sync_post_resolve_refusal |
| M30 | normalise without NFKC / casefold / mark strip (lower() only) | category_gate.py | `test_r15` | KILLED (1/1) | test_r15_case_separators_nfkc_and_accents |
| M31 | rule 1 ignores fragrance_type | category_gate.py | `test_r09 or test_r11` | KILLED (1/2) | test_r09_double_product_type_proceeds |
| M32 | the camera post-vision rule-1 exit without the INCR | image_routes.py | `test_r37` | KILLED (1/1) | test_r37_camera_post_vision_rule1 |
| M33 | the INCR of one of the two keys missing | category_gate.py | `test_r44 or test_r24` | KILLED (3/3) | test_r24_sync_post_resolve_refusal |
| M34 | the orchestrator check keyed on the flag, not the kwarg | structured_comparison_service.py | `test_p05` | KILLED (2/24) | test_p05_orchestrator_order_without_the_kwarg[on-pair-sync] |
| M35 | the trending key gains the segment regardless of the flag | home_routes.py | `test_p01 or test_r50 or test_r54` | KILLED (16/16) | test_p01_flag_off_golden[0] |
| M36 | the per-product check removed (products[0] only) | category_gate.py | `test_r32` | KILLED (1/1) | test_r32_mixed_pairs_refused_per_product |
| M37 | the fragrance_type override removed | category_gate.py | `test_r31` | KILLED (2/2) | test_r31_form_hit_overrides_the_name_detection[pair0] |
| M38 | the second A2b call (the resolver's classification not reused) | category_gate.py | `test_r26c` | KILLED (1/1) | test_r26c_no_chip_reuses_the_resolver_classifier |
| M39 | an A2b 'other' refuses (the spec's L12, overruled by R-S10-3) | category_gate.py | `test_r30` | KILLED (1/1) | test_r30_classifier_outage_proceeds_uncounted |
| M40 | the admin-key bypass removed (R-S10-8) | text_routes.py | `test_p06` | KILLED (1/1) | test_p06_admin_key_path_bypasses_the_gate |
| M41 | the budget exemption removed (R-S10-7) | category_gate.py | `test_r47 or test_r48` | KILLED (2/2) | test_r47_budget_exempt_allow_list |
| M42 | the budget read checks the account axis only (R-S10-1) | category_gate.py | `test_r20 or test_r22` | KILLED (4/7) | test_r20_budget_spent_never_billed[get-dev] |

Result: 42 KILLED by an AssertionError, 1 SURVIVED = M26 (compare_from_text always forwarding fragrance_gate=None to the impl), EQUIVALENT by ruling R-S10-16 (C7: declared equivalent). M07 first came back KILLED-NON-ASSERT (the propagated RuntimeError failed R53 outside an assertion); R53 now converts an escaping seam exception into an AssertionError and the re-run is KILLED: [pyt] tag=s10mut-m07 start=2026-11-02 11:39:52 end=2026-11-02 11:39:56 elapsed=4s bound=600s status=FAIL rc=1. Spec mutants re-cast by rulings: M05 is now 'a house / note hit does NOT rescue rule 1' (R-S10-4 made the rescue correct) and M05b 'evidence kept True beside a category word'; M10 'A2b used on the parser path'; M22 'the A2b skip without the evidence test'. Added beyond C29: M39 (an A2b 'other' refuses, R-S10-3), M40 (admin bypass removed, R-S10-8), M41 (exemption removed, R-S10-7), M42 (budget read on the account axis only, R-S10-1). TSV with every [pyt] line: <scratchpad>/S81-10_red/S81-10_MUTATION_TABLE.tsv; per-mutant logs and junit under <scratchpad>/S81-10_red/mut/.

## 6. Comm set at the base = the BASE RECORD (real worktree, before the two new files existed)

- List: <scratchpad>/S81-10_red/comm_files.txt (425 test modules) + per-file reasons <scratchpad>/S81-10_red/comm_reasons.tsv (build_comm.py). Union: the module / symbol grep re-run at 6c14ac95 (277 hits) UNION the spec-time 308 (all present) UNION the review's PC1-PC7 files (test_s81_s05_request_context, test_s71_u13_compare_auth_required, test_migration_043_delete_user_cascade, test_s81_s06_router_gate_rows, test_w4_13_measurement_truth, the CLAUDE.md readers test_ci_gates / test_behavior_dimension_translation / test_s81_s04_spend_breaker / test_s81_s08b_legacy_fingerprint / test_s81_s08b_gate_rows) UNION the source-scanning class re-derived by grep (`__file__|getsource|ast.parse|rglob|glob(|listdir|scandir|"app"`, 231 hits, every hit added) UNION the 27 named data/ readers + a data/ grep (53) UNION every CLAUDE.md reader (37) UNION every SmartCompareApp-scanning backend test (22) UNION the named source-scanning pins; MINUS helpers / conftest (not test modules), the test_precommit_hook*.py files (only THREE exist: test_precommit_hook.py, _phase_b.py, _phase_b_round2.py), tests/test_secret_scan_static.py (run alone); the four NETWORK_FLAKY_EXCLUDE node ids (scripts/regression_gate_diff.py:56-65) deselected where their file is a member.
- LC-6 reuse: 107 members came from the stored S81-12 rebase-fix record (0ea73814...txt; its failures kept for member files); the 14 spec pin files from s10red-pins14; the remaining 308 ran in 13 chunks of <= 25 (bound 1200) one at a time, through ONE driver launched once (comm_driver.py, log comm/s10cb_driver.log).
- Totals of the 13 chunks: 11,963 passed, 4 failed, 31 skipped, 44 deselected, 0 errors.
- Failures: tests/test_auth_interceptor.py::test_sign_in_with_social_exception and ::test_social_login_user_insert_fails_gracefully (the message reads '[B4-BE-DIAG]... type=Exception' instead of the generic copy), tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest (KeyError 'amount') and ::TestFetchPagePriceOpenGraph::test_og_meta_extraction (0.675 == 0.9). All four reproduce ALONE at the base: [pyt] tag=s10red-basefail-rerun start=2026-11-02 11:03:43 end=2026-11-02 11:03:49 elapsed=6s bound=600s status=FAIL rc=1 ([hermeticity] 132; [netguard] blocked 4 attempt(s) from 3 node(s)): deterministic base failures of THIS box (most likely the local .env flag state, which was not read); untouched by the unit. Plus the 2 cold-tiktoken test_prompt_truth ERROR nodes carried from the S81-12 record (the known base noise).
- BASE RECORD stored: <scratchpad>/harness/base_records/6c14ac954f601902d322547de04982033aca5925/336233f08c08d9faf8c0b8a45c3e5a0902f5c8e96e57fe01f2667cde7870cba1.txt (6 node ids) + .files (the 425-file list; its sha256 IS the file name) + .pyt.log (every [pyt] line).
- tests/test_secret_scan_static.py ALONE: [pyt] tag=s10red-secretscan start=2026-11-02 11:03:57 end=2026-11-02 11:04:02 elapsed=5s bound=1200s status=OK rc=0 ; 31 passed ; [hermeticity] 31 ; [netguard] blocked 0.
- hermeticity / netguard per chunk:
```
s10cb-00: [hermeticity] sentinel checked 630 test(s) [netguard] blocked 41 attempt(s) from 13 node(s) 
s10cb-01: [hermeticity] sentinel checked 968 test(s) [netguard] blocked 18 attempt(s) from 5 node(s) 
s10cb-02: [hermeticity] sentinel checked 524 test(s) [netguard] blocked 11 attempt(s) from 5 node(s) 
s10cb-03: [hermeticity] sentinel checked 1440 test(s) [netguard] blocked 24 attempt(s) from 12 node(s) 
s10cb-04: [hermeticity] sentinel checked 450 test(s) [netguard] blocked 15 attempt(s) from 4 node(s) 
s10cb-05: [hermeticity] sentinel checked 412 test(s) [netguard] blocked 1 attempt(s) from 1 node(s) 
s10cb-06: [hermeticity] sentinel checked 3493 test(s) [netguard] blocked 152 attempt(s) from 17 node(s) 
s10cb-07: [hermeticity] sentinel checked 598 test(s) [netguard] blocked 107 attempt(s) from 14 node(s) 
s10cb-08: [hermeticity] sentinel checked 888 test(s) [netguard] blocked 24 attempt(s) from 3 node(s) 
s10cb-09: [hermeticity] sentinel checked 950 test(s) [netguard] blocked 4 attempt(s) from 2 node(s) 
s10cb-10: [hermeticity] sentinel checked 454 test(s) [netguard] blocked 62 attempt(s) from 9 node(s) 
s10cb-11: [hermeticity] sentinel checked 1035 test(s) [netguard] blocked 72 attempt(s) from 28 node(s) 
s10cb-12: [hermeticity] sentinel checked 148 test(s) [netguard] blocked 12 attempt(s) from 4 node(s) 
```
- The fourteen backend-scanning client fences: NOT run (no junction for the RED by the measurement ruling; GREEN's and the rebase's duty, by path through an orchestrator-made junction: brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout).

## 7. Every [pyt] line of this run (from the harness ledger)

```
[pyt] tag=s10red-pins14 start=2026-11-02 10:51:23 end=2026-11-02 10:52:00 elapsed=37s bound=1200s status=OK rc=0
    summary: 717 passed, 4 deselected, 13 warnings in 35.99s
    [netguard]   tests/test_streaming.py::TestNewResponseStructure::test_scores_event_has_confidence [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10cb-00 start=2026-11-02 10:52:18 end=2026-11-02 10:52:59 elapsed=41s bound=1200s status=FAIL rc=1
    summary: 2 failed, 628 passed, 3 skipped, 1 deselected, 21 warnings in 39.79s
    [netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_new_adapter_miss_falls_through [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10cb-01 start=2026-11-02 10:52:59 end=2026-11-02 10:54:06 elapsed=67s bound=1200s status=OK rc=0
    summary: 967 passed, 1 skipped, 4 deselected, 11 warnings in 65.96s (0:01:05)
    [netguard]   tests/test_converted_price_before_estimate_t1.py::test_tier2_organic_NO_retailer_is_not_phantom_local_bhd [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[pyt] tag=s10cb-02 start=2026-11-02 10:54:06 end=2026-11-02 10:54:24 elapsed=18s bound=1200s status=OK rc=0
    summary: 523 passed, 2 skipped, 3 deselected, 13 warnings in 16.82s
    [netguard]   tests/test_explicit_pair_integration_mocked.py::test_explicit_pair_category_switched_surfaces_on_response_e2e [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10cb-03 start=2026-11-02 10:54:24 end=2026-11-02 10:55:01 elapsed=37s bound=1200s status=OK rc=0
    summary: 1439 passed, 1 skipped, 12 warnings in 35.68s
    [netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_success_result_is_200 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-04 start=2026-11-02 10:55:01 end=2026-11-02 10:55:32 elapsed=31s bound=1200s status=OK rc=0
    summary: 450 passed, 5 deselected, 13 warnings in 30.13s
    [netguard]   tests/test_m13_01_slowapi_middleware.py::test_update_email_respects_account_lockout [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-05 start=2026-11-02 10:55:32 end=2026-11-02 10:55:44 elapsed=12s bound=1200s status=OK rc=0
    summary: 411 passed, 1 skipped, 4 deselected, 14 warnings in 11.17s
    [netguard]   tests/test_m13_26_image_error_envelope.py::test_internal_error_is_not_leaked_to_client [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-06 start=2026-11-02 10:55:45 end=2026-11-02 10:56:27 elapsed=42s bound=1200s status=FAIL rc=1
    summary: 2 failed, 3490 passed, 1 skipped, 2 deselected, 8 warnings in 40.67s
    [netguard]   tests/test_personalization.py::TestComparisonServicePersonalization::test_personalized_false_with_empty_dict [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10cb-07 start=2026-11-02 10:56:27 end=2026-11-02 10:56:53 elapsed=26s bound=1200s status=OK rc=0
    summary: 598 passed, 4 skipped, 7 deselected, 13 warnings in 24.90s
    [netguard]   tests/test_referral_routes.py::TestPostInviteQuiz::test_route_is_registered [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-08 start=2026-11-02 10:56:53 end=2026-11-02 10:59:01 elapsed=128s bound=1200s status=OK rc=0
    summary: 887 passed, 1 skipped, 13 warnings in 126.44s (0:02:06)
    [netguard]   tests/test_s78_all_timeout_cap_as_timeout.py::test_F15_route_end_to_end[off] [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-09 start=2026-11-02 10:59:01 end=2026-11-02 10:59:51 elapsed=50s bound=1200s status=OK rc=0
    summary: 949 passed, 1 xfailed, 13 warnings in 49.36s
    [netguard]   tests/test_shopify_cascade_wiring_l13.py::test_shopify_not_called_for_category_without_shopify_source [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10cb-10 start=2026-11-02 10:59:51 end=2026-11-02 11:00:34 elapsed=42s bound=1200s status=OK rc=0
    summary: 448 passed, 7 skipped, 12 deselected, 20 warnings in 41.19s
    [netguard]   tests/test_tier15_route_trace.py::test_no_route_recorded_when_estimated [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[pyt] tag=s10cb-11 start=2026-11-02 11:00:34 end=2026-11-02 11:01:16 elapsed=42s bound=1200s status=OK rc=0
    summary: 1026 passed, 9 skipped, 6 deselected, 12 warnings in 41.40s
    [netguard]   tests/test_w49_extraction_catch_redaction.py::test_r2c_share_payload_carries_no_raw_text [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10cb-12 start=2026-11-02 11:01:16 end=2026-11-02 11:01:28 elapsed=12s bound=1200s status=OK rc=0
    summary: 147 passed, 1 skipped, 1 warning in 11.07s
    [netguard]   tests/test_winner_prose_reconciliation.py::test_sse_flag_off_verdict_and_complete_agree_on_the_reason [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=s10red-basefail-rerun start=2026-11-02 11:03:43 end=2026-11-02 11:03:49 elapsed=6s bound=600s status=FAIL rc=1
    summary: 4 failed, 128 passed, 18 warnings in 5.45s
    [netguard]   tests/test_auth_interceptor.py::test_refresh_session_includes_user_data [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10red-secretscan start=2026-11-02 11:03:57 end=2026-11-02 11:04:02 elapsed=5s bound=1200s status=OK rc=0
    summary: 31 passed, 1 warning in 4.23s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-golden-record start=2026-11-02 11:21:55 end=2026-11-02 11:21:59 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.50s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-unit-base start=2026-11-02 11:22:12 end=2026-11-02 11:22:23 elapsed=11s bound=600s status=FAIL rc=1
    summary: 86 failed, 41 passed, 11 warnings, 13 errors in 10.03s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-unit-base2 start=2026-11-02 11:22:56 end=2026-11-02 11:23:08 elapsed=11s bound=600s status=FAIL rc=1
    summary: 99 failed, 41 passed, 11 warnings in 10.56s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-probe-ab start=2026-11-02 11:23:52 end=2026-11-02 11:23:56 elapsed=4s bound=600s status=OK rc=0
    summary: 2 passed, 11 warnings in 2.82s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-probe-p01 start=2026-11-02 11:24:06 end=2026-11-02 11:24:10 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 1 passed, 11 warnings in 3.27s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-proto-on start=2026-11-02 11:32:05 end=2026-11-02 11:32:10 elapsed=6s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.86s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-proto-off start=2026-11-02 11:32:19 end=2026-11-02 11:32:24 elapsed=5s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.58s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-proto-pins start=2026-11-02 11:32:36 end=2026-11-02 11:33:33 elapsed=56s bound=1200s status=OK rc=0
    summary: 1524 passed, 4 deselected, 313 warnings in 54.88s
    [netguard]   tests/test_security_regression.py::TestBundleBContentSafety::test_camera_vision_moderation_blocks_explicit_capture [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s10mut-m01 start=2026-11-02 11:36:31 end=2026-11-02 11:36:35 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.37s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m02 start=2026-11-02 11:36:35 end=2026-11-02 11:36:39 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.45s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m03 start=2026-11-02 11:36:39 end=2026-11-02 11:36:44 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.43s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m04 start=2026-11-02 11:36:44 end=2026-11-02 11:36:48 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 5 passed, 134 deselected, 11 warnings in 3.51s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m05 start=2026-11-02 11:36:48 end=2026-11-02 11:36:52 elapsed=4s bound=600s status=FAIL rc=1
    summary: 5 failed, 135 deselected, 11 warnings in 3.60s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m05b start=2026-11-02 11:36:52 end=2026-11-02 11:36:57 elapsed=4s bound=600s status=FAIL rc=1
    summary: 4 failed, 2 passed, 134 deselected, 11 warnings in 3.64s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m06 start=2026-11-02 11:36:57 end=2026-11-02 11:37:01 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.41s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m07 start=2026-11-02 11:37:01 end=2026-11-02 11:37:05 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.47s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m08 start=2026-11-02 11:37:05 end=2026-11-02 11:37:11 elapsed=6s bound=600s status=FAIL rc=1
    summary: 10 failed, 130 deselected, 11 warnings in 4.68s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m09 start=2026-11-02 11:37:11 end=2026-11-02 11:37:15 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 3 passed, 135 deselected, 10 warnings in 3.57s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m10 start=2026-11-02 11:37:15 end=2026-11-02 11:37:20 elapsed=4s bound=600s status=FAIL rc=1
    summary: 3 failed, 137 deselected, 10 warnings in 3.52s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m11 start=2026-11-02 11:37:20 end=2026-11-02 11:37:24 elapsed=4s bound=600s status=FAIL rc=1
    summary: 3 failed, 137 deselected, 11 warnings in 3.51s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m12 start=2026-11-02 11:37:24 end=2026-11-02 11:37:28 elapsed=4s bound=600s status=FAIL rc=1
    summary: 3 failed, 137 deselected, 11 warnings in 3.50s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m13 start=2026-11-02 11:37:28 end=2026-11-02 11:37:32 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.49s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m14 start=2026-11-02 11:37:33 end=2026-11-02 11:37:37 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 1 passed, 138 deselected, 11 warnings in 3.52s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m15 start=2026-11-02 11:37:37 end=2026-11-02 11:37:41 elapsed=4s bound=600s status=FAIL rc=1
    summary: 5 failed, 135 deselected, 10 warnings in 3.59s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m16 start=2026-11-02 11:37:41 end=2026-11-02 11:37:45 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.36s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m17 start=2026-11-02 11:37:45 end=2026-11-02 11:37:50 elapsed=4s bound=600s status=FAIL rc=1
    summary: 6 failed, 134 deselected, 11 warnings in 3.69s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m18 start=2026-11-02 11:37:50 end=2026-11-02 11:37:55 elapsed=5s bound=600s status=FAIL rc=1
    summary: 11 failed, 129 deselected, 11 warnings in 4.53s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m19 start=2026-11-02 11:37:55 end=2026-11-02 11:38:00 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.46s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m20 start=2026-11-02 11:38:00 end=2026-11-02 11:38:04 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.50s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m21 start=2026-11-02 11:38:04 end=2026-11-02 11:38:08 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.55s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m22 start=2026-11-02 11:38:08 end=2026-11-02 11:38:12 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.44s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m23 start=2026-11-02 11:38:13 end=2026-11-02 11:38:17 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 1 passed, 138 deselected, 11 warnings in 3.60s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m24 start=2026-11-02 11:38:17 end=2026-11-02 11:38:21 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.42s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m25 start=2026-11-02 11:38:21 end=2026-11-02 11:38:26 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 15 passed, 123 deselected, 11 warnings in 3.50s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m26 start=2026-11-02 11:38:26 end=2026-11-02 11:38:30 elapsed=4s bound=600s status=OK rc=0
    summary: 30 passed, 110 deselected, 11 warnings in 3.39s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m27 start=2026-11-02 11:38:30 end=2026-11-02 11:38:34 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 138 deselected, 11 warnings in 3.59s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m28 start=2026-11-02 11:38:34 end=2026-11-02 11:38:38 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.43s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m29 start=2026-11-02 11:38:38 end=2026-11-02 11:38:43 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.48s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m30 start=2026-11-02 11:38:43 end=2026-11-02 11:38:47 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.45s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m31 start=2026-11-02 11:38:47 end=2026-11-02 11:38:51 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 1 passed, 138 deselected, 11 warnings in 3.44s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m32 start=2026-11-02 11:38:51 end=2026-11-02 11:38:55 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.49s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m33 start=2026-11-02 11:38:55 end=2026-11-02 11:39:00 elapsed=4s bound=600s status=FAIL rc=1
    summary: 3 failed, 137 deselected, 10 warnings in 3.57s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m34 start=2026-11-02 11:39:00 end=2026-11-02 11:39:04 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 22 passed, 116 deselected, 10 warnings in 3.63s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m35 start=2026-11-02 11:39:04 end=2026-11-02 11:39:10 elapsed=6s bound=600s status=FAIL rc=1
    summary: 16 failed, 124 deselected, 11 warnings in 4.97s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m36 start=2026-11-02 11:39:10 end=2026-11-02 11:39:14 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.52s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m37 start=2026-11-02 11:39:14 end=2026-11-02 11:39:19 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 138 deselected, 10 warnings in 3.47s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m38 start=2026-11-02 11:39:19 end=2026-11-02 11:39:23 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.42s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m39 start=2026-11-02 11:39:23 end=2026-11-02 11:39:27 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 10 warnings in 3.45s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m40 start=2026-11-02 11:39:27 end=2026-11-02 11:39:31 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.42s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m41 start=2026-11-02 11:39:31 end=2026-11-02 11:39:36 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 138 deselected, 11 warnings in 3.56s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m42 start=2026-11-02 11:39:36 end=2026-11-02 11:39:40 elapsed=4s bound=600s status=FAIL rc=1
    summary: 4 failed, 3 passed, 133 deselected, 11 warnings in 3.66s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10mut-m07 start=2026-11-02 11:39:52 end=2026-11-02 11:39:56 elapsed=4s bound=600s status=FAIL rc=1
    summary: 1 failed, 139 deselected, 11 warnings in 3.49s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-unit-base-final start=2026-11-02 11:40:14 end=2026-11-02 11:40:25 elapsed=12s bound=600s status=FAIL rc=1
    summary: 99 failed, 41 passed, 11 warnings in 10.61s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-proto-on-final start=2026-11-02 11:40:35 end=2026-11-02 11:40:40 elapsed=6s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.72s
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10red-proto-off-final start=2026-11-02 11:40:40 end=2026-11-02 11:40:46 elapsed=6s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.68s
    [netguard] blocked 0 attempt(s) from 0 node(s)
```

## 8. Restore check

- Real worktree: the sha256 of all 3,454 tracked files after == before (snap_tracked.py: tracked_before.tsv == tracked_after.tsv, cmp identical); `git status --short` = `?? tests/fixtures/s81_s10_flag_off_golden.json` and `?? tests/test_s81_s10_fragrance_gate.py` only; HEAD 6c14ac954f601902d322547de04982033aca5925. No git write in any existing worktree.
- Scratch worktree: removed with `git -c core.longpaths=true worktree remove --force` (rc 0), absent from `git worktree list`; no .qa-mutation.lock left; no pytest process of this agent alive (tasklist: one unrelated python.exe, 15 MB, not touched).
- No package manager, no .env read, no secret printed, no network.

## 9. Deviations from the spec (each by a ruling or recorded for the gate)

- R-S10-4: R10 / R13 (and the spec's 'Dior Sauvage body cream' $0 refusal) now PROCEED with evidence False when a house or note hit sits beside a non-fragrance product-type word; rule 1 refuses only with no house and no note hit. M05 inverted; M05b added.
- R-S10-3: R27 (parser 'other' without evidence) and R30 (A2b outage) PROCEED and are never counted (spec: refused + counted). M39 added.
- R-S10-1: the budget reads the account key always and the device key additionally; either at the budget -> 429; ONE EVAL increments both (spec R22 / R40 / R41 / R42 reworded; the INCR script is a two-key loop; budget_keys replaces budget_key). M33 / M42.
- R-S10-11: the spec's R43 (drift against S81-09's 429 fields, a post-rebase row) is replaced by R46, a seam row that compares reset_window with usage_service._usage_window when it exists and with the UTC-midnight fallback otherwise; no raising=False stand-in anywhere.
- R-S10-7 / R-S10-8 / R-S10-13: new rows R47 / R48 (exemptions), P06 (admin bypass, PIN), R40 (the 1-product camera exit; it also INCRs, because the vision call was paid).
- R-S10-5 / R-S10-6: new rows R31 (hair mist) and R32 (mixed pairs); R06's form minimum includes 'hair perfume'.
- The golden holds 12 scenarios: the spec's G01-G11 + G12, the admin-key POST R-S10-8 asks the OFF golden to cover. The golden records the home cache keys and the Supabase chain arguments (C9).
- The spec's stream route row (R33, 'stream route refund once') is green at the base with a fake service (the base had_error arm already refunds an error event); kept as PIN P08. The stream refusal itself is RED at the service level (R25, kills M03).
- Spec rows R35-R39 (camera) are R36-R40 here; R43-R48 (budget mechanics) and R49-R57 (surfaces / hygiene) renumbered; R49 'OFF calls nothing' is R54.
- C7: M26 declared equivalent (no impl-kwarg row), per R-S10-16.
- P02 checks the URL path and the warmer statically (url_routes / url_extraction_service name no gate; the warmer's compare call passes no fragrance_gate) and /text/quick at run time; the URL compare is not driven at run time.
- The RED names the S81-09 seams and the helper signatures the rulings leave unnamed (section 2). The premium exemption reads usage_service._get_user_tier_info only when a budget is spent.

## 10. Open questions for the gate

- Q1 (R-S10-5): a hair-mist pair proceeds but is compared under the base category_used (haircare: the resolver's name synonym 'hair'). Should the gate also rewrite category_used to fragrances when the form override fired (a resolver behaviour change), or is it a stated limit? R31 asserts 'proceeds' only.
- Q2 (R-S10-6): 'Dior Sauvage vs iPhone 15' sent as an EXPLICIT pair has stubs other / other and house evidence, so it proceeds without A2b; it is refused on the q= path only (the parse's per-product categories). Per-product A2b for blind 'other' products with evidence costs one more call per pair. Stated limit or rule change?
- Q3: confirm the seam names and signatures pinned here for GREEN: reset_window(now) -> (day, next_reset, offset_hours); budget_exempt_async(user_id); retry_fields(now, next_reset, offset_hours); budget_keys(subject, day); the two-key REFUSAL_INCR_SCRIPT literal.
- Q4: the 1-product camera rule-1 exit (R-S10-13) increments the refusal budget (pinned in R40: the vision call was paid). Confirm.
- Q5 [NATIVE READ]: the prototype lexicon follows the spec's AR list with C4's grocery replacements (taam / mashrub / aruzz / munazzif); 'saa' (watch, also 'hour') kept and flagged; the AR house 'ajmal' (alef-jim-mim-lam) is also the common word 'most beautiful', and 'krim' (cream) is also a given name: both can create evidence / refusals on ordinary Arabic text.
- Q6: the admin-bypass signal (the prototype marks request.state in require_paid_route_user's admin branch); GREEN may pick another mechanism; P06 pins only the outcome.
- Q7: the four comm-set base failures (auth_interceptor x2, page_scraping x2) are deterministic on this box at the base (local flag state): GREEN's head run must show the same four (comm -13 empty).

## 11. NOT MEASURED / out of this RED

- The fourteen client fences (GREEN / rebase, junction). The full jest suite (LC-7: once, last round). The live Upstash multi-key EVAL (no Lua runtime; the fake emulates the script, the static row R43 pins the text). The S81-09 seams against the merged S81-09 helpers (R46 adapts; re-run at the rebase). The A2b / parse 'other' rate on brand-less Gulf fragrance names (a canary read by ruling). The URL path at run time (S81-10b, a flip precondition by R-S10-9).

Not done in this RED: no edit of any tracked file in the real worktree; no commit; the prototype and the E-rows exist only in the removed scratch worktree and the diff; the CLAUDE.md row is GREEN's.

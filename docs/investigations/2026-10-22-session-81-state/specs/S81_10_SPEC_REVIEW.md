# S81-10 FRAGRANCE-ONLY-GATE: adversarial spec review

- Reviewer: Opus 5.5 adversarial spec reviewer (workflow lane wf_4556ee65-9e3), 2026-10-29 16:5x-17:40 AST.
- Spec: C:/Users/SynAckITPC/Documents/AI/sc-s81-s10/.qa-s80/S81-10_UNIT_SPEC.md, sha256 ca9feec5c7f34cfa0d90b1c09fd48b0e34e90d934b9d1226208b99d7cebacc79 (re-hashed first: MATCH), 99,320 B, 481 lines.
- Base: e7c81956f11749b1378aa449c4ac616c82bfe6a9 (`git rev-parse HEAD` in the worktree); `git status --short` of the worktree empty before the first probe and after the last (this review is the only file written there, under the gitignored .qa-s80/).
- Read in full: s81-common.txt (twice), PLAN_S81 (standing constraints, VERIFY corrections :71-118, :106, :148-149, :174, owner decisions :190-212, the abuse analysis :198), PLAN_S80 section 0 and R-A1..R-A15, specs/S81_10_BRIEF.md, specs/RULINGS_S81_09.md, specs/S81_09_UNIT_SPEC.md 2.2-2.8 / 3 / 4.1, specs/GATE_S81_09.md, specs/S81_09_RED_REPORT.md, DEFECT_LEDGER.md, the session-81 ledger tail (newest line 16:40).
- Probes (notes folder <scratchpad>/S81-10-specreview/, <scratchpad> = the SESSION 82 orchestrator scratchpad named in s81-common.txt): (a) probe_gate.py, pure python, no app import, no network (python -I, no bytecode): the spec 2.3 normalise / scan / evaluate implemented literally over the spec 2.2 minimum EN lexicon plus the AR terms the spec names, the base _CATEGORY_SYNONYMS loop (dict extracted by ast from the worktree source), the 043 census regexes; output probe_gate_out.json. (b) a DETACHED scratch worktree at e7c81956 (<scratchpad>/s10r/wt, no node_modules, created with `git -c core.longpaths=true worktree add --detach`, removed with `git worktree remove --force`, absent from `git worktree list` afterwards) running three bounded pyt.py calls, one at a time:

```
[pyt] tag=s10rev-probe1 start=2026-10-29 17:23:40 end=2026-10-29 17:24:36 elapsed=56s bound=600s status=OK rc=0
[hermeticity] sentinel checked 5 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
  -> base: test_s05_p01_no_consumer_in_app PASS; classify_category_from_text("Chanel Coco Mademoiselle Hair Mist Dior Miss Dior Hair Mist") == "haircare", ("Sol de Janeiro Cheirosa 62 Hair & Body Mist Kayali Vanilla 28") == "haircare", ("Byredo Gypsy Water Hair Perfume Le Labo Santal 33") == "fragrances", ("Khamrah Hawas") == "other" (4 PASS)
[pyt] tag=s10rev-probe2 start=2026-10-29 17:25:04 end=2026-10-29 17:25:27 elapsed=23s bound=600s status=FAIL rc=1
[hermeticity] sentinel checked 2 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
  -> with a 14-line app/services/category_gate.py of the spec 2.6 shape (function-local `from app.utils import request_context`): FAILED tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app "AssertionError: app/services/category_gate.py" (:1338); the 043 census row PASS
[pyt] tag=s10rev-probe3 start=2026-10-29 17:26:00 end=2026-10-29 17:27:38 elapsed=98s bound=600s status=FAIL rc=1
[hermeticity] sentinel checked 1 test(s)
[netguard] blocked 1 attempt(s) from 1 node(s)   (the neutralized supabase sentinel, log_search of the failure arm: expected)
  -> POST /api/v1/text/compare with a run-time sentinel in `query`: the base route EMITTED "Text comparison request: dior zzqsentinel77 vs chanel" (text_routes.py:596; grep count 1 in probe3.log); the probe's own caplog assertion failed only because the probe imported app.main inside the caplog context and setup_logging clears the root handlers (logging_config.py:39 / :44)
```
- Box: node -e 0 0.9-3.8 s during the review (two gate-heavy lanes live: S81-12 rebase, S81-09 GREEN); the spec's 14-file base pin run (717 passed) was NOT re-run (load); every file:line below was re-read at e7c81956 with sed/grep.
- No secret, .env or personal value read or written; names only. Pure ASCII, LF.

## Verdict

APPROVE_WITH_CHANGES. The spec is unusually thorough (every major site re-measured, the chip hole of 1.4 is real and decisive, the refund composition with S81-09 is right, the camera avoids comparison_failed, the error envelope is scoped by code), but two BLOCKING issues must be ruled before the RED is cut: the refusal budget is bypassable by rotating the client-chosen X-Device-Fingerprint (B1), and the design trips a frozen S81-05 pin the spec promises stays green and unedited (B2, measured red). Four RED / mutation claims are refuted (R47 unsatisfiable, M15 / M26 not killable as tabled, the trending OFF key unpinned), and three decision rules refuse real fragrances (hair mists on the pair path, the AR coffee / milk terms, brand-less Gulf fragrance names under A2b's "If unsure, reply other"). All are fixable by rulings without a re-spec.

## Refuted claims (claim -> measured truth, file:line at e7c81956)

RF1. 4.1 "No other existing pin changes" and 4.2 "tests/test_s81_s05_request_context.py ... stay green and unedited". REFUTED, MEASURED. tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app (:1330-1412) asserts that every file under app/ or scripts/ whose text contains "request_context" is in `_ALLOWED_CTX_FILES` (:1317-1325 = the two leaf/middleware files, app/main.py, app/api/auth_routes.py, app/services/llm_router.py); its docstring says each consumer unit lists this node as its deliberate pin change (R-S05-10). The spec's budget_subject imports the leaf function-locally (2.6); probe s10rev-probe2 turns the node red with exactly "AssertionError: app/services/category_gate.py". The same node also forbids the lower-cased needles "device_key_pepper", "x-ai-consent-version", "x-compare-request-id", "header_state" anywhere in a non-leaf file (:1339-1355), so a comment in category_gate.py naming DEVICE_KEY_PEPPER fails it even after the file joins the allow-list. -> B2.

RF2. Section 6 "M15 (the error_handler block not gated on the flag) killed by P01 (G03 / G07 bodies), R49". REFUTED. G03 is INSUFFICIENT_DATA and G07 is USAGE_LIMIT (5.3); the 2.8 block fires only for `detail.get("code") == "CATEGORY_NOT_LIVE"`, so an ungated block leaves both golden bodies byte-identical. R49's raising recorders sit on category_gate's public functions; the middleware reads the flag through its own local `_fragrance_gate_keys_enabled()` (2.8, the error_handler.py:43-50 precedent), which no row records. No OFF row passes a CATEGORY_NOT_LIVE detail through http_exception_handler, so M15 survives every listed row. -> C6.

RF3. Section 6 "M26 (compare_from_text always forwards fragrance_gate=None) killed by P01 (compare kwargs), P02". REFUTED. P01 and P02 run the routes against a FAKE service (2.13 `get_comparison_service` a recording fake; 5.2), so the real compare_from_text -> _compare_from_text_impl forwarding is never executed. The impl gains `fragrance_gate=None` (3.3), so forwarding None is behaviourally equivalent; every existing impl patch accepts any kwarg (AsyncMock at tests/test_s81_s04_spend_breaker.py:1375 / :1904 / :2415; `*_args, **_kwargs` fakes at tests/test_compare_from_text_hard_cap.py:29 / :80; `_impl(self, *a, **k)` at tests/test_compare_timeout_graceful.py:87 and tests/test_cost_meter_s74.py:1366). P05 records the order and arguments of parse / A2b / profile / fetch, not the impl kwargs. M26 is EQUIVALENT unless a row asserts the impl call's kwargs. -> C7.

RF4. 4.2 "tests/test_home_routes.py (smart pick + trending bodies and cache keys)". REFUTED for the keys. tests/test_home_routes.py contains neither "home:trending" nor "home:smart_pick" (grep empty); its trending rows (:851-941) assert bodies only; no file under tests/ pins "home:trending:{region}" (grep: only test_account_deletion_u8b, test_history_routes, test_migration_043, test_sentry_channels_u8d name home:smart_pick, none home:trending); and the golden's `calls` (5.2) record no cache key. A mutant that adds the "fragrances" segment to the trending key regardless of the flag survives every row (the OFF body is unchanged). -> C9.

RF5. R47 "no captured log record (any logger) contains the sentinel, the fp, the device key or the uid". REFUTED as satisfiable. The POST route logs the raw query at INFO BEFORE the spec's gate block: text_routes.py:596 `logger.info(f"Text comparison request: {body.query}")` (MEASURED emitting the sentinel, probe s10rev-probe3); the three routes log the uid at WARNING when preferences are absent (:610, :828, :1014 `[PREFS] Authenticated user {user.get('id')} ...`); the stream logs `{q}` on a disconnect (:1203). Changing those base lines breaks the flag-OFF golden. As worded R47 can only go green vacuously (caplog blind because app.main was imported after caplog's handler: setup_logging clears root handlers, logging_config.py:39) or by weakening. -> C5.

RF6. 2.3 / R11 present "hair mist" as a fragrance FORM that proceeds. REFUTED at the decision level. On the explicit-pair and vision paths (the app's main shape, contract_freeze finding 3) the post-resolve chip-free det is `classify_category_from_text(" ".join(names))` (2.5 step 1), whose synonym table maps "hair" -> haircare (extraction_service.py:1199, loop :1333-1341). MEASURED (probe s10rev-probe1): a hair-mist pair and a "Hair & Body Mist" pair both return "haircare"; 2.5 step 3 refuses any positive non-fragrance det (evidence rescues only "other"). So "Chanel Coco Mademoiselle Hair Mist vs Dior Miss Dior Hair Mist" passes rule 1 (R11), is consumed, refused as haircare, refunded and COUNTED. -> C3.

RF7. 2.2 "a non_fragrance term is a product TYPE, never an ingredient or note word" (EN: "deliberately NOT milk, coffee, tea, honey or chocolate") vs the same paragraph's AR grocery minimum "halib / qahwa" (milk / coffee). Internal contradiction, MEASURED (probe P1): the AR query "Lattafa Khamrah Qahwa vs Lattafa Asad" (written in Arabic script) is refused at $0 as grocery although it carries two house hits (evidence True), because a house never rescues rule 1 (2.3); "Khamrah Qahwa vs Hawas" likewise. Khamrah Qahwa is a top-selling Gulf fragrance and the market is Arabic-first. R06 then FORCES an AR term in every non_fragrance list, and the spec's suggestion for grocery is the two note words. -> C4.

RF8. Q2 / R09 present the spec's double-positive rule as "the brief's Q2 default". REFUTED on the brief's own example: specs/S81_10_BRIEF.md Q2 sets the default "the fragrance positive wins and proceeds" for "Dior Sauvage body cream"; the spec refuses exactly that query at $0 (Q2 text, R10). The departure is defensible (houses overlap fashion / makeup brands) but it is a deviation that needs a ruling, and it costs measured false $0 refusals of real fragrances: probe P1 refuses "Jo Malone Peony & Blush Suede vs ..." (makeup: "blush") and "Frederic Malle Lipstick Rose vs ..." (makeup: "lipstick"). L11 names the class but not the scale. -> C13 / Q4.

RF9. L18 "The post-resolve check runs inside the hard-cap wait_for". TRUE for the sync path only. On the stream the parse (:4978), the resolve (:5003-5006) and the new check run with no cap; the stream's wait_for wraps only the fetch gather (:5052-5060). An A2b classify on the stream path is bounded only by its own classify timeout (extraction_service.py:1395). -> C16.

RF10. 2.6 "two literal f-strings" next to 2.1's constants KEY_PREFIX_DEV / KEY_PREFIX_ACCT. A trap, MEASURED with the census regexes (probe P3): `f"refusal:daily:acct:{user_id}:{day}"` normalises to "refusal:daily:acct:{user_id}:{*}" (E1 matches), but `f"{KEY_PREFIX_ACCT}{user_id}:{day}"` and `f"refusal:daily:acct:{subject[1]}:{day}"` are SKIPPED by the census (first part not a constant / no user_id expression, tests/test_migration_043_delete_user_cascade.py:1309-1312), which leaves the E1 KEPT row naming no writer: test_every_per_user_cache_key_is_purged_or_kept red at :1342-1343. -> C15.

RF11. 1.5 line citations are off by one throughout: STATUS_CODE_MAP :24-35 (spec :25-36); _URL_V2_PASSTHROUGH_CODES :40 (:41); _url_mode_v2_keys_enabled :43-50 (:44-51); _is_structured_detail :90-107 (:91-108); _detail_retry_after :110-126 (:111-127); http_exception_handler :129-168 (:130-168); the B4 block :155-163 (:155-162); the W1-9 retry block :164-167 (:163-167), so the 2.8 block goes between :163 and :164. Also PRODUCT_PARSER_PROMPT enum :114 (spec :113), type lists :127-136 (:126-135), the brand rule :137 (:136); _CANONICAL_CATEGORIES :1161 (spec ":143 / :~1163"); the spec's ":4354" is `product_categories = ...`, the partial-ctx update starts at :4355-4356. Every other cited line re-measured within one line (text_routes, image_routes, the orchestrator, request_context :73/:74/:164/:190/:218/:298, llm_router :212-213/:345-357/:426-437, llm_spend_breaker :132/:134/:337-351/:971-977, home_routes, version_routes, the 043 census, trending_curated: one Fragrances entry per region in all six). -> C17.

RF12. 7.6 "The full jest suite is not run (no client file; LC-7 ...)". REFUTED by the precedent: the orchestrator applied LC-7 to the backend unit S81-09 ("the full jest suite deferred to the last round, LC-7", ledger 16:40 and GATE_S81_09); the suite runs once in the last round before the PR. -> C18.

RF13. 7.5 "UNION the CLAUDE.md readers tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py". INCOMPLETE: tests/test_s81_s04_spend_breaker.py:1657, tests/test_s81_s08b_legacy_fingerprint.py:74 / :801 and tests/test_s81_s08b_gate_rows.py:282 (RB8-5a :324-334 pins that the next "## " heading after the S81-08b row is "## Tests") read CLAUDE.md by path. -> C19.

## Blocking issues

B1. The refusal budget is bypassable by rotating X-Device-Fingerprint (2.6, R22). The subject is the device key WHEN the header is bound, ELSE the account. The header is client-chosen: request_context accepts any value matching ^[a-f0-9]{64}$ (parse_device_fingerprint, request_context.py:132) and device_key is a deterministic HMAC of it (:298-312). A scripted account that sends a fresh random fingerprint per request gets a fresh, empty budget every time, so the per-account budget never applies and the refunded-parse loop of PLAN_S81 :198 (the reason the budget exists, and the spec's own Q-E argument) stays unbounded except by the 10/min limiter, which is one shared bucket behind Railway's proxy (PLAN :198, CLAUDE.md #299). S81-09 avoids exactly this by keeping BOTH axes (account-daily AND device-daily keys in one EVAL, specs/S81_09_UNIT_SPEC.md 2.3 / 2.5). Required: count and check BOTH keys when a device key exists (account always, device additionally): the pre-consume read refuses when either count >= budget (one MGET or two GETs through the same dispatch), and the refusal INCRs both keys in ONE EVAL (2 KEYS, the same EXPIREAT). R22 / R40 / R41 / R42 and the 429 math (retry_after / resets_at unchanged: same reset instant) are re-worded accordingly; E1 is unchanged (the account key keeps its literal f-string).

B2. The S81-05 consumer pin (RF1) is not an E-row, and 4.2 promises it unedited. Required: an E-row in the S81-06 E9 form (tests/test_s81_s05_request_context.py:1317-1325 / :1359-1378 precedent): `_ALLOWED_CTX_FILES` gains "app/services/category_gate.py"; a pinned import shape (exactly one `from app.utils import request_context as _request_context`, function-local) and attribute uses limited to {device_fingerprint, device_key}; category_gate.py must not contain the strings DEVICE_KEY_PEPPER / header_state / x-ai-consent-version / x-compare-request-id (comments included) or the needle checks need widening too. Also listed as a stay-green pin: test_s05_p07_route_header_reads_untouched (:1590-1596: the needle `valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` stays count 1 in image_routes.py and text_routes.py, so neither gate reads the header itself). Cross-unit: specs/S81_09_UNIT_SPEC.md :279 makes usage_service.py import the same leaf (`from app.utils import request_context as _request_context`) and S81-09's E-rows (4.1: E1 r25b, E2 r25a) do not list p01; its RED E-row probe ran only ST1 r25 + the 043 census (S81_09_RED_REPORT.md :27), so the S81-09 GREEN now running will meet the same red node; S81-10's E-row is then a known rebase hunk on the same set literal.

## Corrections (each a ruling candidate; MAJOR unless marked minor)

C1. (B1) Two-axis budget as stated in B1; L8 / L13 re-worded (a device with several accounts is bounded per device AND per account).

C2. (B2) The p01 E-row and the p07 stay-green line as stated in B2.

C3. (RF6) The post-resolve decision must not refuse a pair whose query carries a concentration / form hit (fragrance_type True) on the deterministic det of the explicit / vision path: either `fragrance_type` -> det "fragrances" before step 1, or a positive det from classify_category_from_text is overridden by fragrance_type (the parser path keeps the LLM's word). New rows: the hair-mist pair and a "Hair & Body Mist" pair on the pair shape proceed with fetch called; "hair perfume" already proceeds (det fragrances). Mutant: the override removed.

C4. (RF7) Replace the AR grocery suggestions with product-type words (for example the Arabic for food, beverage, rice, detergent: ta'am, mashrub, aruzz, munazzif), and add to R06: no non_fragrance term (EN or AR, after normalise) equals a fragrance note term or a member of a deny set {coffee, milk, tea, honey, chocolate} in both scripts (qahwa, halib, shay, asal, shukulata). Flag the AR fashion term "saa" (watch) for the native read: the same word means "hour" and Arabic perfume queries quote longevity in hours ("12 hours"); without a form word in the query it would refuse at $0.

C5. (RF5) Rewrite R47: assert on (a) every record of the `app.services.category_gate` logger and (b) every record whose message starts with "[CATEGORY-GATE]", from any logger: none contains the sentinel, the fp, the device key or the uid, and each matches the 2.10 grammar; the base route lines are pinned unchanged by the golden. Harness note: import app.main BEFORE caplog installs its handler (setup_logging clears root handlers, logging_config.py:39).

C6. (RF2) Add a handler row under the five OFF spellings: HTTPException(400, refusal_detail("electronics")) and HTTPException(429, budget_detail(...)) through http_exception_handler -> the body is exactly the base keys {success, error, code, request_id} (+ retry_after_seconds / Retry-After only from the W1-9 block on the 429) with no category / categories_live / scope / resets_at. Kills M15.

C7. (RF3) Either add a row that patches StructuredComparisonService._compare_from_text_impl with an AsyncMock and asserts `"fragrance_gate" not in impl.await_args.kwargs` when the caller passes none and `impl.await_args.kwargs["fragrance_gate"] is decision` when passed (the output_lang precedent at structured_comparison_service.py:4079), or declare M26 equivalent in the mutation table. Same for the streaming entry.

C8. (minor) M24 (masking removed) is not observable through evaluate(): for every term the spec lists, the masked sub-term is in the same category or the outcome is already decided by fragrance_type (probe P1: "chanel no 5 hair mist ..." proceeds either way). R11 and R13 must assert scan(...).non_fragrance exactly ([] for the hair-mist query; [("grocery", "ice cream"), ("grocery", "ice cream")] for R13).

C9. (RF4) The golden's per-scenario `calls` record the home cache GET / SET keys (and the Supabase query args of G10); add mutant M35 "trending key gains the segment regardless of the flag" killed by P01 G11.

C10. P05 must use NON-fragrance scenarios (q= with a parse fake returning electronics; the pair shape with blind electronics names and no chip) so a mutant that keys the orchestrator's check on `fragrance_only_gate_enabled()` instead of `fragrance_gate is not None` refuses under ON-without-kwarg and is killed; add that mutant (M34).

C11. Duplicate A2b. When the request has no chip (selected_category None or canonicalising to "other"), the base resolver already ran A2b on the same names (structured_comparison_service.py:494-496), so step 2 calls it a SECOND time on the same pair (two classify calls, up to 2 x the classify timeout, on build-3 traffic without a chip). Reuse the resolver's category_used as det in that branch (it is chip-free there); row: A2b call count exactly 1 for a blind no-chip pair.

C12. Mixed pairs. 2.5 step 1 reads products[0] only (L4). product_categories is computed right at the insertion point (:4354 sync, :5009 stream) and the explicit / vision stubs are per product (explicit :4294-4309, vision :4278-4293): refuse when ANY product's chip-free category is a positive non-fragrance. "perfume vs laptop" and "Dior Sauvage vs iPhone 15" otherwise run as billed fragrance compares (probe-reasoned: classify_category_from_text("perfume laptop") returns fragrances, the longer synonym wins). Rows for both; L4 shrinks to the q= parse's own per-product categories.

C13. (RF8; ruling Q4) Recommended: a house or note hit together with a non-fragrance product-type word does NOT refuse at $0; instead the decision carries evidence False (so the post-resolve classifier decides). Effect: "Jo Malone Peony & Blush Suede" and "Frederic Malle Lipstick Rose" proceed after one A2b / parse; "gucci bag vs prada bag" is still refused (post-consume, refunded, counted). Alternative: keep the spec default and list the measured false $0 refusals in L11.

C14. (minor) 2.6 budget read: a nil reply (missing key: the normal first request of every day) is count 0, silent; only a raising GET or a non-nil non-numeric reply logs the fail-open WARNING. As worded ("a non-int reply -> None + ONE WARNING") the gate would WARN on most compares.

C15. (RF10, minor) The two key f-strings spell their prefixes literally and interpolate a variable literally named `user_id` (account) and `device_key` (device); KEY_PREFIX_* are for readers and tests only.

C16. (RF9, minor) L18 reworded: the sync check runs inside the hard-cap wait_for; the stream's parse, resolve and check run outside it (bounded by the parse and classify timeouts).

C17. (RF11, minor) Fix the 1.5 / 1.4 line citations; GREEN anchors on text, not numbers.

C18. (RF12, minor) 7.6: the full jest suite once, in the last round before the PR (LC-7 as applied to S81-09).

C19. (RF13, minor) 7.5: name the four CLAUDE.md readers above; the S81-10 row is one column-0 "**SESSION 81 flag (S81-10 ..." paragraph after the S81-15 block (and after S81-09's row once merged), adding no "## " heading (RB8-5a).

C20. (minor) Harness: DEVICE_KEY_PEPPER is in tests/_env_safety.CREDENTIALS_UNSET (:136); every row that needs it imports app.main FIRST (autouse) and then monkeypatch.setenv (the S81-09 RED form, specs/S81_09_UNIT_SPEC.md :327).

C21. (minor) T23: tests/test_s71_u13_compare_auth_required.py::test_T23_openapi_unchanged (:987) pins the full operation JSON of the ten routes, including the docstring-derived description: GREEN edits no docstring of POST / GET /text/compare, the stream or /image/identify (else it is an E-row).

C22. (minor) Camera placement: compute `subject` under `_gate_on` before the metering block (:323), independent of ENABLE_PAID_ROUTE_METERING, so step 2's record_refusal never reads an unset name with metering OFF; run step 2 right after `query` is built (:494-496), before the ENABLE_VISION_IDENTITY_V2 preferences read (:509-515, a Supabase call a rule-1 refusal does not need).

C23. (minor) Normalisation keeps Latin accents: NFKC + casefold leaves U+00E8 in "Hermes" typed with its accent, so it misses the house "hermes" (same for Lancome / Chloe written with accents) and pays an A2b call. Strip combining marks for Latin (NFKD, drop Mn, NFKC) before matching, both for terms and text; R15 gains an accented house row.

C24. (minor) GateDecision.subject carries the device key or the uid; declare it `field(repr=False)` so a repr in an exception frame, a log or a recorder never prints it (R47 / the S81-05 "never logged" rule).

C25. (minor) error_handler: validate categories_live members against the canonical tuple as `category` is (R39 row: ["weapons"] dropped).

C26. A2b outage (L12): classify_category_llm returns "other" on any error (extraction_service.py:1399-1403), so an OpenAI / Anthropic outage both refuses blind no-evidence fragrance pairs with the CATEGORY_NOT_LIVE copy ("MYEZ compares fragrances for now", to a fragrance user) and INCRs their budget (10 such taps lock the subject out of every compare until the reset, L13). Rule at least: no INCR when the det came from A2b "other" (record only rule-1-after-vision and positive non-fragrance refusals), and state the copy mismatch; a distinct non-delivery for classifier errors needs an error signal out of classify_category_llm (an extraction_service edit: comm set grows).

C27. (minor) Stated limits to add: (a) the pre-consume budget GET is one more Upstash round trip on EVERY gated compare, inline on the event loop while ENABLE_ASYNC_REDIS_OFFLOAD is OFF and with no timeout (S81-04 bounds its own read at 0.5 s, llm_spend_breaker.py:127); (b) check-then-INCR is not atomic: N concurrent requests from one subject at count budget-1 all pass the read, so the counter can overshoot by the concurrent burst (bounded by the 10/min limiter); (c) the smart-pick filter trusts the stored chip-aware full_response.category (CR9).

C28. History (Q6): PLAN_S81 :106 and :149 (binding unit text) say "Smart pick, trending and History filtered to fragrances"; the spec's KEEP WHOLE default is a deviation that needs an explicit ruling, not a default.

C29. Mutation table additions: M31 rule 1 ignores fragrance_type (killed by R09); M32 the camera post-vision rule-1 exit without the INCR (R35); M33 the INCR of one of the two keys missing (after B1, R41); M34 (C10); M35 (C9); M36 the per-product check removed (C12 rows); M37 the fragrance_type override removed (C3 rows); M38 the second A2b call (C11 row).

C30. RED sequencing: S81-09 GREEN is running; cut the S81-10 RED on the S81-09 merge sha (then `usage_service._usage_window` exists, R43 is an ordinary RED row, no `raising=False` stand-ins, and the golden is recorded on the sha GREEN builds on).

## Contract risks

CR1. (MAJOR) Brand-less fragrance pairs are refused on the app's main path. With Q-A (chip-free), a blind pair without a house / note / form hit goes to A2b, whose prompt ends "If unsure, reply other" (extraction_service.py:1360-1361); "other" without evidence is refused (2.5 step 3). Gulf users routinely type the product name without the house ("Khamrah", "Hawas", "Asad", "Yara", "Club de Nuit", "9pm"), and several are ordinary words ("Asad" = lion, "Yara" = a name). On the q= path the parse's own "other" is refused with no second opinion (no A2b, 2.5 step 2). The false-refusal rate is NOT MEASURED. Recommended ruling (Q3): refuse only a rule-1 word or a POSITIVE non-fragrance detection; when the request carries the fragrances chip, an "other" det (parse or A2b) proceeds (billed, so not an abuse lever; the A2b call still runs for blind no-evidence pairs and catches "iPhone 15 vs Galaxy S24" as electronics). Or keep chip-free and make a measured A2b / parse "other" rate on N brand-less fragrance pairs (the S81-07 fragrance gold set) a dated flip precondition.

CR2. The window between the S81-11 OTA (selected_category=fragrances on every request, spec 1.4) and the flip: with the flag OFF the resolver returns the chip for blind pairs (structured_comparison_service.py:491-493), so "iPhone 15 vs Galaxy S24" runs as a FRAGRANCE compare (fragrance schema, dimensions, verdict personality) for every S81-11 user until the flip. Keep the window short or have S81-11 send the chip only when /app/version carries categories_live.

CR3. App Review / premium accounts are not exempt from the refusal budget (2.6); a reviewer who tries ten other categories is then locked out of EVERY compare, fragrances included, until the reset (L13), with "The daily limit for other searches is reached." S81-09 exempts the review accounts and DEVICE_QUOTA_EXEMPT_USER_IDS (R-S09-4). Ask whether the same allow-list exempts the refusal budget.

CR4. The admin-key smoke / eval harness: require_paid_route_user lets an X-Admin-Key caller run as anonymous (text_routes.py:312-334), so it has no budget subject but is still refused by rules 1 and 3; smoke20 and the eval sets that carry non-fragrance pairs read as failures after the flip (the Anthropic flip gate, PLAN_S81 :79, uses smoke20). Decide a synthetic / admin bypass or fragrance-only sets before the flip.

CR5. The URL path stays ungated (L2) while owner decision 3 names "a typed query, link or photo": flipping S81-10 alone leaves link mode all-category and outside the refusal budget. Make S81-10b a flip precondition or record the owner's acceptance.

CR6. Build-3 stragglers after the flip render CATEGORY_NOT_LIVE as "Sharper match coming up - try with brand or model." (errorCopy.ts friendlyErrorKey default :90-91; en.json:118), which invites retries; each retry of a blind pair is a consume + parse / A2b + refund + INCR. CONTENT_UNAVAILABLE at 200 would render "We don't compare this category" on build 3; the spec's Q1 rejection (analytics pollution) could be met with a distinct `layer` value. The flip precondition (two-launch propagation) bounds but does not remove stragglers.

CR7. S81-11 must render (a) the camera action "error" bodies with code CATEGORY_NOT_LIVE and the budget variant (retry_after_seconds, resets_at), and (b) an SSE `error` event with this code WITHOUT the REST fallback (streamComparison's runRestCompare, api.ts:677-732, would re-run the compare: a second consume / parse / refund / INCR). S81-08's client keys the paywall on code USAGE_LIMIT only (6c14ac95 usageService.ts:83-92), so the scope "refusal_daily" 429 does not open the Paywall: MEASURED read-only with git show.

CR8. A classifier outage (C26) shows the category copy to fragrance users and burns budgets.

CR9. Smart pick's filter reads the stored chip-aware category: blind non-fragrance compares stored as "fragrances" during the CR2 window pass it; delivered "other"-with-evidence compares by build-3 users without a chip are stored as the A2b word and are filtered out.

CR10. The 1-product camera exit (image_routes.py:476-489) still answers "Identified: <product>. Take another photo or type a product to compare with." for a non-fragrance product under the flag (refunded, so no billing risk), inviting a compare that will be refused.

## Pin collisions not in 4.1

PC1. tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app (:1330-1412): MEASURED red (RF1, B2).
PC2. tests/test_s81_s05_request_context.py::test_s05_p07_route_header_reads_untouched (:1590-1596): stays green only if neither route reads the header itself (B2).
PC3. tests/test_s71_u13_compare_auth_required.py::test_T23_openapi_unchanged (:987): no route docstring edit (C21).
PC4. tests/test_migration_043_delete_user_cascade.py C8 census (:1280-1345): E1 as stated plus the prefix-constant trap (RF10, C15).
PC5. tests/test_s81_s06_router_gate_rows.py (:844-857): the sixteen G13 site keys, each routed once; the gate must reuse classify_category_llm and add no `_llm_router.route("classify", ...)` call.
PC6. tests/test_w4_13_measurement_truth.py::test_every_log_search_call_site_passes_duration_ms (:814-821): any new log_search call (C27 / L10 if the camera exits gain a row) passes duration_ms.
PC7. The CLAUDE.md row readers (RF13, C19), including RB8-5a's "next ## heading is ## Tests".
PC8. Checked, no collision: FY25 (tests/test_s75_fanout_identity.py, UNIT_ENV :60-70) is service-level without the route-passed kwarg (B1 / S81-03 / S81-04 / S81-06 added their names because their flags act at service level; S81-10's does not); the W4-13 ledger (tests/test_w4_13_flag_off_ledger.py:111-135) is route-level but deletes only its own names, so it holds while ENABLE_FRAGRANCE_ONLY_GATE is unset (never set it in a .env); w4_11 prompt digests (no prompt change); test_retro_w2_1 patches image_routes.StructuredComparisonService (:357) and the camera kwarg is passed only ON; copy fences (REFUSAL_MESSAGE / BUDGET_MESSAGE carry no forbidden word); no data/ glob walker exists in tests/ (grep), so the new data file trips none.

## Questions for the orchestrator

1. (B1) Rule the two-axis budget: account always, device additionally, one EVAL INCR of both keys, refuse when either count reaches REFUSAL_DAILY_BUDGET.
2. (B2) Rule the p01 E-row in the S81-06 E9 form (allow-list entry, import shape, attribute set {device_fingerprint, device_key}, no needle strings in category_gate.py), and tell the running S81-09 GREEN lane that its usage_service import of the leaf (its spec :279) trips the same node (its E-rows list only r25a / r25b).
3. (CR1) Chip semantics: refuse only rule-1 words and POSITIVE non-fragrance detections, letting an "other" det proceed when the fragrances chip is present (recommended), or keep the spec's chip-free "other" refusal with a measured A2b / parse "other" rate on brand-less fragrance pairs as a flip precondition.
4. (RF8 / C13) Q2: house or note evidence plus a non-fragrance product-type word -> defer to the classifier (recommended; fixes the measured "Peony & Blush Suede" / "Lipstick Rose" $0 refusals) or the spec's $0 refusal.
5. (C3) The fragrance_type override of a deterministic det on the explicit / vision path (hair mists).
6. (C12) The per-product refusal of mixed pairs.
7. (C26) A2b-failure refusals: no INCR; and whether a classifier error should become a distinct non-delivery.
8. (CR3) Do the S81-09 exemptions (premium, DEVICE_QUOTA_EXEMPT_USER_IDS) also exempt the refusal budget?
9. (CR4) An admin-key / synthetic bypass of the gate for the smoke and eval harness, or fragrance-only sets before the flip?
10. (CR5) S81-10b (URL) as a flip precondition, or a dated owner acceptance of link mode staying open?
11. (C28) History: KEEP WHOLE overrides binding plan text; rule it explicitly.
12. (C30) Cut the RED on the S81-09 merge sha?
13. (CR2) Should S81-11 send selected_category=fragrances only when categories_live is present, to close the pre-flip window?
14. (CR10) Should the 1-product camera exit answer CATEGORY_NOT_LIVE for a rule-1 product under the flag?
15. (CR6) Keep code CATEGORY_NOT_LIVE (spec Q1) or CONTENT_UNAVAILABLE with a distinct layer for build-3 stragglers?

## Not done in this review

No code, test, fixture or lexicon written in the worktree; no git write except the detached scratch worktree (created and removed, verified); no package-manager command; no .env or secret read; the spec's 14-file base pin run (717 passed) and the comm-set base record NOT re-run (box load, two gate-heavy lanes); the A2b / parse "other" rate on brand-less fragrance names NOT MEASURED (needs live LLM calls: owner-approved measurement only); the Arabic terms are transliterated here and need the owner's native read.

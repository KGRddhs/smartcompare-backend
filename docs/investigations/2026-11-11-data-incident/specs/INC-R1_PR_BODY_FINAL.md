## INC-R1 RESOLVE-OR-ASK: resolve each typed fragrance name of an explicit pair, or ask (dark: `ENABLE_PRODUCT_RESOLVER`)

Merged, NOT yet proven: nothing here says a production problem is fixed. The unit is "merged, NOT yet proven" until the owner's phone shows the checks of PROOF ON THE PHONE below, after the relay's own flip window (H6). A green suite and a hermetic measurement are necessary and are not that proof.

Base `6104eebd7020cc009589b87afb4a73eb8aa5434d` (origin/main, the merge of #407 INC-I1). Branch `fix/inc-r1-resolve-or-ask`, one commit `1860fbe7f76dbd73470b8164be411d251c70d140`. Class FOCUS (R1-R30): two adversaries. Spec `.qa-s80/INC-R1_UNIT_SPEC.md` (0676c198...) as amended by the BLOCK review's corrections, RULINGS_INC_R1 (R1-R1..R1-R31) and GATE_INC_R1 (GC-1..GC-17, binding).

### What the flag does

`ENABLE_PRODUCT_RESOLVER` (default OFF, the house idiom, read per call as the FIRST statement of each predicate that uses it). ON, the two typed names of an explicit pair (POST / GET `/api/v1/text/compare`, GET `/compare/stream`; never q=, the camera, links, /quick or the warmer) are resolved ONCE per comparison, after Step 1 builds the two product dicts and before `_resolve_pair_category`, by the NEW `app/services/product_resolver.py`:

1. a deterministic arm (no network) over the `data/fragrance_lexicon.json` houses, `price_service.FRAGRANCE_BRAND_KEYWORDS` / `_BRAND_ALIAS_GROUPS` and the NEW `data/fragrance_lines.json` (12 seed lines, public product names only): token-wise optimal-string-alignment (1 edit up to 5 letters, 2 above; digits exact; flankers exact), size spans removed with the `extract_size_ml_any` patterns (R1-R5), the qualifier words ignored (R1-R4), a single-token fuzzy line with no typed house high only with a pair fragrance context (R1-R8), a typed concentration the line does not sell medium (R1-R11; a concentration-word flanker such as "Parfum" of Stronger With You counts as sold, GC-5 Q2);
2. only when a side is unresolved AND `llm_router.decide("text") == "anthropic"` for the request (R1-R6) AND neither a non-fragrance chip nor two non-fragrance category words skip it (R1-R3 (d)): at most ONE call on the NEW router site `resolve` (`SiteSpec("text", 384, None, True)`: no `output_config.format`, the JSON-only line, R1-R7; `route()` byte-equal, R1-R2), dispatched exactly like `disambiguate`, bounded by `PRODUCT_RESOLVER_TIMEOUT_SECONDS` (2.5), cached per process (parsed answers only, 24 h, 2,000 pairs); each side accepted only through the deterministic guard (fragrance, high confidence, a listed or typed house, the line within the edit rule of the typed text; Arabic waives the last).

Outcomes: `resolved` (both dicts rewritten: brand = house, name = line, variant = concentration + typed size, search_query "<brand> <line> <concentration>", category fragrances; the pair category takes the parser path, no classify call); `ask` (a fragrance-intended pair with an unresolved side and a usable Claude answer: the coded 400 INSUFFICIENT_DATA + additive `reason` placeholder_identity + `candidates`, BEFORE the pair category, the S81-10 gate, the profile / KB tasks and any fetch; the stream twin is an `error` event); `partial` / `passthrough` (no usable answer, or neither side a fragrance: no refusal, a resolved side still rewritten). `PRODUCT_RESOLVER_ASK=0` (or false / no / off) = resolve-only. One INFO `[RESOLVE] a=.. b=.. outcome=.. ms=.. cached=0|1 brand_a=.. line_a=.. brand_b=.. line_b=..` line per comparison (resolved names only).

The ask leaves the routes through twins of the S81-20 exits (R1-R9, R1-R10, GC-5 Q6): `text_routes._resolver_ask_exit` (POST / GET) and `_resolver_stream_settle` (stream): the S81-10 refusal budget read (ENABLE_FRAGRANCE_ONLY_GATE ON only), ONE refund WITH the consume's keys (label `usage_refund.<route>.resolver:placeholder_identity`; a spent budget keeps the credit), the count once, ONE failure row whose error_message is the ask sentence, the 400 through `_surface_comparison_failure`; never a history row or a lifetime count (R-A3). `reason` + `candidates` reach the sync 400 at both gates only under the flag (R1-R18); `http_exception_handler` reads the flag only after the refusal marker matches (RC-2).

Flag OFF: byte-identical: P01 (28 nodes: every OFF value x rest / stream x the owner pair / golden pair 4 with the FULL configuration, the base Step-1 literals, the base parser_path, no create, no knob read, no lines-file open, no [RESOLVE] record, the FY digest of the base) and P02 (the nine FY25 digests) are green at the base and the head.

### Footprint (one commit; GC-9 / GC-17)

- `.github/black-clean-paths.txt` (+3 / -0)
- `CLAUDE.md` (+7 / -1)
- `app/api/text_routes.py` (+89 / -0)
- `app/middleware/error_handler.py` (+59 / -0)
- `app/services/llm_router.py` (+4 / -2)
- `app/services/product_resolver.py` (+1431 / -0)
- `app/services/structured_comparison_service.py` (+63 / -2)
- `data/fragrance_lines.json` (+18 / -0)
- `tests/test_inc_r1_resolver.py` (+1907 / -0)
- `tests/test_inc_r1_seam.py` (+1440 / -0)
- `tests/test_s75_fanout_identity.py` (+3 / -1)
- `tests/test_s81_kb_schema.py` (+4 / -2)
- `tests/test_s81_s06_anthropic_router.py` (+4 / -1)
- `tests/test_s81_s06_router_gate_rows.py` (+8 / -5)
- `tests/test_s81_s07_meas_harness.py` (+2 / -1)
- `tests/test_s81_s07c_role_fix.py` (+2 / -1)
- `tests/test_s81_s22b_self_critique_retire.py` (+1 / -0)

### Defects -> RED nodes (frozen RED files, sha256 re-checked at the start and the end)

| Defect (S95-FIX diagnosis) | RED / PIN nodes |
|---|---|
| D1 RC1: the explicit pair is never resolved | seam R03 [rest, stream], R04 [rest, stream] x [owner, second_skin], R13 [rest, stream], R21 [rest, stream]; resolver R07, R08 (10), R09 (9), R10b (8), R36 |
| D1 RC2: every search sends the bare typed string | seam R03 (searches == "<search_query> specifications reviews price"), R14 |
| D1 RC3: brand-keyed price gates stay off (empty brand) | seam R03 / R13 (brand non-empty), resolver R36 (search_query carries the house) |
| D1 RC6: no path asks the user | seam R05, R06, R07, R08, R09, R10 red (2), R11 red (2), R19 (2), R20 (3); resolver R22 (21), R37 |
| D2 RC0: identity drives the picture / specs queries | seam R03 (the canonical query string; picture relevance stays INC-I1's) |
| D4 section 0.1: the empty brand blocks every KB match | seam R15 [red_flag_on] (kb_product_id minted) / [pin_flag_off] |
| ADV R-7: no catalog; Claude only for consent >= 3 | resolver R05, R17, R26, R26b, R28 (3); seam R12, R12b, R13b |

### Deliberate pin changes (E-rows, GC-4; each the smallest edit)

| Id | File | Change |
|---|---|---|
| E1 | tests/test_s81_s06_anthropic_router.py | SITE_ROLES += resolve: text, SITE_CAPS += resolve: 384; R02 docstring "the 17 keys" |
| E2 | tests/test_s81_s06_router_gate_rows.py (black-clean) | G13_SITE_KEYS += "resolve"; `len == 15` -> 16; the docstring and the stale :785 comment |
| E3 | tests/test_s81_s07_meas_harness.py | test_p02 `want` += "resolve": ("text", 384) |
| E4 | tests/test_s81_s07c_role_fix.py | OTHER_SITES_BASE += "resolve": ("text", 384, True, None) (no schema, R1-R7; t06's tag map needs no entry) |
| E5 | tests/test_s75_fanout_identity.py | UNIT_ENV += ENABLE_PRODUCT_RESOLVER, PRODUCT_RESOLVER_TIMEOUT_SECONDS, PRODUCT_RESOLVER_ASK (the nine digests unchanged) |
| E5b | tests/test_s81_kb_schema.py | IDENTITY_NODES re-pins the LF sha256 of tests/test_s75_fanout_identity.py (93c59246... -> e8c4bccf...) + one docstring sentence: E5 moves that file's bytes; the S81-06 E11 / S81-20 E8 precedent for a UNIT_ENV edit (not in GC-4's list: found by the HEAD comm pass, see Gates) |
| E6 | tests/test_s81_s22b_self_critique_retire.py | SITES_BASE += "resolve": ["text", 384, True, True] |

`llm_router.route` is byte-equal: MON1's route digest (tests/test_inc_mon1_credential_health.py G01) stays green unedited.

### Gates (every pytest through harness/gate.py, one at a time)

RED files, flag exported ON / nothing exported:

    246 passed, 15 warnings in 10.45s
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    246 passed, 15 warnings in 10.33s
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)

Identity pins (spec 4.2) and the E-row files:

    1 failed, 859 passed, 2 deselected, 17 warnings in 92.28s (0:01:32)
    [hermeticity] sentinel checked 860 test(s)
    [netguard] blocked 73 attempt(s) from 23 node(s)
    981 passed, 2 skipped, 1 xfailed, 137 warnings, 2 errors in 43.72s
    [hermeticity] sentinel checked 984 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    1 failed, 1098 passed, 17 warnings in 24.78s
    [hermeticity] sentinel checked 1099 test(s)
    [netguard] blocked 48 attempt(s) from 33 node(s)
    1 failed, 1176 passed, 17 warnings in 72.81s (0:01:12)
    [hermeticity] sentinel checked 1177 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)

Static (spec 7.1 G1; the one non-ASCII added line is the pre-existing `**Feature Flags:**` line, whose inserted words are ASCII):

    py_compile 14 files rc=0
    ruff E9,F63,F7,F82 14 files rc=0: All checks passed!
    black 26.5.1 --check --diff 5 allowlisted files rc=0: 5 files would be left unchanged.
    data/fragrance_lines.json json.loads ok version=1 lines=12 bytes=2458 non-ascii=0 CR=0
    app/services/product_resolver.py bytes=54178 non-ascii=0 CR=0
    added lines (vs 6104eebd) 5045, non-ASCII added lines 1

Comm set (GC-7 / GC-16): 504 files at HEAD in 21 chunks (the fresh 6104eebd base record: 502 files, 26 ids); the first HEAD pass found ONE branch-only id (tests/test_s81_kb_schema.py::test_s14_p06_identity_nodes_untouched[tests/test_s75_fanout_identity.py]), fixed by the E5b re-pin, its two chunks re-run; effective HEAD 26 ids; branch-only-NEW: EMPTY.


CI-order set (spec 7.1 G5 + C-11, one process, alphabetical and reversed):

    2 failed, 2087 passed, 2 deselected, 86 warnings in 130.31s (0:02:10)
    [hermeticity] sentinel checked 2089 test(s)
    [netguard] blocked 97 attempt(s) from 32 node(s)
    2 failed, 2087 passed, 2 deselected, 87 warnings in 128.75s (0:02:08)
    [hermeticity] sentinel checked 2089 test(s)
    [netguard] blocked 97 attempt(s) from 32 node(s)

Client fences (the fourteen repository-reading suites, after `gate.py --wait-only`):

    [jest] version 29.7.0 (node v24.11.1)
    Test Suites: 1 failed, 13 passed, 14 total
    Tests:       4 failed, 236 passed, 240 total
    Time:        6.769 s
    FAIL __tests__/config/nativeBundle.w37.test.ts; the other 13 suites PASS
    FAILED (accepted drift node) W3-7 (d) runtime dependencies are imported, justified, or pending removal > d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k2 package-lock.json and node_modules resolve the five packages at or above those patches
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude
    [jest] tag=inc-r1-green-fences start=2026-11-15 23:17:47 end=2026-11-15 23:17:55 rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-fences.log

- The raw [pyt] runner lines of every gate above are in specs/INC-R1_GREEN_REPORT.md on docs/incident-2026-11-11 (filed).
### Adversaries (two lenses, FOCUS): both SOUND, 0 blocking, 0 major

Both ran on 1860fbe7 and re-ran samples of the mutation table (survivors: ruled equivalents, or GREEN behaviours without a frozen row that the probes verified). Their minors are stated limits here (LC-4):
- Correctness (6 minors): (m1) "Creed Aventus Cologne" and "Aventus Cologne" resolve HIGH to Creed Aventus EDP because "cologne" is a generic word; Aventus Cologne is a distinct product, so after the flip that input is searched as the EDP (follow-up: seed the flanker line). (m2) One Arabic code point waives guard (d), mixed-script input included (the R1-6 Arabic waiver is wider than its wording). (m3, m4) Behaviours no frozen test pins but probes verified: the GC-5 Q2 flanker reading, the other-side fragrance-intent clause, the partner pass for side a, the house-alias widening of guard (d), multi-token alias forms. (m5) The pair category still runs the keyword classifier; the resolver only skips the A2b escalation. (m6) Three route-twin WARNING lines are missing from the CLAUDE.md row (carried to the next CLAUDE.md touch).
- Contract and live bundles (10 minors): (m1) ONLY the current over-the-air bundle (consent 3) reaches the model arm: the store JS 683f56c0 sends no X-AI-Consent-Version header and the first update sends consent 2, so those phones get the lexicon arm only. (m2-m4) The stream ask's S81-10 budget arms, the error handler's concentration set and the refund label are correct (probes) but unpinned by the frozen RED. (m5) "An ask is free" holds only while the S81-10 budget is open (ENABLE_FRAGRANCE_ONLY_GATE ON with a spent budget keeps the credit). (m6) E5b verified exact. (m8) The owner's pair resolves by the lexicon with no model call, so its ask branch cannot occur. (m9) llm_router.route's docstring still says 16 sites (route stays byte-equal for MON1's digest). (m10) One more flag read per sync text compare (is_ask_refusal); no behaviour change.

### PROOF ON THE PHONE (R1-R12 as amended by R1-R24, R1-R26 and GC-5 Q1)

When it CAN pass: merged and deployed; the relay flipped `ENABLE_PRODUCT_RESOLVER` on web in its own window on the owner's yes. The phone's compare is the sync GET /api/v1/text/compare, so every backing line is read for that route. No check needs AI text. A screenshot taken before the relay's dated flip line proves nothing (OFF is byte-identical).

| # | Typed on the phone | What must be visible | Backing (names and lines only) |
|---|---|---|---|
| 1 | consent-3: "stronger with you" vs "Tyger" | EITHER the cards read Stronger With You (sub-line Emporio Armani) and Tygar (sub-line Bvlgari), with no truck-part price and no poem picture, OR the coded alert asking for the brand and the fragrance name, with the free-compare pill unchanged | `[RESOLVE] a=lexicon/high b=lexicon/high outcome=resolved`; the saved row's `full_response.overview.products[i].brand` = Emporio Armani / Bvlgari. For an ask: the GET access line with 400, `[RESOLVE] ... outcome=ask`, and no `Fetching reviews for:` line for that request |
| 2 | consent-3: "Sauvage EDP" vs "Bleu de Chanel EDP" | Sauvage (sub-line Dior) and Bleu de Chanel (sub-line Chanel) | the saved row's brands Dior / Chanel; `outcome=resolved` |
| 3 | consent-3: "Dior Sauvage EDP" vs "Chanel Bleu de Chanel EDP" | a normal result, no new refusal | the saved row's names Sauvage / Bleu de Chanel, brands Dior / Chanel; `outcome=resolved` |
| 4 | consent-2: "Tom Ford Ombre Leather" vs "Montblanc Explorer" | the result behaves as today (the typed names, no alert) | `[RESOLVE] a=none/medium b=none/medium outcome=passthrough` (no llm side: the model arm is skipped below consent 3, R1-R6), and no api.anthropic.com request line in a quiet window (GC-5 Q1) |
| 5 | consent-3: "hacivat" vs "erba pura" (unseeded, no houses typed) | Hacivat (Nishane) and Erba Pura (Xerjoff), OR the ask alert, OR as today with a WARNING (a cut call) | `[RESOLVE] a=llm/high b=llm/high outcome=resolved` (or the outcome seen) plus the api.anthropic.com request line; the only check that exercises the model arm (R1-R24) |

The relay files a dated line with the outcome of each check and the saved-row ids. A phone still on the Store JS reads the ask as its own INSUFFICIENT_DATA sentence, which also passes check 1 as the coded alert.

### Owner steps (names only; a dated ledger line per step)

- OS-1 the merge window: the relay's dated word; the orchestrator merges.
- OS-2 the relay sets `ENABLE_PRODUCT_RESOLVER` ON on web on the owner's yes, in its own window, after the merge (no other flag in that window). The knobs stay unset (2.5 s, ask ON).
- OS-3 the PROOF ON THE PHONE run on a consent-3 and a consent-2 account, screenshots and saved-row ids in a dated ledger line.
- OS-4 rollback when needed: `ENABLE_PRODUCT_RESOLVER` false, or `PRODUCT_RESOLVER_ASK=0` to keep resolution without refusals.

Canary watch: the `[RESOLVE]` outcome mix (filter on RESOLVE or outcome=ask, no bracket in the filter), the `ms=` field against the 2.5 s wall and the `class=TimeoutError` WARNING count, the 400 count on GET /api/v1/text/compare, no rise in 503.

### Stated limits

- SL1 Arabic-script names: guard (d) is waived and (c) must hold through the union; the seed has no Arabic alias, so an Arabic name resolves only through the model arm.
- SL2 / SL3 With no usable Claude answer there is no refusal: below consent 3 the model arm is skipped (R1-R6), so a consent-2 account gets only the deterministic arm, which resolves only the 12 seeded lines (not a catalog).
- SL4 / SL5 The Store JS reads every INSUFFICIENT_DATA as its own sentence (R1-R25); no bundle renders `candidates` until INC-C1.
- SL6 / SL7 / SL8 A call cut by the 2.5 s wall (or the hard cap) after it left records nothing in the ledger or the spend breaker though the provider may bill it; the chokepoint's Redis waits sit inside the wall; the resolve site's latency is unmeasured (not in the S81-07 harness): the canary reads the ms= field.
- SL9 The answer cache is per process, lost on every deploy, with no single-flight (two concurrent identical pairs may both call).
- SL10 History titles show the line names without the house (R1-R27).
- SL11 Under ASK on, a house-only pair or a pair with one unknown fragrance side becomes the ask alert when Claude answers.
- SL12 An ask is refunded: only the 10/minute limiter, the spend breaker and (with ENABLE_FRAGRANCE_ONLY_GATE ON) the S81-10 refusal budget bound the calls asks cost.
- SL13 Rows cached under the bare-name keys stay in L1 / L2; a resolved request uses new keys (more provider calls and cold latency on first use) and never reads them; with the flag OFF they serve again.
- SL14 / SL18 With the KB flags OFF nothing reads or writes the KB; a resolved side without a concentration (Acqua di Gio Profumo, a typed flanker, a model-arm line outside the seed) has no KB id; with ENABLE_KB_INGEST ON a model-arm identity enters kb_products unmarked.
- SL15 A non-fragrance pair the skip does not catch (two brand-model names with no category word) costs one model call on consent 3 and is left unchanged.
- SL16 With a pair fragrance context the single-token fuzzy matches resolve HIGH on the deterministic arm (euros -> Eros, sausage / salvage / savage -> Sauvage, aventis -> Aventus, dalton / leyton -> Layton, lire / liber -> Libre, errs / eris -> Eros, tagar -> Tygar); without a context they stay MEDIUM (R1-R8).
- SL19 A pair resolved to one canonical product proceeds (R1-R20); with ENABLE_RESULT_GATE ON S81-20 refuses it after the compare.
- SL21 / SL22 / SL23 The base concentration narrows the price search when none was typed; picture relevance is INC-I1's; a model-arm display brand is the model's cleaned string (at most 60 characters) unless it names exactly one line-file house.
- C-13 The resolver's wall runs inside the compare deadline: with ENABLE_PHASE2_RESIDUAL_GUARD ON a model-arm compare skips Phase 2 more often.
- C-14 A resolved side's [RESOLVE] line value is a catalog name or a model line within the edit rule of the typed text, so it can echo typed words; a brand accepted only because it was typed logs '-'.
- CR-6 On a resolved side the legacy products alias variant moves from null to a string (the concentration); the overview variant is composed from the specs as before.
- R1-R2 If ENABLE_SONNET_ESCALATION is ever set ON, the resolve site could take the compare's one Sonnet escalation (route() untouched); a follow-up must land before that flip.
- A flag flip between the orchestrator's ask and the route twin's check sends that one request through the generic failure arm (a coded 400 without the reason, refunded without keys).
- SL24 A hermetic test is not the production proof: the claim waits for PROOF ON THE PHONE.
- MAIN MERGED IN: main 713782d4 (#408 the timing deflake, #409 S95-LG) was merged into this branch as 4c65052c (one CLAUDE.md conflict, resolved as a union: the S95-LG block, then this unit's block, each followed by a blank line). On the merged bytes the two RED files pass with the flag ON, and with it OFF together with the E-row files, the CLAUDE.md and black-allowlist readers and #409's three test files: 1,621 passed, 1 failed = tests/test_s81_s07_meas_harness.py::test_r35_fixtures, a base-record id (CR bytes in this CRLF checkout).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

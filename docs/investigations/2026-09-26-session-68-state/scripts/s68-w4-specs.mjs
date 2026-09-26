export const meta = {
  name: 's68-w4-specs',
  description: 'Session 68 W4 product-truth lane on Opus 5.5: for each remaining W4 unit (6a, 7, 8, 11, 12, 13, 14) a MEASURED unit spec at base 61585c58 in the session-65d format, then an independent adversarial spec review appended to the spec; two units in flight at a time',
  phases: [
    { title: 'Measure', detail: 'one agent per unit: re-anchor every claim at 61585c58 with real-function probes, write the spec', model: 'claude-opus-5-5' },
    { title: 'Review', detail: 'one adversarial reviewer per spec: refute every measured claim and the design, append the review section', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const DIR = 'C:/Users/SynAckITPC/Documents/AI/sc-w4-specs'
const OUT = DIR + '/.qa-s68/specs'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'
const EXEMPLAR = 'C:/Users/SynAckITPC/Documents/AI/sc-w4-1/.qa-w4/W4_1_UNIT_SPEC.md'
const REVIEW_DOC = DIR + '/docs/investigations/2026-09-06-full-review.md'
const TABLES_DOC = DIR + '/docs/investigations/2026-09-06-full-review-tables.md'
const VERIFIED_JSON = DIR + '/docs/investigations/2026-09-06-full-review-verified.json'
const S66_CLOSE = DIR + '/docs/investigations/2026-09-24-session-66-close-state.md'
const S67_STATE = DIR + '/docs/investigations/2026-09-24-session-67-state.md'
const ISSUES = DIR + '/.qa-s68/issues_w4.md'
const ONLY = (args && Array.isArray(args.only) && args.only.length) ? args.only : null

const UNITS = [
  { key: 'W4-6a', file: 'W4_6A_UNIT_SPEC.md', client: false, row: 'W4-6a rubric truth - stop reporting measured data as missing. Findings PO-RUBRIC-01, -02, -03 (+ -08 P2). Files (anchors from 76ace90, drifted): app/services/scoring_service.py:262-286/328-334/1789-1826/2113-2155/2222-2233. Flags: ENABLE_VALUE_DIM_PARTIAL_SIGNAL + ENABLE_TIE_IS_NOT_MISSING (default OFF, read per call). Red claims: (a) no dimension contributing > 1.0 point of the margin may appear in missing_data or resolve N/A (RED: value_score supplies 14.0/14.0 and is both); (b) an identical fully-verified pair keeps measured reliability >= 90 and is not stamped missing (RED: 4/6 dims at 50); (c) two DIFFERENT fashion products separate on craft_score (RED: 1.0 == 1.0). Notes: independent of the #101 call and a precondition for its evidence being readable (53.7 % of dimension cells carry a missing stamp today); byte-identity via the four *_flag_off_golden.json fixtures (locate them under tests/; the flag-ON arm regenerates a separate golden, the OFF goldens stay byte-identical). W4-10 (#176, UNFLAGGED, merged) changed compute_scores dimension-winner labels and tradeoffs; W4-3 (#177) and W4-4 (#179) touched the scoring paths in structured_comparison_service - every anchor must be re-measured at 61585c58.' },
  { key: 'W4-7', file: 'W4_7_UNIT_SPEC.md', client: false, row: 'W4-7 fact-check honesty. Findings PO-FACTCHECK-CONFIDENCE-01, -02 (+ activation of -03/-04 = issues #109/#106). Files: scoring_service.py:1958-1976, response_builder.py:1055 (anchors drifted). Flag: inside the EXISTING ENABLE_CONFIDENCE_FACTCHECK_WIRING (#109) - decide and justify whether the two fixes ride that flag or need their own. Red claims: _score_reliability(all-unverified) is None (RED: 0.3); builder legs == persisted legs for the same inputs (RED: weak vs acceptable). Activation order per scoring_service.py:982-989 (re-locate): #107 -> cache roll -> #106 -> #109. Read the issue bodies for #106, #107, #109 in the issues file.' },
  { key: 'W4-8', file: 'W4_8_UNIT_SPEC.md', client: false, row: 'W4-8 category truth. Findings PO-CATEGORIES-I18N-01 (P1), -03 (P2 after the second vote). Files: extraction_service.py:1096-1097 (the token synonym map), app/data/content_blocklist.json:53 (anchors drifted). Flag: ENABLE_CATEGORY_TOKEN_FIX (default OFF) for the synonym-map change; the blocklist edit is DATA (unflagged: it strictly narrows a fail-closed block). Red claims: classify_category_from_text(Panadol Extra 24 tablets vs Adol 500 tablets) != electronics (RED today); check_query_intent of the Arabic YSL Opium query (bare-hamza spelling of Opium) .allowed (RED: blocked as illegal_drugs); AND the second node Samsung Galaxy Tab S10 tablet 256GB must STILL classify electronics (rules out the naive token drop). Worse than filed: category also gates the PRICE branch (scs.py:5671-5677 at 76ace90 - re-locate), so electronics kills the iHerb/pharmacy tier for every tablets pair. Flag-OFF gate = equality over the product lane\'s constructed 360-query GCC corpus (9 categories x 40), not the _proof SHA - LOCATE that corpus under docs/investigations/2026-09-06-full-review-state/ (search for the 360 queries / category lane files); if it is not on disk, say so and specify how the spec regenerates an equivalent corpus deterministically. Mirror the EN multi-word forms of commit 9f6e498 (read it with git show) and audit the Arabic entries for rifle, silencer, tactical knife in the same pass.' },
  { key: 'W4-11', file: 'W4_11_UNIT_SPEC.md', client: false, row: 'W4-11 prompt truth (UNFLAGGED by nature). Findings PO-PROMPTS-11 (status, activation), -01, -02, -05, -06, -13, -03 (P2), CR-SECURITY-08 (the extract_specs_targeted fence). Files: extraction_service.py:614-616/824-832/937/1030/1042, openai_service.py:285, prompt_personalities.py:47/77, the 12 model_config-bypassing call sites (anchors drifted - enumerate them at HEAD). Flag: none exists for prompt text - the only lever is ENABLE_SPECS_NO_FABRICATION; the fence, the contradiction and the model_config fixes ship unflagged. Red claims: extend tests/test_prompt_fence.py - a snippet carrying a literal </SEARCH_RESULTS> plus an instruction must not escape its region in extract_specs_targeted OR COMPARISON_SYSTEM, and the raw product name is sanitised before the system message (RED: openai_service imports no sanitizer); test_shipped_prompt_does_not_license_training_data stays red until the flag becomes the default - the spec MUST resolve how a deliberately-red test coexists with a green CI (xfail strict with the flag reason, or a flag-conditional expectation) and say which. The canary IS the gate (byte-identity is meaningless for prompt text): offline render-diff of both flag states + resolved_models() unchanged -> post-deploy eval_runner smoke20 judged on axis averages -> the [specs] no-fabrication guard dropped N line. Prompt-cache cost: the specs (2,121 tok) and verdict (2,241 tok) prefixes are cache-eligible; any edit invalidates them once per deploy; an edit that inserts dynamic text BEFORE the static prefix destroys eligibility permanently - measure where the dynamic text sits today in each prompt. ENABLE_SPECS_NO_FABRICATION flips LAST in the activation order. W4-9 (#178, merged) changed the error envelopes on the text compare paths - re-check what it touched in openai_service / extraction_service.' },
  { key: 'W4-12', file: 'W4_12_UNIT_SPEC.md', client: false, row: 'W4-12 display contract: one spelling, one margin, one verdict. Findings PO-VERDICT-TRUTH-03, -04, -06, -07, -08, -09, -14 (P2). Files: response_builder.py:1136-1174/1387/1635/1801, scs.py:4266, home_routes.py:503/527, profile_routes.py (anchors drifted). Flag: the review says none (restoring intended behaviour) - but the phones (EAS group 561d2cba from ab9442ae) READ these fields: measure in SmartCompareApp/src what the client renders from overview.winner.margin vs scoring_v2.win_margin (the strong-win CTA fires at 13 % where 41 % was intended) and PROPOSE, with evidence, whether a default-OFF flag is required for the margin change (the standing rule: a user-visible result fork sits behind a per-call flag). Red claims: the SSE verdict payload equals the complete payload after scrubbing (RED: raw dict on the wire); overview.winner.margin == scoring_v2.win_margin (RED on 23/23 recorded rows); /home/smart-pick names deduped (RED on 16/26); retailer_quotes pass the score-internals scrub. W4-10 (#176) already routed compute_scores labels through dedup_brand_name and its follow-up notes name home_routes._select_smart_pick priority_match repair vs dedup_brand_name and tests/test_home_routes.py:311/:400-428 pinning a shape production never writes - re-measure which of the seven findings still hold at 61585c58. The client half overlaps the mobile lane - the spec names it as a follow-up, not this unit.' },
  { key: 'W4-13', file: 'W4_13_UNIT_SPEC.md', client: false, row: 'W4-13 measurement truth. Findings PO-RECORDED-MEASURED-01, -07, -10, -11, -17 (P2), PO-CATEGORIES-I18N-13 (P2), LS-MEASURED-EVIDENCE-07/-08. Files: analytics_service.py:12-32/59-74, database_service.py:499, text_routes.py:230/630, url_routes.py (add log_search), a NEW migration for search_logs.is_synthetic (the next free number is 042 - 039 is RESERVED for the M13-29 RLS migration, 040/041 exist; the migration needs a rollback file under migrations/rollback/, IMMUTABLE index predicates, and source-level pins in the style of tests/test_migration_041_user_events_public_select_policy.py). Flag: none (admin read paths + one nullable column) - justify or propose one. Red claims: 10 probe rows at 0 ms + 2 organic at 22,000 ms => avg_duration_ms == 22000 and a non-probe top query (RED: 3,667 ms, product1 vs product2); every log_search failure call passes cost=; a partial increments metadata.partial_stage (W4-4 #179 landed a partial_stage field - measure what remains); /url/compare writes a log_search row. Must land before any launch gate reads a number. Note the 13 probe strings the review used to filter the series (find them in the review state folder) - the spec says how is_synthetic is decided (by caller flag, by string list, or both) and how existing rows are backfilled or excluded.' },
  { key: 'W4-14', file: 'W4_14_UNIT_SPEC.md', client: true, row: 'W4-14 Arabic on the results surface (CLIENT unit + dark backend plumbing). Findings PO-CATEGORIES-I18N-04, -10, -11, -02 (P2), -05, -12 (P3). Files: SmartCompareApp/src/... DimensionBars.tsx:313, ResultsContent.tsx:143 (anchors drifted), extraction_service.py:1849 (+ a locale on the compare routes). Flag: client unflagged (OTA-gated); backend locale plumbing behind a default-OFF flag (name it). Red claims (jest): every rendered dimension label resolves through a results.dimension.* key present in BOTH catalogs (RED: the family does not exist); a price string under lng=ar does not mix numeral systems between Results and History. 52 dimension labels render raw English and every verdict an Arabic user reads is English (no route accepts a locale, the client sends none, no prompt asks for Arabic). W3-11bcd (#175, merged) shipped the Arabic pack and W3-14 (#174) routed settings copy by code - re-measure the 52-label claim and the catalogs at 61585c58 (SmartCompareApp/src/i18n). The worktree has a node_modules JUNCTION into the clone: run jest/tsc from SmartCompareApp there; NEVER run npm install/ci/uninstall/prune (it would mutate the shared node_modules through the junction). Belongs with W3-11 in the same OTA; the OTA itself is Ahmed\'s.' },
]
const SELECTED = ONLY ? UNITS.filter((u) => ONLY.includes(u.key)) : UNITS

const MEASURE_SCHEMA = {
  type: 'object',
  required: ['unit', 'spec_path', 'spec_sha256', 'base_sha_confirmed', 'anchors_remeasured', 'red_claims_status', 'design_summary', 'flag_decision', 'gates_summary', 'open_questions_for_fable', 'files_written', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    spec_path: { type: 'string' },
    spec_sha256: { type: 'string' },
    base_sha_confirmed: { type: 'boolean' },
    anchors_remeasured: { type: 'array', items: { type: 'string' }, description: 'review anchor -> symbol -> line at 61585c58' },
    red_claims_status: { type: 'array', items: { type: 'string' }, description: 'each red claim of the row: HOLDS / REFUTED / CHANGED with the pasted measurement' },
    design_summary: { type: 'string' },
    flag_decision: { type: 'string', description: 'flag name(s), default, per-call reader, what OFF preserves, and WHY (or why unflagged, with the rule it satisfies)' },
    gates_summary: { type: 'string', description: 'the byte-identity / equality gate, comm set grep, CI-order pin files, mutation table size' },
    open_questions_for_fable: { type: 'array', items: { type: 'string' } },
    files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>"' },
    scratch_cleanup: { type: 'string' },
  },
}
const REVIEW_SCHEMA = {
  type: 'object',
  required: ['unit', 'verdict', 'refuted_claims', 'corrections', 'missing_items', 'design_risks', 'appended_section_sha256', 'summary'],
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['APPROVED_WITH_CORRECTIONS', 'REJECTED'] },
    refuted_claims: { type: 'array', items: { type: 'string' }, description: 'each spec claim you re-measured and found wrong, with your measurement' },
    corrections: { type: 'array', items: { type: 'string' }, description: 'concrete edits the spec needs (design, tests, gates, anchors)' },
    missing_items: { type: 'array', items: { type: 'string' }, description: 'what the spec omits (a caller, a flag-OFF path, a pin, a client anchor, a migration rule)' },
    design_risks: { type: 'array', items: { type: 'string' } },
    appended_section_sha256: { type: 'string', description: 'sha256 of the spec file after your section was appended' },
    summary: { type: 'string' },
  },
}

const measurePrompt = (u) => `You are writing the MEASURED UNIT SPEC for ${u.key} (myez/Qaren, W4 product-truth lane), base 61585c58 = origin/main. Worktree (READ-ONLY code; you may write ONLY under ${OUT}/ and your own scratchpad): ${DIR}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line (pytest probes go through the guard plugin; never import app.* outside pytest; never commit; never touch other worktrees).${u.client ? ' CLIENT unit: SmartCompareApp/node_modules in this worktree is a JUNCTION into the shared clone - run jest / tsc only (cd SmartCompareApp; npx jest <path> ; npx tsc --noEmit --pretty false); NEVER run npm install/ci/uninstall/prune/dedupe anywhere.' : ''}

THE UNIT ROW (from docs/investigations/2026-09-06-full-review.md section W4, refined by the session-66 close doc):
${u.row}

READ FIRST: the exemplar spec ${EXEMPLAR} (its structure and rigour are the standard: a "defect, measured" table of REAL function outputs, "what already exists", the design with the per-call flag reader and the OFF identity, Preserve list, red tests with names, gates, mutation checks, activation, honest limits, spec disagreements with the review). Then the findings: ${TABLES_DOC} (the per-severity tables) and ${VERIFIED_JSON} (each finding's evidence; grep your PO-*/CR-*/LS-* ids), the W4 section and the relevant paragraphs of ${REVIEW_DOC}, section 4-5 of ${S66_CLOSE} (batch-5 rulings and follow-ups touching your unit), the flag rows of CLAUDE.md that neighbour your files, and ${ISSUES} (issue bodies #100 #102 #103 #106 #107 #109) where your row names an issue. Standing rules from CLAUDE.md: every price-path or user-visible result fork sits behind a default-OFF ENABLE_* flag read per call via os.getenv (never memoised) with flag OFF byte-identical; module globals resolved at call time; phones run the preview OTA group 561d2cba from ab9442ae via sync REST and SSE, so every backend change stays compatible with them; migrations: next free number 042, 039 reserved, rollback file required, IMMUTABLE index predicates, source-level pins.

YOUR TASK:
1. Confirm HEAD is 61585c58. Re-locate EVERY anchor in the row by symbol at HEAD and record the current line numbers.
2. Re-measure EVERY red claim in the row by running the REAL function through a pytest probe under the guard (no network, no LIVE): does it still hold at 61585c58 (HOLDS), was it fixed or changed by a later merge (CHANGED - say which PR), or was the review wrong (REFUTED)? Paste the measured values. Where the row says a number (23/23 rows, 16/26, 53.7 %), re-derive it from the recorded corpora under docs/investigations/2026-09-06-full-review-state/ when they are on disk, else state that the number is unverifiable offline and pin what IS measurable.
3. Write ${OUT}/${u.file} in the exemplar's format, self-contained for an Opus red agent: base SHA; findings; the measured defect table; what already exists (reuse, do not reinvent); the design (flag name(s), per-call reader, exact effect ON per site, why OFF is byte-identical, the client anchors on the 561d2cba phones where relevant); files to touch and must-NOT-touch; the red test list with test names and the file they live in (RED = fails at HEAD for the stated reason; PIN = green at HEAD and must stay); the mutation table; the Preserve files (every test file that pins the touched functions - grep); the comm-set grep; the byte-identity / equality gate recipe (say exactly what is compared and how); the CI-order pin set; activation order and canary lines; honest limits; spec disagreements with the review; OPEN QUESTIONS FOR FABLE (decisions only the orchestrator can take - flag or not, scope splits, product calls). Every number in the spec is one you measured in this run.
4. Report per the schema with the spec's sha256. Remove any scratch worktree; leave the worktree's tracked files untouched (git status --short shows only the .qa-s68 folder, which is gitignored, i.e. nothing).`

const reviewPrompt = (u, m) => `You are the ADVERSARIAL SPEC REVIEWER for unit ${u.key} (myez/Qaren, W4 lane), base 61585c58. Worktree (READ-ONLY code; you may write ONLY the review section appended to the spec file and your own scratchpad): ${DIR}. Shared rules: read ${COMMON_PATH} in full FIRST.${u.client ? ' CLIENT unit: run jest/tsc only from SmartCompareApp (node_modules is a junction into the shared clone); NEVER run npm install/ci/uninstall/prune.' : ''}
The spec to refute: ${OUT}/${u.file} (sha256 reported by its author: ${m ? m.spec_sha256 : 'unknown'}). The author's report:
${JSON.stringify(m, null, 1)}

Sessions 65d and 66 found 5-13 refuted measured claims in EVERY spec written with this care, including red tests that would have been wrong at HEAD. Assume this spec has them too.
1. Re-measure every measured claim in the spec through the real functions on the pinned venv (pytest probes under the guard; jest for client claims). List each refuted or drifted claim with your measurement.
2. Check the design against the standing rules: every user-visible or price-path fork behind a default-OFF per-call flag with OFF byte-identical (name any fork the spec leaves unflagged and say whether the rule allows it); module globals resolved at call time; phone compatibility (561d2cba client reads - name the field and the screen); migration rules where a migration is proposed; no scope creep beyond the row's findings; each RED test genuinely red at HEAD for the stated reason and each PIN genuinely green; the mutation table kills every load-bearing line; the comm set and Preserve lists are complete (grep yourself); the gate recipe is executable as written.
3. Name what is MISSING: callers the design does not reach, the OFF path it forgets, a pin it needs, a product decision it hides inside a design choice.
4. APPEND to the spec file a section headed exactly "# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)" with: VERDICT (APPROVED_WITH_CORRECTIONS or REJECTED), the refuted claims with measurements, the corrections, the missing items, the design risks, and the questions Fable must rule on. Do not rewrite the author's text; append only. Report the file's sha256 afterwards.
5. reproduced measurements only; do not pad; if the spec is right, say so per claim.`

function chunk(arr, n) { const out = []; for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n)); return out }

log('W4 spec lane: ' + SELECTED.map((u) => u.key).join(', ') + ' (two units in flight at a time)')
const results = []
for (const pair of chunk(SELECTED, 2)) {
  const r = await pipeline(
    pair,
    (u) => agent(measurePrompt(u), { label: 'spec:' + u.key, phase: 'Measure', model: MODEL, effort: 'high', schema: MEASURE_SCHEMA }),
    async (m, u) => {
      if (!m) return { unit: u.key, measure: null, review: null }
      const rv = await agent(reviewPrompt(u, m), { label: 'spec-review:' + u.key, phase: 'Review', model: MODEL, effort: 'high', schema: REVIEW_SCHEMA })
      return { unit: u.key, measure: m, review: rv }
    },
  )
  results.push(...r.filter(Boolean))
  log('W4 spec lane: done ' + pair.map((u) => u.key).join(', '))
}
return { units: results }

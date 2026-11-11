export const meta = {
  name: 'inc-design-measure',
  description: 'Incident fix lane, read-only: measure the size-fairness path (X1) and inventory + propose the fixed fragrance result page (X4/X5/X6/X7); each document is then attacked by a skeptic',
  phases: [
    { title: 'Measure', detail: 'one writer per topic, read-only, writes its document under the design folder' },
    { title: 'Skeptic', detail: 'one skeptic per document re-measures every citation' },
  ],
}

// args: { sp, header, report, t1, t2, t4, srcMain, srcStore, record, out }
const A = args
const RULES = [
  'RULES (violating any fails the task). Read the incident-lane header first: ' + A.header + ' (H0-H7; it is short). This round is READ-ONLY: no pytest, no jest, no tsc, no eslint, no network, no git command that writes, no package manager, no production probe, no .env read. You read plain source exports, never a git checkout: the backend and client at main a74caba7 under ' + A.srcMain + ' (app/ and SmartCompareApp/src/; the client there is byte-identical to the live OTA bundle f1e20c39), and the STORE binary client 683f56c0 under ' + A.srcStore + ' (SmartCompareApp/src/). Never open a path under C:/Users/SynAckITPC/Documents/AI (it injects a 60k-token file into your context). Docs: the verified incident report ' + A.report + ' and its extracts ' + A.t1 + ' (the trace of the three incident comparisons), ' + A.t2 + ' (field sources), ' + A.t4 + ' (the result page); the record copy ' + A.record + ' (s81/PLAN_S81.md, s81/specs/, s80/PLAN_S80.md section 0 = the frozen response contract, CLAUDE_md_a74caba7.txt: grep it, never read it whole).',
  'Cite file:line for every claim, measured in this run (line numbers of the export files equal the lines at the sha). Mark anything you could not verify as UNVERIFIED instead of guessing; state each assumption with the reason it beats the alternative. Write your document(s) THROUGH THE SHELL (python or a quoted heredoc) into ' + A.out + ', pure ASCII except where Arabic strings are required (then UTF-8), LF line endings. Plain English, complete sentences, tables for enumerable facts. Never say a production problem is fixed. No personal values, no credential shapes.',
  'Facts of record: MYEZ compares two fragrances; 1.0.0 (3) is live on the App Store (store JS 683f56c0) and the first OTA (f1e20c39) is out; both bundles read the live backend, so the response keys they read are frozen (new keys are additive; never remove, rename or retype one without a ruling); every backend change lands dark behind a new ENABLE_* flag read per call; a client change ships only in a later OTA after the owner approves the design and reads every new Arabic string. The owner will be asked two questions: N5 "when a found price is for a different bottle size, blank it (today) or show it with its size?" and N5b "then (a) show both prices with their sizes, a per-ml line, and make no cheaper claim, or (b) compare per ml?".',
].join('\n')

const DOC_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    doc_paths: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    key_findings: { type: 'array', items: { type: 'string' } },
    decisions_needed_from_owner: { type: 'array', items: { type: 'string' } },
    proposed_units: { type: 'array', items: { type: 'string' } },
    focus_surfaces: { type: 'array', items: { type: 'string' } },
    unverified: { type: 'array', items: { type: 'string' } },
  },
  required: ['topic', 'doc_paths', 'summary', 'key_findings', 'decisions_needed_from_owner', 'proposed_units', 'unverified'],
}
const SKEPTIC_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    review_path: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'SOUND_WITH_CORRECTIONS', 'UNSOUND'] },
    refuted_claims: { type: 'array', items: { type: 'string' } },
    corrections: { type: 'array', items: { type: 'string' } },
    missing: { type: 'array', items: { type: 'string' } },
    contract_risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['topic', 'review_path', 'verdict', 'refuted_claims', 'corrections', 'missing', 'contract_risks'],
}

const TOPICS = [
  {
    id: 'X1',
    prompt: [
      'You are the MEASURER for unit INC-X1 SIZE-FAIRNESS. Incident fact: the server FOUND real Bahrain prices (Layton 85.000 BHD, YSL Libre 39.000 BHD) and then blanked them with price.reason = size_mismatch because they were off the 100 ml flagship target (price_service.py reconcile_pair_sizes about :2259-2400, _mark_size_pending about :2403-2417); a third (Armani) was only a parked US-converted 40 ml fallback, which must never be shown as a Bahrain price.',
      'Deliverable: ' + A.out + '/X1_MEASURE.md with these sections. 1 THE PATH AT MAIN: every caller of reconcile_pair_sizes and the flags and knobs on that path with their defaults; target_pair_size_ml, effective_pair_size_ml, reselect_to_target_size, make_pending_price (the exact shape of a pending price), where candidates_by_name comes from and what a candidate carries (size, title, retailer, source, region, variant rank). 2 DOWNSTREAM: every consumer of a price that is pending or carries reason size_mismatch: response_builder (every price key of the response in both shapes, best_price, retailer, any price comparison or delta), scoring_service (which dimensions read a price, what a missing price does, the missing_data list), the verdict prompt inputs, the field-status metadata (kb_ingest.py about :166-262 and response_builder about :2322-2329), the saved row. 3 BOTH CLIENT BUNDLES: for 683f56c0 and for a74caba7, the component chain that renders a product price; exactly what is shown for a normal price, for a pending price per reason, and whether a bottle size is ever shown next to a price (name the prop and the condition); the honest lines of S81-11 / D20 and the server flags that feed them. 4 PER-ML: any existing per-ml computation on either side. 5 TWO DESIGNS, one per answer to N5b: (a) show both prices with sizes, a per-ml line, no cheaper claim; (b) compare per ml. For each: the smallest additive server contract (new keys with types; which existing keys keep their meaning), what scoring must do with a price that is not on the common basis, what EACH live bundle would display with NO client change (is it honest or misleading?), the client change needed and whether it must wait for an OTA, the files touched, the flag, the risks, and a truth table on the three incident products (Layton, Libre, the Armani parked fallback). 6 CLASS: name every FOCUS surface (auth, quota or billing, legal or privacy text, consent, security middleware, migrations, Redis or Lua, the App-Review-visible client surface, secrets) each design touches. 7 A RECOMMENDATION with its reason, and the exact wording of what the owner must decide.',
    ].join('\n\n'),
  },
  {
    id: 'PAGE',
    prompt: [
      'You are the INVENTORY-AND-DESIGN writer for the fixed fragrance result page (units X4 fixed page, X5 server text as keys, X6 honest bars, X7 key differences). Incident facts: the result page has no fixed template (sections appear only when their data exists; bars were 0 / 4 / 1 on three results; Pros and Cons is removed on a degraded result); the server sends English-only sentences that the Arabic page shows verbatim; some bars are proxies (star ratings shown as longevity and projection; a missing-data default of 50 can win a dimension); key_differences is always [] (response_builder.py about :2297) and NO client bundle renders it; the owner said: "I thought we had a fixed page".',
      'Deliverable 1: ' + A.out + '/PAGE_INVENTORY.md. (a) Every section of the result page at main (screens/ResultsScreen.tsx and components/results/*, incl. ResultsContent.tsx, DimensionBars.tsx, FactualVerdict.tsx, PersonalizationChip.tsx, the specs and reviews rows, the price block, the honest-state helpers such as resultHonesty.ts and fieldStatusView.ts): its order on screen, its render condition, the response keys it reads, what it shows when its data is empty, and the differences in the store binary 683f56c0. (b) Every string the SERVER writes that a client shows verbatim (the factual verdict templates in response_builder.py about :1073-1181, the bar captions and priority names in scoring_service.py about :1339-1340, :3302, :3660-3685, the region name), each with file:line, its inputs, and whether a key-like field already travels beside it. (c) The bars: every dimension for the fragrance category, its data source, the proxy mappings (scoring_service.py about :2108-2135, :2175-2179, :2339-2353), the default-50 behaviour, and which rows of the three incident results were proxies. (d) key_differences: every producer and consumer on every path (text, camera, link), and what data exists at response-build time from which a list could be built WITHOUT an LLM call.',
      'Deliverable 2: ' + A.out + '/PAGE_DESIGN_PROPOSAL.md, written for a non-technical founder first (plain English, short sentences), then the technical tables. One fixed fragrance result page: the same sections in the same order every time. For EACH section: what the user sees when the data is known, when it is partly known, and when it is not known (an honest line, never a vanished section and never a fake value); the response keys it uses (existing, or a NEW additive key with its type); the server work it needs (name the unit: X5, X6, X7 or none) and the client work (X4). Then: the fixed set of fragrance bars and the rule for an unknown bar; the key-differences block (what it lists and from which data); the server-text-as-keys contract (the key vocabulary with parameters, so the app renders Arabic or English itself, while the old English fields stay for the live bundles); a table of EVERY new user-visible string with a proposed key, the English text and an Arabic draft marked [NATIVE READ] (follow src/i18n/.copy-policy.json and the existing tone in src/i18n/ar.json; reuse existing strings where one fits and cite it); what the two LIVE bundles show while the new server keys are dark or on (nothing may change for them unless stated); a slicing plan (which parts can ship as separate dark server units before the client, which need the client, what order gives the owner something visible soonest); the PROOF ON THE PHONE per slice (the golden pairs of the report, what must be visible, the backing row check); the open questions for the owner, each as one short question with a recommended answer. Do not touch the feedback card (unit CL3 is in flight in another session): show it as an existing section only.',
    ].join('\n\n'),
  },
]

function skepticPrompt(t, doc) {
  return [
    'You are the SKEPTIC for the ' + t.id + ' document(s): ' + (doc.doc_paths || []).join(', ') + '. Your job is to REFUTE: default to doubt.',
    RULES,
    'Re-read every file:line the document cites in the source exports and say for each wrong one what the code really does. Then look for what is MISSING: a consumer or a render path not listed, a response key the live bundles read that the proposal would change, a claim about what the store binary shows that the 683f56c0 source contradicts, a proposed string that breaks the copy policy or duplicates an existing key, a "nothing changes for the live bundles" claim that is false, a design that would show a price for the wrong product or the wrong region, a bar rule that still lets a default value win, a proof on the phone that could pass while the problem remains, an owner question that hides a default. Write your review THROUGH THE SHELL to ' + A.out + '/' + t.id + '_SKEPTIC.md and return the structured output. The writer summary for context: ' + (doc.summary || ''),
  ].join('\n\n')
}

phase('Measure')
const out = await pipeline(
  TOPICS,
  t => agent([t.prompt, RULES].join('\n\n'), { label: 'measure:' + t.id, phase: 'Measure', schema: DOC_SCHEMA }),
  (doc, t) => doc
    ? agent(skepticPrompt(t, doc), { label: 'skeptic:' + t.id, phase: 'Skeptic', schema: SKEPTIC_SCHEMA }).then(review => ({ topic: t.id, doc, review }))
    : { topic: t.id, doc: null, review: null },
)
const done = out.filter(Boolean)
log('documents: ' + done.filter(d => d.doc).length + '/' + TOPICS.length + '; skeptic reviews: ' + done.filter(d => d.review).length)
return done

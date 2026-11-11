export const meta = {
  name: 'inc-design-finalize',
  description: 'Incident fix lane, read-only: apply the skeptic corrections to the X1 and result-page design documents, write the owner brief and a phone mock of the fixed page, then verify each',
  phases: [
    { title: 'Finalize', detail: 'one writer per topic applies every skeptic correction and writes the v2 deliverables' },
    { title: 'Verify', detail: 'one verifier per topic checks each correction and each new claim' },
  ],
}

// args: { header, report, srcMain, srcStore, record, dir }
const A = args
const RULES = [
  'RULES (violating any fails the task). Read the incident-lane header first: ' + A.header + ' (H0-H7). READ-ONLY round: no pytest, no jest, no tsc, no eslint, no network, no git write, no package manager, no production probe, no .env read. Sources are plain exports, never a checkout: main a74caba7 under ' + A.srcMain + ' (app/ and SmartCompareApp/src/; the client equals the live OTA bundle f1e20c39) and the store binary client 683f56c0 under ' + A.srcStore + '. Never open a path under C:/Users/SynAckITPC/Documents/AI. The incident report: ' + A.report + '. The record copy: ' + A.record + '. The design folder with the v1 documents and their skeptic reviews: ' + A.dir + '.',
  'Cite file:line for every claim you add or change, measured in this run. Mark what you could not verify UNVERIFIED. Write every file THROUGH THE SHELL (python or a quoted heredoc) into ' + A.dir + ', LF line endings, UTF-8 (ASCII except Arabic strings). Plain English, short complete sentences, tables for enumerable facts. Never say a production problem is fixed. No personal values, no credential shapes. Do not edit or delete the v1 files.',
  'Facts of record: both live bundles (store 683f56c0, OTA f1e20c39) read the live backend and send no app-version signal; every backend change lands dark behind a new ENABLE_* flag; a client change ships only in a later OTA after the owner approves the design and reads every new Arabic string; ENABLE_FRAGRANCE_ONLY_GATE is OFF today (the live product still accepts other categories); the feedback card (unit CL3) belongs to another session and is shown as an existing section only.',
].join('\n')

const DOC_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, bytes: { type: 'integer' }, sha256: { type: 'string' } }, required: ['path'] } },
    corrections_applied: { type: 'array', items: { type: 'string' } },
    corrections_rejected_with_reason: { type: 'array', items: { type: 'string' } },
    owner_questions: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    unverified: { type: 'array', items: { type: 'string' } },
  },
  required: ['topic', 'files', 'corrections_applied', 'corrections_rejected_with_reason', 'owner_questions', 'summary', 'unverified'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    verdict: { type: 'string', enum: ['READY_FOR_OWNER', 'READY_WITH_NOTES', 'NOT_READY'] },
    corrections_not_applied: { type: 'array', items: { type: 'string' } },
    new_false_claims: { type: 'array', items: { type: 'string' } },
    notes_for_orchestrator: { type: 'array', items: { type: 'string' } },
    review_path: { type: 'string' },
  },
  required: ['topic', 'verdict', 'corrections_not_applied', 'new_false_claims', 'notes_for_orchestrator'],
}

const MOCK_RULES = 'THE PHONE MOCK is ONE self-contained HTML file a non-technical founder opens on a phone. Rules for the file: a <title> of two to four words; all CSS and JS inline; NO external script, image or font request (system fonts only); colours as CSS custom properties on :root, redefined for dark mode under @media (prefers-color-scheme: dark) guarded by :root:not([data-theme="light"]) and again under :root[data-theme="dark"]; an explicit body background; a layout that works at 360 px wide with a 16 px side gutter and no horizontal scroll; any localStorage use wrapped in try/catch and optional; under 150 KB. Content: the fixed fragrance result page drawn as phone-sized cards, with a language switch (Arabic RTL first, English second) and a state switch with three positions (everything known / partly known, using the real shape of the incident result "Creed Aventus EDP vs Parfums de Marly Layton EDP" / almost nothing known, using the shape of "Armani Acqua di Gio Profumo vs Versace Eros EDP"), so the founder sees that the SAME sections appear in the SAME order in every state and that an unknown field shows an honest line instead of vanishing. Use placeholder product tiles (no real photos, no brand logos), the proposal\'s section order, its five bars, its key-differences block and its strings (the Arabic drafts exactly as in the string table). Under the page, a short list titled "Questions for you" with each owner question in one line and the recommended answer. Mark the whole page clearly as a DESIGN PROPOSAL, not the live app, and say that every Arabic line is a draft for the founder\'s native read. No analytics, no forms, no links out.'

const TOPICS = [
  {
    id: 'PAGE',
    prompt: 'You are the FINALIZER for the fixed fragrance result page design (units X4 fixed page, X5 server text as codes, X6 honest bars, X7 key differences). Read PAGE_INVENTORY.md, PAGE_DESIGN_PROPOSAL.md and PAGE_SKEPTIC.md in the design folder, and X1_SKEPTIC.md for the price wire shape. Apply EVERY refuted claim, correction, missing item and contract risk of PAGE_SKEPTIC.md by re-measuring the code; where you reject one, say why with file:line. Binding decisions from the orchestrator for v2: (1) the price row follows the X1 wire shape "price.amount stays null for an off-size listing; the other bottle rides in a NEW additive key", so today\'s apps show nothing new and make no cross-size claim; (2) a size is the product\'s only when it comes from the typed name or from a price accepted at the pair\'s basis; (3) the value bar is unknown whenever the price bar is not known; (4) every place a default or a proxy can still reach the user (the runner-up card\'s tradeoff source, the scores summary sent to the AI, the Home smart-pick caption) is either brought under the X6 flag or listed as a stated limit with its own owner question; (5) the live product is NOT fragrance-only today: every rule states what a non-fragrance result does; (6) the X5 contract has no nested translated fragment, an id for every branch of every template, typed args (numbers stay numbers), and separate ids for the verdict line and the winner reason. Deliverables in the design folder: PAGE_DESIGN_V2.md (the full corrected proposal, same structure, with a change log against v1 at the end); OWNER_BRIEF_RESULT_PAGE.md (at most two pages for the founder: what he will see, what stays the same on today\'s apps, the order the pieces ship in, and every question as ONE short line with a recommended answer, merged and renumbered, no jargon, no file names); RESULT_PAGE_MOCK.html. ' + MOCK_RULES,
  },
  {
    id: 'X1',
    prompt: 'You are the FINALIZER for unit INC-X1 SIZE-FAIRNESS. Read X1_MEASURE.md and X1_SKEPTIC.md in the design folder. Apply EVERY refuted claim, correction, missing item and contract risk of X1_SKEPTIC.md by re-measuring the code; where you reject one, say why with file:line. Binding decisions from the orchestrator for v2: (1) design (a) is the default the unit builds to (the owner\'s N5 / N5b answers are pending): price.amount stays null on a size pend; the found listing rides in a NEW additive key whose name does not collide with the D20 provenance kind "listed" (propose the name); scores, verdict, savings and the winner do not change; no per-ml figure is shown unless BOTH listings are genuine Bahrain listings that state exactly one ml size in their own title; a converted or parked price is never eligible; (2) the new key is projected in response_builder after the verdict call from a product-level stash that is popped by name on every path incl. the partial paths, so the verdict prompt bytes are unchanged with the flag ON (a PIN row); (3) the dormant defect (with ENABLE_FIELD_STATUS_METADATA on, a size pend is labelled "not listed by the stores we can read yet") is closed in the same unit; (4) the proof on the phone is restated so that it can pass and cannot pass falsely: say exactly which saved-row keys and log lines prove it, and that the phone shows it only after the client OTA. Deliverable in the design folder: X1_BRIEF_DRAFT.md in the house brief form (0 what the unit does; 1 the flag ruling; 2 scope rulings R-X1-n, each one sentence of rule plus its reason; 3 questions the spec answers by measurement; 4 PROOF ON THE PHONE; 5 owner steps; 6 stated limits; 7 out of scope), written so a spec writer needs nothing else, plus an appendix "design (b) delta" of at most one page for the case that the owner picks per-ml comparison.',
  },
]

function verifyPrompt(t, doc) {
  return [
    'You are the VERIFIER for the ' + t.id + ' v2 deliverables: ' + (doc.files || []).map(f => f.path).join(', ') + '. Default to doubt.',
    RULES,
    'Check, by re-reading the code and the v1 skeptic review (' + A.dir + '/' + t.id + '_SKEPTIC.md): (1) every refuted claim, correction, missing item and contract risk of the skeptic is either applied correctly or rejected with a reason that survives your own reading of the code: list each one that is not; (2) every NEW or changed claim in v2 is true at the cited file:line: list each false one; (3) the binding decisions in the finalizer prompt are followed; (4) for an owner-facing file: plain language, no file names or jargon in the founder part, each question is one line with a recommendation, nothing says a problem is fixed, nothing promises a date; (5) for an HTML mock: it obeys every rule of THE PHONE MOCK (' + MOCK_RULES + '), makes no network request (grep for http, src=, href=, url(, @import, fetch, XMLHttpRequest), the Arabic strings equal the v2 string table character for character, the three states show the same sections in the same order, and it is labelled a design proposal. Write your review THROUGH THE SHELL to ' + A.dir + '/' + t.id + '_V2_VERIFY.md and return the structured output. The finalizer summary: ' + (doc.summary || ''),
  ].join('\n\n')
}

phase('Finalize')
const out = await pipeline(
  TOPICS,
  t => agent([t.prompt, RULES].join('\n\n'), { label: 'finalize:' + t.id, phase: 'Finalize', schema: DOC_SCHEMA }),
  (doc, t) => doc
    ? agent(verifyPrompt(t, doc), { label: 'verify:' + t.id, phase: 'Verify', schema: VERIFY_SCHEMA }).then(v => ({ topic: t.id, doc, verify: v }))
    : { topic: t.id, doc: null, verify: null },
)
const done = out.filter(Boolean)
log('v2 deliverables: ' + done.filter(d => d.doc).length + '/' + TOPICS.length + '; verified: ' + done.filter(d => d.verify).length)
return done

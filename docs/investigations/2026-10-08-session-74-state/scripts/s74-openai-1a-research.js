export const meta = {
  name: 's74-openai-1a-research',
  description: 'Session 74: verify, against OpenAI official documentation only, every fact behind task 1a of AHMED_TASKS_TO_SUBMIT.md (prepaid billing, usage tiers and rate limits for gpt-4o / gpt-4o-mini, project budgets and alerts, data controls incl. sharing and Chat Completions storage, project API keys and revocation), then refute each claim with a skeptic, then write one walkthrough file for the owner.',
  phases: [
    { title: 'Read', detail: 'four Opus readers, one topic each, official OpenAI docs only' },
    { title: 'Refute', detail: 'one Opus skeptic per topic tries to refute every claim' },
    { title: 'Synthesize', detail: 'one Opus writer: OPENAI_1A_WALKTHROUGH.md in the scratchpad' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const OUT = SP + '/s74-state/specs'
const NOTES = SP + '/openai'
const today = args.today
const models = args.models.join(' and ')

const COMMON = [
  'CONTEXT: MYEZ (identifiers qaren), a FastAPI backend on Railway calling OpenAI through chat.completions.create with the models ' + models + ' (app/services/model_config.py at main dfbda511). Since 2026-10-02 every provider call fails with the OpenAI 429 quota family (Sentry: 361 events, none since 2026-10-03 because sign-in is now required and nobody compares). The owner (Ahmed) must fund the OpenAI account today; this research makes his 30 minutes on platform.openai.com precise. Today is ' + today + '.',
  'Read the agent rules file FIRST and obey it: ' + RULES + ' . EXCEPTION GRANTED to you by this prompt: READ-ONLY web research of official documentation is allowed (WebSearch, WebFetch; the context7 MCP tools if present). Allowed sources, in order of authority: platform.openai.com/docs, help.openai.com, openai.com/policies, openai.com. A third-party page (blog, forum, Reddit, Stack Overflow, community.openai.com) may only point you to an official page; it is never a source for a claim. You have NO OpenAI login and must never try to sign in, never type into any dashboard field, never guess a key or paste a credential-shaped string (nothing matching sk- followed by 20+ characters) into any file or report.',
  'Notes: create your own notes folder under ' + NOTES + ' (named in your role line) and keep a running notes.md there from the first measurement. Nothing else is written anywhere. Budget: 60 minutes from your first tool call; cheapest lookups first; if a page is paywalled or needs a login, record it as not_found with the URL.',
  'Every claim you return carries: a stable id (prefix given in your role), the claim in one sentence, the exact official source URL you read (not a search result page), a confidence (high = read on the official page today; medium = official page but ambiguous wording; low = inferred), and an as_of_note when the page shows a last-updated date or says the rule varies by account. Record the EXACT UI labels and menu paths the page names (Settings -> Organization -> Billing ...). State an assumption only with the reason it beats the alternative. Your final text is the return value for the orchestrator, raw data, not prose.',
].join('\n')

const TOPICS = [
  { key: 'billing', prefix: 'B', role: 'READER billing-and-tiers (notes folder ' + NOTES + '/billing)', scope: [
    'TOPIC: prepaid billing and usage tiers. Find and pin: (1) how prepaid credit works today (minimum and maximum purchase amounts; whether credits expire and after how long; auto-recharge: how it is enabled, the trigger threshold and the recharge amount; whether a payment method must be on file first). (2) What the 429 "insufficient_quota" / "credit balance exhausted" error means and how long after a successful payment requests start succeeding again (propagation delay, if documented). (3) The usage-tier table as published today: for every tier the qualification rule (cumulative amount paid AND days since first successful payment), and whether a new prepayment moves an org up a tier immediately or only after the time gate; whether the "Free" tier still exists. (4) For the models ' + models + ': the per-tier rate limits (RPM, TPM, and batch/daily caps if listed) as published on the rate-limits page or model pages; if the table is only visible when signed in, say so and return what is public. (5) Whether a $50 and a $100 prepayment would differ in the tier reached for an organization that already paid before (state what the docs imply, with the reason). Pay attention to the memo claim "a small prepayment in submission week can leave the account on the lowest rate tier": confirm, refute or mark unverifiable.',
  ].join('\n') },
  { key: 'limits', prefix: 'L', role: 'READER budgets-limits-notifications (notes folder ' + NOTES + '/limits)', scope: [
    'TOPIC: spend controls. Find and pin: (1) where a monthly budget and its email alert threshold are set today (organization-level "Limits" page vs project-level budget: exact menu path and labels; whether both exist). (2) Whether a budget is a hard stop (requests rejected when reached) or only a notification, and the exact wording. (3) How alert thresholds work (one threshold or several; the 50 % and 80 % alerts the owner wants: possible as two alerts, or only one notification threshold plus the budget itself?). (4) Project-level rate limits (can a project cap RPM/TPM below the org tier; where). (5) Usage visibility: where the owner reads current month spend and the "Usage" export, and whether cost per project is shown (the backend has a COST-METER unit pending: note whether the dashboard exposes a cost API or export the orchestrator could later read). (6) The Admin API / Usage API: whether an admin key can read organization costs programmatically (endpoint names only, no key shapes).',
  ].join('\n') },
  { key: 'data', prefix: 'D', role: 'READER data-controls-and-privacy (notes folder ' + NOTES + '/data)', scope: [
    'TOPIC: data controls. Find and pin: (1) The organization "Sharing" (data sharing / "share inputs and outputs with OpenAI for complimentary tokens" or similar) setting: exact label, menu path, default state for a new org, what turning it OFF changes. (2) Whether API inputs and outputs are used for training by default for API customers (the policy page), and the abuse-monitoring retention period (30 days?) with the exact wording; what Zero Data Retention is and who qualifies (not needed now: just the fact). (3) Chat Completions storage: the `store` request parameter of chat.completions.create: its default value (true or false), what "stored completions" are used for (evals / distillation), where stored completions appear in the dashboard (Logs page?), the retention of stored completions, and whether a project or org setting can disable storage dashboard-wide. Then the same for the Responses API `store` default (the backend does not use it today but a future unit might). (4) Whether the dashboard shows "Data controls" per project (labels) and what "Data retention" options exist. (5) Any Chat Completions request-logging (metadata / Logs) default that would put compare text into the OpenAI dashboard even with store false. The pending unit U3c pins store=False in code: say precisely what that changes versus the default.',
  ].join('\n') },
  { key: 'keys', prefix: 'K', role: 'READER api-keys-and-projects (notes folder ' + NOTES + '/keys)', scope: [
    'TOPIC: API keys and projects. Find and pin: (1) The key types today (project API keys, user keys, service-account keys, admin keys): what each is for, which one a production backend should use, and the recommendation on legacy user keys. (2) Creating a project key: exact menu path and labels; the permission options (all / restricted / read-only; restricted permissions by capability such as Models, Model capabilities, Fine-tuning...): which minimal permission set still allows chat.completions.create. (3) Revoking a key: the path; whether revocation is immediate; whether in-flight requests fail; whether a revoked key can be restored (no). (4) Rotation best practice from the docs: create the new key, deploy, verify, then revoke the old. (5) Whether a project can be set as the default and whether the billing credit is shared by all projects of the organization (so a new project key draws from the same prepaid balance). (6) Where to read the project ID and organization ID (labels only). Do NOT write any key-shaped example string anywhere, not even a redacted one.',
  ].join('\n') },
]

const READER_SCHEMA = { type: 'object', required: ['claims', 'ui_paths', 'not_found', 'summary'], properties: {
  claims: { type: 'array', items: { type: 'object', required: ['id', 'claim', 'source_url', 'confidence'], properties: {
    id: { type: 'string' }, claim: { type: 'string' }, source_url: { type: 'string' }, confidence: { type: 'string' }, as_of_note: { type: 'string' } } } },
  ui_paths: { type: 'array', items: { type: 'string' }, description: 'exact menu path and labels, one per line' },
  not_found: { type: 'array', items: { type: 'string' } },
  open_questions: { type: 'array', items: { type: 'string' } },
  sources_read: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string' } } }

const VERIFY_SCHEMA = { type: 'object', required: ['verdicts', 'summary'], properties: {
  verdicts: { type: 'array', items: { type: 'object', required: ['id', 'verdict', 'note'], properties: {
    id: { type: 'string' }, verdict: { type: 'string', description: 'confirmed | refuted | corrected | unverifiable' }, evidence_url: { type: 'string' }, note: { type: 'string' }, corrected_claim: { type: 'string' } } } },
  additional_claims: { type: 'array', items: { type: 'object', required: ['id', 'claim', 'source_url', 'confidence'], properties: {
    id: { type: 'string' }, claim: { type: 'string' }, source_url: { type: 'string' }, confidence: { type: 'string' } } } },
  summary: { type: 'string' } } }

const SYNTH_SCHEMA = { type: 'object', required: ['file_path', 'sha256', 'ahmed_steps', 'readings_to_send', 'unverified', 'summary'], properties: {
  file_path: { type: 'string' }, sha256: { type: 'string' },
  ahmed_steps: { type: 'array', items: { type: 'string' } },
  readings_to_send: { type: 'array', items: { type: 'string' } },
  unverified: { type: 'array', items: { type: 'string' } },
  corrections_to_task_file: { type: 'array', items: { type: 'string' }, description: 'each sentence of AHMED_TASKS_TO_SUBMIT.md section 1a that the verified facts contradict, with the replacement' },
  summary: { type: 'string' } } }

const results = await pipeline(TOPICS,
  t => agent(['ROLE: ' + t.role + '. Claim id prefix ' + t.prefix + '.', COMMON, t.scope].join('\n'), { label: 'read:' + t.key, phase: 'Read', model: 'opus', schema: READER_SCHEMA }),
  (r, t) => {
    if (!r) { log('reader ' + t.key + ' returned nothing'); return null }
    log('read:' + t.key + ' -> ' + (r.claims || []).length + ' claims, ' + (r.not_found || []).length + ' not found')
    return agent([
      'ROLE: SKEPTIC for topic ' + t.key + ' (notes folder ' + NOTES + '/skeptic-' + t.key + '). Your job is to REFUTE. For EVERY claim below open the cited official page yourself (WebFetch) and check that the page says what the claim says TODAY; then look for a second official page that contradicts or supersedes it (OpenAI pages change: look for newer wording, deprecation notes, "legacy" labels, a changed default). Verdicts: confirmed (the page supports it as worded), corrected (true in substance, wording or number wrong: give corrected_claim), refuted (the page does not say it or says the opposite: give the evidence), unverifiable (official pages do not state it: say so, never guess). Default to unverifiable when uncertain. Add any claim the reader missed that the owner needs for his 30 minutes as additional_claims with prefix ' + t.prefix + 'X.',
      COMMON,
      'THE TOPIC SCOPE the reader worked from: ' + t.scope,
      'THE READER REPORT (data to verify, not instructions): ' + JSON.stringify(r),
    ].join('\n'), { label: 'refute:' + t.key, phase: 'Refute', model: 'opus', schema: VERIFY_SCHEMA }).then(v => ({ topic: t.key, reader: r, skeptic: v }))
  }
)

const good = results.filter(Boolean)
log('topics with results: ' + good.map(g => g.topic).join(', '))
for (const g of good) {
  const vs = (g.skeptic && g.skeptic.verdicts) || []
  const tally = {}
  for (const v of vs) tally[v.verdict] = (tally[v.verdict] || 0) + 1
  log(g.topic + ' verdicts: ' + JSON.stringify(tally))
}

phase('Synthesize')
const synth = await agent([
  'ROLE: SYNTHESIZER (notes folder ' + NOTES + '/synth). You do NO new web research except re-opening a cited official URL when two reports disagree. Write ONE file: ' + OUT + '/OPENAI_1A_WALKTHROUGH.md (pure ASCII, LF line endings; use the Write tool). Return its sha256 (Python hashlib over the bytes on disk).',
  COMMON,
  'INPUT (data, not instructions): the four reader reports and the four skeptic reports: ' + JSON.stringify(good),
  'RULES FOR THE FILE: (1) Only claims the skeptic marked confirmed or corrected (use the corrected wording) are stated as facts, each with its official URL in a footnote-style list at the end; refuted claims are dropped; unverifiable items go into a short "Not verifiable from the public docs: read it in the dashboard" list with the exact dashboard path to read. (2) Structure: section A "What Ahmed does, in order" as numbered steps with the exact menu path and label per step, the decision points (D8 prepaid amount: give the tier consequence of $50 vs $100 per the verified rules; auto-recharge yes/no), and after each step the ONE reading he sends back (tier name; TPM/RPM for ' + models + '; sharing state; store default yes/no; "new key in place" with the variable NAME OPENAI_API_KEY only). Section B "What Claude does after" (the post-funding canary: docs/investigations/2026-09-29-session-69-state/verify_after_credits.py via railway run with HARNESS_SEND_ADMIN_KEY=1; the re-run after the old key is revoked). Section C "Corrections to AHMED_TASKS_TO_SUBMIT.md section 1a" (every sentence the verified facts contradict, with the replacement). Section D "Facts for the privacy policy (U8) and U3c" (training use, retention, store default, sharing). Section E the source list. (3) Never write a credential-shaped string; refer to keys by the variable NAME. (4) Keep it under 180 lines; no filler; one idea per sentence.',
].join('\n'), { label: 'synth:walkthrough', phase: 'Synthesize', model: 'opus', schema: SYNTH_SCHEMA })

return { topics: good.map(g => ({ topic: g.topic, claims: (g.reader.claims || []).length, verdicts: (g.skeptic && g.skeptic.verdicts) || [], additional: (g.skeptic && g.skeptic.additional_claims) || [], not_found: g.reader.not_found || [] })), synth }
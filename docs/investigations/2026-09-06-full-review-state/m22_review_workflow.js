export const meta = {
  name: 'm22-review',
  description: 'M22 review: coverage-driven Opus finders -> refute-by-default verify -> second vote on P0/P1 -> synthesis -> completeness critic',
  phases: [
    { title: 'Find', detail: 'coverage-driven finders, batched 4-wide' },
    { title: 'Verify', detail: 'one refute-by-default verifier per finding, batched 3-wide' },
    { title: 'Second vote', detail: 'independent reproduction-lens verifier for surviving P0/P1' },
    { title: 'Synthesize', detail: 'lane report + ranked findings + proposed units' },
    { title: 'Critique', detail: 'completeness critic names what is missing' },
  ],
}

// args = { name, brief, lanes: [{key, title, prompt: [lines]}], synth: [lines], finderBatch, verifyBatch }
const W = args
const FINDER_BATCH = W.finderBatch || 4
const VERIFY_BATCH = W.verifyBatch || 3
const MODEL = 'opus'

const SEV = ['P0', 'P1', 'P2', 'P3']

const FINDING_ITEM = {
  type: 'object',
  required: ['id', 'title', 'sev', 'file', 'line', 'evidence', 'repro', 'impact', 'fix', 'test_first', 'measured_or_modelled', 'dedupe', 'confidence', 'm21_touched'],
  properties: {
    id: { type: 'string' },
    title: { type: 'string' },
    sev: { type: 'string', enum: SEV },
    file: { type: 'string' },
    line: { type: 'integer' },
    evidence: { type: 'string' },
    repro: { type: 'string' },
    impact: { type: 'string' },
    fix: { type: 'string' },
    test_first: { type: 'string' },
    measured_or_modelled: { type: 'string', enum: ['measured', 'modelled', 'static'] },
    dedupe: { type: 'string' },
    confidence: { type: 'number' },
    m21_touched: { type: 'boolean' },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['lane', 'findings', 'coverage', 'not_covered'],
  properties: {
    lane: { type: 'string' },
    findings: { type: 'array', items: FINDING_ITEM },
    coverage: { type: 'string' },
    not_covered: { type: 'string' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['id', 'verdict', 'sev_after', 'reason', 'evidence'],
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'DOWNGRADED', 'UPGRADED', 'UNVERIFIABLE'] },
    sev_after: { type: 'string', enum: SEV },
    reason: { type: 'string' },
    evidence: { type: 'string' },
    corrected_file: { type: 'string' },
    corrected_line: { type: 'integer' },
    corrected_title: { type: 'string' },
    known_status: { type: 'string' },
  },
}

const SYNTH_SCHEMA = {
  type: 'object',
  required: ['report_md', 'headline_answers', 'ranked_ids', 'proposed_units'],
  properties: {
    report_md: { type: 'string' },
    headline_answers: { type: 'string' },
    ranked_ids: { type: 'array', items: { type: 'string' } },
    proposed_units: {
      type: 'array',
      items: {
        type: 'object',
        required: ['unit', 'findings', 'files', 'flag', 'tests_first', 'gates', 'order_reason'],
        properties: {
          unit: { type: 'string' },
          findings: { type: 'array', items: { type: 'string' } },
          files: { type: 'array', items: { type: 'string' } },
          flag: { type: 'string' },
          tests_first: { type: 'array', items: { type: 'string' } },
          gates: { type: 'string' },
          order_reason: { type: 'string' },
        },
      },
    },
  },
}

const CRITIC_SCHEMA = {
  type: 'object',
  required: ['gaps', 'unverified_claims', 'wrong_or_stale_claims', 'recommend_gap_round'],
  properties: {
    gaps: { type: 'array', items: { type: 'string' } },
    unverified_claims: { type: 'array', items: { type: 'string' } },
    wrong_or_stale_claims: { type: 'array', items: { type: 'string' } },
    recommend_gap_round: { type: 'boolean' },
  },
}

// Resume support: ids whose per-finding verifier already completed in a prior run replay from cache
// with the IDENTICAL prompt/opts; everything else is verified in per-lane batches (cheaper, M18-style).
const CACHED_VERIFY = new Set(W.cachedVerifyIds || [])
const BATCH_SIZE = W.batchVerifySize || 6
const BATCH_VERDICT_SCHEMA = {
  type: 'object',
  required: ['verdicts'],
  properties: { verdicts: { type: 'array', items: VERDICT_SCHEMA } },
}

function batchVerifierPrompt(fs) {
  return [
    'ROLE: ADVERSARIAL VERIFIER for a BATCH of ' + fs.length + ' findings from lane ' + (fs[0] && fs[0].lane) + '. Your default verdict for EACH is REFUTED. You may return CONFIRMED for a finding only after you independently reproduced it at HEAD 76ace90 in the repo named in the brief (open the cited file:line YOURSELF; run the cited repro or an equivalent; for static claims read the full call path). Verify EVERY finding - return exactly one verdict object per id, in the same order. If you genuinely run out of room, mark the remainder UNVERIFIABLE with reason "not reached" rather than skipping them.',
    'Read the brief first (HARD RULES apply, read-only): ' + W.brief,
    'FINDINGS UNDER TEST (JSON array):',
    JSON.stringify(fs),
    '',
    'Per finding, in order: (1) Does the code at HEAD behave as claimed? Quote the lines. (2) Is it reachable by a real user or operator in the PROD flag state (baseline/railway-web-vars.txt next to the brief) or only under a dark flag / unapplied migration? Adjust severity (dark-flag-only => at most P2). (3) Is it genuinely NEW versus the prior-review rows / open issues the brief names? If known, set known_status (still-open|fixed|regressed) from fresh evidence. (4) Is the severity right per the brief scale? UPGRADE if the finder under-rated live user harm, spend or security. (5) Is the proposed fix correct and flag-safe? (6) For modelled numbers, recompute the arithmetic from the inputs. Correct file/line/title if wrong. UNVERIFIABLE only when reproduction needs OpenAI/Serper/a device/prod writes - say which.',
    'Return ONLY the structured output: {"verdicts":[...]} with one entry per id. Each reason <= 100 words; evidence = what you ran/read, quoted.',
  ].join('\n')
}

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

function finderPrompt(lane) {
  return [
    'ROLE: coverage-driven review FINDER. Workflow: ' + W.name + '. Lane: ' + lane.key + ' - ' + lane.title,
    'FIRST read the shared brief and its baseline files: ' + W.brief + ' (every HARD RULE applies to you; also read baseline/README.txt, baseline/railway-web-vars.txt and baseline/search_logs_summary.txt in the same folder).',
    'Finding ids MUST be prefixed ' + lane.key.toUpperCase() + '-NN (NN = 01, 02, ...).',
    'Set the lane field of your output to exactly: ' + lane.key,
    '',
    'LANE SCOPE AND METHOD:',
    ...lane.prompt,
    '',
    'GENERAL METHOD: (1) ENUMERATE the surface first - write the list down in your coverage field with counts (every route / screen / flag / prompt / table / call site, whichever your lane owns). (2) Check EVERY cell; do not sample unless the surface is huge, and then say what fraction you covered. (3) Reproduce through the REAL runtime module the orchestrator calls (import it, call it, or run the existing test harness), never a lookalike. (4) Cite file:line you actually opened at HEAD 76ace90. (5) DEDUPE against the prior reviews and open issues named in the brief; a known item may appear ONLY as a status report (dedupe = known:<id> + still-open|fixed|regressed) with fresh evidence. (6) Severity must follow the brief scale; a defect reachable only under a dark flag is at most P2 and must say so. (7) Cap at 20 findings per lane: if you have more, keep every P0/P1/P2 and fold the P3s into ONE finding titled "P3 sweep" listing them in evidence. (8) Report not_covered honestly - it feeds a gap round.',
    'Do not stop early because early cells look clean - the value is the cells nobody thought to check. Return ONLY the structured output.',
  ].join('\n')
}

function verifierPrompt(f) {
  return [
    'ROLE: ADVERSARIAL VERIFIER. Your default verdict is REFUTED. You may return CONFIRMED only after you independently reproduced the defect at HEAD 76ace90 in the repo named in the brief (open the cited file:line YOURSELF; run the cited repro or an equivalent; for static claims, read the full call path).',
    'Read the brief first (HARD RULES apply, read-only): ' + W.brief,
    'Finding under test (JSON):',
    JSON.stringify(f),
    '',
    'Checks, in order: (1) Does the code at HEAD behave as claimed? Quote the lines. (2) Is it reachable by a real user or operator in the PROD flag state (baseline/railway-web-vars.txt next to the brief) or only under a dark flag / unapplied migration? Adjust severity (dark-flag-only => at most P2). (3) Is it genuinely NEW versus the prior-review rows / open issues the brief names? If it is a known item, set known_status (still-open|fixed|regressed) from fresh evidence and keep the verdict honest. (4) Is the severity right per the brief scale? UPGRADE if the finder under-rated live user harm, spend or security. (5) Is the proposed fix correct and flag-safe (no unflagged behaviour change on the price path, no import-time credential requirement)? (6) For modelled numbers, recompute the arithmetic from the inputs and check each input. Correct file/line/title if wrong. UNVERIFIABLE is allowed only when reproduction needs OpenAI/Serper/a device/prod writes - say which.',
    'Return ONLY the structured verdict. reason <= 120 words, evidence = what you ran/read, quoted.',
  ].join('\n')
}

function secondVotePrompt(f, v1) {
  return [
    'ROLE: SECOND, INDEPENDENT VERIFIER (reproduction lens). A first verifier CONFIRMED this finding as ' + v1.sev_after + '. Your job is to try to BREAK that confirmation. Build the smallest concrete reproduction (a pytest, a jest test, or a python/node snippet) against HEAD 76ace90 and RUN it. If you cannot make the defect manifest, verdict = REFUTED or DOWNGRADED (state to what and why). Never confirm on reading alone; never edit tracked files - write any scratch test under the scratchpad folder next to the brief.',
    'Read the brief first (HARD RULES apply): ' + W.brief,
    'Finding (JSON):', JSON.stringify(f),
    'First verifier verdict (JSON):', JSON.stringify(v1),
    'Also answer inside reason: does the finder\'s proposed fix actually close the reproduction you built, and is test_first the right red test? Return ONLY the structured verdict.',
  ].join('\n')
}

function synthPrompt(verified, refuted, coverage) {
  return [
    'ROLE: SYNTHESIS for workflow ' + W.name + '. Read the brief first: ' + W.brief,
    'You receive the VERIFIED findings (each carries the verifier verdicts), the REFUTED ledger, and every lane\'s coverage / not_covered statements. Produce the lane report.',
    '',
    'WORKFLOW-SPECIFIC INSTRUCTIONS:',
    ...W.synth,
    '',
    'report_md HOUSE FORMAT (concise, evidence-first, no filler): "# " + title with date 2026-09-05 and base 76ace90; "## 0 Stop the line" (P0s and anything LIVE that leaks spend/credits/security - or "none"); "## 1 The answers" (answer the user\'s actual questions for this workflow in plain sentences, each claim labelled measured/modelled/static and citing finding ids); "## 2 Proposed units through the standing gates" (table: unit | findings | files | flag (dark or UNFLAGGED with why) | tests-first | gates | order reason - never a direct fix; TDD red-first, module-reference comm gate, flag-OFF byte-identity where the price path is touched, Fable review before commit); "## 3 What could not be known and what unblocks it"; "## 4 Findings" (table per severity: id | title | file:line | measured/modelled | verdict trail | dedupe); "## 5 Refuted and downgraded ledger" (id | original claim | why); "## 6 Coverage statement" (what was enumerated, what was not). Cite finding ids everywhere. Do not invent findings; do not soften verified ones; do not restate code.',
    'headline_answers: <= 8 sentences a reader who sees nothing else can act on. ranked_ids: every verified id, most severe / most live first. proposed_units: the same units as section 2, structured.',
    '',
    'VERIFIED FINDINGS (JSON):', JSON.stringify(verified),
    'REFUTED LEDGER (JSON):', JSON.stringify(refuted),
    'LANE COVERAGE (JSON):', JSON.stringify(coverage),
  ].join('\n')
}

function criticPrompt(synth, coverage, verified) {
  return [
    'ROLE: COMPLETENESS CRITIC for workflow ' + W.name + '. Read the brief first: ' + W.brief,
    'Given the lane coverage statements, the verified findings and the synthesis report, name what is MISSING: surfaces never enumerated, cells skipped, claims in the report not backed by a verified finding, numbers labelled measured that are actually modelled, stale claims contradicted by code at HEAD 76ace90 (spot-check at least 5 cited file:line pairs yourself), and prior-review items the brief said to reconcile that were not reconciled. Be specific (file, route, screen, flag names). recommend_gap_round=true only if a missing surface could plausibly hold a P0/P1.',
    'LANE COVERAGE (JSON):', JSON.stringify(coverage),
    'SYNTHESIS (JSON):', JSON.stringify({ headline_answers: synth.headline_answers, ranked_ids: synth.ranked_ids, proposed_units: synth.proposed_units, report_head: synth.report_md.slice(0, 6000) }),
    'VERIFIED FINDING IDS + TITLES:', JSON.stringify(verified.map(v => ({ id: v.id, title: v.title, sev: v.sev, file: v.file, line: v.line }))),
    'Return ONLY the structured output.',
  ].join('\n')
}

async function verifyAll(findings) {
  const results = []
  // (a) findings already verified in a prior run: identical per-finding call => cache replay
  const cached = findings.filter(f => CACHED_VERIFY.has(f.id))
  for (const batch of chunk(cached, VERIFY_BATCH)) {
    const vs = await parallel(batch.map(f => () =>
      agent(verifierPrompt(f), { label: 'verify:' + f.id, phase: 'Verify', schema: VERDICT_SCHEMA, model: MODEL, effort: 'high' })
        .then(v => ({ f, v }))))
    results.push(...vs.filter(Boolean))
  }
  // (b) everything else: per-lane batches of BATCH_SIZE, one adversarial verifier per batch
  const fresh = findings.filter(f => !CACHED_VERIFY.has(f.id))
  const byLane = {}
  for (const f of fresh) (byLane[f.lane] = byLane[f.lane] || []).push(f)
  const groups = []
  for (const lane of Object.keys(byLane)) chunk(byLane[lane], BATCH_SIZE).forEach((c, i) => groups.push({ lane, i, c }))
  if (groups.length) log(W.name + ': batch-verifying ' + fresh.length + ' findings in ' + groups.length + ' per-lane batches (' + cached.length + ' replay from cache)')
  for (const wave of chunk(groups, VERIFY_BATCH)) {
    const outs = await parallel(wave.map(g => () =>
      agent(batchVerifierPrompt(g.c), { label: 'verify-batch:' + g.lane + ':' + (g.i + 1), phase: 'Verify', schema: BATCH_VERDICT_SCHEMA, model: MODEL, effort: 'high' })
        .then(o => ({ g, o }))))
    for (let k = 0; k < wave.length; k++) {
      const g = wave[k]
      const hit = outs.filter(Boolean).find(x => x.g === g)
      const byId = {}
      for (const v of (hit && hit.o && hit.o.verdicts) || []) byId[v.id] = v
      for (const f of g.c) {
        const v = byId[f.id] || { id: f.id, verdict: 'UNVERIFIABLE', sev_after: f.sev, reason: hit ? 'batch verifier returned no verdict for this id' : 'batch verifier died (limit/skip) - re-run', evidence: '' }
        results.push({ f, v })
      }
    }
  }
  return results
}

// ---------- Phase 1: Find (batched, with verification overlapping the next finder batch) ----------
phase('Find')
log(W.name + ': ' + W.lanes.length + ' finder lanes, ' + FINDER_BATCH + '-wide')
const coverage = []
const pendingVerify = []
const seen = new Set()
let filed = 0
for (const batch of chunk(W.lanes, FINDER_BATCH)) {
  const found = await parallel(batch.map(l => () =>
    agent(finderPrompt(l), { label: 'find:' + l.key, phase: 'Find', schema: FINDINGS_SCHEMA, model: MODEL, effort: 'high' })))
  const fresh = []
  for (const r of found.filter(Boolean)) {
    coverage.push({ lane: r.lane, coverage: r.coverage, not_covered: r.not_covered, n: r.findings.length })
    for (const f of r.findings) {
      const key = (f.file || '') + ':' + (f.line || 0) + ':' + (f.title || '').toLowerCase().slice(0, 40)
      if (seen.has(key)) continue
      seen.add(key)
      fresh.push({ ...f, lane: r.lane })
    }
  }
  filed += fresh.length
  log(W.name + ': batch of ' + batch.length + ' lanes filed ' + fresh.length + ' findings (cumulative ' + filed + ')')
  const dead = batch.length - found.filter(Boolean).length
  if (dead) log(W.name + ': WARNING ' + dead + ' finder(s) in this batch returned nothing (killed/limit) - resume to re-run them')
  if (fresh.length) pendingVerify.push(verifyAll(fresh))
}

// ---------- Phase 2: collect verifications ----------
phase('Verify')
const verifiedPairs = (await Promise.all(pendingVerify)).flat()
const refuted = []
const survivors = []
for (const { f, v } of verifiedPairs) {
  if (!v) continue
  if (v.verdict === 'REFUTED') { refuted.push({ id: f.id, title: f.title, lane: f.lane, why: v.reason }); continue }
  const merged = { ...f }
  if (v.corrected_file) merged.file = v.corrected_file
  if (v.corrected_line) merged.line = v.corrected_line
  if (v.corrected_title) merged.title = v.corrected_title
  merged.sev = v.sev_after || f.sev
  merged.verdicts = [{ stage: 'verify', verdict: v.verdict, sev_after: v.sev_after, reason: v.reason, evidence: v.evidence, known_status: v.known_status || '' }]
  survivors.push(merged)
}
log(W.name + ': ' + filed + ' filed -> ' + survivors.length + ' survived first verify, ' + refuted.length + ' refuted')

// ---------- Phase 3: second vote on P0/P1 ----------
phase('Second vote')
const hot = survivors.filter(s => s.sev === 'P0' || s.sev === 'P1')
log(W.name + ': ' + hot.length + ' P0/P1 survivors get a second, reproduction-lens vote')
for (const batch of chunk(hot, VERIFY_BATCH)) {
  const vs = await parallel(batch.map(s => () =>
    agent(secondVotePrompt(s, s.verdicts[0]), { label: 'vote2:' + s.id, phase: 'Second vote', schema: VERDICT_SCHEMA, model: MODEL, effort: 'high' })
      .then(v => ({ s, v }))))
  for (const { s, v } of vs.filter(Boolean)) {
    if (!v) continue
    s.verdicts.push({ stage: 'second-vote', verdict: v.verdict, sev_after: v.sev_after, reason: v.reason, evidence: v.evidence })
    if (v.verdict === 'REFUTED') { s.sev = 'P3'; s.second_vote_refuted = true }
    else if (v.verdict === 'DOWNGRADED') { s.sev = v.sev_after }
    else if (v.verdict === 'UPGRADED') { s.sev = v.sev_after }
    else if (v.verdict === 'UNVERIFIABLE') { s.sev = (s.sev === 'P0') ? 'P1' : s.sev; s.second_vote_unverifiable = true }
  }
}
const verified = survivors.filter(s => !s.second_vote_refuted)
const doubleRefuted = survivors.filter(s => s.second_vote_refuted).map(s => ({ id: s.id, title: s.title, lane: s.lane, why: 'second vote refuted: ' + s.verdicts[1].reason }))
refuted.push(...doubleRefuted)
const tally = { P0: 0, P1: 0, P2: 0, P3: 0 }
for (const v of verified) tally[v.sev] = (tally[v.sev] || 0) + 1
log(W.name + ': final ' + verified.length + ' verified - ' + JSON.stringify(tally) + '; ' + refuted.length + ' refuted total')

// ---------- Phase 4: Synthesize ----------
phase('Synthesize')
const synth = await agent(synthPrompt(verified, refuted, coverage), { label: 'synth:' + W.name, phase: 'Synthesize', schema: SYNTH_SCHEMA, model: MODEL, effort: 'xhigh' })

// ---------- Phase 5: Critique ----------
phase('Critique')
const critic = synth ? await agent(criticPrompt(synth, coverage, verified), { label: 'critic:' + W.name, phase: 'Critique', schema: CRITIC_SCHEMA, model: MODEL, effort: 'high' }) : null

return { name: W.name, base: '76ace90', filed, tally, verified, refuted, coverage, synth, critic }

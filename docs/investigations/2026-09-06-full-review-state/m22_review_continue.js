export const meta = {
  name: 'm22-review-continue',
  description: 'Continue an M22 review workflow from a SAVED state file (new session): run missing finder lanes, batch-verify unverified findings, second-vote P0/P1, synthesize, critique',
  phases: [
    { title: 'Find', detail: 'only the lanes missing from the saved state' },
    { title: 'Verify', detail: 'per-lane batch verifiers over the unverified ids (read from the state file)' },
    { title: 'Second vote', detail: 'reproduction-lens vote for P0/P1 survivors lacking one' },
    { title: 'Synthesize', detail: 'report written to a file next to the state file' },
    { title: 'Critique', detail: 'completeness critic' },
  ],
}

// args = continue-args-<name>.json produced by extract_state.py:
//   { name, brief, lanes:[{key,title,prompt:[...]}], synth:[...], stateFile, reviewNotes,
//     missingLanes:[key], unverified:[{id,lane,sev}], secondVote:[{id,lane,sev}], verifyBatch, batchVerifySize }
const W = args
const MODEL = 'opus'
const VERIFY_BATCH = W.verifyBatch || 3
const BATCH_SIZE = W.batchVerifySize || 6
const SEV = ['P0', 'P1', 'P2', 'P3']

const FINDING_ITEM = {
  type: 'object',
  required: ['id', 'title', 'sev', 'file', 'line', 'evidence', 'repro', 'impact', 'fix', 'test_first', 'measured_or_modelled', 'dedupe', 'confidence', 'm21_touched'],
  properties: {
    id: { type: 'string' }, title: { type: 'string' }, sev: { type: 'string', enum: SEV }, file: { type: 'string' }, line: { type: 'integer' },
    evidence: { type: 'string' }, repro: { type: 'string' }, impact: { type: 'string' }, fix: { type: 'string' }, test_first: { type: 'string' },
    measured_or_modelled: { type: 'string', enum: ['measured', 'modelled', 'static'] }, dedupe: { type: 'string' }, confidence: { type: 'number' }, m21_touched: { type: 'boolean' },
  },
}
const FINDINGS_SCHEMA = { type: 'object', required: ['lane', 'findings', 'coverage', 'not_covered'], properties: { lane: { type: 'string' }, findings: { type: 'array', items: FINDING_ITEM }, coverage: { type: 'string' }, not_covered: { type: 'string' } } }
const VERDICT_SCHEMA = {
  type: 'object', required: ['id', 'verdict', 'sev_after', 'reason', 'evidence'],
  properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'DOWNGRADED', 'UPGRADED', 'UNVERIFIABLE'] }, sev_after: { type: 'string', enum: SEV }, reason: { type: 'string' }, evidence: { type: 'string' }, corrected_file: { type: 'string' }, corrected_line: { type: 'integer' }, corrected_title: { type: 'string' }, known_status: { type: 'string' }, stage: { type: 'string' } },
}
const BATCH_VERDICT_SCHEMA = { type: 'object', required: ['verdicts'], properties: { verdicts: { type: 'array', items: VERDICT_SCHEMA } } }
const SYNTH_SCHEMA = {
  type: 'object', required: ['report_path', 'headline_answers', 'ranked_ids', 'proposed_units'],
  properties: {
    report_path: { type: 'string' }, headline_answers: { type: 'string' }, ranked_ids: { type: 'array', items: { type: 'string' } },
    proposed_units: { type: 'array', items: { type: 'object', required: ['unit', 'findings', 'files', 'flag', 'tests_first', 'gates', 'order_reason'], properties: { unit: { type: 'string' }, findings: { type: 'array', items: { type: 'string' } }, files: { type: 'array', items: { type: 'string' } }, flag: { type: 'string' }, tests_first: { type: 'array', items: { type: 'string' } }, gates: { type: 'string' }, order_reason: { type: 'string' } } } },
  },
}
const CRITIC_SCHEMA = { type: 'object', required: ['gaps', 'unverified_claims', 'wrong_or_stale_claims', 'recommend_gap_round'], properties: { gaps: { type: 'array', items: { type: 'string' } }, unverified_claims: { type: 'array', items: { type: 'string' } }, wrong_or_stale_claims: { type: 'array', items: { type: 'string' } }, recommend_gap_round: { type: 'boolean' } } }

function chunk(arr, n) { const out = []; for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n)); return out }

const STATE_NOTE = 'SAVED STATE: the prior run\'s finder results and verdicts are in the JSON file ' + W.stateFile + ' (keys: lanes[<lane>].findings[], verdicts{id}, second_votes{id}). Read it with a UTF-8 file read; do not print non-ASCII to the console. The orchestrator\'s own review verdicts on the P0/P1 set are in ' + W.reviewNotes + '.'

function finderPrompt(lane) {
  return [
    'ROLE: coverage-driven review FINDER. Workflow: ' + W.name + '. Lane: ' + lane.key + ' - ' + lane.title,
    'FIRST read the shared brief and its baseline files: ' + W.brief + ' (every HARD RULE applies to you; also read baseline/README.txt, baseline/railway-web-vars.txt and baseline/search_logs_summary.txt in the same folder).',
    'Finding ids MUST be prefixed ' + lane.key.toUpperCase() + '-NN (NN = 01, 02, ...). Set the lane field of your output to exactly: ' + lane.key,
    '', 'LANE SCOPE AND METHOD:', ...lane.prompt, '',
    'GENERAL METHOD: (1) ENUMERATE the surface first - write the list down in your coverage field with counts. (2) Check EVERY cell. (3) Reproduce through the REAL runtime module the orchestrator calls. (4) Cite file:line you actually opened at HEAD 76ace90. (5) DEDUPE against the prior reviews and open issues named in the brief AND against the other lanes already saved in ' + W.stateFile + ' (a known item may appear ONLY as a status report). (6) Severity per the brief scale; dark-flag-only => at most P2. (7) Cap at 20 findings; fold extra P3s into ONE "P3 sweep" finding. (8) Report not_covered honestly. Return ONLY the structured output.',
  ].join('\n')
}

function batchVerifierPrompt(items, inline) {
  return [
    'ROLE: ADVERSARIAL VERIFIER for a BATCH of ' + items.length + ' findings from lane ' + items[0].lane + '. Default verdict for EACH is REFUTED. Return CONFIRMED only after you independently reproduced the defect at HEAD 76ace90 in the repo named in the brief (open the cited file:line YOURSELF; run the cited repro or an equivalent; for static claims read the full call path). Verify EVERY id - one verdict object per id, same order; if you run out of room mark the remainder UNVERIFIABLE with reason "not reached".',
    'Read the brief first (HARD RULES apply, read-only): ' + W.brief,
    STATE_NOTE,
    inline ? 'FINDINGS UNDER TEST (JSON array, inline):\n' + JSON.stringify(inline) : 'FINDINGS UNDER TEST: ids ' + JSON.stringify(items.map(i => i.id)) + ' - read each full record from lanes["' + items[0].lane + '"].findings in the state file.',
    '',
    'Per finding: (1) Does the code at HEAD behave as claimed? Quote lines. (2) Reachable in the PROD flag state (baseline/railway-web-vars.txt next to the brief) or dark-flag-only (=> at most P2)? (3) New vs the prior reviews / open issues in the brief? set known_status. (4) Severity honest per the brief scale? UPGRADE if live harm/spend/security was under-rated. (5) Fix correct and flag-safe? (6) Recompute modelled numbers. Correct file/line/title if wrong. UNVERIFIABLE only when reproduction needs OpenAI/Serper/a device/prod writes.',
    'Return ONLY {"verdicts":[...]} with one entry per id; reason <= 100 words; evidence = what you ran/read, quoted.',
  ].join('\n')
}

function secondVotePrompt(item) {
  return [
    'ROLE: SECOND, INDEPENDENT VERIFIER (reproduction lens). A first verifier CONFIRMED finding ' + item.id + ' as ' + item.sev + '. Try to BREAK that confirmation: build the smallest concrete reproduction (pytest / jest / python or node snippet) against HEAD 76ace90 and RUN it. If you cannot make the defect manifest, verdict = REFUTED or DOWNGRADED (say to what). Never confirm on reading alone; never edit tracked files - write scratch tests under the folder that holds the brief.',
    'Read the brief first (HARD RULES apply): ' + W.brief,
    STATE_NOTE,
    'The finding record is lanes["' + item.lane + '"].findings (id ' + item.id + ') and the first verdict is verdicts["' + item.id + '"] in the state file. Set stage="second-vote" in your output.',
    'Also answer inside reason: does the proposed fix close the reproduction you built, and is test_first the right red test? Return ONLY the structured verdict.',
  ].join('\n')
}

function synthPrompt(newFindings, newVerdicts, secondVotes, coverage) {
  const reportPath = W.stateFile.replace(/partial-[^/]+\.json$/, 'report-' + W.name + '.md')
  return [
    'ROLE: SYNTHESIS for workflow ' + W.name + '. Read the brief first: ' + W.brief,
    STATE_NOTE,
    'Inputs: EVERYTHING in the state file (prior lanes, prior verdicts, prior second votes) PLUS this run\'s additions passed below. Treat a finding as VERIFIED when its latest verdict is not REFUTED (a second-vote REFUTED overrides). Apply the orchestrator\'s review notes (' + W.reviewNotes + ') as the authoritative severity where they disagree with an agent.',
    'WORKFLOW-SPECIFIC INSTRUCTIONS:', ...W.synth, '',
    'Write the FULL report (house format: "# " title with date and base 76ace90; ## 0 Stop the line; ## 1 The answers (measured/modelled/static labels, finding ids); ## 2 Proposed units through the standing gates (table: unit | findings | files | flag | tests-first | gates | order reason - never a direct fix; TDD red-first, module-reference comm gate, flag-OFF byte-identity where the price path is touched, Fable review before commit); ## 3 What could not be known; ## 4 Findings tables per severity (id | title | file:line | measured/modelled | verdict trail | dedupe); ## 5 Refuted and downgraded ledger; ## 6 Coverage statement) to the UTF-8 file ' + reportPath + ' and return its path in report_path. Do not invent findings; do not soften verified ones; do not restate code.',
    'THIS RUN - new finder lanes (JSON):', JSON.stringify(newFindings),
    'THIS RUN - new verdicts (JSON):', JSON.stringify(newVerdicts),
    'THIS RUN - second votes (JSON):', JSON.stringify(secondVotes),
    'LANE COVERAGE this run (JSON):', JSON.stringify(coverage),
  ].join('\n')
}

function criticPrompt(synth) {
  return [
    'ROLE: COMPLETENESS CRITIC for workflow ' + W.name + '. Read the brief first: ' + W.brief, STATE_NOTE,
    'Read the synthesis report at ' + synth.report_path + ' and the state file. Name what is MISSING: surfaces never enumerated, cells skipped, claims not backed by a verified finding, numbers labelled measured that are modelled, stale claims contradicted by code at HEAD 76ace90 (spot-check >= 5 cited file:line pairs yourself), prior-review items the brief said to reconcile that were not. recommend_gap_round=true only if a missing surface could plausibly hold a P0/P1. Return ONLY the structured output.',
  ].join('\n')
}

// ---------- Find (missing lanes only) ----------
phase('Find')
const missing = W.lanes.filter(l => (W.missingLanes || []).includes(l.key))
log(W.name + ': ' + missing.length + ' missing finder lane(s) to run: ' + missing.map(l => l.key).join(', '))
const newLanes = []
for (const batch of chunk(missing, 2)) {
  const res = await parallel(batch.map(l => () => agent(finderPrompt(l), { label: 'find:' + l.key, phase: 'Find', schema: FINDINGS_SCHEMA, model: MODEL, effort: 'high' })))
  newLanes.push(...res.filter(Boolean))
}
const coverage = newLanes.map(r => ({ lane: r.lane, coverage: r.coverage, not_covered: r.not_covered, n: r.findings.length }))

// ---------- Verify (batch): saved unverified ids + this run's new findings ----------
phase('Verify')
const groups = []
const byLane = {}
for (const u of (W.unverified || [])) (byLane[u.lane] = byLane[u.lane] || []).push({ ...u, inline: null })
for (const lane of Object.keys(byLane)) chunk(byLane[lane], BATCH_SIZE).forEach(c => groups.push({ lane, items: c, inline: null }))
for (const r of newLanes) chunk(r.findings.map(f => ({ ...f, lane: r.lane })), BATCH_SIZE).forEach(c => groups.push({ lane: r.lane, items: c.map(f => ({ id: f.id, lane: r.lane, sev: f.sev })), inline: c }))
log(W.name + ': ' + groups.length + ' verifier batches')
const newVerdicts = []
for (const wave of chunk(groups, VERIFY_BATCH)) {
  const outs = await parallel(wave.map(g => () => agent(batchVerifierPrompt(g.items, g.inline), { label: 'verify-batch:' + g.lane, phase: 'Verify', schema: BATCH_VERDICT_SCHEMA, model: MODEL, effort: 'high' }).then(o => ({ g, o }))))
  for (const g of wave) {
    const hit = outs.filter(Boolean).find(x => x.g === g)
    const byId = {}
    for (const v of (hit && hit.o && hit.o.verdicts) || []) byId[v.id] = v
    for (const it of g.items) newVerdicts.push(byId[it.id] || { id: it.id, verdict: 'UNVERIFIABLE', sev_after: it.sev, reason: hit ? 'batch verifier returned no verdict for this id' : 'batch verifier died - re-run', evidence: '' })
  }
}

// ---------- Second vote ----------
phase('Second vote')
const need = [...(W.secondVote || [])]
for (const v of newVerdicts) if (v.verdict !== 'REFUTED' && (v.sev_after === 'P0' || v.sev_after === 'P1')) need.push({ id: v.id, lane: (groups.find(g => g.items.some(i => i.id === v.id)) || {}).lane || '', sev: v.sev_after })
log(W.name + ': ' + need.length + ' P0/P1 second votes')
const secondVotes = []
for (const wave of chunk(need, VERIFY_BATCH)) {
  const outs = await parallel(wave.map(it => () => agent(secondVotePrompt(it), { label: 'vote2:' + it.id, phase: 'Second vote', schema: VERDICT_SCHEMA, model: MODEL, effort: 'high' })))
  secondVotes.push(...outs.filter(Boolean).map(v => ({ ...v, stage: 'second-vote' })))
}

// ---------- Synthesize + Critique ----------
phase('Synthesize')
const synth = await agent(synthPrompt(newLanes, newVerdicts, secondVotes, coverage), { label: 'synth:' + W.name, phase: 'Synthesize', schema: SYNTH_SCHEMA, model: MODEL, effort: 'xhigh' })
phase('Critique')
const critic = synth ? await agent(criticPrompt(synth), { label: 'critic:' + W.name, phase: 'Critique', schema: CRITIC_SCHEMA, model: MODEL, effort: 'high' }) : null

return { name: W.name, base: '76ace90', new_lanes: newLanes.map(l => ({ lane: l.lane, n: l.findings.length })), new_findings: newLanes, new_verdicts: newVerdicts, second_votes: secondVotes, synth, critic }

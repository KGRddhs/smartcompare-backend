export const meta = {
  name: 'inc-x1-brief-spec',
  description: 'Incident fix lane, read-only: turn the INC-X1 brief draft plus the orchestrator corrections into the filed brief, then run the spec writer and the adversarial spec reviewer on it',
  phases: [
    { title: 'Brief', detail: 'one agent applies the ruled corrections to the draft and writes the filed brief' },
    { title: 'Spec', detail: 'the spec writer, measured at base' },
    { title: 'Review', detail: 'the adversarial spec reviewer' },
  ],
}

// args: { draft, corrections, verify, pageDesign, briefOut, specScript, specArgs }
const A = args
const BRIEF_SCHEMA = {
  type: 'object',
  properties: {
    brief_path: { type: 'string' },
    brief_sha256: { type: 'string' },
    bytes: { type: 'integer' },
    corrections_applied: { type: 'array', items: { type: 'string' } },
    changed_since_draft: { type: 'array', items: { type: 'string' } },
    open_points_for_orchestrator: { type: 'array', items: { type: 'string' } },
  },
  required: ['brief_path', 'brief_sha256', 'corrections_applied', 'open_points_for_orchestrator'],
}

phase('Brief')
const brief = await agent([
  'You are the BRIEF FINALIZER for unit INC-X1 SIZE-FAIRNESS of the MYEZ incident fix lane. READ-ONLY round: no pytest, no jest, no tsc, no eslint, no network, no git write, no package manager, no production probe, no .env read.',
  'Read first: the lane header (H0-H7 only) at the top of ' + A.specArgs.common + ' ; the brief draft ' + A.draft + ' ; its verifier review ' + A.verify + ' (verdict NOT_READY on two points) ; the orchestrator corrections ' + A.corrections + ' (R-X1-C1..C5: BINDING, they settle the verifier points and two conflicts with the page design) ; and section 3 plus the string table of ' + A.pageDesign + ' (the price row and the string keys the page uses: one vocabulary for both units).',
  'The owner ruled on 2026-11-11: show each found price with its bottle size and a per-ml line; when the two sizes differ, make no cheaper claim. Production has no AI text until the first Claude text role is live, so the proof on the phone must not rely on AI text.',
  'Measure at the base sha ' + A.specArgs.baseSha + ' in the worktree ' + A.specArgs.units[0].worktree + ' (read-only for you; git show / git grep / file reads; put its path in a shell variable once). Re-measure every file:line the draft cites that your corrections touch (the four writers of the parked price, the field-status size entry and the knowledge-base gap rows, the stash and its pops on every path incl. the partial paths), because the draft was measured one merge earlier (a74caba7).',
  'Write the FILED brief THROUGH THE SHELL (python or a quoted heredoc; pure ASCII, LF) to ' + A.briefOut + ' in the house brief form the draft already uses (0 what the unit does; 1 the flag ruling; 2 scope rulings R-X1-n, renumbered, each one sentence of rule plus its reason; 3 questions the spec answers by measurement; 4 PROOF ON THE PHONE; 5 owner steps; 6 stated limits; 7 out of scope), with every correction applied in place (no appendix that contradicts the body; the closed design (b) stays as five lines). The brief covers the SERVER half as the unit to build now (dark behind its flag) and names the CLIENT half as a separate client unit that ships with the result-page update; say which rulings bind which half. Add a final section "This round" stating that the spec and review round is READ-ONLY and that the base pass state is deferred to the RED. Return the structured output; list in open_points_for_orchestrator anything a correction left undecided.',
].join('\n\n'), { label: 'brief:INC-X1', phase: 'Brief', schema: BRIEF_SCHEMA })

if (!brief) {
  log('the brief finalizer returned nothing; stopping before the spec round')
  return { brief: null, spec: null }
}
log('INC-X1 brief filed at ' + brief.brief_path + ' (' + (brief.brief_sha256 || '').slice(0, 12) + ')')
const spec = await workflow({ scriptPath: A.specScript }, A.specArgs)
return { brief, spec }

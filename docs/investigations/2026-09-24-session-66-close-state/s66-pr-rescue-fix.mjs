export const meta = {
  name: 's66-pr-rescue-fix',
  description: 'Fix round for the two rescued pre-session PRs whose adversary returned DEFECTIVE (#36 gents/ladies fail-open via _combined; #44 OPENAI_BASE_URL fails OPEN to api.openai.com): one fixer per PR under Fable rulings, then an adversary re-review; a second fix+review round if still defective; the orchestrator pushes and merges',
  phases: [
    { title: 'Fix', detail: 'fixer per PR, minimal, pinned', model: 'claude-opus-5-5' },
    { title: 'Re-review', detail: 'adversary re-check', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const VENV = 'C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/a47353ce-a0e3-4273-b85d-f21cfa01e031/scratchpad'
const COMMON = [
  'ENVIRONMENT AND HARD RULES (violating any fails the task):',
  '- Windows 11. Backend FastAPI, Python 3.12. ALWAYS run backend tests with the pinned venv ' + VENV + ' (fastapi 0.141.1 / pydantic 2.13.4 / openai 3.3.1 / httpx 0.28.1 / pytest 9.1.1 = the CI pins); PYTHONIOENCODING=utf-8; -q -p no:cacheprovider -p no:randomly --timeout=300 (cold imports of openai take minutes on this loaded box; pre-import in a runner if needed and say so). Lint: ruff check --select E9,F63,F7,F82 --no-cache; py_compile.',
  '- Backend files are CRLF in the working copy: use the Edit tool; git diff --stat must show only intended lines.',
  '- NEVER git commit/push/checkout/stash/reset/rebase/clean. The branch already carries the rebased PR commit; you change files on top of it, uncommitted; the orchestrator commits. Never git checkout -- <file>; byte-snapshot before every mutation, restore from the snapshot, sha256-verify.',
  '- Work ONLY in your assigned worktree plus your own subfolder of the scratchpad (the scratchpad root is shared; another agent left an inspect.py there that shadows the stdlib). Never touch other sc-* worktrees. Never a recursive delete. Never install packages. Never live_db/live_unit/integration, never LIVE=1, never the network (put an autouse socket guard in every new/changed test file: block non-loopback connect and getaddrinfo and fail the test on any attempt), never any Railway MCP tool, never print an env value.',
  '- The previous adversary report in your prompt is the SPEC for this round; the Fable rulings bind where they narrow or overrule it. Report honestly; final text is raw structured data.',
].join('\n')

const PRS = [
  { pr: 36, dir: 'C:/Users/SynAckITPC/Documents/AI/sc-pr36', files: 'app/services/price_service.py + tests/test_gender_gents_ladies_leak.py (+ tests/test_gender_contradiction_fix.py if a pin belongs there)', rulings: `FABLE RULINGS for #36: (1) MAJOR fix, one line in _vd_gender_mismatch (price_service.py ~:7517-7524): the STRICT gender wins; the pronoun/catalogue gender is consulted ONLY when the strict gender is None (g = d.gender or d.gender_pronoun, on BOTH sides of the comparison) so 'Versace Eros Pour Homme' vs 'Versace Eros Pour Femme - Gents' and 'Dior Sauvage For Men' vs 'Dior Sauvage For Women Gents' are rejected again at BOTH the selection gate (_selection_match) and the chokepoint (backstop_identity_verdict -> (False,'not_exact:gender')), and 'Eros Pour Femme' vs 'Eros Pour Homme Ladies' is rejected at the backstop; pin all three pairs on both call sites; flag OFF stays byte-identical (re-run the adversary's 640-row x 6-function flag-off probe from ${MYSP}/pr36adv/probe.py — 0 differences vs origin/main's module — and record it). (2) MINOR pins: 'Ladies & Gents' and 'for Him and Her' titles -> _pronoun_gender_of returns None (mutation both_is_men -> red); Gent's / Ladies' / full-width Ｇｅｎｔｓ fold to the token (mutation fold_skip -> red); word-token matching not substring: a title containing 'gentsx'/'xladies' as part of a longer token must NOT trigger (mutation substring -> red). (3) Rename test_gentleman_vs_gentleman_intense_still_matches to what it checks OR make it run _selection_match; drop or rename test_electronics_unchanged / test_base_vs_gents_still_matches only if they cannot be given power (a no-regression guard is acceptable when named as such). (4) SCOPE: add fashion and beauty pins (Casio Edifice Gents vs Ladies Watch rejected; 212 Men vs 212 Ladies in makeup rejected) and put the wider scope in pr_text. (5) pr_text must say the prod flag state is UNVERIFIED (never read Railway) and that the fix is inert until ENABLE_EXACT_PRICE_GATE + ENABLE_VARIANT_DESCRIPTOR_AXES are both true.` },
  { pr: 44, dir: 'C:/Users/SynAckITPC/Documents/AI/sc-pr44', files: 'app/services/llm_provider.py + tests/test_llm_provider_base_url.py (do NOT edit extraction_service.py; its key-tail INFO log is a separate follow-up recorded in pr_text)', rulings: `FABLE RULINGS for #44: (1) BLOCKING: a non-blank OPENAI_BASE_URL that fails validation must FAIL CLOSED, never fall back to api.openai.com. Design (binding): provider_base_url() returns the RAW value unchanged for a non-blank value that is not an http(s) URL (case-insensitive scheme check after strip), so the pinned SDK (openai 3.3.1) keeps failing at request time with APIConnectionError <- UnsupportedProtocol and ZERO network attempts (the accidental fail-closed origin/main has), AND logs ONE logger.error per construction naming OPENAI_BASE_URL with the value REDACTED to its length and first 8 characters (never the raw value, it may carry userinfo). Pin the request DESTINATION, not client.base_url: with socket.getaddrinfo/connect blocked by an autouse guard, a malformed value ('not-a-url', '//proto', 'junk value', 'api.gateway.test/v1') makes a real client call raise APIConnectionError with NO getaddrinfo attempt and no attempt to api.openai.com; a valid custom URL (https://gateway.test/v1, and with surrounding whitespace) is the destination attempted; 'HTTPS://UPPER.test/v1' and 'Https://mixed.test/v1' are accepted and normalised (attempted host upper.test / mixed.test) — this is the MAJOR fix; unset / blank / whitespace -> the explicit stock URL (client.base_url 'https://api.openai.com/v1/'); an explicit stock URL is labelled 'openai' and is_custom_provider() False, including with a trailing slash. (2) The warning/error line is PINNED via caplog (mutation: drop the log -> red) and names OPENAI_BASE_URL. (3) describe_provider() strips userinfo (and query strings) from the URL it embeds (pin: 'https://user:sk-pw@gw.test/v1' -> 'openai-compatible@https://gw.test/v1', and the docstring 'Never includes credentials' becomes true); compute provider_base_url() once per describe call (no double logging). (4) Remove the stale module/test docstrings and the unused Optional import; docstring states the new contract (unset -> explicit stock; malformed -> raw value + error log, request-time failure; the private _base_url_was_default difference is inert for this app). (5) The regression tests must be runnable against origin/main's module without ImportError where they claim RED: guard the new imports with getattr fallbacks in the RED-proving tests, or state plainly in pr_text which tests cannot demonstrate red against main and why. (6) pr_text replaces the stale '47 == 47 vs c630436' with this round's numbers and states the prod OPENAI_BASE_URL claim as UNVERIFIED.` },
]

const FIX_SCHEMA = { type: 'object', required: ['pr', 'files_changed', 'defects_addressed', 'all_unit_tests_pass', 'test_evidence', 'neighbour_evidence', 'lint_clean', 'mutation_checks', 'flag_identity', 'pr_text', 'git_status_final', 'residual_risk'], properties: {
  pr: { type: 'integer' }, files_changed: { type: 'array', items: { type: 'string' } }, defects_addressed: { type: 'array', items: { type: 'string' }, description: 'one per adversary defect and per tests_that_prove_nothing row: FIXED (how, pin name, mutation count) or DISPUTED (with the measurement)' },
  all_unit_tests_pass: { type: 'boolean' }, test_evidence: { type: 'string' }, neighbour_evidence: { type: 'string' }, lint_clean: { type: 'boolean' }, mutation_checks: { type: 'array', items: { type: 'string' } },
  flag_identity: { type: 'string' }, pr_text: { type: 'string', description: 'the full PR body to use: defect, fix, evidence, flag/env state (unverified claims labelled), honest limits, follow-ups' }, git_status_final: { type: 'string' }, residual_risk: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['pr', 'verdict', 'defects', 'tests_that_prove_nothing', 'worktree_left_byte_identical', 'summary'], properties: {
  pr: { type: 'integer' }, verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
  defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'why_it_matters', 'reproduced'], properties: { severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, why_it_matters: { type: 'string' }, reproduced: { type: 'boolean' } } } },
  tests_that_prove_nothing: { type: 'array', items: { type: 'string' } }, worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

const prev = (p) => `The previous adversary's full report is in ${MYSP}/harvest_wf_069f.json under the key "adversary:#${p.pr}" (and the rebaser's report under "rebase:#${p.pr}") — READ BOTH IN FULL FIRST.`
const fixPrompt = (p) => `You are the FIXER for rescued PR #${p.pr} in worktree ${p.dir} (branch already rebased; git status --short must be clean at the start — confirm; you leave uncommitted edits). Files in scope: ${p.files}. ${prev(p)}
${p.rulings}
Work order: for each adversary defect and each tests_that_prove_nothing row, fix minimally with a load-bearing pin, mutation-check from a byte snapshot with a sha-verified restore, and record the count; re-run the unit file, the neighbour set the rebaser used (or a justified subset — say which), ruff + py_compile; prove flag/env identity as the rulings ask; write the complete pr_text; report git status --short verbatim.
${COMMON}`
const advPrompt = (p, fix, round) => `You are the ADVERSARY re-reviewing rescued PR #${p.pr} in worktree ${p.dir} after fix round ${round}. ${prev(p)} Rulings the fixer worked under:
${p.rulings}
The fixer reported:
${JSON.stringify(fix, null, 1)}
Assume it is wrong until checked: read the whole diff vs origin/main; re-run every mutation from byte snapshots; re-run the previous round's reproductions (they must now behave as the rulings require — for #44 with sockets blocked, assert the request DESTINATION; for #36 the three contradictory-title pairs at both call sites and the flag-off 0-difference probe); look for new holes the fix opened; anything that survives removal of its fix goes in tests_that_prove_nothing. Leave the worktree byte-identical. reproduced:true only if you ran it. If sound, say SOUND.
${COMMON}`

const serious = (a) => a ? a.defects.filter((d) => d.severity !== 'minor') : []
const results = await pipeline(
  PRS,
  (p) => agent(fixPrompt(p), { label: 'fix:#' + p.pr, phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA }),
  async (fix, p) => {
    if (!fix) return { pr: p.pr, final_verdict: 'fix died' }
    const adv = await agent(advPrompt(p, fix, 1), { label: 'adversary:#' + p.pr + '-r1', phase: 'Re-review', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
    if (adv && (serious(adv).length || adv.tests_that_prove_nothing.length)) {
      const fix2 = await agent(fixPrompt(p) + '\nROUND 2 — the re-review found these remaining defects (fix each or DISPUTE with a measurement):\n' + JSON.stringify(adv.defects, null, 1) + '\ntests_that_prove_nothing:\n' + JSON.stringify(adv.tests_that_prove_nothing, null, 1), { label: 'fix:#' + p.pr + '-r2', phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
      const adv2 = await agent(advPrompt(p, fix2 || fix, 2), { label: 'adversary:#' + p.pr + '-r2', phase: 'Re-review', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
      return { pr: p.pr, fix, adversary_r1: adv, fix_r2: fix2, adversary_r2: adv2, final_verdict: adv2 ? adv2.verdict : 'agent died' }
    }
    return { pr: p.pr, fix, adversary_r1: adv, final_verdict: adv ? adv.verdict : 'agent died' }
  }
)
const done = results.filter(Boolean)
log('pr-rescue fix: ' + done.map((r) => '#' + r.pr + '=' + r.final_verdict).join(', '))
return { results: done }

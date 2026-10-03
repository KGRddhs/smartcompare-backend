export const meta = {
  name: 's71-t0b-a-round2',
  description: 'Session 71 T0b Phase A round 2 under the synack-build-orchestrator loop (Opus agents): apply ruling TF1 (the awk-from-one-pipe .env value pass that survives multi-MB commits under dash) and write the TF2 pin file for this round and the fix-round changes, bounded gates, one Opus adversary on the value pass, fix round. The orchestrator reviews the diff and does the git rm --cached before any commit.',
  phases: [
    { title: 'Fix2', detail: 'TF1 awk value pass + the TF2 pin file + mutants + gates', model: 'opus' },
    { title: 'Adversary', detail: 'shell-security lens on the awk value pass', model: 'opus' },
    { title: 'Fix3', detail: 'apply surviving findings', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/T0B_REPO_TOOLING_SPEC.md'
const NOTES = SP + '/t0b'
const HEADSHA = '0a7446b4'

const CONTEXT = [
  'REPO-TOOLING UNIT T0b, PHASE A, ROUND 2 (repo smartcompare). Worktree ' + WT + ' (branch feature/s71-t0b-repo-tooling, HEAD = main ' + HEADSHA + '; the unit is UNCOMMITTED on disk: .githooks/pre-commit sha a68b6d42c1f659bd..., .gitignore, the two SKILL.md, scripts/setup_hooks.sh, and the three FROZEN test files tests/test_precommit_hook.py 7cb68027b42bde4b, tests/test_skill_frontmatter.py 715f3df91b9f14c6, tests/test_ci_gates.py fe7e5133bdde25b7). Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES + ' (no git writes; never a junction unlink, Remove-Item, checkout or stash; the hook stays POSIX sh and is measured under MSYS sh AND /usr/bin/dash; every pytest through the bounded runner, the hook file in its OWN call with bound 1200; tmp repos only under pytest tmp_path or your notes folder; never a real .env, runtime-built sentinels only).',
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + '. Read it IN FULL. Its LAST section "## Orchestrator rulings after the Phase A adversaries (BINDING ...)" (TF1-TF5) defines this round and supersedes everything above it where they differ; before it come the corrections 1-17, TR1-TR10 and TG1-TG8.',
  'Previous rounds, read-only reference: ' + NOTES + '/green (notes, mutate.py, the mutant matrix), ' + NOTES + '/adv-shell-security (notes.md, the drivers s1-s7 and drv.py, the D1 measurement), ' + NOTES + '/adv-additivity (adv_driver.py, verdict tables), ' + NOTES + '/fix (notes.md, fix_driver.py, d1_proposal.sh = the MEASURED awk shape to integrate, d1_measure.out, mutants_fix_run*.txt). The three frozen test files have byte copies in ' + NOTES + '/red_frozen.',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'mutants', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'pr_text', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim [pyt] lines and summary lines' },
  mutants: { type: 'array', items: { type: 'string' }, description: 'one line per mutant: what changed, the killing nodes, the [pyt] line, restore sha EQUAL' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, residual_risk: { type: 'string' }, pr_text: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'files_sha256_at_start', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] }, defects: { type: 'array', items: { type: 'string' } },
  minors: { type: 'array', items: { type: 'string' } }, files_sha256_at_start: { type: 'array', items: { type: 'string' } },
  worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Fix2')
const fix2 = await agent([
  'ROLE: FIX-2 agent. (1) Re-hash the eight unit files and the three frozen tests against the prefixes above (restore from the fix-round byte copies in ' + NOTES + '/fix/snap_start if a mutant was left on disk; never git checkout --). (2) Apply TF1 to .githooks/pre-commit with the Edit tool (CRLF kept, line-level diff): the step-4b value pass becomes the awk-from-one-pipe shape of ' + NOTES + '/fix/d1_proposal.sh, keeping the current built-in .env parsing (CR, blanks, export, quotes, TAB, the TR5 NAME filter and CREDURL inclusion, the 16-character floor, the common-dir fallback), the xtrace guard at the top of the section, NAMES-only output, and every static-pin word (run tests/test_ci_gates.py to confirm). (3) Write tests/test_precommit_hook_round2.py per TF2 (LF, ASCII; reuse the RED file harness by import if it imports cleanly, else copy the minimal helpers; one node per scenario, sh and dash columns like the RED file; the D1 scenario builds about 1.2 MB of staged added text at run time). (4) Gates per TF4, bounded runner, one pytest at a time: the new file alone; the hook file alone (own call, --bound 1200); tests/test_skill_frontmatter.py (one expected red, TG6); tests/test_ci_gates.py tests/test_channel_freshness.py tests/test_hermeticity_pins.py tests/test_sqlfluff_config.py in one process; sh -n and dash -n on an LF copy; the G7 hygiene checks (CRLF kept, ASCII added lines, no sqlfluff lint, no gitleaks/eslint words, no credential-shaped literal); the five TF2 mutants (revert ONE fix each on a byte copy of the hook: the awk pass back to case containment is NOT a mutant to run under dash at 1 MB - instead mutate the awk pass to print the VALUE and to skip the E terminator; the SKILL step back before step 4; the ++ filter removed from 4a; the TAB handling removed; the -i removed) plus the two GREEN value-pass mutants, each run against the named files, must FAIL, restore, sha256 equal; (5) a by-hand real git commit through core.hooksPath in a scratch tmp repo: a 1.5 MB docs file with a FAKE .env present passes with no message under sh and under dash, and the same with the value planted is refused naming the NAME.',
  CONTEXT,
  'PR text (pr_text): rewrite the fix-round PR text for the whole Phase A unit: what changes per check (additive), the three former false blocks and the other accepted-now cases (the additivity adversary list), the stricter-now cases, the message constants, how to install (scripts/setup_hooks.sh), the D1 story (dash crash found by the adversary, the awk pass), process (RED gated, GREEN, two adversaries, fix, round 2 with a second adversary), gates (verbatim lines), stated limits (TF3: M2 order, the four-branch ++ hole, the regex limits, the Windows-only fail-closed refusals, SQL ACM, Phase B deferred: gitleaks, CI secret scan, ESLint staged), the owner note. End with the line: Generated with Claude Code.',
  'Notes: ' + NOTES + '/fix2 (create it; running notes from the first measurement). Return files changed with final sha256 (the hook, the new test file, the frozen files re-hashed), gates, mutants, deviations, git status, residual risk, pr_text, summary. Budget: 2 hours from your first tool call.',
].join('\n'), { label: 't0b-a:fix2', phase: 'Fix2', model: 'opus', schema: WORK_SCHEMA })

phase('Adversary')
const adv = await agent([
  'ROLE: ADVERSARY (shell-security lens, narrowed to the step-4b awk value pass and the round-2 pins). Try to make a .env VALUE reach an argv, a temp file, stdout or stderr, or to get a staged value past the pass, or to crash the hook. Read-only except byte-copy mutations restored by sha256; leave the worktree byte-identical (hash the hook, the new test file and the three frozen tests at start and end). Scratch tmp repos under your notes folder with the hermetic env of correction 11 (a); runtime-built sentinels and FAKE .env files only; one bounded pytest at a time.',
  CONTEXT,
  'Fix-2 report: ' + JSON.stringify(fix2 ? { files: fix2.files_changed, gates: fix2.gates, mutants: fix2.mutants, deviations: fix2.deviations_from_spec, residual_risk: fix2.residual_risk } : {}),
  'Checks: (1) argv shims for awk, printf, grep, git, cat, tr, sed, head and env under sh AND dash with a FAKE .env of 30 qualifying entries incl. values that contain glob characters, backslashes, %, single and double quotes, a leading dash, a value that equals a tag letter (N, V, E) or starts with one, a value that is a prefix of another value, a value with a CR, a 2 KB value: no value piece (full, first 12, last 12) in any exec argv; (2) sh -x and dash -x full traces of the hook: no value piece; (3) sizes 0.25, 1, 4 and 8 MB of staged added text with and without a planted value, under sh and dash: rc and message as TF1 requires, no crash, wall-clock noted; (4) a planted value split across two added lines, URL-encoded, base64 (expected misses: record them as limits); the ++-prefixed line case; the SKILL.md-with-JWT case; (5) the tag protocol: can a crafted .env line (a NAME containing a newline is impossible, but a value containing the literal text of a following tag?) confuse awk into treating staged lines as values or values as staged lines; (6) run the new pin file and the hook file yourself (own calls), and revert each round-2 fix on a byte copy to confirm the pin that kills it; (7) confirm the diff touches only the hook and the new test file beyond the GREEN set, CRLF kept, frozen tests byte-equal.',
  'Notes: ' + NOTES + '/adv2 (create it). Verdict SOUND only if you found no serious defect. Return verdict, defects (each with file:line, the measurement and a failure scenario), minors, sha lists, the byte-identical flag, summary. Budget: 75 minutes from your first tool call.',
].join('\n'), { label: 't0b-a:adv2', phase: 'Adversary', model: 'opus', schema: ADV_SCHEMA })

const findings = adv ? (adv.defects || []).map(d => 'DEFECT: ' + d).concat((adv.minors || []).map(m => 'MINOR: ' + m)) : []
let fix3 = null
if (findings.length) {
  phase('Fix3')
  fix3 = await agent([
    'ROLE: FIX-3 agent. Apply every DEFECT and every MINOR you verify is real and that the spec, rulings and gates allow (the hook and the round-2 test file may change; the three frozen tests may not; a finding that needs a ruling is reported for the orchestrator with your measurement). First re-hash the hook, the round-2 test file and the frozen tests; restore a left-over mutant from the adversary byte copy (never git checkout --). Afterwards re-run the TF4 gates and every mutant an applied finding names.',
    CONTEXT,
    'Fix-2 report files: ' + JSON.stringify(fix2 ? fix2.files_changed : []),
    'Findings:\n' + findings.join('\n') + '\nNotes: ' + NOTES + '/fix3 (create it).',
    'Return files changed with final sha256, gates, mutants, deviations (incl. rejected findings with the refuting measurement and findings left for the orchestrator), git status, residual risk, the updated full pr_text, summary. Budget: 90 minutes from your first tool call.',
  ].join('\n'), { label: 't0b-a:fix3', phase: 'Fix3', model: 'opus', schema: WORK_SCHEMA })
}
return { fix2, adversary: adv, fix3 }

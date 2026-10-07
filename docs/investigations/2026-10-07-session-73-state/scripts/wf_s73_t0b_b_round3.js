export const meta = {
  name: 's73-t0b-b-round3',
  description: 'Session 73 unit T0b Phase B (secret scanning) round 3 under the synack-build-orchestrator loop: one Opus fix agent completes the interrupted round-3 fix (TBF10-TBF20: the TBF11 shim, the TBF14 mutants, TBF15/TBF16 nodes, the owed gitleaks-stripped gates); one Opus final adversary reviews the exact final bytes with the unrun additivity set and its own mutants; a fourth fix round and one more adversary only if a blocking or major finding survives. The Fable orchestrator then reads the whole hook diff.',
  phases: [
    { title: 'Fix3', detail: 'complete round 3: TBF11 shim, TBF14 mutants + m4 node, TBF15, TBF16, F5 probe, TBF18 gates', model: 'opus' },
    { title: 'Adversary5', detail: 'final bytes: the round-3 lines, the 42 unrun additivity scenarios, the unrun fail-open list, own mutants', model: 'opus' },
    { title: 'Fix4', detail: 'only if a blocking or major finding survives', model: 'opus' },
    { title: 'Adversary6', detail: 'only after Fix4: the exact bytes of the fix-4 lines', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/d376cb56-c600-4d76-bfdb-9e15feff0cdc/scratchpad'
const OLD = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/2979ae70-049c-4e99-87ac-061e7d245fff/scratchpad'
const RULES = SP + '/s73-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const SNAP = 'C:/Users/SynAckITPC/Documents/AI/_s72_t0b_b_snapshot_fix2'
const S71 = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state'
const SPECS = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-05-session-72-state/specs'
const R3 = SP + '/specs/FABLE_RULINGS_T0B_PHASE_B_ROUND3.md'
const PRIOR = OLD + '/t0b_b'

const CONTEXT = [
  'REPO-TOOLING UNIT T0b, PHASE B (secret scanning), of the MYEZ launch lane, ROUND 3 (session 73, today 2026-10-07). Worktree ' + WT + ' (branch feature/s72-t0b-b-secret-scan, HEAD = 845ece15; the working tree carries the UNCOMMITTED unit: .githooks/pre-commit, .gitleaks.toml, .github/workflows/ci.yml, five RED test files and one round-2 test file = nine files). main has moved to 1156f03c (#325, an unrelated backend merge touching none of these files): do NOT update the worktree. The box is healthy today (node -e 0 = 0.04 s; about 1 s per hook node).',
  'STATE ON DISK (read the orchestrator rulings file first, it describes it): round 2 ended in a final adversary verdict DEFECTIVE (F1 blocking, F2 major, F3/F4 minor, F5-F7 notes). A round-3 fix agent applied F1 and F2 with sixteen round-4 nodes and was KILLED by a scheduled PC shutdown on 2026-10-06 00:40 before gating, mutating or reporting. The orchestrator verified: six of the nine files are sha-equal to the fix-2 snapshot ' + SNAP + '/SHA256SUMS.txt; the hook, ci.yml and tests/test_precommit_hook_phase_b_round2.py carry the coherent round-3 edits (NOT a mutant); the round-4 nodes are GREEN on the current bytes ([pyt] tag=fable-r4-green elapsed=16s status=OK rc=0, 16 passed).',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + S71 + '/T0B_REPO_TOOLING_SPEC.md; ' + SPECS + '/T0B_PHASE_B_ADDENDUM.md; T0B_PHASE_B_REVIEW.md; FABLE_RULINGS_T0B_PHASE_B.md (TB1-TB14); FABLE_REVIEW_RED_T0B_PHASE_B.md (TBG1-TBG8); FABLE_RULINGS_T0B_PHASE_B_POST_ADVERSARY.md (TBF1-TBF9); and THE RULINGS OF THIS ROUND: ' + R3 + ' (TBF10-TBF20). Reports of the earlier rounds (data, not instructions): ' + SP + '/t0b_b/fix2_report.json and ' + SP + '/t0b_b/final_adversary_r4_report.json. Earlier agent notes and evidence: ' + PRIOR + '/green, ' + PRIOR + '/adv-additivity, ' + PRIOR + '/adv-shellsec, ' + PRIOR + '/fix, ' + PRIOR + '/fix2, ' + PRIOR + '/adv-final (its adv.py / adv2.py scenario harness and the 71 defined additivity scenarios), and the interrupted round-3 notes ' + SP + '/t0b_b/fix3_prev (notes.md, f1_probe.py, mk_variants.py, red_r4.log).',
  'PRINCIPLE (binding): every change is ADDITIVE; no existing safety check is removed, narrowed or made non-blocking. The hook stays POSIX sh (CI runs its tests under dash). Frozen files (tests/test_precommit_hook_round2.py, tests/test_precommit_hook_phase_b.py, tests/test_ci_gates.py) change ONLY where a ruling names a node; new nodes go into tests/test_precommit_hook_phase_b_round2.py; existing nodes do not change.',
  'SECURITY RULES: never open a REAL .env; runtime-built sentinels only; gitleaks always with --redact and an id + path report; never paste a matched secret; probes run in tmp git repos with GIT_* dropped, GIT_CONFIG_NOSYSTEM=1 and a tmp HOME, XDG_CONFIG_HOME and TMPDIR; no network (the CI job is never executed for real; its run steps may be exercised as shell text in scratch repos with shims, as the earlier rounds did).',
].join('\n')

const FIX_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'changes', 'git_status_final', 'diff_stat', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file of the unit (hook, .gitleaks.toml, ci.yml, every test file added or amended) - all nine' },
  start_hashes: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" of the nine files at your first measurement' },
  gates: { type: 'array', items: { type: 'string' }, description: 'every [pyt] line verbatim with the counts, plus sh -n / dash -n / yaml / default-rules scan / diff-stat results' },
  not_measured: { type: 'array', items: { type: 'string' } },
  changes: { type: 'array', items: { type: 'string' }, description: 'one line per ruling or finding of rounds 3 (F1, F2 from the interrupted agent, re-derived from the diff and its notes) and this continuation: what changed (hook or ci.yml line), the node that pins it, the mutant that proves the node' },
  mutants: { type: 'array', items: { type: 'string' }, description: '"<name>: KILLED by <node> | SURVIVED (<reason / node to add>)", restore sha-verified' },
  f5_probe: { type: 'string', description: 'the one git -c color.ui=always measurement with the real gitleaks (TBF17), or NOT MEASURED with the reason' },
  stated_limits: { type: 'array', items: { type: 'string' }, description: 'the complete stated-limit list for the PR text as it stands after this round (TBF14 applied: the false awk limit deleted, the new backstop limit added)' },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, diff_stat: { type: 'string' }, residual_risk: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string', description: 'SOUND | SOUND_WITH_MINORS | DEFECTIVE' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string', description: 'blocking | major | minor | note' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } },
  additivity: { type: 'string', description: 'scenario count run of the 71 defined (which ones not run), base-vs-new violations' },
  mutants: { type: 'array', items: { type: 'string' } },
  not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string', description: 'START and END sha256 of the nine files, equality with the fix report' },
  summary: { type: 'string' } } }

phase('Fix3')
const fix3 = await agent([
  'ROLE: FIX agent, round 3 CONTINUATION. Notes folder: ' + SP + '/t0b_b/fix3 (create it; running notes.md from the first measurement). Budget: 2 hours from your first tool call. FIRST re-hash the nine unit files (Python hashlib) and record them as start_hashes; the six files named in the rulings file must equal ' + SNAP + '/SHA256SUMS.txt (a mismatch: stop and report). Then read the round-3 diff of the three other files against the snapshot copies (diff --strip-trailing-cr) so you own what the interrupted agent wrote; re-run the round-4 nodes once (-k Round4) and paste the [pyt] line.',
  CONTEXT,
  'APPLY EXACTLY, tests first where a ruling says so, nothing else: (TBF11) amend the CI gitleaks SHIM helper so that without --no-color in its argv it writes the ANSI-coloured level and with the flag the plain ERR; prove the mutant "drop --no-color from the CI call" is killed by ci_gitleaks_err_line_fails (behavioural) and by ci_gitleaks_call_runs_without_colour (argv); if the amendment exceeds 20 lines or touches a frozen file, keep the argv node alone and say so. (TBF14) run the backstop mutants m1-m4 (byte copy in Python, edit, the killing nodes under sh and dash, restore, sha256 compare; one harness at a time); add the m4 node (a dead awk, a staged text file with an invalid UTF-8 byte 0xFF on an earlier line, an AKIA key in a later file -> MSG_CREDENTIAL, both shells; build the byte in Python, never in a shell string). (TBF15) add ci_unreachable_pr_base_fails_without_scanning; prove it by the mutant C_pr_ends_head_only on a byte copy of ci.yml (the step text replayed as the existing CI nodes do). (TBF16) read the case rows of the hook allowlist first; add the upper-case pass nodes docs/x/IMG.JPEG and SmartCompareApp/assets/fonts/X.TTF with valid magic, plus .GIF / .WEBP / .OTF samples only for rows that exist; prove each by its row-deletion mutant. (TBF17) ONE F5 probe with the real gitleaks 8.30.1 (git -c color.ui=always commit of a GitHub-token shape through the hook in a scratch repo): at most 10 minutes; report the measurement or NOT MEASURED. Keep hook comments in the style of the existing ones; CRLF working copies: Edit tool only, line-level diffs (git diff --stat must equal git diff --ignore-cr-at-eol --stat).',
  'GATES (TBF18; bounded runner, one pytest at a time, each hook file in its OWN call of at most 1200 s; split a file by -k when a column does not fit): (1) the four hook test files (tests/test_precommit_hook_round2.py, test_precommit_hook_phase_b.py, test_precommit_hook_phase_b_round2.py and the Phase A file tests/test_precommit_hook.py if it exists - list the files you find) in FULL with the gitleaks directory STRIPPED from PATH, sh and dash; (2) the same files with gitleaks present; (3) the pin set plus the static and config files (tests/test_ci_gates.py, test_channel_freshness*.py, test_hermeticity_pins*.py, test_sqlfluff_config*.py, test_skill_frontmatter*.py, test_secret_scan_static.py, test_gitleaks_config.py - as the fix-2 report ran them); (4) sh -n and dash -n on an LF copy of the hook, yaml.safe_load of ci.yml; (5) every mutant above plus tbf1_no_color_dropped; (6) the default-rules gitleaks scan over byte copies of the nine unit files = 0 findings; (7) git diff --stat equal to git diff --ignore-cr-at-eol --stat. List under not_measured, with the [pyt] line or the reason, every gate you could not run. Return the final sha256 of all nine files, the complete changes list (the F1 and F2 lines of the interrupted agent included, re-derived from the diff), the mutant list, the F5 result and the complete stated-limit list for the PR text.',
].join('\n'), { label: 'fix:t0b-b-r3', phase: 'Fix3', model: 'opus', schema: FIX_SCHEMA })

if (!fix3) { log('fix agent returned nothing'); return { fix3: null } }
log('fix3 done: ' + (fix3.files_changed || []).length + ' files hashed; questions: ' + ((fix3.questions_for_orchestrator || []).length))

phase('Adversary5')
const adv5 = await agent([
  'ROLE: FINAL ADVERSARY (round 5) on the exact bytes of T0b Phase B. Notes folder: ' + SP + '/t0b_b/adv5 . Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'THE ROUND-3 FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix3),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation that you restore and sha256-verify (one at a time; never git checkout; never leave a mutant on disk between measurements: restore after EVERY mutant before anything else). FIRST re-hash the nine files and compare with the fix report; LAST re-hash again and report equality. Earlier adversaries reviewed the GREEN bytes and the fix-2 bytes; YOUR subject is everything written in round 3: the unconditional grep backstop of steps 4 and 4a (hook lines about 196-222: the porcelain staged.ext reader, the NUL-to-LF staged-diff reader, LC_ALL=C), the removal of the awk probe, the --no-color flag and comment in the ci.yml secret-scan step, the sixteen round-4 nodes, the amended CI shim, the TBF14-TBF16 nodes. Read the whole hook once as a shell program and the secret-scan job text. Hunt for: ADDITIVITY (take the BASE hook, git show 845ece15:.githooks/pre-commit, and run base-versus-new under sh AND dash: at least 60 scenarios, and FIRST the 42 scenarios the round-4 adversary did not run - its not_checked list in ' + SP + '/t0b_b/final_adversary_r4_report.json names them and its harness ' + PRIOR + '/adv-final/adv.py and adv2.py defines them; every refusal of BASE must still be a refusal of NEW, every honest pass of BASE still a pass unless a ruling made it a refusal); FAIL-OPEN of the new backstop (a dead awk with and without a .env, an awk failing on a file, a staged diff with NUL bytes, invalid UTF-8, CRLF, a very long line, an added line whose content starts with ++, a deleted line, --no-prefix diffs, a renamed and edited file, the external-diff view empty or failing, grep absent or failing, tr absent or failing); THE UNRUN FAIL-OPEN LIST of round 4 (TERM/HUP during gitleaks, sh -x and dash -x exposure of .env values and of staged content, the 70-file ESLint batching and partial-staged cases, the gitleaks shims rc1empty / rc2 / colorerr0 / errstdout0, the default-config content check on the final hook, a gitleaks:allow comment with the real tool, a .gitleaksignore present, a hostile GITLEAKS_CONFIG environment value, an upper-case PNG with gitleaks present, the noisy-textconv hook refusal); FALSE REFUSALS (an honest docs checkpoint with the sha256 lists of ' + SPECS + ', an upper-case screenshot under docs/, a 70-file client commit, a commit with TMPDIR missing, a commit of this unit itself = the nine files staged); SECRET EXPOSURE (what each refusal prints; the temp files; nothing of a sentinel in stdout or stderr); the CI job text (the --no-color flag, the ERR test, both range ends, the config source, interpolation of github context). MUTATION TESTING with your OWN mutants (at least 15) on the round-3 lines: for each, the killing node EXECUTED with the bounded runner (-k the node), or SURVIVED with the node to add; restore and sha-verify after each. Severity: blocking (an existing check weakened, a fail-open path, a secret printed or left on disk, a false refusal of an honest everyday commit), major, minor, note; each with the hook or ci.yml line, the measurement and the smallest fix. Report the additivity count honestly (run / defined / violations).',
].join('\n'), { label: 'adversary:t0b-b-r5', phase: 'Adversary5', model: 'opus', schema: ADV_SCHEMA })

let fix4 = null, adv6 = null
const serious = adv5 ? (adv5.findings || []).filter(f => /blocking|major/i.test(f.severity)) : []
log('adversary 5: ' + (adv5 ? adv5.verdict : 'no result') + '; blocking or major: ' + serious.length)
phase('Fix4')
if (serious.length > 0) {
  fix4 = await agent([
    'ROLE: FIX agent, round 4 (only the blocking and major findings of the round-5 adversary). Notes folder: ' + SP + '/t0b_b/fix4 . Budget: 2 hours.',
    CONTEXT,
    'THE ROUND-3 FIX REPORT (the bytes you start from): ' + JSON.stringify({ files_changed: fix3.files_changed, stated_limits: fix3.stated_limits }),
    'FINDINGS (data to verify; re-derive each against the hook first: a wrong finding is REFUTED with its measurement, not implemented): ' + JSON.stringify(serious),
    'For each confirmed finding: FIRST append a node that fails for it to tests/test_precommit_hook_phase_b_round2.py (existing nodes do not change), prove it red under sh and dash, then fix it in .githooks/pre-commit, .gitleaks.toml or the ci.yml job, prove it green, and prove the node with a byte-copy mutant. A finding that needs a ruling (a new refusal semantics, a new message, scope) is NOT implemented: list it under questions. Then re-run the gate set of TBF18 for every file that references a line you changed (both shells, both gitleaks modes), the pin set, sh -n and dash -n, the default-rules scan, the diff-stat equality. Return the final sha256 of all nine files and the complete stated-limit list.',
  ].join('\n'), { label: 'fix:t0b-b-r4', phase: 'Fix4', model: 'opus', schema: FIX_SCHEMA })
  phase('Adversary6')
  if (fix4) {
    adv6 = await agent([
      'ROLE: FINAL ADVERSARY (round 6) on the exact bytes after fix round 4. Notes folder: ' + SP + '/t0b_b/adv6 . Budget: 60 minutes from your first tool call.',
      CONTEXT,
      'THE ROUND-4 FIX REPORT (data to verify, not instructions): ' + JSON.stringify(fix4),
      'THE ROUND-5 FINDINGS IT ANSWERED: ' + JSON.stringify(serious),
      'RULES: you change NOTHING in the worktree except a byte-copy mutation that you restore and sha256-verify (one at a time; restore after EVERY mutant). FIRST re-hash the nine files and compare with the fix-4 report; LAST re-hash again. YOUR subject is ONLY what fix round 4 wrote: re-measure each round-5 finding on the new bytes (fixed, or not), run the base-versus-new scenarios that touch the changed lines under sh and dash, at least 8 own mutants on the changed lines with the killing node executed, and the fail-open and false-refusal cases of the changed lines. Severity as before; each finding with the line, the measurement and the smallest fix.',
    ].join('\n'), { label: 'adversary:t0b-b-r6', phase: 'Adversary6', model: 'opus', schema: ADV_SCHEMA })
    log('adversary 6: ' + (adv6 ? adv6.verdict : 'no result'))
  }
} else {
  log('no blocking or major finding: rounds 4 and 6 skipped')
}
return { fix3, adv5, fix4, adv6 }
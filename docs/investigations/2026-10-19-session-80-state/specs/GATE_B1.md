# Fable RED gate for B1 RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA), 2026-10-20 03:30 AST

Verdict: PASS. GREEN may start on the frozen RED files.

## Evidence (orchestrator, independent of the RED agent)
- Worktree `sc-s80-b1` at `81df2b64`; `git status --short` = the two untracked test files only; `git diff --stat` empty.
- Frozen RED files: `tests/test_s80_b1.py` sha256 `88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb` (59,270 B), `tests/test_s80_b1_feedback.py` sha256 `0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3` (7,874 B); 0 bytes > 127, LF only; secret and personal-value scan clean (sk-/AKIA/xox/PEM/JWT shapes, personal mailboxes, owner names).
- Spec sha `05d48e2cef8c17ca472e6cad9696fa582ac2ba37eedc2b823aeb74dc00289bd6` unchanged since the review.
- Orchestrator re-run at base through the bounded runner: `[pyt] tag=gate-b1-red ... 191 failed, 23 passed in 11.91s status=FAIL rc=1`; failure classes in the log: 191 AssertionError, 0 other. Matches the RED report (167 + 24 failed, 20 + 3 passed).
- RED report (`specs/B1_RED_REPORT.md`): prototype ON 214/214, OFF 214/214 with the P1 and FY25 digests equal and zero telemetry messages; mutants 36 applied, 0 survived (X19 not applied, see GA-4); comm set 288 unique files in 12 chunks at base, failures = the seven `tests/.pre_impl_failures.txt` baseline nodes only plus the unit's own RED rows in chunks 00 and 08; the four NOT-MEASURED files ran alone at base; restore check clean, scratch worktree removed, no orphan pytest.

## Gate rulings (binding for GREEN and the adversaries)
- GA-1 (RED Q1) The measured explicit-pair contract stands: `metadata.product_categories == ['other','other']` for brand-only typed names (the per-product keyword stubs), `['electronics','electronics']` on the parser path and the stream. Stated limit for the CLAUDE.md row: the cross-category rule cannot fire on an explicit pair of brand-only names.
- GA-2 (RED Q2, B1-R10) The bucket tags carry the bucket's lower edge in milliseconds as a digit string (1000-ms steps for `vision_ms`, 5000-ms steps for `compare_ms`); raw ints ride extras under the same keys through `telemetry_extras`. GREEN keeps that representation; no enum labels.
- GA-3 (RED Q3) R19 keeps its positive half (exactly one message when the client is present) and stays RED at base; its zero-entries half is the X23 killer.
- GA-4 (RED Q4) Mutant X19 (the stamp moved before the price chokepoint) is applied BY HAND by the correctness adversary on the GREEN bytes in its own scratch worktree; the adversary report names the killing row or declares it equivalent with the measurement.
- GA-5 (RED Q5) P1's literals are sha256 digests of the normalised bodies (the FY25 precedent); accepted as "recorded as literals".
- GA-6 The RED agent's measured deviations (R15 identity/coverage values, R3's veto on the identity-equality arm, R2's normalised placeholder set, R5's numeric non-bool amount, R9/R9b, R13, R8 reasons via `assess_result`, P5/P5b RED at base, P4's zero-entries form, the stream exits driven directly) are the contract GREEN implements; the spec text is amended by this gate, not re-edited.
- GA-7 GREEN may start from the RED agent's prototype text (`<scratchpad>/B1_red/proto/result_gate.py` and `prototype_tracked.diff`) but re-derives every hunk against the spec, the rulings and this gate, keeps CRLF where the file has it, byte-copies every file before editing, and never touches the two RED files.
- GA-8 Before the PR: GREEN rebases `feature/s80-b1-result-status` onto origin/main `4a38ce93` (H0 merged) and places the CLAUDE.md flag row after the B3-B block and before `## Tests`; the CLAUDE.md:105 `/feedback` line is rewritten in place (four fields plus the three optional correctness fields).
- GA-9 Adversary lenses for B1: correctness (runtime truth, flag-OFF identity, the X19 hand mutant, the sampler against sentry-sdk 2.68.1) and engineering (diff hygiene, comm set re-derivation, the CI-order set, CLAUDE.md row truth, PII in telemetry tags and extras). The PR body maps MYEZ-002/003/004/011/012/015/022/023/027 to the RED node ids.

# T0b Phase B (secret scanning) - orchestrator gate on the RED tests (BINDING, 2026-10-05 16:20 AST)

Gate: **PASS.** It supersedes the spec, the addendum, the review and rulings TB1-TB14 where they differ.

Files, frozen from here on (the GREEN edits none of them):
- `tests/test_precommit_hook_phase_b.py` sha256 `ce973c2964b589da...` (57 scenarios x sh/dash)
- `tests/test_secret_scan_static.py` sha256 `05e34918a5c10543...` (30 nodes)
- `tests/test_gitleaks_config.py` sha256 `f305045bcb187319...` (26 nodes; skip without gitleaks)
- `tests/test_ci_gates.py` sha256 `3b322a925500190b...` (the TB2 pipe-pin amendment, +16/-2, black-clean)
- `tests/test_precommit_hook_round2.py` sha256 `d26059912eb26e54...` (the two TB2 amendments, +13/-4)

Orchestrator re-run at base `845ece15` (worktree `sc-s71-t0b`, MSYS sh and dash): `[pyt] tag=fable-t0bb-static ... elapsed=14s status=FAIL rc=1` = 52 failed, 4 passed (static + config; every failure an AssertionError); `[pyt] tag=fable-t0bb-func start=2026-10-05 16:10:10 end=2026-10-05 16:17:14 elapsed=424s bound=1200s status=FAIL rc=1` = 84 failed, 27 passed, 3 skipped; no ERROR line, no pin failure, every failing scenario fails under BOTH shells; the five hashes equal the agent's report. Agent evidence accepted: at base the Phase A file 62 passed, the round-2 file 28 passed + the 2 expected reds, the five-file pin set 204 passed + the 1 expected red; satisfiability on a reference hook `cand3` (the reviewer's `cand2` + TB3 + TB6) = every node of the three new files green with gitleaks present (111 passed, 3 skipped) and stripped (97 passed, 17 skipped); the textconv-reveal PINs fail on the addendum's raw-only hook and the TB3/TB6 nodes fail on `cand2`, as they must.

- **TBG1 (the tracked fonts under docs).** TB3 literally refused three tracked files (`docs/claude-design-handoff/fonts/Geist-*.ttf`). The allowlist gains exactly the row `docs/claude-design-handoff/fonts/*.ttf` with its magic bytes; not `docs/*.ttf`.
- **TBG2 (new message accepted).** `could not read .gitleaks.toml from HEAD for gitleaks` is the fail-closed refusal when the HEAD config copy fails.
- **TBG3 (`.gitleaksignore`).** The hook refuses a present `$TOP/.gitleaksignore` when gitleaks is installed (the reference behaviour). With gitleaks absent it does not; a committed `.gitleaksignore` is then caught by the CI guard. Stated limit.
- **TBG4 (PR-range acceptance nodes).** They find merges by subject in the local history and skip where a merge is absent (CI's shallow checkout): accepted as a local gate.
- **TBG5 (deviations accepted).** The magic-byte refusal reuses the `MSG_BINARY` prefix; node 7b requires the `.env` value pipe to read the staged-diff file with `cat`; the real-commit nodes run in the sh column only; the colour override is checked by behaviour in the shim and by spelling in the static node; the by-path ESLint node does not require `--`; the no-`[extend]` mutant also strips the `targetRules` lines (gitleaks refuses to load an allowlist naming a missing rule: fail-closed, measured).
- **TBG6 (the mawk canary).** `i315_nul_jwt_at_allowlisted_path` may be red only in CI (Ubuntu's awk): that is a real gap in the added-lines filter and is FIXED before merge (never xfailed).
- **TBG7 (message constants).** The fifteen strings of the RED report are binding for the GREEN, each printed through the existing `fail` helper or as a `pre-commit: WARNING` / `pre-commit: NOTE` line on stderr.
- **TBG8 (gates for GREEN).** As TB13. The "own range under default rules" gate is run on the working tree before the commit: `gitleaks dir` with DEFAULT rules over a byte copy of every file the unit adds or changes (the hook, `.gitleaks.toml`, `ci.yml`, the five test files) = 0 findings; the orchestrator repeats it on the commit range before the PR.

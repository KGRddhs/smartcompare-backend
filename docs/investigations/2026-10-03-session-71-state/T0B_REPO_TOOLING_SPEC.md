# T0b — repo tooling (config-audit batch C, skill Step 2) — unit spec

Author: the Fable orchestrator, 2026-10-03. Status: DRAFT until an Opus adversarial spec review appends its binding corrections and the orchestrator rules. Base: main AFTER PR #279 (U4b) merges, because both touch `.github/workflows/ci.yml`.

Sources: `CONFIG_AUDIT_PLAN.md` findings R5, R9, R11, R18, R28; `IMPLEMENTATION_PLAN.md` Milestone 0 row T0b; `.githooks/pre-commit` at `4bd5a09f` (read in full by the author).

## Principle (binding)

Every change is ADDITIVE. No existing safety check is removed, narrowed or made non-blocking. The four existing credential regex branches, the root `.env` refusal, the py_compile, ruff, black and sqlfluff steps keep their behaviour for every input they handle today. A change that weakens one of them is a critical finding, not a cleanup.

The hook stays POSIX `sh` (CI runs the hook test under `dash`). No bashisms, no GNU-only flags without a fallback.

## Requirements

**R1. Secrets, three additive layers in `.githooks/pre-commit` step 4.**
- R1.1 Two new regex branches on staged ADDED lines, beside the existing four: a JWT shape (three base64url segments of 10 or more characters, the first starting with `eyJ`) and a credentialed URL (`scheme://user:password@`). The existing `\bsk-` word-boundary rule and its comment stay byte-equal.
- R1.2 A gitleaks pass when `gitleaks` is on PATH: scan the staged changes only, redacted output, fail closed on a finding. When gitleaks is absent: one WARNING line, commit proceeds. The reviewer confirms the exact flags for the installed 8.30.1 with `gitleaks git --help` before any line is written.
- R1.3 A fixed-string pass: when a repo-root `.env` exists, every value of 16 or more characters whose NAME contains KEY, TOKEN, SECRET or PASSWORD (case-insensitive) is compared against the staged added lines. On a hit the hook fails and prints the variable NAME only. It never prints a value and never writes one to a temp file that outlives the hook. No `.env`: the pass is skipped silently.
- R1.4 If gitleaks default rules flag existing repo content that a normal commit would touch (measure on the diffs of the last 50 commits), add the smallest `.gitleaks.toml` allowlist that clears those, one justification per entry. No blanket path allowlist.

**R2. Hook mechanics (R28).**
- R2.1 py_compile, ruff and black read the STAGED blob of each file, not the working-tree file (materialise the staged content with `git checkout-index --temp` or `git show :path` into a temp dir that is removed on exit; never `git stash`). A staged file with a syntax error whose working-tree copy is already fixed must FAIL.
- R2.2 The `.env` refusal also covers nested paths: `(^|/)\.env(\..*)?$`. Measure `git ls-files` first: the widened rule must not start refusing a file that is tracked today, unless the root rule already refuses it. Any exception is listed by exact path with its reason.
- R2.3 When black is missing and a staged file is on the allowlist: one WARNING line (today it is silent).
- R2.4 ESLint on staged `SmartCompareApp/src/**/*.ts(x)` content, with the PROJECT eslint by path, only when `SmartCompareApp/node_modules/eslint` exists (otherwise one NOTE line). Errors block; warnings do not (the tree carries 148 warnings). The reviewer measures the per-file cost on this box and proposes the invocation (one process for all staged files if the flat config resolves from a temp copy, else per-file stdin) and a cap above which the hook lints the working-tree files with a NOTE.
- R2.5 `scripts/setup_hooks.sh` (and a one-line PowerShell equivalent in its header comment): sets `core.hooksPath .githooks` for the clone and prints the result. Nothing else.

**R3. Skill frontmatter (R9).**
- R3.1 Fix `.claude/skills/qaren-eas-deploy/SKILL.md` and `.claude/skills/qaren-referrals/SKILL.md`: the `last_verified` value is quoted (or its inner `: ` removed) so the frontmatter parses. No other byte of either file changes.
- R3.2 A check that the frontmatter of every `.claude/skills/*/SKILL.md` parses with `yaml.safe_load` and has a non-empty `name` and `description`: as a pytest in CI and as a hook step when a `SKILL.md` is staged. The reviewer measures whether PyYAML is in `requirements-dev.txt`; if it is not, the lock change follows the repo rule (edit `requirements-dev.in`, recompile both locks with `uv`, never hand-edit a lock) and that is done by the orchestrator, not an agent.

**R4. Untrack the personal settings file (R18).** `.claude/settings.local.json` leaves the index (`git rm --cached`, done by the orchestrator at commit) and `.gitignore` gains the path. The file on disk is not touched. Moving shared settings into a tracked `.claude/settings.json` is OUT of scope.

**R5. CI secret scan (R11).** A new job in `ci.yml` that runs a PINNED gitleaks binary (release download verified by sha256; no marketplace action that needs a licence key) over the commits of the PR range only (`origin/main..HEAD`, full fetch depth), redacted. It blocks on a finding in the range. History before the range is not scanned by this job.

**R6. Out of scope, stated.** `.mcp.json` keeps its `railway` entry until Ahmed has applied audit batch A (the user-scope server); removing it earlier would leave repo-rooted sessions without Railway. No Prettier. No CLAUDE.md edit (T0c). No change to required checks in branch protection (Ahmed's setting).

## Files

Touch: `.githooks/pre-commit`, `.github/workflows/ci.yml`, the two `SKILL.md`, `.gitignore`, `scripts/setup_hooks.sh`, `tests/test_ci_gates.py` (new pins only), new `tests/test_skill_frontmatter.py`, new `tests/test_precommit_hook.py`, optionally `.gitleaks.toml`.
Must not change: `.mcp.json`, `CLAUDE.md`, any file under `app/` or `SmartCompareApp/`, the locks (unless R3.2 rules it, by the orchestrator).

## Test list

RED (each fails at base for the stated reason):
- T1 every `SKILL.md` frontmatter parses and has `name` + `description` (red on the two files).
- T2 `test_ci_gates` pins: the hook contains the JWT branch, the credentialed-URL branch, the gitleaks pass with its absent-tool warning, the nested `.env` rule, the staged-blob materialisation, the black-missing warning; `ci.yml` has the secret-scan job with a pinned version and a sha256 check and no `continue-on-error`.
- T3 fixture-driven hook test in a temp git repo (`tmp_path`; the hook is copied in; `sh` is located with `shutil.which`, and the test SKIPS with a reason when no POSIX shell is found, so it runs in CI and under Git Bash):
  - a staged JWT-shaped sentinel is refused; a staged credentialed URL is refused; a staged `sk-` shape is still refused. Every sentinel is BUILT at runtime by concatenation, so the test file itself holds no credential-shaped literal (the hook that guards this repo would refuse the commit otherwise).
  - a nested `sub/.env` is refused; the root `.env` is still refused.
  - a staged Python file with a syntax error fails even when the working-tree copy is fixed afterwards.
  - a clean staged change passes (exit 0) with gitleaks absent from PATH, and prints the WARNING.
  - the fixed-string pass: a temp `.env` with `FAKE_SERVICE_KEY=<runtime-built 24 chars>`; a staged line carrying that value is refused, and the hook output contains the NAME and not the value.
- T4 `.claude/settings.local.json` is not tracked (`git ls-files`) and `.gitignore` lists it.

PIN (green at base and after): the four existing credential branches still fire (one probe each, runtime-built); the `musk-` product slug still passes; the sqlfluff step text with `PYTHONIOENCODING=utf-8` is unchanged; the existing `test_ci_gates`, `test_channel_freshness` and `test_hermeticity_pins` nodes.

Mutants the tests must kill (at least): the JWT branch removed; the URL branch removed; gitleaks made fail-open when present; the nested `.env` rule reverted to root-only; the staged-blob read reverted to the working tree; the fixed-string pass printing the value; the CI job given `continue-on-error`; one existing branch (`AKIA`) dropped while adding the new ones.

## GREEN gates

The three new or changed test files plus `test_ci_gates.py`, `test_channel_freshness.py`, `test_hermeticity_pins.py` through the bounded runner; `py_compile` and the ruff tier on the new tests; the hook exercised by hand on a scratch repo (commands and output pasted); `actionlint` or a YAML parse of `ci.yml`; `git diff --stat` showing no whole-file rewrite (CRLF rule: Edit tool on tracked files).

## Assumptions, each with the reason it beats the alternative

- gitleaks runs fail-closed only when present, because a hard dependency would block every contributor machine without it; CI carries the mandatory scan.
- The CI job scans the PR range, not history, because history findings (already-rotated keys recorded as redacted placeholders, fixtures) would redden every PR for reasons the PR cannot fix; a history sweep is a separate, one-off task.
- The fixed-string pass keys on variable NAMES containing KEY/TOKEN/SECRET/PASSWORD, because matching every `.env` value would refuse public values that legitimately appear in docs (the Supabase project URL, the Sentry DSN in the client).
- ESLint blocks on errors only, because the tree has 148 known warnings and a warning gate would block every client commit.

## Open questions for the reviewer (answer each with a measurement and a recommendation)

1. The exact gitleaks 8.30.1 invocation for staged changes, and its runtime on this box.
2. Does any tracked file match the widened `.env` rule?
3. Is PyYAML in the dev lock?
4. The cheapest correct ESLint-on-staged-content invocation under the flat config.
5. Does the secret-scan job need `fetch-depth: 0`, and what does it cost in CI minutes per run?
6. Does the hook test run under `dash` unchanged (CI) and under Git Bash `sh` (this box)?

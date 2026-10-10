## T0b Phase B: secret scanning in the pre-commit hook and in CI

This PR closes issues #315 and #316 and the Phase B half of spec T0b (R1.2, R1.4, R2.4, R5).

It adds:
- a gitleaks pass to `.githooks/pre-commit`;
- a repo `.gitleaks.toml`;
- a CI `secret-scan` job with a sha256-pinned gitleaks 8.30.1.

It also rebuilds the hook's secret checks on ONE staged-diff file, so these no longer blind them:
- binary staged blobs;
- `color.ui=always`;
- `diff.external`;
- textconv drivers;
- a dead awk.

| | |
|---|---|
| Base | `845ece15` |
| Spec | `T0B_REPO_TOOLING_SPEC.md` (session-71 state) |
| Addendum and review | `T0B_PHASE_B_ADDENDUM.md`, `T0B_PHASE_B_REVIEW.md` |
| Rulings | TB1-TB14, TBG1-TBG8, TBF1-TBF25 (session-72 and session-73 state folders) |
| Files | nine: four tracked files changed, five new |

**Every number below was measured on the Windows box (MSYS bash as `sh`, dash, GNU grep 3.0, the Windows gitleaks 8.30.1) unless it says otherwise.** The Linux CI job had never run when this was written; its first real run is the evidence for the mawk canary below.

---

### 1. What changed in `.githooks/pre-commit`, step by step

The hook is LF in the index and CRLF in the working copy (691 lines). `git diff --stat` equals `git diff --ignore-cr-at-eol --stat`. Final sha256 of the CRLF working copy: `19640dc6a0fb9835264df579cc55a9791c713df92f098517e4ac02f0d8aafce2`.

1. **Private temp dir, once (`make_tmp`).** The dir is created on every commit:
   - with `mktemp -d`;
   - otherwise `qaren-precommit.<pid>` under TMPDIR or `/tmp`, then under the git dir.
   - It is always created under `umask 077` (B5). The traps remove it on EXIT, INT, TERM and HUP. `materialise` (the staged Python and SKILL.md blobs) now uses it.
2. **4-pre: the staged diff is read ONCE (TF7, TB2).** `$TMP/staged.diff` holds two views of the patch:
   - `git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv` (raw);
   - then the same with `--textconv`, so a driver that REVEALS content is still read (review correction, the critical one).

   A failed `git diff` refuses the commit: "could not read the staged diff (git diff failed)". A third view `$TMP/staged.ext` is the porcelain diff with the user's external diff allowed (`--ext-diff`, finding A1). Its status is checked too (TBF3), and its `^\+` lines (not `^\+\+\+`) are appended after an `@@ external-diff view` line.
3. **`ADDED_LINES_AWK`.** This awk program selects the added lines. A file header (from `diff --git` to its first `@@`) is skipped as a block, so an added line whose CONTENT starts with `++` is scanned.
4. **Step 4 (the four-branch credential line).** It now reads `awk "$ADDED_LINES_AWK" "$STAGED_DIFF"`.
   - The four-branch `grep -qE` line and its refusal stay byte-equal, pinned by `tests/test_ci_gates.py`.
   - TB2 lifted the byte-equal pin for the pipe head only.
5. **Step 4a (JWT and credentialed URL).** It reads the same awk stream.
6. **The grep backstop of steps 4 and 4a (findings B3, F1; ruling TBF14).** It runs unconditionally on every commit, whatever awk does. Each block is the old step-4 selection (`^\+` and not `^\+\+\+`, no header state) with the base patterns and the base messages, run over two inputs:
   - `$TMP/staged.ext`;
   - the staged-diff file with every NUL mapped to a line break.

   The upstream stages run under `LC_ALL=C`. The awk probe of fix round 1 was removed. Round 4 (TBF22) corrected the comment only (section 6).
7. **`.env` file refusal.** Unchanged from Phase A.
8. **4e: binary refusal (#315, TB3).** A staged file that git treats as binary (`numstat` `-<TAB>-`, with `--no-textconv --no-renames --diff-filter=ACMRT`) is refused unless:
   - its path matches a known asset row: `app/static`, `docs/`, `SmartCompareApp/assets/` images; `SmartCompareApp/assets/` fonts; `test_images/*.jpeg`; `docs/claude-design-handoff/fonts/*.ttf`;
   - AND its first 12 bytes are the magic of its extension.

   Extensions are compared in lower case (A3; `IMG_0001.PNG` passes). PDF, archives, office files, databases and executables never pass.
9. **4b: the `.env` value pass.** It now reads `cat "$STAGED_DIFF"` (the same file) instead of its own `git diff`. Everything else in Phase A's design stands: names only, one pipe, xtrace off.
10. **4g: gitleaks (spec R1.2, correction 1; TBF1, TBF2, TBF10).**
    - When gitleaks is absent: one WARNING, and the commit proceeds.
    - When it is present, it is called as `gitleaks git --pre-commit --staged --redact --no-banner --no-color --log-level error --ignore-gitleaks-allow`.
    - `--config` is ALWAYS given: the copy of `HEAD:.gitleaks.toml`, or a default-rules file when HEAD has none.
    - The report is a template of rule id, file and line, never content.
    - For the call, `GITLEAKS_CONFIG` and `GITLEAKS_CONFIG_TOML` are blanked, and `color.ui` and `color.diff` are forced to `never` through `GIT_CONFIG_COUNT`.
    - Refusals: a work-tree `.gitleaksignore`; any non-zero exit; an exit 0 with an ` ERR ` line in its stderr file. The stderr file is never printed.
11. **The Python checks (1-3) now run AFTER every secret check.** `py_compile` and ruff echo the offending source line, so a syntax error on a line holding a key used to print the key before any secret check ran.
12. **6: ESLint on the STAGED content of `SmartCompareApp/src/*.ts(x)` (spec R2.4, correction 9).**
    - It uses the project's eslint by path, from `SmartCompareApp/`. Errors and crashes refuse; warnings never do.
    - Fully staged files are linted by path, in batches of 64 (TBF5 c).
    - A partially staged file is linted from its blob through `--stdin` with its relative name.
    - More than 10 partially staged files: their working copies are linted, with a NOTE.
    - No node or no `node_modules`: a NOTE.

### 2. `.gitleaks.toml` (new; spec R1.4, corrections 2 and 3, TB4, TB5)

- `[extend] useDefault = true` is the first table. Without it, the config replaces the default ruleset with nothing (measured: rc 0 on a staged JWT).
- It has ten allowlists. Each names ONE benign shape by a regex on the match and says why it is benign:
  - a sha256 digest after a file name;
  - an OpenAI error quoting a short fake key;
  - the password fixtures of `tests/test_retro_w1_9_429.py` (AND-scoped to that file);
  - a short `access_token` fixture;
  - a short id in a workflow script row;
  - a pytest name;
  - `NAME=<small int>` and `name=True` in prose;
  - already-redacted values;
  - public client keys under `tests/fixtures/`, AND-scoped to three rules.
- There is NO path allowlist on `docs/investigations/`.
- Who reads it: the hook reads `HEAD:`, and CI reads the range BASE. So a widening judges only the commits after it. Widen it in its own PR.
- sha256: `af71860f0f1e8c2f925ec3df8847af6367afcea82fd958c2ed8e2472ecccdb40`.

### 3. The CI `secret-scan` job (`.github/workflows/ci.yml`, +93; spec R5, corrections 4, 5, 11; TB6, TB8, TBF11)

- **Settings.** `ubuntu-latest`, `timeout-minutes: 10`, `permissions: contents: read`, `actions/checkout@v4` with `fetch-depth: 0`.
- **Install.** The release tarball `gitleaks_8.30.1_linux_x64.tar.gz` is checked against the sha256 **`551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`**, read from the v8.30.1 release's own `gitleaks_8.30.1_checksums.txt`. A same-origin checksum proves integrity in transit, not authenticity. Then `test "$(gitleaks version)" = "8.30.1"`. The install checks have no `||` after them.
- **Range.**
  - A pull request scans `base.sha..head.sha`.
  - A push scans `before..sha`.
  - A new branch (`before` all zeros) scans only the pushed commit, with the default rules.
  - The GitHub context reaches the script only through `env:`, never through `${{ }}` inside `run:`.
- **Config.** The config is read from the range BASE. With no `.gitleaks.toml` there, the default rules are written out and passed, because without `--config` gitleaks loads the scanned tree's own file.
- **The job fails on:**
  - a range end missing from the clone, before any scan (F3);
  - a tracked `.gitleaksignore`;
  - an ` ERR ` line in the `--no-color` log (F2: 8.30.1 colours the level even into a file);
  - any finding, with the message "ROTATE THE KEY FIRST, then rewrite the branch".
- **What it is.** On this public repo the job is DETECTION, not prevention. It becomes a required check only when the owner adds it in branch protection.

### 4. Tests

| file | status | content |
|---|---|---|
| `tests/test_precommit_hook_phase_b.py` | new, frozen after RED (TBG) | 57 functional scenarios x sh/dash (114 nodes), incl. the `i315_*` family; two nodes amended by TBF2 |
| `tests/test_secret_scan_static.py` | new | 30 static pins (binary allowlist rows, CI step text) |
| `tests/test_gitleaks_config.py` | new | 26 config pins, real gitleaks where installed (skips without it, as in CI) |
| `tests/test_precommit_hook_phase_b_round2.py` | new, fix rounds 1-4 | 121 nodes (section 4.1) |
| `tests/test_ci_gates.py` | tracked, TB2 amendment (+16 lines with the two removed) | the pipe-head pin and the two staged-diff lines, read before the credential grep |
| `tests/test_precommit_hook_round2.py` | tracked, TB2 amendment (+13 lines with the two removed) | `d1_bulk` tolerates the gitleaks WARNING; `r3_failed_git_diff` expects "could not read the staged diff" |

#### 4.1 The 121 nodes of `tests/test_precommit_hook_phase_b_round2.py`

| class | scenarios | nodes |
|---|---|---|
| `TestPreCommitHookPhaseBRound2` | 25 | 50 |
| `TestSecretScanStep` | 8 | 16 |
| `TestPreCommitHookPhaseBRound4` | 12 | 24 |
| `TestSecretScanStepRound4` | 3 | 6 |
| `TestPreCommitHookPhaseBRound5` | 9 | 18 |
| unparametrised | 7 | 7 |

Round 4 (TBF21) added the class `TestPreCommitHookPhaseBRound5`. Each node runs under sh and dash with runtime-built sentinels and a no-12-character-piece check. Each was proven red on its mutant and green on the bytes:

| node | kills |
|---|---|
| `r5_dead_awk_sk_key_refused` | `bs1_sk_dropped` (a base refusal) |
| `r5_dead_awk_slack_token_refused` | `bs1_xox_dropped` (a base refusal) |
| `r5_dead_awk_credentialed_url_refused` | `bs2_credurl_dropped` |
| `r5_dead_awk_utf8_locale_invalid_byte_same_line_akia_refused` | `m4_lc_all_dropped` (TBF14 m4; the Round-4 earlier-line node stays as a pin) |
| `r5_dead_awk_utf8_locale_ext_diff_invalid_byte_line_refused` | `m1_ext_reader_dropped` and `bs_ext_reader_lc_dropped` |
| `r5_dead_awk_hiding_textconv_akia_refused` | `m2_tr_reader_dropped` |
| `pin_r5_removing_a_committed_key_line_passes` and `pin_r5_dead_awk_removing_a_committed_key_line_passes` | `bs_deleted_lines_too` (the post-leak remediation commit must pass) |
| `pin_r5_sk_word_in_a_new_file_path_passes` | `bs_plus3_filter_dropped` |

### 5. Measured cost per commit

| box | hook | sh (empty / ten files) | dash (empty / ten files) |
|---|---|---|---|
| healthy (review correction 12) | base | 0.98 s / 1.44 s | 0.89 s / 1.30 s |
| healthy (review correction 12) | Phase B | 1.79 s / 2.18 s | 1.67 s / 2.02 s |
| slow (2026-10-05 GREEN, `node -e 0` 0.62 s) | base | 4.47 s / 6.35 s | 4.25 s / 6.03 s |
| slow (2026-10-05 GREEN, `node -e 0` 0.62 s) | Phase B | 6.84 s / 8.05 s | 6.65 s / 7.68 s |

- On the healthy box Phase B adds 0.7-0.8 s. Adversary A, on the slow day: +3.09 s (sh) / +2.61 s (dash) on an empty commit.
- ESLint adds 2-4 s per process when client sources are staged.
- **Not costed:**
  - the round-2 and round-3 additions: the gitleaks stderr file, the ERR grep, and the two backstop greps;
  - adversary 5's figure on a loaded box: new hook about 9 s, base about 4 s, an informal reading.

### 6. Stated limits

This is the fix-3 list, amended by TBF14 and round 4.

- **gitleaks is optional in the hook.** Absent: one WARNING, and the commit proceeds. CI's `secret-scan` is the mandatory scan. On a public repo it is detection, not prevention, and it is not required until branch protection says so.
- **M2 without gitleaks.** Shapes outside the six regex branches stay open, e.g. `py_compile` echoing a GitHub token on a syntax-error line (TB7, review 13).
- **A failing external view refuses.** A textconv command or an external diff (`diff.external`, `GIT_EXTERNAL_DIFF`, a `diff.<driver>.command`) that FAILS refuses with "could not read the staged diff". Base passed silently there (correction 1, TBF3).
- **gitleaks ERR with exit 0 refuses.** When gitleaks logs an ERR line and exits 0 (e.g. a textconv driver writing to stderr), the commit is refused with "run gitleaks git --pre-commit --staged by hand" (TBF1, fail-closed). The hook never prints gitleaks' stderr.
- **The ERR test.** It is ` ERR ` on the `--no-color` log at level error, the same test as CI. A future gitleaks that changes its level text or ignores `--no-color` is guarded only by its exit code and report.
- **`++` content with a dead awk (TBF14).** The backstop uses the base selection, with no header state. With a dead awk, an added line whose CONTENT starts with `++` is skipped there, exactly as the base hook skipped it. With a working awk, steps 4 and 4a catch it.
- **NUL-to-LF residual with a dead awk (round 4, R5-4).** A secret that follows a NUL on the same diff line (text forced by an attribute) loses its `+` when NUL becomes a line break. Base is equally blind. With a working awk it is refused. The candidate `tr '\000' ' '` is in the follow-up issue.
- **The final greps run in the user's locale (round 4, R5-6).** The final `grep -qE` of each backstop block is not under `LC_ALL=C`. It matched on grep 3.0 under `C.UTF-8`. grep 3.5 or later is not measured. The patch is in the follow-up issue.
- **`SHELLOPTS=pipefail` (round 4, R5-5).** It is imported by bash, which is Git for Windows' `sh`. On a large diff it makes every `grep -q` check fail open: the four-branch line, 4a, the backstop and the `.env` pipe. Measured: base 0 and new 0 on a 120,000-line file. The behaviour is pre-existing and identical in base. dash ignores `SHELLOPTS`. The guard is in the follow-up issue.
- **F5, the gitleaks colour bypass.** With gitleaks installed, `git -c color.diff=always commit` defeats the hook's colour override for gitleaks' own `git diff`.
  - Mechanism: git exports `GIT_CONFIG_PARAMETERS`, which it applies after the hook's `GIT_CONFIG_COUNT`, and gitleaks then finds nothing.
  - Measured with 8.30.1: a staged GitHub-token shape was COMMITTED (rc 0).
  - `git -c color.ui=always` alone does not bypass, because the override's `color.diff=never` is more specific.
  - The six regex shapes are unaffected, because the hook's own diffs use `--no-color`.
  - The `GIT_CONFIG_PARAMETERS` patch is in the follow-up issue (TBF17).
- **xtrace and signals (F6, F7; follow-up issue).** Under `sh -x` / `dash -x` the binary check traces the first 12 bytes of each staged binary. QUIT and PIPE are not trapped; the temp dir is mode 700 and holds the staged diff.
- **Allowlisted binary content is barely read (TB14).** Content at an ALLOWLISTED asset path with the right magic bytes (UTF-16, NUL or attribute-binary) is regex-scanned only as far as `--text` exposes ASCII runs, and never for UTF-16. A secret inside an allowlisted image is never read.
- **No second binary detector (TBF4, #317).** Attribute-forced text (an untracked `.gitattributes`, or `.git/info/attributes` with `diff`) and UTF-16 with no NUL in its first 8,000 bytes pass the binary refusal. The regex checks still read the `--text` view.
- **The binary refusal is strict (TB3, A5).** It covers PDF, archives, office files, databases and executables, and images or fonts outside the TB3 rows (`landing/` OG images, `tests/fixtures` images, `test_images/*.jpg`, a UTF-16 `.ps1`). Each stays refused until its path is allowlisted in the hook in its own commit.
- **`.gitleaksignore`, config source and `--no-verify`.**
  - A work-tree `.gitleaksignore` is refused only when gitleaks is installed; a committed one is caught by the CI guard (TBG3).
  - The hook's gitleaks always reads HEAD's `.gitleaks.toml` or a default-only file, never the working tree's (TBF2).
  - `--no-verify` bypasses every check (TB14).
- **Allowlist changes land first.** CI reads `.gitleaks.toml` from the range base, so an allowlist change must land in its own PR first.
- **Merges.** A clean `git merge` runs no pre-commit hook. A concluded conflicted merge runs it over the whole merged-in diff, with no `MERGE_HEAD` exemption (TB9).
- **Amends.** `git commit --amend` scans only the delta against the amended commit. This is pre-existing and applies to every check.
- **ESLint can echo.** Its `i18next/no-literal-string` message may quote a literal: an M2-class echo after every secret check has run (not verified).
- **ESLint and partial staging.** With more than 10 partially staged client files, their working copies are linted (NOTE). By-path calls take at most 64 paths (TBF5 c, TBF13).
- **Path allowlists apply in git mode only.** In dir mode with an absolute source path, gitleaks reports absolute paths and path-scoped entries do not match (TBF5 f).
- **TB5.** With the final config the current tree still reports 27 findings in 16 files (section 7). Changing one of those lines needs an allowlist entry, in its own PR, first.
- **Docs ordering (TBF20, supersedes TBF9).** The session-72 docs PR #326 merged first (2026-10-07 21:35). The session-73 docs branch was cut from main `19bca733` after that merge; its PR opens after this unit merges, so its scan range starts at a base that carries this config.
- **The mawk NUL canary: TBF24, which amends TBF5 (b).** See section 8.
- **Phase A limits stand.**
  - Correction 6's regex limits (M5): credentialed-URL passwords under 12 characters, and the JWT segment lengths.
  - TF6: a single `.env` line of about 1 MB or more takes minutes to parse.
  - M7 and M8: Windows-only fail-closed refusals of `[ab].py`, gitlinks and symlinks (0 tracked).

### 7. TB5: pre-existing findings under the final config (27 in 16 files)

The source is GREEN's tree scan and adversary A's reproduction. The config has not changed since (`af71860f`). With the default rules only: 82.

- `SmartCompareApp/src/services/__tests__/sentry.test.ts`: generic-api-key 1, jwt 2
- `app/services/algolia_service.py`: generic-api-key 4
- `data/bh_gcc_source_candidates_round3.json`: algolia-api-key 1
- `docs/investigations/2026-06-25-bh-gcc-price-source-discovery-round3.md`: algolia-api-key 2
- `docs/investigations/2026-09-06-full-review-state/args-m22-product-output.json`: generic-api-key 1
- `docs/investigations/2026-09-06-full-review-state/continue-args-m22-product-output.json`: generic-api-key 1
- `scripts/probe_truth_freshness.py`: generic-api-key 1
- `tests/fixtures/jsonld_first/iq_miswag_com_no_structured_price_200.html`: jwt 1
- `tests/test_admin_key_and_sentry_scrub.py` 1, `tests/test_algolia_service.py` 1, `tests/test_api_budget_service.py` 3, `tests/test_identity_stamps_wave_b.py` 1, `tests/test_jomashop_persisted_query.py` 1, `tests/test_magento_gql_adapter.py` 1, `tests/test_referral_e2e.py` 4, `tests/test_sentry_service.py` (jwt 1)

### 8. The mawk NUL canary (TBF24; amends TBF5 (b))

- **The canary.** Ubuntu's default `awk` is mawk, which this box does not have. The frozen node `i315_nul_jwt_at_allowlisted_path` is the canary for mawk's NUL handling.
- **If it is red in CI only,** the pre-authorised fix is to MAP every NUL to a line break where the staged-diff VIEWS are written (`tr '\000' '\n'`, the form the backstop already uses).
- **Never `tr -d '\000'`.** It joins UTF-16 into ASCII and turns the frozen `i315_utf16_aws_key` red: the credential message would arrive before the BINARY one (round-3 mutant m3).
- **How it is applied.** Only on that CI evidence, in its own commit on this PR, with the frozen nodes re-run.

### 9. Rounds and adversary verdicts

| round | what | production bytes | result |
|---|---|---|---|
| spec | addendum + adversarial spec review (2026-10-05) | none | APPROVED_WITH_CORRECTIONS (13); rulings TB1-TB14 |
| RED | three new test files + the three TB2 amendments | none | Fable gate PASS (TBG1-TBG8): at base, 84 functional failed / 27 passed; static + config 52 failed |
| GREEN | hook, `.gitleaks.toml`, the `secret-scan` job | hook `fa180f13` | 33 of 34 own mutants killed; tree scan 27 findings in 16 files |
| adversary A (additivity) | base-vs-new matrix on the GREEN bytes | hook `fa180f13` | DEFECTIVE: A1 blocking (external-diff content lost), A2, A3 major |
| adversary B (shell security) | fail-open and exposure | hook `fa180f13` | DEFECTIVE: B1 blocking (gitleaks ERR with exit 0), B2, B3 major |
| fix 1 | A1, A2 (CI half), A3, A4, B2, B3, B5-B7 | hook `edd1b6fe`, ci.yml `3b4b3ed2` | 29 of 29 mutants killed; rulings TBF1-TBF9 |
| fix 2 | TBF1, TBF2, TBF5 (a)(c) | hook `864d30e5` | 11 of 11 mutants killed |
| final adversary (round 2) | the exact fix-2 bytes | hook `864d30e5` | DEFECTIVE: F1 blocking (dead awk after an asset), F2 major (CI ERR grep fail-open), F3, F4 minor, F5-F7 notes |
| fix 3 | the unconditional backstop (TBF14), `--no-color` in CI (TBF11), TBF15, TBF16, the F5 probe | hook `4e9a583c`, ci.yml `05c4ff90` | 10 of 13 mutants killed (m1, m2, m4 survived, killing designs measured); F5 confirmed (stated limit) |
| adversary round 5 | the exact fix-3 bytes | hook `4e9a583c` | SOUND_WITH_MINORS (detail below) |
| round 4 polish (TBF21-TBF25) | eight test-only nodes (18), the hook comment, the follow-up draft | hook `19640dc6` (comment only: the LF diff lists four comment lines) | 9 of 9 mutant runs red on their nodes and restored; no adversary required (TBF25) |

Adversary round 5 in detail:
- 101 base-vs-new scenarios, with 0 violations, 0 sh/dash differences and 0 leaks.
- 11 own mutants were killed by executed nodes; 9 survived, each with a measured killing scenario.
- Findings: R5-1 to R5-3 minor, R5-4 to R5-7 notes.

### 10. Follow-up issue

The issue is titled "T0b Phase B follow-ups: gitleaks colour bypass, pipefail fail-open, backstop residuals, TB5 list". It covers:
- (a) F5, the `GIT_CONFIG_PARAMETERS` patch;
- (b) the `SHELLOPTS=pipefail` guard;
- (c) `tr '\000' ' '` for the NUL residual;
- (d) `LC_ALL=C` on the final greps;
- (e) F6 xtrace and F7 traps;
- (f) the TB5 triage.

### 11. Merge checklist (the orchestrator)

1. Read `git diff -U2 --ignore-cr-at-eol .githooks/pre-commit` and the round-4 comment delta.
2. Re-run the pin set and the four hook test files once.
3. Commit THROUGH the new hook.
4. Watch the first real `secret-scan` run. Apply TBF24 only on canary evidence.
5. Merge on six green checks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

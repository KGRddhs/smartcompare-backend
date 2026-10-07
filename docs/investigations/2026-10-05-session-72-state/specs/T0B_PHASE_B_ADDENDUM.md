# T0b Phase B - build-ready addendum (secret scanning, ESLint on staged content, #315, #316, TF7)

Author: Opus spec agent, 2026-10-05 13:49-14:50 AST, under the synack-build-orchestrator loop.
Base: main 845ece15 (unit worktree sc-s71-t0b, branch feature/s72-t0b-b-secret-scan, clean, untouched).
Status: DRAFT for the Fable orchestrator. Every open question is in section 8.

Sources read in full: T0B_REPO_TOOLING_SPEC.md (corrections 1-17, TR1-TR10, TG1-TG8, TF1-TF8),
FABLE_RULINGS_T0B*.md, PR_312_T0B_A_BODY.md (sections used), STEP6_ACTION_PLAN.md section A, issues
#315 #316 #317 (bodies copied to issue_31x.md in the notes folder), .githooks/pre-commit at 845ece15,
tests/test_precommit_hook.py, tests/test_precommit_hook_round2.py, the T0b pins in tests/test_ci_gates.py,
.github/workflows/ci.yml.

Everything below marked MEASURED was run on this box today; the probe scripts and raw outputs are in the
notes folder (`specs/t0b_b/`): probe1 (gitleaks matrix), probe2 (numstat, binary population), probe3 and
probe3b/3c (base vs candidate hook, sh and dash), probe4 (gitleaks and git color config), probe5 (ESLint
shims, gitleaks shim argv, cost), probe6/6b/6c (PR-range scans, masked shapes), probe7 (config
acceptance), probe8 (merge commits, od, rename). Tools: gitleaks 8.30.1 (WinGet), git 2.52.0.windows.1,
MSYS sh (bash 5.2.37) and /usr/bin/dash, GNU awk 5.3.2, venv python 3.12, node v24.11.1, ESLint
v9.39.4 (sc-s70-u4b, read-only). Box health at start: `node -e 0` = 126 ms (healthy).

Security rules kept: no real .env opened (only FAKE .env files inside scratch repos); every sentinel built
at runtime (the Phase A constructors imported from tests/test_precommit_hook.py, plus three stronger
shapes concatenated in probe_common.py); gitleaks always --redact with a template report of rule id +
path (+ commit and line where a range was scanned); every hook subprocess ran in a scratch repo under
the notes folder with all GIT_* dropped, GIT_CONFIG_NOSYSTEM=1, tmp HOME / XDG_CONFIG_HOME / TMPDIR.
Shapes of PR-range findings are printed as lengths and character classes only.

THE REFERENCE IMPLEMENTATION: `specs/t0b_b/cand/pre-commit` (LF, sha256 in section 4) is a byte copy of
the 845ece15 hook blob with count-checked replacements (`build_cand.py`); `cand/phase_b_hook.diff` is
its histogram diff against the base (177 insertions, 52 deletions, line-level, not a rewrite). It passed
every measurement in section 2. GREEN reproduces it with the Edit tool on the CRLF working copy.

---------------------------------------------------------------------------------------------------

## 1. SCOPE TABLE

Line numbers are the 845ece15 hook. Step names follow the hook's own comments. The new order is the
binding change of this phase (section 8 Q4): ALL secret checks run before ANY Python check.

New step order (cand/pre-commit):
`helpers (TMP, make_tmp, materialise, run_tool, in_batches)` -> `4-pre staged diff read once` ->
`4 four-branch` -> `4a JWT + credentialed URL` -> `.env filename` -> `4e binary refusal (NEW)` ->
`4b .env values` -> `4g gitleaks (NEW)` -> `materialise PY_FILES` -> `1 py_compile` -> `2 ruff` ->
`3 black` -> `4c SKILL.md` -> `5 sqlfluff` -> `6 ESLint (NEW)` -> `exit 0`.
Implementation: move lines 95-138 (the `materialise "$PY_FILES"` call and steps 1-3) DOWN to just
after the 4b section's restore lines (:330-331) and the new 4g block. Nothing else moves.

| Item | Exact change | Place (845ece15) | Message(s) | Fail-closed behaviour |
|---|---|---|---|---|
| helper | factor the temp-dir creation out of `materialise` into `make_tmp()` (same body: mktemp -d, the `qaren-precommit.$$` fallback, the existing fail text); `materialise` calls `make_tmp` first | :40-47 | none new | unchanged (TG4 literals kept) |
| TF7 + #316 + #315a (4-pre) | NEW, before step 4: `make_tmp`; `STAGED_DIFF="$TMP/staged.diff"`; `git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv > "$STAGED_DIFF" \|\| fail "could not read the staged diff (git diff failed)"`; the ADDED_LINES_AWK / JWT_RE / CREDURL_RE assignments move up here unchanged | new block above :140; the three assignments leave :168-170 | `pre-commit: could not read the staged diff (git diff failed)` | a failed git diff refuses the commit before any secret check can pass on a partial or empty stream; closes TF7 for the four-branch line AND 4a AND 4b with one status check |
| #316 (step 4) | the pipe line becomes `if awk "$ADDED_LINES_AWK" "$STAGED_DIFF" \| \`; the grep line (the four-branch ERE) and the fail line stay BYTE-EQUAL | :150 changes; :151-153 unchanged | unchanged four-branch message | the ERE now sees the added lines under color.ui/color.diff=always and diff.external, and an added line starting with `++` (TF3 hole) |
| #315a (step 4a) | the pipe line becomes `if awk "$ADDED_LINES_AWK" "$STAGED_DIFF" \| \`; the grep line unchanged | :171 | unchanged MSG_NEW_SHAPES | as above |
| #315b (4e, NEW) | after the .env filename refusal: `BIN_LIST=$(git -c core.quotePath=false diff --cached --numstat --no-textconv --no-renames --diff-filter=ACMR) \|\| fail ...`; `TAB=$(printf '\t')`; a `while IFS= read -r` loop over BIN_LIST; a line starting `-<TAB>-<TAB>` gives the path; a `case` allowlist (section 2e) passes known asset paths; anything else fails | new block after :183 | `pre-commit: staged file is binary to git and not a known asset path: <path>`; `pre-commit: could not list the staged files for the binary check` | an unknown binary path refuses; a C-quoted (unusual) path never matches the allowlist and refuses; a failed numstat refuses |
| TF7 (4b) | the producer line `git diff --cached --no-color --no-ext-diff -U0 && printf 'Z\n'` becomes `cat "$STAGED_DIFF" && printf 'Z\n'`; the rest of 4b byte-equal (the Z trailer, ENV_MATCH_AWK, the xtrace and allexport guards) | :323 | unchanged MSG_ENV_VALUE and "could not run the .env value check" | unchanged (awk exits 2 without Z) |
| R1.2 (4g, NEW) | after the 4b restore lines: when `command -v gitleaks`: write a report template to `$TMP/gitleaks.tmpl`; `set --`; `--config "$TOP/.gitleaks.toml"` when that file exists; run `GITLEAKS_CONFIG= GITLEAKS_CONFIG_TOML= GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=color.ui GIT_CONFIG_VALUE_0=never GIT_CONFIG_KEY_1=color.diff GIT_CONFIG_VALUE_1=never gitleaks git --pre-commit --staged --redact --no-banner --log-level error --ignore-gitleaks-allow "$@" --report-format template --report-template "$TMP/gitleaks.tmpl" --report-path "$TMP/gitleaks.txt" "$TOP" >/dev/null 2>&1`; on ANY non-zero exit print the report (rule id, file:line) to stderr and fail; absent: one WARNING | new block after :331 | `pre-commit: gitleaks refused the staged changes (rule id and place above; a broken .gitleaks.toml also refuses)`; `pre-commit: could not write the gitleaks report template`; `pre-commit: WARNING gitleaks not installed - secret scan skipped (CI runs it)` | fail closed on rc != 0 (finding, broken config, git failure); absent = WARNING + pass (correction 1, assumption of the spec body) |
| TF3-M2 | steps 1-3 (with the `materialise "$PY_FILES"` call) move below 4g | :95-138 move | none | py_compile, ruff and black can no longer echo a staged line before every secret check ran (MEASURED, 2h) |
| R1.4 | new tracked `.gitleaks.toml` = `specs/t0b_b/gitleaks_draft.toml` (section 2h) | repo root | n/a | `[extend] useDefault = true` first; nine described allowlists; no path allowlist on docs/investigations |
| R5 | new job `secret-scan` appended to `.github/workflows/ci.yml` = `specs/t0b_b/ci_secret_scan_job.yml` (section 2i) | end of ci.yml (after channel-freshness) | CI log | no continue-on-error, no `if:`, `--exit-code 1`; a failed download, checksum, version check or git range also reds the job |
| R2.4 (step 6, NEW) | after step 5: `ESLINT_FILES=$(git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR -- 'SmartCompareApp/src/*.ts' 'SmartCompareApp/src/*.tsx')`; when non-empty and `[ -f "$TOP/SmartCompareApp/node_modules/eslint/bin/eslint.js" ] && command -v node`: split into files with no unstaged change (one by-path process: `(cd "$TOP/SmartCompareApp" && node node_modules/eslint/bin/eslint.js -- "$@")`) and partially staged files (per file `git show ":$f" \| (cd ... && node node_modules/eslint/bin/eslint.js --stdin --stdin-filename "${f#SmartCompareApp/}")`); more than 10 partial files: lint their working copies in the by-path process with a NOTE; otherwise one NOTE | appended before `exit 0` (:405) | `pre-commit: eslint found errors in staged client files`; `pre-commit: eslint found errors in the staged content of <path>`; `pre-commit: could not list the unstaged client files for eslint`; `pre-commit: NOTE more than 10 partially staged client files - eslint read their working copies`; `pre-commit: NOTE eslint not available (no node or no SmartCompareApp/node_modules) - staged client files not linted` | exit 1 (errors) and exit 2 (crash, config error) both refuse; warnings (exit 0) pass; the NOTE is printed only when a client file is staged |

No new line contains the words "sqlfluff lint"; every new message is ASCII (a hyphen, never an em dash).
The four-branch grep line (HOOK_CREDENTIAL_GREP) and its fail line stay byte-equal; only the line before
the grep changes (section 2f).

---------------------------------------------------------------------------------------------------

## 2. MEASURED ANSWERS

### (a) The gitleaks invocation inside the hook, and where it sits

1. Correction 1's line (`gitleaks git --pre-commit --staged --redact --no-banner -v`) is kept in
   substance with five MEASURED additions (probe1, probe3b, probe4, probe5):
   - `--ignore-gitleaks-allow`: a `gitleaks:allow` comment on the line silences a staged AWS-key shape
     (rc=0) without it and is reported with it (rc=1, aws-access-token). `git grep -c gitleaks:allow
     845ece15` = 1 occurrence, inside the T0b spec prose (no secret on that line), so the flag costs
     nothing today.
   - `--config "$TOP/.gitleaks.toml"` when the file exists, and `GITLEAKS_CONFIG=` /
     `GITLEAKS_CONFIG_TOML=` blanked for the call: `gitleaks git --help` lists env vars 2 and 3 above
     the repo file in precedence. MEASURED: GITLEAKS_CONFIG pointing at a rules-less config + a staged
     GitHub-token shape -> the candidate still refuses (gl_GITLEAKS_CONFIG_env_override, sh and dash).
     When the file is absent (every Phase A tmp repo) the default rules apply.
   - color forced off for gitleaks' own git diff: gitleaks 8.30.1 `--pre-commit --staged` finds NOTHING
     under `color.ui=always` or `color.diff=always` (repo config) or `git -c color.ui=always`
     (GIT_CONFIG_PARAMETERS) - a staged GitHub-token shape gave rc=0 in all three (probe4). With
     `GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=color.ui GIT_CONFIG_VALUE_0=never GIT_CONFIG_KEY_1=color.diff
     GIT_CONFIG_VALUE_1=never` on the call it reports github-pat in all four configs, including on top
     of GIT_CONFIG_PARAMETERS='color.ui=always'. `diff.external=true` does not blind gitleaks.
   - no `-v`: a template report (`{{ .RuleID }} {{ .File }}:{{ .StartLine }}`) written to `$TMP`
     and printed by the hook carries the rule id, file and line and no content; `-v` would print the
     redacted line context. Correction 1 needed `-v` only to see file and rule.
   - `--log-level error`, stdout and stderr of gitleaks to /dev/null (the report is the only output).
2. Cost: 0.38-0.56 s per call (probe1); 6/6 checked sentinel runs with no 12-character piece in the
   output (correction 1 had 16/16).
3. WHERE: gitleaks must run after the four regex checks and before the Python checks.
   - It cannot run first: the Phase A file pins `red_jwt_refused` on MSG_NEW_SHAPES, and gitleaks'
     default generic-api-key rule refuses the same staged line `token = <runtime JWT>` (probe1 A_jwt
     rc=1). On this box (gitleaks on PATH, and the Phase A harness keeps PATH) a gitleaks-first hook
     would turn that frozen node red.
   - Default gitleaks rules do NOT catch the other Phase A sentinels (probe1: the sk-, documentation
     AWS key, Slack, PEM header, the 12-char credentialed URL, the URL_VALUE .env value, the `++JWT`
     line, the musk slug: all rc=0), so with gitleaks after 4/4a/.env-name/4e/4b every Phase A
     refusal keeps its message.
   - It must run before py_compile and ruff for M2 (TF3): base hook + staged `bad.py` with a syntax
     error on a line holding a runtime GitHub-token shape -> rc=1 "python syntax error in staged
     files" and a 12-character piece of the token IN the output (sh and dash); candidate -> rc=1
     gitleaks refusal, no piece. The same for the four-branch regex: `bad.py` with the documentation
     AWS shape on the syntax-error line: base echoes it, candidate refuses with the four-branch
     message, no piece (probe3c).
   - No existing check is made to skip on a passing commit: the move only changes WHICH refusal comes
     first when two would refuse. Measured with the real frozen tests against the candidate in a
     detached scratch worktree (section 3.4).

### (b) gitleaks against binary, UTF-16 and NUL-byte staged files (#315 reproduced)

probe1, runtime-built strong AWS-key and strong JWT shapes, `gitleaks git --pre-commit --staged`:
```
                 NUL   UTF-16LE+BOM  UTF-16LE  attr binary  attr -diff  textconv=true
strong AWS key   rc=0  rc=0          rc=0      rc=0         rc=0        rc=0
strong JWT       rc=0  rc=0          rc=0      rc=0         rc=0        rc=0
text control:    AWS rc=1 aws-access-token; JWT rc=1 jwt; sk- rc=1 generic-api-key
```
New beyond #315: gitleaks also misses the `-diff` attribute and the textconv driver cases. No gitleaks
flag changes this (it reads `git diff`), so the hook's own --text/--no-textconv diff and the 4e
refusal are the only closure.

### (c) --text --no-textconv placement and the round-2 shim argv

- Placement AFTER -U0: `git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv`. The
  round-2 shims test `case " $* " in *" diff --cached --no-color --no-ext-diff -U0 "*)`; the padded
  argv `" diff --cached --no-color --no-ext-diff -U0 --text --no-textconv > ..."` still contains that
  substring (the redirect is not argv), so the shim still intercepts the call - MEASURED: the r3
  shims fire on the candidate (they fail for a different reason, section 2f).
- Effect (probe2, probe3): textconv=true driver: 0 added lines without the flags, 1 with them; `-diff`
  attribute: 0 -> 1. Candidate refusals, sh AND dash: NUL+JWT -> MSG_NEW_SHAPES; textconv+.env value
  -> MSG_ENV_VALUE naming FAKE_SERVICE_KEY; textconv+AWS doc key -> four-branch message. Base: rc=0 on
  all three.
- UTF-16 stays invisible to every regex even with --text (one NUL between characters); 4e closes it.

### (d) The numstat "-<TAB>-" detector (`git diff --cached --numstat --no-textconv`)

probe2 (`--diff-filter=ACMR`, without and with filter shown):
```
kind                 ACMR line                    flagged
PNG                  -\t-\ta.png                  yes
NUL text             -\t-\tn.txt                  yes
UTF-16LE             -\t-\tu.txt                  yes
attr -diff           -\t-\ta.json                 yes
attr binary          -\t-\ta.json                 yes
textconv driver      1\t0\ta.dat                  no   (text: covered by --text --no-textconv)
empty file           0\t0\tempty.txt              no
rename (PNG)         -\t-\ti.png => j.png         yes, but the path field is "old => new"
deletion (PNG)       (none; unfiltered: -\t-)     no   (deletions excluded by ACMR)
gitlink              1\t0\tsub                    no
symlink              1\t0\tlink                   no
```
Consequences built into 4e: `--no-renames` (a rename becomes an add of the new path, so the path field
is a plain path - MEASURED: renaming an allowlisted PNG out of the allowlist -> refused "misc/a.png";
renaming it inside the allowlist -> passes, sh and dash); `--diff-filter=ACMR` (a deleted binary
passes - MEASURED); `core.quotePath=false` (non-ASCII stays raw; a path with a TAB, quote or newline is
C-quoted and so refused - fail closed). numstat output is not colored: `color.ui=always` + a PNG in
`misc/` -> still refused (probe5).

### (e) The tracked binary population at 845ece15 and the allowlist design

Detector: git's own, `git diff --numstat --no-textconv 4b825dc6 845ece15` (empty tree vs HEAD),
lines starting `-<TAB>-`. Cross-check: `git ls-files` by binary extension (png, jpe?g, gif, webp, ico,
ttf, otf, woff2?, pdf, zip, gz, svg, mp4, mov, wav, mp3, db, sqlite, bin, exe, dll, so, jar, keystore,
p12, pfx, der, cer) = 58 = the detector's 58. No `.gitattributes` is tracked.
```
tracked files 2941, binary 58 (.png 46, .jpeg 6, .ttf 6)
SmartCompareApp/assets 4 | SmartCompareApp/assets/brand 3 | SmartCompareApp/assets/fonts 3
app/static 1 | docs/brand 1 | docs/claude-design-handoff/assets 8 | docs/claude-design-handoff/fonts 3
docs/claude-design-handoff/screenshots 22 | docs/investigations/2026-09-29-session-69-state/icon-candidates 11
test_images 2
```
(Step 6 said "65 tracked binary files in 13 directories"; not reproduced at 845ece15 by either method.
The list is `binary_paths_845ece15.txt` in the notes folder.)
`--text` false positives over every tracked binary blob (5,984,470 bytes, Python equivalents of the
four-branch ERE, JWT_RE, CREDURL_RE): 0 hits.

PROPOSED allowlist (inline `case` in the hook, extension per directory; `*` in a sh case pattern also
crosses `/`, which is what the nested asset dirs need):
```
SmartCompareApp/assets/*.png|SmartCompareApp/assets/*.ttf) ;;
app/static/*.png|docs/brand/*.png|test_images/*.jpeg) ;;
docs/claude-design-handoff/*.png|docs/claude-design-handoff/*.jpeg|docs/claude-design-handoff/*.ttf) ;;
docs/investigations/*/icon-candidates/*.png) ;;
```
Judged (zero newly refused tracked files / bypass surface / dash+MSYS portability / cost per commit):
| Design | Newly refused tracked | Bypass surface | Portability | Cost |
|---|---|---|---|---|
| inline case, extension per directory (PROPOSED) | 0 (pinned by a test over the tracked population, section 3) | a UTF-16 or NUL dump named `<asset dir>/x.png`; nothing outside 10 directories x 3 extensions | pure case: MEASURED sh and dash | 0 spawns |
| extension-per-directory globs in a tracked file (e.g. .github/binary-paths.txt) | 0 | same as inline | needs a while-read of the file + case; fine | 1 file read, 0 spawns |
| pure extension list (*.png, *.jpeg, *.ttf anywhere) | 0 | any path in the repo with those names | trivial | 0 |
| exact path list (58 lines) | 0 | none for existing paths | trivial | 0 |
Rejected: the pure extension list (largest bypass: `anything/x.png`); the exact path list (every new
screenshot, icon candidate or font needs a hook edit - the icon-candidates and screenshots dirs grow);
the tracked file (one more file to protect, and a PR can widen it without touching the hook - the hook
diff is what reviewers read). OPTIONAL hardening, ruling Q2b: for an allowlisted path also check the
blob's first bytes - `git cat-file blob ":$p" | od -An -tx1 -N8 | tr -d ' \n'` MEASURED portable under
sh and dash (PNG -> 89504e470d0a1a0a; a UTF-16 dump named .png -> fffe690064002000), so `.png` must
start 89504e47, `.jpeg` ffd8ff, `.ttf` 00010000; this closes the rename-a-dump-to-.png bypass at one
3-process pipe per staged binary (0 on a normal commit).

### (f) #316: the rewritten four-branch pipeline, and the frozen nodes that must change

Rewritten (cand/pre-commit):
```
git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv > "$STAGED_DIFF" ||
  fail "could not read the staged diff (git diff failed)"
...
if awk "$ADDED_LINES_AWK" "$STAGED_DIFF" | \
   <the four-branch grep line, byte-equal> ; then
  <the four-branch fail line, byte-equal>
fi
```
probe3 (byte copy of the hook in scratch repos, sh AND dash, base vs candidate):
```
scenario                         base           candidate
pin sk- / AWS doc key / Slack / PEM header   rc=1 four-branch msg  rc=1 four-branch msg (4 x 2 shells)
pin musk- slug                   rc=0           rc=0
color.ui=always + AWS doc key    rc=0 (HOLE)    rc=1 four-branch msg
color.diff=always + AWS doc key  rc=0 (HOLE)    rc=1 four-branch msg
diff.external=true + AWS doc key rc=0 (HOLE)    rc=1 four-branch msg
"++" + AWS doc key (TF3 hole)    rc=0 (HOLE)    rc=1 four-branch msg
```
Real frozen tests against the candidate (a detached scratch worktree at 845ece15 with only the hook
and ci.yml replaced; bounded runner): EXACTLY these nodes change, nothing else:
1. `tests/test_ci_gates.py::test_hook_keeps_the_four_credential_branches_byte_equal` -
   old: `assert lines[i - 1] == HOOK_CREDENTIAL_PIPE` with HOOK_CREDENTIAL_PIPE = the bare
   `if git diff --cached -U0 | grep -E '^\+' | grep -Ev '^\+\+\+' | \` line;
   new: HOOK_CREDENTIAL_PIPE = `if awk "$ADDED_LINES_AWK" "$STAGED_DIFF" | \` and one added assert
   that the hook holds the line `git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv
   > "$STAGED_DIFF" ||`. HOOK_CREDENTIAL_GREP (the ERE) and HOOK_CREDENTIAL_FAIL stay as they are, so
   the ERE string is still pinned byte-equal (MEASURED: only the pipe assertion failed).
2. `tests/test_precommit_hook_round2.py::TestPreCommitHookRound2::test_scenario[{sh,dash}-r3_failed_git_diff_refuses_the_commit]` -
   old: `_assert_refused(run, MSG_ENV_CHECK_FAILED)`; MEASURED now: rc=1 with
   "could not read the staged diff (git diff failed)" (the single diff fails first);
   new: `_assert_refused(run, "could not read the staged diff")`, keep `_assert_no_piece`.
3. `tests/test_precommit_hook_round2.py::...[{sh,dash}-r3_allexport_keeps_values_out_of_child_environments]` -
   old: `run.out.count("T0B-SHIM-RAN") == 2`; MEASURED now: 1 (one staged diff, read before the .env
   parse); new: `== 1`. The leak check stays; its reach to processes started AFTER the parse moves to
   a new Phase B node (gitleaks shim under sh -a, section 3).
4. `tests/test_precommit_hook_round2.py::...[{sh,dash}-d1_bulk_text_without_the_value_passes_with_no_message]` -
   fails only where gitleaks is ABSENT (CI backend-tests; MEASURED by stripping gitleaks from PATH:
   "rc=0; last output lines: ['pre-commit: WARNING gitleaks not installed ...']"); green here with
   gitleaks present. old: `run.rc == 0 and run.hook_messages() == []`; new: `run.rc == 0 and
   run.refusals() == []` and every hook message starts with `pre-commit: WARNING gitleaks not
   installed` (the D1 intent - no crash line, no refusal - kept; refusals() already excludes WARNING
   and NOTE lines). Ruling Q1.
Everything else measured green against the candidate, every frozen hook node run (four -k subsets,
[pyt] tags t0bb-cand-a / -r2 / -rest / -last, each status=OK except -r2 = the 4 nodes above): ALL 62
Phase A nodes (31 scenarios x sh, dash: every four-branch pin, musk, JWT, credentialed URL, every .env
value form, the common-dir fallback, black-absent, both skill refusals, rename, staged-blob, the TR6
pass nodes) and 26 of 30 round-2 nodes, with gitleaks present; pin_clean, pin_musk, black-absent and
valid-skill also with gitleaks absent; 197/198 of test_ci_gates + test_channel_freshness +
test_hermeticity_pins + test_sqlfluff_config with the candidate hook AND the secret-scan job appended
(the 1 = node 1 above). The musk- slug passes (sh, dash, real test node).

### (g) TF7: the Z-trailer equivalent for 4a and the four-branch line

Recommended (implemented in the candidate): ONE staged diff written to `$TMP/staged.diff` with git's
exit status checked directly (`> "$STAGED_DIFF" || fail ...`). This is the Z-trailer guarantee for all
three readers at once: a failed git diff refuses before step 4. MEASURED with a git shim that fails
both diff spellings, staged AWS doc key, no .env: base rc=0 (the TF7 hole: nothing refused), candidate
rc=1 "could not read the staged diff (git diff failed)", sh and dash. 4b keeps its Z trailer
(`cat "$STAGED_DIFF" && printf 'Z\n'`) so a dying .env parse still refuses (r3_parse_crash green).
Alternative (not built, not measured): keep three pipes and give the four-branch line and 4a a
`{ git diff ... && printf 'Z\n'; } | awk <added-lines-plus-Z> | grep -E -e '<ERE>' -e '^Z$' |
awk '<exit 1 on a hit, 2 on no Z>'` tail, then `case $?`; it changes the pinned grep line (the ERE
moves inside `-e`), spawns three diffs instead of one, and still changes nodes 2 and 3.
The single-diff file makes #317 PER-4 bullet 1 FREE (one staged diff feeding 4, 4a and 4b): it rides
along by construction. Stated limit: an awk that dies while reading the file makes step 4 / 4a pass
on an empty stream (grep sees nothing); 4b still refuses. Not fixed because `d1_failed_awk_refuses_the_commit`
(frozen) shims EVERY awk and expects the .env-check message; making 4/4a refuse on awk death would
refuse first with another message.

### (h) The .gitleaks.toml DRAFT and its acceptance

File: `specs/t0b_b/gitleaks_draft.toml` (copy it to the repo root as `.gitleaks.toml`, LF). Content
summary: `title`; `[extend] useDefault = true` FIRST; nine `[[allowlists]]`, each with a description:
1. sha256 digest after a file name - regexTarget match `\.[A-Za-z]{1,5}"?\s*[:=,]\s*"?[0-9a-f]{64}\b`
   (the extension anchor keeps a bare 64-hex value, the shape of a rotated ADMIN_API_KEY, reportable);
2. OpenAI error text with a SHORT fake key - match `API key provided: sk-[A-Za-z0-9_-]{0,19}(?:[^A-Za-z0-9_-]|$)`
   (shorter than the hook's own 20+ floor);
3. password fixtures under tests/ only - condition AND, paths `^tests/`, match
   `(?i)(?:new_|current_|old_)?password"\s*:\s*"`;
4. short access_token fixture in a documented login response - match `access_token"\s*:\s*"[^"\s]{1,20}"`;
5. short id in a workflow script row - match `\bkey:\s*'[A-Za-z0-9-]{1,20}'$` (a UUID is 36 chars);
6. pytest name - secret `^test_[a-z0-9]+(?:_[a-z0-9]+)+$`;
7. UPPER_SNAKE constant = small integer - secret `^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+=[0-9]{1,6}$`;
8. lower_snake = Python literal - secret `^[a-z][a-z0-9]*(?:_[a-z0-9]+)+=(?:True|False|None)\.?$`;
9. already redacted or truncated - secret `REDACTED`, `\*{3,}`, `\.\.\.` (correction 3b).
Entries 6-9 use the default regexTarget (secret): narrower than match, because a real value next to the
same keyword is still reported (MEASURED: `test_api_key = "<64 hex>"` stays rc=1). Correction 3(b)
says "line or match": ruling Q3.

Acceptance (probe6, `gitleaks git --log-opts=<merge>^1..<merge>^2 --redact --ignore-gitleaks-allow`
over each of the last 60 first-parent merges at 845ece15, template report rule/file/commit/line):
```
default rules : 9 of 60 PRs red (#297 #289 #256 #214 #209 #208 #197 #195 #194), 30 findings
                (29 generic-api-key + 1 sentry-access-token), 30.1 s for all 60 ranges, 0 errors
draft config  : 0 of 60 PRs, 0 findings, 29.5 s, 0 errors
```
Masked shapes of the 30 (length + class, probe6c): 19 x 64-hex lower-case digest after a file name
(api.ts:, authService.ts:, `"<file>",\n "<hex>"` pairs; the one sentry-access-token hit is one of
them); 4 x the OpenAI error text with a 17-22 char fake key; 2 x `"new_password": "<12>"` in
tests/test_retro_w1_9_429.py; 1 x `"access_token":"<13>"` in the U13 spec; 1 x `key: '<14-char
kebab id>'` in a workflow script; 1 x a 36-char pytest name; 1 x `UPPER_SNAKE=<int>`; 1 x
`lower_snake=True.`. Every one is a false positive by shape. No shape needed a path entry; no stated
limit is left over the 60 ranges.
Runtime sentinels WITH the draft (probe7, staged hook form): strong JWT rc=1 jwt; strong AWS key rc=1
aws-access-token; strong sk- rc=1 generic-api-key; GitHub-token shape rc=1 github-pat;
`ADMIN_API_KEY = "<64 hex>"` rc=1; the OpenAI error text with a 46-char key rc=1; `{"access_token":
"<JWT>"}` rc=1 jwt; `{ key: '<uuid>' }` rc=1; `test_api_key = "<64 hex>"` rc=1. Benign shapes with
the draft: file digest rc=0, workflow id rc=0. CI log mode `--log-opts=<base>..<head>` with the draft:
AWS key commit rc=1. `tomllib`: extend.useDefault True, no top-level [[rules]], 9 allowlists, all
described. The config file itself committed in a range: default rules rc=0.

### (i) The CI job YAML DRAFT and the existing ci.yml pins

File: `specs/t0b_b/ci_secret_scan_job.yml` (append to ci.yml with CRLF to match the working copy; the
measured append kept CRLF and `yaml.safe_load` parses 7 jobs). Shape: `secret-scan`, `runs-on:
ubuntu-latest`, `timeout-minutes: 10`, job-level `permissions: contents: read`, no job or step `if:`,
no `continue-on-error`; checkout `fetch-depth: 0`; install step: `curl -sSfL -o
"$RUNNER_TEMP/gitleaks.tgz" .../v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz`, `echo "<sha256>
$RUNNER_TEMP/gitleaks.tgz" | sha256sum -c -` with the orchestrator's checksum
551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb, `tar -xzf ... gitleaks`,
`test "$(.../gitleaks version)" = "8.30.1"`; scan step with STEP-level env (EVENT_NAME, PR_BASE =
`github.event.pull_request.base.sha`, PR_HEAD = `...head.sha`, PUSH_BEFORE = `github.event.before`,
PUSH_SHA = `github.sha`): pull_request -> `$PR_BASE..$PR_HEAD`; push -> `$PUSH_BEFORE..$PUSH_SHA`, or
`-1 $PUSH_SHA` when before is the all-zero sha; a tracked `.gitleaksignore` fails the job; the config is
read from the RANGE BASE (`git show "$CFG_REV:.gitleaks.toml"`) when it exists there, else default
rules; `gitleaks git --log-opts="$RANGE" --redact --no-banner -v --exit-code 1 --ignore-gitleaks-allow
[--config ...] .`. Comment block: detection not prevention, a red scan means rotate the key first then
rewrite, the hook is the prevention layer, same-origin checksum = integrity not authenticity.
Beyond corrections 4/5 (rulings Q5): the base-config read, the .gitleaksignore guard (MEASURED:
gitleaks honours a `.gitleaksignore` in the scanned directory even with `--gitleaks-ignore-path`
pointing at an empty or missing path), `--ignore-gitleaks-allow`, `timeout-minutes`.
Existing pins named in correction 4(d), all present at 845ece15, all green with the job appended:
- `tests/test_hermeticity_pins.py::test_ci_job_level_env_references_only_job_level_contexts` (:1358):
  every job's JOB-level env may use only github/needs/strategy/matrix/vars/secrets/inputs; the draft
  has no job-level env (the github contexts are in step env).
- `tests/test_ci_gates.py::test_channel_freshness_is_non_blocking_until_the_dated_flip` (:1176): every
  ci.yml comment line with `NON-BLOCKING until <date>` must carry the single date 2026-10-07; the draft
  never writes that phrase.
- `tests/test_ci_gates.py::test_black_is_pinned_to_an_exact_version_in_ci` (:247) and
  `::test_ci_black_pin_matches_the_dependency_lock` (:267): every job's `run:` lines with "black" and
  "install" must pin `black==X.Y.Z` equal to the lock; the draft never names black.
Cost: the 60-range local scan took 0.5 s per range; CI = checkout at depth 0 (29.41 MiB pack, already
paid by channel-freshness) + download + verify; one billed minute per run (estimate; CI not run).
Required check: adding `secret-scan` to branch protection is Ahmed's setting (R6), not this PR.

### (j) ESLint (correction 9), re-measured

sc-s70-u4b/SmartCompareApp, ESLint v9.39.4, node v24.11.1, flat config `eslint.config.js`, no --fix,
no --cache, `git status --porcelain` empty before and after:
```
by path, api.ts                              2,091 ms rc=0
by path, api.ts + HomeScreen.tsx (1 process) 4,277 ms rc=0
stdin,  api.ts (--stdin-filename src/services/api.ts)        2,125 ms rc=0
stdin,  HomeScreen.tsx (--stdin-filename src/screens/...)     4,279 ms rc=0
`--` before the paths                        rc=0 (accepted)
stdin with a parse error                     "Parsing error" reported (exit code not captured)
```
So one process costs about 2 s of start-up plus about 2 s for a 58 KB screen; two files in one process
(4.3 s) beat two stdin processes (6.4 s). Shim measurements of the candidate step (probe5, dash): a
fully staged file -> ONE by-path call `node_modules/eslint/bin/eslint.js -- src/screens/S0.tsx` from
cwd SmartCompareApp; three fully staged files -> one call with three paths; a partially staged file ->
one `--stdin --stdin-filename src/screens/S0.tsx` call whose stdin is the STAGED content (not the
working copy); shim exit 1 -> refused; exit 2 -> refused; exit 0 -> pass; 11 partially staged files ->
NOTE + one by-path call over 11 working copies; a staged client file with no node_modules -> NOTE, rc 0;
no client file staged -> no NOTE, no message. Cap: 10 partially staged files (worst case about 10 x
2-4 s); above it the working copies are linted in one process with the NOTE.

### Cost per commit (healthy box, median of 3, gitleaks present, default rules)
```
                 base (845ece15)   candidate
empty   sh       0.64 s            1.32 s
empty   dash     0.60 s            1.22 s
10 files sh      1.16 s            1.82 s   (7 text + 3 .py)
10 files dash    1.08 s            1.60 s
```
Delta about +0.5 to +0.7 s per commit, most of it the gitleaks call (0.4-0.55 s). Without gitleaks the
delta is one git diff + one numstat. ESLint adds 2-4 s per client process only when SmartCompareApp/src
files are staged and node_modules exists.

### Merge commits (ruling Q6)
MEASURED (probe8): a clean `git merge --no-ff` does NOT run `.githooks/pre-commit` (there is no
pre-merge-commit hook); concluding a CONFLICTED merge with `git commit` DOES, over the whole merged-in
diff: a non-allowlisted PNG committed on the side branch with --no-verify -> the merge commit is refused
"staged file is binary to git and not a known asset path: misc/side.png". The Phase A checks already
behave the same way on that path.

---------------------------------------------------------------------------------------------------

## 3. THE TEST LIST

### 3.1 New files (TR3: Phase A files frozen except the four nodes of 2f)
- `tests/test_precommit_hook_phase_b.py` - functional, tmp repo per scenario, the Phase A harness
  imported (HookRepo, HookRun, SH, SHELLS, _shell_ids, _assert_refused, _assert_passed, _akia, _jwt,
  _fake, PREFIX, MSG_*), a `_shim(r, tool, body)` copied from round 2. LF, ASCII, every sentinel
  runtime-built (a GitHub-token shape as `"gh" + "p_" + ...`). One node per scenario x shell.
- `tests/test_secret_scan_static.py` - static pins on the hook text, `.gitleaks.toml` (tomllib) and
  the ci.yml `secret-scan` job (yaml, the `_load` / `_run_text` / `_steps` helpers re-implemented
  locally or imported from tests.test_ci_gates).
- `tests/test_gitleaks_config.py` - functional gitleaks with the repo config; every node skips with
  "gitleaks not on PATH" when absent (CI backend-tests); the PR-range acceptance node also skips when
  the merge commits are not in the clone (CI depth 1).

### 3.2 Shim designs
- gitleaks shim: an sh script `gitleaks` first on PATH (round-2 `_shim` pattern), body records `$*`
  and `env | grep -c '^GIT_CONFIG_KEY_0=color.ui'` (never an env value) to a file, then `exit $RC`
  (RC fixed in the body). Works under sh and dash (MEASURED probe5).
- gitleaks absent: PATH without every dir holding `gitleaks` / `gitleaks.exe` (the black-absent pattern;
  MEASURED: stripping the WinGet dir removes it; git still resolves).
- node/eslint shim: an sh script `node` first on PATH that appends `ARGV $*`, the basename of `$PWD`,
  and, when `--stdin` is in `$*`, the stdin bytes between markers, to a log; `exit $RC`. Plus a dummy
  file `SmartCompareApp/node_modules/eslint/bin/eslint.js` in the tmp repo (untracked). MEASURED probe5.
- git argv shim: the round-2 `_shim(r, "git", ...)` failing any call whose padded argv contains
  ` diff --cached --no-color --no-ext-diff -U0 ` (covers the new single diff).

### 3.3 Scenarios of tests/test_precommit_hook_phase_b.py
R = RED at base 845ece15 (reason: the message is absent and rc=0 unless noted); P = PIN (green at base
and after); L = needs real gitleaks (skips without it: local only). Messages (binding constants):
MSG_DIFF_FAILED "could not read the staged diff", MSG_BINARY "staged file is binary to git and not a
known asset path:", MSG_GITLEAKS "gitleaks refused the staged changes", MSG_GITLEAKS_ABSENT "WARNING
gitleaks not installed", MSG_ESLINT "eslint found errors in staged client files", MSG_ESLINT_STAGED
"eslint found errors in the staged content of", MSG_ESLINT_ABSENT "NOTE eslint not available",
MSG_ESLINT_CAP "NOTE more than 10 partially staged client files".
| # | scenario | kind | expectation (candidate MEASURED where marked *) | kills |
|---|---|---|---|---|
| 1 | gl_shim_rc1_refuses | R | shim exit 1 on a clean change -> MSG_GITLEAKS * | 14b (rc ignored) |
| 2 | gl_shim_argv_flags | R | shim argv has `git`, `--pre-commit`, `--staged`, `--redact`, `--no-banner`, `--ignore-gitleaks-allow`, `--report-format template`, and `--config <TOP>/.gitleaks.toml` when the tmp repo has one; color override present in its env * | 14a (no --staged), allow-flag dropped, config dropped, color override dropped |
| 3 | gl_shim_rc2_refuses | R | shim exit 2 -> MSG_GITLEAKS | broken-config fail-open |
| 4 | gl_absent_warns_and_passes | R | gitleaks stripped -> rc 0, MSG_GITLEAKS_ABSENT, no refusal * | missing WARNING |
| 5 | gl_shim_refusal_precedes_python | R (base: MSG_PY_SYNTAX first) | shim exit 1 + staged `def f(:` -> first refusal MSG_GITLEAKS * | gitleaks moved after the Python checks (M2) |
| 6 | m2_regex_refusal_precedes_python_no_echo | R (base: MSG_PY_SYNTAX + echo) | staged bad.py, AWS doc key on the syntax-error line -> four-branch msg, no 12-char piece * | secret block moved back below step 1-3 |
| 7 | gl_allexport_keeps_values_out_of_gitleaks_env | R (base: shim never runs) | sh -a, FAKE .env value with marker, gitleaks shim reports marker presence -> shim ran, no leak | allexport restored before 4g |
| 8 | 316_color_ui_always | R (base rc 0) | AWS doc key -> four-branch msg * | bare git diff restored |
| 9 | 316_color_diff_always | R | same * | same |
| 10 | 316_diff_external | R | same * | --no-ext-diff dropped |
| 11 | 316_plusplus_line | R | `++` + AWS doc key -> four-branch msg * | `grep -Ev '^\+\+\+'` restored |
| 12 | tf7_failed_diff_refuses_without_env | R (base rc 0) | git shim fails the diff, no .env -> MSG_DIFF_FAILED * | `\|\| fail` on the diff dropped |
| 13 | 315_nul_jwt | R | NUL + runtime JWT, non-asset path -> MSG_NEW_SHAPES * | --text dropped |
| 14 | 315_textconv_env_value | R | textconv=true driver + FAKE .env value -> MSG_ENV_VALUE naming FAKE_SERVICE_KEY * | --no-textconv dropped |
| 15 | 315_textconv_aws | R | textconv + AWS doc key -> four-branch msg * | same |
| 16 | 315_minus_diff_env_value | R | `*.json -diff` + .env value -> MSG_BINARY a.json * | binary refusal removed |
| 17 | 315_utf16_aws | R | UTF-16LE+BOM + AWS doc key -> MSG_BINARY * | same |
| 18 | 315_nul_env_value | R | NUL + .env value -> MSG_BINARY * | same |
| 19 | 315_png_outside_allowlist | R | PNG at misc/new.png -> MSG_BINARY * | allowlist widened to *.png |
| 20 | 315_rename_png_out_of_allowlist | R | git mv assets PNG to misc/ -> MSG_BINARY misc/a.png * | rename handling |
| 21 | 315_png_allowlisted_passes | P | the bytes of the repo's own SmartCompareApp/assets/icon.png (read from REPO_ROOT, issue #315 acceptance) staged at that path -> rc 0 (* measured with a 1x1 PNG at SmartCompareApp/assets/new.png) | allowlist narrowed / --text false positive |
| 22 | 315_rename_within_allowlist_passes | P | git mv within SmartCompareApp/assets -> rc 0 * | --no-renames dropped |
| 23 | 315_delete_binary_passes | P | git rm a committed misc PNG -> rc 0 * | ACMR dropped |
| 24 | 315_empty_file_passes | P | empty file -> rc 0 * | numstat parse error |
| 25 | eslint_full_error_blocks | R | shim exit 1 -> MSG_ESLINT; one by-path call `-- src/screens/S0.tsx`, PWD SmartCompareApp * | 14i errors not blocking |
| 26 | eslint_crash_blocks | R | shim exit 2 -> MSG_ESLINT * | rc 2 ignored |
| 27 | eslint_partial_reads_staged_content | R | partially staged -> one --stdin call, stdin == staged bytes, --stdin-filename src/screens/S0.tsx * | 14i working tree linted |
| 28 | eslint_partial_error_blocks | R | partial + exit 1 -> MSG_ESLINT_STAGED SmartCompareApp/src/screens/S0.tsx * | partial path not blocking |
| 29 | eslint_cap_over_10_partial | R | 11 partial -> MSG_ESLINT_CAP + one by-path call with 11 paths * | cap missing |
| 30 | eslint_absent_notes | R | staged src file, no node_modules -> MSG_ESLINT_ABSENT, rc 0 * | missing NOTE |
| 31 | eslint_warnings_pass | P | shim exit 0 -> rc 0 | 14i warnings blocking (`--max-warnings 0`) |
| 32 | eslint_no_client_file_no_note | P | only a .py staged -> no hook message * | NOTE on every commit |
| 33 | gl_real_staged_only_secret_refused | R,L | runtime GitHub-token shape staged, working copy cleaned -> MSG_GITLEAKS | 14a (real) |
| 34 | gl_real_unstaged_secret_passes | P,L | token only in the working tree -> rc 0 | --pre-commit without --staged |
| 35 | gl_real_color_ui_always_refused | R,L | color.ui=always + token -> MSG_GITLEAKS * | color override dropped |
| 36 | gl_real_allow_comment_refused | R,L | token + `gitleaks:allow` (concatenated) -> MSG_GITLEAKS * | --ignore-gitleaks-allow dropped |
| 37 | gl_real_env_config_override_refused | R,L | GITLEAKS_CONFIG -> rules-less file, token staged -> MSG_GITLEAKS * | env blanking dropped |
| 38 | gl_real_m2_no_echo | R,L | bad.py syntax error on the token line -> MSG_GITLEAKS, no 12-char piece * | M2 |
Counts: 38 scenarios; locally (sh + dash, gitleaks present) 76 nodes; CI (dash as sh, no gitleaks)
32 scenarios run + 6 skip = 38 nodes collected. Runtime here at today's 1.2-1.4 s per node: about
100 s for 76 nodes (budget 7-12 s per node on a slow day: 9-15 min; run it alone, bound 1200).

### 3.4 Static file tests/test_secret_scan_static.py (all R at base unless noted, ~22 nodes, < 5 s)
Hook: the single diff line exact; `--text --no-textconv` AFTER `-U0` on it; no `git diff --cached -U0 |`
left; the four-branch pipe reads `"$STAGED_DIFF"`; the numstat line carries `--no-textconv`,
`--no-renames`, `--diff-filter=ACMR`, `core.quotePath=false`; the gitleaks line carries `--pre-commit`,
`--staged`, `--redact`, `--ignore-gitleaks-allow`, `GIT_CONFIG_KEY_0=color.ui`, `GITLEAKS_CONFIG=`;
`pre-commit: WARNING gitleaks not installed` present; ORDER: four-branch < new-shapes fail < binary
fail < env-value msg < gitleaks fail < `py_compile` < `-m black` < skill fail < `sqlfluff lint` <
eslint fail (relative order only, TR3); ESLint lines carry `--stdin`, `--stdin-filename`, the `-gt 10`
cap, `eslint.js` by path and no `--fix`, `--cache` or `--max-warnings`; no new line contains "sqlfluff
lint"; no line carries a non-ASCII byte unless the same line is one of the 11 non-ASCII lines of the
845ece15 hook (em dashes in comments and two messages). Config: tomllib extend.useDefault
is True; no top-level [[rules]]; every allowlist has a description; no `paths` entry matching
docs/investigations; config file present. CI: job `secret-scan` exists; checkout `fetch-depth: 0`;
`8.30.1` in the URL and the version check; the 64-hex checksum; `sha256sum -c`; `--redact`; `-v`;
`--ignore-gitleaks-allow`; both event ranges (`github.event.pull_request.base.sha`,
`github.event.before`, the all-zero branch); no `if:` at job or step level; no `continue-on-error`;
`permissions == {"contents": "read"}`; the `.gitleaksignore` guard; the base-config read. Kills 14(l):
fetch-depth dropped, --redact dropped, sha256 line removed, job gated by `if:`; and 14(c) via tomllib.
Tracked-population node (R at base, where the hook has no allowlist): every path git reports as
binary at HEAD (`git diff --numstat --no-textconv <empty tree> HEAD`, lines `-<TAB>-`) matches the
hook's allowlist `case` (parse the four allowlist lines of the hook and test with fnmatch, whose `*`
also crosses `/`, like a sh case pattern; skip outside a git checkout) - pins "zero newly refused".

### 3.5 tests/test_gitleaks_config.py (L, skips without gitleaks; ~14 nodes, ~10 s + 30 s range node)
Staged in a tmp repo with `--config <repo>/.gitleaks.toml` (correction 2): runtime JWT, AWS key, sk-,
GitHub-token, `ADMIN_API_KEY = "<64 hex>"` -> rc=1 each (kills 14c: a config without useDefault gives
rc=0, MEASURED in correction 2); benign file digest, workflow id, pytest name -> rc=0; a config written
WITHOUT `[extend]` -> rc=0 on the JWT (the mutant is measured inside the test, which proves the test
can see it); PR-range acceptance: the nine PR merges listed in 2h, `--log-opts=<m>^1..<m>^2`, 0 findings
(skips when a merge sha is not in the clone).

### 3.6 Mutants (each on a byte copy of the GREEN file, restored by sha256)
14a gitleaks without `--staged` (nodes 2, 33, 34); 14b rc ignored `|| true` (1, 3); 14c useDefault
removed (3.5); 14i warnings blocking `--max-warnings 0` (31), errors not blocking (25, 28), staged read
replaced by working tree (27); 14l fetch-depth, --redact, sha256 line, job `if:` (3.4). Plus: #315
`--text` dropped (13), `--no-textconv` dropped (14, 15), 4e removed (16-19), allowlist widened to
`*.png` (19), `--no-renames` dropped (22); #316 four-branch back to `git diff --cached -U0 |` (8-10),
`grep -Ev '^\+\+\+'` re-added in front of the ERE (11); TF7 `|| fail` dropped from the diff (12);
M2 Python steps moved back above the secret block (5, 6); color override dropped (2, 35);
`--ignore-gitleaks-allow` dropped (2, 36); env blanking dropped (37).

### 3.7 CI behaviour
backend-tests: no gitleaks, no SmartCompareApp/node_modules, sh = dash (the dash column skips itself):
the L nodes skip with "gitleaks not on PATH"; the ESLint nodes run through the node shim; the absent
WARNING path is the only gitleaks path exercised for real; the PR-range node skips (depth 1). mawk is
CI's awk: NOT VERIFIED here (no mawk on this box) that mawk passes NUL-bearing lines through
ADDED_LINES_AWK and ENV_MATCH_AWK - nodes 13, 18, 21 exercise it in CI; if 21 (allowlisted PNG passes)
reds in CI only, 4b's awk is choking on binary bytes (fix: `LC_ALL=C` already set for 4b; add it to the
two ADDED_LINES_AWK calls).

---------------------------------------------------------------------------------------------------

## 4. FILES

Touched by GREEN: `.githooks/pre-commit` (Edit tool on the CRLF working copy; line-level diff; the
reference is cand/pre-commit, sha256 e0968596e2351a442948330f95f4c2f0dcc4f1e689934387b6fe3e83480d570c,
24,167 bytes LF; base blob de0a4bd8...7dc6, 18,067 bytes), `.gitleaks.toml` (new, LF, from
gitleaks_draft.toml), `.github/workflows/ci.yml` (append the job, CRLF like the file).
Touched by RED: the three new test files of 3.1, and the four frozen-node edits of 2f (only those
assertions; ruling Q1).
Must not change: tests/test_precommit_hook.py (entirely), every other node of
tests/test_precommit_hook_round2.py and tests/test_ci_gates.py, tests/test_skill_frontmatter.py,
.claude/skills/*, scripts/setup_hooks.sh, requirements*.txt / *.in, package.json, package-lock.json,
tests/.pre_impl_failures.txt, .mcp.json, CLAUDE.md, app/, SmartCompareApp/ (no client file).

---------------------------------------------------------------------------------------------------

## 5. GREEN GATES AND THE BY-HAND EXERCISE

1. The three new files + the four changed nodes, the hook files in their OWN runner call (bound 1200),
   sh and dash; report both [pyt] lines.
2. The five-file pin set: test_ci_gates, test_channel_freshness, test_hermeticity_pins,
   test_sqlfluff_config, test_skill_frontmatter (bound 1200).
3. CI emulation: the new functional file and the round-2 file once more with gitleaks stripped from PATH.
4. `sh -n` and `dash -n` on the hook; `yaml.safe_load` of ci.yml; `tomllib` of .gitleaks.toml;
   py_compile + the ruff tier on the new tests; `git diff --stat` (line-level, no whole-file rewrite).
5. The mutants of 3.6, each restored by sha256.
6. The branch's own range under the DEFAULT rules (what CI runs on this PR, whose base has no config):
   `gitleaks git --log-opts=845ece15..HEAD --redact --no-banner --ignore-gitleaks-allow .` -> 0.
7. By hand on a scratch repo with the GREEN hook: one refusal per new check (binary, gitleaks shim,
   color.ui four-branch) and one pass (allowlisted PNG), output pasted.

## 6. STATED LIMITS
- UTF-16 / NUL / attribute-binary content at an ALLOWLISTED asset path is not regex-scanned beyond
  what --text exposes (UTF-16 never) - unless the magic-byte check (Q2b) is ruled in.
- An awk that dies while reading the staged diff file lets steps 4 and 4a pass on an empty stream (4b
  refuses); kept so the frozen d1_failed_awk node stays green (2g).
- A local untracked `.gitleaksignore` or a local edit of `.gitleaks.toml` silences the hook's gitleaks
  pass (same class as `--no-verify`); CI guards the tracked case and reads the base config.
- gitleaks is optional in the hook (WARNING when absent); CI's job is the mandatory scan and it is
  DETECTION on a public repo, not prevention.
- A clean `git merge` runs no pre-commit hook at all; a concluded conflicted merge runs it over the
  whole merged-in diff.
- mawk NUL handling is unverified on this box (3.7).
- Correction 6's regex limits, TF6, M7, M8 stand as in Phase A.

## 7. ASSUMPTIONS (each with why it beats the alternative)
- One staged diff in `$TMP` (staged content, already in .git/objects) rather than three pipes: one
  status check closes TF7 for all readers, one git spawn instead of three, and the frozen nodes 2-3 move
  in either design. The private dir is 0700 (mktemp -d) and removed by the existing traps; no .env value
  is written (4b still streams values through one pipe).
- Python steps move down, not the secret block up: same final order, a 44-line move instead of 190.
- gitleaks after the regex checks, not first: the regex messages stay first for the frozen Phase A
  scenarios on boxes with gitleaks (measured red_jwt conflict), and M2 is still closed.
- The template report instead of `-v`: same actionable data (rule, file, line) with no content echo.
- Inline case allowlist: the hook diff is what a reviewer reads; no second file to protect.
- Base-range config in CI: a PR cannot widen the allowlist that judges it; the cost is that an
  allowlist change lands in its own PR first (its range then has nothing to flag).

## 8. OPEN QUESTIONS FOR THE ORCHESTRATOR
- Q1 (the frozen nodes). Lift correction 6's byte-equal pin for the PIPE line only (keep the ERE grep
  line and the fail line byte-equal) and amend the four nodes of 2f exactly as written. Recommend YES:
  #316 and TF7 cannot be closed without them; each new assertion keeps the node's intent. Alternative
  for d1: drop the absent-gitleaks WARNING (contradicts R1.2 and spec T3) - rejected.
- Q2 (allowlist). Inline case, extension per directory (2e). Recommend YES. Q2b: add the magic-byte
  check for allowlisted binaries (closes rename-a-dump-to-.png; 0 cost on a normal commit). Recommend
  YES if the diff budget allows; else a stated limit.
- Q3 (.gitleaks.toml regexTarget). Entries 6-9 use the secret target (narrower than match, measured);
  correction 3(b) named line or match. Recommend accepting secret-target for value-shape entries.
- Q4 (step order). All secret checks (4, 4a, .env name, 4e, 4b, 4g) before steps 1-3, gitleaks last
  among them; ESLint as step 6 after sqlfluff. Recommend YES (measured: no frozen node besides 2f moves).
- Q5 (CI hardening beyond corrections 4/5): config from the range base, the .gitleaksignore guard,
  `--ignore-gitleaks-allow`, `timeout-minutes: 10`. Recommend YES for all four.
- Q6 (merges). The gitleaks pass and the binary refusal apply to a concluded conflicted merge like
  every other check; no MERGE_HEAD exemption. Recommend YES (content enters history either way;
  `--no-verify` is the escape).
- Q7 (#317). PER-4 bullet 1 (one staged diff for 4, 4a, 4b) rides along - it IS the TF7 fix. Not in
  Phase B: SEC-4 (.env filename forms - a new refusal semantics with its own pins), SEC-3 (runbook,
  not code), PER-4 bullets 2-4, COM-9, COM-10, DEA-8 (none touched by a Phase B line).
- Q8 (cost). +0.5 to +0.7 s per commit on a healthy box (gitleaks is most of it); ESLint 2-4 s per
  process only when client sources are staged. Recommend acceptable.
- Q9 (gitleaks -v). Correction 1 bound `-v`; the candidate prints a template report (rule, file:line)
  instead, so no line context reaches the terminal or a transcript. Recommend the template.

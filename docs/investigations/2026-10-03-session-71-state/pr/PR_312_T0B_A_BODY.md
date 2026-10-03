## T0b Phase A: harden the pre-commit hook and check skill frontmatter

Phase A of unit T0b. The spec is `docs/investigations/2026-10-03-session-71-state/T0B_REPO_TOOLING_SPEC.md`: review corrections 1-17, rulings TR1-TR10, the RED gate TG1-TG8 and the post-adversary rulings TF1-TF5.

Every change is additive. The four existing credential branches, the root `.env` refusal, py_compile, ruff, black and sqlfluff still refuse every input they refused on main. The four-branch credential line and the sqlfluff line are byte-equal, and static pins hold them. The hook stays POSIX sh. It was measured under Git for Windows' sh (bash 5.2) and `/usr/bin/dash`.

### What changes, per check
`.githooks/pre-commit`:
- **1-3. py_compile, ruff and black read the STAGED blob of each file, not the working tree.**
  - `git checkout-index --prefix` writes the blobs into a private `mktemp -d` directory (fallback `${TMPDIR:-/tmp}/qaren-precommit.$$`). Nothing is written into the repo, and no stash is used.
  - `trap cleanup EXIT` plus `trap 'cleanup; exit 1' INT TERM HUP` removes the directory.
  - A blob that cannot be written refuses the commit; no file is skipped.
  - Tools run in batches of at most 64 paths (Windows command-line limit).
  - ruff and black get `--config "$TOP/pyproject.toml"`.
- **Every staged list uses `--diff-filter=ACMR` and `core.quotePath=false`** (the SQL list is unchanged). Renames are checked, and spaced or non-ASCII paths name real files.
- **3. black.**
  - The allowlist is matched on the original repo path as a whole line.
  - Presence is tested with `python -m black --version`, the interpreter that runs black.
  - When black is missing, the hook prints a WARNING and the commit proceeds. On main this was silent.
- **4. The four credential branches:** byte-equal, unchanged.
- **4a. Two new shapes in a grep of their own:**
  - a JWT: `eyJ[A-Za-z0-9_-]{7,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}`;
  - a credentialed URL whose password has 12 or more characters: `[A-Za-z][A-Za-z0-9+.-]*://[^/[:space:]:@]+:[^/[:space:]@]{12,}@`.

  The added lines come from an awk filter that skips each file's header as a block. An added line whose content starts with `++` is therefore still scanned.
- **.env refusal.**
  - It covers nested paths (`(^|/)\.env(\..*)?$`) and renames (`git mv x .env`).
  - It reads NUL-separated names.
  - It is case-insensitive: on Windows and macOS a staged `.Env` is the same file as `.env`.
- **4b. Fixed-string pass over the .env VALUES.**
  - **Which entries count:** an entry whose upper-cased NAME contains KEY, TOKEN, SECRET, PASS, PWD, CREDENTIAL or PRIVATE, or whose value is itself a credentialed URL, whatever the NAME. The value must be 16 or more characters.
  - **Parse.** The file is read with shell built-ins. The parse handles CRLF, `export` followed by a space or a tab, single and double quotes, lower-case names, space and TAB blanks, and ` #` / `<TAB>#` comments.
  - **Where the .env comes from.** A linked worktree with no `.env` falls back to the main checkout's `.env`, next to the common git dir.
  - **Matching (ruling TF1).**
    - Each counted entry is written by the `printf` built-in as tagged lines (`N<name>`, `V<value>`) into ONE pipe.
    - An `E` line, the staged diff and a `Z` line follow. The `Z` line is written only after `git diff` succeeded.
    - A single awk keeps the values in memory and takes the added lines. It tests each value with `index()`, a literal substring test, and prints the NAMES it found.
    - An entry with no NAME (`=<credentialed URL>`) is named `(unnamed)`.
  - **No value is exposed.**
    - No value reaches a process argv, a temp file, stdout or stderr.
    - xtrace AND allexport are switched off for the section and restored afterwards. `sh -x` cannot echo a value, and `sh -a` cannot export one into the environment of the `grep` and `git` processes the section starts.
    - The staged diff never sits in a shell variable.
  - **Failure handling.** The check refuses the commit instead of passing unrun when:
    - awk fails;
    - the `.env` parse dies part-way (dash segfaults on a `.env` line of about 1 MB);
    - `git diff` fails.

    In the last two cases the stream does not end with the `Z` line, and awk exits 2.
- **4c. Skill frontmatter.**
  - The staged `.claude/skills/*/SKILL.md` must parse with `yaml.safe_load` into a mapping with a non-empty `name` and `description`.
  - The step runs after the secret checks, so a credential or a .env value on a frontmatter line is refused before the parse.
  - A parse error is reported by its problem and line/column only, because PyYAML's own message quotes the line.
  - When PyYAML cannot be imported, the hook prints a WARNING and skips the step.
- **5. sqlfluff:** byte-unchanged.

Other files:
- `.claude/skills/qaren-eas-deploy/SKILL.md` and `.claude/skills/qaren-referrals/SKILL.md`: the `last_verified` value is quoted, so both frontmatters parse. No other byte changed.
- `.gitignore`: adds `.claude/settings.local.json`. `git rm --cached` at commit untracks it (TR7).
- `scripts/setup_hooks.sh` (new): sets `core.hooksPath .githooks` for the clone and prints it.
- Tests:
  - `tests/test_precommit_hook.py`: 31 scenarios x {sh, dash}.
  - `tests/test_precommit_hook_round2.py`: 15 scenarios x {sh, dash}. It pins D1, M1, M3, M4 and M6 (TF2) plus four neighbours, and the second adversary's three minors:
    - MINOR-1: a `grep` shim that kills the `.env` parse mid-file, and a `git` shim whose staged diff fails.
    - MINOR-2: a `git` shim that reports whether a `.env` value is in its environment under `sh -a`, without printing the environment.
    - MINOR-3: a `grep` shim that blinds the new-shapes branch, so an unnamed credentialed-URL entry reaches the value pass.
  - `tests/test_skill_frontmatter.py`: T1 + T4.
  - `tests/test_ci_gates.py`: +9 static pins on the hook text; existing nodes are untouched.

  Every scenario runs in a hermetic tmp repo: GIT_* is dropped, plus `GIT_CONFIG_NOSYSTEM=1`, a tmp HOME/XDG/TMPDIR and the LF copy of the hook. Every sentinel and every FAKE .env value is built at runtime.

### Message constants (each printed as `pre-commit: <text>`)
- New refusals:
  - `staged diff contains a JWT or a credentialed URL - remove it (keys live only in gitignored .env)`
  - `staged diff contains the value of .env variable(s): NAME [NAME ...]` (names only; `(unnamed)` for an entry with no NAME)
  - `skill frontmatter check failed: <repo-relative path>`
  - `could not read the staged content of <path>`, and `... of the path(s) named above`
  - `could not create a temp dir for the staged content`
  - `could not run the .env value check (the .env parse, git diff or awk failed)`
- New warnings (the commit proceeds):
  - `WARNING black not installed - allowlist check skipped (pip install -r requirements-dev.txt)`
  - `WARNING PyYAML not importable - skill frontmatter check skipped`
  - `WARNING <file> is not readable - .env value check skipped`
- Reused unchanged: `staged diff contains what looks like a credential ...`, `.env must never be committed`, `python syntax error in staged files`, `ruff blocking tier failed`, `black allowlist check failed ...`, `sqlfluff failed on staged migrations`.
- No new line contains the words `sqlfluff lint`.

### Accepted now (main refused correct content)
- **The three former false blocks (TR6):**
  - a staged-OK file whose working copy is broken;
  - a path with a space;
  - a non-ASCII path.
- **Also accepted (additivity adversary, SOUND):**
  - the working copy was deleted after staging;
  - the working copy is black-dirty while the staged blob is clean;
  - a path with a leading dash (`-ok.py`), which main passed to py_compile as an option;
  - black.exe on PATH while the hook's python cannot import black. main refused with "black allowlist check failed"; now the hook warns and passes (correction 15).
  - more than ~500 staged .py files (by reasoning, not measured): main hit the Windows command-line limit; the new code uses batches of 64.

### Refused now (stricter)
- nested `.env` files, `git mv x .env` and `.Env`;
- a renamed .py with a syntax error;
- a staged syntax error, undefined name or black-dirty blob whose working copy is already fixed;
- a JWT;
- a credentialed URL with a 12+ character password;
- a .env value, refused by name;
- `++`-prefixed added lines carrying a JWT, a credentialed URL or a .env value;
- a SKILL.md frontmatter that does not parse, or lacks name/description;
- a staged `[a].py` with a syntax error next to a clean committed `a.py` (main's unquoted list glob-expanded it);
- a black-dirty allowlisted file when python imports black but no black executable is on PATH (main skipped it via `command -v black`);
- a commit while a .env exists and the value check cannot run to the end: awk exits non-zero, the `.env` parse dies, or `git diff` fails.

### The D1 story
- **The defect.** The shell-security adversary found it. Correction 10's containment test was a `case "$ADDED" in *"$value"*)` pattern over the whole staged diff held in a shell variable. dash overflows its stack on such a pattern at about 1 MB: `case $B in *"x"*)` on a 1 MB string segfaults. Measured on this box:
  - dash crashed (rc 2816, no output) at 1 MB and 4 MB;
  - 0.25 MB was fine;
  - MSYS sh was fine at 4 MB.

  The hook therefore failed closed but silently on any large commit made under dash while a .env existed.
- **The fix (TF1).** The diff now flows through one pipe into awk, next to the tagged entries.
- **Measured after the fix** (LF copy under sh and dash, CRLF working copy under MSYS sh, FAKE .env):
  - with no value staged, 1.2 MB and 4 MB of staged text give rc 0 and no message (0.25-8 MB in the second adversary's run);
  - with a value present, the hook prints the NAMES-only refusal;
  - `-x` traces carry no value;
  - a value with a backslash, `%`, `*`, `[x]`, `?` or `$(` is matched literally.
- **Real commits.** Through `git commit` with `core.hooksPath`, a 1.5 MB docs file with a FAKE .env commits with no message under sh (CRLF and LF) and under dash (a probe hook proved which interpreter Git starts). The same commit with a value planted is refused, naming the NAME only.
- **The same crash on the .env side (second adversary, MINOR-1).**
  - dash also segfaults while PARSING a `.env` line of about 1.1 MB (`case $x in *=*)` and `${x%%=*}`).
  - That killed the left side of the value pipe. awk saw neither the end-of-entries line nor the diff, and the hook passed with no message after 658 s.
  - The stream now ends with a `Z` line written only after a successful `git diff`, and awk exits 2 without it. That case is now refused ("could not run the .env value check").
  - It is still slow (MINOR-4 below).

### Install
Run `sh scripts/setup_hooks.sh` once per clone; it sets `core.hooksPath .githooks`. The PowerShell equivalent is a one-liner in the script header. Worktrees share the clone's config.

### Process
1. **Spec.** Spec, then an adversarial spec review (17 measured corrections), then rulings TR1-TR10.
2. **RED.** RED tests, gated by the orchestrator (TG1-TG8), then frozen.
3. **GREEN.** 62 hook nodes passed under sh and dash; 14/14 mutants were killed.
4. **Two adversaries.**
   - Additivity: SOUND. No staged input that main refused is now accepted, except the correct content listed above.
   - Shell security: DEFECTIVE on D1. Its minors were M1-M8.
5. **Fix round.** Applied M1 (skill step moved after the secret checks, and the YAML message sanitised), M3, M4 and M6; 6/6 re-run mutants were killed.
6. **Rulings TF1-TF5.**
7. **Round 2.** Applied the awk value pass (TF1) and wrote `tests/test_precommit_hook_round2.py` (TF2), with every pin proven by a mutant (11/11 killed).
8. **Second shell-security adversary (TF5), narrowed to the awk value pass.** No defect.
   - What it probed: argv shims under sh and dash, `-x` traces, 0.25-8 MB inputs, and 33 hostile value shapes (glob, `%`, quotes, backslashes, tag letters, prefixes).
   - Result: no value in any argv, stdout, stderr or temp file.
   - Four minors:
     - MINOR-1: fail-open when the left side of the pipe dies.
     - MINOR-2: allexport.
     - MINOR-3: an unnamed entry.
     - MINOR-4: performance.
9. **Fix round 3.** Applied MINOR-1, MINOR-2 and MINOR-3. Each is pinned by a new round-2 scenario and proven by a mutant (6/6 killed). The TF2 and GREEN value-pass mutants were re-run on the new hook (8/8 killed). MINOR-4 is a stated limit (below).

### Gates (fix round 3, final bytes; bounded runner, one pytest at a time)
- `tests/test_precommit_hook_round2.py` alone: 30 passed (15 scenarios x sh+dash), 723 s, status OK.
- `tests/test_precommit_hook.py` alone:
  - sh column: 31 passed, 856 s, status OK;
  - dash column: only the `env` nodes were re-run this round, 10 passed, 337 s, status OK. The full dash column was 31/31 on the previous round's hook.
- `tests/test_skill_frontmatter.py`: 6 passed and 1 expected red (`test_settings_local_json_is_not_tracked`, which turns green once `git rm --cached` runs at commit, TG6).
- Pin set (`test_ci_gates`, `test_channel_freshness`, `test_hermeticity_pins`, `test_sqlfluff_config`): 198 passed, 238 s, status OK.
- Syntax and lint: `sh -n` and `dash -n` pass on the hook and on `scripts/setup_hooks.sh`; py_compile and the ruff blocking tier pass on the round-2 test.
- Hygiene:
  - the hook is CRLF 405/405;
  - new lines are ASCII, with no credential shapes and no `sqlfluff lint`;
  - the frozen tests are byte-equal to their frozen copies;
  - no `.merge_file_*` left behind.
- Mutants: 14/14 killed, each in its own bounded run; the hook was restored and its sha256 re-checked after each.

### Stated limits (TF3 and the second adversary)
- **M2.** py_compile and ruff print the offending staged source line to stderr before the secret steps run (the TR4 order). A secret on a line with a syntax error is echoed to the committer's own terminal before it is refused. Phase B puts gitleaks in front.
- **`++` hole.** The byte-equal four-branch pipeline (correction 6) still skips added lines whose content starts with `++`. The new branches and the value pass do not.
- **M5, regex limits (correction 6).** The credentialed-URL branch misses an unencoded `@` or `/` in the password and an empty user. Passwords under 12 characters pass by design. A value or JWT split across two lines is not seen.
- **Value-pass limits (second adversary, measured).**
  - A `.env` value split across two added lines, URL-encoded or base64-encoded is not seen.
  - A value that appears only in a staged file PATH (the diff's file header) is not scanned.
- **MINOR-4, a very long `.env` line is slow.** The built-in parse is roughly quadratic on a single very long line.
  - 1.5 MB took 520 s under MSYS sh, with the correct verdict.
  - 1.1 MB took 658 s under dash. Before this round that was a silent pass; now it is a refusal.
  - A 2 KB value is fine: 18-47 s end to end with 33 entries.
  - No realistic `.env` has such a line.
- **A failed `git diff` in the credential greps.** The four-branch line (byte-equal) and the new-shapes branch take their status from the last `grep`. A `git diff` that fails there makes them pass; only the value pass (when a `.env` exists) refuses on it.
- **M7/M8, Windows-only fail-closed refusals.** A `[ab].py` path, a gitlink named `*.py` and a symlinked `*.py` (with `core.symlinks=false`) are refused. The repo tracks 0 of each.
- **SQL.** The SQL list keeps ACM (a renamed migration is not linted), and sqlfluff still reads the working tree.
- **TG3.** A .env value that is itself a credentialed URL is refused by the URL branch first.
- **Built-ins.** The value pass relies on `printf` being a shell built-in, which it is in dash and bash.
- **Phase B (deferred, separate PR):**
  - the gitleaks hook pass with `.gitleaks.toml` (R1.2, R1.4);
  - the CI secret-scan job (R5);
  - ESLint on staged client files (R2.4).

### Owner note
- The hook is a local guard; `git commit --no-verify` bypasses it. The CI secret scan arrives in Phase B.
- **Before any other checkout moves past this merge,** back up its `.claude/settings.local.json` by byte copy and restore it afterwards. An unmodified copy is deleted by the pull, and a modified one makes the pull abort. Never resolve the abort with stash or checkout (correction 12, TR7).
- **Cost.** On a loaded box the value pass adds one more `git diff` read whenever a .env exists. A 1.2-4 MB commit took 13-27 s end to end under sh or dash.

## Orchestrator review (session 71)
- Process: spec by the orchestrator, Opus adversarial spec review (17 corrections incl. the gitleaks staged flag, the fail-open .gitleaks.toml, the checkout-index root pollution, the dash CRLF rejection, the T3 hermeticity rules), rulings TR1-TR10 (two phases), Opus RED gated PASS (42 hook scenarios under sh and dash + static pins), Opus GREEN (62 hook nodes, 14 mutants, by-hand commits through core.hooksPath), two Opus adversaries (additivity: 152 HEAD-vs-NEW hook runs, no weakening; shell security: one DEFECT, the dash stack overflow on about 1 MB of staged text, plus 11 minors), fix round, rulings TF1-TF5 (the awk-from-one-pipe value pass), round 2 (fix-2 + the round-2 pins, a second shell-security adversary SOUND on argv shims, -x traces and 0.25-8 MB inputs, fix-3 with the fail-closed stream trailer and allexport guard), rulings TF6-TF8.
- The orchestrator read the whole hook diff, re-ran the hook test dash column on the final hook (31 passed), the round-2 and skill files (36 passed + the one expected red), untracked `.claude/settings.local.json` (`git rm --cached`; the file on disk is kept), and re-ran the skill file plus the four-file pin set (205 passed) before committing.
- For every other checkout that moves past this merge: an unmodified `.claude/settings.local.json` is deleted by the update, a modified one makes the update abort. Move the file aside, update, move it back (never stash, never `checkout --`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

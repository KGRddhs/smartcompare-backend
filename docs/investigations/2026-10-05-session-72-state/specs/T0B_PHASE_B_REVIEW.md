# T0b Phase B - adversarial spec review of T0B_PHASE_B_ADDENDUM.md

Reviewer: Opus adversarial spec reviewer, 2026-10-05 14:29-15:05 AST. Base 845ece15 (unit worktree
sc-s71-t0b clean, untouched). Inputs read in full: T0B_REPO_TOOLING_SPEC.md (corrections 1-17, TR1-TR10,
TG1-TG8, TF1-TF8), the addendum (de46cbf0...), cand/pre-commit (e0968596..., verified), cand/pre-commit.base
(de0a4bd8... == `git show 845ece15:.githooks/pre-commit`, verified), ci_secret_scan_job.yml,
gitleaks_draft.toml, issues #315-#317, STEP6_ACTION_PLAN.md section A. My own fail-open / false-refusal
list was written to `review/notes.md` before I read the addendum's test list; the diff against the
addendum is corrections 1, 4, 5, 6, 8 below (not in the addendum) and 2, 3 (in it, but wrong).

Everything below is MEASURED on this box today unless marked otherwise (gitleaks 8.30.1 WinGet, git
2.52.0.windows.1, MSYS sh + /usr/bin/dash, GNU awk 5.3.2, venv python, `node -e 0` = 0.12 s). Scratch repos
under `review/scratch` with GIT_* dropped, GIT_CONFIG_NOSYSTEM=1, tmp HOME/XDG/TMPDIR; FAKE .env files only
inside scratch repos (all removed); sentinels runtime-built; gitleaks always `--redact` with a rule-id +
path template. Scripts and raw outputs: `review/probe_a.py` (A1 first run printed to the console and
recorded in notes.md, then re-measured with cand2 in probe_e.out; A2-A7 in probe_a2.out),
`probe_b.py`, `probe_c.py`, `probe_e.py`, `mk_cand2.py`, `mk_narrowed.py`, `tree_*.txt`,
`tree_draft_files.txt`, `rv_*.log`. The reviewer's fixed reference hook is `review/cand2/pre-commit`
(sha256 d8f0cfda...b594b0, LF, 24,473 bytes) = cand/pre-commit + corrections 1, 5, 7 only.

## Review corrections (BINDING - supersede the body)

1. **CRITICAL (additivity principle): `--no-textconv` makes the four-branch line, 4a and 4b BLIND to a
   textconv driver that REVEALS content, which the base hook scanned.** `git diff` porcelain applies
   textconv by default, so at 845ece15 all three readers saw the converted text. The addendum's single
   diff (`--text --no-textconv`) sees only the raw bytes. Scratch repo, `*.cfg diff=rot` with
   `diff.rot.textconv = sh rot.sh` (rot13), staged raw = rot13 of the secret (probe_a A1, probe_e):
   ```
   rot13(AWS doc key)         base sh/dash rc=1 four-branch msg | cand sh/dash rc=0 (gitleaks ABSENT and PRESENT)
   rot13(FAKE .env value)     base sh/dash rc=1 MSG_ENV_VALUE FAKE_SERVICE_KEY | cand sh/dash rc=0 (both)
   ```
   (gitleaks present does not save it: its default allowlist drops the documentation AWS key and it has
   no .env-value rule.) Binding fix (built in cand2): the staged diff file carries BOTH views, raw first:
   ```
   {
     git diff --cached --no-color --no-ext-diff -U0 --text --no-textconv &&
       git diff --cached --no-color --no-ext-diff -U0 --text --textconv
   } > "$STAGED_DIFF" ||
     fail "could not read the staged diff (git diff failed)"
   ```
   Measured on cand2, sh and dash: reveal-4 rc=1 four-branch, reveal-4b rc=1 MSG_ENV_VALUE (names only,
   no 12-char piece), hide (textconv=true + AWS doc key) rc=1 four-branch (the #315 case stays closed).
   Cost: +0.09 s (sh) / +0.07 s (dash) per empty commit over cand. Consequence, accepted as fail-closed
   and stated in the PR: a user textconv command that FAILS now refuses the commit ("could not read the
   staged diff"); base passed silently. New PIN tests (green at base, red on the addendum's cand):
   textconv-reveal x {four-branch AWS doc key, 4a rot13 JWT, 4b FAKE .env value}; mutant "the
   `--textconv` diff dropped" must redden them; the static pin holds both diff lines.

2. **Draft allowlist 1 (sha256 after a file name) silences real 64-hex secrets assigned to an attribute
   or key named `token`, `key`, `pass`, `auth` ...** `\.[A-Za-z]{1,5}` accepts any 1-5 letter word after a
   dot. Staged hook form (probe_b / probe_c, rule ids only):
   ```
   self.token = "<64hex>"      default rc=1 generic-api-key | draft rc=0
   settings.key = "<64hex>"    default rc=1                 | draft rc=0
   yaml  auth.key: <64hex>     default rc=1                 | draft rc=0
   ADMIN_API_KEY = "<64hex>"   default rc=1                 | draft rc=1 (control)
   ```
   A rotated ADMIN_API_KEY is exactly this shape. Binding regex (regexTarget match):
   `[\w-]\.(?:py|pyi|ts|tsx|js|jsx|mjs|cjs|json|md|sql|txt|ya?ml|toml|sh|ps1|html?|css|png|jpe?g|webp|ttf|lock|snap|csv|log|out|diff|patch|xml|svg)"?\s*[:=,]\s*"?[0-9a-f]{64}\b`
   (built in `review/gitleaks_narrowed.toml`). Measured: the last 60 merged PR ranges at 845ece15 give
   default 9 PRs / 30 findings, draft 0, narrowed 0; the three bypass shapes rc=1 with narrowed;
   `api.ts: <hex>`, `authService.ts = <hex>` and the JSON `["src/services/api.ts",\n "<hex>"]` pair rc=0.
   test_gitleaks_config.py gains the three bypass shapes as rc=1 nodes.

3. **Draft allowlist 3 allows ANY password value under `tests/`.** `{"password": "<17 mixed chars>"}` in
   tests/test_x.py: default rc=1, draft rc=0 (probe_b). The measured findings are 2, both in one file.
   Binding: `paths = ['''^tests/test_retro_w1_9_429\.py$''']` (condition AND + the match regex kept).
   Measured: 60 ranges still 0 findings; the tests/test_x.py case rc=1. A future password fixture is
   built at runtime (the repo's sentinel rule) or gets its own entry in its own PR.

4. **The 60-PR-range acceptance cannot see the false refusals of the CURRENT TREE: 52 findings in 37 files
   remain with the draft config (82 with default rules).** `gitleaks dir` over a scratch checkout of
   845ece15 (rule + file only, `review/tree_draft_files.txt`): tests/fixtures third-party captures 24 in
   18 files (bh_gcc html/json, jomashop, magento, jsonld_first, platform, visible_text_currency, yotpo;
   generic-api-key, gcp-api-key x3, jwt x1); app/services/algolia_service.py 4; tests/*.py 15 in 9
   files; SmartCompareApp/src/services/__tests__/sentry.test.ts 3; data/bh_gcc_source_candidates_round3.json
   1; docs/investigations 4 (2 algolia-api-key in a round-3 discovery doc, 2 in m22 args JSON); scripts 1.
   Any commit that changes one of those lines, re-captures such a fixture, or adds a NEW captured
   retailer page carrying a public client key is refused by the hook where gitleaks is installed and
   reddens secret-scan. Binding: (a) GREEN gate 6 gains a tree scan with the final config and the PR
   text lists every remaining file; (b) the orchestrator rules per bucket (question QN1 below): a
   `condition = "AND"` allowlist `paths = ['''^tests/fixtures/''']` with `targetRules` for the public
   client-key rules (needs a ruling, correction 3(c) prefers a stated limit over a path entry), or the
   stated limit "editing these lines needs the allowlist PR first". (Note: path allowlists apply only in
   git mode: `gitleaks dir` reports absolute paths, so the tests/ password entry does not match there.)

5. **ESLint step: a failed `git show` lints an EMPTY stdin and passes (fail-open).** The partial-file
   pipeline's status is eslint's. probe_a A4, node shim that exits 1 on a marker, git shim failing
   `show :<path>`: without the shim rc=1 "eslint found errors in the staged content of ..." (sh, dash);
   with it rc=0 and the shim logged STDIN_LEN=0 (sh, dash). Binding fix (built in cand2):
   `git show ":$f" > "$TMP/eslint.stdin" || fail "could not read the staged content of $f"` then
   `(cd ... && node ... --stdin --stdin-filename ...) < "$TMP/eslint.stdin"`. New test + mutant.

6. **The binary allowlist refuses honest docs and asset commits.** Candidate hook (probe_a A7, sh):
   `docs/investigations/2026-10-05-session-72-state/screenshot.png` rc=1 MSG_BINARY,
   `.../report.pdf` rc=1, `SmartCompareApp/assets/images/new.webp` rc=1; only `*/icon-candidates/*.png`
   passes. Session state folders and the App Store lane (screenshots) will add images. Binding unless
   the orchestrator rules otherwise (Q2): rule Q2b IN (magic bytes, measured portable by the spec agent)
   and widen by extension under two roots, each gated by its magic bytes: `docs/*` and
   `SmartCompareApp/assets/*` x {png, jpg, jpeg, webp, gif}, plus `SmartCompareApp/assets/*` x {ttf, otf}
   and the existing `app/static`, `test_images` rows; PDF, zip, office, sqlite and executables stay
   refused (text-bearing containers no regex can read). The refusal message keeps the MSG_BINARY prefix
   and adds the remedy: "convert it to text, or add the path to the allowlist in .githooks/pre-commit in
   its own commit". The tracked-population pin (0 newly refused of 58) stays.

7. **A gitleaks that exits non-zero without a report gets a misleading message.** Shim printing an
   unknown-flag error, exit 1, no report (probe_e): cand prints only "gitleaks refused the staged changes
   (rule id and place above; ...)" with nothing above. A gitleaks older than 8.30.1 on another box (no
   `git` subcommand before 8.19, no template flags) would refuse EVERY commit this way (NOT MEASURED: only
   8.30.1 here). Binding (built in cand2): when the report is non-empty, print it and fail "gitleaks
   refused the staged changes (rule id and place above)"; otherwise fail "gitleaks refused the staged
   changes (it exited non-zero with no finding report: a broken .gitleaks.toml, or a gitleaks other than
   8.30.1)". Both keep the MSG_GITLEAKS prefix, so tests 1 and 3 still assert it; add one node for the
   no-report wording.

8. **The hook trusts the WORKING-TREE `.gitleaks.toml` and any `$TOP/.gitleaksignore`.** (Reasoned; the
   spec agent measured that a root .gitleaksignore silences gitleaks.) CI reads the config from the range
   base so a change cannot widen the allowlist that judges it; the hook should follow the same rule:
   materialise `HEAD:.gitleaks.toml` into `$TMP/gitleaks.toml` when `git cat-file -e` finds it (default
   rules otherwise, e.g. the first commit) and pass that path to `--config`; refuse when
   `$TOP/.gitleaksignore` exists ("a .gitleaksignore would silence gitleaks; remove it"), mirroring the
   CI guard. Cost: two git spawns. Needs a ruling (QN2); if declined, the addendum's stated limit stands.

9. **Frozen-node accounting with correction 1 (re-run, not taken from the addendum).** Scratch detached
   worktree at 845ece15 with the hook replaced; bounded runner:
   ```
   cand2, gitleaks present: tests/test_precommit_hook.py            62 passed
     [pyt] tag=rv-c2-phaseA start=2026-10-05 14:46:44 end=2026-10-05 14:48:37 elapsed=113s bound=1200s status=OK rc=0
   cand2, gitleaks present: tests/test_precommit_hook_round2.py     28 passed, 2 failed (r3_failed_git_diff sh+dash)
     [pyt] tag=rv-c2-round2 start=2026-10-05 14:48:43 end=2026-10-05 14:49:36 elapsed=53s bound=1200s status=FAIL rc=1
   cand2, gitleaks STRIPPED: Phase A file                            62 passed
     [pyt] tag=rv-c2-nogl-A start=2026-10-05 14:50:34 end=2026-10-05 14:52:29 elapsed=115s bound=1200s status=OK rc=0
   cand2, gitleaks STRIPPED: round-2 file                            26 passed, 4 failed (d1_bulk_text_without + r3_failed_git_diff, sh+dash)
     [pyt] tag=rv-c2-nogl-r2 start=2026-10-05 14:52:39 end=2026-10-05 14:53:38 elapsed=59s bound=1200s status=FAIL rc=1
   cand (addendum), r3 subset                                        4 failed (r3_failed_git_diff + r3_allexport, sh+dash)
     [pyt] tag=rv-cand-r3 start=2026-10-05 14:49:49 end=2026-10-05 14:49:59 elapsed=10s bound=600s status=FAIL rc=1
   cand2 + secret-scan job appended: five-file pin set (+test_skill_frontmatter)  204 passed, 1 failed (the four-branch pipe pin)
     [pyt] tag=rv-c2-pins start=2026-10-05 14:54:09 end=2026-10-05 14:54:55 elapsed=46s bound=1200s status=FAIL rc=1
   ```
   So with correction 1 exactly THREE frozen node families change: the test_ci_gates pipe pin,
   r3_failed_git_diff (sh, dash) and d1_bulk_text_without (CI only). r3_allexport passes UNCHANGED
   (count 2) but vacuously: both diffs now run before the .env parse, so it observes no post-parse
   process. Binding: node 7 (gitleaks shim under sh -a) is mandatory, plus a node 7b with a `cat` shim
   under sh -a (the 4b left side, the one post-parse process of the value pipe) asserting the marker is
   absent from its environment.

10. **Test-list corrections.** (a) The PINs of correction 1. (b) The `--text` killer must not depend on
    awk's NUL handling (CI's mawk is unverified): add a text file at an ALLOWLISTED path made binary by a
    `-diff` attribute (with the right magic bytes if correction 6 holds) carrying a runtime JWT -> 4a
    message; keep node 13 and add 13b = NUL + JWT at an allowlisted path as the mawk canary (a CI-only red
    there is a real Linux gap, not a test bug). (c) The gitleaks shim also records whether
    GITLEAKS_CONFIG and GITLEAKS_CONFIG_TOML are EMPTY in its environment while the test exports
    non-empty values: node 37 is L-only, so the env-blanking mutant otherwise survives in CI. (d) Nodes
    for corrections 5 and 7. (e) test_gitleaks_config.py nodes for corrections 2 and 3. (f) RED hygiene:
    every static node asserts its input exists before parsing (a missing .gitleaks.toml, a hook with zero
    allowlist lines, a ci.yml without the job) so each fails by assertion at base, never by a harness
    error. (g) Optional, measured correct already (probe_a A2/A3): a real `git commit -- path` (temp
    GIT_INDEX_FILE) refuses a token in the committed path and passes while another staged path holds one;
    a commit from a linked worktree refuses a staged token and passes clean.

11. **CI job.** Reproduced: YAML parses (7 jobs, job-level `permissions: {contents: read}`, no `if:`,
    no continue-on-error) and the pins pass (correction 9). Additions: `curl --retry 3` on the download
    (a release-CDN blip otherwise reds the job). Gate 6 (the branch's own range under DEFAULT rules,
    because this PR's base has no config) stays binding and must include the three NEW test files, which
    the spec agent's self-scan (probe9) did not cover because they do not exist yet. NOT re-derived: the
    tarball checksum (no network). The job is detection only and not a required check until Ahmed adds
    it (R6).

12. **Numbers re-measured, and one discrepancy explained.** Hook cost, median of 3, healthy box: base
    0.98 / 0.89 s empty (sh / dash), 1.44 / 1.30 s ten files; cand 1.70 / 1.60 and 2.04 / 1.90; cand2
    1.79 / 1.67 and 2.18 / 2.02 (delta base->cand2 about +0.7-0.8 s; the addendum's +0.5-0.7 s reproduced
    in direction, my absolutes run higher). Tracked binaries: 58 by `git diff --numstat --no-textconv
    <empty tree> 845ece15` (reproduced) and 65 by `git ls-files --eol` (i/-text) - the Step 6 number. The
    7 extra are TEXT to git diff (1 markdown with its first NUL at byte 274,709; 6 fixtures with lone CRs),
    so 4e never sees them and the allowlist needs only the 58. PR ranges merged since the spec review
    (15 merges since 2026-10-02 incl. #289 #305 #323 #290 #297 #306 #307 #310 #312 #313): default rules
    red #297 and #289 (1 generic-api-key each), draft 0; the docs checkpoints #305 and #323 are clean
    even under default rules.

13. **Stated limits to add to the PR text.** A failing textconv command refuses (correction 1);
    `git commit --amend` scans only the delta against the amended commit (pre-existing, every check;
    reasoned); ESLint's i18next/no-literal-string message may quote a literal (an M2-class echo after
    every secret check ran; NOT VERIFIED); path allowlists apply in git mode only (correction 4);
    without gitleaks, M2 stays open for shapes outside the six regex branches (e.g. a GitHub token on a
    syntax-error line).

### Answers to the open questions

- **Q1 (frozen nodes):** YES, lift correction 6 for the PIPE line only; keep HOOK_CREDENTIAL_GREP and the
  fail line byte-equal; the new static pin holds the two diff lines of correction 1. With correction 1,
  amend only r3_failed_git_diff (expect "could not read the staged diff", keep _assert_no_piece) and
  d1_bulk_text_without (rc 0, refusals() == [], every message the gitleaks-absent WARNING). r3_allexport
  needs no edit (measured) but correction 9's nodes 7 and 7b replace its lost reach.
- **Q2 (allowlist):** inline case YES; Q2b magic bytes YES; widen as in correction 6 (or, if ruled
  narrow, state the refusal of new screenshots and PDFs as a limit and add the App Store screenshot
  folder before that lane commits images).
- **Q3 (secret target for entries 6-9):** accept. Not reproduced: the spec agent's `test_api_key =
  "<64hex>"` rc=1; reproduced: a token with `...` inside rc=0 by design (entry 9).
- **Q4 (order):** YES. Reproduced: 62/62 Phase A nodes pass with the moved Python block under sh and dash,
  gitleaks present and absent (cand2). Not reproduced: the M2 echo measurements (base leaks, cand does
  not) - taken from the spec agent.
- **Q5 (CI hardening):** YES to all four, plus `curl --retry 3` (correction 11) and the hook-side mirror
  of the base-config and .gitleaksignore rules (correction 8, QN2).
- **Q6 (merges):** YES, no MERGE_HEAD exemption. Not reproduced (spec agent's probe8). Reproduced
  instead: partial commits and linked-worktree commits behave correctly with gitleaks (probe_a A2/A3).
- **Q7 (#317):** PER-4 bullet 1 rides along (with correction 1 the hook makes two diff calls into one
  file, still fewer than the base's three). No other #317 item becomes free or unavoidable: SEC-4's
  filename regex line is not touched (4e is its own block); PER-4 bullets 2-4 are not touched (Phase B
  ADDS one numstat and two name-only listings, so "list staged names once" gets more valuable but is not
  required); COM-9, COM-10, DEA-8 and SEC-3 are untouched.
- **Q8 (cost):** acceptable on a healthy box (correction 12). On the slow-spawn box every extra process
  costs seconds: Phase B adds about four spawns per commit (mktemp, the second diff, numstat, gitleaks
  and its own git calls, the ESLint name listing) while removing two diffs.
- **Q9 (gitleaks output):** the template report in the hook (rule id, file:line, no content); CI keeps
  `-v` per correction 4(c).
- **QN1 (new, correction 4):** how the 52 tree findings are handled (path+targetRules allowlist for
  tests/fixtures third-party captures vs stated limit). Recommendation: the AND allowlist for
  tests/fixtures/ restricted to the public client-key rules (generic-api-key, gcp-api-key,
  algolia-api-key), a stated limit for the rest (app/services/algolia_service.py, tests/*.py,
  sentry.test.ts, data/, docs/, scripts/), listed by file in the PR.
- **QN2 (new, correction 8):** the hook reads `HEAD:.gitleaks.toml` and refuses a present
  `$TOP/.gitleaksignore`. Recommendation: YES.

Verdict: APPROVED_WITH_CORRECTIONS

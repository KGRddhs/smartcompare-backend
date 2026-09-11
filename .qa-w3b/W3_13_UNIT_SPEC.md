# W3-13 — channel-freshness CI guard + publish runbook

Draft of 2026-09-11 01:20 (previous spec agent, killed before reporting) re-verified line by line at ed75dc70 on 2026-09-11 and corrected in place. Corrections are marked **[CORRECTED]**; every other claim was re-measured and held.

## 1. Header

| | |
|---|---|
| Unit | W3-13 |
| Findings | `MB-RECONCILE-06` (P1), `MB-RECONCILE-19` (P3), `MB-TWO-LEVER-RELEASE-05` (P2), `MB-TWO-LEVER-RELEASE-10` (P3) |
| OTA class | **ci-only** for the workflow + script + test half; **docs** for the runbook half. Nothing in this unit reaches a phone, a backend process, or Railway. No flag (there is no runtime behaviour to flag). No migration. |
| Base SHA | `ed75dc708b82c0b911c9de8a3e59d4418c6e278c` (origin/main = HEAD of worktree `sc-w3-ci`; `git status --short` empty) |
| Phones | `preview` channel published from `97b5f1501a1242c405fd3cf12bee9ab419db2bdd` (2026-09-02 01:34:56 +0300, "docs(claude-md): M18 load + scoring flags…"); the publish is recorded in `docs/CONTEXT_SESSION_LOG.md:131` with **no group id** |
| Measured on | eas-cli **18.8.1** (global, `C:\Users\SynAckITPC\AppData\Roaming\npm\node_modules\eas-cli`, `engines.node >= 20.0.0`; `eas.json` `cli.version` is `>= 18.8.1`), `@expo/cli` 54.0.24 (installed; pulled by `expo` 54.0.34 vs pin `~54.0.33`), `@sentry/react-native` 7.2.0 (= pin `~7.2.0`; **CLAUDE.md's "`@sentry/react-native@8.11.1`" line is stale docs drift, not touched here**), `expo-updates` 29.0.17 (= pin `~29.0.17`), TypeScript 5.9.3 (pin `~5.9.2`; `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`), jest 29.7.0 (pin `^29.7.0`), eslint 9.39.4 (pin `^9.39.4`), Python 3.12.9, **pytest 8.2.0 locally vs `pytest==9.1.1` in `requirements-dev.txt`** (drift; nothing here depends on a pytest 9 feature), ruff 0.16.5 (= pin), black 26.5.1 (= pin), pyyaml 6.0.3 (= pin). `SmartCompareApp/node_modules` is the junction into `sc-scraper-proof` and carries `@babel/core` + `.bin/jest`. |

One-paragraph statement: main is 33 first-parent commits (28 merges + 5 direct pushes; 141 commits; 311 files, +74,875/−2,282) ahead of the bundle on every phone, and nothing anywhere reports that. This unit adds a CI job that resolves the `preview` channel's published commit through eas-cli and fails when it is more than one first-parent commit behind `origin/main`; a stdlib-only script that makes that decision and is unit-tested with no network; and the publish procedure in the runbook so the next OTA is auditable (group id + SHA recorded, sourcemaps uploaded, never `--branch production`).

## 2. Scope correction — what is ALREADY on main at ed75dc70

The plan lists one red test ("a CI job that resolves the preview channel's published commit and fails when it is more than one merge behind origin/main — RED today: 6 commits / 72 files behind"). Verified at HEAD:

* **The CI job does not exist — still RED.** `.github/workflows/ci.yml` (274 lines) parses (pyyaml) to exactly five jobs: `['backend-lint', 'backend-tests', 'dependency-audit', 'frontend-tests', 'frontend-typecheck']`. Probe: `ci.yml contains 'preview': False`, `'EXPO_TOKEN': False`, `'eas ': False`, `'channel': False`, `'fetch-depth': False`. No `scripts/check_channel_freshness.py`, no `tests/test_channel_freshness.py`. `grep -rn EXPO_TOKEN` (excluding node_modules/.git) → 0 hits outside this unit's own `.qa-w3b/` scratch.
* **The gap the plan quotes is stale.** "6 commits / 72 files" was measured at 76ace90. At ed75dc70 the phones are **33 first-parent commits / 28 merges / 141 commits / 311 files** behind (section 3.1). The defect grew ~5x while the finding sat in the queue, which is the point of the guard.
* **The runbook exists — the brief's "docs/runbooks listing did not show it" is wrong.** `ls docs/runbooks` lists `qaren-canary-onboarding.md`: 375 lines, last touched by `f3bfb7b1 docs(canary): runbook for ENABLE_NEW_ONBOARDING 10/50/100 ramp + rollback`, "**Last revised:** 2026-05-07" (line 5). It carries `--branch production` at **five** lines (154, 158, 190, 194, 369), which is the hazard `MB-TWO-LEVER-RELEASE-10` names ("Do NOT publish to --branch production: no production build exists, so it reaches zero devices").
* **Three of the four publish lines are ALREADY on main, in the wrong file.** `CLAUDE.md:495` says, verbatim: *"Publish: `eas update --branch preview --clear-cache` for the FIRST run after `8d8b9dc` (Metro `cacheVersion` now keys on `babel.config.js`; …), no `NODE_ENV` override, record the EAS group id + SHA, never `--branch production`."* **[CORRECTED]** The sourcemap-upload line exists nowhere as an instruction: `grep -rn expo-upload-sourcemaps` (excl. node_modules) hits only `SmartCompareApp/package-lock.json:3828` (the `@sentry/react-native` `bin` entry, twice) and the finding text inside the two review JSONs; `src/services/sentry.ts:10-16` carries the follow-up comment ("Sourcemap upload via the expo plugin object form … Needs `SENTRY_AUTH_TOKEN` in CI") but not the literal script name. So the runbook half is: make the runbook agree with CLAUDE.md, add the one missing line, and add the ledger. Do not re-derive the publish policy.
* **Line anchors that moved.** `MB-TWO-LEVER-RELEASE-10` cites `babel.config.js:46-52` for the console-strip gate. At ed75dc70 the gate is at **`babel.config.js:190-198`** (`isProduction = NODE_ENV === 'production' || BABEL_ENV === 'production'` at 190-192, `isTest` at 193, `if (isProduction) plugins.push(removeConsolePlugin)` at 196-197, `if (!isTest)` at 199). `MB-TWO-LEVER-RELEASE-05` cites `sentry.ts:15` — still the sourcemap follow-up comment (13-16). `MB-RECONCILE-06` cites `ResultsScreen.tsx:345`, `MB-RECONCILE-19` cites the checkup doc `:1`, `MB-TWO-LEVER-RELEASE-10` cites `package.json:23` — none is touched by this unit; not re-located.
* **A premise of the NODE_ENV line is weaker than the finding says (measured, section 3.3).** The runbook line is still worth writing, but it must say the true reason.
* **`docs/ota/` does not exist at HEAD** (`ls docs/ota` → No such file). The draft's optional new directory is dropped: the ledger lives in the runbook (section 4.4).

Nothing is dropped. Everything the plan lists is red; the numbers are updated and the runbook scope is narrowed to "reconcile with CLAUDE.md + sourcemaps + ledger".

## 3. The defect — measured

### 3.1 Phones vs main (read-only git at ed75dc70)

```
HEAD          : ed75dc708b82c0b911c9de8a3e59d4418c6e278c
phones (full) : 97b5f1501a1242c405fd3cf12bee9ab419db2bdd
phones is ancestor of origin/main : True
first-parent commits behind       : 33
merge commits behind              : 28
all commits behind                : 141
diff --stat tail                  :  311 files changed, 74875 insertions(+), 2282 deletions(-)
phones is ancestor of origin/main~1 (=> >1 behind): True
```

**[CORRECTED]** Exactly **five** of the 33 first-parent commits are direct pushes, not merges — `git log --oneline --first-parent --no-merges 97b5f15..origin/main`: `9b737d7c`, `76ace902`, `79a4594a`, `54ff871b`, `187155ed` (33 − 28 = 5). The draft also listed `9a825e41`; that commit is the tip of the `docs/session-65-part4` branch merged by `ed75dc70`, is on main but NOT on the first-parent chain (`git rev-list --first-parent origin/main | grep -c 9a825e41` → `0`). This is why the guard counts **first-parent commits**, not merge commits: "one merge behind" as a merge count would let a direct-push regression through.

### 3.2 CI cannot see it

`ci.yml` triggers on `pull_request`/`push` to `main` (lines 3-7) and every job runs `actions/checkout@v4` (lines 13, 116, 166, 205, 251) with the default `fetch-depth` — per the actions/checkout README (context7 `/actions/checkout`): "The `fetch-depth` input specifies the number of commits to fetch, with `0` indicating all history for all branches and tags. It defaults to `1`." Even a job that wanted to compare could not: a depth-1 clone has no history for `merge-base` or `rev-list`.

### 3.3 The runbook publishes to a channel with zero devices, and the NODE_ENV claim is half-true

`docs/runbooks/qaren-canary-onboarding.md`:

```
154	eas update --branch production \
155	  --message "Canary onboarding ramp 10% → 50%"
...
158	eas update:list --branch production --limit 5
...
190	eas update --branch production \
191	  --message "ROLLBACK — canary onboarding to 0%"
...
194	eas update:list --branch production --limit 5
...
369	| EAS Update | `cd SmartCompareApp && eas update --branch production --message "..."` |
```

`SmartCompareApp/eas.json:13-21` binds `build.preview.channel: "preview"` and `build.production.channel: "production"`; the finding records no production build exists, and the phones are on `preview` (shared facts). An operator following the runbook's rollback section (§3, lines 174-214) during an incident would publish to nobody.

**NODE_ENV, measured on the installed toolchain.** `MB-TWO-LEVER-RELEASE-10` says "from a shell with NO NODE_ENV override (babel.config.js gates the production console-strip on NODE_ENV/BABEL_ENV === 'production')". The gate is real (`babel.config.js:190-198`). But `eas update` bundles by spawning `expo export` (`eas-cli/build/project/publish.js:149-212` `buildBundlesAsync`, args `export --output-dir <inputDir> <sourceMapArgs> --dump-assetmap --platform … [--clear]` — no `--dev`), and `@expo/cli@54.0.24` `build/src/export/exportApp.js:116-119` reads:

```js
    // Force the environment during export and do not allow overriding it.
    const environment = dev ? 'development' : 'production';
    process.env.NODE_ENV = environment;
```

with `dev` sourced only from `--dev` (`export/resolveOptions.js:79`). So a shell `NODE_ENV=development` cannot defeat the strip through `eas update`. What CAN: `eas update --skip-bundler` after a hand-run `npx expo export --dev` (`publish.js:218`: "`--skip-bundler` requires the project to be exported manually before uploading"), or `BABEL_ENV=test` in the shell, which flips `isTest` (`babel.config.js:193`) and drops the B1 lucide splitter (`:199`) from the bundle. The runbook line therefore reads: **publish only through `eas update` (never `--skip-bundler`), with no `NODE_ENV`/`BABEL_ENV` set in the shell.** The finding's line is kept; its stated reason is corrected in the PR body.

**Sourcemaps ARE exported by default — the upload line has something to upload.** `eas update`'s hidden `source-maps` flag defaults to `'true'` (`commands/update/index.js:91-95`) and `getSourceMapExportCommandArgs` (`publish.js:669-681`) turns that into `--source-maps` on the `expo export` spawn; `--input-dir` defaults to `dist` (`index.js:73-77`). The installed `@sentry/react-native@7.2.0` ships `scripts/expo-upload-sourcemaps.js` (`bin.sentry-expo-upload-sourcemaps`, `package.json:47-49`); it walks the directory for `.js/.hbc/.map` (`:71-95`), skips any bundle without a `.map` (`:206-215`) and warns "Ensure you are running `expo export` with the `--source-maps` flag" when nothing uploads (`:235-238`). It resolves org/project/url from the app.json plugin block when the env vars are unset (`:137-183`; `app.json:130-134` = `https://de.sentry.io/`, `qaren-rr`, `react-native`) and needs only `SENTRY_AUTH_TOKEN` (`:189`).

### 3.4 What `eas update:list --json` actually returns (the brief's stated mechanism is insufficient)

The brief: "resolving the channel needs `eas update:list --branch preview --json --non-interactive`". Read on eas-cli 18.8.1:

`build/commands/update/list.js:65-71` → `listAndRenderUpdateGroupsOnBranchAsync` → `build/update/queries.js:171-183` `renderUpdateGroupsOnBranch`:

```js
    const updateGroupDescriptions = (0, utils_1.getUpdateGroupDescriptionsWithBranch)(updateGroups);
    const branch = { name: branchName, id: updateGroups[0]?.[0].branch.id ?? 'N/A' };
    if (json) {
        (0, json_1.printJsonOnlyOutput)({ ...branch, currentPage: updateGroupDescriptions });
        return;
    }
```

and `build/update/utils.js:154-165` `getUpdateGroupDescriptionsWithBranch` emits per group exactly: `branch, message (pre-formatted "[Sep 02 01:34 by actor, runtimeVersion: 1.0.0] msg"), runtimeVersion, isRollBackToEmbedded, rolloutPercentage, codeSigningKey, group, platforms`. **No `gitCommitHash`, no `createdAt`.** The hash is only emitted by `eas update:view <groupId> --json` (`build/commands/update/view.js:74` → `getUpdateJsonInfosForUpdates`, `utils.js:129-142`: `id, createdAt, group, branch, message, runtimeVersion, platform, manifestPermalink, isRollBackToEmbedded, gitCommitHash`, one entry per platform). The same `getUpdateJsonInfosForUpdates` shape is what `eas update --json` itself prints at publish time (`commands/update/index.js:446-448`).

Facts that shape the script and the job:

* `build/utils/json.js:26-42` `sanitizeValue` drops every key whose value is `null` (`if (key !== '__typename' && value[key] !== null)`). A group published without a git hash has **no `gitCommitHash` key at all**, not `null`. The parser must treat "absent" as unresolvable, not KeyError.
* `enableJsonOutput` (`json.js:9-15`) redirects `process.stdout.write` to stderr for the duration and `printJsonOnlyOutput` restores it only for the JSON line, so with `--json` stdout is pure JSON — safe to redirect to a file.
* `--limit`: `list.js:34` `getLimitFlagWithCustomValues({ defaultTo: 25, limit: 50 })` → `pagination.js:26-31` parses 1..50, so `--limit 1` is valid. `--json` "Implies --non-interactive" (`commandUtils/flags.js:12-14`); `--non-interactive` is kept explicit anyway.
* `update:view` needs only `LoggedIn` context (`view.js:43-45`, and it calls `getContextAsync` with `nonInteractive: true` at `:51`); `update:list` needs `ProjectId` (`list.js:37-40`) → it must run with `SmartCompareApp` as cwd. Project-id resolution (`ProjectIdContextField.js` → `getPrivateExpoConfigAsync`): because `expo` is in `package.json.dependencies`, `isExpoInstalled` (`project/projectUtils.js:57-60`, reads package.json, not node_modules) is true and eas-cli spawns `npx expo config --json` in the project dir (`project/expoConfig.js:34-42`), falling back to its bundled `@expo/config` with `skipSDKVersionRequirement: true` only if that spawn throws. To make that spawn deterministic the job runs `npm ci` first (the pattern the file already uses at lines 214 and 260, with the setup-node npm cache at 173-177 / 207-211 / 253-257).
* **[CORRECTED — anchor]** `eas.json` `cli.version` is enforced by `applyCliConfigAsync` in `build/commandUtils/context/contextUtils/findProjectDirAndVerifyProjectSetupAsync.js:17-26` (`semver.satisfies(easCliVersion, config.version)` else throws "You are on eas-cli@… which does not satisfy the CLI version constraint defined in eas.json"; escape hatch `EAS_SKIP_CLI_VERSION_CHECK`), reached through the `ProjectId`/`ProjectDir` context fields (so `update:list` runs it; `update:view`, `LoggedIn` only, does not). The job pins **`eas-cli@18.8.1`** — the exact version the shapes above were read on, and it satisfies `>= 18.8.1`. `eas-cli` `engines.node` is `>= 20.0.0` — the job's `setup-node` uses `'20'`, same as the other three node jobs.
* `EXPO_TOKEN`: `build/user/SessionManager.js:31` `return process.env.EXPO_TOKEN ?? null;` and `:118` "Either log in with `eas login` or set the `EXPO_TOKEN` environment variable if you're using EAS CLI on CI (https://docs.expo.dev/accounts/programmatic-access/)".
* The published hash is `git rev-parse HEAD` at publish time (`vcs/clients/git.js:213-221` `getCommitHashAsync`), recorded as `gitCommitHash` (`commands/update/index.js:360, 394`; the human output appends `*` when the tree was dirty, `:492-496`). Non-interactive `eas update` on a dirty tree throws `Commit all changes. Aborting...` (`build/utils/repository.js:41-52`); interactively it offers to commit. So the hash only describes the bundle when the tree was clean — the runbook says so.

### 3.5 The GitHub Actions rules the job relies on (context7 `/websites/github_en_actions`, read 2026-09-11)

1. *Using secrets in a workflow*: "Secrets cannot be directly referenced in if conditionals. To use secrets for conditional logic, set them as job-level environment variables first, then reference those variables within the step." The workflow-syntax reference repeats it under `jobs.<job_id>.steps[*].if`: "secrets cannot be directly referenced in if conditionals; they must first be set as job-level environment variables before being evaluated."
2. *Contexts → Context availability*: "Most job-level keys can access contexts such as github, needs, strategy, matrix, vars, and inputs, whereas step-level keys typically have broader access to additional contexts like job, runner, env, secrets, and steps". So neither `secrets` nor `env` is readable in a job-level `if`; the skip is per-step.
3. The documented example (workflow-syntax, "Run a step if a secret has been set"):

```yaml
jobs:
  my-jobname:
    runs-on: ubuntu-latest
    env:
      super_secret: ${{ secrets.SuperSecret }}
    steps:
      - if: ${{ env.super_secret != '' }}
        run: echo 'This step will only run if the secret has a value set.'
      - if: ${{ env.super_secret == '' }}
        run: echo 'This step will only run if the secret does not have a value set.'
```

4. *Expressions*: "Use the `${{ }}` syntax to evaluate an expression when assigning a value to an environment variable" (`env: MY_ENV_VAR: ${{ <expression> }}`); `!=`/`==` are expression operators. And `jobs.<job_id>.steps[*].env`: "step-level variables override job- and workflow-level variables with the same name … Sensitive values such as passwords or tokens should be set using the `secrets` context."

**Design consequence, and one deliberate hardening over the verbatim example.** The example maps the RAW secret to a job-level env var, which would hand `EXPO_TOKEN` to every step in the job — including `npm ci` and the ~1,500 postinstall scripts it can run. This job instead maps a **boolean** at job level, `EXPO_TOKEN_SET: ${{ secrets.EXPO_TOKEN != '' }}` (facts 1 + 4: `secrets` is readable in `jobs.<job_id>.env`, and a comparison is an expression, which evaluates to the string `true`/`false`), gates every post-checkout step on `env.EXPO_TOKEN_SET == 'true'`, and scopes the raw `EXPO_TOKEN: ${{ secrets.EXPO_TOKEN }}` to the ONE step that runs eas-cli. The composition is two documented facts, not itself a documented example; the shape pin (test 8) therefore asserts the STRUCTURE (job-level key derived from the secret; raw secret only on the eas step; every non-checkout step gated), and if the first CI run ever showed the boolean not evaluating, the fallback is the verbatim form (raw secret at job env) with the same pins minus the scoping assertion. The job always runs and succeeds when the secret is absent — which is exactly "skip cleanly, not fail", and is also the path every fork PR takes (secrets are not passed to fork PRs).

## 4. The fix — minimal design

### 4.1 Files

| file | change |
|---|---|
| `.github/workflows/ci.yml` | **append** one job `channel-freshness` after `frontend-tests` (section 4.2). The five existing jobs are byte-identical. |
| `scripts/check_channel_freshness.py` | **new**, stdlib-only (`json, argparse, subprocess, pathlib, os, sys, dataclasses, typing`). Section 4.3. |
| `tests/test_channel_freshness.py` | **new** — the unit tests (section 5, tests 1-7). |
| `tests/test_ci_gates.py` | **append** the ci.yml + runbook shape pins (section 5, tests 8-10), reusing the existing `_load`/`_steps`/`_run_text` helpers (`:44-61`). Nothing existing changes (38 tests pass at base, measured). |
| `.github/black-clean-paths.txt` | **append** `scripts/check_channel_freshness.py` and `tests/test_channel_freshness.py` (the ratchet's own rule at its line 18: "Added a new .py file? It should be black-clean, so add it here"). Both files are written black-26.5.1-clean. |
| `docs/runbooks/qaren-canary-onboarding.md` | replace the five `--branch production` lines; add "2.0 Publish procedure" and "9. OTA ledger". Section 4.4. |

Not touched: `SmartCompareApp/**` (no client code, no `package.json`, no lockfile), `app/**`, `eas.json`, `app.json`, branch protection, `CLAUDE.md` (its `:495` block stays authoritative; the runbook now agrees with it — the stale `@sentry/react-native@8.11.1` line there is recorded, not fixed), `.claude/skills/qaren-eas-deploy/SKILL.md` (51 lines; its line 50 already points at the runbook as "Operational runbook" — the runbook edit reaches it by reference), `docs/runbooks/bundle-d-ota-delivery-troubleshooting.md` (already uses `--branch preview`, `update:list`, `update:view`, `--clear-cache` at lines 35, 126-139, 209-266 — consistent with the new section, no edit).

### 4.2 The job (append to ci.yml after `frontend-tests`, line 274)

```yaml
  # CHANNEL FRESHNESS (W3-13, MB-RECONCILE-06). Phones run whatever `eas update`
  # last published to the `preview` channel — merging to main ships NOTHING to a
  # device (CLAUDE.md "Two-lever launch model"). Measured 2026-09-11 at ed75dc70:
  # the channel ran 97b5f15, 33 first-parent commits / 311 files behind main, and
  # CI was green. This job resolves the channel's published commit and fails
  # when it is more than ONE first-parent commit behind origin/main.
  #
  # NOT A REQUIRED CHECK and NON-BLOCKING until 2026-09-18: the check step carries
  # `continue-on-error: true` (same device as the npm-audit step above). After a
  # week of readings, remove that line and add `channel-freshness` to the
  # branch-protection required list (repo-admin action). tests/test_ci_gates.py
  # pins the non-blocking state; flip the pin in the same PR that flips the line.
  #
  # SKIPS CLEANLY WITHOUT THE SECRET. `secrets.*` cannot be read from an `if`
  # (docs.github.com "Using secrets in a workflow"), and a job-level `if` sees
  # neither `secrets` nor `env` (contexts reference: job-level keys see
  # github/needs/strategy/matrix/vars/inputs). So a job-level env var DERIVED
  # from the secret gates every step after checkout — the documented "Run a step
  # if a secret has been set" pattern, with one hardening: the job-level value is
  # a boolean, and the raw token is scoped to the single eas-cli step so it is
  # never in the environment of `npm ci` and its postinstall scripts. Until Ahmed
  # adds the EXPO_TOKEN repository secret (an Expo access token,
  # docs.expo.dev/accounts/programmatic-access) the job prints a notice and passes.
  #
  # WHY TWO eas COMMANDS: at eas-cli 18.8.1 `update:list --json` emits group id,
  # runtimeVersion, platforms, message — but NOT the git commit; only
  # `update:view <group> --json` carries `gitCommitHash` (one entry per platform).
  # eas-cli is pinned to the exact version those JSON shapes were read on;
  # eas.json requires >= 18.8.1 and eas-cli requires node >= 20.
  channel-freshness:
    runs-on: ubuntu-latest
    env:
      EXPO_TOKEN_SET: ${{ secrets.EXPO_TOKEN != '' }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # merge-base / rev-list need history; the default (1) has none

      - name: Skipped — EXPO_TOKEN secret not configured
        if: ${{ env.EXPO_TOKEN_SET != 'true' }}
        run: echo "::notice title=channel-freshness skipped::Add the EXPO_TOKEN repository secret to arm the preview-channel freshness guard."

      - uses: actions/setup-node@v4
        if: ${{ env.EXPO_TOKEN_SET == 'true' }}
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: SmartCompareApp/package-lock.json

      - uses: actions/setup-python@v5
        if: ${{ env.EXPO_TOKEN_SET == 'true' }}
        with:
          python-version: '3.12'

      # eas-cli resolves the project id by spawning `npx expo config --json` in
      # the app dir whenever `expo` is a package.json dependency; install first
      # so that spawn is deterministic against the lockfile. No token here.
      - name: Install frontend dependencies
        if: ${{ env.EXPO_TOKEN_SET == 'true' }}
        run: cd SmartCompareApp && npm ci

      - name: Resolve the preview channel (eas-cli 18.8.1)
        if: ${{ env.EXPO_TOKEN_SET == 'true' }}
        env:
          EXPO_TOKEN: ${{ secrets.EXPO_TOKEN }}   # the ONLY step that sees the token
        run: |
          cd SmartCompareApp
          npx --yes eas-cli@18.8.1 update:list --branch preview --limit 1 --json --non-interactive > "$RUNNER_TEMP/preview-list.json"
          GROUP=$(python -c "import json,os; print(json.load(open(os.environ['RUNNER_TEMP'] + '/preview-list.json'))['currentPage'][0]['group'])")
          npx --yes eas-cli@18.8.1 update:view "$GROUP" --json > "$RUNNER_TEMP/preview-group.json"

      - name: Preview channel is at most one first-parent commit behind main (NON-BLOCKING until 2026-09-18)
        if: ${{ env.EXPO_TOKEN_SET == 'true' }}
        continue-on-error: true
        run: |
          python scripts/check_channel_freshness.py \
            --list-json "$RUNNER_TEMP/preview-list.json" \
            --view-json "$RUNNER_TEMP/preview-group.json" \
            --main origin/main --max-behind 1
```

Design notes the implementer must keep:

* `origin/main` exists on both triggers because `fetch-depth: 0` fetches "all history for all branches and tags". On `pull_request` the checkout is the merge ref; the comparison is still phones-vs-`origin/main`, deliberately — a PR does not change what phones run.
* No `pip install`: the script is stdlib-only and a test pins that (test 6). The two `python -c` one-liners in the resolve step are stdlib too.
* The group is taken from `currentPage[0]`. The list JSON carries no `createdAt`, so "index 0 is the newest group" is an assumption about server ordering that only the first armed run can confirm (the `update:view` JSON does carry `createdAt`, which the script prints so the run log shows the date). Recorded in section 8.
* `continue-on-error` on the STEP, not the job — the file already uses this at lines 157 and 199, and a step-level failure still shows red in the job log while the job/check stays green.
* Runtime: `npm ci` (cached ~1-2 min) + two eas calls. If judged too heavy per PR, the alternative is a direct GraphQL query with the token (`eas-cli/build/graphql/queries/UpdateQuery.js`) — not specified here because it pins an internal API instead of a CLI version; the script does not care which fetcher produced the two files.
* If the `secrets.EXPO_TOKEN != ''` boolean ever fails to evaluate at job level (section 3.5), fall back to the verbatim documented form; every pin except the token-scoping assertion survives unchanged.

### 4.3 `scripts/check_channel_freshness.py`

Pure decision logic with the ancestry injected, so the tests never touch git:

```python
@dataclass(frozen=True)
class GroupRef:            # from update:list --json
    group: str
    runtime_version: str | None
    is_rollback_to_embedded: bool
    message: str | None

class ChannelError(Exception): ...

def parse_list(payload: dict) -> GroupRef        # currentPage[0]; ChannelError("no update groups on branch") if empty
def parse_view(payload: list) -> set[str]        # {u["gitCommitHash"] for u in payload if u.get("gitCommitHash")} — absent key ⇒ not counted
                                                 # also surfaces createdAt + platforms for the log line

class Ancestry(Protocol):
    def contains(self, sha: str) -> bool
    def is_ancestor_of_main(self, sha: str) -> bool
    def first_parent_distance(self, sha: str) -> int

class GitAncestry:                               # subprocess git, cwd = repo root, main ref injected
    contains            -> git cat-file -e <sha>^{commit}
    is_ancestor_of_main -> git merge-base --is-ancestor <sha> <main>
    first_parent_distance -> int(git rev-list --count --first-parent <sha>..<main>)

FRESH, STALE, UNRESOLVABLE, NOT_ON_MAIN, ROLLBACK = 0, 1, 2, 3, 4

def evaluate(group: GroupRef, hashes: set[str], ancestry: Ancestry, max_behind: int = 1) -> tuple[int, str]:
    if group.is_rollback_to_embedded: return ROLLBACK, "...phones run the binary's embedded bundle"
    if len(hashes) != 1:                return UNRESOLVABLE, f"gitCommitHash unresolvable from update:view (got {sorted(hashes)})"
    sha = next(iter(hashes))
    if not ancestry.contains(sha):      return UNRESOLVABLE, f"{sha[:8]} is not in this checkout's history (dirty-tree or fork publish? shallow clone?)"
    if not ancestry.is_ancestor_of_main(sha): return NOT_ON_MAIN, f"{sha[:8]} is not an ancestor of main"
    d = ancestry.first_parent_distance(sha)
    if d > max_behind:                  return STALE, f"preview runs {sha[:8]}, {d} first-parent commits behind main (max {max_behind})"
    return FRESH, f"preview runs {sha[:8]}, {d} behind main"

def main(argv=None) -> int:
    # --list-json PATH --view-json PATH --main REF (default origin/main) --max-behind N (default 1) --repo PATH (default repo root)
    # prints one summary line; on non-zero prefixes it with `::error::` (STALE/NOT_ON_MAIN/ROLLBACK) or `::warning::` (UNRESOLVABLE)
    # appends the same line to $GITHUB_STEP_SUMMARY when that env var is set
    # exit code == verdict code
```

Prototype of exactly this logic, run in the probe over the fake payloads and then over REAL git ancestry with the phones' recorded hash (section 10, block 15): today's answer is `1 preview runs 97b5f150, 33 first-parent commits behind main (max 1)`.

Exit-code contract (goes into the module docstring and the PR): 0 fresh · 1 stale · 2 unresolvable (empty page / no hash / >1 hash / hash unknown to the checkout) · 3 published from a commit not on main · 4 roll-back-to-embedded. The CI step treats every non-zero as a failure (non-blocking for now); 2 is a `::warning::` because it usually means the fetch side, not the phones, is wrong.

`--max-behind 1` means: a publish from HEAD followed by ONE more first-parent commit on main is still fresh; the second one without a republish is stale. Direct pushes count the same as merges (section 3.1).

### 4.4 The runbook (`docs/runbooks/qaren-canary-onboarding.md`)

1. Lines 154, 158, 190, 194, 369: `--branch production` → `--branch preview`, each with a one-line reason: *"`preview` is the only channel with devices; no production build exists (eas.json binds `production` to `build.production`, never built) — `--branch production` reaches zero phones."*
2. New **section 2.0 "Publish procedure — the only sanctioned command sequence"** (before 2.1, i.e. between lines 127 and 128), the lines the finding asks for, with the measured reasons:

```bash
cd SmartCompareApp
git fetch origin main
git status --porcelain            # MUST be empty. Non-interactive `eas update` aborts on a dirty tree; interactively it
                                  # offers to commit — either way the recorded gitCommitHash only describes the bundle
                                  # if the tree was clean (the human output marks a dirty publish with a trailing *).
git merge-base --is-ancestor HEAD origin/main && git rev-parse HEAD
                                  # publish from a commit that IS on main — the CI guard fails a hash it cannot find
                                  # on main (exit 3), and reviewers cannot audit a bundle built from a side branch.
# Do NOT set NODE_ENV or BABEL_ENV in this shell, and NEVER use --skip-bundler: `eas update` bundles through
# `expo export`, which forces NODE_ENV=production itself (@expo/cli exportApp.js "Force the environment during
# export"); a hand-exported --dev bundle fed in with --skip-bundler is the way the console-strip
# (babel.config.js isProduction) gets skipped, and BABEL_ENV=test drops the lucide splitter.
eas update --branch preview --clear-cache --message "<PR numbers shipped>" --non-interactive --json \
  | tee "$TEMP/preview-publish-$(date +%F).json"
                                  # --json prints one entry per platform with id, group, gitCommitHash, runtimeVersion,
                                  # createdAt (non-JSON progress goes to stderr) — paste it into the ledger row below.
                                  # --clear-cache: metro.config.js keys the transform cache on babel.config.js since
                                  # 8d8b9dc; keep it, it is cheap insurance. NEVER --branch production (zero devices).
# Sourcemaps — required, or every crash from this bundle is unsymbolicated in Sentry (MB-TWO-LEVER-RELEASE-05).
# `eas update` already exported them (its source-maps flag defaults to true; input dir defaults to dist):
SENTRY_AUTH_TOKEN=<token> node node_modules/@sentry/react-native/scripts/expo-upload-sourcemaps dist
                                  # org/project/url resolve from the @sentry/react-native plugin block in app.json
                                  # (qaren-rr / react-native / https://de.sentry.io/); only the token is needed. The
                                  # script's own `NODE_ENV ||= development` line affects only its process, not the bundle.
# Verify + record:
eas update:view <group-id> --json # gitCommitHash must equal the SHA you published from
# Append a row to section 9 (OTA ledger). Then on a device: force-close and reopen TWICE (first launch downloads,
# second swaps — docs/SESSION_BUNDLES.md:467 "two-launch propagation"), and check one analytics POST returns 2xx.
```

3. New **section 9 "OTA ledger"** — a table `date | channel | group id | gitCommitHash | runtimeVersion | sourcemaps uploaded | published by | notes`, seeded with the known history so the gap is visible: `2026-09-02 | preview | (not recorded) | 97b5f1501a1242c405fd3cf12bee9ab419db2bdd | 1.0.0 | no | Ahmed | M18/M20 set (CONTEXT_SESSION_LOG.md:131); group id was never recorded — the gap MB-two-lever-03 flagged`, plus the earlier rows already in `docs/SESSION_BUNDLES.md` copied as-is with "sourcemaps: no": `d540c1e6-c07c-46d7-ac69-5103dde1fb56` (Bundle E, commit `0129106`, `:36`/`:47`), `18af8a48-a191-4b5d-bc62-9508ab4b5952` (`:523`), `90087c4f-ee62-4e4c-84e7-d0c17a62276f` (`:545`), `ba52fdf9-e5c1-41cd-…` (`:646`), `3efa9d81` (`:721`, backend `2cb4439`, 2026-06-18).
4. "Last revised" (line 5) → 2026-09-11 with a one-line changelog entry.

Nothing else in the runbook changes (the canary metrics §1, monitoring §4, decision tree §5, cleanup §6, open question §7 are untouched).

### 4.5 Flags / migrations / compatibility

None. There is no runtime code. Backend on main and phones on 97b5f15 / on the pending OTA are unaffected by definition.

## 5. Red tests

All backend, `PYTHONIOENCODING=utf-8 python -m pytest tests/test_channel_freshness.py tests/test_ci_gates.py -q -p no:randomly -p no:cacheprovider`, no network, no env. Fixtures are inline dicts shaped exactly as section 3.4 (two-entry `currentPage` where it matters, two-platform `update:view` list — the probe's `FAKE_LIST`/`FAKE_VIEW` are the reference).

`tests/test_channel_freshness.py` (new):

1. **`test_parse_list_takes_the_first_group`** — a two-entry `currentPage` → `GroupRef.group == "g-newest"`, `runtime_version == "1.0.0"`, `is_rollback_to_embedded is False`. RED today: `ModuleNotFoundError: scripts.check_channel_freshness` (file absent, measured). Mutation that must redden it: `currentPage[-1]`.
2. **`test_parse_list_empty_page_is_a_channel_error`** — `{"name":"preview","id":"b","currentPage":[]}` → `pytest.raises(ChannelError)`. RED: module missing. Mutation: returning `None` instead of raising.
3. **`test_parse_view_absent_hash_is_not_a_hash`** — the two-platform list with the `gitCommitHash` key **deleted** (eas-cli's `sanitizeValue` drops nulls) → `parse_view(...) == set()`; with both present and equal → `{"97b5f15…"}`; with the two platforms disagreeing → a 2-set. RED: module missing. Mutation: `u["gitCommitHash"]` (KeyError) reddens the first case.
4. **`test_evaluate_verdicts`** (parametrized over a `FakeAncestry` whose main chain is `m0..m5` with `97b5f15…` at index 2 and a `sidesha` off-main — the probe's class): at head → `(0, …)`; one behind → `(0, …)`; 97b5f15 (3 behind) → `(1, "… 3 first-parent commits behind main (max 1)")`; empty hash set → 2; `deadbeef` → 2; `sidesha` → 3; rollback group → 4; `max_behind=3` makes 97b5f15 fresh. RED: module missing. Mutations: `d >= max_behind` reddens "one behind"; dropping the `contains` check reddens `deadbeef` (it would fall to `is_ancestor` and return 3, not 2); dropping the rollback branch reddens case 4.
5. **`test_git_ancestry_uses_first_parent_and_merge_base`** — monkeypatch `subprocess.run` to record argv and return canned `CompletedProcess(returncode=0, stdout="33\n")`; assert `first_parent_distance("abc") == 33` and the recorded argv is exactly `["git","rev-list","--count","--first-parent","abc..origin/main"]`; `is_ancestor_of_main("abc")` ran `["git","merge-base","--is-ancestor","abc","origin/main"]`; `contains("abc")` ran `["git","cat-file","-e","abc^{commit}"]`; all with `cwd == repo`. RED: module missing. Mutation: dropping `--first-parent` (the count would silently become 141 on today's history) reddens it.
6. **`test_script_is_stdlib_only`** — `ast` over the file: every `import`/`from` root module is in `sys.stdlib_module_names` (Python 3.10+; measured on 3.12.9: 301 names, `json` in, `yaml` NOT in). RED: file missing. Mutation: `import yaml` reddens it. Rationale pinned in the docstring: the CI job installs nothing with pip.
7. **`test_main_exit_codes_and_annotations`** — write the two fixture JSONs to `tmp_path`, call `main([...])` with `GitAncestry` monkeypatched to the `FakeAncestry` (expose an `ancestry_factory` hook or monkeypatch the class attribute), capture stdout: stale → return 1 and the first line starts with `::error::`; unresolvable → 2 and `::warning::`; fresh → 0 and no `::` prefix; `GITHUB_STEP_SUMMARY` set to a tmp file → the line is appended. RED: module missing. Mutation: swapping error/warning prefixes.

`tests/test_ci_gates.py` (append; same `_load`/`_steps`/`_run_text` helpers at `:44-61`, same style as `test_dependency_audit_blocks_on_python_and_still_reports_on_npm` at `:346`):

8. **`test_channel_freshness_job_skips_cleanly_without_the_secret`** — `jobs["channel-freshness"]` exists (RED today: `KeyError` — the parsed job list is the five above); `job["env"]` has exactly one key, `EXPO_TOKEN_SET`, whose value contains `secrets.EXPO_TOKEN` and `!= ''` (a job-level value that is the bare `${{ secrets.EXPO_TOKEN }}` fails — the raw token must not be job-wide); the first step is `actions/checkout@v4` with `with.fetch-depth == 0`; **every other step** has an `if` that mentions `env.EXPO_TOKEN_SET` (the skip-cleanly contract — a step without it would run and fail without the secret); exactly one step's `if` is the negative branch and its `run` contains `::notice`; the resolve step's `env` is exactly `{"EXPO_TOKEN": "${{ secrets.EXPO_TOKEN }}"}` and NO other step has an `env` mentioning `secrets.` (token scoping); the resolve step's run contains `eas-cli@18.8.1`, `update:list --branch preview`, `--json`, `--non-interactive`, and `update:view`; the pin `18.8.1` satisfies `eas.json` `cli.version` (parse the `>= X` range and tuple-compare, no `packaging` import); the check step's run contains `scripts/check_channel_freshness.py` and `--max-behind 1`. Mutations: removing `fetch-depth`, removing one step's `if`, moving the raw secret to job env, changing the eas-cli pin.
9. **`test_channel_freshness_is_non_blocking_until_the_dated_flip`** — the check step has `continue-on-error: True` **and** the job's leading comment block in the raw file text contains `NON-BLOCKING until 2026-09-18`. Docstring: "flip both in the PR that makes it blocking; this pin is the reminder, not a calendar trigger — a date-aware assertion would redden the REQUIRED backend-tests job on a no-change day, which is the failure mode this file exists to end." RED: KeyError. Mutation: deleting `continue-on-error`.
10. **`test_canary_runbook_publishes_to_the_channel_with_devices`** — `docs/runbooks/qaren-canary-onboarding.md`: zero occurrences of `--branch production` (RED today: 5, lines 154/158/190/194/369 — measured); contains `--branch preview --clear-cache`; contains `expo-upload-sourcemaps` (RED: 0, measured); contains `update:view` (RED: 0); contains `--skip-bundler` (in the "never" line); contains the ledger header `| gitCommitHash |` (RED: 0); and `CLAUDE.md` still contains `` never `--branch production` `` (consistency pin between the two documents; green today at `:495`). Mutation: reintroducing one `--branch production` line.

Decoration check: every test above fails without the unit (module/file/job absent or runbook lines present) and each names the mutation that reddens it after the fix. None passes today.

## 6. Preserve — behaviours that must stay identical

| behaviour | proof |
|---|---|
| The five existing CI jobs and their steps are unchanged | `tests/test_ci_gates.py` existing pins, all green at base (**38 passed, 13.07 s, measured**): `test_ci_keeps_existing_backend_and_frontend_jobs` (186), `test_ci_pr_gate_marker_selection_is_unchanged` (192), `test_ci_has_a_lint_job_running_black` (206), `test_lint_job_blocks_on_the_allowlist_and_only_reports_repo_wide_drift` (212), `test_black_is_pinned_to_an_exact_version_in_ci` (247), `test_ci_black_pin_matches_the_dependency_lock` (267), `test_dependency_audit_blocks_on_python_and_still_reports_on_npm` (346), `test_backend_tests_measure_and_floor_coverage` (384), `test_backend_tests_derives_deselect_from_the_committed_baseline` (875) — green before and after; plus a PR-review `git diff` of ci.yml that is a pure append after line 274. |
| Required checks set (`backend-lint, backend-tests, dependency-audit, frontend-tests, frontend-typecheck`) unchanged | branch protection is not touched; the PR body says so. |
| A PR with no `EXPO_TOKEN` secret (every fork PR; the repo today) gets a green `channel-freshness` job | test 8 (every non-checkout step gated) + the docs rules in 3.5. |
| `npm ci` never sees the token | test 8's scoping assertion. |
| Black allowlist entries are all genuinely clean | existing `test_black_allowlist_entries_are_actually_clean` (324) and `test_black_allowlist_exists_and_every_entry_is_a_real_file` (290) — the two new entries must pass them; `tests/test_ci_gates.py` is already on the allowlist and is black-clean at base (measured: "1 file would be left unchanged"). |
| `scripts/` package import style (`from scripts import …`, `scripts/__init__.py` present) | test 1 imports `from scripts.check_channel_freshness import …` exactly like `tests/test_cron_eval_nightly.py:20`. |
| The runbook's canary content (sections 1, 3-8) | unchanged text; `git diff` limited to the five lines + the two new sections + the header date. |
| `CLAUDE.md:495` publish block | untouched; test 10 pins its `never --branch production`. |
| Metro cache keying / babel gate | untouched (`metro.config.js`, `metro.cacheVersion.js` (`8d8b9dc8`), `babel.config.js` not in the diff). |

## 7. Gates

Backend half (the only code half):

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_channel_freshness.py tests/test_ci_gates.py -q -p no:randomly -p no:cacheprovider
python -m ruff check --select E9,F63,F7,F82 scripts/check_channel_freshness.py tests/test_channel_freshness.py tests/test_ci_gates.py
python -m black --check scripts/check_channel_freshness.py tests/test_channel_freshness.py     # both are new allowlist entries
python -m black --check tests/test_ci_gates.py                                                    # already on the allowlist — must stay clean after the append
python -c "import yaml; print(sorted(yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8'))['jobs']))"   # must list six jobs
```
**[CORRECTED]** (the draft's `python -m yaml -c …` is not a real invocation; the one-liner above was run at base and printed the five jobs.)

Module-reference comm gate (base vs head): union of `grep -rlE "check_channel_freshness|ci_gates|black-clean-paths|qaren-canary-onboarding" tests/` = today `tests/test_ci_gates.py` only (no other test references these; `test_channel_freshness.py` is new) + judgement importers: none (`scripts/check_channel_freshness.py` is imported by nothing but its test) + the unit files. Base run: `tests/test_ci_gates.py` → 38 passed (measured at ed75dc70; no `test_ci_gates` node is in `tests/.pre_impl_failures.txt`, 11 rows, all listed). Head run: both files.

Client half: **N/A — no file under `SmartCompareApp/` is touched.** Toolchain printed for the record: `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`. Neighbour jest suites: none (grep `__tests__`/`src` for the touched modules is empty by construction). tsc / eslint not required; the green phase's once-per-unit full jest run still applies per campaign rule.

Workflow YAML: there is no local runner. The shape pins (tests 8-9) are the gate; the first CI run on the PR is the executable one (it will take the skip branch until the secret exists — that run proves the skip path; the armed path is proven only after Ahmed adds the secret, section 8).

## 8. What this unit CANNOT do / Ahmed dependencies / device-only

Ahmed dependencies (the code half lands without any of them; each unlocks a behaviour):

1. **`EXPO_TOKEN` repository secret** — an Expo access token (personal or robot user with access to project `387a4fcb-76f6-4857-a2fb-39482ca4bd40`, `app.json:139-141`). Until then the job prints the notice and passes. This is the ONLY thing between "guard exists" and "guard measures".
2. **First armed run review** — confirms (a) `update:list` returns the newest group at `currentPage[0]` (the list JSON has no `createdAt`; the view JSON does, and the script prints it), (b) `npx expo config --json` behaves in the runner after `npm ci`, (c) the job-level `secrets.EXPO_TOKEN != ''` boolean evaluates as designed (fallback in 4.2 if not), (d) the recorded `gitCommitHash` of the 2026-09-02 publish is really `97b5f15` (taken from the finding; a dirty-tree publish would carry a different hash and the guard would say exit 2, which is itself informative — and MB-two-lever-03's "the cert-pin OTA may never have fired" question gets its first data point).
3. **Flip to blocking after 2026-09-18** — delete `continue-on-error: true`, update test 9, add `channel-freshness` to branch-protection required checks (repo-admin).
4. **The OTA itself** (`eas update --branch preview --clear-cache …` from main ≥ `8e9d499a`, per CLAUDE.md:495) — this unit makes it auditable; it does not perform it. The guard will read STALE until it happens.
5. **`SENTRY_AUTH_TOKEN`** for the sourcemap line — created in Sentry (org `qaren-rr`, project `react-native`, `https://de.sentry.io/`, `app.json:130-134`) with sourcemap-upload permission; used locally at publish time, not in CI. The runbook line is inert without it and says so.
6. **Policy question, not blocking:** should docs-only merges count toward `--max-behind`? Today every first-parent commit counts (22 of the 33 today are docs merges or docs pushes by subject). If that proves noisy, the follow-up is a path filter on `git diff --name-only` between the published SHA and main (`SmartCompareApp/` only) — out of scope here; the script's ancestry abstraction is where it would go.

Device / store only: whether the phones actually run 97b5f15 (EAS says what was published, not what a given device swapped in — the two-launch propagation); whether sourcemaps symbolicate (throw from a debug screen on a preview build and read the Sentry issue — `MB-TWO-LEVER-RELEASE-05` test_first).

Cannot be tested here: the workflow YAML executing (no local Actions runner); the eas-cli network path (no network in this batch — every JSON shape above was READ from the installed 18.8.1 source, not observed from a live call).

## 9. PR-body facts

* Base `ed75dc70`. Adds one CI job `channel-freshness`, one stdlib-only script `scripts/check_channel_freshness.py`, one test file, pins in `tests/test_ci_gates.py`, two allowlist entries, and edits `docs/runbooks/qaren-canary-onboarding.md`. Zero files under `SmartCompareApp/` or `app/`; no dependency, lockfile, flag, or migration. Nothing reaches a phone or Railway.
* Measured 2026-09-11 at ed75dc70: the `preview` channel runs `97b5f1501a1242c405fd3cf12bee9ab419db2bdd` (2026-09-02 01:34:56 +0300), which is **33 first-parent commits (28 merges, 5 direct pushes), 141 commits and 311 files (+74,875/−2,282) behind main**. The review's "6 commits / 72 files" was true at 76ace90. The guard reads STALE (exit 1) on this state; prototype output: `preview runs 97b5f150, 33 first-parent commits behind main (max 1)`.
* The job is **not a required check** and is **non-blocking until 2026-09-18** (`continue-on-error: true` on the check step; pinned by test). Flipping needs a code change plus a branch-protection change.
* **Skips cleanly without the secret**: `secrets` is not readable in an `if`, and a job-level `if` sees neither `secrets` nor `env` (docs.github.com: job-level keys see `github, needs, strategy, matrix, vars, inputs`; step-level keys additionally see `job, runner, env, secrets, steps`), so a job-level env var derived from the secret gates every step after checkout — the documented "Run a step if a secret has been set" pattern. **Hardening over the documented example:** the job-level value is the boolean `secrets.EXPO_TOKEN != ''`; the raw token is scoped to the single eas-cli step, so `npm ci` and its postinstall scripts never see it (pinned). Ahmed must add the `EXPO_TOKEN` repository secret (Expo access token); until then the job prints a notice and passes.
* **Two eas commands, pinned `eas-cli@18.8.1`** (eas.json requires `>= 18.8.1`, enforced by `applyCliConfigAsync`; eas-cli needs node ≥ 20, the job uses 20): at that version `update:list --json` emits `{name, id, currentPage:[{branch, message, runtimeVersion, isRollBackToEmbedded, rolloutPercentage, codeSigningKey, group, platforms}]}` — no commit hash; `update:view <group> --json` emits one entry per platform with `gitCommitHash`, and eas-cli's JSON sanitizer omits null keys, so an unhashed publish has no key (handled as "unresolvable", exit 2).
* `fetch-depth: 0` on the job's checkout: the default depth of 1 has no history for `merge-base`.
* "One merge behind" is implemented as **first-parent distance ≤ 1**; direct pushes to main count (five of the 33 today).
* Exit codes: 0 fresh · 1 stale · 2 unresolvable · 3 published from a commit not on main · 4 roll-back-to-embedded.
* Runbook: the five `--branch production` lines (154, 158, 190, 194, 369) are replaced with `--branch preview`; no production build exists, so that channel reaches zero devices. The publish procedure (section 2.0) and an OTA ledger (section 9) are added; the 2026-09-02 publish is entered with "group id: not recorded" — the gap it exists to close. The runbook now agrees with `CLAUDE.md:495`, which already carried three of the four lines.
* **Correction to `MB-TWO-LEVER-RELEASE-10`'s NODE_ENV reasoning**: `@expo/cli@54.0.24` `exportApp.js:116-119` forces `NODE_ENV=production` during `expo export` ("do not allow overriding it") and `eas update` spawns that export without `--dev`; a shell `NODE_ENV` cannot skip the console-strip through `eas update`. The real hazards are `--skip-bundler` with a hand-exported `--dev` bundle and `BABEL_ENV=test` (drops the lucide splitter). The runbook line says that. Its `babel.config.js:46-52` anchor is now `:190-198`.
* Sourcemaps: `eas update` already exports them (`source-maps` defaults `true`, `--input-dir` defaults `dist`); `node node_modules/@sentry/react-native/scripts/expo-upload-sourcemaps dist` (script shipped by the installed 7.2.0; org/project/url resolve from the app.json plugin block; needs only `SENTRY_AUTH_TOKEN`). Ahmed dependency; documented, not automated. CLAUDE.md's "`@sentry/react-native@8.11.1`" is stale (pin `~7.2.0`, installed 7.2.0) — recorded, not fixed here.
* Not verified here (no network, no runner): that `currentPage[0]` is the newest group (the list JSON has no `createdAt`), that the job-level boolean env evaluates (two documented facts composed; fallback documented), and that the 2026-09-02 publish recorded `97b5f15` as its hash. The first armed run answers all three.
* Local toolchain note: pytest 8.2.0 locally vs the `9.1.1` dev-lock pin; the tests use nothing version-specific.

## 10. Measurements run

All in `C:\Users\SynAckITPC\Documents\AI\sc-w3-ci` (or the paths shown), 2026-09-11. Git status at the end: empty (`.qa-w3b/` is gitignored, `.gitignore:72`).

1. `git rev-parse HEAD origin/main` → both `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git log --oneline -1` → `ed75dc70 Merge pull request #154 …`; `git status --short` → empty; `ls docs/runbooks` → 22 entries incl. `qaren-canary-onboarding.md`; `ls .github/workflows` → `ci.yml live-suite.yml`; `ls docs/ota` → No such file.
2. `git log -1 --format='%H %ci %s' 97b5f15` → `97b5f150… 2026-09-02 01:34:56 +0300 docs(claude-md): M18 load + scoring flags…`; `git merge-base --is-ancestor 97b5f15 origin/main` → yes; `git rev-list --count --first-parent 97b5f15..origin/main` → 33; `--merges` → 28; plain → 141; `git diff --stat 97b5f15 origin/main | tail -1` → `311 files changed, 74875 insertions(+), 2282 deletions(-)`; `--is-ancestor 97b5f15 origin/main~1` → yes; `git log --oneline --first-parent --no-merges 97b5f15..origin/main` → 5 lines (`9b737d7c 76ace902 79a4594a 54ff871b 187155ed`); `git log -1 --format='%h %p' 9a825e41` → parent `a4e7b08b`, and `git rev-list --first-parent origin/main | grep -c 9a825e41` → `0`.
3. `wc -l .github/workflows/ci.yml` → 274; `grep -n` → jobs at 10/113/163/202/248, `on:` 3-7, `continue-on-error: true` at 157 and 199, `actions/checkout@v4` at 13/116/166/205/251 (no `fetch-depth`), setup-node blocks at 173-177/207-211/253-257, `npm ci` at 214/260; `python -c "import yaml; …"` → `['backend-lint', 'backend-tests', 'dependency-audit', 'frontend-tests', 'frontend-typecheck']`.
4. `wc -l docs/runbooks/qaren-canary-onboarding.md` → 375; `git log --oneline -3 -- <file>` → `f3bfb7b1 docs(canary): runbook …` (single commit); `grep -n` → `Last revised` at 5, `--branch production` at 154/158/190/194/369, sections `## 1`-`## 8` at 14/127/174/215/232/302/337/363, zero hits for `expo-upload-sourcemaps|gitCommitHash|update:view|NODE_ENV|skip-bundler`.
5. `grep -n "branch production" CLAUDE.md` → line 495 only; `sed -n 495p CLAUDE.md` quoted in section 2.
6. `grep -n -E "isProduction|isTest|removeConsolePlugin|NODE_ENV|BABEL_ENV" SmartCompareApp/babel.config.js` → 14, 22, 76, 187, 188, 190-193, 196-197, 199; `cat -n SmartCompareApp/eas.json` → 26 lines, `cli.version ">= 18.8.1"` (3), channels 10/15/20; `grep -n … SmartCompareApp/app.json` → `version 1.0.0` (5), Sentry plugin 130-134, `projectId` 140, `runtimeVersion.policy appVersion` 144-145, `updates.url` 148.
7. Pins vs installed (`package.json` line / `node -p require(...).version`): `@sentry/react-native ~7.2.0 / 7.2.0` (22), `expo ~54.0.33 / 54.0.34` (25), `expo-updates ~29.0.17 / 29.0.17` (43), `eslint ^9.39.4 / 9.39.4` (66), `jest ^29.7.0 / 29.7.0` (69), `typescript ~5.9.2 / 5.9.3` (72), `@expo/cli` (not a direct dep) 54.0.24; `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`; `ls -la node_modules` → junction `-> /c/Users/SynAckITPC/Documents/AI/sc-scraper-proof/SmartCompareApp/node_modules`; `@babel/core/package.json` and `.bin/jest` present.
8. `sed -n 1,30p SmartCompareApp/src/services/sentry.ts` → follow-up comment lines 10-16 (sourcemap upload at 13-16).
9. eas-cli: `which eas` → `/c/Users/SynAckITPC/AppData/Roaming/npm/eas`; `package.json` `"version": "18.8.1"`, `engines.node ">=20.0.0"` (247-249). Read and quoted: `build/commands/update/list.js:30-80`, `build/update/queries.js:171-183`, `build/update/utils.js:120-170`, `build/utils/json.js:1-42`, `build/user/SessionManager.js:31,118`, `build/commands/update/view.js:35-80`, `build/commandUtils/flags.js:1-20`, `build/commandUtils/pagination.js:26-39`, `build/vcs/clients/git.js:205-222`, `build/build/utils/repository.js:38-62`, `build/commands/update/index.js` (flags 59-130 incl. `input-dir` default `dist` 73-77, `source-maps` default `'true'` 91-95; `gitCommitHash` 360/394/492-496; `printJsonOnlyOutput` 446-448; `sanitizeFlags` 513-542), `build/project/publish.js:148-212` (`buildBundlesAsync` export args), `:213-218` (`--skip-bundler`), `:669-681` (`getSourceMapExportCommandArgs`), `build/project/expoConfig.js:25-70`, `build/project/projectUtils.js:57-60`, `build/commandUtils/context/contextUtils/findProjectDirAndVerifyProjectSetupAsync.js:10-30` (`applyCliConfigAsync`), and `grep -rln findProjectDirAndVerifyProjectSetupAsync build/commandUtils/context/` → 7 context fields incl. `ProjectIdContextField.js` and `ProjectDirContextField.js`.
10. `@expo/cli` 54.0.24: `build/src/export/exportApp.js:113-119` (NODE_ENV forced), `export/resolveOptions.js:79` (`dev: !!args['--dev']`).
11. `@sentry/react-native` 7.2.0: `ls scripts/` → `expo-upload-sourcemaps.js` present; `package.json:47-49` `bin.sentry-expo-upload-sourcemaps`; script lines 7-10 (env names), 71-95 (asset walk), 123 (`NODE_ENV ||= development`), 137-183 (org/project/url from expo config), 189 (token required), 196 (`dist` example), 200-238 (upload loop, `.map` required per bundle, `--source-maps` warning).
12. Backend toolchain: `python --version` 3.12.9; `python -m pytest --version` 8.2.0; `ruff --version` 0.16.5; `black --version` 26.5.1; pyyaml 6.0.3; `requirements-dev.txt` pins black 26.5.1 (3), pytest 9.1.1 (107), pyyaml 6.0.3 (121), ruff 0.16.5 (136); `pyproject.toml:39-45` markers live_db/integration/live_unit/bench/live_prod; `python -c "import sys; …stdlib_module_names"` → `301 True False` (json in, yaml not in).
13. `tests/test_ci_gates.py`: `grep -n "^def "` → helpers 44/49/56/60/64, the tests named in section 6 at 186/192/206/212/247/267/290/324/346/384/875 (+ live-suite pins 463-900); `sed -n 40,64p`, `186,205p`, `346,383p` read for style. `tests/.pre_impl_failures.txt` → 11 node ids, none in test_ci_gates. `.github/black-clean-paths.txt` → 18 entries incl. `tests/test_ci_gates.py`, `scripts/__init__.py`, `tests/__init__.py`. `.gitignore:72` `.qa-*/`. `grep -n -E "EXPO_TOKEN|CI|GITHUB" tests/conftest.py tests/_env_safety.py` → nothing. `grep -rn "^from scripts|^import scripts" tests/` → 5 files, pattern `from scripts.<mod> import …`.
14. **Base gate run:** `python -m black --check tests/test_ci_gates.py` → "1 file would be left unchanged"; `PYTHONIOENCODING=utf-8 python -m pytest tests/test_ci_gates.py -q -p no:randomly -p no:cacheprovider` → **38 passed, 2 warnings in 13.07s**.
15. Repo grep (excl. node_modules/.git) for `EXPO_TOKEN|check_channel_freshness|expo-upload-sourcemaps` → `.qa-w3b/*` (this unit), `SmartCompareApp/package-lock.json:3828` (`expo-upload-sourcemaps` ×2, the Sentry bin), and the two review JSONs (`expo-upload-sourcemaps` in finding text; `EXPO_TOKEN` count 0 in both). `docs/SESSION_BUNDLES.md` group ids at 36/47/64 (`d540c1e6-…`), 523 (`18af8a48-…`), 545 (`90087c4f-…`), 646 (`ba52fdf9-…`), 721 (`3efa9d81`), "two-launch propagation" at 467; `grep -rn 97b5f15 docs/SESSION_BUNDLES.md docs/CONTEXT_SESSION_LOG.md` → CONTEXT_SESSION_LOG.md:131 records the publish, no group id anywhere. `.claude/skills/qaren-eas-deploy/SKILL.md` 51 lines, runbook pointer at 50. `docs/runbooks/bundle-d-ota-delivery-troubleshooting.md` `--branch preview`/`update:list`/`update:view`/`--clear-cache` at 35, 126-139, 209-266. `SmartCompareApp/metro.config.js:4,15` + `metro.cacheVersion.js` (last commit `8d8b9dc8 fix(mobile): P-B1-CACHE - key Metro transform cache on babel.config.js`).
16. Finding rows: `grep -n` in `docs/investigations/2026-09-06-full-review-tables.md` → 64 (`MB-RECONCILE-06`, `ResultsScreen.tsx:345`), 284 (`-05`, `sentry.ts:15`), 421 (`-19`, checkup doc `:1`), 443 (`-10`, `package.json:23`); W3-13 row in `2026-09-06-full-review.md:140` ("RED today: 6 commits / 72 files behind"); verifier JSON entries for all four ids extracted (the `-10` fix text carries the `babel.config.js:46-52` anchor and the "no NODE_ENV override" reasoning corrected in 3.3; the `-06` test_first carries the `merge-base --is-ancestor … origin/main~<N>` guard idea).
17. context7 `/websites/github_en_actions` (3 queries) and `/actions/checkout` (1 query): the four quotations in section 3.5 and the `fetch-depth` sentence in 3.2 are verbatim from the returned docs.
18. Probe `.qa-w3b/probes/probe_channel_freshness.py` (copy in `scratchpad/b5/W3-13/`; docstring's "three times" corrected to "five lines"), `PYTHONIOENCODING=utf-8 python …`, exit 0, full output:

```
== 1. today's gap, read-only git ==
HEAD          : ed75dc708b82c0b911c9de8a3e59d4418c6e278c
phones (full) : 97b5f1501a1242c405fd3cf12bee9ab419db2bdd
phones is ancestor of origin/main : True
first-parent commits behind       : 33
merge commits behind              : 28
all commits behind                : 141
diff --stat tail                  :  311 files changed, 74875 insertions(+), 2282 deletions(-)
phones is ancestor of origin/main~1 (=> >1 behind): True

== 2. absence ==
ci.yml contains 'preview'     : False
ci.yml contains 'EXPO_TOKEN'  : False
ci.yml contains 'eas '        : False
ci.yml contains 'channel'     : False
ci.yml contains 'fetch-depth' : False
scripts/check_channel_freshness.py exists: False
tests/test_channel_freshness.py exists  : False
runbook lines with '--branch production': [154, 158, 190, 194, 369]
runbook mentions expo-upload-sourcemaps  : False
runbook mentions gitCommitHash           : False
runbook mentions update:view             : False
runbook mentions NODE_ENV                : False

== 3. prototype decision function over fake payloads ==
1  today (3 behind in this fake)        -> preview runs 97b5f150, 3 first-parent commits behind main (max 1)
2  null hash dropped by sanitizeValue   -> gitCommitHash unresolvable from update:view (got [])
2  empty page                           -> no update groups on the branch
4  rollback group                       -> group 11111111-2222-3333-4444-555555555555 is a roll-back-to-embedded — phones run the binary's bundle
3  published from a side branch         -> sidesha is not an ancestor of main
2  unknown sha                          -> deadbeef is not in this checkout's history (dirty-tree or fork publish?)
0  one behind (fresh)                   -> preview runs m4, 1 behind main
0  at head (fresh)                      -> preview runs m5, 0 behind main

REAL ancestry, phones' recorded hash: 1 preview runs 97b5f150, 33 first-parent commits behind main (max 1)
```

Not run, and why: any `eas …` command (network to EAS — forbidden in this batch); jest / eslint (no client file is touched); the full pytest suite (green phase's job).

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS**. Every file:line anchor in sections 2-10 was re-located and every library claim re-read on the installed version (eas-cli 18.8.1 global, `@expo/cli` 54.0.24, `@sentry/react-native` 7.2.0, Python 3.12.9 / pytest 8.2.0 / black 26.5.1 / ruff 0.16.5 / pyyaml 6.0.3) on 2026-09-11; the probe re-ran exit 0; the base gate re-ran (`black --check tests/test_ci_gates.py` → unchanged; `pytest tests/test_ci_gates.py` → 38 passed). The rulings below are the ONLY corrections; where a ruling contradicts an earlier section, the ruling wins. The red phase reads this file once.

1. **Base drift — `origin/main` moved after the spec was written.** Measured: `git rev-parse HEAD origin/main` → HEAD `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`, origin/main **`aac79f786f20acc972f2aa2ab2190deedf941d33`** (branch `feature/s65-w3-13-channel-freshness`). `git log --oneline --first-parent ed75dc70..origin/main` → one merge, `aac79f78 Merge pull request #155 … feature/s65-w3-2-comparison-id-echo`; `git diff --name-only` → `app/api/text_routes.py`, `app/services/feedback_service.py`, `tests/test_comparison_id_echo.py` — **none of this unit's six files**, so every anchor in section 4 survives a later rebase. Live-main gap is now **34 first-parent / 29 merges / 143 commits / 313 files (+76,591/−2,346)**; the probe's REAL-ancestry line now prints `34 first-parent commits behind main`. Rulings: (a) the red/green phases work at HEAD `ed75dc70` and do NOT fetch, rebase or merge; (b) every number in the ci.yml comment, the runbook ledger and the PR body is written as "measured 2026-09-11 at ed75dc70: 33 first-parent commits / 311 files" — a dated measurement, never a live claim; (c) **no test asserts 33, 34, or any real distance** — test 4 runs only over `FakeAncestry`, and test 5 only over the monkeypatched `subprocess.run`; (d) the merger may refresh the comment's numbers at merge time, the red/green phases may not.

2. **REFUTED: "non-interactive `eas update` on a dirty tree throws `Commit all changes. Aborting...`" (section 3.4 last bullet, runbook block in 4.4 lines 304-306, section 8 item 2(d), section 9 bullet).** `commands/update/index.js:143` does call `ensureRepoIsCleanAsync(vcsClient, nonInteractive)`, but that function returns immediately unless `vcsClient.isCommitRequiredAsync()` is true (`build/build/utils/repository.js:41-44`), and `vcs/clients/git.js:109-113` is `if (!this.requireCommit) return false;`. `requireCommit` comes from `resolveVcsClient(requireCommit = false)` (`build/vcs/index.js:10,24`) i.e. `eas.json` `cli.requireCommit`, and **`SmartCompareApp/eas.json` has 0 occurrences of `requireCommit`** (measured). So `eas update` neither aborts nor prompts on a dirty tree; it records `git rev-parse HEAD` as `gitCommitHash` and sends `isGitWorkingTreeDirty` to the server (`index.js:360-361`, `:394-395`), and the `*` marker is rendered ONLY in the human table (`:492-496`) — `getUpdateJsonInfosForUpdates` (`update/utils.js:129-142`, used by both `eas update --json` and `update:view --json`) carries no dirty flag. CLAUDE.md's own "EAS Update infrastructure" block records exactly this (`<sha>*` on an OTA that DID fire). Consequences, binding: (a) rewrite the runbook 2.0 comment on the `git status --porcelain` line to: *"MUST be empty. `eas update` will NOT stop you: eas.json sets no `cli.requireCommit`, so eas-cli publishes a dirty tree, records HEAD's hash as `gitCommitHash`, and the only trace is a `*` in the human output — the JSON and the CI guard cannot see it."*; (b) delete section 8 item 2(d)'s inference "a dirty-tree publish would carry a different hash → exit 2" — a dirty publish carries HEAD's hash and reads FRESH/STALE like any other; the guard is blind to dirtiness by construction and the runbook says so; (c) the script's UNRESOLVABLE message for an unknown hash must not say "dirty-tree": use `f"{sha[:8]} is not in this checkout's history (published from an unpushed branch, a fork, or read from a shallow clone?)"`; adapt the probe-derived expectation in test 4 accordingly; (d) the PR-body bullet about the hash "only describing the bundle when the tree was clean" is replaced by the sentence in (a).

3. **"currentPage[0] is the newest group" is eas-cli's own assumption, not only ours — cite it.** `build/update/queries.js:100-120` (`selectRuntimeAndGetLatestUpdateGroupForEachPublishPlatformOnBranchAsync`) fetches the "latest" group per platform with `limit: 1, offset: 0` through the same `queryUpdateGroupsOnBranchAsync`; `build/update/utils.js:170` reads `const latestUpdate = branch.updates[0]`; `build/project/publish.js:433` labels `updates[0]` "current update". Ruling: the ci.yml comment's "WHY TWO eas COMMANDS" block and section 8 item 2(a) cite these three lines as the basis for `--limit 1` + index 0; the first armed run still confirms it (the script prints the view JSON's `createdAt`). This is evidence, not proof — keep the sentence "confirmed on the first armed run".

4. **JSON loaders must tolerate a non-JSON preface.** `list.js:41-50`: `getContextAsync` (login + project-id resolution, which spawns `npx expo config --json`) runs BEFORE `enableJsonOutput()` redirects stdout, so anything eas-cli logs during context resolution lands in the redirected file ahead of the JSON. Measured: the only pre-redirect emitters found are `Log.warn` on the misconfigured-project path (`getProjectIdAsync.js:34-41,107` — not our case, `app.json:140` carries the id) and no "is now available" emitter exists under `build/`; the ORDER is nonetheless a fact of the installed source. Ruling: `scripts/check_channel_freshness.py` exposes `load_json_document(text: str) -> object` that decodes from the first line whose stripped text starts with `{` or `[` (raising `ChannelError` if none), and BOTH `--list-json`/`--view-json` go through it; the resolve step's inline `python -c` one-liner uses the same rule (inline: `t=open(p,encoding='utf-8').read(); i=min(x for x in (t.find('{'),t.find('[')) if x>=0)` → `json.loads(t[i:])`). Add **test 1b `test_load_json_document_skips_a_chatter_preface`**: two chatter lines then the list JSON → parses to the same dict; garbage-only → `ChannelError`. RED: module missing. Mutation: plain `json.loads`.

5. **Test 7 interface — pin one hook, no class-attribute monkeypatching.** `main(argv: list[str] | None = None, *, ancestry_factory: Callable[[Path, str], Ancestry] = GitAncestry) -> int`; `GitAncestry.__init__(self, repo: Path, main_ref: str)`. `main()` catches `ChannelError` (empty page, no JSON, unreadable file, git failure) and returns `UNRESOLVABLE` with the `::warning::` prefix. Test 7 is parametrized so that exit 2 is exercised by BOTH the empty-page list fixture AND the no-hash view fixture (two cases, one assertion shape). Exit-code contract unchanged (0/1/2/3/4).

6. **`subprocess.run` contract (Windows codec rule in CLAUDE.md "Tests").** Every git call is `subprocess.run(argv, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", check=False)`. Test 5 asserts the recorded `argv` lists exactly as section 5 states and `Path(kwargs["cwd"]) == repo` (accept str or Path); it does not assert other kwargs. A non-zero `rev-list --count` (unknown ref) raises `ChannelError` → exit 2; `cat-file -e` / `merge-base --is-ancestor` use the return code as the boolean.

7. **Stdlib pin detail.** `'__future__' in sys.stdlib_module_names` → `True` on 3.12.9 (measured), so `from __future__ import annotations` is permitted in the script; `json/os/sys/argparse/subprocess/pathlib/dataclasses/typing` all measured present. Test 6 unchanged.

8. **Runbook insertion points, made unambiguous.** Section 2's H2 is line 127 and its intro paragraph is 129-131; the first subsection is `### 2.1 Bump 10 → 50` at **line 133**. Ruling: "2.0 Publish procedure" is inserted immediately BEFORE `### 2.1` (after the intro paragraph), not "between 127 and 128". "9. OTA ledger" is appended after the section-8 table (after line 375). The five `--branch production` sites re-measured at 154/158/190/194/369 with the exact text quoted in section 3.3; replace the flag only, keep each line's `--message`.

9. **Ledger seed is grep-derived, not hand-listed — the hand list is wrong twice.** `grep -n -o -E '<uuid-regex>' docs/SESSION_BUNDLES.md` → `:47 d540c1e6-c07c-46d7-ac69-5103dde1fb56` (line 64 has the short form `d540c1e6-...`; **line 36 does NOT carry it** — spec's "36/47/64" corrected), **`:89 1856c8fb-70ea-4333-b402-b09ad7f2af5f` (an EAS update group the spec's list OMITS — include it)**, `:523 18af8a48-a191-4b5d-bc62-9508ab4b5952`, `:545 90087c4f-ee62-4e4c-84e7-d0c17a62276f`, `:646 ba52fdf9-e5c1-41cd-9bd4-cb5a71c183d7`, plus short `3efa9d81` at `:721`. **EXCLUDE `4aee8e88-da97-41b3-974b-3e75c2c9c10e` (:636) and `54b603e8-4eab-41c9-a34d-a5e391446559` (:752/771/783) — those are eval-runner baseline run ids, not EAS groups.** Ledger rows carry `gitCommitHash: (not recorded)` unless the source line states the commit (Bundle E `0129106` at :47 is the only one); the Wave-3 `2cb4439` at :721 is the BACKEND commit — put it in `notes`, never in `gitCommitHash`. The 2026-09-02 `97b5f15` row is seeded from `docs/CONTEXT_SESSION_LOG.md:131` (re-measured; no group id anywhere, `grep -c 97b5f15 docs/SESSION_BUNDLES.md` → 0).

10. **`npx eas-cli@18.8.1 <cmd>` resolution, verified.** eas-cli `package.json:19-21` `"bin": {"eas": "./bin/run"}` — a single bin entry, which is what lets `npx <pkg>@<ver>` run it under a different command name; `eas-cli` is NOT in `SmartCompareApp/package.json` (0 hits), so `ensureEasCliIsNotInDependenciesAsync` stays quiet and no local copy shadows the pin. `getLimitFlagWithCustomValues({defaultTo: 25, limit: 50})` → `--limit 1` valid (`pagination.js:20-31`). `--json` implies non-interactive (`flags.js:12-14`, `resolveNonInteractiveAndJsonFlags`). Record these in the ci.yml comment in one line.

11. **Secrets/`if` design — docs re-read via context7 2026-09-11 and confirmed verbatim** ("Secrets cannot be directly referenced in if conditionals. To use secrets for conditional logic, set them as job-level environment variables first…"; the "Run a step if a secret has been set" YAML; the context-availability sentence; step-level `env` guidance). The boolean composition `EXPO_TOKEN_SET: ${{ secrets.EXPO_TOKEN != '' }}` remains undocumented as a whole. Ruling: keep the design AND write the fallback INTO the ci.yml comment (not only this spec): *"If the first armed run shows the skip step running despite the secret (or the resolve step running without it), replace this job-level boolean with the documented verbatim form (`EXPO_TOKEN: ${{ secrets.EXPO_TOKEN }}` at job env, steps gated on `env.EXPO_TOKEN != ''`) and delete the token-scoping assertion in tests/test_ci_gates.py in the same PR."* Test 8 is unchanged.

12. **Message assertions in tests 4 and 7 — pin the contract, not the prose.** Assert the exit/verdict code first; for STALE assert the substring `"first-parent commits behind main (max 1)"`; for UNRESOLVABLE/NOT_ON_MAIN/ROLLBACK assert only the code and that the message is non-empty; for FRESH assert the code only. Test 7 asserts the `::error::` / `::warning::` prefix and the absence of any `::` prefix on FRESH.

13. **Decoration and tautology audit — passed with the additions above.** Test 8 reads the eas.json range from disk (cross-file, not the fix's constant); test 10 cross-pins CLAUDE.md:495 (re-measured: line 495 is the only `--branch production` hit and contains `` never `--branch production` ``); test 9 reads the raw comment text; every test names a mutation. New test 1b (ruling 4) names its mutation. Nothing in scope beyond the plan; nothing already-green was kept (ci.yml still five jobs; script/test absent; runbook 5 production lines, 0 sourcemap/update:view/gitCommitHash hits — all re-measured).

14. **Hazard sweep (the campaign's list).** No OTA-gated client change, no backend behaviour, no flag, no migration, no package/lockfile change — confirmed by section 4.1's file list. Hidden dependencies are exactly the two the spec names and they are POST-merge (EXPO_TOKEN repo secret; SENTRY_AUTH_TOKEN local). The console-strip premise correction (`@expo/cli` `exportApp.js:116-118` forces `NODE_ENV`; `resolveOptions.js:79` `dev: !!args['--dev']`) re-read and holds; `--source-maps` default (`update/index.js` flag default `'true'`, hidden) and `getSourceMapExportCommandArgs` (`publish.js:669-681`, `['--source-maps']` for SDK < 55) re-read and hold; the Sentry script's env names (`:7-10`), `NODE_ENV ||= development` (`:123`), org/project/url resolution from the expo plugin block (`:137-182`), token requirement (`:189-190`), example invocation (`:196`), `.map` requirement (`:206`) and the `--source-maps` warning (`:237`) all re-read on 7.2.0 and hold. Two documents disagree on one number: CLAUDE.md:189 `@sentry/react-native@8.11.1` vs pin `~7.2.0`/installed 7.2.0 — recorded in the PR body, CLAUDE.md untouched (scope).

15. **Runtime/cost note for the PR body (not a design change).** The armed path downloads eas-cli via `npx --yes` on every run (no caching) plus `npm ci`; if the job's wall-time is judged too heavy after a week of readings, the fetcher swap in section 4.2 stands. Not a red/green concern.

16. **Reviewer's evidence trail.** Probe re-run output: `scratchpad/b5/W3-13/review/review_probe_out.txt` (exit 0; block 1 now shows 34/29/143/313 per ruling 1). No file outside `.qa-w3b/` and that scratch directory was written; `git status --short` empty at the end of the review.

## FABLE REVIEW RULINGS — SECOND PASS (binding, 2026-09-11 12:0x, supersedes pass 1 where they conflict)

Context the first pass could not have: this review ran AFTER the red phase. At review time
`git status --short` in `sc-w3-ci` showed ` M tests/test_ci_gates.py` (+198 lines) and
`?? tests/test_channel_freshness.py` (445 lines), both written 2026-09-11 11:04, and the
worktree branch `feature/s65-w3-13-channel-freshness` is at **`b63a8368`**, not `ed75dc70`.
Measured red state (`PYTHONIOENCODING=utf-8 python -m pytest tests/test_ci_gates.py -q -p
no:randomly -p no:cacheprovider`): **3 failed, 38 passed, 35.16 s** — the 38 pre-existing pins
still green with the append, and the three new ones red for the right reasons. Run together with
the new unit file the invocation aborts at collection:
`ModuleNotFoundError: No module named 'scripts.check_channel_freshness'` (pytest exit 2, no other
test runs) — that is the correct red, but it means the two files cannot be measured in ONE
invocation until the script exists. Verdict: **APPROVED_WITH_RULINGS**. Rulings 17-27 are binding
and win over anything earlier in this file, pass-1 rulings included.

17. **BASE MOVED AGAIN — the base is `b63a8368`, and pass-1 ruling 1(a) ("work at HEAD
    `ed75dc70`") is VOID.** Measured: `git rev-parse HEAD origin/main` -> both
    `b63a8368b7910a946020438a5447bbcd6b792805`; `git log --oneline --first-parent
    ed75dc70..b63a8368` -> five merges (`aac79f78` #155 W3-2, `5ad0f7dc` #156 W1-5, `d32f2983`
    #158 W4-5, `be5267cf` #157 W1-6, `b63a8368` #159). **`git diff --stat ed75dc70..b63a8368 --
    .github/workflows/ci.yml tests/test_ci_gates.py docs/runbooks/ CLAUDE.md
    .github/black-clean-paths.txt scripts/` -> EMPTY**: not one of this unit's six files moved,
    so every anchor in sections 2-10 survives verbatim. Re-measured at `b63a8368` and ALL HOLD:
    ci.yml 274 lines / jobs exactly `['backend-lint','backend-tests','dependency-audit',
    'frontend-tests','frontend-typecheck']` / checkout@v4 at 13,116,166,205,251 with no
    `fetch-depth` / `continue-on-error: true` at 157 and 199 only / `npm ci` at 214,260 / file
    ends CRLF (13956 bytes, last two bytes 13,10 — the append starts on a fresh line);
    runbook 375 lines with `--branch production` at 154,158,190,194,369 and ZERO hits for
    `expo-upload-sourcemaps`, `gitCommitHash`, `update:view`, `NODE_ENV`, `skip-bundler`,
    `branch preview`; `Last revised` at line 5; `## 2.` at 127 and `### 2.1` at 133;
    CLAUDE.md's `never --branch production` is at line **495** (still the only
    `branch production` hit in that file); `tests/test_ci_gates.py` helpers `_load/_triggers/
    _steps/_run_text/_allowlist_entries` at 44/49/56/60/64 with `re` and `yaml` already imported
    and `REPO_ROOT`/`CI_YML`/`BLACK_ALLOWLIST` already defined; `.github/black-clean-paths.txt`
    18 entries, ratchet rule at line 17; `scripts/__init__.py` and `tests/__init__.py` present
    (0 bytes); `tests/.pre_impl_failures.txt` 89 lines = **11 node ids**, none in
    `test_ci_gates` (the single `ci_gates` hit at line 67 is a comment). **Live gap at
    `b63a8368`: 38 first-parent / 33 merges / 151 commits / 318 files (+78,643/-2,354), same 5
    direct pushes.** Rulings: (a) the base is `b63a8368`; do NOT fetch, rebase or merge; (b)
    pass-1 ruling 1(b)-(d) stand unchanged — every number written into ci.yml, the runbook and
    the PR body is a DATED measurement ("measured 2026-09-11 at ed75dc70: 33 first-parent
    commits / 311 files"), and **no test asserts any real distance**; the already-written unit
    file honours this.

18. **BLOCKING CONTRADICTION — test 10 forbids the runbook from naming the hazard the spec tells
    it to name.** Section 5 test 10 (and the file already on disk, `tests/test_ci_gates.py`
    `test_canary_runbook_publishes_to_the_channel_with_devices`) asserts
    `[i for i,ln in enumerate(text.splitlines(),1) if "--branch production" in ln] == []`, i.e.
    **zero occurrences of the substring anywhere in the runbook**. Section 4.4 item 1 orders each
    replaced line to carry the reason *"... `--branch production` reaches zero phones"*, and
    section 4.4 item 2's publish block carries *"NEVER --branch production (zero devices)"*.
    Both prescribed strings contain the forbidden substring: **the spec's own runbook text
    cannot pass the spec's own test.** Measured today the assertion reddens with
    `[154, 158, 190, 194, 369]`. Binding ruling: amend test 10 (a red-phase touch-up, not a
    green-phase workaround) to scan for the COMMAND, not the flag name —
    `re.findall(r"eas\s+update(?::list)?\s+--branch\s+production", text)` must be empty (RED
    today: all five measured lines match; the form at line 369 is inside a markdown table cell
    and still matches) — and ADD a positive pin that the prose warning survives:
    `"--branch production" in text` must be TRUE, because a runbook that silently stops
    mentioning the trap has lost the finding. Keep every other needle in test 10 unchanged.
    Without this amendment the green phase must either delete the warning prose or fail the
    gate, and the second reviewer would be told the first choice was "what the spec said".

19. **TAUTOLOGY — the exit-code contract 0/1/2/3/4 is quoted in four places and pinned nowhere.**
    Section 4.3, the module docstring, the ci.yml comment, the PR body and section 8 all state
    "0 fresh, 1 stale, 2 unresolvable, 3 not-on-main, 4 rollback", but tests 4 and 7 compare
    against the fix's OWN imported constants (`assert code == expected_code` where
    `expected_code` is `STALE`, and `assert rc == expected_code` likewise). A green agent that
    writes `FRESH, STALE, UNRESOLVABLE, NOT_ON_MAIN, ROLLBACK = 0, 7, 9, 3, 4` keeps every test
    green while every document is wrong. Binding: add one assertion, in `tests/test_channel_freshness.py`,
    `def test_exit_codes_are_the_documented_contract(): assert (FRESH, STALE, UNRESOLVABLE,
    NOT_ON_MAIN, ROLLBACK) == (0, 1, 2, 3, 4)` with a docstring naming the four documents that
    quote it. RED today (module missing). Mutation: any renumbering.

20. **`eas update:view` has NO `--non-interactive` flag — adding one is a hard failure, not a
    no-op.** Measured on the installed eas-cli 18.8.1: `build/commands/update/view.js:41`
    spreads `...flags_1.EasJsonOnlyFlag`, and `build/commandUtils/flags.js:70-74`
    `EasJsonOnlyFlag = { json: Flags.boolean(...) }` — one key. `update:list` by contrast
    spreads `EasNonInteractiveAndJsonFlags` (`flags.js:11-20`), which is where
    `--non-interactive` lives. Test 8 asserts `"--non-interactive" in run` over the WHOLE
    resolve step's run text, which the `update:list` line already satisfies, so a green agent
    "tidying for symmetry" can add it to the `update:view` line and turn the armed job into an
    oclif nonexistent-flag error that no test can see. Binding: the `update:view` invocation is
    exactly `npx --yes eas-cli@18.8.1 update:view "$GROUP" --json` and the ci.yml comment says
    why. Belt and braces, measured: `isNonInteractiveByDefault()` is
    `boolish('CI', false) || !process.stdin.isTTY` (`flags.js:8-10`) and Actions sets `CI=true`,
    and `--json` implies non-interactive (`flags.js:21-25` `resolveNonInteractiveAndJsonFlags`,
    `nonInteractive = flags['non-interactive'] || json`) — so nothing is lost.

21. **The skip notice must print the OBSERVED value, or the one failure mode this design admits
    is indistinguishable from success.** The job-level `EXPO_TOKEN_SET: ${{ secrets.EXPO_TOKEN
    != '' }}` is, as the spec concedes, a composition of two documented facts rather than a
    documented example (re-confirmed verbatim via context7 2026-09-11: the "Run a step if a
    secret has been set" YAML maps the RAW secret at job level; the contexts reference gives
    job-level keys `github, needs, strategy, matrix, vars, inputs` and step-level keys
    additionally `job, runner, env, secrets, steps`; `jobs.<job_id>.env` is documented as
    accepting `${{ }}` expressions including `secrets`). The two step conditions
    (`== 'true'` / `!= 'true'`) are complementary and exhaustive, so the job ALWAYS runs a branch
    and always exits green — it fails safe. But if the boolean ever renders as anything other
    than `true`, the job takes the skip branch and prints *"Add the EXPO_TOKEN repository
    secret"* — which, with the secret already added, is a LIE that reads as normal, and the
    guard measures nothing forever. Binding: the negative step's run is
    `echo "::notice title=channel-freshness skipped::EXPO_TOKEN_SET='${{ env.EXPO_TOKEN_SET }}'
    — add the EXPO_TOKEN repository secret to arm the preview-channel freshness guard; if the
    secret IS set, this value did not evaluate and the job needs the fallback form in the
    comment above."` Test 8's existing `"::notice" in run` assertion is unaffected.

22. **DESIGN HAZARD the plan carries and nobody has written down: making this blocking blocks
    every PR on an action only Ahmed can take.** Measured: `ci.yml:3-7` triggers on
    `pull_request: branches: [main]` AND `push: branches: [main]`, so the job runs on every PR.
    Its verdict is a property of the CHANNEL, not of the PR — and merging anything to main makes
    it worse, while the only cure (`eas update`, interactive `eas login`) is outside CI. On
    2026-09-18, per section 4.2 and Ahmed dependency 3, `continue-on-error` is deleted and the
    job is added to branch protection: from that moment **no contributor can merge anything
    until an OTA is published**, including the PR that would fix an outage. That is a
    self-inflicted merge freeze, and it is exactly the class of failure this campaign keeps
    recording. Binding: (a) the job's leading ci.yml comment carries this paragraph verbatim as
    a FLIP PRECONDITION, not as a footnote; (b) the flip PR must, in the same change, either add
    `if: github.event_name == 'push'` at job level (the `github` context IS available in a
    job-level `if` per the contexts reference; it is compatible with every assertion in test 8,
    which inspects only `job["env"]` and the step list, and it also removes the per-PR `npm ci`
    + two `npx` downloads) or land an equivalent documented break-glass; (c) the flip is
    additionally conditional on the OTA having landed, so the first blocking run is green.
    Nothing changes in THIS unit's code — the job keeps both triggers while it is non-blocking,
    because a per-PR reading is free data and harmless.

23. **`continue-on-error` is not banned here — read the neighbouring comment's scope before
    copying it.** `ci.yml:246-247` says *"Tighten it later with `--max-warnings=N` ratcheted
    downward, the way `.github/black-clean-paths.txt` works — do NOT re-add continue-on-error to
    do it."* Measured in context (`ci.yml:225-247`): that sentence is about draining the
    `frontend-tests` ESLint WARNING backlog on an already-green check. The same block records
    that `frontend-tests` itself *"landed non-blocking with continue-on-error on each check step,
    purely to MEASURE a red count that could not be read locally"* and was ratcheted to blocking
    once measured — which is precisely this unit's device. Binding: the new job's comment cites
    `ci.yml:232-241` as the precedent by name, so the next reader does not mistake the
    `--max-warnings` sentence for a repo-wide prohibition and delete the line.

24. **Claims re-verified on the installed source at `b63a8368` — all HOLD, with citations
    tightened.** eas-cli `package.json` `"version": "18.8.1"`, `engines.node ">=20.0.0"`,
    `"bin": {"eas": "./bin/run"}` (single bin, so `npx --yes eas-cli@18.8.1 <cmd>` resolves).
    `update/queries.js:171-183` emits `{...branch, currentPage: updateGroupDescriptions}` under
    `--json`; `update/utils.js:154-165` `getUpdateGroupDescriptionsWithBranch` emits exactly
    `branch, message, runtimeVersion, isRollBackToEmbedded, rolloutPercentage, codeSigningKey,
    group, platforms` — **no `gitCommitHash`, no `createdAt`**, confirmed by reading the object
    literal; `update/utils.js:129-142` `getUpdateJsonInfosForUpdates` (what `update:view --json`
    prints, `view.js:74`) emits `id, createdAt, group, branch, message, runtimeVersion,
    platform, manifestPermalink, isRollBackToEmbedded, gitCommitHash` as a LIST, one entry per
    platform. `utils/json.js:26-42` `sanitizeValue` drops every key whose value is `null` (and
    `__typename`) — an unhashed publish has no key at all. `json.js:9-15` `enableJsonOutput`
    rebinds `process.stdout.write` to stderr, and BOTH commands call `getContextAsync` BEFORE
    it (`list.js:45-47` then `:51-53`; `view.js:51` then `:53-55`) — pass-1 ruling 4's
    chatter-tolerant loader stands. `pagination.js:26-31` + `list.js:34`
    `getLimitFlagWithCustomValues({defaultTo: 25, limit: 50})` -> `--limit 1` valid.
    `update/utils.js:170` `const latestUpdate = branch.updates[0]` — pass-1 ruling 3's
    index-0 citation holds. **Dirty-tree refutation (pass-1 ruling 2) RE-PROVEN:**
    `build/utils/repository.js:41-44` returns early unless `isCommitRequiredAsync()`;
    `vcs/clients/git.js:109-112` is `if (!this.requireCommit) return false;`;
    `vcs/index.js:10,24` `resolveVcsClient(requireCommit = false)`; `grep -c requireCommit
    SmartCompareApp/eas.json` -> **0**. `commands/update/index.js:73-77` `input-dir` default
    `'dist'`, `:91-95` `source-maps` default `'true'` (hidden); `project/publish.js:218`
    `--skip-bundler requires the project to be exported manually`; `:669-681`
    `getSourceMapExportCommandArgs` (SDK < 55 path). `@expo/cli` **54.0.24**
    `build/src/export/exportApp.js:116-119` *"Force the environment during export and do not
    allow overriding it"* with `dev` from `export/resolveOptions.js:79` `dev: !!args['--dev']`.
    `@sentry/react-native` **7.2.0**, `bin: {"sentry-expo-upload-sourcemaps":
    "scripts/expo-upload-sourcemaps.js"}`, the file exists, `:189-190` requires the token,
    `:196-197` takes the output dir as `process.argv[2]` and prints the example
    `node node_modules/@sentry/react-native/scripts/expo-upload-sourcemaps dist` — the runbook's
    line is that example verbatim, and `cd SmartCompareApp` in section 4.4 makes `dist` resolve.
    `SmartCompareApp/eas.json` is plain JSON with `"cli": {"version": ">= 18.8.1"}` (note the
    space; the already-written test's `re.fullmatch(r">=\s*(\d+)\.(\d+)\.(\d+)", rng)` handles
    it) and binds `build.preview.channel: "preview"` / `build.production.channel: "production"`.
    `actions/checkout` `fetch-depth: 0` -> `getRefSpecForAllHistory` returns
    `['+refs/heads/*:refs/remotes/origin/*', '+refs/tags/*:refs/tags/*']` (context7
    `/actions/checkout` API reference, 2026-09-11), so **`origin/main` exists on both triggers**
    — the one fact the whole guard rests on, previously supported only by the README's
    "all history for all branches and tags" sentence.

25. **Toolchain and gate, re-measured at `b63a8368`.** Python 3.12.9; pytest **8.2.0** local vs
    `requirements-dev.txt` pin 9.1.1 (nothing here is version-specific); black 26.5.1 (= pin);
    ruff 0.16.5 (= pin); `sys.stdlib_module_names` 301 names — `json` in, `yaml` NOT in,
    `__future__` in, and `os/argparse/subprocess/pathlib/dataclasses/typing/ast` all in.
    `python -m black --check tests/test_channel_freshness.py tests/test_ci_gates.py` ->
    **"2 files would be left unchanged"** (black prints a "Python 3.12 cannot parse code
    formatted for Python 3.15" safety-check warning on this box; the verdict is still clean, and
    CI runs the pinned black on the allowlist). `python -m ruff check --select E9,F63,F7,F82`
    on both -> "All checks passed!". Section 7's gate line
    `python -m pytest tests/test_channel_freshness.py tests/test_ci_gates.py ...` is CORRECT for
    green but ABORTS AT COLLECTION while red (exit 2, 0 tests run) — the red phase measures the
    two files SEPARATELY and says so.

26. **Decoration / hazard sweep, second pass.** (a) Every red test named in section 5 is red
    today for the right reason — measured: 3 failed / 38 passed on `tests/test_ci_gates.py`
    (the runbook test on the 5 measured lines, the two job tests on
    `AssertionError: no channel-freshness job; jobs = [...]` via the `_channel_freshness_job`
    helper), and `tests/test_channel_freshness.py` on `ModuleNotFoundError:
    scripts.check_channel_freshness`. (b) Mutations are named on every test; ruling 19 adds the
    one missing pin. (c) Non-tautology cross-file pins confirmed: test 8 reads `cli.version`
    from `SmartCompareApp/eas.json` on disk, test 9 reads the raw ci.yml comment text, test 10
    cross-pins `CLAUDE.md`. (d) Campaign hazard list: no client file, no backend behaviour, no
    flag, no migration, no package.json/lockfile change, no native change — nothing reaches a
    phone on `97b5f15`, a backend process, or Railway; `SmartCompareApp/node_modules` was read
    only (junction intact, `@sentry/react-native` and `@expo/cli` resolved through it). The two
    hidden dependencies are named and both POST-merge (`EXPO_TOKEN` repo secret; local
    `SENTRY_AUTH_TOKEN`). (e) Two documents disagree on one number and it is recorded, not
    fixed: CLAUDE.md's `@sentry/react-native@8.11.1` vs pin `~7.2.0` / installed 7.2.0. (f) The
    four findings are real and still in the tables at `b63a8368`: `MB-RECONCILE-06`
    (tables.md:64), `MB-TWO-LEVER-RELEASE-05` (:284), `MB-RECONCILE-19` (:421),
    `MB-TWO-LEVER-RELEASE-10` (:443); the W3-13 row is `full-review.md:140` and still carries
    the stale "6 commits / 72 files".

27. **Process note the merger must see, not a code ruling.** This review ran after the red phase
    had already written its files, so `git status --short` in `sc-w3-ci` is NOT clean and the
    reviewer deliberately left it that way: ` M tests/test_ci_gates.py`,
    `?? tests/test_channel_freshness.py` (11:04, 2026-09-11). The reviewer wrote nothing outside
    this gitignored `.qa-w3b/` file and
    `scratchpad/b5/W3-13/review/`. Rulings 18 and 19 require edits to files the red phase has
    already produced — apply them as a red touch-up (confirm each still reddens) BEFORE any
    implementation, not as a green-phase amendment, or the green phase will be choosing between
    the spec and the tests.

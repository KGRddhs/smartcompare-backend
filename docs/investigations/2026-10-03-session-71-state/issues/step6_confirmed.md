=== TITLE: Pre-commit hook: staged files git treats as binary (NUL byte, UTF-16, -diff/binary attribute, textconv) skip every secret scan
=== LABELS: security
## Context
The pre-commit hook (`.githooks/pre-commit`, hardened in PR #312, T0b Phase A) scans staged content at three places, and each reads `git diff --cached ... -U0`:
- line 150, the four-branch sk-/AKIA/xox/private-key check;
- line 171, check 4a (JWT and credentialed URL);
- line 323, check 4b (the .env value pass).

None of these calls passes `--text` or `--no-textconv`. For a file git treats as binary, the diff prints only `Binary files ... differ` and emits no added lines, so no branch ever sees the content.

The repository is public, so a commit is a disclosure. Phase B's planned gitleaks layer does not close this gap either; see the measurements below.

Severity: medium. The two verifiers split medium and low. This is not a regression: line 150 has had the gap since 2026-08-30, and 4a/4b inherit it. The hook can be bypassed with `--no-verify`. The likelihood is low but realistic on this Windows box, where tools may write UTF-16.

## Failure scenario
A developer or agent stages a file that holds the root .env value of a credential, a JWT, an AWS access key or a credentialed URL, in any of these forms:
- a dump containing one NUL byte;
- a file a Windows tool wrote as UTF-16LE;
- a path under a `-diff` or `binary` gitattribute;
- a path with a `diff.<drv>.textconv` driver.

The hook exits 0 and the secret is committed. The same content as plain text is refused.

## Measurement
Scratch repos, FAKE values built at runtime, real `git commit` through an LF copy of the #312 hook (sc-s71-t0b @ 62bebafb):
- **Refused (text controls):** a .env value, a JWT, an AKIA key, a credentialed URL.
- **Committed, with the FAKE value present in the blob:**
  - a NUL byte plus each of the four shapes (numstat `-<TAB>-`);
  - `*.json -diff` plus a .env value;
  - `*.json binary` plus an AKIA key;
  - UTF-16LE with a BOM (.env value, AKIA) and without one (JWT);
  - a textconv=true driver plus a .env value.
- **Partial fix tried (reviewer copy with `--text --no-textconv` on 4a and 4b):** the NUL, `-diff` and textconv cases are refused; UTF-16 still commits.
- **The textconv case** shows as text in `numstat --no-textconv`, so a numstat-based refusal alone does not cover it.
- **gitleaks 8.30.1:** catches the text control (rc=1). It returns rc=0 on NUL+AKIA, NUL+JWT, UTF-16+AKIA and `binary`+AKIA, both with `--pre-commit --staged` and in log mode.
- **Docs:** neither the T0b spec, nor rulings TR1-TR10/TF1-TF8, nor the PR #312 stated limits mention binary, NUL, UTF-16, gitattributes or textconv.

Probes: scratchpad `step6/review-security/hook_probe.py`, `step6/verify/SEC-1-reproduce/probe.py`, `step6/verify/sec1_probe.py`.

## Fix
1. **Now (needs an orchestrator ruling; fits in #312):**
   - Append `--text --no-textconv` AFTER `-U0` in the 4a and 4b `git diff --cached` calls. The round-2 test git shim matches the argv `diff --cached --no-color --no-ext-diff -U0 ` followed by a space (`tests/test_precommit_hook_round2.py:87, :306, :327`). Inserting the flags before `-U0` would silently disarm the R3 pins.
   - Leave line 150 alone; it is pinned byte-equal by correction 6.
   - Add to the #312 stated limits: "UTF-16 content and line 150 binary content are not scanned by the hook or by gitleaks".
2. **Phase B, as its own scoped unit:**
   - Refuse a staged A/M/R file that `git diff --cached --numstat --no-textconv` reports as `-<TAB>-`, unless its path is on an allowlist built from the 65 currently tracked binary files in 13 directories (for example `SmartCompareApp/assets/**/*.png`, `docs/brand/*.png`). This closes UTF-16.
   - When Phase B lifts the line-150 pin, give line 150 the same flags.

## Acceptance
- **New hook-behaviour pins (sh and dash), each refused:** NUL plus a .env value, NUL plus a JWT, `*.json -diff` plus a .env value, and a textconv driver plus a .env value. After step 2, also UTF-16LE plus an AKIA key.
- **No false positive:** a pin that staging an existing PNG asset (e.g. `SmartCompareApp/assets/icon.png`) still passes.
- **Existing suites stay green:** round-1 and round-2 hook scenarios, including the R3 shim cases, and the `test_ci_gates` byte-equal pin of line 150.
- **Check one dependency:** confirm that the awk used by the CI test image (mawk on Ubuntu) handles NUL-bearing input in the 4a/4b pipelines.

=== TITLE: Pre-commit hook: the four-branch credential check (sk-/AKIA/xox/private key) sees no added lines under color.ui=always or diff.external
=== LABELS: security
## Context
Line 150-153 of `.githooks/pre-commit` runs the original four-pattern credential check (OpenAI sk-, AWS AKIA, Slack xox, PEM private-key header) over a bare `git diff --cached -U0 | grep -E '^\+'`. PR #312 pins that line byte-for-byte (spec correction 6; `tests/test_ci_gates.py:1408-1464`). The new checks 4a and 4b add `--no-color --no-ext-diff`, and the hook's own comment at :160-162 explains why: color.ui and diff.external can hide added lines. The pinned line does not get those flags. As a result, the hook now has three different ways of extracting the added lines.

Severity: low. Both verifiers agreed.
- The line has been byte-identical since 6205a7ce (2026-08-30), so this is not a regression.
- The gap needs a non-default git config. color.ui, color.diff and diff.external are unset at every level on this box.
- The .env value pass (4b) still catches keys that are in .env.
- The hook can be bypassed with `--no-verify`.
- TF3 records only the `++` hole of this line and TF7 records only the failed-diff case. Neither records this bypass.

## Failure scenario
A committer has `color.ui=always`, `color.diff=always` or a `diff.external` driver in their git config. They stage a file holding an AWS access key or an OpenAI key that is not in the local .env. The four-branch line sees no line starting with `+`, the hook exits 0, and the key is committed to the public repo. A JWT staged under the same config is still refused by 4a.

## Measurement
Hermetic scratch repos: private HOME, GIT_CONFIG_NOSYSTEM=1, LF copy of the #312 hook run with `sh`, payloads built at runtime. The staged file holds the AWS documentation example access key.

| Config | Staged | Result |
|---|---|---|
| default | AWS key | rc=1, "staged diff contains what looks like a credential" |
| color.ui=always | AWS key | rc=0 |
| color.diff=always | AWS key | rc=0 |
| diff.external=true | AWS key | rc=0 |
| color.ui=always | JWT | rc=1, 4a refuses |
| color.ui=always + diff.external | 26-char .env value | rc=1, 4b refuses |

Notes: scratchpad `step6/verify/COM-1_reproduce.md`, `step6/verify/COM-1_impact.md`.

## Fix
This needs an orchestrator ruling that lifts correction 6's byte-equal pin. The natural home is T0b Phase B, which also puts gitleaks in front of this line.
1. Feed the same four-pattern ERE from the 4a stream: `git diff --cached --no-color --no-ext-diff -U0 | awk "$ADDED_LINES_AWK" | grep -qE '<the same ERE>'`. Keep its own refusal message. This also closes the documented TF3 `++` hole: a staged line whose content starts with `++` becomes the diff line `+++...`, and `grep -Ev '^\+\+\+'` drops it.
2. Build ENV_MATCH_AWK's diff-header skip from the same awk fragment as ADDED_LINES_AWK, so there is one extractor.
3. In `test_ci_gates`, pin only the ERE string, not the whole pipeline line.
4. Optional, while the same lines are open: run one staged diff into the hook's private `$TMP` and feed all three checks from it. This is the same refactor surface as the hook-performance follow-up.

Until the ruling: add "the four-branch line is blind under color.ui/color.diff=always or diff.external" to the PR #312 stated limits, next to TF3 and TF7.

## Acceptance
- New scenarios in `tests/test_precommit_hook*.py`, run under sh and dash:
  - `color.ui=always` with the AWS documentation key staged: refused.
  - `diff.external=true` with the same key: refused.
  - A staged line whose content starts with `++` followed by an AWS-key shape: refused.
- The default-config refusal message for the four shapes is unchanged.
- The `test_ci_gates` pin now asserts the ERE, and the round-1 and round-2 suites stay green.

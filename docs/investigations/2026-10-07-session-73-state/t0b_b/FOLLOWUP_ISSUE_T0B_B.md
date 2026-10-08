# T0b Phase B follow-ups: gitleaks colour bypass, pipefail fail-open, backstop residuals, TB5 list

Follow-ups of T0b Phase B (the pre-commit secret scanning unit: `.githooks/pre-commit`, `.gitleaks.toml`, the CI `secret-scan` job). Ruling TBF23 (session 73) parked these items. None of them is a regression against the base hook (`845ece15`) except where an item says so. Each item gives its evidence pointer, the mechanism as measured, and the ready patch or node.

Evidence paths are in the session-73 scratchpad under `t0b_b/`:
- `fix_t0b-b-r3_report.json`: the round-3 fix report.
- `fix3/`: the fix-3 probes.
- `final_adversary_r4_report.json`: the round-2 final adversary.
- `adversary_r5_report.json`: the round-5 adversary.
- `adv5/`: the round-5 harness (`adv5.py`, `lfmut.py`, `mut5.py`, `probe_pipefail.py` and their outputs).

The orchestrator copies these into the session-73 state folder before filing. Hook line numbers refer to the LF copy of the merged hook. Every sentinel named below is built at runtime in the test file, never written as a literal.

Rules for every item:
- Write the test first.
- Run each node under sh and dash.
- Prove the node red on the unpatched bytes and green on the patched bytes.
- Re-run the four hook test files and the pin set, with gitleaks present and with it stripped from PATH.
- Every patch that touches a production line gets an adversary on the exact bytes.

---

## (a) F5: `git -c color.diff=always commit` blinds the gitleaks layer

**Evidence.**
- `fix_t0b-b-r3_report.json`: `f5_probe`, and the F5 stated limit.
- `fix3/f5_probe.py`, `fix3/f5_probe.out`, `fix3/f5_probe_diff.py`, `fix3/f5_probe_diff.out`.
- `fix3/f5_precedence.py`, `fix3/f5_precedence.out`, `fix3/f5_direct.py`, `fix3/f5_direct.out`.
- `final_adversary_r4_report.json`, finding F5: the hypothesis and the patch shape.
- Measured with the real gitleaks 8.30.1 and git 2.52.0.windows.1, each case a real `git commit` through the hook with `core.hooksPath`. The staged content was a runtime-built GitHub-token shape, which only gitleaks knows.

**Measured.**
| case | rc | committed |
|---|---|---|
| plain commit | 1 | no ("gitleaks refused the staged changes (rule id and place above)") |
| `git -c color.ui=always commit` | 1 | no (same refusal) |
| `git -c color.diff=always commit` | 0 | **yes** |

**Mechanism.**
- The hook forces colour off for gitleaks' own `git diff` through `GIT_CONFIG_COUNT=2` (`color.ui=never`, `color.diff=never`), in step 4g.
- `git -c k=v commit` exports `GIT_CONFIG_PARAMETERS` to the hook, and git applies `GIT_CONFIG_PARAMETERS` AFTER the `GIT_CONFIG_COUNT` entries. `f5_precedence.out` shows a git child of the hook reading `color.ui` = always despite the override.
- So the user's `color.diff=always` wins. gitleaks parses a coloured diff, finds nothing and exits 0. `f5_direct.out` confirms it:

  | `GIT_CONFIG_PARAMETERS` | override | rc |
  |---|---|---|
  | `color.ui=always` | none | 0 |
  | `color.ui=always` | the hook's COUNT override | 1 (`github-pat`) |

- `-c color.ui=always` alone fails to bypass only because the override's `color.diff=never` is the more specific key.
- The six regex shapes are NOT affected: the hook's own diffs pass `--no-color`.

**Ready patch (hook step 4g, the gitleaks call only).** Add to the env prefix of the gitleaks command, beside `GIT_CONFIG_COUNT=2`:

```sh
GIT_CONFIG_PARAMETERS="${GIT_CONFIG_PARAMETERS:+$GIT_CONFIG_PARAMETERS }'color.ui'='never' 'color.diff'='never'" \
```

The appended pair comes last, so it wins over anything the user passed with `-c`. Keep the COUNT override, which covers the repo and global config.

**Nodes.**
- Real tool, sh and dash; skips without gitleaks.
  - Stage a runtime GitHub-token shape (`_ghp()`).
  - Run the hook with `GIT_CONFIG_PARAMETERS="'color.diff'='always'"` in its env, which is what `git -c color.diff=always commit` exports.
  - Expect the refusal "gitleaks refused the staged changes (rule id and place above)" and no 12-character piece of the token.
- Repeat with `'color.ui'='always'` and with both keys.
- A shim node: the env that reaches gitleaks ends with `'color.diff'='never'` after the user's pair. This kills a mutant that prepends instead of appends.

**Before / after.** The node is red on the merged hook (rc 0 under the real tool) and green with the patch.

---

## (b) R5-5: `SHELLOPTS=pipefail` fails every `grep -q` check open on a large diff

**Evidence.**
- `adversary_r5_report.json`, finding R5-5.
- `adv5/probe_pipefail.py`, `adv5/probe_pipefail.out`, `adv5/probe_pipefail.json`.

**Measured.**
- Setup: sh = MSYS bash (Git for Windows), gitleaks stripped. `a.txt` is a 120,000-line file with a runtime AKIA key on line 1.
- Results:

  | case | `SHELLOPTS` | base | new |
  |---|---|---|---|
  | 120,000-line file, key on line 1 | unset | 1 | 1 |
  | 120,000-line file, key on line 1 | `pipefail` | 0 | 0 |
  | one-line file with the key | `pipefail` | 1 | 1 |

  - The pipefail row is the same with a working awk and with a dead awk.
- No sentinel leaked.

**Mechanism.**
- bash imports `SHELLOPTS` from the environment at startup.
- `grep -q` exits at its first match. The upstream stage (awk, tr, or the grep reading the staged-diff file) then gets SIGPIPE (status 141).
- Under pipefail the pipeline's status is that non-zero, so `if producer | grep -q ...; then fail ...` takes the no-match branch. Every secret check of that shape fails open: steps 4 and 4a, the backstop, and the `.env` refusal pipe.
- This is pre-existing and identical in base: the old step-4 line has the same shape. It is not a Phase B regression.
- dash ignores `SHELLOPTS`. The hook already neutralises `SHELLOPTS=allexport` (`set +a`, hook lines 367-372), but not pipefail.

**Ready patch.** Near the top of the hook, right after `set -u`:

```sh
if (set +o pipefail) 2>/dev/null; then set +o pipefail; fi
```

The probe runs in a subshell first: in dash, an unknown option to the special builtin `set` aborts a non-interactive shell, so a bare `set +o pipefail` would kill the hook under dash.

**Nodes.**
- sh only (bash), `SHELLOPTS=pipefail` in the env: a 120,000-line staged file with a runtime AKIA key on line 1 gives MSG_CREDENTIAL. It is red on the merged hook and green with the patch.
- dash: a clean commit still passes with the guard in place. This pins that the probe does not abort dash.
- Optional: the same pair with a dead awk.

---

## (c) R5-4: the dead-awk residual of NUL-to-LF in the backstop

**Evidence.**
- `adversary_r5_report.json`, finding R5-4, and its `mutants` entry `bs_tr_nul_to_space`.
- Scenarios `da_textattr_nul_same_line_akia` and `wa_textattr_nul_same_line_akia` in `adv5/adv5.py`.
- The LF mutant `adv5/mut_bs_tr_nul_to_space.lf`; its replay results are in `adv5/lfmut.jsonl`.

**Measured.**
- Setup: a `.gitattributes` line `*.txt diff` forces text, and `a.txt` holds `x`, a NUL byte, then ` k ` and a runtime AKIA key, all on one line.
- Results:

  | awk | hook | rc (sh/dash) |
  |---|---|---|
  | dead | base | 0/0 |
  | dead | new | 0/0 |
  | working | new | 1/1 |

- Base is equally blind, so this is NOT an additivity violation.
- The mutant `tr '\000' ' '` (at hook lines 212 and 218) turns the dead-awk case into a refusal (1/1). It keeps the UTF-16 sample refused (1/1, by the binary refusal 4e).

**Mechanism.**
- The backstop maps every NUL of the staged-diff file to a line break, so `+x<NUL> k <key>` becomes `+x` and ` k <key>`.
- The second segment has no leading `+`, so `grep -E '^\+'` drops it.
- With awk working, steps 4 and 4a read the whole line and refuse. The residual exists only when awk is dead.

**Candidate patch.** `tr '\000' ' '` in place of `tr '\000' '\n'` on both backstop blocks (hook lines 212 and 218).
- It keeps a line whole.
- It still does not join UTF-16 into ASCII: the letters stay space-separated, so no regex branch matches.
- `tr -d '\000'` stays rejected, because it joins UTF-16 into ASCII and turns the frozen `i315_utf16_aws_key` red (round-3 mutant m3).

**Before adopting it:**
- Run the frozen `i315_*` nodes of `tests/test_precommit_hook_phase_b.py` (`-k i315`, sh and dash, gitleaks present and stripped) against the variant.
- Run the round-2 file in full.

**Node.**
- Dead awk (`_broken_awk(r, 1)`), plus `.git/info/attributes` holding `*.txt diff`.
- Stage `a.txt` = `x` + NUL + ` k ` + runtime AKIA + newline, built in Python.
- Expect MSG_CREDENTIAL and no 12-character piece.
- It is red on the merged hook and green with the patch.

---

## (d) `LC_ALL=C` on the final grep of each backstop block

**Evidence.**
- `adversary_r5_report.json`, finding R5-6 (second half).
- Scenario `da_utf8_ff_same_line_akia` (`adv5/adv5.py`).
- The node `r5_dead_awk_utf8_locale_invalid_byte_same_line_akia_refused` of `tests/test_precommit_hook_phase_b_round2.py` (round 4).

**Measured.**
- The upstream stages of both backstop blocks run under `LC_ALL=C`. The final `grep -qE` of each block (hook lines 214 and 220) runs in the user's locale.
- On this box's GNU grep 3.0 it still matched a key on a line holding 0xFF under `LC_ALL=C.UTF-8` (new 1/1).
- Not measured: GNU grep 3.5 or later (CI Ubuntu) and BSD grep. GNU grep documents that under a UTF-8 locale it treats improperly encoded input as binary data and suppresses those output lines; `-q` prints nothing, and its exit status is not documented to change. So this is defence in depth, not a measured hole.

**Ready patch.** Prefix `LC_ALL=C ` to the `grep -qE` on hook lines 214 and 220:

```sh
   LC_ALL=C grep -qE '<the four-branch pattern>'; then        # line 214
   LC_ALL=C grep -qE -e "$JWT_RE" -e "$CREDURL_RE"; then      # line 220
```

**Pin to re-run first.** `tests/test_ci_gates.py::test_hook_keeps_the_four_credential_branches_byte_equal` pins the four-branch line of step 4 (hook line 178). The backstop line 214 repeats that pattern, so re-run the test to be sure it still finds the step-4 line it pins.

**Node.** The existing same-line node covers the scenario. A mutant that drops this new `LC_ALL=C` is expected to SURVIVE on grep 3.0, because no behaviour difference was measured there. State that in the PR. The first CI run on Ubuntu is the evidence for grep 3.5 or later.

---

## (e) F6 and F7: xtrace exposure of the binary head; QUIT and PIPE untrapped

### F6: under `sh -x` / `dash -x` the binary check traces 12 content bytes

**Evidence.**
- `final_adversary_r4_report.json`, finding F6.
- `adversary_r5_report.json`, `reproduced`: "xtrace under sh -x and dash -x: no .env value and no staged AKIA appear in the trace. The 12-byte binary head DOES appear".

**Mechanism.**
- In step 4e, `_head=$(git cat-file blob ":$_bin" | od -An -tx1 -N12 | tr -d ' \n')` is an assignment, so xtrace prints its value: 24 hex digits, which are the first 12 bytes of the staged file.
- For a disguised dump at an allowlisted path, those are 12 content bytes printed before the refusal.
- The `.env` values stay protected: step 4b turns xtrace off (hook lines 364-366) and restores it afterwards (`HOOK_XTRACE`).

**Ready patch.** Wrap the binary-refusal loop the way step 4b does:
- record `HOOK_XTRACE` from `$-` (or reuse it);
- run `{ set +x; } 2>/dev/null` before `BIN_LIST=...`;
- after the loop, `if [ -n "$HOOK_XTRACE" ]; then set -x; fi`.

**Node.**
- Run the hook with xtrace (`r.run_hook(shell, xtrace=True)`), sh and dash.
- Stage at `docs/x/p.png` a NUL-bearing blob whose first 12 bytes are a runtime-built, non-credential marker. It has no PNG magic, so 4e refuses it.
- Assert the BINARY refusal, and assert that the marker's hex form appears nowhere in the output.
- It is red on the merged hook and green with the patch.

### F7: QUIT and PIPE are not trapped

**Evidence.**
- `final_adversary_r4_report.json`, finding F7.
- `adversary_r5_report.json`, `reproduced`: TERM and HUP during gitleaks give rc 143/129 with no temp dir left, under sh and dash.

**Mechanism.**
- Since Phase B the private temp dir (mode 700: mktemp, or `umask 077`) holds the full staged diff (`staged.diff`, `staged.ext`, `gitleaks.err`) on every commit.
- Hook line 36 traps INT, TERM and HUP only. QUIT and PIPE would leave the dir behind, and KILL cannot be trapped.
- Not measured: QUIT and PIPE.

**Ready patch.** `trap 'cleanup; exit 1' INT TERM HUP QUIT PIPE` (hook line 36).

**Node.**
- A gitleaks shim that sleeps, as the adversary's TERM/HUP probe did, under sh and dash.
- Send QUIT to the hook process, then assert a non-zero rc and no `qaren-precommit*` or temp dir left in TMPDIR or `.git`.
- Measure first whether MSYS delivers QUIT to the shell. If it cannot, record the node as Linux-only.

---

## (f) TB5: 27 pre-existing findings in 16 files under the final config

**Evidence.**
- `fix_t0b-b-r3_report.json`, `stated_limits`, the TB5 entries.
- Source: GREEN's tree scan (2026-10-05) and adversary A's reproduction. It was not re-measured in rounds 2-4; `.gitleaks.toml` has not changed since fix 2 (sha256 `af71860f...`).
- With the default rules only, the same tree reported 82 findings.

**What it means.**
- These lines are already in `main`. CI's `secret-scan` job scans only the commits of each event, so they do not fail CI.
- The pre-commit hook scans only staged changes, so they do not fail a commit either.
- But changing any one of these lines makes it staged content, and both layers will then report it. Each needs either an allowlist entry in `.gitleaks.toml` in its OWN PR first (CI reads the config from the range base), or a rewrite of the line, before anyone edits it.

**The list (rule and count per file).**
- `SmartCompareApp/src/services/__tests__/sentry.test.ts`: generic-api-key 1, jwt 2
- `app/services/algolia_service.py`: generic-api-key 4
- `data/bh_gcc_source_candidates_round3.json`: algolia-api-key 1
- `docs/investigations/2026-06-25-bh-gcc-price-source-discovery-round3.md`: algolia-api-key 2
- `docs/investigations/2026-09-06-full-review-state/args-m22-product-output.json`: generic-api-key 1
- `docs/investigations/2026-09-06-full-review-state/continue-args-m22-product-output.json`: generic-api-key 1
- `scripts/probe_truth_freshness.py`: generic-api-key 1
- `tests/fixtures/jsonld_first/iq_miswag_com_no_structured_price_200.html`: jwt 1
- `tests/test_admin_key_and_sentry_scrub.py`: 1
- `tests/test_algolia_service.py`: 1
- `tests/test_api_budget_service.py`: 3
- `tests/test_identity_stamps_wave_b.py`: 1
- `tests/test_jomashop_persisted_query.py`: 1
- `tests/test_magento_gql_adapter.py`: 1
- `tests/test_referral_e2e.py`: 4
- `tests/test_sentry_service.py`: jwt 1

**Work.**
1. Re-measure the list with gitleaks 8.30.1 over a byte copy of current `main`, using the repo config, `--redact`, and a template report of rule id, file and line only.
2. Triage each finding into one of three classes:
   - a real secret: rotate it first, then remove it;
   - a public client key (the Algolia search keys): an allowlist entry scoped by rule and path, like the existing `tests/fixtures/` AND entry;
   - a test fixture: rewrite it to a runtime-built sentinel.
3. Land each allowlist widening in its own PR before the PR that edits the line.

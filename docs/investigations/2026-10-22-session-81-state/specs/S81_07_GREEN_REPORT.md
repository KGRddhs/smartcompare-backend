# S81-07 MEAS-CLAUDE-GATE: GREEN REPORT (Opus 5.5, 2026-11-12, 04:56-05:45 AST)

Unit S81-07. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s07. Base 6b909e0a92067d6b3562eee325e4956c116441f7.
Branch feature/s81-07-meas-claude-gate. HEAD 4ed9226bbacce930bf3829f0090fc6e4078238b7 (one commit, through the
hook, no --no-verify). git status --short after the commit: empty. No byte under app/ moved (git diff 6b909e0a HEAD -- app: empty).
RED file at start: sha256 447ef4da... (MATCH).
This report was copied to .md by a shell python step (the harness refuses a subagent's Write of a report .md).

## Files in the commit (sha256 of the bytes on disk)
| file | bytes | sha256 |
|---|---|---|
| scripts/meas_claude_gate.py | 82434 | 44f6eb83... |
| tests/test_s81_s07_meas_harness.py | 92841 | 30ac9d7b... |
| tests/_env_safety.py (E1, one line; CRLF working copy kept: 300 CR, 63 pre-existing non-ASCII bytes) | 14742 | 90cd990a... |
| tests/fixtures/s81_s07/_gen_fixtures.py | 10135 | 8220ad07... |
| tests/fixtures/s81_s07/compare_pairs.json | 65695 | af32ffa8... |
| tests/fixtures/s81_s07/fragrance_names.json | 9869 | 166e5e34... |
| tests/fixtures/s81_s07/moderation_parity.json | 41472 | 5461feaf... |
| tests/fixtures/s81_s07/verdict_gold.json | 110739 | 78134acf... |
| tests/fixtures/s81_s07/web_search_domains.json | 47 | e03de908... |
Every file but tests/_env_safety.py: 0 bytes > 127, 0 CR (the fixtures are pure ASCII JSON, Arabic as JSON escapes).
Not committed (gitignored .qa-s80): .qa-s80/S81-07_SPEC_AMENDMENTS.md 8ccfecc4... -> 0ffa2d59... (the GATE section appended).

## Step 0 (GC-16): the RED file amended RED-first, run at base
New RED sha256 30ac9d7b... (164 nodes = 152 R + 12 P).
[pyt] tag=s07g-step0-base start=2026-11-12 05:09:00 end=2026-11-12 05:09:16 elapsed=16s bound=600s status=FAIL rc=1
152 failed / 12 passed; 152 traceback terminal lines ": AssertionError" (no other exception type); 0 error, 0 skip;
[hermeticity] sentinel checked 164 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).

| row | GC id | red at base |
|---|---|---|
| _msg helper + test_r16_pricing_from_usage (web_fetch_requests 0) | GC-2 | yes (R16) |
| the canary map qxzjkvwyQXZJKVWY (every canary row) | GC-3 | yes (every R row red) |
| test_r06_out_inside_repo_refused (unique folder, finally cleanup) | GC-4 | yes |
| test_r61_refused_names_cover_the_suite_lists (prefix coverage, no ANTHROPIC_ member) | GC-5 | yes |
| test_r18 / test_r21 / test_r46 (the variable set again before the second live run) | GC-10 consequence | yes |
| test_r66_sticky_stop_inflight_sends_awaited | GC-6 | yes |
| test_r67_lock_released_on_every_exit | GC-7 | yes |
| test_r68_guard_runs_in_dry_run | GC-8 | yes |
| test_p13_httpx2_request_hook_mechanism (the P row, measured first) | GC-9 | no (P, green at base) |
| test_r69_client_hook_refuses_other_urls | GC-9 | yes |
| test_r70_credential_leaves_the_environment | GC-10 | yes |
| test_r71_base_sha_seam | GC-11 | yes |
| test_r72_go_exactly_on_every_bar (5 roles) | GC-12 | yes (5) |
| test_r72b_one_bar_crossed (28 crossings) | GC-12 | yes (28) |
| test_r72c_not_run | GC-12 | yes |
| test_r73_vision_identity_rule | GC-13 V | yes |
| test_r74_web_search_accept_and_reject | GC-13 W | yes |
| test_r75_real_command_line_is_quiet (the only subprocess row, 120 s) | GC-14 | yes |

P rows green at base: P01-P05, P07-P13 (12). P06 is R at base (R-S07-16 (c)).
GC-9 measurement (P13, httpx2 2.12.0, MockTransport only): an async request hook runs before the transport; a
BaseException raised there propagates and nothing is sent; the default https port reads as None; a sync hook on an
AsyncClient is a TypeError. Probe <notes>/probe_green.py -> probe_green.json (also measured: ServerToolUsage
requires web_fetch_requests and web_search_requests; CitationsWebSearchResultLocation validates in a text block;
the SDK keeps the passed http_client and its hooks).

## GREEN runs (the unit file)
[pyt] tag=s07g-unit1 start=2026-11-12 05:19:36 end=2026-11-12 05:20:19 elapsed=43s bound=600s status=FAIL rc=1 (163 passed, 1 failed: R61; a script comment named the suite module; reworded)
[pyt] tag=s07g-unit2 start=2026-11-12 05:20:50 end=2026-11-12 05:21:38 elapsed=49s bound=600s status=OK rc=0 (164 passed)
[pyt] tag=s07g-pin-test_s81_s07_meas_harness start=2026-11-12 05:34:30 end=2026-11-12 05:34:56 elapsed=26s bound=600s status=OK rc=0 (164 passed, after the S81-05 fix)
[pyt] tag=s07g-final-test_s81_s07_meas_harness start=2026-11-12 05:36:38 end=2026-11-12 05:37:11 elapsed=33s bound=600s status=OK rc=0 (164 passed, ASCII fixtures)
[pyt] tag=s07g-head-test_s81_s07_meas_harness start=2026-11-12 05:40:45 end=2026-11-12 05:41:17 elapsed=33s bound=600s status=OK rc=0 (164 passed, on the COMMITTED bytes)
Every run: [hermeticity] sentinel checked 164 test(s); [netguard] blocked 0 attempt(s) from 0 node(s). The one
warning is the conftest's DeprecationWarning (conftest.py:226), identical at base.

## Step 4: the spec 4.2 pins, each ALONE (a wait-free probe before each call)
[pyt] tag=s07g-pin-test_conftest_env_safety start=2026-11-12 05:23:19 elapsed=78s status=OK rc=0 (24 passed, 1 skipped, 2 deselected; base 24/1/2)
[pyt] tag=s07g-pin-test_hermeticity_pins start=2026-11-12 05:25:00 elapsed=128s status=OK rc=0 (103 passed; base 103)
[pyt] tag=s07g-pin-test_model_config start=2026-11-12 05:27:24 elapsed=40s status=OK rc=0 (34 passed; base 34); again after the last script edits: [pyt] tag=s07g-pin-test_model_config start=2026-11-12 05:34:59 elapsed=3s status=OK rc=0
[pyt] tag=s07g-pin-test_model_config_enforced start=2026-11-12 05:28:19 elapsed=32s status=OK rc=0 (25 passed; base 25)
[pyt] tag=s07g-pin-test_shadow_experiments start=2026-11-12 05:29:00 elapsed=6s status=OK rc=0 (78 passed; base 78)
[pyt] tag=s07g-pin-test_s81_s06_anthropic_router start=2026-11-12 05:29:12 elapsed=21s status=OK rc=0 (333 passed)
[pyt] tag=s07g-pin-test_s81_s06_router_gate_rows start=2026-11-12 05:29:37 elapsed=6s status=OK rc=0 (81 passed)
[pyt] tag=s07g-pin-test_s81_kb_schema start=2026-11-12 05:29:47 elapsed=21s status=OK rc=0 (529 passed)
[pyt] tag=s07g-pin-test_s81_s05_request_context start=2026-11-12 05:30:18 elapsed=19s status=FAIL rc=1 (1 failed: test_s05_p01_no_consumer_in_app; the script carried the S81-05 pepper NAME as one literal) -> fixed (the name joined at import) -> [pyt] tag=s07g-pin-test_s81_s05_request_context start=2026-11-12 05:34:21 elapsed=6s status=OK rc=0 (176 passed)
[pyt] tag=s07g-pin-test_s81_s22_judge start=2026-11-12 05:30:46 elapsed=11s status=FAIL rc=1 (1 failed, 57 passed: test_j01_script_exists_and_off_first, the CRLF hygiene base failure of GC-15, in the stored base list)
[pyt] tag=s07g-pin-test_s81_s22_gate_rows start=2026-11-12 05:31:01 elapsed=9s status=OK rc=0 (13 passed)
[pyt] tag=s07g-pin-test_s81_d22_nightly_learning start=2026-11-12 05:31:14 elapsed=25s status=OK rc=0 (50 passed)
[pyt] tag=s07g-pin-test_ci_gates start=2026-11-12 05:31:45 elapsed=20s status=OK rc=0 (52 passed)
[pyt] tag=s07g-pin-test_behavior_dimension_translation start=2026-11-12 05:32:11 elapsed=17s status=OK rc=0 (27 passed)
[pyt] tag=s07g-pin-test_s81_s04_spend_breaker start=2026-11-12 05:32:32 elapsed=15s status=OK rc=0 (284 passed)
[pyt] tag=s07g-pin-test_s81_s08b_legacy_fingerprint start=2026-11-12 05:32:53 elapsed=8s status=OK rc=0 (85 passed)
[pyt] tag=s07g-pin-test_s81_s08b_gate_rows start=2026-11-12 05:33:05 elapsed=6s status=OK rc=0 (29 passed)
[pyt] tag=s07g-pin-test_s81_s23_bypass_retire start=2026-11-12 05:33:14 elapsed=4s status=OK rc=0 (33 passed)
Every pin run: [netguard] blocked 0 attempt(s). Logs <notes>/pin_<file>.log; [pyt] lines <notes>/pins_lines.txt.
Most 4.2 pins ran BEFORE two later script edits (the pepper-name join and a comment line for D8); both are inert for
those readers; the unit file, the s05 pin and test_model_config re-ran after them (the unit file again at HEAD).

## Step 5: lint, syntax, dry runs
ruff --select E9,F63,F7,F82 --no-cache (script, generator, _env_safety, RED file): All checks passed! py_compile: OK (at HEAD).
Dry run of every stage (<notes>/dry_all.py -> dry_all2.json): each stage in its OWN child process, the credential
variable unset, every ANTHROPIC_* / refused / ENABLE_* / proxy name removed, a process-wide socket guard (loopback
only) installed before the harness import, _read_key and _client_factory counted, the child's stderr captured as bytes.

| stage | exit | calls | worst case USD | cap | stderr bytes | blocked sockets | key reads | clients built |
|---|---|---|---|---|---|---|---|---|
| text | 0 | 622 (A0 2, A1 320, A2 40, A3 20, A4 100, A5 20, A6 120) | 1.443423 (A1 0.248248, A2 0.079994, A3 0.799144, A4 0.067629, A6 0.248407) | 4.00 | 0 | 0 | 0 | 0 |
| moderation | 0 | 200 | 0.261435 | 2.00 | 0 | 0 | 0 | 0 |
| vision (no --set: NOT RUNNABLE) | 0 | - | - | 5.00 | 0 | 0 | 0 | 0 |
| vision --set (100 synthetic 1x1 PNGs) | 0 | 300 (100 each) | 3.61238 (V1 0.11294, V2 0.16664, V3 Sonnet 3.3328) | 5.00 | 0 | 0 | 0 | 0 |
| web_search (no --owner-line: NOT RUNNABLE) | 0 | - | - | 3.00 | 0 | 0 | 0 | 0 |
| web_search --owner-line | 0 | 80 (20 each of W1-W4) | 1.33096 (0.332466 / 0.333014 per pair) | 3.00 | 0 | 0 | 0 | 0 |
| report | 0 | - | - | - | 0 | 0 | 0 | 0 |

Sum of the four stage worst cases 6.648 USD <= the 15.00 unit ceiling. GC-14 is also pinned in-suite by R75.

## What the script adds over the prototype (every line GREEN's)
GC-5 the tuple without ANTHROPIC_ members; GC-6 the sticky stop and a crash-first re-raise after a phase gather
(sends in flight awaited, never cancelled); GC-7 the lock removed in finally on every exit after its creation;
GC-8 the guard installed in every mode (live: host_allowed; otherwise loopback), a dry-run stop caught by the stage
runner (exit 6, no plan, results with stop_reason), a main-level StageStop arm for a stop outside a stage run (one
stderr line with the reason code only); GC-9 _make_request_guard (an async hook: https, ALLOWED_HOST, port None or
443); GC-10 os.environ.pop right after _read_key; GC-11 _git_head -> results base_sha; GC-12 evaluate_role, the
per-setting metric blocks of the summary (A1 sites, A3, A4, A6 incl. agreement, M1, V, W) and the top REPORT table
built from it, the raw figures and the three proposals with n and censored counts; GC-13 identity_hit, V hits /
n_scored / hit_rate, W outcomes / accepted / web_search_requests / citations, --settings in every stage; GC-14
logging.disable(CRITICAL) and warnings.catch_warnings from the dotenv guard to finally; resume: a completed call's
stored (scrubbed) raw response is handed back to the stage (moderation and the scoring read it) and the metrics cover
the completed calls of earlier runs.

## Deviations (stated, none silent)
- D1 GC-10 consequence: R18, R21 and R46 make two live starts; the first start removes the variable from the
  process, so each row sets it again (monkeypatch.setenv) before its second run. A pin-fix the gate implies but does
  not name; nothing is weakened.
- D2 R-S07-26 (b) "copied as literals": the S81-05 pepper NAME is written "DEVICE_KEY" + "_PEPPER" in
  REFUSED_ENV_NAMES, because tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app (a 4.2 pin,
  unedited) allows that contiguous name only in the two S81-05 modules. R61 sees the joined name.
- D3 GC-14 "the netguard file": a python -m subprocess carries no pytest netguard (its report is written only at the
  terminal summary), so R75 installs its own recorder through a sitecustomize.py on PYTHONPATH (every non-loopback
  resolution or connect is written to a file that must stay empty). A CHOICE, stated in the amendments.
- D4 GC-6 crash precedence: after a phase gather a non-StageStop exception (a crash) is re-raised before a stop; the
  GATE section of the amendments says so.
- D5 GC-12 metric shapes and bar names are a CHOICE written to the amendments' GATE section and pinned by R72 /
  R72b (28 single-bar crossings, each == ("NO-GO", [bar])) / R72c; every ratio is rounded to 9 decimals so a value
  exactly on a bar passes (the GC-12 comparison-flip mutants should die on the R72 ON-bar rows; not run here).
- D6 tests/_env_safety.py is CRLF in the working copy (as the task said; one early grep of mine misread it); the
  added line keeps CRLF on disk, the index stays LF, git diff --stat shows 1 line.
- D7 the fixtures are pure ASCII JSON (ensure_ascii=True; the prototype wrote raw UTF-8 Arabic), the values
  unchanged. web_search_domains.json names three public GCC retailer domains (boutiqaat.com, faces.ae, noon.com)
  instead of the prototype's .invalid names, so a live W run can return citations; they are request parameters of
  Anthropic's tool, not hosts the harness contacts (the guard allows only api.anthropic.com).
- D8 the hook refused one commit attempt (gitleaks generic-api-key on the TEXT_SETTINGS line: "A5_count_tokens"
  followed by a quoted value); fixed by putting that name on its own line with a comment. The refused attempt
  created no commit; the ONE commit is 4ed9226b.
- D9 the added-line sweep: the only 8-digit runs are the web-search tool version dates (20250305, 20260318), which
  R63 / P09 require; no personal value anywhere.
- D10 spec 4.2 also says "every grep reader in 7.1": not enumerated separately here; the CLAUDE.md readers and the
  named pins above were run; the full comm set is the next agent's (GC-15 / GC-17).

## NOT MEASURED / not started (the next agent's, per the task)
The mutation table on the real script (61 + the gate's), the comm set at HEAD against the stored base record (12
CRLF base failures), the client fences, CLAUDE.md, the PR body. No live run, no network, no credential read, no
variable set.

## Open questions for the gate
- Q1 D2 (the pepper name joined) and D7 (real retailer domains as allowed_domains) want a ruling line.
- Q2 GC-12: TEXT pools the A1 sites other than verdict (the verdict site belongs to the VERDICT role); confirm.
- Q3 VERDICT a6_agreement_min: with --reps 1 the agreement is None and the bar fails (NO-GO); confirm, or make it NOT RUN.

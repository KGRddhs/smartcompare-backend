# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 1 report (2026-10-20)

- Unit B4, flag `ENABLE_URL_MODE_V2` (default OFF, read per call). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, base `81df2b64` (not rebased, GC-7).
- Start: HEAD `9db99de97245aa4543e054dd5f94c0800b270e69`, `git status --short` empty (verified 15:19).
- End: HEAD `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b` (ONE commit through the pre-commit hook, `All checks passed!`; no push, no rebase, no stash, no checkout). `git status --short` empty. No mutation lock left; the scratch worktree is removed (`git worktree list` shows none under B4_fix1); no orphan pytest (the only python.exe processes are two unrelated `http.server` instances, seen before the first run).
- Agent model: claude-opus-5-5 (this agent's system prompt). Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` per RULINGS_FIX1_B4 step 5 ("trailer naming your own model") and F4-6 (D8 accepted); the task text's Fable 5.1 trailer would be a false attribution.
- Inputs read: s80-common.txt (incl. the 2026-10-20 addendum), PLAN_S80.md sections 0-1, RULINGS_BATCH1.md Common + B4, GATE_B4.md, RULINGS_FIX1_B4.md (in full, twice), B4_GREEN_REPORT.md, the GREEN PR body; the spec and the review were searched for the log-level, R12 and image clauses (spec :94, :169, :260; review RC2, C20, the retype note), not read end to end.

## Files (final sha256 = bytes on disk = the committed working copy)

| file | +/- | sha256 before (9db99de9) | sha256 after (96676f1f) | bytes > 127 before/after | line endings |
|---|---|---|---|---|---|
| tests/test_s80_url_mode_v2.py (RED, F4-2) | +75/-0 | c4549be2f5cd8edfd60cbc07db427ed5275cc4b44ab719614ef97b9eca227cae | **546fc27d07579808ea7b8b7fb60cd87a3be8462ebdaea677aa3c8e21587f8b46** | 0/0 | LF (as frozen) |
| app/services/url_extraction_service.py (F4-1) | +10/-4 | 649c93a88cbded0fc399594c9492fcd83cbc568ace3a40cba9f0029a4eaabef1 | 0abf3b950898fd10678f3092c424729696072a6d33b1925d3dc2a09279e647c2 | 18/18 | CRLF 1295/1295 |
| tests/test_paid_route_metering.py (F4-3, E6) | +12/-0 | 9e7fd283e1a23531dc8535517123b9668251482a308ae9c09498ed1c740433c0 | 4724c308c6a5805a873a015f2a07e02850e8db5c020f46423e71208505ead73f | 0/0 | CRLF 831/831 |
| CLAUDE.md (F4-6, the SESSION 80 B4 row) | +2/-2 | 89ce189a83da5f6fc8e95ad5d01937a969194fee3401f84482061466738e06b4 | 8502da3b038953d7ecaad3637567683f8149415af1304c90fc1dc52749a2c0ad | 3979/3979 | CRLF 938/938 |

RED file: a pure append (the first 71,891 bytes hash to `c4549be2...cae`, measured); 253 nodes; the committed blob (`git show HEAD:tests/test_s80_url_mode_v2.py`) hashes to `546fc27d...8b46`. The working copy is byte-identical before and after the commit (pre/post hash files in the notes folder). Added-line sweep (`git diff -U0`, 99 added lines): no @gmail, +973, 8-digit run, sk-/AKIA/xox/eyJ, credentialed URL or PEM; 0 non-ASCII bytes. Byte copies: `B4_fix1/before/` + `SHA256SUMS.txt`.

Notes-folder files (not committed): `B4_fix1/PR_BODY.md` sha256 `ea1a3ae4d909aae87b41243954eb2ba5a8bd9f5e1e6db9f67277c7433b80e82f` (the updated PR body draft; 4 bytes > 127 = the required robot glyph line, D9), `g10_kill.py` `a90fde4ac999bb8173c2b0cfd74902918b25c46a1c085f60a826f6191a58bde5`, `commit_msg.txt`, `notes.md`, every `[pyt]` log below.

## What changed

- **F4-1** `_fetch_page_v2` except arm: `_log_fetch_failed(url, "fetch_error", ...)` (WARNING) replaced by an inline `logger.error("[URL-V2] fetch failed host=%s reason=%s type=%s", _host_only(url), "fetch_error", type(e).__name__)` lexically inside the `except Exception as e:` arm (it must be inline: `tests/test_sentry_channels_u8d_unit.py::test_u8d_pin_r8_no_other_outside_except_error_line` scans every ERROR call OUTSIDE an except arm in app/ and `_host_only(url)` is not an allowed argument there). `_log_fetch_failed` (WARNING) still serves blocked / redirect_cap / non-2xx / challenge; its docstring and the arm's comment now state F4-1. No RED edit. `_host_only` is ValueError-safe (B4-R4), so the ERROR line cannot raise inside the arm.
- **F4-2** PIN row `test_normaliser_coerces_a_raw_image_list_flag_on` (one node): `extract_from_url(url, url_mode_v2=True)` over four cases in both `ENABLE_PRICE_PARSE_OFFLOAD` states -- `noon_jsonld_list` (`https://www.noon.com/uae-en/b4-probe-oud/N4B4PROBEA/p/`, raw JSON-LD `[http, https]` -> `https://f.nooncdn.example.test/b4.jpg`), `amazon_raw_src` (`https://www.amazon.ae/b4-probe-parfum/dp/B0B4PROBE1`, `landingImage` src `//m.media.example.test/images/b4.jpg` -> its https join), `llm_merged_list` (a node with no image and no price; the LLM answer's image LIST is merged raw -> `https://img.example.test/llm.jpg`), `llm_merged_http_only` (-> None); asserts str-or-None, the exact value and the LLM call count (0 / 1). All hosts are `example.test` or mocked through the MockTransport; no network (netguard 0).
- **F4-3 (E6)** `tests/test_paid_route_metering.py` had NO clean list (its only env handling is the `flag_on` / `flag_off` fixtures for `ENABLE_PAID_ROUTE_METERING`); E6 adds `_CLEAN_ENV = ("ENABLE_URL_MODE_V2",)` and an autouse `_clean_env` fixture (the `test_retro_w2_1.py` `_clean_flags` shape). No other file imports this test module (only docstrings in `test_image_identify_llm_unavailable_s69.py` and node ids in `.network_attempt_baseline.txt` name it); node ids unchanged.
- **F4-6** CLAUDE.md row: the header cites F4-1..F4-6; the log sentence now reads ERROR for a transport error / WARNING for blocked hop, redirect cap, non-2xx, challenge, never the base template; D2 stated in the effect clause (a WebPage node's name is not a site name); limit (7) names the normaliser pin; limit (16) rewritten (E5 + E6 close the measured local-.env class; the flag-exported runs); new limit (17) = F4-5. D4 was already stated (the `Detected retailer` label). Word diff checked; the two CLAUDE.md readers pass.

## Runs (every pytest through pyt.py, one at a time; paste of every [pyt] line)

PIN step, RED file with the appended row on the GREEN bytes (before the F4-1 code edit):
```
ENABLE_URL_MODE_V2=true: 2 failed, 251 passed, 11 warnings in 55.72s; [hermeticity] sentinel checked 253 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
FAILED ...::test_transport_error_is_store_unreadable[POST], [GET]  (R12, the pre-F4-1 WARNING)
[pyt] tag=b4f-pin-on start=2026-10-20 15:31:31 end=2026-10-20 15:33:01 elapsed=90s bound=600s status=FAIL rc=1
flag unset: 2 failed, 251 passed, 11 warnings in 20.85s; sentinel 253; netguard 0 (same two R12 nodes)
[pyt] tag=b4f-pin-off start=2026-10-20 15:33:15 end=2026-10-20 15:33:45 elapsed=30s bound=600s status=FAIL rc=1
```
G10 kill (detached scratch worktree `B4_fix1/scratch_g10` at `9db99de9`, the new unit file copied in; lock, byte copy, exact edit matching once on the CRLF copy, restore, sha256 compare, unlock; worktree removed afterwards):
```
control (unmutated): 1 passed, 252 deselected, 10 warnings in 16.90s; sentinel 1; netguard 0
[pyt] tag=b4f-g10-control start=2026-10-20 15:35:32 end=2026-10-20 15:35:53 elapsed=21s bound=600s status=OK rc=0
mutant G10 ("image_url": raw.get("image_url")): 1 failed, 252 deselected, 10 warnings in 3.27s; sentinel 1; netguard 0
  E AssertionError: ('amazon_raw_src', None, '//m.media.example.test/images/b4.jpg')
[pyt] tag=b4f-g10-mutant start=2026-10-20 15:35:54 end=2026-10-20 15:35:59 elapsed=5s bound=600s status=FAIL rc=1
restore sha before=649c93a8...eaabef1 after=649c93a8...eaabef1 OK; lock removed True
```
Gates on the fix-round bytes (identical to the committed bytes):
```
unit ON: 253 passed, 11 warnings in 37.21s; [hermeticity] sentinel checked 253 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4f-unit-on start=2026-10-20 15:37:57 end=2026-10-20 15:38:40 elapsed=43s bound=600s status=OK rc=0
unit OFF: 253 passed, 11 warnings in 52.62s; sentinel 253; netguard 0
[pyt] tag=b4f-unit-off start=2026-10-20 15:38:51 end=2026-10-20 15:39:53 elapsed=62s bound=600s status=OK rc=0
u8d R8 pins (test_sentry_channels_u8d_unit.py + test_sentry_channels_u8d.py, one call, flag unset): 272 passed, 1 warning in 25.22s; sentinel 272; netguard 0
[pyt] tag=b4f-u8d start=2026-10-20 15:39:57 end=2026-10-20 15:40:29 elapsed=32s bound=600s status=OK rc=0
metering flag unset: 21 passed, 13 warnings in 19.18s; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s) (sentinel class, both in .network_attempt_baseline.txt)
[pyt] tag=b4f-meter-off start=2026-10-20 15:40:45 end=2026-10-20 15:41:11 elapsed=26s bound=600s status=OK rc=0
metering flag exported (E6 proof; GREEN b4g-pins1-flagON-info had these 5 url_compare_* nodes red): 21 passed, 13 warnings in 20.42s; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4f-meter-on start=2026-10-20 15:41:14 end=2026-10-20 15:41:39 elapsed=25s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF): 904 passed, 13 warnings in 40.83s; sentinel 904; netguard blocked 10 attempt(s) from 10 node(s) (the GREEN count, sentinel class)
[pyt] tag=b4f-ci-order start=2026-10-20 15:41:52 end=2026-10-20 15:42:35 elapsed=43s bound=1200s status=OK rc=0
GREEN 20-file pin set, flag EXPORTED (local-.env class): 1037 passed, 13 warnings in 227.11s; sentinel 1037; netguard blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4f-pins20-flagON start=2026-10-20 15:43:53 end=2026-10-20 15:47:48 elapsed=235s bound=600s status=OK rc=0
CLAUDE.md readers (test_ci_gates.py + test_behavior_dimension_translation.py): 79 passed, 1 warning in 5.18s; sentinel 79; netguard 0
[pyt] tag=b4f-claude-readers start=2026-10-20 15:49:27 end=2026-10-20 15:49:33 elapsed=7s bound=600s status=OK rc=0
delta chunk (remaining importers of url_extraction_service + source-scanning pins, flag OFF: test_conftest_env_safety, test_llm_provider_base_url, test_openai_breaker, test_retro_w0_4, test_url_validator_offloop_hops, test_model_config, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69): 368 passed, 1 skipped, 2 deselected, 3 warnings in 177.98s; sentinel 369; netguard blocked 121 attempt(s) from 6 node(s) (all six test_openai_breaker.py nodes are in .network_attempt_baseline.txt)
[pyt] tag=b4f-delta-chunk start=2026-10-20 15:50:07 end=2026-10-20 15:53:07 elapsed=180s bound=1200s status=OK rc=0
```
Lint: `ruff check --select E9,F63,F7,F82 --no-cache` over the three app files, the six edited test files (E1-E6) and the unit file: `All checks passed!`; `py_compile` on the same ten: rc 0; full-rule ruff on `app/services/url_extraction_service.py`: 58 findings at 9db99de9 and 58 after (no new finding).

## Counts

RED file: 253 nodes (252 frozen + 1 appended PIN); 253/253 green in both flag states. Mutants this round: 1 (G10) KILLED (AssertionError); GREEN's other 11 were KILLED on the GREEN bytes and are not re-run (the F4-1 edit is outside every one of their edited snippets: G1-G12 snippets were re-read and none spans the except arm). TIMEOUTs: 0.

## Rulings answered

- F4-1 (D1 / Q1): done as ruled; R12 green; u8d R8 green.
- F4-2 (Q2 / G10): row appended and G10 killed (above).
- F4-3 (Q3 / E6): done; the file had no clean list, so E6 creates a one-name one (deviation X1).
- F4-4 (Q4): D2 / D3 / D4 stated as the contract (CLAUDE.md row + PR body).
- F4-5 (Q5): stated limit 17 (CLAUDE.md row + PR body); no code change.
- F4-6: CLAUDE.md row + PR body carry the F4-1 truth (no remaining "WARNING" wording for the transport-error line); the PR body's mutation note records G10 KILLED by the F4-2 row; trailer = own model.

## Deviations

- X1 (F4-3): `tests/test_paid_route_metering.py` had no clean list to add to; E6 adds `_CLEAN_ENV` + an autouse `_clean_env` fixture (12 added lines, test-only) instead of a one-name insertion. Scope: every node of the file (the flag is read only by the url route and the error handler's three B4 codes, so clearing it for the camera / prices nodes is a no-op in CI, which runs it unset).
- X2: the two u8d files ran in ONE pyt call (not one call each); both are R8 pin files and nothing else ran with them.
- X3: no second full comm pass was run; the fix round's delta (one log level inside an except arm, two comments/docstrings, a test-only fixture, an appended row) was covered by the ruling's gates plus the delta chunk above (every remaining importer of `url_extraction_service` and the named source-scanning pins). The GREEN 120-file comm set (on 9db99de9) is the comm evidence; its only branch-only-NEW nodes were the two R12 rows, now green.
- X4: the fix-round PIN's "fails at base on the `_assert_kwarg` AssertionError" is read from the base source (`81df2b64`: `async def extract_from_url(url: str)`), not run at base.
- X5: commit trailer names Claude Opus 5.5 (this agent's model), per the fix rulings, not the task text's Fable 5.1.

## Questions for the gate / the re-verifier

1. Sentry consequence of F4-1 (stated in the PR body owner step 3, NOT in the committed CLAUDE.md row): `sentry_service` installs `LoggingIntegration(level=logging.ERROR)` with the default ERROR event level, so with the flag ON a link transport error becomes a Sentry event under the new `[URL-V2] fetch failed` template (it replaces the base `Failed to fetch URL host` event it produced OFF, so the count is unchanged for transport errors), while a non-2xx link, which raised `raise_for_status` into that base ERROR line OFF, is a WARNING ON and no longer reaches Sentry. Read from code, not from a Sentry canary. Add a sentence to the CLAUDE.md row at the rebase if wanted.
2. The re-verifier's R8 shapes (a second ERROR with the base prefix; the distinct template demoted to WARNING) are not run here (the re-verifier's job); the GREEN `b4g-variant-error-level` measurement and this round's u8d run cover the shipped shape only.

## NOT MEASURED

- The full GREEN M1-M49 / G1-G12 mutation table on the fix-round bytes (only G10 run, in the scratch worktree).
- A second full comm pass (X3); the four `test_precommit_hook*.py` files (excluded by rule; `.githooks` untouched; the hook itself ran on the commit).
- Any Sentry or live behaviour; the post-rebase run on `cb80ea2f` (the orchestrator's step, GC-7).

## Notes folder

`<scratchpad>/B4_fix1/`: notes.md, before/ (+ SHA256SUMS.txt), claude_row_diff.txt, g10_kill.py, g10_byte_copy_url_extraction_service.py, pin_on.log, pin_off.log, b4f-g10-control.log, b4f-g10-mutant.log, unit_on.log, unit_off.log, u8d.log, meter_off.log, meter_on.log, ci_order.log, pins20_files.txt, pins20_on.log, claude_readers.log, delta_chunk_files.txt, delta_chunk.log, precommit_hashes.txt, postcommit_hashes.txt, commit_msg.txt, PR_BODY.md, this report.

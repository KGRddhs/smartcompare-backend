# S81-10 FRAGRANCE-ONLY-GATE: REBASE ROUND REPORT (rebase-and-gates agent, Opus 5.5)

Verdict: **READY_FOR_PR**. Written through the shell (python), 2026-11-02.

## Identity
- worktree sc-s81-s10, branch feature/s81-s10-fragrance-only-gate
- HEAD before: 0e4b69e8065654293db548f0c114ff09714cf4e6 (git status --short EMPTY at start, no .qa-mutation.lock)
- base (origin/main fetched): a513ea3b51a6b08d645547f4e260134fa8273d48 (#380 S81-G1 on #379 S81-09); merge-base before the rebase 6c14ac95
- HEAD after: 2c6875f3bda35ed00ac8c1f54f5b7552b6a9a46a = 27cc9184 (GREEN 0523a06f replayed) + 8e62ca04 (fix 0e4b69e8 replayed) + 2c6875f3 (the round commit)
- git diff --stat origin/main...HEAD:  14 files changed, 5333 insertions(+), 4 deletions(-); name-status: M CLAUDE.md, M app/api/home_routes.py, M app/api/image_routes.py, M app/api/text_routes.py, M app/api/version_routes.py, M app/middleware/error_handler.py, A app/services/category_gate.py, M app/services/structured_comparison_service.py, A data/fragrance_lexicon.json, A tests/fixtures/s81_s10_flag_off_golden.json, M tests/test_migration_043_delete_user_cascade.py, M tests/test_s81_s05_request_context.py, A tests/test_s81_s10_fragrance_gate.py, A tests/test_s81_s10_gate_rows.py
- git status --short at the end: EMPTY
- conflict markers (git grep ^<<<<<<< / ^>>>>>>> over CLAUDE.md, app/, tests/ at HEAD): none

## Frozen files (start = end)
- tests/test_s81_s10_fragrance_gate.py: blob sha256 fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e, disk sha256 fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e (LF, 111629 bytes)
- tests/fixtures/s81_s10_flag_off_golden.json: blob sha256 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a, disk sha256 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a (LF, 17123 bytes)
- start (disk, 16:50): fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e / 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a: identical at the end (blob and disk).
- between: the rebase checkout re-wrote both (and data/fragrance_lexicon.json) with CRLF in the working copy (core.autocrlf=true, no .gitattributes); the blobs never changed. The committed LF bytes were written back from the blobs (tools/lf_from_blob.py: asserted blob has no CR and disk == blob modulo CRLF), then `git add` of the same three paths refreshed the index stat (status had shown ' M' from the size-only stat change with an EMPTY content diff); `git diff --cached --quiet` rc 0, index blob ids == HEAD's.

## Conflicts and resolutions (pick 1 = 0523a06f; pick 2 = 0e4b69e8 replayed clean)
Measured first: `git merge-tree --write-tree --name-only origin/main HEAD` = CONFLICT in exactly CLAUDE.md, app/middleware/error_handler.py, tests/test_s81_s05_request_context.py; auto-merge image_routes, text_routes, structured_comparison_service (= RB10-10). Resolved by tools/resolve1.py (every region shape-checked; CRLF kept; byte copies of the conflicted files kept):
- app/middleware/error_handler.py (RB10-2), 2 regions: (1) after `_url_mode_v2_keys_enabled`: S81-09's `_USAGE_LIMIT_SCOPES` + `_device_quota_keys_enabled` (complete), then S81-10's `_fragrance_gate_keys_enabled` (the shared tail `"true", "1", "yes", "on",` / `)` duplicated so both defs are whole); S81-10's `_CANONICAL_CATEGORY_KEYS` auto-merged after `_URL_V2_PASSTHROUGH_CODES`; (2) after the B4 block: S81-09's USAGE_LIMIT block, then S81-10's CATEGORY_NOT_LIVE block, then `headers = None`. vs main: +35 lines = the GREEN's +35; no line reworded.
- tests/test_s81_s05_request_context.py (RB10-3), 1 region: `_ALLOWED_CTX_FILES` = main's entries + S81-10's comment + `app/services/category_gate.py` after `usage_service.py`; `_GATE_CTX_ATTRS = {device_fingerprint, device_key}` (S81-10's line) after `_USAGE_CTX_ATTRS`; `_CTX_CONSUMER_ATTRS` gains `"app/services/category_gate.py": _GATE_CTX_ATTRS`; S81-10's auto-merged per-file `if rel == "app/services/category_gate.py":` branch (23 lines) DROPPED in favour of main's dict-driven branch; the needle exceptions stay S81-09's. vs main: +6 lines. NOTE: main's dict-driven branch asserts the exact import shape and the attribute set but not that the import is function-local (the GREEN branch did); the function-local import of category_gate.py stays pinned by the frozen RED row R55 (test_r55_request_context_consumer_shape: `froms[0] not in tree.body`). black --check on the file: unchanged (rc 0).
- CLAUDE.md (RB10-4 / RB10-9 / RB10-10), 2 regions: (1) the `**Feature Flags:**` pointer line: base, main and branch measured as two pure insertions at the same point (after the S81-15 entry); union = main's line + the S81-10 entry right after main's S81-09 entry (merge order; main 6291 -> 6500 chars, +209 = the branch's insertion); (2) the rows: main's S81-09 row and S81-G1 block in merge order, a blank line, the S81-10 row, then the existing blank line and `## Tests` (no new `## ` heading). Non-ASCII bytes: main 3913, HEAD 3913 (0 added). vs main after the round: one pointer line changed + the S81-10 block.
- after each continue: `git diff --check` rc 0 for both replayed commits; the hook BY HAND on the staged resolution of pick 1 and, in a scratch worktree at 27cc9184 with 8e62ca04 read into the index, on pick 2's exact diff:
  - `[hook] tag=s10rb-hook-pick1-staged start=2026-11-02 16:54:44 end=2026-11-02 16:54:57 rc=0`
  - `[hook] tag=s10rb-hook-pick2-staged start=2026-11-02 17:23:19 end=2026-11-02 17:23:31 rc=0`
- RB10-5 / RB10-9 re-read: on all three text routes the gate block sits after `start_time` and before the preferences read and S81-09's device-aware consume (text_routes lines 612/618/620/638, 840/846/848/865, 1036/1043/1045/1063 at HEAD); on the camera the budget read precedes the consume; the kwargs lines intact. `git patch-id --stable`: the unit's hunks main..HEAD == base..branch for text_routes and structured_comparison_service, and main's own hunks base..main == branch..HEAD for all three (G1's image-branch and rating-fallback hunks intact); image_routes' unit hunks have identical +/- lines (51) and differ only in context (S81-09's consume line).

## RB10-6 seam collapse (the round's one app/ edit; app/services/category_gate.py +18 / -40)
- re-read FIRST: R46 asserts `(day, next) == usage_service._usage_window(now)` and the offset == 3 iff `usage_service.riyadh_reset_enabled()`; R47 the allow-list outcomes (an upper-case listed id exempt, another not); R48 the premium tier exempt with ONE tier read, none when the budget is not spent; R43 the INCR script text. None pins the local implementation: the collapse proceeded.
- `reset_window(now)` = `_usage_service._usage_window(now)` + offset `_usage_service.RIYADH_UTC_OFFSET_HOURS` if `_usage_service.riyadh_reset_enabled()` else 0; `budget_exempt_async(user_id)` = `_usage_service._device_quota_exempt(user_id)` else the premium tier via `_get_user_tier_info` (unchanged). Deleted: the UTC-midnight fallback, `_RIYADH_OFFSET_HOURS` (private, no reader anywhere: grep), `EXEMPT_ENV`, `_EXEMPT_MAX_IDS`, `_UUID_RE`, `_exempt_ids`, `import re` (no other reader); the module docstring's seam paragraph and the two docstrings updated. Public names and signatures unchanged; the request_context import stays function-local; no needle string added. QM22 stays equivalent: `_get_user_tier_info` still catches every Exception and returns the free default.
- category_gate.py at HEAD: blob sha256 cd3a90b3f2a5216efd79642391111fab00dd1ab30c2f3af3381f965884fadadd (disk CRLF 97332ff705887648b609b3f0ba520808a9e83243290e3457ec19774bfc68a813).

## Pin rows (RB10-11 a) in tests/test_s81_s10_gate_rows.py (blob sha256 fff447ef46854cd3e7992462fa899f62739b4dbc5fa4c581b077e154229b3f5e, disk CRLF 47056816e2ff01a7a8c406d99bf706fc9996466fe05fb966eefadde3eff5aa05; 31 -> 36 nodes)
- a1 `test_rb10_a1_device_debit_refunded_on_post_resolve_refusal[post|stream]` (F1-15 / RB10-7 b2, the MEASUREMENT): the QB02 end-to-end harness with S81-09's REAL `consume_comparison_credit` / `refund_comparison_credit` behind the real routes, `ENABLE_DEVICE_DAILY_QUOTA` ON, the device header bound through the S81-05 middleware with `DEVICE_KEY_PEPPER` set; one Redis fake (the RED's FakeRedis + S81-09's two scripts emulated, keyed on usage_service's constants) shared by usage_service and the budget; the route's refund coroutine run to completion in the request. Measured GREEN at the rebased HEAD: consume EVAL keys [usage:daily:<uid>:<day>, usage:device:<device key>:<day>] reply (0, 1, 1); refund EVAL over the same keys reply (0, 0); both counters 0; one consume, one refund, one refusal INCR on both budget keys, nothing metered, no fetch / profile. NOT BLOCKED.
- a2 `test_rb10_a2_house_only_partner_keeps_its_other_stub[sync|stream]` (rv-m3): 'Kerastase Genesis Hair Mist' / 'Dior Homme' (and reversed), explicit path, flag ON, ENABLE_RESULT_STATUS_METADATA ON: decision proceed; product_categories [fragrances, other] / [other, fragrances]; category_used fragrances; identity_coherence True; no refusal EVAL.
- a3 `test_rb10_a3_reset_seam_follows_the_usage_window` (RB10-6): ENABLE_RIYADH_RESET ON at 2026-11-02T22:15:30Z (Riyadh day 11-03, reset 11-03T21:00Z) and 10:15:30Z (day 11-02, reset 11-02T21:00Z): reset_window == (_usage_window(now), 3); retry_fields' retry_after == ceil(seconds) and resets_at == S81-09's `_reset_instant_text(next, True)`; both budget keys carry the Riyadh day; `budget_state_async` with the gate clock frozen answers exactly (retry_after, resets_at) from ONE MGET of those keys; with S81-09's `RIYADH_UTC_OFFSET_HOURS` patched to 5 the gate follows (offset 5, the +05:00 window).
- first run of the new rows: see `s10rb-rows-new` below (5 passed).
- mutants (byte copies in place under .qa-mutation.lock, tools/mutants.py; each restored and sha256-compared equal; lock removed):
  - M-a1 (app/services/usage_service.py, rows -k rb10_a1): KILLED=True assertion=True failed=2 restored_sha_equal=True sha=570785b43ead06fa1c648cd7a4b27dabf17403c05386c7ffbae476279175e88c
    `[pyt] tag=s10rb-mut-m-a1 start=2026-11-02 17:08:21 end=2026-11-02 17:08:26 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\mut_M-a1.log`
  - M-a2-F12f (app/services/category_gate.py, rows -k rb10_a2): KILLED=True assertion=True failed=2 restored_sha_equal=True sha=97332ff705887648b609b3f0ba520808a9e83243290e3457ec19774bfc68a813
    `[pyt] tag=s10rb-mut-m-a2-f12f start=2026-11-02 17:08:26 end=2026-11-02 17:08:35 elapsed=9s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\mut_M-a2-F12f.log`
  - M-a3-local-offset (app/services/category_gate.py, rows -k rb10_a3): KILLED=True assertion=True failed=1 restored_sha_equal=True sha=97332ff705887648b609b3f0ba520808a9e83243290e3457ec19774bfc68a813
    `[pyt] tag=s10rb-mut-m-a3-local-offset start=2026-11-02 17:08:35 end=2026-11-02 17:08:40 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\mut_M-a3-local-offset.log`
  - M-a3-local-window (app/services/category_gate.py, rows -k rb10_a3): KILLED=True assertion=True failed=1 restored_sha_equal=True sha=97332ff705887648b609b3f0ba520808a9e83243290e3457ec19774bfc68a813
    `[pyt] tag=s10rb-mut-m-a3-local-window start=2026-11-02 17:08:40 end=2026-11-02 17:08:44 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\mut_M-a3-local-window.log`
  M-a1 = `device_keys = None` in usage_service.refund_comparison_credit (S81-09's device refund skipped); M-a2-F12f = apply_form_override_stubs' test widened from scan().fragrance_type to scan().evidence; M-a3-local-offset = the offset pinned to a local 3; M-a3-local-window = a local Riyadh window with a local 3-hour offset.

## Docs (RB10-11 b)
- rv-m1 the gate-rows header names the amended RED blob fe2032237c... (d988882a before EK1); the row map lists a1-a3.
- rv-m4 / rv-m5 in the S81-10 CLAUDE.md row (one physical line, ASCII): 'the resolver's own A2b when no chip or the chip `other` was sent'; 'WITH a real chip (not `other`)' and its complement 'WITHOUT a real chip (the camera always, text before S81-11)'; the camera budget limit reads 'the camera's budget refusal, an HTTP 200 action `error` body and never a 429, is never billed ...'. The same edits, L17 (rv-m2), the header (rv-m6) and the test_s80_b1 note are in PR_BODY.md.

## Gates at the rebased HEAD (every [pyt] line; one pytest at a time; tools/rb_driver.py launched ONCE + stand-alone runs)
Stand-alone runs (the new rows' first run, the four mutants, the unit re-runs after the LF write-back, one informational file):
```
[pyt] tag=s10rb-rows-new start=2026-11-02 17:07:43 end=2026-11-02 17:07:51 elapsed=8s bound=600s status=OK rc=0 log=...\S81-10_rebase\rows_new.log
    5 passed, 31 deselected, 11 warnings in 7.40s (tests/test_s81_s10_gate_rows.py -k rb10: the five new nodes, first run)
    [hermeticity] sentinel checked 5 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-mut-m-a1 start=2026-11-02 17:08:21 end=2026-11-02 17:08:26 elapsed=5s bound=600s status=FAIL rc=1 log=...\S81-10_rebase\mut_M-a1.log
    2 failed, 34 deselected, 11 warnings in 3.63s (mutant M-a1: KILLED, AssertionError, both a1 nodes)
[pyt] tag=s10rb-mut-m-a2-f12f start=2026-11-02 17:08:26 end=2026-11-02 17:08:35 elapsed=9s bound=600s status=FAIL rc=1 log=...\S81-10_rebase\mut_M-a2-F12f.log
    2 failed, 34 deselected, 10 warnings in 7.91s (mutant F12f: KILLED, AssertionError, both a2 nodes)
[pyt] tag=s10rb-mut-m-a3-local-offset start=2026-11-02 17:08:35 end=2026-11-02 17:08:40 elapsed=4s bound=600s status=FAIL rc=1 log=...\S81-10_rebase\mut_M-a3-local-offset.log
    1 failed, 35 deselected, 10 warnings in 3.41s (mutant local offset: KILLED, AssertionError, a3)
[pyt] tag=s10rb-mut-m-a3-local-window start=2026-11-02 17:08:40 end=2026-11-02 17:08:44 elapsed=4s bound=600s status=FAIL rc=1 log=...\S81-10_rebase\mut_M-a3-local-window.log
    1 failed, 35 deselected, 10 warnings in 3.39s (mutant local window: KILLED, AssertionError, a3)
[pyt] tag=s10rb-unit-off2 start=2026-11-02 17:45:32 end=2026-11-02 17:45:38 elapsed=6s bound=600s status=OK rc=0 log=...\S81-10_rebase\singles2\s10rb-unit-off2.log
    176 passed, 11 warnings in 5.13s (the RED 140 + the gate rows 36, ambient OFF, after the LF write-back)
    [hermeticity] sentinel checked 176 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-unit-on2 start=2026-11-02 17:45:38 end=2026-11-02 17:45:44 elapsed=6s bound=600s status=OK rc=0 log=...\S81-10_rebase\singles2\s10rb-unit-on2.log
    176 passed, 11 warnings in 5.22s (ambient ENABLE_FRAGRANCE_ONLY_GATE=true)
    [hermeticity] sentinel checked 176 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-persona start=2026-11-02 17:45:45 end=2026-11-02 17:45:48 elapsed=3s bound=600s status=FAIL rc=1 log=...\S81-10_rebase\singles2\s10rb-persona.log
    2 failed, 4 passed, 1 warning in 2.13s (tests/test_personalization_bundle_c.py, informational: not a member of the S81-10 set; the same two box failures the eaccd550 record holds)
    FAILED tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
    FAILED tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
```
The driver (phase A singles incl. the first unit runs that hit the CRLF artifact, phase B base chunks in wtb, phase C HEAD chunks), from rb_driver.log:
```
[pyt] tag=s10rb-unit-off start=2026-11-02 17:14:05 end=2026-11-02 17:14:12 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-unit-off.log
    1 failed, 175 passed, 11 warnings in 6.22s
    [hermeticity] sentinel checked 176 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
[pyt] tag=s10rb-unit-on start=2026-11-02 17:14:13 end=2026-11-02 17:14:23 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-unit-on.log
    1 failed, 175 passed, 11 warnings in 8.19s
    [hermeticity] sentinel checked 176 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
[pyt] tag=s10rb-s05-alone start=2026-11-02 17:14:23 end=2026-11-02 17:14:28 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-s05-alone.log
    176 passed, 61 warnings in 3.51s
    [hermeticity] sentinel checked 176 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-r8pair start=2026-11-02 17:14:28 end=2026-11-02 17:14:46 elapsed=18s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-r8pair.log
    273 passed, 1 warning in 16.75s
    [hermeticity] sentinel checked 273 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-metering start=2026-11-02 17:14:46 end=2026-11-02 17:14:50 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-metering.log
    21 passed, 13 warnings in 2.79s
    [hermeticity] sentinel checked 21 test(s)
    [netguard] blocked 2 attempt(s) from 2 node(s)
[pyt] tag=s10rb-s09 start=2026-11-02 17:14:50 end=2026-11-02 17:14:55 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-s09.log
    217 passed, 11 warnings in 3.66s
    [hermeticity] sentinel checked 217 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-g1 start=2026-11-02 17:14:55 end=2026-11-02 17:15:00 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-g1.log
    220 passed, 1 warning in 3.55s
    [hermeticity] sentinel checked 220 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-claudemd start=2026-11-02 17:15:00 end=2026-11-02 17:15:07 elapsed=7s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-claudemd.log
    79 passed, 1 warning in 5.19s
    [hermeticity] sentinel checked 79 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-ciorder start=2026-11-02 17:15:07 end=2026-11-02 17:16:43 elapsed=96s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\singles\s10rb-ciorder.log
    2903 passed, 4 deselected, 313 warnings in 93.82s (0:01:33)
[pyt] tag=s10rb-cb-00 start=2026-11-02 17:16:44 end=2026-11-02 17:17:32 elapsed=48s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-00.log
    732 passed, 3 skipped, 1 deselected, 22 warnings in 45.88s
[pyt] tag=s10rb-cb-01 start=2026-11-02 17:17:33 end=2026-11-02 17:18:41 elapsed=69s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-01.log
    1625 passed, 4 skipped, 6 deselected, 13 warnings in 66.79s (0:01:06)
[pyt] tag=s10rb-cb-02 start=2026-11-02 17:18:42 end=2026-11-02 17:19:17 elapsed=35s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-02.log
    535 passed, 2 skipped, 3 deselected, 10 warnings in 34.14s
[pyt] tag=s10rb-cb-03 start=2026-11-02 17:19:17 end=2026-11-02 17:20:32 elapsed=75s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-03.log
    2068 passed, 1 skipped, 5 deselected, 16 warnings in 73.47s (0:01:13)
[pyt] tag=s10rb-cb-04 start=2026-11-02 17:20:33 end=2026-11-02 17:21:07 elapsed=34s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-04.log
    422 passed, 13 warnings in 33.30s
    [hermeticity] sentinel checked 422 test(s)
    [netguard] blocked 13 attempt(s) from 2 node(s)
[pyt] tag=s10rb-cb-05 start=2026-11-02 17:21:07 end=2026-11-02 17:21:43 elapsed=36s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-05.log
    2 failed, 3679 passed, 23 skipped, 14 warnings in 34.08s
    FAILED tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
    FAILED tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
[pyt] tag=s10rb-cb-06 start=2026-11-02 17:21:43 end=2026-11-02 17:22:22 elapsed=39s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-06.log
    724 passed, 6 skipped, 8 deselected, 1 xfailed, 16 warnings, 2 errors in 37.63s
    FAILED tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    FAILED tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
[pyt] tag=s10rb-cb-07 start=2026-11-02 17:22:22 end=2026-11-02 17:25:14 elapsed=172s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-07.log
    2166 passed, 13 warnings in 168.16s (0:02:48)
    [hermeticity] sentinel checked 2166 test(s)
    [netguard] blocked 24 attempt(s) from 3 node(s)
[pyt] tag=s10rb-cb-08 start=2026-11-02 17:25:14 end=2026-11-02 17:26:39 elapsed=85s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-08.log
    2834 passed, 1 xfailed, 13 warnings in 82.50s (0:01:22)
[pyt] tag=s10rb-cb-09 start=2026-11-02 17:26:39 end=2026-11-02 17:27:53 elapsed=74s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-09.log
    858 passed, 8 skipped, 10 deselected, 16 warnings in 72.42s (0:01:12)
[pyt] tag=s10rb-cb-10 start=2026-11-02 17:27:53 end=2026-11-02 17:28:40 elapsed=47s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-10.log
    738 passed, 8 deselected, 35 xfailed, 13 warnings in 45.69s
[pyt] tag=s10rb-cb-11 start=2026-11-02 17:28:40 end=2026-11-02 17:29:03 elapsed=22s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_base\s10rb-cb-11.log
    889 passed, 10 skipped, 11 warnings in 20.87s
    [hermeticity] sentinel checked 899 test(s)
    [netguard] blocked 12 attempt(s) from 4 node(s)
[pyt] tag=s10rb-ch-secret start=2026-11-02 17:29:03 end=2026-11-02 17:29:17 elapsed=14s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-secret.log
    31 passed, 1 warning in 13.28s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-ch-00 start=2026-11-02 17:29:17 end=2026-11-02 17:29:58 elapsed=41s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-00.log
    2 failed, 776 passed, 3 skipped, 1 deselected, 21 warnings in 39.51s
    FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception
    FAILED tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
[pyt] tag=s10rb-ch-01 start=2026-11-02 17:29:59 end=2026-11-02 17:30:37 elapsed=38s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-01.log
    1216 passed, 5 deselected, 23 warnings in 36.94s
[pyt] tag=s10rb-ch-02 start=2026-11-02 17:30:37 end=2026-11-02 17:31:36 elapsed=59s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-02.log
    1008 passed, 1 skipped, 3 deselected, 11 warnings in 57.65s
    [hermeticity] sentinel checked 1009 test(s)
    [netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=s10rb-ch-03 start=2026-11-02 17:31:36 end=2026-11-02 17:31:56 elapsed=19s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-03.log
    416 passed, 1 skipped, 3 deselected, 13 warnings in 18.05s
    [netguard] blocked 11 attempt(s) from 5 node(s)
[pyt] tag=s10rb-ch-04 start=2026-11-02 17:31:56 end=2026-11-02 17:33:07 elapsed=71s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-04.log
    2019 passed, 1 skipped, 11 warnings in 69.40s (0:01:09)
[pyt] tag=s10rb-ch-05 start=2026-11-02 17:33:07 end=2026-11-02 17:34:08 elapsed=61s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-05.log
    1557 passed, 1 skipped, 5 deselected, 18 warnings in 59.92s
[pyt] tag=s10rb-ch-06 start=2026-11-02 17:34:08 end=2026-11-02 17:34:47 elapsed=39s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-06.log
    417 passed, 13 warnings in 37.42s
    [netguard] blocked 16 attempt(s) from 5 node(s)
[pyt] tag=s10rb-ch-07 start=2026-11-02 17:34:47 end=2026-11-02 17:34:59 elapsed=12s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-07.log
    435 passed, 1 skipped, 4 deselected, 12 warnings in 11.11s
    [hermeticity] sentinel checked 436 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10rb-ch-08 start=2026-11-02 17:34:59 end=2026-11-02 17:35:29 elapsed=29s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-08.log
    3650 passed, 22 skipped, 6 deselected, 4 warnings in 27.32s
[pyt] tag=s10rb-ch-09 start=2026-11-02 17:35:29 end=2026-11-02 17:36:08 elapsed=39s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-09.log
    2 failed, 681 passed, 3 skipped, 7 deselected, 16 warnings in 37.64s
    FAILED tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
    FAILED tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
[pyt] tag=s10rb-ch-10 start=2026-11-02 17:36:08 end=2026-11-02 17:37:36 elapsed=88s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-10.log
    616 passed, 4 skipped, 2 deselected, 1 xfailed, 12 warnings, 2 errors in 86.52s (0:01:26)
    FAILED tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    FAILED tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
[pyt] tag=s10rb-ch-11 start=2026-11-02 17:37:37 end=2026-11-02 17:39:17 elapsed=101s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-11.log
    964 passed, 260 warnings in 98.85s (0:01:38)
    [hermeticity] sentinel checked 964 test(s)
    [netguard] blocked 20 attempt(s) from 1 node(s)
[pyt] tag=s10rb-ch-12 start=2026-11-02 17:39:18 end=2026-11-02 17:41:30 elapsed=133s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-12.log
    4106 passed, 63 warnings in 130.14s (0:02:10)
    [hermeticity] sentinel checked 4106 test(s)
    [netguard] blocked 28 attempt(s) from 4 node(s)
[pyt] tag=s10rb-ch-13 start=2026-11-02 17:41:30 end=2026-11-02 17:42:46 elapsed=76s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-13.log
    1453 passed, 1 xfailed, 45 warnings in 74.31s (0:01:14)
[pyt] tag=s10rb-ch-14 start=2026-11-02 17:42:47 end=2026-11-02 17:43:40 elapsed=54s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-14.log
    800 passed, 8 skipped, 10 deselected, 19 warnings in 52.25s
[pyt] tag=s10rb-ch-15 start=2026-11-02 17:43:41 end=2026-11-02 17:44:15 elapsed=35s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-15.log
    553 passed, 8 deselected, 13 warnings in 33.53s
[pyt] tag=s10rb-ch-16 start=2026-11-02 17:44:16 end=2026-11-02 17:45:01 elapsed=45s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-16.log
    1245 passed, 10 skipped, 35 xfailed, 12 warnings in 43.88s
[pyt] tag=s10rb-ch-17 start=2026-11-02 17:45:01 end=2026-11-02 17:45:05 elapsed=4s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-10_rebase\comm_head\s10rb-ch-17.log
    85 passed, 1 warning in 3.15s
    [hermeticity] sentinel checked 85 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
```
- ruff --select E9,F63,F7,F82 --no-cache + py_compile on the 11 touched python files: ruff rc=0 / py_compile rc=0; JSON loads of the lexicon and the golden: OK (lint.log).
- jest (node / jest versions: v24.11.1 / 29.7.0), by path from SmartCompareApp through the junction (node_modules/@babel/core and .bin/jest present), one at a time under timeout 1800:
  - `[jest] tag=s10rb-fences-first2 start=2026-11-02 17:16:27 end=2026-11-02 17:16:33 rc=0`; Test Suites: 2 passed, 2 total; Tests:       25 passed, 25 total; Snapshots:   0 total
  - `[jest] tag=s10rb-fences12 start=2026-11-02 17:16:44 end=2026-11-02 17:16:53 rc=1`; Test Suites: 1 failed, 11 passed, 12 total; Tests:       4 failed, 211 passed, 215 total; Snapshots:   0 total
  - `[jest] tag=s10rb-jest-full start=2026-11-02 17:17:11 end=2026-11-02 17:17:30 rc=1`; Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total; Tests:       4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total; Snapshots:   42 passed, 42 total
  - fences: shareTruth.s74 + medicalNote.s74 first (2 / 2 PASS), then the other twelve: 11 PASS + config/nativeBundle.w37 FAIL on exactly d5, k2, k4, k5 (the accepted base drift). FULL suite once (LC-7): 3794 passed, 4 failed = the same four drift nodes, 13 skipped, 13 todo, 3824 total; 42 snapshots passed; no -u, no .snap written (status EMPTY).
- the pre-commit hook test files tests/test_precommit_hook*.py: NOT re-run (the rulings / task item 7): the re-verifier ran both halves green at 0e4b69e8: `[pyt] tag=s10rv-hook-notdash start=2026-11-02 16:03:49 end=2026-11-02 16:19:08 elapsed=919s bound=1800s status=OK rc=0` (167 passed, 160 deselected) and `[pyt] tag=s10rv-hook-dash start=2026-11-02 16:20:56 end=2026-11-02 16:39:50 elapsed=1134s bound=1800s status=OK rc=0` (157 passed, 3 skipped, 167 deselected); this round changes no .githooks file.
- tests/test_paid_route_metering.py: run ONCE, flag OFF (task item 7 overrides the generic with / without).

## Comm set (zero-regression gate)
- re-derived at the rebased HEAD with the GREEN's union-rule script (tools/build_comm_head.py; classes modsym, new-names, source-scan, named pins, data readers, CLAUDE.md readers, SmartCompareApp scanners, PC1-PC7, the spec-time 308): 429 members (+ tests/test_secret_scan_static.py ALONE = 430) = the 425 of specs/S81_10_COMM_SET.txt - tests/test_m6_c5_judgeme_html_reviews.py (deleted on main) + tests/test_s81_s09_device_quota.py (modsym, source-scan) + tests/test_s81_s09_gate_rows.py (modsym) + tests/test_s81_d08_jsonld_widen.py (modsym, source-scan, data-reader-grep) + tests/test_s81_g1_gate_rows.py (modsym) + tests/test_s81_s23_bypass_retire.py (source-scan, claude-md-reader). Excluded: the unit's own RED + gate rows (run in the unit gates), the 3 test_precommit_hook*.py matches, helpers / conftest. Lists: comm/comm_files.txt, comm/comm_reasons.tsv, comm/set430.txt.
- BASE at a513ea3b assembled per LC-6 (tools/base_assemble.py; base_assemble.tsv): 141 files REUSED from base_records/eaccd550.../406b86f4... (in its list, blob identical at eaccd550 and a513ea3b, text references none of G1's eight modules; their recorded failures: the two tests/test_auth_interceptor.py nodes); 289 files RUN at a513ea3b in the detached scratch worktree S81-10_rebase/wtb (no junction, no .env; reasons, overlapping: 278 reference a G1 module, 11 are not in the eaccd550 record, 5 are new or changed on main since eaccd550) in 12 chunks of <= 25 (s10rb-cb-00..11; 11 x 25 + 14); tests/test_secret_scan_static.py was among the reused (unchanged, no G1 module). Stored: harness/base_records/a513ea3b51a6b08d645547f4e260134fa8273d48/aec543268be8b304962e79e0d0069195edffa0ff4e9b2d1a8b7cf8252289469c.{txt,pyt.log,files}. Scratch worktree removed afterwards (see notes).
- HEAD: the 429 members in 18 chunks of <= 25 in sorted order (s10rb-ch-00..17; 17 x 25 + 4) + tests/test_secret_scan_static.py ALONE (s10rb-ch-secret: 31 passed); the four NETWORK_FLAKY nodes deselected both sides.
- HEAD failed (6): tests/test_auth_interceptor.py::test_sign_in_with_social_exception, tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully, tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- BASE failed (6): tests/test_auth_interceptor.py::test_sign_in_with_social_exception, tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully, tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- comm -13 (branch-only-new): EMPTY
- comm -23 (base-only): none
- the box's eight base failures: six of them are in this set (test_prompt_truth x2 cold tiktoken, test_auth_interceptor x2, test_page_scraping x2) and appear identically both sides (lists above); tests/test_personalization_bundle_c.py (the other two) is not a member of the S81-10 set by the union rule (it was a member of G1's 597-file set), so it was not run here.

## Added-line sweep
- round_commit: 268 added lines, hits {'eight_digit_run': 1}, non-ASCII chars 0 (8-digit runs = hex sha fragments: 8595378939)
- unit_vs_main: 5333 added lines, hits {'eight_digit_run': 3}, non-ASCII chars 22 (8-digit runs = hex sha fragments: 04982033, 04982033, 8595378939)
- the non-ASCII characters on added lines unit-vs-main sit on main's own Feature Flags pointer line (its existing em dashes, carried by the union line); CLAUDE.md's non-ASCII byte count is equal at main and HEAD.

## NOT MEASURED / not run
- the pre-commit hook test files (ruled not re-run; lines above).
- tests/test_paid_route_metering.py with the flag exported (ruled once, flag OFF).

## Deviations and observations
- D-1 (working copy): R06 failed in the first unit runs (s10rb-unit-off / -on, 175 / 176) ONLY because the rebase checkout wrote data/fragrance_lexicon.json with CRLF (no CR in the blob); after the blob bytes were written back the unit runs were repeated (s10rb-unit-off2 / -on2). The three LF-born working copies (lexicon, RED, golden) are LF again; status EMPTY; no content change.
- D-2 (RB10-3): main's dict-driven p01 branch does not assert that the import is function-local; the GREEN's own branch did. Dropped as RB10-3 directs; R55 (frozen) still pins the function-local import.
- D-3 (RB10-4 a): the pointer line keeps the S81-10 entry at the end of the session-81 entries, after main's S81-09 entry (merge order); RB10-4 (a) wrote 'right after the S81-15 entry', which S81-09's entry now occupies.
- D-4: pick 2 replayed without a conflict, so the sequencer committed it without the hook; the hook was run on its exact staged diff in a second scratch worktree (wth at 27cc9184 + `git read-tree 8e62ca04`), removed afterwards; and one `git add` (index stat refresh, no content) beyond the rebase's conflicted-file adds (D-1).
- D-5 (rv-m4 wording): besides the two named phrases, the complement 'WITHOUT a chip (the camera always, ...)' reads 'WITHOUT a real chip (...)' so the pair stays coherent; the canary sentence 'sent WITHOUT a chip (the camera's shape)' is unchanged (it is about sending none).
- the full jest suite ran concurrently with the base comm chunks (one jest and one pytest at a time, never two of either).

## Notes (running log)
```
# S81-10 rebase round notes (agent: Opus 5.5 rebase-and-gates)
- 16:48:25 AST start. Budget to ~18:48.
- worktree sc-s81-s10 branch feature/s81-s10-fragrance-only-gate HEAD 0e4b69e8065654293db548f0c114ff09714cf4e6, git status --short EMPTY (verified 16:50); no .qa-mutation.lock.
- frozen hashes at START (disk): fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e tests/test_s81_s10_fragrance_gate.py ; 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a tests/fixtures/s81_s10_flag_off_golden.json
- 16:51 fetch: origin/main = a513ea3b51a6b08d645547f4e260134fa8273d48; merge-base 6c14ac95; merge-tree: CONFLICT CLAUDE.md, app/middleware/error_handler.py, tests/test_s81_s05_request_context.py (= RB10-10); auto-merge image_routes, text_routes, structured_comparison_service.
- 16:53 rebase origin/main: pick 1 (0523a06f) conflicts in exactly the three; resolved by tools/resolve1.py (union in merge order; CRLF kept): error_handler 2 regions (S81-09 pair then S81-10 def; S81-09 USAGE_LIMIT block then S81-10 CATEGORY_NOT_LIVE block), +35 vs main = the branch's 35; s05 test 1 region (usage_service then category_gate in _ALLOWED_CTX_FILES; _GATE_CTX_ATTRS beside _USAGE_CTX_ATTRS; dict entry category_gate -> _GATE_CTX_ATTRS) + the auto-merged S81-10 per-file branch DROPPED (23 lines), +6 vs main; CLAUDE.md 2 regions (pointer line = main + the S81-10 entry after main's S81-09 entry (merge order); rows: S81-09 block, G1 block, blank, S81-10 block, blank, ## Tests), +5/-1 vs main.
- 16:54 hook by hand on staged pick 1: [hook] tag=s10rb-hook-pick1-staged start=2026-11-02 16:54:44 end=2026-11-02 16:54:57 rc=0 (All checks passed!)
- 16:55 rebase --continue: pick 1 -> 27cc9184; pick 2 (0e4b69e8) applied CLEAN -> 8e62ca04 (sequencer, no conflict). status EMPTY; diff --check rc 0 both commits; diff --stat origin/main...HEAD = the 14 expected files (5111+/4-).
- frozen blobs at 8e62ca04 (git show HEAD:path | sha256) = fe203223... / 159fadb8... (identical); disk now CRLF (git rewrote on the rebase checkout, core.autocrlf=true): disk 2541b5d7... / ff3b2e1b...; gate rows blob 4d44606e..., category_gate blob 9b2d6cc3...
- 17:14 unit OFF run: 1 failed / 175 passed: R06 test_r06_production_lexicon_content asserts no CR in data/fragrance_lexicon.json; the rebase checkout (core.autocrlf=true, no .gitattributes) re-wrote the LF-born working copies with CRLF (lexicon, RED file, golden); the blobs carry no CR (CI checks out LF).
- 17:16 wrote the committed blob bytes (LF) back to the three working copies (tools/lf_from_blob.py: asserted blob has no CR and disk == blob modulo CRLF; byte copies under lf_copies/), then git add of the same three paths to refresh the index stat (status showed ' M' from the size-only stat change with an EMPTY content diff); diff --cached --quiet rc 0, index blob ids == HEAD's, status EMPTY. Disk shas now = blobs: RED fe203223..., golden 159fadb8... (= start).
- 17:23 hook on pick 2: scratch worktree wth (detached 27cc9184, no junction) + read-tree 8e62ca04 (index only) => staged diff = pick 2 exactly (5 files 402+/7-); [hook] tag=s10rb-hook-pick2-staged start=2026-11-02 17:23:19 end=2026-11-02 17:23:31 rc=0 (All checks passed!); wth removed (worktree remove --force), gone from git worktree list.
- 17:29 base phase DONE (12 chunks, 289 files at a513ea3b; failures 4 = test_page_scraping x2, test_prompt_truth x2); base record STORED harness/base_records/a513ea3b51a6b08d645547f4e260134fa8273d48/aec543268be8b304962e79e0d0069195edffa0ff4e9b2d1a8b7cf8252289469c.{files 430, txt 6 failures (+ test_auth_interceptor x2 reused), pyt.log}
- 17:30 scratch worktree wtb removed (worktree remove --force; no junction inside; gone from git worktree list; directory gone).
- 17:31 PR body draft composed from tools/pr_template.md + tools/pr_gates.md + the compact native list (25,022 B with short placeholders); the Arabic table moved to S81_10_NATIVE_READ.md (for specs/, RB10-8).
- 17:45 HEAD phase DONE (18 chunks + secret alone 31 passed); HEAD failed 6 = base 6 (aec54326 record): branch-only-new EMPTY, base-only none.
- 17:45 unit re-runs after the LF fix: s10rb-unit-off2 176 passed OK; s10rb-unit-on2 176 passed OK; tests/test_personalization_bundle_c.py alone at HEAD (not a member of the S81-10 set): the same 2 box failures as the eaccd550 record (s10rb-persona FAIL rc=1, 2 failed / 4 passed).
- 17:48 PR_BODY.md composed: 25,485 B, ASCII, LF, no trailer.
```

## The round commit and the files for the orchestrator
- round commit 2c6875f3bda35ed00ac8c1f54f5b7552b6a9a46a through the hook (venv on PATH; never --no-verify; trailer Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>); commit_round.log:
  - `All checks passed!`
  - `[feature/s81-s10-fragrance-only-gate 2c6875f3] refactor(category-gate): S81-10 rebase round onto a513ea3b (RB10-6 seam collapse, RB10-11 pin rows)`
  - `[commit] start=2026-11-02 17:10:00 end=2026-11-02 17:10:13 rc=0`
- PR_BODY.md: 25485 bytes (<= 25,600; room for the orchestrator's trailer), pure ASCII, LF, no trailer; sha256 71fb5c5fed69a78793759b5c854709902028d667668e4eaf628e355aa5069c5b
- S81_10_NATIVE_READ.md (for specs/, RB10-8): the Arabic [NATIVE READ] table moved out of the PR body (UTF-8, 3259 bytes, sha256 2c94693839ef9c31b5955067fdaf2487994a46f42e82771f7d028a2801982760); the PR body keeps an ASCII list of the 43 terms with meanings and marks and points to it.
- the base record: harness/base_records/a513ea3b51a6b08d645547f4e260134fa8273d48/aec543268be8b304962e79e0d0069195edffa0ff4e9b2d1a8b7cf8252289469c.{files,txt,pyt.log}

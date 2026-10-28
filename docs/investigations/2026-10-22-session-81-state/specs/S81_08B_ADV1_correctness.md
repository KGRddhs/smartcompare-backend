# S81-08b LEGACY-FINGERPRINT-READER: adversary report, lens CORRECTNESS

- Unit: S81-08b (lane B backend, additive, FLAGGED ENABLE_LEGACY_FINGERPRINT_READER, default OFF, read per call).
- Agent: correctness adversary, model Opus 5.5 (claude-opus-5-5). Window 2026-10-29 00:42 - 01:20 AST.
- HEAD verified: 63f159efec41b08e875749c3b3f2b2f7035caa2e on feature/s81-s08b-legacy-fingerprint-reader (parent 86d5a24d = the base); unit worktree status EMPTY at start and end; never edited.
- RED file tests/test_s81_s08b_legacy_fingerprint.py: sha256 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 at start AND end (unit worktree, LF, 45,921 B) = the frozen sha. Note: a fresh autocrlf checkout of the commit gives a CRLF working copy (sha 9436574d..., 47,121 B) whose LF form is 2f4f8237; I copied the exact LF bytes into my scratch before every run.
- Authorities read in full: s81-common.txt (twice), PLAN_S81 (context, standing constraints, VERIFY quota/auth, client lane, flip order), PLAN_S80 sections 0 and 1, GATE_S81_08B, RULINGS_S81_08B, the spec, the spec review, the GREEN report + PR body, the RED file (all 1,200 lines), the diff.
- All probes and mutants ran in MY OWN detached scratch worktree <S>/S81-08b_adv_correctness (git worktree add --detach at 63f159ef; no node_modules; .qa-mutation.lock held during every swap; removed with git worktree remove --force; absent from git worktree list). <S> = the orchestrator scratchpad the task names (the folder that holds harness/pyt.py).
- This report and notes.md were written THROUGH THE SHELL (python heredoc; the harness refuses a subagent Write of a report .md). Scripts/fixtures written with the Write tool: adv_mutate.py, adv_mutants.json, test_zz_s08b_adv_probe.py (scratch only, never in the unit worktree).

## Verdict: SOUND (0 blocking, 0 major, 7 minor)

The GREEN code is correct at runtime on every axis of the lens, measured, not read:
- flag-OFF and flag-ON-no-header identity under the FULL configuration: a base-vs-HEAD differential probe (the 86d5a24d module swapped into the scratch, then restored sha-verified) over 560 register/social/OpenAPI observations: all 539 expected-identical observations are IDENTICAL in status, body, the ordered DB call list, updates, admin-factory count, EVERY app.* log record and the OpenAPI sha (flag unset/'false'/'garbage'/'true'/' TRUE '/'on' x 12 header shapes x 3 seeds at register; W3-3 unset/true x 6 flags x 7 header shapes x own hash NULL/LEG/NEW/OTHER at social; the admin factory raising); the 21 expected-diff observations (flag ON + a valid distinct legacy, register; + W3-3 ON + own NULL, social) differ ONLY in calls/updates/logs, never in status/body/factory.
- the GC-2 dual read at both sites: select 'lifetime_comparisons_used, device_fingerprint_hash', in_ [fp, legacy] in that order, order desc=True as a keyword, limit(1); the update stores NEW only on the caller's row with max(floor, matched) (leg-max -> 3 top=legacy, new-max -> 5 top=new, empty -> 0 top=none; social own 2 + LEG 3 -> 3). postgrest 2.31.0 renders it (offline, no execute) as select=lifetime_comparisons_used,device_fingerprint_hash&device_fingerprint_hash=in.(NEW,LEG)&order=lifetime_comparisons_used.desc&limit=1.
- no upgrade-on-match: own hash LEG / NEW / OTHER at social -> the 5-call own read only, no write, identical to base, flag ON included.
- silent drop: upper / 63 / 65 / empty / non-hex / equal-NEW legacy, legacy without a valid NEW: identical to base incl. every log record.
- except-arm typing: 8 exception types (RuntimeError, ValueError, KeyError, TypeError, OSError, TimeoutError, httpx.ConnectError, postgrest APIError, each message carrying NEW and LEG) on the dual READ and on the UPDATE at both sites: 32/32 -> 200 + the unchanged body, exactly one WARNING '[LEGACY-FP] site=<site> inherit failed: <Type>', no base 'device-fp inheritance failed' line, no write, no value in any record.
- no NEW / LEG / NEW.upper / LEG.upper / UID in any app log record of any HEAD observation (592).
- error-handler mapping, billing R-A3, contract freeze (PLAN_S80 section 0): the diff touches only CLAUDE.md, app/api/auth_routes.py and the RED file (git diff --name-only); no raise, status, code, response key or OpenAPI change (probe: status/body/OpenAPI sha identical in every scenario); the W4-13 flag-OFF ledger, the KB IDENTITY_NODES and FY25 pins green at HEAD (534 passed).
- every spec mutant M1-M20 re-applied by hand on sha-verified byte copies: 20/20 KILLED (AssertionError), plus 8 of my own (N4-N9, N11, N14) KILLED; M17-M20 are the gate-assigned (R-S08B-7) social / share / SAME_DEVICE / cap rows.

What is NOT proven by the committed pins (all minors, the code itself measured correct): five non-equivalent mutants of my own SURVIVE all 85 rows (and pin set A, 599 passed, for N1-N3): N1 (the dual except narrowed to RuntimeError), N2 (the dual update executed outside the try), N3 (an untagged register INFO line on the drop path, flag OFF too), N3b / N3c (a register / social INFO line carrying the RAW legacy header value on the drop path, flag OFF too; under N3b 39 of 222 register probe observations log the legacy VALUE, flag unset included). See m1 / m2.

## Findings

### Blocking: none. Major: none.

### Minor (documentation / pin-strength rulings for the orchestrator)

- m1 (pins vs the identity claim; CLAUDE.md row + PR body overclaim). The row says "Flag OFF, or ON without the legacy header (build 3), or ON with an invalid or primary-equal one: byte-identical (the same DB calls, response bodies and log lines; literal call-list pins REG_BASE / SOCIAL_BASE_NULL / SOCIAL_BASE_OWNED ..., P1-P7)"; the PR body says the same ("same DB calls, bodies and log lines; literal call-list pins P1/P2/P5/P7"); the commit says "byte-identical (the P1-P7 call-list pins)". Measured: P1-P7 (and P4/P6) assert only `_tagged(caplog) == []` (no record containing '[LEGACY-FP]'), and the R6 value sentinel `_assert_no_values_logged` runs only in R3-R9 (valid-legacy scenarios). So N3 (register logs an untagged 'device-fp legacy key unused' INFO whenever legacy is None, flag OFF included), N3b (register logs the RAW X-Device-Fingerprint-Legacy value when it is dropped) and N3c (the same in the social apply) all SURVIVE 85/85 rows (N3 also set A, 599 passed); under N3b my probe sees the legacy VALUE (a device identifier) in an app log record in 39 of 222 register observations, flag unset included. The runtime truth of the GREEN bytes is fine (my differential probe: every app.* record identical to base in all 539 identity scenarios, no value anywhere), so this is not a code defect: the log-line half of the identity and the 'no log line carries a value' / R-S08B-6 'dropped SILENTLY' properties are pinned on the helper (R2 noisy == [] for the AUTH_LOGGER only) and on the dual path (R6), not on the route-level drop paths. Ruling options: (a) reword the row / PR body / commit to "the same DB calls and response bodies (literal call-list pins P1-P7) and no [LEGACY-FP] line; the full log-record identity was measured base-vs-HEAD by the correctness adversary (539 scenarios), not pinned", or (b) a follow-up pin (outside the frozen RED file): run `_assert_no_values_logged` in P1-P7 and compare the full app.* record list with a base-recorded literal.

- m2 (pins vs the failure table; except-arm typing). Spec 2.2 point 5 / 2.5 ("dual read or update raises -> WARNING type name; ... no inheritance write") and the row ("a failure one WARNING ... <Type> (the type name only; the response unchanged)", "the dual function never raises into it"). R9 raises only RuntimeError, only on the dual READ (raise_on={'in_'}). N1 (`except RuntimeError` instead of `except Exception`) and N2 (the update built inside the try, executed after it) SURVIVE 85/85 rows and set A (599). Under N1 a postgrest APIError / httpx error from the dual read would reach the register except arm, which logs str(exc) (the query-echo exposure spec 2.2 point 5 exists to prevent); under N2 an update failure would. Runtime truth of the GREEN bytes: correct for 8 types x read/update x both sites (32/32). Ruling: a follow-up parametrized pin over op in {in_, update} x {RuntimeError, APIError, httpx.ConnectError} at both sites (outside the frozen file), or record as a stated pin limit.

- m3 (canary text, CLAUDE.md row + PR body owner steps). "Canary after the OTA: a re-signup on a pre-OTA test device with no OS update since its first registration logs [LEGACY-FP] site=register top=legacy and inherits the old counter." Measured: migration 043 (delete_user_cascade) sets users.device_fingerprint_hash = NULL and lifetime_comparisons_used = 0 on the deleted account, and only /register (or the W3-3 social apply, production state UNKNOWN) ever stores a hash. A canary run as delete-then-re-register (the natural reading of 're-signup') reads top=none and inherits nothing at base AND at HEAD, a false negative that could prompt a needless rollback or OTA hold. Add: the pre-OTA account must still exist (not deleted) and must have been created by EMAIL register on that device (a Google/Apple account has a NULL hash unless W3-3 was ON), and the canary registers a SECOND account.

- m4 (stakes sentence precision). "the inherited lifetime counter gates only the lifetime-free branch and the /usage/status lifetime figure": usage_service._usage_status_body also reports remaining.daily / remaining.monthly as the FULL allowance while on_lifetime_free, so the inherited counter moves those two /usage/status figures too (no counter changes; display only). Suggest "... the lifetime-free branch (and with it the /usage/status lifetime and remaining figures)".

- m5 ('the highest lifetime_comparisons_used first' vs NULLS FIRST; GREEN Q2). postgrest renders order=lifetime_comparisons_used.desc (no nullslast) and PostgreSQL sorts NULLs FIRST on DESC; the column is nullable (011: INT DEFAULT 0). A NULL-counter row on either hash would be returned first and read as 0, shadowing a higher counter in the other hash group (the base read has the same property within the NEW group; the dual read widens it across the two groups). Practically unreachable (default 0, 043 writes 0, the 011 RPC uses COALESCE). The RED FakeDB sorts NULL as 0 (diverges from PostgreSQL), so no pin sees it. GC-2 binds desc=True exactly, so no code change here: a stated-limit sentence or an S81-09 note.

- m6 (GREEN report figure). "slice 6,558 chars" is the CRLF character count; R11 reads CLAUDE.md with read_text (universal newlines) and sees 6,551 chars. Both under the 8,000 cap; trivial.

- m7 (prove-nothing run presented as a gate). "unit file HEAD, flag ON exported: 85 passed" (GREEN report + PR body) is identical to the OFF run by construction: the RED autouse fixture `_unit_flag_unset` deletes the flag before every row and every row sets the flag itself. Mine (s08b-advc-unit-on) likewise. The meaningful flag-ON sweeps are the A + B (+ kb) runs.

## Runs (bounded runner pyt.py, shared .venv-qaren, one pytest at a time, scratch worktree at the exact bytes)

| run | result | [hermeticity] / [netguard] | [pyt] |
|---|---|---|---|
| RED file, flag unset | 85 passed | 85 / 0 from 0 | `[pyt] tag=s08b-advc-unit-off start=2026-10-29 00:49:50 end=2026-10-29 00:49:59 elapsed=9s bound=600s status=OK rc=0` |
| RED file, ENABLE_LEGACY_FINGERPRINT_READER=true exported (prove-nothing, m7) | 85 passed | 85 / 0 from 0 | `[pyt] tag=s08b-advc-unit-on start=2026-10-29 00:50:05 end=2026-10-29 00:50:10 elapsed=4s bound=600s status=OK rc=0` |
| differential probe at HEAD (5 nodes, scratch-only file) | 5 passed | 5 / 0 from 0 | `[pyt] tag=s08b-advc-probe-head start=2026-10-29 00:59:37 end=2026-10-29 00:59:48 elapsed=10s bound=600s status=OK rc=0` |
| differential probe, base 86d5a24d module swapped in | 5 passed | 5 / 0 from 0 | `[pyt] tag=s08b-advc-probe-base start=2026-10-29 01:00:00 end=2026-10-29 01:00:11 elapsed=10s bound=600s status=OK rc=0` |
| sets A + B (21 files), flag ON exported | 1260 passed, 1 skipped | 1260 / 48 from 14 | `[pyt] tag=s08b-advc-AB-on start=2026-10-29 01:04:31 end=2026-10-29 01:05:12 elapsed=41s bound=1200s status=OK rc=0` |
| test_w4_13_flag_off_ledger + test_s81_kb_schema + test_s75_fanout_identity, flag unset | 534 passed | 534 / 0 from 0 | `[pyt] tag=s08b-advc-ledger-kb start=2026-10-29 01:08:17 end=2026-10-29 01:08:26 elapsed=10s bound=600s status=OK rc=0` |
| probe under N3b (-k "probe_register or zz_write") | 2 passed, 3 deselected | 2 / 0 from 0 | `[pyt] tag=s08b-advc-probe-n3b2 start=2026-10-29 01:10:52 end=2026-10-29 01:10:56 elapsed=4s bound=600s status=OK rc=0` (a first try deselected the writer: `[pyt] tag=s08b-advc-probe-n3b start=2026-10-29 01:10:34 end=2026-10-29 01:10:39 elapsed=4s bound=600s status=OK rc=0`, no output, re-run) |
| RED file at BASE (base module + base CLAUDE.md swapped in) | 14 failed (AssertionError only: R1-R11) / 71 passed | 85 / 0 from 0 | `[pyt] tag=s08b-advc-red-at-base start=2026-10-29 01:12:07 end=2026-10-29 01:12:12 elapsed=5s bound=600s status=FAIL rc=1` (the expected RED) |

Lint at the exact bytes: py_compile rc 0 (auth_routes.py, the RED file); ruff 0.16.5 --select E9,F63,F7,F82 (the CI blocking tier, ci.yml:170 and the hook): All checks passed!; the full [tool.ruff.lint] set (report-only in CI): 24 findings in auth_routes.py at HEAD = 24 at base (B008 x15, W293 x5 at :340-357/:1133, B904 x3, F841 :1132), none on an added line; .github/black-clean-paths.txt names neither file. Added-line bytes: auth_routes +120/-7, 0 bytes > 127 added, CRLF 1650 -> 1763, 0 LF-only, size 67,765 -> 73,488 (= the GREEN figures); CLAUDE.md +9/-2 (the two replaced lines gain a pure-ASCII 280-char and 168-char fragment and lose nothing), CRLF 968 -> 975, bytes > 127 3,937 -> 3,937.

## Mutation table (my own scratch, byte copy -> one exact-string edit matching once -> the full RED file -> restore -> sha256 compare; lock held)

| # | mutant | killing rows (AssertionError) | [pyt] (bound 600) |
|---|---|---|---|
| M1 | flag reader returns True | R1, R2, P1 x7, P5 | advc-M1 00:53:38-00:53:43 5s FAIL rc=1 |
| M2 | no .strip().lower() | R1 | advc-M2 00:53:43-00:53:48 5s FAIL rc=1 |
| M3 | fullmatch -> match | R2 | advc-M3 00:53:48-00:53:53 5s FAIL rc=1 |
| M4 | raw == fp dedupe removed | R2, P3 equal-new, P7 equal-new | advc-M4 00:53:53-00:53:58 5s FAIL rc=1 |
| M5 | dual update stores legacy | R3, R4, R5 x2, R8 x2 | advc-M5 00:53:58-00:54:03 5s FAIL rc=1 |
| M6 | in_ [legacy] only | R3, R4, R5 x2, R8 x2 | advc-M6 00:54:03-00:54:08 5s FAIL rc=1 |
| M7 | dual desc=False | R3, R4, R5 x2, R6, R8 x2 | advc-M7 00:54:09-00:54:14 5s FAIL rc=1 |
| M8b | guarded header read before the flag read | R2 (OFF reads no header), R10 | advc-M8b 00:54:14-00:54:19 5s FAIL rc=1 |
| M9 | INFO formats the legacy value | R3, R4, R5 x2, R6, R7, R8 x2 | advc-M9 00:54:19-00:54:24 5s FAIL rc=1 |
| M10 | dual except re-raises | R9 x2 | advc-M10 00:54:24-00:54:29 5s FAIL rc=1 |
| M11 | social continues past an own hash when legacy is present | P5 on-own-legacy, on-own-new | advc-M11 00:54:29-00:54:36 6s FAIL rc=1 |
| M12 | register consults legacy without a valid NEW | P4 x4 (register, flag true) | advc-M12 00:54:36-00:54:41 5s FAIL rc=1 |
| M13 | register always dual | P1 x7, P2 x6, P3 x6 | advc-M13 00:54:41-00:54:47 6s FAIL rc=1 |
| M14 | legacy-held max labelled new | R6, R7 | advc-M14 00:54:47-00:54:52 5s FAIL rc=1 |
| M15 | no update when no rows | R8 no-rows | advc-M15 00:54:53-00:54:58 5s FAIL rc=1 |
| M16 | social dual floor=0 | R5 own6-floor | advc-M16 00:54:58-00:55:04 7s FAIL rc=1 |
| M17 | social_login applies when the legacy flag is ON whatever W3-3 says | P6 x2 | advc-M17 00:55:04-00:55:09 5s FAIL rc=1 |
| M18 | share forwards the legacy header when the body omits it (referral_routes copy) | R10, P8 body-absent x2 | advc-M18 01:06:48-01:06:53 5s FAIL rc=1 |
| M19 | _load_invitee selects the hash (referral_service copy) | P11 x2 | advc-M19 01:06:53-01:06:58 5s FAIL rc=1 |
| M20 | cap function .in_ [fp, fp] (referral_service copy) | P12 x2 | advc-M20 01:06:58-01:07:03 5s FAIL rc=1 |

### My own mutants (lens: GC-2 at both sites, no upgrade-on-match, silent drop, identity under FULL config, except-arm typing, contract freeze, values in logs)

| # | mutant | result | evidence |
|---|---|---|---|
| N1 | dual `except Exception` -> `except RuntimeError` | SURVIVED (85/85; set A 599 passed) | advc-N1 00:55:10-00:55:15 5s OK rc=0; advc-N1A 00:56:38-00:56:59 21s OK rc=0 (m2) |
| N2 | dual update built in the try, `.execute()` after it (an update failure escapes) | SURVIVED (85/85; set A 599) | advc-N2 00:55:15-00:55:19 4s OK rc=0; advc-N2A 00:56:59-00:57:20 21s OK rc=0 (m2) |
| N3 | register logs an untagged INFO whenever legacy is None (flag OFF too) | SURVIVED (85/85; set A 599) | advc-N3 00:55:20-00:55:24 4s OK rc=0; advc-N3A 00:57:20-00:57:41 21s OK rc=0 (m1) |
| N3b | register logs the RAW legacy header value when it is dropped | SURVIVED (85/85); runtime: legacy VALUE in an app record in 39/222 register observations, flag unset incl. | advc-N3b 01:10:05-01:10:10 5s OK rc=0 (m1) |
| N3c | social apply logs the RAW legacy header value when it is dropped | SURVIVED (85/85) | advc-N3c 01:10:10-01:10:14 4s OK rc=0 (m1) |
| N4 | legacy header declared as a FastAPI Header param on register | KILLED by P10 x2 | advc-N4 00:55:24-00:55:29 5s FAIL rc=1 |
| N5 | upgrade-on-match: rewrite every LEG-hash sibling to NEW | KILLED by R3, R4, R5 x2, R8 x2 | advc-N5 00:55:29-00:55:34 5s FAIL rc=1 |
| N6 | INFO carries the user id | KILLED by R3, R4, R5 x2, R6, R7, R8 x2 | advc-N6 00:55:34-00:55:39 5s FAIL rc=1 |
| N7 | failure logged at ERROR | KILLED by R9 x2 | advc-N7 00:55:39-00:55:45 5s FAIL rc=1 |
| N8 | flag ON + ABSENT legacy still dual-reads (derived key) | KILLED by R2, P2 x6, P7 x6 | advc-N8 00:55:45-00:55:50 5s FAIL rc=1 |
| N9 | social passes (legacy, fp) swapped: in_ [LEG, NEW], stores LEG | KILLED by R5 x2, R7 | advc-N9 00:55:50-00:55:55 5s FAIL rc=1 |
| N11 | a comment inside the base _inherit_device_counter | KILLED by P13 | advc-N11 00:55:55-00:56:00 5s FAIL rc=1 |
| N14 | the helper gated on the W3-3 flag instead of its own (B1: FULL config) | KILLED by R2, R10, P1 x7, P5 | advc-N14 00:56:00-00:56:05 5s FAIL rc=1 |

Every kill above is an AssertionError (M10 / N-rows included: pytest reports 'assert not True' for R9). Every restore sha256-matched the pre-mutation copy (adv_mutants_result.json, adv_mutants_m18_20_result.json, adv_mutants_survivors_setA_result.json, adv_mutants_n3bc_result.json: restore_ok true for all 36 runs). Equivalent survivors: none (N1, N2, N3, N3b, N3c each change behaviour: shown at runtime for N3b; N1 / N2 by construction for a non-RuntimeError / an update failure, which my probe shows the GREEN code handles).

## Claim checks (CLAUDE.md row, Auth bullet, Feature Flags pointer, GREEN report, PR body) against the code at runtime

| claim | verdict | evidence |
|---|---|---|
| flag read per call as the FIRST statement of `_read_valid_legacy_fingerprint`; OFF reads no header beyond today's | TRUE | R1/R2/R10 green; M2, M8b, N14 killed; probe identity incl. flag spellings |
| ON: valid primary AND valid distinct legacy -> ONE read IN (primary, legacy), highest first, one row | TRUE (NULLS FIRST caveat m5) | probe calls literal; postgrest render |
| write = the caller's own row, stores PRIMARY, never legacy; no stored row rewritten; a social own hash kept; max(own, matched) | TRUE | probe updates (NEW only, eq id UID); own LEG/NEW/OTHER -> 5-call read, no write |
| invalid / empty / absent / equal legacy ignored SILENTLY, base path runs; legacy without a valid primary matches nothing | TRUE at runtime; pinned only partly (m1) | probe: every app.* record identical to base; N3/N3b/N3c survive |
| one INFO `[LEGACY-FP] site=... top=...` per dual read; a failure one WARNING with the type name; no value logged; no response/status/header/OpenAPI change | TRUE at runtime; failure typing pinned for RuntimeError-on-read only (m2) | probe 21 dual + 32 failure observations; OpenAPI sha identical |
| social half reachable only with ENABLE_SOCIAL_DEVICE_FINGERPRINT ON; its production state UNKNOWN (no dated ledger line names it) | TRUE | probe w33 unset -> no DB call; grep of every */ledger.md under docs/investigations: 0 hits for the name (only OWNER_ACTIONS_S81 item 5 asks for it) |
| flag OFF / ON-no-header / ON-invalid-or-equal byte-identical "(the same DB calls, response bodies and log lines; literal call-list pins ... P1-P7)" | behaviour TRUE; the pin attribution OVERCLAIMS for log lines (m1) | probe 539/539 identical; P1-P7 assert only no tagged record |
| stakes: daily/monthly counters unaffected; the inherited counter gates only the lifetime-free branch and the /usage/status lifetime figure | MOSTLY (m4) | usage_service :355 / _usage_allowed_body / _usage_status_body (remaining daily/monthly follow on_lifetime_free) |
| activation: OWN step right after deploy, before the first OTA, may precede approval (ON without the header byte-identical for build 3), independent of and earlier than ENABLE_REQUEST_CONTEXT_HEADERS; precondition the DATED ledger line; rollback unset | TRUE (matches R-S08B-2 / GC-7) | probe flag-ON-no-header identical to base under CTX ON; R11 green, forbidden phrase absent |
| canary: a re-signup on a pre-OTA device logs top=legacy and inherits | INCOMPLETE (m3) | 043 NULLs the hash and zeroes the counter on deletion |
| stated limits (1)-(10), the GC-9 list + R-S08B-10 additions | PRESENT | row text; (9) reasoned; (10) the RED's 241-file base |
| Auth bullet :231 and Feature Flags pointer :341 (after the S81-04 pointer) | TRUE, pure-ASCII insertions, nothing removed | byte check of the two replaced lines |
| row placement: after the newest session-81 row on main (S81-14), before `## Tests` | TRUE | SESSION 81 order D03, S81-03, ST1, S81-05, S81-04, S81-14, S81-08b; R11 slice ends at `
## Tests` |
| GREEN: +120/-7, 67,765 -> 73,488, CRLF 1,650 -> 1,763, 0 LF-only, 175 -> 175 bytes > 127; CLAUDE.md +9/-2, 525,719 -> 532,726, 968 -> 975 | TRUE | measured |
| GREEN: row slice 6,558 chars | CRLF count; R11 sees 6,551 (m6) | measured |
| GREEN: first gate 14 failed (AssertionError only) / 71 passed; sets A 599, B 661+1 | TRUE | its gate1 log (14 x AssertionError) and my own RED-at-base re-run |
| GREEN / PR: 20 / 20 spec mutants KILLED, the killing rows as listed | TRUE | my re-application (M11 also kills on-own-new with my edit; M18 also R10) |
| GREEN / PR: node counts RED 14, PIN 71 (P1 x7 ... P14 x2 + r6pre) | TRUE | file read |
| GREEN: 'unit file HEAD, flag ON exported' as a gate | prove-nothing (m7) | autouse `_unit_flag_unset` |
| GREEN rebase note: S81-06 does not touch auth_routes; re-apply the :341 pointer and the row anchor by hand | TRUE | git diff 86d5a24d a8f01379: only sentry_service.py (+15, AnthropicIntegration) and tests/test_s81_s05_request_context.py (+32, llm_router as a request_context consumer) among the unit-relevant files; P9 and the s05 pins must re-run at the rebased HEAD (they are in the comm set) |
| commit: parent 86d5a24d, trailer `Co-Authored-By: Claude Opus 5.5`, three files only | TRUE | git log / git diff --name-only |

## Prove-nothing rows (and low-power rows)

1. The 'RED file, flag ON exported' run (GREEN's and mine): identical to the OFF run by construction (the autouse `_unit_flag_unset`); listed in the GREEN report and PR body as a gate (m7).
2. P9 x4 (Sentry redaction of the legacy header): exercises only untouched sentry_service code (any header off the allowlist ships [Filtered]); green at base and HEAD by construction; no auth_routes defect can fail it (a guard against a future allowlist widening, not evidence for this unit's code).
3. P11 x2, P12 x2: scope pins over untouched referral_service functions; they fail only for an edit of that file (M19 / M20 on copies), i.e. they restate what `git diff --name-only` shows; nothing about auth_routes.
4. The `_tagged(caplog) == []` assertions of P1-P7 as evidence for 'the same log lines' / 'no value logged' on the drop paths (m1: N3, N3b, N3c survive).
5. R9 as evidence for the failure table beyond 'RuntimeError on the dual read' (m2: N1, N2 survive).
6. Low power, not vacuous: the eight flag-'false' P4 nodes (no single mutant reaches them: M1 does not, the helper is never called without a valid NEW; only a double mutant M1+M12 would) and R11's generic words (register, social, rollback, ledger, independent, reasoned; the unique tokens carry the row check).

## Questions for the gate

- Q1 (m1, m2): rule the five surviving mutants: (a) accept as stated pin limits and reword the identity sentence of the row / PR body / commit (the log-line identity measured, not pinned), or (b) add a small follow-up pin file (the RED file is frozen): `_assert_no_values_logged` + a base-recorded app.* record literal in the P1-P7 scenarios, and R9 parametrized over op {in_, update} x {RuntimeError, postgrest APIError, httpx.ConnectError} at both sites. My differential probe file (scratch: test_zz_s08b_adv_probe.py, synthetic values only) is a ready template for (b).
- Q2 (m3): amend the canary sentence (row + PR body owner steps): keep the pre-OTA EMAIL-registered account (043 deletion NULLs the hash and zeroes the counter), register a second account on that device.
- Q3 (m5, GREEN Q2): a NULLS-FIRST stated-limit sentence now, or an S81-09 note only.

## NOT MEASURED

- The comm set (engineering lens; I re-derived nothing there). The pre-commit hook test files (no .githooks change). Any database (the partial-index claim stays reasoned). The rebased HEAD (the rebase onto a8f01379 is the orchestrator's next step). Response HEADERS were not captured by the differential probe (the diff writes none; the RequestID header is random per request).

## Hygiene

- Unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b: never written; HEAD 63f159ef and `git status --short` empty at start and end; no .qa-mutation.lock; RED sha 2f4f8237 at start and end; auth_routes.py f49c4b95 and CLAUDE.md 6a52dd06 unchanged.
- Scratch worktree <S>/S81-08b_adv_correctness: created 00:44 (git worktree add --detach ... 63f159ef), sha-verified against the unit worktree before (auth_routes f49c4b95, CLAUDE.md 6a52dd06, referral_routes 00f624f2, referral_service 3e93b86e, RED after the LF byte copy 2f4f8237) and after the last restore (the same five shas; `git diff --stat` empty); my probe file deleted from it after use; removed 01:12 with `git worktree remove --force` (no node_modules, no junction), absent from `git worktree list`, directory gone.
- Every swap (36 mutant runs, the base-module probe, the N3b probe, the RED-at-base run) held <scratch>/.qa-mutation.lock and restored from a byte copy with a sha256 match; no lock remains. No orphan pytest (process scan by tag / path: none). No package manager, no .env, no network, no secret value read or printed; synthetic values only (sha256 of fixed byte strings, nil-shaped uuids, example.com).

## Files written (all under <S>/S81-08b_adv/, sha256 over the bytes on disk; pure ASCII, LF)

- correctness_REPORT.md (this file; its sha256 is returned in the structured output)
- notes.md eca734a8f36630c46d950c688551c88fead4a5fb94becb61bf5d9f5d68ede65e (the running notes; final append before this report)
- adv_mutate.py c5992c3b3e8670c0d1c0c41115cb9333296ca0563686d61eae4afe01dd68f18f (the mutation harness)
- adv_mutants.json ab905724c4dbda87cb4b74872fd4b1581055ae105e45a98b5e38aaa9042d7f1b; adv_mutants_m18_20.json aef5aa755b50fd3bf4bcdd4a1b55bf9994e9f5adb364c12980ed0bf2e71df410; adv_mutants_n3bc.json 9c878609deaea6ecdd7a824f9f2cc0aa37b2a459c87d913a3fcf9e1ef37d9904; adv_mutants_survivors_setA.json 81b8cdfdfa82264dce778a00393823f38aeb644f7e53204240c34382230a2eb5
- results: adv_mutants_result.json 53113b3e5c0de9bbe3d3c5012250b7afaed51dac94ae905af2cd188d4e90b954; adv_mutants_m18_20_result.json 52f8ea642abf0d21d2277ace1852f838268f73eb08f839e990f8086929375f14; adv_mutants_n3bc_result.json 75ea7a7bc8477726c435855d0e341526a489e782dcfb83c0b9079ef7bf1372f6; adv_mutants_survivors_setA_result.json e7d2c0e64667f4fa5d5c6060a42611cc99f740b09b20d74360d11b0037f3c087
- test_zz_s08b_adv_probe.py 9e4609573cf2a6170e1493abc6dfb7e99d8ee9959e963649f0c770f2bb7042ad (the differential probe; scratch only, never in a repo)
- probe_head.json d938a6c2db3468022941cecb838457de5d0d1edd2e4b243d1a1935c43f507d6b; probe_base.json 93abf6377531c1c9de330133dedcbf1dbfead38ec31688339a56c38ee09a8bbe; probe_n3b.json b085f93000b13d6d5d591ef314200129ffaab6db6e16b8500785293b98d6f785
- auth_routes_base86.py 5add302ddff52770870968dba2bc7d9a29bb6d3b0c348d2f99d5ccb840d98be2 (`git show 86d5a24d:app/api/auth_routes.py`, LF; = the spec's base LF sha) and claude_base86.md 0c6f286705f5013dc0fbc81c2ada0d38da30cde5ec1ef2a94b1868e7971cc010 (`git show 86d5a24d:CLAUDE.md`)
- logs: unit_off.log, unit_on.log, probe_head.log, probe_base.log, probe_n3b.log, AB_on.log, ledger_kb.log, red_at_base.log, mut_advc-<id>.log per mutant run; byte copies in mut_copies/ (the HEAD files the restores came from)

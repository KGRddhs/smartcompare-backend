# S81-G9 FOLLOWUPS: S81-16c WDQS-EXEMPTION + D17c COVERAGE-EMPTY-HOSTS + S81-22d LEDGER-PINS-FLAG-SAFE + S81-23b SCRAPEDO-SUPER-RETIRE

Base `39ac80ba437760d1a77eaac9670faeea505f08f4` (origin/main after #394); HEAD `b39e265fa9d6f808251b8070ab72125660d98ca8` on `feature/s81-g9-followups`. The eighth SAFE group under LC-9 (one GREEN, one adversary). NO new flag: S81-16c rides `ENABLE_KB_BRANDS` (unset in production), D17c rides `ENABLE_KB_COVERAGE_ROLLUP` (apply on the kb-coverage service: the merge changes its next scheduled pass only on the two edge paths, 0 hosts and a failed read), S81-22d is test-only, S81-23b is unflagged under R-A1 (c). Rulings: RULINGS_S81_G9 (R-G9-1..10), RULINGS_S81_16C (R-S16C-0..8), GATE_S81_G9 (GC-1..GC-10); spec `.qa-s80/S81-G9_UNIT_SPEC.md` (f94aaf71...). Mutation tables and per-row evidence: specs/S81_G9_RED_REPORT.md and the GREEN report (state folder).

## S81-16c WDQS-EXEMPTION (`scripts/seed_kb_brands_wikidata.py` + docs)

- `wdqs_exemption_check(robots_body, url)`: None = exempt; else the first refusing check: `url` (not exactly https / query.wikidata.org / /sparql, or a fragment), `named_group` (a group whose token occurs in the production agent string), `rule_set` (the rules for the agent or for '*' differ, as a multiset compared order-insensitively per R-G9-4, from (Disallow /sparql, Disallow /bigdata); any error fails closed). Called ONLY after the existing `can_fetch` gate refuses; the refusal line is the base text + ` check=<name>`; the exemption logs one INFO naming the ruling date and doc. An allowed body is byte-identical (no new line). Unreadable robots stays fail-closed (unchanged branch).
- ONE bounded retry on 429 / 503: Retry-After seconds, or a future HTTP date; else the body's "retry in N seconds" (first 2,000 chars); else the 120 s cap; the wait rides the fetcher's injected politeness sleep (`_pause`, kb_seed_common untouched); a hint ABOVE the cap gives up with one constants-only INFO `query status=429; hint above the cap; giving up retries=0`; a second failure logs `query failed status=<n> retries=1`; a non-retry status keeps the base line exactly. At most 3 fetches per run; every fetch carries `robots_registry._REQUEST_HEADERS` (the production agent with contact). No agent-name literal in the script.
- Docs: NEW `docs/policies/2026-11-07-wdqs-robots-exemption.md` = the docs-branch bytes (3,986 B, LF, sha256 `9613f9feb7161b0ff899b8ddfedb9082da17557408c6b97629d27f1e814cb7dd`, committed blob re-hashed equal); ONE pointer line appended to `docs/policies/2026-08-31-robots-unreadable-ruling.md`.
- RED `tests/test_s81_s16c_wdqs_exemption.py`: 30 nodes (15 RED / 15 PIN). 0 E-rows (the S81-16b frozen rows incl. r24[disallow] green unchanged).

## D17c COVERAGE-EMPTY-HOSTS (+ D17d exit PINs) (`scripts/cron_kb_coverage.py`)

- Root cause (R-G9-2, deterministic): with zero live / blocked hosts the script posted the empty pipeline `[]`; the REST endpoint answers a whole-request error object and the pinned upstash-redis 1.7.0 raises AttributeError iterating it (http.py:191). Now: 0 hosts = one INFO `family=hosts skipped hosts=0`, no `pipeline()` call, `not_built` unchanged; an AttributeError out of the exec call only is relabelled `pipeline_refused` (`_PipelineRefused`, constant `PIPELINE_REFUSED`); EVERY failed read family counts once in the totals `not_built` (one constants-only WARNING per family, never exc_info); the totals line keeps its frozen shape. N >= 1 hosts: unchanged request.
- D17d / D16c: both cron mains exit in a `python -I` child with no thread left besides MainThread (PIN rows P4 / P5).
- RED `tests/test_s81_d17c_coverage_hosts.py`: 11 nodes (6 RED / 5 PIN). 0 E-rows.

## S81-22d LEDGER-PINS-FLAG-SAFE (test-only)

- E-row EK1: `test_i2_camera_flag_off_no_metadata_llm` and `test_i6_off_camera_real_compare_total_cost_is_base` delete `ENABLE_COMPARE_RUN_LEDGER` as their first statement (2 lines, 4 nodes); green exported and unset; the S81-22 frozen files unchanged (P2 shas). Closes S81-22 L-I2I6; the S81-22 flip precondition is met.
- RED `tests/test_s81_s22d_ledger_pins.py`: 11 nodes (6 RED / 5 PIN).

## S81-23b SCRAPEDO-SUPER-RETIRE (`app/services/scrapedo_service.py`, `scripts/ab_render_providers.py`)

- `scrapedo_super_enabled()` no longer reads the legacy `SCRAPEDO_SUPER`: an unset `ENABLE_SCRAPEDO_SUPER` means OFF for every legacy value; a set value keeps the house idiom. Production carries neither name since the 2026-11-07 09:02 unset line, so byte-identical there. `ab_render_providers.py` drops the legacy write WITHOUT setting the new name (R-G9-6 Q-23b-2). The module docstring, the transition comment block and the reader docstring are reworded in place; the source_router (5 lines) and structured_comparison_service (1 line) comments / docstrings that named the legacy variable now name `ENABLE_SCRAPEDO_SUPER` (Q-23b-3; no behaviour change). AST census: no `SCRAPEDO_SUPER` constant under app/ or scripts/.
- E-rows EK2 / EK3 (R-G9-6 Q-23b-1: all seven EK3 rows).
- RED `tests/test_s81_s23b_scrapedo_super_retire.py`: 16 nodes (6 RED / 10 PIN).

## E-rows (deliberate pin changes; LF blob sha256)

| id | file | change | base LF blob | new LF blob |
|---|---|---|---|---|
| EK1 | tests/test_s81_s03_llm_ledger_v2.py | 2 delenv lines (i2, i6-off; 4 nodes) | `7732fa24c9047a0faf78d608cc97902ee6575d3c21661691eb7f56c12d4d4f5b` | `4ccc2c5641acf3bb02f4bb06f4f257004e1aa97920afa3579c423d24011e6083` |
| EK2 | tests/test_s81_s23_bypass_retire.py | P1_CASES true/TRUE -> False (P1 / P2 x2 each), r3 / p3 / p4 start from the new name; docstrings (7 nodes) | `6cf8c6d3f701636f839ab0073d4f29c73d8fcc602648458aa15190bfb7c930dc` | `e686619acc3797d3914cfd9765dd06ff3cb8afa1af8fa3908b076895db899e6d` |
| EK3 | tests/test_fragrance_content_quality.py | the ON-state env key -> ENABLE_SCRAPEDO_SUPER in 7 rows (4 red + 3 vacuous) + their docstring lines | `76a00ea5fe514d2a5815608f2a1dee09ec72a1dad171b656a1f3af2cee05cb77` | `959ad7a69faca71133732cfa99d83456acdff2d3c8948593cddd804538520ecf` |

## Counts and gates

- RED files (frozen, GC-1 shas re-hashed first and last: equal): 68 nodes = 33 RED (AssertionError at base) / 35 PIN. 28 mutants at RED: 27 KILLED, 16c-M5 EQUIVALENT (L-S16c-5).
- `[pyt] tag=g9green-red-off start=2026-11-07 13:35:21 end=2026-11-07 13:35:32 elapsed=11s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 10.08s`
- `[pyt] tag=g9green-red-on start=2026-11-07 13:36:26 end=2026-11-07 13:36:36 elapsed=10s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 9.36s`
- `[pyt] tag=g9green-s03-off start=2026-11-07 13:36:44 end=2026-11-07 13:36:56 elapsed=12s bound=600s status=OK rc=0 | 226 passed, 11 warnings in 10.61s`
- `[pyt] tag=g9green-s03-on start=2026-11-07 13:37:03 end=2026-11-07 13:37:15 elapsed=12s bound=600s status=OK rc=0 | 226 passed, 13 warnings in 10.96s`
- `[pyt] tag=g9green-ciorder start=2026-11-07 13:37:23 end=2026-11-07 13:38:59 elapsed=96s bound=1200s status=FAIL rc=1 | 7 failed, 1622 passed, 15 warnings in 93.88s (0:01:33)`
- `[pyt] tag=g9green-secretscan start=2026-11-07 13:39:07 end=2026-11-07 13:39:17 elapsed=10s bound=600s status=OK rc=0 | 31 passed, 1 warning in 8.65s`
- The CI-order set: the 7 failures are the CRLF working-copy class only (s16 r27 x5, d17 r9, s22 b02), identical at base; on CI's LF bytes the two edited scripts are ASCII with no CR.
- Comm set: the record's 673 (sorted-list sha256 `fe55771e...`) + the four RED files = 677 files in 28 chunks of <= 25 (bound 1200); the STORED base record `39ac80ba/fe55771e...` (25 FAILED ids) REUSED (LC-6). HEAD FAILED 25; `comm -13` (branch-only-new) = EMPTY; ids gone at HEAD: none.
- GREEN additions (the import-graph re-derivation over the two newly edited modules source_router / structured_comparison_service and the `from app.services import <module>` form): 27 files run at HEAD in 2 chunk(s): FAILED none.
- The S03 pair (the S03 file + the 22d file): 226 passed unset and 226 passed with `ENABLE_COMPARE_RUN_LEDGER=true` exported in the runner call only.
- Corpus gate at HEAD, every flag OFF (`scripts/verify_flag_byte_identity.py --proof-root <proof> --flags ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP`): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 `cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c` vs base `cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c`: EQUAL.
- Client fences (the fourteen + b3a/nativeStrings, by path through the junction): `[jest] tag=g9green-fences start=2026-11-07 13:24:16 end=2026-11-07 13:24:29 rc=1 node=v24.11.1 jest=29.7.0`; Test Suites: 1 failed, 14 passed, 15 total; Tests:       4 failed, 242 passed, 246 total; 13 / 14 fences green, the one red suite is config/nativeBundle.w37 with exactly the four known drift nodes (d5, k2, k4, k5); b3a green. FULL jest NOT run (LC-7: the final round). The four hook test files NOT run (no .githooks change).
- ruff --select E9,F63,F7,F82 and py_compile: clean on every edited / new Python file; bytes > 127 = 0 in every added line and new file; `git diff --stat` hunks only (no whole-file diff).

## Comm [pyt] lines (HEAD)

- `[pyt] tag=g9green-comm-c00 start=2026-11-07 13:41:07 end=2026-11-07 13:41:47 elapsed=40s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c01 start=2026-11-07 13:41:54 end=2026-11-07 13:42:23 elapsed=29s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c02 start=2026-11-07 13:42:57 end=2026-11-07 13:43:39 elapsed=43s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c03 start=2026-11-07 13:43:47 end=2026-11-07 13:44:53 elapsed=66s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c04 start=2026-11-07 13:45:02 end=2026-11-07 13:45:22 elapsed=20s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c05 start=2026-11-07 13:45:31 end=2026-11-07 13:45:50 elapsed=19s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c06 start=2026-11-07 13:45:58 end=2026-11-07 13:46:22 elapsed=24s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c07 start=2026-11-07 13:47:14 end=2026-11-07 13:47:56 elapsed=43s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c08 start=2026-11-07 13:48:04 end=2026-11-07 13:49:18 elapsed=73s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c09 start=2026-11-07 13:49:26 end=2026-11-07 13:50:09 elapsed=43s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c10 start=2026-11-07 13:50:16 end=2026-11-07 13:50:34 elapsed=18s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c11 start=2026-11-07 13:50:41 end=2026-11-07 13:51:02 elapsed=21s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c12 start=2026-11-07 13:51:10 end=2026-11-07 13:51:44 elapsed=34s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c13 start=2026-11-07 13:51:51 end=2026-11-07 13:52:30 elapsed=39s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c14 start=2026-11-07 13:52:38 end=2026-11-07 13:52:59 elapsed=21s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c15 start=2026-11-07 13:53:07 end=2026-11-07 13:53:26 elapsed=20s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c16 start=2026-11-07 13:53:34 end=2026-11-07 13:56:18 elapsed=165s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c17 start=2026-11-07 13:56:26 end=2026-11-07 13:58:08 elapsed=102s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c18 start=2026-11-07 13:58:17 end=2026-11-07 13:59:24 elapsed=67s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c19 start=2026-11-07 13:59:32 end=2026-11-07 14:01:07 elapsed=95s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c20 start=2026-11-07 14:01:14 end=2026-11-07 14:01:59 elapsed=44s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9green-comm-c21 start=2026-11-07 14:02:06 end=2026-11-07 14:03:15 elapsed=69s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c22 start=2026-11-07 14:03:23 end=2026-11-07 14:03:44 elapsed=21s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c23 start=2026-11-07 14:03:54 end=2026-11-07 14:04:38 elapsed=45s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c24 start=2026-11-07 14:04:46 end=2026-11-07 14:05:38 elapsed=52s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c25 start=2026-11-07 14:05:46 end=2026-11-07 14:06:25 elapsed=40s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c26 start=2026-11-07 14:06:34 end=2026-11-07 14:06:59 elapsed=25s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-c27 start=2026-11-07 14:07:06 end=2026-11-07 14:07:15 elapsed=8s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-x00 start=2026-11-07 14:07:26 end=2026-11-07 14:07:41 elapsed=15s bound=1200s status=OK rc=0`
- `[pyt] tag=g9green-comm-x01 start=2026-11-07 14:07:49 end=2026-11-07 14:07:52 elapsed=3s bound=1200s status=OK rc=0`

## Stated limits

- L-S16c-1 (R-S16C-7): Arabic labels 38 / 342; 379 hosts exceed MAX_BRAND_HOSTS = 300 (the cap trims); no gzip Accept-Encoding in `_REQUEST_HEADERS`.
- L-S16c-2: the RED body is a synthetic 95-byte shape of the live file; a live file that adds any rule refuses until a new ruling.
- L-S16c-3: the retry wait rides the fetcher's private `_polite._sleep` (no kb_seed_common edit); a PoliteFetcher refactor must keep it (R5 / R7 go red loudly).
- L-S16c-4: the retry GET also waits the Politeness 2 s (total = hint + 2 s).
- L-S16c-5 (GC-3, 16c-M5 equivalent): the rule-set comparison effectively reads the '*' group's rules; a group of the agent's own refuses first by named_group.
- L-S16c-6: the production agent's 429 behaviour at WDQS is unmeasured (only Python-urllib was observed); no live request was made (R-S16C-8).
- L-S16c-7: a Retry-After HTTP date that is not in the future (or unparseable) carries no wait and falls to the body hint, else the cap; the multiset comparison also refuses a duplicated exempt rule (fail closed).
- L-D17c-1: proven against the pinned SDK's request shape, not Upstash itself; the next scheduled run is the live read.
- L-D17c-2: the SDK reads a non-2xx body without a status check; any whole-request error (auth, quota) also surfaces as pipeline_refused.
- L-D17c-3: no chunking (at most KB_COVERAGE_MAX_HOSTS = 500 commands, about 22 KB).
- L-D17c-4: the stuck Railway bookings are not reproduced; P4 / P5 prove local exit with fakes.
- L-D17c-5 (GC-4 D6): the D17c rows drive the real upstash_redis.Redis through its private `_http._client` (httpx MockTransport); an SDK bump that renames the seam turns them red.
- L-S22d-1: the rows prove the OFF ledger's leaf silence only.
- L-S23b-1: a box that still carries the legacy name loses the super tier unless ENABLE_SCRAPEDO_SUPER is set (production carries neither).
- L-S23b-2: the tracked `.qa-bias-rerun/_sephora_provider_test.py` still sets the legacy name (inert).
- L-S23b-3: the corpus gate cannot reach the reader; the behaviour proof is the RED / PIN rows.
- L-S23b-4: docs/contracts and the 2026-06 plans keep the legacy name as history.
- L-G9-CM: the GREEN-added comm members were run at HEAD only (green there, so no base run was needed); the S81-24 records were not consulted.

## CLAUDE.md

- The G9 block after the S81-G8 block (one blank line), before `## Tests`; the Feature Flags pointer clause gains the S81-G9 sentence after the S81-G8 one; in place: the Scrape.do sentence of the price pipeline, the S81-G1 ENABLE_SCRAPEDO_SUPER row (transition ended, L1 / L4 / L5, the post-approval change done, the canary) and its owner step (1), the S81-16b brand-script sentence (the exemption), the D17 row (zero hosts), the S81-22 L-I2I6 sentence and owner step (4). NOT the :92 apply record and NOT the S81-08b row (the S81-24 final round carries them; R-G9-7). CRLF kept; the added text is ASCII.

## Owner steps (names only; a dated ledger line per step)

- S81-16c: after the merge, the owner-approved DRY run (`ENABLE_KB_BRANDS=true` in the command's own environment through railway run; expect about 342 brands), then `ENABLE_KB_BRANDS=apply` the same way, then the kb_brands count. No live Wikidata request before the merge. The ruling: `docs/policies/2026-11-07-wdqs-robots-exemption.md`.
- D17c: re-read the totals line of the next scheduled kb-coverage runs (`not_built`, `redis`).
- S81-22d: none. S81-23b: none (both preconditions met: the 09:02 unset line and approval).

[NATIVE READ]: EMPTY (no Arabic string added or changed).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

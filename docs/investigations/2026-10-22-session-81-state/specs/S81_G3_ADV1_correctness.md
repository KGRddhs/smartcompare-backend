# S81-G3 adversary report (correctness lens, LC-1 folded checks)

Agent: the G3 correctness adversary, model Opus 5.5. Written through the shell. Worktree verified: sc-s81-g3 on feature/s81-g3-kb-ingest at HEAD efa33a81dc6eca04f8f41c024cf3fc627a22032f (base 744616e3, origin/main 744616e3). The GREEN worktree was never edited; every probe and mutant ran in my own detached scratch worktree S81-G3_adv_correctness at efa33a81, whose seven new files were re-written from the committed LF blobs so its bytes equal GREEN's working copy (sha256 of price_service, scs, algolia, CLAUDE.md equal both sides).

## Verdict: NOT_READY (0 blocking, 2 major, 7 minor). Both majors are one-line / one-row fixes.

Frozen RED files re-hashed first and last (committed blobs and the GREEN working copy): 542cd259..., 547cdb74..., 55851c04..., 514d1cd2... = GC-1. New-file blobs: live_robots.py dd30877e..., kb_ingest.py 8b09ed20..., gate rows 16c37591... (= the GREEN report); 0 CR, 0 bytes > 127.

## MAJOR

M-1 (diff hygiene, live request path): app/services/price_service.py:51 carries an unjustified edit of an existing line outside every spec hunk:
  base: `ENABLE_PAGE_SCRAPE = os.environ.get(...)`  HEAD: `ENABLE_PAGE_SCRAPE =os.environ.get(...)` (one space deleted).
  It is the "-1" of price_service's 19/1 numstat; the GREEN report lists the numstat but never justifies the deletion, and spec 3.2 allows only the import beside :46 and the two hooks ("No other file", "no deleted lines you cannot justify"). No runtime effect (same expression; ruff --preview E225 flags it), but an accidental byte change in the live price module must be reverted before the PR, not carried as a stated limit. Fix: restore the space (one hunk; keep CRLF).

M-2 (flag-OFF invariant unpinned; a spec mutant survives): S17-M3 as written in the spec table ("the flag check removed (job always built)") SURVIVES against the GREEN bytes: removing `if not (ingest or expose): return` from `_kb_ingest_tail` builds the projection (`kb_ingest._now()`, `result_gate.assess_result`, the deep copies) on the loop on EVERY success exit with both flags OFF, and a raising build_job then logs `[KB_INGEST] build failed` with the flags OFF; nothing in the 186 RED nodes, the 10 gate rows or the CI-order set sees it (P1 compares the body digest and the fire-and-forget labels only; GREEN's separate `if expose:` / `if ingest:` arms keep the body and the labels unchanged). GC-3 recorded S17-M3 KILLED against the prototype; against GREEN only the RED-form variant S17-M3b (check removed AND the job scheduled) is killed (P1[unset-offload_off]). Spec 2.6 / R-G3-10 make "both OFF -> two env reads, no projection" the main invariant. Fix: one GREEN-owned gate row (G3-GR3) asserting both flags OFF never call kb_ingest.build_job / kb_ingest._now (a raising recorder), with S17-M3 as its mutant; my probe `test_kb_tail_flags_off_no_projection` (recording build_job / _now / _fire_and_forget, asserting zero calls) is such a row: it passes at HEAD and KILLS S17-M3 ([pyt] tag=g3adv-s17-m3 13:55:25-13:55:41 status=FAIL).

## MINOR (documentation rulings / stated limits, LC-4)

m-1 Redis fallback: `_flush_sync` calls `pipe.exec()` (upstash-redis 1.7.0). cache_service builds a redis-py client (`redis.from_url`) when UPSTASH_REDIS_URL is a redis:// URL; a redis-py Pipeline has `execute`, not `exec` (measured: probe test_redis_py_pipeline_has_no_exec), so on that fallback every flush is one WARNING `[LIVE_ROBOTS] health flush failed: AttributeError` and counts nothing. Production uses the REST SDK; state it (D14-L10) or call `execute` when `exec` is absent.
m-2 Redirects inside curl: `curl_fetch_html` (allow_redirects=True) and the Algolia landing GET are gated on the INITIAL URL only (spec 2.3 as written); curl_cffi follows a cross-host redirect to a host with no verdict, and record_response attributes the outcome to the initial host. Only curl_fetch_html_same_site, Shopify and URL-V2 gate hops. Stated limit candidate (D14-L11).
m-3 ADV-8 survives the committed suite: removing `_ATTEMPTS_CTX.set(None)` in flush_attempts (the spec's "reads the bound dict, unbinds it") is not seen by any RED / gate row; a second flush on the same context would re-send the same counts. Killed by my probe test_flush_one_pipeline (flush called twice, ONE pipeline). Fold into the G3-GR3 row of M-2.
m-4 R-G3-5 "load_records_sync at most once per memo window per process": no single flight on the sync path; concurrent ingest jobs that find records_snapshot() None at the window edge each do the paged read (bounded by the executor width). State it.
m-5 DV-G1 (cards AND gaps only for category fragrances): stricter than spec 2.3 step 8; sound (kb_product_id prefixes every id with fragrances, measured by GREEN; no non-fragrance gap rows), needs the orchestrator's ruling Q-G1. PR body and CLAUDE.md already say "fragrance".
m-6 Spec 2.5 says "Redis client None -> ONE WARNING"; the code returns silently (spec 2.2 says "no Redis client -> nothing"): spec self-contradiction, code follows 2.2. Ruling only.
m-7 Evidence freshness: the GREEN CI-order run (12:22) and the corpus gate predate the final docstring-only edit of live_robots.py (12:42:10); the PR body does not say so (the GREEN report does, DV-G6). I re-ran the CI-order set at HEAD: 1953 passed / 1 failed (r06 base node) = GREEN. The corpus gate was not re-run (live_robots is not on the extract_price_from_html path; M-1's fix touches price_service, so the fix round must re-print the corpus SHA). Also: ruff (full ruleset, report-only) B905 zip() without strict at kb_ingest.py:278.

## Mutation table (byte copies in the scratch worktree; restore + sha256 after each; SHA-IDENTICAL over app/services/*.py + CLAUDE.md after every batch; driver mutate_adv.py, logs mut/<id>.log, results mut/results_*.json; killing set = the two RED files + the gate rows, bound 600)

| id | mutant | result | first killer |
|---|---|---|---|
| D14-M1 | gate returns True under ON | KILLED | d14 L3 / L4 rows |
| D14-M2 | flag check removed (gate + curl hook guard, DV-8) | KILLED | P1_flag_off_fetcher_identity[curl-unset] |
| D14-M3 | star rules replaced by qarenbot | KILLED | L2_verdict_table[robots_star_disallows] |
| D14-M4 | origin comparison removed | KILLED | L2_verdict_table[origin_www] |
| D14-M5 | expiry test inverted (jsonld_widen) | KILLED | L2_verdict_table[allow] |
| D14-M6 | V2 hop gate disabled | KILLED | L4_skip_per_fetcher[url_v2_hop] |
| D14-M7 | shopify hop gate returns on allow | KILLED | L4_skip_per_fetcher[shopify] |
| D14-M8 | flush per curl fetch | KILLED | L5_outcomes_counted[200-headers0-ok] |
| D14-M9 | flush ignores the health flag | KILLED | L8_no_pipeline_without_attempts_or_health[health_off] |
| D14-M10 | robots_entry_lookup ignores the flag | KILLED | L7_seam_answers_the_record_under_the_flag |
| D14-M11 | memo select `*` | KILLED | L3_refresh_reads_once_off_loop |
| D14-M12 | skip line carries the URL | KILLED | L11_log_lines_carry_hosts_and_constants_only |
| S17-M1 | tail before moderation (REST) | KILLED | S6_no_key_off_the_success_exits[rest_refusal] |
| S17-M2 | stream tail after settle_complete | KILLED | S7_one_job_per_compare_after_moderation[stream] |
| S17-M3 | flag check removed (projection always built) | SURVIVED the committed suite (M-2); KILLED by my probe | - |
| S17-M3b | check removed AND job scheduled (RED form) | KILLED | P1_flag_off_identity[unset-offload_off] |
| S17-M4 | run_job inline | KILLED | S6 / S8 rows |
| S17-M5 | cards at medium | KILLED | S11_confidence_gates[medium] |
| S17-M6 | verdict skipped for offers | KILLED | S12_offer_refusals[row_blocked] |
| S17-M7 | converted_usd admitted (no rung) | SURVIVED = equivalent by the rung check + builder belt (GC-7 accepted) | - |
| S17-M7b | converted_usd admitted with a rung | KILLED | S12_offer_refusals[converted_usd] |
| S17-M8 | CAS .eq(demand_count) dropped | KILLED | S17_existing_gap_compare_and_set[cas_wins] |
| S17-M9 | pdp_ guard dropped + fields renamed pdp_ | KILLED | S16_no_specs_and_misses_become_gaps |
| S17-M10 | ignore_duplicates False | KILLED | S10_builder_only_writes |
| S17-M11 | field_status stamped with exposure OFF | KILLED | S21_ingest_does_not_change_the_body[camera_full] |
| S17-M12 | a kb_specs write | KILLED | S10_builder_only_writes |
| G3-GRM1 | Decimal normalisation dropped | KILLED | gr1[returned_numeric-0] |
| G3-GRM2 | algolia + url_extraction recording dropped | KILLED | gr2[algolia_explicit] (pattern count 2 per file, both sites mutated) |
| ADV-1 | records_snapshot age check dropped | KILLED | L3_records_snapshot_is_age_aware |
| ADV-2 | needs_operator ignored | KILLED | S17_gap_needs_operator_on_blocked_host |
| ADV-3 | region bahrain check dropped | KILLED | S12_offer_refusals[region_not_bahrain] |
| ADV-4 | EXPIRE dropped (first form was a syntax error, re-applied as `pass`) | KILLED | L8_flush_once_per_compare[rest] |
| ADV-5 | woo outcome recording dropped | KILLED | gr2[woo] |
| ADV-6 | shopify outcome recording dropped | KILLED | gr2[shopify] |
| ADV-7 | KB_INGEST_GAP_MAX bound dropped | KILLED | S17_gap_max_bounds_the_rows |
| ADV-8 | flush does not unbind | SURVIVED the committed suite (m-3); KILLED by my probe | - |

24 spec + S17-M7b + 2 gate mutants re-applied: 25 killed, S17-M7 equivalent (accepted), S17-M3 survives (M-2). 8 own mutants: 7 killed, ADV-8 survives (m-3).

## Probes (tests/test_zz_adv_probes.py in the scratch worktree only; fakes, netguard on): 23 nodes
- Flag-OFF identity with a RAISING recorder at every live_robots seam (_admin_client, _redis_client, _now, _monotonic, row_for_host, url_verdict, host_of) and the health sub-flag ON: gate True, bind / record / flush no-ops, ROBOTS_ENTRY_LOOKUP None, the ContextVar untouched. PASS.
- Fail-closed cold memo: no running loop -> skip `reason=no_row`, nothing scheduled, no raise, the INFO line carries the host only (no path / query). In a loop: two skips, exactly ONE refresh, on a worker thread (not the loop thread). PASS.
- URL mode V2 under the flag (SSRF validator faked allow, cold memo): `outcome=robots_skip`, `_V2_FETCH_OUTCOME_REASONS["robots_skip"] == "robots_skip"` -> STORE_UNREADABLE (classifier :1051-1054). PASS. (The scheduled memo refresh reached the real admin-client factory and the hermeticity sentinel neutralised it: a probe artefact, not a G3 egress.)
- CAS payload: an existing gap row is updated with exactly {demand_count: n+1, last_seen}, filtered .eq(product_key).eq(field).eq(demand_count, n); an empty result counts gap_cas_lost; the insert is ignore_duplicates=True; no `identity` and no `pdp_` field. Identity medium writes kb_gaps only; low writes nothing. PASS.
- R-G3-1 Redis: ONE pipeline() and ONE exec() per compare, on a pool thread (not the loop thread); HINCRBY `kbh:20261104:<host>` `<source>:<outcome>` with positive ints; one EXPIRE per key at 8 d; a second flush on the same context sends nothing; TTL clamp 0 / -1 / nan / inf / garbage -> 8 d, 100 -> 30 d, 0.5 -> 1 d, 3 -> 3 d; a raising exec = exactly ONE WARNING `health flush failed`; health ON + main OFF = no pipeline. `kbh:` occurs once in app/ (live_robots.py:65): no collision with an existing key prefix. PASS.
- R-G3-5: records_snapshot returns the load until MEMO_SECONDS (clamped 300..900) and None after. GC-6: a returned numeric 12.5 matches the sent "12.500" (0 updates), 12.6 gives 1 update. _kb_ingest_tail: both OFF = zero calls to build_job / _now / _fire_and_forget; a raising build_job = ONE WARNING, body untouched. PASS.
- [pyt] tag=g3adv-probes2 start=2026-11-04 13:11:05 end=2026-11-04 13:11:10 elapsed=5s bound=600s status=OK rc=0 (23 passed; the strengthened no-projection row re-run at HEAD below).

## Code reading against the claims (R-G3-9, 12.6, GC-5)
- Both finally arms (scs :4854 REST, :5777 stream) are a bare `live_robots.flush_attempts()`; no return / await in either finally; flush never raises (outer try) and never awaits (fire_and_forget). bind sits in _init_provider_attempts inside the wait_for task (REST) / the generator (stream). The L1 pre-filter return precedes the try (no flush, but nothing was counted). OK.
- The tail placement: REST after the `_l3.allowed` refusal return and before the behaviour-profile block / `return result`, with no await between the job scheduling and the return (a hard-cap cancel cannot split them); stream after the refusal yields and before `yield ("settle_complete", ...)`; product_categories / region are bound on both paths (:4436 / :5128). The job is never awaited (S8 + S17-M4 killed).
- GC-5: curl, curl_same_site, shopify, woo, algolia (landing GET + each explicit query), url_extraction (base from the fetch_page result, V2 terminal response) each record ok / fail; outcome_of tolerates a response with no headers (gr2). UA / impersonate untouched (no hunk touches them).
- Hygiene: no `robots_registry` / `QarenBot` text in the two new modules; no `kb_merchants` in any hooked fetcher; live_robots never imports shopify_pdp_service; fetch_page outside every hunk; existing files 100 % CRLF, new files LF, 0 non-ASCII in added lines (the one non-ASCII added line is the re-written CLAUDE.md :341 line with its existing glyphs). Deleted lines: CLAUDE.md :341 (pointer clause), the url_extraction reasons dict line and the two fetch_page caller lines (re-written), the E1 P01_FUNCTIONS line, and price_service :51 (M-1, unjustified). ruff E9,F63,F7,F82 on the 10 files: All checks passed; compile() OK on all 10.
- Billing (R-A3) / error-handler mapping / contract freeze: no route, metering, refund or error-code hunk; responses change only under default-OFF flags (additive metadata.field_status; V2 STORE_UNREADABLE reason robots_skip, an existing code).
- CLAUDE.md block (+5 lines after the S81-G2 owner steps, :341 pointer) and the PR body (13,589 B < 25,600; counts 186 + 10 + 529 = 725; 1757 + 196 = 1953) match the bytes; R-G3-2/3/4/5/7/8 sentences present; no "every fetch" wording. Exception: neither mentions M-1.

## Gates re-run from the exact bytes (one pytest at a time, except the deviation noted)
```
[pyt] tag=g3adv-unit-off start=2026-11-04 13:08:04 end=2026-11-04 13:08:23 elapsed=20s bound=600s status=OK rc=0   (2 RED files + gate rows + kb_schema: 725 passed)
[pyt] tag=g3adv-unit-on start=2026-11-04 13:08:29 end=2026-11-04 13:08:48 elapsed=19s bound=600s status=OK rc=0   (725 passed, the four flags exported in ONE runner call)
[pyt] tag=g3adv-ci-off start=2026-11-04 13:29:27 end=2026-11-04 13:30:14 elapsed=47s bound=1200s status=FAIL rc=1   (CI-order: 3 G3 files + the 13 existing members OFF: 1953 passed / 1 failed = r06 base node; equal to GREEN)
[pyt] tag=g3adv-pins start=2026-11-04 13:30:21 end=2026-11-04 13:50:22 elapsed=1201s bound=1200s status=TIMEOUT rc=124   (pins + hook files together: measurement failure, split and re-run)
[pyt] tag=g3adv-pins2 start=2026-11-04 13:50:49 end=2026-11-04 13:52:00 elapsed=71s bound=600s status=OK rc=0   (test_model_config, _enforced, test_prompt_fence, test_u3c_store_false_pin, test_migration_index_predicate_immutability, test_migration_044, the two CLAUDE.md readers test_ci_gates + test_behavior_dimension_translation, test_hermeticity_pins, test_legal_disclosure_s77, test_secret_scan_static: 454 passed)
[pyt] tag=g3adv-comm-02 start=2026-11-04 13:52:08 end=2026-11-04 13:53:08 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=g3adv-comm-08 start=2026-11-04 13:53:09 end=2026-11-04 13:53:40 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=g3adv-comm-18 start=2026-11-04 13:53:42 end=2026-11-04 13:54:39 elapsed=57s bound=1200s status=FAIL rc=1   (exactly the 6 base nodes: r06 + the five s16 r27 CRLF nodes)
[pyt] tag=g3adv-hooks start=2026-11-04 13:54:45 end=2026-11-04 14:24:47 elapsed=1802s bound=1800s status=TIMEOUT rc=124   (the four test_precommit_hook*.py alone)
[pyt] tag=g3adv-probes3 start=2026-11-04 14:28:01 end=2026-11-04 14:28:06 elapsed=5s bound=600s status=OK rc=0   (23 probes at HEAD)
```
Mutant runs: 38 [pyt] lines tag=g3adv-<id> in mut/*.log (each ~15-30 s, bound 600). Every run: [netguard] blocked 0 except the probe artefact named above.
- The hook test files (tests/test_precommit_hook*.py): NOT MEASURED (TIMEOUT twice: inside the combined run, then alone at the 1800 s ceiling). Deviation, stated: two of my mutant runs (S17-M3, ADV-8 against the probe file, about 35 s) overlapped the alone re-run. No .githooks file is in the diff (the GREEN report also did not run them).
- Comm set re-derived by the union rule: the only test files that reference live_robots / kb_ingest are the three new G3 files and tests/test_s81_kb_schema.py (already a RED member); RED's 609 + 3 = 612 = GREEN's COMM_SET_HEAD.txt; no missing file. GC-9 reuse confirmed: GREEN's HEAD FAILED set (14) is identical to the stored base record ba26af35....txt (comm -13 and comm -23 both empty).
- The corpus gate and the fourteen client fences were not re-run (GREEN's lines stand for the GREEN bytes; the corpus must be re-printed after the M-1 fix).

## Prove-nothing rows
- P1 of tests/test_s81_s17_kb_ingest.py proves the flag-OFF body and labels, not the "no projection" half of spec 2.6 (M-2).
- No committed row pins the unbind in flush_attempts (m-3).
- The RED's `_admin_client` fakes are callable objects, so the "direct" half of GC-8's seam wording is untested (DV-4 accepted: the fakes are both).

## Fix round asked (small)
1. price_service.py:51 restore `ENABLE_PAGE_SCRAPE = os.environ...` (M-1); re-print the corpus SHA.
2. tests/test_s81_g3_gate_rows.py: G3-GR3 both flags OFF -> zero build_job / _now / _fire_and_forget calls in _kb_ingest_tail (mutant S17-M3), and flush_attempts unbinds (a second flush sends nothing; mutant ADV-8) (M-2, m-3).
3. Minors m-1..m-7 as stated limits / rulings.

Scratch worktree removed at the end (git worktree remove --force; no junction in it); the GREEN worktree untouched (git status clean, HEAD efa33a81); frozen RED files re-hashed at the end (see the last line).

End state (14:3x): scratch worktree removed and gone; sc-s81-g3 HEAD efa33a81, git status clean; frozen RED files re-hashed LAST: 542cd259... 547cdb74... 55851c04... 514d1cd2... = GC-1. Probe file copy: S81-G3_adv/test_zz_adv_probes.py.

## W0-4e / W0-4f / W0-4g: the R-W04 follow-ups (flag: the existing ENABLE_PRICE_PARSE_OFFLOAD)

Follows #196 (R-W04). There is no new flag and no new knob; `PRICE_PARSE_MAX_WORKERS` is unchanged. With the flag OFF, behaviour is byte-identical to `61585c58`.

### Defects
- **W0-4e.** Under the flag, `curl_fetch_html` capped EVERY caller at `PRICE_FETCH_MAX_BYTES` (3,000,000 chars). That included `structured_comparison_service._lazy_bh_pdp_backfill`, which regex-scans a curled retailer SEARCH page for an in-domain `/product/` href. So with the flag ON, an href past 3,000,000 chars was silently lost (R-W04 ruling 5, disclosed there). The existing pin covered flag OFF only.
- **W0-4f.** `url_extraction_service.extract_from_url` ran `extract_amazon_data` / `extract_noon_data` / `extract_generic_data` INLINE on the event loop in both flag states. Each builds one or more `BeautifulSoup` trees; generic builds two. The transitive AST guard carried an allowlist entry for exactly this.
- **W0-4g.** CLAUDE.md's W0 activation step (2) says to watch the price-parse pool's queue depth, but nothing exposed it. Separately, the R-W04 r1 adversary left four test-side gaps (see Gates).

### Design
- **W0-4e: whole-page scan, chunked and yielding on the loop (includes W0-4e2, Fable ruling R11).**
  - `curl_fetch_html(url, *, cap=True)` gains a keyword-only exemption. Under the flag, `cap=False` returns the whole `resp.text`. With the flag OFF the kwarg is never read, so the base statements run.
  - `_lazy_bh_pdp_backfill` is the ONLY `cap=False` site in `app/` (AST-pinned).
  - **Why not the pool.** The first design ran the backfill's `re.findall` on the price-parse pool. It was measured and refuted. CPython's `re` holds the GIL for a whole `findall`, so a pool thread does not free the loop. Measured on a realistic-markup 40 MB page (described under "Measured effect") with a 5 ms heartbeat, 4 reps each over two batches:

    | Arm | Max loop gap |
    |---|---|
    | Inline `findall` on the loop | 0.531 / 1.092 / 0.503 / 0.451 s |
    | `findall` on a worker thread | 0.929 / 1.087 / 0.468 / 0.495 s |
    | Control: `time.sleep(0.6)` on a worker thread | 0.022 / 0.016 / 0.016 / 0.016 s |

    The worker-thread arm stalls the loop as long as the inline arm; only the sleeping-thread control frees it. (The previous revision of this table used the `x`-filler test page: 0.326 / 0.362 s inline, 0.315 / 0.332 s on a thread. The conclusion is the same.) The pool offload is REMOVED for this site. `run_parse_offloaded`, the pool and the other offload sites are untouched.
  - **The scan now, flag ON.** It runs ON the event loop over the uncapped page:
    - Module constants `_W04_SCAN_CHUNK = 1_000_000` and `_W04_SCAN_OVERLAP = 65_536` (chars), both value-pinned (R15).
    - The SAME base pattern (literal unchanged, `re.IGNORECASE` as at base) runs as `re.finditer` over `html[start : min(start + CHUNK + OVERLAP, n)]` for `start` in `range(0, n, CHUNK)`. No scan call sees more than CHUNK + OVERLAP chars (pinned, R14).
    - A match is kept only when its absolute start is `< start + CHUNK`. A match that starts in the overlap tail belongs to the next slice; that is the dedupe rule, and order is preserved.
    - `await asyncio.sleep(0)` runs once per slice.
    - The `_accept` loop (`validate_scrape_url`, `score_source`, ordering) then runs over the collected list exactly as at base, on the loop in both states.
    - The result equals `re.findall` for every match shorter than `_W04_SCAN_OVERLAP`, except the chained-href corner under Stated limits.
  - **Flag OFF:** the base single `re.findall(...)` runs inline over the whole page. The call is byte-identical to `61585c58`'s.
  - **Measured effect, through the real `_lazy_bh_pdp_backfill`.** This is a measurement, not a pin.
    - **The page** is realistic listing markup: each unit is an `<li>` with a category anchor and two `<span>`s, and every 5,000th unit adds one in-domain `/product/` anchor. That gives 29 hrefs on 30 MB and 38 on 40 MB. Every run returned 29 or 38 candidates, and no run built a pool.
    - **The method:** only Serper, curl, `validate_scrape_url` and `score_source` are stubbed, with a 5 ms heartbeat. There were two batches of 3 reps each, one after the other, on a box under concurrent load.

    | Page | Batch | Flag OFF (inline) max gap | Flag ON (chunked) max gap | Wall time OFF / ON |
    |---|---|---|---|---|
    | 30 MB | 1 | 0.353–0.501 s | 0.036–0.041 s | 0.353–0.501 / 0.406–0.428 s |
    | 30 MB | 2 | 0.295–0.376 s | 0.030–0.037 s | 0.295–0.376 / 0.351–0.429 s |
    | 40 MB | 1 | 0.458–0.677 s | 0.035 / 0.070 / 0.035 s | 0.458–0.677 / 0.599–0.758 s |
    | 40 MB | 2 | 0.407–0.668 s | 0.097 / 0.035 / 0.038 s | 0.407–0.668 / 0.449–0.864 s |

    - **Idle floor.** The idle heartbeat reads 0.016–0.018 s over 6 reps (Windows timer granularity).
    - **Cost of one slice.** One slice of 1,065,536 chars costs 0.012–0.017 s median and 0.018 s max, measured as a standalone `finditer` over the same page.
    - **Reading the table.** The typical chunked gap (0.030–0.041 s) is about twice the idle floor: one slice's scan plus the timer granularity. Two single reps at 40 MB read 0.070 s and 0.097 s, both taken while the box was heavily loaded (the six unit files ran at about 3× their earlier wall time this round).
    - **Inline for comparison.** The inline scan stalls the loop for the whole page, 0.29–0.68 s.
    - **Wall time.** The page cost is still paid, spread over 1 MB turns. Total wall time is comparable to inline and sometimes higher: 30 MB 0.35–0.43 s chunked against 0.29–0.50 s inline, and 40 MB 0.45–0.86 s chunked against 0.41–0.68 s inline.
    - **Earlier revision.** Its table (chunked 0.016–0.022 s) was measured on the E2 test fixture's `x`-filler page, the regex's cheapest input. Re-measured this round on that page, the chunked gap was 0.017–0.024 s and inline 0.157–0.433 s. The difference comes from the page, not the code.
  - The href past 3 MB is found again under the flag.
- **W0-4f: the three `ues` extractors run on the pool.**
  - The extractor is selected as a module global at call time.
  - Under the flag, `from app.services import price_service as _w04_ps` is the same package-attribute form scs uses (ruling R2). Then:
    - `html = html[:_w04_ps.PRICE_FETCH_MAX_BYTES]`, one truncation right after the fetch.
    - The SAME capped html also reaches `extract_with_ai`. This mirrors the render legs: bounded parse input, unbounded fetch.
    - `raw_data = await _w04_ps.run_parse_offloaded(_extractor, html, url)`.
  - With the flag OFF, `_extractor(html, url)` runs inline on the whole body.
  - An extractor exception propagates with the same type in both states.
  - `_TRANSITIVE_ALLOWLIST` in `tests/test_retro_w0_4.py` is now `frozenset()`.
  - **Measured effect:** a 2.7 MB generic page parse costs the loop a max gap of 0.28–1.03 s offloaded, against 7.4–9.2 s inline. Soup building releases the GIL often enough for the offload to help, unlike a single `findall`.
- **W0-4g: pool instrumentation.**
  - `price_service._PRICE_PARSE_STATS` holds `{jobs_total, waiting, running, peak_waiting, peak_running}`. It is mutated only in `run_parse_offloaded`, on the loop thread.
  - `waiting` counts a job only when it is BLOCKED on the submission semaphore. `sem.locked()` is checked right before `await sem.acquire()`, and the count is decremented in a `finally` around the acquire. A cancelled waiter never leaks a count and never releases a slot it did not take.
  - `running` and `jobs_total` count after the acquire. `running -= 1` and `sem.release()` sit in the `finally` around the executor await.
  - `price_parse_pool_stats()` is a pure read: `None` until the pool exists, otherwise a FRESH dict `{workers, queued, **counters}`.
  - `_get_price_parse_pool` logs ONE grep-stable line when it builds the pool: `[PRICE-PARSE] pool built workers=N`.
  - `app/main.py::price_parse_pool_snapshot()` reads `sys.modules.get("app.services.price_service")` (never an import) and catches every `Exception` into `{}`. `/health` merges `**price_parse_pool_snapshot()`. The handler stays a pure dict read: no await, no import, none of the forbidden substrings.

### Flag row
| | |
|---|---|
| Flag | `ENABLE_PRICE_PARSE_OFFLOAD`: EXISTING, default OFF, read per call by the three agreeing readers |
| Effect ON | The backfill scans the whole search page in yielding 1 MB slices on the loop. The `ues` extractors run on the price-parse pool with the parse input capped at 3,000,000 chars. `/health` carries `price_parse_pool` once the pool has been built. |
| OFF | Byte-identical in a process that never ran a flagged parse: the pool is never built, so the `/health` key is absent. After an ON→OFF flip, see the contract below. |
| Knobs | `PRICE_PARSE_MAX_WORKERS` (default 4, clamped 1..16, read once at pool build) |

### /health key contract
- **When the key exists.** `price_parse_pool` is **absent until the pool is FIRST built**. A process that never ran a flagged parse never shows it.
  - **After an ON→OFF flip inside one process**, the pool, the key and its counters **persist until a restart**. They are stale but harmless: the pool takes no new work with the flag OFF.
  - A rollback check must therefore not rely on the key disappearing without a restart.
- **Shape.** Once present, the key reads `{workers, queued, waiting, running, jobs_total, peak_waiting, peak_running}`.
- **`waiting`** is the number of parses blocked on the submission semaphore. `peak_waiting >= 1` means queueing happened at least once. One uncontended parse reads `peak_waiting 0` (ruling R1).
- **`queued`** is the executor's own work-queue depth. It is **transiently non-zero on an ordinary semaphore hand-off**: a work item sits in the executor queue until a pool thread dequeues it.
  - Measured with no cancellation anywhere: 0–3 of 60 samples, timing-dependent, up to `queued 2`. One re-run of the same shape saw 0/60. A single sample means nothing.
  - A `queued > 0` that **persists across polls** means orphaned parses. A cancelled await (for example, a `wait_for` cap firing) releases its slot while its parse keeps its thread. `running` counts awaited jobs only, so it under-reports occupancy then. Pinned with a size-1 pool by `test_w04g_cancelled_running_parse_releases_its_slot_and_shows_as_queued`.
- **A stats read that raises** yields no key, and `/health` still answers 200. `AttributeError`, `TypeError`, `KeyError`, `RuntimeError` and `ValueError` are all pinned.

### Gates (measured)
- **Unit files** (`test_retro_w0_4`, `test_retro_w0_4_efg`, `test_price_parse_offload`, `test_verify_flag_byte_identity`, `test_lazy_bh_pdp_backfill`, `test_health_loop_lag`), under a process-wide network guard: **320 passed with the flag unset, 320 passed with =true**, 0 network attempts.
  - The W0-4e2 pins replace the two refuted pool-placement rows:
    - **E2a** `test_w04e2_flag_on_chunked_scan_is_identical_to_findall`: 10 cases on about-5 MB pages. The flag-ON list == `re.findall(base pattern, page, re.IGNORECASE)` == the flag-OFF list, in order with duplicates kept. The cases:
      - matches at CHUNK-1, CHUNK and CHUNK+1;
      - one spanning the first boundary;
      - the same href on both sides of a boundary;
      - matches around every boundary;
      - 300 spread;
      - a page shorter than one chunk;
      - mixed-case hrefs: `HREF=` spanning the first boundary, `/Product/` at the second boundary + 1, `hTtPs`/`pRoDuCt` in an overlap tail, mixed quote kinds spanning the third boundary, plus one lowercase control. The fixture asserts that a case-sensitive `findall` keeps only the control, so the row fails if `re.IGNORECASE` is dropped from EITHER branch.
      - (R15a) an in-domain href of about 4,000 chars (a long query string) starting 1,000 chars before the first boundary, so about 3,000 chars sit past it, plus a short control.
    - **Slice bound** (R14) `test_w04e2_flag_on_scan_slices_are_bounded_and_cover_the_page`, flag ON, the same 10 fixture pages. It is deterministic, with no timing. It asserts:
      - exactly ceil(n/CHUNK) scan calls;
      - every scanned string at most CHUNK + OVERLAP chars (the `re` recorder keeps each string it is handed);
      - the page's slice offsets exactly `(start, min(start + CHUNK + OVERLAP, n))` for `start` in `range(0, n, CHUNK)`, with step 1. The fixture page is a `str` subclass that records every slice key taken of it; `curl_fetch_html(..., cap=False)` returns the same object under the flag;
      - each scan call received exactly its slice's text.
    - **Value pin** (R15b) `test_w04e2_scan_constants_are_the_ruled_values`: `_W04_SCAN_CHUNK == 1_000_000` and `_W04_SCAN_OVERLAP == 65_536`.
    - **E2b** `test_w04e2_flag_on_scan_yields_the_loop_once_per_slice`. Flag ON, the events are exactly scan, sleep(0) × ceil(n/CHUNK), all on MainThread. Flag OFF, exactly one findall and no sleep.
    - `test_w04e2_flag_on_backfill_never_reaches_the_price_parse_pool`: zero `run_parse_offloaded` calls, no pool built.
  - E1/E3/E5/E6/E7 stay.
- **Mutation matrix:** from byte snapshots with sha256-verified restores, each row run in both flag states.
  - **W0-4e2 rows.** Every row is red in both states.
    - **This round:** the ten rows without a dagger (six unmarked + the four marked with a double dagger) were re-run on the final test bytes against the efg file. The four rows marked ‡ also ran against all six unit files, with the same red nodes: X1 '9 failed, 311 passed', step '20 failed, 300 passed', OVERLAP=100 '3 failed, 317 passed', CHUNK=2M '1 failed, 319 passed', identical in both states.
    - **Earlier rounds:** the two `IGNORECASE` rows ran against all six unit files in the previous round. Rows marked † ran in earlier rounds on earlier test bytes; no app byte has changed since.

    | Mutant | Red nodes (efg file) |
    |---|---|
    | Slice end dropped: `html[start:]` (R14 X1) ‡ | 9 (slice-bound pin, every case but the page shorter than one chunk: the first slice received 5,012,345 chars > 1,065,536) |
    | Step `range(0, n, CHUNK * 2)` (R14) ‡ | 20 (slice-bound pin: 3 scan calls where ceil(n/CHUNK) = 6; also E2a, E2b, E1, E6 and the no-pool row) |
    | `_W04_SCAN_OVERLAP = 100` (R15) ‡ | 3 (the long-href E2a case: 1 of 2 matches returned; its slice-bound case; the value pin) |
    | `_W04_SCAN_CHUNK = 2_000_000` (R15) ‡ | 1 (kills the value pin only; every identity and yield row stays green, a tuning equivalent for them) |
    | OVERLAP=0 | 11 |
    | Dedupe dropped | 14 |
    | `sleep(0)` removed | 1 (E2b) |
    | Whole-page findall + one sleep | 12 (E2b's ceil(n/CHUNK) count, the slice-bound pin, the no-pool row) |
    | `re.IGNORECASE` dropped from the flag-ON `finditer` | 2 (the mixed-case E2a case and its slice-bound case) |
    | `re.IGNORECASE` dropped from the flag-OFF `findall` | 1 (the mixed-case E2a case) |
    | Dedupe `<=` † | 1 |
    | Base inline findall under the flag † | 2 |
    | r2 pool offload kept † | 2 |
    | Slices scanned on a worker thread † | 2 |
    | `_accept` loop on a worker thread † | 2 |
    | ON pattern changed † | 14 |
    | OFF pattern changed † | 14 |
    | Chunked scan applied flag OFF † | 1 |
    | Last slice's sleep skipped † | 1 |

  - **The 15-row design matrix P01–P15.** P03, P04 and A4 (the pattern changed inside the pool block) pinned the refuted pool placement. They are superseded by the rows above: base-inline-under-the-flag, `_accept`-on-a-worker, and ON/OFF pattern changed.
  - **The five killed hardening mutants**, all killed: `N_curl_cap_flag_true_only_literal`, `N_render_cap_flag_true_only_literal`, `N_ues_text_trunc_on`, `N_harness_compare_intersection_only`, `N_harness_compare_whole_payload_not_results`.
  - **The R7 additions:** locked-check dropped, waiting not decremented on a cancelled acquire, cap read flag OFF, and the `ues` cap applied before the flag read.
  - **The review rows:**
    - running decrement not in `finally`;
    - `sem.release` not in `finally`;
    - `queued` hard-coded;
    - snapshot try/except removed;
    - catch narrowed to AttributeError;
    - `jobs_total` not counted;
    - the #185 import form in `extract_from_url`;
    - stats returning the shared dict.
  - **Total:** 51 rows run across the rounds, all red in both states. `CHUNK = 2_000_000` reddens only the value pin. Every row outside the W0-4e2 table ran in earlier rounds, and no app byte has changed since.
- **CI-order set** (32 files, one process): 969 passed, 1 skipped (the previous round's 957 plus the 12 new nodes). The only failures are the three `tests/test_security_hardening.py` SSRF nodes. They need real DNS for example.com, fail identically at `61585c58` under the guard, pass without it, and belong to the hermeticity unit.
- **Comm set** (362 files, CI runner + deselects; every chunk holds files referencing `structured_comparison_service`).
  - **This round**, chunk 07 was re-run; it is the chunk holding `test_retro_w0_4_efg.py`. It had 775 passed and 1 skipped (the previous round's 763 plus the 12 new nodes). Its one failure is `test_rate_limiting_complete::TestUrlDetectSsrf::test_detect_allows_valid_url`, the DNS-dependent node below, which fails alone too (the guard blocks `getaddrinfo` for amazon.ae).
  - **Previous round**, all 10 chunks ran: 13,344 passed. There were 4 failures, all DNS-dependent SSRF nodes: the three above plus `test_rate_limiting_complete::TestUrlDetectSsrf::test_detect_allows_valid_url`. Each was re-run alone at HEAD and at `61585c58` (a detached scratch worktree, removed afterwards), and fails identically.
  - Only the efg test file has changed since, so the other nine chunks stand.
- **Corpus** (read-only `_proof`, 414 pages / 1,656 calls):
  - NOT re-run. This round changes no app byte. The W0-4e2 change is confined to `_lazy_bh_pdp_backfill` plus the two constants only it reads, and the harness calls `extract_price_from_html` directly, so it never enters the backfill.
  - The digests stand from the earlier round, on bytes identical in every other app line:
    - OFF with R-W04's four forced-off flags: `OVERALL 9504e5a94a218969764c8cbfdb43243da7bfcd8e0950bb5fb9148b9a9258ce99`, results `a1b3460c28579fab605287e1b5a05dd9cb8a3b07782573dfb5aac005104c59d8` (407 s). This is the recorded R-W04 value. The OVERALL digest also hashes the forced-off list, so a single-flag run prints `994b623e…` over the same results.
    - ON `--compare`: `equal=True`, `DIFFERING RECORDS 0 of 1656` (134 s).
- **Lint:** ruff `E9,F63,F7,F82` is clean and py_compile is clean on the four app modules and both test files. CRLF hygiene holds, and `scripts/` is unchanged.

### Stated limits
- **W0-4e scan OVERLAP limit.** An href longer than `_W04_SCAN_OVERLAP` (65,536 chars) that starts near a slice end is missed. Such an href is not a URL. The value is pinned, and an about-4,000-char href across a boundary is pinned found.
- **W0-4e chained-href boundary corner (measured, not pinned).**
  - **Where it can happen.** A slice boundary falls inside a kept match whose URL text ends in the literal `href=` right before its closing quote, so that quote also opens the next URL. Nothing else triggers it: the pattern's classes exclude quotes, so a second match can start inside a kept match only at such a trailing `href=`.
  - **What changes.** `findall` resumes after the kept match's end. The next slice instead restarts at the boundary, inside the kept match. It collects a match `findall` never sees, and it can then skip one that `findall` returns. So the flag-ON list can be DIFFERENT, not merely longer.
  - **Reproduced through the real `_lazy_bh_pdp_backfill`,** with the boundary 20 chars into `href="https://bahrain.sharafdg.com/product/aaa-href="https://…/product/bbb-href="https://…/product/ccc/"`:
    - `findall` and flag OFF return `[…/aaa-href=, …/ccc/]`;
    - flag ON returns `[…/aaa-href=, …/bbb-href=]`.
  - **Pure-re fuzz** (previous round: 3,000 pages, 400-char slices, 300-char overlap, mixed case and both quote kinds):
    - Without chained URLs, the chunked scan equals `findall` on every page (59,270 matches).
    - With chained URLs, the R11 scan differs from `findall` on 1,533 of 3,000 pages. A resume guard differs on 885. The continuation form differs on 0.
  - Real HTML does not produce a URL ending in `href=`, and every candidate still passes `_accept`'s gates. See follow-up W0-4e3.
- **W0-4e cost.** The flag-ON backfill still pays O(page) regex time on the loop.
  - It pays it in 1 MB turns. On a realistic-markup page on this box, one turn costs about 12–18 ms (the standalone per-slice scan cost). The measured worst loop gap is 0.03–0.04 s typical, against 0.29–0.68 s inline on 30–40 MB.
  - It also holds the whole uncapped page in memory, exactly as at base with the flag OFF. `curl_fetch_html` has no size limit.
- `fetch_page` (httpx, `ues`) is uncapped in both states.
- The corpus harness calls `extract_price_from_html` directly, so it observes neither the cap nor the W0-4c/e/f sites.
- Five over-cap corpus files remain unresolved by the manifest.
- The stats counters are approximate if several event loops share one process (tests only).
- After an ON→OFF flip, the `/health.price_parse_pool` key and its counters persist until a restart (see the contract).
- Exactly TWO production-equivalent mutants are recorded, not pinned: `N_sem_size_check_removed` and `N_pool_size_read_every_call`.
- Nit for the hermeticity follow-up: `extract_with_ai`'s existing `from app.services.price_service import run_parse_offloaded` still uses the sys.modules form. It is not this unit's hunk (R2).
- The three SSRF nodes in `tests/test_security_hardening.py` belong to the hermeticity unit.
- The 674 pre-existing blocked network attempts in the previous round's full comm run are #184.

### Follow-ups
- The `extract_with_ai` import-form nit.
- **W0-4e3: the chained-href corner above**, if Fable wants the scan exact. The continuation form is the candidate.
  - **Exact (the candidate):** use `findall`'s own continuation. Resume each slice at `max(slice start, previous kept match end)`, and end a slice at its first match starting at or past `start + CHUNK`. In the pure-re fuzz it matched `findall` on all 3,000 pages, chained or not. On the example above it returns `[aaa-href=, ccc/]`.
  - **Not exact:** skipping a match that starts before the previous kept match's end. On the example it returns `[aaa-href=]`, losing `ccc`. It differs from `findall` on 885 of 3,000 chained pages.
- #184 (curl_cffi netguard).
- #185 (`sys.modules` re-import class).

### CLAUDE.md corrections for the docs PR
- **The W0-4 row gains:**
  - **W0-4e:** the backfill exempts itself with `curl_fetch_html(..., cap=False)`, so the href past 3 MB is found under the flag.
    - Its scan runs on the loop in 1 MB slices (`_W04_SCAN_CHUNK = 1_000_000`, overlap `_W04_SCAN_OVERLAP = 65_536`, both value-pinned), yielding with `sleep(0)` after each.
    - It never runs on the pool, because `re` holds the GIL.
    - Measured on a realistic-markup 30–40 MB page, the max loop gap is ~0.03–0.04 s chunked, against 0.29–0.68 s inline. The chunked gap is about twice the ~0.016–0.018 s idle floor: one ~12–18 ms slice plus timer granularity.
  - **W0-4f:** the three `ues` extractors run on the pool under the flag, and the `ues` parse input is capped at 3,000,000 chars, including `extract_with_ai`'s html.
  - **W0-4g:** `/health.price_parse_pool` is present only once the pool has been built, and it persists after an ON→OFF flip until a restart. The pool build logs `[PRICE-PARSE] pool built workers=N` once.
  - The "Stated limit … W0-4e" sentence is replaced accordingly, and the chained-href corner is named as follow-up W0-4e3.
- **Activation step (2)** watches `/health.price_parse_pool.waiting | peak_waiting | queued` together with `loop_lag_ms` / `loop_lag_max_60s_ms`.
  - `peak_waiting >= 1` means queueing happened.
  - `queued` is transiently non-zero on hand-offs (0–3 of 60 samples), so only a `queued > 0` that persists across polls signals orphaned parses holding pool threads.
  - A rollback does not remove the key until a restart.

### Evidence base
- The 32-file CI-order set (`.qa-s68/ci_order_set.txt`).
- The 362-file comm set (`.qa-s68/comm_set.txt`).
- The spec `.qa-s68/W0_4EFG_SPEC.md` and the rulings `.qa-s68/RULINGS_W04EFG.md` (R1–R16).

Refs #196, #184, #185.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---
Session 68 unit W0-4e/f/g. Pipeline: red (43 reds / 48 pins) -> Fable gate R1-R10 -> green -> adversary r1 (GIL escalation) -> Fable R11-R13 (chunked yielding scan) -> fix r3/r4 -> adversary r4 DEFECTIVE (slice bound unpinned) -> Fable R14-R16 -> fix r5 -> adversary r5 SOUND. Rebased onto 04acb757 with byte-identical app shas; ship checks and the post-rebase corpus gate recorded in the PR comments.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

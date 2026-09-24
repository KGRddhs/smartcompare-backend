## Retro-fix R-W04 (W0-4 parse-once offload (#135, merged in session 65 without review))

Retroactive adversary sweep (session 66, audit lens C) reproduced these defects on `origin/main`; this PR is the TDD fix: red (Fable-gated) -> green -> adversary -> fix -> re-adversary, all on Opus 5.5 agents with Fable gating, on the pinned CI stack.

**Everything sits inside the EXISTING `ENABLE_PRICE_PARSE_OFFLOAD` (default OFF, read per call; no new flag). Flag OFF is byte-identical to base**, measured on the frozen corpus (OFF `OVERALL 9504e5a9...`, results `a1b3460c...`, equal to a same-environment `origin/main` run) and by the 289-file comm gate (base == head: only the two `test_page_scraping` baseline ids); flag ON `--compare` OFF: **0 of 1,656 records differ** with the cap in place; 11 corpus records exceed 3,000,000 chars and none moves under the cap (0/88 comparisons).

**Verdict:** the session-66 red was KILLED mid-run; session 67 resumed it (44 right-reason reds / 59 pins, satisfiability proven with a prototype green on a scratch `origin/main` worktree) -> Fable gate (the sixth site `StructuredComparisonService._fetch_page_price` stays in scope; `copy_context().run` mandatory; the semaphore is a SUBMISSION-DEPTH contract acquired before submit and created per event loop) -> green (112 unit nodes in both flag states; 32/32 mutants killed incl. the reviewer's M6 lxml-when-ON and the prototype variants; comm 289 files 11,093 passed / the 2 baseline failures) -> adversary r0 SOUND (no code defect, 6 prove-nothing rows) -> fix (test-only: every round-0 survivor killed) -> adversary r1 **SOUND** (5 minor test-side notes, no code defect).

**What the flag now does ON (as amended):** `curl_fetch_html` and the firecrawl / scrapedo render legs hand at most `PRICE_FETCH_MAX_BYTES` = 3,000,000 chars to the parse (mirroring `curl_fetch_html_same_site`; the provider-attempt `html_kb` telemetry keeps the raw body size in both states); the six sites that still parsed INLINE on the event loop - `fetch_iherb_price`, `fetch_bolo_price`, `fetch_boutiqaat_price`, `_try_pharmacy_urls`, `url_extraction_service.extract_with_ai`, `StructuredComparisonService._fetch_page_price` (the earlier CLAUDE.md sentence that iHerb 'already parses inside a run_in_executor lambda' was FALSE) - each move their pure-sync parse block into ONE offload call; every offloaded parse (the three original sites too) runs on a dedicated `ThreadPoolExecutor(thread_name_prefix='price-parse')` sized by `PRICE_PARSE_MAX_WORKERS` (default 4, clamped 1..16; unparsable, empty and non-finite fall back to 4; read once when the pool is built) behind a per-event-loop `asyncio.Semaphore` of the same size acquired BEFORE submit (queued parses wait in asyncio, cancellable, never in the executor's work queue), entered through `contextvars.copy_context().run` so the resolved-category ContextVar reaches the worker (a bare `run_in_executor` fails 9 ContextVar pins); a source-level AST guard keeps the inline-parse allowlist EMPTY. Harness: `scripts/verify_flag_byte_identity.py --flags-on <flags>` (restores the prior env, including unset) and `--compare <other-results.json>` (results-array sha equality + the first differing records, exit 1 on mismatch, occurrence-keyed).

**Measured residual (the reviewer's minor defect, now bounded, not removed):** offloaded real parses of the largest (3.9-4.1 MB) corpus pages still cost the loop 35-143 ms single and 171-534 ms with six at once (six median pages 142-174 ms) against 1,089 ms inline; the CPU-bound heartbeat bound holds at the three shipped sites (~32 ms, the Windows timer floor) and is pinned at all nine.

**Stated limits / follow-ups:** W0-4e - under the flag the 3 MB cap also bounds `structured_comparison_service._lazy_bh_pdp_backfill`'s regex scan of a curled search page (an href past 3,000,000 chars is no longer found; pinned flag-OFF only); W0-4f - `url_extraction_service.extract_from_url`'s three soups (`extract_amazon_data` / `extract_noon_data` / `extract_generic_data`) still build on the loop (allowlisted in the transitive AST test); the corpus harness cannot observe the cap (it calls `extract_price_from_html` directly); five over-cap files on disk are unresolved by the manifest (3.15-3.96 M chars plus one 10.48 M DACH page); the r1 adversary's five test-side notes (the reader tested with 'true' only at one site; a 4,000-char text-truncation blind spot in the extract_with_ai prompt pin; two harness `--compare` edge cases unpinned; two equivalent mutants) - test-hardening follow-up W0-4g.

**CLAUDE.md corrections carried by the docs PR:** delete the '50 ms heartbeat ticked 0 times' claim and the false iHerb sentence in the W0-4 row; activation step (2) gains the pool sizing + queue-depth / `loop_lag_ms` watch and the residual.

---

R-W04 retro: finish W0-4, the ENABLE_PRICE_PARSE_OFFLOAD unit (3 MB cap, six more parse sites off the loop, a bounded parse pool, flag-ON corpus gate)

## Defects (retro adversary verdict DEFECTIVE, on PR #135 / merge 67f716f2)
1. **The 3 MB cap was never built (major).** The wave plan said "land the 3 MB cap in the SAME change". curl_fetch_html had no bound, and the firecrawl/scrapedo render-leg HTML went into the offloaded parse uncapped.
2. **Six async sites still parsed on the event loop (major), and CLAUDE.md made a false claim.** CLAUDE.md says fetch_iherb_price "already parses inside a run_in_executor lambda"; that lambda wraps only curl_requests.get. The six sites:
   - fetch_iherb_price
   - fetch_bolo_price and fetch_boutiqaat_price
   - _try_pharmacy_urls (its extract_jsonld_price soup)
   - url_extraction_service.extract_with_ai
   - StructuredComparisonService._fetch_page_price (found by the empty-allowlist AST guard)
3. **Parses shared the 40-worker default executor (major).** One compare already oversubscribes it. A flagged parse queued behind adapter jobs, a cancelled await left a zombie parse, and nothing bounded the queue.
4. **The off-loop tests proved placement, not latency (minor).** The stub was time.sleep, which releases the GIL.
5. **The harness could only force flags OFF (minor).** So "flag ON causes no result change" was asserted, never measured.

## Fix (everything under ENABLE_PRICE_PARSE_OFFLOAD; default OFF; read per call; no new flag)
- **W0-4b cap.** price_service.PRICE_FETCH_MAX_BYTES = 3_000_000. Under the flag:
  - curl_fetch_html returns resp.text[:PRICE_FETCH_MAX_BYTES], mirroring curl_fetch_html_same_site.
  - _extract_price_from_html_maybe_offloaded caps the render-leg html before the parse.
  - The provider-attempt html_kb telemetry still reports the raw vendor body in both flag states.
- **W0-4d pool.** price_service.run_parse_offloaded(fn, *args, **kwargs):
  - A lazily created ThreadPoolExecutor(max_workers=PRICE_PARSE_MAX_WORKERS, thread_name_prefix='price-parse').
  - PRICE_PARSE_MAX_WORKERS is int(value.strip()) clamped to 1..16. Unset, empty, unparsable, inf and nan fall back to 4.
  - An asyncio.Semaphore of the pool's size is created per event loop and acquired BEFORE submission.
  - The job runs through contextvars.copy_context().run, which keeps the asyncio.to_thread semantics. The resolved-category ContextVar reaches the worker.
  - All nine offloaded sites use this pool.
- **W0-4c sites.** Each moves its pure-sync parse block into ONE offload call. Module globals resolve at call time, and flag OFF runs the same block inline.
  - bolo, boutiqaat and iherb: the block becomes a nested _w04_parse_block (git diff -w shows only the def, the if/await and the call lines).
  - pharmacy: the extract_jsonld_price call is offloaded with identical arguments.
  - extract_with_ai: a nested block, gated by a module-local flag reader, so the flag-OFF path never imports price_service.
  - scs._fetch_page_price: routed through _extract_price_from_html_maybe_offloaded.
- **Harness.** scripts/verify_flag_byte_identity.py gains:
  - --flags-on: forces the named flags to 'true' for the sweep and restores the prior value, including unset.
  - --compare <other.json>: prints both results-array SHA-256s and their equality, the count of differing records keyed on corpus/url/gate/leg/occurrence, and the first --compare-max records (default 5). It exits 1 whenever the results digests differ, whatever it prints.
  - A flag named in both --flags and --flags-on exits 2 before any extraction.
  - Without --flags-on the payload keeps exactly its 6 historical keys, so every recorded OVERALL digest reproduces.

## Pins added after the adversary pass (tests only; no production bytes changed)
The retro adversary listed 0 defects and 6 tests that proved nothing. Each is now a real pin, and every surviving mutant is killed:
- **extract_with_ai prompt.** test_w04c_extract_with_ai_sends_the_same_prompt_flag_on_vs_off captures the LLM prompt. It anchors the flag-OFF 'Page Title:' and content slots, then requires the flag-ON prompt to be byte-identical. Kills the title/text swap in either branch.
- **Pharmacy query_name.** test_w04c_pharmacy_passes_the_query_name_gate_in_both_flag_states uses a page the S4 query-name gate decides: a brand-field-only match on an unrelated same-brand product, priced when ungated and rejected when gated. Both flag states must return None. Kills dropping query_name in either branch.
- **--compare occurrence keying.** A corpus with one URL listed twice; tampering the first occurrence must report "DIFFERING RECORDS 1 of 12" with occurrence=0.
- **Exit status follows the results digest.** With --compare-max 0, a mismatch still exits 1 while printing no DIFF lines. An equal comparison exits 0. A flag named in both lists exits 2, never runs the extractor, and leaves the env untouched.
- **Flag readers.** The price_service, structured_comparison_service and url_extraction_service readers must agree over 18 values (unset, case and whitespace variants of true/1/yes/on, and non-values). Each W0-4c site must offload under '1', 'yes' and 'on'.
- **Cap boundary.** curl_fetch_html and both render legs are checked at 2,999,999 / 3,000,000 / 3,000,001 / 3,500,000 / 4,110,284 (the corpus maximum). Flag ON must give exactly min(len, 3,000,000); flag OFF the whole body.

## Flag row (CLAUDE.md, W0 table)
`ENABLE_PRICE_PARSE_OFFLOAD` (W0-4 + R-W04 retro, default OFF, read PER CALL; the readers accept true/1/yes/on, case- and space-insensitive, identically in all three modules).
- **Effect ON:**
  - extract_price_from_html builds one soup, shared across its three JSON-LD passes.
  - Nine async sites parse on the dedicated bounded 'price-parse' pool, behind a per-loop semaphore of the same size. The sites are fetch_page_price, the firecrawl and scrapedo legs, iherb, bolo, boutiqaat, pharmacy JSON-LD, url extract_with_ai and scs._fetch_page_price.
  - curl_fetch_html and the render legs hand at most 3,000,000 chars to the parse.
- **Knob:** `PRICE_PARSE_MAX_WORKERS` (default 4, clamped 1..16; unparsable or non-finite gives 4). It is read once per process, so changing it needs a restart.
- **Flag OFF:** byte-identical. Four soups, every parse inline, no cap, and the pool is never created.

## Activation gate (the corrected W0 step 2)
Flip after ENABLE_OFFLOOP_DNS_RESOLVE, in its own window. The bounded pool ships here, so the pairing with the never-built ENABLE_PREFETCH_CONCURRENCY_CAP is dropped. Watch:
- /health loop_lag_ms and loop_lag_max_ms. Expect a NON-ZERO residual; see below.
- price-parse queue depth and semaphore waiters (not instrumented yet; follow-up W0-4g).
- Process RSS.
- The genuine vs Tier-3 price share. A drop means parses are missing the 15 s race.

Measured, flag OFF:
- HEAD OVERALL 9504e5a94a218969764c8cbfdb43243da7bfcd8e0950bb5fb9148b9a9258ce99, results a1b3460c28579fab605287e1b5a05dd9cb8a3b07782573dfb5aac005104c59d8 (427 s).
- Same-environment origin/main cb1c64cb: the same two digests (465 s), with byte-identical payload files (sha 414a17eb...).

Measured, flag ON, via --flags-on and --compare against OFF: results a1b3460c... on both sides, equal=True, 0 of 1656 records differ (176 s). The cap is in place in this run.

## CLAUDE.md corrections for the docs PR (not edited here)
- **The W0-4 row:**
  - Delete "a 50 ms heartbeat ticked 0 times" as off-loop proof. It proves placement only; the CPU-bound variant now bounds the max loop gap.
  - Delete the false sentence "price_service.py:15425 (fetch_iherb_price) already parses inside a run_in_executor lambda and is deliberately untouched". The lambda wrapped only the curl GET, and iHerb now parses on the pool under the flag.
  - Add the cap, the pool, the knob and the nine sites.
- **W0 ACTIVATION ORDER step (2):** replace "pure latency/CPU placement, no result change (the corpus gate proves it)" with the measured basis: results sha a1b3460c... on both sides, 0 of 1656, OFF OVERALL 9504e5a9.... Add the bounded pool, the watch list and the residual. Drop the pairing with ENABLE_PREFETCH_CONCURRENCY_CAP, which does not exist.
- **Measured residual loop gap.** Setup: flag ON, 5 ms heartbeat, pool 4, input capped at 3 MB.
  - Single ~4 MB page: 32–167 ms.
  - Six large pages at once: 216–235 ms.
  - Six median ~390 KB pages at once: 78–192 ms.
  - Inline with the flag OFF: 926 ms.
  - The red phase, with asyncio.to_thread and no cap: 35–143 ms single, 171–534 ms six at once, 1089 ms inline.
- **Corpus facts:** 11 of 414 records exceed 3,000,000 chars (3,030,808–4,110,284). Across 88 capped-vs-whole comparisons, 0 move.

## Honest limits
- **The corpus harness cannot observe the cap.** It calls extract_price_from_html directly. The cap evidence is a separate probe (88 comparisons, 0 moved) plus the unit boundary pins.
- **The cap applies to every curl_fetch_html caller under the flag, including structured_comparison_service._lazy_bh_pdp_backfill.** That caller regex-scans a curled search page, and with the flag ON an in-domain /product/ href past 3,000,000 chars is no longer found. Only the flag-OFF behaviour is pinned.
- **The GIL residual is real.** The pool moves the parse off the loop but cannot stop CPU-bound Python from contending for the GIL.
- **A cancelled await releases its semaphore slot while the zombie parse keeps its thread.** The executor queue can briefly hold about one extra job per zombie; it stays bounded by N.
- **PRICE_PARSE_MAX_WORKERS is read once per process.**
- **run_parse_offloaded reads ThreadPoolExecutor._max_workers**, a private attribute, to size the semaphore. The pool-size tests pin it.
- **Five over-cap files in _proof are not in the manifest**, including a 10.48M-char DACH page. The gate cannot see them.

## Follow-ups
- **W0-4e:** exempt the _lazy_bh_pdp_backfill caller from the cap, or raise it for that caller.
- **W0-4f:** url_extraction_service.extract_from_url still builds soups on the loop, through extract_amazon_data, extract_noon_data and extract_generic_data. It is allowlisted in the transitive AST test and out of scope here.
- **W0-4g:** export price-parse queue depth and waiters to /health or logs for the canary.
- **Reviewer minor:** lxml (pinned, never imported) or process-level offload if the residual is unacceptable. Each would be its own unit.

## Verification
- **Units:** 185 of 185 pass with the flag unset and with it =true, under a process-wide network guard (test_retro_w0_4 157, test_verify_flag_byte_identity 19, test_price_parse_offload 9).
- **Comm gate** over the recorded 289-file set: 11,097 passed and 2 known test_page_scraping baseline failures; comm -13 is empty; 0 hangs.
- **Mutation:**
  - The green's matrix: 32 of 32 killed, including the reviewer's M6, the unflagged cap, no-copy_context and no-semaphore.
  - The fixer's matrix: 16 of 16 killed, including all 8 adversary survivors.
- **Lint:** ruff E9,F63,F7,F82 clean; py_compile clean.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

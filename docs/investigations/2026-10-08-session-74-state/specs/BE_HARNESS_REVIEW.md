# BE-HARNESS adversarial spec review (session 74, 2026-10-08)

Spec: s74-state/specs/BE_HARNESS_SPEC.md, sha256 5d6e182094461c093a4fdea5e554a938ded580c4c1822b2e417458ada4bc25a4 (re-hashed, matches).
Code read in sc-docs-70 (HEAD 415e0835). 1898809a and 3b24d182 are NOW in the local object stores: `git diff --name-only 415e0835 1898809a` has no non-docs path (spec A10 VERIFIED); `git diff 1898809a 3b24d182` touches none of the cited files (only scripts/seed_spec_spine.py and scripts/shadow_experiments.py, +1 line each). Every cite below holds at 1898809a and at current main 3b24d182.
Measurements (hermetic, no app import, no .env, no network): notes folder be-harness/review/ probe_rows.py + probe_rows.log, probe_rows2.py + probe_rows2.log (AST-extracted `_clean_specs` and `_build_specs_rows`).

VERDICT: CHANGES REQUIRED before RED. Two blocking defects (F1, F2): the rule as written can PASS a compare whose spec table is all placeholders, and it never applies R3-R10 to the stream, which is the app's primary compare path. Five majors/minors change the exit contract and the fixtures.

## Findings

### F1 BLOCKING - R7 counts placeholder rows: an all-"N/A" spec table passes
- `_build_specs_rows` skips a field only when a value is None or "" (response_builder.py:752-753). `_clean_specs` stamps every None / "" / "null" spec value as the string "N/A" before the build (structured_comparison_service.py:3258-3259; the flag-OFF extractor does the same, extraction_service.py:1678-1680). The builder's own no-data set is `_SPEC_NA_TOKENS = {"n/a","na","none","unknown","-",""}` (response_builder.py:625), but the rows builder does not use it.
- MEASURED (probe_rows2.log case A): LLM specs with every field null for both products -> rows [display N/A|N/A, ram N/A|N/A, battery N/A|N/A] -> R7 PASS. That is the thin-snippet state the canaries ran in today (Serper ConnectTimeouts, ledger 14:07-14:24).
- Second path (case D): a hard-cap partial built from the EARLY buffer ships RAW specs. The buffer receives `_get_specs` output as it lands (structured_comparison_service.py:5438-5448, 5291), before `_clean_specs` runs at :5649-5650, and the stream partial always reads the early buffer (:3436-3438). Raw specs keep brand / model / error / `*_source` keys (extraction_service.py:1609, 1653-1657, 1716), and the rows builder emits them -> rows [brand, model, error, ram_source] -> R7 PASS with zero real specs.
- Case B: the cleaned specs-error dict gives rows [] and R7 FAILs, so the normal sync error path is caught. The holes are cases A and D.
- FIX: R7 counts only REAL rows, where `field` is not in {brand, model, variant, category, error, name}, does not end in "_source", does not start with "_", and BOTH p0_value and p1_value are non-blank and `str(v).strip().lower()` is not in `_SPEC_NA_TOKENS` (copy the set into the script, cite :625). It needs >= 1 real row. Report `spec_rows` (all rows) and `spec_rows_real` (real rows). BH09 gets three cases (rows []; all-N/A rows; identity/error rows only), each -> rc 1. BH20 gets the same three.

### F2 BLOCKING - the stream terminal payload is never held to R3-R10, and "last terminal" is not what the app renders
- The stream is the app's PRIMARY compare path (text_routes.py:1123-1126 comment; api.ts:815-842). Its terminal payload is a full `build_comparison_response` body, or `_build_partial_response` on the hard cap (structured_comparison_service.py:4565-4566, 4351-4352). The spec checks only `data.success is True` (S4), so a success:true partial with no pros/cons, no real specs and no price passes S1-S4.
- Evidence it happens: canary2's stream had 8 event/data lines = 4 frames in 32.7 s (canary2 log, line 6), against 24 lines in canaries 1/3/4/5. That count is consistent with status, status, settle_complete, complete, i.e. a hard-cap partial carrying success:true (:4555-4566). Its content was not logged (NOT VERIFIED). If the q-form compares pass, the new canary still exits 0 with the app path degraded.
- The client latches the FIRST terminal (settle_complete or complete) and also treats any `error` frame as an error (api.ts:779-792, 881-910). The spec reads the LAST terminal (S2-S4), so a diverging pair (settle_complete success:false, then complete success:true) passes the canary while the app shows an error.
- FIX: evaluate_stream: (S2) at least one terminal frame; (S3) no `error` frame anywhere in the stream; (S4) EVERY settle_complete/complete frame has `data.success is True`; (S5, new) `evaluate_compare(200, first_terminal_data)` must not be FAIL, and its reasons are carried into the stream row with a `stream_` prefix. A soft NO_PRICE from S5 counts like a compare's NO_PRICE. BH02-BH04 stay. Add BH04b (terminal success:true, empty pros/cons -> rc 1), BH04c (settle_complete success:false, then complete success:true -> rc 1) and BH04d (an `error` frame before a success terminal -> rc 1). This closes the spec's Q3: yes.

### F3 MAJOR - the exit codes collide with Python and argparse, so rc alone cannot be trusted
- `EXIT_SETUP = 2` is also argparse's usage-error exit (`parse_args` raises SystemExit(2)) and the interpreter's "can't open file" exit. The latter is what every recipe still naming the docs path will hit after the `git rm`: runbook :100 (replaced by this unit), U13_ACTIVATION_RUNBOOK_AHMED.md:19, and session-69/71 NEXT_SESSION_PROMPT.md files (`git grep` at 3b24d182). A wrong path then reads as "401/403 setup".
- `EXIT_FAIL = 1` is also Python's exit for an uncaught exception, so a crash reads as "a compare failed".
- In the wrapper, rc = PIPESTATUS[0] of `timeout -k 15 600 railway run ...` (canary/run_canary.sh:12-13): 124/137 = bound hit. `railway run` was measured passing only 0 and 1 through (canary1 rc=1, canary4/5 rc=0); 2 and 3 are NOT VERIFIED.
- FIX: 0 PASS, 1 FAIL, 3 NO_PRICE, 4 SETUP (was 2), 5 CRASH, with a top-level guard in both `main()`s (see F7). Contract for the orchestrator: an rc counts only when the last stdout line starts with `RESULT:`; no RESULT line = NOT MEASURED, whatever the rc (2 = usage or missing file, 124/137 = bound). Update BH13/BH14/BH15/BH34 to the new constant, and say in the runbook text that a missing RESULT line means "not run".

### F4 MAJOR - an all-pending run exits 3, exactly like a partly-priced run; canary 5 is missing from the fixture table
- canary5 (17:55, the old script, after U3c deployed): all six prices pending_genuine, rc 0, "RESULT: PASS" (canary5 log, lines 3-7). It is the live BE-01 reproduction and it is not in BH06. Under the spec it exits 3. canary4 (2 of 6 priced) also exits 3. "Price stack dead" and "prices thin" are indistinguishable, and the whey pair has had no amount in 5 of 5 runs, so 3 becomes the expected steady state.
- FIX: add run rule R11 `no_price_in_run`. When no compare in the run (q-pairs + probe + stream terminal) carries a positive amount, the run FAILs (exit 1). Exit 3 needs at least one amount somewhere in the run. Warm-up: the same rule over all 12 compares. Add BH06[canary5] -> rc 1 (old script rc 0, so it is a RED-B discriminator). The canary1-3 rows keep rc 1. Note in the spec that the whey pair is structurally unpriced today (5/5 logs), so the owner can choose to swap it for a pair with a local retailer.

### F5 MINOR - the runbook does not say what to do for each exit code, and the first real run may not give the fixture verdicts
- The new A1.8 text lists the codes but not the action. Step 9 ("Revoke the old key", runbook :114) is not gated. Add one line: "0: continue. 3: OpenAI verified, prices thin (the FANOUT-STARVE unit); continue to step 9 and send Claude the lines. 1/4/5: stop and send Claude the lines. No RESULT line: the run did not happen."
- None of the five logs records pros/cons, rows or `comparison` (old script fields only). The BH06 expected exits are DERIVED from healthy-filled fixtures, not measured. The first real run may FAIL on R8 or R7 where the old script passed. The spec should label BH06 as derived and the runbook should not promise exit 3 for today's prod.

### F6 MINOR - an amount counts even when the price is marked unavailable or estimated
- R9/R10 read only `overview.products[i].price.amount`. The price chokepoint pends estimated and non-showable prices inside a try/except that logs "price-pending normalization skipped" and ships the price unchanged on any error (response_builder.py:1610-1729). An estimated amount then passes R10.
- FIX: a positive amount also needs `price.get("unavailable") is not True` and `price.get("source_method") != "estimated"`. A non-dict price = no amount, no retailer. Add BH20 cases (amount 5 + unavailable true -> no amount; amount 5 + source_method estimated -> no amount; price None -> no amount).

### F7 MINOR (secret hygiene; no leak in the spec as written, these are hardening) - exceptions and logging
- MEASURED (venv source): h11 builds `LocalProtocolError("Illegal header value {!r}" % value)` with the raw header value (h11/_headers.py:166). A key pasted with a trailing space or newline therefore puts the whole admin key into str(exc) on every request. httpx.LocalProtocolError is an HTTPError, so the spec's class-name-only catch covers it, but no node pins it. FIX: parametrize BH16 / BH36 over ConnectError, LocalProtocolError and ReadTimeout, each carrying the sentinel in its message.
- MEASURED: httpx.InvalidURL, StreamConsumed and CookieConflict are NOT HTTPError subclasses. A non-ASCII key raises UnicodeEncodeError at Client construction (httpx/_models.py:82), outside every per-request catch; its message names one character of the key and its position. Any exception that escapes prints a traceback with str(exc), and run_canary.sh:12 pipes stderr into the log. FIX: a top-level `try: ... except Exception as exc:` in both `main()`s (and around the Client construction) that prints `RESULT: FAIL error=<ClassName>` and returns EXIT_CRASH, never str(exc) or a traceback. BH node: the Client factory raises UnicodeEncodeError built from the sentinel -> rc 5, sentinel absent.
- State in the spec: no `logging.basicConfig` or handler setup (httpx/httpcore log request lines at INFO/DEBUG only when configured); no CLI option takes a key VALUE; no argparse default is read from the environment.
- `base` is echoed to stdout and the report. A `--base` with userinfo (`scheme://user:pass@host`) would be printed. FIX: refuse a base containing "@" (exit 4, `setup=base_userinfo`) or print scheme://host only.

### F8 MINOR - R8 is the only proof that the verdict ran; say so, and record the strictness as deliberate
- R5 cannot fail on a built 200: `overview.winner.name` falls back to the product name (response_builder.py:1850-1852). R4 passes a partial whose verdict never ran (`comparison = self._partial_comparison or {}`, structured_comparison_service.py:3486, deterministic fill only of winner text :3521-3527). Pros/cons are popped out of the VERDICT response (structured_comparison_service.py:4110-4117, 4888-4895), so R8 is the real verdict proof.
- Known model behaviour: pros/cons keys were absent on cold probes (extraction_service.py:2635-2637), and W4-11 measures empty cons sides (:2729-2735). Per-product cons will sometimes FAIL a healthy-looking compare. Keep R8 per product, write the reason above into A3 so nobody relaxes it, and report `pros` / `cons` counts per side (the spec already does).

### F9 MINOR - test precision and fixture realism
- BH07, BH14, BH30, BH34 and BH38 must count compare requests with `request.url.path == "/api/v1/text/compare"`. U13 H10 uses `startswith`, which also matches `/stream` (test_s71_u13_harness_auth.py:381). Copying that idiom makes "exactly 1 compare request" count the stream.
- BH09 and BH20 fixtures must use the real wire shapes from F1 (all-N/A rows; identity/error rows), not only `rows: []`. Otherwise the tests encode the spec's mistaken payload model and pass tautologically.
- BH06 gets canary5 (F4), and the table says "derived" (F5).

### F10 MINOR - U13 H10 calls the new main() with a degraded handler; GREEN must not crash on it
- H10's handler answers every compare with `{"success": true, "products": [], "overview": {"winner": {"name": "u13"}}}` and the stream with `event: complete / data: {}` (test_s71_u13_harness_auth.py:353-359). It then calls `mod.main()` without asserting rc (:369). The new main() must return normally (rc 1: R6, R8 and S4 fire) and must not raise on a missing `overview.products`, a `data: {}` frame or a missing `success` key. Otherwise H10 x2 turn RED at GREEN. Write this in section 3 as a GREEN requirement. The client rule `httpx.Client(timeout=150[, headers=auth])` with no other kwarg stays (:384-391 `built == [{"timeout": 150}]`).

### F11 MINOR - review_warmup must import only pure names from the canary
- The tests shim `review_warmup.httpx` only. Any I/O helper imported from `scripts.verify_after_credits` would use that module's unshimmed httpx. It fails closed under the netguard (tests/conftest.py:37-41) but would make the nodes error instead of testing. Restrict the import to `DEFAULT_BASE`, the `EXIT_*` constants, `evaluate_compare`, `evaluate_stream` (unused) and `_harness_auth_headers`. Add a BH node asserting that the imported names are exactly these. scripts/__init__.py exists and is empty (checked), so the real-name import is safe.

### F12 MINOR - warm-up classification: a cold FAIL hides a warm PASS
- Run 1 is cold and the most likely to hit the 30 s cap or a 400 (canary1 Dior 400). Run 2 is what the reviewer will meet. "FAILED if any run FAILs" drops pairs that are fine warm. Keep the conservative class, but add a `COLD ONLY (n):` list (run 1 FAIL, run 2 PASS) so the owner can decide. Runbook line 222 "pass the A1 assertions" is ambiguous here.

### F13 MINOR - the orchestrator's wrapper and live recipes after the move
- canary/run_canary.sh:6 points CANARY at the docs path, and :12 bounds the run at 600 s. After the `git rm`, repoint it to `scripts/verify_after_credits.py` in the smartcompare clone (pull to the merge sha first) and raise the bound to 900 s (spec Q5). U13_ACTIVATION_RUNBOOK_AHMED.md:19 still gives the docs path. Either add a one-line "moved to scripts/verify_after_credits.py" note there, or accept the dangling historical recipe (it exits 2, see F3).

### F14 NOTE - report `metadata.partial_stage` beside `partial`
- `partial_stage` (gather | post_gather | scoring | verdict, structured_comparison_service.py:3431-3445, 3558-3560) says whether the verdict existed when the cap fired. Report it per row (no gate; A4 stands) so FANOUT-STARVE has evidence. Q1: keep partial ungated.

### F15 NOTE - the base moved; no cited file changed
- main is 3b24d182 (U3c #335, after CLIENT-TRUTH #334). Measured: no cited file changed between 1898809a and 3b24d182. RED/GREEN should base on current origin/main, and the RED-B scratch worktree should use that sha.

### F16 NOTE - runbook text nits
- The new E2 text repeats the Tom Ford / Creed drop rule: line 220 kept verbatim already says "Drop this pair if the result is partial". While every compare hits the 30 s cap, PARTIAL may name all six pairs. Keep one sentence.
- "the older `env HARNESS_SEND_ADMIN_KEY=1` form works too": `env` exists in Git Bash, not in PowerShell. Say "(Git Bash)".
- The 429 check moved from the pass list to a manual step. Fine, but keep the words "a pass also needs no 429" so RT-1 is unchanged.

### F17 NOTE (out of scope, app-level; for the orchestrator) - raw specs on mid-gather partials
- The early-buffer partial path ships `_get_specs` output uncleaned (F1 case D). On the specs-extraction exception path that output is `{"brand", "model", "error": str(e)}` (extraction_service.py:1716), and it also carries `_search_snippets` (structured_comparison_service.py:6036). str(e) of an OpenAI client error can quote a key tail (the R-METER note at url_extraction_service.py:659-663 measured exactly that on the URL path). On a cap that fires during the gather, this text could reach `specs.products[i].specs.error` and a `specs_comparison.rows` entry on the wire. Static read only (NOT VERIFIED end-to-end; the timing window is narrow). Candidate for a separate backend unit: `_clean_specs` in `_build_partial_response`.

### F18 NOTE - hermeticity holds (positive checks)
- tests/conftest.py:16 runs `load_dotenv(override=True)`, but tests/_env_safety.py:129 neutralizes ADMIN_API_KEY in the default tier. The netguard is installed at conftest import (:37-41). MockTransport opens no socket. The scripts import stdlib + httpx only. The spec's "set or delete both variables in every node" rule is still needed (nine modules set ADMIN_API_KEY at import).

## Claims verified (file:line at 1898809a = 3b24d182 for these files)
- text_routes.py: 422 both/neither :796-807; region :778; nocache default False :782; limiter :772; `return result` :951; stream :954; event set :1032-1055; first-terminal latch and persist :1117-1166, error frames :1167; frame `json.dumps(data, default=str)` :1215; `_surface_comparison_failure` :521-568; U13 guard :242-345 (401 detail :233, header read :292).
- error_handler.py:113-137 envelope; admin_routes.py:34-58 (403 "Invalid admin key").
- response_builder.py: success :1892; winner :1898-1907; products/pros/cons :1908-1930; specs dict :1963-1981; `_build_specs_rows` :725-762; pend sites :1638-1643, :1695-1701, :1704-1727; legacy alias :2164-2205; comparison alias kept with `error` :2210-2219.
- price_service.py: `make_pending_price` :1928-1941 (the only `"unavailable": True` constructor in app/, grep); every pend site nulls the retailer (:2332-2340, :3096-3104, :3155-3161, :3209-3216). Additional `make_pending_price` sites not listed in the spec (text_routes.py:1595 prices route, structured_comparison_service.py:4703/4709 SSE prices event, :9154 regional route) also null the retailer or ship no mirror, so A2 holds.
- structured_comparison_service.py: terminal pairs :4351-4352, :4369-4370, :4565-4566, :4589-4590, :4612-4613, :5091-5092, :5100-5101; error events :4317, :4418, :4468, :5110; INSUFFICIENT_DATA :3689-3697; partial metadata :3557-3560.
- extraction_service.py:46 and :2771-2773 (verdict error dict); url_extraction_service.py:659-678.
- Runbook: lines 99-113 and 214-222 are exactly the quoted blocks (CRLF, UTF-8 with non-ASCII elsewhere in the file); line 104 = the probe pair; line 110 = "at least one price `amount` non-null"; the six warm-up pairs in spec section 4 match lines 215-220 byte for byte (ASCII apostrophe in L'Oreal); `.qa-*/` is git-ignored (.gitignore:72).
- U13 test: SCRIPTS entry :51-52; `_HttpxShim` :87-97; H07 :221-235 calls `helper()` with no argument; H10 :347-391.
- Old canary traps: :37 (len of the specs dict), :38 (`has_verdict`), :67-68 (pass rule), :43 (stream without region); the stream q-form only.
- Hook regexes .githooks/pre-commit:178, :189-190; .gitleaks.toml `useDefault = true`.

## NOT VERIFIED
- The content of any canary stream terminal or of the 200 bodies beyond the old script's fields (pros/cons, rows, comparison, partial, partial_stage).
- `railway run` passing exit codes 2/3/4/5 through (only 0 and 1 observed).
- `railway run -s web -- <python> ...` from PowerShell.
- Whether the web service's injected environment carries HTTP(S)_PROXY / SSL_CERT_FILE, which httpx honours with trust_env (httpx/_config.py:34-37). The five canaries ran fine, so likely none. Names only via the owner.
- F17 end to end.

## Answers to the spec's open questions (recommendations)
- Q1 partial: report `partial` and `partial_stage`, do not gate (F14).
- Q2 exit 3: keep it, but only when the run has at least one amount (F4). SETUP moves to 4 (F3).
- Q3 stream payload: yes, through evaluate_compare (F2).
- Q4 CLAUDE.md:528: DOCS-CONFIG (out of this unit's file list; the line is unchanged at 3b24d182).
- Q5: raise the wrapper bound to 900 s; keep the 150 s per-request default (F13).

## Files written by this reviewer (sha256)
- this file: reported in the return value (a file cannot carry its own hash).
- be-harness/review/notes.md, probe_rows.py, probe_rows.log, probe_rows2.py, probe_rows2.log: hashes in the return value.
Nothing was written in sc-docs-70, sc-s71-t0b or any clone. No pytest, no railway, no network.

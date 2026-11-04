# S81-G2 ADVERSARY REPORT, lens correctness (+ the folded engineering checks, LC-1 / LC-9), Opus 5.5, 2026-11-04
Filed through the shell (the harness refuses a subagent Write of a report .md).
HEAD verified 07cabe47a7bf052c43ef2c526869d2e36657df99 (branch feature/s81-g2-kb-seed, worktree sc-s81-g2, status empty). The six RED files re-hashed at start and end in sc-s81-g2: 6/6 equal to the frozen sha256 (and equal in the committed blobs). Scratch worktree <scratchpad>/S81-G2_adv_correctness made detached at 07cabe47 (first with the house core.autocrlf=true, then re-made with -c core.autocrlf=false to match CI bytes), removed with git worktree remove --force; absent from git worktree list; every mutated script restored and sha256-equal to HEAD; .qa-mutation.lock created and removed; 0 pytest processes left.

VERDICT: NOT_READY (2 MAJOR, 0 BLOCKING; minors below).

## MAJOR
M1 (spend contract, scripts/seed_kb_batch.py::_apply ~L532-538 with _read_results ~L482-484): when the results stream raises mid-iteration, _read_results returns the records read so far with results_ok=False, and _apply still settles the breaker with actual = the sum of the PARTIAL records (and writes the ledger row from the partial records). The provider bills every succeeded result of the batch, so the offclock lane is credited back (bound - partial) that was in fact spent. Runtime probe (probe_settle.py, synthetic fakes, no network): reserve 5.0; 3 results then ConnectionError -> settle(ticket, 0.03): 4.97 USD of the held bound released. A later --resume (no breaker call by D5) cannot repair it and inserts a SECOND llm_spend_ledger row for the same provider_batch_id, double-counting the first partial records. Spec 2.11 says only 'rows parsed so far are written; no delete' for this case; GREEN chose the non-conservative settle. Fix: when results_ok is False, settle(ticket, None) / record(lane, None, admitted_usd=bound) (the bound stays held, as settle documents for an invalid actual) and skip or mark the ledger row; add a RED-style row (results raise mid-iteration with the breaker ON -> settle receives no partial actual).
M2 (comm set, union rule class (d) CLAUDE.md readers): tests/test_s81_s08b_gate_rows.py reads CLAUDE.md (CLAUDE_MD.read_text, _row_slice bounded by the next column-0 '**SESSION' / '## ' heading: exactly the boundary G2's new block adds) and is NOT in GREEN's 72-file set (nor the RED's 68, nor spec 12.1 (d)). Measured green at HEAD alone: [pyt] tag=g2adv-s08b-rows elapsed=4s bound=600s status=OK rc=0 (29 passed; hermeticity 29; netguard 0) and inside my chunk 3. A missed member that is green is still a MAJOR by the brief; add it (and its base run) to the set and the cache at the rebase.

## MINOR (documentation rulings / stated limits)
m1 (portability of a frozen RED row): R27 asserts b'' not in the script bytes. On a house checkout (core.autocrlf=true, no .gitattributes) the five scripts check out CRLF and R27 goes red: [pyt] tag=g2adv-crlf-r27 elapsed=4s bound=600s status=FAIL rc=1 (5 FAILED test_s16_r27_hygiene_of_g2_files[*]). GREEN is green only because it wrote LF bytes into a CRLF-converting worktree; CI (Linux) is green. The rebase (which rewrites the files through the smudge) and every fresh Windows worktree will show 5 red nodes. Ruling options: a .gitattributes 'eol=lf' line for the five scripts, or record it as a stated limit / known base noise.
m2 (R-G2-11 pin absent): the gate/rulings say R19 pins no_brand; R19 never reads it, and the Woo no-brand skip is unpinned: mutant W-M10 on the Woo path (brand guessed from the title's first word) SURVIVED the whole D09 file ([pyt] tag=g2adv-W-M10 status=OK rc=0). The Shopify variant W-M10s is KILLED by R14. Code behaviour verified correct by reading map_woo.
m3 (GC-4 unpinned): mutant X12 (the D11 origin url_gate before robots.txt removed) SURVIVED the whole D11 file: no row has a persisted record disallowing '/'; the 'skip before robots.txt is read' claim of GC-4 / the PR body / the CLAUDE.md row is true in code but prove-nothing in tests.
m4 (equivalent survivors): D-M5 (the _same_site filter on declared sitemaps dropped) is equivalent given url_gate's origin comparison (an off-origin sitemap is refused by the gate); X6 (PoliteFetcher's 3,000,000 cap dropped) is equivalent in production because default_fetch caps the bytes, and no row pins the second cap.
m5 (deployment hazard, D-G4): the three railway.*.json watch scripts/kb_seed_common.py; a later push touching it redeploys = re-runs all three jobs in whatever mode their flag holds (an APPLY batch spend on kbseed if ENABLE_KB_SEED=apply was left set). Owner step (11) 'set each flag back to unset between deliberate runs' is the mitigation; make it explicit as a stated limit with the #98 reference.
m6 (Q-G1): the opaque batch id at INFO is acceptable by spec 2.8 ('the one value logged is the opaque batch id at submit').
m7: CLAUDE.md row 'the batch deleted after its rows are written' omits 'only when the results read and every write succeeded' (code: if results_ok and writes_ok).

## Runs (every pytest through pyt.py, one at a time; scratch worktree LF unless noted)
[pyt] tag=g2adv-units-off start=2026-11-04 07:40:42 elapsed=14s bound=600s status=OK rc=0 (817 passed; hermeticity 817; netguard blocked 0)
[pyt] tag=g2adv-units-on start=2026-11-04 07:41:01 elapsed=13s bound=600s status=OK rc=0 (ENABLE_KB_SEED=apply ENABLE_FEED_WALKER=apply ENABLE_PDP_DISCOVERY=apply ENABLE_CC_CDX=true for that one call; 817 passed; hermeticity 817; netguard 0)
[pyt] tag=g2adv-crlf-r27 elapsed=4s status=FAIL rc=1 (house CRLF checkout; m1)
[pyt] tag=g2adv-ci-order start=07:53:14 elapsed=74s bound=1200s status=OK rc=0 (spec 12.2, 12 files: 1372 passed; hermeticity 1372; netguard blocked 22 from 21 nodes = the hermeticity self-tests, base noise)
[pyt] tag=g2adv-comm-c1 elapsed=66s bound=1200s status=OK rc=0 (GREEN chunk1, 25 files: 951 passed; netguard 22/21 base noise)
[pyt] tag=g2adv-comm-c2 elapsed=138s bound=1200s status=OK rc=0 (GREEN chunk2, 25 files: 3286 passed; netguard 24/2 S81-04 sentinels)
[pyt] tag=g2adv-comm-c3 elapsed=42s bound=1200s status=OK rc=0 (GREEN chunk3 21 files + tests/test_s81_s08b_gate_rows.py: 1218 passed; netguard 8/8 w49 sentinels)
[pyt] tag=g2adv-secret elapsed=5s bound=1200s status=OK rc=0 (tests/test_secret_scan_static.py alone: 31 passed)
[pyt] tag=g2adv-s08b-rows elapsed=4s bound=600s status=OK rc=0 (29 passed)
HEAD failures in the 73-file set: none. Base record: the cached 74b84ef9... (68 files, EMPTY) + GREEN's appended 3535b18a... (s23) reused (LC-6); test_s81_s08b_gate_rows.py NOT run at base (green at head, so comm -13 is EMPTY either way; its base run is owed at the rebase).
ruff --select E9,F63,F7,F82 --no-cache on the five scripts + tests/test_s81_kb_schema.py: All checks passed; py_compile OK. Bytes > 127 = 0 and CR = 0 on the five scripts and three railway files (committed bytes). Added-line sweep: only the two GC-3 host-list digests (accepted). Client fences: not re-run (no junction in a scratch worktree); GREEN's log read: 14 suites, 4 failed = config/nativeBundle.w37 (accepted drift), 236 passed. Hook test files not run (no .githooks change). PR body 12,259 B (<= 25,600).

## Mutants (byte copies in place in the scratch worktree, exact single-match edits, -x -k on the killing rows, restored + sha256 verified; logs <scratchpad>/S81-G2_adv/mut/)
KILLED (AssertionError) 39: S-M1, S-M4, S-M5, S-M6, S-M7, S-M9, S-M11, S-M13, S-M14, S-M15, S-M18, S-M19, S-M20 (brand APPLY inserts into kb_merchants), S-M21, S-M22, W-M1, W-M2, W-M3, W-M4, W-M5, W-M7, W-M9, W-M10s (Shopify), W-M13, W-M14, W-M15, W-M16, D-M3, D-M4, D-M9, D-M10, D-M11, D-M12, X1 (url_gate deny check dropped), X3 (per-hop gate dropped), X5 (not_built check dropped), X8 (max_tokens guard dropped), X9 (demand_count 1), X11 (delete despite a failed results read), X13 (challenge check dropped), X14 (no_brand log arg dropped).
SURVIVED 4 (whole-file re-run): W-M10 Woo path (m2), X12 origin gate before robots.txt (m3), D-M5 and X6 (equivalent, m4).

## Probed claims (runtime truth)
- Flag readers: run_mode's first statement reads os.getenv; every main's first statement is the mode read (all five entries); OFF logs one INFO with mode=off + the flag and returns 0 before args / client / fetch (R2 green with the full config; S-M4 killed). The OFF identity of app/: no app/ file in the diff (git diff --stat), no app importer of the G2 scripts (P01 rows green).
- Contract freeze (PLAN section 0) / error-handler mapping / R-A3 user billing: not reachable (no route, no app/ file). The only billing surface is the LLM spend breaker: M1.
- url_gate: fail-closed (exception -> bad_url), deny list, live, ToS (require_tos), record origin, rating_host_allowed; PoliteFetcher: robots_registry Politeness + _fetch_following (allow_redirects=False, SSRF validator per hop, may_fetch per hop) + default_fetch (named headers, byte cap): read and mutants X1 / X3 killed.
- KbWriter: builder-key check (X5 killed), insert-ignore, offer re-observation update of KB_OFFER_UPSERT_SET only (W-M13 killed), gap last_seen-only update (D-M10 killed).
- R29: the key is read once at import, passed only to the SDK factory; never formatted in a log, the report or a request (grep of seed_kb_batch.py; S-M18 killed by R20).
- R-G2-3: the brand script has no table write (S-M20 killed by R23).
- GC-1: R7 green against the frozen golden; SEED_RULES / system composition / digest / user layout as GC-1 names (read).
- GC-2: grep of module-alias private names in the five scripts = exactly the 21 names GREEN lists.
- E1 / E2: git diff of tests/test_s81_kb_schema.py is line-identical to the RED's E1_E2.diff (+14 -3, no whole-file diff; CLAUDE.md +6, CRLF kept, 0 bytes > 127 in the diff).
- CLAUDE.md block: column 0 after the S81-10 owner-steps bullet, before '## Tests' (:553 at HEAD), rows D11, D09, S81-16, one merged owner-steps bullet carrying R-G2-8 and R-G2-18; claims match the code except m7 and the unpinned GC-4 (m3).

## Prove-nothing rows
- No D11 row exercises a persisted record disallowing '/' (GC-4 behaviour unpinned, X12).
- No D09 row exercises a Woo product without brands (R-G2-11's skip and count unpinned, W-M10).
- No row pins PoliteFetcher's own 3,000,000 cap (X6).
- No row covers results-raise-mid-iteration with the breaker ON (the M1 path).

## Not measured
The client fences on these bytes (no junction allowed in a scratch worktree; GREEN's log read). The base run of tests/test_s81_s08b_gate_rows.py. Anything against the network.

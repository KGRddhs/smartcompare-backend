# S81-10b LINKS-GATE adversary report, lens correctness (Opus 5.5, 2026-11-04)

Verdict: SOUND (no blocking, no major; three minors for the orchestrator).
HEAD verified 0e936223921ec0dd4bf70061807521de75799c95 (sc-s81-s10b, branch feature/s81-s10b-links-gate); GREEN worktree never edited, status clean before and after.
RED files re-hashed start and end (worktree bytes = committed LF blobs): 2df272ff... and aebccaa6... identical.
EK2 blob shas measured: before fe2032237c2a... (git show c6fb6533:path), after ac6b061618319f5947ff4a89b22bc6fd83804eeb30655ebd3287f231d4db7656 (git show HEAD:path) = the GREEN report and PR body.
Scratch worktree <scratchpad>/S81-10b_adv_correctness detached at 0e936223 (no junction; the two RED files rewritten from their LF blobs because autocrlf checked them out CRLF), sha-verified before and after the mutation table, removed with git worktree remove --force.

## Reruns (bounded runner via runone.py, one pytest at a time)
[pyt] tag=adv-corr-red-off start=2026-11-04 07:39:20 end=2026-11-04 07:39:26 elapsed=7s bound=600s status=OK rc=0  -- 75 passed
[pyt] tag=adv-corr-red-on start=2026-11-04 07:39:27 end=2026-11-04 07:39:33 elapsed=6s bound=600s status=OK rc=0  -- 75 passed (flag exported for that one call)
[pyt] tag=adv-corr-s10 start=2026-11-04 07:39:37 end=2026-11-04 07:39:44 elapsed=7s bound=600s status=FAIL rc=1  -- S81-10 RED (EK2) + gate rows: 175 passed, 1 failed = test_r06_production_lexicon_content (environmental CRLF lexicon, red at base)
Mutation runs: 39 pyt calls tagged adv-corr-mut-<id>, each bound 600 s, each status FAIL rc=1 except X04 (OK); per-mutant lines in mut_logs/ and corr_mutants.jsonl.

## Mutation table (by hand on GREEN bytes, byte copies, restored, sha-verified; every kill an AssertionError)
M01 11 (R02) | M02b 5 (R02) | M04 2 (P05) | M06b 1 (R03) | M07 5 (R07, R08) | M09 12 (R01, R08) | M10 1 (R12 llm-fragrances) | M11 1 (R09) | M12 1 (R11) | M13 21 (R06) | M14 21 (R06) | M15 24 | M16 22 | M17 2 (R06 v2) | M18 6 (R02) | M19 1 (R18) | M21 7 (R01, P01) | M22 4 (R02) | M23 4 (R02 get) | M24 2 (R06 v2) | M25 9 (R09, R10) | M26 11 (R06) | M27 2 (R09, R13) | M29 5 (P01) | M30 5 (R17, R19) | M31 1 (R17) | M32 7 (R18, R20) | M33 2 (R20 fragrances) | M34 1 (R09).
Own: X01 classify=None (wrapper bypassed) 2 (R20) | X02 copies without search_query 10 (R08) | X03 rewrite on ANY answer 2 (R20 other) | X05 budget 429 as 400 5 (R02) | X06 resolver_classified ignored in category_gate 13 | X07 v1 call site drops the kwarg 28 | X04 per-product rule 1 on EVERY page (not only `other`) SURVIVED (see m1).
My first M02 / M06 moved only the budget line and crashed on UnboundLocalError (invalid mutants, not counted); M02b / M06b move both lines and are killed. Declared equivalents M-EQ1/2/4 not run.

## Runtime probes of the decision helper (probe_decision.py; real lexicon, classify stubbed and counted, record counted)
blind houses (Dior Sauvage / Chanel Bleu): no chip + A2b fragrances -> proceed, category_used fragrances, 1 A2b over the "<brand> <name>" texts; chip other + A2b fashion -> refused fashion, 1 EVAL; no chip + A2b other -> proceed under other; chip fragrances -> 0 A2b, proceed fragrances.
EDT + laptop (other), both orders, any chip -> refused electronics, 0 A2b, 1 EVAL; EDT + shampoo -> haircare; TV pair (blind or LLM-labelled fragrances) -> refused at pair level.
hair mist labelled haircare + EDT, and hair mist + blind house -> proceed fragrances (form override); brand-only phone + EDT -> proceed fragrances (L4); Chanel bag + EDT -> proceed (house protection).
Every case: the extracted dicts are untouched by the decision (deep-compare); the write-back afterwards is the base one.
Route side read against the bytes: gate_kw read after url_mode_v2_enabled and before SSRF (flag reader then the admin mark), budget as the first statement of _compare_urls_metered (after SSRF / B4 400s, before the consent 503 and the reserve), the refusal through the existing failure arm (one refund, the W4-13 row with the coded message via _failure_log_message, _surface_comparison_failure -> 400 with category / categories_live validated by error_handler); classify_category_llm never raises (A2b failure = other, proceeds uncounted). Flag OFF: {} kwargs, no gate call (P01 golden under five spellings green). resolver_classified=True branch is behaviourally the base branch (only the elif gains `not no_real_chip`, reached only with a real chip at base).
Comm set re-derived independently (a broad grep of tests/ for the four modules, the new symbols, the flag, the code, CLAUDE.md, SmartCompareApp, error_handler, classify_category_llm): 31 extra hits beyond the 108, all either comment-only CLAUDE.md mentions (no read), classify_category_llm users on the text / vision resolver (extraction_service is not edited), a `category_gate` substring in a price_service test name, or the unit RED file; the RED script re-run at HEAD gives 131 raw = 130 + the RED file, as GREEN said. No missing file.

## Findings
Blocking: none. Major: none.
- m1 (doc truth, PR body L12): "a page it labels `fragrances` whose title fires rule 1 is refused at $0" is false per page: probe laptop-labelled-fragrances + EDT proceeds as fragrances (0 A2b) because rule 1 per page runs only on `other` pages (R-S10B-1) and the pair text carries the EDT form word. True only when the PAIR text fires rule 1 (R12). X04 (per-product rule 1 on every page) survives, so no row pins either reading. Reword L12 to "...whose pair titles fire rule 1" (the CLAUDE.md wording "rule 1 did not fire on the titles" is ambiguous but not false), or rule whether the per-page pass should also cover LLM-labelled pages (a design call, not a GREEN defect).
- m2 (stated limit to add): with a REAL non-fragrance chip (electronics) a blind pair WITH house evidence proceeds without a classifier under category_used = the chip (probe blind-elecchip: Dior Sauvage + Chanel Bleu compared as electronics); GREEN's Q1 sentence ("a non-fragrance chip whose blind pair the A2b calls fragrances is compared as fragrances") holds only without evidence. Parity with S81-10's GC-2 arm; post-OTA S81-11 always sends the fragrances chip. Worth one clause in L5.
- m3 (report hygiene): the GREEN report's numstat for CLAUDE.md "+3 -3" and the Q1 answer are consistent with the bytes; nothing else in the report or PR body contradicted the code (order, codes, labels, EXPIREAT + 3600, Retry-After / retry_after_seconds via error_handler, EK2 shas, the four call sites, the module-alias import, no flag literal in either URL file).

## Prove-nothing rows
None found that prove nothing. Weak spots: no RED row distinguishes the per-page pass scope (X04 survives; see m1); no row covers a real non-fragrance chip with house evidence (m2).

## Restore
Scratch app files sha-identical to the before list after the table; scratch worktree removed; GREEN worktree HEAD 0e936223, clean; the junction target @babel/core present; no pytest of mine left running.

# S81-10b LINKS-GATE adversary: quota-and-billing (Opus 5.5, 2026-11-04)

Verdict: SOUND (no blocking, no major; two minors = documentation rulings).
HEAD verified 0e936223921ec0dd4bf70061807521de75799c95 on feature/s81-s10b-links-gate (status clean; the unit worktree never edited).
Scratch worktree S81-10b_adv_quotaandbilling (detached at HEAD): sha-snapshotted (1232 tracked files under app/ tests/ data/ + CLAUDE.md), identical before / after every mutant and at the end, then removed (git worktree remove --force).
Frozen RED files re-hashed at start and end: 2df272ff... and aebccaa6... (match).

## Runs ([pyt] lines)
- [pyt] tag=qb-red-off start=2026-11-04 07:50:15 end=07:50:21 elapsed=5s bound=600s status=OK rc=0 (75 passed; P01 golden under the five OFF spellings with raising recorders included)
- [pyt] tag=qb-red-on start=2026-11-04 07:50:21 end=07:50:26 elapsed=5s bound=600s status=OK rc=0 (flag exported for that one call; 75 passed)
- [pyt] tag=qb-probe start=2026-11-04 07:51:33 end=07:51:37 elapsed=4s bound=600s status=OK rc=0 (11 own probes passed)
- [pyt] tag=qb-ciorder start=2026-11-04 07:55:42 end=07:56:21 elapsed=39s bound=1200s status=FAIL rc=1 (1528 passed, 1 failed = test_r06_production_lexicon_content, the environmental R06; equals GREEN's figure)
- 23 mutant runs qb-mut-* (bound 600, 4-6 s each), all status=FAIL rc=1 (killed); table below; logs S81-10b_adv/qb/mut/.

## Billing probes (scratch tests/test_zz_qb_probe.py on the RED UrlHarness; copy S81-10b_adv/qb/test_zz_qb_probe.py.txt)
- Q01 [post, get] B4 deadline expiring during the gate's A2b (deadline 0.2 s, classify 1 s): 503 TIMEOUT, consume 1, refund 1, EVAL 0, no verdict / lifetime / history (L7 holds).
- Q02 USAGE_LIMIT 429, refusal budget not spent: MGET 1, consume 1, no extraction, no refund, no EVAL.
- Q03 [post, get] exception inside the gate decision: 500 via the base exception arm, consume 1, refund 1, EVAL 0.
- Q04 metering OFF + flag ON refusal: consume 0, refund 0, EVAL 1.
- Q05 ENABLE_ASYNC_REDIS_OFFLOAD ON, GET v2 refusal: MGET 1, EVAL 1, consume 1, refund 1.
- Q06 premium with counters above the budget: exempt, 200, consume 1, lifetime 1, refund 0, EVAL 0, A2b 0.
- Q07 free, budget spent, FRAGRANCE link pair on GET: 429 scope refusal_daily + Retry-After, consume 0, extract 0, refund 0.
- Q08 verdict failure after a proceeding gate: 503, consume 1, refund 1, EVAL 0.
- Q09 no-chip blind pair, A2b other: ONE A2b, 200, consume 1, refund 0.
Code reading: the budget is the first statement of _compare_urls_metered (after the handler's free SSRF / B4 400s, before the S81-06 consent 503 and _reserve_comparison_credit); the refusal leaves compare_from_urls as a coded success-False result, so the existing failure arm refunds once (fire_and_forget; the S81-09 device debit restored through its ContextVar, R14 green), writes the failure row with the refusal copy (R15), no lifetime bump, no history row, then _surface_comparison_failure ships the 400; CATEGORY_NOT_LIVE is not in _URL_V2_REFUSAL_CODES; record_refusal_async runs once (ONE EVAL, EXPIREAT next reset + 3600, keys [acct, dev]); the admin mark returns {} before any read (P05); classify_category_llm never raises (returns other), so the A2b cannot open an unrefunded exit. R-A3 holds on the refusal.

## Mutants (hand-applied on byte copies in the scratch worktree, CRLF-aware anchors, restored + sha-verified each time; RED file + probes, -x)
| id | mutation | killed by (first node) |
|---|---|---|
| M01 | budget read removed | test_r02_budget_spent_never_billed[post-acct] |
| M02 | budget below the reserve | test_r02[post-acct] |
| M03 | account-only subject | test_r02[post-acct] |
| M04 | admin-mark check dropped | test_p05_admin_key_bypass[post] |
| M06 | budget after the consent gate | test_r03_budget_order_reserve_and_consent |
| M13 | record_refusal_async removed | test_r06_post_extract_refusal[post-v1] |
| M14 | record_refusal_async twice | test_r06[post-v1] |
| M16 | failure arm skips the refund on CATEGORY_NOT_LIVE | test_r01 (refund == 1) |
| M21 | gate_route whatever the flag | test_r01_url_routes_read_the_shared_flag_reader |
| M22 | 429 built by refusal_detail | test_r02[post-acct] |
| M23 | GET passes no gate kwargs | test_r02[get-acct] |
| M24 | _compare_with_deadline drops fragrance_gate | test_r06[post-v2] |
| M25 | record before the refused check | test_r09 |
| M28 | refusal returned before the record | test_r06[post-v1] |
| M30 | per-product pass dropped | test_r17_service_signature_and_order |
| M31 | copies not made | test_r17 |
| M32 | no-chip arm takes the evidence shortcut | test_r18_category_gate_resolver_classified |
| M33 | fragrances rewrite dropped | test_r20_no_chip_blind_pair_one_a2b[fragrances-nochip] |
| M34 | selected_category dropped from post_resolve_refusal | test_r09 |
| QB1 | proceed decision carries subject None (never counted) | test_r06[post-v1] |
| QB2 | POST route label "image" | test_r02[post-acct] |
| QB3 | second refund on CATEGORY_NOT_LIVE | test_r01 (refund == 1) |
| QB4 | refusal result marked success True (delivered + billed) | test_r01 |
23 / 23 killed, each by an AssertionError.

## Findings
Blocking: none. Major: none.
- m1 (minor, wording) "$0" on the link path: CLAUDE.md (the S81-10 block's link sentence, "a refusal at $0 whatever the extraction LLM labelled the pages") and the PR body (section 2 (a), L12 "refused at $0") call the link pair-level rule-1 refusal $0. Runtime truth (R12 + probes): it runs AFTER the consume and the paid extraction, is counted (ONE EVAL on both keys) and refunded; only the A2b is skipped. The same block's "Rule 1, $0" for the text path means pre-consume and uncounted, so an operator reading the canary could expect the counters unchanged on a link rule-1 refusal. The words come from GC-1. Suggested: "at no A2b (after the paid extraction; counted and refunded)".
- m2 (minor, stated limit) anonymous header-less link refusals are uncounted (subject None: no MGET, no EVAL; R04 last node) while each still spends the page fetches and any extraction LLM; bounded only by the 10/min limiter. No regression (the base delivers the same anonymous compare in full) and unreachable while ENABLE_COMPARE_AUTH_REQUIRED is ON, but L1-L15 and the CLAUDE.md row do not name it for links ("header-less callers are budgeted per account" covers signed-in callers). Suggested: one clause in L1 or L9.
- Note: L7's offload exception (EVAL already dispatched to a thread) is exercised by no row; acceptable as a stated limit. The GREEN report's [pyt] figures and the EK2 shas (fe203223... before, ac6b0616... after) match the bytes; PR body 15,357 B (< 25,600); no error_handler / structured_comparison_service / migration / lock / client file in the diff.

## Prove-nothing rows
None under this lens: every billing row (R02-R06, R14, R15, P05, P06) died to at least one billing mutant.

## Not run by this lens
Comm chunks, pin sets a-d, jest fences, hook test files (no .githooks change): the other adversary's duties.

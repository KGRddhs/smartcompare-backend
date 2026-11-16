# INC-C1a SIZE-LABEL: ADVERSARY report (LC-1, correctness lens + second lens), 2026-11-16 21:36-21:47 AST

HEAD 2abcbf44aa5d93851c97afe1ace2996649f33934 on fix/inc-c1a-size-label, parent b0ad260363e0cf0074e4ee596b140d073466e92a (git log). On no remote branch (git branch -r --contains empty). 14 files, +705 -31. Worktree git status --short empty before and after (probe folder __tests__/c1a_adv created, run, deleted; copy kept in adv/probe_copy/).

## VERDICT: SOUND (0 BLOCKING, 0 MAJOR, 4 MINOR)

## Checks (each with evidence)
1. Contract = proto.diff: the committed src diff equals red/proto.diff line for line (107 +/- lines each, identical). CC-1 U+00B7 in EN and AR withSize; CC-2/CR-4 the size label wraps the whole of today's formatPrice output (ResultsContent.tsx:220-229 at HEAD); CC-3 per-ml line carries no converted marker; CC-4 grouping false ("1000 ml" observed); CC-5 CLIENT_CAPABILITIES = ['price_size'] (requestContext.ts:38), price_asof not declared; CC-6 per-ml gated on prov.kind !== 'unknown' (:431), caption needs both cards shown and not unknown (:241-250), the honest line replaces the price line (:410-417); CC-7 formatPrice 4th param 0..6 else the default (formatNumber.ts:96-113); CR-5 priceLine is local to ResultsContent; the other formatPrice callers (HomeEditorialSections.tsx:175,220) use 3 args.
2. Wire shape vs in/INC-P2_UNIT_SPEC.md :217, :223, :255-257 matches; ResultsScreen passes overview.products raw (ResultsScreen.tsx:430-432) and result.metadata; SSE prices only drive TTFB (api.ts:959, HomeScreen.tsx:471).
3. Today's body byte-identical, independent of P1: the probe renders the BASE ResultsContent (b0ad2603 bytes, imports remapped) and the HEAD one with the same props through a REAL i18next instance (escapeValue false as src/i18n/index.ts:38-40) and compares JSON.stringify(toJSON()) of the WHOLE page: 6 fixtures x EN/AR = 12 rows identical, incl. an S81-11 stored result (resultOrigin stored, price as_of 40 days -> listed line, field_status fresh, section_status) in AR, an S81-11 live honest-unknown + staleNoDate body, converted + pending, KWD + SAR, and pair_price_sizes present without size keys.
4. New keys on the S81-11 stored AR body: the texts added vs base are exactly the two withSize lines (58.110 / 9.500, AR BHD symbol, U+00B7, 100 / 30, AR ml), the two perMl lines (0.5811 / 0.3167) and the AR differentSizes caption once; removed exactly the two bare price lines; both listed-on provenance lines byte-identical; no Arabic-Indic digit in any added line (APP_DIGIT_SYSTEM latn); one middle dot per line.
5. Real i18next, EN converted: "58.110 BHD (converted from USD) U+00B7 100 ml" and "0.5811 BHD per ml"; converted label count equals base (CC-2).
6. formatPrice: the 3-arg call and every invalid 4th arg (undefined, null, -1, 7, 2.5, NaN, Infinity, '3', {}) equal today's body re-typed from b0ad2603 for BHD/KWD/SAR/USD/XYZ x 6 amounts; 0..6 honoured.
7. i18n: base 1011 keys, head 1014, EN/AR sets equal; 0 changed values; exactly the three keys added; existing key order unchanged; AR strings byte-equal to the PAGE_DESIGN_V2 table rows; EN separator U+00B7 per CC-1. Independent sha256 of sorted names: base 2d351a2c...f543, head cd5995fb...e6, head minus the 3 keys = 2d351a2c...f543 (CC-8 re-record correct).
8. Moved pins: every edit extends an EXACT toEqual object with the capability header, or flips B9 to assert ['price_size'] and the header value; leaf counts 1011 -> 1014 (+3 exact); legal_v3 two literals + the comment exactly per CC-8; no objectContaining introduced, no assertion removed (all 7 diffs read in full).
9. Header on every path: buildContextHeaders adds it when the list is non-empty (requestContext.ts:152-154); REST and /usage/status via the axios interceptor (api.ts:72-80); camera attempt 1 (api.ts:312-322); the camera 401 retry spreads the same contextHeaders (api.ts:352-357); SSE (api.ts:875-891); pinned by the moved rows. No log line added; no console or Sentry statement prints headers (grep). Backend readers at base: only kb_serve.client_price_asof (kb_serve.py:128-138), token price_asof; price_size changes nothing on b0ad2603.
10. Bundle rule: committed paths = 6 SmartCompareApp/src files, 7 SmartCompareApp/__tests__ files, tests/test_s81_12_legal_v3.py; no package, lock or app.json (app.json version 1.0.0).
11. No client cheaper claim: in the different-sizes render the added texts are only the size / per-ml / caption lines, none equal to any catalog value whose key matches cheap|saving|save|less|lower|valueMatch; getPriceDiff (ResultsScreen.tsx:717-735) is computed and never rendered (unchanged dead code); DimensionBars cheaperOfTwo is server value-match data.
12. RED file sha 7a9f3fff...05d (frozen), 24,664 bytes, 0 bytes > 127.

## Runs
- [jest] tag=s96c-adv-probe1 start=2026-11-16 21:40:45 end=2026-11-16 21:40:47 rc=1 (16/17: my own probe text filter caught the price line; fixed)
- [jest] tag=s96c-adv-probe2 start=2026-11-16 21:41:02 end=2026-11-16 21:41:04 rc=0: 17/17 (probe then deleted)
- [jest] tag=s96c-adv-full start=2026-11-16 21:42:12 end=2026-11-16 21:42:25 rc=1 (jest 29.7.0): 414 suites (410 passed, 1 failed, 3 skipped), 4081 tests: 4051 passed, 4 failed, 13 skipped, 13 todo; snapshots 41/41; only FAIL nativeBundle.w37 d5, k2, k4, k5 (the 4 accepted nodes)
- [jest] tag=s96c-adv-pair-ab 21:42:41-21:42:43 rc=0 sizeLabel > requestHeaders 31/31; [jest] tag=s96c-adv-pair-ba 21:42:43-21:42:45 rc=0 requestHeaders > sizeLabel 31/31 (--runInBand, own order-preserving sequencer adv/advSeq.js)
- [jest] tag=s96c-adv-six-ab 21:42:45-21:42:47 rc=0 129/129; [jest] tag=s96c-adv-six-ba 21:42:47-21:42:50 rc=0 129/129 (RED + the six moved-pin suites, both orders, runInBand)
- [pyt] tag=s96c-adv-fences9 start=2026-11-16 21:43:20 end=2026-11-16 21:43:34 elapsed=15s bound=600s status=OK rc=0: 303 passed; [hermeticity] sentinel checked 303 test(s); [netguard] blocked 12 attempt(s) from 6 node(s)
- [pyt] tag=s96c-adv-fences12b start=2026-11-16 21:45:26 end=2026-11-16 21:45:52 elapsed=25s bound=600s status=OK rc=0: 710 passed, 4 deselected; [hermeticity] sentinel checked 710 test(s); [netguard] blocked 25 attempt(s) from 21 node(s). The 12 extra tests/*.py SmartCompareApp readers my grep found beyond GREEN's nine: arabic_verdict_output_w414, ci_gates, feedback_allowlist_superset, legal_disclosure_s77, legal_docs_u8_polish, legal_s78, migration_037_security_definer_grants, review_paraphrase, s81_sf1_gate_rows, s81_sf1_surfaces_be, text_error_envelope_no_raw_exception, timeout_partial_integration (an identical first run s96c-adv-fences12 at 21:43:44 also gave 710 passed; its [pyt] line was discarded)
- [tsc] tag=s96c-adv-tsc 21:44:17-21:44:23 rc=0, 0 lines (tsc 5.9.3)
- [eslint] tag=s96c-adv-eslint 21:44:23-21:44:29 rc=0 (eslint 9.39.4) on the 13 changed client files: 0 errors, 15 warnings; on src only pre-existing lines (ResultsContent 49, 310 = base 265; requestContext 117/120; types 25-28, 453); CI lints src only (.github/workflows/ci.yml:297-298)

## Findings
- MIN-1 (MINOR, stated limit) ResultsContent.tsx:212-217 isShownPrice accepts amount 0 or a negative amount; the wire puts size_ml only on amount > 0 (INC-P2 spec :217). Probe: amount 0 + size_ml 100 + per_ml 0.0004 renders "0.000 BHD U+00B7 100 ml" and "0.0004 BHD per ml". Unreachable from the INC-P2 server; state it, or add price.amount > 0.
- MIN-2 (MINOR, cosmetic) SmartCompareApp/__tests__/s11/copy.s11.test.tsx:10 docblock still reads "1,013 - 17 + 15 = 1,011" while the row now asserts 1,014 (+3 INC-C1a); the title was updated, the header comment was not.
- MIN-3 (MINOR, process) origin/main is now fd983471 (+ #411 INC-I2e, backend only: app/services/image_relevance.py, tests/test_inc_i2e_guard_short_line.py, CLAUDE.md, .github/black-clean-paths.txt); no file overlap; the PR needs the merge/rebase and the full jest after it per house rule.
- MIN-4 (MINOR) the RED file carries two import/first eslint warnings (sizeLabel.c1a.test.tsx:140-141); outside CI's src lint scope.

## NOT MEASURED
- Device rendering (RTL bidi visual order of the AR line, wrap of the longer converted line, the caption layout outside the cards, L-4); anything on a phone; CI; the live server.

## Files
- probe copy adv/probe_copy/{adv.c1a_adv.test.tsx, RCBase.tsx}; logs adv/*.log; sequencer adv/advSeq.js; i18n check adv/chk_i18n.py + chk_i18n.out.
- git status --short of W at the end: empty.

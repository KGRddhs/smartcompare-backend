# GATE INC-C1a SIZE-LABEL (S96 orchestrator, 2026-11-16 about 21:25 AST)

RED wf_05274256-05f (one Opus 5.5 agent, model verified, 319,286 tokens, 18 min) is ACCEPTED.
- RED file SmartCompareApp/__tests__/c1a/sizeLabel.c1a.test.tsx, sha256 7a9f3fffcb66005736a929a55d8498f41526b3b562816856b331c94e36ada05d, 24,664 bytes, pure ASCII: FROZEN.
- At base, C1-C7 fail on assertions and P1-P2 pass; at the prototype 9 of 9. Mutants MC1-MC8 are killed and the restore is proven. tsc shows 0 errors at base and at the prototype; eslint shows 0 errors and no new warning.
- Full jest: at base 11 failing tests = the 7 RED rows + the 4 accepted nativeBundle.w37 nodes. At the prototype 22 failing tests = the 4 accepted nodes + 18 moved pins (listed below).
- The orchestrator reviewed proto.diff (ResultsContent.tsx, requestContext.ts, types.ts, formatNumber.ts, en.json, ar.json). It is the contract, with these rulings.

## Rulings on the open questions
- CC-1 (Q1) The EN separator is U+00B7, the middle dot: "58.110 BHD · 100 ml". The orchestrator accepted that form on 2026-11-16, and the design's hyphen-minus in row 368 is an ASCII stand-in in a markdown table. AR also uses U+00B7.
- CC-2 (Q2) Today's card prints the converted label twice: once in the price line, once in the caption. That is the T7-08 defect, which belongs to INC-C1, so it is NOT fixed here. This unit keeps exactly today's converted text: the size label wraps today's whole formatPrice output, and the caption stays. C4 as written.
- CC-3 (Q3) A converted price's per-ml line carries no marker of its own. Accepted as stated limit L-1: the price line and the caption above it already carry the label.
- CC-4 (Q4) 4-digit sizes have no grouping: "1000 ml". Accepted.
- CC-5 (Q5) Every request that builds context headers now carries `X-Client-Capabilities: price_size`: the REST and stream compare, the link compare, /usage/status, the camera upload and its 401 retry. Server readers measured by the orchestrator at b0ad2603: `kb_serve.client_price_asof` only, which looks for the token price_asof. The data lane's INC-P2 will read price_size by the orchestrator's ruling. So no route changes behaviour on b0ad2603. State it in the PR body.
- CC-6 (Q6) A card on the S81-11 honest line (provenance unknown) never shows a size or a per-ml line. Accepted (D4).
- CC-7 (D2, D5) Accepted: the string table is PAGE_DESIGN_V2 section 6a, and the per-ml digits are the currency's minor unit + 1 for every currency (CR-3), through the optional 4th positional parameter `fractionDigits` of formatNumber.formatPrice (0..6, otherwise today's default; every 3-argument caller byte-identical).

## GREEN (one agent) does
- G-1 Implement exactly proto.diff in the six src files.
- G-2 Update the 18 moved pins as E-rows, each the smallest edit that states the new truth: (a) the exact header objects gain `'x-client-capabilities': 'price_size'` (or the file's own letter case); (b) B9 asserts `['price_size']` and the header present; (c) the two catalog leaf counts in copy.s11 and s11e/arCopy rise by exactly 3 (1011 -> 1014). Never weaken an assertion: no `expect.objectContaining` where the test had an exact object. List every edit (file:line, old -> new) in the report.
- G-3 The backend fences that read the edited client files, through the pytest runner (pyt.py, tags s96c-green-*, waitfree first): tests/test_comparison_id_echo.py, test_dimension_label_catalog_parity_w414.py, test_legal_docs_u8.py, test_legal_docs_u8_d3c.py, test_s81_12_gate_rows.py, test_s81_12_legal_v3.py, plus any other tests/ file that reads en.json, ar.json, requestContext.ts, types.ts, formatNumber.ts or ResultsContent.tsx (grep). Run them at the change; any failure is re-run at base in a detached scratch worktree under the notes folder before it counts.
- G-4 Gates: the RED file 9 of 9; the FULL jest suite once (LC-7) with only the 4 accepted nativeBundle.w37 nodes failing; tsc --noEmit; eslint as CI runs it; the --runInBand pair in both orders for the RED file with requestHeaders.s81_08 (the shared requestContext module); the pre-commit hook.
- G-5 COMMIT on fix/inc-c1a-size-label: "feat(results): INC-C1a SIZE-LABEL bottle size and per-ml line beside a shown price; declare price_size", a body of 3-6 lines, the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Stage by name: the six src files, the RED file and the moved-pin test files only. Never --no-verify, never push. No package, lock or app.json change (the bundle rule).

## Stated limits (for the PR body)
- L-1 a converted price's per-ml line carries no converted marker (CC-3).
- L-2 the converted label still appears twice on a card (today's T7-08; INC-C1 fixes it).
- L-3 a size above 9999 ml or a non-integer size is not drawn.
- L-4 not pinned: the per-ml line's order against the provenance line, the different-sizes caption's position.
- L-5 nothing changes on the phone until the server sends the keys: INC-P2 with ENABLE_PRICE_NOT_LOST on. The capability header goes out from the first launch of the update.

## The adversary (one, LC-1)
The correctness lens with the second lens folded in:
- the contract of spec section 3 and CC-1..CC-7 against the committed diff;
- today's body renders byte-identical text (P1), checked independently with one more fixture of its own (an S81-11 stored result, an AR render);
- every moved-pin edit states the new truth and weakens nothing;
- the header on each request path (camera, SSE, REST, the 401 retry) and that no header value is logged;
- the bundle rule (no package, lock or app.json change; SmartCompareApp/src plus tests only);
- RTL: the Arabic label with the middle dot and the digits policy in an AR render;
- that no client cheaper claim appears when the sizes differ.
Verdict SOUND / NOT_READY, with findings BLOCKING / MAJOR / MINOR.

## ADDENDUM 1 (2026-11-16 about 21:35 AST): the GREEN block on tests/test_s81_12_legal_v3.py
GREEN (wf_4e8febf5-21a, 200,601 tokens) stopped correctly before G-5. Every other gate is green: the RED file 9 of 9; the 18 moved pins edited as listed; the full jest suite fails only the 4 accepted nodes; both runInBand pair orders are green; tsc and eslint are clean. One backend fence failed: tests/test_s81_12_legal_v3.py::test_p3_i18n_key_sets_equal_and_unchanged. It pins BASE_I18N_KEY_COUNT 1011 and the key-name-set sha, and says "Re-record ONLY with a ruling". At base the file passes 38 of 38. The agent proved that the 1014 keys minus the three INC-C1a keys hash to exactly the recorded base sha.
- CC-8 RULING: re-record it as an E-row. BASE_I18N_KEY_COUNT 1011 -> 1014; BASE_I18N_NAMESET_SHA256 -> "cd5995fb42987f33165330732c5fdf1b1c" "88dfc639676d0742fa431077bfe8e6" (two literals, as today). Add one comment line above it: "# INC-C1a (2026-11-16) re-recorded: + results.price.withSize, results.price.perMl, results.price.differentSizes (CC-8)". Reason: the pin guards the LEGAL unit against unplanned catalog changes; the three keys are deliberate, they are not legal text, and the remainder hashes to the recorded base. The file joins the commit's staging list. The bundle rule is unaffected: a tests/*.py file is not in the update bundle.
- GREEN-2 then re-runs that file and the nine backend fence files through pyt.py, the RED file and the moved-pin suites, and commits per G-5 (the new path added to the list). The full jest suite is NOT re-run (LC-7 ran it on these exact client bytes); the hook runs.

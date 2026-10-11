# Orchestrator rulings for the U8 FIX round 4 (session 76, 2026-10-11 ~01:10; orchestrator on Opus 5.5 after the Fable limit)

Inputs: CI on 7f41e800 (backend 1 failed, frontend 2 suites failed), the truth/Apple-compliance reviewer
(wf_03a81c3a-f80, READY, 0 blocking, majors M1-M4), the Arabic reviewer (wf_10bdd5fa-949, NEEDS_FIXES: 1 blocking
AR-T1, 6 minors, corrections in notes/u8ar/corrections.json), and FINAL ADVERSARY 3 (wf_03a81c3a-f80 agent 1;
its findings are appended below as UF16 once it reports). UG1-UG12 and UF1-UF13 stay in force.

- UF14 (M1, terms s8 data clause; the owner's instruction was "comparison data and preference data, never
  personal", "if this is good and legal"). The sale object narrows to aggregated or anonymised statistics, matching
  privacy s2, and ownership attaches to the de-identified compilation (removes the tension with the user's licence
  over "your queries"). Replace the whole TERMS_DERIVED sentence (terms_of_service.md s8, EN) with EXACTLY:
  "We own the de-identified comparison data that MYEZ compiles (the products compared, the verdicts and scores, the prices gathered and de-identified search queries) and the preference and usage statistics we derive from it in aggregated or anonymised form. We may use this data to operate and improve MYEZ, and we may share, license or sell aggregated or anonymised statistics derived from it (for example price trends or category popularity) to third parties; none of it identifies you, and your personal data is never sold."
  AR twin (terms_of_service_ar.md s8), replacing the AR sentence that starts with the AR for "We own MYEZ's
  comparison data" and ends with the AR for "your personal data is never sold.", EXACTLY the text in
  notes/u8final/uf14_ar.txt (UTF-8, one line). Mirror into tests/fixtures/legal_prefill_u8/ if the sentence is
  unconditional there; update TERMS_DERIVED_EN in tests/test_legal_docs_u8_d3c.py and ug12_ar.terms_derived in
  tests/fixtures/legal_d3c_u8.json; the (k) scan must still pass on the documents and its positive controls must
  still fire; add the retired phrase "license or sell that comparison and preference data" to TERMS_RETIRED_EN (it
  may not come back) and its AR twin to the AR retired list if one exists. Re-render landing/terms.html and
  landing/ar/terms.html.
- UF15 (Arabic review, accepted in full): apply AR-T1 (blocking) and AR-P1..AR-P6 from notes/u8ar/corrections.json
  exactly as written there, with every 'extra_edits' entry (prefill snapshot mirror, the d3c fixture pin
  ug12_ar.terms_history, the variants JSON path clauses.DELETION_SECTION.ar.privacy.043 for AR-P1). AR-T1 and the
  UF14 AR sentence sit in the same line 48: apply AR-T1 first, then UF14. Re-render the AR landing pages. Record in
  notes: "Arabic reviewed by an Opus model review at the owner's request (2026-10-11), accepted by the owner in place
  of the native review (session-73 gate 6, D11)".
- UF17 (CI collisions, orchestrator scripts, run FIRST, each exactly once, before any other edit):
  handoff/u8_client_collision_fix.py (api.ts comment without the retired host; landing.brand.s69 ADDRESS_COUNTS
  re-measured: privacy 10, terms 6, support 10, AR same) and handoff/u8_polish_eol_fix.py <worktree> (polish b3
  asserts the page keeps its OWN line endings; verified on an LF checkout). If UF14/UF15 change the number of
  qaren.app|getmyez.com matches on any landing page (they should not), re-measure ADDRESS_COUNTS.
- UF18 (stale comment, minor): tests/fixtures/legal_fill_in_u8.json:5 still says the landing pages publish the
  retired support address outside the legal regions; reword to the getmyez.com fact without the retired host
  (ASCII, JSON stays valid, line endings preserved).
- UF19 (M2, App Store Connect, not code): the App Privacy per-type set-up ticks Other Purposes on rows 3, 4, 5, 8
  and 12 (OA2 + M2). Over-disclosure costs nothing at review. Recorded for the ASC step.
- UF20 (M3, M4, owner/ASC, not code): Email Routing is the owner's publish gate (the classifier blocks the
  orchestrator's DNS clicks). getmyez.com apex and www stay DNS-only (grey cloud) after the domain move so privacy
  s7's website sentence (hosting provider + Google Fonts) stays complete; if they are ever proxied, add Cloudflare to
  that sentence first. ASC URLs become https://getmyez.com/privacy.html and https://getmyez.com/support once the
  landing serves them.

Gates for FIX-4 (all on the real tree unless stated): the five U8 files + test_domain_s76 + test_landing_fallback_pages_s69
+ test_migration_043 green; the LF proof (a detached scratch checkout made with -c core.autocrlf=false, the PR files
synced from the real tree with CR stripped to LF, then the same pytest set green there); render --check rc 0;
fill_in --dry-run rc 0 and a second real run byte-identical; the FULL jest suite under the lock
(node node_modules/jest/bin/jest.js --ci, bound 1500 s) green; tsc --noEmit and eslint on the touched client files;
ruff/py_compile on touched .py; ASCII checks on the test .py files; git diff --stat with no whole-file diff.

## Addendum: FINAL ADVERSARY 3 (NOT_READY: B1, B2 = the two client CI collisions; 0 major; minors m1-m7)

- UF16 (B1, B2): resolved by UF17's client script (the api.ts comment keeps its 3-line count: legalScreenLang.u8 pins
  LANDING_BASE_URL near API_BASE_URL; ADDRESS_COUNTS privacy 10, terms 6, support 10, AR same; also refresh the stale
  comment lines landing.brand.s69.test.ts:59-66 and legalScreenLang.u8.test.tsx:45 so they state the getmyez.com fact
  without the retired host).
- UF21 (m2, scan scope): extend the (k) personal-data claim scan, EN + AR twins, with the verbs give / provide /
  disclose / buy (a sale seen from the buyer's side), the recipients "third parties" when the purpose is marketing or
  advertising, and the object phrase "information that identifies you" (and "data that identifies you"); Y1-Y4 from
  notes/u8adv3/mutants.py become positive controls (EN + AR twins) and must be caught; the shipped documents (after
  UF14/UF15) must still pass.
- UF22 (m3): test_d3c_n scans the WHOLE privacy document (EN + AR), not only s5, for the unqualified core provider
  claim; X3 becomes a positive control.
- UF18 extended (m4): tests/fixtures/legal_fill_in_u8.json _values_comment says the values ARE recorded (2026-10-11,
  production read + 043 POSTCHECK); its _placeholders_comment and _placeholder_answers_comment state the getmyez.com
  fact without the retired host.
- Recorded, no change: m1 (six of the seven flags select no text; the documents disclose those processors and pushes
  unconditionally, the safe side; the flag values are informational), m5 (the fork refusal names the remedy, not the
  key; low value), m6 (LANDING_BASE_URL moves to https://getmyez.com in a later unit once getmyez.com serves the
  landing; it needs an OTA), m7 (PR body).

## Addendum: FINAL ADVERSARY 4 (READY, 0 blocking, 0 major) minors -> FIX-5 (committed FIX-4 = e7d410d6)

- UF23 (m2): the UF14 Arabic second sentence repeats the noun so the licence/sale pronoun can only reach the
  statistics. Replace the whole UF14 AR sentence (the exact bytes of notes/u8final/uf14_ar.txt, now in
  terms_of_service_ar.md:48, its pre-fill snapshot and fixture ug12_ar.terms_derived) with the exact bytes of
  notes/u8final/uf23_ar.txt, in all three places; re-render landing/ar/terms.html.
- UF24 (m3): privacy s9 retention sentence. EN (privacy_policy.md:116 + snapshot + PRIVACY_S9_EN in the d3c test):
  "De-identified comparison data and statistics that cannot identify you may be kept after deletion."
  AR (privacy_policy_ar.md:116 + snapshot + fixture ug12_ar.privacy_s9): the exact bytes of notes/u8final/uf24_ar.txt.
  Re-render landing/privacy.html and landing/ar/privacy.html. The old EN and AR sentences become retired fragments
  only if a retired list exists for privacy s9; otherwise none.
- UF25 (m1): pin AR-P1: a d3c test asserts the doubled-period phrase (the 'old' string of AR-P1 in
  notes/u8ar/corrections.json, stored in the d3c fixture, the test file stays ASCII) is absent from
  privacy_policy_ar.md and from landing/ar/privacy.html, and the AR-P1 'new' string is present in privacy_policy_ar.md.
- UF26 (m4): refresh landing.brand.s69.test.ts:26-29 (the header comment on ADDRESS_COUNTS: say the four legal
  pages and the two support pages were re-counted on the filled pages, 2026-10-11) and :70 (open.html: 3 = getmyez.com
  mentions); no count changes; no retired host added.
- Recorded, no change: m5 (Z1-Z4 paraphrase gaps of a keyword guard; documents unaffected).

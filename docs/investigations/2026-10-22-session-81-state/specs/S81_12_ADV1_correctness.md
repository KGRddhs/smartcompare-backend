# S81-12 LEGAL-V3 -- correctness adversary report (Opus 5.5, 2026-10-29 05:33-06:40 AST)

Unit S81-12 LEGAL-V3 (docs-legal, NO runtime flag, HELD PR). Lens: correctness. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s12, branch feature/s81-legal-v3, HEAD 3c4a198dca34745ad105aef404f381f13a393f58 VERIFIED at start and end (base a8f01379). Read-only there: no file edited; `git status --short` = `A  tests/test_s81_12_legal_v3.py` at start and end. Probes and mutants ran in my own DETACHED scratch worktree <scratchpad>/S81-12_adv_correctness at 3c4a198d (no node_modules; the frozen RED .py byte-copied in and sha-verified, because it is NOT in the commit), removed with `git worktree remove --force` and verified gone (worktree list count 0, directory absent). No .qa-mutation.lock left anywhere. This report was written through the shell (python make_report.py). Notes, logs and the harness: <scratchpad>/S81-12_adv/corr/ (notes.md, mutants.py, mutants_results.jsonl, mut_*.log, unit.log, ci.log, jest_rows.log, gl_report.json, diff_*.txt, bytecopies/ + bytecopies_SHA256SUMS.json).

RED files re-hashed at start and end (unchanged): tests/test_s81_12_legal_v3.py 94ef61a526ccfc10f15c51b61b82fa11755469e8e332bb030c705111e4dcd6b5 (= the staged blob 9e651263); SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts 2af065a2bc230881760d54766312d6a87d24ad5161f6284d477f210b322b6a75 (= the committed blob 9b3bbf7b).

Verdict: NOT_READY (0 blocking, 3 major, 9 minor).

## Runs (every pytest through pyt.py, one at a time; box healthy: ls 0.3 s, node -e 0 0.7 s)
- unit file on the committed bytes: [pyt] tag=s12adv-corr-unit start=2026-10-29 05:44:57 end=2026-10-29 05:45:29 elapsed=32s bound=600s status=FAIL rc=1 -- 1 failed (H1, red by design) / 37 passed; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
- CI-order set (GREEN's 18 files: the 15-file legal set + the unit file + test_s81_s06_anthropic_router + test_s81_s04_spend_breaker): [pyt] tag=s12adv-corr-ci start=2026-10-29 05:45:49 end=2026-10-29 05:50:12 elapsed=263s bound=1200s status=FAIL rc=1 -- 1 failed (H1) / 1157 passed; [hermeticity] sentinel checked 1158 test(s); [netguard] blocked 24 attempt(s) from 2 node(s) (test_s81_s04_spend_breaker r42 / p08, neutralized.supabase.invalid:443). Equals GREEN's ci line.
- jest rows BY PATH in the REAL worktree through its junction (read-only; LinkType Junction -> C:\Users\SynAckITPC\Documents\AI\smartcompare\SmartCompareApp\node_modules; node_modules/@babel/core and .bin/jest present; node v24.11.1, jest 29.7.0, @babel/core 7.29.0): the client RED file + aiConsentVersion.s69 + aiConsentV2.s75 + aiProcessingConsent.s69 + step05Trust.s69 + landing.brand.s69: [jest] tag=s12adv-corr-jest-rows start=06:18:51 end=06:19:36 rc=1 -- Tests 2 failed / 62 passed (Suites 1 failed / 5 passed); the 2 failures are the C2 rows (minor m1). Equals GREEN's subset line. The full jest suite was not re-run (GREEN's full run stands; not this lens's duty).
- gitleaks 8.30.1 (read-only `detect --no-git` on a copy of the RED .py with a copy of HEAD:.gitleaks.toml, --ignore-gitleaks-allow --redact): rc=1, 1 finding: generic-api-key at line 211 (BASE_I18N_KEYS_SHA256). GREEN's D1 / Q2 cause CONFIRMED.

## Mutants
Method: byte copies of every touched file, exact edits matching once, sha-verified restore after each. Text mutants go THROUGH the machinery (edit the pre-fill snapshot or the variants, restore the snapshot over app/legal, run scripts/fill_in_legal.py, then the rows). Control M0 = restore + fill with no edit -> only H1 red, so the refill itself is neutral.

Spec / RED mutants re-applied on the GREEN bytes (unit file, bound 600; every kill an AssertionError, checked in each log):
- M1 privacy s2 'We took part' -> 'We take part': KILLED by R2[en].
- M2 s4 drop the 29-day batch clause: KILLED by R1[en].
- M3 processors.json anthropic public_name true -> false: KILLED by R9.
- M4 AI_CONSENT_VERSION 3 -> 2: KILLED by R14.
- M6 Terms s7 drop the Sponsored sentences: KILLED by R8[en].
- M9 Step05Trust default head back to 'What reaches OpenAI': KILLED by R15.
- M10 privacy s12 drop the AI-disclosure sentence: KILLED by R7[en].
- M11 s5 carve-out drop 'before <AI_SWITCH_DATE>': KILLED by R4[en].
- M12 en.json consent body: the v2 training sentence back in place of the transition sentence: KILLED by R14.
- M13 fill-in d3 'A' -> 'C': KILLED by R10.
- M16 s3.2 'sent to our AI providers' -> 'sent to OpenAI': KILLED by R16[en].
- M20 the two RETENTION_KEYS pairs removed from fill_in_legal.py: KILLED by R19.
- M23 s4 heading back to '(OpenAI)': KILLED by R1[en] + R16[en].
- M24 Terms s8 dual sentence -> 'Our AI provider is OpenAI; ... send it': KILLED by R1b[en] + R8[en] + R16[en].
14 / 14 KILLED ([pyt] lines in mutants_results.jsonl and mut_M*.log; 13-25 s each).

Adversary mutants (the six core legal files: the unit file + test_legal_docs_u8, _d3c, _polish, test_legal_disclosure_s77, test_legal_s78; bound 600):
- X1 EN privacy s4 'Since then, OpenAI does not use the data we send it to train its models' -> 'Since then, OpenAI may use ...': SURVIVED the six core files ([pyt] tag=s12adv-corr-X1 elapsed=58s: 236 passed + H1) AND the other twelve CI-order files ([pyt] tag=s12adv-corr-X1F elapsed=117s status=OK rc=0: 921 passed). MAJOR M-2.
- X2 AR privacy s2: drop 'including photos' from the AR dual-provider sentence: SURVIVED (m4).
- X3 EN s6 'Payment never changes how products are compared, scored or ranked' -> 'Payment may change how products are ranked': KILLED by R6[en].
- X4 EN s4 drop 'Data shared with OpenAI under the programme before that date remains governed by OpenAI's terms.': SURVIVED (m5).
- X5 EN s2 'our part in it has ended' -> 'continues': KILLED by d3c j, s77 d1[en], d5[en], d10.
- X6 EN Terms s8 'our part in it has ended' -> 'continues': KILLED by d3c i, s77 d3[en], d5[en], d10.
- X8 AR s4 Anthropic retention 30 -> 90 days: SURVIVED (R1[ar] accepts any '30' in s4; OpenAI's 30 remains) (m4).
- X9 AR s4 Anthropic 'does not use ... to train its models' -> 'may use ...': SURVIVED (m4).
- X10 AR s4 OpenAI 'does not use (since the switch) ... to train' -> 'may use': SURVIVED (m4; the AR twin of M-2).
- X11 landing/privacy.html region edited without the source: KILLED by P1.
- X12 EN s4 Anthropic no-training qualified '... train its models unless we agree otherwise': SURVIVED (R1 accepts any Anthropic + not + train sentence) (m6).
- X13 variants KB_FEEDBACK_CLAUSE if_null '' -> a bullet text: KILLED by R18 (the fill accepted it: the nonempty KB text has no {value}, so _check_value never runs; R18 is its only guard).
- X14 variants COMPARE_RUNS_CLAUSE if_null '' -> a bullet text: REFUSED by the machinery (fill_in_legal.py exit 3 'COMPARE_RUNS_CLAUSE: value contains markup, a line break or a placeholder', nothing written).
Equivalent survivors: none claimed; X12 is a weakening mutant (ruling).

## Findings

### MAJOR
- M-1 (privacy s14, EN + AR, every state): the new text says the App keeps "your sign-in tokens and a random install identifier stored securely in your iPhone's Keychain"; the base text said "two random device identifiers", which is what the code keeps at merge, during the transition and after OpenAI's retirement: (1) SmartCompareApp/App.tsx:207 `await getStableId()` at every start -> src/config/featureBucket.ts:27 DEVICE_ID_KEY 'qaren_device_id_v1', :74-77 SecureStore.setItemAsync(Crypto.randomUUID()) (the canary bucket id; identical in build 3: `git show 683f56c0:SmartCompareApp/App.tsx` :207, featureBucket.ts :27); (2) src/services/deviceFingerprint.ts:12 NONCE_KEY 'device_fp_nonce', :22-25 a second random UUID in SecureStore (the fingerprint nonce). RULINGS_S81_08 R-S08-7 makes the stable install id REUSE device_fp_nonce and removes neither key; no S81-08 / S81-12 spec mentions qaren_device_id_v1 (grep). So the GREEN text under-states the on-device identifiers in all three states and regresses an accurate base sentence. Cause: the R-S12-10 (amended) wording, enforced by the frozen R17 (S14_EN_FORBIDDEN forbids the literal 'two random device identifiers'; AR forbids the AR twin). R17 does NOT forbid naming a second identifier, so a fix fits the frozen RED, e.g. EN "... your sign-in tokens, a random install identifier and a second random identifier the App uses to choose which new features you see, stored securely in your iPhone's Keychain, ..." + the AR twin [NATIVE READ], through restore + fill + render --check. Needs a ruling (it amends a ruling's wording).
- M-2 (the unit's central fact is unpinned, EN; AR twin in m4): mutant X1 flips privacy s4 "Since then, OpenAI does not use the data we send it to train its models" to "OpenAI may use ..." and the whole 18-file CI-order set stays green (only H1 red). Why: R16's EN sentence classes admit any sentence with 'abuse-monitoring' / 'does not use' / 'no longer' / 'data-sharing programme'; T8 'A' (D3_FORBIDDEN_EN['A']) forbids only opt-out, 'Help improve AI quality' and the programme name; R2 forbids only the present-tense 'we take part'; the retired d3_training fork took the old 'A' no-training sentence with it. This sentence is what makes 'the programme ended' true and what P7 / R-S12-17 lean on. Fix (cheap, no fence moves): a pin row, e.g. in tests/test_legal_docs_u8.py beside test_t8_history_allow_list_is_exact, requiring under d3 'A' exactly one s4 sentence 'OpenAI does not use the data we send it to train its models' (EN) and its AR twin, with a positive control and this mutant; listed as an E-row in the PR body.
- M-3 (the commit is incomplete; GREEN D1 / Q2, CONFIRMED): the frozen RED .py is staged, not committed (gitleaks generic-api-key at line 211, measured above), so the branch carries none of the 38 unit rows and NOT the hold row H1 that the PR body and the new CLAUDE.md row name as 'the hold'. The PR cannot be opened as is; a ruling and a commit are owed. Correction to GREEN's Q2: an edit of the frozen line is NOT the only remedy: the hook always passes --config = a copy of HEAD:.gitleaks.toml, so a prior commit that allow-lists that path (or that constant's regex) in .gitleaks.toml lets the RED file commit byte-identical (it breaks GC-11's 'ONE commit'; the orchestrator rules which).

### MINOR (documentation / rulings for the orchestrator)
- m1 Client RED row C2 (2 nodes) is a wrong row, CONFIRMED: legalV3.s81_12.test.ts:100-104, :111 call aiConsent.hasCurrentAiConsent() / recordAiConsent() without a user id; src/services/aiConsent.ts:78 hasCurrentAiConsent(userId: string | null), :84 recordAiConsent(userId, now) read 'no user' -> false / nothing written. The meant contract is green in aiConsentV2.s75 V2a-V2c (v2 not current; ensureAiConsent writes 3; v3 counts). Ruling: rewrite C2 with the user id (GREEN Q1).
- m2 Terms s8 (EN + AR) keeps the singular 'our AI provider' in the heading ('## 8. Intellectual property, your content and our AI provider') and in the licence grant ('to obtain comparisons from our AI provider as our Privacy Policy describes') while the same paragraph now names two providers; during the transition the licence wording covers 'our AI provider' only. No fence or pin moves (R24 pins privacy headings only). Recommend 'our AI providers' (heading + grant, AR twin) through the machinery in the fix round.
- m3 TERMS_VERSION bump during the OTA lag: consent_service.TERMS_VERSION / consent.ts = 2026-10-29 and legal_routes serve last_updated 2026-10-29 with the v3 Terms text, but build-3 phones send terms_version '2026-10-14' (their bundled consent.ts) at register / social sign-in, which consent_from_fields records 'as sent (what the user actually saw)' (consent_service.py:57-58). No request is refused (TERMS_VERSION is never compared at runtime: only legal_routes.py:57 / :76 read it), so no contract break; state it as a limit in the PR body.
- m4 AR coverage gaps (survivors X2, X8, X9, X10): R1[ar] checks names + any '30' + any '29'; R1b[ar] names only; R16[ar] section-level only; R17[ar] two literals. The AR policy can drop 'including photos', give Anthropic 90 days, or say Anthropic / OpenAI may train, with every legal row green. The owner's native read is the only control (GC-3); list these four facts in the PR body's [NATIVE READ] section as 'unpinned: check these', and extend the M-2 pin to AR (D3_HISTORY_AR shows exact AR pins are feasible).
- m5 Survivor X4: the s4 sentence 'Data shared with OpenAI under the programme before that date remains governed by OpenAI's terms.' can be deleted with every row green, leaving the dated s5 carve-out ('Except as section 4 describes for data shared with OpenAI before <date>') pointing at nothing in s4. Pin it with the M-2 row.
- m6 Survivor X12: R1[en] accepts a qualified Anthropic no-training sentence ('... unless we agree otherwise'). Ruling (weakening mutant).
- m7 The catalogue crawler sentence (privacy s6, EN + AR) is unhedged ('Our catalogue crawler ... reads merchant pages ...') right after 'We may also keep our own catalogue'. At merge no catalogue crawler runs (S81-15's flags OFF; the only UA naming https://getmyez.com/bot today is the off-clock sitemap channel, app/services/sitemap_discovery_service.py:387, ENABLE_SITEMAP_INDEX OFF, and scripts/resolve_search_descriptors.py:80): an over-disclosure in the at-merge state, dictated by R-S12-2. Accept as a stated limit or hedge ('When our catalogue crawler reads ...').
- m8 privacy s4 Anthropic facts (no training; up to 30 days; batches up to 29 days; the usage-policy / law exception; the web-search sentence) are asserted without a reading of Anthropic's documents (GREEN NOT MEASURED; no web grant here either). R-S12-13 makes the window commit record them; keep it on the flip-window checklist (it is there).
- m9 The PR body and the new CLAUDE.md row describe H1 as 'the hold' while H1 is not in the commit (M-3); re-state after the Q2 ruling.

## OpenAI census (EN, by section, on the GREEN bytes)
privacy s2: dual-provider sentence + the undated history sentence (D7); s4: dual-provider, transition, dated history, 'Since then ... abuse-monitoring' (no-training + retention), carve-out 'Data shared with OpenAI ... before that date'; s5: the OpenAI bullet (transition) + the dated carve-out; s9 (P6-frozen deletion text) names no AI provider; Terms s8: dual-provider + undated history; Terms s13 (P6-frozen): 'does not delete data already shared with OpenAI under its data-sharing programme' (true in all states). No OpenAI in privacy s3.2 / s3.3 / s3.6 / s8 (the M16 class killed by R16). Landing regions carry the source counts (R16 + P1 green; X11 killed by P1).

## Three-state truth check (EN and AR read side by side; the AR carries the EN facts except where M-1 and m2 apply to both)
- At merge (the flip window, the first S81-06 text-role flip, sharing OFF): the dual-provider and transition sentences are true; naming Anthropic is over-disclosure only if the text flip is rolled back. The consent v3 'not sent' sentence holds for Anthropic: llm_router.py:980-987 messages.create passes model / system / messages / max_tokens / thinking / output_config / timeout, no metadata or user id. s12 'we check requests and results for unsafe content' holds: L1 check_query_intent (structured_comparison_service.py:4260, :4923), L3 moderate_output (:4719), L4 vision moderation (image_routes.py:419). s14 is false in part (M-1).
- During the transition: the build-3 v2 sheet beside the v3 policy is over-disclosure, as the CLAUDE.md row says, because the router sends consent < 3 to OpenAI or refuses (llm_router.py:16-17, :347-356; MIN_CONSENT_VERSION 3 = AI_CONSENT_VERSION 3) and never to Anthropic. m3 applies.
- After OpenAI's retirement: the present-tense 'MYEZ uses ... OpenAI, L.L.C.' becomes false until S81-12b (a stated limit of R-S12-1; the PR body and the CLAUDE.md row state it).

## Generic correctness duties
- Flag-OFF identity: not applicable (no flag). Envelope / error-handler mapping and billing R-A3: untouched (the app/ diff = the four legal markdowns, processors.json and the TERMS_VERSION literal; no route, envelope, metering or refund code). Contract freeze (PLAN section 0): GET /api/v1/legal/* keys unchanged; only the content and the last_updated VALUE move.
- Dormant if_null hooks: R11 / R12 / R18 green on temp copies; X13 killed by R18; X14 refused by the machinery.
- Fill-in refusals: RETENTION_KEYS widened (M20 killed by R19); the KB clause has no {value}, so _check_value never runs for it and R18 is its only guard (X13).

## Prove-nothing / weak rows
- R16[en] sentence classes ('abuse-monitoring' / 'does not use' / 'no longer' / 'data-sharing programme') pass a sentence that says OpenAI MAY train (X1); R16[ar] is section-level only.
- R1[ar] ('30' and '29' anywhere in s4) passes X8 and has no AR no-training check (X9).
- R1b[ar] (names only) passes X2; R17[ar] (two literals) cannot see the M-1 class.
- R1[en] no-training check passes a qualified sentence (X12).
- R17[en] pins the wording that M-1 shows incomplete (S14_EN_REQUIRED 'random install identifier'; S14_EN_FORBIDDEN 'two random device identifiers').

## Counts
unit 37 / 38 (H1 red by design); CI-order 1157 passed / 1 failed (H1); jest rows 62 / 64 (C2 x2, wrong row); mutants: 14 / 14 spec mutants KILLED + control M0 neutral; adversary mutants 5 KILLED (X3, X5, X6, X11, X13), 1 refused by the machinery (X14), 7 SURVIVED (X1 [+X1F], X2, X4, X8, X9, X10, X12).

## NOT MEASURED
Anthropic's commercial terms / privacy policy (no web grant; m8); the full jest suite (GREEN's run stands); the comm set (engineering lens); the Arabic native read.

## git status --short (real worktree, end)
`A  tests/test_s81_12_legal_v3.py` (unchanged from start); HEAD 3c4a198d.

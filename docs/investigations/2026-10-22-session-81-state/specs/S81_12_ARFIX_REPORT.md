# S81-12 ARFIX REPORT -- verdict COMMITTED
unit S81-12 LEGAL-V3, the Arabic corrections round ARFIX (RULINGS_ARFIX_S81_12 AF-1..AF-10); fix agent Opus 5.5
head_before dd9738f77650fbda370ca75a99c8596e44d00412; head_after a0244f4403c55326ddf0171455805e7d2a5879aa (one parent dd9738f7); origin/main 6b909e0a (fetched twice: start and before the commit); git status --short empty after the commit
commit through the hook rc 0 (gitleaks "All checks passed!"), no --no-verify, not pushed

## AF-6 (1) opening checks
HEAD dd9738f7, branch feature/s81-legal-v3, status empty; frozen git blobs: legal_v3 e860e18d... OK, gate rows b98caa6a... OK (the client RED file not touched); AR policy f9a9de3b..., ar.json b5d84aae... OK; FETCH_HEAD 6b909e0a; junction ok (@babel/core, .bin/jest).

## Where each sentence LIVES (measured before editing)
All eight AF-2 policy / Terms spans are base text of the PRE-FILL SNAPSHOTS tests/fixtures/legal_prefill_u8/privacy_policy_ar.md and terms_of_service_ar.md (each with the same count as the rendered file); none lives in scripts/legal_variants_u8.json or tests/fixtures/legal_fill_in_u8.json (both unchanged, sha at the head kept). The two ar.json values live only in SmartCompareApp/src/i18n/ar.json.

## GREEN (AF-4)
snapshot edit (exact old -> new, counts P1 2, P2 2, P3 1, P4 1, P5 1, T1 1) -> restore (the six sources from the snapshot) -> scripts/fill_in_legal.py rc 0 (wrote the sources, rendered landing/ar/privacy.html + landing/ar/terms.html) ; ar.json: exact substring replacement on the git bytes (J1, J2 count 1 each; key list unchanged; exactly aiConsent.body + onboarding.s5.privacy_anon_body changed).
cmp with <scratch>/s12/arfix/expected (LF-normalised working copy): privacy_policy_ar.md BYTE-EQUAL 5cc039a3... blob 0c600d53 (34,433 B); terms_of_service_ar.md BYTE-EQUAL 7d9c53e5... blob 85e0e6a8 (25,950 B); ar.json BYTE-EQUAL 1fe60d12... blob 9bf36840 (71,911 B). The expected files were never copied into the tree.
fence digest by its recipe (node, from SmartCompareApp) = adfc77d2... (version 3 kept).
landing: landing/ar/privacy.html 12 lines (+6/-6, the six policy lines), landing/ar/terms.html 2 (+1/-1); EN pages unchanged.

## E-rows (file:line at HEAD a0244f44; old -> new; reason)
| id | file:line | old -> new | reason |
|---|---|---|---|
| RED G-k..G-o | tests/test_s81_12_gate_rows.py (:595-744 appended, G-k at :647 .. G-o at :728; docstring :31-36 gains (k)-(o); imports AR_CATALOG, _catalog, BOT_URL_AR) | - -> five rows test_g_k_move_to_anthropic_in_progress_tense, test_g_l_onboarding_step5_never_sends_clause, test_g_m_privacy_s6_links_and_canonical_bot_address, test_g_n_privacy_s14_random_install_identifier, test_g_o_data_shared_with_openai_common_construction + _nomarks (U+064B..U+0652, U+0670, U+0640) | AF-5 (a) |
| EK6 | tests/test_s81_12_legal_v3.py:132 (new line), :620, :623-624 (new) | + BOT_URL_AR = BOT_URL.rstrip("/"); R6 AR needle BOT_URL -> BOT_URL_AR; + 'AR s6 names the bot page address with the trailing slash' when BOT_URL in AR s6 | AF-5 (b), sanctioned; blob e860e18d... -> 3df7c93c... |
| CLASS U | tests/test_s81_12_gate_rows.py:581, :586, :588 (G-j) | `BOT_URL in s` -> `bot_url in s` (EN BOT_URL, AR BOT_URL_AR); docstring names both | G-j[ar] located the slashed address in the AR policy |
| CLASS T | SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts:43 (+2 comment lines :39-40 new) | sha256 77ac6348... -> adfc77d2...; version 3 | the fence pins the AR body bytes; a meaning-preserving copy fix re-records the digest alone |
| CLASS T | CLAUDE.md:199 | '(`77ac6348...`, re-pinned together with the version in ONE edit if a word changes)' -> '(`adfc77d2...` since S81-12 ARFIX, 2026-11-12: a copy fix that changes no meaning re-records the digest alone and keeps the version; a MATERIAL change re-pins the digest together with the version in ONE edit)' | the digest mention; the old sentence is falsified by this round |
| CLASS T | tests/fixtures/legal_prefill_u8/privacy_policy_ar.md :17 :66 :76 :97 :107 :161, terms_of_service_ar.md :57 | the AF-2 old spans -> new | the snapshots ARE the source the machinery fills (test_polish_prefill_snapshot_tracks_the_documents) |
| CLASS L | tests/test_s81_12_gate_rows.py:101 (CARVE_AR :99-104, G-c[ar]) | escaped P2 old (the rare passive) -> P2 new | G-c[ar] red after GREEN ('carve-out 0 times') |
| CLASS L | tests/fixtures/legal_s78.json s5_carveout_ar | P2 old -> new | test_s78_r11 red ('carve-out does not name the mailbox provider', the fixture sentence no longer matched) |
| CLASS L | tests/fixtures/legal_s78.json tos_s8_openai_ar | T1 old -> new | test_s78_r25 red ('ar terms s8: the OpenAI sentence is missing') |
| CLASS L | tests/fixtures/legal_d3c_u8.json fix2_ar.s5_carveout_head | P2 old -> new | test_d3c_n[C] / [A] red ('the carve-out head does not name the data shared with OpenAI') |
| CLASS L | SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts:78 (AR_SENTENCE), :80 (AR_SECTION2) | escaped J1 old -> J1 new | V4 AR body red (occurrences 0) |
| DOC | CLAUDE.md:641 (the S81-12 row) | + one ARFIX sentence before 'The hold: H1 of' | AF-7 (c) |
No other node went red (the full scan of the test trees for old spans, raw or escaped, marks-insensitive, leaves only MOVE_OLD_AR in the new G-k row, which is the intended negative check).

## Footprint (git diff --stat dd9738f7 HEAD): 14 files, +203 / -37; origin/main...HEAD stays 45 files (no new path)
CLAUDE.md; SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts (CLASS L, outside the AF-7 (b) list: E-row above); SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts; SmartCompareApp/src/i18n/ar.json; app/legal/privacy_policy_ar.md; app/legal/terms_of_service_ar.md; landing/ar/privacy.html; landing/ar/terms.html; tests/fixtures/legal_d3c_u8.json (CLASS L, E-row); tests/fixtures/legal_prefill_u8/privacy_policy_ar.md; tests/fixtures/legal_prefill_u8/terms_of_service_ar.md; tests/fixtures/legal_s78.json (CLASS L, E-row); tests/test_s81_12_gate_rows.py; tests/test_s81_12_legal_v3.py.

## EK6 diff
```
diff --git a/tests/test_s81_12_legal_v3.py b/tests/test_s81_12_legal_v3.py
index 2976c5de..5d1d2c4d 100644
--- a/tests/test_s81_12_legal_v3.py
+++ b/tests/test_s81_12_legal_v3.py
@@ -129,6 +129,7 @@ CRAWLER_EN = (
     "https://getmyez.com/bot/, reads merchant pages whose robots.txt permits it"
 )
 BOT_URL = "https://getmyez.com/bot/"
+BOT_URL_AR = BOT_URL.rstrip("/")  # EK6 (RULINGS_ARFIX_S81_12 AF-5 (b)): the Arabic names the canonical address
 # --- R-S12-10 (amended): privacy s14 -------------------------------------------------------
 S14_EN_REQUIRED = {
     "AI permission record removed with the account": r"(?i)\bdeleting your account (?:also )?removes the AI permission record\b",
@@ -616,9 +617,11 @@ def test_r6_privacy_s6_catalogue_crawler_and_sponsored(lang):
             if not re.search(pattern, s6):
                 problems.append(f"s6 lacks {label}")
     else:
-        for label, needle in (("the bot page address", BOT_URL), ("robots.txt", "robots.txt"), ("Sponsored", SPONSORED_AR)):
+        for label, needle in (("the bot page address", BOT_URL_AR), ("robots.txt", "robots.txt"), ("Sponsored", SPONSORED_AR)):
             if needle not in s6:
                 problems.append(f"AR s6 lacks {label}")
+        if BOT_URL in s6:
+            problems.append("AR s6 names the bot page address with the trailing slash")
     assert not problems, _report(f"R6 ({lang}): privacy section 6:", problems)
 
 
```

## Gates (every [pyt] / jest line)
(2) RED: [pyt] tag=s12a-red start=2026-11-12 03:07:10 end=2026-11-12 03:07:14 elapsed=5s bound=600s status=FAIL rc=1 -- 6 failed, 59 passed; [hermeticity] sentinel checked 65 test(s); [netguard] blocked 0 attempt(s) from 0 node(s); FAILED = H1 + G-k, G-l, G-m, G-n, G-o, each on an AssertionError (problems lists), the 22 existing gate rows green, the unit file 37 + H1.
(5) legal set + both unit files, first after GREEN: [pyt] tag=s12a-legalset-1 start=03:09:21 end=03:09:54 elapsed=34s status=FAIL rc=1 -- 6 failed, 554 passed (H1 + the five CLASS L nodes d3c n[C], n[A], s78 r11, s78 r25, G-c[ar]); fixed by CLASS L.
(5) [pyt] tag=s12a-legalset-2 start=2026-11-12 03:11:04 end=2026-11-12 03:11:42 elapsed=38s bound=1200s status=FAIL rc=1 -- 1 failed, 559 passed; [hermeticity] sentinel checked 560 test(s); [netguard] blocked 0 attempt(s) from 0 node(s); FAILED = H1 only.
(4) [pyt] tag=s12a-unit start=03:11:52 end=03:11:55 elapsed=4s status=FAIL rc=1 -- 1 failed, 37 passed (H1); [hermeticity] 38; [netguard] blocked 0.
(4) [pyt] tag=s12a-gaterows start=03:12:00 end=03:12:03 elapsed=3s status=OK rc=0 -- 27 passed; [hermeticity] 27; [netguard] blocked 0.
(6) [pyt] tag=s12a-alone-test_legal_docs_u8 start=03:12:09 end=03:12:34 elapsed=25s status=OK rc=0 -- 48 passed; [hermeticity] 48; [netguard] blocked 0.
(6) [pyt] tag=s12a-alone-test_legal_s78 start=03:12:39 end=03:12:47 elapsed=9s status=OK rc=0 -- 29 passed; [hermeticity] 29; [netguard] blocked 0.
(6) [pyt] tag=s12a-alone-test_legal_disclosure_s77 start=03:12:52 end=03:12:55 elapsed=3s status=OK rc=0 -- 31 passed; [hermeticity] 31; [netguard] blocked 0.
(6) [pyt] tag=s12a-alone-test_consent_capture_w3_16 start=03:12:59 end=03:13:03 elapsed=4s status=OK rc=0 -- 17 passed; [hermeticity] 17; [netguard] blocked 0.
(extra) CLAUDE.md readers after the CLAUDE.md edit: [pyt] tag=s12a-claudemd-readers start=2026-11-12 03:18:28 end=2026-11-12 03:18:45 elapsed=18s bound=1200s status=OK rc=0 -- 510 passed (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire); [hermeticity] 510; [netguard] blocked 24 attempt(s) from 2 node(s) (s04 r42, p08: neutralized.supabase.invalid sentinel).
(7) jest 29.7.0 by path (the S81-12 client RED file, __tests__/consent (5 suites incl. the four edited), landing.brand.s69, onboarding/step05Trust.s69; ConsentRow.copy.w3-16 matched the pattern too): first [jest] tag=s12a-jest-subset start=03:15:20 end=03:15:39 rc=1 -- Test Suites: 1 failed, 8 passed, 9 total; Tests: 1 failed, 76 passed, 77 total (aiConsentV2 V4 AR, CLASS L); after the fix [jest] tag=s12a-jest-subset2 start=03:16:38 end=03:16:53 rc=0 -- Test Suites: 9 passed, 9 total; Tests: 77 passed, 77 total; Snapshots: 0 total.
(7) tsc 5.9.3: [tsc] tag=s12a-tsc start=03:16:54 end=03:17:02 rc=0 errors=0.
(8) FULL jest once, last (timeout -k 15 1500, log jest-full.log):
[wait] jest-full waited 2s; probe clean at 03:19:01
junction ok
29.7.0
[jest] tag=s12a-jest-full start=03:19:03 end=03:19:23 rc=1
FAIL __tests__/config/nativeBundle.w37.test.ts (5.739 s)
FAIL __tests__/config/nativeBundle.w37.test.ts (5.739 s)
Test Suites: 1 failed, 3 skipped, 408 passed, 409 of 412 total
Tests:       4 failed, 13 skipped, 13 todo, 4039 passed, 4069 total
Snapshots:   41 passed, 41 total
  the four failed = config/nativeBundle.w37 d5, k2, k4, k5 (the accepted drift); 4,039 passed = the baseline of record; no .snap in the diff; the fourteen backend-scanning fences run inside it.
(9) scripts/fill_in_legal.py --dry-run rc 0, no output (idempotent); scripts/render_legal_landing.py --check rc 0; ruff --select E9,F63,F7,F82 --no-cache on the two touched python files: All checks passed; py_compile rc 0; git diff --check rc 0; English sha256 equal to ARFIX_INPUTS (privacy_policy.md 75e4fde3..., terms_of_service.md c48e97c5..., en.json 8e3f2206...), landing/privacy.html + landing/terms.html blobs unchanged.

## sha256 of every changed file (git bytes at HEAD; disk bytes CRLF where autocrlf applies)
CLAUDE.md	git_sha256=5384218a...	disk_sha256=78b53f2a...	blob=f3e0d9d3aee7509499ce9468798acb2d82d8fea5
SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts	git_sha256=dc164174...	disk_sha256=81ebf7ef...	blob=5db78d70becf5af3d842eec7bedb9664da07fe60
SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts	git_sha256=a08195ee...	disk_sha256=76966a05...	blob=5664f1b8dd7543beb4f5fdabb6e7d07f43bbfc44
SmartCompareApp/src/i18n/ar.json	git_sha256=1fe60d12...	disk_sha256=1fe60d12...	blob=9bf3684097fc8b76665c77341fb3216da31db0b0
app/legal/privacy_policy_ar.md	git_sha256=5cc039a3...	disk_sha256=d127339d...	blob=0c600d53448b0d14ebe73f898af7295e3e2d2e86
app/legal/terms_of_service_ar.md	git_sha256=7d9c53e5...	disk_sha256=65e9a3c7...	blob=85e0e6a87f15f4564bee7606af5b64ca97e52f71
landing/ar/privacy.html	git_sha256=109bdad0...	disk_sha256=b8ac0a15...	blob=0cf0855b99c1d180815082431858821afaf9948e
landing/ar/terms.html	git_sha256=cc826864...	disk_sha256=8da79cd8...	blob=7b2bb09a99058e4f00663ac11af9d0f58de4ee8d
tests/fixtures/legal_d3c_u8.json	git_sha256=f6342a2d...	disk_sha256=f710f7d2...	blob=51688df73a3ca6f80fdabd09c0800520a79eb9ea
tests/fixtures/legal_prefill_u8/privacy_policy_ar.md	git_sha256=8d5f7629...	disk_sha256=09883246...	blob=b334f843d49b467e80219a7955b9b145015c0de5
tests/fixtures/legal_prefill_u8/terms_of_service_ar.md	git_sha256=328a4efe...	disk_sha256=a9f96dfa...	blob=0cd8ec9bc57dd4f914040f661a6d39178f9bdbb0
tests/fixtures/legal_s78.json	git_sha256=09809a7c...	disk_sha256=c1c6f6a8...	blob=7cfff5d77dabe2b5616c284c98c5b44253cd57d4
tests/test_s81_12_gate_rows.py	git_sha256=4dd5c284...	disk_sha256=c459f0cc...	blob=5e9a594481d2f3f2fb22ea37056212ef1c802fa9
tests/test_s81_12_legal_v3.py	git_sha256=3df7c93c...	disk_sha256=ceead1bd...	blob=5d1d2c4dc77b014922b361f4299061149c491317

check app/legal/privacy_policy_ar.md 5cc039a3... OK
check app/legal/terms_of_service_ar.md 7d9c53e5... OK
check SmartCompareApp/src/i18n/ar.json 1fe60d12... OK
check app/legal/privacy_policy.md 75e4fde3... OK
check app/legal/terms_of_service.md c48e97c5... OK
check SmartCompareApp/src/i18n/en.json 8e3f2206... OK
check landing/privacy.html unchanged True
check landing/terms.html unchanged True
parents a0244f4403c55326ddf0171455805e7d2a5879aa dd9738f77650fbda370ca75a99c8596e44d00412
footprint origin/main...HEAD 45

## PR body
<notes>/PR_BODY.md: 25,454 bytes (<= 25,600), sha256 d07616cb...; ASCII apart from the attribution line; the merge-round section and the older history compressed (the window order, the checklist, the E-rows table and the stated limits kept); the ARFIX section, the E-rows, the R6 / R7 / R8 limit and the [NATIVE READ] CHANGED marks added.

## Deviations
- D1: jest-subset2 (03:16:38) ran while foreign s07r- pytest processes were live (the probe printed 4 and the call was not held back); a client jest run, hermetic; the full jest later waited for a clean probe (2 s).
- D2: one Write call resolved a relative path wrongly and created C:/SYNACK~1/AppData/Local/Temp/.../S81-12_arfix/class_l.py (outside the notes folder, 03:10); the file was moved into the notes folder and the empty directories were removed one by one with rmdir (no recursive delete); C:/SYNACK~1 no longer exists. No repo file was involved.
- D3: three CLASS L members sit outside the AF-7 (b) footprint list (legal_s78.json, legal_d3c_u8.json, aiConsentV2.s75.test.ts): each is an E-row above (literals of old AF-2 spans).

## NOT MEASURED (by this agent; the re-verifiers' per AF-9)
the comm set (RB2-8), the CI-order set (19 files), the mutants; the hook test files tests/test_precommit_hook*.py not run (no .githooks change).

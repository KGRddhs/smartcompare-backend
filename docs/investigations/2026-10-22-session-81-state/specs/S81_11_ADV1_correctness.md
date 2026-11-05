# S81-11 ADVERSARY -- lens: correctness (Claude Opus 5.5), 2026-11-05 10:40-11:30 AST

VERDICT: SOUND (0 blocking, 0 major, 7 minors -> stated limits / orchestrator rulings)

Unit S81-11 HONEST-FRAGRANCE-UI (+ D20). Worktree sc-s81-s11, branch feature/s81-s11-honest-fragrance-ui, HEAD 5fcb9fba3b9d78c23289685613c0ae75f4d1199d (verified first and last), base 6869a3e6.

## Method and harness deviation (stated)
- The task's last paragraph asked for a detached scratch worktree; GC-11, the client exception in the task body and s81-common.txt ("NEVER create one that needs node_modules") rule it out for a client unit. Every probe and mutant ran IN PLACE in sc-s81-s11 under `.qa-mutation.lock` (label "adversary-correctness S81-11"), with shutil byte copies in correctness/bytes/ (12 files), restored and sha256-compared after each mutant (0 mismatches). At the end: HEAD unchanged, `git status --short` empty, `git diff --quiet HEAD` rc 0, lock removed. No git write anywhere. No .env read. No package manager.
- Toolchain by path through the junction: node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint v9.39.4.

## Byte verification
- The 8 RED files re-hashed at start and end: all equal GC-1 (b30471b3 / f6761781 / 35aa6655 / 48988983 / e4abba60 / 751b24d6 / 573a9c13 / c3e4224c).
- The 62 diff paths re-hashed against the GREEN report's table: 62 rows, 0 mismatches (2 DELETED confirmed absent).
- New leaves launchSurfaces.ts / fieldStatusView.ts: ASCII, LF in blob and working copy. Catalogs, CLAUDE.md, api.ts: i/lf w/crlf (autocrlf), index LF as at base. No package.json / lock / app.json / native / .env / app/ / scripts/ / migrations/ / tests/*.py path in the diff. The .snap diff deletes exactly the `renders default snapshot 1` export (147 lines), the counter-target export kept.

## Runs ([jest] / [tsc] / [eslint] / [pyt] lines)
[jest] tag=adv-red start=2026-11-05 10:45:30 end=2026-11-05 10:45:36 rc=0   -> 8 suites, 124 / 124
[jest] tag=adv-erows start=2026-11-05 10:45:49 end=2026-11-05 10:46:06 rc=0 -> 49 suites (all 29 E-row/E1b test files + b3a honestCopy + i18n/ + hero/ + errorCopy.a11 + appVersionService.a9 + api.streamComparison.expoFetch + HomeScreen.errorCopy.a11 + camera.engineUnavailable.s69), 530 / 530
In-band pairs, both orders (GREEN's order-preserving sequencer), all rc=0:
[jest] adv-pair-api-ab/ba (sseFallback.s11 x api.streamComparison.expoFetch) 19/19 each
[jest] adv-pair-rc-ab/ba (honestUnknowns.s11 x components/ResultsContent.render) 59/59 each
[jest] adv-pair-home-ab/ba (categoryRow.s11 x HomeScreen.bundleE.s3.integration) 41/41 each
[jest] adv-pair-ver-ab/ba (launchSurfaces.s11 x appVersionService.a9) 60/60 each
[jest] adv-pair-err-ab/ba (refusals.s11 x errorCopy.a11) 37/37 each
[tsc] tag=adv-tsc start=2026-11-05 11:09:18 end=2026-11-05 11:09:26 rc=0 (re-confirmed rc 0 by a second plain run)
[eslint] tag=adv-eslint start=2026-11-05 11:09:31 end=2026-11-05 11:09:40 rc=0 -> 55 changed ts(x) files, 0 errors, 246 warnings (pre-existing classes)
[pyt] tag=s11adv-cor-be-c1 start=2026-11-05 11:20:24 end=2026-11-05 11:21:31 elapsed=66s bound=1200s status=OK rc=0 -> 1846 passed, 4 deselected (= base / GREEN)
[pyt] tag=s11adv-cor-be-c2 start=2026-11-05 11:24:20 end=2026-11-05 11:24:39 elapsed=18s bound=1200s status=OK rc=0 -> 458 passed (= base / GREEN; with test_ci_gates in c1 = the 6 CLAUDE.md readers)
(Both pyt runs waited for the S81-20 lane's pytest to exit first: one pytest at a time.)

## Mutants (in place, run against the 8 RED files; logs runs/mut-*.json, table mut_all.txt + mut_results_*.json)
RED mutants re-applied (19, all KILLED): M1, M2, M7, M9, M12, M13, M14, M17, M18, M20, M21, M22b, M24, M25, M29, M30, M31, M33, M41. (M36 not applied: equivalent by ruling GC-3.)
Own mutants (18): KILLED 13 -- O1 terminal-frame reason dropped, O2 Home onComplete reason dropped, O4 resultOrigin always live, O5 link send site ungated, O6 soon chips without surfaces, O8 categories_live not lowercased, O9 legacy detail.code ignored on the SSE non-OK arm, O13 field line ignores a listed row, O15 camera routes any reason, O16 no_evidence mapped to a reason key, O17 honest line not rendered, O19 store recorded on a non-OK version read, O20 CATEGORY_NOT_LIVE -> Paywall.
SURVIVED 5 (also re-run against the 29 E-row files + __tests__/screens/ + __tests__/components/ + HomeScreen* + errorCopy/api suites: still survived; the GREEN code is right in every case, the lines are just unpinned -> minor m1):
- O3 the URL 200 success:false Alert drops `response.data.reason`
- O10 the converted-from-USD caption also renders under the honest line (kind unknown)
- O11 staleNoDate also for STORED bodies (R-S11-13: stored lines are dateful and stateless)
- O14 announceForAccessibility on Android too (R-S11-23: iOS only)
- O18 staleNoDate for any field_status price entry with no date (not only state stale)

## Runtime-truth probes (code read against the rulings)
- Flag-OFF / absent identity: absent categories_live -> categoryToSend undefined on BOTH send sites (stream options + /url/compare body; killed M1/M2/O5); absent surfaces -> one Fragrances chip (O6 killed); absent field_status/section_status -> no `honest` prop (M21 killed); absent price.as_of and field_status -> priceProvenance 'none' -> the price Text element and the converted caption are the base element and style; only the cohort slot is gone (intended, R-S11-31). Absent reason -> today's key (O16, P2 rows). Camera: no code / no reason / placeholder_identity -> vision_failed (O15 killed).
- SSE (R-S11-19): non-OK arm reads the body once; CATEGORY_NOT_LIVE (top or detail) -> onError + sawTerminal + return, no runRestCompare; every other non-OK and the no-body arm throw into the unchanged REST fallback (M12/M13/O9 killed). Error event and both terminal frames forward a string reason (M32-class O1 killed, M33 killed).
- Refusals: text/link 400 + 429 CATEGORY_NOT_LIVE -> title home.categories.fragrancesOnly, body home.errors.categoryNotLive, no count, never Paywall (isUsageLimitError keys on USAGE_LIMIT only; O20/M9/M41 killed). Camera: the backend camera_refusal_body / camera_budget_body are HTTP 200 action:error with code CATEGORY_NOT_LIVE (app/services/category_gate.py:601-613) -> results-category-not-live-state, Back CTA, no seconds (M14 killed).
- D20: R-S11-12 estimate -> unknown only under a field_status unknown entry (M20 killed); R-S11-13 stored = the comparison_id entry (History, Home smart-pick, Profile recents: every `navigate('Results', {comparison_id})` site) -> 'listed', never aged (M29/O4 killed); R-S11-18 dateless stale marker (M30 killed); R-S11-21 unavailable only (M22b killed); R-S11-14 retailer as-is, trimmed; R-S11-24 explicit gregory (M31 killed). Invitee and share do not mount ResultsScreen in the client (the quiz renders a score row; a share opens the landing), so `comparison_id` is the only stored entry the app has.
- Counters: LoadingRings default removed + chip only for a numeric target (M24 killed); InviteeQuiz 78 removed (M25 killed). M36 stays equivalent (the chip gate makes the guard unobservable).
- Catalogs (measured): 1,011 / 1,011 leaves, parity 0; 15 added / 10 changed / 17 deleted (= the RED copy.s11 arithmetic 1,013 - 17 + 15); no deleted key referenced in src (one comment mention of loading.tip.peer_prioritize in LoadingScreenVariants.tsx:173); every key the new code reads exists in both catalogs; GC-4: the only diacritic in a new/changed AR value is the shadda inside the brand word (referrals.share.messageWithLink), exempt by r31b; no forbidden EN / AR word; no EN digit. [NATIVE READ]: 25 rows, every added/changed key present, AR and EN cells byte-equal to the catalogs.
- Billing R-A3 and the PLAN section 0 contract freeze: untouched (no backend file in the diff; the client only reads the additive reason / field_status / section_status / as_of / categories_live / surfaces keys).

## Findings
BLOCKING: none.
MAJOR: none.
MINOR (stated limits by default, LC-4):
- m1 (prove-nothing rows) five behaviours of the GREEN code are correct but unpinned: O3 (URL 200 success:false reason), O10 (converted caption suppressed under the honest line), O11 / O18 (staleNoDate only for a live body whose price entry is state stale), O14 (iOS-only announcement). Optional: one test-only gateRows.s11 file in the final round (LC-2); else a stated limit.
- m2 a field_status price entry `unknown` / `no_price` beside a numeric, non-estimated amount the backend judged non-showable (empty source_method, or amount <= 0, result_gate.price_is_showable) renders the bare amount, not the honest line (priceProvenance only replaces when there is no amount or an estimate). A narrow edge; stated limit.
- m3 a field_status price entry `stale` with reason `unmarked` (price._cached absent, kb_ingest.py:196-200) also shows "Price checked earlier", which asserts a cache read that may not have happened. Stated limit.
- m4 (docs) the CLAUDE.md block and the PR body say absent metadata = the build-3 render and place the as-of dates "under metadata.field_status"; the card also reads `price.as_of` WITHOUT field_status (designed, RED E1r rows pp(..., null)), so ENABLE_KB_FIRST_SERVE alone puts as-of / last-seen lines on live cards and replaces a live price whose as_of is older than 30 days with the honest line. The exact OFF identity is absent metadata AND absent price.as_of; the owner flip order (step 2) does not name ENABLE_KB_FIRST_SERVE as a render-changing flag for this OTA. Wording fix at the final round.
- m5 (docs) the gate text's "12 added / 7 changed" vs the measured 15 / 10: GREEN reported it as D-G1; 15 / 10 is what GC-8's 1,011 and the frozen copy.s11 arithmetic require. Orchestrator ruling only.
- m6 (docs, carried from GREEN) the CLAUDE.md Frontend line "CohortBadge inline below verdict" and the PersonalizationChip.tsx header comment still name the deleted badge (outside GC-14).
- m7 (scope note for the App-Review lens) TrendingNearYou "Popular comparisons" can still offer a non-fragrance pair, which the gate refuses after the flip (the refusal copy, never the Paywall); not in the S81-11 change list.

## Not run (by ruling)
The full jest suite (LC-7: the final round), the jest comm set re-run (GREEN's; the RED + E-row + touched suites above are green), the R8 pair, paid-route metering as a gate, the hook test files, a pytest CI-order set, the corpus gate, a base scratch worktree.

## Files
correctness/mutants.py, mut.py, jrun.sh, jsum.py, nr.py, be.sh, mut_all.txt, mut_results_*.json, runs/ (jest json + logs, tsc.log, eslint.log, pyt_c1.log, pyt_c2.log, jest_lines.txt), bytes/ (the mutation byte copies).

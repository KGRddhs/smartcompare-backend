# SESSION 63b handoff — price cluster + mobile wave M23, saved mid-flight 2026-09-06

**Fable orchestrator, Opus 5 workers. Both write-workflows were STOPPED DELIBERATELY at a clean
checkpoint** (not killed by a cap) so this snapshot is exact. `origin/main` = `76ace90` — **no code
has been merged to main this session.** Everything lives on two pushed feature branches.

> ## ⚠️ COORDINATION — SESSION 64 SHARES THIS CHECKOUT
> A parallel session ("SESSION 64", M22 review campaign, 4 review workflows) is working **in the
> same `sc-scraper-proof` working tree.** Its untracked scratch is present and MUST NOT be cleaned:
> `SmartCompareApp/{a11y_out.json,a11y_sites.json,hit_list.txt,hit_out.json,out_c.json}`,
> `a11y_prior.txt`, `docs/investigations/2026-09-06-m22-review-state/`. **Never `git clean`, never
> `git stash -u`, never `rm` those.** `git status` will always look dirty here — look at TRACKED
> changes only (`git status --porcelain | grep -v '^??'`).
> - I reset `master` back to `origin/main` so Session 64's docs commits from this tree cannot drag my
>   UNGATED price code onto main. **My price code exists ONLY on `feature/m22-price-truth-cluster`.**
> - I did **NOT** edit `CLAUDE.md` or the top of `CONTEXT_SESSION_LOG.md` this session — Session 64
>   is saving into them. **DEFERRED TODO, to be done at merge time AFTER Session 64's save lands and
>   after a rebase:** add the 7 new price flags (below) to CLAUDE.md's flag table. The repo contract
>   says every flag is documented there; the #52 implementer flagged this gap explicitly.
> - `MEMORY.md`: I edited only my own SESSION 63 line. Session 64's line is theirs.
> - Before ANY push to main: `git fetch && git rebase origin/main`, then push. Two sessions push here.

---

## 1. PRICE / CACHE-TRUTH CLUSTER (#51–#57) — 7/7 IMPLEMENTED, **UNGATED, UNMERGED**

**Branch `feature/m22-price-truth-cluster` @ `7dd04c1`** (7 linear commits on `76ace90`, pushed).
Workflow `wf_3c174a13-8c7` (script `…/workflows/scripts/price-truth-cluster-v2-wf_3c174a13-8c7.js`).
Every implementer reported DONE with a REAL strip-check (fix removed → tests fail; recorded per task).

| Issue | Commit | Flag (all default OFF, read per call) |
|---|---|---|
| #52 iHerb real currency signal | `334d300` | `ENABLE_IHERB_PAGE_CURRENCY` — **currency-LABEL change, canary ALONE** |
| #51a fan-out keeps converted provenance | `e748cbb` | `ENABLE_CONVERTED_PROVENANCE_STAMP` |
| #53 clear `nogenuine:` on genuine persist | `98231bd` | `ENABLE_NEGCACHE_GENUINE_INVALIDATION` |
| #54 Tier-3 estimate must not clobber genuine | `a2efaa2` | `ENABLE_GENUINE_PRICE_CLOBBER_GUARD` |
| #57 L2→L1 promote with remaining TTL | `81464bf` | `ENABLE_L2_PROMOTION_REMAINING_TTL` |
| #56 regional prices under inferred category | `fd1b97d` | `ENABLE_REGIONAL_PRICES_CATEGORY` |
| #55 admin flush hits the live key + sentinel + L2 | `7dd04c1` | `ENABLE_FLUSH_LIVE_PRICE_KEY` |

**Reviews done:** flag-discipline (4 findings, **1 must_fix**), test-quality (5, 0 must_fix),
cache-coherence (7, 0 must_fix but a **P1**). **NOT done:** provenance-truth review, byte-identity
gate, comm gate (all three were killed by the cap, then stopped by me before re-running).

### MUST FIX before gates (fix-wave-2)
1. **#55 tautological test (reviewer must_fix).** `tests/test_flush_live_price_key.py:131-146`
   `_expected_price_keys` is a character-for-character copy of `app/api/text_routes.py:936-946`
   `_flush_price_cache_keys` — it can only agree with itself. Rewrite to assert against the key the
   LIVE price path actually writes (call `build_size_aware_price_cache_key` / capture the key the
   live path sets), so a drift between flush and writer FAILS.
2. **#54 × #53 interaction — P1, DISPATCHER-CONFIRMED, reviewer under-flagged it.**
   `app/services/structured_comparison_service.py:7538-7565`: the caller DISCARDS
   `_persist_tier3_estimate`'s return and then UNCONDITIONALLY calls
   `_record_negative_price_cache(cache_key, price, …)` with the estimate. When #54's guard fires
   (`:7831-7843`, L1 already holds a GENUINE price → returns False, skips the write), the 30-day
   `nogenuine:{key}` sentinel is still planted holding the estimate; the next request's negcache read
   (`:5721`) serves it and SHADOWS the genuine price the guard just protected. #53's delete ran
   earlier (on the genuine persist that made the guard fire) so ordering defeats it. With both flags
   ON, one fix undoes the other. **Fix (flag-OFF byte-identical — the return is only False under
   `ENABLE_GENUINE_PRICE_CLOBBER_GUARD`):**
   ```python
   persisted = await self._persist_tier3_estimate(cache_key, brand, name, variant, region, price)
   if persisted:
       self._record_negative_price_cache(...)   # unchanged args
   # else: L1 already holds a GENUINE price — the opposite of a structural dead-end (#54 x #53)
   ```
   + a load-bearing test: guard fires → `set_negative_cache` NOT called.
3. **Worth taking in the same wave (P2s from the reviews):** #54's guard re-reads L1 with different
   rules than `_get_price`'s own L1 read (no identity revalidation); #54 without #57 makes #57's
   staleness more reachable (→ **canary order: #57 with/before #54**); #55's `success` field never
   consults whether the L1 deletes actually succeeded (the honest-reporting half is not honest);
   #52's F2.2 microdata-fallback half is UNTESTED (neutering it leaves all 14 nodes green); #55
   rung-2 (raw-q / inferred-category key) is dead under both fixtures; two hand-copies of the
   genuine-method set still exist (the #67 defect).

### Resume recipe (price)
1. The workflow's reviews/gates run `git log origin/main..HEAD` in the MAIN tree, so the branch must
   be checked out there — **but Session 64 shares that tree.** Prefer a NEW worktree:
   `git worktree add C:/Users/SynAckITPC/Documents/AI/sc-price-w2 feature/m22-price-truth-cluster`
   + copy `.env` in, and point a fresh fix-wave-2 workflow at it (sequential implementer for items
   1-3 above → then byte-identity + comm gates on the new HEAD).
2. Only THEN merge to main (rebase first), add the 7 flags to CLAUDE.md (after Session 64's save),
   close #51-#57 with the commit SHAs.
3. `Workflow({scriptPath, resumeFromRunId:'wf_3c174a13-8c7'})` replays the 7 impls + 3 reviews from
   cache and re-runs provenance + gates — valid only if the checked-out tree is the branch.
4. `#52` note from its implementer: the byte-identity script exercises `extract_price_from_html`
   over `_proof`, which never calls `fetch_iherb_price` — that gate is STRUCTURALLY BLIND to #52;
   its flag-OFF claim rests on 4 explicit flag-OFF pins over 5 fixtures. Say so in the merge note.

## 2. MOBILE FIX WAVE M23 — **13/24 IMPLEMENTED**, worktree clean, pushed, UNREVIEWED

**Worktree `C:/Users/SynAckITPC/Documents/AI/sc-mobile-w1`, branch `feature/m23-mobile-w1` @
`1e7c894`** (13 commits on `76ace90`, pushed, clean — the stop landed between tasks).
`node_modules` there is a **Windows JUNCTION** to the main checkout's; `.env` copied. Recreate if
missing: `git worktree add … feature/m23-mobile-w1`, PowerShell `New-Item -ItemType Junction -Path
<wt>/SmartCompareApp/node_modules -Target <main>/SmartCompareApp/node_modules`, copy `.env`.
Workflow `wf_5de04c45-6be` (script `…/scripts/mobile-fix-wave-m23-wf_5de04c45-6be.js`).

**DONE (13, in order):** A18 `b73c47e` from_history dead-tap · A11 `29e6c65` friendly error copy ·
A15 `63eab48` dead usage fetch · A7 `2ad75d2` settle_complete latch · A8 `d610e5a` raw-fetch
deadlines · A4 `d092ea1` loader cancel+watchdog · A2 `57f5649` honest checklist pacing · A3
`e58f022` optimistic boot · A5 `1e9f915` splash floor ends when ready · B5 `c2ad80f` init guards ·
A12 `4f470cc` History search UX · A17 `c8b998e` History→Results floor · A10 `1e7c894` RevealBurst +
PhoneMockup bound.

**REMAINING (11):** B3 LoadingRings bind · B6 Arabic logout copy · B9 minor no-op controls · A16
CounterTicker guard · **B4 Cairo weights + 2 dead files (458 KB size win)** · **B1 lucide per-icon
imports (~1.05 MB size win, 44 files — measure before/after)** · A9 force-update client check ·
**A1 camera `/image/identify` metering (backend flag, SIX refund exits — the double-charge trap)** ·
**A6 url/compare metering+history+category (backend flag)** · **B2 expired-token 401 (backend flag
+ client)** · HYG root scratch cleanup (16 tracked files; re-verify each; never `_proof/`).
Then 4 reviews (copy-and-rtl, did-it-fix-it, flag-and-test-quality, size-and-build) + 2 gates
(frontend jest/tsc/eslint; backend comm for the 3 route files).

**Resume:** `Workflow({scriptPath:'…/mobile-fix-wave-m23-wf_5de04c45-6be.js', resumeFromRunId:
'wf_5de04c45-6be'})` — the 13 done impls replay from cache; B3 onward runs live. Check
`git status --porcelain` in the worktree FIRST; if dirty, preserve to `wip/m23-<task>-partial`,
push, reset, then resume (pattern used twice this session).
**None of the 13 commits has been through review or the full gates** — only per-task `tsc` exit 0 +
own tests. Do not merge before the wave's Review + Gate phases run.
**Ship lever after merge:** `eas update --branch preview` (Ahmed) — mobile code on main does NOT
reach phones by itself.

## 3. RECONCILE VERDICTS (post-M21) — `wf_5b770b81-842`, 27 findings
**24 STILL LIVE (all lane-clear), 2 FIXED_BY_M21** (A13 History stagger, A14 History keystroke
re-render), **1 REFUTED** (B7 compare double-tap — a guard exists). Full per-finding
`current_location` + `fix_shape` in the run output (`…/tasks/wehlxz1kg.output`).
**Hygiene guardrail lane:** 8 SAFE-to-remove (5 unused Cairo weights 458 KB; lucide barrel ~1.05 MB;
`SmartCompareApp/dist/` is UNTRACKED build output — no repo change; `src/types/react-native-vector-
icons.d.ts`; `assets/logo-wordmark.png`; 16 root scratch files [medium]; `useTypography.ts` [low]);
**18 LOOKS-DEAD-BUT-IS-NOT** incl. EVERY suspect package.json dep (react-native-screens/worklets/
gesture-handler/expo-dev-client/expo-build-properties/expo-updates/expo-notifications/intl-pluralrules
— config-plugin or peer-dep linked), all icon/splash assets, `OFL.txt`, all 16 snapshot files, both
`.d.ts` shims, `@sentry/browser` (hard dep of @sentry/react-native), markdown-it (LegalScreen).
**`_proof/` (949 MB) is LOAD-BEARING — never delete.**

## 4. ISSUES
`#51–#57` still OPEN (code on branch, ungated). 33 open total (see the 2026-09-02 findings doc §D).
No issue was closed this session.

## 5. STALE BRANCHES (delete after confirming superseded)
`wip/52-iherb-currency-partial` (superseded by `334d300`), `wip/m23-a2-honest-checklist-partial`
(superseded by `57f5649`).

## 6. LESSONS THIS SESSION
- Three cap kills (resets 06:50 / 01:00 Asia/Bahrain). **Commit-per-task saved everything**; the
  two orphans (#52, A2) were rescued via `wip/*` branches and reused by the re-run implementers.
- **Two sessions in one checkout:** `git status` dirty ≠ my dirty. Keep code on feature branches;
  reset the shared `master` to `origin/main`; write docs to files you own; edit only your own line
  in `MEMORY.md`; defer shared-file edits (CLAUDE.md) to merge time after the other session saves.
- IDE diagnostics fabricated `×` errors again (`friendlyErrorKey`, duplicate `fetchWithDeadline`,
  `minDisplayUntilRef`); `tsc` exit 0 every time. Trust only tsc/jest.
- Concurrent git ops on this repo (two workflows + gate worktrees) push simple `git show`/`push`
  past 60-180s — run git serially, background the long ones.
- A reviewer's `must_fix=false` is not "safe": the #54×#53 P1 was filed as non-must_fix. Gate every
  P1/P2 yourself.

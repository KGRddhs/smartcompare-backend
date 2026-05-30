# Bundle E S3 — Visual Fidelity Completion + Product Image Pipeline

**Filed:** 2026-05-30
**Status:** Approved by Ahmed (this session)
**Predecessor:** Bundle E S2 (`d2d9386` merged + deployed; visual fidelity PARTIAL — surfaces below incomplete)
**Successor doc:** `docs/plans/2026-05-30-bundle-e-s3.md` (implementation plan, written next)

---

## Why this bundle exists

Bundle E S2 shipped 17 onboarding step REWRITEs + LoadingScreen variants + Profile/EditPrefs OptionRow + SlideTransition wrap. The walk-verdict gate scoped to Step14 + Step17 came back GREEN. The dispatcher (this session) over-extended that to "all S2 surfaces GREEN" and rolled to ship: merge → Railway deploy → OTA `d063114b-...` to preview channel → EAS build for TestFlight kicked off.

Then Ahmed's wider device walk surfaced 6 incomplete surfaces:

1. **HomeScreen** — visual layout bugs (overlap / clipped / misaligned) + silent empty sections
2. **Comparison Results screen** — Claude-Design merge NEVER attempted (current `ResultsScreen.tsx` is 1956L Bundle B/C/D scoring overhaul; JSX reference is 410L)
3. **Profile screen** — partial S2 work (REWRITE claimed but incomplete vs JSX 323L)
4. **EditProfile screen** — partial S2 work (OptionRow shipped, but incomplete vs JSX 233L)
5. **History screen** — not checked vs `HistoryScreen.jsx` 388L
6. **Product images** — comparison cards have placeholder slots but no backend `image_url` plumbed through

TestFlight invite path is HALTED pending S3 completion. EAS build that's already running is sunk-cost-but-useful (the build is a shell; it fetches the post-S3 OTA on tester first-launch).

## Scope

### What's IN scope

- **5 frontend REWRITEs** (Home, Profile, EditProfile, Results, History) top-down per the `docs/claude-design-handoff/ui_kits/mobile/*.jsx` references
- **Backend image_url pipeline** wiring existing extractors + adding Tier 1 Serper Images fallback (tier cascade matches price pipeline architecture)
- **Frontend image rendering** in Results / History / SmartPick card slots with placeholder fallback when null
- **80% red/green test coverage** on all new code (Jest for FE, pytest for BE)
- **Ring cross-QA** — every PR peer-reviewed by another agent before dispatcher merges
- **One device walkthrough** at the end across all 6 surfaces on a single OTA

### What's OUT of scope (explicit DEFERRALS)

- App icon ICN-0001 byte-identity — App Store production blocker, TestFlight ships fine. Bundle F.
- Legal docs Qaren-jurisdiction redraft — App Store production blocker, TestFlight ships fine. Bundle F.
- Native deps additions — keep S3 JS/TS-only so the existing EAS build can serve the post-S3 OTA without a rebuild
- Bonus expiry / re-engagement push flag flips — separate flag-flip decision, not S3 work
- The 5 parked post-Bundle-E items from the original handoff (#16/#18/#25/#26/#34) — keep in their own bundles

## Architecture

### Frontend lanes (4 surfaces in 2 agents)

**A1 — `fe-home-profile` (Opus, isolation=worktree):**
- REWRITE `SmartCompareApp/src/screens/HomeScreen.tsx` top-down against `docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx` (717L)
- REWRITE `SmartCompareApp/src/screens/ProfileScreen.tsx` top-down against `ProfileScreen.jsx` (323L)
- REWRITE `SmartCompareApp/src/screens/EditProfileScreen.tsx` top-down against `EditProfileScreen.jsx` (233L)
- Verb discipline: REWRITE (per `memory/feedback_compose_vs_rewrite_phrasing.md`), no "compose" or "patch"
- Each prompt includes enumerated element order + explicit DELETE list for stale Bundle D pieces
- Fix HomeScreen empty-section bugs (likely backend-shape conditionals or RLS-gated data; diagnose then fix in same lane)

**A2 — `fe-results-history` (Opus, isolation=worktree):**
- REWRITE `SmartCompareApp/src/screens/ResultsScreen.tsx` top-down against `ResultsScreen.jsx` (410L). **HIGHEST RISK** — current is 1956L Bundle B/C/D scoring overhaul. Preserve scoring_v2 / personalization / SSE contracts; only rewrite presentation layer.
- Check `HistoryScreen.tsx` against `HistoryScreen.jsx` (388L). If structurally aligned → close gaps; if not → full REWRITE.
- Both lanes consume `products[*].image_url` per A3's contract spec (placeholder fallback when null)

### Backend lane (1 lane, dedicated agent)

**A3 — `be-images` (Opus, isolation=worktree):**
- Existing infrastructure to plumb:
  - `app/models/product_schema.py:125` already has `image_url: Optional[str] = None` on Product model
  - `app/services/url_extraction_service.py` already extracts `image_url` from og:image / JSON-LD / microdata / `<img>`
  - `app/services/serper_service.py:414` has `search_images` (dedicated Serper Images Tier 1 endpoint)
- Tier cascade (mirror price pipeline architecture):
  - **Tier 1 — Serper Images** (`search_images(query, num=1)`, 1 Serper credit per product); when Tier 1.5 page-scrape already returned an image, skip Tier 1
  - **Tier 1.5 — Page scrape** (`url_extraction_service.extract_from_url`) — piggyback on existing price-tier page scrapes; image_url is already extracted, just plumb to comparison response
  - **Tier 2 — Firecrawl** (existing service) for SPA pages where curl_cffi fetched HTML without an image
  - **Tier 2.5 — Scrape.do** (existing service) for residential-proxy-required sites
  - **Tier 3 — GPT-4o-mini fallback** — extract `image_url` from organic results when all prior tiers fail
  - **Final fallback** — `null`; frontend renders placeholder
- Budget gating: `api_budget_service` Firecrawl/Scrape.do/Serper counters already in place; add `serper_image_calls_today` counter (separate from regular `serper_calls_today`) so image pipeline doesn't starve price/spec budget
- Contract for FE: `products[*].image_url: string | null` at comparison response top level
- Tests: tier cascade + null fallback + budget breaker + Serper Images mock; 80% coverage on new code

### Image rendering + QA hub lane

**A4 — `fe-images-qa-anchor` (Opus, isolation=worktree):**
- Wire `image_url` into the comparison card slots:
  - `ResultsScreen.tsx` product card image slot
  - `HistoryScreen.tsx` row mini-VS card image slots
  - `HomeScreen.tsx` SmartPick card image slot
- Placeholder fallback when `image_url` is null (use existing placeholder primitive — DO NOT introduce a new one)
- Responsive `<Image>` sizing matching JSX `aspectRatio` per card
- Tests: present-state, null-state, broken-URL-state
- **QA hub role:** A4 starts working on image rendering immediately, but cycles into peer-QA reviews as PRs come in from A1/A2/A3 (see Ring cross-QA below)

## Ring cross-QA

Every PR must pass peer-QA from a different agent before dispatcher merges:

| PR from | Peer-QA owner |
|---------|---------------|
| A1 | A4 |
| A2 | A1 |
| A3 | A2 |
| A4 | A3 |

**Peer-QA gate per PR:**
1. Read the JSX source of truth + the agent's REWRITE
2. Confirm element order matches JSX (no defensive "added a piece I thought useful")
3. Confirm DELETE list was actually executed (no stale Bundle D pieces lingering)
4. Run the agent's tests + run independent smoke for the surface
5. If anything subpar or missed → send back to original agent with specific complaints + cite which JSX line/element is the deviation
6. If GREEN → return to dispatcher with "peer-QA PASS" + the cross-QA checklist

**Idle behavior:** while waiting for peer-QA to return their review, the original agent writes more red/green tests to push toward 80% coverage. **No idle agent.**

## Definition of Done

- All 4 lanes report PR-ready
- All 4 PRs have peer-QA GREEN
- Static gates: `npx tsc --noEmit` exit 0 (FE), `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)"` exit 0 (BE)
- 80% coverage on new code (Jest --coverage for FE, pytest-cov for BE)
- Dispatcher merges all PRs to main, fires one OTA to preview channel
- Ahmed device-walks all 6 surfaces. RED on any → that lane's agent re-dispatches.
- GREEN all 6 → TestFlight invite path opens

## Operating principles (the team reads this before starting)

1. **REWRITE verb is required** (per `memory/feedback_compose_vs_rewrite_phrasing.md`) — never "compose" or "patch." Enumerated element order + explicit DELETE list in every per-lane prompt.
2. **No deferrals without dispatcher approval** (per `memory/feedback_deferral_discipline.md`) — agents cannot invent "S4 polish phase" to defer items in their lane scope.
3. **Animation initial value = settled state** (per `memory/feedback_animation_initial_value_must_be_destination.md`) — never initialize Reanimated shared values at animation source. Any new animated wrapper follows the SlideTransition #40 fix pattern.
4. **Snapshot verify-before-regen** (per `memory/feedback_snapshots_as_staleness_liability.md`) — if a snapshot fails after a structural fix, FIRST run without `-u` and verify diff is the intended change. Never blanket `-u`.
5. **RN alignItems:'center' child-collapse trap** (per `memory/feedback_rn_alignitems_center_collapse.md`) — when wrapping a primitive with `flex:1` children inside an ancestor with `alignItems:'center'`, the wrapper MUST set `alignSelf:'stretch'`. Add visual-style-presence regression tests.
6. **REWRITE means top-down per JSX, not surgical patch** — if existing `.tsx` has different element order or section set than `.jsx`, tear down + rebuild. DELETE stale pieces explicitly.
7. **JSX is the source of truth** — Bundle D editorial cards / Bundle C scoring widgets / any pre-JSX-redesign component is gone unless the JSX shows it.
8. **Test coverage gate is non-negotiable** — 80% on new code OR the lane doesn't ship. Idle time goes to test authoring.
9. **Peer-QA is honest** — if A1's REWRITE missed a JSX element, A4 sends it back. No rubber-stamping. The walk gate caught Bundle D / Bundle E S1 / Bundle E S2 because self-signoff drift was real.

## Risk + mitigation

| Risk | Mitigation |
|------|-----------|
| ResultsScreen REWRITE breaks scoring_v2 / personalization contracts | A2 prompt explicitly: "preserve scoring_v2 / personalization / SSE contracts; only rewrite presentation layer." A2 reads `app/services/scoring_service.py` + `response_builder.py` before touching the TSX. |
| Image pipeline doubles API costs | Tier cascade is piggyback-first (use existing extractors); only fires NEW Serper Images call when Tier 1.5 page-scrape returned no image. Budget breaker on `serper_image_calls_today`. |
| 4 parallel agents conflict on shared files | Lane boundaries are file-level: A1=Home+Profile+EditProfile, A2=Results+History, A3=`app/api/*.py` + `app/services/*.py`, A4=image rendering across A1/A2 files. A4's image-wiring touches A1/A2 files → A4 waits for A1/A2 merge, then opens a follow-up PR for image-only changes. |
| Peer-QA agent finds something but original agent disagrees | Dispatcher arbitrates via JSX source of truth. JSX wins. |
| Device walk reveals new surface gap not covered by 4 lanes | Add lane or extend existing lane scope. Don't defer to "Bundle E S4 polish" — defer rule from operating principles. |
| EAS build finishes before S3 ready | The build sits in App Store Connect, harmless. No tester invited until S3 OTA + device walk GREEN. |

## Execution sequence

1. Dispatcher writes this design doc + commits (this PR)
2. Dispatcher invokes `superpowers:writing-plans` to produce `docs/plans/2026-05-30-bundle-e-s3.md` (implementation plan with per-lane task lists)
3. Dispatcher spawns 4 Agent calls in ONE message (parallel start)
4. Each agent reports lane PR-ready → peer-QA hands off in ring order
5. Dispatcher merges all 4 PRs after peer-QA GREEN
6. Dispatcher fires OTA to preview channel
7. Ahmed device walk → either RED-cycle a lane or GREEN-all-clear
8. TestFlight invite opens

## Deliverables

- This design doc (committed)
- Implementation plan at `docs/plans/2026-05-30-bundle-e-s3.md` (written by writing-plans skill, committed)
- 4 lane PRs into main (via worktree isolation, merged sequentially after peer-QA)
- One post-merge OTA group ID published to preview channel
- SESSION_BUNDLES.md Bundle E S3 entry (post-walk, post-merge)

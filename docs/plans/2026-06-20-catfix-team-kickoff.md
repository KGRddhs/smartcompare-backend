# Catfix — New-Session Team Kickoff (ready-to-paste)

Paste the block below into a **fresh Claude Code session** (in the repo root) to dispatch the 4-Opus team.
Everything is pre-verified + plan-reviewed; the new session does NOT need to re-derive anything.

---

```
Dispatch a 4-Opus worktree team to execute the approved, plan-reviewed implementation plan:
docs/plans/2026-06-20-fragrance-category-allcat-implementation.md  (v2 — the executable plan)

Supporting (read first): docs/plans/2026-06-20-fragrance-category-allcat-design.md (design) and
docs/plans/2026-06-20-fragrance-category-fix-plan.md (verified line-level findings, workflow wf_01a4745e-9ac).
The plan was adversarially reviewed (wf_0a49790d-765) and revised to v2 — execute it AS WRITTEN.

GOAL: every two-box / camera comparison renders its TRUE category structure (a fragrance is a fragrance,
not 'other'/electronics), with honest ratings and correct Bahrain price sourcing. All backend, $0,
Serper-positive — EXCEPT the FE null-default (needs an EAS preview push).

EXECUTION MODEL (non-negotiable):
- 4 Opus agents only (no sonnet/haiku), in an isolated worktree, mode bypassPermissions:
  git worktree add -b feature/category-allcat-fix ../smartcompare-catfix main   (verify: git worktree list)
- Roles: be-core (WS A), be-render (WS B), test (WS C), fe (WS D) — see the plan's owner table.
- SHARED-FILE SERIALIZATION (prevents git-index race — this was the review's blocker):
  extraction_service.py + scoring_service.py belong to be-core until A1/A2/A2b/A5 are committed; be-render
  does AUDIT-ONLY (read) on them until released, then rebases before editing. The dispatcher serializes the
  two handoffs. (If you'd rather avoid serialization, run it solo/sequential — cheaper, also fine.)
- New test files have single owners (see the plan's test-ownership table) — no concurrent appends.
- Discipline: features 100% complete before disassembly; each member QAs another member's work and sends
  back subpar/missed work; idle members write red-green tests toward 80% in a file they own, or await QA.
- Dispatcher verifies every "complete" claim against the actual commit (git show), never the report.

DEFINITION OF DONE (gate against real commits): the plan's Definition-of-Done checklist, especially:
- the _fetch_product_data CAPTURE test green (sync AND stream) — products[i]["category"]=="fragrances"
  (this, NOT the fragrance-dims test, is the write-back proof);
- no derived/estimated rating shown as real anywhere (overview, reviews, verdict line1 AND line2,
  _dim_value, gpt_review_aggregate-at-source); real review_count preserved;
- Scrape.do meters real cost (0 on no-request paths); all 12 tuple sites updated; firecrawl untouched;
- coverage >=80% on new code; full free unit suite green; smoke20 vs
  54b603e8-4eab-41c9-a34d-a5e391446559 no regression (winner-rate EXPECTED flat — the eval uses the q=
  parser path this fix does NOT touch);
- FE: no silent 'electronics' default; selected_category omitted when null; npx tsc --noEmit clean;
- merge --no-ff to main, then: cd SmartCompareApp && eas update --branch preview; one cold prod
  nocache=true probe on a FRESH fragrance pair confirms the render.

BUDGET: nothing here adds Serper/Scrape.do credits (the category fix is Serper-positive). Reserve ONE cold
prod probe for D2; everything else is $0 unit/scoring tests. Do NOT include any deferred item (image-size,
/quick, URL-engine category, dead comparisons.category_used column, Scrape.do super-mode, paid Serper).
```

---

## Quick reference (if asked)

- **3 commits on main:** `2036c50` (v1 plan trilogy), `25877f2` (v2 review fixes). Plan is current at HEAD.
- **The keystone:** scoring/specs/sources read `products[i]["category"]` (scoring_service.py:1067), NOT
  `category_used` — the fix writes the resolved category back onto the product dicts before the
  `_fetch_product_data` gather. Pin with a capture test.
- **Two AI-rating leaks:** `derive_rating_from_scores` (projection guard) + `gpt_review_aggregate`
  (fix at source, set `rating_derived=True`). Verdict line2 needs the `_safe_rating` chokepoint.
- **Detect-first / chip-refines / no silent default;** deterministic classifier + bounded GPT-mini
  (uncertain + no-chip only).

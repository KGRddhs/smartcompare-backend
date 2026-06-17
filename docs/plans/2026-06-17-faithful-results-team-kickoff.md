# New-Session Kickoff — Dispatch the 4-Opus Team ("Faithful Results + Genuine-BH on Free Tier")

**Use:** open a fresh Claude Code session in this repo and paste the prompt block below. Phase 0 (discovery) is DONE in the prior session; three docs are committed to `main`. The new session is the **dispatcher** for a 4-Opus worktree team executing Phases 1-8.

**Committed context (HEAD `3ed1620` on main):**
- Design — `docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-design.md`
- Plan — `docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-plan.md`
- Findings — `docs/plans/2026-06-17-faithful-results-discovery-findings.md`

---

## ⬇️ READY-TO-PASTE PROMPT

```
You are the DISPATCHER for a 4-Opus worktree team executing a committed implementation plan for the Qaren/SmartCompare app. Phase 0 (discovery) is already DONE. Read these THREE docs FIRST, in order, before anything else:
1. docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-design.md
2. docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-plan.md
3. docs/plans/2026-06-17-faithful-results-discovery-findings.md   ← the Phase-0 findings; fills the plan's [per findings F-x] placeholders

Then execute Phases 1-7 with a 4-Opus team, and run Phase 8 (verify + deploy) yourself.

TEAM (TeamCreate, mode: bypassPermissions REQUIRED, all Opus — NO Sonnet/Haiku):
- Backend  — Phase 1 (sourcing + cache architecture), Phase 4 (verdict bugs), Phase 6 (fairness), Phase 3.2/3.3 (category payload completeness + dims)
- Frontend — Phase 2 (prune to design), Phase 3.1 (CategoryProfile component), Phase 5.2 (review FE)
- Test     — Phase 7 (eval B2 baseline + regression gate + A4 variant) + red-green tests to 80% for ALL new code
- Integration-QA — cross-checks every member's work + Phase 8 prep

RULES (Ahmed's, NON-NEGOTIABLE):
- Features must be 100% complete before disassembly.
- Every member QAs ANOTHER member's work before the team disassembles; subpar or missed work is SENT BACK.
- An idle member either writes red-green tests for the new feature to hit 80%, or waits for their QA to return.
- Work is DELEGATED, not hoarded.
- Teammates ACK every dispatcher ruling between tasks. Escalate any member idle >30min OR after 3 silent nudges → dispatcher takeover (verify "complete" claims against the actual commit via git show, never the report).

PRIORITY ORDER (highest-leverage first, per findings):
1. Phase 1 genuine-price + cache: long-TTL genuine BH prices (24h→7-30d), negative-cache structural dead-ends, warm-once-serve-long, cache-first before any render, fairness-correct cache keys, hit-rate observability. + F1.2 fragrance/haircare wrong-cheap-sample guard (Tobacco 28→~118, K18 4.5→~30+). + F1.3 supplements price gap + the 30s-cap empty verdict.
2. Phase 4 verdict bugs: F4.1 fragrance LONGEVITY contradiction (sub-score opposes prose+reviews; verdict_validation missed it), F4.2 EMPTY tradeoffs when winner sweeps (compute_tradeoff_pairs:1961-1962 → fall back to loser's best dim), F4.3 personalization NOT woven into main verdict text (Ahmed's "not clicking"), F4.4 partial-path emits empty comparison{} → emit deterministic-scoring verdict.
3. Phase 2 FE: remove HeroRings card not in design, F2.2 un-suppress runner-up caption (ResultsContent.tsx:297-316), lighten section chrome.
4. Phase 5 reviews: convert verbatim+cited → PARAPHRASED PRAISE (no citations, real-only ratings) per Ahmed.
5. Phase 3 category render (all 9): CategoryProfile block + F3.1 fashion specs asymmetry.
6. Phase 6 fairness: verify/extend from the prefetch JSONs (electronics honor-each already works).
7. Phase 7 eval: B2 smoke20 --persist baseline + regression gate + A4 cache-reading variant.

SOURCING CONSTRAINT (settled in Phase 0): FREE-tier. Firecrawl enhanced does NOT crack Cloudflare; Scrape.do super DOES but is $249/mo Business (free plan 401s). Free path = curl-extractable non-CF genuine sources + heavy cache. The genuine-share CEILING (luxury via $249 Scrape.do, full-catalog warming via paid Serper) is BUDGET-bound = Ahmed's subscription call, NOT the team's scope. The team builds the cache architecture + all engineering fixes. IMPORTANT — Ahmed will evaluate BETTER/PAID scrapers AFTER implementation, so build the heavy-render tier as a PLUGGABLE adapter: keep the firecrawl_service/scrapedo_service boundary clean + a single config-selected "heavy renderer" seam so a new vendor (Scrape.do Business super-proxy, ZenRows, Bright Data, etc.) drops in via config, NOT a rewrite. The cache + extraction layers stay scraper-AGNOSTIC (they cache/parse genuine prices regardless of which engine produced the HTML).

WORKTREES + OPS GOTCHAS (durable):
- git worktree add -b feature/<name> ../smartcompare-<name> main  (ABSOLUTE paths; verify via git worktree list before dispatch).
- FE worktree needs node_modules: junction the main tree's (mklink /J node_modules <main>\SmartCompareApp\node_modules) OR have the FE member work in the main tree (the prior sessions did FE in main tree for this reason).
- TWO app/ dirs — edit ROOT app/ only (backend/app/ is NOT deployed).
- Windows: pass encoding='utf-8' to open()/subprocess; the Bash tool cwd PERSISTS after a cd into SmartCompareApp.
- Trust ONLY `npx tsc --noEmit` for TS (LSP diagnostics on Windows are unreliable).
- Path-restricted commits in team work: git commit -m "msg" -- <paths>  (the -- is a path separator).
- STALE REDIS masks deploys — verify with a FRESH/different pair or ?nocache=true, never a re-run of the same query (prices 24h / specs+reviews 7d TTL).
- Free-unit tests: python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
- Prod API: https://web-production-58776.up.railway.app  (e.g. /api/v1/text/compare?q=...&nocache=true). Railway MCP/CLI may be invalid_grant → verify deploys via a prod API probe, not Railway tooling.
- EAS: cd SmartCompareApp && eas update --branch preview --message "..."  (two app relaunches to propagate; eas update is NOT interactive-only).
- COPY POLICY: no scary words (EN: couldn't/try again/Failed; AR: تعذر/فشل); "Top match" not "Winner". EN/AR i18n for ALL new copy. Ratings NEVER AI-generated.

OUT OF SCOPE: app icon / Logo Studio; legal-doc redraft; any paid-subscription decision (genuine-share ceiling).

DEPLOY + VERIFY (Phase 8, dispatcher): backend merge --no-ff → Railway auto-deploys ~90s → prod-smoke ?nocache=true per category (data populates, fairness correct, genuine-or-pending, runner-up shows, paraphrased reviews) → cd SmartCompareApp && eas update --branch preview → hand Ahmed the on-device checklist INCLUDING the authenticated re-run for personalization weaving (F4.3) + cohort_summary (F3.2) since those could not be verified anonymously.

Phase-0 discovery scratch (reference, gitignored): .qa-bias-rerun/_discovery/ — prod/*.json (9 category cold responses), headtohead.json, sourcing_extra.md.

Begin by reading the 3 docs, then confirm the worktree + team plan with me before spawning agents.
```

---

## Notes for Ahmed
- This is the "parallel session" handoff (writing-plans). The new session uses `superpowers:executing-plans` discipline implicitly via the dispatcher role.
- The genuine-share **ceiling** decision (pay for Scrape.do Business $249/mo and/or Serper Starter $50/mo) is yours and is separate from the team's engineering scope — flagged in the prompt.
- If the new session's team hits the same transient API rate-limit, it should stagger agent spawns (4 concurrent max) rather than fan out wide.

# Bundle B — S2 "Intelligence" Execution Plan (S2.0 dispatcher refinement)

> **Date:** 2026-06-11 · **Dispatcher:** Claude (main repo session) · **Team:** 5 Opus lanes in worktrees
> **Inputs (read these, in order):** `2026-06-10-bundle-b-s2-design-inputs.md` (the adversarially-verified evidence dossier — this plan cites it, never restates it) · `2026-06-10-bundle-b-s2-prep-notes.md` §0 binding table · `2026-06-10-bundle-b-s1-baseline.md` (anchor row) · `2026-06-10-bundle-b-f17-routing-evidence.md` · `docs/runbooks/qaren-eval.md` · `docs/runbooks/qaren-gold-set.md`
> **Baseline anchor:** eval_runs `4aee8e88-da97-41b3-974b-3e75c2c9c10e` — 21.0% weighted; price .455 / specs .708 / winner .360 / factual .770; p95 30.7s. Every merge gates against it (smoke20 regression, >2pp per-axis drop fails).

**The arithmetic that shapes this session (dossier §1):** winner .360→≥.60 needs 48 net flips. The 45-id pure-bias set yields +27–31 at realistic 60–70% conversion; the remainder must come from the 46 error rows (recovery ≈ +21 at graded rates) and/or the 37 compound fails. **I1/I2 and I5 are co-load-bearing — neither alone reaches the gate.** Standing KPI (Ahmed 2026-06-10): estimates and uncertainty are unacceptable as answers — estimate-share reduction is tracked per eval run.

---

## 0. Ahmed decision record (2026-06-11 S2 kickoff — binding)

| # | Decision | Ruling | Lands in |
|---|---|---|---|
| A | Dimension display 6→8 rows | **Raise to 8** | I3.4 |
| B | One-sided MISSING_SCORE dim-winner | **Attack missing data at the root**: "we don't want missing data — full search/detect/research so we are fully certain; no misleading and false certainty; more sources in Bahrain, more correct data." → BOTH suppress the misleading render AND fill the data | I3.5 (suppress) + I3.6 (Tier-3 fill + coverage metric) + I5.3–I5.5 (more Bahrain sources) |
| C | H2/H4 GCC claims from model prior knowledge | **Allow with guardrails** — qualitative only ("widely available in Bahrain", "GCC crowd-pleaser"); NO store counts, branch names, or unsourced numbers | I1.2 exemplars + I2.2 localization AP carry the guardrail text verbatim |
| D | Latency/scoring levers | **fan_out 15s→12s pre-authorized.** Everything else (reviews trim, order-neutrality, further candidates): *"try all possible methods and A/B test the best winners and review against the current improvement"* — adopt only measured winners (quality axes hold, wall improves, smoke20 green) | I5.7 · I4.4 lever A/Bs · I5.9 swap experiment |
| E | Exemplar contamination | **Synthetic-rewrite rule ratified** (kickoff message): exemplars are synthetic rewrites of the 45-id patterns (different brands, same structure) — never verbatim gold pairs. Exit winner reported full-set AND excluding template ids | I1.2 · G6 |
| F | Carrefour/Géant BH registry rows | Dossier default ratified: **verify-or-delete, never fabricate** | I5.3 |

Flags discipline: nothing flips in Railway without dispatcher + Ahmed at a gate. `ENABLE_SELF_CRITIQUE` stays OFF through S2 build; promotion decisions happen at G5/G6 on evidence.

---

## 1. Lane I1 — Few-shot exemplars + rotation (`feature/s2-i1-fewshot` · worktree `smartcompare-S2-I1`)

Owns exemplar CONTENT + the rotation pipeline. I2 owns the injection mechanism — agree the JSON contract in your first hour (task I1.1/I2.1 joint ACK in team channel).

- **I1.1 Contract with I2 (blocking, ~30 min):** ratify `data/verdict_exemplars.json` schema: `{category: {exemplars: [...], anti_patterns: [...]}}`, exemplar fields (`title`, `setup`, `verdict_json`, `teaches` = H-tag). Post the agreed schema to the team channel; both lanes ACK.
- **I1.2 Synthetic exemplar authoring (the core task):** per category ≤3 compact exemplars (150–250 tok each): one **H1** + one **H3** (the discriminator pair — teach WHEN value wins vs WHEN premium is licensed, never a direction) + one category-precise third — **H8** for skincare/makeup/appliances, **H2** for grocery/fragrances/makeup, **H4** for electronics (dossier §3 lists template ids: supp-013, make-016, groc-009, skin-018, skin-013, make-013, skin-009, other-019, groc-002, frag-016, make-011, elec-024, elec-018). Synthetic rewrites ONLY (Decision E). H2/H4 content obeys Decision C guardrails. Every exemplar: label "EXAMPLE — do not copy", exact verdict schema (`extraction_service.py:582-611`): winner_index 0/1, winner_reason <20 words with a number, `value_context`/`best_for` per-product dicts, pros 4–6 / cons 2–4 never empty, omit `personalized_insights`. Record each exemplar's source-pattern id in a `_provenance` block (for G6 ex-template reporting).
- **I1.3 Injection content tests:** with I2's loader merged, snapshot-test the assembled prompt per category: exemplars present, inside the static-per-category prefix (prompt-cache discipline), token count asserted ≤ budget (≈700 exemplars + ~100 APs), forbidden-words audit green (`tests/test_comparison_quality_detector.py:180` pattern — no "estimated", no scary vocab).
- **I1.4 Weekly rotation cron:** `scripts/cron_few_shot_rotation.py` (pattern: `cron_reengagement.py`) — top-decile `comparison_feedback` (useful=true + winner_correct=true, migration 027 columns) → regenerate exemplar file; cold-start = the I1.2 synthetic seed; privacy: product names + verdict text only. Cron NOT registered on Railway this session (same fail-closed posture as eval cron) — script + tests only.
- **I1.5 Token/cost audit:** measure real prompt tokens before/after on 3 categories; assert +≤$0.002/call vs dossier §3 budget; record in lane report.
- **I1.6 Lane QA (dispatcher GO required, announce before running):** 45-id pure-bias subset re-run (concurrency 1, nocache) — target ≥60% flipped. This is mid-session leading indicator (a), not the exit measure.

**Exit:** exemplars live behind merged mechanism · 45-id flip ≥60% · token budget held · contamination rule provably honored (provenance block).

## 2. Lane I2 — Prompt mechanism + anti-patterns + climate + Arabic sources (`feature/s2-i2-prompt-mech` · worktree `smartcompare-S2-I2`)

Owns the injection MECHANISM + anti-pattern/climate/Source.usage work. Builds on I5.10's unified prompt path — coordinate: I5.10 merges first (G1); rebase after.

- **I2.1 Loader + injection mechanism:** `app/services/verdict_exemplar_loader.py` mirroring `pain_workflow_loader.py:54-82` (`@lru_cache` + `reset_cache()`; autouse fixture for test isolation — the F2.5 lesson). `build_exemplar_block(category)` returns exemplars+APs text. Inject in `build_verdict_prompt` after `build_personality_prompt` (`extraction_service.py:1178`; `:1132`), BEFORE pain-workflow (`:1184`) — inside the static-per-category prefix (OpenAI prompt-cache discipline, D2). Ship with an EMPTY-but-valid exemplar file so the mechanism merges independently of I1 content.
- **I2.2 Global anti-patterns:** extend `COMPARISON_SYSTEM` RULES (`extraction_service.py:613-621`, `:614` precedent): the H1/H3 discriminator AP ("spec-sheet edge at price parity → prefer lower Bahrain price on value-per-dinar UNLESS durability/service-network/update-guarantee licenses the premium") + the localization directive ("grade as a Bahrain buyer, not a global spec sheet") carrying Decision C's qualitative-only guardrail sentence verbatim.
- **I2.3 Per-category anti-patterns:** in the exemplar JSON beside I1's exemplars (H2 "global prestige outranks GCC market reality", H4 "identical on paper = identical in Bahrain", H8 "climate-neutral verdicts in a 45° market", H6 "newer spec sheet beats canonical benchmark") — phrased as named-failure-mode + one-line counter-rule (dossier §3).
- **I2.4 Climate flags:** `heat_stability` extraction keys for makeup/skincare/fragrances in `CATEGORY_SPEC_SCHEMAS` + verdict-prompt awareness. **NO new scoring dimensions** (deterministic scoring untouched — design §4 hard rule).
- **I2.5 `Source.usage` + Arabic sources:** add `usage: "price"|"review"|"both"` to `Source` dataclass, default `"price"` (zero behavior change — pin with test); `_harvest_candidate_urls` filters `usage in ("price","both")` (price-harvest invariants test unchanged); register sayidaty.net / khaleejtimes.com (AR) / gulfnews.com (AR) as `usage="review"`, gcc weight, review categories (fashion/makeup/skincare/haircare/fragrances); a minimal review-content consultation path consumes `usage in ("review","both")` inside the existing reviews race (wait_for-capped, None on miss, never critical-path).
- **I2.6 Audit compliance:** all injected text passes the forbidden-words audit; extend the audit test to cover the exemplar/AP assembly path itself.

**Exit:** mechanism merged with empty file (G2) · APs live · climate keys extracting · Arabic sources consulted by review path with price-harvest invariants intact.

## 3. Lane I3 — Self-critique + missing-data honesty (`feature/s2-i3-critique` · worktree `smartcompare-S2-I3`)

Owns B.3 self-critique + the Decision A/B scoring items (one coherent epic: "verdict quality + no false certainty").

- **I3.1 Critique service:** gpt-4o-mini pass scoring the verdict on bias / vagueness / hedging / missing-citation / pain-workflow-alignment (0–10); any axis <7 → **ONE** regeneration (hard cap). `ENABLE_SELF_CRITIQUE` default OFF in code. Critique failure → serve original verdict, never blocks.
- **I3.2 Persistence:** writes to `verdict_critiques` (migration 030, live) via `_fire_and_forget(coro, label)` — never bare create_task.
- **I3.3 Cost + latency instrumentation:** per-call cost tracked into `self.total_cost` (≤$0.002/cmp gate); wall delta measured under `DEBUG_STAGE_TIMINGS`; p95-inside-cap evidence required before any promotion talk (G5).
- **I3.4 Decision A — 8 dimension rows:** `build_dimensions_v2` cap 6→8 + the 2 test updates (`tests/test_dimensions_builder.py:415`, `tests/test_scoring_v2_models.py:289`). Electronics gains `ecosystem`/`futureproof` rows. FE already supports (HERO_CAP=4 + expander) — backend-only.
- **I3.5 Decision B (render): suppress one-sided MISSING wins:** plumb per-side `was_missing` into `_dim_winner`; winner=None when exactly one side is MISSING_SCORE. Pin both branches (one-sided vs both-sided missing) in tests.
- **I3.6 Decision B (root): missing-data fill + measurement:** implement **A.4.8 Tier-3 batched GPT-4o spec synthesis** as the final fallback when Tier 2 is also blank (bounded: single batched call, inside existing wait_for budget; flag-gated `ENABLE_TIER3_SPEC_SYNTHESIS` default OFF until A/B'd); add a **missing-dim coverage metric** to eval metadata (count of MISSING_SCORE cells per run) so Decision B's "fully certain, no missing data" directive is measured, not asserted. Diagnose supp-010 + skin-012 (the two specs_score=0.0 sole-failures, dossier §1 edge) — root-cause and fix or document.

> **I3.6 ADDENDUM (2026-06-11 dispatcher ruling, code-verified):** A.4.8 found ALREADY LIVE + unconditional (`tier3_synthesize_non_negotiables` ssc:253→:2343, `extract_specs_synthesized` openai_service:298 — shipped pre-S2; the v1.1-backlog "unimplemented" note was stale). Plan item marked PRE-SATISFIED; **NO retroactive flag** — default-OFF gating of live prod behavior would silently regress Decision B's direction. supp-010/skin-012 root cause: `active_ingredient` is PREFERRED-not-NON_NEGOTIABLE for supplements/skincare (extraction_service.py:213,218), so Tier-2/3 fallbacks never guarantee a fill attempt. **RULED: promote `active_ingredient` to NON_NEGOTIABLE for supplements + skincare only**, pinned with fill-attempt tests + DELIBERATE weird-classifier coverage-ratio test updates.

**Exit:** critique shippable-but-OFF with cost/latency evidence · 8 rows live · one-sided MISSING suppressed · Tier-3 fill confirmed live + active_ingredient promoted · missing-dim metric in eval runs.

## 4. Lane I4 — Shadow experiments + A/B harness (`feature/s2-i4-shadow` · worktree `smartcompare-S2-I4`)

Zero prod-path changes. Scripts + harness only. This lane is Ahmed's Decision D instrument: *"try all possible methods and A/B test the best winners."*

- **I4.1 Shadow replay harness:** `scripts/shadow_experiments.py` — re-grade alternative verdict configurations against gold queries. **Serper discipline:** build verdict-stage inputs from captured/cached product data (L2 `product_*` tables + `.qa-bias-rerun/baseline_s1_per_query.jsonl`), NOT full pipeline re-runs; full replays need dispatcher GO with credit math.
- **I4.2 o3-mini verdict arm:** o3-mini (org-confirmed) vs gpt-4o baseline on the same inputs; graded by eval_runner grading functions; promotion bar = quality-up AND cost-neutral-or-better.
- **I4.3 Multi-agent arm:** 3× mini analysts (spec/price/review) + 4o editor; promotion bar ≥5% lift. **Envelope rule (design §4): multi-agent and self-critique cannot BOTH promote** — at most one inside $0.015, or the editor absorbs critique.
- **I4.4 Lever A/B arms (Decision D):** reviews trim (`[:4000]→[:2500]` + `max_tokens 1000→600`) — measure axis deltas + wall delta on a fixed subset; any further candidate methods the team proposes get the same treatment: current-vs-candidate, measured, reviewed at a gate before adoption.
- **I4.5 Promotion evidence report:** one doc (`docs/plans/2026-06-XX-s2-shadow-results.md`) with per-arm quality/cost/latency table → feeds G5 promotion decisions.

**Exit:** evidence report with measured verdicts on o3-mini / multi-agent / reviews-trim / any extra arms — decisions made on numbers, not vibes.

## 5. Lane I5 — "Yield & Wall" (`feature/s2-i5-yield-wall` · worktree `smartcompare-S2-I5`)

The error-recovery + scrape-yield + latency lane — co-load-bearing for the winner gate. Work is ORDERED; ship in two merge waves.

**Wave A (merge at G1, target day 1–2):**
- **I5.0 Serper ceiling reconciliation + 80%-burn alert** (FIRST — protects every measurement this session): reconcile `api_budget_service` serper ceiling with the REAL account balance for key `3d304e...`; Sentry/log alert at 80% burn; drill-test the alert fires (binding-table exit criterion). Use post-B.0 per-query credit math (escalating cold ≈ 10–15 credits).
- **I5.1 Observability pair (~10 min + flag):** per-domain `tier15:source_hits:{domain}` line in `/admin/costs` `tier1_5_hit_rate` block (counters already write); probe **price-only cache-bust flag** (read-through scoped to price; specs/reviews stay warm) for deterministic routing evidence — document in eval runbook.
- **I5.10 Prod/test verdict-prompt unification:** prod `generate_comparison` (`extraction_service.py:1152-1321`) never injects `_WEIRD_VERDICT_INSTRUCTION`; test-only `build_verdict_prompt` does. **Unify prod onto `build_verdict_prompt`** so audits grep what production runs. I2's injection builds on this — it merges FIRST. Pin with a test asserting prod path == build_verdict_prompt output.
- **I5.2 Confirm http_400 = cap-cut via Railway logs** (all 39 carry wall_over_cap=true) BEFORE optimizing — evidence comment in lane report. If the mechanism differs, STOP and report to dispatcher before any lever work.

**Wave B (merge at G4 — hottest path, last before exit):**
- **I5.3 Registry dead-domain replacement (Decision F):** `lulu.com.bh`→`luluhypermarket.com`, `sharafdg.com.bh`→`bahrain.sharafdg.com`, `extra.com.bh`→`extra.com`; carrefour/géant BH **verify-or-delete** (carrefour.com.bh also dead — never fabricate); verify behbehani/eros/jumbo rows (`source_router.py:28-32,40-42`). Every replacement must be liveness-verified the day it's committed.
- **I5.4 Discovery window fix:** get live domains into the queried window — reorder verified-first AND/OR `limit=4`→8 (same single Serper call, longer OR-chain) at `source_router.py:159-161` / call site ssc:2612. shopalmoayyed.com must be queryable for electronics/appliances.
- **I5.5 Category-aware authorized/gcc discovery:** stop sending farfetch/ounass strings for an AC — build authorized/gcc discovery from registry tiers per category (ssc:2605-2606).
- **I5.6 S2-safe latency stack (zero quality risk, −1 to −2.5s mean):** `_get_price` concurrent with unified search (ssc:2051); behavior/demographics fetch alongside product gather (:1347/:1761); cap the uncapped Phase-2 rating race at ~4s (:2282/:2253).
- **I5.7 fan_out 15s→12s + price race 18s→~14–15s (PRE-AUTHORIZED, Decision D):** ssc:2673 / :2088. Escalation TRIGGERING untouched — never blind the instrument.
- **I5.8 Parser hardening (defensive):** list-valued `@type`; `AggregateOffer.lowPrice` (`price_service.py:685,693,716`).
- **I5.9 Position-bias 20-swap experiment:** re-run ~20 index-1-expected winner-fails with product order swapped (concurrency 1, announce, dispatcher GO). If winners follow position → implement order-neutrality in scoring tie-breaks (Decision D: adopt-if-A/B-wins, smoke20-gated; coordinate with I3 on scoring_service paths). Worth up to ~15 flips.
- **I5.11 Registry liveness gate:** `scripts/verify_source_registry.py` (HEAD-resolve all rows) + `live_unit` test — prevents dead-domain recurrence.
- **I5.12 Re-measures:** supplements pair supp-002/supp-003 + groc-001 + elec-010 post-levers (concurrency 1); error-set size check (46 → target <10).

**Exit:** electronics tier1_5 hit_rate >0 · elec-013/014/015-class priced `source_method != estimated` · p95 <30s · error rows <10 · alert drill green · per-domain dashboard live.

---

## 6. Cross-lane dependencies + merge order

1. **G1 = I5 Wave A** (unification + budget alert + observability) — everything prompt-side rebases on it.
2. **G2 = I2** (mechanism w/ empty exemplar file + APs + climate + Source.usage).
3. **G3 = I1** (exemplar content + rotation cron) → then I1.6 45-id indicator.
4. **G4 = I3, then I4 scripts, then I5 Wave B** (hottest path last — S1's F1-last rule), each with its own smoke20.
5. **G5 = promotion review** (I4 evidence: o3-mini / multi-agent / reviews-trim / critique — at most ONE cost-adding promotion; Ahmed pinged with the recommendation).
6. **G6 = S2 exit re-measure** (dossier §7): full gold-200, concurrency 1, nocache, Serper balance pre-checked (~600–1,000 credits; I5.0 alert armed); new eval_runs row vs `4aee8e88` axis-by-axis + per-category + estimate-share + missing-dim metric.

Conflict map: I1/I2 share `data/verdict_exemplars.json` (schema contract I1.1) · I2/I5.10 share `extraction_service.py` verdict path (I5.10 merges first) · I3/I5.9 may both touch `scoring_service.py` (coordinate via dispatcher before either edits tie-breaks) · I5 owns `structured_comparison_service.py` + `source_router.py` exclusively this session.

## 7. Gates protocol (every gate, no exceptions)

1. Lane announces merge-ready with commit SHA + test evidence (free-tier suite green locally; `python -m py_compile` on touched files).
2. Dispatcher verifies the claim against the actual commits (`git show` — never the report).
3. **Ultracode verification workflow** on the lane diff: parallel reviewers (correctness / regression-risk / convention-adherence / plan-fidelity) + adversarial verify of findings + completeness critic vs this plan's lane exit criteria + the §0 binding table.
4. Merge `--no-ff` to main, push (Railway ~90s).
5. **smoke20 regression vs `4aee8e88`** (`python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e`, concurrency 1) + prod curl smoke (`/health` + one full compare + SSE happy-path — the L3-assembly lesson).
6. Sentry check (`is:unresolved`) + `/admin/costs` Serper canary.

## 8. Comms contract (S1 discipline PLUS — binding from session start)

- **ACK-every-ruling:** check inbox between EVERY task; ACK dispatcher rulings BEFORE proceeding. A close-out that re-asks an answered question = the diagnostic tell.
- **Announce long runs** ("suite going, ~10 min") before going quiet; measurement runs ALWAYS `--concurrency 1`.
- Path-restricted commits (`git commit -m "msg" -- <paths>`); no-stash; push-per-commit; TDD per task; free-tier tests stay green; `encoding='utf-8'` on every subprocess/open (Windows cp1252 trap).
- Serper liveness check = `GET /api/v1/text/prices/<product>`, NEVER a full compare. No full-200 or subset eval runs without dispatcher GO.
- Never blind the instrument (no suppressing escalation to make walls fit). No Railway env/flag changes from lanes — dispatcher only.
- Dispatcher: fetch-before-ruling on any destructive call; verify contested "complete" via `git show`; 30-min/3-nudge stall rule → takeover or replacement.
- **LANE_STATE.md (Ahmed ruling 2026-06-11):** each lane maintains an UNTRACKED `LANE_STATE.md` at its worktree root — sections: Done (task ids + commit SHAs) / In-flight / Next / Blockers+questions / Last-updated (UTC). Refresh it (a) after every completed plan-task, (b) before announcing a long run, (c) when blocked. Never committed (path-restricted commits keep it out). Purpose: instant stall diagnosis (content+mtime beats WIP-mtime archaeology) and zero-cost handoff to a takeover/replacement agent — the S1 stall lesson made structural.

## 9. Budget plan

- **Serper:** smoke20 ≈ 60–100 credits/run × ~6 gates + indicators (45-id ≈ 300–500; 20-swap ≈ 100–200; supplements-22 ≈ 150) + full-200 (600–1,000) → **expect 1 key rotation mid-week**; playbook in CLAUDE.md (Railway env + local `.env` + worktree `.env` copies in the same pass; liveness via prices endpoint). I5.0's alert is the tripwire.
- **OpenAI:** exemplar prefill +≤$0.002/call (Decision E budget); I3 critique ≤$0.002 gated; I4 shadow arms are offline/batched — trivial spend; o3-mini per-arm runs logged in the evidence report.
- **Envelope:** blended ≤$0.015 at promotion time — the either-or rule is arithmetic, not preference.

## 10. S2 exit checklist (G6)

- [ ] Full gold-200 re-run recorded as new eval_runs row (concurrency 1, nocache, same grader)
- [ ] **winner ≥0.60** — full-set AND excluding exemplar-template ids (Decision E)
- [ ] electronics tier1_5 hit_rate >0; elec-013/014/015-class priced `source_method != estimated`
- [ ] p95 <30s; persistent-slow four complete; error rows 46→<10
- [ ] factual →~1.0 (any genuine factual fail = NEW regression — zero exist today); graded specs mean holds ~0.92
- [ ] estimate-share + missing-dim coverage reported in run metadata (the KPI dials)
- [ ] smoke20 green at every merge along the way (no axis >2pp drop)
- [ ] Sentry zero new unresolved; `/admin/costs` canary clean during the run
- [ ] Promotion decisions documented (I3/I4 either-or; reviews-trim; order-neutrality)
- [ ] SESSION_BUNDLES.md S2 entry + CLAUDE.md Active-runtime + memory updates; worktrees reaped; team disassembled
- [ ] **Ahmed reminder discharged:** Reddit OAuth app + YouTube Data API key created (~10 min — unblocks S3)

Missed exit criteria carry into S3 scope explicitly (binding table rule) — nothing silently drops.

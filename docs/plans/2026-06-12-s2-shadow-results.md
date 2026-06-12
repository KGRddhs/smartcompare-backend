# Bundle B S2 — Lane I4 Shadow Experiment Results (I4.5)

> **Owner:** I4-shadow · **Date:** 2026-06-11 · **Feeds:** G5 promotion review (plan §6) + I1/I2 few-shot scoping.
> **Harness:** `scripts/shadow_experiments.py` (54+ unit tests, mocked OpenAI). **Grader:** the eval_runner gold graders, imported not forked — a shadow "winner flip" means exactly what the gold eval means.
> **Baseline anchor:** eval_runs `4aee8e88` (S1, 21.0% weighted; winner axis .360).
> **Spend:** OpenAI only (~$2.30 across the four bias45 arms). **Zero Serper** — every verdict input was reconstructed from the L2 `product_*` tables the S1 baseline run wrote on 2026-06-10.

---

## 0. TL;DR for the G5 review

**No reasoning-architecture arm earns promotion.** All four arms land within ±1 winner-flip of each other on the 45-id pure-bias set (19–21 of 45). o3-mini matches gpt-4o on quality but is the same cost and 68% slower; the multi-agent split adds 1 flip (~2%, far under the ≥5% bar) at +$0.0019/call and +1.5s; the reviews-trim lever has no verdict-stage effect. **Recommendation: keep gpt-4o as the verdict model; promote none of o3-mini / multi-agent at the verdict stage. The one cost-adding promotion slot under $0.015 stays open for I3 self-critique** (decided on I3's own evidence at G5).

**The load-bearing finding is not in the rates — it's in the agreement.** Re-running the *current* gpt-4o verdict (the control arm) on the same inputs already flips **20 of 45** pure-bias failures to correct. Cross-arm agreement decomposes the 45 into:

| bucket | n | meaning |
|---|---|---|
| all 4 arms CORRECT | 19 | **variance failures** — the baseline got these wrong on a one-shot at T=0.2; any reasonable verdict config gets them right. They flip "for free" on a re-run. |
| all 4 arms WRONG | 24 | **structural bias** — every model + architecture picks the same wrong winner. This is the real I1/I2 few-shot target. |
| split | 2 | true run-to-run noise (groc-002, groc-023). |

**Consequence for the session:** the 45-id few-shot indicator (I1.6, target ≥60% flip) will over-credit any intervention, because ~19/45 flip regardless of what I1/I2 ship. Read the I1/I2 indicator against the **24 structural ids**, not the full 45 — and report the few-shot exit BOTH ways (this is already the Decision-E "exclude template ids" discipline, sharpened by data). See §4.

**The cheapest win in the session — temperature=0 (measured, §3a).** Acting on the variance finding, the **T=0 greedy-decode arm recovers the variance bucket completely: 18/18 of the completed variance ids flip to correct, 0/22 structural** (same model, same prompt, same inputs, **same cost + same latency** as the prod T=0.2 verdict). Flipping the production verdict call from `temperature=0.2` to `0.0` recovers ~19 of the 48 net winner-flips the gate needs, for **$0** — independent of, and complementary to, the few-shot work on the 24 structural ids. **Recommendation: adopt T=0 on the verdict; skip best-of-3** (3× cost can't beat T=0 on the only bucket either touches). The structural-24 stay the I1/I2 target.

---

## 1. Per-arm results (bias45, n=45, concurrency 1, retry-resilient)

All arms graded winner + factual from their own verdict; price + specs inherited from the S1 baseline grade (a verdict swap cannot move the extraction-set axes — they are set by the pipeline, which the harness does not re-run). factual = 1.000 on every arm (zero forbidden-fact emissions; the S1 factual gap was 100% error rows, which this harness excludes by construction — no verdict ran on them).

| arm | winner rate | net flips | factual | mean $/call | mean verdict ms | p95 ms | promotion bar | verdict |
|---|---|---|---|---|---|---|---|---|
| **baseline_4o** (control) | 0.444 | +20 | 1.000 | $0.01225 | 6218 | 8547 | control (gpt-4o, prod model) | — |
| **o3_mini** | 0.444 | +20 | 1.000 | $0.01254 | 10412 | 13015 | quality-up AND cost ≤ baseline | **REJECT** — no quality gain; +$0.0003 (not cheaper); +4.2s mean |
| **reviews_trim** | 0.422 | +19 | 1.000 | $0.01231 | 6130 | 8844 | winner+factual hold AND latency down | **NO VERDICT-STAGE BENEFIT** — −1 flip (noise); no latency win at the verdict call |
| **multiagent** | 0.467 | +21 | 1.000 | $0.01413 | 7733 | 10328 | ≥5% winner lift | **REJECT** — +1 flip ≈ +2.2% (< 5%); +$0.0019/call; +1.5s |

Cost note: all per-call costs are derived from **metered** token counts × published per-1M rates (gpt-4o $2.50/$10.00, gpt-4o-mini $0.15/$0.60, o3-mini $1.10/$4.40). Multi-agent prices each of its 4 legs (3× mini analysts + 4o editor) at its own model rate. Token counts are in the per-query JSON so the dollar figures are reconstructible if a rate changes.

### Why o3-mini is not cost-neutral
o3-mini's per-1M output rate ($4.40) is below gpt-4o's ($10.00), but it is a **reasoning model**: it bills reasoning tokens as completion tokens, and emits far more of them. Net per-call cost came out ~equal to gpt-4o ($0.01254 vs $0.01225) while taking 68% longer. The promotion bar is "quality-up AND cost-neutral-or-better" — it misses on quality (flat) and is not better on cost or latency.

### Why reviews-trim shows nothing here
Trimming the review context ([:2500] chars) + `max_tokens 600` does not change which product wins on value — the winner is driven by specs/price/scoring, which the trim leaves intact. The latency identical-within-noise because the verdict completion is small either way. **This measures the VERDICT-STAGE effect only.** The pipeline-wide −1–2s wall that the reviews-trim lever targets comes from the UPSTREAM `extract_reviews` change (`max_tokens 1000→600` + `search_context [:4000]→[:2500]`), which **Lane I5 owns** — that is a real candidate, just not measurable from a verdict-only harness. Flagged so G5 doesn't conflate the two.

---

## 2. Promotion recommendations (the G5 decision input)

1. **Verdict model: stay on gpt-4o.** o3-mini buys nothing and costs latency.
2. **Multi-agent: do not promote.** +2% is inside run-to-run noise; it consumes ~$0.0019 of the $0.015 envelope for no defensible lift.
3. **Envelope slot:** with both verdict-stage cost-adders rejected, the single promotion slot under $0.015 is **free for I3 self-critique** — decided at G5 on I3's own cost/latency/lift evidence (the envelope either-or is moot because neither I4 cost-adder qualified).
4. **Reviews-trim:** evaluate as an **I5 upstream latency lever**, not a verdict arm. Its verdict-stage quality cost is nil (winner/factual hold), so if I5's pipeline measurement shows the −1–2s wall, it is safe to adopt on quality grounds. This harness clears the quality-risk question; I5 owns the latency measurement.

---

## 3. The real signal: variance vs structural bias (per-id agreement)

Cross-arm winner agreement on all 45 ids (T = picked gold winner, . = wrong):

```
                base o3   trim multi | #correct
ALL-WRONG (structural, n=24):
  elec-012 elec-018 elec-024 fash-006 fash-008 fash-011 fash-013 fash-014
  frag-010 frag-011 frag-014 frag-018 groc-004 groc-011 groc-014 make-011
  make-014 other-009 other-010 other-012 other-019 skin-009 skin-013 supp-020
ALL-CORRECT (variance, n=19):
  elec-033 fash-009 fash-016 frag-007 frag-016 groc-009 hair-001 hair-014
  hair-021 make-003 make-009 make-013 make-016 other-011 skin-005 skin-010
  skin-015 skin-018 supp-013
SPLIT (noise, n=2): groc-002 groc-023
```

**Dossier template-id cross-check** (the ids I1/I2 will synthesize exemplars from):

| id | H-tag | bucket |
|---|---|---|
| supp-013, make-016, groc-009, skin-018 | H1 value-per-dinar | **all variance** — gpt-4o already makes the H1 call ~half the time; it's noisy, not broken |
| elec-024, elec-018 | H4 local presence/service | **both structural** — the engine cannot infer Bahrain consumables/service advantage from a spec sheet |
| skin-009, other-019 | H8 Gulf climate | structural |
| make-013 | H8 | variance |
| skin-013 | H8 | structural |
| groc-002, make-011 | H2 GCC brand resonance | structural |
| frag-016 | H2 | variance |

**Reading:** the bias themes split by how data-bound they are. **H1 (value-per-dinar) is mostly variance** — the information to make the call is already in the prompt (specs + price + scores), the model just doesn't apply it consistently; few-shots will *stabilize* it but the 45-id indicator will over-credit them. **H4/H2 (local presence / GCC resonance) are structural** — and per the dossier's own §5 honesty, these have *no data layer*: a few-shot can teach the reasoning move ("a Bahrain buyer weights service-network / local adoption"), but the underlying facts ride GPT prior knowledge (Decision C guardrails apply — qualitative only, no fabricated store counts). **H8 (climate) is mixed.**

---

## 3a. Variance-reduction arms (dispatcher orders) — T=0 + best-of-3

The §3 agreement finding predicted a cheap lever: if ~19/45 failures are sampling variance at the production T=0.2, greedy decoding should recover them at zero cost. The dispatcher ordered two arms to test it, reported split by the structural-24 / variance-19 buckets.

**T=0 arm (`temp0`) — gpt-4o at temperature=0, identical prompt + inputs + cost + call-count to `baseline_4o`:**

| bucket | completed | winner-correct | rate |
|---|---|---|---|
| **variance** | 18 | 18 | **1.000** |
| **structural** | 22 | 0 | **0.000** |

(42/45 completed; 3 ids — other-011 variance, other-012 + other-019 structural — errored on an OpenAI **quota** depletion mid-run, not on quality. The split is decisive without them: T=0 recovered *every completed variance id* and *zero* structural ids.)

**Read:** T=0 is a **complete, free fix for the variance bucket** and does nothing for the structural bucket — exactly the split the agreement analysis predicted. Same model, same prompt, same per-call cost ($0.0124), same latency (6.0s mean) as the prod verdict. The 24 structural failures remain the I1/I2 few-shot target; the ~19 variance failures are recoverable today by one config change.

**best-of-3 arm (`best_of_3`) — NOT RUN (OpenAI quota depleted mid-session).** It is also **moot for the promotion decision**: it is the same model + prompt at 3× the cost, so (a) it cannot beat T=0's 1.000 on the variance bucket — the only bucket either touches — and (b) it cannot move the structural bucket (same reasoning, just sampled thrice). Under the $0.015 envelope, a 3×-cost arm that can't beat a 1×-cost arm on the same axis is a clear reject. Will run for completeness if dispatcher wants the number once quota is restored; recommendation stands without it.

**Promotion recommendation (verdict variance):** **adopt `temperature=0` on the verdict call** (`generate_comparison` `temperature=0.2 → 0.0`) — $0, one line, recovers the variance bucket; **skip best-of-3.** Smoke20-gate the swap when Serper is restored (Decision D: adopt measured winners that hold smoke20). Hand-off owner: whoever owns `extraction_service.generate_comparison` in the prod-swap (I5.10 unifies that path; coordinate there).

---

## 4. Recommendations to I1/I2 (few-shot lanes) and G6

1. **Score the I1.6 45-id indicator against the 24 structural ids, not the full 45.** ~19 of 45 flip on any re-run; including them inflates apparent few-shot lift and risks a false ≥60% pass. Report the indicator BOTH ways (full-45 and structural-24) — this is the Decision-E "exclude template ids" rule made precise: the contamination isn't only the template ids, it's the whole variance bucket.
2. **Prioritize H4/H2/H8 exemplars over H1 for net new flips.** H1 ids mostly self-correct; the structural wins are concentrated in local-presence / GCC-resonance / climate reasoning. The H1 discriminator pair is still worth teaching (it stabilizes the noisy half and guards the H3 mirror), but the *incremental* flips come from the structural themes.
3. **A variance-reduction lever, now MEASURED (§3a): set the verdict to temperature=0.** The control runs at the production T=0.2; ~19/45 failures are sampling variance at that temperature. The T=0 arm recovered the variance bucket completely (18/18 completed, 0/22 structural) at zero added cost or latency. **This is complementary to few-shots, not competing** — T=0 takes the ~19 variance ids, I1/I2 few-shots take the 24 structural. Adopt both. (Prod swap is one line in `generate_comparison`; owner is the verdict-path lane, smoke20-gated post-Serper.)
4. **G6 expectation-setting:** of the 45-id "+48 net flips needed" arithmetic in the dossier, ~19 are already achievable by re-run/temperature alone, and ~24 need genuine reasoning help (few-shots + the localization directive). The full winner-gate math (dossier §1: I1/I2 + I5 error-recovery co-load-bearing) is unchanged — but the I1/I2 contribution should be modeled as "stabilize ~19 variance + win some fraction of 24 structural," not "+27–31 from the 45."

---

## 5. Methodology + honesty caveats

**Input reconstruction (zero Serper).** The S1 baseline (eval_runs `4aee8e88`, `?nocache=true`, 2026-06-10) skips the L2 cache *reads* but its *writes* still fire: after fresh extraction the orchestrator unconditionally calls `save_specs` / `save_price` / `save_reviews` (`structured_comparison_service.py:2466-69` etc). So the specs/prices/reviews the baseline verdicts saw are in the L2 `product_*` tables, keyed by brand+name. The harness joins them (brand+name, with a cross-category fallback for parser re-categorization), assembles the `product_data[i]` dicts, and computes `scores_summary` with the REAL deterministic `scoring_service` (offline, $0). Each arm then re-runs only the verdict LLM call.

**Coverage — explicit JOIN accounting (dispatcher directive 1).** The verdict inputs are reconstructed by a **brand+name token JOIN** of the gold query's two product phrases against the L2 rows. Coverage:

| set | http-200 graded | matched | coverage | unmatched ids |
|---|---|---|---|---|
| bias45 (pure winner-bias) | 45 | **45** | 100% | — |
| graded200 (all http-200) | 154 | **154** | 100% | — |

**No silent drops.** Every miss is reported by the harness (`prepare --skipped-out` writes id + query + which side(s) failed + the matched-flags). The JOIN is variant-tolerant by construction (token-subsequence either direction handles "iPhone 15" vs "Apple iPhone 15"; a cross-category fallback handles parser re-categorization). One abbreviation case surfaced and was fixed, not dropped:
- **elec-006 "PS5 vs Xbox Series X":** the gold phrase "PS5" shares ZERO tokens with the L2 row "Sony PlayStation 5" — token overlap failed *honestly* (reported as `matched_a: false`). Added a small audited alias map (`_ALIAS_EXPANSIONS`: PS5→PlayStation 5, +PS4, defensive only) — PS5 is the **only** zero-token-overlap phrase in the entire gold-200 (verified by scanning all 400 product phrases against the 522-row L2 dump). With the alias, elec-006 matches and graded200 is 154/154.

Coverage is **well above the ~130 floor** the dispatcher set for paid arms — no flag needed. The 46 S1 error rows (39 http_400 + 6 http_502 + 1 timeout) have NO reconstructable verdict input — no verdict ran on them — so they are **out of this lane's scope** (Lane I5's recovery domain). Every number in this report is over the http-200 graded population only.

bias45 arms are run (§1); graded200 arms prepared (154/154) but not yet arm-run — see §6.

**What this harness can and cannot measure honestly:**
- **CAN:** winner-axis and factual-axis deltas across verdict configs, real per-call cost (metered tokens), verdict-call latency.
- **CANNOT:** price/specs axis movement (verdict doesn't touch them — held at baseline); end-to-end pipeline wall (only the verdict call is timed, not specs/price/reviews fetch); anything about the 46 error rows.
- **Grading parity:** the same `grade_winner` / `grade_factual` / `weighted_pass_score` functions the gold eval uses, imported from `scripts/eval_runner.py`. No bespoke grader.
- **Control discipline:** every arm is compared against a *fresh re-run* of gpt-4o (baseline_4o), not against the original 2026-06-10 grade — so temperature variance + any L2-reconstruction drift are controlled for. The "20/45 the control flips" is measured against the *original baseline grade*, which is exactly the point: it quantifies how much of the 45 is one-shot variance.

**Reproduce:**
```bash
# offline — reconstruct inputs from L2 (DB read once, or from the SHADOW_L2_DUMP jsonl; no Serper)
python -m scripts.shadow_experiments dump --out .shadow/l2_dump.jsonl
SHADOW_L2_DUMP=.shadow/l2_dump.jsonl python -m scripts.shadow_experiments \
  --baseline <main-repo>/.qa-bias-rerun/baseline_s1_per_query.jsonl \
  prepare --subset bias45 --out .shadow/inputs_bias45.jsonl
# live — one verdict arm over cached inputs (OpenAI cost, concurrency 1 for clean measurement)
SHADOW_L2_DUMP=.shadow/l2_dump.jsonl python -m scripts.shadow_experiments \
  run --arm o3_mini --inputs .shadow/inputs_bias45.jsonl --concurrency 1 --out .shadow/arm_o3_mini_bias45.json
```

---

## 6. Open / not-yet-run

- **Prompt-arm (`prompt_exemplars`) — directive 2, PROD-FAITHFUL + WIRED, OpenAI-quota-blocked only.** G1 (I5.10 verdict-prompt unification) + G2 (I2 loader + AP/exemplar injection into `build_verdict_prompt`) are MERGED to main and pulled into this lane. The harness now calls the REAL prod `build_verdict_prompt`, so every arm grades byte-for-byte what production runs. The A/B is "swap the exemplar FILE the prod prompt reads," not "append a block": `baseline_4o` reads the on-disk file (main's APs-only G2 skeleton); `prompt_exemplars` swaps in I1's filled file (26 exemplars + 9 APs, G3 state) via `SHADOW_EXEMPLAR_FILE` + a loader-cache-reset context manager. **Verified OFFLINE (no OpenAI):** baseline prompt 9271 chars / no exemplars vs prompt-arm 12059 chars (+2788) / exemplars present — `PROMPT-ARM ISOLATES EXEMPLARS: True`. Only the live winner-axis delta remains (OpenAI quota). When restored: ONE unified pass over bias45 (baseline_4o / temp0 / prompt_exemplars / o3_mini / reviews_trim), split structural-24 / variance-19 — the $0-Serper pre-read on the 45-id flip BEFORE the live nocache G3 indicator.
- **T=0 arm — DONE (§3a).** Decisive: variance 18/18, structural 0/22. Recommendation: adopt `temperature=0`, skip best-of-3.
- **best-of-3 arm — BLOCKED on OpenAI quota** (account hit `insufficient_quota` mid-session, parallel to the Serper depletion). Moot for the promotion call (3× cost can't beat T=0 on the variance bucket; can't move structural). Run for completeness only if dispatcher wants the number once OpenAI credits are restored.
- **graded200 arm runs (154 inputs/arm):** inputs prepared (154/154); DEFERRED by dispatcher until G5 demands it, and then run WITH the exemplar arm post-G2/G3 so the wider number includes the prompt change. Also currently OpenAI-quota-blocked.
- **reviews-trim UPSTREAM latency:** handed to I5 (verdict-stage quality cost cleared here = nil).
- **⚠ Cross-cutting blocker:** all remaining LIVE arm runs need OpenAI credit restored (account depleted) — flagged to dispatcher alongside the Serper rotation.

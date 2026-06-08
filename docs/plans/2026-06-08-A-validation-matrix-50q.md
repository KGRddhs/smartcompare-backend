# Bahrain 50-query Validation Matrix — Sprint A Merge Gate

**Owner:** L4-prompts-eval
**Plan:** `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` § L4.3
**Design:** `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 8
**Hard gate:** ≥80% pass rate (weighted) — Sprint A cannot merge below this.

---

## 1. Purpose

Single objective benchmark that catches regressions in price accuracy, spec
correctness, winner declarations, and factual claims across the 9
SmartCompare categories. The 50 queries are biased toward Bahrain retail
visibility (verifiable against `lulu.com.bh`, `sharafdg.com`,
`carrefourbh.com`, `iherb.com`, `bn.boots.com`) so cross-validation is
possible at the gold-truth-authoring step.

## 2. Categories & coverage

| # | Category | Count | Why this many |
|---|---|---|---|
| 1 | Electronics | 12 | Largest SKU surface; phones + TVs + audio + AC + laptops |
| 2 | Supplements | 6 | iHerb + Bahrain pharmacy JSON-LD paths must both work |
| 3 | Fragrances | 6 | Luxury + accessible tiers; Tier 1.5 cascade most exercised |
| 4 | Makeup | 5 | Drugstore + prestige split |
| 5 | Skincare | 5 | Active-ingredient extraction stress |
| 6 | Haircare | 3 | Sulfate-free / paraben-free spec coverage |
| 7 | Fashion | 4 | Footwear + bags + watches |
| 8 | Grocery | 4 | Olive oil + tea + chocolate |
| 9 | Other | 5 | Sodastream / robot vacs / home appliances |
| | **Total** | **50** | |

## 3. Per-query scoring (weighted)

Each query produces 4 axis scores in `[0.0, 1.0]`, weighted into a single
`weighted_score`:

| Axis | Weight | Definition |
|---|---|---|
| Price accuracy | 25% | Both products' `price.amount` within ±15% of gold-truth value |
| Spec correctness | 25% | ≥80% of expected category spec fields present + matching gold-truth `expected_specs` (where authored) |
| Winner correctness | 30% | `overview.winner.product_index` matches `expected_winner_index` from gold-truth |
| Factual claim integrity | 20% | None of the `forbidden_facts` strings (model-knowledge hallucinations) appear in `verdict.winner_reason` / `verdict.key_tradeoff` |

A query is **passing** when `weighted_score ≥ 0.80`. The gate fires at
**aggregate pass-rate ≥ 80%** (≥40 of 50 queries pass).

## 4. Gold-truth file

`data/validation_gold_truth.json` carries the 50 queries + manually
verified expected values. Schema per entry:

```json
{
  "query": "iPhone 15 vs Galaxy S24",
  "category": "electronics",
  "region": "bahrain",
  "expected_prices": {
    "product_0": {"min": 280, "max": 380, "currency": "BHD", "note": "verified lulu.com.bh 2026-06-08"},
    "product_1": {"min": 250, "max": 350, "currency": "BHD"}
  },
  "expected_specs": {
    "product_0": {"display": "6.1", "storage": "128GB", "os": "iOS 17"},
    "product_1": {"display": "6.2", "storage": "128GB", "os": "Android 14"}
  },
  "expected_winner_index": 0,
  "expected_winner_rationale": "Camera + ecosystem lock-in",
  "forbidden_facts": [
    "USB-C 3.2",
    "8K video",
    "Always-on display first introduced"
  ],
  "max_wall_seconds": 25.0
}
```

Field semantics:

- `expected_prices.product_N.{min,max}` — accept any returned amount in
  this BHD range. The 15%-tolerance rule from § 3 is enforced by the
  runner against the gold midpoint.
- `expected_specs.product_N` — only the keys authored need to match
  (partial dict). The runner compares present keys; missing keys in the
  response count as failure.
- `expected_winner_index` — 0 or 1; matches `overview.winner.product_index`.
- `forbidden_facts` — model-knowledge hallucinations specific to this
  query. Each entry is a substring search; presence in any verdict text
  field is a fail. Curated from prior failed comparisons + known
  marketing-speak that GPT-4o-mini is prone to inventing.
- `max_wall_seconds` — soft cap (default 25.0). Wall time over this
  emits a warning but does not fail the query — wall-time is tracked
  separately in `scripts/run_validation_matrix.py` aggregate output.

## 5. Runner

`scripts/run_validation_matrix.py` hits the deployed Railway endpoint
once per query with `nocache=true`. Output: per-query JSON line +
aggregate pass-rate at end.

CLI:

```bash
python scripts/run_validation_matrix.py \
  [--env preview|production] \
  [--limit N] [--category electronics] [--out PATH] \
  [--gold data/validation_gold_truth.json]
```

Exit code: 0 if `pass_rate >= 0.80`, else 2.

## 6. Authoring workflow (Ahmed)

The 50 queries are pre-authored in `data/validation_gold_truth.json`.
Ahmed manually verifies the `expected_prices` ranges against the cited
Bahrain retail sources at run-time. Authoring rules:

1. Use **observed Bahrain retail price ± 15%** as `{min, max}`. Never
   bake the model's training estimate into gold-truth.
2. For supplements, ALWAYS prefer **iHerb USD → BHD converted price** OR
   bn.boots.com JSON-LD where applicable. Note the source in `note`.
3. `expected_winner_index` is the dispatcher's judgment call — escalate
   to Ahmed for any query where the call is non-obvious.
4. `forbidden_facts` should be 3–5 entries per query. Common patterns:
   - Specs from a different model generation that look plausible
   - Marketing claims not in the official spec sheet
   - Wrong-tier comparisons (e.g., flagship vs sub-flagship)

## 7. Re-running on integration

The dispatcher runs the matrix at task M2 against the integrated
`feature/A-integration` branch (Railway preview). Failures below 80%
block the production merge.

## 8. Adding queries post-A

`scripts/run_validation_matrix.py --gold path/to/extended.json` accepts
an alternative gold file. Bundle B.6 expands to 200 queries via the
same schema.

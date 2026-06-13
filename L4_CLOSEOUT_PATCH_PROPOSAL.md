# L4 close-out patch proposal (for team-lead to apply at L4.2 GO / close-out)

> Non-credit head-start per team-lead 2026-06-13. **L4 does NOT apply any of this** —
> team-lead owns the main-repo CLAUDE.md edits + the live Redis op + the persist run.
> This is a ready-to-paste reference so close-out is mechanical.

---

## A. Exact L4.2 command (full-200 persist + S2-regression-check, ONE invocation)

Run from the **merged main** worktree, **sandbox-disabled**, after all lane merges:

```bash
TARGET_BASE_URL=https://web-production-58776.up.railway.app \
  python -m scripts.eval_runner \
    --allow-full \
    --persist \
    --run-kind manual \
    --mode regression \
    --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e \
    --concurrency 1 \
    --out .qa-s3/full200_s3.jsonl
```

- `--allow-full` — required cost guard (full 200 set, ~600-1,000 Serper credits).
- `--persist` — writes ONE `eval_runs` row (service-role Supabase). Capture the id from the
  `# eval_runs row: <UUID>` console line — that UUID is the **new S3 anchor**.
- `--mode regression --baseline-run-id 4aee8e88…` — gates this run against the S1 row
  (still the live anchor; no S2 row was ever persisted), so the run BOTH persists the S3
  row AND fails loudly if any axis dropped >2pp vs S1-state. (S3 should be way up, not down.)
- `--concurrency 1` — measurement discipline (walls are load-sensitive).
- estimate-share rides along automatically — it's in `_format_report` (console) + the persisted
  `metadata` jsonb (`estimate_share`, `estimated_price_cells_total`, `priced_cells_total`).
  **No migration needed** (schema-on-read jsonb).

**Exit-gate read-off from the run** (verify against plan §"Exit gates"):
- winner ≥0.60 · price ≥.84 · specs ≥.87 · factual ≥.94 · pass-rate ≥42.5%
- p95 < 30s (the `within cap` line) · errors ≤1
- estimate-share: present + measurably below the S2-state figure (reconcile vs L1.1 audit)
- row persisted (the `# eval_runs row:` line printed a UUID)

---

## B. CLAUDE.md gate-string re-anchor diff (line ~329) — TEAM-LEAD APPLIES

Replace the S1 baseline UUID with the new S3 row UUID captured in §A. Only the
`--baseline-run-id` value + the trailing baseline-note change; everything else stays.

**BEFORE:**
```
- **Eval gate (Bundle B B.6):** pre-merge `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e` (S1 baseline = 21.0%). Measurement runs ALWAYS `--concurrency 1` (walls are load-sensitive); full-200 needs `--allow-full` + dispatcher GO (~600-1,000 Serper credits). Runbooks: `docs/runbooks/qaren-eval.md` + `qaren-gold-set.md`.
```

**AFTER** (substitute `<S3-RUN-ID>` with the captured UUID, and `<NN.N>` with the S3 pass-rate):
```
- **Eval gate (Bundle B B.6):** pre-merge `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id <S3-RUN-ID>` (S3 baseline = <NN.N>%; S1 row `4aee8e88` = 21.0% / S2 unpersisted, both superseded). Measurement runs ALWAYS `--concurrency 1` (walls are load-sensitive); full-200 needs `--allow-full` + dispatcher GO (~600-1,000 Serper credits). Runbooks: `docs/runbooks/qaren-eval.md` + `qaren-gold-set.md`.
```

Also in the **Active-runtime** block (line ~257), the clause
`S1 baseline row 4aee8e88 remains the anchor until an S2 row persists` should become
`S3 full-200 row <S3-RUN-ID> is the anchor (S1 4aee8e88 / S2-unpersisted superseded)`.

---

## C. Serper rotation-playbook diff (line ~185) — TEAM-LEAD OWNS (per your msg)

L4.3 makes the counter + burn sentinel prefix-scoped, so a rotation self-heals. The playbook's
manual "reset counter + DEL burn_alert_fired:*" step becomes OPTIONAL cleanup.

Suggested edit to the rotation-playbook sentence (the `reset budget:serper:lifetime AND DEL …`
clause): change to note the self-heal, e.g.:
```
→ (S3 L4.3: the counter is now key-scoped `budget:serper:{prefix}:lifetime` + sentinel
`burn_alert_fired:{prefix}`, so a rotation starts a fresh honest counter and re-arms the
alert automatically — the manual reset + DEL is now OPTIONAL cleanup, not required) …
```
Plus the **one-time** live Redis cleanup you flagged you'll own: `DEL budget:serper:lifetime`
(the orphaned unscoped key — safe now that live traffic writes the prefixed key).

---

## D. SESSION_BUNDLES.md Session 62 — L4 contribution line (for your close-out entry)

> **L4 (eval metric + Serper counter):** added the **estimate-share KPI** to eval_runner
> (`extract_price_source_method` + `count_price_source_cells` → GradedQuery → aggregate →
> `EvalReport.estimate_share` → report line + per-query JSONL + persisted metadata jsonb;
> share = produced-estimates / all-produced-prices, blank-method excluded). **Key-scoped the
> Serper lifetime counter** `budget:serper:{prefix}:lifetime` + rotation-safe
> `burn_alert_fired:{prefix}` sentinel — fixes the 5136-across-4-accounts false-trip; rotation
> self-heals (manual reset now optional). 27 TDD tests; 130 passed across the api_budget blast
> radius, zero ripple. Commits 63f514e / 66e58f8 (L4.1) + 0dc806e (L4.3).

---

**L4 commits on `feature/s3-l4-eval-metric`:** 63f514e, 66e58f8 (L4.1), 0dc806e (L4.3). HEAD 66e58f8.

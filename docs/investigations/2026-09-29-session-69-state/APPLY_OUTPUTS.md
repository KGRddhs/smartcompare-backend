# Migration 042 — apply outputs (applied 2026-09-30 ~03:05–03:10 AST, session 70)

Applied in the Supabase SQL editor (project `qulajmyxdbdkchvecmvc`, branch main/PRODUCTION) from the browser pane, Ahmed signed in. Each paste was the file's statements joined onto one line (comment lines dropped; the migration body is whitespace-identical to `migrations/042_search_logs_is_synthetic.sql`), and the editor text was SHA-256-verified against that line before Run.

## 1. Precheck (`APPLY_042_1_PRECHECK.sql`)
`search_logs` had 10 columns (id, user_id, query, input_type, products_found, success, error_message, cost, duration_ms, created_at); **no `is_synthetic`**.

## 2. One-paste apply (`APPLY_042_2_ONE_PASTE.sql`) — BEFORE census, then the transaction, then AFTER
| a | b | c | a_pull | c_pull |
|---|---|---|---|---|
| 14482 | 7 | 422 | 11724 (anchor 11,724 ✓) | 295 (anchor 295 ✓) |

BEFORE = a + b = 14,489; EXCLUDED = c = 422. The eval runner was not explicitly paused; AFTER equalling (a + b) − c exactly shows no probe row committed between the census and the UPDATE.

**AFTER** (same run, after COMMIT): `count(*) WHERE is_synthetic` = **14067** = (a + b) − c exactly (no late-committed probe rows).

## 3. Postcheck (`APPLY_042_3_POSTCHECK.sql`, combined into one read-only SELECT)
| after_true | true_before_2026-06-01 | still_null | total_rows | column type | column comment |
|---|---|---|---|---|---|
| 14067 | 2634 | 2225 | 16292 | boolean | W4-13: TRUE = harness/probe traffic; FALSE = classified organic; NULL = unclassified |

Next (Ahmed's call, CLAUDE.md SESSION 68b W4-13 rows): `ENABLE_SEARCH_LOG_TRUTH` alone → then `SEARCH_LOG_SYNTHETIC_TOKEN` + `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER` → the 1-minute canary. Rollback = flag OFF first, then `migrations/rollback/042`.

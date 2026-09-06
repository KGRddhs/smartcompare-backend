# M22 review — workflow runs (2026-09-05), base 76ace90, Fable orchestrates, Opus workers

| workflow | task id | run id | transcript dir |
|---|---|---|---|
| m22-product-output | wmlim5s9y | wf_4127a8d5-5b2 | C:\Users\SynAckITPC\.claude\projects\C--Users-SynAckITPC-Documents-AI\f110259b-2c46-4d36-b8fd-39f57a9eb840\subagents\workflows\wf_4127a8d5-5b2 |
| m22-code-review | wkj7ekjic | wf_cbda6ac4-a50 | ...\wf_cbda6ac4-a50 |
| m22-load-scale | whz20tcpg | wf_46983729-4eb | ...\wf_46983729-4eb |
| m22-mobile | wufzytndh | wf_e23aeca8-908 | ...\wf_e23aeca8-908 |

Script: m22_review_workflow.js (this folder). Resume: Workflow({scriptPath, resumeFromRunId}) with the SAME args JSON.
Args JSON for each run is in the session transcript (Workflow tool calls); if a resume is needed, re-pass the identical args.

## Baselines (baseline/)
- OpenAI: 429 credit_balance_exhausted (1-token probe) -> recorded/fixture scoring only.
- Serper balance negative (-50) per 2026-09-02 memory; web SERPER_LIFETIME_LIMIT=0 (inert), price-warmer 2200 armed + warmer OFF.
- Prod: /health 200, deployed 76ace90, CPU 0.0016 vCPU, RSS 0.136 GB, ~0 traffic, p50 8ms/p95 22ms on 16 sampled requests.
- Supabase: comparisons 27 (all <= 2026-06-21), search_logs 16,283 (13,237 since 2026-06-01; ~25% failure; success-only p90 18.5s p95 23.8s p99 30.0s max 103.7s), users 18, user_events 146, comparison_feedback 1, product_prices 3,945.
- Mobile at HEAD after npm ci: tsc 0, jest 242 suites/2,320 pass, eslint 0 err/152 warn, npm audit 42 (direct high/crit: expo). Before npm ci, plurals.test.ts failed = stale node_modules (intl-pluralrules missing) — NOT a code defect.
- Backend: local pip OFF-LOCK on 6 pins; 11-node baseline; CI all 5 jobs green at 76ace90, all 5 required.
- Two-lever: phones on 97b5f15 (preview OTA 2026-09-02); 6 commits/38 files of SmartCompareApp on main since.

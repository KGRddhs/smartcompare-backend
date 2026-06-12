# Bundle B S3 "Sources" — Prep Notes (written 2026-06-12 at S2 close)

Next session opens here. S2 plan/template: `docs/plans/2026-06-11-bundle-b-s2-plan.md` (reuse §7 gate protocol + tiered review model). Carry-over ledger: `docs/SESSION_BUNDLES.md` Session 61.

## 0. PREREQUISITES — Ahmed, BEFORE S3 planning starts (~10 min total)

S3's headline lanes ingest Reddit + YouTube as new review/sentiment sources. Without creds the lanes are blocked on day one.

1. **Reddit OAuth app** — reddit.com/prefs/apps → create app (type: `script`) → capture `client_id` + `client_secret`.
2. **YouTube Data API v3 key** — Google Cloud console → enable YouTube Data API v3 → API key.
3. Hand both to dispatcher at kickoff. Dispatcher sets Railway vars via **CLI only** (`railway variables --set ... --service web --skip-deploys` then `railway redeploy --service web --yes`) + syncs local `.env`. **Never the dashboard** — S2 proved dashboard edits stage silently until "Deploy changes" is clicked (prod ran a depleted Serper key through the entire G6 tail because of this).

## 1. Where S2 landed (2026-06-12, all on origin/main)

- **Full-200 exit: 42.5% weighted vs S1 21.0% — doubled.** price .840 / specs .874 / winner .495 / factual .945; p95 29.86s inside 30s cap; errors 46→11 (10 of 11 were the counter/key outage, not engine).
- Merges: G1 `7c07be9`, G2 `7de49e5`, G3 `75a68a7`, G4-1 `06b226a`, G4-2 `7e7a8c7`, G4-3 `1ab5e42`, exemplar-empty `792e07a`, integration fixes `5f137ec`, close-out `d53482c`, op-item resolution `3a1b412`.
- Live: verdict T=0, anti-patterns (exemplars[] emptied — APs carry 100% of signal; content parked `data/verdict_exemplars.s3_parked.json`), unified verdict prompt, registry discovery overhaul + liveness gate, latency stack, 8 dim rows, one-sided-MISSING suppression, missing-dim KPI dial, Serper 80%-burn alert, per-domain /admin/costs buckets. Flag-OFF awaiting evidence: `ENABLE_SELF_CRITIQUE`, `ENABLE_REVIEW_SOURCE_CONSULT`.

## 2. What WORKED in S2 — carry into S3

- **Tiered ultracode review** (per-gate: 4 reviewers → dedup → 2-refuter adversarial verify → completeness critic; one G6 integration sweep): **19 review-confirmed bugs fixed pre-prod**. Fix-before-merge, focused 3-agent re-review on fix deltas. Ahmed-ratified — this is the S3 default.
- **Measurement-first promotion**: every candidate A/B'd before adoption (T=0 + reviews-trim ADOPTED; o3-mini/multi-agent/order-neutrality REJECTED; exemplars emptied on byte-identical +0 evidence). No vibes-based merges.
- **5-lane Opus worktree team** + LANE_STATE.md handoffs + ACK-every-ruling + announced runs. Dispatcher verifies contested "complete" against `git show`, never the report.
- **Dispatcher-direct for small fixes** (token economy — workflows reserved for gate reviews + G6; everything else hands-on). Ahmed-ratified mid-S2 after early workflow overuse.
- **Latency stack discipline**: fan_out 12s, price cap 15s, reviews-trim, 3 concurrency levers → p95 inside cap with quality up.
- **DoH + `curl --resolve`** pattern defeats box DNS for Upstash/Supabase REST when sandbox/local resolver fails.

## 3. What DIDN'T work / lessons (S3 guardrails)

- **Winner axis missed its gate** (.495 < 0.60, ~21 flips short). Proven structural 3 ways: Bahrain data layer, not prompt mechanics. This IS S3's job — more/better Bahrain sources, richer review signal (Reddit/YouTube), winner-relevant evidence density.
- **Token burn**: early S2 fired workflows for everything; at S2 close only ~6-7% of the 20x weekly limit remained. S3 rule: workflows ONLY at gate reviews + final sweep; lanes and dispatcher work direct.
- **Railway dashboard staged-not-applied** (see §0). CLI + explicit redeploy, always; verify with `railway variables --json` after.
- **`budget:serper:lifetime` is not key-scoped** — carried 5136 calls across 4 accounts, false-tripped at 2200 cap mid-run. Reset done 2026-06-12 (counter now honest at ~10). **S3 task: key-scope the counter** (e.g. `budget:serper:{key_prefix}:lifetime`).
- **Local `.env` rot**: Upstash URL pointed at a DELETED database (NXDOMAIN) — local runs were silently Redis-less for weeks; fail-open masked it. Synced 2026-06-12. Periodically liveness-check local creds, don't assume.
- **Eval persistence blocked by box DNS** → S2 has no persisted eval row; S1 row `4aee8e88` is still the regression anchor. S3: persist a row (sandbox-disabled run reaches Supabase) and re-anchor.
- **Agent stalls** (machine sleep + classifier outages): wake → single-step orders → 3-strike → replace/takeover. "Blocked push to main" from a lane = harness guard, dispatcher fast-forwards instead.
- **Test-blind authoring**: tests written against imagined helper signatures failed; read the test file's actual helpers FIRST.
- **Adjudication humility**: the G6 tail-400 burst had TWO causes (counter trip AND dead key) — first single-cause read was wrong. Multi-cause until disproven.

## 4. The three buckets at S2 close

**Bucket 1 — Ahmed prerequisites:** §0 above (Reddit + YouTube creds). Also standing, non-blocking: Google sign-in device diag (`[GOOGLE-DIAG]`), TestFlight external-invite decision (deferred until after Bundle F brainstorm), App Store production gates (icon bytes + legal redraft) only when targeting production.

**Bucket 2 — S3 backlog (Session 61 ledger + today's additions):**
- Winner .495 → ≥0.60 (headline; Bahrain source expansion + Reddit/YouTube ingestion)
- estimate-share metric INTO eval_runner (standing KPI directive; currently underivable from run JSONL) + reduce it
- Persist S2/S3 eval row; advance baseline anchor past `4aee8e88`
- Key-scope `budget:serper:lifetime`; live burn drill
- Carried small bugs: `fetch_retailer_quotes` double-count; `by_source` brand-subdomain attribution; lever-1 orphaned price task on cancel
- Parked exemplars decision (`data/verdict_exemplars.s3_parked.json`); `ENABLE_SELF_CRITIQUE` / `ENABLE_REVIEW_SOURCE_CONSULT` promotion calls on S3 evidence

**Bucket 3 — housekeeping: DONE 2026-06-12.** Old bundle worktrees (b/c/d/e/e-complete/s3-a1/s3-a2 + orphaned bundle-a/e-vf dirs) force-removed after content sampling (only .coverage/lockfile churn/superseded experiments — branches preserved in git); completed-bundle team+task dirs under `~/.claude/{teams,tasks}` deleted per S1 precedent. Remaining: 2 harness-locked `agent-*` worktrees only.

## 5. S3 exit gates (mirror S2 discipline)

- Winner ≥0.60 on full-200 (--concurrency 1, sandbox-disabled)
- estimate-share metric live in eval_runner + measurably reduced vs S2
- No axis regression vs S2 (price ≥.84, specs ≥.87, factual ≥.94); pass-rate ≥42.5%
- p95 inside 30s cap; errors ≤ S2's true count (1)
- Eval row persisted; smoke20 regression gate green at every merge
- Zero review-confirmed bugs unfixed at any gate (fix-before-merge)

## 6. READY-TO-PASTE S3 KICKOFF PROMPT (next session)

```
Bundle B Session 3 "Sources" kickoff. Run ultracode, effort max, on Fable 5.

Prerequisites: here are the Reddit OAuth creds (client_id + secret) and YouTube Data API key: <PASTE>. Set them on Railway via CLI (never dashboard) + local .env first.

1) Sweep: verify S2 residue is clean (housekeeping was done 2026-06-12 — confirm worktree list + team dirs), prune stale branches.
2) Read: docs/plans/2026-06-12-bundle-b-s3-prep-notes.md (prep + lessons), SESSION_BUNDLES.md Session 61 carry-over ledger, docs/plans/2026-06-11-bundle-b-s2-plan.md §7 (gate protocol + tiered review model), CLAUDE.md Active runtime.
3) Ask me the S3 scope/UX decisions BEFORE planning (Bahrain source strategy for the winner axis, Reddit/YouTube surface + attribution rules, estimate-share KPI target, anything ambiguous in the ledger).
4) Refine into a laned plan (~4-5 lanes suggested: Bahrain registry expansion, Reddit+YouTube ingestion, winner-axis scoring/evidence, eval persistence + estimate-share metric, carried small bugs) and run as an Opus worktree agent team with S2 discipline: ACK-every-ruling from session start, LANE_STATE.md per lane, announced runs, measurements ALWAYS --concurrency 1 + sandbox-disabled, smoke20 regression gate vs baseline 4aee8e88 (re-anchor once an S3 row persists) at every merge.
5) Reviews: tiered ultracode — per-gate workflow review (find → dedup → adversarial verify → completeness critic) + one final integration sweep before exit; fix-before-merge on every review-confirmed bug; focused re-review on fix deltas. No bugs leak or remain unfixed. Workflows ONLY at these gates — lanes and dispatcher work direct (token economy).
6) Exit gates per prep-notes §5 (winner ≥0.60 full-200, estimate-share live + reduced, no axis regression, p95 inside cap, eval row persisted).
/loop until /goal S3 fully shipped and tested with ultracode workflows and no errors remain
```

---
name: never_blind_the_instrument_to_fix_a_metric
description: When a measurement shows a feature isn't firing / a metric looks bad, never "fix" it by suppressing the code path that produces the signal — that optimizes the number by destroying the evidence. Make the real condition true instead.
type: feedback
---
When a measurement reveals a feature isn't firing (or a metric looks bad), do NOT resolve it by gating/skipping the code path that PRODUCES the signal. Suppressing the instrument makes the number look better while removing the very evidence the work exists to generate.

**Why:** Bundle B S1 (2026-06-10), the post-merge prod bias probe showed 0 registry-routes because escalating queries (the only ones that can produce a `route:registry`) were cap-breaching at 30s. A "budget-aware gate: skip Bahrain site-discovery when elapsed wall > N" was on the table as the "cheapest cut." It was REJECTED: escalating queries are the sole producers of routing evidence, so skipping them to lower the cap-breach count would also guarantee the registry could never be observed firing — you'd be reporting a green wall metric by blinding the exact instrument the bundle was built to read. Generalizes beyond price routing: applies to any "the metric is red so disable the thing that trips it" temptation (skipping a slow validator to pass CI, dropping a noisy log that's the only failure signal, short-circuiting a check to hit an SLO).

**How to apply:** When tempted to gate/skip/short-circuit to improve a measurement, ask: "does this path PRODUCE the signal I'm measuring?" If yes, the fix is to make the underlying condition true (here: reduce latency so escalation fits the cap, or raise the cap on a measurement canary), NEVER to suppress the path. If you must suppress for an unrelated reason, the metric it feeds becomes invalid and must be re-derived from an un-suppressed source — say so explicitly.

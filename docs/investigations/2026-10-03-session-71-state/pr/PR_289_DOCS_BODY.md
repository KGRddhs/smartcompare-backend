## Session 71 checkpoint (2026-10-03) under `/synack-build-orchestrator`

State folder: `docs/investigations/2026-10-03-session-71-state/` - `SESSION_71_STATE.md` (section 0 = the resume checklist), `ledger.md`, the approved `IMPLEMENTATION_PLAN.md`, `CONFIG_AUDIT_PLAN.md`, `RESEARCH_DIGEST.md`, every Fable ruling and RED-gate record, the traffic finding of 2026-10-02, the T0b spec, the issue and PR bodies, and `scripts/` (every workflow script, the agent rules, `apply_audit_batch_a.py`, `live_schema_meta.py`, the GitHub REST helpers).

### CLAUDE.md
- Ship-blockers: a SESSION 71 CORRECTION - blocker #1 is DONE (launcher art #279, in-app mark #288; the reveal glyph is unit U4d, issue #283); a new binary is needed, never an OTA.
- `model_router_service` line: the 4o cap is read per call (#268, closed by #285).
- The SESSION 69 correction about the retry ceiling is marked RESOLVED (#265 closed by #285: all five `AsyncOpenAI` constructions carry `max_retries`).
- A short SESSION 71 Active-runtime block (process, merged PRs, units in flight, the anonymous-traffic finding and the activation ruling, audit batch A status).

### Runbook
- Section D gains the fresh-install note: the icon and the native launch screen change only with a new binary; delete the old app on the two test iPhones first.

### Not in this PR
- The U13 flag row (added when U13 merges).
- Audit batch C / T0c CLAUDE.md contradiction fixes (their own units).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

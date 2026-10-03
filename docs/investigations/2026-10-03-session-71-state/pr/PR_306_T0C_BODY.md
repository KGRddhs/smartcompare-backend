## T0c: CLAUDE.md contradiction fixes (config audit batch C: R1 step 3, R2, R3, R4, R20)

One file, line-level diff (70 insertions, 75 deletions, CRLF kept). Nothing outside CLAUDE.md.

- **R1** the Railway variable recipe prints names only (`--kv | cut -s -d= -f1 | grep -xE ...`; a non-secret flag may be confirmed by an exact-line count); the "query env vars through `mcp__railway__*`" sentence is deleted.
- **R2** the self-contradicting production statements are dated history or gone (Bright Data gate, migrations 038/042, "no live deployment", the phones OTA group, Serper, Scrape.do); the reference sections carry one pointer to the latest state doc; the migration ledger records dated applies only, so a merged-but-unapplied migration (043) is never read as applied.
- **R3** every appended CORRECTION paragraph is folded into its sentence: ship blockers #1 (done on main, needs a new binary) and #2 (still open, U8), the onboarding canary, the five `AsyncOpenAI` constructions, the SESSION 68b heading, provider keys, the W3-lane RECORD_AUDIO fact; the stale "#223 corrections owed" bullet is deleted; principle 5 gains "edit in place, never append a correction".
- **R4** principle 4 is now the build harness in force (`/synack-build-orchestrator`: Workflow tool, Opus agents, Fable orchestrator, at most two gate-heavy workflows, `pyt.py` bounds, the `node -e 0` probe, the stall rule as `stall_monitor.py` really behaves); the "parallel 4-Opus TeamCreate" and "bypassPermissions REQUIRED" lines are gone; principle 8 points at principle 4.
- **R20** one eval baseline id (the newer one), the CI deselect count measured from `tests/.pre_impl_failures.txt` (11), `node node_modules/typescript/bin/tsc --noEmit` everywhere, the junction rule stated once under Worktree paths with pointers elsewhere.

Process: Opus editor with a grep proof per removed contradiction (in the state folder notes), Opus adversarial diff review (2 defects: an unfolded W3-lane pair and a stall rule that did not match the harness; 9 minors), Opus fix round, orchestrator read of the full diff. Out of scope and untouched: the SESSION 71 Active-runtime block, the flag rows (R21), the archive sections, the large restructure T1-T3.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

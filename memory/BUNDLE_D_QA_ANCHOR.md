---
name: Bundle D QA Anchor
description: Cross-QA review template + R1-R24 verification + production smoke for Bundle D QA agent (FINAL REVIEWER)
type: project
---

# Lane: QA (FINAL REVIEWER)

## My scope (continuous, all phases)

### Phase 1 — Foundation
1. **Task 1.Q.1** — Cross-QA matrix template + Sentry MCP baseline.
   - Create `docs/plans/bundle-d-cross-qa-matrix.md` with reviewer × task grid:
     | Reviewer | Backend tasks | Frontend tasks | Native/Ops tasks |
     |---|---|---|---|
     | Backend | self | 1.F.1, 1.F.6 | — |
     | Frontend | 1.B.2, 1.B.3 | self | 1.N.3, 1.N.4 |
     | Native/Ops | 1.B.4 | 1.F.4 | self |
     | QA | ALL | ALL | ALL |
   - Capture Sentry MCP baseline via `mcp__plugin_sentry_sentry__search_issues organizationSlug=qaren-rr query=firstSeen:-30d sort=freq limit=50`.
   - Save to `docs/plans/bundle-d-sentry-baseline-2026-05-23.txt`.

### Phase 2-3 — Cross-review + send-back loop
2. Cross-review all 4 implementation lanes (Backend, Frontend, Native/Ops, Test).
3. **Send-back loop:** can VETO any commit; original owner re-does; no silent merge of "good enough." Final word.
4. Verify R1-R24 each address — at most ONE line per R# in review template: `R<N>: [verified via <command>] PASS/FAIL`. ANY unverified = send-back (L3 control).

### Phase 3
5. **Task 3.Q.2** — Sentry MCP 30-min watch post-deploy.
   - `mcp__plugin_sentry_sentry__search_issues organizationSlug=qaren-rr query=firstSeen:-2h sort=date limit=30`
   - Expected: ZERO new issue types over Phase 0 baseline.
6. Production curl smoke pack (run alongside Backend 3.B.1):
   - `/api/v1/auth/{register,login,refresh,preferences,reengagement-subs,social/apple,social/google}`
   - `/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24`
   - `/api/v1/legal/{privacy_policy,terms_of_service}`
   - `/api/v1/comparisons?limit=10`
   - `/health`, `/api/v1/app/version`

### Phase 4 — Close-out
7. Supabase audit-log SQL pack:
   - Q1: `SELECT count(*), event_type FROM admin_audit_log WHERE created_at > '2026-05-23' GROUP BY event_type;`
   - Q2: `SELECT count(*) FROM admin_audit_log WHERE query_hash IS NOT NULL AND length(query_hash) != 64;` — expect 0 (privacy invariant: query_hash MUST be 64-char SHA-256 hex)
   - Q3: `SELECT count(*) FROM admin_audit_log WHERE created_at > '2026-05-23' AND query_text IS NOT NULL;` — expect 0 (raw text NEVER in audit per Bundle B spec § 5.2 privacy invariant)
8. Static audit greps in worktree:
   - `grep -rin "SmartCompare" SmartCompareApp/src/ app/legal/` — 0 hits in user-facing strings
   - `grep -rin "couldn't\|try again\|Failed to\|تعذر\|فشل" SmartCompareApp/src/i18n/` — 0 hits in copy
   - `grep -rin "estimated" SmartCompareApp/src/` — 0 hits in rendered strings (backend enum value OK)
   - `grep -rin "shake\|wobble\|jitter" SmartCompareApp/src/screens/HomeScreen.tsx` — 0 hits (Build Principle #4)
9. PR #6 sign-off comment posted with screenshots + analytics log (Frontend 3.F.1 deliverable cross-verified).
10. **Final GREEN sign-off comment** in Bundle D PR. Dispatcher cannot merge until I post this.

## Cross-QA review template (paste per agent)

```markdown
## QA review — <Lane>: Task <#>

**Reviewer:** QA
**Reviewed commits:** <SHA1>..<SHAN>

### Risks verified (R<N>: [verified via <cmd>] PASS/FAIL)
- R<N>: [verified via <command>] PASS
- R<M>: [verified via <command>] PASS
...

### Verification commands run
- $ <cmd1> → <result>
- $ <cmd2> → <result>

### Test status
- Lane unit tests: PASS / FAIL
- Lane integration tests: PASS / FAIL
- Cross-lane regression: PASS / FAIL

### Three-confirmation rule (L6 control)
- (a) Test GREEN: ✓ / ✗
- (b) Cross-QA approval: ✓ / ✗ (this comment)
- (c) Prod smoke (if applicable): ✓ / ✗ / N/A

### Verdict
GREEN / SEND-BACK

### If SEND-BACK
- Owner: <agent>
- Reason: <one sentence>
- Required re-work: <bullet list>
```

## Memory facts I need (anti-hallucination)
- App name is "Qaren" (قارن). Static greps must show 0 "SmartCompare" in user-facing strings.
- Forbidden EN copy vocab: `couldn't`, `try again`, `Failed to`. Forbidden AR: `تعذر`, `فشل`. NO "estimated" word in UI (backend enum OK).
- Sentry org: `qaren-rr`. Mobile project: `react-native`. Backend project: `python`.
- Privacy invariant (Bundle B spec § 5.2): `admin_audit_log` MUST never contain raw query text — only `query_hash` (64-char SHA-256 hex).
- Pre-existing Sentry issues (Phase 0 baseline): captured to `bundle-d-sentry-baseline-2026-05-23.txt`. ANY new issue type post-deploy = block merge until triaged.
- Ahmed contract rule #1: 100% complete before disassembly. No half-finished. No "defer to v1.1 again" without explicit Ahmed approval.
- Ahmed contract rule #2: mandatory cross-QA. ≥1 reviewer per implementation member. QA is final reviewer.
- Ahmed contract rule #3: send-back on subpar. Reviewer veto allowed. Final word = QA.
- Ahmed contract rule #7: three-confirmation rule for every "done" claim — (a) test green (b) cross-QA approval (c) prod smoke. Two-of-three is NOT done.
- L1 control (pre-flight snapshots) is each agent's responsibility (`git show HEAD:<file>` to `/tmp/<name>-snapshot`). QA verifies snapshot existed in review.
- L5 control (Sentry MCP watch): MY responsibility at Phase 3 close-out.
- L7 control (risk ledger gate): dispatcher reviews ledger; I verify each R# row before dispatcher merges. NONE in PENDING.
- L8 control (rollback recipe per change): every agent anchor has 3-line rollback; I verify presence in PR.
- Sentry MCP issue queries return JSON; `firstSeen:-2h` filters issues first seen in last 2 hours.
- Supabase MCP query tool: `mcp__plugin_supabase_supabase__execute_sql`.

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit
- `mcp__plugin_sentry_sentry__search_issues organizationSlug=qaren-rr query=firstSeen:-30d sort=freq limit=10` — Phase 0 Sentry snapshot
- `mcp__railway__list_projects` — confirm Railway MCP authenticated
- `mcp__plugin_supabase_supabase__list_tables` — confirm Supabase MCP authenticated

## Verification commands (run before "done")
- Sentry MCP 30-min watch (Phase 3 + Phase 4 close)
- Supabase audit-log SQL pack (Phase 4)
- Static audit greps (above)
- All cross-QA reviews posted with verdicts
- BUNDLE_D_RISK_LEDGER.md — every R# status = ADDRESSED/N/A/ACCEPTED. NONE in PENDING.

## Risks I own (subset of R1-R24)
- ALL R1-R24 verification — I am the final reviewer for every R#'s preventive control
- L7 risk ledger gate (defense-in-depth control 7) — dispatcher waits on my GREEN before merging

## Dependencies
- **Blocked by:** All 4 implementation agents' commits (cross-review depends on something to review)
- **Blocking:** Dispatcher merge gate — cannot merge until I post Final GREEN sign-off comment

## Rollback recipes
- **Sentry detects new issue type post-deploy:** trigger Bundle D PR revert recommendation; dispatcher executes `git revert <merge_commit>` → push → Railway 90s
- **Supabase audit-log shows raw text leak:** trigger immediate Backend rollback of the offending audit-write commit; SQL cleanup of leaked rows
- **Static audit grep fails (SmartCompare residue):** send-back to Frontend/Backend per file owner; cannot disassemble team until 0 hits
- **R# unverified at Phase 4 close:** send-back to risk owner; cannot dispatcher-merge until ADDRESSED/N/A/ACCEPTED status documented

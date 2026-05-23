# Bundle D — Cross-QA Review Matrix

**Owner:** QA agent (FINAL REVIEWER)
**Created:** 2026-05-23
**Worktree HEAD at creation:** `3928d7a`
**Contract:** Ahmed Rule #2 — every implementation commit reviewed by ≥1 other agent; QA is final word.

---

## Reviewer × task grid

Each column lists tasks reviewed by the row's agent (in addition to QA's universal coverage).

| Reviewer | Backend tasks | Frontend tasks | Native/Ops tasks |
|---|---|---|---|
| **Backend** | self | 1.F.1, 1.F.6 | — |
| **Frontend** | 1.B.2, 1.B.3 | self | 1.N.3, 1.N.4 |
| **Native/Ops** | 1.B.4 | 1.F.4 | self |
| **QA** | ALL | ALL | ALL |

### Reviewer-of-record assignments (rationale)

- **Frontend reviews 1.B.2 (legal markdown rebrand C15)** — Frontend renders the markdown via `LegalScreen`; cross-checks brand string sweep does not break heading/paragraph structure (R22).
- **Frontend reviews 1.B.3 (Sentry `_before_send` query-string scrub C14)** — Frontend owns the URL-construction call sites; verifies regex preserves `?nocache=true`, `?token=` patterns (R21).
- **Backend reviews 1.F.1 (refresh-token mutex R9)** — Backend `auth_routes.refresh` is the failure surface; cross-checks the singleton `Promise` is module-scoped, not function-scoped.
- **Backend reviews 1.F.6 (ai_sharing_enabled default OFF C17)** — Backend owns `users.preferences` schema; verifies SQL spot-check that NEW users default OFF while existing ON rows are untouched (R23).
- **Native/Ops reviews 1.B.4 (`_fire_and_forget` audit on 24 sites R15)** — Native/Ops anchor independence check; per-site WRAP/SKIP-with-reason decisions are listed in PR comment.
- **Frontend reviews 1.N.3 (`expo-apple-authentication` config plugin R5)** + **1.N.4 (`expo-notifications` plugin block C16)** — Frontend consumes `app.json` plugin block; verifies no breaking change to existing plugins.
- **Native/Ops reviews 1.F.4 (camera ? help overlay R17)** — Native/Ops owns the EAS build that will ship this; cross-checks scary-vocab copy gate.

---

## Cross-QA review template (paste per agent commit)

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

---

## Review-progress tracker

| Commit SHA | Lane | Task # | Reviewer | Status | Verdict | Notes |
|---|---|---|---|---|---|---|
| `29e4d76` | Test | 1.T.1 | QA | reviewed | **GREEN** | RED triage doc only; defer of `test_phase1_includes_reviews` cites design § 12 line 385. Doc-only, no test status manipulation. |
| `70a34b3` | Native/Ops | 1.N.4 (C16) | QA | reviewed | **GREEN** | expo-notifications plugin object-form, brand `#10B981` tint, lines 87-92 of `SmartCompareApp/app.json`. Plugin separation discipline preserved. |
| `03cdc1e` | Native/Ops | R5 citation | QA | reviewed | **GREEN** | R5 → ADDRESSED with proper citation per Risk Ledger update protocol. Surfaces R14 BOTH-gate split correctly (app.json leg done, Apple Dev Portal leg PENDING). |

Append rows as commits land on the worktree. Statuses: `pending` → `in_review` → `GREEN` / `SEND-BACK` (→ re-review).

---

## Three-confirmation rule (Ahmed Rule #7) — enforcement

Every "done" sign-off requires:
- **(a)** Test GREEN (unit or integration as applicable)
- **(b)** Cross-QA approval (this matrix + QA template)
- **(c)** Prod smoke where applicable (Backend deploy + Native/Ops EAS build)

**Two-of-three is NOT done.** QA will reject any sign-off that lists 2/3.

---

## Risk Ledger (R1-R24) verification gate

QA verifies every R# transition from PENDING → ADDRESSED / N/A / ACCEPTED. See `memory/BUNDLE_D_RISK_LEDGER.md`. Dispatcher cannot merge until **ZERO PENDING** rows remain. Send-back authority applies to any unverified or improperly-cited risk.

---

## Send-back protocol (Ahmed Rule #3)

When QA issues SEND-BACK:
1. Post template above to the owner via `SendMessage` with `Verdict: SEND-BACK`
2. Cite the specific design doc § / R# / verification command that failed
3. Original owner re-does the work (no silent merge of "good enough")
4. Owner re-requests review with new commit SHA(s)
5. QA re-verifies, posts GREEN or another SEND-BACK

---

## QA Final GREEN sign-off gate

QA posts `## Bundle D QA Final GREEN sign-off — verified 2026-MM-DD` comment on PR only when ALL of the following are GREEN:

- ☐ All 5 lane sign-offs posted in PR (Backend, Frontend, Native/Ops, Test, QA-self)
- ☐ `BUNDLE_D_RISK_LEDGER.md` shows zero PENDING (every R1-R24 = ADDRESSED / N/A / ACCEPTED)
- ☐ Sentry MCP 30-min watch: zero new issue types over `bundle-d-sentry-baseline-2026-05-23.txt`
- ☐ Production curl pack: 100% 200 OK
- ☐ Supabase audit-log: privacy invariants hold (Q2 = 0 bad hash, Q3 = 0 raw text)
- ☐ Static audit greps: zero hits per anchor doc
- ☐ All pre-existing RED tests triaged (greened by Bundle D or explicitly deferred with Ahmed approval)

---

## Sentry baseline reference

`docs/plans/bundle-d-sentry-baseline-2026-05-23.txt` — Phase 0 snapshot:
- 3 known issue types (1 Apple provider, 1 Google Sign-In native, 1 refresh-token race)
- All 3 expected to be addressed by Bundle D itself, NOT regressions
- Phase 3 close-out gate: any NEW issue type post-deploy = block merge until triaged

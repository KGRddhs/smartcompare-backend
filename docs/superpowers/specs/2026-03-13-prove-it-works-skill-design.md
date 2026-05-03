# Prove It Works — Skill Design Spec

**Date:** 2026-03-13
**Status:** Approved & Implemented
**Problem:** Claude claims bugs are fixed without verifying the actual user flow. Login errors, comparison errors, and multi-layer bugs get "fixed" repeatedly, wasting tokens and user patience.

## Problem Statement

Three failure modes when Claude fixes bugs:
1. **Tests pass ≠ bug fixed** — runs pytest, sees green, declares victory without triggering the actual bug scenario
2. **Wrong root cause** — misunderstands the problem, fixes unrelated code
3. **Partial fix** — fixes one layer (e.g., backend) but misses other affected layers (frontend, error handling)

Current skills (`systematic-debugging`, `verification-before-completion`) don't enforce reproduction before fixing or real-flow verification after fixing.

## Solution

A single discipline skill called `prove-it-works` with a rigid 5-phase cycle and a QA agent protocol for team contexts.

### Skill Identity

- **Name:** `prove-it-works`
- **Location:** `~/.claude/skills/prove-it-works/SKILL.md`
- **Type:** Discipline-enforcing (rigid, not flexible)
- **Token budget:** ~600 words
- **No supporting files** — process skill, everything inline

### Trigger Conditions

**Triggers when:**
- User reports a bug, error, or unexpected behavior
- User says "this doesn't work", "I'm getting an error", "login fails", etc.
- User shares error screenshot or message
- An agent claims a fix is done (QA gate)

**Does NOT trigger when:**
- Writing new features from scratch
- Refactoring without a reported bug
- Pure test failures with no user-reported symptom

## The 5 Phases

### Iron Law

```
NO FIX CLAIMS WITHOUT REPRODUCTION BEFORE AND VERIFICATION AFTER
```

### Phase 1: REPRODUCE

Before touching ANY code:
- Get exact steps, error messages, screenshots from user
- Reproduce the error (curl endpoint, trigger flow, read logs)
- Document: "I reproduced the error. Here's what I see: [exact output]"
- If CANNOT reproduce: say so, ask for more details, do NOT guess

**Reproduction criteria by bug type:**

| Bug Type | Reproduction Means |
|----------|-------------------|
| API error | curl with the SAME parameters user reported, get the SAME error |
| Login/auth | Attempt the SAME auth flow (login, register, refresh) |
| Comparison | Run the SAME query, verify the SAME field is wrong |
| Frontend | Trace code path from user action to reported symptom (see escape hatch below) |
| Data issue | Query the SAME data, observe the SAME incorrectness |

**Escape hatch for non-reproducible bugs** (frontend-only, environment-specific, device-specific):
1. State WHY reproduction is impossible in the CLI environment
2. Trace the code path manually with file:line references
3. Identify the exact code that would produce the reported error
4. Get user confirmation: "I can't reproduce this directly, but I believe the issue is [X] at [file:line]. Does this match what you're seeing?"
5. This counts as "confirmed understanding" — but Phase 4 verification must then include asking the user to re-test

**Hard gate:** No code changes until reproduction succeeds OR user confirms understanding via escape hatch.

### Phase 2: INVESTIGATE

After reproducing:
- Trace data flow through ALL layers (frontend → API route → service → external API → response → frontend)
- Identify every file and function in the chain
- Find ACTUAL root cause with evidence
- For multi-layer bugs: add diagnostic logging to pinpoint failure

**Hard gate:** Must state: "The root cause is [X] in [file:line] because [evidence]"

### Phase 3: FIX

- One root cause hypothesis, one cohesive fix (may span multiple files for multi-layer bugs)
- Fix at root cause, not symptom
- If bug spans multiple layers, fix ALL affected layers — do not fix unrelated issues in the same pass
- List every file changed and why

### Phase 4: VERIFY

Re-run the EXACT reproduction scenario from Phase 1:
- Show before/after output
- Unit tests passing is necessary but NOT sufficient
- Must test the actual user flow

| Bug Type | Required Verification |
|----------|----------------------|
| API error | curl the endpoint, show response |
| Login/auth | Full auth flow (login → token → authenticated request) |
| Comparison | Run comparison, check response structure |
| Frontend | tsc + trace exact render path showing fix affects reported UI element. Curl the API the frontend calls to verify data layer. Ask user to re-test the specific flow. |
| Data issue | Query actual data, show correctness |

**Hard gate:** Must show before/after evidence. "Tests pass" alone is NOT acceptable.

### Phase 5: SELF-REVIEW GATE

Answer out loud before claiming done:
1. "Did I fix the root cause or just a symptom?"
2. "Did I fix ALL affected layers?"
3. Quote the exact reproduction from Phase 1 and the exact verification from Phase 4. Are they testing the same scenario? If they differ, explain why.
4. "Am I certain this is fixed, or am I hoping it is?"

If answer to #4 is "hoping" → say so honestly with reasoning.

## Team Context: QA Agent Protocol

When running in multi-agent teams:

### QA Agent Responsibilities
1. Receives the original bug report (same description user gave)
2. Independently reproduces (doesn't trust fixer's reproduction)
3. Reviews the diff (checks all affected layers were touched)
4. Independently verifies (re-runs reproduction scenario after fix)
5. Verdict: "Fix confirmed" or "Bug still present — [evidence]"

### QA Veto Power
- If QA can still reproduce the bug, fix is rejected
- Fixer returns to Phase 2 with QA's evidence
- No rubber-stamping: QA must run, not just read
- **Iteration limit:** After 2 QA rejections on the same bug, escalate to the user with all evidence collected. Do not attempt a third fix without user guidance.

### Team Integration
- 2-agent team: Agent 1 fixes, Agent 2 is QA
- 4-agent team: dedicated QA agent verifies every fix
- QA uses the same 5-phase checklist from reviewer perspective

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Tests pass so it's fixed" | Tests test units. Bugs live in flows. Test the flow. |
| "I can see from the code it's fixed" | Reading ≠ running. Reproduce and verify. |
| "The error was in this function, I fixed it" | Did you check the callers? The frontend? The full chain? |
| "I fixed the backend, frontend should work now" | Did you verify the frontend call? Partial fix = not fixed. |
| "It's probably fixed, let me know if it still happens" | YOU verify. Don't push verification onto the user. |
| "I can't reproduce but I see the problem" | If you can't reproduce, you don't understand it. Get more info. |
| "This is a different issue" | Is it? Same root cause manifesting differently? Investigate. |

### Red Flags — STOP and Return to Phase 1
- About to edit code without having reproduced the bug
- About to say "fixed" without showing before/after output
- Fixed one file but bug spans multiple files
- "Should work now" — the two most dangerous words
- "I think I see the issue" without having run anything

## Relationship to Existing Skills

| Existing Skill | Relationship |
|----------------|-------------|
| `systematic-debugging` | Covers root cause investigation (Phase 2). `prove-it-works` adds mandatory reproduce-before and verify-after gates |
| `verification-before-completion` | Generic evidence requirement. `prove-it-works` is specific: evidence = actual user flow |
| `requesting-code-review` | Code quality review. `prove-it-works` QA = functional correctness |
| `test-driven-development` | May be invoked in Phase 3 for regression tests |

## Success Criteria

1. Claude never claims "fixed" without showing before/after reproduction evidence
2. Multi-layer bugs get ALL layers fixed in one pass
3. When uncertain, Claude says "I'm not sure" instead of "it's fixed"
4. In teams, QA agent independently verifies every fix
5. Token waste from repeated "it's fixed" / "no it isn't" cycles drops to near zero

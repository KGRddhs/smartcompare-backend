# Design — Bundle C prod-state documentation pass

**Date:** 2026-05-22
**Author:** Claude (Opus 4.7) + Ahmed
**Context:** Whole-project audit on 2026-05-22 surfaced `ENABLE_BUNDLE_C_SCORING=false` on Railway despite `CLAUDE.md` + `docs/SESSION_BUNDLES.md` + `MEMORY.md` all describing Bundle C as "shipped, always-on per Option A — no flag-gating retrofit."
**Decision:** Pure-code path. Do **not** flip Railway. Do **not** delete the code flag. Document the discrepancy so future audits, future Ahmed, and future Claude sessions are not misled.

---

## Goal

Leave breadcrumbs that prevent the next reader from chasing phantom bugs the way the audit nearly did. Specifically: anyone debugging scoring behavior in production should be able to answer "is Bundle C calibration's None-propagation active?" in one click, with no ambiguity.

## Non-goals

- Not changing scoring behavior in production
- Not deleting or rewriting historical session log entries (they reflect what was *attempted*)
- Not removing the code flag (the kill switch stays available for the eventual re-validation)

---

## What the flag actually gates (verified by grep)

`_bundle_c_scoring_enabled()` is read at **one site only** — `app/services/scoring_service.py:944` inside `_compute_raw_scores`:

```python
if missing:
    scores[dim_name] = None if flag_on else MISSING_SCORE
```

When flag is `false` (current prod): missing raw signals are written as `MISSING_SCORE=50`. Downstream, `calibrate_score(50)` produces a band-midpoint score (~70). The A.4.9 silent-dim-omission filter (which checks `score_a is None and score_b is None`) **never fires** because scores are never None.

When flag is `true`: missing raw signals propagate as `None`. The omission filter can fire and quietly drop dims that lack data on both sides. `calibrate_score(None, has_signal=False)` short-circuits to indicate no signal.

**Everything else in Bundle C is unconditional.** The flag does *not* gate: A.3.1 pros/cons via `response_format=json_object`, A.3.2 factual_verdict builder, A.3.3 Serper GCC→US fallback, A.4.5 `detect_comparison_quality`, A.4.7 Tier 2 spec fallback, A.5.x 5-tier `top_tier` budget + Migration 024, A.6.1 priority-driven value coefficients, A.7.1 confidence threshold loosening, A.9.1 `applied_shifts` contract, A.10.x diagnostic flag-gating, frontend Section B UX.

This is a **much narrower scope than the audit initially implied**. The framing "Bundle C is OFF in prod" is incorrect. The correct framing is: "Bundle C's missing-signal representation is on the legacy `MISSING_SCORE=50` path; silent dim omission is therefore disabled in prod; 95% of Bundle C is live."

---

## Deliverables (4 file changes)

### 1. New canonical state doc — `docs/BUNDLE_C_PROD_STATE.md`

The single answer to "is Bundle C live?" Sections:
- **TL;DR** — 1 sentence stating flag=false, narrow scope of impact
- **What is and isn't gated** — table separating unconditional Bundle C behaviors from the one flag-gated mechanism
- **Why the flag is off** — set false during Session 52 post-merge debugging by Ahmed; specific trigger not recorded; treat as "paused for re-validation" not "kill switch by design"
- **Before flipping the flag to true** — checklist (low-traffic window, Sentry watch on `_dim_*`, watch `WINNER_INDEX_MISMATCH` log frequency from H1 fix, rollback command ready)
- **Related drift caught in same audit** — paragraph on `ENABLE_HYBRID_MODEL_ROUTING` (env=true in Railway, zero code references — the flag is phantom; `model_router_service.py` runs unconditionally)
- **Sources** — links to CLAUDE.md Bundle C entry + `scoring_service.py:298-306` + `docs/SESSION_BUNDLES.md` Bundle C entry
- **Last verified** — date + the command (`railway variables --kv | findstr BUNDLE_C`)

### 2. CLAUDE.md edit

- Append an inline `[STATUS 2026-05-22:` block immediately after the existing "Bundle C IMPLEMENTATION shipped this session (always-on, Option A — no flag-gating retrofit)" sentence in the Session 52 paragraph. Block calibrated to the narrow scope: "the calibration cascade's None propagation + silent dim omission are on the legacy MISSING_SCORE=50 path; all other Bundle C behaviors are unconditional and live. See `docs/BUNDLE_C_PROD_STATE.md`."
- Patch the env-vars line for `ENABLE_HYBRID_MODEL_ROUTING`: add `(documented but not wired — env value is cosmetic; see docs/BUNDLE_C_PROD_STATE.md § "Related drift")`.

Net: ~5 lines added.

### 3. MEMORY.md edits + new feedback memory

- Insert a `[STATUS 2026-05-22:` line at the top of the existing Bundle C entry under "Pending follow-ups" — calibrated to the narrow scope, links to `BUNDLE_C_PROD_STATE.md`.
- Create new memory file `feedback_docs_vs_railway_env_drift.md` — captures the verification discipline (grep code for flag → run `railway variables` → trace gated vs unconditional → only then trust the doc's "live" claim).
- Add one-line index entry under "Feedback (collaboration discipline)".

### 4. `docs/SESSION_BUNDLES.md` edit

Append a `---\n**RETRACTION (2026-05-22):**` block at the end of the existing Bundle C entry (which currently runs from line 246 to EOF). Same scope-calibrated language, links to `BUNDLE_C_PROD_STATE.md`.

---

## Out-of-scope (deferred to a future bundle)

- Flipping `ENABLE_BUNDLE_C_SCORING=true` in Railway. Requires staging-tester validation first.
- Deleting the code flag. Stays for the eventual re-validation kill-switch.
- Wiring or removing `ENABLE_HYBRID_MODEL_ROUTING`. Mentioned in state doc; fix in next code commit if you want.
- Sweeping the 10 other spec/plan/log files that mention "Bundle C" or "always-on" — those are historical artifacts of what was designed, not deployed state. The 3 operational docs (CLAUDE.md / MEMORY.md / SESSION_BUNDLES.md) are the ones that mislead live debugging.

---

## Verification after implementation

- `cat docs/BUNDLE_C_PROD_STATE.md | head -5` returns the new doc
- `grep "STATUS 2026-05-22" CLAUDE.md` returns 1 hit
- `grep "STATUS 2026-05-22" MEMORY.md` (in the memory dir) returns 1 hit
- `grep "RETRACTION (2026-05-22)" docs/SESSION_BUNDLES.md` returns 1 hit
- New `feedback_docs_vs_railway_env_drift.md` exists in memory dir
- All 4 docs render correctly in a markdown previewer (no broken links)

---

## Why skip the writing-plans skill

The brainstorm skill's terminal state is "invoke writing-plans" to create a structured implementation plan. For this scope (1 new doc + 3 small edits with content already drafted), a plan doc would be ceremony. This design IS the plan; the next step is mechanical Edit/Write calls verified by the checklist above. If the implementation surfaces hidden complexity, we'll fall back to writing-plans for the remediation.

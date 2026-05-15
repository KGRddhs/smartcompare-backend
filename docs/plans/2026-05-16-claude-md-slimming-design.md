# CLAUDE.md Slimming Design

**Date:** 2026-05-16
**Status:** Approved, pending implementation plan
**Problem:** CLAUDE.md is 51.6k chars / 370 lines, tripping Claude Code's 40k perf warning. Hallucination risk + fix-quality degradation from oversized always-loaded context.

## Goals

- Drop CLAUDE.md to ~28k chars (well under the 40k threshold, close to the 270-line target set in Session 34).
- Preserve Claude's ability to find feature-deep context on-demand.
- Respect Session 34's research finding that blanket splitting hurts tightly coupled architecture (pricing ↔ scoring ↔ behavior ↔ personalization) — extract only self-contained subsystems.

## Non-Goals

- Splitting cross-cutting architecture (price pipeline, auth, security hardening) into skills. These stay inline.
- Deleting historical content outright — bundle history goes to a lazy doc, not the trash.
- Per-path auto-loading via `.claude/rules/`. Rejected in Session 34 research.

## Architecture

Three mechanisms working together:

1. **Project-local skills** (`.claude/skills/<name>/SKILL.md`) — auto-surfaced in every session via system-reminder. Loaded on-demand by the Skill tool when description matches user intent. Zero tokens until invoked.
2. **Lazy reference doc** (`docs/SESSION_BUNDLES.md`) — pointed to by a 1-line breadcrumb in CLAUDE.md. Claude reads only when explicitly relevant.
3. **Trimmed CLAUDE.md core** — keeps cross-cutting architecture, commands, gotchas, active flags, two-app warning. Everything always-needed stays inline.

## File layout (after)

```
CLAUDE.md                                      ~28k chars, ~210 lines
.claude/skills/
  qaren-referrals/SKILL.md                     ~3.5k
  qaren-cohort/SKILL.md                        ~2.5k
  qaren-scoring/SKILL.md                       ~3.5k
  qaren-eas-deploy/SKILL.md                    ~1k
docs/SESSION_BUNDLES.md                        ~13k (bundle history A/B/C/D/E)
```

Total chars reclaimed from CLAUDE.md: **~23.5k**.

## Skill triggers (description field, trigger-rich)

Each skill's `description` is the only thing Claude sees before invocation, so it must contain keywords from future requests: file paths, route paths, function names, env var names, table names.

### qaren-referrals
> Use when touching referral invites, share links, /api/v1/referrals/* routes, invite codes (QR-XXXXXX), Loop 1/Loop 2 flow, redemption chain, abuse detection, device-fingerprint caps, bonus expiry, or referral_invites/referral_redemptions tables. Covers Smart Decision Referrals + Bundle B/C/D lifetime-cap overhaul.

**Contains:** original "Smart Decision Referrals" section + Bundle B/C/D referral hardening notes + redemption-only register flow + sources pointer to `app/services/referral_service.py`, `app/services/abuse_detection_service.py`, `app/api/referral_routes.py`.

### qaren-cohort
> Use when touching cohort personalization, demographics endpoint, /api/v1/auth/demographics or /cohort-profile, cohort_priors.json, build_cohorts.py, cohort_service.py, or ENABLE_COHORT_PERSONALIZATION flag. Covers survey-driven priors, hierarchical fallback match, and privacy invariant.

**Contains:** original "Cohort personalization" section + exact-case key gotcha + ETL gotchas from Session 41 + sources pointer to `app/services/cohort_service.py`, `scripts/build_cohorts.py`.

### qaren-scoring
> Use when touching deterministic scoring, scoring_service.py, value badges, tradeoff pairs, dimension winners, personalization caps (plus or minus 30/10/5 percent), prompt personalities, trust validation, behavioral profiles, or the three-layer personalization system.

**Contains:** original "Deterministic scoring", "Prompt personalities + trust validation", "Personalization" sections + sources pointer to `app/services/scoring_service.py`, `app/services/prompt_personalities.py`, `app/services/trust_validation_service.py`, `app/services/behavior_service.py`.

### qaren-eas-deploy
> Use when shipping OTA updates, eas update commands, eas build, EAS channels (development/preview/production), runtime version policy, or when JS-only fixes need to reach testers.

**Contains:** original "EAS Update infrastructure" section + Two-lever launch model note (currently in Commands → Frontend) + Apple Developer gating notes.

## What stays in CLAUDE.md (inline, always-loaded)

- Project Purpose, Operating Principles, Two-app/ warning
- Commands (Backend, Frontend, Dependencies, Migrations)
- Architecture overview (entry, middleware, router list, core service summary, decomposed modules, price pipeline summary, rating pipeline, URL sourcing, supplement-specific gotchas, key services list)
- Frontend overview (navigation, screens, design system, services)
- External APIs section
- Cross-cutting patterns: fact-checking, `product.price` is object, GCC_REGIONS keys, per-request services, cost budget + caching, auth + security hardening, SSE streaming, feedback/events, category selection, sharing+history, luxury detection, review/spec quality
- Qaren UX Redesign (touches frontend-wide, keep inline)
- Bundle A Pre-launch P0 (current deployment baseline, keep inline)
- Environment Variables, Tests, Pre-launch, Known Remaining Bugs
- Detailed Context index

**Replacements for removed sections (inline breadcrumbs):**

```markdown
### Smart Decision Referrals
See skill: qaren-referrals (auto-loads when referral routes / invite codes / Loop 1+2 mentioned)

### Cohort personalization
See skill: qaren-cohort (auto-loads when demographics / cohort flag / cohort_priors mentioned)

### Deterministic scoring + Personalization
See skill: qaren-scoring (auto-loads when scoring_service / dimension scores / personalization caps mentioned)

### EAS Update infrastructure
See skill: qaren-eas-deploy (auto-loads when shipping OTA / building APK / EAS channel mentioned)

### Bundle history (sessions 44-47)
See docs/SESSION_BUNDLES.md — read when investigating regressions from Bundles A/B/C/D/E.
```

## Staleness mitigation

Each skill includes a maintenance header:

```yaml
---
name: qaren-referrals
description: Use when touching ...
last_verified: 2026-05-16
update_when_changing:
  - app/services/referral_service.py
  - app/services/abuse_detection_service.py
  - app/api/referral_routes.py
  - migrations touching referral_invites or referral_redemptions
---
```

Plus a `Sources` block at the end of each skill listing the authoritative code files. Discipline: when a referral PR ships, the skill updates in the same commit. Same maintenance discipline as today's CLAUDE.md, but easier to spot drift because each skill is small and topical.

## Data flow

```
User request arrives
  -> system-reminder lists all skills (incl. project-local qaren-*)
  -> Claude matches request against skill descriptions
  -> invokes Skill(skill="qaren-referrals") if relevant
  -> skill content loaded, work proceeds with full context
  -> unrelated sessions never load it (token-free)

For bundle history:
  -> CLAUDE.md breadcrumb mentions docs/SESSION_BUNDLES.md
  -> Claude reads file only when investigating bundle-related regression
```

## Failure modes & mitigations

| Failure | Mitigation |
|---|---|
| Skill doesn't trigger when it should | description packed with file paths, route paths, function names, env vars, table names |
| Skill triggers too aggressively | descriptions scoped to specific subsystems, not generic terms |
| Cross-cutting fix needs 2+ skills | Claude invokes both — multi-skill invocation supported |
| Skill content drifts behind code | `Sources` block forces verification against current code; `update_when_changing` checklist surfaces affected files |
| New referral system replaces current one | Skill still triggers (topic match), gives current state as context for redesign |

## Testing & validation

1. **Char count check** — `wc -c CLAUDE.md` should be < 40k (target ~28k).
2. **Manual trigger test** — fresh sessions with prompts:
   - "fix the referral cap bug" -> should auto-load `qaren-referrals`
   - "the cohort match is broken" -> should auto-load `qaren-cohort`
   - "tweak the dimension scoring" -> should auto-load `qaren-scoring`
   - "push an OTA update" -> should auto-load `qaren-eas-deploy`
3. **No-regression test** — ask a question that needs only core context ("what's the price pipeline?") and confirm Claude answers correctly from inlined CLAUDE.md alone.
4. **Update Session 34 memory** — note that selective extraction worked where blanket split didn't, so future-Claude doesn't re-litigate the decision.

## Out of scope

- Extracting auth + security hardening, price pipeline, or backend services list. These are cross-cutting and stay inline.
- Auto-loading skills via `paths:` triggers in `.claude/rules/`. Rejected in Session 34.
- Deleting any content. Everything moves to either a skill or `docs/SESSION_BUNDLES.md`.

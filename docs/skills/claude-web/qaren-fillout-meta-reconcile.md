---
name: qaren-fillout-meta-reconcile
description: Use when the user pastes a Fillout CSV (or attaches one) and asks to match Fillout completions back to Meta ads or ad sets via UTM tags. Use when the user says "reconcile Fillout with Meta", "which Meta ad drove the deepest leads", "Fillout attribution", or similar. Reads the UTM columns from the Fillout export, groups by utm_content and utm_term, and reports which Meta ad / ad set drove the most deep-engagement Fillout completers. Bridges the off-platform tracking gap.
---

# Fillout ↔ Meta Ad Attribution Reconciliation

## When to use

- User pastes a CSV directly into the chat
- User uploads a CSV attachment
- User mentions Fillout responses + Meta ads in the same prompt
- `qaren-meta-daily-check` hands off on Day 3 / Day 4

## Input format expected

A Fillout CSV export with at minimum these columns (Fillout names them with the question label, plus metadata):

- `utm_source` (should be "meta" for all paid traffic)
- `utm_medium` (should be "cpc")
- `utm_campaign` (e.g., `BH_LeadGen_V1_2026-05`)
- `utm_content` (the Meta dynamic ad name — `Ad01_VideoA_Arabic` or `Ad02_VideoB_AR-EN-Mix`)
- `utm_term` (the Meta dynamic ad set name — `AS01_AdvB_18-44_AR-EN_IG`)
- `Submission ID` (Fillout's row primary key)
- `Status` (should be "finished" for completed responses)
- Email or phone column (if collected) — for matching against the Meta leads CSV

## What you produce

A reconciliation report:

```
Fillout completions attributable to Meta: XX of YY total Fillout rows
(rows without utm_source=meta are organic / other channels — skip them)

By Meta ad (utm_content):
  Ad01_VideoA_Arabic: XX completions, $X.XX cost per deep completion
    (cost per deep completion = Meta ad spend on this ad / Fillout completions)
  Ad02_VideoB_AR-EN-Mix: XX completions, $X.XX cost per deep completion

By Meta ad set (utm_term):
  AS01_AdvB_18-44_AR-EN_IG: XX completions

Conversion funnel:
  Meta link clicks (form opens): XXX
  Meta leads (Instant Form submits): XXX (XX% of opens)
  Fillout completions (deep): XXX (XX% of Meta leads — drop-off through the funnel)

Deepest-engagement ad: <name> drove XX of YY total Fillout completions (XX%)

Notable observations:
  - <e.g., "Ad01 has higher Instant Form CPL but 2x the Fillout completion rate — these leads are higher intent">
  - <e.g., "AR form completes Fillout at XX% vs EN form at XX% — translate friction matters">
```

## Edge cases to handle

- **Rows missing utm_source:** classify as "organic / non-Meta" and exclude from the per-ad breakdown, but report the count separately.
- **Status != "finished":** count as partial completions, report in a separate line.
- **Same email appearing in both Meta leads CSV and Fillout export:** match if present; tell the user how many leads converted from "Instant Form submit" all the way through to "Fillout deep completion".
- **utm_content has unexpected value (not Ad01/Ad02 names):** report it verbatim; could indicate URL truncation, dynamic-token failure, or a new ad the user hasn't told you about.

## Constraints

- Never invent data. If a column is missing or empty, say so explicitly — don't fill in zeros silently.
- Never store the CSV contents long-term. Process in-context and discard.
- Privacy: don't echo back full email addresses or phone numbers in the report. Hash, count, or summarize — never paste back.
- Use the `qaren-brand-voice` skill for any user-facing commentary text.

## What this skill can NOT do

- Cannot fetch the CSV from Fillout directly (no Fillout MCP installed) — user must paste / attach
- Cannot retro-fire Meta CAPI events from Fillout completions (deferred work, see design doc § 3)
- Cannot deduplicate against organic Fillout responses without an additional source key

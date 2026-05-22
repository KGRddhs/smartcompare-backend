---
name: qaren-meta-campaign-setup-bahrain
description: Use when the user asks to create / set up / launch the Bahrain Qaren lead-gen campaign on Meta Ads, or says "create V1 Bahrain leads campaign", "set up the Qaren ad campaign", "launch Bahrain lead gen", or any variant. Triggers a complete one-shot build of the campaign hierarchy via Meta Ads MCP: 1 campaign + 1 ad set + 2 ads + 2 Instant Forms, all PAUSED. The user must provide video IDs (uploaded to Meta Media Library), Fillout survey URLs (AR + EN), privacy URL, and Instagram handle. After creating, ask the user to verify in Ads Manager before activation. Never auto-activate.
---

# Qaren Bahrain Lead-Gen Campaign Setup (V1)

## Inputs the user MUST provide before running

Before executing any Meta MCP create-call, confirm you have ALL of:

1. **Video A ID** (Meta Media Library) — the pure-Arabic video
2. **Video B ID** (Meta Media Library) — the Arabic-with-English-code-switching video
3. **Privacy URL** (default: `https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy`)
4. **Fillout AR survey URL** (for the Arabic Instant Form thank-you CTA)
5. **Fillout EN survey URL** (for the English Instant Form thank-you CTA)
6. **Qaren Instagram handle** (e.g., `@qaren.app`)
7. **Meta Ad Account ID** (the account the user authorized via MCP OAuth)

If ANY input is missing, ask for it before proceeding. Do not guess defaults except for the privacy URL.

## What you create (in order)

### 1. Campaign

| Field | Value |
|---|---|
| Name | `BH_LeadGen_V1_2026-05` |
| Objective | `OUTCOME_LEADS` |
| Status | `PAUSED` |
| Special ad categories | `[]` (none) |
| Buying type | `AUCTION` |

### 2. Ad Set

| Field | Value |
|---|---|
| Name | `AS01_AdvB_18-44_AR-EN_IG` |
| Optimization goal | `LEAD_GENERATION` |
| Billing event | `IMPRESSIONS` |
| Daily budget | $10 USD (1000 cents) |
| Start time | 24h from now (gives user time to activate) |
| End time | 96h from now (4-day hard stop) |
| Status | `PAUSED` |

**Targeting object:**

```json
{
  "geo_locations": {"countries": ["BH"], "location_types": ["home"]},
  "age_min": 18,
  "age_max": 44,
  "locales": [],
  "publisher_platforms": ["instagram", "facebook"],
  "instagram_positions": ["stream", "story", "reels"],
  "facebook_positions": ["story"],
  "device_platforms": ["mobile"],
  "targeting_automation": {"advantage_audience": 1}
}
```

Notes:
- `genders` is OMITTED to mean "all"
- `interests`, `behaviors`, `custom_audiences` are OMITTED (no detailed targeting at $40 budget)
- Locale codes for AR + EN on Meta: AR = `2304`, EN = `1001` — set `"locales": [2304, 1001]` if MCP supports it; otherwise omit and let language match via creative

### 3. Instant Form — Arabic version

| Field | Value |
|---|---|
| Name | `LeadForm_V1_AR_Qaren-EarlyAccess` |
| Locale | `ar_AR` |
| Privacy policy URL | (from user input) |
| Form type | `MORE_VOLUME` |
| Intro screen | DISABLED |

**Questions (in order):**

1. Full name — `type=FULL_NAME`, `prefilled=true`
2. Email — `type=EMAIL`, `prefilled=true`

**Thank-you screen:**

| Field | Value |
|---|---|
| Title | `شكراً! بنرسلك أول ما ينطلق Qaren 🌿` |
| Body | `بنخبرك أول واحد لما ينطلق Qaren — وبتكون من أول المستخدمين.` |
| CTA #1 button text | `تابعنا على إنستغرام` |
| CTA #1 link | `https://instagram.com/<user-provided-handle>` |
| CTA #2 button text | `ساعدنا بدقيقة — استبيان قصير` |
| CTA #2 link | `<Fillout AR URL>?utm_source=meta&utm_medium=cpc&utm_campaign=BH_LeadGen_V1_2026-05&utm_content={{ad.name}}&utm_term={{adset.name}}` |

### 4. Instant Form — English version

| Field | Value |
|---|---|
| Name | `LeadForm_V1_EN_Qaren-EarlyAccess` |
| Locale | `en_US` |
| Privacy policy URL | (from user input) |
| Form type | `MORE_VOLUME` |
| Intro screen | DISABLED |

**Questions (in order):**

1. Full name — `type=FULL_NAME`, `prefilled=true`
2. Email — `type=EMAIL`, `prefilled=true`

**Thank-you screen:**

| Field | Value |
|---|---|
| Title | `Thanks! We'll email you the moment Qaren launches 🌿` |
| Body | `You'll be one of the first to try Qaren when it goes live.` |
| CTA #1 button text | `Follow us on Instagram` |
| CTA #1 link | `https://instagram.com/<user-provided-handle>` |
| CTA #2 button text | `Help us in 1 minute — short survey` |
| CTA #2 link | `<Fillout EN URL>?utm_source=meta&utm_medium=cpc&utm_campaign=BH_LeadGen_V1_2026-05&utm_content={{ad.name}}&utm_term={{adset.name}}` |

### 5. Ad #1 — Video A → Arabic form

| Field | Value |
|---|---|
| Name | `Ad01_VideoA_Arabic` |
| Ad set ID | (from step 2 above) |
| Creative | Video A by ID, no separate image/text overrides |
| Lead form ID | `LeadForm_V1_AR_Qaren-EarlyAccess` |
| Call to action | `LEARN_MORE` (or `SIGN_UP` — pick whichever Meta surfaces for Instant Form ads) |
| Status | `PAUSED` |

### 6. Ad #2 — Video B → English form

| Field | Value |
|---|---|
| Name | `Ad02_VideoB_AR-EN-Mix` |
| Ad set ID | (from step 2 above) |
| Creative | Video B by ID |
| Lead form ID | `LeadForm_V1_EN_Qaren-EarlyAccess` |
| Call to action | Same as Ad #1 |
| Status | `PAUSED` |

## Report back to user

After all 6 entities are created, output a summary in this exact format:

```
✅ Campaign created (PAUSED): BH_LeadGen_V1_2026-05 (ID: <id>)
✅ Ad set created (PAUSED): AS01_AdvB_18-44_AR-EN_IG (ID: <id>)
   Audience: Bahrain, 18-44, all genders, AR+EN, Advantage+
   Placements: IG Feed + Reels + Stories, FB Stories
   Budget: $10/day, ends in 4 days
✅ Instant Form (AR): LeadForm_V1_AR_Qaren-EarlyAccess (ID: <id>)
✅ Instant Form (EN): LeadForm_V1_EN_Qaren-EarlyAccess (ID: <id>)
✅ Ad #1 (PAUSED): Ad01_VideoA_Arabic (ID: <id>)
✅ Ad #2 (PAUSED): Ad02_VideoB_AR-EN-Mix (ID: <id>)

Next step: Open Ads Manager → review each entity → activate the campaign manually.
DO NOT have me activate it — verify videos render correctly first.
```

## Constraints — never violate

1. **Status PAUSED on every entity.** Never set `status=ACTIVE` in this skill. Activation is a separate human step.
2. **Never invent values for required user inputs.** If a Fillout URL or video ID is missing, ask.
3. **Never edit existing entities** unless the user explicitly says "re-run setup" — and even then, confirm before destructive changes.
4. **Never call activation tools** (`activate_campaign`, `update_status_to_active`, etc.) from this skill.
5. **All copy must pass the `qaren-brand-voice` skill.** If you're drafting any new text not specified above, apply that skill's contract.

## If something fails mid-creation

If MCP returns an error after some entities are created (e.g., ad #2 fails but ads + forms #1 succeeded), DO NOT delete the partially-created entities. Report what was created, what failed, and ask the user how to proceed. The user can manually clean up partial state in Ads Manager.

# Qaren Bahrain Lead-Gen Skill Bundle — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce 4 `SKILL.md` files Ahmed uploads to claude.ai → Settings → Skills, so Claude on claude.ai web (with Meta Ads MCP connected) can set up, run, and iterate on the $40 Bahrain lead-gen campaign described in `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md`.

**Architecture:** Four focused, triggerable Skills with YAML frontmatter (matching Anthropic's Agent Skills spec). They live in this repo under `docs/skills/claude-web/` for version control. Ahmed uploads each file's content into the Skills creation modal in claude.ai. No code is generated; only documentation + structured Skill files.

**Tech Stack:** Markdown with YAML frontmatter (Anthropic Agent Skills spec, public since 2025-12-18). No runtime dependencies. No build step. No tests beyond manual lint of YAML + cross-reference against the design doc.

---

## Pre-flight (one-time, before any task)

**Verify the design doc exists** — every task references it:

```bash
ls docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md
```

Expected: file exists, ~10 KB.

**Verify CLAUDE.md copy contract reference** — Task 2 (brand-voice skill) cites it:

```bash
grep -n "Copy contract" CLAUDE.md
```

Expected: at least one hit, near the "Qaren UX Redesign" section that lists forbidden vocabulary.

---

## Task 1: Create skill directory + README

**Files:**
- Create: `docs/skills/claude-web/README.md`

**Step 1: Create the directory**

```bash
mkdir -p docs/skills/claude-web
```

Expected: directory created, no error.

**Step 2: Write the README**

Create `docs/skills/claude-web/README.md` with the following content (verbatim):

```markdown
# Qaren Claude.ai Web Skills

This directory holds `SKILL.md` files that Ahmed uploads to **claude.ai → Settings → Skills**. These are NOT Claude Code skills (those live under `~/.claude/`); these run in claude.ai web alongside the Meta Ads MCP connector.

## Why claude.ai web, not Claude Code

The official Meta Ads MCP at `https://mcp.facebook.com/ads` works in claude.ai web (Pro/Max/Team) and Claude Desktop, but **fails OAuth in Claude Code CLI** because Meta hasn't whitelisted Claude Code's dynamic-port redirect URIs. Tracked in Anthropic GitHub issues #55002, #55556, #57191. Until that's resolved, all Qaren ad-ops happens in claude.ai web.

## Skills in this bundle

| # | File | Purpose |
|---|---|---|
| 1 | `qaren-meta-campaign-setup-bahrain.md` | One-shot creation of campaign + ad set + 2 ads + 2 Instant Forms (all paused) |
| 2 | `qaren-meta-daily-check.md` | Daily insights pull + decision-rule recommendation |
| 3 | `qaren-fillout-meta-reconcile.md` | Match Fillout completers to Meta ads via UTM tags |
| 4 | `qaren-brand-voice.md` | Copy contract enforcement (no scary words, AR-first, emerald = signal only) |

## How to upload

1. Open https://claude.ai → click your profile → **Settings** → **Skills** tab
2. Click **Create skill** (or **Upload skill**)
3. Paste the entire `SKILL.md` file content into the editor (including YAML frontmatter at top)
4. Save
5. Repeat for each file

Once uploaded, Skills auto-trigger when the user's prompt matches their `description` field. No further setup needed.

## Design + decisions

Full design rationale: `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md`

Updating these skills:
- Change CLAUDE.md copy contract → update `qaren-brand-voice.md` in the same commit
- Change campaign decision rules → update `qaren-meta-daily-check.md`
- New campaign version (V2, V3, ...) → fork the setup skill, don't edit V1 in place
```

**Step 3: Verify file structure**

```bash
ls -la docs/skills/claude-web/
```

Expected: `README.md` present, ~1.5 KB.

**Step 4: Commit**

```bash
git add docs/skills/claude-web/README.md
git commit -m "docs(skills): scaffold claude-web skills directory + README"
```

---

## Task 2: Write `qaren-brand-voice` skill (foundational — written first)

**Files:**
- Create: `docs/skills/claude-web/qaren-brand-voice.md`
- Reference: CLAUDE.md "Qaren UX Redesign" section (copy contract)

**Step 1: Draft the skill file**

Create `docs/skills/claude-web/qaren-brand-voice.md` with this structure:

````markdown
---
name: qaren-brand-voice
description: Use whenever drafting copy, ad text, headlines, CTAs, push notifications, or any user-facing string for Qaren (قارن) — a Bahrain-based product comparison app. Auto-applies invisibly when Claude is asked to write Qaren ad copy, lead-form thank-you text, Instagram captions, or any user-facing language. Enforces forbidden-vocabulary list, Arabic-first cadence with Bahraini code-switching, emerald-as-signal-color discipline, and trust framing.
---

# Qaren Brand Voice — Copy Contract

## When this skill applies

ANY time you're writing user-facing language for Qaren, including but not limited to:

- Ad copy (headline, body, CTA)
- Lead form labels, questions, thank-you screens
- Instagram captions, Stories text
- Push notification bodies
- Onboarding screen copy
- Error / empty / loading states (rare — Qaren has very few)

This skill does NOT apply to:
- Internal logs, backend code, technical documentation
- Names of campaign / ad set / ad entities (those follow the naming convention in `qaren-meta-campaign-setup-bahrain`)

## Forbidden vocabulary (HARD BAN)

Never use these in user-facing strings — neither Arabic nor English. They violate the brand contract.

**English forbidden:**
- couldn't, can't (in error contexts)
- failed, failure
- error, oops
- try again
- something went wrong
- estimated, approx, approximately (in price/spec contexts)
- problem, issue, broken

**Arabic forbidden:**
- تعذر (could not)
- فشل (failed)
- خطأ (error)
- مشكلة (problem) — when describing app state
- تقدير, مُقدَّر (estimate, estimated) — when describing price/spec

If you find yourself wanting to use one of these, the framing is wrong — reword to describe what IS happening instead of what isn't.

## Approved framing patterns

**For "missing data" situations:**
- EN: "More data coming soon" / "We're still finding info on this"
- AR: "نجمع المعلومات الآن" / "بنحدّث قريباً"

**For "loading":**
- EN: "Comparing..." / "Finding the best option..."
- AR: "نقارن لك..." / "نلقي نظرة..."

**For "wait, please":**
- EN: "Almost there..."
- AR: "بنخلص..." (Bahraini cadence — NOT الصبر / wait)

## Language strategy

**Primary: Arabic** — 80%+ of Qaren's Bahrain target audience is Arabic-primary or bilingual (per Fillout n=337 survey: 41% AR, 48% bilingual, 12% EN-only).

**English: secondary, used when:**
- Targeting the bilingual segment (24% surveyed prefer EN-leaning content)
- Specific videos / creatives are scripted with English code-switching (Bahraini millennial speech pattern)
- Form field labels where translation adds ambiguity

**Code-switching is good** when it sounds natural to a Bahraini millennial. Example: "اختر الخيار اللي يناسبك — smart pick" feels native. Bad: full-sentence English with stranded Arabic words.

## Tone

- **Warm, never urgent.** No "ACT NOW", no "LAST CHANCE", no countdown timers.
- **Confident, never dismissive.** Qaren tells you why it picked something; never says "trust us."
- **Concise.** Hero headlines < 50 chars. CTAs ≤ 3 words.
- **Personal.** Use the singular "you" / "أنت" (not "you all" / "أنتم").

## Color discipline (verbal cue when describing UI)

- **Emerald #10B981** is Qaren's signal color — reserved for winner reveal, success ticks, cohort accents. NOT primary CTA color. If asked to describe a CTA, say "black with emerald accent on hover" not "emerald button".
- **Black #0A0A0B** is the primary surface.
- When describing brand visuals to a designer or another AI, lead with this distinction.

## Trust framing (lifted from Fillout survey n=337)

These are the framings 22-69% of survey respondents said would make them trust a tool:

| Framing | % said this builds trust | Suggested usage |
|---|---|---|
| "Explicit pros and cons" (إيجابيات وسلبيات صريحة) | 69% | Use in ad body and verdict text |
| "Recommendation that fits my budget / need" | 38% | Use near pricing or in onboarding |
| "Clear reason for the recommendation" | 23% | Use under verdict line |
| "Doesn't feel like an ad" | 18% | Avoid hard-sell phrasings |

When drafting a CTA or headline, lean into the 69%-trust framing first (pros/cons / clear comparison) — it's the strongest signal.

## Examples — DO vs DON'T

| Context | DO ✅ | DON'T ❌ |
|---|---|---|
| Ad headline (AR) | "تردد قبل ما تشتري؟ Qaren يقارن لك." | "أوقف الندم! اشتري بثقة الآن!" |
| Ad headline (EN) | "Hesitate before you buy? Qaren compares for you." | "Stop regretting! Buy smart NOW!" |
| Thank-you text (AR) | "شكراً! بنرسلك أول ما ينطلق Qaren 🌿" | "تم بنجاح! انتظر إيميل التأكيد." |
| Lead-form field label | "البريد الإلكتروني" (just the field name) | "أدخل بريدك الإلكتروني للمتابعة *" |
| Price uncertainty | "السعر يبدأ من X دينار" | "السعر التقديري X دينار" |

## Self-check before delivering Qaren copy

Before returning any user-facing string to the user, run this checklist:

- [ ] No forbidden vocabulary (EN list + AR list above)
- [ ] Arabic-first when audience is Arabic-primary or bilingual
- [ ] No urgency / scarcity language
- [ ] Singular "you" / "أنت"
- [ ] Trust framing leans on pros/cons or fits-your-budget angles
- [ ] CTA ≤ 3 words

If any item fails, rewrite before returning.
````

**Step 2: Validate frontmatter syntax**

```bash
head -5 docs/skills/claude-web/qaren-brand-voice.md
```

Expected: starts with `---`, has `name:`, has `description:`, ends with `---`.

**Step 3: Check no forbidden words leaked into the skill text itself**

```bash
grep -niE "couldn't|failed to|estimated|تعذر|فشل" docs/skills/claude-web/qaren-brand-voice.md
```

Expected: only matches inside the "forbidden vocabulary" lists (the skill teaches by example). If matches appear in instructional copy, rewrite.

**Step 4: Commit**

```bash
git add docs/skills/claude-web/qaren-brand-voice.md
git commit -m "docs(skills): add qaren-brand-voice copy-contract skill"
```

---

## Task 3: Write `qaren-meta-campaign-setup-bahrain` skill

**Files:**
- Create: `docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md`
- Reference: design doc sections 1–3 + Meta Ads MCP tool names

**Step 1: Draft the skill file**

Create `docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md` with this structure (entire file template):

````markdown
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
````

**Step 2: Validate the file is syntactically a skill**

```bash
head -5 docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md
```

Expected: starts with `---`, has `name:` and `description:`, closes with `---`.

**Step 3: Cross-check against design doc**

```bash
diff <(grep -oE 'BH_LeadGen_V1_2026-05|AS01_AdvB_18-44_AR-EN_IG|Ad01_VideoA_Arabic|Ad02_VideoB_AR-EN-Mix|LeadForm_V1_AR_Qaren-EarlyAccess|LeadForm_V1_EN_Qaren-EarlyAccess' docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md | sort -u) <(grep -oE 'BH_LeadGen_V1_2026-05|AS01_AdvB_18-44_AR-EN_IG|Ad01_VideoA_Arabic|Ad02_VideoB_AR-EN-Mix|LeadForm_V1_AR_Qaren-EarlyAccess|LeadForm_V1_EN_Qaren-EarlyAccess' docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md | sort -u)
```

Expected: no diff (all 6 names appear in both files).

**Step 4: Commit**

```bash
git add docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md
git commit -m "docs(skills): add qaren-meta-campaign-setup-bahrain skill"
```

---

## Task 4: Write `qaren-meta-daily-check` skill

**Files:**
- Create: `docs/skills/claude-web/qaren-meta-daily-check.md`
- Reference: design doc section 4 (iteration playbook)

**Step 1: Draft the skill file**

Create `docs/skills/claude-web/qaren-meta-daily-check.md`:

````markdown
---
name: qaren-meta-daily-check
description: Use when the user asks for a performance check on the Qaren Bahrain lead-gen campaign, says "Day 1/2/3/4 check", "how's the campaign doing", "pull Qaren metrics", "check Qaren performance", or pastes a date and asks for an update. Pulls insights from Meta MCP for campaign BH_LeadGen_V1_2026-05, applies the decision rules in this skill, and recommends exactly ONE concrete action (boost / hold / pause) with the exact MCP tool call to execute it — but never executes without explicit user confirmation in the same message.
---

# Qaren Bahrain Lead-Gen — Daily Performance Check

## Default campaign reference

If the user doesn't name a campaign, default to: `BH_LeadGen_V1_2026-05`.

If multiple Qaren campaigns exist (V2, V3, ...), ask which one they mean before pulling data.

## What you pull (by day)

### Day 1 (T+24h)

Pull last-24h insights at **campaign + ad set + ad** level. Metrics:

- spend, impressions, reach, frequency, cpm
- video_p25_watched_actions, video_p50_watched_actions, video_p75_watched_actions, video_thruplay_watched_actions, video_play_actions
- inline_link_clicks (form opens proxy)
- leads (form submits)
- cost_per_lead (CPL)
- ctr (link click-through rate)

**Do NOT pull breakdowns on Day 1.** Algorithm is still in learning phase, breakdowns will be noisy.

**Output format:**

```
Day 1 baseline — last 24h:
  Spend: $X.XX
  Impressions: X,XXX
  Reach: X,XXX
  Frequency: X.X
  CPM: $X.XX
  Video plays / thru-plays: XXX / XXX (XX% thru-rate)
  Form opens: XXX
  Leads: X
  CPL: $X.XX (or "N/A — too few leads")
  CTR: X.XX%

Learning phase: active. No action recommended yet.
Anything broken? <yes/no — explain if yes>
```

If 0 impressions: investigate before saying "no action" — check delivery status, ad disapproval, payment.

### Day 2+ (T+48h onward)

Pull last-48h insights at campaign / ad set / ad level. Same metrics as Day 1, PLUS breakdowns:

1. **By ad** (`breakdown=ad_name` or pull each ad individually): impressions, CTR, leads, CPL
2. **By placement** (`breakdown=publisher_platform` + `breakdown=platform_position`): impressions, CPL
3. **By age × gender** (`breakdown=age,gender`): leads, CPL

**Output format:**

```
Day N — last 48h:

[same metrics block as Day 1]

By ad:
  Ad01_VideoA_Arabic: X leads, $X.XX CPL, X.XX% CTR
  Ad02_VideoB_AR-EN-Mix: X leads, $X.XX CPL, X.XX% CTR

By placement:
  IG Feed: X leads, $X.XX CPL
  IG Reels: X leads, $X.XX CPL
  IG Stories: X leads, $X.XX CPL
  FB Stories: X leads, $X.XX CPL

By age × gender:
  18-24 F: X leads, $X.XX CPL
  18-24 M: X leads, $X.XX CPL
  25-34 F: X leads, $X.XX CPL
  ...
```

## Decision rules — apply EVERY check from Day 2

Walk through these in order. Stop at the first matching rule. Apply only ONE rule per check.

| # | Signal (last 48h) | Recommendation |
|---|---|---|
| 1 | 0 impressions cumulative | Investigate delivery (ad disapproval, billing, audience too narrow). Don't recommend changes — escalate to user. |
| 2 | <3 leads total cumulative | HOLD. Tell user: too early, learning still. |
| 3 | CPL > $10 AND >50 link clicks per lead AND ≥10 link clicks total | RECOMMEND PAUSE + redesign. Quote: "Cold conversion is below break-even. Pause and redesign creative or offer before more spend." |
| 4 | Video A vs Video B CPL gap >3× AND winner has ≥5 leads | RECOMMEND pause the loser ad. Quote: "Ad <loser_name> is at $X.XX CPL vs <winner_name> at $Y.YY. >3× gap with N leads of evidence on winner — recommend pausing <loser_name> and letting <winner_name> take its budget." |
| 5 | CPL < $5 AND ≥5 leads total | RECOMMEND +20% budget boost (current daily → current × 1.2). Quote: "CPL is healthy. Boost ad set daily budget from $X to $X.XX (+20%, preserves learning phase)." |
| 6 | CPL $5-10 AND ≥5 leads total | HOLD. Quote: "CPL in acceptable range. Hold steady; re-check tomorrow." |
| 7 | Placement spending heavily with 0 leads after ≥$5 burned in it | RECOMMEND pause that placement at ad-set level. (Rare given manual placement filter.) |

Never combine rules. Never recommend more than ONE change in a single check.

## The MCP call format for boost recommendations

When recommending a budget boost (rule 5), output the exact MCP tool call the user can confirm:

```
Recommendation: boost ad set AS01_AdvB_18-44_AR-EN_IG daily budget from $10 to $12.

To execute, reply: "Yes boost to $12"

The call I'll make (do not execute without your confirmation):
  ads_update_adset(
    adset_id=<id from earlier insights call>,
    daily_budget=1200
  )
```

Budget values are in **cents** in the Meta API (1200 = $12.00).

## The MCP call format for pause recommendations

```
Recommendation: pause ad Ad01_VideoA_Arabic (CPL $X.XX vs Ad02 at $Y.YY).

To execute, reply: "Yes pause Ad01"

The call I'll make (do not execute without your confirmation):
  ads_update_ad(
    ad_id=<id>,
    status="PAUSED"
  )
```

## Day 3 — extras

In addition to the above, also tell the user:

- Should the campaign extend past Day 4 end-date or stop?
- Identify the SINGLE strongest audience slice (age × gender × placement intersection with lowest CPL ≥3 leads)
- Ask the user to paste Fillout CSV for reconciliation (handoff to `qaren-fillout-meta-reconcile` skill)

## Day 4 — final wrap

Skip the daily decision rules. Instead output:

```
🏁 Final wrap on BH_LeadGen_V1_2026-05

Total spend: $X.XX (vs $40 budget)
Total leads: XX
Blended CPL: $X.XX
Total reach: X,XXX
Total impressions: X,XXX

Top performers:
  - Top ad: <name> ($X.XX CPL, X leads)
  - Top placement: <name> ($X.XX CPL, X leads)
  - Top audience slice: <age × gender> ($X.XX CPL, X leads)

Demographic check vs survey baseline (73% F / 91% 18-34):
  Pixel actual: XX% F / XX% 18-34
  Verdict: <CONFIRMS / CONTRADICTS / TOO_FEW_LEADS_TO_TELL>

Fillout deep-completions (if user pasted CSV): XX of XX leads went all the way through the survey

Recommendation:
  □ STOP — KPIs missed (less than 5 leads OR CPL > $10)
  □ EXTEND at current $10/day for 3 more days
  □ SCALE to V2: <specific changes — e.g. "duplicate ad set at $25/day, swap loser ad for new creative">

Reasoning: <one paragraph>
```

## Constraints

- Never auto-execute boost / pause / activate. Always wait for user confirmation in the same chat.
- Never combine multiple recommendations in one check. ONE rule, ONE recommendation.
- Never use forbidden vocabulary from `qaren-brand-voice` skill when drafting recommendation messages.
- Never make decisions off <3 leads of data — always say "too early" in those cases.
````

**Step 2: Validate frontmatter**

```bash
head -5 docs/skills/claude-web/qaren-meta-daily-check.md
```

Expected: `---`, `name:`, `description:`, `---`.

**Step 3: Verify decision-rule table matches design doc**

```bash
grep -A1 "CPL < \$5" docs/skills/claude-web/qaren-meta-daily-check.md docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md | head -10
```

Expected: both files mention "CPL < $5" with the same threshold logic.

**Step 4: Commit**

```bash
git add docs/skills/claude-web/qaren-meta-daily-check.md
git commit -m "docs(skills): add qaren-meta-daily-check decision-rule skill"
```

---

## Task 5: Write `qaren-fillout-meta-reconcile` skill

**Files:**
- Create: `docs/skills/claude-web/qaren-fillout-meta-reconcile.md`
- Reference: design doc section 3 (UTM tracking) + section 4 (Day 3 step)

**Step 1: Draft the skill file**

Create `docs/skills/claude-web/qaren-fillout-meta-reconcile.md`:

````markdown
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
````

**Step 2: Validate frontmatter**

```bash
head -5 docs/skills/claude-web/qaren-fillout-meta-reconcile.md
```

Expected: standard skill frontmatter.

**Step 3: Commit**

```bash
git add docs/skills/claude-web/qaren-fillout-meta-reconcile.md
git commit -m "docs(skills): add qaren-fillout-meta-reconcile UTM attribution skill"
```

---

## Task 6: Update MEMORY.md + design doc with cross-references

**Files:**
- Modify: `MEMORY.md` (add an entry under "Pending follow-ups" pointing to the new skill bundle)
- Modify: `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md` (add a "Skill files shipped" note at the top)

**Step 1: Update MEMORY.md**

Find the "Pending follow-ups" section and add this line as the FIRST item:

```markdown
- **Bahrain Lead-Gen Skill Bundle (claude.ai web)** — 4 Skills shipped to `docs/skills/claude-web/`: `qaren-meta-campaign-setup-bahrain`, `qaren-meta-daily-check`, `qaren-fillout-meta-reconcile`, `qaren-brand-voice`. Upload each to claude.ai → Settings → Skills before the $40 campaign launches. Full design + decisions in `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md`. Iteration rules: CPL<$5 → +20% boost; $5-10 → hold; >$10 → pause+redesign. Never auto-execute boost/pause — always confirm.
```

Verify with:

```bash
grep -n "Bahrain Lead-Gen Skill Bundle" MEMORY.md
```

Expected: 1 match in the Pending follow-ups section.

**Step 2: Update the design doc**

At the very top of `docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md`, after the H1 header and the `**Date:** ...` line, insert:

```markdown
**Implementation:** Plan + 4 skill files shipped — see `docs/plans/2026-05-22-bahrain-lead-gen-skills.md` (plan) and `docs/skills/claude-web/*.md` (skills).
```

**Step 3: Commit**

```bash
git add MEMORY.md docs/plans/2026-05-22-bahrain-lead-gen-skills-design.md
git commit -m "docs(skills): cross-reference Bahrain lead-gen skill bundle in MEMORY + design"
```

---

## Post-implementation — verification checklist (Ahmed does this)

After all 6 tasks complete, run this checklist before uploading to claude.ai:

```bash
# All 5 files present
ls -la docs/skills/claude-web/

# Expected: README.md, qaren-brand-voice.md, qaren-meta-campaign-setup-bahrain.md, qaren-meta-daily-check.md, qaren-fillout-meta-reconcile.md (5 files total)

# Frontmatter valid on every skill file
for f in docs/skills/claude-web/qaren-*.md; do
  echo "--- $f ---"
  head -4 "$f"
done

# Expected: each starts with ---, has name: and description:, ends with ---

# No forbidden vocabulary leaked into skill text (outside the brand-voice teaching examples)
grep -niE "couldn't|failed to|تعذر|فشل" docs/skills/claude-web/qaren-meta-*.md docs/skills/claude-web/qaren-fillout-*.md
# Expected: zero matches (forbidden words only appear in the brand-voice skill's instructional sections)
```

After verifying:
1. Open https://claude.ai → Settings → Skills → Create skill
2. For each of the 4 `.md` files (skip README.md), paste the entire file content (including frontmatter) into the Skill creation modal
3. Save
4. Test by typing `Set up the Bahrain Qaren lead-gen campaign` in a new chat — Claude should auto-load the setup skill and start asking for video IDs / Fillout URLs

If a skill doesn't auto-trigger, the description field needs tightening. Edit the markdown file, push the new content, and re-upload (or edit in the claude.ai UI directly and copy the change back to the repo).

---

**Plan complete and saved to `docs/plans/2026-05-22-bahrain-lead-gen-skills.md`.**

## Execution options

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between, fast iteration. Best for this plan since tasks 2–5 are independent file writes that benefit from parallel work.

**2. Sequential (this session, no subagents)** — I execute each task in order myself. Simpler, slower.

**3. Parallel Session** — Open a new Claude Code session with `superpowers:executing-plans`, batch execution with checkpoints. Best if you want to step away.

Which approach?

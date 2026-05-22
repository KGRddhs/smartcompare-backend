# Qaren Bahrain Lead-Gen — Meta MCP Skill Bundle (Design)

**Date:** 2026-05-22
**Author:** Ahmed + Claude (brainstorming session)
**Status:** Design approved, implementation shipped
**Spec mode:** Pre-launch paid acquisition push, Bahrain market
**Implementation:** Plan + 4 skill files shipped — see `docs/plans/2026-05-22-bahrain-lead-gen-skills.md` (plan) and `docs/skills/claude-web/*.md` (skills).

## Context

Qaren has finished domain verification on Meta (qaren.app) and is preparing the first paid acquisition push. Two videos in Arabic (one with English code-switching) are already produced. The goal is **leads / form submissions / contact info** to seed a launch waitlist, NOT app installs.

The user (Ahmed) connected Meta Ads MCP to **claude.ai web** (custom connector — the Claude Code CLI flow is blocked by a known Anthropic ↔ Meta whitelist gap; tracked at github.com/anthropics/claude-code issues #55002, #55556, #57191). All ad ops happen in claude.ai web; this codebase holds the skill source files for version control.

Existing research baseline: a Fillout survey of 338 Bahrainis (337 finished) gives strong demographic + pain-point signal:

- 91% are 18-34 (60.9% in 18-24, 30.2% in 25-34)
- 73% female, 26% male, 1% prefer-not-say
- 43% Northern governorate, 20% Capital, 16% Muharraq, 14% Southern
- 95% Bahraini nationals
- 48% bilingual, 41% Arabic-primary, 12% English-primary
- **75% have delayed a purchase due to uncertainty more than once** (validates the video hook)
- **69% would first see an ad for this kind of tool on Instagram / TikTok / Snap** (decides placement strategy)
- 69% trust "explicit pros and cons" (matches Qaren's core value prop)
- 58% YES + 36% maybe would use AI buying tool (94% openness)
- Categories bought last 6mo: 52% fashion/beauty, 42% perfume, 39% electronics, 36% subscription, 32% health

The 73% female / 91% young skew is treated as **probable distribution bias** from how the survey was shared, not a hard targeting constraint. Targeting does not exclude males or 35+ — let the Meta pixel discover the truth.

## Goal

Two deliverables Ahmed will use:

1. **Targeting strategy** — concrete Meta Ads Manager settings, encoded as a campaign-setup skill Claude can execute via Meta MCP.
2. **Iteration playbook** — daily-check skill that Claude runs to monitor performance and recommend boost / hold / pause decisions.

Both must respect the budget reality ($10/day × 3-4 days = $40 total) and the brand-voice contract in CLAUDE.md (no scary copy, no "estimated" in user-facing strings, emerald = signal color only).

## Non-goals

- Not building a survey-design skill (Fillout survey already done; data is in)
- Not building a creative-brief / video-script skill (videos already produced)
- Not building a creative-fatigue detector (requires 30+ days of run history; out of scope)
- Not building TikTok skills (business verification still pending)
- Not wiring Meta Conversions API (deferred until qaren.app/ landing page exists or app is live)
- Not auto-executing changes (every create / edit / boost requires explicit Ahmed confirmation per MCP session)

## Section 1 — Campaign structure + funnel

### Funnel

```
Reels/Story scroll → Video (5s hook) → Tap CTA → Meta Instant Form
                                                   ↓
                                          Pre-filled Name + Email
                                                   ↓
                                          Thank-you screen
                                          (Follow @qaren + CTA to Fillout survey for deep research)
```

### Meta Ads Manager settings

| Setting | Value |
|---|---|
| Campaign objective | Leads |
| Conversion location | Instant Forms (on-platform — no landing page) |
| Performance goal | Maximize number of leads |
| Optimization event | Lead |
| Buying type | Auction |
| Structure | 1 campaign → 1 ad set → 2 ads (one per video) |

Both ads route to **separate Instant Forms by language**, so the user is never asked to pick AR/EN. Mapping:

- `Ad01_VideoA_Arabic` → `LeadForm_V1_AR_Qaren-EarlyAccess`
- `Ad02_VideoB_AR-EN-Mix` → `LeadForm_V1_EN_Qaren-EarlyAccess`

### Instant Form spec (both AR and EN versions, structurally identical)

| Field | Behavior |
|---|---|
| Form type | "More Volume" (vs "Higher Intent") — removes review step, max submission rate |
| Intro screen | Skip (extra friction) |
| Question 1 | Full name — pre-filled from FB profile |
| Question 2 | Email — pre-filled from FB profile |
| Privacy URL | `https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy` (live policy endpoint until qaren.app/privacy page exists) |
| Thank-you headline (AR) | `شكراً! بنرسلك أول ما ينطلق Qaren 🌿` |
| Thank-you headline (EN) | `Thanks! We'll email you the moment Qaren launches.` |
| Thank-you CTAs | (1) Follow on Instagram → @qaren handle, (2) "ساعدنا بدقيقة — استبيان قصير" / "Help us in 1 minute — short survey" → Fillout URL with UTMs |

### Why Instant Form, not landing page

- No `qaren.app/` page exists today — the Cloudflare Worker only serves `/r/{code}` redirects. Building a landing page is out of scope for a $40 test.
- Instant Forms convert ~3-5× higher than off-platform landing pages on cold mobile video traffic in MENA.
- Pre-filled fields match the survey's "61% not now" soft commitment — minimum friction wins.
- Trade-off accepted: Instant Form leads are slightly lower intent than landing-page submitters, but at pre-launch waitlist scale that's the right trade.

## Section 2 — Audience + placement recipe (Approach B: Tilted Advantage+)

| Setting | Value | Rationale |
|---|---|---|
| Location | Bahrain (country) | Country-level — Bahrain is small enough |
| Location type | People living in this location | Excludes travelers / temp visitors |
| Age | 18 – 44 | 91% survey signal is 18-34; +44 catches 5.9% in 35-44 without diluting |
| Gender | All | 73% female survey skew is likely distribution bias; let pixel discover |
| Languages | Arabic + English | Matches 48% bilingual / 41% AR / 12% EN survey result |
| Detailed targeting | NONE | At $40 Advantage+ algorithm out-targets manual selection |
| Advantage detailed targeting | ON | Lets Meta expand beyond filters when CPL improves |
| Custom audiences | NONE | No pixel data to seed; revisit at v2 |
| Lookalike audiences | NONE | Need ~100+ leads to seed an LLA |

### Placements (manual override of Advantage+ placements)

✅ **Include:**
- Instagram Feed
- Instagram Reels
- Instagram Stories
- Facebook Stories

❌ **Exclude:**
- Facebook Feed (videos are vertical; 69% survey signal is IG-heavy)
- Facebook Reels (low Bahrain volume)
- Audience Network (low quality on cold lead-gen)
- Messenger ads (low conversion to lead form)
- Facebook In-Stream Video (mid-roll, wrong moment for lead capture)

### Schedule + budget

| Setting | Value |
|---|---|
| Run start | Day 0 (Ahmed activates after Claude creates paused) |
| End date | Day 4 (4-day hard stop as safety) |
| Day-parting | None (Bahrain single timezone, audience too small to over-segment) |
| Daily budget | $10 USD at ad set level (not campaign-level) |
| Bid strategy | Highest volume (default) |
| Attribution | 7-day click, 1-day view (Meta default) |
| Account spend limit | $50 lifetime (belt-and-suspenders safety cap, set in Ads Manager) |

## Section 3 — Naming + tracking conventions

### Hierarchy

| Level | Name template | Example |
|---|---|---|
| Campaign | `BH_LeadGen_V1_2026-05` | `BH_LeadGen_V1_2026-05` |
| Ad set | `AS01_AdvB_18-44_AR-EN_IG` | (single ad set) |
| Ad #1 | `Ad01_VideoA_Arabic` | Pure Arabic video |
| Ad #2 | `Ad02_VideoB_AR-EN-Mix` | Code-switching video |
| Form AR | `LeadForm_V1_AR_Qaren-EarlyAccess` | Arabic Instant Form |
| Form EN | `LeadForm_V1_EN_Qaren-EarlyAccess` | English Instant Form |

### UTM template for Fillout thank-you-screen CTA

```
https://fillout.com/<survey-id>?utm_source=meta&utm_medium=cpc
  &utm_campaign=BH_LeadGen_V1_2026-05
  &utm_content={{ad.name}}
  &utm_term={{adset.name}}
```

`{{ad.name}}` and `{{adset.name}}` are **Meta dynamic insertion tokens** — Meta auto-fills them at delivery time. Configure once on the Instant Form thank-you CTA; Meta handles the rest.

### Tracking gap accepted

Fillout completions are visible **only on the Fillout dashboard** (filtered by UTMs). Meta's algorithm cannot optimize toward Fillout completions because Fillout is off-platform. Meta optimizes toward Instant Form submissions only.

Closing this gap requires Meta Conversions API (CAPI) integration — ~2h dev work, deferred to v2 (budget threshold: $200+).

## Section 4 — Iteration playbook (the daily check)

### Schedule

| Day | Time elapsed | Action |
|---|---|---|
| 0 | T+0h | Confirm launch, check for disapprovals |
| 1 | T+24h | Pull baseline metrics, no breakdowns yet, **don't touch** |
| 2 | T+48h | Pull metrics + breakdowns (by ad, placement, demo), apply rules |
| 3 | T+72h | Same + Fillout CSV reconciliation, extend / stop decision starts |
| 4 | T+96h | Final wrap, scale-to-v2 recommendation if signal is good |

### Decision rules (apply same rules each day from Day 2)

| Signal (last 48h) | Action |
|---|---|
| 0 impressions | Investigate — ad disapproved, billing issue, or audience too narrow |
| <3 leads total | Hold — not enough data, learning still |
| CPL < $5 AND ≥5 leads | Recommend +20% budget boost (to $12/day) |
| CPL $5-10 AND ≥5 leads | Hold steady |
| CPL > $10 with ≥10 impressions per lead opportunity | Recommend pause + redesign |
| Video A vs B CPL gap >3× AND ≥5 leads on winner | Pause loser, keep winner |
| Placement dominates spend but 0 leads | Pause that placement (rare given manual filter) |

**Anti-pattern:** Never make audience or budget changes off <5 leads — that's noise.

### Daily prompts (Ahmed copy-pastes into claude.ai)

**Day 1:**

> Pull yesterday's performance for campaign `BH_LeadGen_V1_2026-05`. Report: spend, impressions, reach, frequency, CPM, video plays, thru-play rate, link clicks (form opens), form submits (leads), CTR, CPL. Tell me: is anything broken? Don't recommend changes — too early.

**Day 2:**

> Pull last-48h performance for `BH_LeadGen_V1_2026-05`. Include breakdowns: by ad, by placement, by age × gender. Apply the decision rules I gave you. Give me one concrete recommendation with the exact MCP tool call, but DO NOT execute — I'll approve first.

**Day 3:**

> Same breakdowns. Plus: extend or stop decision? Best audience slice? Here's the Fillout CSV — match by `utm_content` to Meta ads. Tell me which ad sent the deepest leads. [paste CSV]

**Day 4:**

> Final wrap. Total spend, leads, blended CPL, top ad, top placement, top audience slice. Did pixel-discovered demos match the 73% F / 91% young survey skew? Recommendation: stop, extend, or scale to V2.

### Safety defaults

- Every Claude-created entity starts **PAUSED**. Ahmed activates manually.
- Budget changes >20% require Ahmed's explicit per-message confirmation.
- Claude must reference survey insights when recommending changes (no generic advice).
- Claude must respect the copy contract (no scary words, no "estimated").

### What Claude can NOT do (so expectations are calibrated)

- Upload new video creatives (Ahmed does this in Ads Manager; video IDs then passed to Claude)
- Pull Fillout data directly (no Fillout MCP installed; Ahmed pastes CSV)
- Auto-execute changes (MCP requires explicit per-action confirmation — this is the safety default, kept)
- Edit a Meta Pixel (none installed)
- Complete Meta Business / domain verification (one-time human-only steps)

## Section 5 — Skill bundle deliverable

Four `SKILL.md` files. Live in `docs/skills/claude-web/` for version control. Ahmed uploads each to claude.ai → Settings → Skills.

| # | Skill | Trigger phrases | Purpose |
|---|---|---|---|
| 1 | `qaren-meta-campaign-setup-bahrain` | "Set up the Bahrain Qaren lead-gen campaign" / "Create V1 Bahrain leads campaign" | One-shot setup of campaign + ad set + 2 ads + 2 Instant Forms, all PAUSED |
| 2 | `qaren-meta-daily-check` | "Day N check" / "How's the Qaren campaign?" / "Check Qaren performance" | Pull insights, apply decision rules, recommend single action |
| 3 | `qaren-fillout-meta-reconcile` | "Reconcile Fillout completions with Meta ads" / paste of Fillout CSV | UTM-match Fillout completers to Meta ads; report deep-engagement attribution |
| 4 | `qaren-brand-voice` | Auto-applies when drafting Qaren ad copy | Copy contract enforcement (no scary words, AR-first, emerald = signal, Bahraini cadence) |

## Operational notes

### One-time setup Ahmed does in Ads Manager

1. **Upload 2 videos** to Meta Media Library → note both video IDs (~5 min)
2. **Confirm payment method** on file → Ads Manager → Billing
3. **Set account spend limit** to $50 lifetime (safety cap)
4. **Set up Instagram pairing** for the ad account if not done — needed for IG placements (~2 min)

### One-time setup Ahmed does in Fillout

1. **Create AR version** of the survey (if survey is currently mixed, fork into a pure-AR copy)
2. **Create EN version** by translating
3. **Note both survey URLs** to give to Claude when triggering skill #1

### Estimated cost

- $40 USD ad spend (capped at $50 lifetime as safety belt)
- $0 for Meta MCP usage (free during beta)
- $0 for Fillout (existing plan)
- Total: **$40 USD**

### Success criteria (post-campaign)

| Metric | Floor | Target | Stretch |
|---|---|---|---|
| Total leads | 5 | 10 | 20+ |
| Blended CPL | <$10 | <$5 | <$3 |
| Fillout deep-completions | 1 | 3 | 8+ |
| Demographic signal | Pixel data either confirms or contradicts survey skew (both are useful) |
| Insight quality | Top ad / top placement / top demo slice identified | Same | Same + ready V2 plan |

If floor missed: kill campaign, redesign creative + offer. If target hit: scale to v2 at $30-40/day for 7-day run. If stretch hit: consider $50+/day scale with new creative variants.

## Decisions captured

- **Funnel:** Meta Instant Form primary, Fillout linked from thank-you screen for depth (Option 4)
- **Form fields:** Name + Email only, both pre-filled — max volume
- **Languages:** Two Instant Forms (AR + EN), paired to matching ads (no user choice)
- **Audience approach:** Approach B (Tilted Advantage+) — no interest targeting, manual placement filter
- **Budget:** $10/day × 3-4 days = $40 total, with 20%-step boost rule for in-flight scaling
- **Pixel/CAPI:** Deferred to v2 (no qaren.app/ landing page yet)
- **TikTok:** Deferred (business verification pending)
- **Skill files:** 4 of them, in `docs/skills/claude-web/`

## Open items (carry into implementation plan)

- Confirm Fillout AR + EN survey URLs (Ahmed creates these before activation)
- Confirm Qaren Instagram handle for thank-you-screen CTA
- Confirm Meta Media Library video IDs for both videos (after Ahmed uploads)
- Decide privacy URL final state — use Railway endpoint now, switch to qaren.app/privacy when that page exists
- Define exact Arabic copy for Instant Form thank-you headline + button labels (Claude drafts in skill #4)

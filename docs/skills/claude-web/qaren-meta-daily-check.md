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

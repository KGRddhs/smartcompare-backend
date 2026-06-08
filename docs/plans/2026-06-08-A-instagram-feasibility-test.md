# Instagram / TikTok Social-Source Feasibility Test (B-prep)

**Owner:** L4-prompts-eval
**Plan:** `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` § L4.4
**Design:** `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 10
**Status:** Manual exercise — pre-investment validation before B.4 funds Apify integration.

---

## 1. Why this test exists

Bundle (B) Phase B.4 plans a social-source layer (Reddit OAuth + YouTube
Data API + Fragrantica / INCIDecoder / PubMed + Instagram + TikTok). The
last two require Apify (or similar) and would cost ~$0.005 per comparison
on every run. Before we build, we need to know whether brand main
accounts + influencer posts contribute information that Serper + Reddit
+ YouTube don't already surface.

**Decision rule:** if **≥ 3 of 5** test queries score ≥ 3 (out of 5)
unique-value, green-light Apify integration in B.4. Otherwise **cut**
Instagram/TikTok from (B) scope and reinvest the budget into deeper
Reddit / Fragrantica / PubMed coverage.

## 2. The 5 test queries

Each chosen so a different category-level signal type would be expected
to differ between brand main and Serper:

| # | Category | Query | What we expect social to add |
|---|---|---|---|
| 1 | Fragrance | "Tom Ford Black Orchid" | Wear-feel, longevity, sillage details that text reviews don't capture; visual sense of who wears it |
| 2 | Makeup | "Fenty Pro Filt'r Foundation shade 320" | Live shade-match swatches on actual GCC skin tones |
| 3 | Fashion | "Birkenstock Arizona" | Styling angles, sandbox of outfits the typical buyer pairs with |
| 4 | Electronics gadget | "Dyson Airwrap" | Hands-on technique videos showing realistic results, not marketing footage |
| 5 | Supplement | "Garden of Life Omega-3" | User-posted before/after framing + third-party-tested badge surfacing |

## 3. Procedure (per query, ~12 minutes)

For each of the 5 queries:

### Step 1 — Baseline: what does the current backend surface?

Run the query through the deployed backend with `?nocache=true` and note:

```
- Specs surfaced (key fields)
- Reviews summarised (pros + cons)
- Verdict text (key_tradeoff, value_context)
- Source URLs (price + rating)
- Image rendered (yes/no, is it the actual product)
```

### Step 2 — Instagram brand main account

Open Instagram in the browser at `instagram.com/<brand>` (e.g.
`/tomfordbeauty`, `/fentybeauty`, `/birkenstock`, `/dyson`,
`/gardenoflife`). Scroll the most recent ~30 posts. For each:

- Note any **unique product detail** not already in the backend's
  surfaced data (e.g., "official tester video shows pump goes 4 sprays
  for full coverage" → wear-feel signal).
- Distinguish: marketing imagery vs new product info.

Time-box: 5 minutes per brand main.

### Step 3 — Three GCC influencer / reviewer accounts

For each query, identify the top-3 GCC-relevant accounts (Bahrain /
Saudi / UAE-based reviewers, ≥10k followers). For each account search
the brand or query keyword:

- Note unique signals: shade-match on Middle Eastern skin tones,
  Bahrain shipping receipts, ramadan-period usage notes,
  bilingual EN/AR text overlays, in-person retail visits.

Time-box: 5 minutes per query across all 3 accounts.

### Step 4 — TikTok equivalent

Same procedure as Step 2+3 but on TikTok. Search `#brandname` + scan
top 30 results.

### Step 5 — Score

Score per query on the 1–5 scale:

| Score | Meaning |
|---|---|
| **5** | Social surfaces critical info the backend missed entirely (e.g., new variant, recall, GCC-specific availability). |
| **4** | Social adds multiple unique angles the backend's reviews don't cover. |
| **3** | Social adds 1–2 unique angles AND amplifies confidence on existing claims. |
| **2** | Social marginally amplifies existing claims; no new info. |
| **1** | Social is pure brand marketing or duplicate content. |

## 4. Recording sheet

Findings logged into `data/instagram_feasibility_findings.json` with this
schema (one entry per query):

```json
{
  "id": "frag-tomford-black-orchid",
  "category": "fragrances",
  "query": "Tom Ford Black Orchid",
  "tested_at": "YYYY-MM-DD",
  "tester": "<dispatcher_or_ahmed>",
  "instagram_brand_main": {
    "handle": "@tomfordbeauty",
    "posts_reviewed": 30,
    "unique_signals": ["..."],
    "notes": "..."
  },
  "instagram_influencers": [
    {"handle": "@bh_perfume_reviewer_1", "unique_signals": ["..."]},
    {"handle": "@bh_perfume_reviewer_2", "unique_signals": ["..."]},
    {"handle": "@bh_perfume_reviewer_3", "unique_signals": ["..."]}
  ],
  "tiktok": {
    "hashtag_reviewed": "#tomfordblackorchid",
    "posts_reviewed": 30,
    "unique_signals": ["..."]
  },
  "score": 4,
  "decision_rationale": "Wear-feel + GCC retailer availability surfaced uniquely; 4 angles total."
}
```

## 5. Helper script

`scripts/instagram_feasibility_test.py` provides:

- A CLI helper to walk the procedure interactively (records findings
  into the JSON file)
- A summariser that reads the findings file + emits the green-light
  decision per § 1 rule
- A guard that does NOT actually scrape Instagram (manual exercise) —
  only structures the human's observations

## 6. Decision capture

When all 5 queries are scored:

- If ≥3 queries score ≥3 → **Green-light**: add Apify integration to
  Bundle B.4 backlog with a $0.005/comparison budget cap + circuit
  breaker after 3 consecutive failures.
- Otherwise → **Cut**: amend `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 10 with the test
  results and remove Instagram/TikTok from B.4 scope. Re-allocate the
  saved budget to Fragrantica / PubMed deeper coverage.

The decision update is committed to design § 10 as the last step of
L4.4.

## 7. Carry-over from L4.4 to (B)

Even if the test green-lights social integration, B.4 must address:

1. **Privacy / ToS** — Apify's GCC-targeted scraping may need explicit
   user consent before posting account-level inferences.
2. **Refresh cadence** — social signals decay; cache TTL ≤ 24h for IG
   posts vs 7d for static brand info.
3. **De-duplication** — same review reposted on YouTube + Instagram +
   TikTok should not count as 3 independent signals.

These items are out of scope for A.4 (this feasibility test) — they
move into B.4 backlog only if we green-light.

## 8. Execution timeline

A.4 is a 1-day spike at the END of Sprint A — after L4.1/L4.2/L4.3 ship,
before the cross-QA merge gate. If Ahmed executes the manual exercise,
the dispatcher can run the summariser in ~30 seconds; if Ahmed defers
the manual exercise to (B), the design doc § 10 carries a TODO marker
and B.4 starts with the test unfinished.

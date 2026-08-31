# Ahmed unblock pack — 2026-08-31

Everything on this list is Ahmed-only (account signups, payments, product decisions). Each item:
**WHY** (one line) / **DO** (numbered steps) / **UNBLOCKS** (one line). Items 6-7 need no action.

Companion references: activation order = `CLAUDE.md` → **ACTIVATION-ORDER runbook** (Environment
Variables section); prod base = `https://web-production-58776.up.railway.app`.

---

## 1. OpenAI credits → step-1 canary GO

**WHY:** OpenAI returns 429 on every call — no compare completes properly, and no flag canary is
readable until the LLM path is alive.

**DO (the moment credits land):**
1. Top up at platform.openai.com → Settings → Billing (enable auto-recharge if you want this to
   stay fixed). Confirm the topped-up org/project owns the key that Railway's `OPENAI_API_KEY` uses.
2. Smoke test (no flag flips yet):
   `curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"`
   → expect a full comparison JSON; Railway logs must show no 429.
3. Flip the **step-1 additive-capture family** in Railway (web service → Variables), all seven together:
   - `ENABLE_EXTRACTOR_FIXES_2608=true`
   - `ENABLE_RSC_FLIGHT_PRICE=true`
   - `ENABLE_MAGENTO_GQL_ADAPTER=true`
   - `ENABLE_SALLA_SLUG_RESOLVE=true`
   - `ENABLE_NOT_A_PDP_FILTER=true`
   - `ENABLE_WALL_SIGNATURE_ANCHOR=true`
   - `ENABLE_UCP_JSON_PRICE=true`

   These are all "fire only where today's path returns nothing" rungs — safe to batch as ONE step.
   Do NOT touch any other flag: `ENABLE_VISIBLE_TEXT_CURRENCY` needs its own window,
   `ENABLE_SPECS_NO_FABRICATION` needs a working search layer (Serper is still 403), and the
   sitemap/spine/descriptor flags have seed preconditions. Steps 2-7 of the ACTIVATION-ORDER
   runbook stay parked.
4. Run the canary compares (one per adapter — all `nocache=true`):

   | Flag | Canary compare | Watch for |
   |---|---|---|
   | `ENABLE_MAGENTO_GQL_ADAPTER` | `q=YSL Black Opium Eau de Parfum 90ml vs Lancome La Vie Est Belle EDP 100ml&region=bahrain` → klinq.com (Cloudflare-walled HTML, GQL side-door; measured BHD 48.13/53.44) | log `[MAGENTO] <method> BHD <amount> for '...' (klinq.com)`; failures log `[MAGENTO] graphql HTTP ...` / `[MAGENTO] ... configs HTTP ...` |
   | `ENABLE_SALLA_SLUG_RESOLVE` | `q=Abdul Samad Al Qurashi Al Qurashi Blend Perfume 90ml vs Ajmal Amber Wood 100ml&region=kuwait` → the kw.abdulsamadalqurashi.com homepage-collapse host | log `[PRICE] salla slug-collapse for '...' @ <host> -> search-resolve` then `[PRICE] salla genuine|converted: <ccy> <amt> ...` |
   | `ENABLE_UCP_JSON_PRICE` (+ `ENABLE_WALL_SIGNATURE_ANCHOR` rides the same host) | `q=Swiss Arabian Oud Malaki 100ml Eau de Parfum vs Swiss Arabian Shaghaf Oud 75ml&region=oman` → om.swissarabian.com (measured 17.200 OMR, merchant-stated currency) | response price carries `source_method: "shopify_json"`; failures log `[UCP_JSON] ...`. Wall-anchor success = this host is no longer misclassified as walled (it was the JS-comment "access denied" false positive) |
   | `ENABLE_NOT_A_PDP_FILTER` | rides any of the above compares (fires on homepage/search redirects, offsite redirects, CollectionPage shells) | log `[PRICE] <domain> is NOT a product page (<reason>) — not priced, not a render candidate`; errors log `[PRICE] classify_not_a_pdp failed for ...` (fail-open) |
   | `ENABLE_EXTRACTOR_FIXES_2608` | no GCC-reachable positive-fire host (measured hosts: parfumdo.com, aromas.es, beirutdutyfree.com — global corpus). Zero-network parse fixes, already corpus-proven offline. Treat as a no-regression flip | no dedicated log line; judge by "no new failures" on the other canaries |
   | `ENABLE_RSC_FLIGHT_PRICE` | positive fire needs sephora.com.tr (Armani Si 5050 TRY / Bleu de Chanel 8400 / Kayali 2090 — measured), which a GCC-region compare won't select. Treat as a no-regression flip | no dedicated log line; if it ever fires, the price row carries `source_method: "page_scrape"` on a `__next_f` (Next.js) page |

5. Read logs: `railway logs` in a terminal, or Railway dashboard → web service → Deployments →
   View logs. Grep strings: `[MAGENTO]`, `[PRICE] salla`, `NOT a product page`, `[UCP_JSON]`.
6. **Rollback (per flag):** set the variable to `false` (or delete it) in Railway. Every flag is
   read per-call via `os.getenv` — no restart, no redeploy dance; the OFF path is byte-identical
   to pre-wave behavior.

**UNBLOCKS:** ACTIVATION-ORDER step (1) — the entire dark M5+M9/M10 additive price-capture family
goes live; steps 2-7 queue behind it.

---

## 2. Firecrawl top-up

**WHY:** 447/450 lifetime credits used, 3 left — the account is effectively dead, and the #92
rawHtml fix has never been validated live.

**DO:**
1. Go to firecrawl.dev → dashboard → billing. Current plans (verified 2026-08-31 on
   firecrawl.dev/pricing): Free $0/1,000 credits/mo · **Hobby $16/mo/5,000** · Standard
   $83/mo/100,000 · Growth $333/mo/500,000 · Scale $599/mo/1,000,000. Scrape = 1 credit/page.
   One-time top-ups exist: **$5 batches** (1,000 credits on Hobby tier), auto-reload optional.
2. Cheapest sufficient move: Hobby for one month, or a single $5 batch if the account tier allows
   it. The re-bake needs ≤ 15 credits — anything you buy covers it many times over.
3. Tell the next Claude session it's done. (Dev-side follow-up, not yours: the app's own budget
   gate latches at 450 lifetime — Redis keys `budget:firecrawl:lifetime` and
   `budget:firecrawl:burn_alert_fired:budget:firecrawl:lifetime` must be reset after the top-up,
   same playbook as the Serper rotation.)

**UNBLOCKS:** the #92 rawHtml 9-target live re-bake (budgeted ≤ 15 credits) — proves the
`ENABLE_FIRECRAWL_RAW_HTML` repair (0/9 → priced) against live Firecrawl instead of cached bytes.

---

## 3. Awin + CJ publisher signups

**WHY:** B7 verdict — the only two affiliate networks worth filing now: free, abandonable, and
they hold the EU/global advertiser option value (fragrance retailers we already price).

**DO — Awin (~10 min):**
1. Sign up at awin.com (publisher signup; US entry: awin.com/us → Publishers → Sign up).
2. Have ready: your promotional property (the Qaren app / qaren website URL or an app-store
   listing; social channels also accepted), a one-line description of how you promote, and a
   payment card for the **$5 refundable deposit** (identity/bank verification; returned with your
   first commission payment, refunded if declined).
3. Expected approval: ~2 working days (Awin publisher success team review).

**DO — CJ Affiliate (~10 min):**
1. Sign up at **signup.cj.com/member/signup/publisher/** (or cj.com/join → publisher).
2. Requirements are light: 18+, a live promotional property (website/app listing). No deposit.
3. Network account approval is quick; each **advertiser** is then applied to individually and does
   its own review (days, varies). Note: accounts with zero activity for ~6 months can be
   deactivated — file it and forget it is fine, just expect to re-verify later.

**UNBLOCKS:** monetization option value on EU/global fragrance advertisers — zero code depends on
this today, so it can sit idle once approved.

---

## 4. ArabClicks (+ Boostiny / Hareer Deals as alternates)

**WHY:** ArabClicks is the only network with real GCC-fragrance-advertiser overlap — it carries
noon, Namshi, Ounass, and GoldenScent programs, i.e. the exact hosts already in our registry.

**DO:**
1. Primary: sign up free at **arabclicks.com/signup** (publisher/affiliate account). They accept
   website publishers AND app/social publishers; free, no cost to join. Have the Qaren property
   description ready as in item 3.
2. After approval, request the noon / Namshi / Ounass / GoldenScent programs from their advertiser
   directory.
3. Alternates (only if ArabClicks stalls): **Boostiny** (boostiny.com — GCC performance network,
   publisher signup via their site/contact) and **Hareer Deals** (hareerdeals.com/en — free Arabic
   GCC affiliate network, fashion/shopping advertisers, pays via bank/PayPal).

**UNBLOCKS:** GCC affiliate revenue on the retailers we already send users to; also cleaner ToS
posture (affiliate links instead of bare outbound links).

---

## 5. Spec licensing contacts (ONLY if spec-spine seeding plateaus later)

**WHY:** The measured ceiling on notes/longevity (~38%/32%) is a data-licensing problem, not a
scraping problem — Fragrantica/Parfumo are robots-banned for us by name, so the legal paths are
Michael Edwards' Fragrances of the World (~36k+ fragrances, has launch_year + perfumer + note
pyramid) and a written Fragrantica license. **Do not send these yet** — only when the free
spec-spine seeding (M7) plateaus.

**DO — Fragrances of the World:**
1. Open **fragrancesoftheworld.com/Contact** → contact form, category "Industry". (Phone:
   +61 2 9546 2951; Paris studio: 21 rue de l'Hirondelle 75006 Paris; mail: PO Box 3014,
   Blakehurst Sydney NSW 2221, Australia.)
2. Paste:

> **Subject: Data licensing inquiry — GCC product-comparison app (Qaren)**
>
> Dear Fragrances of the World team,
>
> I'm the founder of Qaren, a bilingual Arabic/English product-comparison app serving the Gulf
> (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). Fragrance is one of our nine product
> categories, and we would like to license accurate fragrance metadata — family and note
> classification, launch year, and perfumer — rather than rely on scraping or AI inference.
>
> Could you share your data-licensing options and indicative pricing for in-app/API use of the
> Fragrances of the World database? Our initial need is read access for a few thousand fragrances
> sold at GCC retail, displayed with attribution. We are happy to sign an evaluation NDA or start
> with a small paid pilot.
>
> Best regards,
> Ahmed — Founder, Qaren
> [your contact email]

**DO — Fragrantica:**
1. Open **fragrantica.com/terms-of-service.phtml** yourself (our agents are barred from fetching
   fragrantica.com — their robots.txt disallows Claude agents by name). The ToS names the written
   "Commercial License / Data License" path and lists the licensing contact email; their postal
   contact is FRAGRANTICA, 3830 Valley Centre Dr Suite 705-123, San Diego, CA 92130, USA,
   +1-858-876-2290.
2. Paste:

> **Subject: Written Data License inquiry — Qaren (GCC comparison app)**
>
> Hello,
>
> I'm the founder of Qaren, a product-comparison app for the Gulf region. Per your Terms of
> Service, commercial use of Fragrantica content requires a written Commercial License / Data
> License, and we would like to do this properly — we are explicitly not scraping the site.
>
> We are interested in licensing a limited set of fragrance metadata (note pyramids, main accords,
> launch year, perfumer) for in-app display with attribution and links back to Fragrantica. Could
> you tell me who handles Data License agreements, what scopes you offer, and indicative pricing?
>
> Best regards,
> Ahmed — Founder, Qaren
> [your contact email]

**UNBLOCKS:** the spec-spine ceiling — licensed notes/longevity/perfumer data for the ~62% of pages
where scraping can never provide it.

---

## 6. Already done today — cross these off

- **Egress-probe Railway service: DELETED 2026-08-31.** (The dead probe service from the egress
  measurement run is gone from the dashboard.)
- **Bright Data: CONFIRMED LIVE in prod.** ~10 queries per cold lookup; the 5k/mo free tier ≈ 500
  cold lookups/month. Nothing for you to do.

---

## 7. Still parked — NO action needed

- **Serper 403** — stays dead by choice; Bright Data fallback covers discovery. Rotate only when
  we decide search matters again (`ENABLE_SPECS_NO_FABRICATION` waits on it).
- **scentsplit decision** — settled: decant price for decant queries. No further input needed.

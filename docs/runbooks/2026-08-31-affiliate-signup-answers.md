# Affiliate Network Signup — Answer Dossier (Awin / CJ / ArabClicks)

**Date researched:** 2026-08-31 (all fields enumerated from the live public signup pages + each network's own help-center docs on this date).
**Who signs up:** Ahmed, personally. Claude is policy-barred from creating accounts, entering credentials, or accepting terms — this doc exists so each signup is a five-minute paste job.
**What we are:** Qaren (Arabic **قارن**, "compare") — a bilingual Arabic/English product-comparison app for the GCC (BH / SA / AE / KW / QA / OM). Pre-launch: iOS build in TestFlight internal testing; public App Store / Google Play launch pending. Companion site: `https://qaren.app`. Backend: `web-production-58776.up.railway.app`. First categories: fragrance & beauty, expanding to electronics, supplements, and fashion (as stated on the landing page).
**Why affiliate networks:** every Qaren comparison result links out to the retailer's product page. Affiliate links replace those bare outbound links — same UX, tracked revenue.

---

## Pre-flight (do BEFORE submitting any application)

1. **Put the landing page live at `https://qaren.app`.** It is built (`landing/`, per `landing/README.md`) but **not yet deployed to the domain**. Network compliance teams visit the URL you give them; an empty or parked domain is the #1 rejection reason. Deploy per `docs/runbooks/bundle-d-dns-and-hosting.md` / `landing/README.md` first.
2. **Have a reachable email.** Use your personal email or a working `@qaren.app` mailbox — the `support@`/`legal@`/`privacy@qaren.app` addresses are referenced by the legal docs but were still on your A7 ask list; only give an address that actually receives mail.
3. **Card ready for Awin** — the last Awin step takes a one-time ~5 GBP/USD verification deposit on a credit/debit card (refunded — see below).
4. **Do not inflate traffic.** All three networks reject inflated claims and all our answers below state pre-launch status honestly. Approval with honest answers is common; getting caught claiming fake traffic is a ban.

Reusable one-liner (several forms ask "describe your business" in some form):

> Qaren (Arabic: قارن, "compare") is a bilingual Arabic/English product-comparison app for the GCC (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). Users search a product — fragrance and beauty first — and get a side-by-side comparison of prices, specs, and reviews from regional retailers, with outbound links to buy directly from the retailer. Currently pre-launch (iOS in TestFlight internal testing ahead of a public App Store / Google Play release); joining the network now so retailer links are affiliate-tracked from day one.

---

## 1) Awin

**Signup URL:** https://ui.awin.com/publisher-signup/en/awin/step1
(Reachable from awin.com → Publishers → Sign up. The wizard has 4 steps shown in the page header: **Account Setup → Promotional Type → Promotional Space → Verification**. Step 1 was enumerated live in the browser; steps 2–4 are gated behind step 1, so their fields come from Awin's own Partner Success Center articles "How do I join Awin as a Publisher?" and "How to set your promotional type", plus Awin's compliance page "Application process & joining fee".)

### Step 1 — Account Setup (fields verbatim from the live form)

| Field | Paste this |
|---|---|
| Company Name | [AHMED: registered company name if you have one; the form's own helper says if your publisher business is a registered company enter that name, otherwise leave as your personal/trading name — "Qaren" is fine if unregistered] |
| Tax Residency (dropdown) | [AHMED: your tax residency — "Bahrain" is in the list] |
| First Name | [AHMED: first name as on ID] |
| Last Name | [AHMED: last name as on ID] |
| Email | [AHMED: your login email — this becomes your Awin login] |
| Confirm Email | (same) |
| Password / Confirm Password | [AHMED: new password] |
| reCAPTCHA | Solve it yourself (human-only) |

### Step 2 — Promotional Type

| Field | Paste this |
|---|---|
| Primary region | [AHMED: pick your GCC market if offered (Bahrain / UAE / Saudi Arabia); if no Gulf option exists, pick the region where your target advertiser programmes run — this is only used for directory matching. This dropdown is behind step 1 so its exact options could not be enumerated pre-account.] |
| Promotional type (multiple allowed; ONE primary subcategory) | **Content → Comparison engine** — Awin's own definition: "Tools comparing product prices and features across online stores." That is Qaren, verbatim. Optionally also tick Content → Content creators & influencers if you'll promote on social. |

> **Warning (from Awin's docs):** "Your promotional type is set during registration and cannot be changed later due to compliance requirements." Pick **Comparison engine** as primary — do not improvise here.

### Step 3 — Promotional Space

| Field | Paste this |
|---|---|
| Promotional Space URL | `https://qaren.app` |
| Description | Qaren (Arabic: قارن, "compare") is a bilingual Arabic/English product-comparison app for the GCC — Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, and Oman. Users search a product, fragrance and beauty first, and get a side-by-side comparison of prices, specs, and reviews from regional retailers; every result links out to the retailer's own product page to complete the purchase. Status: pre-launch — the iOS app is in TestFlight internal testing ahead of a public App Store and Google Play release, and qaren.app is the companion site. We are joining Awin now so retailer links are affiliate-tracked from day one. We make no traffic claims yet; initial volume will come from our GCC launch marketing (paid social and an in-app referral programme). Promotion method: in-app price-comparison results with outbound retailer links — no coupon scraping, no paid-search brand bidding, no toolbar/extension. |
| Sectors (multi-select list) | Pick the closest matches to: **Health & Beauty** (fragrance/beauty is category #1), plus **Retail / Shopping**, **Fashion**, **Consumer Electronics** if offered. (List is behind login; choose sectors matching fragrance, beauty, and general retail.) |

### Step 4 — Verification (T&Cs + card deposit)

| Field | Paste this |
|---|---|
| Newsletter opt-in checkbox | Your choice (not required) |
| Terms & conditions checkbox | [AHMED: read + accept yourself — required to join] |
| Verification payment (credit/debit card) | [AHMED: your card — Awin charges a one-time ~£5/$5 deposit as identity verification. Per Awin's compliance page: it is credited to your publisher account and reimbursed with your first commission payment, and refunded on request if the application is declined or you close the account first.] |
| Submit | Click **Join Our Network** |

**After approval:** log in to the Awin dashboard → Advertisers → join advertiser programmes individually (each advertiser approves you separately). Search for GCC-relevant retail/beauty programmes first.

---

## 2) CJ Affiliate

**Signup URL:** https://signup.cj.com/member/signup/publisher/ (redirects to https://public.cj.com/signup/publisher)

The public page is a short credentials form ("Get started by verifying your email" — enumerated live in the browser). Everything else happens **after** you click the verification link in your email, inside members.cj.com. Post-verification steps below are from CJ's documented publisher-onboarding checklist: user info → network profile → promotional property → company details → tax → payment → screener questions.

### Phase A — Public signup form (live-verified)

| Field | Paste this |
|---|---|
| Language (dropdown) | English |
| Country (dropdown) | [AHMED: your country of residence — Bahrain] |
| Email | [AHMED: your email] |
| Password / Confirm Password | [AHMED: new password] |
| reCAPTCHA | Solve it yourself |
| Submit | Then open the verification email → click **Create My CJ Publisher Account** |

### Phase B — Agreements (first login)

| Field | Paste this |
|---|---|
| Age / authority checkboxes | [AHMED: confirm yourself] |
| Publisher Service Agreement, Software Policy, Privacy Policy | [AHMED: read + accept yourself — required] |

### Phase C — Account completion (inside the dashboard)

**C1. User Information**

| Field | Paste this |
|---|---|
| First Name / Last Name | [AHMED: as on ID] |
| Phone | [AHMED: your phone, international format e.g. +973…] |
| Email / User Type | Prefilled — leave as-is |

**C2. Network Profile — description (250–4,000 characters)**

| Field | Paste this |
|---|---|
| Description | Qaren (Arabic: قارن, "compare") is a bilingual Arabic/English product-comparison app for the Gulf (GCC) markets: Bahrain, Saudi Arabia, the UAE, Kuwait, Qatar, and Oman. Users search a product — our launch categories are fragrance and beauty, expanding into electronics, supplements, and fashion — and Qaren returns a side-by-side comparison of prices, specifications, and review signals from regional online retailers. Every comparison result links out to the retailer's own product page; the user always completes the purchase on the retailer's site. Affiliate links will replace our existing plain outbound links, so advertiser tracking is native to the product rather than bolted on. Current status, stated plainly: we are pre-launch. The iOS app is in TestFlight internal testing ahead of a public App Store and Google Play release, and https://qaren.app is our companion site. We make no traffic claims today. Initial volume will come from GCC launch marketing (paid social campaigns and an in-app referral programme), concentrated in high-purchasing-power Gulf markets that are underserved by Arabic-first comparison tools. Promotion methods: in-app product-comparison listings with direct outbound retailer links. We do not run coupon/deal scraping, paid-search brand bidding, toolbars, or browser extensions. Our goal is long-term, compliant partnerships with GCC-relevant advertisers from day one of public launch. |

**C3. Promotional Property**

| Field | Paste this |
|---|---|
| Property Type | **Mobile App** (Website / Social / Email / Mobile App / Browser Extension / Paid Display Ads / Paid Search are the options). If the Mobile App option demands a live app-store listing pre-launch, register `https://qaren.app` as a **Website** property now and add the Mobile App property at launch. |
| URL | `https://qaren.app` |
| Promotional model | **Product Comparison** (it is an explicit option in CJ's list) |
| Property name | Qaren — GCC price comparison |
| Tags / keywords | price comparison, product comparison, GCC, Gulf, Middle East, Arabic, fragrance, beauty, perfume, shopping |

**C4. Company Details**

| Field | Paste this |
|---|---|
| Organization Name | [AHMED: legal entity name, or your personal name if unregistered] |
| Address / City / State / Postal Code / Country | [AHMED: your address] |
| Phone | [AHMED: your phone] |
| Fax | Leave blank |
| Functional Currency | USD |
| Language | English |
| Date Format | Your preference |

**C5. Tax Information**

| Field | Paste this |
|---|---|
| Tax document | [AHMED: as a non-US publisher this will be a W-8 series form (W-8BEN as an individual / W-8BEN-E as an entity) or CJ's "Certificate of No US Activities" if you have no US-based operations — pick what matches your situation; the form self-guides once Country=Bahrain is set] |
| Payee Name + Signature | [AHMED: yours] |

**C6. Payment Information**

| Field | Paste this |
|---|---|
| Minimum payment threshold | $50 (the minimum — raise later if you prefer fewer payouts) |
| Currency | USD |
| Bank details | [AHMED: bank account — for a Bahrain account CJ will ask for the international details (IBAN/SWIFT) it supports for your country; Payoneer is the common fallback if direct deposit to BH is unavailable] |

**C7. Screener questionnaire (four yes/no questions)**

| Question (paraphrased from CJ's checklist) | Paste this |
|---|---|
| Do you operate a network / sub-network of publishers? | No |
| Do you operate a browser extension? | No |
| Are you an agency representing other parties? | No |
| Do you have a rate card / charge placement fees? | No |

**After approval:** CJ has no network-wide approval to promote — apply **per-advertiser** from the dashboard (Advertisers → search → Apply to Program). Each advertiser reviews your Network Profile, so C2's honesty matters.

---

## 3) ArabClicks

**Signup URL:** https://www.arabclicks.com/signup

> **STATUS FLAG (verified live 2026-08-31):** the signup page currently shows **"Affiliate Waitlist — We're currently not accepting new affiliates."** The form below is the **waitlist** form; ArabClicks says they'll notify you "if your channel meets our requirements ... when registration opens up." Fill it now anyway (it's the same channel data a real application needs), and treat Awin + CJ as the near-term paths. ArabClicks explicitly accepts app and social publishers — "Mobile App" is a first-class channel option.

All fields below were enumerated from the live form (single page, `*` = required):

| Field | Paste this |
|---|---|
| First Name | [AHMED: first name] |
| Last Name | [AHMED: last name] |
| Email | [AHMED: your email] |
| Phone | [AHMED: your phone, international format] |
| Preferred Language (dropdown) | English (or Arabic — your choice; both offered) |
| Country (dropdown) | [AHMED: Bahrain] |
| Which of your channels has the most followers? (dropdown: Website, Blog, Mobile App, Paid Campaigns, Instagram, YouTube, Facebook Profile/Page, Facebook Community, Twitter, SnapChat, TikTok, Whatsapp, Telegram, Email List, Community Forums, Programmatic Advertising, Native Advertising, Cashback/Loyalty, Other) | **Mobile App** |
| Where do you run your paid promotions? (dropdown: Ad Network, Push Notifications, Social Media Campaigns, Google Search, Google Display, Others) | **Social Media Campaigns** (matches the planned paid-social launch marketing) |
| Please add your web/social channel URL | `https://qaren.app` |
| Snapchat story screenshot upload | Skip — this upload sits in the form for Snapchat-channel applicants (it asks for a recent story showing follower count). With channel = Mobile App it should not apply; do not fabricate one. |
| Current Monthly Unique Visitors (0–1,000 / 1,000–10,000 / 10,000–100,000 / 100k+) | **0–1,000** (honest: pre-launch) |
| How long have you worked as an affiliate? (No experience / Less than a year / 1–3 years / 3–5 years / 5+ years) | [AHMED: honest answer — "No experience" or "Less than a year" unless you've done affiliate work before] |
| "I agree to ArabClicks …" terms checkbox | [AHMED: read + accept yourself] |
| Second consent checkbox (data processing/marketing) | [AHMED: accept yourself] |
| Submit | **Join the Waitlist** |

There is no free-text description field on this form — the URL is your pitch, which is one more reason the landing page must be live at `qaren.app` before submitting (pre-flight #1).

**After approval:** once off the waitlist and inside the ArabClicks dashboard, request access to the GCC advertiser offers we actually link to — **noon, Namshi, Ounass, GoldenScent** — via the offers directory / your account manager.

---

## Sources

- Awin signup step 1: live form at `ui.awin.com/publisher-signup/en/awin/step1` (browser-verified 2026-08-31).
- Awin steps 2–4: Awin Partner Success Center — "How do I join Awin as a Publisher?" and "How to set your promotional type" (success.awin.com); deposit: awin.com "Compliance: Awin's application process & joining fee".
- CJ phase A: live form at `public.cj.com/signup/publisher` (browser-verified 2026-08-31); phases B–C: CJ publisher-onboarding checklist as documented in CJ support material and current third-party walkthroughs of the members.cj.com flow (field lists cross-checked across two independent 2026-current walkthroughs).
- ArabClicks: live form at `arabclicks.com/signup` (browser-verified 2026-08-31, including the waitlist banner).
- Qaren facts: this repo — `CLAUDE.md` (product + GCC scope + TestFlight status), `landing/README.md` (site built, **not yet live** on qaren.app), `landing/index.html` (categories line), `app/main.py` (backend URL).

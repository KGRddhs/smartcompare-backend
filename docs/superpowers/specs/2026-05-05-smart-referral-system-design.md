# Smart Decision Referral System — Design

**Date:** 2026-05-05
**Status:** Approved (brainstorming complete; ready for writing-plans)
**Author:** Brainstormed with Claude
**Owner:** Ahmed
**Source PDF:** `Qaren_AI_Smart_Referral_System_For_Decision_Making.pdf` (13 psychology principles)
**Related sessions:** Session 39 (freemium tiers), Session 41 (cohort personalization), Session 38 (security hardening)

---

## Executive Summary

Build a virality-optimized referral system grounded in 13 documented psychology principles (regret reduction, social currency, reciprocity, ease, curiosity, gradual commitment, value-tied rewards, trust, honest scarcity, social proof, story framing, habit formation, Hooked-model fit). The system has two intentional loops:

- **Loop 1 (Share moment, drive-by-friendly):** Tapping Share fires immediately. Referrer gets one **Deep Review Mode credit** (next comparison fetches 8-10 review snippets instead of 4 — same gpt-4o-mini, just deeper context). Drive-by users (1-5 comparisons then leave) are rewarded *now*, not later.
- **Loop 2 (Conversion, sticky-user reward):** When the invitee completes their first real comparison (>30s, signed in), referrer gets +5 comparisons added to that month's cap (Free tier) or +10 (Premium tier). Invitee also gets +5 + 1 Deep Review credit as their welcome carrot.

**Reward cap:** 3 successful invites per week framed as *"You have 3 Premium gifts to send this week"* (PDF #9 — scarcity-as-currency, not deadline pressure). Maximum 15/month bonus comparisons (30 for Premium subscribers).

**Anti-cannibalization design:** capacity bumps (not Premium-tier extensions). A free user with +15 comparisons still has Free-tier limits to hit; Premium remains the unlimited choice. Referral bonuses *fuel* Premium conversion ("Premium gets 4× the bonus per invite"), they don't replace it.

**Drive-by re-engagement (replaces price-drop notifications):** A single push pipeline picks the most relevant content type per user per week — Decision Insight (sentiment shift on saved product), Cohort Curiosity (peer divergence in same governorate), Decision Retrospective (14-day "how'd it work out?"). Max 1/week per user. No price-drop spam. Reuses Session 41 cohort tables.

**Cost framing:** marginal cost per redemption is ~$0.01-0.04 with OpenAI data sharing on (Ahmed already enrolled, $5 free credit untouched is the live proof). Compared to typical paid-ads CAC of $1-10, the system is 30-1000× more efficient per acquired user.

**Model strategy (applies to ALL comparisons, not just referrals):** Hybrid per-call routing — `gpt-4o` for verdict generation (highest-impact subjective prose, ~6.5K tokens/comparison), `gpt-4o-mini` for everything else (parsing, specs, prices, reviews, ~18.5K tokens). Switch verdict to mini at 80% of daily 4o cap. ~440 free comparisons/day total under data-sharing caps.

**MVP cut:** **C — Maximum impact v1**. Includes core referral, Loop 1 perk, privacy toggles, curiosity quiz for invitees, admin dashboards (referrals + costs), and the 3-type re-engagement push system.

**Out of scope (deferred to v1.1+):** vanity referral codes (Premium-gated), soft phone verification (added if abuse data shows need), graph-cycle detection for collusion rings.

---

## 1. Architecture Overview

```
[REFERRER FLOW]
  Comparison completed → Result rendered
                      ↓
       Result-aware CTA (PDF #14):
         strong / close / saved variants
                      ↓
            Tap "Share" button
                      ↓
       Bottom sheet:
         • Privacy toggles (name/result/reasons; budget locked off)
         • Pre-filled message (story format, PDF #11)
         • Targets: WhatsApp / Copy / X / Telegram / Snapchat
                      ↓
       POST /api/v1/referrals/share
                      ↓
       referral_invites row inserted (Loop 1 trigger)
       deep_review_credits row granted (referrer)
       Toast: "🎁 Your next comparison gets Deep Review Mode"
       Counter: "2 of 3 gifts this week"

[INVITEE FLOW]
  Tap link in WhatsApp/X/etc → qaren.app/c/{share_token}?ref={code}
                      ↓
     Web page (or deep-link to app if installed)
                      ↓
       Curiosity landing (PDF #5):
         "[Friend] was torn between [A] and [B] — picked [B].
          Your answer doesn't have to be his. Answer 4 questions."
                      ↓
       4-question quiz (reuses onboarding logic):
         priority / budget / brand-attitude / non-negotiable
                      ↓
       Personal result rendered (NO AUTH YET — PDF #6)
       Could differ from referrer's pick
                      ↓
       Soft signup CTA:
         "Save this + get a free Deep Review credit"
                      ↓
       Signup (Apple / Google / Email)
                      ↓
       Backend links comparison → referral_invites.invitee_first_comparison_id
       Anti-abuse checks (device, email, real-action)
                      ↓
       LOOP 2 FIRES:
         • referral_redemptions row inserted
         • users.referral_bonus_comparisons_this_month += 5 (or 10 if Premium)
         • deep_review_credits row granted (invitee)
         • Push to referrer: "Sarah decided thanks to you. +5 comparisons added."

[RE-ENGAGEMENT FLOW]
  Daily cron (3am GCC time) — Railway scheduler or Supabase Edge function
                      ↓
  For each user with notifications enabled + saved comparison in last 60d:
                      ↓
       Selector logic (max 1/week/user):
         IF saved-product sentiment shifted ≥10% → Decision Insight
         ELIF ≥5 same-governorate users picked differently → Cohort Curiosity
         ELIF 14d since their last comparison → Decision Retrospective
         ELSE skip
                      ↓
       re_engagement_events row inserted
                      ↓
       Expo Push dispatched
                      ↓
       Push opened → deep link to relevant screen → re-engagement
```

### New code (high-level)

1. `migrations/014_referral_system.sql` — 4 new tables + user-column additions
2. `app/api/referral_routes.py` — `POST /share`, `GET /status`, `GET /invite/{token}`, `POST /invite/{token}/quiz`, `POST /invite/{token}/redeem`
3. `app/services/referral_service.py` — invite creation, code generation, weekly cap, Loop 1/2 triggers
4. `app/services/abuse_detection_service.py` — device fingerprint, disposable email, real-action gate
5. `app/services/reengagement_service.py` — daily cron, 3 detectors, push dispatcher
6. `app/services/model_router_service.py` — hybrid per-call model selection (4o vs mini, Redis token counter)
7. `app/static/admin/referrals.html` + `costs.html` — Chart.js dashboards mirroring `/admin/cohort.html`
8. Frontend new screens/components:
   - `ReferralLandingScreen.tsx` — invitee web/deep-link entry
   - `InviteeQuizScreen.tsx` — 4-question quiz reusing onboarding
   - `ShareBottomSheet.tsx` — privacy toggles + targets + pre-filled message
   - `ReferralStatusCard.tsx` — Profile screen "Your gifts this week" card
9. `tests/test_referral_service.py`, `test_reengagement_service.py`, `test_abuse_detection.py`, `test_model_router.py`

### Existing code touched

- `app/main.py` — register referral routes; mount cron
- `app/api/auth_routes.py` — link invitee at signup; handle privacy toggle for AI sharing
- `app/services/usage_service.py` — read `referral_bonus_comparisons_this_month` in cap check
- `app/services/structured_comparison_service.py` — model_router integration; Loop 2 trigger after invitee's first comparison; Deep Review credit consumption
- `app/services/extraction_service.py` — Deep Review flag bumps `num_review_results` from 4 to 8-10
- `app/services/review_service.py` — accept `deep_mode` parameter
- `app/api/legal_routes.py` — T&C markdown updates (3 new sections)
- `app/api/admin_routes.py` — `/referrals/*` and `/costs/*` endpoints
- `SmartCompareApp/App.tsx` — deep link handler for `qaren.app/c/{token}?ref={code}`
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — result-aware share CTA
- `SmartCompareApp/src/screens/ProfileScreen.tsx` — referral status, AI sharing toggle, notification settings

---

## 2. Locked-In Decisions

| Area | Decision |
|---|---|
| Reward type | Capacity bump (Loop 2: +5 free / +10 Premium) + Deep Review Mode credit (Loop 1: 1 per share) |
| Weekly cap | 3 invites; framed as "3 gifts/week" (PDF #9) |
| Monthly cap | 15 referral comparisons (Free) / 30 (Premium) |
| Reward expiry | 30 days post-grant — keeps redemption pressure honest |
| Model strategy | Hybrid per-call: gpt-4o for verdict, gpt-4o-mini elsewhere; switch verdict to mini at 80% of daily 4o cap |
| OpenAI data sharing | Already enrolled (Ahmed confirmed); T&C disclosure + Profile opt-out toggle |
| Anti-abuse v1 | Device+email binding, disposable-email blocklist, real-action gate (>30s comparison) |
| Anti-abuse v2 | Soft phone verify deferred — add only if abuse data shows it's needed |
| Re-engagement | 3-type push system (Decision Insight / Cohort Curiosity / Decision Retrospective), max 1/week per user |
| Privacy defaults (PDF #8) | Show name=ON, show result=ON, show reasons=ON, show budget=NEVER (locked off) |
| MVP cut | C — Maximum impact v1 |
| Schema | 4 new tables + user columns; migration 014 via Supabase MCP `apply_migration` |
| Cost dashboard | New page at `/admin/costs.html`, mirrors cohort dashboard (Chart.js, X-Admin-Key auth) |
| Estimated duration | 3-4 weeks with 4-Opus-agent parallel team |

---

## 3. UX Flows + Copy

### 3.1 — Result-aware share CTAs (PDF #14)

| Context | EN | AR (Khaleeji) |
|---|---|---|
| Strong result | *"Confusion sorted. Know anyone agonizing over the same call?"* | *"خلصت من الحيرة. تعرف أحد قاعد يحاتي على نفس الاختيار؟"* |
| Close result | *"Razor-thin difference. Want a second pair of eyes?"* | *"الفرق رفيع. حسم القرار يحتاج عين ثانية."* |
| Saved result | *"You saved your call. How many friends deserve the same shortcut?"* | *"حفظت قرارك. كم واحد ثاني يستاهل نفس المختصر؟"* |

CTA selection logic (server-side, in comparison response):
- Strong = `confidence_score >= 0.75` AND `winner_margin >= 15%`
- Close = `winner_margin < 8%` OR multiple dimension-winners conflicting
- Saved = user previously tapped Save on this comparison
- Default = Strong

### 3.2 — Pre-filled share message (PDF #11 — story framing)

EN: *"I compared [Product A] and [Product B]. Picked [Product B] for my use. Try yours — your answer might differ: [link]"*

AR: *"قارنت بين [A] و[B]. اخترت [B] لاستخدامي. جرّب أنت — جوابك ممكن يختلف: [link]"*

Auto-localized to user's app language. The `[link]` is `qaren.app/c/{share_token}?ref={referrer_code}`.

### 3.3 — Privacy toggles bottom sheet (PDF #8)

| Toggle | Default | Locked |
|---|---|---|
| Show my name | ON | No |
| Show my result | ON | No |
| Show my reasons | ON | No |
| Show my budget | OFF | YES (cannot enable) |

Copy above the toggles: *"What we share when you send this. We never include your budget or personal answers."*

### 3.4 — Loop 1 reward toast (immediate, post-share)

EN: *"🎁 Thanks for sharing. Your next comparison goes 2× deeper on reviews."*
AR: *"🎁 شكراً للمشاركة. مقارنتك الجاية تدخل أعمق في المراجعات."*

Counter below: *"2 of 3 gifts this week"* / *"عندك 3 عطايا هالأسبوع — صرفت 1"*

### 3.5 — Invitee landing page

EN: *"Ahmed was torn between [A] and [B] — picked [B]. His answer doesn't have to be yours. Answer 4 questions, get yours."*

AR: *"أحمد كان محتار بين [A] و[B] — قرر [B]. لكن قراره لك ما يلزم يكون لك. جاوب 4 أسئلة، خذ توصيتك."*

Button: **Start my comparison** / **ابدأ مقارنتي**

NO signup required to enter the quiz (PDF #6 — gradual commitment).

### 3.6 — 4-question quiz

Reuses 4 of the 8 onboarding fields, picked for highest decision-relevance:
1. Priority (1 of 8 dimensions; cohort-derived options if cohort match exists)
2. Budget tier (budget / mid / premium)
3. Brand attitude (`trust_known_brands` / `open_to_emerging` / `value_first`)
4. Non-negotiable (free text or pre-set list per category)

After quiz → personalized result rendered immediately (no auth).

### 3.7 — Soft signup CTA (post-quiz)

EN: *"This is your result. Save it and get a free Deep Review credit since you came from a friend."*
AR: *"هذي نتيجتك أنت. احفظها وخذ مقارنة Deep Review مجانية لأنك دخلت من دعوة."*

Sign up via Apple / Google / Email → Loop 2 fires → push to referrer → invitee gets welcome credit.

### 3.8 — Loop 2 referrer push

EN: *"Sarah decided thanks to you. +5 comparisons added this month."*
AR: *"سارة قررت بفضلك. +5 مقارنات إضافية هذا الشهر."*

### 3.9 — Re-engagement push system

Selector logic (daily cron, max 1/week per user):

```
For user U with notifications_enabled AND saved_comparison in last 60d:
    last_push = max(re_engagement_events.triggered_at WHERE user_id = U)
    IF (now - last_push) < 7 days: skip

    IF any saved-product sentiment shifted ≥10% in last 7d:
        push_type = 'decision_insight'
    ELIF cohort_divergence(U.governorate, U.recent_comparisons) >= 5_users_40%:
        push_type = 'cohort_curiosity'
    ELIF any comparison.created_at == 14 days ago AND no retrospective sent:
        push_type = 'decision_retrospective'
    ELSE: skip

    Insert re_engagement_events row, dispatch via Expo Push
```

Push copy:

| Type | EN | AR |
|---|---|---|
| Decision Insight | *"[Product] update: new reviews shifted the picture. Re-check before buying."* | *"تحديث على [Product]: مراجعات جديدة، صورة جديدة. اعد الفحص قبل ما تشتري."* |
| Cohort Curiosity | *"5 people near you chose differently this week. Why?"* | *"5 ناس في [Capital] اختاروا غيرك على نفس المقارنة هالأسبوع. ليش؟"* |
| Decision Retrospective | *"14 days since your call. How'd [Product] turn out? Help the next person decide."* | *"مر 14 يوم على قرارك. كيف طلع [Product]؟ ساعد ناس ثاني محتارة."* |

Engineering note: Decision Insight detector reuses the existing review-fetch pipeline. Top-100 most-saved products globally are checked; per-user check skipped if user's product isn't in that top-100 set. Keeps Serper cost bounded.

---

## 4. Schema

Migration: `migrations/014_referral_system.sql`. Apply via Supabase MCP `apply_migration` (per Session 41 learning — SQL Editor wraps in single transaction and rolls back on view-level errors).

### 4.1 — `users` table extension

```sql
ALTER TABLE users ADD COLUMN referral_code TEXT UNIQUE;
ALTER TABLE users ADD COLUMN referral_bonus_comparisons_this_month INT DEFAULT 0;
ALTER TABLE users ADD COLUMN referral_bonus_reset_at TIMESTAMPTZ
    DEFAULT date_trunc('month', now()) + interval '1 month';
CREATE INDEX idx_users_referral_code ON users(referral_code);
```

`referral_code` format: 8-char `QR-XXXXXX` from base32 alphabet excluding ambiguous chars (no `0/O/1/I/l`). Generated lazily on first share. Premium subscribers can set vanity codes in v1.1.

`referral_bonus_comparisons_this_month` is read by `usage_service.py::check_usage_allowed()`:
```
effective_monthly_cap = base_cap (10 Free / 70 Premium) + referral_bonus_comparisons_this_month
```

Lazy reset: when `referral_bonus_reset_at < now()`, reset counter to 0 and update `reset_at`. No cron needed.

### 4.2 — `referral_invites`

```sql
CREATE TABLE referral_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  comparison_id UUID NOT NULL REFERENCES comparisons(id) ON DELETE CASCADE,
  share_target TEXT NOT NULL CHECK (share_target IN ('whatsapp','copy','x','telegram','snapchat','other')),
  device_fingerprint_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  first_viewed_at TIMESTAMPTZ,
  redeemed_at TIMESTAMPTZ,
  redeemed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  invitee_first_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  flagged_reason TEXT
);
CREATE INDEX idx_referral_invites_referrer_created ON referral_invites(referrer_user_id, created_at DESC);
CREATE INDEX idx_referral_invites_comparison ON referral_invites(comparison_id);
CREATE INDEX idx_referral_invites_redeemed_by ON referral_invites(redeemed_by_user_id);
```

Weekly cap query (no counter, computed dynamically):
```sql
SELECT count(*) FROM referral_invites
WHERE referrer_user_id = $1 AND created_at > now() - interval '7 days';
```

### 4.3 — `referral_redemptions`

```sql
CREATE TABLE referral_redemptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invite_id UUID NOT NULL UNIQUE REFERENCES referral_invites(id) ON DELETE CASCADE,
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invitee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  loop2_comparisons_granted INT NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_referral_redemptions_referrer ON referral_redemptions(referrer_user_id, created_at DESC);
```

`invite_id` UNIQUE prevents double-redeem. `loop2_comparisons_granted` is 5 for Free referrers, 10 for Premium.

### 4.4 — `deep_review_credits`

```sql
CREATE TABLE deep_review_credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('share_loop1','invitee_signup','manual')),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + interval '30 days',
  consumed_at TIMESTAMPTZ,
  consumed_in_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL
);
CREATE INDEX idx_deep_review_credits_user_available
  ON deep_review_credits(user_id, expires_at)
  WHERE consumed_at IS NULL;
```

Consumption is FIFO (oldest first) and atomic via `SELECT ... FOR UPDATE SKIP LOCKED`.

### 4.5 — `re_engagement_events`

```sql
CREATE TABLE re_engagement_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('decision_insight','cohort_curiosity','decision_retrospective')),
  comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  content_payload JSONB
);
CREATE INDEX idx_re_engagement_user_triggered ON re_engagement_events(user_id, triggered_at DESC);
```

`content_payload` stores localized title/body/deep-link so retries replay identical content.

### 4.6 — RLS policies (Session 38 pattern)

All 4 new tables: RLS enforced. User can SELECT their own rows (as referrer OR invitee). Admin role bypasses via service-role client. One public RPC:

```sql
CREATE FUNCTION resolve_referral_code(p_code TEXT)
RETURNS TABLE(user_id UUID, display_name TEXT) SECURITY DEFINER ...
```

Returns only the referrer's chosen display name (per their privacy toggle for `name`), nothing else. Used by invitee landing page resolution.

### 4.7 — Cascade behavior

Referrer deletes account (existing cascade from Session 38) → all `referral_invites` and `referral_redemptions` rows where they are referrer or invitee are deleted via FK cascade. Bonus comparisons already credited stay (irrevocable, fair to invitee).

---

## 5. Cost Model

### 5.1 — Per-comparison cost (data sharing ON, hybrid routing, 40% cache hit)

| Regime | Daily volume | LLM | Serper | Scrapers | Supabase | Redis | **Total** |
|---|---|---|---|---|---|---|---|
| Within 4o cap | 1-154/day | $0 | $0.0018 | $0.0001 | $0 | $0 | **$0.0019** |
| Within mini cap (verdict→mini) | 155-440/day | $0 | $0.0018 | $0.0001 | $0 | $0 | **$0.0019** |
| Over caps | 441+/day | $0.0066 | $0.0018 | $0.0001 | $0.0001 | $0.00007 | **$0.0086** |

Without data sharing, all comparisons cost ~$0.033 (5-17× more). The **untouched $5 OpenAI credit** is live proof data sharing is working.

### 5.2 — Monthly fixed costs

| Line | Cost | Trigger / Notes |
|---|---|---|
| Railway Hobby | $5 + ~$2-5 usage | Backend mostly idle between requests |
| Apple Developer | $8.25/mo ($99/yr) | Annual, due Sep 2026 |
| Domain (qaren.app) | ~$1.50/mo ($18/yr) | Annual |
| Supabase Free → Pro | $0 → $25 | Crosses to Pro at ~5K comparisons/day |
| Upstash Redis Free → PAYG | $0 → $5-30 | Crosses at ~800 comparisons/day |
| Sentry Free | $0 | 5K errors/mo |
| **Total at low volume** | **~$15/mo** | |

### 5.3 — Scaling scenarios

| Daily comparisons | Free | Paid | Variable | Fixed | **Monthly** | **Per comp** |
|---|---|---|---|---|---|---|
| 100 | 100 | 0 | $5.7 | $15 | **~$21** | $0.007 |
| 500 | 440 | 60 | $40 | $15 | **~$55** | $0.0037 |
| 1,000 | 440 | 560 | $169 | $15 | **~$184** | $0.0061 |
| 5,000 | 440 | 4,560 | $1,202 | $60 | **~$1,260** | $0.0084 |
| 10,000 | 440 | 9,560 | $2,500 | $90 | **~$2,590** | $0.0086 |

The CLAUDE.md target of **$0.01/comparison is met at every scenario**. Without data sharing, breakeven shifts dramatically — data sharing saves $4K-7K/month at production volumes.

### 5.4 — Referral marginal cost

| Component | Cost |
|---|---|
| Push notifications (Expo) | $0 |
| Deep Review credit redemption | +$0.005-0.008 per credit (extra Serper snippets, mini still free if within cap) |
| Loop 2 trigger logic | $0 (Supabase row + counter increment) |
| Re-engagement cron daily | $0 (queries + push, no LLM) |
| Referral_invites/redemptions writes | $0.0001/share (Supabase free tier) |

**CAC per referred user ≈ $0.01-0.04** vs typical paid-ads CAC of $1-10. Even at 20% Loop 2 conversion, the system is 30-1000× more efficient per acquired user.

### 5.5 — Cost dashboard at `/admin/costs.html`

Mirrors `/admin/cohort.html` (Chart.js, X-Admin-Key auth). Four panels:

**A. Monthly Subscriptions** — Railway, Apple Dev, Domain, Supabase, Upstash, Sentry, Twilio (when added). Total recurring.

**B. API Costs This Month** — OpenAI paid spillover (live from Usage API), Serper, Firecrawl, Scrape.do. Daily burn-rate Chart.js line graph.

**C. Service Function Map** — table mapping each service to what it does in Qaren and when it fires (full table in design Section 4.4 of brainstorming notes).

**D. Cap Utilization Gauges** — OpenAI 4o today / cap; OpenAI mini today / cap; Firecrawl lifetime credits remaining / 450; Scrape.do this month / 900; Serper lifetime credits.

---

## 6. T&C / Privacy Policy Updates

Three new sections to add. All localized EN/AR via existing i18n pattern (`src/i18n/`).

### 6.1 — AI Quality Improvement Program (Privacy Policy)

> *To make Qaren's comparisons sharper over time, we participate in OpenAI's Data Sharing Program.*
>
> ***What we share:** your search queries; your country, language, and governorate; your stated preferences (budget tier, priorities, brand attitude, lifestyle tags); aggregate findings from users similar to you; AI-generated comparison responses.*
>
> ***What we never share:** your name, email, phone, payment info, account ID, your specific age or gender, your individual comparison history or behavior data, or anything that ties data back to your personal identity.*
>
> ***Your right to opt out:** Under Bahrain's PDPL, Saudi Arabia's PDPL, and similar GCC regulations, you can disable AI sharing in Settings → Privacy → "Help improve AI quality." When off, your queries are processed without contributing to AI evaluation. Comparisons still work — they just don't help train the system.*

### 6.2 — Smart Decision Referrals (Terms)

> *When you share a Qaren comparison with a friend, you may earn rewards.*
>
> ***How rewards work:** sharing earns a Deep Review credit (limit 3/week). When a friend you invited completes their first real comparison while signed in, you earn 5 additional comparisons added to that month's limit. Maximum 15 referral comparisons per month. Premium subscribers earn 10 per conversion instead of 5.*
>
> ***Fair use:** rewards may be withheld for self-referral, automated signups, fake accounts, or coordinated rings. We use device fingerprints, email validation, and behavior signals to detect abuse. Rewards are not transferable, have no cash value, and expire 30 days after grant.*

### 6.3 — Smart Decision Notifications (Terms)

> *Qaren may send up to 1 re-engagement notification per week to help you make better purchase decisions: review insights on saved products, peer-decision updates, or 14-day decision retrospectives. We never send price-drop spam, advertising, or promotional content. Disable any type in Settings → Notifications.*

---

## 7. Anti-Abuse Implementation

| Control | Trigger | Action | Cost |
|---|---|---|---|
| Device + email binding | Invitee signs up with same `device_fingerprint_hash` (Expo `Device.osBuildId` + IDFV/Android-ID, SHA-256) as referrer | Skip Loop 2; audit log entry with reason `SAME_DEVICE` | $0 |
| Disposable email blocklist | Email domain matches public list (~5K domains, refreshed quarterly via cron) | Allow signup, exclude from referral rewards; audit log `DISPOSABLE_EMAIL` | $0 |
| Real-action gate | Loop 2 only fires if invitee's first comparison: `result_viewed_at - comparison_started_at > 30s` AND query not in spam list (`test`, `asdf`, etc.) | Loop 2 skipped; audit log `BELOW_REAL_ACTION_THRESHOLD` | $0 |
| Soft phone verify | DEFERRED to v1.1; add only if abuse data shows it's needed | — | — |

Audit trail extends `admin_audit_log` (Session 38 table) with new `event_type` values: `referral_self_referral`, `referral_disposable_email`, `referral_below_threshold`. Visible in `/admin/referrals.html` for manual review.

---

## 8. Instrumentation / KPIs

### 8.1 — Volume metrics
- Invites sent (lifetime / month / week)
- Redemptions (Loop 2 fires)
- Conversion rate = redemptions / invites
- Active referrers (≥1 invite this month)

### 8.2 — Viral coefficient
- K = (avg invites per referring user) × (conversion rate)
- Target: K = 0.4-0.7 (typical good consumer apps)
- 12-week trailing trendline

### 8.3 — Reward economics
- Cost per redemption (avg Loop 1 + Loop 2 marginal cost)
- Revenue per redemption (when Premium analytics matures)

### 8.4 — Cohort uplift (referred vs organic)
- Day 7/30 retention
- Comparisons per user per month
- Premium conversion rate
- Reuses Session 41 cohort_service infrastructure

### 8.5 — Re-engagement metrics
- Pushes sent by type
- Push CTR = `opened_at / delivered_at`
- Returning users via push

### 8.6 — Anti-abuse metrics
- Flagged invites by reason code
- (Phone-verify completion rate when v1.1 ships)

---

## 9. Phasing + Rollout

### 9.1 — Build phases (4-Opus-agent parallel team)

| Phase | Scope | Depends on | Duration |
|---|---|---|---|
| **P1 Foundation** | Migration 014 via Supabase MCP; referral code generation; T&C markdown + Profile AI-sharing toggle | — | 2 days |
| **P2 Referrer flow** | Share endpoints; bottom sheet UI; result-aware CTAs; Loop 1 toast; pre-filled message | P1 | 3 days |
| **P3 Invitee flow** | Invite resolution endpoint; landing page (web + deep link); 4-question quiz; personal result render; soft signup CTA | P2 | 3-4 days |
| **P4 Loop 2 + anti-abuse** | Trigger in comparison post-hook; device/email/action checks; bonus crediting; push to referrer | P3 | 2-3 days |
| **P5 Re-engagement** | Daily cron; 3 detectors; push dispatcher; notification settings | P1 (parallel with P3-P4) | 3 days |
| **P6 Admin dashboards** | Referrals + Costs endpoints + HTML pages | P1-P5 (data must flow) | 2-3 days |
| **P7 QA + rollout** | E2E tests; security regression extension; smoke tests; feature-flag rollout | All | 2-3 days |

**Total: ~17-20 working days = 3-4 weeks**.

### 9.2 — Feature flags (default OFF in code, flip ON in Railway after smoke)

| Flag | Gates |
|---|---|
| `ENABLE_REFERRAL_SYSTEM` | All `/referrals/*` endpoints, share CTAs, Loop 1+2 logic |
| `ENABLE_REENGAGEMENT_PUSHES` | Daily cron + push dispatcher |
| `ENABLE_HYBRID_MODEL_ROUTING` | `model_router_service.py` decisions (independent of referrals; ship from day 1) |

Pattern matches `ENABLE_COHORT_PERSONALIZATION` from Session 41.

### 9.3 — Testing strategy

- Backend unit tests target 80%+ coverage on new files
- Security regression extends `tests/test_security_regression.py` (don't break existing 57)
- Live integration: real Supabase + Redis (no DB mocks per project pattern)
- Frontend E2E: invitee web landing → quiz → result → signup happy path
- Production canary: 5% of users get referral CTAs first 48 hours

### 9.4 — Top 3 risks + mitigations

1. **Decision Insight detector cost overhead** — Mitigate: only check products with ≥3 saved comparisons; reuse cache; batch cron at 3am GCC; cap to top-100 saved products globally.
2. **Migration 014 partial-rollback risk** — Mitigate: use Supabase MCP `apply_migration` (not SQL Editor); verify schema with `information_schema.columns`; split CREATE VIEW from CREATE TABLE if any view risky.
3. **Hybrid model routing race conditions** — Mitigate: atomic `INCRBY` (per `api_budget_service.py`); reserve tokens before call; on 429, retry with mini and log.

---

## 10. Implementation Team Rules (per Ahmed)

The implementation team must follow these rules — they are not optional:

1. **Opus-only team**, NO Sonnet, NO Haiku. Quality over cost on this build.
2. **4 agents in parallel** via TeamCreate, with bypassPermissions mode:
   - `backend-referral` — P1, P2 backend, P3 backend, P4 backend, P5 backend
   - `frontend-referral` — P2 frontend, P3 frontend, P4 frontend (counter), P5 frontend (settings), P6 dashboards
   - `test-referral` — All test files; security regression extension; coverage gate
   - `qa-referral` — Cross-review of every other agent's PRs; smoke tests; canary monitoring
3. **100% complete before disbanding** — features must be fully shipped, tested, and verified working before the team is dissolved.
4. **Mutual QA mandatory** — every member must QA at least one other member's work. If work is subpar or missed something, send it back with specific feedback. No rubber-stamping.
5. **No idle agents** — when waiting on dependencies, an idling member must EITHER:
   - Write red-green tests for the new feature (target 80% coverage), OR
   - Wait for their assigned QA to come back with results
   - NEVER sit idle
6. **Delegated work** — task assignment is explicit per phase (see 9.1). No agent freelances outside their lane.
7. **Path-restricted commits** — `git commit -- <paths>` to avoid sweeping teammates' staged work (per Session 41 git-staging learning).

---

## 11. Deferred to v1.1+

- **Vanity referral codes** (Premium-gated upsell)
- **Soft phone verification** (added if abuse data shows need)
- **Graph-cycle detection** for collusion rings (overkill until volume justifies)
- **A/B testing share copy** (test alternative wording variants)
- **Continuous in-app survey collection** to refresh cohort priors (Session 41 deferred this too)

---

## 12. PDF Principles → Design Mapping

| PDF Principle | Implementation |
|---|---|
| #1 Regret reduction | Result-aware "help someone confused" CTAs (3.1); decision-insight push (3.9) |
| #2 Smart identity (social currency) | "Share your smart decision" copy (3.1); pre-filled story-format message (3.2) |
| #3 Reciprocity timing (value first) | Share CTA only appears AFTER comparison renders, never before |
| #4 Ease of action | One-tap share targets (WhatsApp/Copy/X/Telegram/Snapchat); auto-localized pre-filled message |
| #5 Curiosity for invitee | "Your answer might differ" landing copy (3.5); 4-question quiz before result (3.6) |
| #6 Gradual commitment (PLG) | Invitee sees personal result BEFORE signup gate (3.6, 3.7) |
| #7 Value-tied reward | Deep Review Mode (Loop 1) + capacity bumps (Loop 2). No cash. |
| #8 Trust + privacy | Privacy toggles; budget locked off; "We never share your budget" copy (3.3) |
| #9 Honest scarcity | "3 gifts/week" framing (3.4); no countdown timers; 30-day expiry on credits |
| #10 Social proof | Cohort Curiosity push: "5 people near you chose differently" (3.9); admin dashboard surfaces real numbers |
| #11 Story framing | Pre-filled message tells decision narrative, not spec table (3.2) |
| #12 Habit formation | Re-engagement push system creates external triggers (3.9) |
| #13 Hooked model | Trigger (confused buyer) → Action (open app) → Variable Reward (your result) → Investment (save/share/rate) |
| #14 Final CTA versions | All 4 variants implemented in 3.1 (strong/close/saved/default) |

---

## 13. Files Summary

**New files (~14 source + 4 test):**
- `migrations/014_referral_system.sql`
- `app/api/referral_routes.py`
- `app/services/referral_service.py`
- `app/services/abuse_detection_service.py`
- `app/services/reengagement_service.py`
- `app/services/model_router_service.py`
- `app/static/admin/referrals.html`
- `app/static/admin/costs.html`
- `SmartCompareApp/src/screens/ReferralLandingScreen.tsx`
- `SmartCompareApp/src/screens/InviteeQuizScreen.tsx`
- `SmartCompareApp/src/components/ShareBottomSheet.tsx`
- `SmartCompareApp/src/components/ReferralStatusCard.tsx`
- `SmartCompareApp/src/services/referralService.ts`
- `SmartCompareApp/src/i18n/{en,ar}/referrals.ts`
- `tests/test_referral_service.py`
- `tests/test_reengagement_service.py`
- `tests/test_abuse_detection.py`
- `tests/test_model_router.py`

**Modified files:**
- `app/main.py`, `app/api/auth_routes.py`, `app/api/legal_routes.py`, `app/api/admin_routes.py`
- `app/services/usage_service.py`, `app/services/structured_comparison_service.py`, `app/services/extraction_service.py`, `app/services/review_service.py`
- `app/middleware/security.py` (CSP allowlist for new admin pages)
- `tests/test_security_regression.py` (extend with referral cases)
- `SmartCompareApp/App.tsx`, `SmartCompareApp/src/screens/{ResultsScreen,ProfileScreen}.tsx`
- `SmartCompareApp/src/services/api.ts` (referral endpoints)

---

## 14. Acceptance Criteria

The implementation is complete when ALL of the following are true:

1. Migration 014 applied via Supabase MCP; schema verified with `information_schema.columns`.
2. All 7 phases shipped, feature-flagged ON in Railway after smoke test.
3. Backend test coverage ≥80% on new files; existing 57 security regression tests still pass.
4. End-to-end referrer + invitee flows work in production canary (5% rollout, 48h).
5. Admin dashboards (`/admin/referrals.html`, `/admin/costs.html`) render with real data.
6. T&C and Privacy Policy markdown files updated with all 3 new sections (EN + AR).
7. CLAUDE.md and MEMORY.md updated with Session learnings.
8. Mutual QA completed across all 4 agents; no subpar work outstanding.
9. Hybrid model routing operational; OpenAI cap utilization < 80% during canary.
10. Anti-abuse: at least one synthetic test of each control passes (same-device, disposable-email, sub-30s).

When all 10 are true, the team disbands.

---

**Next step:** invoke `superpowers:writing-plans` to translate this design into a phase-by-phase implementation plan with specific tasks per agent.

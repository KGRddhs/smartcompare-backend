---
name: qaren-referrals
description: Use when touching referral invites, share links, /api/v1/referrals/* routes, invite codes (QR-XXXXXX), Loop 1 / Loop 2 flow, redemption chain, abuse detection, device-fingerprint caps, bonus expiry, or referral_invites / referral_redemptions tables. Covers Smart Decision Referrals + Bundle B/C/D lifetime-cap overhaul.
last_verified: 2026-05-16
update_when_changing:
  - app/services/referral_service.py
  - app/services/abuse_detection_service.py
  - app/api/referral_routes.py
  - migrations touching referral_invites or referral_redemptions
  - SmartCompareApp/src/services/playInstallReferrerService.ts
  - SmartCompareApp/src/services/clipboardFallbackService.ts
---

# Qaren Referral System

## Smart Decision Referrals (Phase 1 LIVE 2026-05-05)

Virality dual-loop rewards. 4 endpoints under `/api/v1/referrals/*` gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway). Full endpoint signatures in `app/api/referral_routes.py`.
- **POST /share** — creates `referral_invites` row, grants Loop 1 Deep Review credit, returns `share_link`. ShareRequest accepts flat `show_name`/`show_result`/`show_reasons` + nested `privacy={...}` (back-compat); `extra='ignore'` drops `show_budget` (locked OFF). Persisted to `referral_invites.privacy` JSONB. **Bundle B/C/D changes: no decrement at share time + 3-LIFETIME cap per device (was 3/week per user) + share-button disabled at 3.**
- **GET /invite/{share_token}?ref={code}** (anon-friendly) — invitee landing. Honors privacy flags: drops winner/recommendation (show_result), verdict/key_differences/tradeoffs (show_reasons), swaps display_name to "A friend" (show_name). Strips personalization via `_strip_personalization`.
- **POST /invite/{token}/quiz** (anon-friendly) — 4-question rescoring. Returns `scoring_method = "invitee_quiz"`. NO PII pre-signup.
- **Loop 2 chain:** invite → register-with-`invite_id` → `link_invite_to_user` (fire-and-forget) → first comparison → `try_trigger_loop2` → AbuseDetectionService → on pass: redemption, +5 (Free)/+10 (Premium) bonus comparisons, invitee credit, Expo Push. **Bundle B/C/D adds: lifetime device cap check + inviter's `lifetime_invites_consumed` increment on success.**
- **Re-engagement** (`ENABLE_REENGAGEMENT_PUSHES`, default OFF): daily cron iterates `notifications_enabled` AND `last_comparison_at >= now() - 60d` (1000/run cursor-paginated). Master + per-type sub-toggles in `users.preferences.notification_types`.
- **Admin:** `/admin/referrals/*` + `/admin/costs/*` (X-Admin-Key, 30/min). Dashboards at `/admin/referrals.html` + `/admin/costs.html` (Chart.js v4.4.1 + SRI, sessionStorage key cache, `escapeHtml` on inline values).
- **Code redemption is register-only.** `RegisterRequest.invite_code` accepts `^QR-[unambiguous-alphabet]{6}$`; `referral_service.resolve_code_to_invite_id` creates a fresh row with `source='code_redeem'` then routes through `link_invite_to_user`. No post-hoc redeem endpoint. Share copy locked: *"I overthink every purchase. Qaren ends the debate in 30 seconds. Try it: https://qaren.app/r/{code} (or use code {code} in the app)"* — claims decision *closure*, not *correctness*.

## Bundle B/C/D Referral Hardening (Session 46, Migration 023)

- **Cap moved to 3 LIFETIME per device** (was 3/week per user). Cross-account aggregation via `_referrer_device_lifetime_count` fingerprint SUM.
- **Decrement at receiver signup**, not at share time. Fail-OPEN on DB error (design § 6.1).
- **Share-button disabled at 3 lifetime** with gift-framing copy (`referrals.share.maxReached`).
- **Bonus expiry: 7 days** for Loop 2 (Loop 1 `deep_review_expires_at` stays at 3 days; existing rows unchanged).
- **Hybrid DIY install-survival** (Branch.io DROPPED — free tier paywalled to $199/mo): Android Play Install Referrer + iOS clipboard fallback (Apple-review-safe — consent banner BEFORE read) + Cloudflare Worker at `qaren.app/r/{code}`.
- **Canonical invite-code regex:** `^QR-[A-HJ-NP-Z2-9]{6}$` shared across `playInstallReferrerService.ts`, `clipboardFallbackService.ts`, `attribution_service.py`, `auth_routes._INVITE_CODE_RE`. Defense-in-depth at every layer.
- **Abuse detection priority:** `evaluate_invite()` checks SAME_DEVICE > DISPOSABLE_EMAIL > BELOW_REAL_ACTION_THRESHOLD (`elapsed_seconds` proxy from `metadata.elapsed_seconds`, `REAL_ACTION_MIN_SECONDS` env, default 5s).

## Sources (verify against current code before recommending changes)

- `app/services/referral_service.py` — invite creation, `link_invite_to_user`, `try_trigger_loop2`, `resolve_code_to_invite_id`, code generation
- `app/services/abuse_detection_service.py` — `evaluate_invite()` priority order
- `app/api/referral_routes.py` — 4 endpoints under `/api/v1/referrals/*`
- `app/services/push_service.py` — Expo Push deep-link `qaren://profile/referrals`
- `migrations/023_*.sql` — `users.lifetime_invites_consumed` + partial idx on `device_fingerprint_hash`
- `SmartCompareApp/src/services/playInstallReferrerService.ts` — Android install-survival
- `SmartCompareApp/src/services/clipboardFallbackService.ts` — iOS install-survival
- Plans: `docs/plans/2026-05-05-smart-referral-system.md`, `docs/plans/2026-05-12-bundle-bcd-consolidated-design.md`
- Bundle B/C/D context: `docs/SESSION_BUNDLES.md` (Bundle B/C/D section)

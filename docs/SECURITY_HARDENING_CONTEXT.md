# Security Hardening — Context & Residual Risks

> **Created:** April 4, 2026 (Session 38)
> **Spec:** `docs/superpowers/specs/2026-04-04-security-hardening-design.md`
> **Plan:** `docs/superpowers/plans/2026-04-04-security-hardening.md`
> **Status:** Implementation in progress

---

## What Was Done

### Audit Scope
5-agent deep audit covering:
- Supply chain & malware scan (clean)
- Backend auth & access control
- Frontend client-side security
- Database RLS & Supabase security
- Mobile platform & config security
- IOC host checks (clean)
- Git history secret scan (.env never committed)

### Findings: 24 total
- **4 Critical:** C1 (service-role for all ops), C2 (zero RLS), C3 (AsyncStorage tokens), C4 (admin no rate limit)
- **5 High:** H1 (email no password), H2 (Google no nonce), H3 (Client ID comments), H4 (no token revocation), H5 (weak share token)
- **10 Medium:** M1-M10 (history leak, image errors, query length, debug logs, CORS, cascade delete, login validation, preference errors)
- **5 Low:** L1-L5 (Sentry scrubbing, timing-unsafe comparison, screenshot protection, URL validation, Apple nonce)

### Implementation Plan: 11 Tasks, 3 Phases
- **Phase 1 (Tasks 1-6):** Critical + High — RLS, dual client, SecureStore, token revocation, email password, OAuth nonces, admin rate limits
- **Phase 2 (Tasks 7-9):** Medium + Low — Sentry scrubbing, CORS config, screenshot protection, URL validation, certificate pinning
- **Phase 3 (Tasks 10-11):** Tests + QA — 20+ regression tests, full suite verification, cross-QA checklist

---

## Residual Risks (After All Fixes Applied)

These risks remain even after full implementation. They are **accepted** with mitigations in place.

### 1. Supabase JWT Signing Key Compromise
- **Risk:** If Supabase's JWT signing key is leaked, any attacker can forge valid tokens
- **Mitigation:** Supabase manages key rotation. Redis revocation blacklist provides additional layer.
- **Residual level:** Accept — vendor responsibility
- **Future action:** Monitor Supabase security advisories

### 2. Railway Environment Variable Leak
- **Risk:** If Railway's platform is breached, all env vars (API keys, service-role key) are exposed
- **Mitigation:** Railway encrypts at rest + TLS in transit. Keys are NOT in git.
- **Residual level:** Accept — platform responsibility
- **Future action:** Rotate keys periodically (quarterly recommended)

### 3. Token Theft via Device Malware (Even with SecureStore)
- **Risk:** Sophisticated malware on rooted/jailbroken devices could extract Keychain/Keystore
- **Mitigation:** SecureStore uses hardware-backed storage (Keychain on iOS, Keystore on Android)
- **Residual level:** Low — requires root/jailbreak + targeted malware
- **Future action:** Consider device integrity checks (SafetyNet/Play Integrity, DeviceCheck)

### 4. MITM Without Full Certificate Pinning Validation
- **Risk:** Certificate pinning requires EAS dev build to test. If implementation has bugs, MITM is possible.
- **Mitigation:** HTTPS + HSTS enforced. Pinning targets Let's Encrypt intermediates (E8 + E5 backup). Graceful degradation if pinning init fails.
- **Residual level:** Low — attacker needs compromised CA or local proxy
- **Future action:** Test pinning in EAS dev build before App Store submission. Validate pinning works by testing with a proxy (should reject).

### 5. In-Memory Rate Limiter Bypass (Multi-Instance)
- **Risk:** If Railway scales to 2+ instances, in-memory slowapi rate limiter doesn't share state
- **Mitigation:** Single Railway instance currently. Admin key is required regardless.
- **Residual level:** Accept for now
- **Future action:** When scaling, migrate rate limiter storage to Redis (supported by slowapi)

### 6. RLS Policy Misconfiguration
- **Risk:** RLS policies might have edge cases (e.g., shared comparisons accessible without intended scope)
- **Mitigation:** Regression tests verify policy behavior. Code-level ownership checks remain as defense-in-depth.
- **Residual level:** Low — dual enforcement (RLS + code checks)
- **Future action:** Review policies when adding new tables or features

### 7. Let's Encrypt Intermediate Rotation
- **Risk:** If Let's Encrypt retires E8/E5 intermediates, cert pinning will break the app
- **Mitigation:** Two intermediates pinned (E8 primary + E5 backup). LE intermediates are valid for years.
- **Residual level:** Low — advance notice from Let's Encrypt
- **Future action:** Monitor [letsencrypt.org/certificates](https://letsencrypt.org/certificates) annually. Update SPKI hashes before intermediate expiry.

---

## Future Work (Not in Current Plan)

### Priority 1 — Before App Store Release
- [ ] **Test certificate pinning** in EAS development build (both iOS and Android)
- [ ] **Apply RLS migration** to Supabase SQL Editor (manual step)
- [ ] **Rotate all API keys** as best practice (OpenAI, Serper, Supabase service-role, Upstash, Firecrawl, Scrape.do)
- [ ] **Verify production** after Railway deploy (`/health` + live comparison test)

### Priority 2 — Post-Launch Hardening
- [ ] **Device integrity checks:** SafetyNet/Play Integrity (Android), DeviceCheck (iOS) — reject rooted/jailbroken devices
- [ ] **Redis-backed rate limiting:** Migrate slowapi storage to Upstash Redis when scaling to 2+ instances
- [ ] **Request signing:** HMAC-sign API requests to prevent replay attacks beyond OAuth nonce
- [ ] **Audit logging:** Log all security-relevant events (login, logout, email change, password change, account deletion) to a dedicated audit table
- [ ] **Content Security Policy tightening:** Restrict CSP further once all external resources are cataloged
- [ ] **Dependency vulnerability scanning:** Add `npm audit` and `pip audit` to CI/CD pipeline
- [ ] **Penetration test:** External security audit before public launch

### Priority 3 — Long-Term
- [ ] **OAuth PKCE flow:** Migrate from implicit ID token flow to PKCE for enhanced OAuth security
- [ ] **WebAuthn/Passkeys:** Support passwordless authentication (Supabase supports this)
- [ ] **API versioning with deprecation:** Formal API lifecycle management
- [ ] **Secret rotation automation:** Automated key rotation via Railway CLI/API

---

## Key Files Reference

| File | Role |
|------|------|
| `migrations/010_enable_rls.sql` | RLS policies + cascade delete function |
| `app/services/database_service.py` | Dual client (user RLS + admin bypass) |
| `app/services/auth_service.py` | Token revocation, email password verify |
| `app/api/admin_routes.py` | Rate-limited admin endpoints |
| `SmartCompareApp/src/services/authService.ts` | SecureStore tokens, OAuth nonces |
| `SmartCompareApp/src/services/certificatePinning.ts` | Intermediate cert SPKI pinning |
| `tests/test_security_regression.py` | 20+ regression guards |

## SPKI Pin Hashes (Current as of April 4, 2026)

```
Railway leaf:         i+9suBX/dDafsZIMvCHqAlFdC3WdC0Yu6JsC9yvlNLo= (DO NOT PIN — rotates every 90 days)
LE E8 intermediate:   iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU= (PINNED — primary)
LE E5 intermediate:   NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg= (PINNED — backup)
```

To re-extract after Railway cert changes:
```bash
echo | openssl s_client -servername web-production-58776.up.railway.app \
  -connect web-production-58776.up.railway.app:443 -showcerts 2>/dev/null | \
  csplit -z -f /tmp/cert_ - '/-----BEGIN CERTIFICATE-----/' '{*}'
# Leaf: /tmp/cert_01, Intermediate: /tmp/cert_02
openssl x509 -in /tmp/cert_02 -noout -pubkey | \
  openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | base64
```

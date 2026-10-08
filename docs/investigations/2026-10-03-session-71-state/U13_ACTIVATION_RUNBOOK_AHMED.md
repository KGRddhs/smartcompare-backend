# U13 activation runbook (Ahmed) — paid routes require a caller

Merged 2026-10-03 12:52 as PR #297 (main `b90b5f07`, deployed, `/health` 200). The flag `ENABLE_COMPARE_AUTH_REQUIRED` is OFF: production behaves exactly as before (measured 12:55: anonymous `GET /text/compare` → 400 parse copy, `GET /text/prices/iphone` → 200). Nothing below is done by Claude; every step is yours, in this order, and you tell Claude after each one.

## 0. Why the order matters
- U13 alone would leave `/url/compare` and `/image/identify` unmetered for any self-registered account, so the metering and camera-envelope flags flip in the same window.
- The admin key is the only account-free way to buy a paid compare once the flag is on, and guesses on these routes are not rate-limited yet (#299), so it is rotated FIRST.
- OpenAI is funded LAST, when anonymous callers can no longer reach paid work.

## 1. Rotate `ADMIN_API_KEY` (Railway `web`)
Generate at least 32 random bytes (for example `python -c "import secrets; print(secrets.token_urlsafe(48))"` in your own terminal) and set it from YOUR terminal, never pasted into a chat:
```bash
railway variables -s web --set ADMIN_API_KEY=<the new value>
```
Railway redeploys `web`. Tell Claude "key rotated" (never the value).

## 2. Smoke the credentials while the flag is still OFF (no LLM spend)
```bash
# Moved 2026-10-08 (BE-HARNESS): the canary is now scripts/verify_after_credits.py (opt in with --send-admin-key); the docs copy is removed at this commit.
railway run -s web -- python scripts/verify_after_credits.py --send-admin-key --pairs "iPhone 15 vs Galaxy S24"
```
Expected: the compare line shows an HTTP status that is NOT 401 and NOT 403 (the compare itself still fails while OpenAI is unfunded; only the status matters). Also open the app on a phone, sign in, run one compare: it fails for OpenAI, not for auth.

## 3. Set THREE flags in ONE window on `web`
```bash
railway variables -s web --set ENABLE_COMPARE_AUTH_REQUIRED=true --set ENABLE_PAID_ROUTE_METERING=true --set ENABLE_CAMERA_FAILURE_ENVELOPE=true
```
Tell Claude "flags on". Claude then runs the free anonymous re-probe (each of the ten paid routes → 401 `AUTH_REQUIRED`; `/url/detect`, `/url/retailers`, `/health`, `/legal/*` unchanged) and repeats step 2 (still not 401).

## 4. Watch 24 hours
Claude reads the Railway logs: the 401 count on the ten routes (the scanners), the `[paid-auth]` reason histogram, and any mobile-UA 401 that is not followed by `/auth/refresh` and a successful retry. Testers should open the app at least once in that window (the camera path has no 401 refresh-and-retry yet, #298: an expired token on the camera shows the generic camera error until any other call refreshes it).

## 5. ONLY THEN fund OpenAI
Prepaid, a low project budget, no auto-recharge; the NEW key goes into Railway `web` as `OPENAI_API_KEY` from your terminal. Then run step 2 again with the default pairs to verify end to end.

## 6. Rollback
```bash
railway variables -s web --set ENABLE_COMPARE_AUTH_REQUIRED=false
```
Per call, immediate. It reopens anonymous paid compares, so only with the OpenAI budget capped.

## Also yours (from the same unit)
- Check Supabase Auth "Confirm email" (not measured): if it is off, one anonymous POST creates an account with free credits.
- The production smoke accounts use a password readable in the public repo (#303): delete them or rotate once #303 ships.
- Make the repo private (your decision earlier today).

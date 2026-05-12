# qaren-redirect — install-survival Worker

`qaren.app/r/{code}` → device-aware redirect. Replaces the dropped
Branch.io SDK (free tier was paywalled). See
`docs/plans/2026-05-12-bundle-bcd-consolidated-design.md` § 4.1.

## Behavior

| User agent | Response |
|---|---|
| Android | `302` → Play Store with `?referrer=referrer%3DQR-XXXXXX` so `react-native-play-install-referrer` reads it on first launch |
| iOS | `200` HTML page → copies code to clipboard via `navigator.clipboard.writeText`, then auto-bounces to App Store (~1.2s). On first RegisterScreen mount, `clipboardFallbackService` shows an explicit consent banner before pre-fill |
| Other | `200` HTML page → "open this link on your phone" + display the code for manual entry |
| Anything else | `404` |

Canonical QR alphabet: `[A-HJ-NP-Z2-9]{6}` (no I, L, O, 0, 1). Matches
backend `app/services/attribution_service.py` `_QR_CODE_PATTERN` so a
fake code in the URL never lands on Apple's store with a junk clipboard
value.

## Local dev

```bash
cd cloudflare-workers/qaren-redirect
npm install
npm test                        # 22 unit tests
npm run typecheck               # tsc --noEmit
npm run dev                     # wrangler dev — local Worker on http://127.0.0.1:8787
```

Smoke-test the local worker (in another shell):

```bash
# Android
curl -i -A "Mozilla/5.0 (Linux; Android 13)" \
  "http://127.0.0.1:8787/r/QR-ATAUX9"

# iOS
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1)" \
  "http://127.0.0.1:8787/r/QR-ATAUX9"

# 404
curl -i "http://127.0.0.1:8787/r/qr-lowercase"
```

## Deploy (Ahmed runs interactively)

```bash
cd cloudflare-workers/qaren-redirect
wrangler login          # opens browser; one-time per machine
wrangler deploy         # publishes to Cloudflare; routes qaren.app/r/* to this Worker
```

**Before deploying:** confirm the Apple App Store ID is no longer
`idTBD`. Edit `src/index.ts` line `const APP_STORE_ID = 'idTBD';`,
re-run tests, and commit. Apple Developer enrollment (\$99/year) is the
prerequisite — see CLAUDE.md "Known Remaining Bugs".

Post-deploy verify:

```bash
curl -i -A "Mozilla/5.0 (Linux; Android 13)" "https://qaren.app/r/QR-ATAUX9"
# expect: 302 Location: https://play.google.com/store/apps/details?id=com.kersher2.qaren&referrer=referrer%3DQR-ATAUX9
```

## Rollback

```bash
wrangler rollback       # interactive — pick a previous deployment
```

If the Worker breaks the qaren.app DNS path, you can also unbind the
route directly in the Cloudflare dashboard (`Workers & Pages → qaren-redirect → Triggers`)
without redeploying. The route falls back to whatever upstream handler
the DNS record points at.

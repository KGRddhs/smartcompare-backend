/**
 * Cloudflare Worker — qaren.app/r/{code} install-survival redirect.
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
 *
 * Hybrid DIY install-survival, replacing the dropped Branch.io SDK:
 *   - Android  → 302 → Play Store with `referrer=QR-XXXXXX` query so the
 *                Play Install Referrer API can hand the code to the app
 *                on first launch.
 *   - iOS      → 200 HTML page that copies the code to the user's
 *                clipboard, shows a banner, then redirects to the App
 *                Store. On first RegisterScreen mount the app's
 *                clipboardFallbackService reads it (with an explicit
 *                consent prompt — Apple-review safe).
 *   - Other UA → fallback HTML telling the user to open the link on
 *                their phone (and showing the code for manual entry).
 *   - Non-matching path → 404.
 *
 * Canonical QR alphabet matches `app/services/attribution_service.py`
 * `_QR_CODE_PATTERN`: `^QR-[A-HJ-NP-Z2-9]{6}$` (no I, L, O, 0, 1).
 *
 * Apple App Store ID: TBD (placeholder `idTBD` below). Confirm with
 * team-lead before `wrangler deploy`.
 */

const QR_PATH_PATTERN = /^\/r\/(QR-[A-HJ-NP-Z2-9]{6})$/;

const PLAY_STORE_PACKAGE = 'com.kersher2.qaren';
const APP_STORE_ID = 'idTBD'; // TODO: replace once Apple Developer enrollment lands

// User-agent detection. Cloudflare passes the raw UA — keep this simple
// and resilient to weird strings (curl, scanners, etc.).
function detectPlatform(ua: string): 'android' | 'ios' | 'other' {
  const lower = ua.toLowerCase();
  // iPadOS 13+ may report as Mac; the `Mobile/` token is the give-away
  // for Safari on iOS even when the OS calls itself Mac-like.
  if (
    /iphone|ipad|ipod/.test(lower) ||
    (/macintosh/.test(lower) && /mobile/.test(lower))
  ) {
    return 'ios';
  }
  if (/android/.test(lower)) return 'android';
  return 'other';
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function androidRedirect(code: string): Response {
  // Play Install Referrer reads back whatever we put in `?referrer=...`,
  // verbatim. Our reader expects `referrer=QR-XXXXXX` so the regex in
  // playInstallReferrerService can pick it out — note the *double*
  // encoding (Play decodes once before handing to the app).
  const referrer = encodeURIComponent(`referrer=${code}`);
  const url = `https://play.google.com/store/apps/details?id=${PLAY_STORE_PACKAGE}&referrer=${referrer}`;
  return Response.redirect(url, 302);
}

function iosHandoffPage(code: string): Response {
  const safeCode = escapeHtml(code);
  const appStoreUrl = `https://apps.apple.com/app/qaren/${APP_STORE_ID}`;
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open Qaren</title>
<style>
body{font-family:-apple-system,system-ui,sans-serif;background:#0A0A0B;color:#fff;margin:0;padding:24px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh}
.code{background:rgba(16,185,129,.12);color:#10B981;font-weight:700;letter-spacing:1px;padding:8px 16px;border-radius:8px;font-size:18px;margin:16px 0}
.title{font-size:24px;font-weight:700;margin-bottom:8px;text-align:center}
.msg{font-size:15px;opacity:.7;text-align:center;max-width:320px;line-height:1.4}
.cta{margin-top:24px;background:#10B981;color:#fff;text-decoration:none;padding:14px 28px;border-radius:999px;font-weight:600}
</style>
</head>
<body>
<div class="title">Code copied — open Qaren after install</div>
<div class="code">${safeCode}</div>
<div class="msg">Tap below to install Qaren. The invite code is already on your clipboard.</div>
<a class="cta" href="${appStoreUrl}">Open App Store</a>
<script>
(function(){
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText('${safeCode}').catch(function(){/* user-gesture required on some browsers — fall through */});
    }
  } catch (e) { /* clipboard unavailable; user can still tap CTA */ }
  // Auto-bounce after 1.2s so the user lands on the App Store even
  // if they ignore the manual tap.
  setTimeout(function(){ location.href = ${JSON.stringify(appStoreUrl)}; }, 1200);
})();
</script>
</body>
</html>`;
  return new Response(html, {
    status: 200,
    headers: {
      'content-type': 'text/html;charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

function otherFallbackPage(code: string): Response {
  const safeCode = escapeHtml(code);
  const html = `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open this link on your phone</title>
<style>
body{font-family:system-ui,sans-serif;background:#fafafa;color:#0A0A0B;margin:0;padding:32px;display:flex;flex-direction:column;align-items:center}
.code{background:#10B98122;color:#059669;font-weight:700;letter-spacing:1px;padding:8px 16px;border-radius:8px;font-size:20px;margin:16px 0}
.title{font-size:22px;font-weight:700;margin-bottom:8px}
.msg{font-size:14px;color:#6B7280;text-align:center;max-width:420px;line-height:1.5}
</style>
</head><body>
<div class="title">Open this link on your phone</div>
<div class="msg">Qaren is a mobile app. Open this page on Android or iOS to install, or enter the code manually after signing up:</div>
<div class="code">${safeCode}</div>
</body></html>`;
  return new Response(html, {
    status: 200,
    headers: {
      'content-type': 'text/html;charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const match = QR_PATH_PATTERN.exec(url.pathname);
    if (!match) {
      return new Response('Not found', { status: 404 });
    }
    const code = match[1];
    const ua = request.headers.get('user-agent') ?? '';
    const platform = detectPlatform(ua);

    switch (platform) {
      case 'android':
        return androidRedirect(code);
      case 'ios':
        return iosHandoffPage(code);
      default:
        return otherFallbackPage(code);
    }
  },
};

// Exported for unit tests; not part of the production Worker surface.
export const __test__ = {
  QR_PATH_PATTERN,
  detectPlatform,
  androidRedirect,
  iosHandoffPage,
  otherFallbackPage,
};

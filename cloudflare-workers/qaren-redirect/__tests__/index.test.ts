/**
 * Tests for the qaren.app/r/{code} Worker.
 *
 * Uses the standard Web `Request`/`Response` globals (available in
 * Node 18+/20+), so no Cloudflare runtime emulation is required for
 * these unit-level assertions. Live behavior is verified post-deploy
 * via the curl command in plan § Task 3.4 Step 5.
 */
import worker, { __test__ } from '../src/index';

const { detectPlatform, QR_PATH_PATTERN } = __test__;

function fakeRequest(path: string, ua: string): Request {
  return new Request(`https://qaren.app${path}`, {
    headers: { 'user-agent': ua },
  });
}

const ANDROID_UA =
  'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36';
const IOS_UA =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 ' +
  '(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1';
const DESKTOP_UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const CURL_UA = 'curl/8.4.0';

describe('detectPlatform', () => {
  it('detects Android', () => {
    expect(detectPlatform(ANDROID_UA)).toBe('android');
  });
  it('detects iOS (iPhone)', () => {
    expect(detectPlatform(IOS_UA)).toBe('ios');
  });
  it('detects iPadOS as iOS via Mobile/ token', () => {
    const ipadOS =
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 ' +
      '(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1';
    expect(detectPlatform(ipadOS)).toBe('ios');
  });
  it('classifies desktop Chrome as other', () => {
    expect(detectPlatform(DESKTOP_UA)).toBe('other');
  });
  it('classifies curl as other', () => {
    expect(detectPlatform(CURL_UA)).toBe('other');
  });
  it('classifies empty UA as other', () => {
    expect(detectPlatform('')).toBe('other');
  });
});

describe('QR_PATH_PATTERN', () => {
  it('accepts a canonical-alphabet code', () => {
    expect(QR_PATH_PATTERN.exec('/r/QR-ATAUX9')?.[1]).toBe('QR-ATAUX9');
  });
  it('rejects lowercase', () => {
    expect(QR_PATH_PATTERN.exec('/r/qr-ataux9')).toBeNull();
  });
  it('rejects ambiguous chars (I, L, O, 0, 1)', () => {
    expect(QR_PATH_PATTERN.exec('/r/QR-ABO123')).toBeNull();
  });
  it('rejects wrong length', () => {
    expect(QR_PATH_PATTERN.exec('/r/QR-AB')).toBeNull();
    expect(QR_PATH_PATTERN.exec('/r/QR-ABCDEFGH')).toBeNull();
  });
  it('rejects trailing slash + extra path segments', () => {
    expect(QR_PATH_PATTERN.exec('/r/QR-ATAUX9/')).toBeNull();
    expect(QR_PATH_PATTERN.exec('/r/QR-ATAUX9/extra')).toBeNull();
  });
});

describe('Worker.fetch — happy paths', () => {
  it('Android UA → 302 → Play Store with double-encoded referrer', async () => {
    const res = await worker.fetch(fakeRequest('/r/QR-ATAUX9', ANDROID_UA));
    expect(res.status).toBe(302);
    const loc = res.headers.get('location') ?? '';
    expect(loc).toContain('play.google.com');
    expect(loc).toContain('id=com.kersher2.qaren');
    // Play decodes once before handing to the InstallReferrerClient, so
    // we send `referrer=QR-...` URL-encoded a single time.
    expect(loc).toContain('referrer=referrer%3DQR-ATAUX9');
  });

  it('iOS UA → 200 HTML with clipboard JS + App Store href', async () => {
    const res = await worker.fetch(fakeRequest('/r/QR-ATAUX9', IOS_UA));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toContain('text/html');
    expect(res.headers.get('cache-control')).toBe('no-store');
    const body = await res.text();
    expect(body).toContain('QR-ATAUX9');
    expect(body).toContain('navigator.clipboard.writeText');
    expect(body).toContain('apps.apple.com/app/qaren');
  });

  it('Desktop UA → 200 HTML fallback with manual-entry copy', async () => {
    const res = await worker.fetch(fakeRequest('/r/QR-ATAUX9', DESKTOP_UA));
    expect(res.status).toBe(200);
    const body = await res.text();
    expect(body).toContain('QR-ATAUX9');
    expect(body.toLowerCase()).toContain('open this link');
  });
});

describe('Worker.fetch — rejections', () => {
  it('404 on non-matching path', async () => {
    const res = await worker.fetch(fakeRequest('/notarefer/QR-ATAUX9', ANDROID_UA));
    expect(res.status).toBe(404);
  });

  it('404 on lowercase code', async () => {
    const res = await worker.fetch(fakeRequest('/r/qr-ataux9', ANDROID_UA));
    expect(res.status).toBe(404);
  });

  it('404 on root path', async () => {
    const res = await worker.fetch(fakeRequest('/', ANDROID_UA));
    expect(res.status).toBe(404);
  });

  it('404 on code with ambiguous chars', async () => {
    const res = await worker.fetch(fakeRequest('/r/QR-ABO123', ANDROID_UA));
    expect(res.status).toBe(404);
  });
});

describe('Worker.fetch — HTML safety', () => {
  it('iOS page contains exactly one <script> block (our controlled one)', async () => {
    // The path regex rejects anything except [A-HJ-NP-Z2-9]{6}, so HTML
    // meta-characters can't survive the capture group. Lock the count
    // anyway as a regression tripwire.
    const res = await worker.fetch(fakeRequest('/r/QR-ATAUX9', IOS_UA));
    const body = await res.text();
    const openTags = (body.match(/<script\b/g) ?? []).length;
    expect(openTags).toBe(1);
  });
});

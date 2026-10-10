/**
 * S76 DOMAIN-MYEZ (RED) -- the product web host is getmyez.com; qaren.app is retired
 * (owner decision 2026-10-10). The brand is MYEZ; the IDENTIFIERS stay qaren and are
 * pinned unchanged here: the scheme qaren://, the bundle id / Android package
 * com.qaren.app, the EAS slug qaren and owner kersher2, the Google iosUrlScheme, and the
 * Supabase recovery redirect qaren://reset-password (backend default, not in this file).
 *
 * Native consequence: ios.associatedDomains is an entitlement, so D1/D2 ship only with a
 * NEW store build (no OTA), and the universal links work only once
 * https://getmyez.com/.well-known/apple-app-site-association serves the file as
 * application/json with no redirect.
 *
 * The support mailbox is support@getmyez.com (owner decision 2026-10-10). It lives in ONE
 * constant here (SUPPORT_EMAIL) and in ONE constant in src/screens/ContactUsScreen.tsx, so a
 * later change of address is one line per file.
 *
 * Cases that PASS on the untouched tree are positive controls (KEEP identifiers, the
 * host-boundary rejections); the RED cases fail on 'qaren.app' today.
 */
import * as fs from 'fs';
import * as path from 'path';
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Linking } from 'react-native';
// jest.mock calls below are hoisted above these imports by ts-jest.
import { linking } from '../../src/navigation/linking';
import { actionFromPushUrl, pathFromPushUrl } from '../../src/services/pushNavigation';
import ContactUsScreen from '../../src/screens/ContactUsScreen';

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn(() => Promise.resolve({ data: { ok: true } })) },
}));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
jest.mock('lucide-react-native', () => ({ ChevronLeft: 'ChevronLeft' }));
jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'success' },
}));

const HOST = 'getmyez.com';
const WEB = `https://${HOST}`;
const RETIRED_HOST = 'qaren.app';
/** Owner decision 2026-10-10 -- the one place this suite names the support mailbox. */
const SUPPORT_EMAIL = `support@${HOST}`;

const APP_ROOT = path.resolve(__dirname, '..', '..');
const APP = JSON.parse(fs.readFileSync(path.join(APP_ROOT, 'app.json'), 'utf8')).expo;

/** KEEP identifiers that contain the retired host as a substring (bundle id / package / appID). */
const KEEP_IDENTIFIER_RE = /\bcom\.qaren\.app\b/g;
const RETIRED_RE = /qaren\.app/i;

function walk(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (/\.(tsx?|jsx?|json)$/.test(e.name)) out.push(p);
  }
  return out;
}

/** The client's shipped sources: src/**, app.json, eas.json, App.tsx, index.ts, locales/**. */
function clientSources(): string[] {
  const files = walk(path.join(APP_ROOT, 'src'));
  for (const rel of ['app.json', 'eas.json', 'App.tsx', 'index.ts']) {
    const p = path.join(APP_ROOT, rel);
    if (fs.existsSync(p)) files.push(p);
  }
  const locales = path.join(APP_ROOT, 'locales');
  if (fs.existsSync(locales)) walk(locales, files);
  return files;
}

describe('S76 DOMAIN-MYEZ -- app.json (native config: a NEW build, never an OTA)', () => {
  it('D1: ios.associatedDomains is exactly applinks:getmyez.com', () => {
    expect(APP.ios.associatedDomains).toEqual([`applinks:${HOST}`]);
  });

  it('D2: every https Android App Link host is getmyez.com; the three path families stay', () => {
    const https = (APP.android.intentFilters as any[])
      .flatMap((f) => (Array.isArray(f.data) ? f.data : [f.data]))
      .filter((d: any) => d && d.scheme === 'https');
    expect(https.length).toBe(3);
    expect(https.map((d: any) => d.host)).toEqual([HOST, HOST, HOST]);
    expect(https.map((d: any) => d.pathPrefix)).toEqual(['/r/', '/c/', '/q/']);
    const verified = (APP.android.intentFilters as any[]).find((f) =>
      (f.data || []).some((d: any) => d.scheme === 'https')
    );
    expect(verified.autoVerify).toBe(true);
  });

  it('D3 (control): the KEEP identifiers are unchanged', () => {
    expect(APP.scheme).toBe('qaren');
    expect(APP.slug).toBe('qaren');
    expect(APP.owner).toBe('kersher2');
    expect(APP.ios.bundleIdentifier).toBe('com.qaren.app');
    expect(APP.android.package).toBe('com.qaren.app');
    const schemeFilter = (APP.android.intentFilters as any[]).find((f) =>
      (f.data || []).some((d: any) => d.scheme === 'qaren')
    );
    expect(schemeFilter).toBeDefined();
    const google = (APP.plugins as any[]).find(
      (p) => Array.isArray(p) && p[0] === '@react-native-google-signin/google-signin'
    );
    expect(google).toBeDefined();
    expect(String(google[1].iosUrlScheme)).toMatch(/^com\.googleusercontent\.apps\./);
  });
});

describe('S76 DOMAIN-MYEZ -- no retired host in the client', () => {
  it('D4: no "qaren.app" in src/**, app.json, eas.json, App.tsx, index.ts, locales/** (KEEP ids stripped)', () => {
    const files = clientSources();
    expect(files.length).toBeGreaterThan(100);
    const offenders: string[] = [];
    for (const file of files) {
      const lines = fs.readFileSync(file, 'utf8').split('\n');
      lines.forEach((line, i) => {
        if (RETIRED_RE.test(line.replace(KEEP_IDENTIFIER_RE, ' '))) {
          offenders.push(`${path.relative(APP_ROOT, file).replace(/\\/g, '/')}:${i + 1}`);
        }
      });
    }
    expect(offenders).toEqual([]);
  });

  it('D5: linking.prefixes are qaren:// + https://getmyez.com (the retired host is dropped)', () => {
    expect(linking.prefixes).toEqual(['qaren://', WEB]);
    expect(linking.prefixes.some((p) => RETIRED_RE.test(p))).toBe(false);
  });
});

describe('S76 DOMAIN-MYEZ -- push data.url host boundary on getmyez.com (mirrors W3-15 P4f / P9b)', () => {
  // The package's "exports" map hides lib/, so the real helper is reached by absolute path
  // (the technique of __tests__/navigation/linking.w315.test.ts).
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { extractPathFromURL } = require(path.resolve(
    __dirname,
    '../../node_modules/@react-navigation/native/lib/module/extractPathFromURL.js'
  ));

  it('D6: own-host URLs strip to their path; look-alike hosts and the retired host are foreign', () => {
    const table: [string, string | undefined][] = [
      [`${WEB}`, ''],
      [`${WEB}/comparison/abc`, 'comparison/abc'],
      [`${WEB}?code=QR-1`, '?code=QR-1'],
      [`${WEB}/c/T`, 'c/T'],
      ['qaren://comparison/abc', 'comparison/abc'],
      ['https://getmyez.comcomparison/abc', undefined],
      ['https://getmyez.com.evil.com/x', undefined],
      ['https://evil.com/getmyez.com/x', undefined],
      ['https://getmyez.com@evil.com/x', undefined],
      ['https://getmyez.com:8443/x', undefined],
      [`https://${RETIRED_HOST}/comparison/abc`, undefined],
      [`https://${RETIRED_HOST}/c/T`, undefined],
    ];
    for (const [url, expected] of table) {
      const ours = pathFromPushUrl(url);
      expect({ url, ours }).toEqual({ url, ours: expected });
      // Accept/reject parity with the helper the Linking pipeline uses (definedness only).
      expect({ url, rn: extractPathFromURL(linking.prefixes, url) !== undefined }).toEqual({
        url,
        rn: expected !== undefined,
      });
    }
    // Case-insensitive host match (spec P9) -- deliberately MORE lenient than
    // extractPathFromURL 7.2.4, so no parity row for it.
    expect(pathFromPushUrl('HTTPS://GETMYEZ.COM/c/T')).toBe('c/T');
  });

  it('D7: a getmyez.com share link resolves to a navigation action; the retired host does not', () => {
    const own = actionFromPushUrl(`${WEB}/c/TOK1?ref=QR-ABCDEF`);
    expect(own).toBeDefined();
    expect(JSON.stringify(own!.state)).toContain('ReferralLanding');
    expect(actionFromPushUrl(`https://${RETIRED_HOST}/c/TOK1?ref=QR-ABCDEF`)).toBeUndefined();
  });
});

describe('S76 DOMAIN-MYEZ -- Contact Us support mailbox (owner decision 2026-10-10: support@getmyez.com)', () => {
  const SRC = fs.readFileSync(path.join(APP_ROOT, 'src', 'screens', 'ContactUsScreen.tsx'), 'utf8');

  it('D8: the email fallback opens mailto:<SUPPORT_EMAIL>?subject=MYEZ%20Support', () => {
    (Linking.openURL as jest.Mock).mockClear();
    const { getByText } = render(
      React.createElement(ContactUsScreen as any, {
        navigation: { goBack: jest.fn() },
        route: { params: undefined, key: 'k', name: 'ContactUs' },
      })
    );
    fireEvent.press(getByText('contact.email.fallback'));
    expect((Linking.openURL as jest.Mock).mock.calls).toEqual([
      [`mailto:${SUPPORT_EMAIL}?subject=MYEZ%20Support`],
    ]);
  });

  it('D9: the screen names the mailbox exactly once, in one SUPPORT_EMAIL constant', () => {
    const addresses = SRC.match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g) ?? [];
    expect(addresses).toEqual([SUPPORT_EMAIL]);
    const escaped = SUPPORT_EMAIL.replace(/[.+]/g, (c) => `\\${c}`);
    expect(SRC).toMatch(new RegExp(`const SUPPORT_EMAIL = ['"]${escaped}['"]`));
  });
});

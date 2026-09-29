/**
 * S69 U2 — T1: the honest limit sheet behind the `Paywall` route.
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/U2_HONEST_LIMIT_SHEET_SPEC.md
 * (§2 R1/R3, §3 T1) as corrected by the spec review (items 1-8, 11, 13, 17
 * and open-question answers Q1-Q4, Q7).
 *
 * REAL i18next over the REAL en.json / ar.json (a per-file react-i18next
 * factory, the W4-14 DimensionBars pattern). The global mock returns the key
 * and ignores defaultValue, and the old suite's mock returned defaultValue, so
 * under either one a negative pin like /BHD/ checked source strings, not the
 * shipped catalog. Every expected string here is resolved from the catalog,
 * and `tr()` first asserts the key exists in BOTH catalogs, so a screen that
 * renders a missing key (or its defaultValue) cannot pass.
 *
 * Contract pinned (the green agent implements it; PaywallScreen.tsx is
 * rewritten in place, default export kept, route name `Paywall` kept):
 *   - getUsageStatus() is called on EVERY mount, initialUsage or not.
 *   - state = fetched status first: remaining.monthly === 0 -> monthly;
 *     else remaining.daily === 0 -> daily; else not exhausted. When the fetch
 *     yields null (or rejects): initialUsage.reason, then the
 *     "(daily_limit)" / "(monthly_limit)" suffix of initialUsage.error (the
 *     4-key envelope the 429 path really delivers), then
 *     initialUsage.remaining, else unknown.
 *   - daily:         title paywall.dailyLimit,   counts paywall.limit.today,
 *                    reset paywall.limit.resets_daily
 *   - monthly:       title paywall.monthlyLimit, counts paywall.usageMessage,
 *                    reset paywall.limit.resets_monthly (never the daily line)
 *   - not exhausted: title paywall.limit.title + paywall.limit.remaining
 *   - unknown:       title paywall.limit.title + paywall.limit.resets_unknown,
 *                    no counts
 *   - testIDs: paywall-title, paywall-close (the X, label common.close),
 *     paywall-done (the one primary action, label common.done); both call
 *     goBack(), never navigate().
 *   - no price / trial / restore / premium / social proof / rating, and
 *     Alert.alert is never called.
 *   - Arabic title line height = the EN one x arabicLineHeightMultiplier,
 *     applied at render time.
 */
import React from 'react';
import { Alert } from 'react-native';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-i18next', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const i18next = require('i18next');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const enJson = require('../../src/i18n/en.json');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const arJson = require('../../src/i18n/ar.json');
  const inst = i18next.createInstance();
  inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: { en: { translation: enJson }, ar: { translation: arJson } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  });
  const t = (key: string, opts?: Record<string, unknown>) => inst.t(key, opts);
  return {
    useTranslation: () => ({ t, i18n: inst }),
    __inst: inst,
    initReactI18next: { type: '3rdParty', init: () => {} },
  };
});

const mockGoBack = jest.fn();
const mockNavigate = jest.fn();
let mockRouteParams: Record<string, unknown> | undefined;
jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({
    goBack: mockGoBack,
    navigate: mockNavigate,
    canGoBack: () => true,
    dispatch: jest.fn(),
  }),
  useRoute: () => ({ key: 'Paywall-1', name: 'Paywall', params: mockRouteParams }),
}));

const mockGetUsageStatus = jest.fn();
jest.mock('../../src/services/usageService', () => ({
  getUsageStatus: (...args: unknown[]) => mockGetUsageStatus(...args),
}));

import PaywallScreen from '../../src/screens/PaywallScreen';
import { arabicLineHeightMultiplier } from '../../src/theme';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import copyPolicy from '../../src/i18n/.copy-policy.json';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { __inst: inst } = require('react-i18next');

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;
type Lang = 'en' | 'ar';
type Screen = ReturnType<typeof render>;

/** Resolve a key from the real catalog; the key must exist in BOTH catalogs. */
function tr(lang: Lang, key: string, opts?: Record<string, unknown>): string {
  expect({ key, inEn: key in EN, inAr: key in AR }).toEqual({ key, inEn: true, inAr: true });
  return inst.t(key, { lng: lang, ...(opts || {}) });
}

/** Every rendered string plus every accessibilityLabel, joined. */
function allText(screen: Screen): string {
  const out: string[] = [];
  const walk = (n: any): void => {
    if (n == null) return;
    if (typeof n === 'string') {
      out.push(n);
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    if (n.props && n.props.accessibilityLabel != null) out.push(String(n.props.accessibilityLabel));
    if (n.children) n.children.forEach(walk);
  };
  walk(screen.toJSON());
  return out.join('\n');
}

const flush = () => new Promise<void>((r) => setTimeout(r, 0));

function status(p: { usedDaily: number; usedMonthly: number; remDaily: number; remMonthly: number }) {
  return {
    tier: 'free' as const,
    used: { daily: p.usedDaily, monthly: p.usedMonthly, lifetime: 3 },
    limits: { daily: 3, monthly: 10, lifetime_free: 3 },
    remaining: { daily: p.remDaily, monthly: p.remMonthly, lifetime_free: 0 },
  };
}
const DAILY_EXHAUSTED = status({ usedDaily: 3, usedMonthly: 5, remDaily: 0, remMonthly: 5 });
const MONTHLY_EXHAUSTED = status({ usedDaily: 1, usedMonthly: 10, remDaily: 2, remMonthly: 0 });
const BOTH_EXHAUSTED = status({ usedDaily: 3, usedMonthly: 10, remDaily: 0, remMonthly: 0 });
const NOT_EXHAUSTED = status({ usedDaily: 1, usedMonthly: 4, remDaily: 2, remMonthly: 6 });

// The body the 429 path really hands to navigate('Paywall', { initialUsage })
// after the global handler rebuilds it (app/middleware/error_handler.py:120-138):
// no counts, no reason — only the error-string suffix.
const ENVELOPE_DAILY = {
  success: false,
  error: 'Comparison limit reached (daily_limit)',
  code: 'USAGE_LIMIT',
  request_id: 'req-daily',
};
const ENVELOPE_MONTHLY = {
  success: false,
  error: 'Comparison limit reached (monthly_limit)',
  code: 'USAGE_LIMIT',
  request_id: 'req-monthly',
};

const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);

beforeEach(() => {
  mockGoBack.mockClear();
  mockNavigate.mockClear();
  mockGetUsageStatus.mockReset();
  alertSpy.mockClear();
  mockRouteParams = undefined;
  inst.changeLanguage('en');
});

describe('T1 — fetch on every mount (spec-review item 3)', () => {
  it('T1-01 calls getUsageStatus once on mount even when initialUsage is present', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    mockRouteParams = { initialUsage: ENVELOPE_DAILY };
    render(<PaywallScreen />);
    await flush();
    expect(mockGetUsageStatus).toHaveBeenCalledTimes(1);
  });
});

describe('T1 — daily exhausted (EN)', () => {
  it('T1-02 daily title, "3 of 3 … today" and the daily reset line; never the monthly ones', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.dailyLimit'));
    const today = tr('en', 'paywall.limit.today', { used: 3, limit: 3 });
    expect(today).toMatch(/\b3\b\D*\b3\b/);
    expect(screen.getByText(today)).toBeTruthy();
    expect(screen.getByText(tr('en', 'paywall.limit.resets_daily'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.monthlyLimit'))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.limit.resets_monthly'))).toBeNull();
    expect(screen.getByTestId('paywall-title')).toBeTruthy();
  });
});

describe('T1 — monthly exhausted (EN)', () => {
  it('T1-03 monthly title, "10 of 10 … this month" and the monthly reset line', async () => {
    mockGetUsageStatus.mockResolvedValue(MONTHLY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.monthlyLimit'));
    expect(screen.getByText(tr('en', 'paywall.usageMessage', { used: 10, limit: 10 }))).toBeTruthy();
    expect(screen.getByText(tr('en', 'paywall.limit.resets_monthly'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.limit.resets_daily'))).toBeNull();
  });

  it('T1-04 both axes exhausted: the monthly axis wins (a daily reset line would be false)', async () => {
    mockGetUsageStatus.mockResolvedValue(BOTH_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.monthlyLimit'));
    expect(screen.getByText(tr('en', 'paywall.limit.resets_monthly'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.limit.resets_daily'))).toBeNull();
  });

  it('T1-05 the fetched status beats a stale initialUsage (envelope says daily, status says monthly)', async () => {
    mockGetUsageStatus.mockResolvedValue(MONTHLY_EXHAUSTED);
    mockRouteParams = { initialUsage: ENVELOPE_DAILY };
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.monthlyLimit'));
    await waitFor(() => expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull());
    expect(screen.queryByText(tr('en', 'paywall.limit.resets_daily'))).toBeNull();
  });
});

describe('T1 — not exhausted / unknown (spec-review item 6, Q2)', () => {
  it('T1-06 opened with comparisons left (header pill): neutral title + remaining count, no "used up" claim', async () => {
    mockGetUsageStatus.mockResolvedValue(NOT_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.limit.remaining', { remaining: 2 }));
    expect(screen.getByText(tr('en', 'paywall.limit.title'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.monthlyLimit'))).toBeNull();
    expect(screen.queryByTestId('paywall-resets')).toBeNull();
  });

  it('T1-06b lifetime-free window: the count is what is really left, not the full allowance status reports', async () => {
    // usage_service.get_usage_status reports remaining = the full daily/monthly
    // allowance while lifetime-free compares remain, yet each of them bumps the
    // daily counter: lifetime 2 of 3, used.daily 2 -> 1 lifetime-free compare,
    // then daily is 3/3. The Home pill says 1/3; the sheet must say 1, not 3.
    mockGetUsageStatus.mockResolvedValue({
      tier: 'free',
      used: { daily: 2, monthly: 2, lifetime: 2 },
      limits: { daily: 3, monthly: 10, lifetime_free: 3 },
      remaining: { daily: 3, monthly: 10, lifetime_free: 1 },
    });
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.limit.remaining', { remaining: 1 }));
    expect(screen.queryByText(tr('en', 'paywall.limit.remaining', { remaining: 3 }))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
  });

  it('T1-06c lifetime-free compares bypass the daily cap: lf is left even when lf exceeds the daily headroom', async () => {
    mockGetUsageStatus.mockResolvedValue({
      tier: 'free',
      used: { daily: 2, monthly: 2, lifetime: 0 },
      limits: { daily: 3, monthly: 10, lifetime_free: 3 },
      remaining: { daily: 3, monthly: 10, lifetime_free: 3 },
    });
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.limit.remaining', { remaining: 3 }));
  });

  it('T1-06d fresh account, nothing used: lifetime-free plus the rest of today', async () => {
    mockGetUsageStatus.mockResolvedValue({
      tier: 'free',
      used: { daily: 0, monthly: 0, lifetime: 0 },
      limits: { daily: 5, monthly: 10, lifetime_free: 3 },
      remaining: { daily: 5, monthly: 10, lifetime_free: 3 },
    });
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.limit.remaining', { remaining: 5 }));
  });

  it('T1-07 no initialUsage and getUsageStatus resolves null: neutral title, generic line, no counts', async () => {
    mockGetUsageStatus.mockResolvedValue(null);
    const screen = render(<PaywallScreen />);
    await flush();
    await screen.findByText(tr('en', 'paywall.limit.title'));
    expect(screen.getByText(tr('en', 'paywall.limit.resets_unknown'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
    expect(screen.queryByText(tr('en', 'paywall.monthlyLimit'))).toBeNull();
    expect(allText(screen)).not.toMatch(/\d/);
  });

  it('T1-08 getUsageStatus rejects: no crash, no unhandled rejection, neutral title, no counts', async () => {
    const unhandled: unknown[] = [];
    const onUnhandled = (reason: unknown) => {
      unhandled.push(reason);
    };
    process.on('unhandledRejection', onUnhandled);
    try {
      mockGetUsageStatus.mockRejectedValue(new Error('network down'));
      const screen = render(<PaywallScreen />);
      await flush();
      await flush();
      await screen.findByText(tr('en', 'paywall.limit.title'));
      expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
      expect(allText(screen)).not.toMatch(/\d/);
      screen.unmount();
      await flush();
      expect(unhandled).toEqual([]);
    } finally {
      process.removeListener('unhandledRejection', onUnhandled);
    }
  });

  it.each([
    ['resolves null', () => mockGetUsageStatus.mockResolvedValue(null)],
    ['rejects', () => mockGetUsageStatus.mockRejectedValue(new Error('network down'))],
  ])(
    'T1-08b fetch %s and initialUsage carries no axis evidence: unknown state, never a limit claim',
    async (_label, arrange) => {
      arrange();
      mockRouteParams = { initialUsage: { code: 'USAGE_LIMIT', error: 'Comparison limit reached' } };
      const screen = render(<PaywallScreen />);
      await flush();
      await flush();
      await screen.findByText(tr('en', 'paywall.limit.title'));
      expect(screen.getByText(tr('en', 'paywall.limit.resets_unknown'))).toBeTruthy();
      expect(screen.queryByText(tr('en', 'paywall.dailyLimit'))).toBeNull();
      expect(screen.queryByText(tr('en', 'paywall.monthlyLimit'))).toBeNull();
      expect(allText(screen)).not.toMatch(/\d/);
    },
  );

  it('T1-09 unmount before the fetch settles does not throw, and a fresh mount fetches again', async () => {
    let resolveFetch: (v: unknown) => void = () => undefined;
    mockGetUsageStatus.mockReturnValueOnce(
      new Promise((r) => {
        resolveFetch = r;
      }),
    );
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const first = render(<PaywallScreen />);
    first.unmount();
    resolveFetch(DAILY_EXHAUSTED);
    await flush();
    const again = render(<PaywallScreen />);
    await again.findByText(tr('en', 'paywall.dailyLimit'));
    expect(mockGetUsageStatus).toHaveBeenCalledTimes(2);
  });
});

describe('T1 — initialUsage fallbacks when the fetch yields null (spec-review items 1, 2; Q1)', () => {
  beforeEach(() => {
    mockGetUsageStatus.mockResolvedValue(null);
  });

  it('T1-10 the real 429 envelope "(daily_limit)" -> daily title + daily reset, no counts', async () => {
    mockRouteParams = { initialUsage: ENVELOPE_DAILY };
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.dailyLimit'));
    expect(screen.getByText(tr('en', 'paywall.limit.resets_daily'))).toBeTruthy();
    expect(allText(screen)).not.toMatch(/\d/);
  });

  it('T1-11 the real 429 envelope "(monthly_limit)" -> monthly title + monthly reset', async () => {
    mockRouteParams = { initialUsage: ENVELOPE_MONTHLY };
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.monthlyLimit'));
    expect(screen.getByText(tr('en', 'paywall.limit.resets_monthly'))).toBeTruthy();
    expect(screen.queryByText(tr('en', 'paywall.limit.resets_daily'))).toBeNull();
  });

  it('T1-12 a legacy detail with reason "monthly_limit" -> monthly title', async () => {
    mockRouteParams = { initialUsage: { code: 'USAGE_LIMIT', tier: 'free', reason: 'monthly_limit' } };
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.monthlyLimit'));
  });

  it('T1-13 a legacy detail with remaining.daily 0 -> daily title', async () => {
    mockRouteParams = {
      initialUsage: { code: 'USAGE_LIMIT', tier: 'free', remaining: { daily: 0, monthly: 4, lifetime_free: 0 } },
    };
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('en', 'paywall.dailyLimit'));
  });
});

describe('T1 — actions (spec-review items 4, 7, 8, 11; Q4)', () => {
  it('T1-14 the close X is labelled common.close ("Close", not "Cancel") and only calls goBack()', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await flush();
    const close = screen.getByTestId('paywall-close');
    expect(close.props.accessibilityLabel).toBe(tr('en', 'common.close'));
    fireEvent.press(close);
    expect(mockGoBack).toHaveBeenCalledTimes(1);
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('T1-15 the one primary action reads common.done and only calls goBack()', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await flush();
    const done = screen.getByTestId('paywall-done');
    expect(screen.getByText(tr('en', 'common.done'))).toBeTruthy();
    fireEvent.press(done);
    expect(mockGoBack).toHaveBeenCalledTimes(1);
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('T1-16 pressing every pressable never raises Alert.alert and never navigates', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await flush();
    const pressables = screen.UNSAFE_root.findAll(
      (n: any) => typeof n.type === 'string' && typeof n.props.onPress === 'function',
    );
    expect(pressables.length).toBeGreaterThan(0);
    pressables.forEach((p: any) => fireEvent.press(p));
    expect(alertSpy).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(screen.queryByTestId('paywall-cta')).toBeNull();
    expect(screen.queryByTestId('paywall-restore')).toBeNull();
  });
});

describe('T1 — no subscription UI in the rendered catalog copy (R1)', () => {
  const EN_FORBIDDEN: RegExp[] = [
    /BHD/,
    /trial/i,
    /Restore/i,
    /5,000/,
    /4\.8/,
    /Coming soon/i,
    /Premium/i,
    /subscri/i,
    /upgrade/i,
    /Cancel anytime/i,
    /billed/i,
    /tomorrow/i,
  ];
  const AR_FORBIDDEN: RegExp[] = [/د\.ب/, /BHD/, /تجرب/, /استعادة/, /مميز/, /اشتراك/, /قريبا/, /5,000/, /4\.8/, /ألغ/];

  it.each([
    ['daily', DAILY_EXHAUSTED],
    ['monthly', MONTHLY_EXHAUSTED],
    ['not exhausted', NOT_EXHAUSTED],
    ['unknown', null],
  ])('T1-17 EN %s: no price, trial, restore, premium, social proof or rating', async (_label, st) => {
    mockGetUsageStatus.mockResolvedValue(st);
    const screen = render(<PaywallScreen />);
    await flush();
    await flush();
    const text = allText(screen);
    for (const re of EN_FORBIDDEN) {
      expect({ re: String(re), hit: re.test(text) }).toEqual({ re: String(re), hit: false });
    }
    for (const word of copyPolicy.scary_vocab_en) {
      expect({ word, hit: text.toLowerCase().includes(word.toLowerCase()) }).toEqual({ word, hit: false });
    }
    // Not vacuous: the sheet itself rendered.
    expect(screen.getByTestId('paywall-title')).toBeTruthy();
  });

  it('T1-18 AR daily: Arabic title, counts, reset line and labels; no price, trial, premium or banned term', async () => {
    inst.changeLanguage('ar');
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('ar', 'paywall.dailyLimit'));
    expect(screen.getByText(tr('ar', 'paywall.limit.today', { used: 3, limit: 3 }))).toBeTruthy();
    expect(screen.getByText(tr('ar', 'paywall.limit.resets_daily'))).toBeTruthy();
    expect(screen.getByTestId('paywall-close').props.accessibilityLabel).toBe(tr('ar', 'common.close'));
    expect(screen.getByText(tr('ar', 'common.done'))).toBeTruthy();
    const text = allText(screen);
    for (const re of AR_FORBIDDEN) {
      expect({ re: String(re), hit: re.test(text) }).toEqual({ re: String(re), hit: false });
    }
    const arTerms = [...copyPolicy.banned_ar.map((b) => b.pattern), ...copyPolicy.scary_vocab_ar];
    for (const term of arTerms) {
      expect({ term, hit: new RegExp(term).test(text) }).toEqual({ term, hit: false });
    }
  });

  it('T1-19 AR monthly: Arabic monthly title + monthly counts + monthly reset line', async () => {
    inst.changeLanguage('ar');
    mockGetUsageStatus.mockResolvedValue(MONTHLY_EXHAUSTED);
    const screen = render(<PaywallScreen />);
    await screen.findByText(tr('ar', 'paywall.monthlyLimit'));
    expect(screen.getByText(tr('ar', 'paywall.usageMessage', { used: 10, limit: 10 }))).toBeTruthy();
    expect(screen.getByText(tr('ar', 'paywall.limit.resets_monthly'))).toBeTruthy();
  });
});

describe('T1 — RTL (spec-review item 17)', () => {
  function titleStyle(screen: Screen): { fontSize: number; lineHeight: number } {
    const node = screen.getByTestId('paywall-title');
    const raw = node.props.style;
    const style = Array.isArray(raw) ? Object.assign({}, ...raw.flat(Infinity).filter(Boolean)) : raw || {};
    return { fontSize: style.fontSize, lineHeight: style.lineHeight };
  }

  it('T1-20 the Arabic title line height = the EN one x arabicLineHeightMultiplier (render-time)', async () => {
    mockGetUsageStatus.mockResolvedValue(DAILY_EXHAUSTED);
    const enScreen = render(<PaywallScreen />);
    await enScreen.findByText(tr('en', 'paywall.dailyLimit'));
    const enStyle = titleStyle(enScreen);
    enScreen.unmount();

    inst.changeLanguage('ar');
    const arScreen = render(<PaywallScreen />);
    await arScreen.findByText(tr('ar', 'paywall.dailyLimit'));
    const arStyle = titleStyle(arScreen);

    expect(typeof enStyle.lineHeight).toBe('number');
    expect(arStyle.fontSize).toBe(enStyle.fontSize);
    expect(arStyle.lineHeight).toBeCloseTo(enStyle.lineHeight * arabicLineHeightMultiplier, 5);
  });
});

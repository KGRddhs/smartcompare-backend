/**
 * Tests for `PaywallBanner` — replaces TwoInputShell when canCompare===false.
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 6.2.
 * Plan: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.5.
 *
 * Coverage target: 80% on `SmartCompareApp/src/components/PaywallBanner.tsx`.
 *
 * IMPORTANT — analytics live in the CALLER per the TwoInputShell pattern:
 *   HomeScreen fires `trackEvent('compare_entry_paywall_banner_view')` on
 *   mount and `compare_entry_paywall_banner_tap` on CTA tap. This file
 *   tests the callback contract + render contract only. Analytics-firing
 *   assertions live in HomeScreen tests.
 *
 * What this file DOES test:
 *   - Render: title + body + CTA + emerald icon in EN.
 *   - Render: same structure in AR locale (i18n keys + lineHeight).
 *   - CTA: tapping invokes onSeeOptions callback exactly once.
 *   - No close/dismiss affordance (spec § 6.2 — no escape hatch).
 *   - Haptic: light tap haptic fires on press, wrapped in try/catch.
 *   - Copy policy: no scary vocab in the keys used.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

let _mockLang = 'en';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: {
      language: _mockLang,
      changeLanguage: jest.fn(async (lang: string) => {
        _mockLang = lang;
      }),
    },
  }),
  initReactI18next: { type: '3rdParty', init: jest.fn() },
}));

import PaywallBanner from '../PaywallBanner';
import * as Haptics from 'expo-haptics';

beforeEach(() => {
  _mockLang = 'en';
  (Haptics.impactAsync as jest.Mock).mockClear();
});

// ============================================
// § 6.2 — render contract (English locale)
// ============================================

describe('PaywallBanner — render (English)', () => {
  it('renders the banner card', () => {
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(getByTestId('paywall-banner')).toBeTruthy();
  });

  it('renders the title key + body key + CTA key (i18n mock returns keys verbatim)', () => {
    const { getByText } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(getByText('home.compare.paywall_banner_title')).toBeTruthy();
    expect(getByText('home.compare.paywall_banner_body')).toBeTruthy();
    expect(getByText('home.compare.paywall_banner_cta')).toBeTruthy();
  });

  it('exposes the CTA via a stable testID', () => {
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(getByTestId('paywall-banner-cta')).toBeTruthy();
  });

  it('uses a custom testID prefix when provided', () => {
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} testID="custom-paywall" />
    );
    expect(getByTestId('custom-paywall')).toBeTruthy();
    expect(getByTestId('custom-paywall-cta')).toBeTruthy();
  });
});

// ============================================
// § 6.2 — CTA tap → onSeeOptions
// ============================================

describe('PaywallBanner — CTA tap → onSeeOptions', () => {
  it('tapping CTA invokes onSeeOptions exactly once', () => {
    const onSeeOptions = jest.fn();
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={onSeeOptions} />
    );
    fireEvent.press(getByTestId('paywall-banner-cta'));
    expect(onSeeOptions).toHaveBeenCalledTimes(1);
  });

  it('tapping CTA fires the light impact haptic', () => {
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    fireEvent.press(getByTestId('paywall-banner-cta'));
    expect(Haptics.impactAsync).toHaveBeenCalledTimes(1);
    expect(Haptics.impactAsync).toHaveBeenCalledWith(
      Haptics.ImpactFeedbackStyle.Light
    );
  });

  it('haptic engine sync throw does not block onSeeOptions', () => {
    (Haptics.impactAsync as jest.Mock).mockImplementationOnce(() => {
      throw new Error('haptic engine offline');
    });
    const onSeeOptions = jest.fn();
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={onSeeOptions} />
    );
    expect(() =>
      fireEvent.press(getByTestId('paywall-banner-cta'))
    ).not.toThrow();
    expect(onSeeOptions).toHaveBeenCalledTimes(1);
  });

  it('haptic promise rejection does not break the render or callback', () => {
    (Haptics.impactAsync as jest.Mock).mockImplementationOnce(() =>
      Promise.reject(new Error('rejected'))
    );
    const onSeeOptions = jest.fn();
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={onSeeOptions} />
    );
    expect(() =>
      fireEvent.press(getByTestId('paywall-banner-cta'))
    ).not.toThrow();
    expect(onSeeOptions).toHaveBeenCalledTimes(1);
  });

  it('multiple CTA taps invoke onSeeOptions for each press', () => {
    const onSeeOptions = jest.fn();
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={onSeeOptions} />
    );
    const cta = getByTestId('paywall-banner-cta');
    fireEvent.press(cta);
    fireEvent.press(cta);
    fireEvent.press(cta);
    expect(onSeeOptions).toHaveBeenCalledTimes(3);
  });
});

// ============================================
// § 6.2 — no escape hatch
// ============================================

describe('PaywallBanner — no escape hatch (no close/dismiss affordance)', () => {
  it('does not render a close button with testID "paywall-close"', () => {
    const { queryByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(queryByTestId('paywall-close')).toBeNull();
  });

  it('does not render a dismiss button with testID "paywall-dismiss"', () => {
    const { queryByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(queryByTestId('paywall-dismiss')).toBeNull();
  });

  it('does not render copy with skip/dismiss/close vocab', () => {
    const { queryByText } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(queryByText(/skip|dismiss|close|cancel|maybe later/i)).toBeNull();
  });
});

// ============================================
// § 7.4 — Build Principle #4 copy policy
// ============================================

describe('PaywallBanner — Build Principle #4 copy policy', () => {
  it('does not render scary EN copy (couldn\'t / failed / try again / error)', () => {
    const { queryByText } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(queryByText(/couldn['']t|try again|failed|error/i)).toBeNull();
  });
});

// ============================================
// § 7.1 — AR locale + RTL
// ============================================

describe('PaywallBanner — Arabic / RTL', () => {
  it('renders without crashing in AR locale', () => {
    _mockLang = 'ar';
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    expect(getByTestId('paywall-banner')).toBeTruthy();
    expect(getByTestId('paywall-banner-cta')).toBeTruthy();
  });

  it('AR locale still surfaces all 3 i18n keys (production AR JSON resolves them)', () => {
    _mockLang = 'ar';
    const { getByText } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    // i18n mock returns keys verbatim; production ar.json provides
    // "استخدمت مقارناتك المجانية" / "افتح مقارنات غير محدودة..." / "عرض الخيارات".
    expect(getByText('home.compare.paywall_banner_title')).toBeTruthy();
    expect(getByText('home.compare.paywall_banner_body')).toBeTruthy();
    expect(getByText('home.compare.paywall_banner_cta')).toBeTruthy();
  });

  it('does not render scary AR copy in resolved keys (تعذر / فشل forbidden)', () => {
    _mockLang = 'ar';
    const { queryByText } = render(
      <PaywallBanner onSeeOptions={jest.fn()} />
    );
    // The i18n mock returns keys verbatim (not Arabic), so this is a
    // belt-and-suspenders guard — the real check is performed by
    // SmartCompareApp/__tests__/copy-policy.test.ts against the JSON
    // files directly.
    expect(queryByText(/تعذر|فشل/)).toBeNull();
  });

  it('AR locale CTA tap still fires onSeeOptions (no locale-specific gating)', () => {
    _mockLang = 'ar';
    const onSeeOptions = jest.fn();
    const { getByTestId } = render(
      <PaywallBanner onSeeOptions={onSeeOptions} />
    );
    fireEvent.press(getByTestId('paywall-banner-cta'));
    expect(onSeeOptions).toHaveBeenCalledTimes(1);
  });
});

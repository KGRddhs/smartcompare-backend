/**
 * PaywallScreen Bundle E — per-screen integration test (T-S1.3b).
 *
 * Frontend ship: F-S1.1 PaywallScreen composition (commit 07dadbb).
 * Reference: docs/claude-design-handoff/ui_kits/mobile/PaywallScreen.jsx +
 * screenshots/paywall.png. Design doc § 6 acceptance checkpoints:
 *
 *   - HeroVisual with 3 staggered mini-vs pairs (testIDs
 *     paywall-hero-tile-{0,1,2})
 *   - PlanCardLarge × 2 with "3 days free · Best value" eyebrow on yearly
 *     (testIDs paywall-plan-yearly, paywall-plan-monthly)
 *   - Trial timeline 3 rows (Today / In 2 days / In 3 days), testID
 *     paywall-timeline
 *   - 4 FeatureLine rows w/ emerald-circle check
 *   - Sticky CTA at testID paywall-cta with "Start My 3-Day Free Trial"
 *     label; tap → Alert.alert "Coming soon" (Tap Payments not wired yet)
 *   - Close button testID paywall-close → navigation.goBack()
 *   - Restore link testID paywall-restore → Alert.alert "Coming soon"
 *   - Trust line: "No payment due now · Cancel anytime"
 *
 * No editorial endpoint mocks needed for this screen — paywall reads only
 * route.params.initialUsage + getUsageStatus(). Mocking getUsageStatus
 * keeps the test deterministic.
 */
import React from 'react';
import { Alert } from 'react-native';
import { render, fireEvent } from '@testing-library/react-native';
import PaywallScreen from '../../src/screens/PaywallScreen';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? _key,
  }),
}));

const goBack = jest.fn();
jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({ goBack, navigate: jest.fn() }),
  useRoute: () => ({ params: { initialUsage: { used: 3, total: 3, canCompare: false } } }),
}));

jest.mock('../../src/services/usageService', () => ({
  getUsageStatus: jest.fn().mockResolvedValue({ used: 3, total: 3, canCompare: false }),
}));

jest.mock('lucide-react-native', () => ({
  X: 'X',
  Check: 'Check',
  Star: 'Star',
}));

// Capture Alert.alert calls
const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);

describe('PaywallScreen — Bundle E composition (F-S1.1)', () => {
  beforeEach(() => {
    goBack.mockClear();
    alertSpy.mockClear();
  });

  it('renders the close button + invokes navigation.goBack on press', () => {
    const { getByTestId } = render(<PaywallScreen />);
    const close = getByTestId('paywall-close');
    expect(close).toBeTruthy();
    fireEvent.press(close);
    expect(goBack).toHaveBeenCalledTimes(1);
  });

  it('renders 3 hero-tile vs-pairs', () => {
    const { getByTestId } = render(<PaywallScreen />);
    expect(getByTestId('paywall-hero-tile-0')).toBeTruthy();
    expect(getByTestId('paywall-hero-tile-1')).toBeTruthy();
    expect(getByTestId('paywall-hero-tile-2')).toBeTruthy();
  });

  it('renders both plan cards (yearly + monthly)', () => {
    const { getByTestId } = render(<PaywallScreen />);
    expect(getByTestId('paywall-plan-yearly')).toBeTruthy();
    expect(getByTestId('paywall-plan-monthly')).toBeTruthy();
  });

  it('yearly plan eyebrow contains "3 DAYS FREE" + "BEST VALUE"', () => {
    const { getByText } = render(<PaywallScreen />);
    // The default-value strings from useTranslation mock surface as plain
    // text — confirms the eyebrow copy from the JSX-wins spec.
    expect(getByText(/3 DAYS FREE/)).toBeTruthy();
    expect(getByText(/BEST VALUE/)).toBeTruthy();
  });

  it('renders trial timeline card with 3 anchor rows (Today / In 2 days / In 3 days)', () => {
    const { getByTestId, getByText } = render(<PaywallScreen />);
    expect(getByTestId('paywall-timeline')).toBeTruthy();
    expect(getByText('Today')).toBeTruthy();
    expect(getByText('In 2 days')).toBeTruthy();
    expect(getByText('In 3 days')).toBeTruthy();
  });

  it('renders all 4 feature lines from § 6 spec', () => {
    const { getByText } = render(<PaywallScreen />);
    expect(getByText('70 comparisons per month')).toBeTruthy();
    expect(getByText('Full price history across 25+ GCC retailers')).toBeTruthy();
    expect(getByText('Priority processing — results in under 8 seconds')).toBeTruthy();
    expect(getByText('Ad-free, always')).toBeTruthy();
  });

  it('renders sticky CTA "Start My 3-Day Free Trial"', () => {
    const { getByTestId, getByText } = render(<PaywallScreen />);
    expect(getByTestId('paywall-cta')).toBeTruthy();
    expect(getByText('Start My 3-Day Free Trial')).toBeTruthy();
  });

  it('CTA press fires Alert.alert with "Coming soon" copy (Tap Payments not wired)', () => {
    const { getByTestId } = render(<PaywallScreen />);
    fireEvent.press(getByTestId('paywall-cta'));
    expect(alertSpy).toHaveBeenCalledTimes(1);
    const [title] = alertSpy.mock.calls[0];
    expect(title).toBe('Coming soon');
  });

  it('Restore link press fires Alert.alert "Coming soon"', () => {
    const { getByTestId } = render(<PaywallScreen />);
    fireEvent.press(getByTestId('paywall-restore'));
    expect(alertSpy).toHaveBeenCalledTimes(1);
  });

  it('renders trust-line "No payment due now · Cancel anytime"', () => {
    const { getByText } = render(<PaywallScreen />);
    expect(getByText('No payment due now · Cancel anytime')).toBeTruthy();
  });

  it('renders Terms + Privacy + Restore links in the footer link row', () => {
    const { getByText, getByTestId } = render(<PaywallScreen />);
    expect(getByText('Terms')).toBeTruthy();
    expect(getByText('Privacy')).toBeTruthy();
    // Restore has a stable testID for the Alert-trigger test above.
    expect(getByTestId('paywall-restore')).toBeTruthy();
  });

  it('renders without crashing when route.params.initialUsage is absent', () => {
    // Cover the useEffect fallback path: getUsageStatus() is called when
    // initialUsage missing. Override useRoute IN-PLACE for this test only
    // — DO NOT use jest.resetModules + require, which creates a dual-React
    // instance (FreshPaywall gets a different react module than the test's
    // own React, breaking the hooks dispatcher → useState returns null).
    // Caught by frontend cross-QA 2026-05-26.
    const navMod = require('@react-navigation/native');
    const originalUseRoute = navMod.useRoute;
    navMod.useRoute = () => ({ params: {} });
    try {
      expect(() => render(<PaywallScreen />)).not.toThrow();
    } finally {
      navMod.useRoute = originalUseRoute;
    }
  });
});

describe('PaywallScreen — Build Principle #4 (no scary copy)', () => {
  it('contains no "Failed to" / "couldn\'t" / "try again" strings in rendered tree', () => {
    const { toJSON } = render(<PaywallScreen />);
    const tree = JSON.stringify(toJSON()).toLowerCase();
    expect(tree).not.toContain('failed to');
    expect(tree).not.toContain("couldn't");
    expect(tree).not.toContain('try again');
    // AR forbidden vocab — not expected in EN render but guard against
    // accidental embed of an AR fallback string in the EN tree.
    expect(tree).not.toContain('تعذر');
    expect(tree).not.toContain('فشل');
  });
});

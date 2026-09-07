/**
 * A9 — the blocking update screen.
 *
 * This is the one screen in the app with no way out, so the tests pin the
 * two things that decide whether a blocked user can actually unblock
 * themselves: the store CTA fires with the URL the server supplied, and
 * when the server supplied none the screen still tells them what to do
 * instead of showing a button that goes nowhere.
 *
 * RTL: the screen is centred and carries no directional icon and no
 * physical `textAlign: left/right`, so it is correct in both
 * `I18nManager.isRTL` branches — asserted structurally below, alongside
 * the Arabic line-height branch (design § 1's 1.7x multiplier).
 */
import * as fs from 'fs';
import * as path from 'path';
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { I18nManager, Linking } from 'react-native';
import { useTranslation } from 'react-i18next';
import UpdateRequiredScreen from '../src/screens/UpdateRequiredScreen';
import { arabicLineHeightMultiplier, typography } from '../src/theme';

const STORE_URL = 'https://apps.apple.com/app/id1';

function flatten(style: unknown): Record<string, unknown> {
  if (Array.isArray(style)) {
    return Object.assign({}, ...style.filter(Boolean).map(flatten));
  }
  return (style as Record<string, unknown>) ?? {};
}

beforeEach(() => {
  jest.clearAllMocks();
  (I18nManager as any).isRTL = false;
  useTranslation().i18n.changeLanguage('en');
});

afterEach(() => {
  (I18nManager as any).isRTL = false;
  useTranslation().i18n.changeLanguage('en');
});

describe('UpdateRequiredScreen', () => {
  it('renders the update message with a store CTA when a url is supplied', () => {
    const { getByTestId, queryByTestId } = render(
      <UpdateRequiredScreen updateUrl={STORE_URL} />
    );

    expect(getByTestId('update-required-title')).toBeTruthy();
    expect(getByTestId('update-required-body')).toBeTruthy();
    expect(getByTestId('update-required-cta')).toBeTruthy();
    expect(queryByTestId('update-required-manual')).toBeNull();
  });

  it('opens the supplied store url when the CTA is pressed', () => {
    const { getByTestId } = render(<UpdateRequiredScreen updateUrl={STORE_URL} />);

    fireEvent.press(getByTestId('update-required-cta'));

    expect(Linking.openURL).toHaveBeenCalledTimes(1);
    expect(Linking.openURL).toHaveBeenCalledWith(STORE_URL);
  });

  it.each([[null], [undefined], ['']])(
    'shows the manual instruction instead of a dead button when updateUrl is %p',
    (url) => {
      const { getByTestId, queryByTestId } = render(
        <UpdateRequiredScreen updateUrl={url as string | null | undefined} />
      );

      expect(getByTestId('update-required-manual')).toBeTruthy();
      expect(queryByTestId('update-required-cta')).toBeNull();
      expect(Linking.openURL).not.toHaveBeenCalled();
    }
  );

  it('survives a Linking.openURL that rejects (store app unavailable)', () => {
    (Linking.openURL as jest.Mock).mockRejectedValueOnce(new Error('no handler'));
    const { getByTestId } = render(<UpdateRequiredScreen updateUrl={STORE_URL} />);

    // An unhandled rejection here would crash the one screen the user
    // cannot navigate away from.
    expect(() => fireEvent.press(getByTestId('update-required-cta'))).not.toThrow();
  });

  it('uses the English line-heights under EN', () => {
    const { getByTestId } = render(<UpdateRequiredScreen updateUrl={STORE_URL} />);

    expect(flatten(getByTestId('update-required-title').props.style).lineHeight).toBe(
      typography.display.lineHeight
    );
    expect(flatten(getByTestId('update-required-body').props.style).lineHeight).toBe(
      typography.body.lineHeight
    );
  });

  it('applies the Arabic 1.7x line-height multiplier under AR', () => {
    useTranslation().i18n.changeLanguage('ar');

    const { getByTestId } = render(<UpdateRequiredScreen updateUrl={STORE_URL} />);

    expect(flatten(getByTestId('update-required-title').props.style).lineHeight).toBeCloseTo(
      typography.display.lineHeight * arabicLineHeightMultiplier
    );
    expect(flatten(getByTestId('update-required-body').props.style).lineHeight).toBeCloseTo(
      typography.body.lineHeight * arabicLineHeightMultiplier
    );
  });

  it('renders the same tree in both I18nManager.isRTL branches', () => {
    const ltr = render(<UpdateRequiredScreen updateUrl={STORE_URL} />).toJSON();
    (I18nManager as any).isRTL = true;
    const rtl = render(<UpdateRequiredScreen updateUrl={STORE_URL} />).toJSON();

    // Honest scope: this proves the screen renders under both flags and
    // produces no direction-dependent output. It cannot catch a physical
    // style added to StyleSheet.create (evaluated once at import), which
    // is why the source-level fence below exists as well.
    expect(JSON.stringify(rtl)).toBe(JSON.stringify(ltr));
  });

  it('carries no physical textAlign and no directional icon (RTL fences)', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../src/screens/UpdateRequiredScreen.tsx'),
      'utf8'
    );
    // The M21 W4 fences (__tests__/rtl/*) enforce these repo-wide by an
    // explicit file table; a new screen has to hold the same line or it
    // silently bypasses the sweep.
    expect(src).not.toMatch(/textAlign:\s*'(left|right)'/);
    expect(src).not.toMatch(/<(ArrowLeft|ChevronLeft|ChevronRight)\b/);
    expect(src).not.toMatch(/(marginLeft|marginRight|paddingLeft|paddingRight):/);
  });

  it('uses centred text, which is what makes it direction-neutral', () => {
    // Guards the assertion above from becoming vacuous: the styles really
    // do set an alignment, it is just the logical-neutral one.
    const { getByTestId } = render(<UpdateRequiredScreen updateUrl={STORE_URL} />);
    expect(flatten(getByTestId('update-required-title').props.style).textAlign).toBe('center');
    expect(flatten(getByTestId('update-required-body').props.style).textAlign).toBe('center');
  });
});

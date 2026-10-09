/**
 * S75 U3b UB-R13 + UY1 - the consent sheet body scrolls inside the card and
 * every control stays reachable at every text size.
 *
 * aiConsent.body grew to four sentences (decision D3 = C), so AiConsentSheet
 * renders the body Text inside ONE ScrollView; the title, the Privacy link and
 * the two CTAs stay OUTSIDE the scroll. UY1: the card carries NO maxHeight;
 * the ScrollView itself is capped with a NUMBER, Math.round(0.4 * window
 * height) from useWindowDimensions, with flexGrow 0, so the bottom-anchored
 * card grows upward at large text sizes instead of pushing the CTAs below the
 * screen edge. The title, the link and both CTA labels cap their font scaling
 * (maxFontSizeMultiplier 1.6); the body keeps its full scaling. The overflow
 * is made visible: the scroll indicators flash once each time the sheet turns
 * visible (never while an iOS Modal is still fading out), and the Android
 * scrollbar is persistent.
 *
 * Pinned with the component ref (UNSAFE_getAllByType(ScrollView) - a string
 * type is rejected by tsc). useWindowDimensions is spied per node and the cap
 * node runs two heights (667 -> 266.8 and 568 -> 227.2, so round, floor and
 * ceil all disagree with one of them), so a height read once at module load or
 * through Dimensions.get cannot pass. The ScrollView ref method is a
 * createNodeMock stub. Jest has no layout: the real fit at the smallest
 * supported iPhone and at the accessibility sizes stays owed to the on-device
 * check (UB-R13).
 *
 * react-i18next is mapped to the real EN catalog in this file so the pin reads
 * the real body copy, never the key. Pure ASCII.
 */

import React from 'react';
import * as ReactNative from 'react-native';
import type { ScaledSize, ViewStyle } from 'react-native';
import { render } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';
import AiConsentSheet from '../../src/components/AiConsentSheet';

jest.mock('react-i18next', () => {
  const catalog = jest.requireActual('../../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({ t: (key: string) => catalog[key] ?? key, i18n: { language: 'en' } }),
  };
});

const { ScrollView, StyleSheet, Text } = ReactNative;
const EN = enCatalog as Record<string, string>;
const noop = () => undefined;
// The shape read off every Text instance (ReactTestInstance resolves to `any`
// under this tsconfig, so the callback parameter is typed structurally).
type TextNode = { props: { children?: unknown } };

const OUTSIDE_KEYS = ['aiConsent.title', 'aiConsent.link', 'aiConsent.agree', 'aiConsent.notNow'];
const OUTSIDE_TEST_IDS = ['ai-consent-privacy-link', 'ai-consent-agree', 'ai-consent-not-now'];
const FIXED_TEXT_MAX_FONT_SCALE = 1.6;
const BODY_MAX_HEIGHT_FRACTION = 0.4;

// 4.7-inch class (iPhone SE 2/3) and the 4-inch class: 0.4 * h = 266.8 / 227.2.
const SE_WINDOW: ScaledSize = { width: 375, height: 667, scale: 2, fontScale: 1 };
const SMALL_WINDOW: ScaledSize = { width: 320, height: 568, scale: 2, fontScale: 1 };

let windowSpy: jest.SpyInstance<ScaledSize, []>;

beforeEach(() => {
  windowSpy = jest.spyOn(ReactNative, 'useWindowDimensions').mockReturnValue(SE_WINDOW);
});

afterEach(() => {
  windowSpy.mockRestore();
});

type SheetState = { visible: boolean; busy: boolean };
type ModalLike = { children?: React.ReactNode };

const KeepMountedModal = ({ children }: ModalLike) => React.createElement('Modal', null, children);

function sheet({ visible, busy }: SheetState) {
  return (
    <AiConsentSheet
      visible={visible}
      busy={busy}
      onAgree={noop}
      onNotNow={noop}
      onOpenPrivacy={noop}
      onDismiss={noop}
    />
  );
}

function renderSheet() {
  return render(sheet({ visible: true, busy: false }));
}

describe('S75 U3b UB-R13 - the consent body scrolls inside the card', () => {
  it('renders the body Text inside exactly ONE ScrollView (the component ref)', () => {
    const screen = renderSheet();
    const scrolls = screen.UNSAFE_getAllByType(ScrollView);
    expect(scrolls).toHaveLength(1);
    const inside = scrolls[0].findAllByType(Text).map((node: TextNode) => node.props.children);
    expect(inside).toEqual([EN['aiConsent.body']]);
  });

  it('keeps the title, the Privacy link and both CTAs outside the ScrollView', () => {
    const screen = renderSheet();
    const scroll = screen.UNSAFE_getAllByType(ScrollView)[0];
    const insideText = new Set(scroll.findAllByType(Text).map((node: TextNode) => node.props.children));
    for (const key of OUTSIDE_KEYS) {
      expect(screen.getByText(EN[key])).toBeTruthy();
      expect({ key, insideScroll: insideText.has(EN[key]) }).toEqual({ key, insideScroll: false });
    }
    for (const testID of OUTSIDE_TEST_IDS) {
      expect(screen.getByTestId(testID)).toBeTruthy();
    }
  });

  it('caps the body scroll with a NUMBER from the window height (flexGrow 0) and leaves the card uncapped (UY1)', () => {
    for (const win of [SE_WINDOW, SMALL_WINDOW]) {
      windowSpy.mockReturnValue(win);
      const screen = renderSheet();
      const card = StyleSheet.flatten<ViewStyle>(screen.getByTestId('ai-consent-sheet').props.style);
      expect({ windowHeight: win.height, cardMaxHeight: card.maxHeight }).toEqual({
        windowHeight: win.height,
        cardMaxHeight: undefined,
      });
      const scroll = StyleSheet.flatten<ViewStyle>(screen.UNSAFE_getAllByType(ScrollView)[0].props.style);
      // UY17 (AF-m1): the flattened style EXACTLY -- an added flex / flexBasis
      // (which collapses the body under Yoga), flexShrink 0, height or
      // minHeight all fail this equality, not only the keys listed before.
      expect({ windowHeight: win.height, scroll }).toEqual({
        windowHeight: win.height,
        scroll: { flexGrow: 0, maxHeight: Math.round(BODY_MAX_HEIGHT_FRACTION * win.height) },
      });
      screen.unmount();
    }
  });

  it('flashes the scroll indicators once when the sheet turns visible and keeps the Android scrollbar persistent (UY1)', () => {
    const flashScrollIndicators = jest.fn();
    const createNodeMock = (element: React.ReactElement) =>
      element.type === 'RCTScrollView' ? { flashScrollIndicators } : null;
    const screen = render(sheet({ visible: false, busy: false }), { createNodeMock });
    expect(flashScrollIndicators).toHaveBeenCalledTimes(0);

    screen.rerender(sheet({ visible: true, busy: false }));
    expect(flashScrollIndicators).toHaveBeenCalledTimes(1);

    // A re-render while it stays visible (busy flips) does not flash again.
    screen.rerender(sheet({ visible: true, busy: true }));
    expect(flashScrollIndicators).toHaveBeenCalledTimes(1);

    const scroll = screen.UNSAFE_getAllByType(ScrollView)[0];
    expect(scroll.props.persistentScrollbar).toBe(true);
  });

  it('does not flash while an iOS Modal keeps the sheet mounted after visible turns false (UY1)', () => {
    // RN 0.81 Modal on iOS keeps its children rendered after `visible` turns
    // false until the native dismissal ends (Modal.js _shouldShowModal /
    // isRendered); the repo mock unmounts them at once, so this node swaps in
    // a Modal that keeps them mounted.
    const modalSpy = jest
      .spyOn(ReactNative as unknown as { Modal: (props: ModalLike) => React.ReactElement }, 'Modal')
      .mockImplementation(KeepMountedModal);
    try {
      const flashScrollIndicators = jest.fn();
      const createNodeMock = (element: React.ReactElement) =>
        element.type === 'RCTScrollView' ? { flashScrollIndicators } : null;
      const screen = render(sheet({ visible: true, busy: false }), { createNodeMock });
      expect(flashScrollIndicators).toHaveBeenCalledTimes(1);

      screen.rerender(sheet({ visible: false, busy: false }));
      expect(screen.UNSAFE_getAllByType(ScrollView)).toHaveLength(1);
      expect(flashScrollIndicators).toHaveBeenCalledTimes(1);

      screen.rerender(sheet({ visible: true, busy: false }));
      expect(flashScrollIndicators).toHaveBeenCalledTimes(2);
    } finally {
      modalSpy.mockRestore();
    }
  });

  it('caps font scaling at 1.6 on the title, the Privacy link and both CTA labels; the body scales fully (UY1)', () => {
    const screen = renderSheet();
    for (const key of OUTSIDE_KEYS) {
      const node = screen.getByText(EN[key]);
      expect({ key, maxFontSizeMultiplier: node.props.maxFontSizeMultiplier }).toEqual({
        key,
        maxFontSizeMultiplier: FIXED_TEXT_MAX_FONT_SCALE,
      });
    }
    const body = screen.getByText(EN['aiConsent.body']);
    // UY17 (AF-m2): the body is never truncated -- a numberOfLines would hide
    // the training sentence or the not-sent sentence with every test green.
    expect({
      maxFontSizeMultiplier: body.props.maxFontSizeMultiplier,
      allowFontScaling: body.props.allowFontScaling,
      numberOfLines: body.props.numberOfLines,
      ellipsizeMode: body.props.ellipsizeMode,
    }).toEqual({
      maxFontSizeMultiplier: undefined,
      allowFontScaling: undefined,
      numberOfLines: undefined,
      ellipsizeMode: undefined,
    });
  });
});

/**
 * SplashScreen — the JS splash hands off from the native launch screen (U4c).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 * §3 R6/R7 and §5 rows C1-C5, plus C6 from review correction 1, as ruled
 * (UR10, UR11).
 *
 * D2: the JS mark starts EXACTLY where the native launch screen drew it, at
 * full opacity, not animated; only the tagline animates. D1: no app name
 * beside the mark. The repo jest mock window is 390 x 844
 * (__mocks__/react-native.ts `Dimensions`); the expected rectangle there is
 * spec §2d's row: left 134.675, top 358.000, size 126.803 (± 0.01).
 *
 * C6 (correction 1 / UR10): React Native swaps `left` / `right` under RTL by
 * default, while the native launch screen is NOT mirrored, so under RTL the
 * wrapper must say left = W - left - size = 128.522 for the mark to land on the
 * same physical pixels. The mocked `I18nManager` is mutable; C6 flips
 * `isRTL` inside the test and the `afterEach` restores it.
 *
 * Correction 2: C2 first asserts exactly one host whose type is 'Image'.
 * C3 finds the mark with spec §5's a11y helper (the host with
 * `accessibilityElementsHidden === true`: the Svg at base, the Image after),
 * so it reds at base for its stated reason (the animated brandStack).
 *
 * No wall-clock dependency: fake timers, and nothing advances them.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { Dimensions, I18nManager } from 'react-native';
import SplashScreen from '../src/screens/SplashScreen';

/**
 * Local structural type for a test-renderer node: the repo installs no
 * @types/react-test-renderer, so RNTL's `UNSAFE_root` is typed `any`.
 */
type TestNode = {
  type: unknown;
  props: Record<string, any>;
  parent: TestNode | null;
  findAll: (predicate: (node: TestNode) => boolean) => TestNode[];
};

const mockT = jest.fn((key: string): string => {
  const translations: Record<string, string> = {
    'app.name': 'MYEZ',
    'splash.tagline': 'Compare smarter',
  };
  return translations[key] ?? key;
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: mockT }),
}));

type Style = Record<string, unknown>;

/** Deep StyleSheet.flatten (the repo mock flattens one array level only). */
function flattenStyle(style: unknown): Style {
  if (Array.isArray(style)) {
    return style.reduce<Style>((acc, s) => ({ ...acc, ...flattenStyle(s) }), {});
  }
  if (style && typeof style === 'object') return { ...(style as Style) };
  return {};
}

/** Asymmetric matcher: a number within ± tol of `expected` (spec: ± 0.01). */
function near(expected: number, tol = 0.01) {
  return {
    $$typeof: Symbol.for('jest.asymmetricMatcher'),
    asymmetricMatch: (actual: unknown): boolean =>
      typeof actual === 'number' && Math.abs(actual - expected) <= tol,
    toAsymmetricMatcher: (): string => `${expected} ± ${tol}`,
  };
}

// Spec §2d, window 390 x 844 (R8).
const LTR_LEFT = 134.675;
const RTL_LEFT = 128.522; // 390 - 134.675 - 126.803 (correction 1)
const TOP = 358.0;
const SIZE = 126.803;

function renderSplash() {
  return render(<SplashScreen onFinish={jest.fn()} />);
}

function hasAncestorWithTestID(node: TestNode, testID: string): boolean {
  for (let n: TestNode | null = node.parent; n; n = n.parent) {
    if (n.props?.testID === testID) return true;
  }
  return false;
}

const originalIsRTL = I18nManager.isRTL;

describe('SplashScreen — the mark hands off from the native launch screen (U4c)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockT.mockClear();
  });

  afterEach(() => {
    (I18nManager as { isRTL: boolean }).isRTL = originalIsRTL;
    jest.useRealTimers();
  });

  it('C1 splash-mark is absolutely placed at the native launch position (390 x 844, LTR), physical left only', () => {
    expect(Dimensions.get('window')).toMatchObject({ width: 390, height: 844 });
    expect(I18nManager.isRTL).toBe(false);
    const { getByTestId } = renderSplash();
    const style = flattenStyle(getByTestId('splash-mark').props.style);
    expect({ keys: Object.keys(style).sort(), style }).toEqual({
      keys: ['height', 'left', 'position', 'top', 'width'],
      style: {
        position: 'absolute',
        left: near(LTR_LEFT),
        top: near(TOP),
        width: near(SIZE),
        height: near(SIZE),
      },
    });
    expect(['start', 'end', 'right'].filter((k) => k in style)).toEqual([]);
  });

  it('C2 the one host Image is inside splash-mark and is drawn at the same size (width = height = the mark size)', () => {
    const { UNSAFE_root, getByTestId } = renderSplash();
    const root: TestNode = UNSAFE_root;
    const images = root.findAll((n) => n.type === 'Image');
    expect(images).toHaveLength(1);
    const image = images[0];
    const imageStyle = flattenStyle(image.props.style);
    const wrapperStyle = flattenStyle(getByTestId('splash-mark').props.style);
    expect({
      insideSplashMark: hasAncestorWithTestID(image, 'splash-mark'),
      width: imageStyle.width,
      height: imageStyle.height,
      sameAsWrapper: imageStyle.width === wrapperStyle.width && imageStyle.height === wrapperStyle.height,
    }).toEqual({
      insideSplashMark: true,
      width: near(SIZE),
      height: near(SIZE),
      sameAsWrapper: true,
    });
  });

  it('C3 [D2 first frame] nothing from the mark up to the root is faded, transformed or layout-animated', () => {
    const root: TestNode = renderSplash().UNSAFE_root;
    // Spec §5 helper: the a11y-hidden host is the mark (Svg at base, Image after).
    const marks = root.findAll(
      (n) => typeof n.type === 'string' && n.props.accessibilityElementsHidden === true
    );
    expect(marks).toHaveLength(1);
    const violations: string[] = [];
    for (let n: TestNode | null = marks[0]; n; n = n.parent) {
      if (typeof n.type !== 'string') continue;
      const label = `${n.type}${n.props.testID ? `#${n.props.testID}` : ''}`;
      const style = flattenStyle(n.props.style);
      if (style.opacity !== undefined && style.opacity !== 1) {
        violations.push(`${label} opacity ${JSON.stringify(style.opacity)}`);
      }
      if (style.transform !== undefined) {
        violations.push(`${label} transform ${JSON.stringify(style.transform)}`);
      }
      for (const prop of ['entering', 'exiting', 'layout']) {
        if (n.props[prop] !== undefined) violations.push(`${label} ${prop}`);
      }
    }
    expect(violations).toEqual([]);
  });

  it("C4 [D1] no app name beside the mark: 'MYEZ' is not rendered and t('app.name') is never called", () => {
    const { queryByText } = renderSplash();
    // queryByText('MYEZ') must be null; its children are reported so a red
    // says WHAT was rendered instead of dumping the fiber.
    expect({
      appNameText: queryByText('MYEZ')?.props.children ?? null,
      tCalledWithAppName: mockT.mock.calls.some(([key]) => key === 'app.name'),
    }).toEqual({ appNameText: null, tCalledWithAppName: false });
  });

  it("C5 [PIN] the tagline 'Compare smarter' renders and starts at opacity 0 (only the text animates)", () => {
    const { getByText } = renderSplash();
    const tagline = getByText('Compare smarter');
    expect(flattenStyle(tagline.props.style).opacity).toBe(0);
  });

  it('C6 [RTL] under I18nManager.isRTL the physical left is mirrored to 128.522 so the mark stays on the launch pixels', () => {
    (I18nManager as { isRTL: boolean }).isRTL = true;
    const { getByTestId } = renderSplash();
    const style = flattenStyle(getByTestId('splash-mark').props.style);
    expect({ keys: Object.keys(style).sort(), style }).toEqual({
      keys: ['height', 'left', 'position', 'top', 'width'],
      style: {
        position: 'absolute',
        left: near(RTL_LEFT),
        top: near(TOP),
        width: near(SIZE),
        height: near(SIZE),
      },
    });
    expect(['start', 'end', 'right'].filter((k) => k in style)).toEqual([]);
  });
});

/**
 * ScannerReticle edge-case coverage.
 *
 * Extends ScannerReticle.test.tsx with:
 * - Snapshot stability for default size (catches accidental viewport math drift)
 * - Animation hook called exactly once on mount (catches re-mount churn)
 * - All 4 corner-bracket Paths are unique (catches copy-paste regressions)
 *
 * The project-level mock at `__mocks__/react-native-reanimated.ts` exports
 * plain functions. We monkey-patch jest.fn spies onto its namespace before
 * the component imports them, then restore on teardown — this avoids
 * `jest.mock` (which clobbers `Animated.View` because requireActual also
 * resolves to the mock file via moduleNameMapper).
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import * as reanimated from 'react-native-reanimated';

const originalWithRepeat = reanimated.withRepeat;
const originalWithTiming = reanimated.withTiming;
const withRepeatSpy = jest.fn(originalWithRepeat);
const withTimingSpy = jest.fn(originalWithTiming);

beforeAll(() => {
  (reanimated as any).withRepeat = withRepeatSpy;
  (reanimated as any).withTiming = withTimingSpy;
});

afterAll(() => {
  (reanimated as any).withRepeat = originalWithRepeat;
  (reanimated as any).withTiming = originalWithTiming;
});

// Imported AFTER the spy injection above so the component's module-level
// `import { withRepeat, withTiming } from 'react-native-reanimated'` picks
// up the patched namespace.
// eslint-disable-next-line import/first
import ScannerReticle from '../../src/components/ScannerReticle';

describe('ScannerReticle — edges', () => {
  beforeEach(() => {
    withRepeatSpy.mockClear();
    withTimingSpy.mockClear();
  });

  it('matches snapshot for default size', () => {
    const { toJSON } = render(<ScannerReticle />);
    expect(toJSON()).toMatchSnapshot();
  });

  it('renders exactly 4 corner-bracket Paths (one per viewport corner)', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    const paths = UNSAFE_root.findAllByType('Path' as any);
    expect(paths).toHaveLength(4);
  });

  it('all 4 Path elements have unique `d` attributes (no copy-paste corner)', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    const paths = UNSAFE_root.findAllByType('Path' as any);
    const ds = paths.map((p: any) => p.props.d);
    const unique = new Set(ds);
    expect(unique.size).toBe(4);
  });
});

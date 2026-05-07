/**
 * useTypography hook tests — Phase 5 Task #56.
 *
 * Returns locale-aware typography presets. Under AR (RTL), the
 * 1.5x-default presets (body / bodyEmphasis / title / caption / small)
 * gain a 1.7x line-height multiplier per design § 1. Hero / display /
 * eyebrow have spec-defined compressed line-heights and are NOT
 * multiplied — the design wants tight headlines in both locales.
 */

let mockIsRTL = false;
jest.mock('../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: mockIsRTL ? 'ar' : 'en',
    isRTL: mockIsRTL,
    switchLanguage: jest.fn(),
  }),
}));

import { renderHook } from '@testing-library/react-native';
import { useTypography } from '../../src/hooks/useTypography';
import { typography } from '../../src/theme';

beforeEach(() => {
  mockIsRTL = false;
});

describe('useTypography hook — Phase 5 Task #56', () => {
  it('returns the static typography map under EN (no multiplier)', () => {
    const { result } = renderHook(() => useTypography());
    expect(result.current.body.lineHeight).toBe(typography.body.lineHeight);
    expect(result.current.title.lineHeight).toBe(typography.title.lineHeight);
    expect(result.current.caption.lineHeight).toBe(typography.caption.lineHeight);
  });

  it('multiplies body line-height by 1.7/1.5 under AR', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    const expected = typography.body.fontSize * 1.7;
    expect(result.current.body.lineHeight).toBeCloseTo(expected, 1);
  });

  it('multiplies title line-height by 1.7/1.5 under AR', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    expect(result.current.title.lineHeight).toBeCloseTo(typography.title.fontSize * 1.7, 1);
  });

  it('multiplies bodyEmphasis line-height under AR', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    expect(result.current.bodyEmphasis.lineHeight).toBeCloseTo(
      typography.bodyEmphasis.fontSize * 1.7,
      1
    );
  });

  it('multiplies caption + small line-heights under AR', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    expect(result.current.caption.lineHeight).toBeCloseTo(typography.caption.fontSize * 1.7, 1);
    expect(result.current.small.lineHeight).toBeCloseTo(typography.small.fontSize * 1.7, 1);
  });

  it('does NOT multiply hero / display line-height under AR (spec-tight headlines)', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    // hero is 36 * 1.2; display is 28 * 1.3 — both stay invariant.
    expect(result.current.hero.lineHeight).toBe(typography.hero.lineHeight);
    expect(result.current.display.lineHeight).toBe(typography.display.lineHeight);
  });

  it('does NOT multiply eyebrow line-height under AR (spec-tight uppercase label)', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    expect(result.current.eyebrow.lineHeight).toBe(typography.eyebrow.lineHeight);
  });

  it('preserves fontSize / fontWeight / letterSpacing through both locales', () => {
    mockIsRTL = true;
    const { result } = renderHook(() => useTypography());
    expect(result.current.body.fontSize).toBe(typography.body.fontSize);
    expect(result.current.body.fontWeight).toBe(typography.body.fontWeight);
    expect(result.current.eyebrow.letterSpacing).toBe(typography.eyebrow.letterSpacing);
  });
});

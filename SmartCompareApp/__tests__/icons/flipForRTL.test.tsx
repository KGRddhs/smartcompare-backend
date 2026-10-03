/**
 * flipForRTL helper - the two cases moved from __tests__/icons/QaranIcon.test.tsx
 * (U4d, OQ4 / UR4). QaranIcon.test.tsx is deleted by GREEN together with
 * src/icons/QaranIcon.tsx; the helper keeps its two tests here.
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4D_REVEAL_GLYPH_SPEC.md
 * section 5 rows F1 and F2 (PIN). The case bodies and the describe name are
 * verbatim; each `it` name carries its id (F1 / F2), the only change. The
 * import is the barrel, as before; the barrel stays after U4d.
 */
import { flipForRTL } from '../../src/icons';

describe('flipForRTL helper', () => {
  it('F1 returns no transform when LTR', () => {
    expect(flipForRTL(false)).toEqual({ transform: [] });
  });

  it('F2 returns scaleX(-1) when RTL', () => {
    expect(flipForRTL(true)).toEqual({ transform: [{ scaleX: -1 }] });
  });
});

/**
 * Bundle E S3 hotfix L1 R2 — Gate B code-quality fixes (red-green TDD).
 *
 * Two [IMPORTANT] items from Gate B reviewer:
 *
 *   #1 — setTimeout handle in navigateToResultsWithFloor was discarded.
 *        If the user navigates away during the 0–1200ms wait, the timer
 *        still fires and calls navigation.navigate on a potentially
 *        unmounted screen. Fix: capture the handle in advanceTimerRef
 *        and clear it on unmount + on the onError abort path.
 *
 *   #2 — scanCtaEnabled used inside an already-conditional render block.
 *        disabled / style / accessibilityState branches that depend on
 *        !scanCtaEnabled are dead code because the parent JSX gate
 *        (`canCompare && inputMode === 'scan' &&`) ensures the CTA is
 *        either rendered enabled or not rendered at all. Either drop
 *        the dead defensive surface or replace it with literal `false`.
 *
 * Tests are source-grep contracts (HomeScreen has 25+ mock dependencies;
 * runtime renders can't reliably exercise the unmount-during-floor edge
 * case in Jest). The grep pattern catches future regressions when
 * someone re-introduces a bare setTimeout or revives the dead branches.
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_SRC = fs.readFileSync(
  path.resolve(__dirname, '../src/screens/HomeScreen.tsx'),
  'utf8',
);

describe('Gate B #1 — navigateToResultsWithFloor timer cleanup', () => {
  it('navigateToResultsWithFloor captures the setTimeout handle in a ref', () => {
    // Test fails until impl declares the ref AND assigns setTimeout return
    // value to it (vs the previous bare `setTimeout(advance, remaining)`).
    expect(HOME_SRC).toMatch(/advanceTimerRef\s*=\s*useRef/);
    // The setTimeout call inside the helper assigns its return to the ref.
    expect(HOME_SRC).toMatch(
      /advanceTimerRef\.current\s*=\s*setTimeout\(/,
    );
  });

  it('does NOT have a bare unhandled setTimeout(advance, remaining) call', () => {
    // The previous bare `setTimeout(advance, remaining)` (without ref
    // capture) is the regression Gate B flagged. Pin the absence.
    const stripped = HOME_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(
      /\/\/.*$/gm,
      '',
    );
    // Bare-setTimeout pattern: `setTimeout(advance, ...)` NOT prefixed by
    // an assignment to advanceTimerRef.current on the same line.
    expect(stripped).not.toMatch(/^[^=]*\bsetTimeout\(advance\b/m);
  });

  it('mounts a cleanup useEffect that clears the timer on unmount', () => {
    // Pattern: useEffect with empty deps that returns a cleanup fn
    // clearing the timer ref.
    expect(HOME_SRC).toMatch(/clearTimeout\(advanceTimerRef\.current\)/);
  });

  it('clears the timer on the onError abort path (SSE / URL failure)', () => {
    // When loading flips back to false because a compare failed, the
    // not-yet-fired floor timer must also be cancelled — otherwise it
    // would still fire and silently navigate to Results despite the
    // error UX.
    // Pin a reference to clearTimeout on advanceTimerRef inside the
    // helper or error path. The mount-cleanup effect alone is not
    // enough; the user is still on Home but loading just turned off.
    const clearCount = (
      HOME_SRC.match(/clearTimeout\(advanceTimerRef\.current\)/g) ?? []
    ).length;
    // Expect AT LEAST 2 clearTimeout calls: one in unmount cleanup,
    // one in the onError / loading=false path.
    expect(clearCount).toBeGreaterThanOrEqual(2);
  });

  it('sets advanceTimerRef.current to null after fire (no stale handle)', () => {
    // Inside the `advance` closure, after navigate fires, the ref must
    // be reset to null so subsequent navigateToResultsWithFloor calls
    // don't observe a stale handle.
    expect(HOME_SRC).toMatch(/advanceTimerRef\.current\s*=\s*null/);
  });
});

describe('Gate B #2 — drop dead defensive code around scanCtaEnabled', () => {
  it('does NOT compute scanCtaEnabled as a separate const', () => {
    // The conditional render gate `canCompare && inputMode === 'scan' &&`
    // already covers the only render path. A separate `scanCtaEnabled`
    // const is dead code. Either inline the predicate inside the gate
    // OR drop it entirely. After fix the symbol should not appear.
    const stripped = HOME_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(
      /\/\/.*$/gm,
      '',
    );
    expect(stripped).not.toMatch(/\bscanCtaEnabled\b/);
  });

  it('handleScanCtaPress no longer guards on a redundant flag', () => {
    // Without scanCtaEnabled, handleScanCtaPress simply navigates.
    // The CTA is only mounted when canCompare && inputMode === 'scan',
    // so the press-time guard would be unreachable anyway.
    expect(HOME_SRC).toMatch(
      /handleScanCtaPress\s*=\s*\(\)\s*=>\s*\{\s*navigation\.navigate\(['"]ScanCamera['"]\);?\s*\}/,
    );
  });

  it('compareCtaDisabled style is no longer applied (CTA never disabled in scan mode)', () => {
    const stripped = HOME_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(
      /\/\/.*$/gm,
      '',
    );
    expect(stripped).not.toMatch(/styles\.compareCtaDisabled/);
  });
});

/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R1-R3 (spec section 5, RULINGS_S81_G6
 * R-G6-4): the pure timing leaf src/utils/clientSpeed.ts.
 *
 * The module does not exist at base, so it is read through loadOptional and
 * asserted (an AssertionError at base, never a module-not-found error).
 */

function loadOptional(rel: string): any {
  try {
    return require(rel);
  } catch {
    return null;
  }
}

const MOD = '../../src/utils/clientSpeed';

describe('CL2 clientSpeed leaf', () => {
  it('R1 exports the three constants and the two functions', () => {
    const m = loadOptional(MOD);
    expect(m).not.toBeNull();
    expect(m.HOME_FLOOR_MS).toBe(400);
    expect(m.HOME_FLOOR_SKIP_BELOW_MS).toBe(300);
    expect(m.REVEAL_DELAY_MS).toBe(800);
    expect(typeof m.homeFloorDelayMs).toBe('function');
    expect(typeof m.revealDelayMs).toBe('function');
  });

  it('R2 homeFloorDelayMs follows the A17 300 / 400 rule', () => {
    const m = loadOptional(MOD);
    expect(m).not.toBeNull();
    const table: [number, number][] = [
      [-50, 0],
      [0, 0],
      [100, 0],
      [300, 0],
      [301, 99],
      [350, 50],
      [400, 0],
      [1500, 0],
      [NaN, 0],
    ];
    const got = table.map(([elapsed]) => [elapsed, m.homeFloorDelayMs(elapsed)]);
    expect(got).toEqual(table);
  });

  it('R3 revealDelayMs is 0 on a measured fast hit and 800 otherwise', () => {
    const m = loadOptional(MOD);
    expect(m).not.toBeNull();
    expect(m.revealDelayMs(true)).toBe(0);
    expect(m.revealDelayMs(false)).toBe(800);
  });
});

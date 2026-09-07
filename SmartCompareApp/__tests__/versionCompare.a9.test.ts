/**
 * A9 — exhaustive tests for the force-update comparator.
 *
 * WHY THIS SUITE IS OVERSIZED FOR 90 LINES OF CODE
 * `isBelowMinVersion` is the sole predicate that decides whether an
 * install is bounced behind an unskippable screen. A false positive here
 * bricks every device on the branch until an operator rolls back an env
 * var or ships another OTA. So the whole grammar is pinned: the ordering
 * trap that motivates a numeric comparator at all, the padding rule, and
 * every shape that must resolve to "cannot decide" (→ never block).
 */
import {
  compareVersions,
  isBelowMinVersion,
  parseVersion,
  MAX_VERSION_SEGMENTS,
} from '../src/utils/versionCompare';

describe('parseVersion', () => {
  it.each([
    ['1.2.3', [1, 2, 3]],
    ['1.2', [1, 2]],
    ['7', [7]],
    ['1.2.3.4', [1, 2, 3, 4]],
    ['v1.2.3', [1, 2, 3]],
    ['V1.2.3', [1, 2, 3]],
    ['  1.2.3  ', [1, 2, 3]],
    ['1.01.0', [1, 1, 0]],
    ['0.0.0', [0, 0, 0]],
    ['20260907', [20260907]],
  ])('parses %p', (input, expected) => {
    expect(parseVersion(input)).toEqual(expected);
  });

  it.each([
    ['empty string', ''],
    ['whitespace only', '   '],
    ['bare v', 'v'],
    ['non-numeric', 'abc'],
    ['pre-release suffix', '1.2.3-beta'],
    ['build metadata', '1.2.3+ci'],
    ['empty segment', '1..2'],
    ['trailing dot', '1.2.'],
    ['leading dot', '.1.2'],
    ['negative segment', '1.-2.0'],
    ['negative version', '-1.0.0'],
    ['five segments', '1.2.3.4.5'],
    ['exponent notation', '1e3'],
    ['inner whitespace', '1. 2.3'],
    ['unsafe integer segment', '99999999999999999999'],
  ])('refuses %s', (_label, input) => {
    expect(parseVersion(input)).toBeNull();
  });

  it.each([[null], [undefined], [123], [{ major: 1 }], [['1', '2']], [true]])(
    'refuses the non-string %p',
    (input) => {
      expect(parseVersion(input as unknown)).toBeNull();
    }
  );

  it(`refuses more than ${MAX_VERSION_SEGMENTS} segments`, () => {
    expect(parseVersion('1.2.3.4')).not.toBeNull();
    expect(parseVersion('1.2.3.4.5')).toBeNull();
  });
});

describe('compareVersions — numeric ordering', () => {
  it('orders 1.10.0 ABOVE 1.9.0 (the lexicographic trap)', () => {
    // A string compare reads '1' < '9' at the second segment and inverts
    // this. That single bug would block every user the moment a minor
    // version passed .9.
    expect(compareVersions('1.10.0', '1.9.0')).toBe(1);
    expect(compareVersions('1.9.0', '1.10.0')).toBe(-1);
  });

  it.each([
    ['2.0.0', '10.0.0', -1],
    ['10.0.0', '2.0.0', 1],
    ['1.2.3', '1.2.4', -1],
    ['1.3.0', '1.2.99', 1],
    ['0.9.9', '1.0.0', -1],
    ['1.0.0', '1.0.0', 0],
    ['1.2.10', '1.2.9', 1],
    ['1.0.0.1', '1.0.0.0', 1],
  ])('compare(%s, %s) === %i', (a, b, expected) => {
    expect(compareVersions(a, b)).toBe(expected);
  });

  it('pads missing trailing segments with zero', () => {
    expect(compareVersions('1.2', '1.2.0')).toBe(0);
    expect(compareVersions('1', '1.0.0.0')).toBe(0);
    expect(compareVersions('1.2', '1.2.1')).toBe(-1);
    expect(compareVersions('1.2.1', '1.2')).toBe(1);
  });

  it('ignores a leading v and surrounding whitespace on either side', () => {
    expect(compareVersions('v1.2.3', ' 1.2.3 ')).toBe(0);
    expect(compareVersions('V2.0', 'v1.9.9')).toBe(1);
  });

  it('treats leading zeros as the same number', () => {
    expect(compareVersions('1.01.0', '1.1.0')).toBe(0);
    expect(compareVersions('01.0.0', '1.0.0')).toBe(0);
  });

  it('returns null when EITHER side is unparseable', () => {
    expect(compareVersions('1.2.3', 'nope')).toBeNull();
    expect(compareVersions('nope', '1.2.3')).toBeNull();
    expect(compareVersions(null, '1.2.3')).toBeNull();
    expect(compareVersions('1.2.3', undefined)).toBeNull();
    expect(compareVersions('1.2.3-beta', '1.2.3')).toBeNull();
  });

  it('is antisymmetric across a spread of pairs', () => {
    const versions = ['0.0.1', '1.0.0', '1.0.1', '1.2.0', '1.10.0', '2.0.0', '10.1.1'];
    for (const a of versions) {
      for (const b of versions) {
        const forward = compareVersions(a, b) as number;
        const backward = compareVersions(b, a) as number;
        expect([-1, 0, 1]).toContain(forward);
        // Summing avoids Object.is's +0 / -0 distinction while still
        // pinning that the two directions are exact opposites.
        expect(forward + backward).toBe(0);
      }
    }
  });

  it('is transitive on an ascending chain', () => {
    const ascending = ['0.9.9', '1.0.0', '1.0.10', '1.2.0', '1.10.0', '2.0.0', '11.0.0'];
    for (let i = 0; i < ascending.length - 1; i += 1) {
      expect(compareVersions(ascending[i], ascending[i + 1])).toBe(-1);
      expect(compareVersions(ascending[ascending.length - 1], ascending[i])).toBe(1);
    }
  });
});

describe('isBelowMinVersion — the gate predicate', () => {
  it('is true only when strictly older', () => {
    expect(isBelowMinVersion('1.0.0', '1.0.1')).toBe(true);
    expect(isBelowMinVersion('1.9.0', '1.10.0')).toBe(true);
    expect(isBelowMinVersion('1.0.0', '1.0.0')).toBe(false);
    expect(isBelowMinVersion('1.10.0', '1.9.0')).toBe(false);
    expect(isBelowMinVersion('2.0.0', '1.0.0')).toBe(false);
  });

  it('is false — never true — for every undecidable input', () => {
    const undecidable: unknown[] = [
      null,
      undefined,
      '',
      '   ',
      'latest',
      '1.2.3-rc1',
      42,
      {},
      [],
      NaN,
    ];
    for (const value of undecidable) {
      // Unparseable CURRENT version must not block...
      expect(isBelowMinVersion(value, '99.0.0')).toBe(false);
      // ...and neither must an unparseable MINIMUM.
      expect(isBelowMinVersion('1.0.0', value)).toBe(false);
    }
  });

  it('does not block at the shipped defaults (app.json 1.0.0 vs env 1.0.0)', () => {
    // Backend defaults are min_version "1.0.0" and app.json version is
    // "1.0.0", so even an accidental APP_FORCE_UPDATE=true gates nobody
    // until someone also raises APP_MIN_VERSION.
    expect(isBelowMinVersion('1.0.0', '1.0.0')).toBe(false);
  });
});

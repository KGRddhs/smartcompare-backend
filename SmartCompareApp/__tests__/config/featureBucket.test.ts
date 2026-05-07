/**
 * Unit tests for featureBucket — Tasks 47-48 canary primitive.
 *
 * Asserts:
 * 1. djb2 is deterministic (same input → same output, every call).
 * 2. hashBucket boundary cases: percent <= 0 → false, percent >= 100 → true,
 *    empty/null id → false.
 * 3. hashBucket distribution: 1000 random ids at percent=50 yield ~500 trues
 *    (±5%). Catches a hash that clusters or is biased.
 * 4. hashBucket determinism: same (id, percent) returns same boolean across
 *    calls and monotonic ramps (in at 10% → in at 50% → in at 100%).
 * 5. setStableUserId overrides the cached device-id so an authed user
 *    crosses to user.id-based bucketing.
 */

import {
  djb2,
  hashBucket,
  getStableId,
  setStableUserId,
  _resetStableIdForTests,
} from '../../src/config/featureBucket';

// Mock SecureStore + Crypto — tests must not touch the real device keychain.
jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => {
      store[k] = v;
    }),
  };
});
jest.mock('expo-crypto', () => ({
  randomUUID: jest.fn(() => '00000000-0000-0000-0000-000000000abc'),
}));

describe('djb2', () => {
  it('is deterministic — same input yields same hash', () => {
    expect(djb2('user-abc')).toBe(djb2('user-abc'));
    expect(djb2('')).toBe(djb2(''));
  });

  it('different inputs yield different hashes (collision-rare for short strings)', () => {
    expect(djb2('user-abc')).not.toBe(djb2('user-abd'));
    expect(djb2('a')).not.toBe(djb2('b'));
  });

  it('returns non-negative integers', () => {
    for (const id of ['user-1', 'user-99', 'short', 'a-much-longer-id-string-with-uuid-shape-XXXX']) {
      const h = djb2(id);
      expect(h).toBeGreaterThanOrEqual(0);
      expect(Number.isInteger(h)).toBe(true);
    }
  });
});

describe('hashBucket boundary cases', () => {
  it('percent <= 0 returns false (canary off for everyone)', () => {
    expect(hashBucket('user-1', 0)).toBe(false);
    expect(hashBucket('user-1', -10)).toBe(false);
  });

  it('percent >= 100 returns true (everyone in)', () => {
    expect(hashBucket('user-1', 100)).toBe(true);
    expect(hashBucket('user-1', 150)).toBe(true);
  });

  it('empty/null/undefined id returns false', () => {
    expect(hashBucket('', 50)).toBe(false);
    expect(hashBucket(null, 50)).toBe(false);
    expect(hashBucket(undefined, 50)).toBe(false);
  });
});

describe('hashBucket determinism', () => {
  it('same (id, percent) returns same boolean across many calls', () => {
    const id = 'user-stable-1';
    const first = hashBucket(id, 50);
    for (let i = 0; i < 100; i++) {
      expect(hashBucket(id, 50)).toBe(first);
    }
  });

  it('users "in" at 10% are also in at 50% and 100% (monotonic ramp)', () => {
    let inAt10: string | null = null;
    for (let i = 0; i < 1000; i++) {
      const id = `seek-${i}`;
      if (hashBucket(id, 10)) {
        inAt10 = id;
        break;
      }
    }
    expect(inAt10).not.toBeNull();
    expect(hashBucket(inAt10!, 50)).toBe(true);
    expect(hashBucket(inAt10!, 100)).toBe(true);
  });

  it('users "out" at 90% are also out at 50% and 10% (monotonic ramp)', () => {
    let outAt90: string | null = null;
    for (let i = 0; i < 1000; i++) {
      const id = `seek-${i}`;
      if (!hashBucket(id, 90)) {
        outAt90 = id;
        break;
      }
    }
    expect(outAt90).not.toBeNull();
    expect(hashBucket(outAt90!, 50)).toBe(false);
    expect(hashBucket(outAt90!, 10)).toBe(false);
  });
});

describe('hashBucket distribution', () => {
  it('1000 random ids at percent=50 give ~500 trues (±5%)', () => {
    let trues = 0;
    for (let i = 0; i < 1000; i++) {
      const id = `rnd-${i}-${(i * 7919) % 1000}`;
      if (hashBucket(id, 50)) trues++;
    }
    expect(trues).toBeGreaterThanOrEqual(450);
    expect(trues).toBeLessThanOrEqual(550);
  });

  it('1000 random ids at percent=10 give ~100 trues (±5%)', () => {
    let trues = 0;
    for (let i = 0; i < 1000; i++) {
      const id = `rnd-${i}-${(i * 7919) % 1000}`;
      if (hashBucket(id, 10)) trues++;
    }
    expect(trues).toBeGreaterThanOrEqual(50);
    expect(trues).toBeLessThanOrEqual(150);
  });
});

describe('getStableId + setStableUserId', () => {
  beforeEach(() => {
    _resetStableIdForTests();
  });

  it('returns a stable device id from secure store', async () => {
    const id1 = await getStableId();
    const id2 = await getStableId();
    expect(id1).toBeTruthy();
    expect(id2).toBe(id1);
  });

  it('setStableUserId overrides the cached id with user.id', async () => {
    await getStableId(); // primes cache with device id
    setStableUserId('user-real-uuid');
    const after = await getStableId();
    expect(after).toBe('user-real-uuid');
  });

  it('setStableUserId with empty/null is a no-op', async () => {
    const deviceId = await getStableId();
    setStableUserId(null);
    setStableUserId('');
    setStableUserId(undefined);
    const after = await getStableId();
    expect(after).toBe(deviceId);
  });
});

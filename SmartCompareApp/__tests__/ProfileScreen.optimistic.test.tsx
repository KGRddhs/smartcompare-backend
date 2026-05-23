/**
 * Bundle D Task 2.F.1 — Profile 5-toggle optimistic wiring (R18).
 *
 * Contract:
 *   - 5 toggles: aiSharing + notificationsMaster + 3 sub-toggles
 *     (decision_insight, cohort_curiosity, decision_retrospective)
 *   - aiSharing + notificationsMaster → PUT /preferences (full body)
 *   - 3 sub-toggles → PUT /reengagement-subs (3-field body, plural keys
 *     per Backend 228ff63)
 *   - Optimistic update FIRST, rollback on failure with `Alert`
 *
 * This file pins:
 *   a. `putReengagementSubs(...)` exists in `src/services/api.ts` and
 *      hits the right endpoint with the plural-keyed body shape.
 *   b. `ProfileScreen.tsx` source references putReengagementSubs in its
 *      sub-toggle handler (NOT savePreferences for the 3 sub-toggles).
 *   c. The plural→singular mapping (FE plural keys ↔ DB singular keys)
 *      is honoured by the FE caller — backend translates server-side.
 *
 * Approach: mostly source-grep + a focused unit test on the api wrapper
 * (mocking axios). Rendering ProfileScreen end-to-end pulls in 20+
 * services per the bundleA test's note; the structural contract is
 * what matters here.
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');
const API_PATH = path.resolve(__dirname, '../src/services/api.ts');
const PROFILE_SRC = fs.readFileSync(PROFILE_PATH, 'utf8');
const API_SRC = fs.readFileSync(API_PATH, 'utf8');

describe('Bundle D 2.F.1 — Profile reengagement-subs wiring (R18)', () => {
  it('api.ts exports putReengagementSubs', () => {
    expect(API_SRC).toMatch(/export\s+async\s+function\s+putReengagementSubs/);
  });

  it('putReengagementSubs hits PUT /api/v1/auth/reengagement-subs', () => {
    expect(API_SRC).toMatch(
      /putReengagementSubs[\s\S]{0,400}api\.put\(\s*['"]\/api\/v1\/auth\/reengagement-subs['"]/
    );
  });

  it('ProfileScreen imports + calls putReengagementSubs', () => {
    expect(PROFILE_SRC).toMatch(/import[\s\S]{0,200}putReengagementSubs[\s\S]{0,200}from\s+['"]\.\.\/services\/api['"]/);
    expect(PROFILE_SRC).toMatch(/putReengagementSubs\s*\(/);
  });

  it('ProfileScreen uses plural keys (decision_insights / peer_decision_updates / decision_retrospectives)', () => {
    // The 3 plural keys per Backend 228ff63 endpoint body shape.
    expect(PROFILE_SRC).toMatch(/decision_insights\s*:/);
    expect(PROFILE_SRC).toMatch(/peer_decision_updates\s*:/);
    expect(PROFILE_SRC).toMatch(/decision_retrospectives\s*:/);
  });

  it('ProfileScreen sub-toggle handler still rollbacks state on failure', () => {
    // The existing optimistic-rollback pattern (setPreferences(previous) on
    // catch/!success) must be preserved for the new endpoint path.
    expect(PROFILE_SRC).toMatch(
      /putReengagementSubs[\s\S]{0,400}setPreferences\s*\(\s*previous/
    );
  });
});

describe('Bundle D 2.F.1 — putReengagementSubs runtime body shape', () => {
  let putReengagementSubs: any;
  let mockPut: jest.Mock;

  beforeEach(() => {
    jest.resetModules();
    jest.doMock('axios', () => {
      mockPut = jest.fn().mockResolvedValue({ data: { success: true } });
      const instance = {
        get: jest.fn(),
        put: mockPut,
        post: jest.fn(),
        delete: jest.fn(),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      };
      return { create: () => instance, __instance: instance };
    });
    jest.doMock('../src/services/certificatePinning', () => ({
      setupCertificatePinning: jest.fn(),
    }));
    jest.doMock('../src/services/authService', () => ({
      getToken: jest.fn().mockResolvedValue('fake'),
      refreshSession: jest.fn(),
      clearSession: jest.fn(),
    }));
    jest.doMock('expo-image-manipulator', () => ({
      manipulateAsync: jest.fn(),
      SaveFormat: { JPEG: 'jpeg' },
    }));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    putReengagementSubs = require('../src/services/api').putReengagementSubs;
  });

  it('sends exactly the 3 plural-keyed booleans to the endpoint', async () => {
    await putReengagementSubs({
      decision_insights: true,
      peer_decision_updates: false,
      decision_retrospectives: true,
    });
    expect(mockPut).toHaveBeenCalledTimes(1);
    const [url, body] = mockPut.mock.calls[0];
    expect(url).toBe('/api/v1/auth/reengagement-subs');
    expect(body).toEqual({
      decision_insights: true,
      peer_decision_updates: false,
      decision_retrospectives: true,
    });
  });
});

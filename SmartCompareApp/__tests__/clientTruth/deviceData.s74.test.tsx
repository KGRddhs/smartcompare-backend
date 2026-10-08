/**
 * S74 CLIENT-TRUTH - recent searches are removed with the account (#295,
 * DEVICE-PURGE).
 *
 * Spec CLIENT_TRUTH_SPEC.md section 5 + section 8 rows CT-D1/CT-D2. At main
 * dfbda511 the account-deletion flow (EditProfileScreen.tsx:125-156:
 * api.delete -> clearAiConsent -> clearSession -> onAccountDeleted) never
 * removes the AsyncStorage key `@qaren_recent_searches` that HomeScreen
 * writes (HomeScreen.tsx:94/:322), so the next account on the device sees
 * the deleted account's searches. The fix is a new module
 * src/services/recentSearches.ts (RECENT_SEARCHES_KEY + clearRecentSearches,
 * never throws) called on the success path only.
 *
 * Harness: the mocks of __tests__/EditProfileScreen.bundleE.s3.integration.test.tsx
 * (useFocusEffect as a pass-through effect, factory mocks of api and
 * authService); AsyncStorage is the repo's __mocks__/async-storage.ts.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
      }, []);
    },
  };
});

const mockUpdateProfile = jest.fn();
const mockApiDelete = jest.fn();
const mockGetSavedUser = jest.fn();
const mockClearSession = jest.fn();
const mockUpdateSavedUserDisplayName = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    delete: (...args: any[]) => mockApiDelete(...args),
  },
  parseApiError: (e: any) => ({ message: e?.message || 'error' }),
  updateProfile: (...args: any[]) => mockUpdateProfile(...args),
}));

jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  clearSession: (...args: any[]) => mockClearSession(...args),
  updateSavedUserDisplayName: (...args: any[]) => mockUpdateSavedUserDisplayName(...args),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

import EditProfileScreen from '../../src/screens/EditProfileScreen';

/** The literal HomeScreen.tsx:94 reads and writes. */
const HOME_KEY = '@qaren_recent_searches';
const SEEDED = JSON.stringify(['iphone 15 vs galaxy s24']);

function makeProps() {
  return {
    navigation: { goBack: jest.fn(), navigate: jest.fn() },
    route: { params: undefined, key: 'EditProfile', name: 'EditProfile' as const },
    onAccountDeleted: jest.fn(),
  } as any;
}

async function confirmDelete(rendered: any) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert');
  await waitFor(() => {
    expect(rendered.getByText('K')).toBeTruthy();
  });
  fireEvent.press(rendered.getByTestId('edit-delete-account-row'));
  const buttons = alertSpy.mock.calls[0][2] as any[];
  const destructive = buttons.find((b: any) => b.style === 'destructive');
  await destructive.onPress();
  alertSpy.mockRestore();
}

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
  mockGetSavedUser.mockResolvedValue({
    id: 'u1',
    display_name: 'Kareem',
    email: 'kareem@example.com',
  });
});

describe('S74 CLIENT-TRUTH account deletion clears device search history', () => {
  it('CT-D1: a successful deletion removes @qaren_recent_searches', async () => {
    await AsyncStorage.setItem(HOME_KEY, SEEDED);
    mockApiDelete.mockResolvedValueOnce({});
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await confirmDelete(rendered);
    expect(mockApiDelete).toHaveBeenCalledWith('/api/v1/auth/account');
    expect(props.onAccountDeleted).toHaveBeenCalled();
    expect(await AsyncStorage.getItem(HOME_KEY)).toBeNull();
  });

  it('CT-D1 GUARD: a failed deletion keeps @qaren_recent_searches (success path only)', async () => {
    await AsyncStorage.setItem(HOME_KEY, SEEDED);
    mockApiDelete.mockRejectedValueOnce(new Error('500 boom'));
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await confirmDelete(rendered);
    expect(props.onAccountDeleted).not.toHaveBeenCalled();
    expect(await AsyncStorage.getItem(HOME_KEY)).toBe(SEEDED);
  });

  it('Y9: a rejecting removeItem for the recent-searches key never blocks the deletion (clearSession runs, onAccountDeleted fires)', async () => {
    await AsyncStorage.setItem(HOME_KEY, SEEDED);
    mockApiDelete.mockResolvedValueOnce({});
    const removeItem = AsyncStorage.removeItem as jest.Mock;
    const realImpl = removeItem.getMockImplementation();
    expect(typeof realImpl).toBe('function');
    let rejected = 0;
    removeItem.mockImplementation(async (key: string) => {
      if (key === HOME_KEY && rejected === 0) {
        rejected += 1;
        throw new Error('storage ' + 'unavailable');
      }
      return (realImpl as (k: string) => Promise<void>)(key);
    });
    try {
      const props = makeProps();
      const rendered = render(<EditProfileScreen {...props} />);
      await confirmDelete(rendered);
      expect({
        removeRejected: rejected,
        clearSessionCalls: mockClearSession.mock.calls.length,
        onAccountDeletedCalls: props.onAccountDeleted.mock.calls.length,
      }).toEqual({ removeRejected: 1, clearSessionCalls: 1, onAccountDeletedCalls: 1 });
    } finally {
      removeItem.mockImplementation(realImpl as (k: string) => Promise<void>);
    }
  });

  it('CT-D2: src/services/recentSearches.ts exports RECENT_SEARCHES_KEY equal to the HomeScreen.tsx literal', () => {
    const home = fs.readFileSync(
      path.resolve(__dirname, '../../src/screens/HomeScreen.tsx'),
      'utf8',
    );
    const m = home.match(/const RECENT_SEARCHES_KEY = '([^']+)'/);
    expect(m && m[1]).toBe(HOME_KEY);
    const modulePath = path.resolve(__dirname, '../../src/services/recentSearches.ts');
    expect(fs.existsSync(modulePath)).toBe(true);
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('../../src/services/recentSearches');
    expect(mod.RECENT_SEARCHES_KEY).toBe(HOME_KEY);
    expect(typeof mod.clearRecentSearches).toBe('function');
  });
});

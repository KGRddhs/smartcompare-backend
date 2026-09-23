/**
 * W3-14 R6 — the delete-account failure Alert renders catalog copy, never a raw string.
 *
 * `DELETE /api/v1/auth/account` is `1/minute`: a second confirm inside a
 * minute is a GUARANTEED 429, and at b63a8368 EditProfileScreen.tsx:140 was
 * `Alert.alert(t('editProfile.error.deleteTitle'), parseApiError(err).message)`
 * — i.e. "Rate limit exceeded. Please try again later." (scary "try again"),
 * or the axios fall-through "Request failed with status code 502".
 *
 * Fix contract (spec §4): the body is
 * `t(settingsErrorKey(parseApiError(err).code, 'common.error'))`.
 *
 * Harness = EditProfileScreen.bundleE.s3.integration.test.tsx (`mockApiDelete`
 * declared :31, mapped onto `default.delete` :39; delete drive :253-266) with
 * two deliberate differences: `parseApiError` is the REAL function, and `t`
 * resolves through the REAL en.json — so the asserted string is what a phone
 * renders.
 */
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';

const EN = enCatalog as Record<string, string>;

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

jest.mock('../src/services/api', () => {
  const real = jest.requireActual('../src/services/api');
  return {
    __esModule: true,
    default: {
      delete: (...args: any[]) => mockApiDelete(...args),
    },
    parseApiError: real.parseApiError,
    updateProfile: (...args: any[]) => mockUpdateProfile(...args),
  };
});

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  clearSession: (...args: any[]) => mockClearSession(...args),
  updateSavedUserDisplayName: (...args: any[]) => mockUpdateSavedUserDisplayName(...args),
  // api.ts (required for real parseApiError) imports these at module scope.
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
}));

jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        if (catalog[key] !== undefined) return catalog[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
    }),
  };
});

import EditProfileScreen from '../src/screens/EditProfileScreen';

function makeProps(): any {
  return {
    navigation: { goBack: jest.fn(), navigate: jest.fn() },
    route: { params: undefined, key: 'EditProfile', name: 'EditProfile' as const },
    onAccountDeleted: jest.fn(),
  };
}

function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

const RATE_LIMITED_429 = () =>
  axiosError(429, {
    success: false,
    error: 'Rate limit exceeded. Please try again later.',
    code: 'RATE_LIMITED',
    request_id: 'r1',
    retry_after_seconds: 61,
  });

beforeEach(() => {
  jest.clearAllMocks();
  mockGetSavedUser.mockResolvedValue({ id: 'u1', display_name: 'K', email: 'k@example.com' });
});

/** Tap the delete row, confirm the destructive button, return the failure Alert's body. */
async function confirmDeleteAndGetFailureBody(): Promise<{ body: any; props: any }> {
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
  const props = makeProps();
  const rendered = render(<EditProfileScreen {...props} />);
  fireEvent.press(rendered.getByTestId('edit-delete-account-row'));
  expect(alertSpy).toHaveBeenCalledTimes(1);
  const buttons = alertSpy.mock.calls[0][2] as any[];
  const destructive = buttons.find((b: any) => b.style === 'destructive');
  await destructive.onPress();
  await waitFor(() => expect(alertSpy).toHaveBeenCalledTimes(2));
  const call = alertSpy.mock.calls[1];
  expect(call[0]).toBe(EN['editProfile.error.deleteTitle']);
  alertSpy.mockRestore();
  return { body: call[1], props };
}

describe('W3-14 R6 — EditProfile delete failure copy', () => {
  it('a RATE_LIMITED 429 (1/minute limiter) renders common.errors.rateLimited', async () => {
    mockApiDelete.mockRejectedValueOnce(RATE_LIMITED_429());
    const { body, props } = await confirmDeleteAndGetFailureBody();
    expect(body).not.toMatch(/Rate limit|try again/i);
    expect(body).toBe(EN['common.errors.rateLimited']);
    expect(typeof body).toBe('string');
    expect(props.onAccountDeleted).not.toHaveBeenCalled();
  });

  it('a codeless transport 502 renders common.error, never "failed"', async () => {
    mockApiDelete.mockRejectedValueOnce(new Error('Request failed with status code 502'));
    const { body } = await confirmDeleteAndGetFailureBody();
    expect(body).not.toMatch(/failed/i);
    expect(body).toBe(EN['common.error']);
  });
});

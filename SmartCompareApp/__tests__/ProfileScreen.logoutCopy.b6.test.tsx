/**
 * B6 — the Arabic logout confirmation must NOT carry account-deletion copy.
 *
 * The defect: `handleLogout` borrowed the shared irreversibility string
 * `profile.deleteConfirm` ("Are you sure? This cannot be undone.") and stripped
 * the second sentence with an ENGLISH literal `.replace('This cannot be
 * undone.', '')`. The Arabic catalog string contains no English substring, so
 * the replace never matched and every Arabic user was told that signing out
 * could not be undone — a false irreversibility warning on a reversible action.
 * `fallbackLng: 'en'` cannot rescue it: the key EXISTS in ar.json, so Arabic
 * resolves to the Arabic string and the fallback never fires.
 *
 * The fix is a dedicated `profile.logoutConfirm` key in BOTH catalogs, which
 * removes the locale-dependent string surgery instead of patching it per
 * language. `profile.deleteConfirm` is deliberately left alone — its two other
 * consumers (EditProfileScreen account deletion, HistoryScreen row delete) are
 * genuinely irreversible and the clause is accurate there.
 *
 * Render pattern: the sync-render recipe from
 * ProfileScreen.bundleE.s3.integration.test.tsx (useFocusEffect mocked as a
 * pass-through useEffect, plain render(), no act()).
 *
 * This file drives a CATALOG-BACKED `t` (the repo-wide react-i18next mock
 * returns the key itself), so the Arabic branch is exercised against the real
 * ar.json strings rather than against the mock.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent } from '@testing-library/react-native';

import enCatalog from '../src/i18n/en.json';
import arCatalog from '../src/i18n/ar.json';

const en = enCatalog as Record<string, string>;
const ar = arCatalog as Record<string, string>;

// Arabic question mark (U+061F) — the sentence separator inside ar.json's
// shared delete string. Only the separator is hardcoded here; both the logout
// copy and the deletion clause are read out of the catalogs.
const ARABIC_QUESTION_MARK = '؟';

/** The irreversibility sentence of the shared delete string, per language. */
function irreversibilityClause(catalog: Record<string, string>, sep: string): string {
  const parts = catalog['profile.deleteConfirm'].split(sep);
  return parts.slice(1).join(sep).trim();
}

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

const mockGetSavedUser = jest.fn();
const mockLogout = jest.fn();
const mockGetCohortProfile = jest.fn();
const mockGetPreferences = jest.fn();
const mockSavePreferences = jest.fn();
const mockPutReengagementSubs = jest.fn();
const mockChangePassword = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  changePassword: (...args: any[]) => mockChangePassword(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error' }),
  getCohortProfile: (...args: any[]) => mockGetCohortProfile(...args),
  getPreferences: (...args: any[]) => mockGetPreferences(...args),
  savePreferences: (...args: any[]) => mockSavePreferences(...args),
  putReengagementSubs: (...args: any[]) => mockPutReengagementSubs(...args),
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  logout: (...args: any[]) => mockLogout(...args),
}));

jest.mock('../src/components/ProfileEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    RecentDecisionsRow: () =>
      ReactRequired.createElement('View', { testID: 'mock-recent-decisions-row' }),
    PrioritiesInline: () =>
      ReactRequired.createElement('View', { testID: 'mock-priorities-inline' }),
    MonthStrip: () => ReactRequired.createElement('View', { testID: 'mock-month-strip' }),
  };
});

// The active language for BOTH the language hook and the catalog-backed `t`.
let mockLang: 'en' | 'ar' = 'en';

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: mockLang,
    isRTL: mockLang === 'ar',
    switchLanguage: jest.fn(),
  }),
}));

jest.mock('react-i18next', () => {
  const enJson = require('../src/i18n/en.json') as Record<string, string>;
  const arJson = require('../src/i18n/ar.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        const catalog = mockLang === 'ar' ? arJson : enJson;
        // Real i18next resolves ar -> (fallbackLng) en -> defaultValue -> key.
        if (Object.prototype.hasOwnProperty.call(catalog, key)) return catalog[key];
        if (Object.prototype.hasOwnProperty.call(enJson, key)) return enJson[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
      i18n: { language: mockLang, changeLanguage: jest.fn() },
    }),
  };
});

import ProfileScreen from '../src/screens/ProfileScreen';

function makeProps(overrides: any = {}) {
  return {
    navigation: { goBack: jest.fn(), navigate: jest.fn() },
    onLogout: jest.fn(),
    ...overrides,
  };
}

/** Presses the logout row and returns the Alert.alert call arguments. */
function pressLogout() {
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert');
  const props = makeProps();
  const rendered = render(<ProfileScreen {...props} />);
  fireEvent.press(rendered.getByTestId('profile-row-logout'));
  expect(alertSpy).toHaveBeenCalled();
  const [title, body, buttons] = alertSpy.mock.calls[0] as any[];
  alertSpy.mockRestore();
  return { title, body, buttons, props };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockLang = 'en';
  mockGetSavedUser.mockResolvedValue({
    id: 'u1',
    display_name: 'Kareem',
    email: 'kareem@example.com',
  });
  mockGetCohortProfile.mockResolvedValue({ display: { governorate: 'Capital' } });
  mockGetPreferences.mockResolvedValue({
    priorities: ['quality'],
    budget: 'mid',
    lifestyle: [],
    brand_attitude: 'best_of_both',
    ai_sharing_enabled: true,
    notifications_enabled: true,
    notification_types: {
      decision_insight: true,
      cohort_curiosity: true,
      decision_retrospective: true,
    },
  });
});

describe('B6 — catalog shape', () => {
  it('profile.logoutConfirm exists in BOTH catalogs', () => {
    expect(typeof en['profile.logoutConfirm']).toBe('string');
    expect(typeof ar['profile.logoutConfirm']).toBe('string');
    expect(en['profile.logoutConfirm'].length).toBeGreaterThan(0);
    expect(ar['profile.logoutConfirm'].length).toBeGreaterThan(0);
  });

  it('neither logout string carries the irreversibility clause', () => {
    const enClause = irreversibilityClause(en, '?');
    const arClause = irreversibilityClause(ar, ARABIC_QUESTION_MARK);
    // Sanity: the delete string really does still carry a second sentence, so
    // the two assertions below are not vacuously true.
    expect(enClause.length).toBeGreaterThan(0);
    expect(arClause.length).toBeGreaterThan(0);
    expect(en['profile.logoutConfirm']).not.toContain(enClause);
    expect(ar['profile.logoutConfirm']).not.toContain(arClause);
  });

  it('profile.deleteConfirm keeps its clause for the real deletion call sites', () => {
    // EditProfileScreen (account deletion) + HistoryScreen (row delete) are
    // genuinely irreversible — B6 must not have weakened their warning.
    expect(en['profile.deleteConfirm']).toContain('cannot be undone');
    expect(ar['profile.deleteConfirm']).toContain(irreversibilityClause(ar, ARABIC_QUESTION_MARK));
  });
});

describe('B6 — Arabic logout confirmation', () => {
  it('renders the logout copy, never the deletion copy', () => {
    mockLang = 'ar';
    const { title, body } = pressLogout();

    expect(body).toBe(ar['profile.logoutConfirm']);
    expect(title).toBe(ar['profile.logout']);
    // The actual regression: the AR string arrived intact, irreversibility and
    // all, because the English literal never matched.
    expect(body).not.toBe(ar['profile.deleteConfirm']);
    expect(body).not.toContain(irreversibilityClause(ar, ARABIC_QUESTION_MARK));
  });

  it('still logs the user out from the destructive button', async () => {
    mockLang = 'ar';
    mockLogout.mockResolvedValueOnce(undefined);
    const { buttons, props } = pressLogout();
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    expect(destructive.text).toBe(ar['profile.logout']);
    await destructive.onPress();
    expect(mockLogout).toHaveBeenCalled();
    expect(props.onLogout).toHaveBeenCalled();
  });
});

describe('B6 — English logout confirmation', () => {
  it('renders the logout copy with no leftover English surgery', () => {
    mockLang = 'en';
    const { title, body } = pressLogout();

    expect(body).toBe(en['profile.logoutConfirm']);
    expect(title).toBe(en['profile.logout']);
    expect(body).not.toContain('cannot be undone');
    // The old `.replace()` left a trailing space behind; the dedicated key
    // does not.
    expect(body).toBe(body.trim());
  });
});

describe('B6 — no string surgery on translated output', () => {
  it('no src/ file .replace()s an English literal over a t() result', () => {
    const SRC_DIR = path.resolve(__dirname, '../src');
    const walk = (dir: string): string[] => {
      const out: string[] = [];
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) out.push(...walk(full));
        else if (/\.(ts|tsx)$/.test(entry.name)) out.push(full);
      }
      return out;
    };

    // `t(...).replace('literal'` — string surgery whose match depends on which
    // language resolved, i.e. exactly the B6 defect class. A regex-argument
    // replace (interpolation cleanup) is deliberately NOT matched.
    const re = /\bt\([^)]*\)\s*\.replace\(\s*['"]/;
    const offenders: string[] = [];
    for (const file of walk(SRC_DIR)) {
      const src = fs.readFileSync(file, 'utf8');
      for (const [i, line] of src.split('\n').entries()) {
        if (re.test(line)) {
          offenders.push(`${path.relative(SRC_DIR, file).replace(/\\/g, '/')}:${i + 1}`);
        }
      }
    }
    // A hit means some screen strips a hardcoded English phrase out of
    // translated copy — which silently no-ops in every other language. Add a
    // dedicated key to en.json AND ar.json instead.
    expect(offenders).toEqual([]);
  });
});

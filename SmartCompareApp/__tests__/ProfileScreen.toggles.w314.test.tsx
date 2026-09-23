/**
 * W3-14 R5 — Profile's privacy + notification toggles are usable WITHOUT
 * priorities, go to the new single-purpose route, and never render a raw
 * backend / axios string.
 *
 * The defect (measured at b63a8368, probes b1-b5):
 *  - `PUT /api/v1/auth/preferences` requires `priorities` (min_length=1), so
 *    `dbf152d9` (F-S1.5i, surface C) GATED all five toggles when the user had
 *    no priorities or `getPreferences()` returned null (which it does on ANY
 *    thrown error). Result: the AI-sharing opt-out — a privacy control — was
 *    unreachable (AI row `disabled:true`, 0 PUTs, caption "Pick your
 *    priorities first" x1).
 *  - When the switch WAS live, a failure rendered the raw string:
 *    "Validation error: body → lifestyle → 0: ...", "Failed to save
 *    preferences" (scary_vocab_en), "Request failed with status code 502".
 *
 * Fix contract (spec §4, rulings R-9 / R-14 / R-17): the two masters call
 * `putPreferenceToggles({ ai_sharing_enabled })` / `({ notifications_enabled })`
 * (new additive backend route, no priorities requirement); the F-S1.5i gate
 * (surface C only) is removed; every error render is
 * `t(settingsErrorKey(code, fallback))` — including the `result.error ||`
 * arms and the sub-toggle Alert.
 *
 * Harness = .qa-w3b/probes/w314_profile.test.tsx (= the bundleE.s3 harness
 * with the REAL `parseApiError` and the REAL en.json through `t`).
 * ToggleRow exposes accessibilityRole="switch", accessibilityState
 * {checked, disabled}, accessibilityLabel = label (ToggleRow.tsx:44-46).
 */
import React from 'react';
import { Switch } from 'react-native';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
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

const mockGetSavedUser = jest.fn();
const mockLogout = jest.fn();
const mockGetCohortProfile = jest.fn();
const mockGetPreferences = jest.fn();
const mockSavePreferences = jest.fn();
const mockPutPreferenceToggles = jest.fn();
const mockPutReengagementSubs = jest.fn();
const mockChangePassword = jest.fn();

jest.mock('../src/services/api', () => {
  const real = jest.requireActual('../src/services/api');
  return {
    __esModule: true,
    changePassword: (...args: any[]) => mockChangePassword(...args),
    parseApiError: real.parseApiError,
    getCohortProfile: (...args: any[]) => mockGetCohortProfile(...args),
    getPreferences: (...args: any[]) => mockGetPreferences(...args),
    savePreferences: (...args: any[]) => mockSavePreferences(...args),
    putPreferenceToggles: (...args: any[]) => mockPutPreferenceToggles(...args),
    putReengagementSubs: (...args: any[]) => mockPutReengagementSubs(...args),
  };
});

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  logout: (...args: any[]) => mockLogout(...args),
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
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

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'en', switchLanguage: jest.fn() }),
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

import ProfileScreen from '../src/screens/ProfileScreen';

function makeProps() {
  return { navigation: { goBack: jest.fn(), navigate: jest.fn() }, onLogout: jest.fn() };
}

const AI_LABEL = EN['profile.aiSharing.title']; // "Help improve AI quality"
const SUB_LABELS = [
  EN['profile.notifs.insight'],
  EN['profile.notifs.cohort'],
  EN['profile.notifs.retrospective'],
];
const GATE_CAPTION = 'Pick your priorities first';

// A user WITH priorities: the F-S1.5i gate is open today, so the error rows
// below redden on the RAW STRING, not on the gate.
const FULL_PREFS = {
  priorities: ['quality'],
  budget: 'mid',
  lifestyle: [],
  brand_attitude: 'best_of_both',
  ai_sharing_enabled: false,
  notifications_enabled: true,
  notification_types: {},
};

function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data, headers: {} };
  return err;
}

const VALIDATION_422 = () =>
  axiosError(422, {
    success: false,
    error: 'Validation error: body → lifestyle → 0: Input should be ...',
    code: 'VALIDATION_ERROR',
    request_id: 'r3',
  });
const SAVE_400 = () =>
  axiosError(400, {
    success: false,
    error: 'Failed to save preferences',
    code: 'BAD_REQUEST',
    request_id: 'r4',
  });
const TRANSPORT_502 = () => new Error('Request failed with status code 502');
// OTA'd client vs a backend WITHOUT the new route: Starlette's bare 404.
const STARLETTE_404 = () => ({ response: { status: 404, data: { detail: 'Not Found' } } });
const RATE_LIMITED_429 = () =>
  axiosError(429, {
    success: false,
    error: 'Rate limit exceeded. Please try again later.',
    code: 'RATE_LIMITED',
    request_id: 'r5',
    retry_after_seconds: 61,
  });

const RAW = /Validation error|Failed to|Request failed|Not Found|Rate limit|try again|oops/i;

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Every Text node that is an error line (a raw leak OR one of the catalog error sentences). */
function errorLines(rendered: any): string[] {
  const catalogErrors = [
    EN['profile.aiSharing.errorSave'],
    EN['profile.notifs.errorSave'],
    EN['common.errors.rateLimited'],
    EN['common.errors.locked'],
  ].filter((v): v is string => typeof v === 'string' && v.length > 0);
  const re = new RegExp([RAW.source, ...catalogErrors.map(escapeRe)].join('|'), 'i');
  return rendered.queryAllByText(re).map((n: any) =>
    Array.isArray(n.props.children) ? n.props.children.join('') : String(n.props.children),
  );
}

async function mount(prefs: any) {
  mockGetPreferences.mockResolvedValue(prefs);
  const rendered = render(<ProfileScreen {...makeProps()} />);
  await waitFor(() => expect(mockGetPreferences).toHaveBeenCalled());
  await waitFor(() => expect(rendered.getByLabelText(AI_LABEL)).toBeTruthy());
  return rendered;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetSavedUser.mockResolvedValue({ id: 'u1', display_name: 'K', email: 'k@example.com' });
  mockGetCohortProfile.mockResolvedValue({ display: { governorate: 'Capital' } });
  mockPutPreferenceToggles.mockResolvedValue({
    success: true,
    ai_sharing_enabled: true,
    notifications_enabled: null,
  });
  mockSavePreferences.mockResolvedValue({ success: true });
  mockPutReengagementSubs.mockResolvedValue({ success: true, notification_types: {} });
});

describe('W3-14 R5 (i)/(ii) — the AI-sharing opt-out works with NO priorities', () => {
  it.each([
    ['(i) getPreferences -> null', null],
    ['(ii) toggle-only row, no priorities', { ai_sharing_enabled: false, notification_types: {} }],
  ])('%s: switch enabled, one PUT to /preference-toggles with exactly {ai_sharing_enabled:true}', async (_l, prefs) => {
    const rendered = await mount(prefs);
    expect(rendered.getByLabelText(AI_LABEL).props.accessibilityState.disabled).toBe(false);

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1));
    expect(mockPutPreferenceToggles.mock.calls[0][0]).toStrictEqual({ ai_sharing_enabled: true });
    expect(mockSavePreferences).not.toHaveBeenCalled();
    expect(rendered.queryAllByText(GATE_CAPTION).length).toBe(0);
  });
});

describe('W3-14 R5 (iii) — notifications master + sub-toggles with NO priorities (ruling R-9 order)', () => {
  it('(iii-a) 5 switches, subs enabled; THEN (iii-b) master off -> exactly {notifications_enabled:false}, subs unmount', async () => {
    mockPutPreferenceToggles.mockResolvedValue({
      success: true,
      ai_sharing_enabled: null,
      notifications_enabled: false,
    });
    // A server row WITHOUT priorities (the fixture R-9 names: "no
    // priorities"). NOT `null`: a null read is either a failed/pending GET or
    // a `{}` row, so the stored notification_types are unknown and the subs
    // stay hidden (see the fixer rows below).
    const rendered = await mount({ ai_sharing_enabled: false, notification_types: {} });

    // (iii-a) — the master starts ON (`notifications_enabled !== false`, :233).
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(5);
    for (const label of SUB_LABELS) {
      expect(rendered.getByLabelText(label).props.accessibilityState.disabled).toBe(false);
    }

    // (iii-b)
    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1));
    expect(mockPutPreferenceToggles.mock.calls[0][0]).toStrictEqual({ notifications_enabled: false });
    expect(mockSavePreferences).not.toHaveBeenCalled();
    await waitFor(() => expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(2));
  });
});

// Fixer (adversary major #1): PUT /reengagement-subs OVERWRITES
// preferences.notification_types with all three keys (auth_routes.py
// update_reengagement_subs). When the preferences read did not return a row
// (getPreferences -> null on ANY thrown error, on a `{}` row, and before the
// first GET resolves) the client does not know the stored sub values, so a sub
// flip would write the two it did not touch from default-ON values and
// silently re-enable categories the user opted out of. The subs therefore
// render ONLY after a GET that returned a row; the two masters stay usable
// (single-key RMW writes on /preference-toggles, R5 (i)).
describe('W3-14 fixer — sub-toggles never write from unknown stored values', () => {
  it('getPreferences -> null: masters live, subs NOT rendered (2 switches), no /reengagement-subs write', async () => {
    const rendered = await mount(null);
    expect(rendered.getByLabelText(AI_LABEL).props.accessibilityState.disabled).toBe(false);
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(2);
    for (const label of SUB_LABELS) {
      expect(rendered.queryAllByLabelText(label).length).toBe(0);
    }
    expect(mockPutReengagementSubs).not.toHaveBeenCalled();
  });

  it('getPreferences -> null, THEN a successful master save: subs stay hidden (their stored values are still unknown)', async () => {
    const rendered = await mount(null);
    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(rendered.UNSAFE_getAllByType(Switch)[0].props.value).toBe(true));
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(2);
    expect(mockPutReengagementSubs).not.toHaveBeenCalled();
  });

  // Successor of the deleted togglesGated case (4) ("master ToggleRow disabled
  // includes togglesGated"): a null read must NOT re-gate the notifications
  // master — only notifsSaving disables it, and a flip issues the PUT.
  it('getPreferences -> null: the notifications master is ENABLED and a flip PUTs exactly {notifications_enabled:false}', async () => {
    mockPutPreferenceToggles.mockResolvedValue({
      success: true,
      ai_sharing_enabled: null,
      notifications_enabled: false,
    });
    const rendered = await mount(null);
    const master = rendered.getByLabelText(EN['profile.notifs.master.title']);
    expect(master.props.accessibilityState.disabled).toBe(false);

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1));
    expect(mockPutPreferenceToggles.mock.calls[0][0]).toStrictEqual({ notifications_enabled: false });
    expect(mockSavePreferences).not.toHaveBeenCalled();
  });

  it('GET still pending: subs NOT rendered', async () => {
    mockGetPreferences.mockReturnValue(new Promise(() => {}));
    const rendered = render(<ProfileScreen {...makeProps()} />);
    await waitFor(() => expect(mockGetPreferences).toHaveBeenCalled());
    await waitFor(() => expect(rendered.getByLabelText(AI_LABEL)).toBeTruthy());
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(2);
  });

  it('a row that stores one sub OFF: flipping another sub writes the stored OFF back, not a default ON', async () => {
    const rendered = await mount({
      ai_sharing_enabled: false,
      notification_types: { decision_insight: false },
    });
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(5);
    // Switch[3] = cohort_curiosity ("peer_decision_updates").
    fireEvent(rendered.UNSAFE_getAllByType(Switch)[3], 'valueChange', false);
    await waitFor(() => expect(mockPutReengagementSubs).toHaveBeenCalledTimes(1));
    expect(mockPutReengagementSubs.mock.calls[0][0]).toStrictEqual({
      decision_insights: false,
      peer_decision_updates: false,
      decision_retrospectives: true,
    });
  });
});

describe('W3-14 R5 (iv) — AI toggle failures render catalog copy and roll back', () => {
  it.each([
    ['422 VALIDATION_ERROR envelope', VALIDATION_422],
    ['400 "Failed to save preferences" envelope', SAVE_400],
    ['codeless transport 502', TRANSPORT_502],
    ['bare Starlette 404 (backend without the route)', STARLETTE_404],
  ])('%s -> profile.aiSharing.errorSave, switch back to OFF', async (_l, makeErr) => {
    // Both savers reject identically, so today's savePreferences path shows
    // what it renders (the raw string) and the fixed path is judged the same way.
    mockPutPreferenceToggles.mockRejectedValue(makeErr());
    mockSavePreferences.mockRejectedValue(makeErr());
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['profile.aiSharing.errorSave']);
    expect(rendered.UNSAFE_getAllByType(Switch)[0].props.value).toBe(false);
    expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1);
    expect(mockSavePreferences).not.toHaveBeenCalled();
  });

  it('bare 404 with NO priorities (the R-17 compatibility row): neutral copy + rollback', async () => {
    mockPutPreferenceToggles.mockRejectedValue(STARLETTE_404());
    const rendered = await mount(null);
    expect(rendered.getByLabelText(AI_LABEL).props.accessibilityState.disabled).toBe(false);

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['profile.aiSharing.errorSave']);
    expect(rendered.UNSAFE_getAllByType(Switch)[0].props.value).toBe(false);
  });
});

describe('W3-14 R5 (v) — rate-limit copy and the `result.error ||` arm', () => {
  it('AI toggle rejects RATE_LIMITED -> common.errors.rateLimited', async () => {
    mockPutPreferenceToggles.mockRejectedValue(RATE_LIMITED_429());
    mockSavePreferences.mockRejectedValue(RATE_LIMITED_429());
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['common.errors.rateLimited']);
    expect(rendered.UNSAFE_getAllByType(Switch)[0].props.value).toBe(false);
  });

  it('AI toggle resolves {success:false, error:"oops"} -> profile.aiSharing.errorSave, never "oops"', async () => {
    mockPutPreferenceToggles.mockResolvedValue({ success: false, error: 'oops' });
    mockSavePreferences.mockResolvedValue({ success: false, error: 'oops' });
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[0], 'valueChange', true);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(/oops/);
    expect(line).toBe(EN['profile.aiSharing.errorSave']);
  });

  it('notifications master rejects a codeless 502 -> profile.notifs.errorSave', async () => {
    mockPutPreferenceToggles.mockRejectedValue(TRANSPORT_502());
    mockSavePreferences.mockRejectedValue(TRANSPORT_502());
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['profile.notifs.errorSave']);
    // Rolled back: master ON again, so the three subs are back.
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(5);
  });

  // Fixer (adversary minor #2): the master catch routes on the PARSED code.
  it('notifications master rejects RATE_LIMITED -> common.errors.rateLimited, rolled back', async () => {
    mockPutPreferenceToggles.mockRejectedValue(RATE_LIMITED_429());
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['common.errors.rateLimited']);
    expect(rendered.UNSAFE_getAllByType(Switch)[1].props.value).toBe(true);
  });

  it('notifications master resolves {success:false, error:"Failed to update ..."} -> profile.notifs.errorSave', async () => {
    const body = { success: false, error: 'Failed to update notification preferences' };
    mockPutPreferenceToggles.mockResolvedValue(body);
    mockSavePreferences.mockResolvedValue(body);
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    const [line] = errorLines(rendered);
    expect(line).not.toMatch(RAW);
    expect(line).toBe(EN['profile.notifs.errorSave']);
  });

  // The resolved `{success:false}` arm must roll the optimistic flip back
  // (the catch arm is pinned separately by the 502 row above).
  it('notifications master resolves {success:false}: rolled back to ON, the three subs return', async () => {
    mockPutPreferenceToggles.mockResolvedValue({ success: false, error: 'oops' });
    const rendered = await mount({ ...FULL_PREFS });
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(5);

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[1], 'valueChange', false);
    await waitFor(() => expect(mockPutPreferenceToggles).toHaveBeenCalledTimes(1));
    expect(mockPutPreferenceToggles.mock.calls[0][0]).toStrictEqual({ notifications_enabled: false });
    await waitFor(() => expect(errorLines(rendered).length).toBeGreaterThan(0));
    expect(rendered.UNSAFE_getAllByType(Switch)[1].props.value).toBe(true);
    expect(rendered.UNSAFE_getAllByType(Switch).length).toBe(5);
  });
});

describe('W3-14 R5 (vi) — sub-toggle (PUT /reengagement-subs) failures', () => {
  it('rejects RATE_LIMITED -> Alert body AND inline text are common.errors.rateLimited', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    mockPutReengagementSubs.mockRejectedValue(RATE_LIMITED_429());
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[2], 'valueChange', false);
    await waitFor(() => expect(alertSpy).toHaveBeenCalledTimes(1));
    expect(alertSpy.mock.calls[0][0]).toBe(EN['profile.notifs.errorTitle']);
    const alertBody = alertSpy.mock.calls[0][1];
    expect(alertBody).not.toMatch(RAW);
    expect(alertBody).toBe(EN['common.errors.rateLimited']);
    const [line] = errorLines(rendered);
    expect(line).toBe(EN['common.errors.rateLimited']);
    alertSpy.mockRestore();
  });

  it('resolves {success:false, error:"Failed to update ..."} -> Alert body is profile.notifs.errorSave', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    mockPutReengagementSubs.mockResolvedValue({
      success: false,
      error: 'Failed to update notification preferences',
    });
    const rendered = await mount({ ...FULL_PREFS });

    fireEvent(rendered.UNSAFE_getAllByType(Switch)[2], 'valueChange', false);
    await waitFor(() => expect(alertSpy).toHaveBeenCalledTimes(1));
    const alertBody = alertSpy.mock.calls[0][1];
    expect(alertBody).not.toMatch(RAW);
    expect(alertBody).toBe(EN['profile.notifs.errorSave']);
    alertSpy.mockRestore();
  });
});

// Fixer (tests_that_prove_nothing #2): the password catch routes ONLY the two
// 429 codes to catalog copy; the 400 arm keeps the backend sentence (spec §4,
// "Current password is incorrect" is the actionable information).
describe('W3-14 — password modal catch', () => {
  const LOCKED_429 = () =>
    axiosError(429, {
      success: false,
      error: 'Too many failed attempts. Try again in 15 minutes.',
      code: 'ACCOUNT_LOCKED',
      request_id: 'r6',
      retry_after_seconds: 900,
    });
  // `auth_routes.py` raises HTTPException(400, detail=result["error"]) — a
  // plain-string detail with no code.
  const WRONG_PW_400 = () =>
    axiosError(400, { success: false, error: 'Current password is incorrect', request_id: 'r7' });

  async function submitPassword(rendered: any) {
    fireEvent.press(rendered.getByTestId('profile-row-password'));
    fireEvent.changeText(rendered.getByPlaceholderText(EN['profile.password.current']), 'OldPass123');
    fireEvent.changeText(rendered.getByPlaceholderText(EN['profile.password.new']), 'NewPass1234');
    fireEvent.changeText(rendered.getByPlaceholderText(EN['profile.password.confirm']), 'NewPass1234');
    const saves = rendered.getAllByText(EN['profile.changePassword']);
    fireEvent.press(saves[saves.length - 1]);
    await waitFor(() => expect(mockChangePassword).toHaveBeenCalledTimes(1));
  }

  it.each([
    ['RATE_LIMITED', RATE_LIMITED_429, 'common.errors.rateLimited'],
    ['ACCOUNT_LOCKED', LOCKED_429, 'common.errors.locked'],
  ])('%s -> catalog copy, never the backend sentence', async (_l, makeErr, key) => {
    mockChangePassword.mockRejectedValue(makeErr());
    const rendered = await mount({ ...FULL_PREFS });
    await submitPassword(rendered);
    await waitFor(() => expect(rendered.getByText(EN[key])).toBeTruthy());
    expect(rendered.queryAllByText(/Rate limit|Too many failed|Try again/i).length).toBe(0);
  });

  it('400 plain-string detail keeps the backend sentence (deliberate)', async () => {
    mockChangePassword.mockRejectedValue(WRONG_PW_400());
    const rendered = await mount({ ...FULL_PREFS });
    await submitPassword(rendered);
    await waitFor(() => expect(rendered.getByText('Current password is incorrect')).toBeTruthy());
  });
});

describe('W3-14 R5 — preserve: sub-toggles still use /reengagement-subs with plural keys', () => {
  it('a sub flip sends the three plural keys and never touches the master routes', async () => {
    const rendered = await mount({ ...FULL_PREFS });
    fireEvent(rendered.UNSAFE_getAllByType(Switch)[2], 'valueChange', false);
    await waitFor(() => expect(mockPutReengagementSubs).toHaveBeenCalledTimes(1));
    expect(mockPutReengagementSubs.mock.calls[0][0]).toStrictEqual({
      decision_insights: false,
      peer_decision_updates: true,
      decision_retrospectives: true,
    });
    expect(mockPutPreferenceToggles).not.toHaveBeenCalled();
    expect(mockSavePreferences).not.toHaveBeenCalled();
  });
});

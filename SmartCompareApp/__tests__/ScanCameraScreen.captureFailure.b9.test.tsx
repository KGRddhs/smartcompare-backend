/**
 * B9 — a camera capture (or library pick) that fails must say so.
 *
 * `onCapture` used to end in an empty catch plus a bare `if (!photo?.uri)
 * return;`. Both exits left the slot empty with zero explanation: the
 * shutter haptic fired, the press-scale played, and the "1 of 2" pill never
 * moved. The adjacent M13-54 work already gives the under-2-pick case a
 * visible Alert, so the silence here was a gap, not a house style.
 *
 * The copy is checked against the REAL en.json so these assertions are on
 * the sentence a user sees, and the same catalog is checked against
 * `.copy-policy.json`'s scary vocabulary by __tests__/copy-policy.test.ts.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';
import arCatalog from '../src/i18n/ar.json';

const EN = enCatalog as Record<string, string>;
const AR = arCatalog as Record<string, string>;

const takePictureMock = jest.fn();
const launchImageLibraryMock = jest.fn();

jest.mock('expo-camera', () => {
  const ReactInner = require('react');
  class CameraView extends ReactInner.Component {
    takePictureAsync = takePictureMock;
    render() {
      return ReactInner.createElement('CameraView', this.props);
    }
  }
  return {
    CameraView,
    useCameraPermissions: () => [{ granted: true }, jest.fn()],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: launchImageLibraryMock,
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: { defaultValue?: string }) =>
        catalog[key] ?? opts?.defaultValue ?? key,
      i18n: { language: 'en', changeLanguage: jest.fn() },
    }),
  };
});

import ScanCameraScreen, {
  __resetScanCameraCacheForTests,
} from '../src/screens/ScanCameraScreen';

const makeNav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

beforeEach(() => {
  jest.clearAllMocks();
  __resetScanCameraCacheForTests();
  takePictureMock.mockResolvedValue({ uri: 'file://photo.jpg' });
  launchImageLibraryMock.mockResolvedValue({
    canceled: false,
    assets: [{ uri: 'file://lib.jpg' }],
  });
});

describe('B9 — a failed capture is surfaced, not swallowed', () => {
  it('shows the retry notice when takePictureAsync rejects', async () => {
    takePictureMock.mockRejectedValue(new Error('camera busy'));
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    expect(screen.queryByTestId('scan-capture-notice')).toBeNull();

    await act(async () => {
      fireEvent.press(screen.getByTestId('shutter-button'));
    });

    await waitFor(() => expect(screen.getByTestId('scan-capture-notice')).toBeTruthy());
    expect(screen.getByText(EN['home.camera.capture_retry_hint'])).toBeTruthy();
    expect(screen.getByTestId('scan-capture-retry')).toBeTruthy();
    // The slot really is still empty — the notice is the ONLY new signal.
    expect(screen.queryByTestId('image-slot-0-thumb')).toBeNull();
  });

  it('shows the retry notice when the capture resolves without a URI', async () => {
    takePictureMock.mockResolvedValue({});
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('shutter-button'));
    });

    await waitFor(() => expect(screen.getByTestId('scan-capture-notice')).toBeTruthy());
  });

  it('the notice action re-fires the shutter and clears once a frame lands', async () => {
    takePictureMock.mockRejectedValueOnce(new Error('camera busy'));
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('shutter-button'));
    });
    await waitFor(() => expect(screen.getByTestId('scan-capture-notice')).toBeTruthy());

    await act(async () => {
      fireEvent.press(screen.getByTestId('scan-capture-retry'));
    });

    await waitFor(() => expect(screen.getByTestId('image-slot-0-thumb')).toBeTruthy());
    expect(takePictureMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId('scan-capture-notice')).toBeNull();
  });

  it('a successful capture never raises the notice', async () => {
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('shutter-button'));
    });

    await waitFor(() => expect(screen.getByTestId('image-slot-0-thumb')).toBeTruthy());
    expect(screen.queryByTestId('scan-capture-notice')).toBeNull();
  });
});

describe('B9 — the library picker gets the same treatment', () => {
  it('shows the pick notice when the picker throws', async () => {
    launchImageLibraryMock.mockRejectedValue(new Error('picker unavailable'));
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('gallery-button'));
    });

    await waitFor(() => expect(screen.getByTestId('scan-capture-notice')).toBeTruthy());
    expect(screen.getByText(EN['home.camera.pick_retry_hint'])).toBeTruthy();
    expect(screen.getByText(EN['home.camera.pick_retry_action'])).toBeTruthy();
  });

  it('the pick notice retries the picker, not the shutter', async () => {
    launchImageLibraryMock.mockRejectedValueOnce(new Error('picker unavailable'));
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('gallery-button'));
    });
    await waitFor(() => expect(screen.getByTestId('scan-capture-notice')).toBeTruthy());

    await act(async () => {
      fireEvent.press(screen.getByTestId('scan-capture-retry'));
    });

    await waitFor(() => expect(screen.getByTestId('image-slot-0-thumb')).toBeTruthy());
    expect(launchImageLibraryMock).toHaveBeenCalledTimes(2);
    expect(takePictureMock).not.toHaveBeenCalled();
  });

  it('a user-cancelled pick stays silent — cancelling is not a failure', async () => {
    launchImageLibraryMock.mockResolvedValue({ canceled: true });
    const screen = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('gallery-button'));
    });

    await waitFor(() => expect(launchImageLibraryMock).toHaveBeenCalled());
    expect(screen.queryByTestId('scan-capture-notice')).toBeNull();
  });
});

describe('B9 — the notice copy honours the zero-scary-copy contract', () => {
  it.each([
    'home.camera.capture_retry_hint',
    'home.camera.capture_retry_action',
    'home.camera.pick_retry_hint',
    'home.camera.pick_retry_action',
  ])('%s exists and carries no forbidden token', (key) => {
    const value = EN[key];
    expect(typeof value).toBe('string');
    expect(value.length).toBeGreaterThan(0);
    for (const banned of ["couldn't", 'try again', 'failed to', 'failed']) {
      expect(value.toLowerCase()).not.toContain(banned);
    }
  });
});

/**
 * P-B9 (polish round) — the notice copy describes a LOCAL miss and agrees
 * with the button underneath it.
 *
 * Two defects lived in these four strings. (1) Both Arabic hints were
 * calques of the English delivery idioms: they said the frame/photo
 * "لم تصل" — did not ARRIVE — for a capture that never leaves the phone
 * (`takePictureAsync` / `launchImageLibraryAsync` upload nothing), so an
 * Arabic reader was told a transfer failed. (2) On the gallery arm the
 * hint said "اخترها" / "pick it one more time" (that same photo) directly
 * above a button offering "اختر صورة أخرى" / "Pick another" — two
 * different instructions in one notice. `onCaptureNoticeRetry` (above)
 * re-fires the shutter or re-opens the picker; it never re-submits the
 * frame that just missed, so "another" is the honest half of the pair and
 * both halves now say it.
 *
 * The English fence lives above; this block adds the Arabic side plus the
 * hint/button agreement, and pins the screen's own `defaultValue`
 * fallbacks to the catalog so the two can't drift apart again.
 */
describe('P-B9 — the retry copy is local, and the hint agrees with its button', () => {
  const ARMS = [
    {
      arm: 'capture',
      hint: 'home.camera.capture_retry_hint',
      action: 'home.camera.capture_retry_action',
    },
    {
      arm: 'pick',
      hint: 'home.camera.pick_retry_hint',
      action: 'home.camera.pick_retry_action',
    },
  ] as const;

  const KEYS = ARMS.flatMap((a) => [a.hint, a.action]);

  // وصل / تصل = to arrive, to reach — transmission verbs. تحميل = to
  // upload/download. None of them can describe a failure that happened
  // entirely on-device.
  const AR_DELIVERY = /تصل|وصل|أُرسل|إرسال|تحميل/;
  const EN_DELIVERY = /come through|didn'?t land|\bupload|\bsent\b|\bdeliver|\breceiv/i;
  // أخرى / غيرها = another / a different one.
  const AR_ANOTHER = /أخرى|غيرها/;

  it('all four keys resolve to real copy in BOTH catalogs', () => {
    // Positive control for every assertion below — an absent key would
    // otherwise sail through `not.toMatch` on `undefined`.
    for (const key of KEYS) {
      expect(typeof EN[key]).toBe('string');
      expect(EN[key].trim().length).toBeGreaterThan(0);
      expect(typeof AR[key]).toBe('string');
      expect(AR[key].trim().length).toBeGreaterThan(0);
    }
  });

  it.each(ARMS)(
    'the $arm hint names a local miss, never a delivery one',
    ({ hint }) => {
      expect(AR[hint]).not.toMatch(AR_DELIVERY);
      expect(EN[hint]).not.toMatch(EN_DELIVERY);
    }
  );

  it.each(ARMS)(
    'the $arm hint asks for the same thing its button offers',
    ({ hint, action }) => {
      expect(EN[hint].toLowerCase()).toContain('another');
      expect(EN[action].toLowerCase()).toContain('another');
      expect(AR[hint]).toMatch(AR_ANOTHER);
      expect(AR[action]).toMatch(AR_ANOTHER);
    }
  );

  it('neither pick string sends the user back to the SAME photo', () => {
    // اخترها = "choose IT (fem.)" — re-select the very photo that just
    // missed, which is precisely what the button contradicted.
    expect(AR['home.camera.pick_retry_hint']).not.toContain('اخترها');
    expect(EN['home.camera.pick_retry_hint'].toLowerCase()).not.toContain(
      'pick it'
    );
  });

  it("the screen's defaultValue fallbacks stay identical to en.json", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, '..', 'src', 'screens', 'ScanCameraScreen.tsx'),
        'utf8'
      )
      // Comments first: prose about the copy must never satisfy the grep.
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^[ \t]*\/\/.*$/gm, '');

    const fallbacks = new Map<string, string>();
    const call =
      /t\(\s*'([\w.]+)'\s*,\s*\{\s*defaultValue:\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g;
    for (let m = call.exec(source); m !== null; m = call.exec(source)) {
      const raw = m[2];
      fallbacks.set(
        m[1],
        raw.startsWith('"')
          ? (JSON.parse(raw) as string)
          : raw.slice(1, -1).replace(/\\'/g, "'")
      );
    }

    // Positive control: the grep really found all four call sites.
    expect(KEYS.filter((key) => fallbacks.has(key))).toHaveLength(KEYS.length);
    for (const key of KEYS) {
      expect(fallbacks.get(key)).toBe(EN[key]);
    }
  });
});

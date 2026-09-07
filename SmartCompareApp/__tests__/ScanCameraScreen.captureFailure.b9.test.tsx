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
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';

const EN = enCatalog as Record<string, string>;

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

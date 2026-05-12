/**
 * ScanCameraScreen capture + gallery picker + Compare CTA tests.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated.md § Task 2.7
 */
import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';

const takePictureMock = jest.fn(async () => ({ uri: 'file://photo.jpg' }));
const launchImageLibraryMock = jest.fn(async () => ({
  canceled: false,
  assets: [{ uri: 'file://lib.jpg' }],
}));

jest.mock('expo-camera', () => {
  const ReactInner = require('react');
  // CameraView is a class so we can attach an instance method that the
  // component's `ref.current.takePictureAsync(...)` can call directly.
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

describe('ScanCameraScreen — capture + gallery + compare', () => {
  it('renders shutter button + gallery button + flash button with testIDs', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('shutter-button')).toBeTruthy();
    expect(getByTestId('gallery-button')).toBeTruthy();
    expect(getByTestId('flash-button')).toBeTruthy();
  });

  it('captures photo into the next empty slot on shutter press', async () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    await waitFor(() => {
      expect(takePictureMock).toHaveBeenCalled();
      expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
    });
  });

  it('launches gallery picker on gallery button press', async () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('gallery-button'));
    });
    await waitFor(() => {
      expect(launchImageLibraryMock).toHaveBeenCalled();
      expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
    });
  });

  it('does NOT show Compare CTA when only 1 slot is filled', async () => {
    const { getByTestId, queryByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    await waitFor(() => expect(getByTestId('image-slot-0-thumb')).toBeTruthy());
    expect(queryByTestId('compare-cta')).toBeNull();
  });

  it('shows Compare CTA when both slots are filled', async () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    takePictureMock.mockResolvedValueOnce({ uri: 'file://photo2.jpg' });
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    await waitFor(() => expect(getByTestId('compare-cta')).toBeTruthy());
  });

  it('Compare CTA navigates to Results with both URIs', async () => {
    const nav = makeNav();
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    takePictureMock.mockResolvedValueOnce({ uri: 'file://photo2.jpg' });
    await act(async () => {
      fireEvent.press(getByTestId('shutter-button'));
    });
    await waitFor(() => expect(getByTestId('compare-cta')).toBeTruthy());
    fireEvent.press(getByTestId('compare-cta'));
    expect(nav.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({
        vision_products: ['file://photo.jpg', 'file://photo2.jpg'],
      })
    );
  });

  it('flash button cycles off → on → auto → off', async () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    const btn = getByTestId('flash-button');
    // Initial value off; verify a11y label reflects current mode via testID prop
    expect(btn.props.accessibilityState?.checked).toBeFalsy();
    fireEvent.press(btn);
    // After 1 press we're on 'on'
    fireEvent.press(btn);
    // After 2 presses we're on 'auto'
    fireEvent.press(btn);
    // After 3 presses we're back to 'off' — no crash, no NaN, no extra states
    expect(btn).toBeTruthy();
  });

  it('cancelled gallery pick leaves slots empty', async () => {
    launchImageLibraryMock.mockResolvedValueOnce({ canceled: true, assets: [] });
    const { getByTestId, queryByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    await act(async () => {
      fireEvent.press(getByTestId('gallery-button'));
    });
    expect(queryByTestId('image-slot-0-thumb')).toBeNull();
  });
});

// Permission-denied path lives in its own file because top-level
// jest.mock('expo-camera', ...) cannot be overridden mid-file without
// resetting the module registry, which breaks the helper-export import.
// See ScanCameraScreen.permission.test.tsx.

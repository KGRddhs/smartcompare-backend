/**
 * ScanCameraScreen — permission-denied fallback test.
 *
 * Kept separate from the capture-flow test file so this file can mock
 * `useCameraPermissions` to return `granted: false` without colliding
 * with the granted-state mock used by the capture flow.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

// M13-54: a stable requestPermission mock so we can assert the denied
// branch's CTA actually calls it (the previous inline `jest.fn()` handed
// out a fresh spy on every render, un-assertable).
const mockRequestPermission = jest.fn();

jest.mock('expo-camera', () => {
  const ReactInner = require('react');
  class CameraView extends ReactInner.Component {
    render() {
      return ReactInner.createElement('CameraView', this.props);
    }
  }
  return {
    CameraView,
    useCameraPermissions: () => [{ granted: false }, mockRequestPermission],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn(() =>
    Promise.resolve({ canceled: true, assets: [] })
  ),
  MediaTypeOptions: { Images: 'Images' },
}));

import ScanCameraScreen from '../src/screens/ScanCameraScreen';

const makeNav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

beforeEach(() => {
  mockRequestPermission.mockClear();
});

describe('ScanCameraScreen — permission denied', () => {
  it('renders the permission-required pad instead of the camera UI', () => {
    const { getByTestId, queryByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-permission')).toBeTruthy();
    // Capture-flow controls are NOT rendered when permission is denied.
    expect(queryByTestId('shutter-button')).toBeNull();
    expect(queryByTestId('gallery-button')).toBeNull();
    expect(queryByTestId('flash-button')).toBeNull();
  });

  it('still renders the close button so the user can dismiss the modal', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-close')).toBeTruthy();
  });

  // M13-54: the denied branch is no longer a dead end — it renders a
  // grant-access CTA (calling requestPermission) and a gallery link.
  it('renders the grant-access CTA and the gallery link', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-permission-cta')).toBeTruthy();
    expect(getByTestId('scan-camera-permission-gallery')).toBeTruthy();
  });

  it('grant-access CTA calls requestPermission', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    fireEvent.press(getByTestId('scan-camera-permission-cta'));
    expect(mockRequestPermission).toHaveBeenCalledTimes(1);
  });
});

/**
 * ScanCameraScreen — permission-denied fallback test.
 *
 * Kept separate from the capture-flow test file so this file can mock
 * `useCameraPermissions` to return `granted: false` without colliding
 * with the granted-state mock used by the capture flow.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('expo-camera', () => {
  const ReactInner = require('react');
  class CameraView extends ReactInner.Component {
    render() {
      return ReactInner.createElement('CameraView', this.props);
    }
  }
  return {
    CameraView,
    useCameraPermissions: () => [{ granted: false }, jest.fn()],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn(),
  MediaTypeOptions: { Images: 'Images' },
}));

import ScanCameraScreen from '../src/screens/ScanCameraScreen';

const makeNav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

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
});

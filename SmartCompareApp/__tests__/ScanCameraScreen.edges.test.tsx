/**
 * ScanCameraScreen edge-case coverage.
 *
 * Extends ScanCameraScreen.test.tsx with:
 * - Default state renders without throwing
 * - Help button does NOT call goBack
 * - Mount does not consume the navigation prop (no goBack on mount)
 * - Both slots start empty (no thumbs)
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('expo-camera', () => {
  const ReactInner = require('react');
  class CameraView extends ReactInner.Component {
    takePictureAsync = jest.fn();
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
  launchImageLibraryAsync: jest.fn(),
  MediaTypeOptions: { Images: 'Images' },
}));

import ScanCameraScreen from '../src/screens/ScanCameraScreen';

const makeNav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

describe('ScanCameraScreen — edges', () => {
  it('renders without throwing with default empty slot state', () => {
    expect(() =>
      render(<ScanCameraScreen navigation={makeNav()} route={{} as any} />)
    ).not.toThrow();
  });

  it('renders close + help + reticle + slots in a single mount', () => {
    const { getByTestId, getAllByTestId, UNSAFE_root } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-close')).toBeTruthy();
    expect(getByTestId('scan-camera-help')).toBeTruthy();
    expect(getAllByTestId(/^image-slot-\d$/)).toHaveLength(2);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThanOrEqual(1);
  });

  it('mount does NOT call navigation.goBack', () => {
    const nav = makeNav();
    render(<ScanCameraScreen navigation={nav} route={{} as any} />);
    expect(nav.goBack).not.toHaveBeenCalled();
    expect(nav.navigate).not.toHaveBeenCalled();
  });

  it('help button does NOT call navigation.goBack', () => {
    const nav = makeNav();
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav} route={{} as any} />
    );
    fireEvent.press(getByTestId('scan-camera-help'));
    expect(nav.goBack).not.toHaveBeenCalled();
    expect(nav.navigate).not.toHaveBeenCalled();
  });

  it('close button only triggers goBack, never navigate', () => {
    const nav = makeNav();
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav} route={{} as any} />
    );
    fireEvent.press(getByTestId('scan-camera-close'));
    expect(nav.goBack).toHaveBeenCalledTimes(1);
    expect(nav.navigate).not.toHaveBeenCalled();
  });

  it('default state renders both slots empty (no thumbnails)', () => {
    const { queryByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(queryByTestId('image-slot-0-thumb')).toBeNull();
    expect(queryByTestId('image-slot-1-thumb')).toBeNull();
  });
});

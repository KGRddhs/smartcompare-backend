import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import ScanCameraScreen from '../src/screens/ScanCameraScreen';

const makeNav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

describe('ScanCameraScreen skeleton', () => {
  it('renders close button with testID', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-close')).toBeTruthy();
  });

  it('renders help button with testID', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getByTestId('scan-camera-help')).toBeTruthy();
  });

  it('renders exactly 2 image slots', () => {
    const { getAllByTestId } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    expect(getAllByTestId(/^image-slot-\d$/)).toHaveLength(2);
  });

  it('close button calls navigation.goBack', () => {
    const nav = makeNav();
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav} route={{} as any} />
    );
    fireEvent.press(getByTestId('scan-camera-close'));
    expect(nav.goBack).toHaveBeenCalledTimes(1);
  });

  it('renders ScannerReticle (at least one Svg root)', () => {
    const { UNSAFE_root } = render(
      <ScanCameraScreen navigation={makeNav()} route={{} as any} />
    );
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs.length).toBeGreaterThanOrEqual(1);
  });
});

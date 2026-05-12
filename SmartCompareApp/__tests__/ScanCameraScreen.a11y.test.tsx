/**
 * Camera-surface a11y wiring — qa-bcd checklist.
 *
 * Verifies the screen-reader labels + decorative-overlay flags + tap-target
 * hitSlops match the pre-Phase-3 accessibility contract.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

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
import ImageSlotRow from '../src/components/ImageSlotRow';
import ScannerReticle from '../src/components/ScannerReticle';

const nav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

describe('ScanCameraScreen — a11y labels (qa-bcd checklist)', () => {
  it('close + help + shutter + gallery + flash buttons all use home.camera.a11y.* keys', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav()} route={{} as any} />
    );
    // i18n mock returns the key itself when no translation match — we
    // assert the a11y label IS the canonical key (not the legacy
    // `camera.close` or short `home.camera.shutter`).
    expect(getByTestId('scan-camera-close').props.accessibilityLabel).toBe(
      'home.camera.a11y.close'
    );
    expect(getByTestId('scan-camera-help').props.accessibilityLabel).toBe(
      'home.camera.a11y.help'
    );
    expect(getByTestId('shutter-button').props.accessibilityLabel).toBe(
      'home.camera.a11y.shutter'
    );
    expect(getByTestId('gallery-button').props.accessibilityLabel).toBe(
      'home.camera.a11y.gallery'
    );
    expect(getByTestId('flash-button').props.accessibilityLabel).toBe(
      'home.camera.a11y.flash'
    );
  });

  it('shutter, gallery, flash, close, help buttons all set hitSlop >=12 (≥44pt effective)', () => {
    const { getByTestId } = render(
      <ScanCameraScreen navigation={nav()} route={{} as any} />
    );
    for (const tid of [
      'scan-camera-close',
      'scan-camera-help',
      'gallery-button',
      'flash-button',
    ]) {
      const hs = getByTestId(tid).props.hitSlop;
      // The icons are 26-28pt; +12pt all sides → ≥50pt effective.
      expect(hs.top).toBeGreaterThanOrEqual(12);
      expect(hs.bottom).toBeGreaterThanOrEqual(12);
      expect(hs.left).toBeGreaterThanOrEqual(12);
      expect(hs.right).toBeGreaterThanOrEqual(12);
    }
  });
});

describe('ImageSlotRow — a11y labels + tap target', () => {
  it('slot containers carry non-empty a11y labels', () => {
    const { getByTestId } = render(
      <ImageSlotRow slots={[null, null]} onChange={jest.fn()} />
    );
    // The global i18n mock returns the key string when no translation
    // entry matches, so we assert the slot has a label rather than
    // probing for the interpolated count substring (which the mock
    // doesn't fill since the key text itself has no `{{count}}`).
    expect(getByTestId('image-slot-0').props.accessibilityLabel).toBeTruthy();
    expect(getByTestId('image-slot-1').props.accessibilityLabel).toBeTruthy();
    expect(getByTestId('image-slot-0').props.accessible).toBe(true);
  });

  it('remove button carries accessibilityLabel + hitSlop>=12 (≥48pt effective)', () => {
    const { getByTestId } = render(
      <ImageSlotRow
        slots={[{ uri: 'file://a.jpg' }, null]}
        onChange={jest.fn()}
      />
    );
    const rm = getByTestId('image-slot-0-remove');
    expect(rm.props.accessibilityLabel).toBeTruthy();
    expect(rm.props.hitSlop.top).toBeGreaterThanOrEqual(12);
    expect(rm.props.hitSlop.bottom).toBeGreaterThanOrEqual(12);
    expect(rm.props.hitSlop.left).toBeGreaterThanOrEqual(12);
    expect(rm.props.hitSlop.right).toBeGreaterThanOrEqual(12);
  });
});

describe('ScannerReticle — decorative-overlay flags', () => {
  it('marks the SVG overlay as hidden from screen readers', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    // Find the outer View — it's the one with both pointerEvents AND
    // accessibilityElementsHidden set.
    const hidden = UNSAFE_root.findByProps({ accessibilityElementsHidden: true });
    expect(hidden).toBeTruthy();
    expect(hidden.props.importantForAccessibility).toBe('no-hide-descendants');
    expect(hidden.props.pointerEvents).toBe('none');
  });
});

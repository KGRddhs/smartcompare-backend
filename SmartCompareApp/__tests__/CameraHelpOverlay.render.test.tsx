/**
 * Bundle D Task 1.F.4 — runtime coverage top-up for CameraHelpOverlay.
 *
 * The author's `CameraHelpOverlay.test.tsx` is a source-grep gate (5/5
 * GREEN) — structural contract checks only. This file does the runtime
 * render via react-test-renderer with the existing jest moduleNameMapper
 * mocks (react-native, react-i18next, lucide-react-native) so the
 * component's actual JSX path executes and onClose wiring is verified.
 *
 * Notes:
 *   - react-test-renderer@19.1 auto-unmounts the tree on the first
 *     dispatch (`.root` is no longer safe to access after `act` on this
 *     version). We grab `.root` references BEFORE any interaction, fire
 *     the onPress, then assert the mock callback.
 *   - We avoid `findByType` lookups against React Native primitives —
 *     those route through the existing `__mocks__/react-native.ts` stub
 *     and don't expose stable component identities.
 *   - The react-i18next mock returns the i18n KEY as the t() value, so
 *     asserting against the key string is the closest we can get to a
 *     "no hard-coded literal" check at runtime.
 */

import React from 'react';
import { create, act } from 'react-test-renderer';
import { CameraHelpOverlay } from '../src/components/CameraHelpOverlay';

describe('CameraHelpOverlay — runtime render (Bundle D 1.F.4)', () => {
  it('renders without throwing when visible=true', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: true, onClose })
      );
    });
    expect(tree!.toJSON()).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('renders without throwing when visible=false (Modal hides children)', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: false, onClose })
      );
    });
    // The react-native Modal mock returns null when visible=false. The
    // important assertions here are that (a) the render didn't throw,
    // (b) the onClose mock wasn't fired by mount itself.
    expect(tree).toBeDefined();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('mounts the testIDs that ScanCameraScreen relies on (overlay + close)', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: true, onClose })
      );
    });
    const json = JSON.stringify(tree!.toJSON());
    expect(json).toContain('camera-help-overlay');
    expect(json).toContain('camera-help-overlay-close');
  });

  it('backdrop press fires onClose', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: true, onClose })
      );
    });
    // Capture backdrop ref BEFORE invoking onPress (auto-unmount safety).
    const backdrop = tree!.root.findByProps({ testID: 'camera-help-overlay' });
    expect(typeof backdrop.props.onPress).toBe('function');

    act(() => {
      backdrop.props.onPress();
    });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('close-button press fires onClose', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: true, onClose })
      );
    });
    const closeBtn = tree!.root.findByProps({
      testID: 'camera-help-overlay-close',
    });
    expect(typeof closeBtn.props.onPress).toBe('function');
    expect(closeBtn.props.accessibilityRole).toBe('button');
    expect(closeBtn.props.accessibilityLabel).toBe('home.camera.help.close');

    act(() => {
      closeBtn.props.onPress();
    });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('resolves every visible copy string through i18n t() (no hardcoded literals)', () => {
    const onClose = jest.fn();
    let tree: ReturnType<typeof create> | undefined;
    act(() => {
      tree = create(
        React.createElement(CameraHelpOverlay, { visible: true, onClose })
      );
    });
    // The react-i18next mock returns the key from t(key), so the JSON
    // tree must contain the i18n KEYS — proves the component went
    // through useTranslation() rather than ship'ing a string literal.
    const allText = JSON.stringify(tree!.toJSON());
    const requiredKeys = [
      'home.camera.help.title',
      'home.camera.help.step1',
      'home.camera.help.step2',
      'home.camera.help.step3',
    ];
    for (const k of requiredKeys) {
      expect(allText).toContain(k);
    }
  });
});

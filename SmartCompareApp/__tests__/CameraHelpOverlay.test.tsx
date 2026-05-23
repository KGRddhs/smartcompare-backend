/**
 * Bundle D Task 1.F.4 — Camera ? help overlay (R17).
 *
 * Contract:
 * - A `CameraHelpOverlay` component is exported from
 *   `src/components/CameraHelpOverlay.tsx`.
 * - ScanCameraScreen's `?` button (testID `scan-camera-help`) has a
 *   working `onPress` that opens the overlay.
 * - EN + AR i18n keys for the help copy exist.
 * - Copy is free of forbidden vocabulary (couldn't / try again /
 *   failed to / تعذر / فشل / estimated).
 *
 * Source-grep tests: the runtime render path pulls in expo-camera +
 * permissions hook + Reanimated worklets that don't run cleanly in
 * the jest node env. The contract under test is structural (component
 * exists, button has onPress, i18n keys exist, copy is policy-clean),
 * so static analysis is the right granularity.
 */

import * as fs from 'fs';
import * as path from 'path';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const EN = require('../src/i18n/en.json') as Record<string, string>;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const AR = require('../src/i18n/ar.json') as Record<string, string>;

const OVERLAY_PATH = path.resolve(
  __dirname,
  '../src/components/CameraHelpOverlay.tsx'
);
const SCAN_PATH = path.resolve(
  __dirname,
  '../src/screens/ScanCameraScreen.tsx'
);

describe('Bundle D 1.F.4 — Camera help overlay (R17)', () => {
  it('CameraHelpOverlay component file exists', () => {
    expect(fs.existsSync(OVERLAY_PATH)).toBe(true);
  });

  it('CameraHelpOverlay exports a named component', () => {
    const src = fs.readFileSync(OVERLAY_PATH, 'utf8');
    expect(src).toMatch(/export\s+(function|const)\s+CameraHelpOverlay\b/);
    // Expects `visible` + `onClose` props for the standard overlay shape.
    expect(src).toMatch(/visible/);
    expect(src).toMatch(/onClose/);
  });

  it('ScanCameraScreen wires the ? button to open the overlay', () => {
    const src = fs.readFileSync(SCAN_PATH, 'utf8');
    // The dead `?` button gains onPress + a setHelpVisible(true) call.
    expect(src).toMatch(/testID="scan-camera-help"[\s\S]{0,200}onPress/);
    expect(src).toMatch(/setHelpVisible\s*\(\s*true\s*\)/);
    // The overlay is mounted in ScanCameraScreen JSX.
    expect(src).toMatch(/<CameraHelpOverlay\b/);
  });

  it('declares i18n keys for the overlay copy (EN + AR parity)', () => {
    // Standard three-step explainer + close action — anchor § Risks R17.
    const requiredKeys = [
      'home.camera.help.title',
      'home.camera.help.step1',
      'home.camera.help.step2',
      'home.camera.help.step3',
      'home.camera.help.close',
    ];
    for (const k of requiredKeys) {
      expect(EN[k]).toBeTruthy();
      expect(AR[k]).toBeTruthy();
    }
  });

  it('overlay copy uses approved vocabulary only (R17)', () => {
    const overlayKeys = Object.keys(EN).filter((k) =>
      k.startsWith('home.camera.help.')
    );
    const forbiddenEn = /couldn['']t|try again|failed to|estimated/i;
    const forbiddenAr = /تعذر|فشل/;
    for (const k of overlayKeys) {
      expect(EN[k]).not.toMatch(forbiddenEn);
      expect(AR[k]).not.toMatch(forbiddenAr);
    }
  });
});

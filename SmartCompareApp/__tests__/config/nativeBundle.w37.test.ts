/**
 * W3-7 — the native-only App Store bundle (ONE `eas build`).
 *
 * Findings: MB-TWO-LEVER-RELEASE-02 (RECORD_AUDIO + boilerplate
 * NSMicrophoneUsageDescription), MB-TWO-LEVER-RELEASE-08 (no
 * NSPrivacyCollectedDataTypes), MB-TWO-LEVER-RELEASE-09 (runtimeVersion pin —
 * the fix is deliberately NOT taken; e1 is the tripwire), MB-SAFE-HYGIENE-01
 * (placeholder launcher PNGs), MB-SAFE-HYGIENE-06 (react-native-gesture-handler
 * orphan dependency).
 *
 * OTA class: needs-build for every config half. Nothing asserted here reaches
 * phones by `eas update`.
 *
 * Every input is read with `fs` + `JSON.parse` — never `import`/`require`
 * (spec ruling R14): jest.config.js maps `\.(png|…)$` to __mocks__/fileStub.ts,
 * so an imported PNG would hash the STUB, and `require` of a JSON file caches
 * it for the run. No client module is imported.
 *
 * The executed-plugin assertions (a6, a7, a7b, a8) run the INSTALLED
 * expo-camera / expo-image-picker config plugins plus the two prebuild-config
 * Android base mods (`withInternalBlockedPermissions`, `withPermissions`,
 * registered in that order at @expo/prebuild-config
 * build/plugins/withDefaultPlugins.js:196) over an in-memory deep copy of
 * app.json with empty `modResults` and `introspect: true`. That is the code
 * path `expo prebuild` runs before it serialises Info.plist /
 * AndroidManifest.xml; nothing is written to disk. The Gradle manifest MERGE
 * (which finally drops expo-camera's library-level RECORD_AUDIO at
 * expo-camera/android/src/main/AndroidManifest.xml:3) only runs in a real
 * build — these tests assert the `tools:node="remove"` attribute that
 * @expo/config-plugins emits, not Gradle's behaviour.
 *
 * Session 70 U4b (docs/investigations/2026-09-30-session-70-state/
 * U4B_ICONS_DEPS_SPEC.md + its binding review corrections) closes (b) with the
 * MYEZ art — pinned by PNG header and PIXELS through the inline decoder
 * __tests__/helpers/pngDecode.ts (R9; Node's zlib, no dependency) — closes (d)
 * by removing react-native-gesture-handler, and adds the Expo SDK 54
 * patch-level block (k1-k6) after the U4a block.
 */
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as ts from 'typescript';
import * as zlib from 'zlib';
import { PNG_SIGNATURE, decodePng, pngChunks, readIhdr, type DecodedPng, type PngIhdr } from '../helpers/pngDecode';

type AnyConfig = any;

const APP = path.resolve(__dirname, '../..');
const REPO = path.resolve(APP, '..');

const readJson = (p: string): AnyConfig => JSON.parse(fs.readFileSync(p, 'utf8'));
const loadExpo = (): AnyConfig => readJson(path.join(APP, 'app.json')).expo;
const loadPkg = (): AnyConfig => readJson(path.join(APP, 'package.json'));
const loadLock = (): AnyConfig => readJson(path.join(APP, 'package-lock.json'));
const installedVersion = (name: string): string | undefined => {
  const p = path.join(APP, 'node_modules', ...name.split('/'), 'package.json');
  return fs.existsSync(p) ? (readJson(p).version as string) : undefined;
};
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v));

const RECORD_AUDIO = 'android.permission.RECORD_AUDIO';
const CAMERA = 'android.permission.CAMERA';
const CAMERA_PURPOSE = 'MYEZ needs camera access to photograph products for comparison.';
const PHOTOS_PURPOSE = 'MYEZ needs photo library access to identify products from your photos.';
// Session 69 U4a R2 (EXPO-07): the honest microphone purpose string, carried by
// BOTH the expo-camera and expo-image-picker entries (spec review Q1 option a).
const MIC_PURPOSE = 'MYEZ only uses the camera to photograph products. Audio is never recorded.';

function pluginOptions(expo: AnyConfig, name: string): Record<string, unknown> | undefined {
  const entry = (expo.plugins as unknown[]).find((p) =>
    Array.isArray(p) ? p[0] === name : p === name,
  );
  if (entry === undefined) return undefined;
  return Array.isArray(entry) ? ((entry[1] ?? {}) as Record<string, unknown>) : {};
}

// ---------------------------------------------------------------------------
// Executed-plugin harness (installed plugins, in-memory, no disk writes)
// ---------------------------------------------------------------------------
// Dynamic require by design: the INSTALLED plugin entry points are resolved
// from the app root at run time (they are CJS build artefacts, not typed
// imports). Only node_modules code is loaded this way — never app.json or a PNG.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const reqFromApp = (m: string): AnyConfig => require(require.resolve(m, { paths: [APP] }));

type PluginName = 'expo-camera' | 'expo-image-picker';
const FORWARD: PluginName[] = ['expo-camera', 'expo-image-picker'];
const REVERSED: PluginName[] = ['expo-image-picker', 'expo-camera'];

interface Compiled {
  plist: Record<string, unknown>;
  usesPermission: Record<string, string>[];
}

async function compile(expo: AnyConfig, order: PluginName[] = FORWARD): Promise<Compiled> {
  const withCamera = reqFromApp('expo-camera/app.plugin.js').default;
  const withImagePicker = reqFromApp('expo-image-picker/app.plugin.js').default;
  const { AndroidConfig } = reqFromApp('expo/config-plugins');

  let config: AnyConfig = clone(expo);
  config._internal = { projectRoot: APP, isDebug: false };
  for (const name of order) {
    const plugin = name === 'expo-camera' ? withCamera : withImagePicker;
    config = plugin(config, pluginOptions(config, name) ?? {});
  }
  // prebuild-config withDefaultPlugins.js:196 Android base-mod order.
  config = AndroidConfig.Permissions.withInternalBlockedPermissions(config);
  config = AndroidConfig.Permissions.withPermissions(config);

  const modRequest = {
    projectRoot: APP,
    platformProjectRoot: APP,
    projectName: 'Qaren',
    introspect: true,
  };
  const ios = await config.mods.ios.infoPlist({
    ...config,
    modRequest: { ...modRequest, platform: 'ios', modName: 'infoPlist' },
    modResults: {},
  });
  const android = await config.mods.android.manifest({
    ...config,
    modRequest: { ...modRequest, platform: 'android', modName: 'manifest' },
    modResults: {
      manifest: {
        $: { 'xmlns:android': 'http://schemas.android.com/apk/res/android' },
        'uses-permission': [],
        application: [],
      },
    },
  });
  return {
    plist: ios.modResults,
    usesPermission: android.modResults.manifest['uses-permission'].map(
      (u: { $: Record<string, string> }) => u.$,
    ),
  };
}

function expectRecordAudioOnlyBlocked(usesPermission: Record<string, string>[]): void {
  const audio = usesPermission.filter((p) => p['android:name'] === RECORD_AUDIO);
  expect(audio).toEqual([{ 'android:name': RECORD_AUDIO, 'tools:node': 'remove' }]);
}

// ===========================================================================
// (a) microphone — MB-TWO-LEVER-RELEASE-02
// ===========================================================================
describe('W3-7 (a) microphone: never requested on Android; honest purpose string on iOS since U4a', () => {
  it('a1 [SOURCE-SHAPE PIN, no compiled-output consequence — ruling R3] android.permissions does not list RECORD_AUDIO', () => {
    // Once expo-image-picker's microphonePermission:false lands,
    // @expo/config-plugins build/android/Permissions.js:52-55
    // (withBlockedPermissions) strips RECORD_AUDIO from
    // config.android.permissions at registration time, so re-adding the
    // string changes neither Info.plist nor the manifest (mutation M1). This
    // pin keeps the committed source honest; it is NOT behavioural coverage.
    // Since U4a the picker carries a string, not false, so that registration-
    // time strip no longer happens; android.blockedPermissions (a2) is what
    // blocks RECORD_AUDIO, and a7b proves it is the only guard.
    expect(loadExpo().android.permissions).not.toContain(RECORD_AUDIO);
  });

  it('a2 android.blockedPermissions contains RECORD_AUDIO (scope beyond the finding — ruling R5)', () => {
    // Schema key: @expo/config-types build/ExpoConfig.d.ts:657; consumed by
    // AndroidConfig.Permissions.withInternalBlockedPermissions. A plugin-
    // independent second guard on Android. Since U4a (both plugins carry the
    // honest string) it is the ONLY Android guard; a7b proves that.
    expect(loadExpo().android.blockedPermissions).toContain(RECORD_AUDIO);
  });

  it('a3a [FLIPPED by U4a R2] expo-camera entry: microphonePermission is the honest purpose string (was false)', () => {
    // Session 69 U4a (EXPO-07): the installed expo-camera binary still links
    // the AVCaptureDevice audio API (expo-camera/ios/Common/
    // CameraPermissionsRequester.swift:106-113), so the build ships a purpose
    // string instead of deleting the key. Both plugins carry the SAME string
    // (spec review Q1 option a), so the iOS output is order-independent (a8, u3).
    expect(pluginOptions(loadExpo(), 'expo-camera')?.microphonePermission).toBe(MIC_PURPOSE);
  });

  it('a3b [SELF-DOCUMENTING PIN — ruling R4] expo-camera entry: recordAudioAndroid === false', () => {
    // expo-camera/plugin/build/withCamera.js:7 defaults recordAudioAndroid to
    // true and :15-19 then REQUESTS RECORD_AUDIO. With the image-picker opt-out
    // (and blockedPermissions) in place the permission is blocked regardless,
    // so NO assertion in this suite reddens when this option is removed
    // (mutation M4 is identical to the full fix on every axis). It is kept so
    // the camera entry is self-describing if image-picker is ever removed.
    expect(pluginOptions(loadExpo(), 'expo-camera')?.recordAudioAndroid).toBe(false);
  });

  it('a4 [FLIPPED by U4a R2] expo-image-picker entry: microphonePermission is the honest purpose string (was false)', () => {
    // NOT cameraPermission:false — withImagePicker.js:41 would then BLOCK
    // android.permission.CAMERA, which the app needs (a5 / a7 pin CAMERA).
    // Consequence of the string (withImagePicker.js:34-36 adds RECORD_AUDIO for
    // any value other than the literal false; :39-42 blocks only on false):
    // android.blockedPermissions (a2) becomes the only Android guard — a7b.
    expect(pluginOptions(loadExpo(), 'expo-image-picker')?.microphonePermission).toBe(MIC_PURPOSE);
  });

  it('a5 [PRESERVE] CAMERA is requested and both purpose strings are unchanged', () => {
    const expo = loadExpo();
    expect(expo.android.permissions).toContain(CAMERA);
    expect(pluginOptions(expo, 'expo-camera')?.cameraPermission).toBe(CAMERA_PURPOSE);
    expect(pluginOptions(expo, 'expo-image-picker')?.photosPermission).toBe(PHOTOS_PURPOSE);
  });

  it('a6 [FLIPPED by U4a R2] executed plugins: Info.plist NSMicrophoneUsageDescription is the honest string (was absent); camera + photos strings intact', async () => {
    const { plist } = await compile(loadExpo());
    expect(plist.NSCameraUsageDescription).toBe(CAMERA_PURPOSE);
    expect(plist.NSPhotoLibraryUsageDescription).toBe(PHOTOS_PURPOSE);
    expect(plist.NSMicrophoneUsageDescription).toBe(MIC_PURPOSE);
  });

  it('a7 executed plugins: RECORD_AUDIO appears ONLY as a tools:node="remove" block; CAMERA is a plain request', async () => {
    const { usesPermission } = await compile(loadExpo());
    expect(usesPermission).toContainEqual({ 'android:name': CAMERA });
    expectRecordAudioOnlyBlocked(usesPermission);
  });

  it('a7b [FLIPPED by U4a R2 — spec review Q1(a)] with android.blockedPermissions DELETED, RECORD_AUDIO becomes a plain request: blockedPermissions is the single load-bearing Android guard', async () => {
    // Before U4a the picker's microphonePermission:false emitted its own
    // tools:node="remove" (withImagePicker.js:39-42), so the two levers were
    // mutually redundant and this test isolated the plugin lever. With the
    // honest string on the picker, :34-36 ADDS RECORD_AUDIO and nothing on the
    // plugin side blocks it (spec review correction 3). a2 pins the guard; this
    // test proves it is the only one, so deleting it must surface the request.
    const expo = clone(loadExpo());
    delete expo.android.blockedPermissions;
    const { usesPermission } = await compile(expo);
    expect(usesPermission).toContainEqual({ 'android:name': CAMERA });
    expect(usesPermission.filter((p) => p['android:name'] === RECORD_AUDIO)).toEqual([
      { 'android:name': RECORD_AUDIO },
    ]);
  });

  it('a8 executed output is plugin-ORDER independent (half-fixes C/D are order-dependent)', async () => {
    const expo = loadExpo();
    const pick = (c: Compiled) => ({
      mic: c.plist.NSMicrophoneUsageDescription,
      usesPermission: c.usesPermission,
    });
    const forward = pick(await compile(expo, FORWARD));
    const reversed = pick(await compile(expo, REVERSED));
    expect(reversed).toEqual(forward);
  });
});

// ===========================================================================
// (b) launcher art — MB-SAFE-HYGIENE-01
// ===========================================================================
describe('W3-7 (b) launcher art', () => {
  // SHA-256s recorded on 2026-05-24 (bundle-d-followups ICN-0001; re-measured
  // at b63a8368). Ruling R13: this is the repo's RECORD, not a hash derivable
  // here — no Expo template PNG exists in node_modules. The self-contained
  // evidence that the art is placeholder is splash-icon.png ===
  // adaptive-icon.png byte-for-byte.
  const RECORDED_2026_05_24 = {
    icon: '74c64047eb557b1341bba7a2831eedde9ddb705e6451a9ad9f5552bf558f13de',
    splashAndAdaptive: '5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8',
  };
  // The Expo template favicon (48x48 grey+alpha, interlaced) as committed at
  // base 94c097cd — never part of RECORDED_2026_05_24; pinned by b6.
  const RECORDED_BASE_94C097CD = {
    favicon: '24272cdaeff82cc5facdaccd982a6f05b60c4504704bbf94c19a6388659880bb',
  };
  const sha256Of = (bytes: Uint8Array): string => crypto.createHash('sha256').update(bytes).digest('hex');
  const assetBytes = (file: string): Buffer => fs.readFileSync(path.join(APP, 'assets', file));
  const sha256 = (file: string): string => sha256Of(assetBytes(file));

  // Session 70 U4b (spec R1/R2): the art is rendered from docs/brand/myez-icon-master-2048.png by scripts/render_myez_icons.py.
  const ICON_ART_SUPPLIED = true;
  const itArt = ICON_ART_SUPPLIED ? it : it.skip;

  itArt('b1 icon.png differs from the SHA-256 recorded on 2026-05-24', () => {
    expect(sha256('icon.png')).not.toBe(RECORDED_2026_05_24.icon);
  });

  itArt('b2 splash-icon.png and adaptive-icon.png differ from the SHA-256 recorded on 2026-05-24 and from each other', () => {
    expect(sha256('splash-icon.png')).not.toBe(RECORDED_2026_05_24.splashAndAdaptive);
    expect(sha256('adaptive-icon.png')).not.toBe(RECORDED_2026_05_24.splashAndAdaptive);
    // The reproducible placeholder signal: no custom render is byte-identical.
    expect(sha256('splash-icon.png')).not.toBe(sha256('adaptive-icon.png'));
  });

  it('b3 [PRESERVE] the three launcher PNGs exist, are PNGs, and app.json points at them', () => {
    const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47]);
    for (const file of ['icon.png', 'splash-icon.png', 'adaptive-icon.png']) {
      const bytes = fs.readFileSync(path.join(APP, 'assets', file));
      expect(bytes.subarray(0, 4).equals(PNG_SIGNATURE)).toBe(true);
    }
    const expo = loadExpo();
    expect(expo.icon).toBe('./assets/icon.png');
    expect(expo.splash.image).toBe('./assets/splash-icon.png');
    expect(expo.android.adaptiveIcon.foregroundImage).toBe('./assets/adaptive-icon.png');
  });

  // ---- Session 70 U4b: the MYEZ art, pinned by PNG header and PIXELS --------
  // Pixel pins run through __tests__/helpers/pngDecode.ts (spec R9). The IHDR
  // is asserted BEFORE any decode so a wrong colour type names itself instead
  // of surfacing as a decoder error. Thresholds come from the prototype render
  // (spec §4.4); the exact committed bytes are pinned by the manifest (b7).
  const BRAND_DIR = path.join(REPO, 'docs', 'brand');
  const MASTER_PNG = path.join(BRAND_DIR, 'myez-icon-master-2048.png');
  const MANIFEST = path.join(BRAND_DIR, 'myez-icons.manifest.json');
  const RENDERER = path.join(REPO, 'scripts', 'render_myez_icons.py');
  const MASTER_SHA256 = '70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41';
  const CANVAS = 1024;
  // Android adaptive icon: the 66 dp safe circle on the 108 dp canvas.
  const SAFE_RADIUS = (CANVAS * 33) / 108;
  const ihdr = (width: number, height: number, colorType: 2 | 6): PngIhdr => ({
    width,
    height,
    bitDepth: 8,
    colorType,
    interlace: 0,
  });
  const chunkTypes = (bytes: Buffer): string[] => pngChunks(bytes).map((c) => c.type);
  const isEmerald = (r: number, g: number, b: number): boolean => g > r + 60 && g > b + 20;
  const isNearBlack = (r: number, g: number, b: number): boolean => Math.max(r, g, b) < 40;
  const px = (img: DecodedPng, x: number, y: number): number[] => {
    const i = (y * img.width + x) * img.channels;
    return Array.from(img.pixels.subarray(i, i + img.channels));
  };
  const corners = (img: DecodedPng): number[][] => [
    px(img, 0, 0),
    px(img, img.width - 1, 0),
    px(img, 0, img.height - 1),
    px(img, img.width - 1, img.height - 1),
  ];
  /** Width of the bounding box of every pixel with alpha > 0 (RGBA only). */
  const alphaBboxWidth = (img: DecodedPng): number => {
    expect(img.channels).toBe(4);
    let minX = img.width;
    let maxX = -1;
    for (let y = 0; y < img.height; y++) {
      for (let x = 0; x < img.width; x++) {
        if (img.pixels[(y * img.width + x) * 4 + 3] > 0) {
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
        }
      }
    }
    expect(maxX).toBeGreaterThanOrEqual(0);
    return maxX - minX + 1;
  };

  it('b4 icon.png is a 1024x1024 8-bit truecolour PNG with no alpha channel and no tRNS', () => {
    // The master's transparent corners are flattened onto the tile white
    // (spec R3): iOS applies its own mask, and App Store Connect wants opaque.
    const bytes = assetBytes('icon.png');
    expect(readIhdr(bytes)).toEqual(ihdr(CANVAS, CANVAS, 2));
    expect(chunkTypes(bytes)).not.toContain('tRNS');
  });

  it('b5 adaptive-icon.png and splash-icon.png are 1024x1024 8-bit RGBA PNGs', () => {
    for (const file of ['adaptive-icon.png', 'splash-icon.png']) {
      expect({ file, ihdr: readIhdr(assetBytes(file)) }).toEqual({ file, ihdr: ihdr(CANVAS, CANVAS, 6) });
    }
  });

  it('b6 favicon.png (web.favicon) is a 48x48 8-bit RGBA PNG and differs from the favicon recorded at base 94c097cd', () => {
    const bytes = assetBytes('favicon.png');
    expect(readIhdr(bytes)).toEqual(ihdr(48, 48, 6));
    expect(sha256Of(bytes)).not.toBe(RECORDED_BASE_94C097CD.favicon);
  });

  it("b7 the four PNGs are the committed renderer's output (docs/brand/myez-icons.manifest.json)", () => {
    // spec R4 / §4.5: the manifest pins the committed bytes AND Pillow's
    // `Image.tobytes()` of each file — the latter is what the inline decoder
    // returns, so this cross-checks the decoder against Pillow on four real
    // adaptive-filtered files.
    expect({ manifest: MANIFEST, exists: fs.existsSync(MANIFEST) }).toEqual({ manifest: MANIFEST, exists: true });
    const manifest = readJson(MANIFEST);
    expect(manifest.renderer).toBe('scripts/render_myez_icons.py');
    expect(manifest.master.path).toBe('docs/brand/myez-icon-master-2048.png');
    expect(manifest.master.sha256).toBe(sha256Of(fs.readFileSync(MASTER_PNG)));
    const outputs = ['adaptive-icon.png', 'favicon.png', 'icon.png', 'splash-icon.png'];
    expect(Object.keys(manifest.outputs).sort()).toEqual(outputs.map((f) => `SmartCompareApp/assets/${f}`));
    for (const file of outputs) {
      const entry = manifest.outputs[`SmartCompareApp/assets/${file}`];
      const bytes = assetBytes(file);
      const header = readIhdr(bytes);
      const decoded = decodePng(bytes);
      expect({ file, sha256: sha256Of(bytes) }).toEqual({ file, sha256: entry.sha256 });
      expect({ file, pixels_sha256: sha256Of(decoded.pixels) }).toEqual({ file, pixels_sha256: entry.pixels_sha256 });
      expect({ file, width: decoded.width, height: decoded.height }).toEqual({
        file,
        width: entry.width,
        height: entry.height,
      });
      expect({ file, width: header.width, height: header.height }).toEqual({
        file,
        width: entry.width,
        height: entry.height,
      });
      // Pillow's mode <-> the PNG colour type <-> the decoder's channel count.
      expect({ file, mode: entry.mode, colorType: header.colorType, channels: decoded.channels }).toEqual(
        entry.mode === 'RGB'
          ? { file, mode: 'RGB', colorType: 2, channels: 3 }
          : { file, mode: 'RGBA', colorType: 6, channels: 4 },
      );
    }
  });

  it('b8 icon.png pixels: tile-white corners and the MYEZ mark (not the grey template)', () => {
    const bytes = assetBytes('icon.png');
    expect(readIhdr(bytes)).toEqual(ihdr(CANVAS, CANVAS, 2));
    const img = decodePng(bytes);
    expect(corners(img)).toEqual([
      [255, 255, 255],
      [255, 255, 255],
      [255, 255, 255],
      [255, 255, 255],
    ]);
    let emerald = 0;
    let nearBlack = 0;
    for (let i = 0; i < img.pixels.length; i += 3) {
      const r = img.pixels[i];
      const g = img.pixels[i + 1];
      const b = img.pixels[i + 2];
      if (isEmerald(r, g, b)) emerald++;
      if (isNearBlack(r, g, b)) nearBlack++;
    }
    // Prototype: 3,524 emerald (#10B981 dot) and 151,892 near-black (the
    // MY/EZ ink) pixels; the grey template has 0 of each (spec §1.15, §4.4).
    expect(emerald).toBeGreaterThanOrEqual(2000);
    expect(nearBlack).toBeGreaterThanOrEqual(100000);
  });

  it('b9 adaptive-icon.png pixels: transparent corners, every inked pixel inside the Android 66 dp safe circle', () => {
    const bytes = assetBytes('adaptive-icon.png');
    expect(readIhdr(bytes)).toEqual(ihdr(CANVAS, CANVAS, 6));
    const img = decodePng(bytes);
    expect(corners(img).map((c) => c[3])).toEqual([0, 0, 0, 0]);
    const centre = (CANVAS - 1) / 2; // 511.5 — distances between pixel centres
    let maxRadius = 0;
    let opaque = 0;
    let emeraldOpaque = 0;
    for (let y = 0; y < img.height; y++) {
      for (let x = 0; x < img.width; x++) {
        const i = (y * img.width + x) * 4;
        const a = img.pixels[i + 3];
        if (a === 0) continue;
        const d = Math.hypot(x - centre, y - centre);
        if (d > maxRadius) maxRadius = d;
        if (a >= 128) {
          opaque++;
          if (isEmerald(img.pixels[i], img.pixels[i + 1], img.pixels[i + 2])) emeraldOpaque++;
        }
      }
    }
    // Prototype: max radius 305.57 px (8 px inside the 312.89 px safe circle),
    // 77,320 px at alpha >= 128, 1,716 of them emerald (spec §4.4, §5).
    expect(maxRadius).toBeLessThanOrEqual(SAFE_RADIUS);
    expect(opaque).toBeGreaterThanOrEqual(40000);
    expect(emeraldOpaque).toBeGreaterThanOrEqual(1000);
  });

  it('b10 splash-icon.png pixels: transparent background, wordmark at ~30% of the canvas width, narrower than the adaptive mark', () => {
    const bytes = assetBytes('splash-icon.png');
    expect(readIhdr(bytes)).toEqual(ihdr(CANVAS, CANVAS, 6));
    const img = decodePng(bytes);
    expect(corners(img).map((c) => c[3])).toEqual([0, 0, 0, 0]);
    let transparent = 0;
    for (let i = 3; i < img.pixels.length; i += 4) if (img.pixels[i] === 0) transparent++;
    // Prototype: 95.2 % transparent; alpha bbox width 312 px = 30.5 % of the
    // canvas (spec §4.4) — drawn full-screen-width by the legacy iOS splash
    // path, that is 112–132 pt on 375–440 pt iPhones (spec §1.10, R3).
    expect(transparent / (img.width * img.height)).toBeGreaterThanOrEqual(0.9);
    const width = alphaBboxWidth(img);
    expect(width).toBeGreaterThanOrEqual(0.28 * CANVAS);
    expect(width).toBeLessThanOrEqual(0.33 * CANVAS);
    // The adaptive foreground fills the safe circle; the splash wordmark is
    // the smaller of the two renders (prototype 312 px vs 407 px).
    const adaptive = assetBytes('adaptive-icon.png');
    expect(readIhdr(adaptive)).toEqual(ihdr(CANVAS, CANVAS, 6));
    expect(width).toBeLessThan(alphaBboxWidth(decodePng(adaptive)));
  });

  it('b11 [PRESERVE] the white the transparent art is composited over', () => {
    // adaptive-icon.png and splash-icon.png carry the ink as colour-to-alpha
    // over a REMOVED white tile (spec §4.3 step 3, §7): they are correct only
    // over #ffffff, which is what both app.json fields already say.
    const expo = loadExpo();
    expect(expo.android.adaptiveIcon.backgroundColor).toBe('#ffffff');
    expect(expo.splash.backgroundColor).toBe('#ffffff');
    expect(expo.splash.resizeMode).toBe('contain');
    expect(expo.web.favicon).toBe('./assets/favicon.png');
  });

  it('b12 [HARNESS] the inline PNG decoder round-trips all five filter types and refuses what it cannot read', () => {
    // Proves the harness BEFORE any art exists (spec review correction 13):
    // a PNG is hand-assembled here — forward-filtered rows, zlib.deflateSync,
    // raw chunks with a junk CRC (the decoder skips it, R9) — and must decode
    // to the source pixels exactly.
    const chunk = (type: string, data: Buffer): Buffer => {
      const length = Buffer.alloc(4);
      length.writeUInt32BE(data.length, 0);
      return Buffer.concat([length, Buffer.from(type, 'latin1'), data, Buffer.from([0xde, 0xad, 0xbe, 0xef])]);
    };
    const ihdrChunk = (width: number, height: number, bitDepth: number, colorType: number, interlace: number): Buffer => {
      const d = Buffer.alloc(13);
      d.writeUInt32BE(width, 0);
      d.writeUInt32BE(height, 4);
      d[8] = bitDepth;
      d[9] = colorType;
      d[10] = 0; // compression
      d[11] = 0; // filter method
      d[12] = interlace;
      return chunk('IHDR', d);
    };
    const paeth = (a: number, b: number, c: number): number => {
      const p = a + b - c;
      const pa = Math.abs(p - a);
      const pb = Math.abs(p - b);
      const pc = Math.abs(p - c);
      if (pa <= pb && pa <= pc) return a;
      return pb <= pc ? b : c;
    };
    /** Forward-filters `pixels` (row-major, `channels` bytes each) as an encoder would, one filter type per row. */
    const filterRows = (pixels: Uint8Array, width: number, height: number, channels: number, filters: number[]): Buffer => {
      const stride = width * channels;
      const out = Buffer.alloc(height * (stride + 1));
      for (let y = 0; y < height; y++) {
        const f = filters[y % filters.length];
        out[y * (stride + 1)] = f;
        for (let x = 0; x < stride; x++) {
          const raw = pixels[y * stride + x];
          const a = x >= channels ? pixels[y * stride + x - channels] : 0;
          const b = y > 0 ? pixels[(y - 1) * stride + x] : 0;
          const c = x >= channels && y > 0 ? pixels[(y - 1) * stride + x - channels] : 0;
          const predictors = [0, a, b, (a + b) >> 1, paeth(a, b, c)];
          out[y * (stride + 1) + 1 + x] = (raw - predictors[f]) & 0xff;
        }
      }
      return out;
    };
    const png = (width: number, height: number, colorType: number, bitDepth: number, interlace: number, idat: Buffer[]): Buffer =>
      Buffer.concat([
        PNG_SIGNATURE,
        ihdrChunk(width, height, bitDepth, colorType, interlace),
        ...idat.map((d) => chunk('IDAT', d)),
        chunk('IEND', Buffer.alloc(0)),
      ]);

    // 3 x 5 RGBA; rows filtered None / Sub / Up / Average / Paeth in turn; the
    // deflate stream split across TWO IDAT chunks (the committed master carries
    // 37 — concatenation is load-bearing, spec review correction 1).
    const width = 3;
    const height = 5;
    const channels = 4;
    const source = new Uint8Array(width * height * channels);
    for (let i = 0; i < source.length; i++) source[i] = (i * i * 7 + i * 29 + 5) & 0xff;
    const deflated = zlib.deflateSync(filterRows(source, width, height, channels, [0, 1, 2, 3, 4]));
    const split = Math.floor(deflated.length / 2);
    const rgba = png(width, height, 6, 8, 0, [deflated.subarray(0, split), deflated.subarray(split)]);
    expect(pngChunks(rgba).map((c) => c.type)).toEqual(['IHDR', 'IDAT', 'IDAT', 'IEND']);
    expect(readIhdr(rgba)).toEqual(ihdr(width, height, 6));
    const decoded = decodePng(rgba);
    expect({ width: decoded.width, height: decoded.height, channels: decoded.channels }).toEqual({
      width,
      height,
      channels,
    });
    expect(Array.from(decoded.pixels)).toEqual(Array.from(source));

    // 1 x 1 RGB (three channels, bpp 3).
    const rgb = png(1, 1, 2, 8, 0, [zlib.deflateSync(Buffer.from([0, 10, 200, 30]))]);
    expect(decodePng(rgb)).toEqual({ width: 1, height: 1, channels: 3, pixels: new Uint8Array([10, 200, 30]) });

    // Refused shapes are rejected on the IHDR, before any IDAT is inflated.
    const idat = [zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0]))];
    expect(() => decodePng(png(1, 1, 3, 8, 0, idat))).toThrow(/pngDecode: unsupported colorType 3/);
    expect(() => decodePng(png(1, 1, 6, 16, 0, idat))).toThrow(/pngDecode: unsupported bitDepth 16/);
    expect(() => decodePng(png(1, 1, 6, 8, 1, idat))).toThrow(/pngDecode: unsupported interlace 1/);
    expect(() => readIhdr(Buffer.from('not a png at all', 'latin1'))).toThrow(/pngDecode: bad signature/);
  });

  it('b13 the MYEZ master is committed with its recorded SHA-256', () => {
    // spec R1: a byte copy of Ahmed's original MYEZ-icon-white-2048.png
    // (decision D4); 2048x2048 RGBA, the full-bleed white tile with the mark.
    expect({ master: MASTER_PNG, exists: fs.existsSync(MASTER_PNG) }).toEqual({ master: MASTER_PNG, exists: true });
    const bytes = fs.readFileSync(MASTER_PNG);
    expect(sha256Of(bytes)).toBe(MASTER_SHA256);
    expect(readIhdr(bytes)).toEqual(ihdr(2048, 2048, 6));
  });

  it('b14 [SOURCE-SHAPE] scripts/render_myez_icons.py exists, pins the master SHA-256 and writes the four launcher files', () => {
    // spec R2 / ruling RQ6: the renderer lives under scripts/ (CI ruff + black
    // cover it) and is the ONLY writer of the four assets — never hand-edited.
    expect({ renderer: RENDERER, exists: fs.existsSync(RENDERER) }).toEqual({ renderer: RENDERER, exists: true });
    const text = fs.readFileSync(RENDERER, 'utf8');
    const needles = [
      MASTER_SHA256,
      'docs/brand/myez-icon-master-2048.png',
      'icon.png',
      'adaptive-icon.png',
      'splash-icon.png',
      'favicon.png',
    ];
    for (const needle of needles) {
      expect({ needle, found: text.includes(needle) }).toEqual({ needle, found: true });
    }
  });
});

// ===========================================================================
// (c) iOS privacy manifest — MB-TWO-LEVER-RELEASE-08
// ===========================================================================
describe('W3-7 (c) privacy manifest declares collected data types', () => {
  const INVENTORY_DOC = path.join(REPO, 'docs', 'privacy-data-inventory.md');
  const ENTRY_KEYS = [
    'NSPrivacyCollectedDataType',
    'NSPrivacyCollectedDataTypeLinked',
    'NSPrivacyCollectedDataTypePurposes',
    'NSPrivacyCollectedDataTypeTracking',
  ];
  const ACCESSED_API_TYPES = [
    {
      NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategoryUserDefaults',
      NSPrivacyAccessedAPITypeReasons: ['CA92.1'],
    },
    {
      NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategoryFileTimestamp',
      NSPrivacyAccessedAPITypeReasons: ['C617.1'],
    },
    {
      NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategorySystemBootTime',
      NSPrivacyAccessedAPITypeReasons: ['35F9.1'],
    },
    {
      NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategoryDiskSpace',
      NSPrivacyAccessedAPITypeReasons: ['E174.1'],
    },
  ];
  const byType = (a: AnyConfig, b: AnyConfig) =>
    String(a.NSPrivacyCollectedDataType).localeCompare(String(b.NSPrivacyCollectedDataType));
  const typeSet = (arr: AnyConfig[]) => arr.map((e) => e.NSPrivacyCollectedDataType).sort();

  // Ruling R16: no assertion hard-codes an entry count. Adding or removing a
  // row edits exactly two places — app.json and the inventory doc.
  // Deliberately NOT pinned (R9/R16): WHICH rows exist and each row's Linked /
  // purpose VALUES. c1-c4 pin shape, consistency and doc==manifest; a change
  // made identically in both files (e.g. flipping EmailAddress Linked, or
  // dropping the DeviceID row) passes by design. The content is a human
  // review gate (Ahmed/legal, against the file:line evidence in the doc).

  it('c1 ios.privacyManifests.NSPrivacyCollectedDataTypes is a non-empty array', () => {
    const types = loadExpo().ios.privacyManifests.NSPrivacyCollectedDataTypes;
    expect(Array.isArray(types)).toBe(true);
    expect(types.length).toBeGreaterThan(0);
  });

  it('c2 every entry is well-formed, untracked (NSPrivacyTracking is false, no tracking domains), and type ids are unique', () => {
    const manifest = loadExpo().ios.privacyManifests;
    const types: AnyConfig[] | undefined = manifest.NSPrivacyCollectedDataTypes;
    expect(Array.isArray(types) && types.length > 0).toBe(true);
    expect(manifest.NSPrivacyTracking).toBe(false);
    // Tracking domains are only meaningful when NSPrivacyTracking is true; a
    // non-empty list beside `false` is a self-contradicting manifest.
    expect(manifest.NSPrivacyTrackingDomains ?? []).toEqual([]);
    for (const entry of types as AnyConfig[]) {
      expect(Object.keys(entry).sort()).toEqual(ENTRY_KEYS);
      expect(entry.NSPrivacyCollectedDataType).toMatch(/^NSPrivacyCollectedDataType[A-Z][A-Za-z]+$/);
      expect(typeof entry.NSPrivacyCollectedDataTypeLinked).toBe('boolean');
      expect(entry.NSPrivacyCollectedDataTypeTracking).toBe(false);
      expect(Array.isArray(entry.NSPrivacyCollectedDataTypePurposes)).toBe(true);
      expect(entry.NSPrivacyCollectedDataTypePurposes.length).toBeGreaterThan(0);
      for (const purpose of entry.NSPrivacyCollectedDataTypePurposes) {
        expect(purpose).toMatch(/^NSPrivacyCollectedDataTypePurpose[A-Z][A-Za-z]+$/);
      }
    }
    const ids = typeSet(types as AnyConfig[]);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('c3 docs/privacy-data-inventory.md exists and its first ```json fence deep-equals the manifest array', () => {
    expect(fs.existsSync(INVENTORY_DOC)).toBe(true);
    const md = fs.readFileSync(INVENTORY_DOC, 'utf8');
    const fence = md.match(/```json\s*\r?\n([\s\S]*?)\r?\n```/);
    expect(fence).not.toBeNull();
    const fromDoc: AnyConfig[] = JSON.parse((fence as RegExpMatchArray)[1]);
    const fromApp: AnyConfig[] = loadExpo().ios.privacyManifests.NSPrivacyCollectedDataTypes;
    expect(Array.isArray(fromDoc)).toBe(true);
    expect([...fromDoc].sort(byType)).toEqual([...(fromApp ?? [])].sort(byType));
  });

  it('c4 [KEY-NAME GUARD, not semantic validation — ruling R9] installed mergePrivacyInfo carries the types, tracking:false and the four accessed-API entries', () => {
    // mergePrivacyInfo({}, x) is the identity map over x's collected types
    // (PrivacyInfo.js:96, :112-119) when ids are unique (c2). This reddens on
    // a misspelled/misnested NSPrivacyCollectedDataTypes key or an altered
    // accessed-API reason; it does NOT redden on any change to the data-type
    // or purpose identifier STRINGS — those are unverifiable here (every
    // shipped PrivacyInfo.xcprivacy in node_modules has an empty array) and
    // stay an Ahmed/legal review gate before merge.
    const { IOSConfig } = reqFromApp('expo/config-plugins');
    const privacyManifests = loadExpo().ios.privacyManifests;
    const merged = IOSConfig.PrivacyInfo.mergePrivacyInfo({}, privacyManifests);
    // Preserve half (GREEN today): tracking + the committed four accessed-API entries.
    expect(merged.NSPrivacyTracking).toBe(false);
    expect(merged.NSPrivacyAccessedAPITypes).toEqual(ACCESSED_API_TYPES);
    // Collected-types half.
    expect(merged.NSPrivacyCollectedDataTypes.length).toBeGreaterThan(0);
    expect(typeSet(merged.NSPrivacyCollectedDataTypes)).toEqual(
      typeSet(privacyManifests.NSPrivacyCollectedDataTypes ?? []),
    );
    if (fs.existsSync(INVENTORY_DOC)) {
      const fence = fs.readFileSync(INVENTORY_DOC, 'utf8').match(/```json\s*\r?\n([\s\S]*?)\r?\n```/);
      expect(fence).not.toBeNull();
      expect(typeSet(merged.NSPrivacyCollectedDataTypes)).toEqual(
        typeSet(JSON.parse((fence as RegExpMatchArray)[1])),
      );
    }
  });

  it('c5 every numbered row of the doc\'s human table equals the JSON block entry of the same type (type, Linked, Tracking, Purposes); the JSON block equals app.json', () => {
    // The App Store Connect nutrition labels are filled from the TABLE (doc
    // §2), so a table that drifts from the manifest must redden even when the
    // JSON block and app.json still agree. Rows are the `| <n> |` lines of the
    // "## Collected data types" section; cells split on unescaped `|` (row 7
    // carries `\|` inside a code span). Linked/Tracking read the leading
    // true|false (a parenthetical note may follow); Purposes is the
    // comma-separated list with parentheticals removed. Purpose ORDER is not
    // compared (both sides sorted); membership is.
    const md = fs.readFileSync(INVENTORY_DOC, 'utf8');
    const start = md.indexOf('\n## Collected data types');
    expect(start).toBeGreaterThanOrEqual(0);
    const rest = md.slice(start + 1);
    const end = rest.indexOf('\n## ');
    const section = end === -1 ? rest : rest.slice(0, end);
    const lines = section.split(/\r?\n/).filter((l) => /^\|\s*\d+\s*\|/.test(l));
    expect(lines.length).toBeGreaterThan(0);

    const norm = (e: AnyConfig) => ({
      NSPrivacyCollectedDataType: e.NSPrivacyCollectedDataType,
      NSPrivacyCollectedDataTypeLinked: e.NSPrivacyCollectedDataTypeLinked,
      NSPrivacyCollectedDataTypeTracking: e.NSPrivacyCollectedDataTypeTracking,
      NSPrivacyCollectedDataTypePurposes: [...e.NSPrivacyCollectedDataTypePurposes].sort(),
    });
    const bool = (cell: string, line: string): boolean => {
      const m = cell.match(/^(true|false)\b/);
      expect({ line, cell, parsed: m !== null }).toEqual({ line, cell, parsed: true });
      return (m as RegExpMatchArray)[1] === 'true';
    };
    const fromTable = lines.map((line) => {
      const cells = line.split(/(?<!\\)\|/).slice(1, -1).map((c) => c.trim());
      expect({ line, cells: cells.length }).toEqual({ line, cells: 6 });
      const type = cells[1].match(/^`([A-Z][A-Za-z]+)`$/);
      expect({ line, type: type !== null }).toEqual({ line, type: true });
      const purposes = cells[5]
        .replace(/\([^)]*\)/g, '')
        .split(',')
        .map((p) => p.trim())
        .filter((p) => p.length > 0);
      for (const p of purposes) expect({ line, p }).toEqual({ line, p: expect.stringMatching(/^[A-Z][A-Za-z]+$/) });
      return norm({
        NSPrivacyCollectedDataType: `NSPrivacyCollectedDataType${(type as RegExpMatchArray)[1]}`,
        NSPrivacyCollectedDataTypeLinked: bool(cells[3], line),
        NSPrivacyCollectedDataTypeTracking: bool(cells[4], line),
        NSPrivacyCollectedDataTypePurposes: purposes.map((p) => `NSPrivacyCollectedDataTypePurpose${p}`),
      });
    });

    const fence = md.match(/```json\s*\r?\n([\s\S]*?)\r?\n```/);
    expect(fence).not.toBeNull();
    const fromDoc: AnyConfig[] = JSON.parse((fence as RegExpMatchArray)[1]);
    const fromApp: AnyConfig[] = loadExpo().ios.privacyManifests.NSPrivacyCollectedDataTypes ?? [];
    expect([...fromTable].sort(byType)).toEqual(fromDoc.map(norm).sort(byType));
    expect([...fromDoc].sort(byType)).toEqual([...fromApp].sort(byType));
  });
});

// ===========================================================================
// (d) every runtime dependency is justified — MB-SAFE-HYGIENE-06
// ===========================================================================
describe('W3-7 (d) runtime dependencies are imported, justified, or pending removal', () => {
  /**
   * Ruling R7 — BINDING: exactly these three fields. A devDependencies edge of
   * an installed library is that library's own test tooling and is never a
   * reason to ship a native module. Three devDependency decoys existed for
   * react-native-gesture-handler (measured 2026-09-11 over 898 installed
   * package.json files, before session 70 U4b removed the package):
   * @testing-library/react-native@13.3.3, react-native-reanimated@4.1.7 and
   * react-native-screens@4.16.0, each :: devDependencies. Adding
   * 'devDependencies' here would have justified that orphan and silently
   * deleted this unit's headline test — and would do the same for the next one.
   */
  const EDGE_FIELDS = ['dependencies', 'peerDependencies', 'optionalDependencies'] as const;

  /**
   * Ruling R11 — the import scan covers app source ONLY: src/**\/*.{ts,tsx}
   * minus src/**\/__tests__, src/**\/__mocks__ and *.test.* / *.spec.* files,
   * plus App.tsx and index.ts (see sourceFiles()). MB-SAFE-HYGIENE-06's
   * wording includes __tests__; an import inside a test suite — top-level
   * __tests__/ OR a co-located src/**\/__tests__/ — is not a reason to ship a
   * native module into every EAS build. Measured: the outcome is identical
   * either way (react-native-gesture-handler had 0 test imports; the only
   * zero-src dep with a test import is babel-preset-expo, already justified;
   * excluding the 9 files under src/**\/__tests__ removes no dependency from
   * the imported set — 36 of 43 imported with and without them).
   *
   * Ruling R10 — package.json has 43 runtime `dependencies` + 12
   * `devDependencies` = the finding's 55. Only the 43 ship/autolink; do not
   * widen the input set.
   */
  const JUSTIFIED: Record<string, { reason: string; holds: () => boolean }> = {
    'babel-preset-expo': {
      reason: 'babel.config.js:206 presets: [\'babel-preset-expo\']',
      holds: () => /presets:\s*\[\s*['"]babel-preset-expo['"]/.test(
        fs.readFileSync(path.join(APP, 'babel.config.js'), 'utf8'),
      ),
    },
    'expo-build-properties': {
      reason: 'app.json:118 plugins entry',
      holds: () => pluginOptions(loadExpo(), 'expo-build-properties') !== undefined,
    },
    'expo-dev-client': {
      // If the development profile is ever dropped this reason becomes false
      // and the dependency surfaces as unjustified.
      reason: 'eas.json:8 build.development.developmentClient: true',
      holds: () => readJson(path.join(APP, 'eas.json')).build?.development?.developmentClient === true,
    },
  };

  /**
   * Bookkeeping allowlist (ruling R8). An entry here is a HUMAN toolchain step
   * (npm uninstall + package-lock.json commit), not code. d2 goes RED the
   * moment the package is uninstalled until the entry is deleted; d4 goes RED
   * if the package is ever imported.
   */
  const PENDING_REMOVAL: Record<string, string> = {
    // react-native-gesture-handler was removed in session 70 U4b (npm uninstall + lock).
  };

  // App source only (ruling R11): src/** minus every `__tests__` / `__mocks__`
  // directory and every *.test.* / *.spec.* file, plus App.tsx and index.ts.
  // At b63a8368 this is 142 files; the 9 files it leaves out all sit under
  // src/{components,services,utils}/__tests__.
  // Every helper below takes a project `root` (default: the app) so the
  // synthetic fixture in os.tmpdir() runs through the SAME code as the real
  // tree — that is what makes d1/d2/d4's red paths measurable without editing
  // package.json, node_modules or src.
  function sourceFiles(root: string = APP): string[] {
    const out: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const f = path.join(dir, e.name);
        if (e.isDirectory()) {
          if (e.name !== '__tests__' && e.name !== '__mocks__') walk(f);
        } else if (/\.(ts|tsx)$/.test(e.name) && !/\.(test|spec)\.tsx?$/.test(e.name)) {
          out.push(f);
        }
      }
    };
    walk(path.join(root, 'src'));
    for (const f of ['App.tsx', 'index.ts']) out.push(path.join(root, f));
    return out;
  }

  /**
   * Module specifiers read from the TypeScript AST (installed `typescript`),
   * never by a regex over raw text: comments and string contents are not
   * imports, so `// see from 'react-native-gesture-handler' docs` justifies
   * nothing and reddens nothing. Covered forms: `import … from 'x'`,
   * side-effect `import 'x'`, `export … from 'x'` (incl. `export * from`),
   * `import x = require('x')`, `require('x')` and `import('x')` anywhere in the
   * file. A computed specifier (`require(name)`) is not visible to this scan.
   */
  function moduleSpecifiers(file: string): string[] {
    const source = ts.createSourceFile(
      file,
      fs.readFileSync(file, 'utf8'),
      ts.ScriptTarget.Latest,
      false,
      file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );
    const out: string[] = [];
    const visit = (node: ts.Node): void => {
      if (
        (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
        node.moduleSpecifier !== undefined &&
        ts.isStringLiteral(node.moduleSpecifier)
      ) {
        out.push(node.moduleSpecifier.text);
      } else if (
        ts.isImportEqualsDeclaration(node) &&
        ts.isExternalModuleReference(node.moduleReference) &&
        ts.isStringLiteral(node.moduleReference.expression)
      ) {
        out.push(node.moduleReference.expression.text);
      } else if (
        ts.isCallExpression(node) &&
        node.arguments.length >= 1 &&
        ts.isStringLiteralLike(node.arguments[0]) &&
        (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(node.expression) && node.expression.text === 'require'))
      ) {
        out.push(node.arguments[0].text);
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
    return out;
  }

  function importedDeps(deps: string[], root: string = APP): Set<string> {
    const specifiers = new Set(sourceFiles(root).flatMap(moduleSpecifiers));
    const imported = new Set<string>();
    for (const dep of deps) {
      for (const s of specifiers) {
        if (s === dep || s.startsWith(`${dep}/`)) imported.add(dep);
      }
    }
    return imported;
  }

  function installedManifest(name: string, root: string = APP): AnyConfig | undefined {
    const p = path.join(root, 'node_modules', ...name.split('/'), 'package.json');
    return fs.existsSync(p) ? readJson(p) : undefined;
  }

  function declaredBy(owners: Iterable<string>, dep: string, root: string = APP): string[] {
    const hits: string[] = [];
    for (const owner of owners) {
      if (owner === dep) continue;
      const m = installedManifest(owner, root);
      if (!m) continue;
      for (const field of EDGE_FIELDS) {
        if (m[field] && m[field][dep] !== undefined) hits.push(`${owner}:${field}`);
      }
    }
    return hits;
  }

  type Justified = Record<string, { reason: string; holds: () => boolean }>;

  // d1 / d2 / d4 check bodies, run on the real app AND on the fixture below.
  function expectUnjustifiedEqualsPending(
    root: string,
    pkg: AnyConfig,
    pending: Record<string, string>,
    justified: Justified,
  ): void {
    const deps = Object.keys(pkg.dependencies);
    const imported = importedDeps(deps, root);
    const unjustified: string[] = [];
    for (const dep of deps) {
      if (imported.has(dep)) continue;
      if (justified[dep]) {
        expect({ dep, holds: justified[dep].holds() }).toEqual({ dep, holds: true });
        continue;
      }
      // Peer/dependency edge from an IMPORTED dependency's installed manifest
      // (measured: react-native-safe-area-context + react-native-screens <-
      // @react-navigation/native-stack & bottom-tabs; react-native-worklets <-
      // react-native-reanimated).
      if (declaredBy(imported, dep, root).length > 0) continue;
      unjustified.push(dep);
    }
    // PENDING_REMOVAL is NOT a skip-list: the otherwise-unjustified set must
    // EQUAL its keys, so a stale entry (package now justified) and a new
    // orphan both redden this test.
    expect(unjustified.sort()).toEqual(Object.keys(pending).sort());
  }

  function expectPendingDeclared(pkg: AnyConfig, pending: Record<string, string>): void {
    const declared = pkg.dependencies;
    for (const dep of Object.keys(pending)) expect(declared).toHaveProperty([dep]);
  }

  function expectPendingUnused(root: string, pkg: AnyConfig, pending: Record<string, string>): void {
    const deps = Object.keys(pkg.dependencies);
    const names = Object.keys(pending);
    const imported = importedDeps(names, root);
    for (const dep of names) {
      expect({ dep, imported: imported.has(dep) }).toEqual({ dep, imported: false });
      expect({ dep, declaredBy: declaredBy(deps, dep, root) }).toEqual({ dep, declaredBy: [] });
    }
  }

  /**
   * Synthetic project (test-owned, under os.tmpdir(); never the real
   * package.json). It mirrors the real orphan's shape: `fx-used` is imported
   * by app source and peers on `fx-peer`; `fx-orphan` is named only in a
   * comment, a string literal and three test-only imports (a *.test.ts file
   * under __tests__, a NON-test-named helper under __tests__, and a
   * co-located src/*.test.ts — so each half of ruling R11's exclusion is
   * load-bearing on its own), and its only installed edge is a
   * devDependencies decoy (ruling R7) — so it has zero app imports and no
   * justification. Removed file-by-file / dir-by-dir in afterAll (no
   * recursive delete).
   */
  const FIXTURE_FILES: Record<string, string> = {
    'package.json': JSON.stringify({
      name: 'w37-fixture',
      dependencies: {
        'fx-used': '1.0.0',
        'fx-peer': '1.0.0',
        'fx-orphan': '1.0.0',
        // Shares the orphan's name as a PREFIX and IS imported: only a
        // package-name-boundary match (`s === dep || s.startsWith(dep + '/')`)
        // keeps `fx-orphan` unjustified; a substring match would count this
        // import for it and d1/d4 would go green on a real orphan.
        'fx-orphan-extra': '1.0.0',
      },
    }),
    'src/app.ts':
      "import used from 'fx-used';\nimport extra from 'fx-orphan-extra';\n// import 'fx-orphan' — a comment is not an import\nexport const label = 'fx-orphan';\nexport { extra };\nexport default used;\n",
    'src/__tests__/app.test.ts': "import 'fx-orphan';\n",
    'src/__tests__/helper.ts': "export * from 'fx-orphan';\n",
    'src/orphan.test.ts': "import 'fx-orphan';\n",
    'App.tsx': 'export {};\n',
    'index.ts': "import './src/app';\n",
    'node_modules/fx-used/package.json': JSON.stringify({
      name: 'fx-used',
      peerDependencies: { 'fx-peer': '*' },
      devDependencies: { 'fx-orphan': '*' },
    }),
    'node_modules/fx-peer/package.json': JSON.stringify({ name: 'fx-peer' }),
    'node_modules/fx-orphan/package.json': JSON.stringify({ name: 'fx-orphan' }),
    'node_modules/fx-orphan-extra/package.json': JSON.stringify({ name: 'fx-orphan-extra' }),
  };
  let fxRoot = '';
  let fxPkg: AnyConfig;

  beforeAll(() => {
    fxRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'w37-deps-'));
    for (const [rel, body] of Object.entries(FIXTURE_FILES)) {
      const f = path.join(fxRoot, ...rel.split('/'));
      fs.mkdirSync(path.dirname(f), { recursive: true });
      fs.writeFileSync(f, body);
    }
    fxPkg = readJson(path.join(fxRoot, 'package.json'));
  });

  afterAll(() => {
    if (!fxRoot) return;
    const dirs = new Set<string>();
    for (const rel of Object.keys(FIXTURE_FILES)) {
      const parts = rel.split('/');
      fs.unlinkSync(path.join(fxRoot, ...parts));
      for (let i = 1; i < parts.length; i++) dirs.add(path.join(fxRoot, ...parts.slice(0, i)));
    }
    const deepestFirst = [...dirs].sort((a, b) => b.split(path.sep).length - a.split(path.sep).length);
    for (const d of deepestFirst) fs.rmdirSync(d);
    fs.rmdirSync(fxRoot);
  });

  it('d1 [BOOKKEEPING-RED — ruling R8] the set of unjustified runtime dependencies equals Object.keys(PENDING_REMOVAL)', () => {
    expectUnjustifiedEqualsPending(APP, loadPkg(), PENDING_REMOVAL, JUSTIFIED);
    // Fixture: a dependency with zero app imports and no PENDING_REMOVAL
    // entry reddens the same check; listing it makes the check pass (the
    // imported dep and its peer are justified; the comment, string, test-only
    // import and devDependencies edge justify nothing).
    expect(() => expectUnjustifiedEqualsPending(fxRoot, fxPkg, {}, {})).toThrow(/fx-orphan/);
    expectUnjustifiedEqualsPending(fxRoot, fxPkg, { 'fx-orphan': 'fixture' }, {});
  });

  it('d2 every PENDING_REMOVAL entry is still declared in package.json dependencies (stale-allowlist guard)', () => {
    expectPendingDeclared(loadPkg(), PENDING_REMOVAL);
    // Fixture: a PENDING_REMOVAL entry whose package is not declared reddens
    // the same check (the state right after Ahmed's npm uninstall).
    expectPendingDeclared(fxPkg, { 'fx-orphan': 'fixture' });
    expect(() => expectPendingDeclared(fxPkg, { 'fx-uninstalled': 'fixture' })).toThrow(/fx-uninstalled/);
  });

  it('d4 PENDING_REMOVAL names stay unused: zero app imports and no installed runtime dependency declares them', () => {
    expectPendingUnused(APP, loadPkg(), PENDING_REMOVAL);
    // Fixture: both halves redden the same check — an imported pending name,
    // and a pending name an installed runtime dependency declares (peer edge).
    expectPendingUnused(fxRoot, fxPkg, { 'fx-orphan': 'fixture' });
    expect(() => expectPendingUnused(fxRoot, fxPkg, { 'fx-used': 'fixture' })).toThrow(/fx-used/);
    expect(() => expectPendingUnused(fxRoot, fxPkg, { 'fx-peer': 'fixture' })).toThrow(/fx-used:peerDependencies/);
  });

  it('d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules', () => {
    // Session 70 U4b: the orphan PENDING_REMOVAL used to carry is gone for
    // good — `npm uninstall` + the committed lock (spec R6/R7; its only lock
    // dependents, @egjs/hammerjs and @types/hammerjs, leave with it — P8).
    // With PENDING_REMOVAL empty, d2/d4's real-app halves are vacuous by design
    // (spec review correction 13); this is the pin that replaces them.
    const name = 'react-native-gesture-handler';
    const pkg = loadPkg();
    const lock = loadLock();
    expect({
      dependencies: pkg.dependencies?.[name],
      devDependencies: pkg.devDependencies?.[name],
      lockRootDependencies: lock.packages['']?.dependencies?.[name],
      lockPackage: lock.packages[`node_modules/${name}`]?.version,
      installed: fs.existsSync(path.join(APP, 'node_modules', name)),
    }).toEqual({
      dependencies: undefined,
      devDependencies: undefined,
      lockRootDependencies: undefined,
      lockPackage: undefined,
      installed: false,
    });
  });
});

// ===========================================================================
// (e) runtimeVersion pin + preserve pins — MB-TWO-LEVER-RELEASE-09
// ===========================================================================
describe('W3-7 (e) runtime pin and preserved config', () => {
  it('e1 [CONSCIOUS PIN] runtimeVersion is { policy: "appVersion" } and expo.version is "1.0.0"', () => {
    // Flipping either retargets `eas update`: the appVersion policy derives the
    // runtime solely from expo.version, and phones on `preview` run runtime
    // 1.0.0. Ahmed changes both this pin and app.json in the release commit
    // AFTER the last OTA to the 1.0.0 fleet. Note eas.json:4
    // `appVersionSource: "remote"` (+ production `autoIncrement: true`,
    // eas.json:19): the store build number is managed remotely, so the
    // release commit must not assume app.json `version` alone drives it.
    // W3-7's app.json edits (permissions, plugin options, blockedPermissions,
    // privacyManifests) are runtimeVersion-neutral.
    // U4b (session 70) moved native patch versions without moving expo.version
    // — measured JS-compatible with the 1.0.0 preview binary (spec §1.3); those
    // native fixes reach testers only through a new build. The executable rule
    // (spec review correction 4, ruling RQ2): Before the first `eas update
    // --branch preview` from a main that contains U4b: (a) `npm ls` shows
    // exactly the version set recorded in the U4b PR body; (b) diff `@expo/cli`
    // `build/src/export/**` (the code `eas update` runs; not diffed in §1.3,
    // see §7) between 54.0.24 and the installed version, or smoke-test that OTA
    // on one tester device before announcing it; (c) any later expo-package
    // bump repeats (a)–(b) or bumps `expo.version`. From the first production
    // build on, every native change bumps `expo.version`.
    const expo = loadExpo();
    expect(expo.runtimeVersion).toEqual({ policy: 'appVersion' });
    expect(expo.version).toBe('1.0.0');
  });

  it('p1 [PRESERVE] plugin names and ORDER are unchanged', () => {
    const names = (loadExpo().plugins as unknown[]).map((p) => (Array.isArray(p) ? p[0] : p));
    expect(names).toEqual([
      'expo-font',
      'expo-secure-store',
      'expo-localization',
      'expo-camera',
      'expo-image-picker',
      '@react-native-google-signin/google-signin',
      'expo-apple-authentication',
      'expo-notifications',
      'expo-build-properties',
      '@sentry/react-native',
    ]);
  });

  it('p2 [PRESERVE] updates.url and extra.eas.projectId are unchanged', () => {
    const expo = loadExpo();
    expect(expo.updates.url).toBe('https://u.expo.dev/387a4fcb-76f6-4857-a2fb-39482ca4bd40');
    expect(expo.extra.eas.projectId).toBe('387a4fcb-76f6-4857-a2fb-39482ca4bd40');
  });
});

// ===========================================================================
// Session 69 U4a — native config for the first App Store build
// ===========================================================================
// Findings EXPO-04 / SA-03 / BLD-BP-09 (iPad), EXPO-07 (microphone string —
// flipped in place in (a): a3a, a4, a6, a7b), EXPO-08 (Face ID string),
// EXPO-10 / SA-10 (Arabic bundle localization), PM-5 / PM-6 (privacy manifest).
// Spec: docs/investigations/2026-09-29-session-69-state/U4A_NATIVE_CONFIG_SPEC.md
// plus the spec review's corrections 1-16 (binding where they correct the spec).
//
// Native-only: none of this reaches phones by `eas update`. Verified the same
// way as (a): the INSTALLED plugins run in-process over an in-memory copy of
// app.json with `introspect: true`; nothing is written. Two facts are not
// visible to Info.plist introspection at all and are asserted through the
// installed read-only helpers instead (spec review corrections 1, 8, 15):
// the device family is the pbxproj TARGETED_DEVICE_FAMILY
// (IOSConfig.DeviceFamily.getDeviceFamilies), and the .lproj/InfoPlist.strings
// wiring is a withXcodeProject mod (ios/Locales.js), so the locale files are
// checked through utils/locales.getResolvedLocalesAsync, which only reads.
describe('session 69 U4a', () => {
  const LOCALES_DIR = path.join(APP, 'locales');
  const COPY_POLICY = path.join(APP, 'src', 'i18n', '.copy-policy.json');
  const INVENTORY_DOC = path.join(REPO, 'docs', 'privacy-data-inventory.md');
  const LOCALE_KEYS = [
    'CFBundleDisplayName',
    'NSCameraUsageDescription',
    'NSMicrophoneUsageDescription',
    'NSPhotoLibraryUsageDescription',
  ];
  const AR_DISPLAY_NAME = 'ميّز'; // MYEZ (Ahmed, 2026-09-30); the in-app catalog follows in unit U-R
  // Arabic harakat, tanwin, shadda and sukun (U+064B..U+0652) — the copy rule
  // is "no diacritics".
  const AR_DIACRITICS = /[\u064B-\u0652]/;
  // Base MainActivity configChanges of the installed introspection template
  // (@expo/config-plugins build/plugins/withAndroidBaseMods.js:81).
  const TEMPLATE_CONFIG_CHANGES = 'keyboard|keyboardHidden|orientation|screenSize|screenLayout|uiMode';
  const SECURE_STORE_BACKUP_RULES = '@xml/secure_store_backup_rules';
  const SECURE_STORE_EXTRACTION_RULES = '@xml/secure_store_data_extraction_rules';
  const T = (id: string) => `NSPrivacyCollectedDataType${id}`;
  const PURPOSE = (id: string) => `NSPrivacyCollectedDataTypePurpose${id}`;

  /**
   * The props Expo hands a plugin (withStaticPlugin): the second element of an
   * array entry, `undefined` for a bare string. Not `pluginOptions`, which
   * returns {} for a bare string: expo-localization's default options
   * `{ allowDynamicLocaleChangesAndroid: true }` apply ONLY to undefined
   * (withExpoLocalization.js:106-108), so {} would misstate today's behaviour.
   */
  function rawPluginProps(expo: AnyConfig, name: string): unknown {
    const entry = (expo.plugins as unknown[]).find((p) =>
      Array.isArray(p) ? p[0] === name : p === name,
    );
    return Array.isArray(entry) ? entry[1] : undefined;
  }

  interface NativeOut {
    plist: Record<string, unknown>;
    mainApplication: Record<string, string>;
    mainActivity: Record<string, string>;
    usesPermission: Record<string, string>[];
  }

  /**
   * Runs, in app.json order, the installed expo-secure-store, expo-localization,
   * expo-camera and expo-image-picker plugins, then the iPad full-screen
   * Info.plist plugin and the two Android permission base mods, and evaluates
   * the `ios.infoPlist` and `android.manifest` mod chains once each. The
   * Info.plist starts from the config's static `ios.infoPlist`, exactly as the
   * introspection base mod merges it (withIosBaseMods.js:301-305) — that is how
   * expo-localization's CFBundleLocalizations (set on the static object,
   * withExpoLocalization.js:29-31) reaches the plist. The fake manifest carries
   * the .MainApplication / .MainActivity nodes getMainApplicationOrThrow /
   * getMainActivityOrThrow assert on (spec review correction 7). Dangerous,
   * strings and gradle mods are never evaluated: nothing touches the disk.
   */
  async function compileNative(expo: AnyConfig): Promise<NativeOut> {
    const { AndroidConfig, IOSConfig } = reqFromApp('expo/config-plugins');
    const PLUGINS: Record<string, AnyConfig> = {
      'expo-secure-store': reqFromApp('expo-secure-store/app.plugin.js').default,
      'expo-localization': reqFromApp('expo-localization/app.plugin.js').default,
      'expo-camera': reqFromApp('expo-camera/app.plugin.js').default,
      'expo-image-picker': reqFromApp('expo-image-picker/app.plugin.js').default,
    };
    let config: AnyConfig = clone(expo);
    config._internal = { projectRoot: APP, isDebug: false };
    for (const entry of expo.plugins as unknown[]) {
      const name = (Array.isArray(entry) ? entry[0] : entry) as string;
      if (PLUGINS[name]) config = PLUGINS[name](config, rawPluginProps(expo, name));
    }
    config = IOSConfig.RequiresFullScreen.withRequiresFullScreen(config);
    config = AndroidConfig.Permissions.withInternalBlockedPermissions(config);
    config = AndroidConfig.Permissions.withPermissions(config);

    const modRequest = { projectRoot: APP, platformProjectRoot: APP, projectName: 'Qaren', introspect: true };
    const ios = await config.mods.ios.infoPlist({
      ...config,
      modRequest: { ...modRequest, platform: 'ios', modName: 'infoPlist' },
      modResults: { ...(config.ios?.infoPlist ?? {}) },
    });
    const android = await config.mods.android.manifest({
      ...config,
      modRequest: { ...modRequest, platform: 'android', modName: 'manifest' },
      modResults: {
        manifest: {
          $: { 'xmlns:android': 'http://schemas.android.com/apk/res/android' },
          'uses-permission': [],
          application: [
            {
              $: { 'android:name': '.MainApplication' },
              activity: [
                { $: { 'android:name': '.MainActivity', 'android:configChanges': TEMPLATE_CONFIG_CHANGES } },
              ],
            },
          ],
        },
      },
    });
    const application = android.modResults.manifest.application[0];
    return {
      plist: ios.modResults,
      mainApplication: application.$,
      mainActivity: application.activity[0].$,
      usesPermission: android.modResults.manifest['uses-permission'].map(
        (u: { $: Record<string, string> }) => u.$,
      ),
    };
  }

  const readLocale = (lang: 'en' | 'ar'): AnyConfig => readJson(path.join(LOCALES_DIR, `${lang}.json`));
  const collected = (): AnyConfig[] => loadExpo().ios.privacyManifests.NSPrivacyCollectedDataTypes;
  const entryOf = (id: string): AnyConfig | undefined =>
    collected().find((e) => e.NSPrivacyCollectedDataType === T(id));
  const inventoryRow = (md: string, id: string): string | undefined =>
    md.split(/\r?\n/).find((l) => /^\|\s*\d+\s*\|/.test(l) && l.includes(`| \`${id}\` |`));

  // ---- R1: iPhone only ----------------------------------------------------

  it('u1 [R1 / D1 option A] ios.supportsTablet is false and the installed getDeviceFamilies resolves iPhone only ([1])', () => {
    // TARGETED_DEVICE_FAMILY is a pbxproj setting written by a withXcodeProject
    // mod (ios/DeviceFamily.js:25-31), which introspection never runs, so the
    // family is read through the installed resolver (spec review correction 1).
    const { IOSConfig } = reqFromApp('expo/config-plugins');
    const expo = loadExpo();
    expect(expo.ios.supportsTablet).toBe(false);
    expect(IOSConfig.DeviceFamily.getDeviceFamilies(expo)).toEqual([1]);
  });

  it('u2 [R1] executed withRequiresFullScreen: Info.plist carries no UISupportedInterfaceOrientations~ipad entry', async () => {
    // ios/RequiresFullScreen.js:59-66 adds the four iPad orientations only
    // while tablet support is on. UIRequiresFullScreen:false is still emitted
    // either way (harmless) and is deliberately not asserted.
    const { plist } = await compileNative(loadExpo());
    expect(plist['UISupportedInterfaceOrientations~ipad']).toBeUndefined();
  });

  // ---- R2: the honest microphone string, order-independent -----------------

  it('u3 [R2] executed plugins in BOTH registration orders: NSMicrophoneUsageDescription is the honest string', async () => {
    // Q1 option a: the string on BOTH plugins. With it on one plugin and false
    // on the other the key survives only in one order (ios/Permissions.js:30-32
    // deletes on false, and the later-registered infoPlist mod runs first —
    // spec review correction 4).
    const expo = loadExpo();
    const forward = await compile(expo, FORWARD);
    const reversed = await compile(expo, REVERSED);
    expect(forward.plist.NSMicrophoneUsageDescription).toBe(MIC_PURPOSE);
    expect(reversed.plist.NSMicrophoneUsageDescription).toBe(MIC_PURPOSE);
  });

  // ---- R3: no Face ID purpose string ---------------------------------------

  it('u4 [R3] expo-secure-store entry: faceIDPermission === false and the Android backup half is not switched off', () => {
    // expo-secure-store is the only installed plugin that emits the key
    // (withSecureStore.js:7,10-13, spec review correction 6); the app never
    // uses biometrics. configureAndroidBackup must stay at its default (true,
    // withSecureStore.js:8) — this unit changes the iOS half only.
    const opts = rawPluginProps(loadExpo(), 'expo-secure-store') as Record<string, unknown> | undefined;
    expect(opts?.configureAndroidBackup).not.toBe(false);
    expect(opts?.faceIDPermission).toBe(false);
  });

  it('u5 [R3] executed plugins: Info.plist has no NSFaceIDUsageDescription; secure-store backup rules still reach .MainApplication', async () => {
    const { plist, mainApplication } = await compileNative(loadExpo());
    // Preserve: the Android half is unchanged.
    expect(mainApplication['android:fullBackupContent']).toBe(SECURE_STORE_BACKUP_RULES);
    expect(mainApplication['android:dataExtractionRules']).toBe(SECURE_STORE_EXTRACTION_RULES);
    // R3: applyPermissions deletes the key on the literal false
    // (ios/Permissions.js:30-32).
    expect(plist.NSFaceIDUsageDescription).toBeUndefined();
  });

  // ---- R4: Arabic bundle localization --------------------------------------

  it('u6 [R4] expo-localization entry: supportedLocales { ios: ["en", "ar"] } only, and allowDynamicLocaleChangesAndroid stays true', () => {
    // iOS only (spec review correction 10 / Q3): an `android` half would add
    // android:localeConfig, a locales_config.xml dangerous mod and a gradle
    // resourceConfigurations edit (withExpoLocalization.js:48-84).
    // allowDynamicLocaleChangesAndroid must be passed explicitly: passing ANY
    // options object drops the default (withExpoLocalization.js:106-108,
    // spec review correction 9).
    const opts = rawPluginProps(loadExpo(), 'expo-localization') as Record<string, unknown> | undefined;
    expect(opts?.supportedLocales).toEqual({ ios: ['en', 'ar'] });
    expect(opts?.allowDynamicLocaleChangesAndroid).toBe(true);
  });

  it('u7 [R4] executed expo-localization: CFBundleLocalizations is ["en", "ar"]; MainActivity keeps |locale|layoutDirection and the app gets no android:localeConfig', async () => {
    const { plist, mainApplication, mainActivity } = await compileNative(loadExpo());
    // Preserve (correction 9 / 10): today's Android behaviour.
    expect(mainActivity['android:configChanges']).toBe(`${TEMPLATE_CONFIG_CHANGES}|locale|layoutDirection`);
    expect(mainApplication['android:localeConfig']).toBeUndefined();
    // R4: withExpoLocalization.js:11-14,29-31.
    expect(plist.CFBundleLocalizations).toEqual(['en', 'ar']);
  });

  it('u8 [R4] expo.locales wires en and ar to ./locales/{en,ar}.json', () => {
    expect(loadExpo().locales).toEqual({ en: './locales/en.json', ar: './locales/ar.json' });
  });

  it('u9 [R4] locales/en.json and locales/ar.json parse and nest exactly the four keys under "ios"; every value is InfoPlist.strings-safe', () => {
    // Top-level keys go to BOTH platforms (utils/locales.js:46-65) and Android
    // withLocales would write them as values-b+<lang>/strings.xml junk, so
    // "ios" is the only top-level key (spec review correction 11).
    // ios/Locales.js:82 writes values unescaped: no `"` and no `\`.
    for (const lang of ['en', 'ar'] as const) {
      const file = readLocale(lang);
      expect({ lang, top: Object.keys(file).sort() }).toEqual({ lang, top: ['ios'] });
      expect({ lang, keys: Object.keys(file.ios).sort() }).toEqual({ lang, keys: LOCALE_KEYS });
      for (const key of LOCALE_KEYS) {
        const value = file.ios[key];
        expect({ lang, key, isString: typeof value === 'string' && value.trim().length > 0 }).toEqual({
          lang,
          key,
          isString: true,
        });
        expect({ lang, key, unsafe: /["\\]/.test(value) }).toEqual({ lang, key, unsafe: false });
      }
    }
  });

  it('u10 [R4] locales/en.json equals the shipped English strings: display name = expo.name, camera / photos / microphone = the plugin purpose strings', () => {
    const en = readLocale('en').ios;
    const expo = loadExpo();
    expect(en.CFBundleDisplayName).toBe('MYEZ');
    expect(en.CFBundleDisplayName).toBe(expo.name);
    // No drift between the English .lproj strings and the plugin options
    // (spec review correction 11).
    expect(en.NSCameraUsageDescription).toBe(CAMERA_PURPOSE);
    expect(en.NSCameraUsageDescription).toBe(pluginOptions(expo, 'expo-camera')?.cameraPermission);
    expect(en.NSPhotoLibraryUsageDescription).toBe(PHOTOS_PURPOSE);
    expect(en.NSPhotoLibraryUsageDescription).toBe(pluginOptions(expo, 'expo-image-picker')?.photosPermission);
    expect(en.NSMicrophoneUsageDescription).toBe(MIC_PURPOSE);
    expect(en.NSMicrophoneUsageDescription).toBe(pluginOptions(expo, 'expo-camera')?.microphonePermission);
    expect(en.NSMicrophoneUsageDescription).toBe(pluginOptions(expo, 'expo-image-picker')?.microphonePermission);
  });

  it('u11 [R4] locales/ar.json: display name ميّز; Arabic purpose strings with no Latin letters, no diacritics, none of the copy-policy banned or scary terms', () => {
    // src/i18n/ar.json is the only file __tests__/copy-policy.test.ts reads, so
    // this file is fenced here (spec review correction 12).
    const ar = readLocale('ar').ios;
    const en = readLocale('en').ios;
    const policy = readJson(COPY_POLICY);
    expect(ar.CFBundleDisplayName).toBe(AR_DISPLAY_NAME);
    // The brand spelling the in-app Arabic catalog already uses.
    // The in-app catalog still says قارن until unit U-R renames it; the display name is pinned on the locale file above.
    for (const key of LOCALE_KEYS) {
      const value: string = ar[key];
      // The brand name carries a deliberate shadda (ميّز, decision D13); the no-diacritics rule
      // applies to everything else in the string.
      const withoutBrand = value.split(AR_DISPLAY_NAME).join('');
      expect({ key, diacritics: AR_DIACRITICS.test(withoutBrand) }).toEqual({ key, diacritics: false });
      for (const rule of policy.banned_ar as { pattern: string; label: string }[]) {
        expect({ key, banned: rule.label, hit: new RegExp(rule.pattern).test(value) }).toEqual({
          key,
          banned: rule.label,
          hit: false,
        });
      }
      for (const term of policy.scary_vocab_ar as string[]) {
        expect({ key, scary: term, hit: value.includes(term) }).toEqual({ key, scary: term, hit: false });
      }
    }
    for (const key of LOCALE_KEYS.filter((k) => k !== 'CFBundleDisplayName')) {
      const value: string = ar[key];
      expect({ key, arabic: /[\u0621-\u064A]/.test(value), latin: /[A-Za-z]/.test(value) }).toEqual({
        key,
        arabic: true,
        latin: false,
      });
      expect(value).not.toBe(en[key]);
    }
  });

  it('u12 [R4] getResolvedLocalesAsync (read-only): iOS resolves en and ar with the four keys; Android resolves no strings', async () => {
    // The .lproj/InfoPlist.strings writer (ios/Locales.js:45-53,69-85) is a
    // withXcodeProject mod that introspection never runs and that writes to
    // disk, so only its read-only resolver is executed here (correction 8).
    const { getResolvedLocalesAsync } = reqFromApp('@expo/config-plugins/build/utils/locales');
    const locales = loadExpo().locales ?? {};
    const ios = await getResolvedLocalesAsync(APP, locales, 'ios');
    expect(Object.keys(ios).sort()).toEqual(['ar', 'en']);
    expect(Object.keys(ios.en).sort()).toEqual(LOCALE_KEYS);
    expect(Object.keys(ios.ar).sort()).toEqual(LOCALE_KEYS);
    expect(ios.ar.CFBundleDisplayName).toBe(AR_DISPLAY_NAME);
    const android = await getResolvedLocalesAsync(APP, locales, 'android');
    expect(android).toEqual({ en: {}, ar: {} });
  });

  // ---- R5: privacy manifest ------------------------------------------------

  it('u13 [R5] the privacy manifest declares CustomerSupport: Linked true, Tracking false, purpose AppFunctionality', () => {
    expect(entryOf('CustomerSupport')).toEqual({
      NSPrivacyCollectedDataType: T('CustomerSupport'),
      NSPrivacyCollectedDataTypeLinked: true,
      NSPrivacyCollectedDataTypeTracking: false,
      NSPrivacyCollectedDataTypePurposes: [PURPOSE('AppFunctionality')],
    });
  });

  it('u14 [R5] SearchHistory and ProductInteraction add ProductPersonalization and keep their existing purposes', () => {
    // Spec review Q5: the green must cite the backend personalization consumer
    // of each type in the inventory row; if none exists this half of R5 is
    // dropped and this test changes with it.
    const search = entryOf('SearchHistory');
    const interaction = entryOf('ProductInteraction');
    expect(search?.NSPrivacyCollectedDataTypePurposes).toContain(PURPOSE('AppFunctionality'));
    expect(interaction?.NSPrivacyCollectedDataTypePurposes).toContain(PURPOSE('Analytics'));
    expect(search?.NSPrivacyCollectedDataTypePurposes).toContain(PURPOSE('ProductPersonalization'));
    expect(interaction?.NSPrivacyCollectedDataTypePurposes).toContain(PURPOSE('ProductPersonalization'));
  });

  it('u15 [R5] inventory doc: a CustomerSupport row cites the Contact Us form, and the OtherUserContent row no longer does', () => {
    // Spec review correction 14 / Q4: the Contact Us form
    // (ContactUsScreen.tsx:85-96) is declared once, under CustomerSupport.
    // c3 / c5 keep the table and the JSON fence equal to app.json.
    const md = fs.readFileSync(INVENTORY_DOC, 'utf8');
    const support = inventoryRow(md, 'CustomerSupport');
    expect(support).toBeDefined();
    expect(support).toContain('ContactUsScreen.tsx');
    expect(inventoryRow(md, 'OtherUserContent')).not.toContain('ContactUsScreen.tsx');
  });

  it('u16 [R2] inventory doc no longer claims there is no NSMicrophoneUsageDescription on iOS', () => {
    // docs/privacy-data-inventory.md "Not collected" > Audio (spec review
    // correction 5). Line wraps are normalised before matching.
    const md = fs.readFileSync(INVENTORY_DOC, 'utf8').replace(/\s+/g, ' ');
    expect(md).not.toMatch(/there is no `NSMicrophoneUsageDescription` on iOS/);
  });
});

// ===========================================================================
// Session 70 U4b — Expo SDK 54 patch level with one deliberate exclusion
// ===========================================================================
// Spec: docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md
// with its binding review corrections and the session-71 orchestrator rulings
// (RQ1 ALIGN eslint-config-expo to ~10.0.0, RQ3 split the CI step). NATIVE:
// the patch bumps and the gesture-handler removal (d5) reach users only
// through `eas build`. `npx expo install --check` compares the installed
// packages with the Expo API's expected map ONLINE and with the installed
// expo's own bundledNativeModules.json OFFLINE (EXPO_OFFLINE=1): k5 is the
// offline check's in-jest twin, k6 pins the CI split (blocking offline step,
// report-only online step). react-native-svg is excluded on purpose (k3): SDK
// 54 bundles exact 15.12.1 while the preview binary already runs 15.15.5 and
// a downgrade would be a native change nobody asked for (spec §1.5).
describe('session 70 U4b — Expo SDK 54 patch level with one deliberate exclusion', () => {
  const CI_YML = path.join(REPO, '.github', 'workflows', 'ci.yml');
  const BUNDLED = path.join(APP, 'node_modules', 'expo', 'bundledNativeModules.json');
  const EXCLUDE = ['react-native-svg'];
  // The SDK-54 patch level `expo install --check` expected on 2026-09-30 and
  // again on 2026-10-03 (spec §1.1, ruling RQ8: the registry's newest).
  const SDK54_TARGETS: Record<string, string> = {
    expo: '54.0.37',
    'expo-font': '14.0.12',
    'expo-localization': '17.0.9',
    'expo-screen-capture': '8.0.10',
    'expo-updates': '29.0.20',
  };
  const OFFLINE_RUN = 'cd SmartCompareApp && EXPO_OFFLINE=1 npx expo install --check';
  const ONLINE_RUN = 'cd SmartCompareApp && npx expo install --check';

  type Semver = [number, number, number];
  const parseSemver = (v: string | undefined): Semver | null => {
    const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(v ?? '');
    return m === null ? null : [Number(m[1]), Number(m[2]), Number(m[3])];
  };
  const cmp = (a: Semver, b: Semver): number => a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
  /** `version` has `target`'s major.minor and a patch at or above it. */
  const atOrAbovePatch = (version: string | undefined, target: string): boolean => {
    const have = parseSemver(version);
    const want = parseSemver(target);
    return have !== null && want !== null && have[0] === want[0] && have[1] === want[1] && have[2] >= want[2];
  };
  /** A declared `~x.y.z` range whose x.y.z is at or above `target`'s patch. */
  const tildeAtOrAbove = (declared: string | undefined, target: string): boolean =>
    typeof declared === 'string' && declared.startsWith('~') && atOrAbovePatch(declared.slice(1), target);
  /**
   * The range forms bundledNativeModules.json uses: exact `x.y.z`, `~x.y.z`
   * (same major.minor, patch >=) and `^x.y.z` (same major, >= x.y.z; a 0.y.z
   * caret pins the minor like a tilde). Any other form is reported by name,
   * never guessed at.
   */
  const satisfies = (installed: string, range: string): boolean | 'unsupported range' => {
    const m = /^([~^]?)(\d+\.\d+\.\d+)$/.exec(range);
    if (m === null) return 'unsupported range';
    const have = parseSemver(installed);
    const want = parseSemver(m[2]);
    if (have === null || want === null) return false;
    if (m[1] === '') return cmp(have, want) === 0;
    if (m[1] === '~' || want[0] === 0) return atOrAbovePatch(installed, m[2]);
    return have[0] === want[0] && cmp(have, want) >= 0;
  };
  const lockVersion = (name: string): string | undefined =>
    loadLock().packages[`node_modules/${name}`]?.version as string | undefined;
  // An `expo.install.exclude` entry may carry a range (`name@range`,
  // @expo/cli validateDependenciesVersions.js); only the name matters here.
  const excludedName = (entry: string): string =>
    entry.lastIndexOf('@') > 0 ? entry.slice(0, entry.lastIndexOf('@')) : entry;

  it('k1 package.json declares the five SDK-54 packages at or above the patch expo install --check expects', () => {
    const deps = loadPkg().dependencies;
    const rows = Object.entries(SDK54_TARGETS).map(([name, target]) => {
      const declared: string | undefined = deps[name];
      return { name, target, declared, ok: tildeAtOrAbove(declared, target) };
    });
    expect(rows).toEqual(rows.map((r) => ({ ...r, ok: true })));
  });

  it('k2 package-lock.json and node_modules resolve the five packages at or above those patches', () => {
    const rows = Object.entries(SDK54_TARGETS).map(([name, target]) => {
      const lock = lockVersion(name);
      const installed = installedVersion(name);
      return { name, target, lock, installed, ok: atOrAbovePatch(lock, target) && atOrAbovePatch(installed, target) };
    });
    expect(rows).toEqual(rows.map((r) => ({ ...r, ok: true })));
  });

  it('k3 expo.install.exclude is exactly ["react-native-svg"]', () => {
    // spec R6: the ONE new top-level key, added BEFORE any `expo install` runs
    // (P1) so every later install honours it. eslint-config-expo is aligned
    // (k4), not excluded (ruling RQ1).
    expect(loadPkg().expo).toEqual({ install: { exclude: EXCLUDE } });
  });

  it('k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules', () => {
    // Ruling RQ1 (ALIGN): the 10.0.0 and 55.0.1 tarballs differ in package.json
    // only — version, gitHead and the eslint-plugin-expo range, which the
    // installed 1.0.3 satisfies either way (spec §1.4) — so aligning changes
    // zero lint rules; eslint.config.js keeps `require('eslint-config-expo/flat')`.
    const name = 'eslint-config-expo';
    const pkg = loadPkg();
    expect({
      declared: pkg.devDependencies?.[name],
      runtime: pkg.dependencies?.[name],
      lock: lockVersion(name),
      installed: installedVersion(name),
    }).toEqual({
      declared: expect.stringMatching(/^~10\.0\.\d+$/),
      runtime: undefined,
      lock: expect.stringMatching(/^10\.0\.\d+$/),
      installed: expect.stringMatching(/^10\.0\.\d+$/),
    });
  });

  it('k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude', () => {
    // The in-jest twin of `EXPO_OFFLINE=1 npx expo install --check` (spec
    // §1.1): the INSTALLED versions against the INSTALLED expo's
    // bundledNativeModules.json, honouring expo.install.exclude the way
    // @expo/cli checkPackages.js / validateDependenciesVersions.js do.
    const pkg = loadPkg();
    const bundled: Record<string, string> = readJson(BUNDLED);
    const excluded = ((pkg.expo?.install?.exclude ?? []) as string[]).map(excludedName);
    // An exclusion that names nothing the bundle lists would be a typo, not a decision.
    for (const name of excluded) {
      expect({ excluded: name, bundled: bundled[name] }).toEqual({ excluded: name, bundled: expect.any(String) });
    }
    const declared = [...Object.keys(pkg.dependencies ?? {}), ...Object.keys(pkg.devDependencies ?? {})];
    const checked: { name: string; installed: string | undefined; bundled: string; verdict: boolean | 'unsupported range' }[] = [];
    for (const name of declared) {
      const range = bundled[name];
      if (range === undefined || excluded.includes(name)) continue;
      const installed = installedVersion(name);
      checked.push({ name, installed, bundled: range, verdict: installed === undefined ? false : satisfies(installed, range) });
    }
    expect(checked.length).toBeGreaterThan(0);
    expect(checked.filter((c) => c.verdict !== true)).toEqual([]);
  });

  it('k6 CI: the frontend-tests expo install --check step is blocking and no longer named non-blocking (Q3 = B: the EXPO_OFFLINE=1 lockfile step blocks; the online step stays report-only)', () => {
    // Ruling RQ3 / spec R10 (option B): a text parse of ci.yml — the YAML is
    // split on /\r?\n/ (the file checks out CRLF on Windows), the job runs from
    // `  frontend-tests:` to the next line at indent 2, a step runs from its
    // `      - ` to the next one. The online map moves on Expo's schedule and
    // on API outages (spec §1.1), so only the offline (lockfile) step may block.
    const lines = fs.readFileSync(CI_YML, 'utf8').split(/\r?\n/);
    const jobStart = lines.findIndex((l) => l === '  frontend-tests:');
    expect(jobStart).toBeGreaterThanOrEqual(0);
    const after = lines.findIndex((l, i) => i > jobStart && /^  \S/.test(l));
    const job = lines.slice(jobStart, after === -1 ? lines.length : after);
    const stepsAt = job.findIndex((l) => l === '    steps:');
    expect(stepsAt).toBeGreaterThan(0);
    // No job-level continue-on-error either.
    expect(job.slice(0, stepsAt).filter((l) => l.includes('continue-on-error'))).toEqual([]);
    const starts = job.map((l, i) => (/^      - /.test(l) ? i : -1)).filter((i) => i >= 0);
    const steps = starts.map((start, k) => {
      const block = job.slice(start, k + 1 < starts.length ? starts[k + 1] : job.length);
      const field = (key: string): string | undefined => {
        const re = new RegExp(`^\\s+(?:- )?${key}: (.*)$`);
        const hit = block.map((l) => re.exec(l)).find((m) => m !== null);
        return hit ? hit[1].trim() : undefined;
      };
      return { name: field('name'), run: field('run'), continueOnError: field('continue-on-error') };
    });
    expect(steps.filter((s) => s.name === 'Expo dependency drift (non-blocking)')).toEqual([]);
    expect(steps.filter((s) => s.run === OFFLINE_RUN)).toEqual([
      { name: 'Expo dependency drift (lockfile)', run: OFFLINE_RUN, continueOnError: undefined },
    ]);
    expect(steps.filter((s) => s.run === ONLINE_RUN)).toEqual([
      { name: 'Expo SDK patch drift (report-only)', run: ONLINE_RUN, continueOnError: 'true' },
    ]);
    // The blocking step first, the report-only step after it (R10 "followed by").
    const at = (name: string): number => steps.findIndex((s) => s.name === name);
    expect(at('Expo dependency drift (lockfile)')).toBeGreaterThanOrEqual(0);
    expect(at('Expo dependency drift (lockfile)')).toBeLessThan(at('Expo SDK patch drift (report-only)'));
  });
});

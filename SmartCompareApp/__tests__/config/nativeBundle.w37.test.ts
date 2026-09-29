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
 */
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as ts from 'typescript';

type AnyConfig = any;

const APP = path.resolve(__dirname, '../..');
const REPO = path.resolve(APP, '..');

const readJson = (p: string): AnyConfig => JSON.parse(fs.readFileSync(p, 'utf8'));
const loadExpo = (): AnyConfig => readJson(path.join(APP, 'app.json')).expo;
const loadPkg = (): AnyConfig => readJson(path.join(APP, 'package.json'));
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
  const sha256 = (file: string): string =>
    crypto.createHash('sha256').update(fs.readFileSync(path.join(APP, 'assets', file))).digest('hex');

  // AHMED: flip to true once assets/{icon,splash-icon,adaptive-icon}.png are
  // re-rendered (CLAUDE.md App-Store blocker #1 / bundle-d-followups ICN-0001).
  const ICON_ART_SUPPLIED = false;
  const itArt = ICON_ART_SUPPLIED ? it : it.skip;

  itArt('b1 icon.png differs from the SHA-256 recorded on 2026-05-24 (AHMED: supply art — CLAUDE.md blocker #1 / bundle-d-followups ICN-0001)', () => {
    expect(sha256('icon.png')).not.toBe(RECORDED_2026_05_24.icon);
  });

  itArt('b2 splash-icon.png and adaptive-icon.png differ from the SHA-256 recorded on 2026-05-24 and from each other (AHMED: supply art — CLAUDE.md blocker #1 / bundle-d-followups ICN-0001)', () => {
    expect(sha256('splash-icon.png')).not.toBe(RECORDED_2026_05_24.splashAndAdaptive);
    expect(sha256('adaptive-icon.png')).not.toBe(RECORDED_2026_05_24.splashAndAdaptive);
    // The reproducible placeholder signal: no custom render is byte-identical.
    expect(sha256('splash-icon.png')).not.toBe(sha256('adaptive-icon.png'));
  });

  it.todo('b3-todo flip ICON_ART_SUPPLIED once assets/ are re-rendered');

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
   * reason to ship a native module. Three devDependency decoys exist for
   * react-native-gesture-handler (measured 2026-09-11 over 898 installed
   * package.json files): @testing-library/react-native@13.3.3,
   * react-native-reanimated@4.1.7 and react-native-screens@4.16.0, each
   * :: devDependencies. Adding 'devDependencies' here would justify the orphan
   * and silently delete this unit's headline test.
   */
  const EDGE_FIELDS = ['dependencies', 'peerDependencies', 'optionalDependencies'] as const;

  /**
   * Ruling R11 — the import scan covers app source ONLY: src/**\/*.{ts,tsx}
   * minus src/**\/__tests__, src/**\/__mocks__ and *.test.* / *.spec.* files,
   * plus App.tsx and index.ts (see sourceFiles()). MB-SAFE-HYGIENE-06's
   * wording includes __tests__; an import inside a test suite — top-level
   * __tests__/ OR a co-located src/**\/__tests__/ — is not a reason to ship a
   * native module into every EAS build. Measured: the outcome is identical
   * either way (react-native-gesture-handler has 0 test imports; the only
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
    // MB-SAFE-HYGIENE-06, measured at b63a8368: 0 imports in src/, App.tsx,
    // index.ts (and 0 imports in __tests__/ — this file names it only as
    // data); a walk of every installed package.json (1,067 incl. nested
    // node_modules) finds no dependencies/peerDependencies/
    // optionalDependencies edge — the only edges are the three
    // devDependencies decoys named in EDGE_FIELDS' docstring — so no
    // transitive runtime need exists; package-lock.json references it only as a
    // ROOT dependency (:45) and its own entry. The navigators the app imports
    // (@react-navigation/native-stack, bottom-tabs) peer on
    // react-native-screens + react-native-safe-area-context, NOT on it.
    'react-native-gesture-handler':
      'orphan native module (0 app imports, 0 installed runtime/peer edges) — AHMED: npm uninstall + commit package-lock.json, then delete this entry',
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

  it.todo(
    'd3 AHMED: npm uninstall react-native-gesture-handler, commit package-lock.json, delete the PENDING_REMOVAL entry, then eas build',
  );

  it('d4 PENDING_REMOVAL names stay unused: zero app imports and no installed runtime dependency declares them', () => {
    expectPendingUnused(APP, loadPkg(), PENDING_REMOVAL);
    // Fixture: both halves redden the same check — an imported pending name,
    // and a pending name an installed runtime dependency declares (peer edge).
    expectPendingUnused(fxRoot, fxPkg, { 'fx-orphan': 'fixture' });
    expect(() => expectPendingUnused(fxRoot, fxPkg, { 'fx-used': 'fixture' })).toThrow(/fx-used/);
    expect(() => expectPendingUnused(fxRoot, fxPkg, { 'fx-peer': 'fixture' })).toThrow(/fx-used:peerDependencies/);
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

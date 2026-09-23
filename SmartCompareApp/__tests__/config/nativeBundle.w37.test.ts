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
const CAMERA_PURPOSE = 'Qaren needs camera access to photograph products for comparison.';
const PHOTOS_PURPOSE = 'Qaren needs photo library access to identify products from your photos.';

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
describe('W3-7 (a) no microphone on either platform', () => {
  it('a1 [SOURCE-SHAPE PIN, no compiled-output consequence — ruling R3] android.permissions does not list RECORD_AUDIO', () => {
    // Once expo-image-picker's microphonePermission:false lands,
    // @expo/config-plugins build/android/Permissions.js:52-55
    // (withBlockedPermissions) strips RECORD_AUDIO from
    // config.android.permissions at registration time, so re-adding the
    // string changes neither Info.plist nor the manifest (mutation M1). This
    // pin keeps the committed source honest; it is NOT behavioural coverage.
    expect(loadExpo().android.permissions).not.toContain(RECORD_AUDIO);
  });

  it('a2 android.blockedPermissions contains RECORD_AUDIO (scope beyond the finding — ruling R5)', () => {
    // Schema key: @expo/config-types build/ExpoConfig.d.ts:657; consumed by
    // AndroidConfig.Permissions.withInternalBlockedPermissions. A plugin-
    // independent second guard on Android. a7b isolates the plugin lever so
    // this belt cannot hide whether the braces work.
    expect(loadExpo().android.blockedPermissions).toContain(RECORD_AUDIO);
  });

  it('a3a expo-camera entry: microphonePermission === false (behavioural — dropping it reddens a6 + a8)', () => {
    expect(pluginOptions(loadExpo(), 'expo-camera')?.microphonePermission).toBe(false);
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

  it('a4 expo-image-picker entry: microphonePermission === false', () => {
    // NOT cameraPermission:false — withImagePicker.js:41 would then BLOCK
    // android.permission.CAMERA, which the app needs (a5 / a7 pin CAMERA).
    expect(pluginOptions(loadExpo(), 'expo-image-picker')?.microphonePermission).toBe(false);
  });

  it('a5 [PRESERVE] CAMERA is requested and both purpose strings are unchanged', () => {
    const expo = loadExpo();
    expect(expo.android.permissions).toContain(CAMERA);
    expect(pluginOptions(expo, 'expo-camera')?.cameraPermission).toBe(CAMERA_PURPOSE);
    expect(pluginOptions(expo, 'expo-image-picker')?.photosPermission).toBe(PHOTOS_PURPOSE);
  });

  it('a6 executed plugins: Info.plist has NO NSMicrophoneUsageDescription; camera + photos strings intact', async () => {
    const { plist } = await compile(loadExpo());
    expect(plist.NSCameraUsageDescription).toBe(CAMERA_PURPOSE);
    expect(plist.NSPhotoLibraryUsageDescription).toBe(PHOTOS_PURPOSE);
    expect(plist.NSMicrophoneUsageDescription).toBeUndefined();
  });

  it('a7 executed plugins: RECORD_AUDIO appears ONLY as a tools:node="remove" block; CAMERA is a plain request', async () => {
    const { usesPermission } = await compile(loadExpo());
    expect(usesPermission).toContainEqual({ 'android:name': CAMERA });
    expectRecordAudioOnlyBlocked(usesPermission);
  });

  it('a7b [ruling R2, mandatory] with android.blockedPermissions DELETED the plugin lever alone still blocks RECORD_AUDIO', async () => {
    // Mutation: drop expo-image-picker.microphonePermission:false. blockedPermissions
    // and the picker opt-out are mutually redundant (each alone emits
    // tools:node="remove"), so a7 survives every single-element mutation; this
    // assertion isolates the plugin lever from the app.json lever.
    const expo = clone(loadExpo());
    delete expo.android.blockedPermissions;
    const { usesPermission } = await compile(expo);
    expect(usesPermission).toContainEqual({ 'android:name': CAMERA });
    expectRecordAudioOnlyBlocked(usesPermission);
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

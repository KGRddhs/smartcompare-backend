/**
 * S79 B3-A item 5 -- purpose strings and privacy manifest (spec C5, rows
 * R33-R38; ruling A11: the inventory doc is the REPO-ROOT
 * docs/privacy-data-inventory.md).
 *
 * The executed-plugin compile mirrors config/nativeBundle.w37.test.ts a6
 * (installed plugins, in memory, introspect: true, nothing written).
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const APP = path.resolve(__dirname, '../..');
const REPO = path.resolve(APP, '..');
const INVENTORY_DOC = path.join(REPO, 'docs', 'privacy-data-inventory.md');
const FX = require('../fixtures/b3a_copy.json') as {
  native: { en: Record<string, string>; ar: Record<string, string> };
};

const readJson = (p: string): any => JSON.parse(fs.readFileSync(p, 'utf8'));
const loadExpo = (): any => readJson(path.join(APP, 'app.json')).expo;
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v));
const sha = (s: string) => crypto.createHash('sha256').update(s, 'utf8').digest('hex');

const CAM_EN = FX.native.en.NSCameraUsageDescription;
const PHOTOS_EN = FX.native.en.NSPhotoLibraryUsageDescription;
const OPENAI_AR = 'أوبن إيه آي';
const SERVERS_AR = 'خوادم';

function pluginOptions(expo: any, name: string): Record<string, unknown> | undefined {
  const entry = (expo.plugins as unknown[]).find((p) => (Array.isArray(p) ? p[0] === name : p === name));
  if (entry === undefined) return undefined;
  return Array.isArray(entry) ? ((entry[1] ?? {}) as Record<string, unknown>) : {};
}

const reqFromApp = (m: string): any => require(require.resolve(m, { paths: [APP] }));
type PluginName = 'expo-camera' | 'expo-image-picker';

async function compilePlist(expo: any, order: PluginName[]): Promise<Record<string, unknown>> {
  const withCamera = reqFromApp('expo-camera/app.plugin.js').default;
  const withImagePicker = reqFromApp('expo-image-picker/app.plugin.js').default;
  let config: any = clone(expo);
  config._internal = { projectRoot: APP, isDebug: false };
  for (const name of order) {
    const plugin = name === 'expo-camera' ? withCamera : withImagePicker;
    config = plugin(config, pluginOptions(config, name) ?? {});
  }
  const modRequest = { projectRoot: APP, platformProjectRoot: APP, projectName: 'Qaren', introspect: true };
  const ios = await config.mods.ios.infoPlist({
    ...config,
    modRequest: { ...modRequest, platform: 'ios', modName: 'infoPlist' },
    modResults: {},
  });
  return ios.modResults;
}

const P = 'NSPrivacyCollectedDataTypePurpose';
const T = 'NSPrivacyCollectedDataType';
const OTHER = `${P}Other`;
const FIVE = ['PhotosorVideos', 'OtherUserContent', 'SearchHistory', 'ProductInteraction', 'OtherDataTypes'];
// The base purposes of the other 8 types (b965c63b), frozen.
const FROZEN_OTHERS: Record<string, string[]> = {
  EmailAddress: ['AppFunctionality'],
  Name: ['AppFunctionality'],
  UserID: ['AppFunctionality', 'Analytics'],
  DeviceID: ['AppFunctionality'],
  CrashData: ['AppFunctionality'],
  PerformanceData: ['AppFunctionality', 'Analytics'],
  OtherDiagnosticData: ['AppFunctionality'],
  CustomerSupport: ['AppFunctionality'],
};
// Base purposes of the five (before Other is appended), frozen.
const FROZEN_FIVE_BASE: Record<string, string[]> = {
  PhotosorVideos: ['AppFunctionality'],
  OtherUserContent: ['AppFunctionality', 'Analytics'],
  SearchHistory: ['AppFunctionality', 'Analytics', 'ProductPersonalization'],
  ProductInteraction: ['Analytics', 'ProductPersonalization'],
  OtherDataTypes: ['ProductPersonalization', 'AppFunctionality'],
};

function manifestEntries(): any[] {
  return loadExpo().ios.privacyManifests.NSPrivacyCollectedDataTypes;
}
const purposesOf = (e: any): string[] => (e.NSPrivacyCollectedDataTypePurposes as string[]).map((p) => p.replace(P, ''));
const typeOf = (e: any): string => String(e.NSPrivacyCollectedDataType).replace(T, '');

describe('B3-A purpose strings and privacy manifest (C5)', () => {
  it('r33 plugin options carry the new purpose strings', () => {
    const expo = loadExpo();
    expect(pluginOptions(expo, 'expo-camera')?.cameraPermission).toBe(CAM_EN);
    expect(pluginOptions(expo, 'expo-image-picker')?.photosPermission).toBe(PHOTOS_EN);
    for (const s of [CAM_EN, PHOTOS_EN]) {
      expect(s).toContain('servers');
      expect(s).toContain('OpenAI');
    }
  });

  it('r34 locale files carry the new strings (en == plugin strings, ar == fixture)', () => {
    const en = readJson(path.join(APP, 'locales', 'en.json')).ios;
    const ar = readJson(path.join(APP, 'locales', 'ar.json')).ios;
    expect(en.NSCameraUsageDescription).toBe(CAM_EN);
    expect(en.NSPhotoLibraryUsageDescription).toBe(PHOTOS_EN);
    expect(ar.NSCameraUsageDescription === FX.native.ar.NSCameraUsageDescription).toBe(true);
    expect(ar.NSPhotoLibraryUsageDescription === FX.native.ar.NSPhotoLibraryUsageDescription).toBe(true);
    for (const s of [ar.NSCameraUsageDescription, ar.NSPhotoLibraryUsageDescription]) {
      expect(String(s).includes(OPENAI_AR)).toBe(true);
      expect(String(s).includes(SERVERS_AR)).toBe(true);
    }
  });

  it('r35 executed plugins write them into Info.plist (both plugin orders)', async () => {
    for (const order of [
      ['expo-camera', 'expo-image-picker'],
      ['expo-image-picker', 'expo-camera'],
    ] as PluginName[][]) {
      const plist = await compilePlist(loadExpo(), order);
      expect({ order, cam: plist.NSCameraUsageDescription }).toEqual({ order, cam: CAM_EN });
      expect({ order, photos: plist.NSPhotoLibraryUsageDescription }).toEqual({ order, photos: PHOTOS_EN });
    }
  });

  it('r36 the five label types declare PurposeOther and nothing else moves', () => {
    const entries = manifestEntries();
    const byType: Record<string, string[]> = {};
    for (const e of entries) byType[typeOf(e)] = purposesOf(e);
    for (const t of FIVE) {
      expect({ t, has: (byType[t] ?? []).includes('Other') }).toEqual({ t, has: true });
      const rest = (byType[t] ?? []).filter((p) => p !== 'Other').sort();
      expect({ t, rest }).toEqual({ t, rest: [...FROZEN_FIVE_BASE[t]].sort() });
    }
    for (const [t, frozen] of Object.entries(FROZEN_OTHERS)) {
      expect({ t, purposes: [...(byType[t] ?? [])].sort() }).toEqual({ t, purposes: [...frozen].sort() });
    }
    const withOther = entries.filter((e) => (e.NSPrivacyCollectedDataTypePurposes as string[]).includes(OTHER));
    expect(withOther.map(typeOf).sort()).toEqual([...FIVE].sort());
    expect(entries).toHaveLength(13);
  });

  it('r37 the repo-root inventory doc lists Other for the same five rows and its json fence equals app.json', () => {
    expect(fs.existsSync(INVENTORY_DOC)).toBe(true);
    const md = fs.readFileSync(INVENTORY_DOC, 'utf8');
    const start = md.indexOf('\n## Collected data types');
    expect(start).toBeGreaterThanOrEqual(0);
    const rest = md.slice(start + 1);
    const end = rest.indexOf('\n## ');
    const section = end === -1 ? rest : rest.slice(0, end);
    const rows = section.split(/\r?\n/).filter((l) => /^\|\s*\d+\s*\|/.test(l));
    const rowFor: Record<string, string> = {};
    for (const line of rows) {
      const cells = line.split(/(?<!\\)\|/).slice(1, -1).map((c) => c.trim());
      const m = cells[1].match(/^`([A-Z][A-Za-z]+)`$/);
      if (m) rowFor[m[1]] = cells[5].replace(/\([^)]*\)/g, '');
    }
    for (const t of FIVE) {
      const purposes = (rowFor[t] ?? '').split(',').map((p) => p.trim());
      expect({ t, other: purposes.includes('Other') }).toEqual({ t, other: true });
    }
    for (const t of Object.keys(FROZEN_OTHERS)) {
      const purposes = (rowFor[t] ?? '').split(',').map((p) => p.trim());
      expect({ t, other: purposes.includes('Other') }).toEqual({ t, other: false });
    }
    const fence = md.match(/```json\s*\r?\n([\s\S]*?)\r?\n```/);
    expect(fence).not.toBeNull();
    const fromDoc = JSON.parse((fence as RegExpMatchArray)[1]);
    const byT = (a: any, b: any) => String(a[`${T}`]).localeCompare(String(b[`${T}`]));
    expect([...fromDoc].sort(byT)).toEqual([...manifestEntries()].sort(byT));
  });

  it('r38 [PIN] microphone strings and display names unchanged', () => {
    const en = readJson(path.join(APP, 'locales', 'en.json')).ios;
    const ar = readJson(path.join(APP, 'locales', 'ar.json')).ios;
    const expo = loadExpo();
    const MIC = 'MYEZ only uses the camera to photograph products. Audio is never recorded.';
    expect(en.NSMicrophoneUsageDescription).toBe(MIC);
    expect(en.CFBundleDisplayName).toBe('MYEZ');
    expect(sha(ar.NSMicrophoneUsageDescription)).toBe('999e6f18ca99fd26be8cea763ac2820571d56f8ef910a4c069280ca2eece1832');
    expect(sha(ar.CFBundleDisplayName)).toBe('5d3c4d53670e83071d072f82b67c47a7e82a92ba4e0ee00dbf2afaa145583ac6');
    expect(pluginOptions(expo, 'expo-camera')?.microphonePermission).toBe(MIC);
    expect(pluginOptions(expo, 'expo-image-picker')?.microphonePermission).toBe(MIC);
    expect(Object.keys(en).sort()).toEqual(
      ['CFBundleDisplayName', 'NSCameraUsageDescription', 'NSMicrophoneUsageDescription', 'NSPhotoLibraryUsageDescription'],
    );
  });
});

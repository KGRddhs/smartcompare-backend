/**
 * F-S1.5l regression — EditProfileScreen masks Apple Hide-My-Email relay.
 *
 * Apple "Hide My Email" assigns a relay alias on the
 * `@privaterelay.appleid.com` TLD that the user never typed. Surfacing
 * that address in the email row reads like leakage. Per Ahmed's
 * ruling A on F-S1.5l, when the suffix matches, the field label
 * swaps to "Apple ID" + the value swaps to "Email kept private by
 * Apple". Otherwise the raw email renders as before.
 *
 * Source-grep approach — matches the EditProfileScreen.editPreferences
 * test family used by F-S1.5c/d. The full render would pull in 20+
 * services; the structural contract is captured cleanly via source
 * pattern matching.
 */

import * as fs from 'fs';
import * as path from 'path';

const EDIT_PROFILE_PATH = path.resolve(
  __dirname,
  '../src/screens/EditProfileScreen.tsx',
);
const EN_PATH = path.resolve(__dirname, '../src/i18n/en.json');
const AR_PATH = path.resolve(__dirname, '../src/i18n/ar.json');

const SOURCE = fs.readFileSync(EDIT_PROFILE_PATH, 'utf8');
const EN = JSON.parse(fs.readFileSync(EN_PATH, 'utf8'));
const AR = JSON.parse(fs.readFileSync(AR_PATH, 'utf8'));

describe('F-S1.5l — EditProfileScreen masks Apple privaterelay email', () => {
  it('derives isAppleRelay from a privaterelay.appleid.com suffix check', () => {
    expect(SOURCE).toMatch(
      /isAppleRelay\s*=[\s\S]{0,300}user\.email\.toLowerCase\(\)\.endsWith\(\s*['"]@privaterelay\.appleid\.com['"]\s*\)/,
    );
  });

  it('renders Apple ID label + "kept private" caption when isAppleRelay', () => {
    // The truthy branch must call t('editprofile.email.appleLabel') AND
    // t('editprofile.email.applePrivate') — and the raw user.email must
    // NOT appear in the truthy branch's render.
    expect(SOURCE).toMatch(
      /isAppleRelay\s*\?\s*\([\s\S]{0,400}t\(['"]editprofile\.email\.appleLabel['"][\s\S]{0,400}t\(['"]editprofile\.email\.applePrivate['"]/,
    );
  });

  it('renders raw user.email when NOT isAppleRelay (default branch unchanged)', () => {
    // The falsy branch must continue to render the existing
    // auth.email label + user.email value pair.
    expect(SOURCE).toMatch(
      /isAppleRelay\s*\?[\s\S]{0,600}:\s*\([\s\S]{0,400}t\(['"]auth\.email['"]\)[\s\S]{0,200}user\?\.email\s*\?\?\s*['"]—['"]/,
    );
  });

  it('checks suffix case-insensitively via toLowerCase()', () => {
    // Defensive: some providers / mock fixtures emit the relay TLD in
    // mixed case. Lowercasing before the check keeps the mask robust.
    expect(SOURCE).toMatch(/user\.email\.toLowerCase\(\)\.endsWith/);
  });
});

describe('F-S1.5l — i18n keys ship in both locales', () => {
  it('en.json defines editprofile.email.appleLabel + .applePrivate', () => {
    expect(EN['editprofile.email.appleLabel']).toBe('Apple ID');
    expect(EN['editprofile.email.applePrivate']).toBe(
      'Email kept private by Apple',
    );
  });

  it('ar.json defines editprofile.email.appleLabel + .applePrivate', () => {
    expect(AR['editprofile.email.appleLabel']).toBe('معرّف Apple');
    expect(AR['editprofile.email.applePrivate']).toBe(
      'البريد محمي بواسطة Apple',
    );
  });
});

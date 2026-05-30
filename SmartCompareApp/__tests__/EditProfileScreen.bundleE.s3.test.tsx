/**
 * EditProfileScreen Bundle E S3 — REWRITE element-order + DELETE-list contract.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/
 *                  EditProfileScreen.jsx (1-233).
 * Element-order checklist: docs/plans/_s3-a1-element-order.md.
 *
 * S3 REWRITE deltas (per A1.1 audit):
 *   - Save CTA moved OUT of ScrollView to a sticky bottom slot
 *     [JSX:210-228]
 *   - Eyebrow split: "Account actions" wraps the Delete card; old
 *     "Danger zone" eyebrow label retired [JSX:193]
 *   - Delete card wraps the destructive row in a bordered card with a
 *     Trash icon-circle on the left [JSX:194-206]
 *   - Edit style profile NavRow gets a Star icon-circle on the left +
 *     a sub-text caption "Update priorities, budget, and brand stance"
 *     [JSX:122-148, 187-191]
 *   - Apple Hide-My-Email relay mask preserved from S2 6b2be83
 */

import * as fs from 'fs';
import * as path from 'path';

const EDIT_PATH = path.resolve(__dirname, '../src/screens/EditProfileScreen.tsx');
const EN_LOCALE_PATH = path.resolve(__dirname, '../src/i18n/en.json');

let editSrc: string;
let enLocale: Record<string, string>;

beforeAll(() => {
  editSrc = fs.readFileSync(EDIT_PATH, 'utf8');
  enLocale = JSON.parse(fs.readFileSync(EN_LOCALE_PATH, 'utf8'));
});

describe('EditProfileScreen S3 — JSX:210-228 sticky bottom Save CTA', () => {
  it('Save CTA is at the SafeAreaView level (sibling to ScrollView, not inside)', () => {
    // The Save TouchableOpacity must be OUTSIDE the <ScrollView>. We
    // assert that by matching the structural pattern: </ScrollView> ...
    // <TouchableOpacity ... testID="edit-save-cta" or accessibilityLabel
    // matching the Save i18n key.
    const closingScroll = editSrc.lastIndexOf('</ScrollView>');
    const saveCtaIdx = editSrc.indexOf('testID="edit-save-cta"');
    expect(closingScroll).toBeGreaterThan(0);
    expect(saveCtaIdx).toBeGreaterThan(0);
    // Save CTA must come AFTER the closing ScrollView tag.
    expect(saveCtaIdx).toBeGreaterThan(closingScroll);
  });

  it('Save CTA host has a top hairline border (sticky-bottom signature)', () => {
    // The sticky-footer wrapper carries borderTopWidth + bg.primary.
    const m = editSrc.match(/saveStickyHost\s*:\s*\{[^}]+\}/);
    expect(m).toBeTruthy();
    expect(m![0]).toMatch(/borderTop(Width)?/);
  });
});

describe('EditProfileScreen S3 — JSX:193-206 "Account actions" eyebrow + Delete card', () => {
  it('renders editProfile.section.accountActions eyebrow label', () => {
    // JSX:193 has eyebrow "Account actions" — i18n surface must include
    // an editProfile.section.accountActions key.
    expect(enLocale['editProfile.section.accountActions']).toBeDefined();
    expect(editSrc).toMatch(/editProfile\.section\.accountActions/);
  });

  it('Delete is wrapped in a bordered card (deleteCard style block)', () => {
    const m = editSrc.match(/deleteCard\s*:\s*\{[^}]+\}/);
    expect(m).toBeTruthy();
    expect(m![0]).toMatch(/border(Width|Color)/);
    expect(m![0]).toMatch(/borderRadius/);
  });

  it('Delete row gets a Trash icon (lucide Trash2 import + render)', () => {
    expect(editSrc).toMatch(/\bTrash2\b/);
  });
});

describe('EditProfileScreen S3 — JSX:122-148 Edit-style-profile NavRow w/ Star + sub', () => {
  it('imports lucide Star icon for the linkRow icon-circle', () => {
    expect(editSrc).toMatch(/\bStar\b/);
  });

  it('renders editProfile.editStyleProfile.sub caption', () => {
    expect(enLocale['editProfile.editStyleProfile.sub']).toBeDefined();
    expect(editSrc).toMatch(/editProfile\.editStyleProfile\.sub/);
  });
});

describe('EditProfileScreen S3 — Apple Hide-My-Email relay mask preserved (S2 6b2be83)', () => {
  it('keeps the privaterelay.appleid.com suffix check', () => {
    expect(editSrc).toMatch(/@privaterelay\.appleid\.com/);
  });

  it('keeps the editprofile.email.appleLabel i18n key', () => {
    expect(editSrc).toMatch(/editprofile\.email\.appleLabel/);
  });
});

describe('EditProfileScreen S3 — Build Principle #4 (no scary copy / motion)', () => {
  it('contains no shake / wobble / jitter / bounce in source', () => {
    const stripped = editSrc
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/.*$/gm, '');
    const banned = ['shake', 'wobble', 'jitter', 'bounce'];
    for (const w of banned) {
      expect(stripped.toLowerCase()).not.toContain(w);
    }
  });

  it('contains no scary copy strings as raw text', () => {
    const lower = editSrc.toLowerCase();
    expect(lower).not.toMatch(/'failed to/);
    expect(lower).not.toMatch(/'try again/);
    expect(lower).not.toMatch(/"failed to/);
    expect(lower).not.toMatch(/"try again/);
  });
});

describe('EditProfileScreen S3 — i18n parity', () => {
  it('editProfile.section.accountActions present in en + ar', () => {
    const arPath = path.resolve(__dirname, '../src/i18n/ar.json');
    const ar = JSON.parse(fs.readFileSync(arPath, 'utf8'));
    expect(enLocale['editProfile.section.accountActions']).toBeDefined();
    expect(ar['editProfile.section.accountActions']).toBeDefined();
  });

  it('editProfile.editStyleProfile.sub present in en + ar', () => {
    const arPath = path.resolve(__dirname, '../src/i18n/ar.json');
    const ar = JSON.parse(fs.readFileSync(arPath, 'utf8'));
    expect(enLocale['editProfile.editStyleProfile.sub']).toBeDefined();
    expect(ar['editProfile.editStyleProfile.sub']).toBeDefined();
  });
});

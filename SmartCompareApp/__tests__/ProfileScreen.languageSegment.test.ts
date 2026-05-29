/**
 * F-S1.5n regression — ProfileScreen Language EN/عر toggle animates
 * with motion.modeSegment.
 *
 * The legacy ACCOUNT-group right slot rendered two TouchableOpacity
 * buttons with an active-color background swap — instant snap. This
 * fix swaps the inline JSX for an inline LanguageSegment component
 * that drives a sliding pill via Reanimated using motion.modeSegment
 * (180ms, cubic-bezier 0.32 0.72 0 1) and interpolates text colors
 * with the pill position. Light haptic fires on flip.
 *
 * Source-grep approach — matches the family used by Profile.bundleA
 * etc. Full render would pull in Reanimated test wiring + 20+
 * services; structural contract pinned via source matching.
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');
const MOTION_PATH = path.resolve(__dirname, '../src/theme/motion.ts');

const SOURCE = fs.readFileSync(PROFILE_PATH, 'utf8');
const MOTION_SRC = fs.readFileSync(MOTION_PATH, 'utf8');

describe('F-S1.5n — ProfileScreen language toggle animation contract', () => {
  it('imports the reanimated helpers used by the LanguageSegment', () => {
    expect(SOURCE).toMatch(
      /import\s+Animated[\s\S]{0,400}useSharedValue[\s\S]{0,200}useAnimatedStyle[\s\S]{0,200}withTiming[\s\S]{0,200}interpolateColor[\s\S]{0,200}['"]react-native-reanimated['"]/,
    );
  });

  it('imports motion tokens + expo-haptics', () => {
    expect(SOURCE).toMatch(
      /import\s*\{\s*motion\s*\}\s*from\s*['"]\.\.\/theme\/motion['"]/,
    );
    expect(SOURCE).toMatch(
      /import\s*\*\s*as\s+Haptics\s+from\s+['"]expo-haptics['"]/,
    );
  });

  it('defines an inline LanguageSegment that drives the slide via motion.modeSegment', () => {
    expect(SOURCE).toMatch(/function\s+LanguageSegment\s*\(/);
    // The slide animation must be tied to the spec'd token, not a
    // hand-rolled duration / easing.
    expect(SOURCE).toMatch(
      /withTiming\([\s\S]{0,200}motion\.modeSegment\s*\)/,
    );
  });

  it('interpolates EN + AR text colors across the same progress value', () => {
    // Two useAnimatedStyle blocks for the two text labels, both
    // using interpolateColor on the shared progress signed value.
    const interpHits = SOURCE.match(/interpolateColor\(\s*progress\.value/g) ?? [];
    expect(interpHits.length).toBeGreaterThanOrEqual(2);
  });

  it('fires a light haptic on flip (no warning / error / heavy)', () => {
    // Build Principle #4: confidence-only haptic vocab. The segment
    // must use ImpactFeedbackStyle.Light (matches motion.haptic.chip).
    expect(SOURCE).toMatch(
      /Haptics\.impactAsync\(\s*Haptics\.ImpactFeedbackStyle\.Light\s*\)/,
    );
    expect(SOURCE).not.toMatch(
      /Haptics\.notificationAsync\(\s*Haptics\.NotificationFeedbackType\.(Warning|Error)/,
    );
    expect(SOURCE).not.toMatch(/ImpactFeedbackStyle\.Heavy/);
  });

  it('preserves the switchLanguage call site (underlying RTL behavior unchanged)', () => {
    // The animation polish must NOT change which function actually
    // flips locale + I18nManager.forceRTL — that lives inside
    // useLanguage().switchLanguage.
    expect(SOURCE).toMatch(/onChange=\{\s*switchLanguage\s*\}/);
  });

  it('exposes stable testIDs for spot-check + future a11y / e2e tests', () => {
    expect(SOURCE).toMatch(/testID=['"]profile-language-segment['"]/);
    expect(SOURCE).toMatch(/testID=['"]profile-language-en['"]/);
    expect(SOURCE).toMatch(/testID=['"]profile-language-ar['"]/);
  });

  it('motion.modeSegment token defines the contract this fix consumes', () => {
    // Sanity: the token is what we say it is. If a future commit
    // re-tunes motion.modeSegment, this assertion surfaces the change
    // so the language-segment animation re-validates against it.
    expect(MOTION_SRC).toMatch(/modeSegment\s*:\s*\{[\s\S]{0,200}duration:\s*180/);
    expect(MOTION_SRC).toMatch(
      /modeSegment\s*:\s*\{[\s\S]{0,200}Easing\.bezier\(\s*0\.32\s*,\s*0\.72\s*,\s*0\s*,\s*1\s*\)/,
    );
  });
});

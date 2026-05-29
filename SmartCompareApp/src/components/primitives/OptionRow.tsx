/**
 * OptionRow — Bundle E S0.3 primitive (extended F-S2.W1).
 *
 * Cal-AI-Lite option row used across multiple onboarding steps:
 *   - Step04Country (icon-circle with flag emoji + sub line)
 *   - Step08Priorities (icon-circle style, multi-select max 3)
 *   - Step06Age / Step07Gender / Step09Budget / Step10BrandAttitude /
 *     Step11Attribution (icon-circle OR plain depending on category)
 *
 * style='icon-circle' renders a 36px circle to the left of the label.
 * If `option.icon` is set the glyph renders centered inside the circle
 * (single Text — emoji or symbol). style='plain' is the bare row (no
 * circle). Active state inverts background to bg.inverse (black-on-
 * select per Cal-AI pattern).
 *
 * `option.sub` renders as a secondary 13/400 line below the label when
 * present (e.g. "Capital, Muharraq, Northern, Southern" under "Bahrain"
 * on Step04Country).
 *
 * F-S2.W1 extension contract — both new fields are OPTIONAL and
 * backward-compat: existing callers that pass only {key, label} render
 * identically (empty circle, single label line, no sub). The new
 * rendering only kicks in when option.icon or option.sub is supplied.
 *
 * Contract: __tests__/primitives/OptionRow.test.tsx
 *   - testID forwarded to the Pressable root
 *   - testID="option-row-icon-circle" only when style='icon-circle'
 *   - icon circle is 36x36
 *   - onToggle called with option.key on press
 *   - accessibilityState.selected mirrors `active`
 */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

interface OptionData {
  key: string;
  label: string;
  // F-S2.W1: when style='icon-circle' and `icon` is set, it renders
  // inside the 36px circle as a centered Text glyph (emoji or symbol).
  // When unset, the circle remains empty per pre-S2 behavior.
  icon?: string;
  // F-S2.W1: optional secondary line rendered below `label` in
  // text.secondary 13/400. Used by Step04Country governorate hint and
  // future steps that need a sub-line.
  sub?: string;
}

interface Props {
  option: OptionData;
  active: boolean;
  onToggle: (key: string) => void;
  style: 'icon-circle' | 'plain';
  testID?: string;
}

const CIRCLE_SIZE = 36;

export function OptionRow({ option, active, onToggle, style, testID }: Props) {
  const handlePress = () => onToggle(option.key);
  const hasIcon = style === 'icon-circle' && !!option.icon;
  return (
    <Pressable
      onPress={handlePress}
      style={[styles.row, active ? styles.rowActive : styles.rowInactive]}
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      accessibilityLabel={option.label}
    >
      {style === 'icon-circle' ? (
        <View
          style={[styles.circle, active ? styles.circleActive : null]}
          testID="option-row-icon-circle"
        >
          {hasIcon ? (
            <Text style={styles.iconGlyph} testID="option-row-icon-glyph">
              {option.icon}
            </Text>
          ) : null}
        </View>
      ) : null}
      <View style={styles.textCol}>
        <Text style={[styles.label, active ? styles.labelActive : null]}>
          {option.label}
        </Text>
        {option.sub ? (
          <Text
            style={[styles.sub, active ? styles.subActive : null]}
            testID="option-row-sub"
          >
            {option.sub}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
  },
  rowInactive: {
    backgroundColor: colors.bg.primary,
    borderColor: colors.border.light,
  },
  rowActive: {
    backgroundColor: colors.bg.inverse,
    borderColor: colors.bg.inverse,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circleActive: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  iconGlyph: {
    // 22px keeps emoji-rendered flags + symbol glyphs readable inside
    // the 36px circle without clipping. Centered via the parent's
    // alignItems/justifyContent above.
    fontSize: 22,
    lineHeight: 26,
  },
  textCol: {
    flex: 1,
    minWidth: 0,
  },
  label: {
    fontSize: 15,
    fontWeight: '500',
    lineHeight: 15 * 1.4,
    color: colors.text.primary,
  },
  labelActive: {
    color: colors.text.onInverse,
  },
  sub: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.4,
    color: colors.text.secondary,
    marginTop: 2,
  },
  subActive: {
    // Active state uses a lighter shade so the sub stays legible against
    // the bg.inverse fill without going full onInverse (which would
    // make the secondary line indistinguishable from the primary).
    color: 'rgba(255,255,255,0.7)',
  },
});

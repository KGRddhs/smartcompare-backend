/**
 * OptionRow — Bundle E S0.3 primitive (extended F-S2.W1 + F-S2.W2).
 *
 * Cal-AI-Lite option row used across multiple onboarding steps:
 *   - Step04Country (icon-circle with flag emoji + sub line)
 *   - Step08Priorities (icon-circle with lucide-react-native SVG glyphs)
 *   - Step06Age / Step07Gender / Step09Budget / Step10BrandAttitude /
 *     Step11Attribution (icon-circle OR plain depending on category)
 *
 * style='icon-circle' renders a 36px circle to the left of the label.
 * If `option.icon` is set:
 *   - string (emoji or symbol) → rendered as centered <Text> glyph
 *   - ReactNode (e.g. lucide-react-native <Award size={20} />) →
 *     rendered directly inside the circle, centered
 * style='plain' is the bare row (no circle). Active state inverts
 * background to bg.inverse (black-on-select per Cal-AI pattern).
 *
 * `option.sub` renders as a secondary 13/400 line below the label when
 * present (e.g. "Capital, Muharraq, Northern, Southern" under "Bahrain"
 * on Step04Country).
 *
 * F-S2.W1 extension contract — both `icon` and `sub` are OPTIONAL and
 * backward-compat: existing callers that pass only {key, label} render
 * identically (empty circle, single label line, no sub).
 *
 * F-S2.W2 extension — `icon` now accepts ReactNode in addition to
 * string. Symmetric with PrivacyRow's ReactNode icon. Zero breaking
 * change to Step04Country (still passes flag emoji as string). Enables
 * Step08Priorities to use lucide-react-native SVG glyphs.
 *
 * Contract: __tests__/primitives/OptionRow.test.tsx
 *   - testID forwarded to the Pressable root
 *   - testID="option-row-icon-circle" only when style='icon-circle'
 *   - icon circle is 36x36
 *   - onToggle called with option.key on press
 *   - accessibilityState.selected mirrors `active`
 *   - testID="option-row-icon-glyph" only when icon is a string
 *   - testID="option-row-icon-node" only when icon is a ReactNode
 */
import React, { ReactNode, isValidElement } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

interface OptionData {
  key: string;
  label: string;
  // F-S2.W1 + F-S2.W2: when style='icon-circle' and `icon` is set, it
  // renders inside the 36px circle. String → centered <Text> glyph
  // (emoji/symbol). ReactNode → rendered directly (e.g. lucide icon).
  // When unset, the circle remains empty per pre-S2 behavior.
  icon?: string | ReactNode;
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
  const hasIcon = style === 'icon-circle' && option.icon != null;
  // String icon → wrap in <Text> for emoji/symbol; ReactNode → render
  // node directly. isValidElement guards against falsy/string here so
  // the type narrowing stays explicit for downstream readers.
  const iconIsNode = hasIcon && isValidElement(option.icon);
  const iconIsString = hasIcon && typeof option.icon === 'string';
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
          {iconIsString ? (
            <Text style={styles.iconGlyph} testID="option-row-icon-glyph">
              {option.icon as string}
            </Text>
          ) : iconIsNode ? (
            <View testID="option-row-icon-node">{option.icon}</View>
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

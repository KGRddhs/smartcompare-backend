/**
 * PersonalizationChip — Bundle C spec § 7a + § 7c.
 *
 * Compact single-line chip rendered BELOW the verdict text. Surfaces up
 * to 3 direction arrows reflecting the strongest shifts vs category
 * defaults. Arrows-only — direction (↑/↓), NEVER percentages, NEVER
 * coefficients, NEVER cap math (per project rule "no backend internals
 * in user-facing reveals" + spec § 7a).
 *
 * Hidden when:
 *  - `appliedShifts` is undefined (no priorities set upstream).
 *  - `appliedShifts` is empty (no significant shifts to surface).
 *
 * Spec § 7d — CohortBadge stays SEPARATE. Do not merge here.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, typography, radii } from '../../theme';

interface Shift {
  dim_display: string;
  direction: 'up' | 'down';
}

interface Props {
  appliedShifts: Shift[] | undefined;
  testID?: string;
}

export function PersonalizationChip({ appliedShifts, testID = 'personalization-chip' }: Props) {
  const { t } = useTranslation();

  if (!appliedShifts || appliedShifts.length === 0) return null;

  // Cap to 3 strongest shifts per spec § 7a. Backend pre-sorts by
  // absolute magnitude so `.slice(0, 3)` is the right call.
  const top3 = appliedShifts.slice(0, 3);

  // Arrow glyphs composed directly (not via t()) so the rendered chip
  // shows ↑/↓ + dim label even when i18n mock returns keys verbatim.
  // The shape mirrors the i18n template `↑ {{dim}}` / `↓ {{dim}}`.
  const arrows = top3
    .map((s) => {
      const dim = s.dim_display.replace(/_/g, ' ');
      const arrow = s.direction === 'up' ? '\u2191' : '\u2193';
      return `${arrow} ${dim}`;
    })
    .join(' \u00b7 ');

  // i18n key still drives the wrapper copy ("Weighted ... (based on your
  // priorities)"). The arrows live as a separate Text child so they
  // appear in the rendered tree even when the test mock returns
  // template keys verbatim without interpolation.
  const wrapper = t('results.personalization.chip_template', { arrows: '\u200B' });
  // Split on the zero-width-space placeholder — gives ["Weighted ", " (based on your priorities)"]
  // for real mock OR the full key string (we render arrows as a trailing sibling either way).
  const [before, after] = wrapper.split('\u200B');

  return (
    <View style={styles.chip} testID={testID}>
      <Text style={styles.text}>
        {before ? <Text>{before}</Text> : null}
        <Text testID={`${testID}-arrows`}>{arrows}</Text>
        {after ? <Text>{after}</Text> : null}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    backgroundColor: colors.bg.secondary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.chip,
    alignSelf: 'flex-start',
    marginTop: spacing.sm,
  },
  text: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});

// Dual export: named (preferred) + default. The default keeps
// test-bundle-c's `require(...).default` pattern working without
// forcing them to rebase on a named-import contract.
export default PersonalizationChip;

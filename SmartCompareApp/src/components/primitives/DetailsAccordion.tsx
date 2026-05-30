/**
 * DetailsAccordion — Bundle E S0.3 primitive.
 *
 * Three-section accordion used at the bottom of ResultsScreen
 * (Reviews / Pros & Cons / Specs). Each section has an icon-circle on the
 * left, the label + sub-line in the middle, and a chevron on the right
 * that rotates 0° → 180° (220ms ease via motion.accordionChevron) when the
 * section expands.
 *
 * Single-open invariant: opening section B collapses A. This keeps the
 * results below the fold predictable for screen readers + tests.
 *
 * Contract: __tests__/primitives/DetailsAccordion.test.tsx
 *   - All section headers render
 *   - Tapping a header reveals body content
 *   - Opening one collapses the previously-open one
 *   - testID="accordion-chevron-{key}" exposes each chevron with
 *     style.transform=[{ rotate: 'Ndeg' }] mirroring open state
 */
import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

export interface AccordionSection {
  key: string;
  label: string;
  sub?: string;
  icon: string;
  body: React.ReactNode;
}

interface Props {
  sections: AccordionSection[];
  testID?: string;
}

export function DetailsAccordion({ sections, testID }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  const toggle = (key: string) => setOpenKey((prev) => (prev === key ? null : key));

  return (
    <View style={styles.wrap} testID={testID}>
      {sections.map((section) => {
        const isOpen = openKey === section.key;
        const rotate = isOpen ? '180deg' : '0deg';
        return (
          <View key={section.key} style={styles.section}>
            <Pressable
              onPress={() => toggle(section.key)}
              style={styles.header}
              accessibilityRole="button"
              accessibilityState={{ expanded: isOpen }}
              accessibilityLabel={section.label}
            >
              <View style={styles.iconCircle} />
              <View style={styles.headerText}>
                <Text style={styles.label}>{section.label}</Text>
                {section.sub ? <Text style={styles.sub}>{section.sub}</Text> : null}
              </View>
              <View
                style={[styles.chevron, { transform: [{ rotate }] }]}
                testID={`accordion-chevron-${section.key}`}
              >
                <View style={styles.chevronGlyph} />
              </View>
            </Pressable>
            {isOpen ? <View style={styles.body}>{section.body}</View> : null}
          </View>
        );
      })}
    </View>
  );
}

const ICON_SIZE = 36;
const CHEV_SIZE = 24;

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.md,
  },
  section: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.base,
  },
  iconCircle: {
    width: ICON_SIZE,
    height: ICON_SIZE,
    borderRadius: ICON_SIZE / 2,
    backgroundColor: colors.accentLight,
  },
  headerText: {
    flex: 1,
    minWidth: 0,
  },
  label: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 15 * 1.3,
    color: colors.text.primary,
  },
  sub: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.4,
    color: colors.text.secondary,
    marginTop: 2,
  },
  chevron: {
    width: CHEV_SIZE,
    height: CHEV_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chevronGlyph: {
    width: 10,
    height: 10,
    borderRightWidth: 2,
    borderBottomWidth: 2,
    borderColor: colors.text.secondary,
    transform: [{ rotate: '45deg' }],
  },
  body: {
    paddingHorizontal: spacing.base,
    paddingBottom: spacing.base,
  },
});

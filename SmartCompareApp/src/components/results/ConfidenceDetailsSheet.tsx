/**
 * ConfidenceDetailsSheet — Bundle C spec § 5b, adapted for #105.
 *
 * "What we know" bottom sheet. Renders 1-3 factual lines for the tapped
 * confidence leg. The backend ships `scoring_v2.confidence_details` as
 * per-leg evidence DICTS (see `confidenceDetailsLines.ts`); the
 * `toConfidenceLines` adapter localizes them app-side (the app owns
 * EN/AR; the backend has no locale in scope). A legacy string[] leg still
 * renders verbatim, and any other shape renders an honest empty sheet —
 * never a throw.
 *
 * Critical rules absorbed:
 *  - Rule #2 (NO backend internals): no thresholds, coefficients, cap
 *    percentages, or shift math. Defended by a regex in the test file.
 *  - Rule #5 (no scary copy): English forbidden vocab + Arabic forbidden
 *    vocab guarded the same way.
 *
 * Bottom-sheet pattern mirrors `DemographicsBottomSheet.tsx`: native
 * `Modal` with `transparent` + `slide` animation + a dim backdrop +
 * a flex-end container so the sheet docks to the bottom of the screen.
 */
import React from 'react';
import { View, Text, Modal, StyleSheet, ScrollView, TouchableOpacity, Pressable } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, radii, typography } from '../../theme';
import type { ConfidenceDetails } from '../../types/types';
import { toConfidenceLines } from './confidenceDetailsLines';

export type ConfidenceLeg = 'price' | 'reviews' | 'specs';

interface Props {
  visible: boolean;
  leg: ConfidenceLeg;
  details: ConfidenceDetails;
  onClose: () => void;
  testID?: string;
}

export function ConfidenceDetailsSheet({ visible, leg, details, onClose, testID = 'confidence-sheet' }: Props) {
  const { t } = useTranslation();
  const lines = toConfidenceLines(leg, details, t);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      testID={testID}
    >
      <Pressable style={styles.backdrop} onPress={onClose} testID={`${testID}-backdrop`} />
      <View style={styles.sheet} testID={`${testID}-surface`}>
        <View style={styles.handle} />
        <Text style={styles.title}>{t('results.confidence.sheet.title')}</Text>

        <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
          {lines.map((fact, idx) => (
            <Text key={idx} style={styles.fact} testID={`${testID}-${leg}-fact-${idx}`}>
              {/* Backend-composed text — rendered verbatim per spec § 5b. */}
              {fact}
            </Text>
          ))}
        </ScrollView>

        <TouchableOpacity
          accessibilityRole="button"
          onPress={onClose}
          style={styles.closeBtn}
          testID={`${testID}-close`}
        >
          <Text style={styles.closeBtnText}>{t('results.confidence.sheet.close')}</Text>
        </TouchableOpacity>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  sheet: {
    backgroundColor: colors.bg.primary,
    borderTopLeftRadius: radii.hero,
    borderTopRightRadius: radii.hero,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    maxHeight: '70%',
  },
  handle: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    marginBottom: spacing.md,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  body: {
    maxHeight: 320,
  },
  bodyContent: {
    gap: spacing.sm,
    paddingBottom: spacing.md,
  },
  fact: {
    ...typography.body,
    color: colors.text.primary,
  },
  closeBtn: {
    marginTop: spacing.md,
    backgroundColor: colors.cta.primary,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
  },
  closeBtnText: {
    ...typography.bodyEmphasis,
    color: colors.cta.onPrimary,
  },
});

/**
 * PushPrePrompt — S69 U6 R3 (audit RT-12, App Review guideline 4.5.4).
 *
 * The one-time in-app explanation shown before the iOS / Android system
 * notification prompt, after a fresh compare result renders (ResultsScreen
 * decides WHEN via shouldShowPushPrePrompt). It says what the notifications
 * are — the three re-engagement pushes the backend actually sends (new
 * reviews on a pair you compared, what shoppers near you chose, a check-in
 * on a past decision), at most one a week — and that Profile switches them
 * off. Two actions:
 *   - Allow   -> the system prompt, once; a grant registers the push token;
 *   - Not now -> persisted; never re-asked automatically.
 * Both close the sheet.
 */

import React, { useState } from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Bell } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { answerPushPrePrompt, PushPrePromptAnswer } from '../services/pushPrePrompt';

interface Props {
  visible: boolean;
  /** Fires once the answer is persisted (and, for Allow, the OS answered). */
  onClose: (granted: boolean) => void;
}

export function PushPrePrompt({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);

  const answer = async (choice: PushPrePromptAnswer) => {
    if (busy) return;
    setBusy(true);
    let granted = false;
    try {
      granted = await answerPushPrePrompt(choice);
    } finally {
      setBusy(false);
      onClose(granted);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={() => answer('not_now')}
    >
      <View style={styles.backdrop}>
        <View style={styles.card} testID="push-preprompt" accessibilityViewIsModal>
          <View style={styles.iconWrap}>
            <Bell size={22} color={colors.accentDark} strokeWidth={2} />
          </View>
          <Text style={styles.title} accessibilityRole="header">
            {t('notifications.prePrompt.title')}
          </Text>
          <Text style={styles.body}>{t('notifications.prePrompt.body')}</Text>
          <TouchableOpacity
            testID="push-preprompt-allow"
            onPress={() => answer('allow')}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ disabled: busy }}
            style={[styles.cta, styles.ctaPrimary]}
          >
            <Text style={styles.ctaPrimaryLabel}>{t('notifications.prePrompt.allow')}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="push-preprompt-not-now"
            onPress={() => answer('not_now')}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ disabled: busy }}
            style={styles.cta}
          >
            <Text style={styles.ctaSecondaryLabel}>{t('notifications.prePrompt.notNow')}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  card: {
    backgroundColor: colors.bg.primary,
    borderTopLeftRadius: radii.hero,
    borderTopRightRadius: radii.hero,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing['2xl'],
    gap: spacing.md,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
  },
  body: {
    ...typography.body,
    color: colors.text.secondary,
  },
  cta: {
    minHeight: 48,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.base,
  },
  ctaPrimary: {
    backgroundColor: colors.cta.primary,
    marginTop: spacing.sm,
  },
  ctaPrimaryLabel: {
    ...typography.bodyEmphasis,
    color: colors.cta.onPrimary,
  },
  ctaSecondaryLabel: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
  },
});

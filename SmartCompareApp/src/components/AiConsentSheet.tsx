/**
 * AiConsentSheet — S69 U3 R1/R2 (App Review guideline 5.1.2(i)).
 *
 * The one-time AI-processing disclosure shown before the first compare (text,
 * link or camera) and before the camera / photo-picker permission request.
 * It names what MYEZ sends to OpenAI and what it does not; it promises no
 * opt-out (the Profile AI-sharing toggle routes nothing today, #266).
 *
 * State and the decision live in `useAiConsentGate` (services/aiConsent.ts);
 * this component only renders. Three actions:
 *   - Agree and continue -> the consent is recorded, the sheet closes, the
 *     pending action runs after the dismissal finishes;
 *   - Not now            -> the sheet closes, nothing is sent, the user stays
 *     where they were; the next attempt asks again;
 *   - Privacy Policy     -> the sheet closes (the pending action is dropped),
 *     then the in-app Legal screen opens — never behind the sheet.
 */

import React from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Sparkles } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import type { AiConsentSheetProps } from '../services/aiConsent';

export default function AiConsentSheet({
  visible,
  busy,
  onAgree,
  onNotNow,
  onOpenPrivacy,
  onDismiss,
}: AiConsentSheetProps) {
  const { t } = useTranslation();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onNotNow}
      onDismiss={onDismiss}
    >
      <View style={styles.backdrop}>
        <View style={styles.card} testID="ai-consent-sheet" accessibilityViewIsModal>
          <View style={styles.iconWrap}>
            <Sparkles size={22} color={colors.accentDark} strokeWidth={2} />
          </View>
          <Text style={styles.title} accessibilityRole="header">
            {t('aiConsent.title')}
          </Text>
          <Text style={styles.body}>{t('aiConsent.body')}</Text>
          <Text
            testID="ai-consent-privacy-link"
            style={styles.link}
            onPress={busy ? undefined : onOpenPrivacy}
            accessibilityRole="link"
            accessibilityState={{ disabled: busy }}
          >
            {t('aiConsent.link')}
          </Text>
          <TouchableOpacity
            testID="ai-consent-agree"
            onPress={onAgree}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ disabled: busy, busy }}
            style={[styles.cta, styles.ctaPrimary]}
          >
            <Text style={styles.ctaPrimaryLabel}>{t('aiConsent.agree')}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="ai-consent-not-now"
            onPress={onNotNow}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ disabled: busy }}
            style={styles.cta}
          >
            <Text style={styles.ctaSecondaryLabel}>{t('aiConsent.notNow')}</Text>
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
  link: {
    ...typography.body,
    color: colors.text.primary,
    fontWeight: '600',
    textDecorationLine: 'underline',
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

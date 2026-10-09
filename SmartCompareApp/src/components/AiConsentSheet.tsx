/**
 * AiConsentSheet — S69 U3 R1/R2 (App Review guideline 5.1.2(i)).
 *
 * The one-time AI-processing disclosure shown before the first compare (text,
 * link or camera) and before the camera / photo-picker permission request.
 * It names what MYEZ sends to OpenAI and what it does not; it promises no
 * opt-out (the organisation shares data with OpenAI, decision D3 = C; there
 * is no per-user opt-out).
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

import React, { useEffect, useRef } from 'react';
import {
  Modal,
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { Sparkles } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import type { AiConsentSheetProps } from '../services/aiConsent';

// UY1: the title, the Privacy link and both CTA labels cap their font scaling
// so they stay on screen at the largest Dynamic Type sizes; the body keeps its
// full scaling inside its scroll.
const FIXED_TEXT_MAX_FONT_SCALE = 1.6;
// UY1: the body scroll is capped at this fraction of the window height (a
// number, not a percentage on the card), so the bottom-anchored card grows
// upward instead of pushing the CTAs below the screen edge.
const BODY_MAX_HEIGHT_FRACTION = 0.4;

export default function AiConsentSheet({
  visible,
  busy,
  onAgree,
  onNotNow,
  onOpenPrivacy,
  onDismiss,
}: AiConsentSheetProps) {
  const { t } = useTranslation();
  const { height: windowHeight } = useWindowDimensions();
  const bodyMaxHeight = Math.round(BODY_MAX_HEIGHT_FRACTION * windowHeight);
  const bodyScrollRef = useRef<ScrollView>(null);

  // The body can run below the fold: flash the scroll indicators once each
  // time the sheet becomes visible (iOS shows none until the user scrolls).
  useEffect(() => {
    if (visible) {
      bodyScrollRef.current?.flashScrollIndicators();
    }
  }, [visible]);

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
          <Text
            style={styles.title}
            accessibilityRole="header"
            maxFontSizeMultiplier={FIXED_TEXT_MAX_FONT_SCALE}
          >
            {t('aiConsent.title')}
          </Text>
          {/* persistentScrollbar is Android-only (iOS ignores it). */}
          <ScrollView
            ref={bodyScrollRef}
            style={[styles.bodyScroll, { maxHeight: bodyMaxHeight }]}
            persistentScrollbar
          >
            <Text style={styles.body}>{t('aiConsent.body')}</Text>
          </ScrollView>
          <Text
            testID="ai-consent-privacy-link"
            style={styles.link}
            maxFontSizeMultiplier={FIXED_TEXT_MAX_FONT_SCALE}
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
            <Text style={styles.ctaPrimaryLabel} maxFontSizeMultiplier={FIXED_TEXT_MAX_FONT_SCALE}>
              {t('aiConsent.agree')}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="ai-consent-not-now"
            onPress={onNotNow}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ disabled: busy }}
            style={styles.cta}
          >
            <Text style={styles.ctaSecondaryLabel} maxFontSizeMultiplier={FIXED_TEXT_MAX_FONT_SCALE}>
              {t('aiConsent.notNow')}
            </Text>
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
  // UB-R13 / UY1: the body scrolls; its maxHeight is set inline from the
  // window height (no percentage cap on the card).
  bodyScroll: {
    flexGrow: 0,
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
